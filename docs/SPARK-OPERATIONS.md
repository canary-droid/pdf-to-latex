# Spark operations: saved OCR, portable export and page review

18 October 2026. Run these operator commands from the normal terminal on the
head Spark. Codex's development sandbox has no network access. This runbook
records existing launchers; the converter never manages services automatically.
No credentials belong in this repository.

## Operating rule and current evidence

For this deployment, use separate memory phases: stop GLM, verify memory, run
MinerU to completion and exit, restart regular GLM, verify endpoint/model
readiness, then review **saved** OCR. The operator recorded 7,181,922,304 available
bytes with GLM resident, below Basic's 8,589,934,592-byte admission floor. This is
the current operating rule, not a universal incompatibility. An unreachable
endpoint does not establish that weights have unloaded. Memory gates remain in
place; the project lock provides no host-wide exclusion.

The immediate fixture OCR is already complete. Reuse
`runs/convert-basic-20261018T182257Z-c99779`; both attempts passed saved integrity
checks and recorded MinerU 4.0.12 / DocVortex 0.5.16, CPU ONNX Basic. Both sources
have two pages. The independent
[fixture baseline](evidence/fixture-fidelity-baseline.md) records confirmed errors
and apparently correct content; the transcription remains unaccepted. Do not resume conversion
merely to use the new export code. No GLM document review has been run.

## 1. Run the offline tests

The operator reports 73 earlier offline tests passed after setup. The preparation
check now discovers 89 tests: 74 passed in the sandbox and 15 mock HTTP tests
were blocked at loopback socket creation (PermissionError, errno 1). The new full suite
must be checked in the normal terminal, where its mock loopback servers can run.
This command makes no live GLM requests or OCR calls.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m unittest discover -s tests -v
```

## 2. Inspect the already-generated portable export and offline preview

The portable profile is implemented in `probe/portable_export.py`; the `export`
command in `probe/cli.py` reads validated saved structured OCR, creates a new run,
and bundles it. It loads no models and needs no model endpoint. The original
native TeX, native structured data, page maps, input windows and assets are copied
under `evidence/`. Each of the four `pages/PAGE_ID/document.tex` files uses an
article preamble with packages selected from its actual content. All links and
image references used by the derivative are relative; move the entire ZIP tree.

The native renderer's fixed CJK preamble and auxiliary-block filtering were
inspected locally. This limited profile handles plain text, titles and recognized
math directly; it preserves math strings and inline boundaries without repairs.
Unsupported macros, Unicode, styles, tables or other block types remain explicit
unresolved content with raw JSON recognition and a source image. Unicode is shown
literally in HTML/JSON and as explicit JSON backslash-u escapes in the unresolved
TeX appendix. Supported aside text is retained but still flagged for source
review. Restored OCR is not corrected mathematics. There are no hard-coded label,
table, punctuation or formula corrections. `inventory.json` accounts for every
saved top-level block, with native nested content, source IDs and reading order.
There is no whole-document assembly or compilation claim. No TeX compiler was
available on the Spark; compilation is recorded as not run.

Open the generated derivative and exact offline input preview. They account for
all four fixture pages. The derivative reports 34 blocks: 32 represented and two
unresolved Unicode-bearing asides, with no silently omitted blocks.

```bash
xdg-open runs/export-english-math-20261018T204408Z-59d26b/review.html
xdg-open runs/review-input-20261018T204409Z-301420/review.html
```

The corresponding movable bundles are:

- `results/export-english-math-20261018T204408Z-59d26b-upload.zip`
- `results/review-input-20261018T204409Z-301420-upload.zip`

Preview limits are explicit: at most four owned pages, 48,000 text characters per
page including prompt/schema/data, one original image plus at most four detail
crops, 1 MiB and 2 million pixels per image, and a 2 MiB serialized request.
Original pages have a maximum edge of 1400 pixels; detail crops 1200. The default
page output budget is 8192 tokens (configurable 1024–16384) with a 300-second
request deadline (configurable 1–600). One page request is in flight at a time.
The old candidate/capability default remains 2048 tokens, capped at 4096.
The CLI preview budget switches are `--max-pages`, `--max-page-characters`,
`--page-max-tokens`, and `--page-timeout`. Live page review uses the saved preview's
selection and budgets. No server context settings change. Overflow is explicitly
incomplete/rejected, never silently truncated. Adjust the selection/budgets and
create a new preview if needed; review it before sending.

## 3. Check that OCR has exited

Before a live review, this tested read-only check identifies visible same-user
project converter processes. Review repeats it while holding the project writer
lock. Neither check guarantees exclusion of other projects or other users' jobs.
Do not infer that a stale run status or failed endpoint check proves a process
has exited. The immediate saved run needs no additional OCR.

```bash
.venv-control/bin/python -c 'from pathlib import Path; from probe.saved_pages import converter_idle; print(converter_idle(Path.cwd()))'
free -h
```

The Python command must return `owned_converter_pids: []` (in its printed
Python dictionary); if it raises an error or lists workers, wait and resolve that
state before continuing. `free -h` shows current memory and swap; it does not
prove process exit or authorize changes to memory thresholds.

## 4. Start regular GLM only if needed

First inspect the existing launcher's terminal/job state and query model
discovery. This read-only HTTP request lists served aliases, uses no proxy and
has a ten-second bound; it makes no generation request.

```bash
curl --noproxy '*' --fail --show-error --max-time 10 \
  http://192.168.1.100:8888/v1/models
