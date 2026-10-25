"""Build the published web specimen: one self-contained HTML page (fonts and scan crops inlined).

Each face's section places every glyph of the font exactly where its counterpart sits on the
1978 flyer, so the scan and the font can be compared side by side or overlaid.
"""
import traced
import paths
import base64, html, io, json, os, pickle, sys
from PIL import Image
from fontTools.ttLib import TTFont
from fontTools import agl
from build2 import FONTS
from glyphs import SCALE
from metrics import line_baselines

FONTDIR = paths.FONTS
ORDER = ['ceili', 'carrick', 'kilfane', 'tuam']
CSSNAME = {'ceili': 'Ceili', 'carrick': 'Carrick', 'kilfane': 'Kilfane', 'tuam': 'Tuam Uncial'}
ANCHOR = {'ceili': 'ceili', 'carrick': 'carrick', 'kilfane': 'kilfane', 'tuam': 'tuam'}

INFO = {
    'ceili': dict(
        result='First prize', designer='Hermann Hecht', dates='1923–1985',
        sheets=[('S53915', '24 pt', '6.5 mm'), ('S53916', '42 pt', '11 mm')],
        traits='Old-style figures · insular r, s and g · three stylistic sets',
        note=('Hecht’s winning design is light and calligraphic, with one set of letters for both '
              'cases, as in early Irish manuscripts. The flyer shows three forms of a and two each of '
              'd, e, j, l, n, r, s and v. All of them are in the font.'),
        chips=[('ss01', 'Insular r, s'), ('ss02', 'Uncial a, n'), ('ss03', 'Alternates')]),
    'carrick': dict(
        result='Highly Commended', designer='William Curran', dates='1919–2016',
        sheets=[('S53913', '36 pt', '9 mm'), ('S53914', '60 pt', '15 mm')],
        traits='Lining figures · accents from the sheet’s own set',
        note=('A heavy, chiselled lower case with no capitals. The name comes from carraig, Irish for '
              'rock. Curran’s archive, with his drawings for Carrick and Kilfane, went to the National '
              'Irish Visual Arts Library in 2025.'),
        chips=[]),
    'kilfane': dict(
        result='Commended', designer='William Curran', dates='1919–2016',
        sheets=[('S53909', '30 pt', '7.5 mm'), ('S53910', '48 pt', '13 mm')],
        traits='True capitals · Roman and insular alternates · accents from the sheet’s own set',
        note=('The only one of the four with true capitals. The flyer’s last line shows alternates for '
              'A, D, S, T, Y, d, f, g, l, t and y, which two stylistic sets switch between Roman and '
              'insular forms. It is reported to have been used on the Series C Irish banknotes.'),
        chips=[('ss01', 'Roman forms'), ('ss02', 'Insular forms')]),
    'tuam': dict(
        result='Commended', designer='Jarlath Hayes', dates='1924–2001',
        sheets=[('S53911', '30 pt', '7.5 mm'), ('S53912', '48 pt', '12.5 mm')],
        traits='Lining figures · cut dots and hairline notches, as on the flyer',
        note=('A heavy, square uncial. Hayes is said to have made it by cutting up Helvetica Bold, and '
              'the hairline cuts through its dots and joins are part of the design. Signal Type Foundry '
              'has since released a commercial revival, Jarlath, made with the Hayes family.'),
        chips=[]),
}
SAMPLE = 'Is fearr Gaeilge bhriste ná Béarla cliste'


def b64(data):
    return base64.b64encode(data).decode('ascii')


def jpeg_uri(im, q=86):
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=q, optimize=True, progressive=True)
    return 'data:image/jpeg;base64,' + b64(buf.getvalue()), len(buf.getvalue())


def char_for(name):
    if name == 'ornament':
        return ''
    return agl.toUnicode(name)


def feature_for(key, name):
    """(base glyph name, feature tag) for an alternate, from the face's stylistic sets."""
    for tag, _, mapping in FONTS[key]['sets']:
        for base, alt in mapping.items():
            if alt == name:
                return base, tag
    return None, None


