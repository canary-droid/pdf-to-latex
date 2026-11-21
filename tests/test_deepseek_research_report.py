"""Synthetic reporting checks; no real identity map or generation is read."""
import base64
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from probe import deepseek_research as r
from probe.common import atomic_json, read_json, sha
from scripts import deepseek_research_report as report


PACK = Path('/home/mdi/Downloads/DeepSeek_Research_Comparison_20261116')


class ResearchReportTests(unittest.TestCase):
    def setUp(self):
        if not PACK.exists():
            self.skipTest('User-supplied comparison kit is not installed')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / 'run'
        self.destination = Path(self.temp.name) / 'result'
        self.destination.mkdir()
        self.plan = read_json(PACK / 'run_plan.json')
        self.mapping = {f'S{i:03d}': task for i, task in enumerate(self.plan, 1)}
        self.scores = {}
        attempts = []
        for i, (identifier, task) in enumerate(self.mapping.items()):
            folder = self.run / 'attempts' / task['attempt_id']
            atomic_json(folder / 'outcome.json', {
                'usable_final': True, 'status': 'success', 'finish_reason': 'stop',
                'elapsed_seconds': 10 + i, 'finished_at': '2026-01-01T00:03:00+00:00',
                'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'cost': .001},
                'reasoning_tokens': 30})
            self.scores[identifier] = {'criteria': [4] * 5, 'notes': 'Synthetic grade',
                                      'criterion_notes': [f'Criterion {j}' for j in range(1, 6)]}
            attempts.append({'id': task['attempt_id'],
                             'dispatched_at': '2026-01-01T00:00:00+00:00' if i < 16
                                              else '2026-01-01T00:02:00+00:00'})
        atomic_json(self.run / 'state.json', {'attempts': attempts})
        atomic_json(self.run / 'grading/identity-map.json', self.mapping)
        atomic_json(self.run / 'inspection/recovery/resume-intent.json',
                    {'at': '2026-01-01T00:01:00+00:00', 'reason': 'Synthetic interruption'})

    def calculate(self):
        path = self.run / 'grading/scores.json'
        atomic_json(path, self.scores)
        (self.run / 'grading/scores.sha256').write_text(sha(path) + '\n')
        return report.metrics(self.run, self.destination)

    def test_conditions_do_not_double_family_weight_and_all_repetitions_count(self):
        # Only vision receives credit: it remains one of six equal families.
        family = next(x['family'] for x in self.plan if x['base_id'] == 'V01')
        for identifier, task in self.mapping.items():
            value = 4 if task['family'] == family else 0
            if task['arm'] == 'hosted_fp8' and task['repetition'] == 2:
                value = 0
            self.scores[identifier]['criteria'] = [value] * 5
        result = self.calculate()
        self.assertAlmostEqual(result['local_exl3']['overall'], 100 / 6)
        self.assertAlmostEqual(result['hosted_fp8']['overall'], 50 / 6)
        self.assertEqual(result['base_task_wins_ties_losses_hosted']['independent_base_task_clusters'], 12)
        self.assertEqual(result['hosted_fp8']['repetitions']['1'][family], 100)
        self.assertEqual(result['hosted_fp8']['repetitions']['2'][family], 0)
        with (self.destination / 'per-criterion.csv').open() as f:
            self.assertEqual(next(csv.DictReader(f))['notes'], 'Criterion 1')

    def test_delivery_exclusion_is_separate_and_sensitivity_and_interruption_recorded(self):
        for identifier, task in self.mapping.items():
            if task['base_id'] == 'R01' and task['arm'] == 'local_exl3':
                self.scores[identifier]['criteria'] = [0] * 5
                path = self.run / 'attempts' / task['attempt_id'] / 'outcome.json'
                outcome = read_json(path)
                outcome.update(usable_final=False, status='api_error', finish_reason=None)
                atomic_json(path, outcome)
        identifier = next(k for k, t in self.mapping.items() if t['base_id'] == 'R02'
                          and t['arm'] == 'local_exl3' and t['repetition'] == 1)
        self.scores[identifier].update(contested=True, alternative_criteria=[4, 4, 4, 4, 3])
        result = self.calculate()
        local = result['local_exl3']
        self.assertEqual(local['delivered'], 30)
        self.assertEqual(local['strict_successes'], 30)
        self.assertEqual(local['conditional_overall'], 100)
        self.assertAlmostEqual(local['overall'], 550 / 6)
        bounds = result['contested_grade_sensitivity']['local_exl3']
        self.assertAlmostEqual(bounds['upper']['overall'] - bounds['lower']['overall'], 5 / 24)
        self.assertAlmostEqual(bounds['upper']['conditional_overall'] - bounds['lower']['conditional_overall'], 5 / 12)
        self.assertEqual(len(result['contested_attempts']), 1)
        with (self.destination / 'per-condition.csv').open() as f:
            conditions = list(csv.DictReader(f))
        with (self.destination / 'per-task.csv').open() as f:
            tasks = list(csv.DictReader(f))
        self.assertEqual(len(conditions), 32)
        self.assertEqual(len(tasks), 24)
        r01 = next(x for x in tasks if x['base_id'] == 'R01' and x['arm'] == 'local_exl3')
        self.assertEqual(float(r01['practical_score']), 0)
        self.assertEqual(r01['conditional_quality_score'], '')
        self.assertEqual(int(r01['delivered']), 0)
        timing = result['timing']['by_arm_and_invocation']
        self.assertEqual(sum(x['attempts'] for x in timing), 64)
        self.assertEqual({x['invocation'] for x in timing}, {1, 2})

    def test_missing_final_cannot_receive_credit_and_scores_must_be_locked(self):
        task = next(iter(self.mapping.values()))
        path = self.run / 'attempts' / task['attempt_id'] / 'outcome.json'
        outcome = read_json(path)
        outcome['usable_final'] = False
        atomic_json(path, outcome)
        with self.assertRaisesRegex(ValueError, 'Missing final'):
            self.calculate()
        (self.run / 'grading/scores.sha256').write_text('changed\n')
        with self.assertRaisesRegex(ValueError, 'not locked'):
            report.metrics(self.run, self.destination)

    def test_archive_secret_check_blocks_leaked_answer_without_echoing_secret(self):
        path = Path(self.temp.name) / 'answer.txt'
        secret = 'synthetic-credential-not-a-real-key'
        path.write_text('Ordinary model answer')
        report.verify_no_runtime_secret([path], secret)
        path.write_text('Model answer includes ' + secret)
        with self.assertRaises(ValueError) as caught:
            report.verify_no_runtime_secret([path], secret)
        self.assertNotIn(secret, str(caught.exception))

    def test_qualification_recipes_preserve_content_and_reject_changed_source(self):
        system = {'role': 'system', 'content': 'Synthetic public control'}
        text = 'Return the identifier.'
        for name in ('rough_heston.tex', 'cos.tex', 'markov.tex'):
            path = self.run / 'pack/public/sources' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Synthetic source with μ and a final newline.\n')
            text += '\n\n<source filename="' + name + '">\n' + path.read_text() + '\n</source>'
        atomic_json(self.run / 'qualification-inputs/long.json', [system, {'role': 'user', 'content': text}])
        image = self.run / 'qualification-inputs/numbers.png'
        image.write_bytes(b'synthetic image bytes')
        content = [{'type': 'text', 'text': 'Read two integers.'}, {'type': 'image_url', 'image_url': {
            'url': 'data:image/png;base64,' + base64.b64encode(image.read_bytes()).decode()}}]
        atomic_json(self.run / 'qualification-inputs/image.json', [system, {'role': 'user', 'content': content}])
        for kind in ('long', 'image'):
            recipe = report.qualification_recipe(self.run, kind)
            self.assertTrue(recipe['reconstruction_verified'])
            expected = hashlib.sha256(json.dumps(
                read_json(self.run / 'qualification-inputs' / (kind + '.json')),
                ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            self.assertEqual(recipe['messages_sha256'], expected)
            self.assertNotIn('Synthetic source with', str(recipe))
            self.assertNotIn('c3ludGhldGljIGltYWdlIGJ5dGVz', str(recipe))
        (self.run / 'pack/public/sources/cos.tex').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'differs'):
            report.qualification_recipe(self.run, 'long')

    def test_billing_columns_separate_reported_verified_and_uncertain_amounts(self):
        state = read_json(self.run / 'state.json')
        hosted_ids = [x['attempt_id'] for x in self.plan if x['arm'] == 'hosted_fp8'][:2]
        for item in state['attempts']:
            if item['id'] in hosted_ids:
                item['billing_reservation'] = 't001' if item['id'] == hosted_ids[0] else 't002'
        atomic_json(self.run / 'state.json', state)
        atomic_json(self.run / 'billing.json', {'reservations': [
            {'id': 't001', 'reserved_usd': '.2', 'actual_cost_usd': '.001'},
            {'id': 't002', 'reserved_usd': '.2'}]})
        atomic_json(self.run / 'inspection/completion-audit-20261117/billing-verification.json',
                    {'records': [{'reservation': 't001', 'fresh_billing': {'total_cost': .000999999}},
                                 {'reservation': 't002', 'generation_id': None}]})
        first = self.run / 'attempts' / hosted_ids[0] / 'outcome.json'
        value = read_json(first)
        value['metadata'] = {'providers': ['DeepInfra'], 'models': [r.MODEL]}
        atomic_json(first, value)
        second = self.run / 'attempts' / hosted_ids[1] / 'outcome.json'
        value = read_json(second)
        value.update(usable_final=False, status='api_error', finish_reason=None)
        atomic_json(second, value)
        atomic_json(second.parent / 'transport.json', {'http_status': 520, 'error': 'Synthetic provider error'})
        mid = next(k for k, t in self.mapping.items() if t['attempt_id'] == hosted_ids[1])
        self.scores[mid]['criteria'] = [0] * 5
        self.calculate()
        with (self.destination / 'per-attempt.csv').open() as f:
            rows = {x['attempt_id']: x for x in csv.DictReader(f)}
        self.assertEqual(float(rows[hosted_ids[0]]['cost_usd']), .001)
        self.assertEqual(float(rows[hosted_ids[0]]['verified_generation_cost_usd']), .000999999)
        self.assertEqual(rows[hosted_ids[0]]['unresolved_reservation_usd'], '0')
        self.assertEqual(rows[hosted_ids[1]]['verified_generation_cost_usd'], '')
        self.assertEqual(float(rows[hosted_ids[1]]['unresolved_reservation_usd']), .2)
        self.assertEqual(rows[hosted_ids[0]]['returned_providers'], 'DeepInfra')
        self.assertEqual(rows[hosted_ids[0]]['returned_models'], r.MODEL)
        self.assertEqual(rows[hosted_ids[1]]['http_status'], '520')
        self.assertEqual(rows[hosted_ids[1]]['transport_error'], 'Synthetic provider error')


if __name__ == '__main__':
    unittest.main()
