"""One scorecard for every release: the same measurements on any folder of fonts, kept across versions.

usage: python scripts/scorecard.py [FONTDIR] [--out research/scorecard/NAME.json] [--compare OLD.json] [--styles Regular ...]

FONTDIR holds otf/ (as fonts/ does) or the .otf files themselves (as build/fonts does). Every measure is
of what the eye or a typesetter meets, taken from the shaped font, not from the build's own bookkeeping:

  marks      every letter with every combining mark: the pairs whose outlines overlap (the cedilla and
             ogonek join their letter by design and are left out), and the letters with no mark anchor;
  pairs      every pair of the text characters, shaped with kerning: pairs whose ink overlaps, and pairs
             whose outlines come within NEAR units of each other (the true distance, in any direction);
  linebox    glyphs that rise above or fall below the typographic line box, and the clipping box;
  rhythm     how even the white between letters is in real text: for each adjacent pair the mean white
             between the two letters over the x-height band, weighted by how often the pair occurs in the
             corpus (Irish and English prose). The score is the weighted coefficient of variation of that
             white (0 is perfectly even) and the worst pairs are listed, most frequent first. It is a
             comparison between versions of one face, not a standard: a face with open letters (c, r, t)
             can never score 0.

Nothing here judges fidelity to the 1978 prints (scripts/validate.py does that against the flyer).
"""
import argparse, json, math, sys, unicodedata
from collections import Counter
from pathlib import Path
import numpy as np
import pathops
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.freetypePen import FreeTypePen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.basePen import BasePen
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parent.parent
NEAR = 8                 # font units: closer than this, two letters read as touching at text sizes
GRID = 4                 # font units per profile row and column
JOINING = {0x327, 0x328}  # cedilla and ogonek are drawn into their letter
TEXT = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        "áéíóúÁÉÍÓÚḃċḋḟġṁṗṡṫḂĊḊḞĠṀṖṠṪàèìòùâêîôûäëïöüçñ"
        ".,;:!?'\"‘’“”()[]-–—/&⁊«»")
# Prose for the pair frequencies. The Irish is from the project's own sample texts (plain statements of
# history, as the proof sets them) and common words; the English is the proof's. Weighted 2:1 to Irish.
CORPUS_GA = (
    "Tógadh Brú na Bóinne timpeall 3200 RC, roimh phirimidí na hÉigipte. Scríobhadh Leabhar Cheanannais "
    "timpeall na bliana 800, agus tá sé i gColáiste na Tríonóide i mBaile Átha Cliath. Troideadh Cath "
    "Chluain Tarbh sa bhliain 1014, agus maraíodh Brian Bóramha ann. Chuir Mícheál Ó Cléirigh agus a "
    "chomhghleacaithe Annála na gCeithre Máistrí le chéile idir 1632 agus 1636. Is fearr Gaeilge bhriste "
    "ná Béarla cliste. Tír gan teanga, tír gan anam. Ní neart go cur le chéile. Tús maith leath na hoibre. "
    "Is glas iad na cnoic i bhfad uainn. Leabhar na hUidhre. Tuaim Dhá Ghualann. Cill Chainnigh. "
    "an bhfuil tú ag dul go dtí an siopa inniu nó amárach agus cad é mar atá tú. bhí sé ann ach ní raibh sí "
    "ansin nuair a tháinig siad abhaile ón scoil leis na páistí eile")
CORPUS_EN = (
    "In 1978 Letraset, the Kilkenny Design Workshops and D. O'Sullivan Graphic Supplies asked designers for "
    "an Irish typeface. Four were chosen and sold as dry-transfer lettering: Céilí by Hermann Hecht, "
    "Carrick and Kilfane by William Curran, and Tuam Uncial by Jarlath Hayes. The quick brown fox jumps "
    "over the lazy dog. The type was rubbed down letter by letter from a sheet, with the spacing marks to guide it.")


def fonts_in(folder, styles=None):
    folder = Path(folder)
    files = sorted((folder / 'otf').glob('*.otf')) if (folder / 'otf').is_dir() else sorted(folder.glob('*.otf'))
    return [f for f in files if not styles or f.stem.split('-')[-1] in styles]


