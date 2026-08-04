/**
 * Read-only Python–GEE reference-point comparison and B1 pilot benchmark.
 *
 * The expected values are decoded NetCDF values at four valid native-grid
 * points for all 29 February 2020 timestamps. Run in the existing user-managed
 * Earth Engine Code Editor session. This script creates no exports or assets.
 */

var ASSET_ROOT = 'projects/ee-rahal13001/assets/glorys_current';
var AOI = ee.Geometry.Rectangle(
  [129.199367, -2.797902, 133.329067, 1.4928],
  'EPSG:4326',
  false
);
var GRID_TRANSFORM = [
  0.0833331298828125, 0, 129.12500518798828,
  0, -0.08333333180500911, 1.5416666659025045
];
var DATES = [
  '2020-02-01', '2020-02-02', '2020-02-03', '2020-02-04',
  '2020-02-05', '2020-02-06', '2020-02-07', '2020-02-08',
  '2020-02-09', '2020-02-10', '2020-02-11', '2020-02-12',
  '2020-02-13', '2020-02-14', '2020-02-15', '2020-02-16',
  '2020-02-17', '2020-02-18', '2020-02-19', '2020-02-20',
  '2020-02-21', '2020-02-22', '2020-02-23', '2020-02-24',
  '2020-02-25', '2020-02-26', '2020-02-27', '2020-02-28',
  '2020-02-29'
];

var PILOT = ee.ImageCollection.fromImages(DATES.map(function(date) {
  return ee.Image(ASSET_ROOT + '/glorys12v1_daily_surface_' +
    date.replace(/-/g, '') + '_fixed');
}));

var REFERENCE_ROWS = [
  {
    point_id: 'p1', lat: -1.5, lon: 130.0,
    uo: [0.175176244,0.161137730,0.189214759,0.224005859,0.243537705,0.311288796,0.197759941,0.231330302,0.218512528,0.203253273,0.236823633,0.267342143,0.229499191,0.150761437,0.148930326,0.179448836,0.203863643,0.239875484,0.221564379,0.178228095,0.159916990,0.191656239,0.140385143,0.158696249,0.148319956,0.114139225,0.158085879,0.180059206,0.206915495],
    vo: [-0.026856288,-0.026856288,-0.009155553,-0.008545183,0.026856288,0.096438490,0.067140721,0.029297769,-0.013428144,-0.016479995,0.015869625,0.029908139,0.003051851,-0.029908139,-0.039063692,-0.032959990,-0.032959990,-0.032349620,-0.055543687,-0.077517014,-0.078737755,-0.053712577,-0.053102206,-0.034180731,-0.015869625,-0.006103702,0.003662221,0.014038514,0.003051851]
  },
  {
    point_id: 'p2', lat: 0.0, lon: 131.0,
    uo: [0.195318460,0.322885830,0.292977691,0.397350993,0.466322824,0.421765801,0.310068056,0.193487350,0.192266610,0.233161413,0.305185094,0.282601397,0.189825129,0.241706595,0.195928831,0.310068056,0.349742118,0.375377666,0.385143589,0.423596911,0.379039887,0.479750969,0.417493209,0.398571733,0.390636921,0.385143589,0.459608753,0.468764305,0.403454695],
    vo: [-0.084231086,-0.084841456,-0.028077029,-0.050050356,-0.021362957,0.014038514,-0.020142216,-0.058595539,-0.100711081,-0.095217750,-0.071413312,-0.079348125,-0.016479995,-0.034791101,-0.048829615,-0.069582202,-0.050050356,-0.062257759,-0.063478500,-0.072023683,-0.040894803,-0.048829615,-0.036011841,-0.001220740,-0.012817774,-0.019531847,-0.074465163,-0.039063692,-0.060426649]
  },
  {
    point_id: 'p3', lat: 1.0, lon: 132.0,
    uo: [-0.020752586,-0.134281442,-0.222174749,-0.180669576,-0.145878475,-0.059205908,-0.079958495,-0.131229591,-0.064699240,-0.059205908,-0.087282937,-0.191656239,-0.200201422,-0.178228095,-0.206305124,-0.122074038,-0.108035523,-0.066530351,-0.053712577,-0.119022187,-0.126957000,-0.108645894,-0.089114048,-0.186162908,-0.237434004,-0.250862148,-0.139774773,0.006103702,-0.051881467],
    vo: [-0.177617725,-0.238044374,-0.112308115,-0.119632558,-0.081179236,-0.000610370,-0.004272591,0.042725913,-0.067751091,-0.147709586,-0.183721427,-0.158085879,0.057985168,-0.045777764,0.018311105,-0.051271096,-0.106204413,-0.095828120,-0.197149571,-0.153202917,-0.099490341,-0.081179236,-0.090334788,0.022583697,0.026856288,0.006714072,0.092776269,0.064699240,0.017700735]
  },
  {
    point_id: 'p4', lat: -2.25, lon: 133.0,
    uo: [0.021362957,-0.001220740,0.003662221,0.018921476,0.006103702,-0.010986664,-0.071413312,-0.045167394,0.002441481,0.008545183,0.019531847,0.024414808,-0.009765923,-0.045167394,-0.024414808,0.006714072,0.030518509,0.031128880,0.012207404,-0.009765923,0.002441481,0.013428144,-0.006714072,-0.034791101,-0.046388134,-0.035401471,-0.004272591,0.004272592,-0.026245919],
    vo: [0.033570360,-0.007324442,-0.004882962,0.013428144,0.014648885,-0.032349620,-0.092165899,-0.089114048,0.006714072,0.031739250,0.015869625,0.028687399,-0.023194067,-0.051271096,-0.049439985,0.006103702,0.032959990,0.017090366,0.006714072,-0.014038514,-0.012817774,-0.001220740,-0.019531847,-0.042115543,-0.065309611,-0.079958495,0.009155553,0.012207404,-0.015259255]
  }
];

