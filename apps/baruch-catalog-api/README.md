# presio-api

Read-only FastAPI service for Presio — searches and compares product prices across Peruvian supermarkets (Wong, Plaza Vea).

---

## Stack

- **Python 3.11**
- **FastAPI** — web framework
- **Uvicorn** — ASGI server
- **MySQL** — database (`presio` schema)
- **rapidfuzz** — fuzzy product name matching

---

## Setup

```bash
# From presio-api/ directory
pip install -r requirements.txt
```

Configure your database connection in `db.py` (host, user, password, database).

---

## Run

```bash
cd presio-api
uvicorn main:app --reload
```

Server starts at `http://localhost:8000`.

Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## Endpoints

### `GET /api/products/search`

Fuzzy-search canonical products by name.

**Query parameters**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q`       | string | yes | — | Search query (min 2 chars) |
| `limit`   | int    | no  | 5 | Max results (1–20) |

**Example**

```bash
curl "http://localhost:8000/api/products/search?q=leche&limit=5"
```

**Response**

```json
[
  { "id": 3, "name": "Leche Gloria Entera", "score": 0.91 },
  { "id": 7, "name": "Leche Ideal Cremosita", "score": 0.78 }
]
```

---

### `GET /api/products/{canonical_id}/compare`

Returns price listings for a canonical product across all stores (only `auto_matched` entries, ordered by online price ascending).

**Path parameters**

| Parameter      | Type | Description              |
|----------------|------|--------------------------|
| `canonical_id` | int  | ID from canonical_product table |

**Example**

```bash
curl "http://localhost:8000/api/products/3/compare"
```

**Response**

```json
{
  "canonical_id": 3,
  "name": "Leche Gloria Entera",
  "listings": [
    {
      "store": "Wong",
      "product_name": "Leche Gloria Entera 1L",
      "regular_price": 4.50,
      "online_price": 3.90,
      "discount_pct": 13.3,
      "currency": "PEN",
      "url": "https://wong.pe/..."
    },
    {
      "store": "Plaza Vea",
      "product_name": "Leche Gloria Entera x 1L",
      "regular_price": 4.70,
      "online_price": 4.10,
      "discount_pct": 12.8,
      "currency": "PEN",
      "url": "https://plazavea.com.pe/..."
    }
  ]
}
```

**404** — returned when `canonical_id` does not exist.

---

## Project Structure

```
presio-api/
├── main.py          # FastAPI app, startup cache loader
├── db.py            # MySQL connection factory
├── routes/
│   └── products.py  # /api/products endpoints
└── requirements.txt
```

---

## Architecture Notes

- **Canonical cache** — `canonical_product` rows are loaded into memory at startup for fast fuzzy search without hitting the DB on every request.
- **Read-only** — this service never writes to the database.
- **Matching** — similarity scores are computed with `rapidfuzz.fuzz.token_sort_ratio`; only `auto_matched` rows (score >= 0.85) appear in compare results.
