import scrapy
import json
import re
import yaml
import os
from presio.items import ProductItem


CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config.yaml"))


class FalabellaSpider(scrapy.Spider):
    name = "falabella"
    store_id = 3

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "HTTPERROR_ALLOW_ALL": True,
        "PLAYWRIGHT_BROWSER_TYPE": "chromium",
        "COOKIES_ENABLED": True,
    }

    def __init__(self, max_pages=None, category=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages) if max_pages else None

        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)

        base_url = config["supermarkets"]["falabella"]["base_url"]
        categories = config["categories"]

        if category:
            categories = [
                c for c in categories
                if c["name"].lower() == category.lower() or str(c["id"]) == str(category)
            ]

        self.category_urls = []
        for cat in categories:
            if "falabella" not in cat.get("stores", {}):
                continue
            for url in cat["stores"]["falabella"]["urls"]:
                self.category_urls.append((base_url + url, cat["id"]))

    async def start(self):
        for url, category_id in self.category_urls:
            self.logger.info(f"Starting URL: {url}")
            yield scrapy.Request(
                url=url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_context_kwargs": {
                        "user_agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        ),
                        "locale": "es-PE",
                        "viewport": {"width": 1920, "height": 1080},
                    },
                    "category_id": category_id,
                    "page_num": 1,
                },
                callback=self.parse_page,
                errback=self.errback_close_page,
            )

    async def parse_page(self, response):
        page = response.meta["playwright_page"]
        category_id = response.meta["category_id"]
        page_num = response.meta["page_num"]

        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
            await page.wait_for_selector("script#__NEXT_DATA__", timeout=30000)
            content = await page.content()

            match = re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', content, re.DOTALL
            )
            if not match:
                self.logger.error(f"No __NEXT_DATA__ on {response.url}")
                return

            data = json.loads(match.group(1))
            page_props = data["props"]["pageProps"]
            results = page_props.get("results", [])
            pagination = page_props.get("pagination", {})

            count = pagination.get("count", 0)
            per_page = pagination.get("totalPerPage", 48)

            self.logger.info(
                f"Page {page_num}: {len(results)} products "
                f"(total available: {count})"
            )

            for product in results:
                try:
                    yield self.generate_product(product, category_id)
                except Exception as e:
                    self.logger.error(
                        f"Error extracting product {product.get('productId')}: {e}"
                    )

            has_more = page_num * per_page < count and len(results) > 0
            within_limit = self.max_pages is None or page_num < self.max_pages
            if has_more and within_limit:
                next_page = page_num + 1
                base = response.url.split("?")[0]
                next_url = f"{base}?page={next_page}"
                self.logger.info(f"→ Following page {next_page}")
                yield scrapy.Request(
                    url=next_url,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_context_kwargs": {
                            "user_agent": (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/124.0.0.0 Safari/537.36"
                            ),
                            "viewport": {"width": 1920, "height": 1080},
                        },
                        "category_id": category_id,
                        "page_num": next_page,
                    },
                    callback=self.parse_page,
                    errback=self.errback_close_page,
                )
            else:
                self.logger.info("✓ Category done.")

        except Exception as e:
            self.logger.error(f"✗ Error on page {page_num}: {e}")
        finally:
            await page.close()

    def generate_product(self, product, category_id):
        prices = {
            p["type"]: p["price"][0]
            for p in product.get("prices", [])
            if p.get("price")
        }

        online_price = prices.get("internetPrice")
        regular_price = prices.get("normalPrice")

        discount_label = (product.get("discountBadge") or {}).get("label", "")
        discount_match = re.search(r"\d+", discount_label)
        discount_pct = int(discount_match.group()) if discount_match else None

        brand = product.get("brand", "")
        display_name = product.get("displayName", "")
        name = f"{brand} {display_name}".strip() if brand else display_name

        item = ProductItem()
        item["product_id"] = f"{self.store_id}_{product['productId']}"
        item["store_id"] = self.store_id
        item["product_name"] = name
        item["category_id"] = category_id
        item["regular_price"] = float(regular_price) if regular_price else None
        item["online_price"] = float(online_price) if online_price else None
        item["discount_percentage"] = discount_pct
        item["currency"] = "PEN"
        item["product_url"] = product.get("url")
        return item

    async def errback_close_page(self, failure):
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"Request failed: {failure}")
