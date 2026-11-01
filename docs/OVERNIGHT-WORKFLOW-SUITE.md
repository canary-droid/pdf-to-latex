# Overnight workflow suite — 29 October 2026

**1 November 2026:** the ordinary suite finished with 46 calls (44 work, two
readiness). The active task is [finite book completion](BOOK-COMPLETION.md),
which reuses saved outputs and prepares genuinely missing source spans. Do not
resume or repeat this finished experiment. The seven-call/38-pending guidance
below is historical; automatic supervision remains a separate unqualified path.

**Current instruction, 30 October:** the ordinary repaired experiment may continue
independently of supervisor qualification. Its actual pointer, current code/input
bindings and seven settled calls were verified; Stage A is complete and38 B/C/D
requests remain pending. Use the ordinary launcher:

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-overnight-suite.sh resume --run runs/overnight-suite-20261030T085252Z-fae4ce
```

It retains normal tests/runtime checks and fresh readiness, skips completed work,
and stops after the frozen suite. It does not invoke Codex, bubblewrap or supervisor
qualification. Automatic supervision stays disabled; its unresolved bootstrap
denial is **not a prerequisite** for this ordinary run. See
[the independent verification and diagnostic handover](evidence/supervisor-bootstrap-denial-20261030.md).
Earlier supervisor-dependent launch guidance below is historical and superseded
by this explicit separation.

**Earlier 30 October boundary-hardening update (historical):** automatic promotion and all
supervisor activation/resume paths are disabled pending review. Use only the
[qualification-only command](OVERNIGHT-SUPERVISION.md). It cannot dispatch GLM or
resume a queue. Prior launch instructions below are historical; seven saved
calls and 38 pending requests remain preserved. The hardening task has not armed
supervision or consumed any additional GLM request.

**Earlier 30 October supervision update (historical):** Phase 1 runtime settings and the previous
repair have now been independently checked. The narrow supervisor is implemented
and offline tested, but real Codex-exec qualification is blocked by this sandbox's
read-only app-server state. It is **not qualified, armed or running**. The seven
saved calls and 38 pending B/C/D tasks remain unchanged. Use the persistent
[supervisor entry point and controls](OVERNIGHT-SUPERVISION.md); it completes
normal-terminal qualification before admitting work. Do not repeat the Phase 1
installation or start the bare worker to bypass qualification.

**Earlier 30 October configuration handoff (historical):** the user's next action
is now the [fresh Codex handoff](CODEX-SUPERVISION-HANDOVER-20261030.md), before
launching this worker. Phase1 setup is prepared; the larger context is not active
and automatic supervision is not yet implemented, qualified or armed. The single
normal-terminal command is:

```bash
cd /home/mdi/projects/pdf-to-latex && .venv-control/bin/python scripts/start-codex-supervision-task.py
```

It checks/updates the standalone stable CLI, backs up and applies the explicitly
selected project profile, retains ChatGPT authentication, and opens a fresh local
Codex session with the remaining task already supplied. It uses `--no-daemon`,
leaving shared sessions alone. It does not launch GLM work or change sandbox rules.
The fresh session must verify its actual runtime settings, independently recheck
the prior repair, then implement and qualify supervision before arming it. The
existing repaired suite/preparation below is preserved; rediscover its state if
the operator has launched it in the meantime. The existing worker commands below
remain valid controls, not evidence that supervision has been installed.

**30 October repair: PREPARED, NOT RUNNING.** Same frozen experiment, linked continuation:
`runs/overnight-suite-20261030T085252Z-fae4ce`.
The stopped parent `runs/overnight-suite-20261029T233239Z-708fe8` is unchanged.
All seven calls are inherited: readiness plus six completed Stage A responses.
Five replacements compiled; the sixth was a findings-only review whose local
finalization failed. Its existing notes/annotation have now been verified and
recovered separately. Stage A will **not** run again. Only B/C/D's 38 frozen work
requests remain (4/8/26), plus fresh readiness per genuine launch.
Ordinary Bergomi production remains paused. No production task is adopted, reset
or dispatched by this launcher.

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-overnight-suite.sh run
```

