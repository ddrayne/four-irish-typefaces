"""Kilfane's third finishing pass (research/kilfane-sheet-frame/judged-edits.json, "finishing": "bold_curves",
"bold_marks"), checked on the released fonts (fonts/, or FONTDIR): the bold's faceted curves drawn as curves, and
its cedilla and ogonek drawn with its pen."""
import math, unicodedata
import pytest
from test_kilfane_second_pass import BOLD, font, outline, stroke, bounds

LETTERS, ALTERNATES = set('GSsvwxyßW'), {'g.alt1', 'y.alt1'}


def listed(style):
    """The listed letters (judged-edits.json, "bold_curves") and every accented form of them in the font, each
    with the name of its letter."""
    f, gs, cm, _ = font(style)
    first = {}
    for cp, n in sorted(cm.items()):
        first.setdefault(n, cp)
    out = {}
    for n in f.getGlyphOrder():
        alt = n.endswith('.alt1'); cp = first.get(n[:-5] if alt else n)
        if cp is not None:
            base = unicodedata.normalize('NFD', chr(cp))[0]
            if (base + '.alt1' in ALTERNATES) if alt else (base in LETTERS):
                out[n] = cm[ord(base)] + ('.alt1' if alt else '')
    return out


def letter_contours(style, name, base):
    """The contours of an accented form that draw its letter (with a mark joined to it), not a separate mark."""
    import glyphs, pathops
    b = bounds(outline(style, base, upright=False))
    over = lambda c: min(c[2], b[2]) - max(c[0], b[0]) > 0 and min(c[3], b[3]) - max(c[1], b[1]) > 0.5 * (c[3] - c[1])
    p = pathops.Path()
    for c in glyphs.contours(outline(style, name, upright=False)):
        if over(bounds(c)):
            c.draw(p.getPen())
    return p


def faults(p, short=8.0, longest=90.0, turn=35.0):
    """The pieces of an outline under `short` units, and the joins of a run of straight facets: two lines, each
    under `longest`, meeting at under `turn` degrees (a curve drawn as a polygon)."""
    import kilfane_studio as KS
    small, facets = [], []
    for segs in KS.segments(p):
        n = len(segs)
        for i, (k, q) in enumerate(segs):
            L = math.dist(KS.FN._start(segs, i), q[-1]); j = (i + 1) % n
            if L < short:
                small.append((tuple(round(v) for v in q[-1]), round(L, 1)))
            if k == 'L' and segs[j][0] == 'L' and L < longest and math.dist(KS.FN._start(segs, j), segs[j][1][-1]) < longest:
                t = KS._angle(KS._tan_in(segs, i), KS._tan_out(segs, j))
                if 0.5 < t < turn:
                    facets.append((tuple(round(v) for v in q[-1]), round(t, 1)))
    return small, facets


@pytest.mark.parametrize('style', BOLD)
def test_bold_curves_are_drawn_as_curves(style):
    """G, S, s, v, w, x, y, ß, W and the alternate g and y, with their accented forms: the bold's pen left their
    curves as runs of straight facets, with pieces of 1 to 7 units at their corners (47 glyphs a style); every
    curve is now drawn as curves, the marks' too, and no piece of a letter is under 8 units."""
    names = listed(style)
    assert len(names) >= 44
    facets = {n: f for n in names if (f := faults(outline(style, n, upright=False))[1])}
    short = {n: s for n, b in names.items() if (s := faults(letter_contours(style, n, b))[0])}
    assert not facets and not short, (facets, short)


@pytest.mark.parametrize('style', BOLD)
def test_bold_curves_keep_the_letters(style):
    """The curves keep each letter's pieces and counters, as the Regular has them."""
    import topo
    from conftest import static
    reg = 'Regular' if style == 'Bold' else 'Italic'
    names = set(listed(style))
    flagged = [n for n, *_ in topo.compare(static('KilfaneDigital', reg), static('KilfaneDigital', style)) if n in names]
    assert not flagged, flagged


@pytest.mark.parametrize('style', BOLD)
def test_bold_cedilla_and_ogonek_take_the_bold_pen(style):
    """The cedilla and ogonek took their weight from the ring's hairline (40 to 43 in the Regular, 46 to 50 in the
    bold, against acutes of 90 and stems of 166): they are drawn with the bold's pen at the stroke accents' share,
    as heavy as the bold's comma below, and still join their letters with the hook as far below them."""
    import bolden
    reg = 'Regular' if style == 'Bold' else 'Italic'
    for name in ('cedilla', 'ogonek', 'uni0327', 'uni0328'):
        w, r = stroke(outline(style, name)), stroke(outline(reg, name))
        assert w >= 1.5 * r and w >= 0.7 * stroke(outline(style, 'acute')), (name, w, r)
        assert abs(w - stroke(outline(style, 'uni0326'))) <= 8, name           # the comma below
    for ch, base in (('ç', 'c'), ('Ç', 'C'), ('ş', 's'), ('ţ', 't'), ('ą', 'a'), ('ę', 'e'), ('Ą', 'A')):
        assert bolden.pieces(outline(style, ch)) == bolden.pieces(outline(reg, ch)) == 1, ch
        assert abs(hook_white(style, ch, base) - hook_white(reg, ch, base)) <= 4, ch


def hook_white(style, ch, base):
    """The white between a bottom mark and its letter, below the letter's foot (its neck, where it joins, left out)."""
    import numpy as np
    import shapes as SH, glyphs, kilfane_studio as KS
    from scipy.spatial import cKDTree
    p, b = outline(style, ch), outline(style, base)
    sample = lambda q: np.vstack([np.vstack([KS._samples(KS.FN._start(s, i), g, 1.0) for i, g in enumerate(s)]) for s in KS.segments(q)])
    mark = sample(SH.difference(p, b))
    mark = mark[mark[:, 1] < bounds(b)[1] - 25]
    return float(cKDTree(sample(b)).query(mark)[0].min())
