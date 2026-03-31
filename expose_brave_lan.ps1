param(
    [string]$WslDistro = "",
    [int[]]$Ports = @(4001, 4002)
)

$ErrorActionPreference = "Stop"

function Get-WslIp {
    param([string]$DistroName)

    $invokeArgs = @("bash", "-lc", "hostname -I | cut -d' ' -f1")
    if ($DistroName) {
        $invokeArgs = @("-d", $DistroName) + $invokeArgs
    }

    $raw = (& wsl.exe @invokeArgs | Out-String).Trim()
    if (-not $raw) {
        throw "Could not determine WSL IPv4 address."
    }

    $match = [regex]::Match($raw, '\b\d{1,3}(?:\.\d{1,3}){3}\b')
    if (-not $match.Success) {
        throw "Could not parse a valid WSL IPv4 address from: $raw"
    }

    return $match.Value
}

function Ensure-FirewallRule {
    param([string]$RuleName, [int[]]$RulePorts)

    $existing = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
    if ($existing) {
        Remove-NetFirewallRule -DisplayName $RuleName | Out-Null
    }

    New-NetFirewallRule `
        -DisplayName $RuleName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $RulePorts | Out-Null
}

$wslIp = Get-WslIp -DistroName $WslDistro

foreach ($port in $Ports) {
    & netsh interface portproxy delete v4tov4 listenaddress=0.0.0.0 listenport=$port | Out-Null
    & netsh interface portproxy add v4tov4 `
        listenaddress=0.0.0.0 `
        listenport=$port `
        connectaddress=$wslIp `
        connectport=$port | Out-Null
}

Ensure-FirewallRule -RuleName "Brave Evennia LAN" -RulePorts $Ports

Write-Host "Brave LAN forwarding is active."
Write-Host "WSL IP: $wslIp"
Write-Host "Ports: $($Ports -join ', ')"
