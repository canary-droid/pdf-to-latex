# PDF-to-LaTeX compatibility and fidelity probe 0.1

**Latest, 1 November 2026:** the saved-work finalisation is delivered. See
`results/book-finalisation-current.json` and the linked run's `FINAL-INDEX.md`
for both reading PDFs and editable/TeX-only/complete-source exports. All 34
Gatheral and 61 Bergomi selected parts are included. This is a working edition,
not a claim of whole-book mathematical verification. No further queue is started.

**1 November 2026: [finite Gatheral/Bergomi completion](docs/BOOK-COMPLETION.md).**
The current task reconciles saved production and experimental work, repairs
demonstrated defects in new derivatives, and prepares one missing-content-only
High/Max GLM queue with automatic final assembly/packaging. No inference is run
during coding. Use its separate completion pointer and wrapper; earlier launch
instructions below are historical and must not replay completed suites.

**26 October: the [fresh Gatheral chapter run](docs/SIMPLE-CHAPTER-GLM.md) is
prepared offline, not running.** Both conversion and critic now receive unchanged
native MinerU material plus cached native PDF text, with mathematical/factual meaning
and complete references as the objective. Initial and post-critic accuracy notes,
material-change records, initial TeX and any revised working TeX remain separate.
All Gatheral Chapters 1–11 receive fresh conversions and immediate critics, followed
by the postscript and bibliography. No old GLM drafts, skip list or Klebaner comparison
is inherited. Scope is PDF 32–198 (167 pages); front matter, blank 199 and index remain
outside this run. Earlier runs and their calls are preserved separately.
No overall/generation deadline, sampling change, automatic retry or block-output
protocol is introduced. Streamed reasoning, cumulative calls and isolated compiler
recovery remain intact. New failures remain visible gaps. Use the one
persistent launch command in the runbook; offline checks do not establish accuracy.

**Development update, 25 October:** the eight-passage GLM calibration and its
selected four-passage MiMo stage are completed; their evidence stays frozen.
Task 2 changes were prepared in an ordinary development copy. See [TASK2-DEVELOPMENT.md](docs/TASK2-DEVELOPMENT.md) for copy-back guards,
critic v3 field repair, coherent local context and the new owned-page recovery
adapter. Gatheral extraction must finish before integrating these changes.
The [Gatheral review runbook](docs/GATHERAL-REVIEW.md) describes the protected
small gate and resumable expansion. It has been checked offline only; no actual
Gatheral review preparation or live review has been created by Task 2.

The older preparation descriptions below are dated history, not instructions to
replay the completed calibrations.

Start with **START-HERE.md**. This package implements design 1.1's milestone 0B;
it is a bounded diagnostic package, not the later application. Conversion and the
default critic remain local. The next operator step is the eight-passage
[candidate-only GLM critic](docs/CANDIDATE-CRITIC.md), then a reviewed, costed
selection of at most four MiMo second opinions. Python-bound anchors replace
model-transcribed quotations in this new protocol; legacy schemas stay readable.
The [twelve-passage comparison](docs/GLM-MIMO-CRITIC-PILOT.md) is completed and frozen.
MiMo uses pinned Xiaomi FP8 via OpenRouter with explicit opt-in, no fallback and a
USD 10 cumulative ceiling including previous spending. Future increases require
user approval. No local failure silently dispatches remotely.
The user accepts documented retention below 100 days (Xiaomi: 30 days); no training opt-in or account privacy change is enabled.
Credentials are read privately only at operator runtime. No cloud OCR or whole-book
review is authorized. The intended workflow is MinerU → Qwen visual review →
versioned candidate → GLM text critic → selected MiMo → unresolved review queues.
DeepSeek remains selectable. Candidate-only is the new production default; paired
X/Y requests remain an experimental option. Do not run heavy local phases together.
The [Gatheral intake and integration plan](docs/GATHERAL-PLAN.md) records the
received 210-page PDF and the remaining whole-book visual-recovery adapter work.

23 October: the next opt-in [recovery and text-critic experiment](docs/RECOVERY-CRITIC-TRIAL.md)
is prepared offline. It adds typed conservative TeX support, shared bounded
JSON/conditional reasoning/compiler feedback, experimental candidate export and
an exact-text mathematical critic with local bibliography provenance. Use that
runbook for the fixed Qwen gate/continuation, isolated compiler and subsequent
DeepSeek text phase. All proposals remain UNACCEPTED; this does not change the
default conversion workflow. [Selective sciwrite-lint reuse](docs/SCIWRITE-REUSE.md)
does not install or invoke its application.

