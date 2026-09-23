<# Runs one privacy-limited inventory using secrets from the local .env file. #>
[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [uri]$GatewayUri = 'http://127.0.0.1:8000/internal/inventories'
)

$ErrorActionPreference = 'Stop'
$envPath = Join-Path $RepositoryRoot '.env'
if (-not (Test-Path -LiteralPath $envPath)) { throw "Missing $envPath." }
foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match '^([^#=]+)=(.*)$') { Set-Item -Path "Env:$($matches[1])" -Value $matches[2] }
}
& (Join-Path $PSScriptRoot 'send-minimal-inventory.ps1') -GatewayUri $GatewayUri
$headers = @{ 'X-AssetGuard-Admin-Token' = $env:ASSETGUARD_ADMIN_SHARED_SECRET }
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/admin/maintenance/evaluate-endpoints' -Headers $headers | Out-Null
