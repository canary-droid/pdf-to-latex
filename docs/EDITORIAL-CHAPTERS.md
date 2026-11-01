# Annotated simple chapters — 27 October 2026

**1 November 2026:** the active operator path is
[the reconciled finite book completion](BOOK-COMPLETION.md). Production remains
historically paused at 113 calls; speed and overnight finished at 20/46 calls.
Do not rerun those suites or resume their old bound queue to finish the books.
The new completion pointer preserves their outputs and admits only missing spans.
All earlier operator paths below are dated history.

## Current operator path — 29 October 2026: overnight finite suite

The earlier speed suite finished (19 work calls, one readiness; four Low calls
skipped after a renderer probe error). Production remains paused at113 calls.
Use [OVERNIGHT-WORKFLOW-SUITE.md](OVERNIGHT-WORKFLOW-SUITE.md): a separate linked
44-request preparation, at most two in flight, automatic final stop, no production
adoption or continuation. No generation/overall deadline or service change.

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-overnight-suite.sh run
```

Same wrapper: `status`, `pause`, `resume`, `bundle`. It captures readiness and
refreshes a small Downloads progress file automatically. Exact scope, repairs,
source checks and untested behavior are in the new runbook. The following entries
are historical; do not rerun the completed suite or resume old code-bound production.

## Historical operator path — 29 October 2026: bounded speed suite, automatic stop

The production continuation below has since run and safely paused at113 calls.
Both Chapter4 critics completed; no writer remains. The new authorized work is a
separate five-stage experiment, **at most23 work calls**, followed by an unconditional
stop for inspection. It does not resume the book queue or adopt experimental output.
Read [the bounded-suite instructions](BOUNDED-SPEED-SUITE.md) for the exact targets,
capacity controls, saved comparisons and source-check limitations.

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-speed-suite.sh run
```

This automatically captures readiness inside persistent tmux after required tests
and checks of the existing regular GLM deployment. No service changes or manual path
pasting. Use the same wrapper with `status`, `pause`, `resume` or `bundle`. Pause
means admission stops and active requests/finalization drain; `paused` is published
only after writer release. A finished suite run/resume causes zero model requests.
All later production adoption, edit-only criticism, deterministic rendering and
runtime upgrades remain separate. The old production pointer/evidence are unchanged;
changed code requires a later linked production preparation, not a resealed old run.

## Historical launch preparation — 29 October 2026: ownership repair, two slots only

**Prepared, not running:** `runs/editorial-chapters-trial-20261029T165410Z-1f2179`.
The authoritative wrapper pointer selects this linked continuation of
`runs/editorial-chapters-trial-20261029T153847Z-0c89a4`. The original stopped run,
all requests/responses, both completed outputs and compiler records are unchanged.
The new run inherits103 calls plus24 earlier calls; none is replayed. Its two-slot
pilot is explicitly **interrupted, not qualified**, with two of four requests done.

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-editorial-chapters.sh run
```

This runs required normal-terminal tests once for the changed code/test identity,
checks writer ownership and both nodes' workloads/memory, verifies the **existing**
`glm53-regular` service, then launches persistent tmux `editorial-chapters` with
fresh readiness captured automatically. No service restart, setting change or model
substitution. Current runtime source/image/template identity must match the inherited
`concurrency-runtime-binding.json`; sources, prompts, sections, High conversion/Max
criticism, sampling omissions,131,072 output tokens and compiler policy remain fixed.
No overall call ceiling or execution/generation deadline; connection timeout10s.

Next: critic for **Bergomi3-s02**, whose conversion is saved, and conversion of
**Bergomi3-s03**, subject to capacity. These finish the interrupted four-request
operational sample. If binding, useful output, overlap and resource checks pass,
continue the remaining queue at **maximum two**. There is **no automatic four-slot
stage**. More reasoning tokens or a compiled document do not establish performance
benefit or mathematical correctness. Each task gets one attempt; independent failures
remain gaps, while shared identity/integrity/infrastructure faults stop admission.
There are112 pending conversions and113 pending critics; dependent critics may become
unavailable if their conversion fails. Existing2-s07/2-s10 gaps remain unchanged.

The old guard compared a cached two-request health sample with the one remaining
local request after collecting call102. The fix invalidates that sample whenever
completion changes ownership and checks each snapshot against its contemporaneous
owned call IDs. Fresh excess server activity still stops dispatch and drains owned
work. `concurrency-stops/` now records the first stop timestamp, raw sampled counts,
sample evidence path/time, local call/task IDs and completion transitions. Final
reports label interrupted samples accordingly. Aggregate server health does not
expose request identities; it cannot establish the absence of all external activity.

Saved evidence: last health at16:14:36 UTC showed2 server/2 local requests; call102
finished16:14:46, then call103 drained until16:32:29. The guard event itself was not
timestamped in the old code; its trigger after call102 finalization is reconstructed.
Docker logs were sandbox-denied. If independent server-log confirmation is needed,
this optional read-only normal-terminal command does not contact the model API:

```bash
docker logs --timestamps --since 2026-10-29T16:14:30Z --until 2026-10-29T16:15:00Z glm53-flash-tf 2>&1
```

Controls work in a fresh terminal without remembered variables:

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-editorial-chapters.sh status
bash scripts/run-editorial-chapters.sh pause
bash scripts/run-editorial-chapters.sh resume
bash scripts/run-editorial-chapters.sh bundle
```

