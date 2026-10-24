"""Build the test page app (irish-typefaces.apps.drayne.xyz) from site_src/ and the built fonts.

usage: python site.py DEST [FONTDIR]
  DEST     the app folder (Dockerfile, nginx.conf, publish.json, site/)
  FONTDIR  the built fonts with their .provenance.json files (default build/fonts)
"""
import paths
import html, json, os, shutil, sys
import numpy as np
from PIL import Image
from fontTools.ttLib import TTFont
from build2 import FONTS, VERSION, FAMILY_STYLES
import selfhost_page as SP
import site_data

V = VERSION
SRC = paths.SITE_SRC
PKG = SP.PKG
ORDER = ['ceili', 'carrick', 'kilfane', 'tuam']          # by prize
STACK = {'ceili': '"Céilí", "Ceili", Georgia, serif', 'carrick': '"Carrick", Georgia, serif',
         'kilfane': '"Kilfane", Georgia, serif', 'tuam': '"Tuam Uncial", Georgia, serif'}
CLS = {'ceili': 'f-ceili', 'carrick': 'f-carrick', 'kilfane': 'f-kilfane', 'tuam': 'f-tuam'}
INFO = {
    'ceili': dict(prize='First prize', who='Hermann Hecht', sheets=[('S53915', '24 pt', '6.5 mm'), ('S53916', '42 pt', '11 mm')],
                  sample='céilí mór', feats=[('ss01', 'Insular r, s'), ('ss02', 'Uncial a, n'), ('ss03', 'Alternates')]),
    'carrick': dict(prize='Second prize', who='William Curran', sheets=[('S53913', '36 pt', '9 mm'), ('S53914', '60 pt', '15 mm')],
                    sample='carraig', feats=[]),
    'kilfane': dict(prize='Joint third prize', who='William Curran', sheets=[('S53909', '30 pt', '7.5 mm'), ('S53910', '48 pt', '13 mm')],
                    sample='Fáilte', feats=[('ss01', 'Roman forms'), ('ss02', 'Insular forms')]),
    'tuam': dict(prize='Highly commended', who='Jarlath Hayes', sheets=[('S53911', '30 pt', '7.5 mm'), ('S53912', '48 pt', '12.5 mm')],
                 sample='Tuaim', feats=[]),
}
ROWS_CAPS = ['ABCDEFGHIJKLM', 'NOPQRSTUVWXYZ']
ROWS = ['abcdefghijklm', 'nopqrstuvwxyz', '1234567890&?!£$', 'áéíóúḃċḋḟġṁṗṡṫ⁊', '(;:).,’-–«»']
esc = html.escape


def config(fontdir):
    faces = {}
    for k in ORDER:
        cfg = FONTS[k]; tt = TTFont(os.path.join(fontdir, f'{cfg["ps"]}-Regular.otf'))
        cm = tt.getBestCmap(); upm = tt['head'].unitsPerEm; hh = tt['hhea']; os2 = tt['OS/2']
        rows = ROWS if cfg['unicase'] else ROWS_CAPS + ROWS[:3] + ['ÁÉÍÓÚ'] + ROWS[3:]
        rows = [''.join(c for c in r if ord(c) in cm) for r in rows]
        alts = [[chr(min(cp for cp, g in cm.items() if g == b)), tag, label]
                for tag, label, mapping in cfg.get('sets', []) for b, alt in mapping.items()]
        faces[k] = dict(family=cfg['family'], stack=STACK[k], cls=CLS[k], file=cfg['ps'], sheets=INFO[k]['sheets'], styles=FAMILY_STYLES[k],
                        sample=INFO[k]['sample'], rows=[r for r in rows if r], alts=alts, cmap=sorted(cm),
                        m=dict(asc=round(hh.ascent / upm, 4), desc=round(hh.descent / upm, 4), xh=round(os2.sxHeight / upm, 4)))
    return dict(v=V, q=f'?v={V}', order=ORDER, faces=faces, presets=SP.PRESETS, flyer='img/flyer.jpg', flyerSize=[803, 1125])


def tiles():
    out = []
    for k in ORDER:
        i = INFO[k]
        out.append(f'<li class="face-tile"><a href="#sheet" data-face="{k}"><span class="name {CLS[k]}">{esc(FONTS[k]["family"])}</span>'
                   f'<span class="prize">{esc(i["prize"])}</span><span class="who">{esc(i["who"])}</span>'
                   f'<span class="codes">Sheets {" · ".join(s[0] for s in i["sheets"])}</span></a></li>')
    return '\n      '.join(out)


