"""Kilfane's studio finishing: the consistency a type studio gives a hand-drawn alphabet.

The traces follow the prints faithfully, and the prints carry the artwork's small inconsistencies:
the paste-up and photography of N516 set letters up to two source pixels (about 12 font units) off
one another, and hand-drawn stems differ by a pixel. Three passes of the release build
(scripts/build_candidate.py), each set out with its reasons in
research/kilfane-sheet-frame/judged-edits.json ("finishing"):

shapes(font)    on the finished traces, before anything is derived from them (bold, sloped styles,
                accents, punctuation): each listed letter's flat tops and descenders are put on the
                face's lines, its round tops on the overshoot lines (a vertical map that keeps every
                curve's tangents), and its straight stems are given the face's stem weight by moving
                their edges, at most three units each.
kern(font)      the builder's kerning, eased where it set quotes and hyphens onto lowercase, and pairs
                whose white is wider than the face's own closed by part of the difference.
outlines(font)  on the final outlines of every style: one node where a fitter (or the bold's pen) left
                a chain, tangents made continuous where the outline turns by a few degrees, no piece
                shorter than two units, nodes at the extremes with level handles; each change kept
                only within TOL units of the outline it replaces (a unit more where a kink is turned
                or a corner chain rounded), and a glyph left as it was if its topology would change.
"""
import json, math
from pathlib import Path
import numpy as np
import pathops
from fontTools.pens.recordingPen import RecordingPen, replayRecording
import finish as FN

ROOT = Path(__file__).resolve().parent.parent
EDITS = ROOT / 'research' / 'kilfane-sheet-frame' / 'judged-edits.json'


# ---------------------------------------------------------------- outline <-> segments
def _cubic(rec):
    """A recording with its quadratic splines (pathops' offsets draw them) as the cubics they are."""
    out, cur = [], None
    for op, a in rec:
        if op == 'qCurveTo':
            pts = [cur] + list(a)
            offs, end = pts[1:-1], pts[-1]
            ons = [pts[0]] + [((offs[i][0] + offs[i + 1][0]) / 2, (offs[i][1] + offs[i + 1][1]) / 2)
                              for i in range(len(offs) - 1)] + [end]
            for i, q in enumerate(offs):
                p0, p2 = ons[i], ons[i + 1]
                out.append(('curveTo', ((p0[0] + 2 / 3 * (q[0] - p0[0]), p0[1] + 2 / 3 * (q[1] - p0[1])),
                                        (p2[0] + 2 / 3 * (q[0] - p2[0]), p2[1] + 2 / 3 * (q[1] - p2[1])), p2)))
            if not offs:
                out.append(('lineTo', (end,)))
            cur = end
            continue
        out.append((op, a))
        if a:
            cur = a[-1]
    return out


def segments(p):
    rec = RecordingPen(); p.draw(rec)
    if any(op not in ('moveTo', 'lineTo', 'curveTo', 'qCurveTo', 'closePath', 'endPath') for op, _ in rec.value):
        raise ValueError('unexpected pen operation')
    return [[[k, [tuple(map(float, q)) for q in pts]] for k, pts in c] for c in FN._contours(_cubic(rec.value))]


def path(contours):
    q = pathops.Path(); replayRecording(FN._record(contours), q.getPen()); return q


def _bez(a, seg, n=24):
    k, p = seg; a = np.array(a, float)
    if k == 'L':
        b = np.array(p[0], float); return np.array([a + (b - a) * t for t in np.linspace(0, 1, 3)])
    c1, c2, b = (np.array(q, float) for q in p); t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t * t * c2 + t ** 3 * b


def polygons(contours, n=24):
    out = []
    for segs in contours:
        pts = [_bez(FN._start(segs, i), s, n)[1:] for i, s in enumerate(segs)]
        out.append(np.vstack(pts))
    return out


