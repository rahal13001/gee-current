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
if ($period -and (($period.years -join ',') -ne '2015,2016,2017,2018,2019,2020,2021,2022,2023,2024,2025')) { $errors.Add('analysis_period:years_mismatch') }
if ($period -and ($period.january_march.start_month -ne 1 -or $period.january_march.start_day -ne 1 -or $period.january_march.end_month_exclusive -ne 4 -or $period.january_march.end_day -ne 1)) { $errors.Add('analysis_period:jfm_definition_mismatch') }
if ($depth -and [math]::Abs([double]$depth.analysis_depth_m - 0.494025) -gt 0.000001) { $errors.Add('depth_selection:target_mismatch') }
if ($depth -and ($depth.label -ne 'top_model_layer' -or $depth.selection_method -ne 'exact_after_verification' -or [math]::Abs([double]$depth.tolerance_m - 0.000001) -gt 0.000000000001 -or $depth.full_50_level_extraction_status -ne 'VERIFIED_USER_ACTIVE_DESCRIBE')) { $errors.Add('depth_selection:approved_metadata_mismatch') }
if ($stats -and $stats.speed_thresholds_mps.Count -ne 0) { $errors.Add('statistics:thresholds_must_remain_empty_derived_p90') }
if ($stats -and ($stats.direction_convention -ne 'towards_clockwise_from_north' -or $stats.threshold_status -ne 'RESOLVED_GLOBAL_AOI_P90' -or [double]$stats.minimum_valid_area_fraction -ne 0.95 -or $stats.threshold_method -ne 'relative_high_current_threshold_global_p90' -or $stats.threshold_units -ne 'm s-1' -or $stats.threshold_scope -ne 'global_aoi_per_analysis_plan_id' -or $stats.threshold_label -ne 'Ambang kondisi arus relatif tinggi, P90')) { $errors.Add('statistics:convention_or_resolved_decision_mismatch') }
if ($stats -and ($stats.current_rose.sector_count -ne 16 -or [double]$stats.current_rose.sector_width_deg -ne 22.5 -or $stats.current_rose.direction_convention -ne 'towards' -or $stats.current_rose.direction_reference -ne 'true_north' -or $stats.current_rose.direction_rotation -ne 'clockwise' -or [double]$stats.current_rose.zero_epsilon_mps -ne 0.000001 -or $stats.current_rose.speed_bin_method -ne 'global_aoi_quantiles' -or ($stats.current_rose.speed_bin_quantiles -join ',') -ne '0.25,0.5,0.75,0.9' -or $stats.current_rose.missing_policy -ne 'pairwise_valid_uv_and_minimum_valid_area' -or $stats.current_rose.sparse_class_count -ne 5)) { $errors.Add('statistics:current_rose_decision_mismatch') }
if ($stats -and (($stats.speed_statistics -join ',') -ne 'count,mean,min,max,median,standard_deviation,variance,p10,p25,p50,p75,p90,p95,p99')) { $errors.Add('statistics:speed_fields_mismatch') }
if ($stats -and (($stats.vector_statistics -join ',') -ne 'mean_u,mean_v,resultant_speed,resultant_direction,persistence_index')) { $errors.Add('statistics:vector_fields_mismatch') }

if ($local -and ($local.copernicus_product_id -ne 'GLOBAL_MULTIYEAR_PHY_001_030' -or $local.copernicus_daily_dataset_id -ne 'cmems_mod_glo_phy_my_0.083deg_P1D-m' -or $local.copernicus_monthly_dataset_id -ne 'cmems_mod_glo_phy_my_0.083deg_P1M-m' -or $local.display_timezone -ne 'Asia/Jayapura')) { $errors.Add('local:approved_metadata_identifiers_mismatch') }

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
Write-Output 'AOI ordering, EPSG:4326, period/JFM fields, depth selection metadata, statistic fields, dataset IDs, timezone, asset-root prefix, and resolved P90/current-rose decisions validated.'
Write-Output 'Limitations: no network, authentication, asset existence check, or operational computation performed.'
exit 0
