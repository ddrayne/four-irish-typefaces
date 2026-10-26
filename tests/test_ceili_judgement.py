"""Céilí Study 4, the judgement pass (research/ceili-judgement), and the tools it uses."""
import json, os
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUND = os.environ.get('CEILI_JUDGEMENT_DIR', os.path.join(ROOT, 'research', 'ceili-judgement'))
built = pytest.mark.skipif(not os.path.isdir(os.path.join(ROUND, 'traces')), reason='Study 4 not built')


def load(*parts):
    return json.load(open(os.path.join(*parts), encoding='utf-8'))


def blob(shape=(80, 80)):
    """A test letter: a thick ring with a bar, so scale and rotation are both determined."""
    yy, xx = np.mgrid[:shape[0], :shape[1]]
    r = np.hypot(yy - 40, xx - 38)
    m = ((r > 14) & (r < 24)) | ((abs(yy - 40) < 3) & (xx > 38) & (xx < 70))
    return m.astype(float)


def test_similarity_registration_recovers_scale_rotation_and_shift():
    import ceili_prints as CP
    import impressions as IM
    from scipy import ndimage as ndi
    T = blob()
    origin, step = (0.0, 0.0), 1.0
    # the "print": the template laid down at scale 1.6, rotated 2 degrees, shifted
    a = 1.6 * np.cos(np.radians(2)); b = 1.6 * np.sin(np.radians(2))
    q_true = np.array([a, -b, b, a, 30.0, 12.0])
    sheet = np.zeros((200, 200))
    M = np.linalg.inv(np.vstack([IM.affine_matrix(q_true), [0, 0, 1]]))
    yy, xx = np.mgrid[:200, :200]
    u = M[0, 0] * (xx + 0.5) + M[0, 1] * (yy + 0.5) + M[0, 2]; v = M[1, 0] * (xx + 0.5) + M[1, 1] * (yy + 0.5) + M[1, 2]
    sheet = ndi.map_coordinates(T, [v - 0.5, u - 0.5], order=1, cval=0.0)
    q0 = [1.55, 0, 0, 1.55, 33.0, 10.0]
    q, rms = CP.register(sheet, T, origin, step, q0, blur=1.0, reach=4)
    d = CP.decompose(q)
    assert d['aspect'] == 1.0 and d['shear'] == 0.0                  # never a stretch or a shear
    assert d['scale_x'] == pytest.approx(1.6, abs=0.01) and d['rotation_deg'] == pytest.approx(2, abs=0.3)
    assert q[4] == pytest.approx(30, abs=0.4) and q[5] == pytest.approx(12, abs=0.4)


def test_stem_width_ignores_hairlines():
    import ceili_prints as CP
    m = np.zeros((100, 60), bool)
    m[10:90, 10:22] = True                                             # a 12-pixel stem
    m[10:90, 40:41] = True                                             # and a hairline beside it
    assert CP.stem_width(m, m, 0.5) == pytest.approx(6.0)


def test_keep_topology_closes_only_the_thinned_join():
    import trace_ceili_judgement as TJ
    from scipy import ndimage as ndi
    # a ring whose top joins at a level just under the edge (two prints a little apart)
    yy, xx = np.mgrid[:120, :120]
    r = np.hypot(yy - 60, xx - 60)
    mean = ((r > 30) & (r < 42)).astype(float)
    mean[14:34, 56:64] = 0.3
    mean = ndi.gaussian_filter(mean, 1.0)
    near = np.ones(mean.shape, bool)
    assert TJ.raster_topology(mean > 0.4, near) == (1, 0)              # the edge opens the ring
    field, rec = next(TJ.keep_topology(mean, (1, 1), near, 0.4))
    assert TJ.raster_topology(field > 0.4, near) == (1, 1) and rec['radius'] <= 1.5
    changed = np.abs(field - mean) > 1e-6
    assert changed[:35].any() and not changed[60:].any()               # only along the join


