"""Ink-gain model of the prints: what stem weight was Céilí drawn at?

usage: python scripts/print_model.py [--specimens build/research/original-specimens] [--refit] [--jobs 3]

Céilí has no production sheet; its release is drawn from two prints (N46, a photocopied leaflet, and
N45, an offset brochure) whose stems differ by about a tenth.  A print is the drawing with every edge
moved by the print's gain.  This script measures that gain and takes it off.

The model.  A glyph of a reference outline (a release font, used only as a shape) is laid on the print
at s pixels per font unit, rotated and shifted; every edge is moved outwards by d pixels; the result
is blurred by a Gaussian and compared with the print's ink map between its local paper and local ink.
s, the place, d and the blur are fitted together.  Scale and gain do not trade against each other:
a gain moves opposite edges apart, a scale moves centre-lines.  Straight stems are also measured
directly, on profiles across them at the 40, 50 and 60% levels.

1. Control faces.  Kilfane and Carrick are known from photographs of their Letraset sheets (N517,
   N514).  The sheets' edge against the release outline (font units) is measured first; the same
   letters on N46 and N45 then give each print's gain in pixels.
2. That gain is removed from Céilí (and Tuam Uncial) on the same print.
3. Several sizes on one print: offset_px = gain_px + (drawn - release) * px_per_font_unit, fitted on
   the leaflet's alphabet and its two sheet samples; on Kilfane and Carrick the answer is known.
4. Black against white: stems grow, the gaps between them shrink, same-facing edges stay put.
5. The captions (one type across each page) test whether the gain is the same across the page.

Reads the archive scans from --specimens.  Writes numbers only to research/print-model/results.json.
Everything that holds scan pixels (ink maps, per-glyph fits' boards) is written under ignored
build/print-model/ and nowhere else (research/RIGHTS.md).  The fits are cached per glyph in
build/print-model/fits; --refit measures everything again (about 20 minutes on four cores).
Deterministic: no random numbers but the fixed-seed bootstrap of the medians.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parent.parent
RES = 2.0            # reference raster: pixels per font unit
SS = 2               # model supersampling per print pixel


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------ reference shapes
class Ref:
    """A glyph outline as a signed distance field in font units (positive inside the ink).
    Coordinates: x right, y DOWN from the baseline (so they map to image pixels without a flip)."""
    def __init__(self, sdf, x0, y0, res=RES):
        self.sdf, self.x0, self.y0, self.res = sdf, x0, y0, res      # sdf[i, j] at (x0 + j/res, y0 + i/res)

    @classmethod
    def from_mask(cls, mask, x0, y0, res=RES):
        din = ndi.distance_transform_edt(mask); dout = ndi.distance_transform_edt(~mask)
        return cls(((din - 0.5) * mask - (dout - 0.5) * ~mask) / res, x0, y0, res)

    @classmethod
    def from_font(cls, face, name, pad=120):
        import freetype
        from fontTools.ttLib import TTFont
        key = str(face)
        if key not in _FONTS:
            _FONTS[key] = (freetype.Face(key), TTFont(key))
        ft, tt = _FONTS[key]
        upm = tt['head'].unitsPerEm
        ft.set_pixel_sizes(0, int(round(upm * RES)))
        ft.load_glyph(tt.getGlyphID(name), freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_RENDER)
        bm = ft.glyph.bitmap
        a = np.array(bm.buffer, np.uint8).reshape(bm.rows, bm.pitch)[:, :bm.width] >= 128
        p = int(pad * RES)
        m = np.zeros((a.shape[0] + 2 * p, a.shape[1] + 2 * p), bool); m[p:-p, p:-p] = a
        return cls.from_mask(m, ft.glyph.bitmap_left / RES - pad, -ft.glyph.bitmap_top / RES - pad)

    @property
    def mask(self):
        return self.sdf > 0

    def thickness(self, step=2.0):
        """Local stroke thickness in font units at every raster point: inside the ink, the diameter
        of the largest disc inside the ink that covers the point; outside, that of the nearest ink."""
        if getattr(self, '_T', None) is None:
            sd = self.sdf[::2, ::2]; res = self.res / 2          # at half resolution: fast enough
            T = np.zeros(sd.shape)
            for r in np.arange(step, sd.max() + step, step):
                core = sd >= min(r, sd.max())
                T[ndi.distance_transform_edt(~core) <= min(r, sd.max()) * res + 1.5] = 2 * min(r, sd.max())   # reaches the edge
            inside = sd > 0
            T[inside & (T == 0)] = step
            T[~inside] = 0
            idx = ndi.distance_transform_edt(~inside, return_distances=False, return_indices=True)
            T = T[idx[0], idx[1]]
            self._T = np.repeat(np.repeat(T, 2, 0), 2, 1)[:self.sdf.shape[0], :self.sdf.shape[1]]
        return self._T

    def thin(self, u, v, lo, hi):
        """1 where the stroke is at most `lo` font units thick, 0 where at least `hi`, linear between."""
        T = ndi.map_coordinates(self.thickness(), [(v - self.y0) * self.res, (u - self.x0) * self.res], order=1, mode='nearest')
        return np.clip((hi - T) / (hi - lo), 0, 1)

    def bbox(self):
        ii, jj = np.nonzero(self.mask)
        return (self.x0 + jj.min() / self.res, self.y0 + ii.min() / self.res,
                self.x0 + (jj.max() + 1) / self.res, self.y0 + (ii.max() + 1) / self.res)

    def at(self, u, v):
        return ndi.map_coordinates(self.sdf, [(v - self.y0) * self.res, (u - self.x0) * self.res], order=1, mode='nearest')


_FONTS = {}


# ------------------------------------------------------------------ the forward model
def _uv(shape, ss, s, rot, tx, ty, aspect=1.0, shear=0.0):
    H, W = shape
    jj, ii = np.meshgrid((np.arange(W * ss) + 0.5) / ss, (np.arange(H * ss) + 0.5) / ss)
    c, n = np.cos(rot), np.sin(rot)
    x, y = jj - tx, ii - ty
    v = (-n * x + c * y) / (s * aspect)
    return (c * x + n * y) / s - shear * v, v


def render(ref, shape, s, rot, tx, ty, d, sigma, e=0.0, aspect=1.0, shear=0.0, ss=SS, thin=None):
    """The print the model predicts: the reference at `s` pixels per font unit, rotated by `rot`
    radians, its origin at pixel (tx, ty), every edge moved outwards by `d` pixels (by d + e where
    the stroke is thin: thin = (lo, hi) font units), blurred by a Gaussian of `sigma` pixels and
    integrated over each pixel.  0 paper .. 1 ink.  Pixel (i, j) covers [j, j+1) x [i, i+1).
    aspect and shear (photographs of sheets only) stretch y and slant the letter."""
    H, W = shape
    u, v = _uv(shape, ss, s, rot, tx, ty, aspect, shear)
    off = d + (e * ref.thin(u, v, *thin) if (thin is not None and e != 0.0) else 0.0)
    cov = np.clip((ref.at(u, v) * s + off) * ss + 0.5, 0, 1)
    if sigma > 0:
        cov = ndi.gaussian_filter(cov, sigma * ss, mode='nearest')
    return cov.reshape(H, ss, W, ss).mean((1, 3))


PARAMS = ('s', 'rot', 'tx', 'ty', 'd', 'sigma', 'e', 'aspect', 'shear')


def fit_gain(ink, ref, p0, weight=None, thin=None, affine=False, fix=None, rounds=2, band=4.0):
    """Least-squares fit of the forward model to a print's ink map.  p0 = (s, rot, tx, ty[, d, sigma]).
    Scale and gain are separable because a gain moves opposite edges apart while a scale moves
    centre-lines: outer contours and counters pull d in opposite directions for a wrong scale.
    thin=(lo, hi) frees a second gain for thin strokes; affine frees aspect and shear; fix={name: value}."""
    p = np.array(list(p0) + [0.0, 1.0][len(p0) - 4:] + [0.0, 1.0, 0.0], float)
    xs = np.array([0.01 * p[0], 0.01, 0.5, 0.5, 0.3, 0.3, 0.3, 0.01, 0.01])
    lo = np.array([0.8 * p[0], -0.15, -np.inf, -np.inf, -6, 0.15, -4, 0.9, -0.15])
    hi = np.array([1.25 * p[0], 0.15, np.inf, np.inf, 6, 4.0, 4, 1.1, 0.15])
    free = np.ones(9, bool)
    if thin is None:
        free[6] = False
    if not affine:
        free[7:] = False
    for k, v in (fix or {}).items():
        p[PARAMS.index(k)] = v; free[PARAMS.index(k)] = False
    w = np.ones(ink.shape) if weight is None else weight.astype(float)
    def full(q):
        z = p.copy(); z[free] = q
        return z
    def model(z):
        return render(ref, ink.shape, *z, thin=thin)
    for _ in range(rounds):
        # only pixels near the model's edge carry information; ink far outside belongs to neighbours
        u, v = _uv(ink.shape, 1, p[0], p[1], p[2], p[3], p[7], p[8])
        near = np.abs(ref.at(u, v) * p[0] + p[4]) < band + 2 * p[5]
        ww = w * near
        r = least_squares(lambda q: (ww * (model(full(q)) - ink)).ravel(), np.clip(p[free], lo[free], hi[free]),
                          bounds=(lo[free], hi[free]), x_scale=xs[free], diff_step=1e-3 * np.ones(int(free.sum())),
                          loss='soft_l1', f_scale=0.25, max_nfev=40, xtol=1e-5, ftol=1e-7)
        p = full(r.x)
    n = max(int((ww > 0).sum()), 1)
    rms = float(np.sqrt((((model(p) - ink) * (ww > 0)) ** 2).sum() / n))
    out = {k: float(x) for k, x in zip(PARAMS, p)}
    out.update(rms=rms, n=n)
    return out


# ------------------------------------------------------------------ prints
SPEC = ROOT / 'build' / 'research' / 'original-specimens'
OUT = ROOT / 'build' / 'print-model'
FONT = {f: ROOT / 'fonts' / 'otf' / f'{n}Digital-Regular.otf' for f, n in
        (('ceili', 'Ceili'), ('kilfane', 'Kilfane'), ('carrick', 'Carrick'), ('tuam', 'TuamUncial'))}
FILES = {'N46': 'competition-advert-1.jpg', 'N45': 'competition-brochure-2.jpg', 'N44': 'competition-brochure-1.jpg',
         'N517': 'Kilfane-Letraset.jpg', 'N514': 'Carrick-Letraset.jpg'}


def levels(g):
    """Paper and ink grey levels of a flat scan window: the paper is the median of the lighter
    pixels; the ink the median of pixels at least two pixels inside solid ink."""
    mid = (np.percentile(g, 1) + np.percentile(g, 90)) / 2
    paper = float(np.median(g[g > mid]))
    core = ndi.binary_erosion(g < mid, iterations=2)
    ink = float(np.median(g[core])) if core.sum() > 50 else float(np.percentile(g, 2))
    return paper, ink


def locate(ink, ref, scales, k=1, sigma=1.0, min_sep=None):
    """Where a glyph is in an ink map: normalised cross-correlation of the rendered reference over a
    range of scales.  Returns up to k peaks as (score, s, tx, ty) with (tx, ty) the glyph origin."""
    from skimage.feature import match_template
    x0, y0, x1, y1 = ref.bbox()
    out = []
    for s in scales:
        m = 3
        W, H = int(np.ceil((x1 - x0) * s)) + 2 * m, int(np.ceil((y1 - y0) * s)) + 2 * m
        if H >= ink.shape[0] or W >= ink.shape[1]:
            continue
        t = render(ref, (H, W), s, 0.0, m - x0 * s, m - y0 * s, 0.0, sigma, ss=2)
        r = match_template(ink, t)
        sep = int(min_sep or 0.6 * min(H, W))
        mx = ndi.maximum_filter(r, size=sep)
        for i, j in zip(*np.nonzero((r == mx) & (r > 0.3))):
            out.append((float(r[i, j]), float(s), float(j + m - x0 * s), float(i + m - y0 * s), W, H))
    out.sort(reverse=True)
    keep = []
    for o in out:
        if all(abs(o[2] - q[2]) > 0.5 * o[4] or abs(o[3] - q[3]) > 0.5 * o[5] for q in keep):
            keep.append(o)
        if len(keep) == k:
            break
    return [o[:4] for o in keep]


THIN = {'ceili': (52, 84), 'kilfane': (64, 102), 'carrick': (94, 150), 'tuam': (108, 173)}   # 0.5 and 0.8 of the stem
# Blocks: (source, face, block name, window x0 y0 x1 y1, rough pixels per font unit, glyphs).  The
# windows were read off the scans by eye; every glyph in them is then found by correlation.
KILFANE_CAPS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'K', 'L', 'M', 'N', 'O', 'P', 'R']
CARRICK_LC = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o']
BLOCKS = [
    ('N46', 'kilfane', 'alphabet', (140, 300, 1080, 560), 0.117, KILFANE_CAPS),
    ('N46', 'kilfane', 'S53909 30pt', (300, 1095, 400, 1210), 0.105, ['A']),
    ('N46', 'kilfane', 'S53910 48pt', (620, 1035, 790, 1215), 0.17, ['A']),
    ('N46', 'carrick', 'alphabet', (140, 1400, 1080, 1700), 0.129, CARRICK_LC),
    ('N46', 'carrick', 'S53913 36pt', (300, 1960, 400, 2070), 0.125, ['a']),
    ('N46', 'carrick', 'S53914 60pt', (615, 1930, 780, 2070), 0.21, ['a']),
    ('N46', 'tuam', 'S53911 30pt', (1280, 1010, 1450, 1125), 0.105, ['a', 'one']),
    ('N46', 'tuam', 'S53912 48pt', (1655, 960, 1915, 1125), 0.17, ['a', 'one']),
    ('N45', 'carrick', 'alphabet', (1560, 330, 2260, 660), 0.11, CARRICK_LC),
    ('N45', 'kilfane', 'alphabet', (1560, 910, 2260, 1130), 0.113, KILFANE_CAPS),
]
SHEET_BLOCKS = [   # the photographed production sheets: (source, face, sheet, channel, light ink, letter px, k per glyph)
    ('N517', 'kilfane', '30pt S53909', 1, False, 75, KILFANE_CAPS),
    ('N517', 'kilfane', '48pt S53910', 0, True, 120, KILFANE_CAPS),
    ('N514', 'carrick', '36pt S53913', 1, False, 60, CARRICK_LC),
    ('N514', 'carrick', '60pt S53914', 1, False, 100, CARRICK_LC),
]
_IMG = {}


def gray(src, specimens=SPEC):
    if src not in _IMG:
        from PIL import Image
        _IMG[src] = np.asarray(Image.open(Path(specimens) / FILES[src]).convert('L')).astype(float)
    return _IMG[src]


def ink_window(src, box, specimens=SPEC, pad=40):
    """A flat scan's ink map (0 paper .. 1 ink) in a box grown by pad; levels from the grown box."""
    g = gray(src, specimens)
    x0, y0 = max(0, box[0] - pad), max(0, box[1] - pad); x1, y1 = min(g.shape[1], box[2] + pad), min(g.shape[0], box[3] + pad)
    w = g[y0:y1, x0:x1]
    paper, ink = PRINT_LEVELS.get(src) or levels(w)
    return np.clip((paper - w) / (paper - ink), -0.2, 1.2), (x0, y0), (paper, ink)


