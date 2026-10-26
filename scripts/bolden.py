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


# Narrower than SLIVER stems, a gap is a tracing sliver, not a drawn one. On the flyer, a photocopy,
# anything under a quarter of a stem is; the original sheets show drawn open joins and openings of
# 0.13-0.22 stem (Kilfane's r and 9, Tuam's a, o and 0), so outlines traced from them pass 0.05.
SLIVER = 0.24


def embolden(p, rx, ry, k, xh, stem, separate=True, keep_open=True, apertures=True, sliver=SLIVER):
    # a zero-area contour left by a trace would grow into a stray dot
    parts = [q for q in (components(p) if separate else [p]) if abs(area(q)) > 1]
    wide = [SH.transform(q, (k, 0, 0, 1, 0, 0)) for q in parts]
    bold = heights_back(SH.union(*[grow(q, rx, ry) for q in wide]), xh, ry)
    if not keep_open:
        return bold
    # the regular in the bold's frame: same widening and height map, no growth
    return protect(heights_back(SH.union(*wide), xh, ry), bold, stem, (rx, ry), apertures, sliver)


# ---------------------------------------------------------------------------------------------
# Keeping the bold open. A wider pen fills every narrow background space at once: the eye of an e,
# the counters of a $, the opening of a c. A designer keeps these open by hand, drawing the inside
# of a small counter with a lighter pen, or thinning the strokes either side of an aperture.
# The spaces are read from the regular glyph's background, after closing the hairline gaps where
# two strokes meet but the trace left a sliver between them (those close in the bold, as they should).
# * Every enclosed counter keeps at least F_HOLE of its inscribed radius and F_AREA of its area: where
#   the bold took more, the counter is drawn again as the regular's counter shrunk by a lighter pen, so
#   it keeps its shape. (A small pointed counter, Q's where the tail crosses the bowl, loses area far
#   faster than radius.)
# * Every aperture (a narrowing that is all that joins a real counter to the outside) keeps at least
#   F_PASS of its width all along, as a smooth channel.
# * Every space the regular leaves open to the outside stays open: an open join the bold still closes
#   is kept as a hairline crack along the regular's passage (_reopen).
F_PASS, F_HOLE, F_AREA, RES = 0.62, 0.55, 0.36, 2.0
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


def closes(core, bold):
    """Did growing `core` into `bold` join pieces, close or open a counter, or squeeze one below F_AREA?"""
    def holes(p):
        a = [area(c) for c in contours(p)]
        return sorted(-x for x in a if x < 0) if any(x > 0 for x in a) else sorted(x for x in a if x > 0)
    hc, hb = holes(core), holes(bold)
    return pieces(core) != pieces(bold) or len(hc) != len(hb) or bool(hc) and hb[0] < F_AREA * hc[0]


def _background(R, stem, sliver):
    """The regular's background (raster), with the tracing slivers narrower than `sliver` stems closed."""
    from skimage.morphology import disk
    from scipy import ndimage as ndi
    hair = int(round(sliver / 2 * stem / RES))
    return ndi.binary_opening(~R, disk(hair).astype(bool)) if hair else ~R


