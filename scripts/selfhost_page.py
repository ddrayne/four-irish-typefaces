"""Build the self-hosted web test page as a Drayne app folder (Dockerfile + nginx + site/).

The page loads the fonts the way any website would: WOFF2 with a WOFF fallback through
@font-face, from this site, with CORS so other sites can link the same stylesheet.
It checks in the visitor's browser that each font loaded and which format was used,
and flags characters in the test text that a face doesn't have.
"""
import paths
import html, io, json, os, re, shutil, sys
from PIL import Image, ImageDraw, ImageFont
from build2 import FONTS, VERSION
import artifact_page as A

PKG = paths.PACKAGE
ZIPS = paths.DIST
SLUG = 'irish-typefaces'
TITLE = 'Four Irish Typefaces'
DESCRIPTION = ('Céilí, Carrick, Kilfane and Tuam Uncial, winners of a 1978 Irish typeface competition, '
               'revived as web fonts. Try them in your browser and download them.')
V = VERSION
FAMILY = {'ceili': 'Céilí', 'carrick': 'Carrick', 'kilfane': 'Kilfane', 'tuam': 'Tuam Uncial'}
STACK = {k: f'"{FAMILY[k]}"' + (', "Ceili"' if k == 'ceili' else '') + ', Georgia, serif' for k in FAMILY}
PRESETS = [
    ('ga', 'Irish', 'Is fearr Gaeilge bhriste ná Béarla cliste'),
    ('ga', 'Irish, traditional dots', 'Scríoḃaḋ Leaḃar Ċeanannais timpeall na bliana 800.'),
    ('gd', 'Scottish Gaelic', 'Ciamar a tha thu? Tha gu math, tapadh leibh.'),
    ('gv', 'Manx', 'Moghrey mie! Kys t’ou? Ta mee braew, gura mie ayd.'),
    ('cy', 'Welsh', 'Parciais fy jac codi baw hud llawn dŵr ger tŷ Mabon.'),
    ('br', 'Breton', 'Demat! Penaos emañ kont ganeoc’h?'),
    ('kw', 'Cornish', 'Myttin da! Fatla genes?'),
    ('en', 'English', 'Sphinx of black quartz, judge my vow.'),
    ('en', 'Figures and signs', '1978 · £4.50 · €12 · 7 · 10% · 1–2 · “quoted” ‘text’ «and» so on…'),
    ('ga', 'Insular letters', 'ḃ ċ ḋ ḟ ġ ṁ ṗ ṡ ṫ ⁊ ꝺ ꝼ ᵹ ꞃ ꞅ ꞇ'),
]
esc = A.esc


def kb(path):
    return f'{os.path.getsize(path) / 1024:.0f} KB' if os.path.getsize(path) < 1e6 else f'{os.path.getsize(path) / 1e6:.1f} MB'


def write_css(dest):
    """The package stylesheet, with ?v= on every font URL so a new release is never served stale."""
    css = open(os.path.join(PKG, 'css/four-irish-typefaces.css')).read()
    css = re.sub(r'\.(woff2?)"\)', lambda m: f'.{m.group(1)}?v={V}")', css)
    css = re.sub(r'version \d\.\d{3}', f'version {V}', css)
    open(dest, 'w').write(css)
    return css


def icon(size, path):
    """App icon: Céilí's a, white on the page accent."""
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill=(11, 106, 143, 255))
    font = ImageFont.truetype(os.path.join(PKG, 'fonts/ttf/CeiliDigital-Regular.ttf'), int(size * 0.92))
    l, t, r, b = d.textbbox((0, 0), 'a', font=font)
    d.text(((size - (r - l)) / 2 - l, (size - (b - t)) / 2 - t), 'a', font=font, fill=(255, 255, 255, 255))
    im.save(path)


