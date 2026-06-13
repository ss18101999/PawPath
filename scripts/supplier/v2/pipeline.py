"""V2 autonomous pipeline orchestrator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from ..cj_client import CJClient
from ..config import DATA_DIR, MIN_OPPORTUNITY_SCORE, V2_OPPORTUNITIES_FILE
from ..progress import ProgressLogger, get_logger
from .db import CatalogDB
from .discovery import discover_products
from .merchandiser import import_opportunities
from .quality import filter_opportunities


def run_autonomous_pipeline(
    cj: CJClient,
    *,
    per_seed: int = 8,
    import_limit: int = 5,
    shop_id: Optional[str] = None,
    status: Optional[str] = None,
    dry_run: bool = False,
    log: Optional[ProgressLogger] = None,
) -> dict[str, Any]:
    """
    Full V2 pipeline:
    discover → score → quality filter → merchandise → import
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
    }

    log.phase("PawPath V2 pipeline started")
    log.info(f"mode={'dry-run' if dry_run else 'import'} import_limit={import_limit}")

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

    db.finish_pipeline_run(run_id, stats)
    log.phase(
        f"Pipeline complete — {stats['imported']} imported, "
        f"{stats['skipped']} skipped, {stats['failed']} failed"
    )
    return stats
