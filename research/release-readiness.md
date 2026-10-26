# Release readiness: 3.000 candidate from the original-source studies

Task R1 in the [continuation plan](../docs/superpowers/plans/2026-10-25-continuation.md).
This is a proposal, not a release: `fonts/`, `sources/traced/`, the release metadata
and the showcase still carry 2.101 (2.010 renamed "Digital" and dedicated to the public domain; outlines unchanged). Promotion
needs the user's explicit approval.

## What the candidate is

All twelve styles, under release names and version 3.000, built by
`make candidate` (`scripts/build_candidate.py`) into ignored `build/candidate/fonts`.
Each Regular is the latest accepted study's construction: same traces, named marks,
punctuation and evidence decisions, through `build_original_study.study_class()`.
Its outlines match the committed study glyph for glyph. The one exception is a
1.9-unit² speck hole in Céilí Study 3's ©, which the final clean-up now drops.
The 2026 bold and sloped styles are derived from those Regulars, as the release
derives them from the flyer.

| Face | Study and traces | Traced from | Kept from the flyer | Median ink change from 2.010 | Lowercase mean advance |
|---|---|---|---|---:|---:|
| Kilfane | Study 4, `kilfane-judgement` (on round 2 and Study 3) | N516 alphabet specimen; N517 means for 16 capitals; N47 for v, w | loose-mark cluster | 18% | 507 → 501 |
| Carrick | Study 3, `round-06` (on round 5) | N514 production-sheet means for b to o; N513 for a, p to z, figures, marks | the lower paired mark | 29% | 659 → 634 |
| Tuam Uncial | Study 2, `round-03` | N46 (NIVAL's copy of the flyer) | none | 8% | 850 → 857 |
| Céilí | Study 4, `ceili-judgement` (on Study 3) | mean of N46 and N45 for all 54 letters, N44 deciding where they disagree; N45 punctuation; the N45/N46 síneadh fada | the loose dots (DOTS) | 30% | 611 → 620 |

"Ink change" is the share of each glyph's ink that differs from 2.010 at 2 units per
pixel, with glyphs aligned at the left of their ink so spacing changes don't count. It
measures how far the release moves, not authenticity. The sources' own limitations are in each
round's `evidence.json`: N46/N45 and N513/N47 share reproduction history, so their
agreement is not independent confirmation.

Proofs (font-only): [Kilfane](release-candidate/proofs/kilfane.png),
[Carrick](release-candidate/proofs/carrick.png), [Tuam Uncial](release-candidate/proofs/tuam.png),
[Céilí](release-candidate/proofs/ceili.png). Each sets the same lines in the release and in
the candidate, style by style.

Carrick's candidate is [Study 3](round-06/README.md): b to o from the averaged N514 production
impressions, each letter's pieces and counters read from its impressions (b's bowl closes and m's
strokes stand apart, as every production sheet prints them), x and y separated on N513.

Kilfane's candidate is [Study 4](kilfane-judgement/README.md), the judgement pass: capitals from
the production sheets held to N516's frame, T, U, k and l traced from N516, and the e's notch eased
(a recorded judged edit). The candidate also sits Kilfane's square stem feet (F, P, V, 4, 7, the
roman alternates) on the baseline instead of 8 units below it (`FLAT_FOOT_WIDENING`, Kilfane only:
the other faces' feet have not been reviewed).

Céilí's candidate is [Study 4](ceili-judgement/README.md), the judgement pass. Each letter is the mean
of N46 (the leaflet, a photocopy) and N45 (the brochure, offset), at one level for the whole face, in
Study 3's frame. Where the two prints disagree, a notch is filled. A protrusion is decided by the
cover heading N44 where it prints the letter, and otherwise drawn as N45 has it (a tip the photocopy
lost). Study 4 also takes the sheet's síneadh fada as its acute, sits the 8 on the line and keeps
Study 3's line baselines. It holds no judged edit to any outline. Its 30% change from 2.010 (Study 3:
18%) is mostly weight and edge noise: the hairlines are heavier and evener, and the letters a little
wider. The family line is 974/−251 (Study 3: 961/−251).

## The 2026 styles (modern extensions)

The pen model was written for the flyer, where any gap under a quarter of a stem is a
photocopy sliver. The sheets draw narrower things, and the first candidate build
failed the bold topology check on 22 Kilfane glyphs. The fixes are in `scripts/bolden.py`
and `scripts/build2.py`. Every released 2.010 font, in all four formats, rebuilds
byte-identical with them.

- **Hollow letters.** Uniting an outline with its stroke could leave a whole letter as a
  hole (Y and 3 from N516). `grow()` now checks its result and falls back only when unsound.
- **Open joins.** Kilfane's r, 6, 9 and g, and the joins of Tuam's 8 and 9, cross narrow
  slits that the research says to preserve. Builds from the sheets treat only gaps under
  0.05 stem as slivers. Any space the Regular leaves open but the Bold encloses is reopened
  as a hairline crack along the Regular's passage, so the Bold keeps its weight on both sides.
