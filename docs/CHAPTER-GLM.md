# Chapter-context GLM experiment — 26 October 2026

Later 26 October: the operator ran and paused this marker-based experiment. Its
code, nine calls and all evidence are preserved. The new, separately prepared
[simple whole-chapter route](SIMPLE-CHAPTER-GLM.md) supersedes it for the next trial;
use that runbook's launcher. The preparation-era description below is retained as
dated history and is not the current live status.

**Prepared offline, not running. No model request or real compilation has occurred.**
This opt-in experiment uses completed MinerU extraction, regular local GLM to draft
complete chapters, and fresh GLM conversations to review each draft. It is separate
from Qwen source-image review and does not supply visual coverage. All output remains
experimental and UNACCEPTED. The Task 2 integration and completed evidence are retained.

## One normal-terminal launch command

```bash
cd /home/mdi/projects/pdf-to-latex && bash scripts/run-chapter-glm.sh run
```

This discovers the actual prepared run through `results/chapter-glm-current.json`,
verifies its seals/code, checks visible project converter/model jobs, and reads Docker
container names on the head and `spark-92a4` (existing noninteractive SSH). A resident
Qwen/DeepSeek deployment is conservatively a conflict. It then checks the exact
`glm53-regular` alias at `http://192.168.1.100:8888/v1/models` and the existing root
`/health` workload/context counters. Unavailable/busy GLM, inaccessible workload
checks or another heavy deployment produces an error; nothing starts/stops services,
changes permissions, selects another model or sends cloud requests.

It creates persistent tmux session **`chapter-glm`**. Inside it, the controller runs
the full normal-terminal unittest suite, without opting into real compiler tests.
A failing suite stops before inference. A passing result is cached against the exact
controller and test-file hashes, so an unchanged resume need not repeat the suite.
The prepared complete inputs are verified, then **one fresh text-only readiness
request** is captured automatically. An empty/incorrect reply or response model
mismatch fails readiness. No visual preflight or manually pasted directory is used.
The launch prints the actual run/log paths; tests and inference survive desktop
or terminal disconnection. The process exit status is recorded alongside its log.

First expect offline tests in the log, then `Phase/chapter: readiness`, then
`klebaner-04/convert`. Each serial call prints the book, phase/chapter, exact model,
current action and result directory. A tmux session starting does **not** establish
that readiness passed or inference started; inspect status/logs. The wrapper never
runs `scripts/run-gatheral-review.sh`.

## Actual prepared artifacts

- Input: `runs/chapter-glm-input-20261026T031434Z-2392d8`
- Trial: `runs/chapter-glm-trial-20261026T032225Z-ac8537`
- HTML: `runs/chapter-glm-trial-20261026T032225Z-ac8537/report.html`
- Prepared master with conspicuous missing-draft sections:
  `runs/chapter-glm-trial-20261026T032225Z-ac8537/book/master.tex`
- Offline inspection ZIP:
  `results/chapter-glm-inspection-20261026T032341Z.zip`
- Development checks/logs:
  `runs/chapter-glm-development-20261026T024458Z`

The earlier `chapter-glm-input-20261026T025756Z-142f1d` is retained as an offline
development preparation. The final input adds a conservative proof-boundary guard;
no model calls used either preparation. Do not point the launcher at that earlier
input or create another trial to reset budgets.

Input `chapters/<key>/source.tex`, `source.json` and `inventory.json` retain complete
native text, source IDs, ordered blocks, source-page maps, asset references and
literal formula strings. Trial `prepared/<key>/conversion-request.json` contains
the exact initial request. Review requests depend on actual completed TeX and are
saved immediately before dispatch, not fabricated in advance. Their full extracted
chapter and generated TeX remain intact. Available exact same-edition references
and definition blocks are bounded separately; omissions/uncertain context are
recorded in `context-inventory.json` and are not treated as reviewed targets.

The current offline ZIP includes complete source extracts and native sidecars,
request/settings/budget records, coverage, the placeholder master, and one shared
set of 104 needed assets (including front/index facsimiles). Full source evidence
and additional native formula crops remain in the input preparation/original runs.
After execution, the same bundle operation also includes generated chapter TeX,
reviews, final-channel text from failed attempts and available compiler logs/PDFs.
Full raw HTTP responses and reasoning remain in the run; no old archives or model
weights are copied. The inspection package is book material, not credentials.

## Scope and actual extraction checks

