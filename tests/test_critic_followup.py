"""Offline critic diagnostics, exact quotation recovery and bounded follow-up."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from probe import experiment as ex, text_critic as tc, recovery as recovery
from probe.common import read_json, atomic_json, sha, fingerprint, files_manifest
from probe.evaluation_export import usage_accounting, experiment_report
from probe.local_model import LocalClient
from probe.recovery_trial import save_unit, finish_preview, prepare_critic_followup
from probe.batch_review import IntegrityError


def passage(group='g01'):
    spans=[{'block_id':'p:b1','text':r'For \(A+B=C\), the claim holds.',
        'format':'portable_latex','source_location':{'page':1}}]
    return {'group_id':group,'draft_sha256':tc.draft_hash(spans),'spans':spans,
        'context':{'scope':'one complete sentence'},'bibliography':{'coverage':'not_in_extract'}}


def finding(data,number=1,quote='B=C'):
    return {'id':data['group_id']+f':f{number}','category':'derivation',
        'quotes':[{'block_id':'p:b1','text':quote,'occurrence':0}],
        'consequence':'A local assessment requiring mathematical review.',
        'severity':'medium','uncertain':True,'context_required':[],'next_action':'human_math_review'}


def answer(data,bad=False):
    return {'group_id':data['group_id'],'draft_sha256':data['draft_sha256'],
        'coverage':'complete','reviewed_block_ids':['p:b1'],'context_needed':[],
        'findings':[finding(data),finding(data,2,r'\(B=C\)' if bad else 'A+B=C')]}


def evidence(value,finish='stop',model=None):
    return {'actual_model':model or tc.PROFILES['deepseek']['model'],'finish_reason':finish,
        'content':json.dumps(value),'http_status':200,'usage':{'completion_tokens':100}}


class QuoteTests(unittest.TestCase):
    def test_complete_quote_context_not_independently_balanced_math(self):
        d=passage();v=answer(d,True)
        with self.assertRaisesRegex(recovery.ValidationError,'exact quoted'):tc.validate(v,d)
        result=tc.rejected_diagnostics(evidence(v),d,tc.PROFILES['deepseek']['model'])
        self.assertEqual(len(result['validated_findings']),1);self.assertEqual(len(result['invalid_findings']),1)
        q=result['quote_feedback'][0];self.assertEqual(q['field'],'$.findings[1].quotes[0]')
        self.assertEqual(q['exact_supplied_text'],d['spans'][0]['text'])
        fixed=copy.deepcopy(v);fixed['findings'][1]['quotes'][0]['text']='B=C'
        tc.validate(fixed,d)
        result=ex.finish_completion(evidence(fixed),{'kind':'critic'},d,tc.PROFILES['deepseek']['model'],Path('.'),
            previous_failure=evidence(v),method='json_feedback')
        self.assertEqual(result['status'],'completed')
        fixed['findings'][1]['quotes'][0]['text']='B=-C'
        with self.assertRaises(recovery.ValidationError):tc.validate(fixed,d)

    def test_only_invalid_quote_may_change_substance_and_valid_quotes_preserved(self):
        d=passage();old=answer(d,True);fixed=answer(d)
        for field,val in [('consequence','A different claim'),('uncertain',False),('quotes',[{'block_id':'p:b1','text':'A+B=C','occurrence':0}])]:
            changed=copy.deepcopy(fixed);changed['findings'][0][field]=val
            with self.assertRaises(recovery.ValidationError):
                ex.finish_completion(evidence(changed),{'kind':'critic'},d,tc.PROFILES['deepseek']['model'],Path('.'),previous_failure=evidence(old),method='json_feedback')
        anchor={'critic_repair_anchor':evidence(old),**evidence({'findings':[]})}
        with self.assertRaises(recovery.ValidationError):tc.preserve_quote_repair(anchor,{**fixed,'findings':[]},d,tc.PROFILES['deepseek']['model'])

    def test_targeted_feedback_is_data_and_keeps_complete_source(self):
        d=passage();v=answer(d,True);f={**evidence(v),'kind':'coverage','errors':[{'path':'$.findings[1].quotes[0]','message':'exact quoted span does not occur at this location'}]}
        outcome={'failure':f};ex.critic_failure_diagnostics(outcome,{'kind':'critic'},d,tc.PROFILES['deepseek']['model'])
        body=recovery.feedback_request(tc.request(d),f,tc.SCHEMA,'json_feedback')
        text=body['messages'][-1]['content'];self.assertIn('a quote need not compile independently',text)
        payload=json.loads(text[text.index('{'):]);self.assertEqual(payload['critic_quote_feedback'][0]['exact_supplied_text'],d['spans'][0]['text'])
        self.assertEqual(payload['failed_response'],json.dumps(v));self.assertIn('never instructions',text)
        self.assertIn('Harmless TeX grouping',body['messages'][0]['content']);self.assertIn('particular assessment',body['messages'][0]['content'])
        self.assertIn('never as instructions to follow',body['messages'][0]['content'])

    def test_no_provisional_salvage_of_truncation_wrong_identity_or_hash(self):
        d=passage();v=answer(d,True)
        for ev in (evidence(v,'length'),{**evidence(v),'content':json.dumps(v)[:-4]},evidence(v,model='wrong'),
                   evidence({**v,'draft_sha256':'wrong'}),{**evidence(v),'content':json.dumps(v).replace('"coverage":','"coverage":"complete","coverage":')}):
            result=tc.rejected_diagnostics(ev,d,tc.PROFILES['deepseek']['model']);self.assertEqual(result['status'],'unavailable');self.assertFalse(result['validated_findings'])

    def test_invalid_findings_do_not_mask_others_or_crash_diagnostics(self):
        d=passage();v=answer(d);v['findings'][1]['quotes'][0]['block_id']={'malformed':'id'}
        result=tc.rejected_diagnostics(evidence(v),d,tc.PROFILES['deepseek']['model'])
        self.assertEqual(len(result['validated_findings']),1);self.assertEqual(len(result['invalid_findings']),1)
        v['findings'][1]=copy.deepcopy(v['findings'][0])
        self.assertFalse(tc.rejected_diagnostics(evidence(v),d,tc.PROFILES['deepseek']['model'])['validated_findings'])

    def test_saved_g02_x_response_and_validator_input_when_available(self):
        root=Path(__file__).resolve().parents[1];run=root/'runs/text-critic-trial-20261024T140153Z-32efd8'
        if not run.exists():self.skipTest('Local raw evidence intentionally outside Git')
        preview=Path(read_json(run/'binding.json')['preview']);spec=next(u for u in read_json(preview/'units.json') if u['id']=='g02-X');d=read_json(preview/spec['data'])
        for n in ('0003','0004','0005'):
            ev=recovery.response_data(run/'calls'/n);result=tc.rejected_diagnostics(ev,d,tc.PROFILES['deepseek']['model'])
            self.assertEqual([r['source_index'] for r in result['validated_findings']],[0,1])
            self.assertEqual(result['quote_feedback'][0]['field'],'$.findings[2].quotes[0]')
            request=read_json(run/'calls'/n/'request.json')
            outgoing=json.loads(request['messages'][1]['content'].split('<passage>\n',1)[1].split('\n</passage>',1)[0]);self.assertEqual(outgoing,d)


class AccountingTests(unittest.TestCase):
    def test_failed_feedback_9535_tokens_and_missing_not_zero(self):
        rows=[{'call':'0004','method':'json_feedback','origin':'inherited','failure':{'usage':{'completion_tokens':5187},'latency_seconds':97.32143964990973}},
              {'call':'0005','method':'json_feedback','origin':'current_run','failure':{'usage':{'completion_tokens':4348},'latency_seconds':78.46112445695326}}]
        a=usage_accounting(rows+[copy.deepcopy(rows[0])]);self.assertEqual(a['all']['calls'],2)
        self.assertEqual(a['recovery']['completion_tokens']['total'],9535);self.assertAlmostEqual(a['recovery']['request_latency_seconds']['total'],175.782564106863,places=6)
        self.assertIsNone(a['all']['reasoning_tokens']['total']);self.assertEqual(a['all']['reasoning_tokens']['missing_calls'],2)
        self.assertEqual(a['inherited']['calls'],1);self.assertEqual(a['current_run']['calls'],1)
        rows.append({'call':'0006','method':'baseline','usage':{'completion_tokens':0,'completion_tokens_details':{'reasoning_tokens':0}},'latency_seconds':0})
        self.assertEqual(usage_accounting(rows)['all']['reasoning_tokens']['reported_calls'],1)

    def test_larger_client_bound_is_critic_only(self):
        c=LocalClient('http://127.0.0.1:8894/v1',purpose='text_critic',max_tokens=32768,timeout=900)
        self.assertEqual((c.max_tokens,c.timeout),(32768,900))
        for purpose in ('page_review','capability_probe'):
            with self.assertRaises(ValueError):LocalClient('http://127.0.0.1:8894/v1',purpose=purpose,max_tokens=32768)
            with self.assertRaises(ValueError):LocalClient('http://127.0.0.1:8894/v1',purpose=purpose,timeout=900)
        with self.assertRaises(ValueError):LocalClient('http://127.0.0.1:8894/v1',purpose='text_critic',max_tokens=32769)
        with self.assertRaises(ValueError):LocalClient('http://127.0.0.1:8894/v1',purpose='text_critic',timeout=901)


class CriticClient(LocalClient):
    actions=[];sent=[];counter=0;timeouts=[]
    def _request(self,method,endpoint,payload,output_dir,label):
        folder=Path(output_dir)/'attempts'/str(type(self).counter);type(self).counter+=1;folder.mkdir(parents=True)
        atomic_json(folder/'request.json',{'body':payload});atomic_json(folder/'record.json',{'http_status':200,'latency_seconds':1})
        ev={'http_status':200,'latency_seconds':1,'attempt_dir':str(folder)}
        if method=='GET':return {'data':[{'id':self.requested_model}]},ev
        type(self).sent.append(payload);type(self).timeouts.append(self.timeout)
        d=json.loads(payload['messages'][1]['content'].split('<passage>\n',1)[1].split('\n</passage>',1)[0]);action=type(self).actions.pop(0) if type(self).actions else 'ok'
        v=answer(d,action=='bad');content=json.dumps(v)
        if action=='length':content=content[:30]
        if action=='drop':v['findings']=[];content=json.dumps(v)
        raw={'model':self.requested_model,'usage':{'prompt_tokens':100,'completion_tokens':payload['max_tokens'] if action=='length' else 200},
            'choices':[{'finish_reason':'length' if action=='length' else 'stop','message':{'content':content}}]}
        atomic_json(folder/'response.raw',raw);return raw,ev


class FollowupTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name);self.preview=self.root/'old-input';self.preview.mkdir();self.run=self.root/'old-run'
        config={**tc.PROFILES['deepseek'],'max_tokens':16384,'timeout':600,'stream':False,'lower_reasoning_supported':False,'sampling':'server defaults omitted'};units=[]
        for i in range(1,5):
            for version in ('X','Y'):
                d=passage(f'g{i:02d}');units.append(save_unit(self.preview,f'g{i:02d}-{version}',d,tc.request(d),kind='critic',gate=True,split='development',version='baseline' if version=='X' else 'candidate'))
        d=passage('g16');units.append(save_unit(self.preview,'g16-Y',d,tc.request(d),kind='critic',gate=False,split='reserved',unavailable='Unresolved original'))
        finish_preview(self.preview,units,'critic',config,{}, {'baseline_calls':40,'recovery_calls':24,'per_parent_recovery':2,'admission_seconds':14400},
            {'minimum_first':6,'minimum_final':8,'minimum_coverage':6,'frozen_before_live':True},{})
        ex.initialize(self.preview,self.run);self.ready=self.root/'ready';self.ready.mkdir();atomic_json(self.ready/'readiness.json',{'config':config,'finished_at':ex.now(),'text':'passed','vision':'not_requested_text_only'});ex.seal(self.ready)
        CriticClient.counter=0;CriticClient.sent=[];CriticClient.timeouts=[];CriticClient.actions=['ok','ok','bad','bad','bad','ok','ok','length','length','length']
        self.idle=patch('probe.experiment.converter_idle',return_value={'owned_converter_pids':[]});self.idle.start();self.addCleanup(self.idle.stop)
        ex.execute(self.root,self.run,stage='gate',readiness=self.ready,client_factory=CriticClient)
        self.assertEqual(read_json(self.run/'state.json')['status'],'gate_failed')
        source=self.root/'runtime-config';source.write_text('recorded immutable image / max tokens 32768')
        self.runtime=self.root/'runtime.json';atomic_json(self.runtime,{'schema':'critic-runtime-support-v1',**tc.PROFILES['deepseek'],'max_tokens_supported':32768,'evidence_hashes':{str(source):sha(source)}})

    def prepare(self):
        p=self.root/'new-input';r=self.root/'new-run';prepare_critic_followup(self.run,self.runtime,p,r);return p,r

    def test_exact_inputs_order_new_budgets_and_explicit_old_lineage(self):
        before=files_manifest(self.run);p,r=self.prepare();meta,units=ex.verify_preview(p)
        self.assertEqual(len(units),8);self.assertTrue(all(u['gate'] for u in units))
        for u in units:
            self.assertEqual((p/u['data']).read_bytes(),(self.preview/u['data']).read_bytes())
            body=read_json(p/u['request']);self.assertEqual(body['max_tokens'],32768);self.assertEqual(body['reasoning_effort'],'medium')
            self.assertNotIn('image_url',json.dumps(body));self.assertNotIn('provisional_diagnostics',json.dumps(body))
        self.assertEqual(meta['limits'],{'baseline_calls':8,'recovery_calls':8,'per_parent_recovery':2,'admission_seconds':14400})
        self.assertEqual(read_json(p/'lineage.json')['parent_calls'],10);self.assertEqual(read_json(r/'state.json')['calls'],[])
        self.assertEqual(files_manifest(self.run),before)

    def test_repair_real_serialization_and_gate_no_provisional_credit(self):
        p,r=self.prepare();ready=self.root/'new-ready';ready.mkdir();meta=read_json(p/'preview.json')
        atomic_json(ready/'readiness.json',{'config':meta['config'],'finished_at':ex.now(),'text':'passed','vision':'not_requested_text_only'});ex.seal(ready)
        CriticClient.actions=['bad','ok']+['ok']*7;CriticClient.sent=[];CriticClient.timeouts=[]
        ex.execute(self.root,r,stage='gate',readiness=ready,client_factory=CriticClient)
        state=read_json(r/'state.json');self.assertEqual(state['status'],'completed');self.assertEqual(len(state['calls']),9)
        self.assertEqual(state['gate']['first_attempt_valid'],7);self.assertEqual(state['gate']['final_valid'],8)
        self.assertTrue(all(b['max_tokens']==32768 for b in CriticClient.sent));self.assertEqual(set(CriticClient.timeouts),{900.0})
        self.assertIn('exact_supplied_text',CriticClient.sent[1]['messages'][-1]['content'])
        self.assertEqual(read_json(r/'calls/0001/outcome.json')['status'],'failed')
        count=len(CriticClient.sent);ex.execute(self.root,r,stage='gate',readiness=ready,resume=True,client_factory=CriticClient);self.assertEqual(len(CriticClient.sent),count)

    def test_retry_allowance_anchor_survive_pause_resume_and_no_later_stage(self):
        p,r=self.prepare();ready=self.root/'new-ready';ready.mkdir();meta=read_json(p/'preview.json')
        atomic_json(ready/'readiness.json',{'config':meta['config'],'finished_at':ex.now(),'text':'passed','vision':'not_requested_text_only'});ex.seal(ready)
        with self.assertRaisesRegex(ValueError,'eight-unit gate'):
            ex.execute(self.root,r,stage='development',readiness=ready,client_factory=CriticClient)
        original=CriticClient._request
        def pause(client,*args,**kwargs):
            value=original(client,*args,**kwargs)
            if args[0]=='POST':(r/'PAUSE').touch()
            return value
        CriticClient.actions=['bad']
        with patch.object(CriticClient,'_request',pause):ex.execute(self.root,r,stage='gate',readiness=ready,client_factory=CriticClient)
        self.assertEqual(len(read_json(r/'state.json')['calls']),1);(r/'PAUSE').unlink()
        CriticClient.actions=['drop','drop']+['ok']*7
        ex.execute(self.root,r,stage='gate',readiness=ready,resume=True,client_factory=CriticClient)
        state=read_json(r/'state.json');calls=[c for c in state['calls'] if c['parent']=='g01-X'];self.assertEqual(len(calls),3)
        self.assertEqual(state['units']['g01-X']['status'],'failed');self.assertFalse(state['gate']['passed'])
        self.assertIn('critic_repair_anchor',read_json(r/'calls/0003/outcome.json')['failure'])

    def test_derived_report_preserves_old_evidence_and_counts_failed_calls(self):
        before=files_manifest(self.run);dest=self.root/'derived';summary=experiment_report(self.preview,self.run,report_dir=dest)
        self.assertTrue(summary['derived_report']);self.assertEqual(summary['extra_completion_tokens'],400)
        self.assertEqual(summary['extra_latency_seconds'],2);self.assertEqual(files_manifest(self.run),before)
        self.assertEqual(summary['unit_statuses']['failed'],4);self.assertFalse(summary['gate']['passed'])
        self.assertIn('Provisional diagnostics', (dest/'report.html').read_text())

    def test_stale_runtime_or_parent_binding_refuses_new_preparation(self):
        runtime=read_json(self.runtime);runtime['max_tokens_supported']=16384;atomic_json(self.runtime,runtime)
        with self.assertRaisesRegex(ValueError,'runtime support'):self.prepare()
        runtime['max_tokens_supported']=32768;atomic_json(self.runtime,runtime)
        state=read_json(self.run/'state.json');state['units']['g16-Y']['reason']='changed';atomic_json(self.run/'state.json',state)
        with self.assertRaisesRegex(IntegrityError,'unavailable reason'):self.prepare()


if __name__=='__main__':unittest.main()
