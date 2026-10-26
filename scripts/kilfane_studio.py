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

The second finishing pass (judged-edits.json, "finishing", the keys named below) completes the bold
and the derived glyphs:

bold_pieces(font)  the sheet's loose marks, rules and chevrons drawn with the bold's pen ("bold_pieces"),
                   called as the pieces are read (build_original_study.specimen_pieces).
bold_joins(font)   the bold's drawn open joins (k, r, 6, 9) kept as a gap taken from the terminal
                   alone, the stem's edge left straight, and the g's tail tip lowered ("bold_joins",
                   "g_tail"), on the bold's letters before anything is derived from them.
symbols(font)      the bold's section drawn from the regular's with the bold's pen, the number sign
                   at the bold's weight ("symbols"), before spacing.
clearances(font)   room after kerning: before a fada over i, and between a bold's capitals
                   ("kerning", "clearances").
corners(font)      a corner a union or the grid left as a run of tiny pieces made one node ("corners").

The third pass (the same file, keys "bold_curves" and "bold_marks") finishes what the second left in the bold:

bold_marks(font)   the cedilla and ogonek drawn as the regular's with the bold's pen, as the stroke accents
                   are, once the marks are made ("bold_marks").
bold_curves(font)  on the final outlines of the listed letters and their accented forms, the runs of straight
                   facets the bold's pen left on their curves drawn as curves and every piece under eight
                   units folded away, all within 1.5 units of the outline as it was ("bold_curves").
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
    font.regular_P = dict(font.P)              # what the bold's pen draws (bold_joins, symbols)


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
LOWER_NAMED = {'dotlessi', 'dotlessj', 'ae', 'oe', 'oslash', 'eth', 'thorn', 'germandbls', 'eng', 'lslash', 'kgreenlandic'}


def lowercase(font, n):
    """A lowercase letter: a to z, an alternate of one, a named lowercase letter (æ, ð, ı...), or an
    accented form of any of these."""
    base = getattr(font, 'comp', {}).get(n, n)
    return base.split('.')[0] in LOWER or base in LOWER_NAMED


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
    side = lambda names, n: lowercase(font, n) if names == '*lower' else n in names
    # the class pairs, and the builder's exceptions for the accented letters that stick out of their base's
    # class (’â was -110 there while ’a was eased to -40)
    for table in (pk, font.kern_exc):
        for (a, b), k in list(table.items()):
            for rule in spec['limits']:
                if side(rule['left'], a) and side(rule['right'], b):
                    table[a, b] = max(k, rule['min'])
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


# ---------------------------------------------------------------- the bold's sheet pieces
def bold_pieces(font, edits=EDITS):
    """The sheet's loose marks, rules and chevrons (font.piece, read from pieces.json after the letters were
    drawn with the bold's pen) drawn with that pen too: each piece grown on its own by its judged share of
    the pen, its hole kept open as build2.bold_pieces keeps a ring's, and each pair (the diaeresis, the
    guillemets) set apart again by the width its pen added, so the white between them stays as drawn."""
    import build2, bolden
    from glyphs import bounds, translate
    spec = load(edits)['bold_pieces']; b = build2.BOLD[font.key]
    share = lambda n: spec['share'].get(n, spec['share'].get(n.split('.')[0], 1.0))
    font.piece_regular = dict(font.piece)
    for n, p in list(font.piece.items()):
        pen = (share(n) * b['rx'], share(n) * b['ry'])
        font.piece[n] = bolden.concat([bolden.protect(q, bolden.grow(q, *pen), font.S_regular, pen, sliver=font.SLIVER)
                                       for q in bolden.components(p)])
    for pair in spec['pairs']:
        if not all(n in font.piece for n in pair):
            continue
        left, right = sorted(pair, key=lambda n: bounds(font.piece_regular[n])[0])
        font.piece[left] = translate(font.piece[left], -share(left) * b['rx'], 0)
        font.piece[right] = translate(font.piece[right], share(right) * b['rx'], 0)


def bold_marks(font, edits=EDITS):
    """In a bold, once the marks are made (Font2.make_marks): the cedilla and the ogonek, which the builder draws
    at a weight taken from the ring (marks.MarkSet: 0.27 and 0.29 of the ring's width, and the bold's ring is a
    hairline grown by 0.45 of the pen), drawn as the regular draws them and grown with the bold's pen by their
    share of it, as bold_pieces grows the stroke accents ("bold_marks"). Font2.attach sets them by their neck, so
    they join the letter as before and the hook's white under the letter stays."""
    if not font.bold:
        return
    import build2, bolden
    from marks import MarkSet, centre
    spec = load(edits)['bold_marks']; b = build2.BOLD[font.key]
    ms = MarkSet(font.style, font.S_regular, font.xh, period=font.period, comma=font.P['comma'],
                 weight=font.cfg['mark_weight'], given={'ring': font.piece_regular['ring']})
    for kind, share in spec['share'].items():
        q = getattr(ms, kind)()
        pen = (share * b['rx'], share * b['ry'])
        g = centre(bolden.protect(q, bolden.grow(q, *pen), font.S_regular, pen, sliver=font.SLIVER), top=False)
        font.marks[kind] = font.case_marks[kind] = g


def rule_weight(pieces):
    """The weight of the sheet's two rules, as Font2.dashes measures it (their area over their width)."""
    from glyphs import bounds
    w = lambda p: abs(_area(p)) / (bounds(p)[2] - bounds(p)[0])
    return float(np.mean([w(pieces['endash']), w(pieces['emdash'])]))


# ---------------------------------------------------------------- the bold's open joins
def _point(a, seg, t):
    k, p = seg; a = np.array(a, float)
    if k == 'L':
        return a + (np.array(p[0], float) - a) * t
    c1, c2, e = (np.array(q, float) for q in p)
    return (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t * t * c2 + t ** 3 * e


def _split(a, seg, t):
    """seg (from a) split at t into two."""
    k, p = seg
    m = tuple(_point(a, seg, t))
    if k == 'L':
        return ['L', [m]], ['L', [p[0]]]
    a = np.array(a, float); c1, c2, e = (np.array(q, float) for q in p)
    ab, bc, cd = a + (c1 - a) * t, c1 + (c2 - c1) * t, c2 + (e - c2) * t
    abc, bcd = ab + (bc - ab) * t, bc + (cd - bc) * t
    return ['C', [tuple(ab), tuple(abc), m]], ['C', [tuple(bcd), tuple(cd), tuple(e)]]


def _arc(a, seg, n=64):
    ts = np.linspace(0, 1, n); pts = np.array([_point(a, seg, t) for t in ts])
    return ts, np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]


