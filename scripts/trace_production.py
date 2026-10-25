"""Trace a face's letters from the repeated impressions on its Letraset production sheets.

usage: python scripts/trace_production.py kilfane --sources build/research/original-specimens
           [--base research/round-02/kilfane/traces] [--work build/production/kilfane] [--jobs 4]
           [--frame affine|dash] [GLYPH ...]

1. Each sheet's ink map (scripts/impressions.py ink_map), its letters found and named against the
   base traces at one fixed scale per sheet, so a capital is never taken for its lowercase.
2. Every impression of a letter registered onto the base trace by its own affine transform
   (translation search, then coarse-to-fine least squares), then twice onto the impressions' own
   mean with the frame pinned to the base trace's, and averaged on a 1/8-unit grid.
3. The averaged edge: the level halfway between the mean's own backing and ink, as sub-pixel
   contours in base-trace units (scan pixels, y down), ready for the designer-style fitter.

With frame='dash' (Carrick), the mean keeps the sheet's own geometry. Letraset prints a spacing
mark under every letter, a fixed distance below its baseline, and the marks of a row lie on one
line: the line its users ruled. Registered onto another print's trace, every impression's affine
also takes in that print's differences of slant and proportion, which all of a letter's impressions
share; impressions.sheet_frame removes that shared part (keeping its scale) and turns the letter
square to its marks, and the marks' place in the letter's frame is recorded for
scripts/fit_production.py to set the letter on its baseline.

Writes, under --work (ignored build/, since the means are derived from archive pixels):
impressions.json (every letter found: sheet, box, name, score), registration.json (per
impression: affine, residuals), mean-*.npy / std-*.npy, and contours.json. Nothing is written to
research/ by this script; scripts/fit_production.py turns the contours into a round's traces.
"""
import argparse, hashlib, json, os, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import impressions as IM

