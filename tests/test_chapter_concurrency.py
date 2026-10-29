"""Concurrency ownership and bindings, using threads/fake responses, no sockets/GPU."""
import copy
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from probe import chapter_concurrency as q, chapter_glm as r
from probe.common import atomic_json, fingerprint, files_manifest, read_json, sha
from scripts import editorial_chapters as ctrl

BODY={'model':'glm53-regular','messages':[{'role':'user','content':'Complete existing chapter context.'}],
      'stream':True,'max_tokens':131072,'reasoning_effort':'high'}
DOC=r'\documentclass{article}\begin{document}Preserved formula $x^2$.\end{document}'

def health(active=0,slots=4,pool=2015232):
    return {'context_length':1048576,'pool_tokens':pool,'pool_free_tokens':1000,'kept_mix':{'rows':1900000},
            'streams':{'decoding':active,'prefilling':0,'paused':0,'max':slots},'requests_running':active,'busy':bool(active)}


def fixture(n=8):
    tasks=[{'id':f'u{k}-{p}','key':f'bergomi-{k}','source_key':'bergomi-01','phase':p,'status':'pending',
            'section':{'blocks':[f'b{k}'],'text':'complete existing source'},'draft_label':None,'context':''}
           for k in range(n) for p in ('convert','critic')]
    return {'chapter_contract':'annotated-chapter-v1','execution_limits':{'calls':None,'attempts_per_unit':1},
            'timing_policy':'manual_only','first_dispatch':None,'calls':[], 'historical_calls':[], 'connection_failures':0,
            'tasks':tasks,'production_stage':{'task_ids':[t['id'] for t in tasks]},'current_versions':{},
            'concurrency_policy':copy.deepcopy(q.POLICY),'versions':{}}

class CapacityTests(unittest.TestCase):
    def test_shared_pool_not_context_times_slots_or_just_free_cache(self):
        h=health();fits,b=q.room(BODY,[],h,0);self.assertTrue(fits)
        huge=dict(BODY,messages=[{'role':'user','content':'a'*600000}])
        fits,b=q.room(huge,[],h,0);self.assertTrue(fits)
        self.assertFalse(q.room(huge,[b,b],health(2),2)[0])
        with self.assertRaisesRegex(r.Fatal,'Unowned'):q.health_limits(health(1),0)
        with self.assertRaisesRegex(r.Fatal,'two'):q.health_limits(health(slots=1),0)
        with self.assertRaises(ValueError):q.room(dict(BODY,messages=[{'role':'user','content':'a'*1100000}]),[],h,0)
    def test_four_requires_real_overlap_and_usable_batch_throughput(self):
        s=fixture(0);p={'trials':{'two':{'metrics':{'usable_completion_tokens_per_active_second':10}}}}
        t={'calls':[],'active_seconds':1,'started_epoch':time.time(),'level':4,'resource_pressure':False,'max_server_streams':2}
        self.assertIn('overlap',q.assessment(s,p,t)[1])
        t.update(max_server_streams=4,resource_pressure=True)
        self.assertIn('pressure',q.assessment(s,p,t)[1])
    def test_runtime_binding_requires_actual_sources_and_no_secrets(self):
        self.assertNotIn('HF_TOKEN',q.BUILD_PROGRAM);self.assertNotIn('local.sh',q.BUILD_PROGRAM)
        self.assertIn("'model_metadata_hashes'",q.BUILD_PROGRAM)
    def test_reasoning_volume_is_not_usable_final_output_or_qualification(self):
        s=fixture(1);t=s['tasks'][0];t.update(status='truncation',call='call-001')
        s['calls']=[{'id':'call-001','parent':t['id'],'status':'failed','metadata':{
            'usage':{'completion_tokens':131072,'completion_tokens_details':{'reasoning_tokens':131072}}}}]
        trial={'calls':['call-001'],'active_seconds':1,'started_epoch':time.time(),'level':2,
               'resource_pressure':False,'max_server_streams':2}
        self.assertFalse(q.assessment(s,{},trial)[0])
        self.assertIsNone(trial['metrics']['usable_nonreasoning_tokens'])
        t['status']='conversion_completed'
        s['calls'][0]['metadata']['usage']['completion_tokens_details']['reasoning_tokens']=131000
        self.assertEqual(q.trial_metrics(s,trial)['usable_nonreasoning_tokens'],72)
        del s['calls'][0]['metadata']['usage']['completion_tokens_details']
        self.assertIsNone(q.trial_metrics(s,trial)['usable_nonreasoning_tokens'])

    def test_interrupted_link_preserves_calls_time_and_historical_status(self):
        old={'status':'stopped_error','diagnostic':'ownership stop','concurrency_progress':{
            'phase':'two','qualified_level':None,'trials':{'two':{'status':'running','calls':['call-102','call-103'],
            'active_seconds':2104.6}},'sessions':[{'finished_epoch':123}]}}
        progress=copy.deepcopy(old['concurrency_progress']);q.interrupted_handover(progress,old,Path('/parent'))
        self.assertEqual(old['concurrency_progress']['trials']['two']['status'],'running')
        trial=progress['trials']['two'];self.assertEqual(trial['status'],'interrupted')
        self.assertEqual(trial['calls'],['call-102','call-103']);self.assertEqual(trial['active_seconds'],2104.6)
        self.assertEqual(trial['last_active_epoch'],123)

