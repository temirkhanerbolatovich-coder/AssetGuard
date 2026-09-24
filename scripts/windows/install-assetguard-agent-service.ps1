<#
.SYNOPSIS
Installs or configures the upstream GLPI Agent as the AssetGuard Windows service.

.DESCRIPTION
The script installs the official GLPI Agent from WinGet when necessary, writes one
AssetGuard-owned configuration fragment with a minimal hardware-only profile, and
starts the upstream glpi-agent service. The inventory password is stored only in
the local service configuration, protected with an ACL for SYSTEM and local
Administrators. It is never written to a command line, Scheduled Task, log, or
this repository.

Run from an elevated PowerShell window. An Administrator can intentionally stop,
reconfigure, or remove the service; the script does not attempt to bypass Windows
administration controls.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [uri]$GatewayUri,

    [Parameter(Mandatory)]
    [Security.SecureString]$InventorySecret,

    [ValidatePattern('^[A-Za-z0-9-]{3,128}$')]
    [string]$AgentUsername = 'assetguard',

    [string]$AgentRoot = "$env:ProgramFiles\GLPI-Agent",
    [switch]$AllowTemporaryTunnel,
    [switch]$SkipUpstreamInstall,
    [switch]$RunInventoryNow
)

$ErrorActionPreference = 'Stop'
$serviceName = 'glpi-agent'
$managedFileName = '99-assetguard.cfg'

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-SafeConfigValue([string]$Value, [string]$Name) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -match "[\r\n]") {
        throw "$Name must be a non-empty single-line value."
    }
}

if (-not (Test-Administrator)) {
    throw 'Run this installer from an elevated PowerShell window (Run as administrator).'
}
if ($GatewayUri.Scheme -ne 'https') {
    throw 'GatewayUri must use HTTPS. A Windows service must not send inventory over plain HTTP.'
}
if ($GatewayUri.UserInfo -or $GatewayUri.Query -or $GatewayUri.Fragment -or $GatewayUri.AbsolutePath.TrimEnd('/') -ne '/glpi-agent') {
    throw 'GatewayUri must be exactly an HTTPS AssetGuard endpoint such as https://host.example/glpi-agent.'
}
if ($GatewayUri.Host -like '*.trycloudflare.com' -and -not $AllowTemporaryTunnel) {
    throw 'A trycloudflare.com address changes after a tunnel restart. Use a stable domain, or explicitly pass -AllowTemporaryTunnel for a short-lived pitch demo.'
}

$secretBstr = [IntPtr]::Zero
$plainSecret = $null
try {
    $secretBstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($InventorySecret)
    $plainSecret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretBstr)
    Assert-SafeConfigValue $plainSecret 'InventorySecret'

    $launcher = Join-Path $AgentRoot 'glpi-agent.bat'
    if (-not (Test-Path -LiteralPath $launcher)) {
        if ($SkipUpstreamInstall) {
            throw "GLPI Agent was not found at '$AgentRoot'. Install GLPI Agent 1.19 first or omit -SkipUpstreamInstall."
        }
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $winget) {
            throw 'WinGet is unavailable. Install the official GLPI Agent 1.19 x64 MSI, then re-run with -SkipUpstreamInstall.'
        }
        if ($PSCmdlet.ShouldProcess('GLPI Agent 1.19', 'Install official upstream package via WinGet')) {
            $install = Start-Process -FilePath $winget.Source -ArgumentList @(
                'install', '--id', 'GLPI-Project.GLPI-Agent', '--exact', '--silent',
                '--accept-package-agreements', '--accept-source-agreements'
            ) -Wait -PassThru
            if ($install.ExitCode -ne 0) { throw "WinGet GLPI Agent installation failed with exit code $($install.ExitCode)." }
        }
        if (-not (Test-Path -LiteralPath $launcher)) {
            throw "GLPI Agent installation did not create '$launcher'. Verify the official installer and re-run."
        }
    }

    $configDirectory = Join-Path $AgentRoot 'etc\conf.d'
    $configPath = Join-Path $configDirectory $managedFileName
    $logDirectory = Join-Path $env:ProgramData 'AssetGuard\logs'
    $excludedCategories = 'accesslog,antivirus,battery,database,environment,firewall,input,licenseinfo,local_group,local_user,lvm,modem,port,printer,process,provider,psu,registry,remote_mgmt,rudder,slot,software,sound,usb,user,virtualmachine'
    $config = @"
# Managed by AssetGuard. Remove with uninstall-assetguard-agent-service.ps1.
# Upstream GLPI Agent remains unmodified; this file is loaded after agent.cfg.
server = $($GatewayUri.AbsoluteUri)
user = $AgentUsername
password = $plainSecret
no-category = $excludedCategories
no-compression = 1
no-httpd = 1
delaytime = 60
logger = File
logfile = $logDirectory\glpi-agent.log
"@

    if ($PSCmdlet.ShouldProcess($configPath, 'Write protected AssetGuard hardware-only profile')) {
        New-Item -ItemType Directory -Force -Path $configDirectory, $logDirectory | Out-Null
        Set-Content -LiteralPath $configPath -Value $config -Encoding ascii -NoNewline
        & icacls.exe $configPath '/inheritance:r' '/grant:r' 'SYSTEM:(F)' 'BUILTIN\Administrators:(F)' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not protect '$configPath' with Windows ACLs." }
    }

    $service = Get-Service -Name $serviceName -ErrorAction Stop
    if ($PSCmdlet.ShouldProcess($serviceName, 'Enable automatic start and restart recovery')) {
        Set-Service -Name $serviceName -StartupType Automatic
        & sc.exe failure $serviceName 'reset=' '86400' 'actions=' 'restart/60000/restart/60000/restart/60000' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not configure failure recovery for '$serviceName'." }
    }

    if ($RunInventoryNow -and $PSCmdlet.ShouldProcess($serviceName, 'Request one immediate inventory from upstream GLPI Agent')) {
        # Do not let the service and the foreground process post two initial scans at once.
        if ((Get-Service -Name $serviceName).Status -eq 'Running') { Stop-Service -Name $serviceName -Force }
        & $launcher '--force' '--logger=stderr'
        if ($LASTEXITCODE -ne 0) { throw "Immediate GLPI inventory failed with exit code $LASTEXITCODE. Review $logDirectory\glpi-agent.log." }
    }
    if ($PSCmdlet.ShouldProcess($serviceName, 'Start configured upstream GLPI Agent service')) {
        $currentService = Get-Service -Name $serviceName
        if ($currentService.Status -eq 'Running') { Restart-Service -Name $serviceName -Force } else { Start-Service -Name $serviceName }
    }

    [pscustomobject]@{
        Service = $serviceName
        StartupType = 'Automatic'
        GatewayUri = $GatewayUri.AbsoluteUri
        AgentUsername = $AgentUsername
        ConfigPath = $configPath
        PrivacyProfile = 'hardware-only; users, software, processes, USB and browser-related categories disabled'
        TemporaryTunnel = $GatewayUri.Host -like '*.trycloudflare.com'
    }
}
finally {
    if ($secretBstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretBstr) }
    $plainSecret = $null
}
