"""Tuam Uncial Study 3 (research/tuam-judgement), the tools it uses, and the release's finishing pass."""
import json, os
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUND = os.environ.get('TUAM_JUDGEMENT_DIR', os.path.join(ROOT, 'research', 'tuam-judgement'))
STEM = 'TuamUncialStudy3'
ACCENTED = {'aacute', 'eacute', 'iacute', 'oacute', 'uacute'}      # recomposed by the builder
N46, N45 = 'competition-advert-1.jpg', 'competition-brochure-2.jpg'


def load(*parts):
    return json.load(open(os.path.join(*parts), encoding='utf-8'))


def evidence():
    return load(ROUND, 'traces', 'evidence.json')


def font(ext='otf'):
    return os.path.join(ROUND, 'fonts', f'{STEM}-Regular.{ext}')


def topology_of(path, name):
    import topo
    from fontTools.ttLib import TTFont
    pieces, holes = topo.topology(topo.shape(TTFont(path).getGlyphSet(), name))
    return [pieces, len(holes)]


# ---------------------------------------------------------------- the tools
def test_fix_topology_opens_the_clean_prints_cut_and_fills_a_pinhole():
    import consensus_trace as C
    clean = np.zeros((40, 60)); clean[10:30, 5:28] = 1; clean[10:30, 30:55] = 1       # two strokes, cut apart
    clean[10:30, 28:30] = 0.2
    blurred = clean.copy(); blurred[10:30, 28:30] = 1.0                                 # the blurred print fills it
    mean = 0.5 * (clean + blurred)
    assert C.contour_topology(mean) != (2, 0)
    fixed, steps = C.fix_topology(mean, clean, [2, 0])
    assert C.contour_topology(fixed) == (2, 0) and steps[0]['op'] == 'open'
    assert np.array_equal(fixed[:, :27] > 0.5, mean[:, :27] > 0.5)                     # nothing else moves
    solid = clean.copy(); solid[10:30, 28:30] = 1                                       # one stroke
    holed = solid.copy(); holed[18:22, 12:16] = 0                                       # one print's pinhole
    assert C.contour_topology(holed) == (1, 1)
    fixed, steps = C.fix_topology(holed, solid, [1, 0])
    assert C.contour_topology(fixed) == (1, 0) and steps[0]['op'] == 'fill'


def test_register_recovers_a_uniform_scale_and_shift():
    import consensus_trace as C
    from scipy import ndimage as ndi
    ref = np.zeros((60, 60)); ref[15:45, 20:30] = 1; ref[15:22, 20:45] = 1
    ref = ndi.gaussian_filter(ref, 0.8)
    s, shift = 0.85, (1.5, -2.0)
    mov = C.warp(ref, (55, 55), np.array([30.0, 30.0]), np.array([27.0, 27.0]), 1 / s, 0.0, (0.0, 0.0))
    mov = ndi.shift(mov, shift, order=1)
    r = C.register(ref, mov, 0.85)
    assert r['scale'] == pytest.approx(s, abs=0.01) and r['ncc'] > 0.98


def test_pointed_brace_has_a_point_beyond_its_stems_and_a_full_waist():
    import symbols, evidence_board as EB
    from fontTools.pens.recordingPen import RecordingPen
    import pathops
    w = 136.0
    p = symbols.pointed_brace(800, -200, w, w + 2)
    rec = RecordingPen(); p.draw(rec)
    assert sum(op == 'closePath' for op, _ in rec.value) == 1
    from glyphs import bounds
    x0, y0, x1, y1 = bounds(p)
    assert x0 == pytest.approx(-0.55 * w, abs=1)                     # the point juts beyond the stems
    # the waist, cut horizontally anywhere, is at least the stroke wide
    import shapes as SH
    for y in np.linspace(250, 350, 11):
        cut = SH.op(p, SH.polygon([(-500, y - 0.5), (500, y - 0.5), (500, y + 0.5), (-500, y + 0.5)]),
                    pathops.PathOp.INTERSECTION)
        b = bounds(cut)
        assert b[2] - b[0] >= w - 1, y


