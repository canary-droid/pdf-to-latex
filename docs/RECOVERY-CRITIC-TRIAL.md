# Recovery and text-critic experiment — current handover 25 October 2026

## Task 2 integration update — development copy, 25 October 2026

Completed critic trials remain frozen. New critic preparations use v3 program-owned
bindings and narrowly scoped field repair; see [CANDIDATE-CRITIC.md](CANDIDATE-CRITIC.md).
The explicit `probe.book_review` adapter reuses this recovery executor, conservative
fragment validation and isolated compiler for completed ordinary owned-page OCR.
It adds no OCR engine or scheduler. See [GATHERAL-REVIEW.md](GATHERAL-REVIEW.md) for
its small gate followed by continuation of the same preparation. Omission checks
are separate from block review; insertion proposals stay deferred. No actual
Gatheral preview or model readiness has been prepared during extraction.
Integration must follow [TASK2-DEVELOPMENT.md](TASK2-DEVELOPMENT.md); changed code
must never be copied into an unfinished extraction checkout.

## Current operator scope: candidate-only GLM, then selected MiMo

Use [CANDIDATE-CRITIC.md](CANDIDATE-CRITIC.md) for the eight-passage preparation,
automatic readiness paths, status/pause/resume and costed second-opinion selection.
Both arms of the twelve-passage [comparison](GLM-MIMO-CRITIC-PILOT.md) are completed
and frozen. Do not replay them. GLM is the default text critic; Qwen still owns
source-image comparison. The USD 10 shared cost ceiling includes prior paid costs.
The user explicitly accepts documented provider
retention below 100 days for published nonpersonal book material; Xiaomi's published
30-day retention qualifies. No mandatory ZDR lookup, training opt-in, account privacy
change, provider fallback or cloud conversion is introduced.

The operator's overnight DeepSeek development stage has now **finished gate_failed**:
12 baseline calls plus two quotation repairs; 7/12 first valid, 9/12 final valid,
6/12 complete claimed coverage. Three responses exhausted output without final
content. No reserved g11–g20 calls ran. This supersedes only the preparation status
below; its inputs, attempts and historical instructions remain unchanged. The new
pilot reuses these saved results as reference, without new DeepSeek inference.

## Historical preparation: frozen overnight critic continuation (24 October)

The revised eight-unit gate passed: **7 first valid / 8 final valid / 7 complete
claimed coverage**, nine calls in 39.08 minutes. Its JSON escape failure was repaired.
All findings remain UNACCEPTED. The [separate ChatGPT assessment](evidence/critic-overnight-20261024.md)
checks source quotations and explains which warnings are useful, context-dependent
or misleading. It is not human gold and is excluded from model inputs.

This newly authorized experiment runs g05–g10 (12 development reviews), then
**automatically** g11–g20 only if the frozen technical checkpoint passes:
**9/12 first valid, 12/12 final valid, 9/12 complete claimed coverage**, and no
unresolved identity/integrity failure. Reserved has 20 planned slots, 19 callable:
g16-Y stays unavailable; g16-X is unpaired; paired comparisons have nine available
pairs. The unavailable slot and all failures/pending work remain in reports. The shared executor may
finish as `completed_with_failures` solely because g16-Y is unavailable; inspect
the separate failed/unavailable counts rather than treating that status as a model failure.
No replay of g01–g04, no prompt/context/candidate edits or human tuning between stages.
The reserved set is used once: after inspection it cannot be described as unseen
for future revisions. Later tuning requires new reserved material.

Actual prepared artifacts (zero live calls):

- Preview: `runs/text-critic-overnight-input-20261024T211031Z-de4d3d`.
- Run: `runs/text-critic-overnight-trial-20261024T211031Z-63fbda`.
- Report: `runs/text-critic-overnight-trial-20261024T211031Z-63fbda/overnight/report.html`.
- Initial ZIP: `results/text-critic-overnight-trial-20261024T211031Z-63fbda-inspection-20261024T211034Z-459c8b.zip`.
- Source/gate assessment: `runs/critic-overnight-audit-20261024T211110Z-d3f875`.
- Combined preparation + separate source-assessment ZIP (1240290 bytes):
  `results/critic-overnight-preparation-20261024T211031Z-de4d3d-inspection.zip`.
- Pointer with exact paths: `results/critic-overnight-current.json`.

Frozen settings match the passed follow-up: regular `DeepSeek-V4.1-Flash-TF` at
`http://127.0.0.1:8894/v1`, requested medium, 32768 output tokens, 900-second timeout,
serial, non-streaming and unchanged sampling defaults. Effective server interpretation
of medium remains unknown; lower-reasoning recovery is disabled. All 32 passage files
are byte-identical to the original preparation. Original/candidate hashes, neutral
labels, split order, bibliography, schema and quote/feedback rules stay fixed.

Caps: **31 baseline + 16 shared additional calls**, at most two extras per parent.
One **eight-hour wall admission deadline from the first substantive dispatch** spans
both stages and includes pauses/resumes; it never restarts. One admitted request may
finish up to 900 seconds beyond that boundary, then only local report/ZIP cleanup
(normally seconds, without a hard filesystem-time guarantee). No service restarts,
discretionary identical retries, hidden inference or compiler qualification occur.
Roughly **2–4 hours if similar to the 39-minute gate**, not a promised duration.
No work is added to fill the night. Speed optimisation remains deferred.

### 1. Run the full tests in the normal terminal

This leaves unrelated opt-in real compiler tests disabled. Stop on any unexpected
failure; the normal terminal permits mock loopback sockets denied in Codex's sandbox.

```bash
cd /home/mdi/projects/pdf-to-latex
env -u PDF2TEX_COMPILER_IMAGE .venv-control/bin/python -m unittest discover -s tests -v
```

Offline verification: all 11 new regressions passed. Full suite: 301 tests,
284 passed, 15 sandbox-denied mock socket setup errors, two opt-in compiler
skips, no assertion failures. No model or compiler execution was performed.

### 2. Read-only workload and regular-deployment checks

Confirm no OCR/converter or other review job is using the project/model. Check both
Sparks and leave unrelated work/downloads alone. These checks do not stop anything.
Memory/container status alone cannot prove that every workload is idle.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -c 'from pathlib import Path; from probe.saved_pages import converter_idle; print(converter_idle(Path.cwd()))'
ps -u "$(id -un)" -o pid,etime,args | rg 'probe|mineru|tensorfold|deepseek|python'
free -h
docker ps --format '{{.Names}}  {{.Status}}  {{.Image}}'
ssh -o BatchMode=yes -o ConnectTimeout=10 mdi@192.168.100.2 'ps -u mdi -o pid,etime,args'
ssh -o BatchMode=yes -o ConnectTimeout=10 mdi@192.168.100.2 'docker ps --format "{{.Names}}  {{.Status}}  {{.Image}}"'
ssh -o BatchMode=yes -o ConnectTimeout=10 mdi@192.168.100.2 free -h
```

Compare the running regular head container to the saved immutable deployment evidence,
then discover its exact model alias. Require `DeepSeek-V4.1-Flash-TF`. If already running
and idle, **leave it running**. No GLM, abliterated model or alternate deployment is
permitted. A mismatch is a blocker to investigate, not permission to bypass checks.
If a service change is genuinely needed, use the previously verified retained-pair
launcher instructions in the historical section below; do not interrupt another job.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python - <<'PY'
import json, subprocess
from pathlib import Path
from probe.common import read_json
expected = read_json(Path('runs/critic-followup-audit-20261024T170212Z-523425/runtime-support.json'))
live = json.loads(subprocess.check_output(['docker', 'inspect', 'marco-deepseek-flash17-r0']))[0]
assert live['Image'] == expected['image_id'], 'Different runtime image'
assert live['Config']['Cmd'] == expected['recorded_command'], 'Different serving command'
assert live['State']['Running'], 'Regular DeepSeek is not running'
print('Recorded regular DeepSeek image and command match; running.')
PY
curl --noproxy '*' --fail --show-error --max-time 10 http://127.0.0.1:8894/v1/models
```

### 3. Enter tmux, then obtain fresh TEXT-ONLY readiness

This starts or attaches the persistent terminal. Run the following readiness and
launch blocks **inside tmux**. Detach using Ctrl-B then D; reconnect with the same
command. A desktop disconnection does not end the tmux job.

```bash
cd /home/mdi/projects/pdf-to-latex
tmux new-session -A -s critic-overnight
```

This validates the new preview and makes the small text readiness request. Require
`Text: passed` and `vision: not_requested_text_only`. Copy the actual directory printed
by the command; no future readiness path is assumed. It must be at most one hour old
when launching or resuming. There is no second readiness/prompt between stages.

```bash
(
  set -euo pipefail
  cd /home/mdi/projects/pdf-to-latex
  overnight_preview=runs/text-critic-overnight-input-20261024T211031Z-de4d3d
  test -f "$overnight_preview/manifest.json"
  .venv-control/bin/python -m probe.recovery_trial ready --preview "$overnight_preview"
)
```

### 4. Launch the frozen two-stage run

