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

## 19 October 2026 — first live review failed; native-only retry prepared offline

Inspected local operator-run evidence in
`runs/review-pages-20261019T215307Z-fafbf1`, using each page's
`attempts/*/response.raw` and the run's summary/provenance. All four pages
(`fixture-native-p0001`, `fixture-native-p0002`, `fixture-scan-p0001`,
`fixture-scan-p0002`) report the same outcome: model `glm53-regular`,
`finish_reason: length`, `completion_tokens: 8192`,
`completion_tokens_details.reasoning_tokens: 8192`, and assistant `content: null`.
The server-reported output allocation was entirely reasoning tokens, with no
final content. The saved summary is `review_incomplete`, coverage `failed`, zero
completed pages and zero proposals. This is live execution evidence, not a
successful document review or fidelity result. Raw failures remain untouched.

The existing `runs/preflight-20261019T215021Z-23ef86/model/capabilities.json`
reports text/strict JSON passed and vision qualified for the exact
`glm53-regular` alias at `http://192.168.1.100:8888/v1`; passing response identities
match. This was checked from saved records only, without contacting the endpoint.

Prepared a bounded retry using the existing offline CLI and original conversion
`runs/convert-basic-20261018T182257Z-c99779`. Added
`docs/fixture-native-review-crops.json` as the exact native-only subset of
`docs/fixture-review-crops.json`, including the original 90-degree upright
rotated-aside crop. The original crop plan was not changed. Preparation command:

```bash
.venv-control/bin/python probe.py review --mode pages --preview-only \
  --run runs/convert-basic-20261018T182257Z-c99779 \
  --source fixture-native --max-pages 2 \
  --page-max-tokens 16384 --page-timeout 600 \
  --model glm53-regular --base-url http://192.168.1.100:8888/v1 \
  --crop-plan docs/fixture-native-review-crops.json
```

New preview: `runs/review-input-20261019T220944Z-d96daa` (`review.html` is the
inspection report). New bundle:
`results/review-input-20261019T220944Z-d96daa-upload.zip`, SHA-256
`e26eaa76f68a1e9e527b012c6805ba075232cc831187c06cb33dc8cfb09386f6`.
The preview manifest SHA-256 is
`60bf59bb18b91ff050eecd368670f31da49c5a07f2d7d4c2737c38b769bcb458`.
**Retry status: prepared offline; NOT EXECUTED.** A larger output allowance is an
experiment, not a guarantee of final content or mathematical fidelity.

Verification passed:

- Exactly `fixture-native-p0001` and `fixture-native-p0002`, both ready; maximum
  pages 2, output limit 16,384 tokens and timeout 600 seconds per request. Other
  limits are unchanged. Page 1 has four images, 11,248 text characters and a
  154,314-byte serialized request; page 2 has five images, 10,743 characters and
  a 162,715-byte request.
- Against `runs/review-input-20261018T204409Z-301420`, both `page.json` files,
  every image/crop byte (including the upright aside), copied native evidence,
  prompt messages and response schema match exactly. The only per-page request
  difference is `max_tokens: 8192` becoming `16384`. The original native requests
  also match those saved by the failed live trial. No answer key or baseline was
  added to the requests.
- Original and new preview integrity checks and saved conversion/source/page-map
  checks passed. All 505 pre-existing snapshotted files retained their hashes;
  membership of each existing run stayed unchanged. Snapshot scope included all
  existing runs/results, fixtures, application/test files and the original crop
  plan. The only new result ZIP is the retry preview bundle.
- Live retry command syntax was parser-checked without execution. No application
  code changed; the full test suite was not rerun for this artifact-only task.
  No inference, MinerU run, installation, service action, proposal acceptance or
  Git mutation occurred. Changes remain unstaged; the local instruction copy is
  preserved.

Next operator action: run page review with the new preview, original conversion
and saved successful preflight above, explicitly selecting the same endpoint
and `glm53-regular`. Live review uses the preview's stored budgets, performs fresh
model discovery and saves new UNACCEPTED results separately. Keep all failed
trial evidence; do not resume or overwrite it.

## 19 October 2026 — explicit page reasoning effort; controlled low preview

The operator executed the previously prepared two-page retry as
`runs/review-pages-20261019T221132Z-e5f59b`. Local raw responses and proposal/summary
records confirm:

| Native page | Finish | Completion tokens | Reasoning tokens | Other completion tokens | Result |
| --- | --- | --- | --- | --- | --- |
| 1 | `length` | 16,384 | 16,384 | 0 | No final content; failed |
| 2 | `stop` | 15,528 | 14,695 | 833 | Final content; four UNACCEPTED proposals |

Other completion tokens are calculated as completion minus reasoning tokens.
Both responses identify `glm53-regular`. Run coverage is partial; zero proposals
were accepted. Page 2's valid response does not establish source fidelity. This
dated observation supersedes the previous entry's then-current “not executed”
retry status without altering that history or any run evidence.

Read-only local TensorFold inspection found `low`, `high`, `max` supported as
top-level `reasoning_effort` values in
`/home/mdi/local-llm/glm53-flash-tensorfold/README.md` (“Thinking and sampling”) and
`patches/0023-server-effort-max.patch`. The local template-support patch
`patches/0096-effort-tail.patch` was inspected, not applied. The regular-model
cached template at
`/home/mdi/models/tensorfold/huggingface/hub/models--Mia-AiLab--GLM-5.3-Flash-EXL3-4bpw-TensorFold/snapshots/078455ffe6472f9a52fbc1139f58b9db2881b25c/chat_template.jinja`
selects Low/High explicitly and Max otherwise (lines 2–3); the other present
snapshot `76c0b5173166d2795dd48860f45d8224817f894c` has the same effort logic.
This is local documentation/template support, not a live server qualification.
No server/config/template/launcher changes or execution occurred.

Implemented optional `--page-reasoning-effort` choices `server-default`, `low`,
`high`, `max` for `review --mode pages --preview-only`. New preview metadata
persists the selection. Omission/server-default sends no override, preserving
the old request behavior; old previews remain usable without changes. Explicit
efforts are written as a top-level field in prepared and actual serialized HTTP
requests. Preview validation rejects inconsistent metadata/request effort before
model discovery. Live review records the selection in provenance/summary and
uses only the saved selection; a CLI effort override requires a new preview.
Preflight and candidate requests are unchanged, and explicit overrides through
the client are restricted to page-review purpose.

Prepared a new offline preview, **not yet executed live**:
`runs/review-input-20261019T222910Z-d5cdbd`, with report `review.html`, from the
original conversion `runs/convert-basic-20261018T182257Z-c99779` and unchanged
native-only crop plan `docs/fixture-native-review-crops.json`. Settings: exactly
`fixture-native-p0001` and `fixture-native-p0002`, max pages 2, 16,384 generation
tokens, 600 seconds per request, explicit effort `low`. The saved successful
preflight `runs/preflight-20261019T215021Z-23ef86` matches the alias/endpoint and
reports text passed and vision qualified; it was read, not rerun.

