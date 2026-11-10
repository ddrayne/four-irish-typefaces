# Four Irish Typefaces: brief for the next steward

*Paste this into a new session with the repository `ddrayne/four-irish-typefaces` attached. It is
self-contained; the files it names hold the detail.*

---

You are taking over **Four Irish Typefaces**: open, public-domain (CC0) digital revivals of the four
winners of the 1978 *Design an Irish Typeface* competition, sold then as Letraset dry-transfer sheets:
**Céilí** (Hermann Hecht, first prize), **Carrick** and **Kilfane** (William Curran) and **Tuam
Uncial** (Jarlath Hayes). They are released as Céilí Digital, Carrick Digital, Kilfane Digital and
Tuam Uncial Digital, twelve styles in all. The italics and bolds are 2026 work; only the regulars
existed in 1978. There is also a showcase website (https://irish-typefaces.apps.drayne.xyz).
Version 3.100 is released and passes 568 tests.

## Your mission

Do two things at once, and treat both as open research:

1. **Make these the best possible revivals of the 1978 designs**: faithful to what the designers
   drew, and excellent to set type with.
2. **Make the showcase the best possible demonstration of them**: what they are, where they came
   from, and how to use them.

Previous work went as far as careful scripted passes and independent reviews could take it. You
have more capability. Use it to find out where the real limits are: try approaches that weren't
tried, measure whether they help, keep what does, and say plainly what didn't. Form your own view of
the weakest points; don't treat the lists below as complete or as orders.

## Where things stand

**Sources.** Up to 2.101 the fonts were traced from a 97 dpi photocopy of the competition flyer.
Since 3.000 each face has been redrawn from original prints in the William Curran Archive at the
National Irish Visual Arts Library (NIVAL):

- **Kilfane:** the N516 specimen, with its capitals averaged over the impressions on its Letraset
  production sheet (N517).
- **Carrick:** the N513 specimen and the impressions on its two production sheets (N514).
- **Tuam Uncial and Céilí:** the mean of a sharper scan of the flyer (N46) and the competition
  brochure (N45). Céilí's disagreements are decided by a third print (N44).

No production sheet has been found for Tuam (S53911/S53912) or Céilí (S53915/S53916).
`research/SOURCE-ACCESS.md` and the README's "Making them better" list the leads.

**Pipeline.**
- The research studies in `research/` feed `scripts/build_candidate.py`, which builds each face
  from its latest study, then applies finishing passes:
  - `kilfane_studio.py`, `tuam_studio.py`, `carrick_studio.py` with `settle.py`, and `ceili_finish.py`;
  - shared rules in `symbols.py` and `build2.py`.
- `scripts/release.py` puts the result in `fonts/` and regenerates `css/` and `index.html`.
- Every judged correction is recorded with its reason and numbers in the face's
  `judged-edits.json` and README. A test pins it.
- `make help` lists everything else: proof and tester PDFs, specimen, validation, showcase, deploy.

**Finishing so far.**
- Five passes, each driven by an independent type review that saw only the font outlines, then a
  final regression review against the previous release.
- What they did:
  - settled outlines on the grid;
  - drew the bolds' marks, rules and small signs with the bold's pen;
  - rebuilt the signs so they sit with each face: # % ‰ £ $ ¢ ≈ © ® ° ¤ @ and the brackets;
  - added kerning clearances, mark stacking (mkmk), Kilfane's `case` feature and U+0323;
  - corrected Tuam's word space.
- `FONTLOG.txt` 3.100 summarises it all.

**Showcase.** It lives in `showcase/` and is built by `scripts/showcase.py`; CI deploys it from
`main`. It has:
- a hero;
- a world for each face, with a toy that plays with its letters;
- a poster maker and a type tester;
- glyph grids;
- a flyer section that overlays both the first tracing and the 3.100 letters on the 1978 scan,
  using `docs/validation/flyer-registration.json`, which `scripts/validate.py` writes;
- per-face study panels;
- downloads, which are GitHub release assets.

**Open questions and known gaps.**

- **Nine design questions** print at the end of the proof (`make proof`). Each needs new evidence
  or the user's judgement:
  1. Tuam's í fada.
  2. Céilí's ampersand.
  3. Céilí's weight.
  4. Tuam's slits.
  5. Kilfane's serifs.
  6. Carrick's £ and $ heights.
  7. Figures that break the line.
  8. The ponc (the dot of lenition).
  9. Small figures in the bolds.

  The heaviest is Céilí's weight. It is drawn about a fifth heavier than the flyer copy (median area
  +20%), calibrated between two prints whose stems differ by about 10%.
