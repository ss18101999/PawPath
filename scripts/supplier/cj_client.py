"""CJ Dropshipping API client."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from .config import CACHE_DIR, TOKEN_CACHE

BASE_URL = "https://developers.cjdropshipping.com/api2.0/v1"


class CJError(RuntimeError):
    pass


class CJClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or os.getenv("CJ_API_KEY", "").strip()
        if not self.api_key:
            raise CJError(
                "CJ_API_KEY is missing. Copy .env.example to .env and add your key from "
                "CJ > My CJ > Authorization > API > Generate."
            )
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0

    def _load_cached_token(self) -> Optional[str]:
        if not TOKEN_CACHE.exists():
            return None
        try:
            data = json.loads(TOKEN_CACHE.read_text())
            if data.get("accessToken") and data.get("expiresAt", 0) > time.time() + 300:
                return data["accessToken"]
        except (json.JSONDecodeError, KeyError):
            return None
        return None

    def _save_token(self, access_token: str, expires_at: float) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE.write_text(
            json.dumps({"accessToken": access_token, "expiresAt": expires_at}, indent=2)
        )

    def authenticate(self) -> str:
        cached = self._load_cached_token()
        if cached:
            self._access_token = cached
            return cached

        payload = json.dumps({"apiKey": self.api_key}).encode()
        req = urllib.request.Request(
            f"{BASE_URL}/authentication/getAccessToken",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        data = self._read_json(req)
        token_data = data.get("data") or {}
        token = token_data.get("accessToken")
        if not token:
            raise CJError(f"CJ auth failed: {data.get('message', data)}")
        # Default ~15 days; cache for 7 days conservatively
        expires_at = time.time() + 7 * 86400
        self._access_token = token
        self._token_expiry = expires_at
        self._save_token(token, expires_at)
        return token

    @property
    def token(self) -> str:
        if not self._access_token:
            return self.authenticate()
        return self._access_token

    def _read_json(self, req: urllib.request.Request) -> dict[str, Any]:
        last_err: Optional[Exception] = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    body = resp.read().decode()
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode() if exc.fp else str(exc)
                raise CJError(f"CJ HTTP {exc.code}: {detail}") from exc
            except urllib.error.URLError as exc:
                last_err = exc
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise CJError(f"CJ network error: {exc}") from exc
        else:
            raise CJError(f"CJ network error: {last_err}")

        data = json.loads(body)
        if not data.get("result", data.get("success", False)) and data.get("code") not in (0, 200):
            raise CJError(f"CJ API error: {data.get('message', data)}")
        return data

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = f"{BASE_URL}{path}"
        if params:
            query = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None},
                doseq=True,
            )
            url = f"{url}?{query}"

        headers = {
            "Content-Type": "application/json",
            "CJ-Access-Token": self.token,
        }
        data_bytes = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data_bytes, method=method.upper(), headers=headers)
        response = self._read_json(req)
        return response.get("data")

    def search_products_v2(
        self,
        *,
        keyword: str,
        page: int = 1,
        size: int = 50,
        country_code: Optional[str] = None,
        zone_platform: Optional[str] = None,
        order_by: int = 0,
        features: Optional[list[str]] = None,
        verified_warehouse: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Search CJ catalog. order_by: 0=relevance, 1=listing popularity."""
        params: dict[str, Any] = {
            "keyWord": keyword,
            "page": page,
            "size": size,
            "orderBy": order_by,
            "sort": "desc",
        }
        if country_code:
            params["countryCode"] = country_code
        if zone_platform:
            params["zonePlatform"] = zone_platform
        if verified_warehouse is not None:
            params["verifiedWarehouse"] = verified_warehouse
        if features:
            for i, feat in enumerate(features):
                params[f"features[{i}]"] = feat

        data = self.request("GET", "/product/listV2", params=params)
        if not data:
            return []
        content = data.get("content") or []
        products: list[dict[str, Any]] = []
        for block in content:
            products.extend(block.get("productList") or [])
        return products

    def get_product(self, pid: str) -> dict[str, Any]:
        data = self.request(
            "GET",
            "/product/query",
            params={"pid": pid, "countryCode": "US"},
        )
        if not data:
            raise CJError(f"Product not found: {pid}")
        return data

    def add_to_my_products(self, product_id: str) -> bool:
        try:
            self.request("POST", "/product/addToMyProduct", body={"productId": product_id})
            return True
        except CJError as exc:
            if "added to My Products" in str(exc):
                return True
            raise

    def connect_product(
        self,
        *,
        shop_id: str,
        cj_product_id: str,
        platform_product_id: str,
        variant_pairs: list[dict[str, str]],
        logistics: str = "USPS",
        source_country: str = "CN",
        target_country: str = "US",
    ) -> bool:
        body = {
            "shopId": shop_id,
            "defaultArea": 1,
            "logistics": logistics,
            "cjProductId": cj_product_id,
            "platformProductId": platform_product_id,
            "sourceCountryCode": source_country,
            "sourceCountry": "China",
            "targetCountryCode": target_country,
            "targetCountry": "United States",
            "variantList": variant_pairs,
        }
        try:
            self.request("POST", "/product/conn/connection", body=body)
            return True
        except CJError:
            return False
