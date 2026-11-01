# Fresh Codex handover — 30 October 2026

**Boundary hardening now supersedes activation:** follow the current
[supervision runbook](OVERNIGHT-SUPERVISION.md). Only `qualify-only` is available
for execution checks; automatic promotion/start/resume/link/worker paths refuse.
The original finite-suite authorization is retained for a later explicit start
after review. Do not rerun Phase 1 setup, change permissions or bypass these gates.

**Later fresh-session result:** the requested fresh session has run. See
[OVERNIGHT-SUPERVISION.md](OVERNIGHT-SUPERVISION.md) and the latest PROJECT-STATE
entry for its runtime evidence, independent repair review, implemented supervisor,
tests and blocked real qualification. Do not repeat the installation/fresh-session
handoff below. No overnight or production worker was launched. The remaining
normal-terminal qualification/activation command is in that runbook.

The controlling task is `/home/mdi/Downloads/Codex-configure-review-and-supervise-20261030.txt`.
Read it **in full**. It authorizes three ordered phases: configure/verify a fresh
Codex session; independently review the completed overnight repair; implement and
qualify a narrowly scoped persistent supervisor. It preserves the suite's final
stop and never authorizes starting the separate production Bergomi queue.

## Restart boundary and Phase 1

The preceding session could read, but could not write, `/home/mdi/.codex` or the
standalone installation. It did not attempt to bypass that restriction. The user
explicitly requested one operator command that applies the configuration and opens
a fresh session with the remaining task already supplied:

```bash
cd /home/mdi/projects/pdf-to-latex && .venv-control/bin/python scripts/start-codex-supervision-task.py
```

This helper uses the installed **`codex update`** stable self-update route, checks
the resulting executable/version and existing ChatGPT login, refreshes model
metadata, and writes only the dedicated
`~/.codex/pdf-to-latex-supervision.config.toml` profile. An existing profile is
backed up with its access mode preserved; unrelated entries/base configuration
remain intact. It records the old executable for rollback and uses `--no-daemon`
for the new interactive session. It does not restart or replace a running shared
daemon, select a premium speed tier, change permissions, or copy authentication.
The record lives in the actual `results/codex-setup-<timestamp>/setup.json` printed
by the helper, not an invented preflight directory. An existing setup session is
protected by an advisory lock. No book worker is launched by this helper.

Preferred requested settings: `gpt-6-astra`, `xhigh`, 800000 nominal tokens,
automatic compaction at 650000 **total**, ChatGPT authentication only. They are
conditional on current catalog support; below that range the helper retains the
catalog's supported default window with an explicit lower threshold. It does not
patch model metadata. It preserves the model and effort. Profile syntax is a
separate `<name>.config.toml` file, not the old `[profiles.name]` syntax.

**First action in the fresh session:** verify THIS session's runtime model,
reasoning, auth mode, actual effective context and compaction scope/threshold,
executable and local server identity. Read the setup record path supplied in the
initial prompt. Do not repeat the updater or create another fresh session if this
one is already correctly configured. The requested 800000 × catalog factor 95%
suggests 760000 effective, leaving 110000 after the chosen threshold, but these
are expectations, not runtime observations or a guarantee for a maximum-size
tool/output turn. If measured limits differ, use a supported working setting and
record the limitation. Do not manufacture a large context test. Record
`long_context_exercised: false`. Then proceed with Phases 2 and 3 in order.

Read-only observations at 09:32–09:40 UTC, before applying the helper:

- CLI path `/home/mdi/.local/bin/codex` resolves to
  `/home/mdi/.codex/packages/standalone/releases/0.163.0-aarch64-unknown-linux-musl/bin/codex`.
  `codex --version`: 0.163.0. Native standalone installer, not npm.
- `codex login status`: ChatGPT; only the mode was retained, no auth file read.
- Global config selects gpt-6-astra/xhigh, without context/compaction overrides.
  No project `.codex/config.toml` or existing dedicated profile was found.
- Current cached and bundled model metadata: default272000, maximum872000,
  effective-context percentage95, xhigh supported,
  `supports_experimental_context=false`. The maximum is not the public API limit;
  the boolean alone does not establish how an explicit nominal override is capped.
- Prior runtime audit of thread `01a15101-7f9d-7952-b256-dbf50c13a489` measured
  effective258400, auto-compaction244800, `Total` scope. This existing session did
  not become larger when a future profile was prepared.
- 0.165.0/0.166.0 app-server packages are installed. Cache refresh version changed
  between0.166.0 and0.163.0. Neither identifies the running shared daemon. Its PID
  record names267581/startTicks121550870; that host process is not visible in this
  sandbox PID namespace. Do not claim its executable version is verified.
