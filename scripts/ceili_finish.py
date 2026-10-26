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

The second pass (judged-edits.json, "second_pass"), from a review of the finished fonts:
- even_stems(): the Regular's straight stems given the face's weight (kilfane_studio.harmonise_stems).
- heavier_bar(): a heavy level stroke (the 7's and 3's bars, the hyphen) drawn heavier for the bold, so
  that it takes the stems' gain rather than the pen's thin vertical growth.
- terminal_gap(): an open join the bold's pen closes, kept open from the terminal's side only: the stem
  keeps its grown edge and the arm, leg or bowl coming back to it is cut back along one curve.
- dot_foot(): the bold's dot of ! and ? brought down no further than the Regular's.
- bar_spacing(): ð and đ spaced as d, the bar's overhang added to the advance.
- euro(), yen(): € and ¥ standing with the figures.

The third pass (judged-edits.json, "third_pass"), from a third review:
- math_signs(): the bold's math signs with every piece grown about its own centre, the white beside a rule
  kept as the Regular has it, rather than each piece set out from the bold's heavier rule.
- quote_kerning(near=True): a double quote tucks in over a low foot no further than a single one.
- the bold's small signs (build_original_study.bold_signs): the bullet drawn with the bold's pen, % ‰ and the
  letters of @ © at its stem (at_sign()), superiors, fractions and ® at symbols.make_symbols' SMALL_GLYPH_WEIGHT.
- settled(): an outline put on the whole-unit grid once, from the drawing before rounding, its smooth joins
  kept smooth (round_smooth()), nodes only at extremes it passes by more than a unit (overshoot_extremes()).
- straight_feet(): an evened stem carried straight down to its foot where its edge bulged out and back.
- bar_gap(), set_bar_gap(): the bar over j as far above its stem as i's.
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


def quote_kerning(font, share, cap=350, over_foot=False, near=False):
    """Kerning between letters and quotes from one rule: the quote stands `share` of the n|n gap clear of
    the letter's upper part (from 0.55 x-height up), whatever the letter. The release's rule measured
    only where letter and quote share a height, so a letter whose top just reached the quote's foot
    was kerned 150 and its neighbour not at all (o’ -150 against e’ 0). Exceptions for accented
    letters are made again from the new values, as kerning() makes them.

    With `over_foot`, a quote may tuck in over the letter's lower part (the long foot of l, a leg) but
    never stand wholly over it: its far edge reaches at least the part's tip. Measured from the upper
    part alone, l’ set the quote over the foot 64 units from the stem, where it read as the apostrophe
    of ľ.

    With `near` (the third pass), the far edge is that of the quote's piece nearest the letter, so that a
    double quote tucks in no further than a single one (l” had stood its first comma 64 units from l's stem,
    as l’ did before the rule), and the rule also holds for the pairs of ‘ and “ after a letter that the
    builder's own kerning makes."""
    from spacing import profiles
    from glyphs import bounds, contours
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
    def far(q, after):        # the quote's far edge from the letter: of its nearest piece, with `near`
        if not near:
            return whole(q)[1] if after else whole(q)[0]
        bs = [bounds(c) for c in contours(fin[q])]
        return min(bs, key=lambda b: b[0])[2] if after else max(bs, key=lambda b: b[2])[0]
    k5 = lambda v: int(round(v / 5.0) * 5)
    # over a lower part the quote's far edge reaches at least the part's tip: a kern no tighter (rounded up)
    floor = lambda v: int(math.ceil(v / 5.0) * 5) if over_foot else -cap
    changed = {}
    for a in letters:
        for q in QUOTES_AFTER:
            if q in fin:
                gap = font.adv[a] + whole(q)[0] - upper(a)[1]
                lo = floor(whole(a)[1] - font.adv[a] - far(q, True))
                changed[(a, q)] = max(-cap, lo, min(0, k5(target - gap)))
    for q in QUOTES_BEFORE:
        if q not in fin:
            continue
        for b in letters:
            gap = font.adv[q] + upper(b)[0] - whole(q)[1]
            lo = floor(far(q, False) - font.adv[q] - whole(b)[0])
            changed[(q, b)] = max(-cap, lo, min(0, k5(target - gap)))
    if near and over_foot:
        # the builder's own kerning sets ‘ and “ after a letter: the same floor holds for them
        for a in letters:
            for q in ('quoteleft', 'quotedblleft'):
                if (a, q) in font.kern_pairs and q in fin:
                    lo = floor(whole(a)[1] - font.adv[a] - far(q, True))
                    if font.kern_pairs[(a, q)] < lo:
                        changed[(a, q)] = lo
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


