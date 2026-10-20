# Рис. 3.2, 3.3, 3.5–3.9 — діаграми з CSV-таблиць GEE (data/tables)
# Запуск з теки, де лежать data/ та figures/: python charts.py
import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.ticker import FuncFormatter

D = 'data/tables/'
OUT = 'figures/'
import os; os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
DPI = 200
def c(v, n=1):
    return f'{v:.{n}f}'.replace('.', ',').replace('-', '−')
CF = FuncFormatter(lambda v, p: (f'{v:g}').replace('.', ',').replace('-', '−'))

NAMES = ['Вода', 'Сільськогосподарські угіддя', 'Лучна рослинність', 'Чагарники / дерева',
         'Відкритий ґрунт / розріджена рослинність', 'Забудова', 'Водно-болотна / піонерна рослинність']
SHORT = ['Вода', 'Агроугіддя', 'Луки', 'Чагарники / дерева', 'Відкритий ґрунт', 'Забудова', 'Водно-болотна / піонерна']
COL = ['#2060c0', '#f0d84a', '#7fdb5a', '#1a6b30', '#c8a07a', '#e04030', '#30c8c8']
YEARS = [2021, 2022, 2023, 2024, 2025]
LC, RC = '#d9622b', '#2a7fc0'

area = pd.read_csv(D + 'all_area_by_class_2021_2025.csv')
A = area.pivot_table(index='class', columns='year', values='area_km2')
A.index = A.index.astype(int)
bank = pd.read_csv(D + 'area_by_bank_class_year.csv')
B = bank.pivot_table(index='class', columns=['year', 'bank'], values='area_km2'); B.index = B.index.astype(int)
tr = pd.read_csv(D + 'all_transitions_2021_2025.csv')
tr['from_class'] = tr.from_class.astype(int); tr['to_class'] = tr.to_class.astype(int)

def save(fig, name, px):
    fig.set_size_inches(px[0] / DPI, px[1] / DPI)
    fig.savefig(OUT + name, dpi=DPI)
    plt.close(fig)

# ---- Fig 3.2: stacked bars
fig, (a1, a2) = plt.subplots(1, 2)
x = np.arange(5)
bot = np.zeros(5); botp = np.zeros(5)
tot = A.sum(axis=0).values
for k in range(7):
    v = A.loc[k, YEARS].values
    a1.bar(x, v, bottom=bot, color=COL[k], edgecolor='white', linewidth=0.6, label=SHORT[k])
    p = v / tot * 100
    a2.bar(x, p, bottom=botp, color=COL[k], edgecolor='white', linewidth=0.6)
    for i in range(5):
        if p[i] >= 4:
            a2.text(x[i], botp[i] + p[i] / 2, c(p[i]), ha='center', va='center', fontsize=8.5,
                    color='white' if k in (0, 3) else 'black')
    bot += v; botp += p
for a, t, yl in ((a1, 'а) Абсолютні площі', 'Площа, км²'), (a2, 'б) Частки класів', 'Частка, %')):
    a.set_xticks(x); a.set_xticklabels(YEARS); a.set_title(t); a.set_ylabel(yl); a.set_xlabel('Рік')
    a.yaxis.set_major_formatter(CF)
fig.legend(*a1.get_legend_handles_labels(), loc='lower center', ncol=4, frameon=False, fontsize=10)
fig.subplots_adjust(left=0.06, right=0.99, top=0.92, bottom=0.25, wspace=0.18)
save(fig, 'image2.png', (2400, 1000))

# ---- Fig 3.3: lines
fig, a = plt.subplots()
for k in range(7):
    a.plot(YEARS, A.loc[k, YEARS].values, '-o', color=COL[k], lw=2.2, ms=6, label=SHORT[k])
a.set_xticks(YEARS); a.set_ylabel('Площа, км²'); a.set_xlabel('Рік'); a.grid(alpha=0.3)
a.yaxis.set_major_formatter(CF)
a.legend(ncol=2, frameon=False, fontsize=9.5, loc='upper left')
a.set_ylim(0, 200)
fig.subplots_adjust(left=0.09, right=0.98, top=0.97, bottom=0.11)
save(fig, 'image3.png', (1600, 900))

