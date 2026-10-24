"""Third-generation tracer: the v2 sub-pixel edge, redrawn by curvefit3 (lines, crisp corners, few curves)."""
import traced
import paths
import os, pickle, sys
import numpy as np
from skimage import measure
from seg import segment
from trace import regions
from trace2 import PARAMS2, F, ink_field, offset_inward
from curvefit import resample_closed, curves_to_recording
from curvefit3 import contour_to_curves3, contour_to_curves4

# per-face redraw settings (source px); anything not given uses contour_to_curves3's defaults
PARAMS3 = {
    'kilfane': dict(cutoff=10, corner_deg=55, rms_tol=0.1, max_tol=0.3, line_tol=0.25, line_bulge=0.08, line_min=6.0, snap_deg=2.0,
                    # a toner speck fused to the lower left of O; a darker toner pixel on the em dash's left end
                    glyph={'O': dict(erase=[[(86, 192.5), (90.3, 192.5), (96.5, 198.8), (86, 198.8)]]),
                           'ornament': dict(erase=[[(316.4, 253.8), (321.6, 253.8), (321.6, 256.5), (316.4, 256.5)]])}),
    'tuam':    dict(cutoff=10, corner_deg=50, rms_tol=0.1, max_tol=0.3, line_tol=0.25, line_bulge=0.08, line_min=3.5, snap_deg=2.0),
    'carrick': dict(cutoff=10, corner_deg=50, rms_tol=0.1, max_tol=0.3, line_tol=0.25, line_bulge=0.08, line_min=6.0, snap_deg=2.0),
    'ceili':   dict(cutoff=10, corner_deg=55, rms_tol=0.1, max_tol=0.3, line_tol=0.25, line_bulge=0.08, line_min=6.0, snap_deg=2.0),
}


def erase(fld, origin, polys):
    """Blank scan damage (toner specks fused to a letter) inside polygons given in source px."""
    from skimage.draw import polygon as fill_poly
    ox, oy = origin
    for poly in polys:
        poly = np.asarray(poly, float)
        rr, cc = fill_poly((poly[:, 1] - oy) * F - 0.5, (poly[:, 0] - ox) * F - 0.5, fld.shape)
        fld[rr, cc] = 0.0
    return fld


def trace_glyph3(g, region, sub, paper_mask, origin, P, P3):
    fld, (ox, oy), paper, ink = ink_field(g, region, sub, paper_mask, origin, P)
    P3 = dict(P3)
    if 'erase' in P3:
        fld = erase(fld, (ox, oy), P3.pop('erase'))
    cs = measure.find_contours(np.pad(fld, 2), 0.5)
    contours = []
    for c in cs:
        if len(c) < 8:
            continue
        xy = np.stack([c[:, 1] - 2, c[:, 0] - 2], 1)
        if np.linalg.norm(xy[0] - xy[-1]) > 1e-6:
            continue
        xy = resample_closed(xy[:-1], 0.2 * F)
        xy = offset_inward(xy, fld, P['spread'])
        src = (xy + 0.5) / F + np.array([ox, oy])
        area = 0.5 * np.sum(src[:, 0] * np.roll(src[:, 1], -1) - np.roll(src[:, 0], -1) * src[:, 1])
        if abs(area) < 0.6:
            continue
        fit = contour_to_curves4 if P3.get('v4', True) else contour_to_curves3
        contours.append(fit(src, **{k: v for k, v in P3.items() if k != 'v4'}))
    return dict(rec=curves_to_recording(contours), paper=paper, ink=ink)


def trace_font3(font, only=None):
    lines = segment(font, verbose=False)
    glyphs, region, sub, paper_mask, origin = regions(font, lines)
    P = PARAMS2[font]; P3base = PARAMS3[font]
    out = []
    names = [L['names'] for L in lines]
    for i, g in enumerate(glyphs):
        g['idx'] = i + 1
        if only and g['name'] not in only:
            continue
        Pg = dict(P, **P.get('glyph', {}).get(g['name'], {}))
        P3 = dict(P3base, **P3base.get('glyph', {}).get(g['name'], {})) if 'glyph' in P3base else dict(P3base)
        P3.pop('glyph', None)
        t = trace_glyph3(g, region, sub, paper_mask, origin, Pg, P3)
        out.append(dict(name=g['name'], line=g['line']['names'], rec=t['rec'], paper=t['paper'], ink=t['ink'],
                        line_idx=names.index(g['line']['names'])))
    return out


if __name__ == '__main__':
    os.makedirs(paths.TRACED, exist_ok=True)
    for font in sys.argv[1:]:
        res = trace_font3(font)
        traced.save(font, res)
        segs = sum(len(r['rec']) for r in res)
        print(font, len(res), 'glyphs,', segs, 'segments')
