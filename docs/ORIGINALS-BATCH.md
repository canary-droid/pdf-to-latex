# Original PDF collection batch

For the separately authorized 2 November syntax/Low-recovery continuation and
focused end-of-batch review bundle, see [ORIGINALS-RECOVERY.md](ORIGINALS-RECOVERY.md).
The same run and four arXiv deferrals remain selected. Older no-model-repair text
below describes the original launch; the new bounded policy is explicit and does
not authorize OCR/rotation/coverage rewrites or a supervisor.

The 1 November 2026 collection authorization supersedes the earlier book-only
scope for this separate controller. It admits only the PDFs currently under
`/home/mdi/llm-wiki/originals`. The existing intake's 376-source union supplies
identity/type metadata, never additional work. Gatheral, Bergomi and finished
experiments stay unchanged. No autonomous code modification or supervision runs.

Preparation hashes and freezes every original, deduplicates only identical bytes,
retains aliases/type/partial-source labels, checks case-insensitive folder/ID
collisions and makes verified independent project copies. The observed collection
is 63 distinct PDFs, 1,502 pages, 60,183,390 bytes, identical to the intake baseline.
There are no matching saved MinerU source hashes and neither finished book is in
this collection. Existing wiki summaries are not adopted as complete conversions.

Run from a normal terminal:

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-originals-batch.sh run
```

The current run is selected by `results/originals-batch-current.json`. `prepare`
creates the frozen run once; repeated preparation reuses it or refuses changed
code. A completed run invocation performs no OCR, inference or readiness.
Leave bound code, source copies, environments, model cache and helper configuration
unchanged while the controller is running. Do not start another project writer.

## 2 November selection continuation

The original inventory remains 63 PDFs. The operator requested deferral only of
the six named arXiv candidates with **no document-level GLM reservation for any
part**, including failed or interrupted reservations. Exact filenames and full
source hashes are recorded in the run's sealed
`continuations/arxiv-selection-*/selection.json`. The arXiv IDs are supplied
paper-level candidates; exact-version matching and source acquisition are deferred.

Four were eligible: Brigo, SINC, Bayer–Breneis and Homescu. Thus 59 sources remain
included and four are deferred for arXiv-source intake. Attention's call-044 had
already started, so its remaining eligible critic is retained. COS had completed
both phases and remains retained. Calibrating Heston is included throughout.

The one-time `defer-unstarted-arxiv` control requires the current worker to be
fully paused with all project/converter/run locks released. It rechecks the ledger,
seals prior state/binding snapshots and the selection, and writes a linked active
binding under `continuations/`. Original `collection.json`, `binding.json`, plans,
call outcomes, versions and generations are not rewritten. Resumes retain the
same run ID, call numbering and consumed allowances. Repeating the selection
control is idempotent. Unrelated code changes are not accepted by this handoff.

Deferred sources keep their recorded processing history and reusable OCR/inputs.
Their pending tasks have a distinct deferred disposition and are absent from
admission; a reservation guard and sealed-selection verification also reject
dispatch. They are never generated/published as successful or failed conversions.
Progress/index records distinguish them, and source folders receive an additive
`batch-selection.json`. No existing generation or source record is deleted.
Selection continuation checks the resident GLM without starting/switching services.
Status, pause and resume commands above are unchanged. Future re-inclusion requires
another explicit selection decision; this control never reactivates sources.

Controls, from the same directory:

```bash
bash scripts/run-originals-batch.sh status
bash scripts/run-originals-batch.sh pause
bash scripts/run-originals-batch.sh resume
bash scripts/run-originals-batch.sh bundle
tmux attach -t pdf-originals-batch
```

Status reports the saved phase separately from the observed writer lock. A tmux
launch message alone is not evidence of work. The run's `terminal.log`,
`progress.json` and `state.json` carry actual progress; a compact progress copy is
under `results/originals-batch/`. Pause drains active GLM requests or the current
OCR window. It does not kill a model service. A pause during OCR leaves GLM stopped
until resume reaches the documented handoff. Resume never resets consumed model
allowances or replays an uncertain request. Unsealed calls require diagnosis.

## Resource phases and boundaries

One controller holds the project, converter and run locks. It checks the existing
immutable isolated compiler and performs a real tiny compiler qualification before
OCR or long inference. The finalised compiler image and its sealed qualification
are copied from the delivered book run. The approved existing dependency-recovery
policy can build a versioned compiler image for an allowlisted missing dependency;
untrusted document builds remain network-free, non-root, read-only-source,
no-shell-escape Docker builds. No host LaTeX installation is attempted.

Before OCR the controller verifies project idleness, both deployments, GPU
workloads, actual GLM request counters, helper/configuration hashes and current
serving settings. Only the existing owned idle regular GLM may be stopped through
its documented `stop.sh`. Partial, absent-at-first-handoff, busy or unknown
deployments stop the batch. All missing OCR runs serially with existing MinerU
Basic, project environment/cache and original eight-page windows/one-page context.
No OCR model download, installation, cloud client or concurrent GLM work is added.
The historical Basic worker's offline environment and Python socket guard remain;
`ocr-isolation=none` is the existing qualified route, not an OS network-isolation
claim. Compiler isolation is independent of OCR isolation.

After OCR, the documented `start.sh` restores the same owned regular deployment
with preparation/pulls disabled. Runtime build/settings must match the pre-stop
binding. High/Max template support, memory and shared pool admission are rechecked.
The requests use `glm53-regular`, High conversion, Max immediate own-draft criticism,
131072 output tokens, durable streaming and at most two owned requests. There is
no overall call ceiling or wall deadline. Each model phase has the existing one
attempt allowance; no automatic semantic retries are introduced. Interrupted OCR
windows retain attempts and have at most two attempts, while completed windows are
hash-verified and reused. Document failures remain visible and independent work
continues; shared integrity, ownership, transport, environment or capacity faults
halt admission. No repair agent or promotion mechanism is involved.

The smallest documents are first. The first technically successful document
(conversion, own-draft review and passing build) is the retained smoke check.
The controller continues automatically through the approved frozen collection.
Coverage flags remain visible even when smoke succeeds; this is not an accuracy
certificate. There is no manual inspection gate and no later collection.

## Source fidelity and deliveries

Complete native MinerU blocks/assets and native PDF text are retained. The repaired
scope builder includes nested appendices regardless of shorter descriptive titles.
Whole documents are preferred if conservatively admitted with a critic-draft
reserve; otherwise complete coherent heading spans are split without clipping a
proof or target. Nonblank pages with missing OCR blocks are failures, not silently
declared blank. Existing mathematical correction/attribution policy is unchanged.
The actual critic input is compared with the selected revision. Coverage, asset,
source verification, review and build results remain separate statuses.

The library is `/home/mdi/llm-wiki/sources/`, with a simple `INDEX.md`/`index.json`.
Existing vault, originals, intake and databases are untouched. Folders use portable
author-year-title-hash labels; unknown author/year values are explicit, and metadata
candidates are not claimed as verified bibliography. Each contains `original.pdf`,
`source.json`, relative-link `README.md`, immutable `generations/<run>/` and a
`current.json` pointer. Generation manifests bind copied bytes. Interrupted
publication resumes through verified staging; a conflicting generation is never
overwritten. Initial drafts, selected standalone part TeX/assets, extraction,
accuracy notes, material comparisons, build diagnostics and coverage are included.
Reading PDFs concatenate successful compiled parts; missing parts are explicit.
Raw wire/reasoning logs remain in the project with paths/hashes. Portable sources
do not require them. No Markdown completeness, retrieval or mathematical proof is
claimed.

Per-source transfer ZIPs appear under `results/originals-batch/<run>/`. The controller
automatically publishes the final index, coverage/failure records and a compact
text-first inspection ZIP under `results/inspection/`; `bundle` creates another
snapshot only while no writer holds the locks. Progress includes observed timing,
usage and an uncertain remaining-time range once GLM observations exist. It makes
no time promise before those observations.

The normal launcher runs the full offline regression suite once per code/test
identity. Focused collection tests cover duplicate/version isolation, collision
rejection, completed OCR reuse, uncertain-call refusal, failure isolation,
appendix scope and immutable portable publication. Mock tests do not qualify
actual Docker, SSH, tmux, MinerU fidelity, capacity or GLM execution; those are
separate runtime checks recorded in the run.
