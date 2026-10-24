"""Proof a family's styles together: big letters, a paragraph mixing the styles, and a waterfall.

usage: python famproof.py FONTDIR face out.png
"""
import html, os, sys
from playwright.sync_api import sync_playwright
from build2 import FONTS, FAMILY_STYLES
fontdir, key, out = sys.argv[1], sys.argv[2], sys.argv[3]
ps = FONTS[key]['ps']; fam = 'T'
css = ''
for st in FAMILY_STYLES[key]:
    w = 700 if 'Bold' in st else 400; it = 'italic' if 'Italic' in st else 'normal'
    css += (f'@font-face{{font-family:"{fam}";src:url("file://{fontdir}/{ps}-{st.replace(" ", "")}.woff2") format("woff2");'
            f'font-weight:{w};font-style:{it}}}')
big = 'abcdefghijklm nopqrstuvwxyz' if FONTS[key]['unicase'] else 'Kilfane Hamburgefonts ÁÉÍ'
text = ('Is fearr Gaeilge bhriste ná Béarla cliste. <b>Tír gan teanga, tír gan anam.</b> '
        '<i>Ní neart go cur le chéile</i>, agus <b><i>ar scáth a chéile a mhaireann na daoine</i></b>. '
        'Céilí mór anocht i dTuaim: ceol ⁊ craic, 1978–2026.')
rows = ''.join(f'<div class="big" style="font-weight:{700 if "Bold" in st else 400};font-style:{"italic" if "Italic" in st else "normal"}">'
               f'<span class="tag">{st}</span>{html.escape(big)}</div>' for st in FAMILY_STYLES[key])
doc = (f'<!doctype html><meta charset=utf-8><style>{css} body{{margin:24px 30px;background:#fbf8f1;color:#171513;width:1560px;font-synthesis:none}}'
       f'.big{{font-family:"{fam}";font-size:96px;line-height:1.22;white-space:nowrap}}'
       '.tag{display:inline-block;width:150px;font:600 15px Helvetica,Arial,sans-serif;color:#998f82;vertical-align:middle}'
       f'p{{font-family:"{fam}";font-size:34px;line-height:1.45;max-width:1450px;margin:18px 0}}'
       f'.water span{{display:block;font-family:"{fam}";white-space:nowrap}}</style>{rows}<p>{text}</p>'
       '<div class="water">' + ''.join(f'<span style="font-size:{s}px">{s}px · {text[:90]}</span>' for s in (14, 18, 24)) + '</div>')
path = out.replace('.png', '.html'); open(path, 'w').write(doc)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium'); pg = b.new_page(viewport={'width': 1620, 'height': 600})
    pg.goto('file://' + path); pg.wait_for_timeout(700); pg.screenshot(path=out, full_page=True); b.close()
print(out)
