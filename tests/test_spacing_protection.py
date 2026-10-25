from types import SimpleNamespace
import importlib.util
import pathops


def rectangle(x0,y0,x1,y1):
    p=pathops.Path();p.moveTo(x0,y0);p.lineTo(x1,y0);p.lineTo(x1,y1);p.lineTo(x0,y1);p.close();return p


def test_full_height_protection_opens_descender_collision_and_keeps_safe_pair():
    assert importlib.util.find_spec('study_spacing'), 'full-height collision protection is missing'
    from study_spacing import protect_kerning
    font=SimpleNamespace(final={'q':rectangle(0,-100,110,500),'j':rectangle(-25,-100,25,500),'n':rectangle(0,0,70,500)},
        adv={'q':100,'j':65,'n':100},mark_glyphs={},kern_pairs={},kern_exc={},left_group={},right_group={})
    protect_kerning(font)
    assert font.kern_exc[('q','j')]>=43
    assert ('n','n') not in font.kern_exc


def test_collision_protection_respects_inherited_class_kerning():
    assert importlib.util.find_spec('study_spacing'), 'full-height collision protection is missing'
    from study_spacing import protect_kerning
    p=rectangle(0,0,80,500)
    font=SimpleNamespace(final={'a':p,'aacute':p,'b':p},adv={'a':100,'aacute':100,'b':100},mark_glyphs={},
        kern_pairs={('a','b'):-30},kern_exc={},left_group={'a':['a','aacute']},right_group={'b':['b']})
    protect_kerning(font)
    assert font.kern_exc[('aacute','b')]>-30
    assert 100+font.kern_exc[('aacute','b')]-80>=8
