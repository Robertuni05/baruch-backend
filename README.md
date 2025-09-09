# presio-product-api

API to get product --- prices test how to use stash.

---

## Installation

### 1. Create Conda Environment

```bash
conda create -n presio
conda activate presio
conda install pip
```

### 2. Install Dependencies

```bash
conda install Scrapy
pip install scrapy-playwright
```

### 3. Start Scrapy Project

```bash
scrapy startproject presio
```

### 4. Install Playwright Browsers

```bash
playwright install
```

---

## Usage

To run the Wong spider:

```bash
scrapy crawl wongspider
```

---

## References

- [Scrapy Tutorial](https://docs.scrapy.org/en/latest/intro/tutorial.html)
- [scrapy-playwright GitHub](https://github.com/scrapy-plugins/scrapy-playwright)
