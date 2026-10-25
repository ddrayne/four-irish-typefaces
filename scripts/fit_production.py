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
REDRAW = {'kilfane': ['30pt S53909']}


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


def lock_frame(rec, base, step=0.125, scales=np.linspace(0.96, 1.04, 81)):
    """The uniform scale (about the base's centre) and shift that lay a redrawn letter best over its
    base trace, and the record moved by them. The impressions' affines absorb the photograph's
    perspective, and their scales can drift a percent or two from the base's frame; this puts each
    letter back at the base's size and place, so only its shape comes from the sheet."""
    from scipy.signal import fftconvolve
    B, (bx, by) = IM.trace_mask(base, step, 8.0)
    pts = np.array([p for _, a in base for p in a], float); c = (pts.min(0) + pts.max(0)) / 2
    move = lambda r, s, t: [(op, tuple(tuple((np.array(p) - c) * s + c + t) for p in a)) for op, a in r]
    best = None
    for s in scales:
        M, (mx, my) = IM.trace_mask(move(rec, s, (0, 0)), step, 2.0)
        if M.shape[0] >= B.shape[0] or M.shape[1] >= B.shape[1]:
            continue
        corr = fftconvolve(B, M[::-1, ::-1], mode='valid')
        iy, ix = np.unravel_index(np.argmax(corr), corr.shape)
        sub = B[iy:iy + M.shape[0], ix:ix + M.shape[1]]
        iou = float((sub * M).sum() / max(((sub + M) > 0).sum(), 1))
        if best is None or iou > best[0]:
            best = (iou, float(s), (bx + ix * step - mx, by + iy * step - my))
    iou, s, t = best
    return move(rec, s, t), dict(scale=round(s, 4), shift=[round(t[0], 3), round(t[1], 3)], iou_to_base=round(iou, 4))


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
        for sh in REDRAW[args.face]:
            r = reg.get(f'{name}@{sh.split()[0]}')
            if r and r['n'] >= MIN_IMPRESSIONS and np.mean(r['rms_to_mean']) <= MAX_SPREAD:
                use[name] = f'{name}@{sh.split()[0]}'; break

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
        if topology(rec) != topology(g['rec']):
            # the sheet's resolution can blur shut a small counter the base resolves (Kilfane's Q)
            kept_base[g['name']] = dict(tag=t, base=topology(g['rec']), mean=topology(rec))
            out_glyphs.append(g); continue
        lock = None
        if args.lock_frame:
            rec, lock = lock_frame(rec, g['rec'])
        h = copy.deepcopy(g); h['rec'] = rec
        h['paper'], h['ink'] = lo, hi
        out_glyphs.append(h)
        redrawn[g['name']] = dict(tag=t, level=level, backing=round(lo, 4), ink=round(hi, 4), lock=lock)

    os.makedirs(os.path.join(args.round, 'traces'), exist_ok=True)
    tr2 = dict(tr); tr2['glyphs'] = out_glyphs
    tr2['source'] = f'Multiple original NIVAL specimens; production-sheet means from {meta["source_id"]}; see evidence.json'
    json.dump(tr2, open(os.path.join(args.round, 'traces', f'{args.face}.json'), 'w'))
    ev2 = copy.deepcopy(ev)
    ev2['source_hashes'][meta['photo']] = meta['sha256']
    ev2['production_impressions'] = dict(
        method='Repeated impressions on the Letraset production sheets, each registered onto the round-02 trace by its '
               'own affine transform (absorbing the photograph\'s local perspective), re-registered twice onto their '
               'mean with the frame pinned to the round-02 trace, averaged on a 1/8 trace-unit grid; edge at one level '
               'per sheet between the mean\'s backing and ink; fitted with curvefit3.contour_to_curves4.',
        fit=FIT, min_impressions=MIN_IMPRESSIONS, max_spread=MAX_SPREAD, calibration=calibration,
        base_kept_for_topology={n: dict(sheet=reg[d['tag']]['sheet'], base_pieces_counters=d['base'],
                                        mean_pieces_counters=d['mean']) for n, d in kept_base.items()},
        caveat='The impressions are one artwork printed many times: averaging lowers print and photographic noise; it is '
               'not independent confirmation of the design. Proportions and placement remain those of the round-02 trace.')
    for e in ev2['glyphs']:
        d = redrawn.get(e['name'])
        if not d:
            continue
        r = reg[d['tag']]
        e.update(status='candidate', source_id=meta['source_id'], sheet=r['sheet'], proportion_source=e['source'],
                 source=f'{meta["photo"]} ({r["sheet"].split()[0]} sheet, mean of {r["n"]} impressions) over {e["source"]}',
                 impressions=r['n'], boxes=r['boxes'], affine=r['affine'], rms_to_base=r['rms_to_base'],
                 rms_to_mean=r['rms_to_mean'], edge_level=d['level'], mean_backing=d['backing'], mean_ink=d['ink'],
                 note='Production-sheet mean; proportions and placement from the round-02 trace (N516).')
        if d.get('lock'):
            e['frame_lock'] = d['lock']
    json.dump(ev2, open(os.path.join(args.round, 'traces', 'evidence.json'), 'w'), indent=1, ensure_ascii=False)
    for extra in ('pieces.json', 'source-regions.json', 'mark-audit-regions.json', 'punctuation.json'):
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
