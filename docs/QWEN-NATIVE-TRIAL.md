# Task 5 — paired Qwen native-evidence trial, revision 2

Prepared offline on 21 October 2026. **No live Task 5 request or readiness call has
been sent.** This is the current operator trial. Task 4 is complete and preserved;
its alternatives are not accepted corrections. No GLM server switch is required.
The operator launches Qwen personally; the launcher never manages services.

## Prepared artifacts and scope

- Sealed preview: `runs/qwen-native-input-20261021T062027Z-c025fd`.
- Separate prepared live directory: `runs/qwen-native-trial-20261021T062027Z-a1f40a`.
- HTML: `runs/qwen-native-trial-20261021T062027Z-a1f40a/report.html`.
- Initial offline ZIP:
  `results/qwen-native-trial-20261021T062027Z-a1f40a-inspection-20261021T062043Z-e6ee87.zip`.
  Exactly **4,676,398 bytes**, SHA-256
  `11cbe67bf43d43320cae18755907e1f4905bc0fad7e1d154871ebd59a59b3233`.
  It contains pending inputs, not model results. Later bundles get new names;
  `latest-bundle.json` in the live directory records the actual path, bytes and hash.

The experiment reuses the 267 recognized regions on all sixteen Task 4 pages,
from `runs/native-text-pilot-20261021T052347Z-094634` and the validated saved
conversion `runs/convert-basic-20261020T075104Z-48fd90`. No extraction was rerun.
Original physical pages remain
106,116,126,136,146,156,166,170,176,186,196,205,206,212,218,225.
Selected-page mapping is original minus 105; original block IDs are retained.

The 48-region priority core runs first: the twelve neutral-pack cases in their
recorded order, then eighteen additional flagged and eighteen additional
unflagged cases. The core covers all sixteen pages and contains 25 flagged /
23 unflagged regions. The remaining 219 contain 177 flagged / 42 unflagged.
Total: 202 flagged and 65 unflagged. Flags are not confirmed errors.

Ordering is fixed before dispatch: SHA-256 ordering with seed
`klebaner-native-paired-revision2-20261021`, round-robin pages with alternating
available flag/math strata within each page. Pair order alternates A/B then B/A.
The evaluator manifest separately marks the known development examples, twelve
previously inspected cases, priority core and remainder. These labels and flags
are never model inputs. This exploratory cohort is neither a fresh independent
holdout nor a representative book-wide accuracy sample. Omissions outside
recognized regions remain outside its coverage.

## What each arm receives

A receives the original source crop and full-page context, raw structured MinerU
OCR, neighbouring OCR context and the unreviewed portable draft where available.
B receives exactly those inputs plus a compact literal native PDF character
stream. Controls are escaped/identified, and line boundaries, signs, punctuation
and ligatures are retained. Positioned per-character evidence stays on disk;
it is not dumped into prompts. No saved correction, gold answer or audit finding
is supplied. Source images decide what is printed; both text streams may be wrong.

Seventy-eight regions lack a valid portable rendering. They retain their raw
structured OCR in both arms and are not silently fixed or excluded. Every region
has two images, retained without regeneration. The maximum prepared request is
492,046 bytes and 9,643 text characters, within the existing 2 MiB / 48,000-character
limits. The twelve original pack cases retain identical OCR and image hashes.

Fixed request configuration:

| Setting | Value |
|---|---|
| Endpoint | `http://127.0.0.1:8890/v1` |
| Exact alias | `flash-next-tensorfold` |
| Reasoning effort | Explicit `medium` |
| Maximum output | Explicit 16,384 tokens |
| Wall timeout | 600 seconds per request |
| Streaming | Explicit `false` |
| Server `response_format` | Omitted in both arms; schema stays in prompt |
| Temperature/top-p/top-k/seed | Omitted, inherited server defaults; no tuning |

The saved successful paragraph retry used this effort, token budget, timeout and
inherited sampling. An alias or effort label is not proof of internal weights or
reasoning behaviour. Actual outgoing request bodies, responses, usage and latency
are retained. Unsupported strict JSON in preflight is allowed; strict local JSON,
existing identity/block-coverage validation and additional category accounting
remain mandatory. Fences, duplicate keys, malformed/schema-invalid responses and
truncation are not repaired. Each request starts a fresh conversation. No other
arm's output is included. Categories are model reports, not verified fidelity.

## Bounds and unattended behaviour

- At most **534 review requests**, one per region per arm; priority 96, remainder
  438. Fresh readiness preflight/discovery is separate. No identical automatic
  retry occurs for any failed arm.
- After twelve pairs, each arm needs at least **9/12 validator passes**. Otherwise
  the job pauses permanently for this sealed protocol. Resume does not bypass
  the gate or change prompts. This is an output-reliability gate, not a fidelity
  or model-capability verdict.
- Two consecutive transport/timeouts pause the job. An explicit resume runs
  fresh readiness checks, acknowledges that pause and processes pending arms
  only. Identity/integrity failures or rejected configuration stop it.
- A durable reservation consumes an arm. If interrupted after reservation, it is
  recovered from a committed assistant response where possible, otherwise marked
  interrupted and never sent twice. All failed/interrupted evidence remains.
- Cumulative live admission is limited to **32,400 seconds (nine hours)**. No new
  request starts after that; the current request may finish within its original
  600-second deadline. Expect review admission plus the final request to take at
  most approximately nine hours ten minutes, plus bounded local reporting work.
  The fresh readiness preflight precedes this budget (up to seven bounded
  120-second requests). Completion or a reliability pause can finish much sooner.
