# Sparse library observer

Implemented and qualified on the head Spark, 9 November 2026. **NO_ACTIVE_RUN;
not attached, no timer installed/enabled, no scheduled checkpoint.** The last
library worker was `runs/library-completion-20261109T072416Z-labels`, which finished
at 08:03:43 UTC. It must not be restarted to give the monitor a target.

This observer does not authorize or start a conversion queue. The archived
repair supervisor remains unarmed; its promotion and activation gates are unchanged.

## Operation and controls

Use the existing controller Python through this wrapper:

```bash
bash /home/mdi/projects/pdf-to-latex/monitoring/run-monitor.sh status
bash /home/mdi/projects/pdf-to-latex/monitoring/run-monitor.sh discover
bash /home/mdi/projects/pdf-to-latex/monitoring/run-monitor.sh check-once
bash /home/mdi/projects/pdf-to-latex/monitoring/run-monitor.sh pause
bash /home/mdi/projects/pdf-to-latex/monitoring/run-monitor.sh disable
```

After explicitly selecting the **next already-running authorized library run**,
attach using its exact absolute path, not a current-pointer filename:

```bash
bash /home/mdi/projects/pdf-to-latex/monitoring/run-monitor.sh attach --run /absolute/path/to/selected/running/library-run --activate
```

For a copy/paste command which asks only for that exact future run path:

```bash
read -r -p 'Exact already-running authorized library run: ' monitor_run && bash /home/mdi/projects/pdf-to-latex/monitoring/run-monitor.sh attach --run "$monitor_run" --activate
```

Attachment refuses finished runs, multiple workers, missing ownership, changed
plan/binding, changed monitor/runtime identity or missing qualification. It pins
plan/binding SHA-256, worker PID/start ticks and boot ID. It never follows a
subsequently changed current-run pointer. Reattaching the same running target
resumes a deliberate monitor pause; it cannot reset dispatch reservations or clear
an uncertain/authentication failure. Disable first before selecting another run.

`--activate` links/enables only `pdf-library-observer.timer` in the ordinary user's
service manager. The user manager must be available; no cron/tmux fallback or
linger/global configuration change is performed. Timer continuity after logout
or reboot depends on the existing user-manager lifecycle. Nothing is installed
until a valid target is attached. `pause` durably blocks future AI checks, while
health observations can continue. `disable` also stops this timer, never the worker
or an already-running checkpoint. `check-once` collects once and respects the
same qualification, cadence, gates and caps; it is not an unlimited manual AI call.

## Cadence and durable limits

- One cheap tick every 300 seconds (calendar timer; no missed-interval catch-up).
- Routine Codex checkpoint no more often than 7,200 seconds; at most 12 per
  rolling 24 hours. A simultaneous incident or terminal trigger takes precedence.
- At most four incident checks per rolling 24 hours and two for any incident key
  per run. An unchanged unresolved incident is not redispatched each tick. A
  second incident check requires an intervening observed resolution.
- One terminal assessment per run, with partial source coverage reported separately.
  Afterwards AI monitoring stops and the timer is stopped. Failed/uncertain final
  assessments retain `pending_final_report`; there is no automatic retry.
- One separately recorded real qualification call. There is no replay of it.
- A 30-minute no-progress diagnostic threshold (set at attachment with
  `--warning-seconds`). Recent stream/phase-log evidence prevents treating a long
  active request as a stall. Nothing is killed because this threshold expires.

All reservations are fsynced before dispatch. An exclusive monitor lock covers
a whole checkpoint; timer ticks cannot overlap it. A separate durable control
gate allows pause/disable during a long check. A crash leaves the reservation
consumed and blocks further dispatch pending inspection. Limits count calls,
not exact ChatGPT subscription consumption. Budget/hold values are **saved**
worker accounting with the saved timestamp; there are no provider queries.

## Context and permissions

Model `gpt-6-astra`, Low effort, Standard (`service_tier="default"`), existing
ChatGPT authentication. The installed CLI is 0.166.0. Development XHigh settings
and global configuration were not modified. Every checkpoint is fresh and
`--ephemeral`, with `--ignore-user-config`, explicit task-local overrides and
existing execution rules retained. No historical chat is loaded.

The model receives a sanitized allowlisted JSON snapshot of at most 12,000 bytes,
not PDFs, TeX, source text, images, requests or reasoning. Counts of omitted fields
are included. Installed Codex system instructions still add tokens beyond this
small snapshot; the real qualification used 10,205 input tokens (7,808 cached)
and 140 output tokens, with zero separately reported reasoning-output tokens.

The permission profile denies the filesystem root, granting read access only to
that check's evidence directory and explicit runtime binaries/libraries. It grants
**no writes and no network** to agent tools. Shell, browser, apps/plugins, MCP,
skill discovery, delegation and hooks are disabled. The fixed controller captures
JSONL output and the report; there is no agent-writable report or host execution
bridge. The authenticated Codex client itself necessarily uses its existing
session storage/network; those are not granted to agent tools. Auth files are
never copied. The model's prose is never interpreted as commands.

Permission-boundary qualification used a disposable canary and an existing local
listener: reading the canary succeeded; writing it, visibility of the real auth
file, reading live run directories and connecting to the listener were denied.
This demonstrates the tested boundaries, not exhaustive proof against every
possible runtime defect. Runtime grants for the ARM64 dynamic loader are explicit;
an initial narrower canary execution could not load Python and was preserved as
preflight failure evidence. No global sandbox settings were changed.

## Records and qualification

All monitor-owned mutable state is under:
`/home/mdi/projects/pdf-to-latex/results/library-monitor/`.

- `state.json`: reservations, caps, pinned target and qualification.
- `snapshot.json`: latest attached-run observation (created on attachment/tick).
- `discovery-snapshot.json`: read-only discovery of the finished historical run.
- `checks/<id>/report.md`, `events.jsonl`, `invocation.json`: report, usage and exact
  command/settings. Reports are local only; no ChatGPT post or phone notification.
- `qualification-evidence/`: actual resolver settings, model-support metadata,
  authentication type, tested boundary and executable identity.
- `focused-tests.log`, `REPORT.md`: validation and current handover.

The one real check ran in user service
`pdf-library-observer-qualification-20261109.service` at 22:52:49–22:52:56 UTC,
Codex thread `01a1c283-a58c-71c3-be08-c121ed41b5fd`. It returned a 76-word report,
exit 0, with no tool action. The first classifier rejected an `item.error` startup
notice about `skip_host_skill_discovery`. The exact nonfatal notice now has a
narrow tested exception; genuine errors and any tool activity still block.
The captured call was reclassified offline with identical execution settings,
without a second model call. `qualification-reconciliation-before.json` preserves
the original result; the qualification records both implementation hashes. This
is not a claim that the revised classifier was live-tested by a second call.

The installed configuration resolver verified model, effort, service tier,
authentication restriction, approval policy and named permission profile. JSONL
records successful completion/usage, but does not independently attest the
provider's internal model execution. The live run exercised a disposable snapshot,
not a real active conversion batch or a two-hour timer cycle.

34 focused offline tests passed, including real fake-executable dispatch, unknown
records, identity changes, PID reuse/handoff, concurrent ticks, uncertain dispatch,
restart, caps, pause/disable, rejected tool activity, and terminal partial coverage.
A finished historical run was rejected by the real attach control. Shell syntax,
user-unit validation and Git whitespace checks passed. No full production tests,
GLM, OCR or paid-provider calls were run for monitoring.

Reference: [Codex non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode).
