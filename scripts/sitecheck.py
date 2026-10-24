"""Drive the test page in Chromium like a visitor and screenshot each step."""
import paths
import sys
from playwright.sync_api import sync_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8080/'
OUT = os.path.join(paths.BUILD, 'ui')
import os; os.makedirs(OUT, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium', args=['--no-proxy-server'])
    for name, vw, vh, scheme in (('desk', 1360, 900, 'light'), ('phone', 390, 844, 'light'), ('dark', 1360, 900, 'dark')):
        ctx = b.new_context(viewport={'width': vw, 'height': vh}, color_scheme=scheme, device_scale_factor=1)
        pg = ctx.new_page(); errs = []
        pg.on('console', lambda m: errs.append(m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
        pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
        pg.on('requestfailed', lambda r: errs.append('failed ' + r.url))
        pg.goto(URL); pg.wait_for_timeout(1800)
        pg.screenshot(path=f'{OUT}/{name}_hero.png')
        # sheet: pick a face, rub letters down, type
        pg.locator('#sheet').scroll_into_view_if_needed(); pg.wait_for_timeout(200)
        pg.click('[data-tabs="sheet"] .tab[data-face="ceili"]')
        pg.click('#board-clear')
        for ch in 'ceol':
            pg.locator('#sheet-body .sg', has_text=ch).first.click(); pg.wait_for_timeout(60)
        pg.click('#board-paper'); pg.keyboard.type(' agus ċraic'); pg.wait_for_timeout(700)
        pg.locator('#sheet').screenshot(path=f'{OUT}/{name}_sheet.png')
        board_text = pg.evaluate("document.getElementById('board-line').textContent")
        # characters: Kilfane, the flyer filter, first glyph, compare at 50%
        pg.locator('#characters').scroll_into_view_if_needed(); pg.wait_for_timeout(600)
        pg.click('[data-tabs="chars"] .tab[data-face="kilfane"]'); pg.wait_for_timeout(900)
        pg.click('.chip[data-filter="flyer"]'); pg.wait_for_timeout(300)
        n_chars = pg.locator('#chars .cg').count()
        pg.locator('#chars .cg').nth(2).click(); pg.wait_for_timeout(300)
        rng = pg.locator('#inspect input[type="range"]')
        if rng.count():
            rng.evaluate("r => { r.value = 50; r.dispatchEvent(new Event('input')); }")
        pg.wait_for_timeout(300)
        pg.locator('#characters').screenshot(path=f'{OUT}/{name}_chars.png')
        # accents
        pg.locator('#accents').scroll_into_view_if_needed(); pg.wait_for_timeout(1200)
        pg.locator('#accents').screenshot(path=f'{OUT}/{name}_accents.png')
        sw = pg.evaluate('document.documentElement.scrollWidth')
        print(f'{name}: scrollWidth {sw} (viewport {vw}) | board "{board_text}" | flyer glyphs listed {n_chars} | errors {errs}')
        ctx.close()
    b.close()
