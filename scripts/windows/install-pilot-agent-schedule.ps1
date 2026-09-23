<#
Installs one privacy-limited AssetGuard inventory task on this Windows PC.
Run this locally on each pilot endpoint. Credentials are read only at run time
from the protected .env file; they are never embedded in the Scheduled Task.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [uri]$GatewayUri,
    [Parameter(Mandatory)] [string]$RepositoryRoot,
    [ValidateRange(1, 24)] [int]$EveryHours = 4,
    [string]$NetworkTarget,
    [string]$TaskName = 'AssetGuard pilot inventory'
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath (Join-Path $RepositoryRoot '.env'))) { throw "Missing $RepositoryRoot\.env." }
if ($GatewayUri.Scheme -ne 'https' -and $GatewayUri.Host -notin @('localhost', '127.0.0.1', '::1')) { throw 'Use HTTPS for a remote GatewayUri.' }
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$runner = Join-Path $PSScriptRoot 'run-scheduled-inventory.ps1'
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -RepositoryRoot `"$RepositoryRoot`" -GatewayUri `"$GatewayUri`""
if ($NetworkTarget) { $arguments += " -NetworkTarget `"$NetworkTarget`"" }
$action = New-ScheduledTaskAction -Execute $pwsh -Argument $arguments
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Hours $EveryHours) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 20) -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "AssetGuard privacy-limited inventory every $EveryHours hours." -Force -ErrorAction Stop | Out-Null
Write-Host "Installed '$TaskName'. It will send a baseline-capable inventory every $EveryHours hours."
