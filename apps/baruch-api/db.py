import mysql.connector


def get_connection() -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='Peru123.,',
        database='presio',
    )
