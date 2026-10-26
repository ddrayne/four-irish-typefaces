"""Every print of each Céilí letter, registered into its trace's frame and averaged.

usage: python scripts/ceili_prints.py locate                  # where each letter is on every print
       python scripts/ceili_prints.py average [GLYPH ...]     # register and average (build/ceili-judgement/prints)

Céilí has no production sheet to average, as Kilfane and Carrick have; it has several prints of one
artwork, and none of them is the drawing:

  N46     the D. O'Sullivan leaflet (NIVAL's copy), a photocopy: its toner spreads and speckles, and its
          broken hairlines are what Study 3 traced for 50 of its 54 letters
  flyer   sources/flyer.jpg, the release's scan of the same leaflet, at about a third of N46's resolution
  N45     the competition brochure (NIVAL's copy), offset-printed on textured stock, set out in different
          lines from N46 (a separate paste-up of the same letters)
  B2      Bolger's photograph of Trinity College's copy of the brochure (thesis volume 2, figure 203b):
          the same plate as N45 on a different sheet, at half N45's resolution
  N44     the brochure's cover, whose heading "design an irish typeface" is set in Céilí
          (Bolger, volume 1, pp. 279-80): separately made impressions of fifteen letters
  S53915, S53916   the leaflet's samples of the 24 pt and 42 pt Letraset sheets: a and 1

N45, B2 and N44 share the brochure's press, N46 and flyer the leaflet's photocopying, so agreement within
a branch is not confirmation. Across branches it is the best evidence there is: a gap or notch one
print shows and another fills is print; a feature every print shows is drawing.

Only N46 and N45 are averaged: both print every letter, so every letter is drawn from the same two
prints, the alphabet stays of a piece (the cover heading prints heavier hairlines, and the fifteen
letters it has would come out heavier than the rest), and N44 is left as a check the averaging never
saw. N44, the sheet samples and the low-resolution prints are registered and shown beside them.

Each print's ink (0 paper .. 1 ink, from its own levels; where its letters' ink components are known,
neighbouring letters are masked out) is registered onto the letter's Study 3 trace by a similarity
transform (uniform scale, rotation and shift: translation search, then coarse-to-fine least squares, as
scripts/trace_production.py registers production impressions, but never stretched or sheared), then
twice onto the high-resolution prints' mean, with the frame pinned in the trace's coordinates, and the
prints are averaged, each at its own midpoint (half way from its paper to its ink). The prints differ in
weight and contrast (N46's photocopied stems spread while its hairlines thin; N45's stems print about
10% lighter while its hairlines hold), so the level at which each print's stems match Study 3's is
measured and recorded, but not used to bend the prints: the face's weight is set afterwards by one
edge level of the mean (scripts/trace_ceili_judgement.py). The low-resolution prints (flyer, B2) are
registered and kept for comparison, never averaged.

Everything written here holds archive pixels and stays in ignored build/ (research/RIGHTS.md).
"""
import argparse, hashlib, json, subprocess, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import impressions as IM

SPECIMENS = ROOT / 'build' / 'research' / 'original-specimens'
SOURCES = ROOT / 'build' / 'research' / 'sources'
WORK = ROOT / 'build' / 'ceili-judgement' / 'prints'
BASE = ROOT / 'research' / 'round-04' / 'ceili' / 'traces'          # Study 3 (round-3 letter bodies)
REGIONS = ROOT / 'research' / 'round-03' / 'ceili' / 'traces' / 'source-regions.json'
N46, N45, N44 = 'competition-advert-1.jpg', 'competition-brochure-2.jpg', 'competition-brochure-1.jpg'
B2_PDF, B2_PAGE = 'Bolger-2017-volume-2-illustrations.pdf', 159   # figure 203b, the page's one photograph

