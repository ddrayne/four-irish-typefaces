"""Céilí's studio finish: the outline work a type designer does once the drawing is settled.

Works in font units on pen recordings (closed contours of lines and cubic curves), as finish.py does.
build_original_study.py applies it to Céilí's finished candidate when research/ceili-judgement/
judged-edits.json asks for it; nothing else uses it.

- regular(): a traced Regular letter. smooth_hidden_corners() lets a curve that left a stem on a
  handle too short for its bend leave on the stem's tangent; pen_terminals() draws a stroke end the
  prints' mean rounded as a straight cut between two sharp corners; collapse_clusters() makes a
  corner drawn as a cluster of short pieces one corner; economy() removes the nodes one curve can
  replace (within TOL, with the same end tangents and no new extreme; nodes at extremes stay).
- tidy(): any glyph of any style, above all the derived ones: rounding specks folded away, polygonal
  runs (the bold's reopened joins are traced from a raster) drawn as curves, corner clusters made
  one, extremes given nodes, then economy(). sloped() gives a sheared outline its new extremes.
- pen_diamond(): a dot redrawn as the face's period, fitted to the dot's own corners.
- quote_kerning(): one rule for the space between a letter and a quote.
"""
import math
import numpy as np
import finish as F
from curvefit import _bez, _bez_d, _chord_param, _generate, _reparam, fit_cubics, _split_cubic

TOL = 2.0              # economy: furthest a merged curve may lie from the two it replaces


# ---------------------------------------------------------------- geometry
def _a(p):
    return np.asarray(p, float)


def _start(segs, i):
    return _a(segs[i - 1][1][-1])


def _ctrl(segs, i):
    """The segment as four control points (a line as a straight cubic)."""
    a = _start(segs, i); k, p = segs[i]
    if k == 'L':
        b = _a(p[0]); return np.array([a, a + (b - a) / 3, a + 2 * (b - a) / 3, b])
    return np.array([a, _a(p[0]), _a(p[1]), _a(p[2])])


def _seg(kind, c):
    if kind == 'L':
        return ['L', [tuple(map(float, c[3]))]]
    return ['C', [tuple(map(float, c[1])), tuple(map(float, c[2])), tuple(map(float, c[3]))]]


def _dirs(c):
    """Unit tangent at the start and at the end of a control polygon (degenerate handles fall back)."""
    d0 = next((c[k] - c[0] for k in (1, 2, 3) if np.linalg.norm(c[k] - c[0]) > 1e-6), np.array([1.0, 0]))
    d1 = next((c[3] - c[k] for k in (2, 1, 0) if np.linalg.norm(c[3] - c[k]) > 1e-6), np.array([1.0, 0]))
    return d0 / np.linalg.norm(d0), d1 / np.linalg.norm(d1)


def _angle(u, v):
    return math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])


def _length(c):
    return float(np.linalg.norm(np.diff(_bez(c, np.linspace(0, 1, 17)), axis=0), axis=1).sum())


def _dense(segs, step=0.5):
    pts = []
    for i in range(len(segs)):
        c = _ctrl(segs, i); n = max(4, int(_length(c) / step))
        pts.append(_bez(c, np.linspace(0, 1, n, endpoint=False)))
    return np.vstack(pts)


def _dist(A, B, closed=True):
    """Furthest point of A from the polyline B."""
    a, b = (B, np.roll(B, -1, axis=0)) if closed else (B[:-1], B[1:])
    d = b - a
    L = np.maximum((d ** 2).sum(1), 1e-12)
    worst = 0.0
    for p in A:
        t = np.clip(((p - a) * d).sum(1) / L, 0, 1)
        worst = max(worst, float(np.sqrt((((a + d * t[:, None]) - p) ** 2).sum(1)).min()))
    return worst


def orientation(rec):
    """+1 if the ink is on the left of every contour's direction (outer contours counter-clockwise), else -1."""
    area = 0.0
    for segs in F._contours(rec):
        P = _dense(segs, 2.0)
        area += 0.5 * float(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - P[:, 1] * np.roll(P[:, 0], -1)))
    return 1 if area >= 0 else -1


# ---------------------------------------------------------------- economy
def _is_extreme(segs, i):
    """The node at the end of segment i has a horizontal or vertical tangent at an extreme of the outline."""
    c, nxt = _ctrl(segs, i), _ctrl(segs, (i + 1) % len(segs))
    p = c[3]; u = _dirs(c)[1]
    for axis in (0, 1):
        if abs(u[axis]) < math.sin(math.radians(1.5)):            # tangent along the other axis
            a = _bez(c, [0.8])[0][axis] - p[axis]; b = _bez(nxt, [0.2])[0][axis] - p[axis]
            if a * b > 0:
                return True
    return False


