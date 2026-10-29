# Simple whole-chapter GLM workflow — 26 October 2026

Current preparation: `runs/simple-chapter-glm-trial-20261026T212942Z-533351`.
**Prepared offline, not running.** This is the explicitly authorized fresh Gatheral
experiment, reusing extraction caches from the unlaunched two-source preparation
`runs/simple-chapter-glm-trial-20261026T210920Z-316b1a`. No old GLM drafts, results or
skip list are inherited. All earlier runs and their 11 calls remain unchanged.
The new run starts at zero calls under the existing 80-call ceiling; its binding
records the earlier experiment separately, rather than resetting its history.
The current two-source, meaning-focused contract supersedes older single-source prompts.
The user's no-deadline policy remains in force; older deadlines below are historical.

## One operator command

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-simple-chapter-glm.sh run
```

This discovers the actual prepared path; no path pasting is required. It checks
project writers/workloads, exact `glm53-regular` at
`http://192.168.1.100:8888/v1` and current context capacity, then starts the
persistent `simple-chapter-glm` tmux session. An unavailable/wrong endpoint fails
clearly; it never switches models or starts/stops services. The worker runs the
full controller test suite if this exact code/test version has no passing stamp.
It builds and qualifies the isolated compiler environment described below, captures
one text-only **streamed** readiness call, and starts the scheduled work. Its terminal
log and run directory are printed. Readiness must return the exact nonempty
`CHAPTER_READY` answer, selected model, normal finish and complete SSE stream.
A prepared directory or a started tmux session alone does not establish inference.

Exact order: **Chapter 1 conversion → Chapter 1 critic → Chapter 2 conversion →
Chapter 2 critic**, continuing through **Chapter 11**, then **postscript conversion →
critic → bibliography conversion → critic**. Chapters 3 and 5 have fresh authorized
attempts under the revised two-source workflow; historical failures remain separate.
No Klebaner comparison is included. There is no initial experimental gate. An isolated
failed conversion leaves that part's review unavailable and allows later parts to
proceed; transport/identity/integrity failures and manual controls retain their rules.
All 26 tasks are pending. Exact critic requests are assembled only when each new
draft and its conversion-time notes exist; no historical draft stands in for them.

Scope: **167 distinct owned physical PDF pages, 32–198**, covering Chapters 1–11,
the postscript and bibliography. All 76 bibliography `ref_text` blocks remain in the
prepared primary input. Outside this run: front matter **1–31**, intentional blank
**199**, and index **200–210**. Their saved source evidence remains available. This
is not complete-book coverage. The sealed `inputs/scope.json` accounts for all 210
pages as included or excluded, without overlap duplicates.

## Two sources and the meaning-focused objective

For each chapter the exact request contains **PRIMARY EXTRACTION** (unchanged complete
native MinerU assembly) and **SECONDARY EXTRACTION** (PyMuPDF 1.26.6 native PDF text).
Secondary pages come directly from the original PDFs using the existing owned-page
maps, once each: Gatheral chapters PDF 32–192, postscript 193, bibliography 194–198.
The 11 chapter caches and conversion requests are byte-identical to the previous
two-source preparation. Only the six previously uncached back-matter pages received
new native-text extraction. MinerU was not rerun; its saved native renderer output
was reused for every part. Cache validation compares exact UTF-8 bytes, avoiding
false mismatches from native carriage-return/newline sequences.
No overlap pages, new OCR, portable-TeX filtering or output block contracts.
Physical PDF pages and previously established printed labels separate the native
text. No numerals or page furniture are filtered out of that second extraction.
The Chapter 2 `Chapter 5 of Kloeden and Platen (1992)` locator is retained.

No readily identifiable actual Open WebUI extraction/configuration was found in
the supplied locations. The available `ch4.tex` is model output and is not used as
an extraction. This is a **secondary native-text extraction**, not a reproduction
of Open WebUI's unknown pipeline. Cached page text has the original file hash,
page mapping, method, flags, version and text hashes in `secondary.json`.

