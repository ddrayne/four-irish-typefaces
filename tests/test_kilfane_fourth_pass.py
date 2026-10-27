"""Kilfane's fourth finishing pass (research/kilfane-sheet-frame/judged-edits.json, "finishing": "bold_math", "bold_dots",
"bold_small", "spacing", "case", "settle" and the kerning's "clearances"), checked on the released fonts (fonts/, or
FONTDIR): the bold's math signs grown in place, its dots clear of their strokes, its small signs at its weight; the
capitals' room in every style; j and ? spaced by one rule; the sloped styles' joins smooth; the section; the case forms."""
import math
import numpy as np
import pytest
from test_kilfane_second_pass import STYLES, BOLD, SLANT, font, outline, bounds, stroke, clearance, kern, shaped

UPRIGHT = {'Regular': 'Regular', 'Italic': 'Italic', 'Bold': 'Regular', 'Bold Italic': 'Italic'}


def pieces(p):
    import bolden
    return sorted(bolden.components(p), key=lambda q: bounds(q)[1])


def white(a, b):
    import kilfane_studio as KS
    return KS.white(a, b)


def span(p):
    b = bounds(p); return b[1], b[3]


@pytest.mark.parametrize('style', BOLD)
def test_bold_math_signs_grow_in_place(style):
    """The bold's pen moved each piece of a math sign outward (= bars 142-202 and 280-340 became 88-181 and 301-394, the
    white from 78 to 120): each piece now grows about its own centre and the Regular's white between them stays."""
    reg = UPRIGHT[style]
    for n in ('equal', 'plusminus', 'lessequal', 'greaterequal', 'divide', 'approxequal'):
        b, r = pieces(outline(style, n)), pieces(outline(reg, n))
        assert len(b) == len(r), n
        for (b0, b1), (r0, r1) in zip(zip(b, b[1:]), zip(r, r[1:])):
            assert abs(white(b0, b1) - white(r0, r1)) <= 3, (n, white(b0, b1), white(r0, r1))
    eq = [span(q) for q in pieces(outline(style, 'equal'))]
    assert all(abs(u - v) <= 3 for u, v in zip(eq[0] + eq[1], (110, 202, 280, 372))), eq
    # an underbar or a dot no further out than the Regular's extent and the pen's 17
    assert bounds(outline(style, 'plusminus'))[1] >= bounds(outline(reg, 'plusminus'))[1] - 18
    for n in ('lessequal', 'greaterequal'):
        assert bounds(pieces(outline(style, n))[0])[1] >= bounds(pieces(outline(reg, n))[0])[1] - 18, n
    d, dr = span(outline(style, 'divide')), span(outline(reg, 'divide'))
    assert d[0] >= dr[0] - 18 and d[1] <= dr[1] + 18, (d, dr)
    # ~ and ^ grow about their centres (they grew upward only), and the one-piece signs stay on the axis
    for n in ('asciitilde', 'asciicircum', 'plus', 'minus', 'multiply', 'less', 'greater', 'notequal'):
        (b0, b1), (r0, r1) = span(outline(style, n)), span(outline(reg, n))
        assert abs((b0 + b1) / 2 - (r0 + r1) / 2) <= 3, n
        assert b1 - b0 >= r1 - r0, n


@pytest.mark.parametrize('style', BOLD)
def test_bold_dots_keep_their_white(style):
    """The pen grew the dots of ! and ? and their strokes towards each other (14 and 16 units against the Regular's 49
    and 52; i and j 25 and 21): ! ? ¡ ¿ keep the Regular's white, and the dots of i and j stand 52 units clear."""
    reg = UPRIGHT[style]
    for n in ('exclam', 'question', 'exclamdown', 'questiondown'):
        assert white(*pieces(outline(style, n))) >= white(*pieces(outline(reg, n))) - 1, n
    for n in ('i', 'j'):
        assert white(*pieces(outline(style, n))) >= 50, n
        top = bounds(pieces(outline(style, n))[-1])[3]
        assert top <= bounds(outline(reg, n))[3] + 20, n               # the dot stands only a little higher