def test_release_constructions_stay_off():
    import build2
    assert build2.Font2.OWN_ACUTES == () and build2.Font2.BRACE_POINT is False
    for d in ('round-03/tuam', 'round-04/ceili', 'round-06/carrick', 'kilfane-judgement'):
        assert 'constructions' not in load(ROOT, 'research', d, 'traces', 'evidence.json'), d


# ---------------------------------------------------------------- the study
def test_study3_records_both_prints_and_one_transform():
    ev = evidence()
    hashes = {os.path.basename(a['path']): a['sha256'] for a in load(ROOT, 'research', 'downloads.json')['assets']}
    assert ev['source_hashes'] == {N46: hashes[N46], N45: hashes[N45]}
    glyphs = [g for g in ev['glyphs'] if g['status'] == 'candidate']
    assert len(glyphs) == 46 and all(g['method'] == 'consensus' for g in glyphs)
    t = ev['shared_transform']
    for g in glyphs:
        assert g['source'] == N46 and g['check']['source'] == N45 and len(g['box']) == len(g['check']['box']) == 4
        assert g['check']['transform']['scale'] == t['scale'] and g['check']['transform']['rotation_deg'] == t['rotation_deg']
        assert g['topology']['decision'] and g['uncertainty_font_units'] < 15
    assert 0.83 < t['scale'] < 0.88 and abs(t['rotation_deg']) < 1


def test_study3_topology_decisions():
    ev = {g['name']: g for g in evidence()['glyphs']}
    import consensus_trace as C
    for n, (target, _) in C.TOPOLOGY.items():
        assert ev[n]['topology']['decided'] == target, n
        assert ev[n]['topology']['prints']['N46'] != ev[n]['topology']['prints']['N45'], n   # decided only where they differ
    # the cuts and slits N45 and the production sheet show, against round 3's N46 traces
    want = {'d': [1, 0], 'f': [2, 0], 'h': [2, 0], 'p': [1, 0], 'q': [1, 0], 'r': [2, 0], 's': [1, 0], 'u': [2, 0],
            'v': [2, 0], 'w': [3, 0], 'five': [2, 0], 'six': [1, 0], 'dollar': [1, 2],
            # attested on both prints, kept
            'a': [1, 0], 'o': [1, 0], 'zero': [1, 0], 'eight': [1, 1], 'nine': [1, 0], 'e': [1, 1], 'n': [2, 0], 'm': [3, 0]}
    assert {n: ev[n]['topology']['decided'] for n in want} == want


@pytest.mark.parametrize('ext', ['otf', 'ttf'])
def test_study3_binaries_keep_the_decided_topology(ext):
    for g in evidence()['glyphs']:
        if g['status'] == 'candidate' and g['name'] not in ACCENTED:
            assert topology_of(font(ext), g['name']) == g['topology']['decided'], g['name']


def test_sheet_check_records_the_production_sheets_cuts():
    r = load(ROUND, 'sheet-check.json')
    assert r['image']['sha256'] == '2ea8c4401b68e2435b080cb37d976347086f1acc404da5194b1488ef50b8b8aa'
    L = r['letters']
    for n in ('n', 'h', 'f', 'u'):
        assert set(L[n]['pieces']) == {'2'} and L[n]['pieces']['2'] >= 7, n
    assert L['r']['pieces'].get('2', 0) > L['r']['pieces'].get('1', 0)
    assert set(L['x']['pieces']) == {'1'} and set(L['e']['pieces']) == {'1'}


@pytest.mark.parametrize('ext', ['otf', 'ttf'])
def test_study3_braces_are_one_piece_with_a_point(ext):
    import pinches, evidence_board as EB
    from fontTools.ttLib import TTFont
    f = TTFont(font(ext))
    for n in ('braceleft', 'braceright'):
        assert topology_of(font(ext), n) == [1, 0], n
        polys = EB.glyph_polygons(f, n)
        assert not pinches.pinches(polys, 224, ratio=0.4), n
    # braceleft's point is its leftmost ink, at mid-height
    pts = np.vstack(EB.glyph_polygons(f, 'braceleft'))
    tip = pts[np.argmin(pts[:, 0])]
    assert abs(tip[1] - (pts[:, 1].max() + pts[:, 1].min()) / 2) < 40