def face_section(d):
    key = d['key']; inf = A.INFO[key]; cfg = FONTS[key]; cls = 'f-' + key
    sheets = ''.join(f'<span class="sheet-code"><b>{c}</b> {pt} · {mm}</span>' for c, pt, mm in inf['sheets'])
    spans = ''.join(
        f'<span style="left:{l:.3f}cqw;top:{t:.3f}cqw"' + (f' data-f="{tag}"' if tag else '') + f'>{esc(ch)}</span>'
        for ch, tag, l, t in d['spans'])
    grid = ''.join(f'<span>{esc(c)}</span>' for c in d['chars'])
    alts = ''.join(f'<span data-f="{tag}">{esc(c)}</span>' for c, tag in d['alts'])
    unicase_note = (' Capitals share the lower-case forms in this face, so each letter appears once.' if cfg['unicase'] else '')
    alt_block = (f'<p class="grid-label">Alternates, from the stylistic sets</p><div class="grid {cls}">{alts}</div>' if alts else '')
    return f'''
<section class="face" id="{key}" aria-labelledby="{key}-name">
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
          <img src="img/{key}-scan.jpg" width="{d['Wc'] * 3}" height="{d['Hc'] * 3}" loading="lazy" decoding="async"
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
    key = d['key']; inf = A.INFO[key]; cfg = FONTS[key]
    chips = ''.join(f'<button type="button" class="chip" data-feat="{t}" aria-pressed="false">{esc(l)}</button>'
                    for t, l in inf['chips'])
    return f'''
    <div class="row" data-face="{key}">
      <div class="row-meta">
        <a class="row-name" href="#{key}">{esc(cfg['family'])}</a>
        <span class="row-sub">{esc(inf['designer'])} · {esc(inf['result'].lower())}</span>
        {f'<div class="chips" role="group" aria-label="{esc(cfg["family"])} stylistic sets">{chips}</div>' if chips else ''}
        <span class="coverage" aria-live="polite"></span>
      </div>
      <div class="row-text f-{key}" lang="ga">{esc(PRESETS[0][2])}</div>
    </div>'''


def page(faces, sizes):
    F = {d['key']: d for d in faces}
    order = A.ORDER
    c = F['ceili']['m']; lh = 1.1
    hero_bl = (lh - (c['a'] + c['d'])) / 2 + c['a']; hero_xl = hero_bl - c['xh']
    metrics_js = json.dumps({k: dict(a=round(F[k]['m']['a'], 4), d=round(F[k]['m']['d'], 4), xh=round(F[k]['m']['xh'], 4)) for k in order})
    cover_js = json.dumps({k: F[k]['codepoints'] for k in order}, separators=(',', ':'))
    files_js = json.dumps({k: FONTS[k]['ps'] for k in order})
    fam_js = json.dumps(FAMILY, ensure_ascii=False)
    presets = ''.join(f'<option value="{i}" data-lang="{lg}">{esc(lab)}</option>' for i, (lg, lab, _) in enumerate(PRESETS))
    presets_js = json.dumps([dict(lang=lg, text=t) for lg, _, t in PRESETS], ensure_ascii=False)
    nav = ''.join(f'''
      <a class="index-item" href="#{k}">
        <span class="index-name f-{k}">{esc(FONTS[k]['family'])}</span>
        <span class="index-sub">{esc(A.INFO[k]['result'])} · {esc(A.INFO[k]['designer'])}</span>
      </a>''' for k in order)
    rows = ''.join(tester_row(F[k]) for k in order)
    sections = ''.join(face_section(F[k]) for k in order)
    checks = ''.join(f'''
          <tr data-face="{k}"><th scope="row" class="f-{k} check-name">{esc(FAMILY[k])}</th>
            <td class="st">Checking…</td><td class="fmt">–</td><td class="size">–</td></tr>''' for k in order)
    font_list = ''.join(f'<li><code>"{FONTS[k]["family"]}"</code>' + (' or <code>"Ceili Digital"</code>' if k == 'ceili' else '') + '</li>' for k in order)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{TITLE}</title>
<meta name="description" content="{esc(DESCRIPTION)}">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{esc(DESCRIPTION)}">
<meta property="og:type" content="website">
<meta property="og:image" content="img/social.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f1f3f1" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0f1312" media="(prefers-color-scheme: dark)">
<link rel="icon" type="image/png" sizes="64x64" href="img/icon-64.png">
<link rel="apple-touch-icon" href="img/icon-180.png">
<link rel="preload" href="fonts/woff2/CeiliDigital-Regular.woff2?v={V}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="css/four-irish-typefaces.css?v={V}">
<style>
/* Layout: a drawing-board hero, then one specimen sheet per face. Each sheet sets the 1978 scan
   against the font placed glyph for glyph; testers rule baseline and x-height in non-repro blue. */
:root {{
  --paper: #f1f3f1; --surface: #fafbfa; --ink: #131615; --muted: #56605c; --rule: #d3d9d6;
  --nonrepro: #8ccfe7; --accent: #0b6a8f; --on-accent: #ffffff; --ok: #2d6a3f; --warn: #8a5300;
  --scan-paper: #f4f4f1; --scan-ink: #191a19; --overlay-ink: #00a6dd;
  --brand: #285441; --brand-paper: #f5f3eb;
  --font-ui: "Helvetica Neue", Helvetica, Arial, system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  --gutter-l: max(16px, env(safe-area-inset-left, 0px));
  --gutter-r: max(16px, env(safe-area-inset-right, 0px));
  color-scheme: light;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --paper: #0f1312; --surface: #161b1a; --ink: #e4e9e7; --muted: #9aa49f; --rule: #2a3230;
    --nonrepro: #2c718b; --accent: #7cc9ea; --on-accent: #052230; --ok: #7fd09a; --warn: #f0b45c;
    color-scheme: dark;
  }}
}}
* {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{ margin: 0; background: var(--paper); color: var(--ink); font-family: var(--font-ui); font-size: 16px; line-height: 1.55; }}
img {{ max-width: 100%; }}
[hidden] {{ display: none !important; }}
.f-ceili {{ font-family: {STACK['ceili']}; }}
.f-carrick {{ font-family: {STACK['carrick']}; }}
.f-kilfane {{ font-family: {STACK['kilfane']}; }}
.f-tuam {{ font-family: {STACK['tuam']}; }}
.wrap {{ max-width: 1160px; margin-inline: auto; padding-left: var(--gutter-l); padding-right: var(--gutter-r); }}
a {{ color: var(--accent); text-underline-offset: 0.18em; }}
:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 3px; }}
h1, h2, h3 {{ text-wrap: balance; margin: 0; }}
p {{ margin: 0; }}
code {{ font-family: var(--font-mono); font-size: 0.92em; }}
.eyebrow, .tag, .grid-label, dt, .compare-title, .row-sub, .index-sub, .sheet-code, th {{
  letter-spacing: 0.06em; text-transform: uppercase; font-size: 12px; font-weight: 600; }}
.eyebrow {{ color: var(--muted); }}

/* top bar: back to the Drayne app collection */
.top {{ border-bottom: 1px solid var(--rule); }}
.top .wrap {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; padding-block: 14px; }}
.wordmark {{ display: inline-flex; align-items: center; gap: 9px; color: var(--ink); text-decoration: none; font-weight: 650; font-size: 16px; }}
.wordmark .mark {{ width: 28px; height: 28px; border-radius: 8px; display: grid; place-items: center; background: var(--brand); color: var(--brand-paper);
  font-family: Georgia, serif; font-size: 21px; font-weight: 400; }}
.wordmark .muted {{ color: var(--muted); font-weight: 400; }}
.top .ver {{ color: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }}

/* hero */
.hero {{ padding-block: 36px 28px; border-bottom: 1px solid var(--rule); }}
.hero-head {{ display: grid; gap: 6px; margin-bottom: 24px; }}
.hero-title {{ font-family: {STACK['ceili']}; font-weight: 400; font-size: clamp(3.2rem, 7.8vw, 6.4rem); line-height: {lh};
  background-image: linear-gradient(to bottom,
    transparent calc({hero_xl:.4f}em - 1px), var(--nonrepro) calc({hero_xl:.4f}em - 1px), var(--nonrepro) {hero_xl:.4f}em, transparent {hero_xl:.4f}em,
    transparent {hero_bl:.4f}em, var(--nonrepro) {hero_bl:.4f}em, var(--nonrepro) calc({hero_bl:.4f}em + 1px), transparent calc({hero_bl:.4f}em + 1px));
  background-size: 100% {lh}em; }}
.hero-grid {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 32px; align-items: start; }}
.hero-text {{ display: grid; gap: 20px; min-width: 0; padding-top: 4px; }}
.lede {{ font-size: 1.125rem; max-width: 36em; }}
.actions {{ display: grid; gap: 10px; justify-items: start; }}
.dl {{ display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px; }}
.btn {{ display: inline-block; font: inherit; font-weight: 600; font-size: 15px; border-radius: 6px; padding: 10px 16px; text-decoration: none;
  border: 1px solid var(--accent); background: var(--accent); color: var(--on-accent); }}
.btn.secondary {{ background: transparent; color: var(--accent); }}
.btn:hover {{ filter: brightness(1.08); }}
.dl-size {{ color: var(--muted); font-size: 14px; }}
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
.block-head h2 {{ font-size: 1.75rem; font-weight: 700; line-height: 1.2; }}
.block-head p {{ color: var(--muted); }}

/* tester */
.controls {{ display: flex; flex-wrap: wrap; gap: 12px 24px; align-items: center; margin-bottom: 8px; }}
.controls input[type=text] {{ font: inherit; font-size: 17px; flex: 1 1 320px; min-width: 0; padding: 10px 12px;
  border: 1px solid var(--rule); border-radius: 6px; background: var(--surface); color: var(--ink); }}
.controls select {{ font: inherit; font-size: 15px; padding: 9px 10px; border: 1px solid var(--rule); border-radius: 6px; background: var(--surface); color: var(--ink); }}
.controls label {{ display: inline-flex; align-items: center; gap: 8px; font-size: 14px; color: var(--muted); }}
.controls input[type=range] {{ width: 160px; accent-color: var(--accent); }}
.controls input[type=checkbox] {{ accent-color: var(--accent); width: 16px; height: 16px; }}
.controls output {{ font-variant-numeric: tabular-nums; min-width: 3ch; color: var(--ink); }}
.rows {{ display: grid; }}
.row {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 6px 24px; padding-block: 16px 18px; border-top: 1px solid var(--rule); }}
.row-meta {{ display: grid; gap: 4px; align-content: start; }}
.row-name {{ font-weight: 700; font-size: 16px; color: var(--ink); text-decoration: none; }}
.row-name:hover {{ color: var(--accent); }}
.row-sub {{ color: var(--muted); font-size: 11px; }}
.coverage {{ font-size: 13px; color: var(--ok); }}
.coverage.missing {{ color: var(--warn); }}
.coverage .miss {{ font-family: var(--font-mono); }}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }}
.chip {{ font: inherit; font-size: 13px; padding: 4px 10px; border-radius: 999px; cursor: pointer; border: 1px solid var(--rule); background: transparent; color: var(--ink); }}
.chip[aria-pressed="true"] {{ background: var(--accent); border-color: var(--accent); color: var(--on-accent); }}
.row-text {{ font-size: 56px; line-height: 1.3; overflow-wrap: anywhere; min-width: 0; background-repeat: repeat-y; align-self: start; }}
@media (min-width: 760px) {{ .row {{ grid-template-columns: 200px minmax(0, 1fr); }} }}

/* browser check */
.check-grid {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 28px; }}
@media (min-width: 900px) {{ .check-grid {{ grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 48px; }} }}
.table-wrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 15px; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: left; padding: 8px 12px 8px 0; border-bottom: 1px solid var(--rule); vertical-align: middle; }}
thead th {{ color: var(--muted); }}
th.check-name {{ font-size: 24px; font-weight: 400; letter-spacing: 0; text-transform: none; white-space: nowrap; }}
td.st.ok {{ color: var(--ok); font-weight: 600; }}
td.st.bad {{ color: var(--warn); font-weight: 600; }}
.verdict {{ font-size: 1.05rem; margin-top: 14px; }}
.kern-demo {{ display: flex; flex-wrap: wrap; gap: 8px 24px; align-items: baseline; margin-top: 10px; }}
.kern-demo span {{ font-size: 44px; line-height: 1.1; }}
.kern-demo small {{ display: block; font-size: 12px; color: var(--muted); }}

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
[data-f="ss01"] {{ font-feature-settings: "ss01" 1; }}
[data-f="ss02"] {{ font-feature-settings: "ss02" 1; }}
[data-f="ss03"] {{ font-feature-settings: "ss03" 1; }}
.tag {{ position: absolute; top: 6px; right: 8px; font-size: 10px; color: #5e6461; background: var(--scan-paper); padding: 1px 5px; border-radius: 3px; }}
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
.grid-label {{ color: var(--muted); margin-top: 18px; }}
.grid-note {{ color: var(--muted); font-size: 14px; margin-top: 10px; }}

/* web use + making */
.code {{ position: relative; background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; }}
.code pre {{ margin: 0; padding: 16px; overflow-x: auto; font-family: var(--font-mono); font-size: 13.5px; line-height: 1.6; }}
.copy {{ position: absolute; top: 8px; right: 8px; font: inherit; font-size: 13px; padding: 4px 10px; border-radius: 5px;
  border: 1px solid var(--rule); background: var(--paper); color: var(--ink); cursor: pointer; }}
.two {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 28px; }}
@media (min-width: 900px) {{ .two {{ grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 48px; }} }}
.prose {{ display: grid; gap: 12px; max-width: 36em; align-content: start; }}
.prose h3 {{ font-size: 1.05rem; font-weight: 700; margin-top: 8px; }}
.prose ul, .steps {{ margin: 0; padding-left: 1.3em; display: grid; gap: 6px; }}
.sources {{ margin: 0; padding-left: 1.2em; display: grid; gap: 4px; }}
.fine {{ color: var(--muted); font-size: 14px; }}
footer {{ padding-block: 28px 48px; color: var(--muted); font-size: 14px; }}
footer p + p {{ margin-top: 8px; }}
@media (prefers-reduced-motion: no-preference) {{ html {{ scroll-behavior: smooth; }} }}
</style>
</head>
<body>
<div class="top"><div class="wrap">
  <a class="wordmark" href="https://apps.drayne.xyz/"><span class="mark" aria-hidden="true">d.</span> drayne<span class="muted">/ apps</span></a>
  <span class="ver">Version {V}</span>
</div></div>

<header class="hero">
  <div class="wrap hero-head">
    <p class="eyebrow">Irish typeface competition · 1978</p>
    <h1 class="hero-title">four irish typefaces</h1>
  </div>
  <div class="wrap hero-grid">
    <div class="hero-text">
      <p class="lede">Céilí, Carrick, Kilfane and Tuam Uncial won the 1978 competition to design an Irish typeface and
        were sold as Letraset dry-transfer lettering. Here they are as web and desktop fonts, traced from the
        competition flyer and completed to about 400 characters each.</p>
      <div class="actions">
        <div class="dl">
          <a class="btn" href="downloads/four-irish-typefaces-fonts-v{V}.zip" download>Download the fonts</a>
          <span class="dl-size">ZIP · {sizes['fonts']} · WOFF2, WOFF, OTF, TTF, CSS and a README</span>
        </div>
        <div class="dl">
          <a class="btn secondary" href="downloads/four-irish-typefaces-v{V}.zip" download>Full package</a>
          <span class="dl-size">ZIP · {sizes['full']} · adds the PDF specimen, validation images and build scripts</span>
        </div>
        <div class="dl">
          <a class="btn secondary" href="downloads/Four-Irish-Typefaces-specimen.pdf">Specimen PDF</a>
          <span class="dl-size">9 pages · {sizes['pdf']}</span>
        </div>
        <p class="dl-size">In the public domain (<a href="LICENSE.txt">CC0 1.0</a>): no copyright is claimed.</p>
      </div>
    </div>
    <figure class="flyer">
      <img src="img/flyer.jpg" width="803" height="800" decoding="async"
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
        <p>Type anything, or pick a sample. Each face notes any character it doesn’t have. The blue lines mark the
          baseline and x-height, as on a drawing board.</p>
      </div>
      <div class="controls">
        <input id="tester-text" type="text" value="{esc(PRESETS[0][2])}" aria-label="Sample text" spellcheck="false" autocomplete="off">
        <label for="tester-preset">Sample <select id="tester-preset">{presets}</select></label>
        <label for="tester-size">Size <input id="tester-size" type="range" min="20" max="140" value="56"><output id="tester-size-out" for="tester-size">56</output></label>
        <label for="tester-guides"><input id="tester-guides" type="checkbox" checked> Guidelines</label>
      </div>
      <div class="rows">{rows}
      </div>
    </div>
  </section>

  <section class="block" id="check" aria-labelledby="check-h">
    <div class="wrap check-grid">
      <div>
        <div class="block-head">
          <h2 id="check-h">Your browser</h2>
          <p>This page loads the fonts exactly as any website would: WOFF2, with WOFF for older browsers, through
            <code>@font-face</code>. Here is what your browser did with them.</p>
        </div>
        <div class="table-wrap">
          <table id="check-table">
            <thead><tr><th scope="col">Face</th><th scope="col">Status</th><th scope="col">Format</th><th scope="col">Download</th></tr></thead>
            <tbody>{checks}
            </tbody>
          </table>
        </div>
        <p class="verdict" id="check-verdict" aria-live="polite">Checking the fonts…</p>
      </div>
      <div class="prose">
        <h3>Kerning</h3>
        <p>Kilfane’s most strongly kerned pairs, with kerning on and off. The full stop and comma tuck under P, F and V
          when the browser applies the font’s kerning.</p>
        <div class="kern-demo f-kilfane">
          <span style="font-kerning: normal">P. F. V, LV<small>kerning on</small></span>
          <span style="font-kerning: none">P. F. V, LV<small>kerning off</small></span>
        </div>
        <p class="fine" id="kern-result" aria-live="polite"></p>
        <h3>Served for the web</h3>
        <ul>
          <li>WOFF2 and WOFF files with the <code>font/woff2</code> and <code>font/woff</code> types</li>
          <li><code>font-display: swap</code>, so text shows straight away in a fallback face</li>
          <li>Cross-origin access allowed, so other sites can use the fonts from here</li>
          <li>Versioned URLs, so a new release replaces cached copies</li>
        </ul>
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
        <p>Download the fonts, put the <code>fonts</code> and <code>css</code> folders next to your pages, link
          your own copy of <code>css/four-irish-typefaces.css</code>, then name a face in your CSS. This site does not
          serve the fonts to other sites.</p>
        <h3>Font names</h3>
        <ul>{font_list}</ul>
        <p class="fine">Ready-made classes for the stylistic sets are in the stylesheet: <code>kilfane-roman-forms</code>,
          <code>kilfane-insular-forms</code>, <code>ceili-insular-r-s</code>, <code>ceili-uncial-a-n</code> and
          <code>ceili-alternates</code>.</p>
      </div>
      <div class="code">
        <button type="button" class="copy" id="copy-css">Copy</button>
<pre id="css-snippet">&lt;link rel="stylesheet" href="css/four-irish-typefaces.css"&gt;

&lt;style&gt;
  h1    {{ font-family: "Céilí Digital", "Ceili Digital", serif; }}
  .sign {{ font-family: "Carrick Digital", serif; }}
&lt;/style&gt;

&lt;!-- ready-made classes, including the stylistic sets --&gt;
&lt;h2 class="tuam-uncial"&gt;Tuaim Dá Ghualann&lt;/h2&gt;
&lt;p class="kilfane kilfane-roman-forms"&gt;Banc Ceannais na hÉireann&lt;/p&gt;
&lt;p class="ceili ceili-insular-r-s"&gt;Leabhar na hUidhre&lt;/p&gt;</pre>
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
            and corners and serifs were kept sharp. A smoothing spline removed the photocopy’s ripples without
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
          Irish Visual Arts Library, would sharpen every outline. The tracing and build scripts in the full package can
          be rerun on a new scan.</p>
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
          <li><a href="https://fontsinuse.com/typefaces/205971/ceili">Fonts In Use: Céilí</a></li>
          <li><a href="https://fontsinuse.com/typefaces/248202/carrick">Fonts In Use: Carrick</a></li>
          <li><a href="https://fontsinuse.com/typefaces/248201/kilfane">Fonts In Use: Kilfane</a></li>
          <li><a href="https://fontsinuse.com/typefaces/248203/tuam-uncial">Fonts In Use: Tuam Uncial</a></li>
          <li><a href="https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/45/">NIVAL: the competition brochure</a></li>
          <li><a href="https://www.nival.ie/william-curran-archive/">NIVAL: William Curran archive</a></li>
          <li><a href="https://www.dublininquirer.com/after-almost-50-years-a-renowned-irish-font-is-brought-into-the-digital-age/">Dublin Inquirer (2020) on the Tuam revival</a></li>
          <li><a href="https://www.irishtimes.com/news/master-typographer-and-designer-1.313378">Irish Times obituary of Jarlath Hayes</a></li>
          <li><a href="https://signalfoundry.com/typefaces/jarlath">Signal Type Foundry: Jarlath</a></li>
          <li><a href="https://atypi.org/presentation/retyping-europe/">ATypI: Transnational heritage and alternative futures</a></li>
          <li><a href="https://catalogue.nli.ie/Record/vtls000883198">Dermot McGuinne, Irish Type Design (2nd ed., 2010)</a></li>
        </ul>
      </div>
    </div>
  </section>
</main>

<footer>
  <div class="wrap">
    <p>Typeface designs by Hermann Hecht, William Curran and Jarlath Hayes, 1978. Digitised in 2026 from the printed
      flyer. Version {V}.</p>
    <p>__LICENCE__</p>
    <p>Jarlath, Signal Type Foundry’s revival of Tuam Uncial, is a separate commercial product and is not part of this
      project.</p>
  </div>
</footer>

<script>
(() => {{
  const M = {metrics_js};
  const COVER = Object.fromEntries(Object.entries({cover_js}).map(([k, v]) => [k, new Set(v)]));
  const FILES = {files_js};
  const FAMILY = {fam_js};
  const PRESETS = {presets_js};
  const text = document.getElementById('tester-text');
  const preset = document.getElementById('tester-preset');
  const size = document.getElementById('tester-size');
  const out = document.getElementById('tester-size-out');
  const guides = document.getElementById('tester-guides');
  const rows = [...document.querySelectorAll('.row')];
  let lang = PRESETS[0].lang;

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
  function coverage(row, t) {{
    const have = COVER[row.dataset.face];
    const missing = [...new Set([...t].filter(ch => !/\\s/.test(ch) && !have.has(ch.codePointAt(0))))];
    const note = row.querySelector('.coverage');
    note.classList.toggle('missing', missing.length > 0);
    note.textContent = '';
    if (!missing.length) {{ note.textContent = 'Every character is in this font'; return; }}
    note.append('Not in this font: ');
    const s = document.createElement('span'); s.className = 'miss'; s.textContent = missing.join(' ');
    note.append(s);
  }}
  function update() {{
    const t = text.value.trim() ? text.value : PRESETS[0].text;
    out.value = size.value;
    rows.forEach(r => {{
      const el = r.querySelector('.row-text');
      el.textContent = t; el.lang = lang;
      paint(r); coverage(r, t);
    }});
  }}
  text.addEventListener('input', update);
  preset.addEventListener('change', () => {{
    const p = PRESETS[Number(preset.value)];
    text.value = p.text; lang = p.lang; update();
  }});
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
    try {{ navigator.clipboard.writeText(snippet.textContent).then(() => done('Copied'), select); }} catch (e) {{ select(); }}
  }});

  // browser check: did each face load, and as which format?
  async function check() {{
    const results = [];
    for (const [key, family] of Object.entries(FAMILY)) {{
      const row = document.querySelector(`#check-table tr[data-face="${{key}}"]`);
      let ok = false;
      try {{
        const faces = await document.fonts.load(`40px "${{family}}"`, 'abc');
        ok = faces.length > 0 && faces.every(f => f.status === 'loaded');
      }} catch (e) {{ ok = false; }}
      const entries = performance.getEntriesByType('resource').filter(e => e.name.includes('/fonts/') && e.name.includes(FILES[key] + '-Regular.'));
      const e = entries[entries.length - 1];
      const fmt = e ? (e.name.includes('.woff2') ? 'WOFF2' : e.name.includes('.woff') ? 'WOFF' : '–') : (ok ? 'cached' : '–');
      const bytes = e ? (e.encodedBodySize || e.transferSize || 0) : 0;
      const st = row.querySelector('.st');
      st.textContent = ok ? 'Loaded' : 'Not loaded';
      st.className = 'st ' + (ok ? 'ok' : 'bad');
      row.querySelector('.fmt').textContent = fmt;
      row.querySelector('.size').textContent = bytes ? Math.round(bytes / 1024) + ' KB' : (e ? 'from cache' : '–');
      results.push({{ ok, fmt }});
    }}
    const verdict = document.getElementById('check-verdict');
    const all = results.every(r => r.ok);
    const fmts = [...new Set(results.map(r => r.fmt).filter(f => f !== '–'))];
    verdict.textContent = all
      ? `All four fonts loaded${{fmts.length === 1 && fmts[0] !== 'cached' ? ' as ' + fmts[0] : ''}}. They will work in this browser.`
      : 'Some fonts did not load. Check that this browser allows web fonts, then reload the page.';
    // kerning: the kerned pair is narrower when the browser applies the font's kerning
    const w = [...document.querySelectorAll('.kern-demo span')].map(s => {{
      const r = document.createRange(); r.selectNodeContents(s.firstChild); return r.getBoundingClientRect().width;
    }});
    document.getElementById('kern-result').textContent = (w[0] && w[1] && w[0] < w[1] - 0.5)
      ? 'Kerning is applied in this browser.' : 'Kerning made no difference here.';
  }}
  if (document.fonts && document.fonts.load) {{ document.fonts.ready.then(check); }}
  else {{ document.getElementById('check-verdict').textContent = 'This browser cannot report on web fonts.'; }}
}})();
</script>
</body>
</html>
'''


