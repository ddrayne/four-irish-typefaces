"""Bold and sloped styles derived from the 1978 drawings.

embolden(): the pen model. Each face's regular strokes are widened as if drawn with a wider pen:
the outline is grown by an ellipse (rx across, ry up and down) whose proportions match the face's
own stroke contrast, after a slight horizontal widening that keeps the counters open. Corners stay
sharp (mitred offset), and heights are restored afterwards so Regular and Bold share x-height,
cap height and ascenders.
"""
import math
import numpy as np
import pathops
import shapes as SH
from glyphs import bounds, contours, translate
from fontTools.pens.areaPen import AreaPen


def area(p):
    ap = AreaPen(); p.draw(ap); return ap.value


def components(p):
    """Split a glyph into its separate pieces: each outer contour with the holes inside it."""
    cs = contours(p)
    outer = [c for c in cs if area(c) > 0]; holes = [c for c in cs if area(c) < 0]
    if not outer:                       # winding the other way round
        outer, holes = holes, outer
    groups = []
    for o in outer:
        b = bounds(o)
        inside = [h for h in holes if bounds(h)[0] >= b[0] - 1 and bounds(h)[2] <= b[2] + 1 and
                  bounds(h)[1] >= b[1] - 1 and bounds(h)[3] <= b[3] + 1]
        groups.append((o, inside))
    # a hole belongs to the smallest outer contour that contains it
    out = []
    for o, hs in groups:
        mine = [h for h in hs if min((g for g in groups if h in g[1]), key=lambda g: abs(area(g[0])))[0] is o]
        out.append(SH.difference(o, SH.union(*mine)) if mine else o)
    return out


def concat(paths):
    """Put several shapes into one path without merging them (their contours may overlap)."""
    out = pathops.Path(); pen = out.getPen()
    for p in paths:
        p.draw(pen)
    return out


def pieces(p):
    """How many separate pieces a shape has (its outer contours)."""
    a = [area(c) for c in contours(p)]
    return sum(x > 0 for x in a) or sum(x < 0 for x in a)      # or wound the other way round


def _sound(to, g):
    """A grown shape still covers everything it grew from, and growing never splits a piece."""
    return abs(area(SH.difference(to, g))) <= 1e-3 * abs(area(to)) and pieces(g) <= pieces(to)


def grow(p, rx, ry, miter=4.0):
    """Grow a shape by an axis-aligned ellipse (rx, ry), keeping convex corners sharp."""
    if rx <= 0 and ry <= 0:
        return p
    to = SH.transform(p, (1 / rx, 0, 0, 1 / ry, 0, 0))
    s = pathops.Path(to)
    s.stroke(2.0, pathops.LineCap.BUTT_CAP, pathops.LineJoin.MITER_JOIN, miter)
    s.convertConicsToQuads()
    g = SH.union(to, s)
    if not _sound(to, g):
        # The stroke's inner edge loops back on itself wherever the outline turns inward more
        # tightly than the pen, and pathops can resolve those loops wrongly in the union, leaving a
        # whole letter as a hole (Y and 3 traced from the original sheets did). Resolving the
        # stroke on its own first gives a clean band; it is not always right either (Tuam's sloped
        # thorn), so each result is checked and the first sound one kept.
        alt = SH.union(to, pathops.simplify(s, fix_winding=False, keep_starting_points=False, clockwise=False))
        if _sound(to, alt):
            g = alt
    return SH.transform(g, (rx, 0, 0, ry, 0, 0))


def remap(p, fn):
    """Apply a point-wise mapping to every point of a path."""
    from fontTools.pens.recordingPen import RecordingPen, replayRecording
    rec = RecordingPen(); p.draw(rec)
    out = [(op, tuple(fn(*pt) for pt in args)) for op, args in rec.value]
    q = pathops.Path(); replayRecording(out, q.getPen())
    return pathops.simplify(q, fix_winding=True, keep_starting_points=False, clockwise=False)


def heights_back(p, xh, ry):
    """Undo the height the growth added: baseline and x-height back in place, ascenders and
    descenders moved back by ry, the x-height band compressed to fit."""
    c = xh / (xh + 2 * ry)
    def f(x, y):
        if y < -ry:
            return x, y + ry
        if y > xh + ry:
            return x, y - ry
        return x, (y + ry) * c
    return remap(p, f)


