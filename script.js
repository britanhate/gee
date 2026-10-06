/**
 * v6 запобігання зависанню (Concurrency & Memory Fix).
 */

// ---------------------------------------------------------------
// 1. ПАРАМЕТРИ ТА НАЛАШТУВАННЯ
// ---------------------------------------------------------------

var aoi = ee.Geometry.Rectangle([33.25, 46.7, 33.49, 46.88]);
Map.centerObject(aoi, 10);

var pointsPerClass = 500;
var numberOfTrees = 100; // Зменшено з 150 до 100 для прискорення навчання без втрати точності
var s1OrbitPass = "ASCENDING";

var classNames = [
  "Water",
  "Agriculture",
  "Grassland",
  "Shrub / Tree",
  "Bare / Sparse",
  "Built-up",
  "Wetland / Pioneer",
];

var classificationVis = {
  min: 0,
  max: 6,
  palette: ["0000FF", "FFFF00", "00FF00", "006400", "D2B48C", "FF0000", "00FFFF"],
};

var waterThreshold = 0.6;
var agricultureThreshold = 0.6;
var grasslandThreshold = 0.3;
var shrubTreeThreshold = 0.6;
var bareThreshold = 0.2;
var builtThreshold = 0.6;
var wetlandThreshold = 0.5;

var years = [2021, 2022, 2023, 2024, 2025];

// Параметри SAR-картування прориву дамби
var BEFORE_WINDOW = ["2023-05-20", "2023-06-06"];
var AFTER_WINDOW = ["2023-06-06", "2023-06-26"];
var HAND_MAX = 15;''
var SLOPE_MAX = 5;
var DIFF_THR = -3;
var MIN_PX = 20;

// Ліво/право берегові полігони
var leftBank = ee.Geometry.Polygon([
  [
    [33.51831542968673, 46.83700485723852],
    [33.453770751952355, 46.82854927133564],
    [33.393345947264855, 46.78625138577996],
    [33.35901367187423, 46.77684733865729],
    [33.31232177734298, 46.764619621678555],
    [33.247777099608605, 46.77402580421145],
    [33.22992431640548, 46.688368999996726],
    [33.55402099609298, 46.685542832916866],
  ],
]);

var rightBank = ee.Geometry.Polygon([
  [
    [33.514195556639855, 46.89427987551007],
    [33.22992431640548, 46.89240297499229],
    [33.234044189452355, 46.779668725267484],
    [33.30682861328048, 46.76838229180926],
    [33.382359619139855, 46.78154956754381],
    [33.453770751952355, 46.83042840539449],
    [33.511448974608605, 46.840762468391965],
  ],
]);

Map.addLayer(leftBank, { color: "0b4a8b" }, "leftBank (окупований)", false);
Map.addLayer(rightBank, { color: "ffc82d" }, "rightBank (деокупований)", false);

// ---------------------------------------------------------------
// 2. ФУНКЦІЇ ПРЕПРОЦЕСИНГУ ТА ФОРМУВАННЯ ОЗНАК
// ---------------------------------------------------------------

function maskS2(image) {
  var scl = image.select("SCL");
  var mask = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return image.updateMask(mask).divide(10000).copyProperties(image, ["system:time_start"]);
}

