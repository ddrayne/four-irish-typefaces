# Four Irish Typefaces: digital revival, version 2.000

**Céilí · Carrick · Kilfane · Tuam Uncial**

These four faces won the 1978 "Design an Irish Typeface" competition, sponsored by
Letraset, Kilkenny Design Workshops and D. O'Sullivan Graphic Supplies. They were
sold as Letraset dry-transfer sheets.

These fonts were digitised from a scan of the competition's "Four Irish Typefaces"
flyer, then completed to roughly 400 characters each so they work on the web and in
any app. Further original-source research, a source register and the separately
named candidates are in [research/](research/README.md). The latest
[round 5](research/round-05/README.md) recovers Carrick's original mark components,
following [round 4](research/round-04/README.md) for Céilí's original punctuation.
[Round 3](research/round-03/README.md) reconstructs Tuam and Céilí from larger
original reproductions, following [round 2](research/round-02/README.md), which
improved Kilfane's marks, Carrick's outlines and pair spacing across all four faces.
Agents continuing this work should start with [the handoff](research/HANDOFF.md).
Modern revival fonts are excluded as design references for this research.

The flyer shows each face in a single style. From version 2.000 each face is also a family:
**Céilí** and **Kilfane** have Regular, Italic, Bold and Bold Italic, and **Carrick** and
**Tuam Uncial**, which are already black, have Regular and Italic. The italics and bolds are new
work, drawn in 2026 from the 1978 regulars (see *The 2026 styles* below). They are not
reconstructions of anything the designers drew.

The fonts are free to use under the SIL Open Font License 1.1 (see `OFL.txt`). A live
test page is at https://irish-typefaces.apps.drayne.xyz/.

Open `index.html` to see and test the fonts in a browser. It's a live type tester
with style pickers, stylistic-set toggles and character grids.

## What's new in 2.000

- **Families.** Twelve fonts instead of four: an italic for every face, and a bold and bold
  italic for Céilí and Kilfane. They are style-linked (name table, `OS/2` and `head` style bits,
  `STAT`), so `<b>` and `<i>`, Word's B and I buttons and design apps' style menus all pick the
  real drawings. All styles of a family share one set of line metrics, so changing style never
  moves a line. The stylesheet declares every style, and Carrick and Tuam Uncial answer every
  weight from 400 to 900, so browsers never paint a smeared synthetic bold over them.
- **Hairlines the scan lost** (Céilí). Where Hecht's pen turned to its thinnest, the toner barely
  registered: the trace pinched the e's crossbar, the e.alt1's crossbar and the b's join to a
  point, and left a crack at the top of the e's eye, where the scan shows grey, not paper. They
  now have a 5-unit hairline. A sweep of every traced glyph in all four faces found nothing else.
- **The section sign (§) in every face** is now two interlaced s whose middle bowls close into
  a clean loop. Before, it was two s stacked with an overlap, which turned to a blot in the
  heavy faces. Tuam Uncial's s is too black to interlace, so its § is drawn as one s-stroke and
  its half-turn.
- **Tuam Uncial's © and ®** keep their letters clear of the ring.
- **Checked as families.** Font Bakery's family checks (consistent underline, `STAT`, naming) pass
  with no FAIL or ERROR, and every bold was compared with its regular for lost counters, merged
  pieces and closed openings (see *Quality checks*).

## What was new in 1.200

- **Every glyph on the flyer was checked, one at a time.** Each of the 224 glyphs printed on the
  flyer was registered on the scan to an eighth of a pixel and compared with the print. The mean
  overlap (intersection over union of the filled shapes) is 0.948: Kilfane 0.953, Tuam Uncial
  0.952, Carrick 0.959, Céilí 0.928. The full table is `specimen/validation/flyer-glyph-audit.md`,
  and the test page shows every comparison.
