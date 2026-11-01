"""Trusted in-sandbox qualification harness. Never a host candidate importer."""
import argparse
import errno
import json
import os
from pathlib import Path
import resource
import socket
import sys
import traceback
import unittest
import tempfile
from unittest.mock import patch


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def denied(operation):
    try:
        operation()
    except OSError as exc:
        return exc.errno in (errno.EACCES, errno.EPERM, errno.EROFS, errno.ENOENT)
    return False


def boundary(evidence, output, temporary, code):
    record = json.loads((evidence / 'boundary.json').read_text())
    checks = {}
    for label, path in record['denied_paths'].items():
        checks[label + '_read'] = denied(lambda p=path: Path(p).read_bytes())
        checks[label + '_write'] = denied(lambda p=path: Path(p).write_text('harmless-disposable-probe'))
    for family, address, name in ((socket.AF_INET, tuple(record['tcp']), 'tcp'),
                                   (socket.AF_UNIX, record['unix'], 'unix')):
        def connect():
            with socket.socket(family, socket.SOCK_STREAM) as s:
                s.settimeout(2); s.connect(address)
        checks[name + '_host_socket'] = denied(connect)
    checks['environment'] = all(k not in os.environ for k in (
        'SSH_AUTH_SOCK', 'OPENAI_API_KEY', 'AWS_SECRET_ACCESS_KEY', 'REPAIR_SECRET_PROBE',
        'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'PYTHONPATH'))
    checks['private_home'] = os.environ.get('HOME') == str(temporary)
    checks['private_tmp'] = os.environ.get('TMPDIR') == str(temporary)
    checks['parent_write'] = denied(lambda: (output.parent / 'escaped-output.txt').write_text('probe'))
    (output / 'permitted.txt').write_text('permitted disposable output')
    (temporary / 'permitted.txt').write_text('private temporary output')
    checks['output_write'] = (output / 'permitted.txt').read_text() == 'permitted disposable output'
    checks['temp_write'] = (temporary / 'permitted.txt').is_file()
    checks['code_read'] = (code / 'scripts/editorial_chapters.py').is_file()
    def writable(path):
        try:
            fd = os.open(path, os.O_WRONLY); os.close(fd); return True
        except OSError: return False
    checks['approved_source_mode'] = writable(code / 'scripts/editorial_chapters.py') == record.get('source_writable', False)
    checks['protected_policy_readonly'] = not writable(code / 'scripts/supervision_policy.py')
    checks['existing_tests_readonly'] = not writable(code / 'tests/test_overnight_repair.py')
    checks['scientific_settings_readonly'] = not writable(code / 'probe/chapter_protocol.py')
    checks['no_new_privileges'] = 'NoNewPrivs:\t1' in Path('/proc/self/status').read_text()
    checks['private_pid_namespace'] = os.readlink('/proc/self/ns/pid') != record['host_pid_namespace']
    result = {'status': 'passed' if all(checks.values()) else 'boundary_failed', 'checks': checks,
              'rlimit_nofile': list(resource.getrlimit(resource.RLIMIT_NOFILE)),
              'rlimit_fsize': list(resource.getrlimit(resource.RLIMIT_FSIZE)),
              'pid': os.getpid()}
    write(output / 'boundary-result.json', result)
    if not all(checks.values()):
        raise RuntimeError('Confinement probe failed: ' + ', '.join(k for k, v in checks.items() if not v))
    return result


def load_candidate(code):
    sys.path.insert(0, str(code)); sys.path.insert(0, str(code / 'scripts'))
    sys.path.insert(0, str(code / 'tests'))
    import speed_suite as ctrl
    from test_overnight_repair import setup_finalization, FIXTURE
    return ctrl, setup_finalization, FIXTURE


def fake_worker(code, evidence, output):
    ctrl, setup, fixture = load_candidate(code)
    path = evidence / 'queue.json'
    state = json.loads(path.read_text()) if path.exists() else {
        'status': 'prepared_offline', 'calls': [], 'tasks': [], 'generated': []}
    before = list(state['generated'])
    # A terminal launch returns without readiness, transport or finalization.
    if state['status'] == 'suite_finished_for_inspection':
        write(output / 'queue.json', state); return
    state['status'] = 'running'
    try:
        for number in (1, 2, 3):
            key = 'fake-' + str(number)
            if key in state['tasks']: continue
            if key not in state['generated']:
                state['generated'].append(key)
                state['calls'].append({'id': key, 'status': 'completed_response'})
                write(output / 'queue.json', state)
            if number == 2:
                run = Path(tempfile.mkdtemp(prefix='unit-', dir=output))
                answer = (fixture / 'answer.txt').read_text()
                s, t, c = setup(run, answer)
                def compile_selected(r, s, k, label):
                    text = ctrl.book.bound_output(r, s, k, label)
                    if not ctrl.book.chapter_accuracy.complete_document(text):
                        raise RuntimeError('Incomplete compiled document')
                with patch.object(ctrl.book, 'compile_version', side_effect=compile_selected):
                    ctrl.book.finish_task(run, s, t, answer, c)
                if t['status'] != 'critic_unchanged':
                    raise RuntimeError('Findings were labelled as an applied replacement')
            state['tasks'].append(key)
            write(output / 'queue.json', state)
        state['status'] = 'suite_finished_for_inspection'
    except Exception as exc:
        state.update(status='stopped_error', diagnostic=type(exc).__name__ + ': ' + str(exc))
        (output / 'traceback.txt').write_text(traceback.format_exc())
    state['generation_before'] = before
    write(output / 'queue.json', state)


def redirect(code, output):
    ctrl, setup, fixture = load_candidate(code)
    answer = (fixture / 'answer.txt').read_text()
    state, task, call = setup(output, answer)
    try:
        with patch.object(ctrl.book, 'compile_version'):
            ctrl.book.finish_task(output, state, task, answer, call)
    except OSError as exc:
        if exc.errno not in (errno.EACCES, errno.EPERM, errno.EROFS):
            raise
        write(output / 'redirect-result.json', {'status': 'denied', 'errno': exc.errno})
        return
    raise RuntimeError('Path redirection was not denied by the execution boundary')


def tests(code, output, regression):
    load_candidate(code)
    if regression:
        suite = unittest.defaultTestLoader.discover(str(code / 'tests'), pattern='test_supervisor_regression_*.py')
    else:
        # Fixed existing failure-path checks, without test-source rewriting.
        suite = unittest.defaultTestLoader.loadTestsFromNames([
            'test_overnight_repair.FinalizationTests.test_real_saved_findings_fences_partial_complete_and_ambiguous',
            'test_overnight_repair.FinalizationTests.test_partial_finalization_recovery_is_idempotent_and_integrity_checked',
            'test_overnight_repair.CachedRendererTests',
            'test_overnight_repair.RecoveredControllerTests'])
    if not suite.countTestCases(): raise RuntimeError('No regression tests discovered')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    details = '\n'.join(text for _, text in [*result.errors, *result.failures])
    environment_denied = any(x in details for x in ('PermissionError', 'Operation not permitted',
                                                    'Read-only file system', 'ModuleNotFoundError'))
    write(output / 'test-result.json', {
        'status': 'passed' if result.wasSuccessful() and not result.skipped else
                  'environment_denied' if environment_denied else 'failed',
        'tests': result.testsRun, 'errors': len(result.errors), 'failures': len(result.failures),
        'skipped': len(result.skipped)})
    return 0 if result.wasSuccessful() and not result.skipped else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('boundary', 'redirect', 'fake-worker', 'regressions', 'existing-tests', 'replay'))
    for name in ('code', 'evidence', 'output', 'temporary'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    # This runs BEFORE importing any candidate. The synthetic canaries are
    # controller-created, not actual credentials or live evidence.
    boundary(a.evidence, a.output, a.temporary, a.code)
    if a.action == 'boundary': return
    if a.action == 'redirect': redirect(a.code, a.output)
    elif a.action == 'fake-worker': fake_worker(a.code, a.evidence, a.output)
    elif a.action in ('regressions', 'existing-tests'):
        raise SystemExit(tests(a.code, a.output, a.action == 'regressions'))
    else:
        raise RuntimeError('Live saved-run replay is disabled pending a reviewed data-only adapter')


if __name__ == '__main__':
    main()
