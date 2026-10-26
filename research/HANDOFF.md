# Agent handoff: original-source reconstruction

## Active state

PR #1 merged into `main` on 25 October 2026 as
`573d554871d92a934aea333089b96c4b1237eba2`. All 123 tests pass on the merged
checkout, which also includes other contributors' 2.010 release and showcase work.
Research candidates remain separate. Read the
[shared continuation plan and work queue](../docs/superpowers/plans/2026-10-25-continuation.md)
for task ownership, dependencies, acceptance checks and release boundaries.
Next task: C1, Carrick N514 e/f evidence decision; currently unassigned.
Original source access is now reproducible through
[SOURCE-ACCESS.md](SOURCE-ACCESS.md): `python scripts/fetch_sources.py` retrieves
23 registered original/source files, excluding modern revivals, and verifies
their sizes and SHA-256 hashes. All 23 cached originals were checked; a fresh
N514 JPEG download also matched. Source-containing archive files remain local.

**Latest: [round 5](round-05/README.md), Carrick Study 2.** Ten isolated N513 mark
components recovered; two touching groups remain unassigned. Diaeresis stays
explicitly legacy; paired guillemets repeat the recovered outer shapes. All seven
directly comparable final marks improve against both N513 and N47. 133 derived
glyphs change; body letters remain as in Study 1. All 123 tests pass. Carrick checks
85,849 Latin-plus-punctuation pairs in each OTF/TTF; latest four-face domain totals
324,316 pairs. All are below the recorded collision threshold with kerning enabled.

**Carrick: [Study 3](round-06/README.md), round 6.** Fifteen lowercase letters (b to o, e and f
included, which resolves C1) redrawn from the averaged impressions on the N514 production sheets, with
each letter's pieces and counters read from its impressions, not from their mean; x and y traced from
N513 at last. Start Carrick work from round 6. Remaining: letters after q are not on the photographed
sheets.

**Kilfane: [Study 5](kilfane-sheet-frame/README.md)** is Study 4 with its sixteen production capitals averaged
again in the sheet's own frame (Letraset's spacing marks give each letter its upright and its line, so L no
longer takes N516's 3.5° lean). **[Study 4](kilfane-judgement/README.md), the judgement pass**, built on
[Study 3](kilfane-production/README.md) (capitals from the averaged N517 production impressions) and
round 2. Redrawn capitals keep N516's frame (Study 3's affine registration had let L, O, P and R drift
1–2% in size); T, U, k and l are traced from N516 at last, their fused ink divided at the narrowest
neck; the e's notch is eased as a recorded judged edit. `scripts/evidence_board.py` and
`scripts/pinches.py` are the review tools: every print of a glyph side by side, in the font's own
coordinates. Start Kilfane work from Study 4.

**Tuam Uncial: [Study 3](tuam-judgement/README.md), the judgement pass**, on round 3. Each glyph is traced
from the mean of N46 (a blurred photocopy) and N45 (a clean offset print) in N46's frame
(`scripts/consensus_trace.py`), so N46's ragged edges and pinholes go. Tuam is cut, not joined: N45 prints
cuts and slits N46's blur fills, and the production sheet photographed in Bolger fig. 206
(`scripts/tuam_sheet_check.py`) prints h, u, r and f in two pieces on every impression; Study 3 draws them,
and those of v, w, 5, d, p, q, s and 6 on N45's evidence. The five fadas keep the prints' own acutes; the
braces are drawn with a point. N47 and N44 do not print Tuam. Start Tuam work from Study 3. The release adds a
studio finishing pass ([judged-edits.json](tuam-judgement/judged-edits.json), `scripts/tuam_studio.py`): even cuts,
stems and x-height, the slits and seams at N45's widths, the dots and accents clear, and an Italic that keeps them.
A second pass (the same file and module) steepens í's acute so it is told from i at text sizes, sets the ponc of
ḃ and ḋ beside the ascender as Hayes's 1974 lettering does (Bolger fig. 204) and ḟ's 60 above the stem, draws the §
in continuous curves, gives the quotes a heavier tail, and gives the Italic the Regular's weight with its openings kept.

