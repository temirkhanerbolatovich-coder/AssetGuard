<#
.SYNOPSIS
Installs GLPI collection and the AssetGuard durable Windows delivery task.

.DESCRIPTION
The script installs the official GLPI Agent from WinGet when necessary, writes an
AssetGuard-owned profile to the Windows configuration backend used by the upstream
service. A protected SYSTEM task collects locally and uploads its durable queue;
the upstream daemon is disabled to prevent concurrent uploaders. The password is
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

    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$InstallerVersion = '0.1.8',

    [ValidateRange(1, 1440)][int]$CollectionIntervalMinutes = 5,
    [ValidateRange(0, 3600)][int]$CollectionJitterSeconds = 60,
    [ValidateRange(16, 1024)][int]$MaxQueueMegabytes = 256,

    [string]$AgentRoot = "$env:ProgramFiles\GLPI-Agent",
    [switch]$AllowTemporaryTunnel,
    [switch]$SkipUpstreamInstall,
    [switch]$RunInventoryNow
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'assetguard-agent-runtime.ps1')
$serviceName = 'glpi-agent'
$registryPath = 'HKLM:\SOFTWARE\GLPI-Agent'
$registrySubKey = 'SOFTWARE\GLPI-Agent'
$registryAclBackupPath = Join-Path $env:ProgramData 'AssetGuard\glpi-agent-registry-acl.sddl'
$lifecycleLogPath = Join-Path $env:ProgramData 'AssetGuard\agent-lifecycle.jsonl'
$legacyConfigPath = Join-Path $AgentRoot 'etc\conf.d\99-assetguard.cfg'
$managedRegistryValues = @('server', 'user', 'password', 'tag', 'no-category', 'no-compression', 'no-httpd', 'delaytime')
$pinnedAgentVersion = '1.20'
$supportedAgentVersions = @('1.19', '1.20')
$deliveryTaskName = 'AssetGuard inventory delivery'
$agentStateRoot = Join-Path $env:ProgramData 'AssetGuard\Agent'

