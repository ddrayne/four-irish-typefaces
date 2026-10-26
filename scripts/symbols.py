"""Symbols and extra punctuation drawn in each face's stroke weight."""
import math
import numpy as np
import pathops
import shapes as SH
from glyphs import bounds, translate
from marks import stroke_polyline, stroke_cubics, centre


# Carrick's letters are cut, not written: its small figures and letters (superiors, fractions, ª º, ™,
# ©, @, ¥, §) keep their cut corners (a mitred offset, not a rounded one), and a small counter or
# opening (the 4 and the 3 of ¾) narrows by at most a quarter of its own width on each side rather than
# shutting. Set per face by make_symbols; the other faces keep the round offset.
CUT = False


def embolden(p, d):
    """Offset an outline by d units (negative thins it)."""
    if abs(d) < 0.5:
        return p
    s = pathops.Path(p)
    if CUT:
        s.stroke(2 * abs(d), pathops.LineCap.BUTT_CAP, pathops.LineJoin.MITER_JOIN, 2.0)
    else:
        s.stroke(2 * abs(d), pathops.LineCap.ROUND_CAP, pathops.LineJoin.ROUND_JOIN, 4.0)
    s.convertConicsToQuads()
    out = SH.union(p, s) if d > 0 else SH.difference(p, s)
    return _keep_openings(p, _keep_counters(p, out, d), d) if CUT and d > 0 else out


def _keep_openings(p, grown, d, share=0.25, res=0.5):
    """`grown` (p offset by d) with every narrow opening of p (the mouth of the small 3's lower bowl)
    kept open: through an opening narrower than d / share, the growth on each side is limited to
    `share` of its width. An opening is a narrowing that divides p's background at that width (a corner
    of the ink does not); the channel kept runs along the widest way through it."""
    from scipy import ndimage as ndi
    from skimage.graph import route_through_array
    from skimage import measure
    from outline_util import flatten, raster
    from fontTools.pens.recordingPen import RecordingPen, replayRecording
    from curvefit import curves_to_recording
    from curvefit3 import contour_to_curves4
    from glyphs import SCALE
    b = bounds(grown)
    if b is None:
        return grown
    m = d + 8
    x0, y1 = b[0] - m, b[3] + m
    W, H = int((b[2] - b[0] + 2 * m) / res) + 1, int((b[3] - b[1] + 2 * m) / res) + 1
    rec = RecordingPen(); p.draw(rec)
    bg = ~(raster(flatten(rec.value), (W, H), lambda q: ((q[0] - x0) / res, (y1 - q[1]) / res)) > 0)
    D = ndi.distance_transform_edt(bg) * res                  # distance to p's ink, font units
    reach = d / (2 * share)                                   # half-widths under this are limited
    lab, n = ndi.label(bg); wl, _ = ndi.label(bg & (D >= reach))
    cost = np.where(bg, 1.0 / (D + 0.5) ** 2, 1e6)
    channel = np.zeros(bg.shape, bool)
    yy, xx = np.mgrid[:H, :W]
    for k in range(1, n + 1):                                  # each background region of p that
        parts = sorted((j for j in np.unique(wl[lab == k]) if j), key=lambda j: -(wl == j).sum())
        anchor = lambda j: np.unravel_index(np.argmax(np.where(wl == j, D, -1)), D.shape)
        for j in parts[1:]:                                    # a narrowing divides
            path, _ = route_through_array(cost, anchor(parts[0]), anchor(j), fully_connected=True)
            for r, c in path:
                if D[r, c] < reach:
                    rad = (D[r, c] - share * 2 * D[r, c]) / res
                    channel |= (yy - r) ** 2 + (xx - c) ** 2 <= rad * rad
    channel &= bg
    if not channel.any():
        return grown
    s = SCALE['carrick']; curves = []
    for c in measure.find_contours(np.pad(ndi.gaussian_filter(channel.astype(float), 1.0), 2), 0.5):
        xy = np.column_stack((x0 + (c[:, 1] - 2 + 0.5) * res, y1 - (c[:, 0] - 2 + 0.5) * res))
        if len(xy) > 8:
            fit = contour_to_curves4(xy[:-1] / [s, -s], cutoff=6, corner_deg=55, rms_tol=.07, max_tol=.22,
                                     line_tol=.18, line_bulge=.055, line_min=4.5, snap_deg=1.5)
            curves.append([np.asarray(q) * [s, -s] for q in fit])
    cut = pathops.Path(); replayRecording(curves_to_recording(curves), cut.getPen())
    cut = pathops.simplify(cut, fix_winding=True, keep_starting_points=False, clockwise=False)
    return SH.difference(grown, cut)


def _keep_counters(p, grown, d, share=0.25):
    """`grown` (p offset by d) with each counter of p shrunk by no more than `share` of its own width
    (four times its area over its perimeter: the diameter for a round counter)."""
    from glyphs import contours
    from fontTools.pens.areaPen import AreaPen
    from fontTools.pens.perimeterPen import PerimeterPen
    out = grown
    for c in contours(SH.union(p)):
        ap = AreaPen(); c.draw(ap)
        if ap.value >= 0:                       # an outer contour (counter-clockwise)
            continue
        pp = PerimeterPen(); c.draw(pp)
        keep = min(d, share * 4 * -ap.value / max(pp.value, 1e-9))
        if keep >= d - 0.5:
            continue
        hole = pathops.simplify(c, fix_winding=True, keep_starting_points=False, clockwise=False)   # filled
        s = pathops.Path(hole)
        s.stroke(2 * keep, pathops.LineCap.BUTT_CAP, pathops.LineJoin.MITER_JOIN, 2.0); s.convertConicsToQuads()
        out = SH.difference(out, SH.difference(hole, s))
    return out


