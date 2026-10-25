#!/usr/bin/env python3
"""Full-coverage build of Kilfane, Tuam Uncial, Carrick and Céilí from the v2 traces."""
import paths
import math, os, subprocess, sys, unicodedata
import numpy as np
import pathops
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.recordingPen import RecordingPen, replayRecording
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.ttLib import TTFont
from fontTools.agl import UV2AGL

import bolden
import glyphs as GL
from glyphs import bounds, contours, translate
from metrics import stats
from spacing import side_depths, sidebearings, profiles
import shapes as SH
from marks import MarkSet
from letters import make_letters, stem_at, clip
from symbols import make_symbols

OUT = paths.FONTS
VERSION = '2.010'
RELEASE_DATE = '2026-10-25'          # stamped into head.created/modified, so a rebuild is byte-identical
import calendar as _cal, time as _time
os.environ.setdefault('SOURCE_DATE_EPOCH', str(_cal.timegm(_time.strptime(RELEASE_DATE, '%Y-%m-%d'))))  # fontTools saves honour it
DIGITS = 'zero one two three four five six seven eight nine'.split()

FONTS = {
    'kilfane': dict(family='Kilfane', ps='Kilfane', designer='William Curran', unicase=False, style='round',
                    lining=True, mark_weight=0.46, gap=0.09, note='Commended (£25)',
                    alts={'A': ['A.alt1', 'A.alt2'], 'D': ['D.alt1'], 'S': ['S.alt1'], 'T': ['T.alt1'],
                          'Y': ['Y.alt1'], 'd': ['d.alt1'], 'f': ['f.alt1'], 'g': ['g.alt1'],
                          'l': ['l.alt1'], 't': ['t.alt1'], 'y': ['y.alt1']},
                    sets=[('ss01', 'Roman forms', {'A': 'A.alt2', 'T': 'T.alt1', 'Y': 'Y.alt1', 'd': 'd.alt1',
                                                   'f': 'f.alt1', 'l': 'l.alt1', 't': 't.alt1', 'y': 'y.alt1'}),
                          ('ss02', 'Insular forms', {'A': 'A.alt1', 'D': 'D.alt1', 'S': 'S.alt1', 'g': 'g.alt1'})],
                    insular={0xA779: 'D.alt1', 0xA77A: 'd', 0x1D79: 'g.alt1', 0xA77D: 'g.alt1', 0xA786: 'T', 0xA787: 't'}),
    'tuam': dict(family='Tuam Uncial', ps='TuamUncial', designer='Jarlath Hayes', unicase=True, style='square',
                 lining=True, mark_weight=0.40, gap=0.035, note='Commended (£25)', alts={}, sets=[],
                 insular={0xA786: 't', 0xA787: 't'}),
    'carrick': dict(family='Carrick', ps='Carrick', designer='William Curran', unicase=True, style='chisel',
                    lining=True, mark_weight=0.44, gap=0.08, note='Highly Commended (£50)', alts={}, sets=[],
                    insular={0xA779: 'd', 0xA77A: 'd', 0xA786: 't', 0xA787: 't'}),
    'ceili': dict(family='Céilí', ps='Ceili', designer='Hermann Hecht', unicase=True, style='round',
                  lining=False, mark_weight=0.48, gap=0.09, note='First prize (£250 and a silver medallion)',
                  alts={'a': ['a.alt1', 'a.alt2'], 'd': ['d.alt1'], 'e': ['e.alt1'], 'j': ['j.alt1'],
                        'l': ['l.alt1'], 'n': ['n.alt1'], 'r': ['r.alt1'], 's': ['s.alt1'], 'v': ['v.alt1']},
                  sets=[('ss01', 'Insular r and s', {'r': 'r.alt1', 's': 's.alt1'}),
                        ('ss02', 'Uncial A and N', {'a': 'a.alt2', 'n': 'n.alt1'}),
                        ('ss03', 'Alternate a d e j l v', {'a': 'a.alt1', 'd': 'd.alt1', 'e': 'e.alt1',
                                                           'j': 'j.alt1', 'l': 'l.alt1', 'v': 'v.alt1'})],
                  insular={0xA779: 'd', 0xA77A: 'd', 0xA77B: 'f', 0xA77C: 'f', 0xA77D: 'g', 0x1D79: 'g',
                           0xA782: 'r.alt1', 0xA783: 'r.alt1', 0xA784: 's.alt1', 0xA785: 's.alt1',
                           0xA786: 't', 0xA787: 't'}),
}
KS = {'kilfane': 68.8, 'tuam': 92.8, 'carrick': 72.1, 'ceili': 81.6}   # spacing target calibrated on the sheet
LOOSEN = 1.06

# ------------------------------------------------------------------ the 2026 styles
# Bold and sloped styles are new work, drawn from the 1978 regulars. Only Céilí and Kilfane get a
# bold: Carrick and Tuam Uncial are already black (stems 37-39% of the x-height), and a heavier cut
# would close their counters and Tuam's hairline cuts.
STYLES = {'Regular': (False, False), 'Italic': (False, True), 'Bold': (True, False), 'Bold Italic': (True, True)}
FAMILY_STYLES = {'kilfane': ['Regular', 'Italic', 'Bold', 'Bold Italic'], 'ceili': ['Regular', 'Italic', 'Bold', 'Bold Italic'],
                 'carrick': ['Regular', 'Italic'], 'tuam': ['Regular', 'Italic']}
# the wider pen: growth across (rx) and up and down (ry) in the face's own contrast, a slight widening
# (k) so the counters stay open, and spacing scaled with the counters
BOLD = {'kilfane': dict(rx=24.2, ry=17.4, k=1.03, space=0.92),
        # the tip of Céilí's 6 reaches for its stem across a gap narrower than the bold's pen: there
        # the two meet, rather than the gap being kept as a crack
        'ceili': dict(rx=27.9, ry=5.9, k=1.043, space=0.92, joins=('six',))}
SLANT = 8.0          # degrees
CONDENSE = 0.96      # the sloped styles are a little narrower, with their stems kept

COMB = {0x300: 'grave', 0x301: 'acute', 0x302: 'circumflex', 0x303: 'tilde', 0x304: 'macron', 0x306: 'breve',
        0x307: 'dot', 0x308: 'dieresis', 0x30A: 'ring', 0x30B: 'hungarumlaut', 0x30C: 'caron', 0x312: 'commaturned',
        0x326: 'commabelow', 0x327: 'cedilla', 0x328: 'ogonek'}
BOTTOM = {'commabelow', 'cedilla', 'ogonek'}
SPECIAL = {0x0122: ('G', ['commabelow']), 0x0123: ('g', ['commaturned']), 0x0136: ('K', ['commabelow']),
           0x0137: ('k', ['commabelow']), 0x013B: ('L', ['commabelow']), 0x013C: ('l', ['commabelow']),
           0x0145: ('N', ['commabelow']), 0x0146: ('n', ['commabelow']), 0x0156: ('R', ['commabelow']),
           0x0157: ('r', ['commabelow']), 0x010F: ('d', ['caronvert']), 0x013D: ('L', ['caronvert']),
           0x013E: ('l', ['caronvert']), 0x0165: ('t', ['caronvert'])}
SPACING_MARKS = {0x60: 'grave', 0xA8: 'dieresis', 0xAF: 'macron', 0xB4: 'acute', 0xB8: 'cedilla', 0x2C6: 'circumflex',
                 0x2C7: 'caron', 0x2D8: 'breve', 0x2D9: 'dot', 0x2DA: 'ring', 0x2DB: 'ogonek', 0x2DC: 'tilde',
                 0x2DD: 'hungarumlaut'}
