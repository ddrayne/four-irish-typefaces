"""Reproducible Kilfane research candidate from original NIVAL specimen images.

Usage: python scripts/kilfane_study.py --sources DIR --regions JSON --output DIR
The release and sources/traced are never overwritten. Input images stay untouched.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure
from fontTools.pens.recordingPen import RecordingPen,replayRecording
from fontTools.pens.transformPen import TransformPen
from curvefit import curves_to_recording
from curvefit3 import contour_to_curves4
from metrics import bounds,line_baselines
from source_study import normalise_points

PRIMARY='Kilfane-alphabet-specimen.jpg'
CHECK='competition-advert-2.jpg'
FLAT=set('EFHIKLMNXZ')
SITTING=set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')-set('JQfgjpqty')


def isolated_field(gray,region,pad=5):
    """Local grayscale ink coverage; neighboring glyphs masked by component identity."""
    rx0,ry0,rx1,ry1=region['row_box']
    labels,_=ndi.label(gray[ry0:ry1,rx0:rx1]<130,structure=np.ones((3,3)))
    own=np.isin(labels,region['labels'])
    permitted=ndi.binary_dilation(own,iterations=3)
    x0,y0,x1,y1=region['box']
    x0=max(rx0,x0-pad); y0=max(ry0,y0-pad)
    x1=min(rx1,x1+pad); y1=min(ry1,y1+pad)
    a=gray[y0:y1,x0:x1].astype(float)
    m=permitted[y0-ry0:y1-ry0,x0-rx0:x1-rx0]
    core=own[y0-ry0:y1-ry0,x0-rx0:x1-rx0]
    paper=float(np.percentile(a[~core],80))
    ink=float(np.percentile(a[core],30))
    field=np.where(m,np.clip((paper-a)/max(paper-ink,1),0,1),0.)
    return field,(x0,y0),paper,ink


def calibration(regions,old):
    oldbase=line_baselines(old)
    oldheights={r['name']:oldbase[r['line_idx']]-r['b'][1] for r in old}
    scale=float(np.median([(r['box'][3]-r['box'][1])/oldheights[r['name']]
                          for r in regions if r['name'] in FLAT]))
    baselines={}
    for row in sorted(set(r['row'] for r in regions)):
        rs=[r for r in regions if r['row']==row]
        good=[r for r in rs if r['name'] in SITTING or (row==5 and r['name'] in ['one','two','four','five','seven'])
              or (row==7 and r['name'] in ['A.alt1','A.alt2','D.alt1','S.alt1','T.alt1','Y.alt1','d.alt1','l.alt1','t.alt1'])]
        baselines[row]=float(np.median([r['box'][3]-1 for r in good or rs]))
    return scale,baselines


def trace_region(gray,r,scale,baseline,old_r,old_base,field_function=isolated_field,smoothing_function=None):
    field,origin,paper,ink=field_function(gray,r)
    # Native-resolution antialias smoothing, substantially less than one legacy pixel.
    field,sigma=(ndi.gaussian_filter(field,.8),.8) if smoothing_function is None else smoothing_function(field)
    binary=field>.5
    holes,_=ndi.label(~binary)
    for lab in range(1,holes.max()+1):
        yy,xx=np.nonzero(holes==lab)
        if len(xx)<5 and not (0 in xx or field.shape[1]-1 in xx or 0 in yy or field.shape[0]-1 in yy):
            field[holes==lab]=1
    curves=[]
    for c in measure.find_contours(np.pad(field,2),.5):
        xy=np.column_stack((c[:,1]-2+origin[0],c[:,0]-2+origin[1]))
        if np.linalg.norm(xy[0]-xy[-1])>1e-6:raise ValueError('open source contour: '+r['name'])
        area=abs(np.sum(xy[:,0]*np.roll(xy[:,1],-1)-xy[:,1]*np.roll(xy[:,0],-1))/2)
        # G's tiny enclosed white fleck is print damage, absent from repeated
        # Gs on the NIVAL 517 transfer sheet. Q's secondary counter is much
        # larger and supported by the flyer and transfer-sheet photograph.
        if area<6 or (r['name']=='G' and area<15):continue
        normalized=normalise_points(xy[:-1],scale,(r['box'][0],baseline),(old_r['b'][0],old_base))
        curves.append(contour_to_curves4(normalized,cutoff=6,corner_deg=55,rms_tol=.07,max_tol=.22,
                                         line_tol=.18,line_bulge=.055,line_min=4.5,snap_deg=1.5))
    if not curves:raise ValueError('no contours: '+r['name'])
    result=copy.deepcopy(old_r)
    result.pop('b',None)
    result.update(rec=curves_to_recording(curves),paper=paper,ink=ink)
    if smoothing_function is not None:result['source_smoothing_sigma']=sigma
    return result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sources',type=Path,required=True)
    ap.add_argument('--regions',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    document=json.loads((root/'sources/traced/kilfane.json').read_text())
    old=document['glyphs'];oldbase=line_baselines(old)
    regions=json.loads(args.regions.read_text())
    images={f:np.asarray(Image.open(args.sources/f).convert('L')) for f in regions}
    cal={f:calibration(rs,old) for f,rs in regions.items()}
    lookup={f:{r['name']:r for r in rs} for f,rs in regions.items()}
    revised=[];evidence=[]
    for i,g in enumerate(old):
        name=g['name'];src=PRIMARY if name in lookup[PRIMARY] else CHECK if name in lookup[CHECK] else None
        if src:
            r=lookup[src][name];scale,base=cal[src]
            new=trace_region(images[src],r,scale,base[r['row']],g,oldbase[g['line_idx']])
            revised.append(new)
            evidence.append(dict(name=name,status='candidate',source=src,box=r['box'],scale=scale,
                                 note=('G: small print-damage hole removed; checked against repeated transfer-sheet Gs.' if name=='G' else
                                       'Q: secondary counter retained; visible in flyer and transfer-sheet Qs.' if name=='Q' else
                                       'Open join retained as seen in larger originals and flyer.' if name in ['r','six','nine'] else
                                       'Specimen shape reconstructed; current builder retains text-height regularisation.'),
                                 source_baseline=base[r['row']],old_baseline=oldbase[g['line_idx']],old_x=g['b'][0]))
        else:
            new=copy.deepcopy(g);new.pop('b',None);revised.append(new)
            evidence.append(dict(name=name,status='retained',reason='Fused adjacent letters or loose-mark layout; no unsupported split.'))
        print(f'{i+1}/{len(old)} {name}: {"candidate" if src else "retained"}',flush=True)
    document.update(source='Multiple original NIVAL specimens; see evidence.json',glyphs=revised)
    (args.output/'kilfane.json').write_text(json.dumps(document,separators=(',',':')),encoding='utf-8')
    report=dict(face='kilfane',status='research candidate; not a release',calibration={f:dict(scale=s,baselines=b) for f,(s,b) in cal.items()},
                source_hashes={f:hashlib.sha256((args.sources/f).read_bytes()).hexdigest() for f in images},glyphs=evidence)
    (args.output/'evidence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

if __name__=='__main__':main()
