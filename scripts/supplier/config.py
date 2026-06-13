"""PawPath supplier integration configuration."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
CACHE_DIR = ROOT / ".cache"
TOKEN_CACHE = CACHE_DIR / "cj_token.json"
CANDIDATES_FILE = DATA_DIR / "cj_candidates.json"
IMPORT_LOG_FILE = DATA_DIR / "cj_import_log.json"
V2_DB_FILE = DATA_DIR / "pawpath_catalog.db"
V2_OPPORTUNITIES_FILE = DATA_DIR / "v2_opportunities.json"
V2_PIPELINE_LOG = DATA_DIR / "v2_pipeline_log.json"

SHOPIFY_STORE = os.getenv("SHOPIFY_STORE", "j53k50-mp.myshopify.com")
VENDOR = "PawPath Supply"
ONLINE_STORE_PUBLICATION_ID = os.getenv(
    "SHOPIFY_ONLINE_STORE_PUBLICATION_ID",
    "gid://shopify/Publication/213947351205",
)
DEFAULT_INVENTORY_QUANTITY = int(os.getenv("DEFAULT_INVENTORY_QUANTITY", "999"))

# Shopify standard product taxonomy + admin product type per PawPath category
SHOPIFY_CATALOG: dict[str, dict[str, str]] = {
    "travel-gear": {
        "taxonomy_id": "gid://shopify/TaxonomyCategory/ap-2-14",
        "product_type": "Dog Travel Gear",
    },
    "car-essentials": {
        "taxonomy_id": "gid://shopify/TaxonomyCategory/ap-2-15",
        "product_type": "Dog Car Accessories",
    },
    "feeding-hydration": {
        "taxonomy_id": "gid://shopify/TaxonomyCategory/ap-2-14",
        "product_type": "Dog Bowls & Feeders",
    },
    "enrichment": {
        "taxonomy_id": "gid://shopify/TaxonomyCategory/ap-2-3-7",
        "product_type": "Dog Enrichment Toys",
    },
}

# PawPath collection handles → automated collection tags
COLLECTIONS: dict[str, dict] = {
    "travel-gear": {
        "title": "Travel Gear",
        "tag": "travel",
        "shopify_collection_id": "gid://shopify/Collection/336326623397",
        "queries": [
            "dog travel water bottle portable",
            "dog treat pouch hiking",
            "collapsible dog bowl travel",
            "dog walking bag treat",
        ],
    },
    "car-essentials": {
        "title": "Car Essentials",
        "tag": "car",
        "shopify_collection_id": "gid://shopify/Collection/336326688933",
        "queries": [
            "dog car seat cover",
            "dog seat belt harness",
            "pet car hammock back seat",
            "dog booster seat car",
        ],
    },
    "feeding-hydration": {
        "title": "Feeding & Hydration",
        "tag": "feeding",
        "shopify_collection_id": "gid://shopify/Collection/336326656165",
        "queries": [
            "slow feeder dog bowl",
            "dog silicone lick mat",
            "portable dog water dispenser",
            "collapsible silicone dog bowl",
        ],
    },
    "enrichment": {
        "title": "Enrichment",
        "tag": "enrichment",
        "shopify_collection_id": "gid://shopify/Collection/336326721701",
        "queries": [
            "snuffle mat for dogs",
            "dog puzzle feeder toy",
            "dog lick mat slow feeding",
            "interactive dog feeding mat",
        ],
    },
}

# Reject products that match these (not dog travel niche)
BLOCK_KEYWORDS = [
    "cat ",
    " cats",
    "kitten",
    "bird ",
    "parrot",
    "hamster",
    "rabbit",
    "fish ",
    "aquarium",
    "reptile",
    "women",
    "men shirt",
    "hoodie",
    "jewelry",
    "phone case",
    "wig",
    "nail ",
    "makeup",
    "candle",
    "christmas",
    "halloween costume",
    "shirt",
    "turtleneck",
    "bottoming",
    "apparel",
    "clothing",
    "sweater",
    "dress",
    "pants",
    "leggings",
    "sock",
    "shoe",
    "booties fashion",
    "hair clip",
    "collar charm",
    "poop bag",
    "waste bag",
    "trash bag",
    "litter",
]

MIN_COST_PRICE = float(os.getenv("MIN_COST_PRICE", "2.50"))

# --- V2 autonomous merchandising ---
BRAND_NAME = "PawPath Supply"
BRAND_TAGLINE = "Easy outings for happy dogs."
MIN_OPPORTUNITY_SCORE = float(os.getenv("MIN_OPPORTUNITY_SCORE", "58"))
MIN_IMAGE_SCORE = float(os.getenv("MIN_IMAGE_SCORE", "45"))
V2_IMPORT_STATUS = os.getenv("V2_IMPORT_STATUS", os.getenv("IMPORT_STATUS", "DRAFT"))
V2_AUTO_PUBLISH = os.getenv("V2_AUTO_PUBLISH", "false").lower() in ("1", "true", "yes")
DEFAULT_SHIPPING_ESTIMATE = float(os.getenv("DEFAULT_SHIPPING_ESTIMATE", "4.50"))
TARGET_GROSS_MARGIN_PCT = float(os.getenv("TARGET_GROSS_MARGIN_PCT", "55"))

# Premium collection naming (tag → display title for new automated collections)
PREMIUM_COLLECTION_NAMES: dict[str, dict[str, str]] = {
    "travel-gear": {
        "tag": "travel-essentials",
        "title": "Travel Essentials",
        "description": "Portable gear for walks, hikes, and adventures with your dog.",
    },
    "car-essentials": {
        "tag": "road-trip",
        "title": "Road Trip Accessories",
        "description": "Car protection, safety, and comfort for dogs on the go.",
    },
    "feeding-hydration": {
        "tag": "travel-feeding",
        "title": "Travel Feeding",
        "description": "Bowls, bottles, and slow feeders built for outings and road trips.",
    },
    "enrichment": {
        "tag": "enrichment",
        "title": "Enrichment & Play",
        "description": "Mental stimulation and calmer mealtimes for curious pups.",
    },
}

# Extra discovery queries for trending pet product discovery
DISCOVERY_SEEDS: list[str] = [
    "dog travel water bottle",
    "dog car seat cover",
    "dog snuffle mat",
    "slow feeder dog bowl",
    "dog treat pouch",
    "portable dog bowl",
    "dog car harness",
    "dog lick mat",
    "collapsible dog bowl",
    "dog hiking gear",
]

MIN_LISTED_NUM = 50
MIN_US_INVENTORY = 5
DEFAULT_PER_CATEGORY = 3
MAX_VARIANTS_PER_PRODUCT = 20
MAX_COST_PRICE = float(os.getenv("MAX_COST_PRICE", "45.0"))

SAFETY_FOOTER = (
    "<p><strong>Safety note:</strong> Always supervise your dog with feeding, enrichment, "
    "and travel products. Choose items that fit your dog's size and behavior. "
    "Discontinue use if damaged.</p>"
)
