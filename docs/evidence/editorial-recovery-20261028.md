# Editorial recovery and explicit-effort pilot — 28 October 2026

Prepared offline, not running. Original run
`runs/editorial-chapters-trial-20261027T195212Z-654e71` and all its responses,
versions, seals and inspection ZIP remain unchanged. Its on-disk state is
`stopped_error`; its earlier ZIP said running because it was bundled before
Bergomi preparation failed. No Bergomi model call occurred.

## Actual Bergomi failure

The source is `bergomi`, original PDF SHA-256
`35fd11fb3fe46e9c3de01db6b22dc1e2c848c04b352121fe13c3ccf0fba38413`.
`docs/source-provenance/bergomi-intake-20261027.json` called nine pages
`declared_blank_pages`. The chapter adapter passed that list to a stricter
**verified-empty** reader. All nine pages actually print “This page intentionally
left blank”, recognized as one `text` block, bbox `[.295,.101,.706,.125]`.
Codex inspected all nine original-page images and legible notice crops. This is
an intentional blank with a notice, not absent content or an empty OCR record.

| Physical / selected page | Window | Local index (zero based) | Owner |
|---|---|---:|---|
| 5 | bergomi-0001-0008 | 4 | yes |
| 119 | bergomi-0113-0120 | 7 | yes |
| 149 | bergomi-0145-0152 | 5 | yes |
| 217 | bergomi-0209-0216 | 9 | no, adjacent context |
| 217 | bergomi-0217-0224 | 1 | yes |
| 323 | bergomi-0321-0328 | 3 | yes |
| 373 | bergomi-0369-0376 | 5 | yes |
| 407 | bergomi-0401-0408 | 7 | yes |
| 437 | bergomi-0433-0440 | 5 | yes |
| 469 | bergomi-0465-0472 | 5 | yes |

Exact attempts, mappings and block evidence:
`runs/editorial-repair-audit-20261028/blank-conflicts.json`.
Contact sheet: `runs/editorial-repair-audit-20261028/images/blank-notices-inspection.png`.
There is no cross-book blank list, off-by-one shift or duplicate ownership.
The second occurrence of page 217 is legitimate context. No saved page has a
missing/non-list blocks field. The new source/hash-bound classification preserves
all notices and rejects unexpected additional content. The strict empty-page guard
is unchanged; diagnostics now identify source, physical/selected/local page,
window and the exact structured record.

Offline preflight: 65 completed windows, 520 distinct owned pages, 128 adjacent
context appearances, 8,102 recognized blocks across 16 parts. Both native MinerU
and cached PDF text are present with the same owned page sequence. All literal
native formula strings and referenced assets are retained. There are 118 native
renderer fallbacks, explicitly preserving raw content and/or source images;
these need fidelity review, not another OCR run. This is mechanical accounting,
not visual verification of all 520 pages. Twelve chapters, embedded appendices,
epilogue and bibliography are prepared; front/back are source supplements. The
supplied PDF has no index section.

All 133 prepared conversion requests fit the recorded 1,048,576 context bound
using conservative UTF-8 bytes plus 4,096 template margin and 131,072 output
allowance. The largest bound is 789,339. No source was clipped; no section-only
context fallback was needed. The complete first chapter pair targets physical
18–41; its conversion bound is 376,235. Critics need the future complete draft
before their exact body/fit can be finalized. The live server capacity is checked
again before each dispatch; these are conservative bounds, not tokenizer counts.

## Saved Gatheral work and current dispositions

Confirmed original 30 calls: one readiness, 15 conversions, 14 critics. Eleven
conversions and all dispatched critics completed; four conversions exhausted the
allowance. Request time 30,274.4921 seconds; 1,775,715 completion tokens, including
1,656,305 reported reasoning tokens. The earlier 24 calls are separate retained
history. The linked preparation inherits all 54 calls; none were replayed.

For Chapters 5 and 10, current selection uses the saved, complete critic documents
before the program's extra historical appendix. Other selected document versions
and their complete notes remain unchanged. For those versions, mathematics and document bytes
match the already recorded critic document; their original successful compilation
evidence is identified as inherited. The prior appended versions stay preserved.
Chapter 5 retains the hatted C/D introduction, mean-variance overbar and auxiliary
prefactor. Its T-star issue remains open. Chapter 10 retains the annual floor at
or below -12%, Christopher Jeffery resolution and corrected conventional-loss
comparison. The contract-intended denominator remains open; the printed glyph
has already been checked. Earlier claims have explicit superseded-by links in
`accuracy/*/history.json`. Applied/resolved model claims remain distinct from
independent verification; compilation cannot resolve a mathematical issue.

Coverage now records exact target block IDs/spans/pages separately from parent
chapter and context-only pages. Chapter 7 s01 targets PDF 118–120, not 118–131.
Chapter 11 s01 targets 164–167, not 164–192. The four missing sections get notices
in source order, where they belong:

- `gatheral-07-s03`, Including Jumps, PDF 124–125, call-016.
- `gatheral-07-s05`, Lewis, PDF 127–128, call-019.
- `gatheral-11-s02`, Variance and Volatility Swaps, PDF 167–177, call-024.
- `gatheral-11-s03`, Valuing Volatility Derivatives, PDF 177–187, call-025.

Call-024 had a partial final answer; it remains failed, not a completed draft.
The three other failures spent all 131,072 tokens in reasoning. Dormant future
recovery previews keep both short Chapter 7 sections intact and use observed
whole-block subsection boundaries for the two much longer Chapter 11 failures.
These previews cannot dispatch in the pilot. Any later adopted pilot repair should
be reused rather than converted again.

