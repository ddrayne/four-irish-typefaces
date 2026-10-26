"""Checks every release must pass. Run on fonts/ (the release) or FONTDIR=build/fonts (a fresh build)."""
import os
import pytest
from fontTools.ttLib import TTFont
from conftest import files, static, FONTDIR

FORMATS = ('otf', 'ttf', 'woff', 'woff2')


def test_every_style_in_every_format(config):
    FONTS, STYLES, _ = config
    for key, cfg in FONTS.items():
        for st in STYLES[key]:
            for ext in FORMATS:
                static(cfg['ps'], st, ext)
    assert len(files('otf')) == sum(len(STYLES[k]) for k in FONTS)


@pytest.mark.parametrize('ext', FORMATS)
def test_sanitizer(ext):
    import ots
    bad = [os.path.basename(p) for p in files(ext) if ots.sanitize(p, os.devnull, capture_output=True).returncode != 0]
    assert not bad


def test_truetype_outlines_have_no_specks():
    """The TrueType conversion leaves no loop where a spline crosses its own contour: cu2qu's splines for a hooked
    cubic a few units long, rounded to the grid, crossed themselves (Carrick Italic's ı, i and į kept a 0.16 unit
    square speck at 335, 514; Kilfane's K, ! and q specks of 0.003 to 0.04). build2.ttf_glyph splits such a cubic."""
    import pathops, glyphs
    found = []
    for path in files('ttf'):
        f = TTFont(path); gs = f.getGlyphSet()
        for n in f.getGlyphOrder():
            p = pathops.Path(); gs[n].draw(p.getPen())
            s = pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)
            found += [(os.path.basename(path), n, round(abs(c.area), 3)) for c in glyphs.contours(s) if abs(c.area) < 4]
    assert not found, found


def test_style_linking(config):
    FONTS, STYLES, VERSION = config
    for key, cfg in FONTS.items():
        for st in STYLES[key]:
            for ext in ('otf', 'ttf'):
                f = TTFont(static(cfg['ps'], st, ext)); n = f['name']; os2 = f['OS/2']
                bold, italic = 'Bold' in st, 'Italic' in st
                assert n.getDebugName(1) == cfg['family'] and n.getDebugName(2) == st
                assert n.getDebugName(4) == f'{cfg["family"]} {st}'
                assert n.getDebugName(6) == f'{cfg["ps"]}-{st.replace(" ", "")}'
                assert n.getDebugName(5) == f'Version {VERSION}'
                assert (os2.fsSelection & 0x61) == ((0x01 if italic else 0) | (0x20 if bold else 0) or 0x40)
                assert os2.fsSelection & 0x80                                   # USE_TYPO_METRICS
                assert f['head'].macStyle & 3 == (1 if bold else 0) | (2 if italic else 0)
                assert os2.usWeightClass == (700 if bold else 400)
                assert f['post'].italicAngle == (-8.0 if italic else 0.0)
                assert (f['hhea'].caretSlopeRun != 0) == italic
                assert not any(r.platformID == 1 for r in n.names)
                assert 'STAT' in f


def test_names_mark_a_digitisation(config):
    """The families carry "Digital" so they are never taken for the original type; the description names the design."""
    FONTS, STYLES, _ = config
    for key, cfg in FONTS.items():
        assert cfg['family'] == f'{cfg["name"]} Digital'
        for st in STYLES[key]:
            n = TTFont(static(cfg['ps'], st))['name']
            assert n.getDebugName(1).endswith(' Digital') and n.getDebugName(6).startswith(cfg['ps'])
            desc = n.getDebugName(10)
            assert desc.startswith(f'{cfg["name"]}: ') and 'independent digitisation, not the original type' in desc


def test_family_shares_metrics_and_characters(config):
    FONTS, STYLES, _ = config
    for key, cfg in FONTS.items():
        ref = None
        for st in STYLES[key]:
            f = TTFont(static(cfg['ps'], st)); h, o = f['hhea'], f['OS/2']
            sig = ((h.ascent, h.descent, o.sTypoAscender, o.sTypoDescender, o.sTypoLineGap, o.usWinAscent, o.usWinDescent),
                   frozenset(f.getBestCmap()), frozenset(f.getGlyphOrder()))
            ref = ref or sig
            assert sig == ref, f'{cfg["ps"]} {st} differs from the regular'
            assert f['post'].underlineThickness == TTFont(static(cfg['ps'], 'Regular'))['post'].underlineThickness


def test_bold_keeps_counters(config):
    """A bold may not lose, merge or nearly close a counter of its regular, except where it joins by design."""
    import topo
    FONTS, STYLES, _ = config
    # Céilí's 6, and the cracks its second pass closes (research/ceili-judgement/judged-edits.json, bold_joins)
    allowed = {'ceili': {'six', 'ampersand', 'yen'}}
    for key, cfg in FONTS.items():
        if 'Bold' not in STYLES[key]:
            continue
        flagged = topo.compare(static(cfg['ps'], 'Regular'), static(cfg['ps'], 'Bold'), small=0.30)
        names = {n for n, *_ in flagged} - allowed.get(key, set())
        assert not names, f'{cfg["ps"]}: {sorted(names)}'


def test_brackets_stand_with_the_parentheses():
    # the drawn brackets and bar take the face's (often traced) parentheses' height, and a bracket's
    # arms reach well past its stem, or it reads as a bar
    from fontTools.pens.boundsPen import BoundsPen
    for p in files('otf'):
        f = TTFont(p); gs = f.getGlyphSet(); cm = f.getBestCmap()
        def ink(ch):
            pen = BoundsPen(gs); gs[cm[ord(ch)]].draw(pen); return pen.bounds
        pl, pr = ink('('), ink(')')
        for ch, tol in (('[', 2), (']', 2), ('|', 25)):        # Carrick's bar has cut ends, like its stems
            b = ink(ch)
            assert abs(b[1] - (pl[1] + pr[1]) / 2) <= tol and abs(b[3] - (pl[3] + pr[3]) / 2) <= tol, (os.path.basename(p), ch)
        width = lambda b: b[2] - b[0]
        if 'Italic' not in p:                                    # a slope widens the bar's box
            assert width(ink('[')) >= 2 * width(ink('|')), os.path.basename(p)
