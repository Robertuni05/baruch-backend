# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import mysql.connector
from itemadapter import ItemAdapter
from datetime import datetime


class PresioPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        # add PRODUCT sufix
        # field_names = adapter.field_names()
        adapter['name'] = 'Producto ' + adapter.get('name')

        return item


class SaveProductPipeline:

    def __init__(self):
        self.conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Peru123.,',
            database='presio'
        )

        self.cur = self.conn.cursor()
        # self.cur.execute(""" """)

    from datetime import datetime

    def process_item(self, item, spider):
        current_date = datetime.now()  # Get the current date/time

        self.cur.execute("""
            INSERT INTO product (
                id, 
                name, 
                categoryid,
                price,
                priceonline,
                pricecurrency,
                discount,
                updatedate
            ) VALUES (
                %s, 
                %s, 
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                categoryid = VALUES(categoryid),
                price = VALUES(price),
                priceonline = VALUES(priceonline),
                pricecurrency = VALUES(pricecurrency),
                discount = VALUES(discount),
                updatedate = NOW()
            """, (
            item['id'],
            item['name'],
            1,
            item['price'],
            item.get('priceonline', None),
            item.get('pricecurrency', None),
            item.get('discount', None),
            current_date
        ))

        self.conn.commit()
        return item

    def close_spider(self, spider):
        self.cur.close()
        self.conn.close()
