"""Retail pricing from CJ cost."""

from __future__ import annotations

import math
import os
import re


def parse_cost(value: object) -> float:
    """Parse CJ price fields like '2.81 -- 5.44' or numeric values."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[\d.]+", str(value))
    return float(match.group()) if match else 0.0


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def retail_price(cost: float) -> tuple[str, str]:
    """
    Returns (price, compare_at_price) as strings with 2 decimals.
    Uses .95 charm pricing.
    """
    multiplier = _env_float("TARGET_MARGIN_MULTIPLIER", 2.8)
    min_retail = _env_float("MIN_RETAIL_PRICE", 14.95)

    raw = max(cost * multiplier, cost + 10, min_retail)
    price = math.floor(raw) + 0.95
    if price < min_retail:
        price = min_retail

    compare_raw = price * 1.33
    compare = math.floor(compare_raw) + 0.95

    return f"{price:.2f}", f"{compare:.2f}"
