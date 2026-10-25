"""Finishing: the clean-up a type designer gives a traced outline, without moving it off the drawing.

A fitter that follows a scanned edge leaves marks no designer would: a short straight piece where a
curve passes its extreme (a flat spot, joined to the curves either side almost but not quite
smoothly), joins that bend by a few degrees where the stroke runs on, handles at an extreme that
are nearly but not quite horizontal or vertical, and extremes with no node. finish() removes
exactly these, one node at a time:

- a piece shorter than SHORT between two bends is folded away: a bump (bends opposite ways) into
  one smooth node, a bend drawn as two (the same way) into one corner where its neighbours meet;
- a straight piece shorter than FLAT between two curves that it joins almost smoothly (each join
  turns by less than SMOOTH degrees) is a flat spot: the curves meet at its middle instead;
- a join that turns by less than SMOOTH degrees becomes smooth, its handles turned to their common
  tangent with their lengths kept; one that turns more is a corner and is left alone;
- a smooth tangent within SNAP degrees of horizontal or vertical is squared;
- a curve that passes an extreme away from its ends gets a node there (exact: no shape change).

Each change is tried on its own and kept only if the segments it touches stay within MAX_DEV font
units of where they were, so finishing never moves the outline off the trace by more than that.
Works in font units on pen recordings (closed contours of lines and cubic curves).
"""
import math
import numpy as np

FLAT, SHORT, SMOOTH, SNAP, MAX_DEV = 24.0, 16.0, 12.0, 6.0, 3.0


def _contours(rec):
    out, cur = [], None
    for op, a in rec:
        if op == 'moveTo':
            cur = [tuple(a[0]), []]
        elif op == 'lineTo':
            cur[1].append(['L', [tuple(a[0])]])
        elif op == 'curveTo':
            cur[1].append(['C', [tuple(p) for p in a]])
        elif op in ('closePath', 'endPath'):
            if cur and cur[1]:
                if math.dist(cur[1][-1][1][-1], cur[0]) > 1e-9:      # the implicit closing line
                    cur[1].append(['L', [cur[0]]])
                out.append(cur[1])
            cur = None
    return out


def _record(contours):
    rec = []
    for segs in contours:
        rec.append(('moveTo', (segs[-1][1][-1],)))
        for k, pts in segs:
            rec.append(('lineTo', (pts[0],)) if k == 'L' else ('curveTo', tuple(pts)))
        rec.append(('closePath', ()))
    return rec


def _start(segs, i):
    return segs[i - 1][1][-1]


def _points(a, seg, n=16):
    k, p = seg
    a = np.array(a, float)
    if k == 'L':
        b = np.array(p[0], float)
        return [a + (b - a) * t for t in np.linspace(0, 1, 5)]
    c1, c2, b = (np.array(q, float) for q in p)
    return [(1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t * t * c2 + t ** 3 * b for t in np.linspace(0, 1, n)]


def _chain(start, segs):
    pts, a = [], start
    for s in segs:
        pts += _points(a, s)
        a = s[1][-1]
    return np.array(pts)


def _dist_to(pts, poly):
    a, b = poly[:-1], poly[1:]; d = b - a
    L = np.maximum((d ** 2).sum(1), 1e-12)
    worst = 0.0
    for p in pts:
        t = np.clip(((p - a) * d).sum(1) / L, 0, 1)
        worst = max(worst, float(np.sqrt((((a + d * t[:, None]) - p) ** 2).sum(1)).min()))
    return worst


def _close_enough(start, old, new):
    A, B = _chain(start, old), _chain(start, new)
    return max(_dist_to(B, A), _dist_to(A, B)) <= MAX_DEV


def _tangents(segs, i):
    """Incoming tangent at the end of segment i, outgoing tangent at the start of segment i+1."""
    k, p = segs[i]; nk, np_ = segs[(i + 1) % len(segs)]
    end = p[-1]
    back = p[1] if k == 'C' else _start(segs, i)
    return (end[0] - back[0], end[1] - back[1]), (np_[0][0] - end[0], np_[0][1] - end[1])


def _turn(u, v):
    if math.hypot(*u) < 1e-6 or math.hypot(*v) < 1e-6:
        return 0.0
    return abs(math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])))


def _square(d):
    off = math.degrees(math.atan2(abs(d[1]), abs(d[0])))          # 0 horizontal .. 90 vertical
    if off < SNAP:
        return (math.copysign(1.0, d[0]), 0.0)
    if off > 90 - SNAP:
        return (0.0, math.copysign(1.0, d[1]))
    return d


def _signed(u, v):
    if math.hypot(*u) < 1e-6 or math.hypot(*v) < 1e-6:
        return 0.0
    return math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1]))


def _moved(seg, at_start, to, frm):
    """A segment with one end moved to `to` (from `frm`), its handle on that end moved with it."""
    k, p = seg
    d = (to[0] - frm[0], to[1] - frm[1])
    if k == 'L':
        return ['L', [to]] if not at_start else ['L', list(p)]
    c1, c2, e = p
    if at_start:
        return ['C', [(c1[0] + d[0], c1[1] + d[1]), c2, e]]
    return ['C', [c1, (c2[0] + d[0], c2[1] + d[1]), to]]


