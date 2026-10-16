$root = Join-Path $env:LOCALAPPDATA 'TelegramReposter'
if (-not (Test-Path $root)) { Write-Host 'Bot non installe.'; exit }
New-Item -ItemType File -Force (Join-Path $root 'STOP') | Out-Null
$script = Join-Path $root 'bot.py'
Get-CimInstance Win32_Process | Where-Object {
    $_.Name -like 'python*.exe' -and $_.CommandLine -and $_.CommandLine.Contains($script)
} | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
Write-Host 'Arret demande. Pour reprendre, lance DEMARRER.bat.'
