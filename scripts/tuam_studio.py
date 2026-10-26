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
    builder's 8-unit protection): f's flag over the next ascender or fada is drawn apart, as the cuts are."""
    c = load(path).get('constructions', {}).get('upper_clearance')
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
    """The sloped style's narrowing as an affine transform alone, where the constructions ask for it (returns
    whether it did). The builder grows every narrowed outline by a hair (4.4 units a side) to give the stems
    their weight back, which takes 9 units out of every cut, slit and seam and draws them in short pieces."""
    if load(path).get('constructions', {}).get('italic_condense', {}).get('value') != 'affine':
        return False
    for n, p in list(f.P.items()):
        if bounds(p) is not None:
            f.P[n] = SH.transform(p, (k, 0, 0, 1, 0, 0))
    return True


def extremes(f):
    """After the slant: a node where each sloped curve passes its extreme, as the upright has them."""
    import build2, finish
    for n, p in list(f.final.items()):
        if not bounds(p):
            continue
        rec = RecordingPen(); p.draw(rec)
        if any(op == 'qCurveTo' for op, _ in rec.value):
            continue
        out = [finish._split_extrema([[k, list(q)] for k, q in segs]) for segs in finish._contours(rec.value)]
        q = pathops.Path(); replayRecording(finish._record(out), q.getPen())
        f.final[n] = build2.final_clean(q)


def marks(f, path=EDITS):
    """Construction values for the marks (after Font2.make_marks): the gap above the letter."""
    c = load(path).get('constructions', {})
    if 'accent_gap' in c:
        f.gap = c['accent_gap']['value']