def test_study3_fadas_are_the_prints_and_shape_the_same_decomposed():
    import uharfbuzz as hb, unicodedata
    from fontTools.ttLib import TTFont
    from glyphs import bounds, contours
    import pathops
    f = TTFont(font()); order = f.getGlyphOrder(); gs = f.getGlyphSet()
    face = hb.Face(open(font(), 'rb').read()); hf = hb.Font(face)

    def names(text):
        buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties(); hb.shape(hf, buf, {})
        return [order[i.codepoint] for i in buf.glyph_infos]
    for ch, n in zip('áéíóú', ['aacute', 'eacute', 'iacute', 'oacute', 'uacute']):
        assert names(ch) == [n] and names(unicodedata.normalize('NFD', ch)) == [n], ch
        assert names(ch.upper()) == [n] and names(unicodedata.normalize('NFD', ch.upper())) == [n], ch

    def acute_width(n):
        p = pathops.Path(); gs[n].draw(p.getPen())
        top = max(contours(p), key=lambda c: bounds(c)[3]); b = bounds(top)
        return b[2] - b[0]
    assert acute_width('iacute') < 0.75 * acute_width('uacute')     # í's own short fada
    prov = load(ROUND, 'fonts', f'{STEM}-Regular.provenance.json')
    assert all('as printed on' in prov[n][1] for n in ACCENTED)


@pytest.mark.parametrize('ext', ['otf', 'ttf', 'woff', 'woff2'])
def test_study3_fonts_sanitise_and_keep_the_release_coverage(ext):
    import ots
    from fontTools.ttLib import TTFont
    p = font(ext)
    assert ots.sanitize(p, os.devnull, capture_output=True).returncode == 0
    f = TTFont(p)
    assert f['name'].getDebugName(1) == 'Tuam Uncial Study 3' and f['name'].getDebugName(6) == f'{STEM}-Regular'
    assert f.getBestCmap().keys() == TTFont(os.path.join(ROOT, 'fonts', 'otf', 'TuamUncialDigital-Regular.otf')).getBestCmap().keys()


@pytest.mark.parametrize('ext', ['otf', 'ttf'])
def test_study3_all_latin_pairs(ext):
    from audit_font_pairs import audit_font_pairs
    result = audit_font_pairs(font(ext))
    assert result['pairs_tested'] > 70000 and result['skipped_non_pair_shaping'] == 0
    assert result['collisions'] == 0, result['worst']


# ---------------------------------------------------------------- the finishing pass, in the release (judged-edits.json)
def release(style='Regular', ext='otf'):
    from conftest import static
    return static('TuamUncialDigital', style, ext)


def outline(path, name):
    import pathops
    from fontTools.ttLib import TTFont
    p = pathops.Path(); TTFont(path).getGlyphSet()[name].draw(p.getPen())
    return pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)


def piece_gaps(p):
    """The narrowest white between each pair of a glyph's pieces, narrowest first."""
    import bolden, tuam_studio as T
    from scipy.spatial import cKDTree
    pts = [T.samples(T.contours(c), 1.0)[0] for c in bolden.components(p)]
    return sorted(float(cKDTree(pts[j]).query(pts[i])[0].min()) for i in range(len(pts)) for j in range(i + 1, len(pts)))


def test_studio_operations_set_what_they_state():
    import tuam_studio as T, shapes as SH
    from glyphs import bounds
    stem = SH.polygon([(0, 0), (200, 0), (200, 500), (0, 500)])
    p, was = T.stem(stem, (100, 250), 220)
    assert was == pytest.approx(200, abs=0.5) and bounds(p)[2] - bounds(p)[0] == pytest.approx(220, abs=0.5)
    # a spur (a wedge pointing at a stem 40 units away) is brought to 28 at its tip; its far end stays put
    wedge = SH.polygon([(240, 300), (500, 360), (500, 240)])
    p, was = T.spur(SH.union(stem, wedge), (240, 300), 28)
    assert was == pytest.approx(40, abs=0.5) and piece_gaps(p)[0] == pytest.approx(28, abs=0.5)
    assert bounds(p)[2] == pytest.approx(500, abs=0.5)
    # a blunt end drawn as one point where its sides meet
    blunt = SH.polygon([(100, 0), (300, 40), (300, 60), (100, 100)])
    p, _ = T.point(blunt, (300, 50), 15)
    assert bounds(p)[2] == pytest.approx(350, abs=0.5) and len(T.contours(p)[0][1]) == 3