Compared with `runs/review-input-20261019T220944Z-d96daa`, both page JSON files,
all page/detail/upright-aside image bytes, copied evidence, prompts and schema
match. The only per-page request change is `reasoning_effort: low`. All other
preview limits and crops match. Requests are 154,341 and 162,742 bytes, with
11,248/10,743 text characters and four/five images respectively. No fixture hints,
known-source answers or baseline corrections were added.

New bundle: `results/review-input-20261019T222910Z-d5cdbd-upload.zip`.
Bundle SHA-256:
`0369b5ac9d9ed6c212f33ce5de2fa3ca74e40c864ca53b351c47424c078ff816`.
Preview manifest SHA-256:
`247d1d48aacea15df513a3ee712fa988c0683d2b5bf5d74d0f23724c0c80dbc8`.

Offline validation:

- All 17 saved-review tests passed. Five new cases cover actual HTTP body
  serialization against saved requests for every effort choice, unsupported
  schema-wrapper handling, legacy previews, metadata/request consistency and
  invalid values/CLI scope. The real client writes evidence against an in-memory
  HTTP connection; no sockets or live requests are used in these tests.
- A new client regression rejects invalid efforts and non-page overrides before
  dispatch. Existing in-memory preflight tests also assert the field is absent.
  Full suite: 95 tests, 80 passed, 15 errors, exit 1. All errors are mock loopback
  socket creation denied by the sandbox (`PermissionError: [Errno 1] Operation
  not permitted`); no other application failures observed. Run
  `.venv-control/bin/python -m unittest discover -s tests -v` in the normal
  terminal for full confirmation; no permission changes were made.
- New/old preview integrity, exact request comparisons, Python syntax and live
  command parser checks passed. All 537 snapshotted pre-existing evidence files
  retained their hashes and original run membership: all existing runs/results,
  fixtures and both crop plans. Earlier trials, responses and proposals remain
  unchanged. No tests or checks apply or accept proposals.

Changed application files: `probe/cli.py`, `probe/local_model.py`,
`probe/page_review.py`; tests: `tests/test_local_model.py`,
`tests/test_saved_review.py`; documentation: `docs/SPARK-OPERATIONS.md` and this
state entry. Prior unstaged native crop-plan/state work is preserved. All changes
remain unstaged. No installation, OCR, live model call, service action or Git
mutation occurred. The low-effort effect on completion, latency and source
fidelity is still untested; the operator command is in the updated runbook.

## 19 October 2026 — completed low trial; controlled high preview prepared

Inspected the completed low-effort review
`runs/review-pages-20261019T223423Z-f95dcd` and its original preview
`runs/review-input-20261019T222910Z-d5cdbd`. Both native pages finished with `stop`
and response model `glm53-regular`; coverage is full, zero proposals accepted.
Page 1 reports 112 completion tokens (10 reasoning) and zero proposals; page 2
reports 1,545 completion tokens (917 reasoning) and four UNACCEPTED proposals.
These are execution results, not an assessment of the proposals' source fidelity.
The low run's actual retained HTTP bodies match its prepared requests exactly.
The earlier entry's then-current low-trial “not yet executed” status is retained
as history; this dated observation records its subsequent execution.

Using the existing CLI, prepared a NEW offline high-effort comparison:
`runs/review-input-20261019T224021Z-4aea11`. It uses the same original conversion
`runs/convert-basic-20261018T182257Z-c99779`, native-only crop plan
`docs/fixture-native-review-crops.json`, exactly two fixture-native pages,
16,384 generation tokens and a 600-second per-request timeout. The sole intended
request change is `reasoning_effort: low` to `reasoning_effort: high`.
**High comparison status: prepared offline; NOT EXECUTED live.**

Offline validation passed:

- Preview manifests and source/attempt checks pass. Every high request body
  equals its low counterpart after changing only `reasoning_effort`. All other
  fields, including prompt/instructions, OCR drafts, page data, image content,
  schema, model and generation budget, are identical. Both `page.json` files,
  source/detail images (including the upright aside), and copied native evidence
  are byte-identical. All limits, source provenance and crop metadata match.
- Page 1 has four images, 11,248 text characters and a 154,342-byte request;
  page 2 has five images, 10,743 characters and a 162,743-byte request. The one-byte
  increase per request is the longer effort string, not a changed prompt.
- All 641 snapshotted pre-existing files retained their hashes; original run
  membership is unchanged. Scope includes every existing run/result, fixtures,
  application/tests and both crop plans. Low results and all earlier evidence
  remain untouched. The existing preflight
  `runs/preflight-20261019T215021Z-23ef86` still records passing text and qualified
  vision for the intended endpoint/alias; it was read without a network call.
- The live-review command was parser-checked only. `git diff --check` passed.
  No application/test changes were made and the full suite was not rerun for
  this artifact-only preparation. Live high-effort behavior and low/high fidelity
  comparison remain untested.

New report: `runs/review-input-20261019T224021Z-4aea11/review.html`.
New bundle: `results/review-input-20261019T224021Z-4aea11-upload.zip`.
Bundle SHA-256:
`5899824c811d881b5f68796f43933d1656bccd95d5c508dcec62b08a8aa7185d`.
Preview manifest SHA-256:
`5c0ce0cd761f09449a321e4358f4241853aca811635adf90d3b01416983aa647`.

Updated only this state entry and the current-trial section of
`docs/SPARK-OPERATIONS.md`, plus the newly generated preview and ZIP. Existing
unstaged work is preserved. No live model request, service action, installation,
MinerU run, proposal acceptance or Git mutation occurred. All changes remain
unstaged. Next: the operator runs the high preview with the existing preflight,
then opens the printed report path and retains the printed result ZIP for
independent comparison with low; neither set of proposals is automatically applied.

## 20 October 2026 — explicit acceptance derivative and focused follow-up

Read AGENTS.md and the required handover/operator documents before changes.
This bounded milestone adds explicit selection/application of saved whole-page
proposals and a selected-region review experiment; it does not implement the
full-book application, automatic repairs or chapter assembly. Dates here use
Europe/London; generated run names below use 19 October UTC.

The completed high review `runs/review-pages-20261019T224212Z-e0f284` supersedes
the preceding historical “not executed” status. Both native pages returned
`stop` with exact model `glm53-regular`, using
`runs/review-input-20261019T224021Z-4aea11`. Page 1 took 13.405 seconds, used 543
completion tokens (441 reasoning, 102 other), and proposed nothing. Page 2 took
33.448 seconds, used 1,895 completion tokens (1,153 reasoning, 742 other), and
supplied four proposals. Summed request latency is 46.853 seconds. Raw responses,
parsed proposals, actual requests and source/preview bindings agree. The earlier
low review `runs/review-pages-20261019T223423Z-f95dcd` and all previous runs remain
unchanged. Full block coverage is not source-fidelity qualification: page 1 missed
the missing comma between −1 and 1/252 and bare-word table headings inside maths.