def _tangent(a, seg, t, e=1e-4):
    v = _point(a, seg, min(1, t + e)) - _point(a, seg, max(0, t - e)); return v / np.linalg.norm(v)


def round_face(segs, face, r):
    """The face (segments face[0]..face[-1] of a closed contour) and r units of outline either side of it
    drawn as one curve, tangent to the outline at both ends, its handles reaching to the face's line."""
    n = len(segs); i, j = face[0], face[-1]
    def walk(k, step):
        need = r
        while True:
            ts, d = _arc(FN._start(segs, k), segs[k])
            if d[-1] >= need:
                return k, float(np.interp(d[-1] - need if step < 0 else need, d, ts))
            need -= d[-1]; k = (k + step) % n
    kA, tA = walk((i - 1) % n, -1)
    kB, tB = walk((j + 1) % n, 1)
    sA, sB = FN._start(segs, kA), FN._start(segs, kB)
    firstA, _ = _split(sA, segs[kA], tA)
    _, secondB = _split(sB, segs[kB], tB)
    A, B = np.array(firstA[1][-1]), _point(sB, segs[kB], tB)
    ta, tb = _tangent(sA, segs[kA], tA), _tangent(sB, segs[kB], tB)
    f0, f1 = np.array(FN._start(segs, i)), np.array(segs[j][1][-1])
    fd = (f1 - f0) / np.linalg.norm(f1 - f0); fn = np.array([-fd[1], fd[0]])
    def reach(P, t):                     # along t from P to the face's line
        den = float(np.dot(t, fn))
        return float(np.dot(f0 - P, fn)) / den if abs(den) > 1e-6 else r
    la = min(max(reach(A, ta), 0.3 * r), 2.5 * r); lb = min(max(-reach(B, tb), 0.3 * r), 2.5 * r)
    out = [secondB]; k = (kB + 1) % n
    while k != kA:
        out.append(segs[k]); k = (k + 1) % n
    return out + [firstA, ['C', [tuple(A + ta * la), tuple(B - tb * lb), tuple(B)]]]


def wall(P, at, side, S, margin=45):
    """The stem's edge on `side` (+1: its right, the terminal beyond it) near a join at `at`, where the
    bold has run the terminal into it: a curve x = f(y) (degree two) fitted to the edge where it runs free
    either side of the join. Returns (f, (y0, y1) the heights where the two are joined)."""
    polys = polygons(segments(P)); c0 = at[0] - side * S / 2
    def edge(y):
        run = next(((a, b) for a, b in crossings(polys, y) if a - 1 <= c0 <= b + 1), None)
        return (None, 0.0) if run is None else ((run[1] if side > 0 else run[0]), run[1] - run[0])
    joined = [y for y in np.arange(at[1] - 90, at[1] + 90, 1.0) if edge(y)[1] > S + 12]
    y0, y1 = min(joined), max(joined)
    ys, xs = [], []
    for y in list(np.arange(y0 - margin, y0 - 2, 1.0)) + list(np.arange(y1 + 3, y1 + margin, 1.0)):
        e, w = edge(y)
        if e is not None and w < S + 12:
            ys.append(y); xs.append(e)
    return np.poly1d(np.polyfit(ys, xs, 2)), (float(y0), float(y1))


def gap_at(P, at, side, S, window=90):
    """The narrowest white, across, between the stem and the terminal beyond it near `at`."""
    polys = polygons(segments(P)); c0 = at[0] - side * S / 2; best = None
    for y in np.arange(at[1] - window, at[1] + window, 1.0):
        runs = crossings(polys, y)
        i = next((k for k, (a, b) in enumerate(runs) if a - 1 <= c0 <= b + 1), None)
        if i is None or not 0 <= i + side < len(runs):
            continue
        g = runs[i + side][0] - runs[i][1] if side > 0 else runs[i][0] - runs[i + side][1]
        best = g if best is None else min(best, g)
    return best


def cut_join(P, at, side, S, gap, r, reach=200):
    """P (a bold whose join at `at` is closed) with a gap `gap` wide taken from the terminal alone: the
    white runs along the stem's own edge, which stays as it is, and the terminal's face is one curve."""
    import shapes as SH
    f, joined = wall(P, at, side, S)
    face = f + side * gap
    polys = polygons(segments(P))
    def clear(y):                        # nothing of P between the stem's edge and the face
        lo, hi = sorted((f(y) + side * 0.5, face(y)))
        return all(b <= lo or a >= hi for a, b in crossings(polys, y))
    top = next(y for y in np.arange(at[1], at[1] + reach, 1.0) if clear(y)) + 3
    bot = next(y for y in np.arange(at[1], at[1] - reach, -1.0) if clear(y)) - 3
    def along(g, y0, y1):                # x = g(y), of degree two, from y0 to y1: exactly one cubic
        p0, p3 = np.array([g(y0), y0]), np.array([g(y1), y1])
        q = np.array([g(y0) + g.deriv()(y0) * (y1 - y0) / 2, (y0 + y1) / 2])
        return tuple(p0 + 2 / 3 * (q - p0)), tuple(p3 + 2 / 3 * (q - p3)), tuple(p3)
    cut = pathops.Path(); pen = cut.getPen()
    pen.moveTo((f(bot), bot)); pen.lineTo((face(bot), bot)); pen.curveTo(*along(face, bot, top))
    pen.lineTo((f(top), top)); pen.curveTo(*along(f, top, bot)); pen.closePath()
    cut = pathops.simplify(cut, fix_winding=True, keep_starting_points=False, clockwise=False)
    on_face = lambda q: abs(q[0] - face(q[1])) < 0.6 and bot - 1 < q[1] < top + 1
    out = []
    for segs in segments(SH.difference(P, cut)):
        idx = [i for i, sg in enumerate(segs) if all(on_face(q) for q in _bez(FN._start(segs, i), sg, 8))]
        out.append(round_face(segs, idx, r) if idx else segs)
    return path(out), dict(wall=[round(float(v), 4) for v in f.coeffs], joined=joined, cut=(float(bot), float(top)))


