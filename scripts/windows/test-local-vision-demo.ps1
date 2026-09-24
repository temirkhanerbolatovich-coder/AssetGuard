<#
.SYNOPSIS
Runs AssetGuard Vision's real local baseline-to-warning demonstration.

.DESCRIPTION
Creates an isolated demo location through the local API, sends the two bundled
room photos through the actual Grounding DINO model, accepts the first scan as a
baseline, and verifies that the second scan reports a visual discrepancy.
No request is sent to the public server. The admin bootstrap secret remains in
memory and is never written to command-line arguments, output, or logs.
#>
[CmdletBinding()]
param(
    [string]$RepositoryRoot,
    [int]$Port = 8010
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Net.Http
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) { $RepositoryRoot = Resolve-Path (Join-Path $scriptDirectory '..\..') }
$envPath = Join-Path $RepositoryRoot '.env'
$baselineImage = Join-Path $RepositoryRoot 'demo\vision\room-305-baseline.png'
$warningImage = Join-Path $RepositoryRoot 'demo\vision\room-305-warning.png'
if (-not (Test-Path -LiteralPath $envPath)) { throw "Missing $envPath. Run scripts/windows/new-local-env.ps1 first." }
foreach ($image in @($baselineImage, $warningImage)) {
    if (-not (Test-Path -LiteralPath $image)) { throw "Missing demo image '$image'." }
}

$settings = @{}
foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match '^([^#=]+)=(.*)$') { $settings[$matches[1]] = $matches[2] }
}
$adminSecret = $settings['ASSETGUARD_ADMIN_SHARED_SECRET']
if ([string]::IsNullOrWhiteSpace($adminSecret)) { throw 'Local .env does not contain ASSETGUARD_ADMIN_SHARED_SECRET.' }

$baseUrl = "http://127.0.0.1:$Port"
try { Invoke-RestMethod -Uri "$baseUrl/health" -TimeoutSec 8 | Out-Null }
catch { throw "Local Vision demo is not ready at $baseUrl. Run start-local-vision-demo.ps1 first." }

$headers = @{ 'X-AssetGuard-Admin-Token' = $adminSecret }
$suffix = Get-Date -Format 'yyyyMMdd-HHmmss'
$building = Invoke-RestMethod -Method Post -Uri "$baseUrl/admin/locations/buildings" -Headers $headers -ContentType 'application/json' -Body (@{ name = "Vision demo $suffix" } | ConvertTo-Json)
$floor = Invoke-RestMethod -Method Post -Uri "$baseUrl/admin/locations/buildings/$($building.id)/floors" -Headers $headers -ContentType 'application/json' -Body (@{ name = '1' } | ConvertTo-Json)
$room = Invoke-RestMethod -Method Post -Uri "$baseUrl/admin/locations/floors/$($floor.id)/rooms" -Headers $headers -ContentType 'application/json' -Body (@{ name = '305'; purpose = 'Local Vision test' } | ConvertTo-Json)

function Send-VisionPhoto([string]$Path) {
    # Windows PowerShell 5.1 has no Invoke-RestMethod -Form, so build multipart
    # content with .NET. The admin secret stays in memory rather than in a command line.
    $client = [System.Net.Http.HttpClient]::new()
    $multipart = [System.Net.Http.MultipartFormDataContent]::new()
    $stream = [System.IO.File]::OpenRead($Path)
    $file = [System.Net.Http.StreamContent]::new($stream)
    try {
        $client.Timeout = [TimeSpan]::FromMinutes(15)
        $client.DefaultRequestHeaders.Add('X-AssetGuard-Admin-Token', $adminSecret)
        $multipart.Add([System.Net.Http.StringContent]::new([string]$room.id), 'location_room_id')
        $file.Headers.ContentType = [System.Net.Http.Headers.MediaTypeHeaderValue]::Parse('image/png')
        $multipart.Add($file, 'image', [System.IO.Path]::GetFileName($Path))
        $response = $client.PostAsync("$baseUrl/admin/vision/scans", $multipart).GetAwaiter().GetResult()
        $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) { throw "Vision scan failed with HTTP $([int]$response.StatusCode): $body" }
        return $body | ConvertFrom-Json
    }
    finally {
        $multipart.Dispose()
        $stream.Dispose()
        $client.Dispose()
    }
}

Write-Host 'Processing baseline photo with the real Grounding DINO model. The first run may download the model.'
$first = Send-VisionPhoto $baselineImage
if ($first.status -ne 'NOT_CHECKED') { throw "Baseline scan returned unexpected status '$($first.status)'." }
$baseline = Invoke-RestMethod -Method Post -Uri "$baseUrl/admin/vision/rooms/$($first.room_id)/baseline" -Headers $headers -ContentType 'application/json' -Body (@{ scan_id = $first.id } | ConvertTo-Json)

Write-Host 'Processing comparison photo with the same real model.'
$second = Send-VisionPhoto $warningImage
if ($second.status -ne 'WARNING') {
    throw "Expected a WARNING after the comparison scan, but received '$($second.status)'. Counts: $($second.counts | ConvertTo-Json -Compress)"
}
if (-not $second.comparison.differences -or $second.comparison.differences.Count -lt 1) { throw 'WARNING was returned without an explainable count difference.' }

[pscustomobject]@{
    Result = 'PASS'
    LocalUrl = $baseUrl
    Room = $room.name
    BaselineCounts = $baseline.counts
    ComparisonCounts = $second.counts
    Differences = $second.comparison.differences
    AnnotatedImage = "$baseUrl$($second.annotated_image_url)"
} | ConvertTo-Json -Depth 6