def social_card(path, out_png):
    """1200×630 link preview: the four names, each in its own face."""
    from playwright.sync_api import sync_playwright
    css_link = 'file://' + os.path.join(path, 'site/css/four-irish-typefaces.css')
    names = ''.join(f'<div class="n f-{k}">{esc(FONTS[k]["family"])}</div>' for k in A.ORDER)
    doc = f'''<!doctype html><meta charset=utf-8><link rel="stylesheet" href="{css_link}"><style>
    body{{margin:0;width:1200px;height:630px;background:#f1f3f1;color:#131615;font-family:"Helvetica Neue",Arial,sans-serif;
    display:flex;flex-direction:column;justify-content:center;padding:0 80px;box-sizing:border-box;
    background-image:linear-gradient(#8ccfe7,#8ccfe7);background-size:100% 1px;background-repeat:no-repeat;background-position:0 492px}}
    .e{{font-size:26px;letter-spacing:.08em;text-transform:uppercase;color:#56605c;font-weight:600;margin-bottom:18px}}
    .n{{font-size:92px;line-height:1.08}} .f-ceili{{font-family:"Céilí"}} .f-carrick{{font-family:"Carrick"}}
    .f-kilfane{{font-family:"Kilfane"}} .f-tuam{{font-family:"Tuam Uncial"}}
    .row{{display:flex;flex-wrap:wrap;gap:0 56px}}</style>
    <div class="e">Four Irish Typefaces · 1978</div><div class="row">{names}</div>'''
    tmp = os.path.join(path, 'social.html'); open(tmp, 'w').write(doc)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium'); pg = b.new_page(viewport={'width': 1200, 'height': 630})
        pg.goto('file://' + tmp); pg.wait_for_timeout(600); pg.screenshot(path=out_png); b.close()
    os.remove(tmp)


