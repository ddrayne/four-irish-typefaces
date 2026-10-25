"""Turn averaged production-sheet impressions into a research round's traces.

usage: python scripts/fit_production.py kilfane --round research/kilfane-production
           [--base research/round-02/kilfane/traces] [--work build/production/kilfane]

Reads scripts/trace_production.py's means (ignored build/) and writes, under ROUND/traces:
the face's trace JSON (base traces, with each letter that has enough production impressions
redrawn from their mean), and evidence.json (the base evidence, each redrawn entry recording
its photograph, hash, sheet, impression boxes, affines, residuals and edge level).

The edge is a level line of the mean, between its backing and its ink. One level per sheet is
chosen so that the redrawn letters keep the base traces' stroke weight on average: the base face's
other letters (all the lowercase) are not on the sheets, and capitals and lowercase must match.
The difference in weight that this removes is recorded as a calibration, not hidden.
"""
import argparse, copy, json, os, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import impressions as IM
from curvefit import curves_to_recording
from curvefit3 import contour_to_curves4

# the designer-style fit used for the research rounds (scripts/kilfane_study.py), in trace units
FIT = dict(cutoff=6, corner_deg=55, rms_tol=.07, max_tol=.22, line_tol=.18, line_bulge=.055, line_min=4.5, snap_deg=1.5)
MIN_IMPRESSIONS = 3
MAX_SPREAD = 0.10          # mean RMS of the registered impressions about their mean; above it the base trace stays
# The sheets whose edges redraw letters. Kilfane's 48pt sheet is white ink on a clear carrier over a
# green backing: its photographed edge is not comparable with printed black ink (at the midpoint
# level it inks 10% lighter than N516, against 5% for the black 30pt sheet, and matching N516 needs
# an implausible edge level), so it is a cross-check only.
REDRAW = {'kilfane': ['30pt S53909'],
          # Carrick's two N514 sheets print one artwork at two sizes (their means differ by no more than
          # one sheet's impressions differ among themselves); the larger is preferred
          'carrick': ['60pt S53914', '36pt S53913']}
PREFER_MARGIN = 0.03       # a later sheet wins only when its impressions agree this much better
# the trace each face's sheets are registered onto, as the evidence names it
BASE = {'kilfane': ('round-02 trace', 'N516'), 'carrick': ('round-5 trace', 'N513; e, f from the flyer')}


def levels(mean, base_mask):
    """The mean's backing and ink levels, away from the edge."""
    from scipy import ndimage as ndi
    inner = ndi.binary_erosion(base_mask, iterations=12)
    outer = ~ndi.binary_dilation(base_mask, iterations=12)
    return float(np.median(mean[outer])), float(np.median(mean[inner]))


def contours_at(mean, level, origin, step, base_mask=None):
    """Closed level lines of the mean; with base_mask, only those that are part of the letter (the
    sheet's spacing marks sit at the same place under every impression, so they survive averaging)."""
    from skimage import measure
    out = []
    for c in measure.find_contours(np.pad(mean, 2), level):
        if base_mask is not None:
            rr, cc = np.clip((c[:, 0] - 2).astype(int), 0, base_mask.shape[0] - 1), np.clip((c[:, 1] - 2).astype(int), 0, base_mask.shape[1] - 1)
            near = np.zeros_like(base_mask); near[rr, cc] = True
            from scipy import ndimage as ndi
            if (ndi.binary_dilation(base_mask, iterations=24) & near).sum() < 0.8 * near.sum():
                continue
        xy = np.column_stack((origin[0] + (c[:, 1] - 2 + 0.5) * step, origin[1] + (c[:, 0] - 2 + 0.5) * step))
        if np.linalg.norm(xy[0] - xy[-1]) > 1e-6:
            continue                                            # open: runs off the frame
        area = abs(np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - xy[:, 1] * np.roll(xy[:, 0], -1)) / 2)
        if area >= 6:
            out.append(xy[:-1])
    return out