def protect(core, bold, stem, pen, apertures=True, sliver=SLIVER):
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
    # Gaps under `sliver` stems are where two strokes meet in the drawing but the trace left a sliver
    # between them: a counter behind one is still a counter, and the bold closes the sliver.
    BG = _background(R, stem, sliver)
    hair = max(1, int(round(sliver / 2 * stem / RES)))
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
        if r_reg < min(0.15, 2 * sliver) * stem or (open_bold[region].max() * RES >= F_HOLE * r_reg and
                                         (region & ~B).sum() >= F_AREA * region.sum()):
            continue
        shape = _vector_mask(ndi.binary_dilation(region, disk(hair + 2).astype(bool)), frame)
        if shape is None:
            continue
        C = SH.difference(shape, core)
        a_reg = abs(area(C))
        lo, hi = 0.0, 1.0
        for _ in range(7):
            mid = (lo + hi) / 2
            e = erode(C, mid * pen[0], mid * pen[1])
            if _radius(e, frame) >= F_HOLE * r_reg and abs(area(e)) >= F_AREA * a_reg:
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
        if not (0 < i < len(d) - 1 and d[i] < 0.9 * d[0] and d[i] < 0.9 * d[-1]) or 2 * d[i] * RES < sliver * stem:
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
    out = _cut(bold, cuts) if cuts else bold
    if apertures:
        out = _reopen(core, out, stem, pen, sliver)
    if pieces(out) < pieces(core):
        out = _separate(core, out, pen)
    # a cut can leave specks of either kind; two growth fronts that nearly meet leave a pinhole
    return _despeckle(out, core, stem) if out is not bold else _despeckle(bold, core, stem, holes_only=True)


def _reopen(core, bold, stem, pen, sliver, tries=3):
    """The openings the bold still closes, found by topology rather than by shape: a background
    region that the regular leaves open to the outside but the bold encloses. The original sheets
    have open joins that run as a long slit beside a stem (Kilfane's r and 9), which no single
    narrowing describes, so each is reopened as a hairline crack along the regular's own passage:
    the cheapest path from the region to the outside through the widest background, F_PASS of its
    narrowest width wide wherever the bold has closed in on it. The bold keeps its weight either side."""
    from skimage.morphology import disk
    from skimage.graph import MCP_Geometric
    from scipy import ndimage as ndi
    edge = lambda L: set(np.unique(np.concatenate([L[0], L[-1], L[:, 0], L[:, -1]]))) - {0}
    for attempt in range(tries):
        b = bounds(bold)
        if b is None:
            return bold
        m = 60 + 2 * max(pen)
        x0, y0, x1, y1 = b[0] - m, b[1] - m, b[2] + m, b[3] + m
        W, H = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
        frame = (x0, y1, W, H)
        unit = lambda q: (x0 + (q[1] + 0.5) * RES, y1 - (q[0] + 0.5) * RES)
        R = _raster(core, frame); B = _raster(bold, frame)
        BG = _background(R, stem, sliver)
        lr, _ = ndi.label(BG); outside = list(edge(lr))
        lb, nb = ndi.label(~B); bb = edge(lb)
        closed = []
        for k in range(1, nb + 1):
            region = lb == k
            if k in bb or region.sum() * RES * RES < (0.1 * stem) ** 2:     # smaller is a speck
                continue
            under = lr[region & BG]
            if under.size and np.isin(under, outside).mean() > 0.5:
                closed.append(region & BG)
        if not closed:
            return bold
        dist = ndi.distance_transform_edt(BG)
        open_bold = ndi.distance_transform_edt(~B)
        far = np.isin(lb, list(bb)) & (dist * RES >= 2 * max(pen) + 0.25 * stem)    # well clear, outside the bold
        cost = np.where(BG, 1.0 / (dist + 0.5) ** 2, np.inf)
        cuts = []
        for seed in closed:
            if not far.any():
                break
            start = np.unravel_index(np.argmax(np.where(seed, dist, -1)), dist.shape)
            mcp = MCP_Geometric(cost, fully_connected=True)
            costs, _ = mcp.find_costs([start])
            end = np.unravel_index(np.argmin(np.where(far, costs, np.inf)), costs.shape)
            if not np.isfinite(costs[end]):
                continue
            path = np.array(mcp.traceback(end))
            # the stretch the bold has closed in on, and the passage's narrowest width there
            d = dist[path[:, 0], path[:, 1]]; ob = open_bold[path[:, 0], path[:, 1]]
            shut = np.nonzero(ob < F_PASS * d + 1)[0]
            if not len(shut):
                continue
            i0, i1 = max(0, shut[0] - 6), min(len(path) - 1, shut[-1] + 6)
            w = 2 * float(d[shut[0]:shut[-1] + 1].min()) * RES
            r = F_PASS * w / 2 * (1 + 0.25 * attempt)
            pts = [unit(q) for q in path[i0:i1 + 1]]
            c = _channel(pts, [r] * len(pts))
            if c is not None:
                cuts.append(c)
                LOG.append(('opening', unit(path[shut[0] + int(np.argmin(d[shut[0]:shut[-1] + 1]))]), round(w), attempt))
        if not cuts:
            return bold
        bold = _cut(bold, cuts)
    return bold


