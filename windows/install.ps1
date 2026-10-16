$ErrorActionPreference = 'Stop'
try {
    $source = Split-Path -Parent $PSScriptRoot
    $root = Join-Path $env:LOCALAPPDATA 'TelegramReposter'
    Write-Host 'Installation du bot Telegram pour ce compte Windows.'
    $python = $null
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $candidates += (& py -3 -c 'import sys; print(sys.executable)' 2>$null)
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $candidates += (& python -c 'import sys; print(sys.executable)' 2>$null)
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            & $candidate -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'
            if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
        }
    }
    if (-not $python) {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host 'Installation de Python 3.12 depuis le catalogue Windows...'
            & winget install --id Python.Python.3.12 --exact --source winget --scope user --silent --accept-source-agreements --accept-package-agreements
            $candidate = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
            if (Test-Path $candidate) { $python = $candidate }
        }
    }
    if (-not $python) {
        Start-Process 'https://www.python.org/downloads/windows/'
        throw 'Installe Python 3.12 ou plus depuis la page officielle, puis relance INSTALLER.bat.'
    }
    if (Test-Path (Join-Path $root 'python-path.txt')) {
        throw 'Le bot est deja installe. Utilise le raccourci de demarrage ou ARRETER.bat ; ne reinstalle pas pendant son fonctionnement.'
    }
    New-Item -ItemType Directory -Force $root | Out-Null
    Copy-Item (Join-Path $source 'bot.py') $root -Force
    Copy-Item (Join-Path $source 'windows') $root -Recurse -Force
    New-Item -ItemType Directory -Force (Join-Path $root 'data') | Out-Null
    if ((Test-Path (Join-Path $source 'data\history.sqlite3')) -and -not (Test-Path (Join-Path $root 'data\history.sqlite3'))) {
        Copy-Item (Join-Path $source 'data\history.sqlite3') (Join-Path $root 'data\history.sqlite3')
    }
    Write-Host 'Colle le jeton de ton bot ci-dessous. Il ne sera pas affiche.'
    $token = Read-Host 'Jeton Telegram' -AsSecureString
    if ($token.Length -eq 0) { throw 'Jeton vide : installation interrompue.' }
    $token | ConvertFrom-SecureString | Set-Content (Join-Path $root 'token.protected')
    $env:TELEGRAM_BOT_TOKEN = [System.Net.NetworkCredential]::new('', $token).Password
    $env:BOT_DATA_DIR = Join-Path $root 'data'
    $env:PYTHONUTF8 = '1'
    Write-Host 'Verification du bot et des sources (aucun message envoye)...'
    & $python (Join-Path $root 'bot.py') --check
    if ($LASTEXITCODE -ne 0) { throw 'Jeton ou permissions invalides. Corrige puis relance INSTALLER.bat.' }
    & $python (Join-Path $root 'bot.py') --scan
    if ($LASTEXITCODE -ne 0) { throw 'Sources inaccessibles. Verifie Internet puis relance INSTALLER.bat.' }
    $python | Set-Content (Join-Path $root 'python-path.txt')
    Remove-Item Env:TELEGRAM_BOT_TOKEN
    $shell = New-Object -ComObject WScript.Shell
    foreach ($folder in @([Environment]::GetFolderPath('Startup'), [Environment]::GetFolderPath('Desktop'))) {
        $shortcut = $shell.CreateShortcut((Join-Path $folder 'Bot Telegram.lnk'))
        $shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
        $shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $root 'windows\run.ps1') + '"'
        $shortcut.WorkingDirectory = $root
        $shortcut.WindowStyle = 7
        $shortcut.Save()
    }
    Remove-Item (Join-Path $root 'STOP') -ErrorAction SilentlyContinue
    Write-Host 'Demarrage. Une premiere publication peut partir maintenant si le dernier lot date de plus de 45 minutes.'
    Start-Process powershell.exe -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $root 'windows\run.ps1') + '"') -WindowStyle Minimized
    Write-Host 'Installe : demarrage automatique a chaque ouverture de session Windows.'
    Write-Host 'IMPORTANT : garde le PC allume, connecte et branche ; desactive la veille sur secteur dans les parametres Windows.'
    Write-Host ('Journaux : ' + (Join-Path $root 'logs'))
} catch {
    Write-Host ('Installation arretee : ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {
    Remove-Item Env:TELEGRAM_BOT_TOKEN -ErrorAction SilentlyContinue
}
