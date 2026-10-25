"""Evidence boards: each glyph of a font beside every source that prints it, for judging by eye.

usage: python scripts/evidence_board.py kilfane FONT.otf [--glyphs e X H] [--out build/judgement/kilfane]

Every source gets the font's outline registered over it by translation and one uniform scale (never
a stretch, so a difference in proportion stays visible), and a disagreement map: grey where print
and font agree, orange where the print has ink the font lacks, blue where the font has ink the
print lacks. The sources are not independent: N47 reproduces N516's paste-up, and the production
sheets (N517) print one artwork many times. What a board can show is which differences are print
(a gap one print has and another fills) and which are drawing (a feature every print agrees on).

The boards hold archive pixels, so they are written under ignored build/ only (research/RIGHTS.md).
"""
import argparse, json, os, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
SPECIMENS = ROOT / 'build' / 'research' / 'original-specimens'

# trace units per font unit is the builder's SCALE; the sources' own calibration is in px per trace unit
from glyphs import SCALE as TRACE_UNIT
SOURCES = {
    'kilfane': dict(
        base=dict(id='N516', file='Kilfane-alphabet-specimen.jpg',
                  evidence='research/round-02/kilfane/traces/evidence.json'),
        copies=[dict(id='N47', file='competition-advert-2.jpg', region=(300, 1050, 1900, 2500))],
        flyer=dict(id='flyer', file='sources/flyer.jpg', traces='sources/traced/kilfane.json'),
        production=dict(id='N517', work='build/production/kilfane', sheets=('30pt',))),
    # Carrick: N513 the alphabet specimen; N47's boxes are recorded with round 2's regions ('direct')
    'carrick': dict(
        base=dict(id='N513', file='Carrick-alphabet-specimen.jpg',
                  evidence='research/round-05/carrick/traces/evidence.json'),
        copies=[dict(id='N47', file='competition-advert-2.jpg', direct=True)],
        flyer=dict(id='flyer', file='sources/flyer.jpg', traces='sources/traced/carrick.json'),
        production=dict(id='N514', work='build/production/carrick', sheets=('60pt', '36pt'))),
}
ZOOM = 4


# ---------------------------------------------------------------- glyph geometry
def glyph_polygons(font, name, tol=0.5):
    """The glyph's contours as polygons in font units (y up), curves flattened."""
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    gs = font.getGlyphSet(); pen = DecomposingRecordingPen(gs); gs[name].draw(pen)
    polys, cur, start = [], [], None
    def bez(pts, n):
        pts = np.array(pts, float); t = np.linspace(0, 1, n + 1)[1:, None]
        if len(pts) == 3:
            return (1 - t) ** 2 * pts[0] + 2 * (1 - t) * t * pts[1] + t ** 2 * pts[2]
        return ((1 - t) ** 3 * pts[0] + 3 * (1 - t) ** 2 * t * pts[1] + 3 * (1 - t) * t ** 2 * pts[2] + t ** 3 * pts[3])
    for op, args in pen.value:
        if op == 'moveTo':
            cur = [args[0]]
        elif op == 'lineTo':
            cur.append(args[0])
        elif op in ('curveTo', 'qCurveTo'):
            pts = [cur[-1], *args]
            if op == 'qCurveTo' and len(args) > 2:            # implied on-curve points
                ons = [pts[0]] + [tuple((np.array(a) + np.array(b)) / 2) for a, b in zip(args[:-2], args[1:-1])] + [args[-1]]
                for i, c in enumerate(args[:-1]):
                    cur.extend(map(tuple, bez([ons[i], c, ons[i + 1]], 16)))
                continue
            cur.extend(map(tuple, bez(pts, 24)))
        elif op in ('closePath', 'endPath'):
            if len(cur) > 2:
                polys.append(np.array(cur, float))
            cur = []
    return polys


def rasterise(polys, px, shape, origin):
    """Even-odd fill of font-unit polygons at px pixels per unit; origin = font point at pixel (0, 0)."""
    acc = np.zeros(shape, bool)
    for p in polys:
        q = (p - origin) * [px, -px]
        im = Image.new('1', (shape[1], shape[0]), 0)
        ImageDraw.Draw(im).polygon([tuple(v) for v in q], fill=1)
        acc ^= np.array(im, bool)
    return acc