PRINTS = {
    'N46': dict(file=N46, source_id='N46', branch='leaflet', averaged=True, high=True,
                what="D. O'Sullivan leaflet, NIVAL copy (photocopy); Study 3's source for 50 letters"),
    'flyer': dict(file='sources/flyer.jpg', source_id='flyer', branch='leaflet', averaged=False, high=False,
                  what="the release's scan of the same leaflet, about a third of N46's resolution"),
    'N45': dict(file=N45, source_id='N45', branch='brochure', averaged=True, high=True,
                what='competition brochure, NIVAL copy (offset); a separate paste-up; Study 3 b, e, e.alt1, h'),
    'B2': dict(file=B2_PDF, source_id='B2', page=B2_PAGE, branch='brochure', averaged=False, high=False,
               what="Bolger vol. 2 fig. 203b: Trinity College's copy of the brochure, photographed; half N45's resolution"),
    'N44': dict(file=N44, source_id='N44', branch='brochure cover', averaged=False, high=True,
                what='brochure cover heading "design an irish typeface", set in Céilí (Bolger vol. 1, pp. 279-80)'),
    'S53915': dict(file=N46, source_id='N46', branch='leaflet (Letraset sheet sample)', averaged=False, high=True,
                   what='24 pt Letraset sheet S53915 sample "a1" on the leaflet (N46)'),
    'S53916': dict(file=N46, source_id='N46', branch='leaflet (Letraset sheet sample)', averaged=False, high=True,
                   what='42 pt Letraset sheet S53916 sample "a1" on the leaflet (N46)'),
}
# the cover heading: its ink components (threshold 130, eight-connected) in reading order, in this row
# box. The forms were read by eye (the d's flag, the plain a of "an" and "face", the drawn-out tongue of
# the last e) and are checked by registration in `locate`.
N44_ROW = (1550, 350, 2950, 650)
N44_LETTERS = [('d', [2]), ('e', [23]), ('s', [21]), ('i', [5, 16]), ('g', [9]), ('n', [17]),
               ('a', [18]), ('n', [11]),
               ('i', [3, 7]), ('r', [12]), ('i', [4, 13]), ('s', [14]), ('h', [1]),
               ('t', [6]), ('y', [19]), ('p', [15]), ('e', [22]), ('f', [8]), ('a', [20]), ('c', [24]), ('e.alt1', [25])]
N44_VARIANTS = {'d': ['d', 'd.alt1'], 'a': ['a', 'a.alt1', 'a.alt2'], 'e': ['e', 'e.alt1'], 'e.alt1': ['e', 'e.alt1'],
                'r': ['r', 'r.alt1'], 's': ['s', 's.alt1'], 'n': ['n', 'n.alt1']}
# the leaflet's two sheet samples, each "a1" (row boxes on N46; a is left, 1 right)
SAMPLES = {'S53915': (1250, 1940, 1500, 2066), 'S53916': (1640, 1930, 2000, 2066)}
# the part of each image that holds Céilí (the ink map is computed there only)
WINDOW = {'N46': (1080, 1360, 2110, 2080), 'N45': (730, 310, 1460, 910), 'N44': (1530, 330, 2970, 670),
          'B2': (440, 200, 890, 570), 'flyer': (400, 500, 803, 740)}
WINDOW['S53915'] = WINDOW['S53916'] = WINDOW['N46']
FINE, STEPS, PAD = 0.125, (0.5, 0.25), 3.0


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def b2_image():
    """Figure 203b's photograph, extracted unchanged (pdfimages -j writes the embedded JPEG) into build/."""
    out = WORK / 'b2-fig203b.jpg'
    if not out.exists():
        WORK.mkdir(parents=True, exist_ok=True)
        subprocess.run(['pdfimages', '-f', str(B2_PAGE), '-l', str(B2_PAGE), '-j', str(SOURCES / B2_PDF), str(WORK / 'b2')], check=True)
        jpgs = sorted(WORK.glob('b2-*.jpg'))
        jpgs[0].rename(out)
        for p in WORK.glob('b2-*'):
            if p != out:
                p.unlink()
    return out


def image_path(pid):
    f = PRINTS[pid]['file']
    return b2_image() if pid == 'B2' else ROOT / f if f.startswith('sources/') else SPECIMENS / f


def ink_map(g, pid):
    """0 (paper) .. 1 (ink). The scans are evenly lit: the paper level is the window's 80th percentile
    (the window is mostly paper), the ink level its 2nd. Bolger's photograph is not: its paper level
    is the local backing (a grey closing wider than any stroke removes the letters, then a median)."""
    ink = float(np.percentile(g, 2))
    if pid == 'B2':
        paper = ndi.median_filter(ndi.grey_closing(g, size=(21, 21)), size=31)
    else:
        paper = float(np.percentile(g, 80))
    return np.clip((paper - g) / np.maximum(paper - ink, 1), 0, 1)


