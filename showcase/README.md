# The showcase site

A one-page site for the four faces: the 1978 results, the flyer as evidence, a world
for each face with a toy only that face could have, the original-source research
beside the release, a tester, a shopfront, every character, the designers and downloads.

| Part | File | What it does |
|---|---|---|
| Hero | `js/hero.js` | Every letter of *ceithre chló* is a cell that changes face under the pointer, printed in two overprinting inks |
| Results | `js/board.js` | The 1978 awards as the competition brochure gives them, each name fitted to its row |
| Evidence | `js/evidence.js` | The scan at its real pixels, with segmentation boxes, traced points, overlap scores and a wipe between print and font drawn over it |
| Céilí | `js/ceili.js` | Letters dance to a synthesised bodhrán (jig, reel, slip jig, polka) and change into their alternates on the beat |
| Carrick | `js/carrick.js` | *Carraig*, rock: letters fall and stack into a drystone wall (Matter.js physics on each letter's hull) |
| Kilfane | `js/kilfane.js` | Rub letters down from transfer sheet S53909 onto a cutting mat, by hand or by typing a word; accents come from the sheet's loose marks |
| Tuam Uncial | `js/tuam.js` | An insular page: counters filled with pigment, red-lead dots traced round the initial, generated knotwork |
| Research | `js/study.js` | Each face's latest original-source study beside the release: letters overprinted in two inks, fit to each archive source, and the collisions the study's spacing removes |
| Tester | `js/tester.js` | Type in any face and style, with the stylistic sets, or in the research studies |
| Shopfront | `js/shopfront.js` | Your name gilded over a painted Irish shopfront, in any face and paint |
| Characters | `js/glyphs.js` | Every character with its Unicode name, beside the same character in the other faces, its alternates and the study's drawing |

## Build and preview

```sh
make showcase    # build/showcase, plus build/showcase-artifact (fonts inlined)
make serve       # build and serve at http://localhost:8377
SITE_URL=https://example.org make showcase   # absolute link-preview addresses
```

`scripts/showcase.py` copies this folder and adds what it reads from the rest of the
repository, so the site always shows the current release and research:

- the web fonts from `fonts/woff2/`, and a fonts-only ZIP for the download button
- the flyer scan from `sources/flyer.jpg`
- `data/site.json`: each face's styles, character map and stylistic sets, Unicode
  names, the per-glyph overlap scores from `docs/validation/flyer-glyph-audit.md`,
  where each face sits on the flyer, and the research studies
- `data/traced.json`: every traced flyer glyph as an SVG path in scan pixels
- `img/social.png`, `img/icon.svg`, `img/apple-touch-icon.png`, drawn from the fonts

Research studies are found under `research/`: any `fonts/*Study N-Regular.otf` with
its WOFF2, the round's `metrics.json`, `audit-metrics.json` or `mark-audit-metrics.json`,
`spacing-adjustments.json` and `pair-audit.json`. Exploratory proposals that the
research does not accept (such as `brochure-proposal-metrics.json`) are not shown.
Only font files and numbers are used: no archive pixels (see `research/RIGHTS.md`).

Nothing in this folder is generated. There is no bundler: the page is plain HTML, CSS
and ES modules, and each part's script loads only when it scrolls near. CI checks
that the site builds.

## Checks used while building it

Screenshots at 1440 and 390 px wide, in light and dark mode and with reduced motion;
the toys exercised in a browser; an axe-core audit with every section loaded (no
violations in either theme); and the page weight (about 400 KB before the first scroll).

## Vendored

- `vendor/matter.min.js`: Matter.js 0.20.0 (MIT, Liam Brummitt and contributors; `vendor/matter-LICENSE.txt`)
- `vendor/fonts/`: Archivo and Fragment Mono from Fontsource (SIL Open Font License 1.1)
