function Connect-MuMuLocalPort {
    param([string]$AdbPath, [int]$Port)
    if ($Port -lt 1 -or $Port -gt 65535 -or $Port -eq 5037) { return }
    $probe = New-Object System.Diagnostics.Process
    $probe.StartInfo.FileName = $AdbPath
    $probe.StartInfo.Arguments = 'connect 127.0.0.1:' + $Port
    $probe.StartInfo.UseShellExecute = $false
    $probe.StartInfo.CreateNoWindow = $true
    $probe.StartInfo.RedirectStandardOutput = $true
    $probe.StartInfo.RedirectStandardError = $true
    try {
        if ($probe.Start()) {
            if (-not $probe.WaitForExit(4000)) {
                $probe.Kill()
                $probe.WaitForExit()
            }
        }
    } finally { $probe.Dispose() }
}

function Find-MuMuLocalPorts {
    # Probe only listening sockets owned by the running MuMu processes.
    $mumuIds = @(Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ProcessName -like '*MuMu*' } |
        Select-Object -ExpandProperty Id)
    if ($mumuIds.Count -eq 0) { return }
    try {
        Get-NetTCPConnection -State Listen -ErrorAction Stop |
            Where-Object { $mumuIds -contains $_.OwningProcess -and
                $_.LocalAddress -in @('127.0.0.1', '0.0.0.0', '::') -and $_.LocalPort -ne 5037 } |
            Select-Object -ExpandProperty LocalPort -Unique |
            Sort-Object |
            Select-Object -First 16
    } catch {
        Write-Host 'Windows ne permet pas de lire les ports locaux de MuMu.'
    }
}
