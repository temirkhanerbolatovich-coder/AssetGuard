<# Removes only the AssetGuard-owned GLPI Agent service configuration. #>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$AgentRoot = "$env:ProgramFiles\GLPI-Agent",
    [switch]$RemoveUpstreamAgent
)

$ErrorActionPreference = 'Stop'
$serviceName = 'glpi-agent'
$configPath = Join-Path $AgentRoot 'etc\conf.d\99-assetguard.cfg'

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) { throw 'Run this uninstaller from an elevated PowerShell window.' }
if (Test-Path -LiteralPath $configPath) {
    $firstLine = Get-Content -LiteralPath $configPath -TotalCount 1 -ErrorAction Stop
    if ($firstLine -notmatch '^# Managed by AssetGuard\.') {
        throw "Refusing to remove '$configPath' because it is not an AssetGuard-managed configuration."
    }
}

if ($PSCmdlet.ShouldProcess($serviceName, 'Stop and disable GLPI Agent service')) {
    Stop-Service -Name $serviceName -Force -ErrorAction SilentlyContinue
    Set-Service -Name $serviceName -StartupType Disabled -ErrorAction SilentlyContinue
}
if (Test-Path -LiteralPath $configPath -and $PSCmdlet.ShouldProcess($configPath, 'Remove AssetGuard configuration and its stored credential')) {
    Remove-Item -LiteralPath $configPath -Force
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
