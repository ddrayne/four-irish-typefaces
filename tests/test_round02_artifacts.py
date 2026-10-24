from pathlib import Path
import json,os
import pytest
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

ROOT=Path(__file__).resolve().parents[1]
DIR=Path(os.environ.get('ROUND02_DIR',ROOT/'research/round-02'))
FACES=[('kilfane','KilfaneStudy2','Kilfane'),('carrick','CarrickStudy1','Carrick'),
       ('tuam','TuamUncialStudy1','TuamUncial'),('ceili','CeiliStudy1','Ceili')]


def test_kilfane_named_marks_preserve_counters_and_uncertainty():
    p=DIR/'kilfane/traces/pieces.json'
    assert p.exists(),'named original-source marks have not been reconstructed'
    data=json.loads(p.read_text(encoding='utf-8'))
    pieces={p['name']:p for p in data['pieces']}
    assert len(pieces)==14
    assert 'caron' not in pieces
    assert len(data['unassigned'])==2
    for name in ['ring','ring.b']:
        assert sum(op=='closePath' for op,_ in pieces[name]['rec'])==2
    assert pieces['dieresis.l']['box']!=pieces['dieresis.r']['box']


@pytest.mark.parametrize('ext',['otf','ttf','woff','woff2'])
def test_kilfane_second_candidate_formats(ext):
    import ots
    p=DIR/f'kilfane/fonts/KilfaneStudy2-Regular.{ext}'
    assert p.exists(),'second candidate is missing'
    assert ots.sanitize(str(p),os.devnull,capture_output=True).returncode==0
    f=TTFont(p)
    assert f['name'].getDebugName(1)=='Kilfane Study 2'
    baseline=TTFont(ROOT/'fonts/otf/Kilfane-Regular.otf')
    assert f.getBestCmap().keys()==baseline.getBestCmap().keys()
    gs=f.getGlyphSet()
    for name,count in [('dieresis',2),('ring',2),('caron',1)]:
        rec=RecordingPen();gs[name].draw(rec)
        assert sum(op=='closePath' for op,_ in rec.value)==count,name


def test_caron_provenance_does_not_claim_ambiguous_source():
    p=DIR/'kilfane/fonts/KilfaneStudy2-Regular.provenance.json'
    assert p.exists(),'second candidate provenance is missing'
    data=json.loads(p.read_text(encoding='utf-8'))
    assert 'made from' in data['caron'][1]
    assert 'circumflex' in data['caron'][1]
    assert 'NIVAL' in data['aacute'][1]
    assert 'marks' in data['aacute'][1]


def test_constructed_mark_provenance_identifies_actual_dependencies():
    data=json.loads((DIR/'kilfane/fonts/KilfaneStudy2-Regular.provenance.json').read_text(encoding='utf-8'))
    for name in ['ogonek','cedilla']:
        assert 'modern drawn' in data[name][1],data[name]
        assert 'named components' not in data[name][1],data[name]
    assert 'constructed' in data['macron'][1],data['macron']
    assert 'endash' in data['macron'][1],data['macron']
    assert 'sheet’s own macron' not in data['macron'][1]
    assert 'semicolon' in data['uni0326'][1],data['uni0326']


def test_carrick_euro_provenance_follows_lowercase_source():
    data=json.loads((DIR/'carrick/fonts/CarrickStudy1-Regular.provenance.json').read_text(encoding='utf-8'))
    assert 'base source c: NIVAL' in data['Euro'][1]
    assert 'flyer' not in data['Euro'][1]


