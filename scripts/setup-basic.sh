#!/usr/bin/env bash
# Explicit setup step. Downloads packages/models, never sends a source document.
set -euo pipefail
probe_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$probe_root"
python3 -c 'import sys; assert (3,10)<=sys.version_info[:2]<(3,15), "Use Python 3.10-3.14; do not replace system Python"'
mkdir -p setup-logs
setup_id="$(date -u +%Y%m%dT%H%M%SZ)"
exec > >(tee "setup-logs/setup-$setup_id.log") 2>&1
prepare_owned_env() {
  local env_path="$1"
  if [[ -L "$env_path" ]]; then
    echo "Refusing symlinked environment: $env_path"; exit 2
  fi
  if [[ -e "$env_path" && ! -f "$env_path/.pdf2tex-owned-env" ]]; then
    echo "Existing unowned environment: $env_path. Nothing installed into it."; exit 2
  fi
  if [[ ! -e "$env_path" ]]; then
    python3 -m venv "$env_path"
    touch "$env_path/.pdf2tex-owned-env"
  fi
  "$env_path/bin/python" -c 'import sys; assert sys.prefix!=sys.base_prefix, "Not a virtual environment"'
}
prepare_owned_env "$probe_root/.venv-control"
prepare_owned_env "$probe_root/.venv-mineru"
"$probe_root/.venv-control/bin/python" -m pip install -r requirements-controller.txt
"$probe_root/.venv-mineru/bin/python" -m pip install -r requirements-mineru-basic.txt
"$probe_root/.venv-control/bin/python" -m pip freeze > "setup-logs/controller-$setup_id.freeze.txt"
"$probe_root/.venv-mineru/bin/python" -m pip freeze > "setup-logs/mineru-$setup_id.freeze.txt"
# All MinerU settings and weights stay in this project. No existing model config is edited.
export MINERU_HOME="$probe_root/mineru-state"
export MINERU_CONFIG="$probe_root/mineru-state/download-config.yaml"
export MINERU_MODEL_BASE_DIR="$probe_root/model-cache"
export MINERU_MODEL_SMALL_BACKEND=onnx
export MINERU_MODEL_SOURCE=huggingface
export HF_HUB_DISABLE_TELEMETRY=1
export DO_NOT_TRACK=1
mkdir -p "$MINERU_HOME" "$MINERU_MODEL_BASE_DIR"
"$probe_root/.venv-mineru/bin/python" - "$MINERU_CONFIG" "$MINERU_MODEL_BASE_DIR" <<'PY'
import json,sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({'model': {'source':'huggingface','base_dir':sys.argv[2], 'small_backend':'onnx'}}))
PY
"$probe_root/.venv-mineru/bin/mineru" version --json > "setup-logs/mineru-version-$setup_id.json"
"$probe_root/.venv-mineru/bin/mineru-kit" models download --tier basic --small-backend onnx --source huggingface
"$probe_root/.venv-mineru/bin/mineru-kit" models verify --tier basic --small-backend onnx
echo 'Basic setup finished. Inference remains untested. See START-HERE.md for the fixture and real-source commands.'
