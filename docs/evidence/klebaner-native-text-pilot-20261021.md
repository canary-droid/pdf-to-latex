# Klebaner positioned native-text pilot — 21 October 2026

This is a bounded offline comparison, not a replacement transcription or an
accuracy benchmark. The opt-in `python -m probe.native_text_pilot` module extracts
positioned PyMuPDF characters and font metadata alongside existing saved OCR.
The default converter is unchanged. No OCR, model or external service was called;
no alternative or existing proposal was accepted or applied.

## Inputs and frozen experiment

Source: `klebaner-ch4-7`, conversion
`runs/convert-basic-20261020T075104Z-48fd90`. Registration and preparation manifest
agree: 120 selected pages, original physical PDF 106–225. The actual registered
selection is `inputs/klebaner-ch4-7/source.pdf`, SHA-256
`61102519b11535ee11e817d7b6f5b357e87435429b231c144c0e82f6dc6f80e4`.
Existing saved-page validation verified owned pages, window overlap, hashes and
block identities. Context pages were not counted twice.

All 15 worker summaries report MinerU 4.0.12 and `parse_mode: txt`. Read-only
inspection of installed MinerU/DocVortex code shows Basic maps to medium effort,
with native prose extraction alongside separate formula recognition and OCR
fallback. Thus enabling native text is not itself a new solution. Installed
versions are PyMuPDF 1.26.6, MinerU 4.0.12 and DocVortex 0.5.16; the pilot records
the relevant installed-code hashes in `environment.json` without importing or
executing the OCR pipeline.

The fixed development original pages are
106, 116, 126, 136, 146, 156, 166, 170, 176, 186, 196, 205.
Holdout originals are 206, 212, 218, 225. No replacements were needed. Holdout is
a later section, not a random representative sample. There are no independent
exhaustive holdout labels: it remains **unscored**.

An initial development-only run, `native-text-pilot-20261021T052234Z-9ca87f`, is
preserved. Development inspection showed that generic Unicode whitespace
normalization could hide font-mapped mathematical control characters. The rule
was narrowed to ASCII space/tab/CR/LF, with regression coverage. A new final run
froze rules, code/helper hashes, source bindings and development artifacts before
holdout. No extraction/alignment/flag changes followed that freeze. Saved model
corrections, acceptance plans, gold LaTeX and audit answers were not inputs.

## Observed workload and alignment

| Measure | Development | Holdout | Total |
|---|---:|---:|---:|
| Pages / recognized regions | 12 / 206 | 4 / 61 | 16 / 267 |
| Exact surface matches | 46 | 19 | 65 |
| Conservative prose-anchor matches | 98 | 33 | 131 |
| Geometry-only assignments | 52 | 9 | 61 |
| Ambiguous regions | 10 | 0 | 10 |
| Entirely empty native regions | 0 | 0 | 0 |
| Flagged regions | 160/206 | 42/61 | 202/267 |
| Pages with flags | 12/12 | 4/4 | 16/16 |
| Unassigned non-whitespace native characters | 15 | 8 | 23 |

There are 196 exact/anchor matches. Alignment is not transcription correctness.
Unassigned characters are retained, not adjudicated as OCR omissions. Zero empty
regions does not mean zero lost glyphs or complete mathematical structure.

| Flag reason (overlapping counts) | Development | Holdout | Total |
|---|---:|---:|---:|
| extraction_disagreement | 160 | 42 | 202 |
| native_math_incomplete | 141 | 39 | 180 |
| missing_or_suspicious_glyph | 51 | 10 | 61 |
| alignment_uncertain | 62 | 9 | 71 |
| ligature_present | 49 | 9 | 58 |
| line_end_hyphen | 11 | 3 | 14 |

All OCR-labelled math is conservatively structurally unverified in a plain native
string. Comparing native characters with TeX also generates expected encoding
disagreements. These fractions measure inspection workload, not error rates.
Signs, punctuation, ligatures and line-end hyphens are retained literally.
Shared character boxes remain ambiguous; no winner is forced. Verified unrotated
crop-relative geometry supports nonzero cropbox offsets; rotation or unequal
source/window geometry is explicitly refused rather than guessed.

## Bounded source-image findings

Twelve selected crops on seven pages were inspected, including five unflagged
controls. Full-page context was viewed on originals 106, 170 and 206; that is not
a full-page fidelity audit. Six selected holdout regions were inspected after
the rules froze. The detailed evaluator ledger is separate from neutral inputs.

