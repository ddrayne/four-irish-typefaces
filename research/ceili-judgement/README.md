# Céilí Study 4: the judgement pass

[Céilí Study 4](fonts/) draws every one of Céilí's 54 traced letters, figures and signs from the two
complete prints of Hermann Hecht's 1978 alphabet taken together, instead of from one of them, and adds
the sheet's own síneadh fada. It is built on [round 4](../round-04/README.md) (Study 3) and keeps its
frame, its named punctuation and its builder. It is a research candidate, not a release; it follows the
method of [Kilfane Study 4](../kilfane-judgement/README.md) and [Carrick Study 3](../round-06/README.md).

## The prints, and what they can settle

Céilí has no production sheet. What survives is one artwork reproduced several times:

| Print | What it is | Used |
|---|---|---|
| N46 | D. O'Sullivan's leaflet, NIVAL's copy ([46](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/46/), `0adeda27…`): a photocopy. Study 3 traced 50 of its 54 letters here | averaged |
| N45 | The competition brochure, NIVAL's copy ([45](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/45/), `57d14ab3…`): offset on textured stock, the alphabet set out in different lines (its own paste-up) | averaged |
| N44 | The brochure's cover ([44](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/44/), `172ddcd2…`), whose heading "design an irish typeface" is set in Céilí (Bolger, vol. 1, pp. 279-80): 21 separately made impressions of 15 letters | a check |
| S53915, S53916 | The leaflet's samples of the 24 pt and 42 pt Letraset sheets ("a1", on N46) | a check |
| B2 | Bolger's photograph of Trinity College's copy of the brochure (thesis vol. 2, p. 159, fig. 203b; PDF `f7532cc1…`, the extracted JPEG `a8a80957…`): the same plate as N45 on another sheet, at half its resolution | a check |
| flyer | `sources/flyer.jpg` (`84ef750e…`), the release's scan of the leaflet, a third of N46's resolution | a check |

N47 does not print Céilí (it shows Carrick and Kilfane only). The leaflet's title is American Uncial, not
Céilí (Bolger, fig. 202). N45, N44 and B2 share the brochure's press; N46 and the flyer the leaflet's
copying. Agreement inside a branch is not confirmation; across branches it is the best evidence there is.

The prints can settle shape: where they agree, that is the drawing; where one shows a gap, a notch, a
blob or a lost tip that another does not, that is print. They cannot settle weight: at their own
midpoints N45's stems print about 10% lighter than N46's, while N46's hairlines print thinner than
N45's (a photocopy spreads stems and drops hairlines). They cannot settle the drawing's finest
detail below about one source pixel (0.4 trace units, about 9 font units), nor how the letters were
spaced: both alphabets are paste-ups. Only a production sheet or the artwork can settle those.

## How the letters were drawn

`scripts/ceili_prints.py` finds each letter on every print (N46 and N45 by round 3's regions; N44 by its
ink components, its forms read by eye and confirmed by registration; B2 by one projective transform from
N45; the flyer by the legacy traces, which are in its pixels). Each print's ink is registered onto the
letter's Study 3 trace by a **similarity** transform: one scale, a rotation and a shift, never a stretch
(a free affine squashed 1, z and ! to fit). The prints are then registered onto their own mean and the
frame pinned back in the trace's coordinates, so every letter keeps Study 3's size and place.

`scripts/trace_ceili_judgement.py` draws each letter as one level of the mean of N46 and N45, each print
taken at its own midpoint. Only these two are averaged: both print every letter, so the alphabet is
drawn from the same evidence throughout, and N44 stays a check the averaging never saw (N44 prints
heavier hairlines; averaged in, its fifteen letters came out heavier than the rest). The level is the
face's, not the letter's: 0.36, where the mean's stems are as wide as the median high-resolution print's
(N46, N44 and the sheet samples agree, about 3% lighter than Study 3 traced them; N45 is the outlier).
Across twenty stemmed letters the median stem is 4.69 trace units against Study 3's 4.62, and the spread
is narrower. The builder's stem, measured on l and n alone, falls from 115 to 109.5 units because Study
3's l was one of its heaviest letters. The hairlines lie between the two prints', about 6% heavier than
Study 3's.

