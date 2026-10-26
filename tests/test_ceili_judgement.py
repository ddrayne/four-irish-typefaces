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


# ---------------------------------------------------------------- the finishing pass (judged-edits.json)
def test_the_bold_can_keep_the_regulars_whole_gap():
    import bolden, shapes as SH
    from glyphs import contours, bounds
    box = lambda x0, y0, x1, y1: SH.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    core = SH.union(box(0, 60, 40, 200), box(0, 0, 40, 40))
    bold = SH.union(box(-10, 52, 50, 210), box(-10, -10, 50, 48))
    out = bolden._separate(core, bold, (10, 10), close=True, share=1.0)
    lo, hi = sorted((bounds(c) for c in contours(out)), key=lambda b: b[1])
    assert hi[1] - lo[3] == pytest.approx(20, abs=2.5)


def _segs(rec):
    import finish as F
    return [[k, list(p)] for k, p in F._contours(rec)[0]]


def _rec(points, closed=True):
    """A polygon recording (lines) from points."""
    return [('moveTo', (points[0],))] + [('lineTo', (p,)) for p in points[1:]] + [('closePath', ())]


def test_economy_draws_one_curve_for_two_and_keeps_extremes():
    import ceili_finish as CF, shapes as SH
    from fontTools.pens.recordingPen import RecordingPen
    import pathops
    o = SH.ellipse(0, 0, 200, 120)                                   # four extremes, four curves
    rec = CF.recording(o)
    # split every curve in two at its middle: eight nodes, four of them redundant
    import finish as F
    from curvefit import _split_cubic
    segs = _segs(rec); split = []
    for i in range(len(segs)):
        a, b = _split_cubic(CF._ctrl(segs, i), 0.5)
        split += [CF._seg('C', a), CF._seg('C', b)]
    out = CF.economy(F._record([split]))
    assert len(_segs(out)) == 4
    pts = CF._dense(_segs(out), 1.0)
    assert {round(pts[:, 0].max()), round(pts[:, 0].min()), round(pts[:, 1].max()), round(pts[:, 1].min())} == {200, -200, 120, -120}


def test_a_hidden_corner_leaves_on_the_stems_tangent():
    import ceili_finish as CF, finish as F
    # a stem rising to (100, 300), then a curve that bends 20 degrees within a 1-unit handle
    segs = [['L', [(100.0, 300.0)]], ['C', [(100.0, 301.0), (90.0, 330.0), (60.0, 380.0)]],
            ['L', [(0.0, 380.0)]], ['L', [(0.0, 0.0)]], ['L', [(100.0, 0.0)]]]
    out = CF.smooth_hidden_corners([list(s) for s in segs])
    curve = next(CF._ctrl(out, i) for i in range(len(out)) if out[i][0] == 'C')
    assert np.linalg.norm(curve[1] - curve[0]) > 6                              # a real handle now
    assert abs(CF._dirs(curve)[0][0]) < 1e-6                                     # along the stem
    assert CF._dist(CF._dense(out, 1.0), CF._dense(segs, 1.0)) <= 3.0


def test_a_rounded_pen_cut_is_drawn_straight_between_sharp_corners():
    import ceili_finish as CF, finish as F, shapes as SH
    from glyphs import contours
    # a bar 60 deep whose square end the print rounded at both corners (radius 8)
    box = lambda x0, y0, x1, y1: SH.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    p = SH.union(box(0, 0, 395, 60), box(395, 8, 403, 52), SH.circle(395, 8, 8), SH.circle(395, 52, 8))
    rec = CF.recording(p)
    segs = _segs(rec)
    out = CF.pen_terminals(segs, CF.orientation(rec))
    pts = CF._dense(out, 0.5)
    assert pts[:, 0].max() == pytest.approx(403, abs=0.5)                       # the cut where it was
    for corner in ((403, 0), (403, 60)):                                         # and both corners sharp
        assert np.linalg.norm(pts - corner, axis=1).min() < 1
    # the foot of an upright stem keeps its rounding, as the face's feet do
    stem = SH.union(box(0, 8, 60, 400), box(8, 0, 52, 8), SH.circle(8, 8, 8), SH.circle(52, 8, 8))
    rec = CF.recording(stem)
    assert len(CF.pen_terminals(_segs(rec), CF.orientation(rec))) == len(_segs(rec))


def test_a_corner_drawn_as_facets_becomes_one_corner():
    import ceili_finish as CF
    # a square corner at (100, 100) cut by three short facets
    pts = [(0, 0), (100, 0), (100, 92), (99, 97), (97, 99), (92, 100), (0, 100)]
    out = CF.collapse_clusters(_segs(_rec(pts)))
    corners = sorted(tuple(np.round(CF._a(s[1][-1]), 3)) for s in out)
    assert corners == [(0, 0), (0, 100), (100, 0), (100, 100)]


def test_tidy_draws_a_rasters_polyline_as_curves():
    import ceili_finish as CF
    # a half disc whose arc is a run of short lines, as the bold's reopened joins come out
    arc = [(100 * np.cos(t), 100 * np.sin(t)) for t in np.linspace(0, np.pi, 40)]
    out = CF.tidy(_rec(arc))
    segs = _segs(out)
    assert sum(1 for k, _ in segs if k == 'L') <= 1 and len(segs) <= 5
    assert CF._dist(CF._dense(segs, 1.0), np.array(arc)) <= 1.6


