"""Trace each glyph from the agreement of two prints of the same artwork, not from one print's noise.

usage: python scripts/consensus_trace.py tuam --output ROUND/traces [--report build/tuam-judgement/consensus]

Tuam Uncial's alphabet survives in two reproductions of the same lettering: N46 (NIVAL's copy of the
flyer, a photocopy: large, but its edges are ragged with toner and its ink is speckled) and N45 (the
competition catalogue, offset printed from another paste-up: smaller, with clean edges). Round 3
traced every glyph from N46 alone, so its outlines carry the photocopy's raggedness. Here each glyph's
ink is read from both prints and averaged in N46's own pixel frame, so what both prints agree on is
kept and what only one prints is halved:

- each print's ink field is its named components' coverage (source_study.component_field), at its own
  paper and ink levels, so neither print's weight is privileged;
- N45 is mapped onto N46 by one similarity transform for the whole alphabet (a shared scale and
  rotation, the median of the per-glyph estimates, so no letter is stretched to fit) and a
  translation per letter (the two paste-ups place their letters independently);
- the mean of the two fields is traced through kilfane_study.trace_region at N46's calibration, row
  baselines and boxes, so every glyph keeps round 3's frame, with round 3's 0.8-pixel blur;
- the topology (pieces and counters) of each print and of the mean is recorded, and the traced glyph
  takes the topology decided for it (TOPOLOGY below, from the evidence boards): where the prints agree,
  theirs; where they do not, the cut or slit N45 prints and N46's blur fills, or solid ink where N46
  alone has a pinhole. It is reached by taking N45's ink in the smallest region where the two disagree,
  and the blur is left out only where it would close a decided cut.

The traces are written in the round-3 format with an evidence.json that records, per glyph, both
sources' boxes, labels and hashes, the transform and its residual, how far the two prints' edges
differ and the topology decision; and the face's construction decisions (`constructions`), which
build_original_study reads.
"""
import argparse, copy, hashlib, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from metrics import line_baselines
from kilfane_study import trace_region
from source_study import component_field, contour_topology

N46, N45 = 'competition-advert-1.jpg', 'competition-brochure-2.jpg'
FACES = {'tuam': dict(base=ROOT / 'research' / 'round-03' / 'tuam' / 'traces', primary=N46, check=N45,
                      ids={N46: 'N46', N45: 'N45'},
                      # read by build_original_study.study_class: construction, not tracing, decisions
                      constructions=dict(
                          own_acutes=['aacute', 'eacute', 'iacute', 'oacute', 'uacute'],
                          own_acutes_reason='Both prints set each fada as drawn for its letter: on i a short acute '
                              '(0.43 x-height wide against 0.68 on the others) right of the stem, on o one set right '
                              'of centre. The composites keep each traced acute and its place across the letter; the '
                              'gap above the letter stays the builder\'s uniform one (the traced gaps vary by print). '
                              'a\'s acute touches the bowl on both prints, so a takes the shared acute at a\'s place.',
                          brace='pointed',
                          brace_reason='Braces are not on the specimens. The stroked construction ended the tip inside '
                              'the stems\' outer edge, cutting a notch into the waist; drawn instead with a point.'),
                      # the independent evidence the topology decisions rest on (not traced from)
                      checks=[
                          dict(id='B2 fig. 206', what='Tuam Uncial Letraset sheet S53912, 48 pt, c. 1980 (production)',
                               where='Bolger 2017 volume 2, PDF page 164; pdfimages JPEG 590 x 900, SHA-256 '
                                     '2ea8c4401b68e2435b080cb37d976347086f1acc404da5194b1488ef50b8b8aa',
                               result='sheet-check.json (scripts/tuam_sheet_check.py): n 9 of 9 impressions in two '
                                      'pieces, h 10 of 10, f 7 of 7, u 13 of 13, r 7 of 8, u-acute 2 of 2 in three; v, w, '
                                      'x, e and o in one (x-height about 20 px: cuts narrower than about two N45 pixels '
                                      'do not separate). The means of the v and w impressions show a light seam at '
                                      'the cut N45 prints; the mean of the x impressions (crossed, not cut) shows none.'),
                          dict(id='B2 figs 205b-c', what='Hayes\'s development work with the repro camera, 1974-78',
                               where='Bolger 2017 volume 2, PDF pages 162-163 (205b rotated, 205c a mirrored negative)',
                               result='Earlier drawings, not the final letters (205c\'s b is a capital B form), but the '
                                      'same construction: the hooks of a, d, g, p, q and s stop short of the next stroke '
                                      'and the arches of h, m and n stand off their stems; 205c\'s first v is cut at '
                                      'the vertex.'),
                          dict(id='N47, N44', what='the competition advert\'s second sheet and the brochure\'s cover',
                               where='research/downloads.json', result='neither prints Tuam Uncial')])}

