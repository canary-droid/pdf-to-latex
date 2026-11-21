# Bounded DeepSeek diagnostics, 16 November 2026

Current experiment: `results/deepseek-diagnostics-20261116/current.json`.
Run: `runs/deepseek-diagnostics-20261116T164918Z`.
This is an explicit saved-scope experiment, never an automatic production fallback.

The frozen plan has 27 local and 18 hosted primary tasks. Three additional requests
are allowed only after explicit diagnosis/reconciliation in a linked task record;
they are not scheduled automatically. One attempt per task; valid wrong or truncated
outputs are retained. Finished resume performs zero requests. There is no generation
deadline. Model identity, source/image hashes, plan/code bindings, durable reservations
and response seals remain enforced. Local work is sequential, grouped by model.

The original six scopes/drafts/images/reference and instructions are reused exactly.
B-p039 allowance-control changes only 16,384 to 32,768. All subsequent tasks retain
32,768 and High; diagnostics compare temperature 0/1 with top_p 1, three repetitions.
First repetitions are the primary full-sample comparison. No best-of-three or voting.
Seeds 2/3 are predefined; omitted local seed 1 is prompt-keyed. Top_k 20 / min_p 0 are
unchanged local defaults and explicit hosted fields. Medium=High=75 locally.

Hosted uses only deepseek/deepseek-v4.1-flash-1017 through deepinfra/fp8, ZDR and
no data collection, no fallbacks, required parameters, no tools/plugins. Public
route/price checks and authenticated remaining-allowance checks precede each POST.
The existing CloudClient transport and Ledger provide private key handling, durable
pre-dispatch reservations and provider-cost settlement. Historical holds remain
unchanged and reduce usable live allowance. The new finite plan's derived cap is
$2.30 including the three unscheduled potential extras; no old allocation is reset.

Controls:

```bash
.venv-control/bin/python -B scripts/deepseek_diagnostics.py status --run /home/mdi/projects/pdf-to-latex/runs/deepseek-diagnostics-20261116T164918Z
.venv-control/bin/python -B scripts/deepseek_diagnostics.py pause --run /home/mdi/projects/pdf-to-latex/runs/deepseek-diagnostics-20261116T164918Z
.venv-control/bin/python -B scripts/deepseek_diagnostics.py resume --run /home/mdi/projects/pdf-to-latex/runs/deepseek-diagnostics-20261116T164918Z
```

Pause drains the current call and restores the original GLM service. Never remove
an uncertain reservation or modify a frozen binding to resume. The controller holds
the existing project writer lock; do not edit top-level Python files in probe/ or scripts/ while
it runs. The reporting adapter is an explicit process-local callback to the reused
service lifecycle helpers, not a change to their historical plan schemas.

Result assessment is separate under `results/deepseek-diagnostics-20261116/`.
It distinguishes source reading, actual draft claims, correct repair proposals and
unique-anchor correction eligibility. No experimental correction is published.
Unknown billing/token splits are not zero. GLM remains the working default.
