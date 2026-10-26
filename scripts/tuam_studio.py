"""Tuam Uncial's studio finishing pass: the judged corrections recorded in research/tuam-judgement/judged-edits.json.

The release candidate (scripts/build_candidate.py) applies the edits to the traced letters in font units, after the
builder's own clean-up (finish.py) and height regularisation (Font2.zones), before anything is derived from them;
the file's construction values set the accents' gap, the kerning above the x-height and the sloped style. Each edit
is an operation a type designer makes by hand, and states its target, measured again on the outline as it stands:

  point     a spur's end, or a corner blurred into several nodes, drawn as one sharp corner where its sides meet
  height    a letter's top on its line (x-height, ascender, figures) and its foot on the baseline: the part above
            the baseline is scaled, as Font2.zones does within its tolerance
  level     one flat top (or bottom) moved onto its line, the stroke under it with it, faded out over `feather`
  stem_top  an i or j's stem to the x-height, its dot with it
  stem      a vertical stem's width: the glyph is split down the stem's middle, each half moving half the difference
  smooth    a faceted stretch of outline redrawn as one cubic
  spur      a cut or slit's width where a spur comes closest to the next stroke: the spur's end moves along the
            gap, fading out along the outline, so only that end is redrawn
  cut       a long seam's width: the piece named moves bodily along the gap
  dot       the dot of i, j, ! or ? a gap from its stroke (with `like`, another glyph's dot)

The second pass adds constructions and edits to glyphs made from the traced ones (`derived`, applied in each style's
own frame: smooth, point, settle): í's acute drawn steeper (steepen), the comma and everything made from it
(comma), the ponc on the ascender letters (ponc), the sloped style's weight given back with its openings kept
(grow_back) and its outlines settled after the slant (settled).
"""
import json, math
from pathlib import Path
import numpy as np
import pathops
from fontTools.pens.recordingPen import RecordingPen, replayRecording
from fontTools.pens.pointInsidePen import PointInsidePen

import bolden
import shapes as SH
from glyphs import bounds, translate

ROOT = Path(__file__).resolve().parent.parent
EDITS = ROOT / 'research' / 'tuam-judgement' / 'judged-edits.json'


# ---------------------------------------------------------------- outlines as contours of segments
def contours(p):
    """[[start, [(kind, pts), ...]], ...] with kind 'L' or 'C'; quadratic pieces are written as cubics."""
    from fontTools.pens.basePen import decomposeQuadraticSegment
    r = RecordingPen(); p.draw(r)
    out, cur = [], None
    for op, a in r.value:
        if op == 'moveTo':
            cur = [tuple(a[0]), []]
        elif op == 'lineTo':
            cur[1].append(('L', [tuple(a[0])]))
        elif op == 'curveTo':
            cur[1].append(('C', [tuple(q) for q in a]))
        elif op == 'qCurveTo':
            a = list(a)
            if a[-1] is None:                     # off-curve points only: start on the implied point
                s = ((a[-2][0] + a[0][0]) / 2, (a[-2][1] + a[0][1]) / 2)
                cur = [s, []]; a[-1] = s
            p0 = cur[1][-1][1][-1] if cur[1] else cur[0]
            for q, e in decomposeQuadraticSegment(a):
                c1 = (p0[0] + 2 / 3 * (q[0] - p0[0]), p0[1] + 2 / 3 * (q[1] - p0[1]))
                c2 = (e[0] + 2 / 3 * (q[0] - e[0]), e[1] + 2 / 3 * (q[1] - e[1]))
                cur[1].append(('C', [c1, c2, tuple(e)])); p0 = e
        elif op in ('closePath', 'endPath'):
            if cur[1] and cur[1][-1][1][-1] != cur[0]:
                cur[1].append(('L', [cur[0]]))
            out.append(cur); cur = None
    return out


def path_of(cs):
    p = pathops.Path(); pen = p.getPen()
    for start, segs in cs:
        pen.moveTo(start)
        for k, pts in segs:
            (pen.lineTo if k == 'L' else pen.curveTo)(*pts)
        pen.closePath()
    return p


def samples(cs, step=2.0):
    """Dense points along every contour: (xy, contour index, arc position)."""
    xy, ci, arc = [], [], []
    for i, (start, segs) in enumerate(cs):
        a = np.array(start, float); s = 0.0
        for k, pts in segs:
            P = [a] + [np.array(q, float) for q in pts]
            L = sum(np.linalg.norm(P[j + 1] - P[j]) for j in range(len(P) - 1))
            n = max(2, int(L / step))
            t = np.linspace(0, 1, n, endpoint=False)[:, None]
            if k == 'L':
                q = P[0] + (P[1] - P[0]) * t
            else:
                q = (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t * t * P[2] + t ** 3 * P[3]
            d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(q, axis=0), axis=1))]
            xy.append(q); ci += [i] * len(q); arc.append(s + d)
            s += d[-1] + np.linalg.norm(P[-1] - q[-1]); a = P[-1]
    return np.vstack(xy), np.array(ci), np.concatenate(arc)


def remap(p, fn):
    cs = [[fn(*start), [(k, [fn(*q) for q in pts]) for k, pts in segs]] for start, segs in contours(p)]
    return pathops.simplify(path_of(cs), fix_winding=True, keep_starting_points=True, clockwise=False)


def runs_at(p, y):
    xs = []
    for start, segs in contours(p):
        pts, _, _ = samples([[start, segs]], step=1.0)
        a, b = pts, np.roll(pts, -1, axis=0)
        m = ((a[:, 1] <= y) & (b[:, 1] > y)) | ((b[:, 1] <= y) & (a[:, 1] > y))
        t = (y - a[m, 1]) / (b[m, 1] - a[m, 1]); xs += list(a[m, 0] + t * (b[m, 0] - a[m, 0]))
    xs = sorted(xs)
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


def inside(p, pt):
    pen = PointInsidePen(None, pt); p.draw(pen); return pen.getResult()


# ---------------------------------------------------------------- operations
def stem(p, at, width, ramp=0.3):
    """Split the glyph down the middle of the stem that the scanline at[1] crosses at at[0]; move the halves."""
    run = next(r for r in runs_at(p, at[1]) if r[0] - 1 <= at[0] <= r[1] + 1)
    c, w = (run[0] + run[1]) / 2, ramp * (run[1] - run[0]); d = (width - (run[1] - run[0])) / 2
    return remap(p, lambda x, y: (x + d * max(-1.0, min(1.0, (x - c) / w)), y)), run[1] - run[0]