def test_finishing_edits_are_recorded():
    doc = load(ROUND, 'judged-edits.json')
    names = {g['name'] for g in evidence()['glyphs']}
    ops = {'height', 'level', 'stem_top', 'stem', 'point', 'smooth', 'spur', 'cut', 'dot'}
    assert all(e['op'] in ops and e['glyph'] in names for e in doc['edits'])
    assert all(any('why' in e for e in doc['edits'] if e['op'] == op) for op in {e['op'] for e in doc['edits']})
    assert all(c['why'] for c in doc['constructions'].values())
    # the edits to glyphs made from the traced ones (the section sign), each kind with its reason
    from fontTools.ttLib import TTFont
    made = set(TTFont(release()).getGlyphOrder())
    assert doc['derived'] and all(e['op'] in {'smooth', 'point', 'settle'} and e['glyph'] in made for e in doc['derived'])
    assert all(any('why' in e for e in doc['derived'] if e['op'] == op) for op in {e['op'] for e in doc['derived']})


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_release_keeps_the_decided_topology(style):
    for g in evidence()['glyphs']:
        if g['status'] == 'candidate' and g['name'] not in ACCENTED:
            assert topology_of(release(style), g['name']) == g['topology']['decided'], g['name']


def test_release_italic_keeps_every_piece_and_counter():
    import topo
    assert not topo.compare(release('Regular'), release('Italic'), small=0.35)


@pytest.mark.parametrize('ext', ['otf', 'ttf'])
def test_release_cuts_stems_and_dots_are_even(ext):
    import tuam_studio as T
    p = release('Regular', ext)
    for n in ('n', 'h', 'r', 'u', 'y', 'f'):
        assert piece_gaps(outline(p, n))[0] == pytest.approx(28, abs=1.5), n
    assert piece_gaps(outline(p, 'm'))[:2] == pytest.approx([28, 28], abs=1.5)
    assert piece_gaps(outline(p, 'v'))[0] == pytest.approx(15, abs=2)
    assert piece_gaps(outline(p, 'w'))[:2] == pytest.approx([15, 15], abs=2)
    assert piece_gaps(outline(p, 'five'))[0] == pytest.approx(21, abs=2)
    for n in ('i', 'j', 'exclam', 'question'):
        assert piece_gaps(outline(p, n))[0] == pytest.approx(40, abs=1.5), n
    stems = {'n': [0, 1], 'm': [0, 1, 2], 'h': [0, 1], 'u': [0, 1], 'y': [0, 1], 'i': [0], 'j': [0], 'l': [0],
             'r': [0], 'b': [0], 'p': [0], 'q': [1], 'a': [1], 'g': [1]}
    for n, which in stems.items():
        runs = T.runs_at(outline(p, n), 300)
        assert [round(runs[k][1] - runs[k][0]) for k in which] == pytest.approx([220] * len(which), abs=2.5), n
    at = piece_gaps(outline(p, 'at'))
    assert len(at) == 1 and at[0] > 25                                     # the a stands clear inside the ring


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_release_all_latin_pairs(style):
    from audit_font_pairs import audit_font_pairs
    result = audit_font_pairs(release(style))
    assert result['pairs_tested'] > 70000 and result['collisions'] == 0, result['worst']


def test_release_flat_tops_sit_on_the_x_height():
    """Each letter's flat top (the longest level stretch near the x-height, within 2.5 units) is on it, and every
    other stretch level over 80 units is within 3 of it."""
    import tuam_studio as T
    from fontTools.ttLib import TTFont
    p = release(); xh = TTFont(p)['OS/2'].sxHeight
    for n in 'abcdeghmnopqrsuvwyz':
        q = outline(p, n); x0, _, x1, _ = T.bounds(q)
        tops = [T.level_of(q, x, x, 'top') for x in np.arange(x0 + 2, x1 - 2, 4)]
        runs, cur = [], []
        for t in tops:
            if xh - 25 < t < xh + 10 and (not cur or max(cur + [t]) - min(cur + [t]) <= 2.5):
                cur.append(t); continue
            runs.append(cur); cur = [t] if xh - 25 < t < xh + 10 else []
        runs = sorted((r for r in runs + [cur] if len(r) >= 10), key=len, reverse=True)
        assert runs and abs(np.median(runs[0]) - xh) <= 2, (n, [round(np.median(r)) for r in runs])
        assert all(abs(np.median(r) - xh) <= 3 for r in runs if len(r) >= 20), (n, [round(np.median(r)) for r in runs])


