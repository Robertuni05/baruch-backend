from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import get_connection
from routes.products import router as products_router, canonical_cache

app = FastAPI(title="Presio API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://comprainteligente-cg7n.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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
