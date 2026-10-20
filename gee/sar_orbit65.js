// =====================================================================
// SAR-картування води навколо прориву Каховської ГЕС (06.06.2023)
// Лише відносна орбіта Sentinel-1 № 65: композити «до» і «після» з однакової
// геометрії зйомки. Маска рельєфу (HAND + ухил), поріг Оцу в зоні можливого
// затоплення, детекція змін «після − до», фільтр дрібних плям.
// Класи: 0 — фон, 1 — стабільна вода, 2 — нове затоплення, 3 — вода лише до прориву.
// =====================================================================

// ---------- 1. Параметри ----------
var aoi = ee.Geometry.Rectangle([33.25, 46.70, 33.49, 46.88]);

var ORBIT = 65;
var BEFORE = ['2023-05-20', '2023-06-06'];
var AFTER_WINDOWS = {
  full: ['2023-06-06', '2023-06-26'],
  peak: ['2023-06-07', '2023-06-14']
};
var HAND_MAX = 15;    // м; чутливість 10 / 15 / 20 перевірено — вплив до 0,1 км²
var SLOPE_MAX = 5;    // градуси
var DIFF_THR = -3;    // дБ: падіння VV, що вважається появою води
var MIN_PX = 20;      // мінімальний розмір плями, пікселів по 10 м
var EXPORT_FOLDER = 'Master_SAR';

// Полігони берегів (ті самі, що в основному скрипті)
var leftBank = ee.Geometry.Polygon([[
  [33.51831542968673, 46.83700485723852],
  [33.453770751952355, 46.82854927133564],
  [33.393345947264855, 46.78625138577996],
  [33.35901367187423, 46.77684733865729],
  [33.31232177734298, 46.764619621678555],
  [33.247777099608605, 46.77402580421145],
  [33.22992431640548, 46.688368999996726],
  [33.55402099609298, 46.685542832916866]
]]);
var rightBank = ee.Geometry.Polygon([[
  [33.514195556639855, 46.89427987551007],
  [33.22992431640548, 46.89240297499229],
  [33.234044189452355, 46.779668725267484],
  [33.30682861328048, 46.76838229180926],
  [33.382359619139855, 46.78154956754381],
  [33.453770751952355, 46.83042840539449],
  [33.511448974608605, 46.840762468391965]
]]);
// 0 — поза полігонами, 1 — лівий берег, 2 — правий берег
var bankCode = ee.Image(0)
  .paint(ee.FeatureCollection([ee.Feature(leftBank)]), 1)
  .paint(ee.FeatureCollection([ee.Feature(rightBank)]), 2)
  .rename('bank').clip(aoi);

