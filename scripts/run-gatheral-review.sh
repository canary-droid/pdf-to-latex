#!/usr/bin/env bash
# Operator only, after completed extraction and reviewed copy-back. No service management.
set -euo pipefail
book_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$book_root"
book_python="$book_root/.venv-control/bin/python"
book_action="${1:-status}"
book_image='sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45'
if [[ "$book_action" == prepare ]]; then
  book_conversion="$($book_python -B - <<'PY'
import runpy
from pathlib import Path
module=runpy.run_path('scripts/run-gatheral-extraction.py')
run,state=module['saved_run'](Path.cwd())
assert run and state['status']=='conversion_completed_unreviewed', 'Wait for all 210 pages; no partial conversion input'
from probe.saved_pages import converter_idle
converter_idle(Path.cwd())
print(run)
PY
)"
  test -n "$book_conversion"
  exec "$book_python" -B -m probe.book_review prepare --conversion "$book_conversion" --source gatheral \
    --gate-first 32 --gate-count 2 --recovery-calls 80 --hours 6 --compiler-image "$book_image"
fi
book_run="$($book_python -B - <<'PY'
from pathlib import Path
import json
root=Path.cwd();r=Path(json.loads((root/'results/book-review-current.json').read_text())['run']).resolve()
assert r.parent==root/'runs' and (r/'binding.json').is_file(), 'Missing actual book review preparation'
print(r)
PY
)"
test -n "$book_run"
case "$book_action" in
  gate|continue|resume-gate|resume-continue)
    book_ready="$($book_python -B - "$book_run" <<'PY'
import json,sys
from pathlib import Path
r=Path(sys.argv[1]);p=Path(json.loads((r/'latest-readiness.json').read_text())['path'])
s=json.loads((p/'readiness.json').read_text())
assert s['text']=='passed' and s['vision']=='qualified', 'Fresh visual readiness must pass'
assert s['config']['model']=='flash-next-tensorfold', 'Wrong exact model alias'
print(p)
PY
)"
    test -n "$book_ready" && test -s "$book_ready/readiness.json"
    book_resume=();book_stage="$book_action"
    if [[ "$book_action" == resume-* ]]; then book_resume=(--resume);book_stage="${book_action#resume-}"; fi
    if [[ "$book_stage" == continue ]]; then book_resume=(--resume); fi
    exec "$book_python" -B -m probe.book_review launch --run "$book_run" --readiness "$book_ready" \
      --stage "$book_stage" "${book_resume[@]}" --compiler-image "$book_image" ;;
  ready|status|pause|report|bundle|dispositions)
    exec "$book_python" -B -m probe.book_review "$book_action" --run "$book_run" ;;
  *) printf '%s\n' 'Use prepare, ready, gate, continue, resume-gate, resume-continue, status, pause, report, bundle, dispositions.' >&2; exit 2 ;;
esac
