# Рис. 3.1 — карти земного покриву 2021–2025 з NoData сірим
# Запуск з теки, де лежать data/ та figures/: python map31.py
import numpy as np, rasterio, matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

exec(open("maps.py", encoding="utf8").read().split("# ---------- рис. 3.10")[0])
COL = [
    "#2060c0",
    "#f0d84a",
    "#7fdb5a",
    "#1a6b30",
    "#c8a07a",
    "#e04030",
    "#30c8c8",
    "#9e9e9e",
]
NAMES = [
    "Вода",
    "Сільськогосподарські угіддя",
    "Лучна рослинність",
    "Чагарники / дерева",
    "Відкритий ґрунт / розріджена рослинність",
    "Забудова",
    "Водно-болотна / піонерна рослинність",
    "Немає даних",
]
cm = ListedColormap(COL)
fig, axs = plt.subplots(2, 3)
for i, y in enumerate(range(2021, 2026)):
    a = axs.flat[i]
    img = M[y].copy()
    nod = rasterio.open(f"data/rasters/classified_{y}.tif").read(1) == 255
    img[nod] = 7
    a.imshow(img, cmap=cm, vmin=0, vmax=7, extent=EXT, interpolation="nearest")
    decorate(a, labels=(i == 0), arrow=(i == 0), small=True)
    a.set_title(str(y), fontweight="bold")
ax = axs.flat[5]
ax.axis("off")
h = [Patch(color=c, label=n) for c, n in zip(COL, NAMES)] + [
    Line2D(
        [], [], marker="*", ls="", color="white", mec="k", ms=10, label="Каховська ГЕС"
    ),
    Line2D([], [], marker="o", ls="", color="k", ms=5, label="Нова Каховка"),
    Line2D([], [], ls="--", color="k", lw=0.8, label="Межі полігонів берегів"),
]
ax.legend(handles=h, loc="center", fontsize=9, frameon=False, title="Умовні позначення")
fig.set_size_inches(2380 / 200, 1632 / 200)
fig.subplots_adjust(
    left=0.04, right=0.995, top=0.96, bottom=0.04, wspace=0.12, hspace=0.14
)
fig.savefig("figures/image1.png", dpi=200)
