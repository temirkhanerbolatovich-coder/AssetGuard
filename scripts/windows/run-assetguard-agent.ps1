<# One SYSTEM scheduled tick: collect locally even offline, then drain a bounded queue. #>
[CmdletBinding()]
param([string]$StateRoot = "$env:ProgramData\AssetGuard\Agent")

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'assetguard-agent-runtime.ps1')
$key = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey('SOFTWARE\GLPI-Agent', $false)
if (-not $key) { throw 'AssetGuard Agent configuration was not found.' }
try {
    $gateway = [uri][string]$key.GetValue('server')
    $username = [string]$key.GetValue('user')
    $plain = [string]$key.GetValue('password')
    $tag = [string]$key.GetValue('tag')
    $secure = ConvertTo-SecureString $plain -AsPlainText -Force
    $credential = [pscredential]::new($username, $secure)
}
finally { $key.Dispose(); $plain = $null }
if ($gateway.Scheme -ne 'https' -or $tag -notmatch '^assetguard-installer-\d+\.\d+\.\d+$') { throw 'Invalid AssetGuard Agent configuration.' }
$policyPath = Join-Path $StateRoot 'policy.json'
$policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
$agentRoot = [string]$policy.agent_root
$scratch = Join-Path $StateRoot 'collector'
if ((Test-Path -LiteralPath $scratch) -and ((Get-Item -LiteralPath $scratch).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Invalid collector directory.' }
New-Item -ItemType Directory -Path $scratch -Force | Out-Null

$profilePath = Join-Path $PSScriptRoot 'glpi-agent-minimal-profile.cfg'
$collector = { Get-AssetGuardLocalInventory -AgentRoot $agentRoot -Scratch $scratch -Tag $tag -ProfilePath $profilePath }
$sender = { param($Bytes) Send-AssetGuardQueuedInventory -GatewayUri $gateway -Credential $credential -Bytes $Bytes }
try {
    # Randomize every scheduler tick, including boot and network recovery.
    Start-Sleep -Seconds (Get-Random -Minimum 0 -Maximum 31)
    Invoke-AssetGuardAgentCycle -StateRoot $StateRoot -Collector $collector -Sender $sender `
        -NetworkAvailable ([Net.NetworkInformation.NetworkInterface]::GetIsNetworkAvailable()) `
        -CollectionIntervalSeconds ([int]$policy.collection_interval_seconds) `
        -CollectionJitterSeconds ([int]$policy.collection_jitter_seconds) `
        -MaxSendPerCycle ([int]$policy.max_send_per_cycle) `
        -MaxQueueBytes ([long]$policy.max_queue_bytes) -MaxQueueFiles ([int]$policy.max_queue_files)
}
finally { $credential = $null; $secure = $null }