def scaled(p, k, S, target=0.82, S_to=None):
    """Scale an outline (stems S thick) by k and re-embolden so its stems are about target*S_to."""
    q = SH.transform(p, (k, 0, 0, k, 0, 0))
    return embolden(q, (target * (S_to or S) - k * S) / 2)


def inside_ring(p, cx, cy, r_in, gap):
    """Shrink p about (cx, cy), if need be, until all of it sits gap inside a circle of radius r_in."""
    from fontTools.pens.recordingPen import RecordingPen
    from outline_util import flatten
    rec = RecordingPen(); p.draw(rec)
    far = max(math.hypot(x - cx, y - cy) for poly in flatten(rec.value, 16) for x, y in poly)
    k = (r_in - gap) / far
    if k >= 1:
        return p
    return SH.transform(p, (k, 0, 0, k, cx - k * cx, cy - k * cy))


def bar(style, x0, x1, yc, t):
    if style == 'round':
        return SH.capsule(x0 + t / 2, x1 - t / 2, yc, t)
    if style == 'chisel':
        return SH.slanted_bar(x0, x1, yc, t, cut=0.22 * t)
    return SH.polygon([(x0, yc - t / 2), (x1, yc - t / 2), (x1, yc + t / 2), (x0, yc + t / 2)])


def vbar(style, xc, y0, y1, t):
    p = bar(style, y0, y1, 0, t)
    return SH.transform(p, (0, 1, 1, 0, xc, 0))


def ring(cx, cy, r, t):
    return SH.difference(SH.ellipse(cx, cy, r, r), SH.ellipse(cx, cy, r - t, r - t))


def chevron(style, w, h, t, left=True):
    pts = [(w, h), (0, h / 2), (w, 0)] if left else [(0, h), (w, h / 2), (0, 0)]
    return stroke_polyline(pts, t, style)


def _perimeter(p):
    from fontTools.pens.recordingPen import RecordingPen
    from outline_util import flatten
    rec = RecordingPen(); p.draw(rec)
    return sum(float(np.hypot(*np.diff(np.array(poly + poly[:1]), axis=0).T).sum()) for poly in flatten(rec.value, 16))


def _holes(p):
    from fontTools.pens.areaPen import AreaPen
    from glyphs import contours
    out = []
    for c in contours(p):
        ap = AreaPen(); c.draw(ap)
        if ap.value < 0:
            out.append(-ap.value)
    return out


def section(s, S, Ss, top):
    """Two s interlaced so the lower bowl of one and the upper bowl of the other close into the
    loop at the middle, their terminals tucked into each other's strokes. The overlap is found by
    trial: the tidiest union (shortest outline) that keeps one clear loop, at the heaviest weight
    that allows one (a heavy s is lightened, then narrowed, a step at a time)."""
    def placements(s2, w, sh, pfs, dxs):
        best = None
        for pf in pfs:
            for dxf in dxs:
                u = SH.union(translate(s2, 0, pf * sh), translate(s2, dxf * w, 0))
                hs = _holes(u)
                if len(hs) != 1 or hs[0] < 0.06 * w * sh:
                    continue
                score = _perimeter(u) / (1 + pf)
                if best is None or score < best[0]:
                    best = (score, u, pf, dxf)
        return best
    for tgt in (0.90, 0.84, 0.78, 0.72, 0.66):
        for kx in (1.0, 0.9):
            s2 = scaled(s, 0.80, S, tgt, Ss)
            if kx != 1.0:
                s2 = SH.transform(s2, (kx, 0, 0, 1, 0, 0))
            b = bounds(s2); w, sh = b[2] - b[0], b[3] - b[1]; s2 = translate(s2, -b[0], -b[1])
            best = placements(s2, w, sh, np.arange(0.36, 0.77, 0.04), np.arange(-0.18, 0.181, 0.06))
            if best:
                _, _, pf, dxf = best
                best = placements(s2, w, sh, np.arange(pf - 0.02, pf + 0.021, 0.02), np.arange(dxf - 0.03, dxf + 0.031, 0.03)) or best
                u = best[1]; ub = bounds(u)
                return translate(u, -ub[0], top - ub[3])
    return None


def drawn_section(H, W, t, style):
    """A § drawn as one s-stroke and its half-turn: the lower curve of the first and the upper curve
    of the second close into the loop at the middle. For a face whose own s is too black to interlace."""
    m = t / 2; yc = H / 2; hl = 0.20 * H
    segs = [((W - m, H - 0.05 * H), (0.88 * W, H - m), (0.50 * W, H - m)),
            ((0.12 * W, H - m), (m, H - 0.05 * H), (m, H - 0.20 * H)),
            ((m, H - 0.36 * H), (W - m, yc + 0.16 * H), (W - m, yc - 0.02 * H)),
            ((W - m, yc - 0.15 * H), (0.86 * W, yc - hl), (0.50 * W, yc - hl)),
            ((0.22 * W, yc - hl), (m + 0.02 * W, yc - hl + 0.06 * H), (m + 0.04 * W, yc - hl + 0.12 * H))]
    a = stroke_cubics((W - m, H - 0.24 * H), segs, t, style)
    return SH.union(a, SH.rotate(a, 180, W / 2, H / 2))


