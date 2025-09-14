# PowerShell helper to register the Flask app as a Windows service.
# This script assumes you have Python and the app in place. It uses `sc.exe` to create a service
# that runs the venv python directly. Adjust paths before running.
# Usage (PowerShell as Admin):
#   .\windows-install-service.ps1 -ServiceName "etisalat-logs" -PythonExe "C:\path\to\venv\Scripts\python.exe" -AppPath "C:\path\to\etisalat_logs_portal\app.py"
param(
  [string]$ServiceName = "etisalat-logs",
  [string]$PythonExe = "$env:USERPROFILE\.venv\Scripts\python.exe",
  [string]$AppPath = "$PWD\app.py",
  [string]$WorkingDir = "$PWD",
  [string]$Args = "-u $AppPath"
)

Write-Output "Registering service: $ServiceName"
# Build the binary path with arguments
$binPath = "\"$PythonExe\" $Args"

# Create the service (requires admin)
sc.exe create $ServiceName binPath= "$binPath" start= auto DisplayName= "Etisalat Logs Portal"
sc.exe description $ServiceName "Runs the Etisalat Application Logs Portal (Flask app)"

Write-Output "Service created. To start: sc.exe start $ServiceName"

Write-Output "Notes:"
Write-Output " - Ensure the python executable path is correct and the virtualenv has required packages installed."
Write-Output " - You may prefer to use NSSM (Non-Sucking Service Manager) for better control of services."