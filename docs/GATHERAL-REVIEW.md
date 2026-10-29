# Gatheral protected review — Task 2 offline adapter

Do not run this from the development copy. First finish all 210 owned extraction
pages, ensure the converter has exited, and integrate the tested changes with the
baseline guards in TASK2-DEVELOPMENT.md. No actual Gatheral review preview exists
yet. Commands below discover/create real paths; they do not name future directories.

MinerU provides saved OCR; Qwen compares source images; explicit whole-block
assessments produce an experimental candidate; GLM critiques candidate text;
MiMo is an optional selected second opinion. All model proposals stay UNACCEPTED.
No command here starts/stops a model service. Use SPARK-OPERATIONS.md for the
separate documented deployment phase after the current work finishes.

## Preparation and first gate

Run these in the normal terminal **after guarded integration**. The first block
runs the tests without opting into Docker compilation, then prepares an offline
inventory from the actual completed Gatheral conversion. Preparation verifies
saved source/output evidence; it does not rerun MinerU. The wrapper automatically
records the generated paths in `results/book-review-current.json`.

```bash
cd /home/mdi/projects/pdf-to-latex
env -u PDF2TEX_COMPILER_IMAGE .venv-control/bin/python -B -m unittest discover -s tests -v
bash scripts/run-gatheral-review.sh prepare
bash scripts/run-gatheral-review.sh status
```

Preparation covers all registered owned pages, one complete block per visual
request and one whole-page omission request per page, including pages with no
recognized blocks. Neighbouring OCR/page images are context, not duplicate targets.
Initial gate: physical pages 32–33. Qwen settings remain `flash-next-tensorfold`
at `http://127.0.0.1:8890/v1`, requested medium, 16,384 output tokens, 600 seconds,
sampling defaults unchanged. Unsupported server `response_format` stays omitted;
schema, identity, target coverage and evidence checks stay local and strict.

The sealed limits are the actual unit count, 80 shared recovery calls, two additional
calls per unit and six hours cumulative active admission. One admitted call may
finish within its timeout. There is no promise those limits finish the whole book.
A large indivisible block or omission context that exceeds input limits is recorded
unavailable, never clipped. A missing bbox retains the raw target without review
credit. A gate with any unavailable/failed unit cannot pass.

Once Qwen is deliberately running and no OCR/heavy model work overlaps, the next
block checks the owned converter state and runs **live** fresh readiness. It must
print `Text: passed` and `vision: qualified`. The wrapper saves and validates the
actual readiness path/alias; no copied shell variable is needed.

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -B - <<'PYCODE'
from pathlib import Path
from probe.saved_pages import converter_idle
print(converter_idle(Path.cwd()))
PYCODE
bash scripts/run-gatheral-review.sh ready
tmux new-session -s gatheral-review
```

In that tmux terminal, run **only the initial gate**. Detach with Ctrl-b then d;
remote-desktop disconnection will not end tmux. Requests/attempts/progress are
checkpointed in the displayed run directory. Compiler feedback is enabled with
the qualified immutable image; no image build or installation is requested.

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-gatheral-review.sh gate
```

The wrapper supplies
`--compiler-image sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45`.
Only eligible supported fragments are compiled in the existing isolated adapter.
Compiler setup/access failure is not a model TeX error. Successful compilation is
not proof of transcription or mathematical correctness.

## Inspection, pause and continuation

Status is read-only and may run while writing. Pause requests a stop after the
current bounded call; no services are stopped. Resume the same gate if interrupted;
never prepare a duplicate to reset attempts. A terminal failed gate requires
inspection, not an automatic retry/reset.

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-gatheral-review.sh status
bash scripts/run-gatheral-review.sh pause
# After the writer has stopped, only if resuming an interrupted initial gate:
bash scripts/run-gatheral-review.sh resume-gate
```

After the writer exits, produce the report and ZIP. Inspect both the technically
completed targets and the independent omission checks. Report paths and the
inspection ZIP are printed by these commands.

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-gatheral-review.sh report
bash scripts/run-gatheral-review.sh bundle
bash scripts/run-gatheral-review.sh dispositions
```

The last command prints a new hash-bound assessment template. It defaults every
proposal to investigate/whole-block-not-preserved. Assess complete replacements
before marking any suitable; a formula-only replacement for a paragraph must stay
deferred. Uncertain proposals, conflicts, unsupported deletions/merges/insertions
remain deferred. Do not infer permission from `uncertain=false`.

After inspection and a passed gate, run the remaining prepared units in the same
tmux session. Fresh readiness is recorded automatically. Completed gate units are
not repeated; shared budgets and failures survive resume.

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-gatheral-review.sh ready
bash scripts/run-gatheral-review.sh continue
# After a later pause, use resume-continue instead of preparing a new run.
```

A candidate can also be built after the small gate without pretending the rest
was checked. This block reads the current run pointer and asks only for the **actual**
assessment filename just printed by `dispositions`; it validates both paths before
creating a new candidate. It does not compile or accept the candidate.

```bash
cd /home/mdi/projects/pdf-to-latex
book_run=$(.venv-control/bin/python -B - <<'PYCODE'
import json
from pathlib import Path
p=Path(json.loads(Path('results/book-review-current.json').read_text())['run'])
assert (p/'binding.json').is_file()
print(p)
PYCODE
)
read -r -p 'Actual reviewed dispositions JSON path: ' book_dispositions
test -n "$book_run" && test -n "$book_dispositions" && test -s "$book_dispositions" &&
.venv-control/bin/python -B -m probe.book_review candidate \
  --run "$book_run" --dispositions "$book_dispositions"
```

The printed candidate path contains `candidate.tex`, `inventory.json`, `changes.json`,
`review-coverage.json`, `unresolved-insertions.json`, `bibliography.json`, provenance,
source images and `report.html`. Every original owned block is inventoried in order;
deferred representable text stays exact, while unsupported content keeps complete
raw OCR and source references. There is no silent summary substitution or final
book claim. Proposed insertions stay separate and cannot erase existing content.
The small-gate candidate binds a snapshot of the run; further review changes its
state binding. Assemble a new candidate/critic preparation after expansion rather
than reusing stale candidate bindings.

Next, use `probe.critic_route boundaries --candidate ACTUAL_CANDIDATE --out NEW_MANIFEST`
with actual printed paths. Review the boundary manifest for coherent statements,
proofs and derivations, then `prepare --candidate ... --conversion ... --source gatheral
--passages ... --profile glm`. These are documented CLI templates, not fabricated
artifact names. The generic path preserves target/context distinction and refuses
unresolved candidate targets. The existing candidate-critic wrapper captures the
new pointer, readiness and resume state. GLM remains local/default. Do not send the
whole book to MiMo: selection stays explicit, costed, bounded to four passages and
linked to the latest cumulative ledger. Unsupported images/tables, insertion
assembly, unresolved boundaries and unlabelled references remain integration gaps.
