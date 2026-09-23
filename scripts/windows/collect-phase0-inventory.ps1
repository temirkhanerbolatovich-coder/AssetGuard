<#
Creates a local, full JSON inventory for the AssetGuard Phase 0 laboratory.
It never configures a server, credentials, TLS exceptions, or a listener.
The raw result can contain device identifiers and must remain outside Git.
#>
[CmdletBinding()]
param(
    [string]$OutputRoot = 'C:\AssetGuardPhase0'
)

$ErrorActionPreference = 'Stop'
$agentRoot = 'C:\Program Files\GLPI-Agent'
$agentExe = Join-Path $agentRoot 'perl\bin\glpi-agent.exe'
$inventoryScript = Join-Path $agentRoot 'perl\bin\glpi-inventory'

if (-not (Test-Path -LiteralPath $agentExe) -or -not (Test-Path -LiteralPath $inventoryScript)) {
    throw 'GLPI Agent is not installed in the expected upstream location.'
}

$rawDirectory = Join-Path $OutputRoot 'raw'
New-Item -ItemType Directory -Force -Path $rawDirectory | Out-Null
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$rawFile = Join-Path $rawDirectory "inventory-full-$timestamp.json"
$stderrFile = Join-Path $OutputRoot "glpi-inventory-$timestamp.stderr.log"

& $agentExe $inventoryScript --json 1> $rawFile 2> $stderrFile
if ($LASTEXITCODE -ne 0) {
    throw "GLPI inventory failed. See the local diagnostic file: $stderrFile"
}

try {
    $payload = Get-Content -LiteralPath $rawFile -Raw | ConvertFrom-Json -ErrorAction Stop
} catch {
    throw "GLPI inventory did not produce valid JSON: $rawFile"
}

$file = Get-Item -LiteralPath $rawFile
$hash = Get-FileHash -LiteralPath $rawFile -Algorithm SHA256
[pscustomobject]@{
    File = $file.FullName
    Bytes = $file.Length
    SHA256 = $hash.Hash
    TopLevelFields = @($payload.PSObject.Properties.Name) -join ', '
}
