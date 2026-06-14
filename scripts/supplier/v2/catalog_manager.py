"""Maintain a fixed-size PawPath catalog (ACTIVE + DRAFT) across four categories."""

from __future__ import annotations

from typing import Any, Optional

from .. import shopify_client
from ..cj_client import CJClient
from ..config import (
    CATALOG_CATEGORY_KEYS,
    COLLECTIONS,
    MAX_CATALOG_PRODUCTS,
    MIN_OPPORTUNITY_SCORE,
    SHOPIFY_CATALOG,
    V2_IMPORT_STATUS,
)
from ..progress import ProgressLogger, get_logger
from .db import CatalogDB
from .discovery import score_raw_cj_product
from .merchandiser import import_opportunity
from .models import ProductOpportunity, ScoreBreakdown
from .pricing_engine import recommend_pricing
from .quality import apply_quality_gate

_TAG_TO_CATEGORY: dict[str, str] = {
    cfg["tag"]: key for key, cfg in COLLECTIONS.items()
}
_TAG_TO_CATEGORY.update(
    {
        "travel-essentials": "travel-gear",
        "road-trip": "car-essentials",
        "travel-feeding": "feeding-hydration",
        "car essentials": "car-essentials",
        "dog gear": "travel-gear",
    }
)


def find_product_by_cj_pid(cj_pid: str) -> Optional[dict[str, Any]]:
    for node in iter_products(query="tag:cj-sourced"):
        if _cj_pid_from_shopify(node) == cj_pid:
            return node
    return None


def reactivate_product(product_id: str, *, status: str = "DRAFT", publish: bool = False) -> None:
    set_product_status(product_id, status.upper())
    if publish and status.upper() == "ACTIVE":
        publish_to_online_store(product_id)


def _cj_pid_from_shopify(node: dict[str, Any]) -> Optional[str]:
    mf = node.get("pawpath_metafields") or {}
    if mf.get("cj_pid"):
        return str(mf["cj_pid"])
    for tag in node.get("tags") or []:
        if tag.startswith("cjpid-"):
            return tag.replace("cjpid-", "", 1)
    return None


def category_key_from_shopify(node: dict[str, Any]) -> Optional[str]:
    for tag in node.get("tags") or []:
        tag_l = tag.lower()
        if tag_l in _TAG_TO_CATEGORY:
            return _TAG_TO_CATEGORY[tag_l]
    product_type = (node.get("productType") or "").lower()
    for key, catalog in SHOPIFY_CATALOG.items():
        pt = catalog.get("product_type", "").lower()
        if pt and (pt in product_type or product_type in pt):
            return key
    return None


def _stored_score(node: dict[str, Any]) -> float:
    mf = node.get("pawpath_metafields") or {}
    raw = mf.get("opportunity_score")
    if raw is None:
        for tag in node.get("tags") or []:
            if tag.startswith("score-"):
                try:
                    return float(tag.replace("score-", "", 1))
                except ValueError:
                    pass
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def rescore_shopify_product(
    cj: CJClient,
    node: dict[str, Any],
    *,
    log: Optional[ProgressLogger] = None,
) -> Optional[ProductOpportunity]:
    """Re-score an existing Shopify CJ product from live CJ data."""
    cj_pid = _cj_pid_from_shopify(node)
    if not cj_pid:
        return None

    category_key = category_key_from_shopify(node)
    if not category_key or category_key not in CATALOG_CATEGORY_KEYS:
        return None

    try:
        cj_product = cj.get_product(cj_pid)
        opp = score_raw_cj_product(
            cj_product,
            search_query="shopify-rescore",
            hint_category=category_key,
            log=log,
        )
    except Exception as exc:
        log = log or get_logger()
        log.warn(f"rescore failed for {node.get('title', '')[:40]}: {exc}")
        opp = ProductOpportunity(
            cj_pid=cj_pid,
            cj_sku="",
            title_raw=node.get("title") or "",
            cost_usd=0.0,
            listed_num=0,
            inventory=0,
            category_key=category_key,
            search_query="shopify-rescore-fallback",
            opportunity_score=_stored_score(node),
            score_breakdown=ScoreBreakdown(),
            image_urls=[],
            image_score=0.0,
            images=[],
            pricing=recommend_pricing(10.0, category_key=category_key),
            rejection_reasons=["rescore_unavailable"],
        )

    opp.shopify_id = node["id"]
    opp.shopify_handle = node.get("handle")
    opp.shopify_status = node.get("status")
    return opp


