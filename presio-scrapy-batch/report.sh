#!/bin/bash

DB="presio"
USER="root"
PASS="Peru123.,"
INTERVAL=${1:-5}

mysql_q() {
    mysql -u "$USER" -p"$PASS" "$DB" 2>/dev/null -e "$1"
}

while true; do
    clear

    TOTAL=$(mysql -u "$USER" -p"$PASS" "$DB" 2>/dev/null -se "SELECT COUNT(*) FROM product;")
    SUM_STORE=$(mysql -u "$USER" -p"$PASS" "$DB" 2>/dev/null -se "SELECT COUNT(*) FROM product p JOIN store s ON s.id = p.store_id;")
    SUM_CATEGORY=$(mysql -u "$USER" -p"$PASS" "$DB" 2>/dev/null -se "SELECT COUNT(*) FROM product p JOIN category c ON c.id = p.category_id;")

    if [ "$TOTAL" = "$SUM_STORE" ] && [ "$TOTAL" = "$SUM_CATEGORY" ]; then
        CONSISTENCY="✓ consistent  (total=$TOTAL, by_store=$SUM_STORE, by_category=$SUM_CATEGORY)"
    else
        CONSISTENCY="✗ INCONSISTENT (total=$TOTAL, by_store=$SUM_STORE, by_category=$SUM_CATEGORY)"
    fi

    echo "========================================================"
    echo "  PRESIO — PRODUCT TABLE REPORT"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')   (refresh every ${INTERVAL}s)"
    echo "========================================================"
    echo ""
    echo "  Total products : $TOTAL"
    echo "  Consistency    : $CONSISTENCY"
    echo ""

    echo "── BY STORE ─────────────────────────────────────────"
    mysql_q "
        SELECT
            s.name          AS store,
            COUNT(p.id)     AS products
        FROM product p
        JOIN store s ON s.id = p.store_id
        GROUP BY s.name
        ORDER BY s.name;
    "
    echo ""

    echo "── BY STORE + CATEGORY ──────────────────────────────"
    mysql_q "
        SELECT
            s.name          AS store,
            c.name          AS category,
            COUNT(p.id)     AS products
        FROM product p
        JOIN store s    ON s.id = p.store_id
        JOIN category c ON c.id = p.category_id
        GROUP BY s.name, c.name
        ORDER BY s.name, c.name;
    "
    echo ""
    echo "  Press Ctrl+C to exit"

    sleep "$INTERVAL"
done
