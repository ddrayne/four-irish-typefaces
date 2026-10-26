"""Carrick Study 3 (research/round-06): fifteen letters from the N514 production sheets, x and y from N513."""
import json, os
import numpy as np
import pytest
from conftest import study_coverage

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
        assert 0.96 < g['frame_lock']['scale'] < 1.04, n                   # inside the lock's search range
        lock = g['frame_lock']
        # the shape is the sheet's (its shared slant and stretch taken out, square to its marks), and the
        # letter stands on its marks' line: its foot within the builder's snap of the base's line
        assert set(lock['sheet_frame']) == {'turn_deg', 'stretch_ratio', 'shear_removed_deg'}, n
        assert lock['baseline']['source'] == "the sheet's spacing marks", n
        assert abs(lock['baseline']['foot_below_line']) < (9 if n in 'gj' else 1.0), n
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
    assert set(f.getBestCmap()) == study_coverage(TTFont(os.path.join(ROOT, 'fonts', 'otf', 'CarrickDigital-Regular.otf')))


# ---------------------------------------------------------------- the finishing pass (judged-edits.json)
def release(style='Regular'):
    from conftest import static
    from fontTools.ttLib import TTFont
    return TTFont(static('CarrickDigital', style))


def ink(font, name):
    import evidence_board as EB
    return EB.glyph_polygons(font, name)


def test_judged_edits_are_recorded_and_applied():
    from fontTools.pens.boundsPen import BoundsPen
    edits = load(ROUND, 'carrick', 'judged-edits.json')['edits']
    assert edits and all(e.get('op') and len(e.get('reason', '')) > 40 for e in edits)
    gs = release().getGlyphSet()
    def bottom(n):
        b = BoundsPen(gs); gs[n].draw(b); return round(b.bounds[1])
    assert [e['glyph'] for e in edits if e['op'] == 'cut_foot'] == ['f']
    # f's foot is a stem's cut like i's and l's: they sit on the baseline together, the rounds just below
    assert bottom('f') == bottom('i') == bottom('l') == bottom('n') == 0 and bottom('o') < 0


def test_the_lower_pair_is_the_diaeresis():
    from fontTools.pens.recordingPen import replayRecording
    from test_ceili_punctuation import origin_path, overlap
    data = load(ROUND, 'carrick', 'traces', 'pieces.json')
    pieces = {p['name']: p for p in data['pieces']}
    assert [r['name'] for r in data['unassigned']] == ['unassigned.inner-chevrons']
    assert data['assigned_by_judgement'][0]['assigned_to'] == ['dieresis.l', 'dieresis.r']
    for n in ('dieresis.l', 'dieresis.r'):
        assert pieces[n]['status'] == 'judged' and pieces[n]['source_id'] == 'N513', n
    font = release()
    def pair(pen):
        for n in ('dieresis.l', 'dieresis.r'):
            replayRecording(pieces[n]['rec'], pen)
    assert overlap(origin_path(pair), origin_path(font.getGlyphSet()['dieresis'].draw)) > .97
    # two dots, each the width of the set's own dot to within 15%, parted at their feet by about a third of one
    dots = sorted(ink(font, 'dieresis'), key=lambda p: p[:, 0].min())
    dot = ink(font, 'dotaccent')[0]; w = np.ptp(dot[:, 0])
    assert len(dots) == 2 and all(0.85 < np.ptp(d[:, 0]) / w < 1.15 for d in dots)
    gap = min(np.hypot(*(dots[0] - q).T).min() for q in dots[1])
    assert 0.25 * w < gap < 0.45 * w, gap


def counters(font, name, upx=2.0):
    """The inscribed diameter of each counter of a glyph, font units."""
    import evidence_board as EB
    from scipy import ndimage as ndi
    polys = ink(font, name)
    pts = np.vstack(polys); lo, hi = pts.min(0) - 10, pts.max(0) + 10
    m = EB.rasterise(polys, upx, (int((hi[1] - lo[1]) * upx), int((hi[0] - lo[0]) * upx)), np.array([lo[0], hi[1]]))
    bg, n = ndi.label(~m)
    edge = set(np.unique(np.r_[bg[0], bg[-1], bg[:, 0], bg[:, -1]]))
    return sorted(2 * ndi.distance_transform_edt(bg == i).max() / upx for i in range(1, n + 1)
                  if i not in edge and (bg == i).sum() > 4 * upx * upx)


