# Project checkpoint - 17 October 2026

- Controlling design: PDF-to-LaTeX Framework Design 1.1, 17 October 2026.
- Current scope: milestone 0B, local-only compatibility/fidelity probe.
- Source material: standalone Quant Wiki walkthrough 1.1 (25 September),
  quant-wiki-spark-pilot revision 1.0 (5 October), run-two-spark-models snapshot
  (4 October), adapted to the user's current GLM/two-Spark instructions.
- Older attached ZIP revision 1.0 is superseded; its combined prompt and audit
  suggestions were not imported.
- Implemented: inventory, bounded local endpoint checks, paper/chapter source
  preparation and provenance, known-source fixture, local converter adapter,
  owned/context page windows, atomic attempts, resume integrity, resource sampling,
  HTML review links, unaccepted GLM proposals and result bundling.
- Locally validated: see VALIDATION.md. These tests used the authoring workspace,
  generated PDFs and mock HTTP/converter responses.
- Spark execution: **not run**. No SSH, GLM call, MinerU installation, OCR inference,
  Standard GPU runtime or source-fidelity benchmark has been performed by the
  authoring session.
- Next concrete user action: run the START-HERE preflight on the head Spark and
  return the produced upload ZIP. Preserve active benchmark work.
- Subsequent decision: actual isolated dependency lock, CPU Basic viability,
  local vision capability, resource window, then measured Basic/Standard choice.
- Later milestones: tested SQLite source backbone; one-paper assembled LaTeX;
  full-book worker; optional convenience interfaces. Cloud assistance is disabled
  for this probe by the user's current instruction.

Do not convert planned stages into accepted results without the corresponding
machine logs, source checks and reviewed output. No existing skill, wiki, model
server or benchmark environment was modified by preparing this package.

## 18 October 2026 — explicit optional OCR OS isolation

Operator design decision: OS network isolation is optional for OCR. This
supersedes earlier mandatory OCR namespace prose; design PDF and AGENTS.md are
unchanged. The operator explicitly selects local processing without an OS
network namespace for this trial. Local-only inference remains mandatory.
This decision does not change Codex sandbox/approval settings or host security.

Implemented `--ocr-isolation {namespace,none}` on preflight and convert.
Default/explicit namespace still fails closed on conversion namespace failure;
there is no fallback. Explicit none skips the availability probe and launches
the same local worker directly: "local processing; no OS network isolation".
Preflight records `deliberately_not_run` and null support rather than success.
Settings/fingerprints, attempt completion evidence, preflight summaries and
conversion reports retain the mode. Availability evidence is separate from
successful worker-launch evidence. Changed modes refuse resume before dispatch;
old runs and completed attempts are not migrated or rewritten. Existing code
fingerprints also mean older runs may require starting a new run.

The local MinerU SDK, cached/local model configuration, asset checks, empty
external endpoints, disabled LLM-aided stages, offline/telemetry settings and
best-effort Python guard remain in place. No memory thresholds or monitoring,
source/page-map integrity checks or unreviewed fidelity statuses were relaxed.
The Python guard is not an OS/native-code security boundary.

Observed validation in the existing sandbox using system `python3`:

- Five new dependency-free isolation tests passed, including preflight skip,
  default/explicit parsing, unavailable tools, stub-PDF/fake-worker conversion,
  persisted attempt mode, unchanged-attempt resume and cross-mode rejection.
  Stub orchestration is not PDF extraction or OCR validation.
- Four worker contract tests passed, including private local/offline settings and
  a Python audit-guard check before name resolution (without creating sockets).
- Full `python3 -m unittest discover -s tests -v`: exit 1; 40 discovered entries,
  23 passed, 17 errors. Two are module import failures (`test_cli` and
  `test_documents`) because `fitz`/PyMuPDF is missing. Fifteen HTTP test cases
  cannot create mock loopback sockets: PermissionError, errno 1, Operation not
  permitted. These are dependency/sandbox limitations, not a passing full suite.
  Added real-PDF CLI integration cases remain unexecuted until controller setup.
