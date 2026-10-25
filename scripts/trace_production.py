"""Trace a face's letters from the repeated impressions on its Letraset production sheets.

usage: python scripts/trace_production.py kilfane --sources build/research/original-specimens
           [--base research/round-02/kilfane/traces] [--work build/production/kilfane] [--jobs 4]
           [GLYPH ...]

1. Each sheet's ink map (scripts/impressions.py ink_map), its letters found and named against the
   base traces at one fixed scale per sheet, so a capital is never taken for its lowercase.
2. Every impression of a letter registered onto the base trace by its own affine transform
   (translation search, then coarse-to-fine least squares), then twice onto the impressions' own
   mean with the frame pinned to the base trace's, and averaged on a 1/8-unit grid.
3. The averaged edge: the level halfway between the mean's own backing and ink, as sub-pixel
   contours in base-trace units (scan pixels, y down), ready for the designer-style fitter.

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
SHEETS = {
    'kilfane': dict(photo='Kilfane-Letraset.jpg', source_id='N517', sheets={
        '48pt S53910': dict(channel=0, light_ink=True, letter_px=120, area=(1500, 30000), side=lambda b: not EDGE_30(b)),
        '30pt S53909': dict(channel=1, light_ink=False, letter_px=75, area=(500, 12000), side=EDGE_30)}),
}
SURE = ('E', 'I', 'L', 'H', 'K', 'B', 'F')       # letters no other glyph resembles, for each sheet's scale
MIN_SCORE, STEPS, FINE, PAD = 0.72, (0.5, 0.25), 0.125, 3.0


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def find(face, sources, base, work):
    from PIL import Image
    spec = SHEETS[face]
    photo = os.path.join(sources, spec['photo'])
    im = np.asarray(Image.open(photo))
    tr = {g['name']: g for g in json.load(open(os.path.join(base, f'{face}.json')))['glyphs'] if g['name'] != 'ornament'}
    templates = {n: IM.trace_mask(g['rec'], 0.5, 2) for n, g in tr.items()}
    th = {n: (np.ptp(np.nonzero(m)[0]) + 1) * 0.5 for n, (m, _) in templates.items()}
    found = []
    for sheet, s in spec['sheets'].items():
        p = IM.ink_map(im[..., s['channel']], s['light_ink'], s['letter_px'])
        np.save(os.path.join(work, f'ink-{sheet.split()[0]}.npy'), p.astype(np.float32))
        comps = [c for c in IM.components(p, *s['area'])[0] if s['side'](c['box'])]
        sure = [(c['box'][3] - c['box'][1]) / th[r[0][1]] for c in comps
                for r in [IM.classify(p, c['box'], templates)] if r and r[0][1] in SURE and r[0][0] > 0.75]
        scale = float(np.median(sure))
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
        tag = f'{name}@{sheet.split()[0]}'
        np.save(os.path.join(work, f'mean-{tag}.npy'), mean.astype(np.float32))
        np.save(os.path.join(work, f'std-{tag}.npy'), std.astype(np.float32))
        out[tag] = dict(name=name, sheet=sheet, n=len(imps), boxes=[r['box'] for r in imps],
                        affine=[[round(float(v), 5) for v in q] for q in qs],
                        rms_to_base=[round(v, 4) for v in first], rms_to_mean=[round(v, 4) for v in spread],
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
    args = ap.parse_args()
    base = args.base or str(ROOT / 'research' / 'round-02' / args.face / 'traces')
    work = args.work or str(ROOT / 'build' / 'production' / args.face)
    os.makedirs(work, exist_ok=True)
    meta_path = os.path.join(work, 'impressions.json')
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else find(args.face, args.sources, base, work)
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
