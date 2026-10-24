"""Specimen sheet for the four fonts: A4 PDF plus one PNG per face (rendered by Chromium)."""
import paths
import base64, io, os, sys
from PIL import Image
from fontTools.ttLib import TTFont
from playwright.sync_api import sync_playwright
from build2 import FONTS, OUT, VERSION, FAMILY_STYLES
from specs import SPECS
from seg import GRAY

DEST = paths.SPECIMEN

INFO = {
    'kilfane': dict(credit='William Curran · joint third prize', display='Banc Ceannais na hÉireann',
                    alpha=['ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz', '0123456789 £$€&?!(;:) '],
                    sets=[('ss01', 'ss01 · Roman forms'), ('ss02', 'ss02 · Insular forms')]),
    'tuam': dict(credit='Jarlath Hayes · fourth place (highly commended)', display='Fáilte go Tuaim',
                 alpha=['abcdefghijklmnopqrstuvwxyz', '0123456789 £$€&?!(;:)'], sets=[]),
    'carrick': dict(credit='William Curran · second prize', display='Ceol ⁊ craic',
                    alpha=['abcdefghijklmnopqrstuvwxyz', '0123456789 £$€&?!(;:) '], sets=[]),
    'ceili': dict(credit='Hermann Hecht · first prize', display='Céilí mór anocht!',
                  alpha=['abcdefghijklmnopqrstuvwxyz', '0123456789 £$€&?!(;:)'],
                  sets=[('ss01', 'ss01 · Insular r and s'), ('ss02', 'ss02 · Uncial A and N'),
                        ('ss03', 'ss03 · Alternate a d e j l v')]),
}
IRISH = 'Is fearr Gaeilge bhriste ná Béarla cliste. Tír gan teanga, tír gan anam. Ní neart go cur le chéile.'
LENITION = 'A ċara, mo ġrá ṫú! A Ṡeáin, cá ḃfuil do ṁáṫair? Ceol ⁊ craic.'
GAIDHLIG = 'Ciamar a tha thu? Tha gu math, tapadh leibh. Fàilte gu Dùn Èideann!'
ENGLISH = 'The quick brown fox jumps over the lazy dog. Sphinx of black quartz, judge my vow — “1978”.'


def scan_b64(font):
    x0, y0, x1, y1 = SPECS[font]['box']
    im = Image.fromarray(GRAY[y0:y1, x0:x1].astype('uint8'))
    buf = io.BytesIO(); im.save(buf, 'PNG')
    return base64.b64encode(buf.getvalue()).decode(), im.size


def charset(font):
    f = TTFont(os.path.join(OUT, FONTS[font]['ps'] + '-Regular.otf'))
    cm = f.getBestCmap()
    chars = [chr(c) for c in sorted(cm) if c > 0x20 and c != 0xA0 and not 0x300 <= c < 0x370]
    if FONTS[font]['unicase']:
        chars = [c for c in chars if not (c.isupper() and len(c.lower()) == 1 and c.lower() != c and ord(c.lower()) in cm)]
    return chars


def section(font):
    cfg, inf = FONTS[font], INFO[font]
    b64, (w, h) = scan_b64(font)
    alts = ''.join(f'<p class="lab">{label}</p><p class="t m" style="font-feature-settings:\'{tag}\'">{IRISH}</p>'
                   for tag, label in inf['sets'])
    cells = ''.join(f'<span>{c}</span>' for c in charset(font))
    for tag, label in inf['sets']:
        for b, alt in next(m for t, l, m in cfg['sets'] if t == tag).items():
            cells += f'<span class="alt" style="font-feature-settings:\'{tag}\'" title="{label}">{b}</span>'
    unic = ('' if not cfg['unicase'] else
            '<p class="note">Unicase: capitals and lower case share the same forms, as on the 1978 sheet.</p>')
    return f'''
<section style="--f:'{font}'">
  <header><h1 class="f">{cfg["family"]}</h1>
  <p class="credit">{inf["credit"]} · 1978 “Design an Irish Typeface” competition (Letraset · Kilkenny Design Workshops · D. O’Sullivan)</p></header>
  <p class="f disp">{inf["display"]}</p>
  {''.join(f'<p class="f al">{a}</p>' for a in inf["alpha"])}
  {unic}
  <p class="t l">{IRISH}</p>
  <p class="t m">{LENITION}</p>
  <p class="t m">{GAIDHLIG}</p>
  <p class="t s">{ENGLISH} {IRISH}</p>
  {alts}
  <div class="cmp"><div><p class="lab">The 1978 flyer this was traced from</p>
  <img src="data:image/png;base64,{b64}" style="width:{min(int(w * 1.6), 560)}px"></div></div>
</section>
<section class="cs" style="--f:'{font}'">
  <p class="lab">{cfg["family"]} — character set (alternates shaded)</p>
  <div class="grid f">{cells}</div>
</section>
{family(font)}'''


