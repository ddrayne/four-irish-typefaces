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
    allowed = {'Italic': {}, 'Bold Italic': {'six': 'counters 0->1', 'dollar': 'smallest counter'}}[style]
    assert set(flagged) <= set(allowed) and all(flagged[n].startswith(allowed[n]) for n in flagged), flagged
