"""Kilfane Study 5 (research/kilfane-sheet-frame): Study 4 with the production capitals in the sheet's own frame."""
import json, os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUND = os.path.join(ROOT, 'research', 'kilfane-sheet-frame')
STUDY4 = os.path.join(ROOT, 'research', 'kilfane-judgement')


def load(*parts):
    return json.load(open(os.path.join(*parts), encoding='utf-8'))


def evidence(folder):
    return {g['name']: g for g in load(folder, 'traces', 'evidence.json')['glyphs']}


def recs(folder):
    return {g['name']: g['rec'] for g in load(folder, 'traces', 'kilfane.json')['glyphs']}


def test_the_sheet_capitals_carry_their_frame():
    ev = evidence(ROUND)
    sheet = {n for n, g in ev.items() if g.get('source_id') == 'N517'}
    assert sheet == {n for n, g in evidence(STUDY4).items() if g.get('source_id') == 'N517'}
    for n in sheet:
        lock = ev[n]['frame_lock']
        assert 0.96 < lock['scale'] < 1.04, n
        assert set(lock['sheet_frame']) == {'turn_deg', 'stretch_ratio', 'shear_removed_deg'}, n
        assert lock['baseline']['source'] == "the sheet's spacing marks" and abs(lock['baseline']['foot_below_line']) < 1.0, n
    assert abs(ev['L']['frame_lock']['sheet_frame']['shear_removed_deg']) > 3        # N516's lean, taken out


def test_only_the_sheet_capitals_change_from_study_4():
    new, old = recs(ROUND), recs(STUDY4)
    assert set(new) == set(old)
    sheet = {n for n, g in evidence(ROUND).items() if g.get('source_id') == 'N517'}
    assert {n for n in new if new[n] != old[n]} == sheet
    ev = evidence(ROUND)
    assert [e['op'] for e in ev['e']['judged_edits']] == ['ease_notch']
    assert all(ev[n]['method'] == 'separated' for n in ('T', 'U', 'k', 'l'))


@pytest.mark.parametrize('ext', ['otf', 'ttf', 'woff', 'woff2'])
def test_study5_fonts_sanitise_and_keep_the_release_coverage(ext):
    import ots
    from fontTools.ttLib import TTFont
    p = os.path.join(ROUND, 'fonts', f'KilfaneStudy5-Regular.{ext}')
    assert ots.sanitize(p, os.devnull, capture_output=True).returncode == 0
    f = TTFont(p)
    assert f['name'].getDebugName(1) == 'Kilfane Study 5'
    assert f.getBestCmap().keys() == TTFont(os.path.join(ROOT, 'fonts', 'otf', 'KilfaneDigital-Regular.otf')).getBestCmap().keys()
