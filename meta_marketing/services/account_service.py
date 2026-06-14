"""Account-level performance overview."""

from __future__ import annotations

from datetime import date
from typing import Any

from meta_marketing.api.meta_client import MetaMarketingClient
from meta_marketing.utils.logging import get_logger
from meta_marketing.utils.metrics import MetricSnapshot, parse_insight_row


class AccountService:
    def __init__(self, client: MetaMarketingClient) -> None:
        self.client = client
        self.log = get_logger()

    def get_overview(
        self,
        *,
        date_preset: str | None = "last_7d",
        day: date | None = None,
    ) -> dict[str, Any]:
        period = day.isoformat() if day else date_preset
        self.log.phase(f"Account overview — {period}")

        rows = self.client.get_account_insights(date_preset=date_preset, day=day)
        if not rows:
            self.log.warn("No insight data returned for this period")
            metrics = MetricSnapshot()
        else:
            metrics = parse_insight_row(rows[0])
            self.log.detail(
                f"Spend ${metrics.spend:.2f} | Impressions {metrics.impressions:,} | "
                f"Clicks {metrics.clicks:,} | CTR {metrics.ctr:.2f}% | "
                f"Purchases {metrics.purchases} | ROAS {metrics.roas:.2f}x"
            )

        return {
            "ad_account_id": self.client.config.normalized_ad_account_id,
            "period": period,
            "metrics": metrics.to_dict(),
        }

    def get_overview_metrics(
        self,
        *,
        date_preset: str | None = "last_7d",
        day: date | None = None,
    ) -> MetricSnapshot:
        rows = self.client.get_account_insights(date_preset=date_preset, day=day)
        if not rows:
            return MetricSnapshot()
        return parse_insight_row(rows[0])
