/**
 * Read-only runtime validation for the corrected T6-006 sample assets.
 */

var SOURCE_ID =
  'projects/ee-rahal13001/assets/glorys_current/surface_0p494025m/daily_jfm_2015_2025/glorys12v1_d_20150101_d0p494025m_fixed';
var DERIVED_ID =
  'projects/ee-rahal13001/assets/glorys_current/derived/speed/glorys12v1_speed_20150101_d0p494025m_fixed';
var REGION = ee.Geometry.Rectangle(
  [122.95833587646484, -12.20833160460091,
   143.37475776672363, 4.291666656732559],
  'EPSG:4326',
  false
);

var source = ee.Image(SOURCE_ID);
var derived = ee.Image(DERIVED_ID);
var uo = source.select('uo');
var vo = source.select('vo');
var speed = derived.select('speed');
var expectedSpeed = uo.pow(2).add(vo.pow(2)).sqrt();
var overlap = uo.mask().and(vo.mask()).and(speed.mask());
var reduceOptions = {
  geometry: REGION,
  scale: 9276.34002252204,
  maxPixels: 1e8,
  bestEffort: true
};

print('T6-006 corrected | source asset', SOURCE_ID);
print('T6-006 corrected | derived asset', DERIVED_ID);
print('T6-006 corrected | source bands', source.bandNames());
print('T6-006 corrected | derived bands', derived.bandNames());
print('T6-006 corrected | source time', {
  start: source.get('system:time_start'), end: source.get('system:time_end')
});
print('T6-006 corrected | derived time', {
  start: derived.get('system:time_start'), end: derived.get('system:time_end')
});
print('T6-006 corrected | time equality', {
  start_equal: ee.Algorithms.IsEqual(source.get('system:time_start'), derived.get('system:time_start')),
  end_equal: ee.Algorithms.IsEqual(source.get('system:time_end'), derived.get('system:time_end'))
});
print('T6-006 corrected | source projection', {
  crs: uo.projection().crs(),
  transform: uo.projection().transform(),
  nominal_scale_m: uo.projection().nominalScale()
});
print('T6-006 corrected | derived projection', {
  crs: speed.projection().crs(),
  transform: speed.projection().transform(),
  nominal_scale_m: speed.projection().nominalScale()
});
print('T6-006 corrected | grid equality', {
  crs_equal: ee.Algorithms.IsEqual(uo.projection().crs(), speed.projection().crs()),
  transform_equal: ee.Algorithms.IsEqual(uo.projection().transform(), speed.projection().transform()),
  nominal_scale_difference_m: uo.projection().nominalScale().subtract(speed.projection().nominalScale())
});
print('T6-006 corrected | source band metadata', source.get('system:bands'));
print('T6-006 corrected | derived band metadata', derived.get('system:bands'));
print('T6-006 corrected | source unmasked -9999', source.eq(-9999).updateMask(source.mask()).reduceRegion(
  Object.assign({reducer: ee.Reducer.max()}, reduceOptions)));
print('T6-006 corrected | derived unmasked -9999', speed.eq(-9999).updateMask(speed.mask()).reduceRegion(
  Object.assign({reducer: ee.Reducer.max()}, reduceOptions)));
print('T6-006 corrected | source valid-mask mean', uo.mask().and(vo.mask()).reduceRegion(
  Object.assign({reducer: ee.Reducer.mean()}, reduceOptions)));
print('T6-006 corrected | derived valid-mask mean', speed.mask().reduceRegion(
  Object.assign({reducer: ee.Reducer.mean()}, reduceOptions)));
print('T6-006 corrected | source value range', source.reduceRegion(
  Object.assign({reducer: ee.Reducer.minMax()}, reduceOptions)));
print('T6-006 corrected | derived value range', speed.reduceRegion(
  Object.assign({reducer: ee.Reducer.minMax()}, reduceOptions)));
print('T6-006 corrected | formula max absolute difference', speed.subtract(expectedSpeed)
  .abs().updateMask(overlap).reduceRegion(
    Object.assign({reducer: ee.Reducer.max()}, reduceOptions)));

Map.centerObject(REGION, 3);
Map.addLayer(speed, {min: 0, max: 1.5, palette: ['081d58', '225ea8', '41b6c4', 'a1dab4', 'ffffcc']},
  'T6-006 corrected speed');
