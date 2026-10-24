"""Explicit original-source regions for the Tuam and Céilí outline studies.

N46 is the larger historical flyer. N45 is the competition brochure; both can
share original artwork/reproduction history. Native images are never enhanced.
"""
import argparse,copy,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from metrics import line_baselines
from kilfane_study import trace_region
from source_study import component_field,smooth_preserving_topology
from trace_carrick_study import regions_for

N46='competition-advert-1.jpg'
N45='competition-brochure-2.jpg'
LAYOUT={
 'tuam':{
  N46:dict(x=(1140,2050),ys=[(310,425),(425,530),(530,635),(635,735),(735,850)],rows=[
   {'a':[9],'b':[1],'c':[10],'d':[2],'e':[11],'f':[3],'g':[12],'h':[5],'i':[8,13],'j':[7,14],'k':[6],'l':[4]},
   {'m':[14,13,8],'n':[9,10],'o':[11],'p':[4],'q':[5],'r':[2],'s':[12],'t':[1],'u':[6,7],'v':[3]},
   {'w':[9],'x':[10],'y':[11,12],'z':[8],'one':[1],'two':[2],'three':[3],'four':[5],'five':[6],'six':[7],'seven':[4]},
   {'eight':[10],'nine':[11,12],'zero':[5],'sterling':[2],'dollar':[1],'ampersand':[6],'question':[7,17],'exclam':[8,18],'aacute':[9],'eacute':[3,13,14],'iacute':[4]},
   {'oacute':[2,5],'uacute':[1,3,4]}]),
  N45:dict(x=(2280,2940),ys=[(350,445),(438,540),(535,625),(625,715),(705,805)],rows=[
   {'a':[7],'b':[1],'c':[8],'d':[2],'e':[9],'f':[3,4],'g':[10],'h':[5,11],'i':[6,12]},
   {'j':[5,6],'k':[3],'l':[4],'m':[7,8,9],'n':[10,11],'o':[12],'p':[13],'q':[14],'r':[15,16]},
   {'s':[2],'t':[1],'u':[3,4],'v':[5,6],'w':[7,8,9],'x':[10],'y':[11,12],'z':[13]},
   {'one':[1],'two':[2],'three':[3],'four':[4],'five':[5,11],'six':[6],'seven':[7],'eight':[8],'nine':[9],'zero':[10]},
   {'sterling':[2],'dollar':[1],'ampersand':[3],'question':[4,16],'exclam':[5,17],'aacute':[6],'eacute':[7,11],'iacute':[8,12],'oacute':[9,13],'uacute':[10,14,15]}])},
 'ceili':{
  N46:dict(x=(1130,2070),ys=[(1410,1537),(1525,1680),(1645,1795),(1770,1885)],rows=[
   {'a':[14],'a.alt1':[15],'a.alt2':[12],'b':[2],'c':[7],'d':[3],'d.alt1':[6],'e':[11],'e.alt1':[13],'f':[8],'g':[5],'h':[1,9],'i':[4,10]},
   {'j':[6,17],'j.alt1':[12],'k':[4],'l':[5],'l.alt1':[3],'m':[13],'n':[14],'n.alt1':[15],'o':[7],'p':[9],'q':[16],'r':[10],'r.alt1':[8],'s':[11]},
   {'s.alt1':[4],'t':[12],'u':[18],'v':[19],'v.alt1':[15],'w':[14],'x':[16],'y':[17],'ampersand':[5],'z':[13],'parenleft':[11],'parenright':[8,10]},
   {'zero':[12],'one':[14],'two':[9,20],'three':[11],'four':[13],'five':[10],'six':[1],'seven':[7],'eight':[2],'nine':[6],'sterling':[8],'dollar':[4],'question':[3,17],'exclam':[5,18],'hyphen':[16]}]),
  N45:dict(x=(755,1430),ys=[(340,465),(450,560),(560,665),(665,770),(770,880)],rows=[
   {'a':[3],'a.alt1':[6],'a.alt2':[4],'b':[1],'c':[7],'d':[2],'d.alt1':[5],'e':[8],'e.alt1':[9],'f':[10]},
   {'g':[6],'h':[2],'i':[7,10],'j':[8,11],'j.alt1':[9],'k':[3],'l':[5],'l.alt1':[4],'m':[12],'n':[13],'n.alt1':[15],'o':[14]},
   {'p':[3],'q':[7],'r':[4],'r.alt1':[5],'s':[6],'s.alt1':[1],'t':[2],'u':[8],'v':[10],'v.alt1':[9],'hyphen':[11]},
   {'w':[11],'x':[12],'y':[13],'ampersand':[1],'z':[10],'parenleft':[2],'parenright':[8],'exclam':[9,20]},
   {'zero':[6],'one':[7],'two':[5],'three':[8],'four':[11],'five':[9],'six':[1],'seven':[10],'eight':[2],'nine':[12],'sterling':[13],'dollar':[3],'question':[4,14]}])}}

