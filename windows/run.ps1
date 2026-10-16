$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$mutex = New-Object System.Threading.Mutex($false, 'Local\Hacoo2K26Launcher')
if (-not $mutex.WaitOne(0)) { exit }
try {
    $python = (Get-Content (Join-Path $root 'python-path.txt') -Raw).Trim()
    $env:TELEGRAM_BOT_TOKEN = [System.Net.NetworkCredential]::new('', (Get-Content (Join-Path $root 'token.protected') -Raw | ConvertTo-SecureString)).Password
    $env:BOT_DATA_DIR = Join-Path $root 'data'
    $env:PYTHONUTF8 = '1'
    $env:PYTHONUNBUFFERED = '1'
    New-Item -ItemType Directory -Force (Join-Path $root 'logs') | Out-Null
    while (-not (Test-Path (Join-Path $root 'STOP')) ) {
        $log = Join-Path $root ('logs\bot-' + (Get-Date -Format 'yyyy-MM-dd') + '.log')
        ('Lancement : ' + (Get-Date)) | Out-File $log -Append -Encoding utf8
        $ErrorActionPreference = 'Continue'
        & $python -u (Join-Path $root 'bot.py') *>> $log
        $ErrorActionPreference = 'Stop'
        if (-not (Test-Path (Join-Path $root 'STOP'))) { Start-Sleep -Seconds 30 }
    }
} finally {
    Remove-Item Env:TELEGRAM_BOT_TOKEN -ErrorAction SilentlyContinue
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
