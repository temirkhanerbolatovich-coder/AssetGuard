<# Removes the user-level AssetGuard Quick Tunnel watchdog task. #>
[CmdletBinding()]
param([string]$TaskName = 'AssetGuard Quick Tunnel watchdog')

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Removed '$TaskName'."
