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

A third pass finishes what the second reported and left in the bold (keys `bold_curves` and `bold_marks`):

- **The bold's faceted curves** (noise). Where the curve fitter could not follow the bold's pen, its offset stayed a
  polygon: G, S, s, v, w, x, y, ß, W and the alternate g and y, with their accented forms (47 glyphs a style), drew
  curves as chains of straight facets 7 to 80 units long, with pieces of 1 to 7 units at their corners. Each run of
  facets is fitted with cubics, nodes at its extremes, and each piece under 8 units folded away, everything within
  1.5 units of the outline as it was, pieces, counters and area kept (`kilfane_studio.bold_curves`). The marks of
  the accented forms go with them; three keep one bevel of 5 to 7 units that no fold takes within 1.5 units (the
  Bold Italic's š caron, the comma below of Ģ and Ș), as the same marks on every other letter do.
- **The bold's cedilla and ogonek** (judged). They took their weight from the ring's hairline and went only from
  40–43 to 46–48 against acutes of 90 and stems of 166. They are the Regular's grown with the bold's pen by the
  stroke accents' share (0.72): 67 and 70 (70 and 73 in the Bold Italic), the weight of the bold's comma below,
  joined to their letters as before with the hook's white under the letter as before (ç 28 against the Regular's
  26). Their hooks reach 20 units deeper, so the family's line box grows at the foot from −190 to −204 (as the
  second pass raised it for the bold's capital accents); the Regular and Italic change in their vertical metrics
  only, and in one TrueType glyph (below).
- **TrueType specks** (noise). The conversion to quadratic splines left loops of 0.001 to 0.04 units square where a
  cubic a few units long doubles back on itself: K, Ķ and ! in the Bold Italic, q in the Bold, Ã.alt1 in the
  Regular. `build2.ttf_glyph` converts such a cubic again (under 8 units long and within the conversion's
  tolerance of its chord, as its chord; else split in two), only in a glyph that has a speck; the cubic outlines
  are unchanged (the round-6 README, where Carrick's Italic i had one, gives the detail).

A fourth pass finishes what a third independent review found (keys `bold_math`, `bold_dots`, `bold_small`,
`spacing`, `case`, `settle`, the section's `mouths` and the kerning's `clearances`):

- **The bold's math signs** (judged). Each piece had moved outward instead of growing in place (= 142–202 and
  280–340 became 88–181 and 301–394). Each piece now grows about its own centre and the Regular's white between
  pieces stays: = 110–202 and 280–372, ± and ≤ ≥ with their underbars no lower than the Regular's less the pen's 17,
  ÷ its dots within the Regular's extent and the pen's 17, ≈ its waves 96 apart (97), ~ and ^ grown both ways.
- **The bold's dots** (judged). ! ? ¡ ¿ kept 14 to 16 units between dot and stroke against the Regular's 49 and 52:
  the stroke now ends higher, its rounded end moved whole, and the white is the Regular's. The dots of i and j
  (25 and 21 against 62 and 57) stand a little higher and smaller, 52 clear. The j's hook, raised over the line by
  the pen, is lowered as the g's tail was.
- **The bold's small signs** (judged). The bullet grows as the period does (174 to 261); % ‰ and the letters in
  @ © ® are the Regular's drawn with the bold's pen, their counters kept as the section's; the superiors, fractions,
  ordinals and ™ take the share of the pen that keeps their Regular proportion to the figures (¹ 0.68 of the 1),
  their counters and openings checked open at each share.
- **Spacing by one rule** (judged). j's stem stands where i's does in every style (the bold's j stood 60 units to
  the right, with kerns to make up for it); ? stands on its stem as ! on its stroke, and ¿ as ¡ (the Regular's ?
  stood 41 units closer than its !, the Bold's 13 further).
- **Room for capitals** (judged). The bold's 30 units between capitals now hold in every style and for every
  accented capital (the Regular's T Y kept 10; the Bold's T Í 16), and a capital before a lowercase letter keeps 30
  too (T h was 10 to 14, P f 8), 20 in the Bold and Bold Italic: the final review found 30 too much there, where A l,
  T h, F h and F l had opened from +20/+25 to +45 and A b, T b to +60, the white beside A l's diagonal more than
  between two l (the Bold's H l, two straight sides, keeps 43, the Regular's 69), so All, Abú and The gaped at
  display sizes.
- **Case forms** (judged). An OpenType `case` feature sets the hyphen, dashes, guillemets, colon, middle dot, bullet
  and @ on the capitals' middle (353, against the lowercase axis 241), and ¡ ¿ on the line as ! ? stand, each kerned
  where it stands.
- **Smooth joins** (noise). Rounding the sheared outlines to whole units turned short handles at stem and arch
  joins by about the slope (the Italic m's six joins 8 to 11 degrees). Last of all, in every style, each near-smooth
  join is made smooth within 1.5 units (2 where its curves are drawn again), no curve passing an extreme, a corner of
  the upright kept a corner. The bold section's terminal openings (14 and 26 units against 36 and 54) are taken from
  its terminals to 32.

A fifth pass, shared by the four faces, corrects three defects a fourth independent review found in all of them
(key `fifth_pass`; `scripts/symbols.py` and `scripts/build2.py`, switched on in `scripts/build_candidate.py`):

- **≈** (judged). It was two tildes stretched to the sign's width: 362 units tall (60..422) against the ='s 198
  (142..340), its waves heavier than the bars (72 against 61) and 97 apart where the bars stand 78. Its waves are
  now drawn at the bars' weight (60; Bold 92 against 93), centred where the bars are on the 241 axis and 0.7 of
  the ='s white apart (55): 236 tall (123..359; Bold 304 against the ='s 263). The fourth pass's bold ≈ (96 apart,
  433 tall) gives way to it.
- **Rings** (judged). The rings of © ® @ ° ¤ were hairlines of 31 to 43 units (Bold 53 to 66) beside an o whose
  heavier side is 109 (Bold 160). Each is now at least half of it: 56 (Italic 59 to 61, Bold 82 to 83, Bold Italic
  86 to 87), grown inward as far as the c, r and a leave room (© and ® stay 700 tall in the Regular and Italic, 709
  and 714 in the Bold styles) and outward beyond that, the letters as drawn and clear of the ring (the Regular's a
  33 from its ring); ° keeps a counter of 0.7 of its ring (56 by 64), ¤ one of 1.5 times it (237). at.case follows @.
- **Combining marks** (judged). Every top mark used the ponc's anchor, there was no mkmk (x + circumflex + acute
  set the acute 154 units into the circumflex), no precomposed letter had anchors, the comma below ran 49 to 108
  units into the descenders of f g j y, and U+0323 had no glyph. The dot above keeps its anchor, so ḃ ċ ḋ ḟ ġ ṁ ṗ ṡ
  ṫ and base + U+0307 shape as before; every other top mark stands at least the accents' gap from the letter's ink
  (45 to 46, as on á); precomposed letters carry their own anchors and mkmk stacks marks 46 apart; the comma and the
  new dot below stand at least 21 clear (f̦ 31, g̦ 35, under the descender).

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