Topology is the prints', not the mean's. Every letter's pieces and counters were read on each print; N46
and N45 agree on all of them but the ampersand. Where the two prints disagree by more than edge noise
(0.3 trace units), each region one print inks and the other leaves white is decided by one rule
(`disagreements()`, recorded region by region in each letter's `topology`):

- **A notch**, where the other print's outline closes over the region at 0.75 units, is a gap or dropout
  in that print and is filled. A gap or notch one print shows and another fills is print, so the rule
  fills these. It did so 28 times: 25 where N45 left the notch, 3 where N46 did (the white streaks of h
  and 7).
- **A protrusion** of one print beyond the other is decided by the cover heading N44 wherever N44
  prints the letter. N44 voted 17 times. It kept 14 of N45's tips. It voted out two N45 spurs, on g and
  p, and one N46 lump, the toner blob in g's lower bowl.
- **Where N44 does not print the letter**, a protrusion of N45 is drawn: 36 tips and spurs that the
  photocopy lost (the photocopy loses fine ends, the offset print does not). A lump of N46's toner at
  least a unit thick would be dropped, but no such lump occurs outside the letters N44 votes on. N46's
  thinner excess along its edges is its heavier weight, which the face's level already accounts for.

The ink-map sampling, levels, transforms and residuals of every print of every letter are in
[traces/evidence.json](traces/evidence.json), with the files' hashes.

**Checked against a print it never saw.** The cover heading N44 (21 impressions of 15 letters) matches
the mean of N46 and N45 better than it matches Study 3 or N46. On shape IoU, with weight set aside, the
mean scores 0.915, Study 3 0.893 and N46 0.878. N45 alone scores as well (0.916), but it shares N44's
press. The check scores the plain mean, before any votes, so N44's votes do not feed into it. The frame check (the overlap fit of each letter to Study 3, recorded and not applied) lies
between 0.967 (the left parenthesis, whose tips N45 restores) and 1.009.

## What changed

| | Study 3 | Study 4 |
|---|---|---|
| Source of each letter | N46 (50), N45 (b, e, e.alt1, h) | the mean of N46 and N45, all 54 |
| Weight across the alphabet | stems vary 4.19-5.44 trace units (cv 7.4%); b, e, h lighter | 4.50-5.31 (cv 5.4%); one weight throughout |
| Hairlines (bowls' thin points) | 1.62 median | 1.72; contrast 2.85 → 2.73 |
| Acute and its family | drawn to match | the sheet's síneadh fada |
| Median ink change per letter | | 15% (aligned at the left; mostly edge noise removed). The 8 and £ change most (68%, 54%) because they now sit on the line |
| Lowercase mean advance | 616 | 622 (the spacing method is unchanged; the letters are a little wider) |

Letter by letter, the changes the boards show are print removed, not drawing added:

- **g**: a blob of toner inside the lower bowl (N46 only) is gone; the counter is round, as N45, N44 and B2 print it.
- **h**: N46 prints it broken by white streaks across the stem and leg; Study 3 had used N45, and Study 4 is
  the two together, at the face's weight (Study 3's h, b, e and e.alt1 were N45's lighter weight).
- **7, z, x, k, l, d, n**: nicks and lumps along N46's edges (its toner) are gone; the 7's top bar is clean.
- **d, d.alt1, t, j.alt1, f**: the flags at the top of the stems are pointed, as N45 and N44 print them, not blunted.
- **a.alt2**: the counter is the diamond N45 and B2 print, not N46's rounded one.
- **r**: N46's notch where the bowl meets the leg (one print only) is filled.
- **e, e.alt1**: the eye is closed on every print and stays closed; the tongue of e.alt1 keeps its pointed tip.
- **b**: the bowl's open join is on every print and stays open. **6**: its tip stays apart from the stem
  (the Bold's designed join, `BOLD['ceili']['joins']`, is untouched). **! and ?**: their dots stay separate.

Pen and modulation, across the alphabet: the thin points of the round bowls lie on a near-vertical axis.
Angles are from the horizontal, with N46's and N45's own readings in brackets:

| Letter | Study 4 | N46, N45 |
|---|---|---|
| o | 92° | 88°, 82° |
| zero | 90° | 92°, 92° |
| d.alt1 | 96° | 88°, 90° |
| a.alt1 | 102° | 104°, 96° |
| a | 104° | 102°, 114° |
| q | 106° | 92°, 96° |

The 8's upper bowl tilts to 136°, as both prints draw it (134°, 130°); Study 3's read 90°. The measure is
unstable where a bowl is not round: on e the prints themselves read 120° and 78°, and on g Study 4 reads
74° against 82° and 80°. No letter breaks from the rest of the alphabet in pen angle or terminals.

## Judgements, recorded as such

Study 4 itself has no judged edits: none of its outlines was drawn where a print does not show it. The
release's finishing pass (below) adds a few edits, each recorded in [judged-edits.json](judged-edits.json).
Study 4's calls are these.

- **The ampersand** is the one letter the prints disagree on. N46 (and the flyer) close its lower counter
  where the bowl's terminal meets the diagonal; N45 (and B2, the same plate) leave a sliver of paper about
  one pixel wide. It is kept closed, as N46 draws it and Study 3 has it (a gap one print shows and another
  fills is print). Against this: two copies of the brochure show the gap, and the photocopy prints heavier.
- **The weight** is a calibration, not a measurement (above).
- **Which print draws a disagreement.** Filling notches is the rule the evidence gives. Drawing N45's
  tips where N44 does not vote trusts the offset print over the photocopy for fine ends. That holds where
  N44 votes (it kept 14 of N45's 16 tips) and where B2 resolves them, but B2 is the same plate as N45.
- **The 8 sits on the baseline.** N46 sets it about 2 px higher on its line than 0, 1, 2, 6 and £ (Study 3's
  8 floated 37 units above the baseline); N45 sets it level with them. Placement on a paste-up is setting.
- **Each line keeps Study 3's baseline.** The builder takes a line's baseline as the median of its letters'
  bottoms, which moves with the overshoots of round and pointed letters; on the figures' line it moved by
  0.75 trace units and lifted 2, 6, 8 and £ off the line. `build_original_study.py` reads the baselines
  from the evidence (`line_baselines`).
- **The síneadh fada.** Both prints set three pieces together, in the same order, apart from the
  punctuation: N45's upper row (components 3, 4, 5, beside the quotes) and the foot of N46's stack
  (26, 28, 27). The thin wedge rising to the right (N45 5, N46 27) is no punctuation mark, and Irish cannot
  be set without a fada: it is the face's acute. Its shape is the mean of the two prints, and it builds the
  acute, the grave and the double acute (the grave and double acute are modern constructions from it).
  The sheet's fada is narrower than the drawn acute it replaces, so over an open letter (u, v, w, y) the
  builder now finds the letter's top across half an x-height, not the counter.
- **The round dot** (N45 3, N46 26) is the only round piece in the face: every other dot is a pen-made
  diamond, and it is larger (131 px against 96 for the period on N45) and rounder. Most probably it is the
  ponc séimhithe. It is recorded, not built: the dot accent stays the period, as in Study 3. **The diamond**
  (N45 4, N46 28) is the period's size and shape and stays unassigned. (N46's 26, which round 4 compared with
  the N45 period, is this round dot; N46 prints no separate period.)

## The derived styles

The prints show only the Regular. In the candidate (`make candidate`) the Bold and the sloped styles are
derived from Study 4 by the release's pen model, and two outcomes needed a repair. Both are recorded in
`evidence.json` (`derived_styles`) and read by `build_original_study.py` for this study only. Every
other face and study builds exactly as before.

- **The dot of ? in the Bold.** Every print sets the dot of ! and ? well clear of its stroke (13 and 17
  units in Study 4's Regular). The Bold's wider pen leaves the ? dot only 1.6 units from its stroke
  without joining them (Study 3's: 5), so the Bold has nothing to reopen, and the Bold Italic's extra
  weight then joins them. The dots of ! and ? are now set apart as the Bold sets apart a dot it joins: a
  cut along the midline, F_PASS (0.62) of the Regular's gap wide (`bolden._separate(close=True)`). The
  Bold's ? now has a 9.7-unit gap and the Bold Italic's 8.0; the ! is almost unchanged (7.3 and 5.0).
  This is a judged repair to a derivation, not to the drawing.
- **oe in the Italic.** The sloped styles' extra weight (`build2` condense) came out of pathops unsound
  for oe: part of the e resolved as a hole and the eye was lost. Growing the same outline after
  simplifying it gives a sound result. It is the only growth in the four styles that failed the check.

With both repairs the candidate's topology matches Study 3's: the only flag is the Bold's designed join
in 6 (`BOLD['ceili']['joins']`, untouched).

## The finishing pass

The release (`fonts/`, built by `scripts/build_candidate.py`) finishes Study 4 as a type studio would.
[judged-edits.json](judged-edits.json) records each edit and its reasons, and `scripts/ceili_finish.py`
makes them. `build_original_study.py` applies them only to Céilí's finished candidate (`FINISH`), so
Study 4's own fonts here do not change.

The judged corrections, which the prints support but do not draw:

- **The h** stood 40 units above the baseline (since Study 2, from the frame of N45's h). Both prints set
  it on its line, so it now sits on the baseline with its ascender level with k and l.
- **Pen terminals.** The mean of two prints domes a pen's straight cut and rounds both its corners, while
  N45 and N44 print the cuts crisp. Each stroke end is now drawn as a straight cut between sharp corners,
  each corner within 9 units of the drawn outline. This changes c, e, e.alt1, t, a.alt1, f, g, p (the
  bowl's end), x, z, the ampersand, the parentheses, 3, 4, 5, 7 and ?. The feet of upright stems stay
  rounded, as n and m are on every print.
- **The dots of ! and ?** are the period's pen diamond, fitted to each dot's own corners. N45 and B2
  print them that way. The dots had been 6 to 16% heavier than the period and now share its weight.
- **The Bold's dots** keep the Regular's whole gap, and the Bold Italic's keep 1.3 of it. ! and ? now
  stand 12 and 14 units clear in the Bold (they were 7 and 10) and 13 and 15 in the Bold Italic (they
  were 5 and 8).
- **The double acute** keeps its strokes 13 to 14 units apart in every style. In the Bold Italic they
  had been 3 units apart.
- **Quote kerning** follows one rule: the quote stands 0.65 of the n|n gap clear of the letter's upper
  part. Before, o’ was kerned -150, e’ 0, d’ -85 and m’ 0.

The noise clean-up stays within 2 to 3 units. In the Regular, a curve that left a stem on a handle too
short for its bend (the shoulders of n, m and h) now leaves on the stem's tangent, corner clusters become
single corners, and redundant nodes go. In every style, the Bold's reopened joins (traced from a raster
as runs of short lines) are drawn as curves, rounding specks go, and extremes get nodes again after the
slope's shear. No step may join pieces or open or close a counter. Where one would, the glyph keeps its
outline from before that step.

| From the 3.000 release | Regular | Italic | Bold | Bold Italic |
|---|---|---|---|---|
| nodes per lowercase letter | 22.3 → 19.9 | 43.8 → 22.4 | 85.5 → 23.2 | 82.4 → 26.2 |
| segments under 6 units, whole font | 243 → 53 | 1774 → 278 | 8816 → 122 | 8417 → 281 |
| curves overshooting an extreme by more than a unit | 73 → 1 | 491 → 1 | 71 → 1 | 495 → 0 |

Topology is unchanged. Regular → Bold flags only the designed 6. Regular → Bold Italic also flags the
dollar's small counter at 33%, as it did before. The proofs, which show font outlines only, are
[proofs/finishing.png](proofs/finishing.png) (the Regular after, in black, with the release outlined in
red) and [proofs/finishing-bold-nodes.png](proofs/finishing-bold-nodes.png) (the Bold's nodes, before
and after).

## The second pass

A second review of the finished fonts found seven defects. Each is corrected by one rule, recorded in
[judged-edits.json](judged-edits.json) (`second_pass`) and made by `scripts/ceili_finish.py`; Study 4's own
fonts here do not change. Measurements are font units, from the fonts before and after.

- **Heavy level strokes in the bold.** The bold's pen grows level strokes by its small vertical radius,
  which suits the face's thin horizontals but not the few level strokes drawn at least 0.75 of a stem in
  the Regular. The 7's bar went 93 → 102 and the 3's 91 → 101 while the 1's stem went 102 → 162, so
  "1977" read as a Regular 7 among bold figures. The hyphen went 81 → 91, and the dashes, math signs and #
  are drawn from it. These strokes now take the stems' gain, 1.5: the 7's bar is 139 and the 3's 136 to 138,
  the bar's lower edge coming down with the pen's cut and the diagonal running on along their own lines.
  The hyphen and dashes are 120 to 122, the math signs 121 to 123 and # 103. The letters' crossbars (ð đ ħ ł ŧ
  and the bars of € and ¥) keep the pen's weight, as t's and f's own do. So do the rings of @ © ® ¤ °,
  which the rules' weight would close: @ joined its a, and ° kept only 28% of its counter. The bold's § was
  drawn at the reduced weight the bold gives superiors (85 → 94 while s went 91 → 123); it is a full-size
  sign, so it now takes the bold's stem (120).
- **The quote after l.** The quote rule measures only a letter's upper part, so after l, L and ł it pulled
  the quote in over the long foot to −345, 64 units from the stem, where it read as the apostrophe of ľ. A
  quote may still tuck in over a lower part, but it never stands wholly over it: its far edge reaches at
  least the part's tip. l’, L’ and ł’ are now −205 (Italic −200, Bold −255, Bold Italic −250), with the
  quote's head over the foot's tip, 202 units from the stem in the Regular (it was 62).
- **The bold's open joins.** The bold reopened the joins of b, d, k, p, r and 9 as a channel down the
  middle of the Regular's passage, which took from both sides: p's stem narrowed from 166 to 141 at the
  join and k's from 165 to 142, and the cracks were 12 to 18 units in the Bold and 4 to 10 in the Bold
  Italic. Each stem now keeps the edge the pen gives it (p 169 from top to foot, k 166 to 168). The arm, leg
  or bowl that comes back to it is cut back along one curve parallel to that edge, to stand at least 15
  units clear (F_PASS of the Regular's opening where that is wider). The Bold Italic's hair of weight
  narrows the joins again, so they are cut
  back again there, in every glyph drawn from them (ḃ, þ, ĸ, ð …). A crack under 12 units that cuts off a
  counter is closed instead, as the Bold's 6 is. This applies to the ampersand's tail over its bar (8
  units in both bold styles) and the yen's curl (4 and 6).
- **The bold !.** The pen, mitred at the sharp foot of the pen-diamond dot, ran the ! dot 11 units below
  the Regular's. The ! then missed the baseline snap and sat 25 units low (stroke top 629, dot bottom −33).
  The dots of ! and ? now reach down only as far as the Regular's, so both stand where the Regular's do
  (! −8 to 643, ? −8 to 637), with their gaps unchanged.
- **Stems.** The h's stems were 100 and 99 beside n's 108 and 113, m's 115, 110 and 109 and i's 106, so
  the h read light in every style (Bold 159 against n's 168 and 173). The prints settle no weight finer
  than a source pixel, so the straight stems of f h i j k l.alt1 m n p r r.alt1 s.alt1 1 4 are given the
  face's stem, 108, by moving each edge at most 4 units (kilfane_studio.harmonise_stems). The Bold's are
  about 168.
- **ð and đ.** The spacing saw their bars only where they dipped into the x-height zone. So the Regular's
  ð kept d's advance with its bar hanging 90 units into the letter before (đ 96), while the Bold's was set
  130 wider than d. Both are now spaced as d in every style: d's sidebearings, with the bar's overhang added
  to the advance, and the bar's end no further left than −20. The Regular's ð is 722 wide and the Bold's 837.
- **€ and ¥.** € was 1.12 x-heights tall (602) and ¥ stood at the symbols' 1.05 (565), against 538 for 0
  and £. € now spans the zero (−8 to 538) and ¥ stands from the baseline to the £'s height. Both keep the
  release's construction, and the bold ¥ no longer dips 16 units below the baseline.

Regular → Bold and Bold Italic topology now also flags the closed ampersand and yen, and no letter pair
collides in any style. The proof, which shows font outlines only, is
[proofs/second-pass.png](proofs/second-pass.png).

## The third pass

A third review found six more defects. Each is corrected by one rule, recorded in
[judged-edits.json](judged-edits.json) (`third_pass`) and made by `scripts/ceili_finish.py`; Study 4's own
fonts here do not change. Measurements are font units, from the fonts before and after.

- **The bold's math signs grow in place.** The bold set each piece out from its own rule weight, so when the
  second pass made the rules heavier (81 → 121) the pieces moved apart: = stood 157 between its bars against
  the Regular's 105, the bar of ± dropped to −121..0, that of ≤ ≥ to −67..54, ÷ ran from −40 to 576 (over the
  538 x-height) and ≈ stood 221 apart (175); ~ and ^ grew upward only. Each piece now keeps its weight and
  grows about its Regular counterpart's centre, and the white beside a rule stays the Regular's: = 105 about
  the 268 axis (95..442), ≈ 173, ± −77..598, ≤ ≥ −43..528. The dots of ÷ are the Regular's drawn with the
  bold's pen, about their own centres (28..509); ~ and ^ stand about their centres (195..401, 331..622).
- **No quote stands wholly over a low foot.** The second pass's rule measured the far edge of the whole
  double quote, so l” and L” stayed kerned −345, −330, −350 and −350 with the first comma 64, 64, 69 and 52
  units from the stem. It now measures the quote's nearest piece: l”, L” and ł” kern as l’ does (−205, −200,
  −255, −250), and the rule holds for ‘ and “ after a letter too.
- **The bold's small signs gain weight.** The bullet is drawn with the bold's pen (ink 1.000 → 1.47 of the
  Regular's); % and ‰ take the bold's stem as § does (ink 1.34 → 1.58), and so do the c of © (stem 71 → 110)
  and the a of @ (102 → 147), the a kept as far inside its ring as the release's. The superiors, fractions,
  ordinals, ™ and the r of ® go 0.75 of the way from the Regular's stem to the bold's (the release's 0.5): the
  heaviest weight, of those tried from 0.5 to 1.0, at which every counter keeps at least 0.40 of the
  Regular's area and every opening 0.61 of its width in the Bold and the Bold Italic (at 0.8 the 4's small
  counter in ¼ ¾ fell to 0.37 in the Bold Italic, at 1.0 to 0.23). Their ink is now 1.36 to 1.43 of the
  Regular's (it was 1.13 to 1.28).
- **One rounding, the smooth joins kept smooth.** The drawing has no kinked smooth joins; rounding its short
  handles to whole units made them, and in the sloped styles pathops chopped the sheared curves at extremes a
  unit or two from their corners into pieces of 2 to 5 units: the Italic m had 8-degree joins at its arches and
  10 to 14 degree clusters at its feet, and the h's shoulder met its stem in a 5-degree kink (Bold 12). Every
  outline is now put on the grid once from the drawing (the sloped ones after the shear), each handle at the
  whole-unit place truest to its direction, a join the drawing makes smooth on one tangent, and nodes only at
  extremes a curve passes by more than a unit; an outline is kept only if its pieces and counters stand and it
  lies within 1.5 units of the drawing. m, n and h have no kinked join in any style. Base letters and figures
  with a kink of 5 degrees or more: Regular 37 → 23, Italic 53 → 22, Bold 43 → 29, Bold Italic 56 → 31 (all
  glyphs 164 → 74, 230 → 87, 169 → 124, 242 → 130); what remains are the drawing's own shallow corners.
- **The stems run straight to their feet.** h's left edge bulged out below its line (87 above y 160, 78 at
  y 90, 82 at y 40; Bold 80, 71, 75), the prints' mean, where n, m and k run straight. An evened stem whose edge
  bulges out past its line and comes back to the foot's corner now has its line carried on to the corner; a
  foot that flares out (l.alt1's) is kept. Only h (9 units) and r.alt1 (3 and 4) qualified: h's edge runs at 86
  to its foot (Bold 78).
- **j's bar stands as i's does.** j's bar stood 22 units above its stem against i's 31 (Italic 22 and 30, Bold
  11 and 20, Bold Italic 10 and 18, closest points); it now stands 31, 30, 19 and 19.

Topology is unchanged from the release in every style, and no letter pair collides in any style. The proof,
which shows font outlines only, is [proofs/third-pass.png](proofs/third-pass.png).

## The fifth pass

The pass across all four faces that the third pass left these to. One rule for all four corrects each
(`scripts/symbols.py`, `scripts/build2.py`, and for the bold `scripts/ceili_finish.py`; recorded in
[judged-edits.json](judged-edits.json), `fifth_pass`).

- **≈** stood 395 tall (71..466) against the ='s 267 (135..402), its waves 65 heavy against bars of 81 and 126
  apart where the bars stand 105; the third pass kept that design in the bold (97 against 121, 463 tall). Its
  waves are now drawn at the bars' weight (80.5; Bold 120 against 121), centred on them on the 268.5 axis, 0.7 of
  the ='s white apart (73): 317 tall (110..427; Bold 393 against the ='s 347).
- **Rings.** The rings of © ® @ ° ¤ were drawn at the pen's hairline, 36 to 58 (Bold 41 to 64), beside an o whose
  heavier side is 124 (Bold 185). The review asked for half the o's weight, and no counter closes at it, so each
  ring is now at least that: 63 (Italic 67 to 68, Bold 94 to 95, Bold Italic 99 to 100). This departs from the
  pen-weight design the second pass kept them at; the rules' weight it refused (121 in the bold) would close them,
  half the o does not. The c, r and a inside are as drawn; © and ® grow from 565 to 584 tall (Italic 587, Bold
  634, Bold Italic 656, where the r's 12-unit crack may not narrow) and the Bold Italic @'s a, 4 units from its
  ring, is 18 clear. ° keeps a counter of 64 (it was 89; Bold 79) and ¤ one of 238 (269; Bold 176).
  The final review found the figure-size signs had outgrown the figures (© and ® up to 656 tall against the
  figures' 565, the Bold's ° 162 to 269 tall, twice the bullet), so they are drawn again (`symbols.held_ring`,
  `heavier_ring`): © and ® keep the figures' 565, their ring at 0.4 of the o grown inward, 51 (Italic 54), the c
  and r drawn 0.95 to 1.0 as large. In the bolds the r, whose 12 to 14-unit mouth the slope and the grid would shut
  if it were drawn smaller, holds the ring to the white it leaves: 66 in the Bold, 61 in the Bold Italic.
  ° is no taller than 0.3 of the figures, 170, with a ring of 51 to 56 and a counter as wide (57 to 59).
- **Combining marks.** There was no mkmk (x + circumflex + acute: 140 into each other), no anchor on a
  precomposed letter, the comma below ran 90 units into j's descender and 26 into g's, the bold's g took its top
  marks 42 above it (Bold Italic 40) where ĝ has 48, and U+0323 had no glyph. Every top mark now stands at least
  the accents' gap from the letter's ink (47 to 48; Bold g 47, Bold Italic 52); precomposed letters carry anchors;
  mkmk stacks marks 48 apart; the comma and the new dot below stand at least 21 clear. The dot above keeps its
  anchor, so ḃ ċ ḋ ḟ ġ ṁ ṗ ṡ ṫ and base + U+0307 shape as before.
- **ŗ with the insular r** (ss01): the comma hangs under the r's descender, and the bold's pen brought the two
  within 6.1 units (Bold) and 0.8 (Bold Italic). It moves along the line until it stands the comma's gap (0.06
  x-height) clear: 34.0 and 32.3. The Regular's 50.1 and the Italic's 43.3 are unchanged.

## Not changed

The frame (every letter's size and place is Study 3's: the overlap fit to Study 3, recorded as
`frame_check`, lies between 0.967 and 1.009), the named period, comma and quotes (traced anew from the same N45
components, with N46's quotes averaged in, at the face's level), every modern construction but those the
second and third passes name, the spacing method, the Bold's designed join in 6 and the legacy `DOTS` cluster
(discarded by the builder, as before). The design of ≈, the rings' weight in © ® @ ° ¤ and the mark anchors
(mkmk, g with a top mark), left by the third pass for a pass across all four faces, are the fifth pass's.

## Open questions

- The ampersand's join (above); the identity of the round dot and the diamond.
- The weight: N46's and N45's stems differ by about 10%; a production sheet would settle it.
- The fine tips the photocopy shortens (the ends of the parentheses, the beak of v) are drawn as N45
  prints them. B2 agrees with N45 where it resolves them, but it is the same plate.
- The period sits on the baseline while the dots of ! and ? overshoot it by 8 units, as the round letters
  do (N46 sets them level with the 0). The builder places the period; no print sets it beside a letter.
- (Settled in the finishing pass: the rounded dots of ! and ?, and the Bold's dots set too close.)

## Evidence boards

`python scripts/ceili_prints.py boards --candidate research/ceili-judgement/traces` writes one board per
letter into ignored `build/ceili-judgement/boards/`: every print registered into the letter's frame at its
own midpoint, the consensus of N46 and N45 (black: both; colour: one), and their mean with Study 3's
outline (red) and Study 4's (blue). They hold archive pixels and are not committed ([RIGHTS](../RIGHTS.md)).
[proofs/study3-study4.png](proofs/study3-study4.png) sets the same lines in Study 3 and Study 4 (font only).

## Reproduce

```sh
python scripts/fetch_sources.py --source N44 --format jpg
python scripts/fetch_sources.py --source N45 --format jpg
python scripts/fetch_sources.py --source N46 --format jpg
python scripts/fetch_sources.py --source B2                      # Bolger vol. 2; pdfimages extracts fig. 203b
python scripts/ceili_prints.py locate                            # into build/ceili-judgement/prints
python scripts/ceili_prints.py average                           # about 15 minutes on four cores
python scripts/trace_ceili_judgement.py --round research/ceili-judgement
python scripts/build_original_study.py --face ceili --study 4 --traces research/ceili-judgement/traces --output research/ceili-judgement/fonts
python scripts/ceili_prints.py boards --candidate research/ceili-judgement/traces
CEILI_JUDGEMENT_DIR=research/ceili-judgement python -m pytest -q tests/test_ceili_judgement.py
python scripts/build_candidate.py ceili --output build/fonts       # the release, with the finishing pass
```
