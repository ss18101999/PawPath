"""Generate Meta ad copy variations from Shopify product data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from meta_marketing.services.shopify_catalog import ScoredProduct

BRAND = "PawPath Supply"


@dataclass
class AdVariation:
    angle: str
    headline: str
    primary_text: str
    description: str
    cta: str = "SHOP_NOW"

    def to_dict(self) -> dict[str, str]:
        return {
            "angle": self.angle,
            "headline": self.headline,
            "primary_text": self.primary_text,
            "description": self.description,
            "cta": self.cta,
        }


def _short_title(title: str, max_len: int = 55) -> str:
    clean = title.replace("PawPath — ", "").replace("PawPath Travel — ", "").strip()
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 3].rsplit(" ", 1)[0] + "..."


def generate_variations(product: ScoredProduct) -> list[AdVariation]:
    name = _short_title(product.title)
    price = f"${product.price:.2f}"

    return [
        AdVariation(
            angle="problem_solution",
            headline=f"Solve Your Dog's Outdoor Problem",
            primary_text=(
                f"Tired of messy walks and uncomfortable outings? {name} is built for real-life "
                f"dog adventures. Practical gear that works — from {BRAND}. Free US shipping $50+."
            ),
            description=f"{name} — {price} at {BRAND}",
        ),
        AdVariation(
            angle="emotional",
            headline="They Deserve Better Adventures",
            primary_text=(
                f"Your dog is family. Give them gear that keeps outings comfortable and stress-free. "
                f"Shop {name} — curated by {BRAND} for dog parents who actually get out there."
            ),
            description="Gear for dog parents who love the outdoors",
        ),
        AdVariation(
            angle="lifestyle",
            headline="Built for Walks, Parks & Road Trips",
            primary_text=(
                f"From morning walks to weekend road trips — {name} fits real outings. "
                f"Lightweight, practical, and ready when you are. {BRAND}."
            ),
            description=f"Adventure-ready dog gear — {price}",
        ),
        AdVariation(
            angle="benefits",
            headline=f"Smart Gear for Active Dogs",
            primary_text=(
                f"✓ Designed for daily outings\n✓ Easy to use & pack\n✓ From {BRAND} — "
                f"{name} at {price}\nFree US shipping on orders $50+."
            ),
            description=name[:90],
        ),
        AdVariation(
            angle="urgency",
            headline="Summer Outings Start Now",
            primary_text=(
                f"Don't wait until the next heat wave or road trip. Grab {name} today — "
                f"{price} with fast US shipping from {BRAND}."
            ),
            description="Limited-time: free shipping $50+",
        ),
        AdVariation(
            angle="social_proof",
            headline="Dog Parents Are Switching to PawPath",
            primary_text=(
                f"Join thousands of dog owners choosing practical travel & outdoor gear. "
                f"{name} — {price} at {BRAND}. See why pet parents trust us for real outings."
            ),
            description=f"Shop {name} — rated by active dog owners",
        ),
    ]


def pick_carousel_images(product: ScoredProduct, *, max_images: int = 5) -> list[str]:
    return product.image_urls[:max_images]


def variation_for_carousel(product: ScoredProduct) -> AdVariation:
    name = _short_title(product.title)
    return AdVariation(
        angle="carousel_lifestyle",
        headline=f"Shop {name}",
        primary_text=(
            f"Swipe through {name} — practical dog gear for walks, parks, and road trips. "
            f"${product.price:.2f} at {BRAND}. Free US shipping $50+."
        ),
        description=f"{BRAND} — dog travel & outdoor gear",
    )
