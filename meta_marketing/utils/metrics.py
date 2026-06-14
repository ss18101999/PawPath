"""Parse and normalize Meta Ads insight metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PURCHASE_ACTION_TYPES = frozenset(
    {
        "purchase",
        "omni_purchase",
        "offsite_conversion.fb_pixel_purchase",
        "onsite_conversion.purchase",
    }
)


@dataclass
class MetricSnapshot:
    spend: float = 0.0
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0
    cpc: float = 0.0
    cpm: float = 0.0
    purchases: int = 0
    purchase_value: float = 0.0
    roas: float = 0.0
    entity_id: str | None = None
    entity_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def extract_action_count(actions: list[dict[str, Any]] | None, action_types: set[str]) -> int:
    if not actions:
        return 0
    total = 0
    for action in actions:
        action_type = str(action.get("action_type", "")).lower()
        if action_type in action_types:
            total += _to_int(action.get("value"))
    return total


def extract_action_value(action_values: list[dict[str, Any]] | None, action_types: set[str]) -> float:
    if not action_values:
        return 0.0
    total = 0.0
    for action in action_values:
        action_type = str(action.get("action_type", "")).lower()
        if action_type in action_types:
            total += _to_float(action.get("value"))
    return total


def extract_purchase_roas(purchase_roas: list[dict[str, Any]] | None) -> float:
    if not purchase_roas:
        return 0.0
    for entry in purchase_roas:
        action_type = str(entry.get("action_type", "")).lower()
        if action_type in {"omni_purchase", "purchase"}:
            return _to_float(entry.get("value"))
    if purchase_roas:
        return _to_float(purchase_roas[0].get("value"))
    return 0.0


def parse_insight_row(
    row: dict[str, Any],
    *,
    entity_id_key: str | None = None,
    entity_name_key: str | None = None,
) -> MetricSnapshot:
    spend = _to_float(row.get("spend"))
    purchases = extract_action_count(row.get("actions"), PURCHASE_ACTION_TYPES)
    purchase_value = extract_action_value(row.get("action_values"), PURCHASE_ACTION_TYPES)
    roas = extract_purchase_roas(row.get("purchase_roas"))
    if roas == 0.0 and spend > 0 and purchase_value > 0:
        roas = purchase_value / spend

    return MetricSnapshot(
        spend=spend,
        impressions=_to_int(row.get("impressions")),
        clicks=_to_int(row.get("clicks")),
        ctr=_to_float(row.get("ctr")),
        cpc=_to_float(row.get("cpc")),
        cpm=_to_float(row.get("cpm")),
        purchases=purchases,
        purchase_value=purchase_value,
        roas=roas,
        entity_id=str(row[entity_id_key]) if entity_id_key and row.get(entity_id_key) else None,
        entity_name=str(row[entity_name_key]) if entity_name_key and row.get(entity_name_key) else None,
    )
