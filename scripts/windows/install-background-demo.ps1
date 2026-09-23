<#
Registers user-level scheduled tasks for the local AssetGuard MVP.
The tasks run only while this Windows user is logged on. No task is created until
this explicit script is run; use uninstall-background-demo.ps1 to remove them.
#>
[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [int]$InventoryEveryHours = 4
)

$ErrorActionPreference = 'Stop'
if ($InventoryEveryHours -lt 1 -or $InventoryEveryHours -gt 24) { throw 'InventoryEveryHours must be from 1 to 24.' }
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$runner = Join-Path $PSScriptRoot 'run-scheduled-inventory.ps1'
$starter = Join-Path $PSScriptRoot 'start-demo.ps1'
if (-not (Test-Path (Join-Path $RepositoryRoot '.env'))) { throw 'Create .env before installing scheduled tasks.' }
$currentUser = "$env:USERDOMAIN\$env:USERNAME"

$apiAction = New-ScheduledTaskAction -Execute $pwsh -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$starter`" -RepositoryRoot `"$RepositoryRoot`""
$apiTrigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$inventoryAction = New-ScheduledTaskAction -Execute $pwsh -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -RepositoryRoot `"$RepositoryRoot`""
$inventoryTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Hours $InventoryEveryHours) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -StartWhenAvailable
Register-ScheduledTask -TaskName 'AssetGuard API (local demo)' -Action $apiAction -Trigger $apiTrigger -Settings $settings -Description 'Starts AssetGuard API at user logon.' -User $currentUser -Force -ErrorAction Stop | Out-Null
Register-ScheduledTask -TaskName 'AssetGuard inventory (local demo)' -Action $inventoryAction -Trigger $inventoryTrigger -Settings $settings -Description "Runs privacy-limited GLPI inventory every $InventoryEveryHours hours." -User $currentUser -Force -ErrorAction Stop | Out-Null
Write-Host 'Scheduled tasks installed. Sign out/in to start the API task, or start it manually from Task Scheduler.'
