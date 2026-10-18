$ErrorActionPreference = 'Stop'
try {
    Write-Host 'Ouvre MuMu, puis Hacoo > Affiliate Program > Promotion > Link Customize.'
    Write-Host 'Ferme la fenetre Promote Link pour afficher le champ de saisie.'
    Read-Host 'Appuie sur Entree quand cet ecran est ouvert' | Out-Null
    $roots = @()
    foreach ($process in (Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -like '*MuMu*' })) {
        try {
            if ($process.Path) {
                $parent = Split-Path -Parent $process.Path
                $roots += $parent
                $up = Split-Path -Parent $parent
                if ((Split-Path -Leaf $up) -match 'MuMu') { $roots += $up }
            }
        } catch { }
    }
    $adb = $null
    foreach ($root in ($roots | Select-Object -Unique)) {
        $found = Get-ChildItem -LiteralPath $root -Filter adb.exe -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) { $adb = $found.FullName; break }
    }
    if (-not $adb) {
        $adb = (Read-Host 'Chemin complet du fichier adb.exe fourni avec MuMu').Trim('"')
    }
    if (-not (Test-Path -LiteralPath $adb -PathType Leaf)) { throw 'adb.exe introuvable.' }
    function Find-Devices {
        $output = & $adb devices
        if ($LASTEXITCODE -ne 0) { throw 'ADB ne repond pas.' }
        return @($output | Where-Object { $_ -match '^\S+\s+device$' } | ForEach-Object { ($_ -split '\s+')[0] })
    }
    $devices = @(Find-Devices)
    if ($devices.Count -eq 0) {
        Write-Host 'Active le debogage ADB dans MuMu et releve le port indique par MuMu.'
        $portText = Read-Host 'Port ADB local affiche dans MuMu'
        $portNumber = 0
        if (-not [int]::TryParse($portText, [ref]$portNumber) -or $portNumber -lt 1 -or $portNumber -gt 65535) { throw 'Port invalide.' }
        & $adb connect ('127.0.0.1:' + $portNumber)
        if ($LASTEXITCODE -ne 0) { throw 'Connexion locale ADB impossible.' }
        $devices = @(Find-Devices)
    }
    if ($devices.Count -eq 0) { throw 'Aucun emulateur autorise ; verifie MuMu et ses reglages ADB.' }
    $serial = $devices[0]
    if ($devices.Count -gt 1) {
        Write-Host ('Emulateurs connectes : ' + ($devices -join ', '))
        $serial = Read-Host 'Identifiant exact de ton emulateur Hacoo'
        if ($devices -notcontains $serial) { throw 'Identifiant inconnu.' }
    }
    $folder = Join-Path (Split-Path -Parent $PSScriptRoot) 'diagnostic-mumu'
    New-Item -ItemType Directory -Force $folder | Out-Null
    & $adb -s $serial shell uiautomator dump /sdcard/hacoo-automation.xml
    if ($LASTEXITCODE -ne 0) { throw 'Impossible de lire la structure de cet ecran.' }
    & $adb -s $serial pull /sdcard/hacoo-automation.xml (Join-Path $folder 'hacoo-ui.xml')
    if ($LASTEXITCODE -ne 0) { throw 'Impossible de recuperer le diagnostic.' }
    @{adb_path=$adb; serial=$serial} | ConvertTo-Json | Set-Content (Join-Path $folder 'local-config.json')
    Write-Host 'Diagnostic termine : fichier hacoo-ui.xml dans le dossier diagnostic-mumu.'
    Write-Host 'Ce fichier contient les textes visibles a l ecran. Verifie-le avant de le partager.'
    Write-Host 'Aucun lien cree, aucune annonce publiee.'
    Start-Process explorer.exe -ArgumentList ('"' + $folder + '"')
} catch {
    Write-Host ('Diagnostic arrete : ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
