# Recovery/critic preparation refreshed after compiler qualification — 23 October 2026

No application/test/script changes or inference occurred in this refresh.
Existing preparation was run with explicit 267 baseline / 80 recovery / six-hour
limits and model transport, network connections and subprocess execution blocked.

The operator's `runs/tex-compiler-check-20261023T191527Z-7efa13` reports
`both_compiled` with image
`sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45`.
Both PDFs, return codes, logs, invocation settings and output hashes were verified.
The operator reports nine CompilerTests passed, including both real tests and
the relative include; no separate terminal test log was supplied. Qualification
of this adapter does not establish book compilation or mathematical correctness.
The earlier failed check remains unchanged.

Actual refreshed artifacts:

- Preparation/report: `runs/recovery-preparation-20261023T192303Z-57ed87`.
- Qwen preview: `runs/recovery-vision-input-20261023T192304Z-70e8b9`.
- Qwen run: `runs/recovery-vision-trial-20261023T192309Z-cdec02`.
- Critic recipe: `runs/text-critic-recipe-20261023T192309Z-6796b6`.
- Optional diagnostic preview: `runs/schema-diagnostic-input-20261023T192310Z-708e9f`.
- Optional diagnostic run: `runs/schema-diagnostic-trial-20261023T192310Z-252ea1`.
- Detailed refresh audit: `runs/recovery-refresh-checks-20261023T192253Z-ddf8e2`.
- Compact final inspection ZIP:
  `results/recovery-preparation-20261023T192303Z-57ed87-inspection-final.zip`.

Verified against the old preparation: all 267 Qwen request bodies, source images,
OCR drafts, prompts/schema, region ordering, 24 gate members, settings and budgets
are byte-for-byte identical. Only `tex_compile.py` changed in the preview code
hash map; the metadata and manifest seals reflect that change. There are 819
unchanged visual-preview files. The optional diagnostic retains 86 identical
files, with only the same code-binding/seal differences.

All forty critic baseline input/request files are byte-identical. The twenty
groups, ten development/ten reserved, disjoint page split, four-pair gate,
instructions and budgets are unchanged. The recipe's only substantive metadata
change is the corrected compiler code hash. Actual candidate-version requests
still require the later new Qwen candidate; no candidate was fabricated.

9,955 consumed source bindings verify. Eight preserved artifact directories
(1,147 files, including both compiler checks) and the earlier bundles retain their
bytes and membership. Application, test and script files are unchanged. New
previews pass current-code/seal checks. Both new runs are prepared offline with
zero calls/readiness records: Qwen has 267 pending units; the optional diagnostic
has thirty. The full test suite and real compiler were not rerun because this
task changed no application code.

`compiler-qualification.json`, `gate-launch.json` and `refresh-validation.json`
inside the preparation directory record the qualification, explicit gate compiler
arguments and comparisons. The current runner binds the image in run state at
first launch and rejects a changed choice on resume. No sealed record was patched.

Follow [the updated gate handover](../RECOVERY-CRITIC-TRIAL.md): arrange Qwen with
documented controls, get fresh exact-model text/vision readiness, run only the
24-region gate with the qualified compiler, then bundle and stop for inspection.
All proposals remain UNACCEPTED. No accuracy conclusion follows from preparation
or compiler qualification.
