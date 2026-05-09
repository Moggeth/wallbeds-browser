#!/usr/bin/env python3
import html
import json
import re
import textwrap
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


BASE = "https://www.wallbedsaustralia.com.au"
PRODUCT_SITEMAP = f"{BASE}/product-sitemap.xml"
STORE_API = f"{BASE}/wp-json/wc/store/v1/products"
ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "products.json"


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.links = []
        self._current_href = None
        self._current_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self._current_href = urllib.parse.urljoin(BASE, attrs["href"])
            self._current_text = []

    def handle_endtag(self, tag):
        if tag == "a" and self._current_href:
            text = " ".join("".join(self._current_text).split())
            if text:
                self.links.append({"label": text, "url": self._current_href})
            self._current_href = None
            self._current_text = []

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return
        self.parts.append(text)
        if self._current_href:
            self._current_text.append(text)

    def get_text(self):
        text = html.unescape(" ".join(self.parts))
        text = re.sub(r"\s+", " ", text).strip()
        return text


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 accessible-catalogue"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 accessible-catalogue"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8")


def sitemap_urls():
    xml = fetch_text(PRODUCT_SITEMAP)
    root = ET.fromstring(xml)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [node.text for node in root.findall(".//sm:loc", ns) if node.text]


def clean_html_text(markup):
    parser = TextExtractor()
    parser.feed(markup or "")
    return parser.get_text(), parser.links


def first_sentence_or_summary(text, max_chars=340):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    summary = ""
    for sentence in sentences:
        candidate = f"{summary} {sentence}".strip()
        if len(candidate) > max_chars:
            break
        summary = candidate
    if not summary:
        summary = textwrap.shorten(text, width=max_chars, placeholder="...")
    return summary


def format_price(product):
    prices = product.get("prices") or {}
    currency = prices.get("currency_symbol", "$")
    minor_unit = int(prices.get("currency_minor_unit", 2) or 2)
    price = prices.get("price")
    if not price:
        return ""
    try:
        amount = int(price) / (10**minor_unit)
        return f"{currency}{amount:,.2f}"
    except ValueError:
        return html.unescape(product.get("price_html", ""))


def normalise_product(product):
    description, links = clean_html_text(product.get("description", ""))
    images = product.get("images") or []
    image = images[0] if images else {}
    attributes = []
    for attribute in product.get("attributes") or []:
        terms = [html.unescape(term.get("name", "")) for term in attribute.get("terms", []) if term.get("name")]
        if terms:
            attributes.append({"name": html.unescape(attribute.get("name", "")), "values": terms})

    return {
        "id": product.get("id"),
        "name": html.unescape(product.get("name", "")),
        "slug": product.get("slug", ""),
        "url": product.get("permalink", ""),
        "price": format_price(product),
        "rawPrice": product.get("prices", {}).get("price", ""),
        "onSale": bool(product.get("on_sale")),
        "inStock": bool(product.get("is_in_stock")),
        "stockText": product.get("stock_availability", {}).get("text") or ("In stock" if product.get("is_in_stock") else "Check availability"),
        "categories": [html.unescape(category.get("name", "")) for category in product.get("categories", []) if category.get("name")],
        "attributes": attributes,
        "image": {
            "src": image.get("src", ""),
            "thumbnail": image.get("thumbnail", image.get("src", "")),
            "alt": html.unescape(image.get("alt") or product.get("name", "")),
        },
        "summary": first_sentence_or_summary(description),
        "sourceLinks": links,
    }


def main():
    urls = sitemap_urls()
    products = []
    page = 1
    while True:
        params = urllib.parse.urlencode({"per_page": 100, "page": page})
        batch = fetch_json(f"{STORE_API}?{params}")
        if not batch:
            break
        products.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    by_url = {product.get("permalink"): normalise_product(product) for product in products}
    ordered = [by_url[url] for url in urls if url in by_url]
    for product in products:
        if product.get("permalink") not in urls:
            ordered.append(normalise_product(product))

    categories = sorted({category for product in ordered for category in product["categories"]})
    payload = {
        "source": BASE,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "products": ordered,
        "categories": categories,
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(ordered)} products to {DATA_PATH}")


if __name__ == "__main__":
    main()
