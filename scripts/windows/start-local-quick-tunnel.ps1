<# Starts a free Cloudflare Quick Tunnel for an already running local AssetGuard API. #>
[CmdletBinding()]
param(
    [uri]$LocalUrl = 'http://127.0.0.1:8000',
    [int]$WaitSeconds = 45
)

$ErrorActionPreference = 'Stop'
$cloudflared = (Get-Command cloudflared -ErrorAction Stop).Source
try { Invoke-WebRequest -Uri "$($LocalUrl.Scheme)://$($LocalUrl.Authority)/health" -UseBasicParsing | Out-Null }
catch { throw "AssetGuard API is not reachable at $LocalUrl. Start it first." }
$logPath = Join-Path $env:TEMP "assetguard-quick-tunnel-$PID.log"
$errorLogPath = "$logPath.err"
$process = Start-Process -FilePath $cloudflared -ArgumentList 'tunnel','--no-autoupdate','--url',$LocalUrl.AbsoluteUri -RedirectStandardOutput $logPath -RedirectStandardError $errorLogPath -WindowStyle Hidden -PassThru
$deadline = (Get-Date).AddSeconds($WaitSeconds)
do {
    if ((Test-Path -LiteralPath $logPath) -or (Test-Path -LiteralPath $errorLogPath)) {
        $logFiles = @($logPath, $errorLogPath) | Where-Object { Test-Path -LiteralPath $_ }
        $logs = ($logFiles | ForEach-Object { Get-Content -LiteralPath $_ -Raw }) -join "`n"
        $match = [regex]::Match($logs, 'https://[a-z0-9-]+\.trycloudflare\.com')
        if ($match.Success) {
            Write-Host "Public URL: $($match.Value)"
            Write-Host "Tunnel PID: $($process.Id). Keep this PowerShell process running until the pitch is finished."
            Write-Host 'When AssetGuard asks for the public URL while making a QR code, paste this address.'
            exit 0
        }
    }
    if ($process.HasExited) { throw "cloudflared exited. Log: $logPath" }
    Start-Sleep -Seconds 1
} while ((Get-Date) -lt $deadline)
throw "Cloudflare Quick Tunnel did not publish a URL within $WaitSeconds seconds. Log: $logPath"
