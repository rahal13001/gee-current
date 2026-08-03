[CmdletBinding()]
param([string]$ConfigRoot = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..')).Path 'config'))

$ErrorActionPreference = 'Stop'
$errors = [System.Collections.Generic.List[string]]::new()

function Read-Json([string]$Name) {
    $path = Join-Path $ConfigRoot $Name
    if (-not (Test-Path -LiteralPath $path)) {
        $errors.Add("missing:$Name")
        return $null
    }
    try { return Get-Content -Raw -LiteralPath $path | ConvertFrom-Json }
    catch { $errors.Add("invalid_json:$Name"); return $null }
}

$study = Read-Json 'study_area.json'
$period = Read-Json 'analysis_period.json'
$depth = Read-Json 'depth_selection.json'
$stats = Read-Json 'statistics.json'
$assets = Read-Json 'asset_naming.json'
$pilot = Read-Json 'pilot_config.example.json'
$local = Read-Json 'local.example.json'
$schema = Read-Json 'pilot_config.schema.json'

if ($study -and -not ($study.west -lt $study.east -and $study.south -lt $study.north)) { $errors.Add('study_area:invalid_bbox_order') }
if ($study -and $study.crs -ne 'EPSG:4326') { $errors.Add('study_area:unexpected_crs') }
if ($pilot -and -not ($pilot.west -lt $pilot.east -and $pilot.south -lt $pilot.north)) { $errors.Add('pilot_config:invalid_bbox_order') }
if ($pilot -and $pilot.crs -ne 'EPSG:4326') { $errors.Add('pilot_config:unexpected_crs') }
if ($period -and ($period.full_period.end_exclusive -ne '2026-01-01' -or $period.monthly_count_expected -ne 132 -or $period.daily_jfm_count_expected -ne 993)) { $errors.Add('analysis_period:project_counts_or_end_date_mismatch') }
if ($depth -and [math]::Abs([double]$depth.analysis_depth_m - 0.494025) -gt 0.000001) { $errors.Add('depth_selection:target_mismatch') }
if ($stats -and $stats.speed_thresholds_mps.Count -ne 0) { $errors.Add('statistics:thresholds_must_remain_empty_until_approved') }

foreach ($item in @($local, $pilot, $assets)) {
    if ($item -and $item.earth_engine_project_id -and $item.earth_engine_asset_root) {
        $expected = "projects/$($item.earth_engine_project_id)/assets/"
        if (-not $item.earth_engine_asset_root.StartsWith($expected)) { $errors.Add('asset_root:project_prefix_mismatch') }
    }
}

$secretPattern = '(?i)(password|passwd|secret|api[_-]?key|access[_-]?token|private[_-]?key)'
foreach ($file in Get-ChildItem -LiteralPath $ConfigRoot -Filter '*.json' -File) {
    if ((Get-Content -Raw -LiteralPath $file.FullName) -match $secretPattern) { $errors.Add("config:secret_field_name:$($file.Name)") }
}

if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Output $_ }
    exit 1
}

Write-Output 'M1 configuration validation: PASS_WITH_NOTES'
Write-Output 'AOI ordering, EPSG:4326, project period counts, depth target, asset-root prefix, and empty thresholds validated.'
Write-Output 'Limitations: no network, authentication, asset existence check, or operational computation performed.'
exit 0
