# Implementation checkpoint — 29 October 2026

This task explicitly authorizes staging, committing and pushing this reviewed
checkpoint only. The ordinary AGENTS.md Git restrictions remain unchanged for
subsequent tasks. No running job, service, application code or prepared request
was changed by this checkpoint review.

## Repository and scope

Reviewed base: `7b62030324ac8148c3e14478b0914b83f00bb534` (21 October).
Branch: `main`; upstream: `origin/main`.
Configured fetch/push repository: `git@github.com:canary-droid/pdf-to-latex.git`.
The cached upstream equals the base. Live remote verification was blocked by DNS
resolution of github.com in the sandbox; cached state does not establish remote
currency. The operator completion command checks the actual remote before pushing
and refuses divergence, without force, branch switching or reconciliation.

One checkpoint captures the interdependent accumulated implementation:

- Native PDF evidence experiments and reusable saved-page/book review adapters.
- Qwen/DeepSeek recovery, bound acceptance/candidate export and isolated compiler
  validation with separation of document failures from infrastructure failures.
- Versioned text-critic contracts, coherent local context, surgical response repair,
  GLM-first criticism and explicitly selected/cost-bounded MiMo escalation.
- Gatheral/Bergomi intake, saved MinerU plus native PDF text, meaning-focused simple
  chapter conversion and immediate criticism, separate versions/accuracy notes,
  streamed evidence, linked recovery and persistent operator controls.
- Annotated editorial editions and a single coordinator for concurrent requests,
  including completion/ownership snapshot repair, interrupted-pilot reporting,
  preserved history and maximum-two continuation. Later experiments remain deferred.
- Regression fixtures, runbooks, source metadata, selected evidence summaries and
  the full sciwrite-lint MIT licence/attribution. Historical protocols remain readable.

The file list below is explicit. Existing tracked synthetic fixtures, dependency
files and configuration examples are already in HEAD and remain included in the
repository; unchanged files need no staging. No input book/paper PDFs or complete
book extraction is included. Small selected regression snippets are test fixtures,
not raw-run exports.

## Validation and limits

Reused actual operator evidence from
`runs/editorial-chapters-trial-20261029T165410Z-1f2179/normal-terminal-tests-1793293953077127984.log`:
581 tests in222.354s, OK with4 optional real-compiler skips. Its recorded code/test
identity matches the current checkout:
`406f47484934a1880e1f484a0b3686495f303b5d57787e4d630149f357578c92`.
The preceding sandbox suite reported562 passes,15 loopback-bind PermissionErrors
and4 optional skips; those restrictions are not application assertion failures.

Checkpoint checks:70 changed/new Python files parsed,13 JSON files parsed,7 shell
scripts passed bash syntax; tracked diff and all selected untracked files passed
whitespace checks. The selected text files were scanned for private-key markers,
provider tokens, credential-bearing URLs and literal secret assignments; no matches.
No actual credential file was accessed. This scan is not a security certification.
All selected files are below1MiB; the initial135-file selection totals2,402,821bytes.
This checkpoint note is the only additional selected file.

Read-only job snapshot: the linked editorial run is paused at concurrent_production,
113 calls recorded, no in-progress call, writer locks free. The two-slot sample is
now recorded qualified at level2; this does not certify source fidelity or establish
a causal speedup. Historical wording saying prepared/not running remains dated
history; current state/run records are authoritative. Four-slot promotion and later
experiments are not enabled. No inference, compilation, installation or service
operation was performed for this checkpoint.

Deliberately left local: `pdf-to-latex-codex-next-step.txt` (old operator task), ignored
`inputs/`, `runs/`, `results/`, environments, caches/model weights, machine settings,
credentials and runtime locks. Preserve them; no cleanup is requested. The ignored
checkpoint manifest records hashes of every selected file to prevent accidentally
committing later changes. Existing dated runbooks and source-dependent workflows
retain their documented local paths; a clone does not contain the private books/runs.

## Git operation result in this session

Explicit-path staging was attempted after review and failed before modifying the
index: `.git/index.lock` could not be created because the sandbox presents `.git`
as a read-only filesystem. No local commit exists for this checkpoint and no push
occurred. No alternate index, permission change or sandbox workaround was attempted.
Remote `ls-remote` also failed DNS resolution. The ignored preparation is
`results/checkpoint-20261029/`: exact hash manifest, explicit pathspec, commit message,
operation record and completion script. Run in the normal terminal:

```bash
cd /home/mdi/projects/pdf-to-latex && bash results/checkpoint-20261029/finish.sh
```

It validates the reviewed source hashes, branch and existing repository; checks
the live remote before staging; refuses a changed/diverged remote; stages only the
manifest paths; creates one checkpoint commit; pushes without force; and verifies
the remote tip equals that commit. It supports resuming a completed local commit
if a network interruption prevents the push. It never edits application files,
operates model services, launches tests/inference, switches branches or reconciles
history. See its receipt/terminal output for the actual commit and push result.

## Exact selected paths