def test_the_pen_diamond_keeps_the_dots_corners():
    import ceili_finish as CF
    period = [['C', [(40, 10), (60, 30), (60, 60)]], ['C', [(50, 90), (30, 110), (0, 120)]],
              ['C', [(-30, 110), (-50, 90), (-60, 60)]], ['C', [(-60, 30), (-40, 10), (0, 0)]]]
    dot = [['C', [(140, 20), (150, 40), (150, 50)]], ['C', [(150, 80), (120, 100), (100, 100)]],
           ['C', [(80, 100), (50, 80), (50, 50)]], ['C', [(50, 20), (70, 0), (100, 0)]]]
    out = CF.pen_diamond(dot, period)
    corners = sorted(tuple(np.round(s[1][-1])) for s in out)
    assert corners == sorted(tuple(np.round(s[1][-1])) for s in dot)


def test_a_heavier_bar_runs_its_cut_and_its_diagonal_on():
    import ceili_finish as CF, shapes as SH
    from glyphs import bounds
    # a 7: a level bar with a slanted pen cut at its free end, turning into a diagonal
    seven = SH.polygon([(30, 550), (330, 550), (130, 0), (60, 0), (250, 460), (0, 460)])
    out = CF.heavier_bar(seven, 30, 'bar')
    assert bounds(out)[3] == pytest.approx(550)                                  # the top stays on its line
    assert CF.vertical_runs(out, 120)[-1] == pytest.approx((430, 550), abs=0.5)  # the lower edge came down
    run = [r for r in CF.vertical_runs(out, -5) if r[1] > 400]                 # the cut ran on along its own line
    assert run and run[0][0] == pytest.approx(430, abs=1) and bounds(out)[0] == pytest.approx(-10, abs=1)


def test_a_terminal_gap_keeps_the_stem_and_cuts_the_terminal():
    import bolden, ceili_finish as CF, shapes as SH
    box = lambda x0, y0, x1, y1: SH.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    core = SH.union(box(0, 0, 40, 300), box(40, 280, 200, 300), box(56, 100, 200, 140), box(180, 140, 200, 280))
    bold = bolden.grow(core, 10, 2)                                              # the pen joins the stem and the arm
    import pathops
    out, info = CF.terminal_gap(core, bold, (10, 2), (48, 120), 15)
    assert info['width'] == pytest.approx(16, abs=1)
    # the stem keeps its grown edge (x = 50) all the way past the join, and nothing of the arm stands within 15 of it
    assert any(r[0] <= 2 and r[1] >= 298 for r in CF.vertical_runs(out, 49.5))
    assert abs(bolden.area(SH.op(out, box(50.5, 80, 64.5, 160), pathops.PathOp.INTERSECTION))) < 1
    assert CF.vertical_runs(out, 66) and CF.topology(out) == (1, 0)           # the arm is there beyond the gap


def test_close_cracks_closes_a_counter_but_keeps_a_dots_gap():
    import ceili_finish as CF, shapes as SH
    box = lambda x0, y0, x1, y1: SH.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    hook = SH.difference(box(0, 0, 200, 200), SH.union(box(40, 40, 160, 160), box(100, 160, 108, 200)))   # an 8-unit crack
    out, n = CF.close_cracks(hook, 12)
    assert n == 1 and CF.topology(out) == (1, 1)
    dot = SH.union(box(0, 0, 40, 40), box(0, 48, 40, 200))                                                 # 8 apart
    assert CF.close_cracks(dot, 12) == (dot, 0)
    wide = SH.difference(box(0, 0, 200, 200), SH.union(box(40, 40, 160, 160), box(100, 160, 116, 200)))   # 16 open
    assert CF.close_cracks(wide, 12)[1] == 0


def test_one_rounding_keeps_a_smooth_join_smooth():
    import ceili_finish as CF
    # a sloped stem (an upright one sheared as the italic is, off the grid) leaving into an arch on a 3-unit handle
    t = np.tan(np.radians(8)); sh = lambda x, y: (x + 0.37 + y * t, y + 0.21)
    segs = [['L', [sh(100, 400)]], ['C', [sh(100, 403), sh(115, 470), sh(170, 480)]], ['L', [sh(300, 480)]],
            ['L', [sh(300, 0)]], ['L', [sh(100, 0)]]]
    def join(s):
        return abs(np.degrees(CF._angle(CF._dirs(CF._ctrl(s, 0))[1], CF._dirs(CF._ctrl(s, 1))[0])))
    plain = [[k, [tuple(np.round(q)) for q in p]] for k, p in segs]
    assert join(plain) > 4                                                     # rounding alone turns the short handle
    out = CF.round_smooth([[k, list(p)] for k, p in segs])
    assert join(out) < 2 and all(float(v).is_integer() for _, p in out for q in p for v in q)
    assert CF._dist(CF._dense(out, 1.0), CF._dense(segs, 1.0)) <= 1.0


