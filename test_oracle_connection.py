import os
import cx_Oracle

# Set environment variables for testing
os.environ['DB_URI_FE_UAT'] = "oracle+cx_oracle://username:password@//hostname:port/service_name"

print("1. cx_Oracle version:", cx_Oracle.version)

try:
    print("2. Oracle Client Version:", cx_Oracle.clientversion())
except Exception as e:
    print("Error getting client version:", str(e))

# Test direct cx_Oracle connection
try:
    # Extract connection details from SQLAlchemy URL
    conn_str = os.environ['DB_URI_FE_UAT'].replace('oracle+cx_oracle://', '')
    username, rest = conn_str.split(':', 1)
    password, host = rest.split('@//', 1)
    
    print("\n3. Testing connection...")
    dsn = cx_Oracle.makedsn(host.split(':')[0], 
                           host.split(':')[1].split('/')[0],
                           service_name=host.split('/')[-1])
    
    print("4. DSN created:", dsn)
except Exception as e:
    print("Error creating connection:", str(e))
    print("\nPlease update the connection details in the start_production.ps1 script with:"
          "\n- Correct username/password"
          "\n- Proper hostname and port"
          "\n- Valid service name")