# Etisalat Application Logs Portal

A lightweight Flask web app to query **failure logs** across multiple applications, themed in Etisalat (e&) colors.

## Features
- App dropdown: **B2C Fron-end Logs**, **B2C Selfcare Logs**, **Magento Logs**, **TIBCO**, **6D Logs**.
- Per-application database connection (override via environment variables).
- Inputs: **JSession ID** (optional), **time range**, and **max rows**.
- Secure parameterized queries that return only *failure* logs (levels `ERROR`/`FATAL` or messages containing `fail`/`exception`).
- Clean, responsive UI styled with Etisalat-inspired green & dark theme.

## Quickstart

```bash
# 1) Create & activate a virtual environment (recommended)
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) (Optional) Create sample SQLite DBs with seed data
python seed_dbs.py

# 4) Run the app
python app.py
# Open http://localhost:5000
```

## Configuration
The app maps UI labels to DB URIs via `config.py`. For production, set environment variables (e.g. in a `.env` file loaded by your process manager):

```ini
# .env example
DB_URI_B2C_FE=postgresql+psycopg2://user:pass@host:5432/b2c_fe
DB_URI_B2C_SELFCARE=postgresql+psycopg2://user:pass@host:5432/selfcare
DB_URI_MAGENTO=mysql+pymysql://user:pass@host:3306/magento
DB_URI_TIBCO=oracle+oracledb://user:pass@host:1521/?service_name=TIBCO
DB_URI_6D=mssql+pyodbc://user:pass@host/DB?driver=ODBC+Driver+18+for+SQL+Server
```

If you use the sample DBs (default), URIs are SQLite files under `./db/` and require no additional drivers.

> **Security**
> - Queries are parameterized to avoid SQL injection.
> - The Execute button is enabled only when required fields are populated.
> - In production, set a strong `SECRET_KEY` and run behind HTTPS.

## How filtering works
The backend returns rows where either:
- `level` is `ERROR` or `FATAL`, **or**
- `message` contains `fail` or `exception` (case-insensitive behavior depends on DB collation; for SQLite this is case-insensitive by default for ASCII).

You can edit this predicate in `app.py` if your log schema differs.

## Customize
- Update colors in `static/css/styles.css` to match your exact brand values.
- Extend the table columns by modifying the SQL in `app.py`.
- Replace SQLite with your actual DBs by setting the env vars.

## Project Structure
```
etisalat_logs_portal/
├─ app.py
├─ config.py
├─ seed_dbs.py
├─ requirements.txt
├─ README.md
├─ templates/
│  └─ index.html
├─ static/
│  ├─ css/
│  │  └─ styles.css
│  └─ js/
├─ db/
   ├─ b2c_frontend.db
   ├─ b2c_selfcare.db
   ├─ magento.db
   ├─ tibco.db
   └─ sixd.db
```

---
# Etisalat Application Logs Portal

Lightweight Flask web UI for querying failure logs across multiple application-specific databases.

This README documents how to run locally, deploy as a service, and configure database and SMTP settings the application requires.

Contents
- Quickstart (dev)
- Configuration (env vars and `deploy_config.json`)
- Database schema and where to edit queries
- SMTP/email settings
- Endpoints and their payloads
- Deploying as a service (Windows / systemd)
- Admin: reload config without restart
- Tests

## Quickstart (development)

1. Create & activate a virtual environment (PowerShell on Windows):

```powershell
python -m venv .venv
. .venv\Scripts\Activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. (Optional) Seed local SQLite DBs for development:

```powershell
python seed_dbs.py
```

4. Run the app (dev server):

```powershell
python app.py
# Visit http://127.0.0.1:5000
```

Notes:
- The app uses Flask server in debug by default when run directly. For production, run behind a WSGI server (gunicorn/uvicorn) or via the included systemd/Windows service helpers.

## Configuration

Two ways to configure production values:

- Environment variables (recommended for secrets)
- `deploy_config.json` placed in the project root (optional)

Priority: `deploy_config.json` values are loaded at startup and when you call the reload endpoint; environment variables provide defaults and are easiest to inject into systemd or Windows service.

Important environment variables

 - `DB_URI_B2C_FE`, `DB_URI_B2C_SELFCARE`, `DB_URI_MAGENTO`, `DB_URI_TIBCO`, `DB_URI_6D` — per-app SQLAlchemy connection strings. Example:

```ini
DB_URI_B2C_FE=postgresql+psycopg2://user:pass@host:5432/b2c_fe
```

 - `FLASK_SECRET_KEY` — Flask secret key (override default `change_this_secret_key`).
 - `PORT` — port to run on (default 5000).
 - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_USE_TLS`, `SMTP_FROM` — SMTP settings (see SMTP section below).
 - `SITE_TITLE`, `SITE_LOGO`, `SITE_LOGO_ALT` — optional site title and logo URL/path used by the UI.
 - `RELOAD_TOKEN` — token used to authorize calls to the reload endpoint (see "Admin: reload config" below).

