# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import mysql.connector
from itemadapter import ItemAdapter


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

        self.cur.execute(""" insert into product (
            id, 
            name, 
            categoryid,
            price
        ) values (
            %s, 
            %s, 
            %s,
            %s
        )""", (
            item['id'],
            item['name'],
            1,
            item['price']
        ))

        self.conn.commit()

        return item
    
    def close_spider(self, spider):
        self.cur.close()
        self.conn.close()