# ================================================================ the second pass
# (research/ceili-judgement/judged-edits.json, "second_pass"; build_original_study.py applies each step)

def outline_points(p, step=1.0):
    """Dense points along every contour of a path."""
    return np.vstack([_dense([[k, list(q)] for k, q in segs], step) for segs in F._contours(recording(p))])


def vertical_runs(p, x):
    """The ink runs (y0, y1) that the vertical at x crosses, from the bottom up."""
    from spacing import polys
    ys = []
    for P in polys(p):
        a, b = P, np.roll(P, -1, axis=0)
        m = ((a[:, 0] <= x) & (b[:, 0] > x)) | ((b[:, 0] <= x) & (a[:, 0] > x))
        if m.any():
            t = (x - a[m, 0]) / (b[m, 0] - a[m, 0]); ys += list(a[m, 1] + t * (b[m, 1] - a[m, 1]))
    ys = sorted(ys)
    return list(zip(ys[0::2], ys[1::2]))


# ---------------------------------------------------------------- stems
def even_stems(p, specs, height, target, limit):
    """The straight stems of a traced letter given the face's weight: each [fraction of height, run index]
    (kilfane_studio.harmonise_stems) has its two edges moved apart or together, at most `limit` units
    each. Returns the path and, per stem, (fraction, run, width before, width after)."""
    import kilfane_studio as KS
    c, report = KS.harmonise_stems(KS.segments(p), specs, height, target, limit)
    return KS.path(c), report


# ---------------------------------------------------------------- the bold's heavy level strokes
def _level_line(p, min_length=60.0):
    """The longest level line of the outline with ink just above it (the lower edge of a level stroke):
    (contours, contour index, segment index, x at the line's middle, the stroke's (y0, y1) there)."""
    cs = [[[k, list(q)] for k, q in segs] for segs in F._contours(recording(p))]
    best = None
    for ci, segs in enumerate(cs):
        for i, (k, pts) in enumerate(segs):
            if k != 'L':
                continue
            a, b = _start(segs, i), _a(pts[0])
            if abs(a[1] - b[1]) > 1.0 or abs(b[0] - a[0]) < min_length:
                continue
            run = next((r for r in vertical_runs(p, (a[0] + b[0]) / 2) if abs(r[0] - a[1]) < 1.5), None)
            if run is not None and (best is None or abs(b[0] - a[0]) > best[0]):
                best = (abs(b[0] - a[0]), ci, i, (a[0] + b[0]) / 2, run)
    return None if best is None else (cs, *best[1:])


def level_stroke(p):
    """(x at its middle, (y0, y1)) of a glyph's heavy level stroke, or None."""
    found = _level_line(p)
    return None if found is None else found[3:]


def heavier_bar(p, delta, kind, margin=15.0):
    """The heavy level stroke drawn `delta` units heavier. A 'rule' (the hyphen) grows about its axis. A
    'bar' (the 7's and the 3's, at the figure's top) keeps its top on the line and its lower edge comes
    down: the pen's cut at its free end and the stroke it turns into run on along their own lines to meet
    it, so the cut keeps the pen's angle and the join stays a corner."""
    import shapes as SH
    found = _level_line(p)
    if found is None or delta < 0.5:
        return p
    cs, ci, i, xm, (y0, y1) = found
    if kind == 'rule':
        k = (y1 - y0 + delta) / (y1 - y0); yc = (y0 + y1) / 2
        return SH.transform(p, (1, 0, 0, k, 0, yc * (1 - k)))
    segs = cs[ci]; n = len(segs)
    def line(step):            # the first long straight edge either side of the lower edge
        j = i
        for _ in range(n - 1):
            j = (j + step) % n
            a, b = _start(segs, j), _a(segs[j][1][-1])
            if segs[j][0] == 'L' and np.linalg.norm(b - a) >= 40 and abs(b[1] - a[1]) > 1:
                return a, b
        return None
    A, B = line(-1), line(1)
    if A is None or B is None:
        return p
    at = lambda l, y: l[0][0] + (y - l[0][1]) * (l[1][0] - l[0][0]) / (l[1][1] - l[0][1])
    lo, hi = y0 - delta, y0 + margin
    return SH.union(p, SH.polygon([(at(A, hi), hi), (at(B, hi), hi), (at(B, lo), lo), (at(A, lo), lo)]))


