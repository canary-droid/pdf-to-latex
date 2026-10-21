# Spark operations: saved OCR, portable export and page review

Updated 20 October 2026 (Europe/London). Run these operator commands from the normal terminal on the
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
merely to use the new export code. The first four-page GLM trial exhausted its
output budget on every page. A subsequent two-page native trial completed only
page 2; its four proposals remain UNACCEPTED. See the dated project state for
the preserved results.

## Current trial: resumable 100-page Klebaner review

Prepared offline on 20 October 2026; **no batch inference has run**. The actual
preview is `runs/review-batch-input-20261020T195337Z-32f118`, with inspection ZIP
`results/review-batch-input-20261020T195337Z-32f118-upload.zip` (about 300 MB).
It covers exactly selected pages 1–100 / original physical PDF 106–205 of
`klebaner-ch4-7`, with 1,623 recognized blocks and no duplicate overlap pages.
Its 396 sequential units comprise nine whole-page checks, 296 block groups and
91 separate full-page visual omission checks. Every target block is assigned
once and every page has a visual check for content absent from OCR.

The source conversion remains `runs/convert-basic-20261020T075104Z-48fd90`.
The paragraph retry `runs/review-regions-20261020T192708Z-997831` completed with
one unaccepted proposal; it did not establish mathematical accuracy. The batch
uses the clarified source-authority instructions, medium reasoning effort,
16,384 output tokens and a 600-second timeout per request, with existing server
sampling defaults. No expected corrections or prior proposals enter requests.
See the [batch evidence and limits](evidence/klebaner-100-page-batch.md).

### Tests, OCR exit and preview inspection

Run these personally in the normal terminal:

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m unittest discover -s tests -v
.venv-control/bin/python -c 'from pathlib import Path; from probe.saved_pages import converter_idle; print(converter_idle(Path.cwd()))'
xdg-open runs/review-batch-input-20261020T195337Z-32f118/review.html
```

The tests use offline fixtures/mock servers. The final sandbox run had 118 passes out
of 133 tests; all 15 errors were denied mock-server socket creation, not assertion
failures. No permissions were changed. The process check must show an empty
`owned_converter_pids` list; it checks visible same-user project processes, not
host-wide exclusion. The HTML displays the page map, coverage plan, source images
and exact prepared draft/request links. No OCR needs to be rerun.

### Persistent terminal, endpoint check and fresh preflight

`tmux` 3.4 is installed. Start or reattach a named persistent terminal:

```bash
tmux new-session -A -s klebaner100
```

Run the remaining launch steps **inside that tmux shell** so their variables and
job survive a remote-desktop disconnect. This opens a terminal session; it does
not manage the model server. In it:

```bash
cd /home/mdi/projects/pdf-to-latex
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8890/v1/models
.venv-control/bin/python probe.py preflight --ocr-isolation none \
  --base-url http://127.0.0.1:8890/v1 --model flash-next-tensorfold
read -r -p 'Paste the actual new Preflight directory printed above: ' batch_preflight
.venv-control/bin/python - "$batch_preflight" <<'PY'
import json, sys
from pathlib import Path
caps = json.loads((Path(sys.argv[1]) / 'model/capabilities.json').read_text())
print('Text:', caps['text']['status'], '| vision:', caps['vision']['status'],
      '| strict JSON:', caps['strict_json']['status'])
assert caps['endpoint'] == 'http://127.0.0.1:8890/v1'
assert caps['model_discovery']['selected_model'] == 'flash-next-tensorfold'
assert caps['text']['status'] == 'passed'
assert caps['vision']['status'] == 'qualified'
PY
```

The first request checks discovery; require the exact `flash-next-tensorfold`
alias. Preflight makes fresh bounded text/JSON/vision calls and records their
evidence. Require **Text: passed** and **vision: qualified** before continuing;
exit status alone is insufficient. Strict JSON may remain unsupported because
xgrammar is absent. The review omits only `response_format` in that case; its
prompt schema and local JSON/identity/coverage validation remain required.
The existing preflight at `runs/preflight-20261020T181856Z-070d9b` is preserved.
No future preflight path is assumed by these commands.

### Use the prepared inputs and launch

Still in the tmux shell, select the already-prepared preview and launch:

```bash
batch_preview=runs/review-batch-input-20261020T195337Z-32f118
batch_log="runs/klebaner100-$(date -u +%Y%m%dT%H%M%SZ).log"
set -o pipefail
.venv-control/bin/python -u probe.py review-batch \
  --preview "$batch_preview" --preflight "$batch_preflight" \
  --base-url http://127.0.0.1:8890/v1 --model flash-next-tensorfold \
  2>&1 | tee "$batch_log"