# ---------------------------------------------------------------- sources
def ink_map(gray, paper=None, ink=None):
    """0 (paper) to 1 (ink) from a grey crop, levels from its own histogram unless given."""
    g = gray.astype(float)
    paper = np.percentile(g, 92) if paper is None else paper
    ink = np.percentile(g, 3) if ink is None else ink
    return np.clip((paper - g) / max(paper - ink, 1), 0, 1)


def own_ink(ink, mask, grow=6):
    """The ink of the letter itself: pieces that touch the registered glyph; neighbours are dropped."""
    from scipy import ndimage as ndi
    lab, n = ndi.label(ink > 0.35)
    near = ndi.binary_dilation(mask, iterations=grow)
    keep = np.unique(lab[near & (lab > 0)])
    sel = np.isin(lab, keep) | ndi.binary_dilation(mask, iterations=2)
    return np.where(ndi.binary_dilation(np.isin(lab, keep), iterations=2) & sel, ink, 0.0)


def register(ink, polys, px0, scales=np.linspace(0.97, 1.02, 21)):
    """The uniform scale and placement that best lay the glyph over the ink (normalised correlation)."""
    from scipy.signal import fftconvolve
    lo, hi = np.vstack(polys).min(0), np.vstack(polys).max(0)
    best = None
    for s in scales:
        px = px0 * s
        w, h = int(np.ceil((hi[0] - lo[0]) * px)) + 4, int(np.ceil((hi[1] - lo[1]) * px)) + 4
        if w >= ink.shape[1] or h >= ink.shape[0]:
            continue
        m = rasterise(polys, px, (h, w), np.array([lo[0] - 2 / px, hi[1] + 2 / px])).astype(float)
        k = m - m.mean()
        c = fftconvolve(ink - ink.mean(), k[::-1, ::-1], mode='valid')
        iy, ix = np.unravel_index(np.argmax(c), c.shape)
        # agreement of the placed mask with the ink, for choosing the scale
        sub = ink[iy:iy + h, ix:ix + w]
        iou = (np.minimum(sub, m).sum()) / max(np.maximum(sub, m).sum(), 1)
        if best is None or iou > best[0]:
            best = (iou, s, px, (ix, iy), np.array([lo[0] - 2 / px, hi[1] + 2 / px]), (h, w))
    if best is None:
        return None                                               # the crop is smaller than the glyph
    iou, s, px, (ix, iy), org, _ = best
    origin = org - np.array([ix / px, -iy / px])                  # font point at the crop's (0, 0)
    return dict(iou=float(iou), scale=float(s), px=float(px), origin=origin)


def locate_rows(base_img, copy_img, region, rows, step=3):
    """Where each base row of letters sits in a copy, and at what scale. A copy may re-set the line
    spacing (N47's lines are closer than N516's), so each row is found on its own."""
    from skimage.feature import match_template
    from skimage.transform import rescale
    x0, y0, x1, y1 = region
    c = rescale(ink_map(np.array(copy_img.convert('L'))[y0:y1, x0:x1]), 1 / step, anti_aliasing=True)
    b = ink_map(np.array(base_img.convert('L')))
    out = {}
    for rb in rows:
        t0 = rescale(b[rb[1]:rb[3], rb[0]:rb[2]], 1 / step, anti_aliasing=True)
        best = None
        for s in np.linspace(0.80, 1.30, 51):
            t = rescale(t0, s, anti_aliasing=True)
            if t.shape[0] >= c.shape[0] or t.shape[1] >= c.shape[1]:
                continue
            r = match_template(c, t)
            iy, ix = np.unravel_index(np.argmax(r), r.shape)
            if best is None or r[iy, ix] > best[0]:
                best = (float(r[iy, ix]), float(s), ix * step + x0, iy * step + y0)
        out[tuple(rb)] = dict(score=best[0], scale=best[1], offset=(best[2], best[3]))
    return out


