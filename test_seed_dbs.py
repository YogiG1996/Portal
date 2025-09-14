"""
Test for seed_dbs.py: verifies that each DB has 100 rows and correct app/db type mapping.
"""
import os
import sqlite3
import pytest
from seed_dbs import apps, DB_DIR

def test_seeded_db_rows():
    for app_label, fname, dbtype in apps:
        path = os.path.join(DB_DIR, fname)
        assert os.path.exists(path), f"DB file missing: {path}"
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM logs WHERE app_name=?', (app_label,))
        count = cur.fetchone()[0]
        # seed_dbs.py inserts 7 days * 100 rows_per_day = 700 rows per DB
        assert count == 700, f"Expected 700 rows for {app_label}, found {count}"
        # Check dbtype in at least one message
        cur.execute('SELECT message FROM logs WHERE app_name=? LIMIT 1', (app_label,))
        msg = cur.fetchone()[0]
        assert dbtype.upper() in msg, f"DB type {dbtype} not found in message for {app_label}"
        conn.close()