- `.gitignore`
- `AGENTS.md`
- `README.md`
- `START-HERE.md`
- `docs/BERGOMI-EXTRACTION.md`
- `docs/CANDIDATE-CRITIC.md`
- `docs/CHAPTER-GLM.md`
- `docs/CHECKPOINT-20261029.md`
- `docs/CODEX-HANDOVER.md`
- `docs/DEEPSEEK-ARM-A-TRIAL.md`
- `docs/EDITORIAL-CHAPTERS.md`
- `docs/GATHERAL-EXTRACTION.md`
- `docs/GATHERAL-PLAN.md`
- `docs/GATHERAL-REVIEW.md`
- `docs/GLM-MIMO-CRITIC-PILOT.md`
- `docs/PROJECT-STATE.md`
- `docs/QWEN-NATIVE-TRIAL.md`
- `docs/RECOVERY-CRITIC-TRIAL.md`
- `docs/SCIWRITE-REUSE.md`
- `docs/SIMPLE-CHAPTER-GLM.md`
- `docs/SPARK-OPERATIONS.md`
- `docs/TASK2-DEVELOPMENT.md`
- `docs/critic-calibration-passages.json`
- `docs/editorial-saved-repairs-20261029.json`
- `docs/evidence/candidate-critic-calibration-20261025.md`
- `docs/evidence/chapter-glm-preparation-20261026.md`
- `docs/evidence/critic-backlog-task2-20261025.md`
- `docs/evidence/critic-followup-20261024.md`
- `docs/evidence/critic-overnight-20261024.md`
- `docs/evidence/deepseek-arm-a-preparation-20261022.md`
- `docs/evidence/deepseek-followup-20261023.md`
- `docs/evidence/editorial-concurrency-20261029.md`
- `docs/evidence/editorial-delivery-20261029.md`
- `docs/evidence/editorial-ownership-repair-20261029.md`
- `docs/evidence/editorial-production-20261028.md`
- `docs/evidence/editorial-recovery-20261028.md`
- `docs/evidence/export-recovery-gate-20261024.md`
- `docs/evidence/glm-mimo-route-20261025.json`
- `docs/evidence/klebaner-native-text-pilot-20261021.md`
- `docs/evidence/qwen-continuation-20261024.md`
- `docs/evidence/qwen-native-trial-preparation-20261021.md`
- `docs/evidence/recovery-critic-preparation-20261023.md`
- `docs/evidence/recovery-critic-refresh-20261023.md`
- `docs/evidence/reviewed-candidate-critic-20261024.md`
- `docs/evidence/simple-chapter-131072-20261026.md`
- `docs/evidence/simple-chapter-continuation-20261026.md`
- `docs/evidence/two-source-chapters-20261026.md`
- `docs/gatheral-editorial-plan.json`
- `docs/gatheral-pilot-adoption-20261028.json`
- `docs/licenses/sciwrite-lint-MIT.txt`
- `docs/native-text-pilot-review.json`
- `docs/native-text-pilot-sample.json`
- `docs/source-provenance/bergomi-intake-20261027.json`
- `docs/source-provenance/bergomi-page-classification-20261028.json`
- `docs/source-provenance/gatheral-intake-20261025.json`
- `probe/bibliography.py`
- `probe/book_review.py`
- `probe/chapter_accuracy.py`
- `probe/chapter_concurrency.py`
- `probe/chapter_editorial.py`
- `probe/chapter_glm.py`
- `probe/chapter_inputs.py`
- `probe/chapter_protocol.py`
- `probe/chapter_sources.py`
- `probe/chapter_stream.py`
- `probe/cloud_critic.py`
- `probe/compiler_environment.py`
- `probe/critic_anchors.py`
- `probe/critic_context.py`
- `probe/critic_overnight.py`
- `probe/critic_pilot.py`
- `probe/critic_route.py`
- `probe/deepseek_inputs.py`
- `probe/deepseek_report.py`
- `probe/deepseek_trial.py`
- `probe/editorial_delivery.py`
- `probe/editorial_recovery.py`
- `probe/evaluation_export.py`
- `probe/experiment.py`
- `probe/local_model.py`
- `probe/native_text_pilot.py`
- `probe/paired_inputs.py`
- `probe/paired_report.py`
- `probe/paired_trial.py`
- `probe/portable_export.py`
- `probe/recovery.py`
- `probe/recovery_trial.py`
- `probe/saved_pages.py`
- `probe/sciwrite_subset.py`
- `probe/tex_compile.py`
- `probe/text_critic.py`
- `scripts/book_extraction_intake.py`
- `scripts/editorial_chapters.py`
- `scripts/integrate-editorial-development.py`
- `scripts/render-chapter-native.py`
- `scripts/run-bergomi-extraction.py`
- `scripts/run-candidate-critic.sh`
- `scripts/run-chapter-glm.sh`
- `scripts/run-deepseek-arm-a-trial.sh`
- `scripts/run-editorial-chapters.sh`
- `scripts/run-editorial-continuation.sh`
- `scripts/run-gatheral-extraction.py`
- `scripts/run-gatheral-review.sh`
- `scripts/run-simple-chapter-glm.sh`
- `scripts/simple_chapter_glm.py`
- `scripts/tex-compiler/Dockerfile`
- `sources.json`
- `tests/fixtures/critic-backlog-records.json`
- `tests/fixtures/gatheral-ch2-locator.json`
- `tests/test_bergomi_extraction.py`
- `tests/test_book_review.py`
- `tests/test_chapter_concurrency.py`
- `tests/test_chapter_editorial.py`
- `tests/test_chapter_glm.py`
- `tests/test_critic_backlog.py`
- `tests/test_critic_followup.py`
- `tests/test_critic_overnight.py`
- `tests/test_critic_pilot.py`
- `tests/test_critic_route.py`
- `tests/test_deepseek_trial.py`
- `tests/test_editorial_delivery.py`
- `tests/test_editorial_launch.py`
- `tests/test_editorial_production.py`
- `tests/test_editorial_recovery.py`
- `tests/test_export_recovery.py`
- `tests/test_fresh_gatheral.py`
- `tests/test_gatheral_launch.py`
- `tests/test_isolation_reports.py`
- `tests/test_native_text_pilot.py`
- `tests/test_paired_trial.py`
- `tests/test_recovery_continuation.py`
- `tests/test_recovery_critic.py`
- `tests/test_reviewed_candidate.py`
- `tests/test_simple_chapter_continuous.py`
- `tests/test_simple_chapter_glm.py`
- `tests/test_two_source_chapters.py`