// ---------- 2. Sentinel-1, орбіта 65 ----------
function s1Collection(range) {
  return ee.ImageCollection('COPERNICUS/S1_GRD')
    .filterBounds(aoi)
    .filterDate(range[0], range[1])
    .filter(ee.Filter.eq('instrumentMode', 'IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
    .filter(ee.Filter.eq('relativeOrbitNumber_start', ORBIT))
    .select('VV');
}
function composite(col) {
  return col.median().focal_median(50, 'circle', 'meters').clip(aoi);
}
function sceneDates(col) {
  return col.aggregate_array('system:time_start').map(function (t) {
    return ee.Date(t).format('YYYY-MM-dd HH:mm');
  });
}

var colBefore = s1Collection(BEFORE);
print('Орбіта ' + ORBIT + ', сцени ДО:', sceneDates(colBefore));
print('Орбіта ' + ORBIT + ', сцени ПІСЛЯ (повне вікно):', sceneDates(s1Collection(AFTER_WINDOWS.full)));
print('Орбіта ' + ORBIT + ', сцени ПІСЛЯ (пікове вікно):', sceneDates(s1Collection(AFTER_WINDOWS.peak)));
var before = composite(colBefore);

// ---------- 3. Маска рельєфу ----------
var hand = ee.Image('MERIT/Hydro/v1_0_1').select('hnd');
var dem = ee.ImageCollection('COPERNICUS/DEM/GLO30').filterBounds(aoi)
  .select('DEM').mosaic().setDefaultProjection('EPSG:4326', null, 30);
var slope = ee.Terrain.slope(dem);
var floodable = hand.lt(HAND_MAX).and(slope.lt(SLOPE_MAX)).clip(aoi);

// ---------- 4. Поріг Оцу лише в межах зони можливого затоплення ----------
function otsu(histogram) {
  var counts = ee.Array(ee.Dictionary(histogram).get('histogram'));
  var means = ee.Array(ee.Dictionary(histogram).get('bucketMeans'));
  var size = means.length().get([0]);
  var total = counts.reduce(ee.Reducer.sum(), [0]).get([0]);
  var sum = means.multiply(counts).reduce(ee.Reducer.sum(), [0]).get([0]);
  var mean = sum.divide(total);
  var bss = ee.List.sequence(1, ee.Number(size).subtract(1)).map(function (i) {
    var aCounts = counts.slice(0, 0, i);
    var aCount = aCounts.reduce(ee.Reducer.sum(), [0]).get([0]);
    var aMean = means.slice(0, 0, i).multiply(aCounts)
      .reduce(ee.Reducer.sum(), [0]).get([0]).divide(aCount);
    var bCount = total.subtract(aCount);
    var bMean = sum.subtract(aCount.multiply(aMean)).divide(bCount);
    return aCount.multiply(aMean.subtract(mean).pow(2))
      .add(bCount.multiply(bMean.subtract(mean).pow(2)));
  });
  return means.slice(0, 0, ee.Number(size).subtract(1)).sort(bss).get([-1]);
}
function threshold(img) {
  var h = img.updateMask(floodable).reduceRegion({
    reducer: ee.Reducer.histogram(255, 0.1),
    geometry: aoi,
    scale: 20,
    maxPixels: 1e10
  }).get('VV');
  return ee.Number(otsu(h));
}
function clean(mask) {
  var cc = mask.selfMask().connectedPixelCount(MIN_PX + 1, true);
  return mask.and(cc.gte(MIN_PX)).unmask(0);
}

var thrBefore = threshold(before);
var waterBefore = clean(before.lt(thrBefore).and(floodable));

// ---------- 5. Класи для кожного вікна «після» ----------
function floodClasses(key) {
  var after = composite(s1Collection(AFTER_WINDOWS[key]));
  var thrAfter = threshold(after);
  var waterAfter = clean(after.lt(thrAfter).and(floodable));
  var diff = after.subtract(before);
  var stable = waterBefore.and(waterAfter);
  var newFlood = clean(waterAfter.and(waterBefore.not()).and(diff.lt(DIFF_THR)));
  var onlyBefore = waterBefore.and(waterAfter.not());
  var cls = ee.Image(0)
    .where(onlyBefore, 3)
    .where(newFlood, 2)
    .where(stable, 1)
    .rename('cls').clip(aoi).toByte();
  return { cls: cls, diff: diff, thrAfter: thrAfter };
}

// Площі за класами й берегами, км²
function areaTable(cls, key) {
  var groups = ee.List(ee.Image.pixelArea().divide(1e6)
    .addBands(cls.multiply(10).add(bankCode).rename('code'))
    .reduceRegion({
      reducer: ee.Reducer.sum().group({ groupField: 1, groupName: 'code' }),
      geometry: aoi,
      scale: 10,
      maxPixels: 1e13
    }).get('groups'));
  return ee.FeatureCollection(groups.map(function (g) {
    g = ee.Dictionary(g);
    var code = ee.Number(g.get('code'));
    return ee.Feature(null, {
      orbit: ORBIT,
      after_window: key,
      hand_max: HAND_MAX,
      cls: code.divide(10).floor().int(),
      bank: code.mod(10).int(),
      area_km2: g.get('sum')
    });
  }));
}

var results = {};
var tables = [];
Object.keys(AFTER_WINDOWS).forEach(function (key) {
  var r = floodClasses(key);
  results[key] = r;
  print('Поріг Оцу ДО / ПІСЛЯ (' + key + '), дБ:', thrBefore, r.thrAfter);
  var t = areaTable(r.cls, key);
  tables.push(t);
  print('Площі, км² (' + key + '; cls: 1 стабільна, 2 нове затоплення, 3 лише до; bank: 0 поза, 1 лівий, 2 правий):', t);

  Export.image.toDrive({
    image: r.cls,
    description: 'sar_flood_orbit' + ORBIT + '_' + key,
    folder: EXPORT_FOLDER,
    region: aoi,
    scale: 10,
    crs: 'EPSG:4326',
    maxPixels: 1e13,
    fileFormat: 'GeoTIFF'
  });
});

print('Вода ДО прориву, км² (порівняти з RF 2022 ≈ 54,8):',
  ee.Image.pixelArea().divide(1e6).updateMask(waterBefore)
    .reduceRegion({ reducer: ee.Reducer.sum(), geometry: aoi, scale: 10, maxPixels: 1e13 }));

Export.table.toDrive({
  collection: ee.FeatureCollection(tables).flatten(),
  description: 'sar_orbit' + ORBIT + '_areas',
  folder: EXPORT_FOLDER,
  fileFormat: 'CSV'
});

// ---------- 6. Візуалізація ----------
Map.centerObject(aoi, 12);
Map.addLayer(floodable.selfMask(), { palette: ['#dddddd'] }, 'Зона можливого затоплення', false);
Map.addLayer(results.full.diff, { min: -8, max: 8, palette: ['#b2182b', 'white', '#2166ac'] }, 'VV після − до (повне)', false);
Map.addLayer(results.peak.cls.selfMask(), { min: 1, max: 3, palette: ['#1f5aa6', '#e4572e', '#7fc8e0'] }, 'Класи води (пікове)', false);
Map.addLayer(results.full.cls.selfMask(), { min: 1, max: 3, palette: ['#1f5aa6', '#e4572e', '#7fc8e0'] }, 'Класи води (повне)');
Map.addLayer(ee.FeatureCollection([ee.Feature(leftBank), ee.Feature(rightBank)]).style({ color: '000000', fillColor: '00000000', width: 1 }), {}, 'Межі берегів', false);