Paste **ONLY the printed Readiness directory** at this prompt, then Return.
Do not paste another command block there. Blank/whitespace input and absent files are
rejected. The bound launcher also checks seals, settings, exact model identity and
freshness before substantive dispatch. It runs development, tests the declared
checkpoint, then admits reserved automatically only on a pass. No interaction is
needed between stages. `tee` keeps the terminal log, and pipefail preserves errors.

```bash
(
  set -euo pipefail
  cd /home/mdi/projects/pdf-to-latex
  overnight_preview=runs/text-critic-overnight-input-20261024T211031Z-de4d3d
  overnight_run=runs/text-critic-overnight-trial-20261024T211031Z-63fbda
  read -r -p 'Paste ONLY the actual fresh Readiness directory: ' overnight_ready
  [[ -n "${overnight_ready//[[:space:]]/}" ]] || { echo 'No readiness directory supplied' >&2; exit 2; }
  test -f "$overnight_ready/readiness.json"
  test -f "$overnight_run/binding.json"
  bash "$overnight_preview/operator-launch.sh" "$overnight_ready" 2>&1 | tee -a "$overnight_run/terminal.log"
)
```

### 5. Monitor, pause and resume

These commands only read live state/logs; do not invoke report/bundle commands while
the writer is active. `latest-bundle.json` still points to the preparation ZIP until
the writer stops. The checkpoint counts in status belong to the 12-unit development
stage, not the earlier eight-unit gate.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m probe.recovery_trial status --run runs/text-critic-overnight-trial-20261024T211031Z-63fbda
tail -n 20 runs/text-critic-overnight-trial-20261024T211031Z-63fbda/terminal.log
```

To request a controlled pause, create the existing pause flag. The current request
may finish (up to its 900-second timeout); the controller then stops admitting calls
and creates a partial inspection ZIP. Do not kill the server or delete attempts.
The eight-hour deadline continues during the pause.

```bash
cd /home/mdi/projects/pdf-to-latex
touch runs/text-critic-overnight-trial-20261024T211031Z-63fbda/PAUSE
```

After status shows a stopped writer, obtain fresh readiness using step 3. Then use
this block **inside tmux** to resume. It refuses an active writer and removes only
its pause flag. Completed calls are not replayed; global/per-parent budgets and the
original deadline remain consumed. A failed checkpoint, identity/integrity failure
or exhausted deadline is not an instruction to relaunch a new experiment.

```bash
(
  set -euo pipefail
  cd /home/mdi/projects/pdf-to-latex
  overnight_preview=runs/text-critic-overnight-input-20261024T211031Z-de4d3d
  overnight_run=runs/text-critic-overnight-trial-20261024T211031Z-63fbda
  .venv-control/bin/python - <<'PY'
from pathlib import Path
from probe.common import read_json
s = read_json(Path('runs/text-critic-overnight-trial-20261024T211031Z-63fbda/state.json'))
assert s['active_since_epoch'] is None and s['status'].startswith('paused'), 'Require a controlled paused writer'
PY
  read -r -p 'Paste ONLY the actual fresh Readiness directory: ' overnight_ready
  [[ -n "${overnight_ready//[[:space:]]/}" ]] || { echo 'No readiness directory supplied' >&2; exit 2; }
  test -f "$overnight_ready/readiness.json"
  rm -f "$overnight_run/PAUSE"
  bash "$overnight_preview/operator-launch.sh" "$overnight_ready" --resume 2>&1 | tee -a "$overnight_run/terminal.log"
)
```

### 6. Inspect the automatically saved report and ZIP after stopping

Normal completion, admission deadline, failed checkpoint and controlled pause all
produce a new compact ZIP after execution stops. This read-only block confirms that
state and prints the **actual latest path and size**, including any partial result.
Open `overnight/report.html` locally, or extract the ZIP and open
`overnight/development.html` and `overnight/reserved.html`. The ZIP also includes
Markdown reports, failures CSV, exact selected inputs/requests, parsed answers,
failed final content, usage, lineage and unresolved slots; raw reasoning stays in
the run. No full book PDFs, weights, environments or credentials are bundled.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python - <<'PY'
from pathlib import Path
from probe.common import read_json
run = Path('runs/text-critic-overnight-trial-20261024T211031Z-63fbda')
s = read_json(run/'state.json')
assert s['active_since_epoch'] is None and s['status'] != 'running', 'Writer still active'
print('Status:', s['status'])
print('Report:', (run/'overnight/report.html').resolve())
print('Inspection ZIP:', read_json(run/'latest-bundle.json'))
PY
```

If a later bundle is needed, this existing new-controller command takes the project
writer lock, refuses an active writer and creates another timestamped ZIP. It never
overwrites an earlier bundle or requests inference.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m probe.critic_overnight bundle --run runs/text-critic-overnight-trial-20261024T211031Z-63fbda
```

## Historical preparation: eight-unit follow-up (now completed and passed)

The first critic gate has finished and failed. Do **not** resume
`runs/text-critic-trial-20261024T140153Z-32efd8` under the changed code. Its ten
calls, counters, raw attempts and historical reports remain unchanged. The new
follow-up repeats only the same eight observed gate units, with unchanged
baseline/candidate passages, neutral labels and ordering. They are diagnostic
cases, not unseen gold. The other 31 pending units and unavailable reserved g16-Y
are excluded; the original reserved selection is preserved and unobserved.

Actual new artifacts:

- Diagnosis, revised old report, provisional findings, settings and test evidence:
  `runs/critic-followup-audit-20261024T170212Z-523425/report.html`.
- Derived historical report (does not rewrite the original):
  `runs/critic-followup-audit-20261024T170212Z-523425/derived-old-report/report.html`.
- New preview: `runs/text-critic-followup-input-20261024T171424Z-47ad07`.
- New run: `runs/text-critic-followup-trial-20261024T171424Z-8bb3c1`.
- Compact preparation ZIP:
  `results/critic-followup-preparation-20261024T171424Z-47ad07-inspection.zip`.

Observed original gate: 4 final valid, 4 first-attempt valid and 3 complete claimed
coverage out of eight, after 10 calls and 2361.806 seconds. g02-X failed exact
quotation/location validation three times. g03-X exhausted 16384 tokens with
partial final JSON; g04-X/Y exhausted the same allowance with no final content.
Separate reasoning-token counts were not reported. The original feedback totals
missed 9535 tokens / 175.783 request seconds because those metrics were nested
inside failed outcomes. Corrected accounting is a new derived report, not a
historical rewrite. Request latency and full admission/wall time remain distinct.

Changes are narrow: generic verbatim quotation instructions and exact source-span
feedback; permission to repair only invalid citations while preserving findings,
valid quotes and uncertainty; provisional diagnostics for individually validated
findings in complete rejected responses; clearer relevance/context instructions;
and accounting for both successful and failed outcomes. Truncated JSON is never
salvaged, and provisional findings never count toward gate success. All findings
remain UNACCEPTED and citation validity is not mathematical correctness.

The saved regular deployment command and matching immutable image establish a
32768 response allowance. Embedded runtime messages say max_tokens counts
reasoning and final content together. Medium appears in binary validation choices,
but its effective mapping/honouring remains unknown; no live trial here establishes
it. Saved reasoning is substantive but repeatedly reconsiders findings/context and
presentation; no fixed identical-output loop was established. The new allowance
is a **response-completion experiment**, not a speed optimisation or accuracy claim.

New settings: requested **medium**, **32768 tokens**, **900 seconds**, serial,
unchanged sampling defaults, no server-enforced response format. Lower-effort
recovery stays disabled. Only the critic client purpose gains the larger limits;
page review and preflight limits/behaviour stay unchanged. Bounds: eight initial
requests, at most eight total recoveries, at most two extras per original unit,
four cumulative admission hours. A request admitted before the deadline can
finish up to 900 seconds after it. Existing gate thresholds remain **6 first
valid / 8 final valid / 6 complete claimed coverage**. No remaining group is
admitted automatically, even if the gate passes. Speed work remains deferred.

### 1. Full tests in the normal terminal

If needed, start tmux first (`tmux new-session -s critic-followup`), then execute
these blocks inside it. Detach with Ctrl-B then D; reconnect with
`tmux attach -t critic-followup`. The tests unset the compiler opt-in variable
only for this command, because compiler qualification is outside this task.
Mock socket tests can run in the normal terminal. Stop and inspect any failure.

```bash
cd /home/mdi/projects/pdf-to-latex
env -u PDF2TEX_COMPILER_IMAGE .venv-control/bin/python -m unittest discover -s tests -v
```

Offline results: 290 tests, 273 passed, 15 sandbox socket-setup PermissionErrors,
two opt-in real compiler skips, no assertion failures. All 13 new focused checks
passed. No real compiler, OCR, model or service operation was performed here.

### 2. Check workloads and the intended regular DeepSeek deployment

These are read-only checks. Confirm OCR/project workers have exited and no other
inference job is active. Inspect both nodes and leave unrelated jobs/downloads
alone. Container and memory checks alone do not establish that every job is idle.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -c 'from pathlib import Path; from probe.saved_pages import converter_idle; print(converter_idle(Path.cwd()))'
ps -u "$(id -un)" -o pid,etime,args | rg 'probe|mineru|tensorfold|deepseek|python'
free -h
docker ps --format '{{.Names}}  {{.Status}}  {{.Image}}'
ssh -o BatchMode=yes -o ConnectTimeout=10 mdi@192.168.100.2 'docker ps --format "{{.Names}}  {{.Status}}  {{.Image}}"'
ssh -o BatchMode=yes -o ConnectTimeout=10 mdi@192.168.100.2 free -h
```

