/**
 * Export the three corrected February 2020 pilot assets in Earth Engine.
 *
 * Run this file by pasting it into the Earth Engine Code Editor after the
 * source pilot assets exist under the configured asset root. The literal
 * task descriptions and asset IDs are intentional: Earth Engine Code Editor
 * can mis-handle task fields generated through client-side loops or string
 * concatenation.
 *
 * Source assets:
 *   projects/ee-rahal13001/assets/glorys_current/
 *
 * Output assets:
 *   .../glorys12v1_daily_surface_20200201_fixed
 *   .../glorys12v1_daily_surface_20200215_fixed
 *   .../glorys12v1_daily_surface_20200229_fixed
 *
 * After Run, open Tasks, review all three task forms, and submit them with
 * Run all. Refresh the Assets panel after completion. Do not rerun this file
 * against an existing target asset unless the target is intentionally changed.
 * Authentication and task submission remain user-managed in the Code Editor.
 */

var AOI = ee.Geometry.Rectangle(
  [129.12500518798828, -2.874999919762978,
   133.3749948120117, 1.5416666659025045],
  'EPSG:4326',
  false
);

var fixed01 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200201'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-01').millis())
  .set('date_utc', '2020-02-01')
  .set('source_asset',
    'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200201')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo');

Export.image.toAsset({
  image: fixed01,
  description: 'glorys_current_20200201_fixed',
  assetId:
    'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200201_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: [
    0.0833331298828125, 0, 129.12500518798828,
    0, -0.08333333180500911, 1.5416666659025045
  ],
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed15 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200215'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-15').millis())
  .set('date_utc', '2020-02-15')
  .set('source_asset',
    'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200215')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo');

Export.image.toAsset({
  image: fixed15,
  description: 'glorys_current_20200215_fixed',
  assetId:
    'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200215_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: [
    0.0833331298828125, 0, 129.12500518798828,
    0, -0.08333333180500911, 1.5416666659025045
  ],
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

var fixed29 = ee.Image(
  'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200229'
)
  .select(['b1', 'b2'], ['uo', 'vo'])
  .set('system:time_start', ee.Date('2020-02-29').millis())
  .set('date_utc', '2020-02-29')
  .set('source_asset',
    'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200229')
  .set('nodata_value', -9999)
  .set('band_mapping', 'b1->uo,b2->vo');

Export.image.toAsset({
  image: fixed29,
  description: 'glorys_current_20200229_fixed',
  assetId:
    'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200229_fixed',
  region: AOI,
  crs: 'EPSG:4326',
  crsTransform: [
    0.0833331298828125, 0, 129.12500518798828,
    0, -0.08333333180500911, 1.5416666659025045
  ],
  maxPixels: 1e8,
  pyramidingPolicy: {'.default': 'MEAN'}
});

print('Prepared three explicit corrected pilot export tasks.');