DOCKERFILE = '''FROM nginx:alpine
COPY site/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
'''
DOCKERIGNORE = '''*
!site/
!site/**
!nginx.conf
'''
NGINX = r'''server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    server_tokens off;
    charset utf-8;
    client_max_body_size 1m;
    client_body_timeout 15s;
    send_timeout 30s;
    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml font/ttf font/otf;

    add_header X-Content-Type-Options nosniff always;
    add_header Cache-Control "public, max-age=300" always;

    location / {
        limit_except GET { deny all; }
        try_files $uri $uri/ =404;
    }

    # Web fonts. nginx already maps .woff2/.woff to font/woff2 and font/woff; OTF/TTF get
    # their own types. They are for this page only: no cross-origin access, so other sites
    # cannot link them. URLs carry ?v=<version>, so a long cache is safe.
    location /fonts/ {
        limit_except GET { deny all; }
        add_header X-Content-Type-Options nosniff always;
        add_header Cache-Control "public, max-age=2592000" always;
        location ~* \.ttf$ {
            default_type font/ttf;
            add_header X-Content-Type-Options nosniff always;
            add_header Cache-Control "public, max-age=2592000" always;
        }
        location ~* \.otf$ {
            default_type font/otf;
            add_header X-Content-Type-Options nosniff always;
            add_header Cache-Control "public, max-age=2592000" always;
        }
    }
    location /css/ {
        limit_except GET { deny all; }
        add_header X-Content-Type-Options nosniff always;
        add_header Cache-Control "public, max-age=3600" always;
    }
    location /img/ {
        limit_except GET { deny all; }
        add_header X-Content-Type-Options nosniff always;
        add_header Cache-Control "public, max-age=86400" always;
    }
    location /downloads/ {
        limit_except GET { deny all; }
        add_header X-Content-Type-Options nosniff always;
        add_header Cache-Control "public, max-age=3600" always;
    }
    location ~ /\. { deny all; }
}
'''
README = f'''# Four Irish Typefaces: web test page

The test page and web-font host for Céilí, Carrick, Kilfane and Tuam Uncial, version {V}.
It is a static site served by nginx; the Docker image contains only `site/` and `nginx.conf`.

- `site/index.html`: test page (tester, browser check, scan comparisons, downloads)
- `site/css/four-irish-typefaces.css`: `@font-face` rules other sites can link to
- `site/fonts/`: WOFF2 and WOFF for the web, OTF and TTF for download
- `site/downloads/`: the release ZIPs and the PDF specimen
- `nginx.conf`: font MIME types and caching (no cross-origin access)

Publish with the Drayne helper from the `drayne-apps` checkout:

```powershell
node publisher/cli.mjs publish 'C:\\path\\to\\{SLUG}'
```

`publish.json` is prepared (public, port 80, Dockerfile, 256 MiB). Later updates are
ordinary pushes to `main`. To try it locally: `docker build -t {SLUG} . && docker run -p 8080:80 {SLUG}`.
'''