def embolden(p, rx, ry, k, xh, stem, separate=True, keep_open=True, apertures=True):
    parts = components(p) if separate else [p]
    wide = [SH.transform(q, (k, 0, 0, 1, 0, 0)) for q in parts]
    bold = heights_back(SH.union(*[grow(q, rx, ry) for q in wide]), xh, ry)
    if not keep_open:
        return bold
    # the regular in the bold's frame: same widening and height map, no growth
    return protect(heights_back(SH.union(*wide), xh, ry), bold, stem, (rx, ry), apertures)


# ---------------------------------------------------------------------------------------------
# Keeping the bold open. A wider pen fills every narrow background space at once: the eye of an e,
# the counters of a $, the opening of a c. A designer keeps these open by hand, drawing the inside
# of a small counter with a lighter pen, or thinning the strokes either side of an aperture.
# The spaces are read from the regular glyph's background, after closing the hairline gaps where
# two strokes meet but the trace left a sliver between them (those close in the bold, as they should).
# * Every enclosed counter keeps at least F_HOLE of its inscribed radius: where the bold took more,
#   the counter is drawn again as the regular's counter shrunk by a lighter pen, so it keeps its shape.
# * Every aperture (a narrowing that is all that joins a real counter to the outside) keeps at least
#   F_PASS of its width all along, as a smooth channel.
F_PASS, F_HOLE, RES = 0.62, 0.55, 2.0
LOG = []                       # what protect() changed, for proofs
APERTURE = 'ease'


def erode(p, rx, ry, miter=4.0):
    """Shrink a shape by an axis-aligned ellipse (the inverse of grow)."""
    if rx <= 0 or ry <= 0:
        return p
    to = SH.transform(p, (1 / rx, 0, 0, 1 / ry, 0, 0))
    band = pathops.Path(to)
    band.stroke(2.0, pathops.LineCap.BUTT_CAP, pathops.LineJoin.MITER_JOIN, miter)
    band.convertConicsToQuads()
    return SH.transform(SH.difference(to, band), (rx, 0, 0, ry, 0, 0))


def _raster(p, frame):
    from fontTools.pens.recordingPen import RecordingPen
    from outline_util import flatten, raster
    x0, y1, W, H = frame
    rec = RecordingPen(); p.draw(rec)
    return raster(flatten(rec.value, 16), (W, H), lambda q: ((q[0] - x0) / RES, (y1 - q[1]) / RES))


def _branches(skel):
    """Split a skeleton (bool image) into branches between endpoints and junctions."""
    pts = set(zip(*np.nonzero(skel)))
    nb = {p: [(p[0] + dy, p[1] + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy or dx) and (p[0] + dy, p[1] + dx) in pts]
          for p in pts}
    nodes = {p for p, n in nb.items() if len(n) != 2}
    seen, out = set(), []
    for s in nodes:
        for first in nb[s]:
            if (s, first) in seen:
                continue
            path = [s, first]; seen.add((s, first)); prev, cur = s, first
            while cur not in nodes:
                nxt = [q for q in nb[cur] if q != prev and q not in path[-3:]]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]; path.append(cur)
            seen.add((path[-1], path[-2]))
            out.append((path, len(nb[path[0]]), len(nb[path[-1]])))
    return out


def _smooth(a, n=7):
    a = np.asarray(a, float); h = n // 2
    if len(a) <= n:
        return a
    k = np.ones(n) / n
    pad = np.concatenate([np.repeat(a[:1], h, 0), a, np.repeat(a[-1:], h, 0)])
    if a.ndim == 1:
        return np.convolve(pad, k, 'valid')
    return np.stack([np.convolve(pad[:, d], k, 'valid') for d in range(a.shape[1])], 1)


