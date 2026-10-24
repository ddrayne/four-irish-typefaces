"""Build the showcase site (showcase/) into build/showcase.

usage: python scripts/showcase.py [--artifact]

The site's own files (HTML, CSS, scripts, vendored libraries) live in showcase/.
This copies them, adds the released web fonts (fonts/woff2), the flyer scan, and
data generated from the fonts and sources:

  data/site.json    per face: styles, character map, stylistic sets; Unicode names;
                    the flyer audit (overlap per glyph); where each face sits on the flyer
  data/traced.json  every traced flyer glyph as an SVG path in scan pixels, with its points

--artifact also writes build/showcase-artifact/: the same site with the page split
into the form the Artifact viewer expects and the fonts inlined as data URIs.
"""
import paths
import base64, json, os, re, shutil, sys, unicodedata
from fontTools.ttLib import TTFont
from build2 import FONTS, FAMILY_STYLES, VERSION
import traced

SRC = os.path.join(paths.ROOT, 'showcase')
DEST = os.path.join(paths.BUILD, 'showcase')
WOFF2 = os.path.join(paths.ROOT, 'fonts', 'woff2')
OTF = os.path.join(paths.ROOT, 'fonts', 'otf')
AUDIT = os.path.join(paths.ROOT, 'docs', 'validation', 'flyer-glyph-audit.md')
ORDER = ['ceili', 'carrick', 'kilfane', 'tuam']
STYLE = {'Regular': (400, 'normal'), 'Italic': (400, 'italic'), 'Bold': (700, 'normal'), 'Bold Italic': (700, 'italic')}
HEADINGS = {'Céilí': 'ceili', 'Carrick': 'carrick', 'Kilfane': 'kilfane', 'Tuam Uncial': 'tuam'}


def fontface_css():
    out = []
    for k in ORDER:
        cfg = FONTS[k]
        for style in FAMILY_STYLES[k]:
            w, s = STYLE[style]
            out.append('@font-face{font-family:"%s";src:url("../fonts/%s-%s.woff2") format("woff2");'
                       'font-weight:%d;font-style:%s;font-display:swap}'
                       % (cfg['family'], cfg['ps'], style.replace(' ', ''), w, s))
        if FAMILY_STYLES[k] == ['Regular', 'Italic']:
            # One black weight: answer bold from the same drawing, never a synthetic smear.
            for style, s in (('Regular', 'normal'), ('Italic', 'italic')):
                out.append('@font-face{font-family:"%s";src:url("../fonts/%s-%s.woff2") format("woff2");'
                           'font-weight:500 900;font-style:%s;font-display:swap}' % (cfg['family'], cfg['ps'], style, s))
    return '\n'.join(out) + '\n'


def face_data():
    faces, names = {}, {}
    for k in ORDER:
        cfg = FONTS[k]
        tt = TTFont(os.path.join(OTF, f'{cfg["ps"]}-Regular.otf'))
        cmap = tt.getBestCmap()
        by_glyph = {}
        for cp, g in cmap.items():
            by_glyph.setdefault(g, cp)
        sets = []
        for tag, label, mapping in cfg.get('sets', []):
            sets.append(dict(tag=tag, label=label, chars=''.join(chr(by_glyph[b]) for b in mapping if b in by_glyph)))
        cps = sorted(cp for cp in cmap if cp > 0x20 and not 0xE000 <= cp <= 0xF8FF)
        for cp in cps:
            names.setdefault(cp, unicodedata.name(chr(cp), ''))
        upm = tt['head'].unitsPerEm
        faces[k] = dict(family=cfg['family'], file=cfg['ps'], unicase=cfg['unicase'],
                        styles=FAMILY_STYLES[k], sets=sets, cps=cps, glyphs=len(tt.getGlyphOrder()),
                        xh=round(tt['OS/2'].sxHeight / upm, 4), cap=round(tt['OS/2'].sCapHeight / upm, 4))
    return faces, {f'{cp:04X}': n for cp, n in sorted(names.items())}


def audit_data():
    audit, face = {}, None
    for line in open(AUDIT, encoding='utf-8'):
        m = re.match(r'## (.+)', line)
        if m:
            face = HEADINGS.get(m.group(1).strip())
            if face:
                audit[face] = dict(glyphs={})
            continue
        m = re.match(r'(\d+) glyphs, mean overlap (\d\.\d+)', line)
        if m and face:
            audit[face].update(n=int(m.group(1)), mean=float(m.group(2)))
        m = re.match(r'\| `([^`]+)` \| ([\d.]+) \|', line)
        if m and face:
            audit[face]['glyphs'][m.group(1)] = float(m.group(2))
    return audit


