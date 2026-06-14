"""Shopify Admin API via Shopify CLI."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Optional

from .config import (
    COLLECTIONS,
    DEFAULT_INVENTORY_QUANTITY,
    ONLINE_STORE_PUBLICATION_ID,
    SHOPIFY_CATALOG,
    SHOPIFY_STORE,
)

_TAG_TO_CATEGORY: dict[str, str] = {
    cfg["tag"]: key for key, cfg in COLLECTIONS.items()
}
_TAG_TO_CATEGORY.update(
    {
        "travel-essentials": "travel-gear",
        "road-trip": "car-essentials",
        "travel-feeding": "feeding-hydration",
        "travel gear": "travel-gear",
        "car essentials": "car-essentials",
        "feeding hydration": "feeding-hydration",
        "feeding & hydration": "feeding-hydration",
    }
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


def _parse_product_metafields(nodes: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for node in nodes or []:
        key = node.get("key")
        if key:
            out[key] = node.get("value") or ""
    return out


def iter_products(
    *,
    query: str = "",
    page_size: int = 50,
) -> list[dict[str, Any]]:
    """List all products matching query with cursor pagination."""
    all_nodes: list[dict[str, Any]] = []
    cursor: Optional[str] = None
    while True:
        payload = graphql(
            """query ($query: String, $first: Int!, $after: String) {
              products(first: $first, after: $after, query: $query) {
                pageInfo { hasNextPage endCursor }
                nodes {
                  id
                  title
                  handle
                  status
                  productType
                  tags
                  metafields(first: 10, namespace: "pawpath") {
                    nodes { key value }
                  }
                }
              }
            }""",
            {"query": query or None, "first": page_size, "after": cursor},
        )
        batch = payload["products"]["nodes"]
        for node in batch:
            mf = _parse_product_metafields((node.get("metafields") or {}).get("nodes"))
            node["pawpath_metafields"] = mf
            all_nodes.append(node)
        page = payload["products"]["pageInfo"]
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
    return all_nodes


def list_managed_catalog_products() -> list[dict[str, Any]]:
    """ACTIVE + DRAFT CJ-sourced products (paginated)."""
    nodes = iter_products(query="tag:cj-sourced")
    return [n for n in nodes if n.get("status") in ("ACTIVE", "DRAFT")]


def set_product_status(product_id: str, status: str) -> None:
    payload = graphql(
        """mutation productUpdate($input: ProductInput!) {
          productUpdate(input: $input) {
            product { id status }
            userErrors { message }
          }
        }""",
        {"input": {"id": product_id, "status": status.upper()}},
        allow_mutations=True,
    )
    errors = payload["productUpdate"].get("userErrors") or []
    if errors:
        raise ShopifyError(str(errors))


def unpublish_from_online_store(product_id: str) -> None:
    payload = graphql(
        """mutation publishableUnpublish($id: ID!, $input: [PublicationInput!]!) {
          publishableUnpublish(id: $id, input: $input) {
            userErrors { message }
          }
        }""",
        {
            "id": product_id,
            "input": [{"publicationId": ONLINE_STORE_PUBLICATION_ID}],
        },
        allow_mutations=True,
    )
    errors = payload["publishableUnpublish"].get("userErrors") or []
    if errors:
        raise ShopifyError(str(errors))


def update_opportunity_score_metafield(product_id: str, score: float) -> None:
    graphql(
        """mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
          metafieldsSet(metafields: $metafields) { userErrors { message } }
        }""",
        {
            "metafields": [
                {
                    "ownerId": product_id,
                    "namespace": "pawpath",
                    "key": "opportunity_score",
                    "type": "number_decimal",
                    "value": str(round(score, 1)),
                }
            ]
        },
        allow_mutations=True,
    )


def find_product_by_cj_pid(cj_pid: str) -> Optional[dict[str, Any]]:
    """Find a CJ-linked product by pawpath CJ pid (any status)."""
    for node in iter_products(query="tag:cj-sourced"):
        mf = node.get("pawpath_metafields") or {}
        if mf.get("cj_pid") == cj_pid:
            return node
        for tag in node.get("tags") or []:
            if tag == f"cjpid-{cj_pid}":
                return node
    return None


def reactivate_product(product_id: str, *, status: str = "DRAFT", publish: bool = False) -> None:
    set_product_status(product_id, status.upper())
    if publish and status.upper() == "ACTIVE":
        publish_to_online_store(product_id)


def archive_product(product_id: str) -> None:
    """Unpublish and archive a product (removed from catalog count)."""
    try:
        unpublish_from_online_store(product_id)
    except ShopifyError:
        pass
    set_product_status(product_id, "ARCHIVED")


def get_existing_cj_pids() -> set[str]:
    """Products tagged with cj-sourced or having cj pid in tags/metafields."""
    pids: set[str] = set()
    for node in iter_products(query="tag:cj-sourced"):
        mf = node.get("pawpath_metafields") or {}
        if mf.get("cj_pid"):
            pids.add(mf["cj_pid"])
        for tag in node.get("tags") or []:
            if tag.startswith("cjpid-"):
                pids.add(tag.replace("cjpid-", "", 1))
    return pids


def get_existing_handles() -> set[str]:
    return {n["handle"] for n in iter_products()}


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

    for attempt in range(3):
        payload = graphql(
            f"""mutation inventorySetQuantities($input: InventorySetQuantitiesInput!) {{
              inventorySetQuantities(input: $input)
                @idempotent(key: "pawpath-qty-{key_suffix}-{quantity}-{attempt}") {{
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
        if not errors:
            return
        msg = str(errors)
        if "changeFromQuantity" in msg and attempt < 2:
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
            current_qty = 0
            for level in data["inventoryItem"]["inventoryLevels"]["nodes"]:
                if level["location"]["id"] == location_id:
                    qty_nodes = level.get("quantities") or []
                    if qty_nodes:
                        current_qty = qty_nodes[0].get("quantity", 0)
                    break
            if current_qty == quantity:
                return
            continue
        raise ShopifyError(msg)


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


def infer_category_key(product: dict[str, Any]) -> str:
    """Infer PawPath category from tags, product type, or title."""
    tags = [t.lower() for t in (product.get("tags") or [])]
    for tag in tags:
        if tag in _TAG_TO_CATEGORY:
            return _TAG_TO_CATEGORY[tag]

    joined = " ".join(tags)
    for short, key in (
        ("travel", "travel-gear"),
        ("car", "car-essentials"),
        ("feeding", "feeding-hydration"),
        ("enrichment", "enrichment"),
    ):
        if short in joined:
            return key

    product_type = (product.get("productType") or "").lower()
    for key, catalog in SHOPIFY_CATALOG.items():
        pt = catalog.get("product_type", "").lower()
        if pt and (pt in product_type or product_type in pt):
            return key

    title = (product.get("title") or "").lower()
    if any(w in title for w in ("car seat", "car cover", "car hammock", "seat belt")):
        return "car-essentials"
    if any(w in title for w in ("bowl", "feeder", "water bottle", "hydration", "lick mat")):
        if "car" not in title:
            return "feeding-hydration"
    if any(w in title for w in ("snuffle", "puzzle", "enrichment", "treat mat")):
        return "enrichment"
    return "travel-gear"


def canonical_category_tag(category_key: str) -> str:
    return COLLECTIONS.get(category_key, COLLECTIONS["travel-gear"])["tag"]


def collection_id_for_category(category_key: str) -> Optional[str]:
    return COLLECTIONS.get(category_key, {}).get("shopify_collection_id")


def add_products_to_collection(collection_id: str, product_ids: list[str]) -> None:
    """Add products to a manual Shopify collection (batch up to 250)."""
    if not product_ids:
        return
    for i in range(0, len(product_ids), 250):
        batch = product_ids[i : i + 250]
        payload = graphql(
            """mutation collectionAddProducts($id: ID!, $productIds: [ID!]!) {
              collectionAddProducts(id: $id, productIds: $productIds) {
                userErrors { field message }
              }
            }""",
            {"id": collection_id, "productIds": batch},
            allow_mutations=True,
        )
        errors = payload["collectionAddProducts"].get("userErrors") or []
        if errors:
            raise ShopifyError(str(errors))


def add_product_tags(product_id: str, tags: list[str]) -> None:
    """Merge tags onto a product without replacing existing tags."""
    extra = [t for t in tags if t]
    if not extra:
        return
    data = graphql(
        """query ($id: ID!) { product(id: $id) { tags } }""",
        {"id": product_id},
    )
    existing = list(data.get("product", {}).get("tags") or [])
    merged = list(dict.fromkeys(existing + extra))
    if merged == existing:
        return
    payload = graphql(
        """mutation productUpdate($input: ProductInput!) {
          productUpdate(input: $input) {
            userErrors { message }
          }
        }""",
        {"input": {"id": product_id, "tags": merged}},
        allow_mutations=True,
    )
    errors = payload["productUpdate"].get("userErrors") or []
    if errors:
        raise ShopifyError(str(errors))


def setup_product_catalog(
    product_id: str,
    *,
    category_key: str,
    status: str,
    inventory_quantity: Optional[int] = None,
) -> None:
    """Set Shopify taxonomy, product type, and inventory without publishing."""
    update_product_catalog(product_id, category_key=category_key, status=status)
    enable_product_inventory(product_id, quantity=inventory_quantity)


def finalize_product(
    product_id: str,
    *,
    category_key: str,
    status: str = "ACTIVE",
    publish: bool = True,
    inventory_quantity: Optional[int] = None,
) -> None:
    """Assign category, enable inventory, activate, and optionally publish to Online Store."""
    setup_product_catalog(
        product_id,
        category_key=category_key,
        status=status,
        inventory_quantity=inventory_quantity,
    )
    if publish and status == "ACTIVE":
        publish_to_online_store(product_id)


def repair_cj_catalog(
    *,
    product_ids: Optional[list[str]] = None,
    category_by_id: Optional[dict[str, str]] = None,
    inventory_by_id: Optional[dict[str, int]] = None,
    publish: bool = False,
    add_to_collections: bool = True,
) -> dict[str, Any]:
    """
    Repair CJ imports: taxonomy, inventory, canonical tags, and manual collection membership.
    Preserves each product's current ACTIVE/DRAFT status unless publish=True.
    """
    from .progress import get_logger

    prog = get_logger()
    category_by_id = category_by_id or {}
    inventory_by_id = inventory_by_id or {}
    products = list_cj_products()
    if product_ids:
        wanted = set(product_ids)
        products = [p for p in products if p["id"] in wanted]

    by_collection: dict[str, list[str]] = {}
    log: dict[str, Any] = {"fixed": [], "failed": [], "collections": {}}
    total = len(products)
    prog.info(f"Repairing {total} CJ product(s) (publish={publish})...")

    for idx, product in enumerate(products, start=1):
        product_id = product["id"]
        status = (product.get("status") or "DRAFT").upper()
        if status == "ARCHIVED":
            continue

        category_key = category_by_id.get(product_id) or infer_category_key(product)
        collection_id = collection_id_for_category(category_key)
        tag = canonical_category_tag(category_key)
        qty = inventory_by_id.get(product_id)

        try:
            prog.counter(idx, total, f"repair: {product['title'][:45]}", every=1, force=True)
            setup_product_catalog(
                product_id,
                category_key=category_key,
                status=status,
                inventory_quantity=qty,
            )
            add_product_tags(product_id, [tag, category_key.replace("-", " ")])
            if collection_id:
                by_collection.setdefault(collection_id, []).append(product_id)
            if publish and status == "ACTIVE":
                publish_to_online_store(product_id)
            log["fixed"].append(
                {"id": product_id, "title": product["title"], "category": category_key, "status": status}
            )
            prog.detail(f"✓ {product['title'][:50]} → {category_key}")
        except ShopifyError as exc:
            log["failed"].append({"id": product_id, "title": product["title"], "error": str(exc)})
            prog.warn(f"✗ {product['title'][:50]}: {exc}")

    if add_to_collections:
        for collection_id, pids in by_collection.items():
            handle = next(
                (cfg.get("title", collection_id) for cfg in COLLECTIONS.values() if cfg.get("shopify_collection_id") == collection_id),
                collection_id,
            )
            try:
                prog.info(f"Adding {len(pids)} product(s) to {handle}...")
                add_products_to_collection(collection_id, pids)
                log["collections"][collection_id] = len(pids)
            except ShopifyError as exc:
                prog.warn(f"Collection add failed for {handle}: {exc}")
                log["failed"].append({"collection_id": collection_id, "error": str(exc)})

    return log


def list_cj_products() -> list[dict[str, Any]]:
    return list_managed_catalog_products()


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
        category_key = category_by_id.get(product_id) or infer_category_key(product)

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
    setup_catalog: Optional[bool] = None,
    publish: Optional[bool] = None,
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

    if setup_catalog is None:
        setup_catalog = True
    if publish is None:
        publish = finalize and status == "ACTIVE"

    if setup_catalog:
        setup_product_catalog(
            product_id,
            category_key=category_key,
            status=status,
            inventory_quantity=inventory_quantity,
        )
    if publish:
        publish_to_online_store(product_id)

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
