# Original-source research

Evidence collected on 24 October 2026 for faithful reconstruction of Kilfane,
Carrick, Tuam Uncial and Céilí. Start with [the handoff](HANDOFF.md).
The latest work is [round 5](round-05/README.md): Carrick's named original marks,
with retained and derived components distinguished. [Round 4](round-04/README.md) recovers Céilí's named original punctuation
and the language marks derived from it. [Round 3](round-03/README.md) supplies Tuam and Céilí outline studies
from larger original reproductions, with topology-preserving tracing and explicit
source disagreements. [Round 2](round-02/README.md) supplies the latest Kilfane
and Carrick candidates. [Kilfane Study 1](kilfane-study-01/README.md) is preserved. Released version
2.000 remains the baseline.

## Files

| File | Purpose |
|---|---|
| [source-register.json](source-register.json) | 40 annotated sources and leads, including uninspected and unavailable material |
| [downloads.json](downloads.json) | 25 original download locations, sizes and SHA-256 fingerprints: eight NIVAL images in JPEG and JP2, plus nine PDFs |
| [embedded-image-register.json](embedded-image-register.json) | Native dimensions, page numbers and hashes for 15 images extracted from the research PDFs |
| [local-file-inventory.json](local-file-inventory.json) | Fingerprints of the local evidence pack; an inventory, not a claim that those files are committed |
| [RIGHTS.md](RIGHTS.md) | Why external scans and PDFs are linked rather than mirrored |
| [kilfane-study-01/](kilfane-study-01/) | Candidate fonts, trace data, glyph regions, provenance, metrics and a proof rendered from the new font |

Historical source media remain at their institutions. The metadata here lets a
researcher retrieve the exact evidence, check its identity and regenerate local
comparison sheets. `local_reference` paths in the source register refer to a local
research cache, not files in Git. Use `build/research/` as that cache root.

Modern revival entries are retained only for bibliographic disambiguation and are
explicitly excluded from reconstruction and outline comparison. No modern revival
font was used to build Kilfane Study 1.

## Strongest original specimens

All NIVAL records below belong to the William Curran Archive, collection
`p21086coll129`. The download manifest provides the complete archival references.
Dimensions are native pixels, not an assertion about scanning DPI or master-artwork quality.

| ID and record | Pixels | Use and limitations |
|---|---:|---|
| [N44: brochure front](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/44/) | 3000 × 2113 | Competition and exhibition information |
| [N45: brochure reverse](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/45/) | 3000 × 2106 | Award wording, designers and examples |
| [N46: four-face flyer](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/46/) | 2140 × 3000 | All four alphabets, figures, alternates, loose marks, sheet numbers and sizes |
| [N47: paired flyer](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/47/) | 2140 × 3000 | Larger Carrick and Kilfane; correlated reproduction history with N516 |
| [N513: Carrick alphabet](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/513/) | 1286 × 1073 | Useful alphabet specimen; not established as drawing master |
| [N514: Carrick sheets](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/514/) | 2592 × 2592 | Repeated production letters; perspective, cropping and overlaps |
| [N516: Kilfane alphabet](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/516/) | 1242 × 1576 | Main Study 1 trace source; some letters touch their neighbours |
| [N517: Kilfane sheets](https://nival.contentdm.oclc.org/digital/collection/p21086coll129/id/517/) | 2573 × 2573 | Repeated letters used to assess damage and counters; not suitable for direct tracing without perspective correction |

JPEG and JP2 versions have the same native dimensions. Enlarging either adds no
historical detail. Preserve the original bytes, then derive working images locally.

## Printed and archival research

- **Mary Ann Bolger, _Designing Modern Ireland_, volume 1**, printed pp. 278–280:
  competition history and archive/family leads. **Volume 2**, PDF pp. 157–164,
  figures 201–206: competition ephemera, a 1974 Tuam application, development
  sketches, reproduction negatives and a complete Tuam transfer sheet.
  [RCA record and both volumes](https://researchonline.rca.ac.uk/3543/).
  The record says 2016; the examined PDF title page says October 2017. Local filenames
  use 2017 and do not resolve that catalogue discrepancy.
- **Della Varrilly (1982)**: PDF pp. 94, 96 and 98, figures 30–34, for near-contemporary
  reproductions of Calli/Céilí, Carrick, Tuam, Armóin and Kilfane; printed pp. 73–76
  for discussion. Some PDF pages contain multiple image layers; inspect the rendered
  page as well as extracted images. Download and hash: source `V` in the manifests.
- **Una O'Shea (1993)**: PDF p. 74, figure 23, another competition reproduction.
  Useful corroboration, weaker outline evidence than the archive scans (`O`).
- **Eimear O'Keane (2022)**: PDF pp. 32–33 for contextual discussion, not reliable
  alone for original production dating (`K`).
- **Heritage Outlook, summer 2011**, printed p. 37: KDW archive context and competition
  poster (`HO`). The Klingspor Hayes sheet (`H`) is a supplementary attribution lead.

The highest-value Tuam illustration in Bolger is the full sheet at PDF p. 164,
figure 206, but the embedded image is only 590 × 900 pixels. Figures 205a–c at
pp. 161–163 show development material. Larger rendering cannot recover absent detail;
better scans of the physical items remain valuable.

## Historical corrections and unresolved leads

The primary brochure's award wording is: Céilí (printed as **Caill**), first prize
£250 and silver medallion; Carrick, **Highly Commended**, £50; Kilfane and Tuam,
**Commended**, £25 each. It does not label Tuam fourth place. See N45.

| Typeface | Sheet and size | Sheet and size |
|---|---|---|
| Kilfane | S53909, 30 pt / 7.5 mm | S53910, 48 pt / 13 mm |
| Tuam Uncial | S53911, 30 pt / 7.5 mm | S53912, 48 pt / 12.5 mm |
| Carrick | S53913, 36 pt / 9 mm | S53914, 60 pt / 15 mm |
| Céilí | S53915, 24 pt / 6.5 mm | S53916, 42 pt / 11 mm |

These are transcriptions of N46. A printed 1973 Letraset copyright line does not
establish release year. Tuam's earlier development/application and the 1978
competition are separate events.

- **Céilí:** no high-resolution complete production sheet acquired. Search name
  variants Céilí/Ceili, Caill, Calli and Caili. _Design_ no. 357 (September 1978)
  is a contemporary lead; the archive's PDF/JP2 files were private and page content
  was not inspected. Do not report it as an examined specimen.
- **Hayes originals:** Bolger's illustration credits point to Jarlath Hayes and Bill
  Bolger private collections at the time of the thesis; current custody is unverified.
- **Trinity:** Bolger's references point to Early Printed Books, OLS L-2-922, items
  3 and 4 for competition material. A footnote discrepancy warrants checking both.
- **NIVAL:** [William Curran Archive](https://www.nival.ie/william-curran-archive/),
  KDW and Dolmen Press collections may contain material not yet digitised.
  Public research contact: nivalinfo@ncad.ie. No enquiry has been sent.
- **Hecht:** custody of the Céilí drawings remains unverified. The Brighton Hecht
  Collection is a magic-lantern collection; it does not substantiate a type archive.
  The older README's V&A custody claim was not verified in this research.
- **Applications:** Series C banknotes may contain adapted Kilfane lettering.
  Conflicting Céilí/Tuam attribution for _Glenroe_ needs dated frames and letter-level
  comparison. Neither claim supplies clean original outlines by itself.
