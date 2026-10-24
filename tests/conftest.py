import glob, os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
FONTDIR = os.path.abspath(os.environ.get('FONTDIR', os.path.join(ROOT, 'fonts')))


def files(ext):
    """Every font file with this extension under FONTDIR (fonts/ by format, or a flat build)."""
    return sorted(p for p in glob.glob(os.path.join(FONTDIR, '**', f'*.{ext}'), recursive=True)
                  if os.sep + 'variable' + os.sep not in p)


def static(ps, style, ext='otf'):
    name = f'{ps}-{style.replace(" ", "")}.{ext}'
    hits = [p for p in files(ext) if os.path.basename(p) == name]
    assert hits, f'{name} not found under {FONTDIR}'
    return hits[0]


@pytest.fixture(scope='session')
def config():
    from build2 import FONTS, FAMILY_STYLES, VERSION
    return FONTS, FAMILY_STYLES, VERSION
