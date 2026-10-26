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

| Letter | Sheet | Impressions | Spread | Turned | Shear taken out | Scale | Pieces, counters | Against round 5 |
|---|---|---:|---:|---:|---:|---:|---|---|
| b | 60 pt | 3 | 0.041 | +0.3° | +1.8° | 0.998 | 1, 1 | the bowl closes, as on every production impression (8 of 8 on both sheets); N513 prints it open |
| c | 60 pt | 7 | 0.035 | −1.8° | −0.6° | 1.013 | 2, 0 | |
| d | 36 pt | 12 (2 dropped) | 0.047 | +1.6° | −0.2° | 0.995 | 1, 1 | |
| e | 60 pt | 24 | 0.068 | +1.0° | −0.6° | 0.986 | 2, 0 | **was a flyer trace**; the lower wedge is detached (11 of 24 impressions, and on N513) |
| f | 60 pt | 6 | 0.032 | +0.4° | +1.3° | 1.000 | 1, 0 | **was a flyer trace** |
| g | 60 pt | 7 | 0.038 | +0.3° | −0.9° | 1.007 | 2, 0 | |
| h | 36 pt | 15 | 0.061 | +0.6° | −1.0° | 1.021 | 1, 0 | |
| i | 36 pt | 19 | 0.046 | +1.5° | +3.2° | 0.993 | 2, 0 | |
| j | 36 pt | 4 | 0.043 | +0.8° | +1.2° | 1.004 | 3, 0 | the tail stays apart (3 of 4), recovered from the mean at a 0.6 edge |
| k | 36 pt | 7 | 0.052 | +0.6° | +0.7° | 1.011 | 2, 0 | |
| l | 36 pt | 16 | 0.058 | +2.7° | +5.5° | 0.963 | 1, 0 | upright: N513's l leans, the sheet's does not |
| m | 36 pt | 8 | 0.051 | −1.5° | +3.2° | 1.000 | 3, 0 | the three strokes stand apart (3 of 8; 2 pieces in the rest); N513 prints m in one piece |
| n | 36 pt | 22 | 0.054 | +0.4° | +1.1° | 1.011 | 1, 0 | |
| o | 36 pt | 17 | 0.055 | +2.6° | +1.0° | 1.022 | 1, 1 | |

Spread is the mean RMS of the impressions about their mean, on the 0–1 ink scale. Turned and shear taken
out are the sheet frame's correction (below); scale is the frame lock's. Edge levels: 0.33 of the way from
backing to ink on the 60 pt sheet, 0.38 on the 36 pt (at the midpoint the sheets ink 5% and 4% less than
round 5's N513 letters; the same weight question as Kilfane's).

## The sheet's own frame

Letraset prints a spacing mark under every letter, a fixed distance below its baseline, and a row's marks
lie on one line: the line its users ruled to set the letters straight. The first build of Study 3 registered
each impression onto its round-5 trace by its own affine transform, which absorbs the photograph's local
distortion but also takes in N513's own differences of slant and proportion. Those are the same for every
impression of a letter, so they passed straight into the letter: l took N513's lean (5.5° of shear), i and
m 3°, o and i were turned 1.5 to 2.6°, and n and o, whose feet stand higher in N513's box, floated 30 units
above the baseline in the font.

