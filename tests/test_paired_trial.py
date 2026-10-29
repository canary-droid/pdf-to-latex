"""Offline at-most-once and paired isolation regressions; no mock sockets needed."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from probe.common import atomic_json, files_manifest, fingerprint, read_json, sha
from probe import paired_inputs as inputs, paired_trial as trial, paired_report as report
from probe.local_model import LocalClient, ProbeError
from probe.batch_review import IdentityError, IntegrityError


def rows():
    return [{'block_id':f'p{i%16:02d}:b{i}','page_id':f'p{i%16:02d}',
        'page':{'selected_page':i%16+1,'original_physical_page':106+i%16},
        'flags':{'test':'diagnostic never input'} if i<202 else {},
        'ocr_segments':[{'kind':'inline_math' if i%3 else 'prose','text':'x'}],
        'alignment':'ambiguous' if i%7==0 else 'matched_exact','split':'development'} for i in range(267)]


def data(n=1):
    return {'page_id':'p001','source_id':'synthetic','page':{'selected_page':1,'original_physical_page':106},
        'review_scope':'selected_blocks','blocks':[{'id':f'p001:b{n}','native':{'content':'A sentence.'}}],
        'context_blocks':[],'draft_by_block':[{'latex':'A sentence.'}],'images':[]}


def valid(d):
    return {'page_id':d['page_id'],'scope':'selected_blocks','complete':True,
            'reviewed_block_ids':[d['blocks'][0]['id']],'proposals':[], 'proposal_categories':[],'observations':[]}


class InputTests(unittest.TestCase):
    def test_267_partition_spread_and_priority_without_duplicates(self):
        pool=rows();first=[r['block_id'] for r in pool[:7]+pool[202:207]]
        ordered=inputs.cohort(pool,first)
        self.assertEqual(ordered,inputs.cohort(list(reversed(pool)),first))
        self.assertEqual(len(ordered),267);self.assertEqual(len({s['region_id'] for s in ordered}),267)
        self.assertEqual([s['region_id'] for s in ordered[:12]],first)
        self.assertEqual(sum(s['flagged'] for s in ordered[12:48]),18)
        self.assertEqual(sum(not s['flagged'] for s in ordered[12:48]),18)
        self.assertEqual(len({s['page_id'] for s in ordered[:48]}),16)
        self.assertEqual(len([s for s in ordered if s['phase']=='remainder']),219)
        self.assertEqual(len(trial.slots(ordered)),534)
        for i,s in enumerate(ordered):self.assertEqual(s['arm_order'],['A','B'] if i%2==0 else ['B','A'])
        with self.assertRaises(IntegrityError):inputs.cohort(pool[:-1]+[pool[0]],first)
        pool[0]['flags']={}
        with self.assertRaises(IntegrityError):inputs.cohort(pool,first)

    def test_actual_client_serialization_and_only_B_has_native(self):
        d=data();text='x − 1\x0b\nﬁ ≤ y²;';ims=[({'role':'context','bbox':[0,0,1,1]},b'png')]
        a=inputs.request(d,text,ims,'A');b=inputs.request(d,text,ims,'B')
        self.assertEqual(a['messages'][0]['content'],b['messages'][0]['content'][:-1])
        self.assertEqual(json.loads(inputs.native_serialization(text))['native_pdf_text'],text)
        self.assertIn('U+000B',inputs.native_serialization(text));self.assertIn('\\u000b',inputs.native_serialization(text))
        for body in (a,b):
            self.assertEqual(len(body['messages']),1);self.assertEqual(body['messages'][0]['role'],'user')
            self.assertNotIn('response_format',body);self.assertNotIn('temperature',body)
            self.assertNotIn('alignment',json.dumps(body));self.assertNotIn('diagnostic never input',json.dumps(body))
        with tempfile.TemporaryDirectory() as td:
            client=FakeClient(inputs.CONFIG['endpoint'],model=inputs.CONFIG['model'],purpose='page_review',max_tokens=16384,timeout=600)
            client.model=inputs.CONFIG['model']
            client.chat(b['messages'],Path(td),'test',reasoning_effort='medium')
            self.assertEqual(read_json(next(Path(td).glob('attempts/*/request.json')))['body'],b)

    def test_identity_strict_json_schema_coverage_and_categories(self):
        d=data();a={'actual_model':inputs.CONFIG['model'],'finish_reason':'stop','content':json.dumps(valid(d))}
        self.assertEqual(inputs.validate_answer(a,d),valid(d))
        with self.assertRaises(IdentityError):inputs.validate_answer({**a,'actual_model':'another'},d)
        for content in ['```json\n{}\n```','{"x":1,"x":2}','NaN']:
            with self.assertRaises(inputs.ResponseJSONError):inputs.validate_answer({**a,'content':content},d)
        for key,value in [('reviewed_block_ids',[]),('complete',False),('scope','whole_page'),('proposal_categories',['style']),('observations',[{'category':'style','text':4}])]:
            v=valid(d);v[key]=value
            with self.assertRaises(ValueError):inputs.validate_answer({**a,'content':json.dumps(v)},d)

    def test_future_critic_and_remainder_selection_have_no_gold_labels(self):
        r=rows();order=inputs.cohort(r,[x['block_id'] for x in r[:12]])
        for s in order:
            s.update(arms={'A':{'status':'pending'},'B':{'status':'pending'}},matched_completed_pair=False,pair_answer_difference=False)
        order[70]['arms']['A']={'status':'failed','failure_kind':'json'}
        order[80]['arms']={'A':{'status':'completed'},'B':{'status':'completed'}};order[80]['matched_completed_pair']=True;order[80]['pair_answer_difference']=True
        chosen=report.diagnostic_selection(order)
        self.assertEqual(len(chosen),50);self.assertEqual(chosen[48]['ordinal'],71)


class FakeClient(LocalClient):
    actions=[];dispatched=[];counter=0;tick=None
    def _request(self,method,endpoint,payload,output_dir,label):
        dest=Path(output_dir)/'attempts'/str(FakeClient.counter);FakeClient.counter+=1;dest.mkdir(parents=True)
        atomic_json(dest/'request.json',{'body':payload})
        record={'http_status':200,'latency_seconds':1.0};atomic_json(dest/'record.json',record)
        evidence={'attempt_dir':str(dest),'latency_seconds':1.0,'http_status':200}
        if method=='GET':return {'data':[{'id':inputs.CONFIG['model']}]},evidence
        FakeClient.dispatched.append(payload)
        if FakeClient.tick:FakeClient.tick()
        action=FakeClient.actions.pop(0) if FakeClient.actions else 'ok'
        if action=='crash':raise KeyboardInterrupt()
        if action in ('transport','timeout','option'):
            status=400 if action=='option' else None
            record['http_status']=status;atomic_json(dest/'record.json',record)
            raise ProbeError('timed out' if action=='timeout' else 'failed',attempt_dir=dest,status=status)
        text=payload['messages'][0]['content'][0]['text']
        d=json.loads(text.split('SELECTED DATA:\n')[1]);v=valid(d)
        if action=='coverage':v['reviewed_block_ids']=[]
        if action=='schema':v['extra']=True
        content='```bad json```' if action=='json' else json.dumps(v)
        result={'model':'wrong-model' if action=='identity' else inputs.CONFIG['model'],
                'choices':[{'finish_reason':'length' if action=='length' else 'stop','message':{'content':content}}],
                'usage':{'completion_tokens':16384 if action=='length' else 10}}
        (dest/'response.raw').write_text(json.dumps(result));return result,evidence


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.preview=self.root/'preview';self.preview.mkdir();self.out=self.root/'live'
        self.source=self.root/'source';self.source.write_text('immutable')
        self.order=[]
        for n in range(1,14):
            d=data(n);folder=self.preview/'regions'/f'{n:03d}';folder.mkdir(parents=True)
            atomic_json(folder/'input.json',d);atomic_json(folder/'native.json',{'text':'native','serialization':'native'})
            for arm in ('A','B'):atomic_json(folder/(arm+'.json'),inputs.request(d,'native',[],arm))
            self.order.append({'ordinal':n,'region_id':f'p001:b{n}','page_id':'p001','page':d['page'],
                'phase':'priority','arm_order':['A','B'] if n%2 else ['B','A'],'flagged':False,'alignment':'matched_exact'})
        atomic_json(self.preview/'evaluator-manifest.json',{'regions':self.order})
        atomic_json(self.preview/'preview.json',{'config':inputs.CONFIG,'policy':inputs.POLICY,'code_sha256':inputs.code_hashes(),
                    'source_hashes':{str(self.source):sha(self.source)}})
        atomic_json(self.preview/'manifest.json',files_manifest(self.preview))
        trial.initialize(self.preview,self.out)
        FakeClient.actions=[];FakeClient.dispatched=[];FakeClient.counter=0;FakeClient.tick=None
        self.addCleanup(setattr,FakeClient,'tick',None)
        idle=patch('probe.paired_trial.converter_idle',return_value={'owned_converter_pids':[]});idle.start();self.addCleanup(idle.stop)
    def ready(self,root,out,factory):
        p=out/'readiness'/str(FakeClient.counter);(p/'model').mkdir(parents=True,exist_ok=True)
        atomic_json(p/'model/capabilities.json',{'fixture':'passed'})
        return {'path':str(p),'capabilities_sha256':sha(p/'model/capabilities.json')}
    def run_trial(self,**kwargs):
        with patch('builtins.print'):
            return trial.execute(self.root,self.out,client_factory=FakeClient,ready=self.ready,**kwargs)
    def state(self):return read_json(self.out/'state.json')
    def test_completed_resume_never_repeats_and_no_cross_arm_history(self):
        self.assertEqual(self.run_trial(),0);self.assertEqual(len(FakeClient.dispatched),26)
        self.assertTrue(self.state()['gate']['passed'])
        self.run_trial();self.assertEqual(len(FakeClient.dispatched),26)
        self.assertTrue(all(len(p['messages'])==1 for p in FakeClient.dispatched))
        self.assertEqual(report.aggregate(report.collect(self.out)[2])['overall']['matched_completed_pairs'],13)
        export=report.critic(self.preview,report.collect(self.out)[2])
        self.assertNotIn('flagged',json.dumps(export));self.assertNotIn('source_assessment',json.dumps(export))
    def test_reliability_failure_is_persistent_and_stops_after_twelve_pairs(self):
        FakeClient.actions=['json']*4+['ok']*2+['schema']*4+['ok']*20
        self.run_trial();self.assertEqual(len(FakeClient.dispatched),24)
        self.assertEqual(self.state()['status'],'paused_reliability')
        decision=self.state()['gate'];self.run_trial();self.assertEqual(self.state()['gate'],decision)
        self.assertEqual(len(FakeClient.dispatched),24)
    def test_nine_each_arm_required_not_combined_count(self):
        state=self.state()
        for s in self.order[:12]:
            for a in ('A','B'):state['requests'][f"{s['ordinal']:03d}-{a}"]={'status':'completed'}
        for n in range(1,5):state['requests'][f'{n:03d}-A']={'status':'failed'}
        self.assertFalse(trial.reliability(state,self.order)['passed'])
        state['requests']['004-A']={'status':'completed'}
        self.assertTrue(trial.reliability(state,self.order)['passed'])
    def test_interrupt_consumes_arm_and_resume_continues_pending_only(self):
        FakeClient.actions=['ok','crash'];self.run_trial()
        self.assertEqual(self.state()['requests']['001-B']['status'],'interrupted')
        self.run_trial();self.assertEqual(len(FakeClient.dispatched),26)
        self.assertEqual(self.state()['requests']['001-B']['status'],'interrupted')
    def test_two_transport_failures_pause_without_retries(self):
        FakeClient.actions=['transport','timeout'];self.run_trial()
        self.assertEqual(len(FakeClient.dispatched),2);self.assertEqual(self.state()['status'],'paused_connection')
        self.run_trial();self.assertEqual(len(FakeClient.dispatched),26)
        self.assertEqual(read_json(self.out/'requests/001-B/outcome.json')['failure_kind'],'timeout')
    def test_identity_and_rejected_option_stop_without_silent_fallback(self):
        FakeClient.actions=['identity'];self.run_trial();self.assertEqual(self.state()['status'],'stopped_identity')
        self.run_trial();self.assertEqual(len(FakeClient.dispatched),1)
    def test_rejected_option_stops(self):
        FakeClient.actions=['option'];self.run_trial();self.assertEqual(self.state()['status'],'stopped_configuration')
        self.assertEqual(len(FakeClient.dispatched),1)
    def test_token_exhaustion_is_saved_and_never_retried(self):
        FakeClient.actions=['length'];self.run_trial()
        self.assertEqual(read_json(self.out/'requests/001-A/outcome.json')['failure_kind'],'token_limit')
        self.assertEqual(len(FakeClient.dispatched),26)
    def test_deadline_current_request_finishes_no_next_admission(self):
        state=self.state();state['elapsed_seconds']=32399;atomic_json(self.out/'state.json',state)
        t=[0.0];FakeClient.tick=lambda:t.__setitem__(0,t[0]+600)
        self.run_trial(clock=lambda:t[0]);self.assertEqual(len(FakeClient.dispatched),1)
        self.assertEqual(self.state()['status'],'budget_exhausted');self.assertEqual(self.state()['elapsed_seconds'],32999)
        self.run_trial();self.assertEqual(len(FakeClient.dispatched),1)
    def test_exhausted_budget_avoids_even_readiness(self):
        state=self.state();state['elapsed_seconds']=32400;atomic_json(self.out/'state.json',state)
        with patch.object(self,'ready',side_effect=AssertionError('No readiness after budget')):self.run_trial()
        self.assertFalse(FakeClient.dispatched)
    def test_crash_elapsed_time_conservatively_retained(self):
        state=self.state();state['elapsed_seconds']=32390;state['active_since_epoch']=100;atomic_json(self.out/'state.json',state)
        self.run_trial(wall=lambda:120);self.assertEqual(self.state()['status'],'budget_exhausted');self.assertFalse(FakeClient.dispatched)
    def test_source_preview_and_completed_attempt_mutations_refused(self):
        self.source.write_text('changed');self.run_trial()
        self.assertEqual(self.state()['status'],'stopped_integrity');self.assertFalse(FakeClient.dispatched)
    def test_completed_attempt_tamper_refused(self):
        FakeClient.actions=['ok','transport','transport'];self.run_trial()
        p=self.out/'requests/001-A/assistant-response.json';p.write_text('{}')
        count=len(FakeClient.dispatched);self.run_trial()
        self.assertEqual(self.state()['status'],'stopped_integrity');self.assertEqual(len(FakeClient.dispatched),count)
    def test_changed_prepared_request_refuses_before_dispatch(self):
        p=self.preview/'regions/001/A.json';p.write_text('{}');self.run_trial()
        self.assertEqual(self.state()['status'],'stopped_integrity');self.assertFalse(FakeClient.dispatched)
    def test_partial_bundle_excludes_raw_reasoning_and_keeps_full_ledger(self):
        FakeClient.actions=['transport','timeout'];self.run_trial()
        with patch('builtins.print'):b=report.bundle(self.root,self.out)
        import zipfile
        with zipfile.ZipFile(b['path']) as z:
            self.assertIsNone(z.testzip());self.assertFalse(any('response.raw' in n or '/requests/' in n for n in z.namelist()))
            ledger=json.loads(z.read(self.out.name+'/ledger.json'));self.assertEqual(len(ledger),13)
        self.assertEqual(b['bytes'],Path(b['path']).stat().st_size)
    def test_failure_usage_and_coverage_are_retained(self):
        FakeClient.actions=['json','coverage'];self.run_trial()
        first=read_json(self.out/'requests/001-A/outcome.json')
        second=read_json(self.out/'requests/001-B/outcome.json')
        self.assertEqual(first['failure_kind'],'json');self.assertEqual(first['usage']['completion_tokens'],10)
        self.assertEqual(second['failure_kind'],'coverage')
        self.assertEqual(report.aggregate(report.collect(self.out)[2])['overall']['arms']['A']['usage']['completion_tokens'],130)

    def test_recover_fatal_identity_from_interrupted_raw_record(self):
        dest=self.out/'requests/001-A';dest.mkdir(parents=True)
        atomic_json(dest/'reservation.json',{'key':'001-A','request_sha256':sha(self.preview/'regions/001/A.json')})
        atomic_json(dest/'attempts/raw/record.json',{'actual_model':'different','http_status':200})
        self.run_trial();self.assertEqual(self.state()['status'],'stopped_identity');self.assertFalse(FakeClient.dispatched)


class ReadinessTests(unittest.TestCase):
    def test_fresh_preflight_requires_both_text_and_vision_and_exact_identity(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);atomic_json(root/'fixtures/vision/manifest.json',[])
            caps={'selected_model':inputs.CONFIG['model'],'model_discovery':{'status':'passed'},
                  'text':{'status':'passed'},'vision':{'status':'qualified'},'strict_json':{'status':'unsupported'}}
            def probe(client,folder,cases):
                atomic_json(folder/'capabilities.json',caps)
                return caps
            with patch('probe.paired_trial.converter_idle',return_value={}),patch('probe.paired_trial.probe_model',side_effect=probe),patch('builtins.print'):
                result=trial.readiness(root,root/'live',FakeClient)
                self.assertTrue(Path(result['path']).exists());self.assertEqual(result['strict_json'],'unsupported')
                caps['vision']['status']='failed'
                with self.assertRaisesRegex(RuntimeError,'Text: passed AND vision: qualified'):trial.readiness(root,root/'live',FakeClient)
                caps['vision']['status']='qualified';caps['text']['status']='failed'
                with self.assertRaises(RuntimeError):trial.readiness(root,root/'live',FakeClient)
                caps['text']['status']='passed';caps['selected_model']='different'
                with self.assertRaisesRegex(RuntimeError,'exact alias'):trial.readiness(root,root/'live',FakeClient)

    def test_converter_process_gate_precedes_preflight_calls(self):
        with tempfile.TemporaryDirectory() as td:
            with patch('probe.paired_trial.converter_idle',side_effect=ValueError('OCR active')),patch('probe.paired_trial.probe_model') as probe:
                with self.assertRaisesRegex(ValueError,'OCR active'):trial.readiness(Path(td),Path(td)/'live',FakeClient)
                probe.assert_not_called()


if __name__=='__main__':unittest.main()
