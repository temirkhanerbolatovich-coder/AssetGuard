<# Registers a user-level watchdog that restores the temporary public demo URL. #>
[CmdletBinding()]
param(
    [uri]$LocalUrl = 'http://127.0.0.1:8000',
    [string]$TaskName = 'AssetGuard Quick Tunnel watchdog'
)

$ErrorActionPreference = 'Stop'
if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) { throw 'cloudflared is not installed.' }
$runner = Join-Path $PSScriptRoot 'run-quick-tunnel-watchdog.ps1'
if (-not (Test-Path -LiteralPath $runner)) { throw "Missing $runner." }
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$currentUser = "$env:USERDOMAIN\$env:USERNAME"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -LocalUrl `"$LocalUrl`""
$action = New-ScheduledTaskAction -Execute $pwsh -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Days 3650) -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'Restarts AssetGuard Cloudflare Quick Tunnel after a disconnect.' -User $currentUser -Force -ErrorAction Stop | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Installed and started '$TaskName'. Current state: $env:LOCALAPPDATA\AssetGuard\quick-tunnel.json"
