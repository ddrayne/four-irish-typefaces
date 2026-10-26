"""Kilfane Study 5 (research/kilfane-sheet-frame): Study 4 with the production capitals in the sheet's own frame."""
import json, os
import pytest
from conftest import study_coverage

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
    assert set(f.getBestCmap()) == study_coverage(TTFont(os.path.join(ROOT, 'fonts', 'otf', 'KilfaneDigital-Regular.otf')))


# ---------------------------------------------------------------- the studio finishing of the release build
def rect(x0, y0, x1, y1):
    import pathops
    p = pathops.Path(); p.moveTo(x0, y0); p.lineTo(x1, y0); p.lineTo(x1, y1); p.lineTo(x0, y1); p.close()
    return p


def test_heights_scale_a_letter_onto_its_line_and_keep_its_tangents():
    import kilfane_studio as KS
    c = KS.segments(rect(0, -150, 100, 490))
    out, rep = KS.align_heights(c, [{'band': [0, 1], 'line': 'x'}], {'x': 506})
    ys = [p[1][-1][1] for p in out[0]]
    assert max(ys) == pytest.approx(506) and min(ys) == pytest.approx(-150)      # the descender stays as drawn
    f = KS.YMap([(0, 0), (500, 513), (692, 692)])                                 # a shoulder raised, the ascender kept
    assert f(500) == pytest.approx(513) and f(692) == pytest.approx(692) and f(-10) == pytest.approx(-10 * 513 / 500)


def test_stems_move_both_edges_by_at_most_the_limit():
    import kilfane_studio as KS
    c = KS.segments(rect(100, 0, 208, 500))
    out, rep = KS.harmonise_stems(c, [[0.5, 0]], 506, 114, 3)
    a, b = KS.stem(out, 253, 0)
    assert (a, b) == pytest.approx((97, 211))
    out, rep = KS.harmonise_stems(KS.segments(rect(100, 0, 220, 500)), [[0.5, 0]], 506, 114, 2)
    assert KS.stem(out, 253, 0)[1] - KS.stem(out, 253, 0)[0] == pytest.approx(116)


def test_outline_finishing_merges_a_chain_and_keeps_the_shape():
    import pathops, kilfane_studio as KS
    p = pathops.Path(); p.moveTo(0, 0)
    for x in range(10, 401, 10):                      # a straight bottom drawn as forty pieces
        p.lineTo(x, 0)
    p.lineTo(400, 300); p.lineTo(0, 300); p.close()
    q = KS.finish_glyph(p)
    assert len(KS.segments(q)[0]) == 4
    assert KS._area(q) == pytest.approx(KS._area(p))
    s = pathops.Path(); s.moveTo(0, 0); s.quadTo(50, 100, 100, 0); s.close()   # pathops' offsets draw quadratics
    assert [k for k, _ in KS.segments(s)[0]] == ['C', 'L']


def _kilfane(style='Regular'):
    from conftest import static
    from fontTools.ttLib import TTFont
    return TTFont(static('KilfaneDigital', style))


def test_release_stems_and_lines_are_harmonised():
    """The finishing pass's stems and heights are in the released Regular (fonts/, or FONTDIR)."""
    import kilfane_studio as KS, pathops
    spec = KS.load(); lines = spec['lines']; f = _kilfane(); gs = f.getGlyphSet()
    path = lambda n: (lambda p: (gs[n].draw(p.getPen()), p)[1])(pathops.Path())
    for group in spec['stems'].values():
        h = lines[group['height']]
        for n, st in group['glyphs'].items():
            for frac, run in st:
                a, b = KS.stem(KS.segments(path(n)), frac * h, run)
                assert abs(b - a - group['target']) <= 2 * group['limit'] + 1, (n, frac, run, b - a)
    lc = [b - a for n in 'hilmnu' for a, b in [KS.stem(KS.segments(path(n)), 253, 0)]]
    assert max(lc) - min(lc) <= 2
    polys = lambda n: KS.polygons(KS.segments(path(n)))
    for n, band, line in (('n', [0, 0.25], 'x'), ('i', [0, 1], 'x'), ('m', [0, 0.2], 'x'), ('u', [0.7, 1], 'x'),
                          ('l', [0, 0.5], 'asc'), ('h', [0, 0.3], 'asc'), ('H', [0, 0.3], 'cap'), ('I', [0, 1], 'cap'),
                          ('F', [0.6, 1], 'cap'), ('c', [0.3, 0.7], 'xo'), ('C', [0.3, 0.7], 'capo')):
        assert KS.feature(polys(n), band, below=560 if n == 'i' else None) == pytest.approx(lines[line], abs=1.5), n
    assert f['OS/2'].sxHeight == lines['x'] and f['OS/2'].sCapHeight == lines['cap']


@pytest.mark.parametrize('style', ['Regular', 'Italic', 'Bold', 'Bold Italic'])
def test_release_outlines_are_economical(style):
    """Every style's letters after finishing: few nodes, and a node at each extreme."""
    import kilfane_studio as KS, pathops
    import curvefit as CF
    import numpy as np
    f = _kilfane(style); gs = f.getGlyphSet(); counts = []
    for n in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ':
        p = pathops.Path(); gs[n].draw(p.getPen()); c = KS.segments(p)
        counts.append(sum(len(s) for s in c))
        for segs in c:
            for i, (k, pts) in enumerate(segs):
                if k == 'C':
                    q = np.array([KS.FN._start(segs, i)] + pts, float)
                    for ax in (0, 1):
                        for t in CF._extrema_t(q, ax):
                            v = CF._bez(q, [t])[0][ax]
                            assert not (0.1 < t < 0.9 and min(abs(v - q[0][ax]), abs(v - q[3][ax])) > 1.5), (style, n)
    assert np.mean(counts) <= {'Regular': 22, 'Italic': 28, 'Bold': 29, 'Bold Italic': 33}[style]


def test_release_kerning_eases_quotes_and_closes_wide_pairs():
    import uharfbuzz as hb
    from conftest import static
    path = static('KilfaneDigital', 'Regular')
    font = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
    def kern(s):
        x = []
        for k in (True, False):
            b = hb.Buffer(); b.add_str(s); b.guess_segment_properties(); hb.shape(font, b, {'kern': k})
            x.append(b.glyph_positions[0].x_advance)
        return x[0] - x[1]
    assert kern('’a') >= -40 and kern('‘m') >= -40 and kern('c-') >= -30
    assert kern('Va') <= -20 and kern('Fi') <= -20 and kern('le') < 0 and kern('nn') == 0
