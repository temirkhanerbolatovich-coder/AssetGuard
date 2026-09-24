<#
Keeps a Cloudflare Quick Tunnel alive for a local AssetGuard demo.
It is intentionally a best-effort demo helper: each reconnection receives a new
trycloudflare.com URL. The current URL and last failure are saved outside the repo.
#>
[CmdletBinding()]
param(
    [uri]$LocalUrl = 'http://127.0.0.1:8000',
    [ValidateRange(5, 300)] [int]$RetrySeconds = 10,
    [string]$StatePath = (Join-Path $env:LOCALAPPDATA 'AssetGuard\quick-tunnel.json')
)

$ErrorActionPreference = 'Continue'
$cloudflared = (Get-Command cloudflared -ErrorAction Stop).Source
$stateDirectory = Split-Path -Parent $StatePath
New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null

while ($true) {
    $healthy = $false
    try {
        $health = Invoke-RestMethod -Uri "$($LocalUrl.Scheme)://$($LocalUrl.Authority)/health" -TimeoutSec 10
        $healthy = $health.status -eq 'ok'
    } catch { }
    if (-not $healthy) {
        [ordered]@{ status = 'waiting_for_api'; local_url = $LocalUrl.AbsoluteUri; updated_at = (Get-Date).ToUniversalTime().ToString('o') } |
            ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding utf8
        Start-Sleep -Seconds $RetrySeconds
        continue
    }

    $url = $null
    $startedAt = (Get-Date).ToUniversalTime().ToString('o')
    & $cloudflared tunnel --no-autoupdate --url $LocalUrl.AbsoluteUri 2>&1 | ForEach-Object {
        $line = $_.ToString()
        $match = [regex]::Match($line, 'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($match.Success -and -not $url) {
            $url = $match.Value
            [ordered]@{ status = 'connected'; public_url = $url; local_url = $LocalUrl.AbsoluteUri; started_at = $startedAt; updated_at = (Get-Date).ToUniversalTime().ToString('o') } |
                ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding utf8
        }
        Write-Host $line
    }
    [ordered]@{ status = 'reconnecting'; public_url = $url; local_url = $LocalUrl.AbsoluteUri; updated_at = (Get-Date).ToUniversalTime().ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding utf8
    Start-Sleep -Seconds $RetrySeconds
}
