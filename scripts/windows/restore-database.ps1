[CmdletBinding(SupportsShouldProcess, ConfirmImpact='High')]
param(
    [Parameter(Mandatory)][string]$BackupFile,
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [Security.SecureString]$Passphrase
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'backup-crypto.ps1')
$resolvedBackup = (Resolve-Path -LiteralPath $BackupFile).Path
$envPath = Join-Path $RepositoryRoot '.env'
foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match '^([^#=]+)=(.*)$') { Set-Item -Path "Env:$($matches[1])" -Value $matches[2] }
}
if ($PSCmdlet.ShouldProcess($env:ASSETGUARD_POSTGRES_DB, "restore database from $resolvedBackup")) {
    $restoreSource = $resolvedBackup
    $temporarySql = $null
    try {
        if ($resolvedBackup.EndsWith('.agbackup', [StringComparison]::OrdinalIgnoreCase)) {
            $temporarySql = Join-Path ([IO.Path]::GetTempPath()) "assetguard-restore-$([Guid]::NewGuid().ToString('N')).sql"
            $Passphrase = Get-AssetGuardBackupPassphrase $Passphrase
            Unprotect-AssetGuardBackup -InputFile $resolvedBackup -OutputFile $temporarySql -Passphrase $Passphrase
            $restoreSource = $temporarySql
        }
        Get-Content -LiteralPath $restoreSource -Raw | docker compose --env-file $envPath -f (Join-Path $RepositoryRoot 'infra\containers\docker-compose.yml') exec -T postgres psql -v ON_ERROR_STOP=1 -U $env:ASSETGUARD_POSTGRES_USER -d $env:ASSETGUARD_POSTGRES_DB
        if ($LASTEXITCODE -ne 0) { throw 'Database restore failed.' }
    } finally {
        if ($temporarySql -and (Test-Path -LiteralPath $temporarySql)) { Remove-Item -LiteralPath $temporarySql -Force }
    }
}
