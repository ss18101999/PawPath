#!/usr/bin/env python3
"""Audit PawPath storefront links and repair common Shopify setup gaps."""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from supplier.shopify_client import graphql, publish_to_online_store  # noqa: E402
from supplier.config import ONLINE_STORE_PUBLICATION_ID  # noqa: E402

STORE_URL = "https://pawpathsupply.com"

REQUIRED_PAGES = [
    {"title": "About PawPath", "handle": "about", "templateSuffix": "about"},
    {"title": "FAQ", "handle": "faq", "templateSuffix": "faq"},
    {"title": "Shipping & Returns", "handle": "shipping-returns", "templateSuffix": "shipping-returns"},
    {"title": "Contact", "handle": "contact", "templateSuffix": "contact"},
]

CHECK_PATHS = [
    "/",
    "/collections/all",
    "/collections/travel-gear",
    "/collections/car-essentials",
    "/collections/feeding-hydration",
    "/collections/enrichment",
    "/pages/about",
    "/pages/contact",
    "/pages/faq",
    "/pages/shipping-returns",
    "/cart",
    "/search?q=dog",
    "/policies/privacy-policy",
]


def http_status(path: str) -> int | str:
    url = STORE_URL + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PawPathSiteAudit/1.0"})
        with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception as exc:  # noqa: BLE001
        return str(exc)[:80]


def ensure_pages(*, fix: bool) -> list[str]:
    logs: list[str] = []
    existing = {
        p["handle"]: p
        for p in graphql("""query { pages(first: 50) { nodes { handle title templateSuffix } } }""")["pages"]["nodes"]
    }
    for page in REQUIRED_PAGES:
        if page["handle"] in existing:
            logs.append(f"page ok: /pages/{page['handle']}")
            continue
        if not fix:
            logs.append(f"page missing: /pages/{page['handle']}")
            continue
        result = graphql(
            """mutation pageCreate($page: PageCreateInput!) {
              pageCreate(page: $page) {
                page { handle }
                userErrors { message }
              }
            }""",
            {
                "page": {
                    "title": page["title"],
                    "handle": page["handle"],
                    "isPublished": True,
                    "templateSuffix": page["templateSuffix"],
                }
            },
            allow_mutations=True,
        )
        errs = result["pageCreate"].get("userErrors") or []
        if errs:
            logs.append(f"page error {page['handle']}: {errs}")
        else:
            logs.append(f"page created: /pages/{page['handle']}")
    return logs


def publish_collections(*, fix: bool) -> list[str]:
    logs: list[str] = []
    handles = ["travel-gear", "car-essentials", "feeding-hydration", "enrichment"]
    cols = graphql("""query { collections(first: 20) { nodes { id handle resourcePublicationsV2(first: 3) { nodes { isPublished publication { name } } } } } }""")[
        "collections"
    ]["nodes"]
    for col in cols:
        if col["handle"] not in handles:
            continue
        pubs = col.get("resourcePublicationsV2", {}).get("nodes", [])
        online = next((p for p in pubs if p["publication"]["name"] == "Online Store"), None)
        if online and online["isPublished"]:
            logs.append(f"collection ok: /collections/{col['handle']}")
            continue
        if not fix:
            logs.append(f"collection unpublished: /collections/{col['handle']}")
            continue
        graphql(
            """mutation publishablePublish($id: ID!, $input: [PublicationInput!]!) {
              publishablePublish(id: $id, input: $input) { userErrors { message } }
            }""",
            {"id": col["id"], "input": [{"publicationId": ONLINE_STORE_PUBLICATION_ID}]},
            allow_mutations=True,
        )
        logs.append(f"collection published: /collections/{col['handle']}")
    return logs


def audit_links() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in CHECK_PATHS:
        status = http_status(path)
        rows.append({"path": path, "status": status, "ok": status == 200})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit and optionally fix PawPath storefront links")
    parser.add_argument("--fix", action="store_true", help="Create missing pages and publish collections")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    report = {
        "pages": ensure_pages(fix=args.fix),
        "collections": publish_collections(fix=args.fix),
        "links": audit_links(),
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return

    print("=== Pages ===")
    for line in report["pages"]:
        print(line)
    print("\n=== Collections ===")
    for line in report["collections"]:
        print(line)
    print("\n=== Link audit ===")
    for row in report["links"]:
        mark = "OK" if row["ok"] else "FAIL"
        print(f"[{mark}] {row['path']} -> {row['status']}")

    broken = [r for r in report["links"] if not r["ok"]]
    if broken:
        sys.exit(1)


if __name__ == "__main__":
    main()
