"""A proof for review by eye: an A4 PDF of the release fonts, to print at actual size and mark up.

usage: python scripts/proof_sheet.py [--tester] [--out PDF]

With --tester, a short tester instead: one page per face (its letters, styles, a waterfall and text),
into build/proof/four-irish-typefaces-tester.pdf.

Every face in every style: letters and alternates, accents and signs, a waterfall and text blocks for
colour, spacing and kerning strings, the four together, and the design calls only an eye can settle,
each with boxes to tick. Set by Chromium in fonts/ttf (Chromium embeds CFF fonts in a PDF as Type 3
drawings, which some printers render poorly; TrueType goes in as a font), so it shows the release as built.
"""
import argparse, datetime, html, re, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
STUDY_TUAM = ROOT / 'research' / 'tuam-judgement' / 'fonts' / 'TuamUncialStudy3-Regular.ttf'

FACES = [
    dict(key='kilfane', name='Kilfane Digital', ps='KilfaneDigital', designer='William Curran', caps=True,
         display='Annála na gCeithre Máistrí',
         styles=['Regular', 'Italic', 'Bold', 'BoldItalic'], sets=[('ss01', 'Roman forms'), ('ss02', 'Insular forms')]),
    dict(key='carrick', name='Carrick Digital', ps='CarrickDigital', designer='William Curran', caps=False,
         display='Carraig agus cloch',
         styles=['Regular', 'Italic'], sets=[]),
    dict(key='tuam', name='Tuam Uncial Digital', ps='TuamUncialDigital', designer='Jarlath Hayes', caps=False,
         display='Tús maith leath na hoibre',
         styles=['Regular', 'Italic'], sets=[]),
    dict(key='ceili', name='Céilí Digital', ps='CeiliDigital', designer='Hermann Hecht', caps=False,
         display='Céilí mór anocht!',
         styles=['Regular', 'Italic', 'Bold', 'BoldItalic'],
         sets=[('ss01', 'Insular r and s'), ('ss02', 'Uncial A and N'), ('ss03', 'Alternate a d e j l v')]),
]

LOWER = 'abcdefghijklmnopqrstuvwxyz'
UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
FIGS = '0123456789 £$€&?!(;:)'
ACCENTS = ['áéíóú ÁÉÍÓÚ àèìòù ÀÈÌÒÙ âêîôû äëïöü', 'ãõñ åç ő ű ŵ ŷ ą ę ł ś ź ż č š ž ř ď ť ľ ğ ş ș ț']
DOTTED = 'ḃ ċ ḋ ḟ ġ ṁ ṗ ṡ ṫ  Ḃ Ċ Ḋ Ḟ Ġ Ṁ Ṗ Ṡ Ṫ  ⁊'
FIGURES = ['1978 · £24 · €5 · $3 · ¥9 · 50% · 3‰ · 12:30', '½ ¼ ¾ · x² y³ · Nº 1 · 1ª · #1 · @ · § ¶ † ‡ · © ® ™ · ° • …']
SIGNS = ['+ − × ÷ = ≠ ≈ ± < > ≤ ≥ ¬ ~ ^ |', '( ) [ ] { } ‹ › « » ‚ „ ‘ ’ “ ” \' " ¡ ¿', 'a-b a–b a—b · an, an. an; an: an! an? an…']
WATERFALL = 'Is fearr Gaeilge bhriste ná Béarla cliste.'
SIZES = [72, 48, 36, 24, 18, 14, 12, 10, 9, 8]
IRISH = ('Tógadh Brú na Bóinne timpeall 3200 RC, roimh phirimidí na hÉigipte. Scríobhadh Leabhar Cheanannais '
         'timpeall na bliana 800, agus tá sé i gColáiste na Tríonóide i mBaile Átha Cliath. Troideadh Cath Chluain '
         'Tarbh sa bhliain 1014, agus maraíodh Brian Bóramha ann. Chuir Mícheál Ó Cléirigh agus a chomhghleacaithe '
         'Annála na gCeithre Máistrí le chéile idir 1632 agus 1636.')
