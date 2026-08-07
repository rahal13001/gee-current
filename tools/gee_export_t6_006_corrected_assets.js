/**
 * Prepare corrected T6-006 sample assets without re-uploading source files.
 *
 * The original T6-005 assets were retained during validation; after explicit
 * approval they were replaced by the canonical recreation script. This file
 * remains the historical provenance for the `_fixed` validation assets.
 * These exports only rename the observed raster bands:
 *   source b1,b2 -> uo,vo
 *   derived b1   -> speed
 *
 * Run this script in the logged-in Earth Engine Code Editor, inspect both
 * generated tasks, and submit them only when the target IDs are confirmed
 * absent. The target IDs intentionally carry the `_fixed` suffix so no export
 * can overwrite the original assets.
 */

var SOURCE_ID =
  'projects/ee-rahal13001/assets/glorys_current/surface_0p494025m/daily_jfm_2015_2025/glorys12v1_d_20150101_d0p494025m';
var SOURCE_FIXED_ID =
  'projects/ee-rahal13001/assets/glorys_current/surface_0p494025m/daily_jfm_2015_2025/glorys12v1_d_20150101_d0p494025m_fixed';
var DERIVED_ID =
  'projects/ee-rahal13001/assets/glorys_current/derived/speed/glorys12v1_speed_20150101_d0p494025m';
var DERIVED_FIXED_ID =
  'projects/ee-rahal13001/assets/glorys_current/derived/speed/glorys12v1_speed_20150101_d0p494025m_fixed';

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

var sourceFixed = ee.Image(SOURCE_ID)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2015-01-01').millis())
  .set('system:time_end', ee.Date('2015-01-02').millis())
  .set('date_utc', '2015-01-01')
  .set('source_asset', SOURCE_ID)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('nodata_value', -9999)
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('dataset_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_label', 'top_model_layer')
  .set('units', 'm s-1')
  .set('aoi_id', 'eastern_indonesia_regional_001')
  .set('processing_status', 'corrected_band_contract');

Export.image.toAsset({
  image: sourceFixed,
  description: 't6_006_source_corrected_band_names',
  assetId: SOURCE_FIXED_ID,
  region: REGION,
  crs: 'EPSG:4326',
  crsTransform: CRS_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var derivedFixed = ee.Image(DERIVED_ID)
  .select(['b1'], ['speed'])
  .set('system:time_start', ee.Date('2015-01-01').millis())
  .set('system:time_end', ee.Date('2015-01-02').millis())
  .set('date_utc', '2015-01-01')
  .set('source_asset', DERIVED_ID)
  .set('band_mapping', 'b1->speed')
  .set('nodata_value', -9999)
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('product_type', 'speed')
  .set('analytics_version', 'stage5-analytics-1.1')
  .set('depth_m', 0.494025)
  .set('depth_label', 'top_model_layer')
  .set('units', 'm s-1')
  .set('aoi_id', 'eastern_indonesia_regional_001')
  .set('method', 'speed = sqrt(uo^2 + vo^2); source uo/vo joint mask preserved')
  .set('processing_status', 'corrected_band_contract');

Export.image.toAsset({
  image: derivedFixed,
  description: 't6_006_derived_corrected_band_name',
  assetId: DERIVED_FIXED_ID,
  region: REGION,
  crs: 'EPSG:4326',
  crsTransform: CRS_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

print('T6-006 corrected export tasks prepared', {
  source_target: SOURCE_FIXED_ID,
  derived_target: DERIVED_FIXED_ID,
  source_bands: sourceFixed.bandNames(),
  derived_bands: derivedFixed.bandNames()
});
