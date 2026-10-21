# Klebaner completed-batch audit — 21 October 2026

Offline audit of `runs/review-batch-20261020T202648Z-7e5476`, using the existing
run directly. No images opened, ZIP extraction, inference, retries, acceptance,
production-code edits, dependencies, services or Git mutations.

- [Full report](../../runs/batch-audit-20261021T024353Z-a762f7/report.md)
- [Aggregate results](../../runs/batch-audit-20261021T024353Z-a762f7/summary.json)
- [Exact visual sample and source/crop paths](../../runs/batch-audit-20261021T024353Z-a762f7/visual-sample.json)
- [Small summary ZIP](../../results/batch-audit-20261021T024353Z-a762f7-summary.zip)

The final checkpoint at 2026-10-21 01:24:59 UTC agrees with the operator log:
**360 completed / 36 failed / 0 pending / 0 running / 0 retryable**, 396 distinct
units, 100 owned pages, 1,623 blocks; **66 completed pages / 34 with gaps**.
Selected pages 1–100 map exactly to original PDF pages 106–205. No missing,
extra or duplicate units/pages, interrupted attempts or reconciliation differences.
Elapsed: 17,888.736 seconds. These are processing results, not accuracy scores.

Final failures: **16 JSON parsing, 16 schema, 4 token exhaustion**; no recorded
transport/timeouts, model-identity, primary coverage or other failures. All 36
exhausted both attempts. The 432 attempts include 36 retries with **zero retry
successes**; all retries repeated the first final content, usage and finish reason.
All attempts recorded HTTP 200 and the expected `flash-next-tensorfold` model.
The actual bound preflight is `runs/preflight-20261020T202238Z-265486`.

JSON failures: 14 fenced answers, two prose-prefixed answers. Schema failures:
14 invalid field sets, one null replacement/reason, one wrong unit ID. All four
exhaustion cases used 16,384 reasoning tokens and produced no final content.
Exactly ten of the 14 final fenced answers would pass the unchanged validators
if only their fence were removed in memory. Four remain invalid, including one
visual-coverage claim. **No candidate was recovered or state changed.** The
candidate manifest records all exact paths and remaining diagnostics.

There are **119 UNACCEPTED proposals**, 16 uncertain, affecting 116 distinct
recognized blocks across 68 pages; four are region-only. No same-block competing
proposals were detected. One bounding-box overlap on selected page 44 / original
PDF 149 requires manual interpretation. There are 265 completed units with zero
proposals and 18 completely reviewed pages with zero proposals; failed output is
not counted as zero proposals. **188 recognized blocks** lack completed review;
selected pages **81 and 82** (original PDF 186 and 187) lack completed visual
omission checks. A completed answer validates structure/identity/claimed coverage,
not source fidelity, mathematical correctness, actual visual inspection or TeX.

Recorded latency: median 23.54 s, nearest-rank P95 141.90 s, maximum 328.91 s.
Retries added 2,999.82 s of request latency without additional completed units.
All 432 attempts have recorded usage: 2,951,089 prompt and 1,026,600 completion
tokens, of which 917,511 are reasoning (already included, not added again).
There is no API-cost or Codex-billing estimate.

The later visual sample is selected pages **36, 12, 62, 20, 47, 56, 8, 34**
(original PDF **141, 117, 167, 125, 152, 161, 113, 139**). It covers completed
pages with/without proposals, dense math by a native-marker proxy, uncertain
proposals and all major failure categories. Seed:
`klebaner-batch-visual-audit-20261021-v1`; ordered strata and SHA-256 ranking are
fully specified in the sample manifest. All assigned units/blocks, page context
and detail crops are requested for those eight pages; no images were inspected.

Validation: existing `verify_batch` passed on both prepared/copy previews; source
ownership/maps and registered selected-PDF/listed completed conversion evidence
passed existing checks. All 432 attempt seals, actual request bodies, reservations,
bindings and 360 completed answers were checked. All **5,982 original batch files**
had identical before/after hashes. The original 599,411,149-byte ZIP hash remained
`1b077a7d4d9fe5fdbe0c6a10d3966aa724faec0a2fbc9d123d803e9461400641`.
It was not extracted or verified member-by-member. Conversion incidental logs,
unrelated sources and all preflight raw files were not comprehensively rehashed.
No mathematical/visual or TeX compilation validation was performed.

The audit script syntax, independent CSV totals/token sums, distinct sample and
all sample paths were checked. The summary ZIP's 12 allowed files match the
summaries byte-for-byte and pass ZIP CRC checking. ZIP size **60,554 bytes**;
SHA-256 `d44074d60c3d07d942b32dd933bbb005ebe4cde5e416598e3286c590723f9e98`.
It includes only the audit script, report and aggregate CSV/JSON; source evidence
remains in the original run. No application test suite rerun was needed for this
audit. Keep the small bundle with this record; ignored run/result paths alone
are not durable evidence if those files are later lost.
