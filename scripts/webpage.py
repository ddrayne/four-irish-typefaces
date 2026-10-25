"""Generate the web specimen / type tester (index.html) for the package."""
import html, os, sys
from fontTools.ttLib import TTFont
from build2 import FONTS, OUT, FAMILY_STYLES

INFO = {
    'kilfane': dict(css='Kilfane Digital', credit='William Curran', place='Commended',
                    display='Banc Ceannais na hÉireann',
                    note='The only one of the four with true capitals. Reportedly used on the Series C Irish pound notes.'),
    'tuam': dict(css='Tuam Uncial Digital', credit='Jarlath Hayes', place='Commended',
                 display='Fáilte go Tuaim',
                 note='A heavy, square uncial reportedly made by cutting up Helvetica Bold; seen on Clannad sleeves and the Glenroe credits. Its hairline cuts are part of the design.'),
    'carrick': dict(css='Carrick Digital', credit='William Curran', place='Highly Commended', display='Ceol ⁊ craic',
                    note='A chunky, lower-case-only display face; the name comes from carraig, “rock”.'),
    'ceili': dict(css='Céilí Digital', credit='Hermann Hecht', place='First prize', display='Céilí mór anocht!',
                  note='The winner: a light, calligraphic unicase with insular letterforms and old-style figures.'),
}
TEXT = 'Is fearr Gaeilge bhriste ná Béarla cliste. A ċara, mo ġrá ṫú! Ciamar a tha thu? The quick brown fox jumps over the lazy dog — 1978.'


def chars(key):
    f = TTFont(os.path.join(OUT, FONTS[key]['ps'] + '-Regular.otf'))
    cm = f.getBestCmap()
    out = [chr(c) for c in sorted(cm) if c > 0x20 and c not in (0xA0,) and not 0x300 <= c < 0x370]
    if FONTS[key]['unicase']:
        out = [c for c in out if not (c.isupper() and len(c.lower()) == 1 and c.lower() != c and ord(c.lower()) in cm)]
    return out, len(cm)


def section(key):
    cfg, inf = FONTS[key], INFO[key]
    cs, n = chars(key)
    sets = ''.join(f'<label><input type="checkbox" data-feat="{t}"> {html.escape(t)} · {html.escape(l)}</label>'
                   for t, l, _ in cfg['sets'])
    grid = ''.join(f'<span>{html.escape(c)}</span>' for c in cs)
    ps = cfg['ps']; styles = FAMILY_STYLES[key]
    wt = lambda st: 700 if 'Bold' in st else 400
    sl = lambda st: 'italic' if 'Italic' in st else 'normal'
    strip = ''.join(f'<div class="style-row"><span class="style-name">{st}</span>'
                    f'<span class="f" style="font-weight:{wt(st)};font-style:{sl(st)}">{html.escape(inf["display"])}</span></div>'
                    for st in styles)
    picks = ''.join(f'<label><input type="radio" name="st-{key}" value="{st}"{" checked" if st == "Regular" else ""}> {st}</label>'
                    for st in styles)
    dls = ''.join(f'<tr><th>{st}</th>' + ''.join(
        f'<td><a href="fonts/{x}/{ps}-{st.replace(" ", "")}.{x}" download>{x.upper()}</a></td>' for x in ('woff2', 'woff', 'otf', 'ttf')) + '</tr>'
        for st in styles)
    return f'''
<section class="face" style="--face:'{inf['css']}'">
  <header>
    <h2 class="f">{html.escape(cfg['family'])}</h2>
    <p class="meta">{html.escape(inf['credit'])} · {html.escape(inf['place'])}, 1978 · {n} characters · {' · '.join(styles)}</p>
  </header>
  <div class="styles">{strip}</div>
  <p class="note">{html.escape(inf['note'])}</p>
  <div class="tester">
    <div class="controls">
      <span class="picks">{picks}</span>
      <label>Size <input type="range" min="14" max="140" value="44" class="size"></label>
      <label><input type="checkbox" data-feat="kern" checked> kerning</label>
      {sets}
    </div>
    <div class="f sample" contenteditable="true" spellcheck="false">{html.escape(TEXT)}</div>
  </div>
  <details><summary>Character set</summary><div class="f grid">{grid}</div></details>
  <table class="dl"><caption>Download</caption>{dls}</table>
</section>'''


