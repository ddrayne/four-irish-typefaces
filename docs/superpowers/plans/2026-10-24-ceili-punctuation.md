# Céilí named punctuation pass

Baseline: 3451387 (round 3). Continue the existing original-source design and
inline execution workflow. User-authorised research branch push; no release merge.

## Evidence and scope
N45's row at [755,665,1430,770] shows isolated period (17), comma (18), opening
quote (6) and closing quote (7), at threshold 130 with 8-connected labels.
Colon and semicolon provide repeat dots/tails (14/19 and 15/16). N46 also preserves
the semicolon's comma tail and quotation shapes. The current builder invents a
comma tail and selects legacy DOTS contours by proximity. Replace those four
inputs with explicitly named traces; keep text placement and composed punctuation
declared as modern construction. Unassigned upper pieces stay unassigned.

## Tasks
1. Add candidate tests for source attribution, actual source-piece silhouettes,
   four-format sanitation/coverage, unchanged body outlines, shaping and Latin
   collision protection. Run before candidate exists. Expected: missing candidate.
2. Trace four pieces at the round-3 uniform N45 scale. Add an optional source-parts
   hook to punctuation construction; preserve default release behaviour. Build
   Céilí Study 3. Compare source silhouettes against N45 and N46, inspect punctuation
   strings and all changed glyphs. Expected: attributable shapes and explicit
   disagreements; no invented replacement for unresolved source detail.
3. Run all tests, obtain one fresh review of this pass, fix material findings with
   regression checks, package source-free public records and local comparisons,
   verify clean committed artifacts, push and check CI.

## Review focus
Check source component identities and coordinate transforms; whether quotation
direction and comma descenders survive; whether the default release build changes;
whether derived marks and punctuation retain truthful provenance; whether updated
spacing/kerning still protects punctuation and marks. Scores do not settle intent.

## Ledger
- Round 3 passed 103 tests both locally and from a clean committed archive, with
  artifact hashes, document links and archive-media exclusions verified. Pushed.
- Ruling: N45 comma/period/quotes are direct source shapes, but text heights and
  repeated dots/quotes remain modern layout. Original sheet spacing is not a text
  spacing specification. Cost if wrong: source-relative placement is not preserved.
- Ruling: keep three ambiguous upper N45 pieces outside this pass; they are not
  required to replace the clearly identified punctuation. Cost: those potential
  original symbols remain unrecovered.
- Tests first failed for absent named punctuation as expected. Initial body test
  also included accented alternates, whose dots intentionally change with the new
  period. Restrict body invariance to unaccented letters and their alternates;
  validate accented forms separately through actual decomposed shaping.
- Round 3 push and pull-request CI builds both succeeded at 3451387.
- Apostrophe caron provenance initially named the comma, but the builder uses
  quoteright. A targeted provenance check failed, then passed with that correction.
- Source comparison initially used a zero baseline, placing glyphs outside the
  raster before registration. Per-piece initial baselines now place prior outlines
  inside the frame; full integer translation and fixed source scale remain the only
  fitted transforms. This is shape comparison, not historical layout measurement.
- Nine new tests and all earlier checks pass (112 total). Named-piece silhouettes,
  unaccented bodies, decomposed marks and source attribution are covered. Expanded
  pair audit: 89,401 pairs in each OTF/TTF, plus 1,444 for each stylistic set, zero
  intersections above four square font units. All 64 changed-glyph proof entries
  and the source overlays were visually inspected; source scores improve 4/4 twice.
- One fresh reviewer: no material findings or deferred minors. Independently ran
  all nine new tests, inspected source identities/transforms and compared default
  punctuation for the four Regular faces. Parent additionally checked identical
  punctuation-stage paths/provenance across all twelve release styles.
- Final ruling: historical authentication and three upper pieces remain unresolved;
  no geometry is invented for them. Cost: possible originals remain unavailable.
- Final ruling: N46's faint comma tail is incomplete at the segmentation threshold;
  use N45 and disclose the N46 limitation beside the score. Cost: N45 print spread
  may persist in the candidate tail.
- Final ruling: public packaging, committed checks and CI were outside the fresh
  review. Parent must finish those before publication claims; no reviewer assurance
  is inferred for them.