- `python3 -m compileall -q probe tests`, CLI convert help and `git diff --check`
  passed. All four registered source PDFs are present and match supplied hashes;
  no source content was exposed or changed.
- Read-only path checks: `.venv-control/bin/python`, `.venv-mineru/bin/python`
  and `model-cache` are absent. Neither runtime nor model readiness is established.

Historical evidence remains dated: the operator reports successful local GLM
endpoint preflight on 17 October, with failed namespace checks (unshare uid_map
and Bubblewrap loopback permission errors). That is not OCR/fidelity evidence
and was not repeated here. On 18 October, sandbox project-file operations passed;
external canary and Git probe writes were denied, with independent terminal
confirmation of unchanged/absent files. The operator reports the packaged
Bubblewrap AppArmor profile installed and loaded. None of this establishes an
OCR worker namespace or live OCR success. This task made no host/sandbox changes,
installed no dependencies, downloaded no models and ran no live GLM/OCR.

Next operator steps, from `/home/mdi/projects/pdf-to-latex`:

1. Separately authorise/execute `bash scripts/setup-basic.sh`. This creates the
   two owned project environments, installs pinned requirements, downloads and
   verifies Basic model assets, and saves setup logs/freezes. It does not run OCR.
   Preserve logs if ARM64 dependency/model preparation fails.
2. Run `.venv-control/bin/python -m unittest discover -s tests -v` in the operator
   terminal, where mock loopback sockets can be created. Review the real-PDF CLI
   tests before live inference. No repeated GLM preflight is needed for this option;
   retain the existing valid endpoint evidence and verify its actual alias against
   launcher information when using GLM later.
3. Check memory/workloads, then separately run only the first fixture trial:
   `.venv-control/bin/python probe.py convert --tier basic --ocr-isolation none --source fixture-native,fixture-scan`.
4. Open the printed run's `review.html` (for example
   `xdg-open runs/EXACT_CONVERSION_DIRECTORY/review.html`). The printed result
   ZIP is under `results/`, named `CONVERSION_DIRECTORY-upload.zip` (a unique
   suffix is used on collision). Preserve the run and ZIP. Inspect fixture
   mathematics/source fidelity before authorising the paper/selected chapter.
   A completed run remains unreviewed; full-book conversion is later work.

All changes remain unstaged. The pre-existing untracked task-instruction copy
`pdf-to-latex-codex-next-step.txt` was preserved.

## 18 October 2026 — review fixes: isolation evidence and converter interpreter

Follow-up review identified a reporting defect in the optional-isolation change:
the quality report reused availability-probe evidence and omitted actual worker
isolation results. It also identified a pre-existing executable-selection defect:
resolving the converter Python symlink could select system Python instead of the
prepared virtual environment. These findings qualify the earlier implementation
entry; its dated validation record is retained above.

Implemented fixes in `probe/cli.py`:

- HTML and quality JSON now separate the requested mode, namespace availability
  probe and worker evidence for each attempt. Successful execution through
  `unshare` supports the reported inference that this worker established a
  namespace; availability alone does not. A failed worker has unknown namespace
  establishment (`null`), because failure may occur after entering the namespace.
- Explicit none remains "local processing; no OS network isolation". Reports
  include earlier retried attempts and interrupted attempts without completion
  records. Missing historical evidence remains unknown. Existing attempt records
  are read without alteration; legacy false/unconfirmed values remain available
  as recorded evidence alongside the uncertainty-aware report interpretation.
- Converter executable selection expands `~` and makes relative paths absolute
  without following symlinks. The selected path is used for both runtime discovery
  and worker dispatch. Model/source/output containment checks remain unchanged.

Observed validation using system `python3` in the existing sandbox:

- `python3 -m unittest discover -s tests -p 'test_isolation*.py' -v`: exit 0,
  12 tests passed. Seven new regression cases cover both reports for namespace
  success, failure after a passing probe and explicit none; historical and
  interrupted attempts; preservation across retries; and real venv selection.
