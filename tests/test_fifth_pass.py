"""The fifth finishing pass, shared by the four faces (research/*/judged-edits.json, "fifth_pass"), checked on the
released fonts (fonts/, or FONTDIR): ≈ at the ='s spacing and weight, the rings of © ® @ ° ¤ at the o's weight with
their letters and counters clear, and combining marks that clear their letters, stack and keep Irish input as it was."""
import functools, math, unicodedata
import numpy as np
import pathops
import pytest
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from conftest import static

FACES = {'KilfaneDigital': ('Regular', 'Italic', 'Bold', 'Bold Italic'), 'CarrickDigital': ('Regular', 'Italic'),
         'TuamUncialDigital': ('Regular', 'Italic'), 'CeiliDigital': ('Regular', 'Italic', 'Bold', 'Bold Italic')}
ALL = [(ps, st) for ps, sts in FACES.items() for st in sts]
SLANT = math.tan(math.radians(8.0))
TOP = '̀́̂̃̄̆̇̈̊̋̌'
BOTTOM = '̣̦'                 # marks that hang clear of the letter
ATTACHED = '̧̨'               # marks that join it (cedilla, ogonek)
LETTERS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
_fonts = {}


def font(ps, st):
    if (ps, st) not in _fonts:
        path = static(ps, st); f = TTFont(path)
        _fonts[ps, st] = dict(tt=f, gs=f.getGlyphSet(), cm=f.getBestCmap(), order=f.getGlyphOrder(), path=path,
                              hb=hb.Font(hb.Face(hb.Blob.from_file_path(path))), xh=f['OS/2'].sxHeight)
    return _fonts[ps, st]


def outline(ps, st, name, upright=True, dx=0, dy=0):
    """A glyph's outline; a sloped style's sheared back upright (about the half x-height, as it was sloped)."""
    F = font(ps, st)
    name = F['cm'][ord(name)] if len(name) == 1 else name
    p = pathops.Path(); pen = p.getPen()
    if upright and 'Italic' in st:
        yc = F['xh'] / 2
        pen = TransformPen(pen, (1, 0, -SLANT, 1, yc * SLANT + dx, dy))
    elif dx or dy:
        pen = TransformPen(pen, (1, 0, 0, 1, dx, dy))
    F['gs'][name].draw(pen)
    return pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)


def bounds(p):
    bp = BoundsPen(None); p.draw(bp); return bp.bounds


def area(p):
    from fontTools.pens.areaPen import AreaPen
    ap = AreaPen(); p.draw(ap); return ap.value


def contours(p):
    import glyphs
    return glyphs.contours(p)


def pieces(p):
    import bolden
    return sorted(bolden.components(p), key=lambda q: bounds(q)[1])


def white(a, b):
    """The least white between two outlines (negative: the square root of their overlap's area)."""
    from scipy.spatial import cKDTree
    ov = abs(area(pathops.op(a, b, pathops.PathOp.INTERSECTION, fix_winding=True)))
    if ov > 0.5:
        return -math.sqrt(ov)
    import kilfane_studio as KS
    return float(cKDTree(KS._pts(b)).query(KS._pts(a))[0].min())


def stroke(p):
    import symbols
    return symbols.stroke_weight(p)


def row(p, y):
    from letters import stem_at
    return stem_at(p, y, 'left'), stem_at(p, y, 'right')


def o_side(ps, st):
    """The o's heavier side, the ink run across the middle of its height."""
    o = outline(ps, st, 'o'); b = bounds(o)
    return max(x1 - x0 for x0, x1 in row(o, (b[1] + b[3]) / 2))


def axis(ps, st):
    b = bounds(outline(ps, st, 'hyphen')); return (b[1] + b[3]) / 2


