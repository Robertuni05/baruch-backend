# Define here the models for your scraped items
import scrapy


class ProductItem(scrapy.Item):
    product_id = scrapy.Field()
    product_name = scrapy.Field()
    regular_price = scrapy.Field()
    online_price = scrapy.Field()
    discount_percentage = scrapy.Field()
    product_url = scrapy.Field()


class TestItem(scrapy.Item):
    field = scrapy.Field()


class HtmlPageItem(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    html_content = scrapy.Field()
    filename = scrapy.Field()
