import mysql.connector
from rapidfuzz import fuzz
from processing.normalize.strategy import CanonicalizationStrategy
from processing.normalize.fuzzy_cluster_strategy import FuzzyClusterStrategy

SKIP_THRESHOLD = 0.92


def _already_exists(name: str, existing: list) -> bool:
    for existing_name in existing:
        score = fuzz.token_sort_ratio(name.lower(), existing_name.lower()) / 100.0
        if score >= SKIP_THRESHOLD:
            return True
    return False


def run(conn: mysql.connector.MySQLConnection, strategy: CanonicalizationStrategy = None):
    if strategy is None:
        strategy = FuzzyClusterStrategy()

    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT DISTINCT category_id FROM product WHERE canonical_id IS NULL")
    categories = [row['category_id'] for row in cur.fetchall()]

    cur.execute("SELECT name FROM canonical_product")
    existing_names = [row['name'] for row in cur.fetchall()]

    total_inserted = 0

    for category_id in categories:
        cur.execute(
            "SELECT name FROM product WHERE canonical_id IS NULL AND category_id = %s",
            (category_id,)
        )
        raw_names = [row['name'] for row in cur.fetchall() if row['name']]

        if not raw_names:
            continue

        canonical_names = strategy.canonicalize(raw_names)

        for name in canonical_names:
            if _already_exists(name, existing_names):
                continue
            cur.execute(
                "INSERT INTO canonical_product (name, category_id) VALUES (%s, %s)",
                (name, category_id)
            )
            existing_names.append(name)
            total_inserted += 1

    conn.commit()
    cur.close()
    print(f"Normalize done — {total_inserted} new canonical products inserted.")
