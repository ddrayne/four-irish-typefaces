"""Contour -> clean cubic Bézier outline.

Sub-pixel iso-contours from marching squares are resampled, real corners are
detected and pinned, the runs between corners are smoothed along their length
(removing photocopy wobble without rounding the corners), and each run is fitted
with cubic Béziers (Schneider, "An Algorithm for Automatically Fitting Digitized
Curves", Graphics Gems 1990). Curves are then split at their x/y extrema and the
handles at extrema are made exactly horizontal/vertical.
"""
import numpy as np
from scipy.ndimage import gaussian_filter1d


# ---------------------------------------------------------------- polyline prep
def resample_closed(P, ds):
    Q = np.vstack([P, P[:1]])
    seg = np.sqrt((np.diff(Q, axis=0) ** 2).sum(1))
    s = np.concatenate([[0], np.cumsum(seg)])
    L = s[-1]
    n = max(int(round(L / ds)), 12)
    t = np.linspace(0, L, n, endpoint=False)
    return np.stack([np.interp(t, s, Q[:, 0]), np.interp(t, s, Q[:, 1])], 1)


def turning(P, k):
    f = np.roll(P, -k, 0) - P
    b = P - np.roll(P, k, 0)
    nf = np.linalg.norm(f, axis=1) + 1e-12
    nb = np.linalg.norm(b, axis=1) + 1e-12
    c = np.clip((f * b).sum(1) / (nf * nb), -1, 1)
    return np.degrees(np.arccos(c))


def find_corners(P, k, thr):
    ang = turning(P, k)
    n = len(P)
    idx = []
    for i in range(n):
        if ang[i] < thr:
            continue
        win = [ang[(i + j) % n] for j in range(-k, k + 1)]
        if ang[i] >= max(win) and not any(abs(i - q) <= k or n - abs(i - q) <= k for q in idx):
            idx.append(i)
    return sorted(idx), ang


def smooth_open(seg, sigma):
    """Gaussian smoothing with both endpoints fixed (odd reflection about each end)."""
    if len(seg) < 5 or sigma <= 0:
        return seg
    pad = min(len(seg) - 1, int(3 * sigma) + 1)
    head = 2 * seg[0] - seg[1:pad + 1][::-1]
    tail = 2 * seg[-1] - seg[-pad - 1:-1][::-1]
    ext = np.vstack([head, seg, tail])
    sm = gaussian_filter1d(ext, sigma, axis=0, mode='nearest')[pad:pad + len(seg)]
    sm[0], sm[-1] = seg[0], seg[-1]
    return sm


# ---------------------------------------------------------------- Schneider fit
def _bez(ctrl, t):
    t = np.asarray(t)[:, None]
    mt = 1 - t
    return mt ** 3 * ctrl[0] + 3 * mt * mt * t * ctrl[1] + 3 * mt * t * t * ctrl[2] + t ** 3 * ctrl[3]


def _bez_d(ctrl, t):
    t = np.asarray(t)[:, None]
    mt = 1 - t
    return 3 * mt * mt * (ctrl[1] - ctrl[0]) + 6 * mt * t * (ctrl[2] - ctrl[1]) + 3 * t * t * (ctrl[3] - ctrl[2])


def _bez_dd(ctrl, t):
    t = np.asarray(t)[:, None]
    return 6 * (1 - t) * (ctrl[2] - 2 * ctrl[1] + ctrl[0]) + 6 * t * (ctrl[3] - 2 * ctrl[2] + ctrl[1])


def _chord_param(pts):
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    return d / d[-1] if d[-1] > 0 else np.linspace(0, 1, len(pts))


