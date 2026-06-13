"""V2 pricing recommendation engine."""

from __future__ import annotations

from ..config import TARGET_GROSS_MARGIN_PCT
from ..pricing import parse_cost, retail_price
from .models import PricingRecommendation

# Category positioning multipliers (premium pet DTC)
CATEGORY_MULTIPLIERS: dict[str, float] = {
    "travel-gear": 2.9,
    "car-essentials": 3.0,
    "feeding-hydration": 2.8,
    "enrichment": 2.7,
}

# Market price bands for perceived-value anchoring (USD)
CATEGORY_PRICE_BANDS: dict[str, tuple[float, float]] = {
    "travel-gear": (18.95, 39.95),
    "car-essentials": (24.95, 59.95),
    "feeding-hydration": (14.95, 34.95),
    "enrichment": (16.95, 36.95),
}


def recommend_pricing(
    cost: float,
    *,
    category_key: str,
    shipping_estimate: float,
) -> PricingRecommendation:
    multiplier = CATEGORY_MULTIPLIERS.get(category_key, 2.8)
    landed = cost + shipping_estimate

    margin_target = TARGET_GROSS_MARGIN_PCT / 100
    margin_based = landed / max(1 - margin_target, 0.01)

    markup_based = cost * multiplier + 10
    low, high = CATEGORY_PRICE_BANDS.get(category_key, (14.95, 39.95))
    raw = max(margin_based, markup_based, low)
    raw = min(raw, high * 1.15)

    price_str, compare_str = retail_price(cost)
    retail = float(price_str)
    if raw > retail:
        import math

        retail = math.floor(raw) + 0.95

    compare = max(float(compare_str), retail * 1.28)
    compare = float(f"{compare:.2f}")

    gross = retail - landed
    margin_pct = (gross / retail * 100) if retail > 0 else 0.0

    return PricingRecommendation(
        cost=round(cost, 2),
        shipping_estimate=round(shipping_estimate, 2),
        landed_cost=round(landed, 2),
        retail_price=retail,
        compare_at_price=compare,
        gross_margin=round(gross, 2),
        margin_pct=round(margin_pct, 1),
    )


def pricing_from_product(product: dict, *, category_key: str, shipping_estimate: float) -> PricingRecommendation:
    cost = parse_cost(product.get("sellPrice") or product.get("nowPrice"))
    return recommend_pricing(cost, category_key=category_key, shipping_estimate=shipping_estimate)
