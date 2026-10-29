# Editorial concurrency ownership repair — 29 October 2026

Codex offline diagnosis. Prepared, not running. No inference or service changes.

## Cause and timing

Original, preserved run: `runs/editorial-chapters-trial-20261029T153847Z-0c89a4`.
Its outer state correctly says `stopped_error`, but the embedded two-slot trial
still says `running`. The linked continuation records it as interrupted.

There are67 saved health samples: one with0 server/0 local requests, then66 with
2 server/2 local. None records a contemporaneous excess server request. The last
sample is `concurrency-samples/1793290475934416339/sample.json`: HTTP health began
16:14:35.935 UTC; the sample finished16:14:36.438. It reports2 running,2 decoding,
0 prefilling,0 paused,4 configured slots, and2 locally owned calls (102 and103).
The health endpoint provides aggregate counts, not request identities.

Call102 completed16:14:46.619; its two-pass compilation's last saved outcome is
mtime16:14:47.856. The coordinator removed that completed future, leaving call103.
It then reused the cached sample in `room(..., len(jobs))`: server2 versus local1
raised the ownership error. This is a demonstrated client completion-accounting
race, not evidence that a server count was stale when sampled or an external call
was detected. The old event has no timestamp: its trigger is reconstructed after
call102 finalization (approximately16:14:48), before sample expiry (~16:14:51).
No subsequent health sample exists. Call103 was correctly drained and saved at
16:32:29.847; the session ended16:32:32.506, when the terminal stop was printed.

A single read-only Docker-log attempt was denied at `/var/run/docker.sock`; no
permissions changed or repeated access attempted. No file-backed log was found
under the deployment checkout. Saved samples cannot independently exclude all
external requests. Optional corroboration in a normal terminal:

```bash
docker logs --timestamps --since 2026-10-29T16:14:30Z --until 2026-10-29T16:15:00Z glm53-flash-tf 2>&1
```

## Retained output and performance

|Call|Work / effort|Request seconds|Prompt tokens|Completion|Reasoning|Other completion|Finish / compilation|
|---|---|---:|---:|---:|---:|---:|---|
|102|Bergomi3-s01 critic / max|1036.424|92821|39870|22973|16897|stop / passed|
|103|Bergomi3-s02 conversion / high|2097.331|68750|92657|81284|11373|stop / passed|

Server prefill/decode: call10256.1817/979.905 seconds; call10342.2034/1989.2445.
Final answers contain50,418 and33,169 characters. Both actual transport requests
used streaming and131,072 output tokens, exact `glm53-regular`. Other completion
is reported completion minus reported reasoning, not an independent tokenizer count.
Compilation elapsed counters are absent; file timestamps are not substituted for
compiler timing metrics.

Recorded active pilot batch time is2104.630 seconds (~35.08min), including preparation,
finalization and compilation. Combined completion132,527 contains104,257 reasoning
and28,270 other tokens (~13.43 non-reasoning tokens per active batch second).
Do not add the overlapping per-stream durations or rates as batch wall performance.
There is no matched serial comparison, no established speedup, no source-accuracy
qualification, and only two of the planned four pilot requests completed.

The samples observed two actual decoding streams; no pressure event. Minimum sampled
unadjusted available memory was11.70GiB head/13.13GiB peer. Monitoring stopped at the
ownership guard, so these measurements do not describe the remainder of the drain.
Runtime evidence records image
`sha256:9b00719301e859f7b790b5c4d80ab1e49ef64bef63d3e7af2f3829cfc32cfee1`,
TensorFold0.6.0 plus installed-source/template hashes,4slots,1,048,576 per-request
context and2,015,232 shared pool. Runtime identity is copied and checked on resume;
no settings, weights or runtime were changed.

## Repair and continuation

Completion collection invalidates cached health. Admission checks each sample
against the call set that existed when sampled; full live request reservations still
count against shared pool capacity. Excess fresh server activity remains a fatal
guard. New `concurrency-stops/` evidence includes first-stop time, sampled counts,
sample evidence, local call/task IDs and completion transitions. Interrupted trials
are persisted accurately before final report/ZIP. No reason to retry call102 or103.

New linked run: `runs/editorial-chapters-trial-20261029T165410Z-1f2179`.
All103 calls plus24 earlier calls, original outcomes/documents, runtime/compiler
bindings, stage scope, and pilot call IDs/time are retained. All10,313 original
run files were checked byte-for-byte unchanged. Pending request comparisons:
113 exact concrete bodies (112 conversions plus one immediately eligible critic),
112 identical dependencies on pending drafts. No prepared prompt, source, section,
effort, output allowance, sampling or compiler policy changed.

Next: critic for3-s02, then conversion3-s03 (capacity permitting, overlapping).
Those complete the four-request pilot; its first two results are inherited.
The remaining stage contains112 conversions and113 critics. If operational checks
pass, continue at **maximum two**. Four is deferred and blocked by the sealed policy;
reasoning-token volume cannot qualify it. Independent failures remain gaps with
no automatic replay. No overall call or wall/generation limit added.

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-editorial-chapters.sh run
```

The wrapper runs the required full normal-terminal checks once, verifies free
writer ownership and existing regular GLM, captures readiness, and starts tmux.
Report: `runs/editorial-chapters-trial-20261029T165410Z-1f2179/report.html`.
Log after launch: same directory's `terminal.log`. Status/pause/resume/bundle use
the same wrapper with the corresponding action; no manual readiness paths.

## Validation

Full final suite once:581 tests in245.495s:562 passed,15 sandbox-denied mock
loopback bind errors (`PermissionError`),4 optional compiler skips. No assertion
failure. All19 concurrency/transport/linked-repair tests pass, including an explicit
cached-two/remaining-one completion regression, external-third-request rejection,
drain and interrupted status, pause/resume without replay, exact request binding,
history retention and blocking four slots. AST, wrapper syntax and diff whitespace
checks pass. Actual preparation verified seals and pending request equality.

The operator's pre-repair suite is separately preserved:576 tests in222.579s,
OK with4 skips. It is not claimed as validation of this repair. The new wrapper
runs the normal-terminal suite once for the changed identity before readiness.
Manual full-suite command, if desired:

```bash
cd /home/mdi/projects/pdf-to-latex && .venv-control/bin/python -B -m unittest discover -s tests -v
```

New live serving, Docker-log corroboration and real compilation remain untested.
No permissions, services, model settings, cloud credentials or Git metadata changed.
Changed files: `probe/chapter_concurrency.py`, `scripts/editorial_chapters.py`,
`tests/test_chapter_concurrency.py`, `docs/EDITORIAL-CHAPTERS.md`,
`docs/PROJECT-STATE.md`, and this evidence summary.