```

This creates a **new** live result directory, prints `Batch review run:` before
dispatch, binds the actual preflight and sealed inputs, and discovers the exact
model again. It sends requests sequentially and checkpoints every reservation
and outcome. Progress includes current unit, attempt number, completed/failed/
pending counts, retry eligibility, completed page checks, elapsed execution time
and the output directory. `tee` preserves the terminal log under ignored `runs/`.
Record the printed result directory; it is not the input preview directory.

Press **Ctrl-b, then d** to detach tmux while the job continues. A desktop
disconnect also leaves the session running. Reattach from a terminal with:

```bash
tmux attach -t klebaner100
```

This does not protect against host reboot or power loss; use resume after those
events. Do not launch another batch in parallel. The project writer lock guards
project mutations, not unrelated server or OCR processes.

If you want to prepare a separate new preview instead of using the one above,
this is the exact offline preparation command. It renders only from saved source
PDF windows and makes no model calls or OCR runs:

```bash
.venv-control/bin/python probe.py review-batch --preview-only \
  --run runs/convert-basic-20261020T075104Z-48fd90 \
  --source klebaner-ch4-7 --first-page 1 --page-count 100 \
  --page-max-tokens 16384 --page-timeout 600 --page-reasoning-effort medium \
  --base-url http://127.0.0.1:8890/v1 --model flash-next-tensorfold
read -r -p 'Paste the actual new Batch preview directory printed above: ' batch_preview
```

Inspect that new preview and use its actual path for a **new** launch. Never
substitute a different preview into an existing job's resume command.

### Monitor, pause, resume and bundle

In another terminal, use the actual live result path printed in tmux/the log:

```bash
cd /home/mdi/projects/pdf-to-latex
read -r -p 'Paste the Batch review run directory: ' batch_run
watch -n 15 -x .venv-control/bin/python probe.py batch-status --run "$batch_run"
```

`batch-status` reads the last atomic checkpoint without taking the writer lock.
`watch` refreshes it every 15 seconds; Ctrl-C here stops only the monitor. The
current unit may take up to 600 seconds; elapsed time and reports update at
checkpoints. Open `"$batch_run/review.html"` to inspect page-grouped results.

To pause the job, press **Ctrl-C in its tmux job pane**, then wait for the shell
prompt. It preserves the interrupted attempt and writes a partial report/ZIP;
this does not stop the model service. Two consecutive connection failures also
pause automatically. Check endpoint availability before resuming. After a hard
kill/disconnect that killed the process, the server may still be finishing its
last request; inspect activity before resuming it.

In tmux, resume the same live result directory (paste it again if this is a new
shell). Successful units are skipped; each failed/interrupted unit has at most
one retry across all resumes:

```bash
read -r -p 'Paste the existing Batch review run directory to resume: ' batch_run
batch_log="runs/klebaner100-resume-$(date -u +%Y%m%dT%H%M%SZ).log"
set -o pipefail
.venv-control/bin/python -u probe.py review-batch --resume "$batch_run" \
  --base-url http://127.0.0.1:8890/v1 --model flash-next-tensorfold \
  2>&1 | tee "$batch_log"
