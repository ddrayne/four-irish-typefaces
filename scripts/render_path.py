import numpy as np
from PIL import Image, ImageDraw
from fontTools.pens.recordingPen import RecordingPen
from outline_util import flatten, raster
from glyphs import bounds
def render(paths, scale=0.5, pad=20, labels=None, cols=None):
    """Render list of pathops Paths side by side (font units, y up)."""
    tiles = []
    for i, p in enumerate(paths):
        rec = RecordingPen(); p.draw(rec); polys = flatten(rec.value)
        x0, y0, x1, y1 = bounds(p)
        W, H = int((x1-x0)*scale)+2*pad, int((y1-y0)*scale)+2*pad
        m = raster(polys, (W, H), lambda q: ((q[0]-x0)*scale+pad, (y1-q[1])*scale+pad))
        im = Image.fromarray(np.where(m, 0, 255).astype(np.uint8)).convert('RGB')
        if labels: ImageDraw.Draw(im).text((2, 2), labels[i], fill=(220, 0, 0))
        tiles.append(im)
    if cols:
        rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
        W = max(sum(t.width + 10 for t in r) for r in rows); Hs = [max(t.height for t in r) + 10 for r in rows]
        out = Image.new('RGB', (W, sum(Hs)), 'white'); y = 0
        for r, h in zip(rows, Hs):
            x = 0
            for t in r: out.paste(t, (x, y)); x += t.width + 10
            y += h
        return out
    W = sum(t.width for t in tiles) + 10*len(tiles); H = max(t.height for t in tiles)
    out = Image.new('RGB', (W, H), 'white'); x = 0
    for t in tiles: out.paste(t, (x, 0)); x += t.width + 10
    return out