class Shaped:
    def __init__(self, path):
        self.path = Path(path); self.tt = TTFont(path); self.gs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder(); self.cmap = self.tt.getBestCmap()
        self.hb = hb.Font(hb.Face(self.path.read_bytes()))
        os2, hhea = self.tt['OS/2'], self.tt['hhea']
        self.typo = (os2.sTypoAscender, os2.sTypoDescender); self.win = (os2.usWinAscent, -os2.usWinDescent)
        self.xh = getattr(os2, 'sxHeight', 0) or 500
        self.lo = min(self.win[1], hhea.descent) - 4 * GRID; self.hi = max(self.win[0], hhea.ascent) + 4 * GRID
        self.rows = int((self.hi - self.lo) / GRID); self._prof, self._path = {}, {}

    def shape(self, text, features=None):
        buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties(); hb.shape(self.hb, buf, features or {})
        return [(self.order[i.codepoint], p.x_advance, p.x_offset, p.y_offset) for i, p in zip(buf.glyph_infos, buf.glyph_positions)]

    def outline(self, name, dx=0, dy=0):
        p = pathops.Path(); self.gs[name].draw(TransformPen(p.getPen(), (1, 0, 0, 1, dx, dy)))
        return p

    def profile(self, name):
        """The glyph's left and right ink edge on each GRID row (font units from its origin; nan where no ink)."""
        if name not in self._prof:
            pen = FreeTypePen(self.gs); self.gs[name].draw(pen)
            b = self.outline(name).bounds
            if not b or b[2] <= b[0]:
                self._prof[name] = None
            else:
                x0 = int(np.floor(b[0] / GRID)) - 1; w = int(np.ceil(b[2] / GRID)) + 1 - x0
                a = pen.array(width=w, height=self.rows, transform=(1 / GRID, 0, 0, 1 / GRID, -x0, -self.lo / GRID), contain=False)
                ink = a[::-1] > 0.5                      # row 0 is the lowest
                any_ = ink.any(axis=1)
                left = np.where(any_, (ink.argmax(axis=1) + x0) * GRID, np.nan)
                right = np.where(any_, (w - ink[:, ::-1].argmax(axis=1) + x0) * GRID, np.nan)
                self._prof[name] = (left, right)
        return self._prof[name]


def widen(edge, how, rows):
    """An edge's reach within `rows` rows up and down (the nearer edge wins)."""
    out = edge.copy()
    for k in range(1, rows + 1):
        for sh in (np.r_[edge[k:], [np.nan] * k], np.r_[[np.nan] * k, edge[:-k]]):
            out = how(out, sh)
    return out


def marks(f):
    cm = f.cmap
    mks = sorted(cp for cp in cm if unicodedata.category(chr(cp)) == 'Mn' and cp not in JOINING)
    bases = sorted(cp for cp in cm if unicodedata.category(chr(cp)) in ('Lu', 'Ll', 'Lo'))
    unanchored, hits, n, nxt = set(), [], 0, []
    after = [c for c in 'jpgnlf' if ord(c) in cm]
    for b in bases:
        for m in mks:
            g = f.shape(chr(b) + chr(m))
            if len(g) != 2:
                continue                                # composed into one glyph
            n += 1
            (g0, adv, _, _), (g1, _, dx, dy) = g
            if dx == 0 and dy == 0:
                unanchored.add(chr(b))
            pa, pb = f.outline(g0), f.outline(g1, adv + dx, dy)
            if not pa.bounds or not pb.bounds:
                continue
            x = pathops.op(pa, pb, pathops.PathOp.INTERSECTION, fix_winding=True)
            area = abs(x.area) if x.bounds else 0
            if area > 4:
                hits.append((chr(b), f'{m:04X}', int(round(area))))
            for c in after:                              # and the mark must not land on the letter that follows
                g3 = f.shape(chr(b) + chr(m) + c)
                if len(g3) != 3:
                    continue
                x3 = pathops.op(f.outline(g3[1][0], g3[0][1] + g3[1][2], g3[1][3]), f.outline(g3[2][0], g3[0][1] + g3[1][1] + g3[2][2]),
                                pathops.PathOp.INTERSECTION, fix_winding=True)
                if x3.bounds and abs(x3.area) > 4:
                    nxt.append((chr(b) + c, f'{m:04X}', int(round(abs(x3.area)))))
    return dict(pairs=n, colliding=len(hits), letters_colliding=''.join(sorted({h[0] for h in hits})),
                unanchored=''.join(sorted(unanchored)), worst=sorted(hits, key=lambda h: -h[2])[:12],
                on_next_letter=len(nxt), on_next_worst=sorted(nxt, key=lambda h: -h[2])[:12])


