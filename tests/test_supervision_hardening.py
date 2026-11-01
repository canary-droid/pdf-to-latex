"""Offline boundary construction checks. These do not certify OS confinement."""
import json
import os
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import supervision_isolation as iso
import supervision_policy as policy
import supervision_qualification as qual
from probe.common import atomic_json, read_json


class ScopeRegression(unittest.TestCase):
    def test_actual_unchanged_reporting_file_with_existing_import_passes(self):
        text = (ROOT / 'scripts/speed_suite.py').read_text()
        self.assertIn('import statistics', text)
        policy.ast_scope(text, text, policy.SCOPE['scripts/speed_suite.py'])
        changed = text.replace('def report(run,state):\n', 'def report(run,state):\n    pass\n')
        self.assertNotEqual(changed, text)
        policy.ast_scope(text, changed, policy.SCOPE['scripts/speed_suite.py'])

    def test_new_import_still_rejected(self):
        text = (ROOT / 'scripts/speed_suite.py').read_text()
        changed = text.replace('def report(run,state):\n', 'def report(run,state):\n    import socket\n')
        with self.assertRaises(policy.Blocked): policy.ast_scope(text, changed, policy.SCOPE['scripts/speed_suite.py'])

    def test_path_redirection_scope_acceptance_is_not_called_security(self):
        text = (ROOT / 'scripts/editorial_chapters.py').read_text()
        changed = text.replace('def finish_task(run,state,task,answer,call):\n',
                               'def finish_task(run,state,task,answer,call):\n    run = run.parent\n')
        policy.ast_scope(text, changed, policy.SCOPE['scripts/editorial_chapters.py'])
        # It is never executed on the host by this test. Qualification invokes
        # exactly this fixture through both confined execution paths.

    def test_oversize_and_duplicate_scoped_functions_rejected(self):
        text = 'def finish_task():\n    pass\n'
        with self.assertRaises(policy.Blocked): policy.ast_scope(text, text + text, {'finish_task'})
        with self.assertRaises(policy.Blocked): policy.ast_scope(text, ' ' * (policy.MAX_SOURCE_BYTES + 1), {'finish_task'})