def seg_lengths(start, segs, step=2.0):
    """Each segment's length, measured as samples() measures it."""
    out, a = [], np.array(start, float)
    for k, pts in segs:
        P = [a] + [np.array(q, float) for q in pts]
        L = sum(np.linalg.norm(P[j + 1] - P[j]) for j in range(len(P) - 1))
        n = max(2, int(L / step))
        t = np.linspace(0, 1, n, endpoint=False)[:, None]
        q = P[0] + (P[1] - P[0]) * t if k == 'L' else \
            (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t * t * P[2] + t ** 3 * P[3]
        out.append(float(np.sum(np.linalg.norm(np.diff(q, axis=0), axis=1)) + np.linalg.norm(P[-1] - q[-1])))
        a = P[-1]
    return out


def narrowest(cs, tip, reach, far):
    """The narrowest white between the spur ending at `tip` (the outline within `reach` of its nearest node) and
    whatever lies across from it (another contour, or the same one more than `far` along): (contour, point on
    the spur, point across, width, the spur point's arc position)."""
    xy, ci, arc = samples(cs)
    best = None
    for i, (start, segs) in enumerate(cs):
        for k, pts in segs:
            dd = math.dist(pts[-1], tip)
            if best is None or dd < best[0]:
                best = (dd, i, pts[-1])
    _, i, node = best
    own = ci == i; total = arc[own].max()
    k = np.where(own)[0][np.argmin(np.linalg.norm(xy[own] - node, axis=1))]
    da = np.abs(arc - arc[k]); da = np.minimum(da, total - da)
    A = np.where(own & (da <= reach))[0]; B = np.where(~own | (da > far))[0]
    from scipy.spatial import cKDTree
    d, kb = cKDTree(xy[B]).query(xy[A]); m = int(np.argmin(d))
    return i, xy[A[m]], xy[B[kb[m]]], float(d[m]), float(arc[A[m]])


def spur(p, tip, width, reach=110.0, span=200.0, far=260.0, iters=5):
    """Bring a cut or slit to `width` at its narrowest, between the spur that ends at `tip` (its outline within
    `span` of the tip) and what lies across from it: the spur's points move along the gap, fully where it is
    narrowest and fading (cosine) to nothing `reach` units of outline either side of there."""
    before = None
    for _ in range(iters):
        cs = contours(p)
        i, a, b, d, s0 = narrowest(cs, tip, span, far)
        if before is None:
            before = d
        if abs(d - width) < 0.25:
            break
        move = (a - b) / d * (width - d)
        start, segs = cs[i]
        L = seg_lengths(start, segs); pos = np.r_[0, np.cumsum(L)]; total = pos[-1]
        def wt(s):
            dd = abs(s - s0); dd = min(dd, total - dd)
            return 0.5 * (1 + math.cos(math.pi * dd / reach)) if dd < reach else 0.0
        mv = lambda q, w: (q[0] + move[0] * w, q[1] + move[1] * w)
        new = []
        for j, (k, pts) in enumerate(segs):
            w0, w1 = wt(pos[j]), wt(pos[j + 1])
            new.append(('L', [mv(pts[0], w1)]) if k == 'L' else ('C', [mv(pts[0], w0), mv(pts[1], w1), mv(pts[2], w1)]))
        cs[i] = [new[-1][1][-1], new]
        p = pathops.simplify(path_of(cs), fix_winding=True, keep_starting_points=True, clockwise=False)
    return p, before


def point(p, tip, radius=18.0):
    """Draw a spur's end as one sharp corner: the nodes within `radius` of `tip` give way to the point where
    the outline's two sides, continued along their tangents, meet. Each side keeps its curve and handle."""
    cs = contours(p)
    best = None
    for i, (start, segs) in enumerate(cs):
        ends = [s[1][-1] for s in segs]
        near = [j for j, e in enumerate(ends) if math.dist(e, tip) <= radius]
        if near and (best is None or min(math.dist(ends[j], tip) for j in near) < best[0]):
            best = (min(math.dist(ends[j], tip) for j in near), i, near)
    if best is None:
        raise ValueError(f'point: no node within {radius} of {tip}')
    _, i, near = best
    start, segs = cs[i]; n = len(segs)
    # the run of region nodes, cyclic: j0 .. j1
    s = set(near)
    j0 = next(j for j in near if (j - 1) % n not in s)
    run = [j0]
    while (run[-1] + 1) % n in s:
        run.append((run[-1] + 1) % n)
    j1 = run[-1]
    if len(run) != len(near):
        raise ValueError('point: the nodes near the tip are not contiguous')
    node = lambda j: np.array(segs[j][1][-1], float)
    sin, sout = segs[j0], segs[(j1 + 1) % n]
    a = node(j0); b = node(j1)
    prev_end = node((j0 - 1) % n)
    if sin[0] == 'C':
        c2 = np.array(sin[1][1], float); tin = a - c2 if np.linalg.norm(a - c2) > 1e-6 else a - np.array(sin[1][0], float)
    else:
        tin = a - prev_end
    if sout[0] == 'C':
        c1 = np.array(sout[1][0], float); tout = c1 - b if np.linalg.norm(c1 - b) > 1e-6 else np.array(sout[1][1], float) - b
    else:
        tout = np.array(sout[1][0], float) - b
    tin /= np.linalg.norm(tin); tout /= np.linalg.norm(tout)
    # a + t tin = b - u tout
    M = np.array([tin, tout]).T
    try:
        t, u = np.linalg.solve(M, b - a)
    except np.linalg.LinAlgError:
        t = u = -1
    # a side may also be shortened: a line by up to its length, a curve by a little
    t_min = -(np.linalg.norm(a - prev_end) - 1) if sin[0] == 'L' else -8
    u_min = -(np.linalg.norm(np.array(sout[1][-1], float) - b) - 1) if sout[0] == 'L' else -8
    if t < t_min or u < u_min or t > 4 * radius or u > 4 * radius:
        raise ValueError(f'point: the sides at {tip} do not meet near it (t {t:.1f}, u {u:.1f})')
    corner = tuple(a + t * tin)
    # the entering segment now ends at the corner (its last handle, on the tangent, keeps the direction); the
    # segments between region nodes go; the leaving one starts at the corner, its first handle on the tangent
    new_in = ('L', [corner]) if sin[0] == 'L' else ('C', [sin[1][0], sin[1][1], corner])
    inner = set(run[1:])
    out = [new_in if j == j0 else segs[j] for j in range(n) if j not in inner]
    cs[i] = [out[-1][1][-1], out]
    return pathops.simplify(path_of(cs), fix_winding=True, keep_starting_points=True, clockwise=False), float(len(run))


def _locate(cs, frm, to, tol=12.0):
    """The contour and node indices (a, b) nearest frm and to, b following a in the contour's direction."""
    best = None
    for i, (start, ss) in enumerate(cs):
        ends = [s[1][-1] for s in ss]
        a = min(range(len(ends)), key=lambda j: math.dist(ends[j], frm))
        b = min(range(len(ends)), key=lambda j: math.dist(ends[j], to))
        err = max(math.dist(ends[a], frm), math.dist(ends[b], to))
        if best is None or err < best[0]:
            best = (err, i, a, b)
    if best[0] > tol:
        raise ValueError(f'no nodes near {frm} and {to} (off by {best[0]:.1f})')
    return best[1:]


def smooth(p, frm, to, ends=('smooth', 'smooth')):
    """Redraw the outline from the node nearest `frm` to the node nearest `to` as one cubic, fitted (least
    squares, end points fixed) to the outline it replaces: the facets and wobbles of a traced curve become
    one curve. At each end the curve takes the tangent of the outline beyond it ('smooth') or keeps the
    replaced outline's own ('corner')."""
    cs = contours(p)
    i, a, b = _locate(cs, frm, to)
    start, ss = cs[i]; n = len(ss)
    if (b - a) % n > (a - b) % n:          # the contour runs the other way: take the short way round
        a, b, ends = b, a, ends[::-1]
    idx = [(a + 1 + t) % n for t in range((b - a) % n)]
    if not idx:
        raise ValueError('smooth: nothing between the nodes')
    P0 = np.array(ss[a][1][-1], float); P3 = np.array(ss[b][1][-1], float)
    chain = [[tuple(P0), [ss[j] for j in idx]]]
    Q, _, arc = samples(chain, 1.0)
    Q = np.vstack([Q, P3]); arc = np.r_[arc, arc[-1] + np.linalg.norm(P3 - Q[-2])]
    def tangent(seg, at_end, start_pt):
        k, pts = seg
        if k == 'L':
            d = np.array(pts[0], float) - np.array(start_pt, float)
        elif at_end:
            d = np.array(pts[2], float) - np.array(pts[1], float)
            if np.linalg.norm(d) < 1e-6:
                d = np.array(pts[2], float) - np.array(pts[0], float)
        else:
            d = np.array(pts[0], float) - np.array(start_pt, float)
            if np.linalg.norm(d) < 1e-6:
                d = np.array(pts[1], float) - np.array(start_pt, float)
        return d / np.linalg.norm(d)
    node = lambda j: ss[j % n][1][-1]
    t0 = tangent(ss[a], True, node(a - 1)) if ends[0] == 'smooth' else tangent(ss[idx[0]], False, node(a))
    t1 = tangent(ss[(b + 1) % n], False, node(b)) if ends[1] == 'smooth' else tangent(ss[idx[-1]], True, node(idx[-1] - 1))
    u = arc / arc[-1]
    for _ in range(3):
        B1 = 3 * (1 - u) ** 2 * u; B2 = 3 * (1 - u) * u ** 2
        base = ((1 - u) ** 3 + B1)[:, None] * P0 + (B2 + u ** 3)[:, None] * P3
        A = np.column_stack([np.r_[B1 * t0[0], B1 * t0[1]], np.r_[-B2 * t1[0], -B2 * t1[1]]])
        rhs = np.r_[Q[:, 0] - base[:, 0], Q[:, 1] - base[:, 1]]
        (al, be), *_ = np.linalg.lstsq(A, rhs, rcond=None)
        L = np.linalg.norm(P3 - P0)
        al, be = float(np.clip(al, 0.05 * L, 1.2 * L)), float(np.clip(be, 0.05 * L, 1.2 * L))
        C1, C2 = P0 + al * t0, P3 - be * t1
        # reparameterise: nearest parameter on the fitted curve for each sample
        tt = np.linspace(0, 1, 400)[:, None]
        curve = (1 - tt) ** 3 * P0 + 3 * (1 - tt) ** 2 * tt * C1 + 3 * (1 - tt) * tt ** 2 * C2 + tt ** 3 * P3
        from scipy.spatial import cKDTree
        d, k = cKDTree(curve).query(Q)
        u = tt[k, 0]
    dev = float(d.max())
    cs[i] = [ss[a][1][-1], [('C', [tuple(C1), tuple(C2), tuple(P3)])] + [ss[(b + 1 + t) % n] for t in range(n - len(idx))]]
    return pathops.simplify(path_of(cs), fix_winding=True, keep_starting_points=True, clockwise=False), dev


def cut(p, move, fixed, width, iters=4):
    """Move the piece containing `move` away from (or towards) the piece containing `fixed` along their
    closest approach until the white between them is `width` at its narrowest."""
    comps = bolden.components(p)
    A = next(c for c in comps if inside(c, fixed)); B = next(c for c in comps if inside(c, move))
    rest = [c for c in comps if c is not A and c is not B]
    before = None
    for _ in range(iters):
        xa, _, _ = samples(contours(A), 1.0); xb, _, _ = samples(contours(B), 1.0)
        from scipy.spatial import cKDTree
        d, k = cKDTree(xb).query(xa); i = int(np.argmin(d)); dist = float(d[i])
        if before is None:
            before = dist
        if abs(dist - width) < 0.25:
            break
        u = (xb[k[i]] - xa[i]) / dist
        B = translate(B, *(u * (width - dist)))
    return bolden.concat([*rest, A, B]), before


def height(f, p, line, foot='flat'):
    """Foot on the baseline (flat feet) and the top on `line`, the part above the baseline scaled."""
    y0 = bounds(p)[1]
    if foot == 'flat' and y0 > -0.1 * f.xh:
        p = translate(p, 0, -y0)
    top = bounds(p)[3]
    k = line / top
    return remap(p, lambda x, y: (x, y * k if y > 0 else y)), top


def stem_top(f, p, line):
    """An i or j: raise the stem's top to `line` and its dot with it."""
    comps = bolden.components(p)
    body = min(comps, key=lambda c: bounds(c)[1]); dots = [c for c in comps if c is not body]
    top = bounds(body)[3]; k = line / top
    body = remap(body, lambda x, y: (x, y * k if y > 0 else y))
    return bolden.concat([body] + [translate(d, 0, line - top) for d in dots]), top


def split_dot(p):
    """(stroke, dot, whether the dot is above) of an i, j, ! or ?."""
    comps = bolden.components(p)
    if len(comps) != 2:
        raise ValueError('a dot and one stroke expected')
    lo, hi = sorted(comps, key=lambda c: bounds(c)[1])
    big_is_low = abs(bolden.area(lo)) > abs(bolden.area(hi))
    return (lo, hi, True) if big_is_low else (hi, lo, False)


def dot(p, gap, like=None):
    """The dot of i or j (above its stem) or of ! or ? (on the baseline, below the stroke) set `gap` units from
    its stroke: the dot above moves; under the dot on the line, the stroke's foot is drawn up (the stroke is
    shortened from below). With `like` (another glyph), the dot is that glyph's, centred across where its own was,
    its foot where its own foot was."""
    from scipy.spatial import cKDTree
    stroke, d, above = split_dot(p)
    if like is not None:
        other = split_dot(like)[1]; a, b = bounds(d), bounds(other)
        d = translate(other, (a[0] + a[2] - b[0] - b[2]) / 2, a[1] - b[1])
    def white(s, t):
        return float(cKDTree(samples(contours(s), 1.0)[0]).query(samples(contours(t), 1.0)[0])[0].min())
    was = white(stroke, d)
    if above:
        dy = gap - was
        for _ in range(4):
            now = white(stroke, translate(d, 0, dy))
            if abs(now - gap) < 0.25:
                break
            dy += gap - now
        return bolden.concat([stroke, translate(d, 0, dy)]), was
    b0, top = bounds(stroke)[1], bounds(stroke)[3]
    up = gap - was
    for _ in range(4):
        k = (top - b0 - up) / (top - b0)
        s = remap(stroke, lambda x, y, k=k: (x, top - (top - y) * k))
        now = white(s, d)
        if abs(now - gap) < 0.25:
            break
        up += gap - now
    return bolden.concat([s, d]), was


def level_of(p, x0, x1, side):
    """The median height of the top (or bottom) edge over x0..x1."""
    sw = [[s, [(k, [(q[1], q[0]) for q in pts]) for k, pts in segs]] for s, segs in
          [[(st[1], st[0]), sg] for st, sg in contours(p)]]
    rot = path_of(sw)
    ys = []
    for x in np.arange(x0, x1 + 0.1, 2.0):
        r = runs_at(rot, x)
        if r:
            ys.append(r[-1][1] if side == 'top' else r[0][0])
    return float(np.median(ys)) if ys else float('nan')


def level(p, measure, box, side, to, depth, feather, xfeather=40.0, cap=None):
    """Move the top (or bottom) of the glyph over box[0]..box[1] so that its edge over `measure` sits at `to`:
    everything within `depth` of that edge moves rigidly, fading to nothing over `feather` beyond it, and over
    `xfeather` beyond the box's sides; with `cap`, nothing more than `cap` beyond the edge moves (an ascender)."""
    was = level_of(p, *measure, side)
    dy = to - was
    def wt(x, y):
        wx = 1.0 if box[0] <= x <= box[1] else max(0.0, 1 - min(abs(x - box[0]), abs(x - box[1])) / xfeather)
        reach = (y - (was - depth)) if side == 'top' else ((was + depth) - y)
        wy = 1.0 if reach >= 0 else max(0.0, 1 + reach / feather)
        if cap is not None:
            over = (y - was) if side == 'top' else (was - y)
            wy *= 1.0 if over <= cap else max(0.0, 1 - (over - cap) / 30.0)
        return wx * wy
    return remap(p, lambda x, y: (x, y + dy * wt(x, y))), was


# ---------------------------------------------------------------- the pass
def load(path=EDITS):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def apply(f, path=EDITS):
    """Apply every edit to f.P (a Font2 after zones()); returns the record of what each measured and did."""
    doc = load(path)
    lines = {'xh': f.xh, 'asc': f.asc, 'fig': f.fig}
    report = []
    for e in doc['edits']:
        n, op = e['glyph'], e['op']
        p = f.P[n]
        if op == 'height':
            p, was = height(f, p, lines[e['line']] + e.get('over', 0), e.get('foot', 'flat'))
            now = bounds(p)[3]
        elif op == 'stem_top':
            p, was = stem_top(f, p, lines[e['line']]); now = lines[e['line']]
        elif op == 'stem':
            p, was = stem(p, e['at'], e['width']); now = e['width']
        elif op == 'spur':
            p, was = spur(p, e['tip'], e['width'], e.get('reach', 110.0)); now = e['width']
        elif op == 'point':
            p, was = point(p, e['tip'], e.get('radius', 18.0)); now = None
        elif op == 'smooth':
            p, was = smooth(p, e['from'], e['to'], tuple(e.get('ends', ('smooth', 'smooth')))); now = None
        elif op == 'cut':
            p, was = cut(p, e['move'], e['fixed'], e['width']); now = e['width']
        elif op == 'dot':
            p, was = dot(p, e['gap'], f.P[e['like']] if 'like' in e else None); now = e['gap']
        elif op == 'level':
            to = lines[e['to']] if isinstance(e['to'], str) else e['to']
            p, was = level(p, e['measure'], e['box'], e['side'], to, e['depth'], e['feather'], e.get('xfeather', 40.0), e.get('cap'))
            now = to
        else:
            raise ValueError(f'unknown studio operation {op}')
        f.P[n] = p
        report.append(dict(glyph=n, op=op, before=round(float(was), 1), after=None if now is None else round(float(now), 1)))
    f.studio = report
    c = doc.get('constructions', {})
    if 'crossbar_at' in c:
        f.CROSSBAR_AT = c['crossbar_at']['value']          # letters.make_letters reads it
    return report


def kern(f, path=EDITS):
    """Above the x-height, every pair stands at least the cut's width apart (after Font2.kerning and the
    builder's 8-unit protection): f's flag over the next ascender or fada is drawn apart, as the cuts are. First, in
    the upright, the judged edits to the glyphs made from the traced ones (the sloped style has them before its
    narrowing, in condense())."""
    import build2
    doc = load(path)
    if not f.italic:
        for n in sorted({e['glyph'] for e in doc.get('derived', [])}):
            if n in f.final:
                was = bounds(f.final[n])
                f.final[n] = build2.final_clean(derived_edits(doc, n, f.final[n]))
                if max(abs(u - v) for u, v in zip(bounds(f.final[n]), was)) > 1:     # it was spaced on its extent
                    raise ValueError(f'the derived edits moved the extent of {n}: {was} -> {bounds(f.final[n])}')
    c = doc.get('constructions', {}).get('upper_clearance')
    if not c:
        return []
    import math as m
    from scipy.ndimage import minimum_filter1d
    from study_spacing import silhouette
    clearance = c['value']
    names = [n for n, p in f.final.items() if n not in f.mark_glyphs and n not in {'space', 'underscore'} and bounds(p)]
    high = m.ceil(max(bounds(f.final[n])[3] for n in names)) + 3
    ys = np.arange(m.floor(f.xh) + 0.5, high, 1.0)
    prof = {}
    for n in names:
        left, right = silhouette(f.final[n], ys)
        prof[n] = (minimum_filter1d(left, size=5, mode='constant', cval=np.inf), right)
    effective = {}
    for (a, b), v in f.kern_pairs.items():
        for ga in f.left_group.get(a, [a]):
            for gb in f.right_group.get(b, [b]):
                effective[ga, gb] = v
    effective.update(f.kern_exc)
    changes = []
    for a in names:
        right = prof[a][1]
        if not np.isfinite(right).any():
            continue
        for b in names:
            cur = effective.get((a, b), 0)
            gap = f.adv[a] + cur + prof[b][0] - right
            low = float(np.min(gap))
            if not np.isfinite(low) or low >= clearance:
                continue
            new = int(m.ceil((cur + clearance - low) / 5) * 5)
            f.kern_exc[a, b] = new
            changes.append(dict(left=a, right=b, before=cur, after=new, measured_gap=round(low, 1)))
    f.upper_clearance = changes
    return changes


def condense(f, k, path=EDITS):
    """The sloped style's narrowing, where the constructions ask for it (returns whether it did): 'affine', the
    narrowing alone; 'grown', the narrowing with the stems' and bowls' weight given back (grow_back). The builder
    grows every narrowed outline by a hair (4.4 units a side) with a stroked offset, which takes 9 units out of every
    cut, slit and seam and draws them in short pieces."""
    doc = load(path)
    how = doc.get('constructions', {}).get('italic_condense', {}).get('value')
    if how not in ('affine', 'grown'):
        return False
    rx = (1 - k) * f.S / 2
    import build2
    t = math.tan(math.radians(build2.SLANT)); slope = (1, 0, t, 1, -f.xh / 2 * t, 0)     # as Font2.slant
    f.grown_back = {}
    narrow = {}
    for n, p in list(f.P.items()):
        if bounds(p) is not None:
            narrow[n] = derived_edits(doc, n, SH.transform(p, (k, 0, 0, 1, 0, 0)), k)
    if how == 'affine':
        f.P.update(narrow)
        return True
    comp = getattr(f, 'comp', {})
    for n, q in narrow.items():
        if n not in comp or comp[n] not in narrow:
            f.P[n], f.grown_back[n] = grow_back(q, rx, f.S, slope)
    # an accented letter is its letter as grown, with its marks grown on their own and moved with the letter
    for n, q in narrow.items():
        if n in comp and comp[n] in narrow:
            base = narrow[comp[n]]; grown = f.P[comp[n]]
            rest = SH.difference(q, base)
            if bounds(rest) is None:
                f.P[n] = grown; f.grown_back[n] = f.grown_back[comp[n]]; continue
            rest, f.grown_back[n] = grow_back(rest, rx, f.S, slope)
            dx = (bounds(grown)[0] + bounds(grown)[2] - bounds(base)[0] - bounds(base)[2]) / 2
            f.P[n] = SH.union(grown, translate(rest, dx, 0))
    return True


def derived_edits(doc, name, p, k=1.0):
    """The judged edits to a glyph made from the traced ones (judged-edits.json, `derived`), in its own frame: x
    from its left edge, narrowed by k in the sloped style."""
    eds = [e for e in doc.get('derived', []) if e['glyph'] == name]
    if not eds:
        return p
    x0 = bounds(p)[0]
    at = lambda q: (x0 + k * q[0], q[1])
    for e in eds:
        if e['op'] == 'smooth':
            p, _ = smooth(p, at(e['from']), at(e['to']), tuple(e.get('ends', ('smooth', 'smooth'))))
        elif e['op'] == 'point':
            p, _ = point(p, at(e['tip']), e.get('radius', 18.0))
        elif e['op'] == 'settle':
            import build2
            p = settled(build2.final_clean(p), e.get('tiny', 8))
        else:
            raise ValueError(f'unknown derived edit {e["op"]}')
    return p


# ---------------------------------------------------------------- the sloped style's weight
def ink_raster(p, pad=4):
    """The ink on a one-unit grid: (mask, x0, y1), row r at y = y1 - r, column c at x = x0 + c (even-odd)."""
    from PIL import Image, ImageDraw
    b = bounds(p); x0, y1 = math.floor(b[0]) - pad, math.ceil(b[3]) + pad
    W, H = int(math.ceil(b[2]) - x0) + pad + 1, int(y1 - math.floor(b[1])) + pad + 1
    m = np.zeros((H, W), bool)
    for start, segs in contours(p):
        pts, _, _ = samples([[start, segs]], step=1.0)
        img = Image.new('1', (W, H), 0)
        ImageDraw.Draw(img).polygon([(x - x0, y1 - y) for x, y in pts], fill=1)
        m ^= np.asarray(img, dtype=bool)
    return m, x0, y1


def white_necks(p, limit, step=2.0, far=150.0, window=40.0):
    """The narrow whites of an outline (cuts, slits, seams): [(width, a, b)], narrowest first, where the white
    across from a point of the outline (to the nearest point across it, b) is narrowest within `window` units of
    outline either side; points along one contour count as across only when more than `far` (and three widths)
    apart along it."""
    from scipy.spatial import cKDTree
    cs = contours(p)
    xy, ci, arc = samples(cs, step)
    tot = np.array([arc[ci == i].max() for i in range(len(cs))])
    pairs = cKDTree(xy).query_pairs(limit, output_type='ndarray')
    if not len(pairs):
        return []
    i, j = np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]]
    d = np.linalg.norm(xy[i] - xy[j], axis=1)
    da = np.abs(arc[i] - arc[j]); da = np.minimum(da, tot[ci[i]] - da)
    keep = (ci[i] != ci[j]) | (da > np.maximum(far, 3 * d))
    i, j, d = i[keep], j[keep], d[keep]
    if not len(d):
        return []
    m, x0, y1 = ink_raster(p)
    mid = (xy[i] + xy[j]) / 2
    c = np.clip(np.round(mid[:, 0] - x0).astype(int), 0, m.shape[1] - 1)
    r = np.clip(np.round(y1 - mid[:, 1]).astype(int), 0, m.shape[0] - 1)
    keep = ~m[r, c]
    i, j, d = i[keep], j[keep], d[keep]
    if not len(d):
        return []
    o = np.lexsort((d, i)); first = np.unique(i[o], return_index=True)[1]
    best = np.full(len(xy), np.inf); partner = np.full(len(xy), -1)
    best[i[o][first]] = d[o][first]; partner[i[o][first]] = j[o][first]
    out = []
    for k in np.argsort(best):
        if not np.isfinite(best[k]):
            break
        da = np.abs(arc - arc[k]); da = np.minimum(da, tot[ci[k]] - da)
        near = (ci == ci[k]) & (da <= window)
        if best[k] > best[near].min():
            continue                                    # not the narrowest point of its stretch
        a, b = xy[k], xy[partner[k]]
        if any(math.dist(a, B) < window and math.dist(b, A) < window for _, A, B in out) or \
                any(math.dist(a, A) < window and math.dist(b, B) < window for _, A, B in out):
            continue                                    # the same white, found from its other side
        if _notch(m, x0, y1, a, b):
            continue                                    # the inside of a V, not a white between strokes
        out.append((float(best[k]), a, b))
    return out


