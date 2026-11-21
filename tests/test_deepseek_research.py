import copy
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

from probe import deepseek_research as r, research_billing as accounting
from probe.common import atomic_json, read_json, writer_lock
from probe.local_model import LocalClient
from probe.batch_review import IntegrityError
from scripts import deepseek_research_comparison as runner, deepseek_research_grade as grade

PACK = Path('/home/mdi/Downloads/DeepSeek_Research_Comparison_20261116')
CFG = {'budget_usd': '6.00', 'pilot_budget_usd': '6.00',
       'paid_limits': {'trial_calls': 32, 'readiness_calls': 6},
       'rates': {'prompt': '.000000098', 'completion': '.000000294', 'input_cache_read': '.00000000294'},
       'context_length': 1048576, 'cap': 262144, 'adjustments': []}
MESSAGES = [{'role': 'system', 'content': 'Task'}, {'role': 'user', 'content': 'Question'}]


class PackTests(unittest.TestCase):
    def setUp(self):
        if not PACK.exists():
            self.skipTest('User-supplied comparison kit is not installed')
        self.packets, self.plan = r.verify_pack(PACK)

    def test_counts_counterbalance_and_identical_content(self):
        self.assertEqual(len(self.plan), 64)
        self.assertEqual(len({x['base_id'] for x in self.plan}), 12)
        for condition in {x['condition_id'] for x in self.plan}:
            rows = [x for x in self.plan if x['condition_id'] == condition]
            self.assertEqual(len(rows), 4)
            self.assertEqual(len({x['messages_sha256'] for x in rows}), 1)
        for offset in range(0, 64, 2):
            a, b = self.plan[offset:offset+2]
            self.assertEqual(a['condition_id'], b['condition_id'])
            self.assertNotEqual(a['arm'], b['arm'])

    def test_public_whitelist_and_no_image_transcript(self):
        for path in ('private/RUBRIC.md', 'CODEX_PROMPT.md', 'public/../private/numerical_checks.py'):
            with self.assertRaises(ValueError):
                self.packets.public_file(path)
        for base in ('V01', 'V02'):
            messages = self.packets.build_messages(base + '_image')
            self.assertEqual(len(messages[1]['content']), 2)
            self.assertEqual(messages[1]['content'][0]['text'], (PACK / 'public/prompts' / (base + '.md')).read_text())
            self.assertNotIn((PACK / 'public/fixtures' / (base + '.txt')).read_text(), json.dumps(messages))

    def test_long_and_focused_questions_identical(self):
        for base in ('L01', 'L02'):
            texts = [self.packets.build_messages(base + suffix)[1]['content'][0]['text'] for suffix in ('_focused', '_long')]
            self.assertEqual(texts[0].split('\n\n<source')[0], texts[1].split('\n\n<source')[0])


