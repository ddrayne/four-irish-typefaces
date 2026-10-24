"""Compare two sets of fonts glyph by glyph: outlines, advances and the layout and naming tables
(timestamps and checksums are ignored). Exit status 1 if anything differs.

usage: python scripts/compare_builds.py DIR_A DIR_B
"""
import glob, os, sys
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

TABLES = ('GPOS', 'GSUB', 'GDEF', 'OS/2', 'name', 'STAT', 'hhea', 'post', 'cmap')


def index(d):
    return {os.path.basename(p): p for p in glob.glob(os.path.join(d, '**', '*.otf'), recursive=True)}


def diff(pa, pb):
    a, b = TTFont(pa), TTFont(pb)
    ga, gb = a.getGlyphSet(), b.getGlyphSet()
    if a.getGlyphOrder() != b.getGlyphOrder():
        return ['glyph order']
    out = []
    for n in a.getGlyphOrder():
        r1, r2 = RecordingPen(), RecordingPen(); ga[n].draw(r1); gb[n].draw(r2)
        if r1.value != r2.value or a['hmtx'][n] != b['hmtx'][n]:
            out.append(n)
    out += [f'<{t}>' for t in TABLES if (t in a) != (t in b) or (t in a and a[t].compile(a) != b[t].compile(b))]
    return out


if __name__ == '__main__':
    A, B = index(sys.argv[1]), index(sys.argv[2])
    bad = 0
    for name in sorted(set(A) | set(B)):
        if name not in A or name not in B:
            print(f'{name}: only in {"A" if name in A else "B"}'); bad += 1; continue
        d = diff(A[name], B[name])
        if d:
            print(f'{name}: {len(d)} differences: {" ".join(d[:12])}{" …" if len(d) > 12 else ""}'); bad += 1
    print('identical' if not bad else f'{bad} fonts differ')
    sys.exit(1 if bad else 0)
