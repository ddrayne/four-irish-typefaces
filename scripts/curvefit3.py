"""Contour -> designer-style outline (third generation).

The v2 fitter followed the photocopy edge to within ~0.1 px, so its outlines kept the
toner wobble. This one redraws the way a type designer would from a scan:

1. corners are found on a lightly smoothed edge and kept only if they persist at a
   coarser scale (noise kinks don't);
2. long straight runs (stems, bars, serif faces) are detected and drawn as true lines,
   snapped to vertical/horizontal when they are within a few degrees;
3. adjacent straight lines meet at their exact intersection, so corners are crisp;
4. everything else is fitted with as few cubic Béziers as the tolerance allows, joined
   tangent-continuously to the neighbouring lines.

Coordinates are source px throughout.
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d
from curvefit import resample_closed, turning, add_extrema, _unit, _bez, _generate, _reparam, _chord_param, _split_cubic, _extrema_t


def _nms(ang, thr, sep):
    n = len(ang); idx = []
    order = np.argsort(-ang)
    taken = np.zeros(n, bool)
    for i in order:
        if ang[i] < thr:
            break
        if taken[i]:
            continue
        idx.append(int(i))
        for j in range(-sep, sep + 1):
            taken[(i + j) % n] = True
    return sorted(idx)


def tls(pts):
    """Total-least-squares line: centre, unit direction, max |deviation|."""
    c = pts.mean(0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    d = vt[0]; nrm = np.array([-d[1], d[0]])
    return c, d, float(np.abs((pts - c) @ nrm).max())


def sagitta(pts):
    """Bulge of the best-fit parabola across the run (px): ~0 for a straight stroke, L^2/8R on an arc."""
    c, d, _ = tls(pts)
    nrm = np.array([-d[1], d[0]])
    u = (pts - c) @ d; v = (pts - c) @ nrm
    if u.max() - u.min() < 1e-6:
        return 0.0
    a = np.polyfit(u, v, 2)[0]
    half = (u.max() - u.min()) / 2
    return abs(a) * half * half


def straight(pts, tol, bulge):
    return tls(pts)[2] <= tol and sagitta(pts) <= bulge


def find_lines(Q, ds, min_len, tol, bulge):
    """Maximal straight sub-runs of the open polyline Q: list of (i, j) index pairs (inclusive).
    A run counts as straight only if it stays within tol of a line AND has no consistent bulge,
    so the flat-looking stretch of a large bowl is not mistaken for a stem."""
    n = len(Q)
    step = max(1, int(round(0.4 / ds)))
    found = []

    def longest(a, b):
        best = None; j = a
        for i in range(a, b, step):
            j = max(j, i + step)
            while j + step < b and straight(Q[i:j + step + 1:step], tol, bulge):
                j += step
            if j < b and (j - i) * ds >= min_len and straight(Q[i:j + 1:step], tol, bulge):
                if best is None or j - i > best[1] - best[0]:
                    best = (i, j)
        return best

    def rec(a, b):
        if (b - a) * ds < min_len:
            return
        best = longest(a, b)
        if best is None:
            return
        found.append(best)
        rec(a, best[0]); rec(best[1] + 1, b)

    rec(0, n)
    return sorted(found)


def _snap(d, snap_deg):
    ang = np.degrees(np.arctan2(d[1], d[0]))
    for axis_ang in (0, 90, 180, -90, -180):
        if abs(ang - axis_ang) < snap_deg:
            a = np.radians(axis_ang)
            return np.array([np.cos(a), np.sin(a)])
    return d


def _project(p, c, d):
    return c + d * np.dot(p - c, d)


def _intersect(c1, d1, c2, d2):
    A = np.array([d1, -d2]).T
    if abs(np.linalg.det(A)) < 1e-6:
        return None
    t = np.linalg.solve(A, c2 - c1)
    return c1 + d1 * t[0]


def fit_rms(pts, t1, t2, tan, rms_tol, max_tol, depth=0):
    """As few cubics as possible: accept a fit when its RMS error is within rms_tol and no point is
    further than max_tol. Unlike a max-error fit this doesn't chase single toner bumps. Splits take
    their tangent from `tan` (unit forward tangents of a well-smoothed copy of pts)."""
    n = len(pts)
    if n < 4:
        d = np.linalg.norm(pts[-1] - pts[0]) / 3
        return [np.array([pts[0], pts[0] + t1 * d, pts[-1] + t2 * d, pts[-1]])]
    u = _chord_param(pts)
    ctrl = _generate(pts, u, t1, t2)
    for _ in range(10):
        u = _reparam(ctrl, pts, u)
        ctrl = _generate(pts, u, t1, t2)
    d = np.linalg.norm(_bez(ctrl, u) - pts, axis=1)
    if (np.sqrt(np.mean(d * d)) <= rms_tol and d.max() <= max_tol) or depth > 10 or n < 10:
        return [ctrl]
    e = gaussian_filter1d(d, 3)
    lo, hi = max(2, int(0.2 * n)), min(n - 3, int(0.8 * n))
    k = lo + int(np.argmax(e[lo:hi])) if hi > lo else n // 2
    tc = tan[k]
    return (fit_rms(pts[:k + 1], t1, -tc, tan[:k + 1], rms_tol, max_tol, depth + 1) +
            fit_rms(pts[k:], tc, t2, tan[k:], rms_tol, max_tol, depth + 1))


def _tangents(Q):
    t = np.gradient(Q, axis=0)
    return t / (np.linalg.norm(t, axis=1, keepdims=True) + 1e-12)


def _end_dir(pts, ds, length=1.2):
    """Forward direction of the first `length` px of an open run (line fit, oriented)."""
    k = max(3, int(round(length / ds)))
    seg = pts[:k + 1]
    if len(seg) < 3:
        return _unit(pts[min(1, len(pts) - 1)] - pts[0])
    _, d, _ = tls(seg)
    return d if np.dot(d, seg[-1] - seg[0]) >= 0 else -d


def contour_to_curves3(P, ds=0.2, sigma_fit=0.5, sigma_line=1.0, sigma_tan=1.5, corner_win=1.0, corner_deg=40.0,
                       persist_win=2.0, persist_frac=0.75, line_min=4.5, line_tol=0.45, line_bulge=0.10,
                       snap_deg=3.0, rms_tol=0.12, max_tol=0.5):
    P = resample_closed(np.asarray(P, float), ds)
    n = len(P)
    P1 = gaussian_filter1d(P, sigma_fit / ds, axis=0, mode='wrap')
    P2 = gaussian_filter1d(P, sigma_line / ds, axis=0, mode='wrap')
    T3 = _tangents(gaussian_filter1d(P, sigma_tan / ds, axis=0, mode='wrap'))
    k = max(2, int(round(corner_win / ds))); kp = max(k + 1, int(round(persist_win / ds)))
    a1 = turning(P1, k); a2 = turning(P1, kp)
    cand = _nms(a1, corner_deg, k)
    corners = [i for i in cand if a2[i] >= persist_frac * corner_deg]

    if not corners:
        # a smooth loop (o, O, counters): cut it at its extreme points, which become on-curve nodes
        ext = sorted(set([int(np.argmin(P2[:, 0])), int(np.argmax(P2[:, 0])),
                          int(np.argmin(P2[:, 1])), int(np.argmax(P2[:, 1]))]))
        cuts = [c for i, c in enumerate(ext) if i == 0 or c - ext[i - 1] > 3] or [0, n // 2]
        if len(cuts) < 2:
            cuts = [cuts[0], (cuts[0] + n // 2) % n]
            cuts.sort()
        curves = []
        for i, a in enumerate(cuts):
            b = cuts[(i + 1) % len(cuts)]
            idx = np.arange(a, b + 1) if b > a else np.concatenate([np.arange(a, n), np.arange(0, b + 1)])
            seg = P1[idx].copy(); seg[0] = P2[a]; seg[-1] = P2[b]
            curves += fit_rms(seg, T3[a], -T3[b], T3[idx], rms_tol, max_tol)
        return add_extrema(curves)

    m = len(corners)
    runs = []
    for r in range(m):
        a, b = corners[r], corners[(r + 1) % m]
        idx = np.arange(a, b + 1) if b > a else np.concatenate([np.arange(a, n), np.arange(0, b + 1)])
        if m == 1:
            idx = np.concatenate([np.arange(a, n), np.arange(0, a + 1)])
        Q2 = P2[idx]
        lines = []
        for (i, j) in find_lines(Q2, ds, line_min, line_tol, line_bulge):
            c, d, _ = tls(P1[idx][i:j + 1])
            if np.dot(d, Q2[j] - Q2[i]) < 0:
                d = -d
            lines.append(dict(i=i, j=j, c=c, d=_snap(d, snap_deg)))
        runs.append(dict(idx=idx, lines=lines))

    # corner positions: exact intersections where straight lines meet
    cpos = []
    for r in range(m):
        prev, cur = runs[r - 1], runs[r]
        pt = P1[corners[r]].copy()
        lin = prev['lines'][-1] if prev['lines'] and prev['lines'][-1]['j'] >= len(prev['idx']) - 3 else None
        lout = cur['lines'][0] if cur['lines'] and cur['lines'][0]['i'] <= 2 else None
        if lin and lout:
            x = _intersect(lin['c'], lin['d'], lout['c'], lout['d'])
            pt = x if x is not None and np.linalg.norm(x - pt) < 1.0 else _project(pt, lin['c'], lin['d'])
        elif lin:
            pt = _project(pt, lin['c'], lin['d'])
        elif lout:
            pt = _project(pt, lout['c'], lout['d'])
        cpos.append(pt)

    curves = []
    for r in range(m):
        run = runs[r]; idx = run['idx']; Q1 = P1[idx]; T = T3[idx]; L = len(idx)
        start, end = cpos[r], cpos[(r + 1) % m]

        def curve(p_from, t_from, i_from, p_to, t_to, i_to):
            if i_to - i_from < 3:
                d = np.linalg.norm(p_to - p_from) / 3
                return [np.array([p_from, p_from + t_from * d, p_to + t_to * d, p_to])]
            pts = Q1[i_from:i_to + 1].copy(); pts[0] = p_from; pts[-1] = p_to
            tt = T[i_from:i_to + 1]
            if np.linalg.norm(p_to - p_from) < 1e-6:            # whole loop from one corner: split it
                h = len(pts) // 2
                return (fit_rms(pts[:h + 1], t_from, -tt[h], tt[:h + 1], rms_tol, max_tol) +
                        fit_rms(pts[h:], tt[h], t_to, tt[h:], rms_tol, max_tol))
            return fit_rms(pts, t_from, t_to, tt, rms_tol, max_tol)

        items = []
        for ln in run['lines']:
            p0 = start if ln['i'] <= 2 else _project(Q1[ln['i']], ln['c'], ln['d'])
            p1 = end if ln['j'] >= L - 3 else _project(Q1[ln['j']], ln['c'], ln['d'])
            items.append((ln['i'], ln['j'], p0, p1, ln['d']))
        prev_i, prev_pt, prev_t = 0, start, None
        for (i, j, p0, p1, d) in items:
            if i > prev_i + 1 or np.linalg.norm(p0 - prev_pt) > 1e-6:
                t_from = prev_t if prev_t is not None else _end_dir(Q1[prev_i:], ds)
                curves += curve(prev_pt, t_from, prev_i, p0, -d, max(i, prev_i + 1))
            curves.append(np.array([p0, p0 + (p1 - p0) / 3, p0 + 2 * (p1 - p0) / 3, p1]))
            prev_i, prev_pt, prev_t = j, p1, d
        if prev_i < L - 1 or np.linalg.norm(end - prev_pt) > 1e-6:
            t_from = prev_t if prev_t is not None else _end_dir(Q1[prev_i:], ds)
            t_to = _end_dir(Q1[::-1], ds)
            curves += curve(prev_pt, t_from, prev_i, end, t_to, L - 1)
    curves = [c for c in curves if np.linalg.norm(c[3] - c[0]) > 1e-4 or np.linalg.norm(c[1] - c[0]) > 1e-4]
    return add_extrema(curves)


def corner_angles(P, ds, gap=0.4, w=1.6):
    """Angle (deg) between the edge direction just before and just after each point of a closed
    polyline, each fitted over [gap, w] px away from the point. A smooth curve of radius R gives
    about 2*(gap+w)/2/R rad; a real corner gives its full angle; a toner bump mostly averages out."""
    n = len(P)
    g = max(1, int(round(gap / ds))); W = max(g + 2, int(round(w / ds)))
    ext = np.vstack([P[-W:], P, P[:W]])
    def dirs(offset_lo, offset_hi):
        out = np.zeros((n, 2))
        for i in range(n):
            seg = ext[W + i + offset_lo: W + i + offset_hi + 1]
            c = seg.mean(0); _, _, vt = np.linalg.svd(seg - c, full_matrices=False)
            d = vt[0]
            if np.dot(d, seg[-1] - seg[0]) < 0:
                d = -d
            out[i] = d
        return out
    before = dirs(-W, -g); after = dirs(g, W)
    cosang = np.clip((before * after).sum(1), -1, 1)
    return np.degrees(np.arccos(cosang))


# ---------------------------------------------------------------- curvature-variation smoothing (v4)
from scipy import sparse
from scipy.sparse.linalg import spsolve


def _lam(cutoff_px, ds):
    """Weight giving a 6th-order low-pass whose half-power wavelength is cutoff_px."""
    return (cutoff_px / (2 * np.pi * ds)) ** 6


def spline_smooth(Q, lam, closed=False):
    """Minimise |X - Q|^2 + lam |D3 X|^2 (third differences along the curve).

    Lines and circular arcs have ~zero third derivative, so they pass unchanged; toner wobble
    (short wavelength, high curvature variation) is removed. Open runs keep their endpoints."""
    n = len(Q)
    if n < 8:
        return Q.copy()
    if closed:
        rows = np.arange(n)
        D = sparse.csr_matrix((np.tile([-1.0, 3.0, -3.0, 1.0], n),
                               (np.repeat(rows, 4), (rows[:, None] + np.arange(4)[None, :]).ravel() % n)), shape=(n, n))
        A = sparse.identity(n) + lam * (D.T @ D)
        return np.stack([spsolve(A.tocsc(), Q[:, k]) for k in (0, 1)], 1)
    m = n - 3
    rows = np.arange(m)
    D = sparse.csr_matrix((np.tile([-1.0, 3.0, -3.0, 1.0], m),
                           (np.repeat(rows, 4), (rows[:, None] + np.arange(4)[None, :]).ravel())), shape=(m, n))
    A = (sparse.identity(n) + lam * (D.T @ D)).tolil()
    big = 1e9                                   # pin the endpoints (corners)
    A[0, 0] += big; A[n - 1, n - 1] += big
    A = A.tocsc()
    out = np.zeros_like(Q)
    for k in (0, 1):
        b = Q[:, k].copy(); b[0] += big * Q[0, k]; b[-1] += big * Q[-1, k]
        out[:, k] = spsolve(A, b)
    return out


def _merge_collinear(lines, Sm, ds, line_tol, snap_deg, max_gap=2.0, max_turn=4.0):
    """Join consecutive lines that are nearly collinear and close together into one (a tapering stem
    is one slightly slanted line, not two vertical ones with a step between them)."""
    out = []
    for ln in lines:
        if out:
            a = out[-1]
            turn = np.degrees(np.arccos(np.clip(np.dot(a['d'], ln['d']), -1, 1)))
            if turn <= max_turn and (ln['i'] - a['j']) * ds <= max_gap:
                c, d, dev = tls(Sm[a['i']:ln['j'] + 1])
                if dev <= 1.2 * line_tol:
                    if np.dot(d, Sm[ln['j']] - Sm[a['i']]) < 0:
                        d = -d
                    out[-1] = dict(i=a['i'], j=ln['j'], c=c, d=_snap(d, snap_deg))
                    continue
        out.append(ln)
    return out


def _absorb_ends(lines, Sm, ds, ext_tol):
    """Stretch each line over neighbouring points that stay within ext_tol of it, and drop the tiny
    curve left between a line and the run's corner, so lines meet corners and curves cleanly."""
    L = len(Sm)
    out = []
    for k, ln in enumerate(lines):
        i, j, c, d = ln['i'], ln['j'], ln['c'], ln['d']
        nrm = np.array([-d[1], d[0]])
        lo = out[-1]['j'] if out else 0
        hi = lines[k + 1]['i'] if k + 1 < len(lines) else L - 1
        while i - 1 > lo and abs(np.dot(Sm[i - 1] - c, nrm)) <= ext_tol:
            i -= 1
        while j + 1 < hi and abs(np.dot(Sm[j + 1] - c, nrm)) <= ext_tol:
            j += 1
        if i * ds < 0.6 and i > 0:
            i = 0
        if (L - 1 - j) * ds < 0.6 and j < L - 1:
            j = L - 1
        out.append(dict(ln, i=i, j=j))
    return out


