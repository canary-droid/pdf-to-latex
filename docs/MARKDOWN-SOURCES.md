# Technical Markdown source ingestion

New preparations through `scripts/run-library-first.sh prepare` default to
`--output-format markdown`. `--output-format latex` retains the LaTeX workflow.
This changes newly prepared jobs only. A sealed plan with **no** `output_format`
field means legacy LaTeX; it is never upgraded by a default at resume time.
Existing source editions, author packages, attempts and monitor records remain intact.

The plan, state, unit/task records, saved versions and review payloads bind
`output_format` and `format_protocol`. The current Markdown protocol is
`technical-markdown-v1`; explicit new LaTeX uses `library-latex-v1`.
A review must echo both fields and the exact input draft SHA-256. Requests retain
the existing durable reservations, streaming, capacity checks and one-attempt
policy. A changed format cannot reuse another format's result or consume a new
attempt by resetting an old task. Code changes still require the established
linked preparation/continuation procedure; this feature does not bypass bindings.

The worker still uses MinerU Pro, coherent source units, assessed secondary PDF
text, High conversion and High original-image review, 131072 completion tokens,
at most two local requests and the existing image limits. It does not add images
to conversion or change source-image resolution. Paid Markdown recovery is
unqualified and disabled; no provider credential is read during preparation.
Matching author TeX remains preferred: ready author sources are not reconverted,
and a Markdown derivative never replaces their original package automatically.
Historical task-specific preparers/continuations retain their inherited contracts;
use the public `run-library-first.sh prepare` interface for new source jobs.

## Source format

This is full source transcription, separate from later wiki summaries.

- ATX headings preserve section/appendix hierarchy and titles. Paragraphs, ordered
  and unordered lists preserve source order. Definition, assumption, theorem,
  lemma, proof and algorithm boundaries and original numbers remain explicit.
- Inline mathematics uses `$...$`; display mathematics uses `$$` on separate
  lines. Printed equation numbers use `\tag{...}`. Do not infer absent numbers
  from successful rendering. Retain unresolved macros and flag their definitions
  for qualification rather than deleting or guessing their meaning.
- Explicit `<a id="..."></a>` anchors and `[reference](#...)` links preserve
  cross-references. Undefined or conflicting whole-source anchors remain gaps.
- Figures use portable `![description](assets/name.png)` links, plus the complete
  caption. Keep original figure assets. A model omitting a link does not make the
  expected source figure disappear from coverage checks.
- Footnotes use `[^id]` and `[^id]: text`. Preserve their text, mathematics and
  anchors; missing definitions and conflicting IDs are flagged.
- Simple rectangular tables may use pipe syntax, with escaped cell pipes.
  Complex tables use complete HTML tables with row/column spans, headers, units,
  captions and all cells. Rendering mathematics inside HTML varies by viewer;
  retain an explicitly located mathematical cell transcription if needed.
  Unsupported structures remain verbatim in `raw-tex` fences with a source
  locator and an unresolved finding. Such a fallback is **partial**, not a
  successful editable-table conversion.
- Bibliographic entries remain full source content. Keep source numbering and
  links; do not replace references with a new bibliographic research campaign.
- Source wording and printed mathematics stay distinct from attributed editorial
  corrections. Accuracy notes follow the source response envelope and are saved
  separately. No executable HTML, remote assets or source-provided commands run.

Converters are asked for one four-backtick `markdown` envelope ending with
`<!-- source-transcription-complete -->` inside it. The marker is removed from
the saved source. A normal `stop` finish, closing fence and marker establish only
response completeness. A matching three-or-more-backtick envelope is also accepted;
multiple output blocks remain invalid. Length termination is rejected even if a partial source
looks syntactically plausible. Raw answers and reasoning remain in the run.

Reviewers return focused JSON edits using `replacement_format="markdown"`.
Exact anchors, base hash and format/protocol are mandatory. Mathematical edits
still need separated printed-source, draft, proposed-change and justification
fields. Ambiguous, overlapping, stale, structural or asset-changing proposals
remain unapplied. Located numerical-cell observations retain their model-claim
status. Successful JSON, Markdown syntax or model agreement is not verification.

## Validation, delivery and limitations

