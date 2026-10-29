# Bergomi extraction — 27 October 2026

**Prepared, not running.** Docker and tmux access are denied in the Codex sandbox.
No service was stopped, no OCR/model request was made, and no conversion run exists
yet. The operator launch below performs the authorized idle-GLM-to-MinerU transition.

```bash
cd /home/mdi/projects/pdf-to-latex && .venv-control/bin/python -B scripts/run-bergomi-extraction.py run
```

This validates the existing intake/registry, runs the nine focused launcher tests,
acquires both project/converter writer locks, checks the completed Gatheral writer
and visible project jobs, and checks deployments on both nodes. An unknown/alternative
deployment blocks launch and remains untouched. The known Open WebUI client container
may stay resident; GLM's exact model identity and active/queued stream counters must
establish an idle server. Missing/ambiguous health or a peer-only deployment blocks
the transition. The wrapper checks the existing helper's configured container,
worker and port before using `/home/mdi/local-llm/glm53-flash-tensorfold/stop.sh`.
That helper stops its owned head/peer pair and saves their service logs. No other
deployment is stopped. Both nodes are rechecked afterwards; head available memory
must meet the unchanged 8 GiB floor. These checks cannot exclude a new external
client racing the transition; do not submit other model work during extraction.

The command starts persistent tmux session **bergomi-extraction**, prints the source
and terminal log, and invokes the existing Gatheral wrapper with source **bergomi**.
The worker checks again that no heavy deployment became resident before dispatch.
No GLM conversion, visual review, paid request, dependency installation or model
download is performed. If a dependency, permission, job or service check fails,
the command gives an explicit diagnostic instead of switching models or proceeding.

## Observed source and selection

Lorenzo Bergomi, **Stochastic Volatility Modeling**, Chapman & Hall/CRC, Taylor &
Francis Group, copyright **2016**, PDF version date **20151105**, PDF eBook ISBN
**978-1-4822-4407-6**. The inspected title/copyright pages do not state a numbered
edition; no first/second edition is assumed. Physical title/copyright/contents
pages 6/7/8 and the back cover were visually inspected; the contents and every
chapter-opening native text were checked against the bookmarks.

Source: `/home/mdi/projects/pdf-to-latex/inputs/bergomi/source.pdf`,
105,214,331 bytes, **520 physical pages**, SHA-256
`35fd11fb3fe46e9c3de01db6b22dc1e2c848c04b352121fe13c3ccf0fba38413`.

| Part | Physical PDF pages |
| --- | --- |
| Front matter, contents and preface | 1–17 |
| 1 Introduction | 18–41 |
| 2 Local volatility | 42–119 |
| 3 Forward-start options | 120–149 |
| 4 Stochastic volatility – introduction | 150–167 |
| 5 Variance swaps | 168–217 |
| 6 An example of one-factor dynamics: the Heston model | 218–233 |
| 7 Forward variance models | 234–323 |
| 8 The smile of stochastic volatility models | 324–373 |
| 9 Linking static and dynamic properties of stochastic volatility models | 374–407 |
| 10 What causes equity smiles? | 408–437 |
| 11 Multi-asset stochastic volatility | 438–469 |
| 12 Local-stochastic volatility models | 470–511 |
| Epilogue | 512–513 |
| Bibliography | 514–519 |
| Back cover | 520 |

Main-text printed page = physical PDF page −17. Chapter ranges include their embedded
mathematical appendices and any following separator page. Native text declares pages
5, 119, 149, 217, 323, 373, 407, 437 and 469 intentionally blank; all remain selected.
Pages 1 and 520 have no native text but are image covers, not blank pages.

**Source limitation:** contents lists an index beginning at printed page 503, but
the supplied file ends with bibliography printed page 502 at physical 519, then
the back cover. The absent index cannot be extracted from this file. All supplied
pages are included; this is not a claim that the supplied PDF contains every page
of the published book.

## Prepared evidence and output

- Source ID `bergomi` in `sources.json`; `ocr_mode=auto` because native text is
  present. Existing registrations, including Gatheral, remain unchanged.
- `inputs/bergomi/intake/metadata.json`: source identity, all physical-page maps,
  PDF labels, raw bookmarks and extractor/version. Generic bookmark sections are
  evidence, not automatic chapter adjudication; the source-checked interpretation
  is `docs/source-provenance/bergomi-intake-20261027.json`.