def family(font):
    """The styles drawn in 2026 from the regular, shown together."""
    cfg, inf = FONTS[font], INFO[font]; styles = FAMILY_STYLES[font]
    wt = lambda st: 700 if 'Bold' in st else 400
    sl = lambda st: 'italic' if 'Italic' in st else 'normal'
    rows = ''.join(f'<div class="srow"><span class="lab">{st}</span><span class="f" style="font-weight:{wt(st)};font-style:{sl(st)}">{inf["display"]}</span></div>'
                   for st in styles)
    alpha = inf['alpha'][0] if cfg['unicase'] else inf['alpha'][1]
    pairs = ''.join(f'<p class="t m" style="font-weight:{wt(st)};font-style:{sl(st)}"><span class="lab2">{st}</span>{alpha}</p>' for st in styles)
    mix = ('Tír gan teanga, <i>tír gan anam</i>. Ní neart go cur le chéile, <b>agus ar scáth a chéile</b> '
           '<b><i>a mhaireann na daoine</i></b>.' if 'Bold' in styles else
           'Tír gan teanga, <i>tír gan anam</i>. Ní neart go cur le chéile, <i>agus ar scáth a chéile a mhaireann na daoine</i>.')
    small = ''.join(f'<p class="t s" style="font-weight:{wt(st)};font-style:{sl(st)};margin:6px 0"><span class="lab2">{st} · 15</span>{IRISH} {GAIDHLIG}</p>'
                    for st in styles)
    why = ('An italic, a bold and a bold italic, drawn in 2026 from the 1978 regular. The bold is the regular redrawn with '
           'a wider pen in the face’s own contrast, its counters and openings kept by hand where the pen would close them; '
           'the italic is the regular narrowed four per cent, its stems restored, and sloped eight degrees.'
           if 'Bold' in styles else
           'An italic, drawn in 2026 from the 1978 regular: narrowed four per cent, its stems restored, and sloped eight '
           'degrees. The face is already black (stems over a third of the x-height), so there is no bold: a heavier cut '
           'would close its counters' + (' and its hairline cuts.' if font == 'tuam' else '.'))
    return f'''
<section class="fam" style="--f:'{font}'">
  <p class="lab">{cfg["family"]} — the family</p>
  {rows}
  <p class="note" style="max-width:820px;margin-top:14px">{why}</p>
  {pairs}
  <p class="t l" style="margin-top:16px">{mix}</p>
  {small}
</section>'''


def cover():
    import base64, io
    from PIL import Image
    buf = io.BytesIO(); Image.open(paths.SCAN).save(buf, 'JPEG', quality=92)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f'''
<section class="cover" style="--f:'ceili'">
  <h1 class="f" style="font-size:110px">four irish typefaces</h1>
  <p class="credit">Céilí · Carrick · Kilfane · Tuam Uncial — winners of the 1978 “Design an Irish Typeface” competition,
  sponsored by Letraset, Kilkenny Design Workshops and D. O’Sullivan Graphic Supplies. Digitised 2026, version {VERSION}.
  Fonts copyright 2026 Dan Drayne, free to use under the SIL Open Font License 1.1 (openfontlicense.org).</p>
  <div style="display:flex;gap:28px;align-items:flex-start">
  <img src="data:image/jpeg;base64,{b64}" style="width:430px;border:1px solid var(--rule)">
  <div style="font-size:15px;line-height:1.5;max-width:560px">
  <p><b>Céilí</b> — Hermann Hecht, first prize. <b>Carrick</b> — William Curran, second prize.
  <b>Kilfane</b> — William Curran, joint third. <b>Tuam Uncial</b> — Jarlath Hayes, fourth place (highly commended).</p>
  <p>The faces were issued as Letraset dry-transfer sheets S53909–S53916 and sold through D. O’Sullivan Graphic
  Supplies, Dublin. Kilfane is reported on the Series C Irish banknotes; Tuam Uncial on Clannad sleeves and the
  Glenroe credits; Céilí on National Library of Ireland booklets.</p>
  <p>These fonts were traced from the flyer shown here (left). Each was completed to about 400 characters:
  Irish with the traditional lenition dots and ⁊, Scottish Gaelic, Welsh, and the Latin-script languages of Western and
  Central Europe, with kerning, mark positioning and the original alternates as stylistic sets. Glyphs not shown on the
  sheet were drawn to match each face.</p>
  <p>The sheet shows one style of each. Version 2 adds new work drawn in 2026 from those regulars: an italic for all
  four, and a bold and bold italic for Céilí and Kilfane (Carrick and Tuam Uncial are already black).</p></div></div>
</section>'''


