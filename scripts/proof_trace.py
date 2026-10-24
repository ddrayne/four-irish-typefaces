import traced
import paths
import os
import sys, pickle, numpy as np
from PIL import Image, ImageDraw
from seg import GRAY
from outline_util import flatten
f = 6
for font in sys.argv[1:]:
    res = traced.records(font)
    tiles = []
    for r in res:
        polys = flatten(r['rec'])
        xs = [p[0] for P in polys for p in P]; ys = [p[1] for P in polys for p in P]
        x0, x1, y0, y1 = int(min(xs))-2, int(max(xs))+3, int(min(ys))-2, int(max(ys))+3
        crop = Image.fromarray(GRAY[y0:y1, x0:x1].astype(np.uint8)).resize(((x1-x0)*f, (y1-y0)*f), Image.LANCZOS).convert('RGB')
        d = ImageDraw.Draw(crop)
        for P in polys:
            pts = [((x-x0)*f, (y-y0)*f) for x, y in P]
            d.line(pts + [pts[0]], fill=(230, 0, 0), width=2)
        d.text((2, 2), r['name'], fill=(0, 0, 255))
        tiles.append(crop)
    # pack tiles into rows
    W = 1800; rows = []; cur = []; cw = 0
    for t in tiles:
        if cw + t.width > W and cur: rows.append(cur); cur = []; cw = 0
        cur.append(t); cw += t.width + 6
    rows.append(cur)
    H = sum(max(t.height for t in r) + 6 for r in rows)
    sheet = Image.new('RGB', (W, H), 'white'); y = 0
    for r in rows:
        x = 0
        for t in r: sheet.paste(t, (x, y)); x += t.width + 6
        y += max(t.height for t in r) + 6
    sheet.save(os.path.join(paths.VIEW, f'trace_{font}.png')); print(font, sheet.size)