def pointed_brace(top, bottom, w, reach, point=0.55, cusp=0.45, corner=0.35):
    """A left brace drawn as one outline, in the stroked brace's place: stems w wide (outer edge at x = 0),
    rounded outer corners into square arm ends at x = reach, and a point at the middle that juts beyond the
    stems by `point` x w, with the inner cusp `cusp` x w inside them, so the waist is (1 + point - cusp) x w
    wide wherever it is cut. top/bottom: the outer edges of the arms."""
    mid = (top + bottom) / 2; hh = (top - bottom) / 2
    xo, xi, xe = 0.0, w, max(reach, w)
    xa, xc = xo - point * w, xi - cusp * w             # the point's tip; the inner cusp
    vo = corner * hh                                   # the outer corner's height
    vi = max(vo - w, 0.0) * 0.5                        # the inner corner's, inside the arm
    h1 = 0.30 * hh                                     # where the stems turn towards the point
    a, c = 0.35 * (xo - xa), 0.35 * (xi - xc)          # the point's and the cusp's handles, at 45 degrees
    p = pathops.Path()
    p.moveTo(xe, top)
    p.cubicTo(xe - 0.55 * (xe - xo), top, xo, top - 0.45 * vo, xo, top - vo)
    p.lineTo(xo, mid + h1)
    p.cubicTo(xo, mid + 0.45 * h1, xa + a, mid + a, xa, mid)
    p.cubicTo(xa + a, mid - a, xo, mid - 0.45 * h1, xo, mid - h1)
    p.lineTo(xo, bottom + vo)
    p.cubicTo(xo, bottom + 0.45 * vo, xe - 0.55 * (xe - xo), bottom, xe, bottom)
    p.lineTo(xe, bottom + w)
    p.cubicTo(xi + 0.45 * (xe - xi), bottom + w, xi, bottom + w + 0.45 * vi, xi, bottom + w + vi)
    p.lineTo(xi, mid - h1)
    p.cubicTo(xi, mid - 0.45 * h1, xc + c, mid - c, xc, mid)
    p.cubicTo(xc + c, mid + c, xi, mid + 0.45 * h1, xi, mid + h1)
    p.lineTo(xi, top - w - vi)
    p.cubicTo(xi, top - w - 0.45 * vi, xi + 0.45 * (xe - xi), top - w, xe, top - w)
    p.close()
    return pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)


# ---------------------------------------------------------------- % ‰ # in the figures' weight
# A face whose figures are black (Carrick's, Tuam's: stems a third of the x-height) sets % and ‰ beside
# them: drawn from its small zeros at their own weight and a thin rule, they print half as black as the
# figures. With FIGURE_PERCENT a face's % and ‰ are its own 0 made small with strokes PERCENT_WEIGHT of the
# figure stem (the 1's), a slash of SLASH_WEIGHT, and # has bars of NUMBER_WEIGHT.
PERCENT_WEIGHT, SLASH_WEIGHT, NUMBER_WEIGHT, PERCENT_ZERO, PERCENT_SLOPE, PERCENT_GAP = 0.63, 0.58, 0.50, 0.46, 0.62, 0.35


def _outline_points(p, step=3.0):
    from fontTools.pens.recordingPen import RecordingPen
    from outline_util import flatten
    rec = RecordingPen(); p.draw(rec); pts = []
    for poly in flatten(rec.value, 24):
        a = np.array(poly + poly[:1], float)
        for u, v in zip(a[:-1], a[1:]):
            n = max(1, int(np.hypot(*(v - u)) / step))
            pts.append(u + (v - u) * np.linspace(0, 1, n, endpoint=False)[:, None])
    return np.vstack(pts)


def clearance(a, b):
    """The narrowest white between two outlines (0 where they overlap)."""
    from scipy.spatial import cKDTree
    from fontTools.pens.areaPen import AreaPen
    ap = AreaPen(); SH.op(a, b, pathops.PathOp.INTERSECTION).draw(ap)
    if abs(ap.value) > 1:
        return 0.0
    return float(cKDTree(_outline_points(a)).query(_outline_points(b))[0].min())


def figure_stem(P, top):
    from letters import stem_at
    a, b = stem_at(P['one'], 0.45 * top, 'left')
    return b - a


def figure_zero(f, P, top, T):
    """The face's 0 made small (PERCENT_ZERO of the figure height) with its thick sides T: scaled, then
    grown by a pen in the zero's own contrast (its thinnest stroke against its sides) that moves the
    zero's own nodes, so its corners stay cut and a cut through it (Tuam's) keeps its width
    (bolden.grow_nodes); a counter the pen would still shut is kept open as the bold keeps them."""
    import bolden
    from letters import stem_at
    zero = P['zero']; zb = bounds(zero); h0 = zb[3] - zb[1]; cx, cy = (zb[0] + zb[2]) / 2, (zb[1] + zb[3]) / 2
    s0, s1 = stem_at(zero, cy, 'left'); w0 = s1 - s0
    turned = SH.transform(zero, (0, 1, 1, 0, 0, 0))            # x <-> y: runs down the middle of the 0
    v = [stem_at(turned, cx, side) for side in ('left', 'right')]
    c = float(np.clip(min(b - a for a, b in v) / w0, 0.35, 1.0))
    k = (PERCENT_ZERO * top - c * T) / (h0 - c * w0)
    rx = max(0.0, (T - k * w0) / 2); ry = c * rx
    q = SH.transform(zero, (k, 0, 0, k, 0, 0))
    z = bolden.grow_nodes(q, rx, ry, fallback=bolden.grow, keep_cuts=0.3 * T) if rx > 0.5 else q
    if rx > 0.5 and bolden.closes(q, z):
        z = bolden.protect(q, z, T, (rx, ry), sliver=getattr(f, 'SLIVER', bolden.SLIVER))
    b = bounds(z)
    return translate(z, -b[0], -b[1])


