"""Simple route regressions. No live HTTP or real compiler is invoked here."""
import copy
import json
import re
import subprocess
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts import simple_chapter_glm as simple
from probe import chapter_glm as runtime, chapter_protocol as protocol
from probe.common import atomic_json, read_json, fingerprint, files_manifest, sha


def block(bid, text, kind='text', y=.2, page=1):
    return {'id': bid, 'kind': kind, 'bbox': [.1, y, .8, y + .02], 'assets': [],
            'native': {'type': kind, 'content': text}, 'tex': text,
            'page': {'selected_page': page, 'original_physical_page': page + 105, 'owner': True}}


def data(blocks):
    return {'blocks': blocks, 'pages': [{'page': b['page']} for b in
            {b['page']['selected_page']: b for b in blocks}.values()]}


class SimpleInputsTests(unittest.TestCase):
    def test_running_header_requires_folio_and_matching_heading(self):
        blocks = [block('header', '4.6. ITO’S FORMULA', 'paragraph_title', .048),
                  block('folio', '111', 'page_number', .05),
                  block('heading', '4.6 Itô’s Formula', 'paragraph_title', .6),
                  block('equation', r'\left.\partial_x f\right|_{x=0}', 'equation')]
        text, ledger = simple.chapter_text(data(blocks))
        self.assertNotIn('4.6. ITO', text); self.assertIn('4.6 Itô', text)
        self.assertIn(blocks[-1]['tex'], text); self.assertEqual(ledger['native_math_strings'], 1)
        self.assertEqual(ledger['furniture_count'], 2)
        for row in ledger['blocks']:
            if not row['excluded_furniture']:
                self.assertEqual(text[row['start']:row['end']].strip(), next(b['tex'] for b in blocks if b['id'] == row['id']))
        self.assertIsNone(simple.furniture(blocks[0], [blocks[0], blocks[1]]))
        self.assertIsNone(simple.furniture(blocks[0], [blocks[0], blocks[2]]))

    def test_whole_paragraph_and_native_formula_no_markers(self):
        bs = [block('b0', 'Full prose, assumptions, and references.'),
              block('b1', r'\badPortableGrammar{\alpha_{i,j}}', 'equation')]
        source, ledger = simple.chapter_text(data(bs))
        self.assertIn(bs[0]['tex'], source); self.assertIn(bs[1]['tex'], source)
        self.assertEqual([r['id'] for r in ledger['blocks']], ['b0', 'b1'])
        self.assertNotIn('% SRC', source)

    def test_no_duplicate_or_context_pages(self):
        d = data([block('b', 'text')])
        d['pages'] *= 2
        with self.assertRaises(ValueError): simple.chapter_text(d)
        d = data([block('b', 'text')]); d['pages'][0]['page']['owner'] = False
        with self.assertRaises(ValueError): simple.chapter_text(d)
        d = data([block('b', 'text'), block('b', 'text')])
        with self.assertRaises(ValueError): simple.chapter_text(d)

    def test_math_loss_rejected_before_dispatch(self):
        b = block('b', r'\alpha', 'equation'); b['tex'] = 'missing formula'
        with self.assertRaises(ValueError): simple.chapter_text(data([b]))

    def test_simple_long_prompt_without_legacy_contract(self):
        source = 'Complete chapter\n' + 'Prose and $x$\n' * 15000 + 'LAST WORD'
        q = simple.request(source)
        self.assertEqual(len(q['messages']), 1)
        self.assertIn(source, q['messages'][0]['content'])
        self.assertEqual(set(q), {'model', 'messages', 'max_tokens', 'stream'})
        self.assertEqual(q['max_tokens'], 131072)
        for term in ('ASSIGNED BLOCKS', '% END', '% SRC', 'response_format'):
            self.assertNotIn(term, json.dumps(q))
        with self.assertRaises(ValueError): protocol.budget(q, 32768)

    def test_fresh_review_uses_exact_source_and_generated(self):
        q = simple.request('Full source', 'Exact generated file')
        self.assertEqual(len(q['messages']), 1)
        self.assertIn('Full source', q['messages'][0]['content'])
        self.assertIn('Exact generated file', q['messages'][0]['content'])
        self.assertNotIn(simple.CONVERT, q['messages'][0]['content'])
        self.assertEqual(q['max_tokens'], 32768)

    def test_detokenize_and_plain_assets_are_equivalent_warnings(self):
        source = r'\includegraphics[width=\linewidth]{\detokenize{assets/plot.jpg}}'
        output = r'\includegraphics{assets/plot.jpg}'
        observations = simple.document_observations(output, source, {'assets/plot.jpg'})
        self.assertEqual(observations['source_assets_not_referenced'], [])
        self.assertEqual(observations['references_without_supplied_asset'], [])
        self.assertEqual(simple.document_observations('', source, {})['source_assets_not_referenced'], ['assets/plot.jpg'])


class SimpleExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        self.task = {'key': 'test', 'phase': 'convert', 'id': 'test/convert', 'status': 'pending'}
        self.state = {'first_dispatch': None, 'calls': [], 'tasks': [self.task],
                      'connection_failures': 0, 'compile_unavailable': None, 'status': 'prepared_offline'}
        folder = self.run / 'inputs/test'; folder.mkdir(parents=True)
        (folder / 'source.tex').write_text('Source with full paragraph')
        atomic_json(folder / 'assets.json', [])

    def invoke(self, output, failure='truncation'):
        def fake(run, state, parent, body, **kwargs):
            call = runtime.reserve(state, parent, fingerprint(body))
            call.update(status='completed_response' if output is not None else 'failed',
                        failure_kind=failure, error='output limit', metadata={'finish_reason': 'stop' if output else 'length'})
            return output, call
        return fake

    def test_complete_file_needs_no_old_markers_and_compile_failure_keeps_it(self):
        output = '\\documentclass{book}\n\\begin{document}Body\\end{document}'
        with patch.object(runtime, 'invoke', side_effect=self.invoke(output)), \
             patch.object(simple.tex_compile, 'compile_document', return_value={'status': 'syntax_failure'}):
            simple.task_once(self.run, self.state, self.task)
        self.assertEqual(self.task['status'], 'complete_response')
        self.assertEqual(self.task['compilation']['status'], 'syntax_failure')
        self.assertEqual((self.run / self.task['output']).read_text(), output)

    def test_incomplete_document_warning_does_not_reject_normal_response(self):
        with patch.object(runtime, 'invoke', side_effect=self.invoke('A normally completed answer')), \
             patch.object(simple.tex_compile, 'compile_document', return_value={'status': 'build_failure_unresolved'}):
            simple.task_once(self.run, self.state, self.task)
        self.assertEqual(self.task['status'], 'complete_response')
        self.assertFalse(self.task['document_observations']['end_document_present'])

    def test_length_or_empty_is_preserved_without_identical_retry(self):
        for reason in ('truncation', 'empty_reasoning_only', 'timeout'):
            state = copy.deepcopy(self.state); task = state['tasks'][0]
            with patch.object(runtime, 'invoke', side_effect=self.invoke(None, reason)) as invoke:
                simple.task_once(self.run, state, task)
                simple.task_once(self.run, state, task)
            self.assertEqual(task['status'], reason); self.assertEqual(invoke.call_count, 1)

    def test_interrupted_completed_or_reserved_calls_never_replayed(self):
        for status in ('in_progress', 'completed_response'):
            state = copy.deepcopy(self.state); task = state['tasks'][0]
            call = runtime.reserve(state, task['id'], 'body'); call['status'] = status
            with patch.object(runtime, 'invoke') as invoke:
                simple.task_once(self.run, state, task)
            invoke.assert_not_called(); self.assertEqual(task['status'], 'unresolved_interruption')

    def test_outer_fence_only_is_transparently_removed(self):
        with patch.object(runtime, 'invoke', side_effect=self.invoke('```tex\nOriginal TeX\n```')), \
             patch.object(simple, 'compile_draft'):
            simple.task_once(self.run, self.state, self.task)
        self.assertEqual((self.run / self.task['output']).read_text(), 'Original TeX\n')
        self.assertTrue(self.task['outer_fence_stripped'])

    def test_empty_fence_is_an_empty_answer_not_gate_success(self):
        with patch.object(runtime, 'invoke', side_effect=self.invoke('```tex\n\n```')), \
             patch.object(simple, 'compile_draft') as compiler:
            simple.task_once(self.run, self.state, self.task)
        self.assertEqual(self.task['status'], 'empty_answer')
        compiler.assert_not_called()

    def test_ambiguous_answer_retained_but_not_compiled_or_used_for_review(self):
        answer = ('```latex\n' + DOCUMENT + '```\n') * 2
        with patch.object(runtime, 'invoke', side_effect=self.invoke(answer)) as invoked, \
             patch.object(simple, 'compile_draft') as compiler:
            simple.task_once(self.run, self.state, self.task)
            review = {'id': 'test/review', 'key': 'test', 'phase': 'review', 'status': 'pending'}
            self.state['tasks'].append(review)
            simple.task_once(self.run, self.state, review)
        self.assertEqual(self.task['status'], 'complete_response')
        self.assertFalse(self.task['draft_available']); self.assertNotIn('output', self.task)
        self.assertEqual((self.run / self.task['raw_answer']).read_text(), answer)
        self.assertEqual(review['status'], 'unavailable')
        compiler.assert_not_called(); self.assertEqual(invoked.call_count, 1)

    def test_gatheral_gate_failure_remains_independent_of_klebaner(self):
        self.state['tasks'] = [
            {'id': 'klebaner-04/convert', 'key': 'klebaner-04', 'phase': 'convert', 'status': 'complete_response'},
            {'id': 'gatheral-01/convert', 'key': 'gatheral-01', 'phase': 'convert', 'status': 'truncation'},
            {'id': 'gatheral-02/convert', 'key': 'gatheral-02', 'phase': 'convert', 'status': 'pending'}]
        with patch.object(simple, 'task_once') as attempt:
            with self.assertRaisesRegex(runtime.StopRun, 'Gatheral 1'): simple.run_schedule(self.run, self.state)
        attempt.assert_not_called()

    def test_klebaner_truncation_does_not_block_gatheral_expansion(self):
        self.state['tasks'] = [{'id': k + '/convert', 'key': k, 'phase': 'convert', 'status': 'pending'}
                               for k in ('klebaner-04', 'gatheral-01', 'gatheral-02')]
        seen = []
        def attempt(run, state, task, client):
            seen.append(task['key']); task['status'] = 'truncation' if len(seen) == 1 else 'complete_response'
        with patch.object(simple, 'verify'), patch.object(simple, 'report'), patch.object(simple, 'task_once', side_effect=attempt):
            simple.run_schedule(self.run, self.state)
        self.assertEqual(seen, ['klebaner-04', 'gatheral-01', 'gatheral-02'])
        self.assertEqual(self.state['tasks'][0]['status'], 'truncation')
        self.assertEqual(self.state['status'], 'finished_with_gaps')

    def test_successful_gate_expands_and_resume_skips_completed(self):
        self.state['tasks'] = [{'id': k + '/convert', 'key': k, 'phase': 'convert', 'status': 'pending'}
                               for k in ('klebaner-04', 'gatheral-01', 'gatheral-02')]
        seen = []
        def attempt(run, state, task, client):
            seen.append(task['key']); task['status'] = 'complete_response'
        with patch.object(simple, 'verify'), patch.object(simple, 'report'), patch.object(simple, 'task_once', side_effect=attempt):
            simple.run_schedule(self.run, self.state); simple.run_schedule(self.run, self.state)
        self.assertEqual(seen, ['klebaner-04', 'gatheral-01', 'gatheral-02'])

    def test_pause_and_wall_limit_before_next_dispatch(self):
        (self.run / 'pause.json').write_text('{}')
        with patch.object(simple, 'task_once') as call:
            with self.assertRaises(runtime.StopRun): simple.run_schedule(self.run, self.state)
        call.assert_not_called(); (self.run / 'pause.json').unlink()
        self.state['first_dispatch'] = 1
        with patch.object(simple, 'task_once') as call:
            with self.assertRaises(runtime.StopRun): simple.run_schedule(self.run, self.state)
        call.assert_not_called()

    def test_new_files_do_not_change_historical_code_binding(self):
        self.assertNotIn('scripts/simple_chapter_glm.py', runtime.code_hashes())
        self.assertIn('scripts/simple_chapter_glm.py', simple.code_hashes())

    def test_actual_shared_invocation_saves_simple_request_and_identity(self):
        class FakeClient:
            model = protocol.MODEL
            def __init__(self, *args, **kwargs): pass
            def discover_model(self, out): return {'selected_model': self.model}
            def chapter_health(self, out):
                return {'context_length': 1048576, 'streams': {'decoding': 0, 'filling': 0}}, {}
            def chat(self, messages, out, label):
                return {'content': 'Complete final file', 'actual_model': self.model,
                        'finish_reason': 'stop', 'usage': {'completion_tokens': 10}}
        with patch.object(simple, 'compile_draft'):
            simple.task_once(self.run, self.state, self.task, FakeClient)
        saved = read_json(self.run / 'calls/call-001/request.json')
        self.assertEqual(saved, simple.request('Source with full paragraph'))
        self.assertEqual((self.run / 'calls/call-001/content.txt').read_text(), 'Complete final file')
        FakeClient.model = 'wrong-model'
        with self.assertRaises(runtime.Fatal):
            runtime.invoke(self.run, self.state, 'different-task', saved, client_factory=FakeClient)
        self.assertEqual(self.state['calls'][-1]['failure_kind'], 'identity')

    def test_resume_rejects_modified_inputs_and_outputs(self):
        atomic_json(self.run / 'inputs/manifest.json', files_manifest(self.run / 'inputs'))
        binding = {'code': simple.code_hashes(), 'inputs_manifest_sha256': sha(self.run / 'inputs/manifest.json')}
        atomic_json(self.run / 'binding.json', binding)
        self.state['binding_sha256'] = fingerprint(binding)
        runtime.save(self.run, self.state)
        simple.verify(self.run)
        source = self.run / 'inputs/test/source.tex'; original = source.read_text()
        source.write_text('changed input')
        with self.assertRaises(ValueError): simple.verify(self.run)
        source.write_text(original)
        output = self.run / 'saved.tex'; output.write_text('exact file')
        self.task.update(output='saved.tex', output_sha256=sha(output))
        runtime.save(self.run, self.state); simple.verify(self.run)
        output.write_text('tampered file')
        with self.assertRaises(runtime.Fatal): simple.verify(self.run)