def face_data(key):
    ps = FONTS[key]['ps']
    otf = TTFont(os.path.join(FONTDIR, ps + '-Regular.otf'))
    cm = otf.getBestCmap(); hmtx = otf['hmtx']; gs = otf.getGlyphSet()
    from fontTools.pens.boundsPen import BoundsPen
    def ink(g):
        bp = BoundsPen(gs); gs[g].draw(bp); return bp.bounds
    os2 = otf['OS/2']; upm = otf['head'].unitsPerEm
    m = dict(a=otf['hhea'].ascent / upm, d=-otf['hhea'].descent / upm, xh=os2.sxHeight / upm, cap=os2.sCapHeight / upm)
    # scan geometry
    res = traced.records(key); base = line_baselines(res); s = SCALE[key]
    x0 = min(r['b'][0] for r in res); x1 = max(r['b'][2] for r in res)
    y0 = min(r['b'][1] for r in res); y1 = max(r['b'][3] for r in res)
    sheet = Image.open(paths.SCAN).convert('L')
    gray = sheet.load()
    top = int(y0) - 10
    for y in range(int(y0) - 1, int(y0) - 11, -1):        # stop above the face's label on the flyer
        if sum(gray[x, y] < 150 for x in range(int(x0) - 10, int(x1) + 12)) > 3:
            top = y + 3; break
    crop = (int(x0) - 10, top, int(x1) + 12, int(y1) + 12)
    Wc, Hc = crop[2] - crop[0], crop[3] - crop[1]
    im = sheet.crop(crop).resize((Wc * 3, Hc * 3), Image.LANCZOS)
    uri, nbytes = jpeg_uri(im)
    em_px = upm / s                                   # one em in scan px
    k_top = (1 - (m['a'] + m['d'])) / 2 + m['a']      # baseline below the top of a 1em line box
    spans = []
    rev = {}
    for c, g in cm.items():
        rev.setdefault(g, []).append(c)
    def place(ch, tag, gname, cx, cy=None, line=None):
        gb = ink(gname)
        lsb, w = gb[0], gb[2] - gb[0]
        left_px = cx - (lsb + w / 2) / s - crop[0]
        if cy is None:
            top_px = base[line] - crop[1] - k_top * em_px
        else:                                         # centre the glyph's ink on (cx, cy)
            top_px = cy - crop[1] + (gb[1] + gb[3]) / (2 * s) - k_top * em_px
        spans.append((ch, tag, left_px * 100 / Wc, top_px * 100 / Wc))
    for r in res:
        name = r['name']
        if name == 'DOTS':
            # Céilí's bracketed punctuation: two quote marks over rows of dots
            from fontTools.pens.recordingPen import replayRecording
            cur, boxes = [], []
            for op, args in r['rec']:
                cur.append((op, args))
                if op in ('closePath', 'endPath'):
                    bp = BoundsPen(None); replayRecording(cur, bp); boxes.append(bp.bounds); cur = []
            boxes = [b for b in boxes if (b[2] - b[0]) * (b[3] - b[1]) >= 12]
            boxes.sort(key=lambda b: b[1])
            quotes = sorted(boxes[:2], key=lambda b: b[0])
            for b, (ch, gname) in zip(quotes, (('\u2018', 'quoteleft'), ('\u2019', 'quoteright'))):
                place(ch, None, gname, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            for b in boxes[2:]:
                place('.', None, 'period', (b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            continue
        if '.alt' in name:
            bname, tag = feature_for(key, name)
            ch, gname = char_for(bname), name
        else:
            tag = None; ch = char_for(name); gname = cm.get(ord(ch)) if ch else None
        if not ch or gname is None:
            print('  skip', key, name); continue
        if ink(gname) is None:
            continue
        place(ch, tag, gname, (r['b'][0] + r['b'][2]) / 2, line=r['line_idx'])
    fsize = em_px * 100 / Wc
    # character set
    chars = [chr(c) for c in sorted(cm) if c > 0x20 and c != 0xA0 and not 0x300 <= c < 0x370]
    if FONTS[key]['unicase']:
        chars = [c for c in chars if not (c.isupper() and len(c.lower()) == 1 and c.lower() != c and ord(c.lower()) in cm)]
    alts = []
    for tag, label, mapping in FONTS[key]['sets']:
        for bname, alt in mapping.items():
            alts.append((char_for(bname), tag))
    woff2 = open(os.path.join(FONTDIR, ps + '-Regular.woff2'), 'rb').read()
    return dict(key=key, m=m, crop=crop, Wc=Wc, Hc=Hc, img=uri, img_bytes=nbytes, pil=im, codepoints=sorted(cm), spans=spans, fsize=fsize,
                chars=chars, alts=alts, ncp=len(cm), nglyphs=len(otf.getGlyphOrder()), woff2=woff2)


PKG_ROOT = paths.PACKAGE
PKG_FILES = []


def package_files():
    files = []
    for sub in ('fonts', 'css'):
        for dp, dn, fn in os.walk(os.path.join(PKG_ROOT, sub)):
            dn.sort()
            files += [os.path.relpath(os.path.join(dp, f), PKG_ROOT) for f in sorted(fn)]
    return files + ['README.md', 'OFL.txt', 'index.html']


def flyer_thumb():
    im = Image.open(paths.SCAN).convert('L').crop((0, 0, 803, 800))
    return jpeg_uri(im, q=80)


def esc(s):
    return html.escape(s, quote=True)


def face_section(d):
    key = d['key']; inf = INFO[key]; cfg = FONTS[key]; cls = 'f-' + key
    sheets = ''.join(f'<span class="sheet-code"><b>{c}</b> {pt} · {mm}</span>' for c, pt, mm in inf['sheets'])
    spans = ''.join(
        f'<span style="left:{l:.3f}cqw;top:{t:.3f}cqw"' + (f' data-f="{tag}"' if tag else '') + f'>{esc(ch)}</span>'
        for ch, tag, l, t in d['spans'])
    grid = ''.join(f'<span>{esc(c)}</span>' for c in d['chars'])
    alts = ''.join(f'<span data-f="{tag}">{esc(c)}</span>' for c, tag in d['alts'])
    unicase_note = (' Capitals share the lower-case forms in this face, so each letter appears once.'
                    if cfg['unicase'] else '')
    alt_block = (f'<p class="grid-label">Alternates, from the stylistic sets</p><div class="grid {cls}">{alts}</div>'
                 if alts else '')
    return f'''
<section class="face" id="{ANCHOR[key]}" aria-labelledby="{key}-name">
  <div class="wrap face-grid">
    <div class="face-text">
      <p class="eyebrow">{esc(inf['result'])}</p>
      <h2 class="face-name {cls}" id="{key}-name">{esc(cfg['family'])}</h2>
      <dl class="facts">
        <div><dt>Designer</dt><dd>{esc(inf['designer'])} <span class="dates">({inf['dates']})</span></dd></div>
        <div><dt>Letraset sheets</dt><dd class="sheets">{sheets}</dd></div>
        <div><dt>This font</dt><dd>{d['ncp']} characters · {esc(inf['traits'])}</dd></div>
      </dl>
      <p class="note">{esc(inf['note'])}</p>
    </div>
    <figure class="compare" data-mode="side">
      <div class="compare-bar">
        <span class="compare-title">Flyer and font</span>
        <div class="seg" role="group" aria-label="Comparison view for {esc(cfg['family'])}">
          <button type="button" data-mode="side" aria-pressed="true">Side by side</button>
          <button type="button" data-mode="overlay" aria-pressed="false">Overlay</button>
        </div>
      </div>
      <div class="stage">
        <div class="layer scan">
          <img src="{d['img']}" width="{d['Wc'] * 3}" height="{d['Hc'] * 3}"
               alt="{esc(cfg['family'])} as printed on the 1978 flyer">
          <span class="tag">1978 flyer</span>
        </div>
        <div class="layer digital">
          <div class="glyphs {cls}" style="aspect-ratio:{d['Wc']}/{d['Hc']};--fs:{d['fsize']:.3f}cqw" aria-hidden="true">{spans}</div>
          <span class="tag">Font</span>
        </div>
      </div>
      <figcaption>Each glyph of the font sits where its counterpart sits on the flyer, at the same size.
        In Overlay, the font is blue over the grey scan, and dark where the two agree.</figcaption>
    </figure>
  </div>
  <div class="wrap">
    <details class="charset">
      <summary>Character set</summary>
      <p class="grid-note">{d['ncp']} characters.{unicase_note}</p>
      <div class="grid {cls}">{grid}</div>
      {alt_block}
    </details>
  </div>
</section>'''


def tester_row(d):
    key = d['key']; inf = INFO[key]; cfg = FONTS[key]
    chips = ''.join(f'<button type="button" class="chip" data-feat="{t}" aria-pressed="false">{esc(l)}</button>'
                    for t, l in inf['chips'])
    return f'''
    <div class="row" data-face="{key}">
      <div class="row-meta">
        <a class="row-name" href="#{ANCHOR[key]}">{esc(cfg['family'])}</a>
        <span class="row-sub">{esc(inf['designer'])} · {esc(inf['result'].lower())}</span>
        {f'<div class="chips" role="group" aria-label="{esc(cfg["family"])} stylistic sets">{chips}</div>' if chips else ''}
      </div>
      <div class="row-text f-{key}" lang="ga">{esc(SAMPLE)}</div>
    </div>'''


def page(faces, flyer_uri):
    F = {d['key']: d for d in faces}
    fontface = ''.join(
        f'@font-face{{font-family:"{CSSNAME[k]}";src:url(data:font/woff2;base64,{b64(F[k]["woff2"])}) format("woff2");'
        f'font-weight:400;font-style:normal;font-display:block}}\n' for k in ORDER)
    metrics_js = ','.join(f'{k}:{{a:{F[k]["m"]["a"]:.4f},d:{F[k]["m"]["d"]:.4f},xh:{F[k]["m"]["xh"]:.4f}}}' for k in ORDER)
    c = F['ceili']['m']; lh = 1.1
    hero_bl = (lh - (c['a'] + c['d'])) / 2 + c['a']; hero_xl = hero_bl - c['xh']
    nav = ''.join(f'''
      <a class="index-item" href="#{ANCHOR[k]}">
        <span class="index-name f-{k}">{esc(FONTS[k]['family'])}</span>
        <span class="index-sub">{esc(INFO[k]['result'])} · {esc(INFO[k]['designer'])}</span>
      </a>''' for k in ORDER)
    rows = ''.join(tester_row(F[k]) for k in ORDER)
    sections = ''.join(face_section(F[k]) for k in ORDER)
    return f'''<title>Four Irish Typefaces</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
{fontface}
/* Layout: a drawing-board hero, then one specimen sheet per face. Each sheet sets the 1978 scan
   against the font placed glyph for glyph; testers rule baseline and x-height in non-repro blue. */
:root {{
  --paper: #f1f3f1;
  --surface: #fafbfa;
  --ink: #131615;
  --muted: #56605c;
  --rule: #d3d9d6;
  --nonrepro: #8ccfe7;
  --accent: #0b6a8f;
  --on-accent: #ffffff;
  --scan-paper: #f4f4f1;
  --scan-ink: #191a19;
  --overlay-ink: #00a6dd;
  --font-ui: "Archivo", "Helvetica Neue", Helvetica, Arial, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
  --font-ceili: "Ceili", Georgia, serif;
  --font-carrick: "Carrick", Georgia, serif;
  --font-kilfane: "Kilfane", Georgia, serif;
  --font-tuam: "Tuam Uncial", Georgia, serif;
  --gutter-l: max(16px, env(safe-area-inset-left, 0px));
  --gutter-r: max(16px, env(safe-area-inset-right, 0px));
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --paper: #0f1312; --surface: #161b1a; --ink: #e4e9e7; --muted: #9aa49f; --rule: #2a3230;
    --nonrepro: #2c718b; --accent: #7cc9ea; --on-accent: #052230; color-scheme: dark;
  }}
}}
:root[data-theme="dark"] {{
  --paper: #0f1312; --surface: #161b1a; --ink: #e4e9e7; --muted: #9aa49f; --rule: #2a3230;
  --nonrepro: #2c718b; --accent: #7cc9ea; --on-accent: #052230; color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
body {{ background: var(--paper); color: var(--ink); font-family: var(--font-ui); font-size: 16px;
  line-height: 1.55; font-stretch: 100%; -webkit-text-size-adjust: 100%; }}
.f-ceili {{ font-family: var(--font-ceili); }}
.f-carrick {{ font-family: var(--font-carrick); }}
.f-kilfane {{ font-family: var(--font-kilfane); }}
.f-tuam {{ font-family: var(--font-tuam); }}
.wrap {{ max-width: 1160px; margin-inline: auto; padding-left: var(--gutter-l); padding-right: var(--gutter-r); }}
a {{ color: var(--accent); text-underline-offset: 0.18em; }}
:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 3px; }}
h1, h2, h3 {{ text-wrap: balance; margin: 0; }}
p {{ margin: 0; }}
.eyebrow, .tag, .grid-label, dt, .compare-title, .row-sub, .index-sub, .sheet-code {{
  font-stretch: 87.5%; letter-spacing: 0.06em; text-transform: uppercase; font-size: 12px; font-weight: 600; }}
.eyebrow {{ color: var(--muted); }}

/* hero */
.hero {{ padding-block: 40px 28px; border-bottom: 1px solid var(--rule); }}
.hero-grid {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 32px; align-items: start; }}
.hero-text {{ padding-top: 4px; }}
.hero-text {{ display: grid; gap: 20px; min-width: 0; }}
.hero-head {{ display: grid; gap: 6px; margin-bottom: 24px; }}
.hero-title {{ font-family: var(--font-ceili); font-weight: 400; font-size: clamp(3.2rem, 7.8vw, 6.4rem);
  line-height: {lh}; letter-spacing: 0;
  background-image: linear-gradient(to bottom,
    transparent calc({hero_xl:.4f}em - 1px), var(--nonrepro) calc({hero_xl:.4f}em - 1px), var(--nonrepro) {hero_xl:.4f}em, transparent {hero_xl:.4f}em,
    transparent {hero_bl:.4f}em, var(--nonrepro) {hero_bl:.4f}em, var(--nonrepro) calc({hero_bl:.4f}em + 1px), transparent calc({hero_bl:.4f}em + 1px));
  background-size: 100% {lh}em; }}
.lede {{ font-size: 1.125rem; max-width: 36em; }}
.actions {{ display: grid; gap: 10px; justify-items: start; }}
.dl {{ display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; }}
.btn {{ font: inherit; font-weight: 600; font-size: 15px; border-radius: 6px; padding: 10px 16px; cursor: pointer;
  border: 1px solid var(--accent); background: var(--accent); color: var(--on-accent); }}
.btn.secondary {{ background: transparent; color: var(--accent); }}
.btn:hover {{ filter: brightness(1.08); }}
.btn:disabled {{ opacity: 0.6; cursor: progress; }}
.dl-size {{ color: var(--muted); font-size: 14px; }}
.status {{ color: var(--muted); font-size: 14px; min-height: 1.4em; }}
.flyer {{ margin: 0; display: grid; gap: 8px; justify-self: center; max-width: 440px; width: 100%; }}
.flyer img {{ display: block; width: 100%; height: auto; border: 1px solid var(--rule); background: var(--scan-paper); }}
.flyer figcaption {{ color: var(--muted); font-size: 13px; }}
.index {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 20px; margin-top: 32px; }}
.index-item {{ display: grid; grid-template-rows: 1fr auto; gap: 4px; padding-block: 12px; border-top: 1px solid var(--rule);
  color: var(--ink); text-decoration: none; min-width: 0; }}
.index-item:hover .index-name {{ color: var(--accent); }}
.index-name {{ font-size: clamp(1.45rem, 2.2vw, 1.75rem); line-height: 1.15; align-self: start; }}
.index-sub {{ color: var(--muted); font-size: 11px; }}
@media (min-width: 900px) {{ .hero-grid {{ grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr); gap: 48px; }} }}
@media (min-width: 1100px) {{ .index {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }} }}

/* sections */
.block {{ padding-block: 40px; border-bottom: 1px solid var(--rule); }}
.block-head {{ display: grid; gap: 8px; margin-bottom: 20px; max-width: 46em; }}
.block-head h2 {{ font-size: 1.75rem; font-weight: 700; font-stretch: 95%; line-height: 1.2; }}
.block-head p {{ color: var(--muted); }}

/* tester */
.controls {{ display: flex; flex-wrap: wrap; gap: 12px 24px; align-items: center; margin-bottom: 8px; }}
.controls input[type=text] {{ font: inherit; font-size: 17px; flex: 1 1 320px; min-width: 0; padding: 10px 12px;
  border: 1px solid var(--rule); border-radius: 6px; background: var(--surface); color: var(--ink); }}
.controls label {{ display: inline-flex; align-items: center; gap: 8px; font-size: 14px; color: var(--muted); }}
.controls input[type=range] {{ width: 160px; accent-color: var(--accent); }}
.controls input[type=checkbox] {{ accent-color: var(--accent); width: 16px; height: 16px; }}
.controls output {{ font-variant-numeric: tabular-nums; min-width: 3ch; color: var(--ink); }}
.rows {{ display: grid; }}
.row {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 6px 24px; padding-block: 16px 18px;
  border-top: 1px solid var(--rule); }}
.row-meta {{ display: grid; gap: 4px; align-content: start; }}
.row-name {{ font-weight: 700; font-size: 16px; color: var(--ink); text-decoration: none; }}
.row-name:hover {{ color: var(--accent); }}
.row-sub {{ color: var(--muted); font-size: 11px; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }}
.chip {{ font: inherit; font-size: 13px; padding: 4px 10px; border-radius: 999px; cursor: pointer;
  border: 1px solid var(--rule); background: transparent; color: var(--ink); }}
.chip[aria-pressed="true"] {{ background: var(--accent); border-color: var(--accent); color: var(--on-accent); }}
.row-text {{ font-size: 56px; line-height: 1.3; overflow-wrap: anywhere; min-width: 0; background-repeat: repeat-y; }}
@media (min-width: 760px) {{ .row {{ grid-template-columns: 190px minmax(0, 1fr); }} }}

/* face sections */
.face {{ padding-block: 48px 36px; border-bottom: 1px solid var(--rule); }}
.face-grid {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 28px; align-items: start; }}
.face-text {{ display: grid; gap: 16px; min-width: 0; }}
.face-name {{ font-weight: 400; font-size: clamp(3rem, 7vw, 5.4rem); line-height: 1.05; }}
.facts {{ display: grid; gap: 10px; margin: 0; }}
.facts div {{ display: grid; gap: 2px; }}
dt {{ color: var(--muted); font-size: 11px; }}
dd {{ margin: 0; }}
.dates {{ color: var(--muted); }}
.sheets {{ display: flex; flex-wrap: wrap; gap: 4px 16px; }}
.sheet-code {{ font-size: 13px; font-weight: 500; letter-spacing: 0.03em; text-transform: none; font-variant-numeric: tabular-nums; }}
.sheet-code b {{ font-weight: 700; }}
.note {{ max-width: 34em; }}
.compare {{ margin: 0; display: grid; gap: 10px; min-width: 0; }}
.compare-bar {{ display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; }}
.compare-title {{ color: var(--muted); }}
.seg {{ display: inline-flex; border: 1px solid var(--rule); border-radius: 6px; overflow: hidden; }}
.seg button {{ font: inherit; font-size: 13px; padding: 5px 12px; border: 0; background: transparent; color: var(--ink); cursor: pointer; }}
.seg button + button {{ border-left: 1px solid var(--rule); }}
.seg button[aria-pressed="true"] {{ background: var(--accent); color: var(--on-accent); }}
.stage {{ display: grid; gap: 8px; }}
.layer {{ position: relative; background: var(--scan-paper); border: 1px solid var(--rule); min-width: 0; }}
.layer img {{ display: block; width: 100%; height: auto; }}
.glyphs {{ position: relative; width: 100%; container-type: inline-size; overflow: hidden; }}
.glyphs span {{ position: absolute; font-size: var(--fs); line-height: 1; white-space: pre; color: var(--scan-ink); }}
.glyphs span[data-f="ss01"] {{ font-feature-settings: "ss01" 1; }}
.glyphs span[data-f="ss02"] {{ font-feature-settings: "ss02" 1; }}
.glyphs span[data-f="ss03"] {{ font-feature-settings: "ss03" 1; }}
.tag {{ position: absolute; top: 6px; right: 8px; font-size: 10px; color: #5e6461; background: var(--scan-paper);
  padding: 1px 5px; border-radius: 3px; }}
.compare[data-mode="overlay"] .stage > .layer {{ grid-area: 1 / 1; }}
.compare[data-mode="overlay"] .digital {{ background: transparent; border-color: transparent; mix-blend-mode: multiply; }}
.compare[data-mode="overlay"] .glyphs span {{ color: var(--overlay-ink); }}
.compare[data-mode="overlay"] .tag {{ display: none; }}
.compare figcaption {{ color: var(--muted); font-size: 13px; max-width: 40em; }}
@media (min-width: 960px) {{ .face-grid {{ grid-template-columns: minmax(0, 5fr) minmax(0, 7fr); gap: 48px; }} }}
.charset {{ margin-top: 28px; }}
.charset summary {{ cursor: pointer; font-weight: 600; font-size: 15px; color: var(--accent); width: fit-content; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(46px, 1fr)); gap: 1px; margin-top: 14px;
  background: var(--rule); border: 1px solid var(--rule); font-size: 28px; line-height: 1; }}
.grid span {{ display: flex; align-items: center; justify-content: center; height: 56px; background: var(--surface); }}
.grid span[data-f="ss01"] {{ font-feature-settings: "ss01" 1; }}
.grid span[data-f="ss02"] {{ font-feature-settings: "ss02" 1; }}
.grid span[data-f="ss03"] {{ font-feature-settings: "ss03" 1; }}
.grid-label {{ color: var(--muted); margin-top: 18px; }}
.grid-note {{ color: var(--muted); font-size: 14px; margin-top: 10px; }}

/* web use + making */
.code {{ position: relative; background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; }}
.code pre {{ margin: 0; padding: 16px; overflow-x: auto; font-family: var(--font-mono); font-size: 13.5px; line-height: 1.6; }}
.copy {{ position: absolute; top: 8px; right: 8px; font: inherit; font-size: 13px; padding: 4px 10px; border-radius: 5px;
  border: 1px solid var(--rule); background: var(--paper); color: var(--ink); cursor: pointer; }}
.two {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 28px; }}
@media (min-width: 900px) {{ .two {{ grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 48px; }} }}
.prose {{ display: grid; gap: 12px; max-width: 36em; }}
.prose h3 {{ font-size: 1.05rem; font-weight: 700; margin-top: 8px; }}
.steps {{ margin: 0; padding-left: 1.3em; display: grid; gap: 8px; }}
.table-wrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 15px; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: left; padding: 8px 12px 8px 0; border-bottom: 1px solid var(--rule); vertical-align: top; }}
th {{ font-size: 12px; font-stretch: 87.5%; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); font-weight: 600; }}
.sources {{ margin: 0; padding-left: 1.2em; display: grid; gap: 4px; }}
.fine {{ color: var(--muted); font-size: 14px; }}
footer {{ padding-block: 28px 48px; color: var(--muted); font-size: 14px; }}
footer p + p {{ margin-top: 8px; }}
@media (prefers-reduced-motion: no-preference) {{ html {{ scroll-behavior: smooth; }} }}
</style>

<header class="hero">
  <div class="wrap hero-head">
    <p class="eyebrow">Irish typeface competition · 1978</p>
    <h1 class="hero-title">four irish typefaces</h1>
  </div>
  <div class="wrap hero-grid">
    <div class="hero-text">
      <p class="lede">Céilí, Carrick, Kilfane and Tuam Uncial won the 1978 competition to design an Irish typeface and
        were sold as Letraset dry-transfer lettering. Here they are as fonts for the web and the desktop, traced from the
        competition flyer and completed to about 400 characters each.</p>
      <div class="actions">
        <div class="dl">
          <button type="button" class="btn" data-action="fonts">Download the fonts</button>
          <span class="dl-size">ZIP · about 0.7 MB · WOFF2, WOFF, OTF, TTF, CSS, README and the OFL</span>
        </div>
        <div class="dl">
          <button type="button" class="btn secondary" data-action="pdf">Specimen PDF</button>
          <span class="dl-size">9 pages · 0.9 MB</span>
        </div>
        <p class="status" id="dl-status" role="status" aria-live="polite"></p>
      </div>
    </div>
    <figure class="flyer">
      <img src="{flyer_uri}" width="803" height="800"
           alt="The 1978 Four Irish Typefaces flyer, showing the alphabets of Kilfane, Tuam Uncial, Carrick and Céilí">
      <figcaption>The source: the competition flyer, scanned at about 97 dpi.</figcaption>
    </figure>
  </div>
  <nav class="wrap index" aria-label="The four typefaces">{nav}
  </nav>
</header>

<main>
  <section class="block" id="try" aria-labelledby="try-h">
    <div class="wrap">
      <div class="block-head">
        <h2 id="try-h">Try them</h2>
        <p>Type anything. Irish accents, the lenition dots (ḃ ċ ḋ ḟ ġ ṁ ṗ ṡ ṫ) and the Tironian et (⁊) are all there.
          The blue lines mark the baseline and x-height, as on a drawing board.</p>
      </div>
      <div class="controls">
        <input id="tester-text" type="text" value="{esc(SAMPLE)}" aria-label="Sample text" spellcheck="false" autocomplete="off">
        <label for="tester-size">Size <input id="tester-size" type="range" min="20" max="140" value="56"><output id="tester-size-out" for="tester-size">56</output></label>
        <label for="tester-guides"><input id="tester-guides" type="checkbox" checked> Guidelines</label>
      </div>
      <div class="rows">{rows}
      </div>
    </div>
  </section>
{sections}
  <section class="block" id="web" aria-labelledby="web-h">
    <div class="wrap two">
      <div class="prose">
        <div class="block-head">
          <h2 id="web-h">Use them on a website</h2>
        </div>
        <p>Unzip the fonts next to your pages and link the stylesheet. It declares all four faces with WOFF2 and WOFF
          sources and <code>font-display: swap</code>. Céilí is declared as both “Céilí” and “Ceili”.</p>
        <p>The OTF and TTF files in the same ZIP install on Mac, Windows and Linux for Word, InDesign, Affinity or
          Figma. Stylistic sets appear wherever the app lists OpenType features.</p>
      </div>
      <div class="code">
        <button type="button" class="copy" id="copy-css">Copy</button>
<pre id="css-snippet">&lt;link rel="stylesheet" href="css/four-irish-typefaces.css"&gt;

&lt;style&gt;
  h1    {{ font-family: "Céilí Digital", "Ceili Digital", serif; }}
  .sign {{ font-family: "Carrick Digital", serif; }}
&lt;/style&gt;

&lt;!-- ready-made classes, including the stylistic sets --&gt;
&lt;h2 class="tuam-uncial"&gt;Fáilte go Tuaim&lt;/h2&gt;
&lt;p class="kilfane kilfane-roman-forms"&gt;Banc Ceannais na hÉireann&lt;/p&gt;
&lt;p class="ceili ceili-insular-r-s"&gt;Ceol agus craic&lt;/p&gt;</pre>
      </div>
    </div>
  </section>

  <section class="block" id="making" aria-labelledby="making-h">
    <div class="wrap two">
      <div class="prose">
        <div class="block-head">
          <h2 id="making-h">How they were made</h2>
        </div>
        <ol class="steps">
          <li>Each letter was cut out of the flyer scan, where it stands only 20 to 35 pixels tall. Letters that touched
            were separated along measured cut lines.</li>
          <li>The edge of each letter was traced at sub-pixel precision, then redrawn the way a type designer redraws
            from a scan. Stems and bars became true straight lines, curves were drawn with as few points as possible,
            and corners and serifs were kept sharp. A smoothing spline removed the photocopy's ripples without
            shrinking curves.</li>
          <li>The flyer shows each face at two or three sizes. Comparing stem widths across sizes measured how much the
            photocopy fattened the letters, and that spread was taken back out.</li>
          <li>Damage on the flyer was repaired: a toner speck on Kilfane’s O was erased, and Céilí’s broken h was
            rebuilt from its own stem and the shoulder of its n.</li>
          <li>Accents, punctuation, symbols and letters such as æ, ð, þ, ß and ⁊ were drawn to match each face, then the
            fonts were spaced, kerned and checked with Font Bakery and the OpenType Sanitizer used by browsers.</li>
        </ol>
        <p class="fine">The traced letters are the designers’ own. Everything not on the flyer is a careful
          reconstruction, so treat accents and symbols as informed guesses.</p>
      </div>
      <div class="prose">
        <h3>Checked against the large samples</h3>
        <p>The flyer’s 48 and 60 pt samples were not used for tracing, so they make an independent check of weight and
          shape.</p>
        <div class="table-wrap">
          <table>
            <thead><tr><th scope="col">Face</th><th scope="col">Stem width vs sample</th><th scope="col">Shape overlap</th></tr></thead>
            <tbody>
              <tr><td>Céilí</td><td>−7% (0.4 px)</td><td>0.81–0.87</td></tr>
              <tr><td>Carrick</td><td>+2%</td><td>0.88–0.93</td></tr>
              <tr><td>Kilfane</td><td>−1%</td><td>0.83–0.91</td></tr>
              <tr><td>Tuam Uncial</td><td>+2%</td><td>0.94–0.95</td></tr>
            </tbody>
          </table>
        </div>
        <p class="fine">Shape overlap is intersection over union of the filled letter shapes, where 1.0 is identical.</p>
        <h3>A sharper source would help</h3>
        <p>A 600 to 1200 dpi rescan of the flyer, or scans of the Letraset sheets or Curran’s drawings at the National
          Irish Visual Arts Library, would sharpen every outline. The tracing and build scripts can be rerun on a new
          scan.</p>
      </div>
    </div>
  </section>

  <section class="block" id="history" aria-labelledby="history-h">
    <div class="wrap two">
      <div class="prose">
        <div class="block-head">
          <h2 id="history-h">The competition</h2>
        </div>
        <p>Letraset, Kilkenny Design Workshops and D. O’Sullivan Graphic Supplies of 66 Lower Camden Street, Dublin,
          sponsored a competition for a new Irish typeface. The competition brochure lists the awards: Hermann Hecht’s
          Céilí took first prize (£250 and a silver medallion), William Curran’s Carrick was Highly Commended (£50), and
          Curran’s Kilfane and Jarlath Hayes’s Tuam Uncial were each Commended (£25).</p>
        <p>Each winner was issued as two Letraset sheets, numbered S53909 to S53916. The flyer gives each sheet’s size in
          points and in millimetres of letter height. As far as this research found, Céilí, Carrick and Kilfane have
          never been digitised before.</p>
        <p class="fine">This history was gathered from search results and has not been checked against the original
          documents. Please verify it before citing it.</p>
      </div>
      <div class="prose">
        <h3>Sources</h3>
        <ul class="sources">
          <li><a href="https://fontsinuse.com/typefaces/205971/ceili" target="_blank" rel="noopener">Fonts In Use: Céilí</a></li>
          <li><a href="https://fontsinuse.com/typefaces/248202/carrick" target="_blank" rel="noopener">Fonts In Use: Carrick</a></li>
          <li><a href="https://fontsinuse.com/typefaces/248201/kilfane" target="_blank" rel="noopener">Fonts In Use: Kilfane</a></li>
          <li><a href="https://fontsinuse.com/typefaces/248203/tuam-uncial" target="_blank" rel="noopener">Fonts In Use: Tuam Uncial</a></li>
          <li><a href="https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/45/" target="_blank" rel="noopener">NIVAL: the competition brochure</a></li>
          <li><a href="https://www.nival.ie/william-curran-archive/" target="_blank" rel="noopener">NIVAL: William Curran archive</a></li>
          <li><a href="https://dublininquirer.com/2020/06/24/after-almost-50-years-a-renowned-irish-font-is-brought-into-the-digital-age" target="_blank" rel="noopener">Dublin Inquirer (2020) on the Tuam revival</a></li>
          <li><a href="https://www.irishtimes.com/news/master-typographer-and-designer-1.313378" target="_blank" rel="noopener">Irish Times obituary of Jarlath Hayes</a></li>
          <li><a href="https://signalfoundry.com/typefaces/jarlath" target="_blank" rel="noopener">Signal Type Foundry: Jarlath</a></li>
          <li><a href="https://atypi.org/presentation/retyping-europe/" target="_blank" rel="noopener">ATypI: Transnational heritage and alternative futures</a></li>
          <li><a href="https://catalogue.nli.ie/Record/vtls000883198" target="_blank" rel="noopener">Dermot McGuinne, Irish Type Design (2nd ed., 2010)</a></li>
        </ul>
      </div>
    </div>
  </section>
</main>

<footer>
  <div class="wrap">
    <p>Typeface designs by Hermann Hecht, William Curran and Jarlath Hayes, 1978. Digitised in 2026 from the printed
      flyer. Version 1.100.</p>
    <p>Fonts copyright 2026 Dan Drayne, released under the SIL Open Font License 1.1: use them for anything, share and
      adapt them, but don’t sell the fonts on their own. The licence is in the download.</p>
    <p>Jarlath, Signal Type Foundry’s revival of Tuam Uncial, is a separate commercial product and is not part of this
      project.</p>
  </div>
</footer>

<script>
(() => {{
  const M = {{{metrics_js}}};
  const SAMPLE = {SAMPLE!r};
  const text = document.getElementById('tester-text');
  const size = document.getElementById('tester-size');
  const out = document.getElementById('tester-size-out');
  const guides = document.getElementById('tester-guides');
  const rows = [...document.querySelectorAll('.row')];

  function paint(row) {{
    const m = M[row.dataset.face];
    const el = row.querySelector('.row-text');
    const px = Number(size.value);
    const lh = Math.round(px * 1.3);
    const bl = Math.round((lh - (m.a + m.d) * px) / 2 + m.a * px);
    const xl = Math.round(bl - m.xh * px);
    el.style.fontSize = px + 'px';
    el.style.lineHeight = lh + 'px';
    el.style.backgroundSize = '100% ' + lh + 'px';
    el.style.backgroundImage = guides.checked
      ? `linear-gradient(to bottom, transparent ${{xl - 1}}px, var(--nonrepro) ${{xl - 1}}px, var(--nonrepro) ${{xl}}px, transparent ${{xl}}px, transparent ${{bl}}px, var(--nonrepro) ${{bl}}px, var(--nonrepro) ${{bl + 1}}px, transparent ${{bl + 1}}px)`
      : 'none';
    const on = [...row.querySelectorAll('.chip')].map(c => `"${{c.dataset.feat}}" ${{c.getAttribute('aria-pressed') === 'true' ? 1 : 0}}`);
    el.style.fontFeatureSettings = on.length ? on.join(', ') : 'normal';
  }}
  function update() {{
    const t = text.value.trim() ? text.value : SAMPLE;
    out.value = size.value;
    rows.forEach(r => {{ r.querySelector('.row-text').textContent = t; paint(r); }});
  }}
  text.addEventListener('input', update);
  size.addEventListener('input', update);
  guides.addEventListener('change', update);
  rows.forEach(r => r.querySelectorAll('.chip').forEach(c => c.addEventListener('click', () => {{
    c.setAttribute('aria-pressed', c.getAttribute('aria-pressed') === 'true' ? 'false' : 'true');
    paint(r);
  }})));
  if (window.matchMedia('(max-width: 600px)').matches) size.value = 36;
  update();

  document.querySelectorAll('.compare').forEach(fig => {{
    fig.querySelectorAll('.seg button').forEach(b => b.addEventListener('click', () => {{
      fig.dataset.mode = b.dataset.mode;
      fig.querySelectorAll('.seg button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    }}));
  }});

  const copy = document.getElementById('copy-css');
  const snippet = document.getElementById('css-snippet');
  copy.addEventListener('click', () => {{
    const done = msg => {{ copy.textContent = msg; setTimeout(() => {{ copy.textContent = 'Copy'; }}, 1600); }};
    const select = () => {{
      const r = document.createRange(); r.selectNodeContents(snippet);
      const s = getSelection(); s.removeAllRanges(); s.addRange(r); done('Selected');
    }};
    try {{
      navigator.clipboard.writeText(snippet.textContent).then(() => done('Copied'), select);
    }} catch (e) {{ select(); }}
  }});

  const status = document.getElementById('dl-status');
  const buttons = [...document.querySelectorAll('[data-action]')];
  const PKG = __PKG__;
  const ready = (window.claude && typeof window.claude.use === 'function')
    ? window.claude.use('downloads').catch(() => null) : Promise.resolve(null);
  const unavailable = msg => {{
    buttons.forEach(b => {{ b.closest('.dl').hidden = true; }});
    status.textContent = msg;
  }};
  ready.then(dl => {{ if (!dl) unavailable('Downloading isn’t available in this view of the page.'); }});

  const CRC = new Uint32Array(256).map((_, n) => {{
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  }});
  const crc32 = u8 => {{
    let c = 0xFFFFFFFF;
    for (let i = 0; i < u8.length; i++) c = CRC[(c ^ u8[i]) & 0xFF] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }};
  async function deflate(u8) {{
    if (typeof CompressionStream !== 'function') return null;
    try {{
      const stream = new Blob([u8]).stream().pipeThrough(new CompressionStream('deflate-raw'));
      return new Uint8Array(await new Response(stream).arrayBuffer());
    }} catch (e) {{ return null; }}
  }}
  async function makeZip(entries) {{
    const enc = new TextEncoder(), parts = [], central = [];
    const time = 12 << 11, date = ((2026 - 1980) << 9) | (10 << 5) | 18;
    let offset = 0;
    for (const e of entries) {{
      const name = enc.encode(e.name), crc = crc32(e.data), packed = await deflate(e.data);
      const useDeflate = packed && packed.length < e.data.length;
      const body = useDeflate ? packed : e.data, method = useDeflate ? 8 : 0;
      const h = new DataView(new ArrayBuffer(30));
      h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true);
      h.setUint16(8, method, true); h.setUint16(10, time, true); h.setUint16(12, date, true);
      h.setUint32(14, crc, true); h.setUint32(18, body.length, true); h.setUint32(22, e.data.length, true);
      h.setUint16(26, name.length, true);
      parts.push(new Uint8Array(h.buffer), name, body);
      const c = new DataView(new ArrayBuffer(46));
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true);
      c.setUint16(8, 0x0800, true); c.setUint16(10, method, true); c.setUint16(12, time, true);
      c.setUint16(14, date, true); c.setUint32(16, crc, true); c.setUint32(20, body.length, true);
      c.setUint32(24, e.data.length, true); c.setUint16(28, name.length, true); c.setUint32(42, offset, true);
      central.push(new Uint8Array(c.buffer), name);
      offset += 30 + name.length + body.length;
    }}
    const cd = central.reduce((n, p) => n + p.length, 0);
    const end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, entries.length, true);
    end.setUint16(10, entries.length, true); end.setUint32(12, cd, true); end.setUint32(16, offset, true);
    return new Blob([...parts, ...central, new Uint8Array(end.buffer)]);
  }}
  async function fetchBytes(path) {{
    const res = await fetch(path);
    if (!res.ok) throw {{ code: 'fetch_failed' }};
    return new Uint8Array(await res.arrayBuffer());
  }}
  async function build(action) {{
    if (action === 'pdf') {{
      return {{ filename: 'Four-Irish-Typefaces-specimen.pdf',
               data: new Blob([await fetchBytes('package/specimen/Four-Irish-Typefaces-specimen.pdf')]) }};
    }}
    const entries = [];
    for (const p of PKG) entries.push({{ name: 'four-irish-typefaces/' + p, data: await fetchBytes('package/' + p) }});
    return {{ filename: 'four-irish-typefaces-fonts-v1.0.zip', data: await makeZip(entries) }};
  }}
  buttons.forEach(btn => btn.addEventListener('click', async () => {{
    const dl = await ready;
    if (!dl) return;
    buttons.forEach(b => {{ b.disabled = true; }});
    status.textContent = btn.dataset.action === 'pdf' ? 'Preparing the PDF…' : 'Packing the fonts…';
    try {{
      const file = await build(btn.dataset.action);
      status.textContent = '';
      const r = await dl.save(file);
      status.textContent = r && r.status === 'saved' ? 'Saved ' + file.filename + '.' : '';
    }} catch (e) {{
      const code = e && e.code;
      if (code === 'declined') status.textContent = '';
      else if (code === 'rate_limited') status.textContent = 'Another download is waiting for an answer. Try again in a moment.';
      else if (code === 'fetch_failed') status.textContent = 'The files couldn’t be loaded. Reload the page and try again.';
      else if (code === 'rejected_extension' || code === 'extension_not_enabled') status.textContent = 'This view of the page can’t save that type of file.';
      else if (code === 'too_large') status.textContent = 'That file is too large to save here.';
      else unavailable('Downloading isn’t available in this view of the page.');
    }} finally {{
      buttons.forEach(b => {{ b.disabled = false; }});
    }}
  }}));
}})();
</script>
'''.replace('__PKG__', json.dumps(PKG_FILES))


if __name__ == '__main__':
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True)
    faces = [face_data(k) for k in ORDER]
    for d in faces:
        print(d['key'], 'crop', d['crop'], f"{d['Wc']}x{d['Hc']}", 'img', d['img_bytes'], 'spans', len(d['spans']),
              'fs', round(d['fsize'], 3), 'chars', len(d['chars']))
    flyer_uri, n = flyer_thumb(); print('flyer', n)
    PKG_FILES = package_files()
    out = os.path.join(outdir, 'four-irish-typefaces.html')
    open(out, 'w').write(page(faces, flyer_uri))
    print('wrote', out, os.path.getsize(out))
    served = {f'package/{p}': os.path.join(PKG_ROOT, p) for p in PKG_FILES}
    served['package/specimen/Four-Irish-Typefaces-specimen.pdf'] = os.path.join(PKG_ROOT, 'specimen/Four-Irish-Typefaces-specimen.pdf')
    json.dump(served, open(os.path.join(outdir, 'files.json'), 'w'), indent=1)
    print(len(served), 'supporting files', round(sum(os.path.getsize(v) for v in served.values()) / 1e6, 2), 'MB')
