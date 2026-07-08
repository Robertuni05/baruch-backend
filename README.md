# baruch-backend

**Baruch** helps shoppers find the best product for their need and compare its price across
Peruvian stores. Named after Baruch Spinoza — it cuts through store marketing to reveal the
true value of a product.

This repository is the **backend monorepo**. The web frontend lives in a separate repo
(`baruch-web`) and talks to these services over HTTP only.

---

## Monorepo Layout

```
baruch-backend/
├── apps/
│   ├── baruch-scraper/        # Scrapy spiders + nodriver fetcher → writes product table
│   ├── baruch-api/            # FastAPI read-only service → search + price compare
│   └── baruch-advisor-api/    # (planned) LLM "Asesor" layer → conversational advice
└── packages/
    └── db/                    # shared schema, migrations, dbdiagram source
```

Each app is independently deployable (own dependencies, own container). Folder boundaries
enforce single responsibility — the scraper never serves HTTP, the API never writes.

| App | Stack | Responsibility | Reads / Writes |
|---|---|---|---|
| `baruch-scraper` | Scrapy, scrapy-playwright, nodriver | Collect raw prices | Writes `product` |
| `baruch-api` | FastAPI, rapidfuzz | Search + compare endpoints | Reads all, writes nothing |
| `baruch-advisor-api` | FastAPI, Anthropic SDK *(planned)* | AI advisor over the catalog | Calls catalog-api |

---

## Installation

### 1. Create Conda Environment

```bash
conda create --name presio python=3.11
conda activate presio
conda install pip
```

### 2. Install Dependencies

```bash
# Scraper
conda install Scrapy
pip install scrapy-playwright mysql-connector-python pyyaml nodriver
playwright install

# API
pip install -r apps/baruch-api/requirements.txt
```

---

## apps/baruch-scraper

Collects product data and upserts into the `product` table (`canonical_id` stays `NULL`
until the matching pipeline runs).

**Stores:** Plaza Vea (REST/VTEX API), Wong (Playwright browser), Falabella (nodriver — bypasses
Cloudflare Bot Management).

Categories and store URLs are defined in `apps/baruch-scraper/config.yaml`.
Available categories: `tecnologia`, `higiene_y_belleza`, `electrohogar`, `mascotas`, `despensa`.

### Run (from inside the scraper directory)

```bash
cd apps/baruch-scraper

# Plaza Vea (REST API, fast)
conda run -n presio python main.py --supermarket plazavea --category tecnologia --loglevel INFO 2>&1 | tee server.log

# Wong (Playwright, 45+ min for all categories)
conda run -n presio python main.py --supermarket wong --category tecnologia --loglevel INFO 2>&1 | tee server.log

# Falabella (standalone nodriver fetcher — not a Scrapy spider)
conda run -n presio python -m fetchers.falabella_fetcher --category tecnologia --max-pages 1
```

### Spider arguments

| Argument | Default | Description |
|---|---|---|
| `--supermarket` | `wong` | Spider to run (`wong`, `plazavea`, `falabella`) |
| `--category` | all | Category name or id to scrape |
| `--loglevel` | `INFO` | Log level |
| `--max-pages` | unlimited | Max pages per category |
| `--max-scrolls` | `7` | Max scroll attempts per page (wong only) |
| `--no-change-limit` | `5` | Stop after N scrolls with no new products (wong only) |

---

## apps/baruch-api

Read-only FastAPI service. Loads `canonical_product` into memory at startup and serves
fuzzy search + price comparison.

### Run (from inside the api directory)

```bash
cd apps/baruch-api
conda run -n presio uvicorn main:app --reload
```

### Endpoints

```
GET /api/products/search?q=<query>&limit=5
    → top canonical product matches (rapidfuzz token_sort_ratio)

GET /api/products/{canonical_id}/compare
    → canonical product + price listings per store (auto_matched only)
```

Example:

```bash
curl "http://localhost:8000/api/products/search?q=laptop%20hp%2016GB&limit=5"
curl "http://localhost:8000/api/products/1/compare"
```

---

## Database

MySQL, local (`localhost`, user `root`, db `presio`). Schema source of truth:
`packages/db/migration_001.sql`. Visual diagram: import `packages/db/presio_dbdiagram.dbml`
at [dbdiagram.io](https://dbdiagram.io/d).

### Tables

```sql
store             (id, name)
category          (id, name)                          -- snake_case ASCII names

product           (id, store_id,                      -- PK: (id, store_id)
                   name, category_id,
                   regular_price, online_price,
                   discount_pct, currency, url,
                   canonical_id,                       -- FK → canonical_product, nullable
                   match_score, match_status,          -- nullable until matched
                   matched_at,                         -- match_status: auto_matched | needs_review
                   created_at, updated_at)

canonical_product (id, name, category_id, created_at) -- FULLTEXT index on name
```

### Seed data

```sql
INSERT INTO store (id, name) VALUES (1, 'Plaza Vea'), (2, 'Wong'), (3, 'Falabella');

INSERT INTO category (id, name) VALUES
  (1, 'tecnologia'),
  (2, 'higiene_y_belleza'),
  (3, 'electrohogar'),
  (4, 'mascotas'),
  (5, 'despensa');
```

### Data flow

```
[Admin seeds canonical_product manually]

baruch-scraper      → product (canonical_id = NULL)
(matching pipeline) → product.canonical_id, match_score, match_status, matched_at  (being reworked, not currently runnable)
baruch-api          → reads only, serves search + compare
baruch-advisor-api  → calls baruch-api as tools (planned)
```

---

## Matching Thresholds

| Score | Status | Action |
|---|---|---|
| >= 0.85 | `auto_matched` | Set `product.canonical_id` + `match_status` |
| 0.65 – 0.84 | `needs_review` | Set `product.canonical_id` + `match_status`, queue for manual review |
| < 0.65 | skip | No row inserted |

Algorithm: `rapidfuzz.fuzz.token_sort_ratio` — handles word-order differences across stores.

---

## References

- [Scrapy Documentation](https://docs.scrapy.org/en/latest/intro/tutorial.html)
- [scrapy-playwright](https://github.com/scrapy-plugins/scrapy-playwright)
- [nodriver](https://github.com/ultrafunkamsterdam/nodriver) — Cloudflare-resistant browser automation
- [FastAPI](https://fastapi.tiangolo.com/)
- [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz)
