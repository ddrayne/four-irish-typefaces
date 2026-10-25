# Continuing the original-source research

Read [research/HANDOFF.md](research/HANDOFF.md) and the
[shared continuation plan](docs/superpowers/plans/2026-10-25-continuation.md)
before continuing the reconstruction. Claim a bounded task in the plan's work queue,
record ownership and base commit, and preserve other agents' work.
The user's goal is accurate recovery of the historical designs, one face at a time.
Use Carrick from `research/round-06/` (Study 3, on round 5), Céilí from `research/round-04/`, Tuam from `research/tuam-judgement/` (Study 3, on round 3) and Kilfane from `research/kilfane-sheet-frame/` (Study 5, on Study 4); the handoff records remaining
work on each face. Modern revival fonts are not design references.

For the exact original files, follow [research/SOURCE-ACCESS.md](research/SOURCE-ACCESS.md).
`python scripts/fetch_sources.py` retrieves the registered original/source leads
into ignored `build/research/`, checking sizes and hashes and excluding revivals.

- Keep each research candidate separately named and stored under `research/` or `build/` until a release is requested.
- Record the source identifier, image hash, coordinates, transform and uncertainty for proposed glyph changes. Distinguish attested shapes, retained legacy traces and modern extensions.
- Inspect shapes and counters as well as scores. Correlated reproductions are not independent confirmation; a higher pixel-overlap score alone does not establish authenticity.
- Read `research/RIGHTS.md` before adding external media. Downloaded scans and scan-containing comparisons belong in ignored `build/`, unless redistribution terms have been established.
- Run `python -m pytest -q tests`. For fresh builds set `ROUND05_DIR=build/round-05`, `ROUND04_DIR=build/round-04`, `ROUND03_DIR=build/round-03` or `ROUND02_DIR=build/round-02`; `STUDY_FONT_DIR=build/kilfane-study/fonts` selects a rebuilt first Kilfane study. Defaults check the committed research candidates. Use `--coverage` for new source audits; do not compare its absolute scores with older native-polygon audit scores.
- Respect existing work. Avoid replacing released fonts or another agent's changes while investigating a source.
