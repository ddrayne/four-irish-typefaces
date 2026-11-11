"""Where each glyph of the released Regulars comes from, for the showcase's provenance map.

scripts/showcase.py calls build(dest): data/provenance/<face>.json, one per face, fetched by
the page only when its section comes near. Everything is read from committed files:

  fonts/otf/<Family>-Regular.otf                the release's glyphs and outlines
  <study>/fonts/*-Regular.provenance.json       the builder's record of how each glyph is made: [kind, words]
  <study>/traces/evidence.json                  per traced glyph: prints, regions, impressions, residuals, decisions
  <study>/judged-edits.json                     the release's judged corrections and finishing passes
  research/downloads.json, source-register.json the prints' catalogue records (links only: no scan is copied)

<study> is each face's latest study, as scripts/build_candidate.py names it (LATEST).

Three classes, decided from the builder's record alone:

  a  attested        the record's kind is a trace of a 1978 print (original-specimen, flyer)
  r  reconstruction  not a trace itself, but the record names a print, or a traced glyph it is made from
  m  modern          nothing in the record ties its shape to a print: drawn in 2026 to match (a weight
                     taken from the prints does not make a shape theirs), or not in the record at all

Nothing here is a judgement of its own: a glyph the files do not describe says so.
"""
import json, os, re, unicodedata
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.boundsPen import BoundsPen
import paths
from build2 import FONTS, VERSION

RESEARCH = os.path.join(paths.ROOT, 'research')
OTF = os.path.join(paths.ROOT, 'fonts', 'otf')
ORDER = ['ceili', 'carrick', 'kilfane', 'tuam']
TRACED_KINDS = ('original-specimen', 'flyer')
# words in the builder's record that tie a shape to a print
SOURCE_WORDS = re.compile(r'NIVAL|flyer’s|sheet’s|sheet\'s|from the sheet|specimen’s|accent on ')
# ... unless only a weight or a width was taken from it
WEIGHT_ONLY = re.compile(r'at the (mean )?weight of [^;]*|at the NIVAL \w+ endash weight|'
                         r'(stroke weight|width) calibrated (from|to) [^;]*')
# construction words that name a glyph of the face (scripts/symbols.py and build2.py write them)
PART_WORDS = {'period': ['period'], 'periods': ['period'], 'comma': ['comma'], 'commas': ['comma'],
              'quotes': ['quoteright'], 'zero': ['zero'], 'zeros': ['zero'], 'percent': ['percent'],
              'plus': ['plus'], 'equal': ['equal'], 'circumflex': ['circumflex'],
              'tilde': ['tilde'], 'tildes': ['tilde'], 'long s': ['longs'],
              'small figure': ['one', 'two', 'three'], 'fraction': ['one', 'two', 'three', 'four', 'fraction']}
PART_LETTER = re.compile(r"(?:^|\+ ?|small |rotated |interlaced )([A-Za-z!?'])(?=$|[ +,])")
MARK_GLYPHS = {'grave': 'grave', 'acute': 'acute', 'circumflex': 'circumflex', 'tilde': 'tilde', 'diaeresis': 'dieresis',
               'ring': 'ring', 'caron': 'caron', 'breve': 'breve', 'dot': 'dotaccent', 'macron': 'macron',
               'cedilla': 'cedilla', 'ogonek': 'ogonek', 'double acute': 'hungarumlaut'}
# keys of judged-edits.json that list the glyphs a rule changed
GLYPH_KEYS = ('glyph', 'glyphs', 'added', 'Regular')
REASON_KEYS = ('reason', 'why', 'what')
PROSE_KEYS = ('about', 'note', 'face', 'applied_by', 'frame', 'derived_frame', 'code', 'final_review', 'op')


def latest():
    """Each face's latest study folder, from scripts/build_candidate.py (the release is built from it)."""
    import build_candidate
    return {k: os.path.dirname(os.path.join(paths.ROOT, v)) for k, v in build_candidate.LATEST.items()}


