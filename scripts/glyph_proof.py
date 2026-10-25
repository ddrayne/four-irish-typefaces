"""Font-only proofs: glyphs of several fonts side by side, and the same text set in each.

usage: python scripts/glyph_proof.py OUT.png FONT ... [--glyphs a b ...] [--text "..."] [--sizes 16 28 72]

With --glyphs, each glyph is drawn from every font in turn (in the order given) on one cell row; with
--text, the text is shaped by HarfBuzz and rasterised by FreeType from each font at each size (sizes under
32 px are shown enlarged three times, pixel for pixel). No archive pixels: the images may be committed.
"""
import argparse, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def label_font(size=16):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def glyph_grid(fonts, names, px=0.16, cols=8):
    import evidence_board as EB
    from fontTools.ttLib import TTFont
    tt = [TTFont(f) for f in fonts]
    cell = int(1250 * px) + 10; lab = label_font(14); tiles = []
    for n in names:
        row = Image.new('L', (cell * len(tt), cell + 18), 255); d = ImageDraw.Draw(row)
        for j, f in enumerate(tt):
            polys = EB.glyph_polygons(f, n) if n in f.getGlyphOrder() else []
            if polys:
                m = EB.rasterise(polys, px, (cell, cell), np.array([-60, 950]))
                row.paste(Image.fromarray(np.where(m, 0, 255).astype(np.uint8)), (j * cell, 18))
        d.text((2, 1), n, fill=0, font=lab); tiles.append(row)
    W = cols * (tiles[0].width + 16); H = ((len(tiles) + cols - 1) // cols) * (tiles[0].height + 8)
    board = Image.new('L', (W, H), 255)
    for i, t in enumerate(tiles):
        board.paste(t, ((i % cols) * (t.width + 16), (i // cols) * (t.height + 8)))
    return board


def text_line(path, text, px):
    import uharfbuzz as hb, freetype
    blob = hb.Blob.from_file_path(path); face = hb.Face(blob); font = hb.Font(face); upem = face.upem
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties(); hb.shape(font, buf, {})
    ft = freetype.Face(path); ft.set_pixel_sizes(0, px)
    W = int(sum(p.x_advance for p in buf.glyph_positions) * px / upem) + 2 * px; H = int(px * 1.6)
    canvas = np.zeros((H, W), np.uint8); x = px * 0.5; base = int(px * 1.15)
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        ft.load_glyph(info.codepoint, freetype.FT_LOAD_DEFAULT); ft.glyph.render(freetype.FT_RENDER_MODE_NORMAL)
        bm = ft.glyph.bitmap
        if bm.width:
            a = np.array(bm.buffer, np.uint8).reshape(bm.rows, bm.pitch)[:, :bm.width]
            gx = int(round(x + pos.x_offset * px / upem)) + ft.glyph.bitmap_left
            gy = base - ft.glyph.bitmap_top - int(round(pos.y_offset * px / upem))
            y0, x0 = max(gy, 0), max(gx, 0); sub = a[y0 - gy:, x0 - gx:]
            h, w = min(sub.shape[0], H - y0), min(sub.shape[1], W - x0)
            if h > 0 and w > 0:
                canvas[y0:y0 + h, x0:x0 + w] = np.maximum(canvas[y0:y0 + h, x0:x0 + w], sub[:h, :w])
        x += pos.x_advance * px / upem
    im = Image.fromarray(255 - canvas)
    return im.resize((im.width * 3, im.height * 3), Image.NEAREST) if px < 32 else im


def text_sheet(fonts, text, sizes):
    lab = label_font(16); rows = []
    for s in sizes:
        for f in fonts:
            rows.append((f'{os.path.basename(f)}  {s} px', text_line(f, text, s)))
    W = max(im.width for _, im in rows); H = sum(im.height + 24 for _, im in rows)
    board = Image.new('L', (W, H), 255); d = ImageDraw.Draw(board); y = 0
    for t, im in rows:
        d.text((4, y + 2), t, fill=90, font=lab); board.paste(im, (0, y + 22)); y += im.height + 24
    return board


def main():
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('fonts', nargs='+')
    ap.add_argument('--glyphs', nargs='*'); ap.add_argument('--text'); ap.add_argument('--sizes', nargs='*', type=int, default=[16, 28, 72])
    ap.add_argument('--cols', type=int, default=8); ap.add_argument('--px', type=float, default=0.16)
    a = ap.parse_args()
    board = glyph_grid(a.fonts, a.glyphs, a.px, a.cols) if a.glyphs else text_sheet(a.fonts, a.text, a.sizes)
    board.save(a.out, optimize=True); print(a.out, board.size)


if __name__ == '__main__':
    main()
