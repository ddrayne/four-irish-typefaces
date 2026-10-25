"""Repeated impressions of one letter on a production sheet, registered and averaged.

A Letraset sheet prints each letter many times from the same artwork. Every impression carries
its own print and photographic noise (and the photograph its own local perspective), so no single
one is better evidence than another; registered onto a common frame and averaged, the noise falls
as the square root of their number and the artwork's edge comes through. The repeats are the same
artwork, not independent drawings: averaging them sharpens the evidence of that artwork, it does
not confirm it.

The common frame is the face's current trace (research round coordinates, scan pixels y down).
Each impression is mapped onto it by its own affine transform (absorbing the photograph's
perspective and the sheet's curl at that spot), so the result keeps the current trace's placement
and proportions and takes its edge from the impressions.

Pure functions over arrays; scripts/trace_production.py runs them over a sheet and writes a round.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import least_squares


def ink_map(channel, light_ink, letter_px):
    """Ink probability 0..1 from one image channel, normalising uneven light: the backing level is
    the local median of the backing, the ink level the local median of the ink."""
    v = channel.astype(float)
    if light_ink:
        v = 255 - v
    # backing: a closing removes the (dark) letters; ink: an opening removes the backing
    big = int(letter_px * 1.5) | 1
    backing = ndi.median_filter(ndi.grey_closing(v, size=(big, big)), size=31)
    ink = ndi.median_filter(ndi.grey_opening(v, size=(max(3, letter_px // 12) | 1,) * 2), size=31)
    ink = np.minimum(ink, backing - 20)
    ink = ndi.grey_erosion(ink, size=(big, big))          # the ink level is that of the darkest nearby ink
    return np.clip((backing - v) / np.maximum(backing - ink, 1), 0, 1)


def components(p, min_area, max_area, thr=0.5):
    """Connected letters (and their bounding boxes) in an ink map."""
    lab, n = ndi.label(p > thr)
    out = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        if sl is None:
            continue
        area = int((lab[sl] == k).sum())
        if min_area <= area <= max_area:
            out.append(dict(label=k, box=[sl[1].start, sl[0].start, sl[1].stop, sl[0].stop], area=area))
    return out, lab


def affine_matrix(q):
    """q = (a, b, c, d, tx, ty): maps template (x, y) to sheet (a x + b y + tx, c x + d y + ty)."""
    a, b, c, d, tx, ty = q
    return np.array([[a, b, tx], [c, d, ty]], float)


def warp(img, q, shape, origin, step):
    """Sample `img` (sheet pixels) on the template grid: grid pixel (i, j) is template point
    origin + step * (j, i); the affine q maps it into the sheet."""
    H, W = shape
    jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    x = origin[0] + step * (jj + 0.5); y = origin[1] + step * (ii + 0.5)
    M = affine_matrix(q)
    sx = M[0, 0] * x + M[0, 1] * y + M[0, 2]; sy = M[1, 0] * x + M[1, 1] * y + M[1, 2]
    return ndi.map_coordinates(img, [sy - 0.5, sx - 0.5], order=1, mode='constant', cval=0.0)


def _shift_search(sheet_p, template, origin, step, q, reach, blur):
    """Best whole-pixel translation of q within +-reach sheet pixels, by correlation of blurred maps."""
    T = ndi.gaussian_filter(template, blur / step); T = T - T.mean()
    S = ndi.gaussian_filter(sheet_p, blur)
    best = (-np.inf, 0, 0)
    for dy in range(-reach, reach + 1, 2):
        for dx in range(-reach, reach + 1, 2):
            w = warp(S, np.r_[q[:4], q[4] + dx, q[5] + dy], T.shape, origin, step)
            v = float((w * T).sum())
            if v > best[0]:
                best = (v, dx, dy)
    return np.r_[q[:4], q[4] + best[1], q[5] + best[2]]


def _crop(sheet_p, template, origin, step, q, margin):
    """The part of the sheet the template's frame maps onto (plus a margin), and q in its pixels."""
    H, W = template.shape
    corners = np.array([[origin[0], origin[1]], [origin[0] + W * step, origin[1]],
                        [origin[0], origin[1] + H * step], [origin[0] + W * step, origin[1] + H * step]])
    M = affine_matrix(q)
    sx = M[0, 0] * corners[:, 0] + M[0, 1] * corners[:, 1] + M[0, 2]
    sy = M[1, 0] * corners[:, 0] + M[1, 1] * corners[:, 1] + M[1, 2]
    x0 = max(0, int(sx.min()) - margin); y0 = max(0, int(sy.min()) - margin)
    x1 = min(sheet_p.shape[1], int(sx.max()) + margin); y1 = min(sheet_p.shape[0], int(sy.max()) + margin)
    return sheet_p[y0:y1, x0:x1], np.r_[q[:4], q[4] - x0, q[5] - y0], (x0, y0)


