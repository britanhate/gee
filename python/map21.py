# Рис. 2.1 — карта території дослідження (потрібен geopandas==0.14.4 з вбудованим Natural Earth)
# Запуск з теки, де лежать data/ та figures/: python map21.py
import numpy as np, rasterio, matplotlib, warnings, geopandas as gpd

warnings.filterwarnings("ignore")
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch, Rectangle, Polygon as MPoly
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
r = rasterio.open("data/rasters/classified_2021.tif")
a = r.read(1)
T = r.transform
h, w = a.shape
EXT = [T.c, T.c + T.a * w, T.f + T.e * h, T.f]
ASP = 1 / np.cos(np.deg2rad(46.79))
base = np.zeros(a.shape, np.uint8)
base[a == 5] = 1
base[a == 0] = 2
Lp = [
    [33.51831542968673, 46.83700485723852],
    [33.453770751952355, 46.82854927133564],
    [33.393345947264855, 46.78625138577996],
    [33.35901367187423, 46.77684733865729],
    [33.31232177734298, 46.764619621678555],
    [33.247777099608605, 46.77402580421145],
    [33.22992431640548, 46.688368999996726],
    [33.55402099609298, 46.685542832916866],
]
Rp = [
    [33.514195556639855, 46.89427987551007],
    [33.22992431640548, 46.89240297499229],
    [33.234044189452355, 46.779668725267484],
    [33.30682861328048, 46.76838229180926],
    [33.382359619139855, 46.78154956754381],
    [33.453770751952355, 46.83042840539449],
    [33.511448974608605, 46.840762468391965],
]
fig = plt.figure()
fig.set_size_inches(2380 / 200, 1632 / 200)
ax = fig.add_axes([0.06, 0.07, 0.6, 0.9])
ax.imshow(
    base,
    cmap=ListedColormap(["#f4f1e8", "#b9b4ac", "#8fb9e3"]),
    vmin=0,
    vmax=2,
    extent=EXT,
    interpolation="nearest",
)
ax.add_patch(
    MPoly(Lp, closed=True, fc="#d9622b", alpha=0.07, ec="#d9622b", lw=1.6, ls="--")
)
ax.add_patch(
    MPoly(Rp, closed=True, fc="#2a7fc0", alpha=0.07, ec="#2a7fc0", lw=1.6, ls="--")
)
ax.set_xlim(EXT[0], EXT[1])
ax.set_ylim(EXT[2], EXT[3])
ax.set_aspect(ASP)
ax.plot(33.3705, 46.7790, marker="*", ms=15, color="#c00000", mec="k", zorder=6)
ax.text(33.375, 46.7745, "Каховська ГЕС", fontsize=9, fontweight="bold", zorder=7)
for n, (x, y), dx, dy in [
    ("Нова Каховка", (33.348, 46.7545), -0.012, -0.012),
    ("Берислав", (33.426, 46.845), 0.0, 0.004),
    ("Каховка", (33.478, 46.816), -0.034, -0.0015),
]:
    ax.plot(x, y, "o", ms=6, color="k", zorder=6)
    ax.text(x + dx, y + dy, n, fontsize=9.5, fontweight="bold", zorder=7)
