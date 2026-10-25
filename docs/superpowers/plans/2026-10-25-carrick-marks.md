# Carrick named marks, round 5

Continue the authorised original-source study on research/kilfane-originals.
Baseline 358f4ee. Existing historical reconstruction design applies; no release
merge. Publish generated software and analysis only, following research/RIGHTS.md.

## Evidence and scope
N513 has ten isolated components: two rules, dot, acute, circumflex, two rings,
tilde and the two outer opposed chevrons. The inner opposed chevrons touch; the
lower paired shape also touches and is not confidently identified. N47 repeats
these features but can share source history. N514 has repeated isolated e/f, but
photographic distortion and variant detail need a dedicated later comparison.

Build Carrick Study 2 from unchanged Study 1 body traces plus named mark inputs.
Trace the ten isolated components at the existing uniform N513 scale. Preserve
both ambiguous components as unassigned records. Retain the existing diaeresis
construction explicitly as legacy; do not relabel it newly recovered. Construct
paired guillemets by repeating each newly recovered outer chevron at the inherited
0.88-width pitch, identifying that repetition as modern construction.

## Steps
1. Add tests for evidence, original component preservation, retained diaeresis,
   four-format sanitation/coverage, body stability, combining marks and pairs.
   Expected first run: missing candidate.
2. Add tracer and source-aware builder provenance. Compare the actual font's
   direct marks with N513/N47, examine rings and detached contours, and inspect
   all materially changed glyphs. Expected: supported silhouettes; explicit
   disagreement rather than selecting only improved comparisons.
3. Run full checks, one fresh review, fix material defects, package the latest
   four-font set and public evidence, validate clean committed artifacts, push,
   and verify CI. Existing releases remain unchanged.

## Review focus
Distinguish directly traced, derived and retained pieces; retain ring counters;
ensure Carrick provenance never names Kilfane's N516 source; verify chevron
direction/repetition and uncertain diaeresis handling; check all affected marks
and punctuation through real font shaping. Correlated scans do not authenticate.

## Ledger
- Native N513/N47 clusters inspected; ten isolated and two touching components.
- Ruling: preserve the lower paired shape unassigned and retain the old diaeresis.
  Neither reproduction proves its identity or isolated outlines. Cost: the legacy
  diaeresis may still encode an earlier mistaken interpretation.
- Ruling: paired guillemets repeat the clean outer shapes at inherited pitch.
  Cost: asymmetry or spacing of the hidden inner pieces is not recovered.
- Ruling: defer N514 e/f outline changes until local perspective and repeated
  instances are compared. Cost: those legacy letters remain temporarily retained.
- Nine initial new checks passed; full suite 121 passed. Seven mapped final marks
  improve against each of N513 and N47. 85,849 Latin-plus-punctuation pairs pass in
  each OTF/TTF. All 133 materially changed glyphs were inspected. The first proof
  canvas clipped lacute; expanded it and verified every contour coordinate fits.
- Fresh review found no outline or shaping blocker; independently ran nine tests
  and inspected all proof pages and source assignments. P2: stale inherited evidence
  still called all marks legacy. P3: macron named only one rule although weight is
  averaged from both. Regrade the latter P2 because it misstates the reproducible
  construction rule in this evidence-focused task. Both enter one correction pass.
- Ruling: original-master authentication, universal optical spacing and arbitrary
  mark stacks remain unclaimed. Cost: print distortion or untested layouts may
  remain. Reviewer also deferred packaging/CI to parent; verify those separately.
- Both evidence regressions failed against the old records and pass after the
  single correction pass. Final packaged-artifact suite: 123 passed. Corrected
  the pair-audit method text to describe only the two formats actually checked.
- Verified all 28 round-5 artifact hashes, research JSON and documentation links,
  and the exact allowlist of font-only proof images. No archive media added.
  All 16 downloadable fonts byte-match the current research candidates; ZIP
  integrity passes. Review controls and asset paths pass DOM-stub checks; this
  is not a browser-rendering claim. Clean committed checkout and CI follow.