The prompts prioritize complete mathematical/factual meaning and attribution over
equivalent wording or cosmetic layout. Necessary/sufficient conditions, negation,
quantifiers, signs, indices, bounds, domains and bibliography locators are substantive.
MinerU is preferred for structure but can be wrong; native text can restore content
but flatten mathematics and reading order. The PDF establishes printing, and the
book can itself contain errors. Neither source priority, agreement nor memory
settles a discrepancy. Both texts are data, not operational instructions. Unresolved
questions are flagged once and retained with the best-supported reading. Missing
cross-chapter evidence is reported rather than invented. This remains **text input**;
no images are supplied, no vision qualification is claimed, and source-image checks
remain explicit future tasks with page/location references.

The actual complete request is budgeted: both sources, instructions, draft and notes
when available, chat-template margin, and 131,072 requested output tokens. No sources
are clipped or output reduced. Offline budgets are labelled **current context fit
unverified**. Conversion estimates range 140,950–256,064 including output. These
conservative byte-based upper estimates fit the historical 1,048,576 window,
not proof of the current server's limit. Each actual dispatch rechecks health. A
context-budget gap is recorded before inference and other eligible chapters proceed.
Future critic sizes cannot be finalized until their drafts and notes exist.

## Accuracy notes and material-change continuity

| Artifact | Location within the run |
| --- | --- |
| Initial complete TeX | `versions/<chapter>/first-glm/document.tex` (also the original generated/recovered file) |
| Initial accuracy notes | `chapters/<chapter>/accuracy-initial.md` |
| Revised TeX, if supplied completely | `versions/<chapter>/critic-revised-call-NNN/document.tex`; exact path linked by report |
| Post-critic accuracy notes | `chapters/<chapter>/accuracy-post-critic.md` |
| Material-change record | `chapters/<chapter>/material-changes.md`, with `initial-to-revised.diff` |
| No complete revision supplied | `chapters/<chapter>/revised-tex-status.md` says so; initial TeX remains current |

JSON alongside Markdown is **program-owned metadata**, not a schema demanded of the
model. Markdown layout is tolerant. A complete single TeX document survives oddly
formatted or unavailable notes. Raw answers and notes are retained. Distinct statuses:
“No material issues reported by the model”, “Accuracy notes unavailable/unparsed”,
and “Review incomplete or failed”. None means mathematical certification. Artifacts
for unexecuted phases do not pretend that a review has occurred.

This fresh run has no retrospective baseline notes: every initial note record will
come from its new conversion. The previous preparation's retrospective notes remain
there and are not sent in the new run. No manual-audit answers enter requests. Clear presentation and
positive bookkeeping notes are retained in a collapsed section outside the actionable
queue. Mixed or unclassified notes remain visible rather than losing material claims.

The program gives entries stable identifiers; the critic is not required to reproduce
IDs or hashes for its answer to be saved. Exact duplicate entries are grouped.
An ignored issue stays open. An explicit ID/exact-heading association links updates;
ambiguous matches remain separate/open. Automatic closure is deliberately narrow:
a claimed extraction/transcription resolution needs a unique exact source quotation,
matching old/new text and the actual revision of that quotation in the document.
A generic “fixed”, a disconnected quotation or an unverified mathematical derivation
cannot close an issue. Such claims/derivations remain visible for assessment, even
when a revised working draft contains the change. This is not a mathematical proof
checker or fuzzy matcher. The full mechanical TeX diff is not called a semantic
change inventory; model-reported material changes are recorded beside it.

If criticism fails or truncates, the initial TeX and notes survive; partial returned
text is retained without completion credit or replacement authority. No extra call
is used to repair a note's presentation. All versions and notes are hash-bound, and
later history is not resealed. Compile each complete version separately: compiler
results cannot certify accuracy or erase useful TeX.

## Timing, settings and evidence

There is **no overall wall-clock deadline and no generation timer**, including on
resume. This separate experiment has **zero calls** and no first-dispatch timestamp
yet. All **11 prior calls** retain their timestamps and evidence in the earlier runs,
with their count/reference recorded in this binding. The existing **80 cumulative
inference-call ceiling within this run**, including readiness, remains. New calls
and uncertain attempts remain consumed across its resumes. Each launch/resume gets one
readiness call, without a separate fixed readiness quota. There are no automatic
identical retries or chapter splits. Two consecutive actual connection failures
stop dispatch; identity/integrity errors stop immediately. Interrupted/uncertain
calls retain their evidence and do not get automatic completion credit or replay.