def contours_with_gaps(mean, lo, hi, level, origin, step, base_mask, gap_level=0.5, band=2):
    """Closed contours at the calibrated level, except where the letter's pieces meet: there the edge
    rises to the midpoint, the physical edge of the print. The calibrated level (below the midpoint, to
    keep the base's weight) fills the hairline gaps between Carrick's pieces, which every impression
    shows; the pieces at the midpoint mark them, a watershed of the mean finds where neighbouring
    pieces meet, and only along that line is the edge raised."""
    from scipy import ndimage as ndi
    from skimage.segmentation import watershed
    norm = (mean - lo) / max(hi - lo, 1e-9)
    cal, mid = norm > level, norm > gap_level
    lab, n = ndi.label(mid, structure=np.ones((3, 3)))
    sizes = np.bincount(lab.ravel())
    markers = np.zeros(lab.shape, int)
    for j, i in enumerate(i for i in range(1, n + 1) if sizes[i] >= 12):
        markers[lab == i] = j + 1
    ws = watershed(-norm, markers, mask=cal)
    meet = np.zeros(cal.shape, bool)
    for k in range(1, markers.max() + 1):
        meet |= (ws == k) & ndi.binary_dilation((ws > 0) & (ws != k))
    B = np.clip(2 * ndi.gaussian_filter(ndi.binary_dilation(meet, iterations=band).astype(float), 1.0), 0, 1)
    field = norm - (level + (gap_level - level) * B)          # its zero line is the edge
    return contours_at(field + 1.0, 1.0, origin, step, base_mask)    # offset: contours_at pads with zeros


SHOWN = 0.25              # a topology the impressions show: in at least this share of them


def shown(tops):
    """The topologies at least SHOWN of the impressions have, most common first, as (pieces, counters).
    A hairline gap can print open in some impressions and shut in others, so more than one may stand."""
    from collections import Counter
    c = Counter(tuple(t) for t in tops)
    return [t for t, k in c.most_common() if k >= SHOWN * len(tops)]


def topology(rec):
    """(pieces, counters) of a trace record, as the build sees it (winding fixed)."""
    import pathops
    from fontTools.pens.areaPen import AreaPen
    from glyphs import contours
    p = pathops.Path(); pen = p.getPen()
    for op, a in rec:
        getattr(pen, op)(*[tuple(x) for x in a])
    p = pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)
    areas = []
    for c in contours(p):
        ap = AreaPen(); c.draw(ap); areas.append(ap.value)
    pos, neg = sum(a > 0 for a in areas), sum(a < 0 for a in areas)
    return (pos, neg) if pos >= neg else (neg, pos)


def lock_frame(rec, base, step=0.125, scales=np.linspace(0.96, 1.04, 81), baseline=None):
    """The uniform scale (about the base's centre) and shift that lay a redrawn letter best over its
    base trace, and the record moved by them. The impressions' affines absorb the photograph's
    perspective, and their scales can drift a percent or two from the base's frame; this puts each
    letter back at the base's size and place, so only its shape comes from the sheet.

    With baseline=(y, target), the letter's own baseline (y in the record, from its sheet's spacing
    marks) is put at target, the base's line: only the scale and the horizontal shift are fitted."""
    from scipy.signal import fftconvolve
    B, (bx, by) = IM.trace_mask(base, step, 8.0)
    pts = np.array([p for _, a in base for p in a], float); c = (pts.min(0) + pts.max(0)) / 2
    move = lambda r, s, t: [(op, tuple(tuple((np.array(p) - c) * s + c + t) for p in a)) for op, a in r]
    best = None
    for s in scales:
        ty = 0.0 if baseline is None else baseline[1] - (c[1] + (baseline[0] - c[1]) * s)
        M, (mx, my) = IM.trace_mask(move(rec, s, (0, ty)), step, 2.0)
        if M.shape[0] >= B.shape[0] or M.shape[1] >= B.shape[1]:
            continue
        corr = fftconvolve(B, M[::-1, ::-1], mode='valid')
        if baseline is None:
            iy, ix = np.unravel_index(np.argmax(corr), corr.shape)
        else:
            iy = int(round((my - by) / step))              # the row that leaves the vertical place as set
            if not 0 <= iy < corr.shape[0]:
                continue
            ix = int(np.argmax(corr[iy]))
        sub = B[iy:iy + M.shape[0], ix:ix + M.shape[1]]
        iou = float((sub * M).sum() / max(((sub + M) > 0).sum(), 1))
        if best is None or iou > best[0]:
            best = (iou, float(s), (bx + ix * step - mx, by + iy * step - my if baseline is None else ty))
    iou, s, t = best
    return move(rec, s, t), dict(scale=round(s, 4), shift=[round(float(t[0]), 3), round(float(t[1]), 3)], iou_to_base=round(iou, 4))


