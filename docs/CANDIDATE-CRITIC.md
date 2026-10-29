# Candidate-only critic: GLM first, selected MiMo — 25 October 2026

## Task 2 update — 25 October 2026, development copy only

The GLM run `runs/candidate-critic-trial-20261025T133737Z-95be74` and selected
MiMo run `runs/candidate-critic-trial-20261025T213705Z-c506ee` are completed.
The original reports, requests, seals and outcomes remain unchanged. The initial
"zero calls" preparation table below records historical preparation, not current
status. Do not replay or reseal these runs under the changed implementation.

New preparations use `critic-anchors-v3`. Candidate/draft hashes and exact input
binding are recorded by Python; the response cites bound anchors and passage ID,
not regenerated document hashes. Version 2 and the original quotation contract
still validate according to their recorded schemas. An observed wrong hash or
identity is rejected, never overwritten or silently corrected.

Format repair returns changes to the exact invalid fields, not a newly rewritten
assessment. Valid findings, uncertainty and references remain exact. Removed
unexpected fields are retained separately as extra commentary requiring review.
Optional new-protocol commentary has its own field. Truncated JSON is never
salvaged. Two additional calls per original passage, shared context/repair/paid
limits and durable reservations remain unchanged.

The local index now retrieves leading numbered statements through an observed
structural boundary (proof/new statement/section), including associated displays
and adjacent-page continuation. It excludes folios, distinguishes passing mentions,
normalizes verbose requests and deduplicates them while preserving their wording.
No arbitrary next-two-block stopping rule remains. A gap, unresolved transcription,
ambiguous label, missing boundary or an over-budget statement stays explicit;
a heading alone cannot justify a new theorem reassessment. The existing limits
are eight added context blocks / 18,000 characters and one contextual reassessment.
Current candidate text and unreviewed saved OCR remain separately labelled.
Structural boundary detection is not evidence that a theorem has been verified.

Importance, source-image next action, context dependency and technical coverage
are separate dimensions. A material claim may also need a source check; missing
context for one claim does not erase other supported claims. Pure context requests
are not accusations of author error. Cosmetic and positive observations remain
available in collapsed queues. Overlapping exact candidate spans plus claim topics
identify *potential* agreement for inspection; different categories or anchor-set
sizes do not hide it. Non-repetition is not disagreement. This is not a semantic
proof or a source audit. Diagnostic controls remain separately labelled from
automatic difficult/seeded clean selections; no new live selection was prepared.

Saved MiMo evidence confirms five passage calls (four first attempts plus one c03
context reassessment), about 23m01s, USD **0.0680012862** including readiness,
cumulative linked USD **0.2397167286**, and no unsettled charges. This historical
figure is not the current key balance. All four initial target/candidate/draft
bindings match GLM. No credential was read. Existing spending controls, explicit
operator dispatch, pinned Xiaomi route and no fallback are unchanged.

See [TASK2-DEVELOPMENT.md](TASK2-DEVELOPMENT.md) for validation/copy-back and
[GATHERAL-REVIEW.md](GATHERAL-REVIEW.md) for the next actual candidate boundary.
Old preparations intentionally fail live code-binding checks after integration;
create a new candidate-derived preparation, never patch old seals.

## Historical calibration preparation

Use this sequence for the next calibration. MinerU extracts locally; Qwen compares
source images; the versioned candidate preserves reviewed decisions and unresolved
content; **GLM is the default text critic**. DeepSeek remains selectable. MiMo is
an explicitly enabled, costed second opinion. None accepts or applies critic
findings. Do not run heavy local model phases concurrently.

## Prepared now, offline

| Artifact | Actual path |
|---|---|
| Existing candidate, preserved | `runs/evaluation-candidate-20261024T140145Z-6343d9` |
| Editable/reviewed passage manifest | `docs/critic-calibration-passages.json` |
| New sealed GLM preview | `runs/candidate-critic-input-20261025T133737Z-8816e4` |
| New GLM run, zero calls | `runs/candidate-critic-trial-20261025T133737Z-95be74` |
| HTML / Markdown / data report | same run: `report.html`, `report.md`, `route-summary.json` |
| Initial compact ZIP | `results/candidate-critic-inspection-20261025T133737Z-564db1.zip` |
| Operator pointer (actual paths, no shell memory needed) | `results/candidate-critic-current.json` |

