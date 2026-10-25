"""Proof sheets: the release beside the candidate, the same text in each style, rendered from the fonts.

usage: python scripts/candidate_proofs.py [--release fonts/otf] [--candidate build/candidate/fonts] [--output DIR]

One PNG per face: for each style, a line set in the release (grey label) and the same line in the
candidate (red label), at display and text sizes, plus the letters the candidate changed most.
Font-only images (no archive pixels), so they may be committed.
"""
import argparse, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import build2

ROOT = Path(__file__).resolve().parent.parent
TEXT = {
    'mixed': ['Ceithre Chló: Kilfane, Carrick, Tuam, Céilí', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
              'abcdefghijklmnopqrstuvwxyz 0123456789', 'Is é an samhradh is fearr. Ná bí ag caint! “Dia duit,” ar sí; (¿¡&@$£€%)'],
    'unicase': ['ceithre chló: kilfane, carrick, tuam, céilí', 'abcdefghijklmnopqrstuvwxyz',
                'áéíóú 0123456789 &?!', 'is é an samhradh is fearr. ná bí ag caint! “dia duit,” ar sí; (¿¡@$£€%)'],
}
INK, GREY, RED, PAPER = (20, 20, 20), (120, 120, 120), (190, 30, 30), (250, 248, 242)


def label_font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def sheet(face, release, candidate, out):
    cfg = build2.FONTS[face]; ps = cfg['ps']
    lines = TEXT['unicase' if cfg['unicase'] else 'mixed']
    styles = build2.FAMILY_STYLES[face]
    W = 2400; rows = []
    small = label_font(22)
    for style in styles:
        fn = f'{ps}-{style.replace(" ", "")}.otf'
        for tag, d, colour in (('2.010', release, GREY), ('3.000 candidate', candidate, RED)):
            path = os.path.join(d, fn)
            if not os.path.exists(path):
                continue
            rows.append(('label', f'{cfg["family"]} {style}  ·  {tag}', colour))
            for text, size in ((lines[0], 88), (lines[1], 64), (lines[2], 64), (lines[3], 30), (lines[3], 18)):
                rows.append(('text', text, ImageFont.truetype(path, size)))
        rows.append(('gap', None, None))
    H = 40
    for kind, a, b in rows:
        H += 40 if kind == 'label' else 30 if kind == 'gap' else int(b.size * 1.35)
    im = Image.new('RGB', (W, H), PAPER); d = ImageDraw.Draw(im); y = 30
    for kind, a, b in rows:
        if kind == 'label':
            d.text((40, y + 6), a, font=small, fill=b); y += 40
        elif kind == 'gap':
            d.line([(40, y + 12), (W - 40, y + 12)], fill=(210, 205, 195), width=2); y += 30
        else:
            d.text((40, y), a, font=b, fill=INK); y += int(b.size * 1.35)
    im.quantize(32).save(out, optimize=True)      # a few inks: a third of the size
    print('wrote', out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--release', default=str(ROOT / 'fonts' / 'otf'))
    ap.add_argument('--candidate', default=str(ROOT / 'build' / 'candidate' / 'fonts'))
    ap.add_argument('--output', default=str(ROOT / 'build' / 'candidate' / 'proofs'))
    args = ap.parse_args()
    os.makedirs(args.output, exist_ok=True)
    for face in build2.FONTS:
        sheet(face, args.release, args.candidate, os.path.join(args.output, f'{face}.png'))


if __name__ == '__main__':
    main()
