"""Kilfane's second finishing pass (research/kilfane-sheet-frame/judged-edits.json, "finishing"), checked on the
released fonts (fonts/, or FONTDIR): the bold's marks, rules and symbols at the bold's weight, its open joins
cut from the terminal alone, the g's tail clear of its bowl, Ů's ring on the line, the section's corners, and
the room before a fada, between the bold's capitals and after a quote."""
import math
import numpy as np
import pathops
import pytest
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from conftest import static

STYLES = ['Regular', 'Italic', 'Bold', 'Bold Italic']
BOLD = ['Bold', 'Bold Italic']
SLANT = math.tan(math.radians(8.0))
_fonts = {}


def font(style):
    if style not in _fonts:
        path = static('KilfaneDigital', style); f = TTFont(path)
        _fonts[style] = (f, f.getGlyphSet(), f.getBestCmap(), path)
    return _fonts[style]


def outline(style, name, upright=True):
    """A glyph's outline; a sloped style's sheared back upright (about the half x-height, as it was sloped)."""
    f, gs, cm, _ = font(style)
    name = cm[ord(name)] if len(name) == 1 else name
    p = pathops.Path(); gs[name].draw(p.getPen())
    if upright and 'Italic' in style:
        from shapes import transform
        yc = f['OS/2'].sxHeight / 2
        p = transform(p, (1, 0, -SLANT, 1, yc * SLANT, 0))
    return p


def bounds(p):
    bp = BoundsPen(None); p.draw(bp); return bp.bounds


def stroke(p):
    """The median stroke width along the skeleton (one-unit raster)."""
    from scipy import ndimage
    from skimage.morphology import skeletonize
    from outline_util import flatten, raster
    from fontTools.pens.recordingPen import RecordingPen
    b = bounds(p); x0, y1 = b[0] - 4, b[3] + 4
    r = RecordingPen(); p.draw(r)
    a = raster(flatten(r.value, 16), (int(b[2] - b[0]) + 9, int(b[3] - b[1]) + 9), lambda q: (q[0] - x0, y1 - q[1])) > 0
    return float(2 * np.median(ndimage.distance_transform_edt(a)[skeletonize(a)]))


def shaped(style, text):
    """[(glyph name, x)] for a shaped string, with kerning."""
    import uharfbuzz as hb
    f, gs, cm, path = font(style)
    hf = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties(); hb.shape(hf, buf, {'kern': True})
    order = f.getGlyphOrder(); x = 0; out = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        out.append((order[info.codepoint], x + pos.x_offset)); x += pos.x_advance
    return out


def kern(style, text):
    import uharfbuzz as hb
    path = font(style)[3]; hf = hb.Font(hb.Face(hb.Blob.from_file_path(path))); adv = []
    for k in (True, False):
        b = hb.Buffer(); b.add_str(text); b.guess_segment_properties(); hb.shape(hf, b, {'kern': k})
        adv.append(b.glyph_positions[0].x_advance)
    return adv[0] - adv[1]


def clearance(style, pair, above=None):
    """The narrowest white across between a shaped pair, at one-unit heights (only above `above`, if given)."""
    from study_spacing import silhouette
    (a, xa), (b, xb) = shaped(style, pair)
    pa, pb = outline(style, a, upright=False), outline(style, b, upright=False)
    lo = min(bounds(pa)[1], bounds(pb)[1]); hi = max(bounds(pa)[3], bounds(pb)[3])
    ys = np.arange(math.floor(lo) + .5, hi, 1.)
    _, ra = silhouette(pa, ys); lb, _ = silhouette(pb, ys)
    g = xb + lb - (xa + ra)
    g = g[np.isfinite(g) & (ys > above if above is not None else True)]
    return float(g.min()) if g.size else math.inf          # nothing of the pair at those heights


