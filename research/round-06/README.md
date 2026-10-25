# Carrick Study 3: the production sheets, round 6

[Carrick Study 3](carrick/fonts/) redraws fifteen lowercase letters from the averaged impressions on
Curran's two Letraset production sheets for Carrick, traces x and y from N513 at last, and keeps
everything else from [round 5](../round-05/README.md) (Study 2) unchanged. This resolves C1 and C2 in the
[continuation plan](../../docs/superpowers/plans/2026-10-25-continuation.md); the e/f decision is recorded in
[carrick-ef](../carrick-ef/README.md). It is a research candidate, not a release.

## The sheets

NIVAL [N514](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/514/) photographs two
sheets, 60 pt (S53914: a to h) and 36 pt (S53913, laid over the other: a to q), as `Carrick-Letraset.jpg`
(2592 × 2592, SHA-256 `525f4bb8…35d`, as registered in [downloads.json](../downloads.json)). Black ink
on a pale carrier; the green channel separates them best. The 60 pt letters showing through the 36 pt
carrier, the 36 pt header and the bottom row, whose descenders run off the photograph, are left out.

`scripts/trace_production.py` finds the letters by matching each letter's whole trace, with a margin of
its white space, across the sheet, and decides which matches are letters by matching pursuit (each
pick explains the most unexplained ink, less any ink it claims where the sheet is blank). Carrick's
letters come in separate pieces (the arm of k, the strokes of m, the dots of i and j), which single
ink components could not name; a match must also contain every piece of ink it touches, so a p
whose descender is cut off is never taken for an n. 271 impressions were found (72 on the 60 pt sheet, 199 on the 36 pt) and checked by eye.

Each impression is registered onto its round-5 trace, re-registered onto the impressions' mean, and
averaged, as for [Kilfane Study 3](../kilfane-production/README.md). Four impressions far from their
letter's consensus were dropped and the rest re-averaged (one a, three d). The two sheets print one
artwork at two sizes: for a to h their means differ by no more than one sheet's impressions differ among
themselves (rms 0.04 to 0.06, the same share of ink), so letters from the 36 pt sheet sit beside those
from the 60 pt. The 60 pt sheet is preferred; its d spreads twice as widely as the 36 pt sheet's, so d
comes from the 36 pt. g is the one letter whose two means differ more (0.105); it comes from the 60 pt.

## Topology is read from the impressions

Carrick is cut from separate chiselled pieces divided by hairline gaps. Averaging smears those gaps, and
the weight calibration (an edge below the print's midpoint, to keep round 5's weight) fills them, so a
mean's pieces and counters are not evidence. Each registered impression's own pieces and counters were
read at its midpoint edge, and the letter takes **the most open topology at least a quarter of its
impressions show**: where crisp impressions disagree about a hairline gap, the gap is drawn, since ink
spread closes a drawn gap far more readily than a clean one opens by chance. Where the mean at the
calibrated edge fills such a gap, the edge is raised along the line where the pieces meet
(`fit_production.contours_with_gaps`), and nowhere else.

| Letter | Sheet | Impressions | Spread | Frame lock | Pieces, counters | Against round 5 |
|---|---|---:|---:|---:|---|---|
| b | 60 pt | 3 | 0.041 | 0.993 | 1, 1 | the bowl closes, as on every production impression (8 of 8 on both sheets); N513 prints it open |
| c | 60 pt | 7 | 0.035 | 1.005 | 2, 0 | |
| d | 36 pt | 12 (2 dropped) | 0.047 | 1.000 | 1, 1 | |
| e | 60 pt | 24 | 0.068 | 1.001 | 2, 0 | **was a flyer trace**; the lower wedge is detached (11 of 24 impressions, and on N513) |
| f | 60 pt | 6 | 0.032 | 1.013 | 1, 0 | **was a flyer trace** |
| g | 60 pt | 7 | 0.038 | 1.001 | 2, 0 | |
| h | 36 pt | 15 | 0.061 | 0.996 | 1, 0 | |
| i | 36 pt | 19 | 0.046 | 1.001 | 2, 0 | |
| j | 36 pt | 4 | 0.043 | 1.013 | 3, 0 | the tail stays apart (3 of 4), recovered from the mean at a 0.6 edge |
| k | 36 pt | 7 | 0.052 | 0.999 | 2, 0 | |
| l | 36 pt | 16 | 0.057 | 0.997 | 1, 0 | |
| m | 36 pt | 8 | 0.051 | 0.994 | 3, 0 | the three strokes stand apart (3 of 8; 2 pieces in the rest); N513 prints m in one piece |
| n | 36 pt | 22 | 0.054 | 0.996 | 1, 0 | |
| o | 36 pt | 17 | 0.055 | 0.996 | 1, 1 | |

Spread is the mean RMS of the impressions about their mean, on the 0–1 ink scale. The frame lock puts each
redrawn letter at its round-5 size and place (e and f: the flyer trace's), so only its shape comes from the
sheet. Edge levels: 0.33 of the way from backing to ink on the 60 pt sheet, 0.38 on the 36 pt (at the
midpoint the sheets ink 5% and 4% less than round 5's N513 letters; the same weight question as Kilfane's).

**a keeps round 5's N513 drawing.** Its bowl prints open on N513 and N47 and in 4 of the 14 60 pt
impressions, closed in the rest and on all 16 36 pt ones. By the rule above the gap is drawn, and the mean
cannot show it even at a 0.7 edge, so the trace that does show it stays.

## x and y from N513

On N513 (and N47) x's upper-right piece touches the top corner of y's left arm. `scripts/separate_touching.py`
traces the pair from N513 as round 2 traced every other letter and divides the fused ink at its narrowest
neck. Every piece of each letter's earlier outline marks its body, since y's arm touches x but not y's own
stem; ink no letter's body reaches (the edge of the w inside the window) goes to neither. y's arm has a
square top on both prints: the curled flag of round 5's y was the flyer's blur.

## Not changed

p to w, z, the figures, punctuation and the round-5 marks are unchanged; so are the accented letters'
marks, though the accented e, a and others take their new bodies. No N514 impressions exist for x, y or
any letter after q.

## Reproduce

```sh
python scripts/fetch_sources.py --source N513 --format jpg
python scripts/fetch_sources.py --source N514 --format jpg
python scripts/trace_production.py carrick --base research/round-05/carrick/traces       # about 15 minutes
python scripts/fit_production.py carrick --round research/round-06/carrick --base research/round-05/carrick/traces --lock-frame
python scripts/separate_touching.py carrick --traces research/round-06/carrick/traces
python scripts/build_original_study.py --face carrick --study 3 --traces research/round-06/carrick/traces --output research/round-06/carrick/fonts
python scripts/evidence_board.py carrick research/round-06/carrick/fonts/CarrickStudy3-Regular.otf \
    --evidence research/round-06/carrick/traces/evidence.json      # the boards, into build/judgement/carrick
```

The means, impressions and boards hold archive pixels and stay in ignored `build/`.
