"""Diacritical marks drawn in each face's own stroke style.

Every mark is returned centred on x = 0. Top marks sit with their lowest point
on y = 0; bottom marks hang from y = 0. Strokes are built from centre lines with
pathops' stroker, so weight and terminal style (round / square / chisel) follow
the face. Shapes taken from the specimen (Tuam's acute, each face's own period
and comma) are passed in by the caller.
"""
import math
import numpy as np
import pathops
import shapes as SH
from glyphs import bounds, translate

CAP = {'round': pathops.LineCap.ROUND_CAP, 'square': pathops.LineCap.BUTT_CAP, 'chisel': pathops.LineCap.BUTT_CAP}
JOIN = {'round': pathops.LineJoin.ROUND_JOIN, 'square': pathops.LineJoin.MITER_JOIN, 'chisel': pathops.LineJoin.MITER_JOIN}


def stroke_polyline(pts, width, style, closed=False):
    p = pathops.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if closed:
        p.close()
    p.stroke(width, CAP[style], JOIN[style], 4.0)
    p.convertConicsToQuads()
    return pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)


def stroke_cubics(start, segs, width, style):
    """segs: list of (c1, c2, end) cubic segments from `start`."""
    p = pathops.Path()
    p.moveTo(*start)
    for c1, c2, e in segs:
        p.cubicTo(*c1, *c2, *e)
    p.stroke(width, CAP[style], JOIN[style], 4.0)
    p.convertConicsToQuads()
    return pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)


def centre(p, top=True):
    """Centre on x = 0 and sit on y = 0 (top marks) or hang from y = 0 (bottom marks)."""
    x0, y0, x1, y1 = bounds(p)
    return translate(p, -(x0 + x1) / 2, -y0 if top else -y1)


def chisel_cut(p, angle_deg=0):
    return p


