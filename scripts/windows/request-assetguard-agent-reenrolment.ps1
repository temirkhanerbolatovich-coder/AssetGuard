<#
.SYNOPSIS
Requests administrator-approved AssetGuard Agent re-enrolment after Windows reinstall.

.DESCRIPTION
The script sends the current SMBIOS UUID to AssetGuard, keeps the one-time claim
token only in process memory, and waits for an administrator decision. The token
becomes the new inventory secret after approval; neither the server nor this
script persists it in plaintext.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [uri]$GatewayUri,

    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$InstallerVersion = '0.1.7',

    [ValidateRange(2, 30)]
    [int]$PollSeconds = 5,

    [ValidateRange(1, 30)]
    [int]$TimeoutMinutes = 30
)

$ErrorActionPreference = 'Stop'
if ($GatewayUri.Scheme -ne 'https' -or $GatewayUri.AbsolutePath.TrimEnd('/') -ne '/glpi-agent') {
    throw 'GatewayUri must be exactly an HTTPS AssetGuard /glpi-agent endpoint.'
}

$systemProduct = Get-CimInstance Win32_ComputerSystemProduct -ErrorAction Stop
$hardwareUuid = [string]$systemProduct.UUID
if ([string]::IsNullOrWhiteSpace($hardwareUuid) -or $hardwareUuid -match '^(0+|F+)(-0+)*$') {
    throw 'Windows did not report a usable SMBIOS UUID for secure re-enrolment.'
}

$baseUri = $GatewayUri.GetLeftPart([System.UriPartial]::Authority)
$requestUri = "$baseUri/agent/re-enrolments"
$body = @{
    identifier_type = 'SMBIOS_UUID'
    identifier_value = $hardwareUuid
    computer_name = $env:COMPUTERNAME
    installer_version = $InstallerVersion
} | ConvertTo-Json

$requested = Invoke-RestMethod -Method Post -Uri $requestUri -ContentType 'application/json' -Body $body
$claimToken = [string]$requested.claim_token
$requestId = [string]$requested.id
if ([string]::IsNullOrWhiteSpace($claimToken) -or [string]::IsNullOrWhiteSpace($requestId)) {
    throw 'AssetGuard returned an incomplete re-enrolment response.'
}

$deadline = [DateTimeOffset]::UtcNow.AddMinutes($TimeoutMinutes)
try {
    while ([DateTimeOffset]::UtcNow -lt $deadline) {
        $status = Invoke-RestMethod -Method Get -Uri "$requestUri/$requestId" -Headers @{
            'X-AssetGuard-Reenrolment-Token' = $claimToken
        }
        switch ([string]$status.status) {
            'APPROVED' {
                if ([string]::IsNullOrWhiteSpace([string]$status.agent_username)) {
                    throw 'Approved re-enrolment did not include an Agent username.'
                }
                [pscustomobject]@{
                    RequestId = $requestId
                    AgentUsername = [string]$status.agent_username
                    InventorySecret = ConvertTo-SecureString -String $claimToken -AsPlainText -Force
                }
                return
            }
            'REJECTED' { throw 'The AssetGuard administrator rejected this re-enrolment request.' }
            'EXPIRED' { throw 'The AssetGuard re-enrolment request expired before approval.' }
            'PENDING' { Start-Sleep -Seconds $PollSeconds }
            default { throw "AssetGuard returned an unknown re-enrolment status '$($status.status)'." }
        }
    }
    throw 'Timed out waiting for AssetGuard administrator approval.'
}
finally {
    $claimToken = $null
}