| Original PDF / stable block suffix | Finding |
|---|---|
| 106 / p0001:b4 | Known development paragraph: native characters provide useful punctuation/symbol fragments where OCR is wrong. Its integral glyphs and script structure remain damaged; the full paragraph is unsafe as a replacement. |
| 106 / p0001:b7 | Source agrees with the saved equation; native sum glyph and scripts are damaged. A flagged disagreement does not justify an OCR correction. |
| 116 / p0011:b13,b14 | Native character boxes overlap theorem and following equation, contaminating selection. Ambiguity is exposed. Saved equation agrees with source; native glyphs/scripts are misleading. |
| 170 / p0065:b14 | Known damaged nested exponential/integral: OCR and native alternatives both remain unresolved. Native text does not recover structured LaTeX. Printed signs were preserved rather than mathematically repaired. |
| 170 / p0065:b3 | Unflagged control: no content discrepancy observed. |
| 206 / p0101:b5 | Unflagged control: no content discrepancy observed. |
| 206 / p0101:b13 | Saved equation agrees with source; native parentheses and script roles are lost. |
| 212 / p0107:b17 | Unflagged control misses a representation/style distinction: italic theorem text and mathematical M appear as ordinary prose in OCR. Native font metadata is retained but the comparison ignores style. No changed value or theorem statement was established. |
| 218 / p0113:b15 | Unflagged control: no content discrepancy observed. |
| 225 / p0120:b4 | Native extraction drops an integral without a suspicious control character and flattens an exponent. OCR agrees with source; the general math-incomplete flag still applies. |
| 225 / p0120:b6 | Unflagged control: no content discrepancy observed. |

Of five unflagged controls, four showed no content discrepancy and one exposed a
style/math-mode limitation. No changed character, numerical value or punctuation
was confirmed in those controls. This small selection does not establish absence
of other shared or unflagged errors. Seven selected regions were flagged; helpful
fragments in the known paragraph coexist with unsafe or unresolved mathematics
and alignment in the other cases. No TeX was generated or compiled.

## Artifacts and validation

Final run: `runs/native-text-pilot-20261021T052347Z-094634`.

- `report.html`: full 267-region comparison index, raw extraction and crop links.
- `inspection.html`: compact inspection entry, counts and evaluator links.
- `review-pack/report.html`: neutral twelve-region inputs, with 7 page contexts
  and 12 detail images, deduplicated by hash. No diagnoses, flags, control labels,
  expected answers or saved model corrections appear in reviewer inputs.
- `evaluator/report.html`, `findings.json` and `inspection-log.json`: separate
  source assessment and actual inspection coverage; never extraction inputs.
- ZIP: `results/native-text-pilot-20261021T052347Z-094634-inspection.zip`,
  1,745,381 bytes, 37 members, SHA-256
  `66eefc6be0d42087b5bbfe0044f5bc1dca683e6425836ce4e603ef02f03a1a46`.
  Open its `native-text-pilot-20261021T052347Z-094634/inspection.html` after
  extraction. Only the neutral `review-pack/` directory is reviewer input;
  evaluator diagnoses remain separate. Nothing was transmitted.

Ten new regression tests and 27 existing document/saved-review tests passed.
They cover mapping, overlap, coordinates, unmatched/ambiguous regions, math-sign
preservation, freeze/evidence rejection, pack separation and refusal of native
evidence by the existing acceptance validator. The acceptance assertion was also
rerun after it was added. Syntax, unique comparison IDs, frozen manifests, local
HTML links, image deduplication and ZIP CRC/member-byte checks passed.

All 880 original conversion files were byte-hash verified unchanged, as were
the source registry, selected PDF, preparation manifest and full original PDF.
Another preservation check covered existence/size/mtime for 11,487 pre-existing
input/run/result files; those were **not** all byte-hashed. No changes observed.
All new raw material remains under ignored `runs/` and `results/`.

The full current suite was not run here; 15 loopback-server cases previously hit
the sandbox socket restriction. No workaround was attempted. Run in the normal
terminal: `.venv-control/bin/python -m unittest discover -s tests -v` (143 tests).
The operator's successful 133-test checkpoint predates this implementation.

## Integration decision

Retain this as an optional source-comparison aid. The evidence does **not** support
automatic replacement or current flags as a production workload-reduction gate.
Mathematical reconstruction, style-sensitive comparison and overlapping-region
alignment remain limitations. A separately authorized, independently labelled
study would be needed before broader integration. No whole-book accuracy,
review-time saving or monetary saving follows from this targeted pilot.