The eight passages contain **75 distinct target blocks**, with context counted
separately. They span physical PDF pages 126, 146, 166, 170, 176, 205–206 and 212.
Controls c01/c02 were independently inspected against existing source images by
Codex, with no material discrepancy observed in their selected statements. That is
not human verification or a whole-page accuracy claim. c07 retains the entire
510-character PDF 205/b15 paragraph, including its unresolved transcription;
the formula-only proposal remains deferred. Selection rationale and later quality
criteria live in [the separate assessment](evidence/candidate-critic-calibration-20261025.md),
never in requests. The actual candidate already has three unresolved blocks and
recorded `build_failure_unresolved`; this preparation neither repairs nor compiles it.

Protocol `critic-anchors-v2` uses deterministic whole-block anchors bound to the
candidate version, original block hash, exact text, offsets and source map. Python
retrieves quotations. Unknown/duplicate/stale anchors fail validation. The legacy
quote protocol remains available for historical evidence; no old request, seal or
success count is rewritten. A valid reference establishes location, not truth.

New production requests contain the current candidate once, with a material-math
prompt and exact bounded context. No source images, old model diagnoses, expected
corrections, assessment documents or gold TeX are sent. There is no automatic
sentence splitter. The local index contains 1952 blocks from the same saved edition
and 564 detected labels; lookup is explicitly partial. Theorem 6.2 has ambiguous
matches; some earlier blocks cannot be represented portably; Theorems 2.35/3.18
are outside the converted selection. These remain visible gaps. Added context is
whole labeled blocks with a bounded neighborhood, not a claim to contain an entire
theorem/proof. A model may request a specific local reference for at most one
contextual reassessment. Missing/unreadable/unconverted evidence is not fabricated.

### Frozen settings and shared bounds

- GLM: `glm53-regular`, `http://192.168.1.100:8888/v1`, requested high, 32768
  completion tokens, 900 seconds per request, serial/non-streaming, existing
  sampling defaults omitted. High is requested; backend interpretation is unproven.
- Eight local baselines; **eight shared additional passage calls**; at most **two
  additional calls per original passage**. Context and schema feedback share these
  allowances. The first MiMo second opinion also consumes an additional call.
  A passage that used both local follow-ups cannot acquire a fresh allowance by
  escalating. Limits survive resume and linked paid preparation.
- Four hours cumulative active admission for the local-origin workflow. A paid
  stage additionally admits at most two hours, clipped to the original time
  remaining; one already admitted call may finish within its timeout. Pauses do
  not reset time already consumed. No identical exhaustion retry or unverified
  lower-reasoning control. Truncated final content remains truncation even when
  reasoning used most tokens. Missing reasoning counters remain unknown.
- MiMo stage: at most **four selected passages**, at most **two additional paid
  context/format calls across the stage**, subject to the tighter inherited
  passage/global limits. One separately bounded paid readiness, 2048 tokens /
  120 seconds. Local readiness has at most two attempts; reuse a still-fresh passed
  readiness on resume. An exhausted readiness allowance is a visible stop.
- Selection is frozen before live answers: up to one seeded apparently-clean
  passage (`seed=20261025`), then difficult passages in prepared order for the
  remaining slots. Insufficient-context responses are valid but unresolved.
  Cosmetic, visual-only and service/infrastructure failures do not trigger cloud
  fallback. Budget-exhausted eligible cases stay outside the paid selection.

Reports separate final passage outcomes from attempts and queue material concerns,
context requests, visual/assembly checks, technical gaps and collapsed editorial
observations. Low/info severity alone does not make a mathematical claim editorial.
Deduplication retains draft identity and every contributor; superseded/provisional
findings are labeled and receive no current completion credit. Never infer
correctness from valid JSON, compilation, empty findings or model agreement.
The existing isolated compiler/recovery path is retained; setup/access errors are
not model-output errors. A text critic does not itself generate a new compiled
candidate or apply a proposed correction.

## 1. Tests and workload check — normal terminal on the Spark

Run the full tests with real-compiler opt-ins disabled. Mock loopback sockets denied
in Codex's sandbox should work here. Stop on application failures.

