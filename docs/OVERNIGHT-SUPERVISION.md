# Overnight supervision — hardened review gate, 30 October 2026

**UNARMED. Automatic promotion and activation are disabled. Runtime qualification
has not passed.** This supersedes the earlier launch instructions. The existing
authorization for the finite overnight suite is retained for a later explicit
start after review; this hardening task does not exercise it.

**Ordinary-run separation:** the user has now explicitly requested independent
continuation through the repaired [ordinary overnight runner](OVERNIGHT-WORKFLOW-SUITE.md).
Supervisor qualification is not a prerequisite for that run. The disabled
activation routes here concern automatic supervision; they do not disable the
ordinary runner or its existing safety/admission checks.

The prepared suite remains runs/overnight-suite-20261030T085252Z-fae4ce:
seven recorded calls and 38 pending requests. State, binding, completed evidence
and the separate production pointer remain unchanged.

## Qualification-only command

Run from a normal terminal:

    cd /home/mdi/projects/pdf-to-latex && bash scripts/run-supervised-overnight.sh qualify-only --run runs/overnight-suite-20261030T085252Z-fae4ce

This command cannot arm supervision, start/resume a conversion worker, issue
GLM requests or apply a repair to live project code. It checks confinement,
then may invoke the existing ChatGPT-authenticated Codex for a disposable repair
using fake model transport. Passing produces a **fixture-only** release and patch
for review, not approval to execute that patch with host permissions.

The controller refuses user-service launch from a Codex tool session. This keeps
the service manager from becoming a way around the outer interactive sandbox.
No administrator action or permission relaxation has been established as necessary.
If normal-terminal checks fail, retain the diagnostic and stop; there is no
ordinary-host fallback.

These controls remain available:

    bash scripts/run-supervised-overnight.sh status
    bash scripts/run-supervised-overnight.sh pause
    bash scripts/run-supervised-overnight.sh disable

Pause and disable remain durable latches. Disable never kills healthy work.
The start, resume, activate, worker-entry, loop, link and former qualify actions
refuse before any dispatch or control mutation. There is no environment/CLI switch
that re-enables the removed host execution path. Only a later reviewed
implementation can provide live promotion/resumption.

## Execution boundary and remaining qualification

scripts/supervision_isolation.py is the single execution gateway for candidate
imports, finalization, existing/new tests and fixture execution after integration.
It uses the installed Codex permission-profile executor, backed on Linux by
bubblewrap/seccomp, inside a bounded transient user service. Both layers are
mandatory. The fixed host controller never imports candidate modules.

CLI 0.166 requires the sandbox invocation to select
`--permission-profile incident-only` explicitly; the generated default alone is
insufficient. The separate `--profile pdf-to-latex-supervision` model/config
selection is retained. The sandbox subcommand rejects `--strict-config`, so that
flag remains on exec and is omitted only from sandbox invocations. Argument
parsing does not establish runtime qualification.

The per-invocation profile denies filesystem access by default and lists code,
sanitized evidence, interpreter/dependency files and explicit system runtime paths.
Required project documents are included read-only; the current qualification
scope overrides their dated launch instructions. Raw runs/PDFs and credentials
are excluded from the repair snapshot.
It does not use broad workspace or temporary-directory grants. During repair,
only the two approved source files and private output/temp directories are
writable. Existing tests and policy remain read-only; new regressions are emitted
as separate data under private output, checked, then copied into a controller-owned
snapshot. Validation and fixture releases mount all candidate code read-only.
The agent cannot write the live checkout, original evidence or controller snapshots.

Client and tools have different environments. The Codex client keeps its existing
ChatGPT login and standard runtime storage/network needs. Tool environments are
explicit, with private HOME/TMPDIR and no inherited API keys, proxies, Python path
or SSH-agent socket. Apps, plugins, hooks, browser/computer use, web search,
memories, automatic agents and MCP configuration are disabled for repair.
The selected standalone executable and original model profile/base-config hashes
are checked; no Codex update or global config write is performed.

The transient service requests 4 GiB aggregate memory, no swap, 128 tasks,
NoNewPrivileges, no core dumps, and an FD/file-size ceiling. Controller output is
capped at 32 MiB; private trees are checked against 128 MiB/8192 entries with a
descriptor-based walk that does not follow symlinks. A fixed watchdog exits if
the controller's PID/start/boot identity disappears. KillMode=control-group and
post-exit unit checks account for descendants/background jobs. Test checks have a
600-second limit; **Codex generation has no wall deadline**, and no GLM
generation policy was changed.