class ClosedConfiguration(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        setup = Path(temporary.name) / 'setup.json'
        atomic_json(setup, {'executable': '/verified/release/bin/codex'})
        selected = patch.object(iso, 'SETUP', setup); selected.start(); self.addCleanup(selected.stop)

    def fixture(self, root):
        for name in ('code', 'evidence', 'output', 'tmp'): (root / name).mkdir()
        code = root / 'code'
        (code / 'scripts').mkdir(); (code / 'tests').mkdir()
        for rel in ('scripts/editorial_chapters.py', 'scripts/speed_suite.py',
                    'scripts/supervision_policy.py', 'tests/test_existing.py', 'AGENTS.md'):
            (code / rel).write_text('protected fixture\n')
        return [root / name for name in ('code', 'evidence', 'output', 'tmp')]

    def test_permissions_are_explicit_and_no_broad_temp_or_home_grant(self):
        with tempfile.TemporaryDirectory() as td:
            roots = self.fixture(Path(td)); options = iso.configuration(*roots, editable=True)
            fs = options['permissions']['incident-only']['filesystem']
            self.assertEqual(fs[':root'], 'deny'); self.assertNotIn(':minimal', fs)
            self.assertEqual(fs[str(roots[0])], 'read')
            self.assertEqual(fs[str(roots[0] / 'scripts/editorial_chapters.py')], 'write')
            self.assertEqual(fs[str(roots[0] / 'scripts/supervision_policy.py')], 'read')
            self.assertEqual(fs[str(roots[0] / 'tests/test_existing.py')], 'read')
            self.assertNotIn(str(roots[0] / 'tests'), {p for p, access in fs.items() if access == 'write'})
            self.assertNotIn('/tmp', {p for p, access in fs.items() if access == 'write'})
            self.assertEqual(fs[str(Path.home() / '.codex')], 'deny')
            self.assertFalse(options['permissions']['incident-only']['network']['enabled'])
            self.assertEqual(options['approval_policy'], 'never')
            self.assertEqual(options['shell_environment_policy']['inherit'], 'none')
            self.assertFalse(options['features']['apps']); self.assertFalse(options['features']['plugins'])
            for key, value in options.items(): self.assertEqual(tomllib.loads(key + '=' + iso.toml(value))[key], value)

    def test_readonly_validation_and_explicit_clean_environment(self):
        with tempfile.TemporaryDirectory() as td:
            roots = self.fixture(Path(td)); options = iso.configuration(*roots)
            self.assertEqual(options['permissions']['incident-only']['filesystem'][str(roots[0])], 'read')
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'MOCK-NOT-A-KEY', 'SSH_AUTH_SOCK': '/mock.sock',
                                         'HTTPS_PROXY': 'mock', 'PYTHONPATH': '/untrusted'}):
                env = iso.clean_environment(client=True, temporary=roots[3])
            self.assertTrue(all(k not in env for k in ('OPENAI_API_KEY', 'SSH_AUTH_SOCK', 'HTTPS_PROXY', 'PYTHONPATH')))
            with patch.object(iso, 'executable', return_value=Path('/verified/codex')):
                argv = list(map(str, iso.sandbox_arguments(options, roots[0], 'boundary', roots[1], roots[2], roots[3])))
            self.assertIn('sandbox', argv); self.assertIn('/usr/bin/env', argv); self.assertIn('-i', argv)
            self.assertNotIn('--sandbox', argv); self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', argv)

    def test_all_sandbox_stages_explicitly_select_generated_permission_profile(self):
        with tempfile.TemporaryDirectory() as td:
            code, evidence, output, temporary = self.fixture(Path(td))
            for editable in (False, True):
                options = iso.configuration(code, evidence, output, temporary, editable=editable)
                original = json.loads(json.dumps(options))
                for stage in sorted(iso.STAGES):
                    with self.subTest(editable=editable, stage=stage), \
                         patch.object(iso, 'executable', return_value=Path('/verified/codex')):
                        argv = iso.sandbox_arguments(options, code, stage, evidence, output, temporary)
                        start = argv.index('sandbox')
                        self.assertEqual(argv[start:start + 6], [
                            'sandbox', '--permission-profile', options['default_permissions'], '--cd', code, '--'])
                        self.assertEqual(argv.count('--permission-profile'), 1)
                        self.assertNotIn('--strict-config', argv)
                        selected = argv[argv.index('--permission-profile') + 1]
                        self.assertEqual(selected, 'incident-only')
                        self.assertIn(selected, options['permissions'])
                        # The model/config profile remains a separate selector.
                        self.assertEqual(argv[argv.index('--profile') + 1], iso.PROFILE)
                        self.assertEqual(options, original)

    def test_overlapping_roots_and_unknown_mode_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            roots = self.fixture(Path(td))
            with self.assertRaises(policy.Blocked): iso.configuration(roots[0], roots[0], roots[2], roots[3])
            roots[1].rmdir(); roots[1].symlink_to(roots[0], target_is_directory=True)
            with self.assertRaises(policy.Blocked): iso.configuration(*roots)
        with self.assertRaises(policy.Blocked): iso.sandbox_arguments({}, Path('/x'), 'shell', None, None, None)

    def test_freeze_binds_checked_bytes_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); dev = root / 'dev'; dev.mkdir(); (dev / 'unit.py').write_text('original\n')
            expected = iso.freeze(dev, root / 'frozen')
            (dev / 'unit.py').write_text('background edit\n')
            self.assertEqual(policy.inventory(root / 'frozen'), expected)
            with self.assertRaises(policy.Blocked): iso.freeze(dev, root / 'conflict', expected)
            (dev / 'escape').symlink_to(root)
            with self.assertRaises(policy.Blocked): iso.freeze(dev, root / 'symlink')

    def test_deliberate_subset_never_reads_or_copies_unselected_tree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / 'source'; source.mkdir()
            (source / 'selected.py').write_text('selected')
            (source / 'unselected-link').symlink_to('/not-readable')
            expected = {'selected.py': __import__('hashlib').sha256(b'selected').hexdigest()}
            iso.freeze(source, root / 'frozen', expected, subset=True)
            self.assertEqual(policy.inventory(root / 'frozen'), expected)

    def test_output_parser_rejects_symlink_oversize_and_nonobject(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'result.json').write_text('[]')
            with self.assertRaises(policy.Blocked): iso.read_artifact(root, 'result.json')
            (root / 'result.json').write_text('{}')
            with self.assertRaises(policy.Blocked): iso.read_artifact(root, 'result.json', limit=1)
            (root / 'link.json').symlink_to(root / 'result.json')
            with self.assertRaises(policy.Blocked): iso.read_artifact(root, 'link.json')

    def test_live_output_accounting_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); output = root / 'output'; output.mkdir(); outside = root / 'outside'; outside.mkdir()
            with (outside / 'large').open('wb') as f: f.truncate(iso.TREE_LIMIT + 1)
            (output / 'alias').symlink_to(outside, target_is_directory=True)
            self.assertEqual(iso.tree_size(output), 0)
            with (output / 'large').open('wb') as f: f.truncate(iso.TREE_LIMIT + 1)
            with self.assertRaises(policy.Blocked): iso.tree_size(output)

    def test_service_refusal_has_no_unsandboxed_fallback_and_records_limits(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(iso.subprocess, 'Popen', side_effect=PermissionError('mock service denial')) as launch:
                with self.assertRaises(PermissionError):
                    iso.limited_service(['/verified/codex', 'sandbox'], root / 'check.log', environment=iso.clean_environment())
            self.assertEqual(launch.call_count, 1)
            argv = launch.call_args.args[0]
            self.assertIn('--property=KillMode=control-group', argv)
            self.assertIn('--property=MemoryMax=' + str(iso.MEMORY), argv)
            self.assertIn('--property=TasksMax=' + str(iso.TASKS), argv)
            self.assertIn('--no-ask-password', argv); self.assertIn('-i', argv)
            self.assertIn(str(iso.SERVICE_GUARD), argv)

    def test_service_manager_cannot_bypass_interactive_outer_sandbox(self):
        with patch.dict(os.environ, {'CODEX_SANDBOX_NETWORK_DISABLED': '1'}), \
             patch.object(iso.subprocess, 'Popen', side_effect=AssertionError('must not contact host manager')):
            with self.assertRaisesRegex(policy.Blocked, 'Normal terminal required'):
                iso.limited_service(['/verified/codex'], Path('/unused'), environment={})

    def test_dead_controller_guard_never_starts_child(self):
        import supervision_service_guard as guard
        with patch.object(sys, 'argv', ['guard', '--owner', json.dumps({'pid': 0}), '--', '/bin/true']), \
             patch.object(guard, 'owner_identity', return_value=None), \
             patch.object(guard.subprocess, 'Popen', side_effect=AssertionError('no child')):
            with self.assertRaises(SystemExit): guard.main()

    def test_denied_service_does_not_fall_back_to_host_execution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); code, evidence, _, _ = self.fixture(root)
            with patch.object(iso, 'executable', return_value=Path('/verified/codex')), \
                 patch.object(iso, 'limited_service', side_effect=policy.Blocked('user bus denied')) as service:
                with self.assertRaisesRegex(policy.Blocked, 'user bus'):
                    iso.run_snapshot(code, evidence, root / 'job', 'fake-worker')
            self.assertEqual(service.call_count, 1)