@pytest.mark.parametrize('style,least', [('Regular', 18), ('Italic', 12)])
def test_small_figures_keep_their_counters(style, least):
    f = release(style)
    for name in ('onequarter', 'threequarters'):
        holes = counters(f, name)
        # one counter, the small 4's (11 and 5 units across before the finishing pass); the small 3's
        # lower bowl stays open in both styles
        assert len(holes) == 1 and holes[0] >= least, (name, holes)


def test_the_sloped_style_keeps_the_upright_drawing():
    """The Italic has the Regular's pieces and counters in every glyph, and about its nodes: its hair of
    extra weight moves the drawing's own nodes (bolden.grow_nodes) instead of a stroked offset, which
    left 61 nodes in the average sloped letter against the upright's 34."""
    import topo
    from conftest import static
    from fontTools.pens.recordingPen import RecordingPen
    assert topo.compare(static('CarrickDigital', 'Regular'), static('CarrickDigital', 'Italic')) == []
    def nodes(font):
        gs = font.getGlyphSet(); cm = font.getBestCmap(); n = 0
        for ch in 'abcdefghijklmnopqrstuvwxyz':
            r = RecordingPen(); gs[cm[ord(ch)]].draw(r)
            n += sum(op in ('lineTo', 'curveTo', 'qCurveTo') for op, _ in r.value)
        return n
    assert nodes(release('Italic')) < 1.25 * nodes(release('Regular'))


def test_outlines_are_settled_on_the_grid():
    """No stub of a segment, and the joins that rounding bent are smooth again (scripts/settle.py)."""
    import math, settle
    from fontTools.pens.recordingPen import RecordingPen
    font = release(); gs = font.getGlyphSet(); cm = font.getBestCmap()
    bent = joins = 0
    for ch in 'abcdefghijklmnopqrstuvwxyz0123456789':
        r = RecordingPen(); gs[cm[ord(ch)]].draw(r)
        for segs in settle._contours(r.value):
            for i in range(len(segs)):
                j = (i + 1) % len(segs)
                assert math.dist(settle._start(segs, i), segs[i][1][-1]) >= settle.TINY, (ch, segs[i])
                turn = settle._angle(settle._tin(segs, i), settle._tout(segs, j))
                joins += 1
                bent += 'C' in segs[i][0] + segs[j][0] and 1.5 < turn < settle.SMOOTH
    assert bent < 0.04 * joins, (bent, joins)          # 175 of 1209 joins before, 23 of 1184 after


# ---------------------------------------------------------------- the second finishing pass
def mask(font, name, upx=1.0, pad=50):
    import evidence_board as EB
    polys = ink(font, name)
    pts = np.vstack(polys); lo, hi = pts.min(0) - pad, pts.max(0) + pad
    shape = (int((hi[1] - lo[1]) * upx) + 1, int((hi[0] - lo[0]) * upx) + 1)
    return EB.rasterise(polys, upx, shape, np.array([lo[0], hi[1]])), (lo[0], hi[1])


def weight(font, name):
    """A glyph's stroke weight as the review measured it: twice the distance to the edge along its
    skeleton, the 75th percentile."""
    from scipy import ndimage as ndi
    from skimage.morphology import skeletonize
    m, _ = mask(font, name, pad=4)
    return 2 * np.percentile(ndi.distance_transform_edt(m)[skeletonize(m)], 75)


def topology(m):
    from scipy import ndimage as ndi
    lab, n = ndi.label(m, structure=np.ones((3, 3)))
    pieces = int((ndi.sum(m, lab, range(1, n + 1)) >= 3).sum())
    bg, k = ndi.label(~m); edge = set(np.unique(np.r_[bg[0], bg[-1], bg[:, 0], bg[:, -1]]))
    return pieces, sum(1 for i in range(1, k + 1) if i not in edge and (bg == i).sum() >= 3)


