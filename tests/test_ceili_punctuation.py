from pathlib import Path
import json,os
import pytest,pathops
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import replayRecording
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from test_shaping import area

ROOT=Path(__file__).resolve().parents[1]
DIR=Path(os.environ.get('ROUND04_DIR',ROOT/'research/round-04'))
STEM='CeiliStudy3-Regular'

def font_path(ext='otf'):return DIR/'ceili/fonts'/f'{STEM}.{ext}'

def origin_path(draw):
    b=BoundsPen(None);draw(b)
    p=pathops.Path();draw(TransformPen(p.getPen(),(1,0,0,1,-b.bounds[0],-b.bounds[1])))
    return p

def overlap(a,b):
    return area(pathops.op(a,b,pathops.PathOp.INTERSECTION,fix_winding=True))/area(pathops.op(a,b,pathops.PathOp.UNION,fix_winding=True))

def test_named_original_parts_replace_drawn_comma_and_legacy_dot():
    p=DIR/'ceili/traces/punctuation.json'
    assert p.exists(),'named original punctuation has not been reconstructed'
    data=json.loads(p.read_text(encoding='utf-8'))
    pieces={p['name']:p for p in data['pieces']}
    assert set(pieces)=={'period','comma','quoteleft','quoteright'}
    assert data['source_hashes']['competition-brochure-2.jpg']=='57d14ab343c5942345f14f277be8e92a6182f4b1a6a90a1d9ae413563b26ef18'
    gs=TTFont(font_path()).getGlyphSet()
    for name,piece in pieces.items():
        a=origin_path(lambda pen:replayRecording(piece['rec'],pen))
        b=origin_path(gs[name].draw)
        assert overlap(a,b)>.98,name
    prov=json.loads((DIR/'ceili/fonts'/f'{STEM}.provenance.json').read_text(encoding='utf-8'))
    for name in ['period','comma','colon','semicolon','ellipsis','quoteleft','quoteright','quotedblleft','quotedblright']:
        assert 'N45' in prov[name][1],(name,prov[name])
        assert 'drawn tail' not in prov[name][1]
    assert 'N45' in prov['uni0326'][1]
    assert 'quoteright' in prov['dcaron'][1]

@pytest.mark.parametrize('ext',['otf','ttf','woff','woff2'])
def test_ceili_punctuation_formats(ext):
    import ots
    p=font_path(ext);assert p.exists(),p
    result=ots.sanitize(str(p),os.devnull,capture_output=True)
    assert result.returncode==0,result.stderr
    f=TTFont(p);old=TTFont(ROOT/'research/round-03/ceili/fonts/CeiliStudy2-Regular.otf')
    assert f.getBestCmap().keys()==old.getBestCmap().keys()
    assert f['name'].getDebugName(6)==STEM

def test_punctuation_pass_preserves_original_letter_bodies():
    gs=TTFont(font_path()).getGlyphSet()
    old=TTFont(ROOT/'research/round-03/ceili/fonts/CeiliStudy2-Regular.otf').getGlyphSet()
    # Accented alternates inherit the newly sourced period/comma as marks.
    names=list('abcdefghijklmnopqrstuvwxyz')+[n for n in old if '.alt' in n and len(n.split('.')[0])==1]
    for name in names:
        assert overlap(origin_path(gs[name].draw),origin_path(old[name].draw))>.995,name

@pytest.mark.parametrize('ext',['otf','ttf'])
def test_punctuation_pass_collision_protection(ext):
    from audit_font_pairs import audit_font_pairs
    import unicodedata
    chars=''.join(chr(cp) for cp in TTFont(font_path(ext)).getBestCmap()
        if unicodedata.category(chr(cp)).startswith('L') and 'LATIN' in unicodedata.name(chr(cp),''))
    chars+='.,:;!?\u2018\u2019\u201c\u201d\u201a\u201e\u2026\"\'()-'
    result=audit_font_pairs(font_path(ext),characters=chars)
    assert result['pairs_tested']>78000 and result['skipped_non_pair_shaping']==0
    assert result['collisions']==0,result['worst']

def test_punctuation_pass_decomposed_marks():
    import unicodedata,uharfbuzz as hb
    from test_shaping import shape_path
    p=font_path();font=TTFont(p);blob=hb.Blob.from_file_path(str(p))
    for ch in 'áéíóúḃċḋḟġṁṗṡṫșț':
        a,wa=shape_path(blob,font,ch);b,wb=shape_path(blob,font,unicodedata.normalize('NFD',ch))
        assert wa==wb and overlap(a,b)>.93,ch
