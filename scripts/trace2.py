"""Second-generation tracer: sub-pixel contours + corner-aware smoothing + Bézier fitting.

Same segmentation and per-glyph normalisation as trace.py, but instead of potrace
the 50% iso-contour of the cleaned, upsampled ink field is extracted with marching
squares and fitted by curvefit.contour_to_curves. An optional inward offset
(`spread`, source px) undoes photocopy/printing ink spread.
"""
import os, pickle, sys
import numpy as np
from scipy import ndimage as ndi
from skimage import measure
from specs import SPECS
from seg import segment
from trace import regions, disk
from curvefit import resample_closed, contour_to_curves, curves_to_recording

PARAMS2 = {
    #            blur  bridge        hole  island spread corner  sigma  tol
    'kilfane': dict(blur=0.45, bridge=None, hole=3.0, island=3.0, spread=0.18, corner=40, sigma=0.75, tol=0.10),
    'tuam':    dict(blur=0.40, bridge=(1.2, 0.25), hole=2.5, island=3.0, spread=0.16, corner=36, sigma=0.70, tol=0.10,
                    cuts={'question': [263]}),
    'carrick': dict(blur=0.45, bridge=None, hole=4.0, island=4.0, spread=0.00, corner=34, sigma=0.65, tol=0.10,
                    glyph={'ornament': dict(hole=0.3)}),       # the accent set's rings have tiny counters
    'ceili':   dict(blur=0.35, bridge=(0.8, 0.3), hole=1.5, island=2.0, spread=0.25, corner=40, sigma=0.65, tol=0.08,
                    cuts={'question': [691], 'exclam': [691]},
                    glyph={'h': dict(sigma=1.3, tol=0.10)}),
}
F = 8


def ink_field(g, region, sub, paper_mask, origin, P):
    gi = g['idx']; ox, oy = origin
    ys, xs = np.nonzero(region == gi)
    r0, r1, c0, c1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    pad = 4
    pr0, pr1, pc0, pc1 = max(r0 - 8, 0), r1 + 8, max(c0 - 8, 0), c1 + 8
    pm = paper_mask[pr0:pr1, pc0:pc1]
    paper = np.median(sub[pr0:pr1, pc0:pc1][pm]) if pm.sum() > 20 else 240.0
    cy, cx = g['cl']['pix']; cy = cy - oy; cx = cx - ox
    cm = np.zeros(sub.shape, bool); cm[cy, cx] = True
    core = ndi.binary_erosion(cm[r0:r1, c0:c1])
    ink = np.median(sub[r0:r1, c0:c1][core]) if core.sum() >= 12 else np.percentile(sub[cy, cx], 30)
    patch = np.full((r1 - r0 + 2 * pad, c1 - c0 + 2 * pad), paper, float)
    m = region[r0:r1, c0:c1] == gi
    patch[pad:-pad, pad:-pad][m] = sub[r0:r1, c0:c1][m]
    v = np.clip((paper - patch) / max(paper - ink, 1), 0, 1)
    up = ndi.zoom(v, F, order=3, grid_mode=True, mode='grid-constant', cval=0.0)
    up = ndi.gaussian_filter(up, P['blur'] * F)
    # binary clean-up, then fold the decisions back into the continuous field
    B = up > 0.5
    fld = up.copy()
    if P['bridge']:
        r, lo = P['bridge']; rr = int(round(r * F))
        lab, n = ndi.label(B)
        if n:
            sizes = ndi.sum(B, lab, range(1, n + 1))
            sl = ndi.find_objects(lab); big = int(np.argmax(sizes))
            by0, by1 = sl[big][0].start, sl[big][0].stop
            def stacked(i):
                # dots and accents sit above/below the main stroke; hairline joins sit beside it
                y0, y1 = sl[i][0].start, sl[i][0].stop
                return min(y1, by1) - max(y0, by0) < 0.3 * (y1 - y0)
            minor = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s < 0.2 * sizes.max() or (i != big and stacked(i))])
            major = B & ~minor
            closed = ndi.binary_closing(np.pad(major, rr), structure=disk(rr))[rr:-rr, rr:-rr]
            add = closed & (up > lo) & ~ndi.binary_dilation(minor, structure=disk(rr)) & ~B
            fld[add] = np.maximum(fld[add], 0.5 + 0.5 * (up[add] - lo) / max(0.5 - lo, 1e-6) * 0.5 + 0.01)
            B = B | add
    lab, n = ndi.label(B)
    if n:
        sizes = ndi.sum(B, lab, range(1, n + 1))
        drop = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s < P['island'] * F * F])
        fld[drop] = np.minimum(fld[drop], 0.0); B &= ~drop
    hl, nh = ndi.label(~B)
    if nh:
        border = set(np.unique(np.concatenate([hl[0], hl[-1], hl[:, 0], hl[:, -1]])))
        sizes = ndi.sum(~B, hl, range(1, nh + 1))
        fill = np.isin(hl, [i + 1 for i, s in enumerate(sizes) if s < P['hole'] * F * F and (i + 1) not in border])
        fld[fill] = 1.0
    origin_src = (c0 - pad + ox, r0 - pad + oy)
    # hairline gaps the blur closed (dots of ! and ?): reopen them along the scan row
    for r in P.get('cuts', {}).get(g['name'], []):
        yy = (np.arange(fld.shape[0]) + 0.5) / F + origin_src[1]
        fld[(yy > r + 0.1) & (yy < r + 0.9), :] = 0.0
    return fld, origin_src, paper, ink


