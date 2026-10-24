"""Shape all mapped Latin letter pairs and measure actual outline intersections."""
import argparse,itertools,json,unicodedata
from pathlib import Path
import pathops
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.transformPen import TransformPen


def audit_font_pairs(path,characters=None,features=None,tolerance=4):
    path=Path(path);tt=TTFont(path);gs=tt.getGlyphSet();order=tt.getGlyphOrder();cm=tt.getBestCmap()
    available=([ch for ch in characters if ord(ch) in cm] if characters is not None else
               [chr(cp) for cp in sorted(cm) if unicodedata.category(chr(cp)).startswith('L') and 'LATIN' in unicodedata.name(chr(cp),'')])
    font=hb.Font(hb.Face(path.read_bytes()));hb.ot_font_set_funcs(font)
    cache={};bad=[];total=0;skipped=0
    def glyph(name):
        if name not in cache:
            p=pathops.Path();gs[name].draw(p.getPen());bp=BoundsPen(None);p.draw(bp);cache[name]=(p,bp.bounds)
        return cache[name]
    for left,right in itertools.product(available,repeat=2):
        text=left+right;b=hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(font,b,features or {})
        if len(b.glyph_infos)!=2:
            skipped+=1;continue
        total+=1;names=[order[g.codepoint] for g in b.glyph_infos]
        pa,ba=glyph(names[0]);pb,bb=glyph(names[1]);positions=b.glyph_positions
        if ba is None or bb is None:continue
        dx=positions[0].x_advance+positions[1].x_offset-positions[0].x_offset
        dy=positions[1].y_offset-positions[0].y_offset
        if min(ba[2],bb[2]+dx)<=max(ba[0],bb[0]+dx) or min(ba[3],bb[3]+dy)<=max(ba[1],bb[1]+dy):continue
        shifted=pathops.Path();pb.draw(TransformPen(shifted.getPen(),(1,0,0,1,dx,dy)))
        intersection=pathops.op(pa,shifted,pathops.PathOp.INTERSECTION,fix_winding=True)
        ap=AreaPen();intersection.draw(ap);area=abs(ap.value)
        if area>tolerance:bad.append(dict(text=text,area=area,glyphs=names,advance=positions[0].x_advance))
    return dict(font=path.name,characters=len(available),pairs_tested=total,skipped_non_pair_shaping=skipped,
        tolerance_square_font_units=tolerance,features=features or {},collisions=len(bad),
        worst=sorted(bad,key=lambda r:r['area'],reverse=True)[:30])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('fonts',nargs='+',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();reports=[]
    for font in args.fonts:
        row=audit_font_pairs(font);reports.append(row)
        print(f'{font.name}: {row["pairs_tested"]} pairs, {row["collisions"]} collisions',flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(dict(method='HarfBuzz default shaping; exact path intersection area; mapped Latin letters only.',
        limitations=['A collision check does not establish even optical spacing, historical authenticity or all possible text behavior.',
                     'Combining sequences without precomposed Latin characters, non-Latin scripts, disabled kerning and application-specific shaping need separate review.'],
        fonts=reports),ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