class Prints:
    """Each print's grey image, ink map and component labels, loaded once per process."""
    def __init__(self):
        self.g, self.p, self.lab, self.patches = {}, {}, {}, {}

    def gray(self, pid):
        if pid not in self.g:
            from PIL import Image
            self.g[pid] = np.asarray(Image.open(image_path(pid)).convert('L')).astype(float)
        return self.g[pid]

    def ink(self, pid):
        if pid not in self.p:
            g = self.gray(pid); x0, y0, x1, y1 = WINDOW[pid]
            cache = WORK / f'ink-{pid}.npy'                         # shared by the worker processes
            if cache.exists():
                win = np.load(cache).astype(float)
            else:
                win = ink_map(g[y0:y1, x0:x1], pid)
                np.save(cache, win.astype(np.float32))
            out = np.zeros(g.shape)
            out[y0:y1, x0:x1] = win
            self.p[pid] = out
        return self.p[pid]

    def labels(self, pid, row_box):
        key = (pid, tuple(row_box))
        if key not in self.lab:
            self.lab[key] = labels_in(self.gray(pid), row_box)
        return self.lab[key]

    def patch(self, e):
        """The print's ink around a letter, and the patch's origin. Where the letter's components are
        known, everything else is masked out (as source_study.component_field does): the letter's own
        components grown by three pixels, never into another component."""
        pid = e['print']; P = self.ink(pid)
        x0, y0, x1, y1 = e['box']; m = int(round(0.6 * (y1 - y0))) + 8
        X0, Y0 = max(0, x0 - m), max(0, y0 - m); X1, Y1 = min(P.shape[1], x1 + m), min(P.shape[0], y1 + m)
        key = (pid, tuple(e['box']))
        if key in self.patches:
            return self.patches[key]
        crop = P[Y0:Y1, X0:X1].copy()
        if e.get('labels'):
            rb = e['row_box']; lab = self.labels(pid, rb)
            a0, b0, a1, b1 = max(X0, rb[0]), max(Y0, rb[1]), min(X1, rb[2]), min(Y1, rb[3])
            sub = lab[b0 - rb[1]:b1 - rb[1], a0 - rb[0]:a1 - rb[0]]
            ownm = np.isin(sub, e['labels'])
            allowed = np.zeros(crop.shape, bool)
            allowed[b0 - Y0:b1 - Y0, a0 - X0:a1 - X0] = ndi.binary_dilation(ownm, iterations=3) & ((sub == 0) | ownm)
            crop *= allowed
        self.patches[key] = (crop, (X0, Y0))
        return self.patches[key]


def labels_in(g, box, threshold=130):
    x0, y0, x1, y1 = box
    lab, _ = ndi.label(g[y0:y1, x0:x1] < threshold, structure=np.ones((3, 3)))
    return lab


def box_of(lab, ids, origin):
    yy, xx = np.nonzero(np.isin(lab, ids))
    return [int(xx.min() + origin[0]), int(yy.min() + origin[1]), int(xx.max() + origin[0] + 1), int(yy.max() + origin[1] + 1)]


def traces():
    return {g['name']: g for g in json.loads((BASE / 'ceili.json').read_text())['glyphs']}


def evidence():
    return {g['name']: g for g in json.loads((BASE / 'evidence.json').read_text(encoding='utf-8'))['glyphs']}


def initial(rec, box, offset=(0, 0)):
    """An affine from trace units to patch pixels laying the trace's ink box on the print's box."""
    pts = np.array([p for _, a in rec for p in a], float)
    (u0, v0), (u1, v1) = pts.min(0), pts.max(0)
    x0, y0, x1, y1 = box
    s = (y1 - y0) / (v1 - v0)                                    # uniform to start; the fit frees it
    cx, cy = (x0 + x1) / 2 - offset[0], (y0 + y1) / 2 - offset[1]
    return [s, 0, 0, s, cx - s * (u0 + u1) / 2, cy - s * (v0 + v1) / 2]


def shift(q, offset, sign=1):
    return np.r_[q[:4], q[4] + sign * offset[0], q[5] + sign * offset[1]]


def register(sheet_p, template, origin, step, q0, blur=1.0, reach=0, levels=(6.0, 3.0, 1.0)):
    """impressions.register restricted to a similarity (one uniform scale, a rotation and a shift): these
    are flat scans of one artwork, so a letter is never stretched or sheared onto another print (a free
    affine squashes thin letters such as 1, z and ! to fit). Returns the affine q and the residual."""
    from scipy.optimize import least_squares
    sheet_p, q, (cx, cy) = IM._crop(sheet_p, template, origin, step, np.array(q0, float), 40 + reach)
    if reach:
        q = IM._shift_search(sheet_p, template, origin, step, q, reach, 4.0 * blur)
    H, W = template.shape
    jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    xc, yc = origin[0] + step * W / 2, origin[1] + step * H / 2   # about the frame's centre: well conditioned
    x = (origin[0] + step * (jj + 0.5)).ravel() - xc; y = (origin[1] + step * (ii + 0.5)).ravel() - yc
    s0 = float(np.sqrt(abs(q[0] * q[3] - q[1] * q[2])))
    t0 = IM.affine_matrix(q) @ np.array([xc, yc, 1.0])
    p = np.array([s0, 0.0, t0[0], t0[1]])                         # a = s cos, b = s sin; the centre's place
    lo = [0.9 * s0, -0.1 * s0, -np.inf, -np.inf]; hi = [1.1 * s0, 0.1 * s0, np.inf, np.inf]   # within 10%, 6 degrees
    def at(img, p):
        a, b, tx, ty = p
        sx = a * x - b * y + tx; sy = b * x + a * y + ty
        return ndi.map_coordinates(img, [sy - 0.5, sx - 0.5], order=1, mode='constant', cval=0.0)
    for bl in (blur * f for f in levels):
        T = ndi.gaussian_filter(template, bl / step).ravel()
        S = ndi.gaussian_filter(sheet_p, bl)
        gy, gx = np.gradient(S)
        res = lambda p: at(S, p) - T
        def jac(p):
            Gx, Gy = at(gx, p), at(gy, p)
            return np.column_stack([Gx * x + Gy * y, -Gx * y + Gy * x, Gx, Gy])
        p = least_squares(res, np.clip(p, lo, hi), jac=jac, bounds=(lo, hi), x_scale=[0.02, 0.02, 1.0, 1.0], max_nfev=60).x
    a, b, tx, ty = p
    q = np.array([a, -b, b, a, tx - a * xc + b * yc, ty - b * xc - a * yc])
    r = IM.warp(sheet_p, q, template.shape, origin, step) - template
    return np.r_[q[:4], q[4] + cx, q[5] + cy], float(np.sqrt((r ** 2).mean()))


