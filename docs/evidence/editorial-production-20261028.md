# Production continuation after the high/max pilot — 28 October 2026

Codex assessment and offline preparation; no inference or OCR dispatched.

## Verified starting evidence

Completed pilot: `runs/editorial-chapters-trial-20261028T072031Z-41483c`.
Both project and run writer locks were free, converter processes absent, and no
call was in progress. Saved seals verified. Calls032/034/036 requested high;
033/035/037 requested max. All six finish_reason=stop, nonempty final content and
passing saved compilation records. New conversion times were 77.8725, 227.0187
and 1305.8833 seconds. These are observed technical/timing results, not accuracy
scores or a guaranteed speedup. State preserves 37 calls plus24 earlier calls.

## Offline adoption and image checks

Inspected the existing full-page images for PDF120/printed89 and PDF128/printed97.
The hash-bound, exact replacement plan is
`docs/gatheral-pilot-adoption-20261028.json`; it is **not** model-request content.

| Current finding | Disposition and evidence |
|---|---|
| Lewis section | Adopted saved `pilot-gatheral-07-s05/critic-call-037` into canonical `gatheral-07-s05`; every displayed equation unchanged. |
| J3 / beta2 | Source image confirms the printed brace tends to3. J1=O(t²), J4=O(t³), so the other displayed beta2 terms are bounded and cannot cancel its t^-3 term for nonzero rho/eta with positive variance/lambda. Substantive source inconsistency remains visibly open; no corrected coefficients invented. |
| beta0 | Earlier GLM divergence assertion qualified: J2 is undefined in the supplied section; cancellation has not independently been excluded. Need Lewis(2000), pp142–144 and the definitions. |
| Figure7.1 | Removed sigma/nu tildes from the selected canonical caption, per source image. Genuine proof tilde-x retained. |
| Prose slope | Retained rho eta beta(nu0), obtained by differentiating(7.2); existing visible correction remains. |
| Heston reference | Retained Chapter3, citing actual earlier(3.19), native block gatheral-p0066:b5, PDF66/printed35. Removed the invalid claim that a same-chapter reference is inherently impossible. |
| Control6-s03 | Canonical selected document remains byte-identical. Neither pilot control version replaces its canonical counterpart. |

The clean saved critic documents are retained separately from the edited selected
versions. Exact input/output hashes, attribution and current/history links are in
`adoption-record.json`; full old accuracy logs remain unchanged. The current edition
shows the Lewis open issue once, with the independent qualification. The canonical
7-s01 keeps its substantive text and visible notes, with duplicate/stale end notes
moved out of current display (historical copies retained). No-change observations
are not labelled corrections. Future rendering recognizes explicit quoted TeX-note
labels; it does not infer semantic resolution. An unmatched open issue remains open,
including when its description mentions an unrelated no-change control.

## Prepared continuation

Run: `runs/editorial-chapters-trial-20261028T215454Z-8ef98f`.
Report: `runs/editorial-chapters-trial-20261028T215454Z-8ef98f/report.html`.
Edition: `runs/editorial-chapters-trial-20261028T215454Z-8ef98f/editions/gatheral-1793224497328383556/`.

The stage admits 26 task IDs: Including Jumps pair; six natural subsection pairs
for Gatheral11-s02; five for11-s03; then one whole Bergomi Chapter1 pair (PDF18–41).
Criticism immediately follows each complete conversion. The first Bergomi chapter
has319 substantive blocks. All553 scheduled target blocks are unique across the
13 conversions; each parent recovery is exactly partitioned in reading order.
The long subsections retain full chapter context and original both-source inputs;
physical-page overlap at subsection boundaries does not duplicate target blocks.

All13 saved conversion requests contain the exact complete primary and secondary
texts, use high effort, streaming and131072 output tokens. Critic inputs will add the
actual completed draft/notes at max effort. Byte-bound input+template+output checks
range193905–376410 against recorded context1048576; live health/draft checks remain
mandatory. No exact-tokenizer claim, clipping, sampling change or serving update.

Remaining Gatheral output gaps are7-s03,11-s02,11-s03 (12 visible subsection notices).
Lewis is available despite its explicitly unresolved printed mathematics. Other
prior unresolved findings, including the contract-intended Chapter10 denominator,
are preserved. The new edition includes editable standalone TeX/assets, normalized
bibliography, accuracy history and the original-page front/index supplement.
Changed documents/new master are not compiled here: Docker API access was denied.
Unchanged documents retain their prior successful checks. Operator execution uses
the existing qualified image b9505ed9122f83fd4bb4ae2ab79a1a7ad82187ca712fda0e8868e4e374296211.

Bergomi's sealed cached preparation remains byte-for-byte identical:520 pages,
65 completed extraction windows,8102 blocks,9 notice-bearing intentional blanks,
118 explicit renderer fallbacks. Fallback preservation is not fidelity verification.
The other132 conversion units stay dormant; larger chapters use natural section
outputs with chapter context, while manageable Chapter1 stays whole. This stage
ends for inspection after that first pair, including on a preserved content failure.

The overall local book call ceiling is explicitly null/unlimited in the new binding
and state; no numerical sentinel, reset, or wall/generation deadline. All61 consumed
calls remain. One attempt per scheduled unit, readiness once per launch, no replay
of completed/uncertain work, and explicit stage membership prevent an unlimited
retry loop. Paid/cloud and other experimental limits, and all old sealed limits,
are unchanged. New compilation remains a separate check, not mathematical acceptance.

Two superseded offline preparations are retained, never launched:214827-d56e32
failed seal validation because its new manifest used an object instead of the existing
list schema;214859-3fde75 was superseded after a narrow final note-classification/
remaining-gap reporting correction. Neither is the current launch pointer. No old
seal was patched. The final preparation passes the actual existing seal reader.

## Validation and limits

- Final focused editorial tests:33/33 passed, including new adoption, explicit
  note matching, mixed open/no-change findings, >98 admission, history retention,
  no replay, stage stop and subsection-gap coverage.
- Full offline suite once:551 tests,532 passed,15 socket PermissionError errors,
  4 optional real-compiler skips, no assertion failures. The two final narrow
  reporting/classification edits were covered by the final33 focused checks.
- AST, shell syntax and git diff --check passed. Actual prepared requests, source
  completeness, target uniqueness, preserved control, parent evidence and cached
  extraction seals checked. Logs and machine-readable validation accompany the run.
- No live model/streaming, Docker compilation, service operation or OCR performed.
  The launcher runs the normal-terminal full suite once per code/test identity and
  captures readiness automatically. Real execution/compilation remains untested here.

## Exact project files changed in this task

- `probe/chapter_glm.py`
- `probe/chapter_editorial.py`
- `scripts/editorial_chapters.py`
- `tests/test_editorial_production.py`
- `docs/gatheral-pilot-adoption-20261028.json`
- `docs/EDITORIAL-CHAPTERS.md`
- `docs/PROJECT-STATE.md`
- `docs/evidence/editorial-production-20261028.md`

Ignored new linked runs, pointer and inspection ZIP accompany these changes.
AGENTS.md and unrelated existing modifications were not edited. Nothing staged;
no Git metadata operations. Launch and control commands are in the current runbook.

Final inspection ZIP:
`results/editorial-chapters-inspection-20261028T215454Z-8ef98f-1793224630560782987.zip`
(21,986,082 bytes;731 unique members, archive integrity verified). Includes prepared
state, binding, admission plan, adoption record, current edition/notes/images and
validation logs. Complete historical raw responses remain at their sealed linked
paths; no inference or new compiled-PDF success is implied by this archive.
