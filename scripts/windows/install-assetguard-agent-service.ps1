<#
.SYNOPSIS
Installs or configures the upstream GLPI Agent as the AssetGuard Windows service.

.DESCRIPTION
The script installs the official GLPI Agent from WinGet when necessary, writes an
AssetGuard-owned profile to the Windows configuration backend used by the upstream
service, and starts the upstream glpi-agent service. The inventory password is
stored only in that local configuration, protected with an ACL for SYSTEM and
local Administrators. It is never written to a command line, Scheduled Task, log,
or this repository.

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
$registryPath = 'HKLM:\SOFTWARE\GLPI-Agent'
$registrySubKey = 'SOFTWARE\GLPI-Agent'
$registryAclBackupPath = Join-Path $env:ProgramData 'AssetGuard\glpi-agent-registry-acl.sddl'
$legacyConfigPath = Join-Path $AgentRoot 'etc\conf.d\99-assetguard.cfg'
$managedRegistryValues = @('server', 'user', 'password', 'no-category', 'no-compression', 'no-httpd', 'delaytime')

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

function Open-AgentRegistryKey {
    $key = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey($registrySubKey, $true)
    if ($null -eq $key) { throw "The GLPI Agent registry key '$registrySubKey' was not found." }
    return $key
}

function Protect-AgentRegistryConfiguration {
    if (-not (Test-Path -LiteralPath $registryAclBackupPath)) {
        $originalKey = Open-AgentRegistryKey
        try { $originalSddl = $originalKey.GetAccessControl().Sddl }
        finally { $originalKey.Dispose() }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $registryAclBackupPath) | Out-Null
        Set-Content -LiteralPath $registryAclBackupPath -Value $originalSddl -Encoding ascii -NoNewline
        & icacls.exe $registryAclBackupPath '/inheritance:r' '/grant:r' '*S-1-5-18:(F)' '*S-1-5-32-544:(F)' | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not protect '$registryAclBackupPath' with Windows ACLs." }
    }

    $protectedKey = Open-AgentRegistryKey
    try {
        $acl = $protectedKey.GetAccessControl()
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRuleSpecific($rule) }
        foreach ($sidValue in @('S-1-5-18', 'S-1-5-32-544')) {
            $sid = [Security.Principal.SecurityIdentifier]::new($sidValue)
            $rule = [Security.AccessControl.RegistryAccessRule]::new(
                $sid,
                [Security.AccessControl.RegistryRights]::FullControl,
                [Security.AccessControl.InheritanceFlags]::None,
                [Security.AccessControl.PropagationFlags]::None,
                [Security.AccessControl.AccessControlType]::Allow
            )
            $acl.AddAccessRule($rule)
        }
        $protectedKey.SetAccessControl($acl)
    }
    finally { $protectedKey.Dispose() }
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

    $upstreamLogPath = Join-Path $AgentRoot 'logs\glpi-agent.log'
    $excludedCategories = 'accesslog,antivirus,battery,database,environment,firewall,input,licenseinfo,local_group,local_user,lvm,modem,port,printer,process,provider,psu,registry,remote_mgmt,rudder,slot,software,sound,usb,user,virtualmachine'
    $configValues = @{
        'server' = $GatewayUri.AbsoluteUri
        'user' = $AgentUsername
        'password' = $plainSecret
        'no-category' = $excludedCategories
        'no-compression' = '1'
        'no-httpd' = '1'
        'delaytime' = '60'
    }

    if ($PSCmdlet.ShouldProcess($registryPath, 'Write protected AssetGuard hardware-only profile')) {
        Protect-AgentRegistryConfiguration
        $configuredKey = Open-AgentRegistryKey
        try {
            foreach ($name in $managedRegistryValues) {
                $configuredKey.SetValue($name, [string]$configValues[$name], [Microsoft.Win32.RegistryValueKind]::String)
            }
        }
        finally { $configuredKey.Dispose() }
        if (Test-Path -LiteralPath $legacyConfigPath) {
            $firstLine = Get-Content -LiteralPath $legacyConfigPath -TotalCount 1 -ErrorAction Stop
            if ($firstLine -match '^# Managed by AssetGuard\.') { Remove-Item -LiteralPath $legacyConfigPath -Force }
        }
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
        if ($LASTEXITCODE -ne 0) { throw "Immediate GLPI inventory failed with exit code $LASTEXITCODE. Review $upstreamLogPath." }
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
        ConfigPath = $registryPath
        PrivacyProfile = 'hardware-only; users, software, processes, USB and browser-related categories disabled'
        TemporaryTunnel = $GatewayUri.Host -like '*.trycloudflare.com'
    }
}
finally {
    if ($secretBstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretBstr) }
    $plainSecret = $null
}