def _notch(m, x0, y1, a, b, small=2500.0):
    """Whether the white across a..b closes off a small pocket on one side (the inside of a V or a sharp notch,
    under `small` square units), rather than joining two open whites, as a cut, slit or seam does."""
    from scipy import ndimage as ndi
    from PIL import Image, ImageDraw
    pad = 60
    white = np.pad(~m, pad, constant_values=True)
    img = Image.fromarray(white.astype(np.uint8) * 255)
    P = lambda q: (q[0] - x0 + pad, y1 - q[1] + pad)
    ImageDraw.Draw(img).line([P(a), P(b)], fill=0, width=3)
    lab, _ = ndi.label(np.asarray(img) > 0)
    u = (b - a) / np.linalg.norm(b - a); nrm = np.array([-u[1], u[0]]); mid = (a + b) / 2
    sizes = []
    for sgn in (1, -1):
        c, r = P(mid + sgn * 4 * nrm)
        r, c = int(round(r)), int(round(c))
        if not (0 <= r < lab.shape[0] and 0 <= c < lab.shape[1]) or lab[r, c] == 0:
            return False
        sizes.append(int((lab == lab[r, c]).sum()))
    return min(sizes) < small


def _across(p, a, b, r=20.0):
    """The narrowest white now between the outline near a (on a's side of the gap) and near b: (width, point on
    a's side, its contour, its arc position, point on b's side, its contour, its arc position)."""
    xy, ci, arc = samples(contours(p), 1.0)
    u = (a - b) / np.linalg.norm(a - b); mid = (a + b) / 2
    side = (xy - mid) @ u
    A = np.where((np.linalg.norm(xy - a, axis=1) < r) & (side > 0))[0]
    B = np.where((np.linalg.norm(xy - b, axis=1) < r) & (side < 0))[0]
    if not len(A) or not len(B):
        return None
    D = np.linalg.norm(xy[A][:, None] - xy[B][None], axis=2)
    ka, kb = np.unravel_index(int(np.argmin(D)), D.shape)
    A, B = A[ka], B[kb]
    return float(D[ka, kb]), xy[A], int(ci[A]), float(arc[A]), xy[B], int(ci[B]), float(arc[B])