```

Resume uses the same bound preview and actual fresh preflight from the first
launch; no budget override is accepted. Changed source, requests, preflight,
model or settings refuse resume. Changed response model or detected integrity
failure stops execution rather than retrying a different model or altered input.
Inspect such a stopped run and prepare a separate job after resolving the cause.
Two total attempts include interrupted reservations; no retry-reset option exists.
Isolated exhausted failures leave explicit coverage gaps while other units run.

After the job pauses or completes, regenerate its report and make an inspection
bundle if needed (the runner also bundles automatically when it returns):

```bash
.venv-control/bin/python probe.py report --run "$batch_run"
xdg-open "$batch_run/review.html"
.venv-control/bin/python probe.py bundle --run "$batch_run"
```

The bundle command prints the actual ZIP under `results/`. Repeated bundling
chooses a fresh filename and preserves older ZIPs. Partial runs are supported;
pause first so the writer lock prevents an inconsistent in-flight snapshot.
Reports link source images, original drafts, all attempts, proposed LaTeX and
unresolved issues. All proposals stay **UNACCEPTED**. Completed JSON or coverage
is never a mathematical-correctness claim. Applying batch proposals is outside
this milestone. Hidden server weights/sampling changes behind an unchanged alias
cannot be certified by the client; do not change the deployment during the job.

## Earlier trial: one-paragraph Klebaner follow-up

The original three-region run `runs/review-regions-20261020T185933Z-7075bd`
finished with partial coverage. Paragraph `klebaner-ch4-7-p0001:b4` exhausted
all 16,384 tokens as reasoning with `finish_reason: length` and no final content.
Its diagnostic repeatedly treats OCR and the printed images as competing
authorities. The other two requests completed; their one proposal remains
UNACCEPTED. All existing evidence is preserved.

The retry, subsequently completed in `runs/review-regions-20261020T192708Z-997831`,
contains only that paragraph (printed 91 / original
PDF 106). Its source image, crop, OCR draft, context and schema are unchanged.
The generic prompt now explicitly makes the images authoritative, identifies
OCR-derived material as potentially erroneous, distinguishes printed errors
from OCR mistakes, and requires uncertainty for unreadable details. There are
no expected corrections or specific diagnoses in the request. See the
[independent retry record](evidence/klebaner-paragraph-retry.md).

Run the full tests in the normal terminal using step 1 below. Inspect the new
preview, then check that project OCR workers have exited:

```bash
cd /home/mdi/projects/pdf-to-latex
xdg-open runs/review-regions-input-20261020T191957Z-311b42/review.html
.venv-control/bin/python -c 'from pathlib import Path; from probe.saved_pages import converter_idle; print(converter_idle(Path.cwd()))'
```

The first command opens local HTML. The second is a read-only process check;
`owned_converter_pids` should be empty. Preview ZIP:
`results/review-regions-input-20261020T191957Z-311b42-upload.zip`.

Execute this live command personally when ready; it was not run by Codex:

```bash
.venv-control/bin/python probe.py review --mode regions \
  --run runs/convert-basic-20261020T075104Z-48fd90 \
  --preview runs/review-regions-input-20261020T191957Z-311b42 \
  --preflight runs/preflight-20261020T181856Z-070d9b \
  --base-url http://127.0.0.1:8890/v1 --model flash-next-tensorfold
```

It revalidates saved evidence and exact model/endpoint identity, then sends one
request with saved `reasoning_effort=medium`, 16,384 output tokens, 600-second
timeout and `stream=false`. Local deployment documentation supports medium;
the saved retry completed with one unaccepted proposal. Sampling inherits server settings.
The preflight still reports passing text, four passing simple vision controls
and unsupported strict JSON. Only `response_format` is omitted at dispatch;
the prompt schema and all local response/identity/evidence checks remain in force.
All proposals remain UNACCEPTED and coverage is only the selected paragraph.

Use the actual result directory printed by that command:

```bash
read -r -p 'Paste the Page review run directory printed above: ' paragraph_review_run
xdg-open "$paragraph_review_run/review.html"
ls -l "results/$(basename "$paragraph_review_run")-upload.zip"
```

These commands open the result report and locate its ZIP; nothing is uploaded.
To reproduce preparation offline, creating a separate new preview:

```bash
.venv-control/bin/python probe.py review --mode regions --preview-only \
  --run runs/convert-basic-20261020T075104Z-48fd90 \
  --source klebaner-ch4-7 --block-selection docs/klebaner-paragraph-retry-blocks.json \
  --max-pages 1 --page-max-tokens 16384 --page-timeout 600 \
  --page-reasoning-effort medium \
  --base-url http://127.0.0.1:8890/v1 --model flash-next-tensorfold
