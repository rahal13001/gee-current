/**
 * Normalize the 26 raw February 2020 pilot assets that do not yet have a
 * corrected counterpart.
 *
 * Existing corrected assets for 20200201, 20200215, and 20200229 are reused;
 * this file deliberately creates only the remaining 26 targets.
 *
 * Paste into the Earth Engine Code Editor, run once, review the 26 export
 * tasks, and submit them from the Tasks panel. Do not rerun if a target asset
 * already exists unless overwrite/replacement is intentionally approved.
 * Authentication and task submission remain user-managed.
 */

var AOI = ee.Geometry.Rectangle(
  [129.12500518798828, -2.874999919762978,
   133.3749948120117, 1.5416666659025045],
  'EPSG:4326',
  false
);

var GRID_TRANSFORM = [
  0.0833331298828125, 0, 129.12500518798828,
  0, -0.08333333180500911, 1.5416666659025045
];

var fixed02 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200202'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-02').millis())
  .set('date_utc', '2020-02-02')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200202')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed02,
  description: 'glorys_current_20200202_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200202_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed03 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200203'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-03').millis())
  .set('date_utc', '2020-02-03')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200203')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed03,
  description: 'glorys_current_20200203_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200203_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed04 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200204'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-04').millis())
  .set('date_utc', '2020-02-04')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200204')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed04,
  description: 'glorys_current_20200204_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200204_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed05 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200205'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-05').millis())
  .set('date_utc', '2020-02-05')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200205')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed05,
  description: 'glorys_current_20200205_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200205_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed06 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200206'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-06').millis())
  .set('date_utc', '2020-02-06')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200206')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed06,
  description: 'glorys_current_20200206_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200206_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed07 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200207'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-07').millis())
  .set('date_utc', '2020-02-07')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200207')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed07,
  description: 'glorys_current_20200207_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200207_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed08 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200208'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-08').millis())
  .set('date_utc', '2020-02-08')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200208')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed08,
  description: 'glorys_current_20200208_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200208_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed09 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200209'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-09').millis())
  .set('date_utc', '2020-02-09')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200209')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed09,
  description: 'glorys_current_20200209_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200209_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed10 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200210'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-10').millis())
  .set('date_utc', '2020-02-10')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200210')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed10,
  description: 'glorys_current_20200210_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200210_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed11 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200211'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-11').millis())
  .set('date_utc', '2020-02-11')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200211')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed11,
  description: 'glorys_current_20200211_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200211_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed12 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200212'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-12').millis())
  .set('date_utc', '2020-02-12')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200212')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed12,
  description: 'glorys_current_20200212_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200212_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed13 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200213'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-13').millis())
  .set('date_utc', '2020-02-13')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200213')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed13,
  description: 'glorys_current_20200213_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200213_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed14 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200214'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-14').millis())
  .set('date_utc', '2020-02-14')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200214')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed14,
  description: 'glorys_current_20200214_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200214_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed16 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200216'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-16').millis())
  .set('date_utc', '2020-02-16')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200216')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed16,
  description: 'glorys_current_20200216_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200216_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed17 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200217'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-17').millis())
  .set('date_utc', '2020-02-17')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200217')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed17,
  description: 'glorys_current_20200217_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200217_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed18 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200218'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-18').millis())
  .set('date_utc', '2020-02-18')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200218')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed18,
  description: 'glorys_current_20200218_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200218_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed19 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200219'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-19').millis())
  .set('date_utc', '2020-02-19')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200219')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed19,
  description: 'glorys_current_20200219_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200219_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed20 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200220'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-20').millis())
  .set('date_utc', '2020-02-20')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200220')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed20,
  description: 'glorys_current_20200220_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200220_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed21 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200221'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-21').millis())
  .set('date_utc', '2020-02-21')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200221')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed21,
  description: 'glorys_current_20200221_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200221_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed22 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200222'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-22').millis())
  .set('date_utc', '2020-02-22')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200222')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed22,
  description: 'glorys_current_20200222_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200222_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed23 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200223'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-23').millis())
  .set('date_utc', '2020-02-23')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200223')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed23,
  description: 'glorys_current_20200223_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200223_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed24 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200224'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-24').millis())
  .set('date_utc', '2020-02-24')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200224')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed24,
  description: 'glorys_current_20200224_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200224_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed25 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200225'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-25').millis())
  .set('date_utc', '2020-02-25')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200225')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed25,
  description: 'glorys_current_20200225_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200225_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed26 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200226'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-26').millis())
  .set('date_utc', '2020-02-26')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200226')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed26,
  description: 'glorys_current_20200226_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200226_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed27 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200227'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-27').millis())
  .set('date_utc', '2020-02-27')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200227')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed27,
  description: 'glorys_current_20200227_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200227_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed28 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200228'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-28').millis())
  .set('date_utc', '2020-02-28')
  .set('source_asset', 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200228')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo')
  .set('product_id', 'GLOBAL_MULTIYEAR_PHY_001_030')
  .set('dataset_id', 'cmems_mod_glo_phy_my_0.083deg_P1D-m')
  .set('metadata_version', '202311')
  .set('dataset_part', 'default')
  .set('depth_m', 0.494025)
  .set('depth_units', 'm')
  .set('units', 'm s-1');

Export.image.toAsset({
  image: fixed28,
  description: 'glorys_current_20200228_fixed',
  assetId: 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200228_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: GRID_TRANSFORM,
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

print('Prepared 26 explicit corrected pilot export tasks.');