def register_onto(prints, e, rec, template_steps=STEPS):
    """The affine (print pixels) laying a print's letter onto its trace, and the residual."""
    crop, off = prints.patch(e)
    q = initial(rec, e['box'], off)
    k = abs(q[0]) / 2.7                                           # blur and reach with the print's resolution
    T0, origin = IM.trace_mask(rec, template_steps[0], PAD)
    q, rms = register(crop, T0, origin, template_steps[0], q, blur=max(0.5, 1.0 * k), reach=max(3, int(round(8 * k))))
    T1, origin = IM.trace_mask(rec, template_steps[1], PAD)
    q, rms = register(crop, T1, origin, template_steps[1], q, blur=max(0.4, 0.8 * k))
    return shift(q, off), rms, k


def own_ink(Mp, template, grow):
    """The letter's own ink in a registered map: pieces that lie mostly on the trace grown by `grow`
    pixels; the edges of neighbouring letters inside the frame are dropped (for the prints whose
    components are not labelled)."""
    near = ndi.binary_dilation(template > 0.5, iterations=grow)
    lab, n = ndi.label(Mp > 0.35, structure=np.ones((3, 3)))
    if not n:
        return Mp * 0
    total = np.bincount(lab.ravel(), minlength=n + 1)
    inside = np.bincount(lab[near].ravel(), minlength=n + 1)
    keep = [i for i in range(1, n + 1) if inside[i] >= 0.6 * total[i]]
    sel = ndi.binary_dilation(np.isin(lab, keep), iterations=2)
    return np.where(sel, Mp, 0.0)


def warped(prints, e, q, rec, step):
    crop, off = prints.patch(e)
    m, origin = IM.trace_mask(rec, step, PAD)
    w = IM.warp(crop, shift(q, off, -1), m.shape, origin, step)
    return own_ink(w, m, int(round(1.5 / step)))


# ---------------------------------------------------------------- locating
def locate():
    """Every letter's box on every print, with how it was found. N46 and N45 reuse round 3's regions."""
    WORK.mkdir(parents=True, exist_ok=True)
    regions = json.loads(REGIONS.read_text())
    tr = traces(); pr = Prints()
    out = {}
    for pid, fname in (('N46', N46), ('N45', N45)):
        out[pid] = [dict(name=r['name'], box=r['box'], labels=r['labels'], row_box=r['row_box'],
                         how='round-3 region') for r in regions[fname]]
    legacy = json.loads((ROOT / 'sources' / 'traced' / 'ceili.json').read_text())['glyphs']
    out['flyer'] = []
    for g in legacy:
        if g['name'] == 'DOTS':
            continue
        pts = np.array([p for _, a in g['rec'] for p in a], float)
        out['flyer'].append(dict(name=g['name'], box=[int(np.floor(pts[:, 0].min())), int(np.floor(pts[:, 1].min())),
                                                     int(np.ceil(pts[:, 0].max())), int(np.ceil(pts[:, 1].max()))],
                                 how='bounds of the legacy trace (sources/traced/ceili.json is in flyer pixels)'))
    lab = pr.labels('N44', N44_ROW)
    out['N44'] = []
    for name, ids in N44_LETTERS:
        e = dict(print='N44', box=box_of(lab, ids, N44_ROW[:2]), labels=ids, row_box=list(N44_ROW))
        scores = {}
        for cand in N44_VARIANTS.get(name, [name]):
            q, rms, _ = register_onto(pr, e, tr[cand]['rec'])
            w = warped(pr, e, q, tr[cand]['rec'], 0.25) > 0.5
            t = IM.trace_mask(tr[cand]['rec'], 0.25, PAD)[0] > 0.5
            scores[cand] = round(float((w & t).sum() / max((w | t).sum(), 1)), 4)
        best = max(scores, key=scores.get)
        if best != name:
            print(f'  N44 {name}: registration prefers {best} {scores}; the form read by eye is kept', flush=True)
        out['N44'].append(dict(name=name, box=e['box'], labels=ids, row_box=list(N44_ROW), variant_iou=scores,
                               how='component labels in the heading row; form read by eye, checked by registration'))
        print(f'N44 {name:7s} {scores}', flush=True)
    for pid, rb in SAMPLES.items():
        lab = pr.labels(pid, rb)
        sizes = np.bincount(lab.ravel())[1:]
        big = sorted((int(i) + 1 for i in np.argsort(-sizes)[:2]), key=lambda i: box_of(lab, [i], rb[:2])[0])
        out[pid] = [dict(name=n, box=box_of(lab, [i], rb[:2]), labels=[i], row_box=list(rb),
                         how='the sample\'s two components, left to right') for n, i in zip(('a', 'one'), big)]
    out['B2'] = b2_regions(pr, out['N45'])
    (WORK / 'locations.json').write_text(json.dumps(out, indent=1))
    return out


