# Gatheral extraction launch — 25 October 2026

**Observed completion, 25 October 2026, 23:36 UTC:** the actual run is `runs/convert-basic-20261025T230247Z-e6bb30`; `conversion_completed_unreviewed`, 27/27 windows and 210/210 owned pages, with no visible project converter/launcher. These are extraction completion facts, not fidelity findings. Do not restart extraction from the historical launch instructions below. Use [GATHERAL-REVIEW.md](GATHERAL-REVIEW.md) after guarded integration; no review preview has yet been created.

Book: Gatheral, The Volatility Surface. Phase: MinerU extraction of 210 physical pages.

Preparation is complete; extraction has not started. Source ID **`gatheral`**
selects physical pages 1–210, including all front matter, appendices within that
span, bibliography and index. The existing intake hash/page metadata is reused;
no new PDF audit, copy or discretionary checksum was performed. `ocr_mode=auto`
uses the established native-text policy. Every selected page maps to the same
original physical page. Existing PDF labels and intake metadata remain intact.

## Finish current work and free the local model's memory

Inspect running project jobs and both nodes. Wait for active jobs to finish in
their own tmux panes; do not stop a deployment while requests are active. These
snapshots are not proof that every external client is idle. The saved MiMo job is
remote but may hold this project's writer lock: let it finish as well.

```bash
cd /home/mdi/projects/pdf-to-latex
tmux list-sessions
ps -u "$USER" -o pid,etime,args | rg 'probe|mineru|tensorfold|deepseek|glm|qwen'
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}'
ssh -o BatchMode=yes -o ConnectTimeout=10 spark-92a4 \
  'docker ps --format "{{.Names}} {{.Status}} {{.Ports}}"; free -h'
```

For the last local phase, **regular GLM**, use its existing helper only after
its jobs have finished and the checks identify that deployment. It stops its
configured head/peer containers and retains their logs; it does not drain requests.
Skip if GLM is already stopped. Leave unrelated deployments and downloads alone.

```bash
(cd /home/mdi/local-llm/glm53-flash-tensorfold && ./stop.sh)
free -h
ssh -o BatchMode=yes -o ConnectTimeout=10 spark-92a4 'free -h'
```

If checks instead identify **idle Qwen**, its existing alternative is:

```bash
bash /home/mdi/local-llm/flash-next-tensorfold/spark-tensorfold.sh stop
```

If they instead identify the **idle retained DeepSeek pair**, use its owned-run
helpers (ownership mismatches must stop, never bypass them):

```bash
bash /home/mdi/local-llm/deepseek-flash17-setup/first-serve-853310da-v1/kit-20261022/node.sh \
  stop 0 20261022T070227Z-1623611
ssh -o BatchMode=yes mdi@192.168.100.2 \
  'bash /home/mdi/local-llm/deepseek-flash17-setup/first-serve-853310da-v1/kit-20261022/node.sh stop 1 20261022T070227Z-1623611'
```

Run only the applicable stop block, then check both nodes' `free -h` as above.
Basic keeps the existing **8 GiB available-memory floor**, CPU/ONNX execution,
3600-second per-window timeout, installed `.venv-mineru` MinerU **4.0.12** and
`model-cache`. `--ocr-isolation none` means local processing without OS network
isolation, with the existing offline worker controls. No thresholds are lowered.

## Launch or resume — the same command

Start/reattach tmux, then enter the second block inside its shell:

```bash
tmux new-session -A -s gatheral-extraction
```

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -B scripts/run-gatheral-extraction.py run
```

The wrapper selects only `gatheral`, discovers any saved conversion and passes its
actual directory to the existing `--resume` option. Multiple/mixed Gatheral runs
are refused. The existing project-wide writer lock covers discovery and dispatch;
another writer causes a stop, never a competing run. No manual run-path variable
is needed. stdout/stderr and the converter's exit status are retained in a new
`runs/gatheral-operator/<timestamp-id>.log` on every invocation. The wrapper returns
that status (0 success, 75 memory pause, 130 interrupt, nonzero failure).

First expect `Fingerprinting converter model files...`; normal runtime/source
checks can take time **before a conversion directory exists**. Then the converter
prints its actual `Conversion run: ...` and
`Converting gatheral-0001-0008 with adjacent context`. The first input covers
physical pages 1–9, owning 1–8. In total: **27 windows, 210 distinct owned pages**,
262 input-page occurrences including context, at most ten pages per window. The
last window owns 209–210 and includes context page 208. Context is not counted twice.

Detach without stopping: Ctrl-B, then D. One read-only progress command, usable
from another terminal, finds the actual run and prints owned-page/window counts
and the current worker-log path:

```bash
cd /home/mdi/projects/pdf-to-latex
.venv-control/bin/python -B scripts/run-gatheral-extraction.py status
```

**Pause:** press Ctrl-C in the running extraction's tmux pane and wait for its
shell prompt. This stops only the owned converter child; completed windows remain.
The interrupted window's evidence is retained and that window is retried on
resume. The recorded status may still say `running`; `interrupted.json` marks the
interruption. **Resume:** run the identical `run` command above. Do not launch a
fresh direct conversion or edit state to bypass fingerprint checks.

## Outputs and fixed execution directory

The actual directory is created at launch under `runs/convert-basic-*`; no future
path has been fabricated. Expect `state.json`, per-attempt `input.pdf`,
`page-map.json`, `worker.log`, resource/completion records and `output/` containing
structured native OCR `raw_middle_json.json` / `middle_json.json`, `images/`,
`markdown.md` / `document.md`, native draft `document.tex`,
`review_candidates.json` and `summary.json`. On ordinary completion or a handled
failure/memory pause, existing reporting produces `review.html`,
`quality-report.json` and a `results/*-upload.zip`. Ctrl-C does not promise a new
report/ZIP; saved attempts and terminal logs still remain. These are unreviewed
window exports, **not the final reviewed book**. Context repeats in window drafts;
no visual or mathematical accuracy/compilation is established by extraction.

Execution stays in **`/home/mdi/projects/pdf-to-latex`**. Resume binds selected
source metadata/hash, all top-level `probe/*.py` contents, converter packages and
model-file hashes, worker code, window/overlap, memory floor, timeout and isolation.
Completed output manifests and input/page-map hashes are rechecked. Even an
unrelated critic-module edit in `probe/` would invalidate resume. Keep this checkout,
source, settings, environments and model cache fixed after launch. The later task
must use an ordinary separate DEVELOPMENT COPY including current uncommitted files;
it must not write through symlinks into this execution checkout or its environments
or cache. No execution-snapshot framework or second development copy is created here.
