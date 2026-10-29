# Генерація 1050 точок незалежної валідації (Olofsson et al., 2014):
# стратифікована випадкова вибірка за класами фінальних карт 2021 і 2025 рр., 75 точок на клас, без NoData (255).
# Вихід: сліпий CSV, ключ і KML. Seed фіксовано — повторний запуск дає той самий набір.
import rasterio, numpy as np, pandas as pd

rng = np.random.default_rng(20261018)
rows = []
for y in [2021, 2025]:
    r = rasterio.open(f"data/rasters/classified_{y}.tif")
    a = r.read(1)
    for k in range(7):
        sel = rng.choice(np.flatnonzero(a.ravel() == k), 75, replace=False)
        rr, cc = np.unravel_index(sel, a.shape)
        xs, ys = rasterio.transform.xy(r.transform, rr, cc)
        rows += [(y, float(la), float(lo), k) for lo, la in zip(xs, ys)]
df = (
    pd.DataFrame(rows, columns=["year", "lat", "lon", "map"])
    .sample(frac=1, random_state=7)
    .reset_index(drop=True)
)
df["id"] = np.arange(1, len(df) + 1)
df["ref"] = -1
df[["id", "year", "lat", "lon", "ref"]].to_csv("validation_blind_v8.csv", index=False)
df[["id", "year", "map"]].to_csv("validation_key_v8.csv", index=False)
for y in [2021, 2025]:
    d = df[df.year == y].sort_values("id")
    pm = "".join(
        f"<Placemark><name>{i}</name><ExtendedData><Data name='year'><value>{y}</value></Data><Data name='ref'><value>-1</value></Data></ExtendedData><Point><coordinates>{lo:.7f},{la:.7f}</coordinates></Point></Placemark>\n"
        for i, la, lo in zip(d.id, d.lat, d.lon)
    )
    open(f"validation_blind_v8_{y}.kml", "w", encoding="utf8").write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Валідація {y}</name>\n{pm}</Document></kml>\n'
    )
print(len(df), "точок")