def _channel(pts, radii, step=4.0):
    """A smooth variable-width band along a polyline (font units): the passage kept open. Built
    as a chain of tapered segments (each the hull of two discs), which pathops unites robustly."""
    P = _smooth(pts); r = _smooth(radii)
    if len(P) < 2:
        return None
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if seg[-1] <= 0:
        return SH.circle(P[0, 0], P[0, 1], r[0])
    t = np.linspace(0, seg[-1], max(2, int(seg[-1] / step) + 1))
    P = np.stack([np.interp(t, seg, P[:, 0]), np.interp(t, seg, P[:, 1])], 1); r = np.interp(t, seg, r)
    pieces = []
    for a, b, ra, rb in zip(P[:-1], P[1:], r[:-1], r[1:]):
        d = float(np.linalg.norm(b - a))
        if d < 1e-6 or abs(ra - rb) >= 0.98 * d:
            q = a if ra >= rb else b
            pieces.append(SH.circle(q[0], q[1], max(ra, rb)))
        else:
            pieces.append(SH.wedge(tuple(a), tuple(b), ra, rb))
    return SH.union(*pieces)


def _ease(core, frame_b, neck, across, w, pen, res=1.0):
    """Cut for one aperture: near the neck the pen is eased off, smoothly, to the fraction that leaves
    F_PASS of the regular's width open. The cut is the part of the bold's growth lying beyond the
    eased pen; its edge is a level line of a smooth field, so the walls stay smooth."""
    from skimage.measure import find_contours
    from scipy import ndimage as ndi
    x0, y1, x1, y0 = frame_b
    W, H = int((x1 - x0) / res) + 1, int((y1 - y0) / res) + 1
    fr = (x0, y1, W, H)
    from fontTools.pens.recordingPen import RecordingPen
    from outline_util import flatten, raster
    rec = RecordingPen(); core.draw(rec)
    R = raster(flatten(rec.value, 24), (W, H), lambda q: ((q[0] - x0) / res, (y1 - q[1]) / res))
    rx, ry = pen
    E = ndi.distance_transform_edt(~R, sampling=(res / ry, res / rx))     # distance in pen radii
    r_dir = float(np.hypot(rx * across[0], ry * across[1]))
    lam = min(1.0, (1 - F_PASS) * w / 2 / r_dir)
    if lam >= 0.98:
        return None
    blend = max(3.0 * r_dir, 2.0 * w)
    yy, xx = np.mgrid[:H, :W]
    dn = np.hypot(x0 + (xx + 0.5) * res - neck[0], y1 - (yy + 0.5) * res - neck[1]) / blend
    t = np.clip(dn, 0, 1); omega = lam + (1 - lam) * t * t * (3 - 2 * t)
    phi = np.minimum(E - omega, 0.98 - omega)
    cs = find_contours(np.pad(phi, 1, constant_values=-1), 0.0)
    polys = []
    for c in cs:
        c = c - 1
        if len(c) < 8:
            continue
        pts = [(x0 + (q[1] + 0.5) * res, y1 - (q[0] + 0.5) * res) for q in c[::2]]
        polys.append(SH.polygon(pts))
    return SH.union(*polys) if polys else None


def _cut(bold, cuts):
    """bold minus the cuts, one at a time, so a single awkward cut cannot spoil the rest."""
    for c in cuts:
        try:
            bold = SH.difference(bold, c)
        except pathops.PathOpsError:
            try:
                bold = SH.difference(bold, pathops.simplify(c, fix_winding=True))
            except pathops.PathOpsError:
                pass
    return bold


def _vector_mask(mask, frame):
    """The outline of a raster region, in font units (sub-pixel, marching squares)."""
    from skimage.measure import find_contours
    x0, y1, W, H = frame
    cs = find_contours(np.pad(mask.astype(float), 1), 0.5)
    if not cs:
        return None
    c = max(cs, key=len) - 1
    return SH.polygon([(x0 + (q[1] + 0.5) * RES, y1 - (q[0] + 0.5) * RES) for q in c])


def _radius(p, frame):
    from scipy import ndimage as ndi
    m = _raster(p, frame)
    return float(ndi.distance_transform_edt(m).max()) * RES if m.any() else 0.0


