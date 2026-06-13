# PawPath Dropshipping Operations Report

Date: 2026-06-13  
Store: `j53k50-mp.myshopify.com`  
Brand: PawPath Supply  
Niche: dog travel, car, feeding, hydration, walking, and enrichment accessories

## Phase 1 - Store Audit

### Current Store State

- Shopify store is connected as `PawPath Supply` on the Basic plan.
- Live theme is Shopify `Horizon`, theme ID `156053078181`.
- An unpublished development theme exists: `Development (e04cd2-RP-LAP-L3C7TW46HF)`, theme ID `156053635237`.
- Local theme path is `theme/`.
- Theme validation passes with 24 existing Horizon scoped-CSS warnings and no blocking errors.
- Local homepage has already been repositioned for PawPath with a custom `pawpath-home` section and `pawpath.css`.
- Header announcement is aligned with the brand: `Free US shipping on orders over $50`.
- Footer copy is aligned with the email capture offer: `Get the dog outing checklist`.

### Live Catalog State

The store currently has 8 active PawPath products:

1. PawPath Portable Slow Feeder Lick Mat
2. TrailSip Portable Dog Water Bottle
3. RoadGuard Waterproof Dog Car Seat Cover
4. SafeRide Dog Seat Belt Tether
5. PocketPup Travel Treat Pouch
6. SniffQuest Enrichment Snuffle Mat
7. Walk Ready Bundle
8. Road Trip Bundle

Live collections exist:

1. Travel Gear
2. Feeding & Hydration
3. Car Essentials
4. Enrichment
5. Bundles

### Launch Blockers

- All 8 live products are active but still tagged `supplier-needed`.
- Product media is empty for every product.
- Inventory tracking is disabled.
- Inventory policy is `CONTINUE`, meaning products can sell even with zero inventory.
- Variant shipping weights are `0 kg`, which can distort shipping rates and carrier logic.
- Products are branded placeholder records, not DSers/AliExpress-linked supplier SKUs.
- Admin token cannot read installed apps, pages, menus, or product listings without additional scopes.
- DSers app installation and configuration cannot be verified from the current access.

### Niche Assessment

The dog travel/accessory niche is strong enough to continue. It has clear pain points, easy product demos, low-to-moderate shipping complexity, strong bundling potential, and repeat creative angles:

- Cleaner car after muddy walks.
- Hydration without carrying a bowl.
- Treats and waste bags without pocket mess.
- Calmer feeding and enrichment routines.
- Simple road trip kit for dog owners.

The niche is competitive, but the store can differentiate through bundles, useful curation, US-focused shipping expectations, and honest safety claims.

### Weaknesses To Fix First

1. Supplier connection risk: no product should accept real orders until supplier SKUs, shipping estimates, and fulfillment routing are verified.
2. Visual trust risk: no product media means product pages will not convert.
3. Operational risk: active placeholder products with `CONTINUE` inventory policy can create unfulfillable orders.
4. Conversion risk: product template has title, price, variant picker, buy buttons, and description only; it lacks product-level trust badges, shipping reassurance, FAQ, and bundle/cross-sell logic.
5. Navigation verification is blocked by missing Online Store scopes.
6. App verification is blocked by missing app scopes.

### Execution Plan

1. Get DSers/Admin access and confirm whether DSers is installed.
2. If DSers is not installed, install only after confirming the free plan or getting approval for any paid plan.
3. Import supplier-linked products into DSers first, then connect or replace the current placeholder products.
4. Keep products unpublished or unavailable until each has supplier SKU, media, shipping estimate, return expectations, and test-order result.
5. Add final product media and realistic delivery promises.
6. Add product-page trust/CRO blocks to the theme.
7. Confirm menus, pages, policies, shipping profile, checkout, payments, notifications, pixels, and test order.
8. Publish only after explicit approval.

## Phase 2 - Product Research

Research sources used:

