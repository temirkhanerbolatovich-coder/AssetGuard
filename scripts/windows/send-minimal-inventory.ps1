<#
Collects an AssetGuard-minimal GLPI inventory locally, then sends that exact JSON
to the AssetGuard internal ingestion contract. It never persists a Gateway token.

For production, GatewayUri must use HTTPS. Plain HTTP is allowed only for the
loopback laboratory endpoints localhost and 127.0.0.1.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [uri]$GatewayUri,
    [string]$OutputRoot = 'C:\AssetGuardPhase0',
    [string]$IngestToken = $env:ASSETGUARD_INVENTORY_SHARED_SECRET,
    [string]$SourceVersion = '1.19',
    [string]$SchemaVersion = 'glpi-agent-minimal-v1'
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($IngestToken)) {
    throw 'Set ASSETGUARD_INVENTORY_SHARED_SECRET or pass -IngestToken. Do not save this secret in the script.'
}

$isLoopback = $GatewayUri.Host -in @('localhost', '127.0.0.1', '::1')
if ($GatewayUri.Scheme -ne 'https' -and -not ($GatewayUri.Scheme -eq 'http' -and $isLoopback)) {
    throw 'GatewayUri must use HTTPS outside a loopback laboratory endpoint.'
}

$collector = Join-Path $PSScriptRoot 'collect-minimal-inventory.ps1'
$collection = & $collector -OutputRoot $OutputRoot
$payload = Get-Content -LiteralPath $collection.File -Raw
$idempotencyKey = [guid]::NewGuid().ToString()

$headers = @{
    'X-AssetGuard-Ingest-Token' = $IngestToken
    'X-AssetGuard-Idempotency-Key' = $idempotencyKey
    'X-AssetGuard-Source' = 'GLPI_AGENT'
    'X-AssetGuard-Source-Version' = $SourceVersion
    'X-AssetGuard-Schema-Version' = $SchemaVersion
    'X-AssetGuard-Inventory-Type' = 'FULL'
}

$response = Invoke-RestMethod -Method Post -Uri $GatewayUri -Headers $headers -ContentType 'application/json' -Body $payload
[pscustomobject]@{
    InventoryFile = $collection.File
    InventorySHA256 = $collection.SHA256
    IdempotencyKey = $idempotencyKey
    GatewayResponse = $response
}