@pytest.mark.parametrize('style', STYLES)
def test_capitals_keep_their_room(style):
    """The Bold's capitals kept 30 units (second pass), but not the Regular's and Italic's (T Y 10, F V 11), nor the
    bold's accented capitals (T Í 16 against T I 36, T Ĺ 17): every style's capitals and accented capitals keep 30."""
    caps = 'ABCDEFGHIJKLMNOPQRSTUVWXYZÍÌÎÏĨĹÚÉÁÓ'
    worst = min((clearance(style, a + b), a + b) for a in caps for b in caps)
    assert worst[0] >= 28, worst


@pytest.mark.parametrize('style', STYLES)
def test_capitals_before_lowercase_keep_their_room(style):
    """T F P (and every capital) before lowercase: T h was 12/13/14/10 in the four styles, P i 17/10/13/10, the Bold's
    P f 8 and T b 8. A capital before a lowercase letter keeps 30 units, 20 in the bolds: at 30 their A l, T h, F h and
    F l opened from +20/+25 to +45 and A b, T b to +60, wider than two l (the final review)."""
    bold = 'Bold' in style
    worst = min((clearance(style, a + b), a + b) for a in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for b in 'abcdefghijklmnopqrstuvwxyzíḃḟĥ')
    assert worst[0] >= (18 if bold else 28), worst
    if bold:
        assert max(kern(style, p) for p in ('Al', 'Th', 'Fh', 'Fl')) <= 40, [(p, kern(style, p)) for p in ('Al', 'Th', 'Fh', 'Fl')]


def mid_white(style, pair):
    """The white across a shaped pair about half the x-height (its mean from 0.4 to 0.6 of it)."""
    from study_spacing import silhouette
    (a, xa), (b, xb) = shaped(style, pair)[:2]
    y = font(style)[0]['OS/2'].sxHeight * np.linspace(0.4, 0.6, 9) + 0.5
    _, ra = silhouette(outline(style, a, upright=False), y); lb, _ = silhouette(outline(style, b, upright=False), y)
    return float(np.mean(xb + lb - xa - ra))


@pytest.mark.parametrize('style', STYLES)
def test_j_is_spaced_as_i(style):
    """The bold's j stood 60 units right of i's place (advance 369 against i's 309; n|j 191 against n|i 146 even with
    -15 to -25 kerns): its stem stands where i's does, in every style, with no kerning to make up for it."""
    for left in 'nohu':
        assert abs(mid_white(style, left + 'j') - mid_white(style, left + 'i')) <= 2, left
        assert kern(style, left + 'j') == kern(style, left + 'i'), left
    f = font(style)[0]
    assert abs(f['hmtx']['j'][0] - f['hmtx']['i'][0]) <= 3


@pytest.mark.parametrize('style', STYLES)
def test_question_is_spaced_as_exclam(style):
    """? stood 41 units closer than ! in the Regular (n? 96 against n! 137) and 13 further in the Bold: ? stands on its
    stem as ! on its stroke in every style, and ¿ as ¡."""
    for left in 'noH':
        assert abs(mid_white(style, left + '?') - mid_white(style, left + '!')) <= 4, left
    for right in 'nH':
        assert abs(mid_white(style, '¿' + right) - mid_white(style, '¡' + right)) <= 4, right


def kinks(p, slope=0.0, lo=2.0, hi=12.0):
    """Near-smooth joins left bent: a curve on one side, bending by more than lo degrees as drawn, and by less than hi
    (kilfane_studio.KINK) once the slope is sheared off, so that a corner of the upright that the shear brings under
    12 degrees stays a corner."""
    import kilfane_studio as KS
    up = lambda u: None if u is None else (u[0] - u[1] * slope, u[1])
    out = []
    for segs in KS.segments(p):
        n = len(segs)
        for i, (k, q) in enumerate(segs):
            j = (i + 1) % n
            if k == 'L' and segs[j][0] == 'L':
                continue
            a, b = KS._tan_in(segs, i), KS._tan_out(segs, j)
            if lo < KS._angle(a, b) and KS._angle(up(a), up(b)) < hi:
                out.append((tuple(round(v) for v in q[-1]), round(KS._angle(a, b), 1)))
    return out