## Pilot selection and interpretation

| Case | Historical conversion | Historical elapsed | Completion / reasoning | Reason |
|---|---|---:|---:|---|
| Gatheral 6 s03 | call-006, stop | 738.67 s | 35,396 / 33,024 | Completed local-volatility control; (6.2), homogeneity and derivatives are source-checkable |
| Gatheral 7 s01 | call-012, stop | 1,081.28 s | 52,409 / 49,573 | Completed short-expiry control; SDE (7.1), assumptions and limits |
| Gatheral 7 s05 | call-019, length | 2,168.52 s | 131,072 / 131,072 | Short failed Lewis section, unchanged output boundary |

Codex inspected source crops of (6.2), (7.1) and the Lewis coefficient display;
the two control formulas match their saved initial drafts in the inspected
expressions. This does not certify their entire sections. The independent pack
contains eight distinct source pages and six formula crops, historical initial
answers/drafts and request comparisons. Expected readings are outside requests.

New conversions copy the complete historical request and add only top-level
`reasoning_effort: high`. The existing critic follows each complete draft with
explicit `max`. Ordinary continuation defaults remain max/max; per-task effort
is an explicit validated preparation setting. No sampling changes. No inference
has run. Three conversions, at most three critics, one attempt each; at most three
readiness calls across launches/resumes. Parent accounting and its 98-call ceiling
remain in force. No overall/generation deadline; connection timeout remains 10 s.
The pilot stops for inspection and cannot dispatch Bergomi or other recoveries.

The installed recipe commit, confirmed with read-only `git log -1`, is
`3fd60dfc836fab0f1ed0fd4f0afaf2a1d62b2aab`.
Installed local configuration has `THINKING=1`. Patch 0023 maps medium to high,
accepts max, and none disables thinking; the pinned GLM template renders low/high
explicitly and otherwise Max. The controller rejects unsupported values; it does
not depend on template fallback. Historical requests omitted effort and thus map
to Max under this installed path. Response usage does not attest the actual
rendered runtime prompt or prove a thinking level. New transport tests verify
that the saved effort is really transmitted. No reasoning-budget parameter was
invented. The server launcher's 32,768 default remains unchanged; requests still
explicitly ask for 131,072.

## Deferred serving comparisons

No serving changes were made. Preserve rollback: recipe commit
`3fd60dfc836fab0f1ed0fd4f0afaf2a1d62b2aab`, `tensorfold-glm53:v0.6.0`, reported
image `sha256:9b00719301e859f7b790b5c4d80ab1e49ef64bef63d3e7af2f3829cfc32cfee1`.
Docker identity could not be rechecked in this sandbox; record actual container,
engine/model/template revisions and local overrides before any later comparison.
First compare existing policy against joint verification on the same engine,
then a pinned newer GLM-compatible stack in a separate image/checkout. Match
reasoning, weights, quantization, drafter, KV format, context and workload. Measure
usable output and accuracy as well as throughput. The issue-198 headline speedup
was not consistently reproduced; treat that as a motivation to test, not an
established gain. Model/template changes are separate from engine changes.
References to recheck later, not upgrades performed here:

- https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks-TensorFold/issues/198
- https://github.com/ashhart/TensorFold/releases
- https://github.com/ashhart/TensorFold/blob/main/docs/recipes/glm-5.3-flash-cuda.md


## Validation and changed project files

The full offline suite ran once: 540 tests, 521 passed, 15 mock HTTP-server tests
blocked by `PermissionError: [Errno 1] Operation not permitted` at socket bind,
and four opt-in real-compiler checks skipped. No assertion failures. After the
final report-count, character-count and phase-configuration adjustments, all 15
focused recovery tests passed. Earlier targeted chapter/stream/annotation checks:
82 tests, two opt-in skips, no failures. AST parsing, wrapper shell syntax and
`git diff --check` passed. Docker socket access was denied, so the rebuilt master
was not compiled here. Existing exact-document compilation records are inherited;
new live effort behavior and new output accuracy remain untested.

Changed for this task only (earlier unrelated working-tree edits are preserved):

- `probe/saved_pages.py`
- `probe/chapter_inputs.py`
- `probe/chapter_editorial.py`
- `probe/chapter_glm.py`
- `probe/local_model.py`
- `probe/editorial_recovery.py` (new)
- `scripts/editorial_chapters.py`
- `tests/test_editorial_recovery.py` (new)
- `docs/source-provenance/bergomi-page-classification-20261028.json` (new)
- `docs/evidence/editorial-recovery-20261028.md` (new)
- `docs/EDITORIAL-CHAPTERS.md`
- `docs/PROJECT-STATE.md`

Preparation accepts `--conversion-effort` and `--critic-effort` with explicit
choices `none`, `low`, `medium`, `high`, `max`; defaults max/max. Launch/resume
rejects effort overrides because requests are sealed. The three-case pilot has
its separately fixed high/max settings. Nothing is promoted to a book-wide high
default. An incompatible cached Bergomi effort selection is rejected, not silently
reinterpreted.

Current preparation: `/home/mdi/projects/pdf-to-latex/runs/editorial-chapters-trial-20261028T072031Z-41483c`.
Edition: `/home/mdi/projects/pdf-to-latex/runs/editorial-chapters-trial-20261028T072031Z-41483c/editions/gatheral-1793172035172466728`.
Inspection ZIP: `/home/mdi/projects/pdf-to-latex/results/editorial-chapters-inspection-20261028T072031Z-41483c-1793172160466305250.zip`.
Operator instructions: `docs/EDITORIAL-CHAPTERS.md`.
