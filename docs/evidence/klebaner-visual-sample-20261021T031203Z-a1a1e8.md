# Bounded Klebaner visual sample — 21 October 2026

Task 2 used the exact Task 1 audit `runs/batch-audit-20261021T024353Z-a762f7`
and its recorded sample. Verified links through the completed batch binding to
`runs/review-batch-20261020T202648Z-7e5476` and original conversion
`runs/convert-basic-20261020T075104Z-48fd90`.

- [Inspection HTML](../../runs/sample-audit-20261021T031203Z-a1a1e8/report.html)
- [Report](../../runs/sample-audit-20261021T031203Z-a1a1e8/report.md)
- [Findings table](../../runs/sample-audit-20261021T031203Z-a1a1e8/findings.csv)
- [Prior region selection](../../runs/sample-audit-20261021T031203Z-a1a1e8/selection.json)
- [Actual image-use log](../../runs/sample-audit-20261021T031203Z-a1a1e8/inspection-log.json)
- [Compact inspection ZIP](../../results/sample-audit-20261021T031203Z-a1a1e8-inspection.zip)

This is Codex source-image assessment, **not independent human verification**.
The 136 blocks in Task 1's sample were the available pool, not reviewed coverage.
Exactly **16 regions** were selected structurally before judgment: six saved
proposals, seven unchanged controls, three failed-work regions. This comprises
15 recognized blocks and one region-only omission on the eight recorded pages.
The inspected regions belong to 14 distinct request units: 11 passed response
validation and three failed. No full-page fidelity claim follows.

| Selected | Original PDF | Printed folio read from image |
|---:|---:|---:|
| 36 | 141 | 126 |
| 12 | 117 | 102 |
| 62 | 167 | 152 |
| 20 | 125 | 110 |
| 47 | 152 | 137 |
| 56 | 161 | 146 |
| 8 | 113 | 98 |
| 34 | 139 | 124 |

Opened eight full-page context images and **15 distinct detail crops** in batches
of at most two source pages. Fourteen detail images were existing saved crops.
One additional bounded crop within already-selected p0062:b2 clarified a glyph;
its source-window PDF hash, local index and bounds are recorded. Two pairs of
region crops are identical copies, opened once each. No further images or regions
were inspected after reaching the selected sixteen.

**All six inspected proposals have source support**:

- p0036:b15: restores the printed terminal period in Example 5.3.
- p0062:b2: removes a spurious overbar from B in the draft.
- p0062:b6: restores the printed reference (6.1), misread as delta/I in OCR.
- p0056-u005, region only: restores the omitted second proof-end square.
- p0008:b3: restores the paragraph's printed terminal period.
- p0008:b6: removes spurious dot/hat accents and restores the real-number symbol.

No incorrect or unnecessary-equivalent proposal was observed among these six.
Two saved proposals were uncertain; their flags and UNACCEPTED status remain
unchanged. Three selected blocks lack portable LaTeX drafts, so preserved native
MinerU content was compared explicitly. Bare `\Box` insertion/math-mode/package
handling and source emphasis preservation remain limitations; no TeX was compiled.

**Seven unchanged controls showed no discrepancy in the selected regions**;
zero missed errors were observed there. The printed ds in the page-102 piecewise
formula and awkward grammar on page 124 were preserved rather than silently
corrected. The three failed-work equations also appeared consistent with their
source crops, but remain regions with no usable validated model result. Failure
is a coverage gap, not automatically an OCR error. No failed answer was recovered.

The sample shows useful suggestions, not an unbiased accuracy rate. Three fixes
are substantive symbol/reference changes; three are lower-impact punctuation/
proof-marker changes. The latter are real source corrections, not false positives,
but a whole-paragraph replacement for a missing period still demands checking
unchanged mathematics. No unnecessary-proposal flood was observed; the sample
cannot determine whether total manual review is excessive or estimate operator
time. Whole-page omissions, unselected blocks and Task 1's page-44 potential
proposal overlap were not adjudicated. All proposals remain unaccepted.

Checks passed: selected IDs/mappings, exact 16-region/8-page limits, distinct image
counts, CSV denominators, copied image hashes, local HTML paths, and preservation
of all **5,982 existing batch files and 12 Task 1 audit files**. Key bindings and
conversion state remain unchanged. Full conversion incidental files and original
archives were not comprehensively rehashed during Task 2. No production changes,
application test-suite run, formatting recovery, retry changes, inference, OCR,
services, installations, permission changes or Git mutations. `git diff --check`
passed. All changes remain unstaged.

Inspection ZIP: **3,138,922 bytes**, 33 files, SHA-256
`d5330ba077c0fd97940f5a706c1faa66fc298510fa1924da520303cf86ca7a78`.
CRC and member bytes match the selected report/JSON/CSV/images. Images retain
original resolution; duplicate per-region crop copies retain stable links.
Excluded: full PDFs/book, original 600 MB ZIP, requests/base64, raw model reasoning,
unselected proposals/images and the internal preservation ledger. Keep this
small inspection bundle with the evidence record.