- **The accents were on the flyer.** The cluster beside Kilfane's and Carrick's alphabets, which
  1.000 and 1.100 kept as a "knotwork ornament" at U+E000, is each transfer sheet's set of loose
  accents. Every accented letter in Kilfane and Carrick is now built from it: the fada, the dot of
  the séimhiú, the diaeresis, ring, circumflex, tilde and (in Kilfane) háček, plus the guillemets
  and the degree sign. The grave, double acute, breve and macron are made from those marks, and the
  dashes are drawn at the weight of the sheet's rules. U+E000 has been removed.
- **Céilí's h keeps more of Hecht's drawing.** Its stem and its wider shoulder are now the flyer's;
  only the right leg, which printed starved, comes from n, set on the outer edge of the printed
  leg. Its overlap with the print rose from 0.67 to 0.85.
- **Tuam Uncial's fadas** sit as close to their letters as they do on the flyer.
- **Smaller fixes.** The long s (ſ, and ß built from it) has a clean stem where f's crossbar was
  removed. Tuam's double acute is two short strokes instead of one merged bar. The small zeros in
  % and ‰ stay open in the heavy faces. A toner speck on Kilfane's em-dash rule was erased.
- **Line spacing.** Each face's default line height is now 1.2 em, set from the characters used in
  Irish, Scottish Gaelic, Welsh and Western European text, so tall stacked accents in other
  languages no longer spread every line apart. The Windows clipping metrics still cover every glyph.

## What was new in 1.100

- **Every traced letter was redrawn.** Version 1.000 followed the photocopy's edge to a tenth
  of a pixel, so at poster sizes its stems rippled and its curves were lumpy. The outlines are
  now drawn the way a type designer redraws from a scan: straight stems and bars are true
  straight lines, curves are smooth with few points, and corners and serifs stay sharp. Shape
  and weight still match the flyer (see the fidelity table below), and the fonts are about 20%
  smaller.
- **Céilí's h was rebuilt.** Its right leg is broken on the flyer. The stem is still Hecht's
  from the flyer; the shoulder and leg now come from his n, which they match by design.
- **A toner speck was removed** from Kilfane's O.

## Contents

| Path | What |
|---|---|
| `fonts/woff2/`, `fonts/woff/` | Web fonts. Use these on websites. |
| `fonts/otf/` | OpenType (CFF) for design and print apps |
| `fonts/ttf/` | TrueType, hinted with ttfautohint, for Windows and Office |
| `css/four-irish-typefaces.css` | Ready-made `@font-face` rules and stylistic-set classes |
| `index.html` | Web specimen and type tester; works offline or hosted |
| `docs/specimen/` | A4 PDF specimen (with a page per family) and one PNG per face |
| `docs/validation/` | Evidence: every flyer glyph against the scan, Font Bakery reports, overlays |
| `sources/` | The 1978 flyer scan and the outlines traced from it (one JSON file per face) |
| `scripts/` | The build: tracing, the styles, spacing, kerning, features, proofs, the test page |
| `site/` | Sources of the test page at irish-typefaces.apps.drayne.xyz |
| `tests/` | Checks every release must pass (`make test`) |
| `research/` | Original-source catalogue, evidence metadata, agent handoff and separately named research candidates |
| `OFL.txt`, `FONTLOG.txt` | The licence (SIL Open Font License 1.1) and the release history |

| Family | Styles | Code points | Glyphs | WOFF2 per style | Features |
|---|---|---|---|---|---|
| Kilfane | Regular, Italic, Bold, Bold Italic | 402 | 458 | 50–55 KB | kern, mark, ccmp, salt, aalt, ss01 Roman forms, ss02 Insular forms |
| Tuam Uncial | Regular, Italic | 398 | 262 | 30–31 KB | kern, mark, ccmp |
| Carrick | Regular, Italic | 400 | 262 | 33–34 KB | kern, mark, ccmp |
| Céilí | Regular, Italic, Bold, Bold Italic | 408 | 317 | 35–40 KB | kern, mark, ccmp, salt, aalt, ss01 Insular r and s, ss02 Uncial A and N, ss03 Alternate a d e j l v |

Files are named `Family-Style` (`Kilfane-BoldItalic.woff2`, `TuamUncial-Italic.otf`).

### Using them on a website