function Install-AgentDeliverySchedule {
    $existingTask = Get-ScheduledTask -TaskName $deliveryTaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Disable-ScheduledTask -TaskName $deliveryTaskName | Out-Null
        Stop-ScheduledTask -TaskName $deliveryTaskName
        $stopDeadline = (Get-Date).AddSeconds(30)
        while ((Get-ScheduledTask -TaskName $deliveryTaskName).State -eq 'Running') {
            if ((Get-Date) -ge $stopDeadline) { throw 'Existing Agent task did not stop; runtime files were not replaced.' }
            Start-Sleep -Seconds 1
        }
    }
    $runtimeDirectory = Join-Path $agentStateRoot 'runtime'
    $assetGuardDirectory = Split-Path -Parent $agentStateRoot
    foreach ($path in @($assetGuardDirectory, $agentStateRoot, $runtimeDirectory)) {
        if ((Test-Path -LiteralPath $path) -and ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Agent runtime cannot use reparse points.' }
        New-Item -ItemType Directory -Force -Path $path | Out-Null
    }
    # Protect scripts as well as data: the scheduled task runs them as SYSTEM.
    $paths = @((Get-Item -LiteralPath $assetGuardDirectory), (Get-Item -LiteralPath $agentStateRoot)) + @(Get-ChildItem -LiteralPath $agentStateRoot -Recurse -Force)
    foreach ($entry in $paths) {
        if ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Agent runtime cannot use reparse points.' }
        $acl = Get-Acl -LiteralPath $entry.FullName
        $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
        $acl.SetAccessRuleProtection($true, $false)
        foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRuleSpecific($rule) }
        foreach ($sidValue in @('S-1-5-18', 'S-1-5-32-544')) {
            $sid = [Security.Principal.SecurityIdentifier]::new($sidValue)
            $rule = if ($entry.PSIsContainer) {
                [Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'ContainerInherit, ObjectInherit', 'None', 'Allow')
            } else { [Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'Allow') }
            $acl.AddAccessRule($rule)
        }
        Set-Acl -LiteralPath $entry.FullName -AclObject $acl
    }
    foreach ($name in @('run-assetguard-agent.ps1', 'assetguard-agent-runtime.ps1', 'glpi-agent-minimal-profile.cfg')) {
        Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $runtimeDirectory $name) -Force
    }
    . (Join-Path $runtimeDirectory 'assetguard-agent-runtime.ps1')
    Write-AgentJson (Join-Path $agentStateRoot 'policy.json') @{
        agent_root = $AgentRoot; collection_interval_seconds = $CollectionIntervalMinutes * 60
        collection_jitter_seconds = $CollectionJitterSeconds; max_send_per_cycle = 3
        max_queue_bytes = $MaxQueueMegabytes * 1MB; max_queue_files = 10000
    }
    foreach ($entry in @((Get-Item -LiteralPath (Join-Path $agentStateRoot 'policy.json'))) + @(Get-ChildItem -LiteralPath $runtimeDirectory -File)) {
        $acl = Get-Acl -LiteralPath $entry.FullName
        $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
        Set-Acl -LiteralPath $entry.FullName -AclObject $acl
    }
    $powershell = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $runner = Join-Path $runtimeDirectory 'run-assetguard-agent.ps1'
    $action = New-ScheduledTaskAction -Execute $powershell -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$runner`""
    $boot = New-ScheduledTaskTrigger -AtStartup
    $repeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)
    $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    $settings.Enabled = $false
    Register-ScheduledTask -TaskName $deliveryTaskName -Action $action -Trigger @($boot, $repeat) -Principal $principal -Settings $settings -Description 'AssetGuard durable hardware inventory: collect offline, randomized delivery and retry.' -Force | Out-Null
}

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

function Get-GlpiAgentVersion([string]$Launcher) {
    $versionOutput = @(& $Launcher '--version' 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read the installed GLPI Agent version from '$Launcher'."
    }
    $versionText = $versionOutput -join [Environment]::NewLine
    $versionMatch = [regex]::Match($versionText, 'GLPI Agent \((?<version>\d+\.\d+(?:\.\d+)?)\)')
    if (-not $versionMatch.Success) {
        throw "The installed GLPI Agent returned an unrecognized version string. Supported versions: $($supportedAgentVersions -join ', ')."
    }
    return $versionMatch.Groups['version'].Value
}

function Write-AgentLifecycleEvent([string]$Status, [string]$AgentVersion, [string]$Message) {
    $directory = Split-Path -Parent $lifecycleLogPath
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $event = [ordered]@{
        occurred_at = [DateTimeOffset]::UtcNow.ToString('O')
        operation = 'INSTALL_OR_RECONFIGURE'
        status = $Status
        installer_version = $InstallerVersion
        agent_version = $AgentVersion
        gateway_host = $GatewayUri.Host
        message = $Message
    }
    Add-Content -LiteralPath $lifecycleLogPath -Value ($event | ConvertTo-Json -Compress) -Encoding utf8
    & icacls.exe $lifecycleLogPath '/inheritance:r' '/grant:r' '*S-1-5-18:(F)' '*S-1-5-32-544:(F)' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Could not protect '$lifecycleLogPath' with Windows ACLs." }
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
        $acl.SetOwner([Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))
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
if ($AgentRoot -cmatch '["\r\n\x80-\uFFFF]' -or $agentStateRoot -cmatch '["\r\n\x80-\uFFFF]') {
    throw 'GLPI Agent and ProgramData paths must use ASCII and contain no quotes.'
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
            throw "GLPI Agent was not found at '$AgentRoot'. Install GLPI Agent $pinnedAgentVersion first or omit -SkipUpstreamInstall."
        }
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if (-not $winget) {
            throw "WinGet is unavailable. Install the official GLPI Agent $pinnedAgentVersion x64 MSI, then re-run with -SkipUpstreamInstall."
        }
        if ($PSCmdlet.ShouldProcess("GLPI Agent $pinnedAgentVersion", 'Install version-locked official upstream package via WinGet')) {
            $install = Start-Process -FilePath $winget.Source -ArgumentList @(
                'install', '--id', 'GLPI-Project.GLPI-Agent', '--exact',
                '--version', $pinnedAgentVersion, '--source', 'winget', '--silent',
                '--accept-package-agreements', '--accept-source-agreements', '--disable-interactivity'
            ) -WindowStyle Hidden -Wait -PassThru
            if ($install.ExitCode -ne 0) { throw "WinGet GLPI Agent installation failed with exit code $($install.ExitCode)." }
        }
        if (-not (Test-Path -LiteralPath $launcher)) {
            throw "GLPI Agent installation did not create '$launcher'. Verify the official installer and re-run."
        }
    }

    $installedAgentVersion = Get-GlpiAgentVersion $launcher
    if ($installedAgentVersion -notin $supportedAgentVersions) {
        throw "GLPI Agent $installedAgentVersion is not supported by this AssetGuard installer. Supported versions: $($supportedAgentVersions -join ', ')."
    }

    $excludedCategories = 'accesslog,antivirus,battery,database,environment,firewall,input,licenseinfo,local_group,local_user,lvm,modem,port,printer,process,provider,psu,registry,remote_mgmt,rudder,slot,software,sound,usb,user,virtualmachine'
    $configValues = @{
        'server' = $GatewayUri.AbsoluteUri
        'user' = $AgentUsername
        'password' = $plainSecret
        'tag' = "assetguard-installer-$InstallerVersion"
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
    if ($PSCmdlet.ShouldProcess($deliveryTaskName, 'Install durable collection and delivery task')) {
        Install-AgentDeliverySchedule
        # There must be only one uploader; the collector still uses upstream GLPI.
        if ((Get-Service -Name $serviceName).Status -eq 'Running') { Stop-Service -Name $serviceName -Force }
        Set-Service -Name $serviceName -StartupType Disabled
        Enable-ScheduledTask -TaskName $deliveryTaskName | Out-Null
    }
    if ($RunInventoryNow -and $PSCmdlet.ShouldProcess($deliveryTaskName, 'Start first durable inventory tick')) {
        Start-ScheduledTask -TaskName $deliveryTaskName
    }

    Write-AgentLifecycleEvent 'SUCCEEDED' $installedAgentVersion 'Agent installed or reconfigured successfully.'

    [pscustomobject]@{
        Service = $serviceName
        AgentVersion = $installedAgentVersion
        StartupType = 'SYSTEM scheduled task at boot and every minute'
        DeliveryTask = $deliveryTaskName
        CollectionIntervalSeconds = $CollectionIntervalMinutes * 60
        CollectionJitterSeconds = $CollectionJitterSeconds
        QueueDirectory = Join-Path $agentStateRoot 'pending'
        GatewayUri = $GatewayUri.AbsoluteUri
        AgentUsername = $AgentUsername
        ConfigPath = $registryPath
        PrivacyProfile = 'hardware-only; users, software, processes, USB and browser-related categories disabled'
        TemporaryTunnel = $GatewayUri.Host -like '*.trycloudflare.com'
    }
}
catch {
    try { Write-AgentLifecycleEvent 'FAILED' $installedAgentVersion 'Agent installation or reconfiguration failed. Review the protected installer diagnostic.' }
    catch { }
    throw
}
finally {
    if ($secretBstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretBstr) }
    $plainSecret = $null
}
