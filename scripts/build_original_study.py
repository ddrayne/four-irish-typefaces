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
    # Céilí Study 4's finishing pass: judged corrections and the studio finish (scripts/ceili_finish.py)
    judged_file=Path(traces).parent/'judged-edits.json'
    judged=json.loads(judged_file.read_text(encoding='utf-8')) if face=='ceili' and judged_file.exists() else {}

    constructions=evidence.get('constructions',{})

    class OriginalStudy(build2.Font2):
        # construction decisions a round records in its evidence (Tuam Study 3): the accented letters that
        # keep their own traced acutes, and braces drawn with a point; absent, the release's constructions
        OWN_ACUTES=tuple(constructions.get('own_acutes',()))
        BRACE_POINT=constructions.get('brace')=='pointed'

        @property
        def J(self):
            # the finishing pass belongs to the finished candidate (FINISH), not to the study's own fonts
            return judged if self.FINISH else {}

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

        def finish_traced(self):
            super().finish_traced()
            if self.J.get('finish',{}).get('regular'):
                # hidden corners smoothed, pen terminals cut straight between sharp corners, clusters of short
                # pieces made one corner, redundant nodes removed (ceili_finish.regular)
                import ceili_finish as CF
                for n,p in list(self.P.items()):
                    if n not in ('DOTS','ornament'):
                        self.P[n]=CF.safely(p,lambda r:CF.regular(r,terminals=bool(self.J.get('pen_terminals'))))
            self.even_stems()
            self.judged_dots()

        def even_stems(self):
            # the second pass: the straight stems given the face's weight, every style following (judged-edits.json)
            spec=self.J.get('second_pass',{}).get('stems')
            if not spec:return
            import ceili_finish as CF
            self.stems_evened={}
            for n,st in spec['glyphs'].items():
                if n in self.P:
                    self.P[n],self.stems_evened[n]=CF.even_stems(self.P[n],st,self.xh,spec['target'],spec['limit'])

        def judged_dots(self):
            # the dots of ! and ? drawn as the face's period, the pen diamond the prints show (judged-edits.json)
            if getattr(self,'dots_done',False) or not self.J.get('pen_diamond'):return
            import ceili_finish as CF,finish as F
            period=next(q for q in punctuation_data['pieces'] if q['name']=='period')
            period=F._contours([(op,[tuple(v) for v in a]) for op,a in period['rec']])[0]
            for n in self.J['pen_diamond']['glyphs']:
                cs=F._contours(CF.recording(self.P[n]))
                lo=min(range(len(cs)),key=lambda i:min(q[1][-1][1] for q in cs[i]))
                cs[lo]=CF.pen_diamond(cs[lo],period)
                self.P[n]=CF.path(F._record(cs))
            self.dots_done=True

        def snap(self):
            super().snap()
            # letters a print set off its line (evidence.json, sit_on_baseline; judged-edits.json) are put on it,
            # flat feet on the baseline and round ones just below it, as snap() does for letters within its tolerance
            for n in {**evidence.get('sit_on_baseline',{}),**self.J.get('sit_on_baseline',{})}:
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
            regular=dict(self.P)
            super().embolden_traced()
            # a dot the wider pen brings within a hair of its stroke is set apart as a joined one is
            import bolden,shapes as SH
            b=build2.BOLD[self.key];pen=(b['rx'],b['ry'])
            share=self.J.get('bold_dot_gap',{}).get('share')
            if share and self.italic:
                share+=self.J['bold_dot_gap'].get('sloped_extra',0)   # the slope's hair of weight takes some back
            for n,p in apart.items():
                wide=[SH.transform(q,(b['k'],0,0,1,0,0)) for q in bolden.components(p) if abs(bolden.area(q))>1]
                core=bolden.heights_back(SH.union(*wide),self.xh,b['ry'])
                self.P[n]=bolden._separate(core,self.P[n],pen,close=True,share=share)
            self.tidy_derived()
            self.bold_second_pass(regular)

        def bold_second_pass(self,regular):
            # the second pass on the bold (judged-edits.json, second_pass; ceili_finish): its heavy level strokes take
            # the stems' gain, its open joins are kept open from the terminal's side only, and the dots of ! and ?
            # reach down no further than the Regular's
            sp=self.J.get('second_pass',{})
            if not sp:return
            import bolden,ceili_finish as CF,shapes as SH
            b=build2.BOLD[self.key];pen=(b['rx'],b['ry'])
            def bolder(p,apertures=True):
                return bolden.embolden(p,b['rx'],b['ry'],b['k'],self.xh,self.S_regular,apertures=apertures,sliver=self.SLIVER)
            def core(p):          # the drawing in the bold's frame, as bolden.embolden makes it
                wide=[SH.transform(q,(b['k'],0,0,1,0,0)) for q in bolden.components(p) if abs(bolden.area(q))>1]
                return bolden.heights_back(SH.union(*wide),self.xh,b['ry'])
            tidy=CF.tidy_path if self.J.get('finish',{}).get('tidy') else (lambda p:p)
            self.second_pass={}
            heavy=sp.get('bold_heavy_strokes')
            if heavy:
                # the letters' crossbars (letters.py) keep the pen's weight, the hyphen's before it is made heavier
                h=build2.bounds(self.P['hyphen']);self.crossbar_weight=h[3]-h[1]
                c=self.xh/(self.xh+2*b['ry'])                     # heights_back's scale through the x-height
                for n,kind in heavy['glyphs'].items():
                    xm,(y0,y1)=CF.level_stroke(regular[n])
                    run=lambda p:max(CF.vertical_runs(p,xm*b['k']),key=lambda r:min(r[1],y1+b['ry'])-max(r[0],y0-b['ry']))
                    was=run(self.P[n]);want=heavy['gain']*(y1-y0)
                    self.P[n]=tidy(bolder(CF.heavier_bar(regular[n],(want-(was[1]-was[0]))/c,kind)))
                    now=run(self.P[n])
                    self.second_pass[n]=dict(regular=round(y1-y0,1),pen=round(was[1]-was[0],1),now=round(now[1]-now[0],1))
            joins=sp.get('bold_joins')
            if joins:
                self.bold_joins={}
                for n in sorted(self.kept_open):
                    necks=[(e[1],e[2]) for e in self.kept_open[n] if e[0]=='aperture' and e[2]<joins['narrow']*self.S_regular]
                    if not necks or n not in regular:continue
                    out,cr,done=bolder(regular[n],apertures=False),core(regular[n]),[]
                    for neck,w in necks:
                        r=CF.terminal_gap(cr,out,pen,neck,max(joins['gap'],bolden.F_PASS*w))
                        if r is None:break
                        out=r[0];done.append(r[1])
                    if len(done)==len(necks) and CF.topology(out)==CF.topology(self.P[n]):
                        self.P[n]=tidy(out);self.bold_joins[n]=done
            feet=sp.get('bold_dot_feet')
            if feet:
                from glyphs import contours
                for n in feet['glyphs']:
                    self.P[n]=tidy(CF.dot_foot(self.P[n],min(build2.bounds(q)[1] for q in contours(regular[n]))))

        def tidy_derived(self):
            # the derived outlines finished: rounding specks folded, the raster-traced reopened joins drawn as
            # curves, corner clusters made one corner, extremes given nodes, redundant nodes removed
            if not self.J.get('finish',{}).get('tidy'):return
            import ceili_finish as CF
            for n,p in list(self.P.items()):
                if n not in ('DOTS','ornament') and build2.bounds(p) is not None:
                    self.P[n]=CF.tidy_path(p)

        def make_marks(self):
            super().make_marks()
            gap=self.J.get('double_acute',{}).get('gap')
            if gap and self.italic:
                gap+=(1-build2.CONDENSE)*self.S           # what the sloped styles' growth will take back
            if gap:
                # the double acute's two fadas kept apart as the Regular keeps them, however wide the pen
                import ceili_finish as CF
                for marks in (self.marks,self.case_marks):
                    marks['hungarumlaut']=CF.spread_pair(marks['hungarumlaut'],gap)

        def composites(self):
            # the finish reaches every glyph before accented letters are composed from them, so a base and
            # its accented forms share one outline: the letters, punctuation and marks now; the symbols below
            if self.J.get('finish',{}).get('tidy'):
                import ceili_finish as CF
                for n,p in list(self.P.items()):
                    if n not in ('DOTS','ornament') and build2.bounds(p) is not None:
                        self.P[n]=CF.tidy_path(p)
                for marks in (self.marks,self.case_marks):
                    for k,m in list(marks.items()):
                        marks[k]=CF.tidy_path(m)
                self.tidied=set(self.P)
            super().composites()
            if self.J.get('finish',{}).get('tidy'):
                self.tidied|=set(self.P)

        def parens_slash_misc(self):
            super().parens_slash_misc()
            cur=self.J.get('second_pass',{}).get('currency')
            if cur:
                # the second pass: € stands with the figures, as tall as the zero (ceili_finish.euro)
                import ceili_finish as CF
                z=build2.bounds(self.P[cur['round']])
                self.P['Euro']=CF.euro(self,z[1],z[3],getattr(self,'crossbar_weight',self.hyphen_thick))
                self.made['Euro']=self.made['Euro']+f', as tall as the {cur["round"]}'

        def figure_symbols(self):
            # the second pass: ¥ stands with the figures, as tall as the £, and the bold's § takes the bold's weight
            sp=self.J.get('second_pass',{})
            import ceili_finish as CF
            top=self.fig if self.cfg['lining'] else self.xh*1.05          # symbols.make_symbols' figure-size height
            rings=sp.get('bold_heavy_strokes',{}).get('pen_weight')
            if rings and getattr(self,'crossbar_weight',None):
                # the rings keep the pen's weight, as the crossbars do: the same constructions drawn again with it
                import symbols
                P,t=self.P,self.hyphen_thick
                self.P,self.hyphen_thick=dict(P),self.crossbar_weight
                try:symbols.make_symbols(self)
                finally:light,self.P,self.hyphen_thick=self.P,P,t
                for n in rings:P[n]=light[n]
            cur=sp.get('currency')
            if cur:
                self.P['yen']=CF.yen(self,top,build2.bounds(self.P[cur['flat']])[3],getattr(self,'crossbar_weight',self.hyphen_thick))
                self.made['yen']=self.made['yen']+f', as tall as the {cur["flat"]}'
            if sp.get('bold_section') and self.bold:
                import symbols
                sec=symbols.section(self.P['s'],self.S,self.S,top)
                if sec is not None:
                    self.P['section']=self.norm_x(sec);self.made['section']+=', at the bold\'s full weight'

        def combining_and_spacing_marks(self):
            self.figure_symbols()
            self.close_cracks()
            if self.J.get('finish',{}).get('tidy'):
                import ceili_finish as CF
                for n,p in list(self.P.items()):
                    if n not in self.tidied and build2.bounds(p) is not None:
                        self.P[n]=CF.tidy_path(p)
            super().combining_and_spacing_marks()

        def space(self,K):
            super().space(K)
            bars=self.J.get('second_pass',{}).get('bar_spacing')
            if bars:
                # the second pass: ð and đ spaced as d, by one rule in every style (ceili_finish.bar_spacing)
                import ceili_finish as CF
                self.bars_spaced={n:CF.bar_spacing(self,n,base,bars['min_lsb']) for n,base in bars['glyphs'].items() if n in self.P}
            if not self.J.get('finish',{}).get('tidy'):return
            # a short curve or corner that rounding to the grid turned into facets is drawn again
            for n,p in list(self.final.items()):
                if build2.bounds(p) is not None:
                    self.final[n]=self.unfaceted(p)

        def unfaceted(self,p):
            import ceili_finish as CF
            for _ in range(2):
                if not CF.polygonal(CF.recording(p)):break
                p=build2.final_clean(CF.safely(p,CF.unpolygon))
            return p

        def slant(self):
            super().slant()
            if not self.J.get('finish',{}).get('tidy'):return
            # the shear moves every extreme off its node: extremes get nodes again, then the redundant ones go
            import ceili_finish as CF
            for n,p in list(self.final.items()):
                if build2.bounds(p) is not None:
                    self.final[n]=self.unfaceted(build2.final_clean(CF.safely(p,CF.sloped)))

        def condense(self):
            before=dict(self.P) if self.J.get('finish',{}).get('tidy') else {}
            self.condense_growth()
            if before:
                # the slope's hair of weight never joins what the upright keeps apart: where it closes a
                # narrow opening its protection misses (the yen's, in the Bold Italic), the glyph is only narrowed
                import ceili_finish as CF,shapes as SH
                for n,p in before.items():
                    if build2.bounds(p) is not None and CF.topology(self.P[n])!=CF.topology(p):
                        self.P[n]=SH.transform(p,(build2.CONDENSE,0,0,1,0,0))
                self.sloped_joins(before)
                self.close_cracks()
            self.tidy_derived()

        def close_cracks(self):
            # the second pass: a crack the bold leaves narrower than close_under, cutting a counter off, is closed
            # instead, as the bold's 6 is (ceili_finish.close_cracks); run on every glyph of the bold styles
            joins=self.J.get('second_pass',{}).get('bold_joins')
            if not joins or not self.bold:return
            import ceili_finish as CF
            self.cracks_closed=getattr(self,'cracks_closed',{})
            for n,p in list(self.P.items()):
                if n in ('DOTS','ornament') or build2.bounds(p) is None:continue
                q,k=CF.close_cracks(p,joins['close_under'])
                if k:
                    self.P[n]=CF.tidy_path(q) if self.J.get('finish',{}).get('tidy') else q
                    self.cracks_closed[n]=self.cracks_closed.get(n,0)+k

        def sloped_joins(self,before):
            # the second pass: the Bold Italic's hair of weight narrows the Bold's reopened joins; they are cut back
            # from the terminal again, in the letter and in every glyph drawn from it (ḃ, þ, ĸ, ð ...)
            joins=getattr(self,'bold_joins',{})
            if not joins:return
            import bolden,ceili_finish as CF,shapes as SH,pathops
            rx=(1-build2.CONDENSE)*self.S/2;narrow=lambda p:SH.transform(p,(build2.CONDENSE,0,0,1,0,0))
            def near(p,c,r=60):
                return SH.op(p,SH.circle(c[0],c[1],r),pathops.PathOp.INTERSECTION)
            self.sloped_joined={}
            for n,done in joins.items():
                necks=[(d['neck'][0]*build2.CONDENSE,d['neck'][1],d['gap']) for d in done]
                ref=[near(narrow(before[n]),c) for c in necks]
                for g,p in before.items():
                    if build2.bounds(p) is None or not all(abs(bolden.area(SH.op(near(narrow(p),c),r_,pathops.PathOp.XOR)))<1
                                                           for c,r_ in zip(necks,ref)):
                        continue
                    q,out,ok=narrow(p),self.P[g],True
                    for x,y,gap in necks:
                        r=CF.terminal_gap(q,out,(rx,0.5),(x,y),gap)
                        if r is None:ok=False;break
                        out=r[0]
                    if ok and CF.topology(out)==CF.topology(self.P[g]):
                        self.P[g]=out;self.sloped_joined[g]=n

        def condense_growth(self):
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
            if self.J.get('quote_kerning'):
                import ceili_finish as CF
                CF.quote_kerning(self,self.J['quote_kerning']['share'],over_foot='quote_over_foot' in self.J.get('second_pass',{}))
            from study_spacing import protect_kerning
            protect_kerning(self)

        def specimen_pieces(self):
            if piece_data is None:return super().specimen_pieces()
            self.P.pop('ornament',None);self.piece={}
            for record in piece_data['pieces']:
                p=pathops.Path();replayRecording(record['rec'],p.getPen())
                self.piece[record['name']]=clean(p)
            self.made['accents']=piece_data.get('decision','named original-source marks; see pieces.json; ambiguous lower pair is unassigned')
            if self.bold and getattr(self,'BOLD_PIECES',False):
                # the pieces arrive after the letters were bolded: Kilfane's finishing draws them with the bold's pen too
                import kilfane_studio;kilfane_studio.bold_pieces(self)

        def attach(self,base_name,base,mark_kind,upper,stack_top=None):
            m=super().attach(base_name,base,mark_kind,upper,stack_top)
            if getattr(self,'MARK_ON_LINE',False) and mark_kind not in build2.BOTTOM and mark_kind!='caronvert' and stack_top is None:
                # Kilfane's finishing: a mark narrower than an open letter's counter (the ring on U) found the counter's
                # floor; it is set over the letter's top as the acute's wider window finds it
                line=self.cap if upper else self.xh;b=build2.bounds(m)
                gap=self.gap*(0.85 if upper else 1.0)*(1.4 if mark_kind=='commaturned' else 1.0)
                if b[1]-gap<0.8*line:
                    a=build2.bounds((self.case_marks if upper else self.marks)['acute']);cx=(b[0]+b[2])/2;half=(a[2]-a[0])/2
                    m=build2.translate(m,0,build2.top_under(base,cx-half,cx+half)+gap-b[1])
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
                    if any(p['name']=='dieresis.l' and p['status']=='judged' for p in piece_data['pieces']):
                        return 'diaeresis; the lower paired NIVAL N513 component, identified by judgement, its two dots parted at their neck and set apart (pieces.json)'
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
    one=getattr(f,'ONE_CHEVRON',None)       # every guillemet from one of the sheet's chevrons (Carrick's fourth pass)
    if one:piece_sources.update({g+s:one+('' if g=='guilsingl' else ' + '+one[:-1]+'2') for g in ('guilsingl','guillemot') for s in ('left','right')})
    own_acutes=evidence.get('constructions',{}).get('own_acutes',[])
    def source_words(g):
        region=g['box'] if 'box' in g else f'{len(g.get("boxes",[]))} impressions on the {g.get("sheet","")} sheet'
        words=f'NIVAL {g["source"]}, region {region}'
        if 'check' in g:      # a consensus of two prints (Tuam Study 3)
            words+=f', averaged with NIVAL {g["check"]["source"]}, region {g["check"]["box"]}'
        return words
    for name,(kind,construction) in list(provenance.items()):
        if name in own_acutes and name in updated:
            construction+=f'; the acute as printed on {name}: '+source_words(updated[name])
            provenance[name]=[kind,construction]
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
        provenance[name]=[kind,construction+f'; base source {g["name"]}: '+source_words(g)]
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
