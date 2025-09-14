"""
Create dummy SQLite databases that mirror the production schemas described in
`deploy/TestDbs.txt` for local development and testing. This creates DB files
under `db/` with the expected table names and columns and inserts a small set
of dummy rows.

Usage (PowerShell):
  python seed_production_dbs.py

After running, the project can point to these local SQLite files for dev.
"""
import os
import sqlite3
from datetime import datetime
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE, 'db')
os.makedirs(DB_DIR, exist_ok=True)

now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

def create_db(path, ddl, rows):
    full = os.path.join(DB_DIR, path)
    if os.path.exists(full):
        os.remove(full)
    conn = sqlite3.connect(full)
    cur = conn.cursor()
    cur.executescript(ddl)
    for r in rows:
        # r is (table_name, column_list_string, values_tuple)
        placeholders = ','.join(['?'] * len(r[2]))
        cur.execute(f'INSERT INTO {r[0]} ({r[1]}) VALUES ({placeholders})', r[2])
    conn.commit()
    conn.close()


def seed_b2c_frontend():
    # Table name b2c_audit_log with columns from TestDbs.txt (types simplified for SQLite)
    ddl = '''
    CREATE TABLE b2c_audit_log (
        ID INTEGER PRIMARY KEY,
        BACKEND_URL TEXT,
        BACKEND_SYSTEM_NAME TEXT,
        REQUEST_HEADER TEXT,
        REQUEST_BODY TEXT,
        RESPONSE TEXT,
        RESPONSE_STATUS TEXT,
        STATR_TIME TEXT,
        END_TIME TEXT,
        TIME_CONSUMED_MILI INTEGER,
        CHANNEL TEXT,
        KIOSK_ID TEXT,
        TRANSACTION_ID TEXT,
        JSESSION_ID TEXT,
        THIRD_PARTY_REQUEST_BODY TEXT,
        THIRD_PARTY_RESPONSE TEXT,
        FE_REQUEST_BODY TEXT,
        FE_RESPONSE TEXT
    );
    '''
    rows = []
    # Prepare 50 dummy rows
    for i in range(1,51):
        cols = 'BACKEND_URL,BACKEND_SYSTEM_NAME,REQUEST_HEADER,REQUEST_BODY,RESPONSE,RESPONSE_STATUS,STATR_TIME,END_TIME,TIME_CONSUMED_MILI,CHANNEL,KIOSK_ID,TRANSACTION_ID,JSESSION_ID,THIRD_PARTY_REQUEST_BODY,THIRD_PARTY_RESPONSE,FE_REQUEST_BODY,FE_RESPONSE'
        vals = (
            f'https://backend/{i}',
            'TestSystem',
            'hdr',
            f'req body {i}',
            f'resp {i}',
            '200',
            now,
            now,
            123,
            'web',
            'kiosk1',
            f'tx{i}',
            f'jsid_{i}',
            'tp_req',
            'tp_resp',
            'fe_req',
            'fe_resp'
        )
        rows.append(('b2c_audit_log', cols, vals))
    create_db('b2c_frontend.db', ddl, rows)


