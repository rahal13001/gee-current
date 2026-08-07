/**
 * Recreate the canonical T6-006 sample asset IDs from validated replacements.
 *
 * The original IDs must be absent before these two tasks are submitted. The
 * `_fixed` assets remain as the validated source/evidence copies; these exports
 * restore the canonical IDs with the contract bands uo, vo, and speed.
 */

var SOURCE_FIXED_ID =
  'projects/ee-rahal13001/assets/glorys_current/surface_0p494025m/daily_jfm_2015_2025/glorys12v1_d_20150101_d0p494025m_fixed';
var SOURCE_ID =
  'projects/ee-rahal13001/assets/glorys_current/surface_0p494025m/daily_jfm_2015_2025/glorys12v1_d_20150101_d0p494025m';
var DERIVED_FIXED_ID =
  'projects/ee-rahal13001/assets/glorys_current/derived/speed/glorys12v1_speed_20150101_d0p494025m_fixed';
var DERIVED_ID =
  'projects/ee-rahal13001/assets/glorys_current/derived/speed/glorys12v1_speed_20150101_d0p494025m';

var REGION = ee.Geometry.Rectangle(
  [122.95833587646484, -12.20833160460091,
   143.37475776672363, 4.291666656732559],
  'EPSG:4326',
  false
);
var CRS_TRANSFORM = [
  0.0833282470703125, 0, 122.95833587646484,
  0, -0.08333331346511841, 4.291666656732559
];

var source = ee.Image(SOURCE_FIXED_ID)
  .select(['uo', 'vo'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2015-01-01').millis())
  .set('system:time_end', ee.Date('2015-01-02').millis())
  .set('date_utc', '2015-01-01')
  .set('source_asset', SOURCE_FIXED_ID)
  .set('band_mapping', 'uo->uo,vo->vo')
  .set('nodata_value', -9999)
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('dataset_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_label', 'top_model_layer')
  .set('units', 'm s-1')
  .set('aoi_id', 'eastern_indonesia_regional_001')
  .set('processing_status', 'canonical_asset_recreated_from_validated_fixed');

Export.image.toAsset({
  image: source,
  description: 't6_006_source_recreated_original_id',
  assetId: SOURCE_ID,
  region: REGION,
  crs: 'EPSG:4326',
  crsTransform: CRS_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var derived = ee.Image(DERIVED_FIXED_ID)
  .select(['speed'], ['speed'])
  .set('system:time_start', ee.Date('2015-01-01').millis())
  .set('system:time_end', ee.Date('2015-01-02').millis())
  .set('date_utc', '2015-01-01')
  .set('source_asset', DERIVED_FIXED_ID)
  .set('band_mapping', 'speed->speed')
  .set('nodata_value', -9999)
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('product_type', 'speed')
  .set('analytics_version', 'stage5-analytics-1.1')
  .set('depth_m', 0.494025)
  .set('depth_label', 'top_model_layer')
  .set('units', 'm s-1')
  .set('aoi_id', 'eastern_indonesia_regional_001')
  .set('method', 'speed = sqrt(uo^2 + vo^2); source uo/vo joint mask preserved')
  .set('processing_status', 'canonical_asset_recreated_from_validated_fixed');

Export.image.toAsset({
  image: derived,
  description: 't6_006_derived_recreated_original_id',
  assetId: DERIVED_ID,
  region: REGION,
  crs: 'EPSG:4326',
  crsTransform: CRS_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

print('T6-006 canonical recreation tasks prepared', {
  source_target: SOURCE_ID,
  derived_target: DERIVED_ID,
  source_bands: source.bandNames(),
  derived_bands: derived.bandNames()
});