deploy_config.json (optional)

If you prefer a single file to provide non-secret overrides (or secrets in controlled deployments), create `deploy_config.json` at the repo root. Example structure:

```json
{
   "db_overrides": {
      "b2c_frontend": "postgresql+psycopg2://user:pass@host:5432/b2c_fe",
      "magento": "mysql+pymysql://user:pass@host:3306/magento"
   },
   "smtp": {
      "host": "smtp.example.com",
      "port": 587,
      "user": "smtp-user@example.com",
      "password": "supersecret",
      "use_tls": true,
      "from": "noreply@example.com"
   },
   "site": {
      "title": "My Logs Portal",
      "logo": "/static/img/my-logo.png",
      "logo_alt": "My Company Logo"
   },
   "reload_token": "a-strong-token-you-keep-secret"
}
```

Security note: avoid committing secrets to VCS. Use environment variables or a secrets store where possible.

## Database: structure and queries

Seed DBs (for local dev)
- `seed_dbs.py` creates SQLite files under `./db/` and a single table `logs` with columns: `id, app_name, event_time, jsession_id, message, level`.

Querying in production
- The per-application SQL templates and connection strings live in `db_config.json` and `config.py` (the UI uses `display_name` entries but backend maps display names to config keys via `APP_KEY_MAP` in `app.py`).
- If you need to change which columns appear or adjust filters, update the `select_query` for the appropriate db entry in `db_config.json` or modify `query_logs()` in `app.py`.

Important: queries use SQLAlchemy `text()` and named parameters for SQLite/Postgres/other drivers. MySQL support uses positional parameters in the existing code — be careful if you refactor that section.

## SMTP / Email

The function that sends selected logs is `send_logs_via_email()` in `app.py`. It uses `SMTP_SETTINGS` resolved from `deploy_config.json` or environment variables. Required values:

- `SMTP_HOST` and `SMTP_PORT` — must be set either via env vars or in `deploy_config.json` under `smtp`.
- `SMTP_USER` and `SMTP_PASS` — optional; required if the SMTP server requires auth.
- `SMTP_USE_TLS` — true/false. If true the code calls `starttls()`.
- `SMTP_FROM` — From email address used when sending.

If host/port are missing, the email function raises a runtime error to avoid accidentally attempting to send without a configured SMTP server.

## HTTP Endpoints

- `GET /` — main UI (renders `templates/index.html`). The template receives:
   - `applications` — list of app display names from `db_config.json`.
   - `results` — query results when performing `/query`.
   - `site` — site-level config from `SITE_CONFIG` (`title`, `logo`, `logo_alt`).

- `POST /query` — form POST endpoint. Accepts fields:
   - `application` (display name string)
   - `jsession_id` (optional)
   - `time_span` (minutes)
   - `limit` (number)

- `POST /export` — form POST that returns an Excel file for the current query filters (same form fields as `/query`).

- `POST /send_selected_logs` — JSON POST used by the UI to send selected rows to email. Example payload:

```json
{
   "rows": [ { "id": 1, "event_time": "...", "message": "..." }, ... ],
   "email": "ops@example.com",
   "app_name": "B2C Frontend"
}
```

Response: `{'success': true}` or `{'error': '...'} ` on failure.

- `POST /__reload_config` — admin endpoint to reload `deploy_config.json` without restarting the server. Protected by a token.
   - Provide the token in header `X-Reload-Token: <token>` or query `?token=<token>`.
   - Token source: env `RELOAD_TOKEN` or `reload_token` in `deploy_config.json`.
   - Returns JSON with the updated `site`, `smtp`, and `db_overrides`.

## Deploy as a Service

Two example helpers are included in `deploy/`:

- `deploy/windows-install-service.ps1` — PowerShell helper to register a Windows service using `sc.exe`. Edit the script arguments with the path to your Python executable inside the virtualenv and the path to `app.py`, then run the script as Administrator.

Example (PowerShell Admin):

```powershell
# Adjust paths appropriately
.\deploy\windows-install-service.ps1 -ServiceName "etisalat-logs" -PythonExe "C:\opt\venv\Scripts\python.exe" -AppPath "C:\opt\etisalat_logs_portal\app.py"
sc.exe start etisalat-logs
```

