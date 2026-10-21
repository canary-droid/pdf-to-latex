# Reviewed checkpoint — 21 October 2026

Task 3 review of all relevant uncommitted work since `8487126`
(`Add saved-page review and fixture fidelity baseline`). The inspected branch
is `main`, tracking `origin/main`; HEAD and the local origin/main reference both
point to `8487126`. The index was empty. No remote query was made, so remote
freshness and push authentication are not established.

## Assessment and current status

No concrete implementation defect was found that blocks this bounded checkpoint.
Reviewed tracked changes and all relevant untracked source, tests and documents.
The scope includes reasoning-effort selection, explicit saved-proposal acceptance
and derivative export, focused saved-OCR/derivative review, Klebaner registration,
resumable batch execution and selected audit evidence. This is not approval of
all OCR, model suggestions or generated TeX.

The code review checked exact source/review/request bindings, explicit acceptance
rather than certainty-based application, declared atomic groups, explicit deletion
and unsupported-operation rejection, unaffected-block preservation, prompt/data
separation, old-preview compatibility, unsupported JSON-wrapper handling with
strict local validation, page/block/omission accounting, request limits, durable
attempts, resume compatibility, bounded retries and identity/integrity stops.
No new feature, correction, recovery or retry change was made during Task 3.

**Documentation timing caveat:** SPARK-OPERATIONS.md is dated 20 October and its
“Current trial” section still says the batch has not run. Its launch commands
remain a reproducibility reference, not the next operator action. The dated
preparation summaries likewise retain their then-current “not executed” status.
The later PROJECT-STATE entries, completed audits and this checkpoint supersede
those status statements. Do not relaunch the completed batch or follow an old
service-management sequence as part of this checkpoint. The current task stops
after checkpoint preparation; the extraction pilot is a separate later task.

The completed batch `runs/review-batch-20261020T202648Z-7e5476` has 360 completed
and 36 failed units, with 66 pages having completed checks and 34 with gaps.
Task 1 records 16 JSON, 16 schema and four token-exhaustion final failures, and
zero successful retries. These model failures are retained evidence, not test
failures to hide or recover in this checkpoint. All 119 batch proposals remain
UNACCEPTED.

Task 2 is complete for its agreed extended scope at
`runs/extended-audit-20261021T032917Z-a0c430`: selected pages 8, 12, 20, 34, 36,
47, 56 and 62 (original PDF 113, 117, 125, 139, 141, 152, 161, 167). All 136
recognized blocks and all eight pages' omission checks were assessed. Fifteen
prior block findings were reused and 121 blocks newly inspected.

- Nine proposals contain useful source-supported corrections; no introduced
  harmful or unnecessary proposal was observed. One replacement retains a
  missing comma. All remain UNACCEPTED.
- Thirteen blocks have missed/residual defects, including punctuation,
  math/prose boundaries, a wrong proof marker and spurious accents. Ten belong
  to completed model units and three to failed ones.
- Four additional omitted proof squares were found, besides the previously
  flagged square. Completed omission checks are model claims, not guarantees
  that all omissions were found. The Codex image audit itself is fallible.
- Twenty recognized blocks have recorded discrepancies after accounting for
  overlap; 116 have none observed. Omissions are counted separately. No
  whole-book accuracy or review-time estimate follows from these selected pages.
- Twenty-nine blocks lack portable drafts; native OCR was compared instead.
  Source styling, math-mode/package/insertion handling (including bare `\Box`)
  and compilation remain separate limitations. No TeX compilation is claimed.
- The original 31 completed / three failed model units on these pages stay
  unchanged. The visual audit does not turn failed requests into completions.

The earlier four fixture proposals were explicitly authorized and applied only
to a separate derivative; their original review records remain unchanged. That
limited fixture authorization does not authorize Klebaner proposals.

## Current-code validation

On 21 October, discovered 133 tests and ran all **118 socket-independent cases:
118 passed, zero failures/errors/skips**. The 15 methods using `MockServer`
were deliberately excluded, based on inspected method source. Earlier full-suite
runs encountered `PermissionError: [Errno 1] Operation not permitted` creating
loopback `ThreadingHTTPServer` sockets. That denied operation was not retried and
no sandbox permissions changed. This is not a full-suite pass. Current test log:
`/tmp/pdf-to-latex-checkpoint-tests-20261021.log` (local scratch, not checkpoint).

Current checks also passed: Python syntax compilation in memory, JSON parsing,
all five source registrations through `selected_sources('all')`, unchanged prior
four source entries, exact new 120-page mapping/auto OCR mode, extended-audit
completion/counts and recorded ZIP hash, and `git diff --check`. No source images
were reopened and no audit was extended. Existing historical test counts are
kept as history; current-code claims above come from this run.

The new audit ZIP remains outside Git:
`results/extended-audit-20261021T032917Z-a0c430-inspection.zip`, SHA-256
`542af55c70f2973dcdc7afe5600b30df8f6904b1367e7afc1af33102abd3351b`.
Keep it and the original runs separately; a fresh clone contains summaries and
hashes, not the underlying book images or complete experimental evidence.

