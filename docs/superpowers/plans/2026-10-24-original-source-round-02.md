# Original-source round 2 implementation plan

> Execute inline with superpowers:executing-plans. The user has explicitly asked to continue the agreed original-source approach without another design discussion.

**Goal:** Improve source fidelity and practical quality while retaining uncertainty, with Kilfane first and Carrick next.
**Spec:** ../specs/2026-10-24-kilfane-originals-design.md plus research/HANDOFF.md; same historical-only constraints apply to the other faces.
**Architecture:** Named component evidence replaces location-based guessing for Kilfane's clear loose marks. Candidate-specific build adapters preserve the release. Inspect Carrick's larger alphabet and production examples before reconstructing its Regular. Audit real shaping and outline intersections across all four Regulars.
**Stack:** Existing Python font pipeline, Pillow/SciPy, fontTools, HarfBuzz, pathops.

## Global constraints
- No modern revival outlines; no generative enhancement of sources.
- Candidate font files remain separately named; archived source pixels remain local.
- Geometry changes carry source hashes, regions, transforms and uncertainty.
- No claim of historical authentication from source fit alone.

## Review focus
- Adjacent pieces must not contaminate isolated marks.
- Ring counters and both diaeresis dots survive reconstruction.
- Ambiguous lower pieces are not silently labelled as an attested caron.
- Builder provenance must describe both base and mark sources accurately.
- Shape tests exercise actual font binaries, including decomposed accents and alternates.

## Tasks
- [x] Map and inspect Kilfane's named mark components; add a failing isolation regression test, implement exclusive component extraction, and verify it.
- [x] Generate a separately named Kilfane Study 2 from Study 1 bodies plus named marks; check source fit, counters, coverage and shaping. Keep T/U/k/l and zero uncertainty explicit.
- [x] Inspect Carrick N513/N47, map source regions and build a separately named candidate for source-supported entries, preserving uncertain ones. Validate against additional reproductions.
- [x] Audit four-font text behaviour and candidate geometry, inspect proofs, have a fresh reviewer assess the change, fix material findings, and prepare the updated research branch and local illustrated review for publication.

## Ledger
- Existing research branch and clean worktree reused. Remote PR #1 is the publication destination already authorised by the user.
- T/U and k/l are fused in N516, N47 and N46. No newly independent clean boundary was found; retain the existing forms instead of pretending a cut is fully observed.
- The two lower Kilfane pieces are separated in the larger source; their previous treatment as a single attested caron is uncertain. Preserve their source records as unassigned. A caron derived by reflecting the attested circumflex must be labelled a modern construction.
- Kilfane: 14 source pieces reconstructed; all eight combined mark comparisons improve against N516 and N47. Carrick: 40 source entries reconstructed; all 39 comparable entries improve against N513 and all 37 against N47. Related reproductions are not independent authentication.
- Real text inspection exposed Carrick fl and Kilfane qj collisions. Full-height spacing protection now checks the final composite glyphs and existing kerning exceptions. The all-Latin binary audit reports 0 candidate failures versus 2,143 previous-release failures across 302,556 mapped character pairs (intersection threshold: four square font units).
- Tests for component isolation and spacing first failed, then passed with the implementation. Final suite: 81 passed on committed-artifact paths; OTF, TTF, WOFF and WOFF2 sanitize. Tuam and Céilí outline equality is explicitly checked.
- Fresh reviewer round02_review identified inaccurate mark provenance. Regression tests reproduced and verified the corrected attribution for constructed macron, ogonek/cedilla and related marks. Carrick's Euro now cites its actual lowercase c base. No critical findings remained in the review.
- Rendered text proofs and source overlays were visually inspected locally. Browser automation refused the local-file URL, so no browser-rendering claim is made. Static script validation caught and fixed escaped newlines; DOM-stub checks cover all four selectors, download/image paths, stress text, size and reset.
- The published research package contains fonts, trace data, metrics, provenance and font-rendered proofs. Archive images and archive-pixel overlays remain outside the repository. Exact archive pixels remain available in the local illustrated review.
