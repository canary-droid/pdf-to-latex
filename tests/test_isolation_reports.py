"""Controller orchestration with stub PDFs; no OCR or namespace execution."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import venv

from probe import cli
from probe.common import atomic_json, read_json, sha


class StubPDF:
    def insert_pdf(self, *args, **kwargs):
        pass

    def save(self, path):
        Path(path).write_bytes(b'stub PDF window')

    def close(self):
        pass


class IsolationReportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        source = self.root / 'source.pdf'
        source.write_bytes(b'stub source')
        atomic_json(self.root / 'sources.json', {'fixture-native': {
            'pdf':'source.pdf', 'sha256':sha(source), 'pages':1,
            'original_pages':[1], 'ocr_mode':'auto'}})
        atomic_json(self.root / 'config.example.json', {
            'local_only':True, 'window_pages':8, 'overlap_pages':1,
            'minimum_available_gib_basic':8, 'conversion_timeout_seconds':30})
        self.commands = []
        self.worker_status = 'completed'
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(cli, 'ROOT', self.root))
        self.stack.enter_context(patch.dict(sys.modules, {'fitz':SimpleNamespace(open=lambda *args: StubPDF())}))
        self.runtime = self.stack.enter_context(patch.object(cli, 'runtime_signature', return_value={}))
        self.stack.enter_context(patch.object(cli, 'memory_inventory', return_value={'MemAvailable_bytes':64 * 1024**3}))
        self.stack.enter_context(patch.object(cli, 'execute_window', side_effect=self.worker))
        self.probe = self.stack.enter_context(patch.object(cli, 'isolation_probe', return_value={
            'requested':'namespace', 'status':'passed', 'supported':True,
            'description':cli.isolation_description('namespace'), 'namespace_established':False}))

    def worker(self, command, attempt, minimum, timeout):
        self.commands.append(command)
        output = attempt / 'output'
        output.mkdir()
        atomic_json(output / 'summary.json', {'status':'extracted_unreviewed', 'observed_page_indices':[0]})
        return self.worker_status

    def convert(self, mode='namespace', resume=None, python=None):
        args = ['convert', '--source', 'fixture-native', '--ocr-isolation', mode]
        if resume:
            args += ['--resume', str(resume)]
        if python:
            args += ['--converter-python', str(python)]
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli.main(args)
        run = resume or next((self.root / 'runs').glob('convert-*'))
        return code, run

    def reports(self, run):
        return read_json(run / 'quality-report.json')['ocr_isolation'], (run / 'review.html').read_text()

    def test_successful_namespace_execution_in_both_reports(self):
        code, run = self.convert()
        self.assertEqual(code, 0)
        self.assertEqual(self.commands[0][:4], ['unshare', '--user', '--map-root-user', '--net'])
        report, html = self.reports(run)
        self.assertEqual(report['requested'], 'namespace')
        self.assertEqual(report['namespace_probe']['status'], 'passed')
        self.assertNotIn('namespace_established', report['namespace_probe'])
        attempt = next(iter(report['attempts'].values()))
        self.assertIs(attempt['worker']['namespace_established'], True)
        self.assertIn('Namespace established for this worker', html)
        self.assertIn('This is not evidence of worker isolation', html)
        completion = read_json(run / next(iter(report['attempts'])) / 'completion.json')
        self.assertEqual(attempt['recorded_evidence'], completion['ocr_isolation'])

    def test_worker_failure_after_passing_probe_is_unknown_in_both_reports(self):
        self.worker_status = 'failed'
        code, run = self.convert()
        self.assertEqual(code, 2)
        report, html = self.reports(run)
        self.assertEqual(report['namespace_probe']['status'], 'passed')
        attempt = next(iter(report['attempts'].values()))
        self.assertEqual(attempt['worker']['status'], 'not_confirmed')
        self.assertIsNone(attempt['worker']['namespace_established'])
        self.assertIsNone(attempt['recorded_evidence']['namespace_established'])
        self.assertIn('Unknown whether the worker established a namespace', html)
        self.assertNotIn('Namespace established for this worker', html)

    def test_none_in_both_reports(self):
        self.probe.return_value = {'requested':'none', 'status':'deliberately_not_run',
                                   'supported':None, 'namespace_established':False,
                                   'description':cli.isolation_description('none')}
        code, run = self.convert('none')
        self.assertEqual(code, 0)
        report, html = self.reports(run)
        self.assertEqual(report['requested'], 'none')
        self.assertEqual(report['namespace_probe']['status'], 'deliberately_not_run')
        attempt = next(iter(report['attempts'].values()))
        self.assertIs(attempt['worker']['namespace_established'], False)
        self.assertEqual(attempt['worker']['status'], 'not_requested')
        self.assertIn('local processing; no OS network isolation', html)
        self.assertNotIn('Namespace established for this worker', html)

    def test_retry_reports_both_attempts_and_preserves_previous_evidence(self):
        self.worker_status = 'failed'
        _, run = self.convert()
        first = next((run / 'attempts').glob('*/completion.json'))
        # The first implementation used False for an unconfirmed failed worker.
        legacy = read_json(first)
        legacy['ocr_isolation']['namespace_established'] = False
        atomic_json(first, legacy)
        before = first.read_bytes()
        self.worker_status = 'completed'
        code, _ = self.convert(resume=run)
        self.assertEqual(code, 0)
        self.assertEqual(first.read_bytes(), before)
        report, html = self.reports(run)
        self.assertEqual(len(report['attempts']), 2)
        old = report['attempts'][first.parent.relative_to(run).as_posix()]
        self.assertIsNone(old['worker']['namespace_established'])
        self.assertIs(old['recorded_evidence']['namespace_established'], False)
        self.assertIn('Unknown whether the worker established a namespace', html)
        self.assertIn('Namespace established for this worker', html)

    def test_historical_attempt_without_isolation_is_unknown(self):
        _, run = self.convert()
        first = next((run / 'attempts').glob('*/completion.json'))
        legacy = read_json(first)
        del legacy['ocr_isolation']
        atomic_json(first, legacy)
        before = first.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            cli.report_run(run)
        report, html = self.reports(run)
        self.assertIsNone(next(iter(report['attempts'].values()))['worker']['namespace_established'])
        self.assertEqual(first.read_bytes(), before)
        self.assertIn('Unknown whether the worker established a namespace', html)

    def test_interrupted_previous_attempt_remains_visible_as_unknown(self):
        _, run = self.convert()
        interrupted = run / 'attempts/previous-interrupted'
        interrupted.mkdir()
        atomic_json(interrupted / 'command.json', ['unshare', '--net', 'worker'])
        before = (interrupted / 'command.json').read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            cli.report_run(run)
        report, html = self.reports(run)
        old = report['attempts']['attempts/previous-interrupted']
        self.assertEqual(old['attempt_status'], 'completion_not_recorded')
        self.assertIsNone(old['worker']['namespace_established'])
        self.assertIn('previous-interrupted', html)
        self.assertEqual((interrupted / 'command.json').read_bytes(), before)
        self.assertFalse((interrupted / 'completion.json').exists())

    def test_converter_preserves_and_launches_real_symlinked_venv(self):
        # Use the project only as a temporary parent so ~ expansion can be tested
        # without modifying HOME or creating either operational environment.
        with tempfile.TemporaryDirectory(prefix='test-venv-', dir=Path(__file__).resolve().parents[1]) as directory:
            env = Path(directory) / 'environment'
            venv.EnvBuilder(symlinks=True, with_pip=False).create(env)
            executable = env / 'bin/python'
            self.assertTrue(executable.is_symlink())
            self.assertNotEqual(executable, executable.resolve())
            check = 'import json,sys; print(json.dumps([sys.prefix,sys.base_prefix,sys.executable]))'

            def verify(selected):
                result = subprocess.run([str(selected), '-c', check], capture_output=True,
                                        text=True, timeout=10, check=True)
                prefix, base, actual_executable = json.loads(result.stdout)
                self.assertEqual(Path(prefix), env)
                self.assertNotEqual(prefix, base)
                self.assertEqual(Path(actual_executable), executable)

            for value in (str(executable), os.path.relpath(executable),
                          '~/' + executable.relative_to(Path.home()).as_posix()):
                selected = cli.converter_executable(value)
                self.assertEqual(selected, executable)
                self.assertTrue(selected.is_symlink())
                verify(selected)

            # Exercise cmd_convert's wiring too. Its discovery hook really launches
            # the selected interpreter; the stub OCR worker is never executed.
            def discover(selected, models):
                verify(selected)
                return {}

            self.runtime.side_effect = discover
            _, run = self.convert(python=os.path.relpath(executable))
            selected = self.runtime.call_args.args[0]
            self.assertEqual(selected, executable)
            self.assertEqual(self.commands[0][4], str(executable))
            verify(self.commands[0][4])
