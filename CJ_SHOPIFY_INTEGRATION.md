# CJ Dropshipping ↔ Shopify Integration

**Version 2** is an autonomous Pet Product Discovery, Evaluation, Merchandising, and Import System built on top of the V1 utility.

## V2 Architecture

```
discover (CJ API)
    → score (Product Opportunity Score 0-100)
    → quality gate (brand, images, margin)
    → collection intelligence (match or create)
    → content engine (premium DTC copy + SEO)
    → pricing engine (margin-optimized)
    → import (Shopify + publish + inventory)
```

| Phase | Module | Purpose |
|-------|--------|---------|
| 1 | `v2/discovery.py` | Trending product discovery across CJ catalog |
| 1 | `v2/scoring.py` | Product Opportunity Score (10 dimensions) |
| 3 | `v2/collections_intel.py` | Match existing collections or create premium ones |
| 4 | `v2/content.py` | Premium titles, SEO, descriptions, FAQs |
| 5 | `v2/pricing_engine.py` | Margin-optimized pricing by category |
| 6 | `v2/images.py` | Image quality evaluation & rejection |
| 7 | `v2/quality.py` | Brand curation gate |
| 8-9 | `v2/pipeline.py` | Autonomous orchestration |

Persistence: `data/pawpath_catalog.db` (SQLite)

## Prerequisites

```bash
shopify store auth --store j53k50-mp.myshopify.com \
  --scopes read_products,write_products,read_publications,write_publications,read_inventory,write_inventory,read_locations
```

## Progress logging

All V2 commands stream timestamped progress to stdout (flushed immediately so long runs never look stuck):

```
[12s] ━━ Discovery — 26 search terms, up to 2 pages each ━━
[14s]   [3/104] (2%) search "dog snuffle mat" p1 (popularity)
[18s]   "dog snuffle mat" p1 (popularity): +12 new (pool 45)
[2m05s] ━━ Scoring & image checks — 128 products ━━
[2m08s]   [25/128] (19%) scoring: Portable Pet Dog Water Bottle...
```

Use `--quiet` / `-q` for minimal output.

```bash
python3 scripts/cj_shopify.py run --dry-run --import-limit 10
python3 scripts/cj_shopify.py discover -q
```

## V2 Commands (recommended)

```bash
# Full pipeline: discover → re-score Shopify + CJ → keep top 100 → archive losers → import new as DRAFT
python3 scripts/cj_shopify.py run

# Preview catalog changes without touching Shopify
python3 scripts/cj_shopify.py run --dry-run

# Custom catalog size
python3 scripts/cj_shopify.py run --max-catalog 100

# Legacy mode: import top N only (no archive / no catalog cap)
python3 scripts/cj_shopify.py run --no-maintain --import-limit 5

# Discovery & scoring only
python3 scripts/cj_shopify.py discover --per-seed 8
```

## Catalog maintenance (V2 `run`)

Each `run` (default) will:

1. **Discover** new CJ products and score them
2. **Re-score** existing Shopify CJ products from live CJ data
3. **Merge & rank** into one pool (four categories: travel, car, feeding, enrichment)
4. **Keep top 100** (ACTIVE + DRAFT combined, configurable via `MAX_CATALOG_PRODUCTS`)
5. **Archive** lower-ranked Shopify products (unpublished + ARCHIVED)
6. **Import** new winners from CJ as **DRAFT** when slots open

Use `--dry-run` to preview keeps, archives, and imports without changes.

## V1 Commands (legacy, still supported)

```bash
python3 scripts/cj_shopify.py research --per-category 3
python3 scripts/cj_shopify.py import --limit 5
python3 scripts/cj_shopify.py fix
python3 scripts/cj_shopify.py pipeline --per-category 2 --import-limit 8
```

## Product Opportunity Score

Weighted across 10 signals (max ~100):

- Popularity & demand (CJ listing volume)
- Ratings (comment count / evaluation score)
- Growth (new/trending markers)
- Quality (description depth + image score)
- US market fit (warehouse inventory)
- Shipping suitability
- Uniqueness (anti-generic filtering)
- Brandability (premium keywords, anti-wholesale)
- Margin opportunity

Products below `MIN_OPPORTUNITY_SCORE` (default 58) are rejected.

## Collection Intelligence

Before creating a collection, V2:

1. Loads all Shopify collections
2. Matches by title similarity, tags, and category rules
3. Assigns to existing collection if suitable
4. Otherwise creates a premium automated collection (e.g. "Travel Essentials", "Road Trip Accessories")

## Content & SEO

Each import generates:

- Premium PawPath-branded title
- SEO title & meta description
- Benefits, features, FAQ sections
- Collection tags for automated merchandising

## Pricing

Category-aware pricing with:

- Landed cost (product + estimated shipping)
- Target gross margin % (default 55%)
- Category price bands
- Charm pricing (.95)

## Configuration (.env)

```
MIN_OPPORTUNITY_SCORE=58
MIN_IMAGE_SCORE=45
TARGET_GROSS_MARGIN_PCT=55
V2_IMPORT_STATUS=DRAFT
V2_AUTO_PUBLISH=false
DEFAULT_INVENTORY_QUANTITY=999
MAX_CATALOG_PRODUCTS=100
```

Set `V2_AUTO_PUBLISH=true` and `V2_IMPORT_STATUS=ACTIVE` when ready to go live automatically.

## Output Files

| File | Purpose |
|------|---------|
| `data/v2_opportunities.json` | Scored & filtered opportunities |
| `data/v2_pipeline_log.json` | Import results |
| `data/pawpath_catalog.db` | Discovery, scoring, import history |

## Safety

- Quality gate rejects cheap/off-brand/weak-margin products
- Image engine rejects watermarked and low-res images
- Duplicates skipped via DB + Shopify metafields
- V2 defaults to DRAFT unless `V2_AUTO_PUBLISH=true`
