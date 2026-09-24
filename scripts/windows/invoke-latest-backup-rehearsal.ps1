<#!
.SYNOPSIS
Verifies that the newest encrypted backup can restore into an isolated database.
#>
[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [string]$BackupDirectory = (Join-Path $RepositoryRoot '.local\backups'),
    [string]$SavedPassphrasePath = (Join-Path $env:LOCALAPPDATA 'AssetGuard\backup-passphrase.dpapi')
)
$ErrorActionPreference = 'Stop'
$latest = Get-ChildItem -LiteralPath $BackupDirectory -Filter '*.agbackup' -File |
    Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
if (-not $latest) { throw "No encrypted backup was found in '$BackupDirectory'." }
& (Join-Path $PSScriptRoot 'verify-backup-restore.ps1') -RepositoryRoot $RepositoryRoot `
    -BackupFile $latest.FullName -SavedPassphrasePath $SavedPassphrasePath -NonInteractive
if ($LASTEXITCODE -ne 0) { throw 'The isolated restore rehearsal failed.' }
