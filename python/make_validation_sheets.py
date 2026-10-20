#!/usr/bin/env python3
"""
Контактні аркуші для «сліпої» розмітки точок незалежної валідації за знімками
надвисокої роздільності (WorldView-2 / WorldView-3 тощо).

Для кожної точки року скрипт знаходить знімки, що її покривають (кілька сцен на рік —
нормально), обирає найкращу за датою, вирізає вікно навколо точки й показує його
в натуральних кольорах і, якщо є ближній ІЧ канал, у псевдокольорах (NIR-R-G).
У центрі — рамка 10×10 м (піксель карти) і перехрестя. Класу карти на аркушах немає.

Встановлення:
    pip install rasterio numpy pandas pillow pyproj

Приклад запуску:
    python make_validation_sheets.py --points validation_blind_v8.csv --year 2025 \
        --images D:/WV/2025 --out sheets
    # кілька тек або окремих файлів:
    python make_validation_sheets.py --points validation_blind_v8.csv --year 2021 \
        --images D:/WV/2021_a D:/WV/2021_b/scene3.tif --out sheets

Дата сцени визначається з назви файлу (2025-07-14, 20250714, 25JUL14… у стилі Maxar)
або з необов'язкового CSV --dates (стовпці file,date). Перевірте вивід «Сцени»:
якщо дата не розпізналась, задайте її через --dates.

Канали: за замовчуванням вгадуються за кількістю (8 каналів WV-2/3 MS: R=5,G=3,B=2,NIR=7;
4 канали: B,G,R,NIR; 3 канали: R,G,B). Якщо кольори виглядають дивно — задайте явно,
напр. --rgb 3 2 1 --nir 4 (нумерація з 1).
"""
import argparse, csv, glob, math, os, re, sys
from datetime import date
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from pyproj import Transformer
from PIL import Image, ImageDraw, ImageFont

MONTHS = {m: i + 1 for i, m in enumerate(['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'])}


