#!/usr/bin/env bash
set -euo pipefail
cd /home/mdi/projects/pdf-to-latex
exec .venv-control/bin/python -B scripts/glm_image_review.py "$@"
