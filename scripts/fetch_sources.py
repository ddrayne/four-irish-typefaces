"""Retrieve exact registered originals into a local, ignored research cache.

Standard library only. Never updates source identities or publication rights.
Modern revival references are deliberately excluded from reconstruction inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def select_assets(rows, sources, formats):
    selected = [r for r in rows
                if r.get('role') != 'context_only_excluded_from_reconstruction'
                and (not sources or r['source_id'] in sources)
                and (not formats or r['format'] in formats)]
    if not selected:
        raise ValueError('No matching original sources; revival references are excluded.')
    missing = set(sources) - {r['source_id'] for r in selected}
    if missing:
        raise ValueError('No matching original assets for: ' + ', '.join(sorted(missing)))
    return selected


def check_identity(path, row):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if path.stat().st_size != row['bytes'] or digest != row['sha256']:
        raise ValueError(f"Source identity mismatch: {row['path']}; preserve and investigate, do not silently replace.")


def fetch_asset(row, output, verify_only=False, opener=urlopen):
    output = Path(output).resolve()
    relative = Path(row['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unsafe source path')
    target = (output / relative).resolve()
    if not target.is_relative_to(output) or target == output:
        raise ValueError('Source path escapes output directory')
    if target.exists():
        check_identity(target, row)
        return 'verified'
    if verify_only:
        raise FileNotFoundError(f"Missing source: {row['path']}")
    if not row['url'].startswith('https://'):
        raise ValueError('Source URL must use HTTPS')
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        request = Request(row['url'], headers={'User-Agent': 'FourIrishTypefaces-Research/1.0'})
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.part', delete=False) as stream:
            temporary = Path(stream.name)
            size = 0
            with opener(request, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > row['bytes']:
                        raise ValueError(f"Source identity mismatch (oversized response): {row['path']}")
                    stream.write(chunk)
        check_identity(temporary, row)
        # A concurrent downloader may have completed the same asset meanwhile.
        if target.exists():
            check_identity(target, row)
            return 'verified'
        temporary.replace(target)
        return 'downloaded'
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/research')
    parser.add_argument('--source', action='append', default=[], help='Source ID; repeat for multiple IDs')
    parser.add_argument('--format', action='append', choices=['jpg', 'jp2', 'pdf'], default=[])
    parser.add_argument('--list', action='store_true', help='List selection without downloading')
    parser.add_argument('--verify-only', action='store_true', help='Check cached files without network access')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'research/downloads.json').read_text(encoding='utf-8'))
    try:
        rows = select_assets(manifest['assets'], args.source, args.format)
    except ValueError as error:
        parser.error(str(error))
    print(f"{len(rows)} assets; {sum(r['bytes'] for r in rows):,} bytes. Source rights remain with their owners.")
    failed = 0
    for row in rows:
        if args.list:
            print(f"{row['source_id']:5} {row['bytes']:>10} {row['path']}")
            continue
        try:
            result = fetch_asset(row, args.output, args.verify_only)
            print(f"{result}: {row['path']}")
        except (OSError, ValueError) as error:
            failed += 1
            print(f"FAILED {row['source_id']}: {error}")
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
