"""Research winning CJ products for PawPath categories."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .categorize import clean_title, pick_category, score_product
from .cj_client import CJClient
from .config import (
    CANDIDATES_FILE,
    COLLECTIONS,
    DATA_DIR,
    DEFAULT_PER_CATEGORY,
    MAX_COST_PRICE,
    MIN_COST_PRICE,
)
from .pricing import parse_cost


def research_candidates(
    cj: CJClient,
    *,
    per_category: int = DEFAULT_PER_CATEGORY,
    max_cost: float = MAX_COST_PRICE,
) -> dict[str, Any]:
    seen_skus: set[str] = set()
    by_category: dict[str, list[dict[str, Any]]] = {k: [] for k in COLLECTIONS}

    for category_key, cfg in COLLECTIONS.items():
        pool: list[dict[str, Any]] = []
        for query in cfg["queries"]:
            for page in range(1, 4):
                for order_by in (0, 1):
                    try:
                        results = cj.search_products_v2(
                            keyword=query,
                            page=page,
                            size=50,
                            order_by=order_by,
                            features=["enable_description"] if order_by == 0 else None,
                        )
                    except Exception as exc:  # noqa: BLE001 — collect per-query failures
                        print(f"  warn: search failed for '{query}' page {page}: {exc}")
                        break
                    if not results:
                        continue

                    for product in results:
                        sku = product.get("sku") or product.get("spu") or product.get("id")
                        if not sku or sku in seen_skus:
                            continue
                        seen_skus.add(sku)

                        cost = parse_cost(product.get("sellPrice") or product.get("nowPrice"))
                        if cost < MIN_COST_PRICE or cost > max_cost:
                            continue

                        s = score_product(product, category_key)
                        if s < 10:
                            continue

                        pool.append(
                            {
                                "score": s,
                                "category": category_key,
                                "cj_pid": product.get("id"),
                                "cj_sku": sku,
                                "title_raw": product.get("nameEn") or "",
                                "title": clean_title(product.get("nameEn") or ""),
                                "cost_usd": cost,
                                "listed_num": product.get("listedNum"),
                                "inventory": product.get("warehouseInventoryNum"),
                                "image": product.get("bigImage"),
                                "description": (product.get("description") or "")[:2000],
                                "search_query": query,
                            }
                        )

                    if len(pool) >= per_category * 4:
                        break
                if len(pool) >= per_category * 4:
                    break
            if len(pool) >= per_category * 4:
                break

        pool.sort(key=lambda x: x["score"], reverse=True)
        by_category[category_key] = pool[:per_category]

    flat: list[dict[str, Any]] = []
    for cat, items in by_category.items():
        for item in items:
            assigned = pick_category(
                {
                    "nameEn": item["title_raw"],
                    "description": item.get("description"),
                }
            )
            if assigned:
                item["category"] = assigned
            item["collection_tag"] = COLLECTIONS[item["category"]]["tag"]
            flat.append(item)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "per_category": per_category,
        "total_candidates": len(flat),
        "by_category": {k: len(v) for k, v in by_category.items()},
        "candidates": flat,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATES_FILE.write_text(json.dumps(report, indent=2))
    return report