def offset_inward(poly, fld, e):
    """Move each contour point e px (source) toward the ink side, along the local normal."""
    if e == 0:
        return poly
    t = np.roll(poly, -1, 0) - np.roll(poly, 1, 0)
    t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
    nrm = np.stack([-t[:, 1], t[:, 0]], 1)            # one of the two normals
    d = 0.5 * F                                         # probe half a source px each side (field px)
    a = ndi.map_coordinates(fld, (poly + nrm * d / F * F).T[::-1], order=1)
    b = ndi.map_coordinates(fld, (poly - nrm * d / F * F).T[::-1], order=1)
    toward_ink = np.where((a > b)[:, None], nrm, -nrm)
    return poly + toward_ink * e * F


def trace_glyph2(g, region, sub, paper_mask, origin, P):
    fld, (ox, oy), paper, ink = ink_field(g, region, sub, paper_mask, origin, P)
    cs = measure.find_contours(np.pad(fld, 2), 0.5)
    contours = []
    for c in cs:
        if len(c) < 8:
            continue
        xy = np.stack([c[:, 1] - 2, c[:, 0] - 2], 1)          # (x, y) in upsampled px, centre coords
        if np.linalg.norm(xy[0] - xy[-1]) > 1e-6:
            continue                                          # open contour (shouldn't happen)
        xy = xy[:-1]
        xy = resample_closed(xy, 0.2 * F)
        xy = offset_inward(xy, fld, P['spread'])
        src = (xy + 0.5) / F + np.array([ox, oy])            # -> source edge coordinates
        area = 0.5 * np.sum(src[:, 0] * np.roll(src[:, 1], -1) - np.roll(src[:, 0], -1) * src[:, 1])
        if abs(area) < 0.6:
            continue
        curves = contour_to_curves(src, ds=0.2, corner_win=0.8, corner_deg=P['corner'], sigma=P['sigma'], tol=P['tol'])
        contours.append(curves)
    return dict(rec=curves_to_recording(contours), paper=paper, ink=ink)


def trace_font2(font):
    lines = segment(font, verbose=False)
    glyphs, region, sub, paper_mask, origin = regions(font, lines)
    P = PARAMS2[font]
    out = []
    names = [L['names'] for L in lines]
    for i, g in enumerate(glyphs):
        g['idx'] = i + 1
        Pg = dict(P, **P.get('glyph', {}).get(g['name'], {}))
        t = trace_glyph2(g, region, sub, paper_mask, origin, Pg)
        out.append(dict(name=g['name'], line=g['line']['names'], rec=t['rec'], paper=t['paper'], ink=t['ink'],
                        line_idx=names.index(g['line']['names'])))
    return out


if __name__ == '__main__':
    os.makedirs('traced', exist_ok=True)
    for font in sys.argv[1:]:
        res = trace_font2(font)
        pickle.dump(res, open(f'traced/{font}.pkl', 'wb'))
        segs = sum(len(r['rec']) for r in res)
        print(font, len(res), 'glyphs,', segs, 'segments')
