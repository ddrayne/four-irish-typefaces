"""Reconstruct named loose marks from N516, preserving ambiguous pieces as evidence."""
import argparse,copy,hashlib,json,shutil
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
from fontTools.pens.recordingPen import RecordingPen
from glyphs import SCALE,to_path,clean
from kilfane_study import trace_region,PRIMARY
from source_study import component_field

# Labels in the full punctuation row of the recorded N516 segmentation.
# Names assigned by visual inspection of N516 and N47, not nearest-centre guessing.
NAMES={8:'emdash',9:'tilde',10:'acute',11:'endash',13:'dieresis.l',14:'dieresis.r',
       15:'dot',16:'ring',17:'circumflex',18:'guil.r2',19:'guil.l1',20:'guil.r1',
       21:'guil.l2',23:'ring.b',24:'unassigned.lower-left',25:'unassigned.lower-right'}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sources',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    first=root/'research/kilfane-study-01/traces'
    evidence=json.loads((first/'evidence.json').read_text(encoding='utf-8'))
    image_path=args.sources/PRIMARY
    digest=hashlib.sha256(image_path.read_bytes()).hexdigest()
    if digest!=evidence['source_hashes'][PRIMARY]:raise ValueError('N516 image hash changed; review source before reusing labels')
    gray=np.array(Image.open(image_path).convert('L'))
    rs=json.loads((first/'source-regions.json').read_text(encoding='utf-8'))[PRIMARY]
    row=next(r for r in rs if r['name']=='marks.left')['row_box']
    x0,y0,x1,y1=row;labels,_=ndi.label(gray[y0:y1,x0:x1]<130,np.ones((3,3)))
    scale=evidence['calibration'][PRIMARY]['scale'];s=SCALE['kilfane']
    pieces=[];unassigned=[]
    for label,name in NAMES.items():
        yy,xx=np.nonzero(labels==label)
        if not len(xx):raise ValueError(f'missing component {label}')
        box=[int(xx.min()+x0),int(yy.min()+y0),int(xx.max()+x0+1),int(yy.max()+y0+1)]
        region=dict(name=name,box=box,row_box=row,labels=[label],threshold=130)
        # Common origin and scale retain the relative position of paired pieces.
        template=dict(name=name,line_idx=0,b=[(box[0]-760)/scale,0,0,0])
        record=trace_region(gray,region,scale,1225,template,0,field_function=component_field)
        path=clean(to_path(record['rec'],(s,0,0,-s,0,0)))
        pen=RecordingPen();path.draw(pen)
        entry=dict(**region,source=PRIMARY,source_id='N516',rec=pen.value,
                   source_to_font=[s/scale,0,0,-s/scale,-760*s/scale,1225*s/scale])
        (unassigned if name.startswith('unassigned.') else pieces).append(entry)
    args.output.mkdir(parents=True,exist_ok=True)
    for name in ['kilfane.json','evidence.json','source-regions.json']:
        shutil.copy2(first/name,args.output/name)
    result=dict(face='kilfane',units='font units, y up; common source transform',
                source_hashes={PRIMARY:digest},pieces=pieces,unassigned=unassigned,
                decision='Lower pair is not confidently identified as a caron. Preserve both as unassigned evidence; derive the modern caron from the attested circumflex.',
                body='Study 1 bodies retained without retracing')
    (args.output/'pieces.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(f'{len(pieces)} identified pieces; {len(unassigned)} unassigned pieces; Study 1 bodies unchanged')


if __name__=='__main__':main()
