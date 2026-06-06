"""
Post-scrape processing pipeline.

Runs normalize then score in order.

Usage (from presio-scrapy-batch/ directory):
    conda run -n presio python -m processing.run_pipeline
"""
import mysql.connector
from processing.normalize.run_normalize import run as normalize
from processing.score.run_score import run as score


def get_connection() -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='Peru123.,',
        database='presio',
    )


if __name__ == "__main__":
    conn = get_connection()
    try:
        print("=== Step 1: Normalize ===")
        normalize(conn)

        print("\n=== Step 2: Score ===")
        score(conn)

        print("\nPipeline complete.")
    finally:
        conn.close()