```bash
cd /home/mdi/projects/pdf-to-latex
env -u PDF2TEX_COMPILER_IMAGE .venv-control/bin/python -m unittest discover -s tests -v
```

Check project OCR exit, current jobs and both nodes' memory. Read-only process/state
snapshots are not proof that an unobserved external job is idle. Do not stop a job
just because a port check fails. Arrange the regular GLM window personally if a
heavy phase is still active; use the existing deployment instructions in
[SPARK-OPERATIONS.md](SPARK-OPERATIONS.md).

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python - <<'PY'
from pathlib import Path
from probe.saved_pages import converter_idle
from probe.common import read_json
root=Path.cwd()
print(converter_idle(root))
for p in sorted((root/'runs').glob('*/state.json')):
    s=read_json(p)
    if s.get('active_since_epoch') is not None or s.get('status')=='running':
        print('Recorded active state (check actual process):',p.parent,s.get('status'))
PY
ps -u "$USER" -o pid,etime,args | rg 'probe|mineru|tensorfold|deepseek|glm|qwen'
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}'
free -h
ssh -o BatchMode=yes -o ConnectTimeout=10 spark-92a4 'free -h'
```

**Skip this launcher if regular GLM is already running.** Use it only after the
operator has confirmed the previous heavy local phase is finished and memory is
available. It is the existing regular-model launcher, not a program-managed switch.

```bash
(
  cd "$HOME/local-llm/glm53-flash-tensorfold" &&
  source "$HOME/venvs/menv_hf/bin/activate" &&
  ABLIT=0 ./start.sh
)
```

## 2. Eight-passage GLM calibration — first live step

Start/reattach tmux, then enter the following block inside its shell. No prior
shell variables or manually pasted readiness directory are needed. The wrapper
reads the actual preparation pointer, checks `/v1/models` for the intended exact
alias, obtains fresh **text-only** schema readiness, captures its saved path and
launches serially only if it passes. It never starts/stops services or reads a key
for local operation. It writes progress and bundles on a stopped/completed run.

```bash
tmux new-session -A -s candidate-critic
```

```bash
cd /home/mdi/projects/pdf-to-latex
set -o pipefail
bash scripts/run-candidate-critic.sh run 2>&1 | tee -a runs/candidate-critic-trial-20261025T133737Z-95be74/operator.log
```

Detach with Ctrl-B then D; reattach using the same tmux command. In another shell,
`status` is read-only. `pause` creates the existing pause marker and lets the current
bounded call finish. Wait for the writer to exit before `resume` in tmux. It reuses
completed calls and consumed budgets, checks seals/settings, and refreshes readiness
only when needed and allowed. A changed source/code/identity stops, without fallback.

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-candidate-critic.sh status
```

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-candidate-critic.sh pause
```

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-candidate-critic.sh resume
```

After stopping/completing, open `runs/candidate-critic-trial-20261025T133737Z-95be74/report.html`.
To regenerate report/ZIP only while no writer is active:

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-candidate-critic.sh report
bash scripts/run-candidate-critic.sh bundle
```

`bundle` prints the actual new ZIP path; the run's `latest-bundle.json` records it.
The ZIP contains exact selected inputs, report/data, attempts, usage/billing and
readiness records, excluding the full book/context index and credentials. The raw
full responses remain in the original run. Technical completion is not the quality
assessment: separately inspect useful detections, false alarms, missed problems and
justified context requests against the source, using the frozen external criteria.

## 3. Offline selective MiMo plan — only after GLM completes

These commands make **no network requests** and do not read the key. They select
from the actual new GLM outcomes, bind exact candidate anchors/context and inherited
allowances, and link the completed MiMo pilot's costs. They print the actual plan
path and cost preview. Inspect the plan's `selection.json` and `cost-preview.json`
before creating the paid preparation. No future paid selection/result path is assumed.

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-candidate-critic.sh select
bash scripts/run-candidate-critic.sh cost
```

