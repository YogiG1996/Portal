import os
from datetime import datetime
from flask import Flask, render_template, request, send_file, jsonify, session
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import io
import smtplib
from email.message import EmailMessage
from config import settings
from dt_fmt import dt_fmt
import json
import logging

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change_this_secret_key')

# Load DB config from JSON
with open(os.path.join(os.path.dirname(__file__), 'db_config.json')) as f:
    DB_CONFIG = json.load(f)

# Optional deploy-time overrides. If `deploy_config.json` exists in the repo root it may
# supply `db_overrides` (map of db_key -> connection_string), `smtp`, and `site` settings.
DEPLOY_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'deploy_config.json')
DEPLOY_CONFIG = {}


def load_deploy_config():
    """Read deploy_config.json (if present) and merge overrides into runtime config.
    Returns the loaded deploy config (dict) or {}.
    """
    global DEPLOY_CONFIG, DB_CONFIG, SMTP_SETTINGS, SITE_CONFIG
    if not os.path.exists(DEPLOY_CONFIG_PATH):
        return {}
    try:
        with open(DEPLOY_CONFIG_PATH) as df:
            loaded = json.load(df)
            DEPLOY_CONFIG = loaded or {}
            # Merge DB overrides
            for k, v in (DEPLOY_CONFIG.get('db_overrides') or {}).items():
                if k in DB_CONFIG and v:
                    DB_CONFIG[k]['connection_string'] = v
            # Update SMTP settings
            smtp_cfg = DEPLOY_CONFIG.get('smtp') or {}
            if smtp_cfg:
                SMTP_SETTINGS.update({
                    'host': smtp_cfg.get('host') or SMTP_SETTINGS.get('host'),
                    'port': smtp_cfg.get('port') or SMTP_SETTINGS.get('port'),
                    'user': smtp_cfg.get('user') or SMTP_SETTINGS.get('user'),
                    'password': smtp_cfg.get('password') or SMTP_SETTINGS.get('password'),
                    'use_tls': smtp_cfg.get('use_tls', SMTP_SETTINGS.get('use_tls', True)),
                    'from': smtp_cfg.get('from') or SMTP_SETTINGS.get('from'),
                })
            # Update SITE_CONFIG if present
            site_cfg = DEPLOY_CONFIG.get('site') or {}
            if site_cfg:
                SITE_CONFIG.update(site_cfg)
            return DEPLOY_CONFIG
    except Exception as e:
        logging.warning(f'Failed to load deploy_config.json: {e}')
        return {}


# Try load once at startup
_ = load_deploy_config()


def _expand_env_placeholders_in_db_config():
    """Replace ${VAR} placeholders in DB_CONFIG connection_string entries with env vars.
    This allows storing an env-var token in `db_config.json` (e.g. "${DB_URI_B2C_FE}") while
    keeping real credentials out of source control.
    """
    for k, v in DB_CONFIG.items():
        conn = v.get('connection_string')
        if isinstance(conn, str) and conn.startswith('${') and conn.endswith('}'):
            env_name = conn[2:-1]
            env_val = os.environ.get(env_name)
            if env_val:
                DB_CONFIG[k]['connection_string'] = env_val
            else:
                # Fallback: try a local sqlite file under ./db/<key>.db for dev convenience
                local_path = os.path.join(os.path.dirname(__file__), 'db', f"{k}.db")
                if os.path.exists(local_path):
                    DB_CONFIG[k]['connection_string'] = f"sqlite:///{local_path}"
                    logging.info(f'Falling back to local SQLite for {k}: {local_path}')
                else:
                    logging.warning(f'Environment variable {env_name} not set and no local DB found; leaving placeholder for {k}')


# Expand any ${VAR} placeholders from environment variables
_expand_env_placeholders_in_db_config()


# Optional fail-fast behavior: if any DB_CONFIG connection_string still contains
# an unresolved ${VAR} placeholder and the env var FAIL_ON_UNRESOLVED_DB_PLACEHOLDERS
# is set to a truthy value, raise RuntimeError to avoid starting with missing credentials.
def _fail_on_unresolved_placeholders():
    if os.environ.get('FAIL_ON_UNRESOLVED_DB_PLACEHOLDERS', 'false').lower() in ('1', 'true', 'yes'):
        unresolved = []
        for k, v in DB_CONFIG.items():
            conn = v.get('connection_string')
            if isinstance(conn, str) and conn.startswith('${') and conn.endswith('}'):
                unresolved.append((k, conn))
        if unresolved:
            raise RuntimeError(f'Unresolved DB connection placeholders found: {unresolved}')