def contour_to_curves4(P, ds=0.2, cutoff=4.0, corner_deg=55.0, corner_gap=0.4, corner_w=1.6,
                       line_min=4.0, line_tol=0.14, line_bulge=0.05, snap_deg=3.0, rms_tol=0.05, max_tol=0.18,
                       axis_deg=12.0, diag_min=6.0, ext_tol=0.12):
    P = resample_closed(np.asarray(P, float), ds)
    n = len(P)
    lam = _lam(cutoff, ds)
    P1 = gaussian_filter1d(P, 0.4 / ds, axis=0, mode='wrap')
    ang = corner_angles(P1, ds, corner_gap, corner_w)
    corners = _nms(ang, corner_deg, max(2, int(round(1.0 / ds))))

    if not corners:
        Sm = spline_smooth(P, lam, closed=True)
        T = _tangents(Sm)
        ext = sorted(set([int(np.argmin(Sm[:, 0])), int(np.argmax(Sm[:, 0])),
                          int(np.argmin(Sm[:, 1])), int(np.argmax(Sm[:, 1]))]))
        cuts = [c for i, c in enumerate(ext) if i == 0 or c - ext[i - 1] > 3]
        if len(cuts) < 2:
            cuts = sorted([cuts[0], (cuts[0] + n // 2) % n])
        curves = []
        for i, a in enumerate(cuts):
            b = cuts[(i + 1) % len(cuts)]
            idx = np.arange(a, b + 1) if b > a else np.concatenate([np.arange(a, n), np.arange(0, b + 1)])
            curves += fit_rms(Sm[idx], T[a], -T[b], T[idx], rms_tol, max_tol)
        return add_extrema4(curves)

    m = len(corners)
    runs = []
    for r in range(m):
        a, b = corners[r], corners[(r + 1) % m]
        idx = np.arange(a, b + 1) if b > a else np.concatenate([np.arange(a, n), np.arange(0, b + 1)])
        if m == 1:
            idx = np.concatenate([np.arange(a, n), np.arange(0, a + 1)])
        Q = P[idx].copy(); Q[0] = P1[idx[0]]; Q[-1] = P1[idx[-1]]
        Sm = spline_smooth(Q, lam)
        lines = []
        for (i, j) in find_lines(Sm, ds, line_min, line_tol, line_bulge):
            c, d, _ = tls(Sm[i:j + 1])
            if np.dot(d, Sm[j] - Sm[i]) < 0:
                d = -d
            # a straight run is kept only where a designer would rule a line: along an axis
            # (stems, bars, flat serif faces), or a long diagonal (v, x, z strokes)
            ang = abs(np.degrees(np.arctan2(d[1], d[0]))) % 90
            near_axis = min(ang, 90 - ang) <= axis_deg
            if not near_axis and (j - i) * ds < diag_min:
                continue
            if near_axis or tls(Sm[i:j + 1])[2] <= 0.6 * line_tol:
                lines.append(dict(i=i, j=j, c=c, d=_snap(d, snap_deg)))
        lines = _merge_collinear(lines, Sm, ds, line_tol, snap_deg)
        lines = _absorb_ends(lines, Sm, ds, ext_tol)
        runs.append(dict(idx=idx, S=Sm, T=_tangents(Sm), lines=lines))

    cpos = []
    for r in range(m):
        prev, cur = runs[r - 1], runs[r]
        pt = cur['S'][0].copy()
        lin = prev['lines'][-1] if prev['lines'] and prev['lines'][-1]['j'] >= len(prev['idx']) - 3 else None
        lout = cur['lines'][0] if cur['lines'] and cur['lines'][0]['i'] <= 2 else None
        if lin and lout:
            x = _intersect(lin['c'], lin['d'], lout['c'], lout['d'])
            pt = x if x is not None and np.linalg.norm(x - pt) < 1.0 else _project(pt, lin['c'], lin['d'])
        elif lin:
            pt = _project(pt, lin['c'], lin['d'])
        elif lout:
            pt = _project(pt, lout['c'], lout['d'])
        cpos.append(pt)

    curves = []
    for r in range(m):
        run = runs[r]; Sm = run['S']; T = run['T']; L = len(Sm)
        start, end = cpos[r], cpos[(r + 1) % m]

        def curve(p_from, t_from, i_from, p_to, t_to, i_to):
            if i_to - i_from < 3:
                d = np.linalg.norm(p_to - p_from) / 3
                return [np.array([p_from, p_from + t_from * d, p_to + t_to * d, p_to])]
            pts = Sm[i_from:i_to + 1].copy(); pts[0] = p_from; pts[-1] = p_to
            tt = T[i_from:i_to + 1]
            if np.linalg.norm(p_to - p_from) < 1e-6:
                h = len(pts) // 2
                return (fit_rms(pts[:h + 1], t_from, -tt[h], tt[:h + 1], rms_tol, max_tol) +
                        fit_rms(pts[h:], tt[h], t_to, tt[h:], rms_tol, max_tol))
            return fit_rms(pts, t_from, t_to, tt, rms_tol, max_tol)

        prev_i, prev_pt, prev_t = 0, start, None
        for ln in run['lines']:
            i, j, d = ln['i'], ln['j'], ln['d']
            p0 = start if i <= 2 else _project(Sm[i], ln['c'], d)
            p1 = end if j >= L - 3 else _project(Sm[j], ln['c'], d)
            if i > prev_i + 1 or np.linalg.norm(p0 - prev_pt) > 1e-6:
                t_from = prev_t if prev_t is not None else _end_dir(Sm[prev_i:], ds, 0.6)
                curves += curve(prev_pt, t_from, prev_i, p0, -d, max(i, prev_i + 1))
            curves.append(np.array([p0, p0 + (p1 - p0) / 3, p0 + 2 * (p1 - p0) / 3, p1]))
            prev_i, prev_pt, prev_t = j, p1, d
        if prev_i < L - 1 or np.linalg.norm(end - prev_pt) > 1e-6:
            t_from = prev_t if prev_t is not None else _end_dir(Sm[prev_i:], ds, 0.6)
            curves += curve(prev_pt, t_from, prev_i, end, _end_dir(Sm[::-1], ds, 0.6), L - 1)
    curves = [c for c in curves if np.linalg.norm(c[3] - c[0]) > 1e-4 or np.linalg.norm(c[1] - c[0]) > 1e-4]
    return add_extrema4(curves)


def add_extrema4(curves, edge=0.12):
    """Split curves at x/y extrema (as fonts expect), except where the extremum is so close to an
    existing node that the split would leave a sliver; there the node's handles are simply levelled."""
    out = []
    for c in curves:
        ts = sorted(set(_extrema_t(c, 0) + _extrema_t(c, 1)))
        ts = [t for t in ts if edge < t < 1 - edge]
        rest = c; last = 0.0
        for t in ts:
            lt = (t - last) / (1 - last)
            if not edge < lt < 1 - edge:
                continue
            a, rest = _split_cubic(rest, lt)
            out.append(a); last = t
        out.append(rest)
    return add_extrema(drop_tiny(out))


def drop_tiny(curves, min_len=0.4):
    """Remove segments shorter than min_len px by moving their shared end to their midpoint."""
    cs = [c.copy() for c in curves]
    changed = True
    while changed and len(cs) > 3:
        changed = False
        for k, c in enumerate(cs):
            if np.linalg.norm(c[3] - c[0]) < min_len and np.linalg.norm(c[1] - c[0]) + np.linalg.norm(c[2] - c[3]) < 2 * min_len:
                prev, nxt = cs[k - 1], cs[(k + 1) % len(cs)]
                mid = (c[0] + c[3]) / 2
                d0 = mid - prev[3]; prev[3] = mid; prev[2] = prev[2] + d0
                d1 = mid - nxt[0]; nxt[0] = mid; nxt[1] = nxt[1] + d1
                del cs[k]; changed = True
                break
    return cs
