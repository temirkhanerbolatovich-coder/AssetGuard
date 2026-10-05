param([string]$Root, [string]$Runtime, [string]$Scenario, [string]$GatewayUri = '')
$ErrorActionPreference = 'Stop'
. $Runtime
function Assert-Contract($Passed, [string]$Message) { if (-not $Passed) { throw $Message } }
function Pending { return @(Get-ChildItem -LiteralPath (Join-Path $Root 'pending') -Filter '*.json') }
$script:captures = 0
$script:sent = [Collections.Generic.List[string]]::new()
$collector = {
    $script:captures++
    return ,[Text.Encoding]::UTF8.GetBytes("<REQUEST><DEVICEID>queue-fixture</DEVICEID><QUERY>INVENTORY</QUERY><CONTENT><HARDWARE><UUID>QUEUE-UUID</UUID></HARDWARE></CONTENT><CAPTURE>$script:captures</CAPTURE></REQUEST>")
}
$sender = { param($Bytes) $script:sent.Add([Text.Encoding]::UTF8.GetString($Bytes)); return @{ Status = 'ACCEPTED'; RetryAfterSeconds = 0 } }
$parameters = @{ StateRoot = $Root; Collector = $collector; Sender = $sender; Random = { param($Min, $Max) $Min }; Pause = {} }
$now = [DateTimeOffset]::Parse('2026-10-05T00:00:00Z')
switch ($Scenario) {
    'offline_fifo' {
        foreach ($seconds in @(0, 360, 720)) {
            $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds($seconds) -NetworkAvailable $false
            Assert-Contract ($result.Collected -eq 1 -and $result.Delivered -eq 0) 'Offline capture must continue.'
        }
        Assert-Contract ((Pending).Count -eq 3) 'Offline evidence must survive on disk.'
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(721)
        Assert-Contract ($result.Delivered -eq 3 -and (Pending).Count -eq 0) 'Restored network must drain the queue.'
        for ($index = 0; $index -lt 3; $index++) { Assert-Contract ($script:sent[$index].Contains('<CAPTURE>' + ($index + 1) + '</CAPTURE>')) 'Delivery must retain capture order.' }
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(1081)
        Assert-Contract ($result.Collected -eq 1 -and $result.Delivered -eq 1) 'Later ticks must continue after initial delivery.'
    }
    'batch_limit' {
        foreach ($seconds in @(0, 360, 720, 1080, 1440)) {
            $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds($seconds) -NetworkAvailable $false
        }
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(1441)
        Assert-Contract ($result.Delivered -eq 3 -and (Pending).Count -eq 2) 'Reconnect must send only the bounded batch.'
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(1501)
        Assert-Contract ($result.Delivered -eq 2 -and (Pending).Count -eq 0) 'Later ticks must resume the remaining backlog.'
    }
    'lost_ack' {
        $parameters.Sender = {
            param($Bytes)
            $script:sent.Add([Convert]::ToBase64String($Bytes))
            return @{ Status = $(if ($script:sent.Count -eq 1) { 'TRANSIENT' } else { 'ACCEPTED' }); RetryAfterSeconds = 0 }
        }
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now
        Assert-Contract ((Pending).Count -eq 1) 'A lost acknowledgement must retain the report.'
        $id = (Get-Content (Pending)[0].FullName -Raw | ConvertFrom-Json).id
        . $Runtime # Simulate a fresh worker process, with state read from disk.
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(31)
        Assert-Contract ($result.Delivered -eq 1 -and (Pending).Count -eq 0) 'Retry acknowledgement must release the queue item.'
        Assert-Contract ($script:sent.Count -eq 2 -and $script:sent[0] -ceq $script:sent[1]) 'Retry must use identical bytes for server deduplication.'
        Assert-Contract ((Get-Content (Join-Path $Root 'runtime.jsonl') -Raw).Contains($id)) 'Logs must identify the delivered report.'
    }
    'jitter_retry' {
        $parameters.Random = { param($Min, $Max) $Max }
        $parameters.Sender = { param($Bytes) $script:sent.Add('attempt'); return @{ Status = 'TRANSIENT'; RetryAfterSeconds = 120 } }
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now
        Assert-Contract ($script:sent.Count -eq 0) 'Initial upload jitter must defer delivery.'
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(60)
        $state = Get-Content (Join-Path $Root 'state.json') -Raw | ConvertFrom-Json
        Assert-Contract ($state.next_collect_unix -eq $now.AddSeconds(360).ToUnixTimeSeconds()) 'Collection must include bounded jitter.'
        Assert-Contract ($state.next_upload_unix -ge $now.AddSeconds(180).ToUnixTimeSeconds()) 'Retry-After must not be ignored.'
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(61)
        Assert-Contract ($script:sent.Count -eq 1) 'Early ticks must respect retry backoff.'
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(181)
        Assert-Contract ($script:sent.Count -eq 2) 'Due retry must resume.'
    }
    'queue_recovery_lock' {
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now -NetworkAvailable $false
        $file = (Pending)[0]
        Move-Item -LiteralPath $file.FullName -Destination ($file.FullName + '.tmp')
        Set-Content -LiteralPath (Join-Path $Root 'state.json') -Value 'interrupted'
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(1) -MaxSendPerCycle 1
        Assert-Contract ($result.Delivered -eq 1 -and $script:sent[0].Contains('<CAPTURE>1</CAPTURE>')) 'Interrupted writes must recover before later captures.'
        $held = [IO.File]::Open((Join-Path $Root 'cycle.lock'), 'Open', 'ReadWrite', 'None')
        try { $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(700) }
        finally { $held.Dispose() }
        Assert-Contract ($result.Status -eq 'BUSY' -and $script:captures -eq 2) 'Concurrent ticks must not collect or upload twice.'
    }
    'quota_corruption' {
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now -NetworkAvailable $false -MaxQueueFiles 1
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(360) -NetworkAvailable $false -MaxQueueFiles 1
        Assert-Contract ($script:captures -eq 1 -and (Pending).Count -eq 1) 'A full queue must preserve earlier evidence.'
        $file = (Pending)[0]
        $report = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
        $report.sha256 = 'corrupted'
        Write-AgentJson $file.FullName $report
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(361) -MaxQueueFiles 1
        Assert-Contract ((Pending).Count -eq 0 -and @(Get-ChildItem (Join-Path $Root 'rejected')).Count -eq 1) 'Corrupt evidence must be preserved separately.'
        Assert-Contract ($script:sent.Count -eq 0) 'Corrupt evidence must not reach the server.'
    }
    'auth_rejected' {
        $parameters.Sender = { param($Bytes) return @{ Status = 'AUTH_REJECTED'; RetryAfterSeconds = 300 } }
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now
        Assert-Contract ((Pending).Count -eq 1 -and $result.Delivered -eq 0) 'Revocation must retain unsent evidence.'
        Assert-Contract ((Get-Content (Join-Path $Root 'runtime.jsonl') -Raw).Contains('AUTH_REJECTED')) 'Credential failure must be visible.'
    }
    'http_ack' {
        $credential = [pscredential]::new('ag-contract', (ConvertTo-SecureString 'queue-contract-secret' -AsPlainText -Force))
        $parameters.Sender = { param($Bytes) Send-AssetGuardQueuedInventory -GatewayUri ([uri]$GatewayUri) -Credential $credential -Bytes $Bytes }
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now -NetworkAvailable $false
        foreach ($seconds in @(61, 400, 1000, 2000, 4000)) {
            $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds($seconds) -MaxSendPerCycle 1
            Assert-Contract ($result.Delivered -eq 0 -and (Pending).Count -ge 1) 'HTML, redirect, auth, rate limit or oversized response must not acknowledge a report.'
        }
        $result = Invoke-AssetGuardAgentCycle @parameters -Now $now.AddSeconds(6000) -MaxSendPerCycle 1
        Assert-Contract ($result.Delivered -eq 1) 'Only a valid XML acknowledgement should accept the oldest report.'
        $log = Get-Content (Join-Path $Root 'runtime.jsonl') -Raw
        Assert-Contract (-not $log.Contains('queue-contract-secret') -and -not $log.Contains('<REQUEST>')) 'Logs must not contain credentials or payload.'
    }
    default { throw 'Unknown contract scenario.' }
}
@{ scenario = $Scenario; captures = $script:captures; passed = $true } | ConvertTo-Json -Compress