def test_an_extreme_a_unit_from_a_node_gets_no_node():
    import ceili_finish as CF
    # a curve that passes its x extreme 0.4 units beyond its start, and one that passes it 30 units out
    near = [['L', [(0.0, 0.0)]], ['C', [(1.0, 20.0), (-10.0, 60.0), (-60.0, 80.0)]], ['L', [(-60.0, -100.0)]]]
    far = [['L', [(0.0, 0.0)]], ['C', [(40.0, 20.0), (40.0, 60.0), (0.0, 80.0)]], ['L', [(-60.0, -100.0)]]]
    assert len(CF.overshoot_extremes(near)) == 3 and len(CF.overshoot_extremes(far)) == 4


def test_a_stem_runs_straight_to_its_foot_unless_it_flares():
    import ceili_finish as CF
    from glyphs import bounds
    foot = [('curveTo', ((140, 0), (170, 0), (200, 10))), ('lineTo', ((200, 500),)), ('lineTo', ((100, 500),)), ('lineTo', ((100, 160),))]
    # the left edge bulges 9 units out above the foot and comes back to its corner, as the h's did
    bulge = CF.path([('moveTo', ((100, 20),))] + foot + [('curveTo', ((100, 130), (91, 118), (91, 84))),
                                                          ('curveTo', ((91, 63), (94, 44), (100, 20))), ('closePath', ())])
    q, rep = CF.straight_feet(bulge, [[0.5, 0]], 500, 2.0)
    assert [r['side'] for r in rep] == ['left'] and rep[0]['bulge'] == pytest.approx(9, abs=0.5)
    assert bounds(q)[0] == pytest.approx(100) and CF.topology(q) == (1, 0)
    # a foot that flares out to its corner is drawn so
    flare = CF.path([('moveTo', ((80, 20),)), ('curveTo', ((140, 0), (170, 0), (200, 10))), ('lineTo', ((200, 500),)),
                     ('lineTo', ((100, 500),)), ('lineTo', ((100, 160),)), ('curveTo', ((100, 100), (95, 40), (80, 20))), ('closePath', ())])
    assert CF.straight_feet(flare, [[0.5, 0]], 500, 2.0)[1] == []


def test_the_bar_is_set_its_gap_above_the_stem():
    import ceili_finish as CF, shapes as SH
    from glyphs import bounds
    box = lambda x0, y0, x1, y1: SH.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    j = SH.union(box(0, -150, 100, 500), box(-10, 520, 110, 570))                # 20 apart
    out = CF.set_bar_gap(j, 31)
    assert CF.bar_gap(out) == pytest.approx(31, abs=0.15) and bounds(out)[3] == pytest.approx(581, abs=0.2)


# the finished fonts (fonts/, or FONTDIR=build/fonts for a fresh build)
STYLES = ('Regular', 'Italic', 'Bold', 'Bold Italic')
LOWER = 'a a.alt1 a.alt2 b c d d.alt1 e e.alt1 f g h i j j.alt1 k l l.alt1 m n n.alt1 o p q r r.alt1 s s.alt1 t u v v.alt1 w x y z'.split()


def finished(style):
    from conftest import static
    from fontTools.ttLib import TTFont
    return TTFont(static('CeiliDigital', style))


def test_the_finishing_pass_is_recorded():
    ev = load(ROUND, 'judged-edits.json')
    assert set(ev['sit_on_baseline']) == {'h'} and ev['pen_diamond']['glyphs'] == ['exclam', 'question']
    assert ev['finish']['regular'] and ev['finish']['tidy']


@pytest.mark.parametrize('style', STYLES)
def test_the_h_stands_on_the_baseline_with_n_and_k(style):
    from fontTools.pens.boundsPen import BoundsPen
    f = finished(style); gs = f.getGlyphSet()
    def box(n):
        bp = BoundsPen(gs); gs[n].draw(bp); return bp.bounds
    assert abs(box('h')[1]) <= 1 and abs(box('n')[1]) <= 1
    assert abs(box('h')[3] - box('k')[3]) < 15                       # its ascender with k's, not 40 above it


@pytest.mark.parametrize('style', STYLES)
def test_the_finished_outlines_are_economical_and_clean(style):
    """No glyph keeps a polygonal run (three short lines in a row) or a curve that passes an extreme
    without a node, and the lowercase is drawn with few nodes (the release had 22, 44, 86 and 82 a letter)."""
    import ceili_finish as CF, finish as F
    from fontTools.pens.recordingPen import RecordingPen
    f = finished(style); gs = f.getGlyphSet()
    nodes, runs, missing = [], set(), set()
    for n in f.getGlyphOrder():
        r = RecordingPen(); gs[n].draw(r)
        for segs in F._contours(r.value):
            m = len(segs)
            short = [k == 'L' and np.linalg.norm(CF._ctrl(segs, i)[3] - CF._ctrl(segs, i)[0]) < 14 for i, (k, _) in enumerate(segs)]
            if m > 4 and any(all(short[(i + j) % m] for j in range(3)) for i in range(m)):
                runs.add(n)
            if any(k == 'C' and CF._interior_extreme(CF._ctrl(segs, i), margin=1.5) for i, (k, _) in enumerate(segs)):
                missing.add(n)
            if n in LOWER:
                nodes.append(m)
    per_letter = sum(nodes) / len(LOWER)
    assert per_letter < {'Regular': 21, 'Italic': 25, 'Bold': 27, 'Bold Italic': 31}[style], per_letter
    assert not missing, sorted(missing)
    assert not runs, sorted(runs)