- The venv regression uses standard-library `venv.EnvBuilder(symlinks=True,
  with_pip=False)` in a disposable project-local temporary directory. It actually
  launches the selected interpreter and verifies `sys.prefix`, `sys.base_prefix`
  and `sys.executable`, including absolute, relative and home-expanded paths.
  It also checks that conversion passes the same preserved path to discovery
  and worker dispatch. No packages are installed; the temporary environment is
  removed. OCR dispatch is stubbed, and namespace execution is mocked.
- Full `python3 -m unittest discover -s tests -v`: exit 1, 47 discovered entries,
  30 passed and 17 errors. Two module imports fail because PyMuPDF (`fitz`) is
  absent; fifteen mock HTTP cases cannot create loopback sockets in the sandbox
  (PermissionError, errno 1). No additional application failures were observed.
  The real-PDF CLI tests, including their updated assertions, remain unexecuted.
- `python3 -m compileall -q probe tests` and `git diff --check` passed.
- `.venv-control`, `.venv-mineru` and `model-cache` remain absent; no disposable
  `test-venv-*` directories remain. No live OCR/GLM, namespace qualification,
  dependency installation, model download or setup script execution occurred.

Both reviewed defects are fixed with focused regression coverage. Full runtime
qualification and mathematical fidelity remain untested. The next operator steps
remain separate setup/download, followed by
`.venv-control/bin/python -m unittest discover -s tests -v` in the operator terminal
with mock loopback sockets available, then the explicit-none fixture-only trial
described above. Existing run fingerprints include code hashes, so these code
changes may require a new conversion run rather than resuming older code.

This follow-up changed `probe/cli.py`, `tests/test_cli.py`, added
`tests/test_isolation_reports.py`, and appended this checkpoint. Earlier work and
the untracked instruction copy were preserved. All changes remain unstaged;
AGENTS.md, host/sandbox settings and Git state were not modified.

## 18 October 2026 — stale preflight test arguments repaired

The operator reports completing setup and running 73 offline tests from the
normal terminal, with one error: the portable-fixture preflight test constructed
an incomplete `argparse.Namespace` without `ocr_isolation`. This is an
operator-reported result, not a successful full-suite result from Codex.

`tests/test_local_model.py` now constructs that test's arguments with
`cli.parser().parse_args(["preflight"])` and asserts that `ocr_isolation` defaults
to `namespace`. The mock HTTP server, mocked system operations, portable fixture
checks and existing assertions are preserved. Searching all tests found no other
direct `cmd_preflight` or `cmd_convert` invocation needing this repair. The manual
Namespace for `cmd_review` does not use the OCR isolation option and is unchanged.
No production code or defaults changed.

Observed validation with the now-present `.venv-control/bin/python`:

