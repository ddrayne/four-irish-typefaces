"""Original-specimen measurement helpers. No font mutation and no image enhancement."""
import numpy as np
from scipy import ndimage as ndi


def component_field(gray, region, pad=5):
    """Grayscale coverage for named components, excluding neighboring component ink.

    Labels are calculated at the recorded threshold (130 by default). Background
    pixels around the selected components retain antialiasing and counters.
    """
    rx0, ry0, rx1, ry1 = region['row_box']
    labels, _ = ndi.label(np.asarray(gray)[ry0:ry1, rx0:rx1] < region.get('threshold', 130),
                          structure=np.ones((3, 3)))
    wanted = region['labels']
    if not wanted or 0 in wanted or any(not np.any(labels == label) for label in wanted):
        raise ValueError('source component labels no longer match the image')
    own = np.isin(labels, wanted)
    permitted = ndi.binary_dilation(own, iterations=3) & ((labels == 0) | own)
    x0, y0, x1, y1 = region['box']
    x0, y0 = max(rx0, x0-pad), max(ry0, y0-pad)
    x1, y1 = min(rx1, x1+pad), min(ry1, y1+pad)
    sl = np.s_[y0-ry0:y1-ry0, x0-rx0:x1-rx0]
    a = np.asarray(gray)[y0:y1, x0:x1].astype(float)
    core, allow = own[sl], permitted[sl]
    background = labels[sl] == 0
    if not core.any() or not background.any():
        raise ValueError('component region needs both ink and paper')
    paper = float(np.percentile(a[background], 80))
    ink = float(np.percentile(a[core], 30))
    field = np.where(allow, np.clip((paper-a)/max(paper-ink, 1), 0, 1), 0.)
    return field, (x0, y0), paper, ink


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
