"""V2 autonomous pipeline orchestrator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from ..cj_client import CJClient
from ..config import DATA_DIR, MAX_CATALOG_PRODUCTS, V2_OPPORTUNITIES_FILE, V2_PIPELINE_LOG
from ..progress import ProgressLogger, get_logger
from .catalog_manager import maintain_catalog
from .db import CatalogDB
from .discovery import discover_products
from .merchandiser import import_opportunities
from .quality import filter_opportunities


def run_autonomous_pipeline(
    cj: CJClient,
    *,
    per_seed: int = 8,
    import_limit: int = 5,
    max_catalog: int = MAX_CATALOG_PRODUCTS,
    maintain: bool = True,
    shop_id: Optional[str] = None,
    status: Optional[str] = None,
    dry_run: bool = False,
    log: Optional[ProgressLogger] = None,
) -> dict[str, Any]:
    """
    Full V2 pipeline:
    discover → score → quality filter → [catalog maintenance] → import / archive
    """
    log = log or get_logger()
    db = CatalogDB()
    run_id = db.start_pipeline_run()
    stats: dict[str, Any] = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "discovered": 0,
        "accepted": 0,
        "rejected": 0,
        "imported": 0,
        "skipped": 0,
        "failed": 0,
        "archived": 0,
        "max_catalog": max_catalog,
        "maintain_catalog": maintain,
    }

    log.phase("PawPath V2 pipeline started")
    mode = "dry-run" if dry_run else "import"
    log.info(
        f"mode={mode} maintain={maintain} max_catalog={max_catalog} "
        f"import_limit={import_limit if not maintain else 'auto'}"
    )

    with log.span("Phase 1 — Discovery & scoring"):
        discovered = discover_products(cj, per_seed=per_seed, db=db, log=log)
    stats["discovered"] = len(discovered)
    log.info(f"Discovered {len(discovered)} scored opportunities")

    accepted, rejected = filter_opportunities(discovered, log=log)
    stats["accepted"] = len(accepted)
    stats["rejected"] = len(rejected)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "accepted": [o.to_dict() for o in accepted[:50]],
        "rejected_sample": [o.to_dict() for o in rejected[:20]],
    }
    V2_OPPORTUNITIES_FILE.write_text(json.dumps(report, indent=2))
    log.info(f"Report saved → {V2_OPPORTUNITIES_FILE}")

    if maintain:
        log.phase(
            f"Phase 2 — Catalog maintenance (target {max_catalog} ACTIVE+DRAFT across 4 categories)"
        )
        catalog_result = maintain_catalog(
            cj,
            accepted,
            max_total=max_catalog,
            import_status=status,
            shop_id=shop_id,
            dry_run=dry_run,
            db=db,
            log=log,
        )
        stats.update(
            {
                "catalog": catalog_result,
                "imported": len(catalog_result.get("imported") or []),
                "skipped": len(catalog_result.get("skipped") or []),
                "failed": len(catalog_result.get("failed") or []),
                "archived": len(catalog_result.get("archived") or []),
                "final_catalog_count": catalog_result.get("final_catalog_count"),
            }
        )
        if dry_run:
            stats["dry_run"] = True
        stats["finished_at"] = datetime.now(timezone.utc).isoformat()
        V2_PIPELINE_LOG.write_text(json.dumps(stats, indent=2, default=str))
        db.finish_pipeline_run(run_id, stats)
        log.phase(
            f"Pipeline finished — catalog {stats.get('final_catalog_count', '?')} products "
            f"({stats['imported']} imported, {stats['archived']} archived)"
            if not dry_run
            else "Pipeline finished (dry run)"
        )
        return stats

    if dry_run:
        log.phase(f"Dry run — top {import_limit} accepted (no Shopify changes)")
        for i, opp in enumerate(accepted[:import_limit], start=1):
            log.detail(
                f"{i}. [{opp.category_key}] score={opp.opportunity_score:.0f} "
                f"${opp.cost_usd:.2f}→${opp.pricing.retail_price:.2f} "
                f"({opp.pricing.margin_pct:.0f}% margin) img={opp.image_score:.0f} — "
                f"{opp.title_raw[:55]}"
            )
        if not accepted:
            log.warn("No products passed quality gate")
        stats["dry_run"] = True
        db.finish_pipeline_run(run_id, stats)
        log.phase("Pipeline finished (dry run)")
        return stats

    if not accepted:
        log.warn("No products passed quality gate. Pipeline complete.")
        db.finish_pipeline_run(run_id, stats)
        return stats

    log.phase(f"Phase 4–6 — Importing top {import_limit} curated products")
    import_log = import_opportunities(
        cj,
        accepted,
        limit=import_limit,
        shop_id=shop_id,
        status=status,
        log=log,
    )
    stats["imported"] = len(import_log.get("imported") or [])
    stats["skipped"] = len(import_log.get("skipped") or [])
    stats["failed"] = len(import_log.get("failed") or [])
    stats["finished_at"] = datetime.now(timezone.utc).isoformat()

    V2_PIPELINE_LOG.write_text(json.dumps({**stats, "import_log": import_log}, indent=2, default=str))
    db.finish_pipeline_run(run_id, stats)
    log.phase(
        f"Pipeline complete — {stats['imported']} imported, "
        f"{stats['skipped']} skipped, {stats['failed']} failed"
    )
    return stats