def build_unified_pool(
    cj: CJClient,
    discovered: list[ProductOpportunity],
    *,
    log: Optional[ProgressLogger] = None,
) -> dict[str, ProductOpportunity]:
    """
    Merge re-scored Shopify catalog products with newly discovered CJ candidates.
    Keyed by cj_pid; Shopify entries win on conflict.
    """
    log = log or get_logger()
    pool: dict[str, ProductOpportunity] = {}

    shopify_nodes = shopify_client.list_managed_catalog_products()
    log.phase(f"Re-scoring {len(shopify_nodes)} Shopify catalog product(s)")
    for idx, node in enumerate(shopify_nodes, start=1):
        log.counter(idx, len(shopify_nodes), f"rescore: {(node.get('title') or '')[:40]}")
        opp = rescore_shopify_product(cj, node, log=log)
        if not opp or not opp.cj_pid:
            continue
        if opp.category_key not in CATALOG_CATEGORY_KEYS:
            continue
        pool[opp.cj_pid] = opp

    log.info(f"Shopify pool: {len(pool)} products in {len(CATALOG_CATEGORY_KEYS)} categories")

    new_count = 0
    for opp in discovered:
        if not opp.cj_pid or opp.cj_pid in pool:
            continue
        if opp.category_key not in CATALOG_CATEGORY_KEYS:
            continue
        pool[opp.cj_pid] = opp
        new_count += 1

    log.info(f"Added {new_count} new CJ candidate(s) — unified pool {len(pool)}")
    return pool


def _rank_pool(pool: dict[str, ProductOpportunity]) -> list[ProductOpportunity]:
    gated = [apply_quality_gate(opp) for opp in pool.values()]

    def sort_key(opp: ProductOpportunity) -> tuple:
        rejected = 1 if opp.rejected else 0
        in_shopify = 0 if opp.shopify_id else 1
        return (rejected, in_shopify, -opp.opportunity_score)

    return sorted(gated, key=sort_key)


