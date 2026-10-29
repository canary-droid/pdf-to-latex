# Saved output repair and remaining Bergomi preparation — 29 October 2026

Codex offline assessment and implementation. No inference, OCR, service operation,
installation, compiler build, credential access or Git mutation. Work remains unstaged.

## Evidence and preservation

Parent: `runs/editorial-chapters-trial-20261028T215454Z-8ef98f`.
Its final inspection ZIP SHA-256 matches the supplied
`9cfda146ff2c9ab025b6cea19fa34c8554a6a23cf5f0e5592a71b858f58dbadc`.
Status was `stage_finished_for_inspection / after_bergomi_first_chapter_pair`;
64 calls plus 24 earlier calls, no uncertain dispatch. Project and run locks were
free; no converter was active. The operator's saved normal-terminal log records
551 tests passed, four optional skips, 221.777 seconds. Those are previous results,
not a claim that today's changed implementation passed the normal terminal suite.

New run: `runs/editorial-chapters-trial-20261029T103643Z-713678`.
New calls: **zero**. All 88 consumed calls remain linked and sealed. Parent state,
bindings, request/response seals, source/input seals and document hashes verified.
The failed preliminary preparation `runs/editorial-chapters-trial-20261029T103501Z-b37eca`
is retained as `preparation_failed`, with no dispatch. It exposed an assumption
about a supplement `provenance.json`; the actual input provenance lives in
`native.json` and `secondary.json`. The successful preparation exports those exact
records with their hashes, not fabricated provenance or new extraction.

## Bounded repairs

The hash-bound patch plan is `docs/editorial-saved-repairs-20261029.json`.

- Gatheral `gatheral-11-s02-part05`: repair source is complete `critic-call-050`.
  Added `amsfonts` for `\mathbb`; fixed the `\(` / `$$` mismatch in its appendix.
  Mathematics and the supplied Figure11.1 asset are unchanged. The program-appended
  duplicate whole Markdown log is not reintroduced. Original converter/critic and
  appended versions remain preserved.
- Bergomi `bergomi-01-s01`: repair source is `critic-call-064`. Both erroneous
  averaged-sum variance parentheses now say `2 sigma_hat^4/N^3` with the original
  prefactor retained. For independent standard normals, `Var(sum z_i^2)=2N`, so
  `(sigma_hat^2/N^2)^2 * 2N = 2 sigma_hat^4/N^3`. Main displayed estimator and
  variance remain unchanged. Codex attribution is visible in both repaired notes.
  Three empty/header/umbrella entries are removed from the current TeX log and
  preserved in history. The model's source-inspection requests and gamma question remain.
- Metadata-only TeX escaping makes U+001D/U+001B visible as control labels.
  Seven saved task titles have these font-extraction artifacts; raw titles remain
  in coverage and original input metadata. No mathematical source text is stripped.
- Markdown note boundaries recognize explicit disposition fields and abbreviated
  issue references. Headings/separators are not findings; an applied status is not
  undone by discussion quoting earlier uncertainty. Applied/resolved GLM claims
  stay unverified claims. Open issues are carried forward; neither compilation nor
  a model saying “verified” creates independent verification.
- Current TeX/reference inventory found no undefined/duplicate TeX labels or missing
  referenced assets in the selected documents. Literal references are not validated
  by that check. Bounded target-existence checks found Bergomi §2.2.2 at PDF46/b6,
  §2.8 at PDF96/b5 and §3.1.4 at PDF124/b8; this does not settle the gamma convention.
  Gatheral's jump expansion/conventions and Lewis inconsistency remain explicitly open.

## Delivery and schedule

Gatheral retains all34 selected parts. Its 33 unchanged compiled PDFs are reused;
the repaired Volatility Swaps part awaits compilation. A compiled placeholder is
never counted as delivered PDF content. Bergomi has one retained full chapter,
with its original successful PDF preserved; the corrected-note version awaits a
new build. No new compilation was performed: Docker API access is sandbox-denied.
tmux access is also denied. No repeated access probes or permissions changes.

Prepared masters:

- `runs/editorial-chapters-trial-20261029T103643Z-713678/editions/gatheral-1793270210665074077/master.tex`
- `runs/editorial-chapters-trial-20261029T103643Z-713678/editions/bergomi-1793270211271047422/master.tex`

Each edition retains editable chapter documents, relative assets, accuracy logs and
explicit content/PDF gaps. Original Bergomi PDF retained at:
`runs/editorial-chapters-trial-20261029T103643Z-713678/versions/bergomi-01-s01/critic-call-064/compile-1793238420297318696/attempt-1/document.pdf`.
It predates the note correction; it is not labelled the repaired PDF.

u040/u041 explicitly adopt completed u330/u331 and calls063/064. Their section,
source and context identities match; the completed conversion request matches the
current transport body exactly. No Chapter1 generation is scheduled. The remaining
132 unique units have 6,650 target blocks, each owned once, in original order.
All133 units collectively cover PDF18–519. All520 pages/8,102 recognized blocks
passed the cached-input preflight; nine blank notices and118 renderer fallbacks
are retained, not certified as faithful. Supplements PDF1–17 and520 retain images,
native TeX/text and locators. The preface PDF16–17 and front matter still lack a
reviewed typeset TeX view.

Admission is 132 high-effort conversions followed immediately by up to132 max-effort
critics, starting u042/Bergomi2-s01/PDF42–44, ending u305/bibliography critic.
One attempt per task, no automatic replay of failures/uncertain calls; one fresh
readiness per launch. Overall calls are explicitly `null`, with no generation or
overall deadline. No new spending route or experimental limit is changed.
Both sources and full chapter context are present in all132 prepared conversions.
Conservative combined input/template/output estimates150,602–789,514 fit the
recorded1,048,576 capacity; requested output131,072. Actual live capacity and future
critic drafts are checked before dispatch. No clipping or exact-tokenizer claim.

The wrapper checks both-node GPU membership through the existing GLM container's
host PID inventory and verifies GNOME executable identity. Unknown GPU jobs remain
blocking. Available memory is unadjusted. It does not operate services. Completed
chapters create assembly checkpoints; all retained TeX survives compilation failure.

## Validation

Full suite ran once: **562 tests**, 542 passed, 15 sandbox-denied mock-socket errors,
one new test-fixture error, four optional real-compiler skips. The fixture had used
the same directory for project/run locks; corrected to separate directories.
Final focused suite: **66 tests, 65 passed, one optional real-compiler skip**.
No remaining observed application assertion failure. No second broad run was needed
after the test-only fixture correction. Full normal-terminal checks run automatically
once before launch; standalone command:

```bash
cd /home/mdi/projects/pdf-to-latex && .venv-control/bin/python -B -m unittest discover -s tests -v
```

AST parsing, wrapper shell syntax, `git diff --check`, actual preparation/transport
body comparisons, unique ownership, notes/current-version checks, ZIP integrity and
saved seals passed. No claim of live model, streaming or repaired compiler success.

Exact project files changed in this task:

- `probe/chapter_editorial.py`
- `probe/editorial_delivery.py` (new)
- `scripts/editorial_chapters.py`
- `tests/test_editorial_delivery.py` (new)
- `docs/editorial-saved-repairs-20261029.json` (new)
- `docs/EDITORIAL-CHAPTERS.md`
- `docs/PROJECT-STATE.md`
- `docs/evidence/editorial-delivery-20261029.md` (this record)

Other unstaged/untracked work and AGENTS.md were preserved. Generated inputs,
derivatives, test logs and inspection archives remain under ignored runs/results.