def register(sheet_p, template, origin, step, q0, blur=1.0, reach=0, levels=(6.0, 3.0, 1.0)):
    """The affine q that best lays the impression onto the template (least squares on blurred maps,
    coarse then fine), after an optional correlation search for the translation. Works on the patch
    of the sheet around the impression."""
    sheet_p, q, (cx, cy) = _crop(sheet_p, template, origin, step, np.array(q0, float), 40 + reach)
    q = _register(sheet_p, template, origin, step, q, blur, reach, levels)
    r = warp(sheet_p, q, template.shape, origin, step) - template
    return np.r_[q[:4], q[4] + cx, q[5] + cy], float(np.sqrt((r ** 2).mean()))


def _register(sheet_p, template, origin, step, q, blur, reach, levels=(6.0, 3.0, 1.0)):
    q = np.array(q, float)
    if reach:
        q = _shift_search(sheet_p, template, origin, step, q, reach, 4.0 * blur)
    H, W = template.shape
    jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    x = (origin[0] + step * (jj + 0.5)).ravel(); y = (origin[1] + step * (ii + 0.5)).ravel()
    for b in (blur * f for f in levels):
        T = ndi.gaussian_filter(template, b / step).ravel()
        S = ndi.gaussian_filter(sheet_p, b)
        gy, gx = np.gradient(S)
        def at(img, q):
            sx = q[0] * x + q[1] * y + q[4]; sy = q[2] * x + q[3] * y + q[5]
            return ndi.map_coordinates(img, [sy - 0.5, sx - 0.5], order=1, mode='constant', cval=0.0)
        res = lambda q: at(S, q) - T
        def jac(q):
            Gx, Gy = at(gx, q), at(gy, q)
            return np.column_stack([Gx * x, Gx * y, Gy * x, Gy * y, Gx, Gy])
        q = least_squares(res, q, jac=jac, x_scale=[0.02, 0.02, 0.02, 0.02, 1.0, 1.0], max_nfev=60).x
    return q


def rotation(a):
    """Rotation through a radians, in y-down coordinates (positive turns the x axis towards +y)."""
    return np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])


def sheet_frame(qs, mark_angles):
    """The letter's frame on its own sheet. Registered onto another print's trace, every impression's
    affine also takes in that print's differences of slant and proportion; those are common to all of
    a letter's impressions, while the photograph's local distortions differ from one to the next. So
    the mean of the linear parts is split into a rotation and a stretch (polar decomposition), the
    stretch's shape is removed (its scale kept), and the letter is turned square to its row's mark
    lines: by the median, over its impressions that have one (an angle of None has none), of each
    fit's own rotation less its mark line's angle.
    Returns the template-side map G (each q becomes q composed with G about the template's centre:
    the impressions stay registered on one another) and what it removed."""
    L = np.array([[[q[0], q[1]], [q[2], q[3]]] for q in qs])
    W, S, Vt = np.linalg.svd(L.mean(0))
    stretch = Vt.T @ np.diag(S / np.sqrt(S.prod())) @ Vt               # symmetric, unit determinant
    turn = np.arctan2(L[:, 1, 0] - L[:, 0, 1], L[:, 0, 0] + L[:, 1, 1])
    have = [i for i, a in enumerate(mark_angles) if a is not None]
    off = float(np.median([turn[i] - mark_angles[i] for i in have]))
    to_sheet = rotation(off) @ stretch                                  # template -> the sheet's geometry
    shear = np.degrees(np.arctan2(to_sheet[1, 0], to_sheet[0, 0]) - np.arctan2(-to_sheet[0, 1], to_sheet[1, 1]))
    return np.linalg.inv(to_sheet), dict(turn_deg=round(np.degrees(off), 3), stretch_ratio=round(float(S[0] / S[1]), 4),
                                         shear_removed_deg=round(float(shear), 3))


