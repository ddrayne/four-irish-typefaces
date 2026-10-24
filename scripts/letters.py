"""Letters with no Unicode decomposition, built from each face's own traced letters."""
import math
import numpy as np
import pathops
import shapes as SH
from glyphs import bounds, contours, translate
from spacing import profiles


def stem_at(p, y, side='left'):
    """x-extent (x0, x1) of the stroke crossed at height y: the leftmost or rightmost ink run."""
    ys, L, R = profiles(p, y - 6, y + 6, step=4)
    rot = None
    # crossings at the single scanline nearest y
    from spacing import polys
    xs = []
    for poly in polys(p):
        a = poly; b = np.roll(poly, -1, axis=0)
        m = ((a[:, 1] <= y) & (b[:, 1] > y)) | ((b[:, 1] <= y) & (a[:, 1] > y))
        if m.any():
            t = (y - a[m, 1]) / (b[m, 1] - a[m, 1]); xs += list(a[m, 0] + t * (b[m, 0] - a[m, 0]))
    xs = sorted(xs)
    if len(xs) < 2:
        x0, _, x1, _ = bounds(p); return x0, x1
    runs = [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]
    return runs[0] if side == 'left' else runs[-1]


def clip(p, x0=-1e4, y0=-1e4, x1=1e4, y1=1e4):
    return SH.op(p, SH.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), pathops.PathOp.INTERSECTION)


def bar(f, x0, x1, yc, t):
    st = f.style
    if st == 'round':
        return SH.capsule(x0 + t / 2, x1 - t / 2, yc, t)
    if st == 'chisel':
        return SH.slanted_bar(x0, x1, yc, t, cut=0.22 * t)
    return SH.polygon([(x0, yc - t / 2), (x1, yc - t / 2), (x1, yc + t / 2), (x0, yc + t / 2)])


def ligate(f, a, b, overlap):
    """Join glyph b after glyph a, overlapping by `overlap` units (a's right side into b's left)."""
    pa, pb = f.P[a], f.P[b]
    xa = bounds(pa)[2]; xb = bounds(pb)[0]
    return SH.union(pa, translate(pb, xa - xb - overlap, 0))