The TCP/TLS connection-establishment timeout is **10 seconds**. Small discovery and
health reads also have a ten-second request timeout. Once generation is connected,
the socket has no read/generation deadline. A silent connected server can therefore
wait indefinitely until an operator stops the request or the connection fails.
Compilation still has its independent isolation/resource limits; those do not
terminate model generation.

Conversion and critic requests both explicitly request **131,072 output tokens**,
shared by reasoning and final text. Readiness requests 2,048. Short meaning-focused prompts supply complete MinerU material **and** cached native
PDF text. Reviews also receive the exact draft and open conversion-time accuracy notes. No JSON, output markers, assignment lists or new block validation.
Sampling/thinking overrides remain omitted. Only Open WebUI's `max_tokens` is known;
this is not a recreation of its full configuration. No deployment setting changed.

Installed TensorFold documents the launcher `MAX_TOKENS=32768` as an omitted-request
default, not a hard ceiling. Saved call-009 actually consumed the requested 131,072.
The installed implementation bounds explicit output by **remaining effective
context**, not a separately established 131,072 maximum. Saved health and cached
model config report 1,048,576 total tokens; launch and every request recheck live
health. A larger output allowance would require explicit request preparation and
sufficient remaining context, not automatically a service change. No larger value
was tested or selected here. Installed controls include `reasoning_effort` low,
high, max (medium maps to high) and explicit thinking enable/disable. The regular
template defaults to max when thinking is enabled. These installed defaults are
not a measurement of what each historical request actually honoured. See the
[installed-runtime and reasoning assessment](evidence/simple-chapter-continuation-20261026.md).

No tokenizer dependency is needed or installed. Admission uses the **entire UTF-8
JSON request byte count + 4,096 template margin + requested output**, checked against
live context. This is deliberately conservative, not exact tokenization. It can
reject a request that would fit; it never clips text. Actual usage counters remain
separate. A 256 MiB transport ceiling allows SSE framing; it is not a duration or
generation-token limit.

During streaming, `calls/call-NNN/attempts/<attempt>/response.raw` retains the wire
SSE and `reasoning.txt`, `answer.txt`, `stream-events.jsonl` are flushed to disk as
complete deltas arrive. Partial trailing wire bytes remain available even when
there is no complete delta. No partial response becomes a completed draft.
`response.assembled.json` is explicitly a local assembly of server deltas, not a
claim that the server sent that JSON envelope. On return/failure, each call also has
labelled reasoning/answer files, `request.json`, `settings.json`,
`response-metadata.json`, `outcome.json` and a seal. Usage/finish reason can be unknown
on disconnect; totals identify missing counters. `length` remains truncation even
with a partial final answer or substantial reasoning.

Installed server patches support separate reasoning/content deltas, final usage
and finish fields. This session could not connect through its sandbox, so actual
live streaming is **not yet verified**. The single readiness call at operator launch
checks that behaviour before chapter dispatch. No ordinary-JSON fallback silently
loses interruption evidence.

## Separate versions and compiler environment

Raw MinerU source remains `inputs/<chapter>/source.tex`, with native data, page maps and
assets. `secondary.txt` and `secondary.json` preserve native PDF text page by page. `versions/<chapter>/mineru/document.tex` is only a deterministic compilation
wrapper around that unchanged source. `first-glm/document.tex` preserves the first
completed draft. Critic findings remain `chapters/<chapter>/review.md`. If the critic
also supplies one unambiguous complete revised document, it is stored separately as
`versions/<chapter>/critic-revised-call-NNN/document.tex`, UNACCEPTED; it never replaces
the first draft. Findings-only and ambiguous revisions are explicitly recorded.
The critic may supply a complete revised working derivative when it makes material
corrections; otherwise findings suffice. Clear supported source typos can be corrected
and logged without asking for per-edit approval. Ambiguous mathematical changes
stay visible. No old proposal is marked accepted and no earlier version is replaced. Each representable version gets separate compilation records,
logs/PDF when available; compilation does not establish fidelity.

The previous immutable compiler image lacked `enumitem.sty` and `lmodern.sty`.
The operator command builds a **new** image from the project Dockerfile using
`texlive-latex-base`, `texlive-latex-recommended`, `texlive-latex-extra`,
`texlive-fonts-recommended`, `texlive-science`, `texlive-pictures`, `lmodern`, and
`cm-super`. This downloads Debian packages inside a compiler-image build; it does
not install host TeX, alter system Python, rebuild the model image or change GLM.
Only the Dockerfile enters the build context—no chapter, key or model material.
The build log and immutable image ID are retained under `compiler-environments/`.
A real two-pass enumitem/lmodern/relative-include check must qualify that image.