def _interior_extreme(c, margin=0.25):
    for axis in (0, 1):
        p0, p1, p2, p3 = c[:, axis]
        A = -p0 + 3 * p1 - 3 * p2 + p3; B = 2 * (p0 - 2 * p1 + p2); C = p1 - p0
        roots = []
        if abs(A) < 1e-12:
            if abs(B) > 1e-12:
                roots = [-C / B]
        elif B * B - 4 * A * C >= 0:
            r = math.sqrt(B * B - 4 * A * C); roots = [(-B + r) / (2 * A), (-B - r) / (2 * A)]
        for t in roots:
            if 0.02 < t < 0.98:
                v = _bez(c, [t])[0][axis]
                if (v - p0) * (v - p3) > 0 and min(abs(v - p0), abs(v - p3)) > margin:
                    return True
    return False


def _merge(c1, c2, tol):
    """One cubic for two joined ones with the outer tangents kept, or None."""
    t1 = _dirs(c1)[0]; t2 = -_dirs(c2)[1]
    pts = np.vstack([_bez(c1, np.linspace(0, 1, 24, endpoint=False)), _bez(c2, np.linspace(0, 1, 25))])
    u = _chord_param(pts)
    ctrl = _generate(pts, u, t1, t2)
    for _ in range(12):
        u = _reparam(ctrl, pts, u); ctrl = _generate(pts, u, t1, t2)
    if np.dot(ctrl[1] - ctrl[0], t1) <= 0 or np.dot(ctrl[2] - ctrl[3], t2) <= 0:
        return None
    if _interior_extreme(ctrl):
        return None
    new = _bez(ctrl, np.linspace(0, 1, 64))
    err = max(_dist(new, pts, closed=False), _dist(pts, new, closed=False))
    return (ctrl, err) if err <= tol else None


def economy(rec, tol=TOL, smooth_deg=2.5):
    out = []
    for segs in F._contours(rec):
        segs = [[k, list(p)] for k, p in segs]
        while len(segs) > 3:
            best = None
            for i in range(len(segs)):
                j = (i + 1) % len(segs)
                if segs[i][0] != 'C' or segs[j][0] != 'C':
                    continue
                c1, c2 = _ctrl(segs, i), _ctrl(segs, j)
                if abs(math.degrees(_angle(_dirs(c1)[1], _dirs(c2)[0]))) > smooth_deg or _is_extreme(segs, i):
                    continue
                m = _merge(c1, c2, tol)
                if m and (best is None or m[1] < best[2]):
                    best = (i, m[0], m[1])
            if best is None:
                break
            i, ctrl, _ = best; j = (i + 1) % len(segs)
            segs[i] = _seg('C', ctrl)
            del segs[j]
        out.append(segs)
    return F._record(out)


# ---------------------------------------------------------------- derived outlines
def _fold_specks(segs, short=3.0):
    """Segments shorter than `short` (rounding leftovers): their end joins the next segment's start."""
    changed = True
    while changed and len(segs) > 3:
        changed = False
        for i in range(len(segs)):
            c = _ctrl(segs, i)
            if np.linalg.norm(c[3] - c[0]) >= short or _length(c) >= 2 * short:
                continue
            j = (i + 1) % len(segs)
            nk, np_ = segs[j]
            a = c[0]
            if nk == 'C':
                cj = _ctrl(segs, j); cj[1] = cj[1] + (a - cj[0]); cj[0] = a
                segs[j] = _seg('C', cj)
            del segs[i]
            changed = True
            break
    return segs


def _fit_fixed(pts, t1, t2):
    """One cubic through pts with unit tangents t1 (forward, at the start) and t2 (forward, at the end)."""
    u = _chord_param(pts)
    ctrl = _generate(pts, u, t1, -t2)
    for _ in range(12):
        u = _reparam(ctrl, pts, u); ctrl = _generate(pts, u, t1, -t2)
    if np.dot(ctrl[1] - ctrl[0], t1) <= 0 or np.dot(ctrl[3] - ctrl[2], t2) <= 0:
        return None
    return ctrl


def _effective_turn(node, tangent, c, at_start, reach=12.0):
    P = _bez(c, np.linspace(0, 1, 200))
    s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    if at_start:
        d = P[np.searchsorted(s, min(reach, 0.5 * s[-1]))] - node
        return math.degrees(_angle(tangent, d / (np.linalg.norm(d) + 1e-12)))
    d = node - P[np.searchsorted(s, max(s[-1] - reach, 0.5 * s[-1]))]
    return math.degrees(_angle(d / (np.linalg.norm(d) + 1e-12), tangent))