PRINT_LEVELS = {}


def print_levels(specimens=SPEC):
    """One paper and one ink level per print, from its heaviest face (Carrick; the heading for N44):
    ink density belongs to the print, not to the letter, and a thin stroke never shows it."""
    for src, box in (('N46', (140, 1400, 1080, 1860)), ('N45', (1560, 330, 2260, 890)), ('N44', (1530, 330, 2970, 670))):
        g = gray(src, specimens)
        PRINT_LEVELS[src] = levels(g[box[1]:box[3], box[0]:box[2]])
    PRINT_LEVELS['N44'] = (PRINT_LEVELS['N44'][0], PRINT_LEVELS['N45'][1] - PRINT_LEVELS['N45'][0] + PRINT_LEVELS['N44'][0])
    return PRINT_LEVELS


def relevel(patch, ref, q, inside=3.0):
    """The patch between its own paper (0) and its own ink (1): the paper is the median well outside
    the fitted letter, the ink the median at least `inside` pixels inside it (kept at 1 where the
    letter has no such core).  Returns the patch and the two levels in the old units."""
    u, v = _uv(patch.shape, 1, q['s'], q['rot'], q['tx'], q['ty'], q['aspect'], q['shear'])
    sd = ref.at(u, v) * q['s'] + q['d']
    out = sd < -(3.0 + 2 * q['sigma']); core = sd > inside + q['sigma']
    paper = float(np.median(patch[out])) if out.sum() > 30 else 0.0
    ink = float(np.median(patch[core])) if core.sum() >= 20 else 1.0
    if ink - paper < 0.4:
        paper, ink = 0.0, 1.0
    return (patch - paper) / (ink - paper), paper, ink