def load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def catalogue():
    """The prints by source id: title and catalogue link (research/source-register.json), pixel size and the file
    names the evidence uses for them (research/downloads.json)."""
    out, files = {}, {}
    for s in load(os.path.join(RESEARCH, 'source-register.json')).get('sources', []):
        out[s['id']] = dict(id=s['id'], title=s.get('title'), url=s.get('url'))
    for a in load(os.path.join(RESEARCH, 'downloads.json')).get('assets', []):
        sid = a.get('source_id')
        if not sid or 'path' not in a:
            continue
        files[os.path.basename(a['path'])] = sid
        rec = out.setdefault(sid, dict(id=sid, title=None, url=None))
        rec['url'] = a.get('catalogue_url') or rec['url']
        if a.get('reference'):
            rec['ref'] = a['reference']
        if a.get('width') and a.get('format') == 'jpg':
            rec['px'] = f'{a["width"]} × {a["height"]}'
    out['flyer'] = dict(id='flyer', title='the 1978 flyer, as scanned for this project', url='#fianaise')
    files['flyer.jpg'] = 'flyer'
    return out, files


def source_ids(text, files):
    """The prints a string names, in order: by file name, by id (N516), or as the flyer trace."""
    hits = []
    for m in re.finditer(r'[\w-]+\.(?:jpg|pdf)|\bN\d{2,3}\b|\bB2\b|flyer trace', text or ''):
        t = m.group(0)
        sid = files.get(t) or ('flyer' if t == 'flyer trace' else t if re.fullmatch(r'N\d+|B2', t) else None)
        if sid and sid not in hits:
            hits.append(sid)
    return hits


def num(v):
    if isinstance(v, bool):
        return 'yes' if v else 'no'
    if isinstance(v, float):
        return f'{v:.3f}'.rstrip('0').rstrip('.')
    return str(v)


def words(v, limit=220):
    """A value from the research files as plain words: 'radius 0.7, reach 3'."""
    def w(x):
        if isinstance(x, dict):
            return ', '.join(f'{k.replace("_", " ")} {w(y)}' for k, y in x.items())
        if isinstance(x, (list, tuple)):
            if all(not isinstance(y, (dict, list)) for y in x):
                return ('[' + ', '.join(num(y) for y in x) + ']') if x else 'none'
            return '; '.join(w(y) for y in x)
        return num(x)
    s = w(v)
    return s if len(s) <= limit else s[:limit - 1].rstrip() + '…'


def pieces(t):
    """[pieces, counters] as words."""
    p, c = t
    return f'{p} piece{"" if p == 1 else "s"}, {c} counter{"" if c == 1 else "s"}'


# ---------------------------------------------------------------------- the judged corrections

