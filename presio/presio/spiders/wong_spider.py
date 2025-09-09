import scrapy
import json
import re
from scrapy.utils.log import logger
from urllib.parse import urljoin


class WongSpider(scrapy.Spider):
    name = "wong"
    allowed_domains = ["www.wong.pe"]
    host = "www.wong.pe"
    base_path = "limpieza"
    params = "initialMap=ft&initialQuery=limpieza&map=brand,ft&operator=and&query=/ariel/limpieza&searchState"

    custom_settings = {
        'ITEM_PIPELINES': {
            'presio.pipelines.PresioPipeline': 300,
            'presio.pipelines.JsonWriterPipeline': 400,
        }
    }

    def start_requests(self):
        """Generate initial requests for the spider."""
        url = f"https://{self.host}/{self.base_path}?{self.params}"
        self.logger.info(f"Starting scrape for URL: {url}")
        
        yield scrapy.Request(
            url=url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_page_methods": [
                    ("wait_for_selector", "script[type='application/ld+json']"),
                    ("wait_for_timeout", 3000),  # Wait for dynamic content
                ]
            },
            callback=self.parse,
            errback=self.handle_error
        )

    def parse(self, response):
        """Parse the main page and extract product information."""
        try:
            # Extract JSON-LD structured data
            json_scripts = response.xpath("//script[@type='application/ld+json']/text()").getall()
            
            if not json_scripts:
                self.logger.warning("No JSON-LD scripts found on the page")
                return
            
            # Process each JSON-LD script
            for script_content in json_scripts:
                try:
                    data = json.loads(script_content.strip())
                    yield from self.extract_products_from_json(data, response)
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse JSON-LD: {e}")
                    continue
            
            # Extract products from HTML if JSON-LD doesn't contain products
            yield from self.extract_products_from_html(response)
            
            # Follow pagination links
            yield from self.follow_pagination(response)
            
        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")

    def extract_products_from_json(self, data, response):
        """Extract product information from JSON-LD structured data."""
        if isinstance(data, dict):
            # Check if it's a product or contains products
            if data.get('@type') == 'Product':
                yield self.create_product_item(data, response.url)
            elif 'itemListElement' in data:
                for item in data['itemListElement']:
                    if isinstance(item, dict) and item.get('@type') == 'Product':
                        yield self.create_product_item(item, response.url)
        elif isinstance(data, list):
            for item in data:
                yield from self.extract_products_from_json(item, response)

    def extract_products_from_html(self, response):
        """Extract product information from HTML elements."""
        # Extract product containers
        product_selectors = [
            '.vtex-product-summary-2-x-container',
            '.vtex-search-result-3-x-galleryItem',
            '[data-testid="product-summary"]',
            '.product-item',
            '.product-card'
        ]
        
        products = []
        for selector in product_selectors:
            products = response.css(selector)
            if products:
                break
        
        for product in products:
            try:
                item_data = {
                    'name': self.extract_text(product, [
                        '.vtex-product-summary-2-x-productNameContainer a::text',
                        '.product-name::text',
                        'h3::text',
                        '.title::text'
                    ]),
                    'price': self.extract_price(product),
                    'image_url': self.extract_image_url(product, response),
                    'product_url': self.extract_product_url(product, response),
                    'brand': self.extract_text(product, [
                        '.vtex-product-summary-2-x-brandName::text',
                        '.brand::text'
                    ]),
                    'availability': self.extract_availability(product),
                }
                
                if item_data['name']:  # Only yield if we have at least a name
                    from presio.items import ProductItem
                    item = ProductItem()
                    for key, value in item_data.items():
                        item[key] = value
                    item['source_url'] = response.url
                    item['spider_name'] = self.name
                    yield item
                    
            except Exception as e:
                self.logger.error(f"Error extracting product from HTML: {e}")

    def extract_text(self, selector, css_selectors):
        """Extract text using multiple CSS selectors as fallbacks."""
        for css_sel in css_selectors:
            text = selector.css(css_sel).get()
            if text:
                return text.strip()
        return None

    def extract_price(self, product):
        """Extract price information from product element."""
        price_selectors = [
            '.vtex-product-price-1-x-sellingPrice::text',
            '.vtex-store-components-3-x-sellingPrice::text',
            '.price::text',
            '.selling-price::text',
            '[data-testid="price"]::text'
        ]
        
        price_text = self.extract_text(product, price_selectors)
        if price_text:
            # Extract numeric price using regex
            price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
            if price_match:
                try:
                    return float(price_match.group().replace(',', ''))
                except ValueError:
                    pass
        return None

    def extract_image_url(self, product, response):
        """Extract product image URL."""
        img_selectors = [
            '.vtex-product-summary-2-x-imageContainer img::attr(src)',
            '.product-image img::attr(src)',
            'img::attr(src)'
        ]
        
        img_url = self.extract_text(product, img_selectors)
        if img_url:
            return urljoin(response.url, img_url)
        return None

    def extract_product_url(self, product, response):
        """Extract product detail page URL."""
        url_selectors = [
            '.vtex-product-summary-2-x-clearLink::attr(href)',
            'a::attr(href)',
            '[data-testid="product-link"]::attr(href)'
        ]
        
        product_url = self.extract_text(product, url_selectors)
        if product_url:
            return urljoin(response.url, product_url)
        return None

    def extract_availability(self, product):
        """Extract product availability status."""
        availability_selectors = [
            '.vtex-product-summary-2-x-availabilityContainer::text',
            '.availability::text',
            '.stock-status::text'
        ]
        
        availability = self.extract_text(product, availability_selectors)
        if availability:
            availability_lower = availability.lower()
            if 'disponible' in availability_lower or 'available' in availability_lower:
                return 'in_stock'
            elif 'agotado' in availability_lower or 'out of stock' in availability_lower:
                return 'out_of_stock'
        return 'unknown'

    def create_product_item(self, product_data, source_url):
        """Create a product item from JSON-LD data."""
        from presio.items import ProductItem
        
        item = ProductItem()
        item['name'] = product_data.get('name', '')
        item['brand'] = product_data.get('brand', {}).get('name', '') if isinstance(product_data.get('brand'), dict) else product_data.get('brand', '')
        item['source_url'] = source_url
        item['spider_name'] = self.name
        
        # Extract price from offers
        offers = product_data.get('offers', {})
        if isinstance(offers, dict):
            item['price'] = offers.get('price') or offers.get('lowPrice')
            item['availability'] = 'in_stock' if offers.get('availability') == 'InStock' else 'unknown'
        elif isinstance(offers, list) and offers:
            item['price'] = offers[0].get('price') or offers[0].get('lowPrice')
            item['availability'] = 'in_stock' if offers[0].get('availability') == 'InStock' else 'unknown'
        
        # Extract image
        image = product_data.get('image')
        if isinstance(image, list) and image:
            item['image_url'] = image[0] if isinstance(image[0], str) else image[0].get('url')
        elif isinstance(image, str):
            item['image_url'] = image
        elif isinstance(image, dict):
            item['image_url'] = image.get('url')
        
        item['product_url'] = product_data.get('url', '')
        
        return item

    def follow_pagination(self, response):
        """Follow pagination links to scrape additional pages."""
        # Look for next page links
        next_page_selectors = [
            '.vtex-search-result-3-x-showingProductsCount + a::attr(href)',
            '.pagination .next::attr(href)',
            '[aria-label="Next"]::attr(href)',
            '.next-page::attr(href)'
        ]
        
        for selector in next_page_selectors:
            next_page = response.css(selector).get()
            if next_page:
                next_url = urljoin(response.url, next_page)
                self.logger.info(f"Following pagination: {next_url}")
                yield scrapy.Request(
                    url=next_url,
                    meta={
                        "playwright": True,
                        "playwright_include_page": True,
                        "playwright_page_methods": [
                            ("wait_for_selector", "script[type='application/ld+json']"),
                            ("wait_for_timeout", 3000),
                        ]
                    },
                    callback=self.parse,
                    errback=self.handle_error
                )
                break

    def handle_error(self, failure):
        """Handle request errors."""
        self.logger.error(f"Request failed: {failure.value}")
        # You could implement retry logic here if needed