SHORT = 'Tógadh Brú na Bóinne timpeall 3200 RC, roimh phirimidí na hÉigipte. Scríobhadh Leabhar Cheanannais timpeall na bliana 800.'
OLD = 'Scríoḃaḋ Leaḃar Ċeanannais timpeall na bliana 800. Troideaḋ Caṫ Ċluain Tarḃ sa ḃliain 1014, ⁊ maraíoḋ Brian Bóraṁa ann.'
ENGLISH = ('In 1978 Letraset, the Kilkenny Design Workshops and D. O’Sullivan Graphic Supplies asked designers for '
           'an Irish typeface. Four were chosen and sold as dry-transfer lettering: Céilí by Hermann Hecht, '
           'Carrick and Kilfane by William Curran, and Tuam Uncial by Jarlath Hayes. “The quick brown fox jumps '
           'over the lazy dog” — 24 pounds (£24), 50% off?')
SPACING = [
    'nnanbncndnenfngnhninjnknlnmnnnonpnqnrnsntnunvnwnxnynzn',
    'oaobocodoeofogohoiojokolomonooopoqorosotouovowoxoyozo',
    'bh ch dh fh gh mh ph sh th · ae ai ao ea ei eo ia io iu oi ua ui · ach aidh each eadh igh',
    'i bhFrainc · na hÉireann · an tSlí · i gCorcaigh · i mBaile Átha Cliath · ár nAthair · i dTír Chonaill',
    'fa fe fi fo fu fá fé fí fó fú fh fl fb fk ff ft fr f. f, f’ f?',
    '‘an’ “an” d’fhan m’athair b’fhéidir Neil’s all” (an) [an] {an} an! an? an:',
]
CAPS_SPACING = [
    'HAHBHCHDHEHFHGHHHIHJHKHLHMHNHOHPHQHRHSHTHUHVHWHXHYHZH',
    'OAOBOCODOEOFOGOHOIOJOKOLOMONOOOPOQOROSOTOUOVOWOXOYOZO',
    'Ta Te To Tu Ty Tá Tó Th Va Ve Vo Ya Yo Fa Fe Fo Fh Pa Pe Po Ph Pi',
    'AV AW AY AT LT LV LY TY FV TW TI FI TÍ FÍ VÚ — TÍR NA nÓG · AVE · LAVA',
]