# ---------------------------------------------------------------- the bold's open joins
def terminal_gap(core, bold, pen, seed, gap, reach=150.0, res=1.0, speck=100.0):
    """`bold` with the open join near `seed` kept open from the terminal's side only. `core` is the
    drawing in the bold's frame and `pen` (rx, ry) the growth from it to `bold`. Around the join the core
    falls into two pieces: the stem (the straighter outline where they face) and the arm, leg or bowl
    that comes back to it. The stem keeps the edge the pen grows it to; the terminal is cut back to stand
    `gap` clear of that edge, along the one curve parallel to it. Returns (path, details) or None."""
    import bolden, pathops, shapes as SH
    from scipy import ndimage as ndi
    from scipy.spatial import cKDTree
    from skimage.measure import find_contours
    from outline_util import flatten, raster
    from fontTools.pens.recordingPen import RecordingPen
    rx, ry = pen
    def pieces(c):
        local = SH.op(core, SH.circle(c[0], c[1], reach), pathops.PathOp.INTERSECTION)
        out = []
        for q in (q for q in bolden.components(local) if abs(bolden.area(q)) > 1):
            P = outline_points(q)
            d = 0.0 if q.contains(tuple(map(float, c))) else float(np.linalg.norm(P - c, axis=1).min())
            out.append((d, q, P))
        return sorted(out, key=lambda t: t[0])
    ps = pieces(np.asarray(seed, float))
    if len(ps) < 2:
        return None
    dd, ii = cKDTree(ps[1][2]).query(ps[0][2]); j = int(np.argmin(dd))
    neck = (ps[0][2][j] + ps[1][2][ii[j]]) / 2; width = float(dd[j])
    ps = pieces(neck)
    if len(ps) < 2:
        return None
    def bend(P):               # distance from the best straight line, where the piece faces the join
        near = P[np.linalg.norm(P - neck, axis=1) < width / 2 + 40]
        if len(near) < 5:
            return np.inf
        return float(np.linalg.svd(near - near.mean(0), compute_uv=False)[1] / math.sqrt(len(near)))
    (_, a, Pa), (_, b, Pb) = ps[:2]
    stem, term = (a, b) if bend(Pa) <= bend(Pb) else (b, a)
    grown = bolden.grow(stem, rx, ry)
    band = SH.difference(bolden.grow(grown, gap, gap), grown)
    # the terminal's side of the join: nearer the terminal than any other part of the drawing
    rest = SH.difference(core, term)
    x0, y1 = neck[0] - reach - 4, neck[1] + reach + 4
    W = H = int((2 * reach + 8) / res) + 1
    frame = lambda q: ((q[0] - x0) / res, (y1 - q[1]) / res)
    def ras(p):
        r = RecordingPen(); p.draw(r); return raster(flatten(r.value, 24), (W, H), frame)
    cell = ndi.distance_transform_edt(~ras(term)) < ndi.distance_transform_edt(~ras(rest))
    yy, xx = np.mgrid[:H, :W]
    cell &= np.hypot(x0 + (xx + 0.5) * res - neck[0], y1 - (yy + 0.5) * res - neck[1]) < reach
    cs = find_contours(np.pad(cell.astype(float), 1), 0.5)
    if not cs:
        return None
    c = max(cs, key=len) - 1
    region = SH.polygon([(x0 + (q[1] + 0.5) * res, y1 - (q[0] + 0.5) * res) for q in c])
    out = SH.difference(bold, SH.op(band, region, pathops.PathOp.INTERSECTION))
    # a speck the cut leaves where it meets the side's edge goes
    from glyphs import contours, bounds
    keep = [q for q in contours(out) if abs(bolden.area(q)) >= speck or
            math.hypot((bounds(q)[0] + bounds(q)[2]) / 2 - neck[0], (bounds(q)[1] + bounds(q)[3]) / 2 - neck[1]) > reach]
    out = pathops.simplify(bolden.concat(keep), fix_winding=True, keep_starting_points=False, clockwise=False)
    return out, dict(neck=[round(float(v), 1) for v in neck], width=round(width, 1), gap=gap)


def close_cracks(p, width):
    """Cracks narrower than `width` that cut a counter off from the outside (the ampersand's tail over its
    bar, 8 units in the bold styles) closed, as the bold's designed join in 6 is: what a disc of that width
    closes, kept only where it closes a counter without joining two pieces (a dot keeps its gap) and the
    counter is a real one, not a pinhole left where the disc fills a sharp inner corner.
    Returns the path and the number of cracks closed."""
    import bolden, pathops, shapes as SH
    from glyphs import contours
    def counters(p):          # (pieces, counters' areas), as topology() counts them
        a = [bolden.area(c) for c in contours(pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False))]
        outer, holes = [x for x in a if x > 0], [-x for x in a if x < 0]
        return (len(outer), holes) if outer or not holes else (len(holes), outer)
    r, small = width / 2, (4 * width) ** 2
    add = SH.difference(bolden.erode(bolden.grow(p, r, r), r, r), p)
    if abs(bolden.area(add)) < 1:
        return p, 0
    out, n = p, 0
    for q in bolden.components(add):
        if abs(bolden.area(q)) < 1:
            continue
        u = SH.union(out, q); (pb, hb), (pa, ha) = counters(out), counters(u)
        if pa == pb and len(ha) == len(hb) + 1 and sum(h < small for h in ha) <= sum(h < small for h in hb):
            out, n = u, n + 1
    return out, n


