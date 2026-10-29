"""Offline checks for manual timing, durable streaming, versions and dependencies."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from probe.chapter_stream import ChapterStream
from probe.local_model import LocalClient, ProbeError, _strict_json
from probe import chapter_glm as runtime, chapter_protocol as protocol, compiler_environment as compiler
from probe.common import atomic_json, files_manifest, fingerprint, read_json, sha
from scripts import simple_chapter_glm as simple

DOC = '\\documentclass{article}\n\\begin{document}\nExact $x^2$ and prose.\n\\end{document}\n'


def event(delta=None, finish=None, model=protocol.MODEL, usage=None):
    value = {'model': model, 'choices': [{'index': 0, 'delta': delta or {}, 'finish_reason': finish}]}
    if usage is not None: value['usage'] = usage
    return ('data: ' + json.dumps(value, ensure_ascii=False) + '\n\n').encode()


class FakeResponse:
    status = 200
    def __init__(self, parts, content_type='text/event-stream'): self.parts = iter(parts); self.content_type = content_type
    def getheaders(self): return [('Content-Type', self.content_type)]
    def getheader(self, name): return self.content_type if name.lower() == 'content-type' else None
    def read1(self, count):
        part = next(self.parts, b'')
        if isinstance(part, Exception): raise part
        return part


class FakeConnection:
    def __init__(self, response): self.response = response; self.sock = Mock(); self.sent = None
    def connect(self): pass
    def request(self, method, path, body, headers): self.sent = json.loads(body)
    def getresponse(self): return self.response
    def close(self): pass


class StreamingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_durable_reasoning_answer_and_wire_before_completion(self):
        s = ChapterStream(self.root, protocol.MODEL, _strict_json)
        raw = event({'reasoning_content': 'Reason λ.'})
        for byte in raw: s.feed(bytes([byte]))
        self.assertEqual((self.root / 'response.raw').read_bytes(), raw)
        self.assertEqual((self.root / 'reasoning.txt').read_text(), 'Reason λ.')
        with self.assertRaises(ValueError): s.response()
        s.feed(event({'content': 'Final.'}) + event(finish='stop', usage={'completion_tokens': 7}) + b'data: [DONE]\n\n')
        self.assertEqual(s.response()['choices'][0]['message']['content'], 'Final.')
        s.close(); self.assertEqual(read_json(self.root / 'response.assembled.json')['usage'], {'completion_tokens': 7})
        self.assertTrue((self.root / 'stream-events.jsonl').read_text())

    def test_incomplete_malformed_wrong_identity_tools_and_multiple_choices_rejected(self):
        cases = [event({'content': 'partial'}), event({'content': 'partial'}) + b'data: {bad}\n\n',
                 event({'content': 'wrong'}, model='different'), event({'tool_calls': [{'id': 'x'}]}),
                 b'data: {"choices":[{},{}]}\n\n']
        for i, raw in enumerate(cases):
            folder = self.root / str(i); folder.mkdir(); s = ChapterStream(folder, protocol.MODEL, _strict_json)
            with self.assertRaises(ValueError): s.feed(raw); s.response()
            s.close(); self.assertEqual((folder / 'response.raw').read_bytes(), raw)

    def test_split_credential_redacted_in_all_evidence(self):
        key = 'fake-private-key-for-test'
        s = ChapterStream(self.root, protocol.MODEL, _strict_json, key)
        raw = event({'reasoning_content': key}) + event({'content': key}, finish='stop') + b'data: [DONE]\n\n'
        for i in range(0, len(raw), 3): s.feed(raw[i:i+3])
        s.close()
        for p in self.root.iterdir(): self.assertNotIn(key.encode(), p.read_bytes())

    def client(self, response, **kwargs):
        c = LocalClient(protocol.BASE_URL, protocol.MODEL, purpose='simple_chapter', timeout=None,
                        max_tokens=131072, max_response_bytes=256*1024*1024, **kwargs)
        c.model = protocol.MODEL; connection = FakeConnection(response)
        c._connection = lambda: (connection, urlsplit(protocol.BASE_URL))
        return c, connection

    def test_actual_transport_stream_serialization_has_no_generation_timer(self):
        raw = event({'reasoning_content': 'Work'}) + event({'content': 'CHAPTER_READY'}, finish='stop', usage={'completion_tokens': 8}) + b'data: [DONE]\n\n'
        c, connection = self.client(FakeResponse([raw[:49], raw[49:]]))
        with patch('probe.local_model.threading.Timer', side_effect=AssertionError('No generation timer')):
            result = c.chat([{'role': 'user', 'content': 'Exact input'}], self.root, 'chapter', stream=True)
        self.assertEqual(connection.sent, {'model': protocol.MODEL, 'max_tokens': 131072, 'stream': True,
                                         'messages': [{'role': 'user', 'content': 'Exact input'}]})
        connection.sock.settimeout.assert_called_with(None)
        self.assertEqual(result['content'], 'CHAPTER_READY')
        record = read_json(Path(result['attempt_dir']) / 'record.json')
        self.assertIsNone(record['generation_deadline_seconds']); self.assertTrue(record['stream_done'])
        self.assertEqual(record['connection_timeout_seconds'], 10)

    def test_truncation_retains_reasoning_and_partial_final_and_usage(self):
        raw = event({'reasoning_content': 'Work', 'content': 'Partial'}, finish='length',
                    usage={'completion_tokens': 131072}) + b'data: [DONE]\n\n'
        c, _ = self.client(FakeResponse([raw]))
        with self.assertRaises(ProbeError) as failed: c.chat([], self.root, 'chapter', stream=True)
        folder = Path(failed.exception.attempt_dir)
        self.assertEqual((folder / 'answer.txt').read_text(), 'Partial')
        self.assertEqual((folder / 'reasoning.txt').read_text(), 'Work')
        record = read_json(folder / 'record.json'); self.assertEqual(record['finish_reason'], 'length')
        self.assertEqual(runtime.classify_failure(record, str(failed.exception)), 'truncation')

    def test_disconnect_preserves_partial_wire_without_completion_credit(self):
        raw = event({'reasoning_content': 'Work before disconnect'})
        c, _ = self.client(FakeResponse([raw, ConnectionResetError('connection reset')]))
        with self.assertRaises(ProbeError) as failed: c.chat([], self.root, 'chapter', stream=True)
        folder = Path(failed.exception.attempt_dir)
        self.assertEqual((folder / 'response.raw').read_bytes(), raw)
        self.assertEqual((folder / 'reasoning.txt').read_text(), 'Work before disconnect')
        self.assertEqual(read_json(folder / 'record.json')['status'], 'failed')
        self.assertEqual(runtime.classify_failure(read_json(folder / 'record.json'), str(failed.exception)), 'connection')

    def test_clean_eof_without_done_is_connection_failure_not_success(self):
        c, _ = self.client(FakeResponse([event({'content': 'Incomplete'})]))
        with self.assertRaises(ProbeError) as failed: c.chat([], self.root, 'chapter', stream=True)
        record = read_json(Path(failed.exception.attempt_dir) / 'record.json')
        self.assertEqual(runtime.classify_failure(record, str(failed.exception)), 'connection')
        self.assertFalse(record['stream_done'])

    def test_manual_stop_is_not_a_generation_timeout(self):
        stop = [False]
        response = FakeResponse([event({'reasoning_content': 'Work'})])
        original = response.read1
        def read(count):
            value = original(count); stop[0] = True; return value
        response.read1 = read
        c, _ = self.client(response, stop_requested=lambda: stop[0])
        with self.assertRaises(ProbeError) as failed: c.chat([], self.root, 'chapter', stream=True)
        record = read_json(Path(failed.exception.attempt_dir) / 'record.json')
        self.assertEqual(runtime.classify_failure(record, str(failed.exception)), 'operator_stop')
        self.assertEqual((Path(failed.exception.attempt_dir) / 'reasoning.txt').read_text(), 'Work')

    def test_non_stream_reply_is_preserved_and_refused_before_expensive_work(self):
        raw = b'{"unexpected":"ordinary JSON"}'
        c, _ = self.client(FakeResponse([raw], 'application/json'))
        with self.assertRaisesRegex(ProbeError, 'did not return text/event-stream') as failed:
            c.chat([], self.root, 'chapter', stream=True)
        self.assertEqual((Path(failed.exception.attempt_dir) / 'response.raw').read_bytes(), raw)

    def test_legacy_generation_deadlines_remain_and_connect_failures_are_distinct(self):
        for purpose in ('chapter', 'text_critic', 'page_review'):
            with self.assertRaises(ValueError): LocalClient(protocol.BASE_URL, purpose=purpose, timeout=None)
        c, connection = self.client(FakeResponse([])); connection.connect = Mock(side_effect=TimeoutError('timed out'))
        with self.assertRaises(ProbeError) as failed: c.chat([], self.root, 'chapter', stream=True)
        record = read_json(Path(failed.exception.attempt_dir) / 'record.json')
        self.assertEqual(runtime.classify_failure(record, str(failed.exception)), 'connection_timeout')


class ContinuousWorkflowTests(unittest.TestCase):
    def test_old_elapsed_time_does_not_cut_new_policy_or_reset_calls(self):
        state = {'first_dispatch': 1, 'calls': [], 'timing_policy': 'manual_only'}
        self.assertEqual(runtime.remaining(state), float('inf'))
        self.assertEqual(runtime.reserve(state, 'readiness', 'hash')['id'], 'call-001')
        self.assertEqual(state['first_dispatch'], 1)
        state['calls'] = [dict(state['calls'][0]) for _ in range(80)]
        with self.assertRaises(runtime.StopRun): runtime.reserve(state, 'readiness', 'hash')
        state.pop('timing_policy'); state['calls'] = []
        with self.assertRaises(runtime.StopRun): runtime.reserve(state, 'readiness', 'hash')

    def test_existing_reviews_first_then_every_new_conversion_immediately_reviewed(self):
        tasks = [{'id': k+'/'+p, 'key': k, 'phase': p, 'status': 'pending'} for k in simple.KEYS for p in ('convert','review')]
        for t in tasks:
            if t['phase']=='convert' and t['key'] in ('gatheral-01','gatheral-02','gatheral-04'):t['status']='complete_response'
            if t['phase']=='convert' and t['key'] in ('klebaner-04','gatheral-03','gatheral-05'):t['status']='truncation'
        ordered = simple.review_order(tasks); pending=[t['id'] for t in ordered if t['status']=='pending']
        self.assertEqual(pending[:3],['gatheral-01/review','gatheral-02/review','gatheral-04/review'])
        self.assertEqual(pending[3:7],['gatheral-06/convert','gatheral-06/review','gatheral-07/convert','gatheral-07/review'])
        self.assertEqual(len({t['id'] for t in ordered}),len(tasks))

    def test_critic_has_both_exact_inputs_full_allowance_and_unchanged_prompt(self):
        legacy = simple.request('exact source','exact draft'); current=simple.continuous_request('exact source','exact draft')
        self.assertEqual(current['messages'],legacy['messages']);self.assertEqual(current['max_tokens'],131072)
        self.assertTrue(current['stream']);self.assertNotIn('reasoning_effort',current)

    def test_versions_never_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);state={}
            a=simple.remember_version(run,state,'ch','first-glm',DOC)
            b=simple.remember_version(run,state,'ch','critic-revised-call-002',DOC+'% proposed\n')
            self.assertNotEqual(a['path'],b['path']);self.assertEqual((run/a['path']).read_text(),DOC)
            with self.assertRaises(runtime.Fatal):simple.remember_version(run,state,'ch','first-glm','changed')

    def test_review_records_findings_only_or_separate_unaccepted_revision(self):
        for response, expected in [('A suspected missing condition; no replacement supplied.','not_supplied'),
                                   ('Findings.\n```latex\n'+DOC+'```\nNotes.','supplied_unaccepted')]:
            with tempfile.TemporaryDirectory() as td:
                run=Path(td);(run/'inputs/ch').mkdir(parents=True);(run/'inputs/ch/source.tex').write_text('source')
                (run/'first.tex').write_text(DOC)
                conversion={'id':'ch/convert','phase':'convert','key':'ch','status':'complete_response','output':'first.tex'}
                review={'id':'ch/review','phase':'review','key':'ch','status':'pending'}
                state={'tasks':[conversion,review],'calls':[],'timing_policy':'manual_only','connection_failures':0}
                def invoke(*args,**kwargs):return response,{'id':'call-001'}
                with patch.object(simple,'compile_version',return_value={'status':'passed'}),patch.object(runtime,'invoke',side_effect=invoke):
                    simple.task_once(run,state,review)
                self.assertEqual(review['revised_tex']['status'],expected)
                self.assertEqual((run/'first.tex').read_text(),DOC)
                self.assertEqual((run/review['output']).read_text(),response)

    def test_linked_policy_inherits_completed_versions_and_history_without_replay(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);parent=root/'parent';keys=['gatheral-01','gatheral-02']
            tasks=[]
            for key in keys:
                folder=parent/'inputs'/key;folder.mkdir(parents=True)
                (folder/'source.tex').write_text('Exact source for '+key)
                atomic_json(folder/'assets.json',[]);atomic_json(folder/'conversion-request.json',simple.request((folder/'source.tex').read_text()))
                path=parent/'chapters'/key/'generated.tex';path.parent.mkdir(parents=True);path.write_text(DOC)
                tasks += [{'id':key+'/convert','key':key,'phase':'convert','status':'complete_response','output':str(path.relative_to(parent)),'output_sha256':sha(path)},
                          {'id':key+'/review','key':key,'phase':'review','status':'pending'}]
            atomic_json(parent/'inputs/manifest.json',files_manifest(parent/'inputs'))
            binding={'code':{'historical':'hash'},'inputs_manifest_sha256':sha(parent/'inputs/manifest.json')}
            atomic_json(parent/'binding.json',binding)
            state={'binding_sha256':fingerprint(binding),'first_dispatch':1,'status':'stopped','tasks':tasks,
                   'calls':[{'id':'call-001','parent':'gatheral-01/convert','status':'completed_response'}]}
            atomic_json(parent/'state.json',state);before=files_manifest(parent)
            with patch.object(simple,'KEYS',keys),patch.object(simple,'POINTER',root/'pointer.json'),patch.object(runtime.inputs,'new_path',return_value=root/'new'),patch.object(runtime,'invoke',side_effect=AssertionError('No inference')):
                run=simple.initialize_policy_continuation(parent)
            b,s=simple.verify(run);self.assertEqual(s['first_dispatch'],1);self.assertEqual(len(s['calls']),1)
            self.assertEqual(s['timing_policy'],'manual_only');self.assertEqual(s['tasks'][0]['id'],'gatheral-01/review')
            self.assertEqual(files_manifest(parent),before)
            self.assertEqual((run/s['versions']['gatheral-01']['first-glm']['path']).read_text(),DOC)
            s['timing_policy']='legacy';atomic_json(run/'state.json',s)
            with self.assertRaises(runtime.Fatal):simple.verify(run)


class CompilerEnvironmentTests(unittest.TestCase):
    def test_identifiable_dependencies_do_not_include_assets_or_unknown_commands(self):
        for name,package in [('enumitem.sty','texlive-latex-extra'),('lmodern.sty','lmodern')]:
            self.assertEqual(compiler.missing_dependency("LaTeX Error: File `"+name+"' not found.")['approved_debian_package'],package)
        for name in ('missing.jpg','../../secret.sty','custom.sty'):
            self.assertIsNone(compiler.missing_dependency("LaTeX Error: File `"+name+"' not found.")['approved_debian_package'])
        self.assertIsNone(compiler.missing_dependency('Missing $ inserted'))

    def test_saved_tex_dependency_recovery_is_bounded_and_syntax_is_not_environment_repair(self):
        for message, expected in [("LaTeX Error: File `enumitem.sty' not found.",2),('Missing $ inserted',1),
                                  ("LaTeX Error: File `plot.jpg' not found.",1)]:
            with tempfile.TemporaryDirectory() as td:
                run=Path(td);env=run/'env';env.mkdir();atomic_json(env/'manifest.json',files_manifest(env))
                state={'compiler_environment':{'image':'sha256:'+'a'*64,'packages':['texlive-latex-base'],'path':'env','seal':sha(env/'manifest.json')}}
                calls=[]
                def compile_doc(doc,out,**kwargs):
                    calls.append((doc,kwargs));out.mkdir(parents=True);(out/'console.log').write_text(message)
                    return {'status':'missing_package_or_asset' if 'LaTeX Error' in message else 'syntax_failure'}
                provision=Mock(return_value='sha256:'+'b'*64)
                result=compiler.compile_saved(run,state,run,DOC,run/'compile',{},compiler=compile_doc,provision=provision)
                self.assertEqual(len(calls),expected);self.assertTrue(all(doc==DOC for doc,_ in calls))
                self.assertEqual(provision.call_count,expected-1);self.assertFalse(result['model_repair_requested'])

    def test_provisioning_context_contains_no_document_or_credentials_and_requires_qualification(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);state={}
            def runner(cmd,**kwargs):
                context=Path(cmd[-1]);self.assertEqual([p.name for p in context.iterdir()],['Dockerfile'])
                self.assertIn('lmodern',cmd[cmd.index('--build-arg')+1]);self.assertNotIn('--privileged',cmd)
                Path(cmd[cmd.index('--iidfile')+1]).write_text('sha256:'+'a'*64)
                return subprocess.CompletedProcess(cmd,0)
            with patch.object(compiler.tex_compile,'compile_document',return_value={'status':'passed','compilation_claim':True}) as qualified:
                image=compiler.ensure(run,state,simple.ROOT,runner=runner)
            self.assertEqual(image,'sha256:'+'a'*64);self.assertEqual(qualified.call_args.kwargs['passes'],2)
            self.assertIn('parts/check.tex',qualified.call_args.kwargs['assets'])
            with self.assertRaises(ValueError):compiler.ensure(run,state,simple.ROOT,extra=('unapproved-shell-command',))


if __name__ == '__main__':unittest.main()
