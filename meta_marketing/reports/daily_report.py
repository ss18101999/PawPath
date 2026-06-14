"""Assemble the daily Meta Ads performance report."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from meta_marketing.api.meta_client import MetaMarketingClient
from meta_marketing.reports.exporters import export_csv, export_json
from meta_marketing.services.account_service import AccountService
from meta_marketing.services.ad_analysis_service import AdAnalysisService
from meta_marketing.services.campaign_service import CampaignService
from meta_marketing.utils.dates import yesterday_utc
from meta_marketing.utils.logging import get_logger


class DailyReportGenerator:
    def __init__(self, client: MetaMarketingClient) -> None:
        self.client = client
        self.log = get_logger()
        self.account_service = AccountService(client)
        self.campaign_service = CampaignService(client)
        self.ad_service = AdAnalysisService(client)

    def build(self, *, day: date | None = None) -> dict[str, Any]:
        report_day = day or yesterday_utc()
        self.log.phase(f"Daily report — {report_day.isoformat()}")

        self.log.info("Step 1/3: Account overview")
        account_overview = self.account_service.get_overview(day=report_day)

        self.log.info("Step 2/3: Campaign performance")
        campaigns = self.campaign_service.get_all_campaign_performance(day=report_day)

        self.log.info("Step 3/3: Ad analysis")
        ad_analysis = self.ad_service.analyze_ads(day=report_day)

        self.log.detail("Report assembly complete")
        return {
            "report_type": "daily_performance",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_date": report_day.isoformat(),
            "ad_account_id": self.client.config.normalized_ad_account_id,
            "account_overview": account_overview,
            "campaigns": campaigns,
            "ad_analysis": ad_analysis,
        }

    def generate_files(
        self,
        *,
        output_dir: Path,
        day: date | None = None,
    ) -> dict[str, Path]:
        payload = self.build(day=day)
        report_day = payload["report_date"]
        json_path = output_dir / f"meta_daily_{report_day}.json"
        csv_path = output_dir / f"meta_daily_{report_day}.csv"

        self.log.phase("Export report files")
        paths = {
            "json": export_json(payload, json_path),
            "csv": export_csv(payload, csv_path),
        }
        for kind, path in paths.items():
            self.log.detail(f"Wrote {kind.upper()}: {path}")
        return paths
