# Finite local recovery trial — 3 November 2026


**Kimi remains a pending next phase.** This local implementation generates
`offline-escalations.json` proposals. It does not implement or qualify a Kimi
route, and no Kimi testing or paid execution has been completed. The pending
phase is recorded separately from local recovery results and proposal packaging.

This opt-in trial follows the completed originals batch. It never starts that
production queue. Cooking with Collateral, arXiv intake and paid/cloud work are
excluded. The selected trial is recorded in `results/focused-recovery-current.json`.

The parent source/state hashes, copied inputs, model settings, code identities,
output ownership and conditional tasks are frozen in the new run's `plan.json`
and `binding.json`. Preparation-only development checkpoints have zero calls and
remain preserved. The historical 125 production calls and all failed allowances
remain unchanged. No model generation has a wall deadline or inherited global
call ceiling; the maximum below follows from finite named tasks.

| Target | Primary conversion | Focused review | Conditional Low review | Final syntax request maximum |
| --- | ---: | ---: | ---: | ---: |
| CF Cases 1–3 and 16–18 | 2 Low | 2 Max | 2 | 2 |
| Mean Reversion Bias, complete 3-unit partition | 3 Low | 3 Max | 3 | 3 |
| Alternatives to DL, complete 6-unit partition | 6 High | 6 Max | 6 | 6 |
| Spectral sections 6.2–6.3 after qualified extraction | 1 High | 1 Max | 1 | 1 |
| Pathint barriers, saved converter draft | 0 | 1 Low | 0 | 1 |
| Anfuso appendix, saved draft | 0 | 1 Max | 1 | 1 |
| Information Geometry section 2, saved control | 0 | 1 Max | 1 | 1 |
| Breaking Barriers final page and original Figure 4 | 1 High | 1 Max | 1 | 1 |

There are 29 primary requests, at most 15 Low review recoveries, at most 16
syntax requests and one readiness request: **61 maximum**. Unneeded conditional
requests are skipped. The planned section conversions are the single recovery
round for historical converter failures; no recursive splitting or automatic
conversion repeats occur. Failed criticism never reconverts its draft. Low arms
are explicit reasoning-exhaustion recoveries; High/Max remain reference settings.
Conversions/reviews retain 131072 output tokens; syntax requests retain 8192.
Installed template mapping must verify every requested effort at launch. Internal
model effort is not independently attested by response usage. Requests are text
only; image capability is not assumed or exercised.

Secondary PDF text is assessed by page/line with original bytes and reasons
retained. Only invalid controls, replacement glyphs and unmapped private-use glyphs
cause suppression. Mathematical notation, disagreement and fragmented reading
order alone do not cause deletion. Prose and mathematical quality are separate;
MinerU is never thereby declared correct. CF has no mechanically provable invalid
glyph passages under this conservative detector: narrower tasks and focused review
are still necessary. Do not present input filtering alone as a demonstrated cure.

Output units follow complete cases/major sections, with explicit block ownership
and estimated output size. Definitions/context can be broader than output scope.
The plan preserves all Alternatives/Mean Bias source blocks, including numerical
settings, figures, tables, references and the final Alternatives algorithm appendix.
CF and Pathint are deliberately partial trials and cannot be labelled complete
new paper editions.

Focused reviews return at most eight exact located old/new edits, bound to a draft
SHA256. Stale/ambiguous/outside/overlapping edits, asset changes, numbering/structural
changes and substantial deletion are rejected. Applied changes remain attributed
model claims in separate versions and before/after logs. Unresolved findings and
unapplied suggestions survive. No full-document rewrite fallback exists. Syntax
repair reuses the existing isolated compiler and constrained repair protocol;
misplaced aligned/split equation tags can move to their existing equation wrapper
without changing the number or expression bytes. CF's laptop edit is not used.

Spectral OCR reuses the 24 completed owned pages and every existing attempt.
The diagnostic pass captures exact warp array/matrix/quad/settings, traceback and
available page locals. One correction pass is admitted only for an observed
positive nondegenerate in-image quad rounded to a zero output dimension by the
specific get_rotate_crop_image caller, with cubic/replicate settings. Ceil sizing
is qualified against the installed SDK using an offline subpixel fixture. This is
not a claim that the historical failure had that cause. Other causes remain
unrecovered. Attempts remain bounded including inherited records: old attempt +
diagnostic + at most one qualified correction. Uncertain OCR prevents replay and
GLM restoration until reconciliation. The existing documented helper may stop
only the positively identified owned, idle GLM; its settings must match before
stop/restart. Independent text cases continue after a settled document OCR failure.

Source checks for Anfuso equation (13), original Breaking Barriers Figure 4,
CF and the Information Geometry control live in `evaluation/` and `evidence/`;
expected answers are not model inputs. New harmful changes are not automatically
ruled out. Model agreement, compilation and structural coverage are not independent
mathematical verification. The final bundle includes explicit remaining issues
and offline passage-level escalation proposals, with no cloud dispatch.