Verify the local regular container against the recorded immutable image and exact
command. This checks deployment identity, not mathematical accuracy or available
capacity under every workload. If it succeeds and the service is idle, **skip all
service switching** and proceed to fresh project readiness.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python - <<'PY'
import json, subprocess
from pathlib import Path
from probe.common import read_json
expected = read_json(Path('runs/critic-followup-audit-20261024T170212Z-523425/runtime-support.json'))
live = json.loads(subprocess.check_output(['docker', 'inspect', 'marco-deepseek-flash17-r0']))[0]
assert live['Image'] == expected['image_id'], 'Different runtime image'
assert live['Config']['Cmd'] == expected['recorded_command'], 'Different serving command'
assert live['State']['Running'], 'Regular DeepSeek is not running'
print('Recorded regular DeepSeek image and command match; running.')
PY
curl --noproxy '*' --fail --show-error --max-time 10 http://127.0.0.1:8894/v1/models
```

The endpoint must identify exactly `DeepSeek-V4.1-Flash-TF`. Do not substitute GLM,
an abliterated DeepSeek model or another deployment. **Only if switching is needed**,
Qwen is the competing service and its work is finished, its verified wrapper is:

```bash
bash /home/mdi/local-llm/flash-next-tensorfold/spark-tensorfold.sh stop
```

**Skip the following command if regular DeepSeek is already running.** Once other
heavy work is stopped through its documented controls, the verified retained-pair
launcher checks ownership/settings/memory, starts regular DeepSeek and performs
its deployment smoke controls. No first-launch/image rebuild is needed.

```bash
python3 -B /home/mdi/Downloads/deepseek-retry-20261022.py
```

Then repeat the read-only deployment check above. A failure means inspect the
actual deployment; do not bypass its checks or change settings to force this trial.

### 3. Create fresh TEXT-ONLY readiness

This checks the prepared code/evidence and makes the existing small text readiness
call, with exact discovery/response identity checks. Require `Text: passed` and
`vision: not_requested_text_only`. Record the directory printed by this command;
do not paste an old vision preflight or the failed run directory.

```bash
(
  set -euo pipefail
  cd /home/mdi/projects/pdf-to-latex
  critic_preview=runs/text-critic-followup-input-20261024T171424Z-47ad07
  test -f "$critic_preview/manifest.json"
  .venv-control/bin/python -m probe.recovery_trial ready --preview "$critic_preview"
)
```

### 4. Launch ONLY the new eight-unit follow-up

This block defines paths afresh. At its prompt, paste **only the actual Readiness
directory just printed above**, then press Return. Empty/whitespace values and
missing files are rejected before launch. The explicit Python check also verifies
its seal, exact endpoint/profile and one-hour freshness. No future path is assumed.
The final command launches the bounded gate and records a terminal log in the new
run. It does not resume the failed historical gate or launch other groups.

```bash
(
  set -euo pipefail
  cd /home/mdi/projects/pdf-to-latex
  critic_preview=runs/text-critic-followup-input-20261024T171424Z-47ad07
  critic_run=runs/text-critic-followup-trial-20261024T171424Z-8bb3c1
  test -f "$critic_preview/manifest.json"
  test -f "$critic_run/binding.json"
  read -r -p 'Paste ONLY the actual new text Readiness directory: ' critic_ready
  if [[ -z "${critic_ready//[[:space:]]/}" ]]; then
    echo 'No Readiness directory supplied; nothing launched.' >&2
    exit 2
  fi
  test -f "$critic_ready/readiness.json"
  .venv-control/bin/python - "$critic_preview" "$critic_ready" <<'PY'
import sys
from pathlib import Path
from probe.experiment import verify_preview, check_readiness
meta, _ = verify_preview(Path(sys.argv[1]))
check_readiness(Path(sys.argv[2]).resolve(), meta['config'], False)
print('Fresh exact-profile text readiness verified')
PY
  .venv-control/bin/python -m probe.recovery_trial launch \
    --run "$critic_run" --readiness "$critic_ready" --stage gate \
    2>&1 | tee "$critic_run/operator-gate-$(date -u +%Y%m%dT%H%M%SZ).log"
)
```

### 5. Status during execution; report/ZIP only after it stops

In another normal terminal, this reads status without taking the live writer lock:

```bash
cd /home/mdi/projects/pdf-to-latex
critic_run=runs/text-critic-followup-trial-20261024T171424Z-8bb3c1
test -f "$critic_run/state.json"
.venv-control/bin/python -m probe.recovery_trial status --run "$critic_run"
```

After the job stops, this regenerates **the new run's** report and creates a new
compact inspection ZIP. The printed path and `latest-bundle.json` identify the
actual resulting archive. The ZIP includes Markdown, JSON ledgers and failures CSV;
raw reasoning and all outgoing message records remain in the local run directory.

```bash
(
  set -euo pipefail
  cd /home/mdi/projects/pdf-to-latex
  critic_run=runs/text-critic-followup-trial-20261024T171424Z-8bb3c1
  .venv-control/bin/python - "$critic_run" <<'PY'
import sys
from pathlib import Path
from probe.common import read_json
state = read_json(Path(sys.argv[1]) / 'state.json')
assert state['status'] != 'running' and state['active_since_epoch'] is None, 'Wait for the writer to stop'
PY
  .venv-control/bin/python -m probe.recovery_trial bundle --run "$critic_run"
  xdg-open "$critic_run/report.html"
  .venv-control/bin/python -m json.tool "$critic_run/latest-bundle.json"
)
```

Stop for inspection after this follow-up. For an orderly pause, create `PAUSE` in
this new run; admission stops after the current request. A normal resume uses the
same new run, fresh readiness and `--stage gate --resume`, retaining consumed calls
and time. It does not reset the per-unit/shared allowances. No later development
or reserved stage belongs to this bounded preview. Do not regenerate candidates,
rerun Qwen or change source passages for this experiment.


## Historical preparation: assessed candidate and first critic gate (now failed)

The Qwen continuation `runs/recovery-continuation-trial-20261024T112538Z-8d13d3`
is complete: 267 validated final region responses across 16 pages, 267 baseline
calls and eight recoveries. Its 31 final proposals remain UNACCEPTED. Codex
inspected all 31 complete replacements against saved structured OCR and source
images: **27 suitable for experimental application; four deferred**. This is
Codex assessment, not human verification. Completion and compilation establish
neither preservation nor mathematical correctness.

The four deferrals are v105 (a formula would replace/delete most of a paragraph),
v138 (explicitly uncertain font weight), v250 (unnecessary spacing repair based
on an incorrect claim about `\mathrm{a n d}`), and v210 (valid original TeX
misdescribed as malformed). Their original drafts are unchanged. v093 is recorded
as an explicitly permitted editorial repair of a parenthesis actually printed in
the book; Qwen's OCR-error explanation was wrong. v001 retains a minor missing
comma; no automatic polishing was done. The audit preserves all diagnoses and
original proposal metadata separately from the assessment.

Actual new artifacts:

- Audit, dispositions, complete before/after evidence and source crops:
  `runs/proposal-audit-20261024T134532Z-6a438a/report.html`
  (`report.md`, `dispositions.csv`, `dispositions.json`, `findings.json`).
- Experimental candidate:
  `runs/evaluation-candidate-20261024T140145Z-6343d9`
  (`candidate.tex`, `report.html`, `inventory.json`, `changes.json`, `provenance.json`).
- Refreshed frozen recipe: `runs/text-critic-recipe-20261024T140149Z-e7a9d7`.
  Its lineage points to `runs/text-critic-recipe-20261023T192309Z-6796b6`;
  all 40 baseline input/request files are byte-identical. Selection, 10/10 split,
  prompts, settings, ordering and budgets are unchanged.
- Critic preview: `runs/text-critic-input-20261024T140150Z-062adf`.
- Critic run: `runs/text-critic-trial-20261024T140153Z-32efd8`; zero live calls.
- Combined inspection ZIP:
  `results/reviewed-candidate-critic-20261024T140145Z-6343d9-inspection.zip`.

Candidate assembly now requires a matching exact-version assessment before
applying a proposal experimentally. An omitted assessment applies nothing.
Incomplete, deferred, uncertain, conflicting and partial dependent changes are
blocked. Old review code bindings remain recorded; new candidate assembly has a
separate code binding. No old seal was patched. Neither length, valid JSON nor
compilation is a semantic-preservation test.

Three blocks remain nonportable: `klebaner-ch4-7-p0031:b4`, `p0081:b3` and
`p0081:b19` (same source prefix). Their complete raw OCR and images remain in the
candidate inventory/report; TeX has explicit unresolved placeholders. This is not
a complete editable transcription. The last block makes **g16-Y unavailable**;
g16-X retains the frozen raw-OCR baseline and cannot establish a complete paired
comparison alone. Gate group g04's baseline also retains its original complete
structured OCR fallback; its candidate is repaired. No frozen baseline was
silently replaced with cleaned text. The initial four pairs are all available.

Historical compilation: 29 proposed replacements passed. For v005 the original
OCR failed while the proposal passed. v034/v036 headings were **not attempted**
because the original OCR was unsupported; they did not fail compilation.
The new candidate's Docker invocation was denied access to `/var/run/docker.sock`
before TeX started. Its adapter records `build_failure_unresolved`, with
`compilation_claim: false`; this is an infrastructure limitation, not evidence of
a TeX syntax error. No new successful compilation is claimed.

### 1. Normal-terminal tests and optional isolated compilation

If not already inside tmux, create the persistent terminal, then run the remaining
blocks inside it. Detach with **Ctrl-B, then D**; reconnect with
`tmux attach -t klebaner-text-critic`.

```bash
tmux new-session -s klebaner-text-critic
```

Set the working directory and load the already qualified immutable compiler ID
from the completed run, avoiding manual hash transcription. This runs the full
suite, including mock sockets and both opt-in real compiler checks. Stop and
inspect any failure before launching the experiment.

```bash
cd /home/mdi/projects/pdf-to-latex
set -o pipefail
export PDF2TEX_COMPILER_IMAGE="$(.venv-control/bin/python -c 'from pathlib import Path; from probe.common import read_json; print(read_json(Path("runs/recovery-continuation-trial-20261024T112538Z-8d13d3/state.json"))["compiler_image"])')"
.venv-control/bin/python -m unittest discover -s tests -v
```

The candidate is already assembled. This optional offline check compiles its exact
sealed TeX and separately tests each proposed heading. It creates a **new sidecar**,
never changes the candidate/critic hashes, and does not compare headings with the
unsupported originals. It uses the existing network-isolated, non-root adapter,
without pulling or rebuilding an image. Even a successful build leaves the three
explicit unresolved placeholders and does not establish fidelity.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python - <<'PY'
from pathlib import Path
import json
from probe import experiment as ex, tex_compile
from probe.common import read_json, atomic_json, sha
from probe.portable_export import portable_document
root = Path.cwd()
candidate = root / 'runs/evaluation-candidate-20261024T140145Z-6343d9'
ex.verify_seal(candidate)
ex.InputGuard(read_json(candidate / 'provenance.json')['bindings'])
image = read_json(root / 'runs/recovery-continuation-trial-20261024T112538Z-8d13d3/state.json')['compiler_image']
out = ex.new_path(root, 'candidate-compilation')
out.mkdir()
results = {'candidate': tex_compile.compile_document(
    (candidate / 'candidate.tex').read_text(), out / 'candidate', image=image)}
for change in read_json(candidate / 'changes.json'):
    unit = change['id'].split(':')[0]
    if unit in ('v034', 'v036'):
        assert change['status'] == 'applied_experimental'
        results[unit] = tex_compile.compile_document(
            portable_document([change['latex']], set(change['packages'])),
            out / (unit + '-proposed-only'), image=image)
atomic_json(out / 'summary.json', {
    'candidate': str(candidate), 'candidate_manifest_sha256': sha(candidate / 'manifest.json'),
    'heading_basis': 'proposed-only; original compilation NOT attempted',
    'results': results})
ex.seal(out)
print('Compilation sidecar:', out)
print(json.dumps({key: value['status'] for key, value in results.items()}, indent=2))
PY
```

