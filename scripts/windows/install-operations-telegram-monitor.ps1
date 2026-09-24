<# Installs a current-user task that evaluates AssetGuard operations hourly. #>
[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [ValidateRange(5, 1440)] [int]$EveryMinutes = 60,
    [string]$TaskName = 'AssetGuard Telegram operations monitor'
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath (Join-Path $RepositoryRoot '.env'))) { throw "Missing '$RepositoryRoot\.env'." }
$runner = Join-Path $PSScriptRoot 'send-operations-telegram-alert.ps1'
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$runner`" -RepositoryRoot `"$RepositoryRoot`""
$action = New-ScheduledTaskAction -Execute $pwsh -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'Sends deduplicated AssetGuard operations alerts to Telegram.' -User "$env:USERDOMAIN\$env:USERNAME" -Force | Out-Null
Write-Host "Installed '$TaskName'; it checks operations every $EveryMinutes minutes."
