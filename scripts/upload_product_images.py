#!/usr/bin/env python3
"""Upload PawPath product images to Shopify via staged uploads."""

import json
import mimetypes
import subprocess
import sys
from pathlib import Path
from typing import Optional

STORE = "j53k50-mp.myshopify.com"
ASSETS = Path(__file__).resolve().parents[1] / "theme" / "assets"

PRODUCT_IMAGES = {
    "pawpath-portable-slow-feeder-lick-mat": "pawpath-product-slow-feeder.jpg",
    "trailsip-portable-dog-water-bottle": "pawpath-product-water-bottle.jpg",
    "roadguard-waterproof-dog-car-seat-cover": "pawpath-product-car-cover.jpg",
    "saferide-dog-seat-belt-tether": "pawpath-product-seat-belt.jpg",
    "pocketpup-travel-treat-pouch": "pawpath-product-treat-pouch.jpg",
    "sniffquest-enrichment-snuffle-mat": "pawpath-product-enrichment.jpg",
    "walk-ready-bundle": "pawpath-collection-bundles.jpg",
    "road-trip-bundle": "pawpath-collection-bundles.jpg",
}


def shopify_graphql(query: str, variables: Optional[dict] = None) -> dict:
    cmd = [
        "shopify", "store", "execute",
        "--store", STORE,
        "--json",
        "--allow-mutations",
        "--query", query,
    ]
    if variables:
        cmd.extend(["--variables", json.dumps(variables)])
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    output = result.stdout
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError(output)
    payload = json.loads(output[start:end + 1])
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload


def get_products() -> dict[str, str]:
    data = shopify_graphql(
        """query {
          products(first: 20) {
            nodes { id handle media(first: 1) { nodes { id } } }
          }
        }"""
    )
    products = {}
    for node in data["products"]["nodes"]:
        if node["media"]["nodes"]:
            continue
        products[node["handle"]] = node["id"]
    return products


def staged_upload(filename: str, filepath: Path) -> str:
    mime, _ = mimetypes.guess_type(filename)
    mime = mime or "image/jpeg"
    data = shopify_graphql(
        """mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
          stagedUploadsCreate(input: $input) {
            stagedTargets { url resourceUrl parameters { name value } }
            userErrors { field message }
          }
        }""",
        {
            "input": [{
                "filename": filename,
                "mimeType": mime,
                "resource": "PRODUCT_IMAGE",
                "httpMethod": "POST",
            }]
        },
    )
    target = data["stagedUploadsCreate"]["stagedTargets"][0]
    import urllib.request

    boundary = "----PawPathBoundary"
    body_parts = []
    for param in target["parameters"]:
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{param["name"]}"\r\n\r\n'
            f'{param["value"]}\r\n'
        )
    file_bytes = filepath.read_bytes()
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    )
    body = "".join(body_parts).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(target["url"], data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    with urllib.request.urlopen(req) as resp:
        resp.read()
    return target["resourceUrl"]


def attach_media(product_id: str, resource_url: str, alt: str) -> None:
    data = shopify_graphql(
        """mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
          productCreateMedia(media: $media, productId: $productId) {
            media { alt status }
            mediaUserErrors { field message }
          }
        }""",
        {
            "productId": product_id,
            "media": [{
                "alt": alt,
                "mediaContentType": "IMAGE",
                "originalSource": resource_url,
            }],
        },
    )
    errors = data["productCreateMedia"]["mediaUserErrors"]
    if errors:
        raise RuntimeError(errors)


def main() -> int:
    products = get_products()
    uploaded = 0
    for handle, filename in PRODUCT_IMAGES.items():
        product_id = products.get(handle)
        if not product_id:
            print(f"skip {handle}: not found or already has media")
            continue
        filepath = ASSETS / filename
        if not filepath.exists():
            print(f"skip {handle}: missing {filepath}")
            continue
        print(f"uploading {handle} <- {filename}")
        resource_url = staged_upload(filename, filepath)
        attach_media(product_id, resource_url, handle.replace("-", " ").title())
        uploaded += 1
    print(f"done: {uploaded} products updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
