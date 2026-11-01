**1 November 2026:** this suite is finished and preserved. Its useful outputs are
reconciled by [BOOK-COMPLETION.md](BOOK-COMPLETION.md); do not rerun the experiment.
The preparation and launch descriptions below are historical.

> Completed after operator launch:19 work requests plus one readiness,18 normal
> responses and one truncated Max critic; four Low-stage calls skipped because
> the probe renderer lacked template extensions. No production continuation.
> Next: [the linked overnight suite](OVERNIGHT-WORKFLOW-SUITE.md), not a rerun.
> Original reports/controls remain frozen; version-specific reporting and repairs
> are retained separately in the new derivative.

# Bounded GLM speed suite — 29 October 2026

This is a separate, opt-in experiment. It admits at most **23 work generations**,
one attempt each, across the five fixed stages below, then exits. It never resumes
the Bergomi queue, adopts an experiment output, or starts an articles job. All
results remain experimental and unaccepted. Mathematical accuracy takes priority
over timing; the twelve-hour book target is not a deadline or a promised result.

Actual preparation: `runs/speed-suite-20261029T191756Z-3933e0`.
Report: `runs/speed-suite-20261029T191756Z-3933e0/report.html`.
The current ZIP path is recorded in that directory's `last-inspection.json`.
**Prepared, not running: zero model requests made during development.**