function buildYearFeatures(year) {
  var springStart = year + "-05-01";
  var springEnd = year + "-06-01";
  var summerStart = year === 2023 ? "2023-07-01" : year + "-06-01";
  var summerEnd = year + "-09-01";

  var summerCollection = ee
    .ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(aoi)
    .filterDate(summerStart, summerEnd)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
    .map(maskS2);

  var summerComposite = summerCollection.median().clip(aoi);

  var springCollection = ee
    .ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(aoi)
    .filterDate(springStart, springEnd)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
    .map(maskS2);

  var springComposite = springCollection.median().clip(aoi);

  var ndviS = summerComposite.normalizedDifference(["B8", "B4"]).rename("NDVI_summer");
  var ndwiS = summerComposite.normalizedDifference(["B3", "B8"]).rename("NDWI_summer");
  var nbrS = summerComposite.normalizedDifference(["B8", "B12"]).rename("NBR_summer");
  var ndmiS = summerComposite.normalizedDifference(["B8", "B11"]).rename("NDMI_summer");
  var bsiS = summerComposite
    .expression("((SWIR + RED) - (NIR + BLUE)) / ((SWIR + RED) + (NIR + BLUE))", {
      SWIR: summerComposite.select("B11"),
      RED: summerComposite.select("B4"),
      NIR: summerComposite.select("B8"),
      BLUE: summerComposite.select("B2"),
    })
    .rename("BSI_summer");

  var ndviSpring = springComposite.normalizedDifference(["B8", "B4"]).rename("NDVI_spring");

  var s1Collection = ee
    .ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(aoi)
    .filterDate(summerStart, summerEnd)
    .filter(ee.Filter.eq("instrumentMode", "IW"))
    .filter(ee.Filter.eq("orbitProperties_pass", s1OrbitPass))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
    .select(["VV", "VH"]);

  var s1Composite = s1Collection.median().clip(aoi);
  var vv = s1Composite.select("VV").rename("VV_summer");
  var vh = s1Composite.select("VH").rename("VH_summer");
  var ratio = vv.subtract(vh).rename("VV_VH_ratio");

  var features = summerComposite
    .select(["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"])
    .addBands(ndviS)
    .addBands(ndwiS)
    .addBands(nbrS)
    .addBands(ndmiS)
    .addBands(bsiS)
    .addBands(ndviSpring)
    .addBands(vv)
    .addBands(vh)
    .addBands(ratio);

  return {
    features: features,
    summerComposite: summerComposite,
  };
}

// ---------------------------------------------------------------
// 3. НАВЧАЛЬНІ МІТКИ ТА ФІЛЬТРАЦІЯ
// ---------------------------------------------------------------

function buildTraining2021(features) {
  var worldCover = ee
    .ImageCollection("ESA/WorldCover/v200")
    .filterDate("2021-01-01", "2022-01-01")
    .first()
    .clip(aoi)
    .select("Map");

  var dw = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1").filterBounds(aoi).filterDate("2021-06-01", "2021-09-01");

  var dwProb = dw
    .select(["water", "trees", "grass", "flooded_vegetation", "crops", "shrub_and_scrub", "built", "bare"])
    .median()
    .clip(aoi);

  var wcClass = ee
    .Image(0)
    .where(worldCover.eq(80), 0)
    .where(worldCover.eq(40), 1)
    .where(worldCover.eq(30), 2)
    .where(worldCover.eq(90), 2)
    .where(worldCover.eq(10), 3)
    .where(worldCover.eq(20), 3)
    .where(worldCover.eq(60), 4)
    .where(worldCover.eq(50), 5)
    .rename("CLASS");

  return buildReliableTraining(wcClass, dwProb, features);
}

function buildTrainingDW(year, features) {
  var summerStart = year === 2023 ? "2023-07-01" : year + "-06-01";
  var summerEnd = year + "-09-01";

  var dw = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1").filterBounds(aoi).filterDate(summerStart, summerEnd);

  var dwProb = dw
    .select(["water", "trees", "grass", "flooded_vegetation", "crops", "shrub_and_scrub", "built", "bare"])
    .median()
    .clip(aoi);

  var dwLabelMode = dw.select("label").mode().clip(aoi);

  var dwClass = ee
    .Image(0)
    .where(dwLabelMode.eq(0), 0)
    .where(dwLabelMode.eq(4), 1)
    .where(dwLabelMode.eq(2), 2)
    .where(dwLabelMode.eq(1), 3)
    .where(dwLabelMode.eq(5), 3)
    .where(dwLabelMode.eq(7), 4)
    .where(dwLabelMode.eq(6), 5)
    .rename("CLASS");

  return buildReliableTraining(dwClass, dwProb, features);
}

