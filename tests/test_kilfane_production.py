"""Kilfane Study 3: capitals redrawn from the N517 production impressions (research/kilfane-production)."""
import json, os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUND = os.path.join(ROOT, 'research', 'kilfane-production')
REDRAWN = set('ABDEFGHKLMNOPR') | {'A.alt1', 'A.alt2'}


def load(*parts):
    return json.load(open(os.path.join(ROUND, *parts), encoding='utf-8'))


def test_redrawn_entries_record_their_impressions_and_registered_source():
    ev = load('traces', 'evidence.json')
    downloads = json.load(open(os.path.join(ROOT, 'research', 'downloads.json')))
    items = downloads if isinstance(downloads, list) else downloads.get('assets') or downloads.get('downloads')
    registered = {os.path.basename(a['path']): a['sha256'] for a in items}
    assert ev['source_hashes']['Kilfane-Letraset.jpg'] == registered['Kilfane-Letraset.jpg']
    redrawn = {g['name']: g for g in ev['glyphs'] if g.get('source_id') == 'N517'}
    assert set(redrawn) == REDRAWN
    for n, g in redrawn.items():
        assert g['impressions'] >= 3 and len(g['boxes']) == len(g['affine']) == g['impressions'], n
        assert sum(g['rms_to_mean']) / len(g['rms_to_mean']) <= 0.10, n
        assert g['proportion_source'] == 'Kilfane-alphabet-specimen.jpg', n
    assert 'Q' in ev['production_impressions']['base_kept_for_topology']


def test_only_the_redrawn_traces_differ_from_round_two():
    new = {g['name']: g for g in load('traces', 'kilfane.json')['glyphs']}
    old = {g['name']: g for g in json.load(open(os.path.join(ROOT, 'research', 'round-02', 'kilfane', 'traces', 'kilfane.json')))['glyphs']}
    assert set(new) == set(old)
    assert {n for n in new if new[n]['rec'] != old[n]['rec']} == REDRAWN


def test_redrawn_capitals_keep_their_topology():
    import fit_production
    new = {g['name']: g for g in load('traces', 'kilfane.json')['glyphs']}
    old = {g['name']: g for g in json.load(open(os.path.join(ROOT, 'research', 'round-02', 'kilfane', 'traces', 'kilfane.json')))['glyphs']}
    for n in REDRAWN:
        assert fit_production.topology(new[n]['rec']) == fit_production.topology(old[n]['rec']), n


def test_study_three_font_is_separately_named():
    from fontTools.ttLib import TTFont
    font = TTFont(os.path.join(ROUND, 'fonts', 'KilfaneStudy3-Regular.otf'))
    assert font['name'].getDebugName(1) == 'Kilfane Study 3'
    assert font['head'].fontRevision == pytest.approx(2.003, abs=1e-3)
