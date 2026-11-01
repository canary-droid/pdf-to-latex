# Supervisor permissions inspection — 30 October 2026

**Review snapshot, not qualification.** The implementation is unqualified and
unarmed. No permissions, services, inference or supervisor controls were changed
to prepare this pack. Read this report before treating the included runbook's
descriptions as demonstrated isolation guarantees.

## Exact command and what was effective

The saved qualification invocation, with cwd
`/tmp/pdf2tex-repair-wn3kfnnk/code`, was:

```bash
/home/mdi/.codex/packages/standalone/releases/0.166.0-aarch64-unknown-linux-musl/bin/codex --no-daemon --strict-config -a never --profile pdf-to-latex-supervision exec --sandbox workspace-write --skip-git-repo-check --json --cd /tmp/pdf2tex-repair-wn3kfnnk/code --output-last-message /tmp/pdf2tex-repair-wn3kfnnk/diagnosis.txt -
```

The final `-` reads the saved `handover.txt` on stdin. Exact argv, handover, stderr,
exit status, baseline hashes and fake-worker failure are included under
`evidence/qualification/`. Current code constructs the same argv with a fresh
temporary directory. `-a never` forbids interactive escalation; it does not grant
unrestricted access. No bypass flag, API-key fallback or alternate model is used.

The selected profile specifies gpt-6-astra/xhigh, nominal context800000,
compaction650000/total and forced ChatGPT login. Its permission settings are not
explicit: workspace-write and never come from argv. The inspected base config
contains no allowlisted sandbox/approval overrides; project config and
`/etc/codex/managed_config.toml` are absent. Selected safe fields, hashes and the
current session's exact permission record are in
`evidence/effective-permissions-observations.json`; raw config/auth files are excluded.

**No effective repair-child permission configuration was observed.** Exec exited1
with `failed to initialize in-process app-server client: Read-only file system
(os error 30)` before producing a repair thread. The recorded failure is not a
successful ChatGPT repair or sandbox test. Its exact failed state-file path is not
identified by stderr. The earlier attempt predates the final control hardening.

The *interactive inspection session* has an observed managed, network-restricted
policy: `/` readable subject to OS permissions; project root, `/tmp` and TMPDIR
writable; project `.git`, `.agents`, `.codex`, `.aws` read-only. Approval is
on-request. These are the parent session's settings, **not** the failed child's.
The supervisor checks child runtime records only after a successful exec returns;
that check is not a pre-execution access barrier or a complete mount/socket audit.

## Path and service access

| Surface | Intended repair-tool boundary | Evidence and limits |
|---|---|---|
| `/tmp/pdf2tex-repair-*/code` | Writable development copy, outside live Git ancestry | Source/argv establish intent; real child never started. The entire copy is writable, including copied tests and policy files. Rejected edits are prevented from application, not from being made in that copy. |
| `/tmp`, TMPDIR | Temporary writes permitted by accepted policy | Scope is broader than one repair directory, potentially including other temporary copies. Actual child mount roots were not observed; TMPDIR's value was not collected. |
| Live project, runs, sources, baseline snapshots | Read-only to repair tool commands; host owns mutation | Intended child boundary only. The parent interactive session can write the live project. Neither secret-file read denial nor a narrow read allowlist was demonstrated. Workspace-write must not be described as hiding all host files. |
| `~/.codex` / session storage | Codex runtime uses existing login and needs its normal session/state storage; repair shell tools should not need write access there | Parent exposes this area read-only; initialization was denied. Successful child session-storage access remains untested. No authentication file was read or packed. |
| Network | Repair-tool direct networking intended restricted; Codex client separately communicates with OpenAI | Parent GLM connection and mock-loopback socket creation were denied. Child network restriction, connector/tool surfaces and hostname reachability are untested. The client network path is not the tool sandbox's network path. |
| Docker socket | Repair-tool access intended unavailable; fixed host compiler/runtime helpers use Docker | Parent inspection and harmless compilation denied at docker.sock. This does not prove the child cannot access Docker, or establish a Linux group defect. |
| SSH / peer | Repair-tool direct SSH intended unavailable; host checks use existing noninteractive peer access | Parent BatchMode lookup of spark-92a4 failed DNS. Child SSH and normal-terminal peer access remain untested; no SSH credentials/settings were inspected or changed. |
| tmux socket | Host launches/observes persistent supervisor and worker | Parent socket connection denied with EPERM. Real detached-launch qualification remains outstanding. |

