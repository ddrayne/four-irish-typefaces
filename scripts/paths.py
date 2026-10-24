"""Where everything lives, relative to the repository root. Environment variables override."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _p(*parts):
    return os.path.join(ROOT, *parts)


SCAN = _p('sources', 'flyer.jpg')                                  # the 1978 flyer, as scanned
TRACED = os.environ.get('TRACED', _p('sources', 'traced'))         # traced outlines, one JSON per face
SITE_SRC = _p('site')                                              # the test page's sources
BUILD = os.path.abspath(os.environ.get('BUILD', _p('build')))     # everything generated (not committed)
FONTS = os.path.abspath(os.environ.get('OUT', os.path.join(BUILD, 'fonts')))      # flat build output
SPECIMEN = os.path.abspath(os.environ.get('SPECIMEN', os.path.join(BUILD, 'specimen')))
PACKAGE = os.path.join(BUILD, 'package', 'four-irish-typefaces')   # the release folder that is zipped
DIST = os.path.join(BUILD, 'dist')                                 # the release ZIPs
AUDIT = os.path.join(BUILD, 'audit')
VIEW = os.path.join(BUILD, 'view')
CACHE = os.path.join(BUILD, 'cache')
for d in (BUILD, AUDIT, VIEW, CACHE):
    os.makedirs(d, exist_ok=True)