def rules_of(doc, glyphs):
    """Every rule of a judged-edits.json: (label, reason, style, numbers, [(glyph, own reason?, numbers)]).

    The files differ per face, so this reads their shapes, not their names: a rule is an entry with a reason
    ('reason', 'why' or 'what'), or a block X beside an 'X_reason'; the glyphs it changed are those it lists
    under 'glyph', 'glyphs', 'added' or 'Regular', or the glyph names it is keyed by. In a list of edits an
    entry without a reason follows the last entry that gave one (the files give a run's reason once): it is
    kept with that reason and marked as not having its own. A rule that lists no glyph is a rule for the face."""
    out = []

    def named(v, extra=None):
        """(glyph, numbers) for the glyph names in a value."""
        if isinstance(v, str):
            return [(v, extra)]
        if isinstance(v, list):
            return [(g, extra) for g in v if isinstance(g, str)]
        if isinstance(v, dict):
            return [(g, y if not isinstance(y, (dict, list, str)) or y else None) for g, y in v.items()
                    if not (isinstance(y, (list, dict)) and not y)]
        return []

    def collect(node):
        """The glyphs a rule block lists, with the numbers given for each, and the block's other numbers."""
        got, nums = [], {}
        if not isinstance(node, dict):
            return got, nums
        direct = any(k in node for k in GLYPH_KEYS)
        for k, v in node.items():
            if k in GLYPH_KEYS:
                got += named(v)
            elif k in REASON_KEYS or k in PROSE_KEYS or k.endswith('_reason'):
                continue
            elif isinstance(v, dict) and not any(r in v for r in REASON_KEYS):
                if k in glyphs and not direct:                 # keyed by glyph: {"a": [...]}
                    if v:
                        got.append((k, v))
                else:
                    sub, subnums = collect(v)                   # {"lowercase": {"target": 114, "glyphs": {...}}}
                    got += [(g, {**subnums, **({'at': y} if y is not None else {})} if subnums else y) for g, y in sub]
                    if not sub:
                        nums[k] = v
            elif isinstance(v, list) and k in glyphs and not direct:
                if v:
                    got.append((k, v))
            elif isinstance(v, list) and v and all(isinstance(y, dict) for y in v):
                continue                                        # a list of rules of its own (walked below)
            elif isinstance(v, list) and len(v) > 6 and all(isinstance(y, str) for y in v):
                continue                                        # a long list of names: the reason speaks for it
            elif not isinstance(v, dict):
                nums[k] = v
        return got, nums

    def style(label):
        low = label.lower()
        return 'bold' if 'bold' in low else 'sloped' if re.search(r'sloped|italic', low) else None

    def emit(label, reason, node, inherit=None):
        got, nums = collect(node)
        hits, also = [], []
        for g, y in got:
            for cand in (g, g.split('.')[0]):                   # dieresis.l is a piece of the glyph dieresis
                if cand in glyphs:
                    if (cand, y) not in hits:
                        hits.append((cand, y))
                    break
            else:
                also.append(g)
        op = node.get('op') if isinstance(node, dict) else None
        if inherit is not None and reason is None:
            rule = inherit
            for g, y in hits:
                rule['hits'].append((g, False, words({**({'op': op} if op else {}), **nums, **(y if isinstance(y, dict) else {})}) or None))
            return rule
        rule = dict(label=label + (f' › {op.replace("_", " ")}' if op else ''), reason=reason, style=style(label + ' ' + (op or '')),
                    nums=words(nums) if nums else None, also=also, hits=[])
        if inherit is False:                                    # a list entry: its numbers are its own
            rule['nums'] = None
            rule['hits'] = [(g, True, words({**nums, **(y if isinstance(y, dict) else {})}) or None) for g, y in hits]
        else:
            rule['hits'] = [(g, True, words(y) if y not in (None, '', [], {}) else None) for g, y in hits]
        out.append(rule)
        return rule

    def walk(node, path):
        label = ' › '.join(p.replace('_', ' ') for p in path)
        if isinstance(node, list):
            last = None
            for item in node:
                if not isinstance(item, dict):
                    continue
                reason = next((item[k] for k in REASON_KEYS if isinstance(item.get(k), str)), None)
                if reason is None and last is None:
                    continue
                last = emit(label, reason, item, inherit=last if reason is None else False)
            return
        if not isinstance(node, dict):
            return
        reason = next((node[k] for k in REASON_KEYS if isinstance(node.get(k), str)), None)
        if reason is not None and path:
            emit(label, reason, node)
        for k, v in node.items():
            sub = path + [k]
            if k.endswith('_reason') and isinstance(v, str) and k[:-7] in node:
                emit(' › '.join(p.replace('_', ' ') for p in path + [k[:-7]]), v, node[k[:-7]] if isinstance(node[k[:-7]], dict) else {})
            elif isinstance(v, str) and k not in REASON_KEYS and k not in PROSE_KEYS and not k.endswith('_reason') and len(v) > 60:
                # a reason on its own: for the glyph it is keyed by, or (no glyph named) for the face
                emit(label if k in glyphs else ' › '.join(p.replace('_', ' ') for p in sub), v, {'glyph': k} if k in glyphs else {})
            elif isinstance(v, (dict, list)):
                walk(v, sub)

    walk(doc, [])
    return out