def smooth_hidden_corners(segs, max_turn=25.0, tol=3.0, short=0.12):
    """A curve that leaves a line or curve on a handle too short for its bend (a corner the outline
    hides in a node it calls smooth) is redrawn to leave on the neighbour's tangent: the curve (with
    the next one, where they join smoothly) as one cubic, its bend begun a little earlier along a
    line where that fits better, within `tol` of the drawing."""
    for _ in range(4 * len(segs)):
        n = len(segs); done = False
        for i in range(n):
            if n < 4:
                break
            j = (i + 1) % n
            ci, cj = _ctrl(segs, i), _ctrl(segs, j)
            node = ci[3]
            tin, tout = _dirs(ci)[1], _dirs(cj)[0]
            if abs(math.degrees(_angle(tin, tout))) > 12:
                continue                                   # a corner the outline admits
            for side in ('out', 'in'):
                # rotate so the neighbour is R[0]; the curve chain follows it ('out') or ends the list ('in')
                R = segs[i:] + segs[:i] if side == 'out' else segs[j:] + segs[:j]
                nb = _ctrl(R, 0)
                first = R[1] if side == 'out' else R[-1]
                if first[0] != 'C':
                    continue
                c = _ctrl(R, 1) if side == 'out' else _ctrl(R, len(R) - 1)
                h = np.linalg.norm(c[1] - c[0]) if side == 'out' else np.linalg.norm(c[3] - c[2])
                if h > short * _length(c) or h > 6:
                    continue
                tan = tin if side == 'out' else tout
                eff = _effective_turn(node, tan, c, side == 'out')
                if not 6 <= abs(eff) <= max_turn:
                    continue
                chains = [[c]]
                k2 = 2 if side == 'out' else len(R) - 2
                if R[k2][0] == 'C' and len(R) > 4:
                    c2 = _ctrl(R, k2)
                    a1, a2 = (c, c2) if side == 'out' else (c2, c)
                    if abs(math.degrees(_angle(_dirs(a1)[1], _dirs(a2)[0]))) < 12:
                        chains.append([c, c2] if side == 'out' else [c2, c])
                line = R[0][0] == 'L'
                span = float(np.linalg.norm(nb[3] - nb[0]))
                orig_nb = _bez(nb, np.linspace(0, 1, 40))
                best = None
                for chain in chains:
                    cp = np.vstack([_bez(q, np.linspace(0, 1, 40)) for q in chain])
                    orig = np.vstack([orig_nb, cp]) if side == 'out' else np.vstack([cp, orig_nb])
                    for back in [0.0] + [d for d in (6, 12, 18, 24, 32, 40) if line and d < 0.6 * span]:
                        if side == 'out':
                            start = node - tan * back
                            pts = np.vstack([start + (node - start) * np.linspace(0, 1, 8, endpoint=False)[:, None], cp]) if back else cp
                            ctrl = _fit_fixed(pts, tan, _dirs(chain[-1])[1])
                            if ctrl is None:
                                continue
                            nb2 = nb.copy()
                            if back:
                                nb2 = np.array([nb[0], nb[0] + (start - nb[0]) / 3, nb[0] + 2 * (start - nb[0]) / 3, start])
                            new = np.vstack([_bez(nb2, np.linspace(0, 1, 40)), _bez(ctrl, np.linspace(0, 1, 60))])
                        else:
                            end = node + tan * back
                            pts = np.vstack([cp, node + (end - node) * np.linspace(0, 1, 9)[1:, None]]) if back else cp
                            ctrl = _fit_fixed(pts, _dirs(chain[0])[0], tan)
                            if ctrl is None:
                                continue
                            nb2 = nb.copy()
                            if back:
                                nb2 = np.array([end, end + (nb[3] - end) / 3, end + 2 * (nb[3] - end) / 3, nb[3]])
                            new = np.vstack([_bez(ctrl, np.linspace(0, 1, 60)), _bez(nb2, np.linspace(0, 1, 40))])
                        err = max(_dist(new, orig, closed=False), _dist(orig, new, closed=False))
                        # the redrawn curve must leave on its tangent (its bend no longer crowded at the node)
                        at = start if side == 'out' else end
                        e2 = _effective_turn(at, tan, ctrl, side == 'out')
                        if err > tol or abs(e2) > max(6.0, 0.5 * abs(eff)):
                            continue
                        score = (-len(chain), err)            # fewer nodes first, then the closer fit
                        if best is None or score < best[0]:
                            best = (score, len(chain), nb2, ctrl)
                if best is None:
                    continue
                _, m, nb2, ctrl = best
                if side == 'out':
                    R = [_seg(R[0][0], nb2), _seg('C', ctrl)] + R[1 + m:]
                else:
                    R = [_seg(R[0][0], nb2)] + R[1:len(R) - m] + [_seg('C', ctrl)]
                segs = R
                done = True
                break
            if done:
                break
        if not done:
            break
    return segs