def tabs():
    return ''.join(f'<button type="button" class="tab {CLS[k]}" role="tab" data-face="{k}" aria-selected="false" tabindex="-1">'
                   f'{esc(FONTS[k]["family"])}</button>' for k in ORDER)


def tester_rows():
    out = []
    for k in ORDER:
        i = INFO[k]
        feats = ''.join(f'<button type="button" class="feat" data-feat="{t}" aria-pressed="false">{esc(l)}</button>' for t, l in i['feats'])
        out.append(f'''<div class="row" data-face="{k}">
        <div class="row-meta"><span class="row-name {CLS[k]}">{esc(FONTS[k]["family"])}</span>
          <span class="row-who">{esc(i["who"])} · {esc(i["prize"].lower())}</span>
          {f'<div class="row-feats" role="group" aria-label="Stylistic sets">{feats}</div>' if feats else ''}
          <span class="row-cover"></span></div>
        <div class="row-text {CLS[k]}" lang="ga"></div>
      </div>''')
    return '\n      '.join(out)


STYLES = ['Regular', 'Italic', 'Bold', 'Bold Italic']
SAMPLE2 = {'ceili': 'Céilí mór anocht!', 'carrick': 'Ceol ⁊ craic', 'kilfane': 'Banc Ceannais na hÉireann', 'tuam': 'Fáilte go Tuaim'}
weight = lambda st: 700 if 'Bold' in st else 400
slope = lambda st: 'italic' if 'Italic' in st else 'normal'


def style_chips():
    return ''.join(f'<button type="button" class="chip" data-style="{st}" aria-pressed="{"true" if st == "Regular" else "false"}">{st}</button>'
                   for st in STYLES)


def family_rows():
    out = []
    for k in ORDER:
        styles = FAMILY_STYLES[k]
        note = ('Regular, italic, bold and bold italic' if 'Bold' in styles else
                'Regular and italic · black already, so no bold')
        rows = ''.join(f'<div class="fam-style"><span class="fam-st">{st}</span><span class="fam-txt {CLS[k]}" lang="ga" '
                       f'style="font-weight:{weight(st)};font-style:{slope(st)}">{esc(SAMPLE2[k])}</span></div>' for st in styles)
        out.append(f'<div class="fam" data-face="{k}"><div class="fam-head"><span class="fam-name {CLS[k]}">{esc(FONTS[k]["family"])}</span>'
                   f'<span class="fam-note">{note}</span></div>{rows}</div>')
    return '\n      '.join(out)


def sheet_rows():
    rows = []
    for k in ('kilfane', 'tuam', 'carrick', 'ceili'):
        for code, pt, mm in INFO[k]['sheets']:
            rows.append(f'<tr><td class="num">{code}</td><td class="{CLS[k]}">{esc(FONTS[k]["family"])}</td><td class="num">{pt}</td><td class="num">{mm}</td></tr>')
    return ''.join(sorted(rows))


def match_rows(datadir):
    rows, allv = [], []
    for k in ORDER:
        d = json.load(open(os.path.join(datadir, f'{k}.json')))
        v = [o['iou'] for o in d['flyer'].values()]; allv += v
        rows.append(f'<tr><td class="{CLS[k]}">{esc(FONTS[k]["family"])}</td><td class="num">{len(v)}</td><td class="num">{np.mean(v):.3f}</td></tr>')
    return ''.join(rows), len(allv), f'{np.mean(allv):.3f}'


