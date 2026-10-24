# Kilfane original-source iteration implementation plan

> **For agentic workers:** Use superpowers:executing-plans for this inline iteration. Steps use checkboxes.

**Goal:** Produce a source-supported Kilfane Regular research candidate and inspectable evidence.
**Architecture:** Keep the release intact. A source-analysis tool maps glyph regions and builds candidate trace records in a separate build folder. Existing Font2 builds the candidate. Additional source comparisons and explicit metadata accompany the output; N516/N47 proved to be correlated reproductions.
**Tech stack:** Python, Pillow, NumPy/SciPy, scikit-image, fontTools, skia-pathops, existing curve fitter.
**Spec:** ../specs/2026-10-24-kilfane-originals-design.md

## Global constraints
- Original specimens only; no revival-font reference.
- Preserve originals and released fonts. The subsequent user instruction authorises pushing research and openly redistributable source evidence; unclear archive-media rights are handled with links and metadata rather than mirrored images.
- One face at a time; Kilfane first.
- Measurements and visual checks both required; scores are not historical authentication.

## Review focus
- Detached dots and counters must survive segmentation.
- Source scaling must preserve proportions and must not fit away individual glyph differences.
- A failed/mismatched segmentation must fail visibly.
- Candidate paths must not silently fall back to old geometry.
- Legacy-derived accents and new stylistic expansions must remain explicitly identified.

## Tasks
- [x] Establish exact source regions and baseline font evidence, with all glyph labels visually checked.
- [x] Add tested reusable source segmentation/normalisation helpers in scripts/source_study.py; tests/test_source_study.py checks detached marks, counters and count mismatches.
- [x] Generate candidate trace JSON plus per-glyph provenance outside sources/traced. Compare available original reproductions, examine every candidate glyph, and retain uncertain glyphs explicitly.
- [x] Build a separately named research regular with the existing pipeline; validate output/shaping and counter preservation. Keep the release unchanged.
- [x] Deliver before/source/after visual evidence, candidate font formats, reproducible code and an iteration ledger under outputs/kilfane-iteration-01.

## Ledger
- User supplied direction and execution intent in the conversation; proceeding without an additional design-approval pause.
- Isolated clone on research/kilfane-originals; existing release is the baseline.
- 78/83 entries retraced; T/U/k/l and loose-mark cluster retained. Full candidate has 457 glyphs / 402 code points; new entries propagate to modern constructions.
- Ruling: matching blemishes show N516 and N47 share reproduction history; report them as correlated reproductions, not independent masters.
- Ruling: preserve source-supported Q secondary counter and r/6/9 open joins; remove G's small print-damage hole using transfer-sheet evidence.
- Fresh review identified restricted registration search and provenance overwriting. Added regression checks, implemented full-domain translation, retained construction metadata and updated derived source references.
- Final image fit: N516 0.86808 -> 0.93517; N47 0.89534 -> 0.94256. 75 comparable entries each; semicolon excluded because builder resets its layout. Zero remains worse against N47 and is explicitly unresolved.
- Verified during the local iteration: 34 tests pass; OTS on four candidate formats; accent equivalence; alternates; original release/traces unchanged. Visual inspection of all newly sourced entries. Subsequent publication work packages the candidate and metadata under research/ without promoting a release.
- Next work: clean T/U/k/l references or justified separation, loose-mark evidence, zero reproduction discrepancy, spacing and small-size proofing; only then advance beyond Kilfane Regular.