```

If the intended `glm53-regular` service is already running, skip the start block.
A failed discovery request alone does not prove that GLM has stopped: an existing
launcher may still be loading or a service may be unhealthy. Check its existing
terminal/logs before starting another copy. Do not stop/restart a running job as
part of this sequence. If another model is active, defer review until the
operator has arranged the intended regular-model window.

After OCR has completed and its processes have exited, start the regular GLM
model if necessary using the existing launcher and environment. This block was
supplied by the operator and was not executed during development. Starting a
launcher alone is not proof of model/endpoint readiness.

```bash
(
  cd "$HOME/local-llm/glm53-flash-tensorfold" &&
  source "$HOME/venvs/menv_hf/bin/activate" &&
  ABLIT=0 ./start.sh
)
```

## 5. Run fresh preflight and inspect vision qualification

Reconcile the launcher's actual output with the intended regular model. The
expected alias is `glm53-regular` at `http://192.168.1.100:8888/v1`. No local config
file existed during this task, so these commands explicitly specify both. If the
launcher or `/models` disagrees, investigate the saved diagnostics and intended
weights rather than substituting another alias. The historical
`runs/preflight-20261017T205830Z-c8d5a6` records this alias and a qualified simple
image check, but it does not establish readiness after a restart.

This command performs the existing bounded discovery/text/JSON/image preflight.
It makes live local model calls, so **the operator runs it only when ready**.
It records the actual `/models` response and refuses a missing exact alias.
Each text, JSON and image result must report that exact selected model ID to
qualify its capability; a mismatch is recorded as failure with raw evidence.
A passing image check qualifies basic image input, not mathematical visual accuracy.

**Preflight exit status 0 establishes text success only.** It can still report
`vision: failed`, `unsupported` or `not_tested`. Before page review, require the
printed `Text: passed` and **`vision: qualified`**, and inspect the new run's
`model/capabilities.json`, including model identity and individual image cases.
The fresh run is necessary; historical evidence predates the identity fix.

```bash
.venv-control/bin/python probe.py preflight --ocr-isolation none \
  --base-url http://192.168.1.100:8888/v1 --model glm53-regular
```

Capture the actual `Preflight:` path printed by that command and display its
capability evidence. This reads saved JSON only; it makes no model request.
Do not invent a timestamped directory or reuse the historical preflight.

```bash
read -r -p 'Paste the new Preflight directory printed above: ' page_preflight_run
.venv-control/bin/python -m json.tool "$page_preflight_run/model/capabilities.json"
```

## 6. Run the existing four-page review

Proceed only with `selected_model: glm53-regular`, `text.status: passed` and
`vision.status: qualified` in that fresh evidence. If vision is unqualified,
retain the failed diagnostics and stop here; preflight exit 0 is insufficient.

