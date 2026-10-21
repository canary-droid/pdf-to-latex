# Klebaner extended eight-page audit — 21 October 2026

The user extended Task 2 to all recognized blocks on the same eight pages.
This Codex source-image audit covers selected pages **8, 12, 20, 34, 36, 47,
56 and 62**, original physical PDF pages **113, 117, 125, 139, 141, 152, 161
and 167**. It does not estimate whole-book accuracy or replace independent
human review.

- Batch: `runs/review-batch-20261020T202648Z-7e5476`.
- Task 1: `runs/batch-audit-20261021T024353Z-a762f7`.
- Task 2, located through PROJECT-STATE:
  `runs/sample-audit-20261021T031203Z-a1a1e8`. Its recorded inspection ZIP
  SHA-256 was verified unchanged.
- New audit: `runs/extended-audit-20261021T032917Z-a0c430`.

## Coverage and findings

All **136 recognized blocks** are accounted for: fifteen prior findings reused
and 121 newly inspected, plus the prior region-only omission. Whole-page
omission, duplication and within-page reading-order checks cover all eight
pages. Progress was saved after each pair: 8/12, 20/34, 36/47 and 56/62.

All nine saved proposals contain source-supported corrections; no newly
introduced harmful change or merely equivalent/unnecessary proposal was
observed. Six proposal assessments were reused and three complete replacements
newly checked. One useful replacement, **p0008:b7**, still omits the printed
comma after infinity. Source emphasis and integration limitations are separate
from the correction's transcription value. All proposals remain **UNACCEPTED**.

**Thirteen blocks have unflagged or residual discrepancies:** eight punctuation
cases, three math/prose-boundary cases, one wrong proof-end glyph and one
spurious-accent case. Ten are in completed model units, three in failed units.
Examples include bare `then` in maths in p0020:b8, bare `the`/`SDE` and a
detached differential in p0036:b6, a square recognized as a star in p0056:b4,
and spurious hats in p0056:b10. The detailed ledger identifies every block.

Four additional omitted proof-end squares were found: two on page 8 and one
each on pages 12 and 62. The previously flagged omitted square on page 56
remains supported. No other omission, duplicated content or within-page
reading-order problem was observed. These visual observations are fallible.

Eight recognized blocks have supported proposals; thirteen have missed or
residual issues, overlapping at p0008:b7. Thus twenty recognized blocks have
recorded discrepancies and **116 have no discrepancy observed**. The five
region-only omissions are counted separately. No accuracy percentage follows.

Printed source oddities were preserved, including the page-102 `ds`, the
page-98 k/i index mismatch and the page-146 product-rule differential omissions.
A parenthesis ambiguity in p0056:b11 was resolved using one bounded additional
crop from the hash-verified saved PDF; no error is asserted there. No source
case remains classified as unreadable, without implying infallibility.

## Status and export limitations

Original Qwen statuses remain **31 completed and three failed units** across
these pages. The failed units cover eighteen blocks: p0020-u002 (JSON parsing),
p0047-u003 (schema), p0056-u003 (token exhaustion). Both saved attempts of the
first two have empty proposal arrays in their invalid final responses; no
format recovery was performed. Source inspection does not complete a failed
model request or certify mathematical correctness.

**29 blocks lack portable LaTeX drafts**; native OCR was used for comparison.
This availability gap is not itself a transcription error. Variable math-mode,
inline arrays, source bold/italic emphasis and insertion/compilation questions
are recorded separately. In particular a supported missing-square diagnosis
does not establish that bare `\Box` can safely be inserted. No fixes, acceptance,
application tests or TeX compilation were performed; application code is unchanged.

The practical burden is checking unchanged content, omission regions and the
whole replacement text, not just deciding whether each proposal's stated reason
is useful. This sample shows no excessive unnecessary-proposal load, but it
cannot establish review time or whole-book accuracy.

## Artifacts and checks

- [Inspection report](../../runs/extended-audit-20261021T032917Z-a0c430/report.html).
- [Readable report](../../runs/extended-audit-20261021T032917Z-a0c430/report.md).
- [Block ledger](../../runs/extended-audit-20261021T032917Z-a0c430/blocks.csv).
- [Inspection ZIP](../../results/extended-audit-20261021T032917Z-a0c430-inspection.zip).

The ZIP contains 70 files, including 51 distinct images (50 reused assets plus
one new detail crop), with no repeated image bytes. It excludes PDFs, raw model
requests/reasoning, other pages and the large internal preservation ledger.
Open `extended-audit-20261021T032917Z-a0c430/report.html` after extraction.

ZIP size: **5,996,722 bytes**. SHA-256:
`542af55c70f2973dcdc7afe5600b30df8f6904b1367e7afc1af33102abd3351b`.

Checked exact page mapping and block inventory, all draft/native copies,
original unit statuses and proposal texts, 149 local HTML references, image
hashes, ZIP CRCs and byte equality of all 70 members. Before/after manifests
verify **5,982 batch files, twelve Task 1 files and 34 Task 2 files unchanged**;
the prior Task 2 ZIP also matches its recorded hash. This does not claim a
comprehensive rehash of every conversion incidental file or older archive.
`git diff --check` passed. No inference, service operations, retry changes,
formatting recovery, installations, agents or Git mutations were performed.
