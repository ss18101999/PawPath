"""Shopify Admin API via Shopify CLI."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Optional

from .config import (
    DEFAULT_INVENTORY_QUANTITY,
    ONLINE_STORE_PUBLICATION_ID,
    SHOPIFY_CATALOG,
    SHOPIFY_STORE,
)


class ShopifyError(RuntimeError):
    pass


def graphql(query: str, variables: Optional[dict[str, Any]] = None, *, allow_mutations: bool = False) -> dict[str, Any]:
    cmd = [
        "shopify",
        "store",
        "execute",
        "--store",
        SHOPIFY_STORE,
        "--json",
        "--query",
        query,
    ]
    if allow_mutations:
        cmd.append("--allow-mutations")
    if variables:
        cmd.extend(["--variables", json.dumps(variables)])

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise ShopifyError(output.strip() or "Shopify CLI command failed")

    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end == -1:
        raise ShopifyError(output)
    payload = json.loads(output[start : end + 1])
    if "errors" in payload:
        raise ShopifyError(str(payload["errors"]))
    return payload


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:80] or "product"


def list_collections() -> list[dict[str, Any]]:
    data = graphql(
        """query {
          collections(first: 100) {
            nodes {
              id
              title
              handle
              ruleSet {
                rules { column relation condition }
              }
            }
          }
        }"""
    )
    nodes = data["collections"]["nodes"]
    out: list[dict[str, Any]] = []
    for node in nodes:
        rules = []
        rule_set = node.get("ruleSet") or {}
        for rule in rule_set.get("rules") or []:
            rules.append(
                {
                    "column": rule.get("column"),
                    "relation": rule.get("relation"),
                    "condition": rule.get("condition"),
                }
            )
        out.append(
            {
                "id": node["id"],
                "title": node["title"],
                "handle": node.get("handle"),
                "rules": rules,
            }
        )
    return out


def create_automated_collection(
    *,
    title: str,
    tag: str,
    description: str = "",
) -> dict[str, Any]:
    handle = slugify(title)
    payload = graphql(
        """mutation collectionCreate($input: CollectionInput!) {
          collectionCreate(input: $input) {
            collection { id title handle }
            userErrors { message field }
          }
        }""",
        {
            "input": {
                "title": title,
                "handle": handle,
                "descriptionHtml": f"<p>{description}</p>" if description else "",
                "ruleSet": {
                    "appliedDisjunctively": False,
                    "rules": [
                        {
                            "column": "TAG",
                            "relation": "EQUALS",
                            "condition": tag,
                        }
                    ],
                },
            }
        },
        allow_mutations=True,
    )
    result = payload["collectionCreate"]
    if result.get("userErrors"):
        raise ShopifyError(str(result["userErrors"]))
    return result["collection"]


def update_product_seo(
    product_id: str,
    *,
    seo_title: str,
    seo_description: str,
) -> None:
    payload = graphql(
        """mutation productUpdate($input: ProductInput!) {
          productUpdate(input: $input) {
            userErrors { message }
          }
        }""",
        {
            "input": {
                "id": product_id,
                "seo": {"title": seo_title, "description": seo_description},
            }
        },
        allow_mutations=True,
    )
    errors = payload["productUpdate"].get("userErrors") or []
    if errors:
        raise ShopifyError(str(errors))


def get_existing_cj_pids() -> set[str]:
    """Products tagged with cj-sourced or having cj pid in tags."""
    data = graphql(
        """query {
          products(first: 100, query: "tag:cj-sourced") {
            nodes {
              id
              tags
              metafield(namespace: "pawpath", key: "cj_pid") { value }
            }
          }
        }"""
    )
    pids: set[str] = set()
    for node in data["products"]["nodes"]:
        mf = node.get("metafield")
        if mf and mf.get("value"):
            pids.add(mf["value"])
        for tag in node.get("tags") or []:
            if tag.startswith("cjpid-"):
                pids.add(tag.replace("cjpid-", "", 1))
    return pids


def get_existing_handles() -> set[str]:
    data = graphql(
        """query {
          products(first: 250) {
            nodes { handle }
          }
        }"""
    )
    return {n["handle"] for n in data["products"]["nodes"]}


def unique_handle(base: str, existing: set[str]) -> str:
    handle = slugify(base)
    if handle not in existing:
        existing.add(handle)
        return handle
    i = 2
    while f"{handle}-{i}" in existing:
        i += 1
    final = f"{handle}-{i}"
    existing.add(final)
    return final


_primary_location_id: Optional[str] = None


def get_primary_location_id() -> str:
    global _primary_location_id
    if _primary_location_id:
        return _primary_location_id
    data = graphql(
        """query {
          locations(first: 1, query: "active:true fulfillment:false") {
            nodes { id name }
          }
        }"""
    )
    nodes = data["locations"]["nodes"]
    if not nodes:
        raise ShopifyError("No active merchant location found in Shopify.")
    _primary_location_id = nodes[0]["id"]
    return _primary_location_id


def publish_to_online_store(product_id: str) -> None:
    payload = graphql(
        """mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
          publishablePublish(id: $id, input: $input) {
            userErrors { message }
          }
        }""",
        {
            "id": product_id,
            "input": [{"publicationId": ONLINE_STORE_PUBLICATION_ID}],
        },
        allow_mutations=True,
    )
    errors = payload["publishablePublish"].get("userErrors") or []
    if errors:
        raise ShopifyError(str(errors))


def update_product_catalog(
    product_id: str,
    *,
    category_key: str,
    status: str = "ACTIVE",
) -> None:
    catalog = SHOPIFY_CATALOG.get(category_key, SHOPIFY_CATALOG["travel-gear"])
    payload = graphql(
        """mutation productUpdate($input: ProductInput!) {
          productUpdate(input: $input) {
            product { id status category { fullName } productType }
            userErrors { message }
          }
        }""",
        {
            "input": {
                "id": product_id,
                "status": status,
                "category": catalog["taxonomy_id"],
                "productType": catalog["product_type"],
            }
        },
        allow_mutations=True,
    )
    errors = payload["productUpdate"].get("userErrors") or []
    if errors:
        raise ShopifyError(str(errors))


def _enable_variant_inventory(
    inventory_item_id: str,
    *,
    quantity: int,
    location_id: str,
) -> None:
    graphql(
        """mutation inventoryItemUpdate($id: ID!, $input: InventoryItemInput!) {
          inventoryItemUpdate(id: $id, input: $input) {
            userErrors { message }
          }
        }""",
        {
            "id": inventory_item_id,
            "input": {"tracked": True, "requiresShipping": True},
        },
        allow_mutations=True,
    )

    data = graphql(
        """query ($id: ID!) {
          inventoryItem(id: $id) {
            inventoryLevels(first: 10) {
              nodes {
                location { id }
                quantities(names: ["available"]) { quantity }
              }
            }
          }
        }""",
        {"id": inventory_item_id},
    )
    levels = data["inventoryItem"]["inventoryLevels"]["nodes"]
    current_qty: Optional[int] = None
    has_location = False
    for level in levels:
        if level["location"]["id"] == location_id:
            has_location = True
            qty_nodes = level.get("quantities") or []
            if qty_nodes:
                current_qty = qty_nodes[0].get("quantity", 0)
            break

    key_suffix = inventory_item_id.rsplit("/", 1)[-1]
    if not has_location:
        payload = graphql(
            f"""mutation inventoryActivate($inventoryItemId: ID!, $locationId: ID!) {{
              inventoryActivate(inventoryItemId: $inventoryItemId, locationId: $locationId)
                @idempotent(key: "pawpath-activate-{key_suffix}") {{
                userErrors {{ message }}
              }}
            }}""",
            {"inventoryItemId": inventory_item_id, "locationId": location_id},
            allow_mutations=True,
        )
        errors = payload["inventoryActivate"].get("userErrors") or []
        if errors:
            raise ShopifyError(str(errors))
        current_qty = 0

    if current_qty == quantity:
        return

    payload = graphql(
        f"""mutation inventorySetQuantities($input: InventorySetQuantitiesInput!) {{
          inventorySetQuantities(input: $input)
            @idempotent(key: "pawpath-qty-{key_suffix}-{quantity}") {{
            userErrors {{ message }}
          }}
        }}""",
        {
            "input": {
                "name": "available",
                "reason": "correction",
                "quantities": [
                    {
                        "inventoryItemId": inventory_item_id,
                        "locationId": location_id,
                        "quantity": quantity,
                        "changeFromQuantity": current_qty,
                    }
                ],
            }
        },
        allow_mutations=True,
    )
    errors = payload["inventorySetQuantities"].get("userErrors") or []
    if errors:
        raise ShopifyError(str(errors))


def enable_product_inventory(
    product_id: str,
    *,
    quantity: Optional[int] = None,
    location_id: Optional[str] = None,
) -> None:
    qty = quantity if quantity is not None else DEFAULT_INVENTORY_QUANTITY
    loc = location_id or get_primary_location_id()
    data = graphql(
        """query ($id: ID!) {
          product(id: $id) {
            variants(first: 100) {
              nodes { inventoryItem { id } }
            }
          }
        }""",
        {"id": product_id},
    )
    for variant in data["product"]["variants"]["nodes"]:
        inv_id = variant["inventoryItem"]["id"]
        _enable_variant_inventory(inv_id, quantity=qty, location_id=loc)


def finalize_product(
    product_id: str,
    *,
    category_key: str,
    status: str = "ACTIVE",
    publish: bool = True,
    inventory_quantity: Optional[int] = None,
) -> None:
    """Assign category, enable inventory, activate, and publish to Online Store."""
    update_product_catalog(product_id, category_key=category_key, status=status)
    enable_product_inventory(product_id, quantity=inventory_quantity)
    if publish and status == "ACTIVE":
        publish_to_online_store(product_id)


def list_cj_products() -> list[dict[str, Any]]:
    data = graphql(
        """query {
          products(first: 100, query: "tag:cj-sourced") {
            nodes {
              id
              title
              handle
              status
              productType
              tags
              category { fullName }
              resourcePublicationsCount { count }
              variants(first: 1) {
                nodes { inventoryItem { tracked } }
              }
              metafield(namespace: "pawpath", key: "cj_pid") { value }
            }
          }
        }"""
    )
    return data["products"]["nodes"]


def fix_cj_products(
    *,
    product_ids: Optional[list[str]] = None,
    category_by_id: Optional[dict[str, str]] = None,
    inventory_by_id: Optional[dict[str, int]] = None,
) -> dict[str, Any]:
    """Repair CJ imports: category, inventory, publish to Online Store."""
    from .progress import get_logger

    prog = get_logger()
    category_by_id = category_by_id or {}
    inventory_by_id = inventory_by_id or {}
    products = list_cj_products()
    if product_ids:
        wanted = set(product_ids)
        products = [p for p in products if p["id"] in wanted]

    log: dict[str, Any] = {"fixed": [], "failed": []}
    total = len(products)
    prog.info(f"Repairing {total} CJ product(s)...")

    for idx, product in enumerate(products, start=1):
        product_id = product["id"]
        category_key = category_by_id.get(product_id, "travel-gear")
        for tag in product.get("tags") or []:
            if tag in ("travel", "car", "feeding", "enrichment"):
                tag_map = {
                    "travel": "travel-gear",
                    "car": "car-essentials",
                    "feeding": "feeding-hydration",
                    "enrichment": "enrichment",
                }
                category_key = tag_map[tag]
                break

        try:
            prog.counter(idx, total, f"fixing {product['title'][:45]}", every=1, force=True)
            finalize_product(
                product_id,
                category_key=category_key,
                status="ACTIVE",
                publish=True,
                inventory_quantity=inventory_by_id.get(product_id),
            )
            log["fixed"].append({"id": product_id, "title": product["title"], "category": category_key})
            prog.detail(f"✓ {product['title'][:50]}")
        except ShopifyError as exc:
            log["failed"].append({"id": product_id, "title": product["title"], "error": str(exc)})
            prog.warn(f"✗ {product['title'][:50]}: {exc}")

    return log


def create_product_with_variants(
    *,
    title: str,
    handle: str,
    description_html: str,
    tags: list[str],
    status: str,
    variants: list[dict[str, Any]],
    images: list[str],
    cj_pid: str,
    cj_sku: str,
    category_key: str = "travel-gear",
    finalize: bool = True,
    inventory_quantity: Optional[int] = None,
) -> dict[str, Any]:
    product_options = []
    option_values_map: dict[str, set[str]] = {}

    for variant in variants:
        for ov in variant.get("optionValues", []):
            name = ov["optionName"]
            option_values_map.setdefault(name, set()).add(ov["name"])

    for name, values in option_values_map.items():
        product_options.append(
            {"name": name, "values": [{"name": v} for v in sorted(values)]}
        )

    if not product_options:
        product_options = [{"name": "Title", "values": [{"name": "Default Title"}]}]
        for variant in variants:
            variant["optionValues"] = [{"optionName": "Title", "name": "Default Title"}]

    all_tags = list(dict.fromkeys(tags + ["cj-sourced", "supplier-needed", f"cjpid-{cj_pid}"]))

    payload = graphql(
        """mutation productSet($input: ProductSetInput!) {
          productSet(input: $input) {
            product {
              id
              handle
              legacyResourceId
              variants(first: 50) {
                nodes { id sku legacyResourceId selectedOptions { name value } }
              }
            }
            userErrors { field message }
          }
        }""",
        {
            "input": {
                "title": title,
                "handle": handle,
                "descriptionHtml": description_html,
                "vendor": "PawPath Supply",
                "status": status,
                "tags": all_tags,
                "productOptions": product_options,
                "variants": variants,
            }
        },
        allow_mutations=True,
    )

    result = payload["productSet"]
    if result.get("userErrors"):
        raise ShopifyError(str(result["userErrors"]))

    product = result["product"]
    product_id = product["id"]

    # Metafields for CJ linkage
    graphql(
        """mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
          metafieldsSet(metafields: $metafields) {
            userErrors { field message }
          }
        }""",
        {
            "metafields": [
                {
                    "ownerId": product_id,
                    "namespace": "pawpath",
                    "key": "cj_pid",
                    "type": "single_line_text_field",
                    "value": cj_pid,
                },
                {
                    "ownerId": product_id,
                    "namespace": "pawpath",
                    "key": "cj_sku",
                    "type": "single_line_text_field",
                    "value": cj_sku,
                },
            ]
        },
        allow_mutations=True,
    )

    # Attach images from CJ CDN
    for i, url in enumerate(images[:8]):
        if not url:
            continue
        graphql(
            """mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
              productCreateMedia(media: $media, productId: $productId) {
                mediaUserErrors { field message }
              }
            }""",
            {
                "productId": product_id,
                "media": [
                    {
                        "alt": title,
                        "mediaContentType": "IMAGE",
                        "originalSource": url,
                    }
                ],
            },
            allow_mutations=True,
        )

    if finalize:
        finalize_product(
            product_id,
            category_key=category_key,
            status=status,
            publish=status == "ACTIVE",
            inventory_quantity=inventory_quantity,
        )

    return product


def update_variant_costs(product_id: str, variant_costs: list[tuple[str, str]]) -> None:
    """Set cost on variants where supported (inventoryItem.unitCost)."""
    data = graphql(
        """query ($id: ID!) {
          product(id: $id) {
            variants(first: 50) {
              nodes { id inventoryItem { id } }
            }
          }
        }""",
        {"id": product_id},
    )
    variants = data["product"]["variants"]["nodes"]
    for variant, (_, cost) in zip(variants, variant_costs):
        inv_id = variant["inventoryItem"]["id"]
        graphql(
            """mutation inventoryItemUpdate($id: ID!, $input: InventoryItemInput!) {
              inventoryItemUpdate(id: $id, input: $input) {
                userErrors { message }
              }
            }""",
            {"id": inv_id, "input": {"cost": cost}},
            allow_mutations=True,
        )