def maintain_catalog(
    cj: CJClient,
    discovered: list[ProductOpportunity],
    *,
    max_total: int = MAX_CATALOG_PRODUCTS,
    import_status: Optional[str] = None,
    shop_id: Optional[str] = None,
    dry_run: bool = False,
    db: Optional[CatalogDB] = None,
    log: Optional[ProgressLogger] = None,
) -> dict[str, Any]:
    """
    Rank Shopify + CJ candidates, keep top `max_total` as ACTIVE/DRAFT, archive the rest,
    import new winners as draft when slots open.
    """
    log = log or get_logger()
    db = db or CatalogDB()
    status = (import_status or V2_IMPORT_STATUS).upper()

    pool = build_unified_pool(cj, discovered, log=log)
    ranked = _rank_pool(pool)
    winners = ranked[:max_total]
    losers = ranked[max_total:]

    winner_pids = {w.cj_pid for w in winners}
    shopify_winners = [w for w in winners if w.shopify_id]
    shopify_losers = [o for o in losers if o.shopify_id]
    to_import = [w for w in winners if not w.shopify_id]

    result: dict[str, Any] = {
        "max_catalog": max_total,
        "pool_size": len(ranked),
        "winners": len(winners),
        "losers": len(losers),
        "to_archive": len(shopify_losers),
        "to_import": len(to_import),
        "archived": [],
        "imported": [],
        "skipped": [],
        "failed": [],
        "score_updates": [],
        "dry_run": dry_run,
    }

    log.phase(
        f"Catalog plan — keep {len(winners)}/{max_total} "
        f"(archive {len(shopify_losers)}, import {len(to_import)} new as {status})"
    )

    if dry_run:
        for w in winners[:15]:
            flag = "shopify" if w.shopify_id else "new"
            log.detail(
                f"KEEP [{flag}] score={w.opportunity_score:.0f} "
                f"[{w.category_key}] {w.title_raw[:50]}"
            )
        for o in shopify_losers[:10]:
            log.detail(
                f"ARCHIVE score={o.opportunity_score:.0f} "
                f"[{o.category_key}] {o.title_raw[:50]}"
            )
        for o in to_import[:10]:
            log.detail(
                f"IMPORT score={o.opportunity_score:.0f} "
                f"[{o.category_key}] {o.title_raw[:50]}"
            )
        return result

    for opp in shopify_winners:
        if not opp.shopify_id:
            continue
        try:
            shopify_client.update_opportunity_score_metafield(
                opp.shopify_id, opp.opportunity_score
            )
            result["score_updates"].append(opp.cj_pid)
            db.upsert_scored(
                {
                    "cj_pid": opp.cj_pid,
                    "opportunity_score": opp.opportunity_score,
                    "category_key": opp.category_key,
                    "rejected": opp.rejected,
                    "rejection_reasons": opp.rejection_reasons,
                    "score_breakdown": opp.score_breakdown.to_dict(),
                }
            )
        except Exception as exc:
            log.warn(f"score metafield update failed {opp.title_raw[:40]}: {exc}")

    for opp in shopify_losers:
        if not opp.shopify_id:
            continue
        try:
            log.detail(f"archiving: {opp.title_raw[:50]} (score {opp.opportunity_score:.0f})")
            shopify_client.archive_product(opp.shopify_id)
            result["archived"].append(
                {"cj_pid": opp.cj_pid, "shopify_id": opp.shopify_id, "title": opp.title_raw}
            )
        except Exception as exc:
            result["failed"].append(
                {"cj_pid": opp.cj_pid, "action": "archive", "error": str(exc)}
            )
            log.warn(f"archive failed {opp.title_raw[:40]}: {exc}")

    # Archive in-catalog Shopify products not in the winner set
    for node in shopify_client.list_managed_catalog_products():
        cj_pid = _cj_pid_from_shopify(node)
        if not cj_pid or cj_pid in winner_pids:
            continue
        cat = category_key_from_shopify(node)
        if cat not in CATALOG_CATEGORY_KEYS:
            continue
        if any(a.get("shopify_id") == node["id"] for a in result["archived"]):
            continue
        try:
            log.detail(f"archiving (out of pool): {node.get('title', '')[:50]}")
            shopify_client.archive_product(node["id"])
            result["archived"].append(
                {
                    "cj_pid": cj_pid,
                    "shopify_id": node["id"],
                    "title": node.get("title"),
                }
            )
        except Exception as exc:
            result["failed"].append(
                {"cj_pid": cj_pid, "action": "archive", "error": str(exc)}
            )

    importable = [o for o in to_import if not o.rejected and o.opportunity_score >= MIN_OPPORTUNITY_SCORE]
    slots = max(0, max_total - len(shopify_winners))
    importable = importable[:slots]

    log.phase(f"Importing {len(importable)} new product(s) as {status}")
    for idx, opp in enumerate(importable, start=1):
        log.counter(idx, len(importable), f"import: {opp.title_raw[:40]}")
        try:
            existing = shopify_client.find_product_by_cj_pid(opp.cj_pid)
            if existing and existing.get("status") == "ARCHIVED":
                log.detail(f"reactivating archived: {existing.get('title', '')[:50]}")
                shopify_client.reactivate_product(existing["id"], status=status)
                shopify_client.update_opportunity_score_metafield(
                    existing["id"], opp.opportunity_score
                )
                result["imported"].append(
                    {
                        "cj_pid": opp.cj_pid,
                        "shopify_id": existing["id"],
                        "shopify_handle": existing.get("handle"),
                        "reactivated": True,
                    }
                )
                continue

            row = import_opportunity(
                cj, opp, db=db, shop_id=shop_id, status=status, log=log
            )
            if row.get("skipped"):
                result["skipped"].append(row)
            else:
                result["imported"].append(row)
                log.detail(f"✓ imported {row.get('shopify_handle')}")
        except Exception as exc:
            result["failed"].append(
                {"cj_pid": opp.cj_pid, "action": "import", "error": str(exc)}
            )
            log.warn(f"import failed {opp.title_raw[:40]}: {exc}")

    final_count = len(shopify_client.list_managed_catalog_products())
    result["final_catalog_count"] = final_count
    log.info(
        f"Catalog maintenance done — {final_count} ACTIVE/DRAFT products "
        f"({len(result['imported'])} imported, {len(result['archived'])} archived)"
    )
    return result