def b2_regions(pr, n45):
    """N45's boxes on Bolger's photograph, through one projective transform (the photograph's
    perspective) fitted on the letters' centres, matching each to the nearest component."""
    from skimage.transform import ProjectiveTransform, SimilarityTransform
    g = pr.gray('B2')
    block = (470, 230, 860, 540)                                  # the Céilí alphabet in the photograph
    lab = labels_in(g, block, threshold=int(np.percentile(g[block[1]:block[3], block[0]:block[2]], 50) - 45))
    cents = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        if sl is not None and (lab[sl] == i).sum() >= 12:
            yy, xx = np.nonzero(lab == i)
            cents.append((xx.mean() + block[0], yy.mean() + block[1]))
    cents = np.array(cents)
    src = np.array([[(r['box'][0] + r['box'][2]) / 2, (r['box'][1] + r['box'][3]) / 2] for r in n45])
    s0, s1 = np.array([755, 340]), np.array([1430, 880]); d0, d1 = np.array(block[:2]) + 15, np.array(block[2:]) - 15
    k = float(np.mean((d1 - d0) / (s1 - s0)))
    t = SimilarityTransform(scale=k, translation=d0 - k * s0)
    for _ in range(6):
        p = t(src)
        nn = np.argmin(((p[:, None, :] - cents[None]) ** 2).sum(-1), axis=1)
        d = np.sqrt(((p - cents[nn]) ** 2).sum(-1))
        ok = d < max(4.0, np.percentile(d, 70))
        t = ProjectiveTransform.from_estimate(src[ok], cents[nn[ok]]) if hasattr(ProjectiveTransform, 'from_estimate') else None
        if t is None:
            t = ProjectiveTransform(); t.estimate(src[ok], cents[nn[ok]])
    p = t(src); nn = np.argmin(((p[:, None, :] - cents[None]) ** 2).sum(-1), axis=1)
    resid = np.sqrt(((p - cents[nn]) ** 2).sum(-1))
    H = [[round(float(v), 8) for v in row] for row in t.params]
    out = []
    for r, e in zip(n45, resid):
        c = t(np.array([[r['box'][0], r['box'][1]], [r['box'][2], r['box'][3]]], float))
        out.append(dict(name=r['name'], box=[int(np.floor(c[0, 0])) - 1, int(np.floor(c[0, 1])) - 1, int(np.ceil(c[1, 0])) + 1,
                                             int(np.ceil(c[1, 1])) + 1],
                        how='N45 box through the fitted homography', homography_from_N45=H, centre_residual_px=round(float(e), 2)))
    print(f'B2: homography from N45, median centre residual {np.median(resid):.2f} px, worst {resid.max():.2f}', flush=True)
    return out


# ---------------------------------------------------------------- registration and averaging
def entries():
    loc = json.loads((WORK / 'locations.json').read_text())
    by = {}
    for pid, rs in loc.items():
        for i, r in enumerate(rs):
            by.setdefault(r['name'], []).append(dict(r, print=pid, key=f'{pid}:{i}'))
    return by


GRID = np.linspace(0.2, 0.8, 61)
# the letters whose stems give a print's weight: straight vertical stems, measured across the x-height band
STEMS = ['l', 'i', 'n', 'm', 'k', 'u', 'd', 'q', 'r', 't', 'p', 'j', 'l.alt1', 'n.alt1', 'r.alt1', 'one', 'h', 'b']


