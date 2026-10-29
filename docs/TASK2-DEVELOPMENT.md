# Task 2 development handover — 25 October 2026

Development directory: `/tmp/pdf-to-latex-critic-development-20261025`.
Extraction directory: `/home/mdi/projects/pdf-to-latex`.
The development copy includes current unstaged/untracked source state as ordinary
independent files. It contains no `.git`, environment, credentials, source books,
model cache or large run/result trees. Original file hashes are recorded in
`development/baseline.json`; new files are recorded as originally absent in the
final change manifest. No original project file was edited during development.

Preserve the final patch bundle outside `/tmp` before reboot or cleanup. The bundle
contains changed files, a unified patch, baseline/change records, test results and
a guarded copy-back helper. Its exact path and extraction decision are recorded in
`development/FINAL-HANDOVER.json`. The original extraction fingerprints all top-level
`probe/*.py`; do not copy code or documentation into an unfinished checkout.

## What changed

1. Coherent bounded context: observed statement boundaries, associated displays,
   cross-page continuation, verbose-reference normalization, original wording and
   deduplication. Partial/ambiguous/unavailable evidence stays explicit. Saved c03
   now resolves Theorem 6.3 b2–b5, excluding its folio/proof, rather than b1–b3.
2. Separate reporting dimensions and span-based potential agreement. Saved c03
   sign and c05 limit concerns are visible as material **and** source-image tasks.
   Positive/editorial entries remain separate. Model agreement is not verification.
3. Future critic v3 uses Python-owned document bindings and exact-invalid-field
   patches. Unrelated findings/references/uncertainty cannot be replaced; unexpected
   extra commentary is retained. v1/v2 evidence remains readable under original
   validation. No old response, hash or success count was changed.
4. Explicit `probe.book_review` adapter from a completed ordinary conversion into
   the existing protected visual recovery executor. Exact owned-page/block maps,
   full-block crops/context, page-omission units, shared retry/time limits, compiler
   binding and conservative candidate assembly. Small gate then the same run's
   pending work, with no baseline replay. See GATHERAL-REVIEW.md.

## Focused evidence and limits

Only the supplied completed GLM/MiMo evidence was used. Four initial target sets
and candidate/draft hashes match; preview and call seals were checked read-only.
MiMo: four first attempts plus one c03 contextual reassessment, 23m01s, stage cost
including readiness USD 0.0680012862, cumulative USD 0.2397167286, zero unsettled.
The old c06 extra-notes failure remains a historical failure; the new contract's
repair behavior is demonstrated offline, not retroactively credited to that run.
Small recorded responses in tests are regression fixtures, never future prompts.
Diagnostic controls stay labelled separately from automatic escalation choices.

No model call, paid readiness, compiler/GPU workload, source-PDF re-audit, conversion,
installation, permission/service change or Git mutation occurred. The controller
interpreter is used by absolute path; imports and temporary outputs resolve to the
development copy. No claim of live model quality or real compilation follows from
mocked tests. Review `development/validation.json` for final counts and limitations.

## Safe copy-back

Run `development/copy_back.py --check` with the existing controller interpreter.
It is read-only: it requires the actual Gatheral conversion to be fully complete,
all 210 pages owned once across completed windows, no visible project converter or
launcher, all changed destination hashes to match the recorded baseline, and every
new destination to remain absent. Unknown/failed/paused/running state refuses copy-back.

Only after a successful check, use `--apply`. It repeats checks under the existing
project writer lock, verifies all packaged replacement hashes, and copies only
listed changed files. It never uses Git or copies a whole tree. Keep the tested
development copy until the operator has verified integration. On any mismatch,
preserve both versions and reconcile explicitly; do not override the guard.

## Operator checks

These commands run offline from the development copy and do not invoke a real
compiler. Mock loopback socket tests may be sandbox-denied here; run them in the
normal terminal without changing sandbox permissions. Real compiler/GPU/model
behavior is deliberately untested in Task 2.

```bash
cd /tmp/pdf-to-latex-critic-development-20261025
env -u PDF2TEX_COMPILER_IMAGE TMPDIR="$PWD/test-tmp" PYTHONDONTWRITEBYTECODE=1 \
  /home/mdi/projects/pdf-to-latex/.venv-control/bin/python -B \
  -m unittest discover -s tests -v
```

After guarded integration, follow GATHERAL-REVIEW.md. Do not run its live readiness
or gate from this development copy. The next live step is a small Qwen source-image
gate, then inspection/candidate assembly and local GLM; MiMo remains selected only.

## Integration result

Guarded integration completed at 2026-10-25T23:42:17.326586+00:00. All 210 pages in `runs/convert-basic-20261025T230247Z-e6bb30` were complete, no visible converter/launcher remained, and all changed destinations matched their baselines. All 27 files were integrated under the writer lock. Do not run copy-back again: the original now contains these changes and the original-before guards deliberately refuse a replay. The operator should next run the normal-terminal test suite, then the offline Gatheral preparation and small gate in GATHERAL-REVIEW.md.

Exact changed project files:

- `README.md`
- `docs/CANDIDATE-CRITIC.md`
- `docs/CODEX-HANDOVER.md`
- `docs/GATHERAL-EXTRACTION.md`
- `docs/GATHERAL-PLAN.md`
- `docs/GATHERAL-REVIEW.md`
- `docs/PROJECT-STATE.md`
- `docs/RECOVERY-CRITIC-TRIAL.md`
- `docs/SCIWRITE-REUSE.md`
- `docs/TASK2-DEVELOPMENT.md`
- `docs/evidence/critic-backlog-task2-20261025.md`
- `probe/book_review.py`
- `probe/cloud_critic.py`
- `probe/critic_anchors.py`
- `probe/critic_context.py`
- `probe/critic_route.py`
- `probe/evaluation_export.py`
- `probe/experiment.py`
- `probe/recovery_trial.py`
- `probe/sciwrite_subset.py`
- `probe/text_critic.py`
- `scripts/run-gatheral-review.sh`
- `tests/fixtures/critic-backlog-records.json`
- `tests/test_book_review.py`
- `tests/test_critic_backlog.py`
- `tests/test_critic_route.py`
- `tests/test_isolation_reports.py`
