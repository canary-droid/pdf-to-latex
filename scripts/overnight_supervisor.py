#!/usr/bin/env python3
"""Fail-closed supervisor controls and qualification-only hardening entry point.

Automatic promotion/arming is intentionally unavailable pending review of the
confined replacement. Historical evidence and controls remain on disk unchanged.
No function in this module imports candidate controller modules on the host.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import supervision_policy as policy
from probe.common import atomic_json, read_json, sha

PYTHON = ROOT / '.venv-control/bin/python'
CURRENT = ROOT / 'results/overnight-supervision-current.json'
CHECKS = ROOT / 'scripts/supervision_checks.py'
AUTOMATIC_PROMOTION_ENABLED = False
BLOCK_REASON = ('Automatic promotion and all activation/resume/worker/link paths are disabled. '
                'Run qualification-only; review the confined result before any later start.')


def require_reviewed_execution():
    # No environment variable, command-line switch or candidate patch can enable
    # this route. Its host implementation was removed, not hidden behind a toggle.
    raise policy.Blocked(BLOCK_REASON)


def command(*args, **kwargs):
    raise policy.Blocked('Generic host subprocess execution was removed')


def controller():
    raise policy.Blocked('Host import of candidate-capable controllers was removed')


def apply_patch(*args, **kwargs):
    require_reviewed_execution()


def linked_continuation(*args, **kwargs):
    require_reviewed_execution()


def launch_worker(*args, **kwargs):
    require_reviewed_execution()


def worker_entry(*args, **kwargs):
    require_reviewed_execution()


def loop(*args, **kwargs):
    require_reviewed_execution()


def repair(*args, **kwargs):
    raise policy.Blocked('Unattended repair disabled; use the confined qualification-only path')


def run_check(code, evidence, output, *, stage='fake-worker'):
    from supervision_isolation import run_snapshot
    return run_snapshot(code, evidence, output, stage)


def qualify(folder, run):
    from supervision_qualification import qualify_only
    return qualify_only(folder, run)


def binding(folder):
    cfg = read_json(folder / 'binding.json'); run = Path(cfg['run'])
    if sha(run / 'suite-manifest.json') != cfg['manifest_sha256']:
        raise policy.Blocked('Frozen supervised manifest changed')
    if Path(read_json(ROOT / 'results/overnight-suite-current.json')['run']).resolve() != run:
        raise policy.Blocked('Suite pointer changed outside supervised lineage')
    if read_json(run / 'state.json').get('suite_protocol') != 'overnight-workflow-suite-v1':
        raise policy.Blocked('Unknown workload; production is never supervised here')
    return cfg, run


def control(folder):
    path = folder / 'control.json'
    value = read_json(path) if path.exists() else {'paused': False, 'disabled': False}
    value['paused'] = value['paused'] or (folder / 'pause-latch.json').exists()
    value['disabled'] = value['disabled'] or (folder / 'disabled-latch.json').exists()
    return value


def process_record(path):
    return read_json(path) if path.exists() else None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('qualify-only', 'status', 'pause', 'disable',
        'start', 'resume', 'activate', 'loop', 'worker-entry', 'link', 'qualify'))
    p.add_argument('--run', type=Path); p.add_argument('--folder', type=Path)
    p.add_argument('--incident', type=Path)
    a = p.parse_args()
    if a.action in ('start', 'resume', 'activate', 'loop', 'worker-entry', 'link', 'qualify'):
        require_reviewed_execution()  # Before any controls, imports or run mutation.
    folder = a.folder or (Path(read_json(CURRENT)['folder']) if CURRENT.exists() else None)
    if folder is None:
        raise policy.Blocked('Explicit historical supervisor binding required; no new queue preparation')
    cfg, run = binding(folder)
    if a.run and a.run.resolve() != run:
        raise policy.Blocked('Requested run differs from the retained binding')
    if a.action == 'status':
        state = read_json(run / 'state.json')
        print(json.dumps({'status': 'unarmed_hardening_review_required', 'reason': BLOCK_REASON,
            'automatic_promotion': False, 'run': str(run), 'worker_state': state['status'],
            'recorded_calls': len(state['calls']),
            'pending': sum(t['status'] == 'pending' for t in state['tasks']),
            'control': control(folder), 'historical_evidence': str(folder)}, indent=2))
    elif a.action in ('pause', 'disable'):
        name = 'pause-latch.json' if a.action == 'pause' else 'disabled-latch.json'
        atomic_json(folder / name, {'at': __import__('time').time()})
        if a.action == 'pause' and read_json(run / 'state.json')['status'] != policy.TERMINAL:
            atomic_json(run / 'pause.json', {'supervisor': str(folder)})
        print(a.action + ' latched; no process killed')
    elif a.action == 'qualify-only':
        result = qualify(folder, run)
        print(json.dumps(result, indent=2))
        if result['status'] != 'qualified_fixture_only':
            raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('BLOCKED:', type(exc).__name__ + ':', exc, file=sys.stderr)
        raise SystemExit(1)
