<# Creates a new local .env with random development-only secrets. #>
[CmdletBinding()]
param([string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')))

$ErrorActionPreference = 'Stop'
$envPath = Join-Path $RepositoryRoot '.env'
if (Test-Path -LiteralPath $envPath) { throw ".env already exists at $envPath. It was not changed." }
function New-Secret {
    $bytes = [byte[]]::new(32)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    [Convert]::ToBase64String($bytes).Replace('+', '-').Replace('/', '_').TrimEnd('=')
}
$databasePassword = New-Secret
$content = @"
ASSETGUARD_POSTGRES_DB=assetguard
ASSETGUARD_POSTGRES_USER=assetguard
ASSETGUARD_POSTGRES_PASSWORD=$databasePassword
ASSETGUARD_POSTGRES_PORT=5433
ASSETGUARD_DATABASE_URL=postgresql+psycopg://assetguard:$databasePassword@127.0.0.1:5433/assetguard
ASSETGUARD_INVENTORY_SHARED_SECRET=$(New-Secret)
ASSETGUARD_ADMIN_SHARED_SECRET=$(New-Secret)
ASSETGUARD_MAX_INVENTORY_PAYLOAD_BYTES=2097152
"@
Set-Content -LiteralPath $envPath -Value $content -Encoding utf8NoBOM -NoNewline
Write-Host "Created $envPath. Keep it private; it is excluded from Git."