The subprocess wrapper inherits `os.environ`, adding only
`PYTHONDONTWRITEBYTECODE=1` (`overnight_supervisor.py:39`). It is **not an
environment allowlist**. The pack contains no secret environment values; whether
the future host environment contains secrets is deliberately not asserted.

## Host helpers and agent-controlled execution

The following run outside the **repair agent's** sandbox when the supervisor is
started from a normal terminal, with that user's host permissions (not sudo):

| Operation | Fixed entry/argument source | Agent influence |
|---|---|---|
| Login/version identity and Codex launch | Setup-bound executable/profile hashes; fixed `login status` and argv above | No command string from the model; profile hash checked, other inherited configuration is not exhaustively frozen. |
| Saved-response/fake-worker reproduction | Fixed controller Python + `scripts/supervision_checks.py`, modes `replay`/`fake-worker`; supervisor-created code/run/output paths | **Yes:** helper inserts the candidate on `sys.path`, imports its modules and executes its finalization/reporting code, before application. |
| Existing tests | Fixed `python -B -m unittest discover -s tests -v` in a validation copy; existing test bytes protected, new regression files removed for this run | **Yes:** unchanged tests import and execute candidate implementation with host permissions. |
| New regressions | `codex sandbox --profile pdf-to-latex-supervision --cd <copy> -- <fixed-python> -B <fixed-check-helper> regressions --code <copy>` | Intended sandboxed execution. These commands do not supply a separate explicit permission profile/network override; their effective sandbox was not observed. |
| Application/link/report/resume | Fixed policy, writer/development locks, baseline checks, file replacement, fixed `link` helper and overnight worker entry; tmux commands use `shlex.join` | **Yes after promotion:** permitted changes become live Python used by link/report/worker execution. |
| Runtime checks and GLM admission | Existing `arrange_glm(check_only=True)`, exact model/build/effort checks, fixed Docker/SSH/HTTP helpers and frozen requests | No agent-provided host shell command; bound data supplies run paths/assets. This path can perform authorized pending inference only after activation; none ran for this pack. |
| Compilation | Existing immutable-image Docker helper, fixed engine, validated assets; network=none, read-only image, no capabilities, no shell escape, limited resources, only disposable source/build mounts | TeX/assets are input data. Separate dependency provisioning, if reached, uses fixed allowed packages and Docker build with network=default. This is distinct from the isolated document build. |

**Answer to the central trust question: yes, the repair agent can modify code
that host helpers later execute, including during validation before promotion.**
Fixed executable paths and argv prevent a direct arbitrary-command return channel;
they do not confine Python imported from the candidate.

The patch filter allows only `finish_task`, `report`, `write_progress`, `bundle`
and new regression files. It checks inventory, symlinks/hardlinks, function scope,
existing tests, call-expression names, string constants and selected validation
calls. Twenty focused tests exercise these filters and control paths. They do
**not** prove that allowed Python changes preserve all checks, call arguments,
control flow or filesystem effects. The filter is not a security sandbox. Candidate
files are not made immutable before host execution; no separate OS account or
host capability broker is implemented. This host-execution boundary needs explicit
independent review/hardening, rather than being treated as solved by permissions.

## Tested status and minimum remaining action

Saved results: Phase2 seven tests passed; supervisor20 passed; full suite649:
630 passed,15 loopback EPERM errors,4 skipped. Real qualification detected a
zero-exit fake-worker failure, then failed at Codex initialization. No real agent
patch, host application, fake resume or successful isolated compilation followed.
The ZIP includes those records; no qualification or inference was rerun for packaging.

**No specific chmod, group, socket, global approval or sandbox-permission change
has been established as necessary.** The current outer sandbox cannot initialize
the additional Codex runtime. A separately authorized normal-terminal supervisor
would need normal access to the existing Codex session-storage area, Docker/tmux
sockets, peer SSH and local model endpoint. Those host capabilities must be checked
separately; granting them to the repair shell is not required by the design.
The narrowest failing Codex storage path is not known, so a broader write grant is
not justified by this evidence. Candidate-code verification confinement is a code
boundary issue, not a reason to relax permissions. No change is applied here.

Credentials, authentication files, whole configurations, shell snapshots,
environment dumps, session transcripts, raw book PDFs and large raw runs are
excluded. `MANIFEST.json` gives each included file's SHA-256, source and whether it
is an exact copy or a derived inspection record. This is an inspection subset,
not a standalone runnable installation or a claim of unattended qualification.
