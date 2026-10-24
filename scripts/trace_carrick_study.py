"""Carrick from N513; named components retain intentional detached strokes.

N47 is an additional reproduction with shared source history, not a blind holdout.
Fused e/f and x/y are retained from the previous reconstruction.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
from metrics import line_baselines
from kilfane_study import trace_region
from source_study import component_field

PRIMARY='Carrick-alphabet-specimen.jpg'
CHECK='competition-advert-2.jpg'
# Visually assigned components. Each row uses its own connected-component labels.
LAYOUT={
 PRIMARY:dict(x=(120,1220),ys=[(105,288),(290,460),(490,635),(660,790),(820,980)],rows=[
  {'a':[10],'b':[4],'c':[13,15],'d':[3],'g':[11,19],'h':[5],'i':[7,14],'j':[8,12,20],'k':[6,9]},
  {'l':[1],'m':[8],'n':[10],'o':[3],'p':[9],'q':[6],'r':[7],'s':[4,11],'t':[2]},
  {'u':[6,8],'v':[1,7],'w':[2,3],'z':[5]},
  {'one':[2],'two':[12],'three':[4,10],'four':[5],'five':[3,13],'six':[6],'seven':[8],'eight':[1],'nine':[7,11],'zero':[9]},
  {'ampersand':[6,14],'question':[5,23],'exclam':[7,25],'sterling':[4,24],'dollar':[1],'parenleft':[3],'semicolon':[11,20],'parenright':[2]}]),
 CHECK:dict(x=(500,1700),ys=[(80,275),(275,460),(480,640),(655,805),(820,1000)],rows=[
  {'a':[13],'b':[8],'c':[14,15],'d':[4],'g':[11,18],'h':[5],'i':[6,12],'j':[7,10,19],'k':[3,9]},
  {'l':[1],'m':[10],'n':[9],'o':[5],'p':[8],'q':[7],'r':[6],'s':[3,11],'t':[2]},
  {'u':[8,9],'v':[2,7],'w':[4,5],'z':[1]},
  {'one':[4],'two':[11],'five':[5,12],'six':[6],'seven':[7],'eight':[1],'nine':[2,8],'zero':[3]},
  {'ampersand':[7,15],'question':[5,24],'exclam':[6,25],'sterling':[4,23],'dollar':[1],'parenleft':[3],'semicolon':[11,20],'parenright':[2]}])}
SITTING=set('abcdn hiklmnorstuvwz'.replace(' ',''))
CALIBRATE=set('acmnorsuvwz')


def regions_for(gray,layout):
    result=[]
    for row,((y0,y1),names) in enumerate(zip(layout['ys'],layout['rows'])):
        x0,x1=layout['x'];labels,_=ndi.label(gray[y0:y1,x0:x1]<130,np.ones((3,3)))
        for name,ids in names.items():
            if any(not np.any(labels==i) for i in ids):raise ValueError(f'missing component: {name}')
            yy,xx=np.nonzero(np.isin(labels,ids))
            result.append(dict(name=name,row=row,labels=ids,row_box=[x0,y0,x1,y1],threshold=130,
                box=[int(xx.min()+x0),int(yy.min()+y0),int(xx.max()+x0+1),int(yy.max()+y0+1)]))
    return result


def calibrate(regions,old):
    oldbase=line_baselines(old);old_by={g['name']:g for g in old}
    scale=float(np.median([(r['box'][3]-r['box'][1])/(oldbase[old_by[r['name']]['line_idx']]-old_by[r['name']]['b'][1])
                           for r in regions if r['name'] in CALIBRATE]))
    bases={}
    for row in range(5):
        candidates=[r['box'][3]-1 for r in regions if r['row']==row and
                    (r['name'] in SITTING or r['name'] in ['one','two','three','four','five','six','seven','eight','nine','zero'])]
        if not candidates:candidates=[r['box'][3]-1 for r in regions if r['row']==row and r['name'] in ['exclam','sterling','question']]
        bases[row]=float(np.median(candidates))
    return scale,bases


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sources',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'research/downloads.json').read_text(encoding='utf-8'))['assets']
    images={};hashes={};regions={};cal={}
    doc=json.loads((root/'sources/traced/carrick.json').read_text(encoding='utf-8'))
    old=doc['glyphs'];oldbase=line_baselines(old)
    for filename,layout in LAYOUT.items():
        path=args.sources/filename;digest=hashlib.sha256(path.read_bytes()).hexdigest()
        expected=next(a['sha256'] for a in manifest if a['path']=='original-specimens/'+filename)
        if digest!=expected:raise ValueError(f'source changed: {filename}')
        hashes[filename]=digest;images[filename]=np.array(Image.open(path).convert('L'))
        regions[filename]=regions_for(images[filename],layout);cal[filename]=calibrate(regions[filename],old)
    lookup={r['name']:r for r in regions[PRIMARY]};scale,baselines=cal[PRIMARY]
    traces=[];evidence=[]
    for g in old:
        name=g['name']
        if name in lookup:
            r=lookup[name]
            traces.append(trace_region(images[PRIMARY],r,scale,baselines[r['row']],g,oldbase[g['line_idx']],field_function=component_field))
            evidence.append(dict(name=name,status='candidate',source=PRIMARY,source_id='N513',box=r['box'],
                labels=r['labels'],scale=scale,source_baseline=baselines[r['row']],old_baseline=oldbase[g['line_idx']],
                note='Detached source components preserved together; uniform source scaling. Existing builder still regularises text heights.'))
        else:
            kept=copy.deepcopy(g);kept.pop('b',None);traces.append(kept)
            evidence.append(dict(name=name,status='retained',reason='Fused e/f or x/y; loose marks remain legacy pending separate component study.'))
    doc.update(source='NIVAL N513 plus explicitly retained baseline entries',glyphs=traces)
    report=dict(face='carrick',status='research candidate; not release',source_hashes=hashes,glyphs=evidence,
        calibration={file:dict(scale=s,baselines=b) for file,(s,b) in cal.items()},
        limitations=['N513 and N47 share reproduction history; not independent original drawings.',
                    'N47 three/four are fused and excluded from its comparison regions.',
                    'Forty source entries reconstructed; e/f/x/y and marks cluster remain legacy.'])
    args.output.mkdir(parents=True,exist_ok=True)
    for name,value in [('carrick.json',doc),('evidence.json',report),('source-regions.json',regions)]:
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Carrick: 40 reconstructed entries; five retained; source regions and calibration saved')


if __name__=='__main__':main()