No live inference, endpoint/service readiness, download status, model accuracy,
TeX compilation or remote push was tested. The DeepSeek download and running
services were not accessed or altered. No extraction pilot was begun.

## Exact checkpoint scope

The explicit-path staging command below is the complete **32-file list**:

| Group | Purpose |
|---|---|
| Eight `probe/*.py` files | Acceptance/export, focused/page/client settings, batch preparation/execution and CLI integration |
| Five `tests/*.py` files | Meaningful regressions for acceptance, effort/serialization, focused selection, coverage, resume and retries |
| `sources.json` and Klebaner provenance JSON | Hashes, original-page mapping and `auto` routing; no source PDF/text extraction |
| Four crop/block-selection JSON files | Synthetic crop geometry and exact selected block IDs, without answer hints |
| Eight `docs/evidence/*` files | Fixture acceptance record and small independent experiment/audit summaries, including extended Task 2 |
| README, START-HERE, SPARK-OPERATIONS, PROJECT-STATE and this note | Usage, historical validation, current status and personal checkpoint steps |

All proposed files are text, individually below 100 KB at review. Content review
and credential-signature checks found no credentials/private keys, embedded book
images/base64, raw extracted pages or copied model reasoning. Small intentional
formula/glyph references in independent evidence summaries explain findings; the
full proposal catalog included here concerns the synthetic fixture only. Local
paths/private endpoint addresses are descriptive provenance, not secrets.

Excluded and preserved: `pdf-to-latex-codex-next-step.txt` (the earlier local
instruction copy, already excluded from the prior checkpoint); all `runs/`,
`results/`, `inputs/`, environments, weights/caches, downloaded archives, local
configuration and credentials. Existing synthetic fixtures and the older
baseline are already tracked and unchanged, so need no additional staging.
No unrelated file or existing staging was undone.

## Commands for the operator — not executed by Codex

1. Run the complete offline suite in your normal terminal. It uses synthetic
   fixtures and mock loopback HTTP servers, not live OCR/model inference. Success
   means **133 tests, OK, exit status 0, no failures/errors or unexpected skips**
   for this unchanged tree. If it fails, retain the output and stop before commit.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -m unittest discover -s tests -v
```

2. After tests pass, stage only the reviewed paths. This is the exact file list;
   do not replace it with `git add .`.

```bash
git add -- \
  README.md \
  START-HERE.md \
  docs/CHECKPOINT-20261021.md \
  docs/PROJECT-STATE.md \
  docs/SPARK-OPERATIONS.md \
  docs/evidence/accepted-fixture-followup.md \
  docs/evidence/fixture-native-acceptance.json \
  docs/evidence/klebaner-100-page-batch.md \
  docs/evidence/klebaner-batch-audit-20261021T024353Z-a762f7.md \
  docs/evidence/klebaner-extended-audit-20261021T032917Z-a0c430.md \
  docs/evidence/klebaner-flash-next-experiment.md \
  docs/evidence/klebaner-paragraph-retry.md \
  docs/evidence/klebaner-visual-sample-20261021T031203Z-a1a1e8.md \
  docs/fixture-focused-blocks.json \
  docs/fixture-native-review-crops.json \
  docs/klebaner-flash-next-blocks.json \
  docs/klebaner-paragraph-retry-blocks.json \
  docs/source-provenance/klebaner-ch4-7.json \
  probe/acceptance.py \
  probe/batch_inputs.py \
  probe/batch_review.py \
  probe/cli.py \
  probe/focused_review.py \
  probe/local_model.py \
  probe/page_review.py \
  probe/portable_export.py \
  sources.json \
  tests/test_acceptance_focus.py \
  tests/test_batch_review.py \
  tests/test_local_model.py \
  tests/test_saved_ocr_focus.py \
  tests/test_saved_review.py
```

3. Check the staged summary and whitespace. Expect exactly the 32 listed text
   paths and sensible text sizes (roughly half a megabyte of complete file
   content, not the diff size). No PDFs, PNGs, ZIPs, raw runs/results, inputs,
   model assets, environments or local configuration should appear. The code
   review has already been performed; this is an inventory check, not a request
   to personally audit every function. If staging has changed since this review,
   resolve the scope before committing; do not blindly unstage other work.

```bash
git status --short --branch
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
```

4. Commit only after the tests and staged checks succeed:

```bash
git commit -m "Add accepted derivatives, batch review and audit evidence"
```

5. After that commit succeeds, inspect it and push the observed branch to its
   existing remote. `origin` is `git@github.com:canary-droid/pdf-to-latex.git`.
   Existing SSH configuration is used unchanged; no authentication workaround or
   force push is proposed. Local origin/main matched HEAD before the checkpoint;
   no fetch/query established the server's current state. If push is rejected,
   stop and retain the diagnostic rather than force or change configuration.

```bash
git log -1 --oneline --stat
git push origin main
```

Only this new handover note and a dated PROJECT-STATE entry were written during
Task 3; all prior implementation/evidence files were preserved. Everything is
unstaged. No Git metadata mutation was performed.