# ---------------------------------------------------------------- ≈
@pytest.mark.parametrize('ps,st', ALL)
def test_approx_stands_as_the_equals_sign(ps, st):
    """≈ was much taller than =: Carrick's waves 204 apart at the middle against ='s 101 (it ran -29..541), Céilí's 175
    against 105, Tuam's 179 against 143, and Kilfane's waves 109 thick against the = bars' 60. Each wave is now drawn at
    the rules' weight and centred where a = bar is, on the math axis, the white between the waves 0.7 of the ='s."""
    eq, ap = pieces(outline(ps, st, 'equal')), pieces(outline(ps, st, 'approxequal'))
    assert len(eq) == len(ap) == 2
    mid = lambda q: (bounds(q)[1] + bounds(q)[3]) / 2
    for e, a in zip(eq, ap):
        assert abs(mid(e) - mid(a)) <= 3, (st, mid(e), mid(a))                    # the ='s spacing
        assert abs(stroke(a) / stroke(e) - 1) <= 0.08, (st, stroke(a), stroke(e))   # and its rules' weight
    assert abs((mid(ap[0]) + mid(ap[1])) / 2 - axis(ps, st)) <= 3                   # on the math axis
    w, we = white(*ap), bounds(eq[1])[1] - bounds(eq[0])[3]
    assert 0.6 * we <= w <= 0.85 * we, (st, w, we)
    # no taller than the = and the white between its bars
    hb_, he = bounds(outline(ps, st, 'approxequal')), bounds(outline(ps, st, 'equal'))
    assert (hb_[3] - hb_[1]) - (he[3] - he[1]) <= we, (hb_, he)


# ---------------------------------------------------------------- the rings
def ring_parts(ps, st, name):
    """(the ring, its sides through its counter's middle, its counter's least span, the other pieces)."""
    p = outline(ps, st, name)
    ps_ = sorted(pieces(p), key=lambda q: -(bounds(q)[2] - bounds(q)[0]) * (bounds(q)[3] - bounds(q)[1]))
    rg = ps_[0]
    hole = max((c for c in contours(rg) if area(c) < 0), key=lambda c: -area(c)); h = bounds(hole)
    cx, cy = (h[0] + h[2]) / 2, (h[1] + h[3]) / 2
    (l, r) = row(rg, cy)
    turned = pathops.Path(); rg.draw(TransformPen(turned.getPen(), (0, 1, 1, 0, 0, 0)))
    (b, t) = row(turned, cx)
    sides = [l[1] - l[0], r[1] - r[0], b[1] - b[0], t[1] - t[0]]
    return rg, sides, min(h[2] - h[0], h[3] - h[1]), ps_[1:]


@pytest.mark.parametrize('ps,st', ALL)
def test_rings_take_the_o(ps, st):
    """The rings were hairlines beside the letters: ring against the o's side, Kilfane's © 0.34, Tuam's © 0.31 and @ 0.36,
    Céilí's 0.39 (its Bold's ° 37 -> 41 and @ 57 -> 63 units for a stem 108 -> 169), Carrick's © ® 0.23 and ° 0.18. Every
    ring of @ ¤ is now at least half the o's heavier side, those of © ® (which keep the figures' height) 0.4 of it, and
    °'s half of it or as near as a ring of its size comes with its counter as wide (a third of its height, less the
    sloped styles' narrowing). In Céilí's bolds the r of ®, whose 12 to 14-unit mouth the slope and the grid would
    shut, is not drawn smaller, and their © ® ring takes the white it leaves: 55 -> 66 (Bold Italic 61)."""
    o = o_side(ps, st)
    for n in ['at', 'currency'] + (['at.case'] if ps == 'KilfaneDigital' else []):
        rg, sides, span, rest = ring_parts(ps, st, n)
        assert min(sides) >= 0.5 * o, (st, n, sides, o)
    held = ps == 'CeiliDigital' and 'Bold' in st
    for n in ('copyright', 'registered'):
        rg, sides, span, rest = ring_parts(ps, st, n)
        assert min(sides) >= (1.1 * 55 if held else 0.4 * o), (st, n, sides, o)
    rg, sides, span, rest = ring_parts(ps, st, 'degree'); b = bounds(rg)
    assert min(sides) >= min(0.5 * o, (b[3] - b[1]) / 3 - 15), (st, sides, o, b)


