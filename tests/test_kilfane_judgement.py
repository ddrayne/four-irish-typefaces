"""Kilfane Study 4, the judgement pass (research/kilfane-judgement), and the tools it uses."""
import json, os
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUND = os.path.join(ROOT, 'research', 'kilfane-judgement')
SEPARATED = {'T', 'U', 'k', 'l'}


def square(x0, y0, x1, y1):
    return [('moveTo', [[x0, y0]]), ('lineTo', [[x1, y0]]), ('lineTo', [[x1, y1]]), ('lineTo', [[x0, y1]]), ('closePath', [])]


def area(rec):
    import fit_production
    import impressions as IM
    m, _ = IM.trace_mask(rec, 0.05, 1.0)
    return float((m > 0.5).sum() * 0.05 * 0.05)


def test_lock_frame_undoes_a_uniform_drift():
    import fit_production
    base = square(10, 10, 30, 40)
    drifted = [(op, [[(x - 20) * 1.02 + 20.3, (y - 25) * 1.02 + 24.8] for x, y in a]) for op, a in base]
    rec, lock = fit_production.lock_frame(drifted, base)
    assert lock['scale'] == pytest.approx(1 / 1.02, abs=0.002)
    pts = np.array([p for _, a in rec for p in a])
    assert pts.min(0) == pytest.approx([10, 10], abs=0.15) and pts.max(0) == pytest.approx([30, 40], abs=0.15)


def test_ease_notch_closes_only_the_narrow_end():
    import judge
    # a block with a wedge cut in from the right: 4 units open at the mouth, closing to nothing at x = 12
    rec = [('moveTo', [[0, 0]]), ('lineTo', [[20, 0]]), ('lineTo', [[20, 8]]), ('lineTo', [[12, 10]]),
           ('lineTo', [[20, 12]]), ('lineTo', [[20, 20]]), ('lineTo', [[0, 20]]), ('closePath', [])]
    out, added = judge.ease_notch(rec, at=(13, 10), radius=0.5, reach=4)
    assert 0 < added < 4                                    # the inner end fills ...
    import impressions as IM
    m, (x0, y0) = IM.trace_mask(out, 0.1, 1.0)
    px = lambda x, y: m[int((y - y0) / 0.1), int((x - x0) / 0.1)] > 0.5
    assert px(12.6, 10) and not px(19.5, 10)               # ... and the mouth stays open
    assert area(out) == pytest.approx(area(rec) + added, abs=0.6)


def test_pinches_find_a_neck_and_ignore_a_taper():
    import pinches
    stem = 100
    neck = [np.array([[0, 0], [300, 0], [300, 200], [0, 200]], float),          # two blocks joined by a 20-unit neck
            np.array([[300, 90], [500, 90], [500, 110], [300, 110]], float)]
    import pathops
    from fontTools.pens.recordingPen import RecordingPen
    dumbbell = [np.array([[0, 0], [200, 0], [200, 90], [300, 90], [300, 0], [500, 0], [500, 200], [300, 200],
                          [300, 110], [200, 110], [200, 200], [0, 200]], float)]
    found = pinches.pinches(dumbbell, stem, ratio=0.33)
    assert found and all(250 <= x <= 300 or 200 <= x <= 300 for x, *_ in found)
    taper = [np.array([[0, 0], [200, 0], [200, 200], [0, 200]], float), ]
    assert not pinches.pinches(taper, stem, ratio=0.33)


@pytest.mark.skipif(not os.path.isdir(ROUND), reason='Study 4 not built')
def test_study4_records_every_correction():
    ev = {g['name']: g for g in json.load(open(os.path.join(ROUND, 'traces', 'evidence.json'), encoding='utf-8'))['glyphs']}
    for n in SEPARATED:
        g = ev[n]
        assert g['status'] == 'candidate' and g['method'] == 'separated' and g['source'] == 'Kilfane-alphabet-specimen.jpg', n
        assert len(g['pair']) == 2 and n in g['pair']
    locked = {n: g['frame_lock'] for n, g in ev.items() if 'frame_lock' in g}
    assert set(locked) == {n for n, g in ev.items() if g.get('source_id') == 'N517'}
    assert all(0.97 <= v['scale'] <= 1.03 for v in locked.values())
    edits = ev['e']['judged_edits']
    assert [e['op'] for e in edits] == ['ease_notch'] and 0 < edits[0]['added_area'] < 2


@pytest.mark.skipif(not os.path.isdir(ROUND), reason='Study 4 not built')
def test_study4_changes_only_what_it_records():
    new = {g['name']: g['rec'] for g in json.load(open(os.path.join(ROUND, 'traces', 'kilfane.json')))['glyphs']}
    s3 = {g['name']: g['rec'] for g in json.load(open(os.path.join(ROOT, 'research', 'kilfane-production', 'traces', 'kilfane.json')))['glyphs']}
    ev = {g['name']: g for g in json.load(open(os.path.join(ROUND, 'traces', 'evidence.json'), encoding='utf-8'))['glyphs']}
    changed = {n for n in new if new[n] != s3[n]}
    recorded = SEPARATED | {'e'} | {n for n, g in ev.items() if 'frame_lock' in g}
    assert changed <= recorded and SEPARATED | {'e'} <= changed


@pytest.mark.skipif(not os.path.isdir(ROUND), reason='Study 4 not built')
@pytest.mark.parametrize('ext', ['otf', 'ttf', 'woff', 'woff2'])
def test_study4_fonts_sanitise_and_keep_the_release_coverage(ext):
    import ots
    from fontTools.ttLib import TTFont
    p = os.path.join(ROUND, 'fonts', f'KilfaneStudy4-Regular.{ext}')
    assert ots.sanitize(p, os.devnull, capture_output=True).returncode == 0
    f = TTFont(p)
    assert f['name'].getDebugName(1) == 'Kilfane Study 4'
    assert f.getBestCmap().keys() == TTFont(os.path.join(ROOT, 'fonts', 'otf', 'KilfaneDigital-Regular.otf')).getBestCmap().keys()
