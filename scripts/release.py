"""Put a build in place: fonts/ by format from build/fonts, the stylesheet, and the specimen page.

usage: python scripts/release.py
"""
import glob, os, shutil, subprocess, sys
import paths

FORMATS = ('otf', 'ttf', 'woff', 'woff2')


def main():
    built = sorted(glob.glob(os.path.join(paths.FONTS, '*.otf')))
    if not built:
        sys.exit(f'no fonts in {paths.FONTS}: run `make fonts` first')
    for fmt in FORMATS:
        d = os.path.join(paths.ROOT, 'fonts', fmt)
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        for f in sorted(glob.glob(os.path.join(paths.FONTS, f'*.{fmt}'))):
            shutil.copy(f, d)
    var = os.path.join(paths.FONTS, 'variable')
    if os.path.isdir(var):
        d = os.path.join(paths.ROOT, 'fonts', 'variable')
        shutil.rmtree(d, ignore_errors=True); shutil.copytree(var, d)
    py = sys.executable; here = os.path.dirname(os.path.abspath(__file__))
    subprocess.run([py, os.path.join(here, 'make_css.py'), os.path.join(paths.ROOT, 'css', 'four-irish-typefaces.css')], check=True)
    subprocess.run([py, os.path.join(here, 'webpage.py'), os.path.join(paths.ROOT, 'index.html')], check=True)
    n = sum(len(os.listdir(os.path.join(paths.ROOT, 'fonts', f))) for f in FORMATS)
    print(f'released {n} font files, css/four-irish-typefaces.css and index.html')


if __name__ == '__main__':
    main()