def collapse_clusters(segs, short=10.0, min_turn=20.0, max_depth=6.0, max_reach=22.0, convex_only=0, min_run=2):
    """A corner drawn as a cluster of short pieces (two or more under `short`, between longer
    ones) becomes one corner where the long neighbours' tangents meet, if that lies within
    `max_depth` of the cluster. `convex_only` (the ink's orientation) keeps concave clusters."""
    for _ in range(60):
        n = len(segs)
        if n < 5:
            return segs
        lens = [float(np.linalg.norm(_ctrl(segs, i)[3] - _ctrl(segs, i)[0])) for i in range(n)]
        small = [l < short for l in lens]
        if all(small) or sum(small) < min_run:
            return segs
        k0 = small.index(False)
        order = [(k0 + j) % n for j in range(n)]
        runs, cur = [], []
        for k in order:
            if small[k]:
                cur.append(k)
            else:
                if len(cur) >= min_run:
                    runs.append(cur)
                cur = []
        if len(cur) >= min_run:
            runs.append(cur)
        done = False
        for run in runs:
            if n - len(run) < 3:
                continue
            before, after = (run[0] - 1) % n, (run[-1] + 1) % n
            cb, ca = _ctrl(segs, before), _ctrl(segs, after)
            P0, P1 = cb[3], ca[0]
            u0, u1 = _dirs(cb)[1], _dirs(ca)[0]
            turn = math.degrees(_angle(u0, u1))
            if abs(turn) < min_turn or abs(turn) > 160 or (convex_only and turn * convex_only < 0):
                continue
            A = np.array([u0, u1]).T
            if abs(np.linalg.det(A)) < 1e-6:
                continue
            a, b = np.linalg.solve(A, P1 - P0)              # K = P0 + a u0 = P1 - b u1
            if a < -1 or b < -1 or a > max_reach or b > max_reach:
                continue
            K = P0 + a * u0
            pts = np.vstack([_bez(_ctrl(segs, k), np.linspace(0, 1, 5)) for k in run])
            if float(np.linalg.norm(pts - K, axis=1).min()) > max_depth:
                continue
            cb = cb.copy(); ca = ca.copy()
            cb[2] = cb[2] + (K - cb[3]); cb[3] = K
            ca[1] = ca[1] + (K - ca[0]); ca[0] = K
            rest = [segs[(after + 1 + j) % n] for j in range(n - len(run) - 2)]
            segs = rest + [_seg(segs[before][0], cb), _seg(segs[after][0], ca)]
            done = True
            break
        if not done:
            return segs
    return segs


def _polylines(segs, short=14.0, bend=35.0, tol=1.0):
    """Runs of three or more short lines turning gently (a raster's trace) drawn as curves."""
    n = len(segs)
    is_short = [segs[i][0] == 'L' and np.linalg.norm(_ctrl(segs, i)[3] - _ctrl(segs, i)[0]) < short for i in range(n)]
    gentle = [abs(math.degrees(_angle(_dirs(_ctrl(segs, i))[1], _dirs(_ctrl(segs, (i + 1) % n))[0]))) < bend for i in range(n)]
    if all(is_short) or sum(is_short) < 3:
        return segs
    k0 = is_short.index(False)
    order = [(k0 + j) % n for j in range(n)]
    runs, cur = [], []
    for k in order:
        prev = (k - 1) % n
        if is_short[k] and (cur and gentle[prev] or not cur):
            cur.append(k)
        else:
            if len(cur) >= 3:
                runs.append(cur)
            cur = [k] if is_short[k] else []
    if len(cur) >= 3:
        runs.append(cur)
    if not runs:
        return segs
    replace = {}
    for run in runs:
        pts = np.array([_start(segs, run[0])] + [_a(segs[k][1][-1]) for k in run])
        # end tangents: the neighbours' where they join smoothly, else the run's own ends
        before, after = (run[0] - 1) % n, (run[-1] + 1) % n
        cb, ca = _ctrl(segs, before), _ctrl(segs, after)
        d0 = pts[1] - pts[0]; d0 /= np.linalg.norm(d0)
        d1 = pts[-1] - pts[-2]; d1 /= np.linalg.norm(d1)
        tb, ta = _dirs(cb)[1], _dirs(ca)[0]
        t1 = tb if abs(math.degrees(_angle(tb, d0))) < bend else d0
        t2 = ta if abs(math.degrees(_angle(d1, ta))) < bend else d1
        dense = np.vstack([pts[k] + (pts[k + 1] - pts[k]) * s for k in range(len(pts) - 1) for s in np.linspace(0, 1, 6, endpoint=False)] + [pts[-1:]])
        curves = fit_cubics(dense, t1, -t2, tol)
        replace[run[0]] = (run, [_seg('C', c) for c in curves])
    out, skip = [], set()
    for i in range(n):
        if i in replace:
            run, new = replace[i]; out.extend(new); skip.update(run)
        elif i not in skip:
            out.append(segs[i])
    return out


