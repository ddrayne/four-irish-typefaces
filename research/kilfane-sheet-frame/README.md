# Kilfane Study 5: the production sheet in its own frame

[Study 4](../kilfane-judgement/README.md) with its sixteen production-sheet capitals averaged again in the
sheet's own geometry, as Carrick's letters are in [round 6](../round-06/README.md). Everything else (T, U, k
and l separated on N516, the eased e, every other glyph) is Study 4's, unchanged. This is a research
candidate: it does not replace the release.

## Why

Letraset prints a spacing mark under every letter, a fixed distance below its baseline, and a row's marks lie
on one line. Studies 3 and 4 registered each impression on the 30 pt sheet (N517, S53909) onto its N516
trace by its own affine transform. That absorbs the photograph's local distortion, but also N516's own
differences of slant and proportion, which every impression of a letter shares and so passed into the
letter: L had taken 3.5° of N516's shear, A.alt1 2.6°, G 1.5° and P 1.1°.

`scripts/trace_production.py kilfane --frame dash` finds each impression's mark and its row's mark line
(285 of the 301 impressions show one), and `impressions.sheet_frame` takes out the part of the registration
that all of a letter's impressions share, keeping its scale, and turns the letter square to its marks. Each
impression keeps its own fit's differences, so the impressions stay registered on one another: every
letter's spread is as in Study 3. `scripts/fit_production.py` sets each letter on the line by its marks
(10.77 units above them, the median over the sheet's sitting capitals) and fits only scale and horizontal
place, as before.

| Letter | Impressions | Turned | Shear taken out | Scale | Foot above the line |
|---|---:|---:|---:|---:|---:|
| A | 10 | +0.1° | −0.1° | 1.003 | +0.02 |
| A.alt1 | 3 | +0.5° | +2.6° | 0.993 | +0.18 |
| A.alt2 | 3 | +0.4° | +1.2° | 0.992 | −0.47 |
| B | 7 | +0.1° | −0.6° | 1.005 | −0.52 |
| D | 10 | −0.7° | +0.5° | 0.998 | +0.34 |
| E | 35 | +0.2° | +0.0° | 1.002 | −0.25 |
| F | 5 | −0.3° | −0.2° | 0.995 | +0.14 |
| G | 9 | +0.7° | +1.5° | 1.000 | −0.72 |
| H | 14 | −0.2° | −0.0° | 0.999 | −0.00 |
| K | 9 | +0.8° | −0.1° | 0.990 | −0.20 |
| L | 12 | +0.8° | +3.5° | 0.968 | +0.67 |
| M | 7 | +0.1° | −0.9° | 0.993 | +0.42 |
| N | 23 | +0.0° | +0.1° | 0.989 | +0.04 |
| O | 14 | +0.7° | +0.6° | 0.994 | −0.68 |
| P | 11 | −0.2° | +1.1° | 0.984 | +0.47 |
| R | 6 | +0.6° | −0.2° | 0.992 | −0.07 |

Turned and shear taken out are the sheet frame's correction; scale is the frame lock's; the foot is in trace
units against N516's line before the builder snaps it onto the baseline (Letraset's paste-up placed its
letters within about ±0.7 units of the mark line, so the marks fix each letter's frame, not its exact
height). Q keeps N516's trace, as in Study 3: the sheet's resolution closes its second counter.

The changes are small: L stands straighter (its N516 lean was the print's, not the sheet's), and the other
letters move by under three per cent in width. They are recorded per letter in `traces/evidence.json`
(`frame_lock.sheet_frame`, `frame_lock.baseline`).

## The release's finishing pass

The release build (`scripts/build_candidate.py kilfane`) finishes these traces as a studio would, in
`scripts/kilfane_studio.py`; the traces and the Study 5 fonts here are unchanged. Each step and its reason is in
`judged-edits.json` (`finishing`):

- **Heights** (judged). The prints set letters up to two source pixels off one another, so flat tops ran from
  489 to 514 units at the x-height and 690 to 716 at the capitals, ascenders 680 to 692. Each letter is scaled
  about its baseline onto the lines (x-height 506, overshoot 513; ascender 692; capitals 706 and 719; figures 693
  and 700; descenders −157 and tails −168), keeping what the prints draw as design: the tall tilted o and O, r's
  high bowl, the flags of t, T, D.alt1 and S.alt1, X's raised accent, the short descenders of f and j.
- **Stems** (noise). Straight stems measured 108–119 (lowercase) and 121–139 (capitals), a pixel or two at
  random; their edges move by at most 3 units each towards 114 and 130.
- **Outlines** (noise). Every style's final outlines: nodes a fitter or the bold's pen left in chains merged,
  near-smooth joins made smooth, nodes at extremes, each change within 1.5 units (2.5 where a kink is turned).
- **Kerning** (judged, in text). Quotes and hyphens no longer tuck onto lowercase (’a was −105, c- −115); pairs
  whose white is wider than n n, H H or H n by more than 12 units close by 60% of the excess (l and L with their
  feet, F, V, K, X, Z, P, T before lowercase).

A second pass, after an independent review of the four styles, completes the bold and the derived glyphs (the
same file, keys `bold_pieces`, `bold_joins`, `g_tail`, `symbols`, `marks_on_line`, `corners` and the kerning's
`clearances`):

- **The bold's marks, rules and chevrons** (judged). The sheet's loose pieces were read after the letters were
  bolded, so the bold kept the Regular's accents, dashes, math signs, guillemets, © and °. They are drawn with the
  bold's pen: dots, rules and chevrons with all of it, the stroke accents with the share that keeps the Regular's
  proportion to the stems (0.72; the ring's hairline 0.45), each pair set apart again so its gap stays as drawn.
  The family's ascender rises from 1010 to 1023 units to hold the bold's taller capital accents (Ó).
- **The bold's open joins** (judged). The pen closed the drawn open joins of k, r, 6 and 9, and easing them open
  again notched the stem. The join is drawn closed and a 20-unit gap is taken from the terminal alone, its face one
  curve, the stem straight and whole. The g's tail tip, raised onto the bowl by the pen, is lowered 30 units.
- **The bold's section and number sign** (judged): the Regular's section drawn with the bold's pen in its own
  frame; the number sign at the Regular's proportion to the stems.
- **Marks and corners** (noise). Ů's ring, which found the floor of the U's counter, sits on the line as Å's
  does; the section's corners are single nodes.
- **Room** (judged, in text). Every glyph keeps 40 units from the mark of an accented i (the fada overhangs its
  side bearing and ran into C, S, R, P, F); the bold's capitals keep 30 units; the quotes' −40 limit covers the
  accented lowercase.

## Reproduce

```sh
python scripts/fetch_sources.py --source N516 --format jpg
python scripts/fetch_sources.py --source N47 --format jpg
python scripts/fetch_sources.py --source N517 --format jpg
python scripts/trace_production.py kilfane --frame dash --work build/production/kilfane-marks
python scripts/fit_production.py kilfane --round research/kilfane-sheet-frame --work build/production/kilfane-marks --lock-frame
python scripts/separate_touching.py kilfane --traces research/kilfane-sheet-frame/traces
python scripts/judge.py kilfane --traces research/kilfane-sheet-frame/traces --edits research/kilfane-sheet-frame/judged-edits.json
python scripts/build_original_study.py --face kilfane --study 5 --traces research/kilfane-sheet-frame/traces --output research/kilfane-sheet-frame/fonts
```

The means, impressions and boards hold archive pixels and stay in ignored `build/`.
