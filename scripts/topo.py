"""Compare each glyph's topology (pieces and counters) between two styles of a family.

usage: topo.py REG.otf BOLD.otf [out.png]
Flags glyphs whose number of separate pieces or counters changed, or whose smallest counter shrank
below 35% of the regular's area.
"""
import sys
import pathops
from fontTools.ttLib import TTFont
from fontTools.pens.areaPen import AreaPen
from PIL import Image, ImageDraw
import render_path


def shape(gs, n):
    p = pathops.Path(); gs[n].draw(p.getPen())
    return pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)


def topology(p):
    from glyphs import contours
    a = []
    for c in contours(p):
        ap = AreaPen(); c.draw(ap); a.append(ap.value)
    outer = sorted(x for x in a if x > 0); holes = sorted(-x for x in a if x < 0)
    if not outer and holes:
        outer, holes = holes, outer
    return len(outer), holes


def compare(reg, bold, small=0.35):
    A = TTFont(reg); B = TTFont(bold)
    ga, gb = A.getGlyphSet(), B.getGlyphSet()
    flagged = []
    for n in A.getGlyphOrder():
        if n not in gb or n == '.notdef':
            continue
        pa, pb = shape(ga, n), shape(gb, n)
        (oa, ha), (ob, hb) = topology(pa), topology(pb)
        why = []
        if oa != ob:
            why.append(f'pieces {oa}->{ob}')
        if len(ha) != len(hb):
            why.append(f'counters {len(ha)}->{len(hb)}')
        elif ha and hb[0] / ha[0] < small:
            why.append(f'smallest counter {hb[0] / ha[0]:.0%}')
        if why:
            flagged.append((n, ', '.join(why), pa, pb))
    return flagged


if __name__ == '__main__':
    flagged = compare(sys.argv[1], sys.argv[2])
    for n, why, *_ in flagged:
        print(f'{n:24s} {why}')
    print(len(flagged), 'flagged')
    if len(sys.argv) > 3 and flagged:
        ps, labels = [], []
        for n, why, pa, pb in flagged:
            ps += [pa, pb]; labels += [n, why]
        render_path.render(ps, scale=0.16, pad=14, labels=labels, cols=16).save(sys.argv[3])
