"""Write the package stylesheet: one @font-face per style, so <b>, <i> and font-weight / font-style
pick the real drawings and browsers never paint a synthetic bold or slant.

usage: make_css.py OUT.css
"""
import sys
from build2 import FONTS, FAMILY_STYLES, VERSION

ORDER = ['kilfane', 'tuam', 'carrick', 'ceili']
NAMES = {k: [FONTS[k]['family']] for k in ORDER}
NAMES['ceili'] = [FONTS['ceili']['family'], 'Ceili Digital']


def face(name, ps, style, weight):
    file = f'{ps}-{style.replace(" ", "")}'
    return (f'@font-face {{\n  font-family: "{name}";\n'
            f'  src: url("../fonts/woff2/{file}.woff2") format("woff2"),\n'
            f'       url("../fonts/woff/{file}.woff") format("woff");\n'
            f'  font-weight: {weight};\n  font-style: {"italic" if "Italic" in style else "normal"};\n'
            f'  font-display: swap;\n}}\n')


def css():
    out = [f'''/*
 * Four Irish Typefaces: web fonts, version {VERSION}
 * Kilfane Digital, Tuam Uncial Digital, Carrick Digital and Céilí Digital: independent
 * digitisations of Kilfane, Tuam Uncial, Carrick and Céilí, winners of the 1978
 * "Design an Irish Typeface" competition (Letraset, Kilkenny Design Workshops,
 * D. O'Sullivan Graphic Supplies). Digitised 2026 from the printed specimen sheet.
 * Copyright 2026 Dan Drayne. Licensed under the SIL Open Font License 1.1 (OFL.txt,
 * https://openfontlicense.org).
 *
 * Styles: Kilfane Digital and Céilí Digital have Regular, Italic, Bold and Bold Italic;
 * Carrick Digital and Tuam Uncial Digital, already black, have Regular and Italic. The 1978 sheet showed only the
 * regulars: the italics and bolds were drawn in 2026 from them.
 *
 * Usage:  <link rel="stylesheet" href="css/four-irish-typefaces.css">
 *         h1 {{ font-family: "Kilfane Digital", serif; }}
 *         <b> and <i> (or font-weight: 700 / font-style: italic) select the real styles.
 * Paths below are relative to this file; keep the fonts/ folder beside css/.
 */
''']
    for key in ORDER:
        cfg = FONTS[key]; styles = FAMILY_STYLES[key]; names = NAMES[key]
        has_bold = 'Bold' in styles
        if key == 'ceili':
            out.append('/* Céilí Digital is declared twice so it works with or without the accents in your CSS. */\n')
        if not has_bold:
            out.append(f'/* {names[0]} is already black: its one weight answers every font-weight (400 900),\n'
                       '   so bold text stays in the drawn weight instead of a smeared synthetic bold. */\n')
        for name in names:
            for st in styles:
                w = ('700' if 'Bold' in st else '400') if has_bold else '400 900'
                out.append(face(name, cfg['ps'], st, w))
        out.append('\n')
    out.append('''/* Convenience classes */
.kilfane     { font-family: "Kilfane Digital", serif; }
.tuam-uncial { font-family: "Tuam Uncial Digital", serif; }
.carrick     { font-family: "Carrick Digital", serif; }
.ceili       { font-family: "Céilí Digital", "Ceili Digital", serif; }

/* Stylistic sets (Kilfane and Céilí also support "salt" for single-glyph alternates) */
.kilfane-roman-forms   { font-feature-settings: "ss01"; }  /* roman T Y d f l t y, pointed A */
.kilfane-insular-forms { font-feature-settings: "ss02"; }  /* insular D g, flat-topped S, flourished A */
.ceili-insular-r-s     { font-feature-settings: "ss01"; }  /* traditional Gaelic-script r and s */
.ceili-uncial-a-n      { font-feature-settings: "ss02"; }  /* uncial A and N shapes */
.ceili-alternates      { font-feature-settings: "ss03"; }  /* alternate a d e j l v */
''')
    return ''.join(out)


if __name__ == '__main__':
    open(sys.argv[1], 'w').write(css())