CALIBRATE=set('acemnorsuvwz')
SITTING=set('abcdehiklmnorstuvwz')|{'a.alt1','a.alt2','d.alt1','e.alt1','j.alt1','l.alt1','n.alt1','s.alt1','v.alt1'}
FIGURES={'zero','one','two','five','six','eight','nine'}

def calibration(regions,old,face):
    oldbase=line_baselines(old);byname={g['name']:g for g in old}
    scale=float(np.median([(r['box'][3]-r['box'][1])/(oldbase[byname[r['name']]['line_idx']]-byname[r['name']]['b'][1])
        for r in regions if r['name'] in CALIBRATE]))
    bases={}
    for row in sorted({r['row'] for r in regions}):
        rs=[r for r in regions if r['row']==row]
        good=[r for r in rs if r['name'] in SITTING]
        if not good:good=[r for r in rs if r['name'] in FIGURES]
        if not good:good=[r for r in rs if r['name'] in ['exclam','question','oacute','uacute']]
        bases[row]=float(np.median([r['box'][3]-1 for r in good]))
    return scale,bases

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--face',choices=LAYOUT,required=True)
    ap.add_argument('--sources',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--prefer',choices=['N46','N45'],default='N46',help='Source proposal to inspect; not automatic acceptance')
    args=ap.parse_args();root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'research/downloads.json').read_text(encoding='utf-8'))['assets']
    doc=json.loads((root/f'sources/traced/{args.face}.json').read_text(encoding='utf-8'))
    old=doc['glyphs'];oldbase=line_baselines(old);images={};regions={};hashes={};cal={}
    for filename,layout in LAYOUT[args.face].items():
        path=args.sources/filename;digest=hashlib.sha256(path.read_bytes()).hexdigest()
        expected=next(a['sha256'] for a in manifest if a['path']=='original-specimens/'+filename)
        if digest!=expected:raise ValueError('source image changed: '+filename)
        hashes[filename]=digest;images[filename]=np.array(Image.open(path).convert('L'))
        regions[filename]=regions_for(images[filename],layout)
        for r in regions[filename]:
            x0,y0,x1,y1=r['box'];rx0,ry0,rx1,ry1=r['row_box']
            if x0<=rx0 or y0<=ry0 or x1>=rx1 or y1>=ry1:raise ValueError(f'clipped source region: {filename} {r}')
        cal[filename]=calibration(regions[filename],old,args.face)
    lookup={f:{r['name']:r for r in rs} for f,rs in regions.items()};evidence=[];traces=[]
    for g in old:
        name=g['name'];source=N45 if args.prefer=='N45' else N46
        if args.face=='ceili' and name in ['b','e','e.alt1','h']:source=N45
        if name not in lookup[source]:
            kept=copy.deepcopy(g);kept.pop('b',None);traces.append(kept)
            evidence.append(dict(name=name,status='retained',reason='Loose punctuation cluster retained pending explicit piece-to-glyph mapping.'));continue
        r=lookup[source][name];scale,bases=cal[source]
        traces.append(trace_region(images[source],r,scale,bases[r['row']],g,oldbase[g['line_idx']],field_function=component_field,smoothing_function=smooth_preserving_topology))
        evidence.append(dict(name=name,status='candidate',source=source,source_id='N46' if source==N46 else 'N45',
            box=r['box'],labels=r['labels'],row_box=r['row_box'],scale=scale,source_baseline=bases[r['row']],old_baseline=oldbase[g['line_idx']],
            smoothing_sigma=traces[-1]['source_smoothing_sigma'],topology_policy='Preserve substantive unsmoothed source contours; reduce blur before tracing if needed.',
            note='Brochure supplies a less damaged thin stroke or shoulder.' if source==N45 else 'Larger original flyer; detached components retained together.'))
    doc.update(source='NIVAL N46/N45; explicit identities and calibration in evidence.json',glyphs=traces)
    report=dict(face=args.face,status='research candidate; not release',source_hashes=hashes,glyphs=evidence,
        calibration={file:dict(scale=s,baselines=b) for file,(s,b) in cal.items()},
        limitations=['N46/N45 can share artwork or reproduction history; source fit is not independent authentication.',
                    'Legacy builder text-height regularisation and modern extensions remain.',
                    'Tuam accented entries supply accent geometry; final accents are assembled for text.'])
    if args.face=='ceili':report['disable_legacy_repairs']=['h'];report['disable_legacy_hairlines']=['b','e','e.alt1']
    args.output.mkdir(parents=True,exist_ok=True)
    for name,value in [(args.face+'.json',doc),('evidence.json',report),('source-regions.json',regions)]:
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(args.face, sum(g['status']=='candidate' for g in evidence),'new source entries',len(evidence),'total')

if __name__=='__main__':main()