def cut(font, name, most=45.0):
    """The width of a glyph's narrowest cut: the smallest closing (in font units, at a unit a pixel) that
    joins two of its pieces or shuts or opens a counter."""
    from scipy import ndimage as ndi
    m, _ = mask(font, name)
    closed = lambda r: ndi.distance_transform_edt(ndi.distance_transform_edt(~m) <= r) > r
    t0 = topology(m)
    # the first change, scanned upwards: closings do not change a glyph's topology monotonically (a
    # ring's hole shuts as the ring joins the letter under it, which can restore the count)
    for r in np.arange(1.0, most / 2 + 1):
        if topology(closed(r)) != t0:
            lo, hi = r - 1, r
            while hi - lo > 0.25:
                mid = (lo + hi) / 2
                lo, hi = (lo, mid) if topology(closed(mid)) != t0 else (mid, hi)
            return 2 * hi
    return None


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_percent_and_numbersign_take_the_figures_weight(style):
    """% and ‰ are the face's own 0 made small with strokes about 0.6 of the figure stem, # has bars about
    half of it (all three were 0.39 of it: 68 to 70 units against the 1's 176)."""
    f = release(style); stem = weight(f, 'one')
    for name in ('percent', 'perthousand'):
        assert weight(f, name) >= 0.55 * stem, (name, weight(f, name), stem)
    assert 0.45 * stem <= weight(f, 'numbersign') <= 0.6 * stem
    # the zeros keep their counters, and the zeros and the slash stand apart
    for name, zeros in (('percent', 2), ('perthousand', 3)):
        m, _ = mask(f, name)
        assert topology(m) == (zeros + 1, zeros), name
        assert min(counters(f, name)) >= 0.15 * stem, name


def ponc(font, name):
    """A dotted letter's dot (its smallest piece) and the rest, as rasters at a unit a pixel."""
    from scipy import ndimage as ndi
    m, origin = mask(font, name)
    lab, n = ndi.label(m)
    dot = lab == 1 + int(np.argmin(ndi.sum(m, lab, range(1, n + 1))))
    return dot, m & ~dot, origin


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_the_ponc_stands_clear_of_the_ascender(style):
    """ḃ ḋ ḟ: the dot stood 45 to 47 units above the ascender, so that at 14 to 16 px ḃ and b, ḟ and f
    were hard to tell apart. Irish types set ḃ's ponc beside the ascender, over the bowl (Baoithín, Colum
    Cille, William Britain's 1963 drawings); ḋ's and ḟ's stand above theirs, at least 60 units clear."""
    from scipy import ndimage as ndi
    f = release(style); cm = f.getBestCmap()
    for ch in 'ḃḋḟ':
        dot, base, _ = ponc(f, cm[ord(ch)])
        assert ndi.distance_transform_edt(~base)[dot].min() >= 60, ch
    # ḃ's beside its ascender: below the ascender's top and right of its stem, at the dot's height
    dot, base, _ = ponc(f, cm[ord('ḃ')])
    rows = np.nonzero(dot.any(1))[0]
    assert base[:rows.max()].any(), 'the ascender rises above the foot of the dot'
    for r in rows[base[rows].any(1)]:
        assert np.nonzero(dot[r])[0].min() - np.nonzero(base[r])[0].max() >= 60, r


def test_the_italic_keeps_the_cuts():
    """The sloped style's hair of weight narrowed the cuts by half (@ and 9 from 14 to 6 units, ¢ from 16 to
    6, u from 20 to 10): nodes beside a cut stay where they are, so each keeps the Regular's width to
    within 2 units, the small change that narrowing and sloping the letter make."""
    R, I = release('Regular'), release('Italic'); cm = R.getBestCmap()
    for ch in '@9¢uamyk5e':
        a, b = cut(R, cm[ord(ch)]), cut(I, cm[ord(ch)])
        assert a is not None and b is not None and abs(a - b) <= 2.0, (ch, a, b)


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_the_cent_bar_leaves_the_counter_whole(style):
    """The ¢ bar crossed the c beside the narrow inner curve of its back and shut a lens of the counter off;
    it now stands at the back, so the c's counter stays one open space."""
    f = release(style)
    assert counters(f, 'cent') == counters(f, 'c') == []
    assert cut(f, 'cent') >= 16                         # the bar stands clear of the c's top terminal


