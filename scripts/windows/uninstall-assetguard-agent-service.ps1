<# Removes only the AssetGuard-owned GLPI Agent service configuration. #>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$AgentRoot = "$env:ProgramFiles\GLPI-Agent",
    [switch]$RemoveUpstreamAgent
)

$ErrorActionPreference = 'Stop'
$serviceName = 'glpi-agent'
$legacyConfigPath = Join-Path $AgentRoot 'etc\conf.d\99-assetguard.cfg'
$registryPath = 'HKLM:\SOFTWARE\GLPI-Agent'
$registryAclBackupPath = Join-Path $env:ProgramData 'AssetGuard\glpi-agent-registry-acl.sddl'
$managedRegistryValues = @('server', 'user', 'password', 'no-category', 'no-compression', 'no-httpd', 'delaytime')

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) { throw 'Run this uninstaller from an elevated PowerShell window.' }
if (Test-Path -LiteralPath $legacyConfigPath) {
    $firstLine = Get-Content -LiteralPath $legacyConfigPath -TotalCount 1 -ErrorAction Stop
    if ($firstLine -notmatch '^# Managed by AssetGuard\.') {
        throw "Refusing to remove '$legacyConfigPath' because it is not an AssetGuard-managed configuration."
    }
}

if ($PSCmdlet.ShouldProcess($serviceName, 'Stop and disable GLPI Agent service')) {
    Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    Set-Service -Name $serviceName -StartupType Disabled -ErrorAction SilentlyContinue
}
if (Test-Path -LiteralPath $registryAclBackupPath -and $PSCmdlet.ShouldProcess($registryPath, 'Remove AssetGuard registry configuration and its stored credential')) {
    foreach ($name in $managedRegistryValues) {
        Remove-ItemProperty -LiteralPath $registryPath -Name $name -ErrorAction SilentlyContinue
    }
    $originalSddl = Get-Content -LiteralPath $registryAclBackupPath -Raw -ErrorAction Stop
    $acl = Get-Acl -LiteralPath $registryPath
    $acl.SetSecurityDescriptorSddlForm($originalSddl.Trim())
    Set-Acl -LiteralPath $registryPath -AclObject $acl
    Remove-Item -LiteralPath $registryAclBackupPath -Force
}
if (Test-Path -LiteralPath $legacyConfigPath -and $PSCmdlet.ShouldProcess($legacyConfigPath, 'Remove legacy AssetGuard configuration')) {
    Remove-Item -LiteralPath $legacyConfigPath -Force
}
if ($RemoveUpstreamAgent) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) { throw 'WinGet is unavailable; remove the upstream GLPI Agent from Windows Apps instead.' }
    if ($PSCmdlet.ShouldProcess('GLPI Agent', 'Uninstall official upstream package')) {
        $process = Start-Process -FilePath $winget.Source -ArgumentList @('uninstall', '--id', 'GLPI-Project.GLPI-Agent', '--exact', '--silent') -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw "WinGet GLPI Agent uninstall failed with exit code $($process.ExitCode)." }
    }
}
Write-Host 'AssetGuard Agent configuration removed. The upstream GLPI Agent package was kept unless -RemoveUpstreamAgent was specified.'