def extremes(segs, min_dist=4.0):
    """Nodes at the extremes inside curves (exact splits), except within `min_dist` of a node, where
    the node itself serves: a split there would leave a sliver beside a corner."""
    out = []
    for i, (k, p) in enumerate(segs):
        if k != 'C':
            out.append([k, list(p)]); continue
        c = _ctrl(segs, i); ts = []
        for ax in (0, 1):
            p0, p1, p2, p3 = c[:, ax]
            A = -p0 + 3 * p1 - 3 * p2 + p3; B = 2 * (p0 - 2 * p1 + p2); C = p1 - p0
            if abs(A) < 1e-12:
                roots = [-C / B] if abs(B) > 1e-12 else []
            else:
                disc = B * B - 4 * A * C
                roots = [(-B + q * math.sqrt(disc)) / (2 * A) for q in (1, -1)] if disc >= 0 else []
            for t in roots:
                if 1e-3 < t < 1 - 1e-3:
                    q = _bez(c, [t])[0]
                    if min(np.linalg.norm(q - c[0]), np.linalg.norm(q - c[3])) >= min_dist:
                        ts.append(t)
        rest, done = c, 0.0
        for t in sorted(set(round(t, 6) for t in ts)):
            a, rest = _split_cubic(rest, (t - done) / (1 - done)); done = t
            out.append(_seg('C', a))
        out.append(_seg('C', rest))
    return out


def topology(p):
    """(pieces, counters) of a path, as scripts/topo.py counts them."""
    import pathops
    from glyphs import contours
    from fontTools.pens.areaPen import AreaPen
    q = pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)
    areas = []
    for c in contours(q):
        ap = AreaPen(); c.draw(ap); areas.append(ap.value)
    outer = sum(a > 0 for a in areas); holes = sum(a < 0 for a in areas)
    return (outer, holes) if outer or not holes else (holes, outer)


def safely(p, fn):
    """fn(recording) applied to path p, unless it would join pieces or open or close a counter: a finish
    never changes what the drawing joins and what it keeps apart."""
    q = path(fn(recording(p)))
    return q if topology(q) == topology(p) else p


def tidy_path(p, tol=1.5):
    return safely(p, lambda r: tidy(r, tol))


def tidy(rec, tol=1.5):
    """A derived outline finished: specks folded, polygonal runs drawn as curves, extremes, economy."""
    out = []
    for segs in F._contours(rec):
        segs = [[k, list(p)] for k, p in segs]
        segs = _fold_specks(segs)
        segs = _polylines(segs)
        segs = collapse_clusters(segs)
        segs = collapse_clusters(segs, short=6.0, min_turn=30.0, max_depth=4.0, max_reach=12.0, min_run=1)
        segs = extremes(segs)
        out.append(segs)
    return economy(F._record(out), tol)


def regular(rec, tol=TOL, terminals=True, report=None):
    """A traced Regular outline finished: hidden corners smoothed, pen terminals cut straight between
    sharp corners, corner clusters made one corner, economy."""
    orient = orientation(rec)
    out = []
    for segs in F._contours(rec):
        segs = [[k, list(p)] for k, p in segs]
        segs = smooth_hidden_corners(segs)
        if terminals:
            segs = pen_terminals(segs, orient, report)
        segs = collapse_clusters(segs)
        out.append(segs)
    return economy(F._record(out), tol)


# ---------------------------------------------------------------- the pen diamond
def pen_diamond(dot, period):
    """`dot` (one contour's segments) redrawn as the face's period: the period's outline mapped by the
    affine that best takes its four corners onto the dot's, so the dot keeps its printed corners (and
    with them its gap to the stroke) and takes the period's sides. Both must be four-node diamonds."""
    if len(dot) != 4 or len(period) != 4:
        return dot
    Q = np.array([_a(s[1][-1]) for s in dot]); P = np.array([_a(s[1][-1]) for s in period])
    best = None
    for k in range(4):                                       # the corners in the same order round
        Pk = np.roll(P, k, axis=0)
        X = np.hstack([Pk, np.ones((4, 1))])
        M, *_ = np.linalg.lstsq(X, Q, rcond=None)
        err = float(np.linalg.norm(X @ M - Q))
        if best is None or err < best[0]:
            best = (err, k, M)
    _, k, M = best
    rot = period[k:] + period[:k]
    def mapped(segs, M):
        out = []
        for kind, pts in segs:
            out.append([kind, [tuple(np.array([*q, 1.0]) @ M) for q in pts]])
        return out
    return mapped(rot, M)


def sloped(rec, tol=1.0):
    """A sheared outline: nodes at its new extremes, then the nodes the shear left redundant removed."""
    out = []
    for segs in F._contours(rec):
        out.append(extremes(_polylines([[k, list(p)] for k, p in segs])))
    return economy(F._record(out), tol)


def polygonal(rec):
    """Has the outline a run of three short lines (a curve, or a corner, that rounding to the grid
    turned into facets)?"""
    for segs in F._contours(rec):
        m = len(segs)
        short = [k == 'L' and np.linalg.norm(_ctrl(segs, i)[3] - _ctrl(segs, i)[0]) < 14 for i, (k, _) in enumerate(segs)]
        if m > 4 and any(all(short[(i + j) % m] for j in range(3)) for i in range(m)):
            return True
    return False


