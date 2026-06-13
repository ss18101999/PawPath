"""Category detection and product filtering for PawPath niche."""

from __future__ import annotations

import re
from typing import Any, Optional

from .config import BLOCK_KEYWORDS, COLLECTIONS, MIN_COST_PRICE, MIN_LISTED_NUM, MIN_US_INVENTORY
from .pricing import parse_cost


def _text_blob(product: dict[str, Any]) -> str:
    parts = [
        product.get("nameEn") or "",
        product.get("productNameEn") or "",
        product.get("description") or "",
        product.get("threeCategoryName") or "",
        product.get("categoryName") or "",
        product.get("sku") or product.get("productSku") or "",
    ]
    return " ".join(parts).lower()


def is_blocked(product: dict[str, Any]) -> bool:
    blob = _text_blob(product)
    return any(kw in blob for kw in BLOCK_KEYWORDS)


def is_dog_relevant(product: dict[str, Any]) -> bool:
    blob = _text_blob(product)
    dog_terms = ["dog", "puppy", "pet", "canine", "pup "]
    return any(term in blob for term in dog_terms)


def is_category_relevant(product: dict[str, Any], category_key: str) -> bool:
    """Product text must match the PawPath category we're sourcing for."""
    blob = _text_blob(product)
    rules = {
        "car-essentials": [
            "car", "seat", "vehicle", "automobile", "hammock", "harness", "belt",
        ],
        "feeding-hydration": [
            "bowl", "feed", "feeder", "water", "hydration", "dispenser", "lick mat", "drink",
        ],
        "enrichment": [
            "snuffle", "lick mat", "puzzle", "enrichment", "interactive", "sniff", "foraging",
        ],
        "travel-gear": [
            "travel", "portable", "collapsible", "hiking", "walking", "treat pouch", "carrier",
            "leash", "bag", "bottle",
        ],
    }
    keywords = rules.get(category_key, [])
    return any(kw in blob for kw in keywords)


def score_product(product: dict[str, Any], query_category: str) -> float:
    """Higher = better candidate for PawPath."""
    if is_blocked(product):
        return -1

    if not is_category_relevant(product, query_category):
        return -1

    blob = _text_blob(product)
    score = 0.0

    listed = int(product.get("listedNum") or 0)
    if listed >= MIN_LISTED_NUM:
        score += min(listed / 100, 50)
    else:
        score -= 10

    inventory = int(product.get("warehouseInventoryNum") or product.get("totalVerifiedInventory") or 0)
    if inventory >= MIN_US_INVENTORY:
        score += min(inventory / 20, 25)
    else:
        score -= 15

    try:
        price = parse_cost(product.get("sellPrice") or product.get("nowPrice"))
    except (TypeError, ValueError):
        price = 0
    if price < MIN_COST_PRICE:
        score -= 30
    elif 3 <= price <= 35:
        score += 15
    elif price > 45:
        score -= 20

    if is_dog_relevant(product):
        score += 20
    else:
        score -= 5

    cfg = COLLECTIONS.get(query_category, {})
    for q in cfg.get("queries", []):
        for word in q.lower().split():
            if len(word) > 3 and word in blob:
                score += 3

    if product.get("addMarkStatus") == 1:
        score += 5

    return score


def pick_category(product: dict[str, Any]) -> Optional[str]:
    """Best PawPath collection for a product."""
    blob = _text_blob(product)
    rules = {
        "car-essentials": ["car seat", "seat cover", "seat belt", "car hammock", "vehicle", "automobile"],
        "feeding-hydration": ["slow feed", "feeder", "bowl", "lick mat", "water bottle", "hydration", "dispenser"],
        "enrichment": ["snuffle", "lick mat", "puzzle", "enrichment", "interactive", "sniff"],
        "travel-gear": ["treat pouch", "walking", "hiking", "travel", "portable", "collapsible", "water bottle", "carrier"],
    }
    best_cat = None
    best_hits = 0
    for cat, keywords in rules.items():
        hits = sum(1 for kw in keywords if kw in blob)
        if hits > best_hits:
            best_hits = hits
            best_cat = cat
    return best_cat if best_hits > 0 else None


def clean_title(name: str) -> str:
    title = re.sub(r"\s+", " ", name or "").strip()
    title = re.sub(r"^(wholesale|hot sale|new)\s+", "", title, flags=re.I)
    if len(title) > 80:
        title = title[:77].rsplit(" ", 1)[0] + "..."
    return title
