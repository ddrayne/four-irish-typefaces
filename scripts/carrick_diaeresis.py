"""Carrick's diaeresis from N513: the accent set's lower paired piece, its two dots divided at their neck.

usage: python scripts/carrick_diaeresis.py --traces research/round-06/carrick/traces [--preview build/judgement/carrick]

N513's accent set (and N47's reproduction of it) has one paired piece: two blocks, each the size of the
set's dot, leaning together and touching at their inner lower corners. Round 5 left it unassigned and
kept the flyer's diaeresis. It is the set's only pair, and the only piece a European accent set needs
that is otherwise missing, so it is taken as the diaeresis (a judged identification). It is traced from
N513 exactly as round 5 traced the other marks (scripts/trace_carrick_marks.py: the component at the
130 threshold, the strongest blur up to 0.8 px that keeps its topology, the 0.5 edge, the designer-style
fit, one uniform transform), except that the ink is first divided at its narrowest neck (a watershed of
its distance map from the two blocks' cores) and a gap of GAP source pixels is cut along the division,
as Carrick's pieces are parted by hairlines. Only that cut is a construction.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from curvefit import curves_to_recording
from curvefit3 import contour_to_curves4
from source_study import component_field, smooth_preserving_topology

FIT = dict(cutoff=6, corner_deg=55, rms_tol=.07, max_tol=.22, line_tol=.18, line_bulge=.055, line_min=4.5, snap_deg=1.5)
GAP = 2.0                  # source pixels (about 11 font units): Carrick's hairline between pieces
# The two dots lean together, so where they part they are a hairline apart and at text sizes the pair
# reads as a v (a caron). Each is moved out by SPREAD font units, leaving about a third of a dot between
# them at the foot: a construction of the pair's pitch; the dots keep their shapes.
SPREAD = 15.0
PRIMARY = 'Carrick-alphabet-specimen.jpg'


def divide(field):
    """The two dots of the pair: (field of each, the division line), parted at the narrowest neck."""
    from skimage.segmentation import watershed
    inked = field > 0.5
    dist = ndi.distance_transform_edt(inked)
    for it in range(1, 8):                      # erode until the pair falls into its two blocks
        core = ndi.binary_erosion(inked, iterations=it)
        lab, k = ndi.label(core)
        if k >= 2:
            sizes = ndi.sum(core, lab, range(1, k + 1))
            keep = np.argsort(sizes)[::-1][:2] + 1
            break
    else:
        raise ValueError('the lower pair does not divide')
    order = sorted(keep, key=lambda j: np.nonzero(lab == j)[1].mean())      # left, right
    markers = np.zeros(field.shape, int)
    for i, j in enumerate(order):
        markers[lab == j] = i + 1
    owner = watershed(-dist, markers, mask=field > 0.02)
    out = []
    for i in (1, 2):
        other = ndi.distance_transform_edt(owner != (3 - i))      # distance from the other dot's pixels
        f = np.where((owner == i) & (other > GAP / 2), field, 0.0)
        out.append(f)
    line = ndi.binary_dilation(owner == 1) & (owner == 2)
    return out, line


def trace(field, origin, scale, s, dx=0.0):
    from skimage import measure
    import pathops
    from fontTools.pens.recordingPen import RecordingPen, replayRecording
    from fontTools.pens.transformPen import TransformPen
    f, sigma = smooth_preserving_topology(field)
    curves = []
    for c in measure.find_contours(np.pad(f, 2), .5):
        xy = np.column_stack((c[:, 1] - 2 + origin[0], c[:, 0] - 2 + origin[1]))
        area = abs(np.sum(xy[:, 0] * np.roll(xy[:, 1], -1) - xy[:, 1] * np.roll(xy[:, 0], -1)) / 2)
        if area < 6:
            continue
        uv = (xy[:-1] - [700, 975]) / scale                       # round 5's frame for the accent set
        curves.append(contour_to_curves4(uv, **FIT))
    rec = curves_to_recording(curves)
    p = pathops.Path(); replayRecording(rec, TransformPen(p.getPen(), (s, 0, 0, -s, dx, 0)))
    p = pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)
    pen = RecordingPen(); p.draw(pen)
    ys, xs = np.nonzero(field > 0.5)
    box = [int(origin[0] + xs.min()), int(origin[1] + ys.min()), int(origin[0] + xs.max() + 1), int(origin[1] + ys.max() + 1)]
    return [(op, [list(map(float, q)) for q in a]) for op, a in pen.value], sigma, box


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--traces', type=Path, required=True); ap.add_argument('--preview', type=Path)
    args = ap.parse_args()
    path = args.traces / 'pieces.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    ev = json.loads((args.traces / 'evidence.json').read_text(encoding='utf-8'))
    src = ROOT / 'build' / 'research' / 'original-specimens' / PRIMARY
    if hashlib.sha256(src.read_bytes()).hexdigest() != data['source_hashes'][PRIMARY]:
        raise ValueError('source changed: ' + PRIMARY)
    region = next(r for r in data['unassigned'] + data.get('assigned_by_judgement', []) if r['name'] == 'unassigned.lower-pair')
    region = {k: v for k, v in region.items() if k not in ('status', 'assigned_to')}
    gray = np.asarray(Image.open(src).convert('L'))
    field, origin, paper, ink = component_field(gray, region)
    (fl, fr), line = divide(field)
    import glyphs
    scale = ev['calibration'][PRIMARY]['scale']; s = glyphs.SCALE['carrick']
    pieces = {p['name']: p for p in data['pieces']}
    for name, f, dx in (('dieresis.l', fl, -SPREAD), ('dieresis.r', fr, SPREAD)):
        rec, sigma, box = trace(f, origin, scale, s, dx)
        pieces[name] = dict(
            name=name, row=region['row'], labels=region['labels'], row_box=region['row_box'], threshold=region['threshold'],
            box=box, status='judged', source=PRIMARY, source_id='N513', parent='unassigned.lower-pair',
            smoothing_sigma=sigma, source_to_font=region['source_to_font'], gap_px=GAP, moved_out=dx, rec=rec,
            note='The accent set\'s lower paired piece, identified by judgement as the diaeresis (the set\'s only pair; '
                 'each block is the size of its dot). Traced from N513 as the other marks; the two dots touch at their '
                 f'inner lower corners on N513 and N47 and are divided at the narrowest neck with a {GAP:g}-pixel cut, '
                 f'and each is moved {SPREAD:g} units outward so the pair reads as two dots: both constructions.')
        print(f'{name}: N513 box {box}, smoothing {sigma}')
    data['pieces'] = [pieces[p['name']] for p in data['pieces']]
    data['unassigned'] = [r for r in data['unassigned'] if r['name'] != 'unassigned.lower-pair']
    data['assigned_by_judgement'] = [dict(region, status='assigned',
                                          assigned_to=['dieresis.l', 'dieresis.r'])]
    data['decision'] = ('Ten isolated components traced; the lower paired piece is the diaeresis (judged), its two dots '
                        'divided at their neck. The fused inner chevrons remain unassigned; paired guillemets repeat '
                        'the original outer chevrons.')
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8', newline='\n')
    if args.preview:
        args.preview.mkdir(parents=True, exist_ok=True)
        rgb = np.stack([255 - field * 255] * 3, -1).astype(np.uint8)
        rgb[fl > 0.5] = (rgb[fl > 0.5] * 0.5 + np.array([220, 60, 40]) * 0.5).astype(np.uint8)
        rgb[fr > 0.5] = (rgb[fr > 0.5] * 0.5 + np.array([40, 120, 220]) * 0.5).astype(np.uint8)
        Image.fromarray(rgb).resize((field.shape[1] * 12, field.shape[0] * 12), Image.NEAREST).save(args.preview / 'diaeresis-division.png')


if __name__ == '__main__':
    main()