# ---------------------------------------------------------------- the bold's dots
def dot_foot(p, bottom):
    """The glyph's lowest piece (the dot of ! or ?) drawn from its top down to `bottom` and no further:
    the bold's pen, mitred at the diamond's sharp foot, ran it out 8 to 11 units below the Regular's."""
    import shapes as SH
    from glyphs import contours, bounds
    cs = contours(p)
    lo = min(range(len(cs)), key=lambda i: bounds(cs[i])[1])
    b = bounds(cs[lo])
    if b[1] >= bottom - 0.5:
        return p
    k = (b[3] - bottom) / (b[3] - b[1])
    return SH.union(SH.transform(cs[lo], (1, 0, 0, k, 0, b[3] * (1 - k))), *[q for i, q in enumerate(cs) if i != lo])


# ---------------------------------------------------------------- spacing of the barred d
def bar_spacing(font, name, base, min_lsb=-20.0):
    """A letter made of `base` and a bar across it (ð, đ) spaced as the base: the base keeps its own
    sidebearings, the bar's overhang beyond it is added to the advance, and the bar's end stands no
    further left of the origin than `min_lsb`. Run after space(), on the font's P, lsb, adv and final."""
    import build2
    from glyphs import bounds, translate
    bn, bb = bounds(font.P[name]), bounds(font.P[base])
    left, right = bb[0] - bn[0], max(0.0, bn[2] - bb[2])
    lsb = font.lsb[base] - left
    shift = max(0.0, min_lsb - lsb)
    font.lsb[name] = lsb + shift
    font.adv[name] = int(round(font.adv[base] + shift + right))
    font.final[name] = build2.final_clean(translate(font.P[name], font.lsb[name] - bn[0], 0))
    return dict(lsb=round(font.lsb[name], 1), adv=font.adv[name], overhang=round(left + right, 1))


# ---------------------------------------------------------------- € and ¥ with the figures
def euro(font, bottom, top, t):
    """The release's € (the c with two bars, build2.parens_slash_misc) set from `bottom` to `top`, the
    zero's extent, with bars 0.55 `t` thick at two fifths and three fifths of its height."""
    import shapes as SH
    from glyphs import bounds, translate
    src = font.P['C'] if not font.cfg['unicase'] else font.P['c']
    b = bounds(src); H = top - bottom; k = H / (b[3] - b[1])
    c = SH.transform(src, (k, 0, 0, k, 0, 0)); cb = bounds(c)
    c = translate(c, -cb[0] + 0.12 * (cb[2] - cb[0]), bottom - cb[1])
    cb = bounds(c); w = cb[2] - cb[0]; bh = 0.55 * t
    bars = [SH.polygon([(0, y - bh / 2), (cb[0] + 0.62 * w, y - bh / 2), (cb[0] + 0.62 * w, y + bh / 2), (0, y + bh / 2)])
            for y in (bottom + 0.40 * H, bottom + 0.60 * H)]
    return font.norm_x(SH.union(c, *bars))


def yen(font, top, line, t):
    """The release's ¥ (symbols.make_symbols: a Y from v with two bars 0.7 `t` thick), drawn at its own
    height `top` and then set from the baseline to `line`, the figures' height."""
    import shapes as SH, symbols as SY
    from glyphs import bounds, translate
    P, S, xh, st = font.P, font.S, font.xh, font.style
    Ss = S if not font.bold else font.S_regular + 0.5 * (S - font.S_regular)
    if 'Y.alt1' in P:
        y = P['Y.alt1']
    else:
        v = P['v.alt1'] if 'v.alt1' in P else P['v']; vb = bounds(v)
        kk = top / (vb[3] - vb[1]) * 0.62
        y = SY.embolden(SH.transform(v, (kk, 0, 0, kk, 0, 0)), (Ss - kk * S) / 2 * 0.8)
        yb = bounds(y); y = translate(y, 0, top - yb[3])
        yb = bounds(y); cx = (yb[0] + yb[2]) / 2; ys = yb[1] + 0.2 * (yb[3] - yb[1])
        y = SH.union(y, SH.polygon([(cx - 0.42 * S, 0), (cx + 0.42 * S, 0), (cx + 0.42 * S, ys), (cx - 0.42 * S, ys)]))
    yb = bounds(y); ycx = (yb[0] + yb[2]) / 2
    q = SH.union(y, SY.bar(st, ycx - 0.27 * xh, ycx + 0.27 * xh, 0.30 * top, 0.7 * t),
                 SY.bar(st, ycx - 0.27 * xh, ycx + 0.27 * xh, 0.30 * top - 1.7 * t, 0.7 * t))
    b = bounds(q); k = line / (b[3] - b[1])
    return font.norm_x(SH.transform(q, (1, 0, 0, k, 0, -b[1] * k)))