# Where the two prints disagree about a glyph's pieces or counters, the drawing is decided here, from
# the evidence boards (build/judgement/tuam), the production sheet and Hayes's own development work.
# Tuam is cut, not joined: the arches of n and m stand apart from their stems on both prints, and
# the hooks of a, b, g, o, 8, 9 and 0 stop short of the next stroke, leaving a slit into the counter,
# on both. N46 is blurred (its white gaps run about a pixel narrower than N45's everywhere, n's
# included, while its stems are as wide), so it fills the narrower cuts of the same construction
# that N45, a crisp offset print, shows. Bolger fig. 206, a photograph of the 48 pt production sheet
# (S53912), confirms the wider ones, and is too coarse (x-height 20 px) for the narrowest. Bolger
# figs 205b and 205c, Hayes's repro-camera development work, draw the same hooks and cuts.
BLUR = 0.8                        # source pixels: round 3's antialiasing blur
SHEET = 'every impression on Bolger fig. 206 (the S53912 48 pt production sheet) prints it in separate pieces'
SLIT = ('the hook stops short of the stem and the slit runs into the counter, as both prints draw it in a, b, g, '
        'o and the figures; N46\'s blur closes it (round 3 traced the pinholes it leaves); fig. 206 cannot resolve '
        'a slit this narrow; figs 205b-c draw the same hooks')
TOPOLOGY = {
    'd': ([1, 0], 'N45: ' + SLIT),
    'p': ([1, 0], 'N45: ' + SLIT),
    'q': ([1, 0], 'N45: ' + SLIT),
    's': ([1, 0], 'N45: both hooks of the spine stop short and both counters open, as the slits of a and g do; '
                  'N46\'s blur closes them'),
    'six': ([1, 0], 'N45: the bowl\'s hook stops short of the stem, as the 9\'s does on both prints; N46\'s blur closes it'),
    'f': ([2, 0], 'N45: the flag is cut from the stem; ' + SHEET),
    'h': ([2, 0], 'N45: the arch is cut from the stem, as n\'s is on both prints; ' + SHEET),
    'r': ([2, 0], 'N45: the bowl and leg are cut from the stem; ' + SHEET),
    'u': ([2, 0], 'N45: the bowl is cut from the right stem (u is n turned); ' + SHEET),
    'v': ([2, 0], 'N45: the thin stroke is cut from the thick at the vertex; the mean of the four fig. 206 '
                  'impressions shows a light seam there (x, drawn without a cut, shows none); fig. 205c\'s first v '
                  'draws the cut'),
    'w': ([3, 0], 'N45: each thin stroke is cut from the thick one before it, as in v; the mean of the four '
                  'fig. 206 impressions shows a light seam at the right-hand cut'),
    'five': ([2, 0], 'N45: the flag is cut from the stroke below it, as f\'s flag is; a fig. 206 impression shows '
                     'the seam'),
    'dollar': ([1, 2], 'N46\'s third counter is a toner dropout in the lower terminal; N45 prints it solid'),
    'aacute': ([1, 0], 'as a (the slit open); the acute touches the bowl on both prints'),
    'eacute': ([2, 1], 'N45: the acute stands clear of the e, as on every é of fig. 206; N46\'s blur joins them'),
    'iacute': ([2, 0], 'N45: the acute stands clear of the stem, as on every í of fig. 206; N46\'s blur joins them'),
    'uacute': ([3, 0], 'as u (the bowl cut from the stem), with the acute apart'),
}


def topo_distance(t, target):
    return abs(t[0] - target[0]) + abs(t[1] - target[1])