def parse_date(name):
    s = os.path.basename(name)
    m = re.search(r'(20\d\d)[-_.]?(0[1-9]|1[0-2])[-_.]?([0-2]\d|3[01])', s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(r'(\d\d)(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d\d)', s.upper())
    if m:
        return date(2000 + int(m.group(1)), MONTHS[m.group(2)], int(m.group(3)))
    return None


def date_from_metadata(path, ds):
    """Дата зйомки з тегів GeoTIFF або з файлів метаданих поруч (.XML, .IMD, .TXT, .JSON)."""
    texts = []
    try:
        for ns in [None] + list(ds.tag_namespaces() or []):
            texts += [f'{k}={v}' for k, v in (ds.tags(ns=ns) if ns else ds.tags()).items()]
    except Exception:
        pass
    stem = os.path.splitext(path)[0]
    base = re.sub(r'[-_]ord_\d+$', '', stem)
    folder = os.path.dirname(path)
    for f in glob.glob(os.path.join(folder, '*')):
        if f.lower().endswith(('.xml', '.imd', '.txt', '.json')) and (os.path.basename(f).startswith(os.path.basename(base)) or len(glob.glob(os.path.join(folder, '*.tif'))) <= 1):
            try:
                texts.append(open(f, encoding='utf-8', errors='ignore').read()[:200000])
            except OSError:
                pass
    blob = '\n'.join(texts)
    for key in ['firstLineTime', 'FIRSTLINETIME', 'earliestAcqTime', 'acquisitionDate', 'ACQUISITION', 'acquired', 'DATETIME', 'DateTime']:
        i = blob.find(key)
        if i >= 0:
            m = re.search(r'(20\d\d)[-:/](\d\d)[-:/](\d\d)', blob[i:i + 200])
            if m:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def find_images(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for ext in ('*.tif', '*.TIF', '*.tiff', '*.TIFF', '*.vrt', '*.jp2', '*.JP2'):
                out += glob.glob(os.path.join(p, '**', ext), recursive=True)
        else:
            out += glob.glob(p)
    return sorted(set(out))


def guess_bands(n, rgb, nir, ci=None):
    if rgb:
        return rgb, (None if nir == 0 else nir)
    if ci:
        names = [c.name for c in ci]
        if all(x in names for x in ('red', 'green', 'blue')):
            r, g, b = (names.index(x) + 1 for x in ('red', 'green', 'blue'))
            extra = [i + 1 for i, x in enumerate(names) if x not in ('red', 'green', 'blue', 'alpha')]
            return [r, g, b], (None if nir == 0 else (nir or (extra[0] if extra else None)))
    if n >= 8:
        return [5, 3, 2], (nir or 7)
    if n == 4:
        return [3, 2, 1], (nir or 4)
    if n == 3:
        return [1, 2, 3], nir
    return [1, 1, 1], None


class Scene:
    def __init__(self, path, dt, rgb, nir):
        self.path = path
        self.ds = rasterio.open(path)
        self.date = dt or date_from_metadata(path, self.ds)
        ci = self.ds.colorinterp
        self.alpha = ([c.name for c in ci].index('alpha') + 1) if 'alpha' in [c.name for c in ci] else None
        self.rgb, self.nir = guess_bands(self.ds.count, rgb, nir, ci)
        self.ci = [c.name for c in ci]
        if self.nir and (self.nir > self.ds.count or self.nir == self.alpha):
            self.nir = None
        self.to_scene = Transformer.from_crs('EPSG:4326', self.ds.crs, always_xy=True)
        self.geographic = self.ds.crs.is_geographic
        self.nodata = self.ds.nodata
        self._stretch()

    def _stretch(self):
        # глобальні 2–98 % перцентилі за зменшеною копією — однаковий контраст для всіх точок сцени
        bands = sorted(set(self.rgb + ([self.nir] if self.nir else [])))
        f = max(1, int(max(self.ds.width, self.ds.height) / 1500))
        arr = self.ds.read(bands, out_shape=(len(bands), self.ds.height // f, self.ds.width // f), resampling=Resampling.nearest).astype('float32')
        valid = np.all(arr > 0, axis=0) if self.nodata in (None, 0) else np.all(arr != self.nodata, axis=0)
        self.lim = {}
        for i, b in enumerate(bands):
            v = arr[i][valid]
            self.lim[b] = (np.percentile(v, 2), np.percentile(v, 98)) if v.size else (0, 1)

    def window(self, lon, lat, half_m):
        x, y = self.to_scene.transform(lon, lat)
        if self.geographic:
            dy = half_m / 111320.0
            dx = half_m / (111320.0 * math.cos(math.radians(lat)))
        else:
            dx = dy = half_m
        return (x - dx, y - dy, x + dx, y + dy), (x, y)

    def covers(self, lon, lat):
        (l, b, r, t), (x, y) = self.window(lon, lat, 1)
        B = self.ds.bounds
        if not (B.left <= x <= B.right and B.bottom <= y <= B.top):
            return False
        row, col = self.ds.index(x, y)
        if self.alpha:
            av = self.ds.read(self.alpha, window=((row, row + 1), (col, col + 1)), boundless=True, fill_value=0)
            if not np.all(av > 0):
                return False
        v = self.ds.read(self.rgb, window=((row, row + 1), (col, col + 1)), boundless=True, fill_value=0)
        if self.nodata not in (None, 0):
            return bool(np.all(v != self.nodata))
        return bool(np.all(v > 0))

    def chip(self, lon, lat, half_m, px):
        bounds, _ = self.window(lon, lat, half_m)
        win = from_bounds(*bounds, transform=self.ds.transform)
        def read(bands):
            a = self.ds.read(bands, window=win, out_shape=(len(bands), px, px), boundless=True, fill_value=0,
                             resampling=Resampling.bilinear).astype('float32')
            out = np.zeros_like(a)
            for i, b in enumerate(bands):
                lo, hi = self.lim[b]
                out[i] = np.clip((a[i] - lo) / max(hi - lo, 1e-6), 0, 1)
            return (np.moveaxis(out, 0, -1) * 255).astype('uint8')
        tc = read(self.rgb)
        fc = read([self.nir, self.rgb[0], self.rgb[1]]) if self.nir else None
        return tc, fc


def draw_marks(img, half_m, box_m=10):
    d = ImageDraw.Draw(img)
    w = img.width
    c = w / 2
    s = w * (box_m / 2) / (2 * half_m)  # половина рамки 10 м у пікселях
    d.rectangle([c - s, c - s, c + s, c + s], outline=(255, 255, 0), width=2)
    g = s * 2.2
    for (x0, y0, x1, y1) in [(c - g - 14, c, c - g, c), (c + g, c, c + g + 14, c), (c, c - g - 14, c, c - g), (c, c + g, c, c + g + 14)]:
        d.line([x0, y0, x1, y1], fill=(255, 0, 255), width=2)
    # масштабна лінійка 50 м
    L = w * 50 / (2 * half_m)
    d.rectangle([6, w - 14, 6 + L, w - 9], fill=(255, 255, 255), outline=(0, 0, 0))
    return img


def load_font(size):
    for f in ['DejaVuSans.ttf', 'arial.ttf', 'C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--points', required=True, help='validation_blind_v8.csv (id, year, lat, lon, ref)')
    ap.add_argument('--year', type=int, required=True)
    ap.add_argument('--images', nargs='+', required=True, help='теки та/або файли зі знімками цього року')
    ap.add_argument('--out', default='sheets')
    ap.add_argument('--dates', help='CSV з колонками file,date (YYYY-MM-DD), якщо дата не в назві файлу')
    ap.add_argument('--rgb', nargs=3, type=int, help='номери каналів R G B (з 1)')
    ap.add_argument('--nir', type=int, help='номер ближнього ІЧ каналу (з 1); 0 — каналу NIR немає')
    ap.add_argument('--half', type=float, default=60, help='половина розміру вікна, м (60 → вікно 120×120 м)')
    ap.add_argument('--px', type=int, default=300, help='розмір фрагмента, пікселів')
    ap.add_argument('--cols', type=int, default=3)
    ap.add_argument('--rows', type=int, default=4)
    ap.add_argument('--target', default='07-15', help='бажана дата сезону (MM-DD); обирається найближча сцена')
    ap.add_argument('--second', action='store_true', help='додати другий фрагмент з іншої дати, якщо є')
    ap.add_argument('--info', action='store_true', help='лише показати метадані знімків і вийти')
    a = ap.parse_args()
    if a.info:
        for f in find_images(a.images):
            with rasterio.open(f) as ds:
                print('==', f, ds.count, [c.name for c in ds.colorinterp], ds.dtypes[0], ds.crs, ds.res)
                print('   tags:', dict(list(ds.tags().items())[:20]))
                for ns in (ds.tag_namespaces() or []):
                    print('   ns', ns, dict(list(ds.tags(ns=ns).items())[:10]))
                print('   band1 tags:', ds.tags(1), ' descriptions:', ds.descriptions)
            for g in glob.glob(os.path.join(os.path.dirname(f), '*')):
                if not g.lower().endswith(('.tif', '.tiff')): print('   поруч:', os.path.basename(g))
        return

    pts = pd.read_csv(a.points)
    pts = pts[pts.year == a.year].sort_values('id').reset_index(drop=True)
    dmap = {}
    if a.dates:
        for r in csv.DictReader(open(a.dates, encoding='utf-8')):
            dmap[os.path.basename(r['file'])] = date.fromisoformat(r['date'])

    files = find_images(a.images)
    if not files:
        sys.exit('Не знайдено жодного знімка')
    scenes = []
    print('Сцени:')
    for f in files:
        dt = dmap.get(os.path.basename(f)) or parse_date(f)
        try:
            sc = Scene(f, dt, a.rgb, a.nir)
        except Exception as e:
            print(f'  ! {f}: {e}'); continue
        scenes.append(sc)
        print(f'  {os.path.basename(f)} | дата: {sc.date or "НЕ ВИЗНАЧЕНО"} | каналів: {sc.ds.count} ({",".join(sc.ci)}) | RGB={sc.rgb} NIR={sc.nir} | {sc.ds.crs} | {sc.ds.res[0]:.2e}')
    tgt = date(a.year, *map(int, a.target.split('-')))
    rank = lambda s: abs((s.date - tgt).days) if s.date else 10**6

    os.makedirs(os.path.join(a.out, str(a.year)), exist_ok=True)
    for old in glob.glob(os.path.join(a.out, str(a.year), f'sheet_{a.year}_*.jpg')):
        os.remove(old)  # прибираємо аркуші попереднього запуску
    font, fsmall = load_font(20), load_font(14)
    per = a.cols * a.rows
    nimg = 1 + (1 if any(s.nir for s in scenes) else 0)
    nimg *= 2 if a.second else 1
    tw, th = a.px * nimg + 6 * (nimg - 1), a.px + 30
    report, sheet, cell, sheet_no = [], None, 0, 0

    def flush():
        nonlocal sheet, sheet_no
        if sheet is not None:
            fn = os.path.join(a.out, str(a.year), f'sheet_{a.year}_{sheet_no:03d}.jpg')
            sheet.save(fn, quality=88)
            print('  →', fn)

    for _, p in pts.iterrows():
        cov = sorted([s for s in scenes if s.covers(p.lon, p.lat)], key=rank)
        report.append({'id': int(p.id), 'year': a.year, 'n_scenes': len(cov),
                       'scene': os.path.basename(cov[0].path) if cov else '', 'date': str(cov[0].date) if cov else '',
                       'scene2': os.path.basename(cov[1].path) if a.second and len(cov) > 1 else ''})
        if not cov:
            continue
        if cell % per == 0:
            flush(); sheet_no += 1
            sheet = Image.new('RGB', (a.cols * (tw + 16) + 16, a.rows * (th + 16) + 16), (40, 40, 40))
        x0 = 16 + (cell % per % a.cols) * (tw + 16)
        y0 = 16 + (cell % per // a.cols) * (th + 16)
        d = ImageDraw.Draw(sheet)
        use = cov[:2] if a.second else cov[:1]
        label = f'ID {int(p.id)}   ' + '  /  '.join(str(s.date or '?') for s in use)
        d.text((x0, y0 + 2), label, fill=(255, 255, 255), font=font)
        xi = x0
        for s in use:
            tc, fc = s.chip(p.lon, p.lat, a.half, a.px)
            for im in [tc] + ([fc] if fc is not None else []):
                sheet.paste(draw_marks(Image.fromarray(im), a.half), (xi, y0 + 28))
                xi += a.px + 6
        cell += 1
    flush()

    rep = pd.DataFrame(report)
    rep.to_csv(os.path.join(a.out, f'coverage_{a.year}.csv'), index=False)
    miss = rep[rep.n_scenes == 0]
    print(f'\nТочок року {a.year}: {len(rep)}; на аркушах: {len(rep) - len(miss)}; без покриття: {len(miss)}')
    if len(miss):
        print('  id без покриття:', ', '.join(map(str, miss.id.tolist()[:50])), '…' if len(miss) > 50 else '')
    print(f'Аркушів: {sheet_no}. Легенда: жовта рамка — 10×10 м (піксель карти), біла лінійка — 50 м; '
          f'ліворуч — натуральні кольори, праворуч — NIR-R-G (рослинність червона).')


if __name__ == '__main__':
    main()
