# Getting the original source evidence

The repository contains the source register, retrieval URLs, exact file hashes,
native dimensions, trace coordinates, construction decisions and candidate proofs.
The original archive images and full PDFs are retrieved from their institutions
into a local cache. Open redistribution permission has not been established for
those files; they are not included under this repository's font-software licence.
See [RIGHTS.md](RIGHTS.md).

## Retrieve or verify the originals

From a fresh clone, Python 3.12+ with no additional packages is enough:

```sh
# Inspect the selection first; this makes no network requests.
python scripts/fetch_sources.py --list

# Fetch every registered original/source lead, excluding modern revival specimens.
python scripts/fetch_sources.py

# Check the local cache later without downloading anything.
python scripts/fetch_sources.py --verify-only
```

The default selection is 23 files: 16 NIVAL JPEG/JP2 files and seven research PDFs.
Two modern revival specimens remain in the historical register for context but
are excluded from this command and from reconstruction. An individual source ID
can select both image formats; use `--format` to narrow it:

```sh
# The immediate Carrick e/f investigation needs this photograph.
python scripts/fetch_sources.py --source N514 --format jpg

# Retrieve all eight NIVAL JPEGs for the existing tracing tools.
python scripts/fetch_sources.py --format jpg
```

Files go to ignored `build/research/`, retaining the relative paths from
[downloads.json](downloads.json). Thus tracing commands use
`--sources build/research/original-specimens`. A custom local cache can be selected
with `--output PATH`; keep external media outside tracked/public folders.

Existing files are hash-checked and reused. A mismatch is reported and preserved,
not overwritten; changed downloads are rejected before installation. A missing,
blocked or changed institutional endpoint produces a failure and nonzero exit
status while the remaining selected files are attempted. A hash proves identity
with the registered download, not historical authenticity or a copyright licence.
Do not substitute a different download and quietly change the expected hash.

## What agents should read next

- [Source register](source-register.json): catalogue references, context and leads.
- [Embedded-image register](embedded-image-register.json): native PDF image/page
  identities for locating detail after obtaining the original PDF.
- [Local inventory](local-file-inventory.json): provenance of the original research
  cache. These historical local paths are not expected to exist in a fresh clone.
- [Handoff](HANDOFF.md) and [continuation plan](../docs/superpowers/plans/2026-10-25-continuation.md):
  current candidates, ownership, next tasks and acceptance checks.

Font-only proof images and reconstruction data are committed. Source-containing
comparison sheets remain local and can be regenerated using each round's README.
If permission to mirror an original is obtained, record the specific material,
terms, attribution and supporting evidence before adding it to the public repo.