# ---- Fig 3.5: Sankey 2021 -> 2023 -> 2024 -> 2025
stages = [2021, 2023, 2024, 2025]
pairs = [(2021, 2023), (2023, 2024), (2024, 2025)]
GAP = 6.0
fig, a = plt.subplots()
xs = [0, 1, 2, 3]; W = 0.035
nodepos = {}
for s, yr in zip(xs, stages):
    y = 0
    for k in range(7):
        h = A.loc[k, yr]
        nodepos[(yr, k)] = [y, y + h]
        a.add_patch(Rectangle((s - W / 2, -y - h), W, h, color=COL[k], zorder=3))
        lab = f'{SHORT[k]}\n{c(h)}' if h >= 8 else (f'{SHORT[k]} {c(h)}' if h >= 2.5 else '')
        ha, dx = ('right', -W) if s > 0 else ('right', -W)
        if s == 0: ha, dx = 'right', -W
        a.text(s + dx, -y - h / 2, lab, ha=ha, va='center', fontsize=7.5, zorder=4)
        y += h + GAP
for (y0, y1), s in zip(pairs, xs[:-1]):
    t = tr[(tr.from_year == y0) & (tr.to_year == y1) & (tr.area_km2 >= 1.0)]
    outc = {k: nodepos[(y0, k)][0] for k in range(7)}
    inc = {k: nodepos[(y1, k)][0] for k in range(7)}
    for k in range(7):
        for _, r in t[t.from_class == k].sort_values('to_class').iterrows():
            j = r.to_class; w = r.area_km2
            a0, b0 = outc[k], inc[j]
            outc[k] += w; inc[j] += w
            xa, xb = s + W / 2, s + 1 - W / 2; xm = (xa + xb) / 2
            verts = [(xa, -a0), (xm, -a0), (xm, -b0), (xb, -b0), (xb, -b0 - w), (xm, -b0 - w), (xm, -a0 - w), (xa, -a0 - w), (xa, -a0)]
            codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.CLOSEPOLY]
            a.add_patch(PathPatch(Path(verts, codes), facecolor=COL[k], edgecolor='none', alpha=0.22 if j == k else 0.55, zorder=2))
for s, yr in zip(xs, stages):
    a.text(s, 8, str(yr), ha='center', va='bottom', fontsize=12, fontweight='bold')
a.set_xlim(-0.62, 3.06); a.set_ylim(-(A[2021].sum() + 7 * GAP) - 2, 22)
a.axis('off')
fig.subplots_adjust(left=0.01, right=0.995, top=0.99, bottom=0.01)
save(fig, 'image5.png', (2600, 1500))

# ---- Fig 3.6: heatmaps
from matplotlib.colors import LogNorm
fig, axs = plt.subplots(1, 2)
for a, (y0, y1) in zip(axs, [(2021, 2023), (2021, 2025)]):
    t = tr[(tr.from_year == y0) & (tr.to_year == y1)]
    M = t.pivot_table(index='from_class', columns='to_class', values='area_km2').reindex(index=range(7), columns=range(7)).fillna(0).values
    im = a.imshow(np.where(M > 0.05, M, np.nan), cmap='YlGnBu', norm=LogNorm(0.1, 150))
    for i in range(7):
        for j in range(7):
            v = M[i, j]
            s = c(v) if v >= 0.05 else '·'
            a.text(j, i, s, ha='center', va='center', fontsize=8.5, color='white' if v > 25 else 'black')
    a.set_xticks(range(7)); a.set_yticks(range(7))
    a.set_xticklabels(SHORT, rotation=40, ha='right', fontsize=8); a.set_yticklabels(SHORT, fontsize=8)
    a.set_xlabel(f'Клас у {y1} р.', fontsize=9); a.set_ylabel(f'Клас у {y0} р.', fontsize=9)
    a.set_title(f'{y0} → {y1}, км²', fontsize=10)
    for sp in a.spines.values(): sp.set_visible(False)
fig.subplots_adjust(left=0.07, right=0.99, top=0.93, bottom=0.3, wspace=0.3)
save(fig, 'image6.png', (2600, 1040))

