"""Céilí Study 4's traces: each letter drawn from the consensus of its prints (scripts/ceili_prints.py).

usage: python scripts/trace_ceili_judgement.py --round research/ceili-judgement [--work build/ceili-judgement/prints]

For every letter (each is printed on both N46 and N45), the outline is one level of the two prints' mean
(each print taken at its own midpoint), fitted with the designer-style fit of the research rounds. The level is the face's, not the
letter's: the one at which the means' stems are as wide as the median high-resolution print's (N46, the
N44 heading and the sheet samples print their stems alike, about 3% lighter than Study 3 traced them;
N45's alphabet about 12% lighter),
which also leaves the hairlines near the median print's. The prints cannot settle the weight absolutely;
this is recorded as a calibration. Every print was registered onto Study 3's trace and the
averaged prints' mean correction removed, so the letter keeps Study 3's size and place: only the shape
comes from the consensus (fit_production.lock_frame's overlap fit is recorded as a check).

Topology is the prints', not the mean's. Where every averaged print agrees (pieces and counters), that
is the drawing; averaging two prints a fraction of a pixel apart can still thin a hairline join below
the edge level, so where the mean breaks a join or opens a counter that every print has, the edge drops,
along the bridging pixels only, to the highest level at which the mean has the prints' topology (and,
the other way, rises where the mean fills a gap every print shows). Where the prints disagree, the
letter's entry in DECISIONS says which is drawing and why.

Writes ROUND/traces: ceili.json (Study 3's trace file with the redrawn letters), evidence.json (Study 3's
evidence with each redrawn entry recording its prints, their hashes, boxes, transforms and residuals,
the topology decision and the frame check), source-regions.json, and punctuation.json (the named pieces,
from the same consensus, and the identification of the three upper pieces).
"""
import argparse, copy, json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import ceili_prints as CP
import fit_production as FP
import trace_production as TP
import impressions as IM
from curvefit import curves_to_recording
from curvefit3 import contour_to_curves4

FIT = FP.FIT
# letters whose averaged prints disagree about a gap or counter, or need a recorded call
DECISIONS = {
    'ampersand': dict(topology=[1, 1], why=(
        'The prints disagree. Where the lower bowl\'s terminal meets the diagonal, the leaflet (N46, and the flyer scan) '
        'joins them and closes the counter; the brochure (N45, and Trinity\'s copy B2: the same plate) leaves a sliver '
        'of paper about one source pixel (10 font units) wide. A gap one print shows and another fills is taken as print: '
        'the join is kept closed, as N46 draws it and Study 3 has it. Against this: both brochure copies show the gap, and '
        'the photocopy prints about 10% heavier, enough to close a drawn sliver. Open question.')),
}


def raster_topology(mask, near):
    return tuple(TP.topology_of(TP.own_pieces(mask, near)))


def rec_topology(rec):
    """(pieces, counters) of a trace record, from its raster (fit_production.topology guesses the winding
    from which sign is commoner, which miscounts a letter with more counters than pieces: 8, $)."""
    return tuple(TP.topology_of(IM.trace_mask(rec, CP.FINE, CP.PAD)[0] > 0.5))