@pytest.mark.parametrize('ps,st', ALL)
def test_the_figure_signs_keep_the_figures_height(ps, st):
    """At half the o the rings grew © and ® past the figures (Carrick's 550 to 674 tall, Italic 700; Tuam's 690 to 773,
    Italic 784; Céilí's Bold 565 to 634) and ° into a dot beside the figures, twice the bullet (Carrick's 149 to 324
    tall, Tuam's 163 to 297, Céilí's Bold 162 to 269): © and ® stand from the baseline to the figures' height, the top of
    º, and ° hangs from it, no taller than 0.3 of it, a bold's no more than 1.15 times its Regular's."""
    top = bounds(outline(ps, st, 'ordmasculine'))[3]
    for n in ('copyright', 'registered'):
        b = bounds(outline(ps, st, n))
        assert abs(b[1]) <= 2 and abs(b[3] - top) <= 2, (st, n, b, top)
    b = bounds(outline(ps, st, 'degree'))
    assert abs(b[3] - top) <= 2 and b[3] - b[1] <= 0.31 * top, (st, b, top)
    if 'Bold' in st:
        r = bounds(outline(ps, st.replace('Bold', '').strip() or 'Regular', 'degree'))
        assert b[3] - b[1] <= 1.15 * (r[3] - r[1]), (st, b, r)


@pytest.mark.parametrize('ps,st', ALL)
def test_rings_keep_their_counters_and_letters_clear(ps, st):
    """A heavier ring must not close a counter or crowd its letter: the c of ©, the r of ® and the a of @ stand clear of
    their ring (Céilí's Bold Italic a stood 4 units from it) and keep the pieces and counters of the font's own letter
    (Carrick's c and Tuam's r keep their cuts, Céilí's bold r its open bowl), ° stays a ring (its counter as wide as its
    ring, the final review's rule: at 0.6 of it Carrick's read as a dot at text sizes) and ¤'s counter at least 1.4 of
    its ring; © and ® share one ring."""
    def topology(p):
        a = [area(c) for c in contours(p)]
        return sum(v > 0 for v in a), sum(v < 0 for v in a)
    letter = {'copyright': 'c', 'registered': 'R' if ps == 'KilfaneDigital' else 'r', 'at': 'a'}
    for n, src in letter.items():
        rg, sides, span, rest = ring_parts(ps, st, n)
        assert min(white(rg, q) for q in rest) >= 0.15 * min(sides), (st, n, [white(rg, q) for q in rest], sides)
        own = topology(outline(ps, st, src))
        assert topology(outline(ps, st, n)) == (own[0] + 1, own[1] + 1), (st, n, topology(outline(ps, st, n)), own)
        # its counters as open as its own letter's at that size (Carrick's ® r, drawn smaller at its own weight,
        # kept 0.13 of its bowl): the inner letter's least counter at least 0.4 of the letter's, scaled to its height
        holes = lambda p: sorted(-area(c) for c in contours(p) if area(c) < 0)
        inner, mine = pathops.Path(), outline(ps, st, src)
        for q in rest:
            q.draw(inner.getPen())
        k = (lambda b, c: (b[3] - b[1]) / (c[3] - c[1]))(bounds(inner), bounds(mine))
        for a, b in zip(holes(mine), holes(inner)):
            assert b >= 0.4 * k * k * a, (st, n, b, a, k)
    for n, share in (('degree', 1.0), ('currency', 1.4)):
        rg, sides, span, rest = ring_parts(ps, st, n)
        assert not rest and topology(outline(ps, st, n)) == (1, 1) and span >= share * min(sides), (st, n, span, sides)
    # one ring (a sloped style may narrow one of them without its hair of weight, as Tuam's keeps © narrow)
    c, r = bounds(ring_parts(ps, st, 'copyright')[0]), bounds(ring_parts(ps, st, 'registered')[0])
    across = 1 if 'Italic' not in st else 10
    assert abs(c[1] - r[1]) <= 1 and abs(c[3] - r[3]) <= 1 and abs(c[0] - r[0]) <= across and abs(c[2] - r[2]) <= across, (c, r)