def pair_gap(f, a, b, rows=NEAR // GRID):
    g = f.shape(a + b)
    if len(g) != 2:
        return None
    (ga, adv, _, _), (gb, _, dx, _) = g
    pa, pb = f.profile(ga), f.profile(gb)
    if pa is None or pb is None:
        return None
    key = ('wide', rows)
    if (ga, key) not in f._prof: f._prof[ga, key] = widen(pa[1], np.fmax, rows)
    if (key, gb) not in f._prof: f._prof[key, gb] = widen(pb[0], np.fmin, rows)
    right, left = f._prof[ga, key], f._prof[key, gb]
    gap = adv + dx + left - right
    return None if np.all(np.isnan(gap)) else float(np.nanmin(gap))


class Sampler(BasePen):
    """Points along an outline, about 2 units apart."""
    def __init__(self, gs):
        super().__init__(gs); self.pts = []
    def _moveTo(self, p): self.pts.append(p)
    def _lineTo(self, p):
        a = np.array(self._getCurrentPoint()); b = np.array(p); n = max(1, int(np.hypot(*(b - a)) / 2))
        self.pts += [tuple(a + (b - a) * t) for t in np.linspace(0, 1, n + 1)[1:]]
    def _curveToOne(self, p1, p2, p3):
        p0 = np.array(self._getCurrentPoint()); p1, p2, p3 = map(np.array, (p1, p2, p3))
        n = max(2, int((np.hypot(*(p1 - p0)) + np.hypot(*(p2 - p1)) + np.hypot(*(p3 - p2))) / 2))
        for t in np.linspace(0, 1, n + 1)[1:]:
            self.pts.append(tuple((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3))


def distance(f, ga, gb, shift):
    """The least distance between two glyphs' outlines, the second moved right by `shift`; 0 if their ink overlaps."""
    def pts(n):
        if ('pts', n) not in f._prof:
            pen = Sampler(f.gs); f.gs[n].draw(pen); f._prof['pts', n] = (np.array(pen.pts), cKDTree(np.array(pen.pts)))
        return f._prof['pts', n]
    x = pathops.op(f.outline(ga), f.outline(gb, shift), pathops.PathOp.INTERSECTION, fix_winding=True)
    if x.bounds and abs(x.area) > 4:
        return 0.0
    return float(pts(ga)[1].query(pts(gb)[0] + (shift, 0))[0].min())


def pairs(f):
    chars = [c for c in TEXT if ord(c) in f.cmap]
    touching, near, n = [], [], 0
    for a in chars:
        for b in chars:
            d = pair_gap(f, a, b)
            if d is None:
                continue
            n += 1
            if d < NEAR:                               # a candidate: now the true distance between the outlines
                (ga, adv, _, _), (gb, _, dx, _) = f.shape(a + b)
                d = distance(f, ga, gb, adv + dx)
                if d <= 0:
                    touching.append((a + b, 0))
                elif d < NEAR:
                    near.append((a + b, round(d, 1)))
    return dict(pairs=n, touching=len(touching), near=len(near),
                touching_list=[p for p, _ in touching][:40],
                near_list=sorted(near, key=lambda t: t[1])[:60])


def linebox(f):
    over, under, clip = [], [], []
    rev = {}
    for cp, n in f.cmap.items():
        rev.setdefault(n, cp)
    for n in f.order:
        b = f.outline(n).bounds
        if not b:
            continue
        label = chr(rev[n]) if n in rev else n
        if b[3] > f.typo[0]: over.append((label, int(b[3] - f.typo[0])))
        if b[1] < f.typo[1]: under.append((label, int(f.typo[1] - b[1])))
        if b[3] > f.win[0] or b[1] < f.win[1]: clip.append(label)
    return dict(typo=f.typo, win=f.win, above=sorted(over, key=lambda t: -t[1]), below=sorted(under, key=lambda t: -t[1]), clipped=clip)


def rhythm(f):
    """The white between adjacent letters in prose, over the x-height band, and how even it is."""
    freq = Counter()
    for text, w in ((CORPUS_GA, 2), (CORPUS_EN, 1)):
        for word in text.split():
            word = ''.join(c for c in word if unicodedata.category(c)[0] == 'L')
            for a, b in zip(word, word[1:]):
                freq[a + b] += w
    r0, r1 = int((0 - f.lo) / GRID), int((f.xh - f.lo) / GRID)
    lean = math.tan(math.radians(-f.tt['post'].italicAngle)) * ((np.arange(f.rows) + 0.5) * GRID + f.lo - f.xh / 2)
    cap = 0.5 * f.xh                                    # white deeper than this is not felt between two letters
    white = {}
    for pr in freq:
        g = f.shape(pr)
        if len(g) != 2:
            continue
        (ga, adv, _, _), (gb, _, dx, _) = g
        pa, pb = f.profile(ga), f.profile(gb)
        if pa is None or pb is None:
            continue
        pa, pb = [(l - lean, r - lean) for l, r in (pa, pb)]      # a sloped style is measured upright
        # each side's white from the pair's midline, capped: an open side counts as a deep but bounded bay
        mid = (np.nanmax(pa[1][r0:r1]) + adv + dx + np.nanmin(pb[0][r0:r1])) / 2
        wl = np.clip(mid - np.nan_to_num(pa[1][r0:r1], nan=-1e9), 0, cap / 2)
        wr = np.clip(adv + dx + np.nan_to_num(pb[0][r0:r1], nan=1e9) - mid, 0, cap / 2)
        white[pr] = float((wl + wr).mean())
    if not white:
        return {}
    ps = sorted(white); w = np.array([freq[p] for p in ps], float); v = np.array([white[p] for p in ps])
    mean = float((w * v).sum() / w.sum()); sd = float(np.sqrt((w * (v - mean) ** 2).sum() / w.sum()))
    dev = sorted(((p, round(white[p] - mean), freq[p]) for p in ps), key=lambda t: -abs(t[1]) * t[2] ** 0.5)
    return dict(pairs=len(ps), mean_white=round(mean, 1), cv=round(sd / mean, 4), xheight=f.xh,
                tightest=[d for d in dev if d[1] < 0][:10], loosest=[d for d in dev if d[1] > 0][:10])


def score(path):
    f = Shaped(path)
    return dict(marks=marks(f), pairs=pairs(f), linebox=linebox(f), rhythm=rhythm(f))


def headline(s):
    return dict(mark_collisions=s['marks']['colliding'], marks_on_next_letter=s['marks'].get('on_next_letter'), letters_without_anchor=len(s['marks']['unanchored']),
                pairs_touching=s['pairs']['touching'], pairs_near=s['pairs']['near'],
                above_linebox=len(s['linebox']['above']), below_linebox=len(s['linebox']['below']),
                clipped=len(s['linebox']['clipped']), rhythm_cv=s['rhythm'].get('cv'))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('fontdir', nargs='?', default=str(ROOT / 'fonts'))
    ap.add_argument('--out'); ap.add_argument('--compare'); ap.add_argument('--styles', nargs='*')
    a = ap.parse_args()
    result = {}
    for p in fonts_in(a.fontdir, a.styles):
        result[p.stem] = score(p)
        print(p.stem, json.dumps(headline(result[p.stem])), flush=True)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    if a.compare:
        old = json.loads(Path(a.compare).read_text(encoding='utf-8'))
        print('\nagainst', a.compare)
        for name, s in result.items():
            if name in old:
                h0, h1 = headline(old[name]), headline(s)
                d = {k: (h0[k], h1[k]) for k in h1 if h0[k] != h1[k]}
                print(' ', name, d or 'unchanged')


if __name__ == '__main__':
    main()
