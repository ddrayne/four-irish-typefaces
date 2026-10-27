# Tuam Uncial Study 3: the judgement pass

[Study 2](../round-03/README.md) traced every glyph from N46 alone, NIVAL's copy of the flyer: a
photocopy, large but blurred, ragged at its edges and speckled in its ink. Its outlines followed that:
lumpy edges, pinholes where the toner dropped out (the d, the $, the 5), and half-filled notches where the
photocopy's blur had closed a drawn cut. Study 3 judges each glyph from every print of it. It is a research
candidate: it does not replace the release.

| | |
|---|---|
| Fonts | [Tuam Uncial Study 3](fonts/), Regular, OTF, TTF, WOFF, WOFF2; 261 glyphs, 398 code points (the release's coverage) |
| Traces | [traces/](traces/): `tuam.json` (46 entries), `evidence.json`, `source-regions.json` |
| Evidence | [sheet-check.json](sheet-check.json) (the production sheet), [audit-metrics.json](audit-metrics.json) (source fit) |
| Proofs (font-only) | [glyphs.png](glyphs.png): each glyph in Study 2, then Study 3; [text.png](text.png): the same line in each at 16, 28 and 72 px |

The boards, overlays and sheet crops hold archive pixels and stay in ignored `build/` (see [RIGHTS](../RIGHTS.md)).

## The prints

| Print | What it is | Use |
|---|---|---|
| N46 `competition-advert-1` | the flyer, photocopied: 2140 x 3000, x-height about 52 px | traced, with N45 |
| N45 `competition-brochure-2` | the competition catalogue, offset printed from another paste-up of the same letters: clean edges, x-height about 44 px | traced, with N46 |
| flyer `sources/flyer.jpg` | the same document as N46 at a third of its resolution | on the boards only |
| Bolger fig. 206 | a photograph of the production sheet, Letraset S53912, 48 pt, c. 1980 (volume 2, PDF page 164): many impressions, x-height about 20 px | the independent check ([sheet-check.json](sheet-check.json)) |
| Bolger figs 205b, 205c | Hayes's development work with the repro camera, 1974-78 (PDF pages 162-163): earlier drawings (205c's b is a capital-B form) | construction only |
| N47, N44 | the advert's second sheet; the brochure's cover | neither prints Tuam |

N46 and N45 reproduce the same lettering and may share intermediate copies, so their agreement is not
independent confirmation; the production sheet is a separate line of reproduction.

## How the glyphs were judged

`scripts/evidence_board.py tuam` sets each glyph beside N46, N45 and the flyer, with a consensus view in the
font's coordinates. Two things came out of every board:

- **Where the prints agree, they agree on drawing; where they differ, mostly by print.** Measured on the same
  letter, the two have the same weight (n's stem is 0.400 of its height on N46, 0.403 on N45), but N46 is
  blurred: its white gaps run about a pixel narrower than N45's everywhere, n's included.
- **Tuam is cut, not joined.** On both prints the arches of n and m stand apart from their stems, and the
  hooks of a, b, g, o, 0, 8 and 9 stop short of the next stroke, leaving a slit into the counter. N45 prints
  the same construction in d, f, h, p, q, r, s, u, v, w, 5 and 6, where N46's blur fills it. The
  production sheet prints h, u, f and r in two pieces on every impression (as it does n), and the means of
  its v and w impressions show a light seam where N45 cuts them (x, which is crossed, shows none). Hayes's
  development photostats draw the same hooks and cuts.

So each glyph is traced from **the mean of the two prints**, in N46's frame (`scripts/consensus_trace.py`):
N45 is laid on N46 by one similarity for the whole alphabet (scale 0.8529, rotation -0.27 degrees, the median
of per-glyph fits, which spread by 0.6% and 0.4 degrees) and a shift per letter, and the mean is traced
through round 3's own tracer at N46's calibration, boxes, baselines and 0.8-pixel blur. What both prints show
is kept; what one alone shows is halved. Every glyph then takes the topology recorded for it in
`evidence.json` (`topology`): where the prints agree, theirs; where they differ, the decision below, reached by
taking N45's ink in the smallest region where they disagree. Each entry records both boxes and labels, the
transform, how far the two prints' edges differ (0.4 to 1.1 N46 pixels; the traced edge lies half-way, an
uncertainty of 2 to 6 font units) and the decision.