- **Known small defects:**
  - combining marks on barred and stroked letters collide (e.g. ł + U+0301, in every style);
  - Céilí's ss03 ĵ doesn't follow its j;
  - a few near-touches under 8 units (Kilfane k j; Italic P?; Bold Italic ?? and q j);
  - a few accented capitals rise above the typo ascender (Carrick Ĺ ĺ; Tuam and Céilí Ĥ ĥ; Céilí's
    ss01 š ŝ);
  - Kilfane Bold's comma below reaches past the line box.
- **Next priorities** in `research/HANDOFF.md`:
  - optical spacing and small-size rendering across applications;
  - Kilfane's fused letters, zero and ambiguous lower marks;
  - Carrick's e f x y;
  - unassigned Céilí punctuation pieces;
  - Tuam's recomposed accents.
- **Never tested:** Word, InDesign or Figma, and Windows rendering (DirectWrite and GDI) at small
  sizes. The TrueType files are hinted with ttfautohint.

## Non-negotiables

- **Fidelity to 1978 is the target.**
  - Modern revival fonts are never design references.
  - Keep three things distinct, and say which is which: attested shapes, reconstructions, and modern
    extensions. The modern extensions are the italics, the bolds and every glyph the sheets never had.
  - Read the AGENTS.md rules on recording sources, transforms and uncertainty.
- **Rights.**
  - Read `research/RIGHTS.md`.
  - Archive scans, and anything containing their pixels, stay in the ignored `build/` folder and are
    never committed. Proofs that show only font outlines are fine.
  - The fonts are CC0, and their family names keep "Digital".
- **Every design change is a recorded judgement:**
  - the reason, with before and after numbers, in the face's `judged-edits.json` and README;
  - a test that fails before the change and passes after it.
  - Prefer a rule to a per-glyph patch, but prove the rule regresses nothing else. The fifth pass's
    ring rule grew ° into a bullet and lifted © ® above the figures, and only the regression review
    caught it.
- **Test what the eye sees, not just structure.** Check counter areas, opening widths and
  clearances. Carrick's ® once passed a topology test while its bowl filled in.
- **Reproducibility.**
  - CI rebuilds the fonts and requires them byte-identical. `build_candidate.py` pins numpy's and
    OpenBLAS's CPU dispatch to make that possible; keep it.
  - After any font change, rebuild all four faces and compare all 48 files.
- **Releases.**
  - A push to `main` whose `scripts/build2.py` VERSION has no GitHub release publishes one at once,
    with the notes taken from the first FONTLOG entry. Don't push a version bump until `fonts/`, the
    tests, FONTLOG and the README are final.
  - Park unfinished work on a branch.
  - Run `scripts/validate.py` after changing outlines: it regenerates the flyer audit and the
    registration the showcase uses.
- **Git.**
  - Commit messages say what changed and why, with numbers.
  - Use the attribution lines your environment specifies.
  - Never put model identifiers in anything committed.
- **Irish.**
  - Write only correct Irish, and remember how easy it is to get wrong. For example, autonomous past
    forms like *tógadh* take no lenition.
  - Prefer attested texts. When you compose, keep it simple and flag it for a fluent reader.
  - No tourist or fairy-tale clichés: no Tír na nÓg, céad míle fáilte or craic. The user wants real
    history: places, manuscripts, annals, people.

## What the user values

- **Steady improvement towards the best possible fonts.** Not process for its own sake: they once
  asked to drop an over-engineered versioning and release scheme.
