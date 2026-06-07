"""
Single-pass canonicalization + matching.

Replaces the former normalize (cluster -> mint canonicals) + score (match) two-step.
That split re-ran fuzzy matching twice with different thresholds and could leave orphan
canonicals (minted but never matched) or auto-match a product to a different canonical
than the cluster it formed. This module does both jobs in one pass:

    for each unmatched product (spec-richest first):
        best = best existing canonical in same (category, unit-spec) bucket
        >= AUTO   -> product_match auto_matched + stamp product.canonical_id
        >= REVIEW -> product_match needs_review (no canonical_id)
        else      -> this product DEFINES a new canonical; mint it and self-match (1.0)

Processing the spec-richest name first means the most descriptive listing founds each
canonical and sparser cross-store listings match onto it — folding online clustering and
matching into a single, threshold-consistent loop.
"""
from collections import defaultdict
import mysql.connector
from rapidfuzz import fuzz
from processing.match.strategy import CanonicalNameStrategy
from processing.match.passthrough_strategy import PassthroughStrategy
from processing.text import normalize_name, unit_specs, bare_numbers, spec_conflict

AUTO_MATCH_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.65


def _spec_richness(name: str) -> int:
    return len(unit_specs(name)) + len(bare_numbers(name))


def _record_match(cur, canonical_id: int, product: dict, score: float, status: str) -> None:
    cur.execute("""
        INSERT INTO product_match (canonical_id, product_id, store_id, similarity_score, status)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            similarity_score = VALUES(similarity_score),
            status           = VALUES(status),
            matched_at       = NOW()
    """, (canonical_id, product['id'], product['store_id'], score, status))

    if status == 'auto_matched':
        cur.execute(
            "UPDATE product SET canonical_id = %s WHERE id = %s AND store_id = %s",
            (canonical_id, product['id'], product['store_id'])
        )


def run(conn: mysql.connector.MySQLConnection, strategy: CanonicalNameStrategy = None):
    if strategy is None:
        strategy = PassthroughStrategy()

    cur = conn.cursor(dictionary=True)

    # Existing canonicals, bucketed by category. A product can only match a canonical
    # in the SAME category; within a category, spec_conflict() (subset-aware) does the
    # rejecting. Bucketing by exact unit-spec set was too strict — stores format specs
    # inconsistently, so true twins landed in different buckets and never met.
    # Normalization must use the SAME helpers everywhere, or scores drift below threshold.
    cur.execute("SELECT id, name, category_id FROM canonical_product")
    buckets = defaultdict(list)
    for c in cur.fetchall():
        c['_norm'] = normalize_name(c['name'])
        buckets[c['category_id']].append(c)

    # Unmatched products, spec-richest first so the most descriptive name founds a canonical.
    cur.execute("""
        SELECT id, store_id, name, category_id
        FROM product
        WHERE canonical_id IS NULL AND name IS NOT NULL
    """)
    unmatched = cur.fetchall()
    unmatched.sort(key=lambda p: _spec_richness(p['name']), reverse=True)

    print(f"Matching {len(unmatched)} products against {sum(len(b) for b in buckets.values())} canonicals...")

    auto = review = minted = 0

    for product in unmatched:
        product_norm = normalize_name(product['name'])

        best_score = 0.0
        best_canonical = None
        for canonical in buckets.get(product['category_id'], ()):
            if spec_conflict(product['name'], canonical['name']):
                continue   # different specs (8GB vs 16GB) or disjoint sizes (TV 50 vs 55)
            score = fuzz.token_set_ratio(product_norm, canonical['_norm']) / 100.0
            if score > best_score:
                best_score = score
                best_canonical = canonical

        if best_score >= AUTO_MATCH_THRESHOLD:
            _record_match(cur, best_canonical['id'], product, best_score, 'auto_matched')
            auto += 1
        elif best_score >= REVIEW_THRESHOLD:
            _record_match(cur, best_canonical['id'], product, best_score, 'needs_review')
            review += 1
        else:
            # No good existing canonical — this product defines a new canonical identity.
            canonical_name = strategy.clean(product['name'])
            cur.execute(
                "INSERT INTO canonical_product (name, category_id) VALUES (%s, %s)",
                (canonical_name, product['category_id'])
            )
            new_canonical = {
                'id': cur.lastrowid,
                'name': canonical_name,
                'category_id': product['category_id'],
                '_norm': normalize_name(canonical_name),
            }
            buckets[product['category_id']].append(new_canonical)
            _record_match(cur, new_canonical['id'], product, 1.0, 'auto_matched')
            minted += 1

    conn.commit()
    cur.close()
    print(f"Match done — {auto} auto-matched, {review} needs review, {minted} new canonicals minted.")