def _behind(m, x0, y1, pt, u, cap=400):
    """How far the ink runs from pt in the direction u (the stroke's thickness behind a wall)."""
    for t in range(2, cap):
        x, y = pt + u * t
        c, r = int(round(x - x0)), int(round(y1 - y))
        if not (0 <= r < m.shape[0] and 0 <= c < m.shape[1]) or not m[r, c]:
            return float(t)
    return float(cap)


def _shift(p, i, s0, move, reach):
    """Move contour i's outline by `move` where it passes arc position s0, fading (cosine) to nothing `reach`
    units of outline either side, as spur() moves a spur's end."""
    cs = contours(p)
    start, segs = cs[i]
    L = seg_lengths(start, segs); pos = np.r_[0, np.cumsum(L)]; total = pos[-1]
    def wt(s):
        dd = abs(s - s0); dd = min(dd, total - dd)
        return 0.5 * (1 + math.cos(math.pi * dd / reach)) if dd < reach else 0.0
    mv = lambda q, w: (q[0] + move[0] * w, q[1] + move[1] * w)
    new = []
    for j, (kk, pts) in enumerate(segs):
        w0, w1 = wt(pos[j]), wt(pos[j + 1])
        new.append(('L', [mv(pts[0], w1)]) if kk == 'L' else ('C', [mv(pts[0], w0), mv(pts[1], w1), mv(pts[2], w1)]))
    cs[i] = [new[-1][1][-1], new]
    return pathops.simplify(path_of(cs), fix_winding=True, keep_starting_points=True, clockwise=False)