def fix_topology(field, clean, target, max_steps=12):
    """Bring the mean field to the decided topology by taking the clean print's (N45's) ink exactly where
    the two disagree in a way that matters: a cut or slit the mean has closed, or a speck or pinhole only one
    print has. Each step tries every region where the field and the clean print disagree (paper in one, ink
    in the other) and keeps the smallest that moves the topology towards the target."""
    steps = []
    for _ in range(max_steps):
        top = list(contour_topology(field))
        if top == list(target):
            return field, steps
        best = None
        for kind, mask in (('open', (clean < 0.5) & (field >= 0.5)), ('fill', (clean >= 0.5) & (field < 0.5))):
            lab, n = ndi.label(mask, structure=np.ones((3, 3)))
            for i in range(1, n + 1):
                reg = ndi.binary_dilation(lab == i, iterations=1)
                trial = field.copy()
                trial[reg] = np.minimum(field[reg], clean[reg]) if kind == 'open' else np.maximum(field[reg], clean[reg])
                t = list(contour_topology(trial))
                key = (topo_distance(t, target), int(reg.sum()))
                if key[0] < topo_distance(top, target) and (best is None or key < best[0]):
                    best = (key, kind, trial, reg, t)
        if best is None:
            raise ValueError(f'cannot reach topology {target} from {top}')
        (_, area), kind, field, reg, t = best
        ys, xs = np.nonzero(reg)
        steps.append(dict(op=kind, pixels=area, at_px=[float(xs.mean()), float(ys.mean())], topology=t))
    raise ValueError('topology not reached in the allowed steps')


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    return float((a * b).sum() / max(np.sqrt((a * a).sum() * (b * b).sum()), 1e-9))


def centroid(f):
    yy, xx = np.mgrid[:f.shape[0], :f.shape[1]]
    return np.array([(f * yy).sum(), (f * xx).sum()]) / max(f.sum(), 1e-9)


def warp(f_mov, shape, c_ref, c_mov, s, th, t):
    """N45's field resampled on N46's crop grid: N46 pixel p (row, col) -> N45 pixel
    s R(th) (p - c_ref) + c_mov + t."""
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    A = s * R
    off = c_mov + np.asarray(t) - A @ c_ref
    return ndi.affine_transform(f_mov, A, offset=off, output_shape=shape, order=1, cval=0.0)


def register(f_ref, f_mov, s0, th0=0.0, fixed=None):
    """(s, th, ty, tx) maximising correlation; with `fixed` = (s, th) only the translation moves."""
    c_ref, c_mov = centroid(f_ref), centroid(f_mov)
    if fixed is None:
        cost = lambda q: -ncc(f_ref, warp(f_mov, f_ref.shape, c_ref, c_mov, q[0], q[1], q[2:]))
        best = None
        for ds in (0.97, 1.0, 1.03):
            r = minimize(cost, [s0 * ds, th0, 0.0, 0.0], method='Powell',
                         options=dict(xtol=1e-4, ftol=1e-6, maxiter=4000))
            if best is None or r.fun < best.fun:
                best = r
        s, th, ty, tx = best.x
    else:
        s, th = fixed
        cost = lambda q: -ncc(f_ref, warp(f_mov, f_ref.shape, c_ref, c_mov, s, th, q))
        r = minimize(cost, [0.0, 0.0], method='Powell', options=dict(xtol=1e-4, ftol=1e-6))
        ty, tx = r.x; best = r
    return dict(scale=float(s), rotation=float(th), shift=[float(ty), float(tx)], c_ref=c_ref.tolist(),
                c_mov=c_mov.tolist(), ncc=float(-best.fun))


def signed_distance(f):
    """Signed distance (pixels) to the field's 0.5 edge, negative in the ink; zero on the edge itself
    (half-way between the last ink and the first paper pixel)."""
    A = f > 0.5
    return np.where(A, -(ndi.distance_transform_edt(A) - 0.5), ndi.distance_transform_edt(~A) - 0.5)


def edge_difference(f_a, f_b):
    """Mean absolute and signed distance (pixels) from b's 0.5 edge (sub-pixel contour points) to a's;
    positive when b's ink lies outside a's (b bolder)."""
    from skimage import measure
    sd = signed_distance(f_a)
    pts = [c for c in measure.find_contours(f_b, 0.5)]
    if not pts:
        return 0.0, 0.0
    pts = np.vstack(pts)
    v = ndi.map_coordinates(sd, pts.T, order=1)
    return float(np.mean(np.abs(v))), float(np.mean(v))