`status` is read-only; `pause` stops admission and drains active requests; `resume`
retains every completion and captures fresh readiness. Ambiguous attempts are never
silently replayed. `bundle` requires a free writer lock. `stop` retains partial streams
without stopping GLM. Terminal: `tmux attach -t editorial-chapters` (detach Ctrl-B,D).

Actual report: `runs/editorial-chapters-trial-20261029T165410Z-1f2179/report.html`.
Log after launch: `runs/editorial-chapters-trial-20261029T165410Z-1f2179/terminal.log`.
Diagnosis: `ownership-diagnosis.md/json`; operational progress:
`concurrency-report.md/json`; current documents/PDFs: `state.json.editions`.
Full reasoning/wire evidence stays linked to original call folders. The diagnosis
and current stop records are included in inspection bundles. Source fidelity remains
separate from compilation and model review. See
[ownership diagnosis](evidence/editorial-ownership-repair-20261029.md).

### Historical initial concurrency handover (before calls102/103)


The paused stage contains17 completed conversions,16 revised critics, two
`complete_answer_without_document` conversions and two unavailable dependent critics.
There are113 pending conversions and114 pending critics (227 possible requests,
plus fresh readiness); actual critics can be unavailable after a failed conversion.
All100 recorded calls plus24 earlier calls are retained. Gatheral has34 selected
parts with recorded passing compilation. Bergomi has18 selected parts:14 passing
compilations, three syntax failures and one missing-context/macro failure. None of
those inherited technical failures is repaired or rerun by this concurrency task.
The original full Chapter1 remains retained. OCR remains520 pages/65 windows,
8,102 blocks, nine blank notices and118 preserved renderer fallbacks; front/back
supplements and all unresolved mathematical/image questions remain as recorded.

Bergomi2-s10 conversion call083 finished `stop` after261.771s:158,623 prompt tokens,
12,355 completion tokens, one reported reasoning token; prefill84.4087s/decode177.0397s.
Its37,323-character final response is an analysis/fragment answer, with no
`documentclass`, `begin{document}` or `end{document}`. Existing extraction rejected
it with `Final answer retained but no unambiguous complete LaTeX document` (surrounded
fence did not contain a complete document). Its critic has **no reserved call**:
`unavailable — No complete conversion to review`. The phase announcement therefore
was neither a critic completion nor a transport failure. Bergomi2-s07 has the same
non-document outcome class. Both remain explicit gaps; no content/protocol repair
is smuggled into this task.

The actual production requests inspected comprise19 High conversions (7,067.706
summed request seconds) and16 Max critics (7,693.997s). Tokens, prefill/decode and
finish reasons are extracted per request in the linked `handover-audit.json`.
Compiler elapsed time was not recorded in those outcomes and remains unknown.
These serial measurements are not a forecast for all remaining sections. The old
42-hour estimate and21–26-hour alternatives are historical, unvalidated projections.
Saved health showed four slots, context1,048,576 and pool2,015,232 tokens; actual
running build, available memory and parallel admission must be established at launch.

### Ordered performance roadmap — no automatic promotion of later items

|Item|Status and evidence|Next action|Acceptance condition|
|---|---|---|---|
|1. Concurrent requests on current GLM|Two-slot ownership race repaired/offline tested; two successful calls retained, two pilot requests remain. Four deferred; no automatic promotion.|Run the command above; finish the existing four-request sample and continue at at most two after operational checks. Inspect non-reasoning output, failures and source fidelity; four needs a separate decision.|Correct ownership/bindings, useful complete output, actual overlap, resource stability and source-preserving request identity. Accuracy/source checks stay distinct.|
|2. Group untouched pending recaps|Deferred, documentation only. Initial handover repeated-heading heuristic found46 untouched apparent recap units,74,602 native characters, across8 chapters:5.9% of1,267,535 pending native characters and40.7% of113 pending conversion units. Previously54 included eight now-completed Chapter2 recaps.|After concurrency inspection, verify recap classification on source pages; group only contiguous untouched/unreserved units. In this frozen handover,8 groups could reduce113 pending conversions to75; re-evaluate then.|Every target block retained once in order, references/assets/locators intact, coherent context/output, explicit old/new maps. Repeated headings are not duplicate content to delete. No regrouping of completed drafts awaiting critics. Fewer calls do not prove proportional time savings.|
|3. High critic versus saved Max reviews|Deferred; current production critics stay Max.|Use saved successful High drafts: one ordinary control and difficult mathematics/references. Send same draft/sources to High only, with fixed sampling/output and no conversion replay.|Source-informed useful findings, omissions, false alarms and introduced changes assessed independently; Max is not truth.|
|4. Simple native-PDF-text/Open WebUI-style Chapter4|Deferred; one later Klebaner comparison, not before concurrency/grouping or alongside production. Reported16min was conversion alone. Inspected proof of Theorem4.14 had a substantive coefficient/superscript error; no exhaustive one-error claim.|Recover original WebUI extraction/settings if readily available, else label installed native extraction as approximation. One whole Chapter4 request with prompt: “Can you please convert this PDF into LaTeX, and give me the LaTeX file, either for copy/paste for for download?” Explicit High/current131,072, provenance outside prompt; no block assignments/JSON/sentinels. Then focused dual-source critic.|Retain both versions, no clipping, account for absent graphics; source-check known issue plus representative mathematics/completeness. Time conversion, critic and compiler separately. Input/prompt comparison is not extractor-only causation; historical effective settings are unknown.|
|5. Low conversion; edit-only critic; deterministic MinerU rendering|Three deferred alternatives, not implemented or implicitly scheduled.|Separate small source-checked Low→High study; later full-section critic returning precise edits/notes with immutable draft binding and paragraph-preservation protection; separate deterministic rendering→GLM correction quality experiment.|No blanket Low accuracy assumption, no stale edits or lost paragraphs, all sources/versions and unresolved issues retained; no silently removed conversion/review coverage. Each route needs its own tested commands before use.|
|6. Pinned TensorFold/runtime comparison|Deferred; current model/runtime unchanged. Recipe tag alone insufficient; this launcher captures actual build.|After scheduling/effort results, compare pinned separate image/checkout on real matched mathematical work. Record weights/quantization/drafter/KV/context/template/effort; retain existing image/weights for rollback.|Usable output and source-informed quality as well as wall throughput, matching settings and reversible deployment. Headline kernels/other-model gains are not book speedup. No upgrade during this job.|