def test_figures_share_one_figure_line():
    """N513 prints the figures' tops on one line (all but the 8 within two source pixels) and their feet at
    different depths; set on the baseline by their lowest points they stood from 517 (the 2) to 565 (the 5
    and 7) tall. A flat top meets the figure line, a cut or pointed one stands the round overshoot above it;
    the 8, drawn about 67 units taller on N513 and N47, keeps its height."""
    from fontTools.pens.boundsPen import BoundsPen
    spec = load(ROUND, 'carrick', 'judged-edits.json')['figures']
    line, over = spec['line'], spec['overshoot']
    for style in ('Regular', 'Italic'):
        gs = release(style).getGlyphSet()
        def b(n):
            p = BoundsPen(gs); gs[n].draw(p); return p.bounds
        for n in 'zero one two three four five six seven nine'.split():
            assert line - 2 <= b(n)[3] <= line + over + 2 and -10 <= b(n)[1] <= 0, (style, n, b(n))
        assert b('eight')[3] >= line + 55, style


# ---------------------------------------------------------------- the third finishing pass
def piece_whites(font, name):
    """A glyph's pieces at a unit a pixel, largest first, and the white between each pair of them."""
    from scipy import ndimage as ndi
    m, _ = mask(font, name)
    lab, n = ndi.label(m, structure=np.ones((3, 3)))
    order = sorted(range(1, n + 1), key=lambda i: -np.ptp(np.nonzero(lab == i)[1]))
    whites = {}
    for a in order:
        d = ndi.distance_transform_edt(lab != a)
        for b in order:
            if b != a and (b, a) not in whites:
                whites[a, b] = float(d[lab == b].min())
    return lab, order, whites


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_rings_take_the_figures_weight(style):
    """¤'s ring and arms and @'s ring at about 0.55 to 0.6 of the figure stem, the family of % and # (they were
    0.26 to 0.32: 46 to 56 units against the 1's 176); @'s a keeps the white it had inside the ring (26). The fifth
    pass sets every ring of the four faces at least half the o's heavier side (223): Carrick's go from 106 to 113,
    0.64 of the figure stem, ¤'s arms with them (tests/test_fifth_pass.py)."""
    from scipy import ndimage as ndi
    from skimage.morphology import skeletonize
    f = release(style); stem = weight(f, 'one')
    assert 0.55 * stem <= weight(f, 'currency') <= 0.67 * stem
    assert len(counters(f, 'currency')) == 1 and counters(f, 'currency')[0] >= stem
    lab, order, whites = piece_whites(f, 'at')
    ring = lab == order[0]
    w = 2 * np.median(ndi.distance_transform_edt(ring)[skeletonize(ring)])
    assert 0.55 * stem <= w <= 0.67 * stem, w
    assert len(order) == 2 and 24 <= whites[order[0], order[1]] <= 30, whites


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_the_trademark_m_keeps_its_cuts(style):
    """™'s small m: its strokes stood 1.4 units apart in the Regular and 2 in the Italic (the other pair had
    joined), a hairline that fills in; it is drawn from the m's own three pieces, at least 12 apart."""
    lab, order, whites = piece_whites(release(style), 'trademark')
    assert len(order) == 4, len(order)                       # the T and the m's three pieces
    m = sorted(order, key=lambda i: np.nonzero(lab == i)[1].min())[1:]
    for a, b in zip(m, m[1:]):
        assert whites.get((a, b), whites.get((b, a))) >= 12, (style, whites)


# ---------------------------------------------------------------- the fourth finishing pass
def outline(font, name, unslant=False):
    """A glyph's outline as a pathops path; with `unslant`, the Italic's slope taken out (about the middle of the
    x-height, as build2.Font2.slant slopes it)."""
    import math, pathops, build2
    from fontTools.pens.transformPen import TransformPen
    p = pathops.Path(); pen = p.getPen()
    if unslant and font['post'].italicAngle:
        t = math.tan(math.radians(build2.SLANT)); yc = font['OS/2'].sxHeight / 2
        pen = TransformPen(pen, (1, 0, -t, 1, yc * t, 0))
    font.getGlyphSet()[name].draw(pen)
    return pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)


