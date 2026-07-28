import os

import mysql.connector


def get_connection() -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(
        host=os.getenv('BARUCH_DB_HOST', 'localhost'),
        user=os.getenv('BARUCH_DB_USER', 'root'),
        password=os.getenv('BARUCH_DB_PASSWORD', 'Peru123.,'),
        database=os.getenv('BARUCH_DB_NAME', 'presio'),
    )