For the completed fixture OCR and the next page-review experiment, use
[docs/SPARK-OPERATIONS.md](docs/SPARK-OPERATIONS.md). `export --run ...` creates a
portable English/math derivative from saved OCR. `review --mode pages
--preview-only --run ... --model ...` prepares complete page inputs offline;
`review --mode pages --run ... --preview ... --preflight ... --model ...` sends
them serially to the validated local model and saves UNACCEPTED proposals.
`accept-plan` creates an unselected, hash-bound catalog; `apply-accepted --plan ...`
applies only an explicit operator selection to a new derivative, with deletion
and dependent-group accounting. `review --mode regions --preview-only` prepares
selected-block comparisons from that derivative; whole-page review remains available. The runbook gives actual saved paths, bounds and the
separate OCR/GLM memory-phase procedure. Candidate review remains the default.

The completed 100-page Klebaner trial used `review-batch --preview-only` to prepare an
explicit owned-page range with block and visual-omission coverage, then
`review-batch --preview ... --preflight ...` to run sequentially. It checkpoints
each request, permits at most one retry per unit across resumes, and never
accepts proposals. `batch-status --run ...` monitors a live job without taking
its writer lock. See the runbook for the prepared 100-page Flash Next inputs,
fresh preflight, persistent terminal, resume and partial-bundle commands.

An explicit offline experiment, `python -m probe.native_text_pilot`, compares
positioned PyMuPDF characters with saved OCR. It freezes a development/holdout
sample and rules, preserves disagreements and ambiguous matches, and creates
neutral review inputs without accepting or applying alternatives. It is separate
from conversion and model review. See the native-text pilot section of
[the operator runbook](docs/SPARK-OPERATIONS.md) for actual results and limits.

Task 5 (21 October) is an opt-in paired Qwen experiment over the 267
native-pilot regions: source/OCR alone versus identical inputs plus native text.
It has no automatic retries or acceptance, a twelve-pair reliability gate and a
cumulative nine-hour review admission budget. No live Task 5 calls have been run
by Codex. Use the [exact tmux launch and resume instructions](docs/QWEN-NATIVE-TRIAL.md);
the launcher captures and validates fresh preflight evidence without pasted paths.
As inspected on 22 October, the operator's Qwen run has completed all 534 attempts
(476 structurally completed, 58 failed). Those are usability counts, not accuracy.

The completed comparison is [DeepSeek vs historical Qwen Arm A](docs/DEEPSEEK-ARM-A-TRIAL.md):
all 267 identical Arm A inputs, changing only the model field. Its separate
operator wrapper binds successful deployment evidence, runs fresh project
preflight, checks the first twelve responses and enforces eight-hour cumulative
admission with no retries. The operator completed it: 256 usable responses and
eleven schema/JSON failures. No proposals are accepted. Its dated preparation
instructions and completed evidence are preserved; do not relaunch it.

## Inputs and provenance

`sources.json` fixes hashes, page counts, OCR modes and original-page mappings.
`inputs/paper/manifest.json` and `inputs/book/manifest.json` preserve full-source
identities, selection ledgers, native text/character evidence and page previews.
Their recorded original paths describe preparation provenance, not a required
path on your Spark. Open the bundled `source.pdf` instead. The full book is not
included or processed; its immutable SHA-256 identifies the uploaded edition.
Chapter boundaries were checked against the contents and the pages before/after
the boundary. Catalogue labels and visually printed labels remain distinct.

The known-math TeX fixture was compiled in the authoring workspace and rasterised
to provide a scan. It establishes a small reproducible source, not an OCR result.

## Isolation and permissions

The controller makes direct HTTP requests only to an explicitly local/private
address. Proxies and redirects are refused. It discovers the actual served model
ID and never substitutes a cloud endpoint. Raw requests/responses are retained;
API keys are not stored. Model output is data, never a shell command.

The converter is a separate process in its own Python environment. It uses the
stateless local MinerU SDK, private configuration, predownloaded weights, explicit
CPU ONNX for Basic, disabled LLM-aided processing and no remote VLM URL. OS
network isolation defaults to `--ocr-isolation namespace`, using
`unshare --user --map-root-user --net`. Namespace root maps to the ordinary
invoking user, not host root. Namespace failure stops conversion without fallback.

The operator decision of 18 October 2026 permits explicit `--ocr-isolation none`
on `preflight` and `convert`: **local processing; no OS network isolation**.
This trial uses that mode. It skips the namespace probe and launches the same
local worker directly. Local cached assets, disabled external endpoints and
cloud stages, offline/telemetry settings and the Python socket guard still apply.
The guard is best effort and cannot constrain native-code networking as an OS
namespace can. No host security or Codex sandbox changes are required or authorised.
Preflight records a deliberate skip, never a passing namespace test. Run settings,
attempt records and reports retain the selected mode; resume requires the same
mode and unchanged runtime, source, code and output evidence. Older runs are
preserved; code/settings changes can require a new run.

