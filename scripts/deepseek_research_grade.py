#!/usr/bin/env python3
"""Arm-masked final answers and disposable numerical grading; no model calls."""
import argparse
import ast
import csv
import hashlib
import json
import os
import random
import re
import resource
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from probe.common import atomic_json, read_json, sha
from probe.batch_review import IntegrityError

QUANT = Path('/home/mdi/venvs/quant')


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (180, 180))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024**2, 16 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def sandbox_command(checks, candidate=None, task=None):
    command = ['bwrap', '--unshare-all', '--die-with-parent', '--new-session', '--clearenv',
               '--ro-bind', '/usr', '/usr', '--symlink', 'usr/lib', '/lib',
               '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/home',
               '--ro-bind', str(QUANT), '/opt/quant', '--ro-bind', str(checks), '/checks.py',
               '--setenv', 'PATH', '/opt/quant/bin:/usr/bin',
               '--setenv', 'OPENBLAS_NUM_THREADS', '1', '--setenv', 'OMP_NUM_THREADS', '1']
    if candidate:
        command += ['--ro-bind', str(candidate), '/submission.py']
    command += ['/opt/quant/bin/python', '-I', '-B', '/checks.py']
    command += ['--candidate', '/submission.py', '--task', task] if candidate else ['--self-test']
    return command


def execute_checks(checks, candidate=None, task=None):
    try:
        result = subprocess.run(sandbox_command(checks, candidate, task), capture_output=True,
                                timeout=180, preexec_fn=limits, env={}, cwd='/tmp')
        return {'returncode': result.returncode, 'stdout': result.stdout.decode(errors='replace'),
                'stderr': result.stderr.decode(errors='replace'),
                'category': 'completed' if result.returncode == 0 else 'execution_or_isolation_error'}
    except subprocess.TimeoutExpired as exc:
        return {'category': 'timeout', 'stdout': (exc.stdout or b'').decode(errors='replace'),
                'stderr': (exc.stderr or b'').decode(errors='replace')}


def extract_code(answer):
    matches = list(re.finditer(r'^```(?:python|py)?[ \t]*\r?\n(.*?)^```[ \t]*(?:\r?\n|$)', answer, re.M | re.S))
    if len(matches) != 1:
        raise ValueError('Expected exactly one Python module fence; no repair/selection')
    return matches[0].group(1)


def prohibited_code(code):
    tree = ast.parse(code)
    banned_modules = {'os', 'subprocess', 'socket', 'requests', 'urllib', 'http', 'pathlib',
                      'ctypes', 'shutil', 'multiprocessing', 'importlib', 'pickle', 'marshal'}
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            findings += [a.name for a in node.names if a.name.split('.')[0] in banned_modules]
        if isinstance(node, ast.ImportFrom) and (node.module or '').split('.')[0] in banned_modules:
            findings.append(node.module)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ('open', 'exec', 'eval', '__import__', 'compile'):
                findings.append(node.func.id)
            if isinstance(node.func, ast.Attribute) and node.func.attr in ('tofile', 'fromfile', 'load', 'save', 'loadtxt', 'savetxt', 'memmap', 'read_text', 'write_text'):
                findings.append(node.func.attr)
    return findings


def mask(run):
    destination = run / 'grading'
    if (destination / 'identity-map.json').exists():
        raise IntegrityError('Mask assignment already frozen')
    state = read_json(run / 'state.json')
    if state['status'] != 'finished':
        raise IntegrityError('Do not label an undispatched partial batch complete')
    plan = read_json(run / 'plan.json')
    random.SystemRandom().shuffle(plan)
    mapping = {}
    for i, task in enumerate(plan, 1):
        identifier = f'M{i:03d}'
        source = run / 'attempts' / task['attempt_id'] / 'answer.txt'
        if not source.exists():
            raise IntegrityError('Missing terminal answer artifact')
        folder = destination / 'masked' / identifier
        folder.mkdir(parents=True)
        (folder / 'answer.txt').write_bytes(source.read_bytes())
        atomic_json(folder / 'task.json', {'base_id': task['base_id'], 'condition_id': task['condition_id'],
                                         'answer_sha256': sha(source)})
        mapping[identifier] = task
    atomic_json(destination / 'identity-map.json', mapping)
    atomic_json(destination / 'mask-seal.json', {str(p.relative_to(destination)): sha(p)
        for p in (destination / 'masked').rglob('*') if p.is_file()})