OTHER = {  # code point -> glyph built elsewhere
    0x20: 'space', 0x21: 'exclam', 0x22: 'quotedbl', 0x23: 'numbersign', 0x24: 'dollar', 0x25: 'percent',
    0x26: 'ampersand', 0x27: 'quotesingle', 0x28: 'parenleft', 0x29: 'parenright', 0x2A: 'asterisk', 0x2B: 'plus',
    0x2C: 'comma', 0x2D: 'hyphen', 0x2E: 'period', 0x2F: 'slash', 0x3A: 'colon', 0x3B: 'semicolon', 0x3C: 'less',
    0x3D: 'equal', 0x3E: 'greater', 0x3F: 'question', 0x40: 'at', 0x5B: 'bracketleft', 0x5C: 'backslash',
    0x5D: 'bracketright', 0x5E: 'asciicircum', 0x5F: 'underscore', 0x7B: 'braceleft', 0x7C: 'bar',
    0x7D: 'braceright', 0x7E: 'asciitilde', 0xA0: 'space', 0xA1: 'exclamdown', 0xA2: 'cent', 0xA3: 'sterling',
    0xA4: 'currency', 0xA5: 'yen', 0xA6: 'brokenbar', 0xA7: 'section', 0xA9: 'copyright', 0xAA: 'ordfeminine',
    0xAB: 'guillemotleft', 0xAC: 'logicalnot', 0xAE: 'registered', 0xB0: 'degree',
    0xB1: 'plusminus', 0xB2: 'twosuperior', 0xB3: 'threesuperior', 0xB5: 'mu', 0xB6: 'paragraph',
    0xB7: 'periodcentered', 0xB9: 'onesuperior', 0xBA: 'ordmasculine', 0xBB: 'guillemotright', 0xBC: 'onequarter',
    0xBD: 'onehalf', 0xBE: 'threequarters', 0xBF: 'questiondown', 0xD7: 'multiply', 0xF7: 'divide',
    0xC6: 'AE', 0xE6: 'ae', 0xD8: 'Oslash', 0xF8: 'oslash', 0xD0: 'Eth', 0xF0: 'eth', 0xDE: 'Thorn', 0xFE: 'thorn',
    0xDF: 'germandbls', 0x110: 'Dcroat', 0x111: 'dcroat', 0x126: 'Hbar', 0x127: 'hbar', 0x131: 'dotlessi',
    0x132: 'IJ', 0x133: 'ij', 0x138: 'kgreenlandic', 0x13F: 'Ldot', 0x140: 'ldot', 0x141: 'Lslash', 0x142: 'lslash',
    0x149: 'napostrophe', 0x14A: 'Eng', 0x14B: 'eng', 0x152: 'OE', 0x153: 'oe', 0x166: 'Tbar', 0x167: 'tbar',
    0x17F: 'longs', 0x237: 'dotlessj', 0x2010: 'hyphen', 0x2011: 'hyphen', 0x2013: 'endash', 0x2014: 'emdash',
    0x2018: 'quoteleft', 0x2019: 'quoteright', 0x201A: 'quotesinglbase', 0x201C: 'quotedblleft',
    0x201D: 'quotedblright', 0x201E: 'quotedblbase', 0x2020: 'dagger', 0x2021: 'daggerdbl', 0x2022: 'bullet',
    0x2026: 'ellipsis', 0x2030: 'perthousand', 0x2032: 'minute', 0x2033: 'second', 0x2039: 'guilsinglleft',
    0x203A: 'guilsinglright', 0x2044: 'fraction', 0x204A: 'uni204A', 0x20AC: 'Euro', 0x2122: 'trademark',
    0x2212: 'minus', 0x2248: 'approxequal', 0x2260: 'notequal', 0x2264: 'lessequal', 0x2265: 'greaterequal',
    0xE000: 'uniE000'}
for i, d in enumerate(DIGITS):
    OTHER[0x30 + i] = d
# precomposed letters to build by decomposition
COMPOSED = (list(range(0xC0, 0x100)) + list(range(0x100, 0x180)) + [0x218, 0x219, 0x21A, 0x21B] +
            [0x1E02, 0x1E03, 0x1E0A, 0x1E0B, 0x1E1E, 0x1E1F, 0x1E40, 0x1E41, 0x1E56, 0x1E57, 0x1E60, 0x1E61,
             0x1E6A, 0x1E6B, 0x1E80, 0x1E81, 0x1E82, 0x1E83, 0x1E84, 0x1E85, 0x1EF2, 0x1EF3])


def gname(cp):
    return UV2AGL.get(cp) or ('uni%04X' % cp)


def decompose(cp):
    if cp in SPECIAL:
        return SPECIAL[cp]
    d = unicodedata.normalize('NFD', chr(cp))
    if len(d) < 2 or not d[0].isascii() or not d[0].isalpha():
        return None
    marks = [COMB.get(ord(c)) for c in d[1:]]
    if None in marks:
        return None
    return d[0], marks


def remap(p, fn):
    """Apply a point-wise (non-affine) mapping to every point of a path."""
    rec = RecordingPen(); p.draw(rec)
    out = [(op, tuple(fn(*pt) for pt in args)) for op, args in rec.value]
    q = pathops.Path(); replayRecording(out, q.getPen())
    return pathops.simplify(q, fix_winding=True, keep_starting_points=False, clockwise=False)


def resize_bar(p, L):
    """Lengthen or shorten a horizontal rule to width L, keeping both drawn ends."""
    x0, y0, x1, y1 = bounds(p); W = x1 - x0; cx = (x0 + x1) / 2
    if abs(L - W) < 1:
        return p
    if L < W:
        d = W - L
        return SH.union(clip(p, x1=cx - d / 2 + 1), translate(clip(p, x0=cx + d / 2 - 1), -d, 0))
    d = L - W
    ys, Lp, Rp = profiles(SH.transform(p, (0, 1, 1, 0, 0, 0)), cx - 2, cx + 2, step=2)
    lo, hi = np.nanmin(Lp), np.nanmax(Rp)
    mid = SH.polygon([(cx - 1, lo), (cx + d + 1, lo), (cx + d + 1, hi), (cx - 1, hi)])
    return SH.union(clip(p, x1=cx + 1), mid, translate(clip(p, x0=cx - 1), d, 0))


def top_under(p, xa, xb, step=6):
    rot = SH.transform(p, (0, 1, 1, 0, 0, 0))
    ys, L, R = profiles(rot, xa, xb, step=step)
    return np.nanmax(R) if not np.all(np.isnan(R)) else bounds(p)[3]


def bottom_under(p, xa, xb, step=6):
    rot = SH.transform(p, (0, 1, 1, 0, 0, 0))
    ys, L, R = profiles(rot, xa, xb, step=step)
    return np.nanmin(L) if not np.all(np.isnan(L)) else bounds(p)[1]


def ink_x_extent(p, y0, y1):
    ys, L, R = profiles(p, y0, y1, step=6)
    if np.all(np.isnan(L)):
        b = bounds(p); return b[0], b[2]
    return np.nanmin(L), np.nanmax(R)


from fontTools.pens.filterPen import FilterPen


class CleanPen(FilterPen):
    """Round to integers and drop zero-length / collapsed segments."""
    cur = None

    def _r(self, p):
        return (int(round(p[0])), int(round(p[1])))

    def moveTo(self, pt):
        self.cur = self._r(pt); self._outPen.moveTo(self.cur)

    def lineTo(self, pt):
        p = self._r(pt)
        if p != self.cur:
            self._outPen.lineTo(p); self.cur = p

    def curveTo(self, *pts):
        ps = [self._r(p) for p in pts]
        if ps[-1] == self.cur:
            return
        if all(q == self.cur or q == ps[-1] for q in ps[:-1]):
            self._outPen.lineTo(ps[-1])
        else:
            self._outPen.curveTo(*ps)
        self.cur = ps[-1]

    def qCurveTo(self, *pts):
        ps = [self._r(p) if p is not None else None for p in pts]
        if self.cur is None:                # a closed contour of off-curve points only
            self._outPen.qCurveTo(*ps); return
        out, prev = [], self.cur
        for q in ps:                      # drop points that rounding made identical to their predecessor
            if q is not None and q == prev:
                continue
            out.append(q)
            if q is not None:
                prev = q
        if not out:
            return
        if len(out) == 1:
            if out[0] is not None:
                self._outPen.lineTo(out[0]); self.cur = out[0]
            return
        self._outPen.qCurveTo(*out)
        if out[-1] is not None:
            self.cur = out[-1]

    def closePath(self):
        self._outPen.closePath(); self.cur = None

    def endPath(self):
        self._outPen.endPath()


def _near_line(args, a, b, tol=1.5):
    """All points of a segment lie within tol units of the line through a and b."""
    a = np.array(a, float); b = np.array(b, float); d = b - a; L = np.linalg.norm(d)
    for p in args:
        if p is None:
            continue
        p = np.array(p, float)
        dist = np.linalg.norm(p - a) if L < 1e-9 else abs(d[0] * (p[1] - a[1]) - d[1] * (p[0] - a[0])) / L
        if dist > tol:
            return False
    return True


def despike(p):
    """Remove spikes left by rounding: a line that runs straight back over the previous line
    (A->B->A), and segments of zero length. Repeats until nothing changes."""
    rec = RecordingPen(); p.draw(rec)
    contours, cur = [], []
    for op, args in rec.value:
        if op == 'moveTo':
            cur = [('moveTo', args)]
        elif op in ('closePath', 'endPath'):
            contours.append(cur); cur = []
        else:
            cur.append((op, args))
    out = pathops.Path(); pen = out.getPen()
    for c in contours:
        start = c[0][1][0]
        segs = c[1:]
        changed = True
        while changed and len(segs) > 2:
            changed = False
            pts = [start] + [a[-1] for _, a in segs]
            for i in range(len(segs)):
                prev_end = pts[i]
                op, a = segs[i]
                if a[-1] == prev_end and (op == 'lineTo' or _near_line(a, prev_end, prev_end)):
                    del segs[i]; changed = True; break
                if i + 1 < len(segs) and segs[i + 1][1][-1] == prev_end:
                    # out and straight back again (the curve, if any, hugging the same line): a sliver
                    q = a[-1]
                    if _near_line(a, prev_end, q) and _near_line(segs[i + 1][1], q, prev_end):
                        del segs[i:i + 2]; changed = True; break
        if len(segs) < 2:
            continue
        pen.moveTo(start)
        for op, a in segs:
            getattr(pen, op)(*a)
        pen.closePath()
    return out


def final_clean(p):
    """Round to the integer grid, then let pathops remove the spurs and slivers that rounding exposes."""
    q = pathops.Path()
    p.draw(CleanPen(q.getPen()))
    q = pathops.simplify(q, fix_winding=True, keep_starting_points=False, clockwise=False)
    r = pathops.Path(); q.draw(CleanPen(r.getPen()))
    return despike(r)