Now `scripts/trace_production.py` finds each impression's mark (in pieces where a descender's tail breaks
it) and the mark line of its row. `impressions.sheet_frame` takes the part of the registration that all of a
letter's impressions share, splits it into a rotation and a stretch, removes the stretch's shape (keeping
its scale) and turns the letter square to its marks; each impression keeps its own fit's small differences,
so the impressions stay registered on one another (the spreads are unchanged). `fit_production.py` then sets
each letter on the line by its marks, 9.48 units above them on the 36 pt sheet and 5.18 on the 60 pt (the
median over each sheet's sitting letters), and the frame lock fits only the scale and the horizontal place.
Each letter's correction is in `traces/evidence.json` (`frame_lock.sheet_frame`, `frame_lock.baseline`).

The marks fix the frame, not each letter's exact height: Letraset's paste-up set its letters within about
±0.8 units of the line (e, k and b a little below it, n and l a little above; the impressions of one letter
vary by ±0.3), and the builder snaps every foot onto the baseline as before. The 60 and 36 pt sheets agree
on each letter's place to 0.15 units, so this is the assembly of one master, not noise.

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

p to w, z, the figures, punctuation and the round-5 marks are unchanged (but for the diaeresis, below);
so are the accented letters' marks, though the accented e, a and others take their new bodies. No N514
impressions exist for x, y or any letter after q.

## The finishing pass

The released fonts were judged as a studio would at 96 to 300 px and in Irish and English text. Each
judged correction and its reason is in [judged-edits.json](carrick/judged-edits.json):

- **f** sits on the baseline. Its foot is a stem's cut like i's and l's, but the flat-foot test read it
  against the whole (wide) letter and set it 8 units below them.
- **The diaeresis is N513's lower paired piece**: the accent set's only pair, two blocks the size of its
  dot, in place of the flyer's two tall wedges. They touch at their feet on N513 and N47, so they are
  parted there and each moved 15 units out, so that the pair reads as two dots and not a v
  (`scripts/carrick_diaeresis.py`; the inner chevrons stay unassigned).
- **Small figures and letters** (¹²³ ¼ ½ ¾ ª º ™ © @ ¥ §) take a mitred offset, keeping Carrick's cut
  corners, and keep their small counters and openings: the 4 of ¼ and ¾ had shut to a slit 11 units
  across (5 in the Italic); it is now 21 (14).
- **The Italic** adds its hair of weight by moving the drawing's own nodes (`bolden.grow_nodes`), not by
  a stroked offset: the average sloped letter had 62 nodes against the upright's 34, and now has 39.
  © and ™, whose cuts are narrower than that hair, keep the upright's weight, so the Italic now has the
  Regular's pieces and counters in every glyph (`scripts/topo.py`: 4 glyphs flagged before, none after).

The noise clean-up (`scripts/settle.py`) changes no design: the finished outlines are put on the
whole-unit grid without the kinks and stubs rounding left. In the Regular's letters and figures, 175 of
1209 joins at a curve were bent by 1.5 to 10 degrees (23 now) and 25 pieces were under 4 units long
(none now); no outline moves more than 2 units (median 1). The Italic's move up to 3.4 (median 2.2),
the difference between the two ways of adding its weight.

Looked at and left as drawn. *x-height*: the production n and m are shorter than N513's (523 and 524
units against 541 and 562), but N513's own a, u and z are lower still (532 to 534); the zones set every
flat top (a c m n u z) at 529, and the cut, pointed tops (e o r s v w x) rise 15 to 25 above it, as on
both sheets. *Weight*: stems at 0.4 x-height are 178 to 191 units on the production letters and 177 to
202 on N513's; bowls 214 to 236 and 200 to 217. *Gaps*: the narrowest hairlines are e's lower wedge
(5 units) and m's strokes (8 and 13), which ink spread closes in half their impressions. *Feet*: each
letter keeps its own feet as both sources print them (n's left foot above its right, r's stem foot above
its leg); u's right foot stays below its rounded left. *Spacing*: Letraset's spacing marks span each
letter's ink to within 0 to 20 units (o's lies 35 inside its left edge): they set ink box to ink box and
argue nothing against the optical spacing, which sets nn, oo and prose evenly with no letter pair kerned.

## The second finishing pass

An independent type review of the released fonts (font outlines only) raised the items below; each
correction is in [judged-edits.json](carrick/judged-edits.json) with its reason. Numbers are font units.

- **% ‰ #** were drawn from small zeros at their own weight and thin rules: strokes of 68 to 70
  (skeleton, 75th percentile) beside figures of 176. % and ‰ are now the face's own 0 made small,
  grown by a pen in the zero's own contrast that moves its nodes (so its cut corners stay cut), with a
  slash between the zeros; # has bars half the figure stem (`symbols.figure_signs`, switched on by
  `FIGURE_PERCENT`, which any face can take: a scratch build of Tuam with it measures 0.58 and 0.50 of
  its figure stem, and its zero's cut stays a cut). The strokes are now 104 to 106 (0.59 to 0.60 of
  the figure stem; 0.57 in the Italic) and #'s bars 92 (0.52).
- **The ponc of ḃ ḋ ḟ** stood 44 to 45 units above the ascender, so that at 14 to 16 px ḃ read as b and
  ḟ as f. N513's accent set gives the dot's shape (a diamond) but no dotted letter, and the production
  sheets have none. Irish types set ḃ's dot beside the ascender, over the bowl: Ó Lochlainn's Baoithín
  (c. 1932) and Colum Cille (1934), and William Britain's 1963 drawings for an Cló Nua-Rómhánach, which
  also drew f and t with lower ascenders so that their dots clear them (Bolger 2017, figs 171, 172 and
  181). ḃ's dot now stands beside the ascender, over the bowl; ḋ's (Carrick's d leans back like
  Baoithín's ꝺ, but its tip is too high and steep for the dot to sit in its crook legibly) and ḟ's stand
  above, 70 to 72 units clear (68 to 71 in the Italic; `build2.Font2.ponc`). b, d or f with U+0307
  shapes as the precomposed letter (ccmp). The line box, which covers ḟ, keeps its height (1201) and
  rises 7 units about the baseline: 988 above it and 213 below (it was 981 and 220).
- **The Italic's cuts**: its hair of extra weight narrowed every cut by about 7 units (@ and 9 from 12 to
  3 and 6, ¢ from 14 to 4, u from 19 to 8). The nodes beside a cut narrower than 0.22 stem now stay put,
  a long segment beside one is given a node there to hold, and each held node steps back by what
  narrowing and sloping take from the cut (`bolden.grow_nodes(keep_cuts, cut_frame)`). The Italic's @
  is now 11.6 against the Regular's 12.3, 9 14.4 against 13.7, ¢ 17.2 against 18.6, u 18.3 against
  18.6. Of the 101 glyphs with a cut under 40 units (its width read as the narrowest closing that
  changes the glyph's pieces or counters, at a unit a pixel), 86 lost more than 2 units of it in the
  Italic (median 5.5, up to 11); now the median change is 0.5 and none loses more than 2, but for two
  the measure misreads: ™, whose m strokes stand 1.4 units apart in the Regular as before (under its
  resolution), and ¾, where the small 4's counter (21 across, 20 in the Italic) shuts at the same
  closing at which the 3's opening makes a new one.
- **¢**: the bar stood at the c's middle and shut off a lens of the counter (35 across, 25 in the
  Italic) behind it. It now stands at the c's back, just covering the counter's innermost point, so the
  counter stays one open space and the bar stands 19 units clear of the c's top terminal (17 in the
  Italic; they were 14 and 4).
