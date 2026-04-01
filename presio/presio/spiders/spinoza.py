import scrapy
from scrapy_playwright.page import PageMethod
from presio.items import ProductItem
import random


class SpinozaSpider(scrapy.Spider):
    name = "spinoza"

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def start_requests(self):
        url = "http://www.wong.pe/ninos-y-bebes?page=2"
        self.logger.info(f"********* URL: {url}")

        yield scrapy.Request(
            url=url,
            meta={
                "playwright": True,
                "playwright_include_page": True,  # IMPORTANT: We need page access
                "playwright_context_kwargs": {
                    "user_agent": random.choice(self.user_agents),
                    "viewport": {"width": 1920, "height": 1080},
                },
            },
            callback=self.parse_with_scroll,
        )
        
    async def parse_with_scroll(self, response):
        page = response.meta["playwright_page"]

        # Wait for initial load
        await page.wait_for_timeout(3000)

        previous_product_count = 0
        scroll_attempts = 0
        max_scrolls = 5
        no_change_count = 0
        no_change_limit = 1

        self.logger.info("Starting scroll loop to load all products...")

        while scroll_attempts < max_scrolls:
            # Count current products
            current_product_count = await page.evaluate(
                """() => {
                    return document.querySelectorAll('[data-af-element="search-result"]').length;
                }"""
            )

            self.logger.info(
                f"Scroll #{scroll_attempts + 1}: "
                f"Products on page: {current_product_count}"
            )

            # If no new products loaded in 2 consecutive scrolls, stop
            if current_product_count == previous_product_count:
                no_change_count += 1
                if no_change_count >= no_change_limit:
                    self.logger.info(
                        f"No new products after 2 scrolls. "
                        f"Stopping at {current_product_count} products"
                    )
                    break
            else:
                no_change_count = 0

            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # Wait for content to load (longer wait)
            await page.wait_for_timeout(4000)  # 4 seconds

            previous_product_count = current_product_count
            scroll_attempts += 1

        # Get final product count
        final_count = await page.evaluate(
            """() => {
                return document.querySelectorAll('[data-af-element="search-result"]').length;
            }"""
        )
        self.logger.info(f"Final product count after scrolling: {final_count}")

        # Get the final HTML
        content = await page.content()
        response = response.replace(body=content)

        # Close the page
        await page.close()

        """Extract all products from the page"""
        products_ref = response.xpath(
            '//div[contains(@class, "wongio-cmedia-integration-cencosud-1-x-galleryItem")]'
        )

        self.logger.info(f" Found {len(products_ref)} products on the page")

        for idx, product_ref in enumerate(products_ref, 1):
            product_item = self.generate_product(product_ref)           
            yield product_item
        
        next_page = response.xpath("//link[@rel='next']/@href").get()
        print(f"next page is {next_page}")
        
        if next_page is not None:
            yield scrapy.Request(
            url=next_page,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context_kwargs": {
                    "user_agent": random.choice(self.user_agents),
                    "viewport": {"width": 1920, "height": 1080},
                },
            },
            callback=self.parse_with_scroll,
        )
  
    def generate_product(self, product):
        
        # N
        name = product.xpath(
            './/span[contains(@class, "vtex-product-summary-2-x-productBrand")]/text()'
        ).get()
        
        # Product URL
        product_url = product.xpath(
            './/a[contains(@class, "vtex-product-summary-2-x-clearLink")]/@href'
        ).get()

        # Discount
        discount_elem = product.xpath(
            './/span[contains(@class, "vtex-product-price-1-x-savingsPercentage")]/text()'
        ).get()
        discount = discount_elem.strip().replace("%", "") if discount_elem else None

        # Online price - Get all integer parts
        price_integers = product.xpath(
            './/span[contains(@class, "vtex-product-price-1-x-currencyInteger--product-online-price")]/text()'
        ).getall()
        price_fraction = product.xpath(
            './/span[contains(@class, "vtex-product-price-1-x-currencyFraction--product-online-price")]/text()'
        ).get()

        online_price = None
        if price_integers:
            price_combined = "".join(price_integers)
            online_price = (
                f"{price_combined}.{price_fraction}"
                if price_fraction
                else price_combined
            )

        # Regular price
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

        # Product ID
        product_id = product.xpath("./@data-af-product-id").get()

        # Create item
        product_item = ProductItem()
        product_item["product_id"] = product_id
        product_item["product_name"] = name.strip() if name else None
        product_item["regular_price"] = (
            float(regular_price) if regular_price else None
        )
        product_item["online_price"] = float(online_price) if online_price else None
        product_item["discount_percentage"] = (
            int(discount) if discount and discount.isdigit() else None
        )
        product_item["product_url"] = (
            f"https://www.wong.pe{product_url}" if product_url else None
        )

        return product_item
    