def crossings(polys, y):
    xs = []
    for P in polys:
        a, b = P, np.roll(P, -1, axis=0)
        m = ((a[:, 1] <= y) & (b[:, 1] > y)) | ((b[:, 1] <= y) & (a[:, 1] > y))
        if m.any():
            t = (y - a[m, 1]) / (b[m, 1] - a[m, 1]); xs += list(a[m, 0] + t * (b[m, 0] - a[m, 0]))
    xs = sorted(xs)
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


def column(polys, x):
    ys = []
    for P in polys:
        a, b = P, np.roll(P, -1, axis=0)
        m = ((a[:, 0] <= x) & (b[:, 0] > x)) | ((b[:, 0] <= x) & (a[:, 0] > x))
        if m.any():
            t = (x - a[m, 0]) / (b[m, 0] - a[m, 0]); ys += list(a[m, 1] + t * (b[m, 1] - a[m, 1]))
    return sorted(ys)


def bbox(polys):
    pts = np.vstack(polys); return pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max()


# ---------------------------------------------------------------- heights
def feature(polys, band, edge='top', below=None, above=None):
    """The highest (or lowest) ink within an x band (fractions of the glyph's width), optionally only
    ink below or above a height."""
    x0, _, x1, _ = bbox(polys); best = None
    for x in np.linspace(x0 + band[0] * (x1 - x0) + 0.5, x0 + band[1] * (x1 - x0) - 0.5, 80):
        ys = [y for y in column(polys, x) if (below is None or y <= below) and (above is None or y >= above)]
        if not ys:
            continue
        v = max(ys) if edge == 'top' else min(ys)
        best = v if best is None else (max(best, v) if edge == 'top' else min(best, v))
    return best


class YMap:
    """A monotone piecewise-linear map of heights through anchors (y -> y'). Past the end anchors it
    continues at the end piece's slope, or rigidly (slope 1) where that side is to stay as drawn."""
    def __init__(self, anchors, rigid_top=False, rigid_bottom=False):
        a = sorted(anchors); self.y = np.array([p[0] for p in a]); self.v = np.array([p[1] for p in a])
        assert len(a) >= 2 and np.all(np.diff(self.y) > 0) and np.all(np.diff(self.v) > 0), anchors
        self.rigid_top, self.rigid_bottom = rigid_top, rigid_bottom

    def slope(self, y, side=1):
        """The slope at y; at an anchor, that of the piece on `side` (+1 above, -1 below)."""
        y = y + 1e-6 * side
        if y > self.y[-1] and self.rigid_top or y < self.y[0] and self.rigid_bottom:
            return 1.0
        i = int(np.clip(np.searchsorted(self.y, y) - 1, 0, len(self.y) - 2))
        return (self.v[i + 1] - self.v[i]) / (self.y[i + 1] - self.y[i])

    def __call__(self, y):
        if y >= self.y[-1]:
            return self.v[-1] + (y - self.y[-1]) * self.slope(y)
        if y <= self.y[0]:
            return self.v[0] + (y - self.y[0]) * self.slope(y, -1)
        return float(np.interp(y, self.y, self.v))


def remap(contours, f):
    """Each node to (x, f(y)); each handle kept on its node's tangent, scaled by the map's slope at the
    node, so a smooth join stays smooth and a level handle stays level."""
    def handle(node, node2, h):
        dy = h[1] - node[1]
        return (h[0], node2[1] + dy * f.slope(node[1], 1 if dy >= 0 else -1))
    out = []
    for segs in contours:
        new = []
        for i, (k, p) in enumerate(segs):
            end = p[-1]; e2 = (end[0], f(end[1]))
            if k == 'L':
                new.append(['L', [e2]]); continue
            a = FN._start(segs, i); a2 = (a[0], f(a[1]))
            new.append(['C', [handle(a, a2, p[0]), handle(end, e2, p[1]), e2]])
        out.append(new)
    return out