Implemented:

- `accept-plan` creates a hash-bound, initially unselected proposal catalog.
  `apply-accepted --plan ...` requires explicit authorization and selections,
  exact source/review/preview bindings and stable proposal/target IDs. It rejects
  stale evidence, unknown targets, conflicting edits and partial correction groups
  before export. Only single-block replacement and explicit deletion are supported;
  missing-region insertion, merges/splits, multi-block edits and unsupported TeX
  are deferred. Groups are explicitly declared, not inferred from model confidence.
- The user explicitly authorized page-2 b0/b3/b4/b5. The saved plan
  `docs/evidence/fixture-native-acceptance.json` records b3/b4/b5 as one atomic
  group. b0 restores the rotated aside; b3 gets F.3, b4 gets F.4, and b5 is an
  explicit deletion. Proposal text is taken verbatim from the bound high review.
  Original proposal files are untouched and retain their UNACCEPTED status;
  acceptance is separate. `uncertain: false` does not authorize edits.
- The portable renderer reuses conservative math validation and package selection,
  with a narrow validated prose/inline-math/right-angle rotatebox replacement
  grammar. It preserves every other block and its order, records before/after
  fragments and deletion, and retains original source/native evidence. It is not
  a general TeX sandbox or a proof of compilation/fidelity.
- `review --mode regions` uses an explicit one-to-four-block selection, derivative
  drafts, a full-page context image and per-region source crop. Adjacent OCR is
  context only. The new schema requires `scope: selected_blocks`; successful
  coverage is `selected_regions_complete`, never full-page coverage. Whole-page
  mode, older previews, identity checks and preflight behavior are preserved.
  Focused-response acceptance is deferred; all live outputs remain UNACCEPTED.

Created derivative `runs/accepted-derivative-20261019T230916Z-969d30` with
`review.html`, `acceptance.json`, `provenance.json`, `inventory.json`, source
images and `pages/fixture-native-p000{1,2}/document.tex`. All 17 native blocks are
accounted for: 13 unchanged, three replaced, one explicitly deleted, zero silent
omissions. Page-1 TeX is byte-identical to the original portable export. Its two
known defects remain recorded as unresolved; no fixture-key repairs were applied.
The original high review is copied byte-for-byte under `review-evidence/`, with
the upright aside crop still available. Movable bundle:
`results/accepted-derivative-20261019T230916Z-969d30-upload.zip`.

Prepared **offline only; NOT EXECUTED live**:
`runs/review-regions-input-20261019T230924Z-93edf1`, selected by
`docs/fixture-focused-blocks.json`: native page-1 b1 (inline-math paragraph), b4
(table), b2 (unchanged F.1 control), one request per region. Each uses high effort,
16,384 generation tokens, 600 seconds and two source images. Their drafts match
the original high preview exactly; full-page image bytes and the existing table/
control crops match. Crops were visually inspected locally for usable source
content. The generic instructions check punctuation, symbols, conditions, units
and rendered meaning, including ordinary text in maths. No gold fixture TeX,
expected answers, baseline or human acceptance/issue notes enter the requests.
The inspection report is `review.html`; exact requests are under
`pages/fixture-native-p0001-b{1,4,2}/request.json`. Bundle:
`results/review-regions-input-20261019T230924Z-93edf1-upload.zip`.

Validation:

- Full controller suite: 111 tests; 95 passed, 15 mock HTTP tests denied at
  loopback `socket.socket()` creation (`PermissionError: [Errno 1] Operation not
  permitted`), one existing assertion failed on updated CLI diagnostic wording.
  Corrected that wording; the targeted saved-page suite then passed all 17 tests.
  Thus 96 distinct tests passed across these runs; 15 remain sandbox-blocked.
  All 16 new acceptance/focused tests passed in the full run. They cover binding,
  stale/raw-conflicting evidence, unknown/conflicting edits, atomic groups,
  explicit deletion, preservation, unsupported operations, selection/no answer
  leakage and real outgoing serialization over an in-memory HTTP connection.
  This is not a fully passing normal-terminal suite or evidence of model accuracy.
- `.venv-control/bin/python -m compileall -q probe tests` and `git diff --check`
  passed. Actual CLI creation commands succeeded offline. The live command was
  parsed only; the saved preflight still reports text passed, vision qualified,
  exact `glm53-regular` and endpoint `http://192.168.1.100:8888/v1`.
- Both new manifests, exact request/draft bindings, inventory order, explicit
  deletion, ZIP CRC/content membership and local HTML links passed checks.
  All 771 pre-existing evidence files across 19 roots kept their byte hashes;
  old run membership is unchanged, including the four specified source/high/low
  evidence paths. Original source inputs, all earlier runs and ZIPs remain intact.
- No TeX executable was found (`pdflatex`, `xelatex`, `lualatex`, `tectonic`,
  `latexmk`); compilation is **not run**, no TeX installed. Compile a separate
  laptop copy as documented, preserving the sealed Spark derivative. Focused GLM
  behavior is untested live. No inference, MinerU, service actions, downloads,
  dependency installation, sandbox changes or Git mutations occurred.

Exact hashes and the readable comparison/experiment record are in
`docs/evidence/accepted-fixture-followup.md`. The current operator sequence,
actual report/TeX/ZIP paths, separate laptop compilation and exact live command
are in `docs/SPARK-OPERATIONS.md`. Next operator command:
`.venv-control/bin/python -m unittest discover -s tests -v` in the normal terminal,
then inspect the derivative/preview, check converter exit and run the prepared
focused review using the saved successful preflight
`runs/preflight-20261019T215021Z-23ef86` (or fresh evidence after a server change).

The registered book is still Boyarchenko/Levendorskii Chapter 3: 30 pages,
original physical 89–118 / printed 67–96, forced OCR. Its selected PDF hash
`3f56ca665560dcf21f2fc09845812f353e22bf4c9c284de526a5d0abd25bcc46` and 30-page count
were verified. After inspecting this experiment and laptop PDFs, the proposed
next trial is that existing chapter selection with Basic in an operator-arranged
OCR memory phase, then a bounded saved-page review sample. No chapter work was
launched and the full 421-page book is not the registered input.

Files changed by this milestone: `probe/acceptance.py`, `probe/focused_review.py`,
`probe/cli.py`, `probe/page_review.py`, `probe/portable_export.py`,
`tests/test_acceptance_focus.py`, `README.md`, `START-HERE.md`,
`docs/SPARK-OPERATIONS.md`, `docs/PROJECT-STATE.md`,
`docs/evidence/fixture-native-acceptance.json`,
`docs/evidence/accepted-fixture-followup.md`, `docs/fixture-focused-blocks.json`,
plus the two new runs and two ZIPs above. Prior unstaged reasoning-effort changes,
tests, native crop plan and unrelated operator text are preserved. Everything
remains unstaged; AGENTS.md is unchanged. Bounded milestone complete; awaiting
operator tests, laptop compilation and the focused live experiment.