# The design calls a measurement cannot settle (research/*/README.md and judged-edits.json record each).
QUESTIONS = [
    dict(title='Tuam Uncial: the fada on í',
         note='The print’s fada is short and nearly flat, and at text sizes í could not be told from i (fíor and fior '
              'are different words). The release raises its right end, from 19° to 40°, keeping its width and place. '
              'Top: the release; bottom: as printed.',
         samples=[('tuam', 'Regular', 'fíor fior · sí si · mílí', 24), ('study', 'Regular', 'fíor fior · sí si · mílí', 24),
                  ('tuam', 'Regular', 'Bhí Brian Bóramha ina Ard-Rí ar Éirinn ó 1002 go 1014.', 11),
                  ('study', 'Regular', 'Bhí Brian Bóramha ina Ard-Rí ar Éirinn ó 1002 go 1014.', 11)]),
    dict(title='Céilí: the ampersand',
         note='The prints disagree: N46 and the flyer close the lower counter where the bowl’s end meets the diagonal; '
              'N45 leaves a hairline of paper. It is closed, as N46 draws it.',
         samples=[('ceili', 'Regular', '& &', 44), ('ceili', 'Regular', 'Pádraig & Bríd & Colm Cille', 16)]),
    dict(title='Céilí: the weight',
         note='N46’s and N45’s stems differ by about 10%; the weight is a calibration between them. '
              'Is the colour of the text right?',
         samples=[('ceili', 'Regular', SHORT, 10.5)]),
    dict(title='Tuam Uncial: the slits',
         note='Each slit keeps the print’s own width (20 to 33 units) rather than one shared width (about 27).',
         samples=[('tuam', 'Regular', 'abdgopq 690', 33)]),
    dict(title='Kilfane: the serifs',
         note='The serifs keep their traced variety; they could instead be redrawn to one master serif.',
         samples=[('kilfane', 'Regular', 'HIKLMNTU nhiklmu', 28)]),
    dict(title='Carrick: £ and $ at their printed height',
         note='N513 prints £ as tall as & ? ! and taller than the figures. The release keeps that height and only '
              'sets both signs on the baseline, where they had floated. The alternative is to scale them to the figures.',
         samples=[('carrick', 'Regular', '£24 · $3 · 1978 · £ & ? !', 28)]),
    dict(title='Figures that break the line',
         note='Carrick’s 8 stands taller, as both prints show; Tuam’s 4 and 7 drop below the baseline, as printed.',
         samples=[('carrick', 'Regular', '1978 · 2468', 28), ('tuam', 'Regular', '1974 · 4747', 28)]),
    dict(title='The ponc (dot of lenition)',
         note='Carrick and Tuam set it beside the ascender of ḃ (Tuam also ḋ), as Irish types often do; '
              'Kilfane and Céilí set it above.',
         samples=[(k, 'Regular', 'ḃeag ḋún ḟear ṡíl ṫú', 18) for k in ('kilfane', 'carrick', 'tuam', 'ceili')]),
    dict(title='Small figures in the Bolds',
         note='Superiors, fractions and ordinals are drawn lighter than full-size figures so their counters stay open. '
              'Heavy enough beside the Bold?',
         samples=[('kilfane', 'Bold', 'x² y³ ½ ¼ ¾ 1ª Nº 1978', 22), ('ceili', 'Bold', 'x² y³ ½ ¼ ¾ 1ª Nº 1978', 22)]),
]

CSS = '''
@page { size: A4; margin: 16mm 18mm 18mm 18mm; }
* { box-sizing: border-box; }
body { margin: 0; width: 174mm; color: #000; background: #fff; font: 8.5pt/1.35 "DejaVu Sans", "Liberation Sans", sans-serif; }  /* A4 less the margins: lines are fitted to it */
.page { break-after: page; }
.page:last-child { break-after: auto; }
h1 { font-size: 22pt; font-weight: 700; margin: 0 0 4mm; }
h2 { font-size: 7.5pt; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; margin: 6mm 0 1.5mm;
     border-top: .4pt solid #000; padding-top: 1.2mm; }
.facehead { display: flex; justify-content: space-between; align-items: baseline; border-bottom: .8pt solid #000;
            padding-bottom: 1.5mm; margin-bottom: 2mm; }
.facehead .t { font-size: 26pt; line-height: 1.1; white-space: nowrap; }
.facehead .m { font-size: 7.5pt; text-align: right; }
.lab { font-size: 6.5pt; color: #444; margin: 2.5mm 0 .3mm; }
.line { white-space: nowrap; overflow: hidden; line-height: 1.2; }
.fit { white-space: nowrap; line-height: 1.25; }
.display { margin: 3mm 0 1mm; line-height: 1.15; }
.para { line-height: 1.38; margin: 0 0 2.5mm; hyphens: manual; }
.wf { display: flex; align-items: baseline; gap: 3mm; }
.wf .sz { width: 9mm; flex: none; font-size: 6.5pt; color: #444; text-align: right; }
.wf .line { flex: 1; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; }
.q { border: .5pt solid #000; padding: 2mm 3mm; margin: 0 0 2.5mm; break-inside: avoid; }
.q .h { font-weight: 700; font-size: 9pt; }
.q .n { margin: .8mm 0 1.5mm; }
.q .ticks { margin-top: 1.5mm; font-size: 8pt; }
.box { display: inline-block; width: 3.2mm; height: 3.2mm; border: .6pt solid #000; vertical-align: -0.6mm; margin: 0 1mm 0 4mm; }
.box:first-child { margin-left: 0; }
.notes { border-bottom: .4pt solid #888; height: 6mm; }
.rule { position: relative; width: 100mm; height: 5mm; border-bottom: .6pt solid #000; margin: 2mm 0 1mm; }
.rule i { position: absolute; bottom: 0; width: 0; height: 2mm; border-left: .6pt solid #000; }
ul { margin: 1mm 0 0 4mm; padding: 0; } li { margin: .6mm 0; }
'''