def unpolygon(rec):
    """Runs of short lines drawn as curves again, and corners drawn as facets made single corners."""
    out = []
    for segs in F._contours(rec):
        segs = _polylines([[k, list(p)] for k, p in segs])
        segs = collapse_clusters(segs)
        segs = collapse_clusters(segs, short=6.0, min_turn=30.0, max_depth=4.0, max_reach=12.0, min_run=1)
        out.append(segs)
    return F._record(out)


def recording(p):
    """A path's outline as lines and cubic curves only (quadratic pieces, which the pen's growth leaves,
    raised to cubics exactly)."""
    from fontTools.pens.basePen import BasePen

    class Cubic(BasePen):
        def __init__(self):
            super().__init__(None); self.value = []
        def _moveTo(self, pt): self.value.append(('moveTo', (pt,)))
        def _lineTo(self, pt): self.value.append(('lineTo', (pt,)))
        def _curveToOne(self, a, b, c): self.value.append(('curveTo', (a, b, c)))
        def _closePath(self): self.value.append(('closePath', ()))
        def _endPath(self): self.value.append(('closePath', ()))
    r = Cubic(); p.draw(r)
    return r.value


def path(rec):
    import pathops
    from fontTools.pens.recordingPen import replayRecording
    p = pathops.Path(); replayRecording(rec, p.getPen())
    return p


# ---------------------------------------------------------------- pen terminals
T_WINDOW = 120.0       # arc length over which a stroke's end turns
T_TURN = 150.0         # degrees it turns there
T_CORNER = 22.0        # degrees each of its two corners turns, at the least
T_DEPTH = 9.0          # furthest a sharpened corner may lie from the drawn outline (about one source pixel)
T_FACE = 6.0           # furthest the straightened cut may lie from the drawn one
T_REACH = 36.0         # longest run of an edge on to its corner
T_ROUND = 0.025        # radians per unit: where a corner's rounding ends (a radius of 40 units)


def _samples(segs, step=1.0):
    """Dense samples of a closed contour: points, (segment, t), arc length, unwrapped tangent angle and
    the contour's whole turn."""
    P, I, T, TH = [], [], [], []
    prev = None; acc = 0.0
    for i in range(len(segs)):
        c = _ctrl(segs, i)
        n = max(4, int(math.ceil(_length(c) / step)))
        ts = np.linspace(0, 1, n, endpoint=False)
        d = _bez_d(c, ts); pts = _bez(c, ts)
        for k, t in enumerate(ts):
            v = d[k]
            if np.linalg.norm(v) < 1e-9:
                v = _dirs(c)[0] if t < 0.5 else _dirs(c)[1]
            a = math.atan2(v[1], v[0])
            acc = a if prev is None else acc + (a - prev + math.pi) % (2 * math.pi) - math.pi
            prev = a
            P.append(pts[k]); I.append(i); T.append(float(t)); TH.append(acc)
    P = np.array(P); TH = np.array(TH)
    S = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    total = S[-1] + float(np.linalg.norm(P[0] - P[-1]))
    loop = 2 * math.pi * round((TH[-1] - TH[0]) / (2 * math.pi))
    return P, np.array(I), np.array(T), S, TH, total, loop


def find_terminals(segs, orient):
    """Stroke ends whose cut is drawn rounded: two corners, each turning at least T_CORNER, within
    T_WINDOW of outline that turns T_TURN in all."""
    from scipy.ndimage import gaussian_filter1d
    P, I, T, S, TH, total, loop = smp = _samples(segs)
    n = len(P)
    if total < 4 * T_WINDOW:
        return []
    Se = np.r_[S - total, S, S + total]; THe = np.r_[TH - loop, TH, TH + loop]
    ang = lambda s: np.interp(s, Se, THe)
    turn = (ang(S + T_WINDOW / 2) - ang(S - T_WINDOW / 2)) * orient
    k = gaussian_filter1d(np.gradient(THe, Se)[n:2 * n] * orient, 2.0, mode='wrap')
    out, taken = [], np.zeros(n, bool)
    for c in np.argsort(-turn):
        if math.degrees(turn[c]) < T_TURN:
            break
        if taken[c]:
            continue
        rel_all = ((S - S[c] + total / 2) % total) - total / 2
        taken |= np.abs(rel_all) < T_WINDOW
        win = np.nonzero(np.abs(rel_all) < T_WINDOW / 2 + 10)[0]
        order = np.argsort(rel_all[win]); win = win[order]; rel = rel_all[win]; kw = k[win]
        peaks = [j for j in range(1, len(kw) - 1) if kw[j] >= kw[j - 1] and kw[j] >= kw[j + 1] and kw[j] > 0.03]
        peaks.sort(key=lambda j: -kw[j])
        chosen = []
        for j in peaks:
            if all(abs(rel[j] - rel[q]) >= 12 for q in chosen):
                chosen.append(j)
            if len(chosen) == 2:
                break
        if len(chosen) < 2:
            continue
        j1, j2 = sorted(chosen)
        turn_at = lambda j, r=8.0: math.degrees((ang(S[win[j]] + r) - ang(S[win[j]] - r)) * orient)
        if turn_at(j1) < T_CORNER or turn_at(j2) < T_CORNER:
            continue
        def walk(j, step):
            q = j
            while 0 < q + step < len(win) - 1 and abs(rel[q] - rel[j]) < 30:
                q += step
                if kw[q] < T_ROUND:
                    return q
            return None
        a, f1, f2, b = walk(j1, -1), walk(j1, +1), walk(j2, -1), walk(j2, +1)
        if None in (a, f1, f2, b) or f1 > f2:
            continue
        out.append(dict(a=int(win[a]), f1=int(win[f1]), f2=int(win[f2]), b=int(win[b]), samples=smp))
    return out


