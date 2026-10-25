# Four Irish Typefaces: continuation plan

> **For agentic workers:** Read this plan and the current handoff before editing. Use the available `superpowers:executing-plans` workflow, or `superpowers:subagent-driven-development` when delegation is authorized, for a bounded implementation task. The work below is queued, not already assigned or running.

**Goal:** Recover the four historical Regular designs as faithfully as surviving original evidence permits, then make their modern font implementations reliable and usable.

**Architecture:** Preserve immutable research rounds and separately named candidates. Improve one face and one bounded source problem at a time; retain source observations separately from outline construction, modern extensions and spacing decisions. Integrate checked milestones through PRs into `main`.

**Tech stack:** Python 3.12 with `requirements-study.txt` for research; Python 3.13 with `requirements.txt` for the release/CI build; fontTools, HarfBuzz, OTS, pathops and the existing image-analysis pipeline.

**Spec:** [Original-source design](../specs/2026-10-24-kilfane-originals-design.md), extended to all four faces by the user's continuing instructions; [current handoff](../../../research/HANDOFF.md); [rights policy](../../../research/RIGHTS.md).

## Starting point, 25 October 2026

[PR #1](https://github.com/ddrayne/four-irish-typefaces/pull/1) merged as `573d554871d92a934aea333089b96c4b1237eba2`. Its research tip is `6807edafe08f8da3a784e58f32bd916eb0b578c1`. All 123 tests passed on the merged checkout. Main also includes other contributors' 2.010 release and showcase changes: preserve them. The original 2.000 release is a historical comparison baseline, not the current release version.

| Face | Current research candidate | Start here | Remaining source issues |
|---|---|---|---|
| Carrick | Study 2 | [round 5](../../../research/round-05/README.md) | Legacy e/f/x/y; lower paired mark; fused inner chevrons; historical mark spacing |
| Kilfane | Study 2 | [round 2](../../../research/round-02/README.md) | T/U/k/l; zero disagreement; ambiguous lower marks |
| Céilí | Study 3 | [round 4](../../../research/round-04/README.md) | Unassigned punctuation; fuller production-sheet evidence; modern extension consistency |
| Tuam Uncial | Study 2 | [round 3](../../../research/round-03/README.md) | N45/N46 disagreements; recomposed accents; stronger evidence behind Bolger figures 205–206 |

The 324,316-pair summary uses different domains: Carrick/Céilí include punctuation; Kilfane/Tuam currently cover Latin letters only. Default kerning is required. Do not call this universal collision protection or finished optical spacing.

## Global constraints

- Original specimens only as design references; modern revival fonts are excluded.
- Never invent source detail with generative enhancement. Preserve native pixels, hash source files and record every transform and segmentation choice.
- Avoid independent horizontal/vertical stretching of individual glyphs to improve fit. A photograph may need a documented, shared perspective correction grounded in page/sheet geometry.
- Distinguish direct evidence, retained legacy forms, derived constructions and unassigned components. A research merge does not certify historical authenticity.
- Keep old research rounds intact. Create a new round for accepted new geometry; update the handoff and entry points to the latest candidate.
- Keep scans, PDFs and source-containing comparisons under ignored `build/` unless open redistribution rights are established. Commit source links, coordinates, hashes and font-only proofs.
- Do not overwrite `fonts/`, `sources/traced/`, release metadata, or the showcase's selected fonts as a side effect of research. Promotion is a separate release decision.
- Do not send archive enquiries or other external messages without explicit user authorization. Record retrieval leads and draft questions in the repository instead.
- Current main CI rebuilds and can publish the showcase through `deploy`; `deploy` is generated output. Never use it as a research branch or hand-edit its site files.

## Coordination and work queue

The integrator maintains this table. Before starting, record the task ID, owner/chat identifier, branch, base commit and owned paths in its claim cell. A claim is documentation, not a lock: fetch current main and check active work before editing shared files. Use separate branches/checkouts when concurrent edits would overlap. Do not revert another worker's changes.

| ID | Priority / dependency | Deliverable | Status / claim |
|---|---|---|---|
| C1 | Next | Carrick N514 e/f evidence decision | Ready; unassigned |
| C2 | After C1 accepts geometry | Carrick Study 3 candidate and complete review | Waiting on C1; unassigned |
| E1 | May research independently | Source-gap register for all four faces | Ready; unassigned; no shared builder edits |
| Q1 | After each accepted outline round | Optical spacing and rendering review for that face | Queued; unassigned |
| Q2 | After C2 or a documented C1 rejection | Reproducible research packaging and CI coverage | Queued; unassigned |
| K3 | Independent of C1/C2 | Kilfane capitals from the N517 production impressions (`research/kilfane-production/`) | Done as Kilfane Study 3 by the Claude Code release/showcase session on `main`: 16 capitals from 30 pt means; weight question and text-height limitation recorded in its README. Owns `scripts/impressions.py`, `scripts/trace_production.py`, `scripts/fit_production.py`, `tests/test_kilfane_production.py` |
| N1 | User decision | Release 2.100: the families renamed Céilí Digital, Carrick Digital, Kilfane Digital and Tuam Uncial Digital (files `CeiliDigital-Regular.otf` and so on), so they are never taken for the original type | Done by the Claude Code release/showcase session on `main`; outlines, spacing and features unchanged from 2.010. `build2.FONTS[face]['name']` is the design, `family`/`ps` the font. Studies keep the design's name (`Kilfane Study 3`, `KilfaneStudy3`): `build_original_study.py` names them from `name`, so committed studies rebuild unchanged. Tests that compare a study with the release read `fonts/otf/*Digital-Regular.otf` |
| R1 | After evidence and quality gates | Explicit release-promotion proposal | In progress, not promoted: Claude Code release/showcase session, branch `candidate/release-3`, base `e3a4ba9`. Owns `scripts/build_candidate.py`, `scripts/candidate_proofs.py`, `research/release-readiness.md`, `research/release-candidate/`; release-neutral changes to `scripts/bolden.py`, `scripts/build2.py`; behaviour-preserving refactor of `scripts/build_original_study.py`. Waits on Q1 and the user's decision |

Only the integrator edits shared builders, `AGENTS.md`, this table and `research/HANDOFF.md` during concurrent work, unless ownership is explicitly transferred. An evidence worker can return a report without changing font geometry. A reviewer should receive the exact candidate commit and source decisions, not merely a claim that tests passed. Do not spawn or message other chats solely because this plan mentions agents; follow the user's current coordination authorization.

## C1 — Resolve Carrick e/f from repeated originals

**Owned outputs:** new `research/carrick-ef/evidence.json` and `research/carrick-ef/README.md`; optional reproducible analysis helper `scripts/analyze_carrick_sheet.py`. Local crop and overlay outputs go in `build/carrick-ef/`. Existing candidates remain inputs.

**Inputs:** N514 `Carrick-Letraset.jpg`, 2592 × 2592, SHA-256 `525f4bb849a7f5bea66f82ca5aad0f2dbb3a9d8d7257ae2e91ed7e36c08ef35d`; N513/N47 and the Study 2 candidate. Retrieve using [downloads.json](../../../research/downloads.json); a missing local cache is not missing repository evidence.

- [ ] Verify the native file identity. Inspect initial boxes `e=[550,860,1400,1040]` and `f=[310,1030,1000,1220]`; enumerate all legible repeats rather than choosing the prettiest one.
- [ ] Record each observation's box, source hash, occlusion/blur, baseline and local sheet orientation. Record repeated impressions as related observations, not independent designs.
- [ ] Estimate shared local perspective from sheet geometry and neighbouring repeated letters. Preserve original crops beside corrected views; record the transform matrix, calibration landmarks and uncertainty. If correction is underdetermined, explicitly retain that limitation.
- [ ] Compare repeated e/f forms at native detail, including counters, joins and terminals. Test sensitivity to reasonable segmentation thresholds; do not average away a feature or silently repair damage.
- [ ] Compare the best-supported shapes against current Carrick and visible portions of N513/N47. Keep comparisons in those original source spaces; never score an entire fused cluster as though it were an isolated letter.
- [ ] Publish a decision per glyph: accept a specifically identified outline source, retain current geometry, or defer for missing evidence. Include reasons, rejected alternatives and the next useful source action.

**Evidence interface:** `evidence.json` records source IDs/hashes, observations with pixel boxes, shared transforms and their coordinate conventions, segmentation parameters, per-glyph decisions, uncertainties and links to the baseline. Every number needed to reproduce an accepted trace must be present. Paths to local-only overlays must be labelled as such.

**Acceptance:** Another agent can locate the same pixels and reproduce the comparison. Accept geometry only when repeated observations and a defensible transform support the feature. A documented rejection is a completed C1 outcome; it must not force a fabricated improvement or a new font version.

## C2 — Build and evaluate the accepted Carrick change

**Owned files:** new `scripts/trace_carrick_sheet.py`, `tests/test_carrick_sheet.py`, `research/round-06/carrick/` and `research/round-06/README.md`. Reserve round 6 only after checking no other agent has used it. Reuse `scripts/build_original_study.py`; modify it only if an actual supported construction change requires it.

**Interface:** the tracer consumes C1's evidence and original files, plus round-5 traces/pieces. It emits the existing trace format and updated provenance in `build/round-06/carrick/traces/`. The existing builder consumes that folder. Preserve named mark pieces and unassigned records from round 5; do not regress to the round-2 ornament cluster.

- [ ] Add failing checks for wrong source hashes, accepted e/f source attribution, preserved counter/component topology, and unchanged unrelated body/mark geometry. Declare expected changes to derived accented letters separately.
- [ ] Implement the accepted C1 decision with recorded calibration; retain unsupported e/f forms individually rather than treating acceptance as all-or-nothing.
- [ ] Build Carrick Study 3, if geometry is accepted, in OTF/TTF/WOFF/WOFF2. Preserve mapping coverage and verify distinct family/version naming. Add `ROUND06_DIR` support in the new tests for fresh-build checks.
- [ ] Compare final font outlines with every usable source observation using the coverage audit. Publish per-glyph improvements and regressions, not just averages. Inspect every changed glyph and all counters, including derived letters.
- [ ] Run source tests, four-format sanitation, NFC/NFD shaping, and the expanded Latin-plus-punctuation pair domain in both OTF and TTF. Include actual small-size text proofs and an independent review of source interpretation.
- [ ] Run the full suite, package source-free proofs and exact artifact hashes, and test a clean exported commit. Update handoff/latest-candidate links, open a PR and verify its checks. Report unresolved defects honestly.

**Acceptance:** C1 decisions are implemented reproducibly, all regressions have explicit dispositions, unrelated forms are preserved, and no meaningful check fails. Passing pair checks alone does not complete Q1.

## E1 — Close the source gaps without repeating dead ends

**Owned files:** `research/source-gaps.md`; update `research/source-register.json` and `research/downloads.json` only for new verified facts, with coordination if another evidence worker owns them.

- [ ] Start with the remaining issues in the candidate table. Separate already-inspected material from uninspected archive leads; record catalogue URLs, native dimensions, rights evidence and retrieval results.
- [ ] Prioritize originals that resolve a specific missing feature: Carrick x/y and ambiguous marks; Kilfane T/U/k/l and zero; full Céilí production sheets; Tuam originals behind the published reproductions.
- [ ] Preserve negative findings: N45 still has fused Carrick e/f/x/y and Kilfane T/U/k/l; the inspected N514 photo does not expose x/y; the inspected N517 photo does not expose Kilfane T/U or lowercase k/l. A higher-resolution/new view could change these findings, but rereading the same pixels is not a new discovery.
- [ ] For each useful lead, state exactly what it could resolve and whether it can be retrieved directly or needs an authorized archive enquiry. Stop a search branch when available evidence is exhausted and record that outcome.

**Acceptance:** Each issue has a best available source, confidence limitation and concrete next action. No additional font changes are required to complete this evidence task.

## Q1 — Optical spacing, shaping and rendering, one face at a time

**Owned outputs:** `research/quality/<face>/README.md`, machine-readable results and source-free proof sheets. Make shared `scripts/study_spacing.py` changes only under explicit ownership; put meaningful regression tests alongside the existing spacing/shaping tests.

- [ ] Review historical spacing evidence separately from modern text spacing. Use Irish prose, names, uppercase/lowercase transitions, punctuation, fadas and dotted consonants; include difficult repeated pairs and words.
- [ ] Inspect default and supported alternate features, precomposed/decomposed forms, combining-mark placement, bounds and line metrics. Measure failures in actual shaped text, not isolated glyph bounding boxes alone.
- [ ] Review real font rendering at 12/20/32 px and larger display sizes. Add browser/application checks where tools allow them, recording platform, app and scale. Local raster proofs or DOM checks must not be described as cross-browser verification.
- [ ] Adjust only demonstrated spacing/placement defects. Record before/after examples and test the implicated behaviour, including kerning enabled/disabled where relevant.
- [ ] Re-run the affected face's complete pair domain and full suite after changes; verify no other face or style changed unexpectedly.

**Acceptance:** Demonstrated defects are fixed or explicitly deferred with examples. State the tested applications/domains; do not promise universal layout correctness.

## Q2 — Make the next round reproducible from a fresh clone

Source retrieval is already available through `scripts/fetch_sources.py` and
[SOURCE-ACCESS.md](../../../research/SOURCE-ACCESS.md). Reuse it; the remaining
work here concerns packaging, overlays, manifests and build reproducibility.

**Owned files:** repository packaging/manifest helpers under `scripts/`, their documentation, and narrowly scoped CI updates if required. Reuse current helpers where possible; do not copy local machine paths into the repository.

- [ ] Inventory steps still performed by local-only packaging/verification scripts. Bring the necessary reusable parts into the repository with explicit input/output paths, source-image exclusions and stable manifest rules.
- [ ] Provide a documented command sequence for building, auditing and packaging the latest four candidates. Verify the exact source hashes before tracing; distinguish committed-artifact checks from builds requiring locally retrieved archive files.
- [ ] Check a fresh clone/export with the documented environment. Verify font ZIP contents and hashes, relative documentation links, and public-media exclusions. Add research rebuild CI only where inputs are legally and reliably available.

**Acceptance:** A new agent can reproduce the documented outputs without this chat's private working directory. Separate environment-dependent bytes from geometry/behaviour checks; do not claim research byte reproducibility until demonstrated.

## R1 — Release readiness and promotion

**Owned output:** `research/release-readiness.md`, followed by a separate release PR if the user requests promotion.

- [ ] List every unresolved original-source feature and every deliberate modern construction for each proposed face. Require explicit dispositions rather than hiding uncertainty behind a version number.
- [ ] Complete Q1 for the faces being promoted; validate naming, Unicode coverage, mark positioning, alternates, embedding, web formats, licence metadata and installation alongside older versions.
- [ ] Evaluate effects on the 2026 bold/italic styles separately. They are modern extensions, not recovered historical styles; do not regenerate or promote them silently with a Regular study.
- [ ] Prepare versioning, FONTLOG, specimen, download, showcase and rollback changes as one reviewable release proposal. Preserve earlier candidates and evidence.

**Acceptance:** The user can approve an explicit release scope with supporting evidence. Merging a research PR does not by itself promote research fonts into the release.

## Review focus and handoff contract

Pay particular attention to photographic distortion masquerading as letter proportions (C1), tracing damage as a feature (C1/C2), lost counters or detached pieces (C2), misleading source attribution or aggregate scores (C1/C2/E1), and spacing/mark defects hidden by isolated proofs (Q1). C2's tests and Q1's actual text/application checks own those risks; evidence review cannot be replaced by a pixel score.

Each completed task leaves: base/result commit IDs; owned files; evidence and decision links; exact validation commands/results; source-fit regressions; unresolved questions and costs; and the next task/owner. Update this queue and the active section of `research/HANDOFF.md`. Keep historical rounds as historical records. A future agent should be able to resume from repository files alone.

## Verification commands

From the repository root, with the relevant environment installed:

```sh
python -m pytest -q tests
git diff --check
```

For the existing Carrick mark baseline:

```sh
python scripts/trace_carrick_marks.py --sources build/research/original-specimens --output build/round-05/carrick/traces
python scripts/build_original_study.py --face carrick --study 2 --traces build/round-05/carrick/traces --output build/round-05/carrick/fonts
```

Set `ROUND05_DIR=build/round-05` to test that rebuilt baseline; otherwise tests use committed candidates. The current baseline is 123 passing tests, not a fixed limit for later work. On Windows use `PYTHONUTF8=1`. Full source-audit commands are in each round's README. Release `make release` writes production outputs: run it for release verification in an isolated clean checkout, not casually in an active research working directory.