def main(dest, licence_text):
    site = os.path.join(dest, 'site')
    if os.path.exists(dest):
        shutil.rmtree(dest)
    for sub in ('css', 'img', 'downloads', 'fonts'):
        os.makedirs(os.path.join(site, sub), exist_ok=True)
    for fmt in ('woff2', 'woff', 'otf', 'ttf'):
        shutil.copytree(os.path.join(PKG, 'fonts', fmt), os.path.join(site, 'fonts', fmt))
    write_css(os.path.join(site, 'css/four-irish-typefaces.css'))
    for name in (f'four-irish-typefaces-fonts-v{V}.zip', f'four-irish-typefaces-v{V}.zip'):
        shutil.copy(os.path.join(ZIPS, name), os.path.join(site, 'downloads', name))
    shutil.copy(os.path.join(PKG, 'docs/specimen/Four-Irish-Typefaces-specimen.pdf'), os.path.join(site, 'downloads'))
    shutil.copy(os.path.join(PKG, 'LICENSE.txt'), os.path.join(site, 'LICENSE.txt'))
    shutil.copy(os.path.join(PKG, 'LICENSE.txt'), os.path.join(site, 'fonts', 'LICENSE.txt'))
    faces = [A.face_data(k) for k in A.ORDER]
    for d in faces:
        d['pil'].save(os.path.join(site, f'img/{d["key"]}-scan.jpg'), 'JPEG', quality=86, optimize=True, progressive=True)
    Image.open(paths.SCAN).convert('L').crop((0, 0, 803, 800)).save(os.path.join(site, 'img/flyer.jpg'), 'JPEG', quality=82, optimize=True, progressive=True)
    icon(64, os.path.join(site, 'img/icon-64.png')); icon(180, os.path.join(site, 'img/icon-180.png'))
    sizes = dict(fonts=kb(os.path.join(site, f'downloads/four-irish-typefaces-fonts-v{V}.zip')),
                 full=kb(os.path.join(site, f'downloads/four-irish-typefaces-v{V}.zip')),
                 pdf=kb(os.path.join(site, 'downloads/Four-Irish-Typefaces-specimen.pdf')))
    doc = page(faces, sizes).replace('__LICENCE__', licence_text)
    open(os.path.join(site, 'index.html'), 'w').write(doc)
    social_card(dest, os.path.join(site, 'img/social.png'))
    open(os.path.join(dest, 'Dockerfile'), 'w').write(DOCKERFILE)
    open(os.path.join(dest, '.dockerignore'), 'w').write(DOCKERIGNORE)
    open(os.path.join(dest, 'nginx.conf'), 'w').write(NGINX)
    open(os.path.join(dest, 'README.md'), 'w').write(README)
    publish = dict(slug=SLUG, title=TITLE, description=DESCRIPTION, access='public', repository=f'ddrayne/{SLUG}',
                   branch='main', port=80, buildPack='dockerfile', memoryMiB=256, cpus=0.5,
                   domain=f'https://{SLUG}.apps.drayne.xyz')
    open(os.path.join(dest, 'publish.json'), 'w').write(json.dumps(publish, indent=2, ensure_ascii=False) + '\n')
    total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(dest) for f in fs)
    print('wrote', dest, f'{total / 1e6:.1f} MB', 'index.html', os.path.getsize(os.path.join(site, 'index.html')))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else
         ('No copyright is claimed: the fonts are in the public domain (<a href="LICENSE.txt">CC0 1.0</a>). '
          'Use, change, share or sell them for anything, without asking.'))