# ---------------------------------------------------------------- the second finishing pass, in the release
def pieces_of(path, name):
    """A glyph's pieces, lowest first."""
    import bolden
    from glyphs import bounds
    return sorted(bolden.components(outline(path, name)), key=lambda c: bounds(c)[1])


def white(a, b):
    import tuam_studio as T
    from scipy.spatial import cKDTree
    return float(cKDTree(T.samples(T.contours(b), 1.0)[0]).query(T.samples(T.contours(a), 1.0)[0])[0].min())


def renders(path, name, px):
    """FreeType renders of a glyph at four horizontal phases (antialiased, unhinted), each on its own canvas."""
    freetype = pytest.importorskip('freetype')
    out = []
    for phase in (0.0, 0.25, 0.5, 0.75):
        face = freetype.Face(path); face.set_char_size(int(px * 64))
        face.set_transform(freetype.Matrix(65536, 0, 0, 65536), freetype.Vector(int(phase * 64), 0))
        face.load_glyph(face.get_name_index(name.encode()), freetype.FT_LOAD_NO_HINTING | freetype.FT_LOAD_RENDER)
        bm = face.glyph.bitmap
        a = np.array(bm.buffer, float).reshape(bm.rows, bm.pitch)[:, :bm.width] / 255 if bm.rows else np.zeros((0, 0))
        can = np.zeros((3 * px, 3 * px)); y0, x0 = 2 * px - face.glyph.bitmap_top, px // 2 + face.glyph.bitmap_left
        can[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] = a
        out.append(can)
    return out


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_release_iacute_is_told_from_i_at_text_sizes(style):
    """The acute of í is its traced short wedge drawn steeper (judged-edits.json, iacute_rise): it rises well above the
    dot of i, and at 14 to 20 px the two render at least as differently as í and i do in Liberation Serif, the least
    distinct of DejaVu Sans, DejaVu Serif and Liberation Serif measured the same way (the renders blurred by half a
    pixel, their summed difference over the marks' ink: 0.55, 0.58, 0.69, 0.73). The first pass rendered 0.18 to 0.30."""
    import bolden
    from glyphs import bounds
    from scipy import ndimage as ndi
    p = release(style)
    acute, dot = pieces_of(p, 'iacute')[-1], pieces_of(p, 'i')[-1]
    (a0, b0, a1, b1), (c0, d0, c1, d1) = bounds(acute), bounds(dot)
    assert b1 - b0 >= 1.8 * (d1 - d0) and b1 >= d1 + 80, (bounds(acute), bounds(dot))
    shared = bounds(pieces_of(p, 'uacute')[-1])
    assert a1 - a0 < 0.8 * (shared[2] - shared[0])         # still the short acute the prints set on i
    ink = (abs(bolden.area(acute)) + abs(bolden.area(dot))) / 2
    for px, least in ((14, 0.55), (16, 0.58), (18, 0.69), (20, 0.73)):
        s = px / 1000
        diff = min(np.abs(ndi.gaussian_filter(A, 0.5) - ndi.gaussian_filter(B, 0.5)).sum() / (ink * s * s)
                   for A, B in zip(renders(p, 'i', px), renders(p, 'iacute', px)))
        assert diff >= least, (px, round(diff, 3))


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_release_ponc_stands_clear_of_the_ascenders(style):
    """ḃ and ḋ carry the ponc beside the ascender over the bowl, as Hayes letters ḃ in this face (Bolger fig. 204),
    centred on the ascender's height above the x-height, well clear of the ascender and the bowl; ḟ's stands 60
    above the stem. At 14 to 20 px each renders as a piece of its own (at half ink), where at 14 px all three merged."""
    import shapes as SH, pathops
    from glyphs import bounds
    from scipy import ndimage as ndi
    p = release(style)
    for name, base in (('uni1E03', 'b'), ('uni1E0B', 'd')):
        dot = pieces_of(p, name)[-1]; body = outline(p, base)
        cut = lambda y0, y1: SH.op(body, SH.polygon([(-1e4, y0), (1e4, y0), (1e4, y1), (-1e4, y1)]), pathops.PathOp.INTERSECTION)
        asc, bowl = cut(545, 1e4), cut(-1e4, 545)
        assert abs((bounds(dot)[1] + bounds(dot)[3]) / 2 - (544 + 776) / 2) <= 15, (name, bounds(dot))
        assert white(asc, dot) >= 60 and white(bowl, dot) >= 55, (name, round(white(asc, dot), 1), round(white(bowl, dot), 1))
    stem, flag, dot = pieces_of(p, 'uni1E1F')
    assert white(stem, dot) >= 58
    count = lambda A: ndi.label(A >= 0.5, structure=np.ones((3, 3)))[1]
    for name, base in (('uni1E03', 'b'), ('uni1E0B', 'd'), ('uni1E1F', 'f')):
        for px in (14, 16, 18, 20):
            apart = sum(count(B) > count(A) for A, B in zip(renders(p, base, px), renders(p, name, px)))
            assert apart >= 3, (name, px, apart)