def at_level(patch, level):
    """The ink map rescaled so that its `level` becomes the model's half level (clipped at full ink)."""
    return np.clip(patch * 0.5 / level, 0, 1)


def measure(ink, origin, ref, face, start, affine=False, thin=True, sigma0=1.0, levels_=(0.4, 0.6), stems_=True):
    """Fit one located glyph.  start = (s, tx, ty) in the window's pixels.  Returns the fits with the
    glyph origin in image pixels, the patch box, the stems' widths and the releveled patch."""
    s, tx, ty = start
    bx0, by0, bx1, by1 = ref.bbox(); m = 8
    X0, Y0 = int(np.floor(tx + bx0 * s)) - m, int(np.floor(ty + by0 * s)) - m
    X1, Y1 = int(np.ceil(tx + bx1 * s)) + m, int(np.ceil(ty + by1 * s)) + m
    X0, Y0 = max(X0, 0), max(Y0, 0); X1, Y1 = min(X1, ink.shape[1]), min(Y1, ink.shape[0])
    raw = ink[Y0:Y1, X0:X1]
    core = ('s', 'rot', 'tx', 'ty', 'd', 'sigma')
    f0 = fit_gain(np.clip(raw, 0, 1), ref, (s, 0.0, tx - X0, ty - Y0, 0.0, sigma0), affine=affine, rounds=1)
    patch, paper, inkl = relevel(raw, ref, f0)
    fx = dict(aspect=f0['aspect'], shear=f0['shear'])
    f = fit_gain(at_level(patch, 0.5), ref, [f0[k] for k in core], affine=affine, fix=None if affine else fx, rounds=2)
    out = dict(single=dict(f), local_paper=paper, local_ink=inkl)
    fx = dict(aspect=f['aspect'], shear=f['shear'])
    for L in levels_:
        g = fit_gain(at_level(patch, L), ref, [f[k] for k in core], fix=fx, rounds=1)
        out[f'level{int(round(100 * L))}'] = dict(d=g['d'], s=g['s'], sigma=g['sigma'])
    if thin:
        g = fit_gain(at_level(patch, 0.5), ref, [f[k] for k in core], thin=THIN[face], fix=fx, rounds=1)
        u, v = _uv(patch.shape, 1, g['s'], g['rot'], g['tx'], g['ty'], g['aspect'], g['shear'])
        edge = np.abs(ref.at(u, v) * g['s']) < 1.0
        g['thin_fraction'] = float(ref.thin(u, v, *THIN[face])[edge].mean()) if edge.any() else 0.0
        out['two'] = g
    if stems_:
        out['stems'] = measure_stems(patch, ref, f)
    for k in ('single', 'two'):
        if k in out:
            out[k]['tx'] += X0 + origin[0]; out[k]['ty'] += Y0 + origin[1]
    out['box'] = [X0 + origin[0], Y0 + origin[1], X1 + origin[0], Y1 + origin[1]]
    return out, patch


# ------------------------------------------------------------------ stems, measured on profiles
def find_stems(mask, res=RES, step=4.0, min_len=120.0, tol=2.0):
    """Straight, near-vertical stems of a glyph raster: chains of horizontal ink runs whose two edges
    stay on straight lines (within `tol` font units) for at least `min_len`.  Returns, in raster
    font units (x right, y down, origin at the raster's corner), a list of
    dict(v0, v1, left=(slope, intercept), right=(slope, intercept), width)."""
    k = max(1, int(round(step * res)))
    rows = np.arange(0, mask.shape[0], k)
    chains, open_ = [], []
    for i in rows:
        r = np.flatnonzero(np.diff(np.r_[0, mask[i].astype(np.int8), 0]))
        runs = [(a / res, b / res) for a, b in zip(r[::2], r[1::2])]
        nxt = []
        for a, b in runs:
            for c in open_:
                if c['v'][-1] == (i - k) / res and abs(c['a'][-1] - a) <= 0.3 * step and abs(c['b'][-1] - b) <= 0.3 * step:
                    c['v'].append(i / res); c['a'].append(a); c['b'].append(b); nxt.append(c); break
            else:
                c = dict(v=[i / res], a=[a], b=[b]); chains.append(c); nxt.append(c)
        open_ = nxt
    out = []
    for c in chains:
        v, a, b = (np.array(c[x]) for x in 'vab')
        for trim in (0.15, 0.25, 0.33):
            n = len(v); lo, hi = int(n * trim), n - int(n * trim)
            if hi - lo < 4 or v[hi - 1] - v[lo] < min_len:
                break
            V, A, B = v[lo:hi], a[lo:hi], b[lo:hi]
            pa, pb = np.polyfit(V, A, 1), np.polyfit(V, B, 1)
            if (np.abs(np.polyval(pa, V) - A).max() <= tol and np.abs(np.polyval(pb, V) - B).max() <= tol
                    and abs(pa[0]) < 0.2 and abs(pa[0] - pb[0]) < 0.03):
                out.append(dict(v0=float(V[0]), v1=float(V[-1]), left=[float(x) for x in pa], right=[float(x) for x in pb],
                                width=float((B - A).mean())))
                break
    return sorted(out, key=lambda t: t['left'][1] + t['left'][0] * t['v0'])


def crossing(x, y, level, rising, near):
    """Sub-sample position where the profile y(x) crosses `level` (rising or falling), nearest `near`."""
    d = y - level
    idx = np.flatnonzero((d[:-1] < 0) & (d[1:] >= 0)) if rising else np.flatnonzero((d[:-1] >= 0) & (d[1:] < 0))
    if not len(idx):
        return np.nan
    pos = x[idx] + (x[idx + 1] - x[idx]) * (level - y[idx]) / (y[idx + 1] - y[idx])
    return float(pos[np.argmin(np.abs(pos - near))])


