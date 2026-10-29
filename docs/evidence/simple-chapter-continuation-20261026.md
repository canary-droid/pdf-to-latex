# Simple chapter continuation and reasoning audit — 26 October 2026

Codex offline assessment. No new inference, service operation, compiler build or
package installation. All original responses and failed attempts are preserved.

Parent: `runs/simple-chapter-glm-trial-20261026T151403Z-61cbdb`.
New preparation: `runs/simple-chapter-glm-trial-20261026T192951Z-3efb02`.
**Prepared, not running.** Parent file manifest verified unchanged. The new run
retains all eleven consumed calls and their originating code/evidence links.

| Saved attempt | Finish | Prompt tokens | Completion / reasoning tokens | Final characters | Elapsed seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| Gatheral 1, call-006 | stop | 11,284 | 102,571 / 91,667 | 34,592 | 1,662.049 |
| Gatheral 2, call-008 | stop | 8,032 | 69,491 / 62,197 | 22,738 | 1,224.946 |
| Gatheral 3, call-009 | length | 13,435 | 131,072 / 125,976 | 16,364 | 2,221.456 |
| Gatheral 4, call-010 | stop | 2,848 | 31,266 / 28,072 | 11,616 | 461.009 |
| Gatheral 5, call-011 | no response | unavailable | unavailable | unavailable | 463.581 |

Call-011 records `Remote end closed connection without response`. Its proximity to
the old run deadline is not proof of the cause. Call-009 is actual token-limit
truncation, not merely a generic content error. Non-reasoning completion counts
obtained by subtraction are not independently measured final-text token counts.

Gatheral 1 has a saved successful real two-pass build. Chapters 2/4 have
`missing_package_or_asset` results with explicit `enumitem.sty`/`lmodern.sty`
diagnostics. These are environment dependencies, not demonstrated TeX syntax
failures. This session did not independently compile any document.

## Chapter 3 reasoning export

`results/gatheral03-call009-reasoning-20261026T190941Z-22d35f.zip`, 274,390 bytes.
Expanded directory: `runs/gatheral03-call009-reasoning-20261026T190941Z-22d35f`.
The archive includes complete UTF-8 `reasoning.txt`, separate partial final answer,
exact request and transport request, original raw response, usage/timings/finish,
hash provenance, and `analysis.md`. Reasoning equals the decoded server field
verbatim, with no extra newline. Line numbers are in the analysis, not inserted
into the reasoning. ZIP integrity and equality to the saved field were checked.

Observed examples (1-based reasoning lines): 517–535 reduce a double integral and
check powers of T; 1349 says “I keep flip-flopping” before declaring a decision
“LOCKED”; 3571–3581 draft a LaTeX preamble; 3867 announces “Now — FINAL” before more
label alternatives; 4112 announces “FINAL FILE” inside reasoning; 5292 says “LOCKED
FOREVER” before further checks. One lengthy caption declaration appears six times.
The complete quoted examples and repeated-line locations are in the ZIP.

This is substantive mathematical work mixed with repeated reconsideration and
redrafting. The mathematical deductions were not independently validated. Repeated
TeX alone does not prove a fixed token-cycle decoding loop. Effective effort,
sampling and ambiguous OCR are possible influences, not established causes. No
retry, lower effort or automatic comparison experiment was launched.

## Installed TensorFold evidence and limits

Read-only root: `/home/mdi/local-llm/glm53-flash-tensorfold`.
Exact inspected file hashes are recorded in the new run's
`installed-runtime-inspection.json`.

- `scripts/config.sh:122–135` and `start.sh:60`: regular thinking is enabled by
  default; `MAX_TOKENS=32768` is an omitted-request default, not an explicit-request
  ceiling. Requests override it; reasoning and final answer share the allowance.
- `patches/0044-cuda-context-errors.patch` and installed README API notes: an
  explicit prompt plus output budget must fit the effective context; otherwise
  the server refuses it. No separate fixed 131,072 ceiling was found. Call-009's
  actual reported usage confirms that request exercised 131,072. Larger values
  were not tested; their admission depends on remaining context and memory/runtime.