## One launch, then an automatic stop

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-speed-suite.sh run
```

The wrapper resolves `results/speed-suite-current.json`; no manual run or readiness
variables are needed. It runs the normal-terminal full tests once per code/test
identity, checks the project writer, both nodes' workloads and memory, and the
**existing** exact `glm53-regular` service. It never starts/stops/reconfigures a
service. It starts tmux `pdf-speed-suite`, captures one small text readiness request,
and runs the fixed stages automatically. Actual run/log/report paths are printed.
Current source/image/template hashes must match the saved runtime binding. No
cloud client, key file, model downloads or alternative deployment are involved.

These commands use the same separate pointer:

```bash
bash scripts/run-speed-suite.sh status
bash scripts/run-speed-suite.sh pause
bash scripts/run-speed-suite.sh resume
bash scripts/run-speed-suite.sh bundle
```

Status is short and read-only. Pause stops admission and drains every owned request
and its document finalization. The status remains `draining` until the writer locks
are released; only then is it `paused`. `stop` is also available if partial stream
capture rather than draining is explicitly wanted. Resume retains all outcomes and
reservations; it never repeats a completed, failed or uncertain work request.
Uncertain in-flight reservations require read-only diagnosis before a new launch.
Bundle requires a released run lock; it creates a new inspection ZIP. Attach with
`tmux attach -t pdf-speed-suite` if desired; detaching does not stop the worker.

At the end: `suite_finished_for_inspection`, report, ZIP and exit. Repeating run or
resume after that terminal state makes **zero requests, including readiness**.
There are no overall/generation deadlines. Connection establishment retains its
10-second timeout. Readiness is separately counted, once per genuine launch/resume;
work is not replenished following a failure. A future production continuation is a
separate explicit action, requiring a linked preparation for the changed code.

## Frozen selection

Ranges below are **physical PDF pages of target blocks**, not whole context scope.
The manifest lists every target block and context page, source/draft hashes,
dependencies, control records and exact concrete request bodies. Future critics
seal their sources/template/settings and own-conversion dependency now; their exact
draft hash and actual body are saved before dispatch. No fabricated draft is sent.

| Stage | Targets and controls | New work maximum | Controlled change |
|---|---|---:|---|
| 1 | Pending Bergomi4-s03 (157–167),5-s01 (168–169),6-s01 (218–219),6-s06 (223–230), each with its own critic | 8 | Up to four in flight; exact production construction, High/Max |
| 2 | Bergomi digest2-s11+s12 (113) and2-s15+s16 (116–117); individual calls084–087 and092–095 retained as controls | 4 | Adjacent target grouping only; High/Max, unchanged full-chapter context/prompt |
| 3 | Saved initial critic-input drafts for Bergomi4-s01,4-s02 and pilot Gatheral7-s05 (127–128); Max calls112,113,037 | 3 | Exact historical critic requests, only `reasoning_effort: max → high` |
| 4 | Complete Klebaner Chapter4, PDF106–136 (31 owned pages): dual extraction versus native PDF text alone, same relative assets/locators | 4 | Same short conversion and focused Max-critic prompts across arms; High conversion. Critics see their own arm's declared sources |
| 5 | Bergomi4-s01 (150–152) and4-s02 (152–156); High/Max calls110–113 retained | 4 | Exact conversion requests, only `high → low`; new own-draft critic stays Max |

All work keeps131,072 combined reasoning/final output tokens, durable streamed
reasoning/answers, no sampling overrides, the current isolated compiler and its
bounded dependency recovery, and separate original/revised TeX and accuracy logs.
There are no JSON content contracts, required output block markers or acceptance
loops. A failed conversion makes only its own critic unavailable. Other independent
work may proceed; identity/integrity, unsafe memory, unowned requests and shared
HTTP/connection failures stop admission globally and retain/drain existing work.

Stage1 first checks the actual runtime slots, both nodes' available memory and the
sum of full prompt/output reservations against90% of the shared pool. The four
conversion reservations total1,180,532 conservative token units, versus1,813,708
under the last recorded2,015,232-token pool. **These are preparation bounds, not
fresh live capacity evidence.** A setting named parallel is insufficient. If four
cannot be admitted, Stage1 skips with evidence, without replacement calls.

Stages2–5 retain the same reference concurrency2 regardless of Stage1's outcome.
A large pair serializes under the same pool policy. A one-slot runtime requires a
common serial reference before these stages. There is no adoption of a faster
setting mid-comparison. Compiler finalization remains coordinator-owned, and no
stages overlap. Server overlap and useful final output are reported separately
from reasoning-token volume and are not mathematical qualification.

Low is explicitly named by the exact cached GLM template (hash matches saved
serving metadata). The controller has no Jinja2; it inspects that branch offline.
At launch, a read-only check evaluates the installed request-options mapping and
renders the actual template inside the existing container, without generation.
If Low cannot be confirmed, Stage5 skips; it never substitutes `none`, an unsupported
effort or another model. A changed runtime identity stops the comparison.

## Inputs, inspection and timing

All13 currently concrete requests fit the recorded1,048,576 context window using
the existing conservative UTF-8-byte input estimate plus4,096 template margin and
the full131,072 output allowance. Bounds range204,766–600,310 (asset locator text
included). These are not exact tokenizer counts. Every actual body, including a
future critic's draft/notes, is rechecked against current health before dispatch.
No source clipping, automatic splitting or output-limit reduction is allowed.

The Klebaner chapter uses cached MinerU material and cached native text, selected
pages1–31 / original106–136, exactly once. Native text may flatten mathematical
layout; supplying asset references does not provide model-visible images. Missing
or image-only content remains a fidelity limitation. This is an approximation of
the reported Open WebUI workflow, not a reproduction of its unknown extraction or
settings. No expected Theorem4.14 correction is added to either prompt.

`report.html`, `report.md`, `summary.json` and the inspection ZIP distinguish source
accounting, useful response completion, compilation, model review and the limited
independent source check. `source-checks/` records four selected source-page regions
and historical findings, outside all model inputs. New findings/omissions/false
alarms still need inspection; historical Max responses are not an answer key.

Large raw streams and full reasoning remain local under `calls/`, with paths,
seals and sizes in `evidence-index.json`. The compact ZIP includes exact requests,
answers, original/revised TeX, differences, accuracy notes, compiler outputs, source
check images and relevant reasoning excerpts. Relative image assets are included
once; copy `assets/` beside a selected document for standalone compilation. The
operator launcher/worker also copies concise reports and JSON diagnostics into
`/home/mdi/Downloads`; offline preparation stays inside the project sandbox.

Planning ranges, deliberately broad: Stage1 roughly0.2–3.7h; Stage2 0.1–1.2h;
Stage3 0.2–1.7h; Stage4 1–8h; Stage5 0.2–1.7h. These use saved matched controls or
nearby section sizes, with a wide uncertainty factor; the complete-chapter arm is
especially uncertain. They are not deadlines. Failed output exhaustion can be
slow. Batch wall time includes finalization; overlapping request durations must
not be summed as elapsed time. No whole-book ETA is inferred from tiny recaps.

## Preserved production state and roadmap

Checkpoint: `08a452d88f0a18875fac2f2eec64df84b4849e39`, main tracking origin/main.
Production pointer remains `runs/editorial-chapters-trial-20261029T165410Z-1f2179`.
It is paused with113 calls plus24 earlier calls, no active reservation, both locks
free. Calls112/113 finished and compiled before the writer released at18:20:54 UTC.
The17:59:27 pause record's assertion that work had already drained was premature;
that historical evidence is preserved. New pause reporting does not make that claim.

The264-task production scope has22 completed conversions,22 completed critics,
two unusable-document conversions with unavailable critics, and108 pending pairs.
No complete conversion is currently awaiting its critic. Section2-s10's call083
finished normally but yielded an ambiguous surrounded document fence; no eligible
complete draft was selected, so no critic was sent. The raw answer remains intact.
The two-slot sample102/103/105/106 yielded4 usable results over3,662.35 active batch
seconds,41,391 non-reasoning completion tokens and177,142 reasoning tokens. This is
operational evidence across two sessions, not a matched serial speedup.

| Ordered roadmap | Current status / evidence | Next action and acceptance condition |
|---|---|---|
| 1 Concurrency | Two slots operational; ownership race repaired. Four-slot bounded Stage1 prepared | Inspect real overlap, binding, resource safety and useful output; do not promote on reasoning throughput alone |
| 2 Coherent recap grouping | Two saved-control groups prepared in Stage2;44 pending recap opportunities /69,641 native characters recorded separately | Source-check classification, adjacency and preserved content before any later production regrouping; no pending queue edits here |
| 3 High vs Max critic | Three exact-input comparisons prepared in Stage3 | Inspect material detections, omissions and introduced errors; Max is not unquestionable truth |
| 4 Native/Open WebUI-style chapter route | Dual/native Chapter4 arms prepared in Stage4 | Check whole-chapter delivery and representative mathematics/references; conversion time separate from criticism/compiler |
| 5 Low conversion and alternative output strategies | Low/Max Stage5 prepared. **Edit-only critic** and **deterministic MinerU plus correction** remain unimplemented/deferred | Source-check final content before effort adoption. Later edit-only work needs exact draft identity and paragraph-preserving application; deterministic output needs a separate fidelity comparison |
| 6 Pinned runtime/model serving trial | Deferred; current image/source/template binding unchanged | Separate image/checkout with rollback, matched weights/effort/context/workload; no upgrade during these experiments |

No additional calls are authorized by an inconclusive stage. After inspection,
production use needs an explicitly chosen configuration and new linked preparation
preserving this paused production history. Do not invoke the ordinary book launcher
to finish this suite.

## Offline validation

Final full suite:604 tests in217.705s;585 passed,15 mock-loopback socket binds were
sandbox-denied (`PermissionError: Operation not permitted`), four opt-in real compiler
checks skipped. No assertion failures. All23 new suite regressions and19 existing
concurrency regressions pass. No sandbox/permission changes were attempted. The
launcher runs the full suite in the normal terminal once before inference; optional
real-compiler tests retain their existing environment opt-in.

Actual saved preparation was exercised: all23 frozen IDs,13 concrete request bodies,
31-page Chapter4 ownership, source/asset mapping, Stage1 request equality and
Stages3/5 effort-only differences verified. All consumed production/control files
retain their original hashes. Syntax, shell syntax and `git diff --check` pass.
Four source pages were visually inspected in the bounded assessment; this is not
new-output verification. Actual four-stream serving, live capacity/memory, installed
Low-render execution and new isolated compilation remain operator checks. The
controller uses conservative byte-based context admission, not an exact tokenizer.