var referenceFeatures = [];
REFERENCE_ROWS.forEach(function(row) {
  DATES.forEach(function(date, index) {
    referenceFeatures.push(ee.Feature(
      ee.Geometry.Point([row.lon, row.lat]),
      {
        point_id: row.point_id,
        date_utc: date,
        uo_expected: row.uo[index],
        vo_expected: row.vo[index]
      }
    ));
  });
});

var references = ee.FeatureCollection(referenceFeatures);
var comparisons = references.map(function(feature) {
  var date = ee.String(feature.get('date_utc'));
  var image = ee.Image(PILOT.filter(ee.Filter.eq('date_utc', date)).first());
  var observed = image.reduceRegion({
    reducer: ee.Reducer.first(),
    geometry: feature.geometry(),
    crs: 'EPSG:4326',
    crsTransform: GRID_TRANSFORM,
    maxPixels: 1e8
  });
  var uoValid = ee.Number(ee.Algorithms.If(observed.contains('uo'), 1, 0));
  var voValid = ee.Number(ee.Algorithms.If(observed.contains('vo'), 1, 0));
  var uoObserved = ee.Number(observed.get('uo', -9999));
  var voObserved = ee.Number(observed.get('vo', -9999));
  var uoExpected = ee.Number(feature.get('uo_expected'));
  var voExpected = ee.Number(feature.get('vo_expected'));
  return feature.set({
    uo_gee: uoObserved,
    vo_gee: voObserved,
    uo_valid: uoValid,
    vo_valid: voValid,
    uo_abs_error: uoObserved.subtract(uoExpected).abs(),
    vo_abs_error: voObserved.subtract(voExpected).abs()
  });
});

print('T2-reference comparison_count', comparisons.size());
print('T2-reference date_count', comparisons.aggregate_count_distinct('date_utc'));
print('T2-reference point_count', comparisons.aggregate_count_distinct('point_id'));
print('T2-reference expected_valid_count', comparisons.size());
print('T2-reference uo_valid_count', comparisons.aggregate_sum('uo_valid'));
print('T2-reference vo_valid_count', comparisons.aggregate_sum('vo_valid'));
print('T2-reference uo_mask_mismatch_count', comparisons.size().subtract(comparisons.aggregate_sum('uo_valid')));
print('T2-reference vo_mask_mismatch_count', comparisons.size().subtract(comparisons.aggregate_sum('vo_valid')));
print('T2-reference uo_max_abs_error', comparisons.aggregate_max('uo_abs_error'));
print('T2-reference vo_max_abs_error', comparisons.aggregate_max('vo_abs_error'));
print('T2-reference uo_mean_abs_error', comparisons.aggregate_mean('uo_abs_error'));
print('T2-reference vo_mean_abs_error', comparisons.aggregate_mean('vo_abs_error'));

var b1Stats = PILOT.map(function(image) {
  var speed = image.expression(
    'sqrt(uo * uo + vo * vo)',
    {uo: image.select('uo'), vo: image.select('vo')}
  ).rename('speed');
  var stats = image.addBands(speed).select(['uo', 'vo', 'speed']).reduceRegion({
    reducer: ee.Reducer.mean().combine({
      reducer2: ee.Reducer.count(),
      sharedInputs: true
    }),
    geometry: AOI,
    crs: 'EPSG:4326',
    crsTransform: GRID_TRANSFORM,
    maxPixels: 1e8,
    bestEffort: false
  });
  return ee.Feature(null, stats).set('date_utc', image.get('date_utc'));
});
print('B1 status', 'COMPLETED_WITHOUT_VISIBLE_ERROR');
print('B1 image_count', PILOT.size());
print('B1 result_count', b1Stats.size());
print('B1 uo_count_minmax', b1Stats.aggregate_min('uo_count'), b1Stats.aggregate_max('uo_count'));
print('B1 vo_count_minmax', b1Stats.aggregate_min('vo_count'), b1Stats.aggregate_max('vo_count'));
print('B1 speed_count_minmax', b1Stats.aggregate_min('speed_count'), b1Stats.aggregate_max('speed_count'));
print('B1 duration_seconds', 'NOT_REPORTED_BY_CODE_EDITOR');
print('B1 eecu', 'NOT_AVAILABLE_IN_CODE_EDITOR_OUTPUT');
