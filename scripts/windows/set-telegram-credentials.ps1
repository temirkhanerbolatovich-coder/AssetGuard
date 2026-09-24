<#
.SYNOPSIS
Stores AssetGuard Telegram credentials with Windows DPAPI for the current user.

.DESCRIPTION
The resulting CLIXML credential file can be decrypted only by the same Windows
account on this computer. It keeps the bot token out of .env and Task Scheduler.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [Security.SecureString]$BotToken,
    [Parameter(Mandatory)] [ValidatePattern('^-?\d+$')] [string]$ChatId,
    [string]$Path = (Join-Path $env:LOCALAPPDATA 'AssetGuard\telegram-credentials.clixml')
)
$ErrorActionPreference = 'Stop'
$directory = Split-Path -Parent $Path
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$credential = [PSCredential]::new($ChatId, $BotToken)
Export-Clixml -LiteralPath $Path -InputObject $credential -Force
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = New-Object Security.AccessControl.FileSecurity
$acl.SetOwner($identity)
$acl.SetAccessRuleProtection($true, $false)
$acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($identity, 'FullControl', 'Allow')))
Set-Acl -LiteralPath $Path -AclObject $acl
Write-Host "Saved DPAPI-protected Telegram credentials: $Path"
