# Supervisor bootstrap denial and independent ordinary-run continuation

## What actually failed

The saved qualification
`results/supervision-hardening-20261030/qualification-1793390329959254879/`
passed its user-service resource gate and parsed the explicit permission-profile
argument. Its boundary log contains:

```text
bwrap: execvp /home/mdi/.codex/packages/standalone/releases/0.166.0-aarch64-unknown-linux-musl/bin/codex: Permission denied
```

Bubblewrap could not execute Codex's internal bootstrap executable **inside the
new sandbox**. The Python boundary harness did not start; its output directory is
empty. This command does not invoke Docker, and the evidence does not establish
a Docker setup problem. No repair-model request was dispatched.

The outer Codex process had already run far enough to construct/invoke bubblewrap.
Read-only inspection finds the executable statically linked for ARM64, mode0755,
with searchable ancestors and execute access outside the failed sandbox.
`codex --version` succeeds and reports0.166.0. Changing the ordinary file execute
bit is therefore not supported by this evidence. The visible inspection namespace
does not show a noexec mount, but it is not the failed sandbox's mount table.

The saved permission configuration denies the broader Codex home while explicitly
allowing read access to the exact runtime binaries beneath it. Current official
[permission documentation](https://learn.chatgpt.com/docs/permissions) says a
more-specific rule can reopen a path inside a broader deny. Thus the parent deny
alone is **not sufficient proof** of the cause, and removing it or allowing the
whole home directory would be an unjustified workaround.

**Precise remaining blocker:** the executable is denied at the sandbox bootstrap
step; available evidence does not identify whether the generated mount/access
layout or a host execution policy such as AppArmor supplied that denial. The
read-only sandbox-log and kernel-journal searches returned no additional matching
records in this inspection environment. That absence does not rule out a host
audit event. No narrow, proven application correction or host configuration change
has been identified, so neither permissions nor runtime code was changed.

For independent ChatGPT review, the ZIP includes the exact failed command,
requested permissions, resource observations, failure log and current implementation.
The useful next evidence is the generated bubblewrap mount/argument plan and any
host audit denial for this execution, including the runtime executable's effective
path/mode inside that namespace. Do not change Docker groups, chmod the runtime,
disable host security controls or broaden the profile on the strength of the
generic wrapper message. Automatic supervision remains disabled.

## Ordinary experiment: verified independently

The actual pointer resolves to
`runs/overnight-suite-20261030T085252Z-fae4ce`, status `prepared_offline`.
The real `scripts/speed_suite.py:verify()` passed: current code bindings, frozen
manifest/tasks, input/consumed hashes, saved call seals/request hashes, inherited
call accounting and all registered version hashes match.

All seven calls are settled: one historical readiness and six Stage A critics.
Stage A is `finished_for_inspection` (five revised, one findings-only). There are
38 pending work requests: B4, C8, D26. No call is in progress, the project/run
writer locks are free, and no pause/stop flag is present at inspection.

The ordinary wrapper invokes `scripts/speed_suite.py --overnight`. Its resume
action calls the existing launcher directly; it does not import or qualify the
supervisor and does not call Codex/bubblewrap. It skips completed Stage A, retains
all consumed calls, refuses uncertain in-flight reservations, and admits only
pending frozen work. Completion remains terminal with no production fall-through.

43 relevant offline tests passed: seven saved-response/finalization regressions,
13 overnight-suite tests and23 resume/scheduler tests. They include deterministic
threaded traversal of the remaining38 fake requests without repeating the seven
inherited calls, pause/resume accounting and terminal zero-request behavior.
Compilation/transport stubs in those tests are not live runtime qualification.

Normal-terminal continuation:

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-overnight-suite.sh resume --run runs/overnight-suite-20261030T085252Z-fae4ce
```

This ordinary launcher performs its existing once-per-identity full tests,
Docker/peer/model/workload/compiler checks and one fresh readiness before pending
work. Low verification and other frozen admission/skip policies remain in force.
It requires no supervisor qualification. Those live checks were not launched
here; no new GLM request, queue start, service change or allowance reset occurred.
It runs persistently in tmux and has no automatic Codex repair supervisor attached.
