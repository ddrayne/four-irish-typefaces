"""Settling: a finished outline put on the integer grid without the marks rounding leaves.

Rounding a finished outline to whole units turns the short handles at its smooth joins by several
degrees (a visible kink along a curve at display sizes), leaves pieces a unit or two long where two
nodes nearly met, and lets a curve pass an extreme a unit or two away from its nodes. settle() takes
the rounded outline and, one join at a time:

- folds a piece shorter than TINY units into one node at its middle, the handles either side moved
  with it;
- turns the handles at a join that bends by less than SMOOTH degrees, with at least one curve, to the
  join's common tangent (the line's direction where one side is a line), choosing whole-unit handle
  positions on it, lengthening a handle a little where it is too short to point accurately;
- puts a node at an extreme that a curve passes more than EXTREME units beyond its ends, its handles
  level with it.

Each change is kept only if the segments it touches stay within MAX_DEV units of where they were.
Corners (joins bending by SMOOTH degrees or more) are never touched. Works on pen recordings in font
units (closed contours of lines and cubic curves); the result has whole-unit coordinates.
"""
import math
import numpy as np

TINY, SMOOTH, EXTREME, MAX_DEV = 4.0, 10.0, 1.0, 2.0


def _contours(rec):
    out, cur, start = [], None, None
    for op, a in rec:
        if op == 'moveTo':
            start = tuple(a[0]); cur = []
        elif op == 'lineTo':
            cur.append(['L', [tuple(a[0])]])
        elif op == 'curveTo':
            cur.append(['C', [tuple(p) for p in a]])
        elif op == 'qCurveTo':                      # pathops writes exact quadratics; as cubics
            a = [tuple(p) for p in a]
            ons = [cur[-1][1][-1] if cur else start]
            ons += [((q[0] + r[0]) / 2, (q[1] + r[1]) / 2) for q, r in zip(a[:-2], a[1:-1])] + [a[-1]]
            for k, q in enumerate(a[:-1]):
                p0, p1 = ons[k], ons[k + 1]
                cur.append(['C', [(p0[0] + 2 / 3 * (q[0] - p0[0]), p0[1] + 2 / 3 * (q[1] - p0[1])),
                                  (p1[0] + 2 / 3 * (q[0] - p1[0]), p1[1] + 2 / 3 * (q[1] - p1[1])), p1]])
        elif op in ('closePath', 'endPath'):
            if cur:
                if cur[-1][1][-1] != start:
                    cur.append(['L', [start]])
                out.append(cur)
            cur = None
    return out


def _record(contours):
    rec = []
    for segs in contours:
        rec.append(('moveTo', (segs[-1][1][-1],)))
        for k, p in segs:
            rec.append(('lineTo', (p[0],)) if k == 'L' else ('curveTo', tuple(p)))
        rec.append(('closePath', ()))
    return rec


def _start(segs, i):
    return segs[i - 1][1][-1]


def _sample(a, seg, n=24):
    a = np.array(a, float); k, p = seg
    if k == 'L':
        b = np.array(p[0], float)
        return a + (b - a) * np.linspace(0, 1, 6)[:, None]
    c1, c2, b = (np.array(q, float) for q in p)
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t * t * c2 + t ** 3 * b


def _poly(start, segs):
    pts, a = [], start
    for s in segs:
        pts.append(_sample(a, s)); a = s[1][-1]
    return np.vstack(pts)


def _dist(P, Q):
    """The largest distance from a point of P to the polyline Q."""
    a, b = Q[:-1], Q[1:]; d = b - a
    L = np.maximum((d ** 2).sum(1), 1e-12)
    worst = 0.0
    for p in P:
        t = np.clip(((p - a) * d).sum(1) / L, 0, 1)
        worst = max(worst, float(np.sqrt((((a + d * t[:, None]) - p) ** 2).sum(1)).min()))
    return worst