def esc(s):
    return html.escape(s, quote=False)


def fam(key, style):
    return f'proof-{key}-{style}'


def setin(key, style, text, pt, cls='line', feat=None):
    f = f"font-family:'{fam(key, style)}';font-size:{pt}pt" + (f";font-feature-settings:'{feat}' 1" if feat else '')
    return f'<div class="{cls}" style="{f}">{esc(text)}</div>'


def face_pages(fc):
    k, rs = fc['key'], fc['styles']
    head = (f'<div class="facehead"><span class="t" style="font-family:\'{fam(k, "Regular")}\'">{esc(fc["name"])}</span>'
            f'<span class="m">{esc(fc["designer"])}, 1978<br>{" · ".join(s.replace("BoldItalic", "Bold Italic") for s in rs)}</span></div>')
    pages = []
    # 1. letters in every style, and the alternates
    body = [head, '<h2>Letters</h2>']
    for st in rs:
        body.append(f'<div class="lab">{st.replace("BoldItalic", "Bold Italic")}</div>')
        for t in ([LOWER, UPPER] if fc['caps'] else [LOWER]) + [FIGS]:
            body.append(setin(k, st, t, 34, 'fit'))
    if fc['sets']:
        body.append('<h2>Stylistic sets (Regular)</h2>')
        for tag, label in fc['sets']:
            body.append(f'<div class="lab">{tag} · {esc(label)}</div>')
            body.append(setin(k, 'Regular', LOWER + (' ' + UPPER if fc['caps'] else ''), 28, 'fit', tag))
    pages.append(body)
    # 2. accents, dotted letters, figures and signs (Regular, and Bold where there is one)
    body = [head]
    for st in [s for s in ('Regular', 'Bold') if s in rs]:
        body.append(f'<h2>Accents, figures and signs · {st}</h2>')
        for t in ACCENTS + [DOTTED] + FIGURES + SIGNS:
            body.append(setin(k, st, t, 26, 'fit'))
    pages.append(body)
    # 3. waterfall and text blocks
    body = [head, '<h2>Waterfall · Regular</h2>']
    for pt in SIZES:
        body.append(f'<div class="wf"><span class="sz">{pt} pt</span>{setin(k, "Regular", WATERFALL, pt)}</div>')
    body.append('<h2>Text · Regular</h2>')
    for pt in (9, 10.5, 12):
        body.append(f'<div class="lab">{pt} pt</div>')
        body.append(setin(k, 'Regular', IRISH + (' ' + OLD if pt < 12 else ''), pt, 'para'))
    pages.append(body)
    # 4. every style in text
    body = [head, '<h2>Every style in text · 10.5 pt</h2>', '<div class="lab">Regular</div>',
            setin(k, 'Regular', ENGLISH, 10.5, 'para')]
    for st in rs:
        body.append(f'<div class="lab">{st.replace("BoldItalic", "Bold Italic")}</div>')
        body.append(setin(k, st, IRISH, 10.5, 'para'))
    pages.append(body)
    # 5. spacing and kerning strings
    body = [head]
    for st in [s for s in ('Regular', 'Bold') if s in rs]:
        body.append(f'<h2>Spacing and kerning · {st}</h2>')
        for t in SPACING + (CAPS_SPACING if fc['caps'] else []):
            body.append(setin(k, st, t, 18, 'fit'))
    pages.append(body)
    return pages


