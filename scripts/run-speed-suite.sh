#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec /home/mdi/projects/pdf-to-latex/.venv-control/bin/python -B scripts/speed_suite.py "${@:-status}"