### 2. Inspect workloads, then arrange regular DeepSeek

These checks inspect visible project OCR workers, local model/job processes,
container ownership and memory on both nodes. Require no active OCR or inference
job before switching. They do not stop anything or establish that every remote
job is idle. Leave unrelated workloads and downloads alone.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -c 'from pathlib import Path; from probe.saved_pages import converter_idle; print(converter_idle(Path.cwd()))'
ps -u "$USER" -o pid,etime,args | rg 'probe|mineru|tensorfold|deepseek|python'
free -h
docker ps --format '{{.Names}}  {{.Status}}  {{.Image}}'
ssh -o BatchMode=yes -o ConnectTimeout=10 mdi@192.168.100.2 'docker ps --format "{{.Names}}  {{.Status}}  {{.Image}}"'
ssh -o BatchMode=yes -o ConnectTimeout=10 mdi@192.168.100.2 free -h
```

Only if the completed Qwen service is still running and idle, stop it using its
verified wrapper. **Skip this if Qwen is already stopped.** Do not stop another
model or an active job.

```bash
bash /home/mdi/local-llm/flash-next-tensorfold/spark-tensorfold.sh stop
```

**Skip this if regular DeepSeek is already running.** The existing successful
retry launcher checks its retained pair, settings and memory gates, then starts
regular `DeepSeek-V4.1-Flash-TF` and runs its deployment smoke controls. This
launcher was inspected read-only; it was not executed during preparation. Do not
substitute GLM or another/abliterated deployment. Smoke controls are not evidence
of mathematical accuracy.

```bash
python3 -B /home/mdi/Downloads/deepseek-retry-20261022.py
```

### 3. Fresh text readiness, then only the four-pair gate

Define actual paths in this shell. Model discovery must show the exact
`DeepSeek-V4.1-Flash-TF`. The project readiness command additionally checks the
actual response identity and requires `Text: passed` with
`vision: not_requested_text_only`. There are no image requests in this critic.
At the prompt, paste **only the newly printed Readiness directory**, not a command
or a prior run directory. No future readiness path is assumed. The final Python
check verifies its seal, exact profile and freshness (one hour maximum).

```bash
cd /home/mdi/projects/pdf-to-latex
set -o pipefail
critic_preview=runs/text-critic-input-20261024T140150Z-062adf
critic_run=runs/text-critic-trial-20261024T140153Z-32efd8
test -f "$critic_preview/manifest.json" && test -f "$critic_run/binding.json"
curl --noproxy '*' --fail --show-error --max-time 10 http://127.0.0.1:8894/v1/models
.venv-control/bin/python -m probe.recovery_trial ready --preview "$critic_preview"
read -r -p 'Paste ONLY the actual new text Readiness directory: ' critic_ready
.venv-control/bin/python - "$critic_preview" "$critic_ready" <<'PY'
import sys
from pathlib import Path
from probe.experiment import verify_preview, check_readiness
meta, _ = verify_preview(Path(sys.argv[1]))
check_readiness(Path(sys.argv[2]).resolve(), meta['config'], False)
print('Fresh exact-profile text readiness verified')
PY
```

After those checks pass, launch **only the initial gate**: four original/candidate
pairs (eight baseline requests), sequential medium reasoning, 16,384 output
tokens and 600 seconds per request, sampling defaults omitted. Inputs contain
exact neutral manuscript spans and schema, without images, Qwen explanations,
Codex diagnoses or expected corrections. Frozen experiment ceilings remain 40
baseline calls, 24 shared recoveries, two extra calls per request and four hours
cumulative admission; the gate does not automatically launch later groups.

```bash
.venv-control/bin/python -m probe.recovery_trial launch \
  --run "$critic_run" --readiness "$critic_ready" --stage gate \
  2>&1 | tee "$critic_run/operator-gate-$(date -u +%Y%m%dT%H%M%SZ).log"
```

### 4. Monitor, inspect and bundle; stop after the gate

In another normal terminal, define the run again before inspecting it. `status`
is read-only and can run during execution. Bundle only once the writer has
stopped; it regenerates reports and creates a new compact ZIP, including Markdown,
JSON ledgers and failures CSV. `latest-bundle.json` records its actual path/hash.

```bash
cd /home/mdi/projects/pdf-to-latex
critic_run=runs/text-critic-trial-20261024T140153Z-32efd8
.venv-control/bin/python -m probe.recovery_trial status --run "$critic_run"
```

After the gate stops:

```bash
cd /home/mdi/projects/pdf-to-latex
critic_run=runs/text-critic-trial-20261024T140153Z-32efd8
.venv-control/bin/python -m probe.recovery_trial bundle --run "$critic_run"
xdg-open "$critic_run/report.html"
.venv-control/bin/python -m json.tool "$critic_run/latest-bundle.json"
```

For an orderly pause, `touch "$critic_run/PAUSE"` stops new admissions after the
current request. After it stops, remove only that marker with
`rm "$critic_run/PAUSE"`, repeat section 3's path/readiness block and launch the
same gate with `--resume`. Earlier successful calls are not repeated. Do not
manually edit state, bindings or seals. Inspect the gate before authorizing later
`--stage development --resume`, and reserved only after development inspection;
these are separate later stages, not part of this first launch. Reserved is a
frozen comparison split, not unseen gold. g16-Y remains unavailable.


## Historical preparation: remaining 243 Qwen regions (now completed)

The operator completed the v005 repair in
`runs/recovery-repair-trial-20261024T103428Z-1a2018`. Its one new `export_feedback`
call (`0025`) returned an exportable replacement; its proposed TeX compiled.
The original OCR still failed compilation (`syntax_failure`), so the pair is
`preexisting_or_context_failure_unresolved`, not `both_compiled`. All proposals
remain UNACCEPTED; source fidelity is not established by either compilation or
technical response success. One inherited uncertain proposal remains deferred.

The explicit `continuation-prepare --run ...` addition creates a new linked
artifact from a completed repair. It preserves historical code identities/seals,
copies all 25 call directories unchanged and binds current code separately.
Only the 243 pending non-gate units can be dispatched, in their original order.
The original gate and repair cannot be replayed. Do not prepare another fork;
resume the new run when needed. The old repair-only stopping instruction below
is superseded only for this new continuation, not for the old runs.

Actual offline artifacts:

- Preview: `runs/recovery-continuation-input-20261024T112538Z-e1a1ef`.
- Run: `runs/recovery-continuation-trial-20261024T112538Z-8d13d3`.
- Report: `report.html` in that run; exact inputs/requests remain in the preview.
- Initial ZIP:
  `results/recovery-continuation-trial-20261024T112538Z-8d13d3-inspection-20261024T112540Z-9330de.zip`.
- Parent/call/code provenance: `continuation/provenance.json` and
  `continuation/inherited-state.json` inside the preview.
- Pointer: `results/recovery-continuation-current.json`.
- Offline validation: `runs/continuation-checks-20261024T112017Z-19e3b8/validation.json`.

All 267 baseline inputs/images, ordering, gate flags and settings match both
prior previews byte-for-byte, including the 243 pending units. The immutable
dispatch scope excludes every inherited completed region. Accounting starts
with 24 baseline calls, one recovery call and 839.6103107519448 seconds consumed.
Original ceilings remain 267 baseline, 80 shared recovery, two additional calls
per region and 21,600 cumulative seconds. There are 243 baseline calls, 79
recovery calls and 20,760.389689248055 admission seconds left. Resuming cannot
reset consumed calls/time or change the compiler image, settings or evidence.

Settings remain Qwen `flash-next-tensorfold` at `http://127.0.0.1:8890/v1`, medium
reasoning, 16,384 output tokens, 600-second timeout, serial requests, omitted
sampling settings and omitted `response_format`. Unsupported server-enforced
JSON remains recorded; strict local JSON/schema, exact model identity, coverage,
export and eligible isolated compiler checks remain active. Exhausted or
unsupported proposals stay unresolved; uncertain proposals remain deferred.
The existing two-connection-failure pause and identity/integrity stops remain.