def _meet(p, u, q, v):
    """(a, b, point) with p + a u = q + b v, or None for parallel lines."""
    A = np.array([u, -v]).T
    if abs(np.linalg.det(A)) < 1e-6:
        return None
    a, b = np.linalg.solve(A, q - p)
    return a, b, p + a * u


def sharpen_terminal(segs, term):
    """The terminal's cut drawn straight between two sharp corners, the stroke's edges run on to them."""
    P, I, T, S, TH, total, loop = term['samples']
    a, f1, f2, b = term['a'], term['f1'], term['f2'], term['b']
    n = len(P)
    idx = lambda lo, hi: [q % n for q in range(lo, (hi if hi >= lo else hi + n) + 1)]
    face = P[idx(f1, f2)]
    if len(face) >= 3:
        cen = face.mean(0); _, _, vt = np.linalg.svd(face - cen); fd = vt[0]
        if np.dot(fd, face[-1] - face[0]) < 0:
            fd = -fd
    else:
        cen = (P[f1] + P[f2]) / 2; fd = (P[f2] - P[f1]) / (np.linalg.norm(P[f2] - P[f1]) + 1e-12)
    ua = np.array([math.cos(TH[a]), math.sin(TH[a])]); ub = np.array([math.cos(TH[b]), math.sin(TH[b])])
    upright = lambda u, deg: abs(u[0]) < math.sin(math.radians(deg))
    if upright(ua, 32) and upright(ub, 32) and not upright(fd, 60) and cen[1] - P[:, 1].min() < 60:
        return None          # the foot of an upright stem: the face's feet end rounded, as n's and m's do
    r1, r2 = _meet(P[a], ua, cen, fd), _meet(cen, fd, P[b], ub)
    if r1 is None or r2 is None:
        return None
    ea, _, K1 = r1
    _, eb, K2 = r2
    if not (0 <= ea <= T_REACH) or not (-T_REACH <= eb <= 0) or np.dot(K2 - K1, fd) <= 2:
        return None
    run = P[idx(a, b)]
    d1, d2 = min(np.linalg.norm(run - K1, axis=1)), min(np.linalg.norm(run - K2, axis=1))
    if max(d1, d2) > T_DEPTH or max(d1, d2) < 1.5:          # too far to be print, or already sharp
        return None
    nrm = np.array([-fd[1], fd[0]])
    if float(np.abs((face - cen) @ nrm).max()) > T_FACE:
        return None
    ia, ta, ib, tb = int(I[a]), float(T[a]), int(I[b]), float(T[b])
    m = len(segs)
    span = [ia]
    while span[-1] != ib:
        span.append((span[-1] + 1) % m)
        if len(span) >= m:
            return None
    ca, cb = _ctrl(segs, ia), _ctrl(segs, ib)
    if ia == ib:
        if tb <= ta:
            return None
        head, rest_ = _split_cubic(ca, ta) if ta > 0 else (None, ca)
        tail = _split_cubic(rest_, (tb - ta) / (1 - ta))[1]
    else:
        head = _split_cubic(ca, ta)[0] if ta > 0 else None
        tail = _split_cubic(cb, tb)[1] if tb > 0 else cb
    new = []
    if head is not None:
        new.append(_seg(segs[ia][0], head))
    if np.linalg.norm(K1 - P[a]) > 0.5:
        new.append(['L', [tuple(map(float, K1))]])
    new.append(['L', [tuple(map(float, K2))]])
    if np.linalg.norm(K2 - P[b]) > 0.5:
        new.append(['L', [tuple(map(float, P[b]))]])
    new.append(_seg(segs[ib][0], tail))
    rest = [segs[(ib + 1 + j) % m] for j in range(m - len(span))]
    return rest + new


