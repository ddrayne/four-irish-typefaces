"""Per-glyph audit against the flyer: for every glyph traced from the sheet, the scan, a
difference map (orange = ink on the scan the font lacks, blue = font ink the scan lacks)
and the font glyph itself, all on the scan's own grid (8 tile px per source px).

usage: python audit_glyph.py FONT [glyph,glyph,...]   -> aud/<font>_NN.png + a table on stdout
"""
import traced
import paths
import os, sys, pickle, numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from seg import segment, GRAY
from trace import regions
from trace2 import PARAMS2, F, ink_field
from metrics import line_baselines
from glyphs import SCALE
from outline_util import flatten, raster
from build2 import FONTS, OUT

NAME = {'ornament': 'uniE000'}
LABEL = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15) if os.path.exists(
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf') else ImageFont.load_default()


def font_polys(gs, name):
    rec = RecordingPen(); gs[name].draw(rec)
    return flatten(rec.value, steps=24)


def audit(font, only=None, fontpath=None):
    cfg = FONTS[font]; s = SCALE[font]
    fontpath = fontpath or f'{OUT}/{cfg["ps"]}-Regular.otf'
    tt = TTFont(fontpath); gs = tt.getGlyphSet()
    res = traced.records(font); base = line_baselines(res)
    byname = {r['name']: r for r in res}
    lines = segment(font, verbose=False)
    glyphs, region, sub, paper_mask, origin = regions(font, lines)
    P = PARAMS2[font]; tiles = []; rows = []
    for i, g in enumerate(glyphs):
        g['idx'] = i + 1
        name = g['name']
        if only and name not in only:
            continue
        fname = NAME.get(name, name)
        if fname not in gs:
            continue
        Pg = dict(P, **P.get('glyph', {}).get(name, {}))
        fld, (ox, oy), paper, ink = ink_field(g, region, sub, paper_mask, origin, Pg)
        H, W = fld.shape
        target = ndi.distance_transform_edt(fld > 0.5) > Pg['spread'] * F
        r = byname[name]; b0 = base[r['line_idx']]
        polys = font_polys(gs, fname)
        if not polys:
            continue
        xs = [p[0] for q in polys for p in q]; X0 = min(xs)
        def fit(dx, dy):
            xf = lambda q: (((q[0] - X0) / s + r['b'][0] + dx - ox) * F, ((b0 + dy - q[1] / s) - oy) * F)
            m = raster(polys, (W, H), xf)
            return (m & target).sum() / max((m | target).sum(), 1), dx, dy, m, xf
        # best registration (source px): coarse grid, then refine around the winner
        best = max((fit(dx, dy) for dx in np.arange(-2, 2.01, 0.25) for dy in np.arange(-1.5, 1.51, 0.25)), key=lambda t: t[0])
        best = max([best] + [fit(best[1] + a, best[2] + b) for a in (-0.125, 0, 0.125) for b in (-0.125, 0, 0.125)], key=lambda t: t[0])
        iou, dx, dy, m, xf = best
        scan_only = target & ~m; font_only = m & ~target
        # thickness of disagreement: how far (source px) the worst miss reaches into each region
        depth = lambda a: float(ndi.distance_transform_edt(a).max() / F) if a.any() else 0.0
        rows.append((name, round(float(iou), 3), round(depth(scan_only), 2), round(depth(font_only), 2),
                     round(float(m.sum() / max(target.sum(), 1) - 1) * 100, 1), round(float(dx), 2), round(float(dy), 2)))
        # panels
        crop = GRAY[oy:oy + H // F, ox:ox + W // F].astype(np.uint8)
        scan = Image.fromarray(crop).resize((W, H), Image.BICUBIC).convert('RGB')
        diff = np.full((H, W, 3), 255, np.uint8)
        diff[m & target] = (70, 70, 70); diff[scan_only] = (255, 140, 0); diff[font_only] = (0, 120, 255)
        diff = Image.fromarray(diff)
        ImageDraw.Draw(diff).line([(0, (b0 - oy) * F), (W, (b0 - oy) * F)], fill=(0, 170, 0), width=1)
        fill = Image.fromarray(np.where(m, 0, 255).astype(np.uint8)).convert('RGB')
        d = ImageDraw.Draw(scan)
        for q in polys:
            pts = [xf(p) for p in q]; d.line(pts + [pts[0]], fill=(230, 0, 0), width=1)
        gap = 6
        tile = Image.new('RGB', (3 * W + 2 * gap, H + 22), 'white')
        tile.paste(scan, (0, 22)); tile.paste(diff, (W + gap, 22)); tile.paste(fill, (2 * W + 2 * gap, 22))
        ImageDraw.Draw(tile).text((2, 2), f'{name}  IoU {iou:.3f}  miss {rows[-1][2]:.2f}px  extra {rows[-1][3]:.2f}px  area {rows[-1][4]:+.1f}%  dy {dy:+.2f}',
                                  fill=(160, 0, 0), font=LABEL)
        tiles.append(tile)
    # pack into sheets
    os.makedirs(paths.AUDIT, exist_ok=True)
    Wmax, Hmax = 1500, 1650; sheets = []; cur = []; x = y = rowh = 0
    def flush():
        if cur:
            Wt = max(px + t.width for t, px, py in cur); Ht = max(py + t.height for t, px, py in cur)
            sh = Image.new('RGB', (Wt, Ht), (200, 200, 200))
            for t, px, py in cur:
                sh.paste(t, (px, py))
            sheets.append(sh)
    for t in tiles:
        if x and x + t.width > Wmax:
            x = 0; y += rowh + 10; rowh = 0
        if y and y + t.height > Hmax:
            flush(); cur = []; x = y = rowh = 0
        cur.append((t, x, y)); x += t.width + 10; rowh = max(rowh, t.height)
    flush()
    for k, sh in enumerate(sheets):
        sh.save(os.path.join(paths.AUDIT, f'{font}_{k:02d}.png'))
    return rows, len(sheets)


if __name__ == '__main__':
    font = sys.argv[1]; only = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
    rows, n = audit(font, only)
    print(f'{font}: {len(rows)} glyphs, {n} sheets')
    print(f'  {"glyph":10} {"IoU":>6} {"miss":>5} {"extra":>5} {"area%":>6} {"dx":>5} {"dy":>5}')
    for r in sorted(rows, key=lambda r: r[1]):
        print(f'  {r[0]:10} {r[1]:6.3f} {r[2]:5.2f} {r[3]:5.2f} {r[4]:6.1f} {r[5]:5.2f} {r[6]:5.2f}')
