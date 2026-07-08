# baruch-api

Read-only FastAPI service for Baruch — fuzzy product **search** and cross-store price
**comparison** over the Peruvian-supermarket catalog (Plaza Vea, Wong, Falabella).

> Internal package/DB naming is still `presio`. This is the catalog API app of the
> `baruch-backend` monorepo. For repo-wide context (DB schema, seed data, matching
> thresholds, data flow), see the [root README](../../README.md).

---

## Stack

- **Python 3.11** (conda env `presio`)
- **FastAPI** — web framework
- **Uvicorn** — ASGI server
- **MySQL** — database (`presio` schema)
- **rapidfuzz** — fuzzy product-name matching

---

## Setup

```bash
# From apps/baruch-api/
pip install -r requirements.txt
```

Configure the database connection in `db.py` (host, user, password, database).

---

## Run

The app uses top-level imports (`from db import ...`, `from routes.products import ...`),
so it must run with `apps/baruch-api/` on the import path.

```bash
# From apps/baruch-api/
conda run -n presio uvicorn main:app --reload --port 8000
```

Or as a one-liner from the repo root:

```bash
conda run -n presio uvicorn main:app --reload --port 8000 --app-dir apps/baruch-api
```

- Server: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

On startup the service logs `Cache loaded — N canonical products ready.` — all
`canonical_product` rows are loaded into memory for fast search (see Architecture Notes).

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/products/search` | Fuzzy-search canonical products by name |
| `GET` | `/api/products/{canonical_id}/compare` | Cross-store price comparison for one canonical |

### `GET /api/products/search`

Ranks the in-memory canonical cache against `q` by similarity, highest first.

**Query parameters**

| Parameter | Type | Required | Default | Constraints | Description |
|-----------|------|----------|---------|-------------|-------------|
| `q`       | string | yes | — | min 2 chars | Search query |
| `limit`   | int    | no  | 5 | 1–20 | Max results |

**Example**

```bash
curl "http://localhost:8000/api/products/search?q=laptop%20lenovo&limit=5"
```

**Response** `200 OK` — ordered by `score` descending:

```json
[
  { "id": 142, "name": "Laptop Lenovo IdeaPad 3 15.6", "score": 0.93 },
  { "id": 318, "name": "Laptop Lenovo V15 G4", "score": 0.81 }
]
```

- `score` = `rapidfuzz token_sort_ratio(q, name) / 100`, rounded to 2 decimals (0.0–1.0).
- Always returns up to `limit` rows; matching is best-effort, so low scores can appear
  when nothing is close. Apply a quality cutoff client-side if needed.

**Errors**

- `422 Unprocessable Entity` — `q` shorter than 2 chars, or `limit` outside 1–20.

### `GET /api/products/{canonical_id}/compare`

Returns price listings for one canonical across stores — **only `auto_matched` rows**,
ordered by `online_price` ascending (cheapest first).

**Path parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `canonical_id` | int | ID from the `canonical_product` table |

**Example**

```bash
curl "http://localhost:8000/api/products/142/compare"
```

**Response** `200 OK`:

```json
{
  "canonical_id": 142,
  "name": "Laptop Lenovo IdeaPad 3 15.6",
  "listings": [
    {
      "store": "Plaza Vea",
      "product_name": "Laptop Lenovo IdeaPad 3 15.6 8GB 256GB",
      "regular_price": 1899.00,
      "online_price": 1699.00,
      "discount_pct": 10.5,
      "currency": "PEN",
      "url": "https://plazavea.com.pe/..."
    },
    {
      "store": "Wong",
      "product_name": "Lenovo IdeaPad 3 15.6\" Core i5",
      "regular_price": 1999.00,
      "online_price": 1799.00,
      "discount_pct": 10.0,
      "currency": "PEN",
      "url": "https://wong.pe/..."
    }
  ]
}
```

- `listings` is ordered cheapest-first — the first entry is the lowest `online_price`.
- `listings` may be **empty `[]`** for a valid `canonical_id`: the canonical exists but has
  no `auto_matched` rows (e.g. all its products are still `needs_review`). Returns `200`, not `404`.
- A canonical matched in only one store returns a single listing — true comparison needs a
  canonical matched across ≥2 stores.

**Errors**

- `404 Not Found` — `canonical_id` does not exist in `canonical_product`.

---

## Project Structure

```
apps/baruch-api/
├── main.py            # FastAPI app + startup canonical-cache loader
├── db.py              # MySQL connection factory
├── routes/
│   └── products.py    # /api/products endpoints
└── requirements.txt
```

---

## Architecture Notes

- **Read-only** — this service never writes to the database. All writes happen in the
  scraper + processing batch (`apps/baruch-scraper`).
- **Canonical cache** — `canonical_product` rows are loaded into memory **once at startup**
  for fast fuzzy search without a DB round-trip per request.
  ⚠️ It is a snapshot: after a scrape + processing run mints new canonicals, **restart the API**
  or search will use a stale set. `/compare` always reads live from the DB, so its price
  data is never stale.
- **Matching** — search ranks with `rapidfuzz token_sort_ratio`; `/compare` surfaces only
  `auto_matched` rows (similarity ≥ 0.85). `needs_review` rows (0.65–0.84) are intentionally
  excluded. Quality is judged by canonicals matched across ≥2 stores, not raw match count.
  Threshold definitions live in the [root README](../../README.md#matching-thresholds).