class ControlsTests(unittest.TestCase):
    def test_exact_controls_and_provider(self):
        for arm in r.ARMS:
            body = r.body_for(MESSAGES, arm, 262144, 13, CFG)
            r.validate_body(body, arm, CFG)
            self.assertEqual(body['top_k'], 0)
            self.assertEqual(body['top_p'], 1)
            self.assertNotIn('tools', body)
            self.assertNotIn('stop', body)
            self.assertNotIn('response_format', body)
            for field, value in [('top_k', 20), ('temperature', 0), ('seed', 14)]:
                changed = copy.deepcopy(body)
                changed[field] = value
                if field != 'seed':
                    with self.assertRaises(IntegrityError):
                        r.validate_body(changed, arm, CFG)
        hosted = r.body_for(MESSAGES, r.ARMS[1], 262144, 13, CFG)
        self.assertEqual(hosted['provider']['only'], [r.TAG])
        self.assertFalse(hosted['provider']['allow_fallbacks'])
        self.assertTrue(hosted['provider']['require_parameters'])
        self.assertEqual(hosted['reasoning']['effort'], 'high')

    def test_cost_includes_full_window_and_all_38_calls(self):
        bound = r.cost_bound(CFG, {'max_tokens': 262144})
        self.assertEqual(bound, Decimal('0.154140672'))
        self.assertEqual(bound * 38, Decimal('5.857345536'))
        self.assertLess(bound * 38, Decimal('6'))

    def test_lifetime_and_remaining_not_double_counted(self):
        self.assertEqual(accounting.available({'limit': 12.8, 'usage': 6.8, 'limit_remaining': 6},
                         {'total_credits': 20, 'total_usage': 6.8}, '.2'), Decimal('5.8'))

    def test_only_explicit_no_capacity_refusal_releases(self):
        raw = {'error': {'code': 429, 'metadata': {'provider_error_code': 'no_asap_capacity',
               'limit_source': 'upstream_provider_shared_pool', 'provider_name': 'Sail Research'}}}
        error = {'message': 'OpenRouter HTTP 429; no retry', 'cloud_reservation': '0037'}
        reservation = {'id': '0037'}
        self.assertTrue(accounting.no_capacity_rejection(raw, error, reservation))
        for bad in [dict(raw, id='gen-known'), dict(raw, usage={'cost': .1}), dict(raw, choices=[{}]), {}]:
            self.assertFalse(accounting.no_capacity_rejection(bad, error, reservation))
        self.assertFalse(accounting.no_capacity_rejection(raw, error, dict(reservation, generation_id='gen-x')))

    def test_two_hour_transport_constructor_bound(self):
        c = LocalClient(r.LOCAL_URL, purpose='simple_chapter', timeout=7200, max_tokens=262144)
        self.assertEqual(c.timeout, 7200)
        with self.assertRaises(ValueError):
            LocalClient(r.LOCAL_URL, purpose='simple_chapter', timeout=7201)


class AttemptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        atomic_json(self.run / 'binding.json', {'config': CFG, 'files': {}, 'code': {}})
        self.state = {'status': 'running', 'attempts': []}
        r.save(self.run, self.state)

    def test_reserve_restart_duplicate_and_budget(self):
        ledger = r.ledger(self.run, create=True)
        body = {'max_tokens': 262144}
        with writer_lock(self.run):
            ledger.reserve(body, self.run / 'one', Decimal('6'), 'trial')
        again = r.ledger(self.run)
        self.assertEqual(again.summary()['unresolved_reserved_usd'], '0.154140672')
        with self.assertRaises(Exception):
            again.reserve(body, self.run / 'one', Decimal('6'), 'trial')
        with self.assertRaises(Exception):
            again.reserve(body, self.run / 'two', Decimal('.01'), 'trial')
        again.settle('0001', {'usage': {'cost': .01, 'prompt_tokens': 100, 'completion_tokens': 100}}, 'fixture')
        again.settle('0001', {'usage': {'cost': .01}}, 'repeat')
        self.assertEqual(again.summary()['actual_reported_usd'], '0.01')

    def test_dispatch_marker_precedes_transport_and_no_resend(self):
        task = {'attempt_id': 'one', 'arm': r.ARMS[0], 'phase': 'scored'}
        body = r.body_for(MESSAGES, task['arm'], 262144, 42, CFG)
        client = Mock()
        def fail(*args):
            self.assertEqual(read_json(self.run / 'state.json')['attempts'][0]['status'], 'dispatched')
            raise TimeoutError('ambiguous')
        client._request.side_effect = fail
        result = r.dispatch(self.run, self.state, task, body, client=client)
        self.assertEqual(result['status'], 'uncertain_dispatch')
        r.dispatch(self.run, self.state, task, body, client=client)
        client._request.assert_called_once()

    def test_prepared_not_dispatched_can_resume_once(self):
        task = {'attempt_id': 'one', 'arm': r.ARMS[0], 'phase': 'scored'}
        body = r.body_for(MESSAGES, task['arm'], 262144, 42, CFG)
        before = Mock(side_effect=RuntimeError('occupied'))
        with self.assertRaises(RuntimeError):
            r.dispatch(self.run, self.state, task, body, before_local=before)
        self.assertEqual(self.state['attempts'][0]['status'], 'prepared')
        client = Mock()
        client._request.return_value = ({'model': r.LOCAL_MODEL, 'choices': [{'finish_reason': 'stop', 'message': {'content': 'answer'}}]}, {})
        self.assertEqual(r.dispatch(self.run, self.state, task, body, client=client)['status'], 'success')
        r.dispatch(self.run, self.state, task, body, client=client)
        client._request.assert_called_once()

    def test_interrupted_dispatched_stays_consumed(self):
        self.state['attempts'] = [{'id': 'x', 'status': 'dispatched'}]
        r.recover_attempts(self.run, self.state)
        self.assertEqual(self.state['attempts'][0]['status'], 'uncertain_dispatch')

    def test_qualification_limit_counts_failures(self):
        self.state['attempts'] = [{'id': str(i), 'arm': r.ARMS[0], 'phase': 'qualification', 'status': 'api_error'} for i in range(6)]
        with self.assertRaises(IntegrityError):
            r.dispatch(self.run, self.state, {'attempt_id': '7', 'arm': r.ARMS[0], 'phase': 'qualification'},
                       r.body_for(MESSAGES, r.ARMS[0], 262144, 1, CFG))

    def test_provider_mismatch_halts_and_settles(self):
        r.ledger(self.run, create=True)
        client = Mock()
        client.admission.return_value = Decimal('6')
        client.ledger = r.ledger(self.run)
        client._redact.side_effect = lambda x: x
        client.stream.return_value = ({'model': r.MODEL, 'usage': {'cost': .01},
                                      'choices': [{'finish_reason': 'stop', 'message': {'content': 'answer'}}]}, {})
        with patch.object(r, 'stream_metadata', return_value={'generation_ids': ['gen-test'], 'providers': ['Wrong'], 'models': [r.MODEL]}):
            r.dispatch(self.run, self.state, {'attempt_id': 'x', 'arm': r.ARMS[1], 'phase': 'scored'},
                       r.body_for(MESSAGES, r.ARMS[1], 262144, 1, CFG), client=client)
        self.assertIn('identity_blocker', self.state)
        self.assertEqual(client.ledger.summary()['actual_reported_usd'], '0.01')

    def test_partial_final_and_absent_reasoning_are_distinct(self):
        x = r.outcome({'choices': [{'finish_reason': 'length', 'message': {'content': 'partial'}}]})
        self.assertTrue(x['usable_final'])
        self.assertEqual(x['status'], 'output_exhaustion')
        self.assertIsNone(x['reasoning_tokens'])

    def test_finished_resume_zero_clients_or_services(self):
        self.state['status'] = 'finished'
        r.save(self.run, self.state)
        client, services = Mock(), Mock()
        with patch.object(runner, 'ROOT', self.run):
            # Different lock directories, like the real project/run hierarchy.
            project = self.run / 'project'
            with patch.object(runner, 'ROOT', project):
                runner.worker(self.run, hosted_factory=client, services_factory=services)
        client.assert_not_called()
        services.assert_not_called()

    def test_restoration_even_when_start_fails_or_cancelled(self):
        atomic_json(self.run / 'QUALIFICATION_PLAN.json', {'planned': [
            {'attempt_id': 'a', 'arm': r.ARMS[0], 'phase': 'qualification'},
            {'attempt_id': 'b', 'arm': r.ARMS[1], 'phase': 'qualification'}]})
        atomic_json(self.run / 'plan.json', [])
        for error in (RuntimeError('start failed'), KeyboardInterrupt('cancel')):
            hosted = Mock()
            hosted._redact.side_effect = str
            services = Mock()
            services.start.side_effect = error
            with patch.object(runner, 'ROOT', self.run / 'project'), patch.object(runner, 'request', return_value={}):
                runner.worker(self.run, hosted_factory=lambda _: hosted, services_factory=lambda *_: services)
            services.restore.assert_called_once()


