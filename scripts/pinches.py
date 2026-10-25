"""Find pinches: places where a glyph's ink narrows to a neck between two thick parts.

usage: python scripts/pinches.py FONT.otf [--ratio 0.33] [--glyphs a e ...]

A deliberate hairline (a tapering terminal, a flag, a thin diagonal) thins towards an end or
stays thin; a pinch is thin with thick ink on both sides close by, as where a bowl's terminal
barely touches a bar. Printed artwork can carry pinches that read as gaps at text sizes. Each
pinch is reported with its width as a share of the face's stem, and where it is.
"""
import argparse, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))


def pinches(polys, stem, ratio=0.33, upx=0.25):
    """(x, y, width, kind) in font units of every structural neck narrower than ratio * stem: cut
    there, the glyph would fall into two thick parts ('split') or a counter would open ('opens')."""
    from scipy import ndimage as ndi
    from skimage.morphology import skeletonize, disk
    import evidence_board as EB
    pts = np.vstack(polys); lo, hi = pts.min(0) - 20, pts.max(0) + 20
    shape = (int((hi[1] - lo[1]) * upx) + 1, int((hi[0] - lo[0]) * upx) + 1)
    m = EB.rasterise(polys, upx, shape, np.array([lo[0], hi[1]]))
    dt = ndi.distance_transform_edt(m) / upx                      # half-width in font units
    thick = m & (2 * dt >= 0.6 * stem)
    def counts(mask):
        lab, n = ndi.label(mask, structure=np.ones((3, 3)))
        parts = sum(1 for i in range(1, n + 1) if (thick & (lab == i)).sum() >= 4)
        bg, nb = ndi.label(~mask)
        edge = set(np.unique(np.r_[bg[0], bg[-1], bg[:, 0], bg[:, -1]]))
        return parts, sum(1 for i in range(1, nb + 1) if i not in edge)
    base = counts(m)
    thin = skeletonize(m) & (2 * dt < ratio * stem)
    lab, n = ndi.label(thin, structure=np.ones((3, 3)))
    out = []
    for i in range(1, n + 1):
        ys, xs = np.where(lab == i)
        k = np.argmin(dt[ys, xs]); y, x = ys[k], xs[k]
        r = int(np.ceil(dt[y, x] * upx)) + 2
        cut = m.copy(); y0, x0 = max(y - r, 0), max(x - r, 0)
        d = disk(r).astype(bool)[:min(2 * r + 1, m.shape[0] - y0), :min(2 * r + 1, m.shape[1] - x0)]
        cut[y0:y0 + d.shape[0], x0:x0 + d.shape[1]] &= ~d
        parts, holes = counts(cut)
        kind = 'split' if parts > base[0] else 'opens' if holes < base[1] else None
        if kind:
            out.append((float(lo[0] + x / upx), float(hi[1] - y / upx), float(2 * dt[y, x]), kind))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('font'); ap.add_argument('--ratio', type=float, default=0.33)
    ap.add_argument('--glyphs', nargs='*'); args = ap.parse_args()
    from fontTools.ttLib import TTFont
    import evidence_board as EB
    f = TTFont(args.font); cm = f.getBestCmap()
    stem = None
    # the face's stem: the width of l's or I's vertical, at mid-height
    for probe in ('l', 'I', 'i'):
        if ord(probe) in cm:
            polys = EB.glyph_polygons(f, cm[ord(probe)]); pts = np.vstack(polys)
            m = EB.rasterise(polys, 1.0, (int(np.ptp(pts[:, 1])) + 4, int(np.ptp(pts[:, 0])) + 4), np.array([pts[:, 0].min() - 2, pts[:, 1].max() + 2]))
            stem = float(np.median(m[m.shape[0] // 3: 2 * m.shape[0] // 3].sum(1))); break
    names = args.glyphs or [cm[c] for c in sorted(cm) if chr(c).isalnum() and c < 0x250]
    print(f'stem {stem:.0f}; pinches narrower than {args.ratio:.2f} stem:')
    for n in dict.fromkeys(names):
        ps = pinches(EB.glyph_polygons(f, n), stem, args.ratio)
        if ps:
            print(f'  {n:10s} ' + '  '.join(f'{k} ({x:.0f},{y:.0f}) {w:.0f}u {w / stem:.2f}' for x, y, w, k in ps))


if __name__ == '__main__':
    main()
