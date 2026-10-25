# Kilfane Study 4: the judgement pass

Study 3 ([kilfane-production](../kilfane-production/README.md)) with four kinds of correction, each
decided by comparing every print of a letter rather than by following one trace. This is a research
candidate: it does not replace the release.

## How the letters were judged

`scripts/evidence_board.py` sets each glyph beside every source that prints it: the alphabet specimen
N516, the competition advert N47 (a second print of the same paste-up, located row by row), the flyer,
and for capitals the mean of the N517 production impressions. The font's outline is registered over
each by translation and one uniform scale, and a consensus view maps the prints into the font's own
coordinates: where they all print ink, where only one does, and where the outline runs. A gap one print
has and another fills is print; a feature every print agrees on is drawing. `scripts/pinches.py` lists
every neck that, cut, would split a glyph or open a counter, with its width as a share of the stem.

N516's blur was measured from its stem edges (sigma about 0.85 px). Strokes and joins wider than two
source pixels are traced without bias at that blur, so no deblurring was attempted: the thin places in
the traces are in the prints themselves.

The boards hold archive pixels and stay in ignored `build/judgement/` (see [RIGHTS](../RIGHTS.md)).

## What changed

**Capitals from the production sheets keep N516's frame.** Study 3's impressions were registered by
affine transforms that absorb the photograph's perspective, and some letters' scale drifted from the
base frame: L by 2%, O, P and R by about 1%. `scripts/fit_production.py --lock-frame` puts each redrawn
letter back at its round-2 size and place (one uniform scale about the letter's centre and a shift,
chosen by overlap with the round-2 trace); only the shape comes from the sheet. Each letter's correction
is in `traces/evidence.json` (`frame_lock`).

| Letter | Scale applied | Letter | Scale applied |
|---|---:|---|---:|
| L | 0.980 | M | 0.994 |
| O | 0.991 | R | 0.994 |
| P | 0.992 | A.alt1 | 0.995 |

Every other redrawn capital moves by under half a percent.

**T, U, k and l from N516.** These touch their neighbours on every print (N516, N47 and N46), so
every earlier round kept their flyer-resolution traces. `scripts/separate_touching.py` traces each pair
from N516 as round 2 traced every other letter, and divides the fused ink at its narrowest neck (a
watershed of the ink's distance map, flooded from each letter's body). On N516, T and U meet only along a
hairline at the top edge, so U keeps the flag on its left stem that the flyer-era cut had given to T's
beak; k's leg meets l's foot at a point. The cut across each neck is a construction; the rest of the
four letters is N516's drawing.

**The e's notch is eased.** N516 and N47 agree that the bowl's terminal meets the bar at a hairline,
with a white notch running almost into the eye. The hairline (about 34 units) matches the face's other
bowl joins (b, p, B, P and R all join at 32 to 33 units) and is kept. At text sizes, though, the notch
and the eye run together and the e reads as broken. `scripts/judge.py` closes the notch's inner end where it
is narrower than about 30 units and keeps its mouth. This is a judged edit, not attested drawing, and it
is recorded as such ([judged-edits.json](judged-edits.json); `judged_edits` in the evidence).

## Not changed, after review

- **The capitals' bars.** E's bar is about 82 units deep here against 50 in the flyer-traced release; H's
  crossbar sits where N516, N47 and the 14-impression N517 mean all put it.
- **X** keeps the pointed foot at the bottom of its thin stroke and the curl at the bottom of its thick
  one: N516 and N47 both draw them. The release, traced from the flyer, lost the foot.
- **J, 3** and the other letters the boards flagged were checked at the face's own scale and agree
  with the prints.

## Reproduce

```sh
python scripts/fetch_sources.py --source N516 --format jpg
python scripts/fetch_sources.py --source N47 --format jpg
python scripts/fetch_sources.py --source N517 --format jpg
python scripts/trace_production.py kilfane
python scripts/fit_production.py kilfane --round research/kilfane-judgement --lock-frame
python scripts/separate_touching.py kilfane --traces research/kilfane-judgement/traces
python scripts/judge.py kilfane --traces research/kilfane-judgement/traces --edits research/kilfane-judgement/judged-edits.json
python scripts/build_original_study.py --face kilfane --study 4 --traces research/kilfane-judgement/traces --output research/kilfane-judgement/fonts
python scripts/evidence_board.py kilfane research/kilfane-judgement/fonts/KilfaneStudy4-Regular.otf \
    --evidence research/kilfane-judgement/traces/evidence.json      # the boards, into build/judgement/kilfane
```