class QualificationGuards(unittest.TestCase):
    def test_snapshot_supplies_required_context_without_raw_runs_or_credentials(self):
        selected = qual.repair_inputs()
        for name in ('AGENTS.md', 'README.md', 'START-HERE.md', 'docs/CODEX-HANDOVER.md',
                     'docs/PROJECT-STATE.md', 'docs/OVERNIGHT-SUPERVISION.md'):
            self.assertIn(name, selected)
        self.assertFalse(any(name.startswith(('runs/', 'results/', 'inputs/', '.codex/', '.git/'))
                             for name in selected))

    def test_regressions_are_collected_as_data_and_cannot_replace_tests(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); output = root / 'output'; (output / 'regressions').mkdir(parents=True)
            frozen = root / 'frozen'; (frozen / 'tests').mkdir(parents=True)
            existing = frozen / 'tests/existing.py'; existing.write_text('retained\n')
            candidate = output / 'regressions/test_supervisor_regression_case.py'
            candidate.write_text('import unittest\n')
            qual.collect_regressions(output, frozen)
            self.assertEqual((frozen / 'tests' / candidate.name).read_text(), candidate.read_text())
            self.assertEqual(existing.read_text(), 'retained\n')
            with self.assertRaises(FileExistsError): qual.collect_regressions(output, frozen)

    def test_prior_denied_attempts_are_preserved_across_restarts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            atomic_json(root / 'qualification-old/allowances.json', {'same-incident': 1})
            budget = qual.seed_allowances(root)
            self.assertEqual(policy.reserve_attempt(budget, 'same-incident'), 2)
            qual.seed_allowances(root)
            with self.assertRaises(policy.Blocked): policy.reserve_attempt(budget, 'same-incident')
            self.assertEqual(read_json(root / 'qualification-old/allowances.json'), {'same-incident': 1})

    def test_missing_resource_gate_does_not_run_codex_or_touch_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); live = root / 'live'; live.mkdir(); p = live / 'state.json'; p.write_text('retained')
            record = {'files': {str(p): __import__('hashlib').sha256(p.read_bytes()).hexdigest()}}
            with patch.object(qual, 'RESULTS', root / 'results'), patch.object(qual, 'ROOT', root), \
                 patch.object(qual, 'retained_state', return_value=record), \
                 patch.object(iso, 'resource_preflight', side_effect=policy.Blocked('not available')), \
                 patch.object(qual, 'codex_repair', side_effect=AssertionError('no real exec')):
                result = qual.qualify_only(root / 'supervisor', live)
            self.assertEqual(result['status'], 'blocked'); self.assertFalse(result['armed'])
            self.assertEqual(p.read_text(), 'retained')


if __name__ == '__main__': unittest.main()