### Tests and fresh Qwen readiness

Use the existing tmux terminal. If starting from a separate ordinary terminal,
`tmux new-session -A -s pdf2tex-qwen-continuation` creates or reattaches a persistent
session using the installed tool. Run the following blocks in that same Bash
session. Only copy the code blocks. Codex did not run these live commands.

Set actual paths and read the qualified compiler ID from the bound state, avoiding
manual hash transcription. Run the full suite with real compiler checks enabled.
Offline results: 267 tests, 250 passed, 15 sandbox-denied mock socket errors,
two opt-in compiler skips; all seven new continuation tests passed.

```bash
cd /home/mdi/projects/pdf-to-latex
set -o pipefail
continuation_preview=runs/recovery-continuation-input-20261024T112538Z-e1a1ef
continuation_run=runs/recovery-continuation-trial-20261024T112538Z-8d13d3
tex_image="$(.venv-control/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1]))["compiler_image"])' "$continuation_run/state.json")"
compiler_args=(--compiler-image "$tex_image")
PDF2TEX_COMPILER_IMAGE="$tex_image" .venv-control/bin/python -m unittest discover -s tests -v
```

After tests pass, check discovery and obtain fresh readiness. The readiness command
also checks project OCR exit and records live text/vision controls. Require exact
`flash-next-tensorfold`, **Text: passed** and **vision: qualified**. Paste the
actual newly printed Readiness directory; neither exit status alone nor a model
listing establishes vision qualification. Readiness must be less than one hour old.

```bash
curl --noproxy '*' --fail --show-error --max-time 10 http://127.0.0.1:8890/v1/models
.venv-control/bin/python -m probe.recovery_trial ready --preview "$continuation_preview"
read -r -p 'Paste the actual new Readiness directory: ' continuation_ready
```

### Launch and monitor only the remaining work

`--stage continue` on this prepared run dispatches only its 243 pending units
and their bounded recovery requests. Compilation is mandatory with the inherited
qualified image. Progress and the output directory are printed after each call;
the log stays in the new run. Detach from tmux with Ctrl-b then d; this leaves the
job running. Do not close the shell or edit code/evidence during execution.

```bash
.venv-control/bin/python -m probe.recovery_trial launch \
  --run "$continuation_run" --readiness "$continuation_ready" --stage continue \
  "${compiler_args[@]}" \
  2>&1 | tee "$continuation_run/operator-continue-$(date -u +%Y%m%dT%H%M%SZ).log"
```

From a second terminal, this is read-only status monitoring. The full path avoids
depending on variables from the launching shell:

```bash
cd /home/mdi/projects/pdf-to-latex
watch -n 30 .venv-control/bin/python -m probe.recovery_trial status \
  --run runs/recovery-continuation-trial-20261024T112538Z-8d13d3
```

Ctrl-c here exits only `watch`. It does not interrupt the writer in tmux.

### Pause and resume

To request an orderly pause, create the control file from a second terminal.
The current bounded request/validation finishes; no new request is admitted.
Wait for the launching shell to return and status to report paused:

```bash
touch /home/mdi/projects/pdf-to-latex/runs/recovery-continuation-trial-20261024T112538Z-8d13d3/PAUSE
```

Back in the original Bash/tmux session, remove only that pause marker, obtain
fresh readiness and explicitly resume. This preserves all successful, failed
and interrupted reservations and cumulative budgets. Do not use this to restart
terminal integrity/identity stops or an exhausted/completed run:

```bash
rm -f "$continuation_run/PAUSE"
.venv-control/bin/python -m probe.recovery_trial ready --preview "$continuation_preview"
read -r -p 'Paste the actual new Readiness directory: ' continuation_ready
.venv-control/bin/python -m probe.recovery_trial launch \
  --run "$continuation_run" --readiness "$continuation_ready" --stage continue \
  --resume "${compiler_args[@]}" \
  2>&1 | tee "$continuation_run/operator-resume-$(date -u +%Y%m%dT%H%M%SZ).log"
```

### Inspect and bundle partial or final results

After the writer has paused or finished, generate the current inspection bundle.
Bundling while the writer is active is blocked by the shared writer lock. The
HTML/Markdown report, failures CSV, ledger, images and continuation provenance
distinguish inherited and new calls, valid responses, exportability, original
and proposed compilation, uncertainty and unresolved proposals. The last command
prints the actual generated ZIP path; no future filename is assumed.

```bash
.venv-control/bin/python -m probe.recovery_trial status --run "$continuation_run"
.venv-control/bin/python -m probe.recovery_trial bundle --run "$continuation_run"
xdg-open "$continuation_run/report.html"
.venv-control/bin/python -m json.tool "$continuation_run/latest-bundle.json"
```

Inspect before candidate assembly or critic preparation. Those later phases
are not launched by this continuation. No proposal is automatically accepted.

## Historical v005-only repair instructions (completed 24 October)

The following records the earlier repair handover. Use the continuation commands
above for current work; do not relaunch the completed gate or repair directories.

The operator completed the original 24-region gate in
`runs/recovery-vision-trial-20261023T192309Z-cdec02`: 24 valid JSON/coverage
responses, eight proposals, seven original/proposed pairs `both_compiled`, and
one proposal rejected before compilation. No recovery calls ran; 243 baseline
regions remain pending. These are technical results, not a fidelity assessment.

The remaining proposal is v005, `klebaner-ch4-7-p0065:b14`, original PDF 170.
It declares bare mathematics as `latex_fragment`. The conservative exporter
correctly reports **Raw TeX control or mathematics outside math mode**. Previously
this was only an annotation on a completed response, and the compiler skipped
it; neither returned a recoverable failure. Export feedback now uses the same
shared allowance as JSON and compiler feedback. It retains the exact failed
answer, field diagnostics, permitted fragment contracts and original images/OCR
context, asking for representation repair without changing the mathematics.
Validation and final acceptance requirements have not been relaxed.

Actual offline preparation (do not prepare another fork):

- Preview: `runs/recovery-repair-input-20261024T103428Z-cf096e`.
- Run/report: `runs/recovery-repair-trial-20261024T103428Z-1a2018/report.html`.
- Exact first feedback: `repair/request.json` inside the preview; `repair/seed.json`
  records the separate reassessment and `repair/provenance.json` records lineage.
- Initial inspection ZIP:
  `results/recovery-repair-trial-20261024T103428Z-1a2018-inspection-20261024T103430Z-024f2c.zip`.
- Verification: `runs/export-recovery-checks-20261024T101818Z-f56144/validation.json`.
- Current pointer: `results/export-repair-current.json`.

The new derivative carries all 24 sealed calls, their historical outcomes and
817.8629703969928 seconds of admission time. It permits only v005 repair, with
two additional calls remaining within the original 80-call shared recovery limit
and six-hour cumulative admission budget. All 267 baseline request bodies,
sources, ordering and settings are unchanged; the other 243 are inert. The
original code bindings/seals are preserved, and current code is bound explicitly
in the derivative. Do not resume the old run with changed code. This derivative
refuses `--stage continue`; broader continuation and critic refresh require a
separate explicit preparation after inspecting this repair.

