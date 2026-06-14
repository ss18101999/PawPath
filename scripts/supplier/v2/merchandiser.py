"""V2 merchandising import — premium content, pricing, collections, Shopify ops."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from .. import shopify_client
from ..cj_client import CJClient
from ..config import COLLECTIONS, MAX_VARIANTS_PER_PRODUCT, V2_AUTO_PUBLISH, V2_IMPORT_STATUS, V2_PIPELINE_LOG
from ..importer import _inventory_quantity, _product_images, _variant_option_values
from ..pricing import parse_cost
from ..progress import ProgressLogger, get_logger
from .collections_intel import assign_collection
from .content import generate_content
from .db import CatalogDB
from .images import assess_product_images
from .models import ProductOpportunity
from .pricing_engine import recommend_pricing


def _usable_images(opp: ProductOpportunity, cj_product: dict[str, Any]) -> list[str]:
    urls = _product_images(cj_product) or opp.image_urls
    assessments, _ = assess_product_images(urls, max_images=8)
    usable = [a.url for a in assessments if not a.rejected]
    if usable:
        return usable
    return [u for u in urls if u.startswith("http")][:6]


def _build_variants_v2(cj_product: dict[str, Any], opp: ProductOpportunity) -> list[dict[str, Any]]:
    variants_in = cj_product.get("variants") or []
    if not variants_in:
        p = opp.pricing
        return [
            {
                "optionValues": [{"optionName": "Title", "name": "Default Title"}],
                "price": f"{p.retail_price:.2f}",
                "compareAtPrice": f"{p.compare_at_price:.2f}",
                "sku": f"CJ-{cj_product.get('productSku', 'SKU')}",
                "inventoryPolicy": "DENY",
            }
        ]

    built: list[dict[str, Any]] = []
    for v in variants_in[:MAX_VARIANTS_PER_PRODUCT]:
        cost = parse_cost(v.get("variantSellPrice") or cj_product.get("sellPrice"))
        if cost <= 0:
            continue
        pricing = recommend_pricing(
            cost,
            category_key=opp.category_key,
            shipping_estimate=opp.pricing.shipping_estimate,
        )
        key = v.get("variantKey") or v.get("variantKeyEn") or "Default Title"
        built.append(
            {
                "optionValues": _variant_option_values(str(key)),
                "price": f"{pricing.retail_price:.2f}",
                "compareAtPrice": f"{pricing.compare_at_price:.2f}",
                "sku": f"CJ-{v.get('variantSku', v.get('vid', 'VAR'))}",
                "inventoryPolicy": "DENY",
            }
        )
    return built or _build_variants_v2({**cj_product, "variants": []}, opp)


def import_opportunity(
    cj: CJClient,
    opp: ProductOpportunity,
    *,
    db: Optional[CatalogDB] = None,
    shop_id: Optional[str] = None,
    status: Optional[str] = None,
    log: Optional[ProgressLogger] = None,
) -> dict[str, Any]:
    """Import a single scored opportunity into Shopify."""
    log = log or get_logger()
    db = db or CatalogDB()
    title_short = (opp.title_raw or "product")[:45]

    if db.is_imported(opp.cj_pid):
        return {"skipped": True, "reason": "already_imported", "cj_pid": opp.cj_pid}

    existing_pids = shopify_client.get_existing_cj_pids()
    if opp.cj_pid in existing_pids:
        return {"skipped": True, "reason": "already_in_shopify", "cj_pid": opp.cj_pid}

    log.detail(f"fetching CJ product: {title_short}")
    cj_product = opp.cj_product or cj.get_product(opp.cj_pid)
    log.detail("adding to CJ My Products...")
    cj.add_to_my_products(opp.cj_pid)

    log.detail("assigning collection...")
    opp.collection = assign_collection(opp, db=db)
    log.detail(f"collection → {opp.collection.collection_title}")

    log.detail("generating premium content...")
    opp.content = generate_content(opp)

    import_status = (status or V2_IMPORT_STATUS).upper()
    if V2_AUTO_PUBLISH:
        import_status = "ACTIVE"

    existing_handles = shopify_client.get_existing_handles()
    handle = shopify_client.unique_handle(opp.content.title, existing_handles)

    tags = list(
        dict.fromkeys(
            opp.content.tags
            + [opp.collection.collection_tag, "cj-import", f"score-{int(opp.opportunity_score)}"]
        )
    )

    variants = _build_variants_v2(cj_product, opp)
    images = _usable_images(opp, cj_product)

    log.detail(f"creating Shopify product ({len(variants)} variants, {len(images)} images)...")
    product = shopify_client.create_product_with_variants(
        title=opp.content.title,
        handle=handle,
        description_html=opp.content.description_html,
        tags=tags,
        status=import_status,
        variants=variants,
        images=images,
        cj_pid=opp.cj_pid,
        cj_sku=opp.cj_sku,
        category_key=opp.category_key,
        finalize=import_status == "ACTIVE",
        setup_catalog=True,
        publish=import_status == "ACTIVE",
        inventory_quantity=_inventory_quantity({"inventory": opp.inventory}),
    )

    collection_id = (
        COLLECTIONS.get(opp.category_key, {}).get("shopify_collection_id")
        or opp.collection.collection_id
    )
    if collection_id:
        log.detail("adding to collection...")
        shopify_client.add_products_to_collection(collection_id, [product["id"]])

    log.detail("setting SEO + metafields...")
    shopify_client.update_product_seo(
        product["id"],
        seo_title=opp.content.seo_title,
        seo_description=opp.content.seo_description,
    )

    shopify_client.graphql(
        """mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
          metafieldsSet(metafields: $metafields) { userErrors { message } }
        }""",
        {
            "metafields": [
                {
                    "ownerId": product["id"],
                    "namespace": "pawpath",
                    "key": "opportunity_score",
                    "type": "number_decimal",
                    "value": str(round(opp.opportunity_score, 1)),
                },
            ]
        },
        allow_mutations=True,
    )

    if shop_id:
        log.detail("linking CJ variants for fulfillment...")
        _link_cj_variants(cj, shop_id=shop_id, cj_product=cj_product, product=product, opp=opp)

    row = {
        "cj_pid": opp.cj_pid,
        "shopify_id": product["id"],
        "shopify_handle": product["handle"],
        "collection_id": opp.collection.collection_id,
        "collection_title": opp.collection.collection_title,
        "opportunity_score": opp.opportunity_score,
    }
    db.record_import(row)
    db.upsert_scored(
        {
            "cj_pid": opp.cj_pid,
            "opportunity_score": opp.opportunity_score,
            "category_key": opp.category_key,
            "rejected": False,
            "rejection_reasons": [],
            "score_breakdown": opp.score_breakdown.to_dict(),
        }
    )
    return row


def _link_cj_variants(
    cj: CJClient,
    *,
    shop_id: str,
    cj_product: dict[str, Any],
    product: dict[str, Any],
    opp: ProductOpportunity,
) -> None:
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
            cj_product_id=opp.cj_pid,
            platform_product_id=str(product["legacyResourceId"]),
            variant_pairs=variant_pairs,
        )


def import_opportunities(
    cj: CJClient,
    opportunities: list[ProductOpportunity],
    *,
    limit: Optional[int] = None,
    shop_id: Optional[str] = None,
    status: Optional[str] = None,
    log: Optional[ProgressLogger] = None,
) -> dict[str, Any]:
    prog = log or get_logger()
    db = CatalogDB()
    items = opportunities[:limit] if limit else opportunities
    total = len(items)
    prog.info(f"Importing {total} product(s)...")

    run_log: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "imported": [],
        "skipped": [],
        "failed": [],
    }

    for idx, opp in enumerate(items, start=1):
        prog.info(f"── Product {idx}/{total} (score {opp.opportunity_score:.0f}) ──")
        try:
            result = import_opportunity(
                cj, opp, db=db, shop_id=shop_id, status=status, log=prog
            )
            if result.get("skipped"):
                run_log["skipped"].append(result)
                prog.warn(f"skipped {opp.title_raw[:50]} ({result.get('reason')})")
            else:
                run_log["imported"].append(result)
                prog.info(
                    f"✓ {opp.content.title if opp.content else opp.title_raw} "
                    f"→ /products/{result['shopify_handle']} "
                    f"({opp.collection.collection_title if opp.collection else ''})"
                )
        except Exception as exc:  # noqa: BLE001
            run_log["failed"].append({"cj_pid": opp.cj_pid, "title": opp.title_raw, "error": str(exc)})
            prog.warn(f"failed {opp.title_raw[:50]}: {exc}")

    run_log["finished_at"] = datetime.now(timezone.utc).isoformat()
    V2_PIPELINE_LOG.write_text(json.dumps(run_log, indent=2))
    prog.info(f"Import log → {V2_PIPELINE_LOG}")
    return run_log