def protect(core, bold, stem, pen, apertures=True):
    """Re-open the counters and apertures of `core` (the regular glyph in the bold's frame) that the
    wider pen of `bold` closed in on. `pen` = (rx, ry), the growth from core to bold."""
    from skimage.morphology import medial_axis, disk
    from scipy import ndimage as ndi
    b = bounds(bold)
    if b is None:
        return bold
    m = 60
    x0, y0, x1, y1 = b[0] - m, b[1] - m, b[2] + m, b[3] + m
    W, H = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
    frame = (x0, y1, W, H)
    R = _raster(core, frame); B = _raster(bold, frame)
    # Gaps under a quarter of a stem are where two strokes meet in the drawing but the trace left a
    # sliver between them: a counter behind one is still a counter, and the bold closes the sliver.
    hair = max(1, int(round(0.12 * stem / RES)))
    BG = ndi.binary_opening(~R, disk(hair).astype(bool))
    open_bold = ndi.distance_transform_edt(~B)
    dist = ndi.distance_transform_edt(BG)
    unit = lambda q: (x0 + (q[1] + 0.5) * RES, y1 - (q[0] + 0.5) * RES)
    cuts = []
    lab, n = ndi.label(BG)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    # counters
    for k in range(1, n + 1):
        if k in border:
            continue
        region = lab == k
        r_reg = float(dist[region].max()) * RES
        if r_reg < 0.15 * stem or open_bold[region].max() * RES >= F_HOLE * r_reg:
            continue
        shape = _vector_mask(ndi.binary_dilation(region, disk(hair + 2).astype(bool)), frame)
        if shape is None:
            continue
        C = SH.difference(shape, core)
        lo, hi = 0.0, 1.0
        for _ in range(7):
            mid = (lo + hi) / 2
            if _radius(erode(C, mid * pen[0], mid * pen[1]), frame) >= F_HOLE * r_reg:
                lo = mid
            else:
                hi = mid
        cuts.append(erode(C, lo * pen[0], lo * pen[1]) if lo > 0 else C)
        LOG.append(('counter', unit(np.unravel_index(np.argmax(np.where(region, dist, 0)), dist.shape)), round(r_reg), round(lo, 3)))
    # apertures
    skel, dist = medial_axis(BG, return_distance=True, rng=0)
    for path, d0, d1 in (_branches(skel) if apertures else []):
        if len(path) < 5:
            continue
        d = np.array([dist[q] for q in path])
        i = int(np.argmin(d))
        if not (0 < i < len(d) - 1 and d[i] < 0.9 * d[0] and d[i] < 0.9 * d[-1]) or 2 * d[i] * RES < 0.24 * stem:
            continue
        if not any(open_bold[q] < F_PASS * dist[q] for q in path):
            continue                                        # the bold left this one open enough
        # is this narrowing all that joins a real counter to the rest of the background?
        block = BG.copy()
        yy, xx = np.ogrid[:H, :W]
        block[(yy - path[i][0]) ** 2 + (xx - path[i][1]) ** 2 <= (d[i] + 2) ** 2] = False
        bl, _ = ndi.label(block)
        a, z = bl[path[max(0, i - int(d[i]) - 4)]], bl[path[min(len(path) - 1, i + int(d[i]) + 4)]]
        if not a or not z or a == z:
            continue
        small = min((bl == a), (bl == z), key=lambda r: r.sum())
        if small.sum() * RES * RES < 0.5 * stem * stem or dist[small].max() * RES < 0.3 * stem:
            continue
        if APERTURE == 'channel':
            c = _channel([unit(q) for q in path], [F_PASS * dist[q] * RES for q in path])
        else:
            a_, b_ = path[max(0, i - 3)], path[min(len(path) - 1, i + 3)]
            tx, ty = unit(b_)[0] - unit(a_)[0], unit(b_)[1] - unit(a_)[1]; tn = math.hypot(tx, ty) or 1
            c = _ease(core, (x0, y1, x1, y0), unit(path[i]), (-ty / tn, tx / tn), 2 * d[i] * RES, pen)
        if c is not None:
            cuts.append(c)
            LOG.append(('aperture', unit(path[i]), round(2 * d[i] * RES), round(float(small.sum()) * RES * RES)))
    return _cut(bold, cuts) if cuts else bold
