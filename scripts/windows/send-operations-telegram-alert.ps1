<#
.SYNOPSIS
Sends a deduplicated Telegram alert when AssetGuard operations need attention.

.DESCRIPTION
Reads Telegram credentials and the local AssetGuard admin token from .env at
run time. Neither secret is stored in the task definition or printed to output.
#>
[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [string]$ApiBaseUrl,
    [ValidateRange(5, 1440)] [int]$RepeatAfterMinutes = 240,
    [ValidateRange(1, 99)] [int]$MinimumFreeStoragePercent = 10,
    [string]$StateFile = (Join-Path $env:LOCALAPPDATA 'AssetGuard\operations-alert-state.json'),
    [string]$CredentialPath = (Join-Path $env:LOCALAPPDATA 'AssetGuard\telegram-credentials.clixml'),
    [switch]$SendTest
)
$ErrorActionPreference = 'Stop'
$envPath = Join-Path $RepositoryRoot '.env'
if (-not (Test-Path -LiteralPath $envPath)) { throw "Missing '$envPath'." }
foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match '^([^#=]+)=(.*)$') { Set-Item -Path "Env:$($matches[1])" -Value $matches[2] }
}
if ((-not $env:ASSETGUARD_TELEGRAM_BOT_TOKEN -or -not $env:ASSETGUARD_TELEGRAM_CHAT_ID) -and (Test-Path -LiteralPath $CredentialPath)) {
    $credential = Import-Clixml -LiteralPath $CredentialPath
    $env:ASSETGUARD_TELEGRAM_CHAT_ID = $credential.UserName
    $env:ASSETGUARD_TELEGRAM_BOT_TOKEN = $credential.GetNetworkCredential().Password
}
if (-not $env:ASSETGUARD_TELEGRAM_BOT_TOKEN -or -not $env:ASSETGUARD_TELEGRAM_CHAT_ID) {
    throw 'Configure Telegram in .env or create the current-user DPAPI credential with set-telegram-credentials.ps1.'
}
if (-not $ApiBaseUrl) { $ApiBaseUrl = $env:ASSETGUARD_PUBLIC_URL }
if (-not $ApiBaseUrl) { $ApiBaseUrl = 'http://127.0.0.1:8000' }
$ApiBaseUrl = $ApiBaseUrl.TrimEnd('/')

function Send-AssetGuardTelegram([string]$Message) {
    $uri = "https://api.telegram.org/bot$($env:ASSETGUARD_TELEGRAM_BOT_TOKEN)/sendMessage"
    $body = @{ chat_id = $env:ASSETGUARD_TELEGRAM_CHAT_ID; text = $Message; disable_web_page_preview = $true } | ConvertTo-Json -Compress
    $response = Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json; charset=utf-8' -Body $body -TimeoutSec 20
    if (-not $response.ok) { throw 'Telegram rejected the notification.' }
}

if ($SendTest) {
    Send-AssetGuardTelegram "✅ AssetGuard: тестовое уведомление доставлено. $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    Write-Host 'Telegram test alert sent.'
    exit 0
}

$headers = @{ 'X-AssetGuard-Admin-Token' = $env:ASSETGUARD_ADMIN_SHARED_SECRET }
$operations = Invoke-RestMethod -Method Get -Uri "$ApiBaseUrl/admin/operations/status" -Headers $headers -TimeoutSec 20
$offline = [int]$operations.agents.offline + [int]$operations.agents.stale
$failed = [int]$operations.ingest.failed
$conflicts = [int]$operations.agents.identity_conflicts
$freePercent = if ([int64]$operations.storage.total_bytes -gt 0) { [math]::Floor(100 * [double]$operations.storage.free_bytes / [double]$operations.storage.total_bytes) } else { 100 }
$problems = @()
if ($offline -gt 0) { $problems += "нет связи или устарели Agent: $offline" }
if ($failed -gt 0) { $problems += "ошибки приёма inventory: $failed" }
if ($conflicts -gt 0) { $problems += "конфликты идентификации: $conflicts" }
if ($freePercent -lt $MinimumFreeStoragePercent) { $problems += "мало места для Vision: $freePercent% свободно" }
if (-not $problems.Count) { Write-Host 'Operations are healthy; notification is not needed.'; exit 0 }

$fingerprint = "$offline|$failed|$conflicts|$freePercent"
$previous = $null
if (Test-Path -LiteralPath $StateFile) { $previous = Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json }
$now = [DateTimeOffset]::UtcNow
$lastSent = if ($previous.last_sent_utc) { [DateTimeOffset]::Parse($previous.last_sent_utc) } else { [DateTimeOffset]::MinValue }
if ($previous.fingerprint -eq $fingerprint -and ($now - $lastSent).TotalMinutes -lt $RepeatAfterMinutes) {
    Write-Host 'Alert condition is unchanged and still inside the repeat window.'
    exit 0
}
Send-AssetGuardTelegram ("⚠️ AssetGuard требует внимания`n" + ($problems -join "`n") + "`nПроверка: $($now.ToLocalTime().ToString('yyyy-MM-dd HH:mm'))")
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StateFile) | Out-Null
@{ fingerprint = $fingerprint; last_sent_utc = $now.ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath $StateFile -Encoding utf8
Write-Host 'Telegram alert sent.'
