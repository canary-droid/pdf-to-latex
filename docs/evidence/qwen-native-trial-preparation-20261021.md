# Task 5 revision 2 — offline preparation evidence, 21 October 2026

**Prepared, not executed.** No readiness, model-discovery or inference call was
made. This record reports input/runner validation, not Qwen benefits, failures
or mathematical accuracy. The operator launches the trial separately using
[the exact runbook commands](../QWEN-NATIVE-TRIAL.md).

## Frozen scope and provenance

| Item | Recorded value |
|---|---|
| Source conversion | `runs/convert-basic-20261020T075104Z-48fd90` |
| Task 4 evidence | `runs/native-text-pilot-20261021T052347Z-094634` |
| New sealed preview | `runs/qwen-native-input-20261021T062027Z-c025fd` |
| New prepared live directory | `runs/qwen-native-trial-20261021T062027Z-a1f40a` |
| Preview seal SHA-256 | `7cf4a38517b01a8651721b8fcd0e600ddc9aeae29c6ed03042593999317fe299` |
| Live binding SHA-256 | `853859fa9de2e755e11495cbee7169eb1199e0e7af2fe190337d49c35aedcf99` |
| Recognized regions / pages | 267 / 16 |
| Flagged / unflagged | 202 / 65; flags are not confirmed defects |
| Priority core | 48 across all 16 pages; 25 flagged / 23 unflagged |
| Remainder | 219; 177 flagged / 42 unflagged |
| Review request ceiling | 534, priority 96 then remainder 438; no retries |
| Portable draft unavailable/invalid | 78; structured OCR retained without repair |
| Maximum prepared request | 492,046 bytes / 9,643 text characters |

Original physical pages are
106,116,126,136,146,156,166,170,176,186,196,205,206,212,218,225.
All mappings and owned block IDs agree with saved conversion evidence. No context
page duplicates or new pages are included; no extraction or crop generation was
rerun. Both arms use the same existing page context and region crops.

The initial twelve regions retain the neutral pack's exact OCR and image hashes.
The next 36 are eighteen flagged and eighteen unflagged distinct regions. Seeded
SHA-256 ordering, round-robin across pages and available within-page flag/math
strata, freezes all subsequent cases before outcomes. Seed:
`klebaner-native-paired-revision2-20261021`. Arm order alternates A/B, B/A.
Known development examples, previously inspected cases, priority and remainder
are identified separately in the evaluator manifest, not model inputs. This is
an exploratory diagnostic cohort, not independent gold or a whole-book sample.
Unrecognized omissions outside the regions remain outside its coverage.

## Controlled requests and narrow runner

Arm A: images + raw structured OCR + portable draft when available + neighbouring
OCR context. Arm B adds only compact literal native PDF text. An offline comparison
of all 267 pairs confirmed identical bodies after removing B's one additional
native-evidence content item. No cross-arm messages, evaluator flags, diagnoses,
expected corrections or saved model proposals occur in the request bodies.
Control characters are JSON-escaped and their codepoints identified; no native
mathematics, ligatures, signs, punctuation or line boundaries are repaired.
Positioned character metadata remains bound on disk rather than in the prompt.

Both arms use `http://127.0.0.1:8890/v1`, exact `flash-next-tensorfold`, explicit
`reasoning_effort=medium`, 16,384 maximum output tokens, `stream=false`, and a
600-second wall timeout. Temperature/top-p/top-k/seed are omitted, inheriting
server defaults as in the successful saved paragraph retry. A label does not
verify hidden server settings, weights or actual reasoning behaviour.

`response_format` is intentionally omitted in both arms. The response schema
stays in the prompt; strict parsing and existing model identity, scope, block
coverage and proposal validation remain intact. The narrow schema extension
requires model-reported proposal categories and separates observations. It does
not score truth. Malformed JSON/fences/duplicate keys are rejected, not repaired.

