#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
exec .venv-control/bin/python -B -u scripts/book_completion.py "${@:-run}"