# ---------------------------------------------------------------------- the evidence for a traced glyph

def evidence_facts(e, ev, cat, files):
    """What evidence.json records for one traced glyph: (basis, sources, facts, notes, disagree)."""
    facts, notes, disagree = [], [], False
    region = lambda box: f'x {box[0]}–{box[2]}, y {box[1]}–{box[3]} px'
    if e.get('status') == 'retained' or 'source' not in e and 'prints' not in e:
        return 'kept', ['flyer'], [], [e['reason']] if e.get('reason') else [], False
    if 'impressions' in e:                      # the mean of repeated impressions on a production sheet
        basis = 'sheet'
        src = source_ids(e['source'], files)
        prod = ev.get('production_impressions', {})
        frame = source_ids(e.get('proportion_source', ''), files)
        facts.append(['Outline', f'mean of {e["impressions"]} impressions on the {e.get("sheet", "")} Letraset sheet'
                      + (f' ({e["source_id"]})' if e.get('source_id') else '')])
        if e.get('proportion_source'):
            facts.append(['Size and place', 'from ' + (' and '.join('the flyer trace' if f == 'flyer' else f for f in frame) if frame else e['proportion_source'])
                          + (f', {region(e["box"])}' if e.get('box') else '')])
        if e.get('rms_to_mean'):
            r = e['rms_to_mean']
            facts.append(['Spread', f'{sum(r) / len(r):.3f} mean, {max(r):.3f} worst: each impression against their mean (RMS of ink, 0 to 1)'
                          + (f'; a sheet mean is used only where the mean is {num(prod["max_spread"])} or under' if 'max_spread' in prod else '')])
        fl = e.get('frame_lock', {})
        if 'iou_to_base' in fl:
            facts.append(['Against the earlier trace', f'overlap {num(fl["iou_to_base"])}, scale {num(fl.get("scale"))}'])
        sf = fl.get('sheet_frame')
        if sf:
            facts.append(['Sheet frame', f'turn {num(sf["turn_deg"])}°, shear removed {num(sf["shear_removed_deg"])}°'])
        if e.get('gaps_from_impressions', {}).get('note'):
            notes.append(e['gaps_from_impressions']['note'])
    elif 'prints' in e:                         # Céilí: the mean of the averaged prints, others compared
        av = [p for p in e['prints'] if p.get('averaged')]
        rest = [p['print'] for p in e['prints'] if not p.get('averaged')]
        src = [p['source_id'] for p in av]
        basis = 'two' if len(av) > 1 else 'one'
        facts.append(['Outline', f'mean of {len(av)} prints: ' + ' and '.join(src) if len(av) > 1 else f'traced from {src[0]}'])
        if e.get('box'):
            facts.append(['Region', region(e['box']) + f' on {src[0]}'])
        if rest:
            facts.append(['Compared, not averaged', ', '.join(dict.fromkeys(rest))])
        facts.append(['Spread', ', '.join(f'{p["print"]} {num(p["rms_to_mean"])}' for p in av) + ': each print against their mean (RMS of ink, 0 to 1)'])
        tp = e.get('topology', {})
        tops = {tuple(p['topology']) for p in av if 'topology' in p}
        disagree = len(tops) > 1
        if 'attested' in tp:
            facts.append(['Pieces and counters', ', '.join(f'{p["print"]} {pieces(p["topology"])}' for p in av if 'topology' in p)
                          + f'; drawn with {pieces(tp.get("fitted", tp["attested"]))}'])
        if tp.get('rule'):
            notes.append(tp['rule'])
        groups = {}
        for d in tp.get('disagreements', []):
            key = (d.get('kind'), bool(d.get('drawn')), d.get('why'))
            groups[key] = groups.get(key, 0) + 1
        for (kind, drawn, why), n in groups.items():
            notes.append(f'{n} × {kind}, {"drawn" if drawn else "not drawn"}: {why}.')
        if 'iou_to_base' in e.get('frame_check', {}):
            facts.append(['Against the earlier trace', f'overlap {num(e["frame_check"]["iou_to_base"])}'])
    elif 'check' in e:                          # Tuam: the mean of two prints
        basis = 'two'
        a, b = source_ids(e['source'], files), [e['check'].get('source_id')]
        src = a + [s for s in b if s and s not in a]
        facts.append(['Outline', f'mean of 2 prints: {" and ".join(src)}, in {src[0]}’s frame'])
        facts.append(['Region', f'{region(e["box"])} on {src[0]}; {region(e["check"]["box"])} on {src[-1]}'])
        if 'correlation' in e['check']:
            facts.append(['Agreement', f'correlation {num(e["check"]["correlation"])} between the two prints'])
        ed = e.get('edges', {})
        if 'mean_abs_px' in ed:
            s = ed.get('mean_signed_px', 0)
            facts.append(['Edges', f'{num(ed["mean_abs_px"])} px apart on average ({src[0]} pixels); {src[-1]} prints '
                          f'{"lighter" if s < 0 else "bolder"} by {num(abs(s))} px'])
        if e.get('uncertainty_font_units') is not None:
            facts.append(['Edge uncertainty', f'±{num(e["uncertainty_font_units"])} font units: half the distance between the prints’ edges'])
        tp = e.get('topology', {})
        if tp.get('prints'):
            vals = list(tp['prints'].values())
            disagree = any(v != vals[0] for v in vals)
            facts.append(['Pieces and counters', ', '.join(f'{k} {pieces(v)}' for k, v in tp['prints'].items())
                          + f'; drawn with {pieces(tp["decided"])}'])
            if tp.get('decision'):
                notes.append(tp['decision'][:1].upper() + tp['decision'][1:] + '.')
    else:                                       # one print
        basis = 'one'
        src = source_ids(e['source'], files)
        facts.append(['Outline', f'traced from one print: {src[0] if src else e["source"]}'])
        if e.get('box'):
            facts.append(['Region', region(e['box'])])
        if e.get('method') == 'separated' and e.get('pair'):
            facts.append(['Separated', f'it touches its neighbour on the print ({" and ".join(e["pair"])})'])
    if e.get('scale') and basis in ('one', 'sheet'):
        facts.append(['Scale', f'{e["scale"]:.2f} source pixels to a trace unit'])
    if e.get('note'):
        notes.append(e['note'])
    kept = ev.get('production_impressions', {}).get('base_kept_for_topology', {}).get(e['name'])
    if kept:
        notes.append(f'The {kept.get("sheet", "production")} sheet’s mean draws it with {pieces(kept["mean_pieces_counters"])}; '
                     f'the single-print trace, with {pieces(kept["base_pieces_counters"])}, is kept.')
    tidy = lambda t: t[:1].upper() + t[1:] + ('' if t.rstrip()[-1:] in '.?!' else '.')
    return basis, src, facts, [tidy(t) for t in notes if t], disagree