## Earlier preparation — 29 October 2026: saved repairs and remaining Bergomi

**PREPARED, not running.** The completed checkpoint was
`runs/editorial-chapters-trial-20261028T215454Z-8ef98f`, with 64 calls plus 24
earlier calls. Its normal-terminal suite passed 551 tests (four optional skips).
It stopped intentionally after full Bergomi Chapter 1, not after the whole book.
All original evidence remains unchanged.

The new linked run is
`runs/editorial-chapters-trial-20261029T103643Z-713678`.
The wrapper's pointer already selects it. Use the authoritative project checkout,
not an older `/tmp` development copy. Launch with this single command:

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-editorial-chapters.sh run
```

This runs the full normal-terminal tests once per code/test identity, checks no
converter/other project writer is active, checks both nodes' existing regular GLM
containers and GPU process ownership, records actual available memory, checks exact
`glm53-regular` discovery and idle health/context capacity, then starts tmux
`editorial-chapters`. Container membership comes from `docker top`, not a generic
Python exemption. The verified GNOME remote-desktop process is preserved; its memory
is never credited back. Unknown workloads block launch. An unavailable or wrong
service gives an error; this command does not start, stop or switch model services.

The persistent worker captures fresh text readiness automatically, recompiles the
two saved repairs with the qualified isolated image, rebuilds Gatheral, then runs
the **132 remaining Bergomi conversion/critic pairs** in source order. First:
`bergomi-02-s01`, physical PDF42–44, with full Chapter 2 context. Last: bibliography.
Each complete conversion gets its critic immediately. Checkpoints rebuild at chapter
boundaries, then at completion. A failed independent unit remains a visible gap;
it is not automatically retried and does not prevent later independent work.

Full Bergomi Chapter 1 (PDF18–41) reuses calls063/064. Stale u040/u041 explicitly
adopt u330/u331; they cannot dispatch. The completed conversion request matches the
current request exactly. There are 133 distinct targets total, 6,650 remaining target
blocks, with no duplicate ownership. All 88 consumed calls remain in history.
The new stage admits 264 task IDs: **132 conversions, up to132 critics**, plus one
readiness per launch. No overall numerical call ceiling, overall deadline or
generation deadline; one attempt per scheduled task, 10-second connection timeout,
manual pause/stop/resume. Old sealed limits remain historical evidence.

Conversion is explicit **high**, critic **max**, each requests **131,072** combined
reasoning/output tokens, streamed capture and no sampling overrides. Both source
extractions are present in all132 saved conversion bodies. Full chapter context fits
the recorded capacity for all132: conservative combined bounds150,602–789,514 versus
1,048,576. These are UTF-8 byte/template upper estimates, not tokenizer counts.
Live health capacity and every actual critic request including draft/notes are
checked before dispatch. No source clipping or service changes.

Saved repairs (no inference):

- Gatheral Volatility Swaps: added `amsfonts` for `\mathbb`, fixed the unmatched
  inline-math closer, and removed the program's duplicate raw-note appendix by
  selecting the original complete critic document as the repair source. The original
  converter, critic, appended version and logs remain intact.
- Bergomi Chapter 1: corrected both editorial explanations to
  `2 sigma_hat^4/N^3` for an averaged sum with the same prefactor. The main estimator
  and variance remain unchanged. The note attributes this local algebra to Codex.
  Empty/header/umbrella log entries are historical, not additional open findings.
- Generated navigation escapes control characters visibly (including U+001D).
  Raw titles and source mathematics remain unchanged. Placeholder pages are not
  counted as retained content or included PDFs.
- Current saved dispositions separate applied GLM claims, contextual observations,
  source-inspection needs and independently checked repairs. GLM saying “verified”
  does not create independent verification. Genuine jump/Lewis/gamma/footnote
  questions remain open. The selected TeX has no mechanically undefined labels or
  missing referenced assets; literal reference numbers are not thereby verified.

Editable prepared editions (relative to the new run):

- `editions/gatheral-1793270210665074077/master.tex`
- `editions/bergomi-1793270211271047422/master.tex`

Each contains `chapters/<key>/document.tex`, relative assets, accuracy logs and
coverage. The repaired versions are also in
`versions/gatheral-11-s02-part05/codex-saved-repair-20261029/document.tex` and
`versions/bergomi-01-s01/codex-saved-repair-20261029/document.tex`, beside exact diffs.
Gatheral has all34 retained parts,33 inherited successful PDFs and one repaired
part awaiting compilation. Bergomi has one retained chapter, whose original
compiled PDF is preserved; its repaired note version awaits compilation. Both new
masters are uncompiled here because Docker access is sandbox-denied. A successful
master containing placeholders will still report incomplete delivery.

Bergomi's520-page/65-window extraction,8,102 recognized blocks, nine intentional
blank notices and118 renderer fallbacks are reused without OCR. Unit targets span
PDF18–519. PDF1–17 and520 remain source supplements, with native TeX/text/page maps
and assets retained separately. In particular the preface at PDF16–17 and other
front matter do not yet have a reviewed typeset TeX view. Preservation is not fidelity
certification. Gatheral's front matter/index remain its original-page supplement.

Report: `runs/editorial-chapters-trial-20261029T103643Z-713678/report.html`.
Prepared inspection ZIP:
`results/editorial-chapters-inspection-20261029T103643Z-713678-1793270641823459579.zip`.
Log after launch: `runs/editorial-chapters-trial-20261029T103643Z-713678/terminal.log`.
`state.json.editions` and `last-inspection.json` locate actual later PDF/report/ZIP
outputs. The console identifies book, chapter/section, phase, model and run path.

```bash
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh status
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh pause
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh resume
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh bundle
```

Status is read-only. Pause finishes the current response; resume captures fresh
readiness and skips consumed tasks. `stop` preserves an interrupted stream without
replaying an uncertain call. Bundle only while paused/finished; finalization bundles
automatically. Attach using `tmux attach -t editorial-chapters`, detach with Ctrl-b d.
Once launched, leave this checkout and bound inputs unchanged. A later library task
must use an independent development copy and must respect project/run `.probe.lock`.

## Historical preparation — 28 October 2026: production continuation after the pilot

**Prepared only; not running.** Completed pilot:
`runs/editorial-chapters-trial-20261028T072031Z-41483c` (37 recorded calls plus
24 earlier calls). All six pilot task calls returned normally and their documents
compiled. Faster high-effort conversions support this next task; they do not
establish a fixed speedup or mathematical accuracy.

New linked preparation:
`runs/editorial-chapters-trial-20261028T215454Z-8ef98f`.
The pointer used by the existing wrapper identifies this run and retains the old
integration receipt. Do not launch an older `/tmp` copy or the completed pilot.

Run this **one normal-terminal command**:

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-editorial-chapters.sh run
```

