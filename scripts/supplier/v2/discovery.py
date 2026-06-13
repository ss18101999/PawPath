"""V2 trending product discovery engine."""

from __future__ import annotations

from typing import Any, Optional

from ..cj_client import CJClient
from ..config import COLLECTIONS, DEFAULT_SHIPPING_ESTIMATE, DISCOVERY_SEEDS, MAX_COST_PRICE, MIN_COST_PRICE
from ..pricing import parse_cost
from ..progress import ProgressLogger, get_logger
from .db import CatalogDB
from .images import assess_product_images
from .models import ProductOpportunity
from .pricing_engine import recommend_pricing
from .scoring import compute_opportunity_score, resolve_category


def _collect_image_urls(product: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    main = product.get("bigImage") or product.get("productImage")
    if main:
        urls.append(main)
    for u in product.get("productImageSet") or []:
        if u:
            urls.append(u)
    return urls


def discover_products(
    cj: CJClient,
    *,
    per_seed: int = 8,
    max_pages: int = 2,
    db: Optional[CatalogDB] = None,
    log: Optional[ProgressLogger] = None,
) -> list[ProductOpportunity]:
    """Search CJ catalog across seeds and category queries; return scored opportunities."""
    log = log or get_logger()
    db = db or CatalogDB()
    seen: set[str] = set()
    raw_pool: list[tuple[dict[str, Any], str, str]] = []

    seeds: list[tuple[str, str]] = []
    for key, cfg in COLLECTIONS.items():
        for q in cfg["queries"]:
            seeds.append((q, key))
    for q in DISCOVERY_SEEDS:
        seeds.append((q, ""))

    total_searches = len(seeds) * max_pages * 2
    search_num = 0
    log.phase(f"Discovery — {len(seeds)} search terms, up to {max_pages} pages each")

    for seed_idx, (query, hint_category) in enumerate(seeds, start=1):
        new_for_seed = 0
        for page in range(1, max_pages + 1):
            for order_by in (1, 0):
                search_num += 1
                sort_label = "popularity" if order_by == 1 else "relevance"
                log.counter(
                    search_num,
                    total_searches,
                    f'search "{query}" p{page} ({sort_label})',
                    every=max(1, total_searches // 20),
                )
                try:
                    results = cj.search_products_v2(
                        keyword=query,
                        page=page,
                        size=50,
                        order_by=order_by,
                        features=["enable_description"] if order_by == 0 else None,
                    )
                except Exception as exc:
                    log.warn(f'search failed "{query}" p{page}: {exc}')
                    break
                if not results:
                    break

                added = 0
                for product in results:
                    sku = product.get("sku") or product.get("spu") or product.get("id")
                    if not sku or sku in seen:
                        continue
                    cost = parse_cost(product.get("sellPrice") or product.get("nowPrice"))
                    if cost < MIN_COST_PRICE or cost > MAX_COST_PRICE:
                        continue
                    seen.add(sku)
                    raw_pool.append((product, query, hint_category))
                    added += 1
                    new_for_seed += 1
                    db.upsert_discovered(
                        {
                            "cj_pid": product.get("id"),
                            "cj_sku": sku,
                            "title_raw": product.get("nameEn") or "",
                            "raw": product,
                            "search_query": query,
                        }
                    )

                if added:
                    log.detail(f'"{query}" p{page} ({sort_label}): +{added} new (pool {len(raw_pool)})')

        if new_for_seed:
            log.detail(f"term {seed_idx}/{len(seeds)} done — +{new_for_seed} for \"{query}\"")

    log.info(f"Search complete — {len(raw_pool)} unique products to score")

    opportunities: list[ProductOpportunity] = []
    total_score = len(raw_pool)
    log.phase(f"Scoring & image checks — {total_score} products")

    for idx, (product, query, hint_category) in enumerate(raw_pool, start=1):
        title_preview = (product.get("nameEn") or "untitled")[:50]
        log.counter(
            idx,
            total_score,
            f"scoring: {title_preview}",
            every=max(1, total_score // 25),
        )

        category_key = resolve_category(product, hint_category or "travel-gear")
        image_urls = _collect_image_urls(product)
        _, image_score = assess_product_images(
            image_urls,
            max_images=4,
            log=log if idx % 10 == 1 or idx == total_score else None,
        )

        score, breakdown, reject_reasons = compute_opportunity_score(
            product,
            category_key=category_key,
            image_score=image_score,
        )
        cost = parse_cost(product.get("sellPrice") or product.get("nowPrice"))
        pricing = recommend_pricing(
            cost,
            category_key=category_key,
            shipping_estimate=DEFAULT_SHIPPING_ESTIMATE,
        )

        opp = ProductOpportunity(
            cj_pid=str(product.get("id") or ""),
            cj_sku=str(product.get("sku") or product.get("spu") or ""),
            title_raw=product.get("nameEn") or "",
            cost_usd=cost,
            listed_num=int(product.get("listedNum") or 0),
            inventory=int(product.get("warehouseInventoryNum") or 0),
            category_key=category_key,
            search_query=query,
            opportunity_score=score,
            score_breakdown=breakdown,
            image_urls=image_urls,
            image_score=image_score,
            images=[],
            pricing=pricing,
            rejection_reasons=reject_reasons,
            cj_product=product,
        )
        opportunities.append(opp)
        db.upsert_scored(
            {
                "cj_pid": opp.cj_pid,
                "opportunity_score": opp.opportunity_score,
                "category_key": opp.category_key,
                "rejected": False,
                "rejection_reasons": opp.rejection_reasons,
                "score_breakdown": opp.score_breakdown.to_dict(),
            }
        )

        if idx % max(1, total_score // 10) == 0 or idx == total_score:
            top = max(opportunities, key=lambda o: o.opportunity_score)
            log.detail(
                f"progress — best so far: score {top.opportunity_score:.0f} "
                f"\"{(top.title_raw or '')[:40]}\""
            )

    opportunities.sort(key=lambda o: o.opportunity_score, reverse=True)
    if opportunities:
        log.info(
            f"Ranking done — top score {opportunities[0].opportunity_score:.0f}: "
            f"{opportunities[0].title_raw[:55]}"
        )
    return opportunities