# ================================================================ the third pass
# (research/ceili-judgement/judged-edits.json, "third_pass"; build_original_study.py applies each step)

# ---------------------------------------------------------------- one rounding, its smooth joins kept smooth
SMOOTH = 2.0           # degrees: a join of the exact outline that turns less than this is smooth, and stays so


def overshoot_extremes(segs, beyond=1.0):
    """Exact splits at a curve's interior extremes, where it passes them by more than `beyond` units beyond both
    of its ends. An extreme a unit from a node needs no node of its own: a split there (extremes() splits at 4
    units) leaves a sliver of a segment whose short handles the grid then turns by 10 to 14 degrees."""
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
                    v = _bez(c, [t])[0][ax]
                    if (v - p0) * (v - p3) > 0 and min(abs(v - p0), abs(v - p3)) > beyond:
                        ts.append(t)
        rest, done = c, 0.0
        for t in sorted(set(round(t, 6) for t in ts)):
            a, rest = _split_cubic(rest, (t - done) / (1 - done)); done = t
            out.append(_seg('C', a))
        out.append(_seg('C', rest))
    return out


def _unit(v):
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else None


def _handle_error(q, node, d):
    u = _unit(np.asarray(q, float) - node)
    return 180.0 if u is None else abs(math.degrees(_angle(u, d)))


def _handles(node, d, h, extra=6.0, k=12):
    """Whole-unit handle positions about the ray from `node` along `d`, from a little shorter than the exact
    handle `h` to `extra` units longer, the truest in direction first (to a quarter degree), then the nearest h."""
    L = float(np.linalg.norm(h - node)); seen = {}
    for e in np.arange(-min(2.0, 0.4 * L), extra + 0.01, 0.5):
        ideal = node + d * max(L + e, 1.0)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (float(round(ideal[0]) + dx), float(round(ideal[1]) + dy))
                if q not in seen:
                    seen[q] = (round(_handle_error(q, node, d) * 4) / 4, float(np.linalg.norm(np.asarray(q) - h)))
    return [q for q, _ in sorted(seen.items(), key=lambda kv: kv[1])[:k]]


def _deviation(new, old):
    A = _bez(np.asarray(new, float), np.linspace(0, 1, 32)); B = _bez(np.asarray(old, float), np.linspace(0, 1, 64))
    return max(_dist(A, B, closed=False), _dist(B, A, closed=False))


def round_smooth(segs, tol=1.0, loose=1.5):
    """One contour of an exact outline put on the whole-unit grid: each node rounded, and each handle set at
    the whole-unit place nearest its exact direction, a little longer where that points it truer (settle.py's
    rule), while the curve stays within `tol` units (failing that `loose`) of the exact one. At a join the exact
    outline draws smooth (turning under SMOOTH degrees) both handles take the join's one tangent, or the line's
    direction where one side is a line; at a corner each keeps its own. Rounding handles of a few units on their
    own turns them by up to 14 degrees, a visible kink along a curve."""
    n = len(segs)
    node = [np.asarray(segs[i][1][-1], float) for i in range(n)]
    R = [np.round(q) for q in node]
    tin = [_dirs(_ctrl(segs, i))[1] for i in range(n)]
    tout = [_dirs(_ctrl(segs, (i + 1) % n))[0] for i in range(n)]
    din, dout = list(tin), list(tout)
    for i in range(n):
        if abs(math.degrees(_angle(tin[i], tout[i]))) >= SMOOTH:
            continue
        j = (i + 1) % n
        d = _unit(R[i] - R[i - 1]) if segs[i][0] == 'L' else _unit(R[j] - R[i]) if segs[j][0] == 'L' else _unit(tin[i] + tout[i])
        if d is not None:
            din[i] = dout[i] = d
    out = []
    for j in range(n):
        k, p = segs[j]
        if k == 'L':
            out.append(['L', [tuple(R[j])]]); continue
        a, b, old = R[j - 1], R[j], _ctrl(segs, j)
        h1, h2 = old[1] - old[0] + a, old[2] - old[3] + b
        plain = (tuple(np.round(old[1])), tuple(np.round(old[2])))
        c1s = [tuple(a)] if np.linalg.norm(old[1] - old[0]) < 0.5 else _handles(a, dout[j - 1], h1) + [plain[0]]
        c2s = [tuple(b)] if np.linalg.norm(old[2] - old[3]) < 0.5 else _handles(b, -din[j], h2) + [plain[1]]
        err = lambda q, at, d: 0.0 if q == tuple(at) else _handle_error(q, at, d)
        best = None
        for limit in (tol, loose):
            for c1 in c1s:
                for c2 in c2s:
                    e = max(err(c1, a, dout[j - 1]), err(c2, b, -din[j]))
                    if best is not None and e >= best[0]:
                        continue
                    if _deviation([a, c1, c2, b], old) <= limit:
                        best = (e, c1, c2)
            if best is not None:
                break
        c1, c2 = (best[1], best[2]) if best is not None else plain
        out.append(['C', [tuple(map(float, c1)), tuple(map(float, c2)), tuple(map(float, b))]])
    return out


