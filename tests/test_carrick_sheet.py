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


def test_sheet_frame_removes_the_shared_slant_and_keeps_each_fit():
    import impressions as IM
    # every impression carries the base print's shear and stretch, the photograph's own twist (here 2
    # degrees, as its mark lines show) and a little local wobble of its own
    shared = np.array([[1.0, 0.06], [0.0, 1.04]])
    mark = np.radians(2.0)
    qs, wobble = [], [np.radians(w) for w in (-0.3, 0.1, 0.4)]
    for i, w in enumerate(wobble):
        L = 2.6 * IM.rotation(mark + w) @ shared
        qs.append(np.r_[L[0], L[1], 100.0 * i, 50.0])
    G, removed = IM.sheet_frame(qs, [mark] * 3)
    centre = np.array([10.0, 20.0])
    out = [IM.compose(q, G, centre) for q in qs]
    for q, w in zip(out, wobble):
        L = np.array([[q[0], q[1]], [q[2], q[3]]]) / np.sqrt(abs(np.linalg.det([[q[0], q[1]], [q[2], q[3]]])))
        R = IM.rotation(mark + w - float(np.median(wobble)))        # square to the marks, each fit's own wobble kept
        assert np.allclose(L, R, atol=0.03)
    assert removed['stretch_ratio'] > 1.03 and abs(removed['shear_removed_deg']) > 2
    a, b, c, d, tx, ty = qs[0]; e = out[0]
    assert np.allclose(np.array([[a, b], [c, d]]) @ centre + [tx, ty], np.array([[e[0], e[1]], [e[2], e[3]]]) @ centre + e[4:])


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
