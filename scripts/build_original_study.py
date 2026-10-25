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

    class OriginalStudy(build2.Font2):
        def punctuation(self):
            if punctuation_data is not None:
                self.source_punctuation={}
                for record in punctuation_data['pieces']:
                    p=pathops.Path();replayRecording(record['rec'],p.getPen())
                    self.source_punctuation[record['name']]=clean(p)
            super().punctuation()
            if punctuation_data is not None:
                for name in ['period','comma','quoteleft','quoteright']:
                    record=next(p for p in punctuation_data['pieces'] if p['name']==name)
                    self.made[name]=f'named NIVAL N45 {name}; region {record["box"]}; text position adjusted'
                self.made.update(colon='two NIVAL N45 periods; modern text placement',
                    semicolon='NIVAL N45 comma and period; modern text placement',
                    ellipsis='three NIVAL N45 periods; modern text spacing',
                    quotedblleft='two NIVAL N45 opening quotes; modern text spacing',
                    quotedblright='two NIVAL N45 closing quotes; modern text spacing',
                    quotesingle='modern wedge; width calibrated to named NIVAL N45 period',
                    quotedbl='two modern wedges; width calibrated to named NIVAL N45 period')

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

        def mark_words(self,kind):
            description=super().mark_words(kind)
            if punctuation_data is not None:
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
        provenance[name]=[kind,construction+f'; base source {g["name"]}: NIVAL {g["source"]}, region {g["box"]}']
    path.write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--face',choices=['kilfane','carrick','tuam','ceili'],required=True)
    ap.add_argument('--study',type=int,required=True);ap.add_argument('--traces',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    os.environ['TRACED']=str(args.traces.resolve());os.environ['OUT']=str(args.output.resolve())
    import ttfautohint
    os.environ['PATH']=str(Path(ttfautohint._executable_path()).parent)+os.pathsep+os.environ['PATH']
    import build2
    cfg=build2.FONTS[args.face]
    build2.VERSION=f'2.{args.study:03d}'
    build2.FONTS[args.face]=dict(cfg,family=f'{cfg["family"]} Study {args.study}',ps=f'{cfg["ps"]}Study{args.study}')
    build2.FAMILY_STYLES[args.face]=['Regular']
    OriginalStudy,evidence,piece_data=study_class(args.face,args.traces)
    f=OriginalStudy(args.face,'Regular').prepare();base=f.run()
    update_provenance(base,f,cfg,evidence,piece_data)
    (args.output/'spacing-adjustments.json').write_text(json.dumps(dict(
        method='Full-height one-unit silhouette sampling, two-unit vertical allowance, eight-unit minimum horizontal clearance; verified separately on shaped binaries.',
        changes=f.spacing_protection),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(face=args.face,study=args.study,glyphs=len(f.final),codepoints=len(f.cm),stem=f.S,metrics=f.vm)))


if __name__=='__main__':main()
