<# Durable inventory queue. Windows integration is in run-assetguard-agent.ps1. #>
if ($PSVersionTable.PSVersion.Major -le 5) {
    # A parent PowerShell 7 process can supply incompatible built-in module paths.
    $env:PSModulePath = (Join-Path $PSHOME 'Modules') + ';' + [Environment]::GetEnvironmentVariable('PSModulePath', 'Machine')
}
function Write-AgentJson([string]$Path, $Value) {
    $utf8 = [Text.UTF8Encoding]::new($false)
    $bytes = $utf8.GetBytes(($Value | ConvertTo-Json -Depth 8 -Compress))
    $stream = [IO.File]::Open("$Path.tmp", 'Create', 'Write', 'None')
    try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) }
    finally { $stream.Dispose() }
    Move-Item -LiteralPath "$Path.tmp" -Destination $Path -Force
}

function Write-AgentEvent([string]$Root, [string]$Code, [string]$ReportId = '') {
    $path = Join-Path $Root 'runtime.jsonl'
    if ((Test-Path -LiteralPath $path) -and (Get-Item -LiteralPath $path).Length -gt 5MB) {
        Move-Item -LiteralPath $path -Destination "$path.1" -Force
    }
    $event = @{ occurred_at = [DateTimeOffset]::UtcNow.ToString('O'); code = $Code; report_id = $ReportId }
    [IO.File]::AppendAllText($path, ($event | ConvertTo-Json -Compress) + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
}

function Get-AgentReportBytes($Report, [long]$MaxBytes) {
    if ($Report.schema_version -ne 1) { throw 'Unsupported queue envelope.' }
    $parsedId = [guid]::Empty
    if (-not [guid]::TryParse([string]$Report.id, [ref]$parsedId)) { throw 'Invalid report identifier.' }
    $bytes = [Convert]::FromBase64String([string]$Report.xml_base64)
    if ($bytes.Length -eq 0 -or $bytes.Length -gt $MaxBytes) { throw 'Invalid inventory size.' }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $digest = ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
    if ($digest -ne $Report.sha256) { throw 'Inventory integrity check failed.' }
    return ,$bytes
}

function Invoke-AssetGuardAgentCycle {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$StateRoot,
        [Parameter(Mandatory)][scriptblock]$Collector,
        [Parameter(Mandatory)][scriptblock]$Sender,
        [DateTimeOffset]$Now = [DateTimeOffset]::UtcNow,
        [bool]$NetworkAvailable = $true,
        [ValidateRange(60, 86400)][int]$CollectionIntervalSeconds = 300,
        [ValidateRange(0, 3600)][int]$CollectionJitterSeconds = 60,
        [ValidateRange(1, 10)][int]$MaxSendPerCycle = 3,
        [ValidateRange(1, 100000)][int]$MaxQueueFiles = 10000,
        [ValidateRange(4096, 1073741824)][long]$MaxQueueBytes = 256MB,
        [ValidateRange(1024, 2097152)][long]$MaxInventoryBytes = 2MB,
        [scriptblock]$Random = { param($Minimum, $Maximum) Get-Random -Minimum $Minimum -Maximum ($Maximum + 1) },
        [scriptblock]$Pause = { param($Seconds) Start-Sleep -Seconds $Seconds }
    )
    $ErrorActionPreference = 'Stop'
    foreach ($path in @($StateRoot, (Join-Path $StateRoot 'pending'), (Join-Path $StateRoot 'rejected'))) {
        if ((Test-Path -LiteralPath $path) -and ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'Agent state must not use reparse points.'
        }
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
    $pending = Join-Path $StateRoot 'pending'
    $rejected = Join-Path $StateRoot 'rejected'
    $lock = $null
    try { $lock = [IO.File]::Open((Join-Path $StateRoot 'cycle.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
    catch [IO.IOException] { return [pscustomobject]@{ Status = 'BUSY'; Collected = 0; Delivered = 0 } }
    try {
        $statePath = Join-Path $StateRoot 'state.json'
        $state = @{ schema_version = 1; next_collect_unix = $Now.ToUnixTimeSeconds(); next_upload_unix = $Now.AddSeconds((& $Random 0 60)).ToUnixTimeSeconds(); failures = 0; network_available = $true }
        if (Test-Path -LiteralPath $statePath) {
            try {
                $saved = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
                if ($saved.schema_version -ne 1 -or $null -eq $saved.next_collect_unix -or $null -eq $saved.next_upload_unix) { throw 'Invalid runtime state.' }
                [void][long]$saved.next_collect_unix
                [void][long]$saved.next_upload_unix
                foreach ($name in @('next_collect_unix', 'next_upload_unix', 'failures', 'network_available')) { $state[$name] = $saved.$name }
            }
            catch { Write-AgentEvent $StateRoot 'STATE_RECOVERED' }
        }
        # A crash after writing the complete envelope must not lose that capture.
        foreach ($file in Get-ChildItem -LiteralPath $pending -Filter '*.json.tmp' -File) {
            try {
                $report = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
                [void](Get-AgentReportBytes $report $MaxInventoryBytes)
                Move-Item -LiteralPath $file.FullName -Destination $file.FullName.Substring(0, $file.FullName.Length - 4)
                Write-AgentEvent $StateRoot 'QUEUE_RECOVERED' $report.id
            }
            catch {
                Move-Item -LiteralPath $file.FullName -Destination (Join-Path $rejected $file.Name)
                Write-AgentEvent $StateRoot 'QUEUE_CORRUPT'
            }
        }
        $queue = @(Get-ChildItem -LiteralPath $pending -Filter '*.json' -File | Sort-Object Name)
        $held = @($queue) + @(Get-ChildItem -LiteralPath $rejected -File)
        $heldBytes = [long](($held | Measure-Object Length -Sum).Sum)
        $collected = 0
        $delivered = 0
        if ($Now.ToUnixTimeSeconds() -ge [long]$state.next_collect_unix) {
            # Reserve enough space for the largest allowed base64 envelope. Keep old evidence.
            if ($held.Count -ge $MaxQueueFiles -or $heldBytes + [math]::Ceiling($MaxInventoryBytes * 4 / 3) + 4096 -gt $MaxQueueBytes) {
                Write-AgentEvent $StateRoot 'QUEUE_FULL'
                $state.next_collect_unix = $Now.AddSeconds(60).ToUnixTimeSeconds()
            }
            else {
                try {
                    [byte[]]$bytes = & $Collector
                    if ($bytes.Length -eq 0 -or $bytes.Length -gt $MaxInventoryBytes) { throw 'Invalid collected size.' }
                    $sequence = 1L
                    foreach ($file in $held) {
                        if ($file.Name -match '^(\d{16})-') { $sequence = [math]::Max($sequence, [long]$Matches[1] + 1) }
                    }
                    $id = [guid]::NewGuid().ToString()
                    $sha = [Security.Cryptography.SHA256]::Create()
                    try { $digest = ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
                    finally { $sha.Dispose() }
                    $report = @{ schema_version = 1; id = $id; captured_at = $Now.ToString('O'); sha256 = $digest; xml_base64 = [Convert]::ToBase64String($bytes) }
                    Write-AgentJson (Join-Path $pending ('{0:D16}-{1}.json' -f $sequence, $id)) $report
                    $collected = 1
                    $state.next_collect_unix = $Now.AddSeconds($CollectionIntervalSeconds + (& $Random 0 $CollectionJitterSeconds)).ToUnixTimeSeconds()
                    Write-AgentEvent $StateRoot 'COLLECTED' $id
                }
                catch {
                    Write-AgentEvent $StateRoot 'COLLECTION_FAILED'
                    $state.next_collect_unix = $Now.AddSeconds(60 + (& $Random 0 60)).ToUnixTimeSeconds()
                }
            }
            Write-AgentJson $statePath $state
        }
        if ($NetworkAvailable -and -not $state.network_available) {
            $state.next_upload_unix = $Now.AddSeconds((& $Random 0 60)).ToUnixTimeSeconds()
            $state.failures = 0
            Write-AgentEvent $StateRoot 'NETWORK_RESTORED'
        }
        if (-not $NetworkAvailable -and $state.network_available) { Write-AgentEvent $StateRoot 'NETWORK_UNAVAILABLE' }
        $state.network_available = $NetworkAvailable
        if ($NetworkAvailable -and $Now.ToUnixTimeSeconds() -ge [long]$state.next_upload_unix) {
            $queue = @(Get-ChildItem -LiteralPath $pending -Filter '*.json' -File | Sort-Object Name | Select-Object -First $MaxSendPerCycle)
            foreach ($file in $queue) {
                try {
                    if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Invalid queue entry.' }
                    $report = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
                    [byte[]]$bytes = Get-AgentReportBytes $report $MaxInventoryBytes
                }
                catch {
                    Move-Item -LiteralPath $file.FullName -Destination (Join-Path $rejected $file.Name)
                    Write-AgentEvent $StateRoot 'QUEUE_CORRUPT'
                    continue
                }
                try { $result = & $Sender $bytes }
                catch { $result = @{ Status = 'TRANSIENT'; RetryAfterSeconds = 0 } }
                if ($result.Status -eq 'ACCEPTED') {
                    # Deletion is the acknowledgement. A crash before it replays identical bytes.
                    Remove-Item -LiteralPath $file.FullName
                    $delivered++
                    $state.failures = 0
                    $state.next_upload_unix = $Now.AddSeconds(30).ToUnixTimeSeconds()
                    Write-AgentEvent $StateRoot 'DELIVERED' $report.id
                    if ($delivered -lt $queue.Count) { & $Pause (& $Random 5 15) }
                }
                elseif ($result.Status -eq 'PERMANENT') {
                    Move-Item -LiteralPath $file.FullName -Destination (Join-Path $rejected $file.Name)
                    Write-AgentEvent $StateRoot 'SERVER_REJECTED' $report.id
                }
                else {
                    $state.failures = [math]::Min(10, [int]$state.failures + 1)
                    $cap = [int][math]::Min(300, 60 * [math]::Pow(2, [math]::Min(3, $state.failures - 1)))
                    $delay = & $Random ([int]($cap / 2)) $cap
                    $retryAfter = [math]::Min(3600, [math]::Max(0, [int]$result.RetryAfterSeconds))
                    $state.next_upload_unix = $Now.AddSeconds([math]::Max($delay, $retryAfter)).ToUnixTimeSeconds()
                    Write-AgentEvent $StateRoot $(if ($result.Status -eq 'AUTH_REJECTED') { 'AUTH_REJECTED' } else { 'DELIVERY_RETRY' }) $report.id
                    break
                }
                Write-AgentJson $statePath $state
            }
        }
        Write-AgentJson $statePath $state
        return [pscustomobject]@{ Status = 'COMPLETED'; Collected = $collected; Delivered = $delivered; Pending = @(Get-ChildItem -LiteralPath $pending -Filter '*.json' -File).Count }
    }
    finally { $lock.Dispose() }
}

function Send-AssetGuardQueuedInventory {
    param([uri]$GatewayUri, [pscredential]$Credential, [byte[]]$Bytes)
    $loopback = $GatewayUri.Host -in @('localhost', '127.0.0.1', '::1')
    if (($GatewayUri.Scheme -ne 'https' -and -not ($loopback -and $GatewayUri.Scheme -eq 'http')) -or $GatewayUri.UserInfo -or $GatewayUri.Query -or $GatewayUri.Fragment -or $GatewayUri.AbsolutePath.TrimEnd('/') -ne '/glpi-agent') {
        throw 'A secure AssetGuard inventory endpoint is required.'
    }
    Add-Type -AssemblyName System.Net.Http
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.AllowAutoRedirect = $false
    $client = [Net.Http.HttpClient]::new($handler)
    $client.Timeout = [TimeSpan]::FromSeconds(30)
    $client.MaxResponseContentBufferSize = 65536
    $content = [Net.Http.ByteArrayContent]::new($Bytes)
    $content.Headers.ContentType = [Net.Http.Headers.MediaTypeHeaderValue]::new('application/xml')
    $response = $null
    try {
        $plain = $Credential.GetNetworkCredential().Password
        $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Credential.UserName + ':' + $plain))
        $client.DefaultRequestHeaders.Authorization = [Net.Http.Headers.AuthenticationHeaderValue]::new('Basic', $encoded)
        $plain = $null
        $response = $client.PostAsync($GatewayUri, $content).GetAwaiter().GetResult()
        $status = [int]$response.StatusCode
        if ($status -in @(401, 403, 409)) { return @{ Status = 'AUTH_REJECTED'; RetryAfterSeconds = 300 } }
        if ($status -in @(400, 413, 415, 422)) { return @{ Status = 'PERMANENT'; RetryAfterSeconds = 0 } }
        if ($status -eq 200) {
            try {
                $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
                $settings = [Xml.XmlReaderSettings]::new()
                $settings.DtdProcessing = [Xml.DtdProcessing]::Prohibit
                $settings.XmlResolver = $null
                $reader = [Xml.XmlReader]::Create([IO.StringReader]::new($body), $settings)
                try { $xml = [Xml.XmlDocument]::new(); $xml.XmlResolver = $null; $xml.Load($reader) }
                finally { $reader.Dispose() }
                if ($xml.DocumentElement.Name -eq 'REPLY' -and $xml.REPLY.RESPONSE -eq 'SEND') { return @{ Status = 'ACCEPTED'; RetryAfterSeconds = 0 } }
            }
            catch { }
        }
        $retryAfter = 0
        if ($response.Headers.RetryAfter) {
            if ($response.Headers.RetryAfter.Delta) { $retryAfter = [int]$response.Headers.RetryAfter.Delta.TotalSeconds }
            elseif ($response.Headers.RetryAfter.Date) { $retryAfter = [int]($response.Headers.RetryAfter.Date - [DateTimeOffset]::UtcNow).TotalSeconds }
        }
        return @{ Status = 'TRANSIENT'; RetryAfterSeconds = $retryAfter }
    }
    catch { return @{ Status = 'TRANSIENT'; RetryAfterSeconds = 0 } }
    finally { if ($response) { $response.Dispose() }; $content.Dispose(); $client.Dispose(); $encoded = $null; $plain = $null }
}

function Get-AssetGuardLocalInventory {
    param([string]$AgentRoot, [string]$Scratch, [string]$Tag, [string]$ProfilePath)
    if ((Test-Path -LiteralPath $Scratch) -and ((Get-Item -LiteralPath $Scratch).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Invalid collector directory.' }
    New-Item -ItemType Directory -Path $Scratch -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $Scratch 'state') -Force | Out-Null
    $drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($Scratch))
    if ($drive.AvailableFreeSpace -lt 32MB) { throw 'Insufficient free disk space for inventory collection.' }

    $output = Join-Path $scratch 'inventory.xml'
    $diagnostic = Join-Path $scratch 'collector.log'
    $stdout = Join-Path $scratch 'collector.stdout'
    if (Test-Path -LiteralPath $output) { Remove-Item -LiteralPath $output }
    # Explicit file backend has no server/password. The upstream daemon is disabled.
    $executable = Join-Path $agentRoot 'perl\bin\glpi-agent.exe'
    $script = Join-Path $agentRoot 'perl\bin\glpi-agent'
    $profile = $ProfilePath
    foreach ($path in @($script, $profile, $output, (Join-Path $scratch 'state'))) {
        if ($path -cmatch '["\r\n\x80-\uFFFF]') { throw "GLPI collector paths must use ASCII and contain no quotes: $path" }
    }
    $arguments = @('"' + $script + '"', '--conf-file="' + $profile + '"', '--local="' + $output + '"', '--vardir="' + (Join-Path $scratch 'state') + '"', '--tasks=inventory', '--force', '--no-httpd', '--logger=stderr', '--tag=' + $tag)
    $process = Start-Process -FilePath $executable -ArgumentList $arguments -WorkingDirectory $agentRoot -WindowStyle Hidden -RedirectStandardError $diagnostic -RedirectStandardOutput $stdout -PassThru
    # Cache the handle: Windows PowerShell 5.1 can otherwise return a null ExitCode.
    [void]$process.Handle
    if (-not $process.WaitForExit(120000)) {
        # taskkill /T also terminates collector children; stop before the next tick.
        & taskkill.exe /PID $process.Id /T /F | Out-Null
        throw 'Inventory collection exceeded its time limit.'
    }
    $process.WaitForExit()
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $output)) { throw 'Local inventory collection failed.' }
    if ((Get-Item -LiteralPath $output).Length -gt 2MB) { throw 'Local inventory exceeds the payload limit.' }
    $settings = [Xml.XmlReaderSettings]::new()
    $settings.DtdProcessing = [Xml.DtdProcessing]::Prohibit
    $settings.XmlResolver = $null
    $reader = [Xml.XmlReader]::Create($output, $settings)
    try { $xml = [Xml.XmlDocument]::new(); $xml.XmlResolver = $null; $xml.Load($reader) }
    finally { $reader.Dispose() }
    if ($xml.DocumentElement.Name -ne 'REQUEST' -or $xml.REQUEST.QUERY -ne 'INVENTORY' -or -not $xml.REQUEST.DEVICEID) { throw 'Invalid collector XML.' }
    $versionNode = $xml.REQUEST.CONTENT.SelectSingleNode('VERSIONCLIENT')
    if (-not $versionNode -or $versionNode.InnerText -notmatch '^(?:GLPI-Agent_v)?(?<version>1\.19|1\.20)$') { throw 'Unsupported collector version.' }
    $versionNode.InnerText = $Matches.version
    $forbidden = @('ACCESSLOG', 'ENVS', 'LICENSEINFOS', 'LOCAL_GROUPS', 'LOCAL_USERS', 'PROCESSES', 'SOFTWARES', 'USERS')
    foreach ($name in $forbidden) {
        if ($xml.REQUEST.CONTENT.SelectSingleNode($name)) { throw 'Inventory violates the hardware-only profile.' }
    }
    # This timestamp stays in immutable XML; retries keep exactly these bytes.
    $capture = $xml.CreateElement('ASSETGUARD_CAPTURED_AT')
    $capture.InnerText = [DateTimeOffset]::UtcNow.ToString('O')
    [void]$xml.DocumentElement.AppendChild($capture)
    return ,[Text.Encoding]::UTF8.GetBytes($xml.OuterXml)

}
