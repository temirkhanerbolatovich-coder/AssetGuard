<#!
.SYNOPSIS
Installs daily encrypted backup and weekly isolated restore-rehearsal tasks.

.DESCRIPTION
Tasks run only while the current Windows user is logged in. That is deliberate:
Docker Desktop and the DPAPI-protected passphrase are tied to this account.
#>
[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')]
    [string]$BackupTime = '02:00',
    [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')]
    [string]$RehearsalTime = '03:00',
    [string]$TaskPrefix = 'AssetGuard'
)
$ErrorActionPreference = 'Stop'
$secretPath = Join-Path $env:LOCALAPPDATA 'AssetGuard\backup-passphrase.dpapi'
if (-not (Test-Path -LiteralPath $secretPath)) {
    throw "Create the protected passphrase first: .\set-backup-passphrase.ps1 (expected '$secretPath')."
}
$powershell = (Get-Command powershell.exe -ErrorAction Stop).Source
$backupScript = Join-Path $PSScriptRoot 'backup-database.ps1'
$rehearsalScript = Join-Path $PSScriptRoot 'invoke-latest-backup-rehearsal.ps1'
$backupArgs = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$backupScript`" -RepositoryRoot `"$RepositoryRoot`" -SavedPassphrasePath `"$secretPath`" -NonInteractive"
$rehearsalArgs = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$rehearsalScript`" -RepositoryRoot `"$RepositoryRoot`" -SavedPassphrasePath `"$secretPath`""
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName "$TaskPrefix Daily Encrypted Backup" -Action (New-ScheduledTaskAction -Execute $powershell -Argument $backupArgs) `
    -Trigger (New-ScheduledTaskTrigger -Daily -At $BackupTime) -Settings $settings -Principal $principal -Force | Out-Null
Register-ScheduledTask -TaskName "$TaskPrefix Weekly Restore Rehearsal" -Action (New-ScheduledTaskAction -Execute $powershell -Argument $rehearsalArgs) `
    -Trigger (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $RehearsalTime) -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Installed '$TaskPrefix Daily Encrypted Backup' and '$TaskPrefix Weekly Restore Rehearsal'."
