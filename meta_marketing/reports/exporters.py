"""Export report payloads to JSON and CSV."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from meta_marketing.utils.logging import get_logger


def export_json(payload: dict[str, Any], output_path: Path) -> Path:
    log = get_logger()
    log.detail(f"Writing JSON report → {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, default=str))
    return output_path


def export_csv(payload: dict[str, Any], output_path: Path) -> Path:
    log = get_logger()
    log.detail(f"Writing CSV report → {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = _flatten_report_rows(payload)
    if not rows:
        rows = [{"message": "No data available for this period"}]

    fieldnames = sorted({key for row in rows for key in row})
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def _flatten_report_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    report_date = payload.get("report_date")
    account = payload.get("account_overview", {}).get("metrics", {})

    rows.append(
        {
            "section": "account",
            "report_date": report_date,
            "entity_id": payload.get("ad_account_id"),
            "entity_name": "Account Total",
            **{f"account_{key}": value for key, value in account.items()},
        }
    )

    for campaign in payload.get("campaigns", []):
        metrics = campaign.get("metrics", {})
        rows.append(
            {
                "section": "campaign",
                "report_date": report_date,
                "entity_id": campaign.get("campaign_id"),
                "entity_name": campaign.get("campaign_name"),
                **{f"campaign_{key}": value for key, value in metrics.items()},
            }
        )

    for ad in payload.get("ad_analysis", {}).get("winning_ads", []):
        metrics = ad.get("metrics", {})
        rows.append(
            {
                "section": "winning_ad",
                "report_date": report_date,
                "entity_id": ad.get("ad_id"),
                "entity_name": ad.get("ad_name"),
                "classification": ad.get("classification"),
                "score": ad.get("score"),
                **{f"ad_{key}": value for key, value in metrics.items()},
            }
        )

    for ad in payload.get("ad_analysis", {}).get("losing_ads", []):
        metrics = ad.get("metrics", {})
        rows.append(
            {
                "section": "losing_ad",
                "report_date": report_date,
                "entity_id": ad.get("ad_id"),
                "entity_name": ad.get("ad_name"),
                "classification": ad.get("classification"),
                "score": ad.get("score"),
                **{f"ad_{key}": value for key, value in metrics.items()},
            }
        )

    return rows
