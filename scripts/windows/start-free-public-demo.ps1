<# Starts the complete demo and prints its temporary public HTTPS URL. #>
[CmdletBinding()]
param(
    [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')),
    [int]$WaitSeconds = 120
)

$ErrorActionPreference = 'Stop'
$envPath = Join-Path $RepositoryRoot '.env'
$composePath = Join-Path $RepositoryRoot 'infra\containers\docker-compose.free-demo.yml'
if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Missing $envPath. Run scripts/windows/new-local-env.ps1 first."
}

docker compose --env-file $envPath -f $composePath up -d --build
if ($LASTEXITCODE -ne 0) { throw 'The free public demo stack failed to start.' }

$deadline = (Get-Date).AddSeconds($WaitSeconds)
do {
    $logs = docker compose --env-file $envPath -f $composePath logs --no-color tunnel 2>&1 | Out-String
    $match = [regex]::Match($logs, 'https://[a-z0-9-]+\.trycloudflare\.com')
    if ($match.Success) {
        Write-Host "Local URL:  http://127.0.0.1:$($env:ASSETGUARD_DEMO_PORT ?? '8000')"
        Write-Host "Public URL: $($match.Value)"
        Write-Warning 'Quick Tunnel is for a temporary demonstration only. The URL changes after recreation.'
        exit 0
    }
    Start-Sleep -Seconds 2
} while ((Get-Date) -lt $deadline)

docker compose --env-file $envPath -f $composePath logs --no-color tunnel
throw "Cloudflare Quick Tunnel did not publish a URL within $WaitSeconds seconds."
