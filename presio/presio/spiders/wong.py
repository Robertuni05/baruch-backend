from curses import meta
from re import S
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
            product_item = ProductItem()
            product_item['id'] = Utils.genId(description=item['name'])
            product_item['name'] = item['name']
            offers_item = item['offers']
            product_item['price'] = offers_item['lowPrice']
            product_item['discount']=self.get_discount_by_product_name(response, item['name'])
            yield product_item

        next_page = response.xpath("//link[@rel='next']/@href").get()
        print(f"**********next page is {next_page}")

        # if next_page is not None:
        #     yield scrapy.Request(
        #         next_page,
        #         meta={"playwright": True},
        #         callback=self.parse
        #     )

    def get_discount_by_product_name(self, response, product_name):
        """
        Get discount percentage for a specific product by its name
        
        Args:
            response: Scrapy response object
            product_name: Product name to search for (case-insensitive, partial match)
        
        Returns:
            str: Discount percentage (e.g., "15%") or None if not found
        """
        # Get all product containers
        products = response.xpath('//div[contains(@class, "wongio-cmedia-integration-cencosud-1-x-galleryItem")]')
        
        for product in products:
            # Get product name
            name = product.xpath('.//span[contains(@class, "vtex-product-summary-2-x-productBrand")]/text()').get()
            
            # Check if this is the product we're looking for (case-insensitive partial match)
            # if name and product_name.lower() in name.lower():
                
            #     # Strategy 1: Get discount from savingDiscount-container
            #     discount = product.xpath(
            #         './/div[contains(@class, "savingDiscount-container")]'
            #         '//span[contains(@class, "savingsPercentage--discountInsideContainer")]/text()'
            #     ).get()
                
            #     # Strategy 2: Get from any savingsPercentage span
            #     if not discount:
            #         discount = product.xpath(
            #             './/span[contains(@class, "savingsPercentage--discountInsideContainer")]/text()'
            #         ).get()
                
            #     # Strategy 3: Calculate from aria-label
            #     if not discount:
            #         aria_label = product.xpath(
            #             './/span[contains(@class, "vtex-product-price-1-x-savings--discountInsideContainer")]/@aria-label'
            #         ).get()
                    
            #         if aria_label:
            #             # Extract from "Precio de 649 por 549"
            #             import re
            #             numbers = re.findall(r'\d+', aria_label)
            #             if len(numbers) >= 2:
            #                 try:
            #                     regular = float(numbers[0])
            #                     online = float(numbers[1])
            #                     if regular > online:
            #                         discount_value = ((regular - online) / regular) * 100
            #                         discount = f"{int(discount_value)}%"
            #                 except (ValueError, ZeroDivisionError):
            #                     pass
                
            #     # Return discount (cleaned)
            #     return discount.strip() if discount else None

            print(f"#######These are products {name}")
        # Product not found
        return None
        