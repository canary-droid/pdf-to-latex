"""Real finalization and saved-response recovery, with no model/compiler calls."""
import ast
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from probe import chapter_concurrency as concurrent, chapter_glm as runtime, speed_suite as suite
from probe.common import atomic_json, files_manifest, fingerprint, read_json, sha
from scripts import speed_suite as ctrl, overnight_suite as prep
from test_overnight_suite import overnight
from test_speed_suite import BODY, DOC, health

book=ctrl.book
SAVED=ctrl.ROOT/'runs/overnight-suite-20261029T233239Z-708fe8'
FIXTURE=Path(__file__).parent/'fixtures/overnight-findings-only'


def setup_finalization(run,answer,*,task=None,source=DOC,draft=DOC,call_id='call-005'):
    task=copy.deepcopy(task) if task else {'id':'a/critic','key':'a','source_key':'bergomi-01','phase':'critic','section':None,'draft_label':'saved-control-draft'}
    task.update(status='running',call=call_id)
    state={'tasks':[task],'calls':[],'accuracy':{},'accuracy_records':{},'current_versions':{},'versions':{},'connection_failures':0}
    key=task['key'];v=book.remember(run,state,key,'saved-control-draft',draft,{'source':'saved input'})
    task['expected_draft_sha256']=v['sha256'];state['current_versions'][key]='saved-control-draft'
    f=ctrl.source_folder(run,task['source_key']);f.mkdir(parents=True)
    (f/'source.tex').write_text(source);atomic_json(f/'assets.json',[])
    body=copy.deepcopy(BODY);body['messages'][0]['content']='Review the exact draft:\n'+draft
    c={'id':call_id,'parent':task['id'],'request_sha256':fingerprint(body),'status':'completed_response',
       'metadata':{'actual_model':'glm53-regular','finish_reason':'stop'}}
    d=run/'calls'/call_id;atomic_json(d/'request.json',body);(d/'answer.txt').write_text(answer)
    atomic_json(d/'outcome.json',c);atomic_json(d/'manifest.json',files_manifest(d));c['seal']=sha(d/'manifest.json')
    state['calls'].append(c)
    return state,task,c


