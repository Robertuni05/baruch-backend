import scrapy
from scrapy.http import HtmlResponse
from scrapy_playwright.page import PageMethod
from presio.items import ProductItem


class HumeSpider(scrapy.Spider):
    name = "hume"

    def start_requests(self):
        url = "https://www.wong.pe/mascotas/para-gatos"
        self.logger.info(f"********* URL: {url}")
        yield scrapy.Request(
            url=url,
            meta={
                "playwright": True,
                'playwright_page_methods': [
                    # Scroll to load all products
                    PageMethod(
                        'evaluate', 'window.scrollTo(0, document.body.scrollHeight)'),
                    PageMethod('wait_for_timeout', 2000),  # Wait 2 seconds
                    PageMethod(
                        'evaluate', 'window.scrollTo(0, document.body.scrollHeight)'),
                    PageMethod('wait_for_timeout', 2000),
                    PageMethod(
                        'evaluate', 'window.scrollTo(0, document.body.scrollHeight)'),
                    PageMethod('wait_for_timeout', 2000),
                ],
            },
            callback=self.parse
        )

    async def parse(self, response):
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
            print(f"############### this is a product price {online_price}")
            product_item = ProductItem()
            product_item['product_id'] = product_id
            product_item['product_name'] = name.strip() if name else None
            product_item['regular_price'] = float(regular_price) if regular_price else None
            product_item['online_price'] = float(online_price) if regular_price else None
            product_item['discount_percentage'] = int(discount) if discount and discount.isdigit() else None
            product_item['product_url'] = f"https://www.wong.pe{product_url}" if product_url else None

            self.logger.info(
                f'Product {idx}: {name} - Discount: {discount}%'
                if has_discount
                else f'Product {idx}: {name} - No discount'
            )

            yield product_item
