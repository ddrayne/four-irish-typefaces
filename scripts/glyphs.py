"""Traced outlines -> cleaned pathops Paths in font units (y up, baseline 0)."""
import traced
import os, pickle, numpy as np, pathops
from fontTools.pens.recordingPen import RecordingPen, replayRecording
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from metrics import line_baselines

SCALE = {'kilfane': 720/31.82, 'tuam': 545/19.29, 'carrick': 550/24.07, 'ceili': 540/23.15}

def to_path(rec, xform):
    p = pathops.Path(); pen = p.getPen()
    replayRecording(rec, TransformPen(pen, xform))
    return p

def clean(p):
    out = pathops.simplify(p, fix_winding=True, keep_starting_points=False, clockwise=False)
    return out

def bounds(p):
    bp = BoundsPen(None); p.draw(bp); return bp.bounds

def contours(p):
    """Split a path into single-contour paths."""
    rec = RecordingPen(); p.draw(rec)
    out, cur = [], []
    for op, args in rec.value:
        cur.append((op, args))
        if op in ('closePath', 'endPath'):
            q = pathops.Path(); replayRecording(cur, q.getPen()); out.append(q); cur = []
    return out

def union(paths):
    acc = pathops.Path()
    for p in paths:
        acc = pathops.op(acc, p, pathops.PathOp.UNION, fix_winding=True, keep_starting_points=False, clockwise=False)
    return acc

def translate(p, dx, dy, sx=1.0, sy=1.0):
    q = pathops.Path(); p.draw(TransformPen(q.getPen(), (sx, 0, 0, sy, dx, dy))); return q

def load(font):
    res = traced.records(font)
    base = line_baselines(res); s = SCALE[font]
    G = {}
    for r in res:
        b0 = base[r['line_idx']]
        # x: source col * s (absolute for now); y: (baseline - row) * s
        p = clean(to_path(r['rec'], (s, 0, 0, -s, 0, b0*s)))
        xmin, ymin, xmax, ymax = bounds(p)
        G[r['name']] = dict(path=translate(p, -xmin, 0), line=r['line_idx'], src_x=(r['b'][0], r['b'][2]))
    return G, s

if __name__ == '__main__':
    import sys
    font = sys.argv[1]; G, s = load(font)
    for name in sys.argv[2:]:
        p = G[name]['path']
        print(name, 'bbox', [round(v) for v in bounds(p)], 'contours:',
              [[round(v) for v in bounds(c)] for c in contours(p)])
