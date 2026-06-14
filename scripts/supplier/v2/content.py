"""V2 premium product content generation."""

from __future__ import annotations

import re
from html import escape
from typing import Any

from ..config import BRAND_NAME, BRAND_TAGLINE, COLLECTIONS, SAFETY_FOOTER
from .models import MerchandisedContent, ProductOpportunity

CATEGORY_BENEFITS: dict[str, list[str]] = {
    "travel-gear": [
        "Keeps walks and outings organized with less bulk in your bag.",
        "Built for real-life adventures — parks, trails, and weekend trips.",
        "Easy to pack, use, and clean when you're on the move.",
    ],
    "car-essentials": [
        "Protects your seats from mud, fur, and everyday wear.",
        "Helps keep your dog safer and more comfortable on the road.",
        "Designed for cleaner, calmer car rides with your pup.",
    ],
    "feeding-hydration": [
        "Supports calmer mealtimes and better hydration on the go.",
        "Portable designs that fit walks, road trips, and park days.",
        "Easy to rinse and pack after use.",
    ],
    "enrichment": [
        "Turns treat time into focused, mentally engaging play.",
        "Helps reduce boredom during travel and downtime.",
        "Supports calmer routines at home and on the road.",
    ],
}

CATEGORY_FAQS: dict[str, list[tuple[str, str]]] = {
    "travel-gear": [
        ("Is this good for everyday walks?", "Yes — it's designed for daily outings, not just big trips."),
        ("How do I clean it?", "Most items rinse easily with warm water and mild soap. Air dry before storing."),
    ],
    "car-essentials": [
        ("Will this fit my car?", "Most covers and accessories are designed for standard back seats. Check dimensions in the details."),
        ("Is it easy to install?", "Yes — most items install in minutes without tools."),
    ],
    "feeding-hydration": [
        ("What size dog is this for?", "See the product details for recommended sizes. When in doubt, size up for larger breeds."),
        ("Is it travel-friendly?", "Yes — these are selected specifically for outings and road trips."),
    ],
    "enrichment": [
        ("How do I introduce this to my dog?", "Start with high-value treats and short sessions. Supervise until your dog is comfortable."),
        ("Can I use this every day?", "Yes — many owners use enrichment mats and puzzles as part of a daily routine."),
    ],
}


def _strip_supplier_noise(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    for noise in ("wholesale", "hot sale", "dropshipping", "factory direct", "【", "】"):
        text = re.sub(re.escape(noise), "", text, flags=re.I)
    return text.strip()


def _extract_features(product: dict[str, Any], title: str) -> list[str]:
    desc = _strip_supplier_noise(product.get("description") or "")
    features: list[str] = []
    for sentence in re.split(r"[.!?\n•·]", desc):
        s = sentence.strip()
        if 20 < len(s) < 120 and any(
            k in s.lower() for k in ("portable", "water", "dog", "travel", "car", "bowl", "mat", "leak", "silicone")
        ):
            features.append(s[0].upper() + s[1:])
        if len(features) >= 5:
            break
    if not features:
        features = [
            f"Thoughtfully selected by {BRAND_NAME} for dog outings and travel.",
            "Designed for practical daily use — not novelty clutter.",
            "Pairs well with walks, park days, and road trips.",
        ]
    return features[:5]


def _premium_title(title_raw: str, category_key: str) -> str:
    title = _strip_supplier_noise(title_raw)
    title = re.sub(r"^(new|hot|wholesale)\s+", "", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip(" -.")

    prefixes = {
        "travel-gear": "PawPath Travel",
        "car-essentials": "PawPath Road Trip",
        "feeding-hydration": "PawPath",
        "enrichment": "PawPath Enrichment",
    }
    prefix = prefixes.get(category_key, "PawPath")
    if not title.lower().startswith("pawpath"):
        title = f"{prefix} — {title}"
    if len(title) > 70:
        title = title[:67].rsplit(" ", 1)[0] + "..."
    return title


def generate_content(opp: ProductOpportunity) -> MerchandisedContent:
    product = opp.cj_product or {}
    title = _premium_title(opp.title_raw, opp.category_key)
    features = _extract_features(product, title)
    benefits = CATEGORY_BENEFITS.get(opp.category_key, CATEGORY_BENEFITS["travel-gear"])
    faq_pairs = CATEGORY_FAQS.get(opp.category_key, CATEGORY_FAQS["travel-gear"])

    intro = (
        f"{title} is part of the {BRAND_NAME} collection — {BRAND_TAGLINE.lower()} "
        f"This piece is curated for dog owners who want gear that works on real outings."
    )

    benefits_html = "<ul>" + "".join(f"<li>{escape(b)}</li>" for b in benefits) + "</ul>"
    features_html = "<ul>" + "".join(f"<li>{escape(f)}</li>" for f in features) + "</ul>"
    faq_html = "".join(
        f"<h3>{escape(q)}</h3><p>{escape(a)}</p>" for q, a in faq_pairs
    )

    description_html = (
        f"<p>{escape(intro)}</p>"
        f"<h2>Why you'll love it</h2>{benefits_html}"
        f"<h2>Features</h2>{features_html}"
        f"<h2>FAQ</h2>{faq_html}"
        f"{SAFETY_FOOTER}"
    )

    seo_title = title[:60].rsplit(" ", 1)[0] if len(title) > 60 else title
    seo_title = f"{seo_title} | {BRAND_NAME}"[:70]

    seo_desc = (
        f"Shop {title} at {BRAND_NAME}. {benefits[0]} Free US shipping on orders $50+."
    )[:155]

    tags = [
        COLLECTIONS.get(opp.category_key, COLLECTIONS["travel-gear"])["tag"],
        opp.category_key.replace("-", " "),
        "dog gear",
        "pet travel",
        "cj-sourced",
        "pawpath-curated",
    ]
    if opp.collection:
        tags.append(opp.collection.collection_tag)

    return MerchandisedContent(
        title=title,
        seo_title=seo_title,
        seo_description=seo_desc,
        description_html=description_html,
        benefits=benefits,
        features=features,
        faqs=[{"question": q, "answer": a} for q, a in faq_pairs],
        tags=tags,
    )
