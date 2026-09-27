[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [string]$OutputDirectory = (Join-Path $RepositoryRoot '.local\backups'),
    [Security.SecureString]$Passphrase,
    [string]$OffsiteTarget,
    [ValidateRange(1, 3650)]
    [int]$LocalRetentionDays = 14,
    [ValidateRange(1, 3650)]
    [int]$OffsiteRetentionDays = 30,
    [string]$SavedPassphrasePath = (Join-Path $env:LOCALAPPDATA 'AssetGuard\backup-passphrase.dpapi'),
    [switch]$NonInteractive
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'backup-crypto.ps1')

function Resolve-RcloneExecutable {
    $command = Get-Command rclone -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $wingetPackages = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    $candidate = Get-ChildItem -LiteralPath $wingetPackages -Directory -Filter 'Rclone.Rclone_*' -ErrorAction SilentlyContinue |
        ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -Filter 'rclone.exe' -Recurse -File -ErrorAction SilentlyContinue } |
        Select-Object -First 1
    if ($candidate) { return $candidate.FullName }

    throw 'rclone is required for a cloud OffsiteTarget. Install it with: winget install --id Rclone.Rclone --exact'
}

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
    $Passphrase = Get-AssetGuardBackupPassphrase -Passphrase $Passphrase -SavedPassphrasePath $SavedPassphrasePath -NonInteractive:$NonInteractive
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
        $rclone = Resolve-RcloneExecutable
        $remote = "$($OffsiteTarget.TrimEnd('/'))/$name"
        & $rclone copyto $destination $remote
        if ($LASTEXITCODE -ne 0) { throw 'Encrypted off-site upload failed.' }
        & $rclone delete $OffsiteTarget --min-age "$($OffsiteRetentionDays)d"
        if ($LASTEXITCODE -ne 0) { throw 'Off-site backup retention cleanup failed.' }
    }
    Write-Host "Encrypted off-site copy created: $OffsiteTarget"
}

$localCutoff = (Get-Date).ToUniversalTime().AddDays(-$LocalRetentionDays)
Get-ChildItem -LiteralPath $OutputDirectory -Filter '*.agbackup' -File |
    Where-Object { $_.LastWriteTimeUtc -lt $localCutoff } |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }
Write-Host "Encrypted backup created: $destination"