This runs the required full tests once for the final code/test identity, checks
writer ownership and the existing regular GLM deployment on both nodes without
switching services, then starts tmux `pdf-overnight-suite`. Inside that session it
checks exact model/runtime/template identity, current memory and context/cache
capacity, tests installed Low/High/Max template rendering read-only, compiles the
recovered findings-only annotation if still uncompiled, captures one text-only
readiness automatically, and continues B/C/D. The five successful replacement
compilations and three successful offline-repair compilations are retained, not
repeated. No readiness variables or between-stage prompts.
A failed service/integrity/workload check gives an error and leaves services alone.

Use in any fresh normal terminal:

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-overnight-suite.sh status
bash scripts/run-overnight-suite.sh pause
bash scripts/run-overnight-suite.sh resume
bash scripts/run-overnight-suite.sh bundle
```

`status` is read-only. `pause` stops admission and drains inference plus document
finalization; paused is published only after lock release. `resume` skips all
completed/failed work and obtains fresh readiness once; uncertain reservations
cannot silently replay. `bundle` requires the writer lock to be free. `stop` is
also supported to preserve partial streams without stopping GLM. A terminal suite
run/resume performs zero requests, including readiness. Attach with
`tmux attach -t pdf-overnight-suite`; detach with Ctrl-B then D.

Log: `runs/overnight-suite-20261030T085252Z-fae4ce/terminal.log` after launch.
Report: same run's `report.html` / `report.md`. Final/partial ZIP: path in
`last-inspection.json`. The operator writes and refreshes the small uploadable file
`/home/mdi/Downloads/overnight-suite-20261030T085252Z-fae4ce-progress.json`.
It records stage/active targets, counts, activity, last error, status and actual
log/report/ZIP paths. If Downloads is unwritable it prints a diagnostic and keeps
`progress.json` in the run. Full raw responses/reasoning/wire files stay local;
compact bundles contain their evidence index and selected excerpts.

### What was repaired, and what remains a live check

Call-005 returned normal findings, not replacement TeX. The document extractor
can return non-None prose; the old finalizer later used that weaker condition to
compile a nonexistent `critic-call-005` version. Creation and compilation now share
the same recorded-replacement condition. Retained/annotated drafts compile under
their actual names. Partial or ambiguous revisions remain unusable; no suggested
patch is silently applied. The parent still records `coordinator_failure`; the
new `local-recovery/call-005.json` records verified local recovery with zero model
calls. This does not validate the critic's mathematical claims.

The separate Low probe error came from `inspect.getfile` on Transformers'
`_lru_cache_wrapper`. Source inspection now unwraps the helper; rendering still
uses the installed cached callable. Actual mapping/template hashes and High/Max
labels remain checked. A probe error still skips only B with its diagnostic;
changed identity stops dispatch. The sandbox denied the Docker socket, so the
normal launcher must verify the installed renderer and compile the recovered
annotation. No model/service calls occurred during repair preparation.

Future finalization exceptions retain a full traceback in `diagnostics/`, with
the short cause and path in task/state/progress records and terminal output.
Bundling refreshes `progress.json` to the newly created ZIP, including the copy
inside that ZIP. `continuation-lineage.json` records the changed implementation;
inherited calls retain their historical bindings, raw evidence and counts.
Do not reseal the parent or rerun preparation: the current pointer already names
the repaired continuation. Launch/resume the command above. A terminal run/resume
still performs zero requests and never falls through to production.

## Frozen workload: 44 work requests maximum

Every range below is physical PDF pages. Shared boundary pages are context/shared
pages, not duplicate target blocks. `suite-manifest.json`, `selection.json` and
`inventories/` record every original block, heading, equation/reference locator,
asset and old-to-new task map. There are **4,314 distinct new target blocks** across
Stages C/D. Source ownership/inventories are not a fidelity assessment.

|Stage / target|Physical pages|Work / comparison|
|---|---|---|
|A Bergomi4-s03|157–167|1 High critic; exact input of Max009, which exhausted its output; conversion002 reused|
|A Bergomi5-s01|168–169|1 High critic; exact Max007 input|
|A Bergomi6-s06|223–230|1 High critic; exact Max008 input|
|A complete Klebaner4, dual-source|106–136|1 High critic; exact Max019 input, no repeat conversion|
|A Bergomi3-s01|120–136|1 High critic; exact production Max102 input|
|A Bergomi3-s02|136–147|1 High critic; exact production Max105 input|
|B Bergomi4-s01|150–152|Low conversion + its own Max critic; frozen skipped request, High110/Max112 controls|
|B Bergomi4-s02|152–156|Low conversion + its own Max critic; frozen skipped request, High111/Max113 controls|
|C digest5.1–5.5 (s10–s14)|212–214|High conversion + Max critic|
|C digest7.1,7.3,7.4 (s09–s11)|317–318|High conversion + Max critic|
|C digest8.2–8.5 (s11–s14)|368–370|High conversion + Max critic|
|C digest9.1–9.5 (s12–s16)|403–404|High conversion + Max critic|
|D1 variance swaps5.2–5.8|170–193|High conversion + Max critic|
|D2 weighted variance swaps5.9|193–212|High conversion + Max critic|
|D3 forward-variance models7.1–7.5|234–252|High conversion + Max critic|
|D4 options on realized variance7.6|252–278|High conversion + Max critic|
|D5 VIX7.7|278–295|High conversion + Max critic|
|D6 discrete forward variances7.8|295–317|High conversion + Max critic|
|D7 smile expansions8.1–8.7|324–349|High conversion + Max critic|
|D8 forward smiles / vol-of-vol8.8–8.10|350–368|High conversion + Max critic|
|D9 ATMF skew / SSR9.1–9.11|374–403|High conversion + Max critic|
|D10 equity return distribution10.1–10.3|408–435|High conversion + Max critic|
|D11 multi-asset volatility11.1–11.5|438–466|High conversion + Max critic|
|D12 local-stochastic volatility12.1–12.4, including SSR|470–495|High conversion + Max critic|
|D13 numerical examples/discussion/conclusion12.5–12.7|495–510|High conversion + Max critic|

Totals: A6 + B4 + C8 + D26 = **44 work requests**, plus separately recorded
readiness once per genuine launch/resume. One attempt per frozen ID; no quotas
refilled, no adaptive splitting, no repeated identical failure, no production
fall-through. A failed conversion skips only its own critic. Shared service,
identity, integrity, ownership or resource failures drain and stop admission.
The first two D units produce a nonblocking `early-diagnostic.json`; they do not
require approval or prove accuracy. All units were selected before inference.

The common reference is **up to two requests**, with eligible critics prioritised.
There is no four-slot arm. A large pair serializes under the unchanged 90% shared
pool reservation / minimum-memory policy. If only one slot is available, record a
common serial reference. The observed deployment has4 slots, context1,048,576 and
pool2,015,232; fresh checks are mandatory. Runtime/image/template identity must
match the recorded installed build; neither tag nor HTTP success is sufficient.

Conversion High / criticism Max remain explicit except A's High critics and B's
Low conversions. All have131,072 combined reasoning/final output tokens, durable
streaming, no sampling override, no overall or generation deadline, and a separate
10-second connection-establishment timeout. Low is never `none`/no-thinking.
A probe_error skips only B, with diagnostic; it is not evidence Low is unsupported.
The fixed renderer now obtains Jinja environment options/extensions from installed
serving code (including loopcontrols when configured), or its verified delegated
Transformers helper. Ambiguous/unavailable configuration remains a probe_error.
Requested/rendered effort is recorded separately from unobservable model behavior.

A exact requests differ only in effort. B preserves the skipped Low bodies and
builds each critic from its own actual Low draft. C retains production prompts and
full dual-source parent context; only adjacent complete targets are grouped. D uses
the short successful chapter prompt with complete target text plus full parent
MinerU/native context and existing local references. Native boundary-page extras
are context, not extra output. D is a workflow comparison, not a single-variable
speed experiment. No prior critic findings or offline answers are added.

## Capacity, time and validation

All25 concrete requests fit the recorded context using full UTF-8 JSON bytes plus
4,096 chat-template margin plus131,072 output: bounds254,478–888,223. No tokenizer
was installed; these are conservative admission estimates, not exact token counts.
The19 future-draft critics are bound to their own conversion, source/template and
settings, then checked with the exact document before dispatch. Oversized complete
requests become explicit gaps; nothing is clipped or silently reduced.

Measured source-size controls give a central two-slot planning estimate near10h,
before additional compiler/admission overhead, and a deliberately broad6.4–29.5h
range. Either faster or slower completion is acceptable. This is NOT a deadline.
Reports update remaining ranges within each stage, using at least two observations
before adjustment; tiny recaps are not used to extrapolate long-chapter timing.
Overlapping request durations are never called batch wall time. Reasoning tokens,
other completion tokens, server prefill/decode when returned, finalization/compiler
overhead and actual overlap are separate. Unknown counters stay unknown.

Offline tests and final results are recorded in PROJECT-STATE and the linked run's
`repair-validation.json`; its copied `offline-validation.json` is historical.
The operator's pre-repair full suite passed 617 tests (four optional checks skipped).
The three saved offline repairs and five model replacements have actual passing
compiler records. Docker remains denied in Codex; the recovered findings-only
annotation's compilation and corrected installed Low probe remain operator checks.
No service, inference, credentials or paid calls
were used in development. The finished suite/paused production pointers are intact;
new code invalidates their execution bindings, so a later production resumption
needs its usual explicit linked preparation, never resealing old evidence.

## Independent checks and separate repairs

The historical run remains unchanged. `historical-report/version-specific-results.json`
corrects its reporting in this derivative: each row points only to versions generated
by that call. In particular Max009 has no critic TeX/compilation, despite its compiled
conversion. The failed conversion compilation for6-s06 and recap conversions is not
replaced by their later successful critic compilation. Findings-only Max019 did not
apply its suggested patch. Annotation copies and suggested edits are distinguished.

Three linked repairs live in `offline-repairs/`, outside comparison inputs:
Bergomi4-s02 tag4.14 moved outside aligned; Bergomi4-s01 volga note divided by sigma
(both historical Max and High were wrong); Lewis beta0 claim qualified because J2
is unspecified. Main missing-square repair and open source issues remain visible.
Each has original.tex, document.tex, change.diff, attribution and separate compiler
record. No arbitrary critic prose is spliced into a document. See
[the bounded source assessment](evidence/overnight-source-checks-20261029.md).

Source-image checks confirmed Klebaner Theorem4.14's2delta bound and the printed
but incorrect Var(Z²)=3 in Example4.24. Dual017/Max019 retain3; native018/Max020
correct it to2. Normal responses and compilation therefore cannot decide accuracy.
These known answers stay outside A's exact historical input. Future overnight
outputs get omission diagnostics and source crops for later independent inspection;
that inspection has not happened yet. No output is automatically accepted/adopted.

## Retained roadmap

|Direction|Status / evidence|Next action and acceptance condition|
|---|---|---|
|Four-slot matched comparison|Earlier operational suite complete; no new four-slot arm here|Only if needed later: same-input comparison with useful output, integrity and resource safety; reasoning throughput is insufficient|
|High criticism|Three earlier cases completed; six exact-input High reviews prepared in A|Check supported findings, misses and introduced errors against sources, not Max as truth; no automatic promotion|
|Coherent grouping / larger units|Two earlier grouped pairs complete; four new recap groups and thirteen larger units prepared|Check every target once, conditions/assets/references, useful delivery and failures; unmatched new units give no causal speedup|
|Low conversion|Earlier stage skipped because probe renderer lacked extensions; read-only probe repaired, B prepared|Verify real mapping/rendered labels, then source-check Low draft/Max revision; no no-thinking substitution|
|Edit-only critic / deterministic extraction plus correction|Deferred, not implemented or scheduled|Separate source/draft identity and paragraph-preserving application tests; separate fidelity experiment for deterministic output|
|Pinned TensorFold/GLM updates|Deferred; current runtime and weights preserved|Separate image/checkout, rollback, matched settings and real mathematics; no upgrade in this suite|

The native-only/simple Klebaner comparison remains completed evidence. The larger
simple dual-source route is now D; no repeat whole-chapter conversion is added to A.