Use the real new preflight directory captured above. The following command syntax
is parser-tested; no live page request was sent during development. It uses the
already-inspected four-page preview, revalidates its hashes and the saved OCR,
requires passing text/image capability evidence, and discovers the exact model
again. It loads no OCR models and executes no launcher. If JSON-schema capability
is unavailable, only the API's `response_format` wrapper is omitted; the full
schema remains in the prompt and strict local validation still applies. The
actual request and all raw responses are logged.

```bash
.venv-control/bin/python probe.py review --mode pages \
  --run runs/convert-basic-20261018T182257Z-c99779 \
  --preview runs/review-input-20261018T204409Z-301420 \
  --preflight "$page_preflight_run" \
  --base-url http://192.168.1.100:8888/v1 --model glm53-regular
```

Each response must name the page and every supplied block exactly once as
reviewed. Proposals identify affected blocks or a missing-region bounding box,
suggested LaTeX, a reason and uncertainty. Invalid references, wrong types,
malformed JSON, truncation, non-stop completions and model mismatches fail that
page and retain evidence. Exit 0 means full requested page-review coverage with
UNACCEPTED proposals; exit 2 means blocked/incomplete review. Partial success
never counts as full success. No proposal is applied. `summary.json` distinguishes
requested, completed, failed and pending pages. The HTML compares original OCR
with proposals and links original page/crop evidence. Inspect controls for new
errors as well as label association, omitted aside content, table structure and
punctuation. Grade against the source and the separately held known fixture TeX
and the independent [baseline](evidence/fixture-fidelity-baseline.md) only after
proposals exist. Do not send the answer key, baseline or corrected text to GLM.

## 7. Open and bundle the UNACCEPTED proposals

Use the real new page-review directory printed by the command. It already has a
result ZIP; `bundle` below creates an additional ZIP if needed. Send the reports
for inspection before deciding whether to accept changes or produce a corrected
derivative. No acceptance command is implemented.

```bash
read -r -p 'Paste the Page review run directory printed above: ' page_review_run
xdg-open "$page_review_run/review.html"
.venv-control/bin/python probe.py bundle --run "$page_review_run"
```

`xdg-open` opens the comparison report; `bundle` packages that review run in
`results/` and prints its ZIP path. It does not apply proposals or upload files.
Retain the fresh preflight ZIP and the existing conversion/preview ZIPs alongside
the review ZIP so its evidence references remain inspectable.

The existing `review --mode candidates --run ... --preflight ...` workflow remains
available and is still the default mode. It is a bounded candidate sample, not
full page coverage; raising its candidate limit does not replace page review.

## Reference only: optional offline regeneration and future OCR

The morning sequence above reuses the existing export and preview. These
reference commands are not additional morning steps.

To repeat the offline export, this tested command creates another derivative
run and result ZIP, without altering the completed OCR or its fingerprints.

```bash
.venv-control/bin/python probe.py export \
  --run runs/convert-basic-20261018T182257Z-c99779 \
  --source fixture-native,fixture-scan --profile english-math
```

To prepare another preview, this tested syntax renders the original pages,
kind-selected equation/aside/table crops and explicit crops from the JSON plan.
`docs/fixture-review-crops.json` selects only geometric regions and clockwise
rotations, with no corrected answers. The original view remains available beside
the upright aside view. Both normalized boxes and PDF-point boxes are recorded;
image records retain the PDF-to-raster matrix and raster origin as well as the
clockwise rotation. `probe/saved_pages.py` validates original source hashes,
completed outputs and owned/context mappings; it includes each owned page once.
`probe/page_review.py` records complete native block content and per-block drafts
in the exact prepared request. The known fixture TeX is never an input.

```bash
.venv-control/bin/python probe.py review --mode pages --preview-only \
  --run runs/convert-basic-20261018T182257Z-c99779 \
  --source fixture-native,fixture-scan \
  --model glm53-regular --base-url http://192.168.1.100:8888/v1 \
  --crop-plan docs/fixture-review-crops.json
```

For **future OCR only**, stop the existing two-node GLM deployment with its own
previously established stop script, then inspect memory and other workloads.
This block was supplied by the operator and was not executed during development.
Do not substitute kill commands, change server parameters or lower memory gates.

```bash
(
  cd "$HOME/local-llm/glm53-flash-tensorfold" &&
  ./stop.sh
)
free -h
```

