"""PawPath_FirstAdd campaign optimizer — purchase/ROAS focused."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.targetingsearch import TargetingSearch

from meta_marketing.api.meta_client import MetaMarketingClient
from meta_marketing.utils.config import MetaConfig, load_config
from meta_marketing.utils.logging import get_logger
from meta_marketing.utils.metrics import parse_insight_row

PAWPATH_CAMPAIGN_ID = "120250110463790666"
PAWPATH_ADSET_ID = "120250110463780666"
PAWPATH_AD_ID = "120250110463770666"
PAWPATH_CREATIVE_ID = "1330637318392716"
PAWPATH_PIXEL_ID = "2450255575122418"
PAWPATH_PAGE_ID = "342397042289671"
PRODUCT_URL = (
    "https://pawpathsupply.com/products/"
    "summer-pet-dog-cooling-vest-heat-resistant-cool-dogs-clothes-"
    "breathable-sun-proof-clothing-for-small-large-dogs-outdoor-walking"
    "?variant=47914259611813"
)
LOG_FILE = Path("data/meta_reports/pawpath_firstadd_optimization_log.jsonl")

DOG_INTEREST_NAMES = [
    "Dogs",
    "Dog training",
    "Pet store",
    "Dog walking",
    "Dog food",
    "Dog park",
    "Pet supplies",
]

IMPROVED_BODIES = [
    "Hot pavement? Long summer walks? This cooling vest helps keep your dog comfortable outdoors. "
    "Free US shipping on orders $50+ at PawPath Supply.",
    "Dog parents are switching to lightweight cooling gear for hikes, park days, and road trips. "
    "Shop the PawPath Cooling Vest — built for real adventures with your pup.",
    "Help your dog beat the heat. Breathable cooling vest for small to large dogs. "
    "Trusted by pet owners who travel with their dogs. Shop now.",
]

IMPROVED_TITLES = [
    "Keep Your Dog Cool This Summer",
    "Dog Cooling Vest | PawPath Supply",
    "Free Shipping $50+ | Shop Dog Gear",
    "Beat the Heat on Walks & Road Trips",
    "Comfort for Active Dogs Outdoors",
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_change(entry: dict[str, Any]) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, default=str) + "\n")


def _search_interests(account: AdAccount) -> list[dict[str, str]]:
    log = get_logger()
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for name in DOG_INTEREST_NAMES:
        results = TargetingSearch.search(params={"q": name, "type": "adinterest", "limit": 3})
        for item in results:
            iid = str(item.get("id", ""))
            iname = str(item.get("name", ""))
            if iid and iid not in seen:
                seen.add(iid)
                found.append({"id": iid, "name": iname})
                log.detail(f"Interest: {iname} ({iid})")
    return found[:8]


def _us_dog_targeting(interests: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "geo_locations": {"countries": ["US"]},
        "age_min": 25,
        "age_max": 65,
        "flexible_spec": [{"interests": interests}] if interests else [],
        "targeting_automation": {"advantage_audience": 1},
    }


def _get_metrics(client: MetaMarketingClient, entity_id: str, level: str) -> dict[str, Any]:
    if level == "campaign":
        rows = client.get_campaign_insights(entity_id, date_preset="maximum")
    elif level == "adset":
        adset = AdSet(entity_id)
        rows = [
            dict(r)
            for r in adset.get_insights(
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
                params={"date_preset": "maximum"},
            )
        ]
    else:
        ad = Ad(entity_id)
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
                params={"date_preset": "maximum"},
            )
        ]
    if not rows:
        return parse_insight_row({}).to_dict()
    return parse_insight_row(rows[0]).to_dict()


def run_optimization(config: MetaConfig | None = None) -> dict[str, Any]:
    log = get_logger()
    config = config or load_config()
    client = MetaMarketingClient(config)
    account = AdAccount(config.normalized_ad_account_id)

    log.phase("PawPath_FirstAdd optimization cycle")
    changes: list[dict[str, Any]] = []

    before = {
        "campaign": _get_metrics(client, PAWPATH_CAMPAIGN_ID, "campaign"),
        "adset": _get_metrics(client, PAWPATH_ADSET_ID, "adset"),
        "ad": _get_metrics(client, PAWPATH_AD_ID, "ad"),
    }
    log.detail(
        f"Before — ad spend ${before['ad']['spend']:.2f}, "
        f"CTR {before['ad']['ctr']:.2f}%, CPC ${before['ad']['cpc']:.2f}, "
        f"purchases {before['ad']['purchases']}, ROAS {before['ad']['roas']:.2f}x"
    )

    # 1. Fix campaign budget (₹500/day → ₹150/day for controlled purchase testing)
    new_daily_budget_cents = 15000  # ₹150/day (account currency INR)
    campaign = Campaign(PAWPATH_CAMPAIGN_ID)
    campaign.api_update(params={"daily_budget": new_daily_budget_cents})
    changes.append(
        {
            "action": "update_campaign_budget",
            "entity": PAWPATH_CAMPAIGN_ID,
            "from": "₹500/day",
            "to": "₹150/day",
            "reason": "Prior spend ($366) on wrong audience with 0 purchases; reduce risk while retesting with fixed US dog targeting.",
        }
    )
    log.detail("Campaign budget → ₹150/day")

    # 2. Fix ad set targeting (cats + 50 cities → US + dog interests)
    log.info("Searching dog-related interests...")
    interests = _search_interests(account)
    new_targeting = _us_dog_targeting(interests)
    adset = AdSet(PAWPATH_ADSET_ID)
    adset.api_update(params={"targeting": new_targeting})
    changes.append(
        {
            "action": "update_adset_targeting",
            "entity": PAWPATH_ADSET_ID,
            "from": "50+ US cities + cat/kitten interests",
            "to": f"United States + {len(interests)} dog/pet interests, age 25-65, Advantage audience",
            "reason": "Cat interests and hyper-local city targeting caused $45 CPC and $1,508 CPM with only 243 impressions. PawPath sells dog travel gear — US-wide dog owner audience required.",
            "interests": interests,
        }
    )
    log.detail(f"Ad set targeting → US + {len(interests)} dog interests")

    # 3. Create improved creative (purchase-focused copy)
    log.info("Creating purchase-optimized creative variant...")
    creative = account.create_ad_creative(
        params={
            "name": f"PawPath_CoolingVest_Purchase_v2_{datetime.now().strftime('%Y%m%d')}",
            "object_story_spec": {
                "page_id": PAWPATH_PAGE_ID,
                "video_data": {
                    "video_id": "1318582286469483",
                    "image_hash": "6359918b7256814412ac6119c6029e26",
                    "call_to_action": {
                        "type": "SHOP_NOW",
                        "value": {"link": PRODUCT_URL},
                    },
                },
            },
            "asset_feed_spec": {
                "bodies": [{"text": t} for t in IMPROVED_BODIES],
                "titles": [{"text": t} for t in IMPROVED_TITLES],
                "optimization_type": "DEGREES_OF_FREEDOM",
            },
            "url_tags": "utm_source=facebook&utm_medium=paid&utm_campaign=pawpath_firstadd&utm_content=v2_purchase",
        }
    )
    new_creative_id = creative["id"]
    changes.append(
        {
            "action": "create_creative",
            "entity": new_creative_id,
            "reason": "Original creative had empty primary headline slot and generic copy. New variant emphasizes purchase benefits, free shipping, and dog-specific messaging for ROAS optimization.",
        }
    )
    log.detail(f"New creative: {new_creative_id}")

    # 4. Create A/B ad set (duplicate structure, same optimization, fresh learning)
    log.info("Creating A/B ad set for purchase optimization...")
    ab_adset = account.create_ad_set(
        params={
            "name": "PawPath_US_DogOwners_AB",
            "campaign_id": PAWPATH_CAMPAIGN_ID,
            "status": AdSet.Status.active,
            "optimization_goal": AdSet.OptimizationGoal.offsite_conversions,
            "billing_event": AdSet.BillingEvent.impressions,
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "daily_budget": 10000,  # ₹100/day on A/B ad set
            "promoted_object": {
                "pixel_id": PAWPATH_PIXEL_ID,
                "custom_event_type": "PURCHASE",
            },
            "targeting": new_targeting,
            "attribution_spec": [
                {"event_type": "CLICK_THROUGH", "window_days": 7},
                {"event_type": "VIEW_THROUGH", "window_days": 1},
            ],
        }
    )
    ab_adset_id = ab_adset["id"]
    changes.append(
        {
            "action": "create_ab_adset",
            "entity": ab_adset_id,
            "daily_budget": "₹100/day",
            "reason": "A/B ad set isolates new targeting + creative for clean learning phase without legacy delivery history from misconfigured audience.",
        }
    )
    log.detail(f"A/B ad set: {ab_adset_id}")

    # 5. Create ad in A/B ad set with new creative
    ab_ad = account.create_ad(
        params={
            "name": "PawPath_FirstAdd_v2_Purchase",
            "adset_id": ab_adset_id,
            "creative": {"creative_id": new_creative_id},
            "status": Ad.Status.active,
        }
    )
    changes.append(
        {
            "action": "create_ab_ad",
            "entity": ab_ad["id"],
            "reason": "Runs improved creative in A/B ad set optimized for Purchase conversions.",
        }
    )
    log.detail(f"A/B ad: {ab_ad['id']}")

    # 6. Update original ad with improved creative (keep for comparison in original ad set)
    Ad(PAWPATH_AD_ID).api_update(params={"creative": {"creative_id": new_creative_id}})
    changes.append(
        {
            "action": "update_ad_creative",
            "entity": PAWPATH_AD_ID,
            "creative_id": new_creative_id,
            "reason": "Refresh original ad creative with purchase-focused copy while keeping ad set for comparison.",
        }
    )

    # 7. Resume campaign + ads (do not delete anything)
    campaign.api_update(params={"status": Campaign.Status.active})
    AdSet(PAWPATH_ADSET_ID).api_update(params={"status": AdSet.Status.active})
    Ad(PAWPATH_AD_ID).api_update(params={"status": Ad.Status.active})
    changes.append(
        {
            "action": "resume_campaign_structure",
            "entities": [PAWPATH_CAMPAIGN_ID, PAWPATH_ADSET_ID, PAWPATH_AD_ID, ab_adset_id, ab_ad["id"]],
            "reason": "Campaign was paused with 0 recent delivery. Resuming with fixed targeting to begin purchase optimization.",
        }
    )
    log.detail("Campaign, ad sets, and ads resumed")

    cycle = {
        "timestamp": _utcnow(),
        "cycle": "pawpath_firstadd_optimization_1",
        "changes": changes,
        "before_metrics": before,
        "after_config": {
            "campaign_daily_budget": "₹150/day",
            "original_adset_daily_budget": "campaign budget (CBO)",
            "ab_adset_daily_budget": "₹100/day",
            "targeting": "US, age 25-65, dog interests",
            "optimization": "OFFSITE_CONVERSIONS → PURCHASE",
        },
        "next_actions": [
            "Monitor purchase events in Meta Events Manager (pixel 2450255575122418)",
            "After 3-5 days / 50+ conversions: pause worse ad set, scale winner",
            "If CPC stays above $5 with 0 purchases, test static image carousel vs video",
            "Verify Shopify pixel fires Purchase on test checkout",
        ],
    }
    for change in changes:
        _log_change({"timestamp": _utcnow(), **change})

    log.phase("Optimization cycle complete")
    return cycle


if __name__ == "__main__":
    from meta_marketing.utils.logging import configure

    configure(verbose=True)
    result = run_optimization()
    print(json.dumps(result, indent=2, default=str))
