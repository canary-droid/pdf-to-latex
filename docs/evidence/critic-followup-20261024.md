# Critic repair and bounded follow-up — 24 October 2026

The original gate failed: 4/8 final valid, 4/8 first-attempt valid, 3/8 complete
claimed coverage, after 10 calls and 2361.8064247909933 admission seconds.
The remaining 31 pending units and one unavailable reserved unit were not sent.
No historical results, candidates, acceptance records or raw attempts were changed.
The task's 15:12 inspection ZIP exists and passes CRC; the operator created a
later 16:47 ZIP as well. Both hashes are recorded in validation.json.

## Observed failures and their causes

Three g02-X responses are complete JSON that fail the exact-quotation check at
`$.findings[2].quotes[0]`, block `klebaner-ch4-7-p0100:b12`. The outgoing passage
and validator input agree. The model adds an opening inline-math delimiter before
a substring that already lies inside math mode. The quote consequently does not
occur in the supplied text. A quotation is not required to compile by itself.
Strict substring, occurrence, block, draft-hash and model-identity checks remain.

A second obstacle was the existing recovery substance guard: after a valid quote
repair it would reject changes to the `quotes` field as substantive changes.
Only individually invalid citations may now change during targeted quote repair;
all other finding fields, valid citations and uncertainty remain protected. A
saved original-finding anchor survives intervening failed repairs and resume.
This does not perform fuzzy matching, normalisation or automatic text edits.

Two findings in each rejected g02-X response have independently valid citations.
They are now visible as **provisional diagnostics**, not completed responses,
accepted findings or established mathematical facts. The invalid third finding
and full original response remain available. These are two observations repeated
across three attempts, not six independently established defects. Truncated JSON
is never closed, extracted or promoted to provisional findings.

The original totals skipped usage nested under failed outcomes. The two failed
feedback calls consumed **9535 completion tokens and 175.782564106863 seconds of
request latency**, while the original summary recorded zero for both. The revised
summary is in a new derived-old-report directory. Missing counters remain null
with explicit missing-call counts; inherited calls are counted once. Request
latency is distinct from full admission/wall time.

## Budget failures and runtime evidence

G03-X emitted 3048 final-content characters before its JSON was truncated.
G04-X/Y emitted no final content. Each used 16384 reported completion tokens with
finish_reason=length. All ten replies lack separate reasoning-token counts;
absence is not zero. Saved reasoning_content and reasoning are duplicate strings,
not independent reasoning streams. Final output is in content.

Qualitative inspection of the saved reasoning shows substantive mathematical
analysis mixed with repeated reconsideration of findings, context, formatting,
priority and severity. G03-X progressed to producing JSON; g04-X/Y continued
reconsidering their findings at the cutoff. G04-Y also speculates about grading.
This is not evidence of a fixed identical-output loop or that a larger allowance
would only repeat forever. Nor does it establish that doubling the allowance will
solve the problem. The new general relevance/context instructions address these
observed distractions without supplying diagnoses or imposing a finding cap.

The saved regular deployment command uses --max-tokens 32768. Its immutable
image ID matches the available image archive configuration. Read-only inspection
of its embedded runtime messages explicitly states that max_tokens counts both
reasoning and final content and that these appear in separate response fields.
The binary includes validation messages naming medium. Its exact effective
mapping/honouring cannot be established from the available configuration and
messages; full runtime source and effective-effort telemetry were unavailable.
No endpoint probe or binary execution was used. runtime-support.json records
whitelisted deployment/configuration hashes and the inspected binary hash.

The new trial requests **medium, 32768 maximum output tokens, 900 seconds**, serial
execution and unchanged sampling defaults. This is a response-completion
experiment, not evidence that medium is honoured. Lower-effort recovery remains
disabled: neither a verified lowering effect nor a reasoning-only token counter
trigger has been established. No runtime/server setting was changed.

## Changed behaviour and scope

General instructions now require verbatim substrings without balancing math
quotes; prioritise signs, bounds, indices, symbols, hypotheses, logic and meaningful
references; inspect entire sentences/headings for parentheses; avoid turning
harmless formatting into image-review tasks; and identify the particular check
blocked by missing context while continuing independent local checks. Existing
sciwrite-lint prompt protection is reused; source/model/feedback content is data.
No corrected source text, visual-model explanations or expected diagnoses is added.

All eight input files and user messages are byte-identical to the prior gate.
Only the system instructions and max_tokens change in the prepared request bodies;
timeout and trial scope change in configuration. The original/candidate labels and
order remain fixed. The same eight units are now explicitly diagnostic/development
cases, not unseen gold. The original 20-group recipe and reserved selection remain
unchanged and unobserved. No remaining unit is admitted by this new preview.

Bounds: 8 initial calls, at most 8 shared recoveries, at most 2 extras per unit,
four cumulative admission hours. An admitted request may finish up to 900 seconds
after the admission boundary. Original gate thresholds remain 6 first valid,
8 final valid and 6 complete claimed coverage; provisional findings count toward
none of these. No old counters were reset; the new experiment records explicit
lineage and the original 10 calls / 2361.806 seconds separately.

## Offline validation and limits

13 focused regressions pass. Full suite: 290 tests, 273 passed, 15 mock loopback
socket setup PermissionErrors, 2 opt-in compiler skips, no assertion failures.
Compiler qualification was deliberately not rerun. Python syntax and whitespace
checks pass. No live inference, accuracy measurement, source acceptance, service
operation, package install or Git mutation was performed. Speed work is deferred.

## Completed original attempts

| Call | Unit | Method | Status | Seconds | Prompt tokens | Completion tokens | Finish |
|---|---|---|---|---:|---:|---:|---|
| 0001 | g01-X | baseline | completed | 227.374 | 2539 | 11132 | stop |
| 0002 | g01-Y | baseline | completed | 230.721 | 2542 | 10733 | stop |
| 0003 | g02-X | baseline | failed | 266.657 | 3237 | 14332 | stop |
| 0004 | g02-X | json_feedback | failed | 97.321 | 4906 | 5187 | stop |
| 0005 | g02-X | json_feedback | failed | 78.461 | 6572 | 4348 | stop |
| 0006 | g02-Y | baseline | completed | 308.398 | 3215 | 16239 | stop |
| 0007 | g03-Y | baseline | completed | 188.050 | 2658 | 9059 | stop |
| 0008 | g03-X | baseline | failed | 312.039 | 2661 | 16384 | length |
| 0009 | g04-X | baseline | failed | 311.195 | 5500 | 16384 | length |
| 0010 | g04-Y | baseline | failed | 332.107 | 5211 | 16384 | length |

Actual paths:

- audit: `/home/mdi/projects/pdf-to-latex/runs/critic-followup-audit-20261024T170212Z-523425`
- preview: `/home/mdi/projects/pdf-to-latex/runs/text-critic-followup-input-20261024T171424Z-47ad07`
- run: `/home/mdi/projects/pdf-to-latex/runs/text-critic-followup-trial-20261024T171424Z-8bb3c1`
- old_run: `/home/mdi/projects/pdf-to-latex/runs/text-critic-trial-20261024T140153Z-32efd8`
- old_preview: `/home/mdi/projects/pdf-to-latex/runs/text-critic-input-20261024T140150Z-062adf`