- Amazon Best Sellers and product review roundups for dog car travel accessories, travel bowls, water bottles, treat pouches, and seat belts.
- AliExpress and Alitools-indexed listings for supplier pricing, orders, reviews, and seller reliability signals.
- TikTok Creative Center research guides for Top Products, Top Ads, hook formats, and pet ecommerce creative benchmarks.
- Meta ads research for pet brand creative structure, broad targeting, and short-form video.
- Google Trends-derived articles for lick mats, snuffle mats, and pet enrichment.
- Competitor stores including Dog & Go, K9 Kups, Cleverpup, Bubbie, Meadowlark, and other travel-focused pet accessory brands.
- Reddit-style customer pain points around muddy paws, seat protection, hydration, and car organization.

### Ranking Method

Products were scored for:

- Demand strength.
- Trend direction.
- Perceived value.
- Shipping simplicity.
- Supplier quality.
- Markup potential.
- Refund risk.
- Fit with PawPath's dog outing positioning.

### Top 10 Launch Products

1. TrailSip Portable Dog Water Bottle
   - Trend evidence: Amazon and review sites repeatedly rank portable dog water bottles like MalsiPree, WePet, Springer, and PupFlask for walks, cars, hikes, and travel.
   - Why customers buy it: dog hydration without carrying a separate bowl.
   - Estimated product cost: `$5-$8` landed target.
   - Selling price: `$24.95`.
   - Gross margin: about `$16.95-$19.95`, or `68%-80%`.
   - Competition level: high.
   - Trend score: `9/10`.
   - Fulfillment complexity: low.
   - Recommended ad angle: "Your dog gets thirsty mid-walk. One hand, no bowl, no spilled water."

2. RoadGuard Waterproof Dog Car Seat Cover
   - Trend evidence: Amazon Best Sellers is crowded with waterproof hammock-style dog seat covers; competitor Meadowlark sells a similar premium cover around `$59.90`.
   - Why customers buy it: protect seats from fur, mud, drool, scratches, and post-park mess.
   - Estimated product cost: `$18-$26` landed target; reject suppliers above this unless quality is demonstrably premium.
   - Selling price: `$59.95`.
   - Gross margin: about `$33.95-$41.95`, or `57%-70%`.
   - Competition level: high.
   - Trend score: `8.5/10`.
   - Fulfillment complexity: medium due to size and quality variance.
   - Recommended ad angle: "One muddy park trip should not turn into a full car detail."

3. PawPath Portable Slow Feeder Lick Mat
   - Trend evidence: lick mats are tied to pet wellness, anxiety reduction, slow feeding, and enrichment; Google Trends-derived research shows strong seasonal search peaks.
   - Why customers buy it: slows treat time and creates a calming enrichment routine.
   - Estimated product cost: `$1-$4`.
   - Selling price: `$24.95-$29.95`.
   - Gross margin: about `$20.95-$28.95`, or `84%-96%`.
   - Competition level: medium-high.
   - Trend score: `8.5/10`.
   - Fulfillment complexity: low.
   - Recommended ad angle: "Turn peanut butter or wet food into a 15-minute calm break."

4. PocketPup Silicone Treat Pouch
   - Trend evidence: Amazon treat pouch categories feature magnetic, silicone, easy-clean training pouches; The Spruce Pets highlights silicone magnetic closure as a strong feature.
   - Why customers buy it: quick rewards during walks without dirty pockets.
   - Estimated product cost: `$1.88-$5.20`.
   - Selling price: `$19.95`.
   - Gross margin: about `$14.75-$18.07`, or `74%-91%`.
   - Competition level: medium.
   - Trend score: `8/10`.
   - Fulfillment complexity: low.
   - Recommended ad angle: "No crumbs, no pocket smell, rewards ready in one hand."

