"""Fit the position of a glyph's top mark against the flyer: register the base letter first
(rows below the split), then the mark alone (rows above). Prints the mark offset (font units)
that best matches the scan.

usage: python fit_marks.py FONT glyph[,glyph...] [split_units]
"""
import traced
import sys, pickle, numpy as np
from scipy import ndimage as ndi
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from seg import segment
from trace import regions
from trace2 import PARAMS2, F, ink_field
from metrics import line_baselines
from glyphs import SCALE
from outline_util import flatten, raster
from build2 import FONTS, OUT


def run(font, names, split, fontpath=None):
    cfg = FONTS[font]; s = SCALE[font]
    tt = TTFont(fontpath or f'{OUT}/{cfg["ps"]}-Regular.otf'); gs = tt.getGlyphSet()
    res = traced.records(font); base = line_baselines(res); byname = {r['name']: r for r in res}
    lines = segment(font, verbose=False)
    glyphs, region, sub, paper_mask, origin = regions(font, lines)
    out = {}
    for i, g in enumerate(glyphs):
        g['idx'] = i + 1
        if g['name'] not in names:
            continue
        P = dict(PARAMS2[font], **PARAMS2[font].get('glyph', {}).get(g['name'], {}))
        fld, (ox, oy), paper, ink = ink_field(g, region, sub, paper_mask, origin, P)
        H, W = fld.shape
        target = ndi.distance_transform_edt(fld > 0.5) > P['spread'] * F
        r = byname[g['name']]; b0 = base[r['line_idx']]
        rec = RecordingPen(); gs[g['name']].draw(rec); polys = flatten(rec.value, 24)
        top = lambda q: max(p[1] for p in q); bot = lambda q: min(p[1] for p in q)
        body = [q for q in polys if bot(q) < split]; mark = [q for q in polys if bot(q) >= split]
        X0 = min(p[0] for q in polys for p in q)
        rows = np.arange(H)[:, None]
        def xf(dx, dy):
            return lambda q: (((q[0] - X0) / s + r['b'][0] + dx - ox) * F, ((b0 + dy - q[1] / s) - oy) * F)
        def iou(a, b):
            return (a & b).sum() / max((a | b).sum(), 1)
        best = None
        for dx in np.arange(-2, 2.01, 0.25):
            for dy in np.arange(-1.5, 1.51, 0.25):
                f = xf(dx, dy); split_row = f((0, split))[1]
                m = raster(body, (W, H), f); below = rows > split_row
                v = iou(m & below, target & below)
                if best is None or v > best[0]:
                    best = (v, dx, dy)
        _, dx, dy = best; f = xf(dx, dy); split_row = f((0, split))[1]; above = rows < split_row
        bm = None
        for mx in range(-120, 121, 6):
            for my in range(-60, 61, 6):
                m = raster([[(p[0] + mx, p[1] + my) for p in q] for q in mark], (W, H), f)
                v = iou(m & above, target & above)
                if bm is None or v > bm[0]:
                    bm = (v, mx, my)
        out[g['name']] = bm
        print(f'{g["name"]:10} mark offset that fits the flyer: x {bm[1]:+4d}u  y {bm[2]:+4d}u   (IoU above split {bm[0]:.3f})')
    return out


if __name__ == '__main__':
    run(sys.argv[1], set(sys.argv[2].split(',')), float(sys.argv[3]) if len(sys.argv) > 3 else 560)