# Each sheet of a photograph: the channel with the best ink/backing separation, whether the ink is
# lighter than its backing, the rough letter height in pixels, and which part of the photograph it
# occupies (sheets overlap: `side(box)` is True for letters on this sheet).
EDGE_30 = lambda box: (box[1] + box[3]) / 2 > 1063 + (1183 - 1063) * ((box[0] + box[2]) / 2 - 120) / 2440
# N514: the 36pt sheet lies over the 60pt sheet's lower rows; its top edge runs from y 1295 at x 300 to
# y 1370 at x 2300. The 60pt letters at that edge show faintly through the 36pt carrier and are left out,
# as is the 36pt sheet's header.
EDGE_36 = lambda box: 1295 + 75 * ((box[0] + box[2]) / 2 - 300) / 2000
SHEETS = {
    'kilfane': dict(photo='Kilfane-Letraset.jpg', source_id='N517', sure=('E', 'I', 'L', 'H', 'K', 'B', 'F'), sheets={
        '48pt S53910': dict(channel=0, light_ink=True, letter_px=120, area=(1500, 30000), side=lambda b: not EDGE_30(b)),
        '30pt S53909': dict(channel=1, light_ink=False, letter_px=75, area=(500, 12000), side=EDGE_30)}),
    # the photographed parts of Carrick's sheets hold lowercase only (a to q), so figures are never candidates
    'carrick': dict(photo='Carrick-Letraset.jpg', source_id='N514', sure=('b', 'd', 'g', 'h', 'k', 'l'),
                    letters='abcdefghijklmnopqrstuvwxyz', detect='template', reject=2.5, frame='dash', sheets={
        '60pt S53914': dict(channel=1, light_ink=False, letter_px=100, area=(1500, 30000), side=lambda b: b[3] < EDGE_36(b) - 10),
        '36pt S53913': dict(channel=1, light_ink=False, letter_px=60, area=(400, 12000), side=lambda b: b[1] > EDGE_36(b) + 200)}),
}
MIN_SCORE, STEPS, FINE, PAD = 0.72, (0.5, 0.25), 0.125, 3.0


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def detect(p, templates, scale, side, margin=0.15, threshold=0.6, accept=0.72, coverage=0.75):
    """Whole letters by template: each letter's trace at the sheet's scale, with a margin of the white
    space a letter has around it, matched across the ink map (normalised correlation), so letters made
    of separate pieces (Carrick's k, m, i, j) are found whole. Which finds are letters is then decided by
    matching pursuit: repeatedly take the find that explains the most ink not yet explained, less the
    ink it claims where the sheet is blank, until none explains enough. An n laid over the first two
    legs of an m explains less than the m; an h laid over two l's claims the blank between them."""
    from skimage.feature import match_template, peak_local_max
    from skimage.transform import rescale
    cands = []
    for n, (m, _) in templates.items():
        t = rescale(m.astype(float), 0.5 * scale, order=1, anti_aliasing=True)
        ys, xs = np.nonzero(t > 0.5)
        t = t[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        g = int(round(margin * t.shape[0]))
        r = match_template(p, np.pad(t, g))
        for iy, ix in peak_local_max(r, min_distance=max(3, t.shape[1] // 3), threshold_abs=threshold):
            box = [int(ix + g), int(iy + g), int(ix + g + t.shape[1]), int(iy + g + t.shape[0])]
            if side(box) and box[3] <= p.shape[0] and box[2] <= p.shape[1]:
                cands.append(dict(name=n, score=round(float(r[iy, ix]), 3), box=box, t=t > 0.5))
    from scipy import ndimage as ndi
    lab, _ = ndi.label(p > 0.5, structure=np.ones((3, 3)))
    sizes = np.bincount(lab.ravel())
    def contained(c):
        # every piece of ink the letter covers lies (almost) wholly inside it: a p whose descender runs
        # off the photograph is not an n, and letters fused to a neighbour are left out
        x0, y0, x1, y1 = c['box']
        pieces = np.unique(lab[y0:y1, x0:x1][c['t']])
        pieces = pieces[pieces > 0]
        if not len(pieces):
            return False
        inside = np.bincount(lab[y0:y1, x0:x1].ravel(), minlength=len(sizes))[pieces]
        return inside.sum() >= 0.95 * sizes[pieces].sum()
    cands = [c for c in cands if contained(c)]
    R = p.copy()
    def gain(c):
        x0, y0, x1, y1 = c['box']; t = c['t']
        return float((R[y0:y1, x0:x1] * t).sum() - ((1 - p[y0:y1, x0:x1]) * t).sum())
    keep, live = [], [c for c in cands if c['score'] >= accept]
    while live:
        gains = [gain(c) for c in live]
        i = int(np.argmax(gains)); c = live.pop(i)
        x0, y0, x1, y1 = c['box']; t = c['t']
        explained = float((R[y0:y1, x0:x1] * t).sum() / t.sum())
        if explained < coverage:
            continue                                    # its ink is already another letter's
        R[y0:y1, x0:x1] *= ~t
        rivals = sorted((d for d in cands if d['name'] != c['name'] and abs(d['box'][0] - x0) + abs(d['box'][1] - y0) < 0.5 * (x1 - x0)),
                        key=lambda d: -d['score'])
        keep.append(dict(name=c['name'], score=c['score'], box=c['box'], explained=round(explained, 3),
                         runner_up=rivals[0]['name'] if rivals else None,
                         margin=round(c['score'] - (rivals[0]['score'] if rivals else 0.0), 3)))
    return keep


def find(face, sources, base, work):
    from PIL import Image
    spec = SHEETS[face]
    photo = os.path.join(sources, spec['photo'])
    im = np.asarray(Image.open(photo))
    tr = {g['name']: g for g in json.load(open(os.path.join(base, f'{face}.json')))['glyphs'] if g['name'] != 'ornament'
          and ('letters' not in spec or g['name'] in spec['letters'])}
    templates = {n: IM.trace_mask(g['rec'], 0.5, 2) for n, g in tr.items()}
    th = {n: (np.ptp(np.nonzero(m)[0]) + 1) * 0.5 for n, (m, _) in templates.items()}
    found = []
    for sheet, s in spec['sheets'].items():
        p = IM.ink_map(im[..., s['channel']], s['light_ink'], s['letter_px'])
        np.save(os.path.join(work, f'ink-{sheet.split()[0]}.npy'), p.astype(np.float32))
        comps = [c for c in IM.components(p, *s['area'])[0] if s['side'](c['box'])]
        sure = [(c['box'][3] - c['box'][1]) / th[r[0][1]] for c in comps
                for r in [IM.classify(p, c['box'], templates)] if r and r[0][1] in spec['sure'] and r[0][0] > 0.75]
        scale = float(np.median(sure))
        if spec.get('detect') == 'template':
            for d in detect(p, templates, scale, s['side']):
                found.append(dict(sheet=sheet, scale=round(scale, 4), **d))
            continue
        for c in comps:
            h = c['box'][3] - c['box'][1]
            cand = {n: t for n, t in templates.items() if abs(th[n] * scale / h - 1) < 0.12}
            r = IM.classify(p, c['box'], cand) if cand else []
            if r:
                found.append(dict(sheet=sheet, box=c['box'], name=r[0][1], score=round(r[0][0], 3),
                                  runner_up=r[1][1] if len(r) > 1 else None,
                                  margin=round(r[0][0] - (r[1][0] if len(r) > 1 else 0.0), 3), scale=round(scale, 4)))
    meta = dict(face=face, source_id=spec['source_id'], photo=spec['photo'], sha256=sha256(photo),
                min_score=MIN_SCORE, impressions=found)
    json.dump(meta, open(os.path.join(work, 'impressions.json'), 'w'), indent=1)
    return meta


def own_dash(P, box):
    """An impression's spacing mark: the thin line under its letter (in pieces where a descender's tail
    breaks it). Returns its ends and the line y = a + b x through its middle (sheet pixels), or None."""
    from scipy import ndimage as ndi
    x0, y0, x1, y1 = box; h = y1 - y0; pad = 6
    crop = P[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad] > 0.5
    lab, _ = ndi.label(crop)
    inner = np.zeros_like(crop); inner[pad + 3:-pad - 3, pad + 3:-pad - 3] = True
    keep = np.isin(lab, [l for l in np.unique(lab[inner & crop]) if l and (lab == l).sum() > 30])
    if not keep.any():
        return None
    top = y0 - pad + np.nonzero(keep)[0].max() + 2                     # just under the letter's ink
    band = P[top:top + int(0.8 * h), x0:x1]
    lab, n = ndi.label(band > 0.5)
    thin = []
    for l in range(1, n + 1):
        ys, xs = np.nonzero(lab == l)
        cols = np.bincount(xs - xs.min()); cols = cols[cols > 0]
        if np.median(cols) <= max(4, 0.08 * h) and np.ptp(xs) >= 0.06 * (x1 - x0):
            thin.append((l, float(ys.mean()), xs))
    # the mark: the thin pieces on one line that together run furthest
    best = None
    for _, y, _ in thin:
        group = [q for q in thin if abs(q[1] - y) <= 2.5]
        width = sum(np.ptp(q[2]) + 1 for q in group)
        if best is None or width > best[0]:
            best = (width, group)
    if best is None or best[0] < 0.35 * (x1 - x0):
        return None
    own = ndi.binary_dilation(np.isin(lab, [q[0] for q in best[1]]), iterations=2)
    cx, cy = [], []
    for c in np.unique(np.concatenate([q[2] for q in best[1]])):
        rr = np.nonzero(own[:, c])[0]; w = band[rr, c]
        cx.append(x0 + c + 0.5); cy.append(top + (rr * w).sum() / w.sum() + 0.5)
    b, a = np.polyfit(cx, cy, 1)
    return dict(ends=[float(min(cx)), float(max(cx))], a=float(a), b=float(b))


def add_dashes(face, base, meta, work):
    """Each impression's mark line: a straight line through its own mark and its row neighbours' (the
    photograph's sheet is not flat, so only nearby marks); for a letter whose own mark is not found,
    through its neighbours' alone."""
    for sheet, s in SHEETS[face]['sheets'].items():
        P = np.load(os.path.join(work, f'ink-{sheet.split()[0]}.npy'))
        imps = [r for r in meta['impressions'] if r['sheet'] == sheet]
        for r in imps:
            r['_own'] = own_dash(P, r['box'])
        reach = 5 * s['letter_px']
        for r in imps:
            x0, y0, x1, y1 = r['box']; cx = (x0 + x1) / 2
            o = r['_own']
            def on_row(q):
                d = q['_own']; qx = (q['box'][0] + q['box'][2]) / 2
                if q is r or d is None or abs(qx - cx) > reach:
                    return False
                y = d['a'] + d['b'] * qx
                if o:
                    return abs(y - (o['a'] + o['b'] * qx)) < 0.25 * s['letter_px']
                return y0 + 0.4 * (y1 - y0) < y < y1 + 0.6 * (y1 - y0)   # the row's marks, under a descender's bowl
            pts = [(x, q['_own']['a'] + q['_own']['b'] * x) for q in imps if on_row(q)
                   for x in ((q['box'][0] + q['box'][2]) / 2,)]
            if o:
                pts.append((cx, o['a'] + o['b'] * cx))
            if len(pts) >= 3 and np.ptp([p[0] for p in pts]) > 0:
                b, a = np.polyfit(*zip(*pts), 1)
            elif o:
                a, b = o['a'], o['b']
            else:
                continue
            r['dash'] = dict(x=round(cx, 2), y=round(float(a + b * cx), 3), slope=round(float(b), 5), marks=len(pts),
                             own=[round(v, 2) for v in o['ends']] if o else None)
        for r in imps:
            del r['_own']
    return meta


def dash_in_frame(q, d, centre):
    """The mark line's height in the template frame (where it crosses under the template's centre) and
    the mark's ends along the template's x axis."""
    a, b, c, dd, tx, ty = q
    sx = a * centre[0] + b * centre[1] + tx
    line = lambda x: d['y'] + d['slope'] * (x - d['x'])
    y = float(IM.to_template(q, [[sx, line(sx)]])[0][1])
    ends = IM.to_template(q, [[e, line(e)] for e in d['own']])[:, 0].tolist() if d.get('own') else None
    return y, ends


def topology_of(mask, piece_min=48, counter_min=96):
    """(pieces, counters) of a raster letter at the 1/8-unit grid, ignoring ink specks under piece_min
    pixels (0.75 square trace units) and the light speckle of printed ink under counter_min (1.5)."""
    from scipy import ndimage as ndi
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    pieces = int((np.bincount(lab.ravel())[1:] >= piece_min).sum())
    bg, nb = ndi.label(np.pad(~mask, 1, constant_values=True))          # the padding is background
    sizes = np.bincount(bg.ravel())
    counters = int(sum(1 for i in range(1, nb + 1) if i != bg[0, 0] and sizes[i] >= counter_min))
    return [pieces, counters]


def ndi_dilate(mask, r):
    from scipy import ndimage as ndi
    return ndi.binary_dilation(mask, iterations=r)


def own_pieces(mask, near):
    """The pieces of ink that lie on the letter (mostly within `near`, its base trace grown a little):
    neighbouring letters' edges inside the frame are dropped."""
    from scipy import ndimage as ndi
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    total = np.bincount(lab.ravel(), minlength=n + 1)
    inside = np.bincount(lab[near].ravel(), minlength=n + 1)
    keep = [i for i in range(1, n + 1) if inside[i] >= 0.6 * total[i]]
    return np.isin(lab, keep)


def average_one(args):
    face, name, base, work, meta = args
    tr = {g['name']: g for g in json.load(open(os.path.join(base, f'{face}.json')))['glyphs']}
    T = {st: IM.trace_mask(tr[name]['rec'], st, PAD) for st in (*STEPS, FINE)}
    m, origin = T[FINE]
    ys, xs = np.nonzero(m)
    tb = (origin[0] + xs.min() * FINE, origin[1] + ys.min() * FINE,
          origin[0] + (xs.max() + 1) * FINE, origin[1] + (ys.max() + 1) * FINE)
    out = {}
    for sheet in SHEETS[face]['sheets']:
        imps = [r for r in meta['impressions'] if r['name'] == name and r['sheet'] == sheet and r['score'] > MIN_SCORE]
        if len(imps) < 2:
            continue
        P = np.load(os.path.join(work, f'ink-{sheet.split()[0]}.npy')).astype(float)
        k = imps[0]['scale'] / 4.0                      # blur and reach in proportion to the sheet's resolution
        qs, first = [], []
        for r in imps:
            x0, y0, x1, y1 = r['box']
            sx = (x1 - x0) / (tb[2] - tb[0]); sy = (y1 - y0) / (tb[3] - tb[1])
            q = [sx, 0, 0, sy, x0 - sx * tb[0], y0 - sy * tb[1]]
            q, _ = IM.register(P, T[0.5][0], origin, 0.5, q, blur=1.0 * k, reach=max(3, int(round(10 * k))))
            q, e = IM.register(P, T[0.25][0], origin, 0.25, q, blur=0.8 * k)
            qs.append(q); first.append(e)
        q_ref = list(qs)
        mean, _, _ = IM.average(P, qs, T[0.25][0].shape, origin, 0.25)
        for _ in range(2):                              # onto the impressions' own mean, frame pinned
            qs = [IM.register(P, mean, origin, 0.25, q, blur=0.6 * k, levels=(2.0, 1.0))[0] for q in qs]
            qs = IM.normalise_frames(qs, q_ref)
            mean, _, _ = IM.average(P, qs, T[0.25][0].shape, origin, 0.25)
        mean, std, stack = IM.average(P, qs, m.shape, origin, FINE)
        spread = [float(np.sqrt(((s - mean) ** 2).mean())) for s in stack]
        dropped = []
        if SHEETS[face].get('reject'):
            # an impression far from the others' consensus (misregistered, damaged or occluded) is left
            # out and the rest re-averaged; once, and never below three
            limit = max(SHEETS[face]['reject'] * float(np.median(spread)), 0.08)
            bad = [i for i, v in enumerate(spread) if v > limit]
            if bad and len(qs) - len(bad) >= 3:
                dropped = [dict(box=imps[i]['box'], rms_to_mean=round(spread[i], 4)) for i in bad]
                imps = [r for i, r in enumerate(imps) if i not in bad]
                qs = [q for i, q in enumerate(qs) if i not in bad]
                first = [e for i, e in enumerate(first) if i not in bad]
                q_ref = [q for i, q in enumerate(q_ref) if i not in bad]
                mean, _, _ = IM.average(P, qs, T[0.25][0].shape, origin, 0.25)
                qs = [IM.register(P, mean, origin, 0.25, q, blur=0.6 * k, levels=(2.0, 1.0))[0] for q in qs]
                qs = IM.normalise_frames(qs, q_ref)
                mean, std, stack = IM.average(P, qs, m.shape, origin, FINE)
                spread = [float(np.sqrt(((s - mean) ** 2).mean())) for s in stack]
        marks = None
        if SHEETS[face].get('frame') == 'dash' and any('dash' in r for r in imps):
            # one linear map for all of the letter's impressions puts the mean in the sheet's own geometry
            # (an impression whose mark its own descender hides still shares it)
            centre = np.array([(tb[0] + tb[2]) / 2, (tb[1] + tb[3]) / 2])
            angles = [float(np.arctan(r['dash']['slope'])) if 'dash' in r else None for r in imps]
            G, removed = IM.sheet_frame(qs, angles)
            qs = [IM.compose(q, G, centre) for q in qs]
            mean, std, stack = IM.average(P, qs, m.shape, origin, FINE)
            spread = [float(np.sqrt(((s - mean) ** 2).mean())) for s in stack]
            got = [dash_in_frame(q, r['dash'], centre) for q, r in zip(qs, imps) if 'dash' in r]
            ys = np.array([y for y, _ in got]); ends = np.array([e for _, e in got if e])
            marks = dict(y=round(float(np.median(ys)), 4), spread=round(float(ys.std()), 4), n=len(ys),
                         ends=[round(float(v), 3) for v in np.median(ends, axis=0)] if len(ends) else None,
                         centre=[round(float(v), 4) for v in centre], **removed)
        tag = f'{name}@{sheet.split()[0]}'
        # each impression's own pieces and counters at its midpoint edge: averaging smears hairline gaps
        # shut, so the letter's topology is read from the impressions, not from their mean
        tops = None
        if SHEETS[face].get('reject'):
            near = ndi_dilate(m > 0.5, int(round(1.5 / FINE)))
            tops = [topology_of(own_pieces(st > 0.5, near)) for st in stack]
            np.save(os.path.join(work, f'stack-{tag}.npy'), stack.astype(np.float16))
        np.save(os.path.join(work, f'mean-{tag}.npy'), mean.astype(np.float32))
        np.save(os.path.join(work, f'std-{tag}.npy'), std.astype(np.float32))
        out[tag] = dict(name=name, sheet=sheet, n=len(imps), boxes=[r['box'] for r in imps],
                        affine=[[round(float(v), 5) for v in q] for q in qs],
                        rms_to_base=[round(v, 4) for v in first], rms_to_mean=[round(v, 4) for v in spread],
                        **({'dropped': dropped} if dropped else {}),
                        **({'impression_topology': tops} if tops else {}),
                        **({'frame': 'dash', 'marks': marks} if marks else {}),
                        origin=[float(v) for v in origin], step=FINE, shape=list(m.shape))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('face', choices=list(SHEETS))
    ap.add_argument('glyphs', nargs='*')
    ap.add_argument('--sources', default=str(ROOT / 'build' / 'research' / 'original-specimens'))
    ap.add_argument('--base', default=None)
    ap.add_argument('--work', default=None)
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--frame', choices=['affine', 'dash'], default=None,
                    help="override the face's frame: 'dash' sets the letters in the sheet's spacing-mark frame")
    args = ap.parse_args()
    if args.frame:
        SHEETS[args.face]['frame'] = None if args.frame == 'affine' else args.frame
    base = args.base or str(ROOT / 'research' / 'round-02' / args.face / 'traces')
    work = args.work or str(ROOT / 'build' / 'production' / args.face)
    os.makedirs(work, exist_ok=True)
    meta_path = os.path.join(work, 'impressions.json')
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else find(args.face, args.sources, base, work)
    if SHEETS[args.face].get('frame') == 'dash' and not any('dash' in r for r in meta['impressions']):
        meta = add_dashes(args.face, base, meta, work)
        json.dump(meta, open(meta_path, 'w'), indent=1)
    names = args.glyphs or sorted({r['name'] for r in meta['impressions'] if r['score'] > MIN_SCORE})
    reg_path = os.path.join(work, 'registration.json')
    reg = json.load(open(reg_path)) if os.path.exists(reg_path) else {}
    with Pool(args.jobs) as pool:
        for out in pool.imap_unordered(average_one, [(args.face, n, base, work, meta) for n in names]):
            for tag, r in out.items():
                reg[tag] = r
                print(f'{tag:14s} n={r["n"]:2d}  to base {np.mean(r["rms_to_base"]):.3f}  spread {np.mean(r["rms_to_mean"]):.3f}'
                      f'  worst {max(r["rms_to_mean"]):.3f}', flush=True)
            json.dump(reg, open(reg_path, 'w'), indent=1)


if __name__ == '__main__':
    main()