- Installed help confirms `update`, `--profile`, `--no-daemon`, `--strict-config`,
  `exec --json`, `--output-last-message`, `debug models`, and `login status`.
  A normal-terminal fresh process is required; no update/profile activation was
  performed by the preceding sandboxed session.

Official references checked against installed help:
[configuration precedence](https://learn.chatgpt.com/docs/config-file/config-basic),
[profile/context keys](https://learn.chatgpt.com/docs/config-file/config-reference),
[self-update and session-local CLI](https://learn.chatgpt.com/docs/developer-commands).
CLI flags override trusted project config, then selected profile, user, managed,
system and built-in defaults. Inspect effective runtime rather than assuming the
profile wins over every layer.

## Actual overnight state at the handoff

Rediscover `results/overnight-suite-current.json` and ownership before editing;
these observations are a snapshot, not permission to disregard a later writer.

- Pointer: `runs/overnight-suite-20261030T085252Z-fae4ce`.
- State: `prepared_offline`; project lock free, run lock absent; no worker visible
  in this session. Seven calls inherited; A has five `critic_revised`, one
  `critic_unchanged`; B/C/D still38 pending. No requests started by this task.
- Parent: `runs/overnight-suite-20261029T233239Z-708fe8`, unchanged failed evidence.
- Current report: `runs/overnight-suite-20261030T085252Z-fae4ce/report.html`.
  Current ZIP is in that run's `last-inspection.json`. `terminal.log` starts only
  upon actual worker launch.
- Production pointer names a separate paused queue. Never resume it as a suite
  completion/failure action.

The prior repair remains in the working tree. Its claims must be independently
reviewed, not automatically trusted:

- `scripts/editorial_chapters.py:finish_task` uses a `recorded_replacement` flag
  for both version registration and compilation; findings-only prose retains its
  actual draft/annotation; incomplete/ambiguous TeX remains unusable.
- `probe/speed_suite.py:EFFORT_CHECK` uses `inspect.unwrap` for source inspection
  and the original installed cached callable for actual template rendering.
- `scripts/overnight_suite.py` contains `reconcile_findings_only`,
  `compile_local_recoveries`, `prepare_continuation`. The existing linked-repair
  constructor is specific to the original seven-call/Stage-A failure; do not
  assume it already supports every future supervisor incident.
- `scripts/speed_suite.py` verifies inherited evidence; `probe/chapter_concurrency.py`
  retains coordinator tracebacks. Worker exceptions can still exit0, and the tmux
  launcher exits before the actual worker. Supervision must monitor actual state
  and process identity, not just those exit statuses.
- `tests/test_overnight_repair.py` has real saved-A replay, lru_cache, idempotent
  local recovery, threaded fake B/C/D traversal and terminal-no-op regressions.
  One exact saved-response fixture is under `tests/fixtures/overnight-findings-only/`.

Recorded checks (reuse where applicable; distinguish from your independent review):
historical operator full tests617 OK/skipped4. Prior repair full suite624 in218.137s:
605passed,15 mock-loopback socket PermissionErrors,4 optional compiler skips, zero
assertion failures. Log in the prepared run's `repair-offline-tests.log`; details
`repair-validation.json`. Read-only Docker probe was denied at docker.sock in this
sandbox; normal-terminal Docker had previously compiled5 replacements and3 local
repairs. Do not infer an account/group defect or relax permissions.

All current source and untracked implementation files are authoritative. Preserve
unrelated edits, including `pdf-to-latex-codex-next-step.txt`. AGENTS is unchanged;
no staging/commit/push or other Git mutations. This handoff adds only the Phase1
setup helper/tests/docs; no bound controller code or run evidence was changed.

## Remaining work, in order

1. Verify this fresh profile/session as above; do not attribute past bugs to
   compaction without evidence.
2. Independently review both repair paths and actual saved responses/controller
   transitions. Preserve prior outcomes; run meaningful checks for resulting code
   identity. Read the full controlling file for required cases.
3. Audit capabilities without secrets. Implement the small independent supervisor
   with latched pause/stop, two persisted repair attempts per incident, separate
   dev copies and programmatic patch scope, fixed verification helpers, baseline
   conflict protection, linked continuation, no completed-call replay and no
   production fall-through. Keep policy outside repair-agent editable scope.
4. Qualify with deterministic tests AND one real `codex exec` disposable fake-model
   end-to-end recovery. A mocked Codex response is not qualification. If access is
   denied, finish offline work and give one exact operator qualification/launch
   command; no permission changes or hidden approval prompt.
5. Only then arm/continue the authorized frozen suite. Distinguish IMPLEMENTED,
   QUALIFIED, ARMED, RUNNING. Keep every original response, task and scope boundary.

Do not launch the old worker just to make progress before the requested review
and supervision qualification. User requests the complete three-phase task, not
another manual repair-only loop. Phase1's required restart was the sole reason
the preceding session stopped here.
