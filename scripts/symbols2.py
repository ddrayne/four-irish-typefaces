"""Characters beyond Latin-1 that complete Google Fonts' Latin Plus set: superior and inferior
figures (and the numerators and denominators the frac feature uses), more vulgar fractions, the
world's currency signs, the common maths signs, arrows and geometric shapes, and Kilfane's
capital sharp s. None of them is on the 1978 sheet: each is drawn from the face's own letters,
figures, stem weight and stroke ends.
"""
import math
import shapes as SH
from glyphs import bounds, translate
from marks import stroke_polyline, stroke_cubics
from symbols import bar, vbar, ring, scaled, inside_ring, chevron

DIGITS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
SUPS = ['uni2070', 'onesuperior', 'twosuperior', 'threesuperior'] + [f'uni{0x2074 + i:04X}' for i in range(6)]
SINF = [f'uni{0x2080 + i:04X}' for i in range(10)]
CODEPOINTS = {
    0x1E9E: 'uni1E9E', 0x2070: 'uni2070', **{0x2074 + i: f'uni{0x2074 + i:04X}' for i in range(6)},
    **{0x2080 + i: f'uni{0x2080 + i:04X}' for i in range(10)},
    0x2153: 'onethird', 0x2154: 'twothirds', 0x215B: 'oneeighth', 0x215C: 'threeeighths', 0x215D: 'fiveeighths',
    0x215E: 'seveneighths',
    0x20A1: 'colonmonetary', 0x20A6: 'uni20A6', 0x20A8: 'uni20A8', 0x20A9: 'uni20A9', 0x20AA: 'uni20AA',
    0x20AB: 'dong', 0x20AD: 'uni20AD', 0x20AE: 'uni20AE', 0x20B1: 'uni20B1', 0x20B2: 'uni20B2',
    0x20B4: 'uni20B4', 0x20B5: 'uni20B5', 0x20B8: 'uni20B8', 0x20B9: 'uni20B9', 0x20BA: 'uni20BA',
    0x20BC: 'uni20BC', 0x20BD: 'uni20BD', 0x20BE: 'uni20BE', 0x20BF: 'uni20BF', 0x0E3F: 'uni0E3F',
    0x03C0: 'pi', 0x2202: 'partialdiff', 0x2205: 'emptyset', 0x2206: 'increment', 0x220F: 'product',
    0x2211: 'summation', 0x221A: 'radical', 0x221E: 'infinity', 0x222B: 'integral', 0x2113: 'uni2113',
    0x2116: 'uni2116', 0x2126: 'uni2126', 0x212E: 'estimated', 0x25CA: 'lozenge', 0x2016: 'uni2016',
    0x27E8: 'uni27E8', 0x27E9: 'uni27E9', 0x24B9: 'uni24B9',
    0x2190: 'arrowleft', 0x2191: 'arrowup', 0x2192: 'arrowright', 0x2193: 'arrowdown', 0x2194: 'arrowboth',
    0x2195: 'arrowupdn', 0x2196: 'uni2196', 0x2197: 'uni2197', 0x2198: 'uni2198', 0x2199: 'uni2199',
    0x25A0: 'filledbox', 0x25A1: 'H22073', 0x25AA: 'H18543', 0x25AB: 'H18551', 0x25B2: 'triagup',
    0x25B3: 'uni25B3', 0x25B4: 'uni25B4', 0x25B5: 'uni25B5', 0x25B6: 'uni25B6', 0x25B7: 'uni25B7',
    0x25B8: 'uni25B8', 0x25B9: 'uni25B9', 0x25BC: 'triagdn', 0x25BD: 'uni25BD', 0x25BE: 'uni25BE',
    0x25BF: 'uni25BF', 0x25C0: 'uni25C0', 0x25C1: 'uni25C1', 0x25C2: 'uni25C2', 0x25C3: 'uni25C3',
    0x25C6: 'uni25C6', 0x25C7: 'uni25C7', 0x25CB: 'circle', 0x25CF: 'H18533', 0x25E6: 'openbullet',
}
SMALL = set(SUPS + SINF + [f'{d}.numr' for d in DIGITS] + [f'{d}.dnom' for d in DIGITS])
# glyphs spaced by fixed sidebearings (multiples of the face's spacing unit) rather than by profile
FIXED = {**{n: 0.45 for n in SMALL}, **{n: 0.6 for n in (
    'arrowleft', 'arrowup', 'arrowright', 'arrowdown', 'arrowboth', 'arrowupdn', 'uni2196', 'uni2197', 'uni2198', 'uni2199',
    'filledbox', 'H22073', 'H18543', 'H18551', 'triagup', 'uni25B3', 'uni25B4', 'uni25B5', 'uni25B6', 'uni25B7',
    'uni25B8', 'uni25B9', 'triagdn', 'uni25BD', 'uni25BE', 'uni25BF', 'uni25C0', 'uni25C1', 'uni25C2', 'uni25C3',
    'uni25C6', 'uni25C7', 'circle', 'H18533', 'openbullet', 'lozenge')},
         **{n: 0.9 for n in ('emptyset', 'increment', 'product', 'summation', 'radical', 'infinity', 'integral', 'uni2016',
                             'uni27E8', 'uni27E9')}}


