# DeepSeek comparison with historical Qwen Arm A

Prepared offline on 22 October 2026. No earlier DeepSeek implementation or preview
was found in this checkout, so one separate opt-in path was added. **No DeepSeek
project preflight or review request has been sent by Codex.** The completed Qwen
run, native pilot, OCR and existing GLM/critic material are preserved.

MinerU's saved OCR and original images remain the inputs. DeepSeek receives the
same 267 Arm A requests that Qwen received, including Qwen's failed cases; only
the request's model field changes. This compares deployed models and runtimes,
not quantization alone. Successful JSON, proposal counts and agreement with Qwen
do not establish mathematical accuracy. All proposals remain UNACCEPTED.

## Actual prepared artifacts

- Preview: `runs/deepseek-arm-a-input-20261022T180153Z-4d91d8`.
- Separate live directory: `runs/deepseek-arm-a-trial-20261022T180153Z-0ee3cf`.
- Report: `runs/deepseek-arm-a-trial-20261022T180153Z-0ee3cf/report.html`.
- Initial, offline ZIP:
  `results/deepseek-arm-a-trial-20261022T180153Z-0ee3cf-inspection-20261022T180159Z-994ead.zip`
  (10,878,589 bytes). It compares saved Qwen results with pending DeepSeek cases.
  Future ZIPs have new immutable names. The run's `latest-bundle.json` records the
  actual newest path, bytes and SHA-256; check the status/date before calling it final.

The original paired preview was resolved from
`runs/qwen-native-trial-20261021T062027Z-a1f40a/binding.json`:
`runs/qwen-native-input-20261021T062027Z-c025fd`. All 534 historical attempts were
validated, including failures. Qwen A has 238 structurally completed / 29 failed
requests: 26 schema failures, two JSON failures and one token-limit failure.
These are protocol outcomes, not correctness judgments.

All 267 request bodies match historical A after normalizing only the model field.
Input JSON, prompts/schema, images, OCR/drafts, context and frozen ordinal/block
identities are unchanged. The sixteen original PDF pages remain
106,116,126,136,146,156,166,170,176,186,196,205,206,212,218,225. Printed-page numbers
use the registered offset of 15; separator pages may lack a visible folio.
Seventy-eight unavailable/invalid portable drafts remain unavailable: complete
raw OCR is retained, without repair. No native character stream, model correction,
audit diagnosis or expected answer was added. Recognized regions do not cover
unrecognized whole-page omissions.

## Configuration and bounds

| Setting | Recorded value |
|---|---|
| Endpoint | `http://127.0.0.1:8894/v1` |
| Exact model | `DeepSeek-V4.1-Flash-TF` |
| Reasoning | Explicit `medium` |
| Output allowance / timeout | 16,384 tokens / 600 seconds per review |
| Streaming | `false` |
| Server `response_format` | Omitted even if supported; schema in prompt, strict local validation |
| Sampling parameters | Omitted, inheriting this deployment's defaults |
| Review requests | At most 267, sequential, one attempt per region |
| Initial gate | At least 9 valid responses among the first 12; those 12 are not repeated |
| Live admission budget | Eight hours cumulative across resumes, plus the current request's deadline |

Equal reasoning labels and omitted sampling do not establish equal internal
behaviour across deployments. The pinned runtime is
`sha256:35d9bda39ffde364249f21be294dde6aeee9c51940973477ca5728f32422aa35`,
recipe `853310dab967480013eda7cef4e79c2fd041629a`, EXL3 2.8bpw. The launcher binds
the operator's matching first-launch record; it does not independently inspect
running container weights or change deployment settings.

The observed deployment record passed arithmetic, three digit-image tests and
the blank control. Its saved post-test memory was about 8.8 GiB head / 13.4 GiB
peer. These are deployment observations, not a current capacity guarantee or
mathematical OCR qualification. The project still runs fresh text/image controls.

Readiness and optional waiting precede the eight-hour review admission budget.
Waiting defaults to zero; explicit `--wait-ready 3600` permits at most one hour
of `/models` GET polling. A different advertised model or `STOP.json` stops it;
both exact discovery and a matching `SMOKE-PASS.json` are required. No generation
occurs during waiting. Fresh preflight then uses up to seven separately bounded
120-second requests (discovery, text, strict JSON, four image controls). It must
show **Text: passed AND vision: qualified**. Explicitly unsupported server JSON
formatting is allowed; another JSON-preflight failure blocks dispatch. Successful
and failed response identities are checked. Exit status alone is insufficient.

The first twelve regions form a transport/format/claimed-coverage gate, not an
accuracy gate. Failed JSON, truncation and coverage are never repaired or retried.
Two consecutive transport/timeouts pause; identity, evidence-integrity or rejected
configuration stop. A durable reservation consumes an interrupted/unknown request
even if no answer was committed. Explicit resume runs fresh readiness and sends
only pending regions, retaining failures, gate decisions and remaining budget.
Normal paused time is excluded; unknown crash downtime is charged conservatively.
Reliability-gate failure, budget exhaustion and fatal stops cannot be overridden.