def test_carrick_reconstructs_supported_entries_and_keeps_detached_strokes():
    p=DIR/'carrick/traces/evidence.json'
    assert p.exists(),'Carrick source reconstruction is missing'
    data=json.loads(p.read_text(encoding='utf-8'))
    assert sum(g['status']=='candidate' for g in data['glyphs'])==40
    assert {g['name'] for g in data['glyphs'] if g['status']=='retained'}=={'e','f','x','y','ornament'}
    f=TTFont(DIR/'carrick/fonts/CarrickStudy1-Regular.otf')
    assert f['name'].getDebugName(1)=='Carrick Study 1'
    baseline=TTFont(ROOT/'fonts/otf/Carrick-Regular.otf')
    assert f.getBestCmap().keys()==baseline.getBestCmap().keys()
    for name in ['c','k','u','v','w']:
        rec=RecordingPen();f.getGlyphSet()[name].draw(rec)
        assert sum(op=='closePath' for op,_ in rec.value)>=2,name


@pytest.mark.parametrize('face,ps,baseline',FACES)
@pytest.mark.parametrize('ext',['otf','ttf','woff','woff2'])
def test_all_round02_formats_sanitize_and_keep_coverage(face,ps,baseline,ext):
    import ots
    p=DIR/f'{face}/fonts/{ps}-Regular.{ext}'
    assert p.exists(),p
    result=ots.sanitize(str(p),os.devnull,capture_output=True)
    assert result.returncode==0,result.stderr
    f=TTFont(p);old=TTFont(ROOT/f'fonts/otf/{baseline}-Regular.otf')
    assert f['name'].getDebugName(6)==ps+'-Regular'
    assert f.getBestCmap().keys()==old.getBestCmap().keys()


@pytest.mark.parametrize('face,ps,baseline',FACES)
@pytest.mark.parametrize('ext',['otf','ttf'])
def test_all_mapped_latin_pairs_have_no_ink_collisions(face,ps,baseline,ext):
    from audit_font_pairs import audit_font_pairs
    report=audit_font_pairs(DIR/f'{face}/fonts/{ps}-Regular.{ext}')
    assert report['skipped_non_pair_shaping']==0
    assert report['pairs_tested']>70000
    assert report['collisions']==0,report['worst']


@pytest.mark.parametrize('face,ps,baseline',FACES)
def test_round02_decomposed_accents_match_precomposed(face,ps,baseline):
    import unicodedata,pathops,uharfbuzz as hb
    from test_shaping import shape_path,area,WORDS
    p=DIR/f'{face}/fonts/{ps}-Regular.otf';font=TTFont(p);blob=hb.Blob.from_file_path(str(p));cm=font.getBestCmap()
    for ch in WORDS.replace(' ',''):
        decomposed=unicodedata.normalize('NFD',ch)
        if ord(ch) not in cm or not all(ord(c) in cm for c in decomposed):continue
        a,wa=shape_path(blob,font,ch);b,wb=shape_path(blob,font,decomposed)
        assert wa==wb,ch
        overlap=pathops.op(a,b,pathops.PathOp.INTERSECTION,fix_winding=True)
        union=pathops.op(a,b,pathops.PathOp.UNION,fix_winding=True)
        assert area(overlap)/area(union)>.93,ch


@pytest.mark.parametrize('face,ps,baseline',FACES)
def test_spacing_only_faces_keep_existing_outlines(face,ps,baseline):
    if face not in ['tuam','ceili']:return
    old=TTFont(ROOT/f'fonts/otf/{baseline}-Regular.otf').getGlyphSet()
    new=TTFont(DIR/f'{face}/fonts/{ps}-Regular.otf').getGlyphSet()
    for name in old.keys():
        a=RecordingPen();b=RecordingPen();old[name].draw(a);new[name].draw(b)
        assert a.value==b.value,name


@pytest.mark.parametrize('face,ps,sets',[('kilfane','KilfaneStudy2',['ss01','ss02']),('ceili','CeiliStudy1',['ss01','ss02','ss03'])])
def test_alternate_letter_pairs_remain_collision_free(face,ps,sets):
    from audit_font_pairs import audit_font_pairs
    for tag in sets:
        report=audit_font_pairs(DIR/f'{face}/fonts/{ps}-Regular.otf',characters='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',features={tag:True})
        assert report['collisions']==0,(tag,report['worst'])