def refine_box(base_ink, copy_gray, box, s, reach=14):
    """Refine a glyph's predicted box in a copy by matching the base glyph's own ink."""
    from skimage.feature import match_template
    from skimage.transform import rescale
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    t = rescale(base_ink, s, anti_aliasing=True)
    win = ink_map(copy_gray[max(y0 - reach, 0):y1 + reach, max(x0 - reach, 0):x1 + reach])
    if t.shape[0] >= win.shape[0] or t.shape[1] >= win.shape[1]:
        return box, 0.0
    r = match_template(win, t)
    iy, ix = np.unravel_index(np.argmax(r), r.shape)
    nx, ny = max(x0 - reach, 0) + ix, max(y0 - reach, 0) + iy
    return (nx, ny, nx + t.shape[1], ny + t.shape[0]), float(r[iy, ix])


def global_copy_transform(base_img, copy_img, region, step=4):
    """Scale and offset taking base (N516) pixels to a copy's (N47) pixels: the copy reproduces the
    base's paste-up, so one similarity transform places every letter to within a few pixels."""
    from skimage.feature import match_template
    from skimage.transform import rescale
    b = ink_map(np.array(base_img.convert('L')))
    x0, y0, x1, y1 = region
    c = ink_map(np.array(copy_img.convert('L'))[y0:y1, x0:x1])
    bs = rescale(b, 1 / step, anti_aliasing=True)
    best = None
    for s in np.linspace(0.85, 1.25, 41):
        t = rescale(bs, s, anti_aliasing=True)
        cs = rescale(c, 1 / step, anti_aliasing=True)
        if t.shape[0] >= cs.shape[0] or t.shape[1] >= cs.shape[1]:
            continue
        r = match_template(cs, t)
        iy, ix = np.unravel_index(np.argmax(r), r.shape)
        if best is None or r[iy, ix] > best[0]:
            best = (r[iy, ix], s, ix * step + x0, iy * step + y0)
    score, s, ox, oy = best
    return dict(scale=float(s), offset=(float(ox), float(oy)), score=float(score))


