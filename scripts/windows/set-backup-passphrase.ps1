<#!
.SYNOPSIS
Stores the AssetGuard backup passphrase protected by the current Windows user's DPAPI key.

.DESCRIPTION
The created file is not a reusable plaintext secret. It can be decrypted only
by the same Windows account on the same PC and is intended for the scheduled
backup and restore-rehearsal tasks.
#>
[CmdletBinding()]
param(
    [Security.SecureString]$Passphrase,
    [string]$Path = (Join-Path $env:LOCALAPPDATA 'AssetGuard\backup-passphrase.dpapi')
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'backup-crypto.ps1')

if (-not $Passphrase) { $Passphrase = Read-Host 'New backup passphrase (minimum 16 characters)' -AsSecureString }
# Validate length before writing, without retaining a plaintext copy.
$validationBytes = Get-AssetGuardPassphraseBytes -Passphrase $Passphrase
[Array]::Clear($validationBytes, 0, $validationBytes.Length)
$directory = Split-Path -Parent $Path
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$protected = ConvertFrom-SecureString -SecureString $Passphrase
Set-Content -LiteralPath $Path -Value $protected -NoNewline -Encoding ascii

# Keep the DPAPI blob private even before DPAPI protection is considered.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().User
$acl = New-Object Security.AccessControl.FileSecurity
$acl.SetOwner($identity)
$acl.SetAccessRuleProtection($true, $false)
$acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($identity, 'FullControl', 'Allow')))
Set-Acl -LiteralPath $Path -AclObject $acl
Write-Host "Saved a DPAPI-protected backup passphrase for the current Windows user: $Path"