class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.active=0;self.peak=0;self.lock=threading.Lock();self.seen=[];self.fail=set();self.pause_after=None
    def body(self,run,state,t):
        return dict(BODY,reasoning_effort='max' if t['phase']=='critic' else 'high',messages=[{'role':'user','content':t['id']+' exact original source'}])
    def transport(self,run,c,body,**kwargs):
        with self.lock:
            self.active+=1;self.peak=max(self.peak,self.active);self.seen.append(c['parent'])
        # Workers must observe their reservation already persisted by coordinator.
        saved=read_json(run/'state.json');self.assertIn(c['id'],[x['id'] for x in saved['calls']])
        if hasattr(self,"before_completion"):self.before_completion(c)
        time.sleep(.15)
        if self.pause_after and len(self.seen)>=self.pause_after:atomic_json(run/'pause.json',{'requested':True})
        with self.lock:self.active-=1
        c.update(status='completed_response',elapsed_seconds=.035,metadata={'actual_model':'glm53-regular','finish_reason':'stop','usage':{'completion_tokens':100,'prompt_tokens':30}})
        answer=DOC
        if c['parent'] in self.fail:
            c.update(status='failed',failure_kind='truncation',error='length');answer=None
        dest=run/'calls'/c['id'];dest.mkdir(parents=True)
        atomic_json(dest/'request.json',body);atomic_json(dest/'attempts/one/request.json',{'body':body})
        atomic_json(dest/'outcome.json',c);atomic_json(dest/'manifest.json',files_manifest(dest));c['seal']=sha(dest/'manifest.json')
        return answer,c
    def finish(self,run,s,t,answer,c):
        self.assertEqual(c['parent'],t['id']);t['call']=c['id']
        if answer is None:t.update(status='truncation',error='length');return
        t['status']='conversion_completed' if t['phase']=='convert' else 'critic_unchanged'
        if t['phase']=='convert':s['current_versions'][t['key']]=c['id']
    def sample(self,owned):
        with self.lock:active=self.active
        return {'health':health(active),'memory_available_bytes':{'head':8*1024**3,'peer':12*1024**3},'evidence':{}}
    def run_queue(self,s):
        q.coordinate(self.root,s,s['tasks'],body_for=self.body,finish=self.finish,verify=lambda:None,
                     changed=lambda:None,sample=self.sample,transport=self.transport,poll_seconds=.005)
    def production(self,s,level=2):
        s['concurrency_progress']={'phase':'production','qualified_level':level,'trials':{},'sessions':[]}
    def test_unique_dispatch_correct_association_priority_and_dependency(self):
        s=fixture(4);self.production(s);original=copy.deepcopy(s['tasks']);self.run_queue(s)
        self.assertEqual(len(s['calls']),8);self.assertEqual(len({c['id'] for c in s['calls']}),8);self.assertEqual(self.peak,2)
        for k in range(4):self.assertLess(self.seen.index(f'u{k}-convert'),self.seen.index(f'u{k}-critic'))
        self.assertLess(self.seen.index('u0-critic'),self.seen.index('u2-convert'))
        for before,after in zip(original,s['tasks']):self.assertEqual(before['section'],after['section'])
        old=copy.deepcopy(s['calls']);self.run_queue(s);self.assertEqual(old,s['calls'])
    def test_pause_drains_and_resume_does_not_reconvert(self):
        s=fixture(3);self.production(s);self.pause_after=2
        with self.assertRaises(r.StopRun):self.run_queue(s)
        self.assertEqual(self.active,0);self.assertEqual(len(s['calls']),2)
        self.assertTrue(all(c['status']=='completed_response' for c in s['calls']))
        self.pause_after=None;(self.root/'pause.json').unlink();self.run_queue(s)
        self.assertEqual(len(s['calls']),6);self.assertEqual(len(self.seen),len(set(self.seen)))
    def test_failure_isolation_and_unknown_reservation_never_replayed(self):
        s=fixture(3);self.production(s);self.fail={'u0-convert'}
        s['calls'].append({'id':'call-001','parent':'u2-convert','request_sha256':'unknown','status':'in_progress'})
        self.run_queue(s)
        self.assertNotIn('u0-critic',self.seen);self.assertNotIn('u2-convert',self.seen)
        self.assertIn('u1-critic',self.seen);self.assertEqual(s['tasks'][4]['status'],'interrupted_unresolved')
    def test_historical_98_boundary_has_no_special_meaning_and_stage_is_exact(self):
        s=fixture(1);self.production(s);s['calls']=[{'id':f'call-{i:03d}','parent':'history','status':'completed_response'} for i in range(1,100)]
        s['tasks'].append({'id':'not-admitted','status':'pending','phase':'convert','key':'other','source_key':'other'})
        with self.assertRaises(r.StopRun):self.run_queue(s)
        self.assertEqual(s['calls'][99]['id'],'call-100');self.assertNotIn('not-admitted',self.seen)
    def test_two_slot_pilot_continues_without_automatic_four(self):
        s=fixture(9)
        # Qualification arithmetic is tested independently; thread timing is not
        # a deterministic benchmark. Require actual observed overlap here.
        def assess(state,progress,t):
            t['metrics']=q.trial_metrics(state,t)
            return t['max_server_streams']>=t['level'],'observed overlap'
        with patch.object(q,'assessment',side_effect=assess):self.run_queue(s)
        p=s['concurrency_progress'];self.assertEqual(len(p['trials']['two']['calls']),4)
        self.assertNotIn('four',p['trials']);self.assertEqual(p['qualified_level'],2)
        self.assertEqual(len(s['calls']),18);self.assertEqual(self.peak,2)
    def test_completed_conversion_awaiting_critic_is_not_generated_again(self):
        s=fixture(1);self.production(s)
        s['tasks'][0].update(status='conversion_completed',call='old-conversion')
        s['current_versions']['bergomi-0']='saved-complete'
        s['calls']=[{'id':'old-conversion','parent':'u0-convert','status':'completed_response'}]
        self.run_queue(s);self.assertEqual(self.seen,['u0-critic']);self.assertEqual(len(s['calls']),2)
    def test_completion_invalidates_two_request_snapshot_before_new_admission(self):
        s=fixture(2);self.production(s)
        sampled_two=threading.Event();replacement=threading.Event();clock=[0.0];observed=[]
        base=self.sample
        def before(c):
            if c['parent']=='u0-convert':self.assertTrue(sampled_two.wait(3))
            elif c['parent']=='u1-convert':
                clock[0]=100.0
                self.assertTrue(replacement.wait(3))
            else:replacement.set()
        def sample(owned):
            obs=base(owned);observed.append((owned,obs['health']['requests_running']))
            if obs['health']['requests_running']==2:sampled_two.set()
            return obs
        self.before_completion=before;self.sample=sample
        # Freeze the clock after the two-request sample: the 15s cache would
        # otherwise be reused after one completes. This reproduces call102/103.
        with patch.object(q.time,'monotonic',side_effect=lambda:clock[0]):self.run_queue(s)
        self.assertIn((2,2),observed);self.assertIn((1,1),observed)
        self.assertEqual(len(s['calls']),4);self.assertEqual(len(set(self.seen)),4)

    def test_external_request_still_stops_admission_and_drains_owned_outputs(self):
        s=fixture(3);base=self.sample
        def external(owned):
            obs=base(owned)
            if obs['health']['requests_running']==2:obs['health']=health(3)
            return obs
        self.sample=external
        with self.assertRaisesRegex(r.Fatal,'server running=3.*local owned at sample=2'):self.run_queue(s)
        self.assertEqual(self.active,0);self.assertEqual(len(s['calls']),2)
        self.assertTrue(all(c['status']=='completed_response' for c in s['calls']))
        progress=s['concurrency_progress'];self.assertEqual(progress['trials']['two']['status'],'interrupted')
        evidence=read_json(self.root/progress['sessions'][-1]['stop_record'])
        self.assertEqual(evidence['observation']['coordinator_owned_calls'],['call-001','call-002'])
        self.assertEqual(evidence['observation']['health']['requests_running'],3)
        self.assertEqual(len(evidence['local_calls']),2)
        self.assertEqual(read_json(self.root/'concurrency-report.json')['progress']['trials']['two']['status'],'interrupted')
        self.sample=base;self.run_queue(s)
        self.assertEqual(len(s['calls']),6);self.assertEqual(len(set(self.seen)),6)
        self.assertEqual(len(progress['trials']['two']['calls']),4)
    def test_two_slot_server_skips_four_without_changing_server_or_requests(self):
        s=fixture(5);base=self.sample
        def two(owned):
            v=base(owned);v['health']['streams']['max']=2;return v
        self.sample=two
        with patch.object(q,'assessment',side_effect=lambda st,pr,t:(t.update(metrics=q.trial_metrics(st,t)) or True,'test qualification')):
            self.run_queue(s)
        self.assertEqual(self.peak,2);self.assertNotIn('four',s['concurrency_progress']['trials'])
        self.assertEqual(len(s['calls']),10)
    def test_four_cannot_be_enabled_by_a_saved_progress_value(self):
        s=fixture(6);self.production(s,level=4)
        with self.assertRaisesRegex(r.Fatal,'two-slot'):self.run_queue(s)
        self.assertEqual(self.seen,[])

    def test_wrong_binding_stops_new_dispatch_and_drains_other_output(self):
        s=fixture(3);self.production(s);base=self.transport
        def wrong(run,c,b,**kw):
            a,c=base(run,c,b,**kw)
            if c['parent']=='u0-convert':c['parent']='other'
            return a,c
        with self.assertRaises(r.Fatal):
            q.coordinate(self.root,s,s['tasks'],body_for=self.body,finish=self.finish,verify=lambda:None,changed=lambda:None,
                         sample=self.sample,transport=wrong,poll_seconds=.005)
        self.assertEqual(self.active,0);self.assertEqual(len(s['calls']),2)
        self.assertEqual(s['tasks'][2]['status'],'conversion_completed')