def figure_signs(f, P, top, st):
    """% and ‰ from the face's own 0 and # with bars in the figures' weight (FIGURE_PERCENT): the zeros
    PERCENT_WEIGHT of the figure stem, a slash SLASH_WEIGHT (level ends, as the faces' own slashes have)
    set between them, the zeros and slash parted by PERCENT_GAP of the figure stem; ‰'s third zero
    follows the second a third of the zeros' weight away. #: the release construction's counter, with
    bars NUMBER_WEIGHT of the stem."""
    xh = f.xh; w1 = figure_stem(P, top)
    T, Ts, Tb = PERCENT_WEIGHT * w1, SLASH_WEIGHT * w1, NUMBER_WEIGHT * w1
    z = figure_zero(f, P, top, T); zb = bounds(z); zw, zh = zb[2], zb[3]
    # the slash runs the figure height through the middle at PERCENT_SLOPE; each zero is slid towards it
    # until the white between them is `gap`
    run = top * PERCENT_SLOPE / 2
    if st == 'round':
        sl = stroke_polyline([(-run, 0), (run, top)], Ts, st)
    else:
        hw = Ts / 2 * math.hypot(2 * run, top) / top            # half its level width
        sl = SH.polygon([(-run - hw, 0), (-run + hw, 0), (run + hw, top), (run - hw, top)])
    gap = PERCENT_GAP * w1

    def slid(y0, toward):                    # the zero at height y0, as near the slash as `gap` allows
        lo, hi = 0.0, 2 * zw + 2 * run
        for _ in range(14):
            mid = (lo + hi) / 2
            q = translate(z, -mid - zw if toward > 0 else mid, y0)
            lo, hi = (lo, mid) if clearance(sl, q) >= gap else (mid, hi)
        return translate(z, -hi - zw if toward > 0 else hi, y0)
    up, dn = slid(top - zh, 1), slid(0, -1)
    pc = SH.union(up, dn, sl)
    pm = SH.union(pc, translate(dn, zw + max(0.06 * xh, T / 3), 0))
    # #
    t = f.hyphen_thick; h = top; sh = math.tan(math.radians(12))
    ci, cv = 0.30 * xh - 0.85 * t, 0.33 * h - 0.85 * t        # the release #'s counter, kept
    dx = ci + Tb; xs = [0.18 * xh, 0.18 * xh + dx]
    verts = [stroke_polyline([(x, 0), (x + sh * h, h)], Tb, st) for x in xs]
    # each bar centred on the strokes at its own height (the sloped strokes move right as they rise)
    mid, half = 0.18 * xh + dx / 2, 0.22 * xh + dx / 2
    hb = [bar(st, mid + sh * y - half, mid + sh * y + half, y, Tb) for y in (h / 2 + s * (cv + Tb) / 2 for s in (-1, 1))]
    return {'numbersign': (SH.union(*verts, *hb), 'sheared grid, bars half the figure stem'),
            'percent': (pc, 'the face\'s 0 made small in the figures\' weight + slash'),
            'perthousand': (pm, 'percent + zero')}


def counter_widths(p, res=1.0):
    """The inscribed width of each closed counter of p."""
    from scipy import ndimage as ndi
    from fontTools.pens.recordingPen import RecordingPen
    from outline_util import flatten, raster
    b = bounds(p); x0, y1 = b[0] - 4, b[3] + 4
    W, H = int((b[2] - b[0] + 8) / res) + 1, int((b[3] - b[1] + 8) / res) + 1
    rec = RecordingPen(); p.draw(rec)
    bg = ~(raster(flatten(rec.value), (W, H), lambda q: ((q[0] - x0) / res, (y1 - q[1]) / res)) > 0)
    lab, n = ndi.label(bg); edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    return [2 * res * ndi.distance_transform_edt(lab == k).max() for k in range(1, n + 1)
            if k not in edge and (lab == k).sum() > 2]


def clear_bar(c, bar, x, least):
    """Where the ¢ bar (bar(x), at x) leaves no piece of the c's counter narrower than `least` closed off
    beside it: the nearest place towards the c's back, else the nearest beyond. (Carrick's c is open
    behind a narrow inner curve, and the bar at the middle shut a lens of it off.)"""
    w = bounds(c)[2] - bounds(c)[0]
    for dx in list(np.arange(0, -0.3 * w, -2.0)) + list(np.arange(2, 0.3 * w, 2.0)):
        if all(v >= least for v in counter_widths(SH.union(c, bar(x + dx)))):
            return x + dx + (np.sign(dx) * 0.01 * w if dx else 0)
    return x