def body_bounds(font, name):
    """The bounds of a currency sign's body (the $'s): the ink beside the bar that alone reaches the top and foot,
    less any sliver where the bar flares."""
    from scipy import ndimage as ndi
    import tuam_studio
    m, x0, y1 = tuam_studio.ink_raster(outline(font, name, unslant=True))      # the Italic's bar upright again
    rows = np.nonzero(m.any(1))[0]
    cols = np.nonzero(m[rows[:30]].any(0) | m[rows[-30:]].any(0))[0]
    side = m.copy(); side[:, max(cols.min() - 6, 0):cols.max() + 7] = False
    lab, n = ndi.label(side)
    big = np.isin(lab, [i for i in range(1, n + 1) if (lab == i).sum() >= 0.02 * m.sum()])
    r = np.nonzero(big.any(1))[0]
    return y1 - r.max() - 0.5, y1 - r.min() - 0.5


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_currency_signs_stand_on_the_baseline(style):
    """£ floated 29 units above the baseline (29 to 647) and the S of $ 36 above it (36 to 607): each now stands on the
    baseline as a figure does, £'s flat foot on it and the S's cut foot 8 below, at the heights N513 prints them (as
    tall as its & ? !, not the figures): the drawings only move, so £ is 618 tall, the S 571 and the $ with its bar 806,
    and the line box still covers the bar. € and ¥ stand on the figure line (¢ is the c with its bar)."""
    from fontTools.pens.boundsPen import BoundsPen
    spec = load(ROUND, 'carrick', 'judged-edits.json')['figures']
    line, over = spec['line'], spec['overshoot']
    f = release(style); gs = f.getGlyphSet()
    def b(n):
        p = BoundsPen(gs); gs[n].draw(p); return p.bounds
    for n in ('Euro', 'yen'):
        assert -over - 2 <= b(n)[1] <= 1 and line - 2 <= b(n)[3] <= line + over + 2, (style, n, b(n))
    pound = b('sterling')
    assert -1 <= pound[1] <= 1 and pound[3] - pound[1] == pytest.approx(618, abs=2), (style, pound)
    lo, hi = body_bounds(f, 'dollar')
    assert -over - 2 <= lo <= -over + 2 and hi - lo == pytest.approx(571, abs=4), (style, lo, hi)
    dollar = b('dollar')
    assert dollar[3] - dollar[1] == pytest.approx(806, abs=2) and dollar[1] < lo - 90, (style, dollar)
    assert f['hhea'].descent <= dollar[1] and f['hhea'].ascent >= dollar[3]
    # £'s foot (its lower piece) as thick as it was drawn (110 to 119 units), and the cut between them as it was (26)
    lab, order, whites = piece_whites(f, 'sterling')
    assert len(order) == 2 and min(whites.values()) >= 24, whites
    foot = max(order, key=lambda i: np.nonzero(lab == i)[0].mean())          # lowest on the raster
    cols = (lab == foot).sum(0); cols = cols[cols > 0]
    assert np.percentile(cols, 75) >= 110, np.percentile(cols, 75)


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_guillemets_are_one_drawing_turned_about(style):
    """« and » were drawn from two different chevrons of the sheet (189 by 322 units, advance 432, against 166 by 311,
    advance 388; ‹ 265 against › 242): each pair is now the sheet's ‹ chevron and its mirror image, so the two have one
    advance, one pair of sidebearings and the same outline turned about (the Italic's, with its slope taken out, to
    within 2.5% of its ink: the hair of weight the sloped style adds holds by the slit between the two chevrons, which
    the slope narrows on one side and widens on the other; the two pairs differed by 35 to 52%)."""
    import pathops
    from fontTools.pens.transformPen import TransformPen
    from glyphs import bounds
    f = release(style); hm = f['hmtx']
    for left, right in (('guillemotleft', 'guillemotright'), ('guilsinglleft', 'guilsinglright')):
        assert hm[left][0] == hm[right][0], (left, hm[left][0], hm[right][0])
        a, b = outline(f, left, unslant=True), outline(f, right, unslant=True)
        mirrored = pathops.Path(); b.draw(TransformPen(mirrored.getPen(), (-1, 0, 0, 1, hm[right][0], 0)))
        apart = pathops.op(a, mirrored, pathops.PathOp.XOR, fix_winding=True)
        assert abs(apart.area) <= (0.01 if style == 'Regular' else 0.025) * abs(a.area), (left, abs(apart.area) / abs(a.area))
        ba = bounds(a)
        assert abs(ba[0] - (hm[left][0] - ba[2])) <= 1.5 or style == 'Italic', (left, ba, hm[left][0])
    # the drawing of ‹, not ›'s narrower one
    s = bounds(outline(f, 'guilsinglleft', unslant=True))
    assert s[2] - s[0] >= 175 and s[3] - s[1] >= 315, s


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_f_stands_a_cut_from_the_next_ascender(style):
    """f's flag came within 9 to 14 units of the next ascender (fh fl fb fk, after kerns of +55 to +80), where the face's
    own ascenders stand 15 to 18 apart (lb, ll): above the x-height every pair now stands at least Carrick's cut (13.5,
    the third pass's cut for ™'s strokes) apart, as Tuam's stand its own, f before the accented and dotted ascenders too.
    ll and lb keep their spacing."""
    import uharfbuzz as hb
    from scipy.ndimage import minimum_filter1d
    from study_spacing import silhouette
    from conftest import static
    clearance = load(ROUND, 'carrick', 'judged-edits.json')['kerning']['upper_clearance']
    f = release(style); order = f.getGlyphOrder(); cm = f.getBestCmap(); hm = f['hmtx']
    font = hb.Font(hb.Face(open(static('CarrickDigital', style), 'rb').read()))
    xh = f['OS/2'].sxHeight
    ys = np.arange(xh + 0.5, 1100, 1.0)
    def gap(text):
        buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties(); hb.shape(font, buf, {})
        (ga, gb), pa = [order[i.codepoint] for i in buf.glyph_infos], buf.glyph_positions[0]
        right = silhouette(outline(f, ga), ys)[1]
        left = minimum_filter1d(silhouette(outline(f, gb), ys)[0], size=5, mode='constant', cval=np.inf)
        return float(np.min(pa.x_advance + left - right)), pa.x_advance - hm[ga][0]
    for a in 'fḟ':
        for b in 'hlbkdḃḋḟĺľļŀłíìîïĩĵ':
            g, k = gap(a + b)
            assert g >= clearance - 1, (style, a + b, g, k)
    assert gap('ll')[1] == gap('lb')[1] == 0


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_straight_quotes_match_the_curly_quotes(style):
    """' and " stood 140 units tall and 110 wide with 0.68 of the ink of ’ (198 by 139), so they set small and grey
    beside it: the builder's wedge drawn to the curly quotes' depth, its widths at its top and foot (its taper from the
    period) kept, its top on the quotes' line, so that it carries at least 0.85 of ’'s ink and no more than ’."""
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.areaPen import AreaPen
    f = release(style); gs = f.getGlyphSet()
    def b(n):
        p = BoundsPen(gs); gs[n].draw(p); return p.bounds
    def area(n):
        p = AreaPen(gs); gs[n].draw(p); return abs(p.value)
    q, curly = b('quotesingle'), b('quoteright')
    assert abs((q[3] - q[1]) - (curly[3] - curly[1])) <= 2 and abs(q[3] - curly[3]) <= 1, (q, curly)
    assert 0.85 <= area('quotesingle') / area('quoteright') <= 1.0, area('quotesingle') / area('quoteright')
    assert area('quotedbl') == pytest.approx(2 * area('quotesingle'), rel=0.01)
    assert len(piece_whites(f, 'quotedbl')[1]) == 2
    assert abs((b('minute')[3] - b('minute')[1]) - (q[3] - q[1])) <= 2          # the primes follow
    if style == 'Regular':
        # the builder's taper: 0.8 of the period's half width at the top, 0.35 at the foot
        hw = (b('period')[2] - b('period')[0]) / 2
        m, _ = mask(f, 'quotesingle', pad=0)
        rows = np.nonzero(m.any(1))[0]
        width = lambda r: np.ptp(np.nonzero(m[r])[0]) + 1
        assert width(rows[2]) == pytest.approx(1.6 * hw, abs=4) and width(rows[-3]) == pytest.approx(0.7 * hw, abs=6)