def skeleton_weight(p):
    """The stroke weight the review measured: twice the distance to the edge along the skeleton, its 75th percentile."""
    pytest.importorskip('skimage')
    from skimage.morphology import skeletonize
    from scipy import ndimage as ndi
    import tuam_studio as T
    m, _, _ = T.ink_raster(p)
    return float(np.percentile(2 * ndi.distance_transform_edt(m)[skeletonize(m)], 75))


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_release_quotes_carry_the_faces_weight(style):
    """The comma, and the quotes and apostrophe made from it, with a tail about 120 thick (the first pass 78 to 85)."""
    p = release(style)
    for n in ('comma', 'quoteright', 'quoteleft', 'quotedblright', 'quotesinglbase'):
        assert 112 <= skeleton_weight(outline(p, n)) <= 135, n
    assert len(pieces_of(p, 'quoteright')) == 1


def drawn(path, name):
    """A glyph's outline as the font stores it (not simplified)."""
    import pathops
    from fontTools.ttLib import TTFont
    p = pathops.Path(); TTFont(path).getGlyphSet()[name].draw(p.getPen())
    return p


def joins(p, short=8.0):
    """(pieces under `short` units, joins bending 3 to 25 degrees) of an outline, as the first pass counted them (a
    piece's length along its control points)."""
    import math, tuam_studio as T
    shorts = bent = 0
    for start, segs in T.contours(p):
        ends = [start] + [q[-1] for _, q in segs]
        shorts += sum(sum(math.dist(*pp) for pp in zip([ends[i]] + q[:-1], q)) < short for i, (_, q) in enumerate(segs))
        for i, (k, q) in enumerate(segs):
            k2, q2 = segs[(i + 1) % len(segs)]; e = q[-1]
            a = next((v for v in ([q[-2], q[0]] if k == 'C' else []) + [ends[i]] if math.dist(v, e) > 0.01), ends[i])
            b = next((v for v in ([q2[0], q2[1]] if k2 == 'C' else []) + [q2[-1]] if math.dist(v, e) > 0.01), q2[-1])
            u, w = (e[0] - a[0], e[1] - a[1]), (b[0] - e[0], b[1] - e[1])
            d = abs(math.degrees(math.atan2(u[0] * w[1] - u[1] * w[0], u[0] * w[0] + u[1] * w[1])))
            bent += 3 < d < 25
    return shorts, bent


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_release_section_sign_is_drawn_in_continuous_curves(style):
    """Where the two s of the section sign meet, continuous curves (the first pass: a 76 degree corner on pieces of 2
    to 8 units and stubs at the counters' tips, 11 pieces under 8 units in all)."""
    shorts, bent = joins(drawn(release(style), 'section'))
    assert shorts == 0 and bent <= 4, (shorts, bent)


