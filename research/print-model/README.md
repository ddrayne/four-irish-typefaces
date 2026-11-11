# The prints' ink gain, and the weight Céilí was drawn at

A measurement, not a candidate. No font and no existing script is changed. It asks one question:
what stem weight did Hermann Hecht draw, given that Céilí survives only as prints?

**Result.** Both prints fatten stems. With each print's gain measured on Kilfane and Carrick (whose
Letraset sheets survive) and taken off, Céilí's stem comes out at about **90 font units, 0.166 of the
x-height**, where the release has 108 (0.201). Six estimates lie between 83 and 98 (0.154 to 0.182).
The release's weight and N46's (108) are outside that range; N45's (96) is inside, near its top.
The direction is well supported. The amount is not: the estimates disagree by more than their own
error bars. Details, tests and limits follow.

Run `python scripts/print_model.py` (numbers in [results.json](results.json); `--refit` measures the
scans again, about 20 minutes). Tests: `python -m pytest -q tests/test_print_model.py` (synthetic
images only).

## Sources

All are local archive scans under ignored `build/research/original-specimens/`. No pixel of them is
in this folder. Boards that show them are written only to `build/print-model/`.

| Id | File | SHA-256 | Used for |
|---|---|---|---|
| N46 | competition-advert-1.jpg | `0adeda27c189890fbd78619810cfc144ea3d5b910256971bf1c33a946d4baadc` | leaflet, photocopy: four alphabets and eight sheet samples |
| N45 | competition-brochure-2.jpg | `57d14ab343c5942345f14f277be8e92a6182f4b1a6a90a1d9ae413563b26ef18` | brochure inside, offset: four alphabets |
| N44 | competition-brochure-1.jpg | `172ddcd2548474636df30b9043cacb466694883d5b2bdaab4fbd3f92e8276055` | brochure cover: heading in Céilí |
| N517 | Kilfane-Letraset.jpg | `a3a821f5cb233b4f6bff0b163c9c6992b9431109a6ad706d206d91981ceae16b` | Kilfane sheets, 30 pt (dark ink) and 48 pt (light ink) |
| N514 | Carrick-Letraset.jpg | `525f4bb849a7f5bea66f82ca5aad0f2dbb3a9d8d7257ae2e91ed7e36c08ef35d` | Carrick sheets, 36 pt and 60 pt |

Reference outlines: the four release fonts in `fonts/otf/` (hashes in results.json). They serve as
shapes to lay on the prints. Their weight is not assumed to be right, and for Kilfane and Carrick it
is measured against the sheets first.

Where things were measured (image pixels, x0 y0 x1 y1):

- Céilí on N46, N45, N44 and the two samples: the boxes of `research/ceili-judgement/traces/source-regions.json`.
- Tuam on N46 and N45: `research/tuam-judgement/traces/source-regions.json`.
- Kilfane capitals: N46 (140, 300, 1080, 560); N45 (1560, 910, 2260, 1130). Samples on N46: 30 pt (300, 1095, 400, 1210), 48 pt (620, 1035, 790, 1215).
- Carrick a to o: N46 (140, 1400, 1080, 1700); N45 (1560, 330, 2260, 660). Samples on N46: 36 pt (300, 1960, 400, 2070), 60 pt (615, 1930, 780, 2070).
- Tuam samples on N46: 30 pt (1280, 1010, 1450, 1125), 48 pt (1655, 960, 1915, 1125).
- Sheets: N517 30 pt (0, 1250, 2573, 2573), 48 pt (0, 150, 2573, 1040); N514 36 pt (0, 1520, 2592, 2592), 60 pt (0, 150, 2592, 1280). Up to four impressions of each letter.
- Captions: the boxes in `CAPTIONS` in the script.

Each glyph was found inside its window by correlation with the rendered outline. Its box, scale,
rotation, origin, blur, residual and every stem's width are in `measurements` in results.json
(478 fits, of which 30 were dropped; they are listed with the reason under `results.dropped`).

## Method

**The model.** A print is the drawing with every edge moved outwards by a gain *d*, then blurred.
The outline is laid on the print at *s* pixels per font unit, rotated and shifted. Every edge is
moved by *d* pixels. The result is blurred by a Gaussian and compared with the print. *s*, the
place, *d* and the blur are fitted together, on pixels near the edge only. Scale and gain do not
trade against each other: a gain moves opposite edges apart, a scale moves centre-lines.

