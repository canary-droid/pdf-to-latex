# Selected-passage GLM / MiMo critic pilot — 25 October 2026

## Completed comparison — supersedes the preparation status below

Both arms are completed and frozen. GLM: **7/12 final technically valid**, 16 calls,
1469.064623 seconds elapsed (24.5 minutes). MiMo: **11/12 final technically valid**,
14 passage calls including two repairs, plus one readiness; 2782.185833 seconds
elapsed (46.4 minutes). Saved DeepSeek selected reference: **9/12 final technically
valid**, 13 calls and 4125.856758 seconds summed request latency (68.8 minutes).
These are technical/timing counts, not mathematical accuracy scores; elapsed and
summed request time are different measures. All findings remain UNACCEPTED.

The MiMo ledger records **USD 0.1717154424**, including readiness and repairs,
zero unresolved reservations. Historical local remainder USD 9.8282845576 is not
today's account balance. Final compact comparison:
`results/critic-glm-mimo-inspection-20261025T112007Z-ca5ee9.zip`.
The existing run paths in the table below remain the completed evidence. Do not
relaunch their historical commands or patch their seals.

Next use [CANDIDATE-CRITIC.md](CANDIDATE-CRITIC.md): eight new candidate-only GLM
passages, stable Python anchors, then at most four explicitly selected MiMo
passages under inherited costs and shared follow-up limits. The old twelve-passage
selection and sixteen-call validation remain frozen.

## Historical preparation and operator procedure

The following records the preparation before the completed MiMo run.

The existing private key is already saved. These commands do not create or overwrite
it. The operator must personally set that key's **non-resetting USD 10 spending
limit** before readiness. No account setting is changed by this program.

## Scope, policy and fixed profiles

The frozen order is `g01-Y, g02-X, g02-Y, g04-Y, g05-X, g05-Y, g07-X, g07-Y,
g08-X, g09-X, g09-Y, g10-Y`: twelve requests, eight passage groups, four paired
groups and four singleton groups. X is the baseline; Y is the experimental
candidate, with unresolved content retained. Both new models receive byte-identical
saved passage data and identical generic task messages. No images, diagnoses,
prior findings, expected corrections, new context or g11–g20 reserved passages enter
requests. The evaluation manifest separately records prior ChatGPT assessments,
not human gold. This challenge set was selected partly because DeepSeek struggled;
it is not an unbiased book-wide benchmark.

| Profile | Model and route | Requested reasoning | Response mode |
|---|---|---|---|
| Local GLM | `glm53-regular`, `http://192.168.1.100:8888/v1` | `reasoning_effort=high` | Schema in prompt; strict local validation |
| Opt-in MiMo | `xiaomi/mimo-v2.6-pro`, `https://openrouter.ai/api/v1`, only `xiaomi/fp8` | `reasoning={"enabled":true}` | Strict JSON schema plus the same local validation |
| Saved DeepSeek reference | `DeepSeek-V4.1-Flash-TF` | Recorded medium | Historical prompt-schema results; no new calls |

Each new arm allows twelve baseline requests and **four total additional** format/
quotation repairs, at most two per parent. Requests are serial, non-streaming,
32768 maximum completion tokens and 900 seconds. Sampling is omitted, preserving
server defaults. There is no automatic lower-reasoning or token-exhaustion retry.
Each arm has at most two separately counted harmless readiness calls, each 2048
tokens / 120 seconds. Admission also has the existing eight-hour cumulative active
time bound. One in-flight call may finish within its request timeout.