| Glyph | N46 | N45 | Study 3 | Evidence for the decision |
|---|---|---|---|---|
| h, u, r, f | joined | cut | **cut** | every impression on the production sheet (r: 7 of 8); n's arch is cut on both prints |
| v, w | joined | cut | **cut** | a seam in the means of the sheet's v and w impressions; 205c's first v |
| 5 | joined | flag cut | **cut** | a sheet impression shows the seam; as f's flag |
| d, p, q, s, 6 | closed, with pinholes | slit open | **open** | the same hook as a, b, g, 9 on both prints; 205b-c; too narrow for the sheet |
| $ | three counters | two | **two** | N46's third is a toner dropout |
| é, í, ú | acute joined | apart | **apart** | as on every é, í, ú of the sheet |

Against Study 2 the glyphs carry 2.7% less ink (median), 1.8% more than the release; the edges are smooth
where only N46 was ragged. Study 2's narrow necks (`scripts/pinches.py`, under 0.2 stem: d, h, p, q, s, 6) were
all half-closed cuts and are now the cuts; one remains, in e.

## Kept as attested

- **e.** The bar's wedge meets the bowl at a neck of 32 units (0.14 stem; Study 2 had 29, the release 40):
  both prints and 205c draw it, and at 16 px the e reads closed. No judged edit was needed.
- **The openings of a, o, 0, 8 and 9**, as round 3 kept them: both prints show them, and the sheet shows o's.
  N46's blur had narrowed them in Study 2 (8 and 9 to 8 units at their narrowest); the mean opens them to
  20 to 48 units.

## Constructions (recorded in `evidence.json`, `constructions`)

