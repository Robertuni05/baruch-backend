-- Migration 002: Drop product_match, fold matching fields into product
-- Run from presio-product-api/ root:
--   mysql -u root -pPeru123., presio < db/migration_002.sql

-- Step 1: Add matching fields directly on product
ALTER TABLE product
  ADD COLUMN match_score  FLOAT NULL,
  ADD COLUMN match_status ENUM('auto_matched', 'needs_review') NULL,
  ADD COLUMN matched_at   TIMESTAMP NULL;

-- Step 2: Backfill from product_match (single store per product row, so a direct copy is safe)
UPDATE product p
JOIN product_match pm
  ON pm.product_id = p.id AND pm.store_id = p.store_id
SET p.match_score  = pm.similarity_score,
    p.match_status = pm.status,
    p.matched_at    = pm.matched_at;

-- Step 3: Drop product_match — canonical_product + product now hold the full match model
DROP TABLE product_match;
