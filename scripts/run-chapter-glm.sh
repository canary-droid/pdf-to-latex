#!/usr/bin/env bash
# Exact local chapter route; never starts/stops model services or dispatches cloud work.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_dir"
exec "$project_dir/.venv-control/bin/python" -B -m probe.chapter_glm "${1:-status}"
