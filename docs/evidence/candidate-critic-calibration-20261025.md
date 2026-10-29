# Candidate-only critic calibration: external assessment — 25 October 2026

**Codex assessment, not human verification. This file is not a model input.**
Freeze these criteria before the new live answers. No new accuracy score is claimed.
The sample is deliberately challenging and is not a random estimate of book quality.
The old twelve-passage pilot and all its raw results remain frozen.

## Verified starting evidence

GLM `runs/critic-glm-trial-20261025T075343Z-4034ea`: 7/12 final technically valid,
16 calls, 1469.064623 seconds elapsed. MiMo
`runs/critic-mimo-trial-20261025T101919Z-ebb7eb`: 11/12, 14 passage calls (two
repairs) plus one readiness, 2782.185833 seconds elapsed. Its ledger totals
USD **0.1717154424**, with zero unresolved reservations. DeepSeek's selected saved
reference combines `runs/text-critic-followup-trial-20261024T171424Z-8bb3c1` and
`runs/text-critic-overnight-trial-20261024T211031Z-63fbda`: 9/12, thirteen calls,
4125.856758 seconds summed request latency. Do not compare that sum as though it
were the same measurement as elapsed time or call any of these counts accuracy.

The binding resolves the actual candidate to
`runs/evaluation-candidate-20261024T140145Z-6343d9`, version
`8a60ae7132215c943386564f3d014e9ff6d568a01204bfbe5a2e6b1a31f3f6b2`.
Its source is the completed Qwen recovery continuation
`runs/recovery-continuation-trial-20261024T112538Z-8d13d3`, preserving 267 blocks,
27 experimental applications and three unresolved blocks. Its whole-candidate
build is recorded `build_failure_unresolved`; no fresh compilation occurred here.
The formula-only v105 replacement is still deferred. All original acceptance
statuses and source/review evidence are preserved.

## Eight target passages

All IDs below have prefix `klebaner-ch4-7-`. Physical PDF numbers are distinct
from selected-page numbers. No target block is duplicated across passages.

| ID | Original PDF / selected page | Target block range | Blocks | Selection / assessment criterion outside requests |
|---|---|---|---:|---|
| c01 | 126 / 21 | p0021:b11–b15 | 5 | Itô formula: theorem, smoothness hypothesis and both identities. Independently compare with source; no material discrepancy observed in this bounded control. |
| c02 | 146 / 41 | p0041:b2–b11 | 10 | Stochastic-exponential derivation, differential and quadratic variation. Second independently inspected source-faithful control; investigate substantive alarms, not harmless notation or shorthand. |
| c03 | 170 / 65 | p0065:b2–b17 | 16 | Feynman–Kac proof: assess integrating-factor signs and whether the final inference preserves mathematical meaning. Existing portable repair at b14 did not certify the formula. Do not conflate source-author errors with OCR errors. |
| c04 | 166 / 61 | p0061:b2–b12 | 11 | Initial-value term and time/index consistency in the martingale proof. A missing normalization cannot be inferred from absent context; distinguish a genuine inconsistency from a hypothesis-dependent concern. |
| c05 | 212 / 107 | p0107:b3–b11 | 9 | Conditional Fatou/localization and remaining limiting/index notation. Separate an actual logical gap from a subsequent sentence taking the required limit. |
| c06 | 205 / 100 | p0100:b5–b12 | 8 | Optional stopping theorem with hypotheses/proof. Earlier result (7.7) supplied as bounded exact context. Distinguish integrability conditions from unnecessary stronger assumptions. |
| c07 | 205–206 / 100–101 | p0100:b13–b18, p0101:b2–b4 | 9 | Complete hitting-time example across pages. The entire b15 paragraph is retained, exactly equal to its original portable draft, 510 characters. Its unresolved tilde/transcription and the rest of the derivation are not silently corrected or replaced by a single formula. |
| c08 | 176 / 71 | p0071:b2–b8 | 7 | Stopped diffusion statement/proof and measurability claim. Includes a prior MiMo false-alarm challenge; require a valid argument before treating an extra filtration hypothesis as necessary. |

Control image references under the existing candidate:

- c01: `images/08c01381edffa7540f151a2b476603256e75d25e8d19d7c80f86e8c6354578fc.png`.
- c02: `images/41eb66db839481cc7a47a6d6e5d0d40eca6c45d9224d061aeb5b780cf2af77af.png`.

