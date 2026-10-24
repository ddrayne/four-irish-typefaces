"""Build a separately installable regular candidate; never replace release fonts."""
import argparse,json,os
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--traces',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    os.environ['TRACED']=str(args.traces.resolve());os.environ['OUT']=str(args.output.resolve())
    # The Python distribution bundles the same executable on Windows.
    import ttfautohint
    hint=Path(ttfautohint._executable_path())
    os.environ['PATH']=str(hint.parent)+os.pathsep+os.environ['PATH']
    import build2
    build2.VERSION='2.001'
    build2.FONTS['kilfane']=dict(build2.FONTS['kilfane'],family='Kilfane Study 1',ps='KilfaneStudy1')
    build2.FAMILY_STYLES['kilfane']=['Regular']
    class StudyFont(build2.Font2):
        def build(self,flavour):
            font=super().build(flavour)
            font['name'].setName('Kilfane original-source research candidate. Reconstructed from NIVAL '
                'specimens 516 and 47 with explicitly retained flyer-based entries. New characters, '
                'spacing and text punctuation remain modern constructions; see accompanying evidence.',10,3,1,0x409)
            return font
    f=StudyFont('kilfane','Regular').prepare();f.run()
    # Correct generated provenance: these traces no longer all come from the flyer.
    p=args.output/'KilfaneStudy1-Regular.provenance.json'
    provenance=json.loads(p.read_text(encoding='utf-8'))
    evidence=json.loads((args.traces/'evidence.json').read_text())
    updated={g['name']:g for g in evidence['glyphs'] if g['status']=='candidate'}
    dependencies={**{n:'semicolon' for n in ['period','comma','colon','semicolon','ellipsis','quoteright',
                                           'quoteleft','quotedblleft','quotedblright','quotesinglbase','quotedblbase']},
                  'dotlessi':'i','dotlessj':'j','Euro':'C','uni204A':'seven',**f.comp}
    for name,(kind,construction) in list(provenance.items()):
        g=updated.get(name) or updated.get(dependencies.get(name))
        if not g:continue
        # Keep 'rebuilt' and all construction details (especially punctuation
        # reassembly). Replace only the now-inaccurate source attribution.
        construction=construction.replace('the 1978 flyer','the NIVAL specimen').replace('the flyer’s','the NIVAL specimen’s')
        if kind=='flyer':kind='original-specimen'
        provenance[name]=[kind,construction+f'; source {g["name"]}: NIVAL {g["source"]}, region {g["box"]}; research reconstruction']
    p.write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(glyphs=len(f.final),codepoints=len(f.cm),stem=f.S,metrics=f.vm)))

if __name__=='__main__':main()
