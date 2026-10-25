"""Count the pieces of Tuam's letters on the 48 pt production sheet (Bolger fig. 206), impression by impression.

usage: pdfimages -j -f 164 -l 164 build/research/sources/Bolger-2017-volume-2-illustrations.pdf build/tuam-judgement/bolger/fig206
       python scripts/tuam_sheet_check.py build/tuam-judgement/bolger/fig206-000.jpg [--json research/tuam-judgement/sheet-check.json]
                                          [--preview build/tuam-judgement/sheet]

Bolger's thesis (volume 2, PDF page 164, figure 206) photographs a Letraset sheet of Tuam Uncial,
S53912, 48 pt, c. 1980: the production artwork, printed many times, in a reproduction line apart from the
flyer (N46) and the catalogue (N45). At 590 x 900 pixels its x-height is about 20 pixels, a third of
N46's, so it resolves cuts as wide as n's (about 2.5 N45 pixels) and not the narrowest. Each letter's
impressions are found in its row on the sheet (connected ink at THRESHOLD, the pieces of a letter grouped
by a one-pixel dilation), and each impression's pieces are counted at THRESHOLD. Means of a letter's
impressions (registered by phase correlation, upsampled UP times) are written to --preview for the
narrower cuts, with x (crossed, not cut) as the control. The previews hold archive pixels: build/ only.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

SHA256 = '2ea8c4401b68e2435b080cb37d976347086f1acc404da5194b1488ef50b8b8aa'   # pdfimages' JPEG of fig. 206
THRESHOLD, UP = 95, 4
# letter: (y0, y1, x0, x1) of its impressions on the sheet, the band of one row; widths outside the range are
# other letters or pieces the dilation did not group
ROWS = {
    'n': [((447, 477, 30, 350), (25, 36))],
    'h': [((268, 303, 320, 570), (25, 36)), ((315, 360, 30, 96), (25, 36))],
    'f': [((220, 263, 300, 482), (18, 30))],
    'u': [((659, 688, 290, 552), (26, 36)), ((695, 728, 30, 196), (26, 36))],
    'uacute': [((650, 684, 225, 291), (26, 36))],
    'r': [((534, 563, 310, 571), (26, 36))],
    'v': [((695, 728, 225, 354), (26, 36))],
    'w': [((695, 728, 354, 549), (42, 52))],
    'x': [((736, 776, 130, 226), (26, 36))],                # the y's follow
    'e': [((187, 213, 30, 568), (26, 36))],
    'o': [((492, 529, 30, 302), (28, 38))],
}
MEANS = ('v', 'w', 'x', 'r', 'h')


def impressions(g, band, widths, grow=1):
    y0, y1, x0, x1 = band
    ink = g[y0:y1, x0:x1] < THRESHOLD
    lab, _ = ndi.label(ndi.binary_dilation(ink, iterations=grow))
    out = []
    for sl in ndi.find_objects(lab):
        w = sl[1].stop - sl[1].start
        if widths[0] <= w <= widths[1] and sl[0].stop - sl[0].start >= 12:
            box = (sl[1].start + x0, sl[0].start + y0, sl[1].stop + x0, sl[0].stop + y0)
            sub = g[box[1]:box[3], box[0]:box[2]] < THRESHOLD
            pl, k = ndi.label(sub, structure=np.ones((3, 3)))
            sizes = ndi.sum(sub, pl, range(1, k + 1))
            out.append(dict(box=[int(v) for v in box], pieces=int(sum(s >= 8 for s in sizes))))
    return sorted(out, key=lambda r: (r['box'][1] // 20, r['box'][0]))


def mean_impression(g, boxes, pad=4):
    """The impressions' mean ink, each cropped to its own box (so no neighbour's ink enters it), upsampled
    and aligned on its ink centroid, set on paper `pad` pixels wide."""
    from skimage.transform import rescale
    crops = []
    for x0, y0, x1, y1 in boxes:
        c = g[y0 - 1:y1 + 1, x0 - 1:x1 + 1]
        paper, ink = np.percentile(g[y0 - pad:y1 + pad, x0 - pad:x1 + pad], 90), np.percentile(c, 4)
        crops.append(np.clip((paper - c) / max(paper - ink, 1), 0, 1))
    H = max(c.shape[0] for c in crops) + 2 * pad; W = max(c.shape[1] for c in crops) + 2 * pad
    ups = []
    for c in crops:
        z = np.zeros((H, W)); z[pad:pad + c.shape[0], pad:pad + c.shape[1]] = c; ups.append(rescale(z, UP, order=3))
    centre = np.array([H, W]) * UP / 2
    return np.mean([ndi.shift(u, centre - np.array(ndi.center_of_mass(u)), order=1) for u in ups], 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image', type=Path); ap.add_argument('--json', type=Path); ap.add_argument('--preview', type=Path)
    args = ap.parse_args()
    digest = hashlib.sha256(args.image.read_bytes()).hexdigest()
    if digest != SHA256:
        raise ValueError(f'not the registered extraction of fig. 206: {digest}')
    g = np.asarray(Image.open(args.image).convert('RGB')).astype(float).mean(2)
    report = dict(source='Bolger 2017, volume 2 (B2 in research/downloads.json), PDF page 164, figure 206: '
                         '"Tuam Uncial Letraset sheet, c. 1980", S53912, 48 pt',
                  image=dict(extraction='pdfimages -j -f 164 -l 164 (the page\'s 590 x 900 JPEG)', sha256=digest),
                  threshold=THRESHOLD, letters={})
    for name, rows in ROWS.items():
        imps = [i for band, widths in rows for i in impressions(g, band, widths)]
        counts = [i['pieces'] for i in imps]
        report['letters'][name] = dict(impressions=imps, pieces={str(k): counts.count(k) for k in sorted(set(counts))})
        print(f'{name:7s} {len(imps):2d} impressions, pieces {report["letters"][name]["pieces"]}')
        if args.preview and name in MEANS:
            args.preview.mkdir(parents=True, exist_ok=True)
            m = mean_impression(g, [i['box'] for i in imps])
            Image.fromarray(((1 - np.clip(m, 0, 1)) * 255).astype(np.uint8)).resize(
                (m.shape[1] * 3, m.shape[0] * 3), Image.BICUBIC).save(args.preview / f'mean-{name}.png')
    if args.json:
        args.json.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