def bent(style):
    f = font(style)[0]; slope = SLANT if 'Italic' in style else 0.0
    return {n: k for n in f.getGlyphOrder() if n not in ('.notdef', 'space') and (k := kinks(outline(style, n, upright=False), slope))}


@pytest.mark.parametrize('style', STYLES)
def test_joins_are_smooth(style):
    """Rounding the sheared outlines to whole units bent the short handles at stem and arch joins by about the slope
    (the Italic m's six joins 8 to 11 degrees; 425 Italic and 432 Bold Italic glyphs with near-smooth joins bent 2 to 12
    degrees, 201 and 338 in the uprights): the stem and arch joins are smooth in every style, and three quarters of the
    other bent joins are too (the rest would move more than 1.5 units: an accent's pen corner, a bowl's terminal)."""
    b = bent(style)
    assert not any(b.get(n) for n in 'nhubdpqrkil'), {n: b.get(n) for n in 'nhubdpqrkil' if b.get(n)}
    assert len(b.get('m', [])) <= 1, b.get('m')          # the Italic's stem-top corner, a 60 degree corner upright
    assert len(b) <= {'Regular': 25, 'Italic': 100, 'Bold': 60, 'Bold Italic': 100}[style], (len(b), sorted(b)[:30])


@pytest.mark.parametrize('style', STYLES)
def test_section_is_smooth_and_open(style):
    """The section's joins (6 to 10 degrees in the Bold and Italic) are smooth, and the Bold's terminal openings, 16
    units against the Regular's 40, keep at least 30."""
    import kilfane_studio as KS
    slope = SLANT if 'Italic' in style else 0.0
    assert not kinks(outline(style, 'section', upright=False), slope), kinks(outline(style, 'section', upright=False), slope)
    assert (KS.opening(outline(style, 'section')) or 99) >= 28


@pytest.mark.parametrize('style', BOLD)
def test_bold_small_signs_take_the_bold_pen(style):
    """The bold's bullet was the Regular's outline (174 wide, while the period grew from 107 to 159), and % ‰ @ ® ¹ ² ³
    ½ ¼ ¾ ª º ™ gained about 20 units of stem where the letters gain 52: the bullet grows as the period does, % ‰ and
    the letters in @ © ® take the bold's pen, and the small figures and letters keep (or come near) the Regular's
    proportion to the full-size figures, every counter and opening still open."""
    import topo
    from conftest import static
    reg = UPRIGHT[style]
    w = lambda st, n: (lambda b: b[2] - b[0])(bounds(outline(st, n)))
    assert w(style, 'bullet') >= 0.95 * w(reg, 'bullet') * w(style, 'period') / w(reg, 'period')
    def stem(st, n):                                  # the left side of the upper zero (of %) or the letter's stem
        import kilfane_studio as KS
        p = outline(st, n); b = bounds(p); y = b[3] - 0.22 * (b[3] - b[1]) if n in ('percent', 'perthousand') else 0.45 * (b[1] + b[3])
        a, c = KS.crossings(KS.polygons(KS.segments(p)), y)[0]
        return c - a
    gain = stem(style, 'n') / stem(reg, 'n')            # 114 to 166: % ‰ had gone from 85 only to 105
    for n in ('percent', 'perthousand'):
        assert stem(style, n) / stem(reg, n) >= 0.95 * gain, (n, stem(style, n), stem(reg, n), gain)
    ratio = lambda st, n: stroke(outline(st, n)) / stroke(outline(st, 'one'))
    for n in ('onesuperior', 'twosuperior', 'threesuperior', 'ordfeminine', 'ordmasculine'):
        assert ratio(style, n) >= 0.85 * ratio(reg, n), (n, ratio(style, n), ratio(reg, n))
    names = {'bullet', 'percent', 'perthousand', 'at', 'copyright', 'registered', 'trademark', 'onesuperior', 'twosuperior',
             'threesuperior', 'onequarter', 'onehalf', 'threequarters', 'ordfeminine', 'ordmasculine'}
    flagged = [n for n, *_ in topo.compare(static('KilfaneDigital', reg), static('KilfaneDigital', style), small=0.30) if n in names]
    assert not flagged, flagged