Document compilation remains non-root, network-isolated, no-shell-escape, with
read-only source, separate output, path-checked assets and the existing resource
limits. Environment provisioning is a separate operation. An exact recognized
missing-package diagnostic can trigger **one** allowlisted environment update and
retry of the **unchanged** document/assets, retaining both checks. Unknown/custom
packages, missing assets, already-provisioned package failures and syntax errors
are reported without install loops or model regeneration. No real Docker build or
compilation was possible in this sandbox; the operator launch performs them.

No prior GLM draft or compilation result is inherited into this fresh experiment.
Historical successful builds and missing-dependency failures remain in the old runs.
Each new complete draft and any complete revision receive separate compiler checks.
Raw MinerU compilation may fail on native extraction syntax; that does not discard
the extraction or a normally completed GLM draft.

## Status, manual pause/stop and resume

Use these commands separately, from the project directory; each discovers the same
run and requires no variables from earlier sessions:

```bash
bash scripts/run-simple-chapter-glm.sh status
bash scripts/run-simple-chapter-glm.sh pause
bash scripts/run-simple-chapter-glm.sh stop
bash scripts/run-simple-chapter-glm.sh resume
bash scripts/run-simple-chapter-glm.sh bundle
```

`status` is read-only. `pause` finishes the current request, then stops dispatch;
without a generation deadline that wait can be long. `stop` interrupts the current
stream, retains its partial evidence, and stops the controller without stopping GLM.
Once the worker exits, `resume` clears the operator stop/pause flags, verifies seals,
rechecks readiness and skips finished/failed/uncertain attempts. It does not
regenerate failed chapters. `bundle` creates a new inspection ZIP after the writer
exits. The controller also bundles on controlled stop/completion. Do not edit bound
code during execution. Attach with `tmux attach -t simple-chapter-glm`; Ctrl-B then D
detaches without stopping work.

Actual report: `runs/simple-chapter-glm-trial-20261026T212942Z-533351/report.html`.
Preparation checks: that run's `offline-validation.json`. The related offline suite
ran 109 tests: 108 passed, one opt-in real-compiler skip. Live generation, current
context capacity and real compiler execution are untested here. The wrapper runs
the full normal-terminal suite before dispatch. The original cache manifest was
checked unchanged after preparation. No historical calls are relabelled as new ones.

The separately requested small reasoning export is
`results/gatheral03-call009-reasoning-20261026T190941Z-22d35f.zip` (274,390 bytes).
It contains complete verbatim reasoning, separate partial final text, exact requests,
raw response, usage/timings, provenance and line-numbered quoted analysis. It shows
substantive mathematical work mixed with repeated deliberation and LaTeX redrafting;
it does not establish the cause or prove a fixed decoding loop.

This run prepares thirteen experimental conversion/critic pairs: eleven chapters,
postscript and bibliography. It does not claim whole-book completion, image review
or mathematical acceptance. Front matter, blank 199 and index remain outside its
model-call scope. Generation/compilation success is not mathematical certification.

## Historical records below — superseded timing and compiler instructions

The following dated evidence is preserved for continuity. Its 45-minute/eight-hour
limits, 32,768 review allowance and old compiler-image instructions **do not apply**
to the current linked preparation above.

## Recovery artifacts and compilation — 26 October, 15:14 UTC

- Current run/report: `runs/simple-chapter-glm-trial-20261026T151403Z-61cbdb/report.html`.
- Exact recovered TeX: `runs/simple-chapter-glm-trial-20261026T151403Z-61cbdb/recovery/call-006/generated.tex`.
- Same recovery folder: `answer.raw.txt`, `introductory-prose.txt`,
  `conversion-notes.md`, `extraction.json`, `provenance.json`.
- Checks and compiler diagnosis: the run's `recovery-validation.json`,
  `compiler-classification-review.json` and `offline-focused-tests.log`.
- Inspection ZIP: `results/simple-chapter-glm-inspection-20261026T151403Z-61cbdb-1793027667837803110.zip`.
- Parent evidence: `runs/simple-chapter-glm-trial-20261026T111637Z-634ede`, unchanged.