The saved-page reader and `book_review.owned_scope` verify completion, integrity,
original-page maps and one owner per page/block. Overlap/context pages are excluded.
The installed DocVortex `render_latex` renders individual native blocks using the
existing MinerU interpreter, without OCR/model imports or conversion execution.
There is no restrictive portable-export grammar in the chapter input path. Renderer
limitations retain complete raw native records and explicit fallback information.
Tables use their actual source crops/captions; editable table fidelity is not claimed.

The apparent `KeyError: 'blocks'` came from assuming every native page has that
field. Actual Gatheral records for PDF 3, 9, 15, 21, 23, 31 and 199 contain only
`page_idx`; the installed Middle 2.0 `PageInfo.blocks` defaults to an empty list.
This route explicitly supplies those seven verified blank pages to the existing
reader. Missing/null blocks on another page, or nonempty data on a verified blank,
remain errors. Old evidence and the default strict reader behavior are unchanged.

Read-only checks compared **every prepared block** back to its actual owned-page
record: Gatheral 210 pages/2,184 blocks; Klebaner 31 pages/514 blocks. Complete native
content round-trips exactly, and all 1,850 native mathematical strings occur in the
source extracts. This establishes input preservation, not correct OCR or final
transcription fidelity. Native prose, footnotes, captions, bibliography, unnumbered
equations and page furniture are represented; page furniture may stay comments in
output. Gatheral retains 43 chart, 12 main-text image, 12 table and two front image
blocks, plus all 76 bibliography `ref_text` blocks. Counts are blocks, not unique
figures. All 721 consumed evidence files passed their recorded hashes after preparation.

Klebaner comparison: saved conversion `runs/convert-basic-20261020T075104Z-48fd90`,
source `klebaner-ch4-7`, selected pages 1–31, original PDF 106–136, printed 91–121.
No separator PDF 137 or Chapter 5 is included. No independent `ch4.tex/ch4.pdf`
was found in the obvious supplied input locations; this did not block preparation.
No independent audit findings or expected answers entered requests.

Gatheral uses `runs/convert-basic-20261025T230247Z-e6bb30`, source `gatheral`,
27 completed windows and all 210 owned physical pages. The explicit user-provided
boundaries, not title-classification heuristics, are:

| Part | Physical PDF pages | Printed pages |
| --- | --- | --- |
| Front matter | 1–31 | Roman/unnumbered |
| 01 Stochastic Volatility and Local Volatility | 32–45 | 1–14 |
| 02 The Heston Model | 46–55 | 15–24 |
| 03 The Implied Volatility Surface | 56–73 | 25–42 |
| 04 The Heston-Nandi Model | 74–80 | 43–49 |
| 05 Adding Jumps | 81–104 | 50–73 |
| 06 Modeling Default Risk | 105–117 | 74–86 |
| 07 Volatility Surface Asymptotics | 118–131 | 87–100 |
| 08 Dynamics of the Volatility Surface | 132–137 | 101–106 |
| 09 Barrier Options | 138–152 | 107–121 |
| 10 Exotic Cliquets | 153–163 | 122–132 |
| 11 Volatility Derivatives | 164–192 | 133–161 |
| Postscript | 193 | 162 |
| Bibliography | 194–198 | 163–167 |
| Intentional blank | 199 | 168 |
| Index | 200–210 | 169–179 |

Front matter/index use labelled source-page facsimiles in the assembled book and
keep their native source text separately. Index page references remain the original
printed numbers. The seven verified blanks consume no model requests. Postscript
and bibliography preserve native OCR as a labelled fallback until a GLM draft is
available; repeated-author text is retained without external bibliographic lookup.

## Capacity, settings and bounded adaptation

The installed regular GLM launch configuration documents `MAX_TOKENS=32768` as its
default. This route requests **32,768 tokens**, counting reasoning and final output
together. It requests no sampling/thinking/effort override: Open WebUI settings were
not supplied, and server interpretation is not established. This is a new
MinerU-input experiment, not an exact Open WebUI replay. Each request permits at
most **2,700 seconds**, reduced to the remaining wall allowance (readiness: 120s).

`tokenizers available False` is **not a missing runner dependency**. Nothing is
installed. The controller measures complete serialized UTF-8 request bytes, adds
4,096 tokens of template margin and the full output allowance, and checks that
conservative estimate against the effective `context_length` returned by `/health`.
It also retains the existing 2 MiB transport cap. For the documented byte-level
text-tokenizer family this intentionally overestimates ordinary text token count;
it is not an exact tokenizer measurement or a guarantee about hidden server work.
A smaller effective window can therefore reject a request that an exact tokenizer
would admit. Such a request remains an explicit gap; no clipping or unverified
context-setting change is made. Actual server usage is recorded when returned.