# ---- Fig 3.7: butterfly by bank
fig, axs = plt.subplots(1, 3, sharey=True)
yy = np.arange(7)[::-1]
for a, yr in zip(axs, [2021, 2023, 2025]):
    L = B[(yr, 'left')].values; R = B[(yr, 'right')].values
    a.barh(yy, -L, color=LC, height=0.6, label='Лівобережжя')
    a.barh(yy, R, color=RC, height=0.6, label='Правобережжя')
    for i in range(7):
        a.text(-L[i] - 2, yy[i], c(L[i]), ha='right', va='center', fontsize=7.5)
        a.text(R[i] + 2, yy[i], c(R[i]), ha='left', va='center', fontsize=7.5)
    a.axvline(0, color='k', lw=0.8); a.set_xlim(-135, 135); a.set_title(str(yr), fontweight='bold')
    a.set_xticks([-100, -50, 0, 50, 100]); a.set_xticklabels(['100', '50', '0', '50', '100']); a.set_xlabel('Площа, км²', fontsize=9)
axs[0].set_yticks(yy); axs[0].set_yticklabels(SHORT, fontsize=9)
axs[0].legend(loc='lower left', fontsize=8, frameon=False)
fig.subplots_adjust(left=0.155, right=0.99, top=0.9, bottom=0.15, wspace=0.08)
save(fig, 'image7.png', (2800, 960))

# ---- Fig 3.8: change 2021->2025 by bank
fig, a = plt.subplots()
x = np.arange(7); w = 0.38
dl = B[(2025, 'left')].values - B[(2021, 'left')].values
dr = B[(2025, 'right')].values - B[(2021, 'right')].values
a.bar(x - w / 2, dl, w, color=LC, label='Лівобережжя'); a.bar(x + w / 2, dr, w, color=RC, label='Правобережжя')
for i in range(7):
    for xv, v in ((x[i] - w / 2, dl[i]), (x[i] + w / 2, dr[i])):
        a.text(xv, v + (1 if v >= 0 else -1), c(v), ha='center', va='bottom' if v >= 0 else 'top', fontsize=7.5)
a.axhline(0, color='k', lw=0.8); a.set_xticks(x); a.set_xticklabels(SHORT, rotation=25, ha='right', fontsize=9)
a.set_ylabel('Δ площі 2025−2021, км²'); a.yaxis.set_major_formatter(CF); a.legend(frameon=False)
fig.subplots_adjust(left=0.1, right=0.98, top=0.96, bottom=0.25)
save(fig, 'image8.png', (1600, 900))

# ---- Fig 3.9: fires (MCD64A1 bars + FIRMS per 100 km2 lines)
mcd = pd.read_csv(D + 'mcd64a1_burned_by_bank_class.csv').groupby(['year', 'bank']).burned_km2.sum().unstack()
fr = pd.read_csv(D + 'firms_detections_by_bank.csv').pivot_table(index='year', columns='bank', values='firms_per_100km2')
fig, a = plt.subplots()
x = np.arange(5); w = 0.38
a.bar(x - w / 2, mcd.loc[YEARS, 'left'], w, color=LC, alpha=0.85, label='MCD64A1, Лівобережжя')
a.bar(x + w / 2, mcd.loc[YEARS, 'right'], w, color=RC, alpha=0.85, label='MCD64A1, Правобережжя')
for i, yr in enumerate(YEARS):
    for xv, v in ((x[i] - w / 2, mcd.loc[yr, 'left']), (x[i] + w / 2, mcd.loc[yr, 'right'])):
        a.text(xv, v + 1, c(v), ha='center', va='bottom', fontsize=8)
a.set_ylabel('Площа вигорання MCD64A1, км²'); a.set_xticks(x); a.set_xticklabels(YEARS); a.yaxis.set_major_formatter(CF)
a2 = a.twinx(); a2.spines['right'].set_visible(True)
a2.plot(x, fr.loc[YEARS, 'left'], '-o', color='#7a2e0b', lw=2, label='FIRMS, Лівобережжя')
a2.plot(x, fr.loc[YEARS, 'right'], '--s', color='#0b3a6b', lw=2, label='FIRMS, Правобережжя')
a2.set_ylabel('Детекцій FIRMS на 100 км²'); a2.yaxis.set_major_formatter(CF); a2.set_ylim(0, 290); a.set_ylim(0, 105)
h1, l1 = a.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=8.5, frameon=False)
fig.subplots_adjust(left=0.08, right=0.92, top=0.97, bottom=0.08)
save(fig, 'image9.png', (1980, 970))
print('done')