def topology(f):
    return list(contour_topology(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('face', choices=FACES)
    ap.add_argument('--sources', type=Path, default=ROOT / 'build' / 'research' / 'original-specimens')
    ap.add_argument('--output', type=Path)
    ap.add_argument('--report', type=Path, help='a folder for the per-glyph fields (build/ only: archive pixels)')
    ap.add_argument('--glyphs', nargs='*')
    args = ap.parse_args()
    cfg = FACES[args.face]
    manifest = {a['path']: a['sha256'] for a in json.loads((ROOT / 'research' / 'downloads.json').read_text())['assets']}
    images, hashes = {}, {}
    for f in (cfg['primary'], cfg['check']):
        data = (args.sources / f).read_bytes(); digest = hashlib.sha256(data).hexdigest()
        if digest != manifest['original-specimens/' + f]:
            raise ValueError('source image changed: ' + f)
        hashes[f] = digest; images[f] = np.asarray(Image.open(args.sources / f).convert('L'))
    base_ev = json.loads((cfg['base'] / 'evidence.json').read_text(encoding='utf-8'))
    regions = json.loads((cfg['base'] / 'source-regions.json').read_text(encoding='utf-8'))
    lookup = {f: {r['name']: r for r in rs} for f, rs in regions.items()}
    cal = base_ev['calibration']
    s0 = cal[cfg['check']]['scale'] / cal[cfg['primary']]['scale']
    candidates = [g['name'] for g in base_ev['glyphs'] if g['status'] == 'candidate']
    names = args.glyphs or candidates
    fields = {}
    for n in candidates:
        f46, o46, p46, i46 = component_field(images[cfg['primary']], lookup[cfg['primary']][n])
        f45, o45, p45, i45 = component_field(images[cfg['check']], lookup[cfg['check']][n])
        fields[n] = (f46, o46, f45, o45, (p46, i46), (p45, i45))
    # one similarity for the alphabet: the median of the per-glyph scale and rotation, over every glyph
    free = {n: register(fields[n][0], fields[n][2], s0) for n in candidates}
    S = float(np.median([r['scale'] for r in free.values()])); TH = float(np.median([r['rotation'] for r in free.values()]))
    spread = dict(scale=float(np.std([r['scale'] for r in free.values()])),
                  rotation_deg=float(np.degrees(np.std([r['rotation'] for r in free.values()]))))
    print(f'shared N46 -> N45 similarity: scale {S:.4f} (calibration ratio {s0:.4f}), rotation {np.degrees(TH):.3f} deg; '
          f'per-glyph scale spread {spread["scale"]:.4f}, rotation spread {spread["rotation_deg"]:.3f} deg', flush=True)
    legacy = json.loads((ROOT / 'sources' / 'traced' / f'{args.face}.json').read_text(encoding='utf-8'))
    old = legacy['glyphs']; oldbase = line_baselines(old); by_old = {g['name']: g for g in old}
    base_tr = {g['name']: g for g in json.loads((cfg['base'] / f'{args.face}.json').read_text(encoding='utf-8'))['glyphs']}
    by_ev = {g['name']: g for g in base_ev['glyphs']}
    scale, bases = cal[cfg['primary']]['scale'], cal[cfg['primary']]['baselines']
    traces, evidence = {}, {}
    for n in names:
        f46, o46, f45, o45, lv46, lv45 = fields[n]
        reg = register(f46, f45, S, fixed=(S, TH))
        w45 = warp(f45, f46.shape, np.array(reg['c_ref']), np.array(reg['c_mov']), S, TH, reg['shift'])
        mean = 0.5 * (f46 + w45)
        mad, signed = edge_difference(f46, w45)
        tops = {'N46': topology(f46), 'N45': topology(w45), 'mean': topology(mean)}
        if n in TOPOLOGY:
            target, why = TOPOLOGY[n]
        elif tops['N46'] == tops['N45']:
            target, why = tops['N46'], 'both prints agree'
        else:
            raise ValueError(f'{n}: the prints disagree ({tops}) and no decision is recorded')
        fixed, steps = fix_topology(mean, w45, target)
        kept_sharp = []
        page = lambda ss: [dict({k: v for k, v in s.items() if k != 'at_px'},
                                at_N46_px=[round(s['at_px'][0] + o46[0], 1), round(s['at_px'][1] + o46[1], 1)]) for s in ss]

        def smooth(field):
            # round 3's 0.8-pixel blur everywhere; only where it would close a decided cut or slit is the
            # unblurred field kept, in the smallest region that keeps it open
            out, keep = fix_topology(ndi.gaussian_filter(field, BLUR), field, target)
            kept_sharp.extend(keep)
            return out, BLUR
        r46 = lookup[cfg['primary']][n]
        rec = trace_region(images[cfg['primary']], r46, scale, bases[str(r46['row'])], copy.deepcopy(by_old[n]),
                           oldbase[by_old[n]['line_idx']], field_function=lambda *_: (fixed, o46, lv46[0], lv46[1]),
                           smoothing_function=smooth)
        traces[n] = rec
        r45 = lookup[cfg['check']][n]
        evidence[n] = dict(
            name=n, status='candidate', method='consensus', source=cfg['primary'], source_id='N46+N45',
            box=r46['box'], labels=r46['labels'], row_box=r46['row_box'], scale=scale,
            source_baseline=bases[str(r46['row'])], old_baseline=oldbase[by_old[n]['line_idx']],
            check=dict(source=cfg['check'], source_id='N45', box=r45['box'], labels=r45['labels'], row_box=r45['row_box'],
                       transform=dict(kind='similarity, N46 crop pixel (row, col) -> N45 crop pixel',
                                      scale=round(S, 5), rotation_deg=round(float(np.degrees(TH)), 4),
                                      shift_px=[round(v, 3) for v in reg['shift']],
                                      centre_N46_px=[round(v + o, 3) for v, o in zip(reg['c_ref'], (o46[1], o46[0]))],
                                      centre_N45_px=[round(v + o, 3) for v, o in zip(reg['c_mov'], (o45[1], o45[0]))]),
                       correlation=round(reg['ncc'], 4), free_fit=dict(scale=round(free[n]['scale'], 4),
                                                                        rotation_deg=round(float(np.degrees(free[n]['rotation'])), 3))),
            edges=dict(mean_abs_px=round(mad, 3), mean_signed_px=round(signed, 3),
                       note='N45\'s 0.5 edge against N46\'s, in N46 pixels (one is about 10.6 font units); '
                            'positive where N45 prints bolder. The traced edge lies half-way between them.'),
            topology=dict(prints={'N46': tops['N46'], 'N45': tops['N45']}, mean=tops['mean'], decided=list(target),
                          decision=why, steps=page(steps), kept_unblurred=page(kept_sharp)),
            smoothing_sigma=rec['source_smoothing_sigma'],
            uncertainty_font_units=round(mad * 545 / 19.29 / scale / 2, 1) if args.face == 'tuam' else None,
            round3=dict(source_id=by_ev[n].get('source_id'), smoothing_sigma=by_ev[n].get('smoothing_sigma')))
        print(f'{n:10s} ncc {reg["ncc"]:.3f}  edges differ {mad:.2f}px (N45 {signed:+.2f})  N46 {tops["N46"]} N45 {tops["N45"]} '
              f'mean {tops["mean"]} -> {list(target)} in {len(steps)} steps, sigma {rec["source_smoothing_sigma"]}', flush=True)
        if args.report:
            args.report.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(args.report / f'{n}.npz', f46=f46, w45=w45, mean=mean, fixed=fixed, origin=np.array(o46))
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        doc = json.loads((cfg['base'] / f'{args.face}.json').read_text(encoding='utf-8'))
        doc['source'] = 'NIVAL N46 and N45, averaged in N46\'s frame; identities, transforms and decisions in evidence.json'
        doc['glyphs'] = [traces.get(g['name'], g) for g in doc['glyphs']]
        report = dict(
            face=args.face, status='research candidate; not release', method=__doc__.strip().split('\n\n')[0],
            source_hashes=hashes, calibration=cal,
            constructions=cfg.get('constructions', {}), independent_checks=cfg.get('checks', []),
            shared_transform=dict(scale=round(S, 5), rotation_deg=round(float(np.degrees(TH)), 4),
                                  calibration_ratio=round(s0, 5), per_glyph_spread=spread,
                                  note='The median of free per-glyph fits; each glyph then moves by translation only.'),
            glyphs=[evidence.get(g['name'], by_ev[g['name']]) for g in base_ev['glyphs']],
            limitations=['N46 and N45 reproduce the same lettering and may share intermediate copies: their agreement is not '
                         'independent confirmation. Bolger fig. 206 (the production sheet) is the independent check, at a '
                         'third of their resolution.',
                         'The traced edge is the mean of the two prints at each print\'s own paper and ink levels.',
                         'Legacy builder text-height regularisation and modern extensions remain.'])
        (args.output / f'{args.face}.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        (args.output / 'evidence.json').write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
        (args.output / 'source-regions.json').write_text(json.dumps(regions, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