Largest source extracts: Klebaner Chapter 4 **118,128 characters**, Gatheral Chapter
11 **78,168**. Initial conservative input-plus-output admission values are **178,009**
and **128,914** respectively. Reviews include the exact generated TeX too, and are
checked again at dispatch; their size cannot be known before generation.

Default: one conversion and one independent review per chapter. A `length` response,
reasoning-only empty response, missing tail or missing block accounting is never a
complete chapter. Where a defensible native section boundary is available, at most
two section outputs replace a failed whole output; **each retains full chapter
context**. Boundaries are whole blocks at major section headings, never an arbitrary
character cut. An unclosed proof blocks lesser heading splits; an explicit major
numbered section supplies a structural boundary even if OCR lost a proof square.
Gatheral Chapter 7 currently has no admitted fallback boundary: an output-exhaustion
failure there stays unresolved rather than guessing. Structural boundary/marker
checks do not prove semantic preservation. Exact completion markers are mechanical
accounting, not a length heuristic or mathematical validation.

Order: Klebaner conversion/review; all eleven Gatheral conversions; all eleven
Gatheral reviews; postscript and bibliography conversion/review if time remains.
Each planned task shares **at most two additional calls**, including splits and
format feedback. There are **80 total inference calls**, including all readiness,
failed, split and repair calls. The **eight-hour wall deadline starts at first
inference dispatch**, includes idle time, and persists across resume. Expiry needs
a deliberate future extension, never an automatically new run. Missing usage
counters remain unknown, not zero-token claims.

Calls are reserved durably before dispatch; raw responses and failed attempts are
retained. Completed work is skipped on resume. An interrupted/unfinalized response
is marked unresolved rather than silently replayed. Identity/integrity failures
stop the controller; repeated connection failures pause it. Isolated content,
format, timeout or capacity failures leave visible gaps while independent chapters
can continue. A writer lock prevents competing project writers. Head/peer container
and server workload snapshots cannot exclude an external client arriving later;
keep this model phase dedicated and do not edit controller code during the run.

## Monitor, pause, resume, bundle

These use the saved pointer, not shell variables or pasted readiness paths:

```bash
cd /home/mdi/projects/pdf-to-latex
bash scripts/run-chapter-glm.sh status
```

Status reads the saved ledger, task outcomes, call count, remaining wall time and
launch exit records. To watch the persistent process, use `tmux attach -t chapter-glm`;
Ctrl-B then D detaches without stopping it. The launch prints its actual log under
the trial's `launches/` directory. A finished tmux session may disappear; its log
and `exit.json` remain.

```bash
bash scripts/run-chapter-glm.sh pause
```

Requests a stop after the current bounded call, preserving it. This does not stop
GLM. Wait for the writer/session to finish; idle time still counts.

```bash
bash scripts/run-chapter-glm.sh resume
```

Resumes the **same** bound trial in tmux after checks and one fresh text readiness.
It retains original calls, failures and first-dispatch deadline. It refuses a
changed code/input binding or an existing chapter session. A completed but unfinalized
interrupted request remains explicitly unresolved and is not dispatched again.

```bash
bash scripts/run-chapter-glm.sh bundle
```

After the writer exits, creates a new compact inspection ZIP and prints its actual
path. The controller also bundles automatically when it stops normally. Bundling
while a writer holds the project lock is refused; status remains read-only.

## Compilation and interpretation

The runtime uses only the qualified immutable image
`sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45`.
It never pulls/builds an image or uses system TeX. Explicit relative PNG/JPEG/PDF/TeX
assets under `assets/` or `parts/` can join the disposable build tree; traversal,
symlinks, collisions and nonallowlisted formats are rejected. Read-only `/source`,
separate `/work`, relative `document.tex`, paranoid input/output policies, non-root,
network isolation, disabled shell escape and all existing resource limits remain.

Complete chapter documents are compiled when feasible. Infrastructure/policy failure
is separate from document failure, and disables repeated unavailable compiler
attempts. No automatic semantic suggestion or compiler repair overwrites a draft.
The complete assembled book is attempted only when its model parts are available
and time permits; missing chapters remain conspicuous placeholders. TeX/log/PDF
filenames are recorded in actual per-chapter compilation results after execution.
No compilation has been attempted in this sandbox.

Offline validation checks mechanics only. It does not establish GLM quality, final
mathematical fidelity, visual coverage or acceptance. Inspect substantive omissions,
source-author errors, proposed changes and uncertain context before any application.
