# PawPath Autonomous Ads CHANGELOG

Autonomous Facebook/Instagram campaign management for PawPath Supply.

## Commands

```bash
python -m meta_marketing launch        # Phase 1-3: product selection + campaign creation
python -m meta_marketing optimize-ai   # Phase 4: pause losers, scale winners
```

---

## 2026-06-14T11:17:47Z

### Phase 1–3 Launch — COMPLETE

**Products selected (from 92 active Shopify products):**

| Campaign | Product | Price | Score | Why |
|----------|---------|-------|-------|-----|
| PawPath_AI_Test_1 | Portable Pet Dog Water Bottle (Silicone Leaf) | $14.95 | 101 | Impulse price, 8 images, travel/water demand |
| PawPath_AI_Test_2 | Summer Pet Dog Cooling Vest | $35.95 | 96 | Seasonal, problem/solution, strong visuals |
| PawPath_AI_Test_3 | Pet Water Bottle Feeder Bowl (Travel) | $14.95 | 94 | Multi-use outdoor product, 8 images |

**Campaign structure (each):**
- Objective: Sales → **Purchase** optimization
- Targeting: **United States**, age 25–65, dog-owner interests, Advantage+ audience
- Budget: **₹100/day** CBO per campaign (₹300/day total)
- Page: **PawPath** (`1176239588903352`)
- Placements: Advantage+ (automatic)
- **5 ads per campaign:** problem/solution, emotional, lifestyle, benefits + carousel

**Campaign IDs:**
- Test 1: `120250166516680666`
- Test 2: `120250166589180666`
- Test 3: `120250166600840666`

**Actions taken:**
- Used Shopify CDN images directly (ad image upload API not permitted on app)
- Removed Instagram actor — IG not assigned to ad account (Facebook-only until connected)

**Next:**
1. Connect Instagram to ad account in Business Manager for IG placements
2. Run `python -m meta_marketing optimize-ai` after 24–48h delivery
3. Verify Meta Pixel Purchase events on pawpathsupply.com checkout