def keep_topology(mean, want, near, edge, floor=0.1):
    """Fields whose `edge` level has topology `want`, narrowest change first. A join the mean thins below
    the edge is bridged where a closing of the outline by a disc of radius r fills it (only a gap narrower
    than 2r fills, and only where the mean still has ink above `floor`); a gap the mean fills is opened
    where an opening by the disc removes a neck (only where the mean is below the edge plus 0.3). The fit
    smooths a thin bridge, so the caller takes the first field whose fitted outline keeps the topology.
    Yields (field, record)."""
    from skimage.morphology import disk
    base = mean > edge
    if raster_topology(base, near) == want:
        yield mean, None
    for sign in (+1, -1):
        for r in range(1, int(round(1.5 / CP.FINE)) + 1):
            if sign > 0:
                cand = ndi.binary_closing(np.pad(base, r + 1), structure=disk(r))[r + 1:-r - 1, r + 1:-r - 1] & ~base & (mean > floor)
            else:
                cand = base & ~ndi.binary_opening(base, structure=disk(r)) & (mean < edge + 0.3)
            lab, n = ndi.label(cand, structure=np.ones((3, 3)))
            m, used = base.copy(), []
            # one connected piece at a time, those nearest the edge level first, until the topology is the prints'
            for i in sorted(range(1, n + 1), key=lambda i: -sign * float(mean[lab == i].mean())):
                m = (m | (lab == i)) if sign > 0 else (m & ~(lab == i))
                used.append(i)
                if raster_topology(m, near) == want:
                    break
            if raster_topology(m, near) != want:
                continue
            region = np.isin(lab, used)
            B = np.clip(2 * ndi.gaussian_filter(ndi.binary_dilation(region, iterations=1).astype(float), 0.7), 0, 1)
            field = np.maximum(mean, B * (edge + 0.2)) if sign > 0 else np.minimum(mean, 1 - B * (1.2 - edge))
            yield field, dict(kind='bridged where the mean thins a join every print has' if sign > 0 else
                              'opened where the mean fills a gap every print shows',
                              radius=round(r * CP.FINE, 3), pixels=int(region.sum()), step=CP.FINE)


SLIVER = 0.3        # trace units: half the thickness of a disagreement that is only edge noise
BLOB = 0.5          # trace units: half the thickness of a lump of N46's toner (thinner, it is N46's weight)
NOTCH = 0.75        # trace units: a disagreement the other print's outline closes over at this radius is a notch
LARGEST = 1.0       # stems: a disagreement thicker than this is left to the mean and reported


def disagreements(field, prints, votes, edge, step, stem, near):
    """Where N46 and N45 (`prints`: their names and maps, each at its own midpoint) disagree by more than
    edge noise, which print is drawing. A region one print inks and the other leaves white is
      - a notch, gap or dropout in the other print when the other's outline, closed by a disc of NOTCH,
        covers it: it is drawn (a gap or notch one print shows and another fills is print);
      - otherwise a protrusion of the inking print beyond the other. The cover heading N44, which is not
        averaged, votes where it prints the letter. Without a vote, a protrusion of N45 (a tip or spur the
        photocopy lost: it loses fine ends, the offset print does not) is drawn, and a lump of N46's toner
        thicker than 2 * BLOB is not; N46's thinner excess along its edges is its heavier weight, which
        the face's edge level already accounts for, and is left to the mean.
    Returns the field with each region taken in or left out, and the record of each region."""
    from skimage.morphology import disk
    (na, a), (nb, b) = prints
    ink = {na: a > 0.5, nb: b > 0.5}
    r = max(1, int(round(NOTCH / step)))
    closed = {k: ndi.binary_closing(np.pad(m, r + 1), structure=disk(r))[r + 1:-r - 1, r + 1:-r - 1] for k, m in ink.items()}
    take, drop, record = np.zeros(a.shape, bool), np.zeros(a.shape, bool), []
    opened = lambda m, radius: ndi.binary_opening(m, structure=disk(max(1, int(round(radius / step)))))
    for inking, other in ((na, nb), (nb, na)):
        only = ink[inking] & ~ink[other] & near
        notches = opened(only & closed[other], SLIVER)
        protrusions = opened(only & ~closed[other], BLOB if inking == 'N46' else SLIVER)
        for kind, regions in (('notch', notches), ('protrusion', protrusions)):
            lab, k = ndi.label(regions, structure=np.ones((3, 3)))
            for i in range(1, k + 1):
                region = lab == i
                thick = 2 * ndi.distance_transform_edt(region).max() * step
                ys, xs = np.nonzero(region)
                rec = dict(inked_by=inking, kind=kind, at=[round(float(xs.mean() * step), 2), round(float(ys.mean() * step), 2)],
                           area=round(float(region.sum() * step * step), 3), thickness=round(float(thick), 3))
                if thick > LARGEST * stem:
                    record.append(dict(rec, decision='left to the mean')); continue
                vote = [float((v[region] > 0.5).mean()) > 0.5 for v in votes]
                if kind == 'notch':
                    drawn, why = True, f'{other} leaves a notch or gap that {inking} fills'
                elif vote and 2 * sum(vote) != len(vote):
                    drawn, why = 2 * sum(vote) > len(vote), f'N44 votes {sum(vote)} of {len(vote)}'
                else:
                    drawn = inking == 'N45'
                    why = 'a tip or spur the photocopy lost' if drawn else 'a lump of the photocopy\'s toner'
                (take if drawn else drop)[region] = True
                record.append(dict(rec, drawn=drawn, why=why))
    soft = lambda m: np.clip(2 * ndi.gaussian_filter(ndi.binary_dilation(m, iterations=1).astype(float), 0.7), 0, 1)
    out = field
    if take.any():
        out = np.maximum(out, soft(take) * (edge + 0.2))
    if drop.any():
        out = np.minimum(out, (edge - 0.15) + 2 * (1 - soft(drop)))
    return out, record