def page(fonts):
    css = ''.join(f'@font-face{{font-family:"{k}";src:url("file://{OUT}/{FONTS[k]["ps"]}-{st.replace(" ", "")}.woff2");'
                  f'font-weight:{700 if "Bold" in st else 400};font-style:{"italic" if "Italic" in st else "normal"}}}'
                  for k in fonts for st in FAMILY_STYLES[k])
    body = cover() + ''.join(section(k) for k in fonts)
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>Four Irish Typefaces</title><style>
{css}
@page {{ size: A4; margin: 14mm; }}
:root {{ --ink: #1a1a1a; --mute: #6b6b6b; --rule: #d9d4ca; --paper: #fbf9f4; }}
body {{ margin: 0; background: var(--paper); color: var(--ink); font-family: "DejaVu Sans", sans-serif; }}
section {{ padding: 26px 34px 30px; page-break-after: always; break-after: page; width: 1060px; }}
.f, .t {{ font-family: var(--f); }}
h1 {{ font-size: 92px; font-weight: normal; margin: 0; line-height: 1.05; }}
.credit {{ font-size: 13px; color: var(--mute); margin: 6px 0 18px; letter-spacing: .02em; }}
header {{ border-bottom: 1px solid var(--rule); margin-bottom: 14px; }}
.disp {{ font-size: 74px; margin: 6px 0 10px; line-height: 1.1; }}
.al {{ font-size: 38px; margin: 2px 0; line-height: 1.25; }}
.t {{ margin: 10px 0; line-height: 1.3; }} .l {{ font-size: 34px; }} .m {{ font-size: 26px; }} .s {{ font-size: 15px; }}
.lab {{ font-size: 12px; color: var(--mute); margin: 18px 0 2px; text-transform: uppercase; letter-spacing: .08em; }}
.note {{ font-size: 13px; color: var(--mute); margin: 4px 0 8px; }}
.cmp img {{ display: block; margin-top: 6px; border: 1px solid var(--rule); filter: grayscale(1); }}
.grid {{ display: flex; flex-wrap: wrap; gap: 0; margin-top: 8px; border-left: 1px solid var(--rule); border-top: 1px solid var(--rule); }}
.grid span {{ width: 47px; height: 54px; font-size: 31px; display: flex; align-items: center; justify-content: center;
             border-right: 1px solid var(--rule); border-bottom: 1px solid var(--rule); }}
.grid span.alt {{ background: #efe9dc; }}
.srow {{ display: flex; align-items: baseline; gap: 18px; border-bottom: 1px solid var(--rule); }}
.srow .lab {{ flex: 0 0 120px; margin: 0; }} .srow .f {{ font-size: 60px; line-height: 1.3; white-space: nowrap; }}
.lab2 {{ display: inline-block; width: 130px; font: 12px "DejaVu Sans", sans-serif; color: var(--mute); text-transform: uppercase; letter-spacing: .08em; font-style: normal; font-weight: normal; }}
</style></head><body>{body}</body></html>'''


if __name__ == '__main__':
    fonts = sys.argv[1:] or list(FONTS)
    os.makedirs(DEST, exist_ok=True)
    html_path = os.path.join(DEST, 'specimen.html')
    open(html_path, 'w').write(page(fonts))
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        pg = b.new_page(viewport={'width': 1130, 'height': 900})
        pg.goto('file://' + html_path); pg.wait_for_timeout(600)
        pg.pdf(path=os.path.join(DEST, 'Four-Irish-Typefaces-specimen.pdf'), format='A4',
               print_background=True, prefer_css_page_size=True, scale=0.68)
        for i, k in enumerate(fonts):
            secs = pg.query_selector_all('section')
            box1 = secs[3 * i + 1].bounding_box(); box2 = secs[3 * i + 3].bounding_box()
            clip = dict(x=0, y=box1['y'], width=1130, height=box2['y'] + box2['height'] - box1['y'])
            pg.screenshot(path=os.path.join(DEST, f'{FONTS[k]["ps"]}-specimen.png'), clip=clip, full_page=True)
        b.close()
    os.remove(html_path)
    print('specimen ->', DEST)
