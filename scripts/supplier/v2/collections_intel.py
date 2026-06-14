"""V2 collection intelligence — match or create premium Shopify collections."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Optional

from .. import shopify_client
from ..config import COLLECTIONS, PREMIUM_COLLECTION_NAMES
from .db import CatalogDB
from .models import CollectionAssignment, ProductOpportunity


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _slug_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _match_existing_collection(
    collections: list[dict[str, Any]],
    *,
    category_key: str,
    product_title: str,
) -> Optional[dict[str, Any]]:
    premium = PREMIUM_COLLECTION_NAMES.get(category_key, {})
    target_tag = premium.get("tag") or COLLECTIONS.get(category_key, {}).get("tag", "")
    target_title = premium.get("title") or COLLECTIONS.get(category_key, {}).get("title", "")

    best: Optional[dict[str, Any]] = None
    best_score = 0.0
    title_words = _slug_words(product_title)

    for col in collections:
        score = 0.0
        col_title = col.get("title") or ""
        col_handle = col.get("handle") or ""
        rules = col.get("rules") or []

        if _similarity(col_title, target_title) > 0.72:
            score += 0.5
        if target_tag and target_tag in col_handle:
            score += 0.3
        for rule in rules:
            cond = (rule.get("condition") or "").lower()
            if target_tag and target_tag in cond:
                score += 0.4
        overlap = len(title_words & _slug_words(col_title))
        score += min(overlap * 0.05, 0.2)

        if category_key.replace("-", " ") in col_title.lower():
            score += 0.25

        if score > best_score:
            best_score = score
            best = col

    if best and best_score >= 0.45:
        return best

    legacy_id = COLLECTIONS.get(category_key, {}).get("shopify_collection_id")
    if legacy_id:
        for col in collections:
            if col.get("id") == legacy_id:
                return col
    return None


def assign_collection(
    opp: ProductOpportunity,
    *,
    db: Optional[CatalogDB] = None,
) -> CollectionAssignment:
    """Resolve the PawPath manual collection for this category."""
    db = db or CatalogDB()
    cfg = COLLECTIONS.get(opp.category_key, COLLECTIONS["travel-gear"])
    legacy_id = cfg.get("shopify_collection_id")
    canonical_tag = cfg.get("tag", "travel")

    collections = shopify_client.list_collections()
    db.sync_collections_cache(
        [
            {
                "id": c["id"],
                "title": c["title"],
                "handle": c.get("handle"),
                "tag": _extract_collection_tag(c),
            }
            for c in collections
        ]
    )

    if legacy_id:
        for col in collections:
            if col.get("id") == legacy_id:
                return CollectionAssignment(
                    collection_id=legacy_id,
                    collection_title=col.get("title") or cfg["title"],
                    collection_handle=col.get("handle") or "",
                    collection_tag=canonical_tag,
                    created=False,
                    category_key=opp.category_key,
                )

    existing = _match_existing_collection(
        collections,
        category_key=opp.category_key,
        product_title=opp.title_raw,
    )

    if existing:
        tag = canonical_tag or _extract_collection_tag(existing)
        return CollectionAssignment(
            collection_id=existing["id"],
            collection_title=existing["title"],
            collection_handle=existing.get("handle") or "",
            collection_tag=tag,
            created=False,
            category_key=opp.category_key,
        )

    premium = PREMIUM_COLLECTION_NAMES.get(opp.category_key, PREMIUM_COLLECTION_NAMES["travel-gear"])
    created = shopify_client.create_automated_collection(
        title=premium["title"],
        tag=canonical_tag,
        description=premium.get("description", ""),
    )
    return CollectionAssignment(
        collection_id=created["id"],
        collection_title=created["title"],
        collection_handle=created["handle"],
        collection_tag=canonical_tag,
        created=True,
        category_key=opp.category_key,
    )


def _extract_collection_tag(collection: dict[str, Any]) -> str:
    for rule in collection.get("rules") or []:
        if rule.get("column") == "TAG" and rule.get("condition"):
            return str(rule["condition"])
    handle = collection.get("handle") or ""
    return handle.replace("-", " ")
