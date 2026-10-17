# Codex handover — 17 October 2026

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