def _dense_points(p, step=0.5):
    return np.vstack([_dense([[k, list(q)] for k, q in segs], step) for segs in F._contours(recording(p))])


def ink_distance(p, q):
    """The furthest any point of either outline lies from the other (to a quarter unit)."""
    from scipy.spatial import cKDTree
    A, B = _dense_points(p), _dense_points(q)
    return max(float(cKDTree(B).query(A)[0].max()), float(cKDTree(A).query(B)[0].max()))


def missing_extremes(p, margin=1.5):
    return any(k == 'C' and _interior_extreme(_ctrl(segs, i), margin=margin)
               for segs in F._contours(recording(p)) for i, (k, _) in enumerate(segs))


def settled(exact, current, sloped=False, keep=1.5, cap=2.0, tol=1.0):
    """`exact` (an outline before the builder rounds it) put on the whole-unit grid once by round_smooth(),
    after nodes at the extremes it passes by more than a unit (and, when `sloped`, with the nodes the shear
    left redundant removed, as sloped() removes them). Returned in place of `current` (the builder's rounding
    of the same outline, which can stray 1.7 units from it where it was rounded twice) only if it keeps
    current's pieces and counters, lies within `keep` units of the exact outline and `cap` of current's ink,
    and leaves no extreme without a node and no run of facets; otherwise current is kept.

    The result is not simplified again (as build2.final_clean would): the drawing is simplified already, and
    pathops chops a sheared curve at the x-extreme it passes a unit or two from a corner, which is where the
    release's sloped clusters of 2 to 5 unit pieces came from. It is refused if rounding has made it overlap."""
    import pathops, settle
    cs = [overshoot_extremes([[k, list(q)] for k, q in segs]) for segs in F._contours(recording(exact))]
    rec = economy(F._record(cs), tol=1.0) if sloped else F._record(cs)
    rec = F._record([round_smooth([[k, list(q)] for k, q in segs], tol=tol, loose=keep) for segs in F._contours(rec)])
    q = path(rec)
    if missing_extremes(q):
        # an extreme the grid moved past its node: a node there, its handles level (settle.py)
        q = path(settle._record([settle._extremes(segs) for segs in settle._contours(recording(q))]))
    simple = pathops.simplify(q, fix_winding=True, keep_starting_points=False, clockwise=False)
    if (abs(simple.area - q.area) > 1.0 or topology(q) != topology(current) or missing_extremes(q)
            or polygonal(recording(q)) or ink_distance(q, exact) > keep or ink_distance(q, current) > cap):
        return current
    return q


# ---------------------------------------------------------------- stems run straight to their feet
def _reversed(segs):
    """A closed contour drawn the other way round (the same nodes and handles)."""
    n = len(segs); node = lambda i: tuple(segs[i % n][1][-1])
    return [['L', [node(i - 1)]] if segs[i][0] == 'L' else ['C', [tuple(segs[i][1][1]), tuple(segs[i][1][0]), node(i - 1)]]
            for i in reversed(range(n))]


