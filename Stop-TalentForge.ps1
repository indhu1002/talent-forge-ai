$taskRoot = $PSScriptRoot
$pidFile = Join-Path $taskRoot '.server-pids'
if (Test-Path -LiteralPath $pidFile) {
    foreach ($taskProcessId in Get-Content -LiteralPath $pidFile) {
        $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$taskProcessId" -ErrorAction SilentlyContinue
        if ($taskProcess -and ($taskProcess.CommandLine -like '*manage.py runserver*' -or $taskProcess.CommandLine -like '*npm.cmd run dev*')) {
            taskkill.exe /PID $taskProcessId /T /F
        }
    }
    Remove-Item -LiteralPath $pidFile
}
if (Test-Path -LiteralPath (Join-Path $taskRoot ".mysql-pid")) { & (Join-Path $taskRoot "backend\.venv\Scripts\python.exe") (Join-Path $taskRoot "backend\stop_mysql.py"); Remove-Item -LiteralPath (Join-Path $taskRoot ".mysql-pid") }