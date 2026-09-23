<#
Creates a local AssetGuard MVP-minimal GLPI Agent inventory.
It neither configures GLPI Agent nor defines a server, credentials, TLS exceptions,
or a listener. Output can contain device identifiers and must remain outside Git.
#>
[CmdletBinding()]
param(
    [string]$OutputRoot = 'C:\AssetGuardPhase0'
)

$ErrorActionPreference = 'Stop'
$agentRoot = 'C:\Program Files\GLPI-Agent'
$agentLauncher = Join-Path $agentRoot 'glpi-agent.bat'
$profilePath = Join-Path $PSScriptRoot 'glpi-agent-minimal-profile.cfg'

if (-not (Test-Path -LiteralPath $agentLauncher) -or -not (Test-Path -LiteralPath $profilePath)) {
    throw 'GLPI Agent is not installed in the expected upstream location.'
}

# Every supported inventory category not required by the MVP hardware profile.
$excludedCategories = @(
    'accesslog', 'antivirus', 'battery', 'database', 'environment', 'firewall',
    'input', 'licenseinfo', 'local_group', 'local_user', 'lvm', 'modem', 'port',
    'printer', 'process', 'provider', 'psu', 'registry', 'remote_mgmt', 'rudder',
    'slot', 'software', 'sound', 'usb', 'user', 'virtualmachine'
)

$rawDirectory = Join-Path $OutputRoot 'raw'
$stateDirectory = Join-Path $OutputRoot 'state'
New-Item -ItemType Directory -Force -Path $rawDirectory, $stateDirectory | Out-Null
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stderrFile = Join-Path $OutputRoot "glpi-agent-minimal-$timestamp.stderr.log"

& $agentLauncher "--conf-file=$profilePath" "--vardir=$stateDirectory" "--local=$rawDirectory" '--json' '--force' '--logger=stderr' 2> $stderrFile
if ($LASTEXITCODE -ne 0) {
    throw "GLPI Agent inventory failed. See the local diagnostic file: $stderrFile"
}

$rawFile = Get-ChildItem -LiteralPath $rawDirectory -Filter '*.json' |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName
if (-not $rawFile) {
    throw 'GLPI Agent completed without a local JSON inventory.'
}

try {
    $payload = Get-Content -LiteralPath $rawFile -Raw | ConvertFrom-Json -ErrorAction Stop
} catch {
    throw "GLPI inventory did not produce valid JSON: $rawFile"
}

$forbiddenTopLevelFields = @('ACCESSLOG', 'ENVS', 'LICENSEINFOS', 'LOCAL_GROUPS', 'LOCAL_USERS', 'PROCESSES', 'SOFTWARES', 'USERS')
$presentForbiddenFields = @($forbiddenTopLevelFields | Where-Object { $payload.PSObject.Properties.Name -contains $_ })
if ($presentForbiddenFields.Count -gt 0) {
    throw "Minimal profile unexpectedly contains forbidden fields: $($presentForbiddenFields -join ', ')"
}

$file = Get-Item -LiteralPath $rawFile
$hash = Get-FileHash -LiteralPath $rawFile -Algorithm SHA256
[pscustomobject]@{
    File = $file.FullName
    Bytes = $file.Length
    SHA256 = $hash.Hash
    TopLevelFields = @($payload.PSObject.Properties.Name) -join ', '
    ExcludedCategories = $excludedCategories -join ', '
}
