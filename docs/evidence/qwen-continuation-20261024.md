# Qwen continuation preparation — 24 October 2026

This records offline preparation, not new inference or a fidelity audit.

The operator's completed repair run,
`runs/recovery-repair-trial-20261024T103428Z-1a2018`, inherits 24 baseline calls
from `runs/recovery-vision-trial-20261023T192309Z-cdec02` and adds one
`export_feedback` call for v005. Its replacement is export-supported and its
proposed TeX compiled. The original OCR still has a syntax failure; the pair is
not `both_compiled`. The saved compiler outputs and call seal verify. Proposals
remain UNACCEPTED, with one uncertain proposal deferred.

| Continuation property | Verified preparation |
|---|---|
| New preview | `runs/recovery-continuation-input-20261024T112538Z-e1a1ef` |
| New run | `runs/recovery-continuation-trial-20261024T112538Z-8d13d3` |
| Inherited calls | 24 baseline + one recovery; copied unchanged |
| New calls | Zero |
| Dispatch scope | Exactly 243 pending non-gate regions, original order |
| Baseline input preservation | All 267 request/data/image inputs unchanged |
| Original ceilings | 267 baseline, 80 shared recovery, two extra per region, six cumulative hours |
| Remaining allowances | 243 baseline, 79 recovery; 20,760.389689248055 seconds |
| Elapsed time inherited | 839.6103107519448 seconds |
| Compiler | Existing qualified image, mandatory and bound to parent identity |
| Proposals | UNACCEPTED; uncertain results deferred |

The new opt-in continuation preparation records historical and current code
identities separately. It preserves original seals and refuses a duplicate fork,
inherited budget resets, changes to completed units or dispatch outside the
pending scope. Existing pause/resume/recovery mechanics are reused. No gate or
repair request is replayed. All settings remain unchanged: Flash Next exact alias,
localhost port 8890, medium reasoning, 16,384 output tokens, 600-second timeout,
sequential dispatch, omitted sampling and server `response_format`, strict local
validation. Compilation does not certify transcription or mathematics.

Seven new continuation regressions passed. Full suite: 267 tests, 250 passes,
15 sandbox-denied mock socket errors, two skipped opt-in real compiler tests,
no assertion failures. Log: `results/continuation-full-tests-20261024.log`.
No model or real compiler execution occurred during this preparation.

All 2,287 files and membership in both original runs/previews are unchanged,
and their latest bundles retain their recorded hashes. All 25 inherited call
directories match byte-for-byte; 12,242 source bindings and current code/preview
seals verify. Detailed checks:
`runs/continuation-checks-20261024T112017Z-19e3b8/validation.json`.

HTML: `runs/recovery-continuation-trial-20261024T112538Z-8d13d3/report.html`.
Initial inspection ZIP:
`results/recovery-continuation-trial-20261024T112538Z-8d13d3-inspection-20261024T112540Z-9330de.zip`.
11,625,252 bytes, 298 unique members; CRC and image links pass. SHA-256:
`3373eeaed1c8beb803044a9b604817eccd3439f30e18f1dfd2eb48925c4c0fad`.
Contains HTML/Markdown reports, failures CSV, ledger, images and continuation
lineage; full PDFs/model weights are excluded. Raw attempts remain under runs/.

Use [the current operator runbook](../RECOVERY-CRITIC-TRIAL.md) for fresh readiness,
compiler-enabled continuation, monitoring, pause/resume and partial/final ZIPs.
Live efficacy, source fidelity and the eventual continuation outcome remain
untested. Candidate assembly and critic execution are separate later steps.