```

New focused previews record prompt version 2; older sealed previews keep their
original version-1 instructions and still validate. This does not change the
whole-page prompt, preflight behavior or acceptance requirements.

## Initial three-region Klebaner experiment (historical commands)

Prepared offline on 20 October 2026 and subsequently executed in the partial
review recorded above. The commands in this section describe that initial trial;
use the one-paragraph follow-up above for the next live call. This user-requested
experiment uses `flash-next-tensorfold` at `http://127.0.0.1:8890/v1`, separately
from the GLM fixture workflow below. Do not use the GLM launcher or its preflight
for this trial. No service or server settings were changed during preparation.

The completed conversion is `runs/convert-basic-20261020T075104Z-48fd90`.
Its 120 owned pages and 15 completed windows passed saved-evidence validation.
The saved preflight `runs/preflight-20261020T181856Z-070d9b` records **Text:
passed**, **vision: qualified** (all four simple controls), and **strict JSON:
unsupported** because xgrammar is unavailable. Preserve that result; no package
installation is needed for this review path. Exit status alone does not establish
vision qualification, and simple controls do not establish mathematical fidelity.

The preview `runs/review-regions-input-20261020T185019Z-5a9907` contains:

| Selected block | Printed / original PDF page | Comparison |
|---|---|---|
| `klebaner-ch4-7-p0001:b4` | 91 / 106 | Paragraph containing OCR defects |
| `klebaner-ch4-7-p0065:b14` | 155 / 170 | Nested exponential/integral |
| `klebaner-ch4-7-p0001:b7` | 91 / 106 | Visually checked equation (4.1) control |

Each request includes an enlarged source crop, full-page context, neighboring
OCR blocks and the corresponding saved draft. The model receives no diagnoses,
expected answers or control labels. It must preserve source errors rather than
repair the author's mathematics. Read the independent
[selection and validation record](evidence/klebaner-flash-next-experiment.md).

Run the full offline tests in the normal terminal using step 1 below. Inspect
the already-prepared inputs:

```bash
cd /home/mdi/projects/pdf-to-latex
xdg-open runs/review-regions-input-20261020T185019Z-5a9907/review.html
```

This opens local HTML only. The movable inspection bundle is
`results/review-regions-input-20261020T185019Z-5a9907-upload.zip`.
To check that same-user project OCR/conversion processes have exited:

```bash
.venv-control/bin/python -c 'from pathlib import Path; from probe.saved_pages import converter_idle; print(converter_idle(Path.cwd()))'
```

An empty `owned_converter_pids` list is the expected result. This read-only
check is repeated by live review; it is not a host-wide process lock.

Original live command, retained for reproducibility:

```bash
.venv-control/bin/python probe.py review --mode regions \
  --run runs/convert-basic-20261020T075104Z-48fd90 \
  --preview runs/review-regions-input-20261020T185019Z-5a9907 \
  --preflight runs/preflight-20261020T181856Z-070d9b \
  --base-url http://127.0.0.1:8890/v1 --model flash-next-tensorfold
```

It verifies the saved conversion, preview, model/endpoint agreement and current
model discovery, then sends three requests serially. Saved settings are
`reasoning_effort=high`, 16,384 output tokens, 600-second timeout and
`stream=false`. Sampling parameters inherit the server configuration; the local
recipe documents top-level `high` support and records thinking enabled.
The recorded request/image budgets are in the independent evidence document.
Those settings were used in the original partial review; completion did not
establish fidelity. Re-preparing now uses prompt version 2, whereas the sealed
original preview retains version 1.

Because this preflight reports strict JSON unsupported, live dispatch omits
only `response_format` from the canonical preview request. The schema remains
in the prompt and returned JSON must pass all existing local schema, scope,
block-ID, exact-model and non-truncation checks. Raw failures are retained.
All proposals remain UNACCEPTED, with selected-block coverage only.

Open and locate the result using the directory actually printed by the command:

```bash
read -r -p 'Paste the Page review run directory printed above: ' flash_review_run
xdg-open "$flash_review_run/review.html"
ls -l "results/$(basename "$flash_review_run")-upload.zip"
```

The report displays results/failures; `ls` locates the automatically created ZIP.
Nothing is uploaded automatically. No live-result directory is invented here.

To reproduce the preparation offline, use a new preview run:

```bash
.venv-control/bin/python probe.py review --mode regions --preview-only \
  --run runs/convert-basic-20261020T075104Z-48fd90 \
  --source klebaner-ch4-7 --block-selection docs/klebaner-flash-next-blocks.json \
  --max-pages 2 --page-max-tokens 16384 --page-timeout 600 \
  --page-reasoning-effort high \
  --base-url http://127.0.0.1:8890/v1 --model flash-next-tensorfold
```

