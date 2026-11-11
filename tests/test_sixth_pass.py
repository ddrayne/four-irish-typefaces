"""The sixth finishing pass, shared by the four faces (research/*/judged-edits.json, "sixth_pass"), checked on the
released fonts (fonts/, or FONTDIR) with the scorecard's own measures (scripts/scorecard.py): every mapped letter
places a combining mark, every pair of text characters stands 8 units clear in every direction, and Céilí's ĵ follows
its ss03 j. No outline changes in this pass: only mark anchors, kerning and one substitution."""
import json, os, unicodedata
import pytest
import scorecard
from conftest import ROOT, static

FACES = {'KilfaneDigital': ('Regular', 'Italic', 'Bold', 'Bold Italic'), 'CarrickDigital': ('Regular', 'Italic'),
         'TuamUncialDigital': ('Regular', 'Italic'), 'CeiliDigital': ('Regular', 'Italic', 'Bold', 'Bold Italic')}
ALL = [(ps, st) for ps, sts in FACES.items() for st in sts]
EDITS = {'KilfaneDigital': 'research/kilfane-sheet-frame/judged-edits.json', 'CarrickDigital': 'research/round-06/carrick/judged-edits.json',
         'TuamUncialDigital': 'research/tuam-judgement/judged-edits.json', 'CeiliDigital': 'research/ceili-judgement/judged-edits.json'}
BUILT = 'ðþđħĳĸŀłŋŧßſ'       # letters made from the face's parts, which had no anchors up to 3.100
_fonts = {}


def shaped(ps, st):
    if (ps, st) not in _fonts:
        _fonts[ps, st] = scorecard.Shaped(static(ps, st))
    return _fonts[ps, st]


@pytest.mark.parametrize('ps,st', ALL)
def test_every_letter_places_a_combining_mark(ps, st):
    """3.100: 25 letters per style had no mark anchor, so 171 to 251 letter + mark pairs overlapped (ł + U+0301)."""
    m = scorecard.marks(shaped(ps, st))
    assert m['unanchored'] == '', f'no mark anchor on {m["unanchored"]}'
    assert m['colliding'] == 0, f'marks overlap their letter: {m["worst"]}'


@pytest.mark.parametrize('ps,st', ALL)
def test_built_letters_set_a_mark_above_their_ink(ps, st):
    """What the eye sees, not only the anchor: the acute over each built letter stands wholly above the letter's ink
    under it, and within the letter's width."""
    f = shaped(ps, st)
    for ch in BUILT:
        if ord(ch) not in f.cmap:
            continue
        g = f.shape(ch + '\u0301')
        assert len(g) == 2, ch
        (g0, adv, _, _), (g1, _, dx, dy) = g
        base, mark = f.outline(g0).bounds, f.outline(g1, adv + dx, dy).bounds
        assert mark[1] > f.xh * 0.9, f'{ch}: the acute stands at {mark[1]:.0f}, inside the x-height'
        slope = 0.25 * (mark[3] - 0) if 'Italic' in st else 0          # a sloped style leans the mark's column
        assert base[0] - 20 <= (mark[0] + mark[2]) / 2 <= base[2] + 20 + slope, f'{ch}: the acute stands off the letter'


@pytest.mark.parametrize('ps,st', ALL)
def test_every_text_pair_stands_clear_all_round(ps, st):
    """3.100 kept 8 units across each level line, so tips passing above or below came closer: Kilfane's k before j 5.0
    (Bold 4.4), Carrick's y before j 5.6, Tuam's ( before j 6.5, Céilí Bold's 7 before ] 6.9."""
    p = scorecard.pairs(shaped(ps, st))
    assert p['touching'] == 0, p['touching_list']
    close = [x for x in p['near_list'] if x[1] < scorecard.NEAR - 0.25]     # a quarter unit for the sampling
    assert not close, f'pairs under {scorecard.NEAR} units: {close}'