def _generate(pts, u, t1, t2):
    p0, p3 = pts[0], pts[-1]
    A1 = t1[None, :] * (3 * (1 - u) ** 2 * u)[:, None]
    A2 = t2[None, :] * (3 * (1 - u) * u ** 2)[:, None]
    C = np.array([[np.sum(A1 * A1), np.sum(A1 * A2)], [np.sum(A1 * A2), np.sum(A2 * A2)]])
    base = _bez(np.array([p0, p0, p3, p3]), u)
    tmp = pts - base
    X = np.array([np.sum(A1 * tmp), np.sum(A2 * tmp)])
    det = C[0, 0] * C[1, 1] - C[0, 1] * C[1, 0]
    seg_len = np.linalg.norm(p3 - p0)
    a1 = a2 = 0.0
    if abs(det) > 1e-12:
        a1 = (X[0] * C[1, 1] - X[1] * C[0, 1]) / det
        a2 = (C[0, 0] * X[1] - C[1, 0] * X[0]) / det
    eps = 1e-6 * seg_len
    if a1 < eps or a2 < eps:
        a1 = a2 = seg_len / 3.0
    return np.array([p0, p0 + t1 * a1, p3 + t2 * a2, p3])


def _reparam(ctrl, pts, u):
    q = _bez(ctrl, u) - pts
    d1 = _bez_d(ctrl, u)
    d2 = _bez_dd(ctrl, u)
    num = (q * d1).sum(1)
    den = (d1 * d1).sum(1) + (q * d2).sum(1)
    with np.errstate(divide='ignore', invalid='ignore'):
        nu = np.where(np.abs(den) > 1e-12, u - num / den, u)
    nu = np.clip(nu, 0, 1)
    nu[0], nu[-1] = 0.0, 1.0
    return np.maximum.accumulate(nu)


def _max_err(ctrl, pts, u):
    d = np.linalg.norm(_bez(ctrl, u) - pts, axis=1)
    i = int(np.argmax(d))
    return d[i], i


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def fit_cubics(pts, t1, t2, tol, depth=0):
    """Fit points with cubic Béziers; t1 points along the curve at the start, t2 back along it at the end."""
    if len(pts) == 2:
        d = np.linalg.norm(pts[1] - pts[0]) / 3
        return [np.array([pts[0], pts[0] + t1 * d, pts[1] + t2 * d, pts[1]])]
    u = _chord_param(pts)
    ctrl = _generate(pts, u, t1, t2)
    err, split = _max_err(ctrl, pts, u)
    if err < tol:
        return [ctrl]
    if err < 4 * tol:
        for _ in range(20):
            u = _reparam(ctrl, pts, u)
            ctrl = _generate(pts, u, t1, t2)
            err, split = _max_err(ctrl, pts, u)
            if err < tol:
                return [ctrl]
    if depth > 24 or len(pts) < 4:
        return [ctrl]
    split = min(max(split, 1), len(pts) - 2)
    tc = _unit(pts[split - 1] - pts[split + 1])
    return (fit_cubics(pts[:split + 1], t1, tc, tol, depth + 1) +
            fit_cubics(pts[split:], -tc, t2, tol, depth + 1))


def end_tangents(seg, k):
    k = max(1, min(k, len(seg) - 1))
    return _unit(seg[k] - seg[0]), _unit(seg[-1 - k] - seg[-1])


# ---------------------------------------------------------------- extrema & cleanup
def _split_cubic(c, t):
    p0, p1, p2, p3 = c
    a = p0 + (p1 - p0) * t; b = p1 + (p2 - p1) * t; cc = p2 + (p3 - p2) * t
    d = a + (b - a) * t; e = b + (cc - b) * t; f = d + (e - d) * t
    return np.array([p0, a, d, f]), np.array([f, e, cc, p3])


def _extrema_t(c, axis):
    p0, p1, p2, p3 = c[:, axis]
    a = -p0 + 3 * p1 - 3 * p2 + p3
    b = 2 * (p0 - 2 * p1 + p2)
    cc = p1 - p0
    ts = []
    if abs(a) < 1e-12:
        if abs(b) > 1e-12:
            ts = [-cc / b]
    else:
        disc = b * b - 4 * a * cc
        if disc >= 0:
            r = np.sqrt(disc)
            ts = [(-b + r) / (2 * a), (-b - r) / (2 * a)]
    return [t for t in ts if 0.03 < t < 0.97]


