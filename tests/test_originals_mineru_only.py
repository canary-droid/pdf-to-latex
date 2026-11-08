import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from probe import originals_mineru_only as one, originals_recovery as rec, chapter_glm as runtime
from probe.common import atomic_json, sha, fingerprint
from scripts import originals_batch as ctrl
from test_originals_recovery import low_fixture, DOC
from probe import chapter_concurrency as concurrent
from probe.experiment import seal
from test_speed_suite import health


class MineruOnlyTests(unittest.TestCase):
    def fixture(self,r):
        s,_=low_fixture(r);ts=rec.low_tasks(r,s)
        for t,ident in zip(ts,one.IDS):t.update(id=ident,recovery_kind='mineru_only',status='pending')
        ts[1]['depends_on']=one.CONVERT
        s['tasks']+=ts;s['production_stage']['task_ids']+=list(one.IDS)
        ts[0]['preview_hash']=fingerprint(one.request(ctrl,r,s,ts[0]))
        return s,ts

    def test_shared_scheduler_runs_conversion_then_mineru_only_critic_once(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,ts=self.fixture(r);s.update(status='running',suite_protocol='originals-batch-v1',
                active_stage=1,connection_failures=0,low_supported=True,concurrency_policy=copy.deepcopy(concurrent.POLICY))
            s['production_stage']['task_ids']=list(one.IDS)
            source=r/'inputs'/rec.SOURCE;seal(source)
            atomic_json(r/'plan.json',{'dispatch_input':str(source.relative_to(r)),'dispatch_input_seal':sha(source/'manifest.json'),'assets':{}})
            s['documents'][rec.SOURCE]['plan']='plan.json';atomic_json(r/'effort-support-live.json',{'low_supported':True})
            seen=[];real=concurrent.coordinate
            def transport(run,call,body,**kw):
                seen.append((call['parent'],body));self.assertNotIn('Whole native source.',body['messages'][0]['content'])
                out=run/'calls'/call['id'];atomic_json(out/'request.json',body);seal(out)
                call.update(status='completed_response',metadata={'finish_reason':'stop'},elapsed_seconds=.01,seal=sha(out/'manifest.json'));return DOC,call
            def finish(run,state,t,answer,call):
                p=run/'new.tex';p.write_text(DOC);state['versions'][rec.KEY]={'new':{'path':'new.tex','sha256':sha(p)}};state['current_versions'][rec.KEY]='new'
                t.update(status='conversion_completed' if t['phase']=='convert' else 'critic_unchanged',settled_call=call['id'])
            def coordinator(*a,**kw):return real(*a,**kw,transport=transport,poll_seconds=.01)
            guard=type('Guard',(),{'check':lambda self:None})()
            with patch.object(ctrl.concurrent,'coordinate',side_effect=coordinator),patch.object(ctrl,'finish',side_effect=finish),patch.object(ctrl,'progress'),patch.object(one,'verify',return_value=list(one.IDS)):
                ctrl.dispatch(r,s,s['tasks'],lambda n:health(n),guard);ctrl.dispatch(r,s,s['tasks'],lambda n:health(n),guard)
            self.assertEqual([x[0] for x in seen],list(one.IDS));self.assertIn(DOC,seen[1][1]['messages'][0]['content'])

    def test_conversion_keeps_complete_primary_and_omits_pdf_layer(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,ts=self.fixture(r);body=one.request(ctrl,r,s,ts[0]);text=body['messages'][0]['content']
            self.assertIn(ts[0]['section']['text'],text);self.assertNotIn('Whole native source.',text)
            self.assertNotIn('SECONDARY EXTRACTION —',text);self.assertNotIn('and both sources',text)
            self.assertEqual(body['reasoning_effort'],'low');self.assertEqual(body['max_tokens'],131072)
            self.assertEqual(ts[0]['section'],s['tasks'][0]['section']);self.assertEqual(body['model'],'glm53-regular')

    def test_critic_uses_own_draft_with_mineru_only(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,ts=self.fixture(r);p=r/'draft.tex';p.write_text(DOC)
            s['versions'][rec.KEY]={'new':{'path':'draft.tex','sha256':sha(p)}};s['current_versions'][rec.KEY]='new';ts[0]['status']='conversion_completed'
            body=one.request(ctrl,r,s,ts[1]);self.assertIn(DOC,body['messages'][0]['content']);self.assertNotIn('Whole native source.',body['messages'][0]['content']);self.assertEqual(body['reasoning_effort'],'max')
            with patch.object(one,'verify',return_value=list(one.IDS)):one.before_reserve(ctrl,r,s,ts[1],body)
            self.assertEqual(ts[1]['dispatched_draft_sha256'],sha(p))

    def test_no_critic_before_usable_conversion(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,ts=self.fixture(r)
            self.assertIsNone(one.request(ctrl,r,s,ts[1]))
            with patch.object(one,'verify',return_value=list(one.IDS)),self.assertRaises(runtime.Fatal):one.before_reserve(ctrl,r,s,ts[1],{})

    def test_allowance_survives_resume_and_rejects_source_substitution(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,ts=self.fixture(r);body=one.request(ctrl,r,s,ts[0]);atomic_json(r/'effort-support-live.json',{'low_supported':True})
            changed=copy.deepcopy(body);changed['messages'][0]['content']+='\nPDF layer injected'
            with patch.object(one,'verify',return_value=list(one.IDS)),self.assertRaises(runtime.Fatal):one.before_reserve(ctrl,r,s,ts[0],changed)
            runtime.reserve(s,one.CONVERT,fingerprint(body));saved=copy.deepcopy(s)
            with self.assertRaises(runtime.StopRun):runtime.reserve(saved,one.CONVERT,fingerprint(body))
            self.assertEqual(saved['calls'],s['calls'])

    def test_new_effective_phase_does_not_change_other_documents(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,ts=self.fixture(r);s.update(recovery_continuation={'old':'preserved'},mineru_only_continuation={'new':'authority'})
            s['tasks'].append({'id':'other/convert','source_key':'other','phase':'convert','status':'pending'})
            self.assertEqual([t['id'] for t in rec.effective_tasks(s,rec.SOURCE)],list(one.IDS))
            self.assertEqual(rec.effective_tasks(s,'other')[0]['id'],'other/convert')

    def test_handoff_refuses_an_active_writer(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);p=r/'pointer.json';atomic_json(p,{'run':str(r)})
            with patch.object(ctrl,'POINTER',p),patch.object(ctrl.books.speed,'idle',return_value=False),patch.object(ctrl,'verify',side_effect=AssertionError('No mutable-state read')):
                with self.assertRaisesRegex(runtime.Fatal,'Drain'):one.prepare(ctrl,r)


if __name__=='__main__':unittest.main()
