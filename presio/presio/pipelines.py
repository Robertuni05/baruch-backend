import mysql.connector
from itemadapter import ItemAdapter
import logging
from datetime import datetime


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
        now = datetime.now()
        try:
            self.cur.execute("""
                INSERT INTO product (
                    id,
                    store_id,
                    name,
                    category_id,
                    regular_price,
                    online_price,
                    discount_pct,
                    currency,
                    created_at,
                    updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name         = VALUES(name),
                    category_id  = VALUES(category_id),
                    regular_price= VALUES(regular_price),
                    online_price = VALUES(online_price),
                    discount_pct = VALUES(discount_pct),
                    currency     = VALUES(currency),
                    updated_at   = VALUES(updated_at)
            """, (
                item['product_id'],
                item['store_id'],
                item['product_name'],
                item.get('category_id'),
                item.get('regular_price'),
                item.get('online_price'),
                item.get('discount_percentage'),
                item.get('currency', 'PEN'),
                now,
                now,
            ))
            self.conn.commit()

            if self.cur.rowcount == 1:
                self.logger.info(f"Inserted product: {item['product_id']}")
            else:
                self.logger.info(f"Updated product: {item['product_id']}")

        except mysql.connector.Error as e:
            self.logger.error(f"Database error for product {item['product_id']}: {e}")

        return item

    def close_spider(self, spider):
        self.cur.close()
        self.conn.close()
