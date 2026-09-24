<#
.SYNOPSIS
Starts an isolated local AssetGuard Vision demo on http://127.0.0.1:8010.

.DESCRIPTION
Uses Docker only on the current computer. The demo has its own Compose project,
PostgreSQL volume and model cache, so it neither alters the public Oracle server
nor conflicts with a locally running development database. Grounding DINO is
downloaded lazily on the first image scan and is cached afterwards.
#>
[CmdletBinding()]
param(
    [string]$RepositoryRoot,
    [int]$Port = 8010,
    [int]$WaitSeconds = 180,
    [switch]$OpenBrowser
)

$ErrorActionPreference = 'Stop'
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($RepositoryRoot)) { $RepositoryRoot = Resolve-Path (Join-Path $scriptDirectory '..\..') }
$envPath = Join-Path $RepositoryRoot '.env'
$composePath = Join-Path $RepositoryRoot 'infra\containers\docker-compose.free-demo.yml'
if (-not (Test-Path -LiteralPath $envPath)) { throw "Missing $envPath. Run scripts/windows/new-local-env.ps1 first." }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker Desktop is required for the local Vision demo.' }

$environment = @{}
foreach ($line in Get-Content -LiteralPath $envPath) {
    if ($line -match '^([^#=]+)=(.*)$') { $environment[$matches[1]] = $matches[2] }
}
if (-not $environment.ContainsKey('ASSETGUARD_ADMIN_SHARED_SECRET')) { throw 'Local .env does not contain ASSETGUARD_ADMIN_SHARED_SECRET.' }

$environment['ASSETGUARD_DEMO_PORT'] = "$Port"
$composeArgs = @('--project-name', 'assetguard-vision-demo', '--env-file', $envPath, '-f', $composePath)
foreach ($item in $environment.GetEnumerator()) { Set-Item -Path "Env:$($item.Key)" -Value $item.Value }

& docker compose @composeArgs up -d --build postgres api
if ($LASTEXITCODE -ne 0) { throw 'The local Vision containers could not be started.' }

$healthUrl = "http://127.0.0.1:$Port/health"
$deadline = (Get-Date).AddSeconds($WaitSeconds)
do {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5
        if ($health.status -eq 'ok') {
            Write-Host "Local Vision demo is ready: http://127.0.0.1:$Port"
            Write-Host 'Run scripts/windows/test-local-vision-demo.ps1 to execute the baseline-to-warning scenario.'
            if ($OpenBrowser) { Start-Process "http://127.0.0.1:$Port" }
            exit 0
        }
    }
    catch { }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

& docker compose @composeArgs logs --no-color api
throw "The local Vision API did not become healthy within $WaitSeconds seconds."