@pytest.mark.parametrize('style', STYLES)
def test_the_dots_stand_clear_in_every_style(style):
    """The dots of ! and ? and the strokes of the double acute keep their distance (the Bold Italic's
    double acute touched, and the bold dots stood 5 to 10 units from their strokes)."""
    import evidence_board as EB
    f = finished(style)
    def gap(n):
        ps = [np.vstack([p + (q - p) * t for p, q in zip(P, np.roll(P, -1, axis=0)) for t in np.linspace(0, 1, 6)]) for P in EB.glyph_polygons(f, n)]
        assert len(ps) == 2, n
        return float(np.linalg.norm(ps[0][:, None] - ps[1][None], axis=2).min())
    assert gap('exclam') > 9 and gap('question') > 11
    assert gap('hungarumlaut') > 9


def test_letters_and_quotes_kern_by_one_rule():
    """The space between a letter's upper part and a quote varies little from letter to letter (in the
    release it ran from 100 units for e’ to -50 for o’)."""
    import uharfbuzz as hb
    import evidence_board as EB
    from conftest import static
    path = static('CeiliDigital', 'Regular'); f = finished('Regular'); order = f.getGlyphOrder(); xh = f['OS/2'].sxHeight
    font = hb.Font(hb.Face(open(path, 'rb').read()))
    def clear(a, q):
        b = hb.Buffer(); b.add_str(a + q); b.guess_segment_properties(); hb.shape(font, b, {'kern': True})
        na = order[b.glyph_infos[0].codepoint]; nq = order[b.glyph_infos[1].codepoint]
        pa = np.vstack(EB.glyph_polygons(f, na)); pq = np.vstack(EB.glyph_polygons(f, nq))
        return b.glyph_positions[0].x_advance + pq[:, 0].min() - pa[pa[:, 1] >= 0.55 * xh][:, 0].max()
    room = [clear(c, '’') for c in 'cdemnosu']
    assert max(room) - min(room) < 25, room


@pytest.mark.parametrize('style', ('Italic', 'Bold Italic'))
def test_the_sloped_styles_keep_the_regulars_topology(style):
    """Only the Bold's designed join in 6 (and, in the Bold Italic, the dollar's small counters, which
    the 3.000 release already narrowed to a third) may differ from the Regular."""
    import topo
    from conftest import static
    flagged = {n: why for n, why, *_ in topo.compare(static('CeiliDigital', 'Regular'), static('CeiliDigital', style))}
    allowed = {'Italic': {}, 'Bold Italic': {'six': 'counters 0->1', 'dollar': 'smallest counter',
                                             # the second pass closed their cracks (judged-edits.json, bold_joins)
                                             'ampersand': 'counters 1->2', 'yen': 'counters 0->1'}}[style]
    assert set(flagged) <= set(allowed) and all(flagged[n].startswith(allowed[n]) for n in flagged), flagged


# ---------------------------------------------------------------- the second pass (judged-edits.json, second_pass)
def _polys(style, n, upright=False):
    """The glyph's polygons; with `upright`, a sloped style's shear taken back (about the middle of the x-height,
    as the builder slopes them), so that what the builder measured before the slope can be measured again."""
    import evidence_board as EB
    f = finished(style); polys = [np.asarray(P, float) for P in EB.glyph_polygons(f, n)]
    t = -np.tan(np.radians(f['post'].italicAngle))
    if upright and t:
        yc = f['OS/2'].sxHeight / 2
        polys = [np.column_stack([P[:, 0] - (P[:, 1] - yc) * t, P[:, 1]]) for P in polys]
    return polys


def _box(polys):
    P = np.vstack(polys); return P[:, 0].min(), P[:, 1].min(), P[:, 0].max(), P[:, 1].max()


def _runs(polys, v, axis):
    """Ink runs across a line: axis 0, the vertical x = v (runs in y); axis 1, the level y = v (runs in x)."""
    out, o = [], 1 - axis
    for P in polys:
        a, b = P, np.roll(P, -1, axis=0)
        m = ((a[:, axis] <= v) & (b[:, axis] > v)) | ((b[:, axis] <= v) & (a[:, axis] > v))
        t = (v - a[m, axis]) / (b[m, axis] - a[m, axis]); out += list(a[m, o] + t * (b[m, o] - a[m, o]))
    out = sorted(out); return list(zip(out[0::2], out[1::2]))


def _raster(polys, pad=40):
    """The glyph's ink at one unit a pixel (even-odd), with the frame's origin."""
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = _box(polys); W, H = int(x1 - x0) + 2 * pad, int(y1 - y0) + 2 * pad
    acc = np.zeros((H, W), bool)
    for P in polys:
        im = Image.new('1', (W, H), 0); ImageDraw.Draw(im).polygon([(x - x0 + pad, y1 - y + pad) for x, y in P], fill=1)
        acc ^= np.asarray(im)
    return acc