def stem_width(mask, ref, step, min_run=2.0):
    """The median width (trace units) of the ink runs at least `min_run` wide on scanlines across the middle of
    the reference mask's lower band (the x-height for a letter with an ascender): a stem's weight, hairlines
    and bowls' thin sides left out."""
    ys, _ = np.nonzero(ref)
    if not len(ys):
        return float('nan')
    y0, y1 = ys.min(), ys.max()
    lines = np.linspace(y1 - 0.45 * (y1 - y0), y1 - 0.15 * (y1 - y0), 9).astype(int)
    w = []
    for y in lines:
        r = np.diff(np.r_[0, mask[y].astype(int), 0])
        run = (np.nonzero(r == -1)[0] - np.nonzero(r == 1)[0]) * step
        w += [v for v in run if v >= min_run]
    return float(np.median(w)) if w else float('nan')


_PRINTS = None


def prints():
    """One Prints per process."""
    global _PRINTS
    if _PRINTS is None:
        _PRINTS = Prints()
    return _PRINTS


def first_pass(args):
    """Every print of one letter registered onto its trace; ink counts at each edge level, for calibration."""
    name, ents, rec = args
    pr = prints()
    t = IM.trace_mask(rec, FINE, PAD)[0] > 0.5
    out = {}
    for e in ents:
        q, rms, k = register_onto(pr, e, rec)
        w = warped(pr, e, q, rec, FINE)
        out[e['key']] = dict(q=[float(v) for v in q], rms=float(rms), k=float(k),
                             counts=[float((w > g).sum()) for g in GRID], trace=float(t.sum()))
        if name in STEMS:
            out[e['key']].update(stems=[stem_width(w > g, t, FINE) for g in GRID], trace_stem=stem_width(t, t, FINE))
    return name, out


def second_pass(args):
    """Onto the averaged prints' mean (twice), frame pinned; the registered maps and their mean."""
    import trace_production as TP
    name, ents, rec, first = args
    pr = prints()
    qs = {e['key']: np.array(first[e['key']]['q']) for e in ents}
    q_ref = dict(qs)
    avg = [e for e in ents if PRINTS[e['print']]['averaged']]
    keys = [e['key'] for e in avg]
    M = lambda q: np.vstack([IM.affine_matrix(q), [0, 0, 1]])
    T25, origin = IM.trace_mask(rec, 0.25, PAD)
    norm = lambda e, step: warped(pr, e, qs[e['key']], rec, step)
    if len(avg) >= 2:
        for _ in range(2):
            mean = np.mean([norm(e, 0.25) for e in avg], axis=0)
            for e in ents:
                crop, off = pr.patch(e); k = first[e['key']]['k']
                try:
                    q, _ = register(crop, mean, origin, 0.25, shift(qs[e['key']], off, -1),
                                       blur=max(0.4, 0.6 * k), levels=(2.0, 1.0))
                except ValueError:                                 # ran off its patch: keep the registration it had
                    continue
                qs[e['key']] = shift(q, off)
            # the frame pinned: each print's change is a correction in the trace's own coordinates (the prints'
            # pixels are different spaces, so their transforms cannot be averaged); the averaged prints' mean
            # correction is taken out of every print, shown ones included
            D = np.mean([np.linalg.inv(M(q_ref[k_])) @ M(qs[k_]) for k_ in keys], axis=0)
            for e in ents:
                n_ = M(qs[e['key']]) @ np.linalg.inv(D)
                qs[e['key']] = np.array([n_[0, 0], n_[0, 1], n_[1, 0], n_[1, 1], n_[0, 2], n_[1, 2]])
    m, origin = IM.trace_mask(rec, FINE, PAD)
    stack = [norm(e, FINE) for e in ents]
    mean = np.mean([s for s, e in zip(stack, ents) if PRINTS[e['print']]['averaged']], axis=0) if avg else np.zeros(m.shape)
    np.save(WORK / f'mean-{name}.npy', mean.astype(np.float32))
    np.save(WORK / f'stack-{name}.npy', np.stack(stack).astype(np.float16))
    near = ndi.binary_dilation(m > 0.5, iterations=int(round(1.5 / FINE)))
    info = []
    for e, s in zip(ents, stack):
        info.append(dict(print=e['print'], source_id=PRINTS[e['print']]['source_id'], box=e['box'], how=e['how'],
                         affine=[round(float(v), 5) for v in qs[e['key']]], geometry=decompose(qs[e['key']]),
                         rms_to_trace=round(first[e['key']]['rms'], 4), rms_to_mean=round(float(np.sqrt(((s - mean) ** 2).mean())), 4),
                         topology=TP.topology_of(TP.own_pieces(s > 0.5, near)), averaged=PRINTS[e['print']]['averaged'],
                         **{k: e[k] for k in ('variant_iou', 'centre_residual_px', 'labels') if k in e}))
    return name, dict(origin=[float(v) for v in origin], step=FINE, shape=list(m.shape), prints=info,
                      averaged=len(avg), mean_topology=TP.topology_of(TP.own_pieces(mean > 0.5, near)),
                      trace_topology=TP.topology_of(m > 0.5))