class ChangedAllowanceTests(unittest.TestCase):
    def test_actual_http_serialization_carries_131072(self):
        from probe.local_model import LocalClient
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td); atomic_json(folder / 'record.json', {})
            client = LocalClient(protocol.BASE_URL, protocol.MODEL, purpose='chapter', max_tokens=131072, timeout=2700)
            client.model = protocol.MODEL
            response = {'model': protocol.MODEL, 'choices': [{'finish_reason': 'stop', 'message': {'content': 'Final TeX'}}], 'usage': {}}
            with patch.object(client, '_request', return_value=(response, {'attempt_dir': str(folder), 'http_status': 200})) as transport:
                client.chat(simple.request('Exact full source')['messages'], folder, 'chapter')
            payload = transport.call_args.args[2]
            self.assertEqual(payload, simple.request('Exact full source'))
            self.assertNotIn('reasoning_effort', payload)

    def test_transport_chapter_only_ceiling_and_timeout(self):
        from probe.local_model import LocalClient
        c = LocalClient(protocol.BASE_URL, protocol.MODEL, purpose='chapter', max_tokens=131072, timeout=2700)
        self.assertEqual(c.max_tokens, 131072)
        for purpose, maximum in [('text_critic', 32768), ('page_review', 16384), ('capability_probe', 4096), ('chapter', 131072)]:
            with self.assertRaises(ValueError): LocalClient(protocol.BASE_URL, purpose=purpose, max_tokens=maximum + 1)
        with self.assertRaises(ValueError): LocalClient(protocol.BASE_URL, purpose='chapter', timeout=2701)

    def test_context_admission_counts_entire_131k_output(self):
        q = simple.request('complete source')
        b = protocol.budget(q, 1048576)
        self.assertEqual(b['output_token_ceiling'], 131072)
        with self.assertRaises(ValueError): protocol.budget(q, b['combined_upper_estimate'] - 1)

    def test_linked_preparation_only_changes_allowance_and_keeps_accounting(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); parent = root / 'parent'; folder = parent / 'inputs/test'; folder.mkdir(parents=True)
            (folder / 'source.tex').write_text('Complete unchanged prose and $x$.')
            original = simple.request((folder / 'source.tex').read_text()); original['max_tokens'] = 32768
            atomic_json(folder / 'conversion-request.json', original)
            atomic_json(folder / 'budget.json', protocol.budget(original))
            atomic_json(parent / 'inputs/manifest.json', files_manifest(parent / 'inputs'))
            binding = {'code': {'historical': 'old'}, 'inputs_manifest_sha256': sha(parent / 'inputs/manifest.json')}
            atomic_json(parent / 'binding.json', binding)
            state = {'binding_sha256': fingerprint(binding), 'status': 'stopped', 'first_dispatch': time.time() - 100,
                     'calls': [{'id': 'call-001', 'parent': 'test/convert', 'status': 'failed'}], 'tasks': []}
            atomic_json(parent / 'state.json', state); before = files_manifest(parent)
            with patch.object(simple, 'KEYS', ['test']), patch.object(simple, 'POINTER', root / 'pointer.json'), \
                 patch.object(runtime.inputs, 'new_path', return_value=root / 'linked'):
                linked = simple.initialize_linked(parent)
            b, current = simple.verify(linked)
            self.assertEqual(current['first_dispatch'], state['first_dispatch'])
            self.assertEqual(len(current['calls']), 1)
            self.assertEqual(simple.own_calls(current), [])
            self.assertEqual(current['calls'][0]['inherited_from'], str(parent))
            self.assertNotEqual(current['calls'][0]['parent'], 'test/convert')
            new = read_json(linked / 'inputs/test/conversion-request.json')
            self.assertEqual(new['max_tokens'], 131072)
            new['max_tokens'] = original['max_tokens']; self.assertEqual(new, original)
            self.assertEqual((linked / 'inputs/test/source.tex').read_bytes(), (folder / 'source.tex').read_bytes())
            self.assertEqual(files_manifest(parent), before)
            reserved = runtime.reserve(current, 'readiness', 'hash')
            self.assertEqual(reserved['id'], 'call-002')
            self.assertEqual(current['first_dispatch'], state['first_dispatch'])
            atomic_json(parent / 'state.json', {**state, 'status': 'changed'})
            with self.assertRaises(runtime.Fatal): simple.verify(linked)

    def test_usage_observation_does_not_treat_http_success_as_honoured_cap(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td); folder = run / 'calls/call-001'; folder.mkdir(parents=True)
            atomic_json(folder / 'request.json', simple.request('source'))
            call = {'id': 'call-001', 'parent': 'chapter/convert', 'metadata': {'finish_reason': 'length',
                    'usage': {'completion_tokens': 32768, 'completion_tokens_details': {'reasoning_tokens': 32768}}}}
            result = simple.call_measurements(run, call)
            self.assertIn('before/different', result['allowance_observation'])
            self.assertEqual(result['non_reasoning_completion_tokens_derived'], 0)
            self.assertIsNone(result['final_answer_tokens_reported'])
            call['metadata']['usage']['completion_tokens'] = 131072
            self.assertEqual(simple.call_measurements(run, call)['allowance_observation'], 'reported requested ceiling reached')
            call['metadata'] = {'finish_reason': 'stop'}
            result = simple.call_measurements(run, call)
            self.assertIsNone(result['reasoning_tokens'])
            self.assertIn('does not prove', result['allowance_observation'])


