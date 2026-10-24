"""Data for the test page: every character of each face (name, advance, where it came from) and,
for each glyph on the 1978 flyer, its outline registered on the scan in flyer pixels, so the page
can lay the 2026 outline over the 1978 print.

usage: python site_data.py FONTDIR OUTDIR
"""
import traced
import json, os, pickle, sys, unicodedata
import numpy as np
from scipy import ndimage as ndi
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from seg import segment
from trace import regions
from trace2 import PARAMS2, F, ink_field
from metrics import line_baselines
from glyphs import SCALE
from outline_util import flatten, raster
from build2 import FONTS, Font2

SKIP = {'ornament', 'DOTS', 'semicolon'}          # not glyphs of the font (or rebuilt from their parts)


def overlays(key, tt):
    gs = tt.getGlyphSet(); s = SCALE[key]
    res = traced.records(key); base = line_baselines(res); byname = {r['name']: r for r in res}
    lines = segment(key, verbose=False)
    glyphs, region, sub, paper_mask, origin = regions(key, lines)
    out = {}
    for i, g in enumerate(glyphs):
        g['idx'] = i + 1
        name = g['name']
        if name in SKIP or name not in gs:
            continue
        P = dict(PARAMS2[key], **PARAMS2[key].get('glyph', {}).get(name, {}))
        fld, (ox, oy), paper, ink = ink_field(g, region, sub, paper_mask, origin, P)
        H, W = fld.shape
        target = ndi.distance_transform_edt(fld > 0.5) > P['spread'] * F
        r = byname[name]; b0 = base[r['line_idx']]
        rec = RecordingPen(); gs[name].draw(rec); polys = flatten(rec.value, 24)
        X0 = min(p[0] for q in polys for p in q)
        def fit(dx, dy):
            xf = lambda q: (((q[0] - X0) / s + r['b'][0] + dx - ox) * F, ((b0 + dy - q[1] / s) - oy) * F)
            m = raster(polys, (W, H), xf)
            return (m & target).sum() / max((m | target).sum(), 1), dx, dy
        best = max((fit(dx, dy) for dx in np.arange(-2, 2.01, 0.25) for dy in np.arange(-1.5, 1.51, 0.25)), key=lambda t: t[0])
        best = max([best] + [fit(best[1] + a, best[2] + b) for a in (-0.125, 0, 0.125) for b in (-0.125, 0, 0.125)], key=lambda t: t[0])
        iou, dx, dy = best
        # font units -> flyer pixels
        m = (1 / s, 0, 0, -1 / s, r['b'][0] + dx - X0 / s, b0 + dy)
        sp = SVGPathPen(None, ntos=lambda v: f'{v:.2f}'.rstrip('0').rstrip('.'))
        gs[name].draw(TransformPen(sp, m))
        x0, y0, x1, y1 = r['b'][0] - 3, r['b'][1] - 3, r['b'][2] + 3, r['b'][3] + 3
        out[name] = dict(r=[round(x0, 1), round(y0, 1), round(x1 - x0, 1), round(y1 - y0, 1)], d=sp.getCommands(),
                         iou=round(float(iou), 3), base=round(b0 + dy, 2))
    return out


def pieces(key):
    """Where each accent piece sits on the flyer (for labels on the page)."""
    if key not in Font2.PIECES:
        return None
    res = traced.records(key); base = line_baselines(res); s = SCALE[key]
    r = [r for r in res if r['name'] == 'ornament'][0]; b0 = base[r['line_idx']]
    # the trace bounds left edge is the font-unit origin used by Font2.PIECES
    x0 = r['b'][0]
    pts = [dict(n=n, x=round(x0 + cx / s, 1), y=round(b0 - cy / s, 1)) for n, (cx, cy) in Font2.PIECES[key].items()]
    return dict(r=[round(r['b'][0] - 4, 1), round(r['b'][1] - 4, 1), round(r['b'][2] - r['b'][0] + 8, 1),
                   round(r['b'][3] - r['b'][1] + 8, 1)], pts=pts)


def inventory(key, tt, prov):
    cm = tt.getBestCmap(); hm = tt['hmtx']
    rows = []
    for cp, g in sorted(cm.items()):
        if cp in (0x20, 0xA0):
            continue
        ch = chr(cp)
        try:
            uname = unicodedata.name(ch)
        except ValueError:
            uname = ''
        rows.append(dict(c=ch, cp=cp, g=g, u=uname.title(), a=hm[g][0], k=unicodedata.category(ch)[0],
                         p=prov.get(g, ['made', ''])))
    alts = []
    cfg = FONTS[key]
    rev = {}
    for cp, g in sorted(cm.items()):
        rev.setdefault(g, cp)
    for tag, label, mapping in cfg.get('sets', []):
        for b, alt in mapping.items():
            alts.append(dict(c=chr(rev[b]), g=alt, f=tag, l=label, a=hm[alt][0], p=prov.get(alt, ['made', ''])))
    return rows, alts


def main(fontdir, outdir):
    os.makedirs(outdir, exist_ok=True)
    for key, cfg in FONTS.items():
        ps = cfg['ps']
        tt = TTFont(os.path.join(fontdir, f'{ps}-Regular.otf'))
        prov = json.load(open(os.path.join(fontdir, f'{ps}-Regular.provenance.json')))
        os2 = tt['OS/2']; hh = tt['hhea']
        rows, alts = inventory(key, tt, prov)
        ov = overlays(key, tt)
        data = dict(key=key, family=cfg['family'], upm=tt['head'].unitsPerEm, asc=hh.ascent, desc=hh.descent,
                    xh=os2.sxHeight, cap=os2.sCapHeight, unicase=cfg['unicase'], chars=rows, alts=alts,
                    flyer=ov, pieces=pieces(key))
        path = os.path.join(outdir, f'{key}.json')
        json.dump(data, open(path, 'w'), ensure_ascii=False, separators=(',', ':'))
        print(key, len(rows), 'chars', len(alts), 'alternates', len(ov), 'flyer glyphs',
              f'mean match {np.mean([v["iou"] for v in ov.values()]):.3f}', f'{os.path.getsize(path) / 1024:.0f} KB')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
