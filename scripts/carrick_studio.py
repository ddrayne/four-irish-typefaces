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

The fourth pass adds, from the same file: £ and $ on the figure line with the figures (signs, "figures", "signs");
' and " to the curly quotes' depth (straight_quotes, "quotes"); and Tuam's rule for the white above the x-height
at Carrick's own cut (kern, "kerning"). ‹ › « » from one chevron are symbols.make_symbols' (ONE_CHEVRON).
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


def body(p, bar):
    """The glyph's body: with `bar`, without the vertical bar that alone reaches its top and bottom (the $'s): the ink
    beside the bar's widest extent at its ends, less any sliver where the bar flares."""
    import bolden, build2, shapes as SH
    from glyphs import bounds
    if not bar:
        return p
    x0, y0, x1, y1 = bounds(p); h = 0.04 * (y1 - y0)
    ends = [build2.ink_x_extent(p, y1 - h, y1), build2.ink_x_extent(p, y0, y0 + h)]
    lo, hi = min(e[0] for e in ends) - 4, max(e[1] for e in ends) + 4
    rest = SH.difference(p, SH.polygon([(lo, y0 - 10), (hi, y0 - 10), (hi, y1 + 10), (lo, y1 + 10)]))
    return bolden.concat([c for c in bolden.components(rest) if abs(bolden.area(c)) >= 0.02 * abs(bolden.area(p))])


def signs(font, edits=EDITS):
    """The fourth pass ("figures", "signs"): £ and $ stand with the figures. Each sign's body (with "bar", the $
    without its bar) has its foot set on the baseline as the builder sets a figure's (a flat foot on it, a cut or
    round one `overshoot` below) and is scaled about the baseline as figures() scales the figures: a flat top to the
    figure line, a cut or pointed one `overshoot` above it. With "regrow", the weight that scale takes from a
    horizontal stroke that share of the stem is given back in height by the drawing's own nodes (bolden.grow_nodes),
    the cuts between its pieces held, so a sign scaled well down keeps the weight of its foot, bar and hook.
    Returns {sign: (body before, body after, the height given back on each side)}."""
    import bolden, build2
    from glyphs import bounds
    spec = json.loads(Path(edits).read_text(encoding='utf-8'))['figures']
    line, over, band = float(spec['line']), float(spec['overshoot']), 0.015 * font.xh
    report = {}
    for n, how in spec.get('signs', {}).items():
        if n not in font.P:
            continue
        bar = bool(how.get('bar'))
        p = font.P[n]; q = body(p, bar); b = bounds(q)
        foot = 0.0 if font.flat(q, b[1], band, top=False) else -over
        p = build2.translate(p, 0, foot - b[1])
        q = body(p, bar); top = bounds(q)[3]
        target = line if font.flat(q, top, band) else line + over
        ry = (1 - target / top) * how.get('regrow', 0.0) * font.S_regular / 2
        p = build2.remap(p, lambda x, y, k=(target - 2 * ry) / top: (x, y * k if y > 0 else y))
        if ry > 0:
            p = bolden.grow_nodes(p, 0.01, ry, fallback=bolden.grow, keep_cuts=0.22 * font.S_regular)
            p = build2.translate(p, 0, foot - bounds(body(p, bar))[1])
        font.P[n] = p
        report[n] = ((round(b[1], 1), round(b[3], 1)), (foot, target), round(ry, 1))
    font.signs_on_line = report
    return report


def straight_quotes(font, edits=EDITS):
    """The fourth pass ("quotes"): the straight quote and double quote (build2.punctuation's wedge) drawn to the
    curly quotes' depth, the wedge lengthened about the middle of its top so that its top on the quotes' line
    and its widths at top and foot (its taper from the period) stay as the builder draws them; the double quote
    is two of them, set as the builder sets them, and the primes (symbols.make_symbols) follow."""
    import shapes as SH
    from glyphs import bounds, translate
    spec = json.loads(Path(edits).read_text(encoding='utf-8')).get('quotes')
    if not spec:
        return None
    P = font.P; q = P['quotesingle']; b = bounds(q); ref = bounds(P[spec['depth_of']])
    ky, kx = (ref[3] - ref[1]) / (b[3] - b[1]), spec.get('width', 1.0)
    cx, top = (b[0] + b[2]) / 2, b[3]
    q = font.norm_x(SH.transform(q, (kx, 0, 0, ky, cx - kx * cx, top - ky * top)))
    P['quotesingle'] = q
    P['quotedbl'] = SH.union(q, translate(q, bounds(q)[2] * 1.6, 0))
    font.straight_quotes = ((round(b[2] - b[0], 1), round(b[3] - b[1], 1)), (round(bounds(q)[2], 1), round(bounds(q)[3] - bounds(q)[1], 1)))
    return font.straight_quotes


def kern(font, edits=EDITS):
    """The fourth pass ("kerning"): above the x-height every pair stands at least Carrick's cut width apart, as
    Tuam's do at Tuam's (tuam_studio.upper_clearance, after the builder's kerning and its 8-unit protection): f's
    flag came within 8 to 13 units of the next ascender."""
    spec = json.loads(Path(edits).read_text(encoding='utf-8')).get('kerning', {})
    if 'upper_clearance' not in spec:
        return []
    import tuam_studio
    return tuam_studio.upper_clearance(font, spec['upper_clearance'])