Rootless GPU or a particular ARM64 container is not assumed qualified. The worker
must have a writable project/model bookkeeping area; MinerU uses `.locks` even
with ready local weights. Master originals and approved releases stay outside
worker write access.

## What gets tested

- Preflight: head inventory; optional one-shot peer inventory; local text, strict
  JSON and basic image/control requests. Timing is total request latency, not
  separate prefill/first-token/decode benchmarking.
- Basic: explicit CPU OCR/formula/table path and native LaTeX export. The book
  and scan fixture force OCR. Report package/backend selections honestly; no
  generic GPU claim follows from a successful CPU run.
- Page accounting: strict zero-based local indices, exact requested page set,
  original physical-page map and one owner per overlapping window.
- State: cooperative lifetime lock, atomic JSON records and immutable attempt
  directories. Successful output membership/hashes and input/page-map evidence
  are rechecked on resume and before GLM review. Failed attempts remain. This
  small file-based probe does not implement the later SQLite source database.
- Review: original and recognised files side by side, targeted source checklist,
  and up to eight unaccepted GLM proposals. Empty/image-only math remains
  unresolved. No automatic correction or source-error repair is performed.

The resource sampler records local MemAvailable, swap, process observations and
GPU measurements when available. Sampling can miss short peaks. Root-process
RSS excludes child/GPU allocations; it is not a converter peak-memory claim.
The peer check is a snapshot, not continuous monitoring. Measured system
headroom and logs must be interpreted with other active processes in mind.

## Standard comparison is opt-in

After the Basic results, an administrator/authorised operator can prepare an
independent ARM64-compatible local vLLM runtime containing MinerU 4.0.12, CPU
onnxruntime and the required local Standard weights. Do not install vLLM into
TensorFold or the Basic environment just to try it. See `docs/UPSTREAM_MINERU.md`
for verified model-preparation forms and exact source references.

Once that runtime is actually qualified and the memory window is clear:

```bash
.venv-control/bin/python probe.py convert --tier standard --source both \
  --converter-python /ABSOLUTE/QUALIFIED/ENV/bin/python \
  --models-dir /ABSOLUTE/READY/MODEL/CACHE \
  --quiet-window-confirmed
```

Paths above are placeholders. The controller initially requires 64 GiB available
on the conversion node; the worker also checks local CUDA availability. These
are probe policies, not inferred fit guarantees. The worker selects native local
vLLM, never another engine. Native vLLM may need loopback enabled inside its
namespace when namespace mode is selected; a failure is reported for qualification,
not retried with a different isolation mode. Two Sparks are not a transparent 256 GB GPU. Only the existing
GLM service distributes over both; OCR runs on the node executing this command.

A satisfactory Basic path can proceed without Standard. Specialist recognition
models are expected. The original probe targets GLM; the explicitly authorized
Flash Next experiments use their separately qualified exact local alias, as
recorded in the operator runbook. There is no automatic model substitution.

## Results and commands

Every command's exit code is meaningful: 0 completed its bounded task, 2 failed
or produced no valid result, 3 blocked conversion egress isolation, 75 paused for
memory, 130 interrupted. None certifies mathematical fidelity. `report` rebuilds
HTML/quality JSON from a conversion run; `bundle` makes another result ZIP.

```bash
.venv-control/bin/python probe.py report --run runs/EXACT_CONVERSION_DIRECTORY
python3 probe.py bundle --run runs/EXACT_RUN_DIRECTORY
```

An upload bundle contains its run's logs, requests/responses, selected source
windows and outputs. It excludes API keys, package environments, downloaded model
weights and other runs. Review bundles contain proposals and point to their
conversion/preflight run; send those ZIPs together. No upload occurs automatically.

For book-window TeX, adjacent context is intentionally duplicated. Final assembly,
cross-window reconciliation, safe TeX builds, persistent user overrides, an
interactive editor and the full-book worker remain future work. Do not concatenate
window exports and label the result a completed editable reconstruction.

## Validation and project continuity

`docs/VALIDATION.md` states what was tested in the authoring workspace and what
has not run on the Sparks. To repeat the offline suite after controller setup:

```bash
.venv-control/bin/python -m unittest discover -s tests -v
```

No test uses the real GLM address or downloads OCR weights. Local HTTP tests use
loopback mock servers. The package's `docs/PROJECT-STATE.md` separates implementation,
local validation and deployment status. Keep run folders and result bundles;
they are the evidence for the next decision, independent of conversation memory.

For the authorized annotated Gatheral derivative, section-output recovery and
subsequent Bergomi conversion/critics, see [the editorial continuation](docs/EDITORIAL-CHAPTERS.md).
It reuses completed OCR, preserves historical drafts, and attributes visible
corrections. This is an experimental working edition; successful JSON, generation
or compilation does not certify mathematical correctness. The isolated-development
bootstrap must finish its extraction and destination-conflict checks before copy-back.