## Controls

From `/home/mdi/projects/pdf-to-latex`:

```bash
bash scripts/run-focused-recovery.sh run
bash scripts/run-focused-recovery.sh status
bash scripts/run-focused-recovery.sh pause
bash scripts/run-focused-recovery.sh resume
bash scripts/run-focused-recovery.sh bundle
```

`run` prepares once if absent, performs normal-terminal validation once per final
code/test identity, then launches tmux `pdf-focused-recovery`. `pause` drains owned
HTTP requests and lets the current OCR window settle. `resume` cannot replay an
uncertain reservation, reset allowances or create a duplicate worker. Finished
resume makes zero OCR/model/readiness requests. `bundle` is available while idle;
the worker bundles automatically on completion/pause/error. It stops when the
frozen task set is exhausted and has no next-collection action.

The run's `progress.json` refreshes at phase changes, reservations, settlements
and model capacity samples. `terminal.log`, all requests/responses/reasoning,
immutable versions/builds and the automatically generated inspection ZIP remain
on disk. Source images and held-out notes are evidence, not permission to start
an unrelated experiment. All development changes stay unstaged.


## Qualified linked continuation — 4 November

The initial trial `focused-recovery-20261103T212127Z-c483fb` completed three
requests and paused/drained before integration. Pathint's focused Low review
returned valid JSON/no edits in 107.08 seconds (1,614 reasoning + 54 final tokens).
Anfuso's Max review returned in 1,464.78 seconds (87,455 reasoning + 1,230 final
 tokens), reverting the unsupported numerator correction and updating its inline
note. It explicitly retained an unresolved warning about stale out-of-scope
editorial summaries. Both actual reviewed versions compile. These are different
scopes/settings from the old whole-document failures, not a controlled claim
that Low is globally superior or that all mathematics is verified.

The Spectral diagnostic reproduced the exact failure in
`mineru.model.ocr.image.get_rotate_crop_image`: width 0, height 26, cubic/replicate,
points (696,201), (696,201), (696,227), (696,227). The saved pixel array and traceback
show the affected OCR paragraph; its text matches original physical page 27.
The `get_ocr_result_list` implementation already rejects raw boxes narrower than
3 pixels, but only after calling the crop function. The qualified private worker
adapter applies that exact existing raw-coordinate predicate before cropping.
An offline replay of the captured array reproduces the original failure and
passes with the reordered guard. An accepted valid crop remains byte-identical.
No vendor/SDK files, thresholds or source content were changed. Nonmatching
failures remain unrecovered. The previous positive-subpixel qualification is
retained; the actual degenerate box did not satisfy it and was not silently expanded.

The linked run `focused-recovery-20261103T223632Z-d9c8f9` copies and verifies all
prior calls, versions, syntax allowances and the failed diagnostic. It goes
straight to the one qualified correction pass, preserving the 24 completed owned
pages and both attempts already consumed at the failed window. It may complete
the four remaining windows. The 61-request maximum includes its three inherited
requests; the remaining maximum is 58. No new readiness call is required.

The linked critic now receives only the exact selected saved-draft passages plus
necessary preamble/context, while its hash still binds the complete baseline.
Character offsets stay in program metadata: the initial Max review wasted time
counting characters to interpret them. Completed reviews are not replayed for
this refinement. Invalid secondary glyph spans alone are masked; surrounding
useful prose remains. Original text and suppression reasons remain auditable.

The initial code passed 766 tests (762 passed, four optional skips). The qualified
handoff passed 20 focused tests and an installed-SDK replay of the real captured
failure; required whole-suite qualification runs once for the final linked code
identity before its persistent worker starts. Read saved checks for its outcome.
The final bundle additionally retains actual request/final responses, rejected
syntax plans, exact warp arrays and unresolved findings even when a critic
returned normally. No source-verification claim follows merely from that status.


## Source-name logging correction — staged for an idle boundary

The legacy common transport guessed Gatheral for unrecognised task IDs. The
pending patch snapshots explicit source filename/title, section and phase from
state/task metadata into each new reservation before transport. Both serial and
threaded paths use this same reservation function. The transport prints that
snapshot; it does not inspect prompts or guess a book from an identifier.
Readiness prints “Model readiness”. Missing metadata prints “Unknown source” /
“Unknown section”; the raw task/source IDs remain available for diagnosis.

See `results/pending-source-logging-current.json` for the reviewed proposed module,
regression, base hashes and unified patch. The active worker's bound source has
not been edited and the trial has not been paused for logging. Existing logs and
call records are unchanged. Apply only after rediscovering state/writers and
acquiring all project/converter/run locks. If the run is paused but unfinished,
use a linked continuation preserving all calls, outputs, allowances and old
bindings; do not silently reseal the historical run. Required normal-terminal
checks belong to the integrated code identity before future dispatch.