It runs the full offline test suite once for this code/test identity, saving a
`normal-terminal-tests-*.log` and stopping clearly on failure. It checks workload
ownership, the existing regular two-node GLM deployment, exact `glm53-regular`
discovery and current context capacity, then starts persistent tmux session
`editorial-chapters`. It never starts/stops/substitutes a service. A wrong,
unavailable or busy deployment fails clearly. The worker captures one fresh
text readiness automatically; no readiness path or remembered shell variable is
needed. Tests are not repeated before every chapter or unchanged resume.

Execution order (each conversion immediately followed by a max critic if it
returns a complete draft):

1. **Including Jumps**, Gatheral 7-s03, physical 124–125.
2. Gatheral 11-s02 in its six already prepared natural subsection outputs:
   variance-swaps introduction (167–169), Heston variance swaps (169), skew and
   curvature (169–171), jumps (171–174), volatility swaps (174), Heston convexity
   adjustment (175–177).
3. Gatheral 11-s03 in five already prepared natural subsection outputs:
   introduction/power payoffs (177–178), Laplace transform (178–180), fair volatility
   (180–182), lognormal model (182–185), volatility options (185–187).
4. Assemble/compile the new Gatheral edition, keeping any failed units as gaps.
5. **Bergomi Chapter 1, Introduction, physical 18–41**, one full chapter conversion
   and critic. Then assemble its partial edition and **stop for inspection**.

There are **13 conversions and at most 13 critics**, plus one readiness per launch.
One attempt per scheduled task, no automatic retries. No pilot/control calls are
replayed. An isolated generation failure remains a gap; it does not block the next
independent unit. Identity/integrity errors or repeated connection failures stop
execution. No overall or generation deadline; connection timeout remains 10 seconds.
Conversion effort is explicit **high**, critic effort **max**, output allowance
**131,072 each**; sampling overrides remain absent. Effective runtime thinking is
not independently attested by usage counters.

The new local overall-call ceiling is explicitly JSON `null` (unlimited), **not a
large sentinel**. All 61 consumed calls remain in linked history. Only the sealed
26 task IDs can dispatch; historical calls cannot consume this admission, and
readiness on a later manual resume is not blocked by an accumulated call quota.
Historical artifacts, including the old Bergomi preparation's 98-call record,
remain unchanged; the new binding owns execution limits. Paid and other experimental
limits are unchanged.

Full chapter context and both complete extractions reach every prepared conversion.
Conservative input + template + output bounds range from 193,905 to 376,410 against
the recorded 1,048,576 context capacity. These are byte-based upper estimates, not
exact tokenizer measurements. Each actual request, including the future critic's
new draft/notes, is checked against live health capacity before dispatch; nothing
is clipped. Long Chapter 11 outputs use existing natural headings, keeping every
native target block once; overlapping physical pages are context/section boundaries,
not duplicated target blocks.

Bergomi's completed 520-page/65-window OCR, 8,102 blocks, nine intentional blank
notices and 118 explicit native-renderer fallbacks are preserved in the sealed cached
inputs. The first chapter has 319 substantive target blocks. The remaining **132
prepared conversion units** are dormant. Their natural major-section outputs bound
long final answers while retaining full chapter context when it fits; the manageable
first chapter stays whole. These inputs are preserved, not independently certified.
A later authorized linked stage must reuse this stage's successful work.