ax.text(
    33.405,
    46.818,
    "Каховське водосховище\n(до червня 2023 р.)",
    fontsize=9,
    style="italic",
    color="#1f4e79",
    rotation=33,
    ha="center",
)
ax.text(
    33.268,
    46.785,
    "р. Дніпро",
    fontsize=9,
    style="italic",
    color="#1f4e79",
    rotation=-8,
)
ax.text(33.262, 46.865, "ПРАВИЙ БЕРЕГ", fontsize=10, color="#1f5f99", fontweight="bold")
ax.text(33.262, 46.722, "ЛІВИЙ БЕРЕГ", fontsize=10, color="#a0441b", fontweight="bold")
fmt = FuncFormatter(
    lambda v, p: f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",") + "°"
)
ax.set_xticks([33.30, 33.35, 33.40, 33.45])
ax.set_yticks([46.70, 46.75, 46.80, 46.85])
ax.xaxis.set_major_formatter(fmt)
ax.yaxis.set_major_formatter(fmt)
ax.tick_params(labelsize=8)
ax.grid(color="grey", lw=0.3, alpha=0.6)
kd = 5 / (111.32 * np.cos(np.deg2rad(46.79)))
x0, y0 = 33.262, 46.708
ax.add_patch(
    Rectangle((x0, y0 - 0.0012), kd / 2, 0.0024, fc="k", ec="k", lw=0.6, zorder=6)
)
ax.add_patch(
    Rectangle(
        (x0 + kd / 2, y0 - 0.0012), kd / 2, 0.0024, fc="white", ec="k", lw=0.6, zorder=6
    )
)
ax.text(x0, y0 + 0.003, "0", fontsize=8, ha="center")
ax.text(x0 + kd, y0 + 0.003, "5 км", fontsize=8, ha="center")
ax.annotate(
    "N",
    xy=(33.476, 46.874),
    xytext=(33.476, 46.848),
    ha="center",
    fontsize=11,
    fontweight="bold",
    arrowprops=dict(arrowstyle="-|>", color="k", lw=1.4),
)
# inset
world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
ia = fig.add_axes([0.69, 0.50, 0.30, 0.45])
world.plot(ax=ia, color="#e6e6e6", edgecolor="#aaaaaa", lw=0.5)
world[world.name == "Ukraine"].plot(ax=ia, color="#fdf2c8", edgecolor="#555555", lw=0.8)
ia.add_patch(Rectangle((33.25, 46.70), 0.24, 0.18, fc="none", ec="#c00000", lw=1.5))
ia.plot(33.37, 46.79, "s", ms=7, mfc="none", mec="#c00000", mew=1.8)
ia.annotate(
    "Територія\nдослідження",
    xy=(33.37, 46.6),
    xytext=(30.0, 45.2),
    fontsize=8,
    ha="center",
    arrowprops=dict(arrowstyle="-", color="#c00000", lw=0.8),
)
ia.text(31.2, 49.0, "УКРАЇНА", fontsize=9, fontweight="bold", ha="center", color="#555")
ia.set_xlim(21.5, 41)
ia.set_ylim(43.8, 53)
ia.set_aspect(1 / np.cos(np.deg2rad(48.5)))
ia.set_xticks([])
ia.set_yticks([])
for s in ia.spines.values():
    s.set_edgecolor("#777")
# legend
la = fig.add_axes([0.69, 0.07, 0.30, 0.38])
la.axis("off")
la.legend(
    handles=[
        Patch(fc="#8fb9e3", label="Водна поверхня (2021 р.)"),
        Patch(fc="#b9b4ac", label="Забудова (2021 р.)"),
        Patch(
            fc="#d9622b",
            alpha=0.25,
            ec="#d9622b",
            ls="--",
            label="Полігон лівого берега",
        ),
        Patch(
            fc="#2a7fc0",
            alpha=0.25,
            ec="#2a7fc0",
            ls="--",
            label="Полігон правого берега",
        ),
        Line2D(
            [],
            [],
            marker="*",
            ls="",
            ms=13,
            color="#c00000",
            mec="k",
            label="Каховська ГЕС",
        ),
        Line2D([], [], marker="o", ls="", ms=6, color="k", label="Населені пункти"),
    ],
    loc="upper left",
    fontsize=9.5,
    frameon=False,
    title="Умовні позначення",
    title_fontsize=10.5,
)
la.text(
    0.0,
    0.08,
    "Межі рисунка — межі території дослідження\n(33,25–33,49° сх. д., 46,70–46,88° пн. ш.).\nВодна поверхня й забудова — за класифікацією\n2021 р.; межі держав — Natural Earth.",
    fontsize=7.5,
    color="#444",
    transform=la.transAxes,
)
fig.savefig("figures/study_area.png", dpi=200)