def _ok(start, old, new_start, new):
    A, B = _poly(start, old), _poly(new_start, new)
    return max(_dist(A, B), _dist(B, A)) <= MAX_DEV


def _unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n > 1e-9 else None


def _tin(segs, i):
    """Direction in which segment i arrives at its end."""
    k, p = segs[i]; end = p[-1]
    for q in ([p[1], p[0], _start(segs, i)] if k == 'C' else [_start(segs, i)]):
        u = _unit((end[0] - q[0], end[1] - q[1]))
        if u:
            return u
    return None


def _tout(segs, j):
    """Direction in which segment j leaves its start."""
    k, p = segs[j]; a = _start(segs, j)
    for q in ([p[0], p[1], p[2]] if k == 'C' else [p[0]]):
        u = _unit((q[0] - a[0], q[1] - a[1]))
        if u:
            return u
    return None


def _angle(u, v):
    if u is None or v is None:
        return 180.0
    return abs(math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])))


def _r(p):
    return (int(round(p[0])), int(round(p[1])))


def _fold_tiny(segs):
    changed = True
    while changed and len(segs) > 3:
        changed = False
        for i in range(len(segs)):
            a, b = _start(segs, i), segs[i][1][-1]
            if math.dist(a, b) >= TINY:
                continue
            ip, inx = (i - 1) % len(segs), (i + 1) % len(segs)
            node = _r(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
            prev, nxt = segs[ip], segs[inx]
            da, db = (node[0] - a[0], node[1] - a[1]), (node[0] - b[0], node[1] - b[1])
            np1 = ['L', [node]] if prev[0] == 'L' else ['C', [prev[1][0], _r((prev[1][1][0] + da[0], prev[1][1][1] + da[1])), node]]
            nn1 = ['L', list(nxt[1])] if nxt[0] == 'L' else ['C', [_r((nxt[1][0][0] + db[0], nxt[1][0][1] + db[1])), nxt[1][1], nxt[1][2]]]
            pa = _start(segs, ip)
            if _ok(pa, [prev, segs[i], nxt], pa, [np1, nn1]):
                segs[ip], segs[inx] = np1, nn1
                del segs[i]
                changed = True
                break
    return segs


def _best_handle(node, d, h, longer):
    """Whole-unit point near node + d * |h - node| (lengthened up to `longer`) whose direction from
    node is closest to d; ties go to the point nearest the old handle."""
    L = math.dist(node, h)
    best = None
    for extra in np.arange(0, longer + 0.01, 0.5):
        ideal = (node[0] + d[0] * (L + extra), node[1] + d[1] * (L + extra))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (int(round(ideal[0])) + dx, int(round(ideal[1])) + dy)
                u = _unit((q[0] - node[0], q[1] - node[1]))
                if u is None:
                    continue
                err = _angle(u, d)
                key = (round(err * 2) / 2, math.dist(q, h))     # within half a degree, the nearest
                if best is None or key < best[0]:
                    best = (key, q)
    return best[1], best[0][0]


def _smooth(segs):
    n = len(segs)
    for i in range(n):
        j = (i + 1) % n
        (k, p), (nk, q) = segs[i], segs[j]
        if k == 'L' and nk == 'L':
            continue
        tin, tout = _tin(segs, i), _tout(segs, j)
        turn = _angle(tin, tout)
        if not 0.25 < turn < SMOOTH:
            continue
        node = p[-1]
        if k == 'L':
            d = tin
        elif nk == 'L':
            d = tout
        else:
            d = _unit((tin[0] + tout[0], tin[1] + tout[1]))
            if d is None:
                continue
        new_i, new_j = list(segs[i]), list(segs[j])
        worst = 0.0
        if k == 'C':
            h = p[1]
            if math.dist(h, node) < 0.5:
                continue
            nh, e = _best_handle(node, (-d[0], -d[1]), h, longer=max(0.0, 6 - math.dist(h, node)))
            new_i = ['C', [p[0], nh, node]]; worst = max(worst, e)
        if nk == 'C':
            h = q[0]
            if math.dist(h, node) < 0.5:
                continue
            nh, e = _best_handle(node, d, h, longer=max(0.0, 6 - math.dist(h, node)))
            new_j = ['C', [nh, q[1], q[2]]]; worst = max(worst, e)
        segs2 = list(segs); segs2[i], segs2[j] = new_i, new_j
        after = _angle(_tin(segs2, i), _tout(segs2, j))
        if after >= turn:
            continue
        s = _start(segs, i)
        if _ok(s, [segs[i], segs[j]], s, [new_i, new_j]):
            segs[i], segs[j] = new_i, new_j
    return segs


def _extremes(segs):
    out = []
    for i, (k, p) in enumerate(segs):
        if k != 'C':
            out.append([k, p]); continue
        a = np.array(_start(segs, i), float); c1, c2, b = (np.array(q, float) for q in p)
        best = None
        for ax in (0, 1):
            A = -a[ax] + 3 * c1[ax] - 3 * c2[ax] + b[ax]; B = 2 * (a[ax] - 2 * c1[ax] + c2[ax]); C = c1[ax] - a[ax]
            roots = ([-C / B] if abs(B) > 1e-12 else []) if abs(A) < 1e-12 else \
                ([(-B + s * math.sqrt(B * B - 4 * A * C)) / (2 * A) for s in (1, -1)] if B * B - 4 * A * C >= 0 else [])
            for t in roots:
                if not 0.05 < t < 0.95:
                    continue
                pt = (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t * t * c2 + t ** 3 * b
                beyond = min(abs(pt[ax] - a[ax]), abs(pt[ax] - b[ax])) if (pt[ax] - a[ax]) * (pt[ax] - b[ax]) > 0 else 0
                if beyond > EXTREME and (best is None or beyond > best[0]):
                    best = (beyond, t, ax)
        if best is None:
            out.append([k, p]); continue
        _, t, ax = best
        q0 = a + (c1 - a) * t; q1 = c1 + (c2 - c1) * t; q2 = c2 + (b - c2) * t
        r0 = q0 + (q1 - q0) * t; r1 = q1 + (q2 - q1) * t; s = r0 + (r1 - r0) * t
        m = _r(s)
        lvl = lambda h: (m[0], int(round(h[1]))) if ax == 0 else (int(round(h[0])), m[1])
        first = ['C', [_r(q0), lvl(r0), m]]; second = ['C', [lvl(r1), _r(q2), _r(b)]]
        st = tuple(map(float, a))
        if _ok(st, [[k, p]], st, [first, second]):
            out += [first, second]
        else:
            out.append([k, p])
    return out


def settle(rec):
    """The settled pen recording (whole units)."""
    out = []
    for segs in _contours(rec):
        segs = [[k, [_r(q) for q in p]] for k, p in segs]
        segs = _fold_tiny(segs)
        segs = _extremes(segs)
        for _ in range(4):                          # a turned handle can free its neighbour's join
            before = [[k, list(p)] for k, p in segs]
            if _smooth(segs) == before:
                break
        out.append(segs)
    return _record(out)


def settle_path(p):
    """settle() for a pathops path; the path unchanged if settling would alter its pieces or counters."""
    import pathops
    from fontTools.pens.recordingPen import RecordingPen, replayRecording
    rec = RecordingPen(); p.draw(rec)
    q = pathops.Path(); replayRecording(settle(rec.value), q.getPen())

    def shape(path):
        s = pathops.simplify(path, fix_winding=True, keep_starting_points=False, clockwise=False)
        r = RecordingPen(); s.draw(r)
        return sum(op == 'closePath' for op, _ in r.value), abs(s.area)
    (n0, a0), (n1, a1) = shape(p), shape(q)
    return q if n0 == n1 and abs(a1 - a0) <= 0.005 * max(a0, 1.0) else p
