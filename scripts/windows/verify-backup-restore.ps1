<#
.SYNOPSIS
Safely rehearses restoration of an encrypted AssetGuard database backup.

.DESCRIPTION
Decrypts an .agbackup file into a private temporary file, restores it into an
isolated disposable PostgreSQL container with no published ports, verifies the
schema revision and key table counts, then removes the container and plaintext.
It never writes to the configured AssetGuard PostgreSQL service.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$BackupFile,

    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [Security.SecureString]$Passphrase,
    [switch]$CompareWithCurrentDatabase,
    [ValidateRange(10, 180)]
    [int]$StartupTimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'backup-crypto.ps1')

function Get-AssetGuardTableCounts([string[]]$PsqlCommand) {
    $query = @"
SELECT 'alembic_version=' || COALESCE((SELECT version_num FROM alembic_version LIMIT 1), 'missing')
UNION ALL SELECT 'assets=' || count(*) FROM assets
UNION ALL SELECT 'managed_endpoints=' || count(*) FROM managed_endpoints
UNION ALL SELECT 'raw_inventories=' || count(*) FROM raw_inventories
UNION ALL SELECT 'hardware_snapshots=' || count(*) FROM hardware_snapshots
UNION ALL SELECT 'incidents=' || count(*) FROM incidents
UNION ALL SELECT 'vision_scans=' || count(*) FROM vision_scans;
"@
    $result = & $PsqlCommand[0] $PsqlCommand[1..($PsqlCommand.Length - 1)] -At -v ON_ERROR_STOP=1 -c $query
    if ($LASTEXITCODE -ne 0) { throw 'Could not read restored database verification counts.' }
    $counts = [ordered]@{}
    foreach ($line in $result) {
        $pair = $line -split '=', 2
        if ($pair.Count -eq 2) { $counts[$pair[0]] = $pair[1] }
    }
    if (-not $counts['alembic_version']) { throw 'Restored database does not contain an Alembic schema revision.' }
    return $counts
}

$resolvedBackup = (Resolve-Path -LiteralPath $BackupFile -ErrorAction Stop).Path
if (-not $resolvedBackup.EndsWith('.agbackup', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Recovery rehearsal accepts only an AES-256-GCM .agbackup file.'
}
if (-not (Get-Command docker.exe -ErrorAction SilentlyContinue)) { throw 'Docker Desktop is required for an isolated restore rehearsal.' }
& docker.exe version --format '{{.Server.Version}}' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop is not running or cannot be reached.' }

$envPath = Join-Path $RepositoryRoot '.env'
$composePath = Join-Path $RepositoryRoot 'infra\containers\docker-compose.yml'
if ($CompareWithCurrentDatabase -and (-not (Test-Path -LiteralPath $envPath))) {
    throw "Missing '$envPath', required only for -CompareWithCurrentDatabase."
}

$containerName = "assetguard-restore-rehearsal-$([Guid]::NewGuid().ToString('N').Substring(0, 12))"
$restoreDatabase = 'assetguard_restore'
$restoreUser = 'assetguard_restore'
$passwordBytes = [byte[]]::new(24)
[Security.Cryptography.RandomNumberGenerator]::Fill($passwordBytes)
$restorePassword = [Convert]::ToBase64String($passwordBytes)
[Array]::Clear($passwordBytes, 0, $passwordBytes.Length)
$temporarySql = Join-Path ([IO.Path]::GetTempPath()) "assetguard-rehearsal-$([Guid]::NewGuid().ToString('N')).sql"
$sourceCounts = $null

try {
    $Passphrase = Get-AssetGuardBackupPassphrase $Passphrase
    Unprotect-AssetGuardBackup -InputFile $resolvedBackup -OutputFile $temporarySql -Passphrase $Passphrase
    if ((Get-Item -LiteralPath $temporarySql).Length -eq 0) { throw 'Decryption produced an empty SQL file.' }

    if ($CompareWithCurrentDatabase) {
        foreach ($line in Get-Content -LiteralPath $envPath) {
            if ($line -match '^([^#=]+)=(.*)$') { Set-Item -Path "Env:$($matches[1])" -Value $matches[2] }
        }
        $sourceCounts = Get-AssetGuardTableCounts @('docker.exe', 'compose', '--env-file', $envPath, '-f', $composePath, 'exec', '-T', 'postgres', 'psql', '-U', $env:ASSETGUARD_POSTGRES_USER, '-d', $env:ASSETGUARD_POSTGRES_DB)
    }

    & docker.exe run -d --rm --name $containerName `
        -e "POSTGRES_DB=$restoreDatabase" -e "POSTGRES_USER=$restoreUser" -e "POSTGRES_PASSWORD=$restorePassword" `
        postgres:17-alpine | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not start the isolated PostgreSQL restore container.' }

    $deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    do {
        # pg_isready can succeed during image initialization before POSTGRES_DB
        # has been created. Query the exact target database instead.
        & docker.exe exec $containerName psql -U $restoreUser -d $restoreDatabase -At -c 'SELECT 1' 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { break }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    if ($LASTEXITCODE -ne 0) { throw "Isolated PostgreSQL did not become ready within $StartupTimeoutSeconds seconds." }

    Get-Content -LiteralPath $temporarySql -Raw | & docker.exe exec -i $containerName psql -v ON_ERROR_STOP=1 -U $restoreUser -d $restoreDatabase | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'SQL restore into the isolated database failed.' }

    $restoredCounts = Get-AssetGuardTableCounts @('docker.exe', 'exec', $containerName, 'psql', '-U', $restoreUser, '-d', $restoreDatabase)
    if ($sourceCounts) {
        $differences = @($sourceCounts.Keys | Where-Object { $sourceCounts[$_] -ne $restoredCounts[$_] })
        if ($differences.Count) {
            throw "Restored counts differ from the current database: $($differences -join ', '). The backup may be older than the source, so re-run without -CompareWithCurrentDatabase to validate it independently."
        }
    }

    [pscustomobject]@{
        BackupFile = $resolvedBackup
        IsolatedContainer = $containerName
        ComparedWithCurrentDatabase = [bool]$CompareWithCurrentDatabase
        Verification = 'PASS'
        RestoredCounts = $restoredCounts
    }
}
finally {
    if (Test-Path -LiteralPath $temporarySql) { Remove-Item -LiteralPath $temporarySql -Force }
    & docker.exe rm -f $containerName 2>$null | Out-Null
    $restorePassword = $null
}