def _collapse_short(segs):
    """A short piece between two bends: a bump (bends opposite ways) becomes one smooth node at its
    middle; one bend made of two (the same way) becomes a single corner where the long neighbours'
    tangents meet, or a smooth node if together they turn less than SMOOTH."""
    changed = True
    while changed and len(segs) > 3:
        changed = False
        for i in range(len(segs)):
            ip, inx = (i - 1) % len(segs), (i + 1) % len(segs)
            a, b = _start(segs, i), segs[i][1][-1]
            if math.dist(a, b) >= SHORT:
                continue
            u1, v1 = _tangents(segs, ip); u2, v2 = _tangents(segs, i)
            s1, s2 = _signed(u1, v1), _signed(u2, v2)
            if not (2.5 < abs(s1) < 40 and 2.5 < abs(s2) < 40):
                continue
            prev, nxt = segs[ip], segs[inx]
            pa = _start(segs, ip)
            if s1 * s2 < 0 or abs(s1 + s2) < SMOOTH:            # a bump, or a gentle bend: smooth node
                node = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                np1 = _moved(prev, False, node, a); nn1 = _moved(nxt, True, node, b)
            else:                                               # one bend: a corner where the tangents meet
                d1, d2 = u1, v2
                den = d1[0] * d2[1] - d1[1] * d2[0]
                if abs(den) < 1e-9:
                    continue
                t = ((b[0] - a[0]) * d2[1] - (b[1] - a[1]) * d2[0]) / den
                node = (a[0] + d1[0] * t, a[1] + d1[1] * t)
                if math.dist(node, a) > 2 * SHORT or math.dist(node, b) > 2 * SHORT:
                    continue
                np1 = _moved(prev, False, node, a); nn1 = _moved(nxt, True, node, b)
            if prev[0] == 'L':
                np1 = ['L', [node]]
            if _close_enough(pa, [prev, segs[i], nxt], [np1, nn1]):
                segs[ip], segs[inx] = np1, nn1
                del segs[i]
                changed = True
                break
    return segs


def _merge_flats(segs):
    """Fold each flat spot (a short line joined almost smoothly to curves either side) into a node."""
    i = 0
    while i < len(segs) and len(segs) > 3:
        k, p = segs[i]; ip, inx = (i - 1) % len(segs), (i + 1) % len(segs)
        prev, nxt = segs[ip], segs[inx]
        a, b = _start(segs, i), p[0]
        if k == 'L' and prev[0] == 'C' and nxt[0] == 'C' and math.dist(a, b) < FLAT:
            t1 = _turn(*_tangents(segs, ip)); t2 = _turn(*_tangents(segs, i))
            if t1 < SMOOTH and t2 < SMOOTH:
                mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                d = _square(((b[0] - a[0]) / math.dist(a, b), (b[1] - a[1]) / math.dist(a, b)))
                c1, c2, _ = prev[1]; n1, n2, ne = nxt[1]
                lin = math.dist(c2, a) + math.dist(a, mid) * 0.5; lout = math.dist(n1, b) + math.dist(b, mid) * 0.5
                np1 = ['C', [c1, (mid[0] - d[0] * lin, mid[1] - d[1] * lin), mid]]
                nn1 = ['C', [(mid[0] + d[0] * lout, mid[1] + d[1] * lout), n2, ne]]
                start = _start(segs, ip)
                if _close_enough(start, [prev, segs[i], nxt], [np1, nn1]):
                    segs[ip] = np1; segs[inx] = nn1; del segs[i]
                    continue
        i += 1
    return segs


def _smooth(segs):
    for i in range(len(segs)):
        j = (i + 1) % len(segs)
        k, p = segs[i]; nk, np_ = segs[j]
        if k == 'L' and nk == 'L':
            continue
        tin, tout = _tangents(segs, i)
        lin, lout = math.hypot(*tin), math.hypot(*tout)
        if lin < 1e-6 or lout < 1e-6 or _turn(tin, tout) >= SMOOTH:
            continue                                               # degenerate, or a corner
        node = p[-1]
        if k == 'L':
            d = (tin[0] / lin, tin[1] / lin)                         # the curve follows the line
        elif nk == 'L':
            d = (tout[0] / lout, tout[1] / lout)
        else:
            d = (tin[0] / lin + tout[0] / lout, tin[1] / lin + tout[1] / lout)
            n = math.hypot(*d); d = _square((d[0] / n, d[1] / n))
        new_i = ['C', [p[0], (node[0] - d[0] * lin, node[1] - d[1] * lin), node]] if k == 'C' else segs[i]
        new_j = ['C', [(node[0] + d[0] * lout, node[1] + d[1] * lout), np_[1], np_[2]]] if nk == 'C' else segs[j]
        if _close_enough(_start(segs, i), [segs[i], segs[j]], [new_i, new_j]):
            segs[i], segs[j] = new_i, new_j
    return segs