These settings apply to disposable child processes, not global OS settings.
Their actual effect still needs normal-terminal qualification. The installed
CLI accepted the configuration; that is not proof of OS enforcement.
See the permissions matrix below.

The AST filter remains only a change-scope check. The unchanged current reporting
file, including its existing import statistics, now passes; additional imports
remain rejected. Source and regression size limits bound parsing.
The known run = run.parent example still illustrates why AST matching is not a
sandbox. Qualification executes that exact redirection in both validation and the
private post-integration path; OS write restrictions must reject it.

After the repair service and descendants stop, candidate bytes are copied into
controller storage outside the repair tool's grants. Validation mounts this
snapshot read-only. The fixture release uses those exact checked hashes, not the
mutable development directory. Baseline conflicts block integration. There is
**no live application/link/report/worker path for candidate Python**.

A trusted data-only transport/compiler interface for live operation is **not
implemented or enabled** by this hardening. The old host compiler/controller
calls are not exposed to candidate code. Fake finalization checks use explicit
compiler callbacks; they do not claim real TeX compilation. Live promotion remains
disabled rather than executing accepted Python with full host permissions.

## What qualification checks

All fixtures are disposable and use invented credentials and mock evidence.
Checks cover intended output/private temp writes, denied out-of-tree reads/writes,
immutable code/policy/tests/settings, inaccessible mock credentials/evidence,
no host TCP/Unix socket access, a private PID namespace, NoNewPrivileges and
clean environments. No actual credentials or live files are used as attack targets.

After these gates, real Codex may repair the small injected finalizer defect.
A new regression must fail against the broken baseline and pass against the
frozen candidate; fixed existing failure-path tests must pass without skips.
The candidate then runs in the same confinement after private fixture integration,
resumes only pending fake work, reaches terminal state and makes zero redispatch
on repeated invocation. Original calls/versions/queues are not regenerated.

The two-attempt incident ledger is preserved. The old failed exec already consumed
one attempt for the controlled incident; it is imported without resetting it when
the new path reaches dispatch. Failed environment gates before dispatch consume
no new repair attempt. No failed/skipped capability check is counted as a pass.

Raw evidence is under results/supervision-hardening-20261030/.
The small inspection pointer is results/inspection/supervision-hardening-current.json;
the compact inspection ZIP is also under results/inspection/.
There is no mandatory write to /home/mdi/Downloads.
Historical qualification and inspection records remain unchanged.

## Permissions matrix: observed versus proposed/tested

| Boundary | Proposed restriction | Actually observed/tested here |
|---|---|---|
| Candidate filesystem/network | Explicit named profile, read-only snapshots, private writes, no host sockets/network | CLI configuration parsing succeeded. Boundary fixture execution is blocked here; actual child restrictions remain unqualified. |
| Resources/process lifetime | Memory/task limits, private owned unit, watchdog, group cleanup | Construction/refusal/owner tests pass. User-manager access was denied; aggregate runtime limits and descendant cleanup are not live-qualified. |
| Linux isolation | Installed Codex/bubblewrap executor; no fallback | Tools discovered; nested namespace probe denied in this Codex environment. Normal-terminal availability is not inferred. |
| Codex auth/storage | Client retains ChatGPT login; tools cannot access auth/session storage | Earlier login observation retained. No new repair model turn launched. Exact startup-storage failure path remains unknown because tracing itself was denied. |
| Credentials/environment | No auth copy, explicit environments, mock-only denial fixtures | Allowlist/exclusion tests pass. Actual mock denial trials must pass before real exec. |
| Host capabilities after promotion | No arbitrary Python, shell, Docker or SSH bridge | Live promotion/link/worker routes are removed and reject calls. Private fixture integration still requires execution qualification. |
| Live queues/evidence | Read-only checks; no GLM readiness/dispatch | Seven calls, 38 pending requests and both pointers preserved. No inference or activation. |

This sandbox denied the user bus and namespace creation. File-syscall tracing
also failed with PTRACE_TRACEME EPERM, so no specific writable Codex storage
subpath can responsibly be prescribed. Do not infer that Docker group membership,
socket modes or global user-namespace settings need changing. Any normal-terminal
failure must identify its missing capability before administrator setup is
specified; none is applied automatically.

Final code/test results and hashes are recorded in PROJECT-STATE and
docs/evidence/supervision-hardening-20261030.json.
The initial 20-test report and failed v1 qualification remain historical evidence,
not qualification of this hardened implementation.

Mechanism selection was checked against installed 0.166.0 help/schema and the
official [permission profile documentation](https://learn.chatgpt.com/docs/permissions).
Client service traffic and local command permissions are separate surfaces;
the session-scoped environment/feature controls are documented in the
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).