def remap_across(contours, top, bottom):
    """Heights scaled about the baseline by a factor that varies across the letter: top and bottom are
    [(x, factor)], interpolated in x (constant beyond the ends). Handles follow their node's Jacobian."""
    def g(feats, x):
        if not feats:
            return 0.0, 0.0
        xs, ks = zip(*sorted(feats))
        v = float(np.interp(x, xs, ks))
        i = int(np.searchsorted(xs, x))
        d = 0.0 if i == 0 or i >= len(xs) else (ks[i] - ks[i - 1]) / (xs[i] - xs[i - 1])
        return v, d
    def node(pt):
        x, y = pt; v, d = g(top if y >= 0 else bottom, x)
        return (x, y * (1 + v)), (y * d, 1 + v)
    def handle(n, n2, J, h):
        dx, dy = h[0] - n[0], h[1] - n[1]
        return (n2[0] + dx, n2[1] + J[0] * dx + J[1] * dy)
    out = []
    for segs in contours:
        new = []
        for i, (k, p) in enumerate(segs):
            end = p[-1]; e2, Je = node(end)
            if k == 'L':
                new.append(['L', [e2]]); continue
            a = FN._start(segs, i); a2, Ja = node(a)
            new.append(['C', [handle(a, a2, Ja, p[0]), handle(end, e2, Je, p[1]), e2]])
        out.append(new)
    return out


def align_heights(contours, specs, lines):
    """specs: [{band, edge, line, below?, above?}] -> the map putting each measured feature on its line.
    A dict {"across": [...]} instead scales each feature's part of the letter by its own factor."""
    polys = polygons(contours)
    if isinstance(specs, dict):
        x0, _, x1, _ = bbox(polys); top, bottom, report = [], [], []
        for s in specs['across']:
            edge = s.get('edge', 'top')
            y = feature(polys, s['band'], edge, s.get('below'), s.get('above'))
            target = float(lines[s['line']]); report.append((s['line'], round(y, 1), target))
            xc = x0 + (s['band'][0] + s['band'][1]) / 2 * (x1 - x0)
            (top if edge == 'top' else bottom).append((xc, target / y - 1))
        return remap_across(contours, top, bottom), report
    top, bottom, report = [(0.0, 0.0)], [(0.0, 0.0)], []
    for s in specs:
        y = feature(polys, s['band'], s.get('edge', 'top'), s.get('below'), s.get('above'))
        target = float(lines[s['line']])
        report.append((s['line'], round(y, 1), target))
        (top if s.get('edge', 'top') == 'top' else bottom).append((y, target))
    anchors = sorted(set(top + bottom))
    if all(abs(a - b) < 0.25 for a, b in anchors):
        return contours, report
    # a side with nothing measured (a descender, say) stays as drawn
    f = YMap(anchors, rigid_top=len(top) == 1, rigid_bottom=len(bottom) == 1)
    return remap(contours, f), report


# ---------------------------------------------------------------- stems
def _near_vertical(a, b, deg=20.0):
    dx, dy = b[0] - a[0], b[1] - a[1]
    return math.hypot(dx, dy) > 1e-6 and abs(math.degrees(math.atan2(abs(dx), abs(dy)))) < deg


