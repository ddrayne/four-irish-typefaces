# The showcase site

A one-page site for the four faces: the 1978 results, the flyer they were digitised from,
a world for each face with a toy only that face could have, a poster maker, a tester, a
shopfront, every character, the designers and downloads. Work in progress from the archive
sits closed beside each release. The copy keeps to the faces and their history; how they
were digitised is written up in the repository rather than sold on the page.

It is designed like a risograph poster run: big type, flat strong colour, and headings
printed in two inks a little out of register (`[data-ov]`: main.js adds a copy of the words,
hidden from screen readers, that the stylesheet prints beneath in a second ink). Each face's
plate and the poster maker's blue wall are art-directed, the same in both themes.

| Part | File | What it does |
|---|---|---|
| Hero | `js/hero.js` | Every letter of *ceithre chló* is a cell that changes face under the pointer, printed in two overprinting inks over a third-ink sun |
| Results | `js/board.js` | The 1978 awards as the competition brochure gives them, a band in each face's colours, each name fitted to its row |
| The flyer | `js/evidence.js` | The scan at its real pixels, with the outlines and their points drawn over it and a wipe between print and font |
| Céilí | `js/ceili.js` | Choose your letters: tap a letter to cycle its other forms (insular r and s, uncial a and n, the second a, d, e, j, l and v), or set the whole line in one hand; the line is real text, so it keeps the face's own spacing |
| Carrick | `js/carrick.js` | *Carraig*, rock: letters tumble in as stones (Matter.js physics on each letter's hull) and settle into courses of set type, each where the font's spacing and kerning put it; a stone knocked out finds its way back, and Shake brings the wall down |
| Kilfane | `js/kilfane.js` | Capitals and three forms: a line set large on a cutting mat over its cap height, x-height and baseline, in its standard, Roman (ss01) or insular (ss02) forms, in four styles, and in capitals as Irish writes them (nÓG); each change is rubbed down letter by letter, as from a transfer sheet |
| Tuam Uncial | `js/tuam.js` | An insular page: counters filled with pigment, red-lead dots traced round the initial, generated knotwork |
| Studies | `js/study.js` | Each face's latest study from the archive beside the release, closed until opened, its letters overprinted in two inks |
| Posters | `js/poster.js` | A two-ink risograph poster: ten ready-made posters with Irish phrases to start from, ten layouts, a face, style and alternates for each ink, fourteen inks, six papers, six sheet sizes, three finishes; saved as a PNG at print size, or as clean vectors (SVG, and a PDF with each ink's plate on its own page) |
| Tester | `js/tester.js` | Type in any face and style, with the stylistic sets, or in the research studies |
| Shopfront | `js/shopfront.js` | Your name gilded over a painted Irish shopfront, in any face and paint |
| Characters | `js/glyphs.js` | Every character with its Unicode name, beside the same character in the other faces, its alternates and the study's drawing |

### The poster maker

The posters are set from the fonts' own outlines (`data/outlines/`) rather than by the
browser, so the preview, the PNG, the SVG and the PDF are one drawing:

- `js/poster-type.js` loads a style's outlines and sets lines of type: advance widths, the
  kern feature's pairs and the stylistic sets, as the fonts define them
- `js/poster-layouts.js` the inks, papers, sheet sizes and finishes; the ten layouts, each
  drawing two plates (fills, and cuts out of what a plate has printed); the ready-made posters
- `js/poster-render.js` prints the plates: on a canvas as a risograph would (grain, uneven
  inking, misregistration, the inks multiplied on the paper), or as SVG or PDF vectors with
  no grain. The PDF is written by hand (PDF 1.4: transparency groups for the multiplied inks,
  luminosity masks for the cut-outs, streams deflated with `CompressionStream` where there is one)

The PNG is printed at up to 300 dpi, and never more than 16.7 megapixels, the largest
canvas every browser will draw (so A3 comes out at 293 dpi and A2 at 207). The preview
viewer hides the save buttons (`data-no-downloads`), as it cannot save files.

## Build and preview

```sh
make showcase    # build/showcase, plus build/showcase-artifact (fonts inlined)
make serve       # build and serve at http://localhost:8377
SITE_URL=https://example.org make showcase   # absolute link-preview addresses
```

`scripts/showcase.py` copies this folder and adds what it reads from the rest of the
repository, so the site always shows the current release and research:

- the web fonts from `fonts/woff2/`
- the flyer scan from `sources/flyer.jpg`
- `data/site.json`: each face's styles, character map and stylistic sets, Unicode
  names, the per-glyph overlap scores from `docs/validation/flyer-glyph-audit.md`,
  where each face sits on the flyer, and the research studies
- `data/release.json`: the same glyphs of each released Regular, registered on the scan as the flyer audit
  registers them (`docs/validation/flyer-registration.json`), with each one's overlap with the print
- `data/traced.json`: every traced flyer glyph as an SVG path in scan pixels
- `data/outlines/<Family>-<Style>.json`: every glyph of each released style as outlines,
  with its advance and ink bounds, the flattened kerning and the stylistic sets, for the
  poster maker (read from `fonts/otf/`)
- `img/social.png`, `img/icon.svg`, `img/apple-touch-icon.png`, drawn from the fonts

The download buttons link to the GitHub release of the current version.

Research studies are found under `research/`: any `fonts/*Study N-Regular.otf` with
its WOFF2, the round's `metrics.json`, `audit-metrics.json` or `mark-audit-metrics.json`,
`spacing-adjustments.json` and `pair-audit.json`. Exploratory proposals that the
research does not accept (such as `brochure-proposal-metrics.json`) are not shown.
Only font files and numbers are used: no archive pixels (see `research/RIGHTS.md`).

## Publishing

`make deploy-site` (`scripts/deploy_site.py`) assembles `build/deploy`: the built site, an
nginx configuration (caching, a content security policy) and a Dockerfile. The fonts are for
the site's own pages: nothing is offered for other sites to link, and the downloads are
GitHub release assets. After the tests pass on `main`, CI pushes it to the `deploy` branch,
and Coolify serves https://irish-typefaces.apps.drayne.xyz/ from that branch, rebuilding on
every push.

Nothing in this folder is generated. There is no bundler: the page is plain HTML, CSS
and ES modules, and each part's script loads only when it scrolls near. CI checks
that the site builds.

## Checks used while building it

Screenshots at 1440 and 390 px wide, in light and dark mode and with reduced motion;
the toys exercised in a browser; the poster maker driven through every ready-made poster,
size, paper and finish, its SVGs rendered in Chromium and its PDFs in Poppler; the kerning
in `data/outlines/` checked against HarfBuzz; an axe-core audit with every section loaded
(no violations in either theme); and the page weight before the first scroll.

## Vendored

- `vendor/matter.min.js`: Matter.js 0.20.0 (MIT, Liam Brummitt and contributors; `vendor/matter-LICENSE.txt`)
- `vendor/fonts/`: Archivo and Fragment Mono from Fontsource (SIL Open Font License 1.1)
