import numpy as np
from PIL import Image, ImageDraw

def flatten(rec, steps=12):
    """RecordingPen value -> list of polylines (closed contours)."""
    polys, cur, pt = [], [], None
    for op, args in rec:
        if op == 'moveTo':
            cur = [args[0]]; pt = args[0]
        elif op == 'lineTo':
            cur.append(args[0]); pt = args[0]
        elif op == 'curveTo':
            *ctrls, end = args
            p0 = np.array(pt); c = [np.array(p) for p in args]
            if len(c) == 3:
                for t in np.linspace(0, 1, steps)[1:]:
                    q = (1-t)**3*p0 + 3*(1-t)**2*t*c[0] + 3*(1-t)*t*t*c[1] + t**3*c[2]
                    cur.append(tuple(q))
            else:
                cur.append(tuple(end))
            pt = end
        elif op == 'qCurveTo':
            # quadratic spline with implied on-curve points
            pts = [np.array(pt)] + [np.array(p) for p in args]
            offs = pts[1:-1]; end = pts[-1]; start = pts[0]
            segs = []; s = start
            for i, o in enumerate(offs):
                e = end if i == len(offs)-1 else (o + offs[i+1]) / 2
                for t in np.linspace(0, 1, steps)[1:]:
                    cur.append(tuple((1-t)**2*s + 2*(1-t)*t*o + t*t*e))
                s = e
            pt = tuple(end)
        elif op in ('closePath', 'endPath'):
            if cur: polys.append(cur)
            cur = []
    if cur: polys.append(cur)
    return polys

def raster(polys, size, xform):
    """Even-odd fill of polylines. xform maps (x, y) -> pixel (px, py)."""
    acc = np.zeros(size[::-1], bool)
    for p in polys:
        im = Image.new('1', size, 0)
        ImageDraw.Draw(im).polygon([xform(q) for q in p], fill=1)
        acc ^= np.asarray(im)
    return acc