def grow_back(q, rx, stem, slope=None, limit=45.0, reach=110.0, spur_share=0.4, tolerance=0.6):
    """Give a narrowed outline its weight back: every edge moved out by rx across (bolden.grow_nodes, which keeps
    the drawing's nodes), then each white narrower than `limit` (a cut, a slit, a seam) put back to its width before
    the growth, by the side that ends there: a spur or hook (a side under `spur_share` of a stem thick behind the
    white) drawn back along the gap, as spur() draws it; between two separate strokes, the right-hand one moved over
    bodily, as cut() moves it; otherwise (one stroke, or a piece inside another) half each. Where a white cannot be
    put back (the growth would close it), the glyph keeps the narrowing alone. Returns the outline and, for each
    white, (width before, width after, how). With `slope` (the slant's matrix), the whites are measured and put
    back as the sloped style will have them: the growth and the moves are across, which the slant keeps."""
    import bolden
    if slope is not None:
        from fontTools.misc.transform import Transform
        g, report = grow_back(SH.transform(q, slope), rx, stem, None, limit, reach, spur_share, tolerance)
        return SH.transform(g, tuple(Transform(*slope).inverse())), report
    necks = white_necks(q, limit)
    g = bolden.grow_nodes(q, rx, 0.01, fallback=bolden.grow)      # across only (grow() needs some height)
    if not necks:
        return (g, []) if _topology(g) == _topology(q) else (q, [('kept narrow',)])
    m, x0, y1 = ink_raster(q)
    comps = bolden.components(q)
    pts = [samples(contours(c), 4.0)[0] for c in comps]
    piece = lambda pt: min(range(len(comps)), key=lambda c: float(np.min(np.linalg.norm(pts[c] - pt, axis=1))))
    centre_x = lambda c: (bounds(comps[c])[0] + bounds(comps[c])[2]) / 2
    within = lambda s, t: s[0] >= t[0] and s[1] >= t[1] and s[2] <= t[2] and s[3] <= t[3]
    offset = {}                                             # each piece moved over so far
    # the growth was across, so a side is put back across too (heights never move): the move that widens the
    # white by `amount` where it runs in direction v
    across = lambda v, amount: np.array([math.copysign(amount / max(abs(v[0]), 0.3), v[0]), 0.0])
    report = []
    for w0, a, b in sorted(necks, key=lambda n: (n[1][0] + n[2][0]) / 2):        # left to right
        u = (a - b) / np.linalg.norm(a - b)
        ta, tb = _behind(m, x0, y1, a, u), _behind(m, x0, y1, b, -u)
        pa, pb = piece(a), piece(b)
        nested = pa != pb and (within(bounds(comps[pa]), bounds(comps[pb])) or within(bounds(comps[pb]), bounds(comps[pa])))
        if nested:
            mode = 'both'                                   # a letter inside a ring (@, (c), (R))
        elif min(ta, tb) <= spur_share * stem:
            mode = 'spur'
        elif pa != pb:
            mode = 'piece'                                  # two strokes: the right-hand one moves over
        else:
            mode = 'both'
        moving_a = centre_x(pa) > centre_x(pb) if mode == 'piece' else ta <= tb
        for _ in range(6):
            aa, bb = a + offset.get(pa, 0.0), b + offset.get(pb, 0.0)
            now = _across(g, aa, bb)
            if now is None:
                break
            w, A, ia, sa, B, ib, sb = now
            if abs(w - w0) < 0.25:
                break
            dlt = w0 - w
            if mode == 'piece':
                # the right-hand stroke moves over, and the strokes beyond it with it (w's third)
                which, pt, mv = (pa, A, across(u, dlt)) if moving_a else (pb, B, across(-u, dlt))
                gc = bolden.components(g)
                k = min(range(len(gc)), key=lambda c: float(np.min(np.linalg.norm(samples(contours(gc[c]), 2.0)[0] - pt, axis=1))))
                cx = lambda c: (bounds(c)[0] + bounds(c)[2]) / 2
                moved = [j for j, c in enumerate(gc) if j == k or cx(c) > cx(gc[k])]
                g = bolden.concat([translate(c, *mv) if j in moved else c for j, c in enumerate(gc)])
                for c in range(len(comps)):
                    if c == which or centre_x(c) > centre_x(which):
                        offset[c] = offset.get(c, 0.0) + mv
            elif mode == 'both':
                g = _shift(g, ia, sa, across(u, dlt / 2), reach)
                again = _across(g, aa, bb)
                if again is not None:
                    g = _shift(g, again[5], again[6], across(-u, dlt / 2), reach)
            elif moving_a:
                g = _shift(g, ia, sa, across(u, dlt), reach)
            else:
                g = _shift(g, ib, sb, across(-u, dlt), reach)
        after = _across(g, a + offset.get(pa, 0.0), b + offset.get(pb, 0.0))
        report.append((round(w0, 1), None if after is None else round(after[0], 1), mode))
    if any(w1 is None or abs(w1 - w0) > tolerance for w0, w1, _ in report) or _topology(g) != _topology(q):
        return q, report + [('kept narrow',)]
    return g, report


