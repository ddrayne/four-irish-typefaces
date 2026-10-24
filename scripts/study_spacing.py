"""Conservative full-height collision protection for research builds only.

The release's optical spacing remains the starting point. Positive pair exceptions
are added where full glyph silhouettes (including accents/descenders) need room.
No outline is changed. Binary shaping/intersection audits verify the result.
"""
import math
import numpy as np
from scipy.ndimage import minimum_filter1d
from fontTools.pens.recordingPen import RecordingPen
from glyphs import bounds
from outline_util import flatten


def silhouette(path,ys):
    pen=RecordingPen();path.draw(pen)
    edges=[]
    for poly in flatten(pen.value,steps=24):
        a=np.asarray(poly,float);b=np.roll(a,-1,axis=0)
        mask=np.abs(b[:,1]-a[:,1])>1e-9
        edges.extend(zip(a[mask],b[mask]))
    if not edges:return np.full(len(ys),np.inf),np.full(len(ys),-np.inf)
    a,b=np.asarray(edges).transpose(1,0,2)
    y=ys[:,None]
    crossing=((a[:,1]<=y)&(b[:,1]>y))|((b[:,1]<=y)&(a[:,1]>y))
    x=a[:,0]+(y-a[:,1])*(b[:,0]-a[:,0])/(b[:,1]-a[:,1])
    left=np.min(np.where(crossing,x,np.inf),axis=1)
    right=np.max(np.where(crossing,x,-np.inf),axis=1)
    return left,right


def protect_kerning(font,clearance=8):
    names=[n for n,p in font.final.items() if n not in font.mark_glyphs and n not in {'space','underscore'} and bounds(p)]
    low=math.floor(min(bounds(font.final[n])[1] for n in names))-3
    high=math.ceil(max(bounds(font.final[n])[3] for n in names))+3
    ys=np.arange(low+.5,high,1.)
    profiles={}
    for n in names:
        left,right=silhouette(font.final[n],ys)
        # A two-unit vertical allowance covers tiny diagonal tips between samples.
        profiles[n]=(minimum_filter1d(left,size=5,mode='constant',cval=np.inf),right)
    effective={}
    for (a,b),value in font.kern_pairs.items():
        for ga in font.left_group.get(a,[a]):
            for gb in font.right_group.get(b,[b]):effective[ga,gb]=value
    effective.update(font.kern_exc)
    changes=[]
    for a in names:
        right=profiles[a][1]
        for b in names:
            current=effective.get((a,b),0)
            gap=font.adv[a]+current+profiles[b][0]-right
            minimum=float(np.min(gap))
            if not np.isfinite(minimum) or minimum>=clearance:continue
            adjusted=int(math.ceil((current+clearance-minimum)/5)*5)
            font.kern_exc[a,b]=adjusted
            changes.append(dict(left=a,right=b,before=current,after=adjusted,measured_gap=minimum))
    font.spacing_protection=changes
    return changes
