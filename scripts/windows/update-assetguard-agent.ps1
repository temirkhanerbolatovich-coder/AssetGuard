<# Upgrade the existing protected connection without asking for/copying a new secret. #>
[CmdletBinding()]
param(
    [ValidateRange(1, 1440)][int]$CollectionIntervalMinutes = 5,
    [uri]$GatewayUri
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'assetguard-agent-runtime.ps1')
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]::new($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run the Agent update as administrator.' }
$key = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SOFTWARE\GLPI-Agent', $false)
if (-not $key) { throw 'Existing Agent configuration was not found.' }
try {
    $gateway = if ($GatewayUri) { $GatewayUri } else { [uri][string]$key.GetValue('server') }
    $username = [string]$key.GetValue('user')
    $plain = [string]$key.GetValue('password')
    $legacyMarker = Join-Path $env:ProgramData 'AssetGuard\glpi-agent-registry-acl.sddl'
    # Released 0.1.6 protected the registry but did not write an installer tag.
    if ($key.GetValue('tag') -notlike 'assetguard-installer-*' -and -not (Test-Path -LiteralPath $legacyMarker)) { throw 'This is not an AssetGuard-managed Agent.' }
    $secret = ConvertTo-SecureString $plain -AsPlainText -Force
}
finally { $key.Dispose(); $plain = $null }
try {
    & (Join-Path $PSScriptRoot 'install-assetguard-agent-service.ps1') -GatewayUri $gateway -AgentUsername $username -InventorySecret $secret -InstallerVersion '0.1.8' -CollectionIntervalMinutes $CollectionIntervalMinutes -SkipUpstreamInstall -RunInventoryNow
}
finally { $secret = $null }
