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

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        self.cur.execute("""
            INSERT INTO product (
                id, 
                name, 
                regular_price,
                online_price,
                discount_pct,
                url,                
                category_id
            ) VALUES (
                %s, 
                %s, 
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """, (
            item['product_id'],
            item['product_name'],
            item['regular_price'],
            item['online_price'],
            item['discount_percentage'],
            item['product_url'],
            1,
        ))

        self.conn.commit()
        return item

    def close_spider(self, spider):
        self.cur.close()
        self.conn.close()
