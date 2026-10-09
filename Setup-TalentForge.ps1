$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
Push-Location (Join-Path $taskRoot 'backend')
try {
    if (-not (Test-Path '.venv\Scripts\python.exe')) { py -3.14 -m venv .venv; if ($LASTEXITCODE -ne 0) { throw 'Python 3.14 is required.' } }
    & '.venv\Scripts\python.exe' -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
    & '.venv\Scripts\python.exe' manage.py migrate
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
    & '.venv\Scripts\python.exe' manage.py seed_demo
} finally { Pop-Location }
Push-Location (Join-Path $taskRoot 'frontend')
try { npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' } } finally { Pop-Location }
Write-Host 'Ready. Run Start-TalentForge.ps1. Demo account details: backend\DEMO-CREDENTIALS.txt'