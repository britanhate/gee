/**
 * Експорт знімків для СЛІПОЇ розмітки еталона (Olofsson) за 2021 і 2025 рр.
 * Жодної класифікації на знімках немає — лише Sentinel-2.
 *
 * Для кожного року — 4 растри (сітка 10 м, збігається з classified_YYYY.tif):
 *   1) s2_rgb_summer_YYYY   — true color, червень–серпень (те саме вікно, що й у класифікації)
 *   2) s2_swir_summer_YYYY  — false color B11/B8/B4 (вода, голий ґрунт, забудова, рослинність)
 *   3) s2_rgb_may_YYYY      — true color, травень (фенологія: озимі/ярі, трава)
 *   4) s2_ndvi_monthly_YYYY — NDVI за місяцями травень–вересень, 5 каналів, int16 ×10000, NoData = -9999
 * Усього 8 експортів у Drive/Master_Reference.
 */

var aoi = ee.Geometry.Rectangle([33.25, 46.7, 33.49, 46.88]);
var years = [2021, 2025];

// Та сама сітка, що й у ваших classified_*.tif (EPSG:4326, ~10 м)
var CRS = "EPSG:4326";
var TRANSFORM = [8.983152841195215e-5, 0, 33.24997243181473, 0, -8.983152841195215e-5, 46.880110237760235];

function maskS2(image) {
  var scl = image.select("SCL");
  var mask = scl.neq(3).and(scl.neq(8)).and(scl.neq(9)).and(scl.neq(10)).and(scl.neq(11));
  return image.updateMask(mask).divide(10000).copyProperties(image, ["system:time_start"]);
}

function composite(start, end) {
  return ee
    .ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(aoi)
    .filterDate(start, end)
    .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
    .map(maskS2)
    .median()
    .clip(aoi);
}

function exportVis(img, vis, name) {
  Export.image.toDrive({
    image: img.visualize(vis).unmask(0).toByte(), // 0 = немає даних (чорний)
    description: name,
    folder: "Master_Reference",
    region: aoi,
    crs: CRS,
    crsTransform: TRANSFORM,
    maxPixels: 1e13,
  });
}

years.forEach(function (y) {
  var summer = composite(y + "-06-01", y + "-09-01");
  var may = composite(y + "-05-01", y + "-06-01");

  exportVis(summer, { bands: ["B4", "B3", "B2"], min: 0.0, max: 0.3, gamma: 1.2 }, "s2_rgb_summer_" + y);
  exportVis(summer, { bands: ["B11", "B8", "B4"], min: 0.0, max: 0.5, gamma: 1.2 }, "s2_swir_summer_" + y);
  exportVis(may, { bands: ["B4", "B3", "B2"], min: 0.0, max: 0.3, gamma: 1.2 }, "s2_rgb_may_" + y);

  // Місячні NDVI: травень … вересень
  var months = [
    [y + "-05-01", y + "-06-01"],
    [y + "-06-01", y + "-07-01"],
    [y + "-07-01", y + "-08-01"],
    [y + "-08-01", y + "-09-01"],
    [y + "-09-01", y + "-10-01"],
  ];
  var stack = ee.Image.cat(
    months.map(function (m, i) {
      return composite(m[0], m[1])
        .normalizedDifference(["B8", "B4"])
        .rename("NDVI_m" + (i + 5));
    }),
  );
  Export.image.toDrive({
    image: stack.multiply(10000).unmask(-9999).toInt16(),
    description: "s2_ndvi_monthly_" + y,
    folder: "Master_Reference",
    region: aoi,
    crs: CRS,
    crsTransform: TRANSFORM,
    maxPixels: 1e13,
  });
});