DOCUMENT = '\\documentclass{book}\n\\begin{document}\nExact $x$ and prose.\n\\end{document}\n'


class EnvelopeRecoveryTests(unittest.TestCase):
    def test_surrounded_document_is_exact_slice_with_separate_notes(self):
        intro, notes = 'Here is the file.\n\n', '\nConversion notes: mathematical changes require review.\n'
        answer = intro + '```latex\n' + DOCUMENT + '```\n' + notes
        draft, record = simple.extract_document(answer)
        self.assertEqual(draft, DOCUMENT)
        self.assertEqual(answer[record['start']:record['end']], DOCUMENT)
        with tempfile.TemporaryDirectory() as td:
            run = Path(td); task = {}
            simple.save_conversion(run, task, answer, run / 'chapter')
            self.assertEqual((run / task['raw_answer']).read_text(), answer)
            self.assertEqual((run / task['notes']).read_text(), notes)
            self.assertEqual((run / 'chapter/introductory-prose.txt').read_text(), intro)
            self.assertEqual((run / task['output']).read_text(), DOCUMENT)
            self.assertEqual(task['status'], 'complete_response')

    def test_ambiguous_multiple_and_incomplete_envelopes_are_not_combined(self):
        for answer in ('```latex\n' + DOCUMENT,
                       'Intro\n```latex\nPartial text\n```\nNotes',
                       ('```latex\n' + DOCUMENT + '```\n') * 2,
                       '```tex\n' + DOCUMENT * 2 + '```\n',
                       DOCUMENT * 2,
                       DOCUMENT + '\n```latex\n' + DOCUMENT + '```\n'):
            with self.subTest(answer=answer[:30]):
                draft, record = simple.extract_document(answer)
                self.assertIsNone(draft); self.assertEqual(record['status'], 'ambiguous')
        self.assertEqual(simple.extract_document(DOCUMENT)[0], DOCUMENT)

    def test_comments_multiline_escaped_percent_and_unsafe_paths(self):
        source = r'\includegraphics{assets/one.jpg}' + '\n' + r'\includegraphics{assets/two.jpg}'
        output = ('\\includegraphics[width=\\linewidth]% comment\n {assets/one.jpg}\n'
                  '\\includegraphics\n [width=1cm]\n% another comment\n{\\detokenize{assets/two.jpg}}\n'
                  '% \\includegraphics{assets/not-used.jpg}\n'
                  '\\% literal percent \\includegraphics{../escape.jpg}')
        result = simple.document_observations(output, source, {'assets/one.jpg', 'assets/two.jpg'})
        self.assertEqual(result['source_assets_not_referenced'], [])
        self.assertEqual(result['references_without_supplied_asset'], ['../escape.jpg'])
        self.assertEqual(simple.without_comments('even\\\\%hidden\nnext'), 'even\\\\next')
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'image.jpg'; path.write_bytes(b'fixture')
            with self.assertRaises(ValueError): simple.tex_compile.stage_assets({'../escape.jpg': path})

    def test_saved_call006_exact_envelope_and_three_supplied_assets(self):
        parent = simple.ROOT / 'runs/simple-chapter-glm-trial-20261026T111637Z-634ede'
        raw = parent / 'calls/call-006/content.txt'
        if not raw.is_file(): self.skipTest('Optional local completed response unavailable')
        state = read_json(parent / 'state.json')
        call = next(c for c in state['calls'] if c['id'] == 'call-006')
        self.assertEqual(call['metadata']['finish_reason'], 'stop')
        answer = raw.read_text(); draft, extraction = simple.extract_document(answer)
        self.assertEqual(draft, answer.split('```latex\n', 1)[1].split('```', 1)[0])
        self.assertEqual(extraction['status'], 'single_fenced_document')
        self.assertEqual(len(simple.image_references(draft)), 3)
        source = parent / 'inputs/gatheral-01'
        observations = simple.document_observations(draft, (source / 'source.tex').read_text(), read_json(source / 'assets.json'))
        self.assertEqual(observations['source_assets_not_referenced'], [])
        self.assertEqual(observations['references_without_supplied_asset'], [])
        self.assertEqual(set(re.findall(r'\\tag\{([^}]+)\}', draft)), {f'1.{i}' for i in range(1, 13)})


class ContinuationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.parent = self.root / 'parent'
        self.keys = ['klebaner-04', 'gatheral-01', 'gatheral-02']
        for key in self.keys:
            folder = self.parent / 'inputs' / key; folder.mkdir(parents=True)
            (folder / 'source.tex').write_text('Exact source for ' + key)
            atomic_json(folder / 'conversion-request.json', simple.request((folder / 'source.tex').read_text()))
            atomic_json(folder / 'assets.json', [])
        atomic_json(self.parent / 'inputs/manifest.json', files_manifest(self.parent / 'inputs'))
        answer = 'Introduction\n```latex\n' + DOCUMENT + '```\nNotes retained.'
        folder = self.parent / 'calls/call-002'; folder.mkdir(parents=True)
        (folder / 'content.txt').write_text(answer)
        atomic_json(folder / 'manifest.json', files_manifest(folder))
        output = self.parent / 'chapters/gatheral-01/generated.tex'; output.parent.mkdir(parents=True); output.write_text(answer)
        binding = {'code': {'old': 'hash'}, 'inputs_manifest_sha256': sha(self.parent / 'inputs/manifest.json'),
                   'review_max_tokens': 32768, 'max_tokens': 131072}
        atomic_json(self.parent / 'binding.json', binding)
        self.state = {'binding_sha256': fingerprint(binding), 'status': 'stopped', 'first_dispatch': time.time() - 100,
                      'compile_unavailable': None, 'calls': [
            {'id': 'call-001', 'parent': 'klebaner-04/convert', 'status': 'failed', 'failure_kind': 'truncation'},
            {'id': 'call-002', 'parent': 'gatheral-01/convert', 'status': 'completed_response', 'seal': sha(folder / 'manifest.json'),
             'metadata': {'finish_reason': 'stop', 'actual_model': protocol.MODEL}}], 'tasks': [
            {'id': 'klebaner-04/convert', 'key': 'klebaner-04', 'phase': 'convert', 'status': 'truncation', 'call': 'call-001'},
            {'id': 'gatheral-01/convert', 'key': 'gatheral-01', 'phase': 'convert', 'status': 'complete_response', 'call': 'call-002',
             'output': str(output.relative_to(self.parent)), 'output_sha256': sha(output), 'compilation': {'status': 'syntax_failure'}},
            {'id': 'gatheral-02/convert', 'key': 'gatheral-02', 'phase': 'convert', 'status': 'pending'},
            {'id': 'klebaner-04/review', 'key': 'klebaner-04', 'phase': 'review', 'status': 'pending'},
            {'id': 'gatheral-01/review', 'key': 'gatheral-01', 'phase': 'review', 'status': 'pending'}]}
        atomic_json(self.parent / 'state.json', self.state)

    def prepare(self):
        with patch.object(simple, 'KEYS', self.keys), patch.object(simple, 'POINTER', self.root / 'pointer.json'), \
             patch.object(runtime.inputs, 'new_path', return_value=self.root / 'linked'), \
             patch.object(runtime, 'invoke', side_effect=AssertionError('No model call during preparation')):
            return simple.initialize_continuation(self.parent, 'call-002')

    def test_saved_recovery_inherits_calls_tasks_deadline_and_unchanged_inputs(self):
        before = files_manifest(self.parent); run = self.prepare(); binding, state = simple.verify(run)
        self.assertEqual(files_manifest(self.parent), before)
        self.assertEqual(files_manifest(run / 'inputs'), files_manifest(self.parent / 'inputs'))
        self.assertEqual(state['first_dispatch'], self.state['first_dispatch'])
        self.assertEqual(len(state['calls']), 2); self.assertEqual(simple.own_calls(state), [])
        self.assertEqual(state['tasks'][0]['status'], 'truncation')
        self.assertEqual(state['tasks'][3]['status'], 'unavailable')
        task = state['tasks'][1]
        self.assertEqual((run / task['output']).read_text(), DOCUMENT)
        self.assertEqual(task['compilation']['status'], 'not_attempted')
        seen = []
        def attempt(run, state, task, client):
            seen.append(task['id']); task['status'] = 'complete_response'
        with patch.object(simple, 'task_once', side_effect=attempt):
            simple.run_schedule(run, state); simple.run_schedule(run, state)
        self.assertEqual(seen, ['gatheral-02/convert', 'gatheral-01/review'])
        self.assertEqual(runtime.reserve(state, 'readiness', 'request')['id'], 'call-003')
        self.assertEqual(state['first_dispatch'], self.state['first_dispatch'])
        state['calls'] += [dict(state['calls'][0]) for _ in range(77)]
        with self.assertRaises(runtime.StopRun): runtime.reserve(state, 'readiness', 'request')

    def test_parent_or_recovery_tampering_and_expired_deadline_refused(self):
        self.state['first_dispatch'] = 1; atomic_json(self.parent / 'state.json', self.state)
        with self.assertRaisesRegex(ValueError, 'expired'): self.prepare()
        self.assertFalse((self.root / 'linked').exists())
        self.state['first_dispatch'] = time.time(); atomic_json(self.parent / 'state.json', self.state)
        run = self.prepare()
        notes = run / 'recovery/call-002/conversion-notes.md'; saved = notes.read_text(); notes.write_text('changed')
        with self.assertRaises(ValueError): simple.verify(run)
        notes.write_text(saved)
        atomic_json(self.parent / 'state.json', {**self.state, 'status': 'modified'})
        with self.assertRaises(runtime.Fatal): simple.verify(run)

    def test_truncated_call_cannot_be_recovered_or_replayed(self):
        call = self.state['calls'][1]; call['metadata']['finish_reason'] = 'length'
        atomic_json(self.parent / 'state.json', self.state)
        with self.assertRaisesRegex(ValueError, 'stop/identity'): self.prepare()
        self.assertFalse((self.root / 'linked').exists())

    def test_operator_compiles_recovery_separately_retaining_sandbox_failure(self):
        run = self.prepare(); _, state = simple.verify(run); task = state['tasks'][1]
        before = files_manifest(run / 'recovery'); parent = files_manifest(self.parent)
        with patch.object(simple.tex_compile, 'compile_document', side_effect=[
                {'status': 'unavailable', 'reason': 'Docker socket denied'}, {'status': 'passed', 'passes_completed': 2}]) as compiler, \
             patch.object(runtime, 'invoke', side_effect=AssertionError('No model call')):
            simple.compile_recovered(run, state)
            simple.compile_recovered(run, state)
            simple.compile_recovered(run, state)
        self.assertEqual(compiler.call_count, 2)
        self.assertNotEqual(compiler.call_args_list[0].args[1], compiler.call_args_list[1].args[1])
        self.assertEqual(compiler.call_args.kwargs['passes'], 2)
        self.assertEqual(task['compilation_history'][1]['status'], 'unavailable')
        self.assertEqual(task['compilation']['status'], 'passed')
        self.assertEqual(files_manifest(run / 'recovery'), before)
        self.assertEqual(files_manifest(self.parent), parent)
        self.assertEqual(len(state['calls']), 2)