def _topology(ink):
    from scipy import ndimage as ndi
    pieces = ndi.label(ink, structure=np.ones((3, 3)))[1]
    lab, n = ndi.label(~ink); edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    return pieces, sum(1 for k in range(1, n + 1) if k not in edge and (lab == k).sum() > 4)


def _closes_under(style, n, width):
    """Does closing the glyph's ink with a disc `width` wide change its pieces or counters?"""
    from scipy import ndimage as ndi
    ink = _raster(_polys(style, n)); r = width // 2
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return _topology(ndi.binary_closing(ink, structure=xx ** 2 + yy ** 2 <= r * r)) != _topology(ink)


def test_the_second_pass_is_recorded():
    sp = load(ROUND, 'judged-edits.json')['second_pass']
    assert {'stems', 'bold_heavy_strokes', 'bold_joins', 'bold_dot_feet', 'quote_over_foot', 'bar_spacing', 'currency',
            'bold_section'} <= set(sp) and all(v.get('why') for k, v in sp.items() if k != 'about')


@pytest.mark.parametrize('style', ('Bold', 'Bold Italic'))
def test_the_bolds_heavy_level_strokes_take_the_stems_gain(style):
    """Level strokes drawn at least 0.75 of a stem in the Regular gain as the stems do: the bold's 7 bar went
    from 93 to 102 while the 1's stem went from 102 to 162, and the hyphen, dashes and math signs from 81 to 91."""
    def weight(st, n):
        P = _polys(st, n, upright=True); b = _box(P)
        if n in ('seven', 'three'):         # the bar at the figure's top, a third of the way along
            return next(r[1] - r[0] for r in _runs(P, b[0] + 0.3 * (b[2] - b[0]), 0) if r[1] > b[3] - 3)
        x = b[0] + (0.15 if n == 'plus' else 0.5) * (b[2] - b[0])
        return min(r[1] - r[0] for r in _runs(P, x, 0))
    stem = lambda st: min(r[1] - r[0] for r in _runs(_polys(st, 'one'), 250, 1))
    gain = stem(style) / stem('Regular')
    for n in ('seven', 'three', 'hyphen', 'endash', 'emdash', 'minus', 'plus', 'equal'):
        k = weight(style, n) / weight('Regular', n)
        assert 1.4 <= k <= gain + 0.05, (n, round(k, 2), round(gain, 2))


@pytest.mark.parametrize('style', STYLES)
def test_a_quote_after_l_stands_clear_of_its_stem(style):
    """l’ (and L’ and ł’) were kerned -330 to -350: the quote stood over l's long foot 64 units from the stem
    and read as ľ. A quote may tuck in over a lower part but never stands wholly over it: its far edge reaches
    the foot's tip, so it stands well clear of the stem."""
    import uharfbuzz as hb
    from conftest import static
    f = finished(style); order = f.getGlyphOrder(); hm = f['hmtx']
    font = hb.Font(hb.Face(open(static('CeiliDigital', style), 'rb').read()))
    q = _box(_polys(style, 'quoteright', upright=True))
    n = _box(_polys(style, 'n', upright=True)); nn = hm['n'][0] - (n[2] - n[0])                # the white of n n
    for text in ('l’', 'L’', 'ł’'):
        b = hb.Buffer(); b.add_str(text); b.guess_segment_properties(); hb.shape(font, b, {'kern': True})
        a = order[b.glyph_infos[0].codepoint]; pos = b.glyph_positions[0].x_advance
        P = np.vstack(_polys(style, a, upright=True)); tip = P[:, 0].max()
        stem = P[P[:, 1] >= 0.55 * f['OS/2'].sxHeight][:, 0].max()
        assert pos - hm[a][0] < -100, (text, pos - hm[a][0])                     # it still tucks in
        assert -1 <= pos + q[2] - tip <= 6, (text, pos + q[2] - tip)             # over the foot's tip
        if a == 'l':
            assert pos + q[0] - stem >= 1.8 * nn, (pos + q[0] - stem, nn)


@pytest.mark.parametrize('style', ('Bold', 'Bold Italic'))
def test_the_bolds_open_joins_keep_their_stems_whole(style):
    """The bold reopened the joins of b, k, p and r through the stem (p's narrowed from 166 to 141 at the join,
    k's from 165 to 142), leaving cracks of 4 to 18 units. The stems now keep their width, each join stays at
    least 13 units open, and the ampersand's 8-unit crack is closed, as the bold 6's join is."""
    xh = finished(style)['OS/2'].sxHeight
    for n, lo, hi in (('p', 0.05, 0.6), ('k', 0.1, 0.6), ('r', 0.1, 0.6)):
        P = _polys(style, n)
        w = [_runs(P, f * xh, 1)[0] for f in np.linspace(lo, hi, 15)]
        widths = [b - a for a, b in w]
        assert max(widths) - min(widths) <= 6, (n, [round(v) for v in widths])
    for n in ('b', 'd', 'k', 'p', 'r', 'nine', 'thorn'):
        assert not _closes_under(style, n, 13), n
    assert _topology(_raster(_polys(style, 'ampersand')))[1] == _topology(_raster(_polys('Regular', 'ampersand')))[1] + 1


