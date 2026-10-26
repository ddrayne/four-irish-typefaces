import glob, os, sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
FONTDIR = os.path.abspath(os.environ.get('FONTDIR', os.path.join(ROOT, 'fonts')))


def files(ext):
    """Every font file with this extension under FONTDIR (fonts/ by format, or a flat build)."""
    return sorted(p for p in glob.glob(os.path.join(FONTDIR, '**', f'*.{ext}'), recursive=True)
                  if os.sep + 'variable' + os.sep not in p)


# Code points only the release builds, which the research studies' fonts do not have: the fifth pass's combining
# dot below (build2.Font2.MARK_STACKS, set by scripts/build_candidate.py; research/*/judged-edits.json, fifth_pass).
RELEASE_ONLY = {0x323}


def study_coverage(release):
    """The code points of a release font (a TTFont) that a study font of the face keeps: all but RELEASE_ONLY."""
    return set(release.getBestCmap()) - RELEASE_ONLY


def static(ps, style, ext='otf'):
    name = f'{ps}-{style.replace(" ", "")}.{ext}'
    hits = [p for p in files(ext) if os.path.basename(p) == name]
    assert hits, f'{name} not found under {FONTDIR}'
    return hits[0]


@pytest.fixture(scope='session')
def config():
    from build2 import FONTS, FAMILY_STYLES, VERSION
    return FONTS, FAMILY_STYLES, VERSION