def _separate(core, bold, pen, close=False, share=None):
    """Pieces the regular keeps apart that the bold joins (the dot of a ! that sits close to its
    stroke): cut apart again along the line midway between them, F_PASS of their gap wide, so both
    keep their weight and the gap its place. With `close`, pieces the bold brings within that width
    without joining them are set apart the same way (Céilí Study 4's ? and !, build_original_study),
    `share` of the regular's gap wide where given."""
    share = F_PASS if share is None else share
    from scipy import ndimage as ndi
    from skimage.measure import find_contours
    b = bounds(bold)
    m = 20 + 2 * max(pen)
    x0, y0, x1, y1 = b[0] - m, b[1] - m, b[2] + m, b[3] + m
    W, H = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
    frame = (x0, y1, W, H)
    R = _raster(core, frame); B = _raster(bold, frame)
    lr, nr = ndi.label(R, structure=np.ones((3, 3)))
    lb, _ = ndi.label(B, structure=np.ones((3, 3)))
    dist = [ndi.distance_transform_edt(lr != k) * RES for k in range(1, nr + 1)]
    nearest = np.argmin(np.stack(dist), 0) if nr > 1 else np.zeros(R.shape, int)
    reach = 2 * max(pen)
    cuts = []
    for i in range(nr):
        for j in range(i + 1, nr):
            ki, kj = set(np.unique(lb[lr == i + 1])) - {0}, set(np.unique(lb[lr == j + 1])) - {0}
            if not ki & kj and not close:
                continue                                    # still apart in the bold
            gap = float((dist[i] + dist[j])[~R].min())
            if gap < 1:
                continue
            # a smooth field whose zero line runs either side of the midline, share * gap apart
            field = share * gap - np.abs(dist[i] - dist[j])
            near = (dist[i] < gap + reach) & (dist[j] < gap + reach) & np.isin(nearest, (i, j))
            field = np.where(near, field, -1.0)
            polys = []
            for c in find_contours(np.pad(field, 1, constant_values=-1), 0.0):
                c = c - 1
                if len(c) >= 8:
                    polys.append(SH.polygon([(x0 + (q[1] + 0.5) * RES, y1 - (q[0] + 0.5) * RES) for q in c[::2]]))
            if polys:
                cuts.append(SH.union(*polys))
                LOG.append(('apart', (i, j), round(gap)))
    return _cut(bold, cuts) if cuts else bold


def _despeckle(p, core, stem, holes_only=False):
    """Drop specks under a tenth of a stem square that the regular does not have: ink a cut left
    beside the bold's edge, or a pinhole where two growth fronts nearly met. A small hole inside one
    of the regular's counters is that counter, and a small piece on the regular's ink is drawn."""
    cs = contours(p)
    thr = (0.1 * stem) ** 2
    if all(abs(area(c)) >= thr for c in cs):
        return p
    outer = [c for c in contours(core) if area(c) > 0]
    counters = SH.difference(SH.union(*outer), core) if outer else pathops.Path()
    inter = lambda a, b: abs(area(pathops.op(a, b, pathops.PathOp.INTERSECTION, fix_winding=True)))
    keep = []
    for c in cs:
        a = area(c)
        if abs(a) >= thr or (holes_only and a > -1) or inter(c, core if a > 0 else counters) > 0.5 * abs(a):
            keep.append(c)
    if len(keep) == len(cs):
        return p
    return pathops.simplify(concat(keep), fix_winding=True, keep_starting_points=False, clockwise=False)