function buildReliableTraining(baseClass, dwProb, features) {
  var waterProbability = dwProb.select("water");
  var agricultureProbability = dwProb.select("crops");
  var grassProbability = dwProb.select("grass").max(dwProb.select("flooded_vegetation"));
  var shrubTreeProbability = dwProb.select("trees").max(dwProb.select("shrub_and_scrub"));
  var bareProbability = dwProb.select("bare");
  var builtProbability = dwProb.select("built");
  var wetlandProbability = dwProb.select("flooded_vegetation");

  var waterMask = baseClass.eq(0).and(waterProbability.gte(waterThreshold));
  var agricultureMask = baseClass.eq(1).and(agricultureProbability.gte(agricultureThreshold));
  var grasslandMask = baseClass.eq(2).and(grassProbability.gte(grasslandThreshold));
  var shrubTreeMask = baseClass.eq(3).and(shrubTreeProbability.gte(shrubTreeThreshold));
  var bareMask = baseClass.eq(4).and(bareProbability.gte(bareThreshold));
  var builtMask = baseClass.eq(5).and(builtProbability.gte(builtThreshold));
  var wetlandMask = wetlandProbability.gte(wetlandThreshold).and(features.select("NDVI_summer").gt(0.25));

  var reliableTraining = ee
    .Image(0)
    .updateMask(
      waterMask.or(agricultureMask).or(grasslandMask).or(shrubTreeMask).or(bareMask).or(builtMask).or(wetlandMask),
    )
    .where(waterMask, 0)
    .where(agricultureMask, 1)
    .where(grasslandMask, 2)
    .where(shrubTreeMask, 3)
    .where(bareMask, 4)
    .where(builtMask, 5)
    .where(wetlandMask, 6)
    .rename("CLASS");

  var trainingPoints = reliableTraining.stratifiedSample({
    numPoints: pointsPerClass,
    classBand: "CLASS",
    region: aoi,
    scale: 10,
    geometries: true,
    seed: 42,
  });

  var trainingData = features.sampleRegions({
    collection: trainingPoints,
    properties: ["CLASS"],
    scale: 10,
    geometries: true,
  });

  return { points: trainingPoints, trainingData: trainingData };
}

// ---------------------------------------------------------------
// 4. КЛАСИФІКАЦІЯ ПО РОКАХ ТА ЗБІР ДАНИХ ПЛОЩ
// ---------------------------------------------------------------

var classifiedByYear = {};
var featuresByYear = {};
var allAreaRows = [];
var metricsRows = [];

years.forEach(function (year) {
  var yearData = buildYearFeatures(year);
  var features = yearData.features;
  featuresByYear[year] = features;

  var training = year === 2021 ? buildTraining2021(features) : buildTrainingDW(year, features);

  var rc = training.trainingData.randomColumn("random", 42);
  var trainSet = rc.filter(ee.Filter.lt("random", 0.7));
  var valSet = rc.filter(ee.Filter.gte("random", 0.7));

  var classifier = ee.Classifier.smileRandomForest({
    numberOfTrees: numberOfTrees,
    seed: 42,
  }).train({
    features: trainSet,
    classProperty: "CLASS",
    inputProperties: features.bandNames(),
  });

  // Замість print() відправляємо метрики точності в ледачі серверні Feature
  var valMatrix = valSet.classify(classifier).errorMatrix("CLASS", "classification");
  metricsRows.push(
    ee.Feature(null, {
      year: year,
      overall_accuracy: valMatrix.accuracy(),
      kappa: valMatrix.kappa(),
    }),
  );

  var classified = features.classify(classifier).clip(aoi);
  classifiedByYear[year] = classified;

  Map.addLayer(classified, classificationVis, "Classification " + year, year === 2021);

  var pixelArea = ee.Image.pixelArea();
  var areaByClass = ee.List.sequence(0, 6).map(function (classValue) {
    var mask = classified.eq(ee.Image.constant(classValue));
    var area = pixelArea
      .updateMask(mask)
      .reduceRegion({
        reducer: ee.Reducer.sum(),
        geometry: aoi,
        scale: 20,
        maxPixels: 1e13, // Збільшено scale до 20m для швидкості
      })
      .get("area");
    var areaNumber = ee.Number(ee.Algorithms.If(area, area, 0));
    return ee.Dictionary({ year: year, class: classValue, area_km2: areaNumber.divide(1000000) });
  });

  allAreaRows.push(areaByClass);

  Export.image.toDrive({
    image: classified,
    description: "classified_" + year,
    folder: "Master_Rasters",
    region: aoi,
    scale: 10,
    maxPixels: 1e13,
  });
});

// Експорт таблиці точностей (OA та Kappa)
Export.table.toDrive({
  collection: ee.FeatureCollection(metricsRows),
  description: "validation_accuracy_metrics",
  folder: "Master_Tables",
  fileFormat: "CSV",
});

