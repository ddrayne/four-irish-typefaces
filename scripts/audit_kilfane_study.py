"""Measure both fonts against original specimens with uniform scale and translation only."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from outline_util import flatten,raster
from glyphs import SCALE
from metrics import line_baselines
from kilfane_study import calibration,isolated_field,PRIMARY,CHECK
from source_study import register_translation


def measure_font(gs,name,gray,r,scale,baseline):
    rec=RecordingPen();gs[name].draw(rec)
    polys=flatten(rec.value,steps=30)
    xmin=min(p[0] for q in polys for p in q)
    field,origin,_,_=isolated_field(gray,r,pad=7)
    target=ndi.gaussian_filter(field,.55)>.5
    # More pad allows translation without clipping any ink.
    pad=40
    target=np.pad(target,pad);h,w=target.shape
    sx=scale/SCALE['kilfane']
    fn=lambda p:((p[0]-xmin)*sx+r['box'][0]-origin[0]+pad, baseline-p[1]*sx-origin[1]+pad)
    rendered=raster(polys,(w,h),fn)
    rendered,offset=register_translation(rendered,target)
    iou=float((rendered&target).sum()/max((rendered|target).sum(),1))
    # Original crop stays unmodified apart from display padding.
    oh,ow=field.shape
    crop=Image.fromarray(gray[origin[1]:origin[1]+oh,origin[0]:origin[0]+ow]).convert('RGB')
    background=Image.new('RGB',(w,h),'white');background.paste(crop,(pad,pad))
    arr=np.array(background)
    edge=rendered&~ndi.binary_erosion(rendered)
    arr[edge]=[222,45,95]
    diff=np.full((h,w,3),255,np.uint8)
    diff[target&rendered]=[45,55,50];diff[target&~rendered]=[236,153,55];diff[rendered&~target]=[40,140,215]
    yy,xx=np.nonzero(rendered|target)
    box=(max(0,int(xx.min())-5),max(0,int(yy.min())-5),min(w,int(xx.max())+6),min(h,int(yy.max())+6))
    return (dict(iou=iou,offset=offset),Image.fromarray(arr).crop(box),Image.fromarray(diff).crop(box),
            Image.fromarray(np.where(rendered,20,255).astype(np.uint8)).convert('RGB').crop(box))


def main():
    ap=argparse.ArgumentParser()
    for name in ['sources','regions','candidate','baseline','output']:ap.add_argument('--'+name,type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    regions=json.loads(args.regions.read_text());repo=Path(__file__).resolve().parents[1]
    old=json.loads((repo/'sources/traced/kilfane.json').read_text())['glyphs'];line_baselines(old)
    fonts={label:TTFont(f).getGlyphSet() for label,f in [('before',args.baseline),('candidate',args.candidate)]}
    label_font=ImageFont.load_default(size=17)
    allrows=[]
    for source,rs in regions.items():
        gray=np.asarray(Image.open(args.sources/source).convert('L'))
        scale,bases=calibration(rs,old)
        tiles=[]
        for r in rs:
            name=r['name']
            if name not in fonts['before'] or name=='semicolon':continue
            row=dict(name=name,source=source);panels=[]
            for label,gs in fonts.items():
                metric,overlay,diff,fill=measure_font(gs,name,gray,r,scale,bases[r['row']])
                row[label]=metric
                panels.extend([overlay,fill])
            row['delta']=row['candidate']['iou']-row['before']['iou'];allrows.append(row)
            w=max(170,max(p.width for p in panels));h=max(p.height for p in panels)
            tile=Image.new('RGB',(4*w+30,h+54),'white');d=ImageDraw.Draw(tile)
            d.text((2,2),f'{name}   before {row["before"]["iou"]:.3f}   candidate {row["candidate"]["iou"]:.3f}   delta {row["delta"]:+.3f}',font=label_font,fill='black')
            for i,(p,lab) in enumerate(zip(panels,['Before / source','Before','Candidate / source','Candidate'])):
                tile.paste(p,(i*(w+10),54));d.text((i*(w+10),28),lab,font=label_font,fill='#476052')
            tiles.append(tile)
        # All glyphs available as individual readable panels and five-per-page contact sheets.
        stem='N516' if source==PRIMARY else 'N47'
        for stale in args.output.glob(stem+'-*.png'):
            if stale.stem[len(stem)+1:].isdigit():
                stale.unlink()
        for i in range(0,len(tiles),5):
            subset=tiles[i:i+5];page=Image.new('RGB',(max(p.width for p in subset),sum(p.height for p in subset)+15*len(subset)), '#d9dfd5')
            y=0
            for tile in subset:page.paste(tile,(0,y));y+=tile.height+15
            page.save(args.output/f'{stem}-{i//5+1:02d}.png')
        print(stem,'glyphs',len(tiles),flush=True)
    summary={}
    for source in regions:
        # The production specimen's elevated compact semicolon is intentionally
        # reassembled at text punctuation heights by Font2. It is not a like-for-
        # like outline registration and must not enter the summary statistic.
        rs=[r for r in allrows if r['source']==source and r['name']!='semicolon']
        summary[source]=dict(glyphs=len(rs),before=float(np.mean([r['before']['iou'] for r in rs])),
                            candidate=float(np.mean([r['candidate']['iou'] for r in rs])),
                            improved=sum(r['delta']>0 for r in rs),regressed=[r['name'] for r in rs if r['delta']<-.005])
    (args.output/'metrics.json').write_text(json.dumps(dict(summary=summary,glyphs=allrows,
        limitations=['Two reproductions share matching blemishes; not independent original drawings.',
                     'Candidate was derived from N516 except v/w from N47; this is a fit measure, not blind validation.',
                     'Semicolon excluded from summary because Font2 deliberately resets its vertical layout.',
                     'Uniform source scale, integer translation only; no per-glyph width or height fitting.']),indent=2))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