```html
<link rel="stylesheet" href="css/four-irish-typefaces.css">
<style>
  h1   { font-family: "Céilí", "Ceili", serif; }   /* both names work */
  .tag { font-family: "Carrick", serif; }
  .alt { font-family: "Kilfane", serif; font-feature-settings: "ss01"; }   /* roman forms */
</style>
<p class="alt">Tír gan teanga, <b>tír gan anam</b>, <i>mar a deirtear</i>.</p>
```

`<b>`, `<i>`, `font-weight: 700` and `font-style: italic` select the drawn styles. In Carrick and
Tuam Uncial bold text keeps the face's one (already black) weight; use the italic, colour or size
for emphasis there.

Install the OTF or TTF on your computer for desktop apps. Stylistic sets are under:

| App | Where to find stylistic sets |
|---|---|
| InDesign / Illustrator | OpenType → Stylistic Sets, or the Glyphs panel |
| Word | Font → Advanced → Stylistic sets |
| Affinity | Typography panel |
| Figma | Type details |
| CSS | `font-feature-settings` |

## The typefaces

| Face | Designer | 1978 result | Notes |
|---|---|---|---|
| **Céilí** | Hermann Hecht (1923–1985) | First prize (£250 and a silver medallion) | Light calligraphic unicase with insular forms and old-style figures. Used for National Library of Ireland booklets and reportedly the *Glenroe* titles. |
| **Carrick** | William Curran (1919–2016) | Highly Commended (£50) | A "chunky, lower case typeface". Fonts In Use lists it as having no uppercase. The name comes from *carraig*, "rock". |
| **Kilfane** | William Curran | Commended (£25) | Has upper and lower case, plus alternates. Named after a place in Co. Kilkenny. Reportedly used on the Series C Irish banknotes (Robert Ballagh, 1992–96). |
| **Tuam Uncial** | Jarlath Hayes (1924–2001) | Commended (£25) | Reportedly made by cutting up Helvetica Bold. Used on Clannad sleeves and shopfronts; the *Glenroe* attribution needs dated-frame verification. Hayes also designed the harp on Ireland's euro coins. |

Award wording follows the [original competition brochure](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/45/).

### The designers

- **William Curran.** Trained as a lithographic artist under Bernardus Romein, worked
  at Browne & Nolan, then freelanced. He was a calligrapher and drew the lettering for
  the school primer *An Príméar*. His archive, including the original Kilfane and
  Carrick drawings, went to the National Irish Visual Arts Library (NIVAL) in 2025.
- **Hermann Hecht.** Born in Bingen, he came to England in 1939. He was an assistant to
  Hans Schleger and later taught at Croydon College of Art. Custody of his Céilí
  drawings remains unverified; see the [research leads](research/README.md).

### The competition and the sheets

- **Brochure.** The competition brochure was designed by Liam Miller and printed at the
  Dolmen Press. NIVAL holds it.
- **Letraset sheets.** The flyer lists sheets S53909–S53916, two sizes per face. The
  codes don't fit Letraset's usual numbering, which suggests small "special sheet"
  runs (an inference). No catalogue listing has been found.

  | Face | Sheets and sizes |
  |---|---|
  | Kilfane | S53909 (30pt), S53910 (48pt) |
  | Tuam Uncial | S53911 (30pt), S53912 (48pt) |
  | Carrick | S53913 (36pt), S53914 (60pt) |
  | Céilí | S53915 (24pt), S53916 (42pt) |

- **Dates.** Some sources give 1973 or 1974 dates for the sheets, which is unresolved.
  Those dates may be copyright boilerplate.
- **Existing digitisation.** Earlier projects include Tuam Uncial's **Jarlath** revival
  by Signal Type Foundry and the Céilí-based **Caolchló GC** (2025). They are recorded
  for historical context in the [source register](research/source-register.json),
  and are not design references for the original-source reconstruction.

