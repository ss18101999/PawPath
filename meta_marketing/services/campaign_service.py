"""Campaign listing and management."""

from __future__ import annotations

from datetime import date
from typing import Any

from facebook_business.adobjects.campaign import Campaign

from meta_marketing.api.meta_client import MetaMarketingClient
from meta_marketing.utils.logging import get_logger
from meta_marketing.utils.metrics import MetricSnapshot, parse_insight_row


class CampaignService:
    def __init__(self, client: MetaMarketingClient) -> None:
        self.client = client
        self.log = get_logger()

    def list_campaigns(self, *, limit: int = 100) -> list[dict[str, Any]]:
        self.log.phase(f"List campaigns (limit={limit})")
        campaigns = self.client.list_campaigns(limit=limit)
        active = sum(1 for c in campaigns if c.get("effective_status") == "ACTIVE")
        paused = sum(1 for c in campaigns if c.get("effective_status") == "PAUSED")
        self.log.detail(f"Found {len(campaigns)} campaign(s) — {active} active, {paused} paused")

        for idx, row in enumerate(campaigns[:10], start=1):
            self.log.counter(
                idx,
                min(len(campaigns), 10),
                f"{row.get('name', '')[:45]} [{row.get('effective_status')}]",
                force=True,
            )
        if len(campaigns) > 10:
            self.log.detail(f"... and {len(campaigns) - 10} more")

        return [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "status": row.get("status"),
                "effective_status": row.get("effective_status"),
                "objective": row.get("objective"),
                "daily_budget": row.get("daily_budget"),
                "lifetime_budget": row.get("lifetime_budget"),
                "created_time": row.get("created_time"),
                "updated_time": row.get("updated_time"),
            }
            for row in campaigns
        ]

    def pause_campaign(self, campaign_id: str) -> dict[str, Any]:
        self.log.phase(f"Pause campaign {campaign_id}")
        updated = self.client.set_campaign_status(
            campaign_id, status=Campaign.Status.paused
        )
        self.log.detail(f"Paused: {updated.get('name')}")
        return {
            "id": updated.get("id"),
            "name": updated.get("name"),
            "status": updated.get("status"),
            "effective_status": updated.get("effective_status"),
            "action": "paused",
        }

    def resume_campaign(self, campaign_id: str) -> dict[str, Any]:
        self.log.phase(f"Resume campaign {campaign_id}")
        updated = self.client.set_campaign_status(
            campaign_id, status=Campaign.Status.active
        )
        self.log.detail(f"Resumed: {updated.get('name')}")
        return {
            "id": updated.get("id"),
            "name": updated.get("name"),
            "status": updated.get("status"),
            "effective_status": updated.get("effective_status"),
            "action": "resumed",
        }

    def get_campaign_performance(
        self,
        campaign_id: str,
        *,
        date_preset: str | None = "last_7d",
        day: date | None = None,
    ) -> dict[str, Any]:
        period = day.isoformat() if day else date_preset
        self.log.phase(f"Campaign performance — {campaign_id} ({period})")

        campaign = self.client.get_campaign(campaign_id)
        rows = self.client.get_campaign_insights(
            campaign_id, date_preset=date_preset, day=day
        )
        metrics = parse_insight_row(rows[0]) if rows else MetricSnapshot()
        if rows:
            self.log.detail(
                f"{campaign.get('name')}: spend ${metrics.spend:.2f}, "
                f"clicks {metrics.clicks}, ROAS {metrics.roas:.2f}x"
            )
        else:
            self.log.warn(f"No performance data for {campaign.get('name')}")

        return {
            "campaign": {
                "id": campaign.get("id"),
                "name": campaign.get("name"),
                "status": campaign.get("status"),
                "effective_status": campaign.get("effective_status"),
                "objective": campaign.get("objective"),
            },
            "period": period,
            "metrics": metrics.to_dict(),
        }

    def get_all_campaign_performance(
        self,
        *,
        date_preset: str | None = "last_7d",
        day: date | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        period = day.isoformat() if day else date_preset
        self.log.phase(f"All campaign performance — {period}")

        rows = self.client.get_all_campaign_insights(
            date_preset=date_preset, day=day, limit=limit
        )
        results: list[dict[str, Any]] = []
        for idx, row in enumerate(rows, start=1):
            metrics = parse_insight_row(
                row,
                entity_id_key="campaign_id",
                entity_name_key="campaign_name",
            )
            name = str(row.get("campaign_name") or "")[:40]
            self.log.counter(
                idx,
                len(rows),
                f"{name} — ${metrics.spend:.2f} spend",
                every=max(1, len(rows) // 10),
            )
            results.append(
                {
                    "campaign_id": row.get("campaign_id"),
                    "campaign_name": row.get("campaign_name"),
                    "metrics": metrics.to_dict(),
                }
            )
        self.log.detail(f"Loaded performance for {len(results)} campaign(s)")
        return results