The inspected local TensorFold launcher/template documents GLM low/high/max and
32768-token support; high is the existing qualified GLM profile. Xiaomi documents
thinking enabled/disabled; OpenRouter documents explicitly enabled default reasoning.
No graded MiMo high/medium support or equal computation is assumed. Requested
controls and reported usage are distinct; missing reasoning counters remain unknown.
See [Xiaomi thinking documentation](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/other/deep-thinking)
and [OpenRouter's mapping](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens).

**Explicit user policy clarification, 25 October:** for this project's nonpersonal
published book material, documented retention **below 100 days** is acceptable.
[OpenRouter's provider table](https://openrouter.ai/providers) lists Xiaomi as
not training on prompts and retaining data for 30 days (checked 25 October).
MiMo therefore uses `data_collection=allow`, `zdr=false`, `only=["xiaomi/fp8"]`,
`allow_fallbacks=false`, `require_parameters=true`. No authenticated ZDR proof is
required. This accepts the published policy; it is not a live API attestation of
retention, or an EU/UK residency guarantee. No training opt-ins or account-wide
privacy settings are changed. If account settings prevent the request, investigate
the refusal; this program does not relax those settings.

The narrow AGENTS amendment records this exception. Local conversion and default
critic behavior stay local. No failure automatically sends text remotely. This is
not authorization for cloud OCR or the whole Gatheral book. Ordinary OpenRouter
inference access is sufficient; no Xiaomi account/key, model download or Open WebUI
configuration is needed.

Before every paid dispatch the client checks the exact endpoint, standard FP8 tier,
required reasoning/schema capabilities and rates against the frozen ceilings:
$0.435/M input, $0.87/M output, $0.0036/M cached input. No alternate provider,
paid plugin, web search, remote tool, redirect or blind network retry is enabled.
Public evidence and sources are in
[glm-mimo-route-20261025.json](evidence/glm-mimo-route-20261025.json), based on
[endpoint metadata](https://openrouter.ai/api/v1/models/xiaomi/mimo-v2.6-pro/endpoints)
and [routing documentation](https://openrouter.ai/docs/guides/routing/provider-selection).

**Total MiMo ceiling: USD 10**, including readiness, failed requests, repairs and
unresolved charges. This is a total, not USD 10 added to an earlier allowance.
The amount is sealed as `config.budget_usd`; `--budget-usd` is a preparation option,
not a live override. Positive whole-cent amounts are supported. Future increases
require explicit user approval and a new linked preparation; no code edit is needed.
Model, provider, twelve requests, token/time limits and retry allowances stay fixed.

Before POST, the durable ledger reserves full uncached input cost plus the maximum
output allowance. The input bound is the UTF-8 byte count of the entire JSON body
(including schema) plus 4096 framing tokens, not an average token estimate. Observed
token/cost overflow halts admission. The twelve actual baseline bounds remain
15707–22984 input tokens; their combined maximum remains **$0.441222240**, before
readiness/repairs. Repairs are sized and admitted individually. Nothing is truncated.

The key must have a non-resetting limit **equal to the sealed amount: USD 10.00**.
A USD 1 or USD 100 key, or a resetting limit, is refused. Remaining allowance is
checked privately before dispatch. Actual reported costs replace reservations;
missing charges keep their maximum reservation, including across resumes or budget
amendments. GET-only generation lookup can reconcile known IDs; unknown IDs remain
reserved. Unknown charges may conservatively count against both remaining key
allowance and the local ledger. Missing/tampered evidence fails closed. The program
never raises a limit, enables top-up or changes account privacy/training settings.

The original [route evidence](evidence/glm-mimo-route-20261025.json) records the
initial USD 1 authorization historically; this dated amendment supersedes its
budget only. Its provider/routing evidence and all completed runs remain unchanged.

## Actual preparation and saved reference

| Artifact | Path |
|---|---|
| New frozen comparison / criteria | `runs/critic-glm-mimo-input-20261025T101917Z-661df0` |
| Preserved GLM preview | `runs/critic-glm-input-20261025T075343Z-62c704` |
| Completed GLM run, reference only | `runs/critic-glm-trial-20261025T075343Z-4034ea` |
| New USD 10 MiMo preview | `runs/critic-mimo-input-20261025T101919Z-6fda9b` |
| New MiMo run | `runs/critic-mimo-trial-20261025T101919Z-ebb7eb` |
| New comparison report | `runs/critic-mimo-trial-20261025T101919Z-ebb7eb/comparison-report/report.html` |
| Offline compact ZIP | `results/critic-glm-mimo-inspection-20261025T101920Z-54f53b.zip` |

The new MiMo run is **prepared_offline, zero calls/readiness/charge reservations**.
`results/critic-glm-mimo-current.json` points here. The USD 1 comparison at
`runs/critic-glm-mimo-input-20261025T075341Z-b68be4`, its zero-call MiMo run
`runs/critic-mimo-trial-20261025T075343Z-a006b2`, and all earlier preparations stay
unchanged. Do not launch them. Their old code bindings have not been patched.

The new lineage records the old/new budgets and parent hashes. All twelve MiMo
input/request files are byte-identical; only its budget configuration changed.
Historical GLM and DeepSeek attempts remain labelled inherited. New reports and ZIP
pointers are written under the **new MiMo run**, preserving the completed GLM report.
The amendment mechanism retains prior calls, readiness slots, elapsed admission
time and settled/unknown charges when present; it does not grant more attempts.

GLM used twelve baseline and four repair calls, with seven final valid responses.
The five remaining failures concern quotation/location checks, schema validation
and a repair that dropped findings. They are preserved, not retried here. Technical
usability does not establish content accuracy or make MiMo contingent on GLM passing.

The saved follow-up and overnight evidence is unchanged. The overnight job stopped
at its technical checkpoint: 7/12 first valid, 9/12 final valid, 6/12 complete claimed
coverage; twelve baseline plus two repair calls, no reserved calls. Within this
new selected sample specifically, DeepSeek has **8/12 first valid, 9/12 final valid**,
three failed units and one quotation repair: thirteen historical calls, 53372 input
and 269726 output tokens, 4125.86 seconds summed request latency. Reasoning counts
were not reported. Those denominators differ from the full overnight cohort.

The side-by-side report shows exact quotes, locations, complete final findings,
context requests, editorial observations, failures, per-attempt metrics, requested
versus returned identity and actual MiMo costs. Valid JSON, quotation validation,
many findings or a completed response do not establish mathematical correctness.
Independent inspection should judge useful detections, missed issues, harmful
suggestions, false alarms and context handling before speed or cost. No automatic
winner or acceptance is produced.

## 1. Normal-terminal tests, then tmux

Run the full suite in the normal terminal; it includes mock loopback servers denied
by Codex's sandbox. The environment override leaves unrelated opt-in real compiler
tests disabled. Stop on unexpected failures.

```bash
cd /home/mdi/projects/pdf-to-latex
env -u PDF2TEX_COMPILER_IMAGE .venv-control/bin/python -m unittest discover -s tests -v
```

Start or reattach the persistent trial terminal, then run the next block inside it.
Detach with Ctrl-B then D; reconnect with this same command. MiMo needs no local GPU
or service switch. Leave the existing GLM deployment and unrelated jobs alone.

```bash
tmux new-session -A -s pdf-critic-pilot
```

## 2. Existing key, fresh readiness, then MiMo

First set the existing OpenRouter key's spending limit to **USD 10 with no reset**
yourself. Keep its raw contents unchanged and account privacy/training preferences
unchanged. The path below is nonsecret; the program reads the raw key only at your
runtime, adds the Authorization prefix and does not print it. Do not source the
file or paste its contents. Existing owned mode-600 file / mode-700 directory
requirements remain unchanged.

This block defines every variable it needs. Readiness checks the exact Xiaomi FP8
route, rates/capabilities and matching key limit with authenticated metadata GETs,
then makes one small **paid synthetic text-only** call. It obtains the actual saved
readiness path from the ledger and launches only on success. Launch sends the same
twelve passages with at most four shared repairs, all within the USD 10 total.
No readiness directory is guessed or manually pasted. The readiness must be fresh
within one hour at launch; it is not an accuracy test. If any step fails, inspect
its diagnostic instead of repeatedly consuming the two readiness allowances.

```bash
cd /home/mdi/projects/pdf-to-latex
export OPENROUTER_API_KEY_FILE=/home/mdi/.config/pdf-to-latex/openrouter.key
mimo_run="$PWD/runs/critic-mimo-trial-20261025T101919Z-ebb7eb"

.venv-control/bin/python -m probe.critic_pilot ready --run "$mimo_run" --allow-paid &&
mimo_ready=$(.venv-control/bin/python - "$mimo_run" <<'PYREADY'
import json, sys
from pathlib import Path
r = Path(sys.argv[1])
a = json.loads((r / 'readiness-ledger.json').read_text())['attempts'][-1]
assert a['status'] == 'passed', 'Readiness did not pass'
print(r / 'readiness-attempts' / a['id'])
PYREADY
) && test -s "$mimo_ready/readiness.json" &&
.venv-control/bin/python -m probe.critic_pilot launch \
  --run "$mimo_run" --readiness "$mimo_ready" --allow-paid
```

## 3. Monitoring, pause/resume and inspection ZIP

From another terminal, read progress and the USD ledger without network access or
interrupting the writer. Unknown charges appear as reserved rather than zero.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m probe.critic_pilot status \
  --run runs/critic-mimo-trial-20261025T101919Z-ebb7eb
```

To pause, create its PAUSE marker. The current bounded call finishes; no next call
starts. Wait for status to show no active writer before resuming or bundling.

```bash
cd /home/mdi/projects/pdf-to-latex
touch runs/critic-mimo-trial-20261025T101919Z-ebb7eb/PAUSE
```

Resume uses the existing successful readiness (the executor checks its age), removes
only the pause marker and preserves calls and charges. If readiness expired, run
`ready` as above once within the remaining readiness allowance, then use this
resume block. Do not reset the run/key or create a duplicate to regain attempts.

```bash
cd /home/mdi/projects/pdf-to-latex
export OPENROUTER_API_KEY_FILE=/home/mdi/.config/pdf-to-latex/openrouter.key
mimo_run="$PWD/runs/critic-mimo-trial-20261025T101919Z-ebb7eb"
mimo_ready=$(.venv-control/bin/python - "$mimo_run" <<'PYRESUME'
import json, sys
from pathlib import Path
r = Path(sys.argv[1])
s = json.loads((r / 'state.json').read_text())
assert s['active_since_epoch'] is None and s['status'] != 'running', 'Writer still active'
passed = [a for a in json.loads((r / 'readiness-ledger.json').read_text())['attempts'] if a['status'] == 'passed']
assert passed, 'No successful readiness'
(r / 'PAUSE').unlink(missing_ok=True)
print(r / 'readiness-attempts' / passed[-1]['id'])
PYRESUME
) && test -s "$mimo_ready/readiness.json" &&
.venv-control/bin/python -m probe.critic_pilot launch \
  --run "$mimo_run" --readiness "$mimo_ready" --allow-paid --resume
```

After the writer stops, this optional **GET-only** command looks up unresolved
charges with known generation IDs. It cannot resend a completion or clear unknown
charges without evidence. It reads the existing credential only at operator runtime.

```bash
cd /home/mdi/projects/pdf-to-latex
export OPENROUTER_API_KEY_FILE=/home/mdi/.config/pdf-to-latex/openrouter.key
.venv-control/bin/python -m probe.critic_pilot reconcile \
  --run runs/critic-mimo-trial-20261025T101919Z-ebb7eb --allow-paid
```

Normal launch exit already produces a compact ZIP. Its actual path, size and hash
are in `comparison-latest-bundle.json` under the **new MiMo run**. After the writer
stops, the following block refreshes the HTML/Markdown/JSON report and creates another
ZIP, then opens the report and prints that pointer. Partial results are supported.
Do not run report/bundle while a writer is active. The completed GLM report is not
rewritten. The ZIP contains selected passages/requests, outcomes, validation,
metrics, budget and lineage evidence; it excludes full PDFs, credentials and raw
model reasoning. Original response evidence stays in its original directories.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m probe.critic_pilot bundle \
  --comparison runs/critic-glm-mimo-input-20261025T101917Z-661df0
xdg-open runs/critic-mimo-trial-20261025T101919Z-ebb7eb/comparison-report/report.html
cat runs/critic-mimo-trial-20261025T101919Z-ebb7eb/comparison-latest-bundle.json
```

## Future approved budget amendments

The current USD 10 preparation above already exists; do not prepare it again.
For a future explicitly approved increase, use `reprepare-mimo --comparison` with
the actual current comparison and `--budget-usd` with the newly approved **total**.
This is an offline operation, not an account change or inference command. It creates
new identities and binds their lineage, retaining previous costs, unknown charges,
calls, readiness slots, elapsed time and unchanged request bytes. It references the
completed GLM arm rather than creating a replacement. Read the printed new paths;
old preparation/seal files must never be edited. A prior active/unsealed attempt,
billing halt or incompatible task-code change must be resolved first.

`prepare --budget-usd` is for a separately authorized new experiment, not a way to
reset this pilot. Neither command grants more passage, token or retry allowances.
The default for new experiments is the current USD 10 approval; later amounts are
supplied explicitly without a code change. Runtime key-limit validation uses the
sealed amount, never an unsealed environment override. A budget increase does not
replenish readiness calls; if both slots are spent, stop for review.

## Gatheral and remaining limits

The next whole-book target is Jim Gatheral, *The Volatility Surface*. The intended
destination `inputs/gatheral/source.pdf` is **absent** as checked on 25 October.
The user's Windows source is
`C:\Users\marcd\Documents\Marco\Books\Obsidian_Books\Other\The Volatility Surface.pdf`.
No hash, edition, PDF page count or physical/printed mapping is invented. No new
source is registered. Transfer/intake verification, contents/appendices/bibliography
inspection and full-book processing remain subsequent work; Klebaner is preserved.

MiMo live readiness, effective backend reasoning behavior, schema enforcement,
actual billing and substantive critic quality remain untested. GLM/DeepSeek have
saved live results, preserved here as evidence rather than mathematical verification. No real key was read and no
model, OCR, compiler, service, install, permission or Git operation was performed
by Codex. Offline tests qualify control flow and evidence handling, not accuracy.
