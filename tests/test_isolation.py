"""Isolation policy checks requiring no PDF dependencies or sockets."""
import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from probe import cli
from probe.common import atomic_json, read_json, sha


class IsolationTests(unittest.TestCase):
    def test_parser_defaults_and_explicit_modes(self):
        for command in ('preflight', 'convert'):
            self.assertEqual(cli.parser().parse_args([command]).ocr_isolation, 'namespace')
            for mode in ('namespace', 'none'):
                self.assertEqual(cli.parser().parse_args([command, '--ocr-isolation', mode]).ocr_isolation, mode)

    def test_none_never_probes(self):
        with patch.object(cli.subprocess, 'run', side_effect=FileNotFoundError) as run:
            evidence = cli.isolation_probe('none')
        run.assert_not_called()
        self.assertEqual(evidence['status'], 'deliberately_not_run')
        self.assertIsNone(evidence['supported'])
        self.assertFalse(evidence['namespace_established'])

    def test_namespace_failure_and_success_are_availability_only(self):
        for result in (FileNotFoundError('missing'), subprocess.TimeoutExpired('unshare', 10),
                       subprocess.CompletedProcess([], 1, stderr='denied'),
                       subprocess.CompletedProcess([], 0, stderr='')):
            with self.subTest(result=result):
                with patch.object(cli.sys, 'platform', 'linux'), patch.object(cli.subprocess, 'run') as run:
                    if isinstance(result, Exception):
                        run.side_effect = result
                    else:
                        run.return_value = result
                    evidence = cli.isolation_probe('namespace')
                self.assertFalse(evidence['namespace_established'])
                self.assertEqual(evidence['status'], 'passed' if getattr(result, 'returncode', 1) == 0 else 'failed')

    def test_conversion_modes_with_stub_pdf_and_worker(self):
        # This checks orchestration without claiming PDF extraction validation.
        class PDF:
            def insert_pdf(self, *args, **kwargs):
                pass

            def save(self, path):
                Path(path).write_bytes(b'stub PDF window')

            def close(self):
                pass

        for mode in ('none', 'namespace'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source = root / 'source.pdf'
                source.write_bytes(b'stub source')
                atomic_json(root / 'sources.json', {'fixture-native': {
                    'pdf': 'source.pdf', 'sha256': sha(source), 'pages': 1,
                    'original_pages': [1], 'ocr_mode': 'auto'}})
                atomic_json(root / 'config.example.json', {
                    'local_only': True, 'window_pages': 8, 'overlap_pages': 1,
                    'minimum_available_gib_basic': 8, 'conversion_timeout_seconds': 30})
                commands = []

                def worker(command, attempt, minimum, timeout):
                    commands.append(command)
                    self.assertEqual(minimum, 8 * 1024**3)
                    output = attempt / 'output'
                    output.mkdir()
                    atomic_json(output / 'summary.json', {
                        'status': 'extracted_unreviewed', 'observed_page_indices': [0]})
                    return 'completed'

                with patch.object(cli, 'ROOT', root), \
                     patch.dict(sys.modules, {'fitz': SimpleNamespace(open=lambda *args: PDF())}), \
                     patch.object(cli, 'runtime_signature', return_value={}), \
                     patch.object(cli, 'memory_inventory', return_value={'MemAvailable_bytes': 64 * 1024**3}), \
                     patch.object(cli, 'execute_window', side_effect=worker), \
                     patch.object(cli.subprocess, 'run', side_effect=FileNotFoundError('unshare missing')) as probe, \
                     contextlib.redirect_stdout(io.StringIO()):
                    args = ['convert', '--source', 'fixture-native', '--ocr-isolation', mode]
                    self.assertEqual(cli.main(args), 0 if mode == 'none' else 3)
                    run = next((root / 'runs').glob('convert-*'))
                    state = read_json(run / 'state.json')
                    self.assertEqual(state['settings']['ocr_isolation'], mode)
                    self.assertFalse(state['ocr_isolation']['namespace_established'])
                    if mode == 'namespace':
                        self.assertEqual(commands, [])
                        probe.assert_called_once()
                        continue
                    probe.assert_not_called()
                    self.assertEqual(len(commands), 1)
                    self.assertFalse(any(x in ('unshare', 'bwrap') for x in commands[0]))
                    attempt = run / next(iter(state['units'].values()))['attempt']
                    completion = read_json(attempt / 'completion.json')
                    self.assertEqual(completion['ocr_isolation']['worker_namespace_status'], 'not_requested')
                    self.assertIn('local processing; no OS network isolation', (run / 'review.html').read_text())
                    before = (attempt / 'completion.json').read_bytes()
                    self.assertEqual(cli.main(args + ['--resume', str(run)]), 0)
                    self.assertEqual(len(commands), 1)
                    self.assertEqual((attempt / 'completion.json').read_bytes(), before)
                    snapshot = (run / 'state.json').read_bytes()
                    args[-1] = 'namespace'
                    self.assertEqual(cli.main(args + ['--resume', str(run)]), 2)
                    self.assertEqual((run / 'state.json').read_bytes(), snapshot)
                    probe.assert_not_called()

    def test_preflight_none_records_deliberate_skip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'fixtures/vision').mkdir(parents=True)
            atomic_json(root / 'fixtures/vision/manifest.json', [])
            atomic_json(root / 'config.example.json', {'local_only': True})
            result = {'text': {'status': 'passed'}, 'strict_json': {'status': 'passed'}, 'vision': {'status': 'unqualified'}}
            with patch.object(cli, 'ROOT', root), patch.object(cli, 'inventory', return_value={}), \
                 patch.object(cli, 'selected_sources'), patch.object(cli, 'make_client'), \
                 patch.object(cli, 'probe_model', return_value=result), \
                 patch.object(cli.subprocess, 'run', side_effect=AssertionError('No namespace commands')), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(['preflight', '--ocr-isolation', 'none']), 0)
            run = next((root / 'runs').glob('preflight-*'))
            evidence = read_json(run / 'network-isolation.json')
            self.assertEqual(evidence['status'], 'deliberately_not_run')
            self.assertEqual(read_json(run / 'summary.json')['ocr_isolation'], evidence)