@pytest.mark.parametrize('style', ('Bold', 'Bold Italic'))
def test_the_bold_exclamation_stands_where_the_regulars_does(style):
    """The bold's pen ran the ! dot's sharp foot 11 units further down, so the ! missed the baseline snap and sat
    25 units low (stroke top 629, dot bottom -33, against the Regular's 643 and -8)."""
    for n in ('exclam', 'question'):
        b, r = _box(_polys(style, n)), _box(_polys('Regular', n))
        assert abs(b[1] - r[1]) <= 2 and abs(b[3] - r[3]) <= 3, (n, b, r)


@pytest.mark.parametrize('style', ('Regular', 'Bold'))
def test_the_straight_stems_share_the_faces_weight(style):
    """The h's stems were 100 against n's 107 and 112, m's 115 and i's 106 (Bold 159 against n's 168 and 173)."""
    y = 0.4 * finished(style)['OS/2'].sxHeight
    w = {n: [round(b - a) for a, b in _runs(_polys(style, n), y, 1)] for n in ('h', 'n', 'm', 'i', 'k', 'p', 'r')}
    stems = w['h'] + w['n'] + w['m'] + w['i'] + [w[n][0] for n in 'kpr']
    assert max(stems) - min(stems) <= 4, w


@pytest.mark.parametrize('style', STYLES)
def test_eth_and_dcroat_are_spaced_as_d(style):
    """The Regular's ð kept d's advance with its bar 90 units into the letter before; the Bold's was 130 wider than
    d. Both take d's right sidebearing and its advance plus the bar's overhang, the bar ending no further left than -20."""
    f = finished(style); hm = f['hmtx']
    d = _box(_polys(style, 'd'))
    for n in ('eth', 'dcroat'):
        e = _box(_polys(style, n))
        assert abs((hm[n][0] - e[2]) - (hm['d'][0] - d[2])) <= 1.5, n          # d's right sidebearing
        if 'Italic' not in style:                     # the slope moves the bar's end off the letter's left
            over = e[2] - (d[2] - d[0]) - e[0]                                 # the bar's reach left of the d
            assert abs(e[0] - max(-20, d[0] - over)) <= 1.5, (n, e[0], d[0] - over)
        assert e[0] >= -30, (n, e[0])


@pytest.mark.parametrize('style', STYLES)
def test_euro_and_yen_stand_with_the_figures(style):
    """€ was 602 units tall and ¥ 565, against 538 for 0 and £."""
    z, s = _box(_polys(style, 'zero')), _box(_polys(style, 'sterling'))
    e, y = _box(_polys(style, 'Euro')), _box(_polys(style, 'yen'))
    assert abs(e[1] - z[1]) <= 2 and abs(e[3] - z[3]) <= 2, (e, z)
    assert -1 <= y[1] <= 1 and abs(y[3] - s[3]) <= 2, (y, s)


@pytest.mark.parametrize('style', ('Bold', 'Bold Italic'))
def test_the_bold_section_takes_the_bolds_weight(style):
    """The bold drew § at the weight it gives superiors: 85 to 94 while s went from 91 to 123."""
    from scipy import ndimage as ndi
    from skimage.morphology import skeletonize
    def weight(st, n):
        ink = np.pad(_raster(_polys(st, n)), 2); return 2 * np.median(ndi.distance_transform_edt(ink)[skeletonize(ink)])
    assert weight(style, 'section') / weight(style, 's') >= 0.85
    assert weight(style, 'section') / weight('Regular', 'section') >= 1.3


# ---------------------------------------------------------------- the third pass (judged-edits.json, third_pass)
def _weight(style, n):
    """A glyph's median stroke weight: twice the distance from its skeleton to the paper."""
    from scipy import ndimage as ndi
    from skimage.morphology import skeletonize
    ink = np.pad(_raster(_polys(style, n)), 2)
    return 2 * np.median(ndi.distance_transform_edt(ink)[skeletonize(ink)])


def _upright_of(style):
    return 'Italic' if 'Italic' in style else 'Regular'


def test_the_third_pass_is_recorded():
    tp = load(ROUND, 'judged-edits.json')['third_pass']
    assert {'math_signs', 'quote_near_piece', 'small_signs', 'settle', 'straight_feet', 'j_bar'} <= set(tp)
    assert all(v.get('why') and 'PENDING' not in v['why'] for k, v in tp.items() if k != 'about')