- **Figure heights** (investigated): N513 prints the figures' tops, all but the 8's, on one line (677
  to 683 px, the row's line at 681.5), and N47 too (680 to 687, line 682), while their feet stand at
  different depths (775 to 782 px and 779 to 787: the 7's and 5's cut ends and round bottoms run up to
  7 px, about 37 units, below the 2's flat foot). The builder sets each figure's lowest point on the
  baseline, as it does the lowercase cut feet, and that moved the tops apart: 517 (the 2) to 565 (the
  5 and 7). Each figure is now scaled about the baseline so that a flat top meets a figure line at 550
  and a cut or pointed top stands 8 above it, as cut and round feet stand 8 below the baseline, by at
  most 6% (the 2; `scripts/carrick_studio.py`). The 8 is the exception both prints agree on: it rises
  12 px (about 67 units) above the others with its feet on their line, so it is drawn taller and keeps
  its height (617).

## The third finishing pass

The leftovers the second pass reported (font outlines only; [judged-edits.json](carrick/judged-edits.json), the
values in `signs`). Numbers are font units; the figure stem (the 1's) is 176.

- **¤ and @** had rings at the hyphen's weight: ¤ 46 (0.26 of the figure stem, its arms as light), @'s ring 54
  (0.31), beside % ‰ at 0.6 and # at 0.53. The rings are now 0.58 of the figure stem (¤ 103 overall, @'s ring
  105; 106 and 102.5 in the Italic) and ¤'s arms 0.55 (`symbols.make_symbols`, `RING_WEIGHT` and the rest from
  `signs`). ¤'s ring grows from 0.34 to 0.40 of the x-height so its counter stays open (222 across; it was 275,
  and would have been 157 at the old size), its arms reaching 1.55 of the ring's radius. @'s ring is thickened half
  outward and half inward (789 to 841 across) and its a drawn at 0.92 of its size at its own stem weight, so the
  white between them stays as it was (26.1 to 26.4; Italic 25.5 to 25.9) and the line box keeps 988/−213.
- **™**: the small m, scaled and weighted whole, had one of its cuts joined and the other 1.4 units wide (2 in
  the Italic), a hairline that fills in. It is now drawn from the m's own three pieces, each weighted alone, and
  where two come closer than 13.5 units the left one's arm is cut back along the next stroke's edge
  (`symbols.parted`): the strokes stand 12.5 to 12.8 apart (12.5 in the Italic), read as Carrick's cut pieces.
- **The Italic's TrueType ı, i and į** had a 0.16-unit-square speck at (335, 514), made by the conversion: the
  stem's top corner is a 5-unit cubic whose first handle reaches 10 units, past its end, and cu2qu's spline for it
  (0.8 units' tolerance, then rounded to the grid) crossed itself. `build2.ttf_glyph` now converts each cubic
  within 2 units of such a speck again, only in a glyph that has one: a cubic under 8 units long that strays from
  its chord by no more than the conversion and the grid may (1.5 units) as its chord (this hook: the TrueType
  corner is one clean corner, 1.2 units from the hook's tip), any other split in two halves on the same curve so
  each half's spline follows it; a result with a speck or a point the contour runs out to and back from is
  refused. The cubic outlines are
  unchanged. The clean-up is the conversion's, so it runs for every face (`TTF_UNSPECK`); Céilí and Tuam have
  no specks and convert byte for byte as before, and Kilfane's TrueType K, Ķ, ! (Bold Italic), q (Bold) and
  Ã.alt1 (Regular) lose specks of 0.001 to 0.043 units square the same way.

## Reproduce

```sh
python scripts/fetch_sources.py --source N513 --format jpg
python scripts/fetch_sources.py --source N514 --format jpg
python scripts/trace_production.py carrick --base research/round-05/carrick/traces       # about 15 minutes
python scripts/fit_production.py carrick --round research/round-06/carrick --base research/round-05/carrick/traces --lock-frame
python scripts/separate_touching.py carrick --traces research/round-06/carrick/traces
python scripts/carrick_diaeresis.py --traces research/round-06/carrick/traces
python scripts/build_original_study.py --face carrick --study 3 --traces research/round-06/carrick/traces --output research/round-06/carrick/fonts
python scripts/evidence_board.py carrick research/round-06/carrick/fonts/CarrickStudy3-Regular.otf \
    --evidence research/round-06/carrick/traces/evidence.json      # the boards, into build/judgement/carrick
```

The means, impressions and boards hold archive pixels and stay in ignored `build/`.
