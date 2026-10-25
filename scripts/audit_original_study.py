"""Local source-pixel comparisons for a face's explicit regions and calibration."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
from audit_kilfane_study import measure_font
from source_study import component_field
from glyphs import SCALE


def run(sources,regions,cal,face,before,after,output,coverage=False):
    output.mkdir(parents=True,exist_ok=True);allrows=[];summary={}
    fonts=[TTFont(p).getGlyphSet() for p in [before,after]]
    label_font=ImageFont.load_default(size=17)
    for filename,rs in regions.items():
        gray=np.array(Image.open(sources/filename).convert('L'));tiles=[];rows=[]
        for r in rs:
            name=r['name']
            if name not in fonts[0] or name=='semicolon':continue
            panels=[];row=dict(name=name,source=filename)
            for label,gs in zip(['before','candidate'],fonts):
                options={}
                if coverage:
                    from source_study import raster_coverage
                    options['raster_function']=lambda p,s,f:raster_coverage(p,s,f,samples=8)>.5
                metric,overlay,difference,fill=measure_font(gs,name,gray,r,cal[filename]['scale'],
                    cal[filename]['baselines'][str(r['row'])],unit_scale=SCALE[face],field_function=component_field,**options)
                row[label]=metric;panels.extend([overlay,fill])
            row['delta']=row['candidate']['iou']-row['before']['iou'];rows.append(row)
            w=max(p.width for p in panels);h=max(p.height for p in panels)
            tile=Image.new('RGB',(max(780,4*(w+12)),h+48),'white');d=ImageDraw.Draw(tile)
            d.text((6,4),f'{name}   before {row["before"]["iou"]:.3f}   candidate {row["candidate"]["iou"]:.3f}   delta {row["delta"]:+.3f}',font=label_font,fill='black')
            for i,p in enumerate(panels):tile.paste(p,(i*(w+12),40))
            tiles.append(tile)
        stem=Path(filename).stem
        for i in range(0,len(tiles),5):
            batch=tiles[i:i+5];page=Image.new('RGB',(max(t.width for t in batch),sum(t.height+12 for t in batch)),'#ddd')
            y=0
            for tile in batch:page.paste(tile,(0,y));y+=tile.height+12
            page.save(output/f'{stem}-{i//5+1:02d}.png')
        allrows.extend(rows)
        summary[filename]=dict(entries=len(rows),before=float(np.mean([r['before']['iou'] for r in rows])),
            candidate=float(np.mean([r['candidate']['iou'] for r in rows])),improved=sum(r['delta']>0 for r in rows),
            regressions=[dict(name=r['name'],delta=r['delta']) for r in rows if r['delta']<-.005])
    report=dict(face=face,raster_method='8x8 pixel-centred coverage, threshold >0.5' if coverage else 'legacy inclusive-polygon native raster',summary=summary,glyphs=allrows,limitations=[
        'Additional reproductions can share source history. These are source-fit measurements, not authenticity scores.',
        'Uniform source scaling and integer translation only; source-derived entries are not a blind holdout.',
        'Semicolon excluded because the text builder changes its layout.'])
    (output/'metrics.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(summary,indent=2));return report


def main():
    ap=argparse.ArgumentParser()
    for name in ['sources','traces','baseline','candidate','output']:ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--coverage',action='store_true',help='Use area sampling instead of inclusive native-pixel polygon edges')
    args=ap.parse_args();evidence=json.loads((args.traces/'evidence.json').read_text(encoding='utf-8'))
    regions=json.loads((args.traces/'source-regions.json').read_text(encoding='utf-8'))
    run(args.sources,regions,evidence['calibration'],evidence['face'],args.baseline,args.candidate,args.output,coverage=args.coverage)


if __name__=='__main__':main()