This makes no model requests. Omitting `--derivative` selects saved OCR drafts;
the damaged equation is retained as raw comparison data even though the
conservative exporter rejects it. No acceptance is fabricated and no export
validation is relaxed. Unsupported non-equation drafts remain explicit blockers.
The original derivative-based and whole-page modes remain available.

## Earlier fixture checkpoint: accepted derivative and focused region trial

The high-effort whole-page run `runs/review-pages-20261019T224212Z-e0f284`
completed both native pages in 46.85 seconds of summed request latency. It used
`runs/review-input-20261019T224021Z-4aea11`. Page 1 proposed no changes despite
remaining fidelity defects. Page 2 supplied four proposals. Completion and
block coverage do not establish fidelity. The low review at
`runs/review-pages-20261019T223423Z-f95dcd` and all earlier evidence are preserved.

The operator explicitly authorized only page-2 b0, b3, b4 and b5. The new
`runs/accepted-derivative-20261019T230916Z-969d30` applies three replacements and
one deletion. b3/b4/b5 are an atomic correction group. All 17 native blocks are
accounted for: 13 unchanged, three replaced and one explicitly deleted. The
missing page-1 comma and the table's bare mathematical headings remain unresolved.
Zero unsupported renderer blocks does **not** mean zero fidelity issues. No TeX
compilation has occurred. Read the before/after report and acceptance ledger:

```bash
xdg-open runs/accepted-derivative-20261019T230916Z-969d30/review.html
xdg-open runs/review-regions-input-20261019T230924Z-93edf1/review.html
```

These commands open local HTML only. The derivative retains source images,
original structured OCR and a byte-identical copy of the high review, including
its upright aside crop. Original proposals still say UNACCEPTED; the separate
`acceptance.json` records the user's selection. The portable ZIP is
`results/accepted-derivative-20261019T230916Z-969d30-upload.zip`.

The **not-yet-executed** focused preview is
`runs/review-regions-input-20261019T230924Z-93edf1`. It contains three serial
requests, each with a complete page image for context and one source-region crop:

| Source block | Comparison |
|---|---|
| `fixture-native-p0001:b1` | Paragraph with inline mathematical distinctions |
| `fixture-native-p0001:b4` | Table draft |
| `fixture-native-p0001:b2` | Unchanged F.1 equation control |

Each request uses `reasoning_effort=high`, 16,384 generation tokens and a
600-second timeout. Only the selected block is counted as reviewed. Neighboring
OCR blocks and the complete source image provide context, never full-page
coverage. The prompt asks general checks of punctuation, symbols, conditions,
units and rendered LaTeX meaning. No known answers, baseline, acceptance issues
or fixture TeX enter these requests. All three drafts match the original
whole-page preview exactly. The inspection ZIP is
`results/review-regions-input-20261019T230924Z-93edf1-upload.zip`.

First run the normal-terminal tests in step 1 and the converter-exit check in
step 3. If regular GLM is already running, skip the launcher in step 4. The saved
preflight `runs/preflight-20261019T215021Z-23ef86` reports passing text and qualified
simple vision for `glm53-regular` at the endpoint below. If the server/launcher
has changed since that preflight, use step 5 and substitute its **actual** newly
printed preflight directory. Text success or preflight exit 0 alone is insufficient;
require both **Text: passed** and **vision: qualified**.

Run this live command personally when ready; it was **not executed** during
development:

```bash
.venv-control/bin/python probe.py review --mode regions \
  --run runs/convert-basic-20261018T182257Z-c99779 \
  --preview runs/review-regions-input-20261019T230924Z-93edf1 \
  --preflight runs/preflight-20261019T215021Z-23ef86 \
  --base-url http://192.168.1.100:8888/v1 --model glm53-regular
```

It revalidates the bound OCR, derivative and exact preview, checks converter exit
and model discovery, and sends the three selected-region requests serially.
Saved budgets and reasoning effort are used; there is no live CLI override.
The result uses `completed_regions` and `coverage: selected_regions_complete`
if all three responses validate, with `full_page_coverage: false`. This is not
proof of correctness. All resulting proposals remain UNACCEPTED. Acceptance of
focused responses is deliberately deferred in this milestone.

