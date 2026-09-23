<# Removes only the two user-level AssetGuard local-demo scheduled tasks. #>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Unregister-ScheduledTask -TaskName 'AssetGuard API (local demo)' -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName 'AssetGuard inventory (local demo)' -Confirm:$false -ErrorAction SilentlyContinue
Write-Host 'AssetGuard local-demo scheduled tasks removed.'