def _split_extrema(segs, min_t=0.08):
    out = []
    for i, (k, p) in enumerate(segs):
        if k != 'C':
            out.append([k, p]); continue
        a = np.array(_start(segs, i), float); c1, c2, b = (np.array(q, float) for q in p)
        ts = []
        for ax in (0, 1):
            A = -a[ax] + 3 * c1[ax] - 3 * c2[ax] + b[ax]; B = 2 * (a[ax] - 2 * c1[ax] + c2[ax]); C = c1[ax] - a[ax]
            if abs(A) < 1e-12:
                roots = [-C / B] if abs(B) > 1e-12 else []
            else:
                disc = B * B - 4 * A * C
                roots = [(-B + s * math.sqrt(disc)) / (2 * A) for s in (1, -1)] if disc >= 0 else []
            ts += [t for t in roots if min_t < t < 1 - min_t]
        if not ts:
            out.append([k, p]); continue
        pts, done = [a, c1, c2, b], 0.0
        for t in sorted(set(round(t, 6) for t in ts)):
            u = (t - done) / (1 - done)
            p0, p1, p2, p3 = pts
            q0 = p0 + (p1 - p0) * u; q1 = p1 + (p2 - p1) * u; q2 = p2 + (p3 - p2) * u
            r0 = q0 + (q1 - q0) * u; r1 = q1 + (q2 - q1) * u; s = r0 + (r1 - r0) * u
            out.append(['C', [tuple(q0), tuple(r0), tuple(s)]])
            pts, done = [s, r1, q2, p3], t
        out.append(['C', [tuple(pts[1]), tuple(pts[2]), tuple(pts[3])]])
    return out


def finish(rec):
    """The finished pen recording."""
    out = []
    for segs in _contours(rec):
        f = [[k, list(p)] for k, p in segs]
        f = _smooth(_split_extrema(_smooth(_merge_flats(_collapse_short(f)))))
        out.append(f)
    return _record(out)


# ---------------------------------------------------------------------------------------------
# Refitting: undulations finer than a source pixel are print and scan noise, not drawing. A fitter
# that follows the scanned edge closely keeps them as slow waves along edges a designer would draw
# straight or as one curve. refit() redraws each contour from dense samples of the trace with the
# research rounds' designer-style fitter (curvefit3.contour_to_curves4), at tolerances measured in
# the glyph's own source pixels, then finish() tidies the nodes. Kept only if it preserves the
# contour count and stays within MAX_PX source pixels of the trace.
REFIT_PX = dict(rms_tol=0.35, max_tol=0.9, line_tol=0.8, line_bulge=0.25, cutoff=24.0, line_min=16.0)
REFIT_FIXED = dict(corner_deg=52, snap_deg=3.0)
MAX_PX = 1.4


def _dense(segs, step):
    pts = []
    for i, (k, p) in enumerate(segs):
        a = np.array(_start(segs, i), float)
        if k == 'L':
            b = np.array(p[0], float); n = max(2, int(np.linalg.norm(b - a) / step))
            pts += [a + (b - a) * t for t in np.linspace(0, 1, n, endpoint=False)]
        else:
            c1, c2, b = (np.array(q, float) for q in p)
            n = max(4, 2 * int(np.linalg.norm(b - a) / step))
            pts += [(1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t * t * c2 + t ** 3 * b
                    for t in np.linspace(0, 1, n, endpoint=False)]
    return np.array(pts)


def refit(rec, unit, px):
    """rec in font units; `unit` font units per trace unit, `px` one source pixel in trace units.
    Returns the refitted recording, or None where refitting would change the glyph too much."""
    from curvefit3 import contour_to_curves4
    params = {k: v * px for k, v in REFIT_PX.items()}; params.update(REFIT_FIXED)
    out = []
    for segs in _contours(rec):
        P = _dense(segs, 0.05 * unit) / unit * [1, -1]                 # trace units, y down
        try:
            curves = contour_to_curves4(P, **params)
        except Exception:
            return None
        new = []
        for c in curves:
            c = c * [1, -1] * unit
            p0, c1, c2, p3 = (tuple(map(float, q)) for q in c)
            straight = np.allclose(c1, np.add(p0, np.subtract(p3, p0) / 3), atol=1e-6) and \
                np.allclose(c2, np.add(p0, 2 * np.subtract(p3, p0) / 3), atol=1e-6)
            new.append(['L', [p3]] if straight else ['C', [c1, c2, p3]])
        if len(new) < 2:
            return None
        A, B = _dense(segs, 0.25 * unit * px), _dense(new, 0.25 * unit * px)
        if max(_dist_to(B, np.vstack([A, A[:1]])), _dist_to(A, np.vstack([B, B[:1]]))) > MAX_PX * px * unit:
            return None
        out.append(new)
    return _record(out)