def _carry_edge(segs, si, out, least, corner=35.0):
    """Segment si of `segs` is a stem's straight edge, its lower end its end node; `out` is +1 where the edge
    faces right, -1 left. The smooth run of segments that follows it down to the foot's first corner is drawn
    as the edge carried on, if it bulges out past the edge by more than `least` and comes back in to the
    corner (within `least` of the edge): a foot that flares out to its corner (l.alt1's) is drawn so. Returns
    the new contour and the bulge, or None."""
    n = len(segs); line_x = float(segs[si][1][-1][0])
    run, j = [], si
    for _ in range(n - 1):
        k2 = (j + 1) % n
        c_in, c_out = _ctrl(segs, j), _ctrl(segs, k2)
        if run and abs(math.degrees(_angle(_dirs(c_in)[1], _dirs(c_out)[0]))) >= corner:
            break
        if c_out[3][1] >= c_out[0][1]:                     # the edge has turned into the foot
            break
        run.append(k2); j = k2
    if not run or (len(run) == 1 and segs[run[0]][0] == 'L'):
        return None
    pts = np.vstack([_bez(_ctrl(segs, i), np.linspace(0, 1, 24)) for i in run])
    bulge = float(((pts[:, 0] - line_x) * out).max())
    last = run[-1]; corner_pt = np.asarray(segs[last][1][-1], float)
    if bulge <= least or (corner_pt[0] - line_x) * out > least:
        return None
    dx = line_x - corner_pt[0]; new_corner = (line_x, float(corner_pt[1]))
    nxt = (last + 1) % n
    segs = [[k, list(p)] for k, p in segs]
    if segs[nxt][0] == 'C':
        c1 = segs[nxt][1][0]; segs[nxt][1][0] = (c1[0] + dx, c1[1])
    segs[si] = ['L', [new_corner]]                       # the edge's line, carried on down to the corner
    gone = set(run)
    return [s for i, s in enumerate(segs) if i not in gone], round(bulge, 1)


def straight_feet(p, specs, height, least=2.0):
    """A letter's straight stems (specs: [fraction of height, run index], as even_stems() takes them) carried
    straight down to their feet: where an edge, below its straight line, bulges out past the line by more than
    `least` units before the foot's corner (the h's left foot stood 9 units out, the prints' mean, where n's,
    m's and k's run straight), the line is carried on to the corner instead. Returns (path, report)."""
    import kilfane_studio as KS
    cs = [[[k, list(q)] for k, q in segs] for segs in F._contours(recording(p))]
    report = []
    for frac, run in specs:
        y = frac * height
        st = KS.stem(cs, y, run)
        if st is None:
            continue
        for x, out in ((st[0], -1), (st[1], 1)):
            for ci, segs in enumerate(cs):
                hit = None
                for si, (k, q) in enumerate(segs):
                    a, b = _start(segs, si), _a(q[-1])
                    if k == 'L' and abs(a[0] - b[0]) < 0.5 and min(a[1], b[1]) <= y <= max(a[1], b[1]) and abs(a[0] - x) < 1.0:
                        hit = (si, a[1] > b[1])
                if hit is None:
                    continue
                si, downward = hit
                work = segs if downward else _reversed(segs)
                if not downward:
                    si = len(segs) - 1 - si
                r = _carry_edge(work, si, out, least)
                if r is not None:
                    cs[ci] = r[0] if downward else _reversed(r[0])
                    report.append(dict(stem=[frac, run], side='left' if out < 0 else 'right', bulge=r[1]))
                break
    return path(F._record(cs)), report


# ---------------------------------------------------------------- the bar over i and j
def bar_gap(p):
    """The distance from a glyph's highest piece (the bar over i or j) to the rest of it."""
    from scipy.spatial import cKDTree
    from glyphs import contours, bounds
    cs = sorted(contours(p), key=lambda c: bounds(c)[1])
    if len(cs) < 2:
        return None
    top = outline_points(cs[-1]); rest = np.vstack([outline_points(c) for c in cs[:-1]])
    return float(cKDTree(rest).query(top)[0].min())


def set_bar_gap(p, gap, tries=6):
    """p with its highest piece moved up or down until it stands `gap` from the rest (to a tenth of a unit)."""
    import shapes as SH
    from glyphs import contours, bounds, translate
    for _ in range(tries):
        now = bar_gap(p)
        if now is None or abs(now - gap) < 0.1:
            break
        cs = sorted(contours(p), key=lambda c: bounds(c)[1])
        p = SH.union(*cs[:-1], translate(cs[-1], 0, gap - now))
    return p