- Targeted portable-fixture preflight test: exit 1 because the sandbox denies
  creation of the mock server's loopback socket (`PermissionError: [Errno 1]
  Operation not permitted`). Execution stops before argument construction, so
  this test still requires confirmation in the operator's normal terminal.
- `-m unittest discover -s tests -p test_isolation.py -v`: all five tests passed,
  including parser defaults and mocked preflight behaviour.
- `git diff --check` passed. No missing-dependency error occurred in these checks.

Next operator check:
`.venv-control/bin/python -m unittest discover -s tests -v`.
The full suite was not repeated inside the sandbox for this focused repair.
No dependencies were installed, models downloaded, live OCR/GLM run, permissions
changed or Git state modified. Only this checkpoint and the stale test setup were
changed in this follow-up; all existing work remains unstaged.

## 18 October 2026 — saved portable export and bounded page-review pilot

The operator reports setup completed and all 73 earlier offline tests passed in
the normal terminal. This task inspected the saved run
`runs/convert-basic-20261018T182257Z-c99779`: both two-page fixture units are
completed, their output/input/page-map integrity checks pass, and their summaries
record MinerU 4.0.12 / DocVortex 0.5.16 with CPU ONNX Basic selected. This verifies
saved OCR execution evidence, not mathematical fidelity. No GLM document review
has been performed. The reported result ZIP is also present locally.

All 45 files in that completed run were hashed before and after this task;
membership and every file hash are unchanged. The SHA-256 of the canonical
path-to-hash mapping is
`ef0ae9abc7aea73b17df3e8cbe65db3dc5b80a9ff5a1b6c21f2a99f570a52149`.
Selected validation, bundle hashes and preview budgets are retained in
`docs/evidence/2026-10-18-portable-page-review.json`. Original conversion evidence
was not resumed, migrated or rewritten to match newer code fingerprints.

Implemented:

- `export --run ... --profile english-math` in `probe/cli.py`, backed by
  `probe/saved_pages.py` and `probe/portable_export.py`, creates a new portable
  derivative and ZIP from saved OCR. It validates original sources, completed
  attempts, page ownership and hashes, copies native evidence/assets, and records
  source/block/reading-order provenance. The installed renderer was inspected:
  its fixed CJK preamble and auxiliary-block filtering motivated a limited
  article-based profile. Recognized math is preserved without body rewrites.
  Unsupported content is explicitly unresolved with raw recognition and source
  images, rather than discarded to obtain a compiling draft.
- `review --mode pages --preview-only` prepares complete saved block data and
  per-block drafts, original pages, bounded math/aside/table detail images and
  explicitly selected rotated crops. `probe/page_review.py` implements input
  limits, exact request previews, sequential requests, strict reference/schema/
  completeness checks and full/partial/failed page coverage. Live page review
  requires the inspected preview, passing image/text preflight, an explicit exact
  model alias and fresh discovery. Proposals and failures are retained in a new
  run, with original OCR comparisons and source links. All proposals remain
  UNACCEPTED; none is applied. Candidate mode remains the default.
- The local client permits a separate explicit page-review output budget:
  8192 tokens by default, capped at 16384, with a default 300-second deadline.
  Existing tiny probe/candidate limits remain unchanged. The pilot permits four
  owned pages, 48,000 text characters per page, one full image plus four detail
  crops, 1 MiB/2 million pixels per image and a 2 MiB request. Overflow is rejected
  or marked incomplete without silently dropping content. The JSON schema stays
  in the prompt even if the API's optional response-format wrapper is unsupported.
- The writer lock remains in use. Review also checks visible same-user project
  converter processes; this is not host-wide exclusion. No service-management
  hooks were added. `docs/SPARK-OPERATIONS.md` records the operator-supplied
  launchers, separate OCR/GLM memory phases and exact commands. The low-memory
  observation with GLM resident is operator-reported, not a new measurement here.

Generated and inspected offline artifacts:

- Portable derivative:
  `runs/export-english-math-20261018T204408Z-59d26b/review.html` and
  `results/export-english-math-20261018T204408Z-59d26b-upload.zip`.
  Its four per-page article documents account for 34 blocks: 32 represented,
  two unresolved Unicode-bearing asides and zero silently omitted blocks.
  Raw asides and source-region images remain available. Label association,
  table structure, punctuation and uncertain transcription are evaluation
  targets; no fixture-specific repairs or corrected answers were inserted.
- Final page-input preview:
  `runs/review-input-20261018T204409Z-301420/review.html` and
  `results/review-input-20261018T204409Z-301420-upload.zip`.
  All four pages are ready, with four/five images per page and serialized request
  sizes of 154,313, 162,714, 187,808 and 162,623 bytes. The upright aside crop was
  visually inspected against its original page. The crop plan records geometry
  and rotation only, in `docs/fixture-review-crops.json`; the known fixture TeX
  and handwritten corrections never enter requests. Preview generation sends
  no requests. Earlier generated previews remain separate artifacts.

Observed validation in `.venv-control`:

- Twelve focused saved-export/page-review regression tests passed. They cover
  unchanged original evidence, movable derivative assets, omitted-aside
  accounting, complete block/inline/control inputs, overlap ownership, crop
  coordinates/transforms, exclusion of a synthetic gold-answer sentinel,
  strict proposal references/types, malformed/truncated responses, partial
  coverage, input overflow, changed evidence, process gating, separate token
  limits and absence of inference/service subprocesses in offline commands.
- Full `.venv-control/bin/python -m unittest discover -s tests -v`: 85 tests,
  70 passed, 15 errors. Every error is the sandbox's denial of mock loopback
  HTTP socket creation (`PermissionError: [Errno 1] Operation not permitted`).
  No missing dependencies or other application failures were observed.
- Compile checks, CLI argument parsing and `git diff --check` passed. Export,
  preview and the owned-converter check were exercised locally. Live review
  syntax was parser-tested without calling an endpoint.
- No `pdflatex`, `xelatex` or `lualatex` executable was found. Compilation is
  recorded as not run; no laptop compilation success is claimed. Actual GLM
  page vision, proposal fidelity, live timeouts/context capacity and performance
  remain untested. No current endpoint readiness claim is made from the saved
  17 October preflight, although it records `glm53-regular` with text and simple
  image checks passing. No `config.local.json` was present during inspection.

Next: the operator runs the full suite in the normal terminal, inspects the
derivative and final preview, confirms converter exit, starts regular GLM only
if necessary with the existing launcher, and runs a fresh explicit-model
preflight. Use its actual printed run path with the page-review command in
`docs/SPARK-OPERATIONS.md`. Return the four-page UNACCEPTED proposals for source
comparison before any acceptance or corrected derivative. Source fidelity and
newly introduced errors, rather than appearance or compilation alone, determine
the next decision.

This task changed README.md, START-HERE.md, this checkpoint, probe/cli.py and
probe/local_model.py; added probe/saved_pages.py, probe/portable_export.py,
probe/page_review.py, tests/test_saved_review.py, docs/SPARK-OPERATIONS.md,
docs/fixture-review-crops.json and the selected evidence JSON above. Prior work
was preserved. All changes remain unstaged. No service was started/stopped,
no live OCR or GLM inference, installation, model download, permission/security
change, Git mutation or proposal acceptance occurred.

## 18 October 2026 — preflight identity fix and morning fixture baseline

Bounded preparation completed against the existing working tree. In
`probe/local_model.py`, each preflight text, strict-JSON and image/control result
now requires exact agreement between its reported `actual_model` and the
discovered selected alias before that capability can pass. Mismatches retain
the reported identity, attempt path and raw response, with a diagnostic naming
both aliases. One mismatched image/control prevents vision qualification;
unrelated passing capabilities remain recorded. Existing page-review identity
checks are unchanged. Historical preflight records are not rewritten.

Four focused regressions in `tests/test_local_model.py` cover mismatched text,
JSON and every image/control response, plus matching-model success. They use
in-memory HTTP responses with the actual client parsing/evidence-writing path,
without sockets. Existing successful HTTP fixtures now return the selected
alias; the transport-only test still explicitly checks reporting a different
actual model. Earlier working-tree changes were preserved.

Added `docs/evidence/fixture-fidelity-baseline.md`, independently comparing both
saved fixture attempts with `fixtures/known-math.tex` and visual inspection of
all four original source pages and both prepared upright aside crops. Confirmed
shared errors are the missing comma after -1, F.3 attached to the expectation
instead of the expansion, detached F.4, and omitted rotated asides in native
TeX/Markdown. Structured native aside text loses spacing and script positions;
the scanned aside is more severely corrupted. Most prose, equation bodies,
conditions and numerical values appear preserved. The table retains values and
row association but is recognized as an equation with bare math-mode headers.
Table/cases rendering and human acceptance remain pending; no accuracy score or
compiled-output fidelity is claimed. The portable derivative retains unresolved
aside evidence, not an editable correction. No answer key, baseline or expected
correction was added to any model request.

`docs/SPARK-OPERATIONS.md` now gives a numbered morning sequence: terminal tests,
existing export/preview inspection, converter-exit check, conditional regular
GLM startup using the documented launcher, fresh explicit-model preflight,
four-page review, then open/bundle UNACCEPTED proposals. It requires inspecting
`vision: qualified`: preflight exit 0 means text success only. It captures the
actual printed new preflight path, without inventing a future run directory.
Optional regeneration and future OCR stop instructions are separate reference
material, not morning steps.

Observed validation in `.venv-control`:

- Full `python -m unittest discover -s tests -v` ran once: 89 tests, 74 passed,
  15 errors, exit 1. All four new identity regressions and all 12 saved-review
  tests passed. Every error was mock loopback socket creation denied by the
  sandbox (`PermissionError: [Errno 1] Operation not permitted`); no other
  application failures or missing dependencies were observed. The HTTP tests
  still require a normal-terminal run; this is not a passing full-suite claim.
- Compile checks and `git diff --check` passed. Saved source/output/page-map
  integrity passed for all four fixture pages. Source images were rendered only
  to temporary files for inspection.
- Before/after file membership and SHA-256 comparison matched for all 301
  snapshotted evidence files: 45 original conversion files, 43 portable-export
  files, 196 files in four existing previews, eight fixture files and nine
  result ZIPs. The final four-page preview and existing request bytes are intact.
- No `pdflatex`, `xelatex` or `lualatex` is available. Compilation, live GLM
  readiness/vision and proposal fidelity remain untested. No live GLM/OCR call,
  install, download, service action, permission change or Git mutation occurred.

Next operator command, from `/home/mdi/projects/pdf-to-latex` in the normal
terminal: `.venv-control/bin/python -m unittest discover -s tests -v`. Then
follow the numbered runbook; retain all proposals as UNACCEPTED for independent
source comparison. This task changed only `probe/local_model.py`,
`tests/test_local_model.py`, `docs/SPARK-OPERATIONS.md`, this checkpoint and the
new baseline. Every change remains unstaged; AGENTS.md and prior work are intact.

## 19 October 2026 — checkpoint review before first live four-page trial

Reviewed the tracked working-tree diff and relevant untracked source, tests,
runbook, crop plan and selected evidence. No concrete implementation defect was
found that should block this bounded fixture review. The checkpoint includes
the earlier optional-isolation/reporting/interpreter fixes, saved export/page
review, preflight identity validation and independent fidelity baseline. The
local instruction copy `pdf-to-latex-codex-next-step.txt` is excluded from the
proposed staging list; raw runs/results, environments, caches, input paper/book
PDFs and local configuration remain outside the checkpoint.

Read-only checks confirmed both requested run directories and their reports
exist. Saved source/output/page-map integrity passed for all four owned fixture
pages. The preview manifest, source-state hash and page coverage agree with the
conversion; all four saved request payloads match the current request builder
in memory, including the explicit `glm53-regular` alias and recorded budgets.
No preview or conversion evidence was regenerated or rewritten. All three ZIP
hashes recorded in the selected 18 October evidence JSON still match. The
paper/book inputs required by the existing preflight are present with matching
registered hashes. Python syntax parsing and `git diff --check` passed.

The full suite was deliberately left for the operator's normal terminal; the
latest recorded result remains 18 October's 74 passes and 15 sandbox socket
errors out of 89 tests. No test run, live discovery/inference, worker process
check, launcher invocation, service action or Git mutation was performed in this
checkpoint review. Only this dated state entry was added; prior work remains
unstaged. Endpoint readiness, mathematical vision and proposal fidelity remain
unqualified until the operator trial and independent source assessment.

Next: run `.venv-control/bin/python -m unittest discover -s tests -v`, then
follow `docs/SPARK-OPERATIONS.md` using the existing conversion and final preview.
Confirm OCR exit; start regular GLM only if needed. Require fresh `Text: passed`
and `vision: qualified`, capture the actual printed preflight path, and run the
four-page review. Open its report and retain its printed result ZIP. Keep all
proposals UNACCEPTED and the answer key/baseline outside model requests.
