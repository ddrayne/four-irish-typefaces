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
    if getattr(font,'CLEAR_ROUND',False):clear_round(font,names,ys,profiles,effective,clearance)
    return changes


def clear_round(font,names,ys,profiles,effective,clearance=8):
    """The same clearance in every direction, not only across: after protect_kerning a pair's facing edges are
    `clearance` apart on each level line, but a tip can still pass closer than that above or below another (Kilfane's
    k before j stood 5.0 units off, Carrick's y before j 5.6). Each pair is measured again with the right-hand
    letter's edge on every line within `clearance` up and down, where it must stand off by what a disc of that
    radius reaches at that height; a sloped style measures the lines as its slope will move them. A pair that fails
    is opened by the least kerning step (5 units) that clears it, unless that would take more than 30 units: there one
    letter overhangs the other and the pair is left as it was (font.spacing_round_kept). Recorded in font.spacing_round."""
    from build2 import SLANT
    t=math.tan(math.radians(SLANT)) if getattr(font,'italic',False) else 0.0
    reach=clearance+1.0                       # a unit over, for the grid the outlines are settled on afterwards
    r=int(math.ceil(reach));step=ys[1]-ys[0]
    raw={n:silhouette(font.final[n],ys)[0] for n in names}
    def shifted(a,k):
        out=np.full(len(a),np.inf)
        if k>0:out[:-k]=a[k:]
        elif k<0:out[-k:]=a[:k]
        else:out=a
        return out
    # the left edge as a disc of the clearance sees it from each line: the least of (edge at dy) + slope*dy - reach(dy)
    seen={}
    for n in names:
        best=np.full(len(ys),np.inf)
        for k in range(-r,r+1):
            dy=k*step
            if abs(dy)>=reach:continue
            best=np.minimum(best,shifted(raw[n],k)+t*dy-math.sqrt(reach*reach-dy*dy))
        seen[n]=best
    changes=[];kept=[];limit=30
    for a in names:
        right=profiles[a][1]
        for b in names:
            current=font.kern_exc.get((a,b),effective.get((a,b),0))
            gap=font.adv[a]+current+seen[b]-right
            minimum=float(np.min(gap))
            if not np.isfinite(minimum) or minimum>=0:continue
            adjusted=int(math.ceil((current-minimum)/5)*5)
            if adjusted-current>limit:
                # one letter overhangs the other (Céilí's long s over d): moving across cannot clear it short of a gape
                # (ſ before d needed 170 units), so the pair keeps its spacing and its near pass, as up to 3.100
                kept.append(dict(left=a,right=b,kerning=current,would_need=adjusted-current));continue
            font.kern_exc[a,b]=adjusted
            changes.append(dict(left=a,right=b,before=current,after=adjusted,short_by=round(-minimum,2)))
    font.spacing_round=changes;font.spacing_round_kept=kept
    return changes