Call-005 reports `length`, 131,072 completion tokens, 113,090 reasoning tokens,
45,043 final-answer characters and 1,935.10 seconds. Its partial final answer is
retained at the parent call's `final-channel.raw.txt`; it is not a completed draft.
Call-006 reports `stop`, 102,571 completion tokens, 91,667 reasoning tokens,
34,592 final-answer characters and 1,662.05 seconds. Subtracting reasoning gives
17,982/10,904 non-reasoning tokens respectively, not separately measured text-token
counts. Mechanical recovery checks find all 12 tags and three supplied image paths;
this is not a fidelity audit.

The recovery leaves GLM's mathematical edits untouched. Its notes disclose three
claimed mathematical repairs as well as reconstructed footnotes; those claims are
unverified and unaccepted. The separate chapter review remains pending.

The user's ChatGPT inspection reported an 11-page two-pass build. Codex did not
reproduce it: the sandbox denied access to `/var/run/docker.sock` before TeX ran.
That Docker CLI returned 1, exposing an adapter classification gap now corrected:
explicit Docker-access denial is `unavailable`, not bad document TeX. The first
offline preparation `runs/simple-chapter-glm-trial-20261026T151139Z-64ef50` and its
original failed check remain unchanged. The final preparation copies that check
under `inherited/sandbox-compiler-check` and records the classification review
separately; Docker was not retried here. Its old `result.json` intentionally retains
the originally recorded classification. Current task status and
`compiler-classification-review.json` explain the correction.

The launch command attempts two compiler passes in the same disposable build tree,
with shared 90-second compiler time and separate per-pass logs/auxiliary evidence.
The adapter default remains one pass for other callers. Isolation, image, mounts,
asset allowlist and resource limits are unchanged. Failed/unavailable compilation
does not discard the TeX or schedule model repair. A normal-terminal recovery check
uses a new compilation directory, preserving the sandbox failure.

Final focused checks: 49 tests, 46 passed and three optional real-compiler skips.
Related chapter/recovery tests: 84 tests, 81 passed and the same three skips; affected
compiler checks were rerun after the denial-classification fix. No socket restriction
affected these focused checks. Syntax and whitespace checks passed. All parent files
and every copied chapter input/request/asset were compared unchanged. Full normal
terminal tests run automatically before continuation; live continuation and real
compilation remain untested by this session.

## Earlier allowance preparation — retained history

The installed launcher at `/home/mdi/local-llm/glm53-flash-tensorfold` documents
`MAX_TOKENS=32768` as the default for requests that omit a limit, explicitly stating
that a request's own value wins (`scripts/config.sh:132–135`). `start.sh:60` passes
that setting as `--max-tokens`. The installed context-error and stream-admission
patches distinguish explicit prompt-plus-output context refusal from clamping an
omitted default; the GLM engine patch forwards `max_tokens` to its scheduler. No
service change is indicated for a 131,072 request on this deployment.

Direct inspection of the running container was denied by this session's Docker
socket sandbox. The audit therefore establishes the installed recipe/documented
implementation behavior, not live proof that this particular container has honoured
a 131,072 request. No permission or service changes were attempted. Saved `/health`
evidence reports 1,048,576 context tokens. The new conservative admission estimates
are 237,912 for Klebaner and 171,793 for Gatheral 1, both comfortably within that
window; live admission rechecks the actual window. Existing prompt counts plus the
new allowance are 169,108 and 142,356 respectively (exact for those saved prompts,
not a promise of future cache/template identity).

The old responses took 542.5s and 629.3s. Linear end-to-end extrapolation to four
times the token ceiling is 36.2 and 42.0 minutes; using separately reported prefill
and decode timings gives 35.0 and 41.6 minutes. These estimates leave limited margin
within 45 minutes, especially if longer-context decoding slows. A full allowance
requires roughly 48.6 generated tokens/s before accounting for prefill. Requests may
still time out; the timeout is not increased. Twelve conversions each consuming the
full ceiling could take roughly 7.2–8.4 hours before reviews, exceeding the remaining
cumulative budget. Automatic continuation therefore remains budget-bound and may
leave explicit gaps. Earlier normal completion would use less time; neither success
nor whole-book completion is promised.

