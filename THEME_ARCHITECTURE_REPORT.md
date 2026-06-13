# Theme Architecture Report

## Store Connection

- Store domain: `j53k50-mp.myshopify.com`
- Live theme: `Horizon`
- Theme ID: `156053078181`
- Local theme path: `theme/`
- Shopify CLI: `4.1.0`

## File Inventory

- Layouts: 2 files in `theme/layout/`
- Templates: 13 files in `theme/templates/`
- Sections: 41 files in `theme/sections/`
- Snippets: 103 files in `theme/snippets/`
- Assets: 113 files in `theme/assets/`
- Config: 2 files in `theme/config/`
- Locales: 51 files in `theme/locales/`
- Total pulled files: 418

## Theme Type

This is a Shopify Online Store 2.0 theme. The theme is driven by JSON templates and section/block composition. Most page content is configured in JSON files that Shopify may regenerate from the theme editor.

Important note: files such as `templates/index.json`, `templates/product.json`, `sections/header-group.json`, `sections/footer-group.json`, and `config/settings_data.json` include Shopify's auto-generated warning comments. They can be edited locally, but changes may later be overwritten by Shopify admin edits.

## Global Layout

`theme/layout/theme.liquid` is the main shell for the storefront.

It loads:

- SEO metadata through `snippets/meta-tags.liquid`.
- CSS through `snippets/stylesheets.liquid`.
- Fonts through `snippets/fonts.liquid`.
- JavaScript through `snippets/scripts.liquid`.
- Theme variables and color schemes through `snippets/theme-styles-variables.liquid` and `snippets/color-schemes.liquid`.
- Header section group through `{% sections 'header-group' %}`.
- Page content through `{{ content_for_layout }}`.
- Footer section group through `{% sections 'footer-group' %}`.
- Search modal and quick-add modal globally.

`theme/layout/password.liquid` controls the password/coming-soon page.

## Homepage

Homepage file: `theme/templates/index.json`

Current structure:

1. `hero_jVaWmY`
   - Type: `hero`
   - Current text: `Browse our latest products`
   - CTA: `Shop all`
   - Link: `shopify://collections/all`

2. `product_list_fa6P9H`
   - Type: `product-list`
   - Name: `Featured collection`
   - Collection: `all`
   - Max products: 8
   - Layout: grid

The homepage is still ecommerce-default and has not yet been converted to SaaS positioning.

## Product Page

Product template file: `theme/templates/product.json`

Current structure:

1. `main`
   - Type: `product-information`
   - Includes media gallery, product title, price, variant picker, buy buttons, and description.

2. `product_recommendations_qggXJq`
   - Type: `product-recommendations`
   - Heading: `You may also like`
   - Max products: 4

This page is commerce-ready, but an AI SaaS site may not need standard product purchasing unless using Shopify checkout for plans.

## Collection Page

Collection template file: `theme/templates/collection.json`

Current structure:

1. `section`
   - Type: `section`
   - Shows collection title and description.

2. `main`
   - Type: `main-collection`
   - Includes filters, sorting, grid density controls, and product cards.

This is useful if SaaS pricing tiers are represented as products, but it may be secondary for an AI SDR landing site.

## Cart Page

Cart template file: `theme/templates/cart.json`

Current structure:

1. `cart-section`
   - Type: `main-cart`
   - Includes cart title, products, and summary.

2. `product_list_NNFgcy`
   - Type: `product-list`
   - Heading: `You may also like`
   - Collection: `all`
   - Max products: 4

This can stay mostly unchanged if Shopify checkout is used for subscriptions or one-time plan purchases.

## Header

Header group file: `theme/sections/header-group.json`

Current structure:

1. `header-announcements`
   - Current text: `Welcome to our store`

2. `header`
   - Menu: `main-menu`
   - Search enabled.
   - Country selector enabled.
   - Language selector enabled.
   - Sticky header enabled.

For an AI SaaS site, the header should shift from ecommerce navigation to SaaS navigation:

- Product
- Use Cases
- Pricing
- Results
- FAQ
- Book Demo

## Footer

Footer group file: `theme/sections/footer-group.json`

Current structure:

1. `footer`
   - Newsletter headline: `Join our email list`
   - Newsletter body: `Get exclusive deals and early access to new products.`

2. `footer-utilities`
   - Copyright.
   - Policy links.
   - Social links.

For an AI SaaS site, footer content should focus on trust, demo conversion, company links, legal links, and social proof rather than product drops.

## Reusable Sections

Key section files:

- `sections/hero.liquid`: media-forward hero section with image/video support, overlay, responsive media, layout settings, and nested blocks.
- `sections/section.liquid`: generic composable section wrapper that renders child blocks.
- `sections/product-list.liquid`: collection/product grid or carousel.
- `sections/media-with-content.liquid`: split media/text section suitable for feature blocks.
- `sections/custom-liquid.liquid`: flexible escape hatch for custom Liquid/HTML.
- `sections/header.liquid`: global header behavior.
- `sections/footer.liquid`: main footer content.
- `sections/main-page.liquid`: page content.
- `sections/main-cart.liquid`: cart page.
- `sections/product-information.liquid`: product page purchase area.

## Snippets

The theme uses snippets as partials and component renderers.

Important snippet groups:

- Product cards and media: `product-card`, `product-media`, `product-grid`, `price`, `variant-*`.
- Header: `header-row`, `header-actions`, `header-drawer`, `mega-menu-list`.
- Cart: `cart-summary`, `cart-products`, `cart-items-component`, `cart-bubble`.
- Layout helpers: `section`, `group`, `spacing-style`, `size-style`, `gap-style`.
- Search: `search-modal`, `predictive-search-*`.
- Global setup: `scripts`, `stylesheets`, `meta-tags`, `fonts`, `color-schemes`.

## Assets

Primary stylesheet:

- `assets/base.css`

JavaScript is modular and loaded through `snippets/scripts.liquid` with an import map. Important modules include:

- `component.js`
- `utilities.js`
- `section-renderer.js`
- `section-hydration.js`
- `product-form.js`
- `variant-picker.js`
- `cart-drawer.js`
- `quick-add.js`
- `predictive-search.js`
- `header.js`

For SaaS conversion, the least invasive approach is to add a dedicated SaaS CSS asset and targeted SaaS sections rather than heavily editing `base.css`.

## Configuration

Theme settings:

- `config/settings_schema.json`: defines theme editor settings.
- `config/settings_data.json`: active theme setting values.

Current settings use:

- Inter fonts.
- Narrow page width.
- Drawer cart.
- Black/white default color scheme.
- Rounded primary/secondary buttons.

For premium AI SaaS positioning, recommended settings are:

- Wider landing pages.
- Dark navy or near-black hero scheme.
- Electric blue / violet accent.
- Larger enterprise-style typography.
- Reduced ecommerce UI on homepage.

## Validation

Command run:

`shopify theme check --path theme`

Result:

- Passed with warnings only.
- 306 files inspected.
- 24 warnings across 8 files.
- Warnings are existing Horizon scoped-CSS class warnings.

## Recommended Change Strategy

1. Keep the pulled live theme as the baseline backup.
2. Create a development branch and development theme.
3. Convert the homepage first using JSON template changes and purpose-built SaaS sections.
4. Keep ecommerce product/cart functionality intact unless the business model requires replacing it.
5. Avoid editing broad global assets unless needed.
6. Use `theme dev` for preview and hot reload.
7. Push changes only to a development/unpublished theme until approved.
