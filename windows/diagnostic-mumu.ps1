$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'mumu-connection.ps1')
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
        Write-Host 'Recherche automatique du port local de MuMu...'
        $ports = @(Find-MuMuLocalPorts)
        foreach ($localPort in $ports) {
            Write-Host ('Verification du port MuMu ' + $localPort + '...')
            Connect-MuMuLocalPort -AdbPath $adb -Port $localPort
        }
        $devices = @(Find-Devices)
    }
    if ($devices.Count -eq 0) {
        Write-Host 'Aucune connexion trouvee. Garde le debogage ADB local active et Hacoo ouvert.'
        Write-Host 'Si aucun port n est visible dans MuMu, ne devine pas de numero : envoie une capture de cette fenetre.'
        $portText = Read-Host 'Port ADB local si connu (sinon Entree pour arreter)'
        if (-not $portText) { throw 'Detection automatique non concluante. Aucun port saisi.' }
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
    # A fresh name prevents a failed dump from reusing an older screen.
    $captureId = [Guid]::NewGuid().ToString('N')
    $remotePath = '/sdcard/hacoo-automation-' + $captureId + '.xml'
    $localPath = Join-Path $folder ('capture-' + $captureId + '.xml')
    $oldPreference = $ErrorActionPreference
    try {
        # Some MuMu builds return a nonzero code even after writing the XML.
        # Only this read-only capture ignores exit codes; validate the new file.
        $ErrorActionPreference = 'Continue'
        & $adb -s $serial shell uiautomator dump $remotePath
        & $adb -s $serial pull $remotePath $localPath
        $ErrorActionPreference = $oldPreference
        if (-not (Test-Path -LiteralPath $localPath -PathType Leaf)) {
            throw 'MuMu n a pas fourni de nouveau fichier XML. Copie les messages ADB affiches ci-dessus.'
        }
        $document = New-Object System.Xml.XmlDocument
        $document.XmlResolver = $null
        try { $document.Load($localPath) } catch {
            throw 'Le fichier recupere est incomplet ou illisible. Garde Hacoo ouvert et relance le diagnostic.'
        }
        if ($document.DocumentElement.Name -ne 'hierarchy' -or $document.SelectNodes('/hierarchy//node').Count -eq 0) {
            throw 'Le fichier ne contient pas la structure d un ecran Android.'
        }
        Move-Item -LiteralPath $localPath -Destination (Join-Path $folder 'hacoo-ui.xml') -Force
    } finally {
        $ErrorActionPreference = 'Continue'
        & $adb -s $serial shell rm -f $remotePath
        Remove-Item -LiteralPath $localPath -ErrorAction SilentlyContinue
        $ErrorActionPreference = $oldPreference
    }
    @{adb_path=$adb; serial=$serial} | ConvertTo-Json | Set-Content (Join-Path $folder 'local-config.json')
    $persistentFolder = Join-Path $env:LOCALAPPDATA 'HacooAffiliate'
    New-Item -ItemType Directory -Force $persistentFolder | Out-Null
    @{adb_path=$adb; serial=$serial} | ConvertTo-Json | Set-Content (Join-Path $persistentFolder 'mumu-config.json')
    Write-Host 'Diagnostic termine : fichier hacoo-ui.xml dans le dossier diagnostic-mumu.'
    Write-Host 'Ce fichier contient les textes visibles a l ecran. Verifie-le avant de le partager.'
    Write-Host 'Aucun lien cree, aucune annonce publiee.'
    Start-Process explorer.exe -ArgumentList ('"' + $folder + '"')
} catch {
    Write-Host ('Diagnostic arrete : ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