def pen_terminals(segs, orient, report=None):
    """Every stroke end whose cut the prints' mean rounds, drawn as a straight cut between sharp corners."""
    for _ in range(20):
        done = False
        for t in find_terminals(segs, orient):
            new = sharpen_terminal(segs, t)
            if new is None:
                continue
            if _dist(_dense(new, 1.0), _dense(segs, 1.0)) > T_DEPTH + 1:
                continue
            if report is not None:
                P = t['samples'][0]
                report.append([round(float(v)) for v in (P[t['a']] + P[t['b']]) / 2])
            segs = new; done = True
            break
        if not done:
            break
    return segs


# ---------------------------------------------------------------- quote kerning
QUOTES_AFTER = ('quoteright', 'quotedblright')                  # set after a letter: it’s, d’, ”
QUOTES_BEFORE = ('quoteleft', 'quotedblleft', 'quoteright')     # set before one: “an, ‘s, ’s é


def quote_kerning(font, share, cap=350):
    """Kerning between letters and quotes from one rule: the quote stands `share` of the n|n gap clear of
    the letter's upper part (from 0.55 x-height up), whatever the letter. The release's rule measured
    only where letter and quote share a height, so a letter whose top just reached the quote's foot
    was kerned 150 and its neighbour not at all (o’ -150 against e’ 0). Exceptions for accented
    letters are made again from the new values, as kerning() makes them."""
    from spacing import profiles
    from glyphs import bounds
    xh, fin = font.xh, font.final
    target = share * font.neutral
    quotes = set(QUOTES_AFTER) | set(QUOTES_BEFORE)
    letters = [n for n in font.left_group if n not in quotes and n not in
               ('period', 'comma', 'hyphen', 'colon', 'semicolon', 'seven', 'one', 'quoteleft', 'quotedblleft')]
    cache = {}
    def upper(n):
        if n not in cache:
            b = bounds(fin[n]); _, L, R = profiles(fin[n], 0.55 * xh, b[3] + 2, step=4)
            cache[n] = (float(np.nanmin(L)), float(np.nanmax(R))) if not np.all(np.isnan(L)) else (b[0], b[2])
        return cache[n]
    def whole(n):
        b = bounds(fin[n]); return b[0], b[2]
    k5 = lambda v: int(round(v / 5.0) * 5)
    changed = {}
    for a in letters:
        for q in QUOTES_AFTER:
            if q in fin:
                gap = font.adv[a] + whole(q)[0] - upper(a)[1]
                changed[(a, q)] = max(-cap, min(0, k5(target - gap)))
    for q in QUOTES_BEFORE:
        if q not in fin:
            continue
        for b in letters:
            gap = font.adv[q] + upper(b)[0] - whole(q)[1]
            changed[(q, b)] = max(-cap, min(0, k5(target - gap)))
    for pair, k in changed.items():
        if k <= -15:
            font.kern_pairs[pair] = k
        else:
            font.kern_pairs.pop(pair, None)
    # accented letters: drop the old exceptions for these pairs and make them again
    base = lambda g: font.comp.get(g, g)
    font.kern_exc = {p: v for p, v in font.kern_exc.items() if (base(p[0]), base(p[1])) not in changed}
    lo_y, hi_y = -0.4 * xh, font.cap + 0.35 * xh
    prof = {}
    def P(n):
        if n not in prof:
            prof[n] = profiles(fin[n], lo_y, hi_y, step=8)[1:]
        return prof[n]
    for (a, b), k in changed.items():
        if (a, b) not in font.kern_pairs:
            continue
        for ga in font.left_group[a]:
            for gb in font.right_group[b]:
                if (ga == a and gb == b) or (ga not in font.comp and gb not in font.comp):
                    continue
                gap = font.adv[ga] + k + P(gb)[0] - P(ga)[1]
                if np.all(np.isnan(gap)):
                    continue
                dmin = float(np.nanmin(gap))
                if dmin < 0.6 * font.neutral:
                    font.kern_exc[(ga, gb)] = k5(min(0, k + (0.6 * font.neutral - dmin)))
    return changed


def spread_pair(p, gap):
    """A mark of two pieces side by side (the double acute) with its right piece moved right until
    the pieces stand at least `gap` apart, the pair kept centred where it was."""
    from glyphs import contours, bounds, translate
    import shapes as SH
    cs = sorted(contours(p), key=lambda c: bounds(c)[0])
    if len(cs) != 2:
        return p
    a, b = cs
    da, db = _dense(F._contours(recording(a))[0], 1.0), _dense(F._contours(recording(b))[0], 1.0)
    now = float(np.linalg.norm(da[:, None] - db[None], axis=2).min())
    if now >= gap:
        return p
    # moving b right by d opens the gap by at least d times the sine of the strokes' slope; step until it holds
    d = 0.0
    while now < gap and d < 4 * gap:
        d += 0.5
        now = float(np.linalg.norm(da[:, None] - (db + [d, 0])[None], axis=2).min())
    return translate(SH.union(a, translate(b, d, 0)), -d / 2, 0)
