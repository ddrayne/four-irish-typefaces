"""Find hairline defects in the traced glyphs: places where a stroke thins almost to nothing between
thicker parts (a pinch), and places where two strokes come within a hair of touching (a crack).
Either reads as a break at display sizes.

usage: pinch.py FONT  -> list + pinch_<font>.png (each find circled)
"""
import sys, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage.morphology import medial_axis
from fontTools.pens.recordingPen import RecordingPen
from glyphs import load, bounds
from outline_util import flatten, raster
from bolden import _branches
from metrics import stats

RES = 1.0


def mask(p, m=20):
    b = bounds(p); x0, y0, x1, y1 = b[0] - m, b[1] - m, b[2] + m, b[3] + m
    W, H = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
    r = RecordingPen(); p.draw(r)
    M = raster(flatten(r.value, 24), (W, H), lambda q: ((q[0] - x0) / RES, (y1 - q[1]) / RES))
    return M, (x0, y1)


def finds(p, stem):
    M, (x0, y1) = mask(p)
    out = []
    for kind, region in (('pinch', M), ('crack', ~M)):
        skel, dist = medial_axis(region, return_distance=True, rng=0)
        for path, d0, d1 in _branches(skel):
            if len(path) < 6:
                continue
            d = np.array([dist[q] for q in path]); i = int(np.argmin(d))
            if not 0 < i < len(d) - 1:
                continue
            w = 2 * d[i] * RES
            lim = 0.06 * stem if kind == 'pinch' else 0.22 * stem
            if w < lim and d[0] > 1.8 * d[i] and d[-1] > 1.8 * d[i]:
                q = path[i]; out.append((kind, round(w, 1), (round(x0 + q[1] * RES), round(y1 - q[0] * RES))))
    return out


if __name__ == '__main__':
    key = sys.argv[1]; G, s = load(key)
    st = stats(key); xh = st['xh'][0] * s
    from build2 import stem_at
    w = lambda n: stem_at(G[n]['path'], 0.4 * xh, 'left')
    stem = float(np.mean([w('l')[1] - w('l')[0], w('n')[1] - w('n')[0]]))
    tiles = []
    for n in sorted(G):
        p = G[n]['path']
        if bounds(p) is None:
            continue
        f = finds(p, stem)
        if not f:
            continue
        print(f'{key:8s} {n:14s}', '  '.join(f'{k} {w}u @{xy}' for k, w, xy in f))
        b = bounds(p); sc = 0.3; pad = 10
        Wt, Ht = int((b[2] - b[0]) * sc) + 2 * pad, int((b[3] - b[1]) * sc) + 2 * pad
        r = RecordingPen(); p.draw(r)
        m = raster(flatten(r.value, 24), (Wt, Ht), lambda q: ((q[0] - b[0]) * sc + pad, (b[3] - q[1]) * sc + pad))
        im = Image.fromarray(np.where(m, 0, 255).astype(np.uint8)).convert('RGB'); d = ImageDraw.Draw(im)
        for k, wd, (x, y) in f:
            cx, cy = (x - b[0]) * sc + pad, (b[3] - y) * sc + pad
            d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], outline=(255, 0, 0) if k == 'pinch' else (0, 120, 255), width=2)
        d.text((2, 2), n, fill=(200, 0, 0)); tiles.append(im)
    if tiles:
        cols = 10; rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
        W = max(sum(t.width + 8 for t in r) for r in rows); Hs = [max(t.height for t in r) + 8 for r in rows]
        out = Image.new('RGB', (W, sum(Hs)), 'white'); y = 0
        for r, h in zip(rows, Hs):
            x = 0
            for t in r:
                out.paste(t, (x, y)); x += t.width + 8
            y += h
        out.save(f'{sys.argv[2] if len(sys.argv) > 2 else "."}/pinch_{key}.png')
    print(key, 'stem', round(stem), len(tiles), 'glyphs with finds')
