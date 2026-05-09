# Wallbeds Browser

A small, unofficial, mobile-first catalogue for browsing WallBeds Australia products with large touch targets, readable product cards, and direct links back to the official product pages.

The catalogue is generated from public WallBeds Australia sitemap and WooCommerce Store API data. It does not handle purchasing; all buying and final product verification should happen on the official website.

## Refresh data

```bash
python3 scripts/scrape_products.py
```

## Run locally

Open `index.html` directly in a browser, or serve the folder with any static file server.
