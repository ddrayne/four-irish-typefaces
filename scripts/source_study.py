"""Original-specimen measurement helpers. No font mutation and no image enhancement."""
import numpy as np
from scipy import ndimage as ndi


def line_regions(gray, box, names, threshold=130, min_area=12):
    """Group connected ink by overlapping x spans, preserving detached dots and holes.

    Never silently guess a split or drop a glyph. Touching letters require explicit
    source regions rather than a changed expected count.
    """
    x0, y0, x1, y1 = box
    mask = np.asarray(gray)[y0:y1, x0:x1] < threshold
    labels, _ = ndi.label(mask, structure=np.ones((3, 3)))
    groups = []
    for i, sl in enumerate(ndi.find_objects(labels), 1):
        if sl is None:
            continue
        ys, xs = np.nonzero(labels[sl] == i)
        if len(xs) < min_area:
            continue
        xs = xs + sl[1].start + x0
        ys = ys + sl[0].start + y0
        groups.append(dict(left=int(xs.min()), right=int(xs.max())+1, xs=xs, ys=ys, labels=[i]))
    merged = groups
    changed = True
    while changed:
        changed = False
        for i, m in enumerate(merged):
            for j in range(i+1, len(merged)):
                g = merged[j]
                overlap = min(m['right'], g['right']) - max(m['left'], g['left'])
                width = min(m['right']-m['left'], g['right']-g['left'])
                area_small, area_big = sorted((len(m['xs']), len(g['xs'])))
                if overlap >= .8*width or (overlap >= .5*width and area_small < .35*area_big):
                    m['left'] = min(m['left'], g['left'])
                    m['right'] = max(m['right'], g['right'])
                    m['xs'] = np.concatenate((m['xs'], g['xs']))
                    m['ys'] = np.concatenate((m['ys'], g['ys']))
                    m['labels'].extend(g['labels'])
                    merged.pop(j)
                    changed = True
                    break
            if changed:
                break
    merged.sort(key=lambda g: g['left'])
    if len(merged) != len(names):
        raise ValueError(f'expected {len(names)} glyphs; found {len(merged)}: '
                         f'{[(g["left"], g["right"], len(g["xs"])) for g in merged]}')
    return [dict(name=n, box=[g['left'], int(g['ys'].min()), g['right'], int(g['ys'].max())+1],
                 ink_pixels=len(g['xs']), labels=g['labels'], row_box=list(box)) for n, g in zip(names, merged)]


def normalise_points(points, scale, source_origin, target_origin):
    """Uniform source->legacy coordinate transform; no per-glyph anisotropic fit."""
    if scale <= 0 or not np.isfinite(scale):
        raise ValueError('scale must be positive and finite')
    return (np.asarray(points, float) - np.asarray(source_origin))/scale + np.asarray(target_origin)


def register_translation(rendered, target):
    """Maximise intersection at fixed scale using the full translation domain.

    Since both ink areas are fixed, maximum intersection also maximises IoU.
    A clipped result is rejected instead of being awarded an inflated score.
    """
    from scipy.signal import fftconvolve
    correlation=fftconvolve(target.astype(float),rendered[::-1,::-1].astype(float),mode='full')
    y,x=np.unravel_index(np.argmax(correlation),correlation.shape)
    dy=int(y-rendered.shape[0]+1);dx=int(x-rendered.shape[1]+1)
    moved=ndi.shift(rendered,(dy,dx),order=0,mode='constant',cval=False)
    if moved.sum()!=rendered.sum():
        raise ValueError('registration clipped ink; enlarge the canvas')
    return moved,(dx,dy)