# ---------------------------------------------------------------- the bold's @
def at_sign(f, rule, light):
    """symbols.make_symbols' @ (the face's a in a ring 0.7 `rule` thick), its a drawn at the bold's whole stem
    and made smaller, about the ring's centre, where it must be to keep the white that the release's a (drawn
    at the stem `light`) had inside the ring: at the whole stem alone its corner met the ring. Returns the
    glyph and that white."""
    import shapes as SH, symbols as SY
    from glyphs import bounds, translate
    P, S, xh = f.P, f.S, f.xh
    R = 0.64 * xh + 0.25 * S; ccx, ccy = R, 0.42 * xh; rt = 0.7 * rule
    ring = SY.ring(ccx, ccy, R, rt)
    def a(Ss):
        q = SY.scaled(P['a'], 0.74, S, 0.85, Ss); b = bounds(q)
        return translate(q, ccx - (b[0] + b[2]) / 2 + 0.02 * xh, ccy - (b[1] + b[3]) / 2)
    white = SY.clearance(a(light), ring)
    return f.norm_x(SH.union(SY.inside_ring(a(S), ccx, ccy, R - rt, white), ring)), white


# ---------------------------------------------------------------- the bold's math signs
def math_signs(f, tr, dot, marks_r):
    """The bold's math signs (symbols.make_symbols' constructions), every piece drawn at the bold's weight about
    its Regular counterpart's own centre. Before, each was set out from the bold's rule weight, so the pieces
    moved apart: = 157 between its bars against the Regular's 105, the bar of ± down to -121. A piece stacked
    over a rule keeps the Regular's white to it (= and ≈ about the axis, the underbars of ± ≤ ≥ under the plus
    and the chevron, so ≠ too); the dots of ÷ are the Regular's drawn with the bold's pen, about their own
    centres; ~ and ^, which grew upward only, grow about their own. `tr` is the Regular's rule weight, `dot` its
    ÷ dot and `marks_r` its tilde and circumflex. Returns the new ink extents."""
    import shapes as SH
    from glyphs import bounds, translate
    from symbols import bar, vbar, chevron
    from marks import stroke_polyline
    P, xh, st, t, yc = f.P, f.xh, f.style, f.hyphen_thick, f.hyphen_yc
    L = 0.95 * xh
    def put(n, p):
        P[n] = f.norm_x(p)
    o = 0.65 * tr + t / 2                                 # the Regular's bars at yc +- 1.15 tr: 1.3 tr of white
    put('equal', SH.union(bar(st, 0, L, yc - o, t), bar(st, 0, L, yc + o, t)))
    eq = P['equal']; eb = bounds(eq)
    put('notequal', SH.union(eq, stroke_polyline([(eb[0] + 0.25 * L, yc - 0.42 * L), (eb[0] + 0.75 * L, yc + 0.42 * L)], t, st)))
    pc = yc + 0.18 * xh; lo = pc - L / 2.2                # the plus, and under it a bar 1.1 tr clear
    put('plusminus', SH.union(bar(st, 0, L, pc, t), vbar(st, L / 2, lo, pc + L / 2.2, t), bar(st, 0, L, lo - 1.1 * tr - t / 2, t)))
    cw, chh = 0.66 * xh, 0.84 * xh; y0 = yc - 0.18 * chh      # the chevron's lower arm, and a bar 0.6 tr under it
    for n, left in (('lessequal', True), ('greaterequal', False)):
        put(n, SH.union(translate(chevron(st, cw, 0.62 * chh, t, left), 0, y0), bar(st, 0, cw, y0 - 0.6 * tr - t, t)))
    db = bounds(dot); h = db[3] - db[1]; pen = f.bold_pieces(dot); pb = bounds(pen)
    cx = L / 2 - (pb[0] + pb[2]) / 2
    put('divide', SH.union(bar(st, 0, L, yc, t), *[translate(pen, cx, y - (pb[1] + pb[3]) / 2)
                                                    for y in (yc + 1.4 * tr + h / 2, yc - 1.4 * tr - h / 2)]))
    tw = bounds(f.marks['tilde']); tl = SH.transform(f.marks['tilde'], (L / (tw[2] - tw[0]), 0, 0, 1.25, 0, 0)); tb = bounds(tl)
    put('approxequal', SH.union(translate(tl, -tb[0], yc + 0.6 * tr - tb[1]), translate(tl, -tb[0], yc - 0.6 * tr - tb[3])))
    for n, mark, k, base in (('asciitilde', 'tilde', 1.4, yc - 0.10 * xh), ('asciicircum', 'circumflex', 1.35, None)):
        b, r = bounds(P[n]), bounds(marks_r[mark])
        bottom = base if base is not None else b[1]
        centre = bottom + k * (r[3] - r[1]) / 2              # where the Regular's stands: its mark sits on `bottom`
        P[n] = translate(P[n], 0, centre - (b[1] + b[3]) / 2)
    return {n: [round(v) for v in bounds(P[n])[1::2]] for n in
            ('equal', 'notequal', 'plusminus', 'lessequal', 'greaterequal', 'divide', 'approxequal', 'asciitilde', 'asciicircum')}
