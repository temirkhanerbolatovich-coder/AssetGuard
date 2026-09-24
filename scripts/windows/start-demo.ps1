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
$fallbackPython = 'C:\AssetGuardDev\backend-venv\Scripts\python.exe'
$fallbackBackend = 'C:\AssetGuardWorkspace'
$requiresAsciiFallback = $RepositoryRoot -match '[^\x00-\x7F]'
if ($requiresAsciiFallback -and (Test-Path -LiteralPath $fallbackPython) -and (Test-Path -LiteralPath $fallbackBackend)) {
    $python = $fallbackPython
    $backendPath = $fallbackBackend
} elseif (-not (Test-Path -LiteralPath $python)) {
    throw "Missing $python. Create the Python 3.12 environment and install backend[dev,vision] first."
}
$venvRoot = Split-Path -Parent (Split-Path -Parent $python)
$sitePackages = Join-Path $venvRoot 'Lib\site-packages'
$pythonPathEntries = @((Join-Path $backendPath 'src'))
if (Test-Path -LiteralPath $sitePackages) { $pythonPathEntries += $sitePackages }
if ($env:PYTHONPATH) { $pythonPathEntries += $env:PYTHONPATH.Split([IO.Path]::PathSeparator) }
$env:PYTHONPATH = ($pythonPathEntries | Where-Object { $_ } | Select-Object -Unique) -join [IO.Path]::PathSeparator
docker compose --env-file $envPath -f (Join-Path $RepositoryRoot 'infra\containers\docker-compose.yml') up -d postgres
Push-Location $backendPath
try {
    # The current Windows profile contains a UTF-8 editable-install .pth under
    # a Cyrillic path. Skip site initialization and explicitly add source plus
    # the venv's installed packages so both startup and migrations work there.
    & $python -S -m alembic -c alembic.ini upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
    & $python -S -m uvicorn assetguard.app:app --host 127.0.0.1 --port $Port
} finally { Pop-Location }
