from pathlib import Path

import scrapy


class WongSpider(scrapy.Spider):
    name = "otherspider"
    url = "https://www.wong.pe/hogar-y-bazar?initialMap=c&initialQuery=hogar-y-bazar&map=category-1,category-2&query=/hogar-y-bazar/halloween&searchState"

    def start_requests(self):
        yield scrapy.Request(
            self.url,
            meta={"playwright": True},  # Enable JS rendering
            callback=self.parse
        )

    async def parse(self, response):
        # Extract JSON
        json_id = response.xpath("//script[@type='application/ld+json']")

        for i in json_id.getall():
            print('******************'+str(i))