5. MudStop Portable Dog Paw Cleaner
   - Trend evidence: portable paw cleaners are repeatedly recommended for muddy walks, hikes, and keeping cars/homes clean; Dexas MudBuster is a recognized benchmark.
   - Why customers buy it: prevents muddy paw prints in cars and homes.
   - Estimated product cost: `$3-$7`.
   - Selling price: `$24.95-$29.95`.
   - Gross margin: about `$17.95-$26.95`, or `72%-90%`.
   - Competition level: medium.
   - Trend score: `8/10`.
   - Fulfillment complexity: low-medium due to size variants.
   - Recommended ad angle: "Clean paws before they hit the back seat."

6. SniffQuest Enrichment Snuffle Mat
   - Trend evidence: snuffle mats are identified as a trending pet dropshipping item and support mental stimulation/slow feeding.
   - Why customers buy it: turns treats into a supervised sniffing activity.
   - Estimated product cost: `$7-$15`.
   - Selling price: `$34.95`.
   - Gross margin: about `$19.95-$27.95`, or `57%-80%`.
   - Competition level: medium.
   - Trend score: `7.8/10`.
   - Fulfillment complexity: medium due to fabric quality and packaging.
   - Recommended ad angle: "Rainy day? Turn treats into a sniffing game."

7. ClipFlat Collapsible Travel Bowl Set
   - Trend evidence: Amazon Best Sellers for dog travel bowls includes many collapsible silicone bowl packs with carabiners; Alitools listings show low costs and high order counts.
   - Why customers buy it: compact feeding and water breaks on walks, hikes, and road trips.
   - Estimated product cost: `$1.66-$3.36`.
   - Selling price: `$16.95-$19.95`.
   - Gross margin: about `$13.59-$18.29`, or `80%-92%`.
   - Competition level: high.
   - Trend score: `7.7/10`.
   - Fulfillment complexity: low.
   - Recommended ad angle: "Flat in your bag, full-size when your dog needs a drink."

8. SafeRide Dog Seat Belt Tether
   - Trend evidence: seat belt tethers appear in dog car accessory lists and AliExpress has low-cost, reviewed adjustable models.
   - Why customers buy it: reduces roaming in the back seat.
   - Estimated product cost: `$1.19-$2.77`.
   - Selling price: `$14.95`.
   - Gross margin: about `$12.18-$13.76`, or `81%-92%`.
   - Competition level: high.
   - Trend score: `7.3/10`.
   - Fulfillment complexity: low.
   - Recommended ad angle: "Keep your dog from climbing into the front seat."
   - Compliance note: do not claim crash-tested safety unless supplier certification proves it.

9. SplashGuard No-Spill Travel Bowl
   - Trend evidence: splash-proof car bowls are recommended by The Spruce Pets and other travel bowl guides; Target and competitor stores sell floating-disk versions around `$17-$30`.
   - Why customers buy it: water access in cars without sloshing and wet floors.
   - Estimated product cost: `$3-$7`.
   - Selling price: `$24.95`.
   - Gross margin: about `$17.95-$21.95`, or `72%-88%`.
   - Competition level: medium.
   - Trend score: `7.2/10`.
   - Fulfillment complexity: low-medium due to bulkier shape.
   - Recommended ad angle: "Hydration on the road without the puddle."

10. LeashLock Waste Bag Dispenser
   - Trend evidence: dog poop bag holders are evergreen walking accessories; AliExpress listings show costs under `$2` for basic dispensers.
   - Why customers buy it: keeps bags attached to leash or treat pouch.
   - Estimated product cost: `$0.73-$2.44`.
   - Selling price: `$9.95-$12.95`.
   - Gross margin: about `$7.51-$12.22`, or `75%-94%`.
   - Competition level: high.
   - Trend score: `6.8/10`.
   - Fulfillment complexity: low.
   - Recommended ad angle: "Stop realizing you forgot a bag after the walk starts."

### Top 20 Future Products

