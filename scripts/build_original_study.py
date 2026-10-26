"""Build a separate research Regular with optional explicitly named source marks."""
import argparse,copy,json,os
from pathlib import Path


def study_class(face,traces):
    """The original-source construction of one face: build2.Font2 with the round's named marks,
    punctuation and evidence decisions. TRACED must already name `traces` (build2 reads it on import)."""
    import build2
    from glyphs import clean
    from fontTools.pens.recordingPen import replayRecording
    import pathops
    evidence=json.loads((traces/'evidence.json').read_text(encoding='utf-8'))
    piece_file=traces/'pieces.json'
    piece_data=json.loads(piece_file.read_text(encoding='utf-8')) if piece_file.exists() else None
    punctuation_file=traces/'punctuation.json'
    punctuation_data=json.loads(punctuation_file.read_text(encoding='utf-8')) if punctuation_file.exists() else None
    if punctuation_data is not None and face!='ceili':raise ValueError('named punctuation is currently defined only for Ceili')
    source_acute=next((p for p in punctuation_data['pieces'] if p['name']=='acute' and p.get('use')=='built'),None) if punctuation_data else None
    derived=evidence.get('derived_styles',{})    # Céilí Study 4: two judged repairs to the derived styles

    class OriginalStudy(build2.Font2):
        def __init__(self,key,style_name='Regular'):
            fixed=evidence.get('line_baselines')
            if not fixed:
                return super().__init__(key,style_name)
            # Céilí Study 4: each source line's baseline as Study 3 measured it. The builder takes a line's
            # baseline as the median of its letters' bottoms, which moves with the overshoots of the round
            # and pointed ones; the redrawn letters keep Study 3's frame, so their line does too
            import glyphs,metrics
            fixed={int(k):float(v['baseline']) for k,v in fixed.items()}
            measured=metrics.line_baselines
            def pinned(res):
                measured(res);return dict(fixed)
            glyphs.line_baselines=metrics.line_baselines=pinned
            try:super().__init__(key,style_name)
            finally:glyphs.line_baselines=metrics.line_baselines=measured

        def snap(self):
            super().snap()
            # letters a print set off its line (evidence.json, sit_on_baseline) are put on it, flat feet on the
            # baseline and round ones just below it, as snap() does for letters within its tolerance
            for n in evidence.get('sit_on_baseline',{}):
                if n not in self.P:continue
                p=self.P[n];y0=build2.bounds(p)[1]
                over=0 if self.flat(p,y0,0.015*self.xh,top=False) else 8
                self.P[n]=build2.translate(p,0,-y0-over)

        def punctuation(self):
            if punctuation_data is not None:
                self.source_punctuation={}
                for record in punctuation_data['pieces']:
                    p=pathops.Path();replayRecording(record['rec'],p.getPen())
                    self.source_punctuation[record['name']]=clean(p)
            super().punctuation()
            if punctuation_data is not None:
                src={}
                for name in ['period','comma','quoteleft','quoteright']:
                    record=next(p for p in punctuation_data['pieces'] if p['name']==name)
                    src[name]=record.get('source_id','N45')
                    self.made[name]=f'named NIVAL {src[name]} {name}; region {record["box"]}; text position adjusted'
                self.made.update(colon=f'two NIVAL {src["period"]} periods; modern text placement',
                    semicolon=f'NIVAL {src["comma"]} comma and period; modern text placement',
                    ellipsis=f'three NIVAL {src["period"]} periods; modern text spacing',
                    quotedblleft=f'two NIVAL {src["quoteleft"]} opening quotes; modern text spacing',
                    quotedblright=f'two NIVAL {src["quoteright"]} closing quotes; modern text spacing',
                    quotesingle=f'modern wedge; width calibrated to named NIVAL {src["period"]} period',
                    quotedbl=f'two modern wedges; width calibrated to named NIVAL {src["period"]} period')
                # Céilí Study 4: the sheet's síneadh fada, identified by judgement, is the acute (and the marks made from it)
                if source_acute is not None:
                    a=self.source_punctuation['acute']
                    self.piece['acute']=self.bold_pieces(a) if self.bold else a

        def hairlines(self):
            disabled=set(evidence.get('disable_legacy_hairlines',[]))
            if disabled:
                self.HAIRLINES=copy.deepcopy(self.HAIRLINES)
                config=self.HAIRLINES.get(self.key,{})
                config['pinch']=tuple(n for n in config.get('pinch',()) if n not in disabled)
                config['bridge']={n:v for n,v in config.get('bridge',{}).items() if n not in disabled}
            super().hairlines()

        def repairs(self):
            if self.key=='ceili' and 'h' in evidence.get('disable_legacy_repairs',[]):return
            super().repairs()

        def embolden_traced(self):
            apart={n:self.P[n] for n in derived.get('bold_keep_apart',{}).get('glyphs',()) if n in self.P}
            super().embolden_traced()
            if not apart:return
            # a dot the wider pen brings within a hair of its stroke is set apart as a joined one is
            import bolden,shapes as SH
            b=build2.BOLD[self.key];pen=(b['rx'],b['ry'])
            for n,p in apart.items():
                wide=[SH.transform(q,(b['k'],0,0,1,0,0)) for q in bolden.components(p) if abs(bolden.area(q))>1]
                core=bolden.heights_back(SH.union(*wide),self.xh,b['ry'])
                self.P[n]=bolden._separate(core,self.P[n],pen,close=True)

        def condense(self):
            if not derived.get('sound_sloped_growth'):return super().condense()
            # pathops can resolve the sloped pen's inner loops wrongly, losing part of a letter (oe's e);
            # the same outline, simplified first, grows soundly
            import bolden
            grow=bolden.grow
            def sound(p,rx,ry,miter=4.0):
                g=grow(p,rx,ry,miter)
                if bolden._sound(p,g):return g
                h=grow(pathops.simplify(p,fix_winding=True,keep_starting_points=False,clockwise=False),rx,ry,miter)
                return h if bolden._sound(p,h) else g
            bolden.grow=sound
            try:super().condense()
            finally:bolden.grow=grow

        def kerning(self):
            super().kerning()
            from study_spacing import protect_kerning
            protect_kerning(self)

        def specimen_pieces(self):
            if piece_data is None:return super().specimen_pieces()
            self.P.pop('ornament',None);self.piece={}
            for record in piece_data['pieces']:
                p=pathops.Path();replayRecording(record['rec'],p.getPen())
                self.piece[record['name']]=clean(p)
            self.made['accents']=piece_data.get('decision','named original-source marks; see pieces.json; ambiguous lower pair is unassigned')

        def attach(self,base_name,base,mark_kind,upper,stack_top=None):
            m=super().attach(base_name,base,mark_kind,upper,stack_top)
            if source_acute is None or mark_kind in build2.BOTTOM or mark_kind=='caronvert' or stack_top is not None:return m
            # Céilí Study 4: the sheet's fada is narrower than the drawn acute it replaces, and over an open
            # letter (u, v, w, y) the window under it found the counter: clear the letter's top across at
            # least half an x-height, as the drawn acute did
            b=build2.bounds(m);cx=(b[0]+b[2])/2;half=max(b[2]-b[0],0.5*self.xh)/2
            t=build2.top_under(base,cx-half,cx+half)+self.gap*(0.85 if upper else 1.0)*(1.4 if mark_kind=='commaturned' else 1.0)
            return build2.translate(m,0,t-b[1]) if t>b[1] else m

        def mark_words(self,kind):
            description=super().mark_words(kind)
            if punctuation_data is not None:
                if source_acute is not None and kind=='acute':
                    return f'acute (síneadh fada); named NIVAL {source_acute["source_id"]} piece, identified by judgement (punctuation.json)'
                if source_acute is not None and kind in {'grave','hungarumlaut'}:
                    return f'{self.MARK_WORDS[kind]}; modern construction from the named NIVAL {source_acute["source_id"]} fada'
                if kind in {'commabelow','commaturned'}:
                    return f'{self.MARK_WORDS[kind]}; modern transformation of the named NIVAL N45 comma'
                if kind=='caronvert':
                    return 'apostrophe caron; modern transformation of the named NIVAL N45 quoteright'
                if kind=='dot':
                    return 'dot; modern placement of the named NIVAL N45 period'
                if kind=='dieresis':
                    return 'diaeresis; modern scaled pair of the named NIVAL N45 period'
            if piece_data is None:
                if self.key=='tuam' and kind in {'acute','grave','hungarumlaut'}:
                    record=next((g for g in evidence['glyphs'] if g['name']=='uacute' and g['status']=='candidate'),None)
                    if record:
                        operation='taken' if kind=='acute' else 'constructed'
                        return f'{self.MARK_WORDS[kind]} {operation} from the accent on uacute; mark source NIVAL {record["source"]}, region {record["box"]}'
                return description
            word=self.MARK_WORDS[kind]
            if self.key=='carrick':
                if kind in {'acute','tilde','dot','ring','circumflex'}:
                    return f'{word}; directly traced NIVAL N513 {kind} in pieces.json'
                if kind=='dieresis':
                    return 'diaeresis retained from legacy construction; N513 lower paired component remains unassigned'
                if kind in {'grave','hungarumlaut','breve','caron'}:
                    parent={'grave':'acute','hungarumlaut':'acute','breve':'ring','caron':'circumflex'}[kind]
                    return f'{word}; modern construction from named NIVAL N513 {parent}'
                if kind=='macron':
                    return 'macron drawn as a modern straight rule at the mean weight of the two NIVAL N513 rules'
                if kind in {'commabelow','commaturned','caronvert'}:
                    return f'{word}; modern transformation of NIVAL N513 semicolon punctuation'
                if kind in {'ogonek','cedilla'}:
                    return f'{word}; modern drawn mark, stroke weight calibrated from NIVAL N513 ring'
                return description+'; modern construction'
            direct={'acute':['acute'],'tilde':['tilde'],'dot':['dot'],'ring':['ring'],
                    'circumflex':['circumflex'],'dieresis':['dieresis.l','dieresis.r']}
            derived={'grave':'acute','hungarumlaut':'acute','breve':'ring','caron':'circumflex'}
            if kind in direct:
                return f'{word}; marks: NIVAL N516 named components '+', '.join(direct[kind])+' in pieces.json'
            if kind=='macron':
                return 'macron constructed as a straight rule at the NIVAL N516 endash weight; modern length and geometry, not a traced macron'
            if kind in derived:
                return f'{word} made from the NIVAL N516 {derived[kind]}; modern construction using named marks in pieces.json'
            if kind in {'commabelow','commaturned','caronvert'}:
                return f'{word}; modern scaled/repositioned punctuation derived from the NIVAL N516 semicolon, not the loose-mark cluster'
            if kind in {'ogonek','cedilla'}:
                return f'{word}; modern drawn mark; stroke weight calibrated from the NIVAL N516 ring'
            return description+'; modern construction'

        def build(self,flavour):
            f=super().build(flavour)
            f['name'].setName('Original-source research candidate. Source regions, retained legacy forms, '
                'modern constructions and uncertainties are recorded in accompanying evidence files.',10,3,1,0x409)
            return f
    return OriginalStudy,evidence,piece_data


