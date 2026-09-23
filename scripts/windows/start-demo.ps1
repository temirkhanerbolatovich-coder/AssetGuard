<# Starts the local AssetGuard MVP API after provisioning PostgreSQL and migrations. #>
[CmdletBinding()]
param([string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')), [int]$Port = 8000)

$ErrorActionPreference = 'Stop'
$envPath = Join-Path $RepositoryRoot '.env'
if (-not (Test-Path -LiteralPath $envPath)) { throw "Missing $envPath. Run scripts/windows/new-local-env.ps1 first." }
foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match '^([^#=]+)=(.*)$') { Set-Item -Path "Env:$($matches[1])" -Value $matches[2] }
}
$backendPath = Join-Path $RepositoryRoot 'backend'
$python = Join-Path $backendPath '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw "Missing $python. Create the Python 3.12 environment and install backend[dev] first." }
docker compose --env-file $envPath -f (Join-Path $RepositoryRoot 'infra\containers\docker-compose.yml') up -d postgres
Push-Location $backendPath
try {
    & $python -m alembic -c alembic.ini upgrade head
    & $python -m uvicorn assetguard.app:app --host 127.0.0.1 --port $Port
} finally { Pop-Location }
