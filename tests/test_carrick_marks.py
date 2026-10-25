from pathlib import Path
import json,os,unicodedata
import pytest,pathops
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import replayRecording
from test_ceili_punctuation import origin_path,overlap

ROOT=Path(__file__).resolve().parents[1]
DIR=Path(os.environ.get('ROUND05_DIR',ROOT/'research/round-05'))/'carrick'
STEM='CarrickStudy2-Regular'
OLD=ROOT/'research/round-02/carrick/fonts/CarrickStudy1-Regular.otf'

def font_path(ext='otf'):return DIR/'fonts'/f'{STEM}.{ext}'

def test_carrick_named_pieces_have_honest_sources_and_shapes():
    p=DIR/'traces/pieces.json';assert p.exists(),'Carrick named source marks not built'
    data=json.loads(p.read_text(encoding='utf-8'));pieces={r['name']:r for r in data['pieces']}
    assert sum(p['status']=='direct' for p in pieces.values())==10
    assert len(data['unassigned'])==2
    gs=TTFont(font_path()).getGlyphSet()
    for piece,glyph in [('acute','acute'),('dot','dotaccent'),('ring','ring'),('tilde','tilde'),('circumflex','circumflex'),('guil.r1','guilsinglright'),('guil.l1','guilsinglleft')]:
        r=pieces[piece]
        assert r['source_id']=='N513' and r['labels']
        a=origin_path(lambda pen:replayRecording(r['rec'],pen))
        assert overlap(a,origin_path(gs[glyph].draw))>.97,glyph
    for name in ['dieresis.l','dieresis.r']:assert pieces[name]['status']=='retained'
    for name in ['guil.r2','guil.l2']:assert pieces[name]['status']=='derived'
    prov=json.loads((DIR/'fonts'/f'{STEM}.provenance.json').read_text(encoding='utf-8'))
    assert not any('N516' in row[1] for row in prov.values())
    assert 'retained' in prov['dieresis'][1]
    assert 'N513' in prov['acute'][1] and 'derived' in prov['guillemotleft'][1]

@pytest.mark.parametrize('ext',['otf','ttf','woff','woff2'])
def test_carrick_mark_formats(ext):
    import ots
    p=font_path(ext);assert p.exists(),p
    r=ots.sanitize(str(p),os.devnull,capture_output=True);assert r.returncode==0,r.stderr
    f=TTFont(p);assert f.getBestCmap().keys()==TTFont(OLD).getBestCmap().keys()
    assert f['name'].getDebugName(6)==STEM

def test_carrick_marks_preserve_body_and_legacy_diaeresis():
    gs=TTFont(font_path()).getGlyphSet();old=TTFont(OLD).getGlyphSet()
    for name in list('abcdefghijklmnopqrstuvwxyz')+['dieresis']:
        assert overlap(origin_path(gs[name].draw),origin_path(old[name].draw))>.995,name
    from fontTools.pens.recordingPen import RecordingPen
    for name in ['ring','degree']:
        p=RecordingPen();gs[name].draw(p);assert sum(op=='closePath' for op,_ in p.value)==2,name

@pytest.mark.parametrize('ext',['otf','ttf'])
def test_carrick_mark_pair_protection(ext):
    from audit_font_pairs import audit_font_pairs
    chars=''.join(chr(cp) for cp in TTFont(font_path(ext)).getBestCmap()
        if unicodedata.category(chr(cp)).startswith('L') and 'LATIN' in unicodedata.name(chr(cp),''))
    chars+='.,:;!?‘’“”„…«»‹›°()-'
    result=audit_font_pairs(font_path(ext),characters=chars)
    assert result['pairs_tested']>80000 and result['skipped_non_pair_shaping']==0
    assert result['collisions']==0,result['worst']

def test_carrick_marks_decomposed_shaping():
    import uharfbuzz as hb
    from test_shaping import shape_path,WORDS
    p=font_path();f=TTFont(p);blob=hb.Blob.from_file_path(str(p))
    for ch in WORDS.replace(' ',''):
        a,wa=shape_path(blob,f,ch);b,wb=shape_path(blob,f,unicodedata.normalize('NFD',ch))
        assert wa==wb and overlap(a,b)>.93,ch

def test_current_mark_evidence_replaces_legacy_cluster_description():
    ev=json.loads((DIR/'traces/evidence.json').read_text(encoding='utf-8'))
    assert ev.get('marks_evidence')=='pieces.json'
    group=next(g for g in ev['glyphs'] if g['name']=='ornament')
    assert group['status']=='superseded'
    assert not any('marks cluster remain legacy' in s for s in ev['limitations'])

def test_macron_provenance_names_both_weight_sources():
    prov=json.loads((DIR/'fonts'/f'{STEM}.provenance.json').read_text(encoding='utf-8'))
    assert 'mean' in prov['macron'][1] and 'two' in prov['macron'][1]