The existing source/page/block and attempt records are retained. Physical page
numbers are separate from printed labels; unestablished labels remain null.
Coverage screens count owned equation blocks/tags, tables, expected figures and
substantive spans. They are conservative omission alarms, not proof of semantic
coverage. Unreviewed scopes, unsupported macros and outstanding source spans
remain explicit. Complex-table cell fidelity needs source-image review.

Each unit retains converter and reviewed `.md` files, exact hashes, scope metadata,
raw answers, accuracy logs, findings and diffs. Publication uses
`selected_sources` plus `selected_markdown`; historical `selected_tex` remains
available for LaTeX consumers. A paper-level `source.md` joins the owned units and
adjusts only portable asset paths and namespaces local footnote IDs by unit. Duplicate tags, conflicting references and
substantive overlaps prevent a complete-source claim. Original standalone bytes
are preserved. Inspection ZIPs include Markdown, assets, findings/diffs, timings,
coverage, selected source images and explicit omission records.

Compilation remains separate and optional. Existing LaTeX `--compile-pdf` uses the
qualified isolated compiler. Markdown-to-PDF compilation is **not qualified**;
Markdown jobs explicitly record `not_requested`, including when the optional
LaTeX compilation flag is present. The original PDF remains the reading evidence.
No new renderer or dependency is installed. The installed markdown-it parser was
used for structural HTML checks; Obsidian/MathJax and footnote-extension rendering
still require live application inspection. No renderer test establishes fidelity.

## Saved TeX export

The bounded offline command writes a new directory and never selects a source:

```bash
.venv-control/bin/python scripts/export_source_markdown.py \
  --tex /absolute/saved/document.tex \
  --expected-sha256 EXACT_SAVED_SHA256 \
  --asset-root /absolute/allowlisted/asset/root \
  --evidence /absolute/saved/findings.json \
  --output /absolute/new/derivative-directory
```

It checks the original hash, retains `original.tex`, copies literal dependency
files and compact supplied review evidence, and seals the derivative. It does not
execute TeX, expand arbitrary macros or compile. Bounds: 1 MiB root TeX, 1000
literal dependencies and 32 MiB dependency bytes. Ambiguous or missing includes,
custom environments/macros and automatic equation numbers without a saved mapping
are reported. Unsupported source remains verbatim. Repeating the exact command
verifies/reuses the sealed derivative; it does not overwrite it. Checking this
export is not a new source-image review, and old review findings retain their
original TeX scope and identity.

## Prepared qualification and cookbook benchmark

`prepare_markdown_qualification.py technical` prepares three explicit saved units
from Bang–Daboussi CMS/RFR, Ravagli vol-of-vol and Pykhtin counterparty exposure.
Each uses physical pages 1–4 with exact saved blocks/assets/context. Six primary
requests maximum: one High conversion plus one conditional High image review per
unit. OCR is reused. Existing TeX is contextual comparison evidence only and is
not fed to the new model. These are deliberate format tests, never replacements
for ready library generations.

`prepare_markdown_qualification.py cookbook` prepares a separate run-only benchmark:

| Physical pages | Printed labels | Assigned material |
|---|---|---|
| 24–27 | xxiii–xxvi | Weights, measures, temperatures, conversion and cup tables |
| 28–39 | 1–12 | Two-column sauces, stocks, roux, numbered recipes and fractions |
| 400–403 | 373–376 | Poultry quantities, preparation steps and numbered references |
| 637–644 | 610–617 | Three-column index: recipe numbers versus page references |

Total: **28 assigned physical pages** of the verified 677-page PDF, SHA-256
`cb9fe0df4906189d1a3e86519dc846c777fbabf555e6060b5df48318f596a49c`.
Title/copyright evidence is on physical pages 6–7: **2011 fifth English edition**,
not the original work's 1903 publication. The embedded OCR is only a comparison
baseline. Original 200-dpi page images and their dimensions/hashes are frozen.

Adjacent pages 40, 399, 404 and 645 are retained as operator comparison context,
not extra OCR or assigned output. The sauces sample ends during a recipe; poultry
starts during recipe3099 and ends during the discussion under3130. Those external
continuations are explicitly outside this page-sample benchmark. This does not
claim complete recipes across an external sample edge. At internal joins all
assigned blocks remain owned exactly once. Preserve the source's quantities,
wording and numbered references without modernization or culinary interpretation.

