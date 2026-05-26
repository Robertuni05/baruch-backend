import scrapy
import random
import yaml
import os
from presio.items import ProductItem


CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config.yaml"))


class WongSpider(scrapy.Spider):
    name = "wong"
    store_id = 2

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self, max_pages=None, max_scrolls=None, no_change_limit=None, category=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages) if max_pages else None
        self.max_scrolls = int(max_scrolls) if max_scrolls else 7
        self.no_change_limit = int(no_change_limit) if no_change_limit else 5
        self.pages_scraped = 0

        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)

        base_url = config["supermarkets"]["wong"]["base_url"]
        categories = config["categories"]

        if category:
            categories = [
                c for c in categories
                if c["name"].lower() == category.lower() or str(c["id"]) == str(category)
            ]

        self.start_urls = []
        self.url_category_map = {}
        for cat in categories:
            if "wong" not in cat["stores"]:
                continue
            for url in cat["stores"]["wong"]["urls"]:
                full_url = base_url + url
                self.start_urls.append(full_url)
                self.url_category_map[full_url] = cat["id"]

    async def start(self):
        for url in self.start_urls:
            self.logger.info(f"Starting URL: {url}")
            yield scrapy.Request(
                url=url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_context_kwargs": {
                        "user_agent": random.choice(self.user_agents),
                        "viewport": {"width": 1920, "height": 1080},
                    },
                    "category_id": self.url_category_map[url],
                },
                callback=self.parse_with_scroll,
                errback=self.errback_close_page,
            )

    async def parse_with_scroll(self, response):
        page = response.meta["playwright_page"]
        category_id = response.meta.get("category_id")
        self.pages_scraped += 1

        try:
            self.logger.info(f"{'='*60}")
            self.logger.info(f"PROCESSING PAGE #{self.pages_scraped} — {response.url}")
            self.logger.info(f"{'='*60}")

            await page.wait_for_selector('[data-af-element="search-result"]', timeout=30000)
            await self._scroll_and_load_products(page)

            content = await page.content()
            response = response.replace(body=content)

            products_ref = response.xpath(
                '//div[contains(@class, "wongio-cmedia-integration-cencosud-1-x-galleryItem")]'
            )

            for idx, product_ref in enumerate(products_ref, 1):
                try:
                    yield self.generate_product(product_ref, category_id)
                except Exception as e:
                    self.logger.error(f"Error extracting product {idx}: {e}")

            self.logger.info(f"✓ Extracted products from page #{self.pages_scraped}")

            next_page = await page.evaluate(
                "() => { const l = document.querySelector('link[rel=\"next\"]'); return l ? l.href : null; }"
            )
            if next_page:
                if self.max_pages is None or self.pages_scraped < self.max_pages:
                    self.logger.info("→ Following next page")
                    yield scrapy.Request(
                        url=next_page,
                        meta={
                            "playwright": True,
                            "playwright_include_page": True,
                            "playwright_context_kwargs": {
                                "user_agent": random.choice(self.user_agents),
                                "viewport": {"width": 1920, "height": 1080},
                            },
                            "category_id": category_id,
                        },
                        callback=self.parse_with_scroll,
                        errback=self.errback_close_page,
                    )
                else:
                    self.logger.info(f"✗ Reached max_pages limit ({self.max_pages})")
            else:
                self.logger.info("✗ No next page. Category done.")

        except Exception as e:
            self.logger.error(f"✗ Error on page #{self.pages_scraped}: {e}")
        finally:
            await page.close()

    async def _scroll_and_load_products(self, page):
        previous_count = 0
        no_change_count = 0
        scroll_attempts = 0

        self.logger.info("Starting scroll loop...")

        while scroll_attempts < self.max_scrolls:
            current_count = await page.evaluate(
                "() => document.querySelectorAll('[data-af-element=\"search-result\"]').length"
            )
            self.logger.info(f"  Scroll #{scroll_attempts + 1}: {current_count} products")

            if current_count == previous_count:
                no_change_count += 1
                if no_change_count >= self.no_change_limit:
                    self.logger.info(f"  No new products after {self.no_change_limit} scrolls")
                    break
            else:
                no_change_count = 0

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(5000)

            previous_count = current_count
            scroll_attempts += 1

        final_count = await page.evaluate(
            "() => document.querySelectorAll('[data-af-element=\"search-result\"]').length"
        )
        self.logger.info(f"  Final: {final_count} products loaded")
        return final_count

    def generate_product(self, product, category_id=None):
        name = product.xpath(
            './/span[contains(@class, "vtex-product-summary-2-x-productBrand")]/text()'
        ).get()

        product_url = product.xpath(
            './/a[contains(@class, "vtex-product-summary-2-x-clearLink")]/@href'
        ).get()

        discount_elem = product.xpath(
            './/span[contains(@class, "vtex-product-price-1-x-savingsPercentage")]/text()'
        ).get()
        discount = discount_elem.strip().replace("%", "") if discount_elem else None

        price_integers = product.xpath(
            './/span[contains(@class, "vtex-product-price-1-x-currencyInteger--product-online-price")]/text()'
        ).getall()
        price_fraction = product.xpath(
            './/span[contains(@class, "vtex-product-price-1-x-currencyFraction--product-online-price")]/text()'
        ).get()

        online_price = None
        if price_integers:
            price_combined = "".join(price_integers)
            online_price = f"{price_combined}.{price_fraction}" if price_fraction else price_combined

        regular_price = None
        if discount_elem:
            regular_price_text = product.xpath(
                './/span[contains(@class, "wongio-store-theme-7-x-span-ref-value")]/text()'
            ).get()
            if regular_price_text:
                regular_price = (
                    regular_price_text.strip()
                    .replace("S/", "")
                    .replace("\xa0", "")
                    .replace(" ", "")
                )

        product_id = product.xpath("./@data-af-product-id").get()

        item = ProductItem()
        item["product_id"] = f"{self.store_id}_{product_id}"
        item["store_id"] = self.store_id
        item["product_name"] = name.strip() if name else None
        item["category_id"] = category_id
        item["regular_price"] = float(regular_price) if regular_price else None
        item["online_price"] = float(online_price) if online_price else None
        item["discount_percentage"] = int(discount) if discount and discount.isdigit() else None
        item["currency"] = "PEN"
        item["product_url"] = f"https://www.wong.pe{product_url}" if product_url else None

        return item

    async def errback_close_page(self, failure):
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"Request failed: {failure}")