def main(dest, fontdir, licence):
    site = os.path.join(dest, 'site')
    if os.path.exists(dest):
        shutil.rmtree(dest)
    for sub in ('css', 'js', 'img', 'data', 'downloads', 'fonts'):
        os.makedirs(os.path.join(site, sub), exist_ok=True)
    for fmt in ('woff2', 'woff', 'otf', 'ttf'):
        shutil.copytree(os.path.join(PKG, 'fonts', fmt), os.path.join(site, 'fonts', fmt))
    SP.write_css(os.path.join(site, 'css/four-irish-typefaces.css'))
    shutil.copy(os.path.join(SRC, 'site.css'), os.path.join(site, 'css/site.css'))
    shutil.copy(os.path.join(SRC, 'site.js'), os.path.join(site, 'js/site.js'))
    # the flyer registration is slow: reuse it while the fonts are unchanged
    stamp = json.dumps({f: os.path.getmtime(os.path.join(fontdir, f)) for f in sorted(os.listdir(fontdir)) if f.endswith(('.otf', '.json'))})
    cache = os.path.join(paths.CACHE, 'site')
    if not os.path.exists(os.path.join(cache, 'stamp')) or open(os.path.join(cache, 'stamp')).read() != stamp:
        site_data.main(fontdir, cache); open(os.path.join(cache, 'stamp'), 'w').write(stamp)
    for k in ORDER:
        shutil.copy(os.path.join(cache, f'{k}.json'), os.path.join(site, 'data', f'{k}.json'))
    for name in (f'four-irish-typefaces-fonts-v{V}.zip', f'four-irish-typefaces-v{V}.zip'):
        shutil.copy(os.path.join(SP.ZIPS, name), os.path.join(site, 'downloads', name))
    shutil.copy(os.path.join(PKG, 'docs/specimen/Four-Irish-Typefaces-specimen.pdf'), os.path.join(site, 'downloads'))
    shutil.copy(os.path.join(PKG, 'OFL.txt'), os.path.join(site, 'OFL.txt'))
    shutil.copy(os.path.join(PKG, 'OFL.txt'), os.path.join(site, 'fonts', 'OFL.txt'))
    Image.open(paths.SCAN).convert('L').save(os.path.join(site, 'img/flyer.jpg'), 'JPEG', quality=88, optimize=True, progressive=True)
    SP.icon(64, os.path.join(site, 'img/icon-64.png')); SP.icon(180, os.path.join(site, 'img/icon-180.png'))
    m_rows, n_flyer, mean = match_rows(os.path.join(site, 'data'))
    sizes = dict(SIZE_FONTS=SP.kb(os.path.join(site, f'downloads/four-irish-typefaces-fonts-v{V}.zip')),
                 SIZE_FULL=SP.kb(os.path.join(site, f'downloads/four-irish-typefaces-v{V}.zip')),
                 SIZE_PDF=SP.kb(os.path.join(site, 'downloads/Four-Irish-Typefaces-specimen.pdf')))
    fill = dict(V=V, FACE_TILES=tiles(), TABS=tabs(), TESTER_ROWS=tester_rows(), SHEET_ROWS=sheet_rows(),
                STYLE_CHIPS=style_chips(), FAMILY_ROWS=family_rows(),
                PRESET_OPTIONS=''.join(f'<option value="{i}">{esc(p[1])}</option>' for i, p in enumerate(SP.PRESETS)),
                MATCH_ROWS=m_rows, N_FLYER=str(n_flyer), MEAN_MATCH=mean, LICENCE=licence,
                CONFIG=json.dumps(config(fontdir), ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/'), **sizes)
    doc = open(os.path.join(SRC, 'index.html')).read()
    for k, v in fill.items():
        doc = doc.replace('{{' + k + '}}', v)
    assert '{{' not in doc, doc[doc.index('{{'):doc.index('{{') + 40]
    open(os.path.join(site, 'index.html'), 'w').write(doc)
    SP.social_card(dest, os.path.join(site, 'img/social.png'))
    open(os.path.join(dest, 'Dockerfile'), 'w').write(SP.DOCKERFILE)
    open(os.path.join(dest, '.dockerignore'), 'w').write(SP.DOCKERIGNORE)
    nginx = SP.NGINX.replace("""    location / {
        limit_except GET { deny all; }
        try_files $uri $uri/ =404;
    }""", """    location / {
        limit_except GET { deny all; }
        add_header X-Content-Type-Options nosniff always;
        add_header Cache-Control "public, max-age=300" always;
        add_header Referrer-Policy strict-origin-when-cross-origin always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'none'; frame-ancestors 'self'" always;
        try_files $uri $uri/ =404;
    }
    location /js/ {
        limit_except GET { deny all; }
        add_header X-Content-Type-Options nosniff always;
        add_header Cache-Control "public, max-age=3600" always;
    }
    location /data/ {
        limit_except GET { deny all; }
        add_header X-Content-Type-Options nosniff always;
        add_header Cache-Control "public, max-age=3600" always;
    }""")
    assert 'location /data/' in nginx
    open(os.path.join(dest, 'nginx.conf'), 'w').write(nginx)
    open(os.path.join(dest, 'README.md'), 'w').write(SP.README.replace(
        "- `site/index.html`: test page (tester, browser check, scan comparisons, downloads)",
        "- `site/index.html`, `site/css/site.css`, `site/js/site.js`: the test page (transfer sheet and board, tester,\n"
        "  every character with its 1978 print, the accent sets, the story, downloads)\n"
        "- `site/data/`: per-face character lists and the flyer outlines the page lays over the scan"))
    publish = dict(slug=SP.SLUG, title=SP.TITLE, description=SP.DESCRIPTION, access='public', repository=f'ddrayne/{SP.SLUG}',
                   branch='main', port=80, buildPack='dockerfile', memoryMiB=256, cpus=0.5, domain=f'https://{SP.SLUG}.apps.drayne.xyz')
    open(os.path.join(dest, 'publish.json'), 'w').write(json.dumps(publish, indent=2, ensure_ascii=False) + '\n')
    total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(dest) for f in fs)
    print('wrote', dest, f'{total / 1e6:.1f} MB', 'index.html', os.path.getsize(os.path.join(site, 'index.html')))


def preview(site_dir, page_out, root):
    """The claude.ai preview of the same page. ZIP files can't be served there, so the fonts package is
    packed in the browser from served copies of its files; cache-busting queries are dropped."""
    if os.path.exists(root):
        shutil.rmtree(root)
    shutil.copytree(site_dir, root, ignore=shutil.ignore_patterns('*.zip', 'social.png', 'index.html'))
    for rel in ('README.md', 'index.html', 'css/four-irish-typefaces.css'):
        os.makedirs(os.path.dirname(os.path.join(root, 'package', rel)), exist_ok=True)
        shutil.copy(os.path.join(PKG, rel), os.path.join(root, 'package', rel))
    q = f'?v={V}'
    for rel in ('css/four-irish-typefaces.css',):
        p = os.path.join(root, rel); text = open(p).read().replace(q, ''); open(p, 'w').write(text)
    entries = []
    for fmt in ('woff2', 'woff', 'otf', 'ttf'):
        for f in sorted(os.listdir(os.path.join(root, 'fonts', fmt))):
            entries.append([f'four-irish-typefaces/fonts/{fmt}/{f}', f'fonts/{fmt}/{f}'])
    entries += [['four-irish-typefaces/css/four-irish-typefaces.css', 'package/css/four-irish-typefaces.css'],
                ['four-irish-typefaces/README.md', 'package/README.md'], ['four-irish-typefaces/OFL.txt', 'OFL.txt'],
                ['four-irish-typefaces/index.html', 'package/index.html']]
    doc = open(os.path.join(site_dir, 'index.html')).read().replace(q, '')
    i = doc.index('<script type="application/json" id="config">') + len('<script type="application/json" id="config">')
    j = doc.index('</script>', i)
    cfg = json.loads(doc[i:j].replace('<\\/', '</'))
    cfg.update(q='', pack=dict(name=f'four-irish-typefaces-fonts-v{V}.zip', entries=entries))
    doc = doc[:i] + json.dumps(cfg, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + doc[j:]
    open(page_out, 'w').write(doc)
    files = {}
    for dp, dn, fn in os.walk(root):
        for f in fn:
            full = os.path.join(dp, f); files[os.path.relpath(full, root)] = full
    json.dump(files, open(os.path.join(os.path.dirname(page_out), 'files2.json'), 'w'), indent=1)
    print('preview', page_out, len(files), 'supporting files', f'{sum(os.path.getsize(p) for p in files.values()) / 1e6:.1f} MB')


LICENCE = ('Fonts copyright 2026 Dan Drayne, released under the <a href="OFL.txt">SIL Open Font License 1.1</a>: '
           'use them for anything, share and adapt them, but don’t sell the fonts on their own.')

if __name__ == '__main__':
    if sys.argv[1] == '--preview':           # python site.py --preview APPDIR PAGE.html ROOTDIR
        preview(os.path.join(sys.argv[2], 'site'), sys.argv[3], sys.argv[4])
    else:
        main(sys.argv[1], os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else paths.FONTS, LICENCE)
