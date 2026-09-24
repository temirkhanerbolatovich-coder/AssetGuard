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
$diagnosticDirectory = Join-Path $env:ProgramData 'AssetGuard'
$diagnosticPath = Join-Path $diagnosticDirectory 'last-agent-install-error.txt'

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

function Write-InstallDiagnostic([System.Exception]$Exception) {
    try {
        New-Item -ItemType Directory -Force -Path $diagnosticDirectory | Out-Null
        # Exceptions emitted by the reviewed installer never include the inventory secret.
        Set-Content -LiteralPath $diagnosticPath -Value $Exception.ToString() -Encoding utf8 -NoNewline
        & icacls.exe $diagnosticPath '/inheritance:r' '/grant:r' '*S-1-5-18:(F)' '*S-1-5-32-544:(F)' | Out-Null
    }
    catch {
        # Preserve the original installer failure even if diagnostic recording is unavailable.
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
catch {
    Write-InstallDiagnostic $_.Exception
    throw
}
finally {
    # The only plaintext copy created by the wizard must not remain on disk.
    Remove-OneTimeConfig $ConfigPath
}