The new runner reserves each arm durably before dispatch, saves exact client
requests and raw response evidence, and seals outcomes. Interrupted reservations
are consumed rather than resent. It persists the 12-pair gate (at least 9/12
validator passes in each arm), connection-pause streaks and cumulative nine-hour
admission budget. The gate is protocol reliability, not mathematical accuracy.
Identity/integrity/configuration mismatch stops; two consecutive transport failures
pause. Only pending work is resumed. Crash downtime since the last active
checkpoint is charged conservatively. A running request retains its original
600-second deadline; the budget never adds retries or extra cases.

The launcher checks converter exit and runs a fresh readiness preflight through
project APIs, capturing the actual directory automatically. Both Text passed and
vision qualified are required; unsupported server strict JSON is allowed under
local validation. Tiny vision controls do not establish mathematical vision.
No service/download/model-setting operation or GLM stage is implemented.

## Reports, bundle and later evaluation

Full report: `runs/qwen-native-trial-20261021T062027Z-a1f40a/report.html`.
The prepared state contains 534 pending arms, zero attempts and no readiness run.
Aggregate/per-region ledgers include all regions and distinguish pending, failed,
interrupted and completed arms, matched pairs, model-reported categories,
uncertainty, tokens and latency, separately for priority/remainder/overall.
Useful or harmful changes remain unassessed until compared with source images.

Initial offline compact ZIP:
`results/qwen-native-trial-20261021T062027Z-a1f40a-inspection-20261021T062043Z-e6ee87.zip`.
Exact size **4,676,398 bytes**; SHA-256
`11cbe67bf43d43320cae18755907e1f4905bc0fad7e1d154871ebd59a59b3233`.
It includes complete 267-region ledgers and neutral text export, plus all 48
priority cases with 64 unique images (48 details, 16 contexts). All responses are
pending. Future bundles add at most twelve attempted remainder cases, prioritizing
failures/incomplete pairs then differing validated answers, with frozen order
breaking ties. Raw/base64 API payloads and reasoning fields are excluded; they
remain in the live evidence directory. New ZIP names preserve earlier archives;
`latest-bundle.json` records the actual current path, byte size and hash.

The neutral future `neutral-critic.json` contains OCR/native alternatives and
available Qwen proposals, linked to original page IDs, image/input hashes, without
evaluator labels. It explicitly cannot establish visual fidelity. No GLM call.
The source-audit plan requires full-replacement and unchanged-control inspection,
recording improvements, regressions, misses, uncertainty, insertion/compilation
issues and review burden. Codex judgments must be labelled Codex, not independent
human gold. No accuracy, savings or integration recommendation precedes live
results and source assessment.

## Checks and preservation

- All 23 new offline tests passed, including actual LocalClient serialization,
  fixed cohort/priority partition, source mapping, strict responses and identity,
  per-arm reliability thresholds, at-most-once interruption/resume, retained
  failure usage, deadline/exhausted-budget handling and partial ZIP exclusions.
- Current full discovery: 166 tests. All 151 socket-independent cases passed;
  fifteen known MockServer loopback cases were excluded without a sandbox change.
  Normal-terminal command: `.venv-control/bin/python -m unittest discover -s tests -v`.
- Preparation ran with socket creation, subprocess workers and LocalClient
  transport patched to raise if invoked. It succeeded without invoking them.
- Actual sealed-preview checks passed for all 534 bodies, all page mappings,
  exact twelve-case image/OCR reuse, pair-only native differences, input isolation,
  source hashes, unique region coverage, local HTML/ZIP links and ZIP CRC.
- The preview binds 1,251 existing source/pilot files. A separate before/after
  inventory verified 1,268 protected file hashes unchanged: conversion, Task 4
  pilot, Task 4 implementation/tests/sample/evidence, Task 4 ZIP, registered
  source/manifest, AGENTS and the unrelated local instruction copy. This is the
  byte-hash preservation scope, not a claim to have rehashed every older run.
- Python syntax and `git diff --check` passed. Generated book material remains
  under ignored runs/results. No Git metadata change, staging, installation,
  inference, OCR, service operation or DeepSeek-download interference occurred.

Task 4 changes remain unstaged and preserved. Task 5 changes are also unstaged.
The only next live action is the operator's explicitly launched Qwen experiment.
