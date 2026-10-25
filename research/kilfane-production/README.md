# Kilfane Study 3: capitals from the production sheets

Sixteen Kilfane capitals redrawn from the mean of their repeated impressions on Curran's
Letraset production sheets (NIVAL N517, photograph `Kilfane-Letraset.jpg`, SHA-256
`a3a821f5cb233b4f6bff0b163c9c6992b9431109a6ad706d206d91981ceae16b`, as registered in
[downloads.json](../downloads.json)). Everything else is Study 2
([round 2](../round-02/README.md)) unchanged. This is a research candidate: it does not
replace the release.

## Why the production sheets

N517 photographs two Kilfane transfer sheets: 48 pt (S53910) and 30 pt (S53909). A transfer sheet
prints every letter many times from one artwork. Each impression carries its own print and
photographic noise, so no single one is better evidence than N516's single alphabet. Registered
together and averaged, the noise falls with the square root of their number. The capitals in
round 2 came from one rough-paper impression each. Here they come from 5 to 35 crisp ones.

The repeats are one artwork printed many times. Averaging lowers noise; it is not independent
confirmation of the design, and N516 and N517 may share artwork.

## Method

`scripts/trace_production.py`, then `scripts/fit_production.py` (pure functions in
`scripts/impressions.py`):

1. **Ink map** of each sheet from its best-separated channel (red for the 48 pt white-on-green
   sheet, green for the 30 pt black-on-blue sheet), normalising uneven light against local
   backing and ink levels.
2. **Letters found and named** by shape against the round-2 traces, at one fixed scale per sheet
   (from letters no other glyph resembles: E, I, L, H, K, B, F). A capital therefore cannot be taken
   for its lowercase, and both sheets turn out to hold capitals only.
3. **Each impression registered** onto the round-2 trace by its own affine transform: a correlation
   search for the translation, then coarse-to-fine least squares with an analytic Jacobian. The
   affine absorbs the photograph's perspective and the sheet's curl at that spot. The set is then
   re-registered twice onto its own mean, with the mean transform pinned to the registrations to
   round 2, so the frame (placement and proportions) stays N516's.
4. **Averaged** on a 1/8 trace-unit grid. The edge is one level line per sheet between the mean's
   backing and ink, chosen so that the redrawn capitals keep round 2's stroke weight on average:
   the lowercase is not on the sheets, and capitals and lowercase must match.
5. **Fitted** with the round-2 designer-style fitter and parameters (`curvefit3.contour_to_curves4`).
   Spacing marks under each impression survive averaging, so only contours that belong to the
   letter are kept. A letter whose mean changes the base topology keeps its base.

## Results

| Glyph | Impressions (30 pt) | Spread about mean | Residual to round 2 |
|---|---:|---:|---:|
| A | 10 | 0.047 | 0.227 |
| A.alt1 | 3 | 0.044 | 0.266 |
| A.alt2 | 3 | 0.039 | 0.224 |
| B | 7 | 0.056 | 0.222 |
| D | 10 | 0.046 | 0.230 |
| E | 35 | 0.049 | 0.235 |
| F | 5 | 0.040 | 0.215 |
| G | 9 | 0.053 | 0.257 |
| H | 14 | 0.048 | 0.233 |
| K | 9 | 0.048 | 0.211 |
| L | 12 | 0.061 | 0.220 |
| M | 7 | 0.044 | 0.236 |
| N | 23 | 0.053 | 0.227 |
| O | 14 | 0.092 | 0.247 |
| P | 11 | 0.049 | 0.212 |
| R | 6 | 0.068 | 0.232 |

Spread and residual are RMS on the 0–1 ink scale, over each letter's frame. Every impression's box,
affine transform and residuals are in [traces/evidence.json](traces/evidence.json).

Not redrawn:

- **C, I, J, D.alt1:** fewer than three impressions on the 30 pt sheet.
- **Q:** the 30 pt mean blurs shut the small second counter where the tail crosses the bowl. N516
  and the flyer resolve it, so Q keeps round 2.
- **S, T, U, V–Z and all lowercase:** not on the visible parts of the sheets. The 30 pt sheet covers
  the 48 pt sheet's later rows, and the photograph ends at R.

[Proof](proofs/study2-vs-study3-capitals.png): Study 2 (grey) and Study 3 (red), font outlines only.

## Calibration and open questions

- **Weight.** At the physical midpoint level, the 30 pt production letters ink 5.6% less than N516's,
  so the edge sits at 0.36 of the way from backing to ink to keep round 2's weight. N516 is a print on
  rough paper, where ink spreads. The production sheet may be closer to the artwork's weight, in
  which case the whole face (lowercase included) is slightly heavy. That is a decision for the
  whole face, not something to settle letter by letter, and is left open.
- **The 48 pt sheet** is white ink on a clear carrier over a green backing. Its photographed edge is
  not comparable with printed ink: at the midpoint it inks 10% lighter than N516, and matching needs
  an edge level of 0.10. Four of its letters (E, G, H, L) also register poorly. It serves as a
  cross-check only. Where it registers well (A, B, D, F, K), its shapes agree with the 30 pt means.
- **Text heights.** The builder still regularises heights (round 2's known limitation). Its
  medians move with the new capitals, and capitals within its window are pulled to them. Untouched
  capitals shift by up to 9 units. O falls just outside the window and keeps a 739-unit top: an
  overshoot of 26 against round 2's 6. The release candidate's height rule is being reworked for this.

## Reproduce

```sh
python scripts/fetch_sources.py --source N517 --format jpg
python scripts/trace_production.py kilfane          # about 15 minutes on four cores; build/production/kilfane
python scripts/fit_production.py kilfane --round research/kilfane-production
python scripts/build_original_study.py --face kilfane --study 3 --traces research/kilfane-production/traces --output research/kilfane-production/fonts
```

The means, spreads and ink maps are derived from archive pixels and stay in ignored `build/`.
