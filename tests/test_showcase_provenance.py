"""The showcase's provenance map: every glyph of each released Regular is covered, in exactly one class,
and what is shown is what the research files say."""
import json, os, sys
import pytest
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import showcase_provenance as sp       # noqa: E402
from build2 import FONTS               # noqa: E402

FACES = ['ceili', 'carrick', 'kilfane', 'tuam']


@pytest.fixture(scope='module')
def faces():
    cat, files = sp.catalogue()
    studies = sp.latest()
    return {k: sp.face_data(k, studies[k], cat, files) for k in FACES}


@pytest.mark.parametrize('face', FACES)
def test_every_glyph_once_in_one_class(faces, face):
    data = faces[face]
    order = TTFont(os.path.join(ROOT, 'fonts', 'otf', f'{FONTS[face]["ps"]}-Regular.otf')).getGlyphOrder()
    assert [g['n'] for g in data['glyphs']] == order
    assert all(g['c'] in ('a', 'r', 'm') for g in data['glyphs'])
    assert sum(data['counts'].values()) == len(order)
    assert data['counts'] == {c: sum(g['c'] == c for g in data['glyphs']) for c in 'arm'}


@pytest.mark.parametrize('face', FACES)
def test_classes_follow_the_build_record(faces, face):
    data = faces[face]
    record = json.load(open(os.path.join(ROOT, data['files']['record']), encoding='utf-8'))
    by = {g['n']: g for g in data['glyphs']}
    for name, g in by.items():
        if name not in record:                       # the release added it: never claimed as traced, and said to be unrecorded
            assert g['c'] != 'a' and g['how'] is None
            continue
        kind = record[name][0]
        assert (g['c'] == 'a') == (kind in sp.TRACED_KINDS), name
        if kind == 'composite':
            assert g['c'] == 'r', name
        if g['c'] == 'a':                            # a tracing names its print, or says the basis is not recorded
            assert g.get('basis') is None or g['src'], name
    assert by['space']['c'] == 'm' and by['plus']['c'] == 'm' and by['ae']['c'] == 'r' and by['a']['c'] == 'a'


@pytest.mark.parametrize('face', FACES)
def test_sources_and_corrections_are_the_files_own(faces, face):
    data = faces[face]
    known = {s['id'] for s in data['sources']}
    edits = open(os.path.join(ROOT, data['files']['edits']), encoding='utf-8').read()
    reasons = json.dumps(json.loads(edits), ensure_ascii=False)
    for r in data['rules']:
        assert r['reason'] and json.dumps(r['reason'], ensure_ascii=False)[1:-1] in reasons
    for g in data['glyphs']:
        assert set(g.get('src', [])) <= known
        for i, _, _ in g.get('rules', []):
            assert 0 <= i < len(data['rules'])
    for s in data['sources']:                        # links to catalogue records, never to an image file
        assert s['url'] and not s['url'].lower().endswith(('.jpg', '.jp2', '.png'))


def test_evidence_numbers(faces):
    k = {g['n']: g for g in faces['kilfane']['glyphs']}
    assert k['L']['basis'] == 'sheet' and k['L']['src'] == ['N517', 'N516']
    assert ['Outline', 'mean of 12 impressions on the 30pt S53909 Letraset sheet (N517)'] in k['L']['facts']
    assert k['T']['basis'] == 'one' and k['hyphen.case']['of'] == 'hyphen'
    t = {g['n']: g for g in faces['tuam']['glyphs']}
    assert t['h']['basis'] == 'two' and t['h']['dis'] and t['h']['src'] == ['N46', 'N45']
    assert {g['basis'] for g in faces['ceili']['glyphs'] if g['c'] == 'a'} == {'two'}
