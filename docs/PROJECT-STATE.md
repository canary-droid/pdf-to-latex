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

## 21 October 2026 — Task 4 offline native-text assistance pilot complete

The operator reports Task 3 full normal-terminal tests passed and the reviewed
checkpoint was committed/pushed. Read-only local Git inspection found `main`
and `origin/main` at `7b62030` (`Add accepted derivatives, batch review and audit
evidence`). That completes the previous checkpoint action; it is not validation
of the new code below. No Git mutation occurred in this task.

Implemented an explicit opt-in `python -m probe.native_text_pilot` command with
separate development, holdout and neutral-pack operations. The default converter
is unchanged. It reads positioned PyMuPDF characters/fonts and validated saved
OCR, preserves original page/block identities, reports conservative alignment,
disagreements, uncertain/duplicate character assignments and missing-math risks.
Native alternatives are UNACCEPTED evidence, never replacement LaTeX or accepted
OCR. Existing acceptance validation rejects these candidates. Unsupported rotated
or unequal source/window geometry is refused; crop-relative coordinates retain
nonzero cropbox offsets. Ligatures, signs, punctuation and line-end hyphens are
not silently repaired. No formula reconstruction or style-sensitive flagging.

Verified registered `klebaner-ch4-7` selection: 120 pages, original PDF 106–225,
prepared PDF SHA-256
`61102519b11535ee11e817d7b6f5b357e87435429b231c144c0e82f6dc6f80e4`.
All 15 saved worker summaries already used `parse_mode: txt`, MinerU 4.0.12.
Read-only installed-code inspection confirmed Basic maps to medium effort and
combines native text with separate formula recognition. Controller PyMuPDF is
1.26.6; installed DocVortex is 0.5.16. Enabling text mode is not a new solution.

Fixed development originals: 106,116,126,136,146,156,166,170,176,186,196,205.
Fixed holdout originals: 206,212,218,225. All exist as distinct owned saved pages.
No sample replacements and no overlap/context duplication. The preserved first
development-only run `runs/native-text-pilot-20261021T052234Z-9ca87f` exposed a
generic normalization issue with font-mapped control glyphs. The rule was narrowed
to ASCII whitespace before creating the final experiment. This was development
work, not holdout tuning. No holdout was run against that initial prototype.

Final completed run: `runs/native-text-pilot-20261021T052347Z-094634`.
Rules, module/helper hashes, sample, source bindings and development artifacts
were frozen before extracting holdout; post-holdout verification passed without
changing those inputs. No saved model correction, acceptance plan, fixture answer
or extended-audit answer was used in extraction/alignment/flag inputs. The prior
audit remains background evidence, unchanged.

Observed coverage/workload (not accuracy):

- Development: 12 pages / 206 regions; 46 exact + 98 anchor matches, 52 geometry
  only and ten ambiguous; 160/206 regions flagged, 12/12 pages flagged.
- Holdout: four pages / 61 regions; 19 exact + 33 anchor matches, nine geometry
  only, zero ambiguous; 42/61 regions flagged, 4/4 pages flagged.
- Total: 267 regions, 196 exact/anchor matches, 202 flagged; zero entirely empty
  native regions, but incomplete/missing glyphs remain inside nonempty regions.
  Twenty-three unassigned non-whitespace characters remain visible and are not
  automatically classified as source omissions. Flags overlap; full counts are
  in the selected evidence summary and saved summaries.

The neutral pack contains twelve regions on seven pages (seven context images
and twelve crops, deduplicated). Visual inspection covered those twelve crops
and page context on originals 106,170,206; this was not a full-page fidelity audit.
The known page-106 paragraph has useful native punctuation/symbol fragments, but
its native mathematics is incomplete. The damaged page-170 nested expression
remains unresolved in both alternatives. Other selected native alternatives
lose sums, integrals, parentheses or script roles; shared character boxes
contaminate an adjacent theorem/equation pair. Five unflagged controls were
checked: four showed no content discrepancy; one missed italic/math-mode
representation. No changed value or punctuation was confirmed in those controls.
Six selected holdout regions were visually inspected after freezing rules;
there are no independent exhaustive holdout labels. Holdout remains unscored,
later-section and non-random. No whole-book accuracy or savings claim.

Outputs:

- Full report: `runs/native-text-pilot-20261021T052347Z-094634/report.html`.
- Compact entry: `runs/native-text-pilot-20261021T052347Z-094634/inspection.html`.
- Neutral inputs: same directory's `review-pack/report.html`, `regions.json` and
  images. Diagnoses/control roles/expected answers are excluded from these inputs.
- Separate evaluation: `evaluator/report.html`, `findings.json` and
  `inspection-log.json`. These are never extraction inputs.
- ZIP: `results/native-text-pilot-20261021T052347Z-094634-inspection.zip`,
  1,745,381 bytes / 37 members, SHA-256
  `66eefc6be0d42087b5bbfe0044f5bc1dca683e6425836ce4e603ef02f03a1a46`.
- Selected tracked summary:
  [native-text pilot evidence](evidence/klebaner-native-text-pilot-20261021.md).
  README and SPARK-OPERATIONS document actual commands, results and limitations;
  the runbook now labels the completed batch's launch procedure as historical.

Validation: ten new tests and 27 relevant existing document/saved-review tests
passed offline. The additional acceptance-rejection assertion also passed in its
focused test after insertion. Python syntax, 267 unique block IDs, source loading,
fixed mapping, frozen stage manifests, neutral-input separation, image
uniqueness, local HTML links, ZIP CRC and member bytes passed. Full current suite
has 143 cases; run `.venv-control/bin/python -m unittest discover -s tests -v` in
the normal terminal. The fifteen mock-loopback cases were not repeated here
because of the previously documented sandbox restriction; no permissions or
socket workaround. Offline checks do not establish model accuracy. No TeX
compilation was attempted and no corrected TeX was generated.

Preservation: all 880 conversion files checked byte-for-byte by hash; registry,
selected PDF, preparation manifest and full original PDF hashes unchanged.
Existence/size/mtime checks also found no changes to 11,487 pre-existing files
under inputs/runs/results; those other files were not comprehensively byte-hashed.
All raw pilot material stays ignored under runs/results. The unrelated local
`pdf-to-latex-codex-next-step.txt` remains untouched. No existing proposal or
completed evidence was edited. No inference/OCR, dependency installation,
service/model-setting operation, download interruption or Git mutation occurred.
All project changes remain unstaged. `git diff --check` passed.

Recommendation: keep the opt-in inspection aid, but do not integrate automatic
replacement or rely on current flags to reduce production review workload.
Math structure, overlapping alignment, shared errors and style sensitivity need
separate evidence before integration. Next action is the operator's full suite
and inspection of the pack; no further task or model review was launched.

## 21 October 2026 — Task 5 revision 2 prepared offline; live Qwen trial NOT RUN

Read `/home/mdi/Downloads/05-qwen-native-evidence-trial.txt` revision 2 and the
required instructions/handover/checkpoint. No earlier Task 5 preview/live directory
was found; this is the first preparation. Task 3 is the operator's completed
checkpoint. The Task 5 brief reports Task 4's full tests passed; its working-tree
changes remain unstaged and were preserved. No service/download operation,
model/OCR call, dependency installation, Git mutation or proposal acceptance.

Added a separate opt-in module command `python -m probe.paired_trial` with offline
prepare, operator launch/resume, read-only status and partial/result bundle modes.
`paired_inputs.py` freezes matched A/B requests; `paired_trial.py` implements a
single-attempt sequential runner and readiness launcher; `paired_report.py`
produces ledgers, inspection HTML/ZIP and neutral future text-critic export.
Existing converter, validators, Task 4 implementation and historical evidence
are unchanged. New regression tests exercise the experiment's meaningful risks.

Verified saved conversion `runs/convert-basic-20261020T075104Z-48fd90` and pilot
`runs/native-text-pilot-20261021T052347Z-094634`, including its sealed neutral
review pack and corresponding extraction/comparison records. All 267 unique
recognized regions on the existing sixteen pages are included: 202 flagged and
65 unflagged. Flags remain potential evidence problems, not confirmed errors.
Page/block mapping agrees with owned source evidence; original physical pages
106,116,126,136,146,156,166,170,176,186,196,205,206,212,218,225 are unchanged.

Frozen priority order: twelve neutral-pack regions first, then eighteen additional
flagged and eighteen additional unflagged regions, all distinct. This 48-region
core covers all sixteen pages (25 flagged / 23 unflagged). The remaining 219
contain 177 flagged / 42 unflagged. Seeded hash ordering and round-robin page /
available flag/math strata spread work before any model outcomes; A/B and B/A
pair order alternates. Known development examples, prior inspections and cohort
phases are identified only in the evaluator manifest. There is no fresh independent
holdout or book-wide accuracy sample; unrecognized whole-page omissions are not
covered by this region trial.

Both arms have identical source context/detail images, OCR/draft, task, schema
and settings; B adds only literal compact native-text evidence. All 267 pair-body
comparisons verified this. No model corrections, audit diagnoses, flags, expected
answers or gold TeX are supplied. Seventy-eight portable drafts are unavailable
or invalid; complete raw structured OCR is retained without repair or exclusion.
Existing images and extraction were reused, not regenerated. Original twelve-pack
image/OCR hashes match. Largest request: 492,046 bytes and 9,643 text characters,
within unchanged client/request limits.

Fixed configuration: exact `flash-next-tensorfold` at `http://127.0.0.1:8890/v1`,
medium reasoning effort, 16,384 maximum output tokens, 600-second timeout,
stream=false, sampling defaults inherited by omission. Server response_format
is omitted in both arms; schema-in-prompt plus strict local JSON/schema, identity,
selected-block coverage and proposal validation remain. No answer unwrapping or
repair. Content/punctuation/style/uncertainty categories are model reports only.

At most 534 review requests: priority 96 then remainder 438, one per arm/region,
no automatic retries. After twelve pairs, at least nine valid responses in EACH
arm are required; a failed reliability gate persists and cannot be bypassed on
resume. This tests response usability, not accuracy or model capability. Two
consecutive transport failures pause; identity/integrity/configuration rejection
stops. Durable reservations consume interrupted requests, which are recovered
from committed response evidence or recorded interrupted, never silently resent.
Only pending work resumes. Cumulative admission is nine hours; the current
request can finish within its original 600-second timeout. Normal paused time
is excluded; unknown crash downtime is conservatively charged. Budget exhaustion
and gate decisions persist, so operator absence does not authorize extra work.

The operator-only launcher checks converter exit and performs fresh exact-model
preflight through project APIs, capturing its actual directory automatically.
It requires BOTH Text passed and vision qualified; unsupported server strict JSON
is allowed under local validation. Preflight precedes review admission and is
bounded separately. It never starts/stops a service. No GLM switch/call is needed.

Actual prepared artifacts:

- Preview: `runs/qwen-native-input-20261021T062027Z-c025fd`, manifest SHA-256
  `7cf4a38517b01a8651721b8fcd0e600ddc9aeae29c6ed03042593999317fe299`.
- Separate live directory: `runs/qwen-native-trial-20261021T062027Z-a1f40a`;
  status prepared_offline, all 534 arms pending, zero attempts/readiness calls.
- Full local HTML: that live directory's `report.html`.
- Initial offline ZIP:
  `results/qwen-native-trial-20261021T062027Z-a1f40a-inspection-20261021T062043Z-e6ee87.zip`,
  exactly 4,676,398 bytes, SHA-256
  `11cbe67bf43d43320cae18755907e1f4905bc0fad7e1d154871ebd59a59b3233`.
  This is pending input evidence, not live results. It has complete 267-region
  ledgers and 48 priority cases' 64 deduplicated images. Future compact bundles
  add at most twelve attempted remainder regions, prioritizing failures/incomplete
  pairs and differing validated answers. Raw/base64/reasoning stays outside ZIPs.
  `latest-bundle.json` records the actual newest immutable archive path/bytes/hash.
- `neutral-critic.json`: traceable OCR/native/proposal text without evaluator
  labels; explicitly unable to establish visual fidelity. GLM stage not built.
- `source-audit-plan.txt`: full replacement and unchanged-control image audit,
  improvements/regressions/misses/uncertainty plus insertion/compilation issues,
  tokens/time/review burden; label Codex judgments, never independent human gold.

Validation: 23 new focused tests passed. Full discovery found 166 cases; all 151
socket-independent tests passed (zero failures/errors/skips), excluding fifteen
known MockServer loopback cases without changing permissions. Logs:
`/tmp/task5-tests.log`, `/tmp/task5-offline-suite.log`. The operator must run
`.venv-control/bin/python -m unittest discover -s tests -v` in the normal terminal.
Actual offline preparation succeeded with sockets, subprocess workers and client
transport patched to reject any call. Python syntax, immutable request/source
bindings, exact coverage/order, per-arm isolation, image reuse, all HTML/archive
links, ZIP CRC and `git diff --check` passed. A temporary validation script first
needed PYTHONPATH corrected; the corrected artifact verification passed.

Preservation scope: all 1,268 files in the pre-task hash inventory are unchanged,
including conversion, Task 4 pilot and ZIP, Task 4 source/tests/selection/evidence,
source PDF/manifest/registry, AGENTS and the unrelated local instruction copy.
Not every older run was newly byte-hashed. The preview binds 1,251 source/pilot
files. Raw request bodies/book material/archives remain ignored under runs/results.
All changes remain unstaged; no Git metadata change or additional agent.

Usage: [Task 5 exact normal-terminal/tmux commands](QWEN-NATIVE-TRIAL.md).
Selected evidence: [offline preparation](evidence/qwen-native-trial-preparation-20261021.md).
README/SPARK-OPERATIONS now identify this prepared trial and retain dated prior
history. Next: operator runs all 166 tests, enters dedicated tmux, launches the
prepared Qwen job and detaches. Actual Qwen utility/harm and any integration
recommendation await live outputs plus source audit; no accuracy/savings claim.

## 22 October 2026 — DeepSeek historical Arm A comparison prepared offline

Read the supplied `deepseek-first-launch-20261022/codex-task.txt` and current
project instructions/state. No earlier DeepSeek comparison code, wrapper, preview
or run was found in this checkout; one separate opt-in implementation and one
sealed preview were created. No duplicate Qwen or DeepSeek experiment was made.
No existing GLM critic implementation was found; existing neutral critic exports,
GLM work and unrelated edits were preserved. No agents, live requests/discovery,
OCR, installs, service/deployment changes, proposal acceptance or Git mutations.

New observation of the operator-completed Qwen trial:
`runs/qwen-native-trial-20261021T062027Z-a1f40a` reports completed_with_failures,
534 attempts, 476 structurally completed, 58 failed, zero pending/interrupted.
Both arms have 238 completed / 29 failed: 26 schema, two JSON and one token-limit
failure per arm. A has 46 proposals and B 53, all UNACCEPTED. Its initial gate
passed A=12/12, B=11/12; recorded elapsed time is approximately 12,617 seconds.
These observations supersede the prior prepared-only status, not the dated
preparation record. They are not assessments of fidelity or usefulness.
Resolved the original preview through the run's binding:
`runs/qwen-native-input-20261021T062027Z-c025fd`. Validated all 534 historical
attempt seals, request equality, saved statuses and successful response schemas.

The supplied successful deployment evidence was read, not rerun:
`/home/mdi/local-llm/deepseek-flash17-setup/first-serve-853310da-v1/runs/20261022T171904Z-2128368`.
SMOKE-PASS matches `http://127.0.0.1:8894/v1`, exact model
`DeepSeek-V4.1-Flash-TF` and runtime image
`sha256:35d9bda39ffde364249f21be294dde6aeee9c51940973477ca5728f32422aa35`.
Recipe context: `853310dab967480013eda7cef4e79c2fd041629a`, EXL3 2.8bpw.
Arithmetic, three digit-image cases and the blank passed with matching response
identities. Saved memory after the last image was about 8.8 GiB head / 13.4 GiB
peer; this is not a current-capacity or mathematical-accuracy guarantee.

Added only new application modules `probe/deepseek_inputs.py`,
`probe/deepseek_trial.py`, `probe/deepseek_report.py`, regression tests
`tests/test_deepseek_trial.py` and operator wrapper
`scripts/run-deepseek-arm-a-trial.sh`. Historical paired/native/conversion code and
configuration remain unchanged. The wrapper is invoked with bash; no permission
changes were needed. Documentation: new `docs/DEEPSEEK-ARM-A-TRIAL.md` and
`docs/evidence/deepseek-arm-a-preparation-20261022.md`; updated README, this state
and SPARK-OPERATIONS without erasing earlier work.

The new path copies all 267 A requests in frozen order, including failed Qwen
cases, changing only model. Every normalized request comparison passed, input
JSON is byte-identical, and all 283 images retain original hashes (267 crops /
sixteen contexts). Original page/block identities and the 78 unavailable/invalid
portable drafts are preserved. Largest saved request is 491,360 bytes. No native
character stream, Qwen answers/proposals, audit diagnoses or expected corrections
were inserted. Source errors remain source errors; recognized-region review
cannot certify unrecognized whole-page omissions.

Fixed medium effort, 16,384 output tokens, 600-second request timeout, stream=false,
sampling omitted and response_format omitted are inherited from historical A.
Different deployments can have different defaults; this is not a quantization-only
comparison. Strict local JSON/schema, identity and selected-block coverage are
mandatory. Existing conservative TeX fragment/package checks report unsupported
LaTeX separately as export-blocked. No acceptance/export/compilation occurs.

At most 267 sequential review requests, one per region, no retries. The first
twelve are the technical gate and need at least nine valid responses; they are
not repeated. Cumulative live admission is eight hours across resumes, permitting
the current request to finish within its original timeout. Normal paused time is
excluded; unknown crash downtime is charged conservatively. Durable reservations
consume interrupted/unknown attempts. Explicit resume sends pending requests only.
Two connection/timeouts pause; changed identity/integrity/rejected configuration
stops. Gate failure and exhausted budget persist and cannot be bypassed.

The live launcher binds exact first-launch evidence, checks project OCR exit and
runs fresh project preflight. Exact discovery and identities from successful and
failed responses are checked. Both Text passed and vision qualified are required;
explicitly unsupported strict JSON is allowed, another preflight failure blocks.
Optional bounded `--wait-ready 3600` polls only `/models` before preflight, also
requiring matching SMOKE-PASS; a different model or STOP stops waiting. An explicit
first-launch path is supported; otherwise the documented pointer is read once and
bound. No writes are made under local-llm. Readiness and waiting precede the review
admission budget. The deployment smoke pass never substitutes for project readiness
or source-image assessment.

Actual prepared evidence:

- Preview: `runs/deepseek-arm-a-input-20261022T180153Z-4d91d8`; manifest SHA-256
  `5b10c8801a217be076f652105ab686db21f4eeae718096e841096f47e1e64268`.
- Run: `runs/deepseek-arm-a-trial-20261022T180153Z-0ee3cf`, prepared_offline,
  all 267 pending, zero attempts/readiness calls; its `report.html` is ready.
- Initial ZIP:
  `results/deepseek-arm-a-trial-20261022T180153Z-0ee3cf-inspection-20261022T180159Z-994ead.zip`,
  10,878,589 bytes, SHA-256
  `43af39ec3c7dff7011b6bb786ef55196ef9d037245eca94f64af7d35149aedef`.
  All regions/images are included with deduplication. Raw base64/API reasoning
  stays in the run. This initial archive contains pending DeepSeek cases, not
  live outcomes. `latest-bundle.json` selects the actual newest immutable ZIP.

The HTML/ledger compares like-for-like region IDs, complete old/new text, source
images, final-answer availability, structural failures, token/latency usage and
proposal counts. Content/uncertainty and punctuation/style have separate views;
categories are model claims, and punctuation may affect meaning. Aggregate views
separate the initial twelve and remainder. Missing/nonvalid pairs stay visible.
All proposals remain UNACCEPTED; no accuracy score is computed.

Validation: all 24 new synthetic-transport regression cases passed. Full discovery
ran 190 tests: 175 passed, 15 errored solely at mock loopback `socket.bind` with
`PermissionError: [Errno 1] Operation not permitted`; zero assertion failures.
Log: `results/deepseek-full-tests-20261022.txt`. No sandbox permissions were changed.
The operator must run `.venv-control/bin/python -m unittest discover -s tests -v`
in the normal terminal and require all 190 to pass. Python/shell syntax, source
bindings, exact requests, report/ZIP links, ZIP CRC and `git diff --check` passed.
Preparation explicitly blocked sockets, subprocess workers and model transport.

All 6,948 files in the before-task preservation inventory remain byte-identical:
pre-existing source/tests/scripts, Qwen run/preview, native pilot and conversion.
The new preview binds 6,910 source files. This is not a new byte audit of every
older archive. Details: `results/deepseek-preparation-preservation-20261022.json`
and `results/deepseek-preparation-validation-20261022.json`. Raw runs/results stay
ignored; all changes remain unstaged. No completed evidence was overwritten.

Next: use [the exact normal-terminal/tmux operator sequence](DEEPSEEK-ARM-A-TRIAL.md).
No concrete offline implementation blocker was found. Fresh project preflight,
the 12-region gate, sustained-memory/live-run behaviour and mathematical fidelity
remain untested. Inspect complete replacements and unchanged controls against
source images after the trial; do not infer accuracy from successful JSON.

## 23 October 2026 — focused completed-DeepSeek offline follow-up

Followed `/home/mdi/Downloads/pdf-to-latex-deepseek-followup-v2-20261022.txt`.
The operator's DeepSeek trial is now observed complete: all 267 attempted,
256 structurally completed, eleven failed, no pending/dispatched/interrupted work.
Its initial gate passed 10/12; saved elapsed admission time is 11,538.1 seconds.
This supersedes the earlier prepared-only state without rewriting historical
evidence. No launch process remained, the active timestamp was null, the project
writer lock was free and the final operator log recorded completed_with_failures.

Reused the existing report/ledger/aggregate and checked the missing on-Spark
evidence read-only. Existing helpers verified frozen source/code/preview bindings,
267 DeepSeek and 267 Qwen-A raw seals, exact raw identities (including failures),
actual outgoing serialization and selected-region coverage. Every one of the
267 paired requests differs only in model: same images/messages/schema, medium,
16384, stream=false, 600-second timeout, omitted response_format and sampling.
Different inherited defaults/runtimes remain a confounder. Qwen comparison is
Arm A only. No completed report, raw attempt or status was regenerated/changed.

The supplied completed ZIP
`results/deepseek-arm-a-trial-20261022T180153Z-0ee3cf-inspection-20261022T212950Z-62f929.zip`
matches SHA-256 `475b3e01d0bd8f2004644f7582d016c1dad84a9623d7747f5522e67ae8f3dce4`.
Its CRC and saved aggregate/ledger consistency pass. Prior pack counts agree:
Qwen A 238 completed / 29 failed; matched usable pairs 227, DeepSeek-only 29,
Qwen-only eleven, neither zero. Proposals 105 vs 46, model-labelled content 29
vs 28. Latency sums 11,261.7 vs 5,513.8 seconds. Separate DeepSeek reasoning-token
usage is not supplied, not zero. These are protocol/workload counts, not accuracy.

All eleven DeepSeek failures are normal HTTP-200/finish-stop responses with final
text and exact identity: six missing scope, one extra schema-definition keys,
four malformed schema/result concatenations. No recorded timeout/token-limit
failure or simple fenced JSON answer exists in this set. Original failures stay
failed; no recovery or normalization was attempted. Fresh saved project preflight
records strict_json passed, but the tiny probe does not qualify the actual review
schema. The baseline deliberately omitted response_format.

Inspected the complete strings of all 77 DeepSeek export blockers against actual
parser/allowlist code. Primary diagnoses: 58 ordinary text/heading macros, six
bare equations missing display delimiters, five accent commands, three Unicode
prose cases and five ordinary math-allowlist cases. These sum to 77; overlapping
tags identify additional Unicode (nine), accent (nine) and math (sixteen) issues.
The saved first-error split (71 generic / three wedge / three ge) hides these
details. There are 76 distinct blocked regions because 243 contains two identical
replacements with different labels. No extra definite brace/math-delimiter defect
was observed among the 77, but this is neither compilation nor fidelity validation.
One retained hyphenated line break is context-dependent. No TeX executable was
found on PATH or invoked. Qwen comparators expose real full-replacement defects:
220 ends in an unmatched dollar, and 33 loses math delimiters and contains a tab
in place of the start of a command. Production validators were not modified.

Frozen before image viewing, the additional manifest selects exactly twelve
distinct regions: four neither-model proposals (84,128,216,41), four one-model
proposals (198,38,238,196), and four dense math/definition cases (143,33,217,178).
Seeded hash/density ranking and page diversity are recorded; prior sixteen cases
and within-sample duplicates were excluded, with no reallocation needed. Hash:
`c100db0dc1dcbaae655964bcef582dd5264f307a0e57e6c76c6ad4faca717292`.
Also rechecked the six specified diagnostic comparisons 5,93,201,207,220,235.
Total source-image scope: eighteen selected regions, eighteen original detail
crops and twelve original pages for context only. No full-page omissions or
whole-book accuracy are certified. The ten other prior ChatGPT findings remain
attributed prior AI assessments, not newly verified regions.

Confirmed the key cautions: the disputed exponent parenthesis at 93 is printed
and both models remove it; DeepSeek's blackboard-bold expectation claim at 201
is unsupported; both blanket expectation-style changes at 207 contradict mixed
source styles. Useful shared repairs were confirmed at 5,220,235 and new case 178.
At 235, export support differs because DeepSeek adds display delimiters, not
because Qwen failed to detect the mathematical error. Six additional unchanged
regions, including three substantial equations, showed no content discrepancy;
the folio/heading are weak controls. The four one-model cases support presentation
or punctuation changes. At 33 both identify a true comma omission, but Qwen's
full replacement is unusable TeX and DeepSeek retains minor presentation defects.
No selected crop was unreadable. Human verification/compilation remain outstanding.

Next bounded recommendation: first offline exporter compatibility with balanced
prose support, explicit math additions, typed fragment context and negative tests,
preserving all acceptance/conflict rules. Separately, consider actual-schema
constrained output versus schema-feedback on the eleven failures plus successful
controls 33,93,178,235, at most thirty requests with controls first. No exhaustion
evidence justifies lower reasoning for these failures. A text-only consistency
critic is a third separate decision, preserving suspected author errors and
source provenance. The referenced bibliography/provenance brief was not found
in project docs/relevant Downloads; its path was requested and its contents were
not invented. Resolve that input before preparing the later critic stage.
No new inference preview, repair mechanism or critic implementation was created.

New ignored audit: `runs/deepseek-followup-20261022T231635Z-ba686b` (UTC directory
timestamp; local audit date 23 October). Open `report.html` or read `report.md`.
Detailed artifacts include blocker/failure CSVs, full before/after strings with
small highlighted changes, per-region visual findings, frozen sample, original
source links and validation. Cosmetic work has a separate view. Inspection ZIP:
`results/deepseek-followup-20261022T231635Z-ba686b-inspection.zip`, 3,373,677 bytes,
SHA-256 `b1b8d61e510689a63ae1f534222a22753dd5c93a14cbe8e1febceddfe725e38c`.
Its 45 members include thirty deduplicated images; no PDFs, raw API/base64 trees
or model reasoning. Extract and open the run-named `inspection.html`.

Validation: all 9,570 inventoried existing files remain byte-for-byte unchanged,
with no added files in original evidence/application/tests/scripts folders.
Raw bindings, frozen selection, image hashes, CSV counts, report/ZIP links,
archive contents/CRC, audit-script syntax and git diff --check pass. The full
unit suite was not rerun because production code is unchanged. Only this state
and new selected non-book evidence documentation were changed outside ignored
audit outputs. No model/OCR calls, agents, service changes, installations,
proposal acceptance or Git mutations; all changes remain unstaged.

Selected summary: [focused DeepSeek follow-up](evidence/deepseek-followup-20261023.md).
The evidence supports narrow compatibility/reliability work and continued human
source inspection; it does not demonstrate a unique DeepSeek mathematical
advantage, a review-time saving or book-wide accuracy.

## 23 October 2026 — shared recovery, experimental export and text critic prepared offline

Implemented the current `pdf-to-latex-recovery-critic-20261023/task.txt` after
reading the required project documents, the recovered earlier bibliography brief,
current source and the completed Qwen/DeepSeek/follow-up evidence. The recovered
brief is background, not a second GLM-only task. The previous native/paired/
DeepSeek changes remain intact. No inference, metadata lookup, OCR, installation,
service/settings/permission changes, Git mutations or additional agents occurred.

Policy clarification, effective for this new experiment: the user permits clear,
recorded local editorial repairs in a new evaluation derivative. The visibly extra
closing parenthesis at PDF 166 / printed 151 / b9 is an eligible editorial repair,
not a headline failure merely because the typo was printed. Historical source-
faithfulness findings remain unchanged. Ambiguous regrouping, signs, bounds,
hypotheses and mathematical meaning cannot be hidden as low-priority punctuation.
All final acceptance/conflict rules remain. An experimental candidate is explicitly
UNACCEPTED and unverified; originals and original proposal statuses stay intact.

Exporter: expanded balanced prose/heading nesting, inline math, escaped punctuation,
observed accents, text spacing and normal math commands. The explicit pdfLaTeX
UTF-8/T1 Latin-prose repertoire retains source bytes; arbitrary Unicode math,
unknown commands and dangerous constructs remain unsupported. Renderer-emitted
styles/headings pass the same replacement grammar. Typed math bodies come only
from a verified equation block or validated typed contract. Display wrappers are
recorded transformations with original suggestion bytes retained. Legacy typing
is explicit. Ambiguous line-break hyphenation is not joined. Qwen 33 and 220 still
fail their full-string syntax checks.

All 151 saved proposals were re-evaluated in NEW compatibility reports:

| Classification | Qwen Arm A | DeepSeek |
|---|---:|---:|
| Previously supported | 12 | 28 |
| Newly supported | 25 | 71 |
| Explicit display wrapper required | 7 | 6 |
| Genuinely malformed | 2 | 0 |
| Still unsupported or unresolved | 0 | 0 |

Thus all 77 earlier DeepSeek exporter blockers now have a supported grammar path,
including six separately recorded wrappers. This establishes neither compilation,
source fidelity nor authorization. Duplicate identical replacements remain linked
to every original proposal; differing strings conflict. Dependent edit components
are applied all-or-none in the experimental candidate. Uncertain edits, missing
members, deletions and unknown/multiple targets are deferred; unaffected blocks
and order are retained. A model's cosmetic/editorial label does not hide changed
math. Complete original OCR and source images remain available for unresolved
editable blocks, which get explicit TeX placeholders.

Shared recovery/executor: uses the existing LocalClient, strict JSON parser,
focused-response validator, project writer lock, atomic evidence and seals.
Historical runners/previews are not rebound. A single complete outer JSON fence
is the only mechanical repair, followed by every validator. Schema feedback
contains the full failed answer, exact field/path errors, required data-instance
schema and original context. Readable substantive fields/uncertainty cannot be
silently discarded; semantic preservation for an unparseable answer remains
unverified. Identical repeated failures do not trigger blind retries. Identity
and integrity errors never enter model repair. Finish length with final content,
reasoning-only exhaustion with explicit usage, unknown budget exhaustion,
timeout, transport, JSON, schema, coverage and TeX failure remain distinct.
The eleven historical DeepSeek failures classify as four JSON and seven schema
failures; none is a mechanically removable fence. Original statuses are unchanged.

At most two additional calls per original region/group-version across JSON,
conditional lower reasoning and compiler feedback. Durable reservations, explicit
parent chains and request hashes preserve the ceiling over interruption/resume;
unknown calls are consumed. Config/source/code/model/attempt changes refuse
resume. Two transport failures pause; identity/integrity/configuration errors
stop. Time admission includes prior active time and conservative unknown crash
downtime. Normal pauses and separately explicit readiness are outside review time.
Truncated final JSON is deferred for a separately recorded coherent split/budget
choice; no automatic split or continuation concatenation was added.

The optional compiler adapter uses the portable template and an explicit immutable
Docker image. Only required read-only input and a temporary build directory are
mounted; no network, home, credentials, caches or Docker socket enters the TeX
container. No shell escape, memory/process/time limits, retained source/log/output
hashes and engine identity are implemented. Original/proposed comparisons use
identical packages/context. Introduced syntax errors are separated from preexisting
OCR errors, unknown macros/context, missing packages/encoding, references and
unavailability; only attributable syntax failure enters compiler feedback. Safe
but malformed fragments may reach the isolated compiler for diagnosis while
remaining ineligible for export. Qwen 33/220 and unchanged equation control 143
have actual temporary-document fixtures saved, all marked unavailable/not run.
No host TeX executable was found. A read-only Docker image-list check was denied
by the configured sandbox at `/var/run/docker.sock`; no permission change or
compiler-container execution was attempted. Normal-terminal isolated setup and
real checks are documented; mocks do not establish compilability.

Upstream reuse: verified the supplied sciwrite-lint 0.6.1 archive hash
`7a76f0e3435e145a220eb5f0adabcad445706131ea9631e27f97394e240202b0` and inspected
regular members safely. Retained MIT copyright/licence. Adapted small prompt-
safety, shared-context/query-state, contradiction/finding grouping, balanced TeX
command/citation and bibitem membership helpers; exact function mapping is in
[SCIWRITE-REUSE.md](SCIWRITE-REUSE.md). No whole-package install/import, destructive
TeX cleaner, equation stripping, figure loading, arbitrary clipping, finding caps,
upstream model fallback or service code. The text critic preserves exact strings,
quotes, offsets, source maps, edition/hash and bibliography context. Stable IDs
bind draft and finding. No findings, incomplete coverage, insufficient context and
technical failure remain separate. It cannot establish what the PDF prints.

Bibliography foundation inventories all 120 owned saved pages / 1,952 blocks:
no recognized reference-entry blocks, 99 explicit/possible citation occurrences
(the year-marker subset is deliberately ambiguous). Coverage is not_in_extract
with a saved-block/type limitation, not a new visual bibliography audit. Raw
entries/occurrences and exact spans/hashes are retained. Metadata checked, full
text available, actual consultation and claim support are independent statuses.
No parsed metadata, DOI or consulted-source claim was invented. Candidate BibTeX
requires supported fields and exact raw-source spans; none was generated without
such fields. Local `.bib` preservation is supported, broad parsing deferred.
External lookup/acquisition/claim verification remain disabled, with a concrete
upstream reuse roadmap; bibliography absence does not block criticism.

Frozen new Qwen visual protocol: same 267 recognized regions on sixteen pages,
with exactly unchanged source images/crops and original OCR/draft data. Only
versioned instructions and explicit fragment contracts change; no Arm B/native
characters, assessor diagnoses or expected corrections enter the requests.
Medium / 16,384 / 600 seconds / serial / omitted sampling and response_format.
Maximum 267 baseline + 80 recovery calls; six hours cumulative review admission.
The first 24 cases are the fixed technical gate (minimum 12 first-attempt and 20
final usable/covered responses), including Qwen 161's verified 16,384 reasoning-
token exhaustion. The exact cached Qwen template supports medium and low;
rendered runtime effect remains untested. Completed gate calls are not repeated.

Frozen critic recipe: twenty coherent windows, ten development and ten reserved,
on disjoint page sets. Fewer than 24 were selected to avoid padding with unrelated
text. Four group pairs begin the technical check: eight final valid responses,
minimum six first-attempt and six complete claimed coverage. Prior source-checked
controls are diagnostic, not human gold; reserved does not mean previously unseen.
Instructions/selection are frozen before reserved execution. Actual new Qwen
candidate hashes bind after its run, in separate neutrally identified requests.
No rationales/images/audit verdicts enter the critic. Failed/unresolved candidate
assembly makes a group version unavailable rather than substituting baseline.
DeepSeek medium is the planned profile; GLM high is an explicit separate later
profile. Forty baseline requests, at most 24 recoveries, four hours; two extra
calls per original group/version. Only twenty actual uncorrected baseline request
bodies exist now; candidate-version requests await the real new candidate.

The independent optional diagnostic prepares the eleven historical DeepSeek
failures plus controls 33,93,178,235 under JSON feedback versus constrained output,
at most thirty calls. Four actual-schema constrained controls qualify that condition
first within the same budget; unsupported/unqualified cases are recorded without
fallback. Feedback remains separately runnable. A tiny preflight JSON success
never establishes actual review-schema support or mathematical accuracy.

Actual prepared paths (zero new dispatched calls):

- Preparation: `runs/recovery-preparation-20261023T083548Z-37bf1b`, HTML/Markdown,
  both compatibility CSV/JSONs, bibliography, compiler fixtures and validation.
- Visual preview: `runs/recovery-vision-input-20261023T083548Z-3399ba`.
- Visual run: `runs/recovery-vision-trial-20261023T083553Z-6aa648`.
- Critic recipe: `runs/text-critic-recipe-20261023T083553Z-60180a`.
- Diagnostic preview: `runs/schema-diagnostic-input-20261023T083554Z-26d460`.
- Diagnostic run: `runs/schema-diagnostic-trial-20261023T083554Z-73af08`.

The first offline preparation encountered a bibliography API argument-type error.
It sent no calls; its unused sealed outputs were preserved and superseded,
recorded in `results/recovery-preparation-aborted-20261023T083419Z.json`.
The corrected preparation completed with model transport and subprocess execution
explicitly blocked. No existing OCR or completed evidence was regenerated.

Validation: 49 focused regressions, 48 passed and one real compiler test skipped
because no explicit isolated image is configured. Final full suite: 239 tests,
223 passed, 15 errors exclusively from sandbox-denied mock loopback socket.bind,
one compiler skip, zero assertion failures. Logs:
`results/recovery-critic-focused-tests-20261023.txt` and
`results/recovery-critic-full-tests-20261023-final.txt`. Normal-terminal command:
`.venv-control/bin/python -m unittest discover -s tests -v`.
Python syntax, exact request/image/data comparison, frozen page-disjoint recipe,
preview and source seals, portable archive links/CRC and `git diff --check` pass.
All 9,584 files in the initial original-evidence inventory, plus its directory
memberships, remain unchanged. Source PDFs/model weights were not copied into Git
or bundles; no model weights were hashed. Raw outputs stay ignored; all changes
remain unstaged. New live accuracy, efficacy of recovery/effort, real compilation,
critic false alarms and human review burden remain untested.

Changed this task: `probe/portable_export.py`; new `probe/recovery.py`,
`experiment.py`, `recovery_trial.py`, `evaluation_export.py`, `text_critic.py`,
`tex_compile.py`, `bibliography.py`, `sciwrite_subset.py`; new
`tests/test_recovery_critic.py`, `scripts/tex-compiler/Dockerfile`,
`docs/RECOVERY-CRITIC-TRIAL.md`, `docs/SCIWRITE-REUSE.md`, upstream MIT licence and
selected evidence summary. Updated README, START-HERE, SPARK-OPERATIONS and this
state. Other working-tree work is preserved.

Next: operator follows [the exact sequential runbook](RECOVERY-CRITIC-TRIAL.md),
runs all tests, qualifies the optional isolated compiler, arranges Qwen using
existing controls, runs fresh exact-model text/vision readiness, gate and
continuation, then builds the experimental candidate and binds the text critic.
Only after that switches to DeepSeek and uses fresh text-only readiness. No
book-wide accuracy or fixed human-decision saving is claimed.

Final compact inspection ZIP:
`results/recovery-preparation-20261023T083548Z-37bf1b-inspection-final.zip`,
7,803,209 bytes / 202 members, SHA-256
`06f7d9b09d364c35bc4b4634f9d94103dd0df1559511725176fe17bcffee91ec`.
It includes HTML/Markdown, both compatibility CSVs/full strings, historical
failures CSV/classification, bibliography, compiler fixtures, exact critic
baseline requests/recipe, source images, validation/test logs, operator commands
and upstream reuse/licence. Full PDFs, raw HTTP/base64/reasoning, model files and
credentials are excluded. CRC, member uniqueness and every report image link
were checked. The earlier 7,772,550-byte core preparation ZIP remains intact.

## 23 October 2026 — isolated compiler input-path and failure-classification fix

Inspected the operator's failed check
`runs/tex-compiler-check-20261023T185222Z-dab36a`: `comparison.json`, both
`execution.json` records and both `console.log` files. The exact image was
`sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45`.
Both invocations ran from `/work` and passed `/source/document.tex`; pdfLaTeX
refused that absolute input under `openin_any=p` before reading the document.
Its subsequent Emergency stop was incorrectly classified as syntax_failure.
The failure does not demonstrate a document syntax error. All nine original
files and their file membership were hashed before and after this change and
remain identical; the historical statuses/logs have not been rewritten.

Narrow adapter change in `probe/tex_compile.py`: keep the source mount read-only
at `/source` and the disposable writable build mount at `/work`; use `/source`
as the container working directory, relative input `document.tex`, environment
`TEXMFOUTPUT=/work` and `-output-directory=/work`. Relative includes/assets
resolve from the source tree. Existing non-root UID/GID, `openin_any=p`,
`openout_any=p`, disabled shell escape, no network, read-only container root,
capability restrictions and memory/CPU/process/time limits remain unchanged.
The single-document API still stages only its exact input; no arbitrary caller
files or surrounding directories are now followed/mounted.

Explicit input/output policy denials take precedence over generic Emergency stop
and classify as `adapter_configuration_failure`, including at comparison level.
They never qualify for compiler-feedback model repair or a compilation claim.
Console and produced TeX logs are used for diagnosis; `texput.log` is now retained
and hashed alongside `document.log`, aux/PDF outputs and the original console.
Real syntax failures retain their existing classification and repair routing.

Focused regressions in `tests/test_recovery_critic.py` cover the actual invocation,
unchanged isolation/resource flags, denial precedence, comparison/repair routing,
and texput.log preservation/classification. A new opt-in real test uses the same
container command on a valid document with a nested relative include, requires
its content marker and PDF/log/aux outputs, and checks source-tree immutability.
It complements the existing real original/proposed compilation test. These real
tests do not run unless `PDF2TEX_COMPILER_IMAGE` is explicitly supplied.

Validation: 53 focused recovery/critic tests, **51 passed and two opt-in real
compiler tests skipped**, no failures/errors. Log:
`results/compiler-path-fix-tests-20261023T190128Z.log`. Changed Python syntax and
`git diff --check` pass. Both saved console logs classify as adapter configuration
failures under the new code without altering their records. The read-only Docker
image inspection was denied at `/var/run/docker.sock`; no permission change,
container execution, image rebuild or installation was attempted. Real compilation
and the relative include remain untested here; mocked execution is not compilation
evidence. The full suite was not repeated for this narrow change.

Updated `docs/RECOVERY-CRITIC-TRIAL.md` with normal-terminal recheck commands using
the exact existing image (no rebuild required). Run the fresh `compile-check`
and require `both_compiled`, then enable the real CompilerTests with that image.
Since `tex_compile.py` is part of frozen experiment code hashes, the earlier
recovery previews/critic recipe intentionally refuse reuse after this fix. This
was checked read-only; do not edit their seals. A new explicit offline preparation
is required before the next live experiment. No replacement preview was created
in this compiler-only task. Existing runs/results/proposals and unrelated work
remain intact; no model/OCR/service calls or Git mutations occurred. Changes to
these four project files remain unstaged.

## 23 October 2026 — recovery/critic preparation refreshed with qualified compiler

The operator successfully qualified image
`sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45`.
Inspected `runs/tex-compiler-check-20261023T191527Z-7efa13`: comparison status is
`both_compiled`, both builds are `passed` with return code zero, and both PDFs,
console/build logs, recorded hashes and corrected invocation settings verify.
The operator reports all nine CompilerTests passed with the image set, including
both real compiler tests and the relative-include test. No standalone terminal
test log was supplied; this test result is attributed to the operator. These
results qualify the isolated adapter on its synthetic fixtures, not book
compilation, visual fidelity or critic accuracy. The failed earlier check and
successful check remain unchanged.

Ran the existing `probe.recovery_trial prepare` offline with explicit
`--max-baseline 267 --max-recovery 80 --hours 6`. Model transport, socket connects
and subprocess execution were blocked during preparation; no compiler, model,
OCR, service, package or image operation occurred. No application, test or script
files changed. Existing functionality also refreshed the dependent critic recipe
and the separate optional diagnostic under new identities.

Actual new paths:

- Preparation/report: `runs/recovery-preparation-20261023T192303Z-57ed87`.
- Qwen preview: `runs/recovery-vision-input-20261023T192304Z-70e8b9`.
- Qwen run: `runs/recovery-vision-trial-20261023T192309Z-cdec02`.
- Critic recipe: `runs/text-critic-recipe-20261023T192309Z-6796b6`.
- Optional diagnostic preview: `runs/schema-diagnostic-input-20261023T192310Z-708e9f`.
- Optional diagnostic run: `runs/schema-diagnostic-trial-20261023T192310Z-252ea1`.
- Detailed refresh audit: `runs/recovery-refresh-checks-20261023T192253Z-ddf8e2`.

All 267 Qwen requests, source images, OCR drafts, instruction/schema bytes,
ordering, 24-region gate, generation settings and recovery/admission budgets
match the old preparation exactly. Visual preview has 819 identical files; only
`preview.json` and its manifest differ, with only `tex_compile.py` changing in
the code map. The diagnostic has the same two changed metadata/seal files and
86 identical files. New run bindings change only preview location, preview seal
and compiler code hash; states differ only in creation time and binding hash.
They remain prepared_offline with zero calls/readiness records: 267 visual and
thirty optional diagnostic units pending.

All forty critic baseline input/request files are byte-identical. The twenty
groups retain ten development/ten reserved groups on disjoint pages, the same
four-pair gate, prompts, exact draft hashes and budgets. Only the compiler code
hash and recipe manifest change. Actual candidate-version requests remain deferred
until the new Qwen candidate exists; no future candidate identity was invented.
Legacy previews, recipes, runs and their hashes were not rewritten to pass.

Verified 9,955 consumed source bindings. Eight preserved artifact directories,
1,147 files and their memberships, earlier bundles and application/test/script
bytes remain unchanged. New preview seals and current-code bindings pass.
The runbook now uses the actual refreshed paths and records the qualified image
as explicit `compiler_args`; the existing runner binds it at first launch and
enforces the same image on resume. `compiler-qualification.json`,
`gate-launch.json` and `refresh-validation.json` in the preparation directory
record those facts without modifying sealed requests. The preparation's Qwen
33/220/143 temporary compiler fixtures remain not_run/unavailable; the separate
operator adapter qualification does not imply those book fragments compiled.

Final compact inspection ZIP:
`results/recovery-preparation-20261023T192303Z-57ed87-inspection-final.zip`,
7,790,976 bytes / 199 members, SHA-256
`1eec4adf2750ea626c0e807ebc9163900e1ad4b2070f0d2f048fe2c179addd6c`.
Includes reports, source images, compatibility CSVs, exact critic baseline inputs,
selection, compiler qualification, refresh validation and operator handover.
Archive CRC, unique members, report links, excluded raw-file types and secret
signature checks pass. Full PDFs, model weights, raw API/base64/ reasoning and
credentials are excluded. The original core ZIP and all older bundles remain.
`git diff --check` passes. No full-suite or real compiler repeat was necessary
for this preparation-only task; live Qwen/recovery efficacy remains untested.

Current operator scope: check workloads, arrange Qwen using existing controls,
obtain fresh exact-model text/vision readiness, then run **only the 24-region
gate with compiler feedback enabled**, bundle and stop for inspection even if
the technical gate passes. The other 243 regions remain pending. Continuation,
candidate assembly, critic execution and optional schema diagnostic are later
steps, not part of this gate handover. All proposals remain UNACCEPTED.

Updated `docs/RECOVERY-CRITIC-TRIAL.md`, the current-trial pointer in
`docs/SPARK-OPERATIONS.md`, this state, and added
[the selected refresh summary](evidence/recovery-critic-refresh-20261023.md).
No Git mutations; all changes remain unstaged and unrelated work is preserved.

## 24 October 2026 — export feedback and a v005-only repair derivative

Inspected completed gate `runs/recovery-vision-trial-20261023T192309Z-cdec02`
and its preview `runs/recovery-vision-input-20261023T192304Z-70e8b9`. All 24
baseline calls supplied valid JSON and claimed selected-block coverage. Eight
proposals were recorded: seven original/proposed pairs `both_compiled`, one
`not_compiled_unsupported_fragment`, zero recovery calls. Another 243 regions
remain pending. These response/build counts do not establish source fidelity.

The missed recovery was v005 / `klebaner-ch4-7-p0065:b14` / original PDF 170,
saved call `0003`. It supplied bare mathematical TeX as `latex_fragment` and
received the exact exporter diagnostic “Raw TeX control or mathematics outside
math mode”. The completion validator recorded this export check but retained a
completed status; the compiler skipped it without returning a recoverable
failure. The scheduler therefore saw no failed response to repair.

Narrow implementation changes in `probe/recovery.py`, `probe/experiment.py`,
`probe/recovery_trial.py` and `probe/evaluation_export.py` add actionable export
feedback to the existing shared mechanism. Feedback carries the exact answer,
field diagnostics, permitted fragment formats, schema and original source
context. It requests representation correction while preserving mathematics;
there is no equation-specific answer, automatic relabeling or relaxed exporter.
Every repaired answer runs identity, JSON/schema, coverage, export and applicable
isolated compiler checks. A persistent original-response anchor prevents an
intermediate malformed repair from enabling a later JSON retry to drop or
rewrite other proposals. Infrastructure/configuration failures remain separate.
All methods share two additional calls per original region, the original overall
recovery allowance and durable reservation accounting across resumes.

The original v005 OCR equation is itself unresolved due to unbalanced braces.
For diagnosis only, verified equation bodies passing the existing safe-command
check can be staged unchanged with recorded display wrappers for the isolated
compiler. This preserves raw bytes and source hashes, does not mark the original
exportable, and permits a proposed build to be measured even if the original
fails. No real compilation of this equation occurred during development.
Unsupported non-equation originals remain explicitly deferred.

New opt-in `repair-prepare --run ... --unit ...` verifies the historical seals,
source hashes, model identity, raw/parsed responses, outgoing requests, call
chains and consumed budgets. It creates a separate code-bound derivative,
copies historical calls unchanged and records their origin. It does not edit old
seals or pretend old calls ran under new code. A second fork from the same parent
is refused to prevent attempt resets. Its sealed scope permits only v005 repair;
`--stage continue` cannot dispatch pending baselines in this derivative.

Prepared offline with transport, socket connects and subprocess execution blocked:

- Preview: `runs/recovery-repair-input-20261024T103428Z-cf096e`.
- Run/report: `runs/recovery-repair-trial-20261024T103428Z-1a2018/report.html`.
- Exact feedback, reassessment and provenance: `repair/request.json`,
  `repair/seed.json`, `repair/provenance.json`, `repair/inherited-state.json`
  inside the new preview.
- Initial inspection ZIP:
  `results/recovery-repair-trial-20261024T103428Z-1a2018-inspection-20261024T103430Z-024f2c.zip`.
- Pointer: `results/export-repair-current.json`.
- Detailed checks: `runs/export-recovery-checks-20261024T101818Z-f56144/final-validation.json`.

State is prepared_offline: 24 inherited calls, zero new calls, 23 completed units,
one repair_pending and 243 pending. Inherited elapsed admission time is
817.8629703969928 seconds; 20,782.137029603007 seconds remain within six hours.
v005 has two additional calls remaining; the global recovery ceiling remains
80, with none consumed. The inherited compiler image is mandatory:
`sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45`.
The operator's previous synthetic real check `tex-compiler-check-20261023T191527Z-7efa13`
and reported nine passing CompilerTests remain the qualification evidence; they
do not establish that this book fragment compiles.

Preservation checks passed: all 267 original request bodies/data, image hashes,
unit order and selection are unchanged, including every pending input. All 24
inherited call directories match byte-for-byte. All 1,131 original preview/run
files and their memberships remain unchanged. All 11,086 bound source hashes
and new code/preview seals verify. Historical outcomes stay historically completed;
the export reassessment is separate. Reports distinguish valid response,
exportability, original/proposed compilation, unresolved/deferred proposals and
inherited versus new calls. Inherited gate success is not a fresh compilation
or fidelity claim. All proposals remain UNACCEPTED.

Validation: all 17 focused `tests/test_export_recovery.py` regressions passed,
including the exact saved v005 response, a correctly formatted mocked repair,
valid math-body controls, unchanged gate successes, schema/identity/coverage
checks, exhausted repairs, persistent original-answer anchors, interrupted-answer
reconciliation and durable shared accounting across resume/derivative preparation.
Full controller suite: **260 tests; 243 passed, 15 errors from sandbox-denied
mock loopback sockets, two opt-in real compiler skips, no assertion failures**.
Log: `results/export-recovery-full-tests-20261024.log`. Changed Python syntax and
`git diff --check` pass. No permissions were changed. The normal-terminal full
test command, with `PDF2TEX_COMPILER_IMAGE` set, is in the runbook. Mocked model
and compiler results do not establish live repair efficacy or real compilation.

The initial compact ZIP is 11,505,978 bytes, 296 unique members, SHA-256
`6f0692e10942f3e64d89aff9ecb73ddb1898d6b9d1e7179e91f8e92762923129`.
CRC and report image links pass; raw full PDFs/model weights are excluded.
It contains reports, failures CSV, ledger, images and repair provenance; raw
response bodies/reasoning and the full encoded feedback request remain in runs/.
Selected summary: [export recovery evidence](evidence/export-recovery-gate-20261024.md).

Current operator scope: full normal-terminal tests, fresh exact Flash Next
text/vision readiness, then the prepared **v005-only repair with the qualified
compiler**, inspect and bundle. At most two additional calls; no baseline replay
and no launch of the pending 243. Broader continuation and dependent critic
refresh are separate subsequent work. Model changes to representation still
require human/source assessment of mathematical preservation. No inference,
OCR, install, service operation, acceptance or Git mutation occurred. Updated
the recovery runbook and SPARK-OPERATIONS pointer; unrelated work is preserved
and every change remains unstaged.

## 24 October 2026 — operator test-command image-ID correction

The operator supplied a full-suite summary: 260 tests, two errors in the opt-in
real compiler tests; the other 258 passed. Both traces stop in
`tex_compile.command()` at immutable image-ID validation before Docker execution.
The assistant's previous final chat command accidentally omitted `228` from the
qualified SHA-256 ID, leaving 61 hexadecimal characters rather than 64. This was
a handover transcription error, not a compiler adapter or document failure.
The saved successful compiler execution, prepared repair state/preview and
runbook all retain the correct image ID:
`sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45`.

Updated the runbook to read `compiler_image` directly from the actual prepared
repair state and remind the operator to rebuild `compiler_args` after correcting
the variable. The separate “Command 'Set' not found” indicates explanatory prose
was entered as a shell command; no package installation is needed. Only fenced
command blocks should be pasted into the shell.

Inspected the operator's new readiness record
`runs/recovery-readiness-20261024T105529Z-cd24ce`: exact Flash Next config,
Text passed, vision qualified, strict JSON unsupported as expected; finished at
10:55:37 UTC. It remains subject to the existing one-hour freshness limit.
The repair run remains prepared_offline with 24 inherited calls and zero new
calls. No duplicate preview, code change or seal modification is needed.

Offline checks reproduced rejection of the shortened ID and acceptance of the
recorded 64-character ID by the command builder without invoking Docker. The
new preview/current-code bindings, readiness seal and documented shell syntax
verify; `git diff --check` passes. Real compiler tests/full-suite rerun are for
the operator's normal terminal with the corrected variable. No model calls,
compiler execution, service operation or Git mutation occurred here. Only this
state and `docs/RECOVERY-CRITIC-TRIAL.md` changed in this follow-up, unstaged.

## 24 October 2026 — continuation of the remaining 243 Qwen regions prepared offline

Verified the completed repair derivative
`runs/recovery-repair-trial-20261024T103428Z-1a2018`, including sealed call 0025,
its raw response and export/build results. It inherited the original gate's 24
baseline calls and made one `export_feedback` call for v005. The replacement is
export-supported; its proposed isolated TeX build passed (return code 0 and
recorded PDF). The original OCR build remains `syntax_failure` (return code 1).
The pair is `preexisting_or_context_failure_unresolved`, not `both_compiled`.
All original and repaired proposals remain UNACCEPTED. One inherited uncertain
proposal remains deferred; a build or valid response is not a fidelity judgment.
The completed repair's latest ZIP is
`results/recovery-repair-trial-20261024T103428Z-1a2018-inspection-20261024T111107Z-452676.zip`,
SHA-256 `3644a67e1df154ea95cabb0474b8cd668711da9054b27bb39cd869c014d66ff7`.

The existing repair derivative deliberately refused continuation. Added only
the necessary opt-in `probe.recovery_trial continuation-prepare --run ...`
operation, sharing historical-parent verification with repair preparation. It
requires a completed visual repair, passed inherited gate, unchanged call chains,
raw model identities, source bindings, compiler identity and available cumulative
admission time. It freezes the pending non-gate IDs, preserves every inherited
call/outcome byte-for-byte, and binds current code in a new linked artifact.
Recorded old code hashes remain provenance, not a claim that old requests ran
under new code. A second fork from the same parent is refused; resume the prepared
continuation instead. No old seals or recorded hashes were patched.

The executor accepts only `--stage continue` for this new derivative and refuses
missing/changed compiler arguments, modified inherited calls/time, changes to
completed out-of-scope units, or new calls outside the allowed pending scope.
Existing durable reservations, response/export/compiler validation, per-region
and global recovery limits, pauses and identity/integrity stops are reused.
Reports identify inherited versus newly produced calls and include continuation
provenance in the inspection ZIP. Uncertain proposals remain deferred; there is
no automatic acceptance, candidate assembly or critic launch.

Actual preparation (transport, socket connects and subprocesses blocked):

- Preview: `runs/recovery-continuation-input-20261024T112538Z-e1a1ef`.
- Run: `runs/recovery-continuation-trial-20261024T112538Z-8d13d3`.
- HTML: `report.html` in that run; exact baseline inputs/requests in the preview.
- Lineage: `continuation/provenance.json` and `continuation/inherited-state.json`
  in the preview, retaining the earlier repair provenance as well.
- Current pointer: `results/recovery-continuation-current.json`.
- Verification: `runs/continuation-checks-20261024T112017Z-19e3b8/final-validation.json`.
- Initial ZIP:
  `results/recovery-continuation-trial-20261024T112538Z-8d13d3-inspection-20261024T112540Z-9330de.zip`.

Prepared state: 25 inherited calls (24 baseline + one recovery), zero new calls,
24 completed regions and exactly 243 pending regions. All 267 baseline request
bodies/data, source images, unit order, selection and settings match both prior
previews byte-for-byte. Only pending IDs are dispatchable. All 2,287 files and
membership in the original gate/repair runs and their previews remain unchanged;
all 25 copied call directories match the repair parent byte-for-byte. The prior
latest bundles verify against their recorded hashes. All 12,242 bound source
hashes and the new code/preview seals verify.

Accounting is inherited, not reset: 839.6103107519448 admission seconds consumed;
20,760.389689248055 seconds remain. Limits stay 267 baseline calls, 80 additional
recovery calls shared across methods, two additional calls per original region,
21,600 cumulative seconds. Remaining allowance is 243 baseline and 79 recovery
calls. v005 has used one of its two recovery slots but is completed and excluded
from this continuation. Qwen settings are unchanged: `flash-next-tensorfold` at
`http://127.0.0.1:8890/v1`, medium effort, 16,384 output tokens, 600 seconds,
sequential, server sampling defaults omitted and no server-enforced JSON format.
Strict local response validation remains. The inherited qualified compiler image
is mandatory and read from the prepared state in operator commands to avoid
another manual hash transcription error.

Validation: all seven new `tests/test_recovery_continuation.py` checks passed.
They cover explicit old/new code binding, exact inheritance and pending-only
dispatch, retained original/proposed compilation distinction and uncertainty,
shared limits across pause/resume, per-region consumed allowance, forbidden
counter/time resets, compiler/stage/fork restrictions and stale parent evidence.
Full controller suite: **267 tests, 250 passed, 15 sandbox-denied mock socket
errors, two opt-in real compiler skips, no assertion failures**. All 15 error
tracebacks are socket setup `PermissionError: [Errno 1] Operation not permitted`.
Log: `results/continuation-full-tests-20261024.log`. Python syntax, documented
shell syntax and `git diff --check` pass. No permissions were changed and no real
model/compiler call was executed here. Normal-terminal tests with the qualified
image and the live continuation remain operator steps.

Initial inspection ZIP: 11,625,252 bytes, 298 unique members, SHA-256
`3373eeaed1c8beb803044a9b604817eccd3439f30e18f1dfd2eb48925c4c0fad`.
CRC and all inspection image links pass; full PDFs/model weights are excluded.
The report and ZIP distinguish inherited gate/repair evidence from zero new
continuation calls. Selected summary:
[Qwen continuation preparation](evidence/qwen-continuation-20261024.md).

Changed `probe/recovery_trial.py`, `probe/experiment.py`,
`probe/evaluation_export.py`, added `tests/test_recovery_continuation.py`, and
updated the recovery runbook, SPARK-OPERATIONS pointer, this state and selected
evidence summary. The current runbook supplies actual paths, fresh readiness,
compiler-enabled `--stage continue`, read-only monitoring, orderly pause/resume
and partial/final bundling. No service changes, installs, inference, OCR, Git
mutations or acceptance; all changes remain unstaged and unrelated work preserved.

## 2026-10-24 — 31-proposal assessment, protected candidate and frozen text-critic gate

Observed the completed continuation
`runs/recovery-continuation-trial-20261024T112538Z-8d13d3`, bound to
`runs/recovery-continuation-input-20261024T112538Z-e1a1ef`. All 267 regions have
technically validated final answers. The durable record contains 275 calls:
267 baseline, four JSON feedback and four export feedback; cumulative admission
6,672.5581475258805 seconds. There are 31 final proposals, all UNACCEPTED.
29 proposed replacements have passed compilation (28 `both_compiled` plus v005's
proposed-pass/original-syntax-failure distinction). v034/v036 heading comparisons
were skipped because their original OCR was unsupported: **proposed compilation
was not attempted**, not attempted and failed. Technical completion/compilation
is not content-preservation or mathematical-fidelity evidence.

Bounded Codex assessment, not human verification: inspected all 31 complete
replacement strings, their original blocks/structured OCR and existing source
detail images; additionally used full-page context for physical pages 166, 170,
205 and 212 only to interpret these proposals. No repeat of the 267-region audit,
no whole-page omission or whole-book accuracy claim. Result: **27 suitable for
experimental application, four deferred**. v105/p0100:b15 would replace an entire
paragraph with just its stopped exponential, deleting definitions, assumptions
and references; its useful diagnosis remains saved but no substring repair or
completed response was invented. v138 remains explicitly uncertain; v250 and
v210 are unnecessary cosmetic changes with incorrect descriptions of the original
TeX. v093 removes an unmatched parenthesis actually printed in the source: an
explicitly authorized minor editorial repair, recorded separately from Qwen's
incorrect OCR-error classification. v224's original already contained x^a; only
the t accent is corrected. v001 retains a minor missing comma. Printed apparent
sign/limit issues elsewhere are preserved. No overlapping targets or declared
dependencies occur among these 31.

Candidate assembly now requires a complete separate assessment matching exact
proposal/call/source/run versions. Missing assessments apply nothing; deferred,
incomplete, uncertain, conflicted and unavailable dependent groups cannot be
applied. No length heuristic, JSON result or compiler success substitutes for
whole-block inspection. `candidate --dispositions PATH` saves decisions separately
and never changes acceptance. Historical reviews are verified against their own
bindings/call seals/raw identities; the new derivative records current assembly
code separately. `critic-refresh --recipe PATH` explicitly refreshes code binding
only after the frozen baseline requests still match the current critic protocol;
old recipe and seals remain unchanged.

Actual artifacts:

- Audit: `runs/proposal-audit-20261024T134532Z-6a438a`; `report.html`, `report.md`,
  `dispositions.csv`, exact-bound `dispositions.json`, full proposal/native pool,
  source images, `findings.json`, `critic-preparation.json`, `validation.json`.
- Candidate: `runs/evaluation-candidate-20261024T140145Z-6343d9`; `candidate.tex`,
  `report.html`, `inventory.json`, `changes.json`, `provenance.json`, compiler logs.
- New linked frozen recipe: `runs/text-critic-recipe-20261024T140149Z-e7a9d7`;
  parent `runs/text-critic-recipe-20261023T192309Z-6796b6`.
- Critic preview: `runs/text-critic-input-20261024T140150Z-062adf`.
- Critic run: `runs/text-critic-trial-20261024T140153Z-32efd8`; zero live calls.
- Combined inspection ZIP:
  `results/reviewed-candidate-critic-20261024T140145Z-6343d9-inspection.zip`;
  13,531,336 bytes, 403 unique members, 283 deduplicated source images, SHA-256
  `68d56d4ad8af9c87cdf0489dc0a585c194b917046c20a1d405c974da5dc8e21e`.
  Includes disposition table, complete before/after evidence, derivative/inventory,
  exact critic preparation, validation and operator instructions; no full PDFs or
  model files. ZIP CRC and report image links pass. Local HTML image links are
  adapted for portability; historical/local file seals still describe originals.
- Pointer: `results/reviewed-candidate-critic-current.json`.
- Selected evidence: [31-proposal assessment and critic preparation](evidence/reviewed-candidate-critic-20261024.md).

The derivative inventories all 267 blocks on 16 pages, applies 27 proposals and
leaves all four deferred originals and every unaffected draft string unchanged.
Three other blocks remain nonportable: `klebaner-ch4-7-p0031:b4`,
`klebaner-ch4-7-p0081:b3`, `klebaner-ch4-7-p0081:b19`. Complete raw OCR/source images
remain available with explicit unresolved TeX placeholders, not silent omission.
This is an experimental, incomplete editable derivative, not an accepted export.

Candidate compilation was attempted with the qualified immutable image
`sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45`, but Docker
socket access was denied before TeX started. The existing adapter records
`build_failure_unresolved`, return code 1, `compilation_claim=false`; the console
shows the infrastructure denial. No document syntax conclusion or successful
build is claimed. The runbook provides a normal-terminal sidecar compilation of
the frozen candidate and separate proposed-only builds of both headings, without
altering candidate hashes or mislabelling them original/proposed comparisons.

All 40 old baseline input/request files are byte-identical in the new critic
recipe; groups, 10-development/10-reserved split, ordering, prompts and budgets
are unchanged. The actual candidate/baseline draft hashes are bound. Inputs are
neutral exact text/schema only, with no images, Qwen rationales, assessment
diagnoses or answers. Existing windows include 17 of 27 applied replacements,
with 11 changed pairs; this critic is not a review of every proposed correction.
All eight requests in the initial four-pair gate are available. Reserved g16-Y is
unavailable because p0081:b19 is unresolved. Its baseline g16-X and gate baseline
g04-X retain their frozen complete structured OCR fallbacks; those are not
portable-LaTeX baselines or silently cleaned replacements. Do not count the
unavailable reserved pair as a complete comparison.

Critic settings remain regular `DeepSeek-V4.1-Flash-TF` at
`http://127.0.0.1:8894/v1`, medium effort, 16,384 output tokens, 600 seconds,
sequential, sampling defaults omitted. Limits remain 40 baseline, 24 shared
recoveries, two extras per request and four cumulative hours. First live
experiment step is the four-pair gate only; later development and reserved stages
require inspection and are not automatically launched. The existing regular
DeepSeek retry launcher and Qwen stop wrapper were inspected read-only, not run.
No GLM or other deployment substitution is authorized for this preparation.

Validation: **277 tests run, 260 passed, 15 mock socket setup errors, two opt-in
real compiler skips, zero assertion failures**. All 15 errors are
`PermissionError: [Errno 1] Operation not permitted` at mock server socket setup.
Log: `results/reviewed-candidate-full-tests-20261024.log`. Ten new focused checks
pass, including saved v105, deferred original preservation, exact-version/stale
binding rejection, unresolved raw OCR, historical/current code separation and
frozen-recipe refresh refusal when protocol changes. Existing conflict/dependency
and text-only input tests also pass. Python syntax, documented shell syntax and
`git diff --check` pass. All 3,515 files and membership of the completed run, its
preview and old recipe remain unchanged; all 275 call seals and 12,899 critic
source bindings verify. No speed optimisation, inference, OCR, installations,
service operations, Git mutation or acceptance occurred; unrelated edits remain.

Files changed in this task: `probe/evaluation_export.py`,
`probe/recovery_trial.py`, `tests/test_recovery_critic.py`, new
`tests/test_reviewed_candidate.py`, `docs/RECOVERY-CRITIC-TRIAL.md`,
`docs/SPARK-OPERATIONS.md`, this state and the selected evidence summary above.
Next operator action: full normal-terminal tests (qualified compiler ID loaded
from the saved run), optional separate candidate/heading compilation, workload
inspection, regular DeepSeek readiness, then **only the four-pair critic gate**.
The current runbook defines actual paths/variables afresh and provides report/ZIP
commands. Do not regenerate the already prepared candidate or critic to launch it.

## 2026-10-24 — Critic quotation repair and bounded eight-unit follow-up (offline)

Read `/home/mdi/Downloads/pdf-to-latex-critic-repair-20261024.txt` and independently
verified the completed failed gate
`runs/text-critic-trial-20261024T140153Z-32efd8`, its bound preview
`runs/text-critic-input-20261024T140150Z-062adf`, source/candidate bindings and all
ten sealed call directories. Observed 2361.8064247909933 admission seconds,
four completed/four failed gate units, 31 untouched pending units and one
unavailable reserved unit. Gate totals: 4 first valid, 4 final valid, 3 complete
claimed coverage against unchanged thresholds 6/8/6. The task's final ZIP at
`results/text-critic-trial-20261024T140153Z-32efd8-inspection-20261024T151212Z-b45b1d.zip`
exists, passes CRC and hashes to
`05657ee1a765a42154d0fd12ea038acf7021def5981cc0d616068135f52d462f`.
There is also a later operator bundle at
`results/text-critic-trial-20261024T140153Z-32efd8-inspection-20261024T164714Z-3f69dd.zip`
(SHA-256 `57d4a95a1aa206d37743bd8a4f767a567a6b36bcee719940e650cb91b9756168`).
Both were preserved; no historical summary was rewritten.

Confirmed g02-X's three responses fail exact quotation validation at
`$.findings[2].quotes[0]`, block `klebaner-ch4-7-p0100:b12`. Actual outgoing spans
match the validator data. The quote adds an opening inline-math delimiter where
math mode was already active in the full span. It must be copied verbatim and
need not compile independently. Also found the old substance-preservation guard
would reject an otherwise valid repair because the quotes field changed. Generic
critic instructions now prohibit balancing, completing, reformatting or correcting
quotations; feedback supplies the exact offending field/block and unchanged source
span as untrusted data. Only invalid citations may change; other substantive
finding fields, valid citations and uncertainty are preserved. An original-finding
anchor survives intervening bad repairs/resumes. No fuzzy matching, stripping,
normalisation or weakened identity/location/hash checks was added.

Complete, parseable, correctly bound rejected responses can now expose independently
validated findings as provisional diagnostics. Each g02-X response has two such
findings and one invalid finding, all retained per attempt. These are not six
independently established defects. Provisional findings never change completion,
acceptance or gate credit; valid citations do not establish mathematical correctness.
Incomplete/truncated JSON is never closed or partially extracted. General prompt
changes prioritise material mathematics, inspect complete sentences/headings for
parentheses, avoid unnecessary formatting-driven source-image tasks, and connect
missing context to particular assessments while continuing independent checks.
The existing sciwrite-lint prompt-protection adaptation is reused unchanged.

Budget evidence: g03-X reached `length` with 16384 completion tokens and 3048
final-content characters of partial JSON; g04-X/Y reached `length` with 16384
completion tokens and no final content. Separate reasoning-token counts are absent,
not zero. Saved `reasoning` and `reasoning_content` are duplicate strings, with final
output separately in `content`. Qualitative inspection shows substantive analysis
mixed with repeated reconsideration of findings, context, severity and presentation,
including grading speculation in g04-Y. It does not establish an identical-output
loop or prove that a larger allowance only extends repetition. Live improvement
from the revised instructions/budget remains untested.

Read-only runtime investigation used the recorded regular launcher and deployment
`/home/mdi/local-llm/deepseek-flash17-setup/first-serve-853310da-v1/runs/20261024T142607Z-307224`.
Its command explicitly sets `--max-tokens 32768`; runtime image
`sha256:35d9bda39ffde364249f21be294dde6aeee9c51940973477ca5728f32422aa35`
matches the available image archive's configuration digest. Inspected binary bytes
without executing/extracting a runtime: embedded messages explicitly say max_tokens
counts reasoning plus final content, and validation strings name medium. Runtime
binary SHA-256: `f9d0164fa5d5e11f65e25133123340e5c4894f5e1fe5c957abff6f656ffae6d1`.
Full runtime source/effective-effort telemetry were unavailable: exact medium mapping
or whether it was honoured is not established, and it is not called ignored.
No endpoint probe or service operation was performed. `runtime-support.json` records
whitelisted metadata, hashes, scope of support and uncertainties. The binary and
weights are excluded from the project ZIP.

The new follow-up requests regular `DeepSeek-V4.1-Flash-TF` at
`http://127.0.0.1:8894/v1`, medium, 32768 tokens, 900 seconds, serial execution and
unchanged sampling defaults. This is a response-completion experiment, not proof
that medium is honoured. Lower-reasoning recovery stays disabled because its
mapping/effect and the reasoning-only token trigger are not established. Only the
new text-critic client purpose gains the larger token/timeout bounds; capability
preflight and page-review bounds/behaviour stay unchanged. No server change was
needed or made. Accuracy remains the priority; speed optimisation is deferred.

Reporting now counts successful and nested failed usage/latency, deduplicates calls,
and separates inherited/current/recovery contributions. Missing counters have null
totals plus reported sums and missing-call counts, rather than fabricated zeros.
The two failed feedback calls account for **9535 tokens and 175.782564106863 seconds**;
the original summary recorded zero for both. Corrected historical reports are new
derived artifacts, with their own code/source provenance. Request-latency sums and
full admission/wall time remain separate.

New explicit `critic-followup-prepare --run ... --runtime-evidence ...` workflow
verifies historical seals/bindings and recorded runtime support, then creates a new
experiment with lineage. It does not resume the old failed run or reset its counters.
A narrow historical-verifier correction recognises an untouched unavailable unit
only when its status/reason match the sealed preview; it does not bypass integrity.
All eight complete input files and user messages are byte-identical to the old gate.
Only system instructions and max_tokens differ in outgoing request bodies. The
same order/neutral labels remain; old-versus-new settings and original 10 calls /
2361.806 seconds are recorded. No additional context, images, Qwen rationales,
audit diagnoses or expected answers enter requests.

Bounds are eight initial calls, at most eight shared additional calls, at most two
extras per unit, four cumulative admission hours; an admitted request may finish
up to 900 seconds beyond the admission boundary. The 6/8/6 technical thresholds
are unchanged. All eight are previously observed development/diagnostic cases,
not unseen gold. The remaining 32 units are absent from the new preview; the old
20-group recipe, reserved selection and unobserved responses remain unchanged.
Only gate execution is supported for this bounded preparation.

Actual artifacts:

- Audit: `runs/critic-followup-audit-20261024T170212Z-523425`; `report.html`,
  `report.md`, `quote-diagnosis.json`, `runtime-support.json`, `validation.json`,
  call metrics, before/after settings and focused/full test logs.
- Revised historical report: `derived-old-report/report.html` inside that audit,
  with revised Markdown/summary/ledger/failures CSV and separate provenance.
- Follow-up preview: `runs/text-critic-followup-input-20261024T171424Z-47ad07`.
- Follow-up run: `runs/text-critic-followup-trial-20261024T171424Z-8bb3c1`;
  prepared offline, zero calls. `lineage.json` is in the preview.
- Compact preparation ZIP:
  `results/critic-followup-preparation-20261024T171424Z-47ad07-inspection.zip`;
  819498 bytes, 51 unique members, SHA-256
  `5032782874df599dfb808ed04b4d2e804f889111620af822b9a2b11ffbf64573`.
  Includes diagnosis, changed-behaviour documentation, provisional reports,
  test evidence, exact new requests/settings/lineage and operator instructions.
  CRC/membership checks pass; no credentials, full source PDFs, environments,
  weights or raw reasoning are included.
- Pointer: `results/critic-followup-current.json`.
- Selected summary: [Critic follow-up preparation](evidence/critic-followup-20261024.md).

Validation: all **13 new focused regressions passed**, including the saved failure
shape and actual g02-X evidence, genuinely incorrect mathematical quotation,
substantive preservation, no truncated-response salvage, diagnostic separation,
actual mocked outgoing serialization at 32768/900, unchanged inputs/lineage,
remaining-unit exclusion, durable per-unit recovery/anchor behaviour, old/new report
separation and missing-counter accounting. Full suite: **290 tests, 273 passed,
15 sandbox-denied mock socket setup errors, two opt-in compiler skips, no assertion
failures**. The compiler opt-in environment variable was explicitly unset for tests;
no unrelated real compiler qualification was repeated. Python syntax, documented
shell syntax and whitespace checks pass. All 509 files/membership in the old run,
preview, candidate and frozen recipe remain unchanged; both old inspection ZIP
hashes and all 13078 bound source files verify. No model/API calls, OCR, services,
installs, permissions changes, Git mutations or acceptance occurred.

Changed `probe/text_critic.py`, `probe/recovery.py`, `probe/experiment.py`,
`probe/evaluation_export.py`, `probe/recovery_trial.py`, `probe/local_model.py`,
new `tests/test_critic_followup.py`, the recovery runbook, SPARK-OPERATIONS pointer,
this state and the selected evidence summary. Unrelated changes are preserved and
all edits remain unstaged. Next operator action: normal-terminal full tests,
read-only workload/regular-deployment checks, fresh TEXT-ONLY readiness, then ONLY
the new eight-unit gate. The runbook defines/validates each block's variables,
rejects an empty pasted readiness path, and separates later status/report/ZIP steps.
The revised prompt, recovery and 32768/900 completion behaviour remain untested live;
neither offline checks nor citation validation establish mathematical correctness.

## 24 October 2026 — passed critic gate; frozen overnight continuation prepared

Read `pdf-to-latex-critic-overnight-20261024.txt` and the required project/operator
documentation. The operator authorizes a new fixed continuation through the existing
reserved set after a predeclared technical checkpoint; accuracy has priority and
speed optimisation is deferred. All prior work and evidence remain unchanged.

Verified the actual completed follow-up run
`runs/text-critic-followup-trial-20261024T171424Z-8bb3c1`, its preview
`runs/text-critic-followup-input-20261024T171424Z-47ad07`, and the specified completed
inspection ZIP ending `20261024T192457Z-45ee3b.zip` (SHA-256
`811fcdb49df16ca533a6b13332c085f28dd1cde254ae1894bb6ab7cbf98176c8`).
Observed **7/8 first valid, 8/8 final valid, 7/8 complete claimed coverage**, nine calls,
2344.654650 seconds (39.08 minutes). g03-Y's JSON escape error was repaired with one
feedback call. No quote-validation/token-exhaustion failure occurred. All responses
had exact regular DeepSeek identity and finish_reason=stop. Prompt/completion totals
33738/122016; separate reasoning-token counts absent for all nine, not zero.
Requested medium does not establish its effective server interpretation.

The operator-supplied external **ChatGPT assessment**, explicitly not human gold,
is recorded separately in [selected evidence](evidence/critic-overnight-20261024.md).
Codex inspected six existing source crops and checked every final finding quotation
against the saved passage offsets. PDF 170 b14/b16 really print positive inner
exponents, inconsistent with the b12 integrating-factor derivation; Qwen preserved
the printed source. The critic's alternative future-random-factor integrand is
generally anticipative, and its zero-mean claim requires true-martingale assumptions.
PDF 205 tau/bold-1 and PDF 106 dot-1/c_gamma warnings disappear in revised text.
The c0 endpoint reuse is not a material mathematical defect; missing definitions
remain context requests. The true-martingale concern appears only for g04-X despite
unchanged relevant assumptions in Y. v105/b15 lies outside g02's b5–b12 window and
remains deferred with the complete original paragraph unchanged. No candidate/source
text or acceptance status was modified, and none of these assessments enters requests.

Implemented the narrow opt-in `probe.critic_overnight` preparation/controller/report
wrapper and a guarded `overnight` path in the existing serial executor. It reuses
strict identity, schema and exact quotation checks, targeted bounded recovery,
project locks, readiness, raw attempts, seals, cumulative budgets and reports. No
new inference framework or prompt/validator/feedback tuning. The original failed
critic and passed follow-up keep their historical code bindings and counters.
New lineage records them; their calls are neither replayed nor double-counted.

Both stages are frozen before launch. Development g05–g10: 12 slots, PDF pages
126/156/166/176/212/212. Reserved g11–g20: 20 planned slots, 19 callable; only g16-Y
is unavailable because candidate p0081:b19 is unresolved (PDF 186). Nine available
reserved pairs and unpaired g16-X are reported separately. Planned denominators
retain unavailable/failed/pending work. All 32 input JSON files are byte-identical
to the original 40-unit preparation and preserve location/draft/bibliography data,
neutral version labels and split ordering. Requests match the successful follow-up's
generic system/schema/quotation/recovery behaviour: regular DeepSeek-V4.1-Flash-TF,
localhost:8894, requested medium, 32768 tokens, 900 seconds, non-streaming, unchanged
omitted sampling defaults, lower-reasoning recovery disabled. No images, diagnoses,
expected answers, Qwen rationales, context expansion or candidate regeneration.

After all development units reach their allowed outcomes, reserved dispatch requires
**9/12 first valid, 12/12 final valid, 9/12 complete claimed coverage** and no unresolved
identity/integrity failure. The checkpoint is recomputed on resume before reserved
admission; it does not rewrite the earlier eight-unit gate. Failure stops and bundles.
Passing proceeds without a human wait or tuning. This is one-time reserved evaluation;
once examined, these results are not unseen for later revisions. Future tuning
requires new reserved material. Technical validity is never mathematical correctness.

Bounds: **31 baseline + 16 global additional calls**, maximum two extras per parent.
One eight-hour wall deadline from first substantive reservation includes pauses and
resumes. No dispatch after exhaustion; one in-flight request may finish within its
900-second timeout. Only local report/ZIP cleanup follows (normally seconds, no
hard filesystem-time guarantee). Existing connection handling and identity/integrity
stops remain; no automatic service operations. All findings remain UNACCEPTED.

New actual artifacts:

- Preview: `runs/text-critic-overnight-input-20261024T211031Z-de4d3d`.
- Run: `runs/text-critic-overnight-trial-20261024T211031Z-63fbda` — **prepared_offline,
  zero calls**, 31 pending and one unavailable. Not launched by Codex.
- Bound launcher: `runs/text-critic-overnight-input-20261024T211031Z-de4d3d/operator-launch.sh`.
- Report: `runs/text-critic-overnight-trial-20261024T211031Z-63fbda/overnight/report.html`,
  with separate development/reserved HTML, Markdown and JSON views.
- Initial compact inspection ZIP:
  `results/text-critic-overnight-trial-20261024T211031Z-63fbda-inspection-20261024T211034Z-459c8b.zip`,
  928826 bytes, SHA-256 `629eb03228de8bfe4ad6dbf2f77808c2b186087f5ab65e42afc82509558ddd72`.
- Separate assessment/validation: `runs/critic-overnight-audit-20261024T211110Z-d3f875`.
- Exact-path pointer: `results/critic-overnight-current.json`.

The controller saves a timestamped inspection ZIP after normal completion, deadline,
checkpoint failure or controlled pause, with its actual path/size/hash in
`latest-bundle.json`. Separate stage views preserve original/revised findings, exact
quotes and page/block IDs, mathematical consequences, context needs and editorial
observations; rejected attempts receive no completion credit. Failures and every
reported usage counter remain available, with unknown distinct from zero. Includes
exact selected inputs, requests, final answers, failed content, CSV and provenance;
excludes full PDFs, weights, environments, credentials and unrelated raw material.
Raw reasoning stays in original run records. No whole-page or whole-book claim.

Offline validation: **301 tests, 284 passed, 15 sandbox-denied mock socket setup
PermissionErrors, two opt-in real compiler skips, no assertion failures**; elapsed
140.423 seconds. All **11 new regressions passed**, covering stage selection, no gate
replay, direct-stage exclusion, failed checkpoint, independent first/coverage thresholds,
mutation rejection, unavailable-slot pairing, durable per-parent/global caps, pause
and in-flight deadlines, failed usage and historical non-double-counting, and ZIPs.
No permission changes or unrelated real compiler qualification. Python syntax,
eleven operator Bash blocks, bound launcher syntax and `git diff --check` passed.
All 278 historical run/preview snapshot files and directory membership are unchanged;
13184 bound source hashes verify, including original candidate/recipe seals and the
completed ZIP. New preview ZIP CRC, unique membership, exclusions and secret scan pass.

Changed `probe/experiment.py`; added `probe/critic_overnight.py` and
`tests/test_critic_overnight.py`; updated `docs/RECOVERY-CRITIC-TRIAL.md`,
`docs/SPARK-OPERATIONS.md`, this state and the new selected evidence document.
All changes remain unstaged. No endpoint/model call, OCR, TeX compilation, service
operation, installation, permission change, Git mutation or acceptance occurred.
Next operator action: full tests with `PDF2TEX_COMPILER_IMAGE` unset for that command,
read-only both-node workload/regular-deployment checks, then fresh text-only readiness
inside tmux and the actual bound launcher in the runbook. Every block defines its
variables and rejects blank pasted readiness. Estimated a few hours (roughly 2–4
if like the observed gate), not promised; no work added merely to fill the night.
Live continuation reliability, effective medium semantics and substantive mathematical
quality remain untested. New substantive assessment follows completion.

Final compact preparation/assessment package:
`results/critic-overnight-preparation-20261024T211031Z-de4d3d-inspection.zip`,
1240290 bytes, 108 unique entries, SHA-256
`a815316b3e1c454312cd7194f95800fa7f2d05c0c27538f3e3781905c2d1688c`.
It combines the prepared experiment views/requests with the separate ChatGPT
assessment, six source crops, exact checked quotations, validation logs, operator
instructions and the narrow implementation/test files. CRC, uniqueness and exclusion/
secret-pattern checks pass. No assessment is inserted into model requests.

## 25 October 2026 — bounded GLM / MiMo critic comparison, prepared offline

User authorization replaces the proposed Kimi arm with MiMo and explicitly accepts
documented provider retention **below 100 days** for this project's nonpersonal
published book material. Xiaomi's documented 30-day retention is acceptable; ZDR
is no longer mandatory. The narrow, explicitly authorized AGENTS amendment records
this without changing unrelated instructions. Conversion and default criticism stay
local. Only the twelve frozen selected passages may go to MiMo; no cloud OCR,
whole-book upload, automatic provider fallback, training opt-in or account privacy
change. The real credential was not read, inspected, created or validated.

New `probe/critic_pilot.py` reuses the saved critic schema, exact-quote checks,
feedback, seals, progress and shared executor. The explicit `pilot` stage cannot
be launched through other experiment stages. Local GLM is `glm53-regular` at
`http://192.168.1.100:8888/v1`, requested high; MiMo is `xiaomi/mimo-v2.6-pro` at
OpenRouter, pinned to standard `xiaomi/fp8`, explicitly enabled reasoning with no
graded effort claim. Both use 32768 output tokens, 900 seconds, serial non-streaming
requests and omitted sampling defaults. Twelve baselines and four shared extra
format/quote calls per arm; two extras per parent; no lower-effort/exhaustion retry.
The existing executor's cumulative admission time is bounded to eight active hours.
Two harmless text-only readiness calls per arm, each at most 2048 tokens / 120 seconds,
are separately counted; failed/interrupted readiness consumes its slot.

`probe/cloud_critic.py` is a separate explicit paid transport; local URL checks and
the conversion CLI are unchanged. Runtime-only private key access requires owned
600 file / 700 parent; fake disposable credentials were used in tests. Fixed HTTPS
origin, verified TLS, no redirect/proxy/fallback/retry, no paid plugins or remote
tools. `data_collection=allow`, `zdr=false`, exact provider pin, require_parameters;
no ZDR-list call. The accepted public provider policy is recorded with its source
and date, distinct from live metadata qualification. Before POST, endpoint identity,
FP8/standard tier, limits, reasoning/schema support, ceiling rates and the dedicated
non-resetting $1 key allowance are checked. Strict MiMo JSON-schema mode is fixed;
GLM uses the same schema in the prompt and strict local validation. Effective server
reasoning semantics and schema enforcement remain live-readiness questions.

The durable USD 1 ledger reserves worst-case cost before each paid POST, including
readiness, failures and repairs. It uses full uncached tariffs and one token per
UTF-8 byte of the whole JSON body plus 4096 framing tokens, never an average or text
truncation. Prepared baseline input bounds are 15707–22984; combined twelve-baseline
ceiling **$0.441222240** before readiness and dynamically sized repairs. Unknown
costs retain maximum reservations across resume; GET-only generation reconciliation
cannot resend a completion. Changed/missing ledger evidence, price/capability changes
or insufficient budget prevent dispatch. Actual usage/cost exceeding a reservation
halts further admission. The separate non-resetting $1 inference key is a second
safeguard; no automatic top-up or limit increase. An unknown charge is not zero.

The fixed order is g01-Y, g02-X, g02-Y, g04-Y, g05-X, g05-Y, g07-X, g07-Y, g08-X,
g09-X, g09-Y, g10-Y: twelve units, eight groups, four pairs and four singletons.
All saved passage files are byte-identical to their actual historical versions;
both new arms retain identical task messages. No source images, diagnoses, expected
answers, prior findings or g11–g20 reserved content enter the new requests. Prior
ChatGPT assessments are only in the evaluator manifest/report, not human gold.
Criteria are frozen before inference; there is no keyword scoring or automatic winner.

Historical observation: the overnight DeepSeek run completed its development gate
with status **gate_failed**, 12 baselines + two quotation repairs, 7/12 first valid,
9/12 final valid and 6/12 complete claimed coverage. g07-Y, g08-X and g09-X exhausted
output without final content. No reserved calls occurred. The twelve-unit comparison
selection separately has 8/12 first valid, 9/12 final valid, three failed units and
one repaired quotation, thirteen historical calls: 53372 input / 269726 completion
tokens, 4125.8568 seconds summed latency. Reasoning counters are absent, not zero.
The report labels those as inherited reference usage, not new trial calls. Technical
validity is not mathematical correctness and this selected challenge set supports
no whole-book accuracy estimate.

Actual final artifacts (both new arms prepared_offline, **zero calls**):

- Frozen comparison: `runs/critic-glm-mimo-input-20261025T075341Z-b68be4`.
- GLM preview: `runs/critic-glm-input-20261025T075343Z-62c704`.
- GLM run: `runs/critic-glm-trial-20261025T075343Z-4034ea`.
- MiMo preview: `runs/critic-mimo-input-20261025T075343Z-07f232`.
- MiMo run: `runs/critic-mimo-trial-20261025T075343Z-a006b2`.
- Side-by-side HTML: `runs/critic-glm-trial-20261025T075343Z-4034ea/comparison-report/report.html`;
  Markdown and JSON are adjacent.
- Compact ZIP: `results/critic-glm-mimo-inspection-20261025T075344Z-5d3c0b.zip`,
  **2191151 bytes**, 104 unique entries, SHA-256
  `11f1da92f31a2f87909957a0f3a5302596e5fb572206a728bd1ce26f720bd03d`.
- Pointer: `results/critic-glm-mimo-current.json`. Each stopped launch refreshes
  its comparison ZIP and the GLM run's `comparison-latest-bundle.json` pointer.
- Verification/logs: `runs/critic-glm-mimo-audit-20261025T075811Z-84c225`.

An initial zero-call preparation `runs/critic-glm-mimo-input-20261025T075142Z-e1e197`
and its associated arms/ZIP are preserved but superseded after a narrow report
provenance correction (inherited DeepSeek accounting/profile labels). Its code
binding is obsolete. Do not launch it, reset budgets or run both preparations.
No historical completed run or seal was rewritten to accommodate new code.

Offline validation: full suite **319 tests, 302 passed, 15 mock-loopback socket
setup PermissionErrors, two opt-in real compiler skips**, 162.082 seconds, no
assertion failures. After the final report-origin correction, all **18 new pilot
regressions passed** again (24.101 seconds). Checks cover exact frozen inputs and
actual outgoing serialization, retained-data routing without ZDR, explicit paid
boundary/local no-fallback, provider/model mismatch, private fake credentials and
redaction, conservative reservation-before-dispatch, uncertain charges, monetary
ceiling, readiness/recovery limits, pause/resume/no replay, unchanged historical
evidence and report denominators/bundle exclusions. The suite did not execute a
real compiler or any model; mock success does not establish live behavior.

Python compileall, seventeen operator Bash blocks (syntax only), embedded Python
syntax and `git diff --check` passed. Both preview/code seals and **13423 bound
source hashes per arm** verify. All **306 files** and directory membership in the
four historical follow-up/overnight run/preview directories match the before-work
snapshot. The compact ZIP passes CRC, unique membership, raw-data exclusions and
credential-pattern checks. No real key was accessed for these checks. The operator
must run the full normal-terminal suite for sandbox-denied mock sockets; permissions
were not changed.

Gatheral is the subsequent whole-book target, replacing Klebaner for that later
milestone. `inputs/gatheral/source.pdf` is absent; no title/edition, page count,
hash, mapping, contents/appendix/bibliography assessment or registration is invented.
Windows source and intended destination are recorded in the new runbook. Existing
Klebaner sources and all OCR/candidate evidence are preserved. Whole-book work is
not run concurrently and this cloud pilot does not authorize whole-book uploads.

Changed in this task: `AGENTS.md` (authorized narrow policy note), `README.md`,
`START-HERE.md`, `docs/CODEX-HANDOVER.md`, `docs/SPARK-OPERATIONS.md`,
`docs/RECOVERY-CRITIC-TRIAL.md`, this state and `probe/experiment.py`; added
`probe/cloud_critic.py`, `probe/critic_pilot.py`, `tests/test_critic_pilot.py`,
`docs/GLM-MIMO-CRITIC-PILOT.md`, `docs/evidence/glm-mimo-route-20261025.json`.
Unrelated uncommitted work is preserved; all changes remain unstaged. No model/OCR
call, installation, service operation, permission change or Git mutation occurred.

Next operator action: run the normal-terminal tests, then follow
[GLM-MIMO-CRITIC-PILOT.md](GLM-MIMO-CRITIC-PILOT.md) for both-node workload checks,
the documented retained DeepSeek stop only after work finishes, existing regular
GLM launcher, exact alias and fresh text-only readiness, then GLM in tmux. After
GLM stops, privately set up the capped MiMo key, check its pinned route and run
MiMo readiness/trial. The runbook obtains actual readiness paths from each ledger,
defines variables per block and gives pause/resume, cost reconciliation and ZIP
commands. Live routing/billing/schema behavior and substantive usefulness remain
untested; no concrete offline blocker remains.


## 25 October 2026 — configurable USD 10 MiMo budget; completed GLM preserved

The user explicitly raised the **total MiMo pilot ceiling from USD 1 to USD 10**
and will personally set the existing OpenRouter key's **non-resetting USD 10 limit**.
This supersedes only the earlier spending authorization. The twelve passage IDs,
order, input text, schema, exact MiMo/Xiaomi FP8 route, reasoning enabled, 32768-token
limit, 900-second timeout, twelve baseline/four shared repair calls, two extras per
parent, two 2048-token/120-second readiness calls and eight-hour cumulative active
admission limit are unchanged. No training opt-in, account privacy or service change.
The private key at `/home/mdi/.config/pdf-to-latex/openrouter.key` was not read,
inspected, recreated or validated; tests used disposable fake credentials only.

`probe/cloud_critic.py` now derives the ledger ceiling and key-limit check from
sealed `config.budget_usd`. The current default is `10.00`; positive whole-cent
amounts are configurable at preparation. Key limit must exactly match that amount
and have no reset. Mismatched/resetting limits, missing/tampered ledgers and unknown
charges still fail closed or retain reservations. No live environment override or
automatic account-limit update is introduced. All readiness, failed, unknown and
repair costs share the same total. Raising dollars does not grant extra requests.

`probe.critic_pilot reprepare-mimo --comparison ... --budget-usd ...` creates a new
linked MiMo preparation for a future explicitly approved increase without code
edits. It verifies the parent, preserves call/readiness/time and monetary accounting,
copies exact request bytes and records historical implementation hashes. Frozen
inherited state/charge records prevent resetting those allowances on resume. It
refuses active/unsealed parents, billing stops and incompatible task/validator code
changes. The existing completed GLM arm is a historical reference; new reports and
ZIP pointers live under the new MiMo run. Original seals are not patched. The shared
executor checks inherited accounting before dispatch as well as the pilot launcher.

Observed saved GLM result: `runs/critic-glm-trial-20261025T075343Z-4034ea` is
**completed_with_failures**, 12 baseline + four repair calls, **7/12 final valid**,
five failed, 1469.064623 seconds cumulative elapsed. Failures are quotation/location,
schema and finding-preservation checks; they are not replayed here. DeepSeek remains
saved reference only. Neither technical validity nor completion verifies mathematics.
All findings remain UNACCEPTED.

Actual new artifacts (offline, zero MiMo calls/readiness/charge reservations):

- Comparison: `runs/critic-glm-mimo-input-20261025T101917Z-661df0`.
- MiMo preview: `runs/critic-mimo-input-20261025T101919Z-6fda9b`.
- MiMo run: `runs/critic-mimo-trial-20261025T101919Z-ebb7eb`.
- HTML report: `runs/critic-mimo-trial-20261025T101919Z-ebb7eb/comparison-report/report.html`;
  Markdown and JSON are adjacent. It includes preserved GLM and DeepSeek results.
- Compact ZIP: `results/critic-glm-mimo-inspection-20261025T101920Z-54f53b.zip`,
  **2534589 bytes**, 199 unique entries, SHA-256
  `dd34b57f81de56e6af4ee41304dda857d2d8b35d04230a37894bf9c66520236b`.
- Current pointer: `results/critic-glm-mimo-current.json`.
- Checks/logs: `runs/critic-mimo-budget-audit-20261025T102153Z-28296d`.

The USD 1 comparison `runs/critic-glm-mimo-input-20261025T075341Z-b68be4` and its
MiMo run `runs/critic-mimo-trial-20261025T075343Z-a006b2` remain unchanged and
superseded for launch. They had no MiMo calls, readiness attempts or charges.
All **24 input/request files** for the twelve units, selection, ordering and limits
are byte-identical. The sole model-configuration difference is `budget_usd` from
`1.00` to `10.00`; preparation/code/lineage identities change explicitly. All
**13683 source hashes** and current code/preview seals verify. All **566 files and
directory memberships across nine original comparison/run/preview directories**
match the before-work snapshot, including the completed GLM report and both
DeepSeek parent runs/previews. The completed GLM ZIP
`results/critic-glm-mimo-inspection-20261025T085727Z-f7afef.zip` still has SHA-256
`420045441b583827cbea7b5fe9246f9c17d4f339f059dd0dc51d69d9615ed7d7`.
The original selected provider-policy evidence retains its historical USD 1 entry;
this dated authorization supersedes that amount without rewriting public evidence.

Validation: all **25 focused pilot tests passed** (34.810 seconds). Seven added
regressions cover configurable future amounts, exact key limits, monetary admission,
unchanged requests, cumulative paid/readiness/call accounting, resume without replay,
refusal of active/changed parents, attempted resets and completed-report preservation.
Full suite: **326 tests, 309 passed, 15 sandbox mock-loopback socket-creation
PermissionErrors, two opt-in real-compiler skips**, 172.553 seconds. No assertion
failures. No sandbox settings were changed. Python compileall, `git diff --check`,
eight operator Bash blocks and two embedded Python scripts (syntax only) passed.
The ZIP passed CRC, unique membership, raw-data exclusions and secret-pattern checks;
no real key was used for inspection. MiMo authenticated routing, readiness, actual
billing and substantive output quality are still untested. Offline mocks establish
control flow, not provider behavior or accuracy.

Changed for this amendment: `probe/cloud_critic.py`, `probe/critic_pilot.py`,
`probe/experiment.py`, `tests/test_critic_pilot.py`, `AGENTS.md` (narrow authorized
budget note), `README.md`, `docs/CODEX-HANDOVER.md`, `docs/SPARK-OPERATIONS.md`,
`docs/RECOVERY-CRITIC-TRIAL.md`, `docs/GLM-MIMO-CRITIC-PILOT.md`, and this state.
Unrelated working-tree changes are preserved and everything remains unstaged.
No live model call, credential read, installation, permission change, service
operation, account-setting change or Git mutation occurred.

Next operator action: personally set the existing key's non-resetting USD 10 limit,
run the full normal-terminal suite, then use the runbook's new MiMo path in tmux.
The ready/launch chain defines the existing key path, checks route/rates/key limit,
performs one paid synthetic readiness, extracts its actual saved path automatically
and launches only if it passed. Keep GLM and DeepSeek evidence frozen. Readiness
failure is a stop for diagnosis, not permission to reset/repeatedly probe.


## 25 October 2026 — current source snapshot for independent ChatGPT review

Prepared `results/pdf-to-latex-project-snapshot-20261025T120117Z.zip` at 2026-10-25T12:01:17.754008+00:00 for the user's
requested code review. It includes the current working-tree versions of all project
Python modules/tests (including embedded prompts), scripts, Markdown documentation,
selected evidence/provenance, synthetic fixtures, dependency files, configuration
example and project manifests. Relevant untracked and uncommitted files are included.
The archive's `SNAPSHOT/` records the UTC time, current commit, read-only Git status,
tracked diff from HEAD and complete file inventory with project-file hashes.

Credentials/local configuration, Git metadata, environments/caches/model files,
input book/paper PDFs, raw runs/results and downloaded archives are excluded.
The large synthetic scan fixture and existing design PDF are intentionally included.
Checks cover archive membership, CRC, exact file bytes, excluded paths and credential
patterns; the real key is not read. No application source, existing evidence or
running job is changed. The user reports having run the latest tests; this archive
task does not rerun tests or infer an unprovided normal-terminal result. Only this
state entry and the new ignored ZIP are created/updated, with no Git mutations.

Next: upload the ZIP and ask ChatGPT to start with `SNAPSHOT/README.md`, then the
latest PROJECT-STATE entries and the GLM/MiMo runbook. Raw runtime evidence is not
in this source snapshot; use the separate experiment inspection ZIP when needed.

## 25 October 2026 — candidate-only GLM-first critic and selective MiMo preparation

Implemented and prepared the next bounded workflow, offline: local MinerU → Qwen
source-image review → versioned candidate → local GLM text critic → explicitly
selected MiMo second opinions → unresolved, traceable review queues. DeepSeek stays
selectable. Production reviews the current candidate once; the old X/Y comparison
is preserved as an experiment. The user explicitly authorized the narrow AGENTS
routing amendment. Git, service, credential, evidence and retention rules remain.
No live request, OCR, service operation, installation, permission change, key read,
account change or Git mutation occurred. All project changes remain unstaged.

### Recovered completed evidence

Verified the existing GLM run `runs/critic-glm-trial-20261025T075343Z-4034ea`,
MiMo run `runs/critic-mimo-trial-20261025T101919Z-ebb7eb` and the bindings to saved
DeepSeek follow-up `runs/text-critic-followup-trial-20261024T171424Z-8bb3c1` and
overnight `runs/text-critic-overnight-trial-20261024T211031Z-63fbda`. The actual
candidate is `runs/evaluation-candidate-20261024T140145Z-6343d9`, from the completed
Qwen recovery continuation. Its 267 inventory blocks, 27 experimental applications,
three unresolved blocks and `build_failure_unresolved` status are unchanged.
No new candidate compilation or proposal acceptance is claimed.

Saved comparison counts: GLM **7/12 final valid**, 16 calls, 1469.064623 seconds
elapsed (~24.5 minutes); DeepSeek selected reference **9/12**, 13 calls,
4125.856758 seconds summed request time (~68.8 minutes); MiMo **11/12**, 14 passage
calls (two repairs), 2782.185833 seconds elapsed (~46.4 minutes). These are technical
validity/timing, not accuracy. MiMo's fifteen charged requests include one readiness;
the ledger totals **USD 0.1717154424**, zero unresolved reservations. Historical
remaining USD 9.8282845576 is not the current account balance. The original final
comparison ZIP `results/critic-glm-mimo-inspection-20261025T112007Z-ca5ee9.zip`
retains SHA-256 `06b761188543d4e6a8741fe14d7e60d6b7a148fcdcbf570b2fe3e2e8c9f0dd9f`.
Historical trial files and success/failure counts have not been rewritten.

### Implementation and limits

New `critic-anchors-v2` preparations use deterministic whole-block anchors bound to
candidate, block/source hash, exact text and source map. Models cite IDs; Python
retrieves exact quotations and offsets. Unknown/duplicate/stale anchors fail. Old
schemas/prompts/quote validators stay selected for legacy data. The shared executor,
client, readiness, feedback, durable attempt/seal machinery and cloud ledger are
reused. No new model client, scheduler, compiler or RAG application was introduced.

`probe.critic_route` prepares from an explicit candidate inventory/boundary manifest,
with `--profile glm` default and explicit DeepSeek alternative. Uncertain grouping
can be exported as an editable unresolved boundary manifest. No clipping, guessed
sentence splitting or target/context coverage conflation. `critic_context` reuses
source maps, sciwrite command parsing and bibliography inventory for bounded exact
local lookup. Missing/ambiguous references and unsupported OCR remain explicit.
It adds at most eight whole context blocks / 18000 characters and permits at most
one contextual reassessment. Added text and retrieval reasons are recorded.

The new prompt prioritizes mathematical consequence/support and separates proposed
corrections from quoted evidence. Reports split material, context, visual/assembly,
technical and collapsed optional editorial queues. Low/info alone is not editorial.
Display deduplication includes candidate/draft identity and links all contributing
findings/attempts. Superseded/provisional complete rejected responses remain visible
without completion credit; truncated JSON never counts as complete. A technically
valid insufficient-context response remains unresolved, including when the model
also claims it inspected all targets. Empty findings and agreement are not proof.

All follow-ups share **two additional calls per original local passage**, including
context/format recovery and the first MiMo second opinion. Eight additional calls
are sealed globally for this eight-passage calibration, with four cumulative active
admission hours. A linked paid stage retains local consumed calls/time; it is also
bounded to two admission hours and the original time remaining. Exhaustion stays
visible and cannot buy a fresh allowance by escalating. No identical deterministic
failure or unverified lower-effort retry. Output truncation, known reasoning-only
exhaustion and missing token counters remain distinct. Existing compiler setup/access
failure isolation remains intact; this critic does not automatically export edits.

Offline selection from actual local results admits at most four paid passages,
with at most two extra paid recovery calls across the stage and one separately
bounded readiness. All remain subject to inherited allowances. A configurable
apparently-clean sample is frozen before answers (one here, seed 20261025), alongside
material concerns, unresolved context or eligible unusable responses. Visual-only,
cosmetic and local service/infrastructure failures do not become cloud fallback.
No new MiMo selection/result path is invented before those GLM answers exist.

Paid configuration stays `xiaomi/mimo-v2.6-pro`, only `xiaomi/fp8`, no fallback,
reasoning enabled (no claimed graded effort/token cap), existing private key file,
USD 10 cumulative ceiling, documented 30-day retention and no training opt-in.
Prior actual costs/unknown reservations are frozen into linked billing provenance;
current authenticated key remaining is checked before new paid dispatches. The
frozen pilot's twelve/sixteen-call rules are unchanged. New call caps derive from
sealed selected count/limits. Selection refuses a second paid child from the same
ledger; resume retains durable charges rather than creating another allowance.

Cost preview precedes paid readiness. It reports selected input bytes/caps, empirical
mean USD **0.0143096202** per planned pilot passage, a separate configurable **1.5×
planning margin**, and conservative uncached maximum reservations for selected
requests, two possible context/repair calls and readiness. Four passages extrapolate
to USD 0.0572384808 (USD 0.0858577212 with margin), not a hard maximum. The illustrative
200/400/600-passage estimates are about USD 2.86/5.72/8.59 before margin, not a whole-
book dispatch authorization. Pinned rates USD 0.435/M input and 0.87/M output are
checked again through existing authenticated route metadata at operator runtime.

### Actual offline calibration and inspection artifacts

- Manifest: `docs/critic-calibration-passages.json`.
- Preview: `runs/candidate-critic-input-20261025T133737Z-8816e4`.
- Run: `runs/candidate-critic-trial-20261025T133737Z-95be74` — prepared offline,
  **zero requests and zero readiness attempts**.
- Report: that run's `report.html`, `report.md`, `route-summary.json`.
- Initial request inspection ZIP:
  `results/candidate-critic-inspection-20261025T133737Z-564db1.zip` (135609 bytes).
- Expanded compact inspection with separate assessment, two control source images,
  Gatheral metadata, validation and operator instructions:
  `results/candidate-critic-calibration-inspection-20261025T134301Z-26fbab.zip`,
  **540231 bytes**, 40 unique entries, SHA-256
  `aa2dcf71cf616aeb1f3991172c34105b03c3f114a8781b6f0eba33896a068004`.
- Audit/logs: `runs/candidate-critic-preparation-audit-20261025T131920Z-418b86`.
- Actual-path operator pointer: `results/candidate-critic-current.json`.
- Compact inspection pointer: `results/candidate-critic-calibration-inspection-current.json`.

Eight coherent passages cover **75 distinct target blocks** on eight original PDF
pages (126, 146, 166, 170, 176, 205–206, 212). Independent Codex image inspection of
the c01 Itô statement and c02 stochastic-exponential passage found no material
transcription discrepancy in the selected content. These controls are not human
verification or all-page correctness. The six challenge passages retain sign,
initial-condition, limiting/index and missing-context issues for independent review.
The complete PDF 205/b15 paragraph is exactly preserved (510 characters), including
its unresolved transcription; formula-only v105 remains deferred. The external
assessment records the earlier MiMo `{tau >= s}` right-continuity false alarm and
its independent argument, **outside all model inputs**.

Nine context block occurrences (six distinct IDs) are added only to c03/c06/c07.
The local index has 1952 saved blocks and 564 detected labels. Theorem 6.2 remains
ambiguous; some earlier contexts touch unresolved portable OCR, while Theorems
2.35/3.18 are outside the converted span. All gaps are recorded, with no invented
references or external retrieval. Serialized inputs range 10815–23502 bytes, under
196608 bytes. All 75 target texts/hashes match the candidate exactly; all supplied
context matches the local index. Selection diagnoses/control labels are absent
from live bodies. All 336 source bindings and new preparation/code seals verify.

### Gatheral has arrived; whole-book integration is still a separate task

The exact requested `inputs/gatheral/source.pdf` is readable and unencrypted:
**210 pages**, 202 with native text, 73 bookmarks and three PDF page-label rules.
SHA-256 `6010ddf7fe8456398d35dc7d94b16d1f8c853da5e1671d763c7f92083169a988`.
No repeat laptop transfer is needed. Metadata title/author fields are empty; native
title-page text identifies Jim Gatheral, The Volatility Surface: A Practitioner's
Guide. Small provenance is in `docs/source-provenance/gatheral-intake-20261025.json`;
full intake evidence stays under the ignored audit directory. It is not registered
or converted. The proposed first exercise is Chapter 1, physical pages 32–45,
14 pages (PDF labels 1–14), using a new preparation and `ocr_mode=auto` after
explicit processing authorization.

`docs/GATHERAL-PLAN.md` maps all 210 pages, chapter/reference/bibliography spans and
possible <=100-page ownership shards without lifting `batch_inputs.py`'s limit.
The next concrete implementation is an owned-page manifest adapter into the current
recovery-visual/compiler path plus cross-shard complete candidate coverage. Historical
visual selectors remain sample-bound; the older batch route must not substitute for
new recovery/compiler protections. Whole-book orchestration is not ready merely
because the text critic is now reusable.

### Validation and next operator action

Full suite after final implementation: **350 tests, 333 passed, 15 sandbox-denied
mock loopback socket creations, two opt-in real-compiler skips**, 189.965 seconds.
No assertion failures. All 24 new route regressions passed; an earlier focused run
passed 21 before the final paragraph/order, query-exclusion and unused-refresh tests. Coverage includes old
validation, anchor/hash identity, context versus targets, ambiguous/missing context,
stale candidates, shared format/context/paid allowances, resume without replay,
truncation routing, draft-separated display, prior spending/reservations, live-key
remaining checks and local-only no-key/no-cloud behavior. Real cloud, local-model
quality, backend reasoning interpretation and compiler behavior are not established
by these mocks. The operator must run the full suite in the normal terminal.

Python compileall, Bash syntax and `git diff --check` passed. Archive CRC, unique
membership, size/exclusion and credential-pattern checks passed without reading the
real key. Inputs/runs/results remain ignored. All **945 files across seven original
evidence directories** match the before-work manifests, including directory
membership; historical preview/call seals and the completed comparison ZIP verify.

Exact project files changed for this milestone (unrelated prior edits preserved):
`AGENTS.md`, `README.md`, `START-HERE.md`, `docs/CODEX-HANDOVER.md`,
`docs/PROJECT-STATE.md`, `docs/SPARK-OPERATIONS.md`, `docs/RECOVERY-CRITIC-TRIAL.md`,
`docs/GLM-MIMO-CRITIC-PILOT.md`, `docs/SCIWRITE-REUSE.md`, `docs/CANDIDATE-CRITIC.md`,
`docs/GATHERAL-PLAN.md`, `docs/critic-calibration-passages.json`,
`docs/evidence/candidate-critic-calibration-20261025.md`,
`docs/source-provenance/gatheral-intake-20261025.json`, `probe/critic_anchors.py`,
`probe/critic_context.py`, `probe/critic_route.py`, `probe/text_critic.py`,
`probe/sciwrite_subset.py`, `probe/experiment.py`, `probe/recovery.py`,
`probe/recovery_trial.py`, `probe/evaluation_export.py`, `probe/cloud_critic.py`,
`probe/critic_pilot.py`, `scripts/run-candidate-critic.sh`, `tests/test_critic_route.py`.

Next: use `docs/CANDIDATE-CRITIC.md`. Run full terminal tests, inspect workloads,
arrange regular GLM if needed, then `bash scripts/run-candidate-critic.sh run` in
tmux. It checks exact alias and captures actual readiness automatically. Status,
pause/resume and bundle commands need no remembered variables. Only after the new
GLM outcomes, run `select`/`cost`, inspect the plan, `prepare-selected`, then explicit
`mimo-run`. No entire-book or repeated three-model comparison is launched.

Final preparation refresh within this milestone: the neutral MiMo builder removes
free-form local reference queries as well as explicit diagnoses, while preserving
exact candidate/context anchors. An unused cohort can be replaced after a code
change only after historical binding/membership checks and verification of zero
calls, readiness evidence and consumed time. Used cohorts still require an explicit
budget-preserving continuation and are refused here. The final 13:37 preparation
above links the unused previews `runs/candidate-critic-input-20261025T131150Z-da1aab`
and `runs/candidate-critic-input-20261025T133414Z-6e8dfa`, with their untouched runs
`runs/candidate-critic-trial-20261025T131150Z-2434e9` and
`runs/candidate-critic-trial-20261025T133414Z-9bd0ea`. All sixteen GLM input/request
files are byte-identical across these preparations; only necessary code, lineage
and artifact bindings differ. Use the final current pointer, not either old run.
The audit's `final-validation.json` and `final-full-tests.log` contain the final
350-test result; earlier logs remain for traceability. A temporary-code-marker
fixture error in the intermediate new test was corrected before this final run.

## 25 October 2026 — Task 1: whole Gatheral extraction ready for operator launch

**Book: Gatheral, The Volatility Surface. Phase: MinerU extraction of 210 physical
pages. Preparation complete; extraction has NOT started.** The user's whole-book
authorization supersedes the earlier Chapter 1-only extraction proposal. This does
not implement the later whole-book visual/candidate adapters or critic backlog.

No Gatheral registry entry or saved Gatheral conversion was found. Added only source
`gatheral` to `sources.json`, using the already recorded intake SHA-256
`6010ddf7fe8456398d35dc7d94b16d1f8c853da5e1671d763c7f92083169a988`,
210 pages and the identity original-page map 1–210. The PDF remains at
`inputs/gatheral/source.pdf`, unchanged. The registry references the existing
`docs/source-provenance/gatheral-intake-20261025.json`; no new preparation PDF or
intake manifest is needed for this whole-source selection. `ocr_mode=auto` retains
the native-text policy. Front matter, all chapter/appendix content, bibliography
and index are included. No repeat PDF readability audit or checksum was performed.
The existing converter performs its normal source verification on operator launch.

`scripts/run-gatheral-extraction.py run` is a small wrapper around the existing
CLI parser/converter under its existing project writer lock. It discovers and
resumes the single saved Gatheral Basic run, refuses ambiguous/mixed scopes, logs
terminal output and exit status to `runs/gatheral-operator/`, and requires no pasted
run paths. `status` is read-only and discovers the actual result directory, owned
coverage and current worker log. Ctrl-C in the extraction tmux pane stops the owned
worker and retains interrupted evidence; the same `run` command resumes completed
windows without replay. No application/converter execution code was changed.

Settings match the established Basic conversion: installed MinerU 4.0.12 in
`.venv-mineru`, local `model-cache`, CPU/ONNX, `--ocr-isolation none`, 8 GiB available
memory minimum, 3600 seconds per window, eight owned pages and one adjacent context
page per side. Validated 27 windows and exactly 210 distinct owned pages, 262 total
input-page occurrences; first owns 1–8/input 1–9, last owns 209–210/input 208–210.
No runtime/model-cache fingerprint exercise was run during preparation; normal
launch will perform it before printing the newly created conversion directory.

Validation: six new mocked launcher regressions and all 18 existing CLI integration
checks passed (24 total). Covers automatic resume, preserved evidence, lock refusal,
scope ambiguity, read-only owned-page progress, interruption/exit/log behavior and
existing source/output/window integrity. Python syntax, registry/loader routing
against existing intake metadata (checksum mocked to avoid rereading the book),
window mapping and `git diff --check` passed. All previous source entries preserved.
No live OCR, model requests, service operations, installs, Git mutations, PDF/cache
changes or broad audits were performed. Live extraction/output fidelity is untested.

Execution directory is **`/home/mdi/projects/pdf-to-latex`**. Resume fingerprints
selected source metadata/hash, converter package/model hashes, **every top-level
`probe/*.py` file**, worker code and conversion settings; it verifies completed
output manifests and source-window/page-map hashes before reuse. Keep this checkout,
source, settings, environments and cache fixed once launched. Later critic fixes
must use an ordinary separate DEVELOPMENT COPY including current uncommitted code;
no writes into the extraction project, environments or model cache. No new
execution-snapshot framework or development copy was created.

Changed for this task: `sources.json`, `scripts/run-gatheral-extraction.py`,
`tests/test_gatheral_launch.py`, `docs/GATHERAL-EXTRACTION.md`,
`docs/GATHERAL-PLAN.md`, `docs/PROJECT-STATE.md`. Everything remains unstaged;
unrelated edits, AGENTS.md and completed evidence are preserved. Next: follow
`docs/GATHERAL-EXTRACTION.md` to finish current jobs, stop only the identified idle
owned heavy deployment, check memory, then launch `run` inside `gatheral-extraction`
tmux. The directory/ZIP names will be actual converter outputs, not preinvented paths.


## 25 October 2026 — Task 2 critic backlog and owned-page review adapter

Implemented/tested in `/tmp/pdf-to-latex-critic-development-20261025`, independently
copied from current source including unstaged/untracked work. Original source hashes
were recorded before editing; source files are ordinary copies, never hardlinks or
symlinks. The absolute existing controller interpreter was used with imports and
all test output under the development copy. No .git/environment/cache/credential/book
copy, OCR, model call, installation, permission change or service operation occurred.
The extraction checkout remained untouched throughout development and tests.

Focused evidence: GLM `runs/candidate-critic-trial-20261025T133737Z-95be74`, selected
MiMo `runs/candidate-critic-trial-20261025T213705Z-c506ee`, existing inspection
`results/candidate-critic-inspection-20261025T221621Z-629945.zip`. Preview/call seals
verified read-only. Four initial target/candidate/draft bindings match. MiMo has five
passage calls, 1380.977 seconds, stage USD 0.0680012862 including readiness, cumulative
USD 0.2397167286, no unsettled charges. Historical outcomes were not rewritten.

Implemented observed-statement context spans (including associated displays and
cross-page continuation), verbose reference normalization, deduplication, provenance,
and explicit partial/unavailable/budget outcomes. Saved c03 now resolves theorem
b2–b5 rather than a folio/heading/display. Independent material/context/visual/technical
reporting retains sign/limit concerns and separates positive/cosmetic observations.
Overlap of exact bound spans plus claim topics now exposes c03/c05 potential agreement;
this is a review aid, not proof. Future critic-anchors-v3 uses Python-owned request
bindings and exact-invalid-field patches, retaining unexpected commentary separately
and preserving substantive findings/uncertainty/references. Old v1/v2 validation and
raw evidence remain intact. Shared follow-up/time/spending limits are unchanged.

Added `probe.book_review` and `scripts/run-gatheral-review.sh`: explicit opt-in adapter
from completed ordinary conversion to the existing Qwen recovery/isolated compiler
executor. Every registered owned block is targeted once in full; each page, including
blank pages, gets an independent omission check. Context is not target coverage.
Initial physical pages 32–33 gate; expansion resumes the same run, preserving calls,
failures and budgets. Qualified compiler image remains fixed. Candidate assembly
accounts for every block in order, retains full raw unresolved OCR/source images,
adds coverage/bibliography/insertion inventories, and requires exact-version
whole-block dispositions. Uncertain/conflicting/incomplete replacements and missing
content insertions remain deferred. No proposal is accepted automatically.
The older 100-page batch limit and default conversion behavior are unchanged.

Validation: full suite attempted 378 tests, 354 passed, 16 errors, 8 skipped in
212.315s. Fifteen errors were denied loopback sockets; the one other error was an
existing test assuming a checkout under HOME. Its location-independent revision
passed all seven focused isolation tests. Thus 355 cases passed across the full
run and focused correction; 15 remain sandbox-blocked and 8 intentionally skipped
(six optional old evidence checks absent in this copy, two real compiler tests).
All new backlog/adapter and modified route regressions passed. Python/bash syntax
and changed-line whitespace checks passed. No real compilation or live model
behavior was tested. Run the full suite in the normal terminal; do not relax sandbox
permissions. Logs and exact change manifest are in the development patch bundle.

At 23:36 UTC the actual Gatheral run
`runs/convert-basic-20261025T230247Z-e6bb30` recorded
`conversion_completed_unreviewed`, 27 completed windows, 210 owned pages, and no
visible owned converter/launcher. This permits guarded integration only after
rechecking all destination baselines/new-file absence and the existing writer lock.
The bundle's `development/FINAL-HANDOVER.json` records the actual integration result.
No incomplete conversion was read as final review evidence; no Gatheral preview
or live readiness was generated. Completed extraction is structured OCR/assets/draft
exports, not a final reviewed book. Historical conversion fingerprints remain intact.

Remaining limitations: structural context boundaries are heuristic and missing
labels/hypotheses remain unavailable; text agreement is not proof; unsupported
portable fragments/images/tables, insertions and semantic passage boundaries need
review. Finite six-hour/80-recovery defaults may leave book coverage pending; no
budget resets or promise of whole-book completion. New code intentionally invalidates
old live preparation bindings; never reseal old attempts. GLM stays the default
text critic, Qwen the image reviewer, MiMo optional/selected with current cumulative
cost checks. Follow `docs/GATHERAL-REVIEW.md` for the first small gate and same-run
expansion; `docs/TASK2-DEVELOPMENT.md` describes preservation/copy-back.

Integration completed at 2026-10-25T23:42:17.326586+00:00 after a fresh completion/worker-exit check and matching destination hashes/new-file absence, under the existing project writer lock. All 27 changed files were copied back; no original baseline or completed evidence changed during development. The tested development copy and patch bundle remain under `/tmp/pdf-to-latex-critic-development-20261025`; preserve the bundle outside temporary storage. No Gatheral review preparation or inference has been run.

## 26 October 2026 — Separate chapter-context GLM experiment prepared offline

User-authorized experiment: saved MinerU → regular local GLM chapter drafts → fresh
GLM text reviews. This is separate from the Task 2 Qwen visual route; integrated
Task 2 work and original extraction/review evidence are preserved. No service,
installation, model/paid call, OCR, permission or Git metadata operation occurred.
**Prepared, not running: zero calls and no first-dispatch timestamp.**

Actual input: `runs/chapter-glm-input-20261026T031434Z-2392d8`.
Actual trial: `runs/chapter-glm-trial-20261026T032225Z-ac8537`.
Report: that trial's `report.html`; placeholder assembled book: `book/master.tex`.
Offline ZIP: `results/chapter-glm-inspection-20261026T032341Z.zip`, 12,903,486 bytes,
SHA-256 `1ac87c7b7d276b1a1f0b751693ae8d033abd227d3d81456ba280897a12c5f41c`.
The earlier `chapter-glm-input-20261026T025756Z-142f1d` is retained development
preparation, superseded before any dispatch by the final proof-boundary guard.
The pointer `results/chapter-glm-current.json` selects the actual final trial.

Investigated missing `blocks`: Gatheral's actual Middle 2.0 owned pages 3, 9, 15,
21, 23, 31 and 199 contain `page_idx` without a blocks field. The installed schema
uses an empty-list default. Added an explicit verified-blank opt-in to the existing
saved-page reader; other missing/null block data and nonempty verified blanks still
fail. No saved JSON was repaired. Chapter ownership reuses `book_review.owned_scope`.
The exact explicit Gatheral chapter boundaries account for 210 pages once; Klebaner
Chapter 4 accounts for selected 1–31/original 106–136, excluding separator 137 and
Chapter 5. The new preparation was exercised against both actual saved conversions.

Every prepared native block was compared back to the owned saved page: Gatheral
2,184 blocks, Klebaner 514; 241 selected pages total. All 1,850 native mathematical
strings are present in complete source extracts. Native prose/footnotes/captions/
references remain in source TeX and exact structured sidecars; no portable-export
filter discards grammar. Source counts retain 43 charts, 12 main-text images,
12 tables, two front images and all 76 bibliography ref_text blocks. Tables keep
source crops/captions; front matter/index have labelled page-image fallback, with
original printed index references. Blank pages consume no calls. The installed
native renderer emitted one HTML-table fallback warning; its full native table and
source image remain available. No claim of editable-table fidelity or OCR accuracy.
All 721 consumed source/evidence files passed their recorded hashes after preparation.
Validation details: `runs/chapter-glm-development-20261026T024458Z/actual-input-validation.json`.

Added a distinct ordinary-TeX chapter protocol and purpose in the safe local
transport, preserving historical timeout/token/JSON contracts. Uses exact
`glm53-regular` at `http://192.168.1.100:8888/v1`; serial requests, 32,768 output tokens,
2,700-second maximum request timeout, sampling/thinking overrides omitted. Installed
regular launch config supports the 32,768 default; live effective context is read
from root `/health`. Controller `tokenizers` is absent, but not required: complete
UTF-8 request bytes + 4,096 template margin + output ceiling are conservatively
admitted against actual context, with existing 2 MiB transport cap. This may reject
an input an exact tokenizer would admit; nothing is clipped. Largest extracts:
118,128 characters Klebaner, 78,168 Gatheral Chapter 11. Initial combined estimates
178,009/128,914 tokens respectively; review requests are measured with actual output.
This is a new MinerU-input experiment, not an exact Open WebUI replay.

Ordering: Klebaner draft/review, all eleven Gatheral drafts, all Gatheral reviews,
then short postscript/bibliography work. Output exhaustion/missing tails never pass.
Where supported by native major headings, two complete section outputs retain full
chapter context; no arbitrary text cuts. Unclosed proofs block lesser headings;
Gatheral Chapter 7 has no admitted fallback and will remain unresolved if exhausted.
Section assembly, exact target markers and inventories are structural evidence,
not semantic fidelity. Text reviews remain separate, with local proposals unaccepted;
no semantic or compiler suggestion overwrites raw draft evidence.

Durable serial controller reserves calls before dispatch, keeps raw final/reasoning
responses, skips completed work, and records uncertain interrupted completions
without automatic replay. Each task has at most two additional shared calls, global
80 calls including readiness/splits/failures, eight hours wall time from first
inference dispatch including idle time. Resume preserves all limits and checks code,
input, request, section and completed-output bindings. No expiry reset/new cohort.
Identity/integrity failures stop; repeated connection failures pause; isolated
content/format/timeouts/capacity gaps do not erase other chapters. Writer lock and
head/peer workload checks prevent known conflicting project/deployment work; server
snapshots cannot exclude an external client arriving afterward. Keep the phase
exclusive and controller source fixed while running.

Extended the isolated compiler narrowly with explicit bounded relative asset/include
staging, rejecting symlinks, traversal, collisions and unsupported paths. Original
read-only /source, /work output, paranoid policies, no shell escape/network, non-root
and resource limits remain. Qualified image ID is unchanged. Infrastructure failures
are distinct from bad TeX. No real compilation was attempted here. Compiler checks
in mocks do not establish compilation. The placeholder master is not a finished book.

Validation: final full suite **409 tests in 200.085s: 391 passed, 15 errors, 3 skipped**.
All 15 errors are denied socket creation in existing mock HTTP tests; all three skips
are opt-in real compiler checks. No application failure remains in that final run.
The new 31-test chapter group covers actual protocol/serialization, selection,
long-context admission, native formulas, source assets, truncation, split assembly,
readiness, identity, shared limits, isolated staging and a complete mocked controller
plus same-run resume. Initial full run exposed a proof-test fixture needing an end
marker and an old regression trying to requalify the now-expanded registry against
frozen pre-Gatheral evidence. The former was corrected; the latter now verifies and
reads only the sealed historical v105 input/call for its paragraph-preservation
assertion. Production candidate/parent/source guards were not relaxed. Both initial
and final logs are retained in the development directory. Bash syntax, Python AST,
changed-line whitespace, `git diff --check` and inspection ZIP integrity passed.
The ZIP has 235 files and one shared set of 104 needed images/assets, without old
archives, credentials, environments, model files or input PDFs.

Session access checks were performed once: tmux socket denied, Docker socket denied,
GLM endpoint connection failed immediately. They were not retried or bypassed, and
do not establish that the operator's GLM service is stopped. The new wrapper was
not launched. Its normal-terminal `run` checks the endpoint/workloads, starts tmux,
runs the full suite before dispatch, verifies actual preparation, captures one fresh
text-only readiness and runs the entire bounded schedule. It reports clear failures,
never switches models or changes services, and records logs/exit status. `status`,
`pause`, `resume` and `bundle` discover the same saved paths without shell variables.

Changed in this task: `.gitignore`, `README.md`, `docs/CHAPTER-GLM.md`,
`docs/PROJECT-STATE.md`, `docs/evidence/chapter-glm-preparation-20261026.md`,
`probe/chapter_inputs.py`, `probe/chapter_protocol.py`, `probe/chapter_glm.py`,
`probe/local_model.py`, `probe/saved_pages.py`, `probe/tex_compile.py`,
`scripts/render-chapter-native.py`, `scripts/run-chapter-glm.sh`,
`tests/test_chapter_glm.py`, `tests/test_reviewed_candidate.py`.
The writer-lock runtime file is now ignored; AGENTS.md and all unrelated edits were
left alone. Everything remains unstaged. Next operator action, explained fully in
`docs/CHAPTER-GLM.md`:
`cd /home/mdi/projects/pdf-to-latex && bash scripts/run-chapter-glm.sh run`.

## 26 October 2026 — Simple whole-chapter route prepared; original trial preserved

The operator ran and paused `runs/chapter-glm-trial-20261026T032225Z-ac8537`.
At this task's inspection it was stopped with nine saved calls. Earlier read-only
diagnosis confirmed two avoidable protocol failures: native running headers labelled
paragraph_title made empty output markers fail; valid native `includegraphics` paths
wrapped in `detokenize` failed the old plain-path matcher. Klebaner's first whole
response also genuinely truncated, and Gatheral 1's first whole response spent all
32,768 completion tokens on reasoning without final content. These historical
outcomes remain as recorded; no earlier response, task status or seal was repaired.

User changed the experiment design to simple whole-chapter conversion. Implemented
`scripts/simple_chapter_glm.py` and `scripts/run-simple-chapter-glm.sh`, outside
`probe/` to preserve the old trial's all-controller-module code fingerprint. Reused
the existing safe local transport/invocation, durable call ledger, readiness,
resource/workload checks, writer lock, wall/call limits and isolated compiler.
Existing workflows and their validation contracts are unchanged. No new framework,
OCR, model calls, service operation, installation, permission or Git mutation.

Final actual preparation: `runs/simple-chapter-glm-trial-20261026T101639Z-ac3566`.
Report: that directory's `report.html`; check record: `offline-validation.json`.
ZIP: `results/simple-chapter-glm-inspection-20261026T101639Z-ac3566-1793009800770921313.zip`.
The separate pointer is `results/simple-chapter-glm-current.json`. **Prepared, not
running: zero calls, first_dispatch=null.** The original marker-based pointer is
untouched. The earlier simple preparation `runs/simple-chapter-glm-trial-20261026T101116Z-619b13`
is retained as zero-call development evidence; the final code adds an empty-fence
answer guard and clears stale stop messages on resume. No seal was edited; sources
and conversion requests are byte-identical between these two offline preparations.

Input derives from the already validated native preparation
`runs/chapter-glm-input-20261026T031434Z-2392d8`, not past model drafts or diagnoses.
It reuses owned pages and explicit boundaries, excluding overlap/context duplicates.
The twelve selected chapters comprise 31 Klebaner pages (original 106–136) and 161
Gatheral main-text pages (32–192), in chapter order. The prior native preparation
continues to account for all 210 Gatheral pages and retains front/back matter.
This small alternative does not newly convert those other parts or claim an assembled
reviewed book. No source PDF or extraction was modified or rerendered.

All included prose/native mathematical strings, captions and local asset references
remain in complete chapter extracts. Provenance, exact block spans, original page
mapping, native data, exclusions and hashes live in sidecars. Native page furniture
is omitted from model input. Five additional Klebaner running titles are identified
by a top-margin title sharing a folio baseline and matching another chapter heading;
the corresponding real section titles remain. No blanket top-of-page deletion or
known-answer correction. Klebaner input is 96,935 characters/737 native math strings;
Gatheral 1 is 34,064 characters/129 strings. Across the twelve chapters, 1,838 native
math strings remain; complete native sidecars are retained even for excluded furniture.

Conversion uses a short user prompt requesting a complete LaTeX file, plus the whole
extraction and necessary relative-asset instruction. No JSON, source-ID reproduction,
assignment lists, sentinels, shared document template or block acceptance rules.
Sampling/thinking overrides stay omitted, with 32,768 output tokens and up to 2,700s
per request. Effective Open WebUI settings are unknown. The existing conservative
byte/context admission needs no tokenizer dependency and clips nothing; combined
estimates are 139,607 tokens for Klebaner and 73,488 for Gatheral 1. Actual server
usage will be recorded when present, including failures and reasoning tokens.

One conversion each of Klebaner 4 and Gatheral 1 comes first. Only two normal,
nonempty responses permit automatic Gatheral 2–11 conversion and then independent
reviews of all available chapter files. Output exhaustion or an empty initial answer
stops expansion after both initial attempts. No identical retry, section splitting,
effort reduction, token increase or semantic application. Each conversion/review has
zero automatic additional calls; the new experiment retains an explicit eight-hour
wall budget from first dispatch and 80 total calls including readiness. Normal plan:
24 chapter calls plus readiness. Resume keeps the same deadline and consumed calls,
skips saved work, and never replays uncertain/unfinalized completions. This is an
explicitly authorized new design, not a budget reset for the paused historical trial.

Normal response completion, document observations, compilation and fidelity are
separate. Every final response remains in raw call evidence. A sole enclosing fence
can be stripped transparently in a derivative file, but an empty fenced answer is
not gate success. Missing document delimiters/assets produce warnings independently
of generation status; valid detokenized paths are recognised in those observations.
The existing qualified compiler receives the exact generated document and allowed
assets, preserving its isolation/resource controls. Original generated files survive
syntax, asset or compiler-configuration failures. No repair requests are scheduled.
Fresh reviews contain the full extraction and exact generated TeX, with findings
stored separately and unaccepted. No content-fidelity or mathematical accuracy claim.

Validation: 19 focused offline regressions pass, covering native/paragraph retention,
furniture evidence, exact boundary ownership, simple long inputs, lack of old output
contract, fresh reviewer inputs, detokenized assets, compiler-failure preservation,
empty answers, one-call tasks, gate expansion, pause/deadline, no replay after
interruption, sealed input/output tampering and actual shared request serialization/
identity checks. Full suite run once: 427 tests in 199.721s, 409 passed, 15 errors
all from sandbox-denied mock loopback sockets, three opt-in real compiler skips.
The final empty-fence guard was subsequently checked with the full 19-test focused
group; the operator launcher runs the full final suite before inference. No sandbox
permissions were altered. Full log is copied into the final run with its provenance.
Python AST/bash syntax, `git diff --check`, new-file whitespace and ZIP integrity
checks passed. No real compilation or live generation tested. Original trial files
match the before-task byte manifest, and its original code/evidence verification
still succeeds after this implementation.

Changed in this task only: `scripts/simple_chapter_glm.py`,
`scripts/run-simple-chapter-glm.sh`, `tests/test_simple_chapter_glm.py`,
`docs/SIMPLE-CHAPTER-GLM.md`, `docs/CHAPTER-GLM.md` (historical-status pointer),
`README.md`, and `docs/PROJECT-STATE.md`. All remain unstaged; unrelated work and
AGENTS.md were preserved. The new runbook explains automatic readiness, tmux,
status/pause/resume/bundle, filenames, limits and remaining unverified behavior.
Next operator command (not executed by Codex):
`cd /home/mdi/projects/pdf-to-latex && bash scripts/run-simple-chapter-glm.sh run`.

## 26 October 2026 — Linked 131,072-token simple chapter preparation

Operator clarified that the successful Open WebUI conversion requested
max_tokens=131072. This is the only newly established Open WebUI setting; effective
sampling/thinking/template equivalence is not claimed. The simple short conversion
prompt, complete chapter content, asset paths, lack of block protocol and separate
compilation/review behavior are preserved.

Inspected stopped parent `runs/simple-chapter-glm-trial-20261026T101639Z-ac3566`:
one passed readiness and two failed conversions. Klebaner call-002: finish_reason
length, prompt 38,036, completion 32,768, reasoning 32,768, zero final characters,
542.521s. Gatheral 1 call-003: length, prompt 11,284, completion/reasoning both
32,768, zero final characters, 629.307s. Raw TensorFold timings separately report
prefill/decode 22.8968/519.5246s and 7.1356/622.126s. Both exhausted the requested
allowance entirely in reasoning; no complete final chapter existed in these calls.

Read-only deployment inspection: installed
`/home/mdi/local-llm/glm53-flash-tensorfold/scripts/config.sh:132–135` explicitly
defines MAX_TOKENS as an omitted-field default and says the request's own value
wins; start.sh passes it as --max-tokens. Installed patches show explicit GLM
prompt-plus-output context checking, default clipping to remaining context and
forwarding max_tokens to scheduler generation. README documents combined reasoning
and answer allowance. No service change is indicated by this installed recipe.
Docker API inspection of the running image was denied by the sandbox. No permission
change or repeated Docker attempt occurred. Running-container implementation and a
live 131,072 response have not been verified; HTTP success is not treated as proof
that the ceiling is honoured. The local source hashes and qualification limitation
are recorded in `allowance-validation.json` and
`docs/evidence/simple-chapter-131072-20261026.md`.

Narrow client change: only purpose=chapter now admits up to 131,072 output tokens.
Text critic remains capped at 32,768; page review at 16,384; capability probes at
4,096. Timeout remains 2,700s for chapters. Simple conversions now explicitly use
131,072, reviews 32,768, readiness 2,048. No sampling/effort field, split, retry,
new output-validation layer, compiler change or service operation was added.

New linked run: `runs/simple-chapter-glm-trial-20261026T111637Z-634ede`.
Report: its `report.html`; requests/sidecars: `inputs/`; recorded differences:
`allowance-change.json`; offline checks: `allowance-validation.json`.
Inspection ZIP:
`results/simple-chapter-glm-inspection-20261026T111637Z-634ede-1793013459734206189.zip`.
The existing simple-run pointer selects it. **Prepared offline, not running: zero
new calls; three inherited calls.** Parent files, inputs, responses and seals match
their pre-task byte manifest. Historical validation checks recorded evidence under
its original binding; new execution still requires exact current code/input hashes.
No old seal is patched to pretend historical calls ran under the changed code.

All twelve linked conversion request bodies differ only in max_tokens; complete
source.tex/native.json/provenance.json/assets.json and shared assets are unchanged.
The original first-dispatch timestamp and three consumed calls are retained, so the
eight-hour deadline remains **26 October 2026 at 18:33:44 UTC** and the global ceiling
remains 80 calls. Inherited calls carry their original run/parent IDs and are not
completion credit for the newly authorized changed-allowance comparison. Run once
each: fresh readiness, Klebaner 4 conversion, Gatheral 1 conversion; only two normal
nonempty final responses unlock remaining Gatheral drafts and then separate reviews.
There are no automatic retries or splits. New run/resume understands inherited
versus newly dispatched calls without resetting the original deadline.

Saved server health reports context_length=1,048,576. All complete conversion inputs
plus 131,072 output fit that recorded window. Conservative JSON-byte/template/output
admission estimates: Klebaner 237,912; Gatheral 1 171,793. Saved actual prompt-token
counts plus the new output budget are 169,108 and 142,356; future live request
admission rechecks actual health and never clips inputs. Reviews retain a separate
32,768 ceiling and are checked against their eventual complete generated text.

Time limitation: at observed end-to-end rates, 131,072 tokens extrapolate to about
36.2 and 42.0 minutes (fixed prefill plus scaled decode: 35.0/41.6). These are estimates,
not proof that 45 minutes suffices as context grows. Full-ceiling output needs about
48.6 tokens/s before prefill. All twelve conversions at that utilization could take
7.2–8.4 hours before reviews, more than the remaining cumulative allowance. The
controller retains the requested limits and explicit gaps; no whole-job completion
promise, silent timeout increase or budget reset.

Per-call summary records now include requested allowance, finish reason, prompt/
completion/reasoning tokens, final/reasoning character counts, elapsed and available
server timings. Completion minus reasoning is labelled derived non-reasoning tokens,
not an exact final-answer token count; missing counters remain unknown. A length
stop below the requested ceiling is visible for investigation without retry. Normal
HTTP success does not certify effective allowance, content completeness or accuracy.

Validation: 24 focused tests passed. Final full suite, run once: 433 tests in 198.083s,
415 passed, 15 PermissionError errors all from sandbox-denied mock loopback sockets,
three opt-in real compiler skips. Checks cover actual outgoing 131,072 serialization,
legacy caps/timeouts, 32,768 reviews, complete-context admission, unchanged request
content, inherited calls/deadline, immutable parent evidence and usage interpretation.
Python/bash syntax, whitespace, artifact comparisons and ZIP checks passed. No live
inference, real compiler, OCR, installation, service or Git metadata mutation.

Changed only: `probe/local_model.py`, `scripts/simple_chapter_glm.py`,
`tests/test_simple_chapter_glm.py`, `README.md`, `docs/SIMPLE-CHAPTER-GLM.md`,
`docs/evidence/simple-chapter-131072-20261026.md`, `docs/PROJECT-STATE.md`.
Existing launcher command remains:
`cd /home/mdi/projects/pdf-to-latex && bash scripts/run-simple-chapter-glm.sh run`.
It checks workloads/exact alias, launches tmux, runs the full normal-terminal tests,
captures readiness and dispatches serially; no pasted paths or service changes.
The `status`, `pause`, `resume`, `bundle` actions continue to discover the linked run.
Everything remains unstaged; AGENTS.md and unrelated work were preserved.

## 2026-10-26 — Simple chapter envelope recovery; Gatheral continuation prepared

Inspected and verified the actual stopped run
`runs/simple-chapter-glm-trial-20261026T111637Z-634ede`. Gatheral call-006 finished
with `stop`, 102,571 completion tokens, 91,667 reasoning tokens, 34,592 final-answer
characters and 1,662.05s. The previous envelope handling kept its introduction,
one fenced complete LaTeX document and trailing conversion notes together in
`generated.tex`; the compiler never received just the document. Klebaner call-005
really ended at `length`: 131,072 completion tokens, 113,090 reasoning tokens,
45,043 final-answer characters and 1,935.10s. Its partial answer stays incomplete.
Derived non-reasoning token counts are not independently reported final-text counts.

Narrow correction: recognize a single complete fenced document surrounded by
prose; keep an exact contiguous TeX slice, full raw answer, introduction, conversion
notes, offsets and hashes separately. Refuse incomplete/multiple/ambiguous envelope
extraction without discarding the response or treating it as a usable draft. No
new block protocol, prompt change, splitting or automatic model retry. Image
observations now handle optional arguments followed by comments/newlines and
filename arguments, including existing detokenize paths. Compiler path allowlists,
traversal/symlink rejection and isolation remain intact. Gatheral continuation
depends on Gatheral 1's available response; Klebaner failure no longer blocks it.

Actual new linked preparation, **not running**:
`runs/simple-chapter-glm-trial-20261026T151403Z-61cbdb`.
It copies every source, native record, provenance file, image and prepared request
byte-for-byte; all six consumed calls retain their original origins/code provenance.
First dispatch and the 80-call ceiling are unchanged. The original eight-hour
deadline remains **26 October 2026 18:33:44 UTC**, including idle time. It had not
expired at preparation; no extension/reset was made. Ten Gatheral conversions
(2–11), then eleven Gatheral reviews (1–11), are pending. The first new model call
will be captured readiness, then Gatheral 2; neither earlier conversion is replayed.
Klebaner review is explicitly unavailable. Conversion max remains 131,072, review
max 32,768, request timeout 2,700s reduced to remaining time, sampling/reasoning
overrides omitted. About 3h20m remained at preparation, so finishing every task is
not promised; expiry leaves visible gaps and requires explicit further authorization.

Recovered file:
`runs/simple-chapter-glm-trial-20261026T151403Z-61cbdb/recovery/call-006/generated.tex`.
SHA-256 `f3fe4ca60d9c25340a8f1ef093f60dae5e1803dc783bedac07ad6cb27e87f4e9`.
Raw answer SHA-256
`3772ec7c8a7a6bfbcaf5ab2a6ccdab05dc79e95b3d795c3e1cf08e2fd09b2e6a`.
Exact-slice validation confirms 12 equation tags and three supplied figure paths;
the three missing-asset observations disappear. These are mechanical observations,
not a source-image fidelity audit. GLM's notes disclose mathematical modifications
and reconstructed footnotes; all remain unverified and UNACCEPTED. No content was
manually corrected and no second model assessment ran.

Compilation remains **unavailable here**, not a TeX failure. The user reports that
ChatGPT's exact extraction built in two pdflatex passes to 11 pages. Codex's one
isolated attempt was denied access to the Docker API before TeX started. The Docker
client returned 1 rather than 125, exposing a concrete classifier gap now covered
by regression: explicit Docker permission/daemon denial is `unavailable`, never a
model-output syntax diagnosis. The intermediate offline preparation
`runs/simple-chapter-glm-trial-20261026T151139Z-64ef50` and its failed check remain
unchanged. The final preparation preserves that check under
`inherited/sandbox-compiler-check`, with a separate
`compiler-classification-review.json`; its original result classification was not
rewritten. No second Docker attempt or permission change was made in the sandbox.

The normal-terminal launch will attempt the recovered file's two-pass compilation
in a new output directory before readiness, preserving the blocked attempt. The
adapter supports one or two passes (legacy default one), sharing its existing
90-second compiler timeout and disposable build directory, retaining per-pass
logs/auxiliary evidence. The qualified image, read-only source mount, network
isolation, non-root execution, no-shell-escape and resource limits are unchanged.
Compiler failure does not discard generation or schedule a model repair.

Report: `runs/simple-chapter-glm-trial-20261026T151403Z-61cbdb/report.html`.
Inspection ZIP:
`results/simple-chapter-glm-inspection-20261026T151403Z-61cbdb-1793027667837803110.zip`.
The recovery folder contains `answer.raw.txt`, `introductory-prose.txt`,
`conversion-notes.md`, `extraction.json`, `provenance.json`; run-level
`recovery-validation.json` records input identity, accounting and recovery checks.

Validation: final focused suite **49 tests, 46 passed, three opt-in real compiler
skips**, including the actual saved call-006 regression. Related chapter/recovery
suite **84 tests, 81 passed, three skips**; affected compiler tests were rechecked
after the Docker classification correction. Coverage includes ambiguous envelopes,
exact notes/content separation, commented image syntax, unsafe asset rejection,
no replay/clock reset, inherited success and failed Klebaner preservation, stale
evidence, expiry, shared call ceiling, auxiliary reuse and per-pass failures. No
mock socket restrictions affected these checks. Python/bash syntax, whitespace,
parent file/manifest comparisons and ZIP integrity checks passed. Original parent
evidence remains byte-for-byte unchanged. Real compilation and live continuation
remain untested; the wrapper runs the full suite in the operator's terminal first.

Files changed for this task: `scripts/simple_chapter_glm.py`, `probe/tex_compile.py`,
`tests/test_simple_chapter_glm.py`, `docs/SIMPLE-CHAPTER-GLM.md`,
`docs/PROJECT-STATE.md`, `README.md`. No inference, OCR, service operation, installation, Git
metadata mutation or AGENTS.md edit. Unrelated working-tree changes are preserved;
everything remains unstaged. Next operator command:
`cd /home/mdi/projects/pdf-to-latex && bash scripts/run-simple-chapter-glm.sh run`.
It discovers the prepared path, checks workloads and the exact regular GLM alias,
starts persistent tmux, runs tests, checks the saved recovery with the isolated
compiler, captures readiness and starts Gatheral 2. Status/pause/resume/bundle use
the same wrapper; resume retains the original deadline and never retries failed
chapters automatically. An expired deadline fails clearly instead of resetting it.

## 2026-10-26 — Simple chapter timing, immediate critic, durable reasoning and compiler preparation

Implemented the user's controlling update in a **new linked preparation**, not by
changing the expired run's seals:
`runs/simple-chapter-glm-trial-20261026T192951Z-3efb02`.
It is **prepared offline and not running**. Parent
`runs/simple-chapter-glm-trial-20261026T151403Z-61cbdb` has exited with the historical
eight-hour expiry. Its full recorded file manifest remains byte-for-byte unchanged.
No service, model, system Python, permission or Git metadata operation was made.

The simple route now has no overall elapsed-time cutoff and no generation timer.
Historical first-dispatch time and all **11 consumed calls** remain in the ledger;
age does not control new admission. The 80 cumulative inference-call ceiling is
unchanged. TCP/TLS establishment is separately bounded at ten seconds; discovery
and health checks remain short bounded reads. Manual pause finishes the current
request, while manual stop closes the active stream and retains partial evidence.
A connected silent request can wait until manually stopped or disconnected. Actual
connection failures, incomplete streams and identity failures remain failures;
two consecutive connection failures stop dispatch. No failed/uncertain task gets
an automatic identical retry. Historical/other workflows retain their own policies.

Order is now **Gatheral reviews 1, 2, 4 first**, then conversion/review pairs for
6–11. No existing draft is regenerated. Klebaner, Gatheral 3 and Gatheral 5 remain
explicit gaps. Gatheral 3 call-009 ended `length` at 131,072 completion tokens,
125,976 reasoning tokens, 16,364 final characters and 2,221.456s. Gatheral 5
call-011 has `Remote end closed connection without response`, no usage/finish
counters, 463.581s; proximity to the old deadline does not prove its cause. There
is no automatic new G3 experiment or G5 replay.

Both conversion and critic output allowances are now explicit **131,072**; readiness
is 2,048. The complete source and simple prompts are unchanged. In copied conversion
bodies, only `stream` changes to true. The first three critic bodies contain the
exact MinerU extraction and exact corresponding completed TeX. 669 source/native/
provenance/asset files and all three inherited completed drafts were checked unchanged.
Conservative UTF-8 request bytes + 4,096 template margin + output fit the saved
1,048,576 context; live health is rechecked each call. No tokenizer was installed;
the estimate can over-reject but never clips input.

Streaming uses the existing local HTTP client under an opt-in simple-chapter
purpose. It flushes raw SSE, separated reasoning, final text and timestamped delta
events as data arrives; retains partial trailing wire bytes; rejects incomplete
streams, wrong identities and malformed/tool output. Every completed or failed
attempt retains request/settings, raw response, available reasoning/answer,
usage/finish/timings and seal. Locally assembled delta JSON is labelled as such.
Output exhaustion remains truncation, even with partial final text. Exact source,
first GLM TeX, critic findings and any supplied complete revised TeX are separate
versions. Revisions stay UNACCEPTED and never replace the first draft. Findings-only
and ambiguous revisions are recorded accurately. Compilation logs/PDF are separate
per version, not a proxy for mathematical validity.

Installed runtime inspection: launcher MAX_TOKENS=32768 is an omitted-request
default; saved call-009 actually exercised 131,072. Explicit output is bounded by
remaining effective context, not an established separate 131,072 maximum. Cached
regular model config and saved health report 1,048,576 context tokens. Installed
README/template/patches support low/high/max effort (medium maps to high), default
max when thinking is enabled, and explicit thinking enable/disable. No overrides
were introduced and no higher ceiling was tested. The complete Open WebUI settings
remain unknown. Exact inspected source paths/hashes and qualifications are in
`installed-runtime-inspection.json` and
`docs/evidence/simple-chapter-continuation-20261026.md`.

The installed patches emit reasoning/content SSE deltas and final usage/finish
fields. Live endpoint access was sandbox-denied (`Operation not permitted`), and
Docker API access was denied before execution. These were not retried or bypassed.
Live streaming/current container behavior and real compiler execution remain
untested here. The operator's single streamed readiness checks the intended alias,
normal nonempty sentinel and stream completion before chapter dispatch.

Compiler: parent Gatheral 1 has an actual recorded successful two-pass build;
Chapters 2/4 record missing `enumitem.sty`/`lmodern.sty`, not established syntax
errors. The expanded isolated-image recipe includes standard LaTeX collections,
lmodern and fonts. On operator launch, a separate build with only the Dockerfile
as context creates a new immutable image and must pass real two-pass qualification
using those packages and a relative include. Host TeX/system Python and the model
image are untouched. Document compilation retains non-root, network isolation,
no shell escape, read-only source, separate output and asset/resource limits.
An exact known missing-package diagnostic permits one allowlisted environment
update and retry of unchanged saved TeX; unknown packages/assets, already installed
package failures and syntax errors never trigger install/model repair loops.
No image was built or package installed in this session. Build/qualification
failure stops before inference and retains its logs.

Requested G3 export completed:
`results/gatheral03-call009-reasoning-20261026T190941Z-22d35f.zip`, **274,390 bytes**.
It contains complete verbatim UTF-8 server reasoning, separate partial final answer,
exact request/transport settings, original raw response, counters/timings/finish,
provenance and quoted analysis with original line numbers. Mathematical work at
lines 517–535 coexists with repeated reconsideration (1349, 3867, 5292), TeX drafting
(3571 onwards, 4112) and repeated long lines. This supports repeated deliberation/
redrafting, not a proven fixed decoding loop. Possible causes are labelled
hypotheses, not findings. No expected correction was inserted into live inputs.

Validation: final full suite **465 tests in 200.878s: 447 passed, 15 sandbox socket
errors, three opt-in real-compiler skips**. All errors are mock HTTP server socket
creation denied with PermissionError; no application test failure observed. Earlier
related suite: 95 tests, 92 passed, three real-compiler skips. Final tests cover
stream serialization/durable UTF-8, incomplete/malformed/identity/truncation cases,
manual stop vs timeout, unchanged legacy limits, inherited accounting without time
cutoffs, critic ordering, immutable versions, findings-only/revision separation,
known dependencies, isolated build context and bounded unchanged-document recovery.
Mocked compiler checks do not establish real compilation. Python/bash syntax,
whitespace, original evidence and ZIP integrity checks passed. No inference or OCR.

New report: `runs/simple-chapter-glm-trial-20261026T192951Z-3efb02/report.html`.
Offline checks: that run's `offline-validation.json`, `offline-full-tests.log`,
`offline-related-tests.log` and `installed-runtime-inspection.json`.
Preparation inspection ZIP:
`results/simple-chapter-glm-inspection-20261026T192951Z-3efb02-1793043331798307135.zip`
(11,983,254 bytes). The small G3 reasoning ZIP above is the requested upload artifact.

Files changed for this update: `probe/local_model.py`, `probe/chapter_glm.py`, new
`probe/chapter_stream.py`, new `probe/compiler_environment.py`,
`scripts/simple_chapter_glm.py`, `scripts/tex-compiler/Dockerfile`, new
`tests/test_simple_chapter_continuous.py`, `README.md`, `docs/SIMPLE-CHAPTER-GLM.md`,
`docs/evidence/simple-chapter-continuation-20261026.md`, `docs/PROJECT-STATE.md`.
The existing shell wrapper remains unchanged. Unrelated work and AGENTS.md were
preserved; all changes are unstaged.

Next operator action:
`cd /home/mdi/projects/pdf-to-latex && bash scripts/run-simple-chapter-glm.sh run`.
It discovers the new path, refuses conflicting writers/workloads or unavailable/
wrong GLM, starts persistent tmux, runs the full tests, prepares/qualifies the
compiler environment, captures fresh streamed readiness, then reviews 1/2/4 and
continues paired work. It prints the real run/log and never changes a model service.
The same wrapper supports status, pause, stop, resume and bundle without manual
path variables. See `docs/SIMPLE-CHAPTER-GLM.md` for semantics and limits. No claim
of an accepted book, whole-book fidelity or new real compilation is made.

## 2026-10-26 — Two-source, meaning-focused simple chapters (offline, not launched)

Implemented the user's new contract within the SIMPLE route. Final preparation:
`runs/simple-chapter-glm-trial-20261026T210920Z-316b1a`.
**Prepared only; zero new inference calls.** It links the explicitly unlaunched
`runs/simple-chapter-glm-trial-20261026T192951Z-3efb02`. All eleven inherited calls,
original first-dispatch time, successful drafts, failed attempts and original
acceptance records remain unchanged. The parent's full file manifest was compared
unchanged. Intermediate offline preparations ending `205636Z-d82c0a`,
`205933Z-7220bf` and `210258Z-395343` remain preserved, unlaunched and superseded;
only the final path above matches the final code and current wrapper pointer.
No old seal was patched to claim changed code had run previously.

Both actual saved model requests now receive PRIMARY native MinerU chapter text
and SECONDARY native PDF text. The primary assembly/formula strings, assets and
owned-page mapping are reused unchanged: 669 existing source/native/provenance/
asset files match the parent. PyMuPDF 1.26.6 reads original PDF pages once in order,
using TEXTFLAGS_TEXT and sort=False, with no isolated-number/page-furniture filter.
Cached secondary.txt/secondary.json preserve exact page text, original file hash,
physical/selected/established printed mappings, extractor version/method and text
hashes. 161 Gatheral main-chapter pages (PDF 32–192) and 31 Klebaner Chapter 4 pages
(PDF 106–136) have no duplicate/context-window pages. Original PDF identities were
verified against existing provenance while preparing their actual consumed text;
no OCR was rerun and no model weights were rehashed. Source PDFs are unchanged.

Bounded lookup did not identify actual Open WebUI extraction text or a readily
available extractor configuration in supplied inputs/Downloads and documented
GLM installation. Available ch4.tex is generated model output, not used as source.
The secondary extraction is labelled native PDF text, not an exact reproduction
of Open WebUI's unknown pipeline. No credential/deployment database was read.

The new short conversion/critic prompts prioritize complete mathematical/factual
meaning and attribution, permitting equivalent prose and logged clear corrections
while retaining uncertain readings. Signs, conditions, quantifiers, negations,
indices, bounds and references remain substantive. Both sources can be wrong,
native text can flatten mathematics, and the printed source can itself contain
errors. Disagreement is not settled by source priority, voting or memory. The
original PDF establishes printing, but this route supplies text only; it does
not claim vision qualification. Unsettled image questions retain page/location.
Sources remain data, not operational instructions. No output blocks/markers,
assignment lists, model-returned hashes or mandatory content/notes JSON.

Actual complete saved conversion requests (12) and existing-draft critic requests
(3) were inspected for delivery of both full extractions. Critic requests also
contain the exact draft and retrospective baseline notes from conversion time
only; their original-note paths/hashes resolve correctly. No later T1–T3/M1–M3
manual diagnosis or expected solution was inserted. All three saved drafts remain
byte-identical. The new policy requests 131,072 output tokens for both phases,
stream=True, and no sampling/reasoning override. Readiness remains separately
bounded in tokens, automatically captured; no manual readiness-path entry.

Offline context estimates include complete instructions, both sources, draft/notes
when present, 4,096 template allowance and requested output. Conversion totals:
157,892–301,478; saved-draft critics 1/2/4: 234,381 / 204,604 / 170,991. These fit the
historically recorded 1,048,576 context, but **current effective context fit remains
unverified** because no live health request was made. Controller tokenizers and
transformers are unavailable; the recorded byte-based estimate is conservative,
not an invented exact token count. No input is clipped and output is not reduced.
Each actual call rechecks live capacity; a context-budget gap is retained before
dispatch and does not block independent eligible chapters. Future critic budgets
wait for their actual generated draft and notes.

Accuracy artifacts now distinguish initial TeX, initial Markdown notes, any complete
critic-revised TeX, post-critic notes and a material-change record/full mechanical
diff. Findings-only, malformed notes, a model's explicit “No material issues
reported” and failed/truncated review are distinct; none is certification. A useful
complete TeX fence survives differently formatted notes, including other note/code
fences. Raw responses/reasoning/settings/usage/finish/timings remain retained.
No new call merely reformats notes. A failed or partial critic cannot replace
initial TeX. Revisions are separate experimental working versions; old proposals
are not accepted and earlier versions are never overwritten.

Baselines for saved 1/2/4 are retrospectively assembled solely from their original
conversion notes, not newly invented assessments. Five open historical claim groups
remain (2/2/1); these are not five verified errors. Presentation and positive
bookkeeping are retained collapsed outside the main queue. Exact duplicate notes
are grouped. Python owns stable issue IDs, metadata and hashes; responses remain
free-form. Silence or an unsupported “fixed” does not close an issue. Exact IDs or
exact named headings can associate updates; ambiguous association stays open.
Automatic closure is limited to an explicitly claimed extraction/transcription
resolution with a unique exact source quotation, matching actual old/new edit at
that context and a complete revised document. Unverified mathematical derivations
or author-error claims stay visible for assessment even if a proposed working
revision includes the change. No fuzzy matcher or proof checker was added.

Development evidence was checked on original PDF 47, 52, 53 and 54, not a repeated
full ten-page audit. Ordinary C versus calligraphic C and p(k) versus psi(k) appear
in the saved extraction/draft discrepancies. Native PDF 53 preserves “Chapter 5 of
Kloeden and Platen (1992)”; the old conversion notes explicitly say the detached 5
was discarded. This locator reaches both actual new Chapter 2 request bodies.
The small source-checked fixture tests that retention; it is never used as a model
input. The inner du, eta/2 and radical discrepancies are visibly printed source
issues, not automatically GLM transcription failures. The quadratic-form comparison
is an algebra check, not validation of the stochastic scheme or substitution of
E[Z²] for realized Z². See docs/evidence/two-source-chapters-20261026.md. Later audit
findings remain outside baseline notes and model requests.

Schedule remains: critic for saved Gatheral 1, then 2, then 4; then conversion and
immediate critic pairs for 6–11. Klebaner 4 and Gatheral 3/5 remain explicit gaps
without automatic retry. No overall or generation deadline returns. The separate
ten-second connection timeout, real transport-error handling, manual pause/stop/
resume, durable streamed reasoning/answer capture, shared 80-call ceiling and
compiler dependency recovery remain. Isolated compilation stays separate from
mathematical content; missing packages cannot cause model regeneration. No image
build, installation, compiler execution, service operation or inference occurred
in this task. Prior sandbox limitations were not bypassed or retried.

Validation: 19 focused tests passed. Related suite: 106 tests, 105 passed, one
opt-in real-compiler skip. Full suite at the final functional state: 484 tests in
219.624s, **466 passed, 15 sandbox socket-permission errors, three opt-in real-compiler
skips**. All errors are denied mock HTTP server creation; no application assertion
failure. After that suite the launcher display alone was amended to print its
actual report path beside the log; Python/bash syntax, prepared request/evidence
checks and whitespace checks were repeated, not the full suite. Earlier development
runs remain local test logs; the quoted result is the functional-state validation.
The normal-terminal wrapper runs the exact current code/test suite before dispatch.
Coverage includes native page ownership, locator retention, actual HTTP serialization
of both sources, full-request budgeting/no clipping, context-gap continuation,
tolerant/unavailable notes, conservative issue carry-forward, source-evidenced edit
resolution, failed-critic preservation, separate revised versions, provenance,
resume without replay, ordering and inherited accounting. Live GLM quality, live
stream behavior and new isolated compiler execution remain untested here.

Final report:
`runs/simple-chapter-glm-trial-20261026T210920Z-316b1a/report.html`.
Inspection ZIP:
`results/simple-chapter-glm-inspection-20261026T210920Z-316b1a-1793048994380945649.zip`
(**12,489,547 bytes**, ZIP integrity checked). It includes both cached extractions,
exact request previews, initial drafts/notes, provenance, statuses and preparation
validation. It does not pretend post-critic artifacts exist before dispatch.
Full validation is offline-validation.json in the run, with offline-full-tests.log,
offline-focused-tests.log and offline-related-tests.log. No whole-book completion
or mathematical acceptance is claimed.

Files changed for this task: new probe/chapter_sources.py,
new probe/chapter_accuracy.py, probe/chapter_protocol.py,
scripts/simple_chapter_glm.py, new tests/test_two_source_chapters.py,
new tests/fixtures/gatheral-ch2-locator.json, README.md,
docs/CODEX-HANDOVER.md, docs/SIMPLE-CHAPTER-GLM.md,
new docs/evidence/two-source-chapters-20261026.md, docs/PROJECT-STATE.md.
The existing shell wrapper, compiler implementation, streaming client, AGENTS.md,
source registry and unrelated work were preserved. All changes remain unstaged;
no Git metadata operation was performed.

Next operator command:
`cd /home/mdi/projects/pdf-to-latex && bash scripts/run-simple-chapter-glm.sh run`.
It discovers the final preparation, checks workload/model identity, starts tmux,
runs current full tests, prepares/qualifies the existing isolated compiler recipe,
captures text-only streamed readiness, then starts saved Chapter 1 criticism with
both sources and baseline notes. It prints actual run/report/log paths. Status,
pause, stop, resume and bundle use the same wrapper without shell variables; pause
finishes the current call, stop interrupts it while preserving evidence, resume
skips existing attempts. No model service is switched automatically.

## 26 October 2026 — fresh Gatheral two-source run prepared, not launched

The user superseded reuse of completed GLM conversions and authorized fresh
conversion/critic pairs for all Gatheral chapters, including Chapters 3 and 5.
Prepared `runs/simple-chapter-glm-trial-20261026T212942Z-533351`; the existing wrapper
pointer now selects it. There are **zero calls, 26 pending tasks**, no first-dispatch
timestamp, no historical drafts, no Klebaner and no inherited skip list. This is a
separately authorized experiment with the existing 80-call ceiling across its
resumes; the earlier eleven calls remain unchanged in their original runs, explicitly
recorded as previous-experiment history rather than relabelled as new results.

Exact order: Chapter 1 conversion then its critic, Chapter 2 conversion then its
critic, continuing through Chapter 11, then postscript conversion/critic and
bibliography conversion/critic. This preparation has no initial Chapter 1 success
gate: an isolated content failure leaves that part unresolved and permits later
parts to proceed. Identity, integrity, repeated connection-failure and manual
pause/stop protections remain. There are no automatic retries or new experimental
gates. Source and request bindings protect the selected task scope/order.

Scope verified against the existing native preparation and owned-page maps:
**167 distinct physical PDF pages 32–198**, main chapters 32–192, postscript 193,
bibliography 194–198. All **76 native bibliography ref_text blocks** are retained,
including the source's author/reference text. Outside this run: front matter 1–31,
intentional blank 199, index 200–210 (43 pages). The sealed inputs/scope.json accounts
for all 210 pages without overlap. This is not complete-book coverage or a visual
fidelity review; original PDF and saved MinerU evidence are preserved.

Reused `runs/chapter-glm-input-20261026T031434Z-2392d8` from completed MinerU conversion
`runs/convert-basic-20261025T230247Z-e6bb30`. Reused the secondary caches from
`runs/simple-chapter-glm-trial-20261026T210920Z-316b1a`. All eleven primary assemblies,
native JSON files, secondary text/metadata files and two-source conversion requests
are byte-identical to that preparation. Only six previously uncached native-PDF
pages (postscript/bibliography) were extracted using existing PyMuPDF. No OCR rerun,
model call, compiler execution, installation, service operation or Git mutation.
The original cache directory's complete file manifest is unchanged after preparation.

One initial offline attempt stopped on native CRLF normalization in the new cache
comparison, before sealing or dispatch. Fixed that comparison to use exact UTF-8
bytes and covered it with a regression; retained the zero-call partial directory
`runs/simple-chapter-glm-trial-20261026T212855Z-e58956` for transparency. The completed
preparation above is the sole current pointer. No old evidence was repaired/resealed.

Settings and prompts are unchanged from the meaning-focused two-source route:
exact regular glm53-regular at http://192.168.1.100:8888/v1; 131,072 requested output
tokens for conversion and critic; server sampling/thinking defaults omitted;
streamed reasoning/raw answers, distinct initial/revised TeX and accuracy records;
isolated compiler recovery; no overall or generation deadlines; separate ten-second
connection establishment timeout; manual pause/stop/resume. No baseline accuracy
notes are invented. Exact critic requests will use each newly generated draft and
its new initial notes, immediately following its conversion.

All thirteen saved conversion requests were checked to contain both complete
extractions and preserve literal native formula strings. Conservative full-request
byte-based context upper estimates including output range **140,950–256,064**.
They fit the historically recorded 1,048,576 context window, but current server
capacity remains unverified offline. Launch and each dispatch check it; later
critic budgets include the actual draft/notes when available. Nothing is clipped.

Checks: related suite **109 tests, 108 passed, one opt-in real-compiler skip** in
8.796 seconds after the cache fix. Covers fresh scope/order, cache byte preservation,
CRLF handling, cache mismatch rejection, prior evidence preservation, no inherited
drafts/calls/skips, first-chapter failure independence and existing request/accuracy/
streaming/resume/compilation protections. Python import/CLI, bash syntax, binding,
input/request/page coverage, ZIP integrity and git diff --check passed. Full suite
was not repeated for this narrow scheduling change; the launcher runs the exact
current full suite in the normal terminal before dispatch. Live model behavior,
current context, live streaming and real compiler execution remain untested here.

Report: `runs/simple-chapter-glm-trial-20261026T212942Z-533351/report.html`.
Validation: that run's `offline-validation.json` and `offline-related-tests.log`.
Inspection ZIP:
`results/simple-chapter-glm-inspection-20261026T212942Z-533351-1793050270782083790.zip`
(9,233,038 bytes; integrity checked). It contains preparation/evidence and pending
statuses, not generated chapters or completed reviews.

Files changed in this task: scripts/simple_chapter_glm.py, probe/chapter_sources.py,
new tests/test_fresh_gatheral.py, README.md, docs/CODEX-HANDOVER.md,
docs/SIMPLE-CHAPTER-GLM.md, docs/PROJECT-STATE.md. Unrelated edits and all old evidence
remain preserved. No AGENTS.md, source registry, model service or compiler recipe
change. Everything remains unstaged.

Next operator command:
`cd /home/mdi/projects/pdf-to-latex && bash scripts/run-simple-chapter-glm.sh run`.
It discovers the actual new path, checks workload/GLM identity, starts persistent
tmux, runs required tests/compiler readiness and captures text readiness, then
starts fresh Gatheral Chapter 1 conversion. No inference has started in this task.

## 27 October 2026 — Bergomi full-PDF extraction prepared; operator launch required

Task 1 remains extraction only. The transferred file is now present and inspected:
`inputs/bergomi/source.pdf`, 105,214,331 bytes, **520 physical pages**, SHA-256
`35fd11fb3fe46e9c3de01db6b22dc1e2c848c04b352121fe13c3ccf0fba38413`.
Title: **Stochastic Volatility Modeling**, Lorenzo Bergomi, Chapman & Hall/CRC,
Taylor & Francis Group, ©2016, PDF version date 20151105, eBook PDF ISBN
978-1-4822-4407-6. No numbered edition appears on the inspected title/copyright
pages; do not infer one from the filename. Visual checks covered physical pages
6, 7, 8 and 520; contents and every chapter-opening native text match the 12
chapter bookmarks. Detailed ranges and provenance are in
`docs/source-provenance/bergomi-intake-20261027.json` and `docs/BERGOMI-EXTRACTION.md`.

Chapter ranges (physical PDF, inclusive): 1:18–41, 2:42–119, 3:120–149,
4:150–167, 5:168–217, 6:218–233, 7:234–323, 8:324–373, 9:374–407,
10:408–437, 11:438–469, 12:470–511. Front matter 1–17, epilogue 512–513,
bibliography 514–519, back cover 520. Main-text printed page = physical −17.
Embedded mathematical appendices, captions, figures, tables, footnotes and
references remain within the all-page selection. **Source limitation:** contents
lists an index at printed 503, but the supplied PDF ends after bibliography printed
502 at physical 519, followed by back cover 520. The supplied PDF has no index
pages to extract. This is a source limitation, not an OCR omission.

Registered only the new `bergomi` source, using all 520 pages with identity original
mapping, actual original hash and `ocr_mode=auto` (native text present). Every
existing source entry, including Gatheral, is unchanged. New offline intake:
`inputs/bergomi/intake/`, containing 520 page-located native-text files (1,013,219
characters total), metadata/bookmarks/catalogue labels, source identity, manifest,
window plan and readable `report.html`. No numeral or content filtering. Native text
declares physical pages 5,119,149,217,323,373,407,437,469 intentionally blank; all
remain selected. Text-empty pages 1/520 are image covers, not blanks. The generic
cache marks unverified blank status conservatively; source-checked interpretation
is recorded separately in the provenance document. No sealed intake was rewritten
to disguise manual findings as extractor output.

The existing 8-owned-page/1-adjacent-context profile yields **65 windows** and
exactly one owner for each of 520 pages. `scripts/run-gatheral-extraction.py` now
accepts an internal source parameter while preserving its Gatheral CLI/defaults.
The new small Bergomi wrapper reuses its converter invocation, log/exit handling,
saved-run discovery and resume. It does not add another scheduler or converter.
Failed/interrupted windows remain visible; completed windows retain integrity
checks and are not rerun. The existing converter stops at a failed window; later
windows remain pending for resume, never counted as done or silently discarded.

One normal-terminal command:
`cd /home/mdi/projects/pdf-to-latex && .venv-control/bin/python -B scripts/run-bergomi-extraction.py run`.
The wrapper validates/cache-reuses intake, runs focused tests, checks both writer
locks, visible project jobs, both node deployments, exact regular GLM identity and
idle/queued workload counters, then uses only the verified existing two-node
`/home/mdi/local-llm/glm53-flash-tensorfold/stop.sh` helper. Unknown deployments or
busy/uncertain GLM stop launch without service changes. Both nodes are rechecked;
head memory must meet the unchanged 8 GiB floor. The new tmux session is
`bergomi-extraction`. A worker recheck prevents starting OCR if GLM became resident
again. No silent provider/model substitution and no service restart.

Established execution remains MinerU 4.0.12/DocVortex 0.5.16 (installed metadata
verified), `.venv-mineru`, existing model-cache, Basic CPU/ONNX, isolation none and
existing offline worker controls. No overall deadline was introduced; established
3600-second per-window timeout remains. There is no model-readiness inference for
this extraction. `status`, `pause`, `resume` and `bundle` use the same wrapper;
pause verifies the owned tmux worker before SIGINT and retains interrupted evidence.
Existing reporting supplies raw native structured OCR, assets, maps, Markdown/TeX
drafts, review.html, quality-report.json and result ZIPs. Native text is separately
cached in ignored inputs. These are unreviewed extraction products, not GLM output.

**Actual state: prepared, NOT RUNNING.** Docker socket access was denied and tmux
socket access returned Operation not permitted in this session. Neither denied
operation was repeated or bypassed. No service transition, OCR, inference, install,
permission change or Git mutation occurred. No Bergomi conversion directory or
runtime terminal log exists yet. The operator command prints the actual run after
the converter's normal runtime/model fingerprinting, and its terminal log under
`runs/bergomi-operator/launch-.../terminal.log`; `status` discovers both automatically.
Do not confuse the offline test log with a live extraction terminal.

Observed Gatheral state is now `finished_with_gaps`, with **24 recorded calls**:
Chapters 6/7/11 conversions truncated and their reviews unavailable; bibliography
conversion and review complete. Its saved launch exit is status 2 at
2026-10-27T05:29:11.930862+00:00. Project writer lock was available. Its binding,
state, input manifest and summary hashes remained unchanged during this task.
Sandbox process/container visibility cannot establish all host workloads idle;
the operator launcher must still perform its normal-terminal checks.

Offline validation: **55 tests passed in 4.593s**, including nine new intake/service/
source-routing/logging checks plus existing Gatheral, converter/resume, PDF and
isolation checks. Python AST syntax and git diff --check passed. New input/cache
and operator outputs are Git-ignored. No sandbox socket tests failed in this focused
suite. Real Docker/tmux/SSH service transition and MinerU execution remain untested
here; the launcher runs the nine focused tests again before changing services.

Preparation/execution identity: `runs/bergomi-operator/preparation.json`.
Offline test log: `runs/bergomi-operator/offline-tests.log`.
Input report: `inputs/bergomi/intake/report.html`.
The execution directory remains `/home/mdi/projects/pdf-to-latex`. Actual converter
resume fingerprints all top-level probe modules, source metadata/hash, converter
packages, model-file hashes, worker, window/context, timeout, memory and isolation;
completed output/page-map/input hashes are rechecked. The wrapper also records its
scripts and configuration/registry at launch. Task 2 must use an ordinary separate
development copy while extraction is unfinished, preserving this checkout/input,
environments and model cache. No execution-snapshot framework was added.

Files changed: scripts/run-gatheral-extraction.py, new scripts/run-bergomi-extraction.py,
new scripts/book_extraction_intake.py, new tests/test_bergomi_extraction.py,
sources.json, new docs/BERGOMI-EXTRACTION.md,
new docs/source-provenance/bergomi-intake-20261027.json, docs/CODEX-HANDOVER.md,
docs/PROJECT-STATE.md. AGENTS.md, converter implementation/configuration, Gatheral
source and all completed runs remain unchanged. Unrelated work is preserved and
all changes remain unstaged. No Gatheral editorial work or GLM conversion began.


## 2026-10-27 — annotated Gatheral edition and serial recovery/Bergomi continuation (isolated development)

The original extraction checkout remained unchanged. Bergomi MinerU was actively
running at `runs/convert-basic-20261027T065138Z-f5d477`; work used independent ordinary
files in `/tmp/pdf-to-latex-editorial-development-20261027`, with original hashes in `development/baseline.json`.
No Git mutations, installs, inference, service changes or permissions changes occurred.

Prepared (NOT running): `/tmp/pdf-to-latex-editorial-development-20261027/runs/editorial-chapters-trial-20261027T075228Z-e97ec1`.
Report: `/tmp/pdf-to-latex-editorial-development-20261027/runs/editorial-chapters-trial-20261027T075228Z-e97ec1/report.html`.
Working edition/master and chapter files: `/tmp/pdf-to-latex-editorial-development-20261027/runs/editorial-chapters-trial-20261027T075228Z-e97ec1/editions/gatheral-1793087992088374297`.
Compact inspection: `/tmp/pdf-to-latex-editorial-development-20261027/results/editorial-chapters-inspection-20261027T075228Z-e97ec1-1793087992319066847.zip`.
Code patch/copy-back bundle: `/tmp/pdf-to-latex-editorial-development-20261027/development/task2-editorial-20261027T080232Z.zip`.
Preserve the temporary development directory/bundle until guarded copy-back occurs.

The parent `runs/simple-chapter-glm-trial-20261026T212942Z-533351` remains unchanged:
24 calls, 27,920.0166 recorded request seconds. Calls 012/013/020 exhausted 131,072
reasoning tokens each without final text; 023/024 are the bibliography. The new
preparation has zero calls, retains historical provenance separately, and defines
33 new Gatheral units: 15 section-output conversions with immediate critics
(Chapter 6: five sections; Chapter 7: six; Chapter 11: four), plus finite editorial
requests for Chapters 3, 5 and 10. Each unit has one attempt; the initial new-work
ceiling is 98 including bounded resume readiness, without resetting historical
accounting. There is no overall/generation deadline; connection timeout remains
10 seconds. New prepared requests include the exact controlling editorial policy,
both fallible extractions, visible attributed corrections/unresolved notes, and
131,072 requested shared reasoning/output tokens. No JSON/block-output contract.

32 exact version-bound offline edits and individual dispositions are recorded in
`docs/gatheral-editorial-plan.json`. Source inspection supports the missing eta
factors while retaining the pricing PDE/alpha-prime convention; the explicit stock
drift; the visible Chapter 4 initial-variance qualification; Table 5.4's overbar;
the hatted-definition introduction; the 24%/2.88% coupon arithmetic; k-coordinate
prose; the -12% no-global-floor bound; and corrected note locators/sign comparison.
Prior useful GLM repairs are retained. The 15/20-year period, T-star consistency,
remaining Chapter 3 conventions and reverse-cliquet contract meaning remain
explicit where not settled. No complete mathematical audit is claimed.

Chapters 8/9 retain their complete first drafts after successful findings-only
critics. Chapter 9's Markdown-fenced notes were recovered without inference.
Resolved model claims, independently checked edits, contextual observations,
cosmetic entries and open items are separate; unsupported claims are not independent
verification. Raw notes and prior versions remain available. A failed or ambiguous
critic cannot overwrite the first draft. New section requests never use TeX copied
from diagnostic reasoning as a final answer.

The bibliography keeps 76 stable ordered keys, original printed PDF pages and
native extraction, historical GLM rendering, normalized TeX and structured JSON.
Repeated-author expansions are attributed Codex source-sequence readings; unknown
fields remain null. Black–Scholes page correction and Dumas et al. enrichment are
attributed to the user's supplied ChatGPT primary-publisher checks, not a new fetch.
The breve and two URL underscores were inspected; Matytsin tilde/reachability
remain unverified. Earlier discussion-paper versions are not replaced.

Gatheral chapters/postscript/bibliography cover PDF 32–198. PDF 1–31, 199–210 are
preserved as a searchable original-page supplement, including original index
locators. Missing Chapters 6/7/11 and uncompiled derivatives are visible gaps.
The master uses relative PDF inclusions through TeX part files to isolate
incompatible historical preambles; standalone editable TeX/assets are retained.
No new PDF compilation has been claimed.

Bergomi still requires completed 65-window/520-page owned evidence and successful
operator exit before preparation/copy-back. Its actual recorded 12-chapter,
appendix, epilogue/bibliography map and cached native PDF text are reused. No index
pages exist in the supplied PDF. The guarded normal-terminal bootstrap waits
read-only, refuses failed/paused OCR or conflicting destinations, copies only
reviewed changed files, runs normal-terminal tests once, arranges idle regular GLM
using the existing helpers (downloads/setup disabled), captures readiness, executes
Gatheral recovery/editorial work, assembles/compiles, then prepares/runs Bergomi
section/critic pairs. No manual readiness path entry or new OCR is needed.

Validation: broad suite ran 516 tests in the development copy: 489 passed, 15 errors
were all sandbox-denied mock loopback sockets, 12 skipped; no assertion failures.
After final narrow transactional/ambiguous-notes protections, focused checks:
22 tests, 21 passed, one optional real compiler test skipped. Python syntax and
wrapper syntax checked. Actual saved Gatheral native-reader/renderer exercise:
210 distinct owned pages, 2,184 blocks, 1,113 literal formula strings preserved;
one native table-renderer occupancy warning retained its fallback. Actual final
preparation accounts for 124/160/294 source blocks in the three recovered chapter
plans without duplication. All 18 currently concrete requests contain both
extractions; 15 critic requests correctly await their actual generated drafts.
Maximum conservative request+template+output bound: 307,493 tokens against recorded
1,048,576 capacity, rechecked live. This is not an exact tokenizer count.

This session's tmux socket was denied (`Operation not permitted`) and Docker socket
was denied (`permission denied`). Real model delivery, live service transition,
Bergomi preparation against future completed evidence and real compilation remain
untested here. The already qualified expanded image is retained:
`sha256:b9505ed9122f83fd4bb4ae2ab79a1a7ad82187ca712fda0e8868e4e374296211`.
See `docs/EDITORIAL-CHAPTERS.md` for the single persistent launch, status, pause,
resume, bundle and optional real annotation/PDF-text regression commands.

### Final isolated preparation pointer (27 October, 08:05 UTC)

Use `/tmp/pdf-to-latex-editorial-development-20261027/runs/editorial-chapters-trial-20261027T080547Z-846061` and `/tmp/pdf-to-latex-editorial-development-20261027/runs/editorial-chapters-trial-20261027T080547Z-846061/report.html`. Its code-only link corrects the displayed book name for prefixed Bergomi unit IDs; input/request seals are byte-identical to the preceding zero-call preparation. No historical evidence or consumed-call total changed. The final inspection is `/tmp/pdf-to-latex-editorial-development-20261027/results/editorial-chapters-inspection-20261027T080547Z-846061-1793088347548811446.zip`; code patch bundle `/tmp/pdf-to-latex-editorial-development-20261027/development/task2-editorial-20261027T080855Z.zip`. `bibliography/printed-bibliography.pdf` preserves actual original pages 194–198; `references-structured.json` supplies stable keys, author text/year, attributed publisher enrichment and null unknown fields. The older filename `printed-reference-version.tex` denotes the inherited GLM rendering, not a facsimile.

Final focused regressions: 22 tests, 21 passed and one opt-in real compiler check skipped. All 173 original baseline files still match; 15 changed project files remain isolated. Read-only diff whitespace checks passed. Docker/tmux launch and real compilation remain sandbox-blocked. The normal-terminal bootstrap performs the remaining full-suite check once before any model dispatch.

## 27 October 2026 — integrated editorial launcher repair and linked resume (19:52 UTC)

The preceding "isolated / prepared only / extraction still running" entries are
historical. Actual operator records now establish that Bergomi conversion
`runs/convert-basic-20261027T065138Z-f5d477` finished all 65 windows with exactly
520 distinct owned pages, 1–520. Its state is `conversion_completed_unreviewed`;
`runs/bergomi-operator/launch-20261027T065126Z-4e17f4/exit.json` records successful
converter exit 0. No converter was visible to the same-user process check and the
project writer lock was unheld at inspection. Sandbox process visibility is not a
host-wide job census; the normal-terminal launcher rechecks the head and peer.

The operator's bootstrap integrated all **15** reviewed files. Every destination
matched its recorded `after` hash before this repair:

- `README.md`
- `docs/EDITORIAL-CHAPTERS.md`
- `docs/PROJECT-STATE.md`
- `docs/SIMPLE-CHAPTER-GLM.md`
- `docs/gatheral-editorial-plan.json`
- `probe/chapter_accuracy.py`
- `probe/chapter_editorial.py`
- `probe/chapter_glm.py`
- `probe/chapter_inputs.py`
- `scripts/editorial_chapters.py`
- `scripts/integrate-editorial-development.py`
- `scripts/run-editorial-chapters.sh`
- `scripts/run-editorial-continuation.sh`
- `scripts/simple_chapter_glm.py`
- `tests/test_chapter_editorial.py`

The copied patch is `results/task2-editorial-20261027T080855Z.zip`. The actual
normal-terminal log at
`runs/editorial-chapters-trial-20261027T080547Z-846061/normal-terminal-tests.log`
records **518 tests in 213.399 seconds: 514 passed, four optional real-compiler
checks skipped, no failures/errors**. This supersedes the earlier development
sandbox's mock-socket-denied result. The bootstrap then stopped in `arrange_glm`
because the GPU inventory contained PID 3380837,
`/usr/libexec/gnome-remote-desktop-daemon`. It had not reached the GLM helper,
readiness, compilation or any model request. The run remains `prepared_offline`,
with `first_dispatch=null`, zero new calls and all 33 units pending. There is no
recorded active continuation/model attempt; the project writer lock was free.

Narrow authoritative repair: `scripts/editorial_chapters.py` now verifies the
exact system GNOME remote-desktop executable through `/proc/<pid>/exe` and its
device/inode identity before treating that GPU entry as desktop activity. It does
not trust a fixed PID, GPU-reported name, basename or substring. Unknown/Python
workloads and unreadable/replaced/deleted executable identities still block launch.
MinerU/project-job, deployment, model-identity and idle-model checks remain intact.
Both nodes' unadjusted `MemAvailable` and process identities are recorded; desktop
memory is not added back. Existing launcher/TensorFold memory admission is unchanged.
No remote desktop, model service, permissions or runtime settings were changed.

New explicit linked preparation (NOT RUNNING):
`runs/editorial-chapters-trial-20261027T195212Z-654e71`.
Its `launch_repair_parent` records the original preparation's state/binding hashes
and the one changed bound code file. The narrow `prepare-launch-repair` operation
is offline and refuses dispatched calls, stale evidence, unrelated code changes
or an obsolete pointer. Historical seals are not rewritten. All **1,242** files
in the original preparation remain byte-identical. New input/request seals,
versions, accuracy records, corrections, bibliography, assets, compiler
qualification and prepared edition match their originals. State differs only in
the new binding fingerprint. All 24 historical calls / 27,920.0166 request seconds,
zero new calls, 33 units, per-unit allowance and total call ceiling are retained.
First pending operations remain `u001-gatheral-06-s01-convert` then
`u002-gatheral-06-s01-critic`. No OCR or model work was replayed.

The current pointer retains the successful integration receipt. The actual old
`/tmp/pdf-to-latex-editorial-development-20261027/scripts/run-editorial-continuation.sh status`
was exercised read-only and forwarded to the new authoritative run. It will not
copy the older development code over this fix or incorrectly reapply pre-integration
baseline checks. The normal-terminal resume command is now:

```bash
bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh resume
```

It checks workloads, arranges the documented regular GLM deployment if absent,
starts tmux `editorial-chapters`, captures fresh readiness automatically and
continues the existing serial queue. No full suite repeats on resume. Progress:
`bash /home/mdi/projects/pdf-to-latex/scripts/run-editorial-chapters.sh status`.
Worker log (created at worker start):
`runs/editorial-chapters-trial-20261027T195212Z-654e71/terminal.log`.
Report: `runs/editorial-chapters-trial-20261027T195212Z-654e71/report.html`.
Validation details: the same run's `launch-repair-validation.json` and
`launch-repair-tests.log`.

Validation after this repair: **32 focused tests, 31 passed, one opt-in real
compiler check skipped**. Coverage includes the observed desktop case on both
nodes, preserved memory accounting, spoofed names/PIDs, Python/unknown GPU jobs,
uninspectable/deleted/replaced executables, MinerU guard ordering, no service start
after conflict, unchanged requests/corrections/accounting, stale evidence rejection
and integrated-bootstrap forwarding. Python compilation, wrapper syntax and
`git diff --check` passed. No socket tests were denied in this focused run; the
already passed normal-terminal full suite was not repeated. Live SSH/GPU identity
inspection, Docker, tmux startup, readiness and model delivery were not executed
here. All project changes remain unstaged. Files changed by this narrow repair:
`scripts/editorial_chapters.py`, new `tests/test_editorial_launch.py`,
`docs/EDITORIAL-CHAPTERS.md`, and this state log.


## 2026-10-28 — Bergomi preparation repair, current Gatheral dispositions, high/max pilot (offline)

Read instructions, checked the original writer lock was free, converter workers
absent, parent on-disk status stopped_error with no in-progress calls. The original
run `/home/mdi/projects/pdf-to-latex/runs/editorial-chapters-trial-20261027T195212Z-654e71` and its earlier ZIP
are unchanged. Confirmed 30 calls (1 readiness, 15 conversions, 14 critics),
30,274.4921 request seconds, 1,775,715 completion and 1,656,305 reasoning tokens.
Four length failures remain; call-024 has a partial final answer. The stale running
ZIP predates the Bergomi exception; terminal state was subsequently stopped_error.

Cause: the Bergomi intake's declared blank list was treated as verified-empty.
Physical pages 5,119,149,217,323,373, 407, 437, 469 each contain one correctly recognized
“This page intentionally left blank” text block. Page217 also occurs as non-owned
context in window0209–0216. Codex inspected all nine original-page images. No
cross-book list, off-by-one, missing blocks field or duplicate ownership was found.
New source/hash-bound classification retains the notices; the empty-page guard
remains strict, and its diagnostic includes source/window/physical/selected/local
indices and record. All 520 owned pages, 65 windows, 128 context appearances,
8,102 blocks and both sources across 16 parts preflighted; all assets/native formulas
retained. There are 118 explicit native-renderer fallbacks requiring later fidelity
assessment. 133 conversion previews fit the recorded context bound (largest 789,339
including 131,072 output), no clipping or reduced full-chapter context. Actual
server context and future critic draft size are rechecked before dispatch.

New linked preparation: `/home/mdi/projects/pdf-to-latex/runs/editorial-chapters-trial-20261028T072031Z-41483c`. **Prepared only, zero new model calls.** Retains the
30 parent calls and 24 earlier calls; parent limits are not reset. The three pilot
conversions use exact historical requests plus high effort: G6s03(call006),
G7s01(call012), G7s05(call019). Immediate max critic after each complete conversion;
at most 6 task calls plus 3 readiness calls across resume, no repeat attempts. The
pilot stops for inspection; Bergomi and other recovery previews cannot dispatch.
Ordinary conversion/critic defaults max/max, explicit validated preparation choices;
actual top-level transport field is now transmitted. Installed local THINKING=1,
recipe commit 3fd60dfc836fab0f1ed0fd4f0afaf2a1d62b2aab, patch/template low/high/max
mapping inspected. Requested effort differs from runtime attestation; no speculative
reasoning-budget parameter, sampling/service change or upgrade.

Current annotations: reselected the byte-identical saved critic documents for
Gatheral 5 and 10 before their stale appended historical claims. The other 19 current
documents/notes stay unchanged. Separate history carries superseded-by links.
Hatted C/D, table overbar/prefactor, annual floor<=-12%, Jeffery reference and the
correct conventional-loss comparison survive. G5 T-star and G10 contract-intended
denominator remain open. Claim statuses are not independent verification. Exact
section target spans/pages now differ explicitly from parent/context pages; four
gaps occur at their correct positions. Current selection remains 21 available parts.

Edition: `/home/mdi/projects/pdf-to-latex/runs/editorial-chapters-trial-20261028T072031Z-41483c/editions/gatheral-1793172035172466728`. `master.tex`, editable standalone documents/assets,
bibliography and current/history logs retained. Existing exact-document PDF/compile
records inherited; rebuilt master compilation NOT performed (Docker socket denied).
Report: `/home/mdi/projects/pdf-to-latex/runs/editorial-chapters-trial-20261028T072031Z-41483c/report.html`.
Compact ZIP: `/home/mdi/projects/pdf-to-latex/results/editorial-chapters-inspection-20261028T072031Z-41483c-1793172160466305250.zip` (18,791,993 bytes), checked readable with unique member
paths and correct prepared/zero-new-call state. Full raw calls remain at linked
original evidence paths. New exception finalization saves status/stage/diagnostic
before reporting/bundling and releases locks.

Validation: full suite once, 540 tests: 521 passed, 15 socket-bind PermissionError
errors from sandbox, 4 optional real-compiler skips, no assertion failures. Final
focused recovery suite 15/15 after narrow reporting/configuration changes; earlier
chapter/stream/annotation 82 checks passed with 2 optional skips. AST/shell syntax and
git diff --check passed. Saved input/seal checks passed. No inference, OCR, cloud
credentials, paid calls, service operations, installs or Git mutations. Previous
unrelated unstaged/untracked work preserved; AGENTS unchanged by this task.

Changed files and detailed records: docs/evidence/editorial-recovery-20261028.md.
Current operator sequence: docs/EDITORIAL-CHAPTERS.md. Next operator action: normal
full tests, then `bash scripts/run-editorial-chapters.sh run` from the project.
It checks existing regular GLM, captures readiness, launches persistent tmux and
stops after the three-case pilot. Future serving comparisons are deferred with
rollback recorded; joint verification/newer stack not implemented.

## 2026-10-28 — Adopted Lewis and prepared high/max production continuation (offline)

Current preparation, **not running**:
`runs/editorial-chapters-trial-20261028T215454Z-8ef98f`.
Read AGENTS/current handover/state/runbook and saved evidence. Project/run writer
locks free, no converter or in-progress call. Completed pilot
`runs/editorial-chapters-trial-20261028T072031Z-41483c` is unchanged. Calls032/034/036
converted at high;033/035/037 criticized at max. All six returned stop/nonempty
answers and have recorded successful TeX builds. Independently compared saved
outgoing conversion bodies: only the added reasoning_effort differs from each
historical request. Timings support the next real work, not an accuracy/speed claim.

Adopted saved critic-call-037 into canonical Gatheral7-s05 without inference.
All its displayed equations preserved; the current visible note is qualified by
Codex's PDF128/printed97 image inspection and short-time expansion. The printed
J3 brace tends to3; J1=O(t²), J4=O(t³), so beta2's t^-3 term is not cancelled by
the other displayed terms for nonzero rho/eta, positive variance/lambda. Beta0's
possible cancellation cannot be ruled out without the absent J2 definition.
Precise coefficients still require Lewis(2000), pp142–144 and definitions. This
is flagged usable transcription, not a failed section. No coefficients invented.

Inspected PDF120/printed89 and corrected the canonical Figure7.1 caption's
extraction-added sigma/nu tildes; retained proof tilde-x and restored rho-eta prose
factor. Retained Chapter3 reference using the actual Heston derivation(3.19),
PDF66/printed35; removed the impossible-self-reference rationale. Canonical6-s03
is byte-identical; neither pilot control was substituted. Full before/after logs
and immutable versions remain. Current Lewis/caption dispositions are readable
once, with raw Markdown/history separate; explicit note-label links suppress
duplicate rendered notes. No-change observations are not corrections; mentioning
a no-change control does not hide another open issue. Exact source hashes, edits,
attribution and history links are recorded in adoption-record.json and the
reviewed docs/gatheral-pilot-adoption-20261028.json (not model input).

Queued: Gatheral7-s03 Including Jumps; six already prepared natural subsection
pairs for11-s02; five for11-s03; full Bergomi Chapter1 (Introduction, physical18–41)
conversion/critic pair. Stop after that pair for inspection. 13 conversions,
at most13 immediate critics, plus one readiness per launch. A content failure
remains a gap and independent work continues. No automatic retry; shared
identity/integrity/connection failures stop. Both full extractions retained in
all13 actual conversion requests, high/max,131072 each, streaming, unchanged
sampling defaults.553 target blocks are unique; each recovery parent is exactly
partitioned. First Bergomi chapter has319 substantive blocks. Conservative
input/template/output bounds193905–376410 fit recorded capacity1048576, with
live checks including critic draft size before dispatch; no clipping or exact
tokenizer claim.

Local overall call limit is explicitly null/unlimited in the new binding/state.
All37 parent calls and24 earlier calls remain (61 consumed); old sealed limits
are unchanged. Explicit26-task admission, one attempt per unit, retained history,
manual pause/stop/resume and one readiness per launch govern execution; no overall
or generation deadlines. Later manual resume is not blocked by cumulative call
count. Paid/cloud and other experimental limits are untouched. The other132
prepared Bergomi conversion units remain dormant; no full-book dispatch authorized
by this stage. OCR/preparation remains520 pages/65 windows/8102 recognized blocks,
9 intentional-blank notices and118 native-renderer fallbacks, not certified fidelity.

Edition:
`runs/editorial-chapters-trial-20261028T215454Z-8ef98f/editions/gatheral-1793224497328383556/`.
Contains master.tex, editable chapters/assets, normalized bibliography and accuracy
records. Lewis is present; three parent gaps remain as12 precise subsection notices.
Front matter/index remain original-page supplements. Other unresolved mathematical
issues are retained. Source completeness and compilation are separate from fidelity.
Unchanged documents retain successful recorded builds. Docker API was sandbox-denied;
the two edited documents/new master have not compiled here. Operator launch uses
qualified compiler image sha256:b9505ed9122f83fd4bb4ae2ab79a1a7ad82187ca712fda0e8868e4e374296211.

Report: `runs/editorial-chapters-trial-20261028T215454Z-8ef98f/report.html`.
Inspection ZIP:
`results/editorial-chapters-inspection-20261028T215454Z-8ef98f-1793224630560782987.zip`
(21,986,082 bytes;731 unique members; ZIP integrity checked, prepared/zero-new-call
state and unlimited local ceiling confirmed). Full raw historical calls remain
linked, not rewritten. New terminal.log will be created on operator launch.
Two earlier offline preparation attempts remain preserved, unused:214827-d56e32
rejected a new manifest schema mismatch;214859-3fde75 was superseded after final
narrow note/report checks. Their historical seals were not rewritten.

Validation: full offline suite once,551 tests:532 passed,15 mock socket PermissionError
errors from sandbox,4 optional real-compiler skips; no assertion failures. Final
focused editorial suite33/33 after the final reporting/classification edits.
AST/shell syntax, git diff --check, actual request/source/target/adoption comparisons
and saved-evidence seals passed. No inference, paid requests, service operations,
installation, OCR or Git mutations. AGENTS and unrelated working changes preserved.
Exact changed files/checks: docs/evidence/editorial-production-20261028.md.

Next operator action:
`cd /home/mdi/projects/pdf-to-latex && bash scripts/run-editorial-chapters.sh run`
The integrated wrapper runs full normal-terminal tests once per code/test identity,
checks existing exact regular GLM and workload ownership, starts persistent tmux,
captures fresh readiness automatically, and dispatches only the planned stage.
It never switches services. Runbook: docs/EDITORIAL-CHAPTERS.md; status/pause/resume/
bundle need no remembered shell variables. Live model/streaming and new compilation
remain untested by this offline task. Serving upgrades/joint verification stay deferred.


## 2026-10-29 — Saved output repairs and remaining Bergomi continuation (PREPARED)

Followed the 29 October repairs/continuation task; articles/library/corpus work is
explicitly deferred. Original checkpoint: runs/editorial-chapters-trial-20261028T215454Z-8ef98f,
status stage_finished_for_inspection / after_bergomi_first_chapter_pair. Its supplied
final inspection ZIP hash matches 9cfda146ff2c9ab025b6cea19fa34c8554a6a23cf5f0e5592a71b858f58dbadc.
64 calls plus24 earlier calls, no uncertain in-progress request; project/run locks
free and no converter active. Operator's previous normal-terminal test log passed
551 tests with4 optional skips. No newer Bergomi model outputs were found.

New linked run: runs/editorial-chapters-trial-20261029T103643Z-713678.
PREPARED ONLY, zero new inference calls. All88 consumed calls, source/input seals,
original drafts, compiler records and parent state/binding hashes retained/verified.
Stale pending u040/u041 explicitly adopt completed u330/u331 (calls063/064). The
full Chapter1 source/context identities match and the completed conversion request
matches the current transport body exactly. Unrelated code changes do not cause
regeneration. New binding admits132 remaining conversion/critic pairs, no Chapter1
replay, all in source order from u042/bergomi-02-s01 (PDF42–44) through bibliography.
High conversion / max immediate criticism,131072 per request, streaming and absent
sampling overrides preserved. One attempt per scheduled task; isolated failures
leave gaps and independent work continues. No overall call ceiling (calls=null),
no generation/overall deadline,10-second connection timeout, no automatic replay
of uncertain calls.88 calls remain historical accounting, not a launch limit.
The old98-call preparation stays sealed historical evidence. Checkpoints assemble
at chapter boundaries and final completion; manual pause/resume/stop retained.

Offline cached-input preflight:520 owned pages,8102 recognized blocks,133 distinct
units including reused Chapter1. Remaining132 targets own6650 blocks uniquely.
Nine blank notices and118 native-renderer fallbacks preserved, not independently
certified. Both extractions plus full chapter context are present in all132 saved
conversion requests. Actual body/preview comparisons passed; conservative combined
byte/template/output estimates150602–789514 fit recorded1048576 capacity. These are
not exact tokenizer counts. Live capacity and each future critic draft/notes are
checked before dispatch; no clipping. Units coverPDF18–519; supplementsPDF1–17 and520
retain original images and native TeX/text/maps/assets. PrefacePDF16–17 and other
front matter still lack a reviewed typeset TeX view; no whole-book fidelity claim.

New saved derivatives, no model calls:
- Gatheral Volatility Swaps gatheral-11-s02-part05 uses clean critic-call-050 with
  amsfonts added for mathbb and its inline-math closer repaired. Mathematics and
  Figure11.1 asset unchanged; the appended duplicate raw Markdown notes are not
  selected again. Original versions remain.
- Bergomi Chapter1 uses critic-call-064 with both incorrect variance-note
  parentheses corrected to2*sigma_hat^4/N^3 when the original prefactor multiplies
  an averaged sum. Var(sum z_i^2)=2N; local algebra independently checked and
  explicitly attributed to Codex. Main displayed estimator/variance unchanged.
  Empty/header/umbrella log entries remain historical rather than open findings.
- Metadata-only escaping removes control characters from generated navigation
  TeX by displaying explicit control labels. Raw titles/native mathematics remain
  unchanged. Seven source-derived task titles contain the observed control artifacts.
- Note parser separates explicit disposition fields, heading/separator furniture,
  applied claims and unresolved issues; exact abbreviated references reconcile
  without granting independent verification. Current saved logs reference their
  original history. Gatheral jump/convention/Lewis and Bergomi gamma/footnote/image
  questions remain open; no speculative global sign changes.
- No undefined/duplicate TeX labels or missing referenced assets found in selected
  documents. Literal locators are not thereby verified. Existing headings for
  Bergomi2.2.2,2.8,3.1.4 confirmed atPDF46/b6,96/b5,124/b8; the gamma issue remains.

The new masters explicitly distinguish retained content, included PDFs, compilation,
model-review status and per-finding independent checks. No placeholder is delivered
content. Gatheral has34 retained parts,33 unchanged compiled PDFs, one repaired part
awaiting compilation. Bergomi has its full Chapter1 retained, corrected-note version
awaiting compilation,132 missing outputs. Both new masters await compilation here.
Docker API and tmux socket access were denied; no permission change or repeated
probe. The operator launcher uses the existing qualified immutable compiler image
sha256:b9505ed9122f83fd4bb4ae2ab79a1a7ad82187ca712fda0e8868e4e374296211,
compiles saved repairs separately from inference, then runs the admitted schedule.
No compilation success claimed for these repaired versions. Previous compiled PDFs
remain available as explicitly older versions.

Prepared editable masters:
- runs/editorial-chapters-trial-20261029T103643Z-713678/editions/gatheral-1793270210665074077/master.tex
- runs/editorial-chapters-trial-20261029T103643Z-713678/editions/bergomi-1793270211271047422/master.tex
Each includes editable chapters/assets, current accuracy logs and coverage. Exact
repair records/diffs are under versions/<key>/codex-saved-repair-20261029/ and
saved-repair-record.json. Gatheral normalized bibliography retained; it is not
mislabelled as Bergomi's bibliography. Source supplements and raw metadata retained.
Report: runs/editorial-chapters-trial-20261029T103643Z-713678/report.html.
Inspection ZIP: results/editorial-chapters-inspection-20261029T103643Z-713678-1793270641823459579.zip
(30,654,593 bytes; includes validation evidence). Log after launch:
runs/editorial-chapters-trial-20261029T103643Z-713678/terminal.log.
An incomplete preliminary preparation,103501Z-b37eca, is preserved as preparation_failed:
it expected a supplement provenance.json that the actual cache records instead in
native.json/secondary.json. It is not selected by the launcher; no calls were made.

Validation: full suite once,562 tests:542 passed,15 sandbox socket PermissionError
errors, one new test-fixture double-lock error,4 optional compiler skips. Fixed that
fixture to use distinct project/run directories. Final focused suite66 tests:
65 passed,1 optional compiler skip. No remaining observed application assertion
failure. AST, shell syntax, git diff --check, actual preparation/request/ownership
checks, ZIP integrity and saved seals passed. No inference, OCR, service operation,
installation, cloud credential access or Git mutation. Full normal-terminal suite
runs once automatically before launch, not before every chapter. The real compiler,
current both-node workload/memory/service checks and live generation remain operator
checks, not claimed by offline mocks. Detailed changes: docs/evidence/editorial-delivery-20261029.md.

Next operator command:
`cd /home/mdi/projects/pdf-to-latex && bash scripts/run-editorial-chapters.sh run`
It checks exact existing glm53-regular/idle health and both-node GPU ownership,
counts actual available memory including desktop usage, captures readiness, and
launches persistent tmux editorial-chapters. Unknown GPU processes stay blocking;
owned GLM processes are established by container PID membership, never a blanket
Python exemption. It never operates model services. Status/pause/resume/bundle need
no manual paths or remembered shell variables. See docs/EDITORIAL-CHAPTERS.md.
Once launched, leave this checkout/bound inputs unchanged; a later library task
must use an independent development copy and honor project/run .probe.lock.

### 2026-10-29 — concurrency-only linked production handover (offline preparation)

Discovered the authoritative pointer at editorial-chapters-trial-20261029T103643Z-713678,
with project/run locks held and call100 active. Requested the existing safe pause;
its conversion finished normally (608.054s) and compiled before both locks released.
Final handover includes17 completed conversions,16 revised critics,2 complete final
answers without documents and2 unavailable dependent critics. Pending:113 conversions,
114 critics. First eligible work is the critic for Bergomi3-s01; it must not be
converted again. All100 calls plus24 earlier calls, failed attempts, drafts, source
hashes, compiler/image bindings and original evidence remain unchanged.

Bergomi2-s10 is explained by saved call083: normal stop,261.771s,158623 prompt/12355
completion/1 reasoning tokens, but an analysis/fragment final answer without a complete
LaTeX document. Its critic has no reserved call and is unavailable because there is
no complete conversion. It was not a silently failed critic. Bergomi2-s07 remains the
other conversion gap. Selected Bergomi18 parts include14 passing compiler records,
3 syntax failures and1 missing-context/macro failure; Gatheral34 selected parts pass
compilation. These existing issues are not fixed/retried by concurrency-only work.

Independent development: /tmp/pdf-to-latex-concurrency-development-20261029, ordinary
copies of current source/tests/docs, no .git/env/model/book/raw-run copies. Imports
verified there. Integration requires free locks and exact destination starting hashes.
New linked run: runs/editorial-chapters-trial-20261029T153847Z-0c89a4 (prepared, not running). One coordinator owns state,
call numbers and validation/compilation; isolated HTTP workers stream independently.
First4 pending production requests at max2, then up to8 at max4 if operational/resource
checks support it, then remaining queue at the highest qualified level. Critic
priority/dependency, pause-and-drain, no uncertain replay, single-attempt quarantine,
continued history and unlimited overall local-call accounting remain. No prompts,
sources, boundaries, grouping, effort, sampling, output allowance or compiler policy
changes. No overall/generation deadline. Connection-establishment timeout10s retained.

35 actual stage requests inspected:19 High conversions7067.706 summed request seconds,
16 Max critics7693.997s. Per-call effort, token/reasoning/finish/prefill/decode metrics
are in handover-audit.json. Compiler elapsed time is unrecorded, not zero. Saved
health advertised4 slots,1048576 context and2015232 shared pool; kept cache is evictable
per local source. Concurrent reservation uses full conservative prompt+output bounds
against90% of actual pool and minimum2GiB unadjusted MemAvailable per node. Runtime
build/weights metadata and live memory must be captured at launch: Docker access
was denied here. No services or model requests were performed; no permission change.
Four-way pressure or worse operational usable-token batch throughput drains to two;
shared integrity/identity/server faults stop admission and drain. Different requests
are not a controlled two-versus-four benchmark; neither compilation nor critique
proves mathematical correctness. The12-hour aim is not a termination rule.

Complete six-step roadmap retained in docs/EDITORIAL-CHAPTERS.md:1 concurrency
implemented/offline tested/prepared, live qualification pending;2 contiguous untouched
recap grouping deferred (current heuristic46 units/74602 chars/8 chapters out of113
pending conversions/1267535 chars, source validation required);3 saved-draft High
critic comparison deferred;4 one simple native-text Klebaner/Open-WebUI-style Chapter4
comparison deferred;5 Low→High, edit-only critic and deterministic MinerU alternatives
separately deferred;6 pinned runtime comparison deferred with actual-build rollback.
Each has evidence, next action and acceptance conditions. None is automatically enabled.

Checks: full suite once in development copy576 tests:549 passed,15 sandbox-denied
loopback socket errors,12 skips (4 compiler,8 optional historical evidence not copied).
No assertion failures. Focused scheduler/transport regressions passed. Prior normal
operator suite562/OK,4 skips,216.559s is preserved separately. Live parallel serving,
current runtime capture, resource behavior and new real compiler execution remain
operator checks. Source/actual pending request equality and selected copy-back checks
recorded with the linked handover. Every project change remains unstaged.

Next: cd /home/mdi/projects/pdf-to-latex && bash scripts/run-editorial-chapters.sh run
The wrapper checks current service/workload identity, runs missing full checks once,
captures readiness and persists in tmux; it never restarts services. status is read-only;
pause drains; resume retains outcomes; bundle requires a released writer lock.


### 2026-10-29 — interrupted concurrency pilot: ownership race repaired offline

Authoritative pointer/locks and saved records inspected; no project writer active.
Original run editorial-chapters-trial-20261029T153847Z-0c89a4 is stopped_error.
Call102 (Bergomi3-s01 critic) and103 (3-s02 conversion) both finished stop, were
saved and compiled. Both remain selected; no replay. Its trial.status=running is
stale; the linked interpretation is interrupted. The original snapshot is unchanged.

Cause: last saved health at16:14:36.438UTC had2 running/2 decoding and2 local calls.
After call102 completed16:14:46.619 and was finalized, the coordinator removed it,
then room() compared that cached2 against len(jobs)=1. No new health sample followed.
The first stop event was not timestamped: reconstructed after finalization around
16:14:48, before the15-second cache expired; terminal error printed only after call103
finished16:32:29.847 and finalization ended16:32:32.506. No sampled contemporaneous
excess count. Docker log inspection was sandbox-denied; no independent claim that
all external work was absent. Exact source, sample and response references are in
docs/evidence/editorial-ownership-repair-20261029.md and new ownership-diagnosis.json.

Fix: invalidate sampled health on completion collection; bind its ownership check
to its contemporaneous call set. Fresh excess activity still stops admission/drains.
First-stop diagnostic now saves timestamp, raw counts, sample evidence, local call
and task IDs, completion transitions. Terminal pilot records become interrupted.
New sealed concurrency-v2 policy caps all dispatch at2; no automatic four-slot stage.
Qualification requires operational completion/output/binding/resource evidence;
reasoning-token volume is not a qualification criterion. Per-request settings,
sources, section grouping, High/Max,131072 output, stream capture, compiler handling,
unlimited overall local accounting and no overall/generation deadline unchanged.

Performance: call1021036.424s,92821 prompt/39870 completion/22973 reasoning/16897 other;
call1032097.331s,68750 prompt/92657 completion/81284 reasoning/11373 other. Both stop.
Pilot active batch2104.630s,2/4 requests completed.28270 other-completion tokens
(~13.43 per active batch second),104257 reasoning tokens; sums of overlapping request
durations/rates are not wall throughput. No matched serial speedup or accuracy claim.
Sampled minima11.70GiB head/13.13GiB peer, no recorded pressure; sampling ends atguard,
so drain-period resource behavior remains unknown. Two streams observed, pilot still
unqualified. Existing immutable runtime/source/template binding retained and checked
on resume; runtime was not upgraded or reconfigured.

New prepared linked run: runs/editorial-chapters-trial-20261029T165410Z-1f2179.
Report: same directory/report.html; diagnosis: ownership-diagnosis.md/json;
operational report: concurrency-report.md/json. Log after launch: terminal.log.
All103 calls plus24 earlier calls, successful versions, failed outcomes and pilot
call IDs/2104.630s preserved. All10313 parent files checked byte-for-byte unchanged.
All225 pending task comparisons unchanged:113 concrete request bodies plus112
identical draft dependencies. Actual remainder112 conversions/113critics; first
critic3-s02, conversion3-s03. Two more requests finish the existing sample; if
operational checks pass, continue queue atmax2. Existing2-s07/2-s10 gaps retained.
No new model calls or compiler workload were executed. All changes remain unstaged.

Final full offline suite:581 tests/245.495s:562passed,15 sandbox loopback bind
PermissionErrors,4optional real compiler skips; zero assertion failures. All19
concurrency/transport/linked-history regressions passed. AST, shell syntax and
whitespace checks passed. Prior operator576-test suite passed in222.579s with4skips;
that result is preserved, not attributed to this repair. New live parallel serving,
Docker logs and new real compilation remain normal-terminal checks.

Next: cd /home/mdi/projects/pdf-to-latex && bash scripts/run-editorial-chapters.sh run
Existing wrapper runs required normal-terminal tests once, verifies existing regular
GLM/idle health/workloads and ownership, captures readiness, starts persistent tmux.
It never changes services. status/pause/resume/bundle use the same wrapper. Current
preparation is NOT RUNNING. Six-item roadmap remains documented; four-way admission
and every later optimization remain deferred pending explicit inspection/decision.
Changed files: probe/chapter_concurrency.py, scripts/editorial_chapters.py,
tests/test_chapter_concurrency.py, docs/EDITORIAL-CHAPTERS.md, docs/PROJECT-STATE.md,
docs/evidence/editorial-ownership-repair-20261029.md.
Inspection ZIP (integrity checked; interrupted pilot state included):
results/editorial-chapters-inspection-20261029T165410Z-1f2179-1793293195407470192.zip.


### 2026-10-29 — authorized implementation Git checkpoint preparation

User explicitly authorized staging/commit/push for this checkpoint only; ordinary
AGENTS.md rules are not amended. Reviewed all accumulated relevant tracked changes
and untracked code/tests/scripts/docs/licence since7b62030324ac8148c3e14478b0914b83f00bb534.
Exact selection and limits: docs/CHECKPOINT-20261029.md. No application/request edits.
Read-only current run165410Z-1f2179 is paused at concurrent_production,113 calls,
no active call, both locks free; two-slot sample recorded qualified, max2. No job or
service was interrupted. Mathematical fidelity is not established by that status.
Current code/test identity matches the operator's581-test passing suite (222.354s,
4optional skips). Reused it; syntax/JSON/shell checks and tracked/untracked whitespace
checks pass. Selected-file credential-pattern scan found no matches; no key read.
One interdependent implementation checkpoint is appropriate. All raw source books,
runs/results, environments/models/private settings and the old root task text remain
local. Configured remote origin is git@github.com:canary-droid/pdf-to-latex.git,
branch main/upstream origin/main; live remote query failed DNS resolution. Git
operation outcomes are retained separately in the ignored checkpoint preparation;
this entry does not claim a commit or successful push.

Checkpoint staging attempt was denied: .git/index.lock read-only filesystem.
No staging, commit or push occurred. Live remote DNS resolution is also blocked.
Prepared136 explicit paths and a normal-terminal completion command under ignored
results/checkpoint-20261029. It refuses changed source hashes, wrong branch/remote
or remote divergence; it uses no force, fetch/reconciliation or branch switching.
The user can run: bash results/checkpoint-20261029/finish.sh from project root.


### 2026-10-29 — separate bounded five-stage speed suite, prepared offline

User completed the preceding checkpoint. Read-only HEAD is
08a452d88f0a18875fac2f2eec64df84b4849e39, main tracking origin/main. Initial tree had
only the unrelated untracked pdf-to-latex-codex-next-step.txt; preserved. No Git
metadata operation, service operation, OCR, model call, paid request or credential
read was performed for this task. All new changes remain unstaged.

Authoritative production pointer still selects
runs/editorial-chapters-trial-20261029T165410Z-1f2179. State paused,113 calls plus24
earlier calls, no in-progress reservation, project/run locks released. Calls112 and
113 both completed normally and compiled; final drain ended18:20:54 UTC. The saved
17:59:27 pause diagnostic incorrectly said streams had already drained. Historical
evidence is unchanged; new reporting says draining until requests/finalization
finish and writer ownership is released. The264 admitted production tasks have22
completed conversions,22 completed critics, two unusable-document conversions and
two unavailable critics,108 pending conversions/108 pending critics. No completed
conversion currently awaits criticism.2-s10 call083 has finish_reason stop and37,323
final characters, but the document parser records an ambiguous surrounded fence;
the critic was never dispatched because no eligible complete draft was selected.
That raw response and the2-s07/2-s10 production gaps remain intact.

Historical two-slot evidence102/103/105/106:4 usable outputs,3,662.3495 active batch
seconds across two sessions,218,533 completion tokens =177,142 reasoning +41,391
other completion tokens. No matched serial speedup or source accuracy is inferred.
The paused production pointer was not redirected to this experiment.

Implemented one separate finite suite coordinator reusing the existing streaming
HTTP client, reservation allocator, ownership-race repair, resource admission,
document/accuracy-version handling, isolated compiler and writer locks. Production
max2/no-overall-call-limit behavior is retained. Explicit suite-only fixed levels
admit up to4 in Stage1 and a frozen reference2 (or common serial if unavailable)
in Stages2–5. No stage overlap, new target refill, hidden repair, completed-work
replay, service switch or book continuation. One attempt per frozen work ID,23 total
maximum; readiness separate, once per actual launch/resume. Terminal run/resume is
zero inference including readiness. Shared identity/integrity/ownership, memory and
HTTP/connection faults stop admission and retain/drain owned responses. Local
content failures leave their dependent critics unavailable and independent stages
can proceed. No wall-clock/generation deadlines; connection establishment10s.

Frozen stages:
1. Four pending Bergomi sections4-s03 PDF157–167,5-s01 168–169,6-s01 218–219,
   6-s06 223–230 with own critics:8 calls, production High/Max bodies unchanged.
2. Adjacent digest groups2-s11+s12 PDF113 and2-s15+s16 PDF116–117:4 High/Max calls;
   saved individual controls084–087,092–095. Headings/repetitions/blocks retained.
3. High critics on exact historical input drafts for Bergomi4-s01,4-s02 and pilot
   Gatheral7-s05:3 calls; only effort differs from Max112/113/037.
4. Complete Klebaner4, original PDF106–136 / selected1–31, dual versus native-only
   text with identical asset locators, same short prompt and focused Max critic:
   4 calls. No Chapter5, image API, markers, sentinels, JSON or answer key.
5. Low conversions of Bergomi4-s01/4-s02 with Max critics:4 calls; exact High
   conversion controls110/111 and Max112/113. Installed Low support must verify;
   otherwise skip, never substitute none or change runtime.

Actual preparation: runs/speed-suite-20261029T191756Z-3933e0.
Report: same directory/report.html and report.md; manifest:suite-manifest.json;
compact ZIP path:last-inspection.json. Separate pointer:results/speed-suite-current.json.
Only offline preparation; zero new generations. Earlier unlaunched preparation
validation artifacts remain local; the operator pointer selects only the final one.
Both sources, exact controls, assets and target/context ownership were exercised
against actual saved records.13 concrete bodies fit the recorded1,048,576 context
window with conservative byte-based bounds204,766–600,310 including full131,072
output and4,096 template margin; no clipping. Ten dependent critics bind their own
future draft, exact notes, sources and template and receive a fresh budget check.
Four initial conversion reservations total1,180,532 versus the last recorded90%
pool budget1,813,708; live both-node capacity/memory still must be checked.
The cached template hash41cff9af7b3a86c96751b107a8444f245fbda0bd5320b636a5bb1f7f4ba1a5c3
matches saved serving metadata and explicitly names Low. Controller Jinja2 is absent;
no dependency installed. The normal-terminal launcher evaluates installed request
mapping/template rendering read-only in the existing container before Stage5.

Bounded independent Codex source checks are recorded in
docs/evidence/bounded-speed-suite-source-checks-20261029.md and source-checks/ in the
preparation. Four selected pages: Bergomi113,151,154 and Gatheral128. Confirmed the
adjacent recap statements, printed missing square in the volatility drift, the
terminal-density/local PDE evidence, and the printed J(3) brace tending to3. The
saved Max beta0-divergence assertion is not independently established without J(2).
No new experiment output exists to score; source checks/diagnoses are outside model
requests and are not whole-page/book certification. No production correction adopted.

Pending grouping opportunities were recalculated without changing production:
44 untouched apparent recap targets,69,641 native characters across seven chapters.
Classification/adjacency/source preservation must be checked before later production
grouping. All six roadmap items remain in docs/BOUNDED-SPEED-SUITE.md: concurrency,
grouping, High critic, simple native/dual chapter, Low conversion (edit-only criticism
and deterministic MinerU correction still deferred), then separately pinned runtime
trials with rollback. No stage winner changes other arms or automatically resumes
either book. Planning ranges total roughly2–16h with large uncertainty, particularly
the whole-chapter arm; estimates are not execution cutoffs or whole-book promises.

Validation:604-test full offline suite once,217.705s:585 passed,15 sandbox-denied
mock-loopback binds,4 optional real compiler skips; zero assertion failures. All23
new suite tests and19 existing concurrency tests passed. Exact selected evidence
hashes, body equality/effort-only differences, assets and source mapping passed.
AST/shell syntax and git diff --check passed. Actual new serving concurrency, live
readiness/capacity/Low rendering and new Docker compilation were not performed.
The one operator launcher runs remaining normal-terminal tests once per code/test
identity, then read-only workload/alias checks, automatic readiness and tmux.

Next: cd /home/mdi/projects/pdf-to-latex && bash scripts/run-speed-suite.sh run
Session:pdf-speed-suite. Same wrapper:status/pause/resume/bundle (stop explicitly
preserves partial streams). Actual log:the prepared run/terminal.log after launch.
After Stage5 it saves report/inspection ZIP, releases ownership and exits. The live
operator wrapper/worker copies concise diagnostic files to /home/mdi/Downloads;
Codex offline output stays within project/results and /tmp. Production resumption
later requires a separately authorized linked preparation for changed code.

Files changed:probe/chapter_concurrency.py,probe/chapter_glm.py,
scripts/editorial_chapters.py; new probe/speed_suite.py,scripts/speed_suite.py,
scripts/run-speed-suite.sh,tests/test_speed_suite.py,docs/BOUNDED-SPEED-SUITE.md,
docs/evidence/bounded-speed-suite-source-checks-20261029.md; updated
docs/EDITORIAL-CHAPTERS.md and docs/PROJECT-STATE.md. AGENTS.md unchanged.

### 29 October 2026 — finite overnight suite prepared; no inference launched

Read the new overnight task and rediscovered actual pointers/locks. Finished suite
`runs/speed-suite-20261029T191756Z-3933e0` is suite_finished_for_inspection:
20 calls (19 work +1 readiness),18 normal work responses, Max009 truncated,
four Low tasks skipped. No in-progress reservation. Production remains paused at
`runs/editorial-chapters-trial-20261029T165410Z-1f2179`:113 calls +24 earlier calls;
admitted scope22 completed conversions/22 critics,2 unusable conversions with
unavailable critics,216 pending tasks. Both run locks and the root writer lock free;
no actual worker found. Original pointers, state, sealed calls, controls and book
sources were preserved. No service/API/credential access or inference during work.

New linked preparation (PREPARED, NOT RUNNING):
`runs/overnight-suite-20261029T233239Z-708fe8`.
Separate pointer `results/overnight-suite-current.json`.
Report: same directory/report.html; exact table:frozen-selection.md;
manifest:suite-manifest.json; offline-validation.json records checks.
Inspection ZIP:
`results/speed-suite-inspection-overnight-suite-20261029T233239Z-708fe8-1793317056212025643.zip`
(15,044,649 bytes at preparation). Earlier unlaunched development preparations
are retained; preparation-lineage.json identifies the superseded one. No old
bindings were patched or resealed. Existing code-bound production needs its usual
explicit linked preparation before future resume, not a forced old-code match.

Extended the existing finite-suite coordinator/manifest, not another scheduler.
New protocol freezes44 work IDs: A six High critics on exact historical Max input
(only effort changed); B the two unchanged skipped Low inputs with own Max critics;
C four new adjacent digest groups from chapters5/7/8/9; D thirteen coherent larger
Bergomi units, High conversion/Max critic, source pages170–212,234–317,324–368,
374–403,408–435,438–466,470–510. Source scope is explicit target blocks; shared
boundary pages/whole parent context do not count twice.4,314 distinct target blocks
across C/D. No overlap with the earlier successful pending-unit experiments.
No adoption, completed conversion replay, fill-in targets, hidden retries or
production fall-through. One attempt per frozen request; readiness once per genuine
launch/resume, no model calls after terminal completion. All stages use at most2;
no four-slot arm, model/runtime/sampling changes or global production ceilings.

D retains simple chapter-style instructions, full native MinerU target, native PDF
pages, complete parent dual-source context and existing local references. No answer
keys or new diagnoses are injected.25 concrete requests fit recorded1,048,576 context
under full UTF-8 JSON +4,096 template margin +131,072 output (254,478–888,223).
No tokenizer installed/clipping.19 dependent critics check their exact new drafts
and full context at dispatch. Unfit requests become explicit gaps without splitting.
Two-slot central planning estimate~9.8h before extra compiler/admission overhead;
broad6.4–29.5h range, not a deadline. Updated within-stage ranges avoid extrapolating
recap timing to large work. No overall/generation timeout; connection timeout10s.
First two larger pairs yield a nonblocking diagnostic; independent work continues.

Reporting now associates each row with versions produced by its own call. A failed
critic cannot inherit its conversion's compilation; findings-only reviews do not
claim a returned/applied replacement. Historical corrected reporting is NEW under
historical-report/version-specific-results.json. Original old reports remain as
recorded. Raw findings, annotations and actual replacements stay distinguishable;
arbitrary suggested prose is never spliced automatically.

Separate offline-repairs contain original/repaired TeX and diffs for tag4.14
(outside aligned, no mathematical change), Bergomi4-s01's explanatory volga divisor
(d1_sigma=-d2/sigma, hence vega*d1*d2/sigma), and Lewis beta0 qualification (J2 absent;
J3/beta2 source inconsistency retained). These are Codex-attributed, never new
benchmark inputs. Both historical Max and High had the volga error. Existing
qualified compiler image b9505ed9122f83fd4bb4ae2ab79a1a7ad82187ca712fda0e8868e4e374296211
is retained; real compilation is pending operator access. One read-only Docker
inspection was denied at docker.sock; no permission change/repeated probe.
The launcher compiles saved repairs before readiness without model regeneration.

Low's old failure was the probe's Jinja environment (unknown break tag), not proof
of unsupported Low. The new read-only probe discovers installed serving Jinja
options/extensions (prefers cuda/chat_template.py) or verified delegated rendering;
records renderer/mapping/template hashes and Low/High/Max labels. Distinguishes
supported, unsupported and probe_error. Live installed rendering remains untested
in this sandbox; only Low stage skips on probe_error, never substitutes none.

Bounded source inspection: Bergomi151/155 confirmed source missing square and
(4.14) structure;212/317/368/403 confirmed selected recap classification and visible
mathematical conditions. Klebaner122/131 confirmed2delta bound and printed erroneous
Var(Z²)=3. Dual017/Max019 retain3; native018/Max020 correct to2. Compilation/normal
finish therefore does not establish correctness. Lewis128 J3 evidence from earlier
inspection reused with explicit beta0 limitation. Full source checks and references
are in docs/evidence/overnight-source-checks-20261029.md. New outputs have no source
assessment yet; compact pack provides representative images/locators for later work.

Validation at final code/test identity:617 tests in217.464s;598passed;15errors all
PermissionError at mock loopback socket creation;4 opt-in real compiler skips;
zero assertion failures. All13 new overnight,23 existing finite-suite and19 existing
concurrency tests passed. Exact controls/draft hashes, full body effort-only deltas,
new span uniqueness, both sources, budgets and consumed original file hashes checked.
AST (including installed probe program), Bash syntax and git diff --check passed.
Normal-terminal full suite is mandatory once per new code/test identity and is
included in the launcher. New model behavior/streaming, actual template rendering,
real Docker repair compilation and output fidelity remain untested here.

Next single command:
`cd /home/mdi/projects/pdf-to-latex && bash scripts/run-overnight-suite.sh run`
Persistent session:pdf-overnight-suite. Same wrapper:status/pause/resume/bundle.
Readiness and actual paths are automatic. Progress file written by operator only:
`/home/mdi/Downloads/overnight-suite-20261029T233239Z-708fe8-progress.json`.
Pause drains requests/finalization then releases locks; final completion bundles and
exits, leaving GLM serving. No production resumption. Full roadmap retained in
OVERNIGHT-WORKFLOW-SUITE.md: later four-slot matched test if useful, High qualification,
coherent grouping/larger units, Low, deferred edit-only/deterministic routes, and
separate pinned runtime/model updates with rollback.

Files edited in this task:probe/speed_suite.py,probe/chapter_concurrency.py,
scripts/speed_suite.py,docs/BOUNDED-SPEED-SUITE.md,docs/EDITORIAL-CHAPTERS.md,
docs/PROJECT-STATE.md. New:scripts/overnight_suite.py,scripts/run-overnight-suite.sh,
tests/test_overnight_suite.py,docs/OVERNIGHT-WORKFLOW-SUITE.md,
docs/evidence/overnight-source-checks-20261029.md. Earlier unrelated/uncommitted
changes preserved. AGENTS.md unchanged; all changes unstaged; no Git mutations.

## 30 October 2026 — overnight finalization/probe repair; continuation PREPARED

Read the complete `Codex-repair-overnight-suite-20261030.txt` task. Read-only
inspection found the actual overnight pointer still at
`runs/overnight-suite-20261029T233239Z-708fe8`, status `stopped_error`, writer released
at 00:16:13 UTC. Project, suite and paused-production locks were free; no active
suite/editorial/MinerU writer was found. Ordinary production remains paused at
`runs/editorial-chapters-trial-20261029T165410Z-1f2179`.

All seven calls (one readiness and six High critics) returned HTTP 200, exact
`glm53-regular`, finish_reason `stop`. Five complete replacements have passing
compiler records; all three separate offline repairs also compiled. Call-005
completed at 00:12:34 UTC with findings and an explicit statement that no revised
document was needed. Its raw answer and original/annotated versions survive.
The last call-007 completed at 00:16:11 and was finalized before writer release.
No model response needs replaying. The saved normal-terminal log reports **617
tests, OK (skipped=4), 223.707 seconds** for the earlier implementation.

Two concrete defects were repaired:

- `finish_task` treated the non-None prose returned by envelope extraction as a
  document at compilation time, despite correctly declining to register a
  replacement earlier. Creation and compilation now share the explicit
  recorded-replacement invariant; retained/annotated versions use their actual
  registry identity. Partial/ambiguous document attempts remain unusable. No
  broad KeyError suppression, invented replacement, or suggested edit application.
- The separate Low probe tried `inspect.getfile` on Transformers' cached helper
  and raised `TypeError ... _lru_cache_wrapper`. It now inspects/hashes
  `inspect.unwrap(helper)` while rendering with the actual installed cached
  callable. Installed mapping/template/High/Max identity checks remain enforced.
  Unverifiable Low skips only B; identity mismatch stops the suite.

New linked continuation:
`runs/overnight-suite-20261030T085252Z-fae4ce` — **PREPARED, NOT RUNNING**.
The frozen manifest is byte-identical to the parent; all seven call records and
sealed request/output files are inherited unchanged. Prepared source, targets,
grouping, prompts, settings, output allowance, runtime/compiler bindings and
coverage remain unchanged. Parent snapshot and independent copied evidence hashes
were checked. Original run state, responses, notes and sealed artifacts were not
rewritten. `continuation-lineage.json` records implementation changes and ancestry;
`historical-run/` retains the failed state/diagnostic and old implementation binding.

`local-recovery/call-005.json` records a verified, idempotent offline recovery of
the already-written notes and annotation. It preserves the historical
`coordinator_failure` separately and marks the new task `critic_unchanged`, with
no model replacement and no suggestions applied. Existing immutable version paths
were not replayed or overwritten. The annotation itself still requires compilation
at operator launch; its original draft remains byte-identical. Findings-only and
compilation do not establish mathematical correctness.

Stage A is now `finished_for_inspection` (five revisions, one findings-only result).
Exactly **38** untouched frozen requests remain: B4 (two Low/own-Max pairs, only
if Low verifies), C8 (four recap pairs), D26 (thirteen larger Bergomi pairs).
Readiness is separately recorded once per genuine launch. The next call number
follows the seven consumed calls; no reset/refill. At most two requests, one
attempt per frozen task, 131072 output allowance, no overall/generation deadline,
10-second connection timeout, final stop after D. No production adoption or
fall-through. Terminal run/resume still makes zero calls.

Future coordinator/finalization failures retain full tracebacks outside HTTP
seals in `diagnostics/`, with cause/path in task/state/progress and terminal output.
The small uploadable progress JSON now references the latest bundle after bundling,
including the copy inside the ZIP. New report/log are respectively
`runs/overnight-suite-20261030T085252Z-fae4ce/report.html` and `terminal.log` (created
at launch). `last-inspection.json` points to the actual compact ZIP.

Validation: seven new focused tests passed, including the exact saved call-005
answer, fenced findings, partial/complete/ambiguous TeX, unchanged original bytes,
idempotent partial-finalization recovery and tamper rejection, all six real saved
responses through real finalization with compilation stubbed, the actual cached
function fallback branch, real threaded coordinator traversal of the remaining
38 fake requests with dependencies/accounting and terminal no-op, complete error
tracebacks, and ZIP progress refresh. The full suite ran once at the final code
state: **624 tests in 218.137 seconds; 605 passed, 15 errors, four skipped; zero
assertion failures**. Every error was `test_local_model` failing to create its
mock loopback socket with `PermissionError: [Errno 1] Operation not permitted`.
Four optional real-compiler tests were skipped. Python syntax, wrapper syntax and
`git diff --check` passed. Details/log are in the new run's `repair-validation.json`
and `repair-offline-tests.log`; the copied `offline-validation.json` is historical.

A single read-only attempt to execute the installed effort-rendering probe was
denied at `/var/run/docker.sock`. No permission changes or repeated attempts.
The launcher performs the repaired installed probe and recovered-annotation
compilation in the normal terminal; neither was claimed successful here. No
inference, service operation, credential access, OCR or paid request occurred.

Next operator command:
`cd /home/mdi/projects/pdf-to-latex && bash scripts/run-overnight-suite.sh run`
It runs outstanding full checks once for the changed code/test identity, checks
the existing regular GLM/workloads, starts persistent tmux `pdf-overnight-suite`,
captures readiness automatically and continues B/C/D only. Same wrapper actions:
`status`, `pause`, `resume`, `bundle`. Pause drains before releasing ownership;
resume skips consumed work. No manual readiness path or service switch.

Files changed in this repair: `scripts/editorial_chapters.py`,
`probe/chapter_concurrency.py`, `probe/speed_suite.py`, `scripts/speed_suite.py`,
`scripts/overnight_suite.py`, `tests/test_overnight_repair.py`,
`tests/fixtures/overnight-findings-only/answer.txt`,
`tests/fixtures/overnight-findings-only/provenance.json`,
`docs/OVERNIGHT-WORKFLOW-SUITE.md`, `docs/PROJECT-STATE.md`.
All unrelated edits preserved; AGENTS unchanged, no Git mutations, everything
unstaged. No new experiment, source-quality audit or production inference started.

## 30 October 2026 — Codex configuration handoff before independent review/supervision

Read the complete controlling task
`/home/mdi/Downloads/Codex-configure-review-and-supervise-20261030.txt`. Its ordered
Phase1 requires a fresh, explicitly configured session before Phases2/3. This
session cannot write the standalone installation or `~/.codex` profile directory;
the sandbox exposes them read-only. No permission relaxation or denied mutation
was attempted. The installed CLI supports the session-local `--no-daemon` route,
so updating/opening the new CLI need not restart the shared daemon.

Read-only snapshot around09:32–09:40UTC: the current pointer still names
`runs/overnight-suite-20261030T085252Z-fae4ce`, state `prepared_offline`; project
writer lock free, run lock absent. Seven inherited calls, five revised critics,
one findings-only critic,38 pending tasks. No worker visible in this sandbox
process namespace. All bound controller file hashes still match the prepared
binding. No run/state/evidence or application code was changed by this phase.

Confirmed CLI0.163.0 at
`/home/mdi/.codex/packages/standalone/releases/0.163.0-aarch64-unknown-linux-musl/bin/codex`;
`codex login status` confirms ChatGPT (no credential contents read or displayed).
Global model/effort remain gpt-6-astra/xhigh, context/compaction unset. Cached and
bundled model metadata advertise272000 default,872000 maximum and95% effective
factor, with xhigh available. The prior active session's observed effective258400
and244800 Total compaction remain the verified runtime values, not800000/650000.
0.165.0/0.166.0 server packages and changing cache-client versions do not prove the
executing host daemon version; its recorded PID is outside this sandbox namespace.
No shared server was restarted. Current public stable will be resolved by the
documented native updater at operator execution, not blindly pinned to0.166.0.

Added `scripts/start-codex-supervision-task.py`: normal-terminal Phase1 helper,
not a supervisor or book launcher. It records executable/version rollback data,
uses `codex update`, checks stable-version syntax and ChatGPT auth, refreshes
account model metadata, then installs only
`~/.codex/pdf-to-latex-supervision.config.toml`. Existing profile bytes/mode are
backed up and unrelated entries retained; base config/auth/permissions unchanged.
Preferred800000 nominal/650000 total compaction, gpt-6-astra/xhigh; supported
default fallback if advertised maximum is smaller. It opens one fresh
`--no-daemon --profile pdf-to-latex-supervision --strict-config` task with the full
task-file path, concise handover and actual setup record automatically supplied.
Requested settings and expected headroom are explicitly unverified until the new
session reads its own runtime evidence. No artificial full-window exercise.

`docs/CODEX-SUPERVISION-HANDOVER-20261030.md` records current evidence, applicable
prior tests, limitations, rollback and the remaining Phase2/3 instructions. The
new session must independently assess the existing repair, implement the narrow
supervisor, run actual disposable Codex-exec qualification, and distinguish
implemented/qualified/armed/running before continuing the frozen suite. No claim
that these remaining phases have already happened; the user explicitly required
this fresh-session boundary. No production queue fall-through is authorized.

Validation: all5 `test_codex_profile_setup.py` checks passed. They verify supported
window/fallback, backup/mode/unrelated-TOML preservation and idempotence, symlink
rejection, preview/API-key refusal, and fresh-task arguments without permission
overrides. Python syntax and `git diff --check` passed. No updater, profile write,
new Codex/model session, GLM call or compiler invocation was executed. No unrelated
full-suite repetition; the new session owns the next review/qualification checks.

This phase changes only the new setup helper/test/handover and
`docs/OVERNIGHT-WORKFLOW-SUITE.md`, `docs/PROJECT-STATE.md`. Every prior repair and
unrelated edit remains unstaged. Next operator command:

`cd /home/mdi/projects/pdf-to-latex && .venv-control/bin/python scripts/start-codex-supervision-task.py`

## 30 October 2026 — fresh-session review and narrow supervision, qualification BLOCKED

This is the requested fresh session, thread
`01a18c70-11f6-7023-b87a-1b389cecd101`. Read the complete consolidated authorization,
the supervision handover, setup record and project instructions. The setup had
already selected stable standalone Codex0.166.0; no installation/update, profile
rewrite, authentication change, shared-daemon restart or historical chat resume
was repeated.

**Phase1 observed runtime:** gpt-6-astra/xhigh, existing ChatGPT authentication,
effective context760000, automatic compaction650000 **Total**. Configured nominal
window800000 is recorded separately. The current catalog still reports
default272000/maximum872000 and95% effective factor. Runtime logs identify the
0.166.0 codex-tui client with an in-process app server, process identity
`pid:1132698:8782f94b-a7d0-4b79-9436-1ac4ebec36e5`. The executing sandbox image's
path/hash matches the selected standalone release. Direct host `/proc/.../exe`
inspection remains outside this PID namespace; no cache or shared-daemon binary
is presented as that missing direct observation. **long_context_exercised=false**;
no padding exercise or model-catalog modification. Sanitized evidence is in
`results/supervision-review-20261030/session-runtime.json`.

Rediscovery before implementation and after validation found the same current run,
`runs/overnight-suite-20261030T085252Z-fae4ce`, status `prepared_offline`. The project
lock is free, the run lock is absent/free, and no worker was launched. Its original
bound code hashes still match both the frozen binding and the initial snapshot.
Seven inherited calls, six completed StageA tasks and38 pending B/C/D tasks are
unchanged. All original responses, proposals, compilations and the failed parent
remain preserved. Ordinary Bergomi production was never launched.

**Phase2 independently checked:** the existing finalizer uses the same actual
registered-replacement invariant for creation and compilation. Findings-only notes
retain the real draft/annotation identity; partial/ambiguous TeX remains unusable.
The effort probe inspects `inspect.unwrap` and renders with the installed cached
callable. No corrective edit to these prior repairs was needed. All7 focused
tests passed, including all6 actual saved StageA responses, the real lru_cache
fixture, byte preservation, partial-finalization idempotence, the actual threaded
fake38-request continuation and terminal no-op. A separate trusted-helper replay
also recovered only `critic-call-005-annotated`, retained `critic_unchanged`, and
rebuilt disposable reports/bundles with zero generation. Compilation remains a
separate outcome, not proof of mathematical correctness.

**Phase3 IMPLEMENTED, NOT QUALIFIED/ARMED/RUNNING.** Added the independent persistent
supervisor, fixed verification helper and programmatic patch policy. The persistent
normal-terminal entry point performs qualification before worker admission. It
binds an explicit frozen suite/continuation lineage; monitors actual process
PID/start/boot/executable/command identity through final bundling, including the
legacy lock-release interval; and keeps pause/disable intent latched across links
and restarts. A pause arriving during repair/application prevents later relaunch.
Disable leaves healthy work alone. Explicit resume can reattach compatible healthy
work after supervision was disabled. Long requests have no new deadline.

Repairs run in separate ordinary copies using the verified Codex executable and
explicit project profile, ChatGPT login, workspace-write sandbox and no interactive
approval prompt. Up to2 attempts per normalized incident are persisted. Candidate
patches are confined to finalization/reporting function bodies and new regression
files; path/symlink/hardlink, AST, existing-test, capability/text/check and baseline
hash checks protect the remaining project and supervisor policy. New regressions
must reproduce the baseline failure and pass with the repair under the sandbox;
fixed existing tests and the actual saved failure are checked independently. No
agent-supplied shell command is executed by the supervisor. Application holds the
project/run/development locks, preserves file modes and rollback snapshots, and
rejects conflicting user edits. Parent snapshots and completed work are retained
in general settled-stage links; terminal reporting repairs remain terminal.
Uncertain reservations, protected failures and unsupported repair scopes block.
See [OVERNIGHT-SUPERVISION.md](OVERNIGHT-SUPERVISION.md) for exact scope and limits.

Validation of the final implementation: **20 focused supervisor tests passed**.
They include actual disposable worker failure/recovery, zero-exit stopped_error,
process identity/loss, detached post-lock finalization, pause during repair,
immediate pause latching, healthy disable/reattach, duplicate ownership, persisted
allowances, unavailable Codex, scope/symlink/conflict rejection, and an actual
linked copy of the saved failure preserving all7 calls,38 pending tasks and prior
successful compilations. Compiler callbacks are explicit stubs in that link test.

The final full suite ran649 tests in226.339s: **630 passed,15 errors,4 skipped,
zero assertion failures**. Every error is `test_local_model` failing to create a
mock loopback socket with `PermissionError: [Errno1] Operation not permitted`.
Four optional real-compiler checks were skipped. These are not claimed passes.
Earlier full logs are retained for the earlier code identities; the later runs
followed actual control/ownership fixes, not repetition against unchanged code.
Python AST parsing, shell syntax and `git diff --check` passed. Final log:
`results/supervision-review-20261030/full-tests.log`. Selected hashes and counts:
`docs/evidence/supervision-review-20261030.json`.

Real qualification was attempted in
`results/overnight-supervision/overnight-suite-20261030T085252Z-fae4ce/qualification-1793358381119538295`.
The disposable fake worker saved2 requests, hit the intended missing-version
failure and exited0. The supervisor detected the saved failure and invoked the
actual installed Codex exec. It exited1 before generating a patch:
`failed to initialize in-process app-server client: Read-only file system (os error30)`.
No mocked Codex reply is presented as real qualification. The consumed attempt is
preserved by the qualification allowance ledger on normal-terminal continuation.
Subsequent offline control hardening does not qualify the final code automatically.

Read-only capability audit: project/controller access works; ChatGPT login status
works; Docker inspection and a harmless actual isolated compilation were denied at
docker.sock; tmux socket access was denied; peer SSH DNS and GLM discovery failed
in the network-restricted sandbox. The compile result is `unavailable`,
`compilation_claim=false`. No Linux group/socket/account defect is inferred from
those messages. The full capability table, distinctions between the restricted
repair agent and fixed normal-terminal supervisor helpers, and minimum actions
are in the supervision runbook. No permission/configuration relaxation was made
or established as necessary. Normal-terminal real repair/resume qualification,
compiler/launcher access, model/runtime verification and full tests remain required.

One operator command completes those checks persistently and only then admits the
already-authorized pending overnight suite:

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-supervised-overnight.sh start --run runs/overnight-suite-20261030T085252Z-fae4ce
```

The same wrapper accepts `status`, `pause`, `resume`, `disable`. Status/progress and
the current qualification blocker are in the bound supervision directory; no
active supervisor/worker is claimed. The production pointer stays untouched.

Files added by this fresh session: `scripts/overnight_supervisor.py`,
`scripts/supervision_policy.py`, `scripts/supervision_checks.py`,
`scripts/run-supervised-overnight.sh`, `tests/test_overnight_supervisor.py`,
`docs/OVERNIGHT-SUPERVISION.md`, `docs/evidence/supervision-review-20261030.json`.
Updated `.gitignore` only for the two new runtime lock files, the existing suite
runbook, the concise supervision handover and this dated state entry. The new
locks remain on disk; no lock was deleted to force progress. All prior unrelated
edits are preserved; AGENTS unchanged; every change is unstaged and no Git
index/history/branch/remote mutation occurred.

## 30 October 2026 — supervisor inspection pack and permissions boundary review

Prepared the requested small independent-review ZIP, named
`pdf-to-latex-supervisor-inspection-20261030T114134Z.zip`, with destination
`/home/mdi/Downloads/`. Its working-tree copy and build/delivery records live in
`results/supervisor-inspection-20261030T114134Z/`. It includes the runbook, exact
implementation and relevant tests, selected qualification/test/compiler evidence,
safe permission/configuration observations, a per-file SHA-256 manifest and the
new `docs/evidence/SUPERVISOR-PERMISSIONS-INSPECTION-20261030.md` report. Credentials,
auth files, whole configurations, environment values, historical chats, source PDFs
and large raw runs are excluded.

The report distinguishes the observed interactive sandbox from the requested but
unobserved repair-child sandbox: real exec failed before a child permission record
existed. It also identifies the host-execution boundary explicitly: fixed
verification helpers import and execute candidate Python outside the repair
sandbox before promotion; existing-test commands also execute that implementation
on the host. Patch-scope/AST filters are not an OS security boundary or proof that
accepted code preserves every constraint. Broad temporary writes, inherited
environment and unverified regression-sandbox resolution are documented. No
permission relaxation is established as necessary; the candidate execution boundary
needs independent review/hardening before being treated as confined.

This packaging task makes no implementation, permission, service, supervisor
control or inference changes. It preserves the previous qualification failure and
test counts rather than rerunning qualification. Validation is archive CRC and
manifest/hash consistency, explicit content allowlisting/secret-pattern screening,
unchanged implementation/run hashes and `git diff --check`. Delivery to Downloads
requires the existing filesystem boundary to authorize only that file copy; it
does not grant any permission to the repair agent. All documentation edits remain
unstaged.

## 30 October 2026 — supervision boundary hardening; qualification-only, UNARMED

Found and read all40 lines/8289 bytes of the explicit authorization at
`/home/mdi/Downloads/Codex-harden-supervision-boundaries-20261030.txt`, then the
current runbook, state and permissions inspection. Its hash is retained in
`docs/evidence/supervision-hardening-20261030.json`. The independent review's
host-execution concerns were confirmed. This task makes no inference, queue,
service, global permission/configuration, Codex installation or Git changes.

The active pointer remains `runs/overnight-suite-20261030T085252Z-fae4ce`,
`prepared_offline`:7 recorded calls and38 pending requests. Original controller
bindings, state and both suite/production pointers remain unchanged. Initial
read-only writer inspection found free project/run locks and no recorded
supervisor/worker identity. Host process visibility is limited by this session's
PID namespace; no absence of other host jobs is inferred. No bound pipeline file
was edited and no running model/job was stopped.

The unsafe host candidate execution paths were removed from
`scripts/overnight_supervisor.py`. Direct application, linking, worker launch,
resume and activation now refuse before imports, control mutation or dispatch.
There is no environment/CLI bypass switch. `status`, durable `pause` and `disable`
remain; disabling does not signal healthy inference. **Automatic live promotion
is disabled**, even if qualification passes. The existing authorization for the
finite overnight suite remains available for a later explicit start after review;
it was not exercised here.

Added one confined executor using installed Codex named filesystem permissions
and bounded transient user services. Candidate imports, replay/finalization,
new/existing tests and private fixture releases all use it; there is no fallback
to ordinary host Python. It requests deny-by-default file access, explicit
runtime/code/dependency/evidence reads, only two source-file write grants for
repair, private temp/output writes, and no host network/socket access. Existing
tests and policy are read-only. New regressions are returned separately as bounded
data, checked for collisions/symlinks and copied into the validation snapshot.
Client storage/auth/network remain separate from tool access; child environments
are explicit, without credential/proxy/SSH-agent inheritance. Nonlocal tools,
hooks, plugins and automatic agents are disabled for the repair session.

Validation snapshots are private, copied after repair descendants stop, mounted
read-only, and hashed before/after execution. Integration for qualification is
only a private release copied from those exact checked bytes. Conflicting baseline
edits stop integration. Systemd user-service limits request4GiB aggregate memory,
no swap,128 tasks, NoNewPrivileges and bounded file descriptors/files; controller
logs and private trees also have limits. A fixed owner-identity watchdog plus
KillMode=control-group handles controller death/background descendants. There is
no Codex generation wall deadline or change to GLM generation settings. The
controller explicitly refuses to contact the host service manager from a Codex
tool session, preventing an outer-sandbox workaround.

Fixed the independent AST regression: unchanged `speed_suite.py` and its existing
`import statistics` now pass, including when another scoped body changes. New
imports, duplicate scoped definitions, out-of-scope changes and oversize inputs
remain rejected. The AST filter is explicitly a **scope check only**. The actual
`run = run.parent` example still passes that check; two disposable qualification
probes are prepared to require OS rejection through validation and the private
post-integration path. Those runtime probes have not passed here.

The new qualification-only path uses harmless mock credentials/evidence and local
socket canaries; it requires actual permission/resource observations before real
Codex dispatch. It prepares a controlled finalizer failure, baseline-fail/candidate-
pass regression, fixed existing failure-path tests, safe private integration,
fake queue resume, terminal completion and repeated-launch zero redispatch. The
two-attempt incident ledger is retained; migration imports the prior denied
attempt rather than resetting it. No new repair attempt was dispatched here.
The original failed qualification and all earlier inspection artifacts remain.

**Observed checks:** the installed CLI is still0.166.0; help/schema/feature
discovery and official documentation informed the supported configuration.
Strict configuration parsing succeeded. This release does not accept `--profile`
on app-server diagnostics, so the diagnostic supplies only the verified model
profile's six scalar values inline. Runtime exec/sandbox still explicitly select
the profile. No profile/base-config file was edited.

Nested namespace creation and user-bus access were denied in this Codex
environment. The final qualification-only invocation stops at the explicit
normal-terminal placement guard, with no Codex repair/model request or queue
action. A no-prompt startup trace was also blocked: strace reported
`PTRACE_TRACEME: Operation not permitted`. Therefore the earlier exact failing
Codex storage path remains **unestablished**, not guessed. No Docker group/socket,
global namespace or home-directory permission change has been established as
necessary. Normal-terminal checks must distinguish those capabilities from the
outer interactive restriction; nothing is relaxed automatically.

Offline validation:19 new hardening tests,17 supervisor tests and7 retained-repair
tests passed. The final full suite ran **665 tests in223.171s:646 passed,15 errors,
4 skipped, zero assertion failures**. All15 errors are `test_local_model` mock
loopback socket creation denied with EPERM. Four optional compiler checks remain
skipped. Logs/code hashes are in `results/supervision-hardening-20261030/`; earlier
full logs are retained for intermediate code identities. AST/shell syntax and
`git diff --check` passed. Unit tests/configuration acceptance are not presented
as live confinement, real Codex repair or compiler qualification.

The live data-only transport/compiler adapter is deliberately **not enabled or
implemented** here. Candidate code receives no Docker/SSH bridge, and cannot
obtain host execution by passing tests. Fake finalization uses explicit compiler
callbacks. A future live implementation must provide reviewed restricted
interfaces before automatic promotion/resumption can be enabled.

The last snapshot correction supplies read-only copies of the project documents
required by AGENTS, while explicitly overriding their dated launch instructions
with this qualification-only scope. Raw runs, inputs and credentials stay outside
the snapshot. The added context-selection regression passed; the final full test
run follows that correction. The earlier664-test inspection ZIP is preserved as
an intermediate snapshot, not silently replaced.

One normal-terminal command performs only qualification:

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-supervised-overnight.sh qualify-only --run runs/overnight-suite-20261030T085252Z-fae4ce
```

Even success remains UNARMED and yields only a private fixture release/review
patch. Small inspection records/ZIPs are under `results/inspection/`; there is no
mandatory write to `/home/mdi/Downloads`. The compact uploadable review archive is
`/home/mdi/projects/pdf-to-latex/results/inspection/pdf-to-latex-supervision-hardening-20261030T164815Z.zip`.
That initial archive is preserved; the final archive path is recorded in
`results/supervision-hardening-20261030/inspection-build.json` and printed at
delivery. It includes the permissions matrix, source/tests and blocked qualification evidence,
with per-file hashes; credentials/auth files and secret environment values are
excluded. The current runbook contains the observed/proposed/tested matrix.

Changed: `scripts/overnight_supervisor.py`, `scripts/supervision_policy.py`,
`scripts/supervision_checks.py`, `tests/test_overnight_supervisor.py`, the supervision
runbook, suite runbook, handover and this state entry. Added
`scripts/supervision_isolation.py`, `scripts/supervision_qualification.py`,
`scripts/supervision_service_guard.py`, `tests/test_supervision_hardening.py` and
`docs/evidence/supervision-hardening-20261030.json`. The existing launcher is reused.
All changes remain unstaged; unrelated edits and completed evidence are preserved.

## 30 October 2026 — complete working-tree review ZIP

Prepared an upload package covering every current tracked change versus HEAD and
every non-ignored untracked file, including pre-existing edits and earlier work.
It contains exact current files, baseline copies for changed tracked files, a
combined diff including additions, supporting source/test context, selected
validation evidence and a ChatGPT review guide. It excludes credentials, auth
files, environments, model weights, source PDFs and large raw run directories.
The ZIP path and validation receipt are recorded under `results/inspection/`.
Only this packaging note was added to project documentation; no implementation,
permissions, model settings, qualification or queue state changed. ZIP CRC,
per-file SHA-256 and change-list coverage are checked; tests were not repeated.

**Standing user delivery preference (30 October 2026):** include a fresh,
uploadable ChatGPT review ZIP with future project-change deliveries, without
requiring another request. Cover all current tracked/untracked changes, the diff,
supporting context and relevant evidence; exclude secrets and large raw data.
Save it under `results/inspection/`, verify its manifest/hashes, and print its
absolute path. A ZIP is inspection material, not authorization to run anything.

## 30 October 2026 — explicit sandbox permission-profile invocation fix

Read the operator's failed qualification at
`results/supervision-hardening-20261030/qualification-1793388130965908740/`.
Its resource gate recorded4GiB memory, zero swap and128 tasks, but the first
boundary command failed argument parsing because `--permission-profile` was
missing. No boundary harness or repair model ran in that attempt. Installed
CLI0.166.0 help confirms the named selector.

The shared `sandbox_arguments()` builder now passes
`sandbox --permission-profile incident-only --cd ...`, taking the selector from
the same generated `default_permissions` value. Both snapshot validation and the
repair-tool precheck use this builder; the source search found no other real
sandbox command constructor. Historical invocations and failed evidence are
preserved. The separate model/config profile and all generated permission values
remain unchanged.

A harmless `/usr/bin/true` invocation then exposed a second CLI compatibility
error: sandbox rejects `--strict-config`. It is now omitted for sandbox only;
exec retains it. The corrected invocation passed argument parsing and reached
bubblewrap construction, which this Codex environment blocked with
`app-server socket directory must be a user-owned directory with mode 0700`.
No permission/mode change was made, and this is not a successful sandbox or
runtime qualification. The normal-terminal qualification must still be rerun.

The new regression failed before the fix in all12 stage/editability combinations.
After the fix,20 hardening tests and17 supervisor tests passed. The regression
checks every fixed sandbox stage in both modes, matching the explicit selector
to the generated profile definition, preserving the model profile/configuration,
and excluding the unsupported strict flag. No unrelated full-suite rerun.
Python AST/shell syntax and `git diff --check` passed. Logs and preservation hashes
are under `results/supervision-hardening-20261030/permission-profile-fix/`.

The failed qualification, existing allowances, model/base configuration, seven
recorded calls,38 pending tasks, run binding and queue pointers remain unchanged.
Live promotion stays disabled. No inference, global configuration/permission
change or Git mutation occurred. Changes are unstaged in
`scripts/supervision_isolation.py`, the related explanatory comment in
`scripts/supervision_qualification.py`, `tests/test_supervision_hardening.py`,
the supervision runbook and this state entry.

Normal-terminal rerun, qualification only:

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-supervised-overnight.sh qualify-only --run runs/overnight-suite-20261030T085252Z-fae4ce
```

## 30 October 2026 — bubblewrap bootstrap denial; ordinary experiment independent

Read the actual result, boundary log, command and requested-permission records in
`results/supervision-hardening-20261030/qualification-1793390329959254879/`.
The precise failure is `bwrap: execvp .../bin/codex: Permission denied`: bubblewrap
could not execute Codex's own bootstrap inside the new sandbox, before Python's
boundary harness ran. Its output directory is empty. The resource gate passed;
CLI argument parsing is no longer the failure. This command does not use Docker,
so this evidence does not establish a Docker setup defect.

The Codex binary is a statically linked ARM64 executable with mode0755 and
searchable ancestors; execution/version reporting outside the failed sandbox
works. The requested profile explicitly permits the runtime files under the
broader denied Codex home. Documented specificity rules support such exceptions;
the broad deny alone is not proof of the actual enforcing cause. The exact
namespace mount/access or host security rule responsible remains unestablished.
Sandbox-log and kernel-journal searches exposed no additional matching evidence
here. No speculative permission broadening, chmod, host configuration change or
supervisor code rewrite was made. The diagnostic handover for independent review
is `docs/evidence/supervisor-bootstrap-denial-20261030.md`.

Separately verified the actual ordinary pointer and `scripts/speed_suite.py:verify()`:
current code hashes, frozen manifest/tasks, prepared/consumed evidence, all saved
call seals/request hashes, inherited accounting and registered version hashes pass.
The pointer is still `runs/overnight-suite-20261030T085252Z-fae4ce`, prepared_offline.
All7 calls are settled; Stage A is finished (5 revised,1 findings-only); B4/C8/D26
remain pending. No in-progress reservations or pause/stop flags; project/run
writer locks free at inspection. No completed work was reset or replayed.

The ordinary wrapper invokes the existing overnight controller directly and has
no supervisor/Codex/bubblewrap qualification dependency. Its normal full-test,
workload, runtime/model, compiler and fresh-readiness checks still apply. Completed
Stage A is skipped; only pending frozen work is admitted, with existing Low/skip
policies and the final inspection stop. No production fall-through. No live
service readiness, compilation or inference was launched during this verification.

43 relevant offline tests passed:7 saved-response/repair,13 overnight-suite,
23 scheduler/resume. This includes real threaded fake traversal of38 remaining
requests while preserving7 inherited calls, pause/resume accounting, and terminal
zero-request behavior. Evidence and preserved-file hashes are under
`results/supervision-hardening-20261030/bootstrap-exec-diagnosis/`; all110 recorded
failure/allowance/state/binding/pointer file hashes match after inspection.

The user's explicit instruction now separates ordinary continuation from the
still-disabled automatic supervisor. Updated the suite and supervision runbooks
accordingly; further supervisor development is not a prerequisite for this run.
Only documentation/evidence and the refreshed review ZIP changed; implementation
and permissions remain unchanged, and all edits are unstaged.

Normal-terminal continuation of the ordinary experiment:

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-overnight-suite.sh resume --run runs/overnight-suite-20261030T085252Z-fae4ce
```

## 31 October 2026 — offline Bergomi source export

Read-only discovery now observes the ordinary overnight suite
`runs/overnight-suite-20261030T085252Z-fae4ce` at
`suite_finished_for_inspection`, with 46 recorded calls. The speed suite is also
finished (20 calls); the ordinary editorial run remains paused (113 calls).
No matching editorial/suite/supervisor writer was observed during inspection.
This export did not dispatch, resume, compile, change permissions or operate any
service. Automatic supervision was not enabled.

Created the self-contained source collection
`results/bergomi-source-export-20261031T095646Z-complete.zip`
(220,760,347 bytes; SHA256
`bbb359b060b5418c3a937184090cbf4d85373fde75284f8e368e8f43696e265b`).
It contains the exact supplied 520-page original PDF; latest existing Bergomi
assembly and compiled master; all underlying editable TeX, figures and inline
macros; raw bibliography/epilogue and full extracted source context; original
OCR block/page maps; accuracy/review notes; inherited call evidence; version
identities; and explicit missing-section/dependency reports. The one-off
collector and verification record are in
`results/bergomi-source-export-20261031T095646Z/`.

The latest saved master is still `bergomi-1793296295851700898`: a PDF-inclusion
assembly with 21 retained text parts and 17 compiled section PDFs out of 133
planned parts, not a master compiling chapter text directly. Later production
Chapter 4 outputs and completed speed/overnight alternatives remain separate.
The export preserves 196 registered version records representing 189 distinct
TeX hashes, plus two separate existing editorial repairs with originals/diffs.
All 357 historical Bergomi manuscript files discovered under run version trees
match exported hashes; no unique older manuscript was replaced by a benchmark.

Across the frozen input-target maps, 36 planned parts have no registered output.
This accounting does not certify the other parts' fidelity. In particular,
overnight `d-large-02-bergomi-05` targets physical pages 193–212 but its saved
notes explicitly exclude the timer-option and lognormal-perturbation appendices.
The archive reports that scope mismatch, existing build failures, unfinished
recap material, unreviewed epilogue/bibliography, and the index absent from the
supplied original PDF. No corrected bibliography or missing content was invented.

Validation: all 6,827 ZIP entries passed CRC, SHA256 and size checks; 8,318
collected source/report paths were rehashed unchanged during collection.
All 1,046 scanned literal TeX file references resolve to included bytes.
Existing figures were copied to each standalone document's referenced path
where necessary; no TeX content or historical compilation status changed.
External TeX packages are listed separately. No fresh compilation, mathematical
audit, model inference or production test was run. Assembly into a direct-text
master and source-fidelity/cross-reference review remain future work.
Only export artifacts and this dated checkpoint were added by this task;
previous working-tree changes remain unstaged and untouched.

### 31 October 2026 — compact Bergomi text-only packaging

Created `results/bergomi-tex-only-20261031.zip` (138,057 bytes) from the verified
source export above. It contains only the saved assembly's 21 selected editable
TeX documents, a README and a small manifest: no PDFs, images, alternate versions,
raw call evidence or build dependencies. Each TeX file is byte-identical to its
assembly source; all 44 image-reference filenames, captions and embedded editorial
notes are preserved. The README distinguishes the 112 parts absent from this
selection from the wider collection's 36 missing parts and retains the known
Chapter 5 appendix gap. Image-only chart information and the Chapter 1 math
fragments with recorded textual reconstructions are identified separately.
All 23 ZIP entries passed CRC and exact-byte/hash checks; the source ZIP hash
is unchanged. No compilation, inference, regeneration or code change occurred.
Original artifacts and prior unstaged edits are preserved. Source fidelity and
future master assembly remain unqualified.

## 1 November 2026 — reconciled finite book completion, PREPARED NOT RUNNING

Read the user's full `Codex-Finish-Gatheral-Bergomi-2026-11-01.txt` instruction
and the current inspection package. Rediscovered the production/speed/overnight
pointers, released project/run locks and unchanged state hashes before editing.
Production remains paused at 113 calls with its separately retained 24-call
earlier history; speed and overnight remain finished at 20 and 46 calls. Their
states, requests, original drafts and completed evidence were not resealed or
modified. No new model inference occurred during this task.

Active prepared generation:
`runs/book-completion-20261101T095516Z-b24cfa`.
Separate pointer: `results/book-completion-current.json`.
The earlier unlaunched preparations remain preserved; compatible successful
document builds were carried forward rather than rerun after a code-only change.
The current run has zero new calls and status `prepared_offline`.

Implemented `probe/book_completion.py`, `scripts/book_completion.py`,
`scripts/run-book-completion.sh` and focused completion regressions. The existing
two-request scheduler is reused through a narrowly allowed completion protocol.
No supervisor, Bubblewrap repair or general autonomous code promotion is needed.
The user-authorized current GLM scope is now stated in AGENTS, the active handover,
README and the new completion runbook; earlier workflow instructions remain dated
history. Git/credential/service/permission restrictions remain intact.

Reconciliation retains 78 coherent saved reading documents: Gatheral's recovered
34 parts and 44 Bergomi documents, including grouped outputs once only. It records
source PDF/extraction/asset hashes, original version ancestry, actual target
blocks, adoption choices, original drafts, technical diffs and content-preservation
indicators. Gatheral's selected Lewis note already qualifies beta_2 for nonzero
rho and leaves beta_0 cancellation unresolved without J^(2); it was retained.
The existing Chapter 4 volatility-derivative repair is reused; the already-valid
production Chapter 4 second section is retained without duplicating the separate
High tag repair. Shorter or merely newer experimental alternatives do not displace
fuller production selections by default.

The four omitted Bergomi appendix bodies were removed from adopted coverage:
Ch5 timer options `bergomi-p0197:b4`–`bergomi-p0205:b11` (145 blocks), Ch5 density
perturbation `bergomi-p0205:b12`–`bergomi-p0211:b12` (101), Ch10 jump/Lévy appendix
`bergomi-p0424:b2`–`bergomi-p0434:b9` (183), and Ch11 correlation-estimator appendix
`bergomi-p0463:b6`–`bergomi-p0465:b4` (29). Missing digest headings are restored from
the existing extraction into saved recaps or retained with their missing digest
tail; a recap never replaces an appendix body.

The canonical ledger still identifies 36 fully uncovered parts and four partial
parts (the three appendix-containing targets plus the Chapter 12 boundary digest
heading). The frozen missing-only queue contains **17 coherent units / 34 work
requests**, covering 1,242 unretained source blocks: four appendix bodies, four
coherent substantive units representing the seven missing substantive sections,
seven grouped digest tails, epilogue and bibliography. No adopted block is queued
again. Twelve units retain full separate parent context, three use bounded exact
references, and the two end-matter units are complete chapter targets. Admission
reserves the unchanged output allowance and conservative critic-draft space;
actual runtime context/pool checks remain mandatory and never clip source text.

The completion request builder derives its scope from every assigned block and
nested heading, including appendices. It does not use the historical narrower
`larger_body()` output-title override; historical frozen requests remain unchanged.
Conversion and criticism share the same scope. Lightweight checks expose missing
headings/appendix bodies, required charts/tables, explicit numbered sequences and
broken labels while recording uncertainty about automatic/unnumbered mathematics.
Source/target accounting, output completeness, model review, compilation and
individually verified findings remain separate.

Applied exact derivative repairs for the observed paragraph-in-textcolor note
macros, unmatched note brace, missing AMS symbol package, ornamental U+2767,
misplaced tags 7.1/9.15/9.33, undefined textcompss in a quoted editorial reading,
and the fragile footnote macro inside a Chapter 9 caption. Real compilation exposed
the additional ornament in 2-s14 and the caption footnote after earlier failures
were fixed; neither repair rewrites mathematics. Figure 10.9 was restored from
existing block `bergomi-p0419:b2` and asset
`d6bde87360b133c396f7d878.jpg`, with its native-PDF-corroborated caption and explicit
qualification of the original misleading completeness claim. Actual compiler AUX
records confirm labels `fig:109 = 10.9` and `fig:1010 = 10.10`.

All **78 selected documents have successful compatible isolated build evidence**.
Both current partial reading masters compile: Gatheral 34/34 selected PDF parts,
Bergomi 44/44 selected PDF parts with the 17 unconverted units visibly missing.
Reading PDFs, selected TeX/assets, source/version/coverage manifests, unresolved
issues, compact TeX-only ZIPs and complete-source ZIPs were produced under the
run's `editions/` and `results/book-completion/`. These are working/partial
deliveries, not certificates of complete source fidelity. The existing immutable
Docker image was used through approved execution after outer-sandbox socket
denial; no installation, host fallback, service switch or permission change.

Validation: 17 focused tests passed. The full suite ran 683 tests in the Codex
sandbox with zero assertion failures, 15 mock-loopback socket PermissionErrors
and four opt-in compiler skips. Approved normal-terminal-context rerun:
**683 tests, 679 passed, four opt-in skips, zero failures/errors**, in 227.332s.
Logs are in `results/book-completion-validation-20261101/`; the run's
`validation.json` and `normal-terminal-checks.json` record identities and results.
The successful full check is cached for this exact code/test identity so launch
does not repeat it without a changed identity. Real serving/workload/capacity and
fresh GLM readiness remain runtime checks, not claims from mocks.

One persistent normal-terminal launch, with automatic readiness, the whole
approved queue, final assembly and packaging:

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-book-completion.sh run --run runs/book-completion-20261101T095516Z-b24cfa
```

The same wrapper provides read-only `status`, draining `pause`, settled-output
`resume`, and `bundle`. Terminal run/resume is zero-dispatch, including readiness.
Generation/build failures remain explicit and independent safe work continues;
shared ownership/integrity/scope faults stop admission. No uncertain request is
automatically resent. No completed experiment or old production queue is resumed.
Status/report paths and actual delivery ZIPs are listed in the run's `report.md`
and `results/book-completion/book-completion-20261101T095516Z-b24cfa-progress.json`.
`terminal.log` is created by the persistent worker at launch. Planning latency
from saved overnight work is roughly 4.1 ideal two-slot / 8.2 serial hours before
checks/build overhead; this is uncertain, not a deadline or performance promise.

All project changes remain unstaged; unrelated pre-existing edits were preserved.

## 1 November 2026 — REVISED, UNIFIED finalisation delivered

Read `Codex-Book-Finalisation-2026-11-01.txt` in full and confirmed its opening
identifies the REVISED, UNIFIED task. Actual parent state superseded the earlier
prepared snapshot: `book-completion-20261101T095516Z-b24cfa` finished all 35 calls
(one readiness, 17 conversions and 17 critics), all normal `glm53-regular`
responses. No project writer was visible and project/parent locks were free.
The parent remains unchanged at SHA256
`ccfe81aa4f6cbb9c4c35a8d3c1b1d1db03599a25b6a8b94a838bdb0051fff9f3`.

Linked derivative: `runs/book-finalisation-20261101T154901Z-466f18`.
Pointer: `results/book-finalisation-current.json`.
**DELIVERED: Gatheral 34/34 and Bergomi 61/61 selected PDF parts, both masters
compiled, no PDF gaps.** All 133 Bergomi canonical targets are mechanically
accounted for through grouping. No model/OCR/critic/benchmark work was repeated;
the derivative retains the 35 inherited calls and records zero new model calls.
No article job, production continuation or supervision was launched.

The two failures were verified from actual compiler logs. U+2767 in the Chapter 9
digest now uses the existing narrow ornamental fallback, without removing math
or arbitrary Unicode. Babel's missing `french.ldf` is recorded as a language
dependency, not invalid TeX. The explicitly authorized `texlive-lang-french`
dependency was supplied through the existing isolated compiler-image workflow.
New immutable image:
`sha256:4dd82c02ee37a6df7ee09991a3071d48ee9ea772276b165171697ce03ae62894`.
Only that versioned image was provisioned; no host packages, model services,
credentials or permission settings were changed. TeX builds remain offline,
non-root, read-only-source, no-shell-escape Docker builds with the prior limits.

Compared all 17 actual hash-verified documents sent to critics with their selected
revisions and exported compact diffs. The existing comparison function is now
called for future critic finalisation too. No removed explicit equation numbers,
image references, condition-word decreases or large body contraction were found
in these 17 pairs; these signals are not proof of mathematical preservation.
Substantive inspected changes and harmless formatting are discussed separately
in the derivative's source-review records. Raw inputs, responses and parent
accuracy logs remain untouched and locatable.

Local original PDF images were inspected at physical pages 199, 200, 201, 264 and
431. Page 431 confirms a printed extra inner lambda in (10.27), as well as
extraction damage to grouping. The justified correction from the displayed
forward equation and the small-jump limit is retained; only its source-check note
was updated. Timer footnotes 23/25 and budget/running-variation symbols are
supported by pages 199–201. The Chapter 11 epsilon_ii correction, leading bias and
variance are retained; prose now specifies independence across time and the
existing correlation across assets. No model assumptions were changed.

The timer critic's full Accuracy log was recovered from inside its fenced TeX.
The shared parser supports this explicit form and avoids rendering an exact
already-present log again. The duplicate generated timer suffix was removed in
the derivative; every finding remains available in the readable log and preserved
sidecars. Model-reported resolutions remain unverified claims unless a particular
local observation is separately recorded. Prompts, correction policy, reasoning
settings and acceptance rules were fingerprinted unchanged.

Recorded 12 exact-version reviewed flag groups without weakening global checks.
Flagged headings exist as accents, macros, bold/centred titles or maketitle.
Source page 264 confirms split Table 7.4 was recombined and retains the single-
maturity row 01-Jan-11, 63.8%, 64.9%, 319%, 325%. A separate real numbering defect
was fixed: the saved article had printed Tables 1–5. New compiler AUX verifies
Tables 7.2–7.6 and Figures 7.6–7.7. No table rows or captions were removed.

Applied only the supplied secondary corrections: La Fontaine VI; Durrleman [43]
14(2), 157–177 (2010), DOI 10.1007/s00780-009-0112-1; Carmona–Nadtochiy [21]
13(1), 1–48 (2009), DOI 10.1007/s00780-008-0078-4; Nachman [74] retained as
1(3), 311–328 (1988), DOI 10.1093/rfs/1.3.311. Stale contradictory/duplicate notes
are withdrawn in the derivative and explicitly superseded in current accuracy
dispositions; original evidence remains. These are operator-supplied findings,
not claims that Codex or GLM browsed the cited records. No bibliography audit,
external-fact verification system or more hesitant mathematical critic was added.

Validation: eight focused reusable-change regressions passed. Full offline suite
in the approved normal-terminal context: **691 tests, 687 passed, four optional
compiler skips, zero failures/errors**, 225.831s. Log:
`results/book-finalisation-audit-20261101/full-tests.log`.
Real compilation is separate: seven affected documents and both new masters
compiled successfully; 88 unchanged compatible part PDFs were reused after hash
and dependency checks. All 95 selected documents have passing build evidence.
The source parent, actual draft hashes and immutable policy identities still match.

Delivery index: `runs/book-finalisation-20261101T154901Z-466f18/FINAL-INDEX.md`.
It lists actual reading PDFs, editable part directories, small TeX-only ZIPs and
complete-source ZIPs with build-environment/dependency records. The master remains
a PDF-inclusion assembly; editable text is in individual standalone parts. Original
front/back/index supplements are honestly labelled PDF source pages, not editable
transcription; the missing Bergomi source index was not invented. Case-specific
source inconsistencies and mathematical uncertainties remain explicit; successful
conversion, criticism and compilation do not mathematically verify either book.

Implementation changes: `probe/book_completion.py` (narrow ornament helper),
`probe/chapter_editorial.py` (in-document accuracy capture/deduplication),
`scripts/book_completion.py` (actual critic-input comparisons and reviewed-flag
reporting), `probe/compiler_environment.py` / `probe/tex_compile.py` (French
dependency handling), `probe/book_finalisation.py`, `scripts/book_finalisation.py`,
`tests/test_book_finalisation.py`, and dated handover/runbook/state documentation.
All changes remain unstaged. Unrelated earlier edits and all completed generations
are preserved. Stop after this delivery; do not start another queue.

## 1 November 2026 — local checkpoint and laptop-transfer copies

The user explicitly authorized one local commit of the current relevant project
changes on `main`, with no push, branch switch, remote change or history rewrite.
This is a task-specific exception to the normal working-tree-only rule; the
standing project instructions are not broadened. The older standalone instruction
file `pdf-to-latex-codex-next-step.txt` is outside this checkpoint and remains local.

Reused the recorded successful 691-test finalisation validation after checking
the current finalisation code hashes, reconstructing the preceding code/test
identity, and matching the new finalisation test file and supporting workflow
sources against their saved inspection snapshots. Only checkpoint documentation
and transfer copies were added in this task; no inference, OCR, compilation or
book regeneration was performed. Git diff/whitespace and candidate-file checks
exclude credentials, book PDFs/converted editions, generated runs/results,
environments and model files from the commit.

Copied the existing archives identified by
`runs/book-finalisation-20261101T154901Z-466f18/state.json` into the ignored directory
`results/laptop-transfer/2026-11-01/` as `Gatheral-complete.zip`,
`Bergomi-complete.zip`, `Gatheral-tex-only.zip` and `Bergomi-tex-only.zip`.
All four copies match the recorded delivery SHA256 hashes. Archive CRC checks
passed; the complete archives contain the delivered reading PDFs, editable part
TeX and assets. `SHA256SUMS` contains only the four relative filenames and passes
`sha256sum --check`. Original archives and edition directories are unchanged.
The four archives total 63,566,623 bytes. The transfer directory remains outside
Git under the existing `/results/` ignore rule. No push is authorized or performed
by this checkpoint; the operator will push personally.

## 1 November 2026 — original 63-PDF batch preparation

The user separately authorized the current `/home/mdi/llm-wiki/originals`
collection, including the documented owned-idle-GLM stop/restart needed for a
separate OCR phase. This supersedes the earlier book-only scope for this new run;
it does not reopen finished books, experiments, supervision or the 376-source
intake union. No Git mutations are authorized. The pre-existing untracked
`pdf-to-latex-codex-next-step.txt` remains untouched.

Rediscovered the actual wiki layout before creating library directories: originals,
old vault, extracted (empty), tools and the 29 October intake. There was no sources
directory or root metadata database. Read current project instructions, handover,
state and runbooks. Project/run locks were free; saved production was paused,
speed/overnight finished, book completion finished and finalisation delivered, with
no in-progress reservations. Host tmux inspection found historical sessions but no
new collection worker; container inspection showed only the owned GLM deployment.

Rehashed all **63 distinct PDFs, 1,502 pages, 60,183,390 bytes**. The complete hash
set matches the intake baseline exactly. Labels include 38 research papers,
14 technical articles, three presentations, two surveys, two educational notes,
one partial course-notes chapter, one regulatory briefing, one lecture and one
news/web printout. Neither finished book is in this collection. All existing saved
native MinerU run source hashes were compared: no matches, hence zero reused
conversions/extractions and 63 documents newly queued. Old wiki summaries were
not counted as conversions.

Frozen preparation:
`runs/originals-batch-20261101T212602Z-ab2d41`;
pointer: `results/originals-batch-current.json`.
The manifest, full original identities/aliases, independent project PDF copies,
reuse audit, code binding and inherited sealed compiler qualification are retained.
Preparation did not run OCR, inference, compilation or service operations.

Implemented `probe/source_library.py`, `scripts/originals_batch.py`, its shell
wrapper and focused tests; extended the existing converter with injected frozen
source records, durable per-window progress and bounded interrupted-window
attempts, without changing historical sources.json. Admitted only the new fixed
two-request collection protocol in the existing scheduler. Existing scope,
critic-policy, draft comparison, coverage, asset, compiler and streaming code is
reused. The runbook is `docs/ORIGINALS-BATCH.md`.

Fourteen focused tests passed, including the real saved synthetic native renderer
and parser path through initial/reviewed text and portable generation publication,
with fake model/compiler output. They also check duplicate/version isolation,
Windows collisions, appendix retention, completed OCR reuse, persistent attempt
limits, uncertain-call refusal and independent-document continuation. No completed
experiment was rerun. The full offline suite is being recorded under this new run;
its final result and actual launch status must be read from the subsequent entry.

Read-only host preflight passed after sandbox Docker/tmux access was denied and
the narrow host checks were approved. It observed the exact regular GLM on both
nodes, 1,048,576 context, four serving slots and 1,808,384 shared pool tokens; the
controller still admits at most TWO requests. Available memory at that snapshot
was 12.31 GiB head / 14.54 GiB peer. Documented restart settings match current
serving flags/KV. The existing isolated compiler image was available:
`sha256:4dd82c02ee37a6df7ee09991a3071d48ee9ea772276b165171697ce03ae62894`.
These checks made zero model requests and zero service changes. Live OCR/GLM,
real compiler preflight and library publication remain separate runtime evidence.

### Actual launch — 1 November 2026, 21:41 UTC

The full offline suite passed: **705 tests, 701 passed, four optional compiler
skips**, 230.064 seconds. The run's `normal-terminal-checks.json` binds this result
to the exact code/test identity; full log is `tests-1793568665790214492.log`.

Launched the prepared run through its normal wrapper in the approved host context.
Persistent tmux session: `pdf-originals-batch`; controller PID: `489927`.
The run lock is held. Actual progress was observed: the isolated compiler smoke
passed both passes, all 63 verified original/source-metadata folders were created
under `/home/mdi/llm-wiki/sources`, and the guarded helper released the owned idle
GLM on both nodes. The first native OCR window started for
`original-bb9df37ac3ae2d05` (the one-page arctan source). Saved state is `running`,
resource phase `ocr_only`, with no diagnostic. No GLM requests have yet occurred;
the real conversion/critic smoke and automatic GLM restoration are later phases,
not yet qualified by this launch observation.

Log: `runs/originals-batch-20261101T212602Z-ab2d41/terminal.log`.
Durable `state.json`, `progress.json`, per-window state/logs and exception records
remain in that run. The compact progress copy is
`results/originals-batch/progress-originals-batch-20261101T212602Z-ab2d41.json`.
From the project directory use `bash scripts/run-originals-batch.sh status`,
`pause` or `resume` (replace the final action). The worker is deliberately left
running independently; do not poll until collection completion in this session.
No commit/push, permissions change or completed-book alteration was made. All
development changes remain unstaged. A duration estimate remains unavailable
until actual document-request timings accumulate.

## 2 November 2026 — defer only unstarted arXiv candidates

The operator supplied exactly six paper-level arXiv candidates and instructed that
any existing document-level GLM reservation, including a failed/uncertain one or
any part's reservation, prevents deferral. Calibrating Heston remains included;
no arXiv lookup, download or exact-version acquisition was performed.

At 09:21 UTC the actual run was active with 44 reservations. Attention had already
reserved call-044 conversion; COS had completed call-035 conversion and call-037
criticism and was delivered. Brigo, SINC, Bayer–Breneis and Homescu had zero GLM
reservations. All six filenames mapped uniquely to their frozen full SHA256
identities. Requested the supported pause; HVA criticism call-043 and Attention
conversion call-044 finished normally before the writer released its lock. No
request was cancelled. Bound code was changed only after paused state and exclusive
project, converter and run locks were verified. Candidate code/tests had been
prepared separately under `/tmp` while the worker drained.

Created an append-only linked selection continuation in the SAME run:
`runs/originals-batch-20261101T212602Z-ab2d41/continuations/arxiv-selection-1793611972428247694/`.
The sealed record contains prior state/binding snapshots, the six decisions and
an active binding for the selection implementation. The original collection and
binding files are unchanged; all 44 reservations, document histories, versions,
completed OCR, generation records and consumed allowances were compared unchanged.
The original inventory remains **63**, with **59 included / four deferred**.
Reason: `deferred for arXiv-source intake`. Deferred sources are represented
separately from failures/successes and retain all reusable extraction/preparation.
Attention's completed conversion and pending own-draft critic are retained. COS
and Calibrating Heston remain included. Final selection is based on the drained
ledger, not the earlier running snapshot.

Changes: `probe/originals_selection.py`, the smallest collection-controller
integration in `scripts/originals_batch.py`, `tests/test_originals_selection.py`,
and runbook/handover/state documentation. The deferral mechanism filters task
admission, checks before reservation, seals its selection and inherited calls,
and rejects reactivation or policy/allowance changes. It does not produce failure
deliveries for deferred sources; the library index and additive per-source
batch-selection record show the deferral. Original records/generations are retained.
Resumption of this selection continuation uses check-only GLM service verification.
The misleading log label and separate failure-diagnosis repairs are unchanged.

Focused validation: **24 tests passed**, including ten new selection/continuation
tests. They exercise exact-list matching, any-phase reservation protection,
Attention/COS retention, Heston inclusion, stale-ledger refusal, sealed history,
deferred publication and real threaded mock scheduling across repeated resumes
without duplicate dispatch. Repeating the actual selection control was idempotent;
the run state hash did not change. Evidence is under
`results/originals-selection-20261102/`. The normal resume launcher performs its
required full-suite validation for the new code/test identity before launching.
All changes remain unstaged; no commit, push or unrelated cleanup was performed.

Selection resume qualification completed: **715 tests, 711 passed, four optional
skips**, 228.867 seconds. Bound validation log:
`runs/originals-batch-20261101T212602Z-ab2d41/tests-1793612787979077977.log`.
Resumed in tmux `pdf-originals-batch`, PID `1432929`, with the run lock held and
no diagnostic. Actual new work: call-045 normal readiness, call-046 criticism of
Attention's preserved call-044 draft, and call-047 conversion of
`What_is_vol_of_asian_option.pdf`. The first 44 calls remain identical to the sealed
prior-state snapshot. No service was switched. Deferred sources remain absent
from the admitted task IDs; the original 63-source inventory remains intact.
Status/log/progress retain the same run directory and normal wrapper commands.
The worker is left running independently after this progress check.

## 2 November 2026 — bounded syntax and Low-conversion recovery

Confirmed completion of the preceding selection task before recovery development:
same selected run `originals-batch-20261101T212602Z-ab2d41`, frozen inventory 63,
59 included and four deferred (Brigo, SINC, Bayer–Breneis, Homescu). Attention,
COS and Calibrating Heston remain included. The selected exclusion continuation
and all inherited reservations verified. Production continued while candidate
changes were prepared under `/tmp/originals-recovery-20261102`.

Implemented the two explicitly authorized improvements using the existing
controller/scheduler/compiler: strict scoped syntax patches with one Low/8192-token
request per failed selected-version lineage, and one Low/131072-token conversion
of Characteristic Functions using the exact historical call-030 request with only
reasoning effort changed. Its new Max critic is bound to the new draft. Historical
call-030 (131072 reasoning tokens, zero final text, 3355.84 seconds) remains failed
and consumed. Its old task IDs cannot shadow or redispatch alongside the new
authorized tasks. Runtime/template evidence must establish Low support before
reservation. No global call ceiling, deadline, service switch or model install
was added. Dependency-only compiler recovery remains separate.

Three exact selected hashes/anchors were checked and repaired in separate saved
derivatives without any model call: method-of-characteristics texttt wrapper,
Burnett XVA quoted-math delimiters, Anfuso paragraph-containing colour note.
All three passed two-pass compilation with the existing immutable isolated image.
Before/after files, diffs, exact edits and builds are retained under
`results/originals-recovery-20261102/saved-repairs/`. Anfuso equation (13) bytes are
unchanged; its mathematical correction remains explicitly unverified and flagged
for later review using the operator's independence/conditional-representation
analysis. The derivatives do not approve any mathematical correction.

After candidate checks, requested the supported drain. The final active critics
completed; project/converter/run locks were verified free and then held exclusively
for integration. The handoff retained all 56 calls and the four source deferrals.
Created the linked recovery continuation in the SAME run:
`continuations/recovery-1793619389042707695/`.
It seals the prior state/binding, explicit policy, Low task definitions and the
three precompiled derivatives. Original inventory, bindings, prior generations,
failed attempts and allowances remain unchanged. Revised deliveries use new
immutable generations and retain prior publication/archive records.

Focused validation in the actual checkout: **42 tests passed**, including the
real saved-native fixture path, protected math/prose/assets, scope rejection,
persisted one-attempt allowances, linked deferral preservation, exact Low-only
prompt difference, own-draft Max criticism, repeated shared-scheduler resume,
immutable revised delivery and unchanged Anfuso equation (13). The three real
compiler builds are separate qualification evidence from these offline tests.
The full normal-terminal suite is required once for the final code identity;
its actual result and resumed progress are recorded subsequently.

The existing inspection ZIP now includes a focused `review/` tree: all converter
and critic versions/notes, comparisons, claim dispositions, unresolved issues,
coverage/build records, page/block maps, selected source crops/context and eight
reproducibly selected otherwise-unflagged passages. A staged preview exported
579 note records and eight samples. Package creation is not independent review.
Raw reasoning, original PDFs and bulk assets remain outside the compact bundle.

Changed implementation: `probe/tex_syntax_repair.py`, `probe/originals_recovery.py`,
`probe/originals_review.py`, `probe/originals_selection.py`,
`scripts/originals_batch.py`; new regressions in `tests/test_originals_recovery.py`
and recovery/runbook/handover documentation. Separate OCR, rotation, coverage-check
repairs and the historical logging-label defect remain in the backlog. All changes
are unstaged; no commit, push or unrelated cleanup was performed.

Recovery launch qualification completed: **733 tests, 729 passed, four optional
skips**, 227.783 seconds. Log:
`runs/originals-batch-20261101T212602Z-ab2d41/tests-1793620630467720536.log`.
The existing tmux controller resumed as PID `1655686`, with its writer lock held
and no diagnostic. Call-057 was normal readiness; **call-058 is the authorized
Low conversion recovery**, running alongside ordinary conversion call-059.
The actual saved HTTP body was verified equal to call-030's body with ONLY
`reasoning_effort` changed to `low`; the 131072 allowance remains. Installed
runtime/template evidence explicitly reports Low mapping with thinking enabled
and rendered label `Low`. Its own-draft Max critic remains pending. The historical
56 calls still match the sealed prior-state snapshot, and all four deferrals remain.

All three precompiled syntax derivatives were actually published as new immutable
deliveries with reading PDFs; old generations/archives remain. Selected labels:
`syntax-initial-1ef1df6217f2b296` (method),
`syntax-initial-22d20e9e10e0b0a5` (Burnett),
`syntax-initial-fa535087fd9996e0` (Anfuso).
Actual PDF/archive paths and old publication identities are recorded in
`results/originals-recovery-20261102/launch-verification.json`.
Two other selected-version syntax tasks are pending in the shared queue.
The unrelated OCR failures, rotation qualification and coverage-check work remain
backlogged. The worker is left running independently after this initial check;
end-of-batch inspection automatically includes the new focused `review/` material.

## 2 November 2026 — Characteristic Functions MinerU-only one-off

The user inspected the noisy PDF text layer and explicitly authorized one attempt
using only saved MinerU material. Kept the preceding Low effort and 131072-token
allowance to isolate the source-layer change; a usable draft receives the normal
Max own-draft critic, also with MinerU-only source. All ten pages and 202 primary
blocks remain. No source clipping, OCR, source download, service change, or change
to other papers' normal High/Max dual-source requests was made. The prior High and
dual-source Low failures remain failed/consumed, including their runtime cost.

Prepared changes separately under `/tmp/originals-mineru-only-20261102` while
production continued. Requested a supported pause only when integration was ready;
waited for calls 075 and 077 to complete without cancelling them. Verified all
project/converter/run locks free, then held them exclusively for integration.
All 77 prior calls and the four arXiv deferrals were preserved.

Created an append-only continuation in the SAME run:
`runs/originals-batch-20261101T212602Z-ab2d41/continuations/mineru-only-1793637397840505901/`.
It seals the exact one-off request, task definitions, policy and prior state/binding.
The current recovery/selection chain is verified; original inventories/bindings
are not rewritten. New IDs are `convert-mineru-only-1` and `critic-mineru-only-1`
under the same source-part key. One reservation per new phase persists across
resume; old task histories stay intact and cannot supply the new critic's draft.

Focused qualification: **49 tests passed** in the actual checkout. The seven new
tests cover full primary retention, PDF-layer omission from both phases, exact
own-draft identity, no critic without a usable draft, consumed allowance persistence,
active-writer refusal and real threaded scheduling across repeated resumes without
replay. Implementation changes are `probe/originals_mineru_only.py`, the narrow
recovery/controller integration, and `tests/test_originals_mineru_only.py`, with
dated documentation. All changes remain unstaged; no commit or push.

MinerU-only launch validation: **740 tests, 736 passed, four optional skips**,
238.967 seconds. Log: `tests-1793638035079532560.log` in the same run.
Resumed controller PID `2072840` holds the writer lock, with no diagnostic.
Call-078 was normal readiness, call-079 resumed the pending Smile Risk critic,
and **call-080 is running the one-off MinerU-only Low conversion**. Its
MinerU-only Max critic is pending. All four deferrals and the 77 prior calls remain.
The worker is left running independently after the initial outgoing-request check.


## 2 November 2026 — CF MinerU-only High/Max follow-up and repair cancellation

The user found the call-080 MinerU-only Low draft much better and reports compiling
a personal copy after removing `\tag{33}`. Both saved call-080 versions retain
their original hashes; no personal copy was overwritten or adopted. Its Max critic
call-082 exhausted 131072 reasoning tokens and returned no final text. The user
explicitly cancelled the queued CF syntax repair. It had no reserved model call;
its task and lineage now record `cancelled_by_operator`, preserving the plan and
allowance history. No running inference was cancelled.

Prepared the new High/Max adapter separately while production continued. Requested
a supported drain and waited for Lee call-084 to settle. It failed with truncation
after 2976.26 seconds; the failure is preserved. Confirmed paused status, no
in-progress requests, and all three writer locks free. Held the project, converter
and run locks while installing the narrow adapter/controller changes. Baseline
code hashes were checked; unrelated work was preserved.

The selected run remains `runs/originals-batch-20261101T212602Z-ab2d41`.
Its new append-only continuation is `continuations/mineru-high-1793647467785995034`
with seal `d314bff6cc5b194216f712ac6b663c5617b51807ba56d3eae8219716665af055`.
All 85 prior calls and the four arXiv deferrals remain unchanged (59 admitted of
63 inventoried sources). High and Max each have one new reservation allowance,
not a reset of historical failures. All ten CF pages and 202 assigned MinerU
blocks remain. The frozen conversion request equals call-080's request except
for `reasoning_effort=high`; PDF text is absent. The conditional Max critic is
bound to the new High draft and cannot fall back to the old Low draft if High
fails. Both phases retain the 131072-token allowance and existing shared scheduler.
Normal requests for other papers and serving settings are unchanged.

Focused validation: **57 tests passed**, including cancellation without reservation,
primary-only inputs, High/Max settings, own-draft identity, failed-High gating,
per-phase consumed allowances and shared scheduling/resume without duplication.
Evidence: `results/originals-mineru-high-20261102/{handoff,prelaunch-verification}.json`
and `focused-tests.log`. Normal-terminal launch runs the required full suite once
for this implementation identity before starting tmux; actual progress is recorded
separately below. No commit, push, service switch, downloads or OCR were performed.

High/Max launch qualification passed: **748 tests, 744 passed and four optional
skips**, 268.048 seconds (`tests-1793647591574429780.log` in the run). The same-run
persistent controller resumed and holds the writer lock. Readiness call-086
completed; **call-087 is in progress for the MinerU-only High CF conversion**,
with sealed-request equality checked on the actual outgoing request. Max CF
criticism is pending; independent normal conversion call-088 uses the other slot.
No old CF syntax model request exists. Initial runtime evidence is saved in
`results/originals-mineru-high-20261102/launch-verification.json`. The worker is
left running independently; these observations do not claim conversion completion,
coverage, compilation or mathematical verification of the new High/Max output.
Host read-only verification confirmed tmux session `pdf-originals-batch`, live
controller PID 2302500. Call-087 has nonempty raw streaming/events and saved
reasoning, confirming real model progress beyond reservation. The host PID is not
visible in the sandbox process namespace; host tmux/ps verified it directly.


## 2 November 2026 — saved-input HTML comparisons

Created `results/source-extraction-comparison-20261102T200320Z.zip` and a verified
identical Downloads copy (9,970,385 bytes). Its `index.html` opens page-by-page
saved MinerU TeX versus native PDF-text comparisons for Smile Risk, Lee and the
successful 25-page Information Geometry control (High call-074, Max call-076,
recorded compilation passed). All 77 pages, 530 referenced saved crop assets,
unchanged original PDFs, complete text extracts and source/call identities are
included. Failed Smile Risk part-2 pages 16–25 and Lee pages 1–27 are labelled.
Local HTML links/page counts, asset presence, original/source copy hashes,
archive CRC and SHA256SUMS were checked. No browser rendering or independent
mathematical audit is claimed. No OCR/model requests, tests, compilation or live
code/state changes were made; the production worker was left untouched.


## 3 November 2026 — finished originals batch and full failure-review export

Observed the existing run `originals-batch-20261101T212602Z-ab2d41` in terminal
`collection_finished_with_report`, finished 04:42:42 UTC, zero active requests,
125 historical calls and writer lock released. Final inventory remains 63:
59 admitted and four deferred. Of the admitted sources, 27 are labelled working
editions, 29 have delivered gap/failure records and three failed OCR/preparation.
These statuses are not mathematical verification. Document-level records show
46 conversion-complete, 44 review-complete and 36 compilation-passed; partial
and historical usable drafts must not be confused with complete current phases.

Created the offline review ZIP
`results/inspection/originals-failure-review-20261103T073033Z.zip`, with an
identical copy `/home/mdi/Downloads/originals-failure-review-20261103T073033Z.zip`.
Size: 148,966,666 bytes. SHA-256:
`4de856bd247c0caf5d9f8961d092f26ceb5a144eb91c554013067aa5ac7b9fe9`.
It contains all 32 problem documents plus the successful Information Geometry
control, original PDFs, 975-page side-by-side source comparisons, saved native
inputs/raw OCR evidence, converter/critic/syntax TeX and accuracy records,
compiler diagnostics, 67 exact requests/final answers and all 15 failed-call
reasoning records. Large wire/SSE logs, successful reasoning, environments,
authentication/credential files and model files are excluded. Missing extraction
pages and raw-window images that were never materialized are explicitly listed.

For the three documents without prepared dispatch inputs, comparisons display
saved raw MinerU blocks with completed-owner/context/unexported labels. Their
PDF-text views were extracted offline from unchanged originals during export,
never sent as model requests. No OCR, source rendering, compilation, model calls,
service/permission changes or production state/code changes were made. Hashes,
ZIP CRC, all HTML local links/page counts, expected evidence presence, source-copy
identities and Downloads copy equality were verified; no new unit tests or browser
rendering were run. Only this dated documentation entry and new export artifacts
were written; existing code/evidence and Git state were preserved, unstaged.


## 3 November 2026 — compact representative failure-review upload

Created `results/inspection/originals-failure-sample-20261103T074251Z.zip` and a
verified Downloads copy: 19,325,991 bytes, SHA-256
`bcf4dd2df4b12ed5a6f55f0029f5ff7bbf25594c3ed1ef557dbfbaecb2efa2cf`.
Purposefully selected 14 problem documents and the successful Information Geometry
control, covering all major failure classes and the Anfuso mathematical-review
flag. Full source text comparisons and original PDFs span 357 pages; all available
case TeX/model outputs, relevant diagnostics and 29 exact request/answer records
remain. Included 101 supplementary source crops. Omitted compiled reading PDFs,
unrelated case payloads/full run state, duplicate review PNGs and most other crops
with explicit per-case exclusions; these sample omissions are not extraction gaps.
The full 149 MB archive remains unchanged. Verified HTML links/page counts, ZIP
CRC and file hashes, Downloads equality and unchanged production-state/full-archive
hashes. No OCR, inference, compilation, unit tests, permission/service changes or
code edits; only new export artifacts and this unstaged documentation entry.


## 3 November 2026 — complementary failure-review ZIP

Created `results/inspection/originals-failures-part2-20261103T200433Z.zip` and a
verified identical Downloads copy. Size 18,838,838 bytes; SHA-256
`e6dc147c137060d2ae453e4d72aeda8dd4e8e986112434a028a4ea003e97b359`.
It contains exactly the 18 cases omitted from the first representative sample,
with all 618 physical-page text comparisons, available TeX/model evidence,
38 exact request/answer records and saved failure/compiler/coverage evidence.
Sixteen original PDFs remain whole. Rough Heston and All About XVA each have
five losslessly copied source pages with explicit original-to-excerpt mappings;
their full original PDFs are omitted only from this compact ZIP. All 65/83 text
pages remain. Thirty-five supplementary crops are retained. Most crops, compiled
reading PDFs and hash-identical compiler input sources are omitted explicitly.
Duplicate task primary text is removed only from export CASE metadata; exact
source extracts and outgoing requests remain unchanged. HTML links/page counts,
ZIP CRC/file hashes, Downloads copy equality, source excerpt text/page geometry
and unchanged previous archive hashes were verified. No OCR, rendering, inference,
compilation, code edits or Git operations were performed. Only export artifacts
and this unstaged documentation entry were added.


## 3–4 November 2026 — focused local recovery implementation and linked trial

Implemented an opt-in local trial for CF, Linetsky Spectral, Linetsky Pathint,
Mean Reversion Bias and Alternatives to DL, plus source-checked Anfuso/Breaking
Barriers checks and a saved Information Geometry control. Cooking with Collateral
is excluded. No originals/production generations or historical allowances were
reset; no paid calls/credentials, model downloads, global configuration, Git staging,
commit/push or unrelated service operations were used.

Reusable code adds auditable secondary-text assessment, structural output-unit
ownership, hash-bound focused edits, failure-specific finite tasks, and detailed
OCR warp evidence. Existing compiler repair now relocates invalid inner alignment
tags without deleting their numbers/expressions. The saved CF Low draft's tag(33)
derivative passed both isolated compile passes with unchanged mathematical bytes;
its remaining mathematical transcription issues are recorded separately. This is
not the user's laptop edit and not mathematical acceptance of the Low draft.

Initial run `focused-recovery-20261103T212127Z-c483fb` passed 766 tests (762 passed,
four optional skips, 228.440s), started persistently and made real OCR/model progress.
Its diagnostic found a zero-width crop in physical-page-27 text; the upstream
width<3 rejection occurs too late. The qualified process-local reordering was
replayed on the exact captured array, preserving the existing rejected/accepted
box policy and accepted crop bytes. No SDK installation was edited.

Pathint focused criticism completed with no edits in 107.08s, 1,668 completion
tokens (1,614 reasoning). Anfuso Max criticism completed in 1,464.78s, 88,685 tokens
(87,455 reasoning), reverted the unsupported numerator and revised its inline
note, while retaining an unresolved warning about stale summaries beyond scope.
Both actual versions passed isolated builds. The old whole-document costs remain.

Supported pause drained both requests; all locks were free before integration.
Selected linked run: `runs/focused-recovery-20261103T223632Z-d9c8f9`.
It preserves all three initial requests, versions and syntax allowances plus the
failed OCR diagnostic, and skips directly to the one qualified OCR correction
pass. It retains 24 completed owned OCR pages. The frozen maximum is 61 model
requests INCLUDING the three inherited requests (58 remaining): 13 conversions,
16 focused reviews, 15 conditional Low reviews, 16 conditional syntax requests,
and one readiness. No recursive splitting, global wall deadline or next collection.

The linked route also removes program character offsets/unrelated saved-draft
body text from critic inputs, keeping full-base hashes and exact permitted ranges
in program metadata. Secondary masking preserves prose around invalid glyph spans.
Twenty focused regressions and actual SDK failure replay passed. Final normal-
terminal validation/resumption has been requested; actual runtime outcome follows
below. Preparation-only earlier trial directories have zero calls and are retained.
See docs/FOCUSED-RECOVERY.md for frozen scopes/settings and status/pause/resume/bundle.


## 4 November 2026 — linked trial resumed and Spectral extraction recovered

Final code validation passed **768 tests: 764 passed, four optional skips**, in
229.440s (`tests-1793768365218037039.log` in the selected linked run). Persistent
controller PID 213936 holds the writer lock. The qualified pass completed all
49 owned Spectral pages, preserving the original 24 pages/three windows byte for
byte. The formerly failing pages25–32 window completed successfully with the
existing min-width rejection moved before cropping; later missing windows also
completed. Prepared Spectral sections6.2–6.3 cover physical pages25–32, including
complete boundary blocks; no whole-paper GLM conversion is scheduled.

The unchanged owned GLM deployment was restored, its Low/High/Max mapping was
reverified, and remaining model work started through the existing two-slot
scheduler. By the 05:18 UTC snapshot, Information Geometry's focused control
review and CF Cases1–3 conversion had completed; that unit's Max critic and
CF Cases16–18 Low conversion were active. Both actual outgoing requests used
`glm53-regular`, the intended effort, streaming and 131072 output tokens. The
three inherited requests were not replayed and readiness was not repeated.

CF's saved full Low derivative retains tag(33) and passes two isolated compiler
passes. Pathint's focused review and Anfuso's revised appendix version also have
passing builds. These facts do not certify all mathematics: source inspection
found remaining CF transcription issues, and Anfuso's out-of-scope editorial
summaries remain explicitly unresolved. Current trial progress is separate from
its final mathematical/source-check results.

Actual launch/continuation evidence is
`results/focused-recovery-development-20261103/launch-verification-final.json`.
Current run: `runs/focused-recovery-20261103T223632Z-d9c8f9`; log `terminal.log`,
refreshing status `progress.json`, immutable versions/builds under that run.
The finite worker will create its final inspection ZIP under results/inspection
and stop. It cannot resume the original production queue or launch another study.
All changes remain unstaged. No paid/cloud calls, credential reads, model downloads,
SDK/serving configuration changes or Git history operations were performed.


## 4 November 2026 — Kimi pending; source logging fix staged

Kimi/OpenRouter integration and testing are explicitly a pending next phase for
focused recovery. The current implementation produces offline escalation proposals
only; Kimi integration, qualification and execution have not been completed.
This clarification does not authorize cloud requests or credential access.

Prepared source-aware logging in
`results/pending-source-logging-20261104T055959Z/` (also discoverable through
`results/pending-source-logging-current.json`). Proposed files are
`probe/chapter_glm.py` and `tests/test_chapter_logging.py`; they have NOT replaced
the files used by the active worker. A reservation captures explicit source
filename/title, section and phase from task/state metadata for both serial and
threaded paths. Readiness is labelled Model readiness; missing identities remain
Unknown source/section instead of defaulting to Gatheral or another book. Generic
startup messages are neutral. Existing logs/call records are preserved.

Isolated staged validation ran 61 tests: **60 passed, one optional real-Docker
compiler test skipped**. Eleven new regressions cover ordinary-paper logging,
serial/threaded metadata propagation, neutral/unknown identities, snapshot stability,
unchanged model payloads and historical logs; existing chapter/concurrency tests
also passed. No inference, compiler qualification or full-suite rerun was performed
for this staging task. The active trial's bound logger SHA256 is unchanged and
no pause/interruption was requested. At the next genuine idle boundary, rediscover
writers and verify base hashes; unfinished work requires a linked continuation,
with all consumed attempts retained. Do not overwrite historical bindings.
See the staged README, unified patch, manifest and validation evidence for the
concrete integration procedure. Current handover/runbook documentation is updated;
all changes remain unstaged, with no commit or push.

## 4 November 2026 — optional Kimi K3 implemented; no paid qualification

The focused local run `focused-recovery-20261103T223632Z-d9c8f9` finished on its
own at **09:06:19 UTC**, with 36 recorded calls. No pause or service change was
made for this task. Development occurred under
`results/kimi-development-20261104T064831Z/workspace` while the trial was active.
Before integration all original code hashes still matched the development base;
project, runs and selected-run locks were idle and held during copy-back. The
pending source-logging patch was reconciled and integrated alongside Kimi. Checked
historical binding, state, progress, plan and terminal-log hashes are unchanged;
no historical run was resealed and no allowance was reset. Integration evidence:
`results/kimi-development-20261104T064831Z/integration.json`.

Implemented an explicitly opt-in passage converter/focused reviewer, reusing the
MiMo cloud HTTPS transport, cumulative ledger, reservations, private key handling,
exact draft-hash edit validator and existing isolated compiler. MiMo defaults
are unchanged. Normal local batches cannot automatically call Kimi. The adapter
has no paid retries, tool/search requests or compiler provisioning. The first
selected control is paid protocol qualification; failed/uncertain qualification
blocks subsequent tasks, including after resume. Unknown charges stay reserved;
identity mismatch persists a halt; finished resume makes zero new requests.

Unauthenticated public metadata checked on 4 November identifies exactly
`moonshotai/kimi-k3` through `sail-research/fp4/us`, with supported High effort and
multipart image input. Initial settings are High and 32768 completion tokens
including reasoning, concurrency one, one attempt/task. Routing pins the provider,
disables fallback, requires supported parameters, denies data collection and
requires zero retention. Recorded exact-route prices are $0.504/M input and
$24.12/M output. Sail's general website privacy policy is distinguished from
OpenRouter's exact API-route policy. Price/privacy/support are rechecked before
each paid reservation. Public support is not live image or reasoning validation.

Fresh provisional plan: `runs/kimi-plan-20261104T160838Z-b39701`, discoverable via
`results/kimi-prepared-current.json`. It contains an Information Geometry §2
successful control review and separate CF Case17 conversion/review operations,
using saved page/block identities, exact local draft hashes and source crops.
Pathint was removed from the preliminary sample after verifying its completed
focused review; CF still has unverified mathematical edits and source ambiguities.
Cooking with Collateral remains excluded. No compiler-only or OCR infrastructure
failure is sent to Kimi. All outbound content is reviewable in the plan previews.

Maximum three requests; no extra readiness/recovery. Planning estimate $2.398221288
at full output allowance; conservative maximum $3.906994176 under proposed $4.00
pilot cap. Each image request reserves the full accepted input context because no
exact-route image tokenizer bound is published. Historical recorded spending is
$0.2397167286 across 21 reservations, with zero unresolved prior charges. The
USD10 non-resetting key ceiling is unchanged, not replenished; current authenticated
remaining allowance is unknown and will account for other applications at launch.

Final integrated offline suite: **803 tests in 234.567s, 799 passed and four
optional real-compiler checks skipped**. It includes 24 new Kimi regressions and
11 source-logging regressions, plus existing MiMo budgeting/route/recovery tests.
The earlier development-copy full run had five missing fixture/context files;
the integrated run with actual project fixtures passed. Logs:
`results/kimi-development-20261104T064831Z/validation-integrated-full.log` and
`validation-kimi-final.log`. `git diff --check` and exact prepared-plan verification
also passed. A subsequent preparation-only correction added CF's global negative-
support convention and explicit context page/block mappings; the 24 Kimi tests
and actual saved-plan scope/identity checks passed again. The previous prepared
plans remain unchanged; the pointer selects the fresh plan. No new real compiler,
model inference, credential read, paid call,
installation, Git staging/commit/push or local-service operation occurred.

See `docs/KIMI-ESCALATION.md` for prepare/inspect/explicit paid launch/status/pause/
resume/bundle commands. **Kimi live qualification remains pending**, including
authenticated allowance and actual output/image behavior. A cloud result will
be an unaccepted derivative, not automatic adoption or mathematical verification.
The completed local trial and production queue remain stopped. Changes are
unstaged; unrelated work is preserved.

## 4 November 2026 — Kimi own-draft chain prepared, not launched

Observed first-pilot result supersedes the earlier pending-qualification entry:
`runs/kimi-trial-20261104T163217Z-5bdcc1` finished at 16:37:25 UTC with three normal
responses and passing builds, costing $0.1473857802. Its CF conversion covered
Case17 only; its separate review used a saved GLM version, not the Kimi draft.
The proposed equation(34) edit was rejected by exact-anchor validation and was
not applied. This is live transport/output-protocol evidence, not mathematical
verification. Saved cumulative spending is $0.3871025088 over 24 settled calls;
current authenticated remaining allowance is unknown. The USD10 non-resetting
key ceiling is unchanged.

New plan **`runs/kimi-plan-20261104T173035Z-5b9553` is PREPARED, NOT RUNNING**.
It permits two work requests only: a High Kimi conversion of complete CF
Cases13–18, then fresh High criticism of the exact newly extracted TeX. Reused
qualification binds the prior observed image-bearing request/result, model
revision, provider, reasoning, token allowance and privacy controls; the old
run's executor binding is preserved, not resealed to match this extension.
Current metadata and private allowance checks remain mandatory at paid launch.
No new paid control, readiness inference, split, retry, fallback or paid repair.

Source `original-21debf82bc2c0a3d`, SHA256
`21debf82bc2c0a3d1317bd051960c4ac4de2138213a515d3bea334ac2521edd6` was checked
against the saved original and native extraction. Original PDF images were
inspected. Output owns 26 blocks from physical page4 block10 through page6 block5,
before Case19: Cases13–18, equations25a/25b/26, 27a/27b/28, 29–36, including the
Case14 page crossing and all restrictions/negative-x branches. Printed pages
are 498–500. Context-only page1 supplies definitions/Fourier and support conventions.
The complete assigned MinerU TeX is 6,124 bytes. Three assigned-scope crops and
one context crop retain original page/coordinate/hash provenance.

The existing native-text assessment examined 196 lines on pp4–6 and suppressed
zero invalid-glyph spans. Image comparison nevertheless established severely
garbled ASCII symbol mappings and reading order. The new plan quarantines that
secondary text outside both model inputs, records the heuristic limitation and
manual rationale, and preserves the raw text. MinerU is not presumed correct;
the model receives the corresponding original-image evidence. No OCR was rerun.
Cooking with Collateral remains excluded.

The critic preview is a sealed source-evidence recipe with an explicit new-draft
slot, not a fabricated exact request. Runtime materialization binds the exact
converter TeX/hash, saves the actual request before dispatch and supplies neither
converter reasoning nor its accuracy conclusions. Failed/truncated conversion or
missing case/equation presence signals skips criticism; uncertain transport keeps
its cost reserved and cannot replay. Exact-anchor/hash safeguards retain rejected,
overlapping, stale and unresolved suggestions. Both actual versions compile
separately in the existing isolated image; compilation is not coverage or fidelity.
No new dependency installation is introduced.

Public metadata refreshed **17:12:06 UTC** confirms `moonshotai/kimi-k3`, canonical
revision `moonshotai/kimi-k3-20260715`, `sail-research/fp4/us`, High, image input and
required structured-output support. Reasoning remains High, output allowance
32768 including reasoning, concurrency one. Current pinned prices are lower than
the first pilot: $0.391/M input, $18.723/M output, $0.195/M cached input. Provider
pinning, no fallback, supported-parameter enforcement, deny-data-collection and
zero-retention requirements are retained. Proposed cap **$2.10**, conservative
reservation **$2.021392384**, full-output planning estimate **$1.268162555**. The
estimate is not measured usage; image reservations price the full accepted input
window. Readiness/failed requests share existing persistent cumulative accounting.

The existing wrapper now supports preparing an own-draft chain with
`--qualified-run`, plan-specific status/bundle, dynamically bound critic requests,
and richer final bundles (actual requests/responses/reasoning, both TeX/PDFs when
built, diffs/accuracy/coverage and cost/token/timing tables). Saved GLM Cases16–18
material is comparison-only and never enters either model request. Its scope is
smaller; no equal-workload speedup is inferred. The finite controller stops when
the two tasks settle or cannot continue. Finished resume makes zero new calls.

Validation: **817 tests in 235.774s: 813 passed, four opt-in real-compiler skips**.
All **38 focused Kimi tests** passed, including 14 new chain regressions for exact
own-draft identity, no reasoning leakage, conditional criticism, no extra control,
scope/number coverage, qualification reuse, pause/resume, uncertain-call protection,
and actual result/PDF inclusion in bundles. Real source/template/hash inspection
and `git diff --check` passed. Evidence is under
`results/kimi-own-draft-development-20261104T170843Z/`. Tests used mocked cloud
transports/credentials and compiler outcomes; this new passage has not been
converted, reviewed or compiled. No credential read, paid inference, OCR, model
service operation, Git staging/commit/push or history rewrite occurred.

See `docs/KIMI-ESCALATION.md` for the exact operator launch and status/bundle/pause/
resume commands. All current and prior workers/locks were idle before editing;
historical runs, allowances, originals and unrelated working-tree changes were
preserved. Changes remain unstaged.

## 4 November 2026 — master-archive source audit running independently

User-authorised discovery/download/source inspection targets only the 350 distinct
PDFs with `master` provenance in the completed
`/home/mdi/llm-wiki/source-intake-20261029T102944Z` intake. Frozen membership was
checked against actual master.zip members, its recorded SHA256, all 350 canonical
PDF hashes and page counts. Scope is **350 PDFs / 5,883 pages**, separate from the
376-document union, proxy collection and original 63-document batch. The embedded
workbook supplies bibliographic/download/search-history rows for every master PDF;
the archive README has stale counts and is not treated as current membership.

Audit directory:
`results/source-availability-audit-20261104T194212Z`, discoverable through
`results/source-availability-current.json`. An isolated environment pins
`arxiv==4.0.2` and dependency versions in requirements.lock. The existing controller,
OCR/model environments, original PDFs, intake manifests, conversion generations,
services and queues are unchanged. No inference, OCR or LaTeX compilation occurs.

The serial persistent worker runs in tmux **source-availability-350**, with its own
lock and atomic per-document checkpoints. One shared arxiv client is paced at
3.3 seconds across arXiv requests; downloads and other public hosts are separately
paced. Known identifiers, Crossref, arXiv title/author searches, OpenAlex, Unpaywall,
HAL, Zenodo and returned author/repository/supplement locations are used. The user
supplied a contact email for Unpaywall/polite Crossref; contact configuration is
excluded from inspection ZIPs. Public API queries worked; real denial/rate-limit
responses and bounded transport failures stop that service, not independent papers.
Missing DOI records (404) are cached per document and no longer disable a service.
Earlier classifications/corrections and raw packages are retained as audit evidence.

At the **20:46:20 UTC checkpoint**, 40 documents had been processed and 310 remained:
40 corroborated arXiv work matches, 33 verified TeX downloads, 11 apparently complete
dependency sets with matching-version evidence (229 original pages), seven PDF-only
alternatives and no completed-query negative source findings. Counts overlap;
candidate uncertainty and incomplete auxiliary/wider searches remain separate.
The disjoint snapshot reconciles 11 matching-source, 22 source-assessment, seven
confirmed-arXiv/source-unavailable and 310 pending rows to all 350 originals.
These identifier-first early results are not an estimate of the whole corpus.

Archive inspection never extracts or executes supplied scripts; it checks member
paths/links, size limits, actual TeX, inputs, bibliography, figures and external or
dynamic dependencies. Source URLs returning PDFs/errors are not TeX downloads.
Version correspondence preserves explicit identifiers and alternatives; exact PDF
hashes or full native text with only Unicode/whitespace normalization support a
matching-version record. Mathematical signs, Greek, punctuation and case are kept.
Neither static dependency checks nor matching text establish mathematical fidelity;
compilation remains not tested and no document is automatically removed from a queue.
Different Noether translations and related WMC simulation repositories are recorded
as human-review examples, not silently accepted as the original article's TeX.

Live 350-row CSV/JSON, candidate-location/version tables, reports, package hashes and
diagnostics are under the audit directory. A consistent compact snapshot ZIP at
this checkpoint is `results/source-availability-inspection-20261104T204620Z.zip`
(253,336 bytes); its CRC and file hashes passed. It excludes original/downloaded
PDFs, source packages, caches, environments and contact/credential files. The
worker creates its own final report/bundle when the finite pass ends; unresolved
targeted web/version/dependency questions remain visible rather than negative.

Use `bash results/source-availability-audit-20261104T194212Z/control.sh status`
(or pause/resume/bundle). Resume is persistent, prevents duplicate launch, preserves
settled records and makes zero new requests for an already finished pass. The log is
`worker.log`; details and exact absolute commands are in the audit's README.md.
Fifteen offline safety/matching/dependency/error-classification tests passed. No
production code changes, Git staging/commit/push, model requests, service changes
or conversion queue modifications were made. The audit is **running, not complete**.

## 4 November 2026 — current GLM vision inspected and two short checks completed

Read-only runtime evidence is under
`results/glm-vision-audit-20261104T211847Z`, with report `REPORT.md` and pointer
`results/glm-vision-audit-current.json`. The head container is
`glm53-flash-tf`, image `sha256:9b00719301e859f7b790b5c4d80ab1e49ef64bef63d3e7af2f3829cfc32cfee1`,
published digest `sha256:14b5072e8e9918f1080153f57321415a387bc7d78cf9c9b44a7aeae2d4399ccf`.
TensorFold 0.6.0 upstream revision is `c4646171139ee8a3c38103eaa1699dad226ec12b`.
All 107 installed recipe patch files match the clean local Mia checkout at
`3fd60dfc836fab0f1ed0fd4f0afaf2a1d62b2aab`, including 0003-glm-vision. The image
does not expose an explicit recipe Git-revision label; that distinction is recorded.
Regular model revision remains `078455ffe6472f9a52fbc1139f58b9db2881b25c` and
DFlash2 remains `bf582e4eacc1810f76656d1811693ff6c6737d2a`. The peer's image ID
matched; its additional formatted fields were not successfully captured.

Actual launch arguments include `--vision`, context1048576, parallel4 and thinking.
The 05:11:38 UTC startup line follows tower construction/warmup in installed code
and reports a 1.05 GiB vision tower plus 0.75 GiB workspace. Current code/environment
resolve to **2048 tokens/image, 16384 shared image tokens/request, 50 images max**;
image-budget overrides were unset. Up to eight pictures keep the individual cap;
nine get1820 each and50 get327. The installed resize aligns canvases to multiples
of28, fits aspect ratio with bicubic antialiasing and pads right/bottom; the cap
allows roughly1.61 MP. Larger saved Kimi crops would shrink to71.5–86.1% linear
size under GLM, threatening small symbols. Kimi's own internal resizing is unobserved.

GLM was idle before each of two explicitly authorised local image-only checks.
The installed request parser and actual serving-template renderer verified Low;
each request used Low, 2048 output tokens including reasoning, one image and generic
instructions without expected transcription or extracted source text. Fresh synthetic
Greek/Latin/sign/subscript transcription completed in **5.575s** (1 reasoning/45 final
tokens). The original CF physical-page5 equation(34) crop completed in **2.977s**
(1 reasoning/161 final tokens), visually preserving the printed factors, signs,
exponents and number. Both finished normally as `glm53-regular`; counter34 became36
and the server returned idle. Both images fit without downscaling. Exactly two
requests were reserved/completed; no retry or extra readiness generation occurred.
Requests, image/crop hashes, responses, returned reasoning and timings are preserved.
This establishes supported/enabled/exercised vision separately, not whole-page
mathematical fidelity or correctness of the published formula.

The 19 October digit/blank controls passed. Earlier four full-page mathematical
reviews exhausted8192 tokens entirely in reasoning; a16384 default-effort retry was
partial. Explicit Low/High returned proposals, but missed source defects and remained
unqualified; selected page2 fixes were accepted only after operator source review.
The inspected 20 October follow-ups used other Qwen/Flash aliases and are not counted
as GLM evidence. Saved historical request/response metadata remains unchanged.

All actual transport bodies for the original batch's125 and focused trial's36
requests were checked: **zero image parts**. Five recent Kimi requests contained
13 image parts. Textual image filenames/TeX references are not transmitted pictures.
GLM's new equation-only result and the earlier Kimi Case17 output agree visually
on their shared equation; their scopes/settings differ, so no timing speedup is
inferred. A one-request matched-input GLM High/32768 proposal reuses the exact saved
Kimi Case17 messages/image bytes; it is saved as NOT RUN, not queued or authorised
by the already-consumed two-check allowance. It would require no new paid call.

No service restart/upgrade/configuration change, permission change, OCR, compilation,
paid request, production queue edit, Git staging/commit/push or active-job pause
occurred. Local model calls avoided environment API keys. Only new audit artifacts
and this state entry were written; the independent source audit was left untouched.

## 4 November 2026 — master source-audit first pass finished

Observed at22:25 UTC: `results/source-availability-audit-20261104T194212Z`
completed all350 frozen master PDFs and stopped at21:36:25 UTC; its worker lock
is released. This supersedes the earlier running/40-document snapshot, not the
preserved evidence. Counts are119 corroborated arXiv work matches,108 actual TeX
downloads,25 apparently complete dependency sets, one mathematical HTML/XML
location needing assessment, and25 observed PDF-only alternatives. Counts overlap.
The312 'uncertain match' flags include low-confidence additional candidates for
documents with a stronger verified match; they do not mean312 unidentified PDFs.

Disjoint reconciliation:17 matching-version source candidates +4 alternative-version
source candidates +4 source-version-unresolved +84 requiring structured-source
assessment +11 arXiv matches without usable downloaded TeX +228 uncertain candidate
matches +2 incomplete/no-candidate records =350. The17 apparently complete matching
packages correspond to byte-identical downloaded PDFs and342 original pages; the
four alternative-version packages cover81 original pages and require version
decisions. Static dependencies, matching version and mathematical fidelity are
separate; compilation remains untested and no source or queue selection was changed.

There remain293 records with blocked/incomplete portions of auxiliary or wider
searching. OpenAlex returned429 after202 successful requests, and SSRN plus multiple
publisher/DOI endpoints returned403. These were respected, not bypassed. Zero
definitive negative availability findings were inferred from incomplete searches.
No research, download retries, inference, OCR or compilation was launched for this
status update. The 350-row CSV and counts were read back and reconciled.

Fresh compact snapshot:
`results/source-availability-inspection-20261104T222525Z.zip` (1,044,260 bytes),
CRC/hash verified. Its CSV/JSON/candidate tables are also under the audit's
`snapshots/source-availability-inspection-20261104T222525Z/`. The pointer and README
now record pass completion; historical results and all original files are preserved.

## 5 November 2026 — finite extraction comparison and Mathpix supplement

The 350-document source-availability audit is deferred and unchanged. A separate
32-page/eight-document comparison is prepared. It reuses saved traditional MinerU
extraction and qualifies pinned MinerU Pro and GLM-OCR on the peer before their
full selected workload. Cooking with Collateral and all production queues remain
excluded. See `docs/EXTRACTION-COMPARISON.md` and the current pointer.

Selected local preparation: `runs/extraction-comparison-20261105T094814Z-scope`,
linked from `extraction-comparison-20261104T233805Z` before any local model or OCR
dispatch. The parent code snapshot, source images and manifests remain intact.
The link fixes a scope-selector ambiguity caused by prose mentioning Case19.
The fixed two-assignment downstream schedule admits at most12 primary High/Max
requests, six conditional existing-policy syntax requests and one program readiness
request. The unchanged GLM start helper's small startup smoke is separate overhead.
There is no overall deadline or production continuation. Runtime/model execution
is not established by preparation or by the launcher request.

Baseline versions and all13 model/config hashes were reverified. The head disk
now has219GiB free after the operator's specifically reported weight cleanup;
the peer has about2.2TiB. No files were deleted by this task. The official stable
ARM64 vLLM image was downloaded on the peer and a separate SDK image built:
`sha256:8739f6791c2028acd99cb5284181287a6c9d580865dbd4c8e1acc08fcf14447a`.
It uses vLLM0.19.0, Torch2.10.0+cu129, Transformers5.3.0, mineru-vl-utils2.0.7,
and pinned GLM-OCR SDK0.1.5. Three upstream dependency-metadata conflicts are
recorded explicitly; this is not a clean pip check or GPU qualification. The
documented Transformers override must pass actual BF16 CUDA and the retained smoke
page. Failed build records and the rejected installed nightly image inspection are
preserved. Neither TensorFold nor `.venv-mineru` nor the baseline model cache changed.

Mathpix was separately authorised by the operator up to$1 before tax, using only
the same32 selected pages. `runs/mathpix-comparison-20261105T064003Z` completed
eight standard `/v3/pdf` submissions, with all MMD/MD, native TeX/MMD ZIP and line
JSON outputs downloaded. Source/subset hashes and rendered-pixel equality were
verified before dispatch. Runtime credentials stayed private; response credential
fields were redacted. No Mathpix GLM conversion/critic requests were made.

The durable per-key ledger reserves before POST and preserves uncertain charges
and returned pdf_id values. Observed reservation and local list-price estimate are
both$0.16, with zero uncertain submissions. Provider usage reports32 pdf-page units
and eight of each conversion format; actual invoice cost and credits remain unknown.
The requested privacy flag is `metadata.improve_mathpix=false`; separate PDF page
image/text retention and possible account-level overrides are documented, not
misrepresented as zero retention. No billing settings or quotas were changed.

Seven Mathpix direct TeX builds passed. Breaking Barriers failed at Unicode U+25A0;
its raw output is preserved. Eight named source passages were directly compared:
CF Case17 and Anfuso equation13 were faithful in the checked details; Breaking
Barriers Figure4 survives, while its nearby hat-f formula has letter O instead
of the printed zero. This is a real transcription issue separate from compilation.
See its `SOURCE-REVIEW.md`, `source-review.json` and `docs/MATHPIX-COMPARISON.md`.
These samples do not certify all32 pages or establish a downstream speed benefit.

The Mathpix mock suite passed8 checks covering redaction, budgets across resumes/
key changes, unknown-submit protection, durable pdf_id, archive paths and finished
resume. The local comparison's focused contract tests passed11 checks. An earlier
full offline run passed835 tests with4 optional skips; final changed-code validation
is performed by the normal-terminal launcher and recorded with its actual identity.
All new development remains unstaged. No commit, push or production queue restart.


## 5 November 2026 — observed extraction results and layout compatibility continuation

Head free space rechecked at219GiB; peer about2.2TiB. Downloads and Docker build
layers stay on the peer, with no deletion of additional files. The existing image
and pinned weights are reused, avoiding another build/unpacking peak. Baseline
MinerU, model cache, TensorFold and source audit remain unchanged.

`extraction-comparison-20261105T125157Z-qualification` finished at13:53:58 UTC.
Its ten recorded calls include all six inherited baseline/readiness/syntax calls.
MinerU Pro completed32/32 selected pages with zero page failures:104.85s model load,
238.70s summed page extraction time. Eight named source-image checks found retained
CF Case17 factors, Anfuso equation13, Spectral equation57, table sample and Figure4.
The Figure4 image-analysis output also includes an approximate numerical table
absent from the original: this remains an engine interpretation, not source data.

On the matched CF Cases13–18 assignment, baseline High conversion took38.26min,
its Max critic exhausted131072 reasoning tokens with no answer after34.24min, and
the build remains unresolved. Pro High conversion took3.48min and Max criticism
8.23min; converter and unchanged reviewed version compiled. The control Section2
conversion/critic durations were1.20/8.36min baseline and1.01/5.34min Pro. Durations
can overlap. This small paired result supports improvement for the tested CF scope,
not a corpus-wide speed or fidelity claim. Case17's Pro-derived converter TeX was
also source checked; all other cases are not thereby verified.

GLM-OCR's first SDK import failed before any page request: SDK0.1.5 asks for
PPDocLayoutV3ImageProcessor, while Transformers5.3.0 exports the same V3 processor
as PPDocLayoutV3ImageProcessorFast. A CPU-only import check in the existing image
passed after a process-local alias; no package/weight/algorithm change or rebuild.
The helper explicitly binds Transformers5.3.0, validates required methods and
refuses to overwrite a different processor. Failed startup evidence is preserved.

At a verified idle boundary, the new linked run
`extraction-comparison-20261105T185601Z-layout` was prepared to qualify only the
missing GLM-OCR arm. Ten calls, Pro outputs, selected versions and consumed
allowances are inherited. Original primary bound remains12, with four primary
requests still eligible if GLM-OCR qualifies; no completed call or page is rerun.
The parent plan/binding is not resealed. See its progress.json for launch/current
status. Code/setup preparation is not proof of working GLM-OCR extraction.
The preceding implementation passed840 tests with4 optional skips; this narrow
alias and its regression require a new normal-terminal check, recorded by launcher.
All changes remain unstaged; no commit, push or production queue restart.


## 5 November 2026,19:25 UTC finish — important GLM-OCR validity correction

`extraction-comparison-20261105T185601Z-layout` finished its finite workload and
stopped at19:25:47 UTC. The regular GLM configuration was restored; no production
queue was resumed. All32 GLM-OCR pages returned normal runtime results, but saved
source checks subsequently established a **shared adapter omission**: actual
PP-DocLayoutV3 model labels5/15 are `formula`, while our custom task map accepted
only `display_formula`/`inline_formula`. The SDK silently skips unmatched labels.
`aside_text`/`reference` were unmapped too. CF page5 layout visualisation contains
formula boxes that never reached OCR. All32 native outputs contain zero formula
regions. This is our integration defect, not demonstrated model incapability.

The normal runtime completion flags remain historical evidence, not content
approval. GLM-OCR's CF converter/critic contain visible placeholders and are
INVALID as a full-content speed comparison despite compiling. Its control
converter compiled; revised critic TeX failed, and bounded syntax patch was
rejected. All12 primary calls, one program readiness and two syntax calls across
the lineage are preserved. Nothing was replayed or granted renewed allowances.
The smoke test wrongly admitted prose-only output; this is documented explicitly.

A proposed mapping correction and fail-closed preflight/total-formula-loss guard
are saved under the run's `proposed-label-map-fix/`, with four passing offline
regressions on actual bad output/model labels. They are NOT integrated or runtime
qualified. No rerun was launched after discovering the defect. A new linked plan
must preserve consumed requests and qualify complete mathematical structure before
any further downstream calls. Current finished resume makes zero requests.

The deployed experiment passed841 tests with4 optional skips. Pro and Mathpix
results remain usable for their explicitly sampled checks; Pro's matched CF
conversion/review improvement is real for this scope, but no corpus-wide accuracy
claim follows. Read `DECISION-REPORT.md` and the direct-source-review JSON files.
The final reviewed inspection ZIP is recorded in
`results/extraction-comparison-reviewed-current.json`. Its root report prominently
disqualifies the GLM-OCR comparison and preserves all native evidence. No new
inference, paid usage, deletion, service change or Git mutation occurred in this
final saved-evidence review.

## 5 November 2026 — finite extraction follow-up launched

New authorisation is one corrected GLM-OCR qualification/comparison and three
complete MinerU Pro papers, not a production restart. Run:
`runs/extraction-followup-20261105T204630Z`; pointer
`results/extraction-followup-current.json`; runbook `EXTRACTION-FOLLOWUP.md`.
Original inventory hashes match CF10 pages, Spectral49 and P-values8. Twelve Pro
pages and the existing CF Cases13–18 High/Max versions are reused. Maximum new
allowance:20 primary +10 syntax requests, with all15 historical calls preserved.
The frozen structural scopes cover complete papers, including references and the
Spectral scanned copyright notice. No source/weight deletion or new paid request.

Implementation is separate from the completed comparison: explicit complete-label
routing, detected-to-recognized-to-export region accounting, independent raw-region
export alongside SDK formatter merges, original figure retention and separately
labelled inferred chart data. Missing or unassociated regions fail accounting;
three detected formula regions cannot pass when only one survives. Known source
content and direct visual checks remain necessary to assess detection omissions.
The new implementation passed849 tests with4 optional skips, including8 focused
follow-up regressions. Historical code/configuration and source outputs unchanged.

The two real GLM-OCR qualification pages completed, all41 regions accounted for
(CF23 including11 formula regions; control18 including3 formulas and2 footnotes).
Direct image comparison FAILED CF equation34: GLM-OCR moved -8*a^mu outside the
fraction denominator in the final exponential. Control equations1–3 matched.
Thus only routing/execution qualified; mathematical qualification did not pass.
The remaining30 GLM-OCR pages and its four matched downstream requests are blocked
by the frozen quality gate. No retry, manual mathematical correction or substitute.
The raw export also retains a redundant outer display wrapper around some raw
$$ formulas; this is a separate presentation issue, documented without altering
current bound code. See `qualification/source-review.json` for exact hashes/readings.

The persistent worker continued independently to the Pro whole-paper arm at
21:02 UTC. At that observation the image was loading, with12 inherited pages;
new Pro execution and downstream completion must be checked in progress.json.
The current owned regular GLM service was stopped via its verified helpers for
OCR, and the controller restores its captured configuration before downstream
work. No unrelated workload was stopped. tmux: `pdf-extraction-followup`.
All new files remain unstaged; no commit/push. No corpus queue follows this run.

Follow-up execution confirmed: tmux pane2533206 reports python, pane_dead=0.
Latest saved progress snapshot 2026-11-05T21:06:06.720853+00:00: extraction mineru_pro. Pro page counts: {"completed": 25, "running": 1}.
This includes12 manifest-verified reused pages; only additional completions are new.
Interim qualification inspection: `results/inspection/extraction-followup-qualification-20261105T210430Z.zip`
(3,114,445 bytes; CRC/file hashes checked). This is not the final paper delivery.
The worker automatically assembles and bundles after its finite eligible tasks.

## 6 November 2026 — lifecycle repair and linked preparation

The stopped parent `extraction-followup-20261105T204630Z` completed all67 Pro pages
but crashed at shared `focused.adjust -> focused.progress`, missing plan field
`maximum_model_requests`, before any new conversion reservation. The worker had
released its locks and restored GLM. This supersedes its earlier running snapshot.

Prepared `extraction-followup-20261105T223237Z-lifecycle` from saved evidence.
Original20 primary+10 syntax authorisation is retained; eligible16+8 is explicitly
validated, with15 historical calls kept separate. No allowances reset, OCR rerun,
new model/paid request or service change occurred during migration. The failed
GLM-OCR mathematical gate remains false and its six tasks ineligible.

Rebuilt native-region validation metadata and exact unique ownership for all nine
paper units. P-values now exposes4 tables,19 equations and7 image regions; empty
output produces omission warnings. Later Spectral context includes all preceding
substantive definitions/source, not just the first unit. Scope/context/assets and
native output hashes are bound to the linked plan and checked before dispatch.
Equation tags accept legitimate whitespace; automatic numbering remains unverified.
Original figures are required independently of generated asset references, while
inferred chart data remain separate. CF reused build provenance identifies its
parent; no false local build claim.

The conservative multi-unit assembly fixture passed actual isolated compilation,
including figure, duplicate local macro names, cross-unit reference, namespaced
bibliography keys and paragraph-containing notes. Unknown/conflicting preambles
remain explicit failures. A workflow-specific compiler flag prevents dependency
downloads, preserving the installed image. Standalone TeX remains unchanged.
Eleven focused lifecycle tests passed against actual saved shapes and shared
adjustment/reporting/scheduling/settlement helpers, including the formerly crashing
boundary. The final full normal-terminal suite is running; preparation alone is
not a running model batch. See actual progress and normal-terminal-checks.json.
New changes are unstaged; no commit/push or production queue operations.

### 6 November 2026,08:16 UTC — continuation actually running

Final required suite:860 tests,4 optional skips,240.535s; recorded in the linked
run's normal-terminal-checks.json. The persistent worker launched at08:16:11 UTC
(PID3096532), crossed the prior failing helper boundary, and durably reserved
call-001 and call-002 for the two remaining CF conversion units. Actual response
streams and partial final text are present on disk for both calls. This is real
progress, not only a tmux launch request. At the initial live snapshot14 primary
requests remain unreserved and at most8 conditional syntax requests remain.
No OCR, readiness generation, paid call, service change or download was performed.

No complete-paper delivery is claimed yet. Model review, generated scope coverage,
standalone/master compilation and independent source verification remain separate.
The controller automatically proceeds through eligible tasks and isolated assembly,
records document-specific failures, writes its inspection ZIP and stops. Controls
are unchanged in the runbook; finished resume is a no-op. Current live artifacts:
`runs/extraction-followup-20261105T223237Z-lifecycle/{terminal.log,progress.json}`.

08:20UTC: CF call-001 and call-002 completed in137.5s/145.0s; selected
annotated converter drafts compiled successfully. Calls003/004 are Max critics;
actual saved request payloads match the selected drafts and SHA256s exactly.
12 primary requests remain unreserved, plus up to8 conditional syntax requests.
Coverage is requires_source_review, not verified complete. Live inspection snapshot
with settled TeX and test evidence: `results/inspection/extraction-followup-lifecycle-review-20261106T082115Z.zip` (2304559 bytes), CRC and file hashes verified.

## 6 November 2026 — finite source-image experiment preparation and saved repairs

Read `GLM-SOURCE-IMAGE-REVIEW.md`; pointer `results/glm-image-review-current.json`
selects `runs/glm-image-review-20261106T121258Z`. Initial observed state: old worker
absent, project/run locks released, GLM idle and vision caps unchanged2048/16384/50.
The previous bound implementation and hashes are preserved under
`results/image-review-development-20261106T120547Z/previous-code/`.

Before freezing the new implementation, Spectral and P-values saved derivatives
were compiled using the existing isolated image. Spectral's exact three theorem
declarations are supported without accepting arbitrary commands. A discovered
introductory-display numbering error was corrected in a further preserved derivative;
source equations1–22, assumptions2–4 and cross-references were checked against actual
PDF/aux output. Final Spectral derivative: `repairs/Spectral-numbering-qualified/`.
P-values uses the complete composite Figure1 once; one image, all bounds inside the
page, no oversized-float warning, rendered axes/caption inspected. All panel crops
remain. CF glyph/vector bounds and the widest rendered page showed no physical-page
clipping, so no equation reflow was applied. Old editions remain unchanged.

Eight Spectral unit4 edits were adjudicated directly from source images and local
SDE/Liouville calculations. Each is supported as a correction to the printed
mathematics; source-faithful converter versions remain. Historical converter notes
are labelled superseded and current dispositions recorded. This does not complete
the two failed historical reviews or certify whole-paper accuracy.

New held-out CF evaluation correctly records Eq27b Gamma(b+n), not Gamma(d+n).
Historical incorrect evaluation notes are preserved; reviewers never receive the
answer sheet. The new prompts bind exact historical critic input drafts and original
image bytes. Installed CPU preprocessing includes the application's actual in-memory
vision template patch; the earlier raw-template zero-image diagnostic is preserved.
Returned live prompt usage must match exact image-expanded expected counts before
subsequent inference can proceed. No text-only fallback is permitted.

Option C was explicitly deferred before inference; crops cover the assigned dense
regions at original resolution. Eight work requests are frozen within the ten-call
ceiling: four sequential Max A/B, two conditional concurrent B/Max, two B/High.
No generating-readiness calls planned; no service-setting changes. Failed or uncertain
calls remain consumed. The first targeted suite passed11 tests; the final full suite
is running through the normal launcher. Preparation is not proof of a running trial.
See actual progress for launch and first-response verification. TODO priorities are
recorded in `docs/TODO.md`. All changes unstaged; no paid calls, downloads or Git writes.

### 6 November — saved repairs complete; image experiment running

Two zero-call startup failures were preserved: missing inherited effort-verification
artifact, then missing resource-observation stage records. Linked continuations
restore the verified artifact and initialise all three stages; no allowance reset.
Selected run is now `runs/glm-image-review-20261106T133752Z-stages` (pointer unchanged
in name, updated explicitly). Final suite872 tests,4 optional skips,239.705s passed.
The first live request cf-A/Max is reserved and streaming; further requests are gated
on its returned image-expanded prompt usage. Actual image-processing verification
is pending completion, not claimed from request fields. Tmux `pdf-glm-image-review`.
Serving limits remain2048/image,16384/request,50 images; no restart or paid request.

Saved-file repairs already passed real compilation/render checks. Spectral final
working edition is `repairs/Spectral-numbering-qualified/`; its unnumbered opening
display and original source sequence1–22 now match, with assumptions2–4 resolved.
All eight checked unit4 mathematical corrections are logged and retain source-faithful
converter originals. P-values Figure1 is one full composite, visibly within the page;
all crop assets, geometric provenance and source image are retained. CF was inspected
for actual clipping and preserved without cosmetic changes. The two old exhausted
review scopes are still unreviewed; their later plan is in evaluation/, not this queue.


## 6 November 2026 — bounded image-review recovery prepared

Read the complete operator instruction Codex-Image-Review-Recovery-High-vs-Max-20261106.txt.
The preceding image trial is observed finished at14:33UTC; its worker absent and
project/run locks released. Non-generating current health showed zero requests,
glm53-regular, unchanged2048/16384/50 image limits, four server slots (project cap2),
and13.17GB/17.68GB available head/peer memory at the check. No service was changed.

The previous top-level bound implementation/hashes are preserved under
results/image-review-recovery-development-20261106/previous-code. No historical
run or allowance was resealed/reset. New pointer results/image-review-recovery-current.json
selects image-review-recovery-20261106T215705Z. This dated preparation is NOT a launch claim.

The actual CF-A annotation failure is repaired offline via typed plain annotations
and the existing TeX escape helper; intentional math edits stay untouched. The
new derivative passed isolated compilation and rendered-note inspection. Its
source-math body is byte-identical. Failed prior output/proposal and compiling
original remain. A failed derivative cannot replace a compiling selection.

Eight coherent units cover every region of the two unfinished scopes exactly once:
CF Case19/Continuous, Mixtures, Sums/References; Spectral6/6.1,6.2,6.3.1–2,6.3.3,6.3.4.
Saved drafts match the authorised hashes; Spectral uses only the already-qualified
additional generated-note marker. Corrected editions, numbering/assets and all
eight adjudicated Spectral changes are reused. P-values remains unchanged.

Plan:8 Max recovery reviews +2 matched High reviews +2 for one separated artificial
CF sign-error control =12, one attempt each, within14 authorised;0 readiness planned.
Paired tests are sequential with reversed order across the two natural scopes.
Other recovery units use at most2 existing scheduler slots. Held-out source checks
and mutation records never enter requests; no broad High/selective policy adopted.
All12 exact requests passed installed CPU image/template expansion without inference.
Real server image-processing verification remains pending each live response.
The controlled input also passed real compilation. Focused lifecycle, no-replay,
exact-scope, renderer and bundle regressions are being finalised; final launcher
requires recorded full-suite success for this code/test identity.

See docs/IMAGE-REVIEW-RECOVERY.md for controls. Worker will preserve proposals,
per-arm builds, selection decisions and automatically create a verified compact
inspection ZIP. Source adjudication of new findings is not performed continuously
by Codex after launch. Recommendation5 is explicitly DEFERRED. Cooking excluded,
GLM-OCR stopped,350-source audit deferred. No paid calls, downloads, installations,
OCR/conversion, Git staging/commit/push or production pointer changes.

### 7 November 2026,07:33 UTC — follow-up launched and real progress verified

Run: runs/image-review-recovery-20261106T215705Z. The date in the ID is its
preparation date; actual persistent launch was07:30:55 UTC on7 November, PID212820,
tmux pdf-image-review-recovery. Full final suite:890 tests in242.680s,4 optional
skips, passed identity recorded in normal-terminal-checks.json.

At07:33:43 UTC, call-001 (CF Case19/Continuous, High) had completed with a usable
focused response, verified server image-expanded prompt usage and passing real
compilation. Call-002 is its unchanged-input Max comparator and has real streamed
reasoning saved. Twelve frozen work calls total;0 readiness calls. No OCR or
conversion repeated. No independent accuracy conclusion is drawn from this first
response. Current settings remain2048/image,16384 shared,50 maximum, High/Max
as planned,131072 completion ceiling, at most2; no service restart/change.

Live log: runs/image-review-recovery-20261106T215705Z/terminal.log. Progress and
controls: progress.json and docs/IMAGE-REVIEW-RECOVERY.md. Worker automatically
finishes eligible reviews, compiles candidate editions, preserves failed builds
without promotion, packages a hash/CRC-verified inspection ZIP, and stops. Its
inspection.json will locate the final/partial package. No later queue is enabled.
The session ends after initial progress; Codex does not continuously supervise
or independently adjudicate later mathematical findings. All changes unstaged.

### 7 November 2026 — finished recovery collected for ChatGPT

Saved state confirms completion at08:51:49 UTC,80.90minutes elapsed;12 calls settled,
11 usable review responses/builds and one CF Case19 Max reasoning-only exhaustion
(131072 reasoning tokens,0 final,32.70minutes). Summed request time110.32minutes
includes the failure and overlapping work. CF and Spectral complete assemblies
compile; P-values remains unchanged. Original/full per-arm versions are preserved.

Packaging inspection found two important false source/draft claims: CF Mixtures
expression21 has no printed infinity upper limits (confirmed by direct original-PDF
crop), although Max claimed they were visible and added two to the working edition.
This may be an editorial clarification but is not an observed OCR omission. The
Spectral nu-to-u proposal targets a nonexistent anchor: actual TeX has newline then
u, matching the original u(r). No source/selected output was altered during collection.
Both High and Max detected the artificial sign error; High lacked required evidence
fields, so non-application must not be reported as missed detection. The separate M
proposals require distinguishing print, correct local algebra and literal replacement.

The new self-contained collection contains a report, ChatGPT handover, all selected
editable text/assets/reading PDFs, per-arm outputs/findings/diffs/builds, original
source pages, reconstructible exact requests without repeated base64, and all call
metadata/timings. Long reasoning/wire records remain at recorded paths/hashes.
See results/image-review-recovery-chatgpt-current.json for verified ZIP path/size/hash.
Recorded890-test evidence reused; no tests, model calls, OCR, compilation, service
operations or queue changes for packaging. Broad High/selective rollout deferred.

## 7 November 2026 — library-first implementation, reconciliation and preparation

Read Codex-Library-First-Pipeline-20261107.txt in full. Conversion workers were
finished, writer locks released and GLM had zero active requests. The remaining
start-codex-supervision-task.py process is the old session launcher waiting on its
child, not a conversion worker; it was left alone. No model service was changed.
The prior bound implementation is preserved under
results/library-first-development-20261107/previous-code with hashes.

Image review now rejects non-object JSON and null/non-object findings before
attribute access. The actual finish path records invalid consumed reviews and
continues independent work. Shared evidence/format fields match the final response
example; exact anchors/hash/ranges remain. Literal TeX is a separate text part,
not an escaped draft string. Scope-completion/additional-findings attestations and
pending suggestions propagate separately from successful response/build status.

Saved CF corrections: M=sqrt(b^2-4ac)/(2c); nu>-1/2 in sums(b); seven mapped
o/rho/varrho transcription errors become source Latin g, preserving correct g.
Mixture21 infinity remains an editorial clarification, with the false printed-
source assertion rejected. Contradictory old notes are superseded, preserved in
before/diff records. Spectral's already-correct u(r) stays; duplicated n! corrected
from phi=A_n psi. Only the changed two assemblies were compiled, both passed.
Prior eight Spectral corrections and P-values figure repair remain unchanged.
Historical failed reviews/allowances remain; direct checks are not whole-paper proof.

Actual library reconciliation:63 originals =30 ready working sources +28 partial
+5 deferred/excluded (four arXiv deferrals and Cooking). All identities, selected
TeX/assets and generation manifests checked.27 ready generations reused; three
new CF/Spectral/P-values generations published through source_library. Five
partial experimental supplements catalogued without changing current selections.
Sources: /home/mdi/llm-wiki/sources/LIBRARY-FIRST-INDEX.md; JSON status and
LIBRARY-HANDOFF.md adjacent. Current bounded source assessments distinguish
resolved/rejected findings from raw historical pending counters. Program-generated
READMEs refreshed with guards; existing vault, old index, originals and user edits
preserved. No complete-Markdown/wiki-accuracy claim; no importer discovered beyond
the legacy tools/llm.py helper.

New finite local path: pinned installed Pro -> High conversion -> High original-
image review (Max explicit) -> coverage/assets/isolated build -> per-paper immutable
publication. Uses existing scheduler/locks/transport/compiler, maximum2 requests,
2048/16384/50 image limits, finite one-attempt phases, no overall deadline. Useful
completed conversions are refused for blanket reconversion and stay on the
reconciliation/repair path. Oversized indivisible source sections report explicit
scope blockers instead of clipping. Pro input schema and frozen runtime/compiler
contracts are guarded. Simple deterministic syntax recovery reuses existing code.

Mathpix/Kimi bridges exercised with saved/mock responses only.0USD new budget,
paid routes disabled. Scoped proposals preserve exact identities; provider ledgers
plus a separately approved run cap prevent duplicate/uncertain resubmission.
Direct Mathpix TeX can use the existing isolated compiler without GLM rewriting.
Actual paid launch still needs exact scope/new budget and current route/privacy/
price/live-allowance qualification. No credentials read or paid calls made.

Final required suite:910 tests in244.114s,4 optional skips; current code/test identity
match recorded in normal-terminal-checks.json. Installed CPU preprocessing verified
the new literal-TeX/image request (5588 image rows), with no model inference.
Pinned Pro runtime image presence confirmed on peer; no installs/downloads.

Prepared run: runs/library-first-20261107T170900Z-prepared. It has0 calls and is NOT RUNNING.
The proposed small next batch is Implied_Vol_Lee27pages, Path Integrals and SDEs35,
and BoyarchenkoLevendorskii_eigenfunction_MF_07 38:100 frozen pages,0 compatible
saved Pro pages and no usable completed conversions to replay. Their three old
failed calls remain linked. Exact GLM units/tasks are derived and sealed after Pro
extraction, before dispatch. Earlier zero-call preparations remain preserved in
linked preparation records, with all prepared source images copied unchanged.
No new full-paper inference or production-corpus resumption was performed.
See docs/LIBRARY-FIRST.md for exact controls and remaining limitations. All changes
unstaged; no commit, push, branch/index/history changes.

### Final library-first checkpoint,7 November

Final required suite:912 tests in243.560s,4 optional skips, matching final code/test
identity. Later publication integration checks also cover refreshing the machine
source index per settled paper, preserving edited README/index prose, refusal of
stale preparations after another run publishes/attempts a source, and idempotent
reuse of an already sealed delivery after interrupted publication. Prior test
records/logs and zero-call preparations remain preserved.

Final selected preparation: runs/library-first-20261107T174623Z-prepared.0 model calls; no
worker launched. All100 physical page counts were cross-checked against the actual
PDFs; prepared image/assessment bytes were reused in the linked final preparation.
The future launcher verifies current library selections before dispatch and cannot
use a fresh run name to reset an existing library-first attempt.

The three selected library generations and five partial supplements were reverified
against their seals. Current direct assessments distinguish superseded/rejected
model proposals from remaining questions without rewriting immutable generations.
Normal-terminal launch/status/resume commands and code/source evidence are in the
new compact inspection package pointed to by results/library-first-inspection-current.json.
No new inference, extraction, paid call, service change or Git operation was performed.

## 7 November — targeted library pre-launch planner and bundle corrections

Selected preparation library-first-20261107T191405Z-prelaunch-546226 links the previous never-started preparation; source images, all100 pages, High/High settings, two-request/image limits, disabled paid routes and historical consumption are unchanged.0 calls, no worker launched. The new refresh-prepared command refuses started/consumed plans, copies verified inputs and retains the parent intact.

Long heading sections now split at safe paragraph/mathematical boundaries. Native equations, conditions, figure/caption groups, definitions/context and theorem/proof chains are retained. Oversized indivisible spans are recorded with exact region IDs/pages/text/hash and remain outstanding while safe units proceed. Included plus outstanding ownership is complete and unique; outstanding spans prevent complete-paper/ready promotion even when produced parts compile. Saved Spectral6–6.3 dry planning accounts for all130 regions in four safe units without inference.

Final/manual bundles include selected/candidate TeX and required assets, available reading PDFs, final responses, review findings/diffs, compiler diagnostics, per-paper status and timing summaries, original-page images for flagged/outstanding passages, missing-artifact and omission lists. Credentials, weights, environments, long reasoning and repeated wire/base64 are excluded. Snapshots preserve earlier reports and verify CRC/all member hashes.

Validation:32 focused tests passed; full required suite922 tests,4 optional skips,248.547s, current code/test identity matched. Tests cover five-page sections, preserved proofs/equation/figure groups, outstanding accounting/context, no false complete promotion, actual bundle contents/hash checks, and zero-call linked preparation guards. These are code/fixture checks, not a new model benchmark or claim of runtime conversion accuracy. No inference, OCR, compilation, service/permission changes, paid calls, Git staging/commit/push or library source edits.

## 7 November 2026 evening — content-first library, author intake, no launch

The controlling instruction is Downloads/Codex-Wiki-Source-First-2026-11-07.txt,
read in full. The old zero-call100-page preparation remains unchanged. New linked
preparation: `/home/mdi/projects/pdf-to-latex/runs/library-first-20261107T212314Z-prelaunch-115000` (pointer results/library-first-batch-current.json).
It contains only Implied_Vol_Lee27 and Boyarchenko multi-factor38 pages:65 total,
zero calls/launches. High conversion/High original-image review, max2 requests,
131072 completion allowance, unchanged2048/16384/50 image limits. Compile_pdf is
false, paid routes disabled0USD, no deadline. Exact coherent scopes/finite tasks
are sealed after extraction before GLM reservation; outstanding content prevents
complete status. No OCR, inference, paid request or service operation was launched.

Library /home/mdi/llm-wiki/sources now has43 useful PDF entries,19 partial,1 excluded
(Cooking). Fifteen author packages were imported for16 PDF identities; the two
Homescu PDFs are one work, with identical native text and rendered pixels on all40
pages despite different file hashes. Total known works62, useful subset42. Nine
imports correspond to original versions, six are explicitly alternative, and
Bayer/Breneis correspondence remains unresolved. Noether Tavel translation is not
Delphenich. Alternative text does not claim coverage of the original PDF. Raw
sources/packages, macros, bibliography, figure assets, original PDFs and all prior
selected generations/history are preserved. Only targeted0906.0103v4 was downloaded;
the350-paper audit remains deferred.

Four saved texts are promoted despite historical build failure: Market_Generator,
Liu Slides with option bounds, Markovian_Projection and smoothing. Their complete
assigned content/portable assets remain unchanged; mathematical corrections are
not thereby certified. Other partial content/coverage/damaged-math issues remain.
Library preparation, preflight, saved version selection, publication and reporting
now use substantive content checks independent of optional compilation. Builds are
off by default; not_requested is distinct from failed. Source identity, exact edits,
missing assets/includes, truncation, outstanding scopes and uncertain-call/replay
safeguards remain. Earlier book-edition/compiler workflows are unchanged.

Validation:49 focused checks passed. The required normal-host suite passed939
tests with4 optional skips (248.019seconds), matching the linked plan code/test
identity. The first sandbox run had15 loopback-socket permission errors; preserved
as environment-restriction evidence, then passed outside the sandbox. All20 new
library generations, selected pointers and content/asset hashes reverified.

Evidence: results/wiki-source-first-20261107 (REPORT.md, author-imports,
reassessment, publication, source/version/figure/dependency records). The current
inspection and exact size are indexed by results/wiki-source-first-current.json.
Both current wiki Markdown files are included in the inspection. Code remains
unstaged. No staging, commit, push, branch or other Git mutation.

Future launch (not executed):
```bash
bash /home/mdi/projects/pdf-to-latex/scripts/run-library-first.sh run --run /home/mdi/projects/pdf-to-latex/runs/library-first-20261107T212314Z-prelaunch-115000 --allow-owned-handoff
```

## 8 November 2026 — productive paper queue prepared, not launched

Current run: `/home/mdi/projects/pdf-to-latex/runs/library-overnight-20261108T040405Z`. Active pointer:
results/library-first-batch-current.json. Parent
runs/library-first-20261107T212314Z-prelaunch-115000 remains unchanged, with zero
calls/launches. The new preparation also has zero calls/launches.

Library:56 useful PDF identities (55 works),6 partial,1 excluded. Thirteen saved
research papers covering314 original pages were reconciled without inference.
Specific saved corrections and targeted flag dispositions are in
results/library-overnight-20261107/promotions and REPORT.md; originals, prior TeX,
failed builds, unresolved claims and review limitations remain. All63 originals,
library copies and selected-generation seals were reverified. Content readiness
is not mathematical certification; author-version distinctions remain explicit.

Finite queue: Smile Risk missing333 blocks on pp16–25, retaining332 completed
blocks; Lee27pages; Boyarchenko–Levendorskii multi-factor38pages; appeigenfunction
39pages.104 new MinerU Pro pages plus the10-page missing scope using saved native
extraction. Smile has5 coherent new units. Other units/allowances are sealed after
extraction before GLM admission. High conversion/High original-image review,
max2 local requests, unchanged image limits, compilation disabled, no deadline.
Matrix norms and Kai lecture/presentation material are out of overnight inference;
Cooking remains excluded. Ready sources are not reconverted;350-paper audit deferred.

Both recovery routes are connected and armed under ONE combined7USD new-spend cap:
Mathpix subset submission -> existing ID polling/download -> source/asset/page
validation -> direct adequate TeX or coherent downstream conversion/review;
Kimi K3 exact source/draft/images -> validated separate derivative -> publication,
with recovered conversions receiving their planned local review. No extra budget
per provider/paper/restart. Exact scopes register under frozen source approval;
immutable shared reservation proofs prevent reset. Unknown charges stay reserved;
only provider-confirmed actual costs settle. Current route/private allowance checks
occur at dispatch. No credentials were read or paid requests made in preparation.

Raw response seals now remain immutable: derived accuracy/findings/diffs are in
call-results/ with state-bound hashes. Resume uses the real request-binding and
shared-failure checks before settlement; transport faults cannot turn into paid
content retries. Partial recovery uses new sibling delivery directories and
immutable generations; crash after selecting a recovery generation before controller
checkpointing resumes its exact expected publication. Pause blocks new admissions
and drains owned reservations; finished resume is inert. Reused historical reviews
are not relabelled as new full-scope image reviews.

Validation:968-test required suite passed (4 optional skips),255.213seconds,
matching final code/test identity.61 focused library checks,38 Kimi checks and8
Mathpix checks passed. Mocked transport/resource observations; no live inference,
paid plumbing test, new compiler build, service operation or model download.

Exact operator launch (NOT executed):
```bash
bash /home/mdi/projects/pdf-to-latex/scripts/run-library-first.sh run --run /home/mdi/projects/pdf-to-latex/runs/library-overnight-20261108T040405Z --allow-owned-handoff
```

Status/pause/resume/bundle use scripts/run-library-first.sh with --run above;
resume includes --allow-owned-handoff. Tmux:pdf-library-first. Log:terminal.log;
progress:progress.json. Inspection pointer:results/library-overnight-current.json.
All changes remain unstaged; no commit, push, branch or Git-index change.

## 8 November 2026 — overnight results collected (no retries)

Run library-overnight-20261108T040405Z finished07:16:47 UTC after154.25minutes.
All four deliveries remain partial/unselected at paper level.103 Pro pages
completed; the only failed page is genuinely blank Boyarchenko p38, which blocked
its downstream planning.46 local responses completed, including2 unusable conversion
answers and5 invalid review answers;16 Kimi responses recovered useful derivatives.
Two further Kimi reviews were blocked by the inherited16-call gate, not the7USD cap.
Confirmed Kimi cost1.219735230USD; total shared exposure2.680224254USD including
held pre-dispatch reservations and a0.005USD Mathpix estimate. No allowance changed.
Lee/Smile/caption checker false positives and17 repeated Smile equation tags need
reconciliation. appeigenfunction has53 genuinely outstanding source blocks on pp8–13.
Compilation was not requested. Library counts remain56 useful,6 partial,1 excluded.
Inspection pointer: results/overnight-results-review-current.json. Report:
results/overnight-results-review-20261108/REPORT.md. Packaging/assessment only;
no inference, service changes, code fixes, tests or source promotion during collection.


## 8 November 2026 — revision 2 recovery and exact next 30 (validation in progress)

Authority: `library-next30-20261108-fresh7-v2`, verified against the downloaded
REVISION 2 package. The exact selected30 hashes and archive members were checked
against the existing master archive/intake:397 pages, Kienitz first. No replacement
papers or new source search. A fresh combined7USD allocation is registered once
under results/library-allocations; previous spending and unresolved holds stay in
their original lineage and remain relevant to real account/key allowance. No old
unused capacity or released hold increases the new7USD.

The completed overnight parent remains unchanged.24 saved units are reused across
Smile, Lee and Lewis;103 completed Pro pages are copied with hash manifests.
Smile output seams are reconciled throughA44/A45 andA60/A61 with originals/diffs
retained; A47[f-K]+ is confirmed against the printed source. A59c is source-bound
coverage adjudication. Lee's escaped date linebreak no longer starts false math.
Actual table captions and journal furniture are distinguished from missing source
headings. Boyarchenko's physicalp38 is independently all-white with no text, image
or drawing objects. All37 substantive pages remain eligible without repeatedOCR.
Appendix headings now end prior proof groups; proofs remain intact. Lewis's exact
53-block missing passage receives a source-bound6-page exception, unchanged image
limits and mandatory live admission. Other prior Lewis units/reviews remain.

New registered paid phases remove the hidden legacy16-call gate only for this
authorization. Shared reservations, provider/key limits, uncertain charge retention,
no-send evidence and resume guards remain. Two old pre-POST holds are reconciled
in immutable external events; no provider refund or old ledger mutation is claimed.
Mathpix/Kimi remain conditional, one attempt per eligible scope/phase. Paid denial
does not stop independent local work. High conversion/High image review,131072
completion allowance, at most2 local requests; compilation disabled.

Focused checks passed; the required repository suite is currently running. New
execution is not yet claimed. Active preparation pointer: results/next30-current.json.
Development/evidence: results/tasks/next30-20261108T102340Z. Source/code changes
remain unstaged. No Git metadata, models, permissions or global configuration changed.


## 8 November 2026, 11:42 UTC — revision2 next30 batch RUNNING

Observed persistent worker PID1771618, tmux `pdf-library-first`, run
`runs/library-next30-20261108T113644Z`. Final982 repository tests passed with4
optional skips (256.676s), matching final code/test identity in the run's
normal-terminal-checks.json. The authorized wrapper was executed by Codex.

Smile Risk and Lee were published as new immutable working generations from
saved sources, without inference; library58ready/34partial/1excluded after
registering the exact30new PDFs. Boyarchenko and Lewis recovery remain queued.
The owned idle two-node GLM service was stopped through its existing helper;
MinerU Pro is loading in the qualified peer container for397new pages, Kienitz
first.103 old successfulOCR pages remain reused. Fresh7USD exposure is0 so far.
Extraction and restoredGLM stages continue unattended; no production queue follows.

Main log: `runs/library-next30-20261108T113644Z/terminal.log`. During peerOCR,
detailed live log: `host-operations/pro-extraction-1794138176597142722.log` under
that run. Durable peer page state: `/home/mdi/projects/pdf-to-latex-comparisons/
library-next30-20261108T113644Z/outputs/mineru_pro/state.json`; the head collects
it after the phase. `progress.json` tracks controller/publication/paid state.
Use `bash scripts/run-library-first.sh status|pause|resume|bundle --run` with
this exactrun; resume requires`--allow-owned-handoff`. Finished resume is inert.
The code is now bound to the worker: do not edit it underneath the active run.


Verified peer observation 2026-11-08T11:47:20Z: {'completed': 23, 'running': 1} out of397new pages. Kienitz all7pages completed; independent second paper progressed. No new local downstream/paid calls yet. Existing regularGLM will be restored by the owned controller afterOCR.


## 8 November 2026 — local code checkpoint and committed-tree export

The user explicitly authorizes staging and one normal local commit, superseding
the earlier working-tree-only rule for this checkpoint. No push is authorized.
The active next30worker binds file contents, not HEAD; no commit hooks or content
filters are active. Current code/test hashes still match the982-test successful
validation (4optional skips). Only small static checks are repeated.
See docs/CODEBASE-REVIEW-20261108.md for scope and exported-test limitations.
No active code/settings, workers/services, plans, generations, ledgers, locks or
pointers are changed. The historical root task-instruction note stays untracked.