Codex viewed these existing page images and compared the complete selected
candidate statements/formulas: no material transcription discrepancy observed.
Their prior prose repairs remain visible in the candidate inventory. These are
controls for false alarms, not proof of mathematical correctness, all-page fidelity
or absence of every possible issue. No additional source-image audit is implied
for the other six passages; their challenge rationale comes from saved assessments.

The known c08 false alarm deserves an explicit independent check: for a stopping
time, `{tau < s}` is the countable union of `{tau <= q}` over rational `q < s`.
Each belongs to `F_s`, so its complement `{tau >= s}` belongs to `F_s`. This
measurability does not require right-continuity of the filtration. That observation
alone does not settle all predictability/integrability/regularity questions in the
proof. **This argument and all prior diagnoses are excluded from live requests.**

## Context and coverage limits

Prepared targets total **75**, across eight distinct source pages; nine context
block occurrences are supplied to c03/c06/c07, never credited as targets. Six
context block IDs are distinct because c06 and c07 use the same earlier result.
The lookup uses the saved 120-page Klebaner conversion, same source edition/hash.
It records 1952 blocks and 564 detected labels, not 564 verified references.

- c03 receives the labeled Theorem 6.6 block and adjacent whole blocks, with a
  partial-boundary warning; it is not guaranteed to contain a complete proof.
- Theorem 6.2 lookup is ambiguous: a true labeled statement and a later sentence
  beginning with a reference to it both match the conservative index. No candidate
  is silently chosen; c04 retains that context gap.
- Theorem 7.3 context for c05, and the exit-time section for c08, touch unresolved
  portable OCR; they are recorded unavailable rather than silently summarized.
  Complete structured OCR is retained in the local index for later inspection.
- Earlier Theorems 2.35 and 3.18 are outside the converted span. No external source
  is fetched. A valid context request remains unresolved, not a schema failure.

The new preparation is
`runs/candidate-critic-input-20261025T133737Z-8816e4`, run
`runs/candidate-critic-trial-20261025T133737Z-95be74`. Exact serialized request
sizes are 10815, 14724, 23502, 17083, 15124, 16364, 18699 and 13834 bytes, well
under the sealed 196608-byte cap. All target texts/hashes equal the candidate
inventory; context equals the exact saved local index. No text is clipped. The
selection rationale is stored separately from the body. The model sees anchors,
source maps, candidate text, relevant bounded context and the generic schema/prompt.

## How to assess new live outcomes

For each concern, record useful detection, false alarm, missed/residual problem,
justified context request or unresolved source/assembly question. Inspect the full
claim and its reasoning; an anchor's validity is location evidence only. Keep
original model claims, draft version and independent assessment separately linked.
Controls can expose false alarms but cannot estimate a whole-book false-positive
rate. A blank result means no problem detected in the supplied window.

Inspect the paid plan before readiness. Freeze the one-clean-passage sample seed
20261025, scope at most four and planning margin 1.5 before seeing new answers.
Do not change thresholds to make the new trial look better. The MiMo stage is not
an automatic referee: model agreement can reinforce the same mistake. Meaningful
agreement/disagreement requires comparing supporting arguments; non-repetition is
not a refutation. No critic output is accepted or applied by this workflow.

## Offline checks and preservation

`runs/candidate-critic-preparation-audit-20261025T131920Z-418b86/final-validation.json`
records current seals, 336 consumed source bindings, exact body construction and
scope checks. All **945 files across seven original evidence directories** match
the before-work manifests; historical run/preview/call seals verify. The original
combined comparison ZIP hash remains
`06b761188543d4e6a8741fe14d7e60d6b7a148fcdcbf570b2fe3e2e8c9f0dd9f`.

Full suite after final implementation: **350 tests, 333 passed, 15 mock loopback
socket-creation PermissionErrors, two opt-in real-compiler skips**, 189.965 seconds.
The 24 new route regressions passed within that suite. A prior focused run passed
21 tests before the final paragraph/order, query-exclusion and unused-refresh regressions. No assertion failure;
no permissions changed. Python compilation, Bash syntax and `git diff --check`
passed. No real key read, inference, service operation, paid request, installation,
OCR or real compiler invocation occurred. Live quality and server behavior remain
untested. Run the normal-terminal suite before the operator's new GLM calibration.

The final neutrality check also excludes free-form GLM reference queries from MiMo
inputs; exact retrieved source text/anchors remain unchanged. Unused code-bound
preparations are retained with explicit replacement lineage. The eight GLM input
and request files remain byte-identical through this offline implementation refresh.
