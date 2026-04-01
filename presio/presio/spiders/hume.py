import scrapy
from scrapy_playwright.page import PageMethod
from presio.items import ProductItem
import random


class HumeSpider(scrapy.Spider):
    name = "hume"
    
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    def start_requests(self):
        url = "https://www.wong.pe/carnes-aves-y-pescados"
        self.logger.info(f"********* URL: {url}")
        yield scrapy.Request(
            url=url,
            meta={
                "playwright": True,
                "playwright_context_kwargs":{
                    "user_agent": random.choice(self.user_agents)
                },
                "playwright_page_methods": [
                    PageMethod("wait_for_timeout", 5000),
                    PageMethod(
                        "evaluate", "window.scrollBy(0, document.body.scrollHeight)"
                    )
                ],
            },
            callback=self.parse,
        )

    # Passing callable objects
    # async def scroll_page(page: Page) -> str:
    #     await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
    #     return page.url

    def parse(self, response):
        """Extract all products from the page using XPath selectors"""

        # Find all product containers
        products = response.xpath(
            '//div[contains(@class, "wongio-cmedia-integration-cencosud-1-x-galleryItem")]'
        )

        self.logger.info(f"********** Found {len(products)} products on the page")

        for idx, product in enumerate(products, 1):
            # Product name
            name = product.xpath(
                './/span[contains(@class, "vtex-product-summary-2-x-productBrand")]/text()'
            ).get()

            # Product URL
            product_url = product.xpath(
                './/a[contains(@class, "vtex-product-summary-2-x-clearLink")]/@href'
            ).get()

            # Discount - check if exists
            discount_elem = product.xpath(
                './/span[contains(@class, "vtex-product-price-1-x-savingsPercentage")]/text()'
            ).get()
            has_discount = discount_elem is not None and discount_elem.strip() != ""

            # Extract discount percentage
            discount = discount_elem.strip().replace("%", "") if discount_elem else None

            # Online price
            price_integer = product.xpath(
                './/span[contains(@class, "vtex-product-price-1-x-currencyInteger--product-online-price")]/text()'
            ).get()
            price_fraction = product.xpath(
                './/span[contains(@class, "vtex-product-price-1-x-currencyFraction--product-online-price")]/text()'
            ).get()
            online_price = (
                f"{price_integer}.{price_fraction}"
                if price_integer and price_fraction
                else None
            )

            # Regular price (only if discount exists)
            regular_price = None
            if has_discount:
                regular_price_text = product.xpath(
                    './/span[contains(@class, "wongio-store-theme-7-x-span-ref-value")]/text()'
                ).get()
                if regular_price_text:
                    regular_price = (
                        regular_price_text.strip()
                        .replace("S/", "")
                        .replace("\xa0", "")
                        .replace(" ", "")
                        .strip()
                    )

            # Product ID
            product_id = product.xpath("./@data-af-product-id").get()

            product_item = ProductItem()
            product_item["product_id"] = product_id
            product_item["product_name"] = name.strip() if name else None
            product_item["regular_price"] = (
                float(regular_price) if regular_price else None
            )
            product_item["online_price"] = (
                float(online_price) if regular_price else None
            )
            product_item["discount_percentage"] = (
                int(discount) if discount and discount.isdigit() else None
            )
            product_item["product_url"] = (
                f"https://www.wong.pe{product_url}" if product_url else None
            )

            yield product_item

        next_page = response.xpath("//link[@rel='next']/@href").get()
        self.logger.info(f"**********next page is {next_page}")

        # if next_page is not None:
        #     yield scrapy.Request(
        #         url=next_page,
        #         meta={
        #             "playwright": True,
        #             'playwright_page_methods': [
        #                 # Wait for initial page load
        #                 PageMethod('wait_for_timeout', 2000),
        #                 # More aggressive scrolling pattern for pages with more content
        #                 PageMethod('evaluate', 'window.scrollTo(0, document.body.scrollHeight)'),
        #                 PageMethod('wait_for_timeout', 4000),
        #                 PageMethod('evaluate', 'window.scrollTo(0, document.body.scrollHeight)'),
        #                 PageMethod('wait_for_timeout', 4000),
        #                 PageMethod('evaluate', 'window.scrollTo(0, document.body.scrollHeight)'),
        #                 PageMethod('wait_for_timeout', 4000),
        #                 PageMethod('evaluate', 'window.scrollTo(0, document.body.scrollHeight)'),
        #                 PageMethod('wait_for_timeout', 4000),
        #                 PageMethod('evaluate', 'window.scrollTo(0, document.body.scrollHeight)'),
        #                 PageMethod('wait_for_timeout', 4000),
        #                 # Additional scrolls to ensure all content is loaded
        #                 PageMethod('evaluate', 'window.scrollTo(0, document.body.scrollHeight)'),
        #                 PageMethod('wait_for_timeout', 3000),
        #                 PageMethod('evaluate', 'window.scrollTo(0, document.body.scrollHeight)'),
        #                 PageMethod('wait_for_timeout', 3000),
        #                 # Final scroll and wait
        #                 PageMethod('evaluate', 'window.scrollTo(0, document.body.scrollHeight)'),
        #                 PageMethod('wait_for_timeout', 5000),
        #             ],
        #         },
        #         callback=self.parse
        #     )
