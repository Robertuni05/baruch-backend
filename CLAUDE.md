# CLAUDE.md — presio-product-api

This file gives Claude Code the full architectural context for the Presio project.
The inner `presio/CLAUDE.md` covers scraper-specific details.

---

## Project Purpose

Presio tracks and compares product prices across Peruvian supermarkets (Wong, Plaza Vea).
Users search for a product by generic name and see a price comparison table across stores.

---

## Planned Project Structure

The monorepo will be split into two independent projects:

| Repo / Folder | New name (planned) | Responsibility |
|---|---|---|
| `presio/` | `presio-scrapy-batch` | Scraper + Matching batch processes |
| `api/` | `presio-api` | FastAPI web service (read-only) |

---

## Components

A **component** is a deployable unit with a single responsibility.
Spiders, pipelines, and routes are **artifacts** — implementation details inside a component.

### Scraper Batch (`presio-scrapy-batch`)

**Responsibility:** Collect raw product data from stores and persist to the `product` table.

**Artifacts:** WongSpider, PlazaVeaSpider, SaveProductPipeline, config.yaml, main.py

**Writes:** `product` table only. `canonical_id` is always `NULL` after scraping.

**Never reads:** `canonical_product` or `product_match`.

### Matching Batch (lives inside `presio-scrapy-batch` for now)

**Responsibility:** Enrich scraped products by computing similarity scores against canonical
products. Populate `product_match` and stamp `canonical_id` on matched `product` rows.

**Artifacts:** `matching/run_matching.py`, `FuzzyMatchStrategy`

**Reads:** `product` (unmatched rows), `canonical_product` (seeded manually by admin)

**Writes:** `product_match`, `product.canonical_id`

### Presio API (`presio-api`)

**Responsibility:** Serve HTTP endpoints for product search and price comparison.

**Artifacts:** FastAPI routes, ProductComparisonFacade, Repositories, MatchStrategy, Pydantic schemas

**Reads:** All tables. **Writes nothing.**

---

## Data Flow

```
[Admin seeds canonical_product manually]

presio-scrapy-batch
  └── Spider scrapes store pages
  └── Pipeline upserts → product table (canonical_id = NULL)
  └── Matching job runs after scrape
        reads  → product (WHERE canonical_id IS NULL)
        reads  → canonical_product
        writes → product_match
        writes → product.canonical_id

presio-api (read-only)
  └── GET /api/products/search?q=...
        reads → canonical_product (fuzzy match via rapidfuzz)
  └── GET /api/products/{id}/compare
        reads → product_match JOIN product JOIN store
```

---

## Database

MySQL, local (`localhost`, user `root`, db `presio`).

### Tables

```sql
store            (id, name)
category         (id, name)                          -- snake_case ASCII names

product          (id, store_id,                      -- PK: (id, store_id)
                  name, category_id,
                  regular_price, online_price,
                  discount_pct, currency,
                  url,                               -- product page link
                  canonical_id,                      -- FK → canonical_product, nullable
                  created_at, updated_at)

canonical_product (id, name,                         -- normalized product identity
                   category_id, created_at)          -- FULLTEXT index on name

product_match    (id, canonical_id, product_id,      -- similarity cache
                  store_id, similarity_score,
                  status,                            -- auto_matched | needs_review
                  matched_at)
                  UNIQUE (canonical_id, product_id, store_id)
```

### Seed data

```sql
INSERT INTO store    (id, name) VALUES (1,'Plaza Vea'),(2,'Wong');
INSERT INTO category (id, name) VALUES
  (1,'tecnologia'),(2,'higiene_y_belleza'),
  (3,'electrohogar'),(4,'mascotas'),(5,'despensa');
```

---

## Design Patterns (API layer)

| Pattern | Class | Why |
|---|---|---|
| Repository | `CanonicalProductRepository`, `ProductMatchRepository` | All SQL in one place; no SQL in business logic |
| Strategy | `MatchStrategy` (ABC), `FuzzyMatchStrategy` | Swap matching algorithm without touching callers |
| Facade | `ProductComparisonFacade` | Single entry point for Routes; orchestrates search + compare |

Clean Architecture alignment:
- Entities → `ScoredMatch`, `CanonicalProduct` (no external deps)
- Use Cases → `ProductComparisonFacade` (depends only on abstractions)
- Interface Adapters → Repositories, Strategy implementations
- Frameworks & Drivers → FastAPI, MySQL, rapidfuzz

---

## Matching Thresholds

| Score | Status | Action |
|---|---|---|
| >= 0.85 | `auto_matched` | Insert `product_match`, set `product.canonical_id` |
| 0.65 – 0.84 | `needs_review` | Insert `product_match`, queue for manual review |
| < 0.65 | skip | No row inserted |

Algorithm: `rapidfuzz.fuzz.token_sort_ratio` — handles word-order differences across stores.

---

## API Endpoints

```
GET /api/products/search?q=<query>&limit=5
    → list of top canonical product matches with similarity score

GET /api/products/{canonical_id}/compare
    → canonical product + price listings per store (auto_matched only)
```

---

## Category Naming Convention

Always `snake_case` ASCII, no accents, no spaces.
Example: `higiene_y_belleza`, not `Higiene y Belleza`.

---

## Working Preferences

- **Propose before changing:** Always present a plan and wait for approval before editing files.
- **Spider commands:** Give the command for the user to run; do not run long spiders as foreground tool calls (Wong spider takes 45+ min for all categories).
- **Diagnostics:** Deep technical explanation with references, code samples, phase-by-phase breakdowns. Append errors to `diagnostic.txt` with fixed columns (DATE, SPIDER, COMMAND, PROBLEM, ERROR, ROOT CAUSE, DIAGNOSTIC, REFERENCES, FIX APPLIED, STATUS).
- **History:** Session answers are documented in `history_answer.md` (newest session first).

---

## Run Commands

```bash
# Scraper (from presio-scrapy-batch/ directory)
conda run -n presio python main.py --supermarket wong --category tecnologia --loglevel INFO 2>&1 | tee server.log
conda run -n presio python main.py --supermarket plazavea --category tecnologia --loglevel INFO 2>&1 | tee server.log

# Post-scrape pipeline: canonicalization + matching (from presio-scrapy-batch/ directory)
conda run -n presio python -m processing.run_pipeline

# API server (from presio-product-api/ root, once presio-api/ exists)
conda run -n presio uvicorn presio_api.main:app --reload
```