@pytest.mark.parametrize('style', ('Bold', 'Bold Italic'))
def test_the_bold_math_signs_grow_in_place(style):
    """The bold set its math signs out from its own rule weight, so each piece moved outward instead of growing:
    = stood 157 between its bars against the Regular's 105, the bar of ± dropped to -121..0, that of ≤ and ≥ to
    -67..54, ÷ ran from -40 to 576 (over the 538 x-height) and ≈ stood 221 apart against 175, while ~ and ^ grew
    upward only. Each piece now grows about its own centre: the white beside a rule stays the Regular's, and ÷'s
    dots grow about theirs, within the Regular's reach plus the pen's growth."""
    reg = _upright_of(style)
    def column(st, n):
        P = _polys(st, n, upright=True); b = _box(P)
        return _runs(P, b[0] + 0.5 * (b[2] - b[0]), 0), b
    def whites(st, n):
        r = column(st, n)[0]; return [b[0] - a[1] for a, b in zip(r, r[1:])]
    for n in ('equal', 'approxequal', 'plusminus', 'lessequal', 'greaterequal'):
        w, wr = whites(style, n), whites(reg, n)          # the lowest white: between a rule and the piece over it
        assert len(w) == len(wr) and abs(w[0] - wr[0]) <= 5, (n, w, wr)
    for n in ('equal', 'approxequal', 'asciitilde', 'asciicircum', 'multiply', 'plus', 'minus'):
        b, r = column(style, n)[1], column(reg, n)[1]
        assert abs((b[1] + b[3]) - (r[1] + r[3])) / 2 <= 3, (n, b, r)            # grown about its own centre
    bar = lambda st: [(a + z) / 2 for a, z in _runs(_polys(st, 'logicalnot', upright=True), column(st, 'logicalnot')[1][0] + 60, 0)]
    assert abs(bar(style)[0] - bar(reg)[0]) <= 3                                 # ¬'s bar too (its drop keeps its end)
    b, r = column(style, 'divide')[1], column(reg, 'divide')[1]
    xh = finished(style)['OS/2'].sxHeight
    assert r[1] - 20 <= b[1] and b[3] <= r[3] + 20 and b[3] < xh, (b, r)
    for n in ('plusminus', 'lessequal', 'greaterequal'):                          # the underbar: its own growth and the piece's above
        grow = (_weight(style, 'minus') - _weight(reg, 'minus')) * 1.6
        assert column(style, n)[1][1] >= column(reg, n)[1][1] - grow, (n, column(style, n)[1], column(reg, n)[1])


def _shaped(style, text):
    import uharfbuzz as hb
    from conftest import static
    f = finished(style); order = f.getGlyphOrder()
    font = hb.Font(hb.Face(open(static('CeiliDigital', style), 'rb').read()))
    b = hb.Buffer(); b.add_str(text); b.guess_segment_properties(); hb.shape(font, b, {'kern': True})
    return [order[g.codepoint] for g in b.glyph_infos], [p.x_advance for p in b.glyph_positions]


@pytest.mark.parametrize('style', STYLES)
def test_no_quote_stands_wholly_over_a_low_foot(style):
    """The rule that keeps l’ off l's long foot measured the double quote's far edge, so l” and L” stayed kerned
    -345 to -350: the first comma of ” stood 64 units from the stem and read as ľ”. Every quote after l, L and ł
    now stands as the single one does: the far edge of its nearest piece reaches the foot's tip at least."""
    f = finished(style); hm = f['hmtx']
    for a in ('l', 'L', 'ł'):
        for q in ('’', '”', '‘', '“'):
            (na, nq), (pos, _) = _shaped(style, a + q)
            tip = _box(_polys(style, na, upright=True))[2]
            near = min((P for P in _polys(style, nq, upright=True)), key=lambda P: P[:, 0].min())
            assert pos + near[:, 0].max() - tip >= -1.5, (a + q, pos + near[:, 0].max() - tip)
        assert _shaped(style, a + '”')[1][0] == _shaped(style, a + '’')[1][0], a


@pytest.mark.parametrize('style', ('Bold', 'Bold Italic'))
def test_the_bold_small_signs_gain_weight(style):
    """The bold's bullet was the Regular's outline (ink 1.000), and %, ‰ and the letters of @ © ® gained about a
    fifth of the stem where the letters gain a half (stem 108 to 169). The bullet is drawn with the bold's pen,
    those signs take its stem, and the superiors and fractions go as far as their counters allow (third_pass)."""
    from scipy import ndimage as ndi
    from skimage.morphology import skeletonize
    reg = _upright_of(style)
    ink = lambda st, n: _raster(_polys(st, n)).sum()
    gain = _weight(style, 'n') / _weight(reg, 'n')
    assert ink(style, 'bullet') / ink(reg, 'bullet') >= 1.3
    for n in ('percent', 'perthousand'):
        assert _weight(style, n) / _weight(reg, n) >= 0.9 * gain, (n, _weight(style, n), _weight(reg, n), gain)
    def letter(st, n):          # the stem of the letter inside the ring (the ring, two contours, keeps the pen's weight)
        P = sorted(_polys(st, n, upright=True), key=lambda P: np.ptp(P[:, 0]) * np.ptp(P[:, 1]))[:-2]
        b = _box(P); a, z = _runs(P, b[1] + 0.4 * (b[3] - b[1]), 1)[0]; return z - a
    for n in ('at', 'copyright'):
        assert letter(style, n) / letter(reg, n) >= 0.9 * gain, (n, letter(style, n), letter(reg, n), gain)
    # the r of ® takes the small glyphs' weight: at the whole stem the bold r's open join, made small, closes
    assert letter(style, 'registered') / letter(reg, 'registered') >= 1.2, (letter(style, 'registered'), letter(reg, 'registered'))
    for n in ('onesuperior', 'twosuperior', 'threesuperior', 'onehalf', 'onequarter', 'threequarters', 'ordfeminine',
              'ordmasculine', 'trademark'):
        assert ink(style, n) / ink(reg, n) >= 1.3, (n, ink(style, n) / ink(reg, n))


