"""Carrick's isolated original marks, with explicit retained and derived pieces."""
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from glyphs import SCALE,to_path,clean,bounds,translate
from kilfane_study import trace_region
from source_study import component_field,smooth_preserving_topology
from trace_carrick_study import regions_for

PRIMARY='Carrick-alphabet-specimen.jpg';CHECK='competition-advert-2.jpg'
NAMES={1:'emdash',2:'dot',3:'acute',4:'circumflex',5:'endash',6:'ring',7:'ring.b',
       8:'unassigned.inner-chevrons',9:'guil.l1',10:'guil.r1',11:'tilde',12:'unassigned.lower-pair'}
GLYPHS={'acute':'acute','dot':'dotaccent','ring':'ring','circumflex':'circumflex',
        'tilde':'tilde','guil.r1':'guilsinglright','guil.l1':'guilsinglleft'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sources',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    root=Path(__file__).resolve().parents[1];previous=root/'research/round-02/carrick/traces'
    evidence=json.loads((previous/'evidence.json').read_text(encoding='utf-8'))
    images={};regions={};cal={}
    oldgs=TTFont(root/'research/round-02/carrick/fonts/CarrickStudy1-Regular.otf').getGlyphSet()
    for filename,box,names in [(PRIMARY,[700,835,960,975],NAMES),
        (CHECK,[1120,850,1410,980],{**NAMES,1:'dot',2:'acute',3:'emdash'})]:
        p=args.sources/filename
        if hashlib.sha256(p.read_bytes()).hexdigest()!=evidence['source_hashes'][filename]:raise ValueError('source changed: '+filename)
        images[filename]=np.array(Image.open(p).convert('L'))
        regions[filename]=regions_for(images[filename],dict(x=(box[0],box[2]),ys=[(box[1],box[3])],rows=[{n:[i] for i,n in names.items()}]))
    scale=evidence['calibration'][PRIMARY]['scale'];s=SCALE['carrick'];pieces=[];unassigned=[]
    for r in regions[PRIMARY]:
        record=trace_region(images[PRIMARY],r,scale,975,dict(name=r['name'],line_idx=0,b=[(r['box'][0]-700)/scale,0,0,0]),0,
            field_function=component_field,smoothing_function=smooth_preserving_topology)
        p=clean(to_path(record['rec'],(s,0,0,-s,0,0)));pen=RecordingPen();p.draw(pen)
        entry=dict(**r,status='unassigned' if r['name'].startswith('unassigned') else 'direct',source=PRIMARY,source_id='N513',
            rec=pen.value,smoothing_sigma=record['source_smoothing_sigma'],source_to_font=[s/scale,0,0,-s/scale,-700*s/scale,975*s/scale])
        (unassigned if entry['status']=='unassigned' else pieces).append(entry)
    # Retain the previous uncertain diaeresis, without pretending it was traced anew.
    import paths,build2
    paths.TRACED=str(previous)
    legacy=build2.Font2('carrick','Regular');legacy.specimen_pieces()
    for name in ['dieresis.l','dieresis.r']:
        pen=RecordingPen();legacy.piece[name].draw(pen)
        pieces.append(dict(name=name,status='retained',rec=pen.value,
            note='Legacy flyer construction; right repeats left because the low-resolution cluster was fused. Identification of the larger lower paired component remains unresolved.'))
    for first,second in [('guil.r1','guil.r2'),('guil.l1','guil.l2')]:
        p=to_path(next(r['rec'] for r in pieces if r['name']==first),(1,0,0,1,0,0));b=bounds(p);pitch=.88*(b[2]-b[0])
        pen=RecordingPen();translate(p,pitch,0).draw(pen)
        pieces.append(dict(name=second,status='derived',parent=first,rec=pen.value,pitch=pitch,
            note='Repeated outer chevron at inherited 0.88-width pitch; not a trace of the fused inner component.'))
    audit_regions={}
    for filename,rs in regions.items():
        audit_regions[filename]=[];bases={};scale=evidence['calibration'][filename]['scale']
        for r in rs:
            if r['name'] not in GLYPHS:continue
            row=len(bases);glyph=GLYPHS[r['name']];bp=BoundsPen(None);oldgs[glyph].draw(bp)
            bases[str(row)]=r['box'][3]+bp.bounds[1]*scale/s
            audit_regions[filename].append(dict(r,name=glyph,piece=r['name'],row=row))
        cal[filename]=dict(scale=scale,baselines=bases)
    args.output.mkdir(parents=True,exist_ok=True)
    for name in ['carrick.json','source-regions.json']:shutil.copy2(previous/name,args.output/name)
    evidence['inherited_body_evidence']='research/round-02/carrick/traces/evidence.json'
    evidence['marks_evidence']='pieces.json'
    evidence['limitations']=[s for s in evidence['limitations'] if 'Forty source entries' not in s]
    evidence['limitations'].append('Forty body entries retained from Study 1; e/f/x/y remain legacy. Named mark inputs and their direct/derived/retained status are in pieces.json.')
    for g in evidence['glyphs']:
        if g['name']=='ornament':
            g.update(status='superseded',reason='Legacy cluster preserved only in the inherited trace file; final named mark inputs come from pieces.json.')
        elif g['status']=='retained':g['reason']='Fused e/f or x/y retained from the previous body reconstruction.'
    (args.output/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8',newline='\n')
    report=dict(face='carrick',primary_source_id='N513',source_hashes=evidence['source_hashes'],
        units='font units, y up; direct components share a uniform source transform',pieces=pieces,unassigned=unassigned,
        decision='Ten isolated components traced. Lower paired shape and fused inner chevrons remain unassigned. Diaeresis retained; paired guillemets repeat original outer chevrons.',
        body='Carrick Study 1 body traces unchanged')
    for name,data in [('pieces.json',report),('mark-regions.json',audit_regions),('mark-evidence.json',dict(face='carrick',calibration=cal,
        note='Per-piece baselines initialise translated shape comparisons inside the raster; not historical placement measurements.'))]:
        (args.output/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('10 direct marks, 2 retained diaeresis pieces, 2 derived chevrons, 2 unassigned components')

if __name__=='__main__':main()
