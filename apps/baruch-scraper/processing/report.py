"""
Read-only coverage report for the matching pipeline.

The headline metric is NOT "unmatched products" (the match loop mints a singleton
canonical for every non-match, so that count is always ~0). The metric that matters
for price comparison is how many canonicals are matched across >=2 stores — only
those can power the /compare endpoint.

Usage (from baruch-scraper/ directory):
    conda run -n presio python -m processing.report
"""
import mysql.connector


def run(conn: mysql.connector.MySQLConnection):
    cur = conn.cursor()

    cur.execute("SELECT store_id, COUNT(*) FROM product GROUP BY store_id ORDER BY store_id")
    per_store = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM product")
    total_products = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM canonical_product")
    total_canon = cur.fetchone()[0]

    print("=== Matching coverage report ===\n")
    print(f"products: {total_products}   canonicals: {total_canon}   "
          f"ratio: {total_products / total_canon:.2f} products/canonical")
    print("products per store:", {s: n for s, n in per_store})

    cur.execute("""
        SELECT stores_per_canonical, COUNT(*) FROM (
            SELECT canonical_id, COUNT(DISTINCT store_id) AS stores_per_canonical
            FROM product_match WHERE status = 'auto_matched'
            GROUP BY canonical_id
        ) t GROUP BY stores_per_canonical ORDER BY stores_per_canonical
    """)
    print("\nstores_per_canonical -> num_canonicals")
    for spc, n in cur.fetchall():
        print(f"  {spc}: {n}")

    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT canonical_id FROM product_match WHERE status = 'auto_matched'
            GROUP BY canonical_id HAVING COUNT(DISTINCT store_id) >= 2
        ) t
    """)
    comparable = cur.fetchone()[0]
    print(f"\nCOMPARABLE (>=2 stores): {comparable} / {total_canon} "
          f"({100 * comparable / total_canon:.1f}%)")

    cur.execute("""
        SELECT cp.category_id,
               COUNT(DISTINCT cp.id) AS canonicals,
               COUNT(DISTINCT CASE WHEN m.stores >= 2 THEN cp.id END) AS comparable
        FROM canonical_product cp
        LEFT JOIN (
            SELECT canonical_id, COUNT(DISTINCT store_id) AS stores
            FROM product_match WHERE status = 'auto_matched' GROUP BY canonical_id
        ) m ON m.canonical_id = cp.id
        GROUP BY cp.category_id ORDER BY cp.category_id
    """)
    print("\nper category: canonicals | comparable(>=2) | %")
    for cat, canon, comp in cur.fetchall():
        pct = 100 * comp / canon if canon else 0
        print(f"  cat {cat}: {canon} | {comp} | {pct:.1f}%")

    cur.close()


if __name__ == "__main__":
    conn = mysql.connector.connect(
        host='localhost', user='root', password='Peru123.,', database='presio')
    try:
        run(conn)
    finally:
        conn.close()
