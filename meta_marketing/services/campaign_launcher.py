"""Create PawPath AI test campaigns with creatives from Shopify."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign

from meta_marketing.services.creative_generator import (
    AdVariation,
    generate_variations,
    variation_for_carousel,
)
from meta_marketing.services.shopify_catalog import ScoredProduct, rank_products_for_ads
from meta_marketing.utils.config import MetaConfig, load_config
from meta_marketing.utils.logging import ProgressLogger, get_logger
from meta_marketing.utils.pawpath_constants import (
    AI_CAMPAIGN_NAMES,
    CAMPAIGN_DAILY_BUDGET_INR,
    PAWPATH_INSTAGRAM_USER_ID,
    PAWPATH_PAGE_ID,
    PAWPATH_PIXEL_ID,
    US_DOG_TARGETING,
)

CHANGELOG = Path("data/meta_reports/PAWPATH_ADS_CHANGELOG.md")
STATE_FILE = Path("data/meta_reports/pawpath_ai_campaigns.json")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_changelog(section: str) -> None:
    CHANGELOG.parent.mkdir(parents=True, exist_ok=True)
    if not CHANGELOG.exists():
        CHANGELOG.write_text("# PawPath Autonomous Ads CHANGELOG\n\n")
    with CHANGELOG.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {_utcnow()}\n\n{section}\n")


def _upload_image(account: AdAccount, url: str) -> str | None:
    try:
        result = account.create_ad_image(params={"url": url})
        return str(result["hash"])
    except Exception:
        return None


def _campaign_ad_count(campaign_id: str) -> int:
    campaign = Campaign(campaign_id)
    return len(list(campaign.get_ads(fields=["id"], params={"limit": 50})))


def _existing_campaigns_map(account: AdAccount) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in account.get_campaigns(fields=["id", "name"], params={"limit": 200}):
        d = dict(row)
        name = str(d.get("name") or "")
        if name in AI_CAMPAIGN_NAMES:
            mapping[name] = str(d["id"])
    return mapping


def _get_or_create_adset(account: AdAccount, *, campaign_id: str, campaign_name: str) -> str:
    campaign = Campaign(campaign_id)
    adsets = list(campaign.get_ad_sets(fields=["id", "name"], params={"limit": 10}))
    if adsets:
        return str(dict(adsets[0])["id"])
    adset = account.create_ad_set(
        params={
            "name": f"{campaign_name}_US_Purchase",
            "campaign_id": campaign_id,
            "status": AdSet.Status.active,
            "optimization_goal": AdSet.OptimizationGoal.offsite_conversions,
            "billing_event": AdSet.BillingEvent.impressions,
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "promoted_object": {
                "pixel_id": PAWPATH_PIXEL_ID,
                "custom_event_type": "PURCHASE",
            },
            "targeting": US_DOG_TARGETING,
            "attribution_spec": [
                {"event_type": "CLICK_THROUGH", "window_days": 7},
                {"event_type": "VIEW_THROUGH", "window_days": 1},
            ],
        }
    )
    return str(adset["id"])


def _create_single_image_creative(
    account: AdAccount,
    *,
    product: ScoredProduct,
    variation: AdVariation,
    image_url: str,
    image_hash: str | None,
    campaign_slug: str,
) -> str:
    link_data: dict[str, Any] = {
        "link": product.product_url,
        "message": variation.primary_text,
        "name": variation.headline,
        "description": variation.description,
        "call_to_action": {
            "type": variation.cta,
            "value": {"link": product.product_url},
        },
    }
    if image_hash:
        link_data["image_hash"] = image_hash
    else:
        link_data["picture"] = image_url

    object_story: dict[str, Any] = {"page_id": PAWPATH_PAGE_ID, "link_data": link_data}
    if PAWPATH_INSTAGRAM_USER_ID:
        object_story["instagram_user_id"] = PAWPATH_INSTAGRAM_USER_ID

    creative = account.create_ad_creative(
        params={
            "name": f"{campaign_slug}_{variation.angle}_{product.handle[:30]}",
            "object_story_spec": object_story,
            "url_tags": (
                f"utm_source=facebook&utm_medium=paid&utm_campaign={campaign_slug}"
                f"&utm_content={variation.angle}"
            ),
        }
    )
    return str(creative["id"])


def _create_carousel_creative(
    account: AdAccount,
    *,
    product: ScoredProduct,
    image_urls: list[str],
    image_hashes: list[str | None],
    campaign_slug: str,
) -> str:
    variation = variation_for_carousel(product)
    child_attachments = []
    for idx, url in enumerate(image_urls):
        attachment: dict[str, Any] = {
            "link": product.product_url,
            "name": variation.headline,
            "description": f"{product.title[:40]} — slide {idx + 1}",
        }
        h = image_hashes[idx] if idx < len(image_hashes) else None
        if h:
            attachment["image_hash"] = h
        else:
            attachment["picture"] = url
        child_attachments.append(attachment)

    object_story: dict[str, Any] = {
        "page_id": PAWPATH_PAGE_ID,
        "link_data": {
            "link": product.product_url,
            "message": variation.primary_text,
            "child_attachments": child_attachments,
            "call_to_action": {
                "type": "SHOP_NOW",
                "value": {"link": product.product_url},
            },
        },
    }
    if PAWPATH_INSTAGRAM_USER_ID:
        object_story["instagram_user_id"] = PAWPATH_INSTAGRAM_USER_ID

    creative = account.create_ad_creative(
        params={
            "name": f"{campaign_slug}_carousel_{product.handle[:25]}",
            "object_story_spec": object_story,
            "url_tags": (
                f"utm_source=facebook&utm_medium=paid&utm_campaign={campaign_slug}&utm_content=carousel"
            ),
        }
    )
    return str(creative["id"])


def _populate_campaign_ads(
    account: AdAccount,
    *,
    campaign_id: str,
    campaign_name: str,
    product: ScoredProduct,
    log: ProgressLogger,
) -> dict[str, Any]:
    slug = campaign_name.lower().replace(" ", "_")
    adset_id = _get_or_create_adset(account, campaign_id=campaign_id, campaign_name=campaign_name)
    log.detail(f"Ad set {adset_id}")

    image_urls = product.image_urls[:6]
    if not image_urls:
        raise RuntimeError(f"No images for {product.title}")

    image_hashes: list[str | None] = []
    for url in image_urls:
        image_hashes.append(_upload_image(account, url))
        if image_hashes[-1]:
            log.detail("  Image uploaded to Meta library")
        else:
            log.detail("  Using Shopify CDN URL for creative")

    ads_created: list[dict[str, str]] = []
    variations = generate_variations(product)[:4]

    for idx, variation in enumerate(variations, start=1):
        url = image_urls[min(idx - 1, len(image_urls) - 1)]
        h = image_hashes[min(idx - 1, len(image_hashes) - 1)]
        creative_id = _create_single_image_creative(
            account,
            product=product,
            variation=variation,
            image_url=url,
            image_hash=h,
            campaign_slug=slug,
        )
        ad = account.create_ad(
            params={
                "name": f"{campaign_name}_Ad_{variation.angle}",
                "adset_id": adset_id,
                "creative": {"creative_id": creative_id},
                "status": Ad.Status.active,
            }
        )
        ads_created.append(
            {
                "ad_id": str(ad["id"]),
                "creative_id": creative_id,
                "angle": variation.angle,
                "type": "single_image",
            }
        )
        log.detail(f"  Ad {variation.angle} → {ad['id']}")

    if len(image_urls) >= 3:
        carousel_urls = image_urls[: min(5, len(image_urls))]
        carousel_hashes = image_hashes[: len(carousel_urls)]
        creative_id = _create_carousel_creative(
            account,
            product=product,
            image_urls=carousel_urls,
            image_hashes=carousel_hashes,
            campaign_slug=slug,
        )
        ad = account.create_ad(
            params={
                "name": f"{campaign_name}_Ad_carousel",
                "adset_id": adset_id,
                "creative": {"creative_id": creative_id},
                "status": Ad.Status.active,
            }
        )
        ads_created.append(
            {
                "ad_id": str(ad["id"]),
                "creative_id": creative_id,
                "angle": "carousel_lifestyle",
                "type": "carousel",
            }
        )
        log.detail(f"  Carousel ad → {ad['id']}")

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "adset_id": adset_id,
        "product": product.to_dict(),
        "ads": ads_created,
        "daily_budget_inr": CAMPAIGN_DAILY_BUDGET_INR,
        "created_at": _utcnow(),
    }


def _create_campaign_bundle(
    account: AdAccount,
    *,
    campaign_name: str,
    product: ScoredProduct,
    log: ProgressLogger,
) -> dict[str, Any]:
    log.phase(f"Creating {campaign_name} → {product.title[:45]}")
    campaign = account.create_campaign(
        params={
            "name": campaign_name,
            "objective": Campaign.Objective.outcome_sales,
            "status": Campaign.Status.active,
            "special_ad_categories": [],
            "daily_budget": CAMPAIGN_DAILY_BUDGET_INR,
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        }
    )
    campaign_id = str(campaign["id"])
    log.detail(f"Campaign {campaign_id} — ₹{CAMPAIGN_DAILY_BUDGET_INR / 100:.0f}/day CBO")
    return _populate_campaign_ads(
        account, campaign_id=campaign_id, campaign_name=campaign_name, product=product, log=log
    )


def launch_ai_test_campaigns(config: MetaConfig | None = None) -> dict[str, Any]:
    log = get_logger()
    config = config or load_config()
    FacebookAdsApi.init(config.app_id, config.app_secret, config.access_token)
    account = AdAccount(config.normalized_ad_account_id)

    log.phase("PawPath AI Test Campaign Launch")
    top_products = rank_products_for_ads(top_n=3)
    existing = _existing_campaigns_map(account)

    bundles: list[dict[str, Any]] = []
    completed_existing: list[str] = []
    skipped: list[str] = []

    for campaign_name, product in zip(AI_CAMPAIGN_NAMES, top_products):
        if campaign_name in existing:
            cid = existing[campaign_name]
            if _campaign_ad_count(cid) > 0:
                log.warn(f"{campaign_name} already has ads — skipping")
                skipped.append(campaign_name)
                continue
            log.info(f"Completing partial campaign {campaign_name} ({cid})")
            bundle = _populate_campaign_ads(
                account,
                campaign_id=cid,
                campaign_name=campaign_name,
                product=product,
                log=log,
            )
            bundles.append(bundle)
            completed_existing.append(campaign_name)
            continue

        bundle = _create_campaign_bundle(
            account, campaign_name=campaign_name, product=product, log=log
        )
        bundles.append(bundle)

    result = {
        "launched_at": _utcnow(),
        "products_selected": [p.to_dict() for p in top_products],
        "campaigns_created": bundles,
        "completed_existing": completed_existing,
        "skipped_existing": skipped,
    }

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"campaigns": []}
    state["campaigns"].extend(bundles)
    state["last_launch"] = result["launched_at"]
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))

    changelog_body = "### Phase 1–2 Launch\n\n**Products selected:**\n"
    for i, p in enumerate(top_products, 1):
        changelog_body += f"- Test {i}: {p.title} (${p.price:.2f}) — score {p.score:.0f}\n"
    changelog_body += "\n**Campaigns:**\n"
    for b in bundles:
        changelog_body += (
            f"- `{b['campaign_name']}` — {len(b['ads'])} ads, "
            f"₹{b['daily_budget_inr']/100:.0f}/day → {b['product']['product_url']}\n"
        )
    if completed_existing:
        changelog_body += f"\n**Completed partial:** {', '.join(completed_existing)}\n"
    if skipped:
        changelog_body += f"\n**Skipped:** {', '.join(skipped)}\n"
    changelog_body += "\n**Next:** `python -m meta_marketing optimize-ai` after 24–48h.\n"
    _append_changelog(changelog_body)

    log.phase(f"Launch complete — {len(bundles)} campaign(s) ready")
    return result
