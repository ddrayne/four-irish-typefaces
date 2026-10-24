# Continuing the original-source research

Read [research/HANDOFF.md](research/HANDOFF.md) before continuing the reconstruction.
The user's goal is accurate recovery of the historical designs, one face at a time.
Kilfane Regular is the active study. Modern revival fonts are not design references.

- Keep each research candidate separately named and stored under `research/` or `build/` until a release is requested.
- Record the source identifier, image hash, coordinates, transform and uncertainty for proposed glyph changes. Distinguish attested shapes, retained legacy traces and modern extensions.
- Inspect shapes and counters as well as scores. Correlated reproductions are not independent confirmation; a higher pixel-overlap score alone does not establish authenticity.
- Read `research/RIGHTS.md` before adding external media. Downloaded scans and scan-containing comparisons belong in ignored `build/`, unless redistribution terms have been established.
- Run `python -m pytest -q tests`. For fresh candidate builds set `STUDY_FONT_DIR=build/kilfane-study/fonts` in the environment. The default checks the committed research candidate.
- Respect existing work. Avoid replacing released fonts or another agent's changes while investigating a source.
