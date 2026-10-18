"""
Експорт фрагментів знімків навколо точок валідації (Olofsson) для незалежної перевірки.

Запуск: ArcGIS Pro, вікно Python або Notebook у відкритому проєкті.

Підготовка проєкту перед запуском:
  1. Карта (MAP_NAME) у Web Mercator з двома шарами World Imagery Wayback:
     один із зйомкою якомога ближче до липня 2021, другий до липня 2025.
     WMTS: https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/WMTSCapabilities.xml
  2. Макет (LAYOUT_NAME) з однією КВАДРАТНОЮ рамкою цієї карти на весь аркуш,
     без легенди, підписів і масштабної лінійки (щоб на фрагменті не було зайвого).

Результат: OUT_DIR/<id>.png. На кожному фрагменті червоним контуром показано
10-метровий піксель Sentinel-2, клас якого треба визначити. Клас карти у фрагмент не потрапляє.
"""
import csv
import math
import os

import arcpy

# ---------------------------------------------------------------- налаштування
BLIND_CSV = r"C:\path\to\all_validation_points_blind.csv"
OUT_DIR = r"C:\path\to\chips"
MAP_NAME = "Map"
LAYOUT_NAME = "Chips"
WAYBACK_LAYERS = {
    2021: "World Imagery (Wayback 2021-xx-xx)",  # точна назва шару в Contents
    2025: "World Imagery (Wayback 2025-xx-xx)",
}
HALF_SIZE_M = 75  # половина сторони фрагмента: 75 м -> фрагмент 150 x 150 м
DPI = 150
PIXEL_DEG = 8.983152841195215e-5  # розмір пікселя сітки classified_*.tif (EPSG:4326)
LIMIT = None  # наприклад 20 для пробного запуску
# -----------------------------------------------------------------------------

WGS84 = arcpy.SpatialReference(4326)


def read_points(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    pts = [
        {"id": int(float(r["id"])), "year": int(float(r["year"])), "lon": float(r["lon"]), "lat": float(r["lat"])}
        for r in rows
    ]
    pts.sort(key=lambda p: p["id"])
    return pts[:LIMIT] if LIMIT else pts


def box(lon, lat, half_x, half_y):
    arr = arcpy.Array(
        [
            arcpy.Point(lon - half_x, lat - half_y),
            arcpy.Point(lon - half_x, lat + half_y),
            arcpy.Point(lon + half_x, lat + half_y),
            arcpy.Point(lon + half_x, lat - half_y),
            arcpy.Point(lon - half_x, lat - half_y),
        ]
    )
    return arcpy.Polygon(arr, WGS84)


def build_cells_layer(m, pts):
    """Контури пікселів, у яких лежать точки (точка = центр пікселя сітки)."""
    fc = os.path.join(arcpy.env.scratchGDB, "validation_cells")
    if arcpy.Exists(fc):
        arcpy.management.Delete(fc)
    arcpy.management.CreateFeatureclass(arcpy.env.scratchGDB, "validation_cells", "POLYGON", spatial_reference=WGS84)
    arcpy.management.AddField(fc, "pid", "LONG")
    with arcpy.da.InsertCursor(fc, ["SHAPE@", "pid"]) as cur:
        for p in pts:
            cur.insertRow([box(p["lon"], p["lat"], PIXEL_DEG / 2, PIXEL_DEG / 2), p["id"]])

    for old in m.listLayers("validation_cells"):
        m.removeLayer(old)
    lyr = m.addDataFromPath(fc)
    sym = lyr.symbology
    sym.renderer.symbol.color = {"RGB": [0, 0, 0, 0]}
    sym.renderer.symbol.outlineColor = {"RGB": [255, 0, 0, 100]}
    sym.renderer.symbol.outlineWidth = 2
    lyr.symbology = sym
    return lyr


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.listMaps(MAP_NAME)[0]
    lyt = aprx.listLayouts(LAYOUT_NAME)[0]
    mf = lyt.listElements("MAPFRAME_ELEMENT")[0]
    map_sr = m.spatialReference

    imagery = {y: m.listLayers(name)[0] for y, name in WAYBACK_LAYERS.items()}
    pts = read_points(BLIND_CSV)
    cells = build_cells_layer(m, pts)

    for i, p in enumerate(pts, 1):
        out = os.path.join(OUT_DIR, "{}.png".format(p["id"]))
        if os.path.exists(out):
            continue  # дозволяє продовжити перерваний експорт

        for y, lyr in imagery.items():
            lyr.visible = y == p["year"]
        cells.definitionQuery = "pid = {}".format(p["id"])

        # квадрат HALF_SIZE_M у метрах, переведений у градуси для цієї широти
        half_y = HALF_SIZE_M / 110574.0
        half_x = HALF_SIZE_M / (111320.0 * math.cos(math.radians(p["lat"])))
        mf.camera.setExtent(box(p["lon"], p["lat"], half_x, half_y).projectAs(map_sr).extent)

        lyt.exportToPNG(out, resolution=DPI)
        if i % 25 == 0:
            arcpy.AddMessage("{} / {}".format(i, len(pts)))

    cells.definitionQuery = ""
    arcpy.AddMessage("Готово: {} фрагментів у {}".format(len(pts), OUT_DIR))


main()
