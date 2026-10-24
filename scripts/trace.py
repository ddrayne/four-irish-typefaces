"""Trace segmented specimen glyphs into Bézier outlines (source-pixel coordinates)."""
import os, re, subprocess, tempfile, pickle, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path
from specs import SPECS
from seg import segment, GRAY

PARAMS = {
 'kilfane': dict(F=8, sigma=0.7, alpha=1.0, opt=0.4, hole=3.0, island=3.0, bridge=None),
 'tuam':    dict(F=8, sigma=0.65, alpha=0.8, opt=0.3, hole=2.5, island=3.0, bridge=(1.2, 0.25)),
 'carrick': dict(F=8, sigma=0.7, alpha=0.8, opt=0.3, hole=4.0, island=4.0, bridge=None),
 'ceili':   dict(F=8, sigma=0.5, alpha=1.0, opt=0.3, hole=1.5, island=2.0, bridge=(0.8, 0.3)),
}
R = 3  # px of grey edge taken around each glyph's ink

def disk(r):
    y, x = np.ogrid[-r:r+1, -r:r+1]; return x*x + y*y <= r*r

def regions(font, lines):
    x0, y0, x1, y1 = SPECS[font]['box']; T = SPECS[font]['T']
    sub = GRAY[y0:y1, x0:x1]
    lab = np.zeros(sub.shape, int); glyphs = []
    for L in lines:
        for name, k in zip(L['names'], L['clusters']):
            glyphs.append(dict(name=name, line=L, cl=k))
            ys, xs = k['pix']; lab[ys-y0, xs-x0] = len(glyphs)
    lab[(sub < T) & (lab == 0)] = len(glyphs) + 1          # unclaimed specks
    dist, (iy, ix) = ndi.distance_transform_edt(lab == 0, return_indices=True)
    region = np.where(dist <= R, lab[iy, ix], 0)
    paper_mask = dist > 3
    return glyphs, region, sub, paper_mask, (x0, y0)

def potrace(B, alpha, opt):
    h, w = B.shape
    with tempfile.TemporaryDirectory() as td:
        pbm = os.path.join(td, 'g.pbm'); svg = os.path.join(td, 'g.svg')
        with open(pbm, 'wb') as f:
            f.write(b'P4\n%d %d\n' % (w, h)); f.write(np.packbits(B, axis=1).tobytes())
        subprocess.run(['potrace', '-b', 'svg', '-a', str(alpha), '-O', str(opt), '-t', '2',
                        '-u', '10', '--flat', '-o', svg, pbm], check=True)
        txt = open(svg).read()
    m = re.search(r'translate\(([-\d.]+),([-\d.]+)\) scale\(([-\d.]+),([-\d.]+)\)', txt)
    tx, ty, sx, sy = map(float, m.groups())
    ds = re.findall(r'<path d="([^"]+)"', txt, re.S)
    return ds, (tx, ty, sx, sy)

def trace_glyph(g, region, sub, paper_mask, origin, P):
    gi = g['idx']; ox, oy = origin
    ys, xs = np.nonzero(region == gi)
    r0, r1, c0, c1 = ys.min(), ys.max()+1, xs.min(), xs.max()+1
    pad = 4
    # local paper and ink levels
    pr0, pr1, pc0, pc1 = max(r0-8, 0), r1+8, max(c0-8, 0), c1+8
    pm = paper_mask[pr0:pr1, pc0:pc1]
    paper = np.median(sub[pr0:pr1, pc0:pc1][pm]) if pm.sum() > 20 else 240.0
    cy, cx = g['cl']['pix']; cy = cy - oy; cx = cx - ox
    cm = np.zeros(sub.shape, bool); cm[cy, cx] = True
    core = ndi.binary_erosion(cm[r0:r1, c0:c1])
    vals = sub[r0:r1, c0:c1][core] if core.sum() >= 12 else sub[cy, cx]
    ink = np.median(vals) if core.sum() >= 12 else np.percentile(vals, 30)
    patch = np.full((r1-r0+2*pad, c1-c0+2*pad), paper, float)
    m = region[r0:r1, c0:c1] == gi
    patch[pad:-pad, pad:-pad][m] = sub[r0:r1, c0:c1][m]
    v = np.clip((paper - patch) / max(paper - ink, 1), 0, 1)
    F = P['F']
    up = ndi.zoom(v, F, order=3, grid_mode=True, mode='grid-constant', cval=0.0)
    up = ndi.gaussian_filter(up, P['sigma']*F)
    B = up > 0.5
    if P['bridge']:
        # restore faint hairline joins between major strokes, but never fuse
        # dots/accents (minor pieces) onto their letters
        r, lo = P['bridge']; rr = int(round(r*F))
        lab, n = ndi.label(B)
        if n:
            sizes = ndi.sum(B, lab, range(1, n+1))
            minor = np.isin(lab, [i+1 for i, s in enumerate(sizes) if s < 0.2*sizes.max()])
            major = B & ~minor
            closed = ndi.binary_closing(np.pad(major, rr), structure=disk(rr))[rr:-rr, rr:-rr]
            add = closed & (up > lo) & ~ndi.binary_dilation(minor, structure=disk(rr))
            B = B | add
    lab, n = ndi.label(B)
    if n:
        sizes = ndi.sum(B, lab, range(1, n+1))
        B = np.isin(lab, [i+1 for i, s in enumerate(sizes) if s >= P['island']*F*F])
    hl, nh = ndi.label(~B)
    if nh:
        border = set(np.unique(np.concatenate([hl[0], hl[-1], hl[:, 0], hl[:, -1]])))
        sizes = ndi.sum(~B, hl, range(1, nh+1))
        small = [i+1 for i, s in enumerate(sizes) if s < P['hole']*F*F and (i+1) not in border]
        B = B | np.isin(hl, small)
    ds, (tx, ty, sx, sy) = potrace(B, P['alpha'], P['opt'])
    # potrace coords -> upscaled svg px -> source sheet coords (col, row), y down
    rc = RecordingPen()
    a = sx / F; d = sy / F; e = (tx) / F + (c0 - pad + ox); f = ty / F + (r0 - pad + oy)
    tp = TransformPen(rc, (a, 0, 0, d, e, f))
    for dd in ds: parse_path(dd, tp)
    return dict(rec=rc.value, paper=paper, ink=ink, bitmap=B, up_origin=(c0-pad+ox, r0-pad+oy))

def trace_font(font):
    lines = segment(font, verbose=False)
    glyphs, region, sub, paper_mask, origin = regions(font, lines)
    P = PARAMS[font]
    out = []
    for i, g in enumerate(glyphs):
        g['idx'] = i + 1
        t = trace_glyph(g, region, sub, paper_mask, origin, P)
        out.append(dict(name=g['name'], line=g['line']['names'], rec=t['rec'],
                        paper=t['paper'], ink=t['ink'], line_idx=[L['names'] for L in lines].index(g['line']['names'])))
    return out

if __name__ == '__main__':
    os.makedirs('traced', exist_ok=True)
    for font in sys.argv[1:]:
        res = trace_font(font)
        pickle.dump(res, open(f'traced/{font}.pkl', 'wb'))
        n_nodes = sum(len(r['rec']) for r in res)
        print(font, len(res), 'glyphs,', n_nodes, 'segments; ink/paper medians',
              int(np.median([r['ink'] for r in res])), int(np.median([r['paper'] for r in res])))