Next concrete source lead: N514 contains repeated isolated e/f on the upper sheet.
Round 5 records native crop coordinates. Compare local perspective and repeated
instances before accepting a replacement. It does not expose x/y; N517 does not
expose Kilfane T/U or lowercase k/l (Study 4 now separates them on N516). Do not redo the mark recovery or erase the
remaining diaeresis uncertainty. Review retained versus derived pieces explicitly.

**Céilí: [Study 4](ceili-judgement/README.md), the judgement pass** (branch `research/ceili-judgement`),
built on Study 3 and keeping its frame. Each of the 54 letters is the mean of N46 (photocopy) and N45
(offset), at one level for the whole face. Where the two prints disagree, a notch is filled; N44 decides
a protrusion wherever it prints the letter, and otherwise the protrusion is drawn as N45 has it.
`scripts/ceili_prints.py` is the review tool: one evidence board per letter. The sheet's síneadh fada is
the acute. The round dot (probably the ponc séimhithe) and the diamond are recorded, not built. The
ampersand stays closed, as N46 draws it: a recorded call. Start Céilí work from Study 4.

[Round 4](round-04/README.md), Céilí Study 3: Four named original
punctuation pieces replace the legacy cluster as construction inputs. Period,
comma and opposed quotes come from N45; 64 derived glyphs change, including dotted
letters and comma marks. Body outlines remain as in round 3. All 112 tests pass.
The new Céilí audit includes 89,401 Latin-plus-punctuation pairs per outline format,
plus stylistic-set checks. The four-family combined domain is now 312,996 pairs;
the other three faces retain Latin-only audits. Default kerning is required.

[Round 3](round-03/README.md): Tuam Uncial Study 2 reconstructs all 46
trace entries from N46. Céilí Study 2 reconstructs 54/55 entries, using N45 for
`b/e/e.alt1/h` and N46 for the others. The loose `DOTS` cluster remains legacy.
Use Kilfane Study 2 and Carrick Study 1 from [round 2](round-02/README.md), unchanged.
That checkpoint had 103 passing tests. Its four-family pair audit checks 302,556 Latin
character pairs with no intersections above four square font units. This is not
an optical spacing certification. The Study 1 account below is an earlier ledger.

Next priorities: optical spacing and small-size rendering across applications;
Kilfane's fused letters/zero/ambiguous lower marks; Carrick's e/f/x/y and unresolved
lower paired mark/inner chevrons;
unassigned upper Céilí punctuation pieces; Tuam's recomposed accent placement and source
disagreements. N45 was additionally checked for Kilfane T/U/k/l and Carrick e/f/x/y:
these still touch and do not provide clean isolated replacements.

Round 3's native-size audit uses pixel-centred area coverage (`--coverage`); old
polygon-fill scores cannot be directly compared with it. Higher overlap with N46
is not independent validation: Tuam's aggregate N45 fit slightly decreases.
Topology-aware smoothing preserves Céilí's exclamation dot and Tuam 8/9 openings.
Tuam a/o/zero openings also appear in N45; Bolger fig.206 repeats the o opening.
Read the per-entry exceptions and review decisions before changing them. The
small-size proofs use actual TTF rasterization, not screenshots of every app.

## Historical Study 1 ledger

The paragraphs below describe the first Kilfane iteration and its priorities at
that time. The active state above and continuation plan supersede those priorities.

The user wants accurate reconstruction from original evidence, with repeated
letter-by-letter inspection and no modern revival fonts used as design references.
Work on one face at a time. Kilfane Regular is first because multiple historical
reproductions are available. Research baseline: commit `b6af790` (release 2.000).

The earlier first candidate is committed in [kilfane-study-01/](kilfane-study-01/).
It is separately named **Kilfane Study 1**, version **2.001**, Regular only, in
OTF, TTF, WOFF and WOFF2. It is a research candidate, not a replacement release.
The existing released families and `sources/traced/` have not been modified.