def traced_data():
    out, regions = {}, {}
    for k in ORDER:
        glyphs = []
        for g in traced.records(k):
            d, pts, xs, ys = [], [], [], []
            for op, args in g['rec']:
                if op == 'moveTo':
                    (x, y), = args
                    d.append(f'M{x:.2f} {y:.2f}'); pts.append([round(x, 2), round(y, 2), 1])
                elif op == 'lineTo':
                    (x, y), = args
                    d.append(f'L{x:.2f} {y:.2f}'); pts.append([round(x, 2), round(y, 2), 1])
                elif op == 'curveTo':
                    d.append('C' + ' '.join(f'{x:.2f} {y:.2f}' for x, y in args))
                    for i, (x, y) in enumerate(args):
                        pts.append([round(x, 2), round(y, 2), 1 if i == len(args) - 1 else 0])
                elif op == 'qCurveTo':
                    d.append('Q' + ' '.join(f'{x:.2f} {y:.2f}' for x, y in args))
                    for i, (x, y) in enumerate(args):
                        pts.append([round(x, 2), round(y, 2), 1 if i == len(args) - 1 else 0])
                elif op == 'closePath':
                    d.append('Z')
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            if not xs:
                continue
            glyphs.append(dict(n=g['name'], d=''.join(d), b=[round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)], p=pts))
        out[k] = glyphs
        regions[k] = [min(g['b'][0] for g in glyphs), min(g['b'][1] for g in glyphs),
                      max(g['b'][2] for g in glyphs), max(g['b'][3] for g in glyphs)]
    return out, regions


def build():
    if os.path.exists(DEST):
        shutil.rmtree(DEST)
    shutil.copytree(SRC, DEST, ignore=shutil.ignore_patterns('README.md'))
    os.makedirs(os.path.join(DEST, 'fonts'), exist_ok=True)
    os.makedirs(os.path.join(DEST, 'data'), exist_ok=True)
    for k in ORDER:
        for style in FAMILY_STYLES[k]:
            fn = f'{FONTS[k]["ps"]}-{style.replace(" ", "")}.woff2'
            shutil.copy(os.path.join(WOFF2, fn), os.path.join(DEST, 'fonts', fn))
    shutil.copy(os.path.join(paths.ROOT, 'OFL.txt'), os.path.join(DEST, 'fonts', 'OFL.txt'))
    shutil.copy(paths.SCAN, os.path.join(DEST, 'img', 'flyer.jpg'))
    open(os.path.join(DEST, 'css', 'faces.css'), 'w', encoding='utf-8').write(fontface_css())
    faces, names = face_data()
    glyphs, regions = traced_data()
    site = dict(v=VERSION, order=ORDER, faces=faces, names=names, audit=audit_data(),
                flyer=dict(w=803, h=1125, regions=regions))
    dump = lambda obj, fn: open(os.path.join(DEST, 'data', fn), 'w', encoding='utf-8').write(
        json.dumps(obj, ensure_ascii=False, separators=(',', ':')))
    dump(site, 'site.json')
    dump(glyphs, 'traced.json')
    html = open(os.path.join(DEST, 'index.html'), encoding='utf-8').read()
    open(os.path.join(DEST, 'index.html'), 'w', encoding='utf-8').write(html.replace('{{V}}', VERSION))
    print('built', DEST)


def artifact():
    """The Artifact viewer wraps the page in its own document and blocks font loads
    from anywhere but data: URIs, so split the page and inline the fonts."""
    dest = os.path.join(paths.BUILD, 'showcase-artifact')
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(DEST, dest)
    html = open(os.path.join(dest, 'index.html'), encoding='utf-8').read()
    head = re.search(r'<head>(.*?)</head>', html, re.S).group(1)
    body = re.search(r'<body([^>]*)>(.*?)</body>', html, re.S)
    head = re.sub(r'<meta charset[^>]*>\s*|<meta name="viewport"[^>]*>\s*|<link rel="preload"[^>]*>\s*', '', head)
    page = head.strip() + '\n' + f'<div id="page-root"{body.group(1)}>' + body.group(2) + '</div>\n'
    open(os.path.join(dest, 'index.html'), 'w', encoding='utf-8').write(page)

    def inline(css_path):
        css = open(css_path, encoding='utf-8').read()
        def sub(m):
            path = os.path.normpath(os.path.join(os.path.dirname(css_path), m.group(1)))
            data = base64.b64encode(open(path, 'rb').read()).decode()
            return f'url("data:font/woff2;base64,{data}")'
        open(css_path, 'w', encoding='utf-8').write(re.sub(r'url\("?([^")]+\.woff2)"?\)', sub, css))
    for fn in os.listdir(os.path.join(dest, 'css')):
        inline(os.path.join(dest, 'css', fn))
    print('built', dest)


if __name__ == '__main__':
    build()
    if '--artifact' in sys.argv:
        artifact()
