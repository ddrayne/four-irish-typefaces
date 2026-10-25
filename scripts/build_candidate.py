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
LATEST = {'kilfane': 'research/kilfane-judgement/traces', 'carrick': 'research/round-06/carrick/traces',
          'tuam': 'research/round-03/tuam/traces', 'ceili': 'research/round-04/ceili/traces'}


def build(face, traces, version):
    import build2, build_original_study as study
    build2.VERSION = version
    cfg = build2.FONTS[face]
    Study, evidence, piece_data = study.study_class(face, traces)
    retained = any(g['status'] == 'retained' for g in evidence['glyphs'])

    class Candidate(Study):
        # The sheets are drawings, not a photocopy: their narrow open joins are drawn, and the bold
        # keeps them. The sloped styles add only a hair of weight, so they keep every gap there is.
        SLIVER, SLIVER_SLOPED = 0.05, 0.01
        FINISH = True
        # a single stem's square foot (Kilfane's F, P, V, 4 and 7) sits on the baseline, not 8 units below
        # it. Only Kilfane's feet have been reviewed against its sheets; elsewhere the rule would also
        # move letters (Carrick's s; Tuam's i, s, u, 9; Céilí's h, n, z, £) that need their own review.
        FLAT_FOOT_WIDENING = 1.2 if face == 'kilfane' else None
        # each original-source glyph is refitted at its own source's resolution (its calibration
        # scale is source pixels per trace unit); letters kept from the flyer were designer-fitted already
        REFIT_PX = {g['name']: 1.0 / g['scale'] for g in evidence['glyphs']
                    if g['status'] == 'candidate' and g.get('scale')}

        def build(self, flavour):
            f = build2.Font2.build(self, flavour)        # the release's names, not the study's
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
    ap.add_argument('--version', default='3.000')
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
            subprocess.run([sys.executable, __file__, face, '--version', args.version, '--output', str(args.output)], check=True)
        return
    traces = args.traces.resolve() if args.traces else ROOT / LATEST[faces[0]]
    os.environ['OUT'] = str(args.output.resolve())
    os.environ['TRACED'] = str(traces)
    build(faces[0], traces, args.version)


if __name__ == '__main__':
    main()