Export.table.toDrive({
  collection: ee.FeatureCollection(
    ee
      .List(allAreaRows)
      .flatten()
      .map(function (d) {
        return ee.Feature(null, ee.Dictionary(d));
      }),
  ),
  description: "all_area_by_class_2021_2025",
  folder: "Master_Tables",
  fileFormat: "CSV",
});

// ---------------------------------------------------------------
// 5. МАТРИЦІ ПЕРЕХОДІВ КЛАСІВ
// ---------------------------------------------------------------

function transitionTable(fromImg, toImg) {
  var code = fromImg.toInt().multiply(10).add(toImg.toInt()).rename("code");
  var pixelArea = ee.Image.pixelArea().rename("area");

  var grouped = pixelArea.addBands(code).reduceRegion({
    reducer: ee.Reducer.sum().group({ groupField: 1, groupName: "code" }),
    geometry: aoi,
    scale: 20,
    maxPixels: 1e13, // scale: 20m підходить для підрахунку площ transition matrix
  });

  var groups = ee.List(grouped.get("groups"));

  var rows = groups.map(function (g) {
    g = ee.Dictionary(g);
    var codeNum = ee.Number(g.get("code"));
    var fromClass = codeNum.divide(10).floor();
    var toClass = codeNum.mod(10);
    var areaKm2 = ee.Number(g.get("sum")).divide(1000000);
    return ee.Feature(null, { from_class: fromClass, to_class: toClass, area_km2: areaKm2 });
  });

  return ee.FeatureCollection(rows);
}

var transitionPairs = [
  [2021, 2023],
  [2023, 2024],
  [2024, 2025],
  [2021, 2025],
];
var allTransitionTables = [];

transitionPairs.forEach(function (pair) {
  var table = transitionTable(classifiedByYear[pair[0]], classifiedByYear[pair[1]]).map(function (f) {
    return f.set({ from_year: pair[0], to_year: pair[1] });
  });
  allTransitionTables.push(table);
});

Export.table.toDrive({
  collection: ee.FeatureCollection(allTransitionTables).flatten(),
  description: "all_transitions_2021_2025",
  folder: "Master_Tables",
  fileFormat: "CSV",
});

// ---------------------------------------------------------------
// 6. SAR-КАРТУВАННЯ ВОДИ НАВКОЛО ПРОРИВУ ДАМБИ (06.06.2023)
// ---------------------------------------------------------------

function s1VvComposite(window) {
  var col = ee
    .ImageCollection("COPERNICUS/S1_GRD")
    .filterBounds(aoi)
    .filterDate(window[0], window[1])
    .filter(ee.Filter.eq("instrumentMode", "IW"))
    .filter(ee.Filter.eq("orbitProperties_pass", s1OrbitPass))
    .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
    .select("VV");

  return col.median().focal_median(50, "circle", "meters").clip(aoi);
}

function buildFloodableMask() {
  var hand = ee.Image("MERIT/Hydro/v1_0_1").select("hnd");
  var dem = ee
    .ImageCollection("COPERNICUS/DEM/GLO30")
    .filterBounds(aoi)
    .select("DEM")
    .mosaic()
    .setDefaultProjection("EPSG:4326", null, 30);
  var slope = ee.Terrain.slope(dem);
  return hand.lt(HAND_MAX).and(slope.lt(SLOPE_MAX)).clip(aoi);
}

function otsuThresholdMasked(image, regionMask) {
  var histogram = ee.Dictionary(
    image
      .updateMask(regionMask)
      .reduceRegion({
        reducer: ee.Reducer.histogram(255, 0.1),
        geometry: aoi,
        scale: 20,
        maxPixels: 1e10,
      })
      .get("VV"),
  );

  var counts = ee.Array(histogram.get("histogram"));
  var means = ee.Array(histogram.get("bucketMeans"));
  var size = means.length().get([0]);
  var total = counts.reduce(ee.Reducer.sum(), [0]).get([0]);
  var sum = means.multiply(counts).reduce(ee.Reducer.sum(), [0]).get([0]);
  var mean = sum.divide(total);

  var bss = ee.List.sequence(1, ee.Number(size).subtract(1)).map(function (i) {
    var aCounts = counts.slice(0, 0, i);
    var aCount = aCounts.reduce(ee.Reducer.sum(), [0]).get([0]);
    var aMean = means.slice(0, 0, i).multiply(aCounts).reduce(ee.Reducer.sum(), [0]).get([0]).divide(aCount);
    var bCount = total.subtract(aCount);
    var bMean = sum.subtract(aCount.multiply(aMean)).divide(bCount);
    return aCount.multiply(aMean.subtract(mean).pow(2)).add(bCount.multiply(bMean.subtract(mean).pow(2)));
  });

  return means.slice(0, 0, ee.Number(size).subtract(1)).sort(bss).get([-1]);
}

