/**
 * Read-only visual check for one corrected February 2020 asset.
 *
 * This script is intentionally separate from the validation scripts: validation
 * prints evidence to the Console, while this script adds display layers to the
 * Code Editor map. It does not export, upload, mutate, or authenticate.
 */

var ASSET_ID = 'projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200201_fixed';
var AOI = ee.Geometry.Rectangle(
  [129.199367, -2.797902, 133.329067, 1.492800],
  'EPSG:4326',
  false
);

var image = ee.Image(ASSET_ID);
var speed = image.expression(
  'sqrt(uo * uo + vo * vo)',
  {uo: image.select('uo'), vo: image.select('vo')}
).rename('speed');
var validMask = image.select('uo').mask().rename('valid_mask');

Map.centerObject(AOI, 6);
Map.setOptions('SATELLITE');
Map.addLayer(
  image.select('uo'),
  {min: -1, max: 1, palette: ['313695', '74add1', 'ffffbf', 'f46d43', 'a50026']},
  'uo (m s-1)'
);
Map.addLayer(
  image.select('vo'),
  {min: -1, max: 1, palette: ['313695', '74add1', 'ffffbf', 'f46d43', 'a50026']},
  'vo (m s-1)',
  false
);
Map.addLayer(
  speed,
  {min: 0, max: 1, palette: ['ffffff', '9ecae1', '3182bd', '08519c']},
  'speed (m s-1)',
  false
);
Map.addLayer(validMask, {min: 0, max: 1, palette: ['000000', '00ff00']}, 'valid mask', false);
Map.addLayer(AOI, {color: '00ffff'}, 'pilot AOI', true, 0.8);

print('Display asset', ASSET_ID);
print('Display bands', image.bandNames());
print('Display date', image.get('date_utc'));
print('Display depth_m', image.get('depth_m'));
print('Display units', image.get('units'));
