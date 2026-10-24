"""Style-linking and consistency audit for each family: naming, style bits, slope, STAT, line
metrics and character sets, for every format.

usage: famaudit.py FONTDIR
"""
import sys, glob, os, collections
from fontTools.ttLib import TTFont
d = sys.argv[1]
fams = collections.defaultdict(list)
for p in sorted(glob.glob(f'{d}/*.otf') + glob.glob(f'{d}/*.ttf') + glob.glob(f'{d}/*.woff') + glob.glob(f'{d}/*.woff2')):
    fams[os.path.basename(p).split('-')[0]].append(p)
problems = []
for fam, paths in fams.items():
    ref = None
    rows = []
    for p in paths:
        f = TTFont(p); n = f['name']; os2 = f['OS/2']; head = f['head']; post = f['post']; hhea = f['hhea']
        style = n.getDebugName(2); fname = n.getDebugName(1)
        bold, italic = 'Bold' in style, 'Italic' in style
        exp_sel = (0x01 if italic else 0) | (0x20 if bold else 0) or 0x40
        checks = {
            'fsSelection': (os2.fsSelection & 0x61) == exp_sel and os2.fsSelection & 0x80,
            'macStyle': head.macStyle & 3 == (1 if bold else 0) | (2 if italic else 0),
            'weight': os2.usWeightClass == (700 if bold else 400),
            'italicAngle': post.italicAngle == (-8.0 if italic else 0.0),
            'caret': (hhea.caretSlopeRun == 141) == italic and hhea.caretSlopeRise == 1000,
            'names': n.getDebugName(4) == f'{fname} {style}' and n.getDebugName(6) == f'{os.path.basename(p).rsplit(".", 1)[0]}',
            'no mac names': not any(r.platformID == 1 for r in n.names),
            'STAT': 'STAT' in f and len(f['STAT'].table.AxisValueArray.AxisValue) == 2,
        }
        if 'CFF ' in f:
            top = f['CFF '].cff.topDictIndex[0]
            checks['CFF'] = getattr(top, 'ItalicAngle', 0) == (-8 if italic else 0) and top.Weight == ('Bold' if bold else 'Regular')
        bad = [k for k, v in checks.items() if not v]
        vm = (hhea.ascent, hhea.descent, os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap, os2.usWinAscent, os2.usWinDescent)
        cps = frozenset(f.getBestCmap())
        if ref is None:
            ref = (vm, cps, fname)
        if vm != ref[0]: bad.append(f'line metrics {vm} != {ref[0]}')
        if cps != ref[1]: bad.append(f'cmap differs by {len(cps ^ ref[1])}')
        if fname != ref[2]: bad.append('family name')
        rows.append((os.path.basename(p), style, n.getDebugName(5), bad))
        if bad: problems.append((os.path.basename(p), bad))
    print(f'{fam}: {len(paths)} files, styles {sorted(set(r[1] for r in rows))}, {rows[0][2]}, line {ref[0][:2]}, {len(ref[1])} code points')
print('problems:', problems or 'none')
