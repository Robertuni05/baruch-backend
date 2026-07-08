"""
Canonicalization + matching, one category at a time.

For every unmatched product in a category, compare it against the other unmatched
products in that same category by plain name similarity. The first product in a
matching group founds a new canonical (self-match, score 1.0); every other product
that scores high enough against it attaches to that same canonical.

canonical_product has no list of product ids — the link is one-directional, stored on
product (canonical_id, match_score, match_status, matched_at).

Usage:
    conda run -n presio python -m match.run_match
"""
from rapidfuzz import fuzz

from db import get_connection

AUTO_MATCH_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.65


def _create_canonical(cur, name: str, category_id: int) -> int:
    cur.execute(
        "INSERT INTO canonical_product (name, category_id) VALUES (%s, %s)",
        (name, category_id),
    )
    return cur.lastrowid


def _set_product_match(cur, product_id: str, store_id: int, canonical_id: int, score: float, status: str) -> None:
    cur.execute("""
        UPDATE product
        SET canonical_id = %s, match_score = %s, match_status = %s, matched_at = NOW()
        WHERE id = %s AND store_id = %s
    """, (canonical_id, score, status, product_id, store_id))


def run_category(conn, category_id: int) -> None:
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT id, store_id, name FROM product WHERE category_id = %s AND canonical_id IS NULL",
        (category_id,),
    )
    products = cur.fetchall()
    for product in products:
        product['canonical_id'] = None  # tracked in-memory only; not fetched from DB

    for product_a in products:
        if product_a['canonical_id'] is not None:
            continue  # already folded into another product's canonical this pass

        canonical_id = None

        for product_b in products:
            if product_b is product_a or product_b['canonical_id'] is not None:
                continue

            score = fuzz.token_sort_ratio(product_a['name'], product_b['name']) / 100.0
            if score < REVIEW_THRESHOLD:
                continue

            if canonical_id is None:
                canonical_id = _create_canonical(cur, product_a['name'], category_id)
                _set_product_match(cur, product_a['id'], product_a['store_id'], canonical_id, 1.0, 'auto_matched')
                product_a['canonical_id'] = canonical_id

            status = 'auto_matched' if score >= AUTO_MATCH_THRESHOLD else 'needs_review'
            _set_product_match(cur, product_b['id'], product_b['store_id'], canonical_id, score, status)
            product_b['canonical_id'] = canonical_id

    conn.commit()
    cur.close()


def run_all_categories(conn) -> None:
    cur = conn.cursor()
    cur.execute("SELECT id FROM category")
    category_ids = [row[0] for row in cur.fetchall()]
    cur.close()

    for category_id in category_ids:
        run_category(conn, category_id)


if __name__ == "__main__":
    conn = get_connection()
    try:
        run_all_categories(conn)
    finally:
        conn.close()
