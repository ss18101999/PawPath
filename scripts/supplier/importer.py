"""Import researched CJ products into Shopify."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from html import escape
from typing import Any, Optional

from .cj_client import CJClient
from .config import CANDIDATES_FILE, COLLECTIONS, DEFAULT_INVENTORY_QUANTITY, IMPORT_LOG_FILE, MAX_VARIANTS_PER_PRODUCT, SAFETY_FOOTER
from .pricing import parse_cost, retail_price
from . import shopify_client
from .progress import get_logger


def _inventory_quantity(item: dict) -> int:
    try:
        cj_qty = int(item.get("inventory") or 0)
    except (TypeError, ValueError):
        cj_qty = 0
    if cj_qty >= 10:
        return cj_qty
    return DEFAULT_INVENTORY_QUANTITY


def _build_description_html(cj_description: str, title: str) -> str:
    text = cj_description or ""
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.I | re.S)
    if "<p>" in text.lower() or "<ul>" in text.lower():
        body = text
    else:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if lines:
            body = "<p>" + "</p><p>".join(escape(ln) for ln in lines[:6]) + "</p>"
        else:
            body = f"<p>{escape(title)} — thoughtfully selected for dog outings, travel, and everyday adventures with your pup.</p>"
    return f"{body}{SAFETY_FOOTER}"


def _variant_option_values(variant_key: str) -> list[dict[str, str]]:
    """Parse CJ variantKey like 'Black-L' into option values."""
    if not variant_key or variant_key.lower() in ("default", "default title"):
        return [{"optionName": "Title", "name": "Default Title"}]

    parts = [p.strip() for p in variant_key.split("-") if p.strip()]
    if len(parts) == 1:
        return [{"optionName": "Style", "name": parts[0]}]
    if len(parts) == 2:
        return [
            {"optionName": "Color", "name": parts[0]},
            {"optionName": "Size", "name": parts[1]},
        ]
    return [{"optionName": "Option", "name": variant_key}]


def _build_variants(cj_product: dict[str, Any]) -> list[dict[str, Any]]:
    variants_in = cj_product.get("variants") or []
    if not variants_in:
        cost = parse_cost(cj_product.get("sellPrice") or 5)
        price, compare = retail_price(cost)
        return [
            {
                "optionValues": [{"optionName": "Title", "name": "Default Title"}],
                "price": price,
                "compareAtPrice": compare,
                "sku": f"CJ-{cj_product.get('productSku', 'SKU')}",
                "inventoryPolicy": "DENY",
            }
        ]

    built: list[dict[str, Any]] = []
    for v in variants_in[:MAX_VARIANTS_PER_PRODUCT]:
        try:
            cost = parse_cost(v.get("variantSellPrice") or cj_product.get("sellPrice"))
        except (TypeError, ValueError):
            cost = 5.0
        if cost <= 0:
            continue
        price, compare = retail_price(cost)
        key = v.get("variantKey") or v.get("variantKeyEn") or "Default Title"
        built.append(
            {
                "optionValues": _variant_option_values(str(key)),
                "price": price,
                "compareAtPrice": compare,
                "sku": f"CJ-{v.get('variantSku', v.get('vid', 'VAR'))}",
                "inventoryPolicy": "DENY",
            }
        )
    return built or _build_variants({**cj_product, "variants": []})


def _product_images(cj_product: dict[str, Any]) -> list[str]:
    images: list[str] = []
    main = cj_product.get("bigImage") or cj_product.get("productImage")
    if main:
        images.append(main)
    for url in cj_product.get("productImageSet") or []:
        if url and url not in images:
            images.append(url)
    for v in cj_product.get("variants") or []:
        img = v.get("variantImage") or v.get("image")
        if img and img not in images:
            images.append(img)
    return [u for u in images if u.startswith("http")]


def import_candidates(
    cj: CJClient,
    *,
    limit: Optional[int] = None,
    source_file: Optional[str] = None,
    status: Optional[str] = None,
    shop_id: Optional[str] = None,
) -> dict[str, Any]:
    path = source_file or str(CANDIDATES_FILE)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    candidates = data.get("candidates") or []
    if limit:
        candidates = candidates[:limit]

    import_status = (status or os.getenv("IMPORT_STATUS", "DRAFT")).upper()
    existing_pids = shopify_client.get_existing_cj_pids()
    existing_handles = shopify_client.get_existing_handles()
    prog = get_logger()
    prog.info(f"V1 import — {len(candidates)} candidate(s) as {import_status}")

    log: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "imported": [],
        "skipped": [],
        "failed": [],
    }

    for i, item in enumerate(candidates, start=1):
        pid = item.get("cj_pid")
        title = item.get("title") or "PawPath Product"
        prog.counter(i, len(candidates), f"import {title[:40]}", every=1, force=len(candidates) <= 10)
        if not pid:
            log["skipped"].append({"reason": "missing pid", "item": item})
            continue
        if pid in existing_pids:
            log["skipped"].append({"reason": "already imported", "cj_pid": pid, "title": title})
            prog.detail(f"skipped (duplicate): {title[:40]}")
            continue

        handle = shopify_client.unique_handle(title, existing_handles)
        category = item.get("category") or "travel-gear"
        tag = item.get("collection_tag") or COLLECTIONS.get(category, {}).get("tag", "travel")

        try:
            cj_product = cj.get_product(pid)
            cj.add_to_my_products(pid)

            description = _build_description_html(
                item.get("description") or cj_product.get("description") or "",
                title,
            )
            variants = _build_variants(cj_product)
            images = _product_images(cj_product)

            product = shopify_client.create_product_with_variants(
                title=title,
                handle=handle,
                description_html=description,
                tags=[tag, category.replace("-", " "), "cj-import"],
                status=import_status,
                variants=variants,
                images=images,
                cj_pid=pid,
                cj_sku=item.get("cj_sku") or cj_product.get("productSku", ""),
                category_key=category,
                finalize=True,
                inventory_quantity=_inventory_quantity(item),
            )

            # Optional CJ ↔ Shopify variant linking for fulfillment
            if shop_id:
                variant_pairs = []
                cj_variants = {v.get("variantKey"): v for v in cj_product.get("variants") or []}
                for sv in product["variants"]["nodes"]:
                    opts = "-".join(o["value"] for o in sv.get("selectedOptions") or [])
                    cj_v = cj_variants.get(opts) or (cj_product.get("variants") or [{}])[0]
                    if cj_v.get("vid") and sv.get("legacyResourceId"):
                        variant_pairs.append(
                            {
                                "cjVariantId": str(cj_v["vid"]),
                                "platformVariantId": str(sv["legacyResourceId"]),
                            }
                        )
                if variant_pairs:
                    cj.connect_product(
                        shop_id=shop_id,
                        cj_product_id=pid,
                        platform_product_id=str(product["legacyResourceId"]),
                        variant_pairs=variant_pairs,
                    )

            log["imported"].append(
                {
                    "title": title,
                    "handle": product["handle"],
                    "shopify_id": product["id"],
                    "cj_pid": pid,
                    "category": category,
                    "status": import_status,
                }
            )
            existing_pids.add(pid)
            prog.info(f"✓ {title} → /products/{product['handle']} ({category})")

        except Exception as exc:  # noqa: BLE001
            log["failed"].append({"title": title, "cj_pid": pid, "error": str(exc)})
            prog.warn(f"✗ {title[:40]}: {exc}")

    log["finished_at"] = datetime.now(timezone.utc).isoformat()
    IMPORT_LOG_FILE.write_text(json.dumps(log, indent=2))
    return log