def _closed_bold(font, p, at):
    """p drawn with the bold's pen as Font2.embolden_traced draws it, but with its join at `at` left to
    close: the aperture there not eased (the ease thinned the stem as well as the terminal) and no crack
    reopened in its place."""
    import build2, bolden
    b = build2.BOLD[font.key]
    ease, reopen = bolden._ease, bolden._reopen
    def eased(core, frame_b, neck, across, w, pen, res=1.0):
        return None if math.dist(neck, at) < 30 else ease(core, frame_b, neck, across, w, pen, res)
    bolden._ease, bolden._reopen = eased, (lambda core, bold, *a, **k: bold)
    try:
        return bolden.embolden(p, b['rx'], b['ry'], b['k'], font.xh, font.S_regular, sliver=font.SLIVER)
    finally:
        bolden._ease, bolden._reopen = ease, reopen


def lower_tip(p, at, drop, reach):
    """The outline near `at` moved down by `drop`, falling off smoothly with the distance along the
    contour (to nothing at `reach`): the tip of a tail lowered, the stroke it ends left where it is."""
    out = []
    for segs in segments(p):
        n = len(segs); nodes = [sg[1][-1] for sg in segs]
        i0 = int(np.argmin([math.dist(q, at) for q in nodes]))
        if math.dist(nodes[i0], at) > 40:
            out.append(segs); continue
        length = [_arc(FN._start(segs, i), sg, 24)[1][-1] for i, sg in enumerate(segs)]
        s = [math.inf] * n; s[i0] = 0.0
        for step in (1, -1):
            acc, j = 0.0, i0
            for _ in range(n):
                acc += length[(j + 1) % n] if step > 0 else length[j]
                j = (j + step) % n; s[j] = min(s[j], acc)
        w = lambda v: 1 - (lambda t: t * t * (3 - 2 * t))(min(1.0, v / reach))
        moved = []
        for i, (k, q) in enumerate(segs):
            wa, wb = w(s[(i - 1) % n]), w(s[i])
            if k == 'L':
                moved.append(['L', [(q[0][0], q[0][1] - drop * wb)]])
            else:
                c1, c2, e = q
                moved.append(['C', [(c1[0], c1[1] - drop * wa), (c2[0], c2[1] - drop * wb), (e[0], e[1] - drop * wb)]])
        out.append(moved)
    return path(out)


def bold_joins(font, edits=EDITS):
    """In a bold, on its letters before anything is derived from them (and before the zones, in the frame
    the pen drew them in): each drawn open join ("bold_joins") closed by the pen and opened again from the
    terminal alone, so that the stem keeps its straight edge and full weight and the terminal's face is
    one curve; and the g's tail tip, which the pen and the restored heights raised against the bowl,
    lowered ("g_tail")."""
    if not font.bold:
        return
    import build2
    from glyphs import bounds, translate
    spec = load(edits); J, G = spec['bold_joins'], spec['g_tail']
    S = font.stem_width()
    # a sloped style narrows every glyph and adds a hair of weight each side (Font2.condense): its gap is
    # cut that much wider here, so that it is as wide as the upright's once sloped
    hair = (1 - build2.CONDENSE) * S / 2 if font.italic else 0.0
    target = (J['gap'] + 2 * hair) / (build2.CONDENSE if font.italic else 1.0)
    font.joins = {}
    for n, j in J['glyphs'].items():
        if n not in font.P:
            continue
        closed = _closed_bold(font, font.regular_P[n], j['at'])
        closed = translate(closed, 0, bounds(font.P[n])[1] - bounds(closed)[1])     # where snap() set the bold
        cut = target
        for _ in range(5):               # the curved face stands off the cut a little: aim at the gap itself
            q, info = cut_join(closed, j['at'], j['side'], S, cut, J['round'])
            g = gap_at(q, j['at'], j['side'], S)
            if g is None or abs(g - target) < 0.5:
                break
            cut = max(4.0, cut + target - g)
        font.P[n] = q; font.joins[n] = dict(info, gap=None if g is None else round(g, 1))
    n = G['glyph']
    if n in font.P:
        font.P[n] = lower_tip(font.P[n], G['at'], G['drop'], G['reach'])


# ---------------------------------------------------------------- symbols
def symbols(font, edits=EDITS):
    """Before spacing, and before a sloped style narrows its glyphs: in a bold, the section drawn as the
    regular's (two interlaced s, symbols.section, at the regular's weight) with the bold's pen in its own
    frame, so that it keeps the regular's extent and is as black as the bold's s (interlacing the bold s
    itself lightens it until a loop opens); and the number sign, drawn at the rules' weight, kept to the
    proportion of the stems that the regular's has ("symbols")."""
    if getattr(font, 'symbols_done', False):
        return
    font.symbols_done = True
    if not font.bold:
        return
    import build2, bolden, symbols as SY
    from glyphs import bounds, translate
    spec = load(edits)['symbols']; b = build2.BOLD[font.key]
    top = font.fig if font.cfg['lining'] else font.xh * 1.05
    sec = SY.section(font.regular_P['s'], font.S_regular, font.S_regular, top)
    y0, y1 = bounds(sec)[1], bounds(sec)[3]
    # its loop, its one counter, kept a little more open than a letter's least counter is (bolden.F_AREA, F_HOLE)
    kept = bolden.F_AREA, bolden.F_HOLE
    bolden.F_AREA, bolden.F_HOLE = spec['section']['counter_area'], spec['section']['counter_radius']
    try:
        g = bolden.embolden(translate(sec, 0, -y0), b['rx'], b['ry'], b['k'], y1 - y0, font.S_regular, sliver=font.SLIVER)
    finally:
        bolden.F_AREA, bolden.F_HOLE = kept
    font.P['section'] = font.norm_x(translate(g, 0, y0))
    font.made['section'] = 'two interlaced s at the regular\'s weight, drawn with the bold\'s pen'
    if 'numbersign' in font.P and 'endash' in getattr(font, 'piece_regular', {}):
        k = spec['numbersign']['stroke']                    # its strokes against the rules (symbols.make_symbols)
        now, want = k * font.hyphen_thick, k * rule_weight(font.piece_regular) * font.S / font.S_regular
        if now - want > 1:
            font.P['numbersign'] = font.norm_x(bolden.erode(font.P['numbersign'], (now - want) / 2, (now - want) / 2))
            font.made['numbersign'] = 'sheared grid at the bold\'s weight'