def make_symbols(f):
    global CUT
    CUT = f.key == 'carrick'
    P, S, xh, st = f.P, f.S, f.xh, f.style
    # Small glyphs (superiors, fractions, the letters in ® and ©) in a bold are drawn lighter in
    # proportion than its full-size letters, or their counters close: halfway to the regular's stem.
    Ss = S if not f.bold else f.S_regular + 0.5 * (S - f.S_regular)
    fig, asc, cap = f.fig, f.asc, f.cap
    top = fig if f.cfg['lining'] else xh * 1.05      # height of "figure-size" symbols
    t = f.hyphen_thick                                # bar weight for math and rules
    yc = f.hyphen_yc                                  # math axis = hyphen centre
    made = {}

    def put(name, p, how):
        P[name] = f.norm_x(p); made[name] = how

    # ---------------------------------------------------------------- math
    L = 0.95 * xh
    put('plus', SH.union(bar(st, 0, L, yc, t), vbar(st, L / 2, yc - L / 2, yc + L / 2, t)), 'bars')
    put('minus', bar(st, 0, L, yc, t), 'bar')
    put('equal', SH.union(bar(st, 0, L, yc - 1.15 * t, t), bar(st, 0, L, yc + 1.15 * t, t)), 'bars')
    put('multiply', SH.rotate(SH.union(bar(st, 0, 0.78 * L, yc, t), vbar(st, 0.39 * L, yc - 0.39 * L, yc + 0.39 * L, t)),
                              45, 0.39 * L, yc), 'rotated plus')
    dot = SH.transform(f.period, (0.85, 0, 0, 0.85, 0, 0)); db = bounds(dot); dw = db[2] - db[0]
    put('divide', SH.union(bar(st, 0, L, yc, t), translate(dot, L / 2 - dw / 2 - db[0], yc + 1.4 * t - db[1]),
                           translate(dot, L / 2 - dw / 2 - db[0], yc - 1.4 * t - db[3])), 'bar + dots')
    put('plusminus', SH.union(bar(st, 0, L, yc + 0.18 * xh, t), vbar(st, L / 2, yc + 0.18 * xh - L / 2.2, yc + 0.18 * xh + L / 2.2, t),
                              bar(st, 0, L, yc + 0.18 * xh - L / 2.2 - 1.6 * t, t)), 'plus over bar')
    cw, chh = 0.66 * xh, 0.84 * xh
    put('less', translate(chevron(st, cw, chh, t, True), 0, yc - chh / 2), 'chevron')
    put('greater', translate(chevron(st, cw, chh, t, False), 0, yc - chh / 2), 'chevron')
    put('lessequal', SH.union(translate(chevron(st, cw, 0.62 * chh, t, True), 0, yc - 0.18 * chh),
                              bar(st, 0, cw, yc - 0.18 * chh - 1.6 * t, t)), 'chevron + bar')
    put('greaterequal', SH.union(translate(chevron(st, cw, 0.62 * chh, t, False), 0, yc - 0.18 * chh),
                                 bar(st, 0, cw, yc - 0.18 * chh - 1.6 * t, t)), 'chevron + bar')
    eq = P['equal']; eb = bounds(eq)
    put('notequal', SH.union(eq, stroke_polyline([(eb[0] + 0.25 * L, yc - 0.42 * L), (eb[0] + 0.75 * L, yc + 0.42 * L)], t, st)), 'equal + slash')
    tw = bounds(f.marks['tilde']); tl = SH.transform(f.marks['tilde'], (L / (tw[2] - tw[0]), 0, 0, 1.25, 0, 0)); tb = bounds(tl)
    put('approxequal', SH.union(translate(tl, -tb[0], yc + 0.6 * t - tb[1]), translate(tl, -tb[0], yc - 0.6 * t - tb[3])), 'two tildes')
    put('logicalnot', SH.union(bar(st, 0, L, yc + 0.06 * xh, t), vbar(st, L - t / 2, yc - 0.18 * xh, yc + 0.06 * xh + t / 2, t)), 'bar + drop')

    # ---------------------------------------------------------------- ASCII extras
    h = top; sh = math.tan(math.radians(12))
    xs = [0.18 * xh, 0.48 * xh]
    verts = [stroke_polyline([(x - sh * 0.0, 0), (x + sh * h, h)], 0.85 * t, st) for x in xs]
    if getattr(f, 'CENTRED_NUMBERSIGN', False):
        # each bar centred on the strokes at its own height: level bars at one span overhung the sloped
        # strokes far more on the left than the right (the upper bar 199 to 23 in Kilfane)
        hb = [bar(st, 0.33 * xh + sh * y - 0.37 * xh, 0.33 * xh + sh * y + 0.37 * xh, y, 0.85 * t) for y in (0.33 * h, 0.66 * h)]
    else:
        hb = [bar(st, -0.02 * xh, 0.72 * xh, y, 0.85 * t) for y in (0.33 * h, 0.66 * h)]
    put('numbersign', SH.union(*verts, *hb), 'sheared grid')

    # heavy faces keep the small zeros' own weight: re-emboldening would close their counters
    z = scaled(P['zero'], 0.42, S, 0.78 if f.S_regular < 0.3 * xh else 0.42, Ss)
    zb = bounds(z); zw, zh = zb[2] - zb[0], zb[3] - zb[1]
    z_up = translate(z, -zb[0], top - zb[3]); z_dn = translate(z, -zb[0] + zw + 0.16 * xh, -zb[1])
    sl = stroke_polyline([(0.05 * zw, 0), (zw + 0.16 * xh + 0.95 * zw, top)], 0.6 * t, st)
    put('percent', SH.union(z_up, z_dn, sl), 'scaled zeros + slash')
    pc = P['percent']; pb = bounds(pc)
    put('perthousand', SH.union(pc, translate(z_dn, zw + 0.06 * xh, 0)), 'percent + zero')
    if getattr(f, 'FIGURE_PERCENT', False):
        for name, (p, how) in figure_signs(f, P, top, st).items():
            put(name, p, how)

    # asterisk: five tapering arms
    r = 0.29 * xh; cy = top - 0.30 * xh
    arms = []
    for k in range(5):
        a = math.radians(90 + 72 * k)
        arms.append(SH.wedge((0, cy), (r * math.cos(a), cy + r * math.sin(a)), 0.13 * S, 0.24 * S, rounded=(st == 'round')))
    put('asterisk', SH.union(*arms), 'five arms')

    # @: the face's own a inside an open ring
    R = 0.64 * xh + 0.25 * S; ccx = R; ccy = 0.42 * xh
    if getattr(f, 'AT_INSIDE_RING', False):
        # the a scaled to stand clear inside the ring, as the c of (c) and the r of (R) do: a wide a pressed
        # against the ring closes its slit and joins it
        from fontTools.pens.recordingPen import RecordingPen
        from outline_util import flatten
        ab = bounds(P['a']); rec = RecordingPen(); P['a'].draw(rec)
        far = max(math.hypot(x - (ab[0] + ab[2]) / 2, y - (ab[1] + ab[3]) / 2) for poly in flatten(rec.value, 16) for x, y in poly)
        rt = 0.7 * t; gap = 0.45 * rt
        k = (R - rt - gap) / far
        a = scaled(P['a'], k, S, k, Ss); ab = bounds(a)          # at its own weight: a heavier pen closes the slit
        a = inside_ring(translate(a, ccx - (ab[0] + ab[2]) / 2, ccy - (ab[1] + ab[3]) / 2), ccx, ccy, R - rt, gap)
        put('at', SH.union(a, ring(ccx, ccy, R, rt)), 'a inside a ring')
    else:
        a = scaled(P['a'], 0.74, S, 0.85, Ss); ab = bounds(a)
        a = translate(a, ccx - (ab[0] + ab[2]) / 2 + 0.02 * xh, ccy - (ab[1] + ab[3]) / 2)
        put('at', SH.union(a, ring(ccx, ccy, R, 0.7 * t)), 'a in a ring')

    pt, pbm = asc + 0.02 * xh, -0.30 * xh
    sw = 0.62 * S; arm = 0.24 * xh
    if getattr(f, 'MATCHED_BRACKETS', False):
        # brackets, braces and bar stand as tall as the face's own parentheses: Carrick's and Céilí's are
        # traced and reach only to their figures, so the fixed span left the drawn ones a third taller.
        # And a bracket's arms reach twice its stem: Tuam's stem is as wide as the fixed arm, so its
        # brackets read as bars
        pb = [bounds(P[n]) for n in ('parenleft', 'parenright')]
        pbm, pt = sum(b[1] for b in pb) / 2, sum(b[3] for b in pb) / 2
        arm = max(arm, 2 * sw)
    lb = SH.union(SH.polygon([(0, pbm), (sw, pbm), (sw, pt), (0, pt)]),
                  SH.polygon([(0, pt - 0.55 * t), (arm, pt - 0.55 * t), (arm, pt), (0, pt)]),
                  SH.polygon([(0, pbm), (arm, pbm), (arm, pbm + 0.55 * t), (0, pbm + 0.55 * t)]))
    put('bracketleft', lb, 'stem + arms')
    put('bracketright', SH.transform(lb, (-1, 0, 0, 1, 0, 0)), 'mirror')
    mid = (pt + pbm) / 2; hh = (pt - pbm) / 2; bw = 0.20 * xh
    segs = [((bw * 0.35, pt), (bw * 0.35, pt - 0.12 * hh), (bw * 0.35, pt - 0.35 * hh)),
            ((bw * 0.35, mid + 0.30 * hh), (bw * 0.35, mid + 0.02 * hh), (0, mid)),
            ((bw * 0.35, mid - 0.02 * hh), (bw * 0.35, mid - 0.30 * hh), (bw * 0.35, pbm + 0.35 * hh)),
            ((bw * 0.35, pbm + 0.12 * hh), (bw * 0.35, pbm), (bw, pbm))]
    if getattr(f, 'BRACE_POINT', False):
        # the stroked brace's tip ends inside the stems' outer edge, so its point is cut in as a notch (and
        # the butt caps leave spurs): drawn instead as one outline with the same stems, arms and extent
        w = 0.62 * S
        brace = pointed_brace(pt + w / 2, pbm - w / 2, w, 0.65 * bw + w / 2)
        put('braceleft', brace, 'drawn outline: stems and arms at the stroked brace\'s weight, a point at the waist')
    else:
        # two halves stroked separately and joined at the tip: no self-overlapping join at the cusp
        brace = SH.union(stroke_cubics((bw, pt), segs[:2], 0.62 * S, st),
                         stroke_cubics((0, mid), segs[2:], 0.62 * S, st))
        put('braceleft', brace, 'stroked curve')
    put('braceright', SH.transform(brace, (-1, 0, 0, 1, 0, 0)), 'mirror')
    put('bar', vbar(st, 0, pbm, pt, 0.45 * S), 'rule')
    put('brokenbar', SH.union(vbar(st, 0, pbm, mid - 0.06 * xh, 0.45 * S), vbar(st, 0, mid + 0.06 * xh, pt, 0.45 * S)), 'split rule')
    sl = P['slash']; slb = bounds(sl)
    put('backslash', SH.transform(sl, (-1, 0, 0, 1, 0, 0)), 'mirrored slash')
    put('underscore', bar('square', 0, 0.56 * 1000 * 0.9, -0.24 * xh, 0.55 * t), 'rule')
    put('asciicircum', translate(SH.transform(f.marks['circumflex'], (1.35, 0, 0, 1.35, 0, 0)), 0, top * 0.62), 'circumflex, raised')
    put('asciitilde', translate(SH.transform(f.marks['tilde'], (L / (tw[2] - tw[0]), 0, 0, 1.4, 0, 0)), 0, yc - 0.10 * xh), 'tilde at math axis')

    # ---------------------------------------------------------------- Latin-1 symbols
    def inverted(src):
        b = bounds(P[src]); q = SH.rotate(P[src], 180, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        qb = bounds(q); return translate(q, 0, xh - qb[3])
    put('exclamdown', inverted('exclam'), 'rotated !'); put('questiondown', inverted('question'), 'rotated ?')
    c = P['c']; cb = bounds(c)
    if getattr(f, 'CENT_CLEAR', False):
        cbar = lambda x: vbar(st, x, cb[1] - 0.14 * xh, cb[3] + 0.14 * xh, 0.4 * S)
        put('cent', SH.union(c, cbar(clear_bar(c, cbar, (cb[0] + cb[2]) / 2 + 0.03 * xh, S / 3))), 'c + bar, clear of its counter')
    else:
        put('cent', SH.union(c, vbar(st, (cb[0] + cb[2]) / 2 + 0.03 * xh, cb[1] - 0.14 * xh, cb[3] + 0.14 * xh, 0.4 * S)), 'c + bar')
    # yen: a Y (roman alternate where the face has one) with two bars
    if 'Y.alt1' in P:
        y = P['Y.alt1']
    else:
        v = P['v.alt1'] if 'v.alt1' in P else P['v']; vb = bounds(v)
        kk = top / (vb[3] - vb[1]) * 0.62
        y = embolden(SH.transform(v, (kk, 0, 0, kk, 0, 0)), (Ss - kk * S) / 2 * 0.8)
        yb = bounds(y); y = translate(y, 0, top - yb[3])
        yb = bounds(y); cx = (yb[0] + yb[2]) / 2
        y = SH.union(y, SH.polygon([(cx - 0.42 * S, 0), (cx + 0.42 * S, 0), (cx + 0.42 * S, yb[1] + 0.2 * (yb[3] - yb[1])), (cx - 0.42 * S, yb[1] + 0.2 * (yb[3] - yb[1]))]))
    yb = bounds(y); ycx = (yb[0] + yb[2]) / 2
    put('yen', SH.union(y, bar(st, ycx - 0.27 * xh, ycx + 0.27 * xh, 0.30 * top, 0.7 * t),
                        bar(st, ycx - 0.27 * xh, ycx + 0.27 * xh, 0.30 * top - 1.7 * t, 0.7 * t)), 'Y + bars')
    rr = 0.34 * xh
    spurs = [stroke_polyline([(math.cos(a) * rr * 0.85, yc + math.sin(a) * rr * 0.85), (math.cos(a) * rr * 1.45, yc + math.sin(a) * rr * 1.45)], 0.55 * t, st)
             for a in (math.radians(d) for d in (45, 135, 225, 315))]
    put('currency', SH.union(ring(0, yc, rr, 0.6 * t), *spurs), 'ring + spurs')
    sec = section(P['s'], S, Ss, top)
    if sec is not None:
        put('section', sec, 'two interlaced s')
    else:
        H = top + 0.30 * xh
        put('section', translate(drawn_section(H, 0.58 * H, 0.64 * Ss, st), 0, top - H), 'drawn: an s-stroke and its half-turn')
    bw2 = 0.34 * xh
    bowl = SH.ellipse(bw2, top - 0.25 * top, bw2, 0.25 * top)
    pil = SH.union(bowl, SH.polygon([(bw2, top), (bw2 * 2 + 0.35 * S, top), (bw2 * 2 + 0.35 * S, top - 0.5 * top), (bw2, top - 0.5 * top)]),
                   vbar(st, bw2 * 2, -0.20 * xh, top, 0.42 * S), vbar(st, bw2 * 2 + 0.30 * xh, -0.20 * xh, top, 0.42 * S))
    put('paragraph', pil, 'bowl + two stems')
    R = 0.5 * top
    cc = scaled(P['c'], 0.58, S, 0.62, Ss); ccb = bounds(cc)
    rt = 0.42 * t + 0.1 * S                                       # the ring's weight
    cc = inside_ring(translate(cc, R - (ccb[0] + ccb[2]) / 2, R - (ccb[1] + ccb[3]) / 2), R, R, R - rt, 0.45 * rt)
    put('copyright', SH.union(ring(R, R, R, rt), cc), 'ring + c')
    rsrc = P['R'] if not f.cfg['unicase'] else P['r']
    rg = scaled(rsrc, 0.50 if not f.cfg['unicase'] else 0.62, S, 0.62, Ss); rgb = bounds(rg)
    rg = inside_ring(translate(rg, R - (rgb[0] + rgb[2]) / 2, R - (rgb[1] + rgb[3]) / 2), R, R, R - rt, 0.45 * rt)
    put('registered', SH.union(ring(R, R, R, rt), rg), 'ring + r')
    tm_t = P['T.alt1'] if 'T.alt1' in P else (P['T'] if not f.cfg['unicase'] else P['t'])
    tm_m = P['M'] if not f.cfg['unicase'] else P['m']
    k = 0.42 if not f.cfg['unicase'] else 0.52
    a1 = scaled(tm_t, k, S, 0.55, Ss); a2 = scaled(tm_m, k, S, 0.55, Ss); b1 = bounds(a1); b2 = bounds(a2)
    tmx = SH.union(translate(a1, -b1[0], top - b1[3]), translate(a2, b1[2] - b1[0] - b2[0] + 0.04 * xh, top - b2[3]))
    put('trademark', tmx, 'small T + M')
    if 'ring' in getattr(f, 'piece', {}):
        rg_ = f.piece['ring']; put('degree', translate(rg_, 0, top - bounds(rg_)[3]), 'the sheet\'s ring')
    else:
        put('degree', ring(0.15 * xh, top - 0.15 * xh, 0.15 * xh, 0.45 * t), 'small ring')
    for name, src in (('ordfeminine', 'a'), ('ordmasculine', 'o')):
        g = scaled(P[src], 0.55, S, 0.7, Ss); gb = bounds(g)
        g = translate(g, -gb[0], top - gb[3]); gb = bounds(g)
        put(name, SH.union(g, bar('square', gb[0], gb[2], gb[1] - 0.10 * xh, 0.45 * t)), f'small {src} + rule')
    sup = {}
    for name, src in (('onesuperior', 'one'), ('twosuperior', 'two'), ('threesuperior', 'three')):
        g = scaled(P[src], 0.56, S, 0.7, Ss); gb = bounds(g)
        sup[src] = g
        put(name, translate(g, -gb[0], top - gb[3]), 'small figure')
    fr = stroke_polyline([(0, -0.02 * top), (0.40 * xh, top * 1.0)], 0.45 * t, st)
    put('fraction', fr, 'steep slash')
    def frac(num, den):
        n = scaled(P[num], 0.52, S, 0.7, Ss); d = scaled(P[den], 0.52, S, 0.7, Ss)
        nb, dbb = bounds(n), bounds(d); fb = bounds(P['fraction'])
        n = translate(n, -nb[0], top - nb[3])
        fx = nb[2] - nb[0] - 0.12 * xh
        fpath = translate(P['fraction'], fx - fb[0], 0)
        d = translate(d, fx + (fb[2] - fb[0]) - 0.12 * xh - dbb[0], -dbb[1])
        return SH.union(n, fpath, d)
    put('onequarter', frac('one', 'four'), 'fraction'); put('onehalf', frac('one', 'two'), 'fraction')
    put('threequarters', frac('three', 'four'), 'fraction')
    u = P['u']; s0 = bounds(u)
    from letters import stem_at
    l0, l1 = stem_at(u, 0.4 * xh, 'left')
    put('mu', SH.union(u, SH.polygon([(l0, -0.30 * xh), (l1, -0.30 * xh), (l1, 0.3 * xh), (l0, 0.3 * xh)])), 'u + descender')
    put('periodcentered', translate(f.period, 0, yc - (bounds(f.period)[1] + bounds(f.period)[3]) / 2), 'raised period')
    put('bullet', SH.ellipse(0, yc, 0.17 * xh, 0.17 * xh), 'disc')
    dg = SH.union(vbar(st, 0, -0.18 * xh, top, 0.42 * S), bar(st, -0.21 * xh, 0.21 * xh, top - 0.30 * xh, 0.8 * t))
    put('dagger', dg, 'stem + bar')
    put('daggerdbl', SH.union(dg, bar(st, -0.21 * xh, 0.21 * xh, 0.10 * xh, 0.8 * t)), 'stem + two bars')

    # ---------------------------------------------------------------- quotes, guillemets, primes
    cm = P['comma']; cmb = bounds(cm)
    put('quotesinglbase', cm, 'comma')
    put('quotedblbase', SH.union(cm, translate(cm, (cmb[2] - cmb[0]) * 1.45, 0)), 'two commas')
    pc = getattr(f, 'piece', {})
    if 'guil.r1' in pc:
        # the sheet's own chevrons, centred on the hyphen like the drawn ones
        mirror = lambda p: SH.transform(p, (-1, 0, 0, 1, 0, 0))
        mid = lambda p: translate(p, 0, yc - (bounds(p)[1] + bounds(p)[3]) / 2)
        rr = SH.union(pc['guil.r1'], pc['guil.r2'])
        ll = SH.union(pc['guil.l1'], pc['guil.l2']) if 'guil.l1' in pc else mirror(rr)
        put('guilsinglright', mid(pc['guil.r1']), 'chevron from the sheet')
        put('guilsinglleft', mid(pc['guil.l1'] if 'guil.l1' in pc else mirror(pc['guil.r1'])), 'chevron from the sheet')
        put('guillemotright', mid(rr), 'chevrons from the sheet'); put('guillemotleft', mid(ll), 'chevrons from the sheet')
    else:
        gw, gh = 0.30 * xh, 0.52 * xh; gt = min(0.55 * S, 0.17 * xh)
        gl = translate(chevron(st, gw, gh, gt, True), 0, yc - gh / 2); gr = translate(chevron(st, gw, gh, gt, False), 0, yc - gh / 2)
        put('guilsinglleft', gl, 'chevron'); put('guilsinglright', gr, 'chevron')
        put('guillemotleft', SH.union(gl, translate(gl, gw * 0.62 + gt, 0)), 'two chevrons')
        put('guillemotright', SH.union(gr, translate(gr, gw * 0.62 + gt, 0)), 'two chevrons')
    q = P['quotesingle']
    pr = SH.transform(q, (1, 0, math.tan(math.radians(14)), 1, 0, 0))
    put('minute', pr, 'slanted wedge')
    put('second', SH.union(pr, translate(pr, (bounds(pr)[2] - bounds(pr)[0]) * 1.4, 0)), 'two wedges')
    return made
