"""Validation evidence for a release, into docs/validation/:

  * the OpenType Sanitizer (as in Chrome and Firefox) on every font file;
  * Font Bakery's universal profile per family, family checks included;
  * every glyph printed on the flyer against the scan (flyer-glyph-audit.md);
  * the traced outlines over the scan, and the large-sample weight check.

usage: python scripts/validate.py [--no-fontbakery]
"""
import glob, os, subprocess, sys
import numpy as np
from PIL import Image
import paths
from build2 import FONTS as CFG, VERSION

FONTDIR = os.path.join(paths.ROOT, 'fonts')
DOCS = os.path.join(paths.ROOT, 'docs', 'validation')
FAMS = {'kilfane': 'Kilfane', 'tuam': 'Tuam Uncial', 'carrick': 'Carrick', 'ceili': 'Céilí'}
NOTE = {('h', 'ceili'): 'right leg replaced from n (the printed leg is broken)',
        ('e', 'ceili'): 'hairlines restored at the top of the eye and in the crossbar (grey on the scan, so not counted as print)',
        ('e.alt1', 'ceili'): 'hairline restored in the crossbar',
        ('b', 'ceili'): 'hairline restored where the bowl joins the stem',
        ('semicolon', None): 'the font builds ; from this comma and dot, spaced like its colon, not the sheet’s compact pair'}


def ots_all():
    import ots
    files = sorted(p for p in glob.glob(os.path.join(FONTDIR, '**', '*'), recursive=True) if p.endswith(('.otf', '.ttf', '.woff', '.woff2')))
    bad = [os.path.relpath(p, paths.ROOT) for p in files if ots.sanitize(p, os.devnull, capture_output=True).returncode != 0]
    print(f'OTS: {len(files)} files, failures: {bad or "none"}')
    return not bad


def fontbakery():
    fb = os.path.join(os.path.dirname(sys.executable), 'fontbakery')
    ok = True
    for key, cfg in CFG.items():
        ps = cfg['ps']; ttfs = sorted(glob.glob(os.path.join(FONTDIR, 'ttf', f'{ps}-*.ttf')))
        md = os.path.join(DOCS, f'fontbakery-{ps}.md'); log = os.path.join(paths.BUILD, f'fontbakery-{ps}.log')
        with open(log, 'w') as f:
            subprocess.run([fb, 'check-universal', '-x', 'fontdata_namecheck', '-l', 'WARN', '--succinct', '--ghmarkdown', md, *ttfs],
                           stdout=f, stderr=subprocess.STDOUT, timeout=1800)
        summary = next((l.strip() for l in open(log) if 'ERROR:' in l and 'FATAL:' in l), '?')
        print(f'Font Bakery {ps}: {summary}')
        ok &= ' FAIL: 0 ' in summary + ' ' and ' ERROR: 0 ' in ' ' + summary
    return ok


def flyer_audit():
    import audit_glyph
    out = [f'# Every flyer glyph against the scan (version {VERSION})', '',
           'Each glyph printed on the 1978 flyer, registered on the scan (best shift, to an eighth of a pixel) and',
           'compared with the print at 8× resolution. **Overlap** is intersection over union of the filled shapes',
           '(1.000 is identical). **Miss** and **extra** are how far, in flyer pixels, the deepest spot of print',
           'the font lacks, and of font the print lacks, reaches. At this scan (about 97 dpi) a quarter of a pixel',
           'is about 0.07 mm on the flyer. Letters are listed from the lowest overlap up. The regular of each face',
           'is the one compared: the italics and bolds were drawn from it and have no print to match.', '']
    total = []
    for key in ('ceili', 'carrick', 'kilfane', 'tuam'):
        rows, _ = audit_glyph.audit(key, fontpath=os.path.join(FONTDIR, 'otf', f'{CFG[key]["ps"]}-Regular.otf'))
        rows.sort(key=lambda r: r[1])
        v = [r[1] for r in rows if r[0] != 'semicolon']; total += v
        out += [f'## {FAMS[key]}', '', f'{len(v)} glyphs, mean overlap {np.mean(v):.3f}' +
                (' (the semicolon is listed but not counted)' if len(v) < len(rows) else '') + '.', '',
                '| Glyph | Overlap | Miss (px) | Extra (px) | Area vs print | Note |', '|---|---|---|---|---|---|']
        for n, iou, miss, extra, area, dx, dy in rows:
            note = NOTE.get((n, key), NOTE.get((n, None), ''))
            out.append(f'| `{n}` | {iou:.3f} | {miss:.2f} | {extra:.2f} | {area:+.1f}% | {note} |')
        out.append('')
    open(os.path.join(DOCS, 'flyer-glyph-audit.md'), 'w').write('\n'.join(out))
    print(f'flyer audit: {len(total)} glyphs, mean overlap {np.mean(total):.3f}')


def images():
    """The overlays, as 64-colour PNGs (they are scans with outlines; nothing is lost that matters)."""
    here = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([sys.executable, os.path.join(here, 'proof_trace.py'), 'kilfane', 'tuam', 'carrick', 'ceili'], check=True, capture_output=True)
    subprocess.run([sys.executable, os.path.join(here, 'weightcheck.py')], check=True, capture_output=True,
                   env=dict(os.environ, OUT=os.path.join(FONTDIR, 'otf')))
    pairs = [(f'trace_{k}.png', f'traced-outlines-over-scan-{k}.png') for k in FAMS] + [('weightcheck.png', 'large-sample-overlay.png')]
    for a, b in pairs:
        im = Image.open(os.path.join(paths.VIEW, a)).convert('RGB')
        im.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(os.path.join(DOCS, b), optimize=True)


if __name__ == '__main__':
    os.makedirs(DOCS, exist_ok=True)
    ok = ots_all()
    if '--no-fontbakery' not in sys.argv:
        ok &= fontbakery()
    flyer_audit()
    images()
    sys.exit(0 if ok else 1)