def compose(q, G, centre):
    """q applied after the template-side linear map G about `centre` (which still maps where q mapped it)."""
    a, b, c, d, tx, ty = q
    M = np.array([[a, b], [c, d]]); N = M @ G
    t = M @ centre + [tx, ty] - N @ centre
    return np.array([N[0, 0], N[0, 1], N[1, 0], N[1, 1], t[0], t[1]])


def to_template(q, pts):
    """Sheet points mapped back into template units through the affine q."""
    a, b, c, d, tx, ty = q
    return (np.linalg.inv([[a, b], [c, d]]) @ (np.asarray(pts, float) - [tx, ty]).T).T


def average(sheet_p, qs, shape, origin, step):
    """Mean and per-pixel standard deviation of the registered impressions."""
    stack = np.stack([warp(sheet_p, q, shape, origin, step) for q in qs])
    return stack.mean(0), stack.std(0), stack


def normalise_frames(qs, q_ref):
    """Generalised Procrustes step: after re-registering to the mean, the mean of the transforms is
    pinned to that of the registrations to the original template, so iterating never drifts the
    frame (and with it the proportions) away from the current trace."""
    M = [np.vstack([affine_matrix(q), [0, 0, 1]]) for q in qs]
    R = [np.vstack([affine_matrix(q), [0, 0, 1]]) for q in q_ref]
    mean = lambda Ms: np.mean(Ms, axis=0)
    C = mean(R) @ np.linalg.inv(mean(M))
    out = []
    for m in M:
        n = C @ m
        out.append(np.array([n[0, 0], n[0, 1], n[1, 0], n[1, 1], n[0, 2], n[1, 2]]))
    return out


def trace_mask(rec, step, pad):
    """Rasterise one trace record (scan pixels, y down) at `step` trace units per pixel.
    Returns the mask and the grid origin (trace units)."""
    from outline_util import flatten, raster
    pts = [pt for _, args in rec for pt in args]
    x0, y0 = min(p[0] for p in pts) - pad, min(p[1] for p in pts) - pad
    x1, y1 = max(p[0] for p in pts) + pad, max(p[1] for p in pts) + pad
    W, H = int(np.ceil((x1 - x0) / step)), int(np.ceil((y1 - y0) / step))
    m = raster(flatten([(op, [tuple(p) for p in args]) for op, args in rec], 16), (W, H),
               lambda q: ((q[0] - x0) / step, (q[1] - y0) / step))
    return m.astype(float), (x0, y0)


def classify(p, box, templates, pad=4):
    """Name an impression by shape: each template is scaled to the impression's height and
    compared by overlap (IoU) on the impression's box. Returns [(score, name)], best first."""
    from skimage.transform import resize
    x0, y0, x1, y1 = box
    crop = np.pad(p, pad)[y0:y1 + 2 * pad, x0:x1 + 2 * pad] > 0.5      # padded: letters at the photo's edge
    h, w = y1 - y0, x1 - x0
    out = []
    for name, (m, _) in templates.items():
        ys, xs = np.nonzero(m)
        t = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        tw = t.shape[1] * h / t.shape[0]
        if not 0.75 < tw / w < 1.33:
            continue
        t = resize(t, (h, w), order=1, anti_aliasing=True) > 0.5
        c = crop[pad:pad + h, pad:pad + w]
        out.append((float((t & c).sum() / max((t | c).sum(), 1)), name))
    return sorted(out, reverse=True)
