"""Small vector-geometry kit for synthesised glyphs (pathops Paths, font units)."""
import math
import numpy as np
import pathops
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import RecordingPen

K = 0.5522847498  # cubic circle constant


def ellipse(cx, cy, rx, ry):
    p = pathops.Path()
    p.moveTo(cx + rx, cy)
    p.cubicTo(cx + rx, cy + K * ry, cx + K * rx, cy + ry, cx, cy + ry)
    p.cubicTo(cx - K * rx, cy + ry, cx - rx, cy + K * ry, cx - rx, cy)
    p.cubicTo(cx - rx, cy - K * ry, cx - K * rx, cy - ry, cx, cy - ry)
    p.cubicTo(cx + K * rx, cy - ry, cx + rx, cy - K * ry, cx + rx, cy)
    p.close()
    return p


def circle(cx, cy, r):
    return ellipse(cx, cy, r, r)


def polygon(pts):
    p = pathops.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    return p


def op(a, b, kind):
    return pathops.op(a, b, kind, fix_winding=True, keep_starting_points=False, clockwise=False)


def union(*paths):
    acc = pathops.Path()
    for q in paths:
        acc = op(acc, q, pathops.PathOp.UNION)
    return acc


def difference(a, b):
    return op(a, b, pathops.PathOp.DIFFERENCE)


def transform(p, m):
    """m = (xx, xy, yx, yy, dx, dy) affine (fontTools convention)."""
    q = pathops.Path()
    p.draw(TransformPen(q.getPen(), m))
    # mirroring flips contour direction; simplify restores a consistent winding
    return pathops.simplify(q, fix_winding=True, keep_starting_points=False, clockwise=False)


def rotate(p, deg, cx=0.0, cy=0.0):
    a = math.radians(deg); c, s = math.cos(a), math.sin(a)
    return transform(p, (c, s, -s, c, cx - c * cx + s * cy, cy - s * cx - c * cy))


def wedge(p0, p1, r0, r1, rounded=True):
    """Tapered stroke from p0 (radius r0) to p1 (radius r1)."""
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    d = np.linalg.norm(p1 - p0); u = (p1 - p0) / d; n = np.array([-u[1], u[0]])
    if rounded:
        cb = (r0 - r1) / d; sb = math.sqrt(max(0.0, 1 - cb * cb))
        va = u * cb + n * sb; vb = u * cb - n * sb
        quad = polygon([tuple(p0 + r0 * va), tuple(p1 + r1 * va), tuple(p1 + r1 * vb), tuple(p0 + r0 * vb)])
        return union(quad, circle(*p0, r0), circle(*p1, r1))
    return polygon([tuple(p0 + r0 * n), tuple(p1 + r1 * n), tuple(p1 - r1 * n), tuple(p0 - r0 * n)])


def slanted_bar(x0, x1, yc, h, cut=0.0):
    """Horizontal bar with ends sheared by `cut` units (parallelogram), for chiselled styles."""
    return polygon([(x0 + cut, yc - h / 2), (x1 + cut, yc - h / 2), (x1 - cut, yc + h / 2), (x0 - cut, yc + h / 2)])


def capsule(x0, x1, yc, h):
    r = h / 2
    return union(polygon([(x0, yc - r), (x1, yc - r), (x1, yc + r), (x0, yc + r)]), circle(x0, yc, r), circle(x1, yc, r))


def crescent(y0, y1, depth, thick, end_thick, n=48):
    """Left parenthesis: a curved stroke bulging left, spanning y0..y1.
    depth = horizontal bulge of the centre line; thickness tapers to end_thick."""
    pts_out, pts_in = [], []
    h = (y1 - y0) / 2; yc = (y0 + y1) / 2
    for i in range(n + 1):
        t = -1 + 2 * i / n                       # -1..1 along the stroke
        y = yc + h * t
        xc = depth * (1 - t * t)                 # parabola-ish centre line, bulging left
        w = end_thick + (thick - end_thick) * (1 - t * t) ** 0.8
        pts_out.append((-xc - w / 2, y)); pts_in.append((-xc + w / 2, y))
    pts = pts_out + pts_in[::-1]
    p = polygon(pts)
    return pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)


def paren_arc(y0, y1, depth, thick, taper=1.10):
    """Smooth left parenthesis from two ellipse arcs: outer bulge `depth`,
    mid-stroke thickness `thick`, ends thinned by a taller inner ellipse; blunt ends."""
    h = (y1 - y0) / 2; yc = (y0 + y1) / 2; H = h * 1.18
    rx = depth / (1 - math.sqrt(1 - (h / H) ** 2))
    outer = ellipse(rx, yc, rx, H)
    inner = ellipse(rx + thick, yc, rx * 1.02, H * taper)
    band = polygon([(-10, y0), (rx * 3, y0), (rx * 3, y1), (-10, y1)])
    return op(difference(outer, inner), band, pathops.PathOp.INTERSECTION)


def recording(p):
    rec = RecordingPen(); p.draw(rec); return rec.value