def _topology(p):
    """(pieces, counters) of the outline as it will be filled."""
    import bolden, glyphs
    a = [bolden.area(c) for c in glyphs.contours(pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False))]
    return sum(x > 0 for x in a), sum(x < 0 for x in a)


def extremes(f):
    """After the slant: a node where each sloped curve passes its extreme, as the upright has them; then, where the
    constructions ask for it, each outline settled on the unit grid (settled())."""
    import build2, finish
    c = load().get('constructions', {}).get('italic_settle', {})
    for n, p in list(f.final.items()):
        if not bounds(p):
            continue
        rec = RecordingPen(); p.draw(rec)
        if any(op == 'qCurveTo' for op, _ in rec.value):
            q = p                                       # pathops' exact quadratics: settle() reads them as cubics
        else:
            out = [finish._split_extrema([[k, list(q)] for k, q in segs]) for segs in finish._contours(rec.value)]
            q = pathops.Path(); replayRecording(finish._record(out), q.getPen())
            q = build2.final_clean(q)
        f.final[n] = settled(q, c['tiny']) if c.get('value') else q


def settled(p, tiny, passes=3):
    """settle.settle_path (as Carrick's outlines are settled) with pieces under `tiny` units folded, repeated until
    it changes nothing: the joins that rounding after the slant left bent by a few degrees made smooth again, and
    the pieces of a unit or two that splitting the sloped curves at their extremes left folded into one node."""
    import settle
    from fontTools.pens.recordingPen import RecordingPen as R
    keep = settle.TINY
    settle.TINY = tiny
    try:
        for _ in range(passes):
            q = settle.settle_path(p)
            a, b = R(), R(); p.draw(a); q.draw(b)
            if a.value == b.value:
                break
            p = q
    finally:
        settle.TINY = keep
    return p


