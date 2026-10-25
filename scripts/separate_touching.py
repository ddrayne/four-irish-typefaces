"""Trace letters that touch their neighbours on the original specimen, at its resolution.

usage: python scripts/separate_touching.py kilfane --traces ROUND/traces [--preview build/judgement/kilfane]

On N516 Kilfane's T touches U and k touches l, so earlier rounds kept their flyer-resolution
traces. Here each pair's fused ink is traced from N516 as round 2 traced every other letter
(scripts/kilfane_study.py: the letter's own ink, sigma 0.8 smoothing, the 0.5 edge, the
designer-style fit, the row's baseline). Only the contact is a construction: each letter's
existing (flyer) outline is laid over N516 at the round's scale to mark its body, and the fused ink
is divided at its narrowest neck (a watershed of the ink's distance map flooded from each body).
Away from the contact the drawing is N516's; the cut is a construction across the neck. The traces are rewritten in place and their
evidence entries record the pair, the registration and the construction.
"""
import argparse, copy, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from curvefit import curves_to_recording
from curvefit3 import contour_to_curves4
from metrics import line_baselines

FIT = dict(cutoff=6, corner_deg=55, rms_tol=.07, max_tol=.22, line_tol=.18, line_bulge=.055, line_min=4.5, snap_deg=1.5)
# each fused pair: the window holding both letters on N516 (pixels) and its row
PAIRS = {'kilfane': [dict(names=('T', 'U'), window=(930, 270, 1180, 420), row=1),
                     dict(names=('k', 'l'), window=(805, 600, 955, 740), row=3)],
         # on N513, x's upper-right piece touches the top of y's left arm
         # Carrick's y is three pieces (arm, stem, tail) and its arm touches x but not its own stem, so
         # every piece of each letter's earlier outline marks its body, not only the largest
         'carrick': [dict(names=('x', 'y'), window=(520, 490, 760, 655), row=2, markers='all')]}
PRIMARY = {'kilfane': 'Kilfane-alphabet-specimen.jpg', 'carrick': 'Carrick-alphabet-specimen.jpg'}
SOURCE_ID = {'kilfane': 'N516', 'carrick': 'N513'}
PRINTS = {'kilfane': 'N47 and N46', 'carrick': 'N47'}            # the other prints on which they touch


def raster(rec, shape, to_px):
    from outline_util import flatten, raster as fill
    return fill(flatten([(op, [tuple(p) for p in a]) for op, a in rec], 16), (shape[1], shape[0]), to_px) > 0


