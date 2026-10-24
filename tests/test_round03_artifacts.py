from pathlib import Path
import json,os
import pytest
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

ROOT=Path(__file__).resolve().parents[1]
DIR=Path(os.environ.get('ROUND03_DIR',ROOT/'research/round-03'))
FACES=[('tuam','TuamUncialStudy2','TuamUncial'),('ceili','CeiliStudy2','Ceili')]

@pytest.mark.parametrize('face,ps,old',FACES)
def test_outline_studies_have_explicit_original_evidence(face,ps,old):
    p=DIR/face/'traces/evidence.json'
    assert p.exists(),'the original-source outline study has not been built'
    data=json.loads(p.read_text(encoding='utf-8'))
    revised=[g for g in data['glyphs'] if g['status']=='candidate']
    assert len(revised)>=40
    for g in revised:
        assert g['source'] in data['source_hashes']
        assert len(data['source_hashes'][g['source']])==64
        assert g['labels'] and g['scale']>0 and len(g['box'])==4

@pytest.mark.parametrize('face,ps,old',FACES)
@pytest.mark.parametrize('ext',['otf','ttf','woff','woff2'])
def test_round03_formats_sanitize_and_preserve_coverage(face,ps,old,ext):
    import ots
    p=DIR/face/f'fonts/{ps}-Regular.{ext}'
    assert p.exists(),p
    result=ots.sanitize(str(p),os.devnull,capture_output=True)
    assert result.returncode==0,result.stderr
    f=TTFont(p);baseline=TTFont(ROOT/f'fonts/otf/{old}-Regular.otf')
    assert f.getBestCmap().keys()==baseline.getBestCmap().keys()
    assert f['name'].getDebugName(6)==ps+'-Regular'

@pytest.mark.parametrize('face,ps,old',FACES)
@pytest.mark.parametrize('ext',['otf','ttf'])
def test_round03_all_latin_pairs(face,ps,old,ext):
    from audit_font_pairs import audit_font_pairs
    result=audit_font_pairs(DIR/face/f'fonts/{ps}-Regular.{ext}')
    assert result['pairs_tested']>70000 and result['skipped_non_pair_shaping']==0
    assert result['collisions']==0,result['worst']

def test_ceili_new_source_closes_eyes_and_preserves_alternates():
    f=TTFont(DIR/'ceili/fonts/CeiliStudy2-Regular.otf');gs=f.getGlyphSet()
    for name in ['e','e.alt1','a','o','q']:
        pen=RecordingPen();gs[name].draw(pen)
        assert sum(op=='closePath' for op,_ in pen.value)>=2,name
    # b's upper and p's lower bowls deliberately stop short of their stems.
    for name in ['b','p']:
        pen=RecordingPen();gs[name].draw(pen)
        assert sum(op=='closePath' for op,_ in pen.value)==1,name
    for tag in ['ss01','ss02','ss03']:
        from audit_font_pairs import audit_font_pairs
        result=audit_font_pairs(DIR/'ceili/fonts/CeiliStudy2-Regular.otf',characters='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',features={tag:True})
        assert result['collisions']==0,(tag,result['worst'])

def test_ceili_h_uses_brochure_instead_of_borrowed_n_leg():
    p=DIR/'ceili/fonts/CeiliStudy2-Regular.provenance.json'
    data=json.loads(p.read_text(encoding='utf-8'))
    assert 'competition-brochure-2.jpg' in data['h'][1]
    assert 'from n' not in data['h'][1]
    for name in ['b','e','e.alt1']:
        assert 'restored' not in data[name][1]
        assert 'minimum' not in data[name][1]

def test_tuam_accent_provenance_separates_base_and_mark():
    data=json.loads((DIR/'tuam/fonts/TuamUncialStudy2-Regular.provenance.json').read_text(encoding='utf-8'))
    assert 'uacute' in data['acute'][1]
    assert 'base source a:' in data['aacute'][1]
    assert 'base source aacute:' not in data['aacute'][1]

def test_source_dot_and_numeral_openings_survive_final_binary():
    checks=[('ceili','CeiliStudy2','exclam',2),('tuam','TuamUncialStudy2','eight',2),
            ('tuam','TuamUncialStudy2','nine',1),('tuam','TuamUncialStudy2','zero',1)]
    for face,ps,name,count in checks:
        for ext in ['otf','ttf']:
            f=TTFont(DIR/face/f'fonts/{ps}-Regular.{ext}');pen=RecordingPen()
            f.getGlyphSet()[name].draw(pen)
            assert sum(op=='closePath' for op,_ in pen.value)==count,(face,name,ext)

@pytest.mark.parametrize('face,ps,old',FACES)
def test_round03_decomposed_accents(face,ps,old):
    import unicodedata,pathops,uharfbuzz as hb
    from test_shaping import shape_path,area,WORDS
    p=DIR/face/f'fonts/{ps}-Regular.otf';f=TTFont(p);blob=hb.Blob.from_file_path(str(p));cm=f.getBestCmap()
    for ch in WORDS.replace(' ',''):
        decomp=unicodedata.normalize('NFD',ch)
        if ord(ch) not in cm or not all(ord(c) in cm for c in decomp):continue
        a,wa=shape_path(blob,f,ch);b,wb=shape_path(blob,f,decomp)
        assert wa==wb,ch
        overlap=pathops.op(a,b,pathops.PathOp.INTERSECTION,fix_winding=True)
        union=pathops.op(a,b,pathops.PathOp.UNION,fix_winding=True)
        assert area(overlap)/area(union)>.93,ch