def marks(f, path=EDITS):
    """Construction values for the marks (after Font2.make_marks, before the letters, composites and symbols are
    made from them): the gap above the letter, í's acute, the comma and the marks made from it, and the ponc."""
    c = load(path).get('constructions', {})
    if 'accent_gap' in c:
        f.gap = c['accent_gap']['value']
    if 'iacute_rise' in c and 'iacute' in getattr(f, 'own_acute', {}):
        shape, dx = f.own_acute['iacute']
        f.own_acute['iacute'] = (steepen(shape, c['iacute_rise']['value']), dx)
    if 'comma' in c:
        comma(f, c['comma'])
    if 'ponc' in c:
        ponc(f, c['ponc'])


# ---------------------------------------------------------------- the second pass: constructions
def steepen(shape, rise):
    """An acute drawn steeper: its right end raised `rise` units over its width (a vertical shear about its left
    end), so its left end, its width and each column's thickness stay as drawn."""
    x0, y0, x1, y1 = bounds(shape)
    k = rise / (x1 - x0)
    return SH.transform(shape, (1, k, 0, 1, 0, -k * x0))


def comma_tail(dot, root, inner, tip, corner):
    """The comma: the period with a tail drawn down to the left, as the builder draws it (build2.punctuation), in
    the dot's frame (shares of its width w and height h, depths below its foot). The tail's outer side leaves the dot
    at its right extreme, so the two make one outline there; `root` and `inner` set the tail's inner side."""
    dx0, dy0, dx1, dy1 = bounds(dot); w, h = dx1 - dx0, dy1 - dy0
    ys = np.arange(dy0 + 1.0, dy1 - 0.5, 1.0)
    right = [max((r[1] for r in runs_at(dot, y)), default=-1e9) for y in ys]
    ry = float(ys[int(np.argmax(right))])
    tail = SH.polygon([(dx0 + root * w, ry), (dx1, ry), (dx1 - corner[0] * w, dy0 - corner[1] * h),
                       (dx0 + tip[0] * w, dy0 - tip[1] * h), (dx0 + inner[0] * w, dy0 - inner[1] * h)])
    return SH.union(dot, tail)


