"""V2 Product Opportunity Score engine."""

from __future__ import annotations

import re
from typing import Any

from ..categorize import _text_blob, is_blocked, is_category_relevant, pick_category
from ..config import MAX_COST_PRICE, MIN_COST_PRICE, TARGET_GROSS_MARGIN_PCT
from ..pricing import parse_cost
from .models import ScoreBreakdown


CHEAP_SIGNALS = [
    "wholesale",
    "factory",
    "dropship",
    "random color",
    "no box",
    "opp bag",
    "clearance",
    "liquidation",
]

PREMIUM_SIGNALS = [
    "portable",
    "waterproof",
    "leak proof",
    "collapsible",
    "silicone",
    "non-slip",
    "durable",
    "travel",
    "premium",
    "ergonomic",
]


def _int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def compute_opportunity_score(
    product: dict[str, Any],
    *,
    category_key: str,
    image_score: float = 50.0,
) -> tuple[float, ScoreBreakdown, list[str]]:
    """Return (total score 0-100, breakdown, rejection reasons)."""
    reasons: list[str] = []
    if is_blocked(product):
        reasons.append("blocked_niche_keyword")
    if not is_category_relevant(product, category_key):
        reasons.append("off_category")

    blob = _text_blob(product)
    bd = ScoreBreakdown()

    listed = _int(product.get("listedNum"))
    bd.popularity = min(listed / 200, 1.0) * 18
    bd.demand = min(listed / 100, 1.0) * 12

    comment_num = _int(product.get("commentNum") or product.get("evaluationNum"))
    rating = _float(product.get("score") or product.get("evaluationScore"))
    if comment_num > 0:
        bd.ratings = min(comment_num / 50, 1.0) * 8
        if rating >= 4.5:
            bd.ratings += 4
        elif rating >= 4.0:
            bd.ratings += 2
        elif rating > 0 and rating < 3.5:
            reasons.append("low_rating")
    else:
        bd.ratings = 3

    if product.get("addMarkStatus") == 1 or product.get("isNew"):
        bd.growth = 8
    create_time = product.get("createTime") or product.get("shelveTime")
    if create_time and _int(create_time) > 0:
        bd.growth += 2

    desc_len = len(product.get("description") or "")
    bd.quality = min(desc_len / 500, 1.0) * 6
    bd.quality += min(image_score / 100, 1.0) * 9
    if image_score < 45:
        reasons.append("weak_images")

    inventory = _int(product.get("warehouseInventoryNum") or product.get("totalVerifiedInventory"))
    if inventory >= 20:
        bd.us_market = 12
    elif inventory >= 5:
        bd.us_market = 8
    elif inventory > 0:
        bd.us_market = 4
    else:
        bd.us_market = 1
        reasons.append("low_us_inventory")

    delivery = product.get("deliveryTime") or product.get("shippingTime")
    if delivery:
        days = re.findall(r"\d+", str(delivery))
        if days:
            max_days = max(int(d) for d in days)
            if max_days <= 10:
                bd.shipping = 8
            elif max_days <= 15:
                bd.shipping = 5
            else:
                bd.shipping = 2
                reasons.append("slow_shipping")
    else:
        bd.shipping = 4

    generic_hits = sum(1 for s in CHEAP_SIGNALS if s in blob)
    premium_hits = sum(1 for s in PREMIUM_SIGNALS if s in blob)
    bd.uniqueness = max(0, 8 - generic_hits * 2)
    bd.brandability = min(premium_hits * 2.5, 10)
    if generic_hits >= 2:
        reasons.append("low_brandability")

    cost = parse_cost(product.get("sellPrice") or product.get("nowPrice"))
    if cost < MIN_COST_PRICE:
        reasons.append("cost_too_low")
    if cost > MAX_COST_PRICE:
        reasons.append("cost_too_high")

    ship_est = 4.5
    landed = cost + ship_est
    min_retail = landed / max(1 - TARGET_GROSS_MARGIN_PCT / 100, 0.01)
    potential_margin = (min_retail - landed) / min_retail * 100 if min_retail > 0 else 0
    if potential_margin >= TARGET_GROSS_MARGIN_PCT:
        bd.margin = 10
    elif potential_margin >= 40:
        bd.margin = 6
    else:
        bd.margin = 2
        reasons.append("weak_margin")

    if "dog" not in blob and "puppy" not in blob and "pet" not in blob:
        reasons.append("not_pet_relevant")
        bd.brandability -= 5

    total = min(100.0, bd.total)
    return total, bd, reasons


def resolve_category(product: dict[str, Any], fallback: str) -> str:
    return pick_category(product) or fallback