def seed_selfcare():
    # test_uat.test_transactions_logger
    ddl1 = '''
    CREATE TABLE test_transactions_logger (
        SC_ID INTEGER PRIMARY KEY,
        SC_USER_NAME TEXT,
        SC_MSISDN TEXT,
        SC_TRANSACTION_ID TEXT,
        SC_OPERATION TEXT,
        SC_SERVICE_NAME TEXT,
        SC_SESSION_TOKEN TEXT,
        SC_OS_VERSION TEXT,
        SC_STATUS TEXT,
        SC_REQUEST_TIME_IN TEXT,
        SC_REQUEST_PAYLOAD TEXT,
        SC_RESPONSE_TIME_OUT TEXT,
        SC_RESPONSE_PAYLOAD TEXT,
        SC_EXCEPTION_STACKTRACE TEXT,
        SC_CHANNEL TEXT,
        SC_RESPONSE_CODE TEXT,
        SC_RESPONSE_MESSAGE TEXT,
        SC_GUEST_SESSION TEXT,
        SC_CUSTOMER_IP TEXT,
        SC_CUSTOMER_IP1 TEXT,
        SC_ROUND_TRIP_TIME INTEGER,
        SC_HEADERS TEXT,
        AUDIT_TIMESTAMP TEXT,
        KIOSK_ID TEXT,
        AUDIT_TIMESTUMP TEXT
    );
    '''
    rows1 = []
    for i in range(1,51):
        cols = 'SC_USER_NAME,SC_MSISDN,SC_TRANSACTION_ID,SC_OPERATION,SC_SERVICE_NAME,SC_STATUS,SC_REQUEST_TIME_IN,SC_REQUEST_PAYLOAD,SC_CHANNEL,AUDIT_TIMESTAMP,KIOSK_ID'
        vals = (f'user{i}', f'965000{i}', f'sc_tx_{i}', 'op', 'svc', 'OK', now, f'{{"p":{i}}}', 'web', now, 'kiosk1')
        rows1.append(('test_transactions_logger', cols, vals))

    # test_uat.test_transactions_lgr_be
    ddl2 = '''
    CREATE TABLE test_transactions_lgr_be (
        ID INTEGER PRIMARY KEY,
        TRANSACTION_ID TEXT,
        SERVICE_ORDER INTEGER,
        SERVICE_INTERFACE TEXT,
        SERVICE_OPERATION TEXT,
        REQUEST TEXT,
        REQUEST_TIME_IN TEXT,
        RESPONSE TEXT,
        RESPONSE_TIME_OUT TEXT,
        CHANNEL TEXT,
        RESPONSE_CODE TEXT,
        RESPONSE_DESCRIPTION TEXT,
        ROUND_TRIP_TIME INTEGER,
        AUDIT_TIMESTAMP TEXT,
        SERVICE_NAME TEXT,
        KIOSK_ID TEXT
    );
    '''
    rows2 = []
    for i in range(1,51):
        cols = 'TRANSACTION_ID,SERVICE_ORDER,SERVICE_INTERFACE,SERVICE_OPERATION,REQUEST,REQUEST_TIME_IN,RESPONSE,CHANNEL,RESPONSE_CODE,AUDIT_TIMESTAMP'
        vals = (f'tx_{i}', i, 'iface', 'op', f'req_{i}', now, f'resp_{i}', 'web', '200', now)
        rows2.append(('test_transactions_lgr_be', cols, vals))

    create_db('selfcare_uat.db', ddl1, rows1)
    create_db('selfcare_pd.db', ddl2, rows2)


def seed_magento():
    ddl = '''
    CREATE TABLE outbound_call_log (
        id INTEGER PRIMARY KEY,
        server_name TEXT,
        transaction_id TEXT,
        channel TEXT,
        backend_system TEXT,
        request_body TEXT,
        response_body TEXT,
        method_name TEXT,
        request_time TEXT,
        created_at TEXT,
        response_time TEXT,
        round_time REAL,
        session_id TEXT,
        req_identifier_type TEXT,
        end_point TEXT,
        req_identifier_value TEXT,
        failure TEXT
    );
    '''
    rows = []
    for i in range(1,101):
        cols = 'server_name,transaction_id,channel,backend_system,request_body,response_body,method_name,request_time,created_at,session_id'
        vals = ('srv', f'tx{i}', 'web', 'Test', f'req{i}', f'resp{i}', 'm', now, now, f'session_{i}')
        rows.append(('outbound_call_log', cols, vals))
    create_db('magento.db', ddl, rows)

    # Also create magento_uat.db and magento_pd.db as copies for config keys
    src = os.path.join(DB_DIR, 'magento.db')
    dst_uat = os.path.join(DB_DIR, 'magento_uat.db')
    dst_pd = os.path.join(DB_DIR, 'magento_pd.db')
    shutil.copyfile(src, dst_uat)
    shutil.copyfile(src, dst_pd)


if __name__ == '__main__':
    print('Seeding B2C Frontend...')
    seed_b2c_frontend()
    print('Seeding Selfcare DBs...')
    seed_selfcare()
    print('Seeding Magento...')
    seed_magento()
    print('Done seeding production-style DBs.')

    # Create copies matching config keys for FE and SELFCARE
    import os
    base = os.path.join(os.path.dirname(__file__), 'db')
    # FE copies
    fe_src = os.path.join(base, 'b2c_frontend.db')
    for name in ('fe_uat.db', 'fe_pd.db'):
        dst = os.path.join(base, name)
        if os.path.exists(fe_src):
            shutil.copyfile(fe_src, dst)
    # SELFCARE files are created directly by seed_selfcare(); no extra copies needed