The benchmark's exact conversion units are sealed after OCR using the same
coherent planner. Indivisible oversized spans remain outstanding. Allowance is
one conversion and conditional image review per derived unit; no recursive
splits/retries, paid calls or production queue continuation. Its source ID,
publication and progress remain in the benchmark run, never the quantitative
source collection. Dan's pipeline can use the same PDF/page hashes and images.

The original 15 November plans were prepared without dispatch. The authorized
16 November linked technical qualification and cookbook benchmark are now
**FINISHED**; the cookbook delivery remains partial. The original preparations
are preserved. Current result paths are in
`results/markdown-source-preparation-current.json`; do not launch the obsolete
zero-call plans as additional work. The following are general lifecycle forms;
preparation, status and export make no inference calls.

```bash
bash scripts/run-library-first.sh run --run EXACT_TECHNICAL_RUN
bash scripts/run-library-first.sh run --run EXACT_COOKBOOK_RUN --allow-owned-handoff
bash scripts/run-library-first.sh status --run EXACT_RUN
bash scripts/run-library-first.sh pause --run EXACT_RUN
bash scripts/run-library-first.sh resume --run EXACT_RUN
bash scripts/run-library-first.sh bundle --run EXACT_RUN
```

The persistent wrapper retains its ownership locks and resource checks. Its
finished resume makes zero requests; uncertain reservations require reconciliation.
These new explicit pointers do not replace production or monitoring pointers.

### 16 November diagnostic qualification update

The previously blocked normal-terminal socket tests passed, as reported by the
operator. `prepare_markdown_qualification.py refresh --parent EXACT_PREPARATION`
links only an idle, isolated, unpaid, zero-call/zero-launch preparation to current
code. It preserves prepared source bytes, unit ownership and finite task IDs;
started preparations cannot use this path. Production pointers are not updated.

Standard TeX/AMS mathematical-command recognition (including `\prime` and arrows)
is not viewer qualification. Unknown source macros remain verbatim and unresolved;
known extension-dependent notation is labelled separately. No MathJax/Obsidian
rendering is inferred from passing the validator. Coverage accepts exact retained
bibliographic entries and styled proof pointers; arbitrary prose mentions and
generated notes cannot satisfy the corresponding legacy source heading.

### 16 November live results and remaining limitations

The three technical units completed six total requests with no new OCR. A
supported drain and linked saved-response continuation handled a three-backtick
envelope and an inequality/HTML-normalization false positive without repeating
the five consumed requests. The final code suite ran 1,014 tests with no failures
or errors and four optional skips; the operator-qualified 23 socket tests were
reused with unchanged hashes.

The cookbook completed all 28 OCR pages and 12 work requests. Six conversion
drafts cover 20 pages; the eight index pages remain explicitly outstanding because
their entry groups lack qualified split boundaries. Five review responses are
valid, one is invalid JSON, and one valid review attests further findings remain.
One draft and its review retain raw TeX headings; the validator correctly flags
them and does not select the review. No retry or new unit was added.

Direct source checks found useful numerical corrections, but also a disputed
print reading, a still-incorrect replacement, and missed fractions. Reviewed
derivatives are model claims, not automatically accepted source corrections.
The technical sample retains inherited composite/panel duplication and imperfect
Markdown footnote representation. Structural HTML was produced with markdown-it;
MathJax, Obsidian, mathematical browser rendering and footnote extensions remain
unqualified. Firefox could not start under the current snap confinement; no
permissions or services were changed to bypass that restriction.

Full evidence, source crops, per-unit/per-request statistics and the inspection
archive record are under `results/markdown-qualification-20261116/`. Read its
`REPORT.md` and `INSPECTION.json`. Both workers stopped; the original GLM serving
configuration was restored and production/library/monitor records were unchanged.
The benchmark is intentionally outside the quantitative collection.

## 16 November 2026 — bounded Obsidian compatibility derivatives

The user's actual Obsidian inspection found literal `\(...\)` inline math and
unlinked superscript notes. `probe/markdown_compat.py` now normalizes recognized
balanced inline spans to `$...$` with delimiter-adjacent whitespace removed, while
retaining inner mathematical bytes. Code/fences, literal HTML code/pre, comments,
escaped currency, existing dollar/display math, and ordinary superscripts are
protected. Unknown or ambiguous transformations remain findings.

