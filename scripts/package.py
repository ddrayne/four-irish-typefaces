"""The release ZIPs, from the committed tree.

  four-irish-typefaces-vX.zip        everything tracked in the repository (fonts, docs, sources, scripts)
  four-irish-typefaces-fonts-vX.zip  just what a user installs: fonts, stylesheet, specimen page, licence

The full ZIP is also unpacked to build/package/four-irish-typefaces, where the test page build
finds the fonts and specimen. Run after committing: files that git does not track are left out.

usage: python scripts/package.py
"""
import os, shutil, subprocess, zipfile
import paths
from build2 import VERSION

ROOT_NAME = 'four-irish-typefaces'
FONTS_ONLY = ('fonts/', 'css/', 'index.html', 'README.md', 'OFL.txt', 'FONTLOG.txt')


def tracked():
    out = subprocess.run(['git', 'ls-files', '-z'], cwd=paths.ROOT, check=True, capture_output=True).stdout
    return sorted(f for f in out.decode().split('\0') if f)


def write_zip(path, files):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in files:
            z.write(os.path.join(paths.ROOT, f), f'{ROOT_NAME}/{f}')
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
    return os.path.getsize(path)


def main():
    files = tracked()
    os.makedirs(paths.DIST, exist_ok=True)
    full = os.path.join(paths.DIST, f'{ROOT_NAME}-v{VERSION}.zip')
    fonts = os.path.join(paths.DIST, f'{ROOT_NAME}-fonts-v{VERSION}.zip')
    a = write_zip(full, files)
    b = write_zip(fonts, [f for f in files if f.startswith(FONTS_ONLY)])
    shutil.rmtree(os.path.dirname(paths.PACKAGE), ignore_errors=True)
    with zipfile.ZipFile(full) as z:
        z.extractall(os.path.dirname(paths.PACKAGE))
    print(f'{full} {a / 1e6:.2f} MB, {len(files)} files')
    print(f'{fonts} {b / 1e6:.2f} MB')
    if a > 8 * 1024 * 1024:
        print('warning: the full ZIP is over 8 MiB, the app publisher scans files up to that size')


if __name__ == '__main__':
    main()
