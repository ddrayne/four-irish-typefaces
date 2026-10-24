"""The traced outlines: one JSON file per face in sources/traced/.

Each glyph record keeps what trace3.py measured on the scan: its name, the flyer line it sits on,
the local paper and ink levels, and its redrawn outline as pen operations in scan pixels
(x right, y down). JSON floats round-trip exactly, so a build from these files is identical to a
build from the tracer's own output.
"""
import json, os
import paths


def path(face):
    return os.path.join(paths.TRACED, f'{face}.json')


def records(face):
    d = json.load(open(path(face)))
    out = []
    for g in d['glyphs']:
        r = dict(g)
        r['rec'] = [(op, tuple(tuple(pt) for pt in args)) for op, args in g['rec']]
        out.append(r)
    return out


def save(face, res):
    """One pen operation per line, so a re-trace shows up in a diff as the operations that moved."""
    c = lambda v: json.dumps(v, separators=(',', ':'))
    lines = ['{', f'"face":{c(face)},', '"units":"scan pixels, x right, y down",', '"source":"sources/flyer.jpg",', '"glyphs":[']
    for i, r in enumerate(res):
        meta = {k: (float(v) if hasattr(v, 'dtype') else v) for k, v in r.items() if k not in ('rec', 'b')}
        ops = [c([op, [[float(x), float(y)] for x, y in args]]) for op, args in r['rec']]
        lines.append('{' + c(meta)[1:-1] + ',"rec":[')
        lines.append(',\n'.join(ops))
        lines.append(']}' + (',' if i < len(res) - 1 else ''))
    lines += [']', '}']
    with open(path(face), 'w') as f:
        f.write('\n'.join(lines) + '\n')