Every repair passes model identity, JSON/schema, selected-block coverage, export
checks and, when eligible, isolated compilation. A persistent original-answer
anchor prevents a later JSON retry from dropping proposals. Only representation
fields of the diagnosed proposal may change; mathematical equivalence still
requires source/human review. Exhausted or deferred proposals remain unresolved
and UNACCEPTED. Infrastructure/configuration failures do not request model repair.

The original v005 OCR equation also has unbalanced braces. For compiler diagnosis,
its exact safe equation body can now be staged with recorded display wrappers;
this does not make it exportable or repair its content. A repaired replacement
may compile while the original fails. Reports separate response validity,
exportability, each build result and unresolved/deferred proposals. An inherited
gate pass or `repair_completed` is not proof of compilation or mathematical fidelity.

### Operator commands: tests, fresh readiness, one repair, inspection

Run these blocks in the same normal Bash terminal (inside the existing tmux
session if desired). No live or real compiler execution occurred during this
offline preparation. Full-suite sandbox results were 243 passed, 15 denied mock
socket tests and two opt-in real compiler skips; all 17 new regressions passed.

Run the full suite, including both real compiler checks against the already
qualified image. No image rebuild or installation is needed:

24 October handover correction: the chat command accidentally omitted `228`
from the image ID, producing 61 hex characters and two real-test setup errors
before Docker execution. The saved run and the ID documented here were correct.
Read the ID from the saved run to avoid retyping it. If `compiler_args` was
already set using the shortened value, recreate that array after this block.
Copy only commands inside code blocks; explanatory prose is not shell input.

```bash
cd /home/mdi/projects/pdf-to-latex
set -o pipefail
tex_image="$(.venv-control/bin/python -c 'import json; print(json.load(open("runs/recovery-repair-trial-20261024T103428Z-1a2018/state.json"))["compiler_image"])')"
PDF2TEX_COMPILER_IMAGE="$tex_image" .venv-control/bin/python -m unittest discover -s tests -v
```

Set the actual preparation paths and explicit compiler arguments, check OCR is
idle, inspect model discovery, and obtain new readiness for this exact preview:

```bash
repair_preview=runs/recovery-repair-input-20261024T103428Z-cf096e
repair_run=runs/recovery-repair-trial-20261024T103428Z-1a2018
compiler_args=(--compiler-image "$tex_image")
.venv-control/bin/python -c 'from pathlib import Path; from probe.saved_pages import converter_idle; print(converter_idle(Path.cwd()))'
curl --noproxy '*' --fail --show-error --max-time 10 http://127.0.0.1:8890/v1/models
.venv-control/bin/python -m probe.recovery_trial ready --preview "$repair_preview"
read -r -p 'Paste the actual fresh Readiness directory: ' repair_ready
```

Require OCR idle, exact model `flash-next-tensorfold`, **Text: passed** and
**vision: qualified**. Readiness performs live controls and must be less than one
hour old at launch. Paste its actual printed Readiness directory; no future path
is assumed. Unsupported server-enforced JSON remains recorded/allowed, with
strict local validation. If the endpoint is absent or serves another alias,
stop here and consult the existing model-phase instructions below; these commands
do not start or stop a service.

Launch only the saved v005 repair. `--stage gate` on this bound derivative cannot
replay the gate or dispatch pending baselines. The compiler argument is mandatory
and must match the inherited qualified image. The timestamped log records progress:

```bash
.venv-control/bin/python -m probe.recovery_trial launch \
  --run "$repair_run" --readiness "$repair_ready" --stage gate \
  "${compiler_args[@]}" \
  2>&1 | tee "$repair_run/operator-repair-$(date -u +%Y%m%dT%H%M%SZ).log"
```

If normally paused/interrupted, obtain fresh readiness and use this same launch
command with `--resume`; consumed calls and elapsed admission time remain charged.
Do not create a second preparation to reset attempts. Terminal `repair_completed`
or `repair_unresolved` is not resumable. Status is read-only and can be inspected
from a second terminal using the actual run path.

After the writer returns, inspect the report and create the current compact ZIP.
The last command displays its actual path; bundles contain HTML/Markdown reports,
failure CSV, ledger, source images and repair provenance. All proposals remain
UNACCEPTED. Stop after bundling; do not launch the other 243 regions:

```bash
.venv-control/bin/python -m probe.recovery_trial status --run "$repair_run"
xdg-open "$repair_run/report.html"
.venv-control/bin/python -m probe.recovery_trial bundle --run "$repair_run"
.venv-control/bin/python -m json.tool "$repair_run/latest-bundle.json"
```

## Historical 23 October preparation and later-phase reference

The sections below preserve the original gate preparation and later-stage design.
The original gate has now completed. Its older code-bound paths are historical;
do not launch them or continue the 243 pending regions under this handover.

This is the new opt-in `recovery-critic-v1` protocol. Historical Qwen Arm A/B and
DeepSeek trials, their failures and their proposals remain unchanged. It is not
an unchanged Arm A comparison. Refreshed offline after the compiler-path fix on
23 October. The operator qualified the existing compiler image: the saved real
check reports `both_compiled`, and the operator reports all nine CompilerTests
passed, including both real tests and the relative include. See section 2.
This qualifies the adapter, not book transcription or mathematical fidelity.

**Historical operator scope: run only the 24-region Qwen gate, bundle it, and stop
for inspection.** Continuation, candidate assembly, critic and optional diagnostic
commands below are later reference, not part of this gate launch.

The user now permits clear, recorded local editorial repairs, including the
printed extra exponent parenthesis at PDF 166 / printed 151 / b9. Such a change
can enter an **experimental evaluation candidate**, with original/proposed bytes,
source location and transformation recorded. It is not final acceptance. Changed
signs, bounds, hypotheses or ambiguous regrouping stay in the material queue.
Model cosmetic labels cannot automatically hide changed mathematics. Uncertainty,
conflicts, unsupported fragments, partial dependent groups and deletions are
explicitly deferred. Existing final acceptance commands/rules are unchanged.

## Prepared artifacts and observed compatibility

These were the new preparation directories with valid code bindings on 23 October.
The earlier preview `runs/recovery-vision-input-20261023T083548Z-3399ba`, run
`runs/recovery-vision-trial-20261023T083553Z-6aa648` and critic recipe
`runs/text-critic-recipe-20261023T083553Z-60180a` remain unchanged; do not edit their
seals or launch them with the corrected compiler. No historical inference was
repeated. All 267 prepared request bodies, OCR/images, ordering, the 24-region
gate, settings/budgets and all twenty critic baseline requests are byte-identical.
Only `tex_compile.py` changed in the bound code map; new seals and run identities
reflect that change.

- Preparation report: `runs/recovery-preparation-20261023T192303Z-57ed87/report.html`.
- Markdown/CSV/JSON reports and bibliography: that same preparation directory.
- Core inspection ZIP: `results/recovery-preparation-20261023T192303Z-57ed87-inspection.zip`
  (7,772,556 bytes). The refreshed `-inspection-final.zip` additionally includes
  compiler qualification, refresh validation and the current gate handover.
- Refresh checks: `runs/recovery-preparation-20261023T192303Z-57ed87/refresh-validation.json`.
- Qualified image and gate arguments: `compiler-qualification.json` and
  `gate-launch.json` in the same preparation directory. The existing runner binds
  the image in run state at the first launch and requires it on subsequent resumes.
- Qwen preview: `runs/recovery-vision-input-20261023T192304Z-70e8b9`.
- Prepared Qwen run: `runs/recovery-vision-trial-20261023T192309Z-cdec02`.
- Frozen critic recipe: `runs/text-critic-recipe-20261023T192309Z-6796b6`.
- Optional schema diagnostic preview: `runs/schema-diagnostic-input-20261023T192310Z-708e9f`.
- Optional diagnostic run: `runs/schema-diagnostic-trial-20261023T192310Z-252ea1`.

`results/recovery-current.json` records these paths. One earlier offline
preparation stopped on an argument-type error in bibliography inventory. Its
unused artifacts are preserved and marked in
`results/recovery-preparation-aborted-20261023T083419Z.json`; do not launch them.

| New grammar classification | Qwen A (46 proposals) | DeepSeek (105 proposals) |
|---|---:|---:|
| Previously supported | 12 | 28 |
| Newly supported | 25 | 71 |
| Explicit equation display wrappers required | 7 | 6 |
| Genuinely malformed | 2 | 0 |
| Still unsupported / unresolved | 0 | 0 |

All 77 previous DeepSeek export blockers are covered by grammar expansion or
recorded wrappers. This is **not** compilation, source fidelity or acceptance.
Qwen 33 (tab/damaged textstyle and math outside delimiters) and 220 (unmatched
math delimiter) still fail. Full replacements, not just issue descriptions, were
checked. Identical proposals are grouped in display without deleting records;
different replacements for the same target conflict. Ambiguous line-break
hyphenation is left intact. The engine policy is pdfLaTeX with an explicit UTF-8/T1
Latin-prose repertoire; arbitrary Unicode math and unknown macros remain blocked.

## Bounds, stages and recovery

