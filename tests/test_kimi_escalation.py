"""Offline K3 qualification: synthetic metadata, injected fake key and transport."""
import base64
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

from probe import kimi_escalation as k, cloud_critic as c, focused_recovery as f
from probe.common import atomic_json, read_json, sha
from probe.batch_review import IntegrityError, IdentityError
from probe.local_model import ProbeError
from scripts import kimi_escalation as cli


def metadata():
    return {'model':{'id':k.MODEL,'reasoning':{'supported_efforts':['high','max','low']},
                    'architecture':{'input_modalities':['text','image']}},
            'endpoints':{'data':{'id':k.MODEL,'endpoints':[{
                'tag':k.TAG,'model_id':k.MODEL,'provider_name':k.PROVIDER,'quantization':'fp4',
                'status':0,'service_tier':None,'max_completion_tokens':943718,'context_length':1048576,
                'supported_parameters':['reasoning','max_tokens','response_format','structured_outputs'],
                'pricing':{'prompt':'0.000000504','completion':'0.00002412','input_cache_read':'0.000000252'},
                'native_tools':{}}]}},
            'route':{'provider_slug':k.TAG,'provider_region':'us','provider_name':k.PROVIDER,
                     'quantization':'fp4','is_disabled':False,'model_variant_slug':k.MODEL,
                     'supports_multipart':True,
                     'data_policy':dict.fromkeys(('training','trainingOpenRouter','retainsPrompts','safetyRetention','canPublish'),False),
                     'model':{'slug':k.MODEL,'input_modalities':['text','image'],
                              'reasoning_config':{'supports_reasoning_effort':True,'supported_reasoning_efforts':['high','low','max']}}}}


class KimiTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.run=self.root/'runs/kimi-test';self.run.mkdir(parents=True)
        self.config=k.profile(metadata());self.task={'id':'selected','source_id':'original-test','source_sha256':'a'*64,
                 'operation':'convert','reason':'mathematical_transcription','pages':[3],'images':[]}
        self.body=k.build_body(self.config,self.task,'A complete equation $x=1$.','','A definition.')
        self.history={'summary':{'ceiling_usd':'10.00','actual_reported_usd':'.24','unresolved_reserved_usd':'0',
                       'reservations':21,'unresolved_charge_ids':[],'halt':None},'charges':[]}
        atomic_json(self.root/'prior.json',self.history)
        atomic_json(self.run/'binding.json',{'config':self.config,'prior_billing':{'path':str(self.root/'prior.json'),'sha256':sha(self.root/'prior.json')}})
        self.authorise();k.ledger(self.run,create=True)
        self.fake='fake-K3-secret-never-real';self.sent=[];self.actions=[];self.remaining='9.76'
        self.start(patch.dict(os.environ,{'OPENROUTER_API_KEY_FILE':c.KEY_FILE}))
        self.key_reader=Mock(return_value=self.fake)
        self.metadata_fetch=Mock(return_value=metadata())

    def start(self,p):v=p.start();self.addCleanup(p.stop);return v
    def authorise(self):
        atomic_json(self.run/'authorisation.json',{'binding_sha256':sha(self.run/'binding.json'),'accepted_pilot_budget_usd':self.config['pilot_budget_usd']})
    def client(self):
        client=k.KimiClient(self.run,key_reader=self.key_reader,metadata_fetch=self.metadata_fetch,history_reader=lambda:self.history)
        client._http=lambda method,path,body=None:self.http(client,method,path,body)
        return client
    def http(self,client,method,path,body):
        self.sent.append((method,path,copy.deepcopy(body)))
        if method=='GET':
            if path=='/key':data={'data':{'limit':10,'limit_reset':None,'limit_remaining':self.remaining,'label':self.fake}}
            elif path.startswith('/generation?'):data={'data':{'id':path.partition('=')[2],'model':k.MODEL,'provider_name':k.PROVIDER,'total_cost':'.02','native_tokens_prompt':100,'native_tokens_completion':200,'native_tokens_reasoning':100}}
            else:raise AssertionError(path)
            return 200,json.dumps(data).encode(),.1
        action=self.actions.pop(0) if self.actions else 'ok'
        # The durable reservation must already exist at the transport boundary.
        self.assertEqual(len(k.ledger(self.run).read()['reservations']),sum(m=='POST' for m,p,b in self.sent))
        if action=='disconnect':raise OSError('Disconnected '+self.fake)
        usage={'prompt_tokens':100,'completion_tokens':200,'completion_tokens_details':{'reasoning_tokens':100},'cost':'.02'}
        if action=='unknown':usage.pop('cost')
        d={'id':'gen-'+str(len(self.sent)),'model':k.MODEL if action!='model' else 'moonshotai/kimi-k3.1',
           'provider':k.PROVIDER if action!='provider' else 'Other','usage':usage,
           'choices':[{'finish_reason':'length' if action=='length' else 'stop','message':{
               'content':'\\documentclass{article}\\begin{document}$x=1$\\end{document} '+self.fake,
               'reasoning':'Returned optional reasoning '+self.fake}}]}
        return 200,json.dumps(d).encode(),.25

    def test_exact_high_route_privacy_settings(self):
        self.assertEqual(self.body['reasoning'],{'effort':'high','exclude':False})
        self.assertEqual(self.body['max_tokens'],32768)
        self.assertEqual(self.body['provider']['only'],['sail-research/fp4/us'])
        self.assertFalse(self.body['provider']['allow_fallbacks']);self.assertTrue(self.body['provider']['require_parameters'])
        self.assertEqual(self.body['provider']['data_collection'],'deny');self.assertTrue(self.body['provider']['zdr'])
        self.assertEqual(self.config['paid_limits'],{'trial_calls':3,'readiness_calls':0})
        self.assertEqual(self.config['concurrency'],1);self.assertNotIn('reasoning_effort',self.body)

    def test_unsupported_route_or_settings_fail_closed(self):
        for name,value in [('tag','sail-research/fp4'),('provider_name','Other'),('quantization','fp8'),
                ('status',1),('service_tier','flex'),('supported_parameters',[]),('max_completion_tokens',8192)]:
            m=metadata();m['endpoints']['data']['endpoints'][0][name]=value
            with self.subTest(field=name),self.assertRaises((IdentityError,c.AdmissionError)):k.validate_metadata(m)
        for location,name,value in [('route','supports_multipart',False),('model','id','moonshotai/kimi-k3.1')]:
            m=metadata();m[location][name]=value
            with self.assertRaises((IdentityError,c.AdmissionError)):k.validate_metadata(m,images=True)
        m=metadata();m['model']['reasoning']['supported_efforts']=['max']
        with self.assertRaises(c.AdmissionError):k.validate_metadata(m)
        m=metadata();m['route']['data_policy']['retainsPrompts']=True
        with self.assertRaises(c.AdmissionError):k.validate_metadata(m)
        m=metadata();m['endpoints']['data']['endpoints'][0]['pricing']['completion']='.001'
        with self.assertRaises(c.AdmissionError):k.validate_metadata(m,self.config)
        for field,value in [('model','moonshotai/kimi-k3.1'),('reasoning',{'effort':'low'}),('tools',[{}])]:
            b=copy.deepcopy(self.body);b[field]=value
            with self.assertRaises(IntegrityError):k.validate_body(self.config,b)

    def test_disabled_escalation_never_accesses_key_or_transport(self):
        for p in ({},{'enabled':False,'selected_tasks':['selected']},{'enabled':True,'selected_tasks':[]}):self.assertFalse(k.opt_in(p,self.task))
        (self.run/'authorisation.json').unlink()
        with self.assertRaises(c.AdmissionError):self.client()
        self.key_reader.assert_not_called();self.assertFalse(self.sent)
        for reason in ('compiler_failure','ocr_infrastructure'):
            with self.assertRaises(c.AdmissionError):k.build_body(self.config,{**self.task,'reason':reason},'A','','')
        with self.assertRaises(c.AdmissionError):k.build_body(self.config,{**self.task,'source_id':k.EXCLUDED_SOURCE},'A','','')

    def test_image_identity_scope_and_full_context_cost_bound(self):
        p=self.root/'page.png';p.write_bytes(b'\x89PNG\r\n\x1a\nsynthetic-test-only')
        asset={'path':str(p),'sha256':sha(p),'source_id':self.task['source_id'],'source_sha256':self.task['source_sha256'],'page':3,'bbox':[0,0,1,1]}
        b=k.build_body(self.config,self.task,'A','','',assets=[asset])
        self.assertEqual(k.cost_bound(self.config,b),Decimal('1.302331392'))
        self.assertEqual(k.input_bound(self.config,b),1015808)
        for field,val in [('source_id','wrong'),('source_sha256','b'*64),('page',9),('sha256','0'*64)]:
            with self.assertRaises(IntegrityError):k.build_body(self.config,self.task,'A','','',assets=[dict(asset,**{field:val})])
        b['messages'][0]['content'][-1]['image_url']['url']='https://example.com/not-permitted.png'
        with self.assertRaises(IntegrityError):k.validate_body(self.config,b)

    def test_request_contains_only_selected_draft_not_expected_answers_or_full_book(self):
        draft='UNRELATED PRIVATE MATERIAL\nSelected $x=1$.\nEND OF BOOK'
        a=draft.index('Selected');b=draft.index('\nEND')
        body=k.build_body(self.config,{**self.task,'operation':'review'},'SOURCE','','DEFINITION',draft,[[a,b]])
        wire=json.dumps(body);self.assertNotIn('UNRELATED PRIVATE MATERIAL',wire);self.assertNotIn('END OF BOOK',wire)
        self.assertIn(f.digest(draft),wire);self.assertIn('Selected',wire)
        self.assertEqual(body['response_format']['json_schema']['schema']['properties']['base_sha256']['enum'],[f.digest(draft)])

    def test_redaction_optional_reasoning_and_usage_persist_separately(self):
        folder=self.run/'calls/selected';answer,outcome=self.client().dispatch(self.task,self.body,folder)
        self.assertNotIn(self.fake,answer)
        for p in self.run.rglob('*'):
            if p.is_file():self.assertNotIn(self.fake.encode(),p.read_bytes(),str(p))
        self.assertTrue((folder/'reasoning.txt').exists());self.assertTrue(outcome['reasoning_text_returned'])
        self.assertEqual(outcome['usage']['completion_tokens_details']['reasoning_tokens'],100)
        self.assertEqual(k.ledger(self.run).read()['reservations'][0]['actual_cost_usd'],'0.02')

    def test_live_allowance_includes_other_applications(self):
        self.remaining='.01'
        with self.assertRaises(c.AdmissionError):self.client().dispatch(self.task,self.body,self.run/'calls/selected')
        self.assertEqual(k.ledger(self.run).read()['reservations'],[])
        self.assertFalse(any(m=='POST' for m,p,b in self.sent))

    def test_prior_unknown_charges_and_global_ceiling_cannot_reset(self):
        self.history['summary']['unresolved_reserved_usd']='9.5'
        with self.assertRaises(c.AdmissionError):self.client().dispatch(self.task,self.body,self.run/'calls/selected')
        self.assertFalse(any(m=='POST' for m,p,b in self.sent))

    def test_pilot_budget_and_finite_call_limit(self):
        ledger=k.ledger(self.run);ledger.pilot_budget=Decimal('.01')
        with self.assertRaises(c.AdmissionError):ledger.admit(self.body,Decimal(10))
        ledger=k.ledger(self.run)
        for i in range(3):
            identity=ledger.reserve(self.body,self.run/'calls'/str(i),Decimal(10),'trial')
            ledger.settle(identity,{'usage':{'cost':'.01','completion_tokens':1}},'synthetic')
        with self.assertRaisesRegex(c.AdmissionError,'ceiling'):ledger.reserve(self.body,self.run/'calls/4',Decimal(10),'trial')
        with self.assertRaises(c.AdmissionError):ledger.reserve(self.body,self.run/'calls/ready',Decimal(10),'readiness')

    def test_disconnect_keeps_reservation_redacts_error_and_never_resends(self):
        self.actions=['disconnect'];client=self.client();folder=self.run/'calls/selected'
        with self.assertRaises(ProbeError) as error:client.dispatch(self.task,self.body,folder)
        self.assertNotIn(self.fake,str(error.exception));self.assertNotIn(self.fake,(folder/'error.json').read_text())
        self.assertGreater(Decimal(client.ledger.summary()['unresolved_reserved_usd']),0)
        client=self.client();client.reconcile()
        with self.assertRaisesRegex(c.AdmissionError,'already reserved'):client.dispatch(self.task,self.body,folder)
        self.assertEqual(sum(m=='POST' for m,p,b in self.sent),1)

    def test_get_only_charge_reconciliation_does_not_retry(self):
        self.actions=['unknown'];client=self.client();client.dispatch(self.task,self.body,self.run/'calls/selected')
        self.assertGreater(Decimal(client.ledger.summary()['unresolved_reserved_usd']),0)
        client=self.client();client.reconcile()
        self.assertEqual(client.ledger.summary()['unresolved_reserved_usd'],'0')
        self.assertEqual(sum(m=='POST' for m,p,b in self.sent),1)
        self.assertTrue(any(p.startswith('/generation?') for m,p,b in self.sent))

    def test_identity_mismatch_is_charged_but_stops(self):
        self.actions=['model']
        with self.assertRaises(IdentityError):self.client().dispatch(self.task,self.body,self.run/'calls/selected')
        self.assertEqual(k.ledger(self.run).read()['reservations'][0]['actual_cost_usd'],'0.02')
        self.assertIn('identity',k.ledger(self.run).read()['halt'])
        with self.assertRaises(c.AdmissionError):self.client().dispatch({**self.task,'id':'next'},self.body,self.run/'calls/next')
        self.assertEqual(sum(m=='POST' for m,p,b in self.sent),1)

    def test_truncation_retains_partial_answer_and_no_retry(self):
        self.actions=['length'];answer,outcome=self.client().dispatch(self.task,self.body,self.run/'calls/selected')
        self.assertTrue(answer);self.assertEqual(outcome['status'],'incomplete_response')
        self.assertEqual(outcome['finish_reason'],'length');self.assertEqual(sum(m=='POST' for m,p,b in self.sent),1)

    def test_focused_hash_scope_ambiguous_overlap_and_unapplied_findings(self):
        draft='Definitions. $x=1$ then $x=2$. Repeated Repeated.'
        def response(findings,base=None):return json.dumps({'base_sha256':base or f.digest(draft),'findings':findings})
        def edit(old,new):return {'status':'edit','old':old,'new':new,'source':'p3 eq1','reason':'Located supported correction'}
        with self.assertRaisesRegex(ValueError,'Stale'):f.apply_focused(draft,response([],base='bad'))
        revised,log=f.apply_focused(draft,response([edit('Repeated','Different')]))
        self.assertEqual(revised,draft);self.assertEqual(log['findings'][0]['disposition'],'rejected')
        revised,log=f.apply_focused(draft,response([edit('$x=1$','$x=3$')]),[[0,5]])
        self.assertEqual(revised,draft)
        revised,log=f.apply_focused(draft,response([edit('$x=1$ then','$x=3$ then'),edit('$x=1$','$x=4$')]))
        self.assertEqual(revised,draft);self.assertTrue(all(n['disposition']=='rejected' for n in log['findings']))
        revised,log=f.apply_focused(draft,response([edit('$x=1$','$x=3$'),{'status':'unresolved','old':'','new':'','source':'p3','reason':'Ambiguous source'}]))
        self.assertIn('$x=3$',revised);self.assertIn('unresolved',[n['disposition'] for n in log['findings']])

    def test_reserved_first_task_cannot_be_bypassed_on_resume(self):
        self.actions=['disconnect'];client=self.client()
        with self.assertRaises(ProbeError):client.dispatch(self.task,self.body,self.run/'calls/selected')
        state={'tasks':{'selected':{'status':'pending'}},'live_qualified':False}
        with self.assertRaisesRegex(c.AdmissionError,'qualification'):cli.restore_reserved(self.run,{'tasks':[self.task]},client.ledger,state)
        self.assertEqual(state['tasks']['selected']['status'],'reserved_unfinished')
        self.assertEqual(sum(m=='POST' for m,p,b in self.sent),1)

    def test_saved_success_restored_without_reprocessing_or_post(self):
        client=self.client();folder=self.run/'calls/selected';client.dispatch(self.task,self.body,folder)
        atomic_json(folder/'result.json',{'status':'candidate_saved','mathematical_verification':False})
        state={'tasks':{'selected':{'status':'pending'}},'live_qualified':False}
        with patch.object(cli,'process_answer',side_effect=AssertionError('No regeneration')):
            cli.restore_reserved(self.run,{'tasks':[self.task]},client.ledger,state)
        self.assertTrue(state['live_qualified']);self.assertEqual(sum(m=='POST' for m,p,b in self.sent),1)

    def test_finished_resume_does_not_read_key_use_network_or_start_worker(self):
        with patch.object(cli,'verify_plan',return_value=({'project_root':str(cli.ROOT)},{})),\
             patch.object(cli,'existing_run',return_value=self.run),\
             patch.object(cli,'verify_run',return_value=({},None,{'status':'finished'})),\
             patch.object(k,'KimiClient',side_effect=AssertionError('No client')),\
             patch.object(cli.subprocess,'run',side_effect=AssertionError('No child')):
            self.assertEqual(cli.launch(self.root/'plan',resume=True),self.run)
        self.key_reader.assert_not_called();self.assertFalse(self.sent)

    def test_staged_overlay_refuses_paid_launch(self):
        with patch.object(cli,'verify_plan',return_value=({'project_root':str(self.root)},{})),\
             patch.object(k,'KimiClient',side_effect=AssertionError('No client')):
            with self.assertRaisesRegex(c.AdmissionError,'Staged'):cli.launch(self.root/'plan','4.00')

    def test_updated_pilot_uses_settled_control_and_cf_disagreement(self):
        plan=cli.provisional_spec(None)
        self.assertEqual([t['id'] for t in plan['tasks']],['information-control-review','cf-case17-convert','cf-case17-review'])
        self.assertTrue(plan['tasks'][0]['control'])
        self.assertEqual(plan['tasks'][2]['reason'],'converter_critic_disagreement')
        self.assertEqual(plan['tasks'][1]['context_blocks'],8)
        self.assertEqual(plan['tasks'][2]['context_blocks'],8)
        self.assertNotIn('pathint',json.dumps(plan));self.assertNotIn(k.EXCLUDED_SOURCE,json.dumps(plan))

    def test_admission_interruption_without_reservation_can_resume_safely(self):
        state={'tasks':{'selected':{'status':'dispatching'}},'live_qualified':False}
        cli.restore_reserved(self.run,{'tasks':[self.task]},k.ledger(self.run),state)
        self.assertEqual(state['tasks']['selected']['status'],'pending')
        self.assertFalse(self.sent)

    def test_prior_ledger_reconciliation_deduplicates_snapshot(self):
        # Remove the synthetic aggregate: real history must have charge identities.
        binding={'config':self.config};atomic_json(self.run/'binding.json',binding)
        (self.run/'billing.json').unlink();self.authorise();ledger=k.ledger(self.run,create=True)
        identity=ledger.reserve(self.body,self.run/'calls/selected',Decimal(10),'trial')
        ledger.settle(identity,{'id':'gen-known','usage':{'cost':'.02','completion_tokens':1}},'test')
        first=k.history_snapshot(self.root);self.assertEqual(first['summary']['actual_reported_usd'],'0.02')
        path=self.root/'prior2.json';atomic_json(path,first)
        second=self.root/'runs/second';second.mkdir()
        atomic_json(second/'binding.json',{'config':self.config,'prior_billing':{'path':str(path),'sha256':sha(path)}});k.ledger(second,create=True)
        final=k.history_snapshot(self.root);self.assertEqual(final['summary']['actual_reported_usd'],'0.02');self.assertEqual(final['summary']['reservations'],1)

    def worker_fixture(self):
        plan=self.root/'plan';plan.mkdir();parent=self.root/'parent';(parent/'compiler').mkdir(parents=True)
        binding=read_json(self.run/'binding.json');binding['plan_path']=str(plan);atomic_json(self.run/'binding.json',binding)
        (self.run/'billing.json').unlink();self.authorise();ledger=k.ledger(self.run,create=True)
        tasks=[]
        for i in range(3):
            task={**self.task,'id':'task-'+str(i),'filename':'Synthetic paper','request':'request-'+str(i)+'.json','reservation_usd':str(k.cost_bound(self.config,self.body))}
            atomic_json(plan/task['request'],self.body);tasks.append(task)
        data={'project_root':str(self.root),'source_parent':str(parent),'compiler_environment':{'path':'compiler'},'pilot_cap_usd':'4.00','tasks':tasks}
        atomic_json(self.run/'state.json',{'status':'prepared','tasks':{t['id']:{'status':'pending'} for t in tasks},'live_qualified':False})
        client=self.client()
        self.start(patch.object(cli,'ROOT',self.root))
        self.start(patch.object(cli,'verify_run',side_effect=lambda r:(data,ledger,read_json(r/'state.json'))))
        self.start(patch.object(cli,'selected_fresh'))
        self.start(patch.object(cli.os,'dup2'))
        self.start(patch.object(cli.local.books,'qualify_compiler'))
        self.start(patch.object(k,'history_snapshot',return_value=self.history))
        self.start(patch.object(k,'KimiClient',return_value=client))
        self.start(patch.object(cli,'bundle',return_value=None))
        self.start(patch.object(cli,'process_answer',side_effect=lambda r,t,a,o,d:{'status':'candidate_saved' if o['status']=='complete_response' else 'incomplete_answer'}))
        return client

    def test_finite_worker_finishes_and_second_resume_is_zero_requests(self):
        self.worker_fixture();cli.worker(self.run)
        self.assertEqual(read_json(self.run/'state.json')['status'],'finished')
        self.assertEqual(sum(m=='POST' for m,p,b in self.sent),3)
        count=len(self.sent);cli.worker(self.run);self.assertEqual(len(self.sent),count)

    def test_worker_continues_after_later_document_incomplete_answer(self):
        self.worker_fixture();self.actions=['ok','length','ok'];cli.worker(self.run)
        state=read_json(self.run/'state.json');self.assertEqual(state['status'],'finished_with_failures')
        self.assertEqual(state['tasks']['task-2']['status'],'candidate_saved')
        self.assertEqual(sum(m=='POST' for m,p,b in self.sent),3)

    def test_worker_disconnect_resume_does_not_bypass_qualification(self):
        self.worker_fixture();self.actions=['disconnect'];cli.worker(self.run)
        self.assertEqual(read_json(self.run/'state.json')['status'],'blocked')
        cli.worker(self.run)
        self.assertEqual(read_json(self.run/'state.json')['status'],'blocked')
        self.assertEqual(sum(m=='POST' for m,p,b in self.sent),1)


if __name__=='__main__':unittest.main()
