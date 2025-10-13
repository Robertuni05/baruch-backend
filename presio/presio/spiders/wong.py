from curses import meta
import scrapy
import json
from scrapy.utils.log import logger
from presio.items import ProductItem
from presio.utils import Utils

class WongSpider(scrapy.Spider):
    name = "wong"

    def start_requests(self):
        url = "https://www.wong.pe/electrohogar"
        self.logger.info(f"********* URL: {url}")
        yield scrapy.Request(
            url=url,
            meta={"playwright": True},
            callback=self.parse
        )

    async def parse(self, response):
        
        string_selector = "//script[@type='application/ld+json']/text()"
        reponse_ = response.xpath(string_selector)
        value_string = reponse_.getall()
        print(f"******* value_string is {value_string}")
        json_products = json.loads(value_string[1])

        for e in json_products['itemListElement']:
            item = e['item']
            #print("********** ", item)
            product_item = ProductItem()
            product_item['id'] = Utils.genId(description=item['name'])
            product_item['name'] = item['name']
            offers_item = item['offers']
            product_item['price'] = offers_item['lowPrice']
            yield product_item

        next_page = response.xpath("//link[@rel='next']/@href").get()
        print(f"**********next page is {next_page}")

        # if next_page is not None:
        #     yield scrapy.Request(
        #         next_page,
        #         meta={"playwright": True},
        #         callback=self.parse
        #     )