A source-classified footnote must match its definition and unique contextual
reference before conversion to `[^id]`. Existing descriptive Markdown note IDs
are valid too. Expected source-note coverage is checked independently of whether
any Markdown notes were found; ten source notes versus zero definitions is a
failure. References cannot be silently retargeted by review edits. Unnumbered
source notes receive a visible source locator without an invented marker.

Standalone raw TeX headings are converted only against matching source titles;
recipe Notes are subordinate to the containing numbered recipe. Cross-page
sentence splits are reported for checking, not automatically merged. A merge
requires explicit original-image evidence and exact owned source-block hashes.
The saved CMS sentence and two cookbook paragraph joins qualify under this rule.

The normal version path saves `before-normalization.md`, `normalization.json` and
`normalization.diff`; normalized converter bytes/hash become the critic's exact
input. Post-review formatting has a new derivative identity and explicit status:
the prior review did not examine transformed bytes. Publication and inspection
bundles preserve these artifacts. This does not reseal old runs, reset attempts,
or claim source fidelity from compatible syntax.

Offline repair report/vault: `results/markdown-obsidian-repair-20261116/REPORT.md`.
Six saved samples include Pykhtin, CMS, sauce recipes41–49, Fish Stock/Roux,
conversion tables and an unchanged figure control. Three independently supported
saved sauce edits are recovered separately from format changes. The remaining
shallot quantity, disputed/wrong earlier reviews, index gaps and inherited figure
duplication remain explicit. Historical sources/selections are unchanged.

Installed Python-Markdown's footnote extension produced ten Pykhtin links and ten
backlinks with valid targets. Structural table/heading/asset checks ran. Obsidian
Reading view/Live Preview and MathJax have **not** been qualified here: Firefox
snap refused startup, and no Obsidian application could be operated. Formula
bytes were protected rather than typeset in the structural previews. Comment
metadata remains unchanged pending actual Reading view inspection. Open the
packaged vault in Obsidian; rendering and source fidelity are separate questions.

## 16 November — CMS native-table mathematics repair

`obsidian-compat-v2` handles the demonstrated CMS rendering failure before a
new version is validated. A simple rectangular HTML table containing inline
mathematics can become a native Markdown table, preserving its caption, header,
row order and formula content. The safe subset requires a header row, plain
cells and no merged cells, nested markup or display mathematics. Other complex
structures remain unchanged with an explicit unresolved compatibility finding;
raw HTML math is no longer counted as renderer-compatible merely because the
HTML parses.

Pipe characters inside supported mathematical cells use `\vert` / `\Vert`;
prose pipes use an entity. Ambiguous constructs, including a pipe inside a
`\text{...}` argument, are not guessed. Literal code, fences and comments remain
protected, and repeated normalization is idempotent. Every transformation keeps
before/after hashes and a separate formatting log. This does not authorize a
mathematical correction or retroactively extend a historical review to new bytes.

The repaired saved CMS sample retains all four instrument rows, the caption,
unchanged formula strings, and the previously source-checked disclaimer and
sentence join. A real Firefox158 / Python-Markdown3.5.2 / MathJax2.7.9 check
rendered all nine table expressions and all 65 document expressions without a
MathJax error. This browser harness explicitly protects math before Markdown
parsing. It is not Obsidian Reading view or Live Preview qualification; the new
vault remains the application test. The other prior compatibility samples were
copied byte-for-byte and their local asset links checked.

Evidence: `results/cms-cookbook-comparison-20261116/` (CMS diff, browser result
and screenshot, vault content check). The separate quantity comparison in that
directory evaluates a bounded cookbook sample, not a production migration or
whole-cookbook fidelity certification.

### Completed quantity-only follow-up

The six-page comparison finished all 24 requests on 16 November. GLM criticism
returned 148/150 correct unambiguous readings without newly wrong controls;
DeepSeek criticism left 51 quantities unanswered after reasoning exhaustion.
Image-only GLM returned 148/150 with one new error; image-only DeepSeek 141/150
with six new errors. Keep these findings separate from CMS rendering and from
whole-document fidelity. Ten independently source-checked numerical derivatives
are in the new test vault; the ambiguous Brown Veal Stock glyph remains unresolved.
The report and INSPECTION.json are under
`results/cms-cookbook-comparison-20261116/`. No production policy was automatically
changed, and the exact initial GLM serving configuration was restored.
