import scrapy
from scrapy.http import HtmlResponse


class HumeSpider(scrapy.Spider):
    name = "hume"
    # custom_settings = {
    #     'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 30000,  # 30 seconds
    #     'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
    # }

    def start_requests(self):
        url = "https://www.wong.pe/mascotas/para-gatos"
        self.logger.info(f"********* URL: {url}")
        yield scrapy.Request(
            url=url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    ("wait_for_load_state", "networkidle"),
                ]
            },
            callback=self.parse
        )

    async def parse(self, response):
        
        # Check if playwright_page is available before using it
        page = response.meta.get("playwright_page")
        if page:
            await page.wait_for_load_state('networkidle')
            # Additional wait to ensure all dynamic content is loaded
            await page.wait_for_timeout(9000)
            self.logger.info("Network idle achieved and additional wait completed")
        else:
            self.logger.warning("Playwright page not available, proceeding without network idle wait")
        
        
        """Extract all products from the page using XPath selectors"""

        # Find all product containers
        products = response.xpath(
            '//div[contains(@class, "wongio-cmedia-integration-cencosud-1-x-galleryItem")]')

        self.logger.info(f'Found {len(products)} products on the page')

        for idx, product in enumerate(products, 1):
            # Product name
            name = product.xpath(
                './/span[contains(@class, "vtex-product-summary-2-x-productBrand")]/text()').get()

            # Product URL
            product_url = product.xpath(
                './/a[contains(@class, "vtex-product-summary-2-x-clearLink")]/@href').get()

            # Discount - check if exists
            discount_elem = product.xpath(
                './/span[contains(@class, "vtex-product-price-1-x-savingsPercentage")]/text()').get()
            has_discount = discount_elem is not None and discount_elem.strip() != ''

            # Extract discount percentage
            discount = discount_elem.strip().replace('%', '') if discount_elem else None

            # Online price
            price_integer = product.xpath(
                './/span[contains(@class, "vtex-product-price-1-x-currencyInteger--product-online-price")]/text()').get()
            price_fraction = product.xpath(
                './/span[contains(@class, "vtex-product-price-1-x-currencyFraction--product-online-price")]/text()').get()
            online_price = f"{price_integer}.{price_fraction}" if price_integer and price_fraction else None

            # Regular price (only if discount exists)
            regular_price = None
            if has_discount:
                regular_price_text = product.xpath(
                    './/span[contains(@class, "wongio-store-theme-7-x-span-ref-value")]/text()').get()
                if regular_price_text:
                    regular_price = regular_price_text.strip().replace(
                        'S/', '').replace('\xa0', '').replace(' ', '').strip()

            # Product ID
            product_id = product.xpath('./@data-af-product-id').get()

            # Calculate savings amount
            savings_amount = None
            if has_discount and regular_price and online_price:
                try:
                    reg = float(regular_price.replace(',', '.'))
                    sale = float(online_price.replace(',', '.'))
                    savings_amount = round(reg - sale, 2)
                except Exception as e:
                    self.logger.error(f'Error calculating savings: {e}')

            result = {
                'position': idx,
                'product_id': product_id,
                'product_name': name.strip() if name else None,
                'product_url': f"https://www.wong.pe{product_url}" if product_url else None,
                'has_discount': has_discount,
                'discount_percentage': int(discount) if discount and discount.isdigit() else None,
                'online_price': online_price,
                'regular_price': regular_price,
                'savings_amount': savings_amount
            }

            self.logger.info(
                f'Product {idx}: {name} - Discount: {discount}%'
                if has_discount
                else f'Product {idx}: {name} - No discount'
            )

            yield result