`summary.json` now includes each call's requested allowance, finish reason, elapsed
time, reported prompt/completion/reasoning tokens, final/reasoning character lengths,
and server timings when returned. Completion minus reasoning is labelled a derived
non-reasoning count, which can include delimiters; an exact final-text token count
is left unknown unless reported. A `length` result below its requested ceiling is
flagged for investigation, without retry. HTTP success or a short normal answer
alone never establishes that the maximum was exercised or honoured.

- Earlier corrected linked trial: `runs/simple-chapter-glm-trial-20261026T111637Z-634ede`
- Report: that directory's `report.html`; summary: `summary.json`.
- Inputs: `inputs/<chapter>/source.tex`, `native.json`, `provenance.json`,
  `conversion-request.json`, `budget.json`, `assets.json`; one shared `inputs/assets/`.
- Allowance/context/speed/input checks: `allowance-validation.json`; full tests: `offline-full-tests.log`.
- Offline inspection ZIP:
  `results/simple-chapter-glm-inspection-20261026T111637Z-634ede-1793013459734206189.zip`.
- Its completed calls remain under that trial's `calls/`; generated files,
  observations, reviews and compilation evidence under `chapters/<chapter>/`.

The operator completed the initial two-chapter attempts in
`runs/simple-chapter-glm-trial-20261026T101639Z-ac3566`: both exhausted 32,768 tokens
in reasoning, with no final content. The corrected run copies its sealed inputs;
every source/native/provenance/asset file is unchanged and all twelve conversion
request bodies differ only in `max_tokens`. `allowance-change.json` links the parent,
records exact input hashes and describes the change. Parent calls are inherited for
accounting, not presented as calls made under corrected code. Failed earlier
responses remain at their original paths. The earlier zero-call
`simple-chapter-glm-trial-20261026T101116Z-619b13` also remains untouched.

Earlier 32,768 preparation validation: 19 focused regressions passed. Its full suite was run once:
427 tests, 409 passed, 15 sandbox-denied mock socket errors, three opt-in real-compiler
skips. A final empty-fence guard was then checked with all 19 focused tests. The
launcher runs the full final-version suite in the normal terminal before dispatch.
Bash/Python syntax, whitespace and ZIP integrity checks passed. These checks do not
establish live model quality or real TeX compilation.

Corrected 131,072 preparation: 24 focused tests passed. Final full suite: **433 tests
in 198.083s, 415 passed, 15 sandbox-denied mock socket errors, three optional real
compiler skips**. No application failure was observed. Serialization tests check
the actual LocalClient payload, unchanged legacy purpose limits, separate review
allowance, context reservation, linked evidence/accounting and missing usage counters.
The launch command runs the full suite in the normal terminal before inference.

The existing isolated compiler uses the already qualified immutable image
`sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45`.
It receives the generated complete file and only the explicitly allowed saved
assets. Existing network isolation, no shell escape, read-only source mount,
non-root execution and resource limits are unchanged. No host TeX fallback or image
pull/build occurs. Missing packages/assets, syntax/encoding failures and compiler
configuration failures are distinct. Every generated file survives failed compilation;
no model repair is scheduled. An unavailable compiler disables repeated compiler
attempts but not generation/review. No real compilation has been performed by Codex.

For laptop compilation, copy a chapter's `generated.tex` into a directory alongside
the supplied `assets/` folder, then run `pdflatex -no-shell-escape generated.tex` in
that directory if your laptop has the required TeX packages. Generated syntax may
need inspection. Compilation is not evidence of mathematical correctness.


## 27 October 2026 — annotated editorial continuation

The new opt-in [annotated-chapter runbook](EDITORIAL-CHAPTERS.md) supersedes older
instructions to preserve a well-supported printed mathematical error merely as an
unapplied caveat. Both extractions remain fallible evidence; local mathematical
consistency and inspected source images support attributed corrections. New critics
apply supported changes and include visible GLM correction/unresolved notes.
Original first drafts, reviewed drafts, raw notes, responses and call history stay
unchanged. Findings-only reviews retain their complete first drafts. Chapter 9's
fenced notes are recoverable without inference. Compilation and semantic assessment
remain distinct. The continuation has finite new section work and no arbitrary
overall/generation deadline; it does not restart successful Gatheral conversions.

Development for this task is isolated while Bergomi OCR runs. Do not use the new
code in the extraction checkout until the completion/worker/conflict guards pass.
