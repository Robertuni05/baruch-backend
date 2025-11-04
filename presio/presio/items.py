# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html
import scrapy


class ProductItem(scrapy.Item):
    id = scrapy.Field()
    name = scrapy.Field()
    price = scrapy.Field()
    discount = scrapy.Field()


class TestItem(scrapy.Item):
    field = scrapy.Field()


class HtmlPageItem(scrapy.Item):
    url = scrapy.Field()
    title = scrapy.Field()
    html_content = scrapy.Field()
    filename = scrapy.Field()