class FinalizationTests(unittest.TestCase):
    def test_real_saved_findings_fences_partial_complete_and_ambiguous(self):
        answer=(FIXTURE/'answer.txt').read_text()
        self.assertEqual(sha(FIXTURE/'answer.txt'),read_json(FIXTURE/'provenance.json')['sha256'])
        for text,expected in ((answer,'critic_unchanged'),('```markdown\n'+answer+'\n```','critic_unchanged'),
             (r'\documentclass{article}\begin{document}Partial revision','critic_revision_unusable'),
             ('```latex\n'+DOC+'\n```\n## Accuracy notes\nUnresolved source reference.','critic_revised'),
             ('```latex\n'+DOC+'\n```\n```latex\n'+DOC+'\n```','critic_revision_unusable')):
            with self.subTest(result=expected,text=text[:45]),tempfile.TemporaryDirectory() as td:
                r=Path(td);s,t,c=setup_finalization(r,text);original=(r/s['versions']['a']['saved-control-draft']['path']).read_bytes();compiled=[]
                def compile_version(run,state,key,label):
                    self.assertIn(label,state['versions'][key]);self.assertTrue(book.chapter_accuracy.complete_document(book.bound_output(run,state,key,label)))
                    compiled.append(label)
                with patch.object(book,'compile_version',side_effect=compile_version):book.finish_task(r,s,t,text,c)
                self.assertEqual(t['status'],expected)
                self.assertEqual((r/s['versions']['a']['saved-control-draft']['path']).read_bytes(),original)
                self.assertEqual('critic-call-005' in s['versions']['a'],expected=='critic_revised')
                self.assertEqual('critic-call-005' in compiled,expected=='critic_revised')
                self.assertIn(s['current_versions']['a'],compiled)
                self.assertTrue((r/s['accuracy_records']['a']).is_file())
                self.assertEqual((r/'calls/call-005/answer.txt').read_text(),text)

    def test_partial_finalization_recovery_is_idempotent_and_integrity_checked(self):
        answer=(FIXTURE/'answer.txt').read_text()
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,t,c=setup_finalization(r,answer)
            # Reproduce a failure after the immutable annotation was already saved.
            with patch.object(book,'compile_version',side_effect=KeyError('critic-call-005')):
                with self.assertRaises(KeyError):book.finish_task(r,s,t,answer,c)
            t.update(status='coordinator_failure',error="KeyError: 'critic-call-005'")
            before={p['path']:p['sha256'] for p in files_manifest(r)}
            with patch.object(runtime,'invoke',side_effect=AssertionError('no inference')):
                rec=prep.reconcile_findings_only(r,s,t,c);first=files_manifest(r);snapshot=copy.deepcopy(s)
                self.assertEqual(prep.reconcile_findings_only(r,s,t,c),rec)
                self.assertEqual(files_manifest(r),first);self.assertEqual(s,snapshot)
            self.assertEqual(t['status'],'critic_unchanged');self.assertFalse(rec['model_replacement'])
            self.assertEqual(rec['historical_status'],'coordinator_failure');self.assertNotIn('critic-call-005',s['versions']['a'])
            for p,h in before.items():self.assertEqual(sha(r/p),h)
            with patch.object(book,'compile_version') as compiler:
                prep.compile_local_recoveries(r,s)
                compiler.assert_called_once_with(r,s,'a','critic-call-005-annotated')
            selected=s['versions']['a']['critic-call-005-annotated']
            selected['compilation']={'status':'passed'}
            with patch.object(book,'compile_version',side_effect=AssertionError('no repeat compile')):prep.compile_local_recoveries(r,s)
            (r/selected['path']).write_text('changed')
            with self.assertRaises(runtime.Fatal):prep.reconcile_findings_only(r,s,t,c)

    @unittest.skipUnless((SAVED/'state.json').exists(),'Optional local saved six-response audit fixture unavailable')
    def test_all_six_actual_saved_responses_through_real_finalization(self):
        old=read_json(SAVED/'state.json');counts={};source_hashes={}
        for task in suite.stage_tasks(old,1):
            c=next(c for c in old['calls'] if c['id']==task['call']);path=SAVED/'calls'/c['id']/'answer.txt'
            source_hashes[path]=sha(path);answer=path.read_text()
            original=SAVED/old['versions'][task['key']]['saved-control-draft']['path'];source_hashes[original]=sha(original)
            with self.subTest(call=c['id']),tempfile.TemporaryDirectory() as td:
                r=Path(td);s,t,call=setup_finalization(r,answer,task=task,draft=original.read_text(),call_id=c['id'],
                    source=(ctrl.source_folder(SAVED,task['source_key'])/'source.tex').read_text())
                def checked_compile(run,state,key,label):self.assertIn(label,state['versions'][key])
                with patch.object(book,'compile_version',side_effect=checked_compile),patch.object(runtime,'invoke',side_effect=AssertionError('no model')):
                    book.finish_task(r,s,t,answer,call)
                expected='critic_unchanged' if c['id']=='call-005' else 'critic_revised'
                self.assertEqual(t['status'],expected);counts[expected]=counts.get(expected,0)+1
                self.assertEqual(sha(r/s['versions'][t['key']]['saved-control-draft']['path']),source_hashes[original])
        self.assertEqual(counts,{'critic_revised':5,'critic_unchanged':1})
        for p,h in source_hashes.items():self.assertEqual(sha(p),h)


