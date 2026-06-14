"""Tests for Meta Marketing utilities (no API calls)."""

from __future__ import annotations

from meta_marketing.utils.metrics import MetricSnapshot, parse_insight_row


def test_parse_insight_row_computes_roas_from_purchase_value() -> None:
    row = {
        "spend": "100.00",
        "impressions": "10000",
        "clicks": "200",
        "ctr": "2.0",
        "cpc": "0.50",
        "cpm": "10.00",
        "actions": [{"action_type": "purchase", "value": "5"}],
        "action_values": [{"action_type": "purchase", "value": "250.00"}],
        "purchase_roas": [],
    }
    metrics = parse_insight_row(row)
    assert metrics.spend == 100.0
    assert metrics.purchases == 5
    assert metrics.purchase_value == 250.0
    assert metrics.roas == 2.5


def test_parse_insight_row_empty_returns_zeros() -> None:
    metrics = parse_insight_row({})
    assert metrics == MetricSnapshot()