## 20 October 2026 — Klebaner chapters 4–7 prepared; conversion not run

The user explicitly authorized preparation of an additional 120-page selection
from Klebaner, *Introduction to Stochastic Calculus with Applications*, second
edition. Read AGENTS.md, the required handover/current-state documents, README,
relevant START-HERE instructions and the existing `probe.documents.prepare_source()`
implementation. No application features or code changes were needed.

Verified `inputs/klebaner-original/source.pdf` before preparation: 431 pages,
unencrypted PDF, SHA-256
`4df3fd75e2c040875bb14d4540caaced3eefd5a836f0419837e619abd3c72934`.
The destination did not exist. Called the existing preparation workflow once,
with original physical pages 106–225 inclusive and label `klebaner-ch4-7`, creating
`inputs/klebaner-ch4-7` with its selected PDF, manifest, native character/text
records and page previews. Original input and completed preparation evidence
were not overwritten.

| Chapter | Original physical PDF pages | Selected pages | Count |
|---|---|---|---:|
| 4 | 106–137 | 1–32 | 32 |
| 5 | 138–163 | 33–58 | 26 |
| 6 | 164–197 | 59–92 | 34 |
| 7 | 198–225 | 93–120 | 28 |

The operator-supplied printed-page span is 91–210. Native text corroborates the
chapter openings at physical pages 106, 138, 164 and 198, with printed numbers
91, 123, 149 and 183, and the final selected page's 210. Physical page 226 begins
Chapter 8 and is excluded. Pages 137 and 197 contain “This page intentionally
left blank”; both remain selected, at positions 32 and 92. Catalogue labels and
per-page printed labels remain as recorded by the existing workflow; no invented
labels were inserted into its manifest.

Registered the separate `sources.json` entry `klebaner-ch4-7` with:

- `pdf: inputs/klebaner-ch4-7/source.pdf`, `pages: 120`;
- `original_pages`: every integer from 106 through 225, in order;
- `manifest: inputs/klebaner-ch4-7/manifest.json`;
- prepared-selection SHA-256
  `61102519b11535ee11e817d7b6f5b357e87435429b231c144c0e82f6dc6f80e4`;
- `ocr_mode: auto`, explicitly requested because the PDF contains native text and
  fonts. All 120 selected pages have native text and fonts; the preparation
  heuristic classifies none as image-backed or OCR-recommended. These are routing
  observations, not mathematical-fidelity validation. The existing `book` entry
  remains forced `ocr`; all four earlier source entries are unchanged.

Validation passed:

- Original hash/page count rechecked; selected PDF count is exactly 120.
  The full 431-page scope ledger, all 120 selected-page records and registration
  agree on the original physical-page mapping, including both separators.
- Every selected page's native text, geometry and rendered pixels at 72 dpi match
  its corresponding original page. All 242 manifest-referenced artifact hashes
  and sizes match (selected PDF, metadata, 120 native records, 120 previews).
- Existing `probe.cli.selected_sources('klebaner-ch4-7')` validates the prepared
  PDF hash and returns only the new source. `selected_sources('all')` validates
  all five registered sources. Supplemental page-count/ledger checks cover facts
  beyond that loader's hash validation. The final conversion command parsed
  successfully; it was not executed.
- All 10 existing document-preparation tests passed with
  `.venv-control/bin/python -m unittest discover -s tests -p test_documents.py -v`.
  No mock socket tests or full-suite rerun were needed for this registration-only
  change. `git diff --check` passed.
- Git ignore checks confirm all 245 original/selection/evidence files are ignored
  by the unchanged `/inputs/` rule; no files in either Klebaner input directory
  are tracked. The new preparation contains 244 files, including a separate raw
  `preparation-validation.json`. All 1,274 snapshotted pre-existing input, run,
  result and fixture files retain their hashes; old run/result membership is
  unchanged. Application code, tests and AGENTS.md are unchanged.

Small provenance record: `docs/source-provenance/klebaner-ch4-7.json`, including
chapter ranges, original/selected hashes, manifest hash, routing rationale and
checks. This task changes only `sources.json`, that new provenance record, this
state entry and the new ignored preparation directory. Existing unrelated
unstaged work is preserved; all changes remain unstaged. No Git metadata,
permissions, services or dependencies were changed. No OCR or GLM inference ran.

Next operator step, in the normal terminal after arranging the documented OCR
memory phase, converts only the new selection:

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python probe.py convert \
  --source klebaner-ch4-7 --tier basic --ocr-isolation none
```

This selects local MinerU Basic with the saved `auto` routing and explicit local
processing without an OS network namespace. Existing memory gates remain in
force. It creates a new conversion run/result ZIP and leaves prior sources/runs
alone. Preparation does not establish conversion success or transcription fidelity.

## 20 October 2026 — Flash Next Klebaner region experiment prepared offline

Read AGENTS.md, required handover/state/README/START-HERE sections and the operator
instructions. The requested saved conversion
`runs/convert-basic-20261020T075104Z-48fd90` now exists and records
`conversion_completed_unreviewed`: all 15 windows and 120 owned Klebaner pages
passed the existing saved-source/output/hash/page-map validation. This supersedes
the preparation-only status above; it does not establish OCR fidelity. No OCR
was run or resumed in this task.

The requested preflight `runs/preflight-20261020T181856Z-070d9b` records passing
text, all four simple vision controls passed, and `vision: qualified` for the
exact alias `flash-next-tensorfold` at `http://127.0.0.1:8890/v1`. Strict JSON
remains **unsupported**, with its raw HTTP 400 reporting missing xgrammar.
The existing review dispatch already omits `response_format` for this case
while retaining the full response schema in the prompt and validating returned
JSON locally. Model identity, completion, schema, block references, selected
coverage and evidence checks are unchanged. Preflight code/results are unchanged.

Two concrete preparation gaps were found: focused mode required an accepted
derivative, which this conversion does not have, and the damaged equation fails
the conservative export renderer. Added a narrow saved-OCR branch to the existing
focused machinery: `--derivative` is optional when preparing regions with an
explicit `--source`; source drafts are regenerated and checked against the bound
saved evidence. Renderer-rejected equation content can be supplied verbatim as
untrusted comparison data inside display delimiters. Export validation is not
relaxed, and non-equation blocks without usable drafts still fail explicitly.
No acceptance record is manufactured. Old derivative previews and whole-page
mode retain their behavior. The raw-OCR prompt explicitly requests complete
source-faithful replacement LaTeX when warranted, with no repair of author errors.

New offline preview: `runs/review-regions-input-20261020T185019Z-5a9907`.
Report: that directory's `review.html`. Bundle:
`results/review-regions-input-20261020T185019Z-5a9907-upload.zip`.
Selection: `docs/klebaner-flash-next-blocks.json`, containing only three IDs:

| Request | Printed / original physical / selected page | Selected block |
|---|---|---|
| Paragraph with visible OCR defects | 91 / 106 / 1 | `klebaner-ch4-7-p0001:b4` |
| Damaged nested exponential/integral | 155 / 170 / 65 | `klebaner-ch4-7-p0065:b14` |
| Independently visually checked equation (4.1) control | 91 / 106 / 1 | `klebaner-ch4-7-p0001:b7` |

Source printed page numbers, crop contents and control transcription were
visually checked. Each request includes the full source page for context,
neighboring OCR blocks, its source crop and exact saved draft. The selection
contains no diagnoses, expected answers or control labels. The independent
assessment `docs/evidence/klebaner-flash-next-experiment.md` records findings,
budgets and hashes; it is not a request input. Coverage is selected blocks only.

Explicit settings: `reasoning_effort=high`, `max_tokens=16384`, timeout 600
seconds, `stream=false`, three serial requests over two pages. Read-only local
Flash Next README/recipe inspection documents top-level high effort support
and identifies the Qwen3.8 Flash Next model behind this user-authorized alias.
Launcher files record thinking enabled and sampling defaults; these are not a
live configuration audit. Sampling/template overrides are not added to the
client. Every request fits existing character, image and 2 MiB request limits.
The canonical offline requests retain the schema wrapper; the supplied
preflight causes only `response_format` to be removed at live dispatch.

Validation:

- 21 acceptance/focused tests passed, including five new saved-OCR tests; all
  17 saved-page tests passed, for 38 relevant offline regressions. New checks use
  the real client's serialization with an in-memory transport, proving wrapper
  omission/schema retention and rejection of malformed JSON, wrong scope/block/
  model and truncated responses. Changed draft evidence fails before discovery.
  No live endpoint or sockets were used by these checks.
- Python compilation and `git diff --check` passed. The full suite was not rerun;
  previously documented mock loopback socket restrictions remain a reason to
  run it in the normal terminal. No sandbox permissions were changed.
- New preview manifest/source/draft/request verification passed. Independently
  rerendering from the original conversion reproduced all six image hashes.
  The old accepted-derivative preview
  `runs/review-regions-input-20261019T230924Z-93edf1` still validates unchanged.
- All 2,452 snapshotted pre-existing files across input/fixture/run/result roots
  retain their hashes, and old run membership is unchanged. `sources.json`,
  AGENTS.md, acceptance code, exporter validation and local-model/preflight code
  are unchanged by this task. New raw preview/results remain ignored by Git.

Files changed by this preparation: `probe/focused_review.py`, `probe/page_review.py`,
`probe/cli.py`, `tests/test_saved_ocr_focus.py`,
`docs/klebaner-flash-next-blocks.json`,
`docs/evidence/klebaner-flash-next-experiment.md`, `docs/SPARK-OPERATIONS.md`,
and this state document, plus the new ignored preview and ZIP. Prior unrelated
unstaged work remains intact. No Git metadata, services, installations, inference
or TeX compilation were performed. No new proposals exist yet; all eventual
proposals remain UNACCEPTED. There is no remaining offline preparation blocker,
but live response behavior and mathematical fidelity are untested.

Next operator step after normal-terminal tests and preview inspection:

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python probe.py review --mode regions \
  --run runs/convert-basic-20261020T075104Z-48fd90 \
  --preview runs/review-regions-input-20261020T185019Z-5a9907 \
  --preflight runs/preflight-20261020T181856Z-070d9b \
  --base-url http://127.0.0.1:8890/v1 --model flash-next-tensorfold
```

This exact live command is **displayed only, not executed**. Operator instructions
explain converter-exit checking, report opening and locating the automatically
bundled result ZIP using the actual run path printed after execution.

## 20 October 2026 — paragraph-only medium-effort follow-up prepared

Inspected the operator's `runs/review-regions-20261020T185933Z-7075bd` and verified
its source, original preview and preflight bindings. The failed region is
`klebaner-ch4-7-p0001:b4` (printed 91 / original physical 106 / selected 1).
Its raw response reports exact model `flash-next-tensorfold`,
`finish_reason: length`, 16,384 completion tokens, all 16,384 reasoning tokens,
and `content: null`. The diagnostic repeatedly questions whether OCR-derived
content or the images are authoritative. The validator correctly retained the
raw failure without producing a paragraph proposal.

The original run's other two regions completed: one UNACCEPTED proposal for
the nested display, none for the control. Coverage remains partial and fidelity
unreviewed. These results and all preceding runs/proposals remain unchanged;
this task does not assess or accept the completed proposal.

Clarified the generic focused-review prompt: original source images are
authoritative; `native.content`, neighboring OCR and `draft_by_block` are
potentially erroneous OCR-derived comparison material. Correct OCR using the
images, preserve only errors actually printed in the source, and mark unreadable
details uncertain instead of guessing. No specific correction or diagnostic is
included. New focused previews record prompt version 2. Unversioned historical
previews retain the exact original wording and remain usable. Unknown versions
or inconsistent prompt/data bindings fail before discovery.

Added `medium` to the existing page-review effort choices, serialization and
validation tests. Read-only local Flash Next deployment documentation explicitly
supports this value. Capability preflight still cannot receive an effort override;
its behavior and saved results are unchanged. Whole-page instructions, response
schema/validation, exact-model checks, evidence validation and acceptance rules
are intact. No server or dependency changes were needed.

Prepared **but did not execute**:

- Preview: `runs/review-regions-input-20261020T191957Z-311b42`.
- Report: `runs/review-regions-input-20261020T191957Z-311b42/review.html`.
- ZIP: `results/review-regions-input-20261020T191957Z-311b42-upload.zip`.
- Selection: `docs/klebaner-paragraph-retry-blocks.json`, containing only b4.
- Independent assessment/hashes: `docs/evidence/klebaner-paragraph-retry.md`,
  which is not a model input.

Settings remain the same endpoint `http://127.0.0.1:8890/v1` and exact alias
`flash-next-tensorfold`, 16,384 generation tokens, 600-second timeout and
`stream=false`, now with explicit medium effort. The preview selects one page
and one request, with 9,084 prompt characters and two images. The prepared body
is 381,269 bytes; unsupported strict-JSON dispatch omits only `response_format`,
leaving 380,319 bytes and retaining the prompt schema. Sampling inherits server
settings. Simple-control vision qualification does not certify transcription.

Validation passed:

- 42 relevant offline tests: 24 acceptance/focused, 17 saved-page and one client
  effort-validation test. New coverage checks medium on the actual serialized
  request using an in-memory transport, source-authority instructions, preservation
  of input data, legacy prompt compatibility and version mismatch rejection.
  Existing malformed JSON, scope, block-ID, model and truncation checks pass.