def trace_letter(name, reg, mean, base_rec, edge, prints=None, votes=(), stem=None):
    origin, step = reg['origin'], reg['step']
    m, _ = IM.trace_mask(base_rec, step, CP.PAD)
    base_mask = m[:mean.shape[0], :mean.shape[1]] > 0.5
    near = ndi.binary_dilation(base_mask, iterations=int(round(1.5 / step)))
    avg = [p for p in reg['prints'] if p['averaged']]
    tops = {tuple(p['topology']) for p in avg}
    decision = DECISIONS.get(name)
    if decision and 'topology' in decision:
        want, rule = tuple(decision['topology']), decision['why']
    elif len(tops) == 1:
        want, rule = tops.pop(), f'all {len(avg)} averaged prints agree'
    else:
        raise ValueError(f'{name}: the averaged prints disagree ({[p["topology"] for p in avg]}); add a decision')
    tried, disagree = [], None
    if prints is not None:
        mean, disagree = disagreements(mean, prints, votes, edge, step, stem, near)
    for field, local in keep_topology(mean, want, near, edge):
        cs = FP.contours_at(field, edge, origin, step, base_mask)
        rec = curves_to_recording([contour_to_curves4(c, **FIT) for c in cs])
        got = rec_topology(rec)
        if got == want:
            return rec, dict(attested=list(want), rule=rule, mean=reg['mean_topology'], fitted=list(got),
                             **({'local_level': local} if local else {}), **({'disagreements': disagree} if disagree else {}), ok=True)
        tried.append(dict(local or {}, fitted=list(got)))
    return None, dict(attested=list(want), rule=rule, mean=reg['mean_topology'], tried=tried, ok=False)


# ---------------------------------------------------------------- the loose punctuation pieces
# N45 prints its punctuation in a row box of its own; N46 stacks the same pieces inside its parentheses.
# Components at threshold 130, eight-connected, in each row box (as trace_ceili_punctuation.py labels them).
PUNCT_ROWS = {'N45': (755, 665, 1430, 770), 'N46': (1130, 1645, 2070, 1795)}
PIECES = {
    # Study 3's four named pieces; N46 prints no separate period or comma (its colon and semicolon only)
    'period': dict(N45=[17]), 'comma': dict(N45=[18]),
    'quoteleft': dict(N45=[6], N46=[6]), 'quoteright': dict(N45=[7], N46=[7]),
    # the upper row's three pieces, which both prints set together and in the same order
    'acute': dict(N45=[5], N46=[27]), 'dot.round': dict(N45=[3], N46=[26]), 'dot.diamond': dict(N45=[4], N46=[28]),
}
IDENTIFIED = {
    'acute': ('síneadh fada (acute)', 'built',
              'A thin wedge rising to the right from a point to a blunt head, the size of the dots, set with the quotes at the '
              'top of N45\'s punctuation row and at the foot of N46\'s stack, beside the round dot and the diamond in the '
              'same order on both. No punctuation mark has this shape (the apostrophe is the closing quote, piece 7), '
              'the specimen shows no accented letter, and Irish cannot be set without the fada: it is the face\'s acute. '
              'An identification by judgement; the shape is attested.'),
    'dot.round': ('probably the ponc séimhithe (dot above)', 'recorded, not built',
                  'The only round piece: every dot of the face\'s punctuation, of ! and ? is a pen-made diamond, and this one '
                  'is larger (N45 131 px against 96 for the period; N46 132 against 82-110) and rounder (it fills 88% of '
                  'its circumscribed disc on N45, the diamonds 60-71%). A mark, not punctuation; in an Irish face most '
                  'probably the dot of séimhiú. The dot accent stays the N45 period, as in Study 3, until the identity is settled.'),
    'dot.diamond': ('unassigned', 'recorded, not built',
                    'A diamond the size and shape of the period, set with the marks rather than the punctuation. '
                    'Possibly a second dot above or a raised point; the prints do not say which.'),
}


