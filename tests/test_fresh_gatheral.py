"""Fresh Gatheral scheduling/cache reuse; no models, services or real compilation."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fitz
from probe import chapter_sources as sources
from probe.common import atomic_json, read_json, sha, files_manifest, fingerprint
from scripts import simple_chapter_glm as simple
from test_simple_chapter_glm import block


class FreshGatheralTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.native = self.root/'native'; self.cache = self.root/'cache'
        self.native.mkdir(); self.cache.mkdir()
        self.pdf = self.root/'source.pdf'
        with fitz.open() as doc:
            for n in range(1, 211):
                page = doc.new_page(); page.insert_text((40, 60), f'Native page {n}\n5\nReference locator')
            doc.save(self.pdf)
        atomic_json(self.root/'docs/source-provenance/gatheral-intake-20261025.json',
                    {'path': str(self.pdf), 'sha256': sha(self.pdf), 'pages': 210})
        parts = []
        for part, title, first, last in simple.runtime.inputs.PARTS:
            key = 'gatheral-'+part; pages = []; blocks = []
            for n in range(first, last+1):
                b = block(key+f':b{n}', f'Complete primary prose {n}.', page=n)
                b['page']['original_physical_page'] = n
                blocks.append(b); pages.append({'page_id': f'gatheral-p{n:04d}', 'page': b['page']})
            data = {'source': 'gatheral', 'pages': pages, 'blocks': blocks}
            atomic_json(self.native/'chapters'/key/'source.json', data)
            atomic_json(self.native/'chapters'/key/'inventory.json', {'title': title})
            parts.append({'source': 'gatheral', 'pages': list(range(first, last+1))})
            if key in simple.GATHERAL_KEYS[:11]:
                folder = self.cache/'inputs'/key
                atomic_json(folder/'native.json', data)
                atomic_json(folder/'provenance.json', {'original_pages': list(range(first, last+1))})
        atomic_json(self.native/'inputs.json', {'parts': parts})
        atomic_json(self.native/'manifest.json', files_manifest(self.native))
        sources.prepare_secondary(self.cache, self.root, simple.GATHERAL_KEYS[:11])
        atomic_json(self.cache/'inputs/manifest.json', files_manifest(self.cache/'inputs'))
        binding = {'inputs_manifest_sha256': sha(self.cache/'inputs/manifest.json')}
        atomic_json(self.cache/'binding.json', binding)
        atomic_json(self.cache/'state.json', {'binding_sha256': fingerprint(binding),
                    'status': 'prepared_linked_offline', 'first_dispatch': 123,
                    'calls': [{'id': f'old-{i}', 'status': 'completed_response'} for i in range(11)],
                    'tasks': [{'id': 'gatheral-03/convert', 'status': 'truncation'}]})

    def prepare(self):
        return simple.initialize(self.native, fresh_gatheral_from=self.cache)

    def test_fresh_scope_pair_order_cache_reuse_and_history_preserved(self):
        # Native PDF text may contain CRLF. Text-mode newline normalization must
        # not cause a false cache-integrity failure or rewrite the original cache.
        cached = self.cache/'inputs'/simple.GATHERAL_KEYS[0]
        record = read_json(cached/'secondary.json'); record['pages'][0]['text'] += 'Native\r\nline ending\r'
        (cached/'secondary.txt').write_bytes(sources.render_pages(record['pages']).encode('utf-8'))
        record['text_sha256'] = sha(cached/'secondary.txt'); atomic_json(cached/'secondary.json', record)
        (self.cache/'inputs/manifest.json').unlink()
        atomic_json(self.cache/'inputs/manifest.json', files_manifest(self.cache/'inputs'))
        binding = read_json(self.cache/'binding.json'); binding['inputs_manifest_sha256'] = sha(self.cache/'inputs/manifest.json')
        atomic_json(self.cache/'binding.json', binding)
        previous = read_json(self.cache/'state.json'); previous['binding_sha256'] = fingerprint(binding)
        atomic_json(self.cache/'state.json', previous)
        baseline = files_manifest(self.cache); run = self.root/'new-run'
        with patch.object(simple, 'ROOT', self.root), patch.object(simple, 'POINTER', self.root/'pointer.json'), \
             patch.object(simple.runtime.inputs, 'new_path', return_value=run), \
             patch.object(simple, 'code_hashes', return_value={'test': 'binding'}), \
             patch.object(sources, 'extract_pages', wraps=sources.extract_pages) as extraction:
            self.assertEqual(self.prepare(), run)
            binding, state = simple.verify(run)
            extracted = [r['physical_pdf_page'] for call in extraction.call_args_list for r in call.args[1]]
            self.assertEqual(extracted, list(range(193, 199)))
            self.assertEqual(binding['scope']['physical_pdf_pages'], list(range(32, 199)))
            excluded = [n for p in binding['scope']['excluded_parts'] for n in p['physical_pdf_pages']]
            self.assertEqual(sorted(excluded + binding['scope']['physical_pdf_pages']), list(range(1, 211)))
            self.assertFalse(binding['scope']['whole_book']); self.assertIsNone(binding['gate'])
            self.assertEqual(binding['previous_experiment_calls'], 11)
            self.assertEqual(state['calls'], []); self.assertIsNone(state['first_dispatch'])
            self.assertEqual(state['accuracy'], {}); self.assertEqual(state['timing_policy'], 'manual_only')
            self.assertIsNone(binding['request_timeout']); self.assertEqual(binding['connection_timeout'], 10)
            expected = [k+'/'+phase for k in simple.GATHERAL_KEYS for phase in ('convert', 'review')]
            self.assertEqual([t['id'] for t in state['tasks']], expected)
            self.assertTrue(all(t['status'] == 'pending' for t in state['tasks']))
            self.assertEqual(set(state['versions']), set(simple.GATHERAL_KEYS))
            self.assertTrue(all(list(v) == ['mineru'] for v in state['versions'].values()))
            for key in simple.GATHERAL_KEYS:
                folder = run/'inputs'/key; body = read_json(folder/'conversion-request.json')
                self.assertEqual(body, sources.request((folder/'source.tex').read_text(), (folder/'secondary.txt').read_text()))
                self.assertEqual(body['max_tokens'], 131072); self.assertTrue(body['stream'])
                self.assertFalse((folder/'review-request.json').exists())  # No invented future draft.
                if key in simple.GATHERAL_KEYS[:11]:
                    for name in ('secondary.txt', 'secondary.json'):
                        self.assertEqual((folder/name).read_bytes(), (self.cache/'inputs'/key/name).read_bytes())
            self.assertEqual(files_manifest(self.cache), baseline)
            state['tasks'].reverse(); simple.runtime.save(run, state)
            with self.assertRaisesRegex(simple.runtime.Fatal, 'scope/order'): simple.verify(run)

    def test_wrong_cache_page_binding_rejected(self):
        key = simple.GATHERAL_KEYS[0]; folder = self.cache/'inputs'/key
        data = read_json(folder/'secondary.json'); data['pages'][0]['physical_pdf_page'] += 1
        atomic_json(folder/'secondary.json', data)
        with self.assertRaisesRegex(ValueError, 'cache source/page/text mismatch'):
            sources.prepare_secondary(self.cache, self.root, [key], cache_run=self.cache)

    def test_first_chapter_failure_is_local_and_does_not_reinstate_gate(self):
        tasks = [{'id': k+'/'+p, 'key': k, 'phase': p, 'status': 'pending'}
                 for k in simple.GATHERAL_KEYS for p in ('convert', 'review')]
        state = {'timing_policy': 'manual_only', 'schedule_policy': simple.FRESH_SCHEDULE,
                 'first_dispatch': None, 'calls': [], 'tasks': tasks}
        visited = []
        def execute(run, state, task, factory):
            visited.append(task['id'])
            task['status'] = ('truncation' if task['id'] == 'gatheral-01/convert' else
                              'unavailable' if task['id'] == 'gatheral-01/review' else 'complete_response')
        with patch.object(simple, 'verify'), patch.object(simple, 'report'), patch.object(simple, 'task_once', side_effect=execute):
            simple.run_schedule(self.root, state)
        self.assertEqual(visited, [t['id'] for t in tasks]); self.assertEqual(state['status'], 'finished_with_gaps')


if __name__ == '__main__': unittest.main()
