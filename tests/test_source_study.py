import importlib
import importlib.util
import numpy as np
import pytest


def module():
    assert importlib.util.find_spec('source_study'), 'source-study helpers are missing'
    return importlib.import_module('source_study')


def specimen():
    a = np.full((40, 80), 255, np.uint8)
    a[12:32, 5:22] = 0
    a[17:27, 10:17] = 255  # counter
    a[15:32, 35:42] = 0
    a[5:10, 35:42] = 0  # detached dot belongs to i
    a[12:32, 55:73] = 0
    a[1, 1] = 0  # isolated dirt
    return a


def test_regions_keep_counter_and_detached_dot():
    regions = module().line_regions(specimen(), (0, 0, 80, 40), ['o', 'i', 'n'])
    assert [r['name'] for r in regions] == ['o', 'i', 'n']
    assert regions[0]['box'] == [5, 12, 22, 32]
    assert regions[1]['box'] == [35, 5, 42, 32]
    assert regions[0]['ink_pixels'] == 17 * 20 - 7 * 10
    assert regions[1]['ink_pixels'] == 7 * (17 + 5)


def test_count_mismatch_fails_instead_of_mislabeling():
    with pytest.raises(ValueError, match='expected 4.*found 3'):
        module().line_regions(specimen(), (0, 0, 80, 40), ['o', 'i', 'n', 'x'])


def test_uniform_transform_preserves_proportions_and_origin():
    points = np.array([[10., 20.], [30., 20.], [10., 60.]])
    got = module().normalise_points(points, 4., (10., 60.), (3., 9.))
    assert np.allclose(got, [[3., -1.], [8., -1.], [3., 9.]])
    assert np.linalg.norm(got[1]-got[0])/np.linalg.norm(got[2]-got[0]) == .5


def test_overhanging_serifs_do_not_merge_adjacent_letters():
    a = np.full((50, 60), 255, np.uint8)
    a[10:30, 5:25] = 0
    a[32:48, 22:45] = 0
    rs = module().line_regions(a, (0, 0, 60, 50), ['A', 'B'])
    assert [r['name'] for r in rs] == ['A', 'B']


def test_registration_finds_large_translation_without_clipping():
    a=np.zeros((100,100),bool);a[20:60,20:50]=True;a[25:45,25:40]=False
    b=np.zeros_like(a);b[8:48,35:65]=True;b[13:33,40:55]=False
    moved,offset=module().register_translation(a,b)
    assert offset==(15,-12)
    assert np.array_equal(moved,b)