def test_disagreements_fill_notches_keep_lost_tips_and_drop_toner():
    import trace_ceili_judgement as TJ
    n46 = np.zeros((160, 160)); n45 = np.zeros((160, 160))
    n46[40:120, 40:80] = n45[40:120, 40:80] = 1.0                       # the body, in both prints (5 x 10 trace units)
    n46[68:74, 40:60] = 0.0                                            # a white streak across N46's stem
    n45[120:136, 56:62] = 1.0                                          # a tip only the offset print keeps
    n46[60:76, 80:92] = 1.0                                            # a lump of toner on N46's edge
    mean = (n46 + n45) / 2
    near = np.ones(mean.shape, bool)
    edge = 0.6                                                         # above the half of a one-print region
    field, rec = TJ.disagreements(mean, [('N46', n46), ('N45', n45)], [], edge, 0.125, 4.8, near)
    kinds = sorted((r['inked_by'], r['kind'], r['drawn']) for r in rec)
    assert kinds == [('N45', 'notch', True), ('N45', 'protrusion', True), ('N46', 'protrusion', False)]
    assert (field[69:73, 44:56] > edge).all()                          # the streak is filled
    assert (field[122:134, 58:60] > edge).all()                        # the tip is drawn
    assert (field[62:74, 84:90] < edge).all()                          # the lump is not
    votes = [np.maximum(n45, (np.arange(160)[None, :] >= 80) & (np.arange(160)[:, None] >= 60) & (np.arange(160)[:, None] < 76))]
    _, rec = TJ.disagreements(mean, [('N46', n46), ('N45', n45)], votes, edge, 0.125, 4.8, near)
    assert any(r['inked_by'] == 'N46' and r['drawn'] and r['why'].startswith('N44') for r in rec)   # a vote decides


@built
def test_every_redrawn_letter_names_its_prints_and_their_hashes():
    ev = load(ROUND, 'traces', 'evidence.json')
    downloads = {os.path.basename(a['path']): a['sha256'] for a in load(ROOT, 'research', 'downloads.json')['assets']}
    from ceili_prints import sha256
    flyer = sha256(os.path.join(ROOT, 'sources', 'flyer.jpg'))
    redrawn = [g for g in ev['glyphs'] if g.get('method') == 'consensus']
    assert len(redrawn) == 54 and {g['name'] for g in ev['glyphs'] if g['status'] == 'retained'} == {'DOTS'}
    for g in redrawn:
        averaged = [p for p in g['prints'] if p['averaged']]
        assert len(averaged) >= 2 and {'N46', 'N45'} <= {p['print'] for p in averaged}, g['name']
        for p in g['prints']:
            want = flyer if p['print'] == 'flyer' else downloads[p['file']] if p['print'] != 'B2' else None
            if want:
                assert p['sha256'] == want, (g['name'], p['print'])
            geo = p['geometry']
            assert geo['aspect'] == 1.0 and geo['shear'] == 0.0, (g['name'], p['print'])
        assert 0.95 <= g['frame_check']['scale'] <= 1.05, g['name']             # a check only: not applied
    assert ev['prints']['B2']['sha256'] == ev['source_hashes']['b2-fig203b.jpg (pdfimages -j, page 159)']
    assert ev['source_hashes']['Bolger-2017-volume-2-illustrations.pdf'] == downloads['Bolger-2017-volume-2-illustrations.pdf']


@built
def test_topology_is_the_prints_and_the_ampersand_is_a_recorded_decision():
    import trace_ceili_judgement as TJ
    ev = {g['name']: g for g in load(ROUND, 'traces', 'evidence.json')['glyphs']}
    tr = {g['name']: g for g in load(ROUND, 'traces', 'ceili.json')['glyphs']}
    for n, g in ev.items():
        if g.get('method') != 'consensus':
            continue
        t = g['topology']
        assert t['fitted'] == t['attested'] and tuple(t['attested']) == TJ.rec_topology(tr[n]['rec']), n
        prints = {tuple(p['topology']) for p in g['prints'] if p['averaged']}
        assert prints == {tuple(t['attested'])} or n in TJ.DECISIONS, n
    want = {'b': [1, 0], 'e': [1, 1], 'e.alt1': [1, 1], 'six': [1, 0], 'eight': [1, 2], 'exclam': [2, 0],
            'question': [2, 0], 'i': [2, 0], 'j': [2, 0], 'ampersand': [1, 1]}
    assert {n: ev[n]['topology']['attested'] for n in want} == want


