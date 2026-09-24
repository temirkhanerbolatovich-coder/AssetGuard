<#
.SYNOPSIS
Builds the redistributable AssetGuard Agent Windows installer.

.DESCRIPTION
Requires Inno Setup 6. The installer is a bootstrapper: it contains only
AssetGuard configuration scripts and installs the official GLPI Agent with WinGet
on the destination computer. No credential, database, local .env, or inventory
data is included in the resulting EXE.
#>
[CmdletBinding()]
param(
    [string]$InnoSetupCompiler = ''
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$source = Join-Path $repositoryRoot 'installer\windows\AssetGuardAgent.iss'
if (-not (Test-Path -LiteralPath $source)) { throw "Inno Setup source was not found: $source" }

if ([string]::IsNullOrWhiteSpace($InnoSetupCompiler)) {
    $candidatePaths = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
    )
    $InnoSetupCompiler = $candidatePaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if ([string]::IsNullOrWhiteSpace($InnoSetupCompiler) -or -not (Test-Path -LiteralPath $InnoSetupCompiler)) {
    throw 'Inno Setup 6 was not found. Install it once with: winget install --id JRSoftware.InnoSetup --exact --source winget'
}

& $InnoSetupCompiler $source
if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed with exit code $LASTEXITCODE." }

$output = Join-Path $repositoryRoot 'installer-output\AssetGuard-Agent-Setup-0.1.1.exe'
if (-not (Test-Path -LiteralPath $output)) { throw "Expected installer output was not found: $output" }
$hash = Get-FileHash -LiteralPath $output -Algorithm SHA256
[pscustomobject]@{ Installer = $output; Bytes = (Get-Item -LiteralPath $output).Length; SHA256 = $hash.Hash }
