/**
 * Read-only runtime validation for the recreated canonical T6-006 assets.
 */

var SOURCE_ID =
  'projects/ee-rahal13001/assets/glorys_current/surface_0p494025m/daily_jfm_2015_2025/glorys12v1_d_20150101_d0p494025m';
var DERIVED_ID =
  'projects/ee-rahal13001/assets/glorys_current/derived/speed/glorys12v1_speed_20150101_d0p494025m';
var REGION = ee.Geometry.Rectangle(
  [122.95833587646484, -12.20833160460091,
   143.37475776672363, 4.291666656732559],
  'EPSG:4326',
  false
);
var reduceOptions = {
  geometry: REGION,
  scale: 9276.34002252204,
  maxPixels: 1e8,
  bestEffort: true
};

var source = ee.Image(SOURCE_ID);
var derived = ee.Image(DERIVED_ID);
var uo = source.select('uo');
var vo = source.select('vo');
var speed = derived.select('speed');
var expectedSpeed = uo.pow(2).add(vo.pow(2)).sqrt();
var overlap = uo.mask().and(vo.mask()).and(speed.mask());

print('T6-006 recreated | source asset', SOURCE_ID);
print('T6-006 recreated | derived asset', DERIVED_ID);
print('T6-006 recreated | source bands', source.bandNames());
print('T6-006 recreated | derived bands', derived.bandNames());
print('T6-006 recreated | time', {
  source_start: source.get('system:time_start'),
  source_end: source.get('system:time_end'),
  derived_start: derived.get('system:time_start'),
  derived_end: derived.get('system:time_end')
});
print('T6-006 recreated | grid', {
  source_crs: uo.projection().crs(),
  derived_crs: speed.projection().crs(),
  source_transform: uo.projection().transform(),
  derived_transform: speed.projection().transform(),
  scale_difference_m: uo.projection().nominalScale()
    .subtract(speed.projection().nominalScale())
});
print('T6-006 recreated | no unmasked -9999', {
  source: source.eq(-9999).updateMask(source.mask()).reduceRegion(
    Object.assign({reducer: ee.Reducer.max()}, reduceOptions)),
  derived: speed.eq(-9999).updateMask(speed.mask()).reduceRegion(
    Object.assign({reducer: ee.Reducer.max()}, reduceOptions))
});
print('T6-006 recreated | valid-mask mean', {
  source: uo.mask().and(vo.mask()).reduceRegion(
    Object.assign({reducer: ee.Reducer.mean()}, reduceOptions)),
  derived: speed.mask().reduceRegion(
    Object.assign({reducer: ee.Reducer.mean()}, reduceOptions))
});
print('T6-006 recreated | ranges', {
  source: source.reduceRegion(Object.assign({reducer: ee.Reducer.minMax()}, reduceOptions)),
  derived: speed.reduceRegion(Object.assign({reducer: ee.Reducer.minMax()}, reduceOptions))
});
print('T6-006 recreated | formula max absolute difference', speed
  .subtract(expectedSpeed).abs().updateMask(overlap).reduceRegion(
    Object.assign({reducer: ee.Reducer.max()}, reduceOptions)));

Map.centerObject(REGION, 3);
Map.addLayer(speed, {min: 0, max: 1.5,
  palette: ['081d58', '225ea8', '41b6c4', 'a1dab4', 'ffffcc']},
  'T6-006 recreated speed');
