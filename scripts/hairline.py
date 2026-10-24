"""Hairline repairs for traced glyphs.

Where a pen's hairline printed fainter than the scanner's threshold, the trace pinches the stroke
to nothing (a crossbar that narrows to a point mid-way, a stroke end that hangs on by a thread) or
breaks it outright. At display sizes either reads as a crack. pinches() finds them; spine() gives
the stroke back a minimum hairline through each; bridge() joins two hairline tips that the
trace separated, with edges tangent to both.
"""
import numpy as np
import pathops
from scipy import ndimage as ndi
from skimage.morphology import medial_axis
from fontTools.pens.recordingPen import RecordingPen
import shapes as SH
from glyphs import bounds
from outline_util import flatten, raster

RES = 0.5


def _dp(pts, tol):
    """Douglas-Peucker: drop the points a polyline does not need to stay within tol."""
    pts = np.asarray(pts, float)
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]; d = b - a; L = np.hypot(*d)
    dist = (np.abs(d[0] * (pts[:, 1] - a[1]) - d[1] * (pts[:, 0] - a[0])) / L) if L > 1e-9 else np.hypot(*(pts - a).T)
    i = int(np.argmax(dist))
    if dist[i] <= tol:
        return np.array([a, b])
    return np.vstack([_dp(pts[:i + 1], tol)[:-1], _dp(pts[i:], tol)])


def _mask(p, m=10):
    b = bounds(p); x0, y0, x1, y1 = b[0] - m, b[1] - m, b[2] + m, b[3] + m
    W, H = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
    r = RecordingPen(); p.draw(r)
    M = raster(flatten(r.value, 32), (W, H), lambda q: ((q[0] - x0) / RES, (y1 - q[1]) / RES))
    return M, (x0, y1)


def _pinch_regions(p, h_min, pad=0.75):
    """The pinched stretches of a glyph. The outline is first grown by `pad` so the thinnest part
    of a pinch (it can be a mathematical point) stays connected on the raster."""
    from skimage.morphology import disk
    import bolden
    M, (x0, y1) = _mask(bolden.grow(p, pad, pad))
    r = max(1, int(round((h_min / 2 + pad) / RES)))
    O = ndi.binary_opening(M, disk(r).astype(bool))
    rem = M & ~O
    lab, n = ndi.label(rem, structure=np.ones((3, 3)))
    out = []
    for k in range(1, n + 1):
        reg = lab == k
        if reg.sum() * RES * RES < 1.0:
            continue
        touch = ndi.binary_dilation(reg, iterations=1) & O
        _, pieces = ndi.label(touch, structure=np.ones((3, 3)))
        if pieces >= 2:
            out.append(reg)
    return out, (x0, y1)


def pinches(p, h_min):
    """Where the ink is thinner than h_min between two thicker parts (not at a stroke's end):
    the parts an opening by h_min removes that touch the remaining ink in two separate places."""
    regs, (x0, y1) = _pinch_regions(p, h_min)
    pts = []
    for reg in regs:
        ys, xs = np.nonzero(reg)
        pts.append((x0 + (xs.mean() + 0.5) * RES, y1 - (ys.mean() + 0.5) * RES))
    return pts


def spine(p, h_min, margin=16.0):
    """Give every pinch a hairline at least h_min wide: a band of that width laid along the stroke's
    own centre line through the pinch, which lies inside the ink wherever the stroke is wider."""
    regs, (x0, y1) = _pinch_regions(p, h_min)
    bands = []
    for reg in regs:
        ys, xs = np.nonzero(reg)
        X = np.stack([x0 + (xs + 0.5) * RES, y1 - (ys + 0.5) * RES], 1)
        c0 = X.mean(0); ev, evec = np.linalg.eigh(np.cov((X - c0).T))
        ax = evec[:, np.argmax(ev)]                      # the stroke's direction through the pinch
        ang = float(np.degrees(np.arctan2(ax[1], ax[0])))
        q = SH.rotate(p, -ang, *c0)                      # stroke horizontal, pinch at c0
        U = (X - c0) @ ax
        u0, u1 = U.min() - margin, U.max() + margin
        res = 0.25; Hh = 60.0
        W = int((u1 - u0) / res) + 1; H = int(2 * Hh / res) + 1
        r = RecordingPen(); q.draw(r)
        M = raster(flatten(r.value, 48), (W, H), lambda t: ((t[0] - (c0[0] + u0)) / res, (c0[1] + Hh - t[1]) / res))
        cen = np.full(W, np.nan); prev = H / 2
        for k in range(W):
            col = np.nonzero(M[:, k])[0]
            if not len(col):
                continue
            runs = np.split(col, np.nonzero(np.diff(col) > 1)[0] + 1)
            run = min(runs, key=lambda rr: abs((rr[0] + rr[-1]) / 2 - prev))
            if abs((run[0] + run[-1]) / 2 - prev) > 12 / res:
                continue
            cen[k] = prev = (run[0] + run[-1]) / 2
        ok = ~np.isnan(cen)
        if ok.sum() < 4:
            continue
        ks = np.arange(W); cen = np.interp(ks, ks[ok], cen[ok])
        cen = np.convolve(np.r_[np.repeat(cen[0], 12), cen, np.repeat(cen[-1], 12)], np.ones(25) / 25, 'valid')
        uu = c0[0] + u0 + ks * res; vv = c0[1] + Hh - cen * res
        top = _dp([(a, b + h_min / 2) for a, b in zip(uu, vv)], 0.15)
        bot = _dp([(a, b - h_min / 2) for a, b in zip(uu, vv)], 0.15)
        band = SH.polygon([tuple(q) for q in top] + [tuple(q) for q in bot[::-1]])
        bands.append(SH.rotate(band, ang, *c0))
    return SH.union(p, *bands) if bands else p


def bridge(p, a, b, reach=14.0):
    """Join two stroke tips near a and b: the convex hull of the outline within `reach` of each."""
    from scipy.spatial import ConvexHull
    r = RecordingPen(); p.draw(r)
    pts = np.array([q for poly in flatten(r.value, 48) for q in poly])
    near = pts[(np.hypot(pts[:, 0] - a[0], pts[:, 1] - a[1]) < reach) | (np.hypot(pts[:, 0] - b[0], pts[:, 1] - b[1]) < reach)]
    h = ConvexHull(near)
    ring = near[h.vertices]
    k = int(np.argmax(np.hypot(*(ring - ring.mean(0)).T)))      # start at an extreme vertex
    ring = np.roll(ring, -k, axis=0); ring = _dp(np.vstack([ring, ring[:1]]), 0.15)[:-1]
    return SH.union(p, SH.polygon([tuple(q) for q in ring]))
