"""Profile-based spacing (HT-Letterspacer style) and conservative auto-kerning."""
import numpy as np
from fontTools.pens.recordingPen import RecordingPen
from outline_util import flatten
from glyphs import bounds

def polys(path):
    rec = RecordingPen(); path.draw(rec); return [np.array(p) for p in flatten(rec.value, steps=10)]

def profiles(path, z0, z1, step=8):
    """Leftmost/rightmost ink x at each scanline in [z0, z1] (nan where no ink)."""
    P = polys(path); ys = np.arange(z0 + step/2, z1, step)
    L = np.full(len(ys), np.nan); R = np.full(len(ys), np.nan)
    for poly in P:
        a = poly; b = np.roll(poly, -1, axis=0)
        for k, y in enumerate(ys):
            m = ((a[:, 1] <= y) & (b[:, 1] > y)) | ((b[:, 1] <= y) & (a[:, 1] > y))
            if not m.any(): continue
            t = (y - a[m, 1]) / (b[m, 1] - a[m, 1]); xs = a[m, 0] + t*(b[m, 0] - a[m, 0])
            L[k] = np.nanmin([L[k], xs.min()]); R[k] = np.nanmax([R[k], xs.max()])
    return ys, L, R

def side_depths(path, zone, dmax):
    """Average clamped depth on each side + overhang of the bbox beyond the zone extreme."""
    x0, y0, x1, y1 = bounds(path)
    ys, L, R = profiles(path, *zone)
    if np.all(np.isnan(L)):           # nothing in zone (accents, quotes): use own extent
        ys, L, R = profiles(path, y0, y1)
    xl = np.nanmin(L); xr = np.nanmax(R)
    dl = np.where(np.isnan(L), dmax, np.minimum(L - xl, dmax)).mean()
    dr = np.where(np.isnan(R), dmax, np.minimum(xr - R, dmax)).mean()
    return dict(dl=dl, dr=dr, ohl=xl - x0, ohr=x1 - xr, x0=x0, x1=x1)

def sidebearings(info, K, minsb):
    lsb = max(K - info['dl'], minsb) - info['ohl']
    rsb = max(K - info['dr'], minsb) - info['ohr']
    return lsb, rsb