_fail_on_unresolved_placeholders()

# SMTP settings resolved from deploy config or environment variables
SMTP_SETTINGS = DEPLOY_CONFIG.get('smtp', {}) if DEPLOY_CONFIG else {}
SMTP_SETTINGS.setdefault('host', os.environ.get('SMTP_HOST'))
SMTP_SETTINGS.setdefault('port', int(os.environ.get('SMTP_PORT', '0')) or None)
SMTP_SETTINGS.setdefault('user', os.environ.get('SMTP_USER'))
SMTP_SETTINGS.setdefault('password', os.environ.get('SMTP_PASS'))
SMTP_SETTINGS.setdefault('use_tls', os.environ.get('SMTP_USE_TLS', 'true').lower() in ('1', 'true', 'yes'))
SMTP_SETTINGS.setdefault('from', os.environ.get('SMTP_FROM') or os.environ.get('EMAIL_FROM') or 'noreply@example.com')

# Site-level settings exposed to templates. These may come from deploy_config.json (key: "site")
# or via environment variables. Example deploy_config.json:
# { "site": { "title": "My Logs", "logo": "/static/img/my-logo.png", "logo_alt": "My Logo" } }
SITE_CONFIG = DEPLOY_CONFIG.get('site', {}) if DEPLOY_CONFIG else {}
SITE_CONFIG.setdefault('title', os.environ.get('SITE_TITLE', 'Etisalat Application Logs Portal'))
# `logo` may be an absolute or relative URL. If not provided, templates will fall back to the default static image.
SITE_CONFIG.setdefault('logo', os.environ.get('SITE_LOGO'))
SITE_CONFIG.setdefault('logo_alt', os.environ.get('SITE_LOGO_ALT', 'Logo'))


def _reload_token():
    # Token may be provided via env var or in deploy config under key 'reload_token'
    return os.environ.get('RELOAD_TOKEN') or DEPLOY_CONFIG.get('reload_token')


@app.route('/__reload_config', methods=['POST'])
def reload_config():
    """Protected endpoint to reload `deploy_config.json` from disk and update runtime config.
    To call, set header `X-Reload-Token: <token>` or send `?token=<token>`. Token must match
    environment variable `RELOAD_TOKEN` or `reload_token` inside `deploy_config.json`.
    """
    token = request.headers.get('X-Reload-Token') or request.args.get('token')
    expected = _reload_token()
    if not expected:
        return jsonify({'error': 'Reload token not configured on server'}), 403
    if not token or token != expected:
        return jsonify({'error': 'Invalid reload token'}), 403
    loaded = load_deploy_config()
    return jsonify({'reloaded': True, 'site': SITE_CONFIG, 'smtp': SMTP_SETTINGS, 'db_overrides': loaded.get('db_overrides')}), 200

APPLICATIONS = [v['display_name'] for v in DB_CONFIG.values()]
APP_KEY_MAP = {v['display_name']: k for k, v in DB_CONFIG.items()}

BASE_QUERY = """
SELECT * FROM logs
WHERE app_name = :app_name
    AND event_time BETWEEN :start_time AND :end_time
    AND (:jsid IS NULL OR jsession_id = :jsid)
ORDER BY event_time DESC
LIMIT :limit
"""

logging.basicConfig(level=logging.INFO)
# Enhanced file logging: rotate logs to keep disk usage bounded
from logging.handlers import RotatingFileHandler
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'app.log')
file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
file_handler.setFormatter(formatter)
logging.getLogger().addHandler(file_handler)

# Request timing & logging
from time import time
@app.before_request
def _before_request_log():
    request._start_time = time()
    logging.info(f"REQ start {request.remote_addr} {request.method} {request.path} params={request.args.to_dict()} form={request.form.to_dict()}")

@app.after_request
def _after_request_log(response):
    duration = (time() - getattr(request, '_start_time', time()))
    logging.info(f"REQ done {request.remote_addr} {request.method} {request.path} status={response.status_code} duration_ms={int(duration*1000)}")
    # Add simple X-Server-Timing header for diagnostics
    response.headers['X-Server-Duration-ms'] = str(int(duration*1000))
    return response


from werkzeug.exceptions import HTTPException