class Font2:
    def __init__(self, key, style_name='Regular'):
        self.key = key; self.cfg = FONTS[key]; self.style = self.cfg['style']
        self.style_name = style_name; self.bold, self.italic = STYLES[style_name]
        G, self.s = GL.load(key)
        st = stats(key); s = self.s
        self.xh = st['xh'][0] * s; self.asc = st['asc'][0] * s
        self.cap = st['cap'][0] * s if st['cap'] else self.asc
        self.fig = st['fig'][0] * s
        self.P = {n: g['path'] for n, g in G.items()}
        self.traced = set(self.P)                 # names cut from the flyer itself
        self.hairlines()
        self.S_regular = self.stem_width()
        if self.bold:
            self.embolden_traced()
        self.made = {}
        self.repairs()
        self.snap()
        self.zones()
        self.S = self.stem_width()

    # Hairlines too faint for the scan: where Céilí's pen turned to its thinnest the toner barely
    # registered, so the trace pinched three strokes to a point and left the top of the e's eye open
    # (the scan shows grey there, not paper). Found by hairline.pinches() over every traced glyph of
    # all four faces; these are all it found.
    HAIRLINES = {'ceili': dict(h=5.0, pinch=('b', 'e', 'e.alt1'), bridge={'e': ((192, 506), (207, 513))})}

    def hairlines(self):
        import hairline
        self.touched = {}
        h = self.HAIRLINES.get(self.key)
        if not h:
            return
        for n, (a, b) in h['bridge'].items():
            self.P[n] = hairline.bridge(self.P[n], a, b, reach=12)
            self.touched[n] = 'the hairline closing the top of the eye, too faint for the scan, restored'
        for n in h['pinch']:
            self.P[n] = hairline.spine(self.P[n], h['h'])
            note = f'a hairline the scan pinched to nothing given back its {h["h"]:.0f}-unit minimum'
            self.touched[n] = self.touched[n] + '; ' + note if n in self.touched else note

    def stem_width(self):
        w = lambda n: stem_at(self.P[n], 0.4 * self.xh, 'left')
        return float(np.mean([w('l')[1] - w('l')[0], w('n')[1] - w('n')[0]]))

    # ------------------------------------------------------------------ the bold: a wider pen
    def embolden_traced(self):
        """Draw every traced letter with a wider pen before anything is derived from it, so the
        punctuation, accents and symbols built from the letters follow it."""
        b = BOLD[self.key]; self.kept_open = {}
        for n, p in list(self.P.items()):
            if n in ('ornament', 'DOTS'):
                # the sheet's loose accents and dots: each piece grown on its own, nothing moved, and
                # kept apart (some sit close enough on the sheet for a wider pen to join them); a
                # ring keeps its hole open as the letters' counters do
                pen = (b['rx'], b['ry'])
                self.P[n] = bolden.concat([bolden.protect(q, bolden.grow(q, *pen), self.S_regular, pen)
                                           for q in bolden.components(p)])
            else:
                bolden.LOG.clear()
                self.P[n] = bolden.embolden(p, b['rx'], b['ry'], b['k'], self.xh, self.S_regular,
                                            apertures=n not in b.get('joins', ()))
                if bolden.LOG:
                    self.kept_open[n] = list(bolden.LOG)

    # ------------------------------------------------------------------ the sloped styles
    def condense(self):
        """A little narrower than the upright, with the stems' weight put back, as a written
        italic is. Applied to every glyph before spacing."""
        rx = (1 - CONDENSE) * self.S / 2
        for n, p in list(self.P.items()):
            if bounds(p) is None:
                continue
            q = SH.transform(p, (CONDENSE, 0, 0, 1, 0, 0))
            self.P[n] = bolden.grow(q, rx, 0.5) if rx > 0.5 else q

    def slant(self):
        """Slope the finished glyphs about the middle of the x-height, so the space before and after a
        sloped word stays even. Spacing and kerning carry over unchanged: a shear moves both sides of
        every gap by the same amount at each height."""
        t = math.tan(math.radians(SLANT)); yc = self.xh / 2
        m = (1, 0, t, 1, -yc * t, 0)
        for n, p in list(self.final.items()):
            if bounds(p) is not None:
                self.final[n] = final_clean(SH.transform(p, m))
        sh = lambda x, y: int(round(x + (y - yc) * t))
        self.top_anchor = {n: (sh(x, y), y) for n, (x, y) in self.top_anchor.items()}
        self.bottom_anchor = {n: (sh(x, y), y) for n, (x, y) in self.bottom_anchor.items()}
        self.mark_anchor = {n: (w, sh(x, y), y) for n, (w, x, y) in self.mark_anchor.items()}

    # ------------------------------------------------------------------ letters damaged on the scan
    def repairs(self):
        """Rebuild letters whose print on the flyer is broken, from the same face's sound parts."""
        P = self.P
        if self.key == 'ceili':
            # The flyer's h printed starved in its right leg: 65-85 units wide against about 100 for
            # every other leg, eroded on both sides. Its stem and shoulder are sound (and the shoulder
            # is wider than n's), so keep them and replace only the leg with n's, set on the leg's
            # best-preserved outer edge (toner loss only ever moves an edge inward).
            h, n, xh = P['h'], P['n'], self.xh
            ys = np.linspace(0.08 * xh, 0.72 * xh, 17)
            outer = lambda p, y: stem_at(p, y, 'right')[1]
            target = float(np.percentile([outer(h, y) for y in ys], 80))
            dx = target - float(np.median([outer(n, y) for y in ys]))
            n0, _ = stem_at(n, 0.45 * xh, 'right')
            leg = translate(clip(n, x0=n0 - 0.15 * (target - dx - n0)), dx, 0)
            # join where the shoulder's edges and the moved leg's edges agree best
            def mismatch(y):
                (a0, a1), (b0, b1) = stem_at(h, y, 'right'), stem_at(leg, y, 'right')
                return abs(a0 - b0) + abs(a1 - b1)
            yj = min(np.linspace(0.70 * xh, 0.90 * xh, 21), key=mismatch)
            s0, s1 = stem_at(h, 0.45 * xh, 'left')
            stem = clip(h, x1=s1 + 0.25 * (s1 - s0))
            shoulder = clip(h, x0=s1, y0=yj - 0.02 * xh)
            P['h'] = SH.union(stem, shoulder, clip(leg, y1=yj + 0.02 * xh))
            self.made['h'] = ('stem and shoulder from the scan; the right leg, which printed broken, '
                              'from n, aligned to the flyer leg\'s outer edge')

    # ------------------------------------------------------------------ the sheet's accent sets
    # Kilfane and Carrick are shown with Letraset's set of loose accents and punctuation (what
    # earlier versions kept as an "ornament"). Each piece is found by where it sits in the set
    # (centre in font units, relative to the set's own left edge and the line's baseline).
    PIECES = {
        'kilfane': {'emdash': (347, 631), 'endash': (230, 500), 'acute': (683, 528), 'tilde': (1117, 619),
                    'dieresis.l': (814, 431), 'dieresis.r': (958, 437), 'dot': (1243, 441), 'ring': (84, 304),
                    'ring.b': (94, 82), 'circumflex': (1138, 291), 'caron': (1139, 59),
                    'guil.r1': (333, 136), 'guil.r2': (483, 148), 'guil.l1': (708, 151), 'guil.l2': (841, 158)},
        'carrick': {'emdash': (440, 579), 'endash': (312, 460), 'acute': (1278, 438), 'tilde': (1273, 131),
                    'dot': (1138, 526), 'dieresis.l': (800, 120), 'ringdot': (926, 208), 'ring': (1367, 313),
                    'circumflex': (921, 439), 'guil.r1': (95, 194)},
    }

    def specimen_pieces(self):
        """Split the sheet's accent set into named marks and rules (holes stay with their rings)."""
        self.piece = {}
        if self.key not in self.PIECES or 'ornament' not in self.P:
            return
        cs = contours(self.P.pop('ornament'))
        from fontTools.pens.areaPen import AreaPen
        def area(c):
            ap = AreaPen(); c.draw(ap); return ap.value
        outer = [c for c in cs if area(c) > 0]; holes = [c for c in cs if area(c) < 0]
        centre = lambda c: ((bounds(c)[0] + bounds(c)[2]) / 2, (bounds(c)[1] + bounds(c)[3]) / 2)
        for name, (x, y) in self.PIECES[self.key].items():
            c = min(outer, key=lambda c: math.hypot(centre(c)[0] - x, centre(c)[1] - y))
            assert math.hypot(centre(c)[0] - x, centre(c)[1] - y) < 40, (self.key, name)
            inside = [h for h in holes if bounds(c)[0] <= centre(h)[0] <= bounds(c)[2] and bounds(c)[1] <= centre(h)[1] <= bounds(c)[3]]
            self.piece[name] = SH.difference(c, SH.union(*inside)) if inside else c
        pc = self.piece
        if self.key == 'carrick':
            # ink spread joined the second diaeresis dot to the ring above it: repeat the clean
            # first dot at the pair's spacing on the sheet instead
            rd = pc.pop('ringdot'); lo = bounds(pc['dieresis.l'])
            cut = bounds(clip(rd, y1=lo[3] + 0.02 * self.xh))
            pitch = (cut[0] + cut[2]) / 2 - (lo[0] + lo[2]) / 2
            pc['dieresis.r'] = translate(pc['dieresis.l'], pitch, 0)
            # the other chevrons printed fused into each other; Letraset's pairs repeat one chevron
            r1 = pc['guil.r1']; w = bounds(r1)[2] - bounds(r1)[0]
            pc['guil.r2'] = translate(r1, 0.88 * w, 0)
        if self.bold:
            # the wider pen took its own width out of the gap between the pairs: give it back
            rx = BOLD[self.key]['rx']
            for a, b in (('dieresis.l', 'dieresis.r'), ('guil.r1', 'guil.r2'), ('guil.l1', 'guil.l2')):
                if a in pc and b in pc:
                    pc[a] = translate(pc[a], -rx, 0); pc[b] = translate(pc[b], rx, 0)
        self.made['accents'] = 'from the accent set on the sheet: ' + ', '.join(sorted(n for n in pc if '.' not in n))

    def norm_x(self, p):
        b = bounds(p); return translate(p, -b[0], 0)

    # ------------------------------------------------------------------ vertical regularisation
    def flat(self, p, y, band, top=True):
        y0, y1 = (y - band, y) if top else (y, y + band)
        ys, L, R = profiles(p, y0, y1, step=2)
        if np.all(np.isnan(L)):
            return False
        b = bounds(p)
        return np.nanmax(R - L) >= 0.3 * (b[2] - b[0])

    def snap(self):
        tol = 1.2 * self.s
        for n, p in list(self.P.items()):
            if n in ('DOTS', 'semicolon', 'ornament', 'parenleft', 'parenright', 'hyphen'):
                continue
            x0, y0, x1, y1 = bounds(p)
            if abs(y0) > tol:
                continue
            over = 0 if self.flat(p, y0, 0.015 * self.xh, top=False) else 8
            self.P[n] = translate(p, 0, -y0 - over)

    def zones(self):
        """Pull x-height / ascender / cap / figure tops onto common lines (with overshoot for round tops)."""
        P, xh = self.P, self.xh
        unic = self.cfg['unicase']
        classes = {'xh': 'a c e m n o r s u v w x z'.split() + [a for b in 'acenrsv' for a in self.cfg['alts'].get(b, [])],
                   'asc': 'b d h k l'.split() + [a for b in 'dl' for a in self.cfg['alts'].get(b, [])]}
        if not unic:
            classes['cap'] = [c for c in 'ABCDEFGHIJKLMNOPRSTUVWXYZ'] + ['A.alt1', 'A.alt2', 'D.alt1', 'S.alt1', 'T.alt1', 'Y.alt1']
        if self.cfg['lining']:
            classes['fig'] = DIGITS
        self.zone_report = {}
        for cname, names in classes.items():
            names = [n for n in names if n in P]
            tops = {n: bounds(P[n])[3] for n in names}
            flat = {n: self.flat(P[n], tops[n], 0.015 * xh) for n in names}
            # each top type converges on its own median; only small (noise-sized) deviations are corrected
            groups = {True: [n for n in names if flat[n]], False: [n for n in names if not flat[n]]}
            targets = {}
            for typ, members in groups.items():
                if len(members) >= 3:
                    targets[typ] = float(np.median([tops[n] for n in members]))
            moved = 0
            for n in names:
                if flat[n] not in targets:
                    continue
                target = targets[flat[n]]; top = tops[n]
                if 0.5 < abs(top - target) <= 0.02 * xh and top > 0:
                    k = target / top
                    P[n] = remap(P[n], lambda x, y, k=k: (x, y * k if y > 0 else y)); moved += 1
            line = float(np.median(list(tops.values())))
            over = round(targets[False] - targets[True]) if len(targets) == 2 else 0
            self.zone_report[cname] = (round(line), over, moved, len(names))
            if cname == 'xh':
                self.xh = line
            elif cname == 'asc':
                self.asc = line
            elif cname == 'cap':
                self.cap = line
            elif cname == 'fig':
                self.fig = line

    # ------------------------------------------------------------------ punctuation from the specimen
    def punctuation(self):
        P, xh, S = self.P, self.xh, self.S
        qtop = self.cap if not self.cfg['unicase'] else self.asc
        source_parts = getattr(self, 'source_punctuation', None)
        if source_parts is not None:
            dot, comma = source_parts['period'], source_parts['comma']
            ql, qr = source_parts['quoteleft'], source_parts['quoteright']
            P.pop('DOTS', None)
        elif self.key in ('kilfane', 'carrick'):
            # the sheet's semicolon gives the comma and the dot; its own pair is drawn compact and set
            # high between the parentheses, but here the dot aligns with the colon's like any text face
            comma, dot = sorted(contours(P.pop('semicolon')), key=lambda c: bounds(c)[1])
        elif self.key == 'ceili':
            cs = contours(P.pop('DOTS'))
            near = lambda x, y: min(cs, key=lambda c: abs(bounds(c)[0] - x) + abs(bounds(c)[1] - y))
            dot = near(195, 17); qr = near(174, 483); ql = near(9, 463)
            d0, e0, d1, e1 = bounds(dot); r = (d1 - d0) / 2; cx = (d0 + d1) / 2
            comma = SH.union(dot, SH.wedge((cx + 0.25 * r, e0 + 0.55 * r), (cx - 0.55 * r, e0 - 1.55 * r), 0.55 * r, 0.16 * r))
        else:
            dot = sorted(contours(P['exclam']), key=lambda c: bounds(c)[1])[0]
            dx0, dy0, dx1, dy1 = bounds(dot); w = dx1 - dx0; h = dy1 - dy0
            tail = SH.polygon([(dx0 + 0.45 * w, dy0 + 2), (dx1, dy0 + 2), (dx1 - 0.08 * w, dy0 - 0.75 * h),
                               (dx0 + 0.05 * w, dy0 - 1.15 * h), (dx0 + 0.42 * w, dy0 - 0.35 * h)])
            comma = SH.union(dot, tail)
        dot = self.norm_x(dot)
        period = translate(dot, 0, -bounds(dot)[1]); ph = bounds(period)[3]
        comma = self.norm_x(comma); comma = translate(comma, 0, ph - bounds(comma)[3])
        P['period'] = period; P['comma'] = comma; self.period = period
        if self.key == 'ceili':
            qr = self.norm_x(qr); ql = self.norm_x(ql)
            P['quoteright'] = translate(qr, 0, qtop - bounds(qr)[3]); P['quoteleft'] = translate(ql, 0, qtop - bounds(ql)[3])
        else:
            qr = translate(comma, 0, qtop - bounds(comma)[3]); P['quoteright'] = qr
            b = bounds(qr); ql = SH.rotate(qr, 180, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            P['quoteleft'] = translate(self.norm_x(ql), 0, qtop - bounds(ql)[3])
        for single, double in (('quoteleft', 'quotedblleft'), ('quoteright', 'quotedblright')):
            q = P[single]; w = bounds(q)[2]
            P[double] = SH.union(q, translate(q, w + 0.45 * w, 0))
        hw = (bounds(period)[2] - bounds(period)[0]) / 2
        qs = SH.wedge((0, qtop - hw * 0.8), (0, qtop - 0.36 * xh), hw * 0.8, hw * 0.35, rounded=(self.style == 'round'))
        qs = self.norm_x(qs); P['quotesingle'] = translate(qs, 0, qtop - bounds(qs)[3])
        w = bounds(P['quotesingle'])[2]
        P['quotedbl'] = SH.union(P['quotesingle'], translate(P['quotesingle'], w * 1.6, 0))
        top_dot = translate(period, 0, xh - ph)
        P['colon'] = SH.union(period, top_dot)
        cw = bounds(comma)[2]; pw = bounds(period)[2]
        P['semicolon'] = SH.union(comma, translate(top_dot, (cw - pw) / 2 if self.key != 'ceili' else 0, 0))
        P['ellipsis'] = SH.union(period, translate(period, pw * 1.7, 0), translate(period, pw * 3.4, 0))
        dot_src = {'kilfane': 'the dot of the flyer’s semicolon', 'carrick': 'the dot of the flyer’s semicolon',
                   'ceili': 'a dot from the flyer’s punctuation', 'tuam': 'the dot of the flyer’s exclamation mark'}[self.key]
        comma_src = {'kilfane': 'the comma of the flyer’s semicolon', 'carrick': 'the comma of the flyer’s semicolon',
                     'ceili': 'the flyer’s dot with a drawn tail', 'tuam': 'the flyer’s dot with a drawn tail'}[self.key]
        self.made.update(period=dot_src, comma=comma_src, colon=f'two of {dot_src.replace("the dot", "the dots").replace("a dot", "the dots")}',
                         semicolon=f'{comma_src}, with the colon’s upper dot', ellipsis='three periods',
                         quoteright='the flyer’s quote' if self.key == 'ceili' else 'the comma, raised',
                         quoteleft='the flyer’s quote' if self.key == 'ceili' else 'the comma, raised and turned',
                         quotedblleft='two quotes', quotedblright='two quotes', quotesingle='wedge drawn to match',
                         quotedbl='two wedges')

    def dashes(self):
        P, xh, S = self.P, self.xh, self.S
        st = self.style
        if 'endash' in self.piece:
            # The sheet's two rules give the dash weight. They are only about 2.5 px thick on the scan,
            # so their ends are blur: the dashes are drawn as clean rules with the face's own terminals.
            from fontTools.pens.areaPen import AreaPen
            def weight(p):
                ap = AreaPen(); p.draw(ap); b = bounds(p); return abs(ap.value) / (b[2] - b[0])
            thick = float(np.mean([weight(self.piece['endash']), weight(self.piece['emdash'])])); yc = 0.47 * xh
            def bar(L):
                if st == 'round':
                    return SH.capsule(thick / 2, L - thick / 2, yc, thick)
                return SH.slanted_bar(0, L, yc, thick, cut=0.22 * thick)
            self.rule = bar
            P['hyphen'] = self.norm_x(bar(0.5 * xh)); P['endash'] = self.norm_x(bar(470)); P['emdash'] = self.norm_x(bar(930))
            how = 'drawn at the weight of the rules in the sheet’s accent set'
            self.made.update(hyphen=how, endash=how, emdash=how)
            self.hyphen_thick = thick; self.hyphen_yc = yc
            return
        if 'hyphen' in P and self.key == 'ceili':
            h = bounds(P['hyphen']); P['hyphen'] = self.norm_x(P['hyphen'])
            thick = h[3] - h[1]; yc = (h[1] + h[3]) / 2
            hy = P['hyphen']
            bar = lambda L: resize_bar(hy, L)          # longer dashes keep the hyphen's pen-cut ends
        else:
            thick = {'round': 0.72, 'square': 0.50, 'chisel': 0.62}[st] * S; yc = 0.47 * xh
            def bar(L):
                if st == 'round':
                    return SH.capsule(thick / 2, L - thick / 2, yc, thick)
                if st == 'square':
                    return SH.polygon([(0, yc - thick / 2), (L, yc - thick / 2), (L, yc + thick / 2), (0, yc + thick / 2)])
                return SH.slanted_bar(0, L, yc, thick, cut=0.22 * thick)
            P['hyphen'] = self.norm_x(bar(0.5 * xh))
        P['endash'] = self.norm_x(bar(470)); P['emdash'] = self.norm_x(bar(930))
        if self.key == 'ceili':
            self.made.update(endash='the flyer’s hyphen, lengthened', emdash='the flyer’s hyphen, lengthened')
        else:
            self.made.update(hyphen='drawn to match', endash='drawn to match', emdash='drawn to match')
        self.hyphen_thick = thick; self.hyphen_yc = yc

    def parens_slash_misc(self):
        P, xh, S = self.P, self.xh, self.S
        top = self.asc + 0.02 * xh; bot = -0.33 * xh
        if 'parenleft' not in P:
            self.made.update(parenleft='drawn to match', parenright='drawn to match')
            P['parenleft'] = self.norm_x(SH.paren_arc(bot, top, depth=0.20 * xh, thick=0.72 * S))
            b = bounds(P['parenleft'])
            P['parenright'] = self.norm_x(SH.transform(P['parenleft'], (-1, 0, 0, 1, b[2], 0)))
        else:
            for n in ('parenleft', 'parenright'):
                P[n] = self.norm_x(P[n])
        t = 0.55 * S if self.style != 'square' else 0.50 * S
        dx = 0.42 * (top - bot)
        if self.style == 'round':
            sl = SH.wedge((0, bot + t / 2), (dx, top - t / 2), t / 2, t / 2)
        else:
            sl = SH.polygon([(0, bot), (t * 1.15, bot), (dx + t * 1.15, top), (dx, top)])
        P['slash'] = self.norm_x(sl)
        sv = P['seven']; P['uni204A'] = translate(sv, 0, xh - bounds(sv)[3])
        self.made.update(slash='drawn to match', uni204A='the flyer’s 7 at x-height, as in Gaelic type')
        src = P['C'] if not self.cfg['unicase'] else P['c']
        b = bounds(src); target = self.fig if self.cfg['lining'] else xh * 1.12
        k = target / (b[3] - b[1])
        c = SH.transform(src, (k, 0, 0, k, 0, 0)); cb = bounds(c); c = translate(c, -cb[0] + 0.12 * (cb[2] - cb[0]), -cb[1])
        cb = bounds(c); w = cb[2] - cb[0]; bh = 0.55 * self.hyphen_thick
        bars = [SH.polygon([(0, y - bh / 2), (cb[0] + 0.62 * w, y - bh / 2), (cb[0] + 0.62 * w, y + bh / 2), (0, y + bh / 2)])
                for y in (0.40 * target, 0.60 * target)]
        P['Euro'] = self.norm_x(SH.union(c, *bars)); self.made['Euro'] = 'the flyer’s ' + ('C' if not self.cfg['unicase'] else 'c') + ' with two bars'

    def dotless(self):
        P, xh = self.P, self.xh
        for src, dst in (('i', 'dotlessi'), ('j', 'dotlessj')):
            body = [c for c in contours(P[src]) if bounds(c)[1] < 0.6 * xh]
            P[dst] = SH.union(*body); self.made[dst] = f'the flyer’s {src} without its dot'

    # ------------------------------------------------------------------ marks & composites
    def make_marks(self):
        P = self.P
        acute = max(contours(P['uacute']), key=lambda c: bounds(c)[3]) if self.key == 'tuam' else None
        pc = self.piece
        given = {k: pc[k] for k in ('acute', 'tilde', 'dot', 'ring', 'circumflex', 'caron') if k in pc}
        if 'dieresis.l' in pc:
            given['dieresis'] = SH.union(pc['dieresis.l'], pc['dieresis.r'])
        if 'endash' in pc:
            given['macron'] = self.rule(0.44 * self.xh)
        self.mark_source = {k: 'sheet' for k in given}
        if acute is not None:
            self.mark_source['acute'] = 'flyer'
        ms = MarkSet(self.style, self.S, self.xh, acute=acute, period=self.period, comma=P['comma'],
                     weight=self.cfg['mark_weight'], given=given)
        self.marks = ms.all()
        self.marks['caronvert'] = ms.caronvert(P['quoteright'])
        # flatter accents for capitals
        self.case_marks = {k: (SH.transform(v, (1, 0, 0, 0.82, 0, 0)) if k not in BOTTOM else v) for k, v in self.marks.items()}
        for n in ('aacute', 'eacute', 'iacute', 'oacute', 'uacute'):
            P.pop(n, None)
        self.gap = self.cfg['gap'] * self.xh

    def attach(self, base_name, base, mark_kind, upper, stack_top=None):
        """Return (positioned mark path, anchor) for mark_kind on base."""
        xh, asc, cap = self.xh, self.asc, self.cap
        m = (self.case_marks if upper else self.marks)[mark_kind]
        a0, b0, a1, b1 = bounds(m); aw = a1 - a0; acx = (a0 + a1) / 2
        x0, y0, x1, y1 = bounds(base)
        if mark_kind == 'caronvert':
            mh = b1 - b0
            topy = (cap if upper else (asc if base_name[0] != 't' else y1 + 0.12 * xh))
            ys, L, R = profiles(base, topy - mh, topy + 4, step=4)
            right = np.nanmax(R) if not np.all(np.isnan(R)) else x1
            return translate(m, right + 0.07 * xh - a0, topy - b1)
        if mark_kind in BOTTOM:
            lo, hi = ink_x_extent(base, -0.02 * xh, 0.18 * xh)
            if mark_kind == 'ogonek':
                cx = hi - 0.35 * self.S
                ty = bounds(m)[3]
                # ogonek's neck is its highest point
                ys, L, R = profiles(m, ty - 0.03 * xh, ty, step=2)
                neck = (np.nanmin(L) + np.nanmax(R)) / 2
                return translate(m, cx - neck, bottom_under(base, cx - 10, cx + 10) + 0.04 * xh - b1)
            cx = (lo + hi) / 2
            if base_name.lower()[0] in 'klnr' and mark_kind == 'commabelow':
                s0, s1 = stem_at(base, 0.2 * xh, 'left'); cx = (s0 + s1) / 2 if base_name[0] in 'kl' else cx
            if mark_kind == 'cedilla':
                ty = bounds(m)[3]; ys, L, R = profiles(m, ty - 0.03 * xh, ty, step=2)
                neck = (np.nanmin(L) + np.nanmax(R)) / 2
                return translate(m, cx - neck, bottom_under(base, cx - 10, cx + 10) + 0.05 * xh - b1)
            return translate(m, cx - acx, -0.06 * xh - b1)
        # top marks
        top_ref = cap if upper else xh
        if not upper and base_name[0] in 'bdhkl' and base_name not in ('dotlessi',):
            s0, s1 = stem_at(base, xh + 0.6 * (asc - xh), 'left'); cx = (s0 + s1) / 2
        else:
            lo, hi = ink_x_extent(base, 0.72 * top_ref, 1.02 * top_ref); cx = (lo + hi) / 2
        t = top_under(base, cx - aw / 2, cx + aw / 2) if stack_top is None else stack_top
        gap = self.gap * (0.85 if upper else 1.0)
        if mark_kind == 'commaturned':
            gap *= 1.4
        return translate(m, cx - acx, t + gap - b0)

    def composites(self):
        P, cfg = self.P, self.cfg
        self.comp = {}            # composite -> base glyph (for metrics/kerning)
        self.comp_marks = {}      # composite -> the marks put on it
        self.widen = set()        # composites whose mark may extend past the base's advance
        self.cmap = {}
        alts = cfg['alts']
        for cp in COMPOSED:
            dec = decompose(cp)
            if dec is None:
                continue
            letter, kinds = dec
            ch = chr(cp)
            if kinds == ['caronvert'] and letter == 't' and bounds(P['t'])[3] < self.xh * 1.15:
                kinds = ['caron']
            upper = ch.isupper()
            if cfg['unicase']:
                if upper:
                    continue
                letter = letter.lower()
            base = letter
            if base in ('i', 'j') and any(k not in BOTTOM for k in kinds):
                base = 'dotlessi' if base == 'i' else 'dotlessj'
            if base not in P:
                continue
            name = gname(cp)
            for bn in [base] + alts.get(base, []):
                path = P[bn]; acc_top = None; out = path
                kk = kinds
                if cp == 0x165 and bounds(path)[3] >= self.xh * 1.15:
                    kk = ['caronvert']
                for k in kk:
                    mk = self.attach(bn, out if k not in BOTTOM else path, k, upper, acc_top if k not in BOTTOM else None)
                    if k not in BOTTOM:
                        acc_top = bounds(mk)[3]
                    out = SH.union(out, mk)
                gn = name + bn[len(base):] if bn != base else name
                P[gn] = out; self.comp[gn] = bn; self.comp_marks[gn] = list(kk)
                if 'caronvert' in kk:
                    self.widen.add(gn)
            self.cmap[cp] = name

    def combining_and_spacing_marks(self):
        P = self.P; xh = self.xh
        ow = bounds(P['o'])[2]
        self.mark_glyphs = {}
        for cp, kind in COMB.items():
            m = self.marks[kind]; b = bounds(m)
            if kind in BOTTOM:
                pos = translate(m, -ow / 2 - (b[0] + b[2]) / 2, -b[3] - (0.06 * xh if kind == 'commabelow' else -0.04 * xh))
            else:
                pos = translate(m, -ow / 2 - (b[0] + b[2]) / 2, xh + self.gap - b[1])
            name = gname(cp); P[name] = pos; self.mark_glyphs[name] = kind; self.cmap[cp] = name
        for cp, kind in SPACING_MARKS.items():
            m = self.marks[kind]; b = bounds(m)
            if kind in BOTTOM:
                q = translate(m, -b[0], -b[3] + (0.04 * xh if kind != 'commabelow' else -0.06 * xh))
            else:
                q = translate(m, -b[0], xh + self.gap - b[1])
            name = gname(cp); P[name] = q; self.cmap[cp] = name; self.made[name] = 'spacing ' + self.mark_words(kind)

    # ------------------------------------------------------------------ cmap
    def build_cmap(self):
        P, cfg = self.P, self.cfg
        cm = dict(self.cmap)
        for c in range(0x41, 0x5B):
            lo = chr(c).lower()
            if cfg['unicase']:
                cm[c] = {'I': 'dotlessi', 'J': 'dotlessj'}.get(chr(c), lo)
            else:
                cm[c] = chr(c)
            cm[ord(lo)] = lo
        for cp, g in OTHER.items():
            if g in P or g == 'space':
                cm[cp] = g
        if cfg['unicase']:
            pairs = {0xC6: 'ae', 0xD8: 'oslash', 0xD0: 'eth', 0xDE: 'thorn', 0x110: 'dcroat', 0x126: 'hbar',
                     0x132: 'ij', 0x13F: 'ldot', 0x141: 'lslash', 0x14A: 'eng', 0x152: 'oe', 0x166: 'tbar'}
            cm.update(pairs)
            for cp in COMPOSED:
                ch = chr(cp)
                if ch.isupper() and len(ch.lower()) == 1:
                    lo = ord(ch.lower())
                    if lo in cm:
                        cm[cp] = cm[lo]
            cm[0x130] = 'i'           # İ
        for cp, g in cfg['insular'].items():
            cm[cp] = g
        self.cm = {cp: g for cp, g in cm.items() if g in P or g == 'space'}

    # ------------------------------------------------------------------ spacing
    def zone(self, n):
        base = self.comp.get(n, n)
        if not self.cfg['unicase'] and (base[:1].isupper() and len(base.split('.')[0]) <= 2 or base in
                                        ('AE', 'OE', 'Oslash', 'Eth', 'Dcroat', 'Hbar', 'Lslash', 'Tbar', 'Eng', 'Thorn', 'IJ', 'Ldot')):
            return (0, self.cap)
        if self.cfg['lining'] and (base in DIGITS or base in ('Euro', 'numbersign', 'percent', 'perthousand', 'sterling',
                                                               'dollar', 'yen', 'cent', 'section', 'paragraph', 'dagger', 'daggerdbl')):
            return (0, self.fig)
        return (0, self.xh)

    def space(self, K):
        P = self.P; self.adv = {}; self.lsb = {}
        dmax = 0.2 * self.xh; minsb = 0.12 * K
        fixed = {'hyphen': 0.75, 'endash': 0.45, 'emdash': 0.25, 'period': 0.8, 'comma': 0.8, 'colon': 0.8,
                 'semicolon': 0.8, 'ellipsis': 0.8, 'uniE000': 0.6, 'quoteleft': 0.7, 'quoteright': 0.7,
                 'quotedblleft': 0.7, 'quotedblright': 0.7, 'quotesingle': 0.7, 'quotedbl': 0.7,
                 'quotesinglbase': 0.7, 'quotedblbase': 0.7, 'plus': 0.9, 'minus': 0.9, 'equal': 0.9, 'multiply': 0.9,
                 'divide': 0.9, 'plusminus': 0.9, 'less': 0.9, 'greater': 0.9, 'lessequal': 0.9, 'greaterequal': 0.9,
                 'notequal': 0.9, 'approxequal': 0.9, 'logicalnot': 0.9, 'underscore': 0.0, 'bar': 1.0,
                 'brokenbar': 1.0, 'periodcentered': 0.8, 'bullet': 0.9, 'degree': 0.6, 'minute': 0.6, 'second': 0.6,
                 'guilsinglleft': 0.5, 'guilsinglright': 0.5, 'guillemotleft': 0.5, 'guillemotright': 0.5,
                 'asciicircum': 0.6, 'asciitilde': 0.8, 'fraction': -0.6}
        for cp, kind in SPACING_MARKS.items():
            fixed[gname(cp)] = 0.45
        for n, p in P.items():
            if n in self.comp or n in self.mark_glyphs:
                continue
            b = bounds(p)
            if n in fixed:
                sb = fixed[n] * K
                self.lsb[n] = sb; self.adv[n] = int(round(sb + (b[2] - b[0]) + sb))
                continue
            info = side_depths(p, self.zone(n), dmax)
            l, r = sidebearings(info, K, minsb)
            self.lsb[n] = l; self.adv[n] = int(round(l + (b[2] - b[0]) + r))
        for n, bn in self.comp.items():
            self.lsb[n] = self.lsb[bn] + (bounds(P[n])[0] - bounds(P[bn])[0]); self.adv[n] = self.adv[bn]
            if n in self.widen:
                shift = self.lsb[bn] - bounds(P[bn])[0]
                self.adv[n] = max(self.adv[bn], int(round(bounds(P[n])[2] + shift + 0.35 * K)))
        for n in self.mark_glyphs:
            self.lsb[n] = None; self.adv[n] = 0
        math_names = [m for m in ('plus', 'minus', 'equal', 'multiply', 'divide', 'plusminus', 'less', 'greater',
                                  'lessequal', 'greaterequal', 'notequal', 'approxequal', 'logicalnot') if m in self.adv]
        mw = max(self.adv[m] for m in math_names)
        for m in math_names:
            w = bounds(P[m])[2] - bounds(P[m])[0]
            self.lsb[m] = (mw - w) / 2; self.adv[m] = mw
        self.adv['space'] = int(round(min(max(0.5 * self.adv['n'], 220), 320)))
        self.final = {'space': pathops.Path()}
        for n, p in P.items():
            if n in self.mark_glyphs:
                self.final[n] = p; continue
            b = bounds(p); self.final[n] = final_clean(translate(p, self.lsb[n] - b[0], 0))

    # ------------------------------------------------------------------ kerning (class based, with exceptions)
    def kerning(self):
        xh = self.xh
        letters = [n for n in self.final if n not in self.comp and n not in self.mark_glyphs and
                   (len(n.split('.')[0]) == 1 and n[0].isalpha() or n in ('dotlessi', 'dotlessj', 'ae', 'oe', 'AE', 'OE',
                    'oslash', 'Oslash', 'eth', 'Eth', 'thorn', 'Thorn', 'germandbls', 'eng', 'Eng', 'lslash', 'Lslash'))]
        punct = ['period', 'comma', 'quoteright', 'quoteleft', 'quotedblright', 'quotedblleft', 'hyphen', 'colon', 'semicolon']
        names = letters + [p for p in punct if p in self.final] + ['seven', 'one']
        lo_y, hi_y = -0.4 * xh, self.cap + 0.35 * xh
        win = max(1, int(round(0.10 * xh / 8)))

        def roll_min(a):
            pad = np.pad(a, win, constant_values=np.nan)
            st = np.lib.stride_tricks.sliding_window_view(pad, 2 * win + 1)
            with np.errstate(all='ignore'):
                return np.nanmin(st, axis=1)
        ext = {}
        def prof(n):
            if n not in ext:
                yy, L, R = profiles(self.final[n], lo_y, hi_y, step=8)
                ext[n] = (roll_min(L), R)
            return ext[n]
        nl, nr = prof('n')
        neutral = np.nanmin(nl + self.adv['n'] - nr)
        quotes = {'quoteright', 'quoteleft', 'quotedblright', 'quotedblleft'}
        figs = set(DIGITS) - {'seven'}
        pk = {}
        for a in names:
            for b in names:
                if (a in figs or b in figs) or (a in quotes and b in quotes):
                    continue
                if a in ('period', 'comma', 'colon', 'semicolon') and b in ('period', 'comma', 'colon', 'semicolon'):
                    continue
                gap = self.adv[a] + prof(b)[0] - prof(a)[1]
                if np.all(np.isnan(gap)):
                    continue
                dmin = np.nanmin(gap)
                if dmin > 1.6 * neutral:
                    k = max(-0.5 * (dmin - 1.25 * neutral), -150)
                    k = int(round(k / 5.0) * 5)
                    if k <= -15:
                        pk[(a, b)] = k
        # groups: a composite joins its base's group on a side if it doesn't stick out on that side
        left_group, right_group = {}, {}
        for n in names:
            left_group[n] = [n]; right_group[n] = [n]
        for c, bn in self.comp.items():
            if bn not in left_group:
                continue
            cb, bb = bounds(self.final[c]), bounds(self.final[bn])
            if cb[2] <= bb[2] + 0.03 * xh:
                left_group[bn].append(c)
            if cb[0] >= bb[0] - 0.03 * xh:
                right_group[bn].append(c)
        # exceptions: kerning that would make an accent collide
        exc = {}
        for (a, b), k in pk.items():
            for ga in left_group[a]:
                for gb in right_group[b]:
                    if ga == a and gb == b:
                        continue
                    if ga not in self.comp and gb not in self.comp:
                        continue
                    gap = self.adv[ga] + k + prof(gb)[0] - prof(ga)[1]
                    if np.all(np.isnan(gap)):
                        continue
                    dmin = np.nanmin(gap)
                    if dmin < 0.6 * neutral:
                        k2 = int(round(min(0, k + (0.6 * neutral - dmin)) / 5) * 5)
                        exc[(ga, gb)] = k2
        self.kern_pairs, self.kern_exc = pk, exc
        self.left_group, self.right_group = left_group, right_group
        self.neutral = neutral

    # ------------------------------------------------------------------ mark anchors
    def anchors(self):
        """Top/bottom anchors on every letter base for combining marks."""
        xh = self.xh; ow = bounds(self.P['o'])[2]
        self.top_anchor, self.bottom_anchor = {}, {}
        bases = [n for n in self.final if n not in self.mark_glyphs and n not in self.comp and
                 (len(n.split('.')[0]) == 1 and n[0].isalpha() or n in ('dotlessi', 'dotlessj', 'ae', 'oe', 'oslash', 'AE', 'OE'))]
        for n in bases:
            p = self.final[n]; upper = n[0].isupper() and not self.cfg['unicase']
            m = self.attach(n, p, 'acute', False)       # marks are lowercase-sized in the mark feature
            mb = bounds(m); src = bounds(self.marks['acute'])
            self.top_anchor[n] = (int(round((mb[0] + mb[2]) / 2)), int(round(mb[1])))
            lo, hi = ink_x_extent(p, -0.02 * xh, 0.18 * xh)
            self.bottom_anchor[n] = (int(round((lo + hi) / 2)), 0)
        self.mark_anchor = {}
        for name, kind in self.mark_glyphs.items():
            b = bounds(self.final[name])
            if kind in BOTTOM:
                self.mark_anchor[name] = ('bottom', int(round((b[0] + b[2]) / 2)), 0)
            else:
                self.mark_anchor[name] = ('top', int(round((b[0] + b[2]) / 2)), int(round(b[1])))

    # ------------------------------------------------------------------ features
    def variants(self, b, alt):
        out = [(b, alt)]; suffix = alt[len(b):]
        for n, bn in self.comp.items():
            if bn == b and n + suffix in self.final:
                out.append((n, n + suffix))
        return out

    def features(self):
        cfg = self.cfg
        fea = ['languagesystem DFLT dflt;', 'languagesystem latn dflt;', '']
        tops = [n for n, k in self.mark_glyphs.items() if k not in BOTTOM]
        bots = [n for n, k in self.mark_glyphs.items() if k in BOTTOM]
        fea += [f'@CombTop = [{" ".join(sorted(tops))}];', f'@CombBottom = [{" ".join(sorted(bots))}];', '']
        fea += ['lookup DOTLESS { sub i by dotlessi; sub j by dotlessj; } DOTLESS;', '',
                'feature ccmp {', "    sub [i j]' lookup DOTLESS @CombTop;", '} ccmp;', '']
        salt = {}
        for b, al in cfg['alts'].items():
            for alt in al:
                for d, a in self.variants(b, alt):
                    salt.setdefault(d, []).append(a)
        if salt:
            fea += ['feature aalt { feature salt; } aalt;', '', 'feature salt {']
            fea += [f'    sub {d} from [{" ".join(al)}];' for d, al in sorted(salt.items())] + ['} salt;', '']
        for tag, label, mapping in cfg.get('sets', []):
            fea += [f'feature {tag} {{', f'    featureNames {{ name "{label}"; }};']
            for b, alt in mapping.items():
                fea += [f'    sub {d} by {a};' for d, a in self.variants(b, alt)]
            fea += [f'}} {tag};', '']
        # kerning: exceptions first (format 1), then classes (format 2)
        fea += ['feature kern {', '    lookup KERN {']
        for (a, b), k in sorted(self.kern_exc.items()):
            fea.append(f'        pos {a} {b} {k};')
        cls_l, cls_r = {}, {}
        for (a, b), k in sorted(self.kern_pairs.items()):
            cls_l[a] = self.left_group[a]; cls_r[b] = self.right_group[b]
        for a, g in cls_l.items():
            fea.insert(3, f'@kL_{a.replace(".", "_")} = [{" ".join(g)}];')
        for b, g in cls_r.items():
            fea.insert(3, f'@kR_{b.replace(".", "_")} = [{" ".join(g)}];')
        for (a, b), k in sorted(self.kern_pairs.items()):
            fea.append(f'        pos @kL_{a.replace(".", "_")} @kR_{b.replace(".", "_")} {k};')
        fea += ['    } KERN;', '} kern;', '']
        # mark positioning
        for name, (where, x, y) in sorted(self.mark_anchor.items()):
            fea.insert(3, f'markClass {name} <anchor {x} {y}> @MC_{where};')
        fea += ['feature mark {', '    lookup MARK_TOP {']
        for n, (x, y) in sorted(self.top_anchor.items()):
            fea.append(f'        pos base {n} <anchor {x} {y}> mark @MC_top;')
        fea += ['    } MARK_TOP;', '    lookup MARK_BOTTOM {']
        for n, (x, y) in sorted(self.bottom_anchor.items()):
            fea.append(f'        pos base {n} <anchor {x} {y}> mark @MC_bottom;')
        fea += ['    } MARK_BOTTOM;', '} mark;']
        return '\n'.join(fea)

    # ------------------------------------------------------------------ binary
    # the line box covers everything Irish, Scottish Gaelic, Welsh and Western European text uses;
    # rarer stacks (ĺ, ĥ, Ő...) may rise above it, and the Windows metrics still cover every glyph
    LINE_CHARS = ([chr(c) for c in range(0x21, 0x7F)] + [chr(c) for c in range(0xC0, 0x100)] +
                  list('ḂḃĊċḊḋḞḟĠġṀṁṖṗṠṡṪṫŴŵŶŷẀẁẂẃẄẅỲỳ'))

    def vertical(self):
        line = {self.cm[ord(c)] for c in self.LINE_CHARS if ord(c) in self.cm}
        ys = [bounds(self.final[n]) for n in line if n in self.final and bounds(self.final[n])]
        allb = [bounds(p) for n, p in self.final.items() if n != 'space' and bounds(p)]
        ymax = max(b[3] for b in ys); ymin = min(b[1] for b in ys)
        self.win = (int(math.ceil(max(b[3] for b in allb))) + 2, int(math.ceil(-min(b[1] for b in allb))) + 2)
        asc = int(math.ceil(ymax + 10)); desc = int(math.floor(ymin - 10))
        if asc - desc < 1200:
            extra = 1200 - (asc - desc); asc += int(extra * 0.6); desc -= extra - int(extra * 0.6)
        return asc, desc, int(math.ceil(ymax)), int(math.floor(ymin))

    def build(self, flavour):
        cfg = self.cfg; is_ttf = flavour == 'ttf'
        order = ['.notdef', 'space'] + sorted(n for n in self.final if n != 'space')
        fb = FontBuilder(1000, isTTF=is_ttf)
        fb.setupGlyphOrder(order); fb.setupCharacterMap(self.cm)
        from fontTools.misc.timeTools import timestampSinceEpoch
        import calendar, time
        stamp = timestampSinceEpoch(calendar.timegm(time.strptime(RELEASE_DATE, '%Y-%m-%d')))
        fb.updateHead(fontRevision=float(VERSION), macStyle=(1 if self.bold else 0) | (2 if self.italic else 0),
                      created=stamp, modified=stamp)
        style = self.style_name; ps = cfg['ps'] + '-' + style.replace(' ', '')
        adv = dict(self.adv); adv['.notdef'] = 500
        notdef = SH.difference(SH.polygon([(50, 0), (450, 0), (450, 700), (50, 700)]),
                               SH.polygon([(100, 50), (400, 50), (400, 650), (100, 650)]))
        paths = dict(self.final); paths['.notdef'] = notdef
        if is_ttf:
            glyf = {}
            for n in order:
                pen = TTGlyphPen(None)
                if bounds(paths[n]) is not None:
                    paths[n].draw(CleanPen(Cu2QuPen(CleanPen(pen), max_err=0.8, reverse_direction=True)))
                glyf[n] = pen.glyph()
            fb.setupGlyf(glyf)
            metrics = {n: (adv[n], getattr(fb.font['glyf'][n], 'xMin', 0)) for n in order}
        else:
            cs = {}
            for n in order:
                pen = T2CharStringPen(adv[n], None); paths[n].draw(CleanPen(pen)); cs[n] = pen.getCharString()
            info = {'FullName': f'{cfg["family"]} {style}', 'FamilyName': cfg['family'], 'Weight': 'Bold' if self.bold else 'Regular'}
            if self.italic:
                info['ItalicAngle'] = -SLANT
            fb.setupCFF(ps, info, cs, {})
            metrics = {}
            for n in order:
                b = cs[n].calcBounds(None); metrics[n] = (adv[n], b[0] if b else 0)
        fb.setupHorizontalMetrics(metrics)
        asc, desc, win = self.family_vm
        run = int(round(1000 * math.tan(math.radians(SLANT)))) if self.italic else 0
        fb.setupHorizontalHeader(ascent=asc, descent=desc, caretSlopeRise=1000, caretSlopeRun=run)
        fam = cfg['family']
        new = {'Regular': '', 'Italic': ' The sloped style was drawn in 2026 from the 1978 regular.',
               'Bold': ' The bold was drawn in 2026 from the 1978 regular, with a wider pen.',
               'Bold Italic': ' The bold sloped style was drawn in 2026 from the 1978 regular.'}[style]
        fb.setupNameTable(dict(
            copyright=f'Copyright 2026 Dan Drayne. Original design 1978 by {cfg["designer"]}; digitised 2026 from the printed specimen sheet.',
            licenseDescription=('This Font Software is licensed under the SIL Open Font License, Version 1.1. '
                                'This license is available with a FAQ at: https://openfontlicense.org'),
            licenseInfoURL='https://openfontlicense.org',
            familyName=fam, styleName=style, uniqueFontIdentifier=f'{VERSION};{ps}',
            fullName=f'{fam} {style}', psName=ps, version=f'Version {VERSION}',
            designer=cfg['designer'],
            description=(f'{fam}: {cfg["note"]} in the 1978 "Design an Irish Typeface" competition sponsored by '
                         'Letraset, Kilkenny Design Workshops and D. O\'Sullivan Graphic Supplies. Traced from the '
                         '"Four Irish Typefaces" flyer; glyphs not on the sheet were drawn to match.' + new)), mac=False)
        sel = (0x01 if self.italic else 0) | (0x20 if self.bold else 0)
        fb.setupOS2(sTypoAscender=asc, sTypoDescender=desc, sTypoLineGap=0, usWinAscent=max(asc, win[0]),
                    usWinDescent=max(-desc, win[1]), sxHeight=int(round(self.xh)), sCapHeight=int(round(self.cap)),
                    achVendID='NONE', fsType=0, usWeightClass=700 if self.bold else 400,
                    fsSelection=(sel or 0x40) | 0x80, version=4)
        fb.setupPost(keepGlyphNames=is_ttf, underlinePosition=-120, underlineThickness=int(0.35 * self.S_regular),
                     italicAngle=-SLANT if self.italic else 0)
        if is_ttf:
            fb.font['head'].flags |= (1 << 3)       # integer ppem (the TTF is hinted)
        addOpenTypeFeaturesFromString(fb.font, self.features())
        self.stat(fb.font)
        os2 = fb.font['OS/2']; os2.recalcUnicodeRanges(fb.font)
        try:
            os2.recalcCodePageRanges(fb.font)
        except AttributeError:
            pass
        return fb.font

    def stat(self, font):
        """Style attributes: where this style sits on weight and slope (one value per axis, as a
        static font should have), so apps that read STAT name and group the styles as the name
        table does. Regular and Roman are elided from names and point to Bold and Italic."""
        from fontTools.otlLib.builder import buildStatTable
        styles = FAMILY_STYLES[self.key]
        if self.bold:
            w = dict(value=700, name='Bold')
        else:
            w = dict(value=400, name='Regular', flags=0x2, **({'linkedValue': 700} if 'Bold' in styles else {}))
        if self.italic:
            it = dict(value=1, name='Italic')
        else:
            it = dict(value=0, name='Roman', flags=0x2, **({'linkedValue': 1} if 'Italic' in styles else {}))
        buildStatTable(font, [dict(tag='wght', name='Weight', values=[w]), dict(tag='ital', name='Italic', values=[it])],
                       elidedFallbackName=2, windowsNames=True, macNames=False)

    def prepare(self):
        K = KS[self.key] * LOOSEN * (BOLD[self.key]['space'] if self.bold else 1.0)
        self.specimen_pieces()
        self.punctuation(); self.dashes(); self.parens_slash_misc(); self.dotless(); self.make_marks()
        self.made.update(make_letters(self))
        self.composites()
        self.made.update(make_symbols(self))
        self.combining_and_spacing_marks()
        if self.italic:
            self.condense(); K *= CONDENSE
        self.build_cmap()
        self.space(K); self.kerning(); self.anchors()
        if self.italic:
            self.slant()
        self.vm = self.vertical()
        return self

    def run(self, family_vm=None):
        if not hasattr(self, 'vm'):
            self.prepare()
        asc, desc, _, _ = self.vm
        self.family_vm = family_vm or (asc, desc, self.win)
        os.makedirs(OUT, exist_ok=True)
        base = os.path.join(OUT, self.cfg['ps'] + '-' + self.style_name.replace(' ', ''))
        self.build('otf').save(base + '.otf')
        self.build('ttf').save(base + '.raw.ttf')
        r = subprocess.run(['ttfautohint', '--no-info', '-W', base + '.raw.ttf', base + '.ttf'], capture_output=True, text=True)
        if r.returncode != 0:
            os.replace(base + '.raw.ttf', base + '.ttf'); print('  ttfautohint failed:', r.stderr[:300])
        else:
            os.remove(base + '.raw.ttf')
        for flav in ('woff2', 'woff'):
            w = TTFont(base + '.ttf'); w.flavor = flav; w.save(base + '.' + flav)
        self.write_provenance(base + '.provenance.json')
        return base

    # ------------------------------------------------------------------ where each glyph came from
    DERIVED = {'grave': 'acute', 'hungarumlaut': 'acute', 'caron': 'circumflex', 'breve': 'ring', 'macron': 'endash'}
    MARK_WORDS = {'acute': 'acute', 'grave': 'grave', 'circumflex': 'circumflex', 'caron': 'caron', 'breve': 'breve',
                  'tilde': 'tilde', 'macron': 'macron', 'dot': 'dot', 'dieresis': 'diaeresis', 'ring': 'ring',
                  'hungarumlaut': 'double acute', 'commaturned': 'turned comma', 'commabelow': 'comma below',
                  'cedilla': 'cedilla', 'ogonek': 'ogonek', 'caronvert': 'apostrophe caron'}

    def mark_words(self, k):
        src = self.mark_source.get(k)
        w = self.MARK_WORDS[k]
        if src == 'sheet':
            return f'the sheet’s own {w}'
        if src == 'flyer':
            return f'the flyer’s {w}'
        d = self.DERIVED.get(k)
        if k == 'macron' and 'endash' in self.piece:
            return 'macron at the weight of the sheet’s rules'
        if d and self.mark_source.get(d):
            return f'{w} made from the sheet’s {self.MARK_WORDS.get(d, "rule")}'
        if k in ('dot', 'dieresis'):
            return f'{w} from the flyer’s dot'
        return f'{w} drawn to match'

    def write_provenance(self, path):
        import json
        out = {}
        for n in self.final:
            if n in self.mark_glyphs:
                how = ('mark', self.mark_words(self.mark_glyphs[n]))
            elif n in self.comp:
                how = ('composite', f'{self.comp[n]} + ' + ' + '.join(self.mark_words(k) for k in self.comp_marks.get(n, [])))
            elif n in self.made:
                how = ('made' if n not in self.traced else 'rebuilt', self.made[n])
            elif n in self.traced:
                how = ('flyer', 'traced from the 1978 flyer' + (f'; {self.touched[n]}' if n in self.touched else ''))
            elif n == 'space':
                how = ('made', 'word space')
            else:
                how = ('made', 'drawn to match the face')
            out[n] = how
        json.dump(out, open(path, 'w'), ensure_ascii=False, indent=0)


def family_metrics(fonts):
    """One set of line metrics for every style of a family, so switching style never moves a line."""
    asc = max(f.vm[0] for f in fonts); desc = min(f.vm[1] for f in fonts)
    return asc, desc, (max(f.win[0] for f in fonts), max(f.win[1] for f in fonts))


if __name__ == '__main__':
    only = [s.strip() for s in os.environ['STYLES'].split(',')] if os.environ.get('STYLES') else None
    for key in sys.argv[1:]:
        fonts = [Font2(key, st).prepare() for st in FAMILY_STYLES[key]]     # all styles set the metrics
        vm = family_metrics(fonts)
        for f in fonts:
            if only and f.style_name not in only:
                continue
            f.run(vm)
            print(f'{key} {f.style_name}: {len(f.final)} glyphs, {len(f.cm)} code points, {len(f.kern_pairs)} class kerns + '
                  f'{len(f.kern_exc)} exceptions, stem {f.S:.0f}, line {vm[0]}/{vm[1]}')
