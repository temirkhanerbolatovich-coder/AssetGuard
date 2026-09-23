<#
Creates a reproducible pitch case through the same public inventory and admin APIs
used by GLPI Agent. The second FULL inventory omits one RAM module, so AssetGuard
creates an explainable COMPONENT_REMOVED event and an Incident.

This is a controlled demo fixture, not a claim that hardware was physically stolen.
#>
[CmdletBinding()]
param(
    [uri]$BaseUri = 'http://127.0.0.1:8000',
    [string]$EnvironmentFile = (Join-Path $PSScriptRoot '..\..\.env'),
    [string]$RunId = (Get-Date -Format 'yyyyMMddHHmmss')
)

$ErrorActionPreference = 'Stop'
$base = $BaseUri.AbsoluteUri.TrimEnd('/')
if ($BaseUri.Host -notin @('localhost', '127.0.0.1', '::1') -and $BaseUri.Scheme -ne 'https') {
    throw 'A non-loopback demo endpoint must use HTTPS.'
}
if (-not (Test-Path -LiteralPath $EnvironmentFile)) {
    throw "Environment file was not found: $EnvironmentFile"
}

$settings = @{}
Get-Content -LiteralPath $EnvironmentFile | Where-Object { $_ -match '^[A-Za-z_][A-Za-z0-9_]*=' } | ForEach-Object {
    $name, $value = $_ -split '=', 2
    $settings[$name] = $value
}
$ingestToken = $env:ASSETGUARD_INVENTORY_SHARED_SECRET
$adminToken = $env:ASSETGUARD_ADMIN_SHARED_SECRET
if ([string]::IsNullOrWhiteSpace($ingestToken)) { $ingestToken = $settings['ASSETGUARD_INVENTORY_SHARED_SECRET'] }
if ([string]::IsNullOrWhiteSpace($adminToken)) { $adminToken = $settings['ASSETGUARD_ADMIN_SHARED_SECRET'] }
if ([string]::IsNullOrWhiteSpace($ingestToken) -or [string]::IsNullOrWhiteSpace($adminToken)) {
    throw 'Inventory and admin secrets are required in the environment or .env file.'
}

$adminHeaders = @{ 'X-AssetGuard-Admin-Token' = $adminToken }
function Send-Inventory([object]$Payload) {
    $headers = @{
        'X-AssetGuard-Ingest-Token' = $ingestToken
        'X-AssetGuard-Idempotency-Key' = [guid]::NewGuid().ToString()
        'X-AssetGuard-Source' = 'GLPI_AGENT'
        'X-AssetGuard-Source-Version' = '1.19-pitch-fixture'
        'X-AssetGuard-Schema-Version' = 'glpi-agent-minimal-v1'
        'X-AssetGuard-Inventory-Type' = 'FULL'
    }
    Invoke-RestMethod -Method Post -Uri "$base/internal/inventories" -Headers $headers -ContentType 'application/json' -Body ($Payload | ConvertTo-Json -Depth 12)
}

$deviceId = "PITCH-PC-$RunId"
$macTail = [guid]::NewGuid().ToString('N').Substring(0, 6)
$demoMac = "02:30:50:$($macTail.Substring(0, 2)):$($macTail.Substring(2, 2)):$($macTail.Substring(4, 2))"
$initial = [ordered]@{
    action = 'inventory'
    deviceid = $deviceId
    itemtype = 'Computer'
    content = [ordered]@{
        hardware = [ordered]@{ name = 'PC-305-TEACHER'; uuid = "pitch-smbios-$RunId"; chassis_type = 'Desktop'; memory = 16384; workgroup = 'COLLEGE' }
        bios = [ordered]@{ smanufacturer = 'Lenovo'; smodel = 'ThinkCentre M70q'; ssn = "PC305-$RunId"; bmanufacturer = 'LENOVO'; bversion = 'M2WKT58A' }
        operatingsystem = [ordered]@{ full_name = 'Microsoft Windows 11 Pro'; version = '23H2'; kernel_version = '10.0.22631'; arch = '64-bit' }
        cpus = @([ordered]@{ name = 'Intel Core i5-12400'; manufacturer = 'Intel'; core = 6; thread = 12; speed = 2500 })
        memories = @(
            [ordered]@{ serialnumber = "RAM-A-$RunId"; numslots = 'DIMM 0'; capacity = 8589934592; manufacturer = 'Kingston'; partnumber = 'KVR32N22S8/8'; speed = 3200; type = 'DDR4' },
            [ordered]@{ serialnumber = "RAM-B-$RunId"; numslots = 'DIMM 1'; capacity = 8589934592; manufacturer = 'Kingston'; partnumber = 'KVR32N22S8/8'; speed = 3200; type = 'DDR4' }
        )
        storages = @([ordered]@{ serial = "SSD-$RunId"; model = 'Samsung NVMe 980'; disksize = 512000; type = 'SSD'; interface = 'NVMe' })
        networks = @([ordered]@{ macaddr = $demoMac; description = 'Intel Ethernet Connection'; status = 'Up'; speed = '1 Gbit/s' })
    }
}

$first = Send-Inventory $initial
$snapshot = Invoke-RestMethod -Uri "$base/admin/snapshots/$($first.snapshot_id)" -Headers $adminHeaders
$assetBody = @{
    inventory_number = "PITCH-$RunId"
    name = 'ПК преподавателя — демо инцидент'
    asset_type = 'Desktop'
    room = 'Кабинет 305'
    notes = 'Контролируемый сценарий для питча: исчезновение второго модуля RAM.'
} | ConvertTo-Json
$asset = Invoke-RestMethod -Method Post -Uri "$base/admin/assets" -Headers $adminHeaders -ContentType 'application/json' -Body $assetBody
Invoke-RestMethod -Method Post -Uri "$base/admin/endpoints/$($snapshot.endpoint_id)/asset/$($asset.id)" -Headers $adminHeaders | Out-Null
$baselineBody = @{ reason = 'Исходный состав перед демонстрацией' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$base/admin/snapshots/$($first.snapshot_id)/baseline" -Headers $adminHeaders -ContentType 'application/json' -Body $baselineBody | Out-Null

$changed = $initial | ConvertTo-Json -Depth 12 | ConvertFrom-Json
$changed.content.memories = @($changed.content.memories[0])
$second = Send-Inventory $changed
$incidents = @(Invoke-RestMethod -Uri "$base/admin/incidents?endpoint_id=$($snapshot.endpoint_id)" -Headers $adminHeaders)
$changes = @(Invoke-RestMethod -Uri "$base/admin/changes?endpoint_id=$($snapshot.endpoint_id)" -Headers $adminHeaders)

[pscustomobject]@{
    Result = 'READY'
    Device = $asset.name
    InventoryNumber = $asset.inventory_number
    AssetId = $asset.id
    EndpointId = $snapshot.endpoint_id
    BaselineSnapshotId = $first.snapshot_id
    ChangedSnapshotId = $second.snapshot_id
    Change = $changes[0].type
    IncidentStatus = $incidents[0].status
    PitchAction = "Open $base, refresh the page, then click 'Open device card' for $($asset.name)."
}