# ---------------------------------------------------------------- drawing
def panel(gray, ink, polys, reg, title, zoom=ZOOM):
    """The source at zoom with the outline over it, and the disagreement map beside it."""
    h, w = ink.shape
    ink = own_ink(ink, rasterise(polys, reg['px'], (h, w), reg['origin']))
    gray = np.where(ink > 0, gray, 255 - (255 - gray.astype(int)) // 4).astype(np.uint8)   # neighbours faded
    big = Image.fromarray(gray).convert('RGB').resize((w * zoom, h * zoom), Image.LANCZOS)
    d = ImageDraw.Draw(big)
    for p in polys:
        q = (p - reg['origin']) * [reg['px'] * zoom, -reg['px'] * zoom]
        d.line([tuple(v) for v in q] + [tuple(q[0])], fill=(220, 0, 0), width=2)
    m = rasterise(polys, reg['px'] * zoom, (h * zoom, w * zoom), reg['origin'])
    inkz = np.array(Image.fromarray((ink * 255).astype(np.uint8)).resize((w * zoom, h * zoom), Image.BILINEAR)) > 127
    diff = np.full((h * zoom, w * zoom, 3), 255, np.uint8)
    diff[inkz & m] = (150, 150, 150)
    diff[inkz & ~m] = (240, 140, 20)          # print has it, font lacks it
    diff[~inkz & m] = (40, 110, 230)          # font has it, print lacks it
    lab = f'{title}  iou {reg["iou"]:.3f}  scale {reg["scale"]:.3f}'
    return big, Image.fromarray(diff), lab


def to_font_space(ink, reg, lo, hi, upx):
    """A source's ink resampled onto a font-unit grid (upx units per pixel), through its registration."""
    from scipy.ndimage import map_coordinates
    X = np.arange(lo[0], hi[0], upx); Y = np.arange(hi[1], lo[1], -upx)
    gx, gy = np.meshgrid(X, Y)
    cx = (gx - reg['origin'][0]) * reg['px']; cy = -(gy - reg['origin'][1]) * reg['px']
    return map_coordinates(ink, [cy - 0.5, cx - 0.5], order=1, cval=0.0)


def consensus(layers, polys, upx=2.0, margin=40):
    """Prints overlaid in the font's own coordinates: black where they all print ink, a print's colour
    where only it does (N516 red, N47 green, N517 violet), with the font's outline in blue."""
    pts = np.vstack(polys); lo, hi = pts.min(0) - margin, pts.max(0) + margin
    cols = {'N516': (215, 40, 40), 'N513': (215, 40, 40), 'N47': (40, 160, 60), 'N517': (140, 60, 200), 'N514': (140, 60, 200)}
    maps = {k: to_font_space(own_ink(ink, rasterise(polys, reg['px'], ink.shape, reg['origin'])), reg, lo, hi, upx) > 0.5
            for k, (ink, reg) in layers.items()}
    shape = next(iter(maps.values())).shape
    img = np.full((*shape, 3), 255, np.uint8)
    count = np.sum(list(maps.values()), axis=0)
    img[(count > 1) & (count < len(maps))] = (150, 150, 150)       # some prints but not all
    img[count == len(maps)] = (30, 30, 30)
    for k, m in maps.items():
        img[m & (count == 1)] = cols.get(k, (120, 120, 120))
    im = Image.fromarray(img).resize((shape[1] * 2, shape[0] * 2), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for p in polys:
        q = (p - [lo[0], hi[1]]) * [2 / upx, -2 / upx]
        d.line([tuple(v) for v in q] + [tuple(q[0])], fill=(30, 90, 255), width=2)
    return im


def compose(rows, name, out):
    font = ImageFont.load_default()
    W = max(sum(i.width for i in r[:2]) + 30 for r in rows)
    H = sum(max(r[0].height, r[1].height) + 26 for r in rows)
    board = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(board); y = 0
    for big, diff, lab in rows:
        d.text((4, y + 4), lab, fill=(0, 0, 0), font=font)
        board.paste(big, (0, y + 20)); board.paste(diff, (big.width + 10, y + 20))
        y += max(big.height, diff.height) + 26
    board.save(out / f'{name}.png')


def crop(img, box, pad):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    return np.array(img.convert('L').crop((x0 - pad, y0 - pad, x1 + pad, y1 + pad)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('face'); ap.add_argument('font')
    ap.add_argument('--glyphs', nargs='*'); ap.add_argument('--out', type=Path)
    ap.add_argument('--evidence', type=Path, help="a round's evidence.json (default: the face's base round)")
    args = ap.parse_args()
    from fontTools.ttLib import TTFont
    cfg = SOURCES[args.face]; tu = TRACE_UNIT[args.face]
    out = args.out or ROOT / 'build' / 'judgement' / args.face; out.mkdir(parents=True, exist_ok=True)
    font = TTFont(args.font); cmap = font.getBestCmap(); order = set(font.getGlyphOrder())
    ev = {g['name']: g for g in json.load(open(args.evidence or ROOT / cfg['base']['evidence']))['glyphs']}
    base_img = Image.open(SPECIMENS / cfg['base']['file'])
    all_regions = json.load(open(ROOT / Path(cfg['base']['evidence']).parent / 'source-regions.json'))
    regions = {g['name']: g for g in all_regions[cfg['base']['file']]}
    calibration = json.load(open(ROOT / cfg['base']['evidence'])).get('calibration', {})
    rows = rows_ = sorted({tuple(g['row_box']) for g in regions.values()}, key=lambda r: r[1])
    copies = []
    for c in cfg['copies']:
        img = Image.open(SPECIMENS / c['file'])
        if c.get('direct'):
            # the copy's own boxes, at its own calibration
            loc = dict(direct={g['name']: g['box'] for g in all_regions[c['file']]},
                       scale=calibration[c['file']]['scale'] / calibration[cfg['base']['file']]['scale'])
            copies.append((c, img, loc)); continue
        loc = locate_rows(base_img, img, c['region'], rows)
        for rb, t in loc.items():
            print(f'{c["id"]} row {rb}: scale {t["scale"]:.3f}, at {t["offset"]}, score {t["score"]:.3f}')
        copies.append((c, img, loc))
    flyer_img = Image.open(ROOT / cfg['flyer']['file'])
    flyer = {g['name']: g for g in json.load(open(ROOT / cfg['flyer']['traces']))['glyphs']}
    prod = ROOT / cfg['production']['work']
    report = {}
    names = args.glyphs or [n for n in ev if n in order]
    for name in names:
        g = ev.get(name)
        base_file = cfg['base']['file']
        on_base = 'box' in g if g else False
        if g is not None and on_base and not (g.get('source', base_file).startswith(base_file) or g.get('proportion_source') == base_file):
            on_base = False                # drawn from another source (round 2's v and w are N47's)
        if g is None or name not in order or not (on_base or g.get('source_id') == cfg['production']['id']):
            continue                       # retained
        polys = glyph_polygons(font, name)
        if not polys:
            continue
        rows, rep, layers = [], {}, {}
        pad = 24
        if on_base:
            px0 = g['scale'] / tu                                    # source px per font unit
            gray = crop(base_img, g['box'], pad); ink = ink_map(gray)
            reg = register(ink, polys, px0)
            if reg is None:
                print(name, 'skipped: its box is smaller than the glyph'); continue
            rows.append(panel(gray, ink, polys, reg, f'{name} · {cfg["base"]["id"]}'))
            rep[cfg['base']['id']] = round(reg['iou'], 4)
            layers = {cfg['base']['id']: (ink, reg)}
            base_ink = own_ink(ink, rasterise(polys, reg['px'], ink.shape, reg['origin']))[pad:-pad, pad:-pad]
        for c, img, loc in (copies if on_base else []):
            if 'direct' in loc:
                if name not in loc['direct']:
                    continue
                box, s = loc['direct'][name], loc['scale']
            else:
                rb = tuple(regions[name]['row_box']) if name in regions else rows_[g['row']] if 'row' in g else None
                if rb not in loc or loc[rb]['score'] < 0.3:
                    continue
                t = loc[rb]; b = g['box']; s = t['scale']; ox, oy = t['offset']
                box = ((b[0] - rb[0]) * s + ox, (b[1] - rb[1]) * s + oy, (b[2] - rb[0]) * s + ox, (b[3] - rb[1]) * s + oy)
                box, score = refine_box(base_ink, np.array(img.convert('L')), box, s)
            gray = crop(img, box, int(pad * s)); ink = ink_map(gray)
            reg = register(ink, polys, px0 * s)
            if reg is None:
                continue
            rows.append(panel(gray, ink, polys, reg, f'{name} · {c["id"]}'))
            rep[c['id']] = round(reg['iou'], 4)
            layers[c['id']] = (ink, reg)
        if name in flyer:
            from fontTools.pens.recordingPen import RecordingPen
            pts = np.array([p for op, a in flyer[name]['rec'] for p in a], float)
            lo, hi = pts.min(0), pts.max(0)
            gray = crop(flyer_img, (*lo, *hi), 8); ink = ink_map(gray)
            reg = register(ink, polys, 1 / tu, scales=np.linspace(0.9, 1.1, 41))
            if reg is None:
                continue
            rows.append(panel(gray, ink, polys, reg, f'{name} · flyer', zoom=ZOOM * 2))
            rep['flyer'] = round(reg['iou'], 4)
        sheet = next((sh for sh in cfg['production']['sheets'] if (prod / f'mean-{name}@{sh}.npy').exists()), None)
        mean = prod / f'mean-{name}@{sheet}.npy'
        if sheet:
            reg_meta = json.load(open(prod / 'registration.json')).get(f'{name}@{sheet}', {})
            m = np.load(mean).astype(float); lo_, hi_ = np.percentile(m, 2), np.percentile(m, 98)
            ink = np.clip((m - lo_) / max(hi_ - lo_, 1e-6), 0, 1)
            gray = ((1 - ink) * 255).astype(np.uint8)
            step = reg_meta.get('step', 0.125)
            reg = register(ink, polys, 1 / (tu * step))
            if reg is None:
                continue
            rows.append(panel(gray, ink, polys, reg, f'{name} · {cfg["production"]["id"]} {sheet} mean of {reg_meta.get("n", "?")}', zoom=max(1, ZOOM // 2)))
            rep[cfg['production']['id']] = round(reg['iou'], 4)
            layers[cfg['production']['id']] = (ink, reg)
        if not rows:
            continue
        compose(rows, name, out)
        consensus(layers, polys).save(out / f'{name}-consensus.png')
        report[name] = rep
        print(name, rep, flush=True)
    json.dump(report, open(out / 'agreement.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
