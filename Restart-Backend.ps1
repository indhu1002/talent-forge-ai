$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskPidFile=Join-Path $taskRoot '.server-pids'
if (-not (Test-Path -LiteralPath $taskPidFile)) { throw 'Run Start-TalentForge.ps1 first.' }
$taskPids=Get-Content -LiteralPath $taskPidFile
$taskBackendPid=$taskPids | Select-Object -First 1
$taskProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$taskBackendPid" -ErrorAction SilentlyContinue
if ($taskProcess -and $taskProcess.CommandLine -like '*manage.py runserver*') { taskkill.exe /PID $taskBackendPid /T /F | Out-Null }
$taskBackend=Start-Process -FilePath (Join-Path $taskRoot 'backend\.venv\Scripts\python.exe') -ArgumentList @('manage.py','runserver','127.0.0.1:8000','--noreload') -WorkingDirectory (Join-Path $taskRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskRoot 'backend\server.log') -RedirectStandardError (Join-Path $taskRoot 'backend\server-error.log') -PassThru
@($taskBackend.Id,($taskPids | Select-Object -Last 1)) | Set-Content -LiteralPath $taskPidFile
Write-Host 'Backend restarted. Refresh http://localhost:5173.'