def _edge_nodes(contours, x, y):
    """The nodes of the straight edge that crosses height y at x: the segment crossing there and its
    near-vertical neighbours, as (contour, segment index) of each node (a node ends its segment)."""
    best = None
    for ci, segs in enumerate(contours):
        for si, s in enumerate(segs):
            pts = _bez(FN._start(segs, si), s, 48)
            for a, b in zip(pts[:-1], pts[1:]):
                if (a[1] - y) * (b[1] - y) <= 0 and a[1] != b[1]:
                    xc = a[0] + (y - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                    if best is None or abs(xc - x) < best[0]:
                        best = (abs(xc - x), ci, si)
    _, ci, si = best; segs = contours[ci]; n = len(segs)
    straight = lambda j: _near_vertical(FN._start(segs, j), segs[j][1][-1])
    def tangent(j, at_end):
        k, p = segs[j]; a = FN._start(segs, j)
        if k == 'C':
            u, v = (p[1], p[2]) if at_end else (a, p[0])
            if math.dist(u, v) > 1e-6:
                return _near_vertical(u, v)
        return straight(j)
    nodes, fwd, bwd = set(), None, None
    if straight(si):
        nodes |= {(si - 1) % n, si}; fwd, bwd = si, (si - 1) % n
    else:                         # a curve that turns into the stem (a bowl's inside): from its vertical end
        if tangent(si, True):
            nodes.add(si); fwd = si
        if tangent(si, False):
            nodes.add((si - 1) % n); bwd = (si - 1) % n
    j = fwd
    for _ in range(n if fwd is not None else 0):           # forward: segment j+1 runs from node j to j+1
        if not straight((j + 1) % n):
            break
        j = (j + 1) % n; nodes.add(j)
    j = bwd
    for _ in range(n if bwd is not None else 0):           # back: segment j runs from node j-1 to j
        if not straight(j):
            break
        j = (j - 1) % n; nodes.add(j)
    return ci, sorted(nodes)


def _move_nodes(segs, nodes, dx):
    n = len(segs)
    for i in nodes:
        k, p = segs[i]
        p[-1] = (p[-1][0] + dx, p[-1][1])
        if k == 'C':
            p[1] = (p[1][0] + dx, p[1][1])
        k2, p2 = segs[(i + 1) % n]
        if k2 == 'C':
            p2[0] = (p2[0][0] + dx, p2[0][1])


def stem(contours, y, run):
    polys = polygons(contours); runs = crossings(polys, y)
    return runs[run] if runs else None


def harmonise_stems(contours, specs, height, target, limit):
    """specs: [[fraction of height, run index]]: each such stem given `target` width, its two edges
    moved apart or together by at most `limit` units each."""
    report = []
    for frac, run in specs:
        y = frac * height
        x0, x1 = stem(contours, y, run); w = x1 - x0
        d = float(np.clip((target - w) / 2, -limit, limit))
        if abs(d) < 0.25:
            report.append((frac, run, round(w, 1), round(w, 1))); continue
        cl, left = _edge_nodes(contours, x0, y); cr, right = _edge_nodes(contours, x1, y)
        if not left or not right or (cl == cr and set(left) & set(right)):
            report.append((frac, run, round(w, 1), None)); continue
        _move_nodes(contours[cl], left, -d); _move_nodes(contours[cr], right, d)
        a, b = stem(contours, y, run)
        report.append((frac, run, round(w, 1), round(b - a, 1)))
    return contours, report


# ---------------------------------------------------------------- the passes
def load(edits=EDITS):
    return json.loads(Path(edits).read_text(encoding='utf-8'))['finishing']


def shapes(font, edits=EDITS):
    """Heights and stems of the traced letters (font.P, in font units), after finishing; snaps the
    letters onto the baseline first, as the builder would."""
    spec = load(edits)
    font.S_regular = font.stem_width()
    font.snap()
    lines = spec['lines']; font.studio = {}
    for name, h in spec['heights'].items():
        if name not in font.P:
            continue
        c, rep = align_heights(segments(font.P[name]), h, lines)
        font.P[name] = path(c); font.studio.setdefault(name, {})['heights'] = rep
    for group in spec['stems'].values():
        height = lines[group['height']]
        for name, st in group['glyphs'].items():
            if name not in font.P:
                continue
            c, rep = harmonise_stems(segments(font.P[name]), st, height, group['target'], group['limit'])
            font.P[name] = path(c); font.studio.setdefault(name, {})['stems'] = rep


# ---------------------------------------------------------------- outline finishing
TOL, SHORT, KINK = 1.5, 6.0, 12.0            # units a change may stray; a tiny piece; a kink (degrees)


def _tan_out(segs, i):
    """Unit tangent leaving the start of segment i."""
    k, p = segs[i]; a = np.array(FN._start(segs, i))
    for q in (p if k == 'C' else p[:1]):
        d = np.array(q) - a
        if np.linalg.norm(d) > 1e-6:
            return d / np.linalg.norm(d)
    return None


def _tan_in(segs, i):
    """Unit tangent arriving at the end of segment i."""
    k, p = segs[i]; e = np.array(p[-1])
    for q in ((p[1], p[0], FN._start(segs, i)) if k == 'C' else (FN._start(segs, i),)):
        d = e - np.array(q)
        if np.linalg.norm(d) > 1e-6:
            return d / np.linalg.norm(d)
    return None


def _angle(u, v):
    if u is None or v is None:
        return 180.0
    return math.degrees(math.atan2(abs(u[0] * v[1] - u[1] * v[0]), u[0] * v[0] + u[1] * v[1]))


def _samples(a, seg, step=2.0):
    pts = _bez(a, seg, 200 if seg[0] == 'C' else 2)
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    n = max(6, int(L[-1] / step))
    s = np.linspace(0, L[-1], n)
    return np.column_stack([np.interp(s, L, pts[:, 0]), np.interp(s, L, pts[:, 1])])


def _hausdorff(A, B):
    from scipy.spatial import cKDTree
    return max(cKDTree(B).query(A)[0].max(), cKDTree(A).query(B)[0].max())


REF = None                    # the contour as it was before finishing (a KD tree of its samples)


def _err(old, new):
    """How far a replacement strays: from the pieces it replaces, and from the original outline."""
    e = _hausdorff(old, new)
    return max(e, REF.query(new)[0].max()) if REF is not None else e


def _bulges(c, tol=0.5):
    """A cubic passes an extreme in x or y between its ends by more than tol."""
    import curvefit as CF
    c = np.asarray(c, float)
    for ax in (0, 1):
        for t in CF._extrema_t(c, ax):
            if 0.06 < t < 0.94:
                v = CF._bez(c, [t])[0][ax]
                if min(abs(v - c[0][ax]), abs(v - c[3][ax])) > tol and (v - c[0][ax]) * (v - c[3][ax]) > 0:
                    return True
    return False


def _merge(segs, i, tol):
    """Segments i and i+1 as one, if one segment draws them within tol units: (segment, error) or None."""
    import curvefit as CF
    n = len(segs); j = (i + 1) % n
    A, B = segs[i], segs[j]; p0 = FN._start(segs, i); p1 = A[1][-1]; p3 = B[1][-1]
    pts = np.vstack([_samples(p0, A), _samples(p1, B)[1:]])
    lens = (math.dist(p0, p1), math.dist(p1, p3))
    if A[0] == 'L' and B[0] == 'L':
        q = _samples(p0, ['L', [p3]])
        err = _err(pts, q)
        if err <= tol:
            return ['L', [p3]], err
        if max(lens) > 4 * SHORT:
            return None                                     # two rules meeting at an angle
    turn = _angle(_tan_in(segs, i), _tan_out(segs, j))
    if turn > KINK:
        return None                                         # a corner stays a corner
    for k, L in zip((A[0], B[0]), lens):
        if k == 'L' and L > (4 * SHORT if turn < 3 else SHORT):
            return None                                     # a straight run stays straight
    t1 = _tan_out(segs, i); t2 = _tan_in(segs, j)
    if t1 is None or t2 is None:
        return None
    u = CF._chord_param(pts); P = np.array(pts)
    ctrl = CF._generate(P, u, t1, -t2)
    for _ in range(6):
        u = CF._reparam(ctrl, P, u); ctrl = CF._generate(P, u, t1, -t2)
    if _bulges(ctrl):
        return None
    seg = ['C', [tuple(ctrl[1]), tuple(ctrl[2]), tuple(p3)]]
    err = _err(pts, _samples(p0, seg))
    return (seg, err) if err <= tol else None


def _fit(pts, t1, t2):
    """One cubic through sampled points from pts[0] to pts[-1], leaving along t1 and arriving along t2."""
    import curvefit as CF
    P = np.asarray(pts, float); u = CF._chord_param(P)
    ctrl = CF._generate(P, u, t1, -t2)
    for _ in range(6):
        u = CF._reparam(ctrl, P, u); ctrl = CF._generate(P, u, t1, -t2)
    return ctrl


FILLET = 32.0                 # a run of pieces shorter than this, turning a corner, is one rounded corner


def _fillets(segs, tol):
    """A corner that a fitter or the bold's pen drew as a chain of short pieces, each turning a little,
    becomes one curve tangent to the strokes either side, where that curve stays within tol."""
    changed = True
    while changed and len(segs) > 4:
        changed = False
        n = len(segs)
        short = [math.dist(FN._start(segs, i), segs[i][1][-1]) < FILLET for i in range(n)]
        if all(short):
            return segs
        start = next(i for i in range(n) if not short[i])
        i = 1
        while i < n:
            a = (start + i) % n
            if not short[a]:
                i += 1; continue
            run = []
            while i < n and short[(start + i) % n]:
                run.append((start + i) % n); i += 1
            if len(run) < 2:
                continue
            before, after = (run[0] - 1) % n, (run[-1] + 1) % n
            t1, t2 = _tan_in(segs, before), _tan_out(segs, after)
            total = _angle(t1, t2)
            if not 20 <= total <= 120:
                continue
            # the strokes either side must enter and leave the run smoothly (else it is a real corner)
            if _angle(t1, _tan_out(segs, run[0])) > 60 or _angle(_tan_in(segs, run[-1]), t2) > 60:
                continue
            p0 = FN._start(segs, run[0])
            pts = np.vstack([_samples(FN._start(segs, r), segs[r]) for r in run])
            ctrl = _fit(pts, t1, t2)
            seg = ['C', [tuple(ctrl[1]), tuple(ctrl[2]), tuple(segs[run[-1]][1][-1])]]
            if _bulges(ctrl) or _err(pts, _samples(p0, seg)) > tol:
                continue
            keep = run[-1]
            segs[keep] = seg
            for r in sorted(run[:-1], reverse=True):
                del segs[r]
            changed = True
            break
    return segs


def _drop_specks(segs, tol, speck=2.0):
    """A piece under two units long (rounding left it at a corner) goes: the next piece starts where it did."""
    i = 0
    while i < len(segs) and len(segs) > 3:
        a, e = FN._start(segs, i), segs[i][1][-1]
        if math.dist(a, e) >= speck:
            i += 1; continue
        j = (i + 1) % len(segs); k, p = segs[j]
        d = (a[0] - e[0], a[1] - e[1])
        new = ['C', [(p[0][0] + d[0], p[0][1] + d[1]), p[1], p[2]]] if k == 'C' else [k, list(p)]
        pts = _samples(a, new)
        if REF is not None and REF.query(pts)[0].max() > tol:
            i += 1; continue
        segs[j] = new; del segs[i]
    return segs


def _is_extreme(segs, i):
    """Node i is a horizontal or vertical extreme of its contour's neighbourhood (a node to keep)."""
    t_in, t_out = _tan_in(segs, i), _tan_out(segs, (i + 1) % len(segs))
    if t_in is None or t_out is None or _angle(t_in, t_out) > 2:
        return False
    d = t_in + t_out; n = len(segs)
    node, prev, nxt = segs[i][1][-1], FN._start(segs, i), segs[(i + 1) % n][1][-1]
    for ax, level in ((1, abs(d[1]) < 0.035 * np.linalg.norm(d)), (0, abs(d[0]) < 0.035 * np.linalg.norm(d))):
        # level, and the outline either side falls away from it: an extreme (a run along a flat is not)
        if level and (prev[ax] - node[ax]) * (nxt[ax] - node[ax]) > 0 and \
                min(abs(prev[ax] - node[ax]), abs(nxt[ax] - node[ax])) > 0.5:
            return True
    return False


def tidy(segs, tol=TOL):
    """One contour (segments), finished: merged, smoothed, squared, with nodes at its extremes."""
    segs = [[k, list(p)] for k, p in segs]
    segs = [s for i, s in enumerate(segs) if math.dist(FN._start(segs, i), s[1][-1]) > 0.01 or s[0] == 'C']
    global REF
    from scipy.spatial import cKDTree
    REF = cKDTree(np.vstack([_samples(FN._start(segs, i), s, 1.0) for i, s in enumerate(segs)]))
    segs = _fillets(_drop_specks(segs, tol), tol + 1)      # a corner chain may round by a unit more, as a kink may
    cache = {}
    def candidate(i):
        a, b = segs[i], segs[(i + 1) % len(segs)]
        hit = cache.get((id(a), id(b)))
        if hit is not None and hit[0] is a and hit[1] is b:
            return hit[2]
        m = None if _is_extreme(segs, i) else _merge(segs, i, tol)
        cache[(id(a), id(b))] = (a, b, m)
        return m
    while len(segs) > 3:
        best = None
        for i in range(len(segs)):
            m = candidate(i)
            if m and (best is None or m[1] < best[0]):
                best = (m[1], i, m[0])
        if best is None:
            break
        _, i, seg = best; j = (i + 1) % len(segs)
        segs[j] = seg; del segs[i]
    def guarded(step, segs, dev):
        FN.MAX_DEV = dev
        new = step([[k, list(p)] for k, p in segs])
        pts = np.vstack([_samples(FN._start(new, i), s) for i, s in enumerate(new)])
        return new if REF.query(pts)[0].max() <= dev else segs
    old = FN.MAX_DEV
    try:
        # a kink is turned smooth with a unit more allowance: its handles turn about the node
        for step, dev in ((FN._collapse_short, tol), (FN._merge_flats, tol), (FN._smooth, tol + 1),
                          (FN._split_extrema, tol + 1), (FN._smooth, tol + 1)):
            segs = guarded(step, segs, dev)
    finally:
        FN.MAX_DEV = old
    return segs


def _rounded(segs):
    out = []
    r = lambda q: (float(round(q[0])), float(round(q[1])))
    for i, (k, p) in enumerate(segs):
        if k == 'L':
            out.append(['L', [r(p[0])]]); continue
        a = FN._start(segs, i); e = p[-1]; c1, c2 = list(p[0]), list(p[1])
        for c, n in ((c1, a), (c2, e)):              # level handles stay level on the grid
            for ax in (0, 1):
                if abs(c[ax] - n[ax]) < 0.01:
                    c[ax] = n[ax]
        out.append(['C', [r(c1), r(c2), r(e)]])
    # drop what rounding collapsed
    return [s for i, s in enumerate(out) if math.dist(FN._start(out, i), s[1][-1]) > 0 or
            (s[0] == 'C' and (s[1][0] != s[1][-1] or s[1][1] != s[1][-1]))]


def _area(p):
    from fontTools.pens.areaPen import AreaPen
    ap = AreaPen(); p.draw(ap); return ap.value


def finish_glyph(p, tol=TOL):
    """The finished outline of one final glyph. A contour that finishing would move further than tol plus
    the kink allowance and the grid's half unit is kept as it was, and so is a glyph whose topology or
    area would change."""
    contours = segments(p)
    new = []
    for c in contours:
        if len(c) < 3:
            new.append(c); continue
        t = _rounded(tidy(c, tol))
        if len(t) < 2:
            new.append(c); continue
        A = np.vstack([_samples(FN._start(c, i), s) for i, s in enumerate(c)])
        B = np.vstack([_samples(FN._start(t, i), s) for i, s in enumerate(t)])
        h = _hausdorff(A, B)
        if h > tol + 1.5:
            LOG.append(('contour kept', round(h, 2)))
        new.append(t if h <= tol + 1.5 else c)
    q = path(new)
    s0 = pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)
    s1 = pathops.simplify(q, fix_winding=True, keep_starting_points=False, clockwise=False)
    n0 = len(segments(s0)); n1 = len(segments(s1))
    if n0 != n1 or abs(_area(s1) - _area(s0)) > 0.01 * abs(_area(s0)) + 20:
        LOG.append(('glyph kept', n0, n1, round(_area(s0)), round(_area(s1))))
        return p
    return q


