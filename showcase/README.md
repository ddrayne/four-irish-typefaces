# The showcase site

A one-page site for the four faces: the 1978 results, the flyer as evidence (scroll
through segmentation, tracing, scoring, a wipe between print and font, and the transfer
sheet), a world for each face with a toy only that face could have, a tester, every
character, the designers and downloads.

| Part | File | What it does |
|---|---|---|
| Hero | `js/hero.js` | Every letter of *ceithre chló* is a cell that changes face under the pointer, printed in two overprinting inks |
| Results | `js/board.js` | The 1978 placings, each name fitted to its row |
| Evidence | `js/evidence.js` | The scan at its real pixels with the traced outlines, points, overlap scores and a wipe drawn over it |
| Céilí | `js/ceili.js` | Letters dance to a synthesised bodhrán (jig, reel, slip jig, polka) and change into their alternates on the beat |
| Carrick | `js/carrick.js` | *Carraig*, rock: letters fall and stack into a drystone wall (Matter.js physics on each letter's hull) |
| Kilfane | `js/kilfane.js` | Rub letters down from transfer sheet S53909 onto a cutting mat |
| Tuam Uncial | `js/tuam.js` | An insular page: counters filled with pigment, red-lead dots traced round the initial, generated knotwork |
| Tester, glyphs | `js/tester.js`, `js/glyphs.js` | Type in any face and style, with the stylistic sets; every character with its Unicode name |

## Build and preview

```sh
make showcase    # build/showcase, plus build/showcase-artifact (fonts inlined)
make serve       # build and serve at http://localhost:8377
```

`scripts/showcase.py` copies this folder and adds what it reads from the rest of the
repository, so the site always shows the current release:

- the web fonts from `fonts/woff2/`
- the flyer scan from `sources/flyer.jpg`
- `data/site.json`: each face's styles, character map and stylistic sets, Unicode
  names, the per-glyph overlap scores from `docs/validation/flyer-glyph-audit.md`, and
  where each face sits on the flyer
- `data/traced.json`: every traced flyer glyph as an SVG path in scan pixels, with its points

Nothing in this folder is generated. There is no bundler: the page is plain HTML, CSS
and ES modules, and each part's script loads only when it scrolls near.

## Vendored

- `vendor/matter.min.js`: Matter.js 0.20.0 (MIT, Liam Brummitt and contributors)
- `vendor/fonts/`: Archivo and Fragment Mono from Fontsource (SIL Open Font License 1.1)
