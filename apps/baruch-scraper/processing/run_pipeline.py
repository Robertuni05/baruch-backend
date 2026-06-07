"""
Post-scrape processing pipeline.

Single pass: match each unmatched product to an existing canonical, or mint a new
canonical when none fits. Replaces the former normalize + score two-step.

Usage (from baruch-scraper/ directory):
    conda run -n presio python -m processing.run_pipeline
"""
import mysql.connector
from processing.match.run_match import run as match


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
        print("=== Match (canonicalize + score) ===")
        match(conn)
        print("\nPipeline complete.")
    finally:
        conn.close()