def decompose(q):
    """Scale x, scale y, shear and rotation of an affine's linear part (for the record)."""
    A = np.array([[q[0], q[1]], [q[2], q[3]]])
    sx = float(np.hypot(A[0, 0], A[1, 0])); rot = float(np.degrees(np.arctan2(A[1, 0], A[0, 0])))
    shear = float((A[0, 0] * A[0, 1] + A[1, 0] * A[1, 1]) / sx)
    sy = float(np.linalg.det(A) / sx)
    return dict(scale_x=round(sx, 4), scale_y=round(sy, 4), aspect=round(sy / sx, 4), shear=round(shear / sx, 4),
                rotation_deg=round(rot, 3))


def average(names=None, jobs=4, resume=False):
    by = entries(); tr = traces(); ev = evidence()
    names = names or [n for n in tr if n in by and n != 'DOTS']
    pr = prints()
    for pid in PRINTS:                                             # the ink maps, once, before the workers start
        pr.ink(pid)
    first_path = WORK / 'first-pass.json'
    first = json.loads(first_path.read_text()) if resume and first_path.exists() else {}
    todo = [n for n in names if n not in first]
    with Pool(jobs) as pool:
        for name, out in pool.imap_unordered(first_pass, [(n, by[n], tr[n]['rec']) for n in todo]):
            first[name] = out
            print(f'{name:10s} ' + '  '.join(f'{k.split(":")[0]} {v["rms"]:.3f}' for k, v in out.items()), flush=True)
    first_path.write_text(json.dumps(first))
    # each print's edge level: where its stems are as wide as Study 3's over the stemmed letters it shares with
    # Study 3's N46 traces (the face's weight is its stems'; the prints' hairlines differ more than their stems,
    # so matching the ink area instead would trade stem for hairline). The ink-area figures are recorded.
    levels, calibration = {}, {}
    every = [n for n in tr if n in first]                           # the levels always come from every letter registered
    half = int(np.argmin(np.abs(GRID - 0.5)))
    for pid in PRINTS:
        rows = [first[n][e['key']] for n in every for e in by[n] if e['print'] == pid and ev.get(n, {}).get('source_id') == 'N46']
        if not rows:
            rows = [first[n][e['key']] for n in every for e in by[n] if e['print'] == pid]
        target = sum(r['trace'] for r in rows)
        got = np.sum([r['counts'] for r in rows], axis=0)
        stemmed = [r for r in rows if 'stems' in r] or [first[n][e['key']] for n in every for e in by[n]
                                                         if e['print'] == pid and 'stems' in first[n][e['key']]]
        ratio = np.array([np.nanmedian([r['stems'][i] / r['trace_stem'] for r in stemmed]) for i in range(len(GRID))])
        levels[pid] = float(GRID[int(np.nanargmin(np.abs(ratio - 1)))])
        at = int(np.argmin(np.abs(GRID - levels[pid])))
        calibration[pid] = dict(level=round(levels[pid], 3), stem_letters=len(stemmed), letters=len(rows),
                                stems_at_half_vs_study3=round(float(ratio[half] - 1), 4),
                                ink_at_half_vs_study3=round(float(got[half]) / target - 1, 4),
                                ink_at_level_vs_study3=round(float(got[at]) / target - 1, 4))
        print(f'{pid:7s} edge level {levels[pid]:.3f}: at 0.5 its stems are {100 * (ratio[half] - 1):+.1f}% and its ink '
              f'{100 * (got[half] / target - 1):+.1f}% against Study 3; at its level the ink is {100 * (got[at] / target - 1):+.1f}% '
              f'({len(stemmed)} stemmed letters, {len(rows)} in all)', flush=True)
    # Each print is averaged at its own midpoint (the half-ink edge of its own ink), not at the stem-matched
    # level: the prints differ in contrast as well as weight (the photocopy's stems spread while its hairlines
    # thin; the offset print's hairlines hold while its stems are about 10% lighter), and moving N45's edge down
    # to N46's stem weight would inflate its hairlines. The face's weight is set afterwards, by one edge level
    # of the mean (scripts/trace_ceili_judgement.py). The stem-matched levels are recorded.
    used = {pid: 0.5 for pid in PRINTS}
    summary = {}
    with Pool(jobs) as pool:
        for name, s in pool.imap_unordered(second_pass, [(n, by[n], tr[n]['rec'], first[n]) for n in names]):
            summary[name] = s
            print(f'{name:10s} trace {s["trace_topology"]} mean {s["mean_topology"]}  ' +
                  '  '.join(f'{i["print"]} {i["topology"]} {i["rms_to_mean"]:.3f}' for i in s['prints']), flush=True)
    path = WORK / 'registration.json'
    old = json.loads(path.read_text()) if path.exists() else {}
    old.update(summary)
    path.write_text(json.dumps(old, indent=1))
    hashes = {pid: sha256(image_path(pid)) for pid in PRINTS}
    hashes['B2_pdf'] = sha256(SOURCES / B2_PDF)
    (WORK / 'levels.json').write_text(json.dumps(dict(levels=used, stem_matched_levels=levels, calibration=calibration,
                                                      hashes=hashes), indent=1))


