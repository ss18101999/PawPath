"""Facebook Business SDK wrapper for PawPath Meta Marketing."""

from __future__ import annotations

from datetime import date
from typing import Any

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.api import FacebookAdsApi

from meta_marketing.utils.config import MetaConfig
from meta_marketing.utils.dates import date_range_for_day
from meta_marketing.utils.logging import ProgressLogger, get_logger

INSIGHT_FIELDS = [
    "spend",
    "impressions",
    "clicks",
    "ctr",
    "cpc",
    "cpm",
    "actions",
    "action_values",
    "purchase_roas",
]

CAMPAIGN_INSIGHT_FIELDS = INSIGHT_FIELDS + ["campaign_id", "campaign_name"]
ADSET_INSIGHT_FIELDS = INSIGHT_FIELDS + [
    "adset_id",
    "adset_name",
    "campaign_id",
    "campaign_name",
]
AD_INSIGHT_FIELDS = INSIGHT_FIELDS + [
    "ad_id",
    "ad_name",
    "adset_id",
    "adset_name",
    "campaign_id",
    "campaign_name",
]


class MetaMarketingClient:
    """Thin wrapper around the Facebook Business SDK."""

    def __init__(self, config: MetaConfig, *, log: ProgressLogger | None = None) -> None:
        self.config = config
        self.log = log or get_logger()
        self.log.detail(f"Initializing Meta API for {config.normalized_ad_account_id}")
        with self.log.span("Meta API authentication"):
            FacebookAdsApi.init(
                config.app_id,
                config.app_secret,
                config.access_token,
            )
            self._account = AdAccount(config.normalized_ad_account_id)

    @property
    def ad_account(self) -> AdAccount:
        return self._account

    def _period_label(self, *, date_preset: str | None, day: date | None) -> str:
        if day is not None:
            return day.isoformat()
        return date_preset or "yesterday"

    def get_account_insights(
        self,
        *,
        date_preset: str | None = None,
        day: date | None = None,
    ) -> list[dict[str, Any]]:
        period = self._period_label(date_preset=date_preset, day=day)
        params: dict[str, Any] = {"level": "account"}
        if day is not None:
            params["time_range"] = date_range_for_day(day)
        elif date_preset:
            params["date_preset"] = date_preset
        else:
            params["date_preset"] = "yesterday"

        with self.log.span(f"Fetch account insights ({period})"):
            cursor = self._account.get_insights(fields=INSIGHT_FIELDS, params=params)
            rows = [dict(row) for row in cursor]
        self.log.detail(f"Account insights: {len(rows)} row(s)")
        return rows

    def list_campaigns(
        self,
        *,
        limit: int = 500,
        effective_status: str | None = None,
    ) -> list[dict[str, Any]]:
        fields = [
            "id",
            "name",
            "status",
            "effective_status",
            "objective",
            "daily_budget",
            "lifetime_budget",
            "created_time",
            "updated_time",
        ]
        params: dict[str, Any] = {"limit": limit}
        if effective_status:
            params["effective_status"] = [effective_status]
        label = f"List campaigns (limit={limit}"
        if effective_status:
            label += f", status={effective_status}"
        label += ")"
        with self.log.span(label):
            cursor = self._account.get_campaigns(fields=fields, params=params)
            rows = [dict(row) for row in cursor]
        self.log.detail(f"Campaigns returned: {len(rows)}")
        return rows

    def list_active_campaigns(self, *, limit: int = 500) -> list[dict[str, Any]]:
        return self.list_campaigns(limit=limit, effective_status="ACTIVE")

    def list_ad_sets(
        self,
        *,
        limit: int = 500,
        effective_status: str | None = None,
    ) -> list[dict[str, Any]]:
        fields = [
            "id",
            "name",
            "status",
            "effective_status",
            "campaign_id",
            "daily_budget",
            "lifetime_budget",
            "optimization_goal",
            "created_time",
            "updated_time",
        ]
        params: dict[str, Any] = {"limit": limit}
        if effective_status:
            params["effective_status"] = [effective_status]
        label = f"List ad sets (limit={limit}"
        if effective_status:
            label += f", status={effective_status}"
        label += ")"
        with self.log.span(label):
            cursor = self._account.get_ad_sets(fields=fields, params=params)
            rows = [dict(row) for row in cursor]
        self.log.detail(f"Ad sets returned: {len(rows)}")
        return rows

    def list_active_ad_sets(self, *, limit: int = 500) -> list[dict[str, Any]]:
        return self.list_ad_sets(limit=limit, effective_status="ACTIVE")

    def list_ads(
        self,
        *,
        limit: int = 500,
        effective_status: str | None = None,
    ) -> list[dict[str, Any]]:
        fields = [
            "id",
            "name",
            "status",
            "effective_status",
            "campaign_id",
            "adset_id",
            "created_time",
            "updated_time",
        ]
        params: dict[str, Any] = {"limit": limit}
        if effective_status:
            params["effective_status"] = [effective_status]
        label = f"List ads (limit={limit}"
        if effective_status:
            label += f", status={effective_status}"
        label += ")"
        with self.log.span(label):
            cursor = self._account.get_ads(fields=fields, params=params)
            rows = [dict(row) for row in cursor]
        self.log.detail(f"Ads returned: {len(rows)}")
        return rows

    def list_active_ads(self, *, limit: int = 500) -> list[dict[str, Any]]:
        return self.list_ads(limit=limit, effective_status="ACTIVE")

    def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        with self.log.span(f"Get campaign {campaign_id}"):
            campaign = Campaign(campaign_id)
            campaign.api_get(
                fields=[
                    "id",
                    "name",
                    "status",
                    "effective_status",
                    "objective",
                    "daily_budget",
                    "lifetime_budget",
                ]
            )
            return dict(campaign)

    def set_campaign_status(self, campaign_id: str, *, status: str) -> dict[str, Any]:
        with self.log.span(f"Set campaign {campaign_id} → {status}"):
            campaign = Campaign(campaign_id)
            campaign.api_update(params={"status": status})
            campaign.api_get(fields=["id", "name", "status", "effective_status"])
            return dict(campaign)

    def get_campaign_insights(
        self,
        campaign_id: str,
        *,
        date_preset: str | None = None,
        day: date | None = None,
    ) -> list[dict[str, Any]]:
        period = self._period_label(date_preset=date_preset, day=day)
        campaign = Campaign(campaign_id)
        params: dict[str, Any] = {"level": "campaign"}
        if day is not None:
            params["time_range"] = date_range_for_day(day)
        elif date_preset:
            params["date_preset"] = date_preset
        else:
            params["date_preset"] = "last_7d"

        with self.log.span(f"Campaign {campaign_id} insights ({period})"):
            cursor = campaign.get_insights(fields=CAMPAIGN_INSIGHT_FIELDS, params=params)
            rows = [dict(row) for row in cursor]
        self.log.detail(f"Campaign insights: {len(rows)} row(s)")
        return rows

    def get_all_campaign_insights(
        self,
        *,
        date_preset: str | None = None,
        day: date | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        period = self._period_label(date_preset=date_preset, day=day)
        params: dict[str, Any] = {"level": "campaign", "limit": limit}
        if day is not None:
            params["time_range"] = date_range_for_day(day)
        elif date_preset:
            params["date_preset"] = date_preset
        else:
            params["date_preset"] = "last_7d"

        with self.log.span(f"All campaign insights ({period}, limit={limit})"):
            cursor = self._account.get_insights(fields=CAMPAIGN_INSIGHT_FIELDS, params=params)
            rows = [dict(row) for row in cursor]
        self.log.detail(f"Campaign insight rows: {len(rows)}")
        return rows

    def get_all_adset_insights(
        self,
        *,
        date_preset: str | None = None,
        day: date | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        period = self._period_label(date_preset=date_preset, day=day)
        params: dict[str, Any] = {"level": "adset", "limit": limit}
        if day is not None:
            params["time_range"] = date_range_for_day(day)
        elif date_preset:
            params["date_preset"] = date_preset
        else:
            params["date_preset"] = "last_7d"

        with self.log.span(f"All ad set insights ({period}, limit={limit})"):
            cursor = self._account.get_insights(fields=ADSET_INSIGHT_FIELDS, params=params)
            rows = [dict(row) for row in cursor]
        self.log.detail(f"Ad set insight rows: {len(rows)}")
        return rows

    def get_ad_insights(
        self,
        *,
        date_preset: str | None = None,
        day: date | None = None,
        limit: int = 250,
    ) -> list[dict[str, Any]]:
        period = self._period_label(date_preset=date_preset, day=day)
        params: dict[str, Any] = {"level": "ad", "limit": limit}
        if day is not None:
            params["time_range"] = date_range_for_day(day)
        elif date_preset:
            params["date_preset"] = date_preset
        else:
            params["date_preset"] = "last_7d"

        with self.log.span(f"Ad-level insights ({period}, limit={limit})"):
            cursor = self._account.get_insights(fields=AD_INSIGHT_FIELDS, params=params)
            rows = [dict(row) for row in cursor]
        self.log.detail(f"Ad insight rows: {len(rows)}")
        return rows

    def get_ad(self, ad_id: str) -> dict[str, Any]:
        with self.log.span(f"Get ad {ad_id}"):
            ad = Ad(ad_id)
            ad.api_get(fields=["id", "name", "status", "effective_status", "campaign_id"])
            return dict(ad)