def make_letters(f):
    """Adds special letters to f.P. Returns {glyphname: description} of what was built."""
    P, S, xh = f.P, f.S, f.xh
    asc, cap = f.asc, f.cap
    made = {}
    t_bar = 0.62 * f.hyphen_thick if f.style != 'round' else 0.7 * f.hyphen_thick
    cases = [('', xh, asc)] if f.cfg['unicase'] else [('', xh, asc), ('UC', cap, cap)]

    # --- æ œ (and Æ Œ): overlap the right stroke of the first letter with the second
    for first, name in (('a', 'ae'), ('o', 'oe')):
        ov = 0.9 * S if first == 'a' else 0.55 * S
        P[name] = ligate(f, first, 'e', ov); made[name] = f'{first}+e'
    if not f.cfg['unicase']:
        P['AE'] = ligate(f, 'A', 'E', 0.9 * S); P['OE'] = ligate(f, 'O', 'E', 0.55 * S)
        made['AE'] = 'A+E'; made['OE'] = 'O+E'

    # --- ø Ø: oblique stroke through the bowl
    for name, base, top in (('oslash', 'o', xh), ('Oslash', 'O', cap)):
        if base not in P:
            continue
        x0, y0, x1, y1 = bounds(P[base]); ext = 0.06 * top
        st = SH.wedge((x0 - 0.02 * top, y0 - ext), (x1 + 0.02 * top, y1 + ext), 0.21 * S, 0.21 * S,
                      rounded=(f.style == 'round'))
        P[name] = SH.union(P[base], st); made[name] = f'{base}+stroke'

    # --- đ ð Đ Ð: bar across the ascender / left stem
    if 'd' in P:
        yb = xh + 0.42 * (asc - xh)
        s0, s1 = stem_at(P['d'], yb, 'right') if f.key == 'tuam' else stem_at(P['d'], yb, 'left')
        w = s1 - s0
        P['dcroat'] = SH.union(P['d'], bar(f, s0 - 0.55 * w - 0.05 * xh, s1 + 0.55 * w + 0.05 * xh, yb, t_bar))
        P['eth'] = SH.union(P['d'], SH.rotate(bar(f, s0 - 0.55 * w - 0.05 * xh, s1 + 0.55 * w + 0.05 * xh, yb, t_bar),
                                              14, (s0 + s1) / 2, yb))
        made['dcroat'] = 'd+bar'; made['eth'] = 'd+slanted bar'
    if not f.cfg['unicase']:
        D = P['D']; yb = 0.48 * cap; s0, s1 = stem_at(D, yb, 'left')
        P['Dcroat'] = SH.union(D, bar(f, s0 - 0.18 * xh, s1 + 0.20 * xh, yb, t_bar)); made['Dcroat'] = 'D+bar'
        P['Eth'] = P['Dcroat']; made['Eth'] = 'D+bar'

    # --- ħ Ħ: bar across the ascender / above the crossbar
    if 'h' in P:
        yb = xh + 0.45 * (asc - xh); s0, s1 = stem_at(P['h'], yb, 'left')
        P['hbar'] = SH.union(P['h'], bar(f, s0 - 0.12 * xh, s1 + 0.32 * xh, yb, t_bar)); made['hbar'] = 'h+bar'
    if not f.cfg['unicase']:
        H = P['H']; x0, y0, x1, y1 = bounds(H)
        P['Hbar'] = SH.union(H, bar(f, x0 - 0.05 * xh, x1 + 0.05 * xh, 0.76 * cap, t_bar)); made['Hbar'] = 'H+bar'

    # --- ł Ł: oblique bar through the stem
    for name, base, top in (('lslash', 'l', xh), ('Lslash', 'L', cap)):
        if base not in P or (name == 'Lslash' and f.cfg['unicase']):
            continue
        yc = 0.50 * top if name == 'lslash' else 0.45 * cap
        s0, s1 = stem_at(P[base], yc, 'left'); cx = (s0 + s1) / 2; d = 0.22 * xh + (s1 - s0) / 2
        sl = SH.rotate(bar(f, cx - d, cx + d, yc, t_bar), 32, cx, yc)
        P[name] = SH.union(P[base], sl); made[name] = f'{base}+slash'

    # --- ŧ Ŧ: bar across the stem
    if 't' in P:
        yc = 0.42 * xh; s0, s1 = stem_at(P['t'], yc, 'left')
        P['tbar'] = SH.union(P['t'], bar(f, s0 - 0.14 * xh, s1 + 0.14 * xh, yc, t_bar)); made['tbar'] = 't+bar'
    if not f.cfg['unicase']:
        T = P['T']; yc = 0.45 * cap; s0, s1 = stem_at(T, yc, 'left') if True else (0, 0)
        # insular T: the vertical part is the left bowl; bar across it
        P['Tbar'] = SH.union(T, bar(f, s0 - 0.12 * xh, s1 + 0.16 * xh, yc, t_bar)); made['Tbar'] = 'T+bar'

    # --- ŋ Ŋ: n with j's descender hook on the right stem
    if 'n' in P and 'j' in P:
        j = P['dotlessj'] if 'dotlessj' in P else P['j']
        hook = clip(j, y1=0.08 * xh)
        js0, js1 = stem_at(j, 0.3 * xh, 'right')
        for name, base in (('eng', 'n'), ('Eng', 'N')):
            if base not in P or (name == 'Eng' and f.cfg['unicase']):
                continue
            ns0, ns1 = stem_at(P[base], 0.3 * xh, 'right')
            body = clip(P[base], y0=0.02 * xh) if True else P[base]
            body = SH.union(body, clip(P[base], x1=ns0 - 1))
            P[name] = SH.union(body, translate(hook, (ns0 + ns1) / 2 - (js0 + js1) / 2, 0)); made[name] = f'{base}+hook'

    # --- þ Þ: p with an ascender; Þ: stem with the P bowl moved down
    if 'p' in P:
        s0, s1 = stem_at(P['p'], 0.5 * xh, 'left')
        stem = SH.polygon([(s0, 0.5 * xh), (s1, 0.5 * xh), (s1, asc), (s0, asc)])
        if f.style == 'round' and 'l' in P:
            # reuse the l's ascender terminal so the top matches the face
            l0, l1 = stem_at(P['l'], 0.5 * xh, 'left')
            top = clip(P['l'], y0=xh + 0.25 * (asc - xh))
            stem = SH.union(SH.polygon([(s0, 0.5 * xh), (s1, 0.5 * xh), (s1, xh + 0.3 * (asc - xh)), (s0, xh + 0.3 * (asc - xh))]),
                            translate(top, s0 - l0 + ((s1 - s0) - (l1 - l0)) / 2, 0))
        P['thorn'] = SH.union(P['p'], stem); made['thorn'] = 'p+ascender'
    if not f.cfg['unicase']:
        Pp = P['P']; s0, s1 = stem_at(Pp, 0.3 * cap, 'left')
        bowl = clip(Pp, x0=s1 - 0.25 * (s1 - s0), y0=0.35 * cap)
        stem = clip(Pp, x1=s1 + 1)
        P['Thorn'] = SH.union(stem, translate(bowl, 0, -0.17 * cap)); made['Thorn'] = 'P stem + lowered bowl'

    # --- ß: a long-s/s ligature where the face has an insular s, otherwise a tight 'ss'

    # --- ĳ Ĳ, ŀ Ŀ
    P['ij'] = ligate(f, 'i', 'j', -0.06 * xh); made['ij'] = 'i+j'
    if not f.cfg['unicase']:
        P['IJ'] = ligate(f, 'I', 'J', -0.06 * xh); made['IJ'] = 'I+J'
    dot = f.period
    db = bounds(dot); dw = db[2] - db[0]
    l0, l1 = stem_at(P['l'], 0.5 * xh, 'left')
    P['ldot'] = SH.union(P['l'], translate(dot, l1 + 0.10 * xh - db[0], 0.48 * xh - (db[1] + db[3]) / 2)); made['ldot'] = 'l+dot'
    if not f.cfg['unicase']:
        L0, L1 = stem_at(P['L'], 0.5 * cap, 'left')
        P['Ldot'] = SH.union(P['L'], translate(dot, L1 + 0.16 * xh - db[0], 0.45 * cap - (db[1] + db[3]) / 2)); made['Ldot'] = 'L+dot'

    # --- ĸ: k cut to x-height
    if 'k' in P:
        P['kgreenlandic'] = clip(P['k'], y1=xh + 2); made['kgreenlandic'] = 'k trimmed'

    # --- ŉ: apostrophe + n
    q = f.P['quoteright']; qb = bounds(q)
    P['napostrophe'] = SH.union(translate(q, 0, xh + 0.15 * (asc - xh) - qb[3] + (qb[3] - qb[1]) * 0.15),
                                translate(P['n'], qb[2] - qb[0] + 0.08 * xh, 0)); made['napostrophe'] = "'+n"

    # --- ſ: Céilí's insular s; elsewhere the f without its crossbar
    if f.key == 'ceili':
        P['longs'] = P['s.alt1']; made['longs'] = 'insular s'
    else:
        src = P['f.alt1'] if 'f.alt1' in P else P['f']
        s0, s1 = stem_at(src, 0.25 * xh, 'left')
        sw = s1 - s0
        # crossbar band: the run of rows around the crossbar where the ink is wider than the stem,
        # followed out until it is back to the stem's own width (so no burr of the bar is left)
        ys, L, R = profiles(src, 0.30 * xh, 1.20 * xh, step=2)
        w = np.where(np.isnan(L), 0, R - L)
        wide = []
        if np.nanmax(w) > 1.7 * sw:
            i = int(np.nanargmax(w)); j0 = j1 = i
            while j0 > 0 and w[j0 - 1] > 1.12 * sw:
                j0 -= 1
            while j1 < len(w) - 1 and w[j1 + 1] > 1.12 * sw:
                j1 += 1
            wide = [ys[j0], ys[j1]]
        if wide:
            lo, hi = min(wide) - 0.01 * xh, max(wide) + 0.01 * xh
            # bridge the band with the stem's own edges just below and above it (a fixed column
            # would notch a stem that leans or tapers)
            (l0, r0), (l1, r1) = stem_at(src, lo - 4, 'left'), stem_at(src, hi + 4, 'left')
            span = SH.polygon([(l0, lo - 6), (r0, lo - 6), (r1, hi + 6), (l1, hi + 6)])
            keep = SH.union(clip(src, y0=hi), clip(src, y1=lo), span)
        else:
            keep = src
        P['longs'] = keep; made['longs'] = 'f without crossbar'
    # --- ß: the historical long-s + s ligature, from the face's own letters
    P['germandbls'] = ligate(f, 'longs', 's', (0.25 if f.key == 'ceili' else 0.18) * S)
    made['germandbls'] = 'long s + s ligature'
    return made
