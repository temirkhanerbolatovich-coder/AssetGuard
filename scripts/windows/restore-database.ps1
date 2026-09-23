[CmdletBinding(SupportsShouldProcess, ConfirmImpact='High')]
param(
    [Parameter(Mandatory)][string]$BackupFile,
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..'))
)
$ErrorActionPreference = 'Stop'
$resolvedBackup = (Resolve-Path -LiteralPath $BackupFile).Path
$envPath = Join-Path $RepositoryRoot '.env'
foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match '^([^#=]+)=(.*)$') { Set-Item -Path "Env:$($matches[1])" -Value $matches[2] }
}
if ($PSCmdlet.ShouldProcess($env:ASSETGUARD_POSTGRES_DB, "restore database from $resolvedBackup")) {
    Get-Content -LiteralPath $resolvedBackup -Raw | docker compose --env-file $envPath -f (Join-Path $RepositoryRoot 'infra\containers\docker-compose.yml') exec -T postgres psql -v ON_ERROR_STOP=1 -U $env:ASSETGUARD_POSTGRES_USER -d $env:ASSETGUARD_POSTGRES_DB
    if ($LASTEXITCODE -ne 0) { throw 'Database restore failed.' }
}