class TransportTests(unittest.TestCase):
    def test_actual_body_keeps_effort_stream_and_tokens_without_state_write(self):
        from test_simple_chapter_continuous import FakeConnection,FakeResponse,event
        from probe.local_model import LocalClient
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);client=LocalClient('http://127.0.0.1:8888/v1','glm53-regular',purpose='simple_chapter',timeout=10,max_tokens=131072)
            client.model='glm53-regular'
            wire=FakeConnection(FakeResponse([event({'reasoning_content':'server reasoning'}),event({'content':DOC},finish='stop'),b'data: [DONE]\n\n']))
            call={'id':'call-001','parent':'u0-convert','request_sha256':fingerprint(BODY),'status':'in_progress'}
            with patch('probe.local_model.http.client.HTTPConnection',return_value=wire):
                answer,result=r.perform_reserved(run,call,BODY,continuous=True,admission_budget={},health_evidence={},client=client)
            self.assertEqual(wire.sent,BODY);self.assertEqual(answer,DOC);self.assertFalse((run/'state.json').exists())
            self.assertEqual((run/'calls/call-001/reasoning.txt').read_text(),'server reasoning')
            q.response_binding(run,result,BODY)
    def test_legacy_idle_guard_is_preserved(self):
        with self.assertRaisesRegex(ValueError,'overlapping'):r.protocol.health_capacity(health(1))