def code_checks(run):
    checks = run / 'pack/private/numerical_checks.py'
    preflight = execute_checks(checks)
    atomic_json(run / 'grading/sandbox-self-test.json', preflight)
    if preflight.get('returncode') != 0 or not json.loads(preflight['stdout']).get('ok'):
        raise IntegrityError('Disposable sandbox/oracle unavailable; do not execute submissions')
    for folder in sorted((run / 'grading/masked').iterdir()):
        task = read_json(folder / 'task.json')['base_id']
        if task not in ('C01', 'C02') or (folder / 'numerical.json').exists():
            continue
        try:
            code = extract_code((folder / 'answer.txt').read_text())
            (folder / 'submission.py').write_text(code)
            forbidden = prohibited_code(code)
            if forbidden:
                result = {'category': 'contract_violation_not_executed', 'findings': forbidden}
            else:
                result = execute_checks(checks, folder / 'submission.py', task)
                if result.get('returncode') == 0:
                    result['checks'] = json.loads(result['stdout'])
        except SyntaxError as exc:
            result = {'category': 'syntax_error', 'error': str(exc)}
        except ValueError as exc:
            result = {'category': 'format_error', 'error': str(exc)}
        atomic_json(folder / 'numerical.json', result)


def aggregate(run):
    folder = run / 'grading'
    scores = read_json(folder / 'scores.json')
    seal = folder / 'scores.sha256'
    if not seal.exists() or seal.read_text().strip() != sha(folder / 'scores.json'):
        raise IntegrityError('Lock masked criterion scores before joining identity map')
    mapping = read_json(folder / 'identity-map.json')
    if set(scores) != set(mapping):
        raise IntegrityError('All 64 attempts must have grades')
    rows = []
    for identifier, task in mapping.items():
        grade = scores[identifier]
        points = grade['criteria']
        if len(points) != 5 or any(not isinstance(x, (int, float)) or not 0 <= x <= 4 for x in points):
            raise IntegrityError('Five 0-4 criterion scores required')
        outcome = read_json(run / 'attempts' / task['attempt_id'] / 'outcome.json')
        rows.append({**task, 'masked_id': identifier, 'total': sum(points), 'score100': sum(points) * 5,
            'usable_final': outcome['usable_final'], 'delivery_status': outcome['status'],
            **{f'criterion_{i+1}': x for i, x in enumerate(points)},
            'notes': grade['notes'], 'contested': grade.get('contested', False)})
    with (folder / 'per-attempt.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    condition, bases, families = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in rows:
        condition[(row['arm'], row['family'], row['base_id'], row['condition_id'])].append(row['score100'])
    for (arm, family, base, _), values in condition.items():
        bases[(arm, family, base)].append(sum(values) / len(values))
    for (arm, family, base), values in bases.items():
        families[(arm, family)].append(sum(values) / len(values))
    result = {'family_scores': {arm: {family: sum(values) / len(values)
              for (a, family), values in families.items() if a == arm}
              for arm in ('local_exl3', 'hosted_fp8')}, 'all_attempts': len(rows)}
    result['overall'] = {arm: sum(values.values()) / len(values) for arm, values in result['family_scores'].items()}
    result['coverage'] = {arm: sum(x['usable_final'] for x in rows if x['arm'] == arm) / 32
                          for arm in ('local_exl3', 'hosted_fp8')}
    atomic_json(folder / 'summary.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['mask', 'code-checks', 'aggregate', 'sandbox-check'])
    p.add_argument('--run', required=True, type=Path)
    args = p.parse_args()
    run = args.run.resolve()
    if args.command == 'sandbox-check':
        result = execute_checks(run / 'pack/private/numerical_checks.py')
        atomic_json(run / 'sandbox-self-test.json', result)
        print(result['category'], result.get('returncode'))
    else:
        {'mask': mask, 'code-checks': code_checks, 'aggregate': aggregate}[args.command](run)
