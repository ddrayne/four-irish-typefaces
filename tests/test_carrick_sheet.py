"""Carrick Study 3 (research/round-06): fifteen letters from the N514 production sheets, x and y from N513."""
import json, os
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUND = os.environ.get('ROUND06_DIR', os.path.join(ROOT, 'research', 'round-06'))
BASE = os.path.join(ROOT, 'research', 'round-05', 'carrick', 'traces')
REDRAWN = set('bcdefghijklmno')


def load(*parts):
    return json.load(open(os.path.join(*parts), encoding='utf-8'))


def traces(folder):
    return {g['name']: g for g in load(folder, 'carrick.json')['glyphs']}


def test_topology_counts_counters_not_the_outside():
    import trace_production as T
    ring = np.zeros((40, 40), bool); ring[5:35, 5:35] = True; ring[15:25, 15:25] = False
    bar = np.zeros((40, 40), bool); bar[10:30, 5:35] = True
    assert T.topology_of(ring) == [1, 1] and T.topology_of(bar) == [1, 0]
    speckled = bar.copy(); speckled[18:20, 18:20] = False                # light speckle in the ink
    assert T.topology_of(speckled) == [1, 0]


def test_the_most_open_shown_topology_wins():
    import fit_production as F
    tops = [[1, 1]] * 10 + [[1, 0]] * 4                                   # a: open in 4 of 14
    ok = F.shown(tops)
    assert (1, 0) in ok and max(ok, key=lambda t: (t[0] - t[1], t[0])) == (1, 0)
    assert F.shown([[2, 0]] * 9 + [[3, 0]]) == [(2, 0)]                  # one in ten is not shown


def test_c1_records_the_registered_source_and_accepts_e_and_f():
    ev = load(ROOT, 'research', 'carrick-ef', 'evidence.json')
    downloads = load(ROOT, 'research', 'downloads.json')
    registered = {os.path.basename(a['path']): a['sha256'] for a in downloads['assets']}
    assert ev['sha256'] == registered['Carrick-Letraset.jpg']
    assert {n: d['decision'] for n, d in ev['decisions'].items()} == {'e': 'accept', 'f': 'accept'}
    for tag, o in ev['observations'].items():
        assert o['impressions'] == len(o['boxes']) == len(o['affine']) == len(o['impression_topology']) >= 3, tag


def test_redrawn_letters_name_their_sheet_and_keep_the_frame():
    ev = {g['name']: g for g in load(ROUND, 'carrick', 'traces', 'evidence.json')['glyphs']}
    redrawn = {n for n, g in ev.items() if g.get('source_id') == 'N514'}
    assert redrawn == REDRAWN
    for n in REDRAWN:
        g = ev[n]
        assert g['impressions'] >= 3 and g['sheet'] in ('60pt S53914', '36pt S53913'), n
        assert 0.97 <= g['frame_lock']['scale'] <= 1.03, n
    assert ev['e']['proportion_source'].startswith('the flyer trace')
    assert ev['x']['method'] == ev['y']['method'] == 'separated' and ev['x']['source'] == 'Carrick-alphabet-specimen.jpg'


def test_topologies_follow_the_impressions():
    import fit_production as F
    new = traces(os.path.join(ROUND, 'carrick', 'traces'))
    want = {'a': (1, 0), 'b': (1, 1), 'e': (2, 0), 'f': (1, 0), 'j': (3, 0), 'm': (3, 0), 'o': (1, 1)}
    assert {n: F.topology(new[n]['rec']) for n in want} == want


def test_only_the_recorded_letters_change():
    new, old = traces(os.path.join(ROUND, 'carrick', 'traces')), traces(BASE)
    assert set(new) == set(old)
    assert {n for n in new if new[n]['rec'] != old[n]['rec']} == REDRAWN | {'x', 'y'}


@pytest.mark.parametrize('ext', ['otf', 'ttf', 'woff', 'woff2'])
def test_study3_fonts_sanitise_and_keep_the_release_coverage(ext):
    import ots
    from fontTools.ttLib import TTFont
    p = os.path.join(ROUND, 'carrick', 'fonts', f'CarrickStudy3-Regular.{ext}')
    assert ots.sanitize(p, os.devnull, capture_output=True).returncode == 0
    f = TTFont(p)
    assert f['name'].getDebugName(1) == 'Carrick Study 3'
    assert f.getBestCmap().keys() == TTFont(os.path.join(ROOT, 'fonts', 'otf', 'CarrickDigital-Regular.otf')).getBestCmap().keys()