class CachedRendererTests(unittest.TestCase):
    def test_actual_fallback_inspects_unwrapped_source_and_renders_cached_callable(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);path=root/'helper.py'
            path.write_text('from functools import lru_cache\n@lru_cache\ndef _compile_jinja_template(template):\n return template.upper()\n')
            spec=importlib.util.spec_from_file_location('cached_fixture',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            (root/'serving.py').write_text('tokenizer.apply_chat_template(messages)\n')
            # Execute the actual installed-Transformers fallback branch of the
            # remote probe, using an actual cached function imported from a file.
            node=next(n for n in ast.parse(suite.EFFORT_CHECK).body if isinstance(n,ast.If) and ast.unparse(n.test)=='not configs')
            code=compile(ast.Module(body=node.body,type_ignores=[]),'effort-fallback','exec')
            scope={'root':root,'template':'real cached function','Path':Path,'hashlib':hashlib}
            with patch.dict(sys.modules,{'transformers.utils.chat_template_utils':module}):exec(code,scope)
            self.assertEqual(scope['renderer']['source'],str(path));self.assertEqual(scope['renderer']['sha256'],sha(path))
            self.assertEqual(scope['rendered_template'],'REAL CACHED FUNCTION')
            self.assertEqual(module._compile_jinja_template.cache_info().misses,1)


class RecoveredControllerTests(unittest.TestCase):
    def test_recovered_stage_a_to_bcd_real_coordinator_no_replay_terminal_zero_calls(self):
        s=overnight();s['accuracy']={};s['accuracy_records']={};seen=[]
        with tempfile.TemporaryDirectory() as td,patch.object(ctrl,'report'):
            r=Path(td)
            # Six completed Stage A responses, one recovered locally, plus its
            # already consumed readiness. Neither these calls nor IDs are reset.
            s['calls']=[{'id':'call-001','parent':'readiness','status':'completed_response'}]
            for i,t in enumerate(suite.stage_tasks(s,1),2):
                t.update(status='critic_unchanged' if i==5 else 'critic_revised',call=f'call-{i:03d}')
                s['calls'].append({'id':t['call'],'parent':t['id'],'status':'completed_response'})
            suite.finish_stage(s,1);inherited=copy.deepcopy(s['calls'])
            def body(run,state,t):
                b=copy.deepcopy(BODY);b['reasoning_effort']=t['reasoning_effort'];b['messages'][0]['content']=t['id']
                if t['phase']=='critic':
                    self.assertEqual(next(x for x in state['tasks'] if x['id']==t['depends_on'])['status'],'conversion_completed')
                    t['dispatch_draft_sha256']=state['versions'][t['key']]['draft']['sha256']
                return b
            def transport(run,c,b,**kwargs):
                seen.append(c['parent']);c.update(status='completed_response',elapsed_seconds=.001,metadata={'finish_reason':'stop'})
                d=run/'calls'/c['id'];atomic_json(d/'request.json',b);atomic_json(d/'manifest.json',files_manifest(d));c['seal']=sha(d/'manifest.json')
                return DOC,c
            def finish(run,state,t,a,c):
                t.update(call=c['id'],status='conversion_completed' if t['phase']=='convert' else 'critic_unchanged')
                state['versions'][t['key']]={'draft':{'sha256':t['key']}};state['current_versions'][t['key']]='draft'
            def coordinator(*args,**kwargs):concurrent.coordinate(*args,**kwargs,transport=transport,poll_seconds=.001)
            with patch.object(ctrl,'body_for',side_effect=body):
                ctrl.run_stages(r,s,sample=lambda n:health(n),verify_inputs=Mock(),coordinator=coordinator,finish=finish)
            self.assertEqual(len(seen),38);self.assertEqual(len(set(seen)),38);self.assertEqual(s['calls'][:7],inherited)
            self.assertEqual(s['status'],suite.TERMINAL)
            for t in s['tasks']:
                if t['stage']>1 and t['phase']=='critic':self.assertLess(seen.index(t['depends_on']),seen.index(t['id']))
            ctrl.run_stages(r,s,sample=Mock(side_effect=AssertionError('no request')),verify_inputs=Mock(),coordinator=Mock(side_effect=AssertionError('no production')))
            with patch.object(ctrl,'verify',return_value=s),patch.object(ctrl.subprocess,'run',side_effect=AssertionError('terminal launch must do nothing')):ctrl.launch(r)
            self.assertEqual(len(s['calls']),45)

    def test_finalizer_error_traceback_saved_and_other_response_drained(self):
        s=overnight();tasks=suite.stage_tasks(s,2);s['active_stage']=2
        def body(run,state,t):return dict(BODY,reasoning_effort=t['reasoning_effort'])
        def transport(run,c,b,**kwargs):
            c.update(status='completed_response',metadata={},elapsed_seconds=.01)
            d=run/'calls'/c['id'];atomic_json(d/'request.json',b);atomic_json(d/'manifest.json',files_manifest(d));c['seal']=sha(d/'manifest.json')
            return DOC,c
        def fail(*args):raise KeyError('missing-version-fixture')
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)
            with self.assertRaises(KeyError):
                concurrent.coordinate(r,s,tasks,body_for=body,finish=fail,verify=Mock(),changed=Mock(),sample=lambda n:health(n),
                    transport=transport,fixed_level=2,before_reserve=suite.reservation_guard,poll_seconds=.001)
            for t in tasks:
                if t['status']=='coordinator_failure':
                    trace=(r/t['diagnostic_file']).read_text();self.assertIn('Traceback (most recent call last)',trace);self.assertIn('missing-version-fixture',trace)
            self.assertTrue(all(c['status']=='completed_response' for c in s['calls']))
            ctrl.write_progress(r,s);self.assertTrue(Path(read_json(r/'progress.json')['diagnostic_file']).is_file())

    def test_bundle_refreshes_progress_in_archive_and_on_disk(self):
        s=overnight()
        with tempfile.TemporaryDirectory() as td,patch.object(ctrl,'report'):
            root=Path(td);r=root/'run';r.mkdir();(root/'results').mkdir()
            atomic_json(r/'last-inspection.json',{'path':'old.zip'})
            with patch.object(ctrl,'ROOT',root):path=ctrl.bundle(r,s)
            self.assertEqual(read_json(r/'progress.json')['zip'],str(path))
            with zipfile.ZipFile(path) as z:self.assertEqual(json.loads(z.read('progress.json'))['zip'],str(path))
