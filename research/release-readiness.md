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
| Kilfane | Study 4, `kilfane-judgement` (on round 2 and Study 3) | N516 alphabet specimen; N517 means for 16 capitals; N47 for v, w | loose-mark cluster | 17% | 507 → 501 |
| Carrick | Study 3, `round-06` (on round 5) | N514 production-sheet means for b to o, in the sheet's own frame; N513 for a, p to z, figures, marks | the lower paired mark | 26% | 659 → 636 |
| Tuam Uncial | Study 3, `tuam-judgement` (on round 3) | N46 and N45 averaged in N46's frame; cuts confirmed on the S53912 production sheet (Bolger fig. 206) | none | 9% | 850 → 850 |
| Céilí | Study 3, `round-04` | N46; N45 punctuation | the loose dots (DOTS) | 18% | 611 → 614 |

"Ink change" is the median, over the code points both map, of the share of each glyph's ink
that differs from 2.010 (outlines unchanged in 2.101) at 2 units per pixel, with glyphs aligned
at the left of their ink so spacing changes don't count; the advance is the mean of a to z. Both
come from `scripts/candidate_change.py`, one count for every row. They measure how far the
release moves, not authenticity. The sources' own limitations are in each
round's `evidence.json`: N46/N45 and N513/N47 share reproduction history, so their
agreement is not independent confirmation.

Proofs (font-only): [Kilfane](release-candidate/proofs/kilfane.png),
[Carrick](release-candidate/proofs/carrick.png), [Tuam Uncial](release-candidate/proofs/tuam.png),
[Céilí](release-candidate/proofs/ceili.png). Each sets the same lines in the release and in
the candidate, style by style.

Carrick's candidate is [Study 3](round-06/README.md): b to o from the averaged N514 production
impressions, each letter's pieces and counters read from its impressions (b's bowl closes and m's
strokes stand apart, as every production sheet prints them), x and y separated on N513. The letters
keep the sheet's own geometry: Letraset's spacing marks give each one its upright and its line, so
they no longer take N513's slants (l's 5.5° lean among them), and n and o no longer float above the
baseline. As for Kilfane, the candidate sits Carrick's slanted stem feet on the baseline.

Tuam's candidate is [Study 3](tuam-judgement/README.md), the judgement pass: each glyph traced from the mean
of the flyer (N46, a blurred photocopy) and the catalogue (N45, a clean offset print), so N46's ragged edges
and pinholes are gone; Tuam's drawn cuts kept where N45 prints them and N46's blur fills them (h, u, r and f
in two pieces on every impression of the production sheet; v, w, 5 and the slits of d, p, q, s, 6 on N45's
evidence); the five fadas as the prints set them (í's short acute; a `ccmp` ligature for the decomposed
forms); and the braces drawn with a point. The lowercase advance is 854 by the same count for the Study 2 candidate.

Kilfane's candidate is [Study 4](kilfane-judgement/README.md), the judgement pass: capitals from
the production sheets held to N516's frame, T, U, k and l traced from N516, and the e's notch eased
(a recorded judged edit). The candidate also sits Kilfane's square stem feet (F, P, V, 4, 7, the
roman alternates) on the baseline instead of 8 units below it (`FLAT_FOOT_WIDENING`, Kilfane and
Carrick: Tuam's and Céilí's feet have not been reviewed).

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
  the midline between them.
- **Named source punctuation.** In the first build, Céilí's N45 period, comma and quotes
  stayed at Regular weight in the Bold. They are now bolded like the sheet's loose marks.
- **Sloped styles.** The italics' small extra weight goes through the same protection
  wherever it changes a glyph's topology.

Topology after the fixes (`scripts/topo.py`, pieces and counters per glyph):

| Pair | Flagged | Disposition |
|---|---|---|
| Kilfane Regular → Bold | none | |
| Kilfane Regular → Italic | none | |
| Kilfane Bold → Bold Italic | none | (Study 2 flagged ŋ: a slit under 4 units; gone with Study 4.) |
| Céilí Regular → Bold | 6 | Joins by design (`BOLD['ceili']['joins']`), as in 2.010. Accept. |
| Céilí Regular → Italic, Bold → Bold Italic | none | |
| Carrick Regular → Italic | ©, ™, ¼, ¾ | At their small size the hairline gaps between the pieces of c and m (drawn from the production sheets) are a few units wide and close under the slope; the small 4 of the fractions keeps a barely open counter, as it does in 2.101's Italic. Invisible at text sizes. Accept. |
| Tuam Regular → Italic | @, ˚ | @ also flags in 2.010: the a inside it nearly touches the ring (necks of 8 units). The spacing ring ˚ (U+02DA) loses its counter in the Italic, as in the released 2.101 Italic; the combining ring and å keep theirs. The braces, drawn with a point since Study 3, no longer flag. |

## Checks run on the candidate

| Check | Result |
|---|---|
| `FONTDIR=build/candidate/fonts pytest tests/test_release.py tests/test_shaping.py` | 20 of 21 pass. Style linking fails only because the expected version is the release's (2.101). Bold counters: 0 flags beyond the designed Céilí 6. The "Digital" naming check passes. |
| Pair collisions, all 12 styles ([summary](release-candidate/pair-audit.json)) | 0 collisions in 1,346,872 HarfBuzz-shaped pairs: Latin letters, figures and punctuation, default features (Tuam rerun on Study 3: unchanged, 108,900 per style) |
| OTS, 48 files (OTF, TTF, WOFF, WOFF2) | no failures (Tuam rerun on Study 3: 8 files, no failures) |
| Font Bakery `check-universal`, per family | 0 FAIL, 0 ERROR; the same two WARN kinds as 2.010 (decomposed carons, contour counts); Tuam rerun on Study 3: the same |
| Full test suite on the committed fonts | 173 pass (18 for Tuam Study 3); the release rebuilds byte-identical |

## Before promotion

1. **Q1, optical spacing and rendering, per face.** Not done. The candidate keeps the
   studies' spacing protection (`*.spacing-adjustments.json`, per style) and the release's
   class kerning. Nobody has yet reviewed it as text in Irish prose at 12–32 px in real applications.
2. **Tuam braces.** Done in the candidate: since Tuam Study 3 the brace is drawn as one outline with a
   point (`symbols.pointed_brace`, on for that study only). The released 2.101 braces still have the
   notch cut into the waist and small spurs at the tip; they change only when the candidate is promoted.
   Tuam's @ and the Italic's spacing ring ˚ still flag (see the topology table).
3. **Independent review of the source interpretation**, as the plan requires, using the
   exact study commits above.
4. **Open source issues stay open.** Carrick's e/f/x/y are resolved in Study 3 (C1/C2: e and f from
   the production sheets, x and y separated on N513); its lower paired mark stays unassigned. The same
   goes for Kilfane's zero disagreement (T/U/k/l are traced from N516 in Study 4) and Céilí's unassigned punctuation. Tuam's N45/N46
   disagreements and its five fadas are resolved in Study 3; the cuts of v, w and 5 and the slits of d, p, q, s and 6
   rest on N45 alone (the production sheet is too coarse for them), and Tuam's other accents remain constructions. Each glyph's provenance file already labels it
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