- Python compilation and `git diff --check` passed. The full suite and mock socket
  tests were not rerun. The normal-terminal full-suite command remains
  `.venv-control/bin/python -m unittest discover -s tests -v`; no permissions
  were changed to bypass previously documented sandbox socket restrictions.
- Compared the retry with both original preview and failed live request:
  source/crop bytes, OCR drafts, neighboring blocks, page mappings and response
  schema are identical. Only the generic instruction prefix and effort field
  change in the model request. An internal version field is added to preview/page
  metadata, not to model comparison data. No known corrections are introduced.
- New preview/source/request validation and ZIP verification passed. Original
  Klebaner and accepted-fixture focused previews still validate unchanged under
  the updated code. All 2,703 snapshotted pre-existing input, fixture, run and
  result files retain their hashes; old run membership is unchanged.

Changed files this task: `probe/local_model.py`, `probe/page_review.py`,
`probe/focused_review.py`, `tests/test_local_model.py`, `tests/test_saved_review.py`,
`tests/test_saved_ocr_focus.py`, `docs/klebaner-paragraph-retry-blocks.json`,
`docs/evidence/klebaner-paragraph-retry.md`, `docs/SPARK-OPERATIONS.md` and this
state document, plus the ignored new preview and ZIP. Unrelated work, AGENTS.md,
source registration, original selection and earlier evidence summaries are
preserved. Everything remains unstaged; no Git metadata, services, dependencies,
OCR or live inference were changed/run. Medium-effort completion and fidelity
remain untested. All future proposals remain UNACCEPTED.

Next operator command (displayed only, not executed):

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python probe.py review --mode regions \
  --run runs/convert-basic-20261020T075104Z-48fd90 \
  --preview runs/review-regions-input-20261020T191957Z-311b42 \
  --preflight runs/preflight-20261020T181856Z-070d9b \
  --base-url http://127.0.0.1:8890/v1 --model flash-next-tensorfold
```

## 20 October 2026 — resumable 100-page Klebaner batch prepared offline

Read AGENTS.md, handover/state/README, relevant START-HERE sections and the
operator runbook; inspected the existing saved-page, focused, client, validation,
locking and bundle machinery before extending it. The user explicitly authorized
this 100-page batch and its necessary project changes. No inference, OCR,
installation, server/service operation, permission change or Git mutation occurred.

Verified the existing conversion `runs/convert-basic-20261020T075104Z-48fd90` and
selected exactly the first 100 distinct owned `klebaner-ch4-7` pages: selected
1–100, original physical 106–205, preserving all 1,623 block IDs and native order.
Overlap/context pages do not increase that count. Original pages 137 and 197 are
included separators. The final source page visibly shows printed 190. The copied
13 source windows retain their original context, including pages beyond the
review selection; those are not claimed as reviewed.

The earlier three-region review `runs/review-regions-20261020T185933Z-7075bd`
remains partial. The operator's paragraph retry
`runs/review-regions-20261020T192708Z-997831` completed with matching model,
`finish_reason: stop`, 3,011 completion tokens (2,353 reasoning / 658 other),
46.02 seconds and one UNACCEPTED proposal. Its provenance bindings passed checks.
That success establishes a completed validated response, not independent fidelity.
Neither those proposals nor diagnoses/expected answers are used as batch inputs.

Implemented a separate `review-batch` path, preserving the four-page and focused
modes. Its sealed offline plan records explicit page/block/visual coverage,
immutable requests and budgets. Nine pages use whole-page review. The remaining
91 pages have 296 bounded block groups plus 91 full-page omission checks: **396
requests total**. All 1,623 blocks are assigned exactly once, including headers,
page numbers and unsupported/unresolved drafts. Visual checks inspect complete
pages and overlapping high-resolution halves, including margins and regions
outside OCR boxes. Dense groups preserve native order, have full-page context
and readable union crops, and split further on overflow. Unsplittable overflow
fails preparation explicitly instead of discarding text or images.

Batch prompts carry the successful source-authority clarification and general
source-faithful correction instructions. Source images establish what is printed;
OCR/drafts may be wrong. Printed author errors are preserved, unreadable details
are uncertain, and known answers remain outside requests. Settings are exact alias
`flash-next-tensorfold` at `http://127.0.0.1:8890/v1`, medium effort, 16,384 output
tokens, 600-second timeout, serial execution, no sampling overrides. Strict JSON
may be unsupported: only the API wrapper is omitted, while prompt schema and
local JSON/scope/block/model validation remain enforced.

Prepared, **not executed**:

- Preview: `runs/review-batch-input-20261020T195337Z-32f118`.
- Report: `runs/review-batch-input-20261020T195337Z-32f118/review.html`.
- ZIP: `results/review-batch-input-20261020T195337Z-32f118-upload.zip`.
- Independent record: `docs/evidence/klebaner-100-page-batch.md`.

The preview is 373,446,958 bytes; ZIP is 300,341,555 bytes. Maximum request is
857,621 bytes, maximum prompt 17,880 characters and maximum images three, within
existing request/image limits. Complete preview/source/draft/request/coverage
verification passed, and all ZIP entries match the preview. Previously rendered
page-1/page-65 source-image hashes match. Representative source crops and the
final page were inspected visually; no full manual transcription review is claimed.

The live executor persists reservations before dispatch, seals outcomes/raw
evidence, then checkpoints counts, elapsed execution time, report and coverage.
Unattempted work precedes one retry pass. At most two dispatch attempts per unit
are retained across every resume, including interruptions. Validated saved answers
recover without resending; unfinished attempts remain evidence and consume budget.
Successful work is skipped. Isolated failed units do not stop other work. Two
consecutive connection failures pause, including timeouts after HTTP 200 headers;
discovery unavailability pauses without chat. Changed identity or detected evidence
integrity failure stops. Resume refuses changed source, prepared requests,
preflight, explicit model or client settings. No retry reset or automatic repair
loop is implemented.

The page-grouped report links source images, original drafts, attempts and
UNACCEPTED proposed corrections, and records unresolved issues and coverage gaps.
Page completion requires both all block units and the visual omission check; it
does not mean mathematical correctness. `batch-status` bypasses the writer lock
for read-only monitoring. `report` handles batch runs, and the existing append-only
ZIP behavior supports paused/partial/completed snapshots without replacing old ZIPs.

Validation:

- Final full suite: **133 tests, 118 passed, 15 errors**, all errors caused by
  sandbox-denied mock HTTP socket creation (`PermissionError`, errno 1).
  No application assertion failures occurred. No permission changes were made.
- All 14 new batch tests passed, covering exact owned selection, coverage gaps/
  duplicates, dense splitting, blank recognition, overflow rejection, actual
  client serialization using in-memory HTTP, answer exclusion, resume/skip,
  persistent retry limits, connections/timeouts, interruptions/recovery,
  model mismatch, stale evidence, concurrent status and partial bundles.
