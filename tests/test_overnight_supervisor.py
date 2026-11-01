"""Supervisor boundary and actual disposable-process regressions, no live models."""
import copy
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import supervision_policy as p
import overnight_supervisor as sup
from probe.common import atomic_json, read_json, sha


class Decisions(unittest.TestCase):
    def state(self, status='running'):
        return {'status': status, 'calls': []}

    def test_zero_nonzero_and_loss_before_final_state_are_incidents(self):
        for status, code in [('running', 1), ('running', None), ('stopped_error', 0), ('running', 0)]:
            self.assertEqual(p.classify(self.state(status), worker_alive=False, owned=False, exit_code=code), 'incident')

    def test_live_reasoning_has_no_deadline_and_terminal_waits_for_bundle(self):
        for status in ('running', 'stopped_error', p.TERMINAL):
            self.assertEqual(p.classify(self.state(status), worker_alive=True, owned=True), 'healthy')
        self.assertEqual(p.classify(self.state(p.TERMINAL), worker_alive=False, owned=False, exit_code=0), 'finished')
        self.assertEqual(p.classify(self.state(p.TERMINAL), worker_alive=False, owned=False, exit_code=1), 'incident')

    def test_pause_disable_and_uncertain_ownership(self):
        for status in ('paused', 'draining'):
            self.assertEqual(p.classify(self.state(status), worker_alive=False, owned=False), 'paused')
        s = self.state(); s['calls'] = [{'status': 'in_progress'}]
        self.assertEqual(p.classify(s, worker_alive=False, owned=False), 'blocked_uncertain')
        self.assertEqual(p.classify(s, worker_alive=False, owned=True), 'blocked_ownership')
        self.assertEqual(p.classify(s, worker_alive=True, owned=True, latched=True), 'draining')
        self.assertEqual(p.classify(s, worker_alive=True, owned=True, disabled=True), 'disabled')

    def test_pid_start_boot_and_command_identity(self):
        own = p.process(os.getpid()); self.assertTrue(p.alive(own))
        for key in ('start_ticks', 'boot_id', 'argv_sha256', 'executable', 'cwd'):
            changed = dict(own); changed[key] = 'different'
            self.assertFalse(p.alive(changed))
        child = subprocess.Popen([sys.executable, '-c', 'pass'])
        child.wait()
        self.assertIsNone(p.process(child.pid))

    def test_duplicate_owner_and_restart_allowance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with p.lock(root / 'owner'):
                with self.assertRaises(p.Blocked):
                    with p.lock(root / 'owner'): pass
            with p.lock(root / 'owner'): pass  # released, never deleted
            self.assertTrue((root / 'owner').exists())
            self.assertEqual(p.reserve_attempt(root, 'same'), 1)
            self.assertEqual(p.reserve_attempt(Path(td), 'same'), 2)
            with self.assertRaises(p.Blocked): p.reserve_attempt(root, 'same')
            self.assertEqual(read_json(root / 'allowances.json')['same'], 2)

    def test_fingerprint_survives_call_run_and_line_number_changes(self):
        s = self.state()
        a = p.incident_key(s, "Traceback\nKeyError: 'critic-call-005'", 0)
        b = p.incident_key(s, "Traceback at /tmp/new/run.py:14\nKeyError: 'critic-call-021'", 0)
        self.assertEqual(a, b)


class PatchBoundaries(unittest.TestCase):
    BEFORE = 'def finish_task(a):\n    if a is not None:\n        print(a)\n\ndef protected():\n    return 131072\n'
    AFTER = 'def finish_task(a):\n    if a:\n        print(a)\n\ndef protected():\n    return 131072\n'

    def fixture(self, root):
        code = root / 'code'; file = code / 'scripts/editorial_chapters.py'
        file.parent.mkdir(parents=True); file.write_text(self.BEFORE)
        (code / 'tests').mkdir(); (code / 'tests/test_existing.py').write_text('assert True\n')
        baseline = p.code_inventory(code)
        base = p.snapshot(code, root / 'baseline', baseline)
        dev = p.snapshot(code, root / 'candidate', baseline)
        (dev / 'scripts/editorial_chapters.py').write_text(self.AFTER)
        (dev / 'tests/test_supervisor_regression_case.py').write_text('import unittest\nclass Check(unittest.TestCase):\n def test_case(self): self.assertTrue(True)\n')
        return code, base, dev, baseline

    def test_valid_operational_patch_and_existing_test_protection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); code, base, dev, baseline = self.fixture(root)
            changed, diff = p.proposed_patch(base, dev, baseline)
            self.assertEqual(len(changed), 2); self.assertIn('if a:', diff)
            (dev / 'tests/test_existing.py').write_text('assert False\n')
            with self.assertRaises(p.Blocked): p.proposed_patch(base, dev, baseline)

    def test_policy_limits_new_calls_and_missing_regression_rejected(self):
        cases = [self.AFTER.replace('131072', '1'),
                 self.AFTER.replace('print(a)', '__import__(a)'),
                 self.AFTER.replace('print(a)', 'print("new prompt")')]
        for text in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as td:
                code, base, dev, baseline = self.fixture(Path(td))
                (dev / 'scripts/editorial_chapters.py').write_text(text)
                with self.assertRaises(p.Blocked): p.proposed_patch(base, dev, baseline)
        with tempfile.TemporaryDirectory() as td:
            code, base, dev, baseline = self.fixture(Path(td))
            (dev / 'tests/test_supervisor_regression_case.py').unlink()
            with self.assertRaises(p.Blocked): p.proposed_patch(base, dev, baseline)

    def test_symlinks_hardlinks_and_escape_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); code, base, dev, baseline = self.fixture(root)
            (dev / 'escape').symlink_to(code, target_is_directory=True)
            with self.assertRaises(p.Blocked): p.inventory(dev)
            with self.assertRaises(p.Blocked): p.regular(dev, '../code')
            with self.assertRaises(p.Blocked): p.regular(dev, 'escape/tests/test_existing.py')
            os.link(code / 'tests/test_existing.py', dev / 'hardlink')
            with self.assertRaises(p.Blocked): p.regular(dev, 'hardlink')

    def test_conflicting_user_edit_blocks_application_and_retains_rollback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); code, base, dev, baseline = self.fixture(root)
            incident = root / 'incident'; incident.mkdir()
            changed, _ = p.proposed_patch(base, dev, baseline)
            target = code / 'tests/test_existing.py'; target.write_text('user edit\n')
            with self.assertRaises(p.Blocked): sup.apply_patch(code, incident, dev, baseline, changed)
            self.assertEqual(target.read_text(), 'user edit\n')
            self.assertEqual((code / 'scripts/editorial_chapters.py').read_text(), self.BEFORE)

    def test_live_application_is_disabled_even_for_a_valid_patch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); code, base, dev, baseline = self.fixture(root)
            incident = root / 'incident'; incident.mkdir()
            changed, _ = p.proposed_patch(base, dev, baseline)
            with self.assertRaises(p.Blocked): sup.apply_patch(code, incident, dev, baseline, changed)
            self.assertEqual((code / 'scripts/editorial_chapters.py').read_text(), self.BEFORE)
            self.assertEqual((base / 'scripts/editorial_chapters.py').read_text(), self.BEFORE)
            self.assertEqual((code / 'tests/test_existing.py').read_text(), 'assert True\n')
            self.assertFalse((incident / 'application.json').exists())