def font_faces():
    faces = []
    for fc in FACES:
        for st in fc['styles']:
            src = (ROOT / 'fonts' / 'ttf' / f'{fc["ps"]}-{st}.ttf').as_uri()
            faces.append(f"@font-face{{font-family:'{fam(fc['key'], st)}';src:url('{src}')}}")
    faces.append(f"@font-face{{font-family:'{fam('study', 'Regular')}';src:url('{STUDY_TUAM.as_uri()}')}}")
    return ''.join(faces)


def document(title, pages):
    out = ''.join(f'<section class="page">{"".join(p)}</section>' for p in pages)
    return (f'<!doctype html><html><head><meta charset="utf-8"><title>{esc(title)}</title>'
            f'<style>{font_faces()}{CSS}</style></head><body>{out}</body></html>')


def build_tester_html(version, commit, today):
    """One page per face: its name, a display line, letters, every style, a waterfall and text."""
    pages = []
    for fc in FACES:
        k, rs = fc['key'], fc['styles']
        label = lambda st: st.replace('BoldItalic', 'Bold Italic')
        body = [f'<div class="facehead"><span class="t" style="font-family:\'{fam(k, "Regular")}\'">{esc(fc["name"])}</span>'
                f'<span class="m">{esc(fc["designer"])}, 1978 · digitised from the originals<br>'
                f'{" · ".join(label(s) for s in rs)} · version {esc(version)}</span></div>',
                setin(k, 'Regular', fc['display'], 56, 'fit display')]
        body.append('<h2>Letters</h2>')
        for t in ([LOWER, UPPER] if fc['caps'] else [LOWER]) + [FIGS, DOTTED]:
            body.append(setin(k, 'Regular', t, 24, 'fit'))
        body.append('<h2>Styles</h2>')
        for st in rs:
            body.append(f'<div class="lab">{label(st)}</div>')
            body.append(setin(k, st, WATERFALL, 18, 'fit'))
        body.append('<h2>Sizes</h2>')
        for pt in (36, 24, 18, 14, 11, 9):
            body.append(f'<div class="wf"><span class="sz">{pt} pt</span>{setin(k, "Regular", SHORT, pt)}</div>')
        body.append('<h2>Text</h2>')
        body.append(setin(k, 'Regular', IRISH, 10.5, 'para'))
        body.append(setin(k, 'Regular', ENGLISH, 9, 'para'))
        pages.append(body)
    return document('Four Irish Typefaces tester', pages)


