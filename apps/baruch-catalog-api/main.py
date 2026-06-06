from fastapi import FastAPI
from db import get_connection
from routes.products import router as products_router, canonical_cache

app = FastAPI(title="Presio API", version="0.1.0")
app.include_router(products_router)


@app.on_event("startup")
def load_canonical_cache():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM canonical_product")
    canonical_cache.extend(cur.fetchall())
    cur.close()
    conn.close()
    print(f"Cache loaded — {len(canonical_cache)} canonical products ready.")
