$ErrorActionPreference='Stop'
$taskEnv=Join-Path $PSScriptRoot 'backend\.env'
if (-not (Test-Path -LiteralPath $taskEnv)) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'backend\.env.example') -Destination $taskEnv }
$taskSecureKey=Read-Host 'Enter your new OpenAI API key (hidden)' -AsSecureString
$taskPointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($taskSecureKey)
try {
    $taskKey=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($taskPointer).Trim()
    if (-not $taskKey.StartsWith('sk-') -or $taskKey.Contains([char]10) -or $taskKey.Contains([char]13)) { throw 'Enter a valid single-line OpenAI API key.' }
    $taskText=[System.IO.File]::ReadAllText($taskEnv)
    $taskText=[regex]::Replace($taskText,'(?m)^OPENAI_API_KEY=.*\r?\n?','')
    [System.IO.File]::WriteAllText($taskEnv,$taskText.TrimEnd()+[char]10+'OPENAI_API_KEY='+$taskKey+[char]10,(New-Object System.Text.UTF8Encoding($false)))
    Write-Host 'Key saved privately in backend\.env. Run .\Restart-Backend.ps1 to apply it.'
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($taskPointer)
    $taskKey=$null
}