"""Named Céilí punctuation from N45, with N46 comparison regions."""
import argparse,hashlib,json,shutil
from pathlib import Path
import numpy as np
from PIL import Image
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from glyphs import SCALE,to_path,clean
from kilfane_study import trace_region
from source_study import component_field,smooth_preserving_topology
from trace_carrick_study import regions_for

N45='competition-brochure-2.jpg'
N46='competition-advert-1.jpg'
LAYOUT={
 N45:dict(x=(755,1430),ys=[(665,770)],rows=[{'period':[17],'comma':[18],'quoteleft':[6],'quoteright':[7]}]),
 N46:dict(x=(1130,2070),ys=[(1645,1795)],rows=[{'period':[26],'comma':[25],'quoteleft':[6],'quoteright':[7]}])}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--sources',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();root=Path(__file__).resolve().parents[1]
    previous=root/'research/round-03/ceili/traces'
    evidence=json.loads((previous/'evidence.json').read_text(encoding='utf-8'))
    regions={};images={};cal={}
    previous_glyphs=TTFont(root/'research/round-03/ceili/fonts/CeiliStudy2-Regular.otf').getGlyphSet()
    for filename,layout in LAYOUT.items():
        p=args.sources/filename
        if hashlib.sha256(p.read_bytes()).hexdigest()!=evidence['source_hashes'][filename]:
            raise ValueError('source image changed: '+filename)
        images[filename]=np.array(Image.open(p).convert('L'))
        regions[filename]=regions_for(images[filename],layout)
        # Text positions differ from the sheet. Start each comparison in-frame;
        # the audit then searches all integer translations at the fixed scale.
        scale=evidence['calibration'][filename]['scale'];bases={}
        for i,r in enumerate(regions[filename]):
            pen=BoundsPen(None);previous_glyphs[r['name']].draw(pen)
            r['row']=i;bases[str(i)]=r['box'][3]+pen.bounds[1]*scale/SCALE['ceili']
        cal[filename]=dict(scale=scale,baselines=bases)
    scale=evidence['calibration'][N45]['scale'];s=SCALE['ceili']
    pieces=[]
    for region in regions[N45]:
        template=dict(name=region['name'],line_idx=0,b=[0,0,0,0])
        record=trace_region(images[N45],region,scale,region['box'][3],template,0,
            field_function=component_field,smoothing_function=smooth_preserving_topology)
        path=clean(to_path(record['rec'],(s,0,0,-s,0,0)))
        pen=RecordingPen();path.draw(pen)
        pieces.append(dict(**region,source=N45,source_id='N45',rec=pen.value,
            smoothing_sigma=record['source_smoothing_sigma'],
            source_to_font=[s/scale,0,0,-s/scale,-region['box'][0]*s/scale,region['box'][3]*s/scale]))
    args.output.mkdir(parents=True,exist_ok=True)
    for filename in ['ceili.json','evidence.json','source-regions.json']:
        shutil.copy2(previous/filename,args.output/filename)
    report=dict(face='ceili',units='font units, y up; uniform round-3 N45 scale, per-piece origin',
        source_hashes=evidence['source_hashes'],pieces=pieces,
        decision='Period and comma from the isolated N45 pair; quotes from the N45 opposed pair. Colon/semicolon provide repeated dot/tail evidence. Three upper pieces remain unassigned.',
        limitations=['Text positioning, repeated dots/quotes, straight quotation marks and derived language marks remain modern construction.',
                    'N46 comma is the semicolon lower component: its faint tail is incompletely captured at threshold 130; keep this limitation beside its score.'])
    for filename,data in [('punctuation.json',report),('punctuation-regions.json',regions),
        ('punctuation-evidence.json',dict(face='ceili',calibration=cal,
            note='Baselines initialise isolated glyph comparisons inside the raster; they are not historical layout measurements. Uniform scale and full integer translation only.'))]:
        (args.output/filename).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Four named N45 pieces; N46 comparison regions; round-3 body traces unchanged')

if __name__=='__main__':main()
