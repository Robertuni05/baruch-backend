import asyncio
import argparse
import json
import logging
import re
import yaml
import mysql.connector
import nodriver as uc
from datetime import datetime


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("falabella")

CONFIG_PATH = "config.yaml"
STORE_ID = 3


# ── DB ────────────────────────────────────────────────────────────────────────

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Peru123.,",
        database="presio",
    )


def upsert_product(cur, conn, product: dict):
    now = datetime.now()
    cur.execute(
        """
        INSERT INTO product (
            id, store_id, name, category_id,
            regular_price, online_price, discount_pct,
            currency, url, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name          = VALUES(name),
            category_id   = VALUES(category_id),
            regular_price = VALUES(regular_price),
            online_price  = VALUES(online_price),
            discount_pct  = VALUES(discount_pct),
            currency      = VALUES(currency),
            url           = VALUES(url),
            updated_at    = VALUES(updated_at)
        """,
        (
            product["product_id"],
            product["store_id"],
            product["product_name"],
            product["category_id"],
            product["regular_price"],
            product["online_price"],
            product["discount_pct"],
            "PEN",
            product["url"],
            now,
            now,
        ),
    )
    conn.commit()


# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_product(raw: dict, category_id: int) -> dict:
    prices = {
        p["type"]: p["price"][0]
        for p in raw.get("prices", [])
        if p.get("price")
    }
    online_price  = prices.get("internetPrice")
    regular_price = prices.get("normalPrice")

    discount_label = (raw.get("discountBadge") or {}).get("label", "")
    discount_match = re.search(r"\d+", discount_label)
    discount_pct   = int(discount_match.group()) if discount_match else None

    brand        = raw.get("brand", "")
    display_name = raw.get("displayName", "")
    name         = f"{brand} {display_name}".strip() if brand else display_name

    return {
        "product_id":    f"{STORE_ID}_{raw['productId']}",
        "store_id":      STORE_ID,
        "product_name":  name,
        "category_id":   category_id,
        "regular_price": float(regular_price.replace(",", "")) if regular_price else None,
        "online_price":  float(online_price.replace(",", ""))  if online_price  else None,
        "discount_pct":  discount_pct,
        "url":           raw.get("url"),
    }


def extract_next_data(html: str):
    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
    )
    if not match:
        return None, None
    data       = json.loads(match.group(1))
    page_props = data["props"]["pageProps"]
    results    = page_props.get("results", [])
    pagination = page_props.get("pagination", {})
    return results, pagination


# ── Fetcher ───────────────────────────────────────────────────────────────────

async def fetch_page(browser, url: str) -> str:
    logger.info(f"Fetching: {url}")
    tab = await browser.get(url)

    # Wait for page to fully settle (CF challenge can take a few seconds)
    for attempt in range(6):
        await asyncio.sleep(5)
        content = await tab.get_content()
        if "__NEXT_DATA__" in content:
            logger.info(f"__NEXT_DATA__ found after {(attempt + 1) * 5}s")
            return content
        logger.info(f"Waiting for page... attempt {attempt + 1}/6")

    raise TimeoutError(f"__NEXT_DATA__ not found on {url} after 30s")


async def scrape_category(browser, base_url: str, category_id: int, max_pages: int | None, cur, conn):
    page_num   = 1
    total_saved = 0

    while True:
        url  = base_url if page_num == 1 else f"{base_url}?page={page_num}"
        html = await fetch_page(browser, url)

        results, pagination = extract_next_data(html)
        if not results:
            logger.info("No products found — stopping.")
            break

        count    = pagination.get("count", 0)
        per_page = pagination.get("totalPerPage", 48)
        logger.info(f"Page {page_num}: {len(results)} products (total available: {count})")

        saved = 0
        for raw in results:
            try:
                product = parse_product(raw, category_id)
                upsert_product(cur, conn, product)
                saved += 1
            except Exception as e:
                logger.error(f"Error on product {raw.get('productId')}: {e}")

        total_saved += saved
        logger.info(f"Page {page_num}: saved {saved} products")

        has_more     = page_num * per_page < count and len(results) > 0
        within_limit = max_pages is None or page_num < max_pages
        if not (has_more and within_limit):
            break

        page_num += 1

    return total_saved


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(category_filter: str | None, max_pages: int | None):
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    base_url   = config["supermarkets"]["falabella"]["base_url"]
    categories = config["categories"]

    if category_filter:
        categories = [
            c for c in categories
            if c["name"].lower() == category_filter.lower()
            or str(c["id"]) == str(category_filter)
        ]

    category_urls = []
    for cat in categories:
        if "falabella" not in cat.get("stores", {}):
            continue
        for url in cat["stores"]["falabella"]["urls"]:
            category_urls.append((base_url + url, cat["id"]))

    if not category_urls:
        logger.error("No Falabella URLs found for the given category filter.")
        return

    conn = get_connection()
    cur  = conn.cursor()

    chrome_path = (
        "/home/gustavo/.cache/ms-playwright/chromium-1200/chrome-linux64/chrome"
    )
    browser = await uc.start(headless=True, browser_executable_path=chrome_path)

    total = 0
    try:
        for url, category_id in category_urls:
            saved = await scrape_category(browser, url, category_id, max_pages, cur, conn)
            total += saved
    finally:
        cur.close()
        conn.close()
        browser.stop()

    logger.info(f"Done — {total} products saved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Falabella fetcher (nodriver)")
    parser.add_argument("--category",  type=str, default=None, help="Category name or id")
    parser.add_argument("--max-pages", type=int, default=None, help="Max pages per category")
    args = parser.parse_args()

    uc.loop().run_until_complete(main(args.category, args.max_pages))
