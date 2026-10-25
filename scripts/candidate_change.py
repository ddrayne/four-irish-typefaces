"""How far the release candidate moves from the release, per face (research/release-readiness.md).

usage: python scripts/candidate_change.py [--release fonts/otf] [--candidate build/candidate/fonts]

For each Regular: the median, over the code points both fonts map to glyphs with ink, of the share
of the release glyph's ink that differs in the candidate (both drawn at 2 units per pixel, aligned
at the left of their ink so spacing changes don't count), and the mean advance of a to z. It
measures how far the release moves, not authenticity.
"""
import argparse, glob, os
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from PIL import Image, ImageDraw


class Polygons(BasePen):
    """Each contour as a polygon (curves flattened to 8 segments)."""
    def __init__(self, gs):
        super().__init__(gs); self.contours, self.cur = [], []

    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, a, b, c):
        p0 = np.array(self.cur[-1])
        for t in np.linspace(0, 1, 9)[1:]:
            self.cur.append(tuple((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * np.array(a) + 3 * (1 - t) * t * t * np.array(b) + t ** 3 * np.array(c)))
    def _closePath(self): self.contours.append(self.cur); self.cur = []


def ink(gs, name, x0, units=2):
    """The glyph's ink at `units` font units per pixel, its left ink edge at x = 20 px (even-odd fill)."""
    pen = Polygons(gs); gs[name].draw(pen)
    acc = np.zeros((800, 700), bool)
    for c in pen.contours:
        if len(c) < 3:
            continue
        im = Image.new('1', (700, 800), 0)
        ImageDraw.Draw(im).polygon([((x - x0) / units + 20, (1000 - y) / units) for x, y in c], fill=1)
        acc ^= np.array(im)
    return acc


def change(release, candidate):
    a, b = TTFont(release), TTFont(candidate)
    ga, gb, ca, cb = a.getGlyphSet(), b.getGlyphSet(), a.getBestCmap(), b.getBestCmap()
    shares = []
    for cp in sorted(set(ca) & set(cb)):
        ba, bb = BoundsPen(ga), BoundsPen(gb)
        ga[ca[cp]].draw(ba); gb[cb[cp]].draw(bb)
        if ba.bounds and bb.bounds:
            ma, mb = ink(ga, ca[cp], ba.bounds[0]), ink(gb, cb[cp], bb.bounds[0])
            shares.append((ma ^ mb).sum() / max(ma.sum(), 1))
    lc = [c for c in 'abcdefghijklmnopqrstuvwxyz' if ord(c) in ca and ord(c) in cb]
    advance = lambda f, cm: float(np.mean([f['hmtx'][cm[ord(c)]][0] for c in lc]))
    return float(np.median(shares)), advance(a, ca), advance(b, cb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--release', default='fonts/otf')
    ap.add_argument('--candidate', default='build/candidate/fonts')
    args = ap.parse_args()
    for rel in sorted(glob.glob(os.path.join(args.release, '*-Regular.otf'))):
        cand = os.path.join(args.candidate, os.path.basename(rel))
        if os.path.exists(cand):
            share, before, after = change(rel, cand)
            print(f'{os.path.basename(rel)}: median ink change {100 * share:.0f}%, lowercase mean advance {before:.0f} -> {after:.0f}')


if __name__ == '__main__':
    main()