@app.errorhandler(Exception)
def _handle_exception(e):
    # If the exception is an HTTPException (404, 400, etc.), log lightly and return a friendly message
    if isinstance(e, HTTPException):
        # Log at warning level without stack trace to avoid noise
        logging.warning(f"HTTP exception during request {request.remote_addr} {request.method} {request.path}: {e.code} {e.name}")
        # For static file requests, return the original HTTP exception response (preserves 404 behavior)
        if request.path.startswith('/static/'):
            return e
        message = e.description or e.name
        if request.is_json or request.path.startswith('/send_selected_logs'):
            return jsonify({'error': message}), e.code
        else:
            # Render the main UI with a friendly error message and preserve HTTP status
            return render_template('index.html', applications=APPLICATIONS, results={'error': message}, selected=None, site=SITE_CONFIG), e.code

    # Non-HTTP exceptions: log full stack trace for diagnostics but hide details from end users
    logging.exception(f"Unhandled exception during request {request.remote_addr} {request.method} {request.path}")
    friendly = 'An internal error occurred. Please try again later or contact support.'
    if request.is_json or request.path.startswith('/send_selected_logs'):
        return jsonify({'error': friendly}), 500
    else:
        return render_template('index.html', applications=APPLICATIONS, results={'error': friendly}, selected=None, site=SITE_CONFIG), 500

def _get_engine(uri: str):
    return create_engine(uri, pool_pre_ping=True, future=True)


def _resolve_connection_string(db_info: dict, app_key: str) -> str:
    """Ensure a usable SQLAlchemy URI is returned.
    If the configured connection_string is a ${VAR} placeholder, prefer the
    environment variable; otherwise fall back to a local sqlite file under db/<app_key>.db
    (useful for local development where production URIs are not available).
    """
    conn = db_info.get('connection_string')
    if isinstance(conn, str) and conn.startswith('${') and conn.endswith('}'):
        env_name = conn[2:-1]
        env_val = os.environ.get(env_name)
        if env_val:
            return env_val
        # fallback to local sqlite file
        local_path = os.path.join(os.path.dirname(__file__), 'db', f"{app_key}.db")
        if os.path.exists(local_path):
            logging.info(f'Falling back to local SQLite for {app_key}: {local_path}')
            return f"sqlite:///{local_path}"
        # unresolved: return original (will raise during engine creation)
        return conn
    return conn

def query_logs(app_name, jsession_id, start_dt, end_dt, limit):
    # Map display name to config key
    app_key = APP_KEY_MAP.get(app_name, app_name)
    db_info = DB_CONFIG.get(app_key)
    if not db_info:
        return [], []
    # Resolve connection string at call time to catch placeholders that may
    # not have been resolvable at startup (for example if DB files were created
    # after the app started).
    resolved_conn = _resolve_connection_string(db_info, app_key)
    engine = _get_engine(resolved_conn)
    with engine.connect() as conn:
        dt_fmt2 = '%Y-%m-%d %H:%M:%S'
        # Use named-parameter binding by default. If the SQL contains a LIKE :jsid
        # clause and a jsession_id is provided, wrap it with '%' for pattern match.
        params = {
            'app_name': app_key,
            'start_time': start_dt.strftime(dt_fmt2),
            'end_time': end_dt.strftime(dt_fmt2),
            'jsid': jsession_id if jsession_id else None,
            'limit': limit,
            'backend_system': None,
            'channel': None,
            'sc_transaction_id': None,
            'transaction_id': None,
        }

        # Auto-wrap jsid for LIKE queries (Oracle FE entries typically use LIKE)
        sql_lower = db_info['select_query'].lower()
        if 'like :jsid' in sql_lower and jsession_id:
            params['jsid'] = f"%{jsession_id}%"

        print(f"[DEBUG] SQL: {db_info['select_query']}")
        print(f"[DEBUG] Params: {params}")
        result = conn.execute(text(db_info['select_query']), params)
        columns = list(result.keys())
        rows = [dict(zip(columns, r)) for r in result.fetchall()]
    return rows, columns

