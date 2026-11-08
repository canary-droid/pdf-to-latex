import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from probe import originals_mineru_high as high, originals_mineru_only as low, originals_recovery as rec, chapter_glm as runtime
from probe.common import sha, fingerprint
from scripts import originals_batch as ctrl
from test_originals_recovery import low_fixture, DOC
from probe import chapter_concurrency as concurrent
from probe.common import atomic_json
from probe.experiment import seal
from test_speed_suite import health


def fixture(root):
    s,_=low_fixture(root);previous=rec.low_tasks(root,s)
    for t in previous:t.update(status='truncation' if t['phase']=='convert' else 'unavailable')
    job={'id':rec.KEY+'/syntax-original','key':rec.KEY,'source_key':rec.SOURCE,'phase':'syntax','status':'pending'}
    tasks=[]
    for phase,ident in [('convert',high.CONVERT),('critic',high.CRITIC)]:
        t={k:copy.deepcopy(previous[0][k]) for k in ('key','source_key','section','context')}
        t.update(id=ident,phase=phase,status='pending',reasoning_effort='high' if phase=='convert' else 'max',
                 depends_on=job['id'] if phase=='convert' else high.CONVERT,recovery_kind='mineru_high')
        tasks.append(t)
    s['tasks']+=previous+[job]+tasks;s['mineru_high_continuation']={'authority':'fixture'}
    s['production_stage']['task_ids']+=[job['id'],*high.IDS]
    return s,job,tasks