- **Small counters.** Q's second counter and the 4 of the fractions keep at least 36% of
  their area as well as 55% of their radius.
- **Separate pieces.** The dots of Céilí's ! and ? are cut apart from their strokes along
  the midline between them. Study 4's Bold left the ? dot 1.6 units from its stroke without
  joining them, and the Bold Italic then joined them. Study 4 therefore also sets apart dots that the
  Bold only brings close (`derived_styles` in its evidence, `bolden._separate(close=True)`).
  The Bold's ? gap is now 9.7 units and the Bold Italic's 8.0.
- **Named source punctuation.** In the first build, Céilí's N45 period, comma and quotes
  stayed at Regular weight in the Bold. They are now bolded like the sheet's loose marks.
- **Sloped styles.** The italics' small extra weight goes through the same protection
  wherever it changes a glyph's topology. In Céilí Study 4's Italic, that weight came out
  unsound on oe: part of the e became a hole and the eye was lost. Study 4 grows any outline that fails
  the check again after simplifying it. oe is the only one that fails.

Topology after the fixes (`scripts/topo.py`, pieces and counters per glyph):

| Pair | Flagged | Disposition |
|---|---|---|
| Kilfane Regular → Bold | none | |
| Kilfane Regular → Italic | none | |
| Kilfane Bold → Bold Italic | none | (Study 2 flagged ŋ: a slit under 4 units; gone with Study 4.) |
| Céilí Regular → Bold | 6 | Joins by design (`BOLD['ceili']['joins']`), as in 2.010. Accept. |
| Céilí Regular → Italic, Bold → Bold Italic | none | Study 4 first flagged oe (Italic) and ?, ¿ (Bold Italic). Both are repaired in Study 4's derived styles, as above. |
| Carrick Regular → Italic | ©, ™, ¾ | At their small size the hairline gaps between the pieces of c, m and 3 (c and m now drawn from the production sheets) are a few units wide and close under the slope; invisible at any size. Accept. |
| Tuam Regular → Italic | @, } | @ also flags in 2.010. The } waist pinches to two pieces in the Regular itself (see below). Fix the brace construction before release. |

## Checks run on the candidate

| Check | Result |
|---|---|
| `FONTDIR=build/candidate/fonts pytest tests/test_release.py tests/test_shaping.py` | 20 of 21 pass. Style linking fails only because the expected version is the release's (2.101). Bold counters: 0 flags beyond the designed Céilí 6. The "Digital" naming check passes. |
| Pair collisions, all 12 styles ([summary](release-candidate/pair-audit.json)) | 0 collisions in 1,346,872 HarfBuzz-shaped pairs: Latin letters, figures and punctuation, default features (Céilí rerun with Study 4) |
| OTS, 48 files (OTF, TTF, WOFF, WOFF2) | no failures (rerun with Céilí Study 4) |
| Font Bakery `check-universal`, per family | 0 FAIL, 0 ERROR; the same two WARN kinds as 2.010 (decomposed carons, contour counts). Not yet rerun with Céilí Study 4 |
| Full test suite on the committed fonts | 172 pass; the release rebuilds byte-identical |

## Before promotion

1. **Q1, optical spacing and rendering, per face.** Not done. The candidate keeps the
   studies' spacing protection (`*.spacing-adjustments.json`, per style) and the release's
   class kerning. Nobody has yet reviewed it as text in Irish prose at 12–32 px in real applications.
2. **Tuam braces.** Both 2.010 and the candidate cut a notch into the brace's waist. In
   the candidate it pinches the Regular into two pieces. Redraw the point.
3. **Independent review of the source interpretation**, as the plan requires, using the
   exact study commits above.
4. **Open source issues stay open.** Carrick's e/f/x/y are resolved in Study 3 (C1/C2: e and f from
   the production sheets, x and y separated on N513); its lower paired mark stays unassigned. The same
   goes for Kilfane's zero disagreement (T/U/k/l are traced from N516 in Study 4), Céilí's upper pieces (Study 4 builds the fada;
   the round dot, probably the ponc séimhithe, and the diamond stay recorded, not built) and its ampersand join, and Tuam's N45/N46
   disagreements and recomposed accents. Each glyph's provenance file already labels it
   as traced, retained legacy or modern construction.

## Proposed release mechanics, when approved

- `make fonts` builds through `scripts/build_candidate.py` (the traces map in `LATEST`).
  `VERSION = '3.000'`. CI's byte-identical check then pins the new outputs.
- FONTLOG and README: what changed per face, the sources, retained legacy glyphs, and the
  2026 styles' new rules.
- Regenerate the specimen, CSS, the showcase data (its research panels become the release),
  the download ZIP and the deploy branch.
- Rollback: 2.010 stays tagged (`v2.010`, local until pushed), and every study stays in
  `research/`. Installed side by side, 3.000 replaces 2.010 under the same family names, as
  any release does.

Base: `e3a4ba9` on `main`. Work on branch `candidate/release-3`.