def add_extrema(curves):
    out = []
    for c in curves:
        ts = sorted(set(_extrema_t(c, 0) + _extrema_t(c, 1)))
        rest = c; last = 0.0
        for t in ts:
            lt = (t - last) / (1 - last)
            if not 0.02 < lt < 0.98:
                continue
            a, rest = _split_cubic(rest, lt)
            out.append(a); last = t
        out.append(rest)
    # make handles at extrema exactly axis-aligned
    n = len(out)
    for i in range(n):
        cur, nxt = out[i], out[(i + 1) % n]
        p = cur[3]
        hin, hout = cur[2] - p, nxt[1] - p
        if np.linalg.norm(hin) < 1e-9 or np.linalg.norm(hout) < 1e-9:
            continue
        # smooth join only (not a corner)
        cosang = -np.dot(hin, hout) / (np.linalg.norm(hin) * np.linalg.norm(hout))
        if cosang < 0.985:
            continue
        for axis in (0, 1):
            if abs(hin[axis]) < 0.08 * np.linalg.norm(hin) and abs(hout[axis]) < 0.08 * np.linalg.norm(hout):
                cur[2][axis] = p[axis]; nxt[1][axis] = p[axis]
    return out


def is_line(c, tol):
    p0, p1, p2, p3 = c
    d = p3 - p0
    L = np.linalg.norm(d)
    if L < 1e-9:
        return True
    nrm = np.array([-d[1], d[0]]) / L
    return abs(np.dot(p1 - p0, nrm)) < tol and abs(np.dot(p2 - p0, nrm)) < tol


# ---------------------------------------------------------------- top level
def contour_to_curves(P, ds=0.2, corner_win=0.8, corner_deg=38.0, sigma=0.7, tol=0.12):
    """P: closed polyline (N,2) in source px. Returns list of cubic control arrays (4,2)."""
    P = resample_closed(np.asarray(P, float), ds)
    n = len(P)
    k = max(2, int(round(corner_win / ds)))
    corners, _ = find_corners(P, k, corner_deg)
    sig = sigma / ds
    curves = []
    if not corners:
        sm = gaussian_filter1d(P, sig, axis=0, mode='wrap')
        # split the loop at its extreme left/right/top/bottom points for stable fitting
        cut = sorted(set([int(np.argmin(sm[:, 0])), int(np.argmax(sm[:, 0])),
                          int(np.argmin(sm[:, 1])), int(np.argmax(sm[:, 1]))]))
        cut = [c for i, c in enumerate(cut) if i == 0 or c - cut[i - 1] > 3]
        if len(cut) < 2:
            cut = [0, n // 2]
        for i, a in enumerate(cut):
            b = cut[(i + 1) % len(cut)]
            seg = sm[a:b + 1] if b > a else np.vstack([sm[a:], sm[:b + 1]])
            ta = _unit(sm[(a + 1) % n] - sm[(a - 1) % n])
            tb = _unit(sm[(b - 1) % n] - sm[(b + 1) % n])
            curves += fit_cubics(seg, ta, tb, tol)
    else:
        m = len(corners)
        for i in range(m):
            a, b = corners[i], corners[(i + 1) % m]
            seg = P[a:b + 1] if b > a else np.vstack([P[a:], P[:b + 1]])
            if m == 1:
                seg = np.vstack([P[a:], P[:a + 1]])
            seg = smooth_open(seg, sig)
            if len(seg) < 3:
                curves.append(np.array([seg[0], seg[0] + (seg[-1] - seg[0]) / 3, seg[0] + 2 * (seg[-1] - seg[0]) / 3, seg[-1]]))
                continue
            t1, t2 = end_tangents(seg, k)
            curves += fit_cubics(seg, t1, t2, tol)
    return add_extrema(curves)


def curves_to_recording(contours, line_tol=0.04):
    rec = []
    for curves in contours:
        if not curves:
            continue
        rec.append(('moveTo', (tuple(curves[0][0]),)))
        for c in curves:
            if is_line(c, line_tol):
                rec.append(('lineTo', (tuple(c[3]),)))
            else:
                rec.append(('curveTo', (tuple(c[1]), tuple(c[2]), tuple(c[3]))))
        rec.append(('closePath', ()))
    return rec
