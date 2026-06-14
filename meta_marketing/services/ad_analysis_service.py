"""Ad-level performance analysis and recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from meta_marketing.api.meta_client import MetaMarketingClient
from meta_marketing.utils.logging import get_logger
from meta_marketing.utils.metrics import MetricSnapshot, parse_insight_row


@dataclass
class AdPerformance:
    ad_id: str
    ad_name: str
    campaign_id: str | None
    campaign_name: str | None
    metrics: MetricSnapshot
    score: float
    classification: str
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ad_id": self.ad_id,
            "ad_name": self.ad_name,
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "metrics": self.metrics.to_dict(),
            "score": round(self.score, 2),
            "classification": self.classification,
            "reasons": self.reasons,
        }


class AdAnalysisService:
    MIN_SPEND_FOR_EVALUATION = 5.0
    MIN_IMPRESSIONS_FOR_EVALUATION = 500

    def __init__(self, client: MetaMarketingClient) -> None:
        self.client = client
        self.log = get_logger()

    def analyze_ads(
        self,
        *,
        date_preset: str | None = "last_7d",
        day: date | None = None,
        limit: int = 250,
    ) -> dict[str, Any]:
        period = day.isoformat() if day else date_preset
        self.log.phase(f"Ad analysis — {period}")

        self.log.detail("Fetching ad-level insights...")
        rows = self.client.get_ad_insights(date_preset=date_preset, day=day, limit=limit)
        self.log.detail("Fetching account benchmarks...")
        account_rows = self.client.get_account_insights(date_preset=date_preset, day=day)
        account_metrics = (
            parse_insight_row(account_rows[0]) if account_rows else MetricSnapshot()
        )

        evaluated: list[AdPerformance] = []
        total = len(rows)
        self.log.detail(f"Scoring {total} ad(s) against account benchmarks...")
        for idx, row in enumerate(rows, start=1):
            metrics = parse_insight_row(
                row,
                entity_id_key="ad_id",
                entity_name_key="ad_name",
            )
            score, classification, reasons = self._score_ad(metrics, account_metrics)
            if classification in ("winner", "loser"):
                self.log.counter(
                    idx,
                    total,
                    f"{classification.upper()}: {(row.get('ad_name') or '')[:35]}",
                    every=max(1, total // 15),
                )
            evaluated.append(
                AdPerformance(
                    ad_id=str(row.get("ad_id") or ""),
                    ad_name=str(row.get("ad_name") or ""),
                    campaign_id=str(row.get("campaign_id") or "") or None,
                    campaign_name=str(row.get("campaign_name") or "") or None,
                    metrics=metrics,
                    score=score,
                    classification=classification,
                    reasons=reasons,
                )
            )

        winners = sorted(
            [ad for ad in evaluated if ad.classification == "winner"],
            key=lambda ad: ad.score,
            reverse=True,
        )
        losers = sorted(
            [ad for ad in evaluated if ad.classification == "loser"],
            key=lambda ad: ad.score,
        )
        neutral = [ad for ad in evaluated if ad.classification == "neutral"]
        recommendations = self._build_recommendations(winners, losers, account_metrics)

        self.log.detail(
            f"Results — {len(winners)} winner(s), {len(losers)} loser(s), {len(neutral)} neutral"
        )
        for rec in recommendations[:3]:
            self.log.detail(f"Recommendation: {rec}")

        return {
            "period": day.isoformat() if day else date_preset,
            "account_benchmarks": account_metrics.to_dict(),
            "summary": {
                "total_ads": len(evaluated),
                "winners": len(winners),
                "losers": len(losers),
                "neutral": len(neutral),
            },
            "winning_ads": [ad.to_dict() for ad in winners[:10]],
            "losing_ads": [ad.to_dict() for ad in losers[:10]],
            "recommendations": recommendations,
        }

    def _score_ad(
        self,
        metrics: MetricSnapshot,
        account: MetricSnapshot,
    ) -> tuple[float, str, list[str]]:
        reasons: list[str] = []
        if metrics.spend < self.MIN_SPEND_FOR_EVALUATION:
            return 0.0, "neutral", ["Insufficient spend for reliable evaluation"]
        if metrics.impressions < self.MIN_IMPRESSIONS_FOR_EVALUATION:
            return 0.0, "neutral", ["Insufficient impressions for reliable evaluation"]

        score = 0.0
        account_ctr = account.ctr or 0.0
        account_cpc = account.cpc or 0.0
        account_roas = account.roas or 0.0

        if account_ctr > 0:
            ctr_ratio = metrics.ctr / account_ctr
            score += (ctr_ratio - 1.0) * 30
            if ctr_ratio >= 1.2:
                reasons.append(
                    f"CTR {metrics.ctr:.2f}% beats account average ({account_ctr:.2f}%)"
                )
            elif ctr_ratio <= 0.8:
                reasons.append(
                    f"CTR {metrics.ctr:.2f}% trails account average ({account_ctr:.2f}%)"
                )

        if account_cpc > 0 and metrics.cpc > 0:
            cpc_ratio = account_cpc / metrics.cpc
            score += (cpc_ratio - 1.0) * 25
            if metrics.cpc <= account_cpc * 0.85:
                reasons.append(
                    f"CPC ${metrics.cpc:.2f} is below account average (${account_cpc:.2f})"
                )
            elif metrics.cpc >= account_cpc * 1.15:
                reasons.append(
                    f"CPC ${metrics.cpc:.2f} is above account average (${account_cpc:.2f})"
                )

        if metrics.purchases > 0:
            score += 20
            reasons.append(f"{metrics.purchases} purchase(s) recorded")
        if account_roas > 0 and metrics.roas > 0:
            roas_ratio = metrics.roas / account_roas
            score += (roas_ratio - 1.0) * 35
            if roas_ratio >= 1.1:
                reasons.append(
                    f"ROAS {metrics.roas:.2f}x beats account average ({account_roas:.2f}x)"
                )
            elif roas_ratio <= 0.9:
                reasons.append(
                    f"ROAS {metrics.roas:.2f}x trails account average ({account_roas:.2f}x)"
                )
        elif metrics.spend > 20 and metrics.purchases == 0:
            score -= 25
            reasons.append("Spend without purchases")

        if score >= 15:
            return score, "winner", reasons
        if score <= -10:
            return score, "loser", reasons
        return score, "neutral", reasons or ["Performance near account average"]

    def _build_recommendations(
        self,
        winners: list[AdPerformance],
        losers: list[AdPerformance],
        account: MetricSnapshot,
    ) -> list[str]:
        recommendations: list[str] = []

        if winners:
            top = winners[0]
            recommendations.append(
                f"Scale budget toward top performer '{top.ad_name}' "
                f"(score {top.score:.1f}, ROAS {top.metrics.roas:.2f}x)."
            )
        if losers:
            worst = losers[0]
            recommendations.append(
                f"Pause or refresh creative for '{worst.ad_name}' "
                f"(score {worst.score:.1f}, spend ${worst.metrics.spend:.2f})."
            )
        if account.roas > 0 and account.roas < 1.0:
            recommendations.append(
                "Account ROAS is below 1.0x — review targeting, landing page, and offer."
            )
        elif account.roas >= 2.0:
            recommendations.append(
                "Strong account ROAS — consider increasing daily budgets on winning campaigns."
            )
        if account.ctr > 0 and account.ctr < 1.0:
            recommendations.append(
                "CTR is under 1% — test new hooks, thumbnails, and primary text variants."
            )
        if not recommendations:
            recommendations.append(
                "Collect more data before making major budget shifts (aim for 7+ days of spend)."
            )
        return recommendations
