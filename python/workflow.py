# Рис. 2.2 — схема геоінформаційного моделювання
# Запуск з теки, де лежать data/ та figures/: python workflow.py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams.update({"font.family": "DejaVu Sans"})
fig, a = plt.subplots()
fig.set_size_inches(13, 7.5)
a.set_xlim(0, 13)
a.set_ylim(0, 7.5)
a.axis("off")
C = {
    "data": "#dbe8f6",
    "proc": "#fff2cc",
    "model": "#d9ead3",
    "res": "#f4cccc",
    "acc": "#e6e0f2",
}


def box(x, y, w, h, t, c, fs=8.8, bold=False):
    a.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.04,rounding_size=0.12",
            fc=C[c],
            ec="#555",
            lw=1,
        )
    )
    a.text(
        x + w / 2,
        y + h / 2,
        t,
        ha="center",
        va="center",
        fontsize=fs,
        fontweight="bold" if bold else "normal",
        wrap=True,
    )


def arr(x1, y1, x2, y2):
    a.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", color="#444", lw=1.2),
    )


for x, t in [
    (0.2, "Вихідні дані"),
    (2.85, "Підготовка даних"),
    (5.5, "Моделювання"),
    (8.15, "Аналіз змін"),
    (10.8, "Результати"),
]:
    a.text(x + 1.0, 7.2, t, ha="center", fontsize=11, fontweight="bold", color="#333")
box(0.2, 5.6, 2.0, 1.1, "Sentinel-2 SR\n(травень; червень–серпень\n2021–2025)", "data")
box(0.2, 4.3, 2.0, 1.1, "Sentinel-1 GRD\n(VV, VH; висхідний\nвиток)", "data")
box(0.2, 3.0, 2.0, 1.1, "ESA WorldCover 2021,\nDynamic World\n2021–2025", "data")
box(
    0.2,
    1.7,
    2.0,
    1.1,
    "MERIT Hydro (HAND),\nCopernicus DEM,\nS1 орбіта 65 (2023)",
    "data",
)
box(0.2, 0.4, 2.0, 1.1, "MODIS MCD64A1,\nFIRMS", "data")
box(
    2.85,
    5.0,
    2.0,
    1.7,
    "Маскування хмар (SCL),\nмедіанні композити,\n19 ознак: канали,\nNDVI, NDWI, NDMI,\nNBR, BSI, NDVI весни,\nVV, VH, VV−VH",
    "proc",
    8.8,
)
box(
    2.85,
    3.0,
    2.0,
    1.4,
    "Навчальні мітки:\nпороги ймовірності DW,\nлише однозначні\nпікселі; 500 точок/клас",
    "proc",
    8.8,
)
box(2.85, 1.7, 2.0, 1.1, "Маска HAND < 15 м,\nухил < 5°; поріг Оцу", "proc", 8.8)
box(2.85, 0.4, 2.0, 1.1, "Маски класів\nтого самого року", "proc", 8.8)
box(
    5.5,
    3.9,
    2.0,
    1.6,
    "Random Forest\n(100 дерев)\nокремо для\nкожного року;\nподіл 70 / 30",
    "model",
    9,
    True,
)
box(5.5, 1.7, 2.0, 1.1, "Детекція змін VV\n(−3 дБ), класи води", "model", 8.8)
box(5.5, 0.4, 2.0, 1.1, "Площа вигорання,\nдетекції, dNBR", "model", 8.8)
box(8.15, 5.3, 2.0, 1.4, "Площі класів\n(pixelArea),\nматриці переходів", "res", 8.8)
box(
    8.15, 3.6, 2.0, 1.4, "Порівняння\nлівого / правого\nберегів (з 2023 р.)", "res", 8.8
)
box(8.15, 1.7, 2.0, 1.1, "SAR-класи води\nза берегами", "res", 8.8)
box(8.15, 0.4, 2.0, 1.1, "Пірогенний чинник\nза берегами й класами", "res", 8.8)
box(
    10.8,
    4.6,
    2.0,
    2.1,
    "Карти земного\nпокриву 2021–2025,\nтаблиці площ\nі переходів,\nоцінка воєнного\nвпливу",
    "res",
    9,
    True,
)
box(
    10.8,
    1.4,
    2.0,
    2.6,
    "Оцінка точності:\n• контрольна\n  вибірка 30 %\n• незалежна\n  валідація\n  (Olofsson,\n  1050 точок,\n  WorldView-2/3)",
    "acc",
    8.8,
)
for y in (6.15, 4.85):
    arr(2.2, y, 2.85, 5.85)
arr(2.2, 3.55, 2.85, 3.7)
arr(2.2, 2.25, 2.85, 2.25)
arr(2.2, 0.95, 2.85, 0.95)
arr(4.85, 5.85, 5.5, 4.9)
arr(4.85, 3.7, 5.5, 4.4)
arr(4.85, 2.25, 5.5, 2.25)
arr(4.85, 0.95, 5.5, 0.95)
arr(7.5, 4.9, 8.15, 6.0)
arr(7.5, 4.5, 8.15, 4.3)
arr(7.5, 2.25, 8.15, 2.25)
arr(7.5, 0.95, 8.15, 0.95)
arr(7.5, 4.0, 10.8, 2.9)
arr(10.15, 6.0, 10.8, 5.9)
arr(10.15, 4.3, 10.8, 5.0)
arr(10.15, 2.25, 10.8, 4.7)
arr(10.15, 0.95, 10.8, 4.6)
fig.subplots_adjust(0.005, 0.005, 0.995, 0.995)
fig.set_size_inches(2600 / 200, 1500 / 200)
fig.savefig("figures/workflow.png", dpi=200)