@pytest.mark.parametrize('st', FACES['CeiliDigital'])
def test_ceili_jcircumflex_follows_the_alternate_j(st):
    """3.100: with ss03 on, j took its alternate form but ĵ and j + a combining mark kept the default."""
    f = shaped('CeiliDigital', st)
    plain, alt = f.shape('j', {'ss03': True})[0][0], 'j.alt1'
    assert plain == alt
    assert f.shape('ĵ', {'ss03': True})[0][0] == 'jcircumflex.alt1'
    assert f.shape('ĵ')[0][0] == 'jcircumflex'
    assert [g[0] for g in f.shape('j\u0302', {'ss03': True})] == ['jcircumflex.alt1']      # composed, then swapped
    assert [g[0] for g in f.shape('j\u030c', {'ss03': True})][0] == alt                     # no such letter: j and a mark
    # the accented alternate is the alternate letter with a circumflex above it, not the default j
    a, c = f.outline(alt).bounds, f.outline('jcircumflex.alt1').bounds
    assert abs(a[0] - c[0]) <= 1 and abs(a[1] - c[1]) <= 1 and c[3] > a[3] + 50


@pytest.mark.parametrize('ps', FACES)
def test_the_sixth_pass_is_recorded(ps):
    doc = json.loads(open(os.path.join(ROOT, EDITS[ps]), encoding='utf-8').read())
    rec = doc['sixth_pass']
    assert {'about', 'anchors', 'clearance', 'changed'} <= set(rec)
    assert rec['anchors']['letters'] and rec['clearance']['least'] == scorecard.NEAR
    assert rec['changed']['outlines'] == 0
    if ps == 'CeiliDigital':
        assert rec['alternate_j']['added'] == ['jcircumflex.alt1']


@pytest.mark.parametrize('ps,st', ALL)
def test_a_built_letters_mark_stays_off_the_next_letter(ps, st):
    """The first build of this pass moved ŋ's dot below along the baseline, past the letter's advance and into a
    following j (Kilfane, 7,900 square units): an independent review caught it. A built letter's mark hangs under the
    middle of its foot, below a descender where it must, and clears the letter after it."""
    import pathops
    f = shaped(ps, st)
    for ch in BUILT + 'ĲŊ':
        if ord(ch) not in f.cmap:
            continue
        for mark in '̣̦́':
            for nxt in 'jpn':
                if nxt == 'j' and ch in 'łŀſ':
                    continue          # j's tail runs under a narrow letter and meets a mark below it, as under l and i
                g = f.shape(ch + mark + nxt)
                if len(g) != 3:
                    continue
                m = f.outline(g[1][0], g[0][1] + g[1][2], g[1][3]); n = f.outline(g[2][0], g[0][1] + g[1][1] + g[2][2])
                x = pathops.op(m, n, pathops.PathOp.INTERSECTION, fix_winding=True)
                assert not (x.bounds and abs(x.area) > 4), f'{ch} + U+{ord(mark):04X} lands on the following {nxt}'


LONG_S = {'Regular': [('ſd', {'ss03': True}, 0), ('ſ7', {}, 0), ('sd', {'ss01': True, 'ss03': True}, 0)],
          'Italic': [('ſ7', {}, 0), ('ſj', {'ss03': True}, 0)],
          'Bold': [('ſn', {'ss02': True}, 0), ('ſu', {}, 20), ('ſy', {}, 0), ('ſw', {}, 30)]}


@pytest.mark.parametrize('st', LONG_S)
def test_no_pair_gapes_for_the_clearance(st):
    """Where one letter overhangs the next (Céilí's long s over d, with ss03), no shift across clears it short of a
    gape: the first build of this pass opened ſ before d by 170 units and ſ before 7 by 165, which an independent
    review caught. A pair that would need more than 30 units keeps the kerning 3.100 gave it."""
    f = shaped('CeiliDigital', st)
    for text, feat, kern in LONG_S[st]:
        g = f.shape(text, feat)
        assert g[0][1] - f.tt['hmtx'][g[0][0]][0] == kern, text
