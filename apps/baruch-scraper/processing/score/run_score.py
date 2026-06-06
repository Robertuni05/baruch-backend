import mysql.connector
from rapidfuzz import fuzz

AUTO_MATCH_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.65


def run(conn: mysql.connector.MySQLConnection):
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id, name FROM canonical_product")
    canonicals = cur.fetchall()

    cur.execute("""
        SELECT id, store_id, name
        FROM product
        WHERE canonical_id IS NULL
    """)
    unmatched = cur.fetchall()

    print(f"Matching {len(unmatched)} products against {len(canonicals)} canonicals...")

    for product in unmatched:
        best_score = 0.0
        best_canonical = None

        for canonical in canonicals:
            score = fuzz.token_sort_ratio(product['name'].lower(), canonical['name'].lower()) / 100.0
            if score > best_score:
                best_score = score
                best_canonical = canonical

        if best_score >= AUTO_MATCH_THRESHOLD:
            status = 'auto_matched'
        elif best_score >= REVIEW_THRESHOLD:
            status = 'needs_review'
        else:
            continue

        cur.execute("""
            INSERT INTO product_match (canonical_id, product_id, store_id, similarity_score, status)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                similarity_score = VALUES(similarity_score),
                status           = VALUES(status),
                matched_at       = NOW()
        """, (best_canonical['id'], product['id'], product['store_id'], best_score, status))

        if status == 'auto_matched':
            cur.execute(
                "UPDATE product SET canonical_id = %s WHERE id = %s AND store_id = %s",
                (best_canonical['id'], product['id'], product['store_id'])
            )

    conn.commit()
    cur.close()
    print(f"Matching done.")
