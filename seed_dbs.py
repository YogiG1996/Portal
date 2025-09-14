"""
Creates sample SQLite databases with a `logs` table and a few seeded rows so the portal
works out-of-the-box. In production, point the app to real DBs using environment variables
(see .env.example).
"""
import os
import sqlite3
from datetime import datetime, timedelta

DBS = [
    ('db/b2c_frontend.db', 'b2c_frontend'),
    ('db/b2c_selfcare.db', 'b2c_selfcare'),
    ('db/magento.db', 'magento'),
]

# Public variables expected by tests
DB_DIR = 'db'
# apps: list of (app_label, filename, dbtype)
apps = [
    ('b2c_frontend', 'b2c_frontend.db', 'b2c_frontend'),
    ('b2c_selfcare', 'b2c_selfcare.db', 'b2c_selfcare'),
    ('magento', 'magento.db', 'magento'),
]

LEVELS = ['INFO', 'ERROR', 'DEBUG', 'WARNING', 'CRITICAL', 'SUCCESS']
MESSAGES = [
    'User login successful',
    'User login failed',
    'Order placed',
    'Order failed',
    'Payment processed',
    'Payment failed',
    'Exception occurred',
    'Service started',
    'Service stopped',
    'API call succeeded',
    'API call failed',
    'Data synced',
    'Data sync failed',
    'Session expired',
    'Session started',
    'Resource created',
    'Resource deleted',
    'Resource updated',
    'Permission denied',
    'Timeout error',
]

now = datetime.utcnow()
rows_per_day = 100


def seed_db(db_path, app_name):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_name TEXT,
        event_time TEXT,
        jsession_id TEXT,
        message TEXT,
        level TEXT
    )''')
    # Clear old logs
    cur.execute('DELETE FROM logs')
    # Insert logs for last 7 days
    for day in range(7):
        for i in range(rows_per_day):
            ts = (now - timedelta(days=day, minutes=i*10)).strftime('%Y-%m-%d %H:%M:%S')
            # Prefix messages with the dbtype so tests can verify db type presence
            dbtype = app_name
            message_text = f"{dbtype.upper()} - {MESSAGES[(day*rows_per_day + i) % len(MESSAGES)]}"
            cur.execute(
                'INSERT INTO logs (app_name, event_time, jsession_id, message, level) VALUES (?, ?, ?, ?, ?)',
                (
                    app_name,
                    ts,
                    f'jsid_{day}_{i}',
                    message_text,
                    LEVELS[(day*rows_per_day + i) % len(LEVELS)]
                )
            )
    con.commit()
    con.close()


if __name__ == '__main__':
    for db_path, app_name in DBS:
        print(f'Seeding {db_path} for {app_name}')
        seed_db(db_path, app_name)
    print('Done seeding all DBs.')
