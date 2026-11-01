"""Offline checks; never run an updater, read auth, or open a Codex session."""
import importlib.util
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest import mock

PATH = Path(__file__).resolve().parents[1] / 'scripts/start-codex-supervision-task.py'
SPEC = importlib.util.spec_from_file_location('codex_profile_setup', PATH)
setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(setup)


class CodexProfileSetupTests(unittest.TestCase):
    def model(self, maximum=872000):
        return {'slug':'gpt-6-astra', 'context_window':272000, 'max_context_window':maximum,
                'effective_context_window_percent':95, 'supported_reasoning_levels':[{'effort':'xhigh'}]}

    def test_preferred_values_and_supported_fallback(self):
        preferred = setup.select_settings(self.model())
        self.assertEqual((preferred['model_context_window'], preferred['model_auto_compact_token_limit']), (800000,650000))
        self.assertEqual(preferred['forced_login_method'], 'chatgpt')
        fallback = setup.select_settings(self.model(272000))
        self.assertEqual(fallback['model_context_window'], 272000)
        self.assertLess(fallback['model_auto_compact_token_limit'], 258400)
        with self.assertRaisesRegex(ValueError, 'xhigh'):
            setup.select_settings({**self.model(), 'supported_reasoning_levels':[]})
        with self.assertRaisesRegex(ValueError, 'headroom'):
            setup.select_settings({**self.model(), 'effective_context_window_percent':None})

    def test_preserves_unrelated_configuration_and_access_mode(self):
        previous = '# operator settings\nmodel = "older"\nweb_search = "cached"\n\n[custom]\nnote = "leave me alone"\n'
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'profile.config.toml'
            p.write_text(previous)
            mode = p.stat().st_mode
            settings = setup.select_settings(self.model())
            backup = setup.install_profile(p, settings, 'test')
            self.assertEqual(Path(backup).read_text(), previous)
            self.assertEqual(p.stat().st_mode, mode)
            self.assertEqual(Path(backup).stat().st_mode, mode)
            data = tomllib.loads(p.read_text())
            self.assertEqual(data['custom'], {'note':'leave me alone'})
            self.assertEqual(data['web_search'], 'cached')
            self.assertEqual(data['model'], 'gpt-6-astra')
            self.assertIsNone(setup.install_profile(p, settings, 'second'))
            self.assertEqual(len(list(Path(td).glob('*.before-*'))),1)

    def test_symlink_and_unknown_catalog_are_refused(self):
        with tempfile.TemporaryDirectory() as td:
            original = Path(td) / 'original'; original.write_text('untouched')
            p = Path(td) / 'profile'; p.symlink_to(original)
            with self.assertRaisesRegex(RuntimeError, 'symlink'):
                setup.install_profile(p, setup.select_settings(self.model()), 'test')
            self.assertEqual(original.read_text(), 'untouched')
        with self.assertRaises(ValueError):
            setup.select_settings({**self.model(), 'slug':'different-model'})

    def test_fresh_session_receives_handover_without_permission_overrides(self):
        argv = setup.launch_args(Path('/fake/stable/codex'), Path('/fake/setup.json'))
        self.assertIn('--no-daemon',argv)
        self.assertEqual(argv[argv.index('--profile')+1], 'pdf-to-latex-supervision')
        self.assertIn(str(setup.TASK),argv[-1])
        self.assertIn(str(setup.HANDOVER),argv[-1])
        for forbidden in ('--remote','--sandbox','--ask-for-approval','--worktree','resume','--dangerously-bypass-approvals-and-sandbox'):
            self.assertNotIn(forbidden,argv)

    def test_preview_and_api_key_auth_are_not_silently_used(self):
        with mock.patch.object(setup,'captured',return_value='codex-cli 0.166.0-alpha.1\n'):
            with self.assertRaisesRegex(RuntimeError,'stable'):
                setup.cli_version('/fake/codex')
        with mock.patch.object(setup,'captured',return_value='Logged in using an API key'):
            with self.assertRaisesRegex(RuntimeError,'ChatGPT'):
                setup.chatgpt_login('/fake/codex')
        with mock.patch.object(setup,'captured',return_value='Logged in using ChatGPT'):
            setup.chatgpt_login('/fake/codex')


if __name__ == '__main__':
    unittest.main()
