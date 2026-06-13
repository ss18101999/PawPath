#!/usr/bin/env python3
"""Upload PawPath theme images to Shopify Files and write URL map for Liquid."""

import json
import mimetypes
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Optional

STORE = "j53k50-mp.myshopify.com"
ASSETS = Path(__file__).resolve().parents[1] / "theme" / "assets"
OUT = Path(__file__).resolve().parents[1] / "theme" / "snippets" / "pawpath-image-urls.liquid"

IMAGE_KEYS = {
    "hero": "pawpath-hero-walk.jpg",
    "collection-travel": "pawpath-collection-travel.jpg",
    "collection-car": "pawpath-collection-car.jpg",
    "collection-feeding": "pawpath-collection-feeding.jpg",
    "collection-enrichment": "pawpath-collection-enrichment.jpg",
    "collection-bundles": "pawpath-collection-bundles.jpg",
    "lifestyle-car": "pawpath-lifestyle-car.jpg",
    "lifestyle-walk": "pawpath-lifestyle-walk.jpg",
    "lifestyle-mealtime": "pawpath-lifestyle-mealtime.jpg",
    "lifestyle-park": "pawpath-lifestyle-park.jpg",
    "product-water-bottle": "pawpath-product-water-bottle.jpg",
    "product-car-cover": "pawpath-product-car-cover.jpg",
    "product-seat-belt": "pawpath-product-seat-belt.jpg",
    "product-treat-pouch": "pawpath-product-treat-pouch.jpg",
    "product-enrichment": "pawpath-product-enrichment.jpg",
    "product-slow-feeder": "pawpath-product-slow-feeder.jpg",
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
    payload = json.loads(output[start:end + 1])
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload


def staged_upload(filename: str, filepath: Path) -> str:
    mime, _ = mimetypes.guess_type(filename)
    mime = mime or "image/jpeg"
    data = shopify_graphql(
        """mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
          stagedUploadsCreate(input: $input) {
            stagedTargets { url resourceUrl parameters { name value } }
            userErrors { message }
          }
        }""",
        {"input": [{
            "filename": filename,
            "mimeType": mime,
            "resource": "FILE",
            "httpMethod": "POST",
        }]},
    )
    target = data["stagedUploadsCreate"]["stagedTargets"][0]
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


def create_file(resource_url: str, alt: str) -> str:
    data = shopify_graphql(
        """mutation fileCreate($files: [FileCreateInput!]!) {
          fileCreate(files: $files) {
            files {
              ... on MediaImage { id image { url } }
              ... on GenericFile { id url }
            }
            userErrors { message }
          }
        }""",
        {"files": [{
            "alt": alt,
            "contentType": "IMAGE",
            "originalSource": resource_url,
        }]},
    )
    errors = data["fileCreate"]["userErrors"]
    if errors:
        raise RuntimeError(errors)
    file_node = data["fileCreate"]["files"][0]
    if file_node.get("image"):
        return file_node["image"]["url"]
    return file_node["url"]


def write_liquid(url_map: dict[str, str]) -> None:
    lines = [
        "{% comment %} Auto-generated Shopify CDN image URLs {% endcomment %}",
        "{% case key %}",
    ]
    for key, url in url_map.items():
        lines.append(f"  {{% when '{key}' %}}{url}")
    lines.append("{% endcase %}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    url_map = {}
    for key, filename in IMAGE_KEYS.items():
        filepath = ASSETS / filename
        if not filepath.exists():
            print(f"missing {filepath}")
            continue
        print(f"uploading {key} <- {filename}")
        resource_url = staged_upload(filename, filepath)
        cdn_url = create_file(resource_url, f"PawPath {key}")
        url_map[key] = cdn_url
        print(f"  -> {cdn_url}")
    write_liquid(url_map)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
