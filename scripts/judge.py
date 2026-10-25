"""Apply judged edits to a research round's traces: the calls a type studio makes where the evidence
is the artwork's own, and the artwork was not drawn for the sizes a font is used at.

usage: python scripts/judge.py kilfane --traces ROUND/traces --edits research/<round>/judged-edits.json

Each edit names a glyph, an operation, where it applies and why. Every edit is recorded in the
glyph's evidence entry (judged_edits), with the area of ink it adds or removes, so a judged shape
is never mistaken for an attested one. Operations:

  ease_notch   fill the narrow inner end of a notch in the outline: background reachable from
               outside that a disc of `radius` (trace units) cannot enter, within `reach` of `at`.
               The notch keeps its mouth; only the part narrower than the disc closes.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from curvefit import curves_to_recording
from curvefit3 import contour_to_curves4
import impressions as IM

FIT = dict(cutoff=6, corner_deg=55, rms_tol=.07, max_tol=.22, line_tol=.18, line_bulge=.055, line_min=4.5, snap_deg=1.5)
STEP = 0.125                      # trace units per pixel of the working raster


def ease_notch(rec, at, radius, reach):
    from skimage import measure
    from skimage.morphology import disk
    m, (x0, y0) = IM.trace_mask(rec, STEP, 2 * radius + 4)
    m = m > 0.5
    r = int(round(radius / STEP))
    closed = ndi.binary_closing(np.pad(m, r + 1), structure=disk(r))[r + 1:-r - 1, r + 1:-r - 1]
    fill = closed & ~m
    # only the outside's notch, not a counter's corner, and only near `at`
    bg, _ = ndi.label(~m)
    outside = np.isin(bg, np.unique(np.r_[bg[0], bg[-1], bg[:, 0], bg[:, -1]]))
    yy, xx = np.mgrid[:m.shape[0], :m.shape[1]]
    near = np.hypot(x0 + (xx + 0.5) * STEP - at[0], y0 + (yy + 0.5) * STEP - at[1]) <= reach
    fill &= outside & near
    # the filled region, overlapping the outline by a pixel so the union is clean, is added to the
    # outline as it stands: the rest of the glyph keeps its curves exactly
    grown = ndi.binary_dilation(fill, iterations=1) & (closed | m)
    patches = []
    for c in measure.find_contours(np.pad(grown.astype(float), 2), 0.5):
        xy = np.column_stack((x0 + (c[:, 1] - 2 + 0.5) * STEP, y0 + (c[:, 0] - 2 + 0.5) * STEP))
        if len(xy) > 8:
            patches.append(contour_to_curves4(xy[:-1], **FIT))
    return union(rec, curves_to_recording(patches)), float(fill.sum() * STEP * STEP)


def union(rec, extra):
    """The union of two trace records, as a record (pathops; winding fixed)."""
    import pathops
    from fontTools.pens.recordingPen import RecordingPen
    p = pathops.Path(); pen = p.getPen()
    for r in (rec, extra):
        for op, a in r:
            getattr(pen, op)(*[tuple(x) for x in a])
    p = pathops.simplify(p, fix_winding=True, keep_starting_points=True)
    out = RecordingPen(); p.draw(out)
    return [(op, [list(x) for x in a]) for op, a in out.value]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('face'); ap.add_argument('--traces', type=Path, required=True)
    ap.add_argument('--edits', type=Path, required=True)
    args = ap.parse_args()
    tr_path = args.traces / f'{args.face}.json'; ev_path = args.traces / 'evidence.json'
    tr = json.loads(tr_path.read_text()); ev = json.loads(ev_path.read_text())
    edits = json.loads(args.edits.read_text())
    byname = {g['name']: g for g in tr['glyphs']}
    evidence = {e['name']: e for e in ev['glyphs']}
    for e in edits['edits']:
        g = byname[e['glyph']]
        if e['op'] == 'ease_notch':
            g['rec'], area = ease_notch(g['rec'], e['at'], e['radius'], e['reach'])
        else:
            raise ValueError(f'unknown operation {e["op"]}')
        evidence[e['glyph']].setdefault('judged_edits', []).append(dict(e, added_area=round(area, 3)))
        print(f'{e["glyph"]}: {e["op"]} adds {area:.2f} square trace units', flush=True)
    tr_path.write_text(json.dumps(tr, separators=(',', ':')), encoding='utf-8')
    ev['glyphs'] = [evidence[x['name']] for x in ev['glyphs']]
    ev_path.write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
