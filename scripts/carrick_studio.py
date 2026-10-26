"""Carrick's second finishing pass: the figures on one figure line (research/round-06/carrick/judged-edits.json,
"figures"), called from scripts/build_candidate.py after the zones.

N513 prints Carrick's figures with their tops on one line (all but the 8 within two source pixels, about 11
units) and their feet at different depths: the 7's and 5's cut ends and round bottoms run up to 37 units
below the 2's flat foot. The builder sets each letter's lowest point on the baseline (or 8 below it, for a
cut or round foot), as it does Carrick's lowercase cut feet, and that moved the tops apart: from 517 (the
2) to 565 (the 5 and 7). Each figure is scaled about the baseline so that a flat top meets the figure line
and a cut or pointed top stands the round overshoot above it, as the builder's feet stand below the
baseline. The 8 stands about 12 source pixels (67 units) above the others on N513 and on N47, its feet on
the line with theirs: drawn so, it keeps its height.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EDITS = ROOT / 'research' / 'round-06' / 'carrick' / 'judged-edits.json'
FIGURES = 'zero one two three four five six seven eight nine'.split()


def load(edits=EDITS):
    return json.loads(Path(edits).read_text(encoding='utf-8'))['figures']


def figures(font, edits=EDITS):
    """Each figure (font.P, after the zones) on the figure line; font.fig becomes that line. Returns
    {figure: (top before, top after)}."""
    import build2
    from glyphs import bounds
    spec = load(edits)
    line, over, keep = float(spec['line']), float(spec['overshoot']), set(spec['keep'])
    report = {}
    for n in FIGURES:
        if n in keep or n not in font.P:
            continue
        p = font.P[n]; top = bounds(p)[3]
        target = line if font.flat(p, top, 0.015 * font.xh) else line + over
        if abs(target - top) > 0.25:
            font.P[n] = build2.remap(p, lambda x, y, k=target / top: (x, y * k if y > 0 else y))
        report[n] = (round(top, 1), target)
    font.fig = line
    font.figure_line = report
    return report