CASE = {'hyphen': '-', 'endash': '–', 'emdash': '—', 'guillemotleft': '«', 'guillemotright': '»', 'guilsinglleft': '‹',
        'guilsinglright': '›', 'colon': ':', 'periodcentered': '·', 'bullet': '•', 'at': '@', 'exclamdown': '¡',
        'questiondown': '¿'}


@pytest.mark.parametrize('style', STYLES)
def test_case_forms_stand_with_the_capitals(style):
    """Kilfane has true capitals, but its hyphen, dashes, guillemets and colon sat on the lowercase axis (241) against
    the capitals' middle (353): with the case feature (HarfBuzz), each is the case form, centred on the capitals, and
    ¡ ¿ stand on the line as ! ? do; without it, nothing changes."""
    import uharfbuzz as hb
    f, gs, cm, path = font(style)
    hf = hb.Font(hb.Face(hb.Blob.from_file_path(path))); order = f.getGlyphOrder()

    def run(text, case):
        b = hb.Buffer(); b.add_str(text); b.guess_segment_properties(); hb.shape(hf, b, {'case': case})
        return [order[i.codepoint] for i in b.glyph_infos], [p.x_advance for p in b.glyph_positions]
    cap = f['OS/2'].sCapHeight
    for n, ch in CASE.items():
        (g,), (a,) = run(ch, True)
        (g0,), (a0,) = run(ch, False)
        assert g == n + '.case' and g0 == n and a == a0, (n, g, g0)
        lo, hi = span(outline(style, g))
        if n in ('exclamdown', 'questiondown'):
            src = 'exclam' if n == 'exclamdown' else 'question'
            assert abs(lo - span(outline(style, src))[0]) <= 2, n
        else:
            assert abs((lo + hi) / 2 - cap / 2) <= 2, (n, lo, hi)
    # the case forms are kerned where they stand: never closer than their glyphs are kerned, and clear of the capitals
    # (the low hyphen tucks under F's arm, F - -110; the raised one is level with it)
    for c in 'ABCDEFHKLPRTVXYZ':
        for text in (c + '-', '-' + c, c + '»', '«' + c, c + ':'):
            with_case, without = kern_case(hf, text, True), kern_case(hf, text, False)
            assert min(without, 0) <= with_case <= max(without, 0) or with_case >= 0, (text, with_case, without)
            assert case_clearance(style, text) >= 8, text


def case_clearance(style, pair):
    """The narrowest white across a pair shaped with the case feature (one-unit heights)."""
    import uharfbuzz as hb
    from study_spacing import silhouette
    f, gs, cm, path = font(style); order = f.getGlyphOrder()
    b = hb.Buffer(); b.add_str(pair); b.guess_segment_properties()
    hb.shape(hb.Font(hb.Face(hb.Blob.from_file_path(path))), b, {'kern': True, 'case': True})
    (a, b_), x = [order[i.codepoint] for i in b.glyph_infos], b.glyph_positions[0].x_advance
    pa, pb = outline(style, a, upright=False), outline(style, b_, upright=False)
    ys = np.arange(math.floor(min(bounds(pa)[1], bounds(pb)[1])) + .5, max(bounds(pa)[3], bounds(pb)[3]), 1.)
    _, ra = silhouette(pa, ys); lb, _ = silhouette(pb, ys)
    g = x + lb - ra; g = g[np.isfinite(g)]
    return float(g.min()) if g.size else math.inf


def kern_case(hf, text, case):
    """The kerning of a two-glyph text, with or without the case feature."""
    import uharfbuzz as hb
    adv = []
    for k in (True, False):
        b = hb.Buffer(); b.add_str(text); b.guess_segment_properties(); hb.shape(hf, b, {'kern': k, 'case': case})
        adv.append(b.glyph_positions[0].x_advance)
    return adv[0] - adv[1]