def punctuation(round_traces, levels, hashes, edge):
    """Each named piece from the mean of its prints (N45 alone for period and comma), each print at its own
    midpoint, at the face's edge level, in the font units, y up, of Study 3's punctuation records (the
    round-3 N45 scale, per-piece origin)."""
    from glyphs import SCALE, to_path, clean
    from fontTools.pens.recordingPen import RecordingPen
    import skimage.measure as measure
    ev = json.loads((CP.BASE / 'evidence.json').read_text(encoding='utf-8'))
    old = json.loads((CP.BASE / 'punctuation.json').read_text())
    s45 = ev['calibration'][CP.N45]['scale']; s46 = ev['calibration'][CP.N46]['scale']; fu = SCALE['ceili']
    pr = CP.prints()
    step = CP.FINE
    pieces, records = [], {}
    for name, comps in PIECES.items():
        maps, info = [], []
        e45 = dict(print='N45', labels=comps['N45'], row_box=list(PUNCT_ROWS['N45']))
        lab = pr.labels('N45', PUNCT_ROWS['N45'])
        e45['box'] = CP.box_of(lab, comps['N45'], PUNCT_ROWS['N45'][:2])
        x0, y0, x1, y1 = e45['box']; pad = 6
        # the grid, in trace units of the N45 scale: grid pixel (j, i) is N45 pixel (x0 - pad, y0 - pad) + step * s45 * (j, i)
        origin = ((x0 - pad) / s45, (y0 - pad) / s45)
        shape = (int(np.ceil((y1 - y0 + 2 * pad) / (s45 * step))), int(np.ceil((x1 - x0 + 2 * pad) / (s45 * step))))
        crop, off = pr.patch(e45)
        q45 = np.array([s45, 0, 0, s45, -off[0], -off[1]])
        m45 = IM.warp(crop, q45, shape, origin, step)
        maps.append(m45); info.append(dict(print='N45', box=e45['box'], labels=comps['N45'], scale=s45, shift=[0.0, 0.0]))
        if 'N46' in comps:
            e46 = dict(print='N46', labels=comps['N46'], row_box=list(PUNCT_ROWS['N46']))
            lab = pr.labels('N46', PUNCT_ROWS['N46'])
            e46['box'] = CP.box_of(lab, comps['N46'], PUNCT_ROWS['N46'][:2])
            crop, off = pr.patch(e46)
            # the N46 piece at the leaflet's calibrated scale, placed by its centre of ink and then the best
            # whole-grid shift (no rotation or scale: too few pixels to estimate them)
            ref = m45
            cy, cx = ndi.center_of_mass(ref)
            g = crop; gy, gx = ndi.center_of_mass(g)
            u = origin[0] + step * (cx + 0.5); v = origin[1] + step * (cy + 0.5)
            q46 = np.array([s46, 0, 0, s46, gx + 0.5 - s46 * u, gy + 0.5 - s46 * v])
            best = None
            for dx in np.arange(-1.5, 1.51, 0.25):
                for dy in np.arange(-1.5, 1.51, 0.25):
                    w = IM.warp(g, q46 + [0, 0, 0, 0, dx, dy], shape, origin, step)
                    err = float(((w - ref) ** 2).mean())
                    if best is None or err < best[0]:
                        best = (err, dx, dy, w)
            maps.append(best[3])
            info.append(dict(print='N46', box=e46['box'], labels=comps['N46'], scale=s46,
                             shift=[round(float(q46[4] + best[1] + off[0]), 3), round(float(q46[5] + best[2] + off[1]), 3)],
                             rms_to_N45=round(best[0] ** 0.5, 4)))
        mean = np.mean(maps, axis=0)
        cs = []
        for c in measure.find_contours(np.pad(mean, 2), edge):
            xy = np.column_stack((origin[0] + (c[:, 1] - 2 + 0.5) * step, origin[1] + (c[:, 0] - 2 + 0.5) * step))
            area = abs(np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - xy[:, 1] * np.roll(xy[:, 0], -1)) / 2)
            if area >= 1.0:
                cs.append(xy[:-1])
        rec = curves_to_recording([contour_to_curves4(c, **FIT) for c in cs])
        # font units as Study 3's pieces: x from the N45 box's left, y up from its foot
        to_font = (fu, 0, 0, -fu, -x0 / s45 * fu, y1 / s45 * fu)
        path = clean(to_path([(op, [tuple(p) for p in a]) for op, a in rec], to_font))
        pen = RecordingPen(); path.draw(pen)
        ident = IDENTIFIED.get(name)
        record = dict(name=name, source=' + '.join(i['print'] for i in info), source_id='N45' if len(info) == 1 else 'N45+N46',
                      prints=[dict(i, file=CP.PRINTS[i['print']]['file'], sha256=hashes[i['print']],
                                   averaged_at=levels[i['print']], row_box=list(PUNCT_ROWS[i['print']]), threshold=130) for i in info], edge_level=edge,
                      box=e45['box'], rec=[(op, [list(p) for p in a]) for op, a in pen.value],
                      source_to_font=[fu / s45, 0, 0, -fu / s45, -x0 * fu / s45, y1 * fu / s45],
                      topology=list(rec_topology(rec)))
        if ident:
            record.update(identification=ident[0], use=ident[1], reason=ident[2])
        pieces.append(record)
        print(f'{name:12s} from {record["source"]:8s} topology {record["topology"]}'
              f'{"  " + str(info[-1].get("rms_to_N45")) if len(info) > 1 else ""}', flush=True)
    report = dict(old, pieces=pieces, units=old['units'],
                  decision='Period and comma from N45 (N46 prints no separate pair); the quotes and the three upper pieces from '
                           'the mean of N45 and N46, each print\'s ink at its own edge level (as the letters). The thin rising '
                           'wedge is identified as the síneadh fada and builds the acute; the round dot is recorded as probably '
                           'the ponc séimhithe and the diamond as unassigned; neither is built.',
                  study3_pieces={p['name']: p['box'] for p in old['pieces']})
    report['limitations'] = old['limitations'] + [
        'N46 component 26, which round 4 compared with the N45 period, is the round dot (larger and rounder, in the same '
        'place in the set as N45 piece 3); N46 prints no separate period.']
    (round_traces / 'punctuation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def holdout(reg, work, tr, edge):
    """A check the averaging did not see: the cover heading N44 against N46 and N45 combined without it.
    Shape agreement only (IoU, each N44 impression thresholded to the candidate's own ink area, so that
    the prints' weights are set aside). N44 shares the brochure's press with N45, so N45 alone is not a
    fair comparison; Study 3 and N46 are."""
    iou = lambda a, b: float((a & b).sum() / max((a | b).sum(), 1))
    rows = {}
    for n, R in reg.items():
        if not any(p['print'] == 'N44' for p in R['prints']):
            continue
        st = np.load(work / f'stack-{n}.npy').astype(float)
        get = lambda pid: [s for p, s in zip(R['prints'], st) if p['print'] == pid]
        a, b = get('N46')[0], get('N45')[0]
        study3 = IM.trace_mask(tr[n]['rec'], R['step'], CP.PAD)[0][:a.shape[0], :a.shape[1]] > 0.5
        cands = {'Study 3': study3, 'N46': a > 0.5, 'N45 (same press)': b > 0.5, 'mean of N46 and N45': (a + b) / 2 > edge}
        for t in get('N44'):
            for k, m in cands.items():
                rows.setdefault(k, []).append(iou(m, t > np.quantile(t, 1 - m.mean())))
    return {k: dict(mean_iou=round(float(np.mean(v)), 4), impressions=len(v)) for k, v in rows.items()}


def edge_level(reg, work, tr, ev, calibration):
    """The one level of the prints' means at which their stems are as wide as the median print's, over the
    stemmed letters Study 3 traced from N46. Each high-resolution print's stems are measured at its own
    midpoint against Study 3's: N46 and the cover heading N44 print them alike, N45's alphabet about 10%
    lighter, so the median print (and with it the face) is a little lighter than Study 3, and the hairlines,
    which N45 and N44 print heavier than N46, come out near the median print's too."""
    grid = np.linspace(0.2, 0.8, 61)
    ratios = []
    for n in CP.STEMS:
        if n not in reg or reg[n]['averaged'] < 2 or ev.get(n, {}).get('source_id') != 'N46':
            continue
        mean = np.load(work / f'mean-{n}.npy').astype(float)
        t = IM.trace_mask(tr[n]['rec'], reg[n]['step'], CP.PAD)[0][:mean.shape[0], :mean.shape[1]] > 0.5
        target = CP.stem_width(t, t, reg[n]['step'])
        ratios.append([CP.stem_width(mean > g, t, reg[n]['step']) / target for g in grid])
    r = np.nanmedian(np.array(ratios), axis=0)
    prints = {pid: c['stems_at_half_vs_study3'] for pid, c in calibration.items() if CP.PRINTS[pid]['high']}
    target = 1 + float(np.median(list(prints.values())))
    i = int(np.nanargmin(np.abs(r - target)))
    half = int(np.argmin(np.abs(grid - 0.5)))
    return float(grid[i]), dict(level=round(float(grid[i]), 3), letters=len(ratios), prints_stems_at_midpoint_vs_study3=prints,
                                target_vs_study3=round(target - 1, 4), means_stems_at_half_vs_study3=round(float(r[half] - 1), 4),
                                means_stems_at_level_vs_study3=round(float(r[i] - 1), 4))


# N46 sets its 8 higher on the line than its neighbours (its foot 2 px above the median of 0, 1, 2, 6 and the
# pound's; Study 3's 8 floats 37 units above the baseline); N45 sets it level with them
SIT_ON_BASELINE = {'eight': 'N46 sets the 8 about 2 px (0.7 trace units) higher on its line than 0, 1, 2, 6 and the pound '
                            '(feet at 1853 against a median of 1855 px); N45 sets it level with them (858 against 858). '
                            'Placement on a paste-up is setting, not drawing: the 8 sits on the baseline like the other figures.'}

# The derived styles (build_original_study reads these). Judged repairs to the builder's bold and sloped
# derivations, not to the drawing: the prints show only the Regular.
DERIVED_STYLES = {
    'bold_keep_apart': dict(
        glyphs=['exclam', 'question'],
        why='Every print sets the dot of ! and ? clear of its stroke (Study 4 Regular: 13 and 17 units). The bold\'s '
            'wider pen leaves the ? dot 1.6 units from the stroke without joining it (Study 3: 5), so the bold keeps '
            'nothing to reopen and the sloped bold\'s hair of weight joins them. Set apart as the bold sets apart a dot it '
            'joins: a cut F_PASS of the regular\'s gap wide along the midline (bolden._separate, close).'),
    'sound_sloped_growth': 'The sloped styles\' hair of weight (build2 condense) on oe comes out of pathops unsound '
                           '(part of the e resolved as a hole, the eye lost); the outline simplified first grows soundly. '
                           'Only oe in the Italic is affected; every other growth is unchanged.'}


def line_baselines(doc):
    """Each source line's baseline as the builder measures it (metrics.line_baselines) for a trace file."""
    import metrics
    res = [dict(g, rec=[(op, tuple(tuple(q) for q in a)) for op, a in g['rec']]) for g in doc['glyphs']]
    return metrics.line_baselines(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--round', type=Path, required=True)
    ap.add_argument('--work', type=Path, default=CP.WORK)
    args = ap.parse_args()
    out = args.round / 'traces'; out.mkdir(parents=True, exist_ok=True)
    reg = json.loads((args.work / 'registration.json').read_text())
    lv = json.loads((args.work / 'levels.json').read_text())
    doc = json.loads((CP.BASE / 'ceili.json').read_text())
    ev = json.loads((CP.BASE / 'evidence.json').read_text(encoding='utf-8'))
    byname = {g['name']: g for g in doc['glyphs']}
    evidence = {e['name']: e for e in ev['glyphs']}
    files = {pid: CP.PRINTS[pid]['file'] for pid in CP.PRINTS}
    edge, edge_record = edge_level(reg, args.work, byname, evidence, lv['calibration'])
    stem = float(np.median([CP.stem_width(IM.trace_mask(byname[n]['rec'], CP.FINE, CP.PAD)[0] > 0.5,
                                          IM.trace_mask(byname[n]['rec'], CP.FINE, CP.PAD)[0] > 0.5, CP.FINE) for n in ('l', 'n', 'i')]))
    print(f'edge level of the means {edge:.3f}: {edge_record}', flush=True)
    redrawn, kept = {}, {}
    for name, g in byname.items():
        r = reg.get(name)
        if name == 'DOTS' or r is None or r['averaged'] < 2:
            kept[name] = 'fewer than two high-resolution prints' if name != 'DOTS' else 'the legacy cluster; discarded by the builder'
            continue
        mean = np.load(args.work / f'mean-{name}.npy').astype(float)
        stack = np.load(args.work / f'stack-{name}.npy').astype(float)
        prints = [(p['print'], s) for s, p in zip(stack, r['prints']) if p['averaged']]
        votes = [s for s, p in zip(stack, r['prints']) if p['print'] == 'N44']
        rec, topo = trace_letter(name, r, mean, g['rec'], edge, prints, votes, stem)
        if rec is None or not topo['ok']:
            kept[name] = f'consensus topology not reached: {topo}'
            print(f'{name:10s} KEPT Study 3: {topo}', flush=True)
            continue
        # the frame is already Study 3's (each print was registered onto its trace, and the averaged prints'
        # mean correction taken out); lock_frame's overlap fit is recorded as a check, not applied: it shrinks a
        # heavier shape and grows a lighter one to overlap better
        _, lock = FP.lock_frame(rec, g['rec'])
        h = copy.deepcopy(g); h['rec'] = [(op, [list(p) for p in a]) for op, a in rec]
        h.pop('paper', None); h.pop('ink', None); h.pop('source_smoothing_sigma', None)
        byname[name] = h
        avg = [p for p in r['prints'] if p['averaged']]
        px = float(np.mean([np.sqrt(p['geometry']['scale_x'] * p['geometry']['scale_y']) for p in avg]))
        old = evidence[name]
        prints = []
        for p in r['prints']:
            prints.append(dict(print=p['print'], source_id=p['source_id'], file=files[p['print']], sha256=lv['hashes'][p['print']],
                               box=p['box'], located=p['how'], averaged=p['averaged'], edge_level=lv['levels'][p['print']],
                               affine=p['affine'], geometry=p['geometry'], rms_to_trace=p['rms_to_trace'],
                               rms_to_mean=p['rms_to_mean'], topology=p['topology'],
                               **{k: p[k] for k in ('labels', 'variant_iou', 'centre_residual_px') if k in p}))
        primary = next(p for p in avg if p['print'] == 'N46') if any(p['print'] == 'N46' for p in avg) else avg[0]
        counts = {}
        for p in avg:
            counts[p['print']] = counts.get(p['print'], 0) + 1
        ids = ', '.join(f'{k} x{v}' if v > 1 else k for k, v in counts.items())
        evidence[name] = dict(
            name=name, status='candidate', method='consensus', source_id='+'.join(dict.fromkeys(p['print'] for p in avg)),
            source=f'mean of {len(avg)} prints ({ids}; files in prints)', box=primary['box'], scale=round(px, 5),
            prints=prints, topology=topo, frame_check=lock,
            replaces=dict(source_id=old.get('source_id'), source=old.get('source'), box=old.get('box'), smoothing_sigma=old.get('smoothing_sigma')),
            note=f'Edge at the face\'s one level ({edge:.2f}) of the mean of {len(avg)} prints, each at its own midpoint, in the Study 3 trace\'s frame; '
                 f'the frame is Study 3\'s (frame_check: the overlap fit to Study 3, not applied). Low-resolution prints '
                 f'registered for comparison only.')
        redrawn[name] = topo
        print(f'{name:10s} {len(avg)} prints  topology {topo["attested"]} ({topo["rule"]})'
              f'{"  " + topo["local_level"]["kind"] + " at " + str(topo["local_level"]["level"]) if "local_level" in topo else ""}'
              f'  check {lock["scale"]:.4f} {lock["shift"]}', flush=True)
    doc['source'] = 'NIVAL N46/N45/N44 and the leaflet\'s sheet samples, averaged per letter; see evidence.json'
    doc['glyphs'] = [byname[g['name']] for g in doc['glyphs']]
    ev2 = copy.deepcopy(ev)
    ev2['glyphs'] = [evidence[g['name']] for g in ev['glyphs']]
    base3 = line_baselines(json.loads((CP.BASE / 'ceili.json').read_text())); base4 = line_baselines(doc)
    ev2['line_baselines'] = {str(k): dict(baseline=base3[k], measured_on_study4=round(base4[k], 4),
                                          note='Study 3\'s baseline for this source line, kept (build_original_study reads it): '
                                               'the median of the bottoms moves with the overshoots of round and pointed letters')
                             for k in sorted(base3)}
    ev2['sit_on_baseline'] = SIT_ON_BASELINE
    ev2['derived_styles'] = DERIVED_STYLES
    ev2['status'] = 'research candidate (Céilí Study 4, the judgement pass); not release'
    ev2['source_hashes'] = {**ev['source_hashes'], **{files[p]: lv['hashes'][p] for p in CP.PRINTS if p != 'B2'},
                            CP.B2_PDF: lv['hashes']['B2_pdf'], 'b2-fig203b.jpg (pdfimages -j, page 159)': lv['hashes']['B2']}
    ev2['prints'] = {pid: dict(spec, sha256=lv['hashes'][pid], averaged_at=lv['levels'][pid],
                               stem_matched_level=lv['stem_matched_levels'][pid], calibration=lv['calibration'][pid])
                     for pid, spec in CP.PRINTS.items()}
    study3 = {g['name']: g for g in json.loads((CP.BASE / 'ceili.json').read_text())['glyphs']}
    check = holdout(reg, args.work, study3, edge)
    print('hold-out against N44:', check, flush=True)
    ev2['consensus'] = dict(
        method='Each print registered onto the Study 3 trace by a similarity (uniform scale, rotation, shift: translation '
               'search, coarse-to-fine least squares), then twice onto the averaged prints\' mean, the frame pinned in the '
               'trace\'s coordinates; mean of the high-resolution prints, each at its own midpoint, on a '
               f'{CP.FINE} trace-unit grid; edge at the face\'s one level (edge_level: the means\' stems as wide as the median print\'s); '
               'fitted with curvefit3.contour_to_curves4; the frame is Study 3\'s.',
        fit=FIT, edge_level=edge_record, disagreements=dict(sliver=SLIVER, blob=BLOB, notch=NOTCH, largest_stems=LARGEST, stem=round(stem, 3),
            rule=disagreements.__doc__.split('Returns')[0].strip().replace('\n    ', ' ')),
        holdout_N44=dict(check, note=holdout.__doc__.split('\n\n')[0].replace('\n    ', ' ').strip()),
        redrawn=sorted(redrawn), kept=kept,
        caveat='The prints reproduce one artwork. Averaging lowers each reproduction\'s noise (photocopy toner on N46, '
               'offset ink and paper on N45); it does not confirm the design. The weight is a calibration, not a measurement: '
               'at their own midpoints N45\'s stems print about 10% lighter than N46\'s and N44\'s, its hairlines no lighter.')
    ev2.setdefault('limitations', []).append(
        'Without a production sheet the weight and contrast of the design are not settled: N46 (photocopy) prints its stems '
        'heavier and its hairlines thinner than N45 (offset); Study 4 takes the median print\'s stems (about 3% lighter than '
        'Study 3) and the prints\' mean contrast.')
    (out / 'ceili.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'evidence.json').write_text(json.dumps(ev2, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    loc = json.loads((args.work / 'locations.json').read_text())
    (out / 'source-regions.json').write_text(json.dumps(loc, indent=1) + '\n', encoding='utf-8')
    punctuation(out, lv['levels'], lv['hashes'], edge)
    print(f'redrawn {len(redrawn)}; kept {sorted(kept)}')


if __name__ == '__main__':
    main()
