[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [string]$OutputDirectory = (Join-Path $RepositoryRoot '.local\backups'),
    [Security.SecureString]$Passphrase,
    [string]$OffsiteTarget
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'backup-crypto.ps1')
$envPath = Join-Path $RepositoryRoot '.env'
foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match '^([^#=]+)=(.*)$') { Set-Item -Path "Env:$($matches[1])" -Value $matches[2] }
}
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$destination = Join-Path $OutputDirectory "assetguard-$(Get-Date -Format 'yyyyMMdd-HHmmss').sql.agbackup"
$temporarySql = Join-Path ([IO.Path]::GetTempPath()) "assetguard-$([Guid]::NewGuid().ToString('N')).sql"
try {
    docker compose --env-file $envPath -f (Join-Path $RepositoryRoot 'infra\containers\docker-compose.yml') exec -T postgres pg_dump -U $env:ASSETGUARD_POSTGRES_USER -d $env:ASSETGUARD_POSTGRES_DB --format=plain --no-owner | Out-File -LiteralPath $temporarySql -Encoding utf8NoBOM
    if ($LASTEXITCODE -ne 0) { throw 'Database backup failed.' }
    $Passphrase = Get-AssetGuardBackupPassphrase $Passphrase
    Protect-AssetGuardBackup -InputFile $temporarySql -OutputFile $destination -Passphrase $Passphrase
} finally {
    if (Test-Path -LiteralPath $temporarySql) { Remove-Item -LiteralPath $temporarySql -Force }
}

if ($OffsiteTarget) {
    $name = Split-Path -Leaf $destination
    if ($OffsiteTarget -match '^[A-Za-z]:[\\/]' -or $OffsiteTarget.StartsWith('\\')) {
        New-Item -ItemType Directory -Force -Path $OffsiteTarget | Out-Null
        Copy-Item -LiteralPath $destination -Destination (Join-Path $OffsiteTarget $name) -Force
    } else {
        if (-not (Get-Command rclone -ErrorAction SilentlyContinue)) { throw 'rclone is required for a cloud OffsiteTarget.' }
        $remote = "$($OffsiteTarget.TrimEnd('/'))/$name"
        & rclone copyto $destination $remote
        if ($LASTEXITCODE -ne 0) { throw 'Encrypted off-site upload failed.' }
    }
    Write-Host "Encrypted off-site copy created: $OffsiteTarget"
}
Write-Host "Encrypted backup created: $destination"
