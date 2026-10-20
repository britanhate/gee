# П. 3.3.1 — перевірка трендів за растрами 10 м та колишня водна зона.
# Вхід: data/rasters/classified_2021…2025.tif, data/rasters/sar_flood_orbit65_full.tif
# Вихід: друк показників і data/zone_former_water.npy (для maps.py)
import rasterio, numpy as np

M = {
    y: rasterio.open(f"data/rasters/classified_{y}.tif").read(1)
    for y in range(2021, 2026)
}
S = rasterio.open("data/rasters/sar_flood_orbit65_full.tif").read(1)
r = rasterio.open("data/rasters/classified_2021.tif")
T = r.transform
h, w = r.shape
lat = T.f + T.e * (np.arange(h) + 0.5)
R = 6371008.8
d = np.deg2rad(T.a)
rowA = (
    R**2
    * d
    * np.abs(np.sin(np.deg2rad(lat + T.e / 2)) - np.sin(np.deg2rad(lat - T.e / 2)))
) / 1e6  # км² пікселя за рядком
PA = np.repeat(rowA[:, None], w, axis=1)
km = lambda m: PA[m].sum()
# колишня водна зона: вода 2021 або 2022 р. або SAR «стабільна вода» / «вода лише до прориву»
zone = (M[2021] == 0) | (M[2022] == 0) | (S == 1) | (S == 3)
np.save("data/zone_former_water.npy", zone)
print("Колишня водна зона, км²:", round(km(zone), 2))
b21, b25 = M[2021] == 5, M[2025] == 5
nb = b25 & ~b21
print(
    "Нова / втрачена / чистий приріст забудови:",
    round(km(nb), 2),
    round(km(b21 & ~b25), 2),
    round(km(b25) - km(b21), 2),
)
print(
    "Забудова в усіх роках / в об’єднанні:",
    round(km(np.logical_and.reduce([M[y] == 5 for y in M])), 2),
    round(km(np.logical_or.reduce([M[y] == 5 for y in M])), 2),
)
print(
    "Походження нової забудови за класами 2021 р.:",
    [round(km(nb & (M[2021] == k)), 2) for k in range(7)],
)
print("Нова забудова в колишній водній зоні:", round(km(nb & zone), 2))
g = (M[2021] == 2) & (M[2025] == 1)
print(
    "Луки 2021 → агроугіддя 2025; з них рілля у 2022 / 2024:",
    round(km(g), 2),
    round(km(g & (M[2022] == 1)), 2),
    round(km(g & (M[2024] == 1)), 2),
)
b = M[2025] == 4
print(
    "Відкритий ґрунт 2025: усього / у зоні / був водою у 2021:",
    round(km(b), 2),
    round(km(b & zone), 2),
    round(km(b & (M[2021] == 0)), 2),
)
