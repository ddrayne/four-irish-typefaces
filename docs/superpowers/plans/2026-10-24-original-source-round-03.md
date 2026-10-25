# Original-source round 3

Continue the user-authorised historical reconstruction, using the existing design
specification and inline executing-plans workflow. Baseline: c3e80db. Publication
to the existing research branch and PR is already authorised. No release merge.

## Constraints and decisions
- Original historical sources only; no modern revival outline references.
- Work on Tuam, then Céilí. The N46 flyer is larger than the release's source;
  compare against N45's competition brochure and available production examples.
- Keep native image bytes, record hashes and explicit component identities.
- Uniform source calibration; do not silently stretch individual source shapes.
- Retain unresolved touching forms and record all regressions, not only successes.
- Separately named Study 2 candidates; preserve round 2 and released fonts.
- Public repository receives generated software/analysis only, never archive pixels.

## Tasks and verification
1. Inspect and label N46/N45 regions for Tuam and Céilí. Record which entries
   can be recovered, which need multiple detached components, and which touch.
   Expected: every accepted region has a visual identity and exact source hash.
2. Add candidate-artifact tests before the new builds exist. Reconstruct accepted
   Tuam regions, retain uncertain entries, build Study 2, inspect every overlay,
   and compare N46/N45. Repeat for Céilí, preserving thin strokes and alternates.
   Expected: source-fit and topology evidence supports every accepted change;
   failures or regressions receive an explicit decision.
3. Validate actual candidate binaries in all formats, coverage, mark shaping,
   alternate sets and full Latin pair intersections. Inspect text at multiple sizes.
   Expected: no unexplained test failure; no claim of finished optical typography.
4. Obtain one fresh review of the completed changes, fix material findings, and
   package local comparisons and public evidence with checksums and continuation
   notes. Run checks from clean committed files, push and verify CI.

## Ledger
- Round 2 GitHub push and pull-request builds both succeeded.
- Existing clean research checkout reused. No implementation overlap with other agents.
- Pre-flight: tracers produce the trace/evidence/region schemas already consumed by
  build_original_study and audit_original_study. Tests must select a new round-03
  directory so round-02 outline-equality assertions continue to validate round 2.
- Ruling: the existing source evidence permits a meaningful new outline pass even
  without a newly acquired master scan; source resolution and correlation limits
  remain explicit. Do not postpone measurable improvements indefinitely.
- Inspection: all 46 Tuam entries and 54 Céilí entries have explicit source regions;
  Céilí's loose punctuation cluster remains legacy pending a named-piece mapping.
- Ruling: N46 supplies the production-flyer target; N45 supplies Céilí b/e/e.alt1/h
  where detail is clearer. Brochure-only proposals were built and compared, but
  their broad deterioration against N46 does not support wholesale substitution.
  Reproduction discrepancies remain visible; fidelity to a single original master
  is not established. Cost if wrong: some source-specific distortions may remain.
- The initial topology test incorrectly assumed b and p have closed bowls. Native
  enlarged crops show deliberate gaps; the test now preserves the observed joins.
- Audit diagnosis: inclusive native-pixel polygon fills inflate edges, materially
  biasing thin-stroke comparisons. A pixel-centred 8x8 area sampler preserves
  square area, fractional edges and counters (two regression tests RED→GREEN).
  Round 3 metrics use this explicit method; earlier saved metrics are not rewritten.
- Disable the old Céilí h-from-n repair and e eye-bridge/minimum-stroke patches only
  for the new brochure-derived entries. Original release and round 2 stay unchanged.
  Provenance tests reproduced the old repair and Tuam accent-source mislabelling,
  then passed with the conditional builder adapters.
- One fresh reviewer completed the planned review. Critical findings: none.
  Important finding accepted: smoothing merged Céilí exclamation components and
  closed Tuam eight/nine openings. Specific binary checks failed before the fix
  and pass after topology-preserving smoothing. All 103 tests pass on the build.
  Minor findings: none. No second review loop is requested.
- Review rulings: authentication remains unclaimed because reproductions may be
  correlated; app-wide rasterization and optical spacing remain separate work.
  Source openings are preserved, not interpreted as conclusive master-artwork
  intent. N45 and production repeats strengthen a/o/zero evidence, not every gap.
  Cost of preserving a reproduction defect: an unintended hairline may remain;
  closing it without evidence would erase an equally plausible original detail.
- Additional topology audit: 93/95 direct entries match substantive contour counts.
  Tuam d and dollar lose only small white flecks at 7.08 and 6.03 native px²;
  substantial counters remain. These exceptions are retained and recorded.
- N45 follow-up: Kilfane T/U/k/l and Carrick e/f/x/y remain touching. No new cuts
  or speculative isolated replacements are justified by this reproduction.
- Small-size actual-TTF proofs were inspected at 12, 16, 20, 24 and 32 px. Local
  review includes all comparisons; public proofs contain only rendered fonts.
