import paths
import os
import sys, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage.segmentation import watershed
from specs import SPECS
GRAY = np.asarray(Image.open(paths.SCAN).convert('L')).astype(float)

def overlap(a0,a1,b0,b1): return max(0, min(a1,b1)-max(a0,b0))

def label_block(box, T):
    x0,y0,x1,y1 = box
    lab = np.zeros(GRAY.shape, int)
    l, n = ndi.label(GRAY[y0:y1, x0:x1] < T, structure=np.ones((3,3)))
    lab[y0:y1, x0:x1] = l
    return lab, n

def comp_info(lab, cid):
    ys, xs = np.nonzero(lab == cid)
    return dict(id=cid, x0=xs.min(), x1=xs.max()+1, y0=ys.min(), y1=ys.max()+1, area=len(xs), pix=(ys, xs))

def split_component(c, nparts, cuts=None):
    """Split a fused component into nparts using darker cores as watershed seeds,
    or at explicit cut columns when given."""
    ys, xs = c['pix']; y0,x0 = ys.min(), xs.min()
    if cuts:
        edges = [-1e9] + list(cuts) + [1e9]
        return [(ys[(xs >= a) & (xs < b)], xs[(xs >= a) & (xs < b)]) for a, b in zip(edges, edges[1:])], None
    mask = np.zeros((ys.max()-y0+1, xs.max()-x0+1), bool); mask[ys-y0, xs-x0] = True
    g = GRAY[y0:y0+mask.shape[0], x0:x0+mask.shape[1]]
    for T in range(150, 40, -10):
        l, n = ndi.label((g < T) & mask, structure=np.ones((3,3)))
        sizes = ndi.sum(np.ones_like(l), l, range(1, n+1))
        big = [i+1 for i in np.argsort(sizes)[::-1][:nparts] if sizes[i] >= max(12, 0.06*mask.sum())]
        if len(big) == nparts:
            markers = np.zeros_like(l)
            for k, i in enumerate(sorted(big, key=lambda i: np.nonzero(l==i)[1].mean())): markers[l==i] = k+1
            ws = watershed(g, markers, mask=mask)
            parts = []
            for k in range(1, nparts+1):
                py, px = np.nonzero(ws == k)
                parts.append((py+y0, px+x0))
            return parts, T
    raise RuntimeError(f'could not split component at x={c["x0"]}')

def make_cluster(pixlist):
    ys = np.concatenate([p[0] for p in pixlist]); xs = np.concatenate([p[1] for p in pixlist])
    return dict(pix=(ys, xs), x0=xs.min(), x1=xs.max()+1, y0=ys.min(), y1=ys.max()+1, area=len(xs))

def segment(font, verbose=True):
    sp = SPECS[font]
    lab, n = label_block(sp['box'], sp['T'])
    comps = [comp_info(lab, i) for i in range(1, n+1)]
    lines = []
    for li, ((ya, yb), names) in enumerate(sp['lines']):
        cs = [c for c in comps if ya <= (c['y0']+c['y1'])/2 < yb]
        force = {k: v for k, v in sp.get('force', {}).items() if k in names}
        groups, rest = {}, []
        for c in cs:
            fx = [k for k, (a, b) in force.items() if a <= (c['x0']+c['x1'])/2 < b]
            if fx: groups.setdefault(fx[0], []).append(c)
            elif c['area'] >= 6: rest.append(c)
        clusters = [dict(members=m, forced=k) for k, m in groups.items()] + [dict(members=[c]) for c in rest]
        def ext(k): return min(m['x0'] for m in k['members']), max(m['x1'] for m in k['members'])
        changed = True
        while changed:
            changed = False
            for i in range(len(clusters)):
                for j in range(i+1, len(clusters)):
                    a, b = clusters[i], clusters[j]
                    if a.get('forced') or b.get('forced'): continue
                    a0, a1 = ext(a); b0, b1 = ext(b)
                    ov = overlap(a0, a1, b0, b1); mw = min(a1-a0, b1-b0)
                    sa = sum(m['area'] for m in a['members']); sb = sum(m['area'] for m in b['members'])
                    if ov >= 0.5*mw and (min(sa, sb) < 0.35*max(sa, sb) or ov >= 0.8*mw):
                        a['members'] += b['members']; clusters.pop(j); changed = True; break
                if changed: break
        # splits of fused glyphs
        out = []
        for k in clusters:
            k0, k1 = ext(k)
            sp_ = [s for s in sp.get('split', []) if s[0] == li and k0 <= s[1] < k1]
            if not sp_:
                out.append(make_cluster([m['pix'] for m in k['members']])); continue
            big = max(k['members'], key=lambda m: m['x1']-m['x0'])
            parts, T = split_component(big, sp_[0][2], sp_[0][3] if len(sp_[0]) > 3 else None)
            bins = [[p] for p in parts]
            for m in k['members']:
                if m is big: continue
                ov = [overlap(m['x0'], m['x1'], p[1].min(), p[1].max()+1) for p in parts]
                bins[int(np.argmax(ov))].append(m['pix'])
            out += [make_cluster(b) for b in bins]
        out.sort(key=lambda k: k['x0'])
        lines.append(dict(names=names, clusters=out))
        if verbose and len(out) != len(names):
            print(f'{font} L{li+1}: {len(out)} clusters / {len(names)} expected MISMATCH',
                  [(k['x0'], k['x1'], k['area']) for k in out])
    return lines

def annotate(font, lines, out, f=3):
    x0, y0, x1, y1 = SPECS[font]['box']
    im = Image.fromarray(GRAY[y0:y1, x0:x1].astype(np.uint8)).convert('RGB')
    im = im.resize((im.width*f, im.height*f), Image.LANCZOS)
    tint = np.asarray(im).copy()
    for L in lines:
        for i, k in enumerate(L['clusters']):
            col = np.array([(230,40,40),(30,110,230),(20,160,60)][i % 3])
            ys, xs = k['pix']
            for dy in range(f):
                for dx in range(f):
                    yy, xx = (ys-y0)*f+dy, (xs-x0)*f+dx
                    tint[yy, xx] = (0.35*tint[yy, xx] + 0.65*col).astype(np.uint8)
    im = Image.fromarray(tint); d = ImageDraw.Draw(im)
    for L in lines:
        for i, k in enumerate(L['clusters']):
            nm = L['names'][i] if i < len(L['names']) else '?'
            d.text(((k['x0']-x0)*f, (k['y1']-y0)*f+2), nm.replace('.alt', '.')[:8], fill=(0,0,0))
    im.save(out)

if __name__ == '__main__':
    for font in sys.argv[1:]:
        lines = segment(font)
        annotate(font, lines, os.path.join(paths.VIEW, f'seg_{font}.png'))
        print(font, 'lines ok:', all(len(L['clusters']) == len(L['names']) for L in lines))
