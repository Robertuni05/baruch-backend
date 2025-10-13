import scrapy
from scrapy.utils.log import logger

class HumeSpider(scrapy.Spider):
    name = "hume"
    
    def start_requests(self):
        url = "https://www.wong.pe/hervidor%20thomas%20th-5408i%202200w%201.8l%20cuerpo%20acero%20inoxidable?_q=Hervidor%20Thomas%20TH-5408I%202200W%201.8L%20Cuerpo%20Acero%20Inoxidable&map=ft"
        self.logger.info(f"********* URL: {url}")
        yield scrapy.Request(
            url=url,
            meta={"playwright": True},  # Enable JS rendering
            callback=self.parse
        )

    async def parse(self, response):
        string_selector = "//span[@class='vtex-product-price-1-x-savingsPercentage vtex-product-price-1-x-savingsPercentage--discountInsideContainer']"
        selector_1 = response.xpath(string_selector)
        value_string = selector_1.getall()
        
        [print("************", e) for e in value_string]
        
        yield {"product": "value_string"}