Saved-output adoption, without inference:

- Lewis is canonical `gatheral-07-s05`, based on **critic-call-037**, with exact
  version hashes and edits in `adoption-record.json`. Its printed J3 inconsistency
  remains visible; no corrected coefficient was invented. The beta2 divergence
  follows locally; beta0 remains undetermined without J2. Lewis (2000) pp.142–144
  and definitions are still needed. A flagged source issue is not failed transcription.
- The existing canonical 7-s01 was retained with a source-image correction removing
  caption-only sigma/nu tildes (PDF120/printed89). Proof tilde-x and the restored
  rho-eta factor remain. Its cross-reference note cites the actual Chapter3 Heston
  derivation (3.19), **PDF66/printed35**. The impossible-self-reference rationale and
  duplicate appendix were removed from the current display, retained in history.
- The canonical 6-s03 control remains byte-identical. Neither pilot control version
  was substituted. New note rendering follows explicit in-document note labels
  instead of appending duplicates; no-change observations are not corrections.

Current editable edition:
`runs/editorial-chapters-trial-20261028T215454Z-8ef98f/editions/gatheral-1793224497328383556/master.tex`.
Standalone TeX/assets, normalized bibliography and before/after logs accompany it.
The three parent gaps remain as twelve precise output notices until recovery.
Front matter/index remain an original-page supplement, with original pagination.
Existing unchanged PDFs retain their recorded compilation evidence. Docker access
was denied in Codex: the two edited documents and new master have **not** compiled
here. The worker uses the existing qualified compiler image
`sha256:b9505ed9122f83fd4bb4ae2ab79a1a7ad82187ca712fda0e8868e4e374296211`;
compiler/environment failures remain separate from accuracy, and successful compilation
is not proof of completeness or mathematical correctness.

Controls work from a fresh shell:

```bash
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh status
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh pause
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh resume
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh bundle
```

Status is read-only and shows admitted tasks. Pause finishes the current response;
resume captures readiness and skips consumed tasks. `stop` interrupts streaming while
preserving partial evidence; uncertain attempts are not replayed automatically.
Bundle when paused/finished; finalization also bundles automatically. After the
Bergomi pair the stage is finished and cannot silently dispatch later chapters.

Log (created at launch):
`runs/editorial-chapters-trial-20261028T215454Z-8ef98f/terminal.log`.
Report: `runs/editorial-chapters-trial-20261028T215454Z-8ef98f/report.html`.
`state.json.editions` records the actual latest edition directories after execution;
`last-inspection.json` records the resulting inspection ZIP. The terminal prints
book, chapter/section, phase, model and output path. Attach with
`tmux attach -t editorial-chapters`; Ctrl-b then d detaches safely.

---

The following pilot and earlier sections are historical, not the current launch plan.


## Current operator path — 28 October 2026: three-case pilot only

**Prepared, not running. No model calls were made during this repair.** Current
linked run: `/home/mdi/projects/pdf-to-latex/runs/editorial-chapters-trial-20261028T072031Z-41483c`. It preserves 30 parent calls and 24 earlier calls, with zero
new calls. The current pointer retains the prior integration receipt; use the
integrated checkout wrapper below, not an older preparation or `/tmp` copy.

Normal-terminal full suite (15 mock socket tests were sandbox-blocked here):

```bash
cd /home/mdi/projects/pdf-to-latex && .venv-control/bin/python -B -m unittest discover -s tests -v
```

