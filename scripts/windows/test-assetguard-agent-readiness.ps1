<#
.SYNOPSIS
Captures a secret-free readiness report for one AssetGuard pilot computer.

.DESCRIPTION
Run after each fleet-test phase. The script reads service, version and protected
configuration metadata without changing the Agent configuration or triggering an
inventory. It never reads or exports the inventory password value.
#>
[CmdletBinding()]
param(
    [ValidateSet('INITIAL', 'AFTER_REBOOT', 'OFFLINE', 'NETWORK_RESTORED', 'SERVICE_RECOVERED', 'HARDWARE_CHANGED', 'REENROLLED')]
    [string]$Phase = 'INITIAL',
    [string]$ExpectedAgentVersion = '1.20',
    [string]$ExpectedInstallerVersion = '0.1.7',
    [string]$OutputPath = ''
)

$ErrorActionPreference = 'Stop'
$serviceName = 'glpi-agent'
$agentRoot = Join-Path $env:ProgramFiles 'GLPI-Agent'
$launcher = Join-Path $agentRoot 'glpi-agent.bat'
$lifecycleLogPath = Join-Path $env:ProgramData 'AssetGuard\agent-lifecycle.jsonl'

function Get-AgentVersion {
    if (-not (Test-Path -LiteralPath $launcher)) { return $null }
    $output = @(& $launcher '--version' 2>&1)
    if ($LASTEXITCODE -ne 0) { return $null }
    $match = [regex]::Match(($output -join [Environment]::NewLine), 'GLPI Agent \((?<version>\d+\.\d+(?:\.\d+)?)\)')
    if ($match.Success) { return $match.Groups['version'].Value }
    return $null
}

function Add-Check([System.Collections.Generic.List[object]]$Checks, [string]$Name, [bool]$Passed, [string]$Actual) {
    $Checks.Add([pscustomobject]@{ name = $Name; passed = $Passed; actual = $Actual })
}

$service = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction SilentlyContinue
$config = $null
$passwordConfigured = $false
$registryKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SOFTWARE\GLPI-Agent', $false)
if ($registryKey) {
    try {
        $config = [pscustomobject]@{
            server = $registryKey.GetValue('server', $null)
            user = $registryKey.GetValue('user', $null)
            tag = $registryKey.GetValue('tag', $null)
            no_compression = $registryKey.GetValue('no-compression', $null)
        }
        $passwordConfigured = $registryKey.GetValueNames() -contains 'password'
    }
    finally { $registryKey.Dispose() }
}
$agentVersion = Get-AgentVersion
$installerTag = if ($config) { [string]$config.tag } else { '' }
$installerVersion = if ($installerTag -match '^assetguard-installer-(?<version>\d+\.\d+\.\d+)$') { $Matches.version } else { $null }
$gateway = if ($config -and $config.server) { [uri][string]$config.server } else { $null }
$checks = [System.Collections.Generic.List[object]]::new()

Add-Check $checks 'service_exists' ($null -ne $service) $(if ($service) { $service.Name } else { 'missing' })
Add-Check $checks 'service_running' ($service.State -eq 'Running') $(if ($service) { $service.State } else { 'missing' })
Add-Check $checks 'service_automatic' ($service.StartMode -eq 'Auto') $(if ($service) { $service.StartMode } else { 'missing' })
Add-Check $checks 'agent_version' ($agentVersion -eq $ExpectedAgentVersion) $(if ($agentVersion) { $agentVersion } else { 'unknown' })
Add-Check $checks 'installer_version' ($installerVersion -eq $ExpectedInstallerVersion) $(if ($installerVersion) { $installerVersion } else { 'unknown' })
Add-Check $checks 'https_gateway' ($gateway -and $gateway.Scheme -eq 'https' -and $gateway.AbsolutePath.TrimEnd('/') -eq '/glpi-agent') $(if ($gateway) { $gateway.GetLeftPart([System.UriPartial]::Authority) + $gateway.AbsolutePath } else { 'missing' })
Add-Check $checks 'unique_agent_login_present' (-not [string]::IsNullOrWhiteSpace([string]$config.user) -and [string]$config.user -ne 'assetguard') $(if ($config) { [string]$config.user } else { 'missing' })
Add-Check $checks 'password_configured' $passwordConfigured $(if ($passwordConfigured) { 'present (value not read)' } else { 'missing' })
Add-Check $checks 'uncompressed_transport' ([string]$config.no_compression -eq '1') $(if ($config) { [string]$config.no_compression } else { 'missing' })

$lastLifecycleEvent = $null
if (Test-Path -LiteralPath $lifecycleLogPath) {
    $lastLine = Get-Content -LiteralPath $lifecycleLogPath -Tail 1
    if ($lastLine) { $lastLifecycleEvent = $lastLine | ConvertFrom-Json }
}
Add-Check $checks 'lifecycle_log' ($lastLifecycleEvent -and $lastLifecycleEvent.status -eq 'SUCCEEDED') $(if ($lastLifecycleEvent) { "$($lastLifecycleEvent.status) at $($lastLifecycleEvent.occurred_at)" } else { 'missing' })

$os = Get-CimInstance Win32_OperatingSystem
$report = [ordered]@{
    schema_version = 'assetguard-fleet-readiness-v1'
    captured_at = [DateTimeOffset]::UtcNow.ToString('O')
    phase = $Phase
    computer_name = $env:COMPUTERNAME
    windows_last_boot = $os.LastBootUpTime
    agent_username = if ($config) { [string]$config.user } else { $null }
    gateway_host = if ($gateway) { $gateway.Host } else { $null }
    agent_version = $agentVersion
    installer_version = $installerVersion
    lifecycle_event = $lastLifecycleEvent
    checks = $checks
    passed = -not ($checks | Where-Object { -not $_.passed })
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $directory = Join-Path $env:ProgramData 'AssetGuard\fleet-reports'
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $OutputPath = Join-Path $directory "$($env:COMPUTERNAME)-$Phase-$stamp.json"
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding utf8
& icacls.exe $OutputPath '/inheritance:r' '/grant:r' '*S-1-5-18:(F)' '*S-1-5-32-544:(F)' | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Could not protect fleet report '$OutputPath'." }

[pscustomobject]@{ Passed = $report.passed; Phase = $Phase; Report = $OutputPath; Checks = $checks.Count }
if (-not $report.passed) { exit 1 }