## What changed

- 78 of 83 source trace entries were reconstructed. N516 supplies most; N47 supplies
  `v` and `w` because they touch on N516. `T`, `U`, `k`, `l` and the entry historically
  labelled `ornament` remain legacy traces. That last entry is actually loose marks.
- One uniform scale per source and row baselines preserve relative proportions.
  The existing builder still regularises text heights; the final font is not a
  literal transfer-sheet facsimile. New characters, punctuation assembly, spacing
  and kerning include modern construction inherited from the project.
- Preserve Q's secondary counter and open joins in `r`, `six`, `nine`.
  Remove G's tiny internal white fleck: repeated Gs on production-sheet photo N517
  support its interpretation as reproduction damage. Every such decision needs
  continued scrutiny when better evidence arrives.
- Per-glyph coordinates, source identity, calibration and retained entries are in
  `traces/evidence.json`; font construction provenance accompanies the fonts.
- Registration uses full-domain integer translation at a fixed source scale.
  An earlier ±5 px search biased the baseline; it was replaced and regression-tested.
  The provenance fix preserves construction labels while updating source attribution.

## Evidence and validation

| Source | Compared entries | Baseline mean IoU | Candidate mean IoU | Improved entries |
|---|---:|---:|---:|---:|
| N516 | 75 | 0.86808 | 0.93517 | 75 |
| N47 | 75 | 0.89534 | 0.94256 | 74 |

IoU is overlap of filled shapes after alignment. These are fits to training or
correlated reproductions, **not independent validation or authenticity scores**.
N516 and N47 share blemishes. `zero` regresses against N47 while improving against
N516; do not hide that disagreement. Semicolon is excluded because the builder
reassembles its vertical layout for text. Raw per-entry results are in `metrics.json`.

34 tests passed locally on Python 3.12/Windows: existing release checks plus source
segmentation, translation, topology, four-format sanitization, coverage, combining
marks, alternates and provenance. All 402 mapped code points are retained; the
candidate has 457 glyphs. Visual review included every newly sourced entry, source
labels, key counters against N46/N517, and text rendered from the actual candidate.

The existing kerning-envelope calculation emits an `All-NaN slice encountered`
RuntimeWarning for empty height slices. The fonts sanitize and shaping checks pass;
this does not replace a complete spacing review. Study dependencies and commands
are recorded in the candidate README. The original release toolchain uses Python 3.13.

## Next Kilfane iteration

1. Seek clearer `T`, `U`, `k`, `l` evidence, ideally repeated transfer-sheet letters
   with enough detail and controlled perspective. Do not split touching forms by
   arbitrary cuts without recording the uncertainty.
2. Resolve the loose-mark cluster at original scale, including components used for
   Irish fadas and séimhiú. Distinguish originally supplied marks from derived ones.
3. Investigate `zero` across more examples; keep both current source fits visible.
4. Review spacing, kerning, punctuation proportions, text rhythm, small-size rendering
   and overshoots. Matching a photocopy's silhouette is only one requirement.
5. Review all modern extensions against the chosen historical model, with provenance
   separated from attested characters. Preserve uncertain alternatives until resolved.

After Kilfane, Carrick has the next strongest source coverage (N513/N514/N47/N46).
Tuam needs better access to the originals behind Bolger figures 205–206. Céilí needs
a high-resolution full production sheet most urgently. See the main research index
for archive leads and historical corrections.

## Continuing safely and efficiently

Read [RIGHTS.md](RIGHTS.md), use `downloads.json` to identify exact source files, and
store downloads and illustrated audits under `build/`. Do not infer missing detail
with generative image enhancement. Preserve the native source and derive working
copies. Record any threshold, blur, correction or geometry change.

Rebuild the candidate, run meaningful tests, and inspect comparisons before claiming
an improvement. Keep per-glyph regressions and retained legacy entries visible.
No new source enquiry, purchase, publication of archive pixels or release merge has
been performed as part of this research handoff.
