"""Shaping with HarfBuzz, as browsers do: accents typed as separate marks land where the
precomposed letters have them, in every style."""
import unicodedata
import pathops
import pytest
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.areaPen import AreaPen
from conftest import static

WORDS = 'áéíóú àèìòù âêîôû äëïöü ãñõ åç ḃċḋḟġṁṗṡṫ ąę čšž őű'


def shape_path(blob, font, text):
    face = hb.Face(blob); f = hb.Font(face); buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(f, buf, {'kern': True, 'mark': True})
    gs = font.getGlyphSet(); order = font.getGlyphOrder()
    p = pathops.Path(); x = 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        g = order[info.codepoint]
        gs[g].draw(TransformPen(p.getPen(), (1, 0, 0, 1, x + pos.x_offset, pos.y_offset)))
        x += pos.x_advance
    return pathops.simplify(p, fix_winding=True), x


def area(p):
    ap = AreaPen(); p.draw(ap); return abs(ap.value)


@pytest.mark.parametrize('ps,style', [(ps, st) for ps, sts in
                                      [('Ceili', ('Regular', 'Italic', 'Bold', 'Bold Italic')), ('Kilfane', ('Regular', 'Italic', 'Bold', 'Bold Italic')),
                                       ('Carrick', ('Regular', 'Italic')), ('TuamUncial', ('Regular', 'Italic'))] for st in sts])
def test_decomposed_accents_match_precomposed(ps, style):
    path = static(ps, style); font = TTFont(path); blob = hb.Blob.from_file_path(path)
    cmap = font.getBestCmap()
    for ch in WORDS.replace(' ', ''):
        dec = unicodedata.normalize('NFD', ch)
        if not all(ord(c) in cmap for c in dec) or ord(ch) not in cmap:
            continue
        a, wa = shape_path(blob, font, ch); b, wb = shape_path(blob, font, dec)
        assert wa == wb, f'{ch}: advance {wa} vs {wb}'
        both = pathops.op(a, b, pathops.PathOp.INTERSECTION, fix_winding=True)
        union = pathops.op(a, b, pathops.PathOp.UNION, fix_winding=True)
        assert area(both) / area(union) > 0.93, f'{ps} {style} {ch}: decomposed accent lands elsewhere'
