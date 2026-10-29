"""Offline frozen continuation: actual scheduler, mock HTTP serialization, no sockets."""
import copy
import json
from datetime import datetime,timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from probe import critic_overnight as co, experiment as ex, text_critic as tc
from probe.common import atomic_json,read_json,sha,files_manifest
from probe.recovery_trial import save_unit,finish_preview
from probe.batch_review import IntegrityError
from test_critic_followup import passage,CriticClient


class OvernightTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.old=self.root/'old';self.op=self.root/'old-input';self.op.mkdir();self.gate=self.root/'gate';self.gp=self.root/'gate-input';self.gp.mkdir()
        config={**tc.PROFILES['deepseek'],'max_tokens':32768,'timeout':900,'stream':False,'lower_reasoning_supported':False,'sampling':'server defaults omitted'}
        units=[]
        for n in range(1,21):
            for version in ('X','Y'):
                d=passage(f'g{n:02d}');units.append(save_unit(self.op,f'g{n:02d}-{version}',d,tc.request(d),kind='critic',gate=n<5,
                    split='development' if n<=10 else 'reserved',version='baseline' if version=='X' else 'candidate',
                    location={'page':co.PAGES.get(n,1),'blocks':['p:b1']},unavailable=co.UNAVAILABLE if (n,version)==(16,'Y') else None))
        gate={'minimum_first':6,'minimum_final':8,'minimum_coverage':6,'frozen_before_live':True}
        finish_preview(self.op,units,'critic',{**config,'max_tokens':16384,'timeout':600},{},{'baseline_calls':40,'recovery_calls':24,'per_parent_recovery':2,'admission_seconds':14400},gate,{})
        ex.initialize(self.op,self.old)
        gu=[]
        for u in units[:8]:
            d=read_json(self.op/u['data']);gu.append(save_unit(self.gp,u['id'],d,tc.request(d,max_tokens=32768),**{k:v for k,v in u.items() if k not in ('id','request','data')}))
        atomic_json(self.gp/'lineage.json',{'parent_run':str(self.old),'parent_preview_manifest_sha256':sha(self.op/'manifest.json')})
        finish_preview(self.gp,gu,'critic',{**config,'diagnostic_followup_only':True},{},{'baseline_calls':8,'recovery_calls':8,'per_parent_recovery':2,'admission_seconds':14400},gate,{})
        ex.initialize(self.gp,self.gate)
        self.idle=patch('probe.experiment.converter_idle',return_value={'owned_converter_pids':[]});self.idle.start();self.addCleanup(self.idle.stop)
        self.reset_client();gr=self.ready(self.gp,'gate-ready')
        with patch('builtins.print'):ex.execute(self.root,self.gate,stage='gate',readiness=gr,client_factory=CriticClient)
        self.zip=self.root/'gate.zip'
        with zipfile.ZipFile(self.zip,'x') as z:z.write(self.gate/'state.json','state.json')
        self.p=self.root/'input';self.r=self.root/'run';self.reset_client()

    def reset_client(self):
        CriticClient.counter=0;CriticClient.actions=[];CriticClient.sent=[];CriticClient.timeouts=[]

    def ready(self,preview,name='ready'):
        d=self.root/name;d.mkdir();atomic_json(d/'readiness.json',{'config':read_json(preview/'preview.json')['config'],'finished_at':ex.now(),'text':'passed','vision':'not_requested_text_only'});ex.seal(d);return d

    def prepare(self):
        co.prepare(self.gate,self.old,self.zip,self.p,self.r);self.readiness=self.ready(self.p)

    def run_job(self,**kw):
        with patch('builtins.print'):return ex.execute(self.root,self.r,stage='overnight',readiness=self.readiness,client_factory=CriticClient,**kw)

    def test_frozen_inputs_cohort_lineage_and_successful_two_stages(self):
        before={str(p):files_manifest(p) for p in (self.gate,self.gp,self.old,self.op)};self.prepare()
        units=read_json(self.p/'units.json');self.assertEqual(len(units),32)
        for u in units:
            self.assertEqual((self.p/u['data']).read_bytes(),(self.op/u['data']).read_bytes())
            body=read_json(self.p/u['request']);self.assertEqual(body,tc.request(read_json(self.p/u['data']),max_tokens=32768))
        self.run_job();s=read_json(self.r/'state.json');self.assertEqual(len(s['calls']),31)
        self.assertEqual([c['parent'] for c in s['calls']],[u['id'] for u in units if not u.get('unavailable')]);self.assertTrue(s['gate']['passed'])
        self.assertEqual(s['gate']['units'],12);self.assertEqual(s['units']['g16-Y']['status'],'unavailable')
        summary=co.reports(self.p,self.r);self.assertEqual(summary['stages']['reserved']['available_pairs'],9)
        self.assertEqual(summary['stages']['reserved']['planned_slots'],20);self.assertEqual(summary['stages']['reserved']['callable_slots'],19)
        self.assertEqual(summary['stages']['reserved']['unpaired_callable_units'],['g16-X'])
        self.assertEqual(summary['usage_accounting']['all']['calls'],31)
        self.assertEqual({str(p):files_manifest(p) for p in (self.gate,self.gp,self.old,self.op)},before)
        with patch('builtins.print'):record=co.bundle(self.root,self.p,self.r)
        with zipfile.ZipFile(record['path']) as z:
            self.assertIsNone(z.testzip());self.assertIn('overnight/reserved.html',z.namelist());self.assertIn('prepared/units/g16-Y/input.json',z.namelist())

    def test_failed_checkpoint_never_dispatches_reserved(self):
        self.prepare();CriticClient.actions=['length']+['ok']*11
        self.run_job();s=read_json(self.r/'state.json');self.assertEqual(s['status'],'gate_failed');self.assertEqual(len(s['calls']),12)
        self.assertFalse(s['gate']['passed']);self.assertEqual(s['units']['g11-X']['status'],'pending')
        self.run_job(resume=True);self.assertEqual(len(CriticClient.sent),12)

    def test_first_attempt_threshold_not_just_final_valid(self):
        self.prepare();CriticClient.actions=['bad','ok']*4+['ok']*8
        self.run_job();s=read_json(self.r/'state.json');self.assertEqual(s['gate']['final_valid'],12)
        self.assertEqual(s['gate']['first_attempt_valid'],8);self.assertFalse(s['gate']['passed']);self.assertEqual(len(s['calls']),16)
        self.assertEqual(co.reports(self.p,self.r)['usage_accounting']['all']['calls'],16)

    def test_insufficient_context_is_valid_but_not_complete_coverage(self):
        self.prepare();original=CriticClient._request
        def context(client,*args,**kwargs):
            raw,ev=original(client,*args,**kwargs)
            if args[0]=='POST' and len(CriticClient.sent)<=4:
                v=json.loads(raw['choices'][0]['message']['content']);v.update(coverage='insufficient_context',context_needed=['Earlier definition needed'])
                raw['choices'][0]['message']['content']=json.dumps(v)
                atomic_json(Path(ev['attempt_dir'])/'response.raw',raw)
            return raw,ev
        with patch.object(CriticClient,'_request',context):self.run_job()
        s=read_json(self.r/'state.json');self.assertEqual(s['gate']['final_valid'],12)
        self.assertEqual(s['gate']['complete_claimed_coverage'],8);self.assertFalse(s['gate']['passed'])
        self.assertEqual(len(CriticClient.sent),12)

    def test_cannot_launch_reserved_directly_or_mutate_sealed_inputs(self):
        self.prepare()
        for stage in ('gate','development','reserved','continue'):
            with self.assertRaisesRegex(ValueError,'overnight controller'):ex.execute(self.root,self.r,stage=stage,readiness=self.readiness,client_factory=CriticClient)
        p=self.p/'units/g11-X/request.json';body=read_json(p);body['max_tokens']=100;atomic_json(p,body)
        with self.assertRaises(IntegrityError):self.run_job()
        self.assertFalse(CriticClient.sent)

    def test_between_stage_mutation_stops_before_reserved(self):
        self.prepare();original=CriticClient._request
        def mutate(client,*args,**kwargs):
            result=original(client,*args,**kwargs)
            if len(CriticClient.sent)==12:
                p=self.p/'units/g11-X/input.json';p.write_text(p.read_text()+' ')
            return result
        with patch.object(CriticClient,'_request',mutate):self.run_job()
        s=read_json(self.r/'state.json');self.assertEqual(s['status'],'stopped_integrity');self.assertEqual(len(s['calls']),12)

    def test_pause_checkpoint_resume_and_original_call_limits(self):
        self.prepare();original=CriticClient._request
        def pause(client,*args,**kwargs):
            result=original(client,*args,**kwargs)
            if args[0]=='POST':(self.r/'PAUSE').touch()
            return result
        CriticClient.actions=['bad']
        with patch.object(CriticClient,'_request',pause):self.run_job()
        (self.r/'PAUSE').unlink();CriticClient.actions=['drop','drop']+['ok']*11
        self.run_job(resume=True);s=read_json(self.r/'state.json')
        self.assertEqual(len([c for c in s['calls'] if c['parent']=='g05-X']),3);self.assertFalse(s['gate']['passed'])
        self.assertFalse(any(c['parent'].startswith('g11') for c in s['calls']))

    def test_deadline_includes_controlled_pause_and_resume(self):
        self.prepare();original=CriticClient._request
        def pause(client,*args,**kwargs):
            result=original(client,*args,**kwargs)
            if args[0]=='POST':(self.r/'PAUSE').touch()
            return result
        epoch=datetime.now(timezone.utc).timestamp()
        with patch.object(CriticClient,'_request',pause):self.run_job(wall=lambda:epoch)
        (self.r/'PAUSE').unlink();self.run_job(resume=True,wall=lambda:epoch+28801)
        s=read_json(self.r/'state.json');self.assertEqual(s['status'],'budget_exhausted');self.assertEqual(len(s['calls']),1)
        self.assertGreaterEqual(s['elapsed_seconds'],28801)

    def test_inflight_finishes_but_no_dispatch_after_deadline(self):
        self.prepare();original=CriticClient._request;epoch=[datetime.now(timezone.utc).timestamp()]
        def slow(client,*args,**kwargs):
            value=original(client,*args,**kwargs)
            if args[0]=='POST':epoch[0]+=28801
            return value
        with patch.object(CriticClient,'_request',slow):self.run_job(wall=lambda:epoch[0])
        s=read_json(self.r/'state.json');self.assertEqual(s['status'],'budget_exhausted')
        self.assertEqual(len(s['calls']),1);self.assertEqual(s['calls'][0]['status'],'completed')

    def test_global_recovery_cap_shared_across_stages_and_resumes(self):
        self.prepare();original=CriticClient._request
        def pause(client,*args,**kwargs):
            result=original(client,*args,**kwargs)
            if len(CriticClient.sent)==15:(self.r/'PAUSE').touch()
            return result
        # 3 development repairs pass 9/12 first-valid. Then 13 reserved repairs consume the remainder.
        CriticClient.actions=['bad','ok']*3+['ok']*9
        with patch.object(CriticClient,'_request',pause):self.run_job()
        (self.r/'PAUSE').unlink();CriticClient.actions=['bad','ok']*13+['bad']*6
        self.run_job(resume=True);s=read_json(self.r/'state.json')
        self.assertEqual(sum(c['method']!='baseline' for c in s['calls']),16)
        self.assertEqual(sum(c['method']=='baseline' for c in s['calls']),31)
        self.assertEqual(len(s['calls']),47);self.assertTrue(s['gate']['passed'])
        self.assertEqual(s['units']['g16-Y']['status'],'unavailable')
        self.assertEqual(co.reports(self.p,self.r)['usage_accounting']['all']['calls'],47)

    def test_unexpected_selection_or_changed_successful_prompt_rejected(self):
        meta=read_json(self.gp/'preview.json');meta['code_sha256']['text_critic.py']='changed'
        # Historical consistency checks must fail rather than silently refresh old evidence.
        atomic_json(self.gp/'preview.json',meta)
        with self.assertRaises(IntegrityError):self.prepare()


if __name__=='__main__':unittest.main()
