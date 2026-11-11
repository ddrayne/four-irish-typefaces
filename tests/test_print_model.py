"""The print model's measuring code on synthetic images (no archive files needed)."""
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
import print_model as M


def letter():
    """An 'n' of two 100-unit stems, 500 high, joined by a 60-unit bar: thick and thin strokes, a counter."""
    res = M.RES
    m = np.zeros((int(800 * res), int(800 * res)), bool)
    def box(x0, y0, x1, y1):
        m[int(y0 * res):int(y1 * res), int(x0 * res):int(x1 * res)] = True
    box(150, 150, 250, 650); box(450, 150, 550, 650); box(150, 150, 550, 210)
    return M.Ref.from_mask(m, -150.0, -650.0)


@pytest.fixture(scope='module')
def ref():
    return letter()


def synthetic(ref, d, sigma, s=0.12, noise=0.03, seed=0, paper=0.05, ink=0.92, e=0.0, thin=None):
    rng = np.random.default_rng(seed)
    img = M.render(ref, (90, 80), s, 0.012, 14.3, 76.6, d, sigma, e=e, thin=thin)
    return paper + (ink - paper) * img + rng.normal(0, noise, img.shape)


@pytest.mark.parametrize('d,sigma', [(0.9, 1.0), (-0.6, 0.7), (0.0, 1.5)])
def test_fit_recovers_gain_and_scale(ref, d, sigma):
    out, _ = M.measure(synthetic(ref, d, sigma), (0, 0), ref, 'ceili', (0.123, 15.0, 76.0), thin=False)
    f = out['single']
    assert abs(f['d'] - d) < 0.06
    assert abs(f['s'] / 0.12 - 1) < 0.003
    assert abs(f['sigma'] - sigma) < 0.15
    assert abs(out['local_paper'] - 0.05) < 0.02 and abs(out['local_ink'] - 0.92) < 0.03


def test_stem_profiles_recover_gain_and_complement(ref):
    d = 0.8
    out, _ = M.measure(synthetic(ref, d, 1.0), (0, 0), ref, 'ceili', (0.12, 14.0, 77.0), thin=False)
    stems = out['stems']
    assert len(stems) == 2 and all(abs(t['ref_width'] - 100) < 1 for t in stems)
    for t in stems:
        assert abs(t['L50']['half_gain_px'] - d) < 0.08
        assert t['L40']['width_px'] > t['L50']['width_px'] > t['L60']['width_px']
    a, b = stems
    s = out['single']['s']
    # same-facing edges keep their distance; the counter loses what the stems gain
    assert abs((b['L50']['left'] - a['L50']['left']) - 300) * s < 0.1
    gap = (b['L50']['left'] - a['L50']['right']) * s
    assert abs(gap - (200 * s - 2 * d)) < 0.15


def test_thin_strokes_get_their_own_gain(ref):
    thin = (50, 90)
    img = synthetic(ref, 0.8, 1.0, e=-0.7, thin=thin)
    f = M.fit_gain(np.clip((img - 0.05) / 0.87, 0, 1), ref, (0.12, 0.0, 14.0, 77.0), thin=thin)
    assert abs(f['d'] - 0.8) < 0.12 and abs(f['e'] + 0.7) < 0.2


def test_a_thresholded_copy_shifts_the_edge_by_its_threshold(ref):
    """A copier that thresholds a blurred original at 35% fattens a straight edge by 0.385 sigma
    (the 35% point of a Gaussian edge); the model reads that as gain."""
    from scipy import ndimage as ndi
    soft = M.render(ref, (90, 80), 0.12, 0.0, 14.3, 76.6, 0.0, 1.2)
    copy = ndi.gaussian_filter((soft > 0.35).astype(float), 0.8)
    f = M.fit_gain(copy, ref, (0.12, 0.0, 14.0, 77.0))
    assert abs(f['d'] - 0.385 * 1.2) < 0.1


def test_thickness_and_stems(ref):
    T = ref.thickness()
    i, j = int(400 * M.RES), int(200 * M.RES)            # middle of the left stem
    assert abs(T[i, j] - 100) <= 4
    i, j = int(180 * M.RES), int(350 * M.RES)            # middle of the bar
    assert abs(T[i, j] - 60) <= 4
    st = M.find_stems(ref.mask)
    assert [round(t['width']) for t in st] == [100, 100]


def test_multi_size_regression_separates_gain_from_weight():
    s = np.array([0.08, 0.11, 0.15, 0.2]); g, tau = 0.7, -6.0
    d = g + tau * s
    fit = M.line_fit(s, d, np.full(4, 0.05))
    assert abs(fit['intercept'] - g) < 1e-9 and abs(fit['slope'] - tau) < 1e-9
    assert fit['intercept_se'] > 0.05