LOG = []                      # what finish_glyph kept as it was, and why (for inspection)


def outlines(font, tol=None):
    """Finish every final outline of a style (font.final), after its spacing, kerning and slant."""
    tol = tol or TOL
    for n, p in list(font.final.items()):
        if n == 'space' or not segments(p):
            continue
        font.final[n] = finish_glyph(p, tol)


# ---------------------------------------------------------------- kerning
LOWER = set('abcdefghijklmnopqrstuvwxyz')


def _profile(p, top, step=8.0):
    ys = np.arange(4, top, step); L = np.full(len(ys), np.nan); R = np.full(len(ys), np.nan)
    for P in polygons(segments(p), 12):
        b = np.roll(P, -1, axis=0)
        for k, y in enumerate(ys):
            m = ((P[:, 1] <= y) & (b[:, 1] > y)) | ((b[:, 1] <= y) & (P[:, 1] > y))
            if m.any():
                t = (y - P[m, 1]) / (b[m, 1] - P[m, 1]); xs = P[m, 0] + t * (b[m, 0] - P[m, 0])
                L[k] = np.nanmin([L[k], xs.min()]); R[k] = np.nanmax([R[k], xs.max()])
    return L, R


def optical_gaps(font, pairs):
    """The white between each pair as a reader sees it: the mean gap across the x-height (the cap height
    between two capitals), each side's depth counted to a fifth of the x-height at most."""
    cache = {}
    dmax = 0.2 * font.xh
    def prof(n, top):
        if (n, top) not in cache:
            cache[n, top] = _profile(font.final[n], top)
        return cache[n, top]
    out = {}
    for a, b in pairs:
        top = font.cap if a[0].isupper() and b[0].isupper() else font.xh     # where a line of text is read
        _, Ra = prof(a, top); Lb, _ = prof(b, top)
        if np.all(np.isnan(Ra)) or np.all(np.isnan(Lb)):
            continue
        ra = np.where(np.isnan(Ra), np.nanmax(Ra) - dmax, np.maximum(Ra, np.nanmax(Ra) - dmax))
        lb = np.where(np.isnan(Lb), np.nanmin(Lb) + dmax, np.minimum(Lb, np.nanmin(Lb) + dmax))
        out[a, b] = float(np.mean(font.adv[a] + lb - ra))
    return out


