"""Build every style of the four faces from their original-source research, as a release candidate.

usage: python scripts/build_candidate.py [FACE ...] [--version 3.000] [--output build/candidate/fonts]

Each face's Regular is its latest research study's construction (scripts/build_original_study.py:
the round's traces, named marks, punctuation and evidence decisions), so it matches the committed
study's outlines; the 2026 bold and sloped styles are derived from it as the release derives them
from the flyer, and all styles share one set of line metrics. Fonts get the release names, so the
release checks (FONTDIR=build/candidate/fonts make test) apply to them. They are written under
build/ only: promoting them into fonts/ is a separate release decision (R1 in
docs/superpowers/plans/2026-10-25-continuation.md).
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# the latest accepted study of each face (research/HANDOFF.md)
LATEST = {'kilfane': 'research/kilfane-sheet-frame/traces', 'carrick': 'research/round-06/carrick/traces',
          'tuam': 'research/tuam-judgement/traces', 'ceili': 'research/ceili-judgement/traces'}


def build(face, traces, version):
    import build2, build_original_study as study
    if version:
        build2.VERSION = version
    cfg = build2.FONTS[face]
    Study, evidence, piece_data = study.study_class(face, traces)
    retained = any(g['status'] == 'retained' for g in evidence['glyphs'])
    edits = Path(traces).parent / 'judged-edits.json'
    judged = json.loads(edits.read_text(encoding='utf-8'))['edits'] if face == 'carrick' and edits.exists() else []

    class Candidate(Study):
        # The sheets are drawings, not a photocopy: their narrow open joins are drawn, and the bold
        # keeps them. The sloped styles add only a hair of weight, so they keep every gap there is.
        SLIVER, SLIVER_SLOPED = 0.05, 0.01
        FINISH = True
        # a single stem's square foot (Kilfane's F, P, V, 4 and 7) sits on the baseline, not 8 units below
        # it. Kilfane's and Carrick's feet have been reviewed against their sheets (Carrick's are slanted
        # cuts, s's bottom among them, so n, h and s now sit as m and i do); elsewhere the rule would also
        # move letters (Tuam's i, s, u, 9; Céilí's h, n, z, £) that need their own review.
        FLAT_FOOT_WIDENING = 1.2 if face in ('kilfane', 'carrick') else None
        # each original-source glyph is refitted at its own source's resolution (its calibration
        # scale is source pixels per trace unit); letters kept from the flyer were designer-fitted already
        REFIT_PX = {g['name']: 1.0 / g['scale'] for g in evidence['glyphs']
                    if g['status'] == 'candidate' and g.get('scale')}
        # Carrick's finishing pass (research/round-06/carrick/judged-edits.json): letters whose lowest
        # point is a stem's cut foot that the flat-foot test misreads, and the finished outlines settled
        # on the whole-unit grid without the kinks and stubs that rounding leaves (scripts/settle.py)
        CUT_FEET = tuple(e['glyph'] for e in judged if e['op'] == 'cut_foot')
        SETTLE = face == 'carrick'

        def snap(self):
            super().snap()
            for n in self.CUT_FEET:
                if n in self.P:
                    self.P[n] = build2.translate(self.P[n], 0, -build2.bounds(self.P[n])[1])

        def condense(self):
            if self.STUDIO:
                import tuam_studio
                if tuam_studio.condense(self, build2.CONDENSE):
                    return
            if not self.SETTLE:
                return super().condense()
            # the sloped styles' hair of extra weight must not join a glyph's pieces or close an opening
            # its upright keeps (in © the c's cut, in ™ the m's strokes, both narrower than the hair):
            # such a glyph keeps the upright's weight, only narrowed
            import bolden, math, shapes as SH
            t = math.tan(math.radians(build2.SLANT)); yc = self.xh / 2
            def topology(p, slope=True):  # pieces and counters as the font has them: sloped, on the unit grid
                q = SH.transform(p, (1, 0, t, 1, -yc * t, 0)) if slope else p
                a = [bolden.area(c) for c in build2.contours(build2.final_clean(q))]
                outer, holes = sum(x > 0 for x in a), sum(x < 0 for x in a)
                return (outer, holes) if outer else (holes, outer)
            upright = {n: topology(p, slope=False) for n, p in self.P.items() if build2.bounds(p) is not None}
            narrow = {n: SH.transform(p, (build2.CONDENSE, 0, 0, 1, 0, 0)) for n, p in self.P.items()
                      if build2.bounds(p) is not None}
            # and the hair is added by moving the drawing's own nodes (bolden.grow_nodes), not by a
            # stroked offset, which nearly doubled the sloped outlines' nodes
            grow = bolden.grow
            bolden.grow = lambda p, rx, ry, miter=4.0: bolden.grow_nodes(p, rx, ry, miter, fallback=grow)
            try:
                super().condense()
            finally:
                bolden.grow = grow
            self.kept_upright_weight = sorted(n for n, q in narrow.items()
                                              if topology(self.P[n]) != upright[n] and topology(q) == upright[n])
            for n in self.kept_upright_weight:
                self.P[n] = narrow[n]

        def space(self, K):
            super().space(K)
            self.settle_final()

        def slant(self):
            super().slant()
            if self.STUDIO:
                import tuam_studio
                tuam_studio.extremes(self)
            self.settle_final()

        def settle_final(self):
            if not self.SETTLE:
                return
            import settle
            for n, p in self.final.items():
                if build2.bounds(p) is not None:
                    self.final[n] = settle.settle_path(p)

        # Tuam: the studio finishing pass (research/tuam-judgement/judged-edits.json, scripts/tuam_studio.py):
        # judged edits to the traced letters, construction values for the marks, kerning and sloped style, and
        # the @ drawn inside its ring as the (c) and (R) letters are (symbols.make_symbols)
        STUDIO = AT_INSIDE_RING = face == 'tuam'

        def make_marks(self):
            super().make_marks()
            if self.STUDIO:
                import tuam_studio
                tuam_studio.marks(self)

        # Kilfane: the studio finishing pass (scripts/kilfane_studio.py; research/kilfane-sheet-frame/judged-edits.json)
        def finish_traced(self):
            super().finish_traced()
            if face == 'kilfane':
                import kilfane_studio
                kilfane_studio.shapes(self)

        # each finishing pass's zone and kerning steps, one method per step
        def zones(self):
            if face == 'kilfane':
                keep = {n: self.P[n] for n in self.studio}          # the studio pass has set their heights
                super().zones()
                self.P.update(keep)
                return
            super().zones()
            if self.STUDIO:
                import tuam_studio
                tuam_studio.apply(self)

        def kerning(self):
            if face == 'kilfane':
                import kilfane_studio
                from study_spacing import protect_kerning
                build2.Font2.kerning(self)
                kilfane_studio.kern(self)
                protect_kerning(self)
                return
            super().kerning()
            if self.STUDIO:
                import tuam_studio
                tuam_studio.kern(self)

        def vertical(self):
            if face == 'kilfane':
                import kilfane_studio
                kilfane_studio.outlines(self)
            return super().vertical()

        def build(self, flavour):
            f = build2.Font2.build(self, flavour)        # the release's names, not the study's
            if face == 'kilfane':
                import kilfane_studio
                lines = kilfane_studio.load()['lines']
                f['OS/2'].sxHeight, f['OS/2'].sCapHeight = lines['x'], lines['cap']      # the flat lines
            name = f['name']
            text = name.getDebugName(10).replace(
                'Traced from the "Four Irish Typefaces" flyer;',
                'Traced from 1978 originals in the National Irish Visual Arts Library (NIVAL)' +
                (', with a few letters kept from the "Four Irish Typefaces" flyer' if retained else '') + ';'
            ).replace('glyphs not on the sheet were', 'glyphs not on the sheets were')
            name.setName(text, 10, 3, 1, 0x409)
            return f

    fonts = [Candidate(face, st).prepare() for st in build2.FAMILY_STYLES[face]]
    vm = build2.family_metrics(fonts)
    spacing = {}
    for f in fonts:
        base = f.run(vm)
        study.update_provenance(base, f, cfg, evidence, piece_data)
        spacing[f.style_name] = f.spacing_protection
        print(f'{face} {f.style_name}: {len(f.final)} glyphs, {len(f.cm)} code points, stem {f.S:.0f}, '
              f'{len(f.spacing_protection)} spacing fixes, line {vm[0]}/{vm[1]}', flush=True)
    out = Path(os.environ['OUT']) / f'{cfg["ps"]}.spacing-adjustments.json'
    out.write_text(json.dumps(dict(
        method='Full-height one-unit silhouette sampling, two-unit vertical allowance, eight-unit minimum '
               'horizontal clearance (scripts/study_spacing.py), per style.',
        traces=os.path.relpath(Path(traces).resolve(), ROOT), changes=spacing), indent=2) + '\n',
        encoding='utf-8', newline='\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('faces', nargs='*', help=f'any of {", ".join(LATEST)} (default: all four)')
    ap.add_argument('--version', default=None, help="the fonts' version (default: build2.VERSION)")
    ap.add_argument('--output', type=Path, default=ROOT / 'build' / 'candidate' / 'fonts')
    ap.add_argument('--traces', type=Path, help='another trace folder for the one face named (a round under study)')
    args = ap.parse_args()
    faces = args.faces or list(LATEST)
    if set(faces) - set(LATEST):
        ap.error(f'unknown face: {", ".join(sorted(set(faces) - set(LATEST)))}')
    args.output.mkdir(parents=True, exist_ok=True)
    if args.traces and len(faces) != 1:
        ap.error('--traces needs exactly one face')
    if len(faces) > 1:
        # build2 reads TRACED when it is imported, so each face is built in a fresh interpreter
        for face in faces:
            subprocess.run([sys.executable, __file__, face, *(['--version', args.version] if args.version else []), '--output', str(args.output)], check=True)
        return
    traces = args.traces.resolve() if args.traces else ROOT / LATEST[faces[0]]
    os.environ['OUT'] = str(args.output.resolve())
    os.environ['TRACED'] = str(traces)
    build(faces[0], traces, args.version)


if __name__ == '__main__':
    main()
