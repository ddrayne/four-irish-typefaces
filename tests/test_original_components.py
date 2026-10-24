import numpy as np
import source_study


def test_isolation_excludes_adjacent_component_but_preserves_counter():
    image=np.full((30,40),240,np.uint8)
    image[5:25,5:20]=20
    image[10:20,10:15]=240
    image[5:25,22:28]=20
    region={'row_box':[0,0,40,30],'box':[5,5,20,25],'labels':[1]}
    assert hasattr(source_study,'component_field'), 'exclusive component extraction is missing'
    field,origin,_,_=source_study.component_field(image,region,pad=8)
    assert field[15-origin[1],12-origin[0]]==0
    assert field[15-origin[1],7-origin[0]]>.9
    assert not field[:,22-origin[0]:].any(), 'neighbor ink leaked into isolated mark'


def test_component_field_rejects_unmatched_labels():
    image=np.full((20,20),255,np.uint8)
    region={'row_box':[0,0,20,20],'box':[3,3,10,10],'labels':[1]}
    assert hasattr(source_study,'component_field'), 'exclusive component extraction is missing'
    import pytest
    with pytest.raises(ValueError,match='component'):
        source_study.component_field(image,region)