Launch the prepared pilot:

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-editorial-chapters.sh run
```

This checks worker/service ownership, requires the existing regular GLM deployment
and exact `glm53-regular` discovery/healthy capacity, and starts persistent tmux
session `editorial-chapters`. **It does not start, stop or replace services.** A
missing/wrong/busy service produces an error. The worker captures fresh readiness
automatically; no path needs pasting. It compiles the linked saved edition with the
qualified isolated environment, then runs this order:

1. Gatheral 6 s03 conversion at **high**, immediately followed by **max** critic
   if a complete draft is returned.
2. Gatheral 7 s01 conversion at **high**, then **max** critic.
3. Gatheral 7 s05 (Lewis) conversion at **high**, then **max** critic.

Stop for inspection after these cases. There are three conversion calls, at most
three critic calls, one attempt each, and at most three readiness calls across
launch/resume. The inherited ceiling/accounting also remains enforced. No
automatic repeated retry, promotion of high, other Gatheral recovery or Bergomi
inference is admitted. The historical Max requests are reused exactly except for
adding `reasoning_effort: high`; comparisons are recorded per case. Critics use
both sources, the newly produced draft and its notes. Sampling stays omitted.
No overall/generation deadline; the distinct connection timeout is 10 seconds.

Preparation exposes `--conversion-effort` and `--critic-effort` (none/low/medium/
high/max), default max/max for ordinary continuation. Launch/resume cannot override
sealed settings. The installed adapter maps medium to high and none disables
thinking. High/max requests and wire serialization are verified offline; the
server's effective runtime prompt is not independently attested by usage fields.

Controls, available from a fresh shell without remembered variables:

```bash
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh status
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh pause
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh resume
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh bundle
```

Status is read-only. Pause finishes the current response; resume captures new
readiness and skips consumed work. `stop` can interrupt streaming while retaining
partial evidence; an interrupted unit is not automatically replayed. Bundle
requires the writer lock, so use it when paused/finished; the worker also bundles
its final state automatically, including exceptions. `tmux attach -t editorial-chapters`
shows the live terminal; Ctrl-b then d detaches without stopping it.

Log: `/home/mdi/projects/pdf-to-latex/runs/editorial-chapters-trial-20261028T072031Z-41483c/terminal.log` (created on launch).
Report: `/home/mdi/projects/pdf-to-latex/runs/editorial-chapters-trial-20261028T072031Z-41483c/report.html`.
Pilot metrics/assessment ledger: `/home/mdi/projects/pdf-to-latex/runs/editorial-chapters-trial-20261028T072031Z-41483c/pilot-comparison.json` and `.md`.
Current prepared inspection ZIP: `/home/mdi/projects/pdf-to-latex/results/editorial-chapters-inspection-20261028T072031Z-41483c-1793172160466305250.zip` (18,791,993 bytes).
Each later snapshot prints its actual path and records it in `last-inspection.json`.

Rebuilt editable edition: `/home/mdi/projects/pdf-to-latex/runs/editorial-chapters-trial-20261028T072031Z-41483c/editions/gatheral-1793172035172466728`; entry point `master.tex`, standalone chapter
TeX/assets, normalized bibliography, accuracy logs and history. Its four gaps are
in source order. Existing selected chapter PDFs carry inherited compilation
records. **The new master has not compiled in this sandbox** (Docker denied).
At launch its real check writes `compile/attempt-*/document.pdf` and logs in a new
edition directory, with `state.json.editions.gatheral` identifying the actual one.
No missing-package error causes a model regeneration; existing bounded compiler
dependency handling remains separate. Compilation is not completeness or accuracy.

Bergomi: OCR is complete (65 windows, 520 owned pages). Every chapter input was
preflighted offline, including 128 non-owned context appearances and both text
sources. All nine notice-bearing intentional blanks retain their recognized text.
There are 118 explicit native-renderer fallbacks, not dropped blocks. The first
chapter conversion/critic pair and later schedule are dormant under
`bergomi/prepared/`; `bergomi/preflight.json` records actual coverage. None can run
under the pilot admission. `continuation-plan.json` and `future-recovery-previews/`
record the four Gatheral gaps and possible coherent long-section outputs. A later
linked admission must reuse any approved pilot repair and preserve consumed calls.

See [the evidence and exact changed-file list](evidence/editorial-recovery-20261028.md)
for blank-page records, current annotation reconciliation, validation and deferred
serving trials. Preserve rollback; no joint-verification or newer TensorFold trial
was implemented. Do not upgrade while generating the books.

---

The dated sections below describe earlier preparations and are retained as history.


This opt-in continuation uses saved MinerU native material plus cached native PDF
text, regular local `glm53-regular`, then an immediate mathematical critic. It
creates an authorized annotated **working edition**, not an accepted or certified
book. No cloud inference or keys are involved.

The controlling editorial policy is in `probe/chapter_editorial.py:POLICY` and is
included verbatim in new critic requests. Well-supported printed errors and OCR
errors both deserve correction. Visible **GLM editorial correction** and **GLM
unresolved issue** notes accompany material findings. Codex's offline edits and
user-supplied ChatGPT publisher checks retain their own attribution. Historical
model explanations remain historical claims, not independent verification.

## Current resume after the desktop-workload repair (27 October, 19:52 UTC)

Integration **already completed**. Bergomi finished all 65 windows / 520 owned
pages with operator exit status 0. The normal-terminal suite ran 518 tests:
514 passed and four optional real-compiler checks skipped. The subsequent launcher failed on
GNOME remote desktop before GLM startup/readiness: the editorial preparation has
zero new calls, not a partially executed model task. The project writer lock was
unheld when inspected; host/peer workloads are checked again at operator launch.

Current preparation:
`runs/editorial-chapters-trial-20261027T195212Z-654e71`.
Its explicit `launch_repair_parent` binding points to unchanged
`runs/editorial-chapters-trial-20261027T080547Z-846061`. All prepared requests,
corrections, document versions, task order and budgets are preserved, including
24 historical calls and zero new calls. The new artifact changes the code binding
and records lineage; the old artifact is not resealed. The narrow offline
`prepare-launch-repair` operation refuses dispatched work, unrelated code changes,
changed evidence or an obsolete current-run pointer. This operation is already
complete; use resume now, not another preparation or copy-back.

From a normal terminal, run this single command:

```bash
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh resume
```

It uses the current integrated code and actual run pointer, checks completed OCR
and workloads, arranges the existing regular GLM deployment if absent, then
starts the queue in tmux `editorial-chapters`. The worker captures fresh text
readiness automatically. Gatheral Chapter 6 recovery/critic pairs run first,
followed by the existing serial queue below; completed conversions are not replayed.
The previously passed full suite is not rerun by resume.

The GPU check exempts only `/usr/libexec/gnome-remote-desktop-daemon` verified via
`/proc/<pid>/exe` **and matching device/inode identity** against that installed
executable on the relevant node. A reported name or PID alone is insufficient.
Unknown/Python workloads and unavailable, replaced or deleted executable identities
remain blockers. MinerU, competing project jobs, deployment and model-identity
checks remain active. Actual `MemAvailable` includes desktop consumption; no
memory is credited back. The existing launcher/TensorFold memory admission remains
unchanged. Read-only observations are saved separately in
`launch-checks/gpu-workloads-*.json` for each new admission attempt.

Progress (read-only):

```bash
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh status
```

Worker log, created when the worker starts:
`runs/editorial-chapters-trial-20261027T195212Z-654e71/terminal.log`.
Report: `runs/editorial-chapters-trial-20261027T195212Z-654e71/report.html`.
Use the same authoritative wrapper with `pause`, `resume` or `bundle` as needed.
The old `/tmp` wrapper also forwards to this checkout because its integration
receipt is retained; it does not overwrite the repair or repeat copy-back checks.

Repair checks: 32 focused tests, 31 passed and one opt-in compiler check skipped;
Python/shell syntax and whitespace checks passed. These mock workload tests do
not establish live Docker, SSH, GPU or model behavior. No inference/service
operations were performed during this repair. The earlier development sandbox's
socket-denied suite is historical and is superseded by the recorded successful
normal-terminal suite above.

## Original isolated integration (completed; historical launch procedure)

The following records the earlier preparation and bootstrap. Integration has now
finished; use the current resume command above.

Development is isolated in `/tmp/pdf-to-latex-editorial-development-20261027` while
Bergomi extracts from `/home/mdi/projects/pdf-to-latex`. Ordinary independent files
were copied from the current dirty tree, without Git metadata, environments,
models, credentials or source books. `development/baseline.json` records original
hashes. Nothing in the extraction checkout may change before successful extraction
and worker exit. Because `/tmp` is temporary, preserve the development directory
and its `development/task2-editorial-*.zip` patch bundle.

From a normal terminal on the Spark:

```bash
bash /tmp/pdf-to-latex-editorial-development-20261027/scripts/run-editorial-continuation.sh run
```

This creates tmux session `editorial-chapters` immediately. Its bootstrap waits
read-only while the owned Bergomi conversion runs. A paused/failed extraction,
nonzero operator exit, incomplete ownership, another job, a destination conflict,
missing dependency, unavailable endpoint or wrong model produces an explicit error.
It never restarts OCR or overwrites conflicting edits. After 65 windows / 520 owned
pages have completed and workers exit, it checks every changed destination against
the baseline, copies only tested changed files and the prepared derivative, and
preserves the patch under project `results/`. It runs the full suite **once** before
inference. It then checks both nodes, starts the existing GLM helper with `ABLIT=0
PREPARE=0 PULL=0 HF_HUB_OFFLINE=1` only if the deployment is absent, and validates the
exact alias and idle workload. It does not stop unrelated deployments, install or
download anything. The worker captures fresh text readiness automatically; no path
pasting is required.

A successful launch prints the actual run/report/log paths. While waiting, the log
is `development/continuation-launch.log` in the development directory. After
integration, inference progress is in the prepared run's `terminal.log`.

Use the same wrapper from any fresh terminal; it automatically forwards to the
integrated project once copied back:

```bash
bash /tmp/pdf-to-latex-editorial-development-20261027/scripts/run-editorial-continuation.sh status
bash /tmp/pdf-to-latex-editorial-development-20261027/scripts/run-editorial-continuation.sh pause
bash /tmp/pdf-to-latex-editorial-development-20261027/scripts/run-editorial-continuation.sh resume
bash /tmp/pdf-to-latex-editorial-development-20261027/scripts/run-editorial-continuation.sh bundle
```

Status reads saved records. Pause lets the current model response finish before
stopping the queue, without stopping GLM. Before integration it stops only the
waiting bootstrap, leaving OCR alone. Resume rechecks evidence and captures fresh
readiness, skipping all reserved/completed requests. Bundle is available when the
writer is idle; the live writer also bundles at book boundaries. For an immediate
request interruption after integration, `bash scripts/run-editorial-chapters.sh
stop` retains the partial stream and leaves its unit unresolved; it does not stop
the model service or automatically replay the unit. Reattach using `tmux attach -t
editorial-chapters`; detach with Ctrl-b then d.

## Prepared work and accounting

Parent: `runs/simple-chapter-glm-trial-20261026T212942Z-533351`. Its 24 calls,
27,920.0166 request seconds, original drafts, notes and failures remain unchanged.
Calls 023/024 are the bibliography. New work has a separately recorded finite call
plan, not the old experimental deadline/count. Historical and new totals are
reported separately and cumulatively inspectable.

The Gatheral schedule is Chapter 6's five coherent sections and immediate critics,
then Chapter 7's six sections and critics, Chapter 11's four sections and critics,
then finite editorial application/annotation requests for Chapters 3, 5 and 10.
Every recovery request supplies full chapter context where it fits. No successful
Gatheral conversion is repeated. If Chapter 6 delivers no usable section, Chapters
7/11 are explicitly deferred; independent editorial work remains eligible. Failed
sections are gaps, not synthesized from reasoning.

Each new unit has **one** attempt, including uncertain/interrupted dispatches;
there are no automatic identical retries. New-work ceilings allow planned calls
plus bounded readiness across resumes (`2 * planned units + 32` total). Adding the
already-authorized Bergomi plan records its extra units/ceiling in a separate seal;
consumed calls are never reset. There is no overall or generation deadline. The
connection-establishment timeout remains 10 seconds. Manual stop/pause, actual
transport failures, repeated connection failures and evidence/identity checks
remain active.

Installed TensorFold patches expose effort levels and thinking on/off. The launcher
`MAX_TOKENS=32768` is a default, not a request ceiling. No reliable independent
reasoning-token quota was established. This preparation requests 131,072 shared
reasoning/output tokens and leaves thinking/sampling controls unset. The saved
server capacity was 1,048,576 tokens; every dispatch checks current health and
capacity. Admission uses complete UTF-8 request bytes + 4,096 template margin +
output allowance, a conservative upper estimate, not an exact tokenizer count.
Sources are never silently clipped. If necessary for Bergomi, a complete coherent
section, exact relevant local references and matching native pages replace full
chapter context, with unavailable/partial references recorded. A still-oversized
request remains a visible gap.

## Documents, notes and compilation

`versions/` retains first GLM drafts, previously reviewed versions and new annotated
versions independently. A findings-only critic retains the successful draft and
is labelled `critic_unchanged`; it is not unreviewed. Chapters 8/9 use this path.
Chapter 9's Markdown-fenced updated accuracy notes are recovered offline.
`accuracy/` preserves raw notes, individual model claims, Codex dispositions and
before/after records. Resolved claims, checked corrections, contextual observations,
cosmetic notes and genuinely open findings are distinct. Unaddressed findings
carry forward; unsupported assertions never become independent verification.

All actual calls retain exact requests, streamed raw bytes, separated returned
reasoning/final text, finish reason, usage and elapsed time through the existing
transport. A truncated response cannot replace a complete document. New annotation
text is visible TeX; raw Markdown remains available when non-TeX Unicode must be
represented by its code point in a pdfLaTeX note.

The already-qualified expanded compiler image is reused:
`sha256:b9505ed9122f83fd4bb4ae2ab79a1a7ad82187ca712fda0e8868e4e374296211`.
Compiler dependency recovery uses the existing bounded allowlist and separate
image provisioning; documents compile with network disabled, non-root identity,
read-only source, no shell escape and unchanged resource limits. Environment
failures are not model math errors. No compiler success is claimed by offline
mock tests. Normal launch compiles new saved versions and editions.

Edition directories contain separately usable TeX/asset files, accuracy logs,
structured bibliography, a coverage inventory and `master.tex`. The master uses
relative `parts/*.tex` with `pdfpages` inclusion of independently compiled chapters
or sections. This deliberately isolates incompatible historical preambles/macros;
it does not rewrite their mathematics. Standalone TeX remains the editable text
source. Uncompiled/missing parts are conspicuous placeholders, not a successful
whole-book claim. Rebuild standalone documents before the master if editing them
on a laptop with LaTeX installed. Compiler output paths are reported in the run.

Gatheral PDF 32–198 is the chapter/postscript/bibliography scope. Original front
matter 1–31, blank 199 and index 200–210 accompany it as a searchable source-page
supplement. Original index locators refer to original pagination. Chapters 6/7/11
remain explicit gaps until actual recovery succeeds. `bibliography/references.json`
is an ordered structured bibliography with 76 stable keys, normalized author lists,
exact original entries, provenance and unknown fields left unspecified. Old
publication versions are retained. Matytsin tildes/URL reachability are unverified.

## Bergomi boundary

The registered source is Lorenzo Bergomi, *Stochastic Volatility Modeling*, CRC
Press, copyright 2016, PDF version 2015-11-05; no numbered edition is inferred.
The source has 520 physical pages and twelve chapters with embedded mathematical
appendices, followed by epilogue/bibliography. Title/copyright/front matter and back
cover are source supplements. The contents mentions an index, but no index pages
are present in the supplied PDF; this cannot be manufactured.

Bergomi preparation refuses incomplete MinerU evidence. After completion, it reuses
`runs/convert-basic-20261027T065138Z-f5d477`, actual source ownership/readers and the
Task 1 native-text cache; there is no OCR rerun. Boundaries come from the recorded
intake, not Gatheral. Each observed major section output is followed immediately by
its critic, with source IDs/page ownership only in sidecars. Cross-boundary context
is distinct from reviewed targets. An isolated failure remains a visible gap while
independent work continues. Real model delivery, complete mathematical fidelity and
new compiler builds remain untested until operator execution.

## Tests

The persistent launch runs the normal-terminal full suite once. To run it personally:

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -B -m unittest discover -s tests -v
```

Optional real annotation/PDF-text regression (existing image, no rebuild):

```bash
PDF2TEX_COMPILER_IMAGE=sha256:b9505ed9122f83fd4bb4ae2ab79a1a7ad82187ca712fda0e8868e4e374296211 \
  .venv-control/bin/python -B -m unittest discover -s tests -p test_chapter_editorial.py -v
```

## Actual offline preparation

Current prepared run: `/tmp/pdf-to-latex-editorial-development-20261027/runs/editorial-chapters-trial-20261027T080547Z-846061`.
Report: `/tmp/pdf-to-latex-editorial-development-20261027/runs/editorial-chapters-trial-20261027T080547Z-846061/report.html`.
Edition: `/tmp/pdf-to-latex-editorial-development-20261027/runs/editorial-chapters-trial-20261027T080547Z-846061/editions/gatheral-1793087992088374297`.
Inspection ZIP: `/tmp/pdf-to-latex-editorial-development-20261027/results/editorial-chapters-inspection-20261027T080547Z-846061-1793088347548811446.zip`.
Patch bundle: `/tmp/pdf-to-latex-editorial-development-20261027/development/task2-editorial-20261027T080855Z.zip`.
This is prepared, not running; copy-back is deferred while extraction remains active.
The preceding zero-call preparations are preserved as linked offline history.