class HighMineruTests(unittest.TestCase):
    def test_operator_cancelled_syntax_is_not_reserved_and_high_is_ready(self):
        with tempfile.TemporaryDirectory() as td:
            s,job,ts=fixture(Path(td));job['status']='cancelled_by_operator'
            admitted=[t for t in s['tasks'] if high.admitted(s,t) and high.ready(s,t)]
            eligible=concurrent.eligible(s,admitted)
            self.assertEqual([t['id'] for t in eligible],[high.CONVERT]);self.assertNotIn(job['id'],[t['id'] for t in eligible])
            self.assertEqual(len(s['calls']),1)

    def test_shared_scheduler_finishes_existing_repair_before_high_and_own_critic(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,job,ts=fixture(r);s.update(status='running',suite_protocol='originals-batch-v1',
                concurrency_policy=copy.deepcopy(concurrent.POLICY),connection_failures=0,low_supported=True,active_stage=1)
            job.update(recovery_kind='syntax',plan_path='syntax-plan');repair_body={'model':'glm53-regular','messages':[{'role':'user','content':'Existing syntax job'}],'reasoning_effort':'low','max_tokens':8192,'stream':True}
            atomic_json(r/'syntax-plan/request.json',repair_body);atomic_json(r/'effort-support-live.json',{'low_supported':True})
            source=r/'inputs'/rec.SOURCE;seal(source);atomic_json(r/'plan.json',{'dispatch_input':str(source.relative_to(r)),'dispatch_input_seal':sha(source/'manifest.json'),'assets':{}});s['documents'][rec.SOURCE]['plan']='plan.json'
            p=r/'old.tex';p.write_text(DOC);s['versions'][rec.KEY]={'old':{'path':p.name,'sha256':sha(p)}};s['current_versions'][rec.KEY]='old'
            seen=[];real=concurrent.coordinate;new=DOC.replace('Assume','High assume')
            def transport(run,call,body,**kw):
                seen.append((call['parent'],body));folder=run/'calls'/call['id'];atomic_json(folder/'request.json',body);seal(folder)
                call.update(status='completed_response',elapsed_seconds=.01,metadata={'finish_reason':'stop'},seal=sha(folder/'manifest.json'));return new,call
            def finish(run,state,t,answer,call):
                if t['phase']=='syntax':t['status']='syntax_patch_rejected'
                elif t['phase']=='convert':
                    p=run/'high.tex';p.write_text(new);state['versions'][rec.KEY]['high']={'path':p.name,'sha256':sha(p)};state['current_versions'][rec.KEY]='high';t['status']='conversion_completed'
                else:t['status']='critic_unchanged'
                t['settled_call']=call['id']
            def coordinator(*args,**kw):return real(*args,**kw,transport=transport,poll_seconds=.01)
            guard=type('Guard',(),{'check':lambda self:None})()
            with patch.object(ctrl.concurrent,'coordinate',side_effect=coordinator),patch.object(ctrl,'finish',side_effect=finish),patch.object(ctrl,'progress'),patch.object(rec,'extra_ids',return_value=[job['id'],*high.IDS]),patch.object(high,'verify',return_value=list(high.IDS)):
                ctrl.dispatch(r,s,s['tasks'],lambda n:health(n),guard);ctrl.dispatch(r,s,s['tasks'],lambda n:health(n),guard)
            self.assertEqual([x[0] for x in seen],[job['id'],*high.IDS]);self.assertEqual(seen[1][1]['reasoning_effort'],'high');self.assertEqual(seen[2][1]['reasoning_effort'],'max');self.assertIn(new,seen[2][1]['messages'][0]['content']);self.assertEqual((r/'old.tex').read_text(),DOC)

    def test_neither_phase_is_eligible_before_syntax_job_settles(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,job,ts=fixture(r)
            for status in ('pending','running','interrupted_unresolved'):
                job['status']=status
                for t in ts:self.assertFalse(high.ready(s,t));self.assertIsNone(high.request(ctrl,r,s,t))

    def test_completed_or_failed_syntax_job_unlocks_high_only_primary(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,job,ts=fixture(r)
            for status in high.FINISHED:
                job['status']=status;body=high.request(ctrl,r,s,ts[0]);self.assertEqual(body['reasoning_effort'],'high')
                self.assertEqual(body['max_tokens'],131072);self.assertIn(ts[0]['section']['text'],body['messages'][0]['content']);self.assertNotIn('Whole native source.',body['messages'][0]['content'])

    def test_old_draft_is_not_reviewed_as_new_if_high_fails(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,job,ts=fixture(r);job['status']='syntax_patch_rejected'
            p=r/'old-low.tex';p.write_text(DOC);s['versions'][rec.KEY]={'old':{'path':p.name,'sha256':sha(p)}};s['current_versions'][rec.KEY]='old'
            for status in ('pending','running','truncation','complete_answer_without_document'):
                ts[0]['status']=status;self.assertIsNone(high.request(ctrl,r,s,ts[1]))

    def test_max_critic_is_bound_to_new_high_draft(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s,job,ts=fixture(r);job['status']='syntax_still_uncompiled';ts[0]['status']='conversion_completed'
            p=r/'high.tex';p.write_text(DOC);s['versions'][rec.KEY]={'high':{'path':p.name,'sha256':sha(p)}};s['current_versions'][rec.KEY]='high'
            body=high.request(ctrl,r,s,ts[1]);self.assertEqual(body['reasoning_effort'],'max');self.assertIn(DOC,body['messages'][0]['content']);self.assertNotIn('Whole native source.',body['messages'][0]['content'])
            with patch.object(high,'verify',return_value=list(high.IDS)):high.before_reserve(ctrl,r,s,ts[1],body)
            self.assertEqual(ts[1]['dispatched_draft_sha256'],sha(p))

    def test_old_attempts_are_history_and_syntax_task_is_prioritized(self):
        with tempfile.TemporaryDirectory() as td:
            s,job,ts=fixture(Path(td));before=copy.deepcopy(s['tasks'])
            active=[t for t in s['tasks'] if high.admitted(s,t)]
            self.assertEqual([t['id'] for t in active if t['phase']=='convert'],[high.CONVERT])
            self.assertEqual(high.priority(s,job),0);self.assertLess(high.priority(s,ts[0]),3)
            self.assertEqual(before,s['tasks'])

    def test_one_attempt_allowance_survives_resume(self):
        with tempfile.TemporaryDirectory() as td:
            s,job,ts=fixture(Path(td));runtime.reserve(s,high.CONVERT,'hash');resumed=copy.deepcopy(s)
            with self.assertRaises(runtime.StopRun):runtime.reserve(resumed,high.CONVERT,'hash')
            self.assertEqual(s['calls'],resumed['calls'])


if __name__=='__main__':unittest.main()