- Python compilation and `git diff --check` passed. Earlier focused previews
  remain valid. All 2,809 snapshotted pre-existing input, fixture, run and result
  files retain their bytes and original run membership is unchanged. AGENTS.md,
  existing source registration, acceptance/export validators, preflight code,
  historical requests and proposals are unchanged. New raw artifacts are ignored.

Changed files this task: `probe/batch_inputs.py`, `probe/batch_review.py`,
`probe/cli.py`, `tests/test_batch_review.py`, `README.md`, `docs/SPARK-OPERATIONS.md`,
`docs/evidence/klebaner-100-page-batch.md` and this state document, plus the new
ignored preview/ZIP. Prior unrelated working-tree edits remain intact; everything
is unstaged. Long-running live behavior, mathematical accuracy, inherited server
sampling/weight stability and TeX compilation are not certified by offline checks.

The runbook now gives the exact normal-terminal test/OCR-exit/model-discovery/
fresh-preflight commands, use of the actual prepared preview, optional offline
re-preparation, live launch, monitoring, resume and partial/completed ZIP steps.
Installed `tmux` 3.4 and `watch --exec` were checked read-only. The launch runs
inside tmux to survive remote-desktop disconnect; no tmux session was started here.
The user must retain the **actual new preflight directory** printed by their
preflight and require Text: passed plus vision: qualified. The existing preflight
`runs/preflight-20261020T181856Z-070d9b` stays unchanged. No future preflight/live
run directory is invented. All live commands are displayed only for the operator.


## 21 October 2026 — completed 100-page batch audited offline

Completed the bounded audit requested in `01-batch-audit.txt`. Read project
instructions/handover/current state/README/operator documentation and relevant
START-HERE sections. Preserved historical entries and all existing work.

Actual audit directory: `runs/batch-audit-20261021T024353Z-a762f7`.
[Evidence summary](evidence/klebaner-batch-audit-20261021T024353Z-a762f7.md),
[full report](../runs/batch-audit-20261021T024353Z-a762f7/report.md), and
[summary ZIP](../results/batch-audit-20261021T024353Z-a762f7-summary.zip).

Saved final batch `runs/review-batch-20261020T202648Z-7e5476` reconciles to
360 completed / 36 failed / 0 pending / 0 running / 0 retryable, 396 unique
units, 100 owned pages (selected 1–100 / original PDF 106–205), 66 pages with
completed checks and 34 with gaps; elapsed 17,888.736 seconds. No missing/extra/
duplicate units/pages or interrupted attempts. Final failure reasons are
16 JSON parsing, 16 schema and four token exhaustion; zero recorded transport/
timeout, identity or primary coverage errors. Both attempts failed for all 36
units; none of the 36 retries succeeded. The retry final content, usage and
finish reason repeated the initial attempt. This does not establish the cause
of that repetition. All recorded HTTP statuses were 200 with the intended alias.

Ten final single-fence answers are formatting-only candidates that pass remaining
validation in memory; four more fenced answers still fail, including one visual
coverage claim. Nothing was recovered or reclassified. The report inventories
119 UNACCEPTED proposals (16 uncertain), 188 recognized blocks without completed
review and two incomplete visual checks (selected 81/82). Counts/valid responses
are not mathematical fidelity. Recorded request latency median/P95 is 23.54/
141.90 seconds; retries added about 50 minutes without new completions. All
432 attempts have usage; reasoning is a subset of completion tokens.

A deterministic eight-page later visual sample is recorded: selected
36, 12, 62, 20, 47, 56, 8, 34 (original PDF 141, 117, 167, 125, 152, 161,
113, 139), seed `klebaner-batch-visual-audit-20261021-v1`, with exact units,
blocks, source/crop paths and selection rule. No images were opened.

Checks passed: existing read-only preview/source validation, all 432 attempt
seals and actual request bodies, all 360 successful-answer validations, page/
unit/coverage reconciliation, script syntax, independent CSV/sample checks,
summary ZIP CRC and exact members. All 5,982 existing batch files and original
ZIP retain before/after hashes. Integrity scope and unverified incidental logs/
preflight raw files are stated in the report; original ZIP was not extracted
or member-verified. No application test suite, visual audit or TeX compilation.
Summary-only ZIP: 60,554 bytes, SHA-256
`d44074d60c3d07d942b32dd933bbb005ebe4cde5e416598e3286c590723f9e98`.

Changed only this state file, the new dated evidence summary, and new ignored
audit summaries/script/ZIP. No production code, original evidence, proposals,
services, dependencies, model requests or Git metadata changed. Everything
remains unstaged. Later recovery/visual review is proposed, not executed.


## 21 October 2026 — bounded eight-page / sixteen-region visual sample completed

Completed Task 2 using exactly `runs/batch-audit-20261021T024353Z-a762f7` and
its `visual-sample.json`. Read required project instructions and handover/state/
README/operator documentation; verified the sample's batch and conversion bindings.
The user reiterated that the 136-block pool must not become full-page review.

Actual output: `runs/sample-audit-20261021T031203Z-a1a1e8`.
[Evidence summary](evidence/klebaner-visual-sample-20261021T031203Z-a1a1e8.md),
[inspection HTML](../runs/sample-audit-20261021T031203Z-a1a1e8/report.html), and
[inspection ZIP](../results/sample-audit-20261021T031203Z-a1a1e8-inspection.zip).

Recorded 16 regions before judging: six proposals, seven unchanged controls and
three failed-work regions, spanning 15 recognized blocks and one omission region.
Selected pages 36/12/62/20/47/56/8/34 map to original PDF
141/117/167/125/152/161/113/139; printed folios read from the source images are
126/102/152/110/137/146/98/124. Fourteen distinct selected request units comprise
11 validated successes and three failures. No full-page fidelity claim.

Opened exactly eight full-page context images and 15 distinct detail images,
in batches of at most two pages. Used 14 existing crops plus one bounded
higher-detail crop inside already-selected p0062:b2; no additional region.
Two identical crop pairs were opened once each. The selection and actual image
use are recorded separately. No further images were inspected after this sample.

All six inspected proposals have source support: three symbol/reference fixes,
two missing periods and one omitted proof-end square. No incorrect or merely
equivalent/unnecessary proposal was observed. Seven controls showed no discrepancy
in the selected text/equations; zero missed errors were observed there. The three
failed-work equations appeared source-consistent but still lack usable validated
model results. No failed answer was recovered. Existing uncertainty flags and
all proposal acceptance states are unchanged. This is Codex visual assessment,
not independent human verification, mathematical certification or an unbiased
whole-book accuracy estimate. Three blocks had no portable draft; native OCR
was compared. Source emphasis and bare Box insertion/compilation remain untested.

The sample supports usefulness but cannot establish total/excessive review burden.
Three low-impact fixes still require checking full replacement paragraphs or
insertion context. Unselected blocks, full-page omissions and the separate
page-44 overlap remain outside this bounded check. No automatic expansion.