> **Sources and caveat.** This environment could run web searches but could not open
> pages or download images (network policy). The facts above come from search-result
> extracts, so treat them as reported and verify them before publication. Sources:
> Fonts In Use pages for [Céilí](https://fontsinuse.com/typefaces/205971/ceili),
> [Kilfane](https://fontsinuse.com/typefaces/248201/kilfane),
> [Carrick](https://fontsinuse.com/typefaces/248202/carrick),
> [Tuam Uncial](https://fontsinuse.com/typefaces/248203/tuam-uncial) and
> [Hermann Hecht](https://fontsinuse.com/type_designers/8591/hermann-hecht);
> [NIVAL brochure](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/45/);
> [NIVAL Curran archive](https://www.nival.ie/william-curran-archive/);
> [Dublin Inquirer (2020)](https://dublininquirer.com/2020/06/24/after-almost-50-years-a-renowned-irish-font-is-brought-into-the-digital-age);
> [Irish Times obituary of Jarlath Hayes](https://www.irishtimes.com/news/master-typographer-and-designer-1.313378);
> [Wikipedia: Jarlath Hayes](https://en.wikipedia.org/wiki/Jarlath_Hayes);
> [Signal: Jarlath](https://signalfoundry.com/typefaces/jarlath).

## Character set (about 400 code points per face)

- **Letters**
  - Latin A–Z and a–z.
  - All of Latin-1 and Latin Extended-A.
  - Romanian ș ț, Welsh ŵ ŷ ẁ ẃ ẅ ỳ, and Irish dot-above lenition ḃ ċ ḋ ḟ ġ ṁ ṗ ṡ ṫ.
  - Insular letters (Ꝺ ꝺ Ꝼ ꝼ Ᵹ ᵹ Ꞃ ꞃ Ꞅ ꞅ Ꞇ ꞇ) where the face has the form.
  - Tironian et ⁊, ı, ȷ, ĳ, ŀ, ŋ, ð, þ, ß and ſ.
- **Unicase faces.** Tuam Uncial, Carrick and Céilí have one case, as on the sheets.
  Capitals give the same forms as lower case, and capital I gives the dotless form ı.
- **Figures.** Céilí's are old-style, as drawn; the other three are lining. All faces
  have superiors ¹²³ and fractions ¼½¾.
- **Punctuation.** All ASCII and Latin-1 punctuation, curly quotes ‘ ’ “ ” ‚ „,
  guillemets « » ‹ ›, dashes, … • · † ‡ ′ ″ and ¡ ¿.
- **Symbols.** `# % ‰ * @ & § ¶ © ® ™ ° µ ¬ | ¦ \ _ ^ ~`, the currencies £ $ € ¢ ¥ ¤,
  and the maths signs + − × ÷ = ≠ ≈ < > ≤ ≥ ±. The maths signs share one width.
- **Combining marks.** U+0300–U+030C, U+0312 and U+0326–U+0328 have GPOS mark
  positioning, so decomposed text (e + ◌́) renders correctly. `ccmp` swaps i and j
  for their dotless forms under top marks.
- **Accents.** Kilfane's and Carrick's are the ones printed on their Letraset sheets (see
  *Details found on the sheet*). Tuam Uncial's fada is its own, from the flyer's á é í ó ú.
  Céilí's are drawn in its pen stroke.

## How they were made, and how faithful they are

### Source and tracing

1. **Source.** The flyer scan is 803 × 1125 px (about 97 dpi), so each letter was only
   20–35 px tall.
2. **Segmentation.** Each glyph was cut out and checked by eye. Letters that touched on
   the sheet were separated with watershed splits or measured cut lines.
3. **Tracing.**
   - Each glyph's ink is normalised to its local ink and paper levels and upsampled 8×.
   - The 50% edge is taken as a sub-pixel contour (marching squares).
4. **Redrawing** (new in 1.100).
   - Real corners are found from the edge direction just before and just after each point,
     so a toner bump is not mistaken for a corner.
   - Between corners, the edge is smoothed with a spline that penalises changes of
     curvature. Straight lines and circular arcs pass through it unchanged, while the
     photocopy's short ripples are removed.
   - Straight runs along the axes (stems, bars, flat serif faces) and long diagonals become
     true lines, snapped to vertical or horizontal within 2°. Where two lines meet, the
     corner is their exact intersection.
   - Everything else is fitted with as few cubic Béziers as the tolerance allows, joined
     smoothly to the lines, with points at the extrema.
   - Toner specks fused to a letter were erased before tracing, and the broken leg of one
     letter (Céilí's h) was replaced from the same face's n.
5. **Checking** (new in 1.200). Every traced glyph was registered on the scan (the best shift,
   to an eighth of a pixel) and compared with the print: scan, difference map and font side by
   side, scored by intersection over union and by how far the worst miss and the worst excess
   reach, in pixels. This is what found the accent sets, the Céilí h and Tuam's fada setting.

### The 2026 styles

The flyer shows one style of each face, and none of the four had an italic or bold in 1978. These
were drawn for version 2.000 from the regulars, by rule, then checked glyph by glyph:

- **Bold** (Céilí, Kilfane): the regular redrawn with a wider pen. Each stroke is grown by an
  ellipse whose proportions follow the face's own contrast (Céilí's broad flat nib adds 2.8% of
  the em across and 0.6% up and down; Kilfane's rounder pen 2.4% and 1.7%), after a 3–4%
  widening that keeps counters open. Corners stay sharp, and x-height, cap height and ascenders are
  restored to the regular's, so the styles mix on a line. Stems come out at about 1.6 (Céilí) and
  1.4 (Kilfane) times the regular's.
- **Kept open by hand.** A wider pen closes every narrow space at once. Where it left a counter
  less than 55% of its width, the counter is redrawn as the regular's counter shrunk by a lighter
  pen, so it keeps its shape (the lenses of $, Kilfane's ring, its alternate A). Where it closed an opening that is
  all that joins a counter to the outside (the tails of Kilfane's g and y, the bowls of s), the
  pen is eased off around the opening, smoothly, until 62% of its width is open again.
  Gaps under a quarter of a stem are strokes that touch on the drawing, and they close. One
  opening closes by choice: the tip of Céilí's 6 reaches for its stem across a gap narrower than
  the bold pen, and there the two meet.
- **Built pieces follow.** Accents, punctuation and symbols are rebuilt from the bold letters.
  The pairs from the sheets' accent sets (diaeresis dots, guillemets) are moved apart by the
  pen's growth, small glyphs (superiors, fractions, the letters in © and ®) are drawn halfway
  between the regular and bold weights so their counters stay open, and spacing is 8% tighter,
  as the counters are smaller.
- **Italic** (all four): the regular narrowed 4% with its stems restored, spaced and kerned
  upright, then sloped 8° about the middle of the x-height. A slope moves both sides of every
  letter alike, so the upright spacing and kerning carry over exactly. Mark anchors are sloped
  with the letters, so decomposed accents land as the precomposed ones do. These are sloped
  romans, as for most display faces: no cursive forms were invented.
- **No bold for Carrick or Tuam Uncial.** Their stems are already 37–39% of the x-height. A
  heavier cut would close their counters and, in Tuam's case, the hairline cuts that are part of
  Hayes's design.

### Ink spread and weight

The same glyph appears on the sheet at two or three sizes. Fitting stem width against
size gives the toner spread the photocopy added, and that spread was removed.

The result was checked against the independent 48–60pt samples printed on the sheet
(`specimen/validation/large-sample-overlay.png`):

| Face | Stem width vs sample | Shape overlap (IoU) |
|---|---|---|
| Kilfane | −1% | 0.83–0.91 |
| Tuam Uncial | +2% | 0.94–0.95 |
| Carrick | +2% | 0.88–0.93 |
| Céilí | −7% (0.4 px, at the measurement's resolution) | 0.81–0.87 |

The 1.100 redraw keeps each face's total ink within 0.2% of the 1.000 trace, and every
traced glyph within 2.5%.

### Details found on the sheet

- **Tuam's dots are cut.** The dots of Tuam's i, j, ! and ? are separated by a hairline
  cut. That is part of Hayes's notched style, and is reproduced.
- **Hairline joins restored.** Where the photocopy dropped Tuam's hairline joins (m,
  n, h), they were bridged back in.
- **Céilí's i-dot** is a short slanted stroke, as drawn.
- **The sheets' accent sets.** Beside Kilfane's and Carrick's alphabets the flyer prints the loose
  accents that came on each transfer sheet: two rules, the fada, dots, diaeresis, ring (twice on
  Kilfane's), circumflex, háček (Kilfane's), tilde and guillemets. Each piece was identified and
  used. Where ink spread joined two pieces (one of Carrick's diaeresis dots and its ring), the
  clean copy was repeated. The rules are only about 2.5 px thick on the scan, so their weight was
  measured and the dashes drawn as clean rules with each face's own terminals.
- **Tuam's fadas** are a long flat bar set very close to the letter, and the font keeps both.
- **Baselines straightened.** The letters on the sheet were hand-placed, wandering up
  to about 1 px off the baseline. They were seated on the baseline, and x-height and
  cap height were regularised conservatively.
- **The flyer's title is not one of the four.** It's set in another insular face, so
  it was not used.

### Spacing and kerning

- **Spacing.** Profile-based autospacing, calibrated to the letter spacing printed on
  the sheet. The flyer justified every line to its column, so the spacing changes from
  line to line (Kilfane's lower-case lines differ by about 25%). The spacing is therefore
  set from the median over all lines, 6% looser for text use. Line lengths match the
  specimen lines to about ±5%.
- **Kerning.** Automatic class-based kerning (40–390 class pairs per face), with exceptions
  that stop accents colliding with overhangs.

### What isn't the designers' drawing

**Every italic and bold** is 2026 work derived from the regulars (above). In the regulars, these
glyphs were drawn to match each face's weight and terminals. Treat them as informed
reconstructions:

- Céilí's accents, and Tuam Uncial's except its acute (from the flyer's á é í ó ú).
- In every face, the cedilla, ogonek and commas below; in Céilí and Tuam also the grave, double
  acute and breve (Kilfane's and Carrick's are made from their sheets' marks).
- Hyphens and dashes, except Céilí's hyphen, which is from the sheet. Kilfane's and Carrick's
  dashes take their weight from their sheets' rules.
- The slash, brackets and braces, Tuam's and Céilí's guillemets, and all symbols.
- Tuam's comma and parentheses, and Céilí's comma.
- Letters built from the faces' own parts: æ œ ø ð đ ħ ł ŧ ŋ þ ß ſ ĳ ŀ ĸ ⁊ €.
- The right leg of Céilí's h (it is Hecht's n leg, because the flyer's h leg printed broken).
  The stem and shoulder are the flyer's.
- The hairlines restored in Céilí's b, e and e.alt1 (5 units, where the scan shows grey but the
  trace found nothing).

## Quality checks

| Check | Result |
|---|---|
| OpenType Sanitizer (OTS, as used by Chrome and Firefox) | All 48 font files pass |
| Every flyer glyph against the scan | 224 glyphs, mean overlap 0.948 after registration (`specimen/validation/flyer-glyph-audit.md`) |
| Font Bakery universal profile, run per family | Zero FAIL and zero ERROR in all four families, including the family checks (the online name-registry check was skipped; it needs network access). The remaining WARNs are informational (`alt_caron` asks for a manual check of ď ľ ť; `contour_count` flags glyphs that differ from typical fonts by design, such as Kilfane's insular r). Reports are in `specimen/validation/`. |
| Style linking | Every file's names, style bits, weight class, italic angle, caret slope, `STAT` and CFF data agree with its style; all styles of a family share line metrics and the same characters |
| Bold against regular | Every glyph's pieces and counters compared: none lost or merged, except Céilí's 6, which joins by design |
| Accents in the italics and bolds | Decomposed sequences (a + ◌́ and so on) render like the precomposed letters in all twelve fonts |
| Browser test | All faces load in Chromium (HarfBuzz shaping); kerning, marks and stylistic sets work; the specimen page has no horizontal scroll at phone width |

## Limitations

- These are reconstructions from a roughly 100 dpi photocopy. The 1.100 redraw makes them
  clean at poster sizes, but details smaller than about a twentieth of the x-height (the
  exact shape of a serif tip, say) are interpretation, not measurement.
- The italics and bolds are new designs in the spirit of the regulars, not facsimiles: the
  designers drew neither. Carrick and Tuam Uncial have no bold. There is no Greek or Cyrillic.
- ẞ (capital sharp s) is not included.

## Making them better: sources to obtain

A higher-resolution source would sharpen every outline. In order of value:

1. **The NIVAL competition brochure** ([record](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/45/)).
   Use its download button. For high-resolution scans of Curran's original drawings,
   contact nivalinfo@ncad.ie.
2. **The Fonts In Use pages** linked above. They carry photos of the Letraset sheets
   and glyph sets.
3. **Mary Ann Bolger's RCA PhD thesis** ([PDF](https://researchonline.rca.ac.uk/3543/1/MABolger_PhD_Thesis_Vol1.pdf)).
   Chapter 4 covers 1970s Irish dry-transfer faces and may settle the dates.
4. **Signal's Jarlath specimen** ([PDF](https://signalfoundry.com/media/pages/typefaces/jarlath/b33a81de89-1738147593/signal_jarlath.pdf)),
   for its Tuam background.
5. **Series C banknote scans**, for Kilfane in use:
   [irishpapermoney.com](https://www.irishpapermoney.com/c-old-irish-banknotes-series-c.html)
   and Numista.
6. **A 600–1200 dpi rescan of the flyer itself** would roughly double or triple the
   detail.
7. **Dermot McGuinne, *Irish Type Design: a history of printing types in the Irish
   character*** (Irish Academic Press 1992; 2nd ed. National Print Museum 2010;
   [NLI record](https://catalogue.nli.ie/Record/vtls000883198)). The standard history, and
   the likeliest printed source for the competition's results and dates.
8. **Talks on the competition and its afterlife:** the ATypI presentation
   [*Transnational heritage and alternative futures*](https://atypi.org/presentation/retyping-europe/),
   which uses the 1978 competition as a case study, and the NCAD talk
   [*Athbheochan: Type, Revival, and Ideas of Irishness*](https://www.ncad.ie/news/view/athbheochan-type-revival-and-ideas-of-irishness-max-phillips-and-mary-annbolger)
   by Max Phillips and Mary Ann Bolger (Hayes's niece).

## Building

The fonts are built from `sources/` by the scripts in `scripts/`. Everything generated goes to
`build/` (not committed); `make release` copies the fonts, stylesheet and evidence into place.

```sh
make setup        # a Python 3.13 venv with the pinned tools (needs ttfautohint on PATH)
make fonts        # build every style of every face into build/fonts (about a minute and a half)
make test         # the release checks: OTS, style linking, coverage, shaping, topology
make release      # fonts/, css/ and index.html from build/fonts
make validate     # Font Bakery per family and the flyer audit into docs/validation
make specimen     # the PDF and PNG specimen into docs/specimen
make package      # the release ZIPs in build/dist
make site         # the test page app in build/app
make trace        # re-trace sources/traced/*.json from the scan (slow; only for a new scan)
```

Builds are deterministic: the same sources give the same fonts. To work from a better image,
replace `sources/flyer.jpg`, update the coordinates in `scripts/specs.py`, run `make trace`, and
review the changes to `sources/traced/` like any other diff.

## Rights

As far as I know, Irish law (Copyright and Related Rights Act 2000, s.84) and UK law
(CDPA 1988, s.55) protect a typeface design for 25 years after it is first marketed.
That has long passed for these 1978 designs. Names and trademarks are a separate
matter, and Jarlath is its own commercial product.

The digitisation is new work, copyright 2026 Dan Drayne, and it is released under the
**SIL Open Font License 1.1** (`OFL.txt`). You may use the fonts for anything, including
commercial work, and share or adapt them, but you may not sell the fonts on their own,
and adapted versions must stay under the OFL. No Reserved Font Names are declared. Each
font's name table carries the copyright, the licence and its original designer.
