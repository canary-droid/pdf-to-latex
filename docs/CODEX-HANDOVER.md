# Active handover — 1 November 2026

**Latest: revised, unified finalisation completed from saved outputs.** Read the
latest PROJECT-STATE entry and `results/book-finalisation-current.json`.
The controlling instruction is
`/home/mdi/Downloads/Codex-Book-Finalisation-2026-11-01.txt`, whose opening explicitly
identifies it as the REVISED, UNIFIED task. The 35-call completion run has finished;
do not launch it again to obtain these finalisation results. The linked derivative
is `runs/book-finalisation-20261101T154901Z-466f18`; its `FINAL-INDEX.md` lists the
reading PDFs and all exports. Gatheral has 34/34 selected PDF parts and Bergomi
61/61, with no PDF gaps. This is not a mathematical-verification certificate.

Converter/critic prompts, mathematical correction policy, reasoning and acceptance
rules are unchanged. Finalisation used no new inference. The specifically
authorized French dependency was added only to a versioned isolated compiler
image; no global host package, service or permission change was made. Stop after
delivery; article processing, another queue and supervision remain out of scope.

## Earlier 1 November completion preparation — historical

The user explicitly authorized completion of the existing Gatheral and Bergomi
working editions. Read [BOOK-COMPLETION.md](BOOK-COMPLETION.md) and the latest
PROJECT-STATE entry. The controlling instruction is
`/home/mdi/Downloads/Codex-Finish-Gatheral-Bergomi-2026-11-01.txt`.
Reconcile saved production/speed/overnight outputs before scheduling genuinely
missing content; do not blindly resume the old production queue or repeat suites.

The approved route uses native MinerU plus corroborating native PDF text, full
coherent assigned spans, High GLM conversion and Max own-draft criticism, 131072
output tokens and at most two owned requests. Existing outputs/drafts remain
traceable; grouped documents occur once. No OCR rerun, model installation, service
switch, cloud dispatch, permission change or autonomous code promotion is part
of this completion. Supervision qualification is a separate unfinished project.

Implementation/preparation is not inference authorization during the coding task.
The one normal-terminal completion launch performs its own required checks and
fresh readiness, processes the finite missing-only queue, assembles and packages
both books, and exits without inspection stops. Explicit pause/resume remain.
Read the current completion pointer/state before launch; a prepared run is not
running. Compilation, target accounting and critic claims are not fidelity proof.

## Historical handover — 17 October 2026

27 October extraction task: [BERGOMI-EXTRACTION.md](BERGOMI-EXTRACTION.md) is prepared,
not running from Codex (Docker/tmux sandbox access denied). Bergomi's actual PDF is
Stochastic Volatility Modeling, CRC Press ©2016, 520 pages/12 chapters. All pages are
registered and native text cached; the supplied PDF lacks the index listed in its
contents. Use the one operator command there. Task 2 must use an independent copy
while extraction is unfinished. Gatheral's latest two-source run has now exited
finished_with_gaps: Chapters 6/7/11 truncated, bibliography conversion/review complete;
preserve its 24 calls. The earlier "not running" entries below are dated preparation
history, not the latest observed execution status.

Current simple-chapter update (26 October): use [SIMPLE-CHAPTER-GLM.md](SIMPLE-CHAPTER-GLM.md)
and the latest PROJECT-STATE entry. The fresh two-source meaning-focused preparation is
`runs/simple-chapter-glm-trial-20261026T212942Z-533351`, not running. It starts at Gatheral
Chapter 1 and pairs each new conversion immediately with its critic through Chapter 11,
then postscript and bibliography. Chapters 3/5 have fresh authorized attempts. No
Klebaner, old drafts or skip list is inherited. PDF pages 32–198 are included; front
matter 1–31, blank 199 and index 200–210 are excluded, so this is not the complete book.
The earlier 11 calls remain unchanged in previous runs. This separately authorized
experiment starts with zero calls and the existing 80-call ceiling across resumes.
No overall/generation deadline; connection timeout remains separate. Before/after
accuracy notes and document versions are retained. Historical failures remain in
their original evidence. This does not restart Qwen, DeepSeek or structured critics.

Task 2 development continuity (25 October): read
[TASK2-DEVELOPMENT.md](TASK2-DEVELOPMENT.md) before integration. Work lives in
`/tmp/pdf-to-latex-critic-development-20261025`; the extraction checkout is separate.
The selected GLM/MiMo calibration described below has completed. New context,
reporting, field-repair and Gatheral-adapter changes must not alter an unfinished
conversion's code fingerprints. Preserve the patch bundle outside temporary storage.