- **Fadas.** Both prints set each acute as drawn for its letter: on í a short acute, 0.43 x-height wide
  against 0.68 on the others, set 36 units right; on ó one set 44 units right of centre. The builder used one
  acute (ú's) on every letter. Now á, é, í, ó and ú keep their own traced acute and its place across the letter
  (á's touches the bowl on both prints, so á takes the shared acute at á's place); the gap above the letter
  stays the builder's uniform one, the traced gaps varying by print. A `ccmp` ligature makes the decomposed
  letter + U+0301 the same glyph. Other accents still derive from ú's acute.
- **Braces** are not on the specimens. The stroked construction ended its tip inside the stems' outer edge, so
  its point was cut in as a notch, and the butt caps left spurs; Study 2's } fell into two pieces. The brace is
  now drawn as one outline at the same weight and extent, with a point jutting 0.55 stroke beyond the stems
  and an inner cusp 0.45 inside, so the waist is 1.1 strokes wide wherever it is cut (`symbols.pointed_brace`).

Both are off for the release (`Font2.OWN_ACUTES`, `Font2.BRACE_POINT`): `build_original_study.py` turns them
on for a round whose evidence asks for them, and 2.101 rebuilds byte-identical.

## Source fit

[audit-metrics.json](audit-metrics.json), `scripts/audit_original_study.py --coverage` against Study 2:

| Print | Entries | Study 2 mean IoU | Study 3 mean IoU | Improved | Worse by more than 0.005 |
|---|---:|---:|---:|---:|---:|
| N46 | 46 | 0.94398 | 0.92715 | 7 | 39 |
| N45 | 46 | 0.88083 | 0.91115 | 43 | 0 |

A mean of two prints fits each less closely than its own trace; the two differ from each other by about 7%
IoU in N46's own pixels. These are fits to correlated reproductions, not authenticity scores.

## The finishing pass (the release only)

The release builds Tuam from these traces through a studio pass, [judged-edits.json](judged-edits.json), applied by
`scripts/tuam_studio.py` from `build_candidate.py`; the Study 3 fonts here stay as traced. Each edit states its
target and is measured again on the outline; units are font units (one N46 pixel is about 10.6).

| What | 3.000 | Now | Why |
|---|---|---|---|
| Arch cuts of n, m, h, r, u, y, f | 23 to 37 | 28 | N45 prints n, m, h, u, f at 25 to 29; the spread was averaging and refitting |
| Seams of v and w; the cut of 5 | 8 to 13; 14 | 15 to 16; 21 | N45's widths: averaging with N46, which fills them, had halved them |
| Slits of a, b, d, g, o, p, q, 6, 9, 0 | b, o, p, 0 8 to 14 off N45 | within 2 of N45 | as N45 prints each (measured alike) |
| Spur and hook ends | spikes, flats, blunt ends | one sharp point | consistent ends; the prints cannot resolve them |
| Vertical stems | 213 to 228 | 218 to 222 | N45 prints them 211 to 222; N46's blur thickened some |
| Flat tops at the x-height | 529 to 545 | 542 to 544 | the builder's baseline snap left o (530), d, m's first arch, g low |
| o, l, 9 | 530, 761, 669 (9 below the line) | 544, 774, 690 (on it) | as tall as their neighbours on both prints |
| Bowls of p, q, y | 6 to 10 above the baseline | on it | as every other bowl |
| Dots of i, j, !, ? | 25 to 32 from the stroke | 40 (j takes i's dot, ? takes !'s) | N45 prints them 37 to 45 apart; ? and ! at the figures' height, their dots on the line |
| Gap under every accent | 19 | 30 | N45 prints the fadas 26 to 38 above their letters |
| @ | its a pressed into the ring, joined to it | an a inside the ring, 34 clear | as (c) and (R) are drawn |
| Italic | cuts 13 to 27, seams 3 to 6, ˚ without its counter | cuts 26 to 27, seams 14 to 15, ˚ open | narrowed as drawn, without the hair of weight that closed them; nodes at its extremes |
| f before an ascender or fada | flag 10 units from it (fl +10) | 28 (fl +30, fb and fk +40) | the face's cut width, above the x-height |

Also: corners blurred into two or three nodes drawn as one (the beaks of r and u, b's foot, the crotches of p
and g, made sharp as q's, e's eye, l's foot); s's inner turn one curve; ð's bar raised to clear d's lifted bowl.
Outline totals over the 41 traced letters, figures and symbols: Regular 2711 points, 29 segments under 8 units and
86 joins bent 3 to 25 degrees, now 2644, 17 and 76; Italic 4223, 279 and 462, now 2990, 62 and 194.

**The cut widths.** Evened only within each construction, where N45 shows one width: the arch cuts (28) and the
vertex seams (15), which N45 prints distinctly narrower and which stay so. The slits are left at N45's own widths
(20 to 33), which differ by under two N45 pixels; evening them to one width (about 27) would be the next step, but
nothing in the prints asks for it.

### The second pass (a review of the release)

A type review of the release found six defects. Each fix is in [judged-edits.json](judged-edits.json) with its reason
(`constructions`; r's top in `edits`; the section sign in `derived`, edits to a glyph made from the traced ones).

| What | First pass | Now | Evidence and reasoning |
|---|---|---|---|
| í against i | acute 223 x 125 at 19 degrees, 30 above the stem; dot 249 x 93, 40 above: alike at 14 to 20 px | the traced acute drawn steeper, its right end raised 100: 223 x 213 at 40 degrees, its width, thin left end, place and gap kept | N45 prints í's acute steeper and taller than the dot (18 degrees, 136 units, against 3 and 74) and closer to the stem (25 against 37); the production sheet the same (13 to 14 degrees against 1 to 3; 26 against 54). Of eight options, proofed at 14 to 20 px, this is the least change that renders i and í at least as differently as Liberation Serif, the least distinct of three common text faces (FreeType, blurred half a pixel: 0.18 to 0.30, now 0.70 to 0.85, against 0.55 to 0.73); a larger gap also passes but draws a raised dot, not a fada, against the prints, which set the acute nearer than the dot |
| ḃ ḋ ḟ | the ponc 30 above the ascender, one with it at 14 px | ḃ ḋ: beside the ascender over the bowl, centred over the counter and on the ascender's height above the x-height (61 above the bowl, 73 and 70 from the ascender; 63 and 62 in the Italic); ḟ: 60 above the stem | Hayes letters the dotted b of leabhair this way in the face on his 1974 cover (Bolger fig. 204, PDF page 160); f has no bowl and its flag fills the space beside its stem. All three now render apart at 14 to 20 px. The line's ascender rises from 934 to 951 to hold ḟ |
| § | a 76 degree corner on pieces of 2 to 8 units where the two s meet, and stubs at the counters' tips: 11 pieces under 8 units | continuous curves, none under 8 units; joins bent 3 to 25 degrees 15 to 2 (the two corners where the s meet) | the joins redrawn as single curves, then the outline settled |
| Quotes and apostrophe | tails 84 thick (skeleton) against stems of 220, a notch where the tail met the dot | 123; the same wedge, its inner side moved out, one outline with the dot | no print sets a comma or quote; the comma, quotes, semicolon, comma accents and apostrophe caron share the one drawing |
| Italic weight | stems 210 to 213, o 207 (the Regular 220, 216): narrowed by a plain transform | stems 219 to 222, o 216: every edge grown 4.4 across, each cut, slit and seam put back to its first-pass width (within 1.6) | grown by the drawing's own nodes, the whites restored as the slope shows them, by the side that ends there; ð, ½, ¼, ™ and the braces, whose hairline gaps the growth would close, keep the narrowing alone |
| Italic joins | 194 joins bent 3 to 25 degrees, 62 pieces under 8 units (the Regular 76 and 17) | 72 and 8 | settled on the grid after the slant (`scripts/settle.py`, pieces under 8 folded) |
| r | its arm's top 542 | 544, with n, m and h | a level edit, as the other flat tops |

### The third pass (what the second pass reported and left)

| What | Second pass | Now | Reasoning |
|---|---|---|---|
| ' and " | the builder's wedge, 160 by 116 units: skeleton weight 82 (median 57) against the curly quotes' and apostrophe's 123 (92), so it set grey beside them | the same wedge scaled by 1.53 about the middle of its top: 245 by 177, weight 124 (median 86); its taper (0.8 to 0.35 of the period's half width), proportions and top on the quotes' line kept | no print sets a straight quote; the curly quotes, the comma and the apostrophe set the punctuation's weight. The primes ′ ″, made from the straight quote, follow it (`constructions`, `straight_quotes`) |

### The fourth pass (a third review)

| What | Third pass | Now | Reasoning |
|---|---|---|---|
| Word space | 320 (Italic 320): 0.36 of the 897-unit n and 2.2 times n's sidebearings (3.0 to 6.7 in the other faces), held there by the builder's cap of `min(max(0.5 n, 220), 320)`; short Irish words (a, an, ar, na, i) ran into their neighbours in every line | 448 (Italic 435): half the n, the rule the builder sets every face's space by, without the cap; the no-break space is the same glyph | 320, 380, 400, 420, 448 and 470 were set in Irish and English at 14 to 28 px and at 48 px: from 400 the words part at 14 to 16 px, where 320 runs them together; 448 is the family's rule and the most that opens no holes (470 does, at 14 and 28 px); at 48 px it is generous but even. Its word white (the space with the letters' sidebearings beside it, 568 on average) is 4.9 times the white between letters, still the least in the family (5.7 to 9.2), so it is not loose for the face (`constructions`, `word_space`; `tuam_studio.word_space`) |

The traced í acute stays in the Study 3 fonts here. A stylistic alternate for it was not added: build2's stylistic
sets would carry it, but the alternate has to be made as a composite of the dotless i between the composites and
the spacing, where the release build has no Tuam step.

### The fifth pass (a fourth review, shared by the four faces)

One rule for all four faces corrects each of three defects (`scripts/symbols.py`, `scripts/build2.py`;
`judged-edits.json`, `fifth_pass`):

- **≈** stood 466 tall (23..489) against the ='s 365 (73..438), its waves 99 heavy against bars of 112 and 155
  apart where the bars stand 143. Its waves are now drawn at the bars' weight (109), centred on them on the 255.5
  axis, 0.7 of the ='s white apart (101; Italic 98): 425 tall (43..468).
- **Rings.** © ® @ ° ¤ had rings of 50 to 77 beside an o of 216; each is now at least half of it, 110 (Italic 109
  to 115). © and ® grow outward (690 to 773 tall; Italic 784) and @ (807 to 839), their letters as drawn, 31 to 35
  from the ring; ° has a counter of 77 (63 before) and ¤ one of 165 (237).
  The final review found © and ® taller than the figures and ° (163 to 297 tall) twice the bullet: © and ® keep the
  figures' 690 with a ring of 0.4 of the o grown inward, 88, the c and r drawn 0.92 to 0.95 as large and 29 to 31
  from it (`symbols.held_ring`); ° is no taller than 0.3 of the figures, 207, its ring 68 (Italic 61) and its
  counter as wide (71, Italic 74) (`heavier_ring`).
- **Combining marks.** The ponc construction sets ḃ's and ḋ's dot beside the ascender and ḟ's 60 above its stem,
  and the ponc's anchor was the only top anchor, so every top mark followed it: a diaeresis on b or d stood 64 and
  58 units into the ascender, and every mark stood 60 over f where it stands 30 over h, k and l. There was no mkmk
  (176 into each other), no anchor on a precomposed letter, the comma below ran 155 units into f's and j's
  descenders, and U+0323 had no glyph. The dot above keeps the ponc's anchor, so ḃ ċ ḋ ḟ ġ ṁ ṗ ṡ ṫ and base +
  U+0307 shape as before; every other top mark stands the face's accent gap, 30, from the letter's ink, as the
  precomposed accents do; precomposed letters carry anchors, mkmk stacks marks 30 apart, and the comma and the new
  dot below stand at least 30 clear.

## Open

- The cuts of v, w and 5, and the slits of d, p, q, s and 6, are N45's: the sheet resolves only the wider cuts.
  A sharper photograph of S53912 or the 30 pt S53911 would settle them.
- Accents other than the five fadas and all modern extensions are constructions.

## Reproduce

```sh
python scripts/fetch_sources.py --source N46 --format jpg
python scripts/fetch_sources.py --source N45 --format jpg
python scripts/fetch_sources.py --source B2
python scripts/consensus_trace.py tuam --output research/tuam-judgement/traces --report build/tuam-judgement/consensus
python scripts/build_original_study.py --face tuam --study 3 --traces research/tuam-judgement/traces --output research/tuam-judgement/fonts
pdfimages -j -f 164 -l 164 build/research/sources/Bolger-2017-volume-2-illustrations.pdf build/tuam-judgement/bolger/fig206
python scripts/tuam_sheet_check.py build/tuam-judgement/bolger/fig206-000.jpg --json research/tuam-judgement/sheet-check.json --preview build/tuam-judgement/sheet
python scripts/evidence_board.py tuam research/tuam-judgement/fonts/TuamUncialStudy3-Regular.otf \
    --evidence research/tuam-judgement/traces/evidence.json      # the boards, into build/judgement/tuam
(cd scripts && python audit_original_study.py --coverage --sources ../build/research/original-specimens \
    --traces ../research/tuam-judgement/traces --baseline ../research/round-03/tuam/fonts/TuamUncialStudy2-Regular.otf \
    --candidate ../research/tuam-judgement/fonts/TuamUncialStudy3-Regular.otf --output ../build/tuam-judgement/coverage-audit)
python scripts/glyph_proof.py research/tuam-judgement/glyphs.png research/round-03/tuam/fonts/TuamUncialStudy2-Regular.otf \
    research/tuam-judgement/fonts/TuamUncialStudy3-Regular.otf --glyphs a b c ...
python -m pytest -q tests/test_tuam_judgement.py
```
