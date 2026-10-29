#!/usr/bin/env bash
# Operator-only live launcher. Does not manage any model service.
set -uo pipefail
cd /home/mdi/projects/pdf-to-latex || exit 1
run=runs/deepseek-arm-a-trial-20261022T180153Z-0ee3cf
preview=runs/deepseek-arm-a-input-20261022T180153Z-4d91d8
args=()
while (($#)); do
  case "$1" in
    --resume) args+=(--resume); shift ;;
    --wait-ready|--first-launch)
      if (($# < 2)); then printf 'Missing value for %s\n' "$1" >&2; exit 2; fi
      args+=("$1" "$2"); shift 2 ;;
    *) printf 'Unknown option: %s\nAllowed: --resume --wait-ready SECONDS --first-launch DIRECTORY\n' "$1" >&2; exit 2 ;;
  esac
done
if [[ ! -f "$run/binding.json" || ! -f "$preview/manifest.json" ]]; then
  printf 'Prepared DeepSeek evidence is missing; refusing launch.\n' >&2
  exit 2
fi
printf 'UTC: %s\nPreview: %s\nRun: %s\nLog: %s/operator.log\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$preview" "$run" "$run" | tee -a "$run/operator.log"
.venv-control/bin/python -u -m probe.deepseek_trial launch --run "$run" "${args[@]}" \
  2>&1 | tee -a "$run/operator.log"
codes=("${PIPESTATUS[@]}")
printf 'Report: /home/mdi/projects/pdf-to-latex/%s/report.html\n' "$run"
if [[ -f "$run/latest-bundle.json" ]]; then cat "$run/latest-bundle.json"; fi
if ((codes[0] != 0)); then exit "${codes[0]}"; fi
exit "${codes[1]}"
