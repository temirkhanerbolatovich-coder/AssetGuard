<#
.SYNOPSIS
Installs the AssetGuard Agent from the one-time configuration created by the Windows installer.

.DESCRIPTION
The graphical installer writes a short-lived configuration file with an ACL that allows only
SYSTEM and local Administrators to read it. This helper converts the inventory secret to a
SecureString, invokes the reviewed service installer, then removes the configuration in a
finally block. It never writes the secret to output or a command line.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ConfigPath
)

$ErrorActionPreference = 'Stop'

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Remove-OneTimeConfig([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $firstLine = Get-Content -LiteralPath $Path -TotalCount 1 -ErrorAction SilentlyContinue
    if ($firstLine -eq '{') {
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Administrator)) {
    throw 'AssetGuard Agent installer must run elevated.'
}

try {
    if (-not (Test-Path -LiteralPath $ConfigPath)) {
        throw 'The one-time installer configuration was not found.'
    }
    $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json -ErrorAction Stop
    $gateway = [string]$config.gatewayUri
    $username = [string]$config.agentUsername
    $secret = [string]$config.inventorySecret
    $runNow = [bool]$config.runInventoryNow

    if ([string]::IsNullOrWhiteSpace($gateway) -or [string]::IsNullOrWhiteSpace($username) -or [string]::IsNullOrWhiteSpace($secret)) {
        throw 'Installer configuration is incomplete.'
    }

    $secureSecret = ConvertTo-SecureString -String $secret -AsPlainText -Force
    $arguments = @{
        GatewayUri = [uri]$gateway
        AgentUsername = $username
        InventorySecret = $secureSecret
    }
    if ($runNow) { $arguments.RunInventoryNow = $true }
    & (Join-Path $PSScriptRoot 'install-assetguard-agent-service.ps1') @arguments
}
finally {
    # The only plaintext copy created by the wizard must not remain on disk.
    Remove-OneTimeConfig $ConfigPath
}