def page():
    body = ''.join(section(k) for k in ('ceili', 'carrick', 'kilfane', 'tuam'))
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Four Irish Typefaces</title>
<link rel="stylesheet" href="css/four-irish-typefaces.css">
<style>
:root {{ --ink:#1b1a17; --mute:#6e6a62; --rule:#dcd6ca; --paper:#faf8f3; --accent:#2f6b4f; }}
@media (prefers-color-scheme: dark) {{ :root {{ --ink:#ece8df; --mute:#a59f93; --rule:#3a3832; --paper:#171614; --accent:#7fc4a0; }} }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--paper); color:var(--ink); font:16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width:1080px; margin:0 auto; padding:32px 20px 64px; }}
.hero h1 {{ font-family:"Céilí Digital","Ceili Digital",serif; font-weight:400; font-size:clamp(44px,9vw,104px); line-height:1; margin:8px 0 12px; }}
.hero p {{ max-width:720px; color:var(--mute); margin:6px 0; }}
.face {{ border-top:1px solid var(--rule); padding:28px 0 20px; }}
.f {{ font-family:var(--face), serif; }}
.face h2 {{ font-weight:400; font-size:clamp(40px,7vw,76px); margin:0; line-height:1.05; }}
.meta {{ margin:4px 0 0; color:var(--mute); font-size:14px; }}
.styles {{ margin:14px 0 4px; }}
.style-row {{ display:flex; align-items:baseline; gap:14px; border-bottom:1px solid var(--rule); padding:2px 0 6px; }}
.style-row .f {{ font-size:clamp(28px,5.4vw,60px); line-height:1.2; overflow-wrap:anywhere; }}
.style-name {{ flex:0 0 92px; font-size:12px; letter-spacing:.06em; text-transform:uppercase; color:var(--mute); }}
.picks {{ display:inline-flex; flex-wrap:wrap; gap:4px 12px; }}
.note {{ max-width:720px; margin:6px 0 14px; }}
.tester {{ border:1px solid var(--rule); border-radius:10px; padding:12px 14px; }}
.controls {{ display:flex; flex-wrap:wrap; gap:6px 18px; font-size:13px; color:var(--mute); margin-bottom:8px; align-items:center; }}
.controls input[type=range] {{ vertical-align:middle; width:140px; }}
.sample {{ font-size:44px; line-height:1.25; outline:none; min-height:1.3em; overflow-wrap:anywhere; }}
details {{ margin:14px 0 6px; }} summary {{ cursor:pointer; color:var(--mute); font-size:14px; }}
.grid {{ display:flex; flex-wrap:wrap; margin-top:10px; border-left:1px solid var(--rule); border-top:1px solid var(--rule); font-size:30px; }}
.grid span {{ width:46px; height:52px; display:flex; align-items:center; justify-content:center; border-right:1px solid var(--rule); border-bottom:1px solid var(--rule); }}
.dl {{ font-size:14px; color:var(--mute); border-collapse:collapse; margin-top:10px; }}
.dl caption {{ text-align:left; padding-bottom:4px; }} .dl th {{ text-align:left; font-weight:500; padding:2px 14px 2px 0; }}
.dl td {{ padding:2px 10px 2px 0; }} a {{ color:var(--accent); }}
pre {{ background:rgba(127,127,127,.08); border:1px solid var(--rule); border-radius:8px; padding:12px; overflow:auto; font-size:13px; }}
footer {{ border-top:1px solid var(--rule); margin-top:28px; padding-top:16px; color:var(--mute); font-size:13px; }}
</style>
</head>
<body><main>
<div class="hero">
  <h1>four irish typefaces</h1>
  <p>Céilí, Carrick, Kilfane and Tuam Uncial won the 1978 “Design an Irish Typeface” competition sponsored by Letraset,
  Kilkenny Design Workshops and D. O’Sullivan Graphic Supplies, and were sold as Letraset dry-transfer sheets.
  These independent digital versions, named Céilí Digital, Carrick Digital, Kilfane Digital and Tuam Uncial
  Digital to keep them apart from the originals, were traced from the competition’s “Four Irish Typefaces” flyer and completed with
  around 400 characters each, covering Irish (including traditional lenition dots and ⁊), Scottish Gaelic, Welsh
  and the other Latin-script languages of Europe.</p>
  <p>The sheet shows each face in one style. Version 2 adds, as new work drawn in 2026 from those regulars, an italic
  for all four and a bold and bold italic for Céilí and Kilfane. Carrick and Tuam Uncial are already black.</p>
</div>
{body}
<section class="face">
  <h3>Use on a website</h3>
<pre>&lt;link rel="stylesheet" href="css/four-irish-typefaces.css"&gt;

h1     {{ font-family: "Céilí Digital", "Ceili Digital", serif; }}
.sign  {{ font-family: "Carrick Digital", serif; }}
p.note {{ font-family: "Kilfane Digital", serif; font-feature-settings: "ss01"; }}  /* roman forms */

&lt;p class="kilfane"&gt;Tír gan teanga, &lt;b&gt;tír gan anam&lt;/b&gt;, &lt;i&gt;mar a deirtear&lt;/i&gt;.&lt;/p&gt;
/* &lt;b&gt;, &lt;i&gt;, font-weight: 700 and font-style: italic pick the drawn styles */</pre>
</section>
<footer>Original designs 1978: Hermann Hecht (Céilí), William Curran (Carrick, Kilfane), Jarlath Hayes (Tuam Uncial).
Digitised 2026 from the printed specimen sheet; glyphs not shown on the sheet, and the italic and bold styles, were drawn to match each face.<br>
Fonts copyright 2026 Dan Drayne, released under the <a href="OFL.txt">SIL Open Font License 1.1</a>: use them for anything,
share and adapt them, but don’t sell the fonts on their own.</footer>
</main>
<script>
document.querySelectorAll('.face .tester').forEach(t => {{
  const sample = t.querySelector('.sample');
  const size = t.querySelector('.size');
  const boxes = t.querySelectorAll('input[data-feat]');
  const picks = t.querySelectorAll('.picks input');
  const apply = () => {{
    sample.style.fontSize = size.value + 'px';
    const st = ([...picks].find(p => p.checked) || {{ value: 'Regular' }}).value;
    sample.style.fontWeight = st.includes('Bold') ? 700 : 400;
    sample.style.fontStyle = st.includes('Italic') ? 'italic' : 'normal';
    const feats = [...boxes].map(b => `"${{b.dataset.feat}}" ${{b.checked ? 1 : 0}}`);
    sample.style.fontFeatureSettings = feats.join(', ');
  }};
  size.addEventListener('input', apply); [...boxes, ...picks].forEach(b => b.addEventListener('change', apply)); apply();
}});
</script>
</body>
</html>'''


if __name__ == '__main__':
    out = sys.argv[1]
    open(out, 'w').write(page())
    print('wrote', out)
