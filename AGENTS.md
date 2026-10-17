# PDF-to-LaTeX project instructions

## Read first

Read `docs/CODEX-HANDOVER.md`, `docs/PROJECT-STATE.md`, `README.md` and the
relevant parts of `START-HERE.md` before changing this project. The accepted
design is `docs/design/PDF_to_LaTeX_Framework_Design_v1_1.pdf`. Do not invent
missing decisions or treat a planned milestone as completed.

## Working tree only — user's explicit rule

You may edit project files and run suitable checks within the working tree.
The user reviews, stages, commits and pushes personally.

- Never run `git commit` or `git push`, even if a task appears finished.
- Do not stage files with `git add`, create or switch branches, or run fetch,
  pull, merge, rebase, reset, clean, restore or stash. Do not change Git config,
  remotes, tags, the index or other `.git` metadata.
- Read-only Git inspection is allowed: status, diff, log, show and ls-files.
- Do not make GitHub writes, open PRs, create releases, or use another command,
  script, API, alias or tool to perform the prohibited operations.
- Do not change permission settings or these rules to get around a boundary.
- Finish with files changed, what was checked, what remains untested, and an
  optional suggested commit message. Leave every change unstaged.
- Preserve unrelated user edits. If tests require access that the configured
  sandbox denies, explain the specific blocked operation and provide a command
  for the user to run in their own terminal.

## Project scope

Prioritise complete content and mathematical fidelity. Layout matching is not
a goal; figures may remain extracted images. Current work is a compatibility
and fidelity probe: one complete paper, one selected book chapter and synthetic
fixtures. The full-book application is later work.

The conversion pipeline uses local GLM 5.3 Flash and local specialist OCR.
Do not enable OpenRouter or other cloud inference in the conversion program.
Codex's OpenAI connection for development is separate from that program.
Never silently replace GLM with another served model. Verify the intended alias
against actual model-discovery results and the user's launcher information.

## Spark environment

The user reports a two-node GB10 Spark setup; the head is aitopatom-ae2b,
normally mdi@192.168.1.100. The peer alias is spark-92a4. The existing GLM
endpoint is http://192.168.1.100:8888/v1. Recheck current state before using it.

Do not change system Python, TensorFold, drivers, CUDA, model-server settings,
cluster networking or other projects. Do not stop a model or benchmark job.
Keep dependencies in this project's virtual environments. Package/model
downloads and actual inference are separate, explicit operator steps.

## Evidence and continuity

- The delivered probe passed 59 offline tests in the authoring workspace.
  This is not a Spark result or evidence of OCR accuracy.
- No live GLM/OCR or Spark installation was performed before this handover.
- Keep source files and completed attempt evidence unchanged. Preserve hashes,
  original page maps, failed attempts and unaccepted model proposals.
- Do not simplify mathematics, omit conditions, summarise source prose, silently
  repair source errors, or treat image-only formulas as editable transcription.
- Use `python -m unittest discover -s tests -v` in the project controller
  environment when available. Some tests use mock loopback HTTP servers;
  distinguish a sandbox socket restriction from an application regression.
- Update `docs/PROJECT-STATE.md` with observed changes, validation and next work.
  Preserve historical status with dates. Keep selected reviewed evidence in
  `docs/evidence/`; large raw runs and source PDFs remain outside Git by default.
- Do not change `AGENTS.md` unless the user explicitly asks to change project
  instructions. No subagent/delegation workflow is required for this project.