@built
def test_the_upper_pieces_are_identified_and_only_the_fada_is_built():
    p = {q['name']: q for q in load(ROUND, 'traces', 'punctuation.json')['pieces']}
    assert {n: p[n].get('use') for n in ('acute', 'dot.round', 'dot.diamond')} == \
        {'acute': 'built', 'dot.round': 'recorded, not built', 'dot.diamond': 'recorded, not built'}
    assert p['acute']['box'] == [1308, 685, 1321, 698] and [q['labels'] for q in p['acute']['prints']] == [[5], [27]]
    assert {n: p[n]['source_id'] for n in ('period', 'comma', 'quoteleft', 'quoteright')} == \
        {'period': 'N45', 'comma': 'N45', 'quoteleft': 'N45+N46', 'quoteright': 'N45+N46'}


def font(ext='otf'):
    return os.path.join(ROUND, 'fonts', f'CeiliStudy4-Regular.{ext}')


@built
@pytest.mark.parametrize('ext', ['otf', 'ttf', 'woff', 'woff2'])
def test_study4_fonts_sanitise_and_keep_the_release_coverage(ext):
    import ots
    from fontTools.ttLib import TTFont
    assert ots.sanitize(font(ext), os.devnull, capture_output=True).returncode == 0
    f = TTFont(font(ext))
    assert f['name'].getDebugName(1) == 'Céilí Study 4' and f['name'].getDebugName(6) == 'CeiliStudy4-Regular'
    assert f.getBestCmap().keys() == TTFont(os.path.join(ROOT, 'fonts', 'otf', 'CeiliDigital-Regular.otf')).getBestCmap().keys()


@built
@pytest.mark.parametrize('ext', ['otf', 'ttf'])
def test_the_acute_is_the_sheets_fada_and_clears_open_letters(ext):
    from fontTools.ttLib import TTFont
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    from fontTools.pens.boundsPen import BoundsPen
    import evidence_board as EB
    f = TTFont(font(ext)); gs = f.getGlyphSet()
    piece = next(q for q in load(ROUND, 'traces', 'punctuation.json')['pieces'] if q['name'] == 'acute')
    pts = np.array([q for _, a in piece['rec'] for q in a], float)
    bp = BoundsPen(gs); gs['acutecomb'].draw(bp); b = bp.bounds
    assert (b[2] - b[0]) == pytest.approx(np.ptp(pts[:, 0]), abs=3) and (b[3] - b[1]) == pytest.approx(np.ptp(pts[:, 1]), abs=3)
    xh = f['OS/2'].sxHeight
    for n in ('uacute', 'wacute', 'yacute', 'aacute', 'iacute', 'oacute', 'eacute'):
        polys = EB.glyph_polygons(f, n)
        top = max(polys, key=lambda p: p[:, 1].max())
        assert top[:, 1].min() > xh, n                                 # the fada sits above the letter, never in it
    prov = load(ROUND, 'fonts', 'CeiliStudy4-Regular.provenance.json')
    assert 'síneadh fada' in prov['acute'][1] and 'fada' in prov['grave'][1]


@built
@pytest.mark.parametrize('ext', ['otf', 'ttf'])
def test_the_exclamation_and_question_dots_stay_separate(ext):
    from fontTools.ttLib import TTFont
    import evidence_board as EB
    f = TTFont(font(ext))
    for n in ('exclam', 'question', 'exclamdown', 'questiondown'):
        assert len(EB.glyph_polygons(f, n)) == 2, n


def test_a_dot_the_bold_brings_close_is_set_apart_only_when_asked():
    import bolden, shapes as SH
    from glyphs import contours, bounds
    box = lambda x0, y0, x1, y1: SH.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    core = SH.union(box(0, 60, 40, 200), box(0, 0, 40, 40))               # a stroke and its dot, 20 apart
    bold = SH.union(box(-10, 52, 50, 210), box(-10, -10, 50, 48))          # the wider pen leaves 4 units
    assert bolden._separate(core, bold, (10, 10)) is bold                  # still apart: left alone by default
    out = bolden._separate(core, bold, (10, 10), close=True)
    lo, hi = sorted((bounds(c) for c in contours(out)), key=lambda b: b[1])
    assert hi[1] - lo[3] == pytest.approx(bolden.F_PASS * 20, abs=2.5)     # the gap F_PASS of the regular's


def test_the_bold_keeps_its_designed_join():
    import build2
    assert build2.BOLD['ceili']['joins'] == ('six',)