# ---------------------------------------------------------------- room after kerning
def clearances(font, edits=EDITS):
    """After kerning and its collision protection, the room a pair needs, as the white across at each
    height (one-unit steps, with the two units of vertical allowance study_spacing.protect_kerning gives):
    before a fada (or another mark) over i, which overhangs the i's side bearing and ran into a capital's
    arm, measured across the mark; and in a bold, between capitals, whose wider pen brought A V, T Y and
    Z V within ten units. A pair of letters is opened by its class kerning, so that their accented forms
    follow; an accented i, which no class holds, by an exception. Both are rounded up to five units."""
    from study_spacing import silhouette
    from scipy.ndimage import minimum_filter1d
    from glyphs import bounds
    spec = load(edits)['kerning']['clearances']
    names = [n for n, p in font.final.items() if n not in font.mark_glyphs and n not in ('space', 'underscore') and bounds(p)]
    lo = math.floor(min(bounds(font.final[n])[1] for n in names)) - 3
    hi = math.ceil(max(bounds(font.final[n])[3] for n in names)) + 3
    ys = np.arange(lo + .5, hi, 1.); prof = {}
    def side(n):
        if n not in prof:
            left, right = silhouette(font.final[n], ys)
            prof[n] = (minimum_filter1d(left, size=5, mode='constant', cval=np.inf), right)
        return prof[n]
    owner_l = {g: a for a, gs in font.left_group.items() for g in gs}
    owner_r = {g: b for b, gs in font.right_group.items() for g in gs}
    def kern(a, b):
        return font.kern_exc[a, b] if (a, b) in font.kern_exc else font.kern_pairs.get((owner_l.get(a, a), owner_r.get(b, b)), 0)
    def least(a, b, k, above=None):
        g = font.adv[a] + k + side(b)[0] - side(a)[1]
        g = g[np.isfinite(g) & (ys > above if above is not None else True)]
        return float(g.min()) if g.size else None
    font.clearance_fixes = []
    for rule in spec:
        if font.style_name not in rule.get('styles', [font.style_name]):
            continue
        want = rule['clearance'] + rule.get('margin', 0)
        if rule['right'] == '*capitals':
            caps = [n for n in font.left_group if n in font.right_group and n[:1].isupper() and n not in font.comp]
            for a in caps:
                for b in caps:
                    k = kern(a, b); m = least(a, b, k)
                    if m is None or m >= want:
                        continue
                    new = int(math.ceil((k + want - m) / 5.0) * 5)
                    font.kern_pairs[a, b] = new
                    for ga in font.left_group[a]:
                        for gb in font.right_group[b]:
                            if (ga, gb) in font.kern_exc:
                                font.kern_exc[ga, gb] = max(font.kern_exc[ga, gb], new)
                    font.clearance_fixes.append(dict(left=a, right=b, before=k, after=new, measured_gap=round(m, 1)))
            continue
        for b in [n for n in rule['right'] if n in font.final and n in font.comp]:
            above = bounds(font.final[font.comp[b]])[3] + 5          # across the mark, above its letter
            for a in names:
                k = kern(a, b); m = least(a, b, k, above)
                if m is None or m >= want:
                    continue
                new = int(math.ceil((k + want - m) / 5.0) * 5)
                font.kern_exc[a, b] = new
                font.clearance_fixes.append(dict(left=a, right=b, before=k, after=new, measured_gap=round(m, 1)))


# ---------------------------------------------------------------- corners
def clean_corners(segs, short=8.0, near=5.0, tol=2.5):
    """A corner drawn as a run of pieces shorter than `short` (where a union of two strokes or a rounded
    offset left them, and the grid kept them) becomes one node, where the outline either side would meet;
    a short piece along a smooth run is merged into a neighbour."""
    from scipy.spatial import cKDTree
    segs = [[k, list(p)] for k, p in segs]
    original = cKDTree(np.vstack([_samples(FN._start(segs, i), s, 1.0) for i, s in enumerate(segs)]))
    changed = True
    while changed and len(segs) > 3:
        changed = False; n = len(segs)
        L = [math.dist(FN._start(segs, i), s[1][-1]) for i, s in enumerate(segs)]
        for i in range(n):
            if L[i] >= short or L[(i - 1) % n] < short:
                continue
            run = [i]
            while L[(run[-1] + 1) % n] < short and len(run) < n - 2:
                run.append((run[-1] + 1) % n)
            prev, nxt = (i - 1) % n, (run[-1] + 1) % n
            t1, t2 = _tan_in(segs, prev), _tan_out(segs, nxt)
            if t1 is None or t2 is None or _angle(t1, t2) < 20:
                continue                                    # a smooth run: tidy() merges those
            a = np.array(FN._start(segs, i)); e = np.array(segs[run[-1]][1][-1])
            C = (a + e) / 2
            M = np.array([t1, -t2]).T
            if abs(np.linalg.det(M)) > 1e-6:
                s_, _ = np.linalg.solve(M, e - a)
                if math.dist(a + s_ * t1, C) <= near:
                    C = a + s_ * t1
            k, p = segs[prev]
            segs[prev] = ['L', [tuple(C)]] if k == 'L' else ['C', [p[0], tuple(np.array(p[1]) + C - a), tuple(C)]]
            k, p = segs[nxt]
            if k == 'C':
                segs[nxt] = ['C', [tuple(np.array(p[0]) + C - e), p[1], p[2]]]
            for r in sorted(run, reverse=True):
                del segs[r]
            changed = True
            break
    # a short piece along a smooth run (what easing an aperture leaves): one with a neighbour, where a
    # single curve draws both within `tol`
    global REF
    ref, REF = REF, original                 # each merge kept within tol of the outline as it came
    try:
        i = 0
        while i < len(segs) and len(segs) > 3:
            n = len(segs)
            if math.dist(FN._start(segs, i), segs[i][1][-1]) >= short:
                i += 1; continue
            for j in sorted(((i - 1) % n, i), key=lambda j: math.dist(FN._start(segs, j), segs[(j + 1) % n][1][-1])):
                m = _merge(segs, j, tol)
                if m:
                    segs[(j + 1) % n] = m[0]; del segs[j]; i = max(0, min(i, j) - 1)
                    break
            else:
                i += 1
    finally:
        REF = ref
    # and one that no curve takes in (a small zigzag where a cut met the pen's offset): dropped, its
    # neighbours meeting at its middle, their handles turned to one tangent there where that stays within tol
    i = 0
    while i < len(segs) and len(segs) > 3:
        n = len(segs); a, e = np.array(FN._start(segs, i)), np.array(segs[i][1][-1])
        if math.dist(a, e) >= short:
            i += 1; continue
        prev, nxt = (i - 1) % n, (i + 1) % n
        M = (a + e) / 2
        (kp, pp), (kn, pn) = segs[prev], segs[nxt]
        P = ['C', [pp[0], tuple(np.array(pp[1]) + M - a), tuple(M)]] if kp == 'C' else ['L', [tuple(M)]]
        N = ['C', [tuple(np.array(pn[0]) + M - e), pn[1], pn[2]]] if kn == 'C' else [kn, list(pn)]
        options = []
        trial = list(segs); trial[prev], trial[nxt] = P, N
        t1, t2 = _tan_in(trial, prev), _tan_out(trial, nxt)
        if t1 is not None and t2 is not None and _angle(t1, t2) < 20:
            d = t1 if kp == 'L' else t2 if kn == 'L' else (t1 + t2) / np.linalg.norm(t1 + t2)
            P2, N2 = [P[0], list(P[1])], [N[0], list(N[1])]
            if kp == 'C':
                P2[1][1] = tuple(M - d * math.dist(P[1][1], M))
            if kn == 'C':
                N2[1][0] = tuple(M + d * math.dist(N[1][0], M))
            options.append((P2, N2))
        options.append((P, N))
        for P_, N_ in options:
            pts = np.vstack([_samples(FN._start(segs, prev), P_, 1.0), _samples(tuple(M), N_, 1.0)])
            if original.query(pts)[0].max() <= tol:
                segs[prev], segs[nxt] = P_, N_; del segs[i]
                break
        else:
            i += 1
    return segs