function cleanSmallBlobs(mask, minPixels) {
  var cc = mask.selfMask().connectedPixelCount(minPixels + 1, true);
  return mask.and(cc.gte(minPixels)).unmask(0);
}

var floodable = buildFloodableMask();
var vvBefore = s1VvComposite(BEFORE_WINDOW);
var vvAfter = s1VvComposite(AFTER_WINDOW);

var thresholdBefore = ee.Number(otsuThresholdMasked(vvBefore, floodable));
var thresholdAfter = ee.Number(otsuThresholdMasked(vvAfter, floodable));

var waterBefore = cleanSmallBlobs(vvBefore.lt(thresholdBefore).and(floodable), MIN_PX);
var waterAfter = cleanSmallBlobs(vvAfter.lt(thresholdAfter).and(floodable), MIN_PX);
var vvDiff = vvAfter.subtract(vvBefore);

var stableWater = waterBefore.and(waterAfter);
var newFlood = cleanSmallBlobs(waterAfter.and(waterBefore.not()).and(vvDiff.lt(DIFF_THR)), MIN_PX);
var waterOnlyBefore = waterBefore.and(waterAfter.not());

var floodClass = ee
  .Image(0)
  .where(waterOnlyBefore, 3)
  .where(newFlood, 2)
  .where(stableWater, 1)
  .rename("cls")
  .clip(aoi)
  .toByte();

Map.addLayer(floodClass.selfMask(), { min: 1, max: 3, palette: ["1f5aa6", "e4572e", "7fc8e0"] }, "SAR класи води");

Export.image.toDrive({
  image: floodClass,
  description: "sar_flood_hand_2023",
  folder: "Master_Rasters",
  region: aoi,
  scale: 10,
  maxPixels: 1e13,
});

// ---------------------------------------------------------------
// 7. ЛІВИЙ/ПРАВИЙ БЕРІГ + ВИГОРАННЯ (dNBR) + ПОЖЕЖІ (FIRMS)
// ---------------------------------------------------------------

var banks = { left: leftBank, right: rightBank };

function areaByClassInBank(classified, geometry, year, bankName) {
  var pixelArea = ee.Image.pixelArea();
  var rows = ee.List.sequence(0, 6).map(function (classValue) {
    var mask = classified.eq(ee.Image.constant(classValue));
    var area = pixelArea
      .updateMask(mask)
      .reduceRegion({
        reducer: ee.Reducer.sum(),
        geometry: geometry,
        scale: 20,
        maxPixels: 1e13,
      })
      .get("area");
    var areaNumber = ee.Number(ee.Algorithms.If(area, area, 0));
    return ee.Feature(null, {
      year: year,
      bank: bankName,
      class: classValue,
      area_km2: areaNumber.divide(1e6),
    });
  });
  return ee.FeatureCollection(rows);
}

var bankTables = [];
years.forEach(function (year) {
  Object.keys(banks).forEach(function (bankName) {
    bankTables.push(areaByClassInBank(classifiedByYear[year], banks[bankName], year, bankName));
  });
});

Export.table.toDrive({
  collection: ee.FeatureCollection(bankTables).flatten(),
  description: "area_by_bank_class_year",
  folder: "Master_Tables",
  fileFormat: "CSV",
});

var DNBR_THRESHOLD = 0.27;
var VEGETATED_CLASSES = [1, 2, 3];

function vegetatedInBothYears(year1, year2) {
  function isVegetated(classified) {
    return classified
      .eq(VEGETATED_CLASSES[0])
      .or(classified.eq(VEGETATED_CLASSES[1]))
      .or(classified.eq(VEGETATED_CLASSES[2]));
  }
  return isVegetated(classifiedByYear[year1]).and(isVegetated(classifiedByYear[year2]));
}

