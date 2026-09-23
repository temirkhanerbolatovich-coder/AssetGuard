[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [string]$OutputDirectory = (Join-Path $RepositoryRoot '.local\backups')
)
$ErrorActionPreference = 'Stop'
$envPath = Join-Path $RepositoryRoot '.env'
foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match '^([^#=]+)=(.*)$') { Set-Item -Path "Env:$($matches[1])" -Value $matches[2] }
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$destination = Join-Path $OutputDirectory "assetguard-$(Get-Date -Format 'yyyyMMdd-HHmmss').sql"
docker compose --env-file $envPath -f (Join-Path $RepositoryRoot 'infra\containers\docker-compose.yml') exec -T postgres pg_dump -U $env:ASSETGUARD_POSTGRES_USER -d $env:ASSETGUARD_POSTGRES_DB --format=plain --no-owner | Out-File -LiteralPath $destination -Encoding utf8NoBOM
if ($LASTEXITCODE -ne 0) { throw 'Database backup failed.' }
Write-Host "Backup created: $destination"
