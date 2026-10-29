"""DeepSeek-only regression checks; synthetic clients, no live sockets/services."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from probe.common import atomic_json, files_manifest, fingerprint, read_json, sha
from probe import deepseek_inputs as di, deepseek_trial as dt, deepseek_report as dr
from probe import paired_inputs as qi
from probe.local_model import LocalClient, ProbeError
from probe.batch_review import IdentityError, IntegrityError
from test_paired_trial import data,valid


def smoke():
    return {'status':'passed','model':di.CONFIG['model'],'base_url':di.CONFIG['endpoint'],'image_id':di.IMAGE,
            'text':'passed','vision':'simple_digits_and_blank_passed','mathematical_ocr_qualified':False}


class FakeClient(LocalClient):
    actions=[];sent=[];counter=0;tick=None;models=[di.CONFIG['model']];methods=[]
    def _request(self,method,endpoint,payload,output_dir,label):
        FakeClient.methods.append((method,endpoint));folder=Path(output_dir)/'attempts'/str(FakeClient.counter)
        FakeClient.counter+=1;folder.mkdir(parents=True)
        atomic_json(folder/'request.json',{'body':payload});atomic_json(folder/'record.json',{'http_status':200,'latency_seconds':1})
        evidence={'attempt_dir':str(folder),'http_status':200,'latency_seconds':1}
        if method=='GET':return {'data':[{'id':x} for x in FakeClient.models]},evidence
        FakeClient.sent.append(payload)
        if FakeClient.tick:FakeClient.tick()
        action=FakeClient.actions.pop(0) if FakeClient.actions else 'ok'
        if action=='crash':raise KeyboardInterrupt()
        if action in ('transport','timeout','option','wrong400'):
            status=400 if action in ('option','wrong400') else None
            atomic_json(folder/'record.json',{'http_status':status,'latency_seconds':1})
            if action=='wrong400':(folder/'response.raw').write_text(json.dumps({'model':'wrong','error':'bad option'}))
            raise ProbeError('timed out' if action=='timeout' else 'failed',attempt_dir=folder,status=status)
        d=json.loads(payload['messages'][0]['content'][0]['text'].split('SELECTED DATA:\n')[1]);v=valid(d)
        if action=='coverage':v['reviewed_block_ids']=[]
        if action=='schema':v['extra']=1
        obj={'model':'wrong' if action=='identity' else di.CONFIG['model'],'choices':[{'finish_reason':'length' if action=='length' else 'stop',
            'message':{'content':'```bad```' if action=='json' else json.dumps(v),'reasoning_content':'REASONING_NOT_FOR_BUNDLE'}}],
            'usage':{'completion_tokens':10}}
        (folder/'response.raw').write_text(json.dumps(obj));return obj,evidence


class ValidationTests(unittest.TestCase):
    def test_model_endpoint_separation_and_actual_serialization(self):
        original=copy.deepcopy(qi.CONFIG);q=qi.request(data(),'native',[],'A');d={**q,'model':di.CONFIG['model']}
        self.assertEqual({**d,'model':q['model']},q);self.assertEqual(qi.CONFIG,original)
        self.assertNotEqual(di.CONFIG['endpoint'],qi.CONFIG['endpoint'])
        with tempfile.TemporaryDirectory() as td:
            c=FakeClient(di.CONFIG['endpoint'],model=di.CONFIG['model'],purpose='page_review',max_tokens=16384,timeout=600)
            c.model=di.CONFIG['model'];answer=c.chat(d['messages'],Path(td),'test',reasoning_effort='medium')
            self.assertEqual(read_json(Path(answer['attempt_dir'])/'request.json')['body'],d)
            self.assertEqual(di.validate_answer(answer,data()),valid(data()))
            with self.assertRaises(IdentityError):qi.validate_answer(answer,data())
        self.assertEqual(qi.CONFIG,original)
    def test_invalid_json_coverage_identity_and_tex_safeguards(self):
        answer={'actual_model':di.CONFIG['model'],'finish_reason':'stop','content':json.dumps(valid(data()))}
        for text in ('```json {} ```','{"x":1,"x":2}'):
            with self.assertRaises(ValueError):di.validate_answer({**answer,'content':text},data())
        with self.assertRaises(IdentityError):di.validate_answer({**answer,'actual_model':qi.CONFIG['model']},data())
        v=valid(data());v['reviewed_block_ids']=[]
        with self.assertRaises(ValueError):di.validate_answer({**answer,'content':json.dumps(v)},data())
        checks=di.latex_checks({'proposals':[{'suggested_latex':r'\input{/etc/passwd}'},{'suggested_latex':''},{'suggested_latex':'A sentence.'}]})
        self.assertEqual(checks[0]['status'],'unsupported_export_blocked');self.assertFalse(any(c['accepted'] for c in checks))
    def test_exact_full_order_required(self):
        order=[{'ordinal':n,'region_id':str(n),'page_id':str(n%16)} for n in range(1,268)]
        di.validate_order(order)
        for bad in (order[:-1],list(reversed(order)),order[:-1]+[order[0]]):
            with self.assertRaises(IntegrityError):di.validate_order(bad)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
        self.preview=self.root/'preview';self.preview.mkdir();self.out=self.root/'live';self.source=self.root/'original';self.source.write_text('unchanged')
        self.qwen=self.root/'qwen';self.order=[]
        for n in range(1,14):
            key=f'{n:03d}';folder=self.preview/'regions'/key;folder.mkdir(parents=True);d=data(n)
            original=self.root/'historical'/key/'A.json';q=qi.request(d,'native',[],'A');atomic_json(original,q)
            atomic_json(folder/'request.json',{**q,'model':di.CONFIG['model']});atomic_json(folder/'input.json',d)
            qfolder=self.qwen/'requests'/(key+'-A');atomic_json(qfolder/'outcome.json',{'status':'completed','answer':valid(d)})
            self.order.append({'ordinal':n,'region_id':f'p001:b{n}','page_id':'p001','page':d['page'],'phase':'priority','printed_page':91,
                'printed_page_basis':'synthetic','historical_request':str(original),'historical_sha256':sha(original),
                'new_sha256':sha(folder/'request.json'),'input_sha256':sha(folder/'input.json')})
        atomic_json(self.qwen/'state.json',{'requests':{f'{n:03d}-A':{'status':'completed'} for n in range(1,14)}})
        atomic_json(self.preview/'order.json',self.order)
        atomic_json(self.preview/'preview.json',{'config':di.CONFIG,'policy':di.POLICY,'image_id':di.IMAGE,'code_sha256':di.code_hashes(),
                    'source_hashes':{str(self.source):sha(self.source)},'historical_run':str(self.qwen)})
        di.seal(self.preview)
        size=patch('probe.deepseek_inputs.validate_order');size.start();self.addCleanup(size.stop)
        dt.initialize(self.preview,self.out)
        FakeClient.actions=[];FakeClient.sent=[];FakeClient.counter=0;FakeClient.tick=None;FakeClient.models=[di.CONFIG['model']];FakeClient.methods=[]
        self.addCleanup(setattr,FakeClient,'tick',None)
        idle=patch('probe.deepseek_trial.converter_idle',return_value={'owned_converter_pids':[]});idle.start();self.addCleanup(idle.stop)
    def ready(self,root,out,factory,deployment,wait):
        p=root/'deployment';p.mkdir(exist_ok=True);atomic_json(p/'SMOKE-PASS.json',smoke())
        dt.deployment_path(out,p);atomic_json(out/'deployment-binding.json',{'path':str(p),'smoke_sha256':sha(p/'SMOKE-PASS.json')})
        r=out/'readiness'/str(FakeClient.counter);atomic_json(r/'model/capabilities.json',{'fixture':'passed'})
        return {'path':str(r),'capabilities_sha256':sha(r/'model/capabilities.json')}
    def run_trial(self,**kwargs):
        with patch('builtins.print'):return dt.execute(self.root,self.out,client_factory=FakeClient,ready=self.ready,**kwargs)
    def state(self):return read_json(self.out/'state.json')
    def test_complete_explicit_resume_never_repeats_and_original_preserved(self):
        before=files_manifest(self.qwen);self.assertEqual(self.run_trial(),0);self.assertEqual(len(FakeClient.sent),13)
        with self.assertRaisesRegex(ValueError,'explicit --resume'):self.run_trial()
        self.run_trial(resume=True);self.assertEqual(len(FakeClient.sent),13);self.assertEqual(files_manifest(self.qwen),before)
        self.assertTrue(all(len(b['messages'])==1 and 'response_format' not in b for b in FakeClient.sent))
    def test_gate_failure_persists_after_first_twelve(self):
        FakeClient.actions=['json']*4;self.run_trial();self.assertEqual(len(FakeClient.sent),12)
        self.assertEqual(self.state()['status'],'paused_reliability');self.assertEqual(self.state()['gate']['valid_responses'],8)
        self.run_trial(resume=True);self.assertEqual(len(FakeClient.sent),12)
    def test_nine_gate_passes_without_repeating_twelve(self):
        FakeClient.actions=['schema']*3;self.run_trial();self.assertEqual(len(FakeClient.sent),13);self.assertTrue(self.state()['gate']['passed'])
    def test_interrupt_consumes_request(self):
        FakeClient.actions=['ok','crash'];self.run_trial();self.assertEqual(self.state()['requests']['002']['status'],'interrupted')
        self.run_trial(resume=True);self.assertEqual(len(FakeClient.sent),13)
    def test_crash_error_identity_and_serialization_checked_before_readiness(self):
        dest=self.out/'requests/001';body=read_json(self.preview/'regions/001/request.json')
        atomic_json(dest/'reservation.json',{'key':'001','request_sha256':sha(self.preview/'regions/001/request.json')})
        atomic_json(dest/'request.json',body)
        atomic_json(dest/'attempts/error/request.json',{'body':body})
        atomic_json(dest/'attempts/error/record.json',{'http_status':400})
        atomic_json(dest/'attempts/error/response.raw',{'model':'wrong','error':'bad option'})
        with patch.object(self,'ready',side_effect=AssertionError('No readiness after wrong model')):self.run_trial()
        self.assertEqual(self.state()['status'],'stopped_identity');self.assertEqual(self.state()['counts']['failed'],1)
        # Even an uncommitted serialization discrepancy must stop without dispatch.
        atomic_json(dest/'attempts/error/request.json',{'body':{**body,'max_tokens':1}})
        self.run_trial(resume=True);self.assertEqual(self.state()['status'],'stopped_integrity');self.assertFalse(FakeClient.sent)
    def test_two_connections_pause_then_skip_failures(self):
        FakeClient.actions=['transport','timeout'];self.run_trial();self.assertEqual(self.state()['status'],'paused_connection')
        self.run_trial(resume=True);self.assertEqual(len(FakeClient.sent),13)
    def test_identity_stops_valid_response(self):
        FakeClient.actions=['identity'];self.run_trial();self.assertEqual(self.state()['status'],'stopped_identity');self.assertEqual(len(FakeClient.sent),1)
    def test_identity_stops_failed_http_response(self):
        FakeClient.actions=['wrong400'];self.run_trial();self.assertEqual(self.state()['status'],'stopped_identity')
    def test_option_rejection_no_fallback(self):
        FakeClient.actions=['option'];self.run_trial();self.assertEqual(self.state()['status'],'stopped_configuration')
    def test_length_usage_retained_no_retry(self):
        FakeClient.actions=['length'];self.run_trial();r=read_json(self.out/'requests/001/outcome.json')
        self.assertEqual(r['failure_kind'],'token_limit');self.assertEqual(r['usage']['completion_tokens'],10);self.assertEqual(len(FakeClient.sent),13)
    def test_eight_hour_admission_and_final_request_timeout(self):
        s=self.state();s['elapsed_seconds']=28799;atomic_json(self.out/'state.json',s);t=[0]
        FakeClient.tick=lambda:t.__setitem__(0,t[0]+600)
        self.run_trial(clock=lambda:t[0]);self.assertEqual(len(FakeClient.sent),1);self.assertEqual(self.state()['elapsed_seconds'],29399)
        self.run_trial(resume=True);self.assertEqual(len(FakeClient.sent),1)
    def test_exhausted_budget_skips_readiness(self):
        s=self.state();s['elapsed_seconds']=28800;atomic_json(self.out/'state.json',s)
        with patch.object(self,'ready',side_effect=AssertionError('No live readiness')):self.run_trial()
        self.assertEqual(self.state()['status'],'budget_exhausted')
    def test_crash_downtime_charged(self):
        s=self.state();s.update(elapsed_seconds=28790,active_since_epoch=100);atomic_json(self.out/'state.json',s)
        self.run_trial(wall=lambda:120);self.assertEqual(self.state()['status'],'budget_exhausted')
    def test_stale_sources_and_exact_request_equality(self):
        p=self.preview/'regions/001/request.json';body=read_json(p);body['messages'].append({'role':'assistant','content':'LEAK'})
        atomic_json(p,body)
        with self.assertRaises(IntegrityError):di.verify_preview(self.preview)
        self.run_trial();self.assertFalse(FakeClient.sent);self.assertEqual(self.state()['status'],'stopped_integrity')
    def test_completed_attempt_change_refused(self):
        FakeClient.actions=['ok','transport','transport'];self.run_trial()
        (self.out/'requests/001/assistant-response.json').write_text('{}')
        self.run_trial(resume=True);self.assertEqual(self.state()['status'],'stopped_integrity');self.assertEqual(len(FakeClient.sent),3)
    def test_report_raw_reasoning_exclusion_and_failed_final_answer(self):
        FakeClient.actions=['json','transport','timeout'];self.run_trial()
        self.assertTrue(dr.collect(self.out)[2][0]['deepseek']['final_answer_available'])
        with patch('builtins.print'):b=dr.bundle(self.root,self.out)
        import zipfile
        with zipfile.ZipFile(b['path']) as z:
            self.assertIsNone(z.testzip())
            self.assertNotIn(b'REASONING_NOT_FOR_BUNDLE',b''.join(z.read(n) for n in z.namelist()))
            self.assertEqual(len(json.loads(z.read(self.out.name+'/ledger.json'))),13)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);self.out=self.root/'out';self.out.mkdir();self.dep=self.root/'deploy';self.dep.mkdir()
        atomic_json(self.dep/'SMOKE-PASS.json',smoke());dt.deployment_path(self.out,self.dep)
        FakeClient.counter=0;FakeClient.models=[di.CONFIG['model']];FakeClient.methods=[]
    def test_smoke_binding_wait_is_get_only_and_resume_path_pinned(self):
        dt.wait_for_deployment(self.out,self.dep,self.out/'ready',0,FakeClient)
        self.assertEqual(FakeClient.methods,[('GET','/models')]);dt.verify_deployment(self.out)
        with self.assertRaises(IntegrityError):dt.deployment_path(self.out,self.root/'other')
        v=smoke();v['image_id']='different';atomic_json(self.dep/'SMOKE-PASS.json',v)
        with self.assertRaises(IntegrityError):dt.verify_deployment(self.out)
    def test_stop_and_different_advertised_model_never_wait(self):
        FakeClient.models=['other']
        with self.assertRaises(IdentityError):dt.wait_for_deployment(self.out,self.dep,self.out/'ready',3600,FakeClient)
        atomic_json(self.dep/'STOP.json',{'reason':'stop'})
        before=len(FakeClient.methods)
        with self.assertRaises(IntegrityError):dt.wait_for_deployment(self.out,self.dep,self.out/'ready',3600,FakeClient)
        self.assertEqual(len(FakeClient.methods),before)
    def test_wait_smoke_missing_bounded_no_post(self):
        (self.dep/'SMOKE-PASS.json').unlink();t=[0]
        with self.assertRaisesRegex(RuntimeError,'not both ready'):
            dt.wait_for_deployment(self.out,self.dep,self.out/'ready',6,FakeClient,clock=lambda:t[0],sleep=lambda n:t.__setitem__(0,t[0]+n))
        self.assertEqual(t[0],6);self.assertTrue(all(m=='GET' for m,e in FakeClient.methods))
    def test_fresh_project_preflight_not_replaced_by_smoke(self):
        atomic_json(self.root/'fixtures/vision/manifest.json',[])
        caps={'model_discovery':{'selected_model':di.CONFIG['model'],'available_models':[di.CONFIG['model']]},'text':{'status':'passed'},'vision':{'status':'qualified'},'strict_json':{'status':'unsupported'}}
        def preflight(client,folder,cases):atomic_json(folder/'capabilities.json',caps);return caps
        with patch('probe.deepseek_trial.converter_idle',return_value={}),patch('probe.deepseek_trial.probe_model',side_effect=preflight) as pf:
            dt.readiness(self.root,self.out,FakeClient,self.dep,0);self.assertEqual(pf.call_count,1)
            caps['vision']['status']='failed'
            with self.assertRaises(RuntimeError):dt.readiness(self.root,self.out,FakeClient,self.dep,0)
    def test_failed_preflight_response_identity_checked(self):
        atomic_json(self.root/'fixtures/vision/manifest.json',[])
        def preflight(client,folder,cases):
            atomic_json(folder/'attempts/bad/record.json',{'http_status':400})
            atomic_json(folder/'attempts/bad/response.raw',{'model':'other','error':'bad'})
            return {'model_discovery':{},'text':{'status':'passed'},'vision':{'status':'qualified'},'strict_json':{'status':'unsupported'}}
        with patch('probe.deepseek_trial.converter_idle',return_value={}),patch('probe.deepseek_trial.probe_model',side_effect=preflight):
            with self.assertRaises(IdentityError):dt.readiness(self.root,self.out,FakeClient,self.dep,0)

if __name__=='__main__':unittest.main()
