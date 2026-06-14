"""Full account audit — campaigns, ad sets, ads, and ranked performance."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from meta_marketing.api.meta_client import MetaMarketingClient
from meta_marketing.reports.exporters import export_csv, export_json
from meta_marketing.services.ad_analysis_service import AdAnalysisService
from meta_marketing.utils.logging import get_logger
from meta_marketing.utils.metrics import MetricSnapshot, parse_insight_row


def _entity_row(
    row: dict[str, Any],
    *,
    id_key: str,
    name_key: str,
) -> dict[str, Any]:
    metrics = parse_insight_row(row, entity_id_key=id_key, entity_name_key=name_key)
    return {
        "id": row.get(id_key),
        "name": row.get(name_key),
        "metrics": metrics.to_dict(),
    }


def _rank_score(metrics: MetricSnapshot) -> float:
    """Higher is better. Used to sort ads best → worst."""
    if metrics.spend <= 0 and metrics.impressions <= 0:
        return -999.0
    score = 0.0
    if metrics.roas > 0:
        score += metrics.roas * 40
    elif metrics.purchases > 0 and metrics.spend > 0:
        score += (metrics.purchase_value / metrics.spend) * 40
    score += metrics.ctr * 5
    if metrics.cpc > 0:
        score += min(20.0, 5.0 / metrics.cpc)
    score += min(metrics.purchases * 10, 50)
    if metrics.spend > 0 and metrics.purchases == 0:
        score -= min(metrics.spend / 10, 30)
    return round(score, 2)


class AccountAuditService:
    def __init__(self, client: MetaMarketingClient) -> None:
        self.client = client
        self.log = get_logger()
        self.ad_analysis = AdAnalysisService(client)

    def run(
        self,
        *,
        date_preset: str | None = "last_30d",
        day: date | None = None,
    ) -> dict[str, Any]:
        period = day.isoformat() if day else date_preset
        self.log.phase(f"Account audit — {period}")

        self.log.info("Fetching active campaigns...")
        campaigns = self.client.list_active_campaigns()
        self.log.detail(f"Active campaigns: {len(campaigns)}")

        self.log.info("Fetching active ad sets...")
        ad_sets = self.client.list_active_ad_sets()
        self.log.detail(f"Active ad sets: {len(ad_sets)}")

        self.log.info("Fetching active ads...")
        ads = self.client.list_active_ads()
        self.log.detail(f"Active ads: {len(ads)}")

        self.log.info("Fetching account insights...")
        account_rows = self.client.get_account_insights(date_preset=date_preset, day=day)
        account_metrics = (
            parse_insight_row(account_rows[0]) if account_rows else MetricSnapshot()
        )
        self._log_metrics("Account", account_metrics)

        self.log.info("Fetching campaign performance...")
        campaign_insights = self.client.get_all_campaign_insights(
            date_preset=date_preset, day=day, limit=500
        )
        active_campaign_ids = {str(c["id"]) for c in campaigns}
        campaign_performance = [
            _entity_row(row, id_key="campaign_id", name_key="campaign_name")
            for row in campaign_insights
            if str(row.get("campaign_id") or "") in active_campaign_ids
            or not active_campaign_ids
        ]
        if not campaign_performance and campaign_insights:
            campaign_performance = [
                _entity_row(row, id_key="campaign_id", name_key="campaign_name")
                for row in campaign_insights
            ]

        self.log.info("Fetching ad set performance...")
        adset_insights = self.client.get_all_adset_insights(
            date_preset=date_preset, day=day, limit=500
        )
        active_adset_ids = {str(a["id"]) for a in ad_sets}
        adset_performance = [
            _entity_row(row, id_key="adset_id", name_key="adset_name")
            for row in adset_insights
            if str(row.get("adset_id") or "") in active_adset_ids
            or not active_adset_ids
        ]
        if not adset_performance and adset_insights:
            adset_performance = [
                _entity_row(row, id_key="adset_id", name_key="adset_name")
                for row in adset_insights
            ]

        self.log.info("Fetching ad performance & building rankings...")
        ad_insights = self.client.get_ad_insights(
            date_preset=date_preset, day=day, limit=500
        )
        active_ad_ids = {str(a["id"]) for a in ads}

        ranked_ads: list[dict[str, Any]] = []
        for row in ad_insights:
            ad_id = str(row.get("ad_id") or "")
            if active_ad_ids and ad_id not in active_ad_ids:
                continue
            metrics = parse_insight_row(
                row,
                entity_id_key="ad_id",
                entity_name_key="ad_name",
            )
            score = _rank_score(metrics)
            ranked_ads.append(
                {
                    "rank": 0,
                    "ad_id": row.get("ad_id"),
                    "ad_name": row.get("ad_name"),
                    "adset_id": row.get("adset_id"),
                    "adset_name": row.get("adset_name"),
                    "campaign_id": row.get("campaign_id"),
                    "campaign_name": row.get("campaign_name"),
                    "score": score,
                    "metrics": metrics.to_dict(),
                }
            )

        ranked_ads.sort(key=lambda item: item["score"], reverse=True)
        for idx, item in enumerate(ranked_ads, start=1):
            item["rank"] = idx

        self.log.detail(f"Ranked {len(ranked_ads)} ad(s) with performance data")
        if ranked_ads:
            best = ranked_ads[0]
            worst = ranked_ads[-1]
            self.log.detail(
                f"Best: #{best['rank']} {str(best['ad_name'])[:40]} (score {best['score']})"
            )
            self.log.detail(
                f"Worst: #{worst['rank']} {str(worst['ad_name'])[:40]} (score {worst['score']})"
            )

        ad_analysis = self.ad_analysis.analyze_ads(
            date_preset=date_preset, day=day, limit=500
        )

        return {
            "report_type": "account_audit",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "period": period,
            "ad_account_id": self.client.config.normalized_ad_account_id,
            "summary": {
                "active_campaigns": len(campaigns),
                "active_ad_sets": len(ad_sets),
                "active_ads": len(ads),
                "ads_with_performance": len(ranked_ads),
            },
            "account": {
                "metrics": account_metrics.to_dict(),
            },
            "active_campaigns": [
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "objective": c.get("objective"),
                    "daily_budget": c.get("daily_budget"),
                    "lifetime_budget": c.get("lifetime_budget"),
                }
                for c in campaigns
            ],
            "active_ad_sets": [
                {
                    "id": a.get("id"),
                    "name": a.get("name"),
                    "campaign_id": a.get("campaign_id"),
                    "optimization_goal": a.get("optimization_goal"),
                    "daily_budget": a.get("daily_budget"),
                }
                for a in ad_sets
            ],
            "active_ads": [
                {
                    "id": a.get("id"),
                    "name": a.get("name"),
                    "campaign_id": a.get("campaign_id"),
                    "adset_id": a.get("adset_id"),
                }
                for a in ads
            ],
            "campaign_performance": campaign_performance,
            "adset_performance": adset_performance,
            "ads_ranked": ranked_ads,
            "ad_analysis": ad_analysis,
        }

    def _log_metrics(self, label: str, metrics: MetricSnapshot) -> None:
        self.log.detail(
            f"{label}: spend ${metrics.spend:.2f} | imps {metrics.impressions:,} | "
            f"CTR {metrics.ctr:.2f}% | CPC ${metrics.cpc:.2f} | CPM ${metrics.cpm:.2f} | "
            f"purchases {metrics.purchases} | ROAS {metrics.roas:.2f}x"
        )

    def generate_files(
        self,
        *,
        output_dir: Path,
        date_preset: str | None = "last_30d",
        day: date | None = None,
    ) -> dict[str, Path]:
        payload = self.run(date_preset=date_preset, day=day)
        period = str(payload["period"]).replace(":", "-")
        json_path = output_dir / f"meta_audit_{period}.json"
        csv_path = output_dir / f"meta_audit_{period}.csv"

        self.log.phase("Export audit report")
        paths = {
            "json": export_json(payload, json_path),
            "csv": export_audit_csv(payload, csv_path),
        }
        for kind, path in paths.items():
            self.log.detail(f"Wrote {kind.upper()}: {path}")
        return paths


def export_audit_csv(payload: dict[str, Any], output_path: Path) -> Path:
    log = get_logger()
    log.detail(f"Writing audit CSV → {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import csv

    rows: list[dict[str, Any]] = []
    period = payload.get("period")

    account = payload.get("account", {}).get("metrics", {})
    rows.append(
        {
            "section": "account",
            "period": period,
            "rank": "",
            "entity_id": payload.get("ad_account_id"),
            "entity_name": "Account Total",
            "spend": account.get("spend"),
            "impressions": account.get("impressions"),
            "ctr": account.get("ctr"),
            "cpc": account.get("cpc"),
            "cpm": account.get("cpm"),
            "purchases": account.get("purchases"),
            "roas": account.get("roas"),
            "score": "",
        }
    )

    for item in payload.get("campaign_performance", []):
        m = item.get("metrics", {})
        rows.append(
            {
                "section": "campaign",
                "period": period,
                "rank": "",
                "entity_id": item.get("id"),
                "entity_name": item.get("name"),
                "spend": m.get("spend"),
                "impressions": m.get("impressions"),
                "ctr": m.get("ctr"),
                "cpc": m.get("cpc"),
                "cpm": m.get("cpm"),
                "purchases": m.get("purchases"),
                "roas": m.get("roas"),
                "score": "",
            }
        )

    for item in payload.get("adset_performance", []):
        m = item.get("metrics", {})
        rows.append(
            {
                "section": "adset",
                "period": period,
                "rank": "",
                "entity_id": item.get("id"),
                "entity_name": item.get("name"),
                "spend": m.get("spend"),
                "impressions": m.get("impressions"),
                "ctr": m.get("ctr"),
                "cpc": m.get("cpc"),
                "cpm": m.get("cpm"),
                "purchases": m.get("purchases"),
                "roas": m.get("roas"),
                "score": "",
            }
        )

    for item in payload.get("ads_ranked", []):
        m = item.get("metrics", {})
        rows.append(
            {
                "section": "ad_ranked",
                "period": period,
                "rank": item.get("rank"),
                "entity_id": item.get("ad_id"),
                "entity_name": item.get("ad_name"),
                "campaign_name": item.get("campaign_name"),
                "adset_name": item.get("adset_name"),
                "spend": m.get("spend"),
                "impressions": m.get("impressions"),
                "ctr": m.get("ctr"),
                "cpc": m.get("cpc"),
                "cpm": m.get("cpm"),
                "purchases": m.get("purchases"),
                "roas": m.get("roas"),
                "score": item.get("score"),
            }
        )

    fieldnames = sorted({key for row in rows for key in row})
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path
