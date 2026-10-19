# PDF-to-LaTeX compatibility and fidelity probe 0.1

Start with **START-HERE.md**. This package implements design 1.1's milestone 0B;
it is a bounded diagnostic package, not the later application. All inference is
local. No OpenRouter feature or credential is supported.

For the completed fixture OCR and the next page-review experiment, use
[docs/SPARK-OPERATIONS.md](docs/SPARK-OPERATIONS.md). `export --run ...` creates a
portable English/math derivative from saved OCR. `review --mode pages
--preview-only --run ... --model ...` prepares complete page inputs offline;
`review --mode pages --run ... --preview ... --preflight ... --model ...` sends
them serially to the validated local model and saves UNACCEPTED proposals. No
command applies proposals. The runbook gives actual saved paths, bounds and the
separate OCR/GLM memory-phase procedure. Candidate review remains the default.

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
models are expected; GLM remains the only general-purpose LLM in this probe.

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