# ---------------------------------------------------------------- combining marks
def shape(ps, st, text):
    F = font(ps, st)
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties(); hb.shape(F['hb'], buf, {'kern': False})
    out, x = [], 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        n = F['order'][info.codepoint]
        out.append((n, outline(ps, st, n, upright=False, dx=x + pos.x_offset, dy=pos.y_offset)))
        x += pos.x_advance
    return out


@functools.lru_cache(maxsize=None)
def gap(ps, st):
    """The face's accent gap: the median white under the marks of its precomposed vowels (á à â ä é è ê ë ...)."""
    ws = []
    for v in 'aeiou':
        base = outline(ps, st, {'i': 'dotlessi'}.get(v, v), upright=False)
        for m in '́̀̂̈':
            p = outline(ps, st, unicodedata.normalize('NFC', v + m), upright=False)
            ws += [white(q, base) for q in pieces(p)
                   if abs(area(pathops.op(q, base, pathops.PathOp.INTERSECTION, fix_winding=True))) < 1]
    return float(np.median(ws))


def least(ps, st, m):
    """The least white a mark must keep from its letter: 0.7 of the face's accent gap above the letter; 0.6 of the comma
    below's own gap (0.06 x-height) under it."""
    return 0.7 * gap(ps, st) if m in TOP else 0.6 * 0.06 * font(ps, st)['xh']


@functools.lru_cache(maxsize=None)
def descends(ps, st, name):
    return bounds(outline(ps, st, name, upright=False))[1] < -0.1 * font(ps, st)['xh']


@pytest.mark.parametrize('ps,st', ALL)
def test_combining_marks_clear_their_letters(ps, st):
    """A combining mark typed after a letter with no precomposed form (HarfBuzz composes those that have one) took the
    one anchor the acute set: Carrick's t + tilde stood 22 units from the t's flag (the face's gap is 44), Tuam's
    b and d + any top mark landed on the bowl, where the ponc goes (b + diaeresis -64), and every bottom mark on a letter
    with a descender ran into it (Carrick y + cedilla -94, Céilí j + ogonek -102). Every top mark now stands at least 0.7
    of the face's gap clear of every Latin letter and the comma and dot below 0.6 of the comma's gap under the line;
    a cedilla or ogonek, which join their letter, join a letter with a descender no deeper than one on the baseline."""
    bad, joins = [], {m: [] for m in ATTACHED}
    for b in LETTERS:
        for m in TOP + BOTTOM + ATTACHED:
            s = shape(ps, st, b + m)
            assert '.notdef' not in [n for n, _ in s], (b + m)
            if len(s) == 1:
                continue                                        # composed: a precomposed letter
            (bn, bp), (mn, mp) = s[0], s[-1]
            w = white(mp, bp)
            if m in ATTACHED:
                joins[m].append((w, b, descends(ps, st, bn)))
            elif w < least(ps, st, m):
                bad.append((b + m, round(w, 1)))
    for m, ws in joins.items():
        floor = min(w for w, b, d in ws if not d)
        bad += [(b + m, round(w, 1)) for w, b, d in ws if d and w < 1.25 * floor - 3]
    assert not bad, (st, bad[:20])


STACKS = ['̈́', '̂́', '̄́', '̆̃', '̇̄', '̃̄', '́̇',
          '̌̇', '́́', '̣̂', '̣̦', '̦̣', '̣́̂']


@pytest.mark.parametrize('ps,st', ALL)
def test_stacked_marks_build_outward(ps, st):
    """There was no mkmk feature, so a second top mark printed on the first (x + circumflex + acute: -154 in Kilfane) and
    a mark typed after a precomposed letter (é + circumflex, which HarfBuzz composes first) on its accent. Each mark now
    stands on the one before it, or hangs from it, at least 0.7 of the face's gap apart, and clear of the letter."""
    assert 'mkmk' in {fr.FeatureTag for fr in font(ps, st)['tt']['GPOS'].table.FeatureList.FeatureRecord}
    g = 0.7 * gap(ps, st); bad = []
    for b in LETTERS:
        for ms in STACKS:
            s = shape(ps, st, b + ms)
            ps_ = [q for _, q in s]
            for i in range(1, len(ps_)):
                kind = TOP[0] if s[i][0] in TOPS(ps, st) else BOTTOM[0]
                w_base = white(ps_[i], ps_[0]); w_marks = min((white(ps_[i], q) for q in ps_[1:i]), default=1e9)
                if w_base < least(ps, st, kind) or w_marks < g:
                    bad.append((b + ms, [n for n, _ in s], round(w_base, 1), round(w_marks, 1)))
    assert not bad, (st, bad[:12])


