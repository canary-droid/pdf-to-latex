"""Offline launcher checks; converter calls are mocked, no book PDF is read."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from probe.common import atomic_json, read_json, writer_lock

spec = importlib.util.spec_from_file_location('gatheral_launch', Path(__file__).resolve().parents[1] / 'scripts/run-gatheral-extraction.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class GatheralLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def saved(self, name='convert-basic-test', source='gatheral'):
        run = self.root / 'runs' / name
        atomic_json(run / 'state.json', {'settings': {'tier': 'basic', 'sources': {source: {'pdf': 'inputs/gatheral/source.pdf'}}},
                                        'status': 'paused_memory', 'units': {}})
        return run

    def test_exact_source_new_launch_and_exit_status_logged(self):
        with patch.object(launcher.cli, 'cmd_convert', return_value=75) as convert, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.launch(self.root), 75)
        args = convert.call_args.args[0]
        self.assertEqual((args.source, args.tier, args.ocr_isolation, args.resume), ('gatheral', 'basic', 'none', None))
        self.assertEqual(args.converter_python, str(self.root / '.venv-mineru/bin/python'))
        log = next((self.root / 'runs/gatheral-operator').glob('*.log')).read_text()
        self.assertIn('Converter exit status: 75', log)

    def test_resume_uses_saved_path_without_rewriting_evidence(self):
        run = self.saved(); before = (run / 'state.json').read_bytes()
        with patch.object(launcher.cli, 'cmd_convert', return_value=0) as convert, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.launch(self.root), 0)
        self.assertEqual(convert.call_args.args[0].resume, str(run))
        self.assertEqual((run / 'state.json').read_bytes(), before)

    def test_project_writer_lock_blocks_dispatch(self):
        with writer_lock(self.root / 'runs'), patch.object(launcher.cli, 'cmd_convert') as convert:
            with self.assertRaisesRegex(RuntimeError, 'Another mutating'):
                launcher.launch(self.root)
            convert.assert_not_called()

    def test_ambiguous_or_wrong_scope_refused(self):
        self.saved(); self.saved('convert-basic-second')
        with self.assertRaisesRegex(ValueError, 'Multiple'):
            launcher.saved_run(self.root)
        other = Path(self.temp.name) / 'different'
        atomic_json(other / 'runs/convert-basic-test/state.json', {'settings': {'tier': 'basic', 'sources': {'other': {'pdf': 'inputs/gatheral/source.pdf'}}}})
        with self.assertRaisesRegex(ValueError, 'different scope'):
            launcher.saved_run(other)

    def test_status_is_read_only_and_counts_only_owned_pages(self):
        run = self.saved(); s = read_json(run / 'state.json')
        s['units'] = {'gatheral-0001-0008': {'status': 'completed', 'window': {'owned_start': 1, 'owned_end': 8, 'input_start': 1, 'input_end': 9}}}
        atomic_json(run / 'state.json', s)
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(launcher.status(self.root), 0)
        self.assertIn('8/210; windows: 1/27', output.getvalue())
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_interrupt_keeps_130_and_log(self):
        with patch.object(launcher.cli, 'cmd_convert', side_effect=KeyboardInterrupt), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.launch(self.root), 130)
        self.assertIn('Converter exit status: 130', next((self.root / 'runs/gatheral-operator').glob('*.log')).read_text())


if __name__ == '__main__':
    unittest.main()
