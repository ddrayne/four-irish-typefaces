# Agent handoff: original-source reconstruction

## Active state

**Latest: [round 3](round-03/README.md).** Tuam Uncial Study 2 reconstructs all 46
trace entries from N46. Céilí Study 2 reconstructs 54/55 entries, using N45 for
`b/e/e.alt1/h` and N46 for the others. The loose `DOTS` cluster remains legacy.
Use Kilfane Study 2 and Carrick Study 1 from [round 2](round-02/README.md), unchanged.
There are 103 passing tests. The four-family pair audit checks 302,556 Latin
character pairs with no intersections above four square font units. This is not
an optical spacing certification. The Study 1 account below is an earlier ledger.

Next priorities: optical spacing and small-size rendering across applications;
Kilfane's fused letters/zero/ambiguous lower marks; Carrick's e/f/x/y and marks;
named Céilí punctuation components; Tuam's recomposed accent placement and source
disagreements. N45 was additionally checked for Kilfane T/U/k/l and Carrick e/f/x/y:
these still touch and do not provide clean isolated replacements.

Round 3's native-size audit uses pixel-centred area coverage (`--coverage`); old
polygon-fill scores cannot be directly compared with it. Higher overlap with N46
is not independent validation: Tuam's aggregate N45 fit slightly decreases.
Topology-aware smoothing preserves Céilí's exclamation dot and Tuam 8/9 openings.
Tuam a/o/zero openings also appear in N45; Bolger fig.206 repeats the o opening.
Read the per-entry exceptions and review decisions before changing them. The
small-size proofs use actual TTF rasterization, not screenshots of every app.

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