Qwen uses the same 267 regions/16 pages, original OCR, source images and crops.
The request instructions and typed response contract are versioned changes.
There is no Arm B/native-character augmentation and no expected answer in input.
Settings: `flash-next-tensorfold`, `http://127.0.0.1:8890/v1`, medium,
16,384 output tokens, 600 seconds, serial, inherited sampling, no response_format.
Maximum 267 baseline calls + 80 recovery calls, two recovery calls per original
region across all methods, six cumulative review hours. These are configurable
within the authorized ceiling at explicit preparation, not runtime permissions.

The first 24 distinct regions are a fixed technical gate: historical schema/JSON
failures, Qwen 161's confirmed all-reasoning exhaustion, syntax/export cases,
source-checked controls and additional unassessed equation controls. At least
12 first-attempt usable answers and 20 final usable answers with selected-block
coverage are required. The gate is part of the 267 and is never replayed.
Passing it does not establish mathematical accuracy or full-page omissions.

Only a single complete outer Markdown fence around one strict JSON object may
be removed mechanically. The original and transformed text remain recorded and
all validators still run. JSON/schema/coverage feedback supplies the complete
failed answer, exact field/path errors, original source context and the actual
schema, requesting a data instance. Readable substantive fields cannot silently
change/disappear. For an unparseable original, semantic preservation remains
unverified. Identical repeated failures are not blindly retried.

Lower effort is conditional on an empty final answer AND explicit token evidence
that reasoning consumed the output budget. Qwen's cached template supports medium
and low; its SHA-256 is
`c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041`.
Actual runtime benefit is untested. A truncated final JSON answer is a different
failure requiring a separately recorded coherent split/output-budget decision;
no continuation concatenation or automatic split is implemented. DeepSeek's
historical eleven schema failures do not justify globally reducing effort.

A real compiler-attributable introduced syntax error can receive bounded compiler
feedback within that same two-call ceiling. Original/proposed fixtures use the
same template/packages. Pre-existing OCR syntax, missing context/macros/packages,
encoding/engine problems, unresolved references, timeout and compiler unavailable
are distinct outcomes. Grammar support is not a substitute for the compiler.
No unrestricted macro acceptance or host-TeX fallback exists.

Durable reservations consume budget before dispatch. Unknown interrupted calls
remain consumed; completed calls are not repeated. Evidence, request, source,
code, model, settings, compiler identity and parent-chain changes refuse resume.
Two consecutive transport/timeouts pause; identity/integrity/configuration errors
stop. `PAUSE` stops admission after the current bounded request. A crash's unknown
downtime is conservatively charged; normal paused time is excluded. Readiness is
a separate explicit preflight step outside review-call/admission limits.

The text-only recipe has 20 coherent windows, ten development and ten reserved
on separate pages, rather than padding to 24 with unrelated fragments. It retains
complete mathematical strings, necessary local theorem/proof context and explicit
missing-context limitations. The first four pairs are the technical gate: all
eight final responses must validate, at least six on first attempt and six with
complete claimed coverage. Some external hypotheses/definitions may still be
missing; that is an explicit critic outcome, not a mathematical defect.
Previously inspected cases are diagnostic material, not unseen gold. Freeze and
retain these instructions before reserved results; do not tune on them.

Actual new candidate hashes bind at `critic-prepare` after the Qwen run. Each
original/candidate pair uses separate neutrally identified requests with the same
settings; visual rationales, audit verdicts and images are excluded. Candidate
assembly/review gaps make the affected version unavailable. Maximum 40 baseline
calls (within the requested 48 ceiling), 24 recovery calls, two per original
group/version, four cumulative hours. DeepSeek medium is the planned profile;
GLM high is an explicit later alternative, never fallback. Missing bibliography
does not block criticism. Exact quotations, occurrence, block IDs and draft hashes
are validated; a valid no-finding response is distinct from incomplete/context
missing/malformed/exhausted/transport/wrong-model outcomes.

## 1. Persistent terminal, full tests and read-only workload checks

All commands below are **operator commands**. Run them yourself on the head Spark.
No service, installation or inference commands were executed during development.
Start a dedicated tmux session, or attach to it if it already exists:

```bash
tmux new-session -s pdf2tex-recovery -c /home/mdi/projects/pdf-to-latex
```

Inside it, run the full suite. The development sandbox denied 15 mock loopback
socket binds; your normal terminal must establish that those tests pass.

```bash
cd /home/mdi/projects/pdf-to-latex
set -o pipefail
.venv-control/bin/python -m unittest discover -s tests -v \
  2>&1 | tee "results/recovery-tests-$(date -u +%Y%m%dT%H%M%SZ).log"
```

Check project OCR has exited, memory, and currently running model containers on
both nodes. These commands do not stop anything. The Python result must list no
owned converter PIDs. Also check any existing job terminals before switching a
model; discovery failure alone is not proof a service has exited.

```bash
.venv-control/bin/python -c 'from pathlib import Path; from probe.saved_pages import converter_idle; print(converter_idle(Path.cwd()))'
free -h
docker ps --format '{{.Names}}  {{.Status}}  {{.Image}}'
ssh -o BatchMode=yes -o ConnectTimeout=10 mdi@192.168.100.2 \
  "docker ps --format '{{.Names}}  {{.Status}}  {{.Image}}'; free -h"
```

## 2. Select the already-qualified compiler image

The operator check `runs/tex-compiler-check-20261023T185222Z-dab36a` used the image
below. Both documents were rejected by `openin_any=p` before input was read;
the recorded syntax failures were adapter/configuration failures. That run stays
unchanged. The fixed command works in read-only `/source`, reads `document.tex`
relatively and writes to `/work` with both `TEXMFOUTPUT` and `-output-directory`.
Input/output policy, non-root user, disabled shell escape, no network and existing
resource limits remain. Explicit policy denials cannot trigger model repair;
`texput.log` is retained alongside the ordinary logs when produced.

The subsequent operator check
`runs/tex-compiler-check-20261023T191527Z-7efa13` reports `both_compiled`.
Both return codes, PDFs, logs and recorded hashes were verified read-only during
this refresh. The operator also reports nine CompilerTests passed with the image
enabled, including the real original/proposed and relative-include tests; no
standalone terminal-test log was supplied. These are operator results, not mocked
compilation. No compiler was executed by Codex during this refresh.

Use the existing image and explicitly enable compiler feedback. This does not
rebuild, pull or requalify it. The first launch persists this exact image choice;
keep the same arguments on resume. Compiler feedback shares the existing two-
additional-call ceiling per region with all other recovery methods.

```bash
tex_image=sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45
docker image inspect --format '{{.Id}}' "$tex_image"
compiler_args=(--compiler-image "$tex_image")
```

No repeat compiler check is required for this gate preparation. The relative test
stages a valid document with `\input{sections/example.tex}`
under the read-only source tree, checks the include was read, verifies PDF/log/aux
outputs under `/work`, and verifies the source tree remained unchanged. The
single-document API still copies only its exact TeX; it does not follow arbitrary
caller paths or mount surrounding project files.

The generated Qwen 33/220/143 compiler fixture files were not compiled during
offline preparation; their `not_run`/unavailable records describe those fixtures,
not the separately qualified adapter. If this exact image is unavailable, stop
and investigate rather than silently omitting compiler feedback from this gate.

## 3. Arrange the Qwen phase using existing controls

Heavy models must run sequentially. If regular Qwen is already the intended
running service, skip its start and the DeepSeek stop commands. When the matching
DeepSeek pair is active and its work has finished, the existing pinned node helper
can stop only its owned containers. These exact retained containers carry the
original first-launch label, even though the successful retry has a newer record.
The helper checks ownership, image and run label; investigate a mismatch instead
of bypassing it.

```bash
bash /home/mdi/local-llm/deepseek-flash17-setup/first-serve-853310da-v1/kit-20261022/node.sh \
  stop 0 20261022T070227Z-1623611
ssh -o BatchMode=yes mdi@192.168.100.2 \
  'bash /home/mdi/local-llm/deepseek-flash17-setup/first-serve-853310da-v1/kit-20261022/node.sh stop 1 20261022T070227Z-1623611'
```

**Skip this if regular Qwen is already running.** This is its documented launcher;
it performs its own startup checks and makes no project OCR request.

```bash
bash "$HOME/local-llm/flash-next-tensorfold/spark-tensorfold.sh" start
```

Confirm the exact alias and run fresh project readiness against the frozen
preview. This performs project text/JSON/four-image controls, retaining raw
responses. Require both **Text: passed** and **vision: qualified**; preflight exit
status alone does not establish vision. JSON unsupported is allowed on Qwen, with
strict schema-in-prompt and local validation retained. No xgrammar installation.

```bash
visual_preview=runs/recovery-vision-input-20261023T192304Z-70e8b9
visual_run=runs/recovery-vision-trial-20261023T192309Z-cdec02
curl --noproxy '*' --fail --show-error --max-time 10 http://127.0.0.1:8890/v1/models
.venv-control/bin/python -m probe.recovery_trial ready --preview "$visual_preview"
read -r -p 'Paste the actual Readiness directory printed above: ' visual_ready
```

The directory is generated by this command; none is predicted here. Readiness
must match the profile and be at most one hour old at launch.

## 4. Run only the 24-case gate, bundle and inspect

This dispatches serially with checkpointing, raw evidence, bounded shared recovery
and the compiler choice from step 2. Its log stays with the run. Detach with
**Ctrl-b, then d**; reconnect with `tmux attach -t pdf2tex-recovery`.