Use the actual paths printed by that command:

```bash
read -r -p 'Paste the Page review run directory printed above: ' focused_review_run
xdg-open "$focused_review_run/review.html"
ls -l "results/$(basename "$focused_review_run")-upload.zip"
```

`xdg-open` opens the result report; `ls` locates its automatically generated ZIP.
No upload is automatic. The live result directory cannot be named before the
operator runs the command. Keep the original derivative sealed on the Spark;
compiling into it would change its manifest and correctly block reuse.

### Compile a separate copy on the laptop

Transfer `results/accepted-derivative-20261019T230916Z-969d30-upload.zip` to the
laptop. In the directory containing that ZIP, use an existing TeX installation:

```bash
unzip accepted-derivative-20261019T230916Z-969d30-upload.zip
cp -R accepted-derivative-20261019T230916Z-969d30 accepted-derivative-20261019T230916Z-969d30-build
(
  cd accepted-derivative-20261019T230916Z-969d30-build/pages/fixture-native-p0001 &&
  pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode document.tex
)
(
  cd accepted-derivative-20261019T230916Z-969d30-build/pages/fixture-native-p0002 &&
  pdflatex -no-shell-escape -halt-on-error -interaction=nonstopmode document.tex
)
```

Extraction preserves the movable tree; the copy isolates build artifacts from
the sealed derivative. Each command compiles one actual `document.tex` from its
own directory, preserving relative asset paths. Inspect both resulting
`document.pdf` files and logs. These are two per-page drafts, not an assembled
chapter. Packages are `amsmath`, `amssymb` and (page 2) `graphicx`; there is no CJK
preamble. No compiler is installed or invoked by this task, and no TeX success is
claimed. Retain unresolved page-1 issues even if compilation succeeds.

### Reproduce or select a different bounded experiment offline

The saved project acceptance plan is
`docs/evidence/fixture-native-acceptance.json`; it binds source/review manifests,
preview manifest, stable proposal IDs and exact target-block hashes. Only the
`selected` list authorizes edits. `correction_groups` lists proposal IDs that
must be selected together. `uncertain: false` is never acceptance. Unknown IDs,
changed evidence, repeated/conflicting edits and partial groups fail before
export. Groups are explicit operator declarations; the program does not infer
semantic dependencies. The current label group must remain intact.

For a future saved **whole-page** review, prepare an empty selection with
`accept-plan --run CONVERSION --review REVIEW --preview PREVIEW`. It prints a
new `selection.json` with no authorization or selected proposals. Copy it to a
new operator file, inspect the catalog, record explicit `authorization`, add
`selected` entries with `proposal_id` and `operation: replace` or `delete`, and
declare any dependent groups before applying. Replacement text comes only from
the bound saved suggestion, never an alternate string in the selection.
An empty suggestion requires explicit deletion. Multi-block edits, insertion of
missing regions, merges/splits and arbitrary TeX macros are deferred. The narrow
replacement grammar handles display math, ordinary prose/inline math and an
outer right-angle `rotatebox`, using the existing conservative math allowlist.
This is not a general TeX security sandbox or proof of compilability.

These optional commands create **new** runs, not overwrites; there is no need to
repeat them for the prepared trial:

```bash
.venv-control/bin/python probe.py apply-accepted \
  --plan docs/evidence/fixture-native-acceptance.json

.venv-control/bin/python probe.py review --mode regions --preview-only \
  --run runs/convert-basic-20261018T182257Z-c99779 \
  --derivative runs/accepted-derivative-20261019T230916Z-969d30 \
  --block-selection docs/fixture-focused-blocks.json --max-pages 1 \
  --page-max-tokens 16384 --page-timeout 600 --page-reasoning-effort high \
  --base-url http://192.168.1.100:8888/v1 --model glm53-regular
```

The first uses the explicitly authorized plan and produces a new derivative,
report, provenance and ZIP. The second renders and serializes three exact inputs
without discovery or inference. A block selection contains only `block_ids`,
with one to four distinct blocks with usable drafts and source boxes; sources
come from the bound derivative when `--derivative` is supplied. For a saved-OCR
comparison without acceptance, omit it and pass `--source`, as above.
Change selection in a new file to prepare another small experiment, never add
expected answers or modify completed previews. Output can overflow explicitly;
evidence is never silently truncated.

