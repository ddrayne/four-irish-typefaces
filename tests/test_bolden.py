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