def ink_fraction(mean, level, lo, hi):
    """The share of the frame inked at this edge level (a proxy for stroke weight)."""
    return float((mean > lo + level * (hi - lo)).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('face')
    ap.add_argument('--round', required=True)
    ap.add_argument('--base', default=None)
    ap.add_argument('--work', default=None)
    ap.add_argument('--lock-frame', action='store_true',
                    help="put each redrawn letter back at its base trace's size and place (Study 4)")
    args = ap.parse_args()
    base = args.base or str(ROOT / 'research' / 'round-02' / args.face / 'traces')
    work = args.work or str(ROOT / 'build' / 'production' / args.face)
    meta = json.load(open(os.path.join(work, 'impressions.json')))
    reg = json.load(open(os.path.join(work, 'registration.json')))
    tr = json.load(open(os.path.join(base, f'{args.face}.json')))
    ev = json.load(open(os.path.join(base, 'evidence.json')))
    byname = {g['name']: g for g in tr['glyphs']}

    # which sheet's mean redraws each letter: the larger sheet if it has enough consistent impressions
    use = {}
    for name in sorted({r['name'] for r in reg.values()}):
        ok = [f'{name}@{sh.split()[0]}' for sh in REDRAW[args.face]]
        ok = [t for t in ok if t in reg and reg[t]['n'] >= MIN_IMPRESSIONS and np.mean(reg[t]['rms_to_mean']) <= MAX_SPREAD]
        if ok:
            spread = lambda t: float(np.mean(reg[t]['rms_to_mean']))
            best = min(ok, key=spread)
            use[name] = best if spread(best) < spread(ok[0]) - PREFER_MARGIN else ok[0]

    # one edge level per sheet that keeps the base traces' weight on average
    calibration = {}
    for sheet in {reg[t]['sheet'] for t in use.values()}:
        tags = [t for t in use.values() if reg[t]['sheet'] == sheet]
        data = []
        for t in tags:
            r = reg[t]; mean = np.load(os.path.join(work, f'mean-{t}.npy')).astype(float)
            m, _ = IM.trace_mask(byname[r['name']]['rec'], r['step'], 3.0)
            m = m[:mean.shape[0], :mean.shape[1]] > 0.5
            lo, hi = levels(mean, m)
            data.append((mean, m, lo, hi))
        target = np.mean([m.mean() for _, m, _, _ in data])
        grid = np.linspace(0.1, 0.9, 81)
        got = [np.mean([ink_fraction(mean, g, lo, hi) for mean, _, lo, hi in data]) for g in grid]
        level = float(grid[int(np.argmin(np.abs(np.array(got) - target)))])
        at_half = np.mean([ink_fraction(mean, 0.5, lo, hi) for mean, _, lo, hi in data])
        calibration[sheet] = dict(level=round(level, 3), letters=sorted(reg[t]['name'] for t in tags),
                                  ink_at_half_level_vs_base=round(float(at_half / target - 1), 4))
        print(f'{sheet}: edge level {level:.3f} of the way from backing to ink; at 0.5 the sheet inks '
              f'{100 * (at_half / target - 1):+.1f}% against the base traces')

    # Letraset's spacing marks: where the sheet frame records them, each letter's baseline is its marks'
    # line less the sheet's mark-to-baseline distance, the median over the sheet's sitting letters of
    # how far their feet stand above their marks (round letters overshoot either way)
    from metrics import line_baselines, bounds as rec_bounds
    lines = line_baselines([dict(g) for g in tr['glyphs']])
    sits = {g['name'] for g in tr['glyphs'] if abs(rec_bounds(g['rec'])[3] - lines[g['line_idx']]) <= 1.5}
    for sheet in list(calibration):
        feet = {}
        for t, r in reg.items():
            if r['sheet'] != sheet or r.get('frame') != 'dash' or r['name'] not in sits:
                continue
            mean = np.load(os.path.join(work, f'mean-{t}.npy')).astype(float)
            m, _ = IM.trace_mask(byname[r['name']]['rec'], r['step'], 3.0)
            mm = m[:mean.shape[0], :mean.shape[1]] > 0.5
            lo, hi = levels(mean, mm)
            cs = contours_at(mean, lo + calibration[sheet]['level'] * (hi - lo), r['origin'], r['step'], mm)
            feet[r['name']] = round(r['marks']['y'] - max(float(np.max(np.asarray(c)[:, 1])) for c in cs), 3)
        if feet:
            calibration[sheet]['mark_to_baseline'] = round(float(np.median(list(feet.values()))), 3)
            calibration[sheet]['feet_above_marks'] = feet
            print(f'{sheet}: marks {calibration[sheet]["mark_to_baseline"]:.2f} units under the baseline (median of {len(feet)} letters)')

    out_glyphs, redrawn, kept_base = [], {}, {}
    for g in tr['glyphs']:
        t = use.get(g['name'])
        if not t:
            out_glyphs.append(g); continue
        r = reg[t]; mean = np.load(os.path.join(work, f'mean-{t}.npy')).astype(float)
        m, _ = IM.trace_mask(g['rec'], r['step'], 3.0)
        lo, hi = levels(mean, m[:mean.shape[0], :mean.shape[1]] > 0.5)
        level = calibration[r['sheet']]['level']
        cs = contours_at(mean, lo + level * (hi - lo), r['origin'], r['step'], m[:mean.shape[0], :mean.shape[1]] > 0.5)
        curves = [contour_to_curves4(c, **FIT) for c in cs]
        rec = curves_to_recording(curves)
        # the letter's topology as its impressions show it, where they were read (Carrick); else the base's
        ok = shown(r['impression_topology']) if r.get('impression_topology') else [topology(g['rec'])]
        # where crisp impressions disagree about a hairline gap, the gap is drawn: ink spread closes a
        # drawn gap far more readily than a clean one opens by chance. So the most open topology the
        # impressions show (most pieces less counters) is the letter's.
        ok = [max(ok, key=lambda t: (t[0] - t[1], t[0]))]
        gaps = False
        if topology(rec) not in ok and r.get('impression_topology'):
            mm = m[:mean.shape[0], :mean.shape[1]] > 0.5
            for gl in (0.5, 0.6, 0.7):                 # a finer gap shows only at a stricter level of the mean
                cs = contours_with_gaps(mean, lo, hi, level, r['origin'], r['step'], mm, gap_level=gl)
                rec2 = curves_to_recording([contour_to_curves4(c, **FIT) for c in cs])
                if topology(rec2) in ok:
                    rec, gaps = rec2, gl
                    break
        want = topology(rec) if topology(rec) in ok else ok[0]
        if topology(rec) not in ok:
            # the sheet's resolution can blur shut a small counter the base resolves (Kilfane's Q)
            kept_base[g['name']] = dict(tag=t, base=topology(g['rec']), mean=topology(rec), impressions=want)
            out_glyphs.append(g); continue
        lock = None
        if args.lock_frame:
            base_line = None
            if r.get('frame') == 'dash' and 'mark_to_baseline' in calibration[r['sheet']]:
                base_line = (r['marks']['y'] - calibration[r['sheet']]['mark_to_baseline'], lines[g['line_idx']])
            rec, lock = lock_frame(rec, g['rec'], baseline=base_line)
            if base_line:
                foot = max(p[1] for _, a in rec for p in a)
                lock.update(baseline=dict(source='the sheet\'s spacing marks', marks_y=r['marks']['y'],
                                          mark_to_baseline=calibration[r['sheet']]['mark_to_baseline'],
                                          line=round(base_line[1], 3), foot_below_line=round(foot - base_line[1], 3)),
                            sheet_frame={k: r['marks'][k] for k in ('turn_deg', 'stretch_ratio', 'shear_removed_deg')})
        h = copy.deepcopy(g); h['rec'] = rec
        h['paper'], h['ink'] = lo, hi
        out_glyphs.append(h)
        redrawn[g['name']] = dict(tag=t, level=level, backing=round(lo, 4), ink=round(hi, 4), lock=lock, gaps=gaps,
                                  topology=list(want))

    os.makedirs(os.path.join(args.round, 'traces'), exist_ok=True)
    tr2 = dict(tr); tr2['glyphs'] = out_glyphs
    tr2['source'] = f'Multiple original NIVAL specimens; production-sheet means from {meta["source_id"]}; see evidence.json'
    json.dump(tr2, open(os.path.join(args.round, 'traces', f'{args.face}.json'), 'w'))
    ev2 = copy.deepcopy(ev)
    ev2['source_hashes'][meta['photo']] = meta['sha256']
    ev2['production_impressions'] = dict(
        method=f'Repeated impressions on the Letraset production sheets, each registered onto the {BASE[args.face][0]} by its '
               'own affine transform (absorbing the photograph\'s local perspective), re-registered twice onto their '
               f'mean with the frame pinned to the {BASE[args.face][0]}, averaged on a 1/8 trace-unit grid; edge at one level '
               'per sheet between the mean\'s backing and ink; fitted with curvefit3.contour_to_curves4.',
        fit=FIT, min_impressions=MIN_IMPRESSIONS, max_spread=MAX_SPREAD, calibration=calibration,
        base_kept_for_topology={n: dict(sheet=reg[d['tag']]['sheet'], base_pieces_counters=d['base'],
                                        mean_pieces_counters=d['mean']) for n, d in kept_base.items()},
        caveat='The impressions are one artwork printed many times: averaging lowers print and photographic noise; it is '
               f'not independent confirmation of the design. Proportions and placement remain those of the {BASE[args.face][0]}.')
    for e in ev2['glyphs']:
        d = redrawn.get(e['name'])
        if not d:
            continue
        r = reg[d['tag']]
        frame = e.get('source', 'the flyer trace (sources/traced)')     # e and f were retained flyer traces
        e.update(status='candidate', source_id=meta['source_id'], sheet=r['sheet'], proportion_source=frame,
                 source=f'{meta["photo"]} ({r["sheet"].split()[0]} sheet, mean of {r["n"]} impressions) over {frame}',
                 impressions=r['n'], boxes=r['boxes'], affine=r['affine'], rms_to_base=r['rms_to_base'],
                 rms_to_mean=r['rms_to_mean'], edge_level=d['level'], mean_backing=d['backing'], mean_ink=d['ink'],
                 note=f'Production-sheet mean; proportions and placement from the {BASE[args.face][0]} ({BASE[args.face][1]}).')
        if d.get('lock'):
            e['frame_lock'] = d['lock']
        if d.get('gaps'):
            e['gaps_from_impressions'] = dict(topology=d['topology'], gap_level=d['gaps'], note='The mean, at the weight-matching edge, '
                'fills hairline gaps between the letter\'s pieces that its impressions show; along the line '
                'where the pieces meet the edge is raised to gap_level instead.')
    json.dump(ev2, open(os.path.join(args.round, 'traces', 'evidence.json'), 'w'), indent=1, ensure_ascii=False)
    for extra in ('pieces.json', 'source-regions.json', 'mark-audit-regions.json', 'punctuation.json', 'mark-evidence.json', 'mark-regions.json'):
        src = os.path.join(base, extra)
        if os.path.exists(src):
            open(os.path.join(args.round, 'traces', extra), 'w').write(open(src).read())
    print('redrawn from production impressions:', ', '.join(sorted(redrawn)) or 'none')
    for n, d in sorted(redrawn.items()):
        if d.get('lock'):
            print(f'  {n}: frame lock scale {d["lock"]["scale"]:.4f}, shift {d["lock"]["shift"]}, overlap {d["lock"]["iou_to_base"]:.3f}')
    for n, d in sorted(kept_base.items()):
        print(f'  {n}: base kept, the mean has {d["mean"]} pieces/counters against {d["base"]}')


if __name__ == '__main__':
    main()
