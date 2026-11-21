#!/usr/bin/env bash
set -euo pipefail
exec /home/mdi/projects/pdf-to-latex/.venv-control/bin/python -B /home/mdi/projects/pdf-to-latex/monitoring/observer.py "$@"
