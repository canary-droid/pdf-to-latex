# MinerU adapter evidence and limitations

Checked 17 October 2026 against the official release and source tag
`mineru-4.0.12-released` (release commit short ID `b7f3dd0`, dated 11 October).
The worker requires this exact installed MinerU version. Dependencies and model
contents must also be recorded: pinning MinerU alone is not a reproducible lock.

Primary release: https://github.com/opendatalab/MinerU/releases/tag/mineru-4.0.12-released

The following tagged source files were read directly from raw.githubusercontent.com
during implementation; no model inference was run:

- `mineru/parser/__init__.py`: `parse(path, tier, ocr_mode, image_analysis,
  page_range, vlm_config)` is a stateless local API. `page_range="all"` covers the
  input PDF, with zero-based source page indices in output.
- `mineru/parser/base.py`: `ParseResult.save(FileBasedDataWriter(...))` materializes
  images on a copy and writes `middle_json.json`, `markdown.md`,
  `structured_content.json`, images and optional raw `model_output.json`.
  `to_json()` alone omits PDF embedded image bytes.
- `mineru/render/latex.py`: `render_latex(middle_json, asset_base_path="")`
  returns a complete UTF-8 document. The adapter reloads the **saved** MiddleJson
  before rendering so asset references match the exported image files.
- `mineru/config.py`: `model.source="local"`, `model.base_dir`,
  `model.small_backend="onnx"`, explicit VLM engine/blank server URL, and disabled
  `llm_aided.features` are real configuration fields. `MINERU_MODEL_ROOT` is not.
- `mineru/model/runtime/device.py`: `MINERU_DEVICE_MODE` and explicit ONNX backend.
- `mineru/model/registry.py`: public `model_repos_for_tier` selects required
  repositories; VLM `vllm` selects original `MinerU2.5-Pro-2605-1.2B` weights;
  ONNX small models select `MinerU-4_models_onnx`.
- `mineru/model/download.py`: `verify_model_repo` is read-only readiness checking;
  configured local source raises on missing assets instead of downloading.
- `mineru/model/vlm/runtime.py` and `engine_utils.py`: a selected vLLM engine uses
  native asynchronous vLLM, not an external inference HTTP endpoint. Its default
  memory utilization has a 0.1 floor for large-memory devices. The worker leaves
  the upstream engine implementation intact; its 16 GiB-free gate is a probe
  operating policy, not proof the model fits or that coexistence with GLM is safe.
- `mineru/cli/commands/telemetry.py`: `mineru telemetry disable` is a **Doclib
  daemon** action. The stateless SDK does not create/use that daemon. The worker
  does not invent a MinerU telemetry-disable environment variable or start a
  daemon solely to alter unused state. VLLM/Hugging Face analytics are disabled by
  their environment settings. OS network isolation remains controller-owned.

Source prefix (append a path above):
https://raw.githubusercontent.com/opendatalab/MinerU/mineru-4.0.12-released/

Human-facing reference docs:

- https://opendatalab.github.io/MinerU/usage/sdk_api/
- https://opendatalab.github.io/MinerU/reference/output_files/
- https://opendatalab.github.io/MinerU/usage/model_source/
- https://opendatalab.github.io/MinerU/usage/cli_tools/
- https://opendatalab.github.io/MinerU/usage/tiers/
- https://docs.vllm.ai/en/latest/usage/usage_stats/ (`VLLM_NO_USAGE_STATS=1`,
  `DO_NOT_TRACK=1`)
- https://huggingface.co/docs/huggingface_hub/package_reference/environment_variables
  (`HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`; set before import)

The output documentation still mentions a DocVortex 0.4.19 minimum in places.
The 4.0.12 release/source requires **docvortex>=0.5.16,<1**. Use installed package
metadata and the pinned source dependency contract, not that stale minimum.

## Separate preparation stage (network allowed, no PDF passed)

Use a dedicated Python 3.12 environment/container, with its own pinned lock.
Never run these commands inside TensorFold's environment or against system pip.
The following are verified upstream model-management command forms; resolve the
exact package environment before executing them:

```bash
export MINERU_HOME="/absolute/project-owned/mineru-state"
export MINERU_MODEL_BASE_DIR="/absolute/project-owned/model-cache"
mineru-kit models download --tier basic --small-backend onnx --source huggingface
mineru-kit models verify --tier basic --small-backend onnx
mineru-kit models show
```

For the **optional independently prepared vLLM** environment:

```bash
mineru-kit models download --tier standard --small-backend onnx --vlm-engine vllm --source huggingface
mineru-kit models verify --tier standard --small-backend onnx --vlm-engine vllm
```

These commands create provider-selected model directories and completion markers
beneath `MINERU_MODEL_BASE_DIR`; do not invent their contents or synthesize markers.
The worker receives the identical root via `--models-dir`. No downloaded model
repository is treated as verified ground truth. `--probe-runtime` hashes actual
files (excluding provider `.cache` bookkeeping) and reports upstream readiness;
these hashes support identity/repeatability, not authenticity or fidelity.

MinerU's local loaders still acquire lock files under
`MINERU_MODEL_BASE_DIR/.locks`, even when every model is already present and the
source is `local`. Keep that bookkeeping directory writable. A fully read-only
model-root mount can fail; weight subdirectories can be mounted read-only with
separate writable lock bookkeeping. The worker does not download missing files.

## Execution contract

The controller runs the isolated interpreter with `--input PDF --output EMPTYDIR
--tier basic --ocr-mode auto --models-dir ROOT`. `--tier standard --engine vllm`
is explicit opt-in, needs a qualified CUDA/vLLM installation and sufficient free
memory, and never falls back to another engine. The worker selects ONNX CPU for
small models in both modes. The root controller owns original-book window/page
mapping, process resource limits, timeout and process-group cleanup. Since the
18 October 2026 operator decision, `--ocr-isolation namespace` (default) requires
an actual network namespace; explicit `--ocr-isolation none` launches the same
worker directly: local processing; no OS network isolation. The Python guard is
best effort in either mode. Loopback may be needed inside a selected namespace
for native vLLM IPC; failures never trigger fallback to a different isolation mode.

`--probe-runtime --output EMPTYDIR --tier ... --models-dir ROOT` checks packages,
device availability and model readiness/hashes without opening a PDF or running
OCR. It is **not** an inference compatibility test.

Exit 0 means requested files were exported (or runtime preflight passed).
Exit 2 means preflight blocked; exit 3 means extraction/export failed. On an
accepted output directory, `summary.json` records status. A successful export
remains `extracted_unreviewed`, including when page coverage checks find gaps;
the controller must inspect the diagnostic fields. No mathematical correctness
claim follows from success or LaTeX document delimiters.

`review_candidates.json` is a convenience view of native top-level blocks.
`native_content` is retained verbatim as a JSON value; `text` joins native inline
span strings without inserting or repairing mathematics. Its kind is the native
backend label, not a verified classification. Overlong convenience text is
explicitly flagged, and the full native content/raw output remains available.

The socket audit guard denies non-loopback Python network calls. It does not
constrain native libraries or child processes and is not a replacement for the
controller's OS-level egress restriction. No live Spark access, package install,
OCR inference or native LaTeX compilation was performed while writing this module.