class TwoPassCompilerTests(unittest.TestCase):
    def test_docker_permission_denial_returning_one_is_not_bad_tex(self):
        log = b'permission denied while trying to connect to the docker API at unix:///var/run/docker.sock\n'
        self.assertEqual(simple.tex_compile.classify_log(log.decode(), 1), 'unavailable')
        with tempfile.TemporaryDirectory() as td, patch.object(simple.tex_compile.shutil, 'which', return_value='/usr/bin/docker'):
            runner = unittest.mock.Mock(return_value=subprocess.CompletedProcess([], 1, log))
            result = simple.tex_compile.compile_document(DOCUMENT, Path(td) / 'out', image=protocol.IMAGE, runner=runner, passes=2)
            self.assertEqual(result['status'], 'unavailable'); self.assertFalse(result['compilation_claim'])
            self.assertEqual(result['passes_completed'], 0); runner.assert_called_once()

    def test_aux_reused_logs_preserved_and_time_is_shared(self):
        with tempfile.TemporaryDirectory() as td, patch.object(simple.tex_compile.shutil, 'which', return_value='/usr/bin/docker'):
            root = Path(td); calls = []
            def runner(cmd, **kw):
                build = Path(next(s.split('src=')[1].split(',dst=')[0] for s in cmd if s.endswith('dst=/work')))
                self.assertIn('--network=none', cmd); self.assertIn('-no-shell-escape', cmd)
                self.assertLessEqual(kw['timeout'], 90)
                if calls: self.assertEqual((build / 'document.aux').read_text(), 'retained auxiliary data')
                else: (build / 'document.aux').write_text('retained auxiliary data')
                calls.append(cmd)
                return subprocess.CompletedProcess(cmd, 0, b'undefined references' if len(calls) == 1 else b'Clean second pass')
            result = simple.tex_compile.compile_document(DOCUMENT, root / 'out', image=protocol.IMAGE, runner=runner, passes=2)
            self.assertEqual(result['passes_completed'], 2); self.assertEqual(result['status'], 'passed')
            self.assertEqual((root / 'out/pass-1/console.log').read_text(), 'undefined references')
            self.assertEqual((root / 'out/pass-2/console.log').read_text(), 'Clean second pass')

    def test_no_second_pass_on_failure_and_no_claim_if_second_fails(self):
        for returncodes in ([1], [0, 125]):
            with tempfile.TemporaryDirectory() as td, patch.object(simple.tex_compile.shutil, 'which', return_value='/usr/bin/docker'):
                runner = unittest.mock.Mock(side_effect=[subprocess.CompletedProcess([], rc, b'failed') for rc in returncodes])
                result = simple.tex_compile.compile_document(DOCUMENT, Path(td) / 'out', image=protocol.IMAGE, runner=runner, passes=2)
                self.assertEqual(runner.call_count, len(returncodes)); self.assertFalse(result['compilation_claim'])
        for count in (0, 3, True):
            with self.assertRaises(ValueError): simple.tex_compile.compile_document(DOCUMENT, '/unused', passes=count)


if __name__ == '__main__': unittest.main()
