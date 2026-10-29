# Gatheral: received source and the next integration boundary — 25 October 2026

**Observed completion, 25 October 2026, 23:36 UTC:** the actual run is `runs/convert-basic-20261025T230247Z-e6bb30`; `conversion_completed_unreviewed`, 27/27 windows and 210/210 owned pages, with no visible project converter/launcher. These are extraction completion facts, not fidelity findings. Do not restart extraction from the historical launch instructions below. Use [GATHERAL-REVIEW.md](GATHERAL-REVIEW.md) after guarded integration; no review preview has yet been created.

## Current Task 2 adapter update — 25 October 2026

The whole-source registration and Task 1 launch supersede the historical Chapter 1
subset plan below. Task 2 implements an explicit owned-page → protected recovery
adapter in a separate development copy. It preserves the 100-page limit of the
older batch path; it does not call that runner. Instead it inventories all pages
from a **completed** ordinary conversion, prepares each whole recognized block
once plus one page-omission unit, and uses the existing bounded recovery executor.

Start with physical pages **32–33** as the technical gate; other prepared pages
remain pending. Inspect before expanding the same run. This retains prior calls,
compiler protections, page maps, full paragraphs, raw unresolved OCR, images and
bibliography. Empty/blank pages still receive omission checks. The full-book scope
includes front matter, appendices, references and index. See the executable
operator sequence in [GATHERAL-REVIEW.md](GATHERAL-REVIEW.md).

No Gatheral output has been consumed as final evidence for this task, and no future
conversion/preview directory is invented. The wrapper finds the actual completed
Task 1 run later. Oversized/unrenderable targets remain explicit unavailable units;
a failed gate blocks expansion. Automatic insertion, unresolved image/table TeX,
unlabelled/ambiguous context and full-book semantic boundary decisions still need
review. The default finite six-hour admission budget is not a promise that a whole
book completes; exhausted allowance stays a gap rather than resetting on resume.
A larger review budget needs an explicit plan **before** preparing/launching.

This replaces the "next implementation task" assessment in the dated plan below.
The adapters are offline tested, not live-qualified on Gatheral. Copy-back is
conditional on successful extraction and baseline hashes; no original files were
edited during extraction.

**Launch update, 25 October:** the user has authorized extraction of the entire
210-page book, superseding the Chapter 1-only extraction proposal below. Source
`gatheral` is now registered; no prior Gatheral conversion was found. Follow
[GATHERAL-EXTRACTION.md](GATHERAL-EXTRACTION.md) for the prepared Basic launch/resume
command. Extraction has not started. The later visual/candidate integration work
below remains separate; whole-book extraction is not a reviewed-book runner.

`inputs/gatheral/source.pdf` is already present and readable. No repeat transfer is
needed. Read-only PyMuPDF inspection found **210 pages**, no encryption, **202 pages
with native text**, 73 bookmarks and three PDF page-label rules. SHA-256:
`6010ddf7fe8456398d35dc7d94b16d1f8c853da5e1671d763c7f92083169a988`.
The native title page identifies Jim Gatheral, *The Volatility Surface: A
Practitioner's Guide*. Title/author PDF metadata fields are empty. Exact intake,
bookmarks and label rules are in
[source-provenance/gatheral-intake-20261025.json](source-provenance/gatheral-intake-20261025.json).
Bookmarks/labels are navigation evidence, not OCR fidelity or independent edition
verification. The source remains ignored by Git. At intake no registration,
extraction, model request or compilation had been performed; see the launch update.

## Concrete processing plan

First exercise **Chapter 1, physical PDF pages 32–45 (14 pages)**, corresponding
to PDF labels 1–14. Native text makes `ocr_mode=auto` the initial preparation
choice. Use the existing `probe.documents.prepare_source()` workflow in a new
ignored preparation directory, then add a separate hash-bound source entry with
those original physical pages and validate it with the existing source loader.
Do not overwrite `inputs/gatheral/source.pdf`. This registration/preparation is a
next task, not an already-created source or a command that is ready to convert.