class MarkSet:
    def __init__(self, style, S, xh, acute=None, period=None, comma=None, weight=0.45, size=1.0, given=None):
        self.style = style; self.S = S; self.xh = xh
        self.w = weight * S                      # mark stroke weight
        self.k = size                            # overall size factor
        self.period = centre(period)
        self.comma = comma
        self._acute = acute
        # marks drawn by the designer (the sheet's accent set); everything else derives from them
        self.given = {k: centre(v) for k, v in (given or {}).items()}
        if 'ring' in self.given:
            # the ring's stroke sets the weight of the marks that still have to be drawn
            b = bounds(self.given['ring']); self.w = 0.30 * (b[2] - b[0])

    # ---------------------------------------------------------------- top marks
    def acute(self):
        if 'acute' in self.given:
            return self.given['acute']
        if self._acute is not None:
            return centre(self._acute)
        L = 0.36 * self.xh * self.k; ang = math.radians(38)
        r0, r1 = {'round': (0.11, 0.36), 'chisel': (0.16, 0.40), 'square': (0.14, 0.38)}[self.style]
        a = SH.wedge((0, 0), (L * math.cos(ang), L * math.sin(ang)), r0 * self.S, r1 * self.S,
                     rounded=(self.style == 'round'))
        return centre(a)

    def grave(self):
        a = self.acute(); b = bounds(a)
        return centre(SH.transform(a, (-1, 0, 0, 1, 0, 0)))

    def hungarumlaut(self):
        a0 = self.acute(); b0 = bounds(a0)
        if b0[2] - b0[0] > 1.8 * (b0[3] - b0[1]):
            # a long flat fada (Tuam) would merge into one bar: two short strokes instead
            a = SH.transform(a0, (0.52, 0, 0, 0.95, 0, 0)); b = bounds(a); w = b[2] - b[0]
            return centre(SH.union(a, translate(a, w + 0.07 * self.xh, 0)))
        a = SH.transform(a0, (0.82, 0, 0, 0.9, 0, 0))
        b = bounds(a); w = b[2] - b[0]
        return centre(SH.union(a, translate(a, 0.78 * w, 0)))

    def circumflex(self, flip=False):
        if 'circumflex' in self.given:
            m = self.given['circumflex']
            return centre(SH.transform(m, (1, 0, 0, -1, 0, 0))) if flip else m
        w = 0.44 * self.xh * self.k; h = 0.25 * self.xh * self.k
        if self.style == 'round':
            # thin-to-thick: tapered wedges meeting at the apex
            l = SH.wedge((-w / 2, 0), (0, h), 0.18 * self.S, 0.30 * self.S)
            r = SH.wedge((0, h), (w / 2, 0), 0.30 * self.S, 0.18 * self.S)
            m = SH.union(l, r)
        else:
            m = stroke_polyline([(-w / 2, 0), (0, h), (w / 2, 0)], self.w, self.style)
            # flat (horizontal) feet for square/chisel styles
            x0, y0, x1, y1 = bounds(m)
            m = SH.op(m, SH.polygon([(x0 - 50, 0), (x1 + 50, 0), (x1 + 50, y1 + 50), (x0 - 50, y1 + 50)]),
                      pathops.PathOp.INTERSECTION)
        if flip:
            m = SH.transform(m, (1, 0, 0, -1, 0, 0))
        return centre(m)

    def caron(self):
        if 'caron' in self.given:
            return self.given['caron']
        return self.circumflex(flip=True)

    def breve(self):
        if 'ring' in self.given:
            # the lower half of the designer's ring, opened out
            r = self.given['ring']; b = bounds(r)
            half = SH.op(r, SH.polygon([(b[0] - 5, b[1] - 5), (b[2] + 5, b[1] - 5), (b[2] + 5, (b[1] + b[3]) / 2),
                                       (b[0] - 5, (b[1] + b[3]) / 2)]), pathops.PathOp.INTERSECTION)
            return centre(SH.transform(half, (1.25, 0, 0, 1, 0, 0)))
        w = 0.42 * self.xh * self.k; h = 0.20 * self.xh * self.k; K = 0.5522847498
        segs = [((-w / 2, h - K * h * 1.2), (-K * w / 2, 0), (0, 0)), ((K * w / 2, 0), (w / 2, h - K * h * 1.2), (w / 2, h))]
        return centre(stroke_cubics((-w / 2, h), segs, self.w, self.style))

    def tilde(self):
        if 'tilde' in self.given:
            return self.given['tilde']
        w = 0.46 * self.xh * self.k; h = 0.13 * self.xh * self.k
        segs = [((-w / 2 + 0.10 * w, h), (-w / 2 + 0.25 * w, h * 1.05), (0, h / 2)),
                ((w / 2 - 0.25 * w, -h * 0.05), (w / 2 - 0.10 * w, 0), (w / 2, h))]
        return centre(stroke_cubics((-w / 2, 0), segs, self.w * 0.95, self.style))

    def macron(self):
        if 'macron' in self.given:
            return self.given['macron']
        w = 0.44 * self.xh * self.k; t = self.w * 0.95
        if self.style == 'round':
            m = SH.capsule(-w / 2 + t / 2, w / 2 - t / 2, 0, t)
        elif self.style == 'chisel':
            m = SH.slanted_bar(-w / 2, w / 2, 0, t, cut=0.22 * t)
        else:
            m = SH.polygon([(-w / 2, -t / 2), (w / 2, -t / 2), (w / 2, t / 2), (-w / 2, t / 2)])
        return centre(m)

    def dot(self):
        return self.given.get('dot', self.period)

    def dieresis(self):
        if 'dieresis' in self.given:
            return self.given['dieresis']
        d = SH.transform(self.period, (0.92, 0, 0, 0.92, 0, 0)); b = bounds(d); w = b[2] - b[0]
        gap = max(0.55 * w, 0.10 * self.xh)
        return centre(SH.union(translate(d, -(w + gap) / 2, 0), translate(d, (w + gap) / 2, 0)))

    def ring(self):
        if 'ring' in self.given:
            return self.given['ring']
        t = self.w * 0.85
        ro = max(0.16 * self.xh, 1.9 * t) * self.k
        if ro > 0.21 * self.xh:
            ro = 0.21 * self.xh; t = ro / 1.9
        m = SH.difference(SH.ellipse(0, ro, ro, ro), SH.ellipse(0, ro, ro - t, ro - t))
        return centre(m)

    def commaturned(self):
        c = SH.transform(self.comma, (0.8, 0, 0, 0.8, 0, 0)); b = bounds(c)
        return centre(SH.rotate(c, 180, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2))

    # ---------------------------------------------------------------- bottom marks
    def commabelow(self):
        c = SH.transform(self.comma, (0.85, 0, 0, 0.85, 0, 0))
        return centre(c, top=False)

    def cedilla(self):
        s = self.xh * self.k; t = self.w * 0.9
        # short neck from the letter, then a hook curling round to the left
        segs = [((0.02 * s, -0.06 * s), (0.17 * s, -0.08 * s), (0.17 * s, -0.17 * s)),
                ((0.17 * s, -0.25 * s), (0.04 * s, -0.27 * s), (-0.11 * s, -0.24 * s))]
        m = stroke_cubics((-0.01 * s, 0.03 * s), segs, t, 'round' if self.style == 'round' else 'square')
        return centre(m, top=False)

    def ogonek(self):
        s = self.xh * self.k; t = self.w * 0.95
        segs = [((-0.04 * s, -0.06 * s), (-0.13 * s, -0.12 * s), (-0.10 * s, -0.20 * s)),
                ((-0.08 * s, -0.27 * s), (0.02 * s, -0.27 * s), (0.10 * s, -0.22 * s))]
        m = stroke_cubics((0.02 * s, 0.02 * s), segs, t, 'round' if self.style == 'round' else 'square')
        return centre(m, top=False)

    def caronvert(self, quoteright):
        q = SH.transform(quoteright, (0.85, 0, 0, 0.85, 0, 0))
        return centre(q)

    def all(self):
        return {'acute': self.acute(), 'grave': self.grave(), 'circumflex': self.circumflex(), 'caron': self.caron(),
                'breve': self.breve(), 'tilde': self.tilde(), 'macron': self.macron(), 'dot': self.dot(),
                'dieresis': self.dieresis(), 'ring': self.ring(), 'hungarumlaut': self.hungarumlaut(),
                'commaturned': self.commaturned(), 'commabelow': self.commabelow(), 'cedilla': self.cedilla(),
                'ogonek': self.ogonek()}