def update_provenance(base,f,cfg,evidence,piece_data):
    """Attribute a built style's glyphs to the NIVAL regions their source traces came from."""
    path=Path(base+'.provenance.json')
    provenance=json.loads(path.read_text(encoding='utf-8'))
    updated={g['name']:g for g in evidence['glyphs'] if g['status']=='candidate'}
    deps={**{n:'semicolon' for n in ['period','comma','colon','semicolon','ellipsis','quoteright','quoteleft',
          'quotedblleft','quotedblright','quotesinglbase','quotedblbase']},'dotlessi':'i','dotlessj':'j',
          'Euro':'c' if cfg['unicase'] else 'C','uni204A':'seven',**f.comp}
    piece_sources={'degree':'ring','guilsinglright':'guil.r1','guilsinglleft':'guil.l1',
                   'guillemotright':'guil.r1 + guil.r2','guillemotleft':'guil.l1 + guil.l2'}
    for name,(kind,construction) in list(provenance.items()):
        if piece_data is not None and name in piece_sources:
            source_id=piece_data.get('primary_source_id','N516')
            detail=piece_sources[name]
            if source_id=='N513':
                lookup={p['name']:p for p in piece_data['pieces']}
                detail=' + '.join(n+' ('+lookup[n]['status']+')' for n in detail.split(' + '))
            provenance[name]=[kind,construction+f'; named source pieces: NIVAL {source_id} '+detail]
        g=updated.get(deps.get(name,name))
        if not g:continue
        construction=construction.replace('the 1978 flyer','the NIVAL specimen').replace('the flyer’s','the NIVAL specimen’s')
        if kind=='flyer':kind='original-specimen'
        region=g['box'] if 'box' in g else f'{len(g.get("boxes",[]))} impressions on the {g.get("sheet","")} sheet'
        provenance[name]=[kind,construction+f'; base source {g["name"]}: NIVAL {g["source"]}, region {region}']
    path.write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--face',choices=['kilfane','carrick','tuam','ceili'],required=True)
    ap.add_argument('--study',type=int,required=True);ap.add_argument('--traces',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    os.environ['TRACED']=str(args.traces.resolve());os.environ['OUT']=str(args.output.resolve())
    try:  # ttfautohint-py bundles the binary; otherwise the system's ttfautohint on PATH is used
        import ttfautohint
        os.environ['PATH']=str(Path(ttfautohint._executable_path()).parent)+os.pathsep+os.environ['PATH']
    except ImportError:
        pass
    import build2
    cfg=build2.FONTS[args.face]
    build2.VERSION=f'2.{args.study:03d}'
    # studies are named after the design ("Kilfane Study 3"), not the release family ("Kilfane Digital")
    name,ps=cfg.get('name',cfg['family']),cfg['ps'].removesuffix('Digital')
    build2.FONTS[args.face]=dict(cfg,name=f'{name} Study {args.study}',family=f'{name} Study {args.study}',ps=f'{ps}Study{args.study}')
    build2.FAMILY_STYLES[args.face]=['Regular']
    OriginalStudy,evidence,piece_data=study_class(args.face,args.traces)
    f=OriginalStudy(args.face,'Regular').prepare();base=f.run()
    update_provenance(base,f,cfg,evidence,piece_data)
    (args.output/'spacing-adjustments.json').write_text(json.dumps(dict(
        method='Full-height one-unit silhouette sampling, two-unit vertical allowance, eight-unit minimum horizontal clearance; verified separately on shaped binaries.',
        changes=f.spacing_protection),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(face=args.face,study=args.study,glyphs=len(f.final),codepoints=len(f.cm),stem=f.S,metrics=f.vm)))


if __name__=='__main__':main()
