"""Autonomous optimization for PawPath AI test campaigns."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign

from meta_marketing.api.meta_client import MetaMarketingClient
from meta_marketing.services.campaign_launcher import CHANGELOG, _append_changelog
from meta_marketing.utils.config import MetaConfig, load_config
from meta_marketing.utils.logging import get_logger
from meta_marketing.utils.metrics import PURCHASE_ACTION_TYPES, extract_action_count, parse_insight_row
from meta_marketing.utils.pawpath_constants import AI_CAMPAIGN_NAMES, CAMPAIGN_DAILY_BUDGET_INR

STATE_FILE = Path("data/meta_reports/pawpath_ai_campaigns.json")

FUNNEL_ACTIONS = {
    "add_to_cart": frozenset(
        {"add_to_cart", "offsite_conversion.fb_pixel_add_to_cart", "onsite_web_add_to_cart"}
    ),
    "initiate_checkout": frozenset(
        {
            "initiate_checkout",
            "offsite_conversion.fb_pixel_initiate_checkout",
            "onsite_web_initiate_checkout",
        }
    ),
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"campaigns": []}


def _ad_insights(ad_id: str, *, preset: str = "last_7d") -> dict[str, Any]:
    ad = Ad(ad_id)
    rows = [
        dict(r)
        for r in ad.get_insights(
            fields=[
                "spend",
                "impressions",
                "clicks",
                "ctr",
                "cpc",
                "cpm",
                "actions",
                "action_values",
                "purchase_roas",
            ],
            params={"date_preset": preset},
        )
    ]
    if not rows:
        return parse_insight_row({}).to_dict()
    row = rows[0]
    metrics = parse_insight_row(row).to_dict()
    metrics["add_to_cart"] = extract_action_count(row.get("actions"), FUNNEL_ACTIONS["add_to_cart"])
    metrics["initiate_checkout"] = extract_action_count(
        row.get("actions"), FUNNEL_ACTIONS["initiate_checkout"]
    )
    return metrics


def _rank_ads(ads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for ad in ads:
        metrics = ad["metrics"]
        score = 0.0
        if metrics.get("purchases", 0) > 0:
            score += metrics["purchases"] * 100
            if metrics.get("spend", 0) > 0:
                score += (metrics.get("purchase_value", 0) / metrics["spend"]) * 50
        score += metrics.get("initiate_checkout", 0) * 15
        score += metrics.get("add_to_cart", 0) * 8
        score += metrics.get("ctr", 0) * 2
        if metrics.get("spend", 0) > 20 and metrics.get("purchases", 0) == 0:
            score -= min(metrics["spend"] / 5, 40)
        ranked.append({**ad, "optimizer_score": round(score, 2)})
    ranked.sort(key=lambda x: x["optimizer_score"], reverse=True)
    return ranked


def optimize_ai_campaigns(
    config: MetaConfig | None = None,
    *,
    date_preset: str = "last_7d",
    min_spend_to_pause: float = 25.0,
) -> dict[str, Any]:
    log = get_logger()
    config = config or load_config()
    client = MetaMarketingClient(config)
    state = _load_state()

    log.phase("Phase 4 — Autonomous optimization")
    actions: list[dict[str, Any]] = []
    campaign_reports: list[dict[str, Any]] = []

    # Discover AI campaigns from account if state empty
    campaign_ids = {name: None for name in AI_CAMPAIGN_NAMES}
    from facebook_business.adobjects.adaccount import AdAccount

    account = AdAccount(config.normalized_ad_account_id)
    for row in account.get_campaigns(fields=["id", "name", "status", "daily_budget"], params={"limit": 200}):
        d = dict(row)
        if d.get("name") in campaign_ids:
            campaign_ids[d["name"]] = d["id"]

    for campaign_name, campaign_id in campaign_ids.items():
        if not campaign_id:
            log.warn(f"{campaign_name} not found — run launch first")
            continue

        log.info(f"Optimizing {campaign_name} ({campaign_id})")
        campaign_metrics = parse_insight_row(
            client.get_campaign_insights(campaign_id, date_preset=date_preset)[0]
            if client.get_campaign_insights(campaign_id, date_preset=date_preset)
            else {}
        ).to_dict()

        campaign = Campaign(campaign_id)
        ads = campaign.get_ads(fields=["id", "name", "status", "effective_status"])
        ad_results: list[dict[str, Any]] = []
        for ad_row in ads:
            ad_d = dict(ad_row)
            ad_id = ad_d["id"]
            metrics = _ad_insights(ad_id, preset=date_preset)
            ad_results.append({"ad_id": ad_id, "name": ad_d.get("name"), "metrics": metrics})

        ranked = _rank_ads(ad_results)
        winners = [a for a in ranked if a["optimizer_score"] > 10]
        losers = [
            a
            for a in ranked
            if a["metrics"].get("spend", 0) >= min_spend_to_pause
            and a["metrics"].get("purchases", 0) == 0
            and a["optimizer_score"] < 0
        ]

        for loser in losers:
            if loser.get("status") == "PAUSED":
                continue
            Ad(loser["ad_id"]).api_update(params={"status": Ad.Status.paused})
            action = {
                "action": "pause_ad",
                "ad_id": loser["ad_id"],
                "ad_name": loser["name"],
                "reason": f"Spend ${loser['metrics']['spend']:.2f} with 0 purchases, score {loser['optimizer_score']}",
            }
            actions.append(action)
            log.detail(f"Paused {loser['name']}")

        if winners and losers:
            top = winners[0]
            action = {
                "action": "scale_signal",
                "campaign_id": campaign_id,
                "top_ad": top["name"],
                "reason": f"Top performer score {top['optimizer_score']} — consider budget increase if ROAS holds",
            }
            actions.append(action)

        campaign_reports.append(
            {
                "campaign_name": campaign_name,
                "campaign_id": campaign_id,
                "campaign_metrics": campaign_metrics,
                "ads_ranked": ranked,
                "winners": len(winners),
                "losers_paused": len(losers),
            }
        )

    # Budget reallocation: boost best campaign if clear winner across tests
    if len(campaign_reports) >= 2:
        best = max(
            campaign_reports,
            key=lambda c: c["campaign_metrics"].get("roas", 0) * 100
            + c["campaign_metrics"].get("purchases", 0) * 50
            - c["campaign_metrics"].get("cpc", 0),
        )
        best_roas = best["campaign_metrics"].get("roas", 0)
        best_purchases = best["campaign_metrics"].get("purchases", 0)
        if best_purchases > 0 or best_roas > 1.0:
            new_budget = int(CAMPAIGN_DAILY_BUDGET_INR * 1.5)
            Campaign(best["campaign_id"]).api_update(params={"daily_budget": new_budget})
            actions.append(
                {
                    "action": "scale_campaign_budget",
                    "campaign_id": best["campaign_id"],
                    "campaign_name": best["campaign_name"],
                    "new_budget_inr": new_budget,
                    "reason": f"Leading campaign — purchases {best_purchases}, ROAS {best_roas:.2f}x",
                }
            )
            log.detail(f"Scaled {best['campaign_name']} budget → ₹{new_budget/100:.0f}/day")

    result = {
        "optimized_at": _utcnow(),
        "date_preset": date_preset,
        "campaigns": campaign_reports,
        "actions": actions,
    }

    changelog = "### Phase 4 Optimization\n\n"
    for report in campaign_reports:
        m = report["campaign_metrics"]
        changelog += f"**{report['campaign_name']}** — spend ${m.get('spend',0):.2f}, "
        changelog += f"purchases {m.get('purchases',0)}, ROAS {m.get('roas',0):.2f}x\n"
    if actions:
        changelog += "\n**Actions:**\n"
        for a in actions:
            changelog += f"- {a['action']}: {a.get('reason', a.get('ad_name', ''))}\n"
    else:
        changelog += "\nNo automated actions — insufficient data or all ads within tolerance.\n"
    changelog += "\n**Next:** Continue monitoring; pause ads above $25 spend with 0 purchases.\n"
    _append_changelog(changelog)

    state["last_optimization"] = result
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))

    log.phase(f"Optimization complete — {len(actions)} action(s)")
    return result
