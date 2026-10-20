# Рис. 3.4 і 3.10 — карти перевірки трендів і SAR-класів (потрібен data/zone_former_water.npy з trend_check.py)
# Запуск з теки, де лежать data/ та figures/: python maps.py
import numpy as np, rasterio, matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
U = "data/rasters/"
M = {
    y: rasterio.open(f"data/rasters/classified_{y}.tif").read(1)
    for y in range(2021, 2026)
}
r = rasterio.open(U + "classified_2021.tif")
T = r.transform
h, w = r.shape
EXT = [T.c, T.c + T.a * w, T.f + T.e * h, T.f]
ASP = 1 / np.cos(np.deg2rad(46.79))
zone = np.load("data/zone_former_water.npy")

L = [
    [33.51831542968673, 46.83700485723852],
    [33.453770751952355, 46.82854927133564],
    [33.393345947264855, 46.78625138577996],
    [33.35901367187423, 46.77684733865729],
    [33.31232177734298, 46.764619621678555],
    [33.247777099608605, 46.77402580421145],
]
R = [
    [33.234044189452355, 46.779668725267484],
    [33.30682861328048, 46.76838229180926],
    [33.382359619139855, 46.78154956754381],
    [33.453770751952355, 46.83042840539449],
    [33.511448974608605, 46.840762468391965],
]
HES = (33.3705, 46.7790)
NK = (33.348, 46.7545)
fmt = FuncFormatter(
    lambda v, p: f"{v:.2f}".rstrip("0").rstrip(".").replace(".", ",") + "°"
)


def decorate(a, labels=True, arrow=True, small=False):
    a.set_xlim(EXT[0], EXT[1])
    a.set_ylim(EXT[2], EXT[3])
    a.set_aspect(ASP)
    for line in (L, R):
        xs, ys = zip(*line)
        a.plot(xs, ys, "--", color="k", lw=0.7)
    a.plot(*HES, marker="*", color="white", mec="k", ms=9 if not small else 7, zorder=5)
    a.plot(*NK, "o", color="k", ms=4, zorder=5)
    if labels:
        a.text(
            HES[0] + 0.004,
            HES[1] + 0.004,
            "Каховська ГЕС",
            fontsize=8,
            fontweight="bold",
            zorder=6,
        )
        a.text(
            NK[0] + 0.005,
            NK[1] - 0.006,
            "Нова Каховка",
            fontsize=8,
            fontweight="bold",
            zorder=6,
        )
        a.text(33.27, 46.872, "ПРАВИЙ БЕРЕГ", fontsize=8, color="#0b3a6b")
        a.text(33.27, 46.728, "ЛІВИЙ БЕРЕГ", fontsize=8, color="#7a2e0b")
    a.set_xticks([33.30, 33.35, 33.40, 33.45])
    a.set_yticks([46.70, 46.75, 46.80, 46.85])
    a.xaxis.set_major_formatter(fmt)
    a.yaxis.set_major_formatter(fmt)
    a.tick_params(labelsize=7)
    a.grid(color="grey", lw=0.3, alpha=0.6)
    # масштаб 5 км
    km_deg = 5 / (111.32 * np.cos(np.deg2rad(46.79)))
    x0, y0 = 33.262, 46.709
    from matplotlib.patches import Rectangle

    a.add_patch(
        Rectangle(
            (x0, y0 - 0.0012),
            km_deg / 2,
            0.0024,
            facecolor="k",
            edgecolor="k",
            lw=0.6,
            zorder=6,
        )
    )
    a.add_patch(
        Rectangle(
            (x0 + km_deg / 2, y0 - 0.0012),
            km_deg / 2,
            0.0024,
            facecolor="white",
            edgecolor="k",
            lw=0.6,
            zorder=6,
        )
    )
    a.text(x0 + km_deg / 2, y0 + 0.003, "5 км", ha="center", fontsize=7)
    if arrow:
        a.annotate(
            "N",
            xy=(33.476, 46.873),
            xytext=(33.476, 46.846),
            ha="center",
            fontsize=9,
            fontweight="bold",
            arrowprops=dict(arrowstyle="-|>", color="k", lw=1.2),
        )


# ---------- рис. 3.10: SAR, орбіта 65, повне вікно
S = rasterio.open("data/rasters/sar_flood_orbit65_full.tif").read(1)
cm = ListedColormap(["#f2f2f2", "#1f5aa6", "#e4572e", "#7fc8e0"])
fig, a = plt.subplots()
a.imshow(S, cmap=cm, vmin=0, vmax=3, extent=EXT, interpolation="nearest")
decorate(a)
a.legend(
    handles=[
        Patch(color="#1f5aa6", label="Стабільна вода"),
        Patch(color="#e4572e", label="Нове затоплення"),
        Patch(color="#7fc8e0", label="Вода лише до прориву"),
        Line2D([], [], ls="--", color="k", lw=0.7, label="Межі полігонів берегів"),
    ],
    loc="lower right",
    fontsize=8,
    framealpha=0.9,
)
fig.set_size_inches(1520 / 200, 1330 / 200)
fig.subplots_adjust(left=0.1, right=0.98, top=0.98, bottom=0.06)
fig.savefig("figures/image10.png", dpi=200)
plt.close(fig)

# ---------- рис. 3.4: перевірка трендів
nb = (M[2025] == 5) & (M[2021] != 5)
g2a = (M[2021] == 2) & (M[2025] == 1)
b25 = M[2025] == 4
panels = [
    (nb, "#d7191c", "а) Нова забудова 2025 р. (не була забудовою у 2021 р.)"),
    (g2a, "#e6a800", "б) Луки 2021 р. → агроугіддя 2025 р."),
    (b25, "#8c5a2b", "в) Відкритий ґрунт у 2025 р."),
]
fig, axs = plt.subplots(1, 3)
for i, (a, (m, col, title)) in enumerate(zip(axs, panels)):
    img = np.zeros(m.shape, np.uint8)
    img[zone] = 1
    img[m] = 2
    a.imshow(
        img,
        cmap=ListedColormap(["#ececec", "#c6dff5", col]),
        vmin=0,
        vmax=2,
        extent=EXT,
        interpolation="nearest",
    )
    decorate(a, labels=False, arrow=(i == 0), small=True)
    a.set_title(title, fontsize=9)
fig.legend(
    handles=[
        Patch(
            color="#c6dff5",
            label="Колишня водна зона (вода 2021–2022 рр. або SAR-вода до прориву)",
        ),
        Patch(color="#d7191c", label="а: нова забудова"),
        Patch(color="#e6a800", label="б: луки → агроугіддя"),
        Patch(color="#8c5a2b", label="в: відкритий ґрунт"),
    ],
    loc="lower center",
    ncol=4,
    fontsize=8,
    frameon=False,
)
fig.set_size_inches(2550 / 200, 951 / 200)
fig.subplots_adjust(left=0.035, right=0.995, top=0.93, bottom=0.12, wspace=0.12)
fig.savefig("figures/image4.png", dpi=200)
plt.close(fig)
print("ok")
