# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Presio is a Scrapy-based price scraper for Peruvian supermarkets (Wong and Plaza Vea). It collects product prices and stores them in a MySQL database named `presio`.

## Environment setup

Uses a Conda environment named `presio` (Python 3.11). Always prefix run commands with `conda run -n presio`.

```bash
conda create --name presio python=3.11
conda activate presio
conda install pip && conda install Scrapy
pip install scrapy-playwright mysql-connector-python pyyaml
playwright install
```

## Running spiders

All commands run from inside the `presio-scrapy-batch/` directory:

```bash
# Run all categories for a store
conda run -n presio python main.py --supermarket wong --output out.json --loglevel INFO 2>&1 | tee server.log
conda run -n presio python main.py --supermarket plazavea --output out.json --loglevel INFO 2>&1 | tee server.log

# Run a specific category (by name or id)
conda run -n presio python main.py --supermarket wong --category tecnologia --output out.json --loglevel INFO
conda run -n presio python main.py --supermarket plazavea --category 1 --output out.json --loglevel INFO
```

Key CLI flags: `--supermarket` (`wong`|`plazavea`), `--category` (name or id), `--output`, `--loglevel`, `--max-pages`, `--max-scrolls` (wong only), `--no-change-limit` (wong only).

## Architecture

```
presio/              ← working directory (run commands from here)
  main.py            ← CLI entry point; dispatches to spider via CrawlerProcess
  config.yaml        ← single source of truth for store base_urls and category→URL mappings
  scrapy.cfg
  presio/            ← Scrapy project package
    settings.py      ← Playwright handler, pipeline config, throttling
    items.py         ← ProductItem (the only item used in production)
    pipelines.py     ← SaveProductPipeline: upserts ProductItem into MySQL
    spiders/
      wong.py        ← Playwright-driven scroll spider (store_id=2)
      plazavea.py    ← REST API spider via VTEX catalog endpoint (store_id=1)
```

### Data flow

1. `main.py` parses args → creates `CrawlerProcess` → calls `spider.__init__` with category filter.
2. Spider `__init__` reads `config.yaml`, builds `start_urls` (wong) or `category_urls` (plazavea) filtered by the requested category.
3. Spider yields `ProductItem` objects with `product_id = "{store_id}_{raw_id}"`.
4. `SaveProductPipeline` upserts each item into the `product` table using `ON DUPLICATE KEY UPDATE`.

### Wong vs Plaza Vea spider differences

| Concern | Wong | Plaza Vea |
|---|---|---|
| Rendering | Playwright (Firefox, scroll loop) | None — hits VTEX REST API directly |
| Pagination | Follows `<link rel="next">` | Increments `_from`/`_to` query params (50 items/page) |
| Stop condition | No `<link rel="next">` | Empty JSON array response |
| `store_id` | `2` | `1` |

### Category config

Categories are defined in `config.yaml`. Each category has a numeric `id` (matching the DB `category` table), a snake_case `name`, and per-store URL path lists. A category can map to multiple URLs for one store (e.g. `higiene_y_belleza` maps to two Plaza Vea paths).

Current categories: `tecnologia` (1), `higiene_y_belleza` (2), `electrohogar` (3), `mascotas` (4), `despensa` (5).

To add a new category: add an entry to `config.yaml` and insert a row into the `category` DB table.

## Database

MySQL database `presio`, local connection (`localhost`, user `root`). Connection credentials are hardcoded in `pipelines.py:SaveProductPipeline.__init__`.

Seed SQL:
```sql
INSERT INTO store (id, name) VALUES (1, 'Plaza Vea'), (2, 'Wong');
INSERT INTO category (id, name) VALUES
  (1, 'tecnologia'), (2, 'higiene_y_belleza'),
  (3, 'electrohogar'), (4, 'mascotas'), (5, 'despensa');
```

## Key constraints

- Playwright uses Firefox (`settings.py:PLAYWRIGHT_BROWSER_TYPE`). Navigation timeout is 300 s.
- `CONCURRENT_REQUESTS_PER_DOMAIN = 1` and `DOWNLOAD_DELAY = 1` — do not raise these aggressively.
- `ROBOTSTXT_OBEY = True` in settings; Wong spider uses a random UA list to avoid blocks.
- `product_id` is a composite string `"{store_id}_{raw_id}"` — primary key is `(id, store_id)` in the DB.

## References

- [Scrapy docs](https://docs.scrapy.org/en/latest/)
- [scrapy-playwright](https://github.com/scrapy-plugins/scrapy-playwright)
- [VTEX Catalog API](https://developers.vtex.com/docs/api-reference/catalog-api)
