$ErrorActionPreference = 'Stop'
try {
    $root = Split-Path -Parent $PSScriptRoot
    $configPath = Join-Path $root 'diagnostic-mumu\local-config.json'
    $config = $null
    if (Test-Path $configPath) {
        try { $config = Get-Content $configPath -Raw | ConvertFrom-Json } catch { $config = $null }
    }
    if (-not $config -or -not $config.adb_path -or -not $config.serial -or
        -not (Test-Path -LiteralPath $config.adb_path -PathType Leaf)) {
        Write-Host 'Preparation automatique de MuMu : aucun dossier a copier.'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'diagnostic-mumu.ps1')
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $configPath)) {
            throw 'Diagnostic non termine. Envoie une capture de cette fenetre avec le message ci-dessus.'
        }
        $config = Get-Content $configPath -Raw | ConvertFrom-Json
    }
    $candidates = @()
    $saved = Join-Path $env:LOCALAPPDATA 'TelegramReposter\python-path.txt'
    if (Test-Path $saved) { $candidates += (Get-Content $saved -Raw).Trim() }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $candidates += (& py -3 -c 'import sys; print(sys.executable)' 2>$null)
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $candidates += (& python -c 'import sys; print(sys.executable)' 2>$null)
    }
    $python = $null
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            & $candidate -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'
            if ($LASTEXITCODE -eq 0) { $python = $candidate; break }
        }
    }
    if (-not $python) { throw 'Python 3.12 ou plus est necessaire : https://www.python.org/downloads/windows/' }
    Write-Host 'Ouvre Hacoo > Affiliate Program > Promotion > Link Customize.'
    Write-Host 'Ce test cree un lien affilie sur ton compte. Aucune publication Telegram.'
    $code = Read-Host 'Code produit (7 ou 8 chiffres commencant par 40)'
    if ($code -notmatch '^40[0-9]{5,6}$') { throw 'Code produit invalide.' }
    $env:PYTHONUTF8 = '1'
    & $python (Join-Path $root 'hacoo_mumu.py') --adb $config.adb_path --serial $config.serial convert $code
    if ($LASTEXITCODE -ne 0) { throw 'Conversion non confirmee. Copie le message affiche ci-dessus.' }
    Write-Host 'Conversion terminee, fenetre de resultat fermee. Aucune annonce publiee.'
} catch {
    Write-Host ('Test arrete : ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Envoie une capture de cette fenetre pour continuer.'
} finally {
    Write-Host 'Tu peux lire le resultat ci-dessus. Pour fermer cette fenetre, clique sur la croix X.'
}
