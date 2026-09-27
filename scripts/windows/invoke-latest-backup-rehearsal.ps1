<#!
.SYNOPSIS
Verifies that the newest encrypted backup can restore into an isolated database.
#>
[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [string]$BackupDirectory = (Join-Path $RepositoryRoot '.local\backups'),
    [string]$OffsiteTarget,
    [string]$SavedPassphrasePath = (Join-Path $env:LOCALAPPDATA 'AssetGuard\backup-passphrase.dpapi')
)
$ErrorActionPreference = 'Stop'

function Resolve-RcloneExecutable {
    $command = Get-Command rclone -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $wingetPackages = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    $candidate = Get-ChildItem -LiteralPath $wingetPackages -Directory -Filter 'Rclone.Rclone_*' -ErrorAction SilentlyContinue |
        ForEach-Object { Get-ChildItem -LiteralPath $_.FullName -Filter 'rclone.exe' -Recurse -File -ErrorAction SilentlyContinue } |
        Select-Object -First 1
    if ($candidate) { return $candidate.FullName }

    throw 'rclone is required for an off-site restore rehearsal.'
}

$downloadedBackup = $null
try {
    if ($OffsiteTarget) {
        $rclone = Resolve-RcloneExecutable
        $entries = & $rclone lsf $OffsiteTarget --files-only --format 'pt'
        if ($LASTEXITCODE -ne 0) { throw "Could not list encrypted backups in '$OffsiteTarget'." }
        $latestEntry = $entries |
            ForEach-Object {
                $parts = $_ -split ';', 2
                if ($parts.Count -eq 2 -and $parts[0].EndsWith('.agbackup')) {
                    [pscustomobject]@{ Name = $parts[0]; LastWriteTime = [DateTimeOffset]::Parse($parts[1]) }
                }
            } |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if (-not $latestEntry) { throw "No encrypted backup was found in '$OffsiteTarget'." }

        $stageDirectory = Join-Path $BackupDirectory '.offsite-rehearsal'
        New-Item -ItemType Directory -Force -Path $stageDirectory | Out-Null
        $downloadedBackup = Join-Path $stageDirectory $latestEntry.Name
        & $rclone copyto "$($OffsiteTarget.TrimEnd('/'))/$($latestEntry.Name)" $downloadedBackup
        if ($LASTEXITCODE -ne 0) { throw 'Could not download the latest off-site backup.' }
        $backupFile = $downloadedBackup
    } else {
        $latest = Get-ChildItem -LiteralPath $BackupDirectory -Filter '*.agbackup' -File |
            Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
        if (-not $latest) { throw "No encrypted backup was found in '$BackupDirectory'." }
        $backupFile = $latest.FullName
    }

    & (Join-Path $PSScriptRoot 'verify-backup-restore.ps1') -RepositoryRoot $RepositoryRoot `
        -BackupFile $backupFile -SavedPassphrasePath $SavedPassphrasePath -NonInteractive
    if ($LASTEXITCODE -ne 0) { throw 'The isolated restore rehearsal failed.' }
}
finally {
    if ($downloadedBackup -and (Test-Path -LiteralPath $downloadedBackup)) {
        Remove-Item -LiteralPath $downloadedBackup -Force
    }
}
