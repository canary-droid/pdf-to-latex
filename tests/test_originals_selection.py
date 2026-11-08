"""Never-started selection, sealed history and real scheduler resume checks."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from probe import originals_selection as sel, chapter_glm as runtime, chapter_concurrency as scheduler
from probe.common import atomic_json, sha, read_json, fingerprint
from probe.experiment import seal
from scripts import book_completion as books
from test_speed_suite import DOC, BODY, health


def fixture():
    docs=[];tasks=[]
    for i,name in enumerate([*sel.CANDIDATES,'Calibrating Heston for Credit Risk (2017).pdf']):
        source='source-'+str(i)
        docs.append({'source_id':source,'sha256':str(i)*64,'originals':[{'name':name}]})
        for phase in ('convert','critic'):
            tasks.append({'id':source+'-part-001/'+phase,'key':source+'-part-001','source_key':source,
                          'phase':phase,'status':'pending','reasoning_effort':'high' if phase=='convert' else 'max'})
    state={'documents':{d['source_id']:{'status':'queued'} for d in docs},'tasks':tasks,'calls':[],
           'versions':{},'current_versions':{},'status':'paused','chapter_contract':'annotated-chapter-v1',
           'suite_protocol':'originals-batch-v1','timing_policy':'manual_only','first_dispatch':None,
           'execution_limits':{'calls':None,'attempts_per_unit':1},'phase_efforts':{'convert':'high','critic':'max'},
           'concurrency_policy':copy.deepcopy(scheduler.POLICY),'connection_failures':0,'active_stage':1,
           'production_stage':{'task_ids':[t['id'] for t in tasks]}}
    return {'documents':docs},state


class SelectionTests(unittest.TestCase):
    def test_controller_refuses_selection_while_writer_is_active(self):
        from scripts import originals_batch as ctrl
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);pointer=root/'pointer.json';atomic_json(pointer,{'run':str(root)})
            with patch.object(ctrl,'POINTER',pointer),patch.object(ctrl.books.speed,'idle',return_value=False),patch.object(ctrl,'verify',side_effect=AssertionError('Must not read mutable state')):
                with self.assertRaisesRegex(runtime.Fatal,'Drain'):ctrl.prepare_deferrals(root)

    def test_controller_never_generates_failure_package_for_deferred_source(self):
        from scripts import originals_batch as ctrl
        m,s=fixture();sel.apply(s,sel.decisions(m,s))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with self.assertRaisesRegex(runtime.Fatal,'Deferred'):ctrl.generation(root,s,m['documents'][0])
            self.assertFalse((root/'deliveries').exists())

    def test_deferred_library_record_is_additive_and_preserves_original(self):
        from scripts import originals_batch as ctrl
        m,s=fixture()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source=root/'original.pdf';source.write_bytes(b'%PDF-fixture')
            d=m['documents'][0];d.update(sha256=sha(source),folder='source-0--hash',title='Fixture',document_type='paper')
            s['documents']['source-0']['original']='original.pdf';sel.apply(s,sel.decisions(m,s))
            with patch.object(ctrl,'LIBRARY',root/'library'):
                ctrl.publish_document(root,s,d)
                out=root/'library'/d['folder'];first=sha(out/'original.pdf')
                ctrl.publish_document(root,s,d)
            self.assertEqual(first,sha(source));self.assertEqual(sha(out/'original.pdf'),first)
            self.assertEqual(read_json(out/'batch-selection.json')['reason'],sel.REASON)
            self.assertFalse((out/'generations').exists());self.assertFalse((out/'current.json').exists())

    def test_reservation_in_any_part_or_phase_retains_source_even_failed(self):
        for status in ('in_progress','completed_response','failed'):
            for phase in ('convert','critic'):
                m,s=fixture();t=next(t for t in s['tasks'] if t['source_key']=='source-0' and t['phase']==phase)
                s['calls']=[{'id':'call-1','parent':t['id'],'status':status}]
                rows=sel.decisions(m,s)
                self.assertEqual(rows[0]['decision'],'retained')
                self.assertEqual(sum(r['decision']=='deferred' for r in rows),5)

    def test_exact_six_only_and_heston_never_deferred(self):
        m,s=fixture();before=copy.deepcopy(s);rows=sel.decisions(m,s);sel.apply(s,rows)
        self.assertEqual(len(s['deferred_sources']),6)
        self.assertEqual(s['documents'],before['documents'])
        self.assertEqual(s['calls'],before['calls'])
        self.assertEqual([t['source_key'] for t in sel.active_tasks(s,s['tasks'])],['source-6','source-6'])
        self.assertEqual(sel.document_status(s,'source-0'),sel.STATUS)
        self.assertEqual(books.frozen_tasks(s),books.frozen_tasks(before))
        self.assertEqual(s['execution_limits'],before['execution_limits'])
        sel.apply(s,rows);self.assertEqual(len(s['production_stage']['task_ids']),2)

    def test_started_attention_and_finished_cos_keep_critics(self):
        m,s=fixture()
        for i,source in enumerate(('source-0','source-2')):
            t=next(t for t in s['tasks'] if t['source_key']==source and t['phase']=='convert')
            t['status']='conversion_completed';s['calls'].append({'id':'call-'+str(i+1),'parent':t['id'],'status':'completed_response'})
        before=copy.deepcopy(s);sel.apply(s,sel.decisions(m,s))
        self.assertEqual(len(s['deferred_sources']),4)
        for source in ('source-0','source-2'):
            t=next(t for t in s['tasks'] if t['source_key']==source and t['phase']=='critic')
            self.assertEqual(t['status'],'pending');sel.assert_dispatch(s,t)
        self.assertEqual(s['calls'],before['calls'])
        for t in s['tasks']:
            if sel.deferred(s,t['source_key']):
                with self.assertRaisesRegex(ValueError,'selection'):sel.assert_dispatch(s,t)
                with self.assertRaises(runtime.StopRun):runtime.reserve(s,t['id'],'hash')

    def test_ambiguity_missing_and_unreconciled_work_fail_closed(self):
        for change in ('ambiguous','missing','orphan','unledgered'):
            m,s=fixture()
            if change=='ambiguous':m['documents'].append(copy.deepcopy(m['documents'][0]))
            if change=='missing':m['documents']=m['documents'][1:]
            if change=='orphan':s['calls'].append({'id':'unknown','parent':'unknown'})
            if change=='unledgered':s['tasks'][0]['status']='running'
            with self.subTest(change=change),self.assertRaises(ValueError):sel.decisions(m,s)

    def test_stale_selection_cannot_cancel_a_new_reservation(self):
        m,s=fixture();rows=sel.decisions(m,s)
        s['calls'].append({'id':'new','parent':s['tasks'][0]['id'],'status':'in_progress'})
        with self.assertRaisesRegex(ValueError,'stale'):sel.apply(s,rows)
        self.assertNotIn('deferred_sources',s)

    def continuation(self,root):
        m,s=fixture();s['calls']=[{'id':'call-1','parent':s['tasks'][0]['id'],'status':'completed_response'}]
        folder=root/'continuations/one';atomic_json(root/'collection.json',m)
        atomic_json(folder/'prior-state.json',s);atomic_json(folder/'binding.json',{'code':'test fixture'})
        rows=sel.decisions(m,s);atomic_json(folder/'selection.json',{'inventory_sha256':sha(root/'collection.json'),'candidates':rows});seal(folder)
        sel.apply(s,rows);s['binding_path']='continuations/one/binding.json';s['selection_continuation']={'path':'continuations/one','seal':sha(folder/'manifest.json')}
        return s

    def test_seal_selection_policy_and_history_cannot_be_bypassed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);s=self.continuation(root);sel.verify(root,s)
            for mutate in ('reactivate','history','limits','selection','admission'):
                changed=copy.deepcopy(s)
                if mutate=='reactivate':changed['tasks'][2]['status']='pending'
                if mutate=='history':changed['calls'][0]['status']='failed'
                if mutate=='limits':changed['execution_limits']['attempts_per_unit']=2
                if mutate=='selection':changed['deferred_sources'].clear()
                if mutate=='admission':changed['production_stage']['task_ids'].append(changed['tasks'][2]['id'])
                with self.subTest(mutate=mutate),self.assertRaises(ValueError):sel.verify(root,changed)
            (root/'continuations/one/selection.json').write_text('{}')
            with self.assertRaises(ValueError):sel.verify(root,s)

    def test_threaded_resume_dispatches_only_retained_work_once(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);m,s=fixture();sel.apply(s,sel.decisions(m,s));seen=[]
            def transport(r,c,b,**kw):
                seen.append(c['parent']);c.update(status='completed_response',metadata={'finish_reason':'stop'},elapsed_seconds=.01)
                out=r/'calls'/c['id'];atomic_json(out/'request.json',b);seal(out);c['seal']=sha(out/'manifest.json');return DOC,c
            def finish(r,state,t,a,c):
                t['status']='conversion_completed' if t['phase']=='convert' else 'critic_unchanged'
                state['current_versions'][t['key']]='draft';state['versions'][t['key']]={'draft':{'sha256':'fixture'}}
            def go():
                scheduler.coordinate(root,s,sel.active_tasks(s,s['tasks']),body_for=lambda *_:BODY,finish=finish,
                    verify=lambda:None,changed=lambda:None,sample=lambda n:health(n),transport=transport,
                    fixed_level=2,poll_seconds=.01,before_reserve=lambda state,t,b:sel.assert_dispatch(state,t))
            go();calls=copy.deepcopy(s['calls']);go()
            self.assertEqual(seen,['source-6-part-001/convert','source-6-part-001/critic'])
            self.assertEqual(calls,s['calls']);self.assertTrue(all(t['status']==sel.STATUS for t in s['tasks'][:12]))


if __name__=='__main__':unittest.main()
