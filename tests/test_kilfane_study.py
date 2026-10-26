"""Check the committed candidate, or a fresh build selected by STUDY_FONT_DIR."""
import os
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
import pytest
from conftest import study_coverage

ROOT=Path(__file__).resolve().parents[1]
DIR=Path(os.environ.get('STUDY_FONT_DIR', ROOT/'research/kilfane-study-01/fonts'))


def test_candidate_preserves_source_supported_topology():
    f=TTFont(DIR/'KilfaneStudy1-Regular.otf');gs=f.getGlyphSet()
    expected={'G':1,'Q':3,'r':1,'six':1,'nine':1,'B':3,'eight':3,'a':2,'i':2,'j':2}
    for n,count in expected.items():
        rec=RecordingPen();gs[n].draw(rec)
        assert sum(op=='closePath' for op,_ in rec.value)==count,n


@pytest.mark.parametrize('ext',['otf','ttf','woff','woff2'])
def test_candidate_sanitizes_and_is_separately_named(ext):
    import ots,os
    p=DIR/f'KilfaneStudy1-Regular.{ext}'
    result=ots.sanitize(str(p),os.devnull,capture_output=True)
    assert result.returncode==0,result.stderr
    f=TTFont(p)
    assert f['name'].getDebugName(1)=='Kilfane Study 1'
    assert f['name'].getDebugName(6)=='KilfaneStudy1-Regular'
    assert f['name'].getDebugName(5)=='Version 2.001'


def test_candidate_keeps_coverage_and_shapes_irish_marks():
    import uharfbuzz as hb
    p=DIR/'KilfaneStudy1-Regular.otf'
    f=TTFont(p);before=TTFont(ROOT/'fonts/otf/KilfaneDigital-Regular.otf')
    assert set(f.getBestCmap())==study_coverage(before)
    font=hb.Font(hb.Face(p.read_bytes()));hb.ot_font_set_funcs(font)
    for text in ['ÁÉÍÓÚ áéíóú','A\u0301 E\u0301 I\u0301 O\u0301 U\u0301','Ḃḃ Ċċ Ḋḋ Ḟḟ Ṁṁ Ṗṗ Ṡṡ Ṫṫ']:
        buf=hb.Buffer();buf.add_str(text);buf.guess_segment_properties();hb.shape(font,buf)
        assert all(g.codepoint!=0 for g in buf.glyph_infos),text


def test_candidate_combining_marks_match_precomposed_outlines():
    import unicodedata,pathops,uharfbuzz as hb
    from test_shaping import shape_path,area,WORDS
    p=DIR/'KilfaneStudy1-Regular.otf';font=TTFont(p);blob=hb.Blob.from_file_path(str(p))
    for ch in WORDS.replace(' ',''):
        a,wa=shape_path(blob,font,ch)
        b,wb=shape_path(blob,font,unicodedata.normalize('NFD',ch))
        assert wa==wb,ch
        both=pathops.op(a,b,pathops.PathOp.INTERSECTION,fix_winding=True)
        union=pathops.op(a,b,pathops.PathOp.UNION,fix_winding=True)
        assert area(both)/area(union)>.93,ch


def test_candidate_stylistic_sets_select_alternates():
    import uharfbuzz as hb
    p=DIR/'KilfaneStudy1-Regular.otf';font=hb.Font(hb.Face(p.read_bytes()));hb.ot_font_set_funcs(font)
    def shape(features):
        b=hb.Buffer();b.add_str('ADSTYdfglty');b.guess_segment_properties();hb.shape(font,b,features)
        return [g.codepoint for g in b.glyph_infos]
    default=shape({})
    assert shape({'ss01':True})!=default
    assert shape({'ss02':True})!=default


def test_provenance_preserves_construction_and_updates_sources():
    import json
    p=json.loads((DIR/'KilfaneStudy1-Regular.provenance.json').read_text(encoding='utf-8'))
    assert p['semicolon'][0]=='rebuilt'
    assert 'NIVAL' in p['semicolon'][1]
    for n in ['period','comma','colon','dotlessi','dotlessj','Euro']:
        assert 'flyer' not in p[n][1],(n,p[n])
        assert 'NIVAL' in p[n][1],(n,p[n])