No eligible or affordable follow-up is an explicit stop, not a reason to send every
clean passage. Selection may contain fewer than four. Do not retune the seed or
thresholds after seeing calibration answers. If the plan is appropriate, prepare
its sealed requests offline; the pointer `escalation-run.json` under the GLM run
captures the actual new result path for subsequent commands.

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-candidate-critic.sh prepare-selected
bash scripts/run-candidate-critic.sh mimo-cost
```

Cost preview lists actual passage count, each input's bytes/token reservation,
empirical estimate, **1.5× planning margin**, and conservative uncached reservations
for every selected baseline, both possible paid follow-ups and the one readiness.
The empirical pilot mean is **USD 0.0143096202 per planned passage**, including
repairs/readiness, not a maximum. Four would extrapolate to USD 0.0572384808,
or USD 0.0858577212 with the planning margin. 200/400/600 would be approximately
USD 2.86/5.72/8.59 before that margin; those are all-book planning extrapolations,
**not authorized dispatches**. Passage density and failures can change costs greatly.
No cache discount is assumed for reservation. The hard USD 10 ceiling is separate.

Pinned Xiaomi rates recorded 25 October are USD 0.435/M uncached input and 0.87/M
output, not another provider's discounted model-page rate. The existing authenticated
readiness/dispatch checks verify current endpoint rates and capabilities before
POST. Prior known spending USD 0.1717154424 and any unresolved reservations count
against the same ceiling. Current authenticated key remaining allowance is checked
as well: other applications may have spent since the historical record.

## 4. Selected MiMo live stage — explicit operator opt-in

Run this in tmux after reviewing the offline cost/selection. It uses the already
existing raw-key file `/home/mdi/.config/pdf-to-latex/openrouter.key`; do not recreate,
overwrite, print or source it. No account setting or key limit is changed. The key
must retain its already arranged non-resetting USD 10 limit. The wrapper prints
costs first, performs its one bounded authenticated readiness when needed, captures
the actual readiness path and dispatches only the sealed selected requests.

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-candidate-critic.sh mimo-run
```

Profile remains `xiaomi/mimo-v2.6-pro`, provider `xiaomi/fp8`, no fallback,
`reasoning.enabled=true`, 32768 output tokens / 900 seconds. This does not establish
graded effort or a separate reasoning-token cap; neither is sent. Documented
30-day retention is accepted under the below-100-day policy. Training opt-ins and
account privacy settings remain untouched. See the saved
[provider evidence](evidence/glm-mimo-route-20261025.json) and its public sources.

The following operations resolve the actual paid result path from the saved pointer.
Status is read-only; pause finishes the current bounded call. Resume only after it
has stopped. Report/bundle only after the writer exits. `mimo-bundle` prints the ZIP
path and updates that paid run's `latest-bundle.json`; actual failed-call costs and
unknown reservations remain visible. Potential agreements, differing claims and
unresolved cases are shown without treating non-repetition as disagreement or proof.

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-candidate-critic.sh mimo-status
```

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-candidate-critic.sh mimo-pause
```

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-candidate-critic.sh mimo-resume
```

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-candidate-critic.sh mimo-report
bash scripts/run-candidate-critic.sh mimo-bundle
```

## Reuse and limits

For a different already-created candidate, `python -m probe.critic_route boundaries
--candidate ACTUAL_PATH --out NEW_MANIFEST` emits an editable manifest and unresolved
boundaries. Review it, then use `prepare --candidate ... --conversion ... --source ...
--passages ... --profile glm` (`deepseek` is the explicit alternative). These are
interface descriptions, not invented artifact paths to run now. The preparation
never clips text or silently includes unsupported targets. It rejects stale hashes
and duplicate/order-inconsistent target selections. Requested input limits and
selection policy are sealed. The conversion default and old paired experiment
remain unchanged. See [GATHERAL-PLAN.md](GATHERAL-PLAN.md) for the concrete adapter
needed before protected whole-book visual review and complete candidate assembly.

Offline validation does not establish live GLM/MiMo quality, server interpretation
of reasoning, fresh provider prices, live billing, or real TeX compilation. Compiler
setup/access failures remain separate from syntax errors under the existing adapter.

Unused preparations may be refreshed after a code change only when they have zero
calls, zero readiness attempts and zero consumed time. The new seal records the old
code/preview/run lineage and leaves it untouched. Any consumed cohort requires an
explicit continuation preserving allowances; this command refuses to restart it.
The MiMo body retains the exact candidate and source context but excludes free-form
local lookup queries as well as model diagnoses. Those queries remain in the local
evidence; they are not an implicit unverified claim in the second opinion.
