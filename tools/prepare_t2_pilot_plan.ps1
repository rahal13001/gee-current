[CmdletBinding()]
param(
    [string]$ConfigRoot = (Join-Path $PSScriptRoot '..\config')
)

$ErrorActionPreference = 'Stop'

function Read-ConfigJson([string]$Name) {
    $path = Join-Path $ConfigRoot $Name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Missing configuration file: $path"
    }
    return Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
}

try {
    $pilot = Read-ConfigJson 'pilot_config.example.json'
    $local = Read-ConfigJson 'local.example.json'
    $depth = Read-ConfigJson 'depth_selection.json'
}
catch {
    Write-Output 'status=BLOCKED'
    Write-Output ('error=' + $_.Exception.Message)
    Write-Output 'limitations=No network, authentication, download, or upload was performed.'
    exit 2
}

$errors = [System.Collections.Generic.List[string]]::new()
if ($pilot.aoi_id -ne 'pilot_001') {
    $errors.Add('pilot aoi_id must be pilot_001')
}
if ($pilot.crs -ne 'EPSG:4326') {
    $errors.Add('AOI CRS must be EPSG:4326')
}
foreach ($field in @('west', 'east', 'south', 'north')) {
    if ($null -eq $pilot.$field) {
        $errors.Add("pilot AOI field missing: $field")
    }
}
if (-not ([double]$pilot.west -lt [double]$pilot.east -and [double]$pilot.south -lt [double]$pilot.north)) {
    $errors.Add('AOI bbox ordering is invalid')
}
if ($pilot.pilot_period.start -ne '2020-02-01' -or
    $pilot.pilot_period.end -ne '2020-03-01' -or
    $pilot.pilot_period.end_inclusive -ne $false) {
    $errors.Add('pilot period must be 2020-02-01 inclusive to 2020-03-01 exclusive')
}
if ($local.copernicus_product_id -ne 'GLOBAL_MULTIYEAR_PHY_001_030') {
    $errors.Add('product ID does not match approved baseline')
}
if ($local.copernicus_daily_dataset_id -ne 'cmems_mod_glo_phy_my_0.083deg_P1D-m') {
    $errors.Add('daily dataset ID does not match approved baseline')
}
if ($depth.analysis_depth_m -ne 0.494025 -or
    $depth.label -ne 'top_model_layer' -or
    $depth.full_50_level_extraction_status -ne 'VERIFIED_USER_ACTIVE_DESCRIBE') {
    $errors.Add('verified depth configuration is incomplete')
}
if ($local.earth_engine_asset_root -ne $pilot.earth_engine_asset_root) {
    $errors.Add('asset root mismatch between local and pilot configuration')
}

$start = [datetime]::ParseExact($pilot.pilot_period.start, 'yyyy-MM-dd', $null)
$end = [datetime]::ParseExact($pilot.pilot_period.end, 'yyyy-MM-dd', $null)
$dates = @()
for ($date = $start; $date -lt $end; $date = $date.AddDays(1)) {
    $dates += $date.ToString('yyyy-MM-dd')
}
if ($dates.Count -ne 29) {
    $errors.Add("pilot period generated $($dates.Count) dates; expected 29")
}

if ($errors.Count -gt 0) {
    Write-Output 'status=BLOCKED'
    foreach ($error in $errors) {
        Write-Output ('error=' + $error)
    }
    Write-Output 'limitations=No network, authentication, download, or upload was performed.'
    exit 2
}

Write-Output 'status=PASS_WITH_NOTES'
Write-Output 'mode=DRY_RUN'
Write-Output 'network=NOT_PERFORMED'
Write-Output 'authentication=NOT_PERFORMED'
Write-Output 'download=NOT_PERFORMED'
Write-Output 'upload=NOT_PERFORMED'
Write-Output ('aoi_id=' + $pilot.aoi_id)
Write-Output ('aoi_source=' + $pilot.aoi_source)
Write-Output ('crs=' + $pilot.crs)
Write-Output ('bbox_west=' + $pilot.west)
Write-Output ('bbox_east=' + $pilot.east)
Write-Output ('bbox_south=' + $pilot.south)
Write-Output ('bbox_north=' + $pilot.north)
Write-Output ('product_id=' + $local.copernicus_product_id)
Write-Output ('daily_dataset_id=' + $local.copernicus_daily_dataset_id)
Write-Output 'variables=uo,vo'
Write-Output ('start_inclusive=' + $pilot.pilot_period.start)
Write-Output ('end_exclusive=' + $pilot.pilot_period.end)
Write-Output ('expected_timestep_count=' + $dates.Count)
Write-Output ('depth_m=' + $depth.analysis_depth_m)
Write-Output ('depth_selection_status=' + $depth.full_50_level_extraction_status)
Write-Output ('planned_dates=' + ($dates -join ','))
Write-Output 'next_gate=User review required before any Copernicus subset or download.'
Write-Output 'limitations=Plan validates local configuration only; no asset existence, write access, NetCDF, or Cloud operation was checked.'
exit 0