def stem_profile(patch, q, x0, y0, stem, pad_px=6.0, du_px=0.1, blocks=6):
    """Mean ink profiles across a stem, in `blocks` groups of rows along it.  (x0, y0) is the raster
    origin of the stem's coordinates in font units.  Returns u (font units, raster frame) and the
    block profiles."""
    s = q['s']; c, n = np.cos(q['rot']), np.sin(q['rot'])
    vs = np.arange(stem['v0'], stem['v1'], 0.5 / s)
    mid = (stem['v0'] + stem['v1']) / 2
    lo = np.polyval(stem['left'], mid) - pad_px / s; hi = np.polyval(stem['right'], mid) + pad_px / s
    rel = np.arange(lo, hi, du_px / s)
    slope = (stem['left'][0] + stem['right'][0]) / 2
    U = rel[None, :] + slope * (vs[:, None] - mid) + x0; V = vs[:, None] + y0 + 0 * rel[None, :]
    Us = U + q['shear'] * V; Vs = V * q['aspect']
    X = s * (c * Us - n * Vs) + q['tx']; Y = s * (n * Us + c * Vs) + q['ty']
    P = ndi.map_coordinates(patch, [Y - 0.5, X - 0.5], order=1, mode='nearest')
    groups = np.array_split(np.arange(len(vs)), min(blocks, max(1, len(vs) // 3)))
    return rel, np.array([P[g].mean(0) for g in groups])


def measure_stems(patch, ref, q, levels_=(0.4, 0.5, 0.6)):
    """Each straight stem's width on the print at three levels, against the reference's (pixels).
    half_gain = (print width - reference width) / 2; `left`/`right` are the edges' places in the
    reference's font units, so distances between same-facing edges test the fitted scale."""
    out = []
    for st in find_stems(ref.mask, ref.res):
        rel, prof = stem_profile(patch, q, ref.x0, ref.y0, st)
        mid = (st['v0'] + st['v1']) / 2
        xl, xr = np.polyval(st['left'], mid), np.polyval(st['right'], mid)
        rec = dict(v0=st['v0'] + ref.y0, v1=st['v1'] + ref.y0, x_left=xl + ref.x0, x_right=xr + ref.x0, ref_width=st['width'],
                   peak=float(np.median(prof.max(1))), n_blocks=len(prof))
        for L in levels_:
            e = np.array([[crossing(rel, p, L, True, xl), crossing(rel, p, L, False, xr)] for p in prof])
            ok = np.isfinite(e).all(1) & (np.abs(e[:, 0] - xl) < 6 / q['s']) & (np.abs(e[:, 1] - xr) < 6 / q['s'])
            if ok.sum() < 2:
                rec[f'L{int(round(100 * L))}'] = None; continue
            w = (e[ok, 1] - e[ok, 0]) * q['s']
            rec[f'L{int(round(100 * L))}'] = dict(width_px=float(w.mean()), se_px=float(w.std(ddof=1) / np.sqrt(len(w))),
                                                  half_gain_px=float((w.mean() - st['width'] * q['s']) / 2),
                                                  left=float(e[ok, 0].mean() + ref.x0), right=float(e[ok, 1].mean() + ref.x0))
        out.append(rec)
    return out


def board(path, patch, ref, f, face):
    """Print | model | difference, for the eye.  Holds archive pixels: build/ only."""
    from PIL import Image
    assert OUT in Path(path).resolve().parents, 'scan pixels stay under build/print-model'
    x0, y0 = f['box'][:2]; q = f.get('two') or f['single']
    m = render(ref, patch.shape, q['s'], q['rot'], q['tx'] - x0, q['ty'] - y0, q['d'], q['sigma'], q['e'], q['aspect'], q['shear'], thin=THIN[face])
    row = np.hstack([np.clip(patch, 0, 1), m, np.clip(0.5 + (patch - m), 0, 1)])
    im = Image.fromarray((255 * (1 - row)).astype(np.uint8)).resize((row.shape[1] * 3, row.shape[0] * 3), Image.LANCZOS)
    Path(path).parent.mkdir(parents=True, exist_ok=True); im.save(path)


SHEET_WINDOWS = {'30pt S53909': ((0, 1250, 2573, 2573), 0.107), '48pt S53910': ((0, 150, 2573, 1040), 0.172),
                 '36pt S53913': ((0, 1520, 2592, 2592), 0.116), '60pt S53914': ((0, 150, 2592, 1280), 0.193)}


def sheet_ink(src, sheet, channel, light, letter_px, specimens=SPEC):
    """A production sheet's ink map (scripts/impressions.ink_map: local backing and local ink levels,
    since a photograph is unevenly lit), cached under build/print-model."""
    sys.path.insert(0, str(ROOT / 'scripts'))
    import impressions as IM
    from PIL import Image
    cache = OUT / f'sheet-ink-{src}-{sheet.split()[0]}.npy'
    (x0, y0, x1, y1), _ = SHEET_WINDOWS[sheet]
    if cache.exists():
        return np.load(cache).astype(float), (x0, y0)
    im = np.asarray(Image.open(Path(specimens) / FILES[src]))
    p = IM.ink_map(im[y0:y1, x0:x1, channel], light, letter_px)
    OUT.mkdir(parents=True, exist_ok=True); np.save(cache, p.astype(np.float32))
    return p, (x0, y0)


# ------------------------------------------------------------------ collecting the fits
CEILI_REGIONS = ROOT / 'research' / 'ceili-judgement' / 'traces' / 'source-regions.json'
TUAM_REGIONS = ROOT / 'research' / 'tuam-judgement' / 'traces' / 'source-regions.json'
SKIP = {'hyphen', 'parenleft', 'parenright', 'exclam', 'question', 'aacute', 'eacute', 'iacute', 'oacute', 'uacute'}


def tasks():
    """Every glyph to measure: dict(src, face, block, glyph, window, s0 or None, k, sheet)."""
    out = []
    for src, face, block, win, s0, glyphs in BLOCKS:
        for g in glyphs:
            out.append(dict(src=src, face=face, block=block, glyph=g, window=list(win), s0=s0, k=1, n=0))
    reg = json.loads(CEILI_REGIONS.read_text())
    for pid in ('N46', 'N45', 'N44', 'S53915', 'S53916'):
        src = 'N46' if pid.startswith('S') else pid
        for i, e in enumerate(reg[pid]):
            if e['name'] not in SKIP:
                out.append(dict(src=src, face='ceili', block={'N46': 'alphabet', 'N45': 'alphabet', 'N44': 'heading'}.get(pid, pid),
                                glyph=e['name'], region=e['box'], k=1, n=i))
    for src, face, sheet, ch, light, lpx, glyphs in SHEET_BLOCKS:
        for g in glyphs:
            out.append(dict(src=src, face=face, block=sheet, glyph=g, sheet=[ch, light, lpx], s0=SHEET_WINDOWS[sheet][1], k=4, n=0))
    reg = json.loads(TUAM_REGIONS.read_text())
    for pid in ('N46', 'N45'):
        for i, e in enumerate(reg[FILES[pid]]):
            if e['name'] not in SKIP:
                out.append(dict(src=pid, face='tuam', block='alphabet', glyph=e['name'], region=e['box'], k=1, n=i))
    return out


def run_task(t, specimens=SPEC, boards=True):
    ref = Ref.from_font(FONT[t['face']], t['glyph'])
    bx0, by0, bx1, by1 = ref.bbox()
    if 'sheet' in t:
        ink, origin = sheet_ink(t['src'], t['block'], *t['sheet'], specimens=specimens)
        scales = t['s0'] * 1.03 ** np.arange(-3, 4); min_score = 0.85
    elif 'region' in t:
        x0, y0, x1, y1 = t['region']
        ink, origin, _ = ink_window(t['src'], (x0, y0, x1, y1), specimens, pad=14)
        scales = (y1 - y0) / (by1 - by0) * 1.025 ** np.arange(-4, 5); min_score = 0.5
    else:
        ink, origin, _ = ink_window(t['src'], t['window'], specimens, pad=0)
        scales = t['s0'] * 1.03 ** np.arange(-5, 6); min_score = 0.6
    recs = []
    for i, loc in enumerate(locate(np.clip(ink, 0, 1), ref, scales, k=t['k'])):
        if loc[0] < min_score:
            continue
        f, patch = measure(ink, origin, ref, t['face'], loc[1:], affine='sheet' in t)
        f.update(src=t['src'], face=t['face'], block=t['block'], glyph=t['glyph'], n=t['n'] * 10 + i, score=loc[0])
        if boards:
            board(OUT / 'boards' / f"{t['src']}-{t['face']}-{t['block'].replace(' ', '_')}-{t['glyph']}-{f['n']}.png", patch, ref, f, t['face'])
        recs.append(f)
    return recs


def task_key(t):
    return f"{t['src']}-{t['face']}-{t['block'].replace(' ', '_')}-{t['glyph']}-{t['n']}"


def _run(a):
    np.seterr(all='ignore')
    t, specimens = a
    cache = OUT / 'fits' / (task_key(t) + '.json')
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        recs = run_task(t, specimens)
    except Exception as e:                                   # a glyph that cannot be measured is reported, not hidden
        recs = [dict(error=f'{type(e).__name__}: {e}', **{k: t[k] for k in ('src', 'face', 'block', 'glyph')})]
    cache.write_text(json.dumps(recs, default=_json))
    return json.loads(cache.read_text())


def collect(specimens=SPEC, jobs=3, only=None):
    """Measure every glyph (one cache file per glyph under build/print-model/fits, so a stopped run resumes)."""
    from multiprocessing import Pool
    print_levels(specimens)
    (OUT / 'fits').mkdir(parents=True, exist_ok=True)
    ts = [t for t in tasks() if only is None or only(t)]
    for src, face, sheet, ch, light, lpx, _ in SHEET_BLOCKS:   # cache the sheets' ink maps before forking
        if any(t['src'] == src and t['block'] == sheet for t in ts):
            sheet_ink(src, sheet, ch, light, lpx, specimens)
    with Pool(jobs) as pool:
        res = pool.map(_run, [(t, specimens) for t in ts], chunksize=1)
    return [r for rs in res for r in rs]


# ------------------------------------------------------------------ analysis (numbers only)
def line_fit(x, y, se=None):
    """Weighted least squares y = intercept + slope x.  Standard errors from the given se, scaled up
    by the scatter about the line when that is larger (more than two points)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    w = np.ones(len(x)) if se is None else 1 / np.maximum(np.asarray(se, float), 1e-9) ** 2
    A = np.column_stack([np.ones(len(x)), x])
    C = np.linalg.inv(A.T @ (A * w[:, None]))
    b = C @ (A.T @ (w * y))
    r = y - A @ b
    chi = float((w * r * r).sum() / max(len(x) - 2, 1)) if len(x) > 2 else 1.0
    if se is None:
        C = C * chi
    else:
        C = C * max(chi, 1.0)
    return dict(intercept=float(b[0]), slope=float(b[1]), intercept_se=float(np.sqrt(C[0, 0])), slope_se=float(np.sqrt(C[1, 1])),
                cov=float(C[0, 1]), n=int(len(x)), chi2_per_dof=chi)


def centre(v, seed=0, B=2000):
    """Median of a sample with a bootstrap standard error (fixed seed: deterministic)."""
    v = np.asarray([x for x in v if x is not None and np.isfinite(x)], float)
    if len(v) == 0:
        return dict(value=None, se=None, n=0)
    if len(v) == 1:
        return dict(value=float(v[0]), se=None, n=1)
    rng = np.random.default_rng(seed)
    bs = np.median(v[rng.integers(0, len(v), (B, len(v)))], axis=1)
    return dict(value=float(np.median(v)), se=float(bs.std()), n=int(len(v)), sd=float(v.std(ddof=1)))


def rnd(o, k=4):
    if isinstance(o, dict):
        return {a: rnd(b, k) for a, b in o.items()}
    if isinstance(o, (list, tuple)):
        return [rnd(b, k) for b in o]
    if isinstance(o, (float, np.floating)):
        return round(float(o), k)
    if isinstance(o, np.integer):
        return int(o)
    return o


VARIANTS = ('fit', 'fit40', 'fit60', 'thick', 'thin', 'stem', 'stem40', 'stem60')
RELEASE = dict(ceili=dict(stem=108.0, x_height=538.0), tuam=dict(stem=220.0, x_height=544.0))
N46_PX_PER_MM = 2140 / 210.0          # the leaflet is A4 and the scan is the whole page (assumed; checked on the samples)


def values(r):
    """A record's edge offsets against the release outline, in pixels, by variant, and its scale."""
    v = dict(fit=r['single']['d'], fit40=r['level40']['d'], fit60=r['level60']['d'])
    if 'two' in r and r['two'].get('thin_fraction', 0) >= 0.1:
        v['thick'] = r['two']['d']; v['thin'] = r['two']['d'] + r['two']['e']
    for L, key in ((50, 'stem'), (40, 'stem40'), (60, 'stem60')):
        g = [t[f'L{L}']['half_gain_px'] for t in r.get('stems', []) if t.get(f'L{L}')]
        if g:
            v[key] = float(np.mean(g))
    return v, r['single']['s']


def good(recs):
    """Drop fits that failed: an error, a gain or blur at its bound, a poor fit (rms above 0.25 of the
    paper-to-ink range), a scale more than 4% from its block's median (a letter found in the wrong place
    or at the wrong size), or on a sheet a correlation below 0.9 (another letter taken for this one)."""
    recs = [r for r in recs if 'error' not in r]
    by = {}
    for r in recs:
        by.setdefault((r['src'], r['face'], r['block']), []).append(r['single']['s'])
    out, dropped = [], []
    for r in recs:
        q = r['single']; med = np.median(by[(r['src'], r['face'], r['block'])])
        why = ('gain at bound' if abs(q['d']) > 5.5 else 'blur at bound' if q['sigma'] > 3.9 else
               'rms' if q['rms'] > 0.25 else 'scale' if abs(q['s'] / med - 1) > 0.04 else
               'score' if (r['src'] in ('N517', 'N514') and r['score'] < 0.9) else None)
        (dropped.append(dict(src=r['src'], face=r['face'], block=r['block'], glyph=r['glyph'], why=why)) if why else out.append(r))
    return out, dropped


def analyse(recs, levels_=None):
    recs, dropped = good(recs)
    blocks = {}
    for r in recs:
        blocks.setdefault((r['src'], r['face'], r['block']), []).append(r)
    res = dict(dropped=dropped, blocks={})
    for (src, face, block), rs in sorted(blocks.items()):
        res['blocks'][f'{src} {face} {block}'] = dict(
            n=len(rs), px_per_font_unit=centre([r['single']['s'] for r in rs]), blur_sigma_px=centre([r['single']['sigma'] for r in rs]),
            rms=centre([r['single']['rms'] for r in rs]), offset_vs_release_px={k: centre([values(r)[0].get(k) for r in rs]) for k in VARIANTS},
            local_ink=centre([r['local_ink'] for r in rs]))

    # ---- 1. the sheets: how far the artwork's edge lies from the release outline (font units per edge)
    tau, tau_face, sheets = {}, {}, {}
    for face, src in (('kilfane', 'N517'), ('carrick', 'N514')):
        per = {}                                             # (sheet, glyph) -> variant -> median over impressions
        for (s_, f_, block), rs in blocks.items():
            if s_ != src:
                continue
            for g in sorted({r['glyph'] for r in rs}):
                mine = [r for r in rs if r['glyph'] == g]
                per[(block, g)] = dict(s=float(np.median([r['single']['s'] for r in mine])), n=len(mine),
                                       **{k: (float(np.median(x)) if (x := [values(r)[0][k] for r in mine if k in values(r)[0]]) else None) for k in VARIANTS})
        sheets[face] = {}
        for sheet in sorted({b for b, _ in per}):
            sheets[face][sheet] = dict(glyphs=sorted(g for b, g in per if b == sheet), px_per_font_unit=centre([v['s'] for (b, g), v in per.items() if b == sheet]),
                                       offset_px={k: centre([v[k] for (b, g), v in per.items() if b == sheet]) for k in ('fit', 'thick', 'thin', 'stem')},
                                       sheet_minus_release_fu={k: centre([v[k] / v['s'] for (b, g), v in per.items() if b == sheet and v[k] is not None])
                                                               for k in ('fit', 'fit40', 'fit60', 'thick', 'thin', 'stem')})
        # photograph's own edge gain: two sheet sizes in one photograph, d = g_photo + tau * s
        pts = [(v['s'], v['fit']) for v in per.values()]
        sheets[face]['two_sizes'] = line_fit([p[0] for p in pts], [p[1] for p in pts]) if len({b for b, _ in per}) > 1 else None
        if sheets[face]['two_sizes']:
            sheets[face]['two_sizes']['reading'] = 'offset_px = photo_gain_px (intercept) + sheet_minus_release_fu (slope) * px_per_font_unit'
        for k in VARIANTS:
            base = 'fit' if k.startswith('fit') else 'stem' if k.startswith('stem') else k      # the sheet is always read at its half level
            for g in sorted({g for _, g in per}):
                x = [v[base] / v['s'] for (b, gg), v in per.items() if gg == g and v[base] is not None]
                if x:
                    tau[(face, g, k)] = float(np.mean(x))
            x = [v[base] / v['s'] for v in per.values() if v[base] is not None]
            tau_face[(face, k)] = float(np.median(x)) if x else None
    res['sheets'] = sheets

    # ---- 2. each print's gain, measured on the control faces (pixels per edge)
    gains = {}
    for src in ('N46', 'N45'):
        gains[src] = {}
        for face in ('kilfane', 'carrick'):
            rs = blocks.get((src, face, 'alphabet'), [])
            out = {}
            for k in VARIANTS:
                g = []
                for r in rs:
                    v, s_ = values(r)
                    t = tau.get((face, r['glyph'], k))
                    if k in v and t is not None:
                        g.append(v[k] - t * s_)
                out[k] = centre(g)
            # the same with one face-wide sheet offset instead of each glyph's own
            out['fit_facewide'] = centre([values(r)[0]['fit'] - tau_face[(face, 'fit')] * values(r)[1] for r in rs]) if tau_face.get((face, 'fit')) is not None else None
            out['per_glyph_fit'] = {r['glyph']: values(r)[0]['fit'] - tau[(face, r['glyph'], 'fit')] * values(r)[1] for r in rs if (face, r['glyph'], 'fit') in tau}
            out['px_per_font_unit'] = centre([values(r)[1] for r in rs])
            gains[src][face] = out
        comb = {}
        for k in VARIANTS:
            a, b = gains[src]['kilfane'][k], gains[src]['carrick'][k]
            if a['value'] is None or b['value'] is None:
                comb[k] = a if b['value'] is None else b
                continue
            comb[k] = dict(value=(a['value'] + b['value']) / 2,
                           se=float(np.sqrt(((a['se'] or 0) ** 2 + (b['se'] or 0) ** 2) / 4 + ((a['value'] - b['value']) / 2) ** 2)),
                           note='mean of Kilfane and Carrick; se includes half their difference')
        gains[src]['both'] = comb
    res['print_gain_px'] = gains

    # ---- 3. the unknown faces with that gain removed (font units per edge against the release; and the stem)
    def corrected(face, src, block, gain_src, control):
        rs = blocks.get((src, face, block), [])
        out = {}
        for k in VARIANTS:
            g = gains[gain_src][control][k]
            raw = [(values(r)[0][k]) / values(r)[1] for r in rs if k in values(r)[0]]
            c = centre(raw)
            row = dict(print_minus_release_fu=c)
            if g['value'] is not None and c['value'] is not None:
                s_ = float(np.median([values(r)[1] for r in rs]))
                x = centre([(values(r)[0][k] - g['value']) / values(r)[1] for r in rs if k in values(r)[0]])
                se = float(np.sqrt((x['se'] or 0) ** 2 + ((g['se'] or 0) / s_) ** 2))
                row['drawn_minus_release_fu'] = dict(value=x['value'], se=se, n=x['n'])
                st = RELEASE[face]['stem']
                row['printed_stem_fu'] = st + 2 * c['value']
                row['drawn_stem_fu'] = dict(value=st + 2 * x['value'], se=2 * se)
                row['drawn_stem_over_x_height'] = dict(value=(st + 2 * x['value']) / RELEASE[face]['x_height'], se=2 * se / RELEASE[face]['x_height'])
            out[k] = row
        return out
    res['corrected'] = {}
    for face in ('ceili', 'tuam'):
        for src, block, gsrc in (('N46', 'alphabet', 'N46'), ('N45', 'alphabet', 'N45'), ('N44', 'heading', 'N45'),
                                 ('N46', 'S53915', 'N46'), ('N46', 'S53916', 'N46')):
            if (src, face, block) in blocks:
                res['corrected'][f'{face} {src} {block}'] = {c: corrected(face, src, block, gsrc, c) for c in ('kilfane', 'carrick', 'both')}

    # ---- 4. several sizes on one print: offset_px = gain_px + (drawn - release) * px_per_font_unit
    def sizes(face, src, glyphs, blks, key):
        pts = []
        for b in blks:
            for r in blocks.get((src, face, b), []):
                if r['glyph'] in glyphs and key in values(r)[0]:
                    pts.append(dict(block=b, glyph=r['glyph'], s=values(r)[1], offset_px=values(r)[0][key]))
        if len({p['block'] for p in pts}) < 2:
            return None
        fit = line_fit([p['s'] for p in pts], [p['offset_px'] for p in pts], [SIZE_SE] * len(pts))
        return dict(points=pts, gain_px=dict(value=fit['intercept'], se=fit['intercept_se']),
                    drawn_minus_release_fu=dict(value=fit['slope'], se=fit['slope_se']), chi2_per_dof=fit['chi2_per_dof'], assumed_point_se_px=SIZE_SE)
    ms = {}
    for key in ('fit', 'stem'):
        ms[key] = {
            'ceili N46 (a, 1: alphabet, 24pt, 42pt)': sizes('ceili', 'N46', {'a', 'one'}, ['alphabet', 'S53915', 'S53916'], key),
            'kilfane N46 (A: alphabet, 30pt, 48pt)': sizes('kilfane', 'N46', {'A'}, ['alphabet', 'S53909 30pt', 'S53910 48pt'], key),
            'carrick N46 (a: alphabet, 36pt, 60pt)': sizes('carrick', 'N46', {'a'}, ['alphabet', 'S53913 36pt', 'S53914 60pt'], key),
            'tuam N46 (a, 1: alphabet, 30pt, 48pt)': sizes('tuam', 'N46', {'a', 'one'}, ['alphabet', 'S53911 30pt', 'S53912 48pt'], key)}
    for face, g in (('kilfane', 'A'), ('carrick', 'a')):
        for key in ('fit', 'stem'):
            k = [x for x in ms[key] if x.startswith(face)][0]
            if ms[key][k]:
                ms[key][k]['known_sheet_minus_release_fu'] = tau.get((face, g, key))
    # the offset branch: the brochure's alphabet (N45) and its cover heading (N44), letter by letter
    a45 = {r['glyph']: r for r in blocks.get(('N45', 'ceili', 'alphabet'), [])}
    pair = [(values(a45[r['glyph']]), values(r)) for r in blocks.get(('N44', 'ceili', 'heading'), []) if r['glyph'] in a45]
    if pair:
        dd = centre([b[0]['fit'] - a[0]['fit'] for a, b in pair]); ds = float(np.median([b[1] - a[1] for a, b in pair]))
        ms['offset branch (N44 heading against N45 alphabet)'] = dict(
            offset_difference_px=dd, scale_difference_px_per_fu=ds, scale_ratio=float(np.median([b[1] / a[1] for a, b in pair])),
            drawn_minus_release_fu=dict(value=dd['value'] / ds, se=(dd['se'] or 0) / abs(ds)),
            note='assumes the cover and the inside page print with the same gain; the sizes differ by too little to separate gain from weight')
    res['multi_size'] = ms

    # ---- 5. black and white: stems against the gaps between them, and same-facing edges
    comp = {}
    for (src, face, block), rs in sorted(blocks.items()):
        stem, gap, pitch = [], [], []
        for r in rs:
            st = [t for t in r.get('stems', []) if t.get('L50')]
            s_ = r['single']['s']
            for a, b in zip(st, st[1:]):
                if min(a['v1'], b['v1']) - max(a['v0'], b['v0']) < 60:
                    continue
                stem.append(a['L50']['half_gain_px'] + b['L50']['half_gain_px'])            # mean growth of one stem's width
                gap.append(((b['L50']['left'] - a['L50']['right']) - (b['x_left'] - a['x_right'])) * s_)
                pitch.append((((b['L50']['left'] - a['L50']['left']) + (b['L50']['right'] - a['L50']['right'])) / 2 - ((b['x_left'] - a['x_left']) + (b['x_right'] - a['x_right'])) / 2) * s_)
        if stem:
            comp[f'{src} {face} {block}'] = dict(stem_width_growth_px=centre(stem), gap_width_change_px=centre(gap),
                                         sum_px=centre(np.add(stem, gap)), pitch_error_px=centre(pitch), pairs=len(stem))
    res['complementarity'] = comp
    return res


SIZE_SE = 0.2     # one glyph's offset, pixels: the scatter of single glyphs about their block's median


# ------------------------------------------------------------------ is the gain the same across a page?
CAPTIONS = {   # the same small grotesque type set across each page: boxes read off the scans
    'N46': {'left (beside Kilfane and Carrick)': [(290, 1212, 470, 1300), (610, 1212, 800, 1300), (290, 2072, 450, 2150), (610, 2072, 800, 2150)],
            'right (beside Tuam and Ceili)': [(1280, 1128, 1450, 1205), (1660, 1128, 1860, 1205), (1280, 2058, 1450, 2145), (1660, 2058, 1860, 2145)]},
    'N45': {'left page (under Ceili)': [(750, 1970, 850, 2005)],
            'right page (under Carrick, Kilfane, Tuam)': [(1590, 1948, 1700, 1980), (1590, 1982, 1700, 2012), (2270, 1955, 2440, 1985), (2270, 1987, 2440, 2017)]},
}


def stroke_width(I):
    """Mean stroke width of thin lettering in an ink map: twice its ink area over its outline's length."""
    from skimage import measure
    I = np.pad(np.clip(I, 0, 1), 2)
    P = sum(np.linalg.norm(np.diff(c, axis=0), axis=1).sum() for c in measure.find_contours(I, 0.5))
    return float(2 * I[I > 0.15].sum() / P) if P else None


def page_uniformity(specimens=SPEC):
    """Stroke widths of the captions on each side of each page.  The captions are one type at one
    size, so a difference between the sides is a difference of gain (half of it per edge)."""
    out = {}
    for src, sides in CAPTIONS.items():
        g = gray(src, specimens); o = {}
        for side, boxes in sides.items():
            w = []
            for x0, y0, x1, y1 in boxes:
                c = g[y0:y1, x0:x1]; paper = float(np.median(c)); ink = float(np.percentile(c, 1))
                w.append(stroke_width((paper - c) / (paper - ink)))
            o[side] = dict(boxes=[list(b) for b in boxes], stroke_width_px=w, mean=float(np.mean(w)),
                           se=(float(np.std(w, ddof=1) / np.sqrt(len(w))) if len(w) > 1 else None))
        (a, A), (b, B) = o.items()
        key = 'ceili_side_minus_control_side_gain_px_per_edge'
        ce, ct = (B, A) if src == 'N46' else (A, B)
        o[key] = dict(value=(ce['mean'] - ct['mean']) / 2, se=float(np.sqrt((ce['se'] or ct['se'] or 0) ** 2 + (ct['se'] or 0) ** 2) / 2))
        out[src] = o
    return out


# ------------------------------------------------------------------ what it comes to
PX_PER_MM = {'N46': 2140 / 210.0, 'N45': 3000 / 420.0, 'N44': 3000 / 420.0}   # A4 page; A3 spread (assumed, see size_check)


def conclude(res, uniformity=None):
    """The estimates of the drawn stem side by side, and their range.  The range is a range of
    methods and prints, not a statistical confidence interval."""
    out = {}
    blocks = res['blocks']
    s_of = lambda k: blocks[k]['px_per_font_unit']['value']
    out['size_check'] = dict(
        note='nominal heights from the leaflet captions; l is 767 font units tall in the Ceili release, Kilfane capitals 706',
        ceili_42pt_sample_N46_mm=s_of('N46 ceili S53916') * 767 / PX_PER_MM['N46'], ceili_24pt_sample_N46_mm=s_of('N46 ceili S53915') * 767 / PX_PER_MM['N46'],
        ceili_heading_N44_mm=s_of('N44 ceili heading') * 767 / PX_PER_MM['N44'], ceili_nominal_mm={'24pt': 6.5, '42pt': 11.0},
        kilfane_48pt_sample_N46_mm=s_of('N46 kilfane S53910 48pt') * 706 / PX_PER_MM['N46'], kilfane_nominal_mm={'48pt': 13.0},
        px_per_mm=PX_PER_MM)
    out['print_gain_mm_per_edge'] = {src: {face: {k: (res['print_gain_px'][src][face][k]['value'] / PX_PER_MM[src]
                                                       if res['print_gain_px'][src][face][k]['value'] is not None else None)
                                                   for k in ('fit', 'stem', 'thick', 'thin')} for face in ('kilfane', 'carrick', 'both')}
                                     for src in ('N46', 'N45')}
    for face in ('ceili', 'tuam'):
        st, xh = RELEASE[face]['stem'], RELEASE[face]['x_height']
        est = []
        def add(name, key, kind, bias=None):
            c = res['corrected'].get(key)
            if not c or 'drawn_stem_fu' not in c['both']['stem']:
                return
            row = dict(name=name, kind=kind, stem_fu=c['both']['stem']['drawn_stem_fu']['value'], se=c['both']['stem']['drawn_stem_fu']['se'],
                       kilfane_only=c['kilfane']['stem']['drawn_stem_fu']['value'], carrick_only=c['carrick']['stem']['drawn_stem_fu']['value'],
                       at_40=c['both']['stem40'].get('drawn_stem_fu', {}).get('value'), at_60=c['both']['stem60'].get('drawn_stem_fu', {}).get('value'),
                       n_glyphs=c['both']['stem']['drawn_minus_release_fu']['n'], printed_stem_fu=c['both']['stem']['printed_stem_fu'],
                       whole_outline_stem_fu=c['both']['fit']['drawn_stem_fu']['value'],
                       hairline_offset_fu_per_edge=c['both']['thin'].get('drawn_minus_release_fu', {}).get('value'))
            if bias:
                row['known_bias'] = bias
            est.append(row)
        add('N46 alphabet, gain from N46 controls', f'{face} N46 alphabet', 'control faces')
        add('N45 alphabet, gain from N45 controls', f'{face} N45 alphabet', 'control faces')
        add('N44 cover heading, gain from N45 controls', f'{face} N44 heading', 'control faces (another forme of the same press)')
        add('N46 42 pt sheet sample, gain from N46 controls', f'{face} N46 S53916', 'control faces (one stem)')
        add('N46 24 pt sheet sample, gain from N46 controls', f'{face} N46 S53915', 'control faces (one stem)')
        ms = [v for k, v in res['multi_size']['fit'].items() if k.startswith(face)][0]
        if ms:
            est.append(dict(name='N46, three sizes of a and 1 (no control face)', kind='multi-size regression',
                            stem_fu=st + 2 * ms['drawn_minus_release_fu']['value'], se=2 * ms['drawn_minus_release_fu']['se'],
                            gain_px=ms['gain_px']['value'], gain_se=ms['gain_px']['se']))
        if uniformity:      # the same estimates if the captions' side-to-side difference of gain is added to the controls' gain
            for e, src in ((est[0], 'N46'), (est[1], 'N45')):
                du = uniformity[src]['ceili_side_minus_control_side_gain_px_per_edge']['value'] if face == 'ceili' else None
                if du is not None:
                    e['with_caption_difference'] = e['stem_fu'] - 2 * du / s_of(f"{src} {face} alphabet")
        vals = [e['stem_fu'] for e in est] + [e['with_caption_difference'] for e in est if 'with_caption_difference' in e]
        best = float(np.mean([est[0]['stem_fu'], est[1]['stem_fu']]))
        lo, hi = float(min(vals)), float(max(vals))
        raw = {src: res['corrected'][f'{face} {src} alphabet']['both']['stem']['printed_stem_fu'] for src in ('N46', 'N45')}
        out[face] = dict(
            release_stem_fu=st, release_x_height_fu=xh, release_stem_over_x_height=st / xh, estimates=est,
            best_stem_fu=best, range_fu=[lo, hi], best_over_x_height=best / xh, range_over_x_height=[lo / xh, hi / xh],
            best_is='mean of the N46 and N45 alphabets, each with its own print gain removed (stems against stems)',
            range_is='smallest and largest central value among all estimates and their caption-adjusted variants: a range of methods, not a confidence interval',
            printed_stem_fu=raw, release_inside=bool(lo <= st <= hi), N46_inside=bool(lo <= raw['N46'] <= hi), N45_inside=bool(lo <= raw['N45'] <= hi),
            implied_change_of_release_stem_percent=dict(best=100 * (best / st - 1), range=[100 * (lo / st - 1), 100 * (hi / st - 1)]),
            implied_change_per_edge_fu=dict(best=(best - st) / 2, range=[(lo - st) / 2, (hi - st) / 2]))
    return out


def report(res):
    f = lambda b, k=2: '   --   ' if (b is None or b.get('value') is None) else f"{b['value']:+.{k}f} ±{(b.get('se') or 0):.{k}f}"
    print('\nSheet minus release outline, font units per edge (half level of the photograph)')
    for face, v in res['sheets'].items():
        for sh, w in v.items():
            if sh != 'two_sizes':
                print(f"  {face:8s} {sh:12s} whole {f(w['sheet_minus_release_fu']['fit'])}   stems {f(w['sheet_minus_release_fu']['stem'])}   ({len(w['glyphs'])} letters)")
        t = v['two_sizes']
        print(f"  {face:8s} two sizes: photograph's own gain {t['intercept']:+.2f} ±{t['intercept_se']:.2f} px")
    print('\nPrint gain on the control faces, pixels per edge')
    for src, v in res['print_gain_px'].items():
        for face, w in v.items():
            print(f"  {src} {face:8s} whole {f(w['fit'])}   stems {f(w['stem'])}   thick {f(w['thick'])}   thin {f(w['thin'])}")
    for face in ('ceili', 'tuam'):
        c = res['conclusion'][face]
        print(f"\n{face}: release stem {c['release_stem_fu']:.0f}; printed N46 {c['printed_stem_fu']['N46']:.1f}, N45 {c['printed_stem_fu']['N45']:.1f}")
        for e in c['estimates']:
            print(f"  {e['name']:50s} {e['stem_fu']:6.1f} ±{e['se']:.1f}" + (f"   (captions: {e['with_caption_difference']:.1f})" if 'with_caption_difference' in e else ''))
        print(f"  best {c['best_stem_fu']:.1f} ({c['best_over_x_height']:.3f} x-height), range {c['range_fu'][0]:.1f} to {c['range_fu'][1]:.1f}; "
              f"release inside: {c['release_inside']}; N46: {c['N46_inside']}; N45: {c['N45_inside']}")


def _json(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    raise TypeError(type(o))


def load_cached():
    recs = []
    for t in tasks():
        f = OUT / 'fits' / (task_key(t) + '.json')
        if f.exists():
            recs += json.loads(f.read_text())
    return recs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--specimens', default=str(SPEC), help='folder holding the archive scans (default build/research/original-specimens)')
    ap.add_argument('--jobs', type=int, default=3)
    ap.add_argument('--refit', action='store_true', help='measure the scans again (default: reuse build/print-model/fits/*.json where present)')
    ap.add_argument('--out', default=str(ROOT / 'research' / 'print-model' / 'results.json'))
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if a.refit:
        for f in (OUT / 'fits').glob('*.json'):
            f.unlink()
    recs = collect(a.specimens, a.jobs)                       # cached glyphs are read back, the rest measured
    res = analyse(recs)
    res['page_uniformity'] = page_uniformity(a.specimens)
    res['conclusion'] = conclude(res, res['page_uniformity'])
    files = {src: dict(file=FILES[src], sha256=sha256(Path(a.specimens) / FILES[src])) for src in FILES}
    fonts = {f: dict(file=str(p.relative_to(ROOT)), sha256=sha256(p)) for f, p in FONT.items()}
    meas = [dict(src=r['src'], face=r['face'], block=r['block'], glyph=r['glyph'], box=r['box'], score=r['score'],
                 px_per_font_unit=r['single']['s'], rotation_rad=r['single']['rot'], origin_px=[r['single']['tx'], r['single']['ty']],
                 aspect=r['single']['aspect'], shear=r['single']['shear'], blur_sigma_px=r['single']['sigma'], rms=r['single']['rms'],
                 offset_px=values(r)[0], local_paper=r['local_paper'], local_ink=r['local_ink'],
                 stems=[dict(ref_width_fu=t['ref_width'], x_left_fu=t['x_left'], x_right_fu=t['x_right'], y0_fu=t['v0'], y1_fu=t['v1'],
                             width_px={L: (t[L]['width_px'] if t.get(L) else None) for L in ('L40', 'L50', 'L60')},
                             se_px=(t['L50']['se_px'] if t.get('L50') else None)) for t in r.get('stems', [])])
            for r in recs if 'error' not in r]
    out = dict(
        what='Ink-gain model of the prints of the four faces; see research/print-model/README.md',
        sources=files, reference_outlines=fonts, print_levels={k: dict(paper=v[0], ink=v[1]) for k, v in PRINT_LEVELS.items()},
        windows=dict(blocks=[dict(src=b[0], face=b[1], block=b[2], window=b[3], rough_px_per_fu=b[4], glyphs=b[5]) for b in BLOCKS],
                     sheets={k: dict(window=v[0], rough_px_per_fu=v[1]) for k, v in SHEET_WINDOWS.items()},
                     ceili_regions=str(CEILI_REGIONS.relative_to(ROOT)), tuam_regions=str(TUAM_REGIONS.relative_to(ROOT))),
        model=dict(supersampling=SS, reference_px_per_font_unit=RES, thin_stroke_limits_fu=THIN, release=RELEASE,
                   transform='print pixel = origin_px + px_per_font_unit * R(rotation) * (x + shear*y, aspect*y), font units, y down from the baseline',
                   offset='every edge of the release outline moved outwards by offset_px, then a Gaussian blur; half level between local paper and ink'),
        results=res, measurements=meas)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rnd(out), indent=1, default=_json) + '\n')
    report(res)


if __name__ == '__main__':
    main()
