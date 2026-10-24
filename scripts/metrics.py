import traced
import os, pickle, sys, numpy as np
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import replayRecording

def bounds(rec):
    bp = BoundsPen(None); replayRecording(rec, bp); return bp.bounds  # (xmin, rowmin, xmax, rowmax)

XH = set('a c e m n o r s u v w x z'.split())
ASC = set('b d h k l'.split()); DESC = set('p q'.split())
CAPS = set('E F H I K L M N T U V W X Z'.split()); FIG = set('one two four five seven'.split())

def line_baselines(res):
    by = {}
    for r in res:
        r['b'] = bounds(r['rec']); by.setdefault(r['line_idx'], []).append(r)
    base = {}
    for li, rs in by.items():
        bots = np.array([r['b'][3] for r in rs]); med = np.median(bots)
        sit = bots[np.abs(bots - med) <= 1.5]
        base[li] = float(np.median(sit))
    return base

def stats(font):
    res = traced.records(font)
    base = line_baselines(res)
    def pick(names, key):
        v = [key(r) for r in res if r['name'] in names]
        return (round(float(np.median(v)), 2), len(v)) if v else None
    top = lambda r: base[r['line_idx']] - r['b'][1]
    bot = lambda r: base[r['line_idx']] - r['b'][3]
    return dict(base={k: round(v, 2) for k, v in base.items()}, xh=pick(XH, top), asc=pick(ASC, top), desc=pick(DESC, bot),
                cap=pick(CAPS, top), fig=pick(FIG, top), maxtop=round(max(top(r) for r in res), 1), minbot=round(min(bot(r) for r in res), 1))

if __name__ == '__main__':
    for f in sys.argv[1:]: print(f, stats(f))
