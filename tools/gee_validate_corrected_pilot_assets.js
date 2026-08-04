/**
 * Full read-only validation for the 29 corrected February 2020 pilot assets.
 *
 * Run in the user-managed signed-in Earth Engine Code Editor after all
 * normalization export tasks complete. This script starts no export task.
 */

var AOI = ee.Geometry.Rectangle(
  [129.199367, -2.797902, 133.329067, 1.4928],
  'EPSG:4326',
  false
);

var pilot = ee.ImageCollection.fromImages([
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200201_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200202_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200203_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200204_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200205_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200206_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200207_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200208_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200209_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200210_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200211_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200212_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200213_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200214_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200215_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200216_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200217_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200218_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200219_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200220_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200221_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200222_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200223_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200224_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200225_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200226_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200227_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200228_fixed'),
  ee.Image('projects/ee-rahal13001/assets/glorys_current/glorys12v1_daily_surface_20200229_fixed')
]);

var pilotJfm = pilot.filterDate('2020-02-01', '2020-03-01');

print('T2-full asset_count', pilot.size());
print('T2-full filter_count_exclusive_end', pilotJfm.size());
print('T2-full date_utc', pilotJfm.aggregate_array('date_utc'));
print('T2-full date_min', pilotJfm.aggregate_min('date_utc'));
print('T2-full date_max', pilotJfm.aggregate_max('date_utc'));
print('T2-full time_start', pilotJfm.aggregate_array('system:time_start'));
print('T2-full time_start_min', pilotJfm.aggregate_min('system:time_start'));
print('T2-full time_start_max', pilotJfm.aggregate_max('system:time_start'));

var schema = pilotJfm.map(function(image) {
  return ee.Feature(null, {
    date_utc: image.get('date_utc'),
    bands: image.bandNames().join(','),
    time_start: image.get('system:time_start'),
    band_mapping: image.get('band_mapping'),
    source_asset: image.get('source_asset')
  });
});
print('T2-full schema', schema);
print('T2-full band_signature_histogram',
  schema.aggregate_array('bands').reduce(ee.Reducer.frequencyHistogram()));
print('T2-full band_mapping_histogram',
  schema.aggregate_array('band_mapping').reduce(ee.Reducer.frequencyHistogram()));
print('T2-full band_signature_keys',
  ee.Dictionary(schema.aggregate_array('bands').reduce(ee.Reducer.frequencyHistogram())).keys());
print('T2-full band_mapping_keys',
  ee.Dictionary(schema.aggregate_array('band_mapping').reduce(ee.Reducer.frequencyHistogram())).keys());

var withSpeed = pilotJfm.map(function(image) {
  var speed = image.expression(
    'sqrt(uo * uo + vo * vo)',
    {uo: image.select('uo'), vo: image.select('vo')}
  ).rename('speed');
  return image.addBands(speed);
});

var combinedReducer = ee.Reducer.mean().combine({
  reducer2: ee.Reducer.count(),
  sharedInputs: true
});

var aoiStats = withSpeed.map(function(image) {
  var stats = image.select(['uo', 'vo', 'speed']).reduceRegion({
    reducer: combinedReducer,
    geometry: AOI,
    scale: 10000,
    maxPixels: 1e8,
    bestEffort: true
  });
  return ee.Feature(null, stats).set('date_utc', image.get('date_utc'));
});
print('T2-full aoi_stats_mean_count', aoiStats);
print('T2-full aoi_stats_dates', aoiStats.aggregate_array('date_utc'));
print('T2-full aoi_uo_mean', aoiStats.aggregate_array('uo_mean'));
print('T2-full aoi_vo_mean', aoiStats.aggregate_array('vo_mean'));
print('T2-full aoi_speed_mean', aoiStats.aggregate_array('speed_mean'));
print('T2-full aoi_uo_count', aoiStats.aggregate_array('uo_count'));
print('T2-full aoi_vo_count', aoiStats.aggregate_array('vo_count'));
print('T2-full aoi_speed_count', aoiStats.aggregate_array('speed_count'));
print('T2-full aoi_uo_count_minmax',
  aoiStats.aggregate_min('uo_count'), aoiStats.aggregate_max('uo_count'));
print('T2-full aoi_vo_count_minmax',
  aoiStats.aggregate_min('vo_count'), aoiStats.aggregate_max('vo_count'));
print('T2-full aoi_speed_count_minmax',
  aoiStats.aggregate_min('speed_count'), aoiStats.aggregate_max('speed_count'));

function bearingToward(u, v) {
  return ee.Number(v).atan2(ee.Number(u))
    .multiply(180 / Math.PI)
    .add(360)
    .mod(360);
}

var cardinalTest = ee.FeatureCollection([
  ee.Feature(null, {name: 'north', expected: 0, observed: bearingToward(0, 1)}),
  ee.Feature(null, {name: 'east', expected: 90, observed: bearingToward(1, 0)}),
  ee.Feature(null, {name: 'south', expected: 180, observed: bearingToward(0, -1)}),
  ee.Feature(null, {name: 'west', expected: 270, observed: bearingToward(-1, 0)})
]);
print('T2-full expected_bearing', cardinalTest.aggregate_array('expected'));
print('T2-full observed_bearing', cardinalTest.aggregate_array('observed'));
