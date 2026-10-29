#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_dir"
exec "$project_dir/.venv-control/bin/python" -B -m scripts.simple_chapter_glm "${1:-status}"
