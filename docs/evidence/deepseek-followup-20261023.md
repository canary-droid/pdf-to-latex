# Focused DeepSeek follow-up — 23 October 2026 (Europe/London)

Offline audit only. No production-code changes, inference, OCR, installations,
service/deployment changes, response recovery or proposal acceptance. All work
remains unstaged. The original completed reports and all historical statuses are
unchanged. This summary contains no book extracts or expected model answers.

## Evidence and original-record checks

- DeepSeek: `runs/deepseek-arm-a-trial-20261022T180153Z-0ee3cf`.
- Comparator: `runs/qwen-native-trial-20261021T062027Z-a1f40a`, Arm A only.
- OCR: `runs/convert-basic-20261020T075104Z-48fd90`.
- Supplied completed inspection ZIP:
  `results/deepseek-arm-a-trial-20261022T180153Z-0ee3cf-inspection-20261022T212950Z-62f929.zip`,
  SHA-256 `475b3e01d0bd8f2004644f7582d016c1dad84a9623d7747f5522e67ae8f3dce4`.

The run was no longer being written: completed_with_failures, null active timestamp,
zero pending/dispatched/interrupted work, no launch process and free project writer
lock. Existing helpers validated both previews/source/code bindings and all 267
DeepSeek plus 267 Qwen-A raw attempt seals. Actual outgoing requests match their
prepared bodies, and all 267 pairs match after changing only model identity.
Messages, images, schema, medium effort, 16,384-token limit and stream=false are
identical; timeout remains 600 seconds. Omitted sampling inherits potentially
different server defaults. Exact raw response identities pass, including failures.
All 256 usable DeepSeek responses have exact selected-block coverage.

Existing ledger/aggregate counts were cross-checked, not rebuilt in the original
run: DeepSeek 256 completed / 11 failed, Qwen A 238 / 29. Paired usable counts:
227 both, 29 DeepSeek-only, 11 Qwen-only, zero neither. Proposals: 105 versus 46;
model-labelled content 29 versus 28. Latency sums: 11,261.7 versus 5,513.8 seconds.
DeepSeek separate reasoning-token usage is not supplied, not zero. None of these
counts establishes mathematical accuracy or human review time.

All eleven DeepSeek failures have HTTP 200, finish_reason=stop and final text:
six missing scope (9,66,105,221,249,261), one result mixed with schema-definition
keys (73), four malformed schema/result concatenations (8,78,148,265). There are
no demonstrated timeout/token-limit failures or simple fenced answers in this set.
Saved strict-JSON readiness passed, but its tiny schema does not qualify the actual
review schema. The baseline intentionally omitted response_format.

## Export blockers: compatibility is separate from quality

All 77 full blocked DeepSeek replacements were inspected against the actual
accepted_fragment/math_fragment implementation. They cover 76 regions: ordinal
243 has two identical replacements under different category labels.

| Primary diagnosis | Proposals |
|---|---:|
| Ordinary text/heading commands outside the small grammar | 58 |
| Bare equations missing display delimiters | 6 |
| Ordinary accent commands outside the grammar | 5 |
| Unicode prose outside the ASCII subset | 3 |
| Ordinary math commands outside the allowlist | 5 |

The first error (71 generic prose/macro, three wedge, three ge) is incomplete as
a diagnosis. Overlapping issues include nine Unicode cases, nine accent cases
and sixteen mathematical allowlist cases. Missing ordinary math commands include
wedge, ge/le, liminf, ldots and delimiter sizing. Existing render_block can emit
textbf while accepted_fragment rejects it; future compatibility work must keep
the renderer and acceptance grammar consistent without admitting arbitrary TeX.

Two of the six bare equation bodies pass math_fragment unchanged; four also need
allowlist consideration. No additional definite brace/math-delimiter defect was
observed in the 77 blocked DeepSeek strings; that is not compilation or fidelity
certification. One explicit hyphenated line break remains context-dependent.
Qwen comparison strings expose separate real syntax defects: ordinal 220 has an
unmatched dollar, and ordinal 33 has missing math delimiters plus a tab/command
corruption. No TeX executable was found on PATH and no compilation was attempted.
Package/engine availability must not be confused with malformed model output.

## Visual scope and practical findings

