"""The pen model on outlines traced from the original sheets (research rounds), not only the flyer."""
import os
import paths, glyphs, bolden
import shapes as SH
from build2 import BOLD
from glyphs import contours

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def research(monkeypatch, face, rnd):
    monkeypatch.setattr(paths, 'TRACED', os.path.join(ROOT, 'research', rnd, face, 'traces'))
    G, _ = glyphs.load(face)
    return {n: g['path'] for n, g in G.items()}


def test_growth_never_hollows_a_letter(monkeypatch):
    """Kilfane's Y and 3 from N516: the stroke's inner edge loops back on itself, and uniting it
    unresolved left each letter as a hole inside a ring."""
    P = research(monkeypatch, 'kilfane', 'round-02'); b = BOLD['kilfane']
    for n in ('Y', 'three'):
        q = SH.transform(P[n], (b['k'], 0, 0, 1, 0, 0))
        g = bolden.grow(q, b['rx'], b['ry'])
        a = [bolden.area(c) for c in contours(g)]
        assert sum(x > 0 for x in a) == 1 and not any(x < 0 for x in a), f'{n}: contour areas {a}'
        assert abs(bolden.area(SH.difference(q, g))) < 1, f'{n} lost ink in growing'


def regular_and_bold(monkeypatch, face, rnd, names, sliver=0.05):
    """Each named glyph as the bold receives it (traced, before any derivation) and as the bold
    draws it, under the rule for outlines traced from the original sheets."""
    import build2
    monkeypatch.setattr(paths, 'TRACED', os.path.join(ROOT, 'research', rnd, face, 'traces'))
    seen = {}
    monkeypatch.setattr(build2.Font2, 'embolden_traced', lambda self: seen.update(P=dict(self.P), xh=self.xh))
    f = build2.Font2(face, 'Bold'); b = BOLD[face]
    return {n: (seen['P'][n], bolden.embolden(seen['P'][n], b['rx'], b['ry'], b['k'], seen['xh'], f.S_regular,
                                              apertures=n not in b.get('joins', ()), sliver=sliver)) for n in names}


def shape(p):
    a = sorted(x for x in (bolden.area(c) for c in contours(p)) if abs(x) > 1)     # not degenerate contours
    return sum(x > 0 for x in a), sorted(-x for x in a if x < 0)


def test_bold_keeps_the_open_joins_of_the_original_sheets(monkeypatch):
    """N516's r, 6 and 9 join the stem across a narrow slit, and its g's tail leaves the bowl open
    (research/HANDOFF.md: preserve them); Q's tail crosses the bowl to make a small second counter."""
    for n, (reg, bold) in regular_and_bold(monkeypatch, 'kilfane', 'round-02',
                                           ('r', 'six', 'nine', 'g', 'Q', 'ampersand', 'parenright')).items():
        (pr, hr), (pb, hb) = shape(reg), shape(bold)
        assert pb == pr and len(hb) == len(hr), f'{n}: regular {pr} pieces {len(hr)} counters, bold {pb} and {len(hb)}'
        if hr:
            assert hb[0] >= 0.30 * hr[0], f'{n}: smallest counter kept {hb[0] / hr[0]:.0%}'


def test_bold_keeps_separate_pieces_apart(monkeypatch):
    """Céilí's ! and ? from N46: the dot sits closer to its stroke than the bold's pen is deep."""
    for n, (reg, bold) in regular_and_bold(monkeypatch, 'ceili', 'round-04', ('exclam', 'question')).items():
        assert shape(bold)[0] == shape(reg)[0] == 2, n
