import numpy as np
from source_study import raster_coverage

def test_pixel_area_does_not_grow_with_inclusive_polygon_edges():
    square=[[(2.5,2.5),(12.5,2.5),(12.5,12.5),(2.5,12.5)]]
    a=raster_coverage(square,(20,20),lambda p:p,samples=8)
    assert abs(a.sum()-100)<.01
    assert np.all(a[3:13,3:13]==1)
    assert not a[:3].any()

def test_subpixel_coverage_preserves_counter_and_fractional_edges():
    outer=[(2,2),(12,2),(12,12),(2,12)]
    hole=[(5,5),(9,5),(9,9),(5,9)]
    a=raster_coverage([outer,hole],(20,20),lambda p:p,samples=8)
    assert abs(a.sum()-84)<.01
    assert a[2,2]==.25
    assert a[6,6]==0
    assert a[3,3]==1