The additional sample was frozen before image viewing: exactly twelve distinct
regions, four no-proposal cases, four one-model cases and four dense cases. It
excludes the sixteen previously inspected diagnostic regions. Deterministic
hash/density ordering and within-group page diversity are documented; no
reallocation was needed. Sample SHA-256:
`c100db0dc1dcbaae655964bcef582dd5264f307a0e57e6c76c6ad4faca717292`.

- No-proposal cases: ordinals 84,128,216,41.
- One-model cases: 198,38,238,196.
- Dense cases: 143,33,217,178.
- Required rechecks: 5,93,201,207,220,235.

Eighteen selected regions were inspected with twelve original pages for context,
using eighteen original detail crops. This is not full-page omission review or
independent human verification. No new images were generated. The other ten prior
ChatGPT assessments are attributed, not claimed as newly verified here.

Confirmed cautions: both models remove a parenthesis actually printed at ordinal
93; DeepSeek invents blackboard-bold expectation styling at 201; both impose
unsupported uniform expectation styling on mixed source styles at 207. Export
support does not protect against these fidelity mistakes.

Shared useful repairs were confirmed at 5,220,235 and additional case 178. The
235 exporter difference is display wrapping, not unique mathematical detection.
Six additional unchanged cases, including three substantial equations, showed
no content discrepancy. A folio and heading are weak controls, retained as frozen.
The one-model cases support presentation or punctuation changes, not a demonstrated
unique mathematical advantage. At 33 both identify the missing comma, but Qwen's
full replacement is unusable TeX and DeepSeek retains minor presentation defects.
No selected crop was unreadable. Human confirmation remains outstanding.

The larger proposal count, routine styling, export blockers, duplicate replacement
and unsupported source edits create manual work. This sample does not quantify
that burden or prove all extra proposals unnecessary. Keep cosmetic work separate,
check complete replacements, and never use agreement/JSON/export support as
automatic acceptance.

## Recommended next bounded tasks

1. Offline exporter compatibility with narrow balanced prose grammar, explicit
   safe math additions, package/Unicode policy and typed fragment context. Preserve
   original proposal bytes and acceptance/conflict requirements. Regression cases
   must retain rejection of unmatched delimiters, mixed bare prose/math and dangerous
   commands. No compatibility fixes were implemented in this audit.
2. Separate schema-feedback versus constrained-output trial: eleven failures plus
   four successful controls (33,93,178,235), at most thirty requests across the two
   conditions, controls first. Validate support for the actual review schema before
   admitting failure cases; retain strict client validation and medium/16384/600.
   Do not insert this audit's answers or diagnoses. No exhaustion evidence justifies
   lowering reasoning for these eleven. No new live preview/request was prepared.
3. Separate text-only GLM/DeepSeek consistency critic with neutral before/after
   text and source hashes. Keep suspected author errors distinct from transcription
   concerns; it cannot adjudicate visual fidelity. The requested existing
   bibliography/provenance brief was not located in project docs or relevant
   Downloads files. Its path was requested; its contents were not invented. Bind
   that brief unchanged before preparing the later critic stage. Available registry,
   source-provenance files, fidelity checklist and neutral critic export remain.

## Artifacts and validation

- Report: `runs/deepseek-followup-20261022T231635Z-ba686b/report.html`.
- Narrative: same directory's `report.md`.
- Detailed evidence: `export-blockers.csv`, `failures.csv`, `visual-findings.json`
  and `.csv`, frozen sample, exact-string comparisons and verification records.
- Movable inspection ZIP:
  `results/deepseek-followup-20261022T231635Z-ba686b-inspection.zip`.
  **3,373,677 bytes**, SHA-256
  `b1b8d61e510689a63ae1f534222a22753dd5c93a14cbe8e1febceddfe725e38c`.
  Extract and open its run-named `inspection.html`. It contains 45 files, including
  30 deduplicated source images; no PDFs, raw API/base64 trees or reasoning fields.

All 9,570 inventoried original files remain byte-identical, with no added files
in the original evidence/code directories. Image/sample hashes, CSV counts,
report and archive links, ZIP contents/CRC and git diff --check passed. The
one-off audit scripts compile; they remain under ignored runs/. The full unit
suite was not repeated because production code/tests/scripts are unchanged.
All source-quality findings are bounded AI judgments, not book-wide accuracy.
