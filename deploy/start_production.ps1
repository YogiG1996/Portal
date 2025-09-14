# Set Oracle Client paths
$env:PATH = "$env:PATH;C:\oracle\instantclient_19_19"
$env:ORACLE_HOME = "C:\oracle\instantclient_19_19"
$env:TNS_ADMIN = "C:\oracle\instantclient_19_19\network\admin"

# Database connection strings
$env:DB_URI_FE_UAT = "oracle+cx_oracle://username:password@//hostname:port/service_name"
$env:DB_URI_FE_PD = "oracle+cx_oracle://username:password@//hostname:port/service_name"
$env:DB_URI_MAGENTO_UAT = "mysql+pymysql://username:password@hostname:port/database_name"
$env:DB_URI_MAGENTO_PD = "mysql+pymysql://username:password@hostname:port/database_name"
$env:DB_URI_SELFCARE_UAT = "oracle+cx_oracle://username:password@//hostname:port/service_name"
$env:DB_URI_SELFCARE_PD = "oracle+cx_oracle://username:password@//hostname:port/service_name"

# Set Oracle Client path
$env:PATH = "$env:PATH;C:\oracle\instantclient_19_19"
# If using a specific Oracle Home:
$env:ORACLE_HOME = "C:\oracle\instantclient_19_19"
$env:TNS_ADMIN = "C:\oracle\instantclient_19_19\network\admin"

# Flask production settings
$env:FLASK_ENV = "production"
$env:FLASK_DEBUG = "0"

# Install required packages if not already installed
python -m pip install -r requirements.txt

# Verify the format of connection strings in config
$content = Get-Content -Raw db_config.json
if ($content -match '\$-{') {
    Write-Host "Fixing connection string format in db_config.json..."
    $content = $content -replace '\$-{([^}]+)}', '${$1}'
    $content | Set-Content db_config.json
    Write-Host "Fixed connection string format."
}

# Start the Flask app with Gunicorn
Write-Host "Starting application with Gunicorn..."
python -m gunicorn --bind 0.0.0.0:5000 --log-file logs/gunicorn.log --log-level info app:app