1. Dog car door protector pair.
2. Dog travel organizer bag with collapsible bowls.
3. Dog cooling bandana, seasonal summer test only.
4. Dog cooling vest, future only due sizing return risk.
5. Foldable dog ramp for senior dogs, future only due bulk and shipping risk.
6. Backseat extender platform, future only due size and return risk.
7. Dog first-aid travel pouch, verify compliance and contents.
8. Reflective leash/collar set.
9. LED safety collar.
10. Waterproof leash.
11. Portable dog towel/microfiber drying mitt.
12. Pet-safe travel wipes.
13. Airtight treat container.
14. Dog food travel storage bag.
15. Compact grooming brush for after walks.
16. Dog raincoat, future only due sizing.
17. Car cargo liner for SUVs.
18. Dog travel blanket.
19. Slow feeder bowl, non-travel home add-on.
20. Enrichment puzzle toy, future only after breakage testing.

### Products To Avoid

- Medical or supplement products: regulatory and refund risk.
- Chew-proof or indestructible toys: high refund risk unless independently tested.
- Crash-tested safety harnesses/tethers without certifications: legal and trust risk.
- Heavy beds, ramps, crates, and hard-bottom backseat extenders at launch: shipping and return risk.
- Electric automatic paw cleaners: defect, battery, and support risk.
- Apparel-heavy SKUs at launch: sizing exchanges hurt margins.
- Cheap plush toys for aggressive chewers: quality complaints and choking-risk concerns.
- Pet food or treats: compliance, freshness, and repeat fulfillment complexity.

## Phase 3 - Supplier Research

Supplier scoring uses a 100-point model:

- Product fit and quality: 25 points.
- Seller reliability: 20 points.
- Order/review signal: 15 points.
- Shipping performance: 15 points.
- Margin: 15 points.
- DSers/import suitability: 10 points.

### Recommended Suppliers For Top 10

1. Portable Dog Water Bottle
   - Preferred route: AliExpress search for `portable dog water bottle`, then filter by 95%+ store feedback, 4.7+ item rating, 500+ orders, and AliExpress Standard Shipping.
   - Backup supplier references: Doba portable dog water bottle listings and Spocket portable pet water bottle.
   - Supplier URL: `https://www.doba.com/product/lKQZvDnMqcVo/dropshipping-collapsible-pet-water-bottle-for-outdoor-dog-walking.html`
   - Supplier score: `82/100` until exact AliExpress DSers SKU is selected.
   - Delivery estimate: target `7-15 business days` AliExpress Standard or `3-7 business days` if US warehouse.
   - Risk: medium; many clones, need leak test and BPA-free proof.

2. Waterproof Dog Car Seat Cover
   - Candidate: PETRAVEL Official Store / Prodigen cover.
   - Supplier URL: `https://alitools.io/en/showcase/prodigen-dog-car-seat-cover-waterproof-pet-transport-dog-carrier-car-backseat-protector-mat-car-hammock-for-small-large-dogs-32964803636`
   - Visible metrics: Alitools 88%, AliExpress 100%, 62 orders, 10 reviews, 5.0 rating, price `$35.52-$38.56`.
   - Supplier score: `61/100`.
   - Delivery estimate: requires DSers quote.
   - Risk: high margin pressure at visible price; find a lower landed-cost supplier with similar 600D quality or use a US supplier.

3. Silicone Lick Mat
   - Preferred route: AliExpress search for `silicone dog lick mat suction cups slow feeder`.
   - Supplier reference: Melikey Silicone / Alibaba custom lick mat.
   - Supplier URL: `https://www.alibaba.co.uk/product-detail/Wholesale-Custom-Logo-Non-Slip-Silicone_1601578946258.html`
   - Visible metrics: 4.9/5 supplier rating, food-grade silicone claim, `$0.85-$0.97` bulk pricing, lead time `7-15 days` by quantity.
   - Supplier score: `84/100` for private label; `validation-required` for AliExpress single-order DSers.
   - Delivery estimate: supplier quote required.
   - Risk: low if food-grade/BPA-free documentation is confirmed.