Whole-page mode and old previews are preserved. The effort options remain
`server-default`, `low`, `medium`, `high` and `max`; omission/server-default sends no API
field. Preflight is unchanged. Read-only local TensorFold support was previously
verified in its README, effort patch and regular-model template; no server files
or settings were changed here. New focused live behavior remains untested.

The numbered sections below retain the original four-page GLM workflow as a
reference. For the current Klebaner trial, use the Flash Next command above
instead of steps 4–6.

## 1. Run the offline tests

The operator reports 73 earlier offline tests passed after setup. The earlier
accepted-derivative milestone discovered 111 tests. Its full sandbox run had 95 passes, 15 mock HTTP
socket-creation errors (PermissionError, errno 1), and one diagnostic-text assertion
failure. The diagnostic was corrected; all 17 saved-page regression tests then
passed. Thus 96 distinct tests passed across those runs, including all 16 new
acceptance/focused tests; 15 remain sandbox-blocked. Run the full suite in the
normal terminal, where its mock loopback servers can run.
This command makes no live GLM requests or OCR calls.

The Flash Next preparation adds five focused saved-OCR tests. All 38 relevant
tests passed (21 acceptance/focused plus 17 saved-page tests), including actual
client serialization through an in-memory transport with no sockets. Python
compilation and `git diff --check` passed. The full suite was not rerun during
this preparation; no sandbox settings were changed.

The paragraph follow-up adds three regression tests and extends effort coverage
to medium. Its 42 relevant checks passed: 24 acceptance/focused, 17 saved-page
and one client effort-validation test. Python compilation and `git diff --check`
also passed. The full suite was not rerun; use the normal-terminal command below.

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
selection and budgets. `--page-reasoning-effort` additionally selects the saved
reasoning effort during preview creation only. No server context settings change. Overflow is explicitly
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
For this initial workflow, use the fresh result. The current focused trial above
identifies a later passing preflight recorded after the identity fix.

```bash
.venv-control/bin/python probe.py preflight --ocr-isolation none \
  --base-url http://192.168.1.100:8888/v1 --model glm53-regular
```

Capture the actual `Preflight:` path printed by that command and display its
capability evidence. This reads saved JSON only; it makes no model request.
Do not invent a timestamped directory. This capture step applies when running
fresh preflight, not when reusing the verified preflight named in the current trial.

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
derivative. The separate explicit-selection mechanism above now supports this
bounded step; review and bundle commands themselves never apply proposals.

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

To prepare another native-only low-effort preview with the same controlled
settings, this offline command creates a new run and ZIP; it does not overwrite
any completed evidence or contact GLM:

```bash
.venv-control/bin/python probe.py review --mode pages --preview-only \
  --run runs/convert-basic-20261018T182257Z-c99779 \
  --source fixture-native --max-pages 2 \
  --page-max-tokens 16384 --page-timeout 600 --page-reasoning-effort low \
  --model glm53-regular --base-url http://192.168.1.100:8888/v1 \
  --crop-plan docs/fixture-native-review-crops.json
```

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


## Proposed next chapter trial — not launched

The currently registered `book` is Chapter 3 of Boyarchenko/Levendorskii,
*Non-Gaussian Merton–Black–Scholes Theory*: 30 selected pages at
`inputs/book/source.pdf`, original physical pages 89–118 (printed 67–96), forced
OCR. Its registered SHA-256 is
`3f56ca665560dcf21f2fc09845812f353e22bf4c9c284de526a5d0abd25bcc46`, verified locally
with its 30-page count. The full 421-page book is not the registered input.

After inspecting the focused fixture results and laptop PDFs, the proposed next
trial is Basic OCR of this existing chapter selection in the separately arranged
OCR memory phase, followed by source-based inspection of a small saved-page sample
and explicit review of any proposals. Use the existing `convert --source book
--tier basic --ocr-isolation none` workflow only when the operator has arranged
that window and the unchanged memory gate passes. Do not rerun the fixtures or
start a full-book conversion. Chapter OCR, fidelity qualification and assembled
chapter export have not been performed by this task.
