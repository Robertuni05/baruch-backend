import scrapy
import json
import yaml
import os
from presio.items import ProductItem


CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config.yaml"))
PAGE_SIZE = 50


class PlazaVeaSpider(scrapy.Spider):
    name = "plazavea"
    store_id = 1

    def __init__(self, max_pages=None, category=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages) if max_pages else None

        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f)

        self.base_url = config["supermarkets"]["plazavea"]["base_url"]
        categories = config["categories"]

        if category:
            categories = [
                c for c in categories
                if c["name"].lower() == category.lower() or str(c["id"]) == str(category)
            ]

        self.category_urls = []
        for cat in categories:
            if "plazavea" not in cat["stores"]:
                continue
            for url in cat["stores"]["plazavea"]["urls"]:
                self.category_urls.append((url.lstrip("/"), cat["id"]))

    def start_requests(self):
        for slug, category_id in self.category_urls:
            url = self._build_api_url(slug, page=0)
            self.logger.info(f"Starting category: {slug}")
            yield scrapy.Request(
                url=url,
                callback=self.parse_products,
                meta={"slug": slug, "page": 0, "category_id": category_id},
            )

    def _build_api_url(self, slug, page):
        from_idx = page * PAGE_SIZE
        to_idx = from_idx + PAGE_SIZE - 1
        return f"{self.base_url}/api/catalog_system/pub/products/search/{slug}/?_from={from_idx}&_to={to_idx}"

    def parse_products(self, response):
        slug = response.meta["slug"]
        page = response.meta["page"]
        category_id = response.meta.get("category_id")

        products = json.loads(response.text)

        if not products:
            self.logger.info(f"✓ Category '{slug}' done — no more products")
            return

        self.logger.info(f"  Category '{slug}' page {page + 1}: {len(products)} products")

        for product in products:
            try:
                yield self.generate_product(product, category_id)
            except Exception as e:
                self.logger.error(f"Error extracting product {product.get('productId')}: {e}")

        if self.max_pages is None or page + 1 < self.max_pages:
            next_page = page + 1
            yield scrapy.Request(
                url=self._build_api_url(slug, next_page),
                callback=self.parse_products,
                meta={"slug": slug, "page": next_page, "category_id": category_id},
            )

    def generate_product(self, product, category_id=None):
        offer = product["items"][0]["sellers"][0]["commertialOffer"]

        online_price = offer.get("Price")
        list_price = offer.get("ListPrice")

        discount_percentage = None
        if list_price and online_price and list_price > online_price:
            discount_percentage = round((list_price - online_price) / list_price * 100)

        item = ProductItem()
        item["product_id"] = f"{self.store_id}_{product.get('productId')}"
        item["store_id"] = self.store_id
        item["product_name"] = product.get("productName")
        item["category_id"] = category_id
        item["regular_price"] = float(list_price) if list_price else None
        item["online_price"] = float(online_price) if online_price else None
        item["discount_percentage"] = discount_percentage
        item["currency"] = "PEN"
        item["product_url"] = product.get("link")

        return item