- Saved health and cached regular `config.json` report **1,048,576** context
  tokens. Cached snapshot `76c0b5173166d2795dd48860f45d8224817f894c` also contains the
  inspected `chat_template.jinja` and `generation_config.json`. These files do not
  independently identify the running container image.
- README “Thinking and sampling”, `patches/0023-server-effort-max.patch`, and
  `patches/0057-server-thinking-alias.patch`: supported controls include top-level
  `reasoning_effort` low/high/max, medium→high, xhigh→max, none→thinking disabled;
  explicit `chat_template_kwargs.enable_thinking` is supported. The regular cached
  template defaults to max when thinking is enabled. Temperature 1/top-p .95 are
  documented defaults. No sampling/thinking override was added. Actual effective
  settings on each old request are not independently confirmed by usage counters.
- `patches/0061-server-smooth-stream.patch` and
  `patches/0084-anthropic-messages.patch:613–615`: OpenAI SSE uses separate
  reasoning/content deltas and final finish/usage fields. The new client preserves
  each wire chunk and flushes complete deltas to disk; unexpected identity,
  malformed/incomplete streams and token exhaustion cannot receive completion
  credit. No speculative `stream_options` or reasoning-budget field is sent.
  An Anthropic translation mentioning `thinking_budget` is not treated as proof
  of a separately qualified OpenAI GLM reasoning-token cap.

The sandbox denied Docker API inspection and local HTTP discovery. No permission
change or repeated probe was attempted. Live SSE compliance and current container
configuration remain operator checks. The launch captures one streamed readiness
and refuses chapter dispatch if identity, nonempty final text, finish or stream
completion fail. It never changes a model service.

## New policy, preparation and checks

The user explicitly removed overall and generation time cutoffs. New sealed
policy `manual_only` leaves historical time/calls intact but ignores elapsed age
for admission. TCP/TLS establishment remains bounded to ten seconds. Manual pause
finishes the request; manual stop closes the active connection, retaining partial
evidence. The 80-call cumulative ceiling remains; no identical automatic retries.
Other workflows retain their historical timeout semantics.

Both conversion and critic now request 131,072 tokens. Conversion messages and
source are exact copies; only `stream` changes in their prepared bodies. The first
three reviews contain the exact extraction and corresponding completed draft.
669 source/provenance/asset files and all three completed drafts match their parent
bytes. Conservative byte/template/output budgets fit saved context; current health
is rechecked for each request. No tokenizer was installed and no input clipped.

New order: reviews 1, 2, 4; then conversion/review pairs for Gatheral 6–11. Klebaner,
Gatheral 3 and Gatheral 5 failures remain unresolved, not replayed. Version inventory
separates raw MinerU plus its compilation wrapper, first draft, findings, any supplied
unaccepted revised document, and each compiler check. No review suggestion is applied.

The expanded Docker recipe provisions standard LaTeX collections plus lmodern.
Environment builds contain only the fixed Dockerfile and allowlisted package names;
untrusted documents are compiled separately with the existing isolation. One
identifiable missing-package recovery can rebuild the environment and retry exact
saved TeX; unknown packages/assets and syntax failures cannot trigger install or
model loops. New images need real two-pass qualification. Docker is unavailable to
this session; all compiler-environment execution tests here are mocked.

Full suite: **465 tests in 200.878s: 447 passed, 15 socket-permission errors, three
opt-in real-compiler skips**. Every error is mock HTTP server creation denied with
`PermissionError: [Errno 1] Operation not permitted`; no application assertion
failure. Earlier related suite: 95 tests, 92 passed, three real-compiler skips.
Final full suite includes the added clean-EOF/disconnect classification checks.
The normal-terminal wrapper runs the full suite before inference. No offline test
establishes model fidelity, live stream behaviour or real compiler success.
