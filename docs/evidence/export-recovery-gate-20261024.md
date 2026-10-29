# Export-validation recovery — 24 October 2026

This is an offline implementation/preparation record, not a source-fidelity
audit or live model result. All proposals remain UNACCEPTED.

## Observed historical gate

Preview: `runs/recovery-vision-input-20261023T192304Z-70e8b9`.
Run: `runs/recovery-vision-trial-20261023T192309Z-cdec02`.

| Observed property | Result |
|---|---:|
| Baseline calls with valid JSON/claimed selected-block coverage | 24 |
| Proposals | 8 |
| Original/proposed pairs recorded `both_compiled` | 7 |
| Proposal rejected before compilation | 1 |
| Recovery calls | 0 |
| Pending baseline regions | 243 |

v005 (`klebaner-ch4-7-p0065:b14`, PDF 170, call 0003) supplies bare math but
declares `latex_fragment`. The exact exporter diagnostic is “Raw TeX control or
mathematics outside math mode”. Validation retained completed status and the
compiler skipped unsupported fragments, leaving no recoverable failure for the
scheduler. Valid JSON/gate success did not establish exportability.

## Corrected path and limits

Actionable export failures now enter the existing shared feedback mechanism.
Feedback retains the exact failed answer/diagnostic, allowed formats, actual
schema and original images/OCR context. It requests representation correction
while preserving mathematical content. Only affected representation fields may
change; a persistent original-answer anchor survives malformed intermediate
repairs. No expected answer or equation-specific relabeling is used. Identity,
schema, coverage, export and eligible compilation are checked again. Unreadable,
unsupported, conflicting or exhausted outcomes stay unresolved/deferred, with
infrastructure/configuration problems classified separately.

The original v005 OCR equation also has unbalanced braces. Exact safe source
equation bodies may be wrapped for isolated compiler diagnosis, with the
transformation recorded; this does not make an original fragment exportable.
A replacement may compile while its original fails. Neither was compiled anew
in this task. Mathematical equivalence still requires human/source review.

New preview: `runs/recovery-repair-input-20261024T103428Z-cf096e`.
New run: `runs/recovery-repair-trial-20261024T103428Z-1a2018`.
Only v005 is dispatchable; no baseline is replayed. All 24 old sealed calls are
inherited unchanged. Two additional v005 calls remain within the same 80-call
overall recovery ceiling. The six-hour admission clock inherits 817.8629703969928
seconds already used. Repeated preparation cannot reset allowances; resume
retains every consumed reservation. Current-code binding and old-code provenance
are separate, without rewriting historical seals. The other 243 inputs remain
unchanged and cannot be launched from this derivative.

## Offline checks and artifacts

- 17 new focused regressions passed, including saved v005, successful mocked
  representation repair/export/compiler progression, invalid/exhausted repairs,
  valid math-body controls, unchanged gate successes and durable resume limits.
- Full suite: 260 tests, 243 passes, 15 sandbox mock-socket permission errors,
  two skipped opt-in real compiler tests; no assertion failures. Full log:
  `results/export-recovery-full-tests-20261024.log`.
- All 267 original request bodies/data and image hashes match, with identical
  ordering/selection; all 24 copied call directories match byte-for-byte.
- All 1,131 original preview/run files and membership remain unchanged; 11,086
  bound source hashes and new preview/current-code seals verify.
- Detailed validation:
  `runs/export-recovery-checks-20261024T101818Z-f56144/validation.json`.
- HTML: `runs/recovery-repair-trial-20261024T103428Z-1a2018/report.html`.
- ZIP:
  `results/recovery-repair-trial-20261024T103428Z-1a2018-inspection-20261024T103430Z-024f2c.zip`.
  11,505,978 bytes, 296 unique members; CRC and image links pass. SHA-256:
  `6f0692e10942f3e64d89aff9ecb73ddb1898d6b9d1e7179e91f8e92762923129`.

The ZIP includes HTML/Markdown reports, failures CSV, ledger, source images and
repair provenance. Raw reasoning/API bodies and encoded requests stay in runs/;
full PDFs and model weights are excluded. No live repair or new real compilation
has occurred. See [the current operator runbook](../RECOVERY-CRITIC-TRIAL.md)
for fresh readiness, mandatory qualified compiler arguments, v005-only launch
and a new post-repair bundle. Stop after inspection; broader continuation and
critic refresh remain separate work.