4. Silicone Treat Pouch
   - Candidate: KEAN Silicone wholesale/custom.
   - Supplier URL: `https://m.keansilicone.com/dog-water-bottle/Dog_Treat_Bag_Wholesale_2771.html`
   - Visible metrics: price `$1.88`, MOQ 100 per color, lead time `3-15 workdays`, FDA/BPA-free claim, OEM/ODM.
   - Supplier score: `86/100`.
   - Delivery estimate: wholesale quote required; DSers AliExpress SKU still needed for automated dropshipping.
   - Risk: low-medium; validate magnet strength and clip durability.

5. Portable Dog Paw Cleaner
   - Candidate: LYA Silicone 2-in-1 paw cleaner.
   - Supplier URL: `https://www.lyasilicone.com/product/custom-2-in-1-silicone-dog-paw-cleaner-manufacturer/`
   - Visible metrics: OEM/ODM, food-grade silicone positioning, standard and custom sizes.
   - Supplier score: `80/100`.
   - Delivery estimate: quote/sample required.
   - Risk: medium; size fit and odor/material quality must be sampled.

6. Snuffle Mat
   - Candidate: AE Pet Products Store / AIHOME snuffle mat.
   - Supplier URL: `https://alitools.io/en/showcase/pet-dog-snuffle-mat-pet-sniffing-training-blanket-detachable-fleece-pads-dog-mat-relieve-stress-nosework-puzzle-toy-pet-nose-pad-4000134278495`
   - Visible metrics: Alitools 71%, AliExpress 96%, 185 orders, 16 reviews, 4.8 rating, price `$29.45-$101.54`.
   - Supplier score: `48/100`.
   - Delivery estimate: requires DSers quote.
   - Risk: high at visible price and low seller trust. Use this only as product-shape research; source a better listing or US supplier.

7. Collapsible Travel Bowl Set
   - Candidate: FlySong / VanKood 1000ml collapsible bowl.
   - Supplier URL: `https://alitools.io/en/showcase/1000ml-large-collapsible-dog-pet-folding-silicone-bowl-outdoor-travel-portable-puppy-food-container-feeder-dish-bowl-32916677749`
   - Visible metrics: Alitools 86%, AliExpress 96%, 2,000 orders, 416 reviews, 4.8 rating, price `$1.66-$3.36`.
   - Supplier score: `88/100`.
   - Delivery estimate: requires DSers quote; likely standard AliExpress delivery.
   - Risk: low; confirm food-grade/BPA-free and carabiner quality.

8. Dog Seat Belt Tether
   - Candidate: Yiwu Pets Supplies Store adjustable elastic reflective tether.
   - Supplier URL: `https://alitools.io/en/showcase/pet-supplies-car-seat-belt-dog-seat-belt-dog-leash-vehicle-belt-adjustable-cushioning-elastic-reflective-safety-rope-for-dog-cat-4001273374433`
   - Visible metrics: Alitools 96%, 600 orders, 4.8 rating, price `$1.19-$1.79`, 50-75cm length.
   - Supplier score: `84/100`.
   - Delivery estimate: requires DSers quote.
   - Risk: medium due safety claims. Sell as restraint/anti-roaming accessory only.

9. SplashGuard No-Spill Travel Bowl
   - Candidate: Shenzhen Top Technology / TOLOPU anti-spill bowl.
   - Supplier URL: `https://www.alibaba.com/product-detail/Non-Wet-Mouth-Pet-Water-Bowl_1601638280399.html`
   - Visible metrics: 5.0 store rating from 12 reviews, lead time 6 days for 1-500 units, PP+ABS construction, anti-spill function.
   - Supplier score: `77/100`.
   - Delivery estimate: quote required.
   - Risk: medium; bulkier than other launch products and not every floating disk is easy to clean.