class LinkedRepairTests(unittest.TestCase):
    def test_link_keeps_completed_calls_requests_runtime_and_interrupted_pilot(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);parent=root/'parent';parent.mkdir();new=root/'linked'
            old=fixture(3);old.update(status='stopped_error',diagnostic='ownership stop',
                                    compiler_environment={'path':'compiler'})
            old['tasks'][0].update(status='conversion_completed',call='call-100')
            old['tasks'][1].update(status='critic_revised',call='call-102')
            old['tasks'][2].update(status='conversion_completed',call='call-103')
            old['current_versions']={'bergomi-0':'reviewed','bergomi-1':'saved-draft'}
            old['calls']=[{'id':ident,'parent':task['id'],'status':'completed_response'}
                          for ident,task in zip(['call-100','call-102','call-103'],old['tasks'][:3])]
            old['concurrency_progress']={'phase':'two','qualified_level':None,'trials':{'two':{
                'status':'running','level':2,'calls':['call-102','call-103'],'active_seconds':2104.6,
                'started_epoch':1,'max_server_streams':2,'resource_pressure':False}},
                'sessions':[{'finished_epoch':2106}]}
            binding={'code':{'old':'hash'}}
            atomic_json(parent/'binding.json',binding);atomic_json(parent/'state.json',old)
            atomic_json(parent/'concurrency-runtime-binding.json',{'identity':'verified-existing-runtime'})
            atomic_json(parent/'inputs/native.json',{'content':'unchanged source'})
            pointer=root/'pointer.json';atomic_json(pointer,{'run':str(parent)})
            original_state=sha(parent/'state.json');bodies=[]
            def body(run,state,task):
                bodies.append((run,task['id']))
                return {'source':'same source','task':task['id']}
            with patch.object(ctrl,'ROOT',root),patch.object(ctrl,'POINTER',pointer),\
                 patch.object(ctrl,'recorded_evidence',return_value=(binding,old)),\
                 patch.object(ctrl,'code_hashes',return_value={'fixed':'hash'}),patch.object(ctrl,'converter_idle'),\
                 patch.object(ctrl.chapter_inputs,'new_path',return_value=new),patch.object(ctrl,'body_for',side_effect=body),\
                 patch.object(ctrl,'verify'),patch.object(ctrl,'report'):
                self.assertEqual(ctrl.prepare_concurrency(parent,repair=True),new)
            linked=read_json(new/'state.json');progress=linked['concurrency_progress']
            self.assertEqual(sha(parent/'state.json'),original_state)
            self.assertEqual(linked['tasks'],old['tasks']);self.assertEqual(linked['current_versions'],old['current_versions'])
            self.assertEqual(progress['trials']['two']['calls'],['call-102','call-103'])
            self.assertEqual(progress['trials']['two']['active_seconds'],2104.6)
            self.assertEqual(progress['trials']['two']['status'],'interrupted')
            self.assertTrue(all(c['inherited_from']==str(parent) for c in linked['calls']))
            self.assertEqual(linked['concurrency_policy']['maximum_in_flight'],2)
            self.assertEqual(read_json(new/'ownership-recovery.json')['remaining_pilot_requests'],2)
            self.assertEqual(sha(new/'concurrency-runtime-binding.json'),sha(parent/'concurrency-runtime-binding.json'))
            self.assertEqual(read_json(pointer)['run'],str(new))
            self.assertEqual({task for _,task in bodies},{t['id'] for t in old['tasks'] if t['status']=='pending'})
