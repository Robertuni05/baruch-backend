# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import mysql.connector
from itemadapter import ItemAdapter
from datetime import datetime
import logging


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
        self.logger = logging.getLogger(__name__)

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        try:
            # Use INSERT IGNORE to prevent integrity key errors
            # This will silently skip duplicate records based on primary key
            self.cur.execute("""
                INSERT IGNORE INTO product (
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
            
            # Log if the record was actually inserted
            if self.cur.rowcount > 0:
                self.logger.info(f"Inserted new product: {item['product_id']}")
            else:
                self.logger.info(f"Product already exists, skipped: {item['product_id']}")
                
        except mysql.connector.Error as e:
            self.logger.error(f"Database error for product {item['product_id']}: {e}")
            # Don't re-raise the exception to continue processing other items
            
        return item

    def close_spider(self, spider):
        self.cur.close()
        self.conn.close()