| Step | Implemented part | Exact remaining integration work |
|---|---|---|
| Intake / MinerU Basic | `prepare_source()`, source loading, `probe.py convert --sources ID --tier basic --ocr-isolation none`, chunk ownership/page maps and resume | Register a new actual selection first. `ID` is a placeholder here, not a registered Gatheral source. Run OCR only at the operator's later authorization. Preserve the native-text evidence and all source hashes. |
| Qwen visual review | Saved pages/blocks/images, readable splits, omitted-content checks in batch preparation; shared recovery executor, export checks and isolated compiler | Adapt the **recovery visual preparer** from the historical 267-region sample to a supplied owned-page manifest. Combine split-block coverage and one explicit whole-page omission check per owned page with the current bounded recovery/compiler path. Do not route a whole book through the older batch runner merely because it accepts pages; that loses the newer recovery protections. |
| Versioned candidate | Reviewed dispositions, exact-proposal binding, conflict/atomic-group/deletion handling, complete raw unresolved content and source references | Assemble every owned block exactly once across the new visual shards, retain full paragraphs and excluded/unavailable blocks, and inventory omission/insertion proposals separately. Unsupported insertions stay unresolved; never silently drop them or count a missing portable draft as checked. |
| GLM text review | New `probe.critic_route boundaries` / `prepare --profile glm`, explicit coherent passages, exact anchors, same-edition local references, serial execution and bounded follow-ups | Build/review the Gatheral boundary manifest from its actual candidate inventory. Cover theorem+hypotheses/proof and cross-page derivations. Use context-only overlap; resolve uncertain boundaries explicitly rather than clipping or inferring sentence splits. |
| Selected MiMo | `select`, offline cost preview, `prepare-selected`, explicit paid readiness/launch, prior costs/reservations and shared limits | Select from the actual GLM results after local context; no whole-book upload or automatic failed-service fallback. This calibration remains capped at four passages; a larger paid scope needs a new explicit authorization. |
| Traceable output | Raw evidence, separate queues, experimental candidate, exact anchors and inspection ZIPs | Join shard ownership/coverage, candidate versions, unresolved content, reference/bibliography provenance and later explicit human decisions into a book inventory. No automatic acceptance or model-vote repair. |

`batch_inputs.py` still has **MAX_PAGES=100**. Do not raise it for this plan.
For the full 210 physical pages, a possible ownership plan is 1–100, 101–192,
193–210: 100 + 92 + 18 distinct pages, with no overlap counted as owned twice.
Keep cross-boundary context outside ownership and distinguish its OCR availability
from visual/critic completion. Within each shard, split by coherent section/proof
where needed and retain source-global physical numbers and stable block IDs.
Reconcile every page, including blanks, covers, figures, front matter, bibliography
and index; explicitly classify non-prose pages rather than dropping them.

Bookmark ranges are: front matter 1–31; chapters 1–11 at 32–45, 46–55, 56–73,
74–80, 81–104, 105–117, 118–131, 132–137, 138–152, 153–163 and 164–192;
Postscript 193; bibliography 194–199; index 200–210. These are proposed navigation
boundaries derived from the next bookmark; inspect boundary pages at source
preparation. PDF labels from physical page 32 begin at Arabic 1; earlier labels
use cover prefixes and Roman numerals. Preserve both physical and printed/label
identities and do not silently assume they coincide.

Bibliography text/labels can feed the local exact lookup after conversion. Preserve
raw entries and unresolved natural-language citations; an inventory is not evidence
that cited works were read or that they support a claim. No external retrieval is
part of this milestone. Missing earlier chapters remain unavailable context.

**Next implementation task:** the owned-page → recovery-visual adapter and
cross-shard candidate coverage inventory, first tested on the 14-page Chapter 1
selection. The critic is reusable now; a protected whole-book runner is **not**
ready. Complete the eight-passage GLM calibration and review its selective second
opinions before integrating a book-scale workflow. No second OCR benchmark,
service operation or automatic repair loop is proposed here.