@pytest.mark.parametrize('style', BOLD)
def test_bold_marks_take_the_bold_pen(style):
    reg = 'Regular' if style == 'Bold' else 'Italic'
    # the acute at about the Regular's proportion to the stems (61 against 114: about 90 against 166)
    assert 80 <= stroke(outline(style, 'acute')) <= 100
    # the ponc near the bold's i dot, not the Regular's
    b = bounds(outline(style, 'dotaccent')); w, h = b[2] - b[0], b[3] - b[1]
    assert w >= 155 and h >= 130, (w, h)
    for name in ('circumflex', 'caron', 'tilde', 'ring', 'dieresis'):
        assert stroke(outline(style, name)) >= 1.25 * stroke(outline(reg, name)), name
    # and the gap between letter and mark stays the Regular's
    import glyphs
    def mark_gap(st, ch, base):
        top = bounds(outline(st, base))[3]
        return min(bounds(c)[1] for c in glyphs.contours(outline(st, ch)) if bounds(c)[1] > top) - top
    for ch, base in (('é', 'e'), ('É', 'E'), ('ċ', 'c'), ('Ċ', 'C')):
        assert abs(mark_gap(style, ch, base) - mark_gap(reg, ch, base)) <= 2, ch


@pytest.mark.parametrize('style', BOLD)
def test_bold_rules_and_symbols_at_the_bold_weight(style):
    for name in ('hyphen', 'endash', 'emdash', 'minus'):
        b = bounds(outline(style, name))
        assert 90 <= b[3] - b[1] <= 100, (name, b[3] - b[1])           # 60 + 2 ry
    for name in ('plus', 'equal', 'less', 'guillemotleft', 'guilsinglright'):
        assert stroke(outline(style, name)) >= 85, name
    assert 70 <= stroke(outline(style, 'numbersign')) <= 80
    # the section drawn from the regular's with the bold's pen: as black as the bold s, over the regular's extent
    sec = outline(style, 'section'); b = bounds(sec)
    assert abs(b[1] - 66) <= 6 and abs(b[3] - 700) <= 3, b
    assert stroke(sec) >= 0.95 * stroke(outline(style, 's'))


@pytest.mark.parametrize('style', STYLES)
def test_g_tail_clears_its_bowl(style):
    import kilfane_studio as KS
    for ch in 'gġğĝģ':
        assert (KS.opening(outline(style, ch)) or 0) >= 30, ch


@pytest.mark.parametrize('style', BOLD)
def test_bold_joins_keep_a_straight_full_stem(style):
    import kilfane_studio as KS
    for ch in 'kr':
        polys = KS.polygons(KS.segments(outline(style, ch)))
        widths = [KS.crossings(polys, y)[0] for y in range(150, 300, 2)]
        w = [b - a for a, b in widths]
        right = [b for a, b in widths]
        assert max(abs(v - 166) for v in w) <= 3, (ch, min(w), max(w))
        assert max(right) - min(right) <= 2, ch                       # the stem's edge runs straight past the join
    for ch in ('k', 'r', 'six', 'nine'):
        assert 15 <= (KS.opening(outline(style, ch)) or 0), ch            # and the drawn open join stays open


@pytest.mark.parametrize('style', STYLES)
def test_ring_sits_above_U(style):
    import glyphs
    p, u = outline(style, 'Ů'), outline(style, 'U')
    top = bounds(u)[3]
    ring = [c for c in glyphs.contours(p) if bounds(c)[1] > 0.5 * top]
    assert ring and min(bounds(c)[1] for c in ring) >= 740


@pytest.mark.parametrize('style', STYLES)
def test_section_has_no_spurs(style):
    import kilfane_studio as KS
    for segs in KS.segments(outline(style, 'section', upright=False)):
        for i, (k, q) in enumerate(segs):
            assert math.dist(KS.FN._start(segs, i), q[-1]) >= 8, (style, q[-1])


@pytest.mark.parametrize('style', STYLES)
def test_fada_clears_the_letter_before_it(style):
    for left in 'BCEFPRSTVÉḂĊḞṖṠṪNMfltr':
        for i in 'íìîïĩī':
            cm = font(style)[2]
            if ord(left) in cm and ord(i) in cm:
                above = font(style)[0]['OS/2'].sxHeight + 10
                assert clearance(style, left + i, above) >= 38, (left + i)


@pytest.mark.parametrize('style', BOLD)
def test_bold_capitals_keep_their_room(style):
    caps = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    worst = min((clearance(style, a + b), a + b) for a in caps for b in caps)
    assert worst[0] >= 28, worst


@pytest.mark.parametrize('style', STYLES)
def test_quotes_keep_off_accented_lowercase(style):
    for q in '’‘”“':
        for ch in 'aâáàäãåeêéèëiîíoôóöuûúüyýcçgġsṡ':
            assert kern(style, q + ch) >= -40, q + ch
            assert kern(style, ch + q) >= -40, ch + q