Conservative existing TeX fragment/package checks are recorded separately from
format validation. Unsupported LaTeX stays visible and export-blocked; a valid
response does not certify compilability. No proposal is applied or compiled.
Human review must check full replacements and unchanged controls against images,
including signs, indices, bounds, grouping, conditions, logical meaning and
references. Punctuation/style has a separate view, but category labels are model
claims and punctuation can change meaning. Preserve errors actually printed.

## Normal-terminal commands

Run the full synthetic/mock-server suite first. Require **190 tests, OK** before
launch. In the sandbox, 175 passed and 15 failed solely because loopback socket
binding was denied (`PermissionError: Operation not permitted`). All 24 new
DeepSeek tests passed. No permissions were changed.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m unittest discover -s tests -v
```

Enter a dedicated persistent terminal. This handles an existing tmux client
without nesting; it does not launch or alter any model service.

```bash
if [ -n "${TMUX:-}" ]; then
  tmux has-session -t deepseek-arm-a 2>/dev/null || tmux new-session -d -s deepseek-arm-a -c /home/mdi/projects/pdf-to-latex
  tmux switch-client -t deepseek-arm-a
else
  tmux new-session -A -s deepseek-arm-a -c /home/mdi/projects/pdf-to-latex
fi
```

Inside that session, run this **live operator command**. The wrapper uses the
actual prepared directories above, checks project OCR workers have exited,
verifies evidence, binds the supplied successful first-launch directory, performs
fresh preflight and starts the gated sequential review. It records the actual
preflight path automatically, writes `operator.log`, and prints report/ZIP paths
on exit. It never starts/stops services. Codex has not executed this command.

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-deepseek-arm-a-trial.sh \
  --first-launch /home/mdi/local-llm/deepseek-flash17-setup/first-serve-853310da-v1/runs/20261022T171904Z-2128368
```

Watch for both required preflight statuses and dispatch. Detach with **Ctrl-b,
then d**; the job survives remote-desktop disconnection. It can finish or pause
much earlier than eight hours and never adds work to fill the available time.

If deliberately queuing while a separate deployment is loading, append
`--wait-ready 3600` to that command. Omitting `--first-launch` instead reads
`/home/mdi/local-llm/deepseek-flash17-setup/last-first-launch-run.txt` once, prints
and binds its exact directory. Missing/invalid paths fail clearly; resume cannot
switch the bound deployment. This is optional, not needed for the reported
already-running deployment. Nothing under `local-llm` is modified.

From another terminal, inspect the most recent durable checkpoint and log. These
commands send no requests and do not take the writer lock. During a request the
checkpoint can remain unchanged for its 600-second timeout.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m probe.deepseek_trial status \
  --run runs/deepseek-arm-a-trial-20261022T180153Z-0ee3cf
tail -n 30 runs/deepseek-arm-a-trial-20261022T180153Z-0ee3cf/operator.log
```

From outside tmux, return with `tmux attach -t deepseek-arm-a`; from inside another
tmux session use `tmux switch-client -t deepseek-arm-a`. Only after the previous
process has exited, explicitly resume an eligible readiness/connection/interruption
pause with the same wrapper. Do not alter evidence/code/settings or run a second
trial to bypass a stop.

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-deepseek-arm-a-trial.sh --resume \
  --first-launch /home/mdi/local-llm/deepseek-flash17-setup/first-serve-853310da-v1/runs/20261022T171904Z-2128368
```

On normal completion or pause a new compact ZIP is produced. Open the report and
read the actual latest archive location, size and hash:

```bash
xdg-open /home/mdi/projects/pdf-to-latex/runs/deepseek-arm-a-trial-20261022T180153Z-0ee3cf/report.html
cat /home/mdi/projects/pdf-to-latex/runs/deepseek-arm-a-trial-20261022T180153Z-0ee3cf/latest-bundle.json
```

If a hard interruption prevented bundling, create a partial inspection ZIP **after
the process has exited**. This verifies bindings and archives existing evidence
without inference. An uncommitted dispatch remains unknown until reconciled on
resume; the bundle does not turn it into a success.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m probe.deepseek_trial bundle \
  --run runs/deepseek-arm-a-trial-20261022T180153Z-0ee3cf
```

Extract the ZIP and open its run-named `inspection.html`. The archive contains
all 267 comparison records and 283 deduplicated images (267 detail crops and
16 page contexts), full old/new text and final-answer availability, validation
failures, usage and latency. Raw API payloads/base64/reasoning remain in the run.
Aggregate views separate the initial gate and remainder, paired valid results
and missing/nonvalid sides. These are inspection aids, not accuracy scores.
