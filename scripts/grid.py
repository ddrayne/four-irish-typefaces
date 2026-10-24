"""Every glyph of a built font in a grid: outline filled, advance box, baseline / x-height / cap lines.

usage: python grid.py FONTFILE OUTPREFIX [per_sheet]
"""
import sys, unicodedata, numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from outline_util import flatten, raster

path, out = sys.argv[1], sys.argv[2]; per = int(sys.argv[3]) if len(sys.argv) > 3 else 120
tt = TTFont(path); gs = tt.getGlyphSet(); cmap = tt.getBestCmap(); rev = {}
for cp, g in sorted(cmap.items()):
    rev.setdefault(g, cp)
os2 = tt['OS/2']; xh, cap = os2.sxHeight, os2.sCapHeight
asc, desc = tt['hhea'].ascent, tt['hhea'].descent
order = [g for g in tt.getGlyphOrder() if g not in ('.notdef',)]
# characters first in code point order, then unencoded glyphs
order = sorted(order, key=lambda g: (g not in rev, rev.get(g, 0), g))
lab = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
k = 0.085; CW, CH = 120, int((asc - desc) * k) + 34; COLS = 12
for sheet in range(0, len(order), per):
    names = order[sheet:sheet + per]; rows = (len(names) + COLS - 1) // COLS
    im = Image.new('RGB', (COLS * CW, rows * CH), 'white'); d = ImageDraw.Draw(im)
    for i, g in enumerate(names):
        cx, cy = (i % COLS) * CW, (i // COLS) * CH
        adv = tt['hmtx'][g][0]; x0 = cx + (CW - adv * k) / 2; base = cy + asc * k + 6
        for y, col in ((0, (120, 200, 120)), (xh, (190, 210, 240)), (cap, (240, 200, 200))):
            d.line([(cx + 4, base - y * k), (cx + CW - 4, base - y * k)], fill=col)
        d.rectangle([x0, base - asc * k, x0 + adv * k, base - desc * k], outline=(225, 225, 225))
        rec = RecordingPen(); gs[g].draw(rec); polys = flatten(rec.value, 16)
        if polys:
            m = raster(polys, (CW, CH), lambda q: (x0 - cx + q[0] * k, base - cy - q[1] * k))
            tile = np.asarray(im.crop((cx, cy, cx + CW, cy + CH))).copy(); tile[m] = (0, 0, 0)
            im.paste(Image.fromarray(tile), (cx, cy))
        cp = rev.get(g); txt = (f'{cp:04X} ' if cp else '') + g
        d.text((cx + 3, cy + CH - 15), txt[:20], fill=(170, 0, 0), font=lab)
    im.save(f'{out}_{sheet // per:02d}.png')
print(len(order), 'glyphs ->', (len(order) + per - 1) // per, 'sheets')
