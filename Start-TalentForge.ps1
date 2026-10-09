$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$pythonPath = Join-Path $taskRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run Setup-TalentForge.ps1 first.' }
$taskEnv = Join-Path $taskRoot 'backend\.env'
if ((Test-Path -LiteralPath $taskEnv) -and (Get-Content -Raw -LiteralPath $taskEnv) -match 'DB_ENGINE=mysql' -and (Get-Content -Raw -LiteralPath $taskEnv) -match 'MYSQL_PORT=3307') {
    $mysqlPath = 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe'
    if (-not (Get-NetTCPConnection -State Listen -LocalPort 3307 -ErrorAction SilentlyContinue)) {
        if (-not (Test-Path -LiteralPath $mysqlPath)) { throw 'Install MySQL 8 or configure a different database in backend\.env.' }
        $mysqlProcess = Start-Process -FilePath $mysqlPath -ArgumentList @('--no-defaults','--basedir="C:\Program Files\MySQL\MySQL Server 8.0"',"--datadir=`"$taskRoot\mysql-data`"",'--port=3307','--bind-address=127.0.0.1','--mysqlx=0','--console') -WindowStyle Hidden -RedirectStandardOutput "$taskRoot\mysql-data\server.log" -RedirectStandardError "$taskRoot\mysql-data\server-error.log" -PassThru
        $mysqlProcess.Id | Set-Content -LiteralPath "$taskRoot\.mysql-pid"
        for ($attempt=0; $attempt -lt 30; $attempt++) {
            if (Get-NetTCPConnection -State Listen -LocalPort 3307 -ErrorAction SilentlyContinue) { break }
            Start-Sleep -Milliseconds 500
        }
    }
}
if ((Get-NetTCPConnection -State Listen -LocalPort 8000,5173 -ErrorAction SilentlyContinue)) { throw 'Port 8000 or 5173 is occupied. Stop existing development servers first.' }
$backendProcess = Start-Process -FilePath $pythonPath -ArgumentList @('manage.py','runserver','127.0.0.1:8000','--noreload') -WorkingDirectory (Join-Path $taskRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskRoot 'backend\server.log') -RedirectStandardError (Join-Path $taskRoot 'backend\server-error.log') -PassThru
$frontendProcess = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/c','npm.cmd run dev -- --port 5173 --strictPort') -WorkingDirectory (Join-Path $taskRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskRoot 'frontend\server.log') -RedirectStandardError (Join-Path $taskRoot 'frontend\server-error.log') -PassThru
@($backendProcess.Id, $frontendProcess.Id) | Set-Content -LiteralPath (Join-Path $taskRoot '.server-pids')
Write-Host 'Talent Forge AI: http://localhost:5173'
Write-Host 'Run Stop-TalentForge.ps1 to stop the development servers.'