def kern(font, edits=EDITS):
    """Kilfane's kerning on these outlines: the builder's closest-approach kerning, with its pairs of
    quotes and hyphens over lowercase eased (they set a quote onto the next letter's shoulder and a
    hyphen into c's mouth), and letter pairs whose white is wider than the face's own (n n, H H, H n)
    closed by part of the difference. The builder's collision protection runs after this."""
    spec = load(edits)['kerning']
    pk = font.kern_pairs
    side = lambda names, n: n in LOWER if names == '*lower' else n in names
    for (a, b), k in list(pk.items()):
        for rule in spec['limits']:
            if side(rule['left'], a) and side(rule['right'], b):
                pk[a, b] = max(k, rule['min'])
    letters = [n for n in spec['letters'] if n in font.left_group and n in font.right_group]
    gaps = optical_gaps(font, [(a, b) for a in letters for b in letters])
    # the white of two straight stems: n n, H H, H n or n H. (Where a capital or an ascender meets the
    # next letter's arm, as F meets b, the collision protection after this gives the room back.)
    stem = lambda n: 'H' if n[0].isupper() else 'n'
    font.optical = {}
    for (a, b), g in gaps.items():
        excess = g - gaps[stem(a), stem(b)]
        if excess <= spec['threshold'] or (a, b) in pk:
            continue
        k = max(-int(round(spec['share'] * excess / 5.0)) * 5, spec['max'])
        if k <= -5:
            pk[a, b] = k; font.optical[a, b] = (round(excess, 1), k)