class StreamAndGradeTests(unittest.TestCase):
    def test_hosted_usage_trailer_and_reasoning_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            stream = r.HostedStream(Path(tmp), r.MODEL, json.loads)
            values = [
                {'model': r.MODEL, 'choices': [{'delta': {'reasoning': 'work', 'content': ''}}]},
                {'model': r.MODEL, 'choices': [{'delta': {'content': '68'}, 'finish_reason': 'stop'}]},
                {'model': r.MODEL, 'choices': [{'delta': {'content': ''}, 'finish_reason': 'stop'}],
                 'usage': {'cost': .001}}]
            wire = b''.join(('data: ' + json.dumps(v) + '\n\n').encode() for v in values) + b'data: [DONE]\n\n'
            stream.feed(wire)
            result = stream.response()
            stream.close()
            self.assertEqual((Path(tmp) / 'response.raw').read_bytes(), wire)
            self.assertEqual(result['choices'][0]['message']['content'], '68')
            self.assertEqual(result['choices'][0]['message']['reasoning_content'], 'work')
            self.assertEqual(result['usage']['cost'], .001)

    def test_hosted_trailer_does_not_hide_conflict_or_incomplete_stream(self):
        for finish, content, done in [('length', '', True), ('stop', 'extra', True), ('stop', '', False)]:
            with tempfile.TemporaryDirectory() as tmp:
                stream = r.HostedStream(Path(tmp), r.MODEL, json.loads)
                stream.event(json.dumps({'model': r.MODEL, 'choices': [
                    {'delta': {'content': '68'}, 'finish_reason': 'stop'}]}).encode())
                with self.assertRaises(ValueError):
                    stream.event(json.dumps({'model': r.MODEL, 'choices': [
                        {'delta': {'content': content}, 'finish_reason': finish}], 'usage': {'cost': .001}}).encode())
                    if done:
                        stream.event(b'[DONE]')
                    stream.response()
                stream.close()

    def test_partial_stream_saved_before_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            client = object.__new__(r.HostedClient)
            client._key = 'not-a-real-secret'
            response = Mock(status=200)
            response.getheader.return_value = 'text/event-stream'
            event = {'model': r.MODEL, 'provider': 'DeepInfra', 'id': 'gen-fixture',
                     'choices': [{'index': 0, 'delta': {'content': 'partial'}}]}
            wire = ('data: ' + json.dumps(event) + '\n\n').encode()
            response.read1.side_effect = [wire, TimeoutError('test absolute deadline')]
            connection = Mock()
            connection.getresponse.return_value = response
            client._connection = Mock(return_value=connection)
            with self.assertRaises(TimeoutError):
                client.stream({}, folder)
            self.assertEqual((folder / 'response.raw').read_bytes(), wire)
            self.assertEqual((folder / 'answer.txt').read_text(), 'partial')
            self.assertEqual(read_json(folder / 'transport.json')['absolute_timeout_seconds'], 7200)
            connection.request.assert_called_once()

    def test_extraction_preserves_module_and_isolation_contract(self):
        code = 'import math\n\ndef f():\n    return 1\n'
        self.assertEqual(grade.extract_code('```python\n' + code + '```\nExplanation.'), code)
        with self.assertRaises(ValueError):
            grade.extract_code('```python\na=1\n```\n```python\na=2\n```')
        self.assertTrue(grade.prohibited_code('import os\nos.system("ls")'))
        command = grade.sandbox_command(Path('/checks'), Path('/candidate'), 'C01')
        self.assertIn('--unshare-all', command)
        self.assertIn('--clearenv', command)
        self.assertNotIn(str(r.ROOT), command)
        self.assertNotIn(cloud_key_path(), command)


def cloud_key_path():
    return '/home/mdi/.config/pdf-to-latex/openrouter.key'