var nbrByYear = {};
years.forEach(function (year) {
  nbrByYear[year] = featuresByYear[year].select("NBR_summer");
});

var burnPairs = [
  [2021, 2022],
  [2022, 2023],
  [2023, 2024],
  [2024, 2025],
];
var burnRows = [];

burnPairs.forEach(function (pair) {
  var dnbr = nbrByYear[pair[0]].subtract(nbrByYear[pair[1]]).rename("dNBR");
  var vegMask = vegetatedInBothYears(pair[0], pair[1]);
  var burnMask = dnbr.gt(DNBR_THRESHOLD).and(vegMask);

  Object.keys(banks).forEach(function (bankName) {
    var area = ee.Image.pixelArea()
      .updateMask(burnMask)
      .reduceRegion({
        reducer: ee.Reducer.sum(),
        geometry: banks[bankName],
        scale: 20,
        maxPixels: 1e13,
      })
      .get("area");
    var areaNumber = ee.Number(ee.Algorithms.If(area, area, 0)).divide(1e6);
    burnRows.push(
      ee.Feature(null, {
        from_year: pair[0],
        to_year: pair[1],
        bank: bankName,
        burn_area_km2: areaNumber,
      }),
    );
  });
});

Export.table.toDrive({
  collection: ee.FeatureCollection(burnRows),
  description: "dnbr_burn_area_by_bank_v3",
  folder: "Master_Tables",
  fileFormat: "CSV",
});

var firms = ee.ImageCollection("FIRMS");
var firmsRows = [];

years.forEach(function (year) {
  var yearStart = year + "-01-01";
  var yearEnd = year + 1 + "-01-01";
  var fireCount = firms.filterDate(yearStart, yearEnd).filterBounds(aoi).select("T21").count().rename("fire_count");

  Object.keys(banks).forEach(function (bankName) {
    var stat = fireCount.reduceRegion({
      reducer: ee.Reducer.sum(),
      geometry: banks[bankName],
      scale: 1000,
      maxPixels: 1e13,
    });
    var count = ee.Number(ee.Algorithms.If(stat.get("fire_count"), stat.get("fire_count"), 0));
    firmsRows.push(ee.Feature(null, { year: year, bank: bankName, firms_index: count }));
  });
});

Export.table.toDrive({
  collection: ee.FeatureCollection(firmsRows),
  description: "firms_fire_index_by_bank",
  folder: "Master_Tables",
  fileFormat: "CSV",
});

// ---------------------------------------------------------------
// 8. ТОЧКИ ДЛЯ НЕЗАЛЕЖНОЇ OLOFSSON-ВАЛІДАЦІЇ
// ---------------------------------------------------------------

var validationYears = [2021, 2025];
var PER_CLASS = 75;

var allBlindPts = [];
var allKeyPts = [];

validationYears.forEach(function (yr) {
  var mapForValidation = classifiedByYear[yr];

  var pts = mapForValidation
    .stratifiedSample({
      numPoints: PER_CLASS,
      classBand: "classification",
      region: aoi,
      scale: 10,
      seed: 42 + yr,
      geometries: true,
      dropNulls: true,
    })
    .map(function (f) {
      var c = f.geometry().coordinates();
      return f.set({ lon: c.get(0), lat: c.get(1), ref: -1, year: yr });
    });

  allBlindPts.push(pts);
  allKeyPts.push(pts);
});

var combinedBlind = ee.FeatureCollection(allBlindPts).flatten();
var combinedKey = ee.FeatureCollection(allKeyPts).flatten();

Export.table.toDrive({
  collection: combinedBlind.select(["year", "lon", "lat", "ref"]),
  description: "all_validation_points_blind",
  folder: "Master_Validation",
  fileFormat: "CSV",
});

Export.table.toDrive({
  collection: combinedBlind.select(["year", "ref"]),
  description: "all_validation_points_map",
  folder: "Master_Validation",
  fileFormat: "KML",
});

Export.table.toDrive({
  collection: combinedKey,
  description: "all_validation_points_key",
  folder: "Master_Validation",
  fileFormat: "CSV",
});