def _joins(style, n):
    """The angle at each join of a glyph's outline where a curve meets a curve or a line (handle directions)."""
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    import finish as F
    f = finished(style); gs = f.getGlyphSet(); pen = DecomposingRecordingPen(gs); gs[n].draw(pen)
    out = []
    for segs in F._contours(pen.value):
        m = len(segs)
        for i in range(m):
            a, b = segs[i], segs[(i + 1) % m]
            pa = [F._start(segs, i)] + list(a[1]); pb = [a[1][-1]] + list(b[1])
            u = next((np.subtract(pa[-1], q) for q in reversed(pa[:-1]) if np.hypot(*np.subtract(pa[-1], q)) > 0.01), None)
            v = next((np.subtract(q, pb[0]) for q in pb[1:] if np.hypot(*np.subtract(q, pb[0])) > 0.01), None)
            if u is not None and v is not None and 'C' in (a[0], b[0]):
                out.append(abs(np.degrees(np.arctan2(u[0] * v[1] - u[1] * v[0], u @ v))))
    return out


@pytest.mark.parametrize('style', ('Italic', 'Bold Italic'))
def test_the_sloped_outlines_keep_their_smooth_joins(style):
    """Rounding the sheared outlines to whole units turned their short handles by up to 14 degrees: the Italic m had
    8-degree joins at its arches and 10-14 degree clusters at its feet where the Regular has none, and 53 of the 74
    letters and figures had a kink of 5 degrees or more (Regular 37). The sloped outlines are put on the grid once,
    from the drawing, their smooth joins kept within 2 degrees; what remains are the drawing's own shallow corners."""
    for n in ('m', 'n', 'h', 'i', 'r'):
        assert not [a for a in _joins(style, n) if 2 < a < 15], (n, [round(a, 1) for a in _joins(style, n) if 2 < a < 15])
    kinked = lambda st: sum(any(5 <= a < 15 for a in _joins(st, n)) for n in LOWER)
    assert kinked(style) <= kinked('Regular' if style == 'Italic' else 'Bold') + 3, (kinked(style), style)


@pytest.mark.parametrize('style', ('Regular', 'Bold'))
def test_the_stems_run_straight_to_their_feet(style):
    """The second pass gave the stems the face's weight by moving their straight edges, but h's left foot still
    bulged 9 units out below the line (its edge 87 above y 160, 78 at y 90; Bold 80 and 71), where n, m and k run
    straight; and the h's shoulder met its right stem in a 5-degree kink (Bold 12). Every evened stem now runs
    straight to its foot, and the h's joins are smooth."""
    xh = finished(style)['OS/2'].sxHeight
    stems = load(ROUND, 'judged-edits.json')['second_pass']['stems']['glyphs']
    for n, spec in stems.items():
        P = _polys(style, n)
        for frac, run in spec:
            ref = _runs(P, frac * xh, 1); out = {0: [], 1: []}
            for y in np.arange(frac, 0.03, -0.01) * xh:       # from the stem down to its foot
                r = _runs(P, y, 1)
                if len(r) != len(ref):
                    continue
                (a, b), (a0, b0) = r[run], ref[run]
                if b - a > b0 - a0 + 20:
                    continue                          # the stem has met another stroke (f's foot)
                out[0].append(a0 - a); out[1].append(b - b0)
            for side, d in out.items():
                # a bulge: the edge out past the stem's line and back in again lower down (a foot that flares stays out)
                back = max((d[i] - min(d[i:]) for i in range(len(d)) if d[i] > 2.5), default=0)
                assert back <= 2.5, (n, frac, run, 'left' if side == 0 else 'right', round(back, 1))
    assert not [a for a in _joins(style, 'h') if 2 < a < 15], [round(a, 1) for a in _joins(style, 'h')]


@pytest.mark.parametrize('style', STYLES)
def test_the_bar_of_j_stands_as_far_as_is(style):
    """j's bar stood 22 units above its stem (Bold 19, Bold Italic 18) against 31 for i's (19 and 18 in the bolds,
    as the bars' closest points measure it)."""
    def gap(n):
        ps = [np.vstack([p + (q - p) * t for p, q in zip(P, np.roll(P, -1, axis=0)) for t in np.linspace(0, 1, 8)]) for P in _polys(style, n)]
        top = max(range(len(ps)), key=lambda k: ps[k][:, 1].min())
        rest = np.vstack([P for k, P in enumerate(ps) if k != top])
        from scipy.spatial import cKDTree
        return float(cKDTree(rest).query(ps[top])[0].min())
    assert abs(gap('j') - gap('i')) <= 1.5, (gap('j'), gap('i'))
