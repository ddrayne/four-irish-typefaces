"""Overlay the built fonts on the large 48-60pt samples printed on the sheet and compare stem weights."""
import paths
import os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from outline_util import flatten, raster
from seg import GRAY
from build2 import FONTS, OUT

REG = {'kilfane': (230, 392, 345, 449), 'tuam': (600, 364, 720, 416), 'carrick': (220, 715, 330, 772), 'ceili': (610, 734, 720, 770)}
NAMES = {'kilfane': ['A', 'a', 'one'], 'tuam': ['a', 'one'], 'carrick': ['a', 'one'], 'ceili': ['a', 'one']}
F = 8

def scan_glyphs(box):
    x0, y0, x1, y1 = box
    g = GRAY[y0:y1, x0:x1].astype(float)
    m = g < 160
    lab, n = ndi.label(m, structure=np.ones((3, 3)))
    out = []
    for i, sl in enumerate(ndi.find_objects(lab)):
        if (lab[sl] == i + 1).sum() >= 40:
            out.append((sl[1].start + x0, sl[0].start + y0, sl[1].stop + x0, sl[0].stop + y0))
    return sorted(out)

def field(box):
    x0, y0, x1, y1 = box
    g = GRAY[y0 - 3:y1 + 3, x0 - 3:x1 + 3].astype(float)
    paper = np.percentile(g, 92); core = ndi.binary_erosion(g < 160, iterations=1)
    ink = np.median(g[core]) if core.sum() > 10 else 90
    v = np.clip((paper - g) / (paper - ink), 0, 1)
    return ndi.zoom(v, F, order=3, grid_mode=True, mode='grid-constant', cval=0.0) > 0.5

def stem(mask):
    rows = np.nonzero(mask.any(1))[0]; t, b = rows.min(), rows.max()
    ws = []
    for r in range(int(t + 0.35 * (b - t)), int(t + 0.65 * (b - t))):
        xs = np.nonzero(mask[r])[0]
        if len(xs): ws.append(max(len(q) for q in np.split(xs, np.nonzero(np.diff(xs) > 1)[0] + 1)))
    return np.median(ws) / F, (b - t + 1) / F

tiles = []
for font, box in REG.items():
    cfg = FONTS[font]; tt = TTFont(f'{OUT}/{cfg["ps"]}-Regular.otf'); gs = tt.getGlyphSet()
    comps = scan_glyphs(box)
    comps = [c for c in comps if c[3] - c[1] > 15][-len(NAMES[font]):]
    for name, c in zip(NAMES[font], comps):
        sm = field(c)
        rec = RecordingPen(); gs[name].draw(rec); P = flatten(rec.value, steps=20)
        xs = [p[0] for q in P for p in q]; ys = [p[1] for q in P for p in q]
        gh = max(ys) - min(ys); gw = max(xs) - min(xs)
        H = (sm.any(1).sum()) / F      # scan glyph height in px
        k = H / gh * F                  # font units -> upsampled px
        W, Hh = sm.shape[1], sm.shape[0]
        fm = raster(P, (W, Hh), lambda q: ((q[0] - min(xs)) * k, (max(ys) - q[1]) * k))
        # align centroids
        cy0, cx0 = ndi.center_of_mass(sm); cy1, cx1 = ndi.center_of_mass(fm)
        fm = ndi.shift(fm.astype(float), (cy0 - cy1, cx0 - cx1), order=0) > 0.5
        iou = (sm & fm).sum() / (sm | fm).sum()
        if name == 'one':
            ws, hs = stem(sm); wf, hf = stem(fm)
            print(f'{font:8s} {name:4s} scan stem {ws:.2f}px  font stem {wf:.2f}px  (font-scan {wf - ws:+.2f}px, i.e. {100 * (wf / ws - 1):+.0f}%)  IoU {iou:.2f}')
        else:
            print(f'{font:8s} {name:4s} IoU {iou:.2f}  ink area font/scan {fm.sum() / sm.sum():.2f}')
        rgb = np.full(sm.shape + (3,), 255, np.uint8)
        rgb[sm & ~fm] = (60, 110, 230); rgb[fm & ~sm] = (230, 60, 60); rgb[sm & fm] = (40, 40, 40)
        tiles.append(Image.fromarray(rgb).resize((rgb.shape[1] // 2, rgb.shape[0] // 2)))
W = sum(t.width for t in tiles) + 12 * len(tiles); H = max(t.height for t in tiles)
o = Image.new('RGB', (W, H), 'white'); x = 0
for t in tiles: o.paste(t, (x, 0)); x += t.width + 12
o.save(os.path.join(paths.VIEW, 'weightcheck.png')); print(o.size)