def TOPS(ps, st):
    F = font(ps, st)
    return {F['cm'][ord(m)] for m in TOP}


IRISH = 'ḃċḋḟġṁṗṡṫḂĊḊḞĠṀṖṠṪ'


@pytest.mark.parametrize('ps,st', ALL)
def test_irish_dotted_letters_shape_as_before(ps, st):
    """The dot above has an anchor of its own: Irish input, a lenited letter typed whole or as letter + U+0307, still
    shapes as the precomposed letter, and its dot stands where the face sets its ponc."""
    F = font(ps, st)
    for ch in IRISH:
        if ord(ch) not in F['cm']:
            continue
        whole = shape(ps, st, ch); parts = shape(ps, st, unicodedata.normalize('NFD', ch))
        assert [n for n, _ in parts] == [n for n, _ in whole] == [F['cm'][ord(ch)]], ch


def test_dot_below_is_built():
    """U+0323, the combining dot below, which the test sequences need, is built in every style, from the face's dot."""
    for ps, st in ALL:
        F = font(ps, st)
        assert 0x323 in F['cm'] and F['tt']['hmtx'][F['cm'][0x323]][0] == 0, (ps, st)


@pytest.mark.parametrize('st', FACES['CeiliDigital'])
def test_the_insular_r_comma_stands_clear(st):
    """Céilí's ŗ with the insular r (ss01): the comma below hung where it hangs under r, beside the r's descender, and the
    bold's pen brought the two within 6 units (Bold) and 0.8 (Bold Italic). It moves along the line until it stands at
    least the comma's own gap under the baseline (0.06 x-height) clear."""
    r, rc = outline('CeiliDigital', st, 'r.alt1', upright=False), outline('CeiliDigital', st, 'uni0157.alt1', upright=False)
    comma = [q for q in pieces(rc) if abs(area(pathops.op(q, r, pathops.PathOp.INTERSECTION, fix_winding=True))) < 1]
    assert len(comma) == 1 and white(comma[0], r) >= 0.05 * font('CeiliDigital', st)['xh'], white(comma[0], r)


RECORDS = {'KilfaneDigital': 'kilfane-sheet-frame', 'CarrickDigital': 'round-06/carrick',
           'TuamUncialDigital': 'tuam-judgement', 'CeiliDigital': 'ceili-judgement'}


@pytest.mark.parametrize('ps', FACES)
def test_the_fifth_pass_is_recorded(ps):
    """Each face's judged-edits.json records the pass (`fifth_pass`): each correction with its reason, and the glyphs
    whose outlines it changes in each style, none but the signs, @'s case form and Céilí's ŗ.alt1."""
    import json, os
    path = os.path.join(os.path.dirname(__file__), '..', 'research', RECORDS[ps], 'judged-edits.json')
    rec = json.load(open(path, encoding='utf-8'))['fifth_pass']
    assert all(len(rec[k]['why']) > 40 for k in ('approxequal', 'rings', 'marks'))
    assert rec['approxequal']['white'] == 0.7 and rec['rings']['share'] == 0.5 and rec['marks']['added'] == ['dotbelowcomb']
    signs = {'approxequal', 'at', 'copyright', 'currency', 'degree', 'registered'}
    for st in FACES[ps]:
        changed = set(rec['changed'][st.replace(' ', '')])
        assert signs <= changed <= signs | {'at.case', 'uni0157.alt1'}, st
        assert all(n in font(ps, st)['order'] for n in changed | {'dotbelowcomb'}), st
