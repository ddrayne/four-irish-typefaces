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

## Open

- The cuts of v, w and 5, and the slits of d, p, q, s and 6, are N45's: the sheet resolves only the wider cuts.
  A sharper photograph of S53912 or the 30 pt S53911 would settle them.
- The cuts and slits are as printed, so their widths vary: at their narrowest, 20 to 36 units for h, n, u, r
  and f, 12 for v, w and 5, and 8 where p's hook meets its stem. A studio might even them out; no judged edit
  has been made.
- Accents other than the five fadas, the accents' vertical gap and all modern extensions are constructions.
- The builder's text-height regularisation and spacing protection are unchanged from round 3.

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