- `inputs/bergomi/intake/native/page-NNNNNN.txt`: all 520 native-text pages, including
  empty ones, with no removal of numerals, formulas or references. Total 1,013,219
  characters. This is secondary text, not OCR or verified mathematical transcription.
- `inputs/bergomi/intake/report.html`: readable title/copyright/contents evidence,
  bookmarks and links to every page's native text.
- `inputs/bergomi/intake/window-plan.json`: **65 windows**, eight owned pages and
  one adjacent context page on either side where available. Each of 520 physical
  pages is owned exactly once; context is not counted twice.
- `runs/bergomi-operator/preparation.json`: current code/configuration/source/cache
  identity and offline-check result. Raw books and generated artifacts stay ignored.

At launch the existing converter fingerprints installed packages, worker and model
cache before printing its **actual** `runs/convert-basic-...` directory. The startup
delay can therefore precede the first window; it is not proof of a stalled model.
The wrapper prints `runs/bergomi-operator/launch-.../terminal.log` and records the
active launch in `runs/bergomi-operator/current.json`. No future run name is invented.
Each launch saves an execution identity, service/memory checks, logs and exit status.

Basic remains the installed MinerU **4.0.12**, DocVortex **0.5.16**, existing
`.venv-mineru`, `model-cache`, CPU/ONNX Basic, `--ocr-isolation none` and existing
offline worker controls. There is no overall deadline. The established per-window
3600-second timeout and memory floor remain. Successful windows retain native
structured OCR, assets, page maps, Markdown/TeX draft exports and candidate records.
The converter produces `review.html`, `quality-report.json` and an upload ZIP on
ordinary completion or handled failure. These are unreviewed extraction outputs,
not a GLM rewrite or a final accepted book.

## Progress, pause/resume and bundling

```bash
.venv-control/bin/python -B scripts/run-bergomi-extraction.py status
```

Read-only: reports actual run, owned-page/window counts, pending/failed windows,
worker logs and the latest terminal log/exit record. To watch the persistent terminal,
use `tmux attach -t bergomi-extraction`; Ctrl-B then D detaches without stopping it.

```bash
.venv-control/bin/python -B scripts/run-bergomi-extraction.py pause
.venv-control/bin/python -B scripts/run-bergomi-extraction.py resume
.venv-control/bin/python -B scripts/run-bergomi-extraction.py bundle
```

Run these separately as needed. Pause sends Ctrl-C's SIGINT only to the verified
owned tmux worker; the existing converter cleans up its current child process and
retains interrupted evidence. Wait for its exit before resume. Resume rechecks
workloads and uses the actual existing run; it never redoes intact completed
windows. It retries incomplete windows in new attempt directories. The existing
converter stops on a failed window; later pages remain pending, not discarded or
reported complete. A bundle after pause/completion reuses existing reporting and
creates a new result ZIP without replacing previous ones. The native cache remains
separately under `inputs/bergomi/intake`; the converter ZIP is its saved run evidence.

## Task 2 separation and checks

Execution directory is **/home/mdi/projects/pdf-to-latex**. Resume binds all top-level
`probe/*.py`, source identity, settings, worker, installed converter packages and
model-file hashes, plus completed outputs and page maps. Do not edit these during
an unfinished extraction. Task 2 must work in an ordinary independent development
copy including current uncommitted work; no source symlinks/hardlinks back here,
no shared environment/cache changes. The launcher scripts/configuration/registry
are also recorded in the launch identity. No execution-snapshot framework was added.

Offline checks: **55 tests passed**, covering intake, source-specific launch/resume,
ownership, blank/empty page retention, changed evidence, service guards, existing
converter resume/integrity, interruption and isolation reporting. Python syntax and
`git diff --check` passed. Actual Docker/tmux/SSH transition and live OCR remain
operator-only checks because the sandbox denies Docker and tmux access. No permission
changes were attempted. Gatheral's latest writer exited at 05:29:11 UTC on 27 October;
24 calls remain recorded, Chapters 6/7/11 are truncation gaps, bibliography conversion
and review are complete. This task did not change its evidence.