Current policy note (25 October): the conversion remains local. The user authorized
[candidate-only GLM-first criticism and selected MiMo escalation](CANDIDATE-CRITIC.md).
Qwen remains the source-image reviewer; DeepSeek is a selectable text critic.
The twelve-passage [GLM/MiMo comparison](GLM-MIMO-CRITIC-PILOT.md) is complete and
frozen. Next is eight anchored GLM passages, then at most four explicitly selected
MiMo passages; no automatic service-failure fallback. The USD 10 cumulative ceiling
includes the prior USD 0.1717154424, unknown charges and all new readiness/follow-ups.
The configurable budget is sealed; approved increases preserve consumed costs/calls.
Documented retention below 100 days is
accepted for nonpersonal published book material; Xiaomi's 30-day policy qualifies.
No training opt-in, account privacy change, cloud OCR or whole-book upload follows
from this exception. Read the latest PROJECT-STATE entry before continuing.

This repository starter preserves the application and test bytes from
`PDF_to_LaTeX_Local_Probe_v0_1.zip` and adds development instructions. It is not
a new converter release. No Git repository, commit or remote has been created
by the authoring assistant. The user owns all Git mutations and GitHub writes.

## Accepted direction

Build PDF-to-LaTeX reconstruction for technical papers and eventually entire
books, with content and mathematical fidelity first. Reproducing page layout
is unnecessary. Figures can remain images. The currently authorised experiment
uses GLM 5.3 Flash only as the general-purpose LLM; local specialist recognition
models are permitted. OpenRouter is excluded from this probe.

Design 1.1 is bundled in `docs/design/`. The original package documentation
describes the implemented scope and later milestones. The design reused the
Quant Wiki walkthrough 1.1 (25 September 2026), the quant-wiki-spark-pilot skill
revision dated 5 October, and the run-two-spark-models snapshot dated 4 October.
Those full skills are not installed into Codex by this archive; the applicable
project decisions are captured here and in the design. ChatGPT memory or this
conversation must not be assumed available in a new CLI session.

## Actual state at handover

- Probe 0.1 implements inventory, exact local endpoint discovery, text/JSON/basic
  image probes, source preparation, bounded converter windows, page ownership,
  durable attempts, resume checks, memory observations, review and result ZIPs.
- MinerU Basic is the initial local OCR candidate. Its pinned adapter exists;
  ARM64 installation and actual OCR are not qualified yet.
- 59 offline tests passed in the authoring environment. Tests include mocks;
  no successful Spark run or reconstruction score is claimed.
- Inputs are the complete 17-page Guyon/Henry-Labordere paper and Chapter 3 of
  Boyarchenko/Levendorskii: 30 selected pages, original physical pages 89–118
  (printed 67–96). The entire 421-page book is not included.
- Native/scanned two-page mathematical fixtures have a known LaTeX source.
- No probe result from the Spark has been received in this project at handover.

## Immediate next work

1. Establish the user's checkout, Codex sign-in and working-tree-only workflow.
2. Read the existing source and instructions. Report inconsistencies before
   expanding scope; do not redesign the pipeline.
3. Have the user run the existing preflight in their terminal when GLM is free:
   `python3 probe.py preflight --peer spark-92a4`.
4. Inspect its generated JSON/logs. Identify the exact intended GLM alias and
   record missing prerequisites. No automatic OCR installation or model restart.
5. Continue the existing START-HERE sequence after the preflight evidence is
   assessed: isolated Basic setup, fixtures, paper/chapter, bounded GLM review,
   then source-based fidelity checks.

## Repository contents and source data

The starter ZIP includes the original probe inputs so it can run after extraction.
`.gitignore` keeps `inputs/`, environments, model weights and raw runs out of Git.
`sources.json` and `docs/source-provenance/` preserve input identification.
Synthetic fixtures and the design PDF are tracked: there is no blanket PDF ignore.

Keep the starter ZIP as a separate backup for the original inputs. For a fresh
clone, extract that ZIP into a separate temporary folder and copy only its
`inputs/` directory into the clone. Do not overlay old code on a newer checkout.
The supplied hashes will detect accidental changes. The original full book must
be recovered separately if a later milestone requires it.

The original `PACKAGE_MANIFEST.json` is a historical manifest for probe 0.1,
not a live Git inventory. `REPOSITORY_STARTER_MANIFEST.json` identifies this
starter's initial files. Git becomes the record of subsequent reviewed changes;
neither snapshot manifest needs to be rewritten after every development task.

For each useful run, preserve the full result bundle separately and commit a
small reviewed summary under `docs/evidence/`, identifying the source, runtime,
date and bundle SHA-256. A path to a lost raw file is not retained evidence.

## User's development agreement

Codex changes working-tree files only. The user reviews and runs all staging,
commit, branch and push commands. Suggested commit messages are welcome.
Read `AGENTS.md` for the exact boundary. Source credentials and Codex auth files
must not be copied into the repository. This archive contains none.
