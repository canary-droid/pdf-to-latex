# PDF to LaTeX: first local probe

This is version 0.1 of the **probe package**, built from design 1.1. It uses your
existing local GLM endpoint and local specialist OCR software. It has no cloud
model adapter and never calls OpenRouter. It does not stop, restart, reconfigure
or install anything into TensorFold.

## 1. Start on the head Spark, with the model free

Extract the ZIP into a new directory, for example
`~/local-llm/pdf2tex-probe-v0.1`. Keep the extracted folder intact. Use the
existing authorised restricted worker account if already configured. Do not run
this as host root or with sudo. Wait for active benchmarks or an ongoing GLM
answer to finish; the probe shares the existing endpoint.

Confirm that endpoint is serving **GLM 5.3 Flash**. Automatic discovery requires
one GLM-labelled model and will not substitute a sole unrelated model. A server
alias is not proof of the underlying weights; confirm it against your launcher.

In a terminal inside the extracted `pdf2tex-probe-v0.1` folder, run:

```bash
python3 probe.py preflight --peer spark-92a4
```

`spark-92a4` is your previously reported second-node SSH alias. If that alias is
not available to this account, the second-node check is recorded as unavailable;
the local model checks can still run. You can omit `--peer spark-92a4` for a
head-only check. SSH is noninteractive and requires an existing trusted host key;
the probe never edits SSH configuration or accepts a new key automatically.

This first command requires only the standard Python installation. It creates
files under `runs/` and `results/`, reads machine information, and makes one model
discovery request and six small generation requests: text, structured JSON,
three digit images and a blank image. It installs nothing and runs no
OCR. It uses the reported `http://192.168.1.100:8888/v1` address. Each request has
a 120-second bound, so an unavailable/busy endpoint can take several minutes.

If discovery finds several GLM aliases, the result explains the ambiguity. Rerun
with the **exact intended ID returned by your server**, for example:

```bash
python3 probe.py preflight --peer spark-92a4 --model YOUR_EXACT_SERVED_MODEL_ID
```

The example placeholder is not a model name. Use `--base-url` only if the actual
LAN address differs. If authentication is enabled, set `LOCAL_MODEL_API_KEY` in
your terminal; do not put the key in configuration or send it with the results.

**Send back the `*-upload.zip` printed at the end, from `results/`.** This is the
first bounded run to review before installing OCR. A failed image test is useful:
the package can still use GLM for text/structure and the local converter for OCR.

## 2. Install the isolated Basic converter after checking the inventory

The package includes all four test inputs; no document copying is required:

| Input | Scope |
|---|---|
| `paper` | Complete Guyon / Henry-Labordère paper, 17 pages |
| `book` | Chapter 3, 30 pages; original PDF pages 89-118, printed 67-96 |
| `fixture-native` | Two-page artificial example with its known LaTeX source |
| `fixture-scan` | Rasterised copy of the same example, with no selectable text |

The book is image-backed with a damaged hidden text layer. The probe forces OCR
for it and preserves the original page mapping. It does not treat that text layer
as an answer key.

Run the explicit setup step only when ready for package/model downloads:

```bash
bash scripts/setup-basic.sh
```

This creates `.venv-control`, `.venv-mineru`, `model-cache`, `mineru-state` and
setup logs inside this directory. It uses no sudo or Docker socket and does not
change system Python. Downloads fetch software/model assets; no PDF is passed
to a download command. The full dependency resolution is captured in the logs.
MinerU 4.0.12 is pinned; ARM64 wheel availability and inference are still checks
to be performed on the Spark. If setup fails, retain `setup-logs/`; do not repair
it by changing TensorFold's packages or the host CUDA installation.

## 3. Exercise the small fixture, then the paper and chapter

Check memory and active workloads first. Basic is CPU-only but uses the same
unified memory as GLM. The starting admission floor is **8 GiB available RAM**;
this is a conservative probe policy, not a measured peak-memory guarantee.
No service is stopped automatically. If the floor is not met, conversion pauses
before dispatch; arrange an idle window and use the existing model launcher only
after identifying its correct stop/restart procedure.

```bash
.venv-control/bin/python probe.py convert --source fixture-native,fixture-scan
.venv-control/bin/python probe.py convert --source both
```

Run the second command only after inspecting the fixture outputs. Each command
prints a run directory and a result ZIP. Inputs are processed in windows of eight
owned pages with one adjacent context page on each side. Completed windows are
retained and verified before reuse. The converter child runs in a separate Linux
network namespace, with no Internet/LAN route; missing assets fail rather than
downloading or invoking a cloud service.

If the system refuses that network namespace, the probe stops with
`blocked_network_isolation` and preserves diagnostics. It does **not** disable
AppArmor, use sudo, give the worker Docker access, or retry online. See README
for the bounded administrator-side alternatives.

Open `review.html` in the printed conversion run directory. It links source-window
PDFs, page maps, raw data, Markdown and the converter's native LaTeX. Extracted
images are retained in each window's output directory. Keep those assets with
its TeX. These are **unreviewed window exports**,
not an assembled final article/book. Compilation has not been performed.

Resume the same run with exactly the same settings:

```bash
.venv-control/bin/python probe.py convert --source both --resume runs/EXACT_CONVERSION_DIRECTORY
```

Use the real directory printed by the earlier command. Changed source, code,
models or completed outputs prevent silent reuse. A memory-pressure interruption
stops only this probe's child process; it never kills GLM or other jobs. Resume is
manual in this probe, not an automatic thermal-management service.

## 4. Ask GLM to inspect a small sample

Once conversion is complete and the existing GLM server is available again:

```bash
.venv-control/bin/python probe.py review \
  --run runs/EXACT_CONVERSION_DIRECTORY \
  --preflight runs/EXACT_PREFLIGHT_DIRECTORY
```

If you selected an exact model alias or another base URL in step 1, copy
`config.example.json` to `config.local.json`, set those two fields, and put
`--config config.local.json` **before** the command name for later calls.

This reviews at most eight bounded candidates, prioritising mathematics/tables
and distinct pages. With failed/unqualified vision it performs syntax/structure
review only. With a passing simple-image test it may inspect source page images;
mathematical visual accuracy remains unqualified. It saves proposals and issues,
never applies edits, and never summarises away source content.

Complete `docs/FIDELITY_REVIEW.md`'s ten targeted checks and record your findings
in a copy of `docs/review-results.csv`. Send the preflight, conversion and GLM
review ZIPs plus that CSV. Failed or partial runs are useful evidence too.

## What follows these results

We will decide whether Basic meets the fidelity requirement, whether to qualify
Standard's separate local VLM runtime, and what the one-paper application needs.
The current package already contains the explicit Standard adapter, but does
not install its GPU runtime or assume it can coexist with GLM. The entire
421-page book, persistent accept/edit/defer UI, final chapter assembly and
controlled TeX compilation belong to subsequent milestones.
