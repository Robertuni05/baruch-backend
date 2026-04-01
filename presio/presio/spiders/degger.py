import scrapy
from scrapy_playwright.page import PageMethod
from presio.items import ProductItem
import random


class Degger(scrapy.Spider):
    name = "degger"

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    def __init__(self, max_pages=None, *args, **kwargs):
        super(Degger, self).__init__(*args, **kwargs)
        self.max_pages = int(max_pages) if max_pages else None
        self.pages_scraped = 0

    def start_requests(self):
        url = "https://www.wong.pe/ninos-y-bebes"
        self.logger.info(f"********* Starting URL: {url}")

        yield scrapy.Request(
            url=url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_context_kwargs": {
                    "user_agent": random.choice(self.user_agents),
                    "viewport": {"width": 1920, "height": 1080},
                },
            },
            callback=self.parse_with_scroll,
            errback=self.errback_close_page,
        )

    async def parse_with_scroll(self, response):
        page = response.meta["playwright_page"]
        self.pages_scraped += 1

        try:
            self.logger.info(f"{'='*60}")
            self.logger.info(f"PROCESSING PAGE #{self.pages_scraped}")
            self.logger.info(f"URL: {response.url}")
            self.logger.info(f"{'='*60}")

            # Wait for initial load
            await page.wait_for_timeout(3000)

            # Scroll to load all products
            final_count = await self._scroll_and_load_products(page)

            # Get the final HTML
            content = await page.content()
            response = response.replace(body=content)

            # Extract and yield products
            products_count = self._extract_products(response)

            self.logger.info(f"✓ Extracted {products_count} products from page #{self.pages_scraped}")

            # Follow next page if it exists
            self._follow_next_page(response)

        except Exception as e:
            self.logger.error(f"✗ Error on page #{self.pages_scraped}: {e}")
        finally:
            await page.close()

    async def _scroll_and_load_products(self, page):
        """Scroll the page to load all products"""
        previous_product_count = 0
        scroll_attempts = 0
        max_scrolls = 5
        no_change_count = 0
        no_change_limit = 2

        self.logger.info("Starting scroll loop...")

        while scroll_attempts < max_scrolls:
            current_product_count = await page.evaluate(
                """() => {
                    return document.querySelectorAll('[data-af-element="search-result"]').length;
                }"""
            )

            self.logger.info(f"  Scroll #{scroll_attempts + 1}: {current_product_count} products")

            if current_product_count == previous_product_count:
                no_change_count += 1
                if no_change_count >= no_change_limit:
                    self.logger.info(f"  No new products after {no_change_limit} scrolls")
                    break
            else:
                no_change_count = 0

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(4000)

            previous_product_count = current_product_count
            scroll_attempts += 1

        final_count = await page.evaluate(
            """() => {
                return document.querySelectorAll('[data-af-element="search-result"]').length;
            }"""
        )
        
        self.logger.info(f"  Final: {final_count} products loaded")
        return final_count

    def _extract_products(self, response):
        """Extract all products from the page"""
        products_ref = response.xpath(
            '//div[contains(@class, "wongio-cmedia-integration-cencosud-1-x-galleryItem")]'
        )

        for idx, product_ref in enumerate(products_ref, 1):
            try:
                product_item = self.generate_product(product_ref)
                # Add page counter (optional)
                product_item["page_scraped"] = self.pages_scraped
                yield product_item
            except Exception as e:
                self.logger.error(f"Error extracting product {idx}: {e}")

        #return len(products_ref)
        return 3

    def _follow_next_page(self, response):
        """Extract next page URL from HTML and follow it"""
        
        # Extract next page link from HTML
        # next_page = response.xpath("//link[@rel='next']/@href").get()
        next_page = response.css("link[rel='next']").href
        self.logger.info(f"✓ Next page found: {next_page}")
        
        if next_page:
            self.logger.info(f"✓ Next page found: {next_page}")
            
            # Check if we should continue
            if self.max_pages is None or self.pages_scraped < self.max_pages:
                self.logger.info(f"→ Following next page (scraped: {self.pages_scraped}/{self.max_pages or '∞'})")
                
                yield scrapy.Request(
                    url=response.urljoin(next_page),  # ✓ Handle relative URLs
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_context_kwargs": {
                            "user_agent": random.choice(self.user_agents),
                            "viewport": {"width": 1920, "height": 1080},
                        },
                    },
                    callback=self.parse_with_scroll,
                    errback=self.errback_close_page,
                )
            else:
                self.logger.info(f"✗ Reached max_pages limit ({self.max_pages})")
        else:
            self.logger.info(f"✗ No next page found. Finished scraping.")

    def generate_product(self, product):
        """Extract product data from product element"""
        
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

        product_item = ProductItem()
        product_item["product_id"] = product_id
        product_item["product_name"] = name.strip() if name else None
        product_item["regular_price"] = float(regular_price) if regular_price else None
        product_item["online_price"] = float(online_price) if online_price else None
        product_item["discount_percentage"] = (
            int(discount) if discount and discount.isdigit() else None
        )
        product_item["product_url"] = (
            f"https://www.wong.pe{product_url}" if product_url else None
        )

        return product_item

    async def errback_close_page(self, failure):
        """Handle errors"""
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()
        self.logger.error(f"Request failed: {failure}")