def send_logs_via_email(to_email, df, app_name=None):
    # Convert DataFrame to HTML table with some Web 3 style
    html_table = df.to_html(index=False, border=0, classes='web3-table', escape=False)
    app_label = f" for {app_name}" if app_name else ""
    html_content = f'''
    <html>
    <head>
    <style>
    .web3-table {{
        width: 100%;
        border-collapse: collapse;
        font-family: 'Segoe UI', Arial, sans-serif;
        background: #fff;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    }}
    .web3-table th {{
        background: #f7f7fa;
        color: #009a44;
        font-weight: bold;
        padding: 8px;
        border-bottom: 2px solid #e5e5e5;
    }}
    .web3-table td {{
        padding: 8px;
        border-bottom: 1px solid #e5e5e5;
        color: #222;
    }}
    </style>
    </head>
    <body>
    <h2>Selected Error Logs - {app_label}</h2>
    {html_table}
    </body>
    </html>
    '''
    msg = EmailMessage()
    msg['Subject'] = f'Selected Error Logs{app_label}'
    msg['From'] = SMTP_SETTINGS.get('from', 'noreply@example.com')
    msg['To'] = to_email
    msg.set_content(f'Please find the selected error logs{app_label} below.')
    msg.add_alternative(html_content, subtype='html')

    host = SMTP_SETTINGS.get('host')
    port = SMTP_SETTINGS.get('port')
    user = SMTP_SETTINGS.get('user')
    password = SMTP_SETTINGS.get('password')
    use_tls = SMTP_SETTINGS.get('use_tls', True)

    if not host or not port:
        raise RuntimeError('SMTP host and port must be configured (deploy_config.json or SMTP_HOST/SMTP_PORT env vars)')

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
    except Exception as smtp_err:
        logging.exception('SMTP send failed')
        raise

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', applications=APPLICATIONS, results=None, selected=None, site=SITE_CONFIG)

@app.route('/query', methods=['POST'])
def query():
    app_name = request.form.get('application')
    jsession_id = request.form.get('jsession_id', '').strip() or None
    backend_system = request.form.get('backend_system', '').strip() or None
    channel = request.form.get('channel', '').strip() or None
    sc_transaction_id = request.form.get('sc_transaction_id', '').strip() or None
    transaction_id = request.form.get('transaction_id', '').strip() or None
    time_span = request.form.get('time_span')
    try:
        limit = int(request.form.get('limit', '500'))
    except ValueError:
        return render_template('index.html', applications=APPLICATIONS, results={'error': 'Invalid limit'}, selected=app_name, site=SITE_CONFIG)

    logging.info(f"API Request: app_name={app_name}, jsession_id={jsession_id}, time_span={time_span}, limit={limit}")

    error = None
    if not app_name or app_name not in APPLICATIONS:
        error = 'Please select a valid application.'

    try:
        minutes = int(time_span)
        from datetime import timedelta
        # Always use UTC for both DB and query
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(minutes=minutes)
    except Exception:
        error = 'Invalid time span selection.'
        start_dt = end_dt = None

    if not start_dt or not end_dt:
        error = error or 'Please provide a valid time span.'

    if error:
        return render_template('index.html', applications=APPLICATIONS, results={'error': error}, selected=app_name, site=SITE_CONFIG)

    session['app_name'] = app_name  # Always update session with current app_name
    # pass extra filters along; query_logs uses named params so these will be bound when present
    rows, columns = query_logs(app_name, jsession_id, start_dt, end_dt, limit)
    logging.info(f"Query returned {len(rows)} rows. Columns: {columns}")
    if not rows:
        return render_template('index.html', applications=APPLICATIONS, results={'error': 'No data found.'}, selected=app_name, site=SITE_CONFIG)

    results = {
        'columns': columns,
        'rows': rows,
        'count': len(rows),
        'app_name': app_name,
        'jsession_id': jsession_id,
        'start_time': start_dt.strftime('%Y-%m-%d %H:%M'),
        'end_time': end_dt.strftime('%Y-%m-%d %H:%M'),
        'time_span': time_span
    }
    logging.info(f"API Response: {results['count']} rows from {results['start_time']} to {results['end_time']}")
    return render_template('index.html', applications=APPLICATIONS, results=results, selected=app_name, site=SITE_CONFIG)

@app.route('/export', methods=['POST'])
def export_excel():
    app_name = request.form.get('application')
    jsession_id = request.form.get('jsession_id', '').strip() or None
    time_span = request.form.get('time_span')
    try:
        limit = int(request.form.get('limit', '500'))
    except ValueError:
        return 'Invalid limit', 400

    try:
        minutes = int(time_span)
        from datetime import timedelta
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(minutes=minutes)
    except Exception:
        return 'Invalid time span', 400
    rows, columns = query_logs(app_name, jsession_id, start_dt, end_dt, limit)
    if not rows:
        return 'No data to export', 404
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Logs')
    output.seek(0)
    return send_file(output, download_name='error_logs.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/send_selected_logs', methods=['POST'])
def send_selected_logs():
    data = request.get_json()
    rows = data.get('rows')
    email = data.get('email')
    app_name = data.get('app_name')
    if not app_name:
        app_name = session.get('app_name')
    if not rows or not email:
        return jsonify({'error': 'Missing rows or email'}), 400
    df = pd.DataFrame(rows)
    try:
        send_logs_via_email(email, df, app_name)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=True)