def build_html(version, commit, today):
    pages = []
    # cover
    ticks = ''.join(f'<i style="left:{x}mm"></i>' for x in range(0, 101, 10))
    toc = ''.join(f'<li>{esc(fc["name"])}: letters, accents and signs, waterfall and text, styles and spacing</li>' for fc in FACES)
    pages.append([
        '<h1>Four Irish Typefaces: proof for review</h1>',
        f'<p>Version {esc(version)} (commit {esc(commit)}), {esc(today)}. Céilí Digital, Carrick Digital, Kilfane Digital '
        'and Tuam Uncial Digital, digitised from the 1978 originals.</p>',
        '<h2>Print at actual size</h2>',
        '<p>Print on A4 at 100% (“actual size”), not “fit to page”. This rule should measure 100 mm:</p>',
        f'<div class="rule">{ticks}</div>',
        '<h2>What to look for</h2>',
        '<ul><li>In the text blocks, an even grey: a letter that looks darker, lighter, bigger or smaller than its neighbours.</li>'
        '<li>Spacing: pairs that clot or gap in real words, and anything uneven in the n and o strings.</li>'
        '<li>Accents and dots: placement, size, clearance from the letter and from the line above.</li>'
        '<li>Consistency: figures, punctuation, quotes and signs that belong together, and each Italic and Bold against its Regular.</li>'
        '<li>Outlines at display size: bumps, flats, kinks, joins that are not clean.</li>'
        '<li>The questions on the last pages: the design calls that only an eye can settle.</li></ul>',
        '<h2>Contents</h2>', f'<ul>{toc}<li>The four together</li><li>Questions</li></ul>',
        '<h2>Notes</h2>', ''.join('<div class="notes"></div>' for _ in range(6)),
    ])
    for fc in FACES:
        pages += face_pages(fc)
    # the four together
    body = ['<h1>The four together</h1>', '<h2>Display · Regular</h2>']
    for fc in FACES:
        body.append(setin(fc['key'], 'Regular', 'Cath Chluain Tarbh, 1014', 30, 'fit'))
    body.append('<h2>Text · every style · 10 pt</h2>')
    for fc in FACES:
        for st in fc['styles']:
            body.append(f'<div class="lab">{esc(fc["name"])} {st.replace("BoldItalic", "Bold Italic")}</div>')
            body.append(setin(fc['key'], st, SHORT, 10, 'para'))
    pages.append(body)
    # questions
    body = ['<h1>Questions</h1>', '<p>Each is a call the evidence leaves open. Tick one and add a note if you like.</p>']
    for i, q in enumerate(QUESTIONS, 1):
        sm = ''.join(setin(k, st, t, pt, 'para' if pt < 14 else 'fit') for k, st, t, pt in q['samples'])
        body.append(f'<div class="q"><div class="h">{i}. {esc(q["title"])}</div><div class="n">{esc(q["note"])}</div>{sm}'
                    '<div class="ticks"><span class="box"></span>keep as it is<span class="box"></span>change'
                    '<span class="box"></span>not sure</div><div class="notes"></div></div>')
    pages.append(body)
    return document('Four Irish Typefaces proof', pages)


FIT = '''() => {
  for (const el of document.querySelectorAll('.fit')) {
    let px = parseFloat(getComputedStyle(el).fontSize);
    while (el.scrollWidth > el.clientWidth + 0.5 && px > 6) { px *= 0.97; el.style.fontSize = px + 'px'; }
  }
}'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tester', action='store_true', help='one page per face instead of the full proof')
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    kind = 'tester' if args.tester else 'proof'
    args.out = args.out or ROOT / 'build' / 'proof' / f'four-irish-typefaces-{kind}.pdf'
    version = re.search(r"^VERSION = '([^']+)'", (ROOT / 'scripts' / 'build2.py').read_text(encoding='utf-8'), re.M).group(1)
    git = lambda *a: subprocess.run(['git', *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    commit = git('rev-parse', '--short', 'HEAD') + ('+' if git('status', '--porcelain', '--', 'fonts') else '')
    today = datetime.date.today().isoformat()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    page_html = args.out.with_suffix('.html')
    page_html.write_text((build_tester_html if args.tester else build_html)(version, commit, today), encoding='utf-8')
    footer = ('<div style="font:6.5pt sans-serif;width:100%;padding:0 18mm;display:flex;justify-content:space-between">'
              f'<span>Four Irish Typefaces · {kind} of {esc(version)} ({esc(commit)}) · {esc(today)} · CC0</span>'
              '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
    with sync_playwright() as p:
        exe = Path('/opt/pw-browsers/chromium')           # the preinstalled Chromium, as famproof.py uses
        browser = p.chromium.launch(**({'executable_path': str(exe)} if exe.exists() else {}))
        page = browser.new_page()
        page.emulate_media(media='print')
        page.goto(page_html.as_uri())
        # load every face before measuring: document.fonts.ready alone can resolve before a font is asked for
        page.evaluate('Promise.all([...document.fonts].map(f => f.load())).then(() => document.fonts.ready).then(() => true)')
        page.evaluate(FIT)
        page.pdf(path=str(args.out), prefer_css_page_size=True, print_background=True, display_header_footer=True,
                 header_template='<span></span>', footer_template=footer)
        browser.close()
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main()
