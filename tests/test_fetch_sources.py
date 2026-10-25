import hashlib
import io
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from fetch_sources import fetch_asset, select_assets


def asset(content=b'original'):
    return dict(source_id='N514', path='original-specimens/example.jpg',
                format='jpg', url='https://example.org/original.jpg',
                bytes=len(content), sha256=hashlib.sha256(content).hexdigest())


def test_valid_download_and_cached_verification(tmp_path):
    row = asset()
    assert fetch_asset(row, tmp_path, opener=lambda *a, **kw: io.BytesIO(b'original')) == 'downloaded'
    assert fetch_asset(row, tmp_path, verify_only=True) == 'verified'


def test_changed_download_is_rejected_without_installing(tmp_path):
    row = asset()
    with pytest.raises(ValueError, match='identity'):
        fetch_asset(row, tmp_path, opener=lambda *a, **kw: io.BytesIO(b'modified'))
    assert not (tmp_path / row['path']).exists()
    assert not list(tmp_path.rglob('*.part'))


def test_bad_existing_file_is_preserved(tmp_path):
    row = asset()
    path = tmp_path / row['path']
    path.parent.mkdir()
    path.write_bytes(b'other')
    with pytest.raises(ValueError, match='identity'):
        fetch_asset(row, tmp_path)
    assert path.read_bytes() == b'other'


def test_path_escape_and_missing_cache_are_rejected(tmp_path):
    with pytest.raises(ValueError, match='path'):
        fetch_asset(dict(asset(), path='../outside.jpg'), tmp_path)
    with pytest.raises(FileNotFoundError):
        fetch_asset(asset(), tmp_path, verify_only=True)


def test_modern_revivals_excluded_and_selection_explicit():
    rows = [asset(), dict(asset(), source_id='JPDF', role='context_only_excluded_from_reconstruction')]
    assert select_assets(rows, [], []) == rows[:1]
    assert select_assets(rows, ['N514'], ['jpg']) == rows[:1]
    with pytest.raises(ValueError, match='No matching'):
        select_assets(rows, ['JPDF'], [])
