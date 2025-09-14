import sqlite3
from datetime import datetime, timedelta

def test_row_count():
    con = sqlite3.connect('db/b2c_frontend.db')
    cur = con.cursor()
    cur.execute('SELECT COUNT(*) FROM logs')
    count = cur.fetchone()[0]
    con.close()
    assert count == 700, f"Expected 700 rows, got {count}"

def test_recent_log():
    con = sqlite3.connect('db/b2c_frontend.db')
    cur = con.cursor()
    cur.execute('SELECT event_time FROM logs ORDER BY event_time DESC LIMIT 1')
    latest = cur.fetchone()[0]
    con.close()
    # Should be within the last 24 hours
    dt = datetime.strptime(latest, '%Y-%m-%d %H:%M:%S')
    assert datetime.utcnow() - dt < timedelta(days=1), f"Latest log is too old: {latest}"

def test_log_fields():
    con = sqlite3.connect('db/b2c_frontend.db')
    cur = con.cursor()
    cur.execute('PRAGMA table_info(logs)')
    columns = [row[1] for row in cur.fetchall()]
    con.close()
    expected = {'id', 'app_name', 'event_time', 'jsession_id', 'message', 'level'}
    assert set(columns) == expected, f"Columns mismatch: {columns}"

if __name__ == '__main__':
    test_row_count()
    test_recent_log()
    test_log_fields()
    print('All DB tests passed!')
