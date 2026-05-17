# presio-product-api

Scraper that collects product prices from Peruvian supermarkets (Wong and Plaza Vea) and stores them in a MySQL database.

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
conda install Scrapy
pip install scrapy-playwright
pip install mysql-connector-python
pip install pyyaml
```

### 3. Install Playwright Browsers

```bash
playwright install
```

---

## Configuration

Categories and store URLs are defined in `presio/config.yaml`. Each category maps to one or more URL paths per store.

Available categories: `tecnologia`, `higiene_y_belleza`, `electrohogar`, `mascotas`, `despensa`.

See `presio/category.txt` for the full list of wong and plaza vea category URLs.

---

## Usage

Run from inside the `presio/` directory:

```bash
cd presio
```

### Run all categories for a spider

```bash
# Wong (uses Playwright browser)
conda run -n presio python main.py --supermarket wong --output out.json --loglevel INFO 2>&1 | tee server.log

# Plaza Vea (uses REST API, faster)
conda run -n presio python main.py --supermarket plazavea --output out.json --loglevel INFO 2>&1 | tee server.log
```

### Run a specific category

```bash
conda run -n presio python main.py --supermarket wong --category tecnologia --output out.json --loglevel INFO
conda run -n presio python main.py --supermarket plazavea --category tecnologia --output out.json --loglevel INFO
```

### Available arguments

| Argument | Default | Description |
|---|---|---|
| `--supermarket` | `wong` | Spider to run (`wong` or `plazavea`) |
| `--category` | all | Category name or id to scrape |
| `--output` | `out.json` | Output file |
| `--loglevel` | `INFO` | Log level |
| `--max-pages` | unlimited | Max pages per category |
| `--max-scrolls` | `7` | Max scroll attempts per page (wong only) |
| `--no-change-limit` | `5` | Stop scrolling after N scrolls with no new products (wong only) |

---

## Database Model

MySQL database named `presio` with the following tables:

```sql
CREATE TABLE store (
    id   INT          NOT NULL,
    name VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE category (
    id   INT          NOT NULL,
    name VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE product (
    id             INT           NOT NULL,
    store_id       INT           NOT NULL,
    name           VARCHAR(1000) NOT NULL,
    category_id    INT,
    regular_price  DECIMAL(18,2),
    online_price   DECIMAL(18,2),
    discount_pct   DECIMAL(10,2),
    currency       VARCHAR(5),
    created_at     DATETIME,
    updated_at     DATETIME,
    PRIMARY KEY (id, store_id),
    CONSTRAINT fk_product_store FOREIGN KEY (store_id)    REFERENCES store(id),
    CONSTRAINT fk_product_cat   FOREIGN KEY (category_id) REFERENCES category(id)
);
```

### Seed data

```sql
INSERT INTO store (id, name) VALUES (1, 'Plaza Vea'), (2, 'Wong');

INSERT INTO category (id, name) VALUES
  (1, 'tecnologia'),
  (2, 'higiene_y_belleza'),
  (3, 'electrohogar'),
  (4, 'mascotas'),
  (5, 'despensa');
```

---

## References

- [Scrapy Documentation](https://docs.scrapy.org/en/latest/intro/tutorial.html)
- [scrapy-playwright GitHub](https://github.com/scrapy-plugins/scrapy-playwright)