**Levels.** Each letter is read between its own paper (median outside the letter) and its own ink
(median at least three pixels inside it). The edge is the half level. Every number was also taken
at the 40% and 60% levels.

**Stems.** Straight vertical stems are found on the outline (both edges straight for at least 120
units). On the print each is measured on profiles across it, in six groups of rows, at the three
levels. This is the measure used for the stem weight. The whole-outline fit gives the scale.

**Transform.** Flat scans: one scale, a rotation, a shift. Sheet photographs: also an aspect and a
shear per letter, which take up the photograph's perspective. Ratios within one letter are used, so
perspective across the sheet does not enter.

**Release metrics.** Céilí Regular: x-height 538 (OS/2; flat letters stand 534 to 542). Stem 108:
the median of the 15 straight stems the script finds in l, i, n, 1, m, h, u, k, p, r, j (all 107 to 109).

## 1. The sheets against the release outlines

The release's Kilfane and Carrick were drawn from the sheets at a calibrated level (0.33 to 0.38),
chosen to match the specimen prints. So they are heavier than the sheets, and by this much
(sheet minus release, font units per edge, at the photograph's half level):

| Sheet | Letters | Whole outline | Stems |
|---|---|---|---|
| Kilfane 30 pt, dark ink | 15 | −2.3 ± 0.4 | −3.0 ± 0.8 |
| Kilfane 48 pt, light ink | 10 | −1.3 ± 0.4 | −1.7 ± 0.9 |
| Carrick 36 pt | 15 | −1.2 ± 0.3 | −2.8 ± 0.9 |
| Carrick 60 pt | 10 | −1.5 ± 0.5 | −2.9 ± 1.1 |

**Does the photograph add or lose edge?** Two tests, both passed.
A photograph's own gain would be the same in pixels on both sheet sizes. Fitted across the two
sizes it is −0.10 ± 0.11 px (Kilfane) and −0.03 ± 0.20 px (Carrick): none found.
A tone or halation error would fatten light letters and thin dark ones. Kilfane's light-ink sheet
reads 1.0 ± 0.6 units per edge heavier than its dark-ink sheet. The truth lies between them, so the
error is at most about half a unit per edge. Each letter's own sheet value (the mean of its sheets)
is used below.

## 2. Each print's gain, on the control faces

Print minus sheet, pixels per edge, same letters:

| Print | Face | Whole outline | Stems | Thick strokes | Thin strokes |
|---|---|---|---|---|---|
| N46 | Kilfane | +0.49 ± 0.10 | +0.96 ± 0.11 | +0.51 ± 0.11 | +0.20 ± 0.15 |
| N46 | Carrick | +0.15 ± 0.09 | +0.80 ± 0.15 | +0.25 ± 0.11 | +0.03 ± 0.06 |
| N45 | Kilfane | +0.30 ± 0.07 | +0.39 ± 0.06 | +0.32 ± 0.06 | +0.40 ± 0.10 |
| N45 | Carrick | +0.28 ± 0.14 | +0.60 ± 0.09 | +0.37 ± 0.11 | +0.26 ± 0.25 |

Stems, both faces together: **N46 +0.88 ± 0.12 px per edge, N45 +0.50 ± 0.12 px**. In millimetres
that is about 0.09 and 0.07 per edge, if N46 is an A4 page (10.2 px/mm) and N45 an A3 spread
(7.1 px/mm). The page sizes are assumed; see "sizes" below.

What the table shows:

- One number does not describe a print. On the photocopy stems gain a pixel while thin strokes gain
  almost nothing: it fattens stems and starves hairlines and tips. The offset print gains evenly.
- Stems of different width gain alike on N46 (Kilfane's are 15 px, Carrick's 22 px). On N45 Carrick's
  gain more (0.60 against 0.39, two standard errors apart). Céilí's stems are 9 to 13 px, nearest
  Kilfane's.
- At the 40% and 60% levels every offset moves by 0.2 to 0.4 px on N46 and 0.1 to 0.2 px on N45. The
  corrected stems below move by less than 0.3 units, because Céilí and the controls are read at
  the same level on the same print.

## 3. Céilí with the gain removed

Stems against stems. "Printed" is the stem as the print shows it; "drawn" has the print's gain
(both control faces) taken off. Font units at the release's scale.

| Estimate | Stems | Printed | Drawn | Kilfane only | Carrick only |
|---|---|---|---|---|---|
| N46 alphabet | 21 letters | 108.1 | **92.9 ± 3.3** | 91.5 | 94.3 |
| N45 alphabet | 21 letters | 96.0 | **86.1 ± 2.5** | 88.2 | 84.0 |
| N44 heading, N45's gain | 10 letters | 106.1 | 96.8 ± 2.6 | 98.8 | 94.9 |
| N46 42 pt sample, N46's gain | the 1 | 103.4 | 91.8 | 90.7 | 92.9 |
| N46 24 pt sample, N46's gain | the 1 | 117.9 | 97.9 | 96.0 | 99.7 |
| N46, three sizes (section 4) | a and 1 | | 82.7 ± 6.2 | | |

Do the two prints agree once corrected? Better than before, not fully. The printed stems differ by
12 units (108 against 96). The corrected ones differ by 7 (93 against 86), about 1.6 standard
errors. Both are well below the release.

The whole outline moves less than the stems: by −3.4 ± 1.6 units per edge on N46 and −6.6 ± 0.8 on
N45, against −7.5 and −11.0 for stems. Thin strokes move least: −2.0 ± 1.0 and −4.7 ± 1.5. So the
stems are the part of the release that is most too heavy.

## 4. Several sizes on one print

With a gain *g* that is the same in pixels at every size, the offset against the release is
*g* + (drawn − release) × *s*. N46 prints a and 1 of each face at three sizes: the alphabet and two
sheet samples.

| Face on N46 | Sizes | Gain, px | Drawn − release, units per edge | Known from the sheet |
|---|---|---|---|---|
| Kilfane, A | 3 | +0.27 ± 0.44 | +1.8 ± 3.0 | −1.1 |
| Carrick, a | 2 (alphabet a was dropped) | −0.15 ± 0.60 | +2.7 ± 3.3 | +3.4 |
| Céilí, a and 1 | 3 | +1.49 ± 0.38 | **−12.6 ± 3.1** | |
| Tuam, a and 1 | 3 | +1.28 ± 0.36 | −8.7 ± 2.8 | |

On the two faces where the answer is known the method lands within one standard error. That error is
large: about 3 units per edge, 6 in the stem. For Céilí it gives a stem of 83 ± 6, with no control
face involved. It assumes the samples and the alphabet carry the same gain; the samples look rougher
and may be a copy further on.

The offset branch cannot do this. The cover heading (N44) is only 7% larger than N45's alphabet.
Read as a size effect, their difference would put the drawing 64 units per edge above the release,
which is absurd. It is a difference of gain between the two formes (next section).

**Sizes.** If N46 is A4 and the brochure spread A3, the 42 pt sample on N46 and the cover heading on
N44 have the same size: l is 11.49 mm and 11.52 mm tall (nominal 11 mm). So the heading was very
probably set from the 42 pt Letraset sheet, or from artwork of exactly that size. This also supports
the two page sizes.

## 5. Tests of the assumptions

| Assumption | Test | Outcome |
|---|---|---|
| A uniform edge shift describes a print | Stems against the gaps between them, and same-facing edges | Holds. Stem growth and gap loss cancel within 0.1 px on Céilí (N46, N45, N44), Tuam, Kilfane's sheets and Carrick's 36 pt sheet. Exceptions: Kilfane's stems stand 0.58 ± 0.17 px further apart on N46 and 0.22 ± 0.06 on N45 than the outline's; Carrick's 60 pt sheet −0.34 (two pairs) |
| The sheet photograph is neutral | Two sizes; light against dark ink | Holds within about half a unit per edge (section 1) |
| The half level is neutral | 40% and 60% | Offsets move a lot, corrected values hardly (section 2) |
| Gain does not depend on stroke width | Kilfane against Carrick; thick against thin | Fails for thin strokes on N46. For stems: holds on N46, doubtful on N45. Kilfane alone gives 91.5 and 88.2 |
| Gain is the same across a page | Stroke width of the captions, one type across the page | **Fails, weakly.** N46: the captions beside Tuam and Céilí are 0.23 ± 0.10 px per edge heavier than those beside Kilfane and Carrick. N45: the one caption on Céilí's page is 0.16 ± 0.03 heavier than the four on the other page (different words; weak). Both would make Céilí lighter still: 88.9 and 82.8 |
| The cover prints as the inside does | N44 against N45, stems and hairlines | **Fails.** N44 is heavier than N45 by about 5 units per edge on stems and on hairlines alike. An equal shift on both is gain, not a heavier design. So N44's 96.8 is too high by an unknown part of that |
| The samples carry the alphabet's gain | Kilfane's A | Roughly. The samples' stem gains 1.0 and 1.4 px; the alphabet's A gains 0.7, the alphabet as a whole 0.96 |
| Céilí's sheet relates to its print as Kilfane's and Carrick's do | none possible | Untested. No Céilí sheet is known |
| The control gain applies to Céilí's part of the plate | captions only | Untested beyond the row above. If the brochure's alphabets were separate blocks, each has its own gain |

Not used: Bolger's photographs (too coarse for a tenth of a stem), N47, and the JP2 files.

## Conclusion

- **Gain.** N46 fattens stems by 0.88 ± 0.12 px per edge (about 0.09 mm) and thin strokes hardly at
  all. N45 fattens stems by 0.50 ± 0.12 px per edge (about 0.07 mm), thin strokes about as much.
- **Céilí's drawn stem.** Best estimate 89.5 units, 0.166 of the x-height: the mean of the two
  alphabets, each with its own gain removed. All estimates and their caption-adjusted variants lie
  between 82.7 and 97.9 (0.154 to 0.182). This is a range of methods, not a confidence interval.
  Their own error bars (2.5 to 6 units) are smaller than their disagreement.
- **Inside or outside.** Release 108: outside. N46 as printed, 108: outside. N45 as printed, 96:
  inside, near the top. The earlier calibration took N45 for the outlier. This measurement says N45
  is the print nearest the drawing, and still a little heavy.
- **What it would imply** (a recommendation, not a change): lighten the stems by about 17%, some 9
  units per edge; the range is 9% to 23%. Hairlines should lose much less, 2 to 5 units per edge.
  A uniform thinning by 9 units would halve the hairlines and is not what the prints show.
  Confidence: high that the release's stems are too heavy; moderate that N45's weight (−11%) is a
  safe first step; low for any figure finer than that.
- **Every bias found points the same way.** The caption test and the cover's extra gain both make
  the true value lighter than the table, not heavier. An offset print rarely prints thinner than its
  artwork, and on the control faces N45 prints fatter. So 96 is close to an upper bound.

**Tuam Uncial** (secondary; release stem 220, x-height 544). Printed: N46 232.8, N45 214.7.
Corrected: N46 214.0 ± 3.8, N45 202.5 ± 3.2, three sizes 202.7 ± 5.6. So the stems would lose 3 to
9 units per edge (3% to 8%), and each slit between strokes would open by 6 to 18 units. The two
prints again disagree after correction, in the same direction as for Céilí.

## Limits

- "Drawn" here means "as the Letraset sheet would show it". The controls measure print against
  sheet. If Letraset's production changed a weight, that is inside the control gain. The leaflet's
  own sheet samples of Kilfane gain as much as its alphabet, so most of it is print.
- The sheets photographed hold Kilfane's capitals and Carrick's a to o. Both are heavier than
  Céilí. No control has Céilí's weight and contrast.
- One photograph of each sheet, one scan of each print. Agreement between N45 and N44, or between
  N46's alphabet and its samples, is not independent confirmation.
- The page sizes behind the millimetre figures are assumed (A4, A3). Pixel and font-unit figures
  do not depend on them.
- Kilfane's letters on N46 are about 1.5% wider between stems than on the sheet. Not explained.
  It changes stem gain by less than 0.1 px.
- Error bars are bootstrap errors of medians across letters. They do not include the untested
  assumptions.
- Stems only. Curves, joins and terminals were not judged, and no outline was drawn.