def place(rec, ink, scale, base_y, old_base, x_guess):
    """The x offset (N516 pixels) at which the trace, at the round's scale and on the row's
    baseline, best covers the ink: trace (u, v) -> N516 (x0 + u * scale, base_y + (v - old_base) * scale)."""
    pts = np.array([p for _, a in rec for p in a], float)
    best = None
    for dx in np.arange(x_guess - 40, x_guess + 40, 0.5):
        to_px = lambda q, dx=dx: (dx + q[0] * scale, base_y + (q[1] - old_base) * scale)
        m = raster(rec, ink.shape, to_px)
        score = float((ink * m).sum() - 0.5 * ((1 - ink) * m).sum())
        if best is None or score > best[0]:
            best = (score, dx)
    return best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('face'); ap.add_argument('--traces', type=Path, required=True)
    ap.add_argument('--preview', type=Path)
    args = ap.parse_args()
    tr_path = args.traces / f'{args.face}.json'; ev_path = args.traces / 'evidence.json'
    tr = json.loads(tr_path.read_text()); ev = json.loads(ev_path.read_text())
    legacy = json.loads((ROOT / 'sources' / 'traced' / f'{args.face}.json').read_text())['glyphs']
    oldbase = line_baselines(legacy)
    byname = {g['name']: g for g in tr['glyphs']}
    old_line = {g['name']: g['line_idx'] for g in legacy}
    primary = PRIMARY[args.face]; src = SOURCE_ID[args.face]
    cal = ev['calibration'][primary]; scale = cal['scale']
    gray = np.asarray(Image.open(ROOT / 'build' / 'research' / 'original-specimens' / primary).convert('L')).astype(float)
    evidence = {e['name']: e for e in ev['glyphs']}
    previews = []
    for pair in PAIRS[args.face]:
        x0, y0, x1, y1 = pair['window']
        a = gray[y0:y1, x0:x1]
        base_y = cal['baselines'][str(pair['row'])] - y0
        # the pair's own ink: the components (at round 2's 130 threshold) touching the window's middle rows
        lab, _ = ndi.label(a < 130, structure=np.ones((3, 3)))
        traces = {n: byname[n]['rec'] for n in pair['names']}
        guesses = {pair['names'][0]: 10.0, pair['names'][1]: (x1 - x0) / 2}
        paper = float(np.percentile(a, 90)); inkv = float(np.percentile(a, 3))
        field = np.clip((paper - a) / max(paper - inkv, 1), 0, 1)
        placed, masks = {}, {}
        for n, rec in traces.items():
            pts = np.array([p for _, q in rec for p in q], float)
            x_guess = guesses[n] - pts[:, 0].min() * scale
            dx = place(rec, field, scale, base_y, oldbase[old_line[n]], x_guess)
            placed[n] = dx
            masks[n] = raster(rec, a.shape, lambda q, dx=dx, n=n: (dx + q[0] * scale, base_y + (q[1] - oldbase[old_line[n]]) * scale))
        both = masks[pair['names'][0]] | masks[pair['names'][1]]
        keep = np.isin(lab, [v for v in np.unique(lab[ndi.binary_dilation(both, iterations=3)]) if v])
        permitted = ndi.binary_dilation(keep, iterations=3)
        # divide the fused ink at its narrowest neck: a watershed of the ink's distance map, flooded
        # from each letter's body (its earlier outline, eroded, largest piece)
        from skimage.segmentation import watershed
        first, second = pair['names']
        inked = permitted & (field > 0.5)
        markers = np.zeros(a.shape, int)
        for i, n in enumerate(pair['names']):
            core = ndi.binary_erosion(masks[n], iterations=5) & inked
            cl, k = ndi.label(core)
            if k and pair.get('markers') == 'all':
                sizes = ndi.sum(core, cl, range(1, k + 1))
                markers[np.isin(cl, [j + 1 for j in range(k) if sizes[j] >= 20])] = i + 1
            elif k:
                markers[cl == 1 + int(np.argmax(ndi.sum(core, cl, range(1, k + 1))))] = i + 1
        ws = watershed(-ndi.distance_transform_edt(inked), markers, mask=inked)
        # soft edge pixels go with the nearest divided ink; ink no letter's body reaches (the edge of a
        # neighbour inside the window) goes to neither
        idx = ndi.distance_transform_edt(ws == 0, return_distances=False, return_indices=True)
        owner = ws[idx[0], idx[1]] - 1
        stray = inked & (ws == 0)
        owner[ndi.binary_dilation(stray, iterations=2) & ~(ws > 0)] = -1
        for i, n in enumerate(pair['names']):
            f = np.where(permitted & (owner == i), field, 0.0)
            f = ndi.gaussian_filter(f, .8)
            from skimage import measure
            curves = []
            for c in measure.find_contours(np.pad(f, 2), .5):
                xy = np.column_stack((c[:, 1] - 2, c[:, 0] - 2))
                area = abs(np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - xy[:, 1] * np.roll(xy[:, 0], -1)) / 2)
                if area < 6:
                    continue
                ob = oldbase[old_line[n]]
                uv = np.column_stack(((xy[:-1, 0] - placed[n]) / scale, (xy[:-1, 1] - base_y) / scale + ob))
                curves.append(contour_to_curves4(uv, **FIT))
            g = byname[n]; g['rec'] = curves_to_recording(curves); g['paper'], g['ink'] = paper, inkv
            ys, xs = np.nonzero(f > 0.5)
            box = [int(x0 + xs.min()), int(y0 + ys.min()), int(x0 + xs.max() + 1), int(y0 + ys.max() + 1)]
            evidence[n] = dict(
                name=n, status='candidate', source=primary, box=box, scale=scale,
                method='separated', pair=list(pair['names']), window=list(pair['window']), row=pair['row'],
                source_baseline=cal['baselines'][str(pair['row'])], old_baseline=oldbase[old_line[n]],
                note=f'{first} and {second} touch on {src} (and on {PRINTS[args.face]}). Traced from {src} like every other '
                     f'round-2 letter; the fused ink is divided at its narrowest neck, flooded from each '
                     f'letter\'s body, so the cut across the neck is a construction and the rest is {src}.')
            print(f'{n}: {src} box {box}, {len(curves)} contours', flush=True)
        if args.preview:
            rgb = np.stack([a] * 3, -1).astype(np.uint8)
            cut = (owner == 0) & permitted & (field > 0.5)
            rgb[cut] = (rgb[cut] * 0.5 + np.array([220, 60, 40]) * 0.5).astype(np.uint8)
            cut = (owner == 1) & permitted & (field > 0.5)
            rgb[cut] = (rgb[cut] * 0.5 + np.array([40, 120, 220]) * 0.5).astype(np.uint8)
            previews.append(Image.fromarray(rgb).resize((a.shape[1] * 4, a.shape[0] * 4), Image.NEAREST))
    tr_path.write_text(json.dumps(tr, separators=(',', ':')), encoding='utf-8')
    ev['glyphs'] = [evidence.get(e['name'], e) for e in ev['glyphs']]
    ev_path.write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding='utf-8')
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        for i, p in enumerate(previews):
            p.save(args.preview / f'separated-{"".join(PAIRS[args.face][i]["names"])}.png')


if __name__ == '__main__':
    main()