TRACED41 = list('abcdefghijklmnopqrstuvwxyz') + ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
                                                 'zero', 'sterling', 'dollar', 'ampersand', 'question', 'exclam']


def test_release_italic_has_the_regulars_weight():
    """The Italic narrowed and given its weight back on the stems' and bowls' edges (the first pass: stems 210 to 213
    against 220, o 207 against 216), every cut, slit and seam kept as wide as the first pass had it."""
    import tuam_studio as T
    reg, it = release('Regular'), release('Italic')
    stems = {'n': [0, 1], 'm': [0, 1, 2], 'h': [0, 1], 'u': [0, 1], 'y': [0, 1], 'i': [0], 'j': [0], 'l': [0],
             'r': [0], 'b': [0], 'p': [0], 'q': [1], 'a': [1], 'g': [1]}
    for n, which in stems.items():
        for p in (reg, it):
            runs = T.runs_at(outline(p, n), 300)
            assert [round(runs[k][1] - runs[k][0]) for k in which] == pytest.approx([220] * len(which), abs=2.5), (p, n)
    bowl = lambda p: [b - a for a, b in T.runs_at(outline(p, 'o'), 272)]
    assert bowl(it) == pytest.approx(bowl(reg), abs=2)
    first_pass = {'n': 26.2, 'h': 26.7, 'r': 26.5, 'u': 26.5, 'y': 26.2, 'f': 26.5, 'v': 14.1, 'five': 19.8}
    for n, w in first_pass.items():
        assert piece_gaps(outline(it, n))[0] == pytest.approx(w, abs=1.75), n
    assert piece_gaps(outline(it, 'm'))[:2] == pytest.approx([26.5, 27.2], abs=1.75)
    assert piece_gaps(outline(it, 'w'))[:2] == pytest.approx([15.1, 15.2], abs=1.75)
    slits = {'a': 31.6, 'b': 28.9, 'd': 24.0, 'g': 35.5, 'o': 29.1, 'p': 21.2, 'q': 28.2, 'six': 25.1, 'nine': 19.6, 'zero': 33.8}
    for n, w in slits.items():
        assert T.white_necks(outline(it, n), 45)[0][0] == pytest.approx(w, abs=1.75), n
    # an accented letter is its letter as grown
    for n, base in (('ntilde', 'n'), ('uacute', 'u'), ('ecaron', 'e'), ('wcircumflex', 'w'), ('uni1E03', 'b')):
        for y in (150, 300):
            assert [b - a for a, b in T.runs_at(outline(it, n), y)] == \
                pytest.approx([b - a for a, b in T.runs_at(outline(it, base), y)], abs=1.5), (n, y)


def test_release_italic_outlines_are_settled():
    """After the slant the Italic's outlines are settled on the grid: no more bent joins or short pieces than the
    Regular has (the first pass: 194 joins bent 3 to 25 degrees and 62 pieces under 8 units, against 76 and 17)."""
    count = lambda p: [sum(x) for x in zip(*(joins(drawn(p, n)) for n in TRACED41))]
    (rs, rb), (i_s, ib) = count(release('Regular')), count(release('Italic'))
    assert i_s <= rs and ib <= rb + 5, ((rs, rb), (i_s, ib))


@pytest.mark.parametrize('style', ['Regular', 'Italic'])
def test_release_r_is_on_the_x_height(style):
    """r's flat top, its arm, on the x-height with the arches of n and h (it was 2 units low)."""
    import tuam_studio as T
    from fontTools.ttLib import TTFont
    p = release(style); xh = TTFont(p)['OS/2'].sxHeight
    for n in ('r', 'n', 'h'):
        q = outline(p, n); x0, _, x1, _ = T.bounds(q)
        runs, cur = [], []                                 # level stretches of the top near the x-height
        for t in [T.level_of(q, x, x, 'top') for x in np.arange(x0 + 2, x1 - 2, 4)]:
            if xh - 25 < t < xh + 10 and (not cur or max(cur + [t]) - min(cur + [t]) <= 2.5):
                cur.append(t); continue
            runs.append(cur); cur = [t] if xh - 25 < t < xh + 10 else []
        longest = max(runs + [cur], key=len)
        assert abs(np.median(longest) - xh) <= 1, (n, np.median(longest))
