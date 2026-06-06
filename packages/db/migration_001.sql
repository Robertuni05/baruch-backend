-- Migration 001: Add canonical_product, product_match tables; extend product table
-- Run from presio-product-api/ root:
--   mysql -u root -pPeru123., presio < db/migration_001.sql

-- Step 1: canonical_product (must exist before product.canonical_id FK)
CREATE TABLE IF NOT EXISTS canonical_product (
  id          INT          PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(255) NOT NULL,
  category_id INT          NOT NULL,
  created_at  TIMESTAMP    DEFAULT NOW(),
  FOREIGN KEY (category_id) REFERENCES category(id),
  FULLTEXT KEY ft_name (name)
);

-- Step 2: Extend product table with url and canonical_id
ALTER TABLE product
  ADD COLUMN url          VARCHAR(500) NULL,
  ADD COLUMN canonical_id INT          NULL,
  ADD CONSTRAINT fk_product_canonical
    FOREIGN KEY (canonical_id) REFERENCES canonical_product(id);

-- Step 3: product_match (FKs to canonical_product and store)
CREATE TABLE IF NOT EXISTS product_match (
  id               INT         PRIMARY KEY AUTO_INCREMENT,
  canonical_id     INT         NOT NULL,
  product_id       VARCHAR(50) NOT NULL,
  store_id         INT         NOT NULL,
  similarity_score FLOAT       NOT NULL,
  status           ENUM('auto_matched', 'needs_review') NOT NULL DEFAULT 'needs_review',
  matched_at       TIMESTAMP   DEFAULT NOW(),
  FOREIGN KEY (canonical_id) REFERENCES canonical_product(id),
  FOREIGN KEY (store_id)     REFERENCES store(id),
  UNIQUE KEY uq_match (canonical_id, product_id, store_id)
);