# ---------------------------------------------------------------------- one face

def face_data(k, study, cat, files):
    cfg = FONTS[k]
    tt = TTFont(os.path.join(OTF, f'{cfg["ps"]}-Regular.otf'))
    order = tt.getGlyphOrder()
    gs = tt.getGlyphSet()
    cmap = tt.getBestCmap()
    rel = lambda p: os.path.relpath(p, paths.ROOT).replace(os.sep, '/')

    recs = [f for f in sorted(os.listdir(os.path.join(study, 'fonts'))) if f.endswith('-Regular.provenance.json')]
    record_path = os.path.join(study, 'fonts', recs[0]) if len(recs) == 1 else None
    record = load(record_path) if record_path else {}
    ev_path = os.path.join(study, 'traces', 'evidence.json')
    ev = load(ev_path) if os.path.exists(ev_path) else {}
    traces = {g['name']: g for g in ev.get('glyphs', [])}
    je_path = os.path.join(study, 'judged-edits.json')
    je = load(je_path) if os.path.exists(je_path) else {}

    # glyph -> character and the stylistic set that calls it up
    char = {}
    for cp, g in sorted(cmap.items()):
        if 0xE000 <= cp <= 0xF8FF:
            continue
        if g not in char or (chr(cp).islower() and not chr(char[g][0]).islower()):
            char[g] = (cp, None)
    alts = {alt: (base, tag) for tag, _, mapping in cfg.get('sets', []) for base, alt in mapping.items()}
    for g in order:
        if g in char or '.' not in g[1:]:
            continue
        root, suffix = g.split('.', 1)
        base = next((b for b in (root, root[:1].lower() + root[1:]) if b in char), None)   # Aacute.alt1 -> Aacute
        if base:
            tag = next((t for a, (b, t) in alts.items() if a.endswith('.' + suffix) and a.split('.')[0] == re.sub(
                r'(grave|acute|circumflex|tilde|dieresis|ring|macron|breve|ogonek|caron|dotaccent)$', '', root)), None)
            char[g] = (char[base][0], tag or suffix)

    def describe(text):
        # the builder calls its traced source "the flyer" whatever print the trace now comes from
        return text.replace('the flyer’s', 'the traced').replace('the 1978 flyer', 'the print')

    def parts_of(name):
        """The glyphs of the face that the record says a glyph is made from."""
        kind, text = record[name]
        found = []
        m = re.search(r'base source ([\w.]+):', text)
        if m:
            found.append(m.group(1))
        head = text.split(';')[0]
        if kind == 'composite' and ' + ' in head:
            base, mark = head.split(' + ', 1)
            found.append(base.strip())
            mk = next((g for w, g in sorted(MARK_GLYPHS.items(), key=lambda p: -len(p[0])) if re.match(rf'(the |its own )?{w}\b', mark)), None)
            if mk:
                found.append(mk)
        elif kind in ('made', 'rebuilt') and not SOURCE_WORDS.search(text):
            plain = re.sub(r"[’']s\b", '', head) if not head.startswith("'") else head
            if plain == 'insular s':
                found += [alt for tag, label, mapping in cfg.get('sets', []) if 'nsular' in label for b, alt in mapping.items() if b == 's']
            for w, gl in PART_WORDS.items():
                if re.search(rf'(?<![a-z]){w}(?![a-z])', plain) and not (w == 'fraction' and plain != 'fraction'):
                    found += gl
            for ch in PART_LETTER.findall(plain):
                g = cmap.get(ord(ch))
                if g:
                    found.append(g)
        return [g for g in dict.fromkeys(found) if g in order and g != name]

    parts = {n: parts_of(n) for n in order if n in record}
    cls = {}

    def classify(name, seen=()):
        if name in cls:
            return cls[name]
        if name not in record:
            root = name.rsplit('.', 1)[0]
            c = 'm' if root == name or root not in record or name in seen else ('m' if classify(root, seen + (name,)) == 'm' else 'r')
        else:
            kind, text = record[name]
            if kind in TRACED_KINDS:
                c = 'a'
            elif SOURCE_WORDS.search(WEIGHT_ONLY.sub('', text.split('; base source')[0])) and kind != 'composite':
                c = 'r'
            elif name in seen:
                c = 'm'
            else:
                c = 'r' if any(classify(p, seen + (name,)) != 'm' for p in parts[name]) else 'm'
        cls[name] = c
        return c

    for n in order:
        classify(n)

    # the judged corrections, and which glyphs each names; a release form (hyphen.case) goes with its glyph
    rules = rules_of(je, set(order))
    by_glyph = {}
    for i, r in enumerate(rules):
        for g, own, nums in r['hits']:
            by_glyph.setdefault(g, []).append([i, nums, own])
            for form in order:
                if form not in record and form.rsplit('.', 1)[0] == g and form != g:
                    by_glyph.setdefault(form, []).append([i, nums, own])

    n_ = lambda v: ('%d' % round(v)) if abs(v - round(v)) < 0.05 else ('%.1f' % v)
    glyphs = []
    for name in order:
        rec = DecomposingRecordingPen(gs)
        gs[name].draw(rec)
        d = []
        for op, args in rec.value:
            if op in ('moveTo', 'lineTo', 'curveTo'):
                d.append({'moveTo': 'M', 'lineTo': 'L', 'curveTo': 'C'}[op] + ' '.join(f'{n_(x)} {n_(y)}' for x, y in args))
            elif op in ('closePath', 'endPath'):
                d.append('Z')
        bp = BoundsPen(gs)
        gs[name].draw(bp)
        g = dict(n=name, c=cls[name], d=''.join(d), b=[round(v) for v in bp.bounds] if bp.bounds else None, w=gs[name].width)
        if name in char:
            cp, tag = char[name]
            g['u'] = cp
            if tag:
                g['set'] = tag
        e = traces.get(name)
        if name in record:
            kind, text = record[name]
            g['k'] = kind
            g['how'] = describe(text.split('; base source')[0])
            if parts[name]:
                g['parts'] = parts[name]
            src = source_ids(text, files)
        else:
            root = name.rsplit('.', 1)[0]
            g['how'] = None
            if root != name and root in record:
                g['of'] = root                   # a release form of another glyph (hyphen.case)
            src = []
        if e and (cls[name] == 'a' or e.get('status') == 'candidate'):
            basis, esrc, facts, notes, disagree = evidence_facts(e, ev, cat, files)
            if cls[name] == 'a':
                g['basis'] = basis
                src = esrc
            else:
                g['traced'] = True               # the print's own drawing of it exists, though the glyph is built (Tuam's á)
                src = list(dict.fromkeys(src + esrc))
            g['facts'], g['notes'] = facts, notes
            if disagree:
                g['dis'] = True
        elif cls[name] == 'a':
            g['basis'] = None                    # traced, but evidence.json has no entry under its name
        if src:
            g['src'] = src
        if name in by_glyph:
            g['rules'] = by_glyph[name]
        glyphs.append(g)

    used = sorted({s for g in glyphs for s in g.get('src', [])}, key=lambda s: (not s.startswith('N'), len(s), s))
    counts = {c: sum(1 for g in glyphs if g['c'] == c) for c in 'arm'}
    limits = list(ev.get('limitations', []))
    for key in ('production_impressions', 'consensus'):
        if ev.get(key, {}).get('caveat'):
            limits.append(ev[key]['caveat'])
    os2, upm = tt['OS/2'], tt['head'].unitsPerEm
    family = TTFont(os.path.join(study, 'fonts', recs[0].replace('.provenance.json', '.otf')))['name'].getDebugName(1) if recs else None
    return dict(
        face=k, v=VERSION, study=family, m=[upm, tt['hhea'].ascent, tt['hhea'].descent, os2.sCapHeight, os2.sxHeight],
        files=dict(record=rel(record_path) if record_path else None, evidence=rel(ev_path) if ev else None,
                   edits=rel(je_path) if je else None),
        counts=counts, sources=[cat.get(s, dict(id=s, title=None, url=None)) for s in used],
        rules=[dict(label=r['label'], reason=r['reason'], style=r['style'], nums=r['nums'], also=r['also'],
                    n=len({g for g, _, _ in r['hits']})) for r in rules],
        limits=limits, glyphs=glyphs)


def build(dest):
    """Write data/provenance/<face>.json under dest; returns {face: counts} for the caller's log."""
    out_dir = os.path.join(dest, 'data', 'provenance')
    os.makedirs(out_dir, exist_ok=True)
    cat, files = catalogue()
    studies = latest()
    summary = {}
    for k in ORDER:
        data = face_data(k, studies[k], cat, files)
        with open(os.path.join(out_dir, f'{k}.json'), 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
        summary[k] = data['counts']
    return summary


if __name__ == '__main__':
    import sys
    cat, files = catalogue()
    for k, study in latest().items():
        if sys.argv[1:] and k not in sys.argv[1:]:
            continue
        data = face_data(k, study, cat, files)
        print(k, data['study'], data['counts'], len(data['rules']), 'rules')