# ---------------------------------------------------------------- boards
COLOURS = {'N46': (215, 40, 40), 'N45': (40, 160, 60), 'N44': (140, 60, 200), 'S53915': (230, 140, 20),
           'S53916': (230, 140, 20)}


def outline(draw, rec, origin, step, colour, width=1):
    from outline_util import flatten
    for poly in flatten([(op, [tuple(p) for p in a]) for op, a in rec], 16):
        pts = [((x - origin[0]) / step, (y - origin[1]) / step) for x, y in poly]
        draw.line(pts + [pts[0]], fill=colour, width=width)


def board(name, reg, stack, mean, base_rec, cand_rec=None, out=None):
    """One letter: every print registered into the trace's frame at its own (normalised) weight, the
    averaged prints' consensus, and their mean with Study 3's outline (red) and the candidate's (blue)."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default()
    origin, step = reg['origin'], reg['step']
    panels = []
    def grey(a):
        return Image.fromarray((255 - np.clip(a, 0, 1) * 255).astype(np.uint8)).convert('RGB')
    for info, s in zip(reg['prints'], stack):
        im = grey(s.astype(float)); d = ImageDraw.Draw(im)
        outline(d, base_rec, origin, step, (220, 0, 0))
        if cand_rec:
            outline(d, cand_rec, origin, step, (0, 90, 255))
        panels.append((im, f'{info["print"]} {"avg" if info["averaged"] else "shown"} rms {info["rms_to_mean"]:.3f} '
                           f'top {info["topology"]}'))
    avg = [(i, s.astype(float) > 0.5) for i, s in zip(reg['prints'], stack) if i['averaged']]
    if avg:
        count = np.sum([m for _, m in avg], axis=0)
        img = np.full((*count.shape, 3), 255, np.uint8)
        img[(count > 0) & (count < len(avg))] = (165, 165, 165)
        img[count == len(avg)] = (25, 25, 25)
        for i, m in avg:
            img[m & (count == 1)] = COLOURS.get(i['print'], (120, 120, 120))
        im = Image.fromarray(img); d = ImageDraw.Draw(im)
        if cand_rec:
            outline(d, cand_rec, origin, step, (0, 90, 255))
        panels.append((im, f'consensus of {len(avg)}: black all, grey some, colour one'))
        im = grey(mean); d = ImageDraw.Draw(im)
        outline(d, base_rec, origin, step, (220, 0, 0))
        if cand_rec:
            outline(d, cand_rec, origin, step, (0, 90, 255))
        panels.append((im, f'mean; red Study 3{", blue candidate" if cand_rec else ""}'))
    W = sum(p.width + 8 for p, _ in panels); H = max(p.height for p, _ in panels) + 16
    cols = max(1, min(len(panels), 6))
    rows = [panels[i:i + cols] for i in range(0, len(panels), cols)]
    W = max(sum(p.width + 8 for p, _ in r) for r in rows); H = sum(max(p.height for p, _ in r) + 18 for r in rows)
    sheet = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(sheet); y = 0
    for r in rows:
        x = 0
        for p, lab in r:
            d.text((x + 2, y + 2), lab, fill=(0, 0, 0), font=font)
            sheet.paste(p, (x, y + 16)); x += p.width + 8
        y += max(p.height for p, _ in r) + 18
    if out:
        sheet.save(out)
    return sheet


def boards(names=None, candidate=None):
    reg = json.loads((WORK / 'registration.json').read_text()); tr = traces()
    cand = {g['name']: g for g in json.loads((Path(candidate) / 'ceili.json').read_text())['glyphs']} if candidate else {}
    out = WORK.parent / 'boards'; out.mkdir(parents=True, exist_ok=True)
    for n in names or sorted(reg):
        stack = np.load(WORK / f'stack-{n}.npy'); mean = np.load(WORK / f'mean-{n}.npy').astype(float)
        board(n, reg[n], stack, mean, tr[n]['rec'], cand.get(n, {}).get('rec'), out / f'{n}.png')
    print('boards in', out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['locate', 'average', 'boards'])
    ap.add_argument('glyphs', nargs='*')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--candidate', help="a round's traces folder, whose outlines the boards draw in blue")
    ap.add_argument('--resume', action='store_true', help='reuse the first pass (build/ceili-judgement/prints/first-pass.json)')
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    if args.command == 'locate':
        locate()
    elif args.command == 'average':
        average(args.glyphs or None, args.jobs, args.resume)
    else:
        boards(args.glyphs or None, args.candidate)


if __name__ == '__main__':
    main()