def make_symbols2(f):
    P, S, xh, st = f.P, f.S, f.xh, f.style
    top = f.fig if f.cfg['lining'] else xh * 1.05
    t = f.hyphen_thick; yc = f.hyphen_yc
    Ss = S if not f.bold else f.S_regular + 0.5 * (S - f.S_regular)
    uc = f.cfg['unicase']
    made = {}

    def put(name, p, how):
        P[name] = f.norm_x(p); made[name] = how

    def at(p, x=0, y=0):
        b = bounds(p); return translate(p, x - b[0], y - b[1])

    def letter(name, h=None):
        """The face's letter (its unicase form where it has one case), on the baseline, scaled to
        the height of the figures with its stems kept at the face's weight."""
        src = name if not uc else {'I': 'dotlessi'}.get(name, name.lower())
        g = at(P[src]); b = bounds(g); k = (h or top) / (b[3] - b[1])
        return at(scaled(g, k, S, 1.0)) if abs(k - 1) > 0.03 else g

    def wh(p):
        b = bounds(p); return b[2] - b[0], b[3] - b[1]

    sw = 0.8 * t                          # bar weight for currency strokes
    # ---------------------------------------------------------------- small figures
    h8 = max(wh(P[d])[1] for d in DIGITS)
    hs = 0.58 * h8                        # every small figure the same height (lining small figures)
    small = {}
    for d in DIGITS:
        g = at(P[d]); k = hs / wh(g)[1]
        small[d] = at(scaled(g, k, S, 0.7, Ss))
    for d, sup, inf in zip(DIGITS, SUPS, SINF):
        put(sup, at(small[d], 0, top - hs), 'small figure, superior')
        P[f'{d}.numr'] = P[sup]; made[f'{d}.numr'] = 'small figure, numerator'
        put(f'{d}.dnom', small[d], 'small figure, denominator')
        put(inf, at(small[d], 0, -0.30 * hs), 'small figure, inferior')

    fb = bounds(P['fraction']); fw = fb[2] - fb[0]

    def frac(num, den):
        n = P[f'{num}.numr']; d = P[f'{den}.dnom']
        nw = wh(n)[0]; gap = 0.10 * xh
        fx = nw - gap
        return SH.union(n, translate(P['fraction'], fx - fb[0], 0), translate(d, fx + fw - gap, 0))
    for name, (a, b) in {'onequarter': ('one', 'four'), 'onehalf': ('one', 'two'), 'threequarters': ('three', 'four'),
                         'onethird': ('one', 'three'), 'twothirds': ('two', 'three'), 'oneeighth': ('one', 'eight'),
                         'threeeighths': ('three', 'eight'), 'fiveeighths': ('five', 'eight'), 'seveneighths': ('seven', 'eight')}.items():
        put(name, frac(a, b), 'numerator, fraction slash, denominator')

    # ---------------------------------------------------------------- capital sharp s
    if not uc:
        B = at(P['B']); bw, bh = wh(B)
        from letters import stem_at
        s0, s1 = stem_at(B, 0.5 * bh, 'left')
        waist = 0.52 * bh
        from letters import clip
        lower = clip(B, y1=waist)
        stem = clip(B, x1=s1 + 2)
        arm = 0.6 * bw; th = 0.62 * S
        top_bar = SH.polygon([(s0, bh - th), (arm, bh - th), (arm + 0.2 * th, bh), (s0, bh)])
        diag = stroke_polyline([(arm, bh - th / 2), (s1 + 0.12 * bw, waist + 0.02 * bh)], 0.7 * S, st)
        put('uni1E9E', SH.union(stem, lower, top_bar, diag), 'capital sharp s: B’s stem and lower bowl, an arm and a diagonal')

    # ---------------------------------------------------------------- currency signs
    def through(p, ys, ext=0.10, h=None, w=None):
        b = bounds(p); W = b[2] - b[0]; H = b[3] - b[1]
        return SH.union(p, *[bar(st, b[0] - ext * W, b[2] + ext * W, b[1] + y * H, sw) for y in ys])

    def vthrough(p, xs, lo=-0.12, hi=1.12):
        b = bounds(p); W = b[2] - b[0]; H = b[3] - b[1]
        return SH.union(p, *[vbar(st, b[0] + x * W, b[1] + lo * H, b[1] + hi * H, sw) for x in xs])

    C = letter('C'); cb = bounds(C); cw, ch = wh(C)
    slash = lambda x: stroke_polyline([(cb[0] + (x - 0.10) * cw, cb[1] - 0.12 * ch), (cb[0] + (x + 0.10) * cw, cb[3] + 0.12 * ch)], sw, st)
    put('colonmonetary', SH.union(C, slash(0.42), slash(0.62)), 'C + two strokes')
    put('uni20B5', vthrough(C, [0.52]), 'C + stroke')
    put('uni20A6', through(letter('N'), [0.38, 0.62]), 'N + two bars')
    put('uni20A9', through(letter('W'), [0.36, 0.60]), 'W + two bars')
    put('uni20AD', through(letter('K'), [0.5], ext=0.06), 'K + bar')
    G = letter('G'); put('uni20B2', vthrough(G, [0.5]), 'G + stroke')
    Pp = letter('P'); pb = bounds(Pp); pw, ph = wh(Pp)
    put('uni20B1', SH.union(Pp, *[bar(st, pb[0] - 0.14 * pw, pb[2] + 0.06 * pw, pb[1] + y * ph, sw) for y in (0.60, 0.78)]), 'P + two bars')
    put('uni20BD', SH.union(Pp, bar(st, pb[0] - 0.16 * pw, pb[0] + 0.62 * pw, pb[1] + 0.30 * ph, sw)), 'P + bar')
    R = letter('R'); s_ = at(scaled(P['s'], 0.74, S, 0.85, Ss))
    put('uni20A8', SH.union(R, at(s_, wh(R)[0] + 0.03 * xh, 0)), 'R + s')
    T = letter('T'); tb = bounds(T); tw, th_ = wh(T)
    slant = lambda y: stroke_polyline([(tb[0] + 0.22 * tw, tb[1] + (y - 0.06) * th_), (tb[0] + 0.78 * tw, tb[1] + (y + 0.06) * th_)], sw, st)
    put('uni20AE', SH.union(T, slant(0.34), slant(0.54)), 'T + two strokes')
    T2 = letter('T', 0.82 * top)
    put('uni20B8', SH.union(T2, bar(st, bounds(T2)[0], bounds(T2)[2], top - sw / 2, sw)), 'T + bar above')
    Ssh = SH.transform(letter('S'), (-1, 0, 0, 1, 0, 0))
    put('uni20B4', through(Ssh, [0.38, 0.62], ext=0.12), 'reversed S + two bars')
    Bb = letter('B'); bb = bounds(Bb); bw2, bh2 = wh(Bb)
    put('uni0E3F', vthrough(Bb, [0.42]), 'B + stroke')
    stubs = [vbar(st, bb[0] + x * bw2, y0, y1, sw) for x in (0.30, 0.56) for y0, y1 in ((bb[3] - 0.02 * bh2, bb[3] + 0.14 * bh2), (bb[1] - 0.14 * bh2, bb[1] + 0.02 * bh2))]
    put('uni20BF', SH.union(Bb, *stubs), 'B + four stubs')
    dc = P['dcroat']; db = bounds(dc)
    put('dong', SH.union(dc, bar(st, db[0], db[2] - 0.05 * (db[2] - db[0]), -0.20 * xh, sw)), 'đ + underline')
    # drawn signs
    w = 0.86 * top; m = 0.36 * S
    sh_l = stroke_polyline([(m, 0), (m, top - m), (0.62 * w, top - m), (0.62 * w, 0.40 * top)], 0.72 * S, st)
    sh_r = stroke_polyline([(0.38 * w, 0.60 * top), (0.38 * w, m), (w - m, m), (w - m, top)], 0.72 * S, st)
    put('uni20AA', SH.union(sh_l, sh_r), 'two interlocked strokes')
    w = 0.72 * top; ss = 0.62 * S
    bowl = stroke_cubics((0.18 * w, top - sw / 2), [((0.86 * w, top - sw / 2), (0.86 * w, 0.46 * top), (0.18 * w, 0.46 * top))], ss, st)
    leg = stroke_polyline([(0.24 * w, 0.46 * top), (0.86 * w, 0.0)], ss, st)
    put('uni20B9', SH.union(bar(st, 0, w, top - sw / 2, sw), bar(st, 0, w, 0.70 * top, sw), bowl, leg), 'two bars, bowl and leg')
    w = 0.70 * top; x0 = 0.34 * w
    lira = stroke_cubics((x0, top), [((x0, 0.25 * top), (x0, ss / 2), (0.55 * w, ss / 2)), ((0.85 * w, ss / 2), (w, 0.2 * top), (w - ss / 2, 0.46 * top))], ss, st)
    cross = lambda y: stroke_polyline([(0.0, y - 0.08 * top), (0.66 * w, y + 0.10 * top)], sw, st)
    put('uni20BA', SH.union(lira, cross(0.40 * top), cross(0.60 * top)), 'L with a rising foot and two strokes')
    w = 0.86 * top
    arch = stroke_cubics((ss / 2, 0), [((ss / 2, 0.86 * top), (w - ss / 2, 0.86 * top), (w - ss / 2, 0))], ss, st)
    put('uni20BC', SH.union(arch, vbar(st, w / 2, 0.30 * top, top, sw)), 'arch + stroke')
    w = 0.86 * top
    arch = stroke_cubics((0.12 * w, sw), [((0.0, 0.72 * top), (w, 0.72 * top), (0.92 * w, 0.24 * top))], ss, st)
    put('uni20BE', SH.union(bar(st, 0, w, sw / 2, sw), arch, vbar(st, 0.40 * w, 0.42 * top, top, sw), vbar(st, 0.60 * w, 0.42 * top, top, sw)),
        'arch on a line, two strokes')

    # ---------------------------------------------------------------- maths
    pw = 0.62 * xh; ms = 0.62 * S
    pi = SH.union(bar(st, 0, pw, xh - 0.4 * t, 0.8 * t), vbar(st, 0.24 * pw, 0, xh - 0.4 * t, ms),
                  stroke_cubics((0.74 * pw, xh - 0.4 * t), [((0.74 * pw, 0.2 * xh), (0.74 * pw, ms / 2), (0.95 * pw, ms / 2))], ms, st))
    put('pi', pi, 'two stems under a bar')
    put('partialdiff', P['d'], 'the face’s round d')
    r = 0.40 * top; cx, cy = r + 0.1 * r, top / 2
    put('emptyset', SH.union(ring(cx, cy, r, 0.9 * t), stroke_polyline([(cx - 1.2 * r, cy - 1.2 * r), (cx + 1.2 * r, cy + 1.2 * r)], 0.9 * t, st)),
        'ring + slash')
    w = 0.86 * top; es = 0.55 * S
    put('increment', stroke_polyline([(es / 2, es / 2), (w - es / 2, es / 2), (w / 2, top - es / 2)], es, st, closed=True), 'triangle')
    w = 0.80 * top; ps = 0.7 * S
    put('product', SH.union(bar(st, 0, w, top - 0.45 * t, 0.9 * t), vbar(st, 0.16 * w, -0.12 * top, top - 0.45 * t, ps),
                            vbar(st, 0.84 * w, -0.12 * top, top - 0.45 * t, ps)), 'two stems under a bar')
    w = 0.70 * top
    put('summation', stroke_polyline([(w, top + 0.02 * top), (0.04 * w, top + 0.02 * top), (0.52 * w, 0.44 * top),
                                      (0.04 * w, -0.12 * top), (w, -0.12 * top)], 0.55 * S, st), 'sigma')
    w = 0.80 * top
    put('radical', stroke_polyline([(0.0, 0.46 * top), (0.12 * w, 0.52 * top), (0.36 * w, 0.0), (0.72 * w, 1.06 * top), (w, 1.06 * top)],
                                   0.5 * S, st), 'tick, stroke and bar')
    pts = []
    a = 0.62 * xh
    for i in range(96):
        tt = 2 * math.pi * i / 96; d = 1 + math.sin(tt) ** 2
        pts.append((a * math.cos(tt) / d, yc + 1.35 * a * math.sin(tt) * math.cos(tt) / d))
    put('infinity', stroke_polyline(pts, 0.6 * t + 0.2 * S, 'round', closed=True), 'lemniscate')
    w = 0.40 * top; is_ = 0.5 * S
    put('integral', stroke_cubics((0.0, -0.10 * top), [((0.22 * w, -0.26 * top), (0.5 * w, -0.16 * top), (0.5 * w, 0.40 * top)),
                                                      ((0.5 * w, 1.10 * top), (0.78 * w, 1.20 * top), (w, 1.04 * top))], is_, st), 'long s-curve')
    h = f.asc; w = 0.40 * h; ls = 0.45 * S
    put('uni2113', stroke_cubics((0.10 * w, 0.24 * h), [((0.90 * w, 0.60 * h), (0.90 * w, h), (0.55 * w, h)),
                                                       ((0.25 * w, h), (0.20 * w, 0.40 * h), (0.40 * w, 0.06 * h)),
                                                       ((0.55 * w, -0.10 * h), (0.85 * w, 0.05 * h), (w, 0.16 * h))], ls, st), 'script l')
    N = letter('N'); om = at(P['ordmasculine'], wh(N)[0] + 0.06 * xh, top - wh(P['ordmasculine'])[1])
    put('uni2116', SH.union(N, om), 'N + º')
    r = 0.46 * top; cx, cy = r, 0.54 * top; os_ = 0.75 * S
    arc = SH.difference(ring(cx, cy, r, os_), SH.polygon([(cx - 0.36 * r, -top), (cx + 0.36 * r, -top), (cx + 0.36 * r, cy - 0.5 * r), (cx - 0.36 * r, cy - 0.5 * r)]))
    feet = SH.union(bar(st, cx - 0.62 * r, cx - 0.18 * r, 0.4 * t, 0.8 * t), bar(st, cx + 0.18 * r, cx + 0.62 * r, 0.4 * t, 0.8 * t))
    legs = SH.union(*[vbar(st, cx + s * 0.31 * r, 0, cy - 0.55 * r, 0.6 * os_) for s in (-1, 1)])
    put('uni2126', SH.union(arc, feet, legs), 'open ring on two feet')
    r = 0.40 * xh; cx, cy = r, 0.48 * xh; es = 0.45 * S
    e_arc = SH.difference(ring(cx, cy, r, es), SH.polygon([(cx + 0.1 * r, cy - 2 * r), (cx + 2 * r, cy - 2 * r), (cx + 2 * r, cy - 0.12 * r)]))
    put('estimated', SH.union(e_arc, bar('square', cx - r + es / 2, cx + r - es / 2, cy, es)), 'open ring + bar')
    w = 0.58 * top; ls = 0.45 * S
    put('lozenge', stroke_polyline([(w / 2, 0), (w, top / 2), (w / 2, top), (0, top / 2)], ls, st, closed=True), 'lozenge')
    bb_ = P['bar']; bw_ = wh(bb_)[0]
    put('uni2016', SH.union(bb_, translate(bb_, bw_ + 0.12 * xh, 0)), 'two bars')
    pl = bounds(P['parenleft']); ph_ = pl[3] - pl[1]
    ang = translate(chevron(st, 0.26 * xh, ph_, 0.5 * S, True), 0, pl[1])
    put('uni27E8', ang, 'tall chevron'); put('uni27E9', SH.transform(ang, (-1, 0, 0, 1, 0, 0)), 'tall chevron')
    R0 = 0.5 * top; rt = 0.42 * t + 0.1 * S
    D = scaled(P['D' if not uc else 'd'], 0.50 if not uc else 0.62, S, 0.62, Ss); dbb = bounds(D)
    D = inside_ring(translate(D, R0 - (dbb[0] + dbb[2]) / 2, R0 - (dbb[1] + dbb[3]) / 2), R0, R0, R0 - rt, 0.45 * rt)
    put('uni24B9', SH.union(ring(R0, R0, R0, rt), D), 'ring + D')

    # ---------------------------------------------------------------- arrows
    aw = 1.0 * xh + 0.3 * S; hl = 0.30 * xh + 0.15 * S; ak = 0.9 * t

    def arrow(both=False):
        p = [bar(st, 0, aw, yc, ak), stroke_polyline([(aw - hl, yc + hl), (aw - ak * 0.3, yc), (aw - hl, yc - hl)], ak, st)]
        if both:
            p.append(stroke_polyline([(hl, yc + hl), (ak * 0.3, yc), (hl, yc - hl)], ak, st))
        return SH.union(*p)
    right = arrow(); both = arrow(True)
    rot = lambda p, deg: SH.rotate(p, deg, aw / 2, yc)
    put('arrowright', right, 'arrow'); put('arrowleft', rot(right, 180), 'arrow'); put('arrowboth', both, 'arrow')
    put('arrowup', rot(right, 90), 'arrow'); put('arrowdown', rot(right, -90), 'arrow'); put('arrowupdn', rot(both, 90), 'arrow')
    dg = SH.transform(right, (0.88, 0, 0, 0.88, 0, 0)); dgb = bounds(dg)
    dcx, dcy = (dgb[0] + dgb[2]) / 2, (dgb[1] + dgb[3]) / 2
    for name, deg in (('uni2197', 45), ('uni2196', 135), ('uni2199', 225), ('uni2198', 315)):
        q = SH.rotate(dg, deg, dcx, dcy); qb = bounds(q)
        put(name, translate(q, 0, yc - (qb[1] + qb[3]) / 2), 'arrow')

    # ---------------------------------------------------------------- geometric shapes
    big = 0.72 * top; little = 0.40 * top; gk = 0.55 * t + 0.08 * S

    def square(s, y0, filled):
        box = SH.polygon([(0, y0), (s, y0), (s, y0 + s), (0, y0 + s)])
        return box if filled else SH.difference(box, SH.polygon([(gk, y0 + gk), (s - gk, y0 + gk), (s - gk, y0 + s - gk), (gk, y0 + s - gk)]))

    def poly(pts, filled):
        if filled:
            return SH.polygon(pts)
        return stroke_polyline(pts, gk, 'square', closed=True)

    def tri(s, y0, direction, filled):
        hgt = 0.87 * s
        pts = [(0, y0), (s, y0), (s / 2, y0 + hgt)]
        p = poly(pts, filled)
        c = (s / 2, y0 + hgt / 2)
        return SH.rotate(p, {'up': 0, 'down': 180, 'right': -90, 'left': 90}[direction], *c)

    ylo = lambda s: yc - s / 2
    put('filledbox', square(big, 0, True), 'square'); put('H22073', square(big, 0, False), 'square')
    put('H18543', square(little, ylo(little), True), 'square'); put('H18551', square(little, ylo(little), False), 'square')
    for (filled, small_), names in {(True, False): ('triagup', 'triagdn', 'uni25B6', 'uni25C0'), (False, False): ('uni25B3', 'uni25BD', 'uni25B7', 'uni25C1'),
                                     (True, True): ('uni25B4', 'uni25BE', 'uni25B8', 'uni25C2'), (False, True): ('uni25B5', 'uni25BF', 'uni25B9', 'uni25C3')}.items():
        s = little * 1.1 if small_ else big
        for name, dr in zip(names, ('up', 'down', 'right', 'left')):
            put(name, tri(s, 0 if not small_ else ylo(0.87 * s), dr, filled), 'triangle')
    dm = [(big * 0.5, 0), (big * 0.92, big * 0.6), (big * 0.5, big * 1.2), (big * 0.08, big * 0.6)]
    put('uni25C6', poly(dm, True), 'diamond'); put('uni25C7', poly(dm, False), 'diamond')
    put('H18533', SH.ellipse(big / 2, big / 2, big / 2, big / 2), 'circle')
    put('circle', ring(big / 2, big / 2, big / 2, gk), 'circle')
    put('openbullet', ring(0.17 * xh, yc, 0.17 * xh, 0.35 * t + 0.05 * S), 'small circle')
    return made