- **Toys that are playful and show off the letterforms.** They rejected an animation that was too
  musical, and letters dropped in a heap where you couldn't see them.
- **Honesty.** Every claim on the site and in the docs must be true now; they caught the flyer copy
  going stale. Measure, don't assert.
- **Things they can see.** They like printed proof and tester PDFs and before/after images, and
  they comment directly on the showcase preview.
- **Short, plain updates.** They make the design calls the evidence can't, so bring those as clear
  side-by-side choices.

## Where to push the boundaries

These are directions, not a checklist. Choose by expected gain against risk, and say why.

**A. Fidelity research**
- Model each print process: dry transfer, the offset-printed brochure, and the photocopy, each with
  its own ink spread and erosion. Infer the drawn letter from several prints, rather than averaging
  them, and quantify each glyph's uncertainty.
- Settle the proof questions with evidence where you can. Bring the rest to the user as side-by-side
  comparisons.
- Hunt for the missing sources: the Tuam and Céilí sheets, Letraset catalogues, Fonts In Use,
  Bolger's thesis, McGuinne's *Irish Type Design*. `scripts/fetch_sources.py` keeps fetched sources
  out of the repository.

**B. Type quality**
- Judge spacing and kerning in real text at real sizes. Build a text-weighted spacing measure and an
  optical review, beyond pair metrics.
- Test rendering at 9–16 px with FreeType/HarfBuzz, in Chromium and in LibreOffice, and on Windows
  if you can. Improve the hinting where it matters.
- Fix the known defects.
- Add OpenType only where it serves Irish typesetting, grounded in practice: fractions, figure
  styles where meaningful, contextual insular forms, old-orthography support.
- A variable weight axis for Céilí and Kilfane needs masters that match point for point; the bolds
  are currently emboldened outlines. Attempt it only if it can meet the same standard.

**C. Showcase**
- Make the provenance tangible. Let a visitor see, glyph by glyph, which print a letter came from,
  how certain it is, and every judged correction; `judged-edits.json` already holds the data. Show
  no archive pixels publicly unless the rights allow.
- New ways to feel and use the type:
  - a printable Letraset-style transfer-sheet generator;
  - a specimen book;
  - the faces in the context of 1970s Irish design. Keep that illustrative: never a facsimile of
    currency or a real brand.
- Performance, accessibility and phones matter as much as spectacle.

**D. Evaluation and process**
- Before changing anything, write down how you will judge it: metrics plus blinded visual
  comparisons. Keep a scorecard across versions.
- Independent reviewers who see only the outlines, not your reasoning, find real defects. Run one
  before every release, plus a regression review against the previous release.
- Use parallel agents for independent faces or tracks. Merge, rebuild and verify their work
  yourself.

## How to start

1. **Read:**
   - `README.md`, `FONTLOG.txt`, `AGENTS.md`;
   - `research/HANDOFF.md` and `research/RIGHTS.md`;
   - each face's `judged-edits.json` and README;
   - skim `scripts/build_candidate.py` and `scripts/symbols.py`.
2. **Reproduce:** run `make setup`, `make fonts`, and compare with `fonts/`; then `make test`,
   `make proof`, `make tester`, `make showcase`.
3. **Look** at every page of the proof and at the showcase yourself, before reading anyone's
   conclusions.
4. **Write a short plan:**
   - the three to five changes with the best gain for their risk;
   - how you will measure each;
   - what needs the user's eye.

   Send it to the user before design-level work. Clear defects you can just fix.
5. **Ship in small, verified steps:**
   - send updated proof and tester PDFs as changes land;
   - show showcase previews as they land;
   - keep the docs true as you go.

**Definition of done for each change:**
- old and new tests pass;
- all four faces rebuild byte-identical;
- OTS is clean;
- `scripts/audit_font_pairs.py` finds no collisions;
- `scripts/topo.py` shows no change except the intended ones;
- an independent review has looked at what changed;
- the judged edits, README and FONTLOG are updated and `scripts/validate.py` has been run;
- the proof, tester and showcase are regenerated.
