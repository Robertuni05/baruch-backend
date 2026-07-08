from fastapi import APIRouter, HTTPException, Query
from rapidfuzz.fuzz import token_sort_ratio
from db import get_connection

router = APIRouter(prefix="/api/products")

# Loaded once at startup by main.py — list of (id, name) tuples
canonical_cache: list = []


@router.get("/search")
def search(q: str = Query(..., min_length=2), limit: int = Query(5, ge=1, le=20)):
    scored = [
        {"id": id, "name": name, "score": round(token_sort_ratio(q, name) / 100, 2)}
        for id, name in canonical_cache
    ]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


@router.get("/{canonical_id}/compare")
def compare(canonical_id: int):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM canonical_product WHERE id = %s", (canonical_id,))
    canonical = cur.fetchone()
    if not canonical:
        raise HTTPException(status_code=404, detail="Product not found")

    cur.execute("""
        SELECT
            s.name        AS store,
            p.name        AS product_name,
            p.regular_price,
            p.online_price,
            p.discount_pct,
            p.currency,
            p.url
        FROM product p
        JOIN store s ON s.id = p.store_id
        WHERE p.canonical_id = %s
          AND p.match_status = 'auto_matched'
        ORDER BY p.online_price ASC
    """, (canonical_id,))

    listings = [
        {
            "store":         row[0],
            "product_name":  row[1],
            "regular_price": row[2],
            "online_price":  row[3],
            "discount_pct":  row[4],
            "currency":      row[5],
            "url":           row[6],
        }
        for row in cur.fetchall()
    ]

    cur.close()
    conn.close()

    return {
        "canonical_id": canonical[0],
        "name":         canonical[1],
        "listings":     listings,
    }