10. Waste Bag Dispenser
   - Candidate: Xleipet Store dispenser set.
   - Supplier URL: `https://alitools.io/en/showcase/useful-pet-poop-bag-set-multipurpose-carrier-garbage-clean-dispenser-box-dog-waste-poop-bag-dog-accessories-mascota-pet-supplies-32929294745`
   - Visible metrics: Alitools 90%, AliExpress 98%, 216 orders, 65 reviews, 4.9 rating, price `$0.73-$1.47`.
   - Supplier score: `83/100`.
   - Delivery estimate: requires DSers quote.
   - Risk: low; low AOV, best used as bundle add-on or threshold gift.

### Supplier Rules Before Launch

- Order samples for the water bottle, car seat cover, lick mat, treat pouch, paw cleaner, snuffle mat, and bowl set.
- Confirm no supplier invoices, branding, QR codes, or AliExpress packaging inserts.
- Confirm US delivery estimate with real checkout calculation.
- Confirm product materials and safety claims.
- Confirm photo reviews match listing photos.
- Send a test message and reject suppliers that do not respond within 24 hours.

## Phase 4 - DSers Setup

Status: blocked by platform/app access.

The current Admin token cannot list app installations. DSers installation/configuration must be done through Shopify Admin or a broader app-access token.

Required settings once access is available:

- Connect AliExpress account to DSers.
- Connect DSers to Shopify store `j53k50-mp.myshopify.com`.
- Enable product synchronization.
- Enable inventory synchronization.
- Enable price synchronization with manual approval for product cost changes.
- Enable tracking synchronization.
- Map each Shopify product variant to its DSers/AliExpress supplier variant.
- Keep automatic fulfillment disabled until test order passes.
- Enable order sync from Shopify to DSers.
- Set shipping method preference: AliExpress Standard Shipping or supplier's fastest reliable US option.
- Enable automated tracking updates back to Shopify.

Verification required:

1. Place test order for TrailSip.
2. Confirm order appears in DSers.
3. Confirm supplier and variant mapping is correct.
4. Place supplier order through DSers.
5. Confirm tracking is returned to Shopify.
6. Confirm Shopify customer notification includes tracking.

## Phase 5 - Product Import

Status: blocked for true supplier-linked import until DSers is installed/configured.

Existing products are polished placeholder records, not DSers imports. Recommended next action is to import supplier-linked DSers products as drafts, copy optimized PawPath content over, then either:

- Replace current placeholders, or
- Connect current Shopify products to DSers supplier variants if DSers supports mapping cleanly.

Recommended launch import queue:

1. TrailSip Portable Dog Water Bottle.
2. RoadGuard Waterproof Dog Car Seat Cover.
3. PawPath Portable Slow Feeder Lick Mat.
4. PocketPup Silicone Treat Pouch.
5. MudStop Portable Dog Paw Cleaner.
6. SniffQuest Enrichment Snuffle Mat.
7. ClipFlat Collapsible Travel Bowl Set.
8. SafeRide Dog Seat Belt Tether.
9. SplashGuard No-Spill Travel Bowl.
10. LeashLock Waste Bag Dispenser.

Copy rules for every product:

- Remove supplier brand names.
- Remove AliExpress formatting and claims.
- Use benefit-led titles.
- Add realistic shipping estimate.
- Add material and cleaning notes.
- Add safety/usage note.
- Add product-specific FAQ.
- Add bundle recommendation.

## Phase 6 - Store Structure

Existing collections are directionally correct. Recommended final structure:

- Shop All
- Travel Gear
- Feeding & Hydration
- Car Essentials
- Walking Gear
- Enrichment
- Bundles
- FAQ

Recommended homepage order:

1. Announcement bar: free US shipping over `$50`.
2. Hero: Make every outing easier.
3. Best sellers: water bottle, seat cover, lick mat, treat pouch.
4. Problem blocks: cleaner car rides, calmer mealtimes, ready for the road.
5. Build-your-kit bundle section.
6. Trust block: US-focused shipping, tracking provided, easy returns on unused items.
7. FAQ.
8. Email signup.

## Phase 7 - Conversion Optimization

High-priority theme additions:

- Product-page trust badges near add-to-cart:
  - Tracking provided.
  - Secure checkout.
  - US-focused shipping.
  - 30-day unused-item returns.
- Product-page FAQ block.
- Shipping estimate block.
- Bundle/cross-sell block.
- Cart free-shipping progress reminder.
- Cart checkout reassurance.
- Social proof placeholders clearly labeled until real reviews exist.

Avoid fake reviews. Use starter testimonial copy only if marked as example copy or replace with real reviews after launch.

## Phase 8 - Automation

Target fulfillment flow:

1. Customer places order in Shopify.
2. Shopify order syncs to DSers.
3. DSers matches the Shopify variant to the AliExpress supplier variant.
4. Operator reviews first 5-10 orders manually before enabling full auto-fulfillment.
5. DSers places order with supplier.
6. Supplier processes and ships.
7. Supplier tracking syncs to DSers.
8. DSers syncs tracking back to Shopify.
9. Shopify sends shipping/tracking notification to customer.
10. Operator monitors exceptions: out of stock, delayed shipment, invalid address, wrong variant, duplicate order.

Automation cannot be verified until DSers is installed and at least one test order is placed.

## Phase 9 - Business Report

### Priority Launch Strategy

Start with a 6-product MVP before scaling all 10:

1. TrailSip Portable Dog Water Bottle.
2. RoadGuard Waterproof Dog Car Seat Cover.
3. PawPath Portable Slow Feeder Lick Mat.
4. PocketPup Silicone Treat Pouch.
5. MudStop Portable Dog Paw Cleaner.
6. ClipFlat Collapsible Travel Bowl Set.

Reason: these products are easy to explain, easy to demonstrate, compact enough for dropshipping, and form natural bundles.

### Recommended Bundles

- Walk Ready Kit: water bottle, treat pouch, waste bag dispenser, collapsible bowl.
- Clean Car Kit: car seat cover, paw cleaner, no-spill bowl.
- Calm Pup Kit: lick mat, snuffle mat, treat pouch.

### TikTok Creative Recommendations

- Use 15-30 second vertical UGC clips.
- Open with the dog or the mess in the first 1-2 seconds.
- Use native pet sounds: water pouring, treat pouch click, muddy paws, car door opening.
- Show before/after, not just product shots.
- Test 8-12 hooks before scaling spend.

Example hooks:

- "POV: your dog found every puddle at the park."
- "The one thing I keep in my car for every dog walk."
- "If your dog drinks from your hand on walks, try this."
- "My back seat used to look like this after every park trip."
- "A 10-minute calm break with one lick mat."

### Meta Campaign Recommendations

- Start broad targeting in the US.
- Use Advantage+ Shopping once pixel/catalog data exists.
- Launch with 5-8 truly different creatives per ad set, not minor variations.
- Prioritize Reels and Feed video.
- Retarget video viewers and add-to-cart visitors with bundle offers.

Initial campaign structure:

- Campaign 1: Prospecting, product sales objective, broad US dog owners.
- Campaign 2: Retargeting, 7-day site visitors and video viewers.
- Campaign 3: Bundle offer once 50+ add-to-carts exist.

### Key Risks

- Supplier delivery promises are unverified.
- Current products can sell without inventory tracking.
- No product images exist in Shopify.
- DSers is not verified.
- Menus/pages/apps require additional scopes.
- Safety claims for seat belt tether must be conservative.

### Immediate Next Blockers

Need one of the following:

- Shopify Admin access in browser to install/configure DSers, or
- CLI reauthorization with scopes for apps, pages, menus, listings, fulfillment, and orders, or
- Manual confirmation that DSers is installed and connected.

Recommended extra scopes for the next authenticated pass:

- `read_apps`
- `read_content`
- `write_content`
- `read_online_store_navigation`
- `write_online_store_navigation`
- `read_product_listings`
- `read_orders`
- `write_orders`
- `read_fulfillments`
- `write_fulfillments`

Do not publish or accept live customer orders until the supplier and test-order checks pass.
