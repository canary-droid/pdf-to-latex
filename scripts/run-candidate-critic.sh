#!/usr/bin/env bash
# Operator entry point. No service operations, installation, key creation or fallback.
set -euo pipefail
critic_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$critic_root"
critic_python="$critic_root/.venv-control/bin/python"
critic_action="${1:-status}"
critic_run="$($critic_python - "$critic_root" <<'PY'
import json, sys
from pathlib import Path
root=Path(sys.argv[1])
p=root/'results/candidate-critic-current.json'
r=Path(json.loads(p.read_text())['run']).resolve()
assert r.parent==root/'runs' and (r/'binding.json').is_file(), 'Missing actual local preparation'
b=json.loads((r/'binding.json').read_text())
assert b['config']['profile'] in ('glm','deepseek'), 'Pointer must name a local candidate critic'
print(r)
PY
)"
test -n "$critic_run"
case "$critic_action" in
  select)
    # Frozen completed calibration billing parent; never read its secret.
    exec "$critic_python" -m probe.critic_route select --run "$critic_run" \
      --billing-parent "$critic_root/runs/critic-mimo-trial-20261025T101919Z-ebb7eb" ;;
  prepare-selected)
    exec "$critic_python" -m probe.critic_route prepare-selected --run "$critic_run" ;;
  mimo-*)
    critic_run="$($critic_python - "$critic_run" <<'PY'
import json, sys
from pathlib import Path
local=Path(sys.argv[1]); r=Path(json.loads((local/'escalation-run.json').read_text())['run']).resolve()
assert r.parent==local.parent and (r/'binding.json').is_file(), 'No prepared paid selection'
b=json.loads((r/'binding.json').read_text())
assert b['config']['profile']=='mimo', 'Wrong selected profile'
preview=json.loads((Path(b['preview'])/'preview.json').read_text())
assert Path(preview['critic_route']['local_run']).resolve()==local, 'Wrong local parent'
print(r)
PY
)"
    test -n "$critic_run"
    critic_action="${critic_action#mimo-}" ;;
esac
case "$critic_action" in
  run|resume|ready)
    critic_profile="$($critic_python -c 'import json,sys;print(json.load(open(sys.argv[1]))["config"]["profile"])' "$critic_run/binding.json")"
    if [[ "$critic_profile" == mimo ]]; then
      # Cost preview first; runtime client checks authenticated identity/rates/remaining dollars.
      "$critic_python" -m probe.critic_route cost --run "$critic_run"
      exec "$critic_python" -m probe.critic_route "$critic_action" --run "$critic_run" --allow-paid
    fi
    # Exact discovery is repeated by fresh readiness and by the serial executor.
    "$critic_python" - "$critic_run" <<'PY'
import json, sys, urllib.request
from pathlib import Path
c=json.loads((Path(sys.argv[1])/'binding.json').read_text())['config']
assert c['profile'] in ('glm','deepseek')
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(c['endpoint'].rstrip('/')+'/models', timeout=10) as response:
    data=json.load(response)
assert c['model'] in [x.get('id') for x in data.get('data',[])], 'Intended exact local alias absent; no fallback'
print('Intended local alias:',c['model'],flush=True)
PY
    exec "$critic_python" -m probe.critic_route "$critic_action" --run "$critic_run" ;;
  status|pause|report|bundle|cost)
    exec "$critic_python" -m probe.critic_route "$critic_action" --run "$critic_run" ;;
  *) printf '%s\n' 'Use run, resume, ready, status, pause, report, bundle, select, cost, prepare-selected, or mimo-{run,resume,ready,status,pause,report,bundle,cost}.' >&2; exit 2 ;;
esac
