"""Fetch and score Shopify products for Meta ad selection."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from supplier.shopify_client import graphql  # noqa: E402

from meta_marketing.utils.logging import get_logger
from meta_marketing.utils.pawpath_constants import PAWPATH_STORE_URL

IMPULSE_KEYWORDS = (
    "portable",
    "travel",
    "water",
    "bottle",
    "cooling",
    "car seat",
    "cover",
    "harness",
    "bowl",
    "leak",
    "collapsible",
    "hiking",
    "road trip",
)
PROBLEM_KEYWORDS = (
    "leak",
    "cool",
    "heat",
    "protect",
    "waterproof",
    "safety",
    "comfort",
    "mess",
    "spill",
    "hydration",
    "waterproof",
)
SEASONAL_BOOST = ("cooling", "cool", "summer", "heat", "water bottle", "vest")


@dataclass
class ScoredProduct:
    shopify_id: str
    title: str
    handle: str
    price: float
    currency: str
    image_urls: list[str]
    inventory: int
    product_type: str
    tags: list[str]
    score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)
    product_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "shopify_id": self.shopify_id,
            "title": self.title,
            "handle": self.handle,
            "price": self.price,
            "currency": self.currency,
            "image_urls": self.image_urls,
            "inventory": self.inventory,
            "product_type": self.product_type,
            "tags": self.tags,
            "score": self.score,
            "score_breakdown": self.score_breakdown,
            "product_url": self.product_url,
        }


def fetch_active_products() -> list[dict[str, Any]]:
    log = get_logger()
    all_nodes: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        data = graphql(
            """query ($after: String) {
              products(first: 50, after: $after, query: "status:active") {
                pageInfo { hasNextPage endCursor }
                nodes {
                  id title handle status productType tags description
                  priceRangeV2 {
                    minVariantPrice { amount currencyCode }
                  }
                  featuredImage { url }
                  images(first: 10) { nodes { url altText } }
                  variants(first: 1) { nodes { id price } }
                  totalInventory
                }
              }
            }""",
            {"after": cursor},
        )
        batch = data["products"]["nodes"]
        all_nodes.extend(batch)
        log.detail(f"Fetched {len(all_nodes)} active product(s)...")
        if not data["products"]["pageInfo"]["hasNextPage"]:
            break
        cursor = data["products"]["pageInfo"]["endCursor"]
    return all_nodes


def _score_product(raw: dict[str, Any]) -> ScoredProduct:
    title = raw.get("title") or ""
    text = (
        title
        + " "
        + (raw.get("description") or "")[:600]
        + " "
        + " ".join(raw.get("tags") or [])
    ).lower()
    price = float(raw["priceRangeV2"]["minVariantPrice"]["amount"])
    currency = raw["priceRangeV2"]["minVariantPrice"]["currencyCode"]
    images = raw.get("images", {}).get("nodes", [])
    image_urls = [img["url"] for img in images if img.get("url")]
    if not image_urls and raw.get("featuredImage", {}).get("url"):
        image_urls = [raw["featuredImage"]["url"]]
    inv = int(raw.get("totalInventory") or 0)

    breakdown: dict[str, float] = {
        "market_demand": sum(3 for k in IMPULSE_KEYWORDS if k in text),
        "ad_potential": min(len(image_urls), 8) * 2 + (3 if 14.95 <= price <= 49.95 else 0),
        "visual_appeal": min(len(image_urls), 6) * 3 + (5 if image_urls else 0),
        "problem_solving": sum(4 for k in PROBLEM_KEYWORDS if k in text),
        "impulse_buy": 10 if 14.95 <= price <= 39.95 else (5 if price <= 49.95 else 0),
        "competitive_position": 5 if re.search(r"pawpath|dog|pet travel", text) else 2,
        "conversion_potential": (8 if inv > 0 else 0) + (5 if price < 45 else 2),
    }
    if any(w in text for w in SEASONAL_BOOST):
        breakdown["market_demand"] += 8

    total = sum(breakdown.values())
    handle = raw.get("handle") or ""
    return ScoredProduct(
        shopify_id=raw["id"],
        title=title,
        handle=handle,
        price=price,
        currency=currency,
        image_urls=image_urls,
        inventory=inv,
        product_type=raw.get("productType") or "",
        tags=list(raw.get("tags") or []),
        score=total,
        score_breakdown=breakdown,
        product_url=f"{PAWPATH_STORE_URL}/products/{handle}",
    )


def rank_products_for_ads(*, top_n: int = 3) -> list[ScoredProduct]:
    log = get_logger()
    log.phase("Phase 1 — Shopify product analysis")
    raw_products = fetch_active_products()
    log.info(f"Analyzing {len(raw_products)} active products")

    scored = [_score_product(p) for p in raw_products]
    scored.sort(key=lambda p: p.score, reverse=True)

    for idx, product in enumerate(scored[:10], start=1):
        log.detail(
            f"#{idx} score={product.score:.0f} ${product.price:.2f} "
            f"{len(product.image_urls)} imgs — {product.title[:50]}"
        )

    top = scored[:top_n]
    log.info(f"Selected top {len(top)} products for campaigns")
    return top