Notes for Windows services:
- Using `sc.exe` is simple but doesn't provide advanced process management; consider using NSSM (Non-Sucking Service Manager) if you need better behavior (auto-restart, stdout capture).

- `deploy/systemd/etisalat-logs-portal.service` — a sample systemd unit. Copy it to `/etc/systemd/system/etisalat-logs-portal.service`, update `ExecStart` and `WorkingDirectory` to your deployment paths, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable etisalat-logs-portal
sudo systemctl start etisalat-logs-portal
sudo journalctl -u etisalat-logs-portal -f
```

Set environment variables in a systemd drop-in or rely on `deploy_config.json` for settings.

## Admin: reload config without restart

If you set a `RELOAD_TOKEN` (env) or `reload_token` in `deploy_config.json`, you can update `deploy_config.json` on disk and call the reload endpoint to apply database overrides, SMTP, and site settings immediately:

```bash
curl -X POST -H "X-Reload-Token: your-token-here" http://127.0.0.1:5000/__reload_config
```

The endpoint returns JSON with `site`, `smtp`, and `db_overrides` that were applied.

## Tests

Run unit tests with pytest. The test suite uses the seeded SQLite DBs by default.

```powershell
pip install -r requirements.txt
python seed_dbs.py
pytest
```

## Troubleshooting

- 404 on `/static/img/logo.png`: ensure your logo file exists at `static/img/logo.png` or set `SITE_LOGO`/`site.logo` to another valid path.
- SMTP errors: verify host/port/auth and `SMTP_USE_TLS` are correct. The app logs exceptions when sending fails.
- Database connection errors: ensure drivers for your DB are installed (e.g., `psycopg2-binary` for Postgres, `pymysql` for MySQL). Add them to `requirements.txt` if needed in your environment.

## Where to edit behavior

- SQL and returned columns: `db_config.json` (`select_query`) and `app.py`'s `query_logs()` control which columns are returned and how parameters are passed. If you change the selected columns, update any UI code that relies on column names.
- Email formatting: `send_logs_via_email()` in `app.py` builds the HTML email — edit styles or content there.
- UI layout and colors: `templates/index.html` and `static/css/styles.css`.

## Final notes

 - Keep secrets out of version control. Use environment variables or secrets manager in production.
 - For production scaling consider running behind a reverse proxy (nginx) and using a WSGI server.

If you'd like, I can add a small admin page to edit `SITE_CONFIG` from the browser (authenticated) or add a Dockerfile to containerize the app.

## Oracle Notes (B2C Frontend)

If you plan to use Oracle for the `b2c_frontend` dataset, set the environment variable `DB_URI_B2C_FE` to a SQLAlchemy-compatible Oracle URI. Example:

```ini
DB_URI_B2C_FE=oracle+cx_oracle://user:pass@host:1521/?service_name=ORCLPDB1
```

Requirements and tips:
- Install `cx_Oracle` (or `oracledb` as compatible replacement) into your virtualenv and add it to `requirements.txt` if you rely on Oracle in CI.
- On Windows you also need Oracle Instant Client installed and accessible (add its `bin` to `PATH`). See Oracle docs for the correct Instant Client package.
- The `db_config.json` entry for `b2c_frontend` in this repo uses a placeholder `${DB_URI_B2C_FE}` which the app resolves at startup from environment variables. Do not commit credentials to the repo.
- The provided Oracle query in `db_config.json` is executed with SQLAlchemy `text()` and named parameters; if you encounter binding errors, you may need to adapt `query_logs()` to use positional params or adjust the SQL to match your Oracle driver semantics.

## Installing DB drivers (Oracle & MySQL)

If you plan to connect to Oracle or MySQL databases, install the required drivers in your virtualenv. Examples:

PowerShell (Windows):

```powershell
# Activate your venv first
. .venv\Scripts\Activate

# Install MySQL driver
pip install pymysql

# Oracle: either cx_Oracle (older) or oracledb (recommended modern driver)
pip install cx_Oracle
# or
pip install oracledb
```

Oracle Instant Client (Windows):

- Download the appropriate Oracle Instant Client package for your platform from: https://www.oracle.com/database/technologies/instant-client.html
- Unzip/install and add the Instant Client `bin` folder to your `PATH` (System Properties -> Environment Variables on Windows).
- After installing Instant Client, `cx_Oracle` (or `oracledb` configured to use the client) will be able to connect.

Notes:
- Only add these drivers to `requirements.txt` if you want CI to install them; Oracle Instant Client itself is not installable via pip and must be installed on the host OS.
- If you use Docker or containerized deployments, include the Instant Client RPMs or packages in your image and set `LD_LIBRARY_PATH` appropriately on Linux.
"# Portal" 