def comma(f, c):
    """Redraw the comma and everything made from it, as Font2.punctuation and Font2.make_marks make them: the
    quotes (the comma raised; turned), the semicolon, and the marks taken from the comma (the turned comma above,
    the comma below, the apostrophe caron)."""
    import marks as MK
    from build2 import BOTTOM
    P = f.P; period = P['period']
    cm = comma_tail(period, c['root'], tuple(c['inner']), tuple(c['tip']), tuple(c['corner']))
    cm = translate(cm, -bounds(cm)[0], bounds(period)[3] - bounds(cm)[3])
    P['comma'] = cm
    qtop = f.asc if f.cfg['unicase'] else f.cap
    qr = translate(cm, 0, qtop - bounds(cm)[3]); P['quoteright'] = qr
    b = bounds(qr); ql = SH.rotate(qr, 180, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    P['quoteleft'] = translate(ql, -bounds(ql)[0], qtop - bounds(ql)[3])
    for single, double in (('quoteleft', 'quotedblleft'), ('quoteright', 'quotedblright')):
        q = P[single]; w = bounds(q)[2]
        P[double] = SH.union(q, translate(q, w + 0.45 * w, 0))
    ph = bounds(period)[3]; top_dot = translate(period, 0, f.xh - ph)
    P['semicolon'] = SH.union(cm, translate(top_dot, (bounds(cm)[2] - bounds(period)[2]) / 2, 0))
    small = SH.transform(cm, (0.8, 0, 0, 0.8, 0, 0)); sb = bounds(small)
    made = {'commaturned': MK.centre(SH.rotate(small, 180, (sb[0] + sb[2]) / 2, (sb[1] + sb[3]) / 2)),
            'commabelow': MK.centre(SH.transform(cm, (0.85, 0, 0, 0.85, 0, 0)), top=False),
            'caronvert': MK.centre(SH.transform(qr, (0.85, 0, 0, 0.85, 0, 0)))}
    for k, m in made.items():
        f.marks[k] = m
        f.case_marks[k] = m if k in BOTTOM else SH.transform(m, (1, 0, 0, 0.82, 0, 0))


def ponc(f, c):
    """The ponc (dot above) and every top mark on the ascender letters, through Font2.attach (so the precomposed
    letters and the mark feature's anchors agree): on b and d over the bowl, beside the ascender, as Hayes sets
    ḃ in his 1974 lettering of the face (Bolger fig. 204): centred over the counter and on the height of the
    ascender above the x-height, and at least `clear` from the ascender; on f above the stem, `above` clear of it."""
    from build2 import BOTTOM, top_under
    from scipy.spatial import cKDTree
    import letters
    orig = f.attach
    bowl, above, clear = set(c['beside']), c['above'], c['clear']

    def place(base):
        """(centre x, foot y) of the dot over the bowl of b or d."""
        xh, asc = f.xh, f.asc
        s0, s1 = letters.stem_at(base, xh + 0.6 * (asc - xh), 'left')
        runs = runs_at(base, 0.5 * xh)
        gaps = [(a[1], b[0]) for a, b in zip(runs, runs[1:])]
        counter = min(gaps, key=lambda g: min(abs(g[0] - s1), abs(g[1] - s0)))
        cx = (counter[0] + counter[1]) / 2
        away = 1.0 if cx > (s0 + s1) / 2 else -1.0
        dot = f.marks['dot']; d0, e0, d1, e1 = bounds(dot)
        stem = SH.op(base, SH.polygon([(-1e4, xh + 1), (1e4, xh + 1), (1e4, 1e4), (-1e4, 1e4)]), pathops.PathOp.INTERSECTION)
        tree = cKDTree(samples(contours(stem), 1.0)[0])
        mid = xh + (asc - xh) / 2 - (e1 - e0) / 2
        def at(x):
            foot = max(top_under(base, x - (d1 - d0) / 2, x + (d1 - d0) / 2) + f.gap, mid)
            m = translate(dot, x - (d0 + d1) / 2, foot - e0)
            return foot, float(tree.query(samples(contours(m), 1.0)[0])[0].min())
        if at(cx)[1] < clear:                       # moved away from the ascender only as far as it needs
            lo, hi = 0.0, 300.0
            for _ in range(14):
                if at(cx + away * (lo + hi) / 2)[1] >= clear:
                    hi = (lo + hi) / 2
                else:
                    lo = (lo + hi) / 2
            cx += away * hi
        return cx, at(cx)[0]

    def attach(base_name, base, mark_kind, upper, stack_top=None):
        letter = base_name.split('.')[0]
        if upper or stack_top is not None or mark_kind in BOTTOM or mark_kind == 'caronvert' or \
                letter not in bowl and letter not in above:
            return orig(base_name, base, mark_kind, upper, stack_top)
        if letter in above:
            return translate(orig(base_name, base, mark_kind, upper, stack_top), 0, above[letter] - f.gap)
        cx, foot = place(base)
        m = f.marks[mark_kind]; b = bounds(m)
        return translate(m, cx - (b[0] + b[2]) / 2, foot - b[1])

    f.attach = attach