- Normal paused time is excluded from cumulative admission. After a hard crash,
  time since the last durable active checkpoint is charged conservatively,
  including unknown downtime; this can shorten the resumed trial rather than
  create extra budget. Budget and terminal gate decisions persist across resume.

The writer lock prevents concurrent project writers; requests are sequential.
The same-user `/proc` converter check is best effort, not host-wide exclusion.
No services are started/stopped, and the DeepSeek download is untouched. All
proposals remain UNACCEPTED. Do not change code, preview, source evidence or
settings during the job: bindings will reject an incompatible resume.

## Operator commands

Run the full suite in the normal terminal from the project directory. These tests
use synthetic inputs and mock servers, not live models. Require **166 tests, OK**
with no errors/failures before launching. Offline preparation passed 151 tests;
15 known loopback-server cases were excluded in the sandbox, not bypassed.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m unittest discover -s tests -v
```

Enter the dedicated tmux session. This block switches sessions if already inside
tmux, avoiding a nested tmux client; otherwise it creates or attaches the session.
No model service changes occur.

```bash
if [ -n "${TMUX:-}" ]; then
  tmux has-session -t qwen-native5 2>/dev/null || tmux new-session -d -s qwen-native5 -c /home/mdi/projects/pdf-to-latex
  tmux switch-client -t qwen-native5
else
  tmux new-session -A -s qwen-native5 -c /home/mdi/projects/pdf-to-latex
fi
```

In that session, launch the prepared run. This is the **live** command; Codex has
not executed it. It checks converter exit, verifies all bound inputs, discovers
the exact endpoint alias, runs a fresh preflight through project APIs, captures
its actual path and requires both `Text: passed` and `vision: qualified`. It then
starts the bounded paired job. No directory needs pasting. Preflight exit status
alone is insufficient, and simple-image qualification is not mathematical
qualification. If Qwen is unavailable, the launcher records a clear failure and
leaves services and prepared work alone.

```bash
cd /home/mdi/projects/pdf-to-latex
set -o pipefail
.venv-control/bin/python -u -m probe.paired_trial launch \
  --run runs/qwen-native-trial-20261021T062027Z-a1f40a \
  2>&1 | tee -a runs/qwen-native-trial-20261021T062027Z-a1f40a/operator.log
```

Watch until readiness passes and dispatch starts before leaving. Press **Ctrl-b,
then d** to detach; remote-desktop disconnection does not end the tmux process.
The job stops itself at completion, a gate/pause or the budget. It does not add
work to fill the absence. No GLM call or server switch is part of this stage.

From another terminal, monitor the atomic status and log without taking the
writer lock or sending requests. Status shows the last checkpoint, so it can
remain unchanged during a request's 600-second timeout.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m probe.paired_trial status \
  --run runs/qwen-native-trial-20261021T062027Z-a1f40a
tail -n 30 runs/qwen-native-trial-20261021T062027Z-a1f40a/operator.log
```

To return to tmux from outside it:

```bash
tmux attach -t qwen-native5
```

If already inside tmux, use `tmux switch-client -t qwen-native5`. For an eligible
connection/interruption/readiness pause, run the **same launch block above** in
that session. It resumes only pending arms with the remaining budget. It never
repeats completed, failed or consumed interrupted attempts. Do not repeatedly
resume a reliability, identity, integrity, configuration or exhausted-budget
stop; those cannot be overridden by this launcher.

The launcher writes the report and a new compact ZIP on normal completion or
pause. Open the report and print the actual latest ZIP path, exact bytes and hash:

```bash
xdg-open /home/mdi/projects/pdf-to-latex/runs/qwen-native-trial-20261021T062027Z-a1f40a/report.html
cat /home/mdi/projects/pdf-to-latex/runs/qwen-native-trial-20261021T062027Z-a1f40a/latest-bundle.json
```

If a hard interruption prevented the final bundle, or another partial bundle is
needed, run this **only after the job has stopped**. It takes the project lock,
validates evidence and creates a new ZIP without inference or overwriting earlier
archives. A changed/invalid source binding is a blocker, not silently ignored.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m probe.paired_trial bundle \
  --run runs/qwen-native-trial-20261021T062027Z-a1f40a
```

## Reports and assessment after the live job

The full local HTML covers all 267 regions and every attempted arm, including
failed/interrupted/pending work. Aggregate and per-region ledgers distinguish
matched completed pairs, incomplete pairs, validation failures, model-reported
content/punctuation/style/uncertainty, tokens and latency, separately for priority,
remainder and overall. No mathematical correctness or usefulness score is inferred.

The compact ZIP retains complete ledgers and neutral text export, plus the
priority core's deduplicated context/detail images, OCR/native evidence and both
answers/outcomes. It adds at most twelve attempted remainder cases: failures first,
then incomplete pairs, then differing validated answers, then other attempted
cases; frozen order breaks ties. It does not select only apparent successes. Raw
API payloads, base64 requests and reasoning fields stay in the live run, outside
this inspection ZIP. Archive names are immutable; `latest-bundle.json` selects the
latest actual archive. Extract and open its run-named `inspection.html`.

`neutral-critic.json` is a text-only, source-hash-linked export for a later GLM
critic. It has no evaluator labels and explicitly cannot establish visual fidelity.
No GLM inference stage is implemented. `source-audit-plan.txt` requires comparing
complete replacements and unchanged controls with images, recording improvements,
regressions, misses, unreadability and insertion/compilation issues separately.
Codex judgments must be labelled as such, not independent human gold. Actual
useful/harmful-change assessment awaits live results; fewer proposals do not
establish accuracy, review-time savings or monetary savings.