Validation: exact sample IDs/counts/maps, copied image hashes, CSV denominators,
local HTML links, ZIP CRC and member bytes, and `git diff --check` passed.
All 5,982 original batch files and 12 Task 1 audit files retain before/after hashes;
key files and conversion state unchanged. Full conversion/archives not rehashed
comprehensively in Task 2. No application suite or TeX compilation performed.
Inspection ZIP is 3,138,922 bytes with SHA-256
`d5330ba077c0fd97940f5a706c1faa66fc298510fa1924da520303cf86ca7a78`.

Changed only this state file, the new dated evidence summary and ignored new
sample-audit files/ZIP. No production code, formatting recovery, retry behavior,
original evidence, inference, OCR, services, dependencies, permissions or Git
metadata changed. Every proposal remains UNACCEPTED; all work remains unstaged.

## 21 October 2026 — full eight-page extension of Task 2

Completed the explicitly authorized extension in
`runs/extended-audit-20261021T032917Z-a0c430`, preserving Task 1 and Task 2.
Task 2 was located through this state record at
`runs/sample-audit-20261021T031203Z-a1a1e8`; its inspection ZIP hash was verified.
Selected pages 8, 12, 20, 34, 36, 47, 56 and 62 map to original PDF pages 113,
117, 125, 139, 141, 152, 161 and 167. All **136 recognized blocks** are covered:
fifteen prior block findings reused, 121 newly inspected, plus the prior
region-only omission. All eight whole-page omission/duplication/reading-order
checks are recorded; progress was saved after each two-page pair.

All nine available proposals contain useful supported corrections. No introduced
harmful change or merely equivalent/unnecessary proposal was observed. One
replacement (p0008:b7) remains incomplete: its source comma after infinity is
still missing. Thirteen blocks have missed or residual discrepancies: eight
punctuation, three math/prose-boundary, one wrong proof-end glyph and one
spurious-accent case. Ten are in completed model units and three in failed
units. Four further missing proof squares were found on pages 8 (two), 12 and
62; the prior flagged square on page 56 remains supported. The overlapping
counts yield twenty recognized blocks with discrepancies and 116 with none
observed, with omissions separate. No accuracy percentage or whole-book claim.

Original model status stays 31 completed / three failed units on these pages;
eighteen blocks belong to failed units. No failed output was recovered or
promoted. All proposals remain UNACCEPTED. Source oddities are preserved. No
source case remains unreadable after one additional bounded parenthesis crop,
but visual assessment is fallible. There are **29 missing portable drafts**;
native OCR was compared instead. Export styling and insertion limitations are
separate, including unverified math-mode/package handling of bare `\Box`.
No TeX compilation or application code change was performed.

Artifacts: `runs/extended-audit-20261021T032917Z-a0c430/report.html`, per-page
JSON, block/page CSVs, proposal and omission ledgers, progress and validation.
Compact ZIP: `results/extended-audit-20261021T032917Z-a0c430-inspection.zip`
(5,996,722 bytes; 70 entries; 51 distinct image assets). SHA-256:
`542af55c70f2973dcdc7afe5600b30df8f6904b1367e7afc1af33102abd3351b`.
Selected evidence: [extended audit summary](evidence/klebaner-extended-audit-20261021T032917Z-a0c430.md).

Validation: exact coverage/mapping, original draft/native/proposal equality and
status separation, 149 local HTML references, image hashes, ZIP CRC and every
member's byte equality passed. Before/after hashes confirm all 5,982 batch
files, twelve Task 1 files and 34 Task 2 files unchanged, plus the original
Task 2 ZIP. No comprehensive rehash of all incidental conversion files is
claimed. `git diff --check` passed. No application suite was run because no
application code changed. No model/OCR calls, agents, recovery, retries,
services, installation, acceptance or Git mutations. All changes unstaged.

Practical implication: useful proposals alone leave missed errors; source
review must include unchanged blocks, page margins and complete replacements.
Next step is human inspection of this report, not automatic correction. This
bounded audit stops here and does not authorize recovery or a new model run.

## 21 October 2026 — Task 3 reviewed checkpoint prepared

Reviewed all relevant tracked/untracked changes since `8487126`, including
acceptance/export, reasoning-effort and focused saved-OCR review, Klebaner
registration, resumable batch review, tests and all selected audit summaries.
No staged files were present; branch `main` tracks `origin/main`, both locally
at `8487126`. No remote freshness/authentication check or Git mutation occurred.
No blocking implementation defect was found. The checkpoint is conditional on
the operator's full normal-terminal test suite and staged-inventory checks.

[Checkpoint handover and exact 32-file staging command](CHECKPOINT-20261021.md)
records scope, review findings, validation, commit/push commands and exclusions.
Only that note and this state entry were written during Task 3. The old local
instruction copy `pdf-to-latex-codex-next-step.txt` remains excluded and untouched.
Raw runs/results, book material, environments, caches/models, local configuration
and archives are excluded; public candidate content was reviewed for secrets
and accidental raw book payloads. No such payloads or credentials were found.

Task 2 is complete for all 136 recognized blocks and omission inspection on its
eight agreed pages, as recorded in the preceding entry and the extended audit.
Nine useful proposals, thirteen missed/residual block defects, four new omitted
proof markers, 29 missing portable drafts and unchanged original model statuses
are retained as findings/limitations. All Klebaner proposals remain UNACCEPTED.
Completed model coverage and the fallible visual audit do not prove absence of
other omissions, whole-book fidelity or TeX compilability.

Documentation timing caveat: SPARK-OPERATIONS.md's 20 October “Current trial”
section still says batch inference has not run. It and the earlier preparation
summaries describe historical preparation; later dated state/audit entries and
the checkpoint note supersede those status claims. Its launch/service commands
are not the next checkpoint action; do not rerun the completed batch. Historical
files were not rewritten during this bounded review.

Current-code validation: 133 tests discovered; all 118 socket-independent cases
passed (zero errors/failures/skips). Fifteen MockServer-dependent tests were
explicitly excluded because previous runs were denied loopback socket creation
with PermissionError/errno 1; no socket workaround or permission change. Run
`.venv-control/bin/python -m unittest discover -s tests -v` in the normal terminal;
require all 133 tests to finish OK with exit 0 before committing. Older test
results are not substituted for this current-code check. Python syntax/JSON,
registered source hashes/mapping, extended-audit counts/completion/ZIP hash and
`git diff --check` passed. Test log is local scratch under
`/tmp/pdf-to-latex-checkpoint-tests-20261021.log`.

No fixes, new feature, further visual audit, formatting recovery, retry change,
inference/OCR, service/download operation, dependency change, proposal acceptance
or extraction pilot occurred. DeepSeek download and running services were left
alone. No TeX compilation or live accuracy claim. All changes remain unstaged.
Next: operator runs full tests, uses the explicit path list, checks staged scope,
then commits/pushes personally if checks pass; Task 4 remains a separate task.