def smooth_facets(segs, tol=1.5, turn=35.0, longest=60.0):
    """A run of straight pieces that each turn a little (an eased aperture's cut, traced from a raster as a
    polygon) drawn as the curve it stands for: one cubic, or two, tangent to the outline either side where it
    runs on smoothly, kept only within `tol` of the polygon."""
    from scipy.spatial import cKDTree
    segs = [[k, list(p)] for k, p in segs]
    def unit(v):
        v = np.asarray(v, float); n = np.linalg.norm(v); return v / n if n > 1e-9 else None
    i = 0
    while i < len(segs):
        n = len(segs)
        if n < 4:
            break
        is_facet = lambda j: segs[j % n][0] == 'L' and math.dist(FN._start(segs, j % n), segs[j % n][1][-1]) < longest
        bend = lambda j: _angle(_tan_in(segs, (j - 1) % n), _tan_out(segs, j % n))      # at the start of j
        if not is_facet(i) or (is_facet(i - 1) and 0.5 < bend(i) < turn):
            i += 1; continue                                # not the start of a run
        run = [i]
        while len(run) < n - 2 and is_facet(run[-1] + 1) and 0.5 < bend(run[-1] + 1) < turn:
            run.append((run[-1] + 1) % n)
        if len(run) < 2:
            i += 1; continue
        prev, nxt = (run[0] - 1) % n, (run[-1] + 1) % n
        pts = np.vstack([_samples(FN._start(segs, r), segs[r], 1.0) for r in run])
        first, last = unit(np.subtract(segs[run[0]][1][-1], FN._start(segs, run[0]))), unit(np.subtract(segs[run[-1]][1][-1], FN._start(segs, run[-1])))
        t_in, t_out = _tan_in(segs, prev), _tan_out(segs, nxt)
        t1 = t_in if t_in is not None and _angle(t_in, first) < turn else first
        t2 = t_out if t_out is not None and _angle(last, t_out) < turn else last
        ref = cKDTree(pts)
        def fits(a, b, ta, tb):
            """[pieces] of one cubic from a to b through the run's points (split at its extremes), or None."""
            import curvefit as CF
            sub = pts[(np.linalg.norm(pts - a, axis=1).argmin()):(np.linalg.norm(pts - b, axis=1).argmin() + 1)]
            if len(sub) < 4:
                return None
            c = _fit(sub, ta, tb)
            seg = ['C', [tuple(c[1]), tuple(c[2]), tuple(b)]]
            drawn = _samples(tuple(a), seg, 1.0)
            if ref.query(drawn)[0].max() > tol or cKDTree(drawn).query(sub)[0].max() > tol:
                return None
            ts = sorted(t for ax in (0, 1) for t in CF._extrema_t(np.array([a, c[1], c[2], b], float), ax) if 0.08 < t < 0.92)
            pieces, start, last = [], tuple(a), 0.0
            for t in ts:                                   # a node at each extreme, as the outlines have
                if (t - last) / (1 - last) < 0.05:
                    continue
                one, seg = _split(start, seg, (t - last) / (1 - last))
                pieces.append(one); start = one[1][-1]; last = t
            return pieces + [seg]
        a, b = np.array(FN._start(segs, run[0])), np.array(segs[run[-1]][1][-1])
        new = fits(a, b, t1, t2)
        if new is None and len(run) >= 3:
            mid = run[len(run) // 2]; m = np.array(FN._start(segs, mid))
            tm = unit(np.subtract(segs[mid][1][-1], FN._start(segs, (mid - 1) % n)))
            one, two = fits(a, m, t1, tm), fits(m, b, tm, t2)
            new = one + two if one is not None and two is not None else None
        if new is None:
            i += 1; continue
        keep = [s for j, s in enumerate(segs) if j not in run]
        at = sum(1 for j in range(run[0]) if j not in run) if run[0] <= run[-1] else 0
        if run[0] > run[-1]:                               # the run wraps past the contour's start
            segs = keep + new
            i = len(segs)
        else:
            segs = keep[:at] + new + keep[at:]
            i = at + len(new)
    return segs


def corners(font, edits=EDITS):
    """The listed glyphs' corners, on the final outlines of every style, cleaned by clean_corners ("corners")."""
    spec = load(edits)['corners']
    names = list(spec['glyphs']) + (list(spec['bold']) if font.bold else [])
    names += [n for n, b in font.comp.items() if b in names]            # and their accented forms
    for n in names:
        if n in font.final:
            font.final[n] = path([clean_corners(smooth_facets(c, spec['facets']), spec['short'], tol=spec['tolerance'])
                                  for c in segments(font.final[n])])


# ---------------------------------------------------------------- the bold's curves (third pass)
def _seg_len(segs, j):
    return math.dist(FN._start(segs, j), segs[j][1][-1])


def _fewer(curves, ref, tol):
    """Neighbouring fitted cubics drawn as one where one cubic draws both within tol of the run (`ref`) and
    passes no extreme between its ends, so the nodes at extremes stay."""
    from scipy.spatial import cKDTree
    curves = [np.asarray(c, float) for c in curves]
    seg = lambda c: ['C', [tuple(c[1]), tuple(c[2]), tuple(c[3])]]
    changed = True
    while changed and len(curves) > 1:
        changed = False
        for k in range(len(curves) - 1):
            A, B = curves[k], curves[k + 1]
            t1, t2 = A[1] - A[0], B[3] - B[2]
            if np.linalg.norm(t1) < 1e-9 or np.linalg.norm(t2) < 1e-9:
                continue
            pts = np.vstack([_samples(tuple(A[0]), seg(A), 1.0), _samples(tuple(B[0]), seg(B), 1.0)[1:]])
            c = _fit(pts, t1 / np.linalg.norm(t1), t2 / np.linalg.norm(t2))
            if _bulges(c):
                continue
            drawn = _samples(tuple(c[0]), seg(c), 1.0)
            if ref.query(drawn)[0].max() <= tol and cKDTree(drawn).query(pts)[0].max() <= tol:
                curves[k:k + 2] = [np.array([A[0], c[1], c[2], B[3]])]
                changed = True
                break
    return curves


def facet_curves(segs, tol=1.5, longest=90.0, turn=35.0, smooth=12.0, short_curve=12.0):
    """Each run of straight facets on a curve (two or more lines under `longest` units, with pieces of curve
    under `short_curve` between them, each join turning by under `turn` degrees: what the bold's pen left where
    its offset was drawn as a polygon) drawn as the curve it stands for. The run is fitted with cubics
    (curvefit.fit_cubics), nodes at its extremes, as few as draw it within `tol` of the polygon both ways,
    tangent to the outline either side where it joins smoothly (under `smooth` degrees)."""
    import curvefit as CF
    from scipy.spatial import cKDTree
    segs = [[k, list(p)] for k, p in segs]
    unit = lambda v: (lambda n: np.asarray(v, float) / n if n > 1e-9 else None)(np.linalg.norm(v))
    i = 0
    for _ in range(400):
        n = len(segs)
        if i >= n or n < 4:
            break
        facet = lambda j: (segs[j % n][0] == 'L' and _seg_len(segs, j % n) < longest) or \
            (segs[j % n][0] == 'C' and _seg_len(segs, j % n) < short_curve)
        bend = lambda j: _angle(_tan_in(segs, (j - 1) % n), _tan_out(segs, j % n))
        if not facet(i) or (i > 0 and facet(i - 1) and 0.3 < bend(i) < turn):
            i += 1; continue                                # not the start of a run
        run = [i]
        while len(run) < n - 2 and facet(run[-1] + 1) and 0.3 < bend(run[-1] + 1) < turn:
            run.append((run[-1] + 1) % n)
        if len(run) < 2 or sum(segs[r][0] == 'L' for r in run) < 2:
            i += 1; continue
        prev, nxt = (run[0] - 1) % n, (run[-1] + 1) % n
        pts = np.vstack([_samples(FN._start(segs, r), segs[r], 1.0) for r in run])
        pts = pts[np.r_[True, np.linalg.norm(np.diff(pts, axis=0), axis=1) > 1e-6]]
        k0, p0 = segs[run[0]]; k1, p1 = segs[run[-1]]
        first = unit(np.subtract(p0[-1] if k0 == 'L' else p0[0], FN._start(segs, run[0])))
        last = unit(np.subtract(p1[-1], FN._start(segs, run[-1]) if k1 == 'L' else p1[1]))
        t_in, t_out = _tan_in(segs, prev), _tan_out(segs, nxt)
        t1 = t_in if t_in is not None and bend(run[0]) < smooth else first
        t2 = t_out if t_out is not None and bend(nxt) < smooth else last
        ref = cKDTree(pts)
        for share, fewer in ((0.8, True), (0.6, True), (0.4, True), (0.4, False)):   # the fitter's own measure
            cs = CF.add_extrema(CF.fit_cubics(pts, t1, -t2, share * tol))                # is not quite the distance
            cs = _fewer(cs, ref, tol) if fewer else cs
            new = [['C', [tuple(c[1]), tuple(c[2]), tuple(c[3])]] for c in cs]
            drawn = np.vstack([_samples(tuple(c[0]), s, 1.0) for c, s in zip(cs, new)])
            if ref.query(drawn)[0].max() <= tol and cKDTree(drawn).query(pts)[0].max() <= tol:
                break
        else:
            i += 1; continue
        keep = [s for j, s in enumerate(segs) if j not in run]
        if run[0] > run[-1]:                                # the run wraps past the contour's start
            segs = keep + new; i = len(segs)
        else:
            segs = keep[:run[0]] + new + keep[run[0]:]; i = run[0] + len(new)
    return segs


def _merged(segs, i, j, ref, tol, short_first=True):
    """Segments i and j (= i + 1) as one: a line if both are lines, else one cubic leaving along i's start
    tangent and arriving along j's end; at the short piece's own corner end the longer neighbour's tangent may
    be taken instead, whichever draws the two closer. None unless it stays within tol of the outline (`ref`)
    and of the two pieces."""
    from scipy.spatial import cKDTree
    a, e = FN._start(segs, i), segs[j][1][-1]
    pts = np.vstack([_samples(a, segs[i], 1.0), _samples(segs[i][1][-1], segs[j], 1.0)[1:]])
    if segs[i][0] == 'L' and segs[j][0] == 'L':
        options = [['L', [e]]]
    else:
        t1, t2 = _tan_out(segs, i), _tan_in(segs, j)
        if t1 is None or t2 is None:
            return None
        alt = [(t1, t2), (_tan_out(segs, j), t2) if short_first else (t1, _tan_in(segs, i))]
        options = []
        for u1, u2 in alt:
            if u1 is not None and u2 is not None:
                c = _fit(pts, u1, u2)
                if not _bulges(c):
                    options.append(['C', [tuple(c[1]), tuple(c[2]), tuple(e)]])
    best = None
    for seg in options:
        drawn = _samples(a, seg, 1.0)
        err = max(ref.query(drawn)[0].max(), cKDTree(drawn).query(pts)[0].max())
        if err <= tol and (best is None or err < best[0]):
            best = (err, seg)
    return best and best[1]


def _cut_at(segs, j, length, from_end):
    """Segment j split `length` units (along it) from its end (or its start): (first part, second part, unit
    tangent at the split), or None if it is not longer than that."""
    a = FN._start(segs, j); ts, d = _arc(a, segs[j])
    if d[-1] <= length + 1:
        return None
    t = float(np.interp(d[-1] - length if from_end else length, d, ts))
    one, two = _split(a, segs[j], t)
    return one, two, _tangent(a, segs[j], t)


def _unit_or(v):
    v = np.asarray(v, float); m = np.linalg.norm(v)
    return v / m if m > 1e-9 else None


def _fold_options(segs, i, L, short):
    """Ways of folding away the short piece i, most faithful first, each as (new contour, indices of the pieces
    that changed in it)."""
    import curvefit as CF
    n = len(segs); prev, nxt = (i - 1) % n, (i + 1) % n
    tin = _angle(_tan_in(segs, prev), _tan_out(segs, i))
    tout = _angle(_tan_in(segs, i), _tan_out(segs, nxt))
    copy = lambda: [[k, list(p)] for k, p in segs]
    sides = sorted(((i, nxt, tout), (prev, i, tin)), key=lambda o: o[2])
    # beside a smooth join: one curve with the neighbour there, or the neighbour drawn on over it
    for j0, j1, bent in sides:
        if bent <= 20:
            yield ('merge', j0, j1, j0 == i)
    spike = max(tin, tout) > 90                          # a spur: out and back
    for j, bent in sorted(((nxt, tout), (prev, tin)), key=lambda o: o[1]):
        if (bent <= 20 or spike) and segs[j][0] == 'C':
            a, e = np.array(FN._start(segs, i)), np.array(segs[i][1][-1])
            trial = copy(); p = trial[j][1]
            trial[j] = ['C', [tuple(np.array(p[0]) + a - e), p[1], p[2]]] if j == nxt else \
                ['C', [p[0], tuple(np.array(p[1]) + e - a), tuple(e)]]
            del trial[i]
            yield ('trial', trial, [j if j < i else j - 1])
            if spike:                                   # or fitted again to its own points beyond the spur
                a, e = (FN._start(segs, i), segs[i][1][-1]) if j == nxt else (segs[i][1][-1], FN._start(segs, i))
                own = _samples(FN._start(segs, j), segs[j], 1.0)
                own = own[np.linalg.norm(own - np.array(e), axis=1) > _seg_len(segs, i)]
                if len(own) > 4:
                    pts = np.vstack([a, own]) if j == nxt else np.vstack([own, a])
                    u1 = _unit_or(np.subtract(pts[3], a)) if j == nxt else _tan_out(segs, j)
                    u2 = _tan_in(segs, j) if j == nxt else _unit_or(np.subtract(a, pts[-4]))
                    if u1 is not None and u2 is not None:
                        c = _fit(pts, u1, u2); trial = copy()
                        trial[j] = ['C', [tuple(c[1]), tuple(c[2]), tuple(c[3])]]
                        del trial[i]
                        yield ('trial', trial, [j if j < i else j - 1])
    # a run of short pieces at a corner: one node, where the outline either side meets or at the run's middle
    run = [i]
    while L[(run[-1] + 1) % n] < short and len(run) < n - 3:
        run.append((run[-1] + 1) % n)
    p, q = (run[0] - 1) % n, (run[-1] + 1) % n
    t1, t2 = _tan_in(segs, p), _tan_out(segs, q)
    a, e = np.array(FN._start(segs, run[0])), np.array(segs[run[-1]][1][-1])
    spots = [(a + e) / 2]
    if t1 is not None and t2 is not None and abs(np.linalg.det(np.array([t1, -t2]).T)) > 1e-6:
        spots.insert(0, a + np.linalg.solve(np.array([t1, -t2]).T, e - a)[0] * t1)
    for C in spots:
        for refit in (False, True):
            trial = copy()
            for x, end in ((p, True), (q, False)):
                k, pp = trial[x]; s0 = np.array(FN._start(segs, x))
                if k == 'L':
                    trial[x] = ['L', [tuple(C)]] if end else ['L', list(pp)]
                elif not refit:
                    trial[x] = ['C', [pp[0], tuple(np.array(pp[1]) + C - a), tuple(C)]] if end else \
                        ['C', [tuple(np.array(pp[0]) + C - e), pp[1], pp[2]]]
                else:                                   # the neighbour fitted again to its own points, to C
                    pts = _samples(tuple(s0), segs[x], 1.0)
                    pts = np.vstack([pts, C]) if end else np.vstack([C, pts])
                    u1 = _tan_out(segs, x) if end else _unit_or(np.subtract(pts[3], C))
                    u2 = _unit_or(np.subtract(C, pts[-4])) if end else _tan_in(segs, x)
                    if u1 is None or u2 is None:
                        break
                    c = _fit(pts, u1, u2)
                    trial[x] = ['C', [tuple(c[1]), tuple(c[2]), tuple(c[3])]]
            else:
                kept = [s for k, s in enumerate(trial) if k not in run]
                at = [next(k for k, s in enumerate(kept) if s is trial[x]) for x in (p, q)]
                yield ('trial', kept, at)
    # at a corner: one curve with a neighbour all the same, where it stays within tol
    for j0, j1, bent in sides:
        if bent > 20:
            yield ('merge', j0, j1, j0 == i)
    # or the corner rounded: the piece and a few units of each neighbour drawn as one curve tangent to both
    for r in (4.0, 6.0, 8.0, 12.0):
        A, B = _cut_at(segs, prev, r, True), _cut_at(segs, nxt, r, False)
        if A is None or B is None:
            continue
        pts = np.vstack([_samples(A[0][1][-1], A[1], 1.0), _samples(FN._start(segs, i), segs[i], 1.0)[1:],
                         _samples(segs[i][1][-1], B[0], 1.0)[1:]])
        c = _fit(pts, A[2], B[2])
        if _bulges(c):                                  # a corner at an extreme: a node there, as the outlines have
            cs = CF.add_extrema([c])
            if any(math.dist(q[0], q[3]) < short for q in cs):
                continue
        else:
            cs = [c]
        arc = [['C', [tuple(q[1]), tuple(q[2]), tuple(q[3])]] for q in cs]
        trial = copy(); trial[prev] = A[0]; trial[nxt] = B[1]
        trial[i:i + 1] = arc
        k = len(arc)
        yield ('trial', trial, [prev if prev < i else prev + k - 1] + list(range(i, i + k)) + [(nxt + k - 1) if nxt > i else nxt])



def fold_short(segs, tol=1.5, short=9.0, ref=None):
    """Every piece shorter than `short` folded away, the shortest first, each change kept within `tol` of the
    outline as it came (`ref`, a KD tree of its samples) and every node on its ink: beside a smooth join the
    piece and its neighbour there are drawn as one curve, or the neighbour is drawn on over it (the corner's node
    stays where it is), and a spur of a few units is dropped, its neighbour drawn on past it; a run of short
    pieces at a corner becomes one node, where the outline either side meets or at the run's middle; failing
    these, the piece is drawn as one curve with a neighbour across the corner, or the corner is rounded, a node
    at its extreme. A piece none of these folds within tol stays."""
    from scipy.spatial import cKDTree
    segs = [[k, list(p)] for k, p in segs]
    if ref is None:
        ref = cKDTree(np.vstack([_samples(FN._start(segs, i), s, 1.0) for i, s in enumerate(segs)]))
    import curvefit as CF
    bulging = lambda c: sum(k == 'C' and _bulges([FN._start(c, j)] + list(p)) for j, (k, p) in enumerate(c))
    def ok(trial, idx):
        """The trial, a node put at the extreme of each changed curve that passes one, if it stays within tol
        and leaves no new piece under `short`; else None."""
        idx = {k % len(trial) for k in idx}
        out, changed = [], []
        for k, (kind, p) in enumerate(trial):
            if k in idx and kind == 'C' and _bulges([FN._start(trial, k)] + list(p)):
                cs = CF.add_extrema([np.array([FN._start(trial, k)] + list(p), float)])
                if any(math.dist(q[0], q[3]) < short for q in cs):
                    return None
                pieces = [['C', [tuple(q[1]), tuple(q[2]), tuple(q[3])]] for q in cs]
            else:
                pieces = [[kind, p]]
            changed += list(range(len(out), len(out) + len(pieces))) if k in idx else []
            out += pieces
        if bulging(out) > bulging(segs):
            return None                             # a curve passing an extreme between its nodes
        drawn = np.vstack([_samples(FN._start(out, k), out[k], 1.0) for k in changed])
        nodes = np.array([out[k][1][-1] for k in changed] + [FN._start(out, k) for k in changed])
        return out if ref.query(drawn)[0].max() <= tol and ref.query(nodes)[0].max() <= tol else None
    stuck = set()
    for _ in range(300):
        n = len(segs)
        if n <= 3:
            break
        L = [_seg_len(segs, k) for k in range(n)]
        cand = sorted((k for k in range(n) if L[k] < short and tuple(np.round(segs[k][1][-1], 3)) not in stuck), key=lambda k: L[k])
        if not cand:
            break
        i = cand[0]; done = False
        for o in _fold_options(segs, i, L, short):
            if o[0] == 'merge':
                _, j0, j1, sf = o
                m = _merged(segs, j0, j1, ref, tol, sf)
                if m is not None and ref.query(np.atleast_2d(m[1][-1]))[0].max() <= tol:
                    segs[j1] = m; del segs[j0]; done = True
                    break
            else:
                t = ok(o[1], o[2])
                if t is not None:
                    segs = t; done = True
                    break
        if done:
            stuck = set()                           # its neighbours have changed: try the others again
        else:
            stuck.add(tuple(np.round(segs[i][1][-1], 3)))
    return segs


def bold_contour(segs, tol=1.5, short=9.0):
    """One contour of a bold letter, its facets drawn as curves and its short pieces folded, every node and the
    outline within tol of the outline as it came; kept as it was where they would stray further (or where the
    outline as it came would stand more than twice tol from the new one: only a spur of a few units may go)."""
    from scipy.spatial import cKDTree
    segs = [[k, list(p)] for k, p in segs]
    ref = cKDTree(np.vstack([_samples(FN._start(segs, i), s, 1.0) for i, s in enumerate(segs)]))
    new = fold_short(facet_curves(segs, tol), tol, short, ref)
    drawn = np.vstack([_samples(FN._start(new, i), s, 1.0) for i, s in enumerate(new)])
    nodes = np.array([s[1][-1] for s in new])
    if max(ref.query(drawn)[0].max(), ref.query(nodes)[0].max()) > tol or cKDTree(drawn).query(ref.data)[0].max() > 2 * tol:
        return segs
    return new


def bold_curves(font, edits=EDITS):
    """In a bold, on the final outlines of the listed letters and their accented forms ("bold_curves"): each
    contour through bold_contour, and the glyph left as it was if its pieces, counters or area would change."""
    if not font.bold:
        return
    spec = load(edits)['bold_curves']
    names = list(spec['glyphs']); names += [n for n, b in font.comp.items() if b in names]
    font.bold_curved = {}
    for n in names:
        if n not in font.final:
            continue
        p = font.final[n]
        q = path([bold_contour(c, spec['tolerance'], spec['short'] + 1) if len(c) > 3 else c for c in segments(p)])
        s0, s1 = (pathops.simplify(x, fix_winding=True, keep_starting_points=False, clockwise=False) for x in (p, q))
        a0, a1 = _area(s0), _area(s1)
        if len(segments(s0)) != len(segments(s1)) or abs(a1 - a0) > 0.005 * abs(a0):
            continue
        font.final[n] = q; font.bold_curved[n] = round(100 * (a1 - a0) / a0, 3)


def opening(p, rmax=48):
    """The narrowest opening of a glyph, in units: the diameter of the smallest disc whose closing (on a
    one-unit raster) changes its pieces or counters, as a reviewer measures an opening."""
    from scipy import ndimage
    from outline_util import flatten, raster
    from glyphs import bounds
    b = bounds(p); pad = rmax + 4
    x0, y1 = b[0] - pad, b[3] + pad
    W, H = int(b[2] - b[0] + 2 * pad) + 1, int(b[3] - b[1] + 2 * pad) + 1
    r = RecordingPen(); p.draw(r)
    a = raster(flatten(r.value, 16), (W, H), lambda q: (q[0] - x0, y1 - q[1])) > 0
    def topology(m):
        _, n = ndimage.label(m, structure=np.ones((3, 3)))
        lab, nw = ndimage.label(~m)
        edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
        return n, sum(1 for i in range(1, nw + 1) if i not in edge and (lab == i).sum() >= 3)
    t0 = topology(a)
    for rad in range(1, rmax):
        yy, xx = np.ogrid[-rad:rad + 1, -rad:rad + 1]
        if topology(ndimage.binary_closing(a, structure=xx * xx + yy * yy <= rad * rad)) != t0:
            return 2 * rad
    return None