```bash
.venv-control/bin/python -m probe.recovery_trial launch \
  --run "$visual_run" --readiness "$visual_ready" --stage gate \
  "${compiler_args[@]}" \
  2>&1 | tee "$visual_run/operator-gate-$(date -u +%Y%m%dT%H%M%SZ).log"
.venv-control/bin/python -m probe.recovery_trial status --run "$visual_run"
xdg-open "$visual_run/report.html"
```

The gate dispatches only its 24 regions, plus eligible bounded recovery, and
leaves the other 243 regions pending. **Stop after the gate even if it passes.**
Inspect failures and complete replacements; `gate.passed: true` is technical,
not a fidelity score. Do not reset the ledger to force continuation. Bundle the
finished gate using the command below; later phases require a separate decision.

In another terminal, these read-only commands show progress and the log paths:

```bash
.venv-control/bin/python -m probe.recovery_trial status \
  --run runs/recovery-vision-trial-20261023T192309Z-cdec02
ls -t runs/recovery-vision-trial-20261023T192309Z-cdec02/operator-*.log
```

Use `tail -f` on the actual log printed by `ls`. To pause after the current request:

```bash
touch "$visual_run/PAUSE"
```

Wait until status is paused. Remove only the control sentinel when ready:

```bash
rm "$visual_run/PAUSE"
```

Then run fresh readiness and repeat the gate launch with `--resume` added,
retaining `--stage gate` and the same compiler arguments. Do not reset failures
or counters. A hard
interruption consumes an unknown call rather than blindly sending it again.
If you reattach a new shell, reassign the paths above and reconstruct the same
compiler option from `state.json`:

```bash
tex_image=$(.venv-control/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1])).get("compiler_image") or "")' "$visual_run/state.json")
compiler_args=()
if [ -n "$tex_image" ]; then compiler_args=(--compiler-image "$tex_image"); fi
```

After completion or a normal pause, produce a compact partial/completed ZIP:

```bash
.venv-control/bin/python -m probe.recovery_trial bundle --run "$visual_run"
.venv-control/bin/python -m json.tool "$visual_run/latest-bundle.json"
```

The ZIP includes portable inspection HTML, Markdown, failures CSV, structured
ledger/state, selection/provenance and deduplicated source images. Raw HTTP/base64
and reasoning remain in the run. It excludes full PDFs, weights and environments.
Do not run mutating report/bundle/candidate commands while the live writer owns the
project lock; `status` remains read-only and available.

## Later reference only: continue after separate gate inspection

This is outside the current gate-only handover. If continuation is subsequently
chosen and `gate.passed: true`, refresh readiness and resume the same trial;
completed gate requests are skipped. Preserve the same compiler arguments.

```bash
.venv-control/bin/python -m probe.recovery_trial ready --preview "$visual_preview"
read -r -p 'Paste the new actual Readiness directory: ' visual_ready
.venv-control/bin/python -m probe.recovery_trial launch \
  --run "$visual_run" --readiness "$visual_ready" --stage continue --resume \
  "${compiler_args[@]}" \
  2>&1 | tee "$visual_run/operator-continuation-$(date -u +%Y%m%dT%H%M%SZ).log"
```

## 5. Candidate preparation reference (superseded by the current artifacts above)

The current candidate and critic are already prepared; do not regenerate them for
the gate. The new `candidate --dispositions PATH` option requires exact-version
assessments; without it all proposals are deferred. `critic-refresh --recipe PATH`
creates a linked recipe only after frozen requests still match exactly. It never
patches historical seals. See the current first section for actual artifacts,
compilation limitations and the four-pair launch. The later generic stage commands
below remain reference material, not authorization to run development/reserved
before gate inspection.

## 6. Sequential DeepSeek text phase

Once Qwen work has finished, stop only regular Qwen using its documented wrapper:

```bash
bash "$HOME/local-llm/flash-next-tensorfold/spark-tensorfold.sh" stop
```

**Skip the next command if the intended DeepSeek pair is already running.** The
existing successful retry launcher verifies the retained stopped pair/settings,
uses its original memory gates, restarts it, runs its own smoke controls and saves
new deployment evidence. It does not overwrite the successful launch record.
Do not rerun the old first-launch path merely to create new containers.

```bash
python3 -B /home/mdi/Downloads/deepseek-retry-20261022.py
```

The recovered script and successful saved copy were read; no launcher was changed
or executed. Its smoke checks do not replace project readiness. Confirm the exact
DeepSeek ID, then run **text-only** project readiness (no vision gate or image
attachments in this critic path):

```bash
curl --noproxy '*' --fail --show-error --max-time 10 http://127.0.0.1:8894/v1/models
.venv-control/bin/python -m probe.recovery_trial ready --preview "$critic_preview"
read -r -p 'Paste the actual text Readiness directory: ' critic_ready
.venv-control/bin/python -m probe.recovery_trial launch \
  --run "$critic_run" --readiness "$critic_ready" --stage gate \
  2>&1 | tee "$critic_run/operator-gate-$(date -u +%Y%m%dT%H%M%SZ).log"
.venv-control/bin/python -m probe.recovery_trial status --run "$critic_run"
xdg-open "$critic_run/report.html"
```

Require the four-pair gate to pass. Continue remaining development groups with
fresh readiness; completed pairs are not repeated:

```bash
.venv-control/bin/python -m probe.recovery_trial ready --preview "$critic_preview"
read -r -p 'Paste the actual fresh text Readiness directory: ' critic_ready
.venv-control/bin/python -m probe.recovery_trial launch \
  --run "$critic_run" --readiness "$critic_ready" --stage development --resume \
  2>&1 | tee "$critic_run/operator-development-$(date -u +%Y%m%dT%H%M%SZ).log"
```

After inspecting development results, keep the frozen protocol unchanged and run
reserved groups. Tuning requires a distinct future experiment; these groups must
not be described as untouched gold after their results have been seen.

```bash
.venv-control/bin/python -m probe.recovery_trial ready --preview "$critic_preview"
read -r -p 'Paste the actual fresh text Readiness directory: ' critic_ready
.venv-control/bin/python -m probe.recovery_trial launch \
  --run "$critic_run" --readiness "$critic_ready" --stage reserved --resume \
  2>&1 | tee "$critic_run/operator-reserved-$(date -u +%Y%m%dT%H%M%SZ).log"
.venv-control/bin/python -m probe.recovery_trial bundle --run "$critic_run"
.venv-control/bin/python -m json.tool "$critic_run/latest-bundle.json"
```

Pause/status/resume work exactly as for Qwen, using `critic_run`. The reports keep
no finding, incomplete coverage, insufficient context, technical failure, export,
compilation, tokens/time and human assessments separate. Human usefulness, missed
errors, harmful changes and critic false alarms stay unassessed until reviewed.
A text critic may request a small image follow-up; none is automatically launched.

For the later GLM substitution only, use its documented `ABLIT=0 ./start.sh` path
in [SPARK-OPERATIONS.md](SPARK-OPERATIONS.md#4-start-regular-glm-only-if-needed),
with the other heavy model stopped normally. Prepare `--profile glm`, then use
the same fresh text-readiness/gate/development/reserved sequence. GLM is not an
extra mandatory pass.

## Separate optional DeepSeek schema diagnostic

This is independent of the main sequence. With the intended DeepSeek service
available, use its actual prepared paths. The gate consists of four constrained
controls using the **actual historical review schema**, within the 30-call budget.
A tiny preflight JSON pass alone is insufficient. Qualification records accepted
schema requests and locally valid results; it is not proof that a backend could
never emit invalid output. Local validation always remains mandatory.

```bash
diagnostic_preview=runs/schema-diagnostic-input-20261023T192310Z-708e9f
diagnostic_run=runs/schema-diagnostic-trial-20261023T192310Z-252ea1
.venv-control/bin/python -m probe.recovery_trial ready --preview "$diagnostic_preview"
read -r -p 'Paste the actual diagnostic Readiness directory: ' diagnostic_ready
.venv-control/bin/python -m probe.recovery_trial launch \
  --run "$diagnostic_run" --readiness "$diagnostic_ready" --stage gate
.venv-control/bin/python -m probe.recovery_trial status --run "$diagnostic_run"
```

After inspecting the gate, continuation runs the separately recorded feedback
condition. If the actual schema was rejected/failed qualification, remaining
constrained cases stay unsupported/unavailable and are not sent; there is no
silent prompt-only relabelling. Otherwise it runs those constrained cases too.

```bash
.venv-control/bin/python -m probe.recovery_trial ready --preview "$diagnostic_preview"
read -r -p 'Paste the actual fresh diagnostic Readiness directory: ' diagnostic_ready
.venv-control/bin/python -m probe.recovery_trial launch \
  --run "$diagnostic_run" --readiness "$diagnostic_ready" --stage continue --resume
.venv-control/bin/python -m probe.recovery_trial bundle --run "$diagnostic_run"
```

No external bibliography lookup, paper acquisition, source acceptance or model
service control is performed by this project's experiment commands. The local
bibliography foundation and precise upstream adaptation map are documented in
[SCIWRITE-REUSE.md](SCIWRITE-REUSE.md).