class RecoveryFlow(unittest.TestCase):
    def test_all_activation_entries_block_before_mutation_or_import(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); marker = root / 'retained.json'
            atomic_json(marker, {'paused': True, 'calls': 7})
            before = marker.read_bytes()
            for action in ('start', 'resume', 'activate', 'loop', 'worker-entry', 'link', 'qualify'):
                with self.subTest(action=action), patch.object(sys, 'argv', ['supervisor', action]), \
                     patch.object(sup, 'binding', side_effect=AssertionError('no run access')), \
                     patch.object(sup, 'controller', side_effect=AssertionError('no candidate import')):
                    with self.assertRaises(p.Blocked): sup.main()
            self.assertEqual(marker.read_bytes(), before)

    def test_pause_latch_is_immediate_even_while_application_holds_control_lock(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); folder = root / 'supervisor'; folder.mkdir(); run = root / 'run'; run.mkdir()
            atomic_json(folder / 'control.json', {'paused': False, 'disabled': False})
            atomic_json(run / 'state.json', {'status': 'running'})
            with p.lock(folder / 'control.lock'), patch.object(sup, 'binding', return_value=({}, run)), \
                 patch.object(sys, 'argv', ['supervisor', 'pause', '--folder', str(folder)]):
                sup.main()
            self.assertTrue(sup.control(folder)['paused'])
            self.assertTrue((run / 'pause.json').exists())

    def test_disable_never_signals_healthy_work(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); folder = root / 'supervisor'; folder.mkdir(); run = root / 'run'; run.mkdir()
            atomic_json(run / 'state.json', {'status': 'running'})
            identity = p.process(os.getpid())
            with patch.object(sup, 'binding', return_value=({}, run)), \
                 patch.object(sys, 'argv', ['supervisor', 'disable', '--folder', str(folder)]), \
                 patch.object(os, 'kill', side_effect=AssertionError('must not kill work')):
                sup.main()
            self.assertTrue(sup.control(folder)['disabled']); self.assertTrue(p.alive(identity))

    def test_legacy_host_execution_functions_fail_closed(self):
        for function in (sup.command, sup.controller, sup.apply_patch, sup.linked_continuation,
                         sup.launch_worker, sup.worker_entry, sup.loop, sup.repair):
            with self.subTest(function=function.__name__):
                with self.assertRaises(p.Blocked): function()

    def test_confined_dispatch_has_no_host_fallback(self):
        import supervision_isolation as isolation
        with patch.object(isolation, 'run_snapshot', side_effect=p.Blocked('confinement unavailable')) as runner:
            with self.assertRaisesRegex(p.Blocked, 'unavailable'):
                sup.run_check(Path('/snapshot'), Path('/sanitized-evidence'), Path('/private-output'))
        runner.assert_called_once()

    def test_saved_suite_and_attempt_history_are_not_reset_by_disabled_link(self):
        saved = ROOT / 'runs/overnight-suite-20261030T085252Z-fae4ce/state.json'
        if not saved.exists(): return  # No local-book fixture is required by this offline guard test.
        before = saved.read_bytes(); state = read_json(saved)
        with self.assertRaises(p.Blocked): sup.linked_continuation(saved.parent, None, None)
        self.assertEqual(saved.read_bytes(), before)
        self.assertEqual(read_json(saved)['calls'], state['calls'])


if __name__ == '__main__':
    unittest.main()
