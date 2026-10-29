"""Offline only: fake private files and mocked transport, never real credentials."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from probe import cloud_critic as cloud, critic_pilot as pilot, experiment as ex, text_critic as tc
from probe.common import atomic_json, read_json, files_manifest, sha
from probe.local_model import LocalClient, ProbeError
from probe.batch_review import IntegrityError, IdentityError
from probe.recovery_trial import save_unit, finish_preview
from test_critic_followup import passage, answer, CriticClient


def endpoint():
    return {'data':{'id':cloud.MODEL,'endpoints':[{'model_id':cloud.MODEL,'provider_name':'Xiaomi',
        'tag':cloud.TAG,'quantization':'fp8','service_tier':None,'status':0,'pricing':cloud.RATES.copy(),
        'max_completion_tokens':131072,'context_length':1048576,
        'supported_parameters':['reasoning','max_tokens','response_format','structured_outputs']}]}}


class Transport:
    def __init__(self):self.sent=[];self.actions=[];self.limit='1';self.remaining='1';self.routes=endpoint();self.hook=None
    def call(self,client,method,path,body=None):
        self.sent.append((method,path,copy.deepcopy(body)))
        if method=='GET':
            if path.endswith('/endpoints'):v=self.routes
            elif path=='/key':v={'data':{'limit':self.limit,'limit_reset':None,'limit_remaining':self.remaining,'label':client._key}}
            elif path.startswith('/generation?'):
                v={'data':{'id':path.split('=')[1],'model':cloud.MODEL,'provider_name':'Xiaomi','total_cost':'.001',
                    'native_tokens_prompt':100,'native_tokens_completion':200}}
            else:raise AssertionError('Unexpected metadata lookup (ZDR must not be required): '+path)
            return 200,json.dumps(v).encode(),0.1
        d=json.loads(body['messages'][1]['content'].split('<passage>\n')[1].split('\n</passage>')[0])
        a=self.actions.pop(0) if self.actions else 'ok'
        if a=='timeout':raise ProbeError('OpenRouter transport TimeoutError; charge remains reserved if dispatched')
        v=answer(d,a=='bad') if d['group_id']!='ready' else {'group_id':'ready','draft_sha256':d['draft_sha256'],
            'coverage':'complete','reviewed_block_ids':['ready:b0'],'context_needed':[],'findings':[]}
        if a=='drop':v['findings']=[]
        usage={'prompt_tokens':100,'completion_tokens':200,'cost':'.001'}
        if a=='unknown':usage.pop('cost')
        raw={'id':'gen-'+str(len(self.sent)),'model':cloud.MODEL if a!='identity' else 'other',
            'provider':'Xiaomi' if a!='provider' else 'DeepInfra','usage':usage,
            'choices':[{'finish_reason':'length' if a=='length' else 'stop',
                'message':{'content':json.dumps(v) if a!='length' else None}}]}
        if self.hook:self.hook()
        return 200,json.dumps(raw).encode(),1.0


class PilotTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        (self.root/'runs').mkdir();(self.root/'results').mkdir()
        self.key=self.root/'fake.key';fd=os.open(self.key,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:f.write('fake-test-secret-only\n')
        self.start_patch(patch.object(pilot,'ROOT',self.root))
        self.start_patch(patch('probe.experiment.converter_idle',return_value={'owned_converter_pids':[]}))
        self.start_patch(patch.dict(os.environ,{'OPENROUTER_API_KEY_FILE':str(self.key)}))
        self.transport=Transport()
        self.start_patch(patch.object(cloud.CloudClient,'_http',lambda client,*a,**kw:self.transport.call(client,*a,**kw)))
        self.parents=[]
        for name,ids in (('gate',pilot.SAMPLE[:4]),('overnight',pilot.SAMPLE[4:])):
            p=self.root/(name+'-input');p.mkdir();r=self.root/name;units=[]
            for identity in ids:
                d=passage(identity[:3]);units.append(save_unit(p,identity,d,tc.request(d,max_tokens=32768),kind='critic',
                    gate=False,split='development',version='baseline' if identity[-1]=='X' else 'candidate',location={'page':123,'blocks':['p:b1']}))
            finish_preview(p,units,'critic',{**tc.PROFILES['deepseek'],'max_tokens':32768},{},pilot.LIMITS,{},{});ex.initialize(p,r)
            self.parents.extend([r,p])
        self.before={str(p):files_manifest(p) for p in self.parents}
        self.comparison=self.root/'comparison';self.paths=pilot.prepare(self.comparison,gate=self.parents[0],overnight=self.parents[2],budget_usd='1.00')
        self.mimo=Path(self.paths['mimo']['run']);self.glm=Path(self.paths['glm']['run'])

    def start_patch(self,p):value=p.start();self.addCleanup(p.stop);return value
    def client(self):return cloud.CloudClient(cloud.BASE,cloud.MODEL,run=self.mimo)
    def ready_record(self,run):
        dest=self.root/(run.name+'-ready');dest.mkdir(exist_ok=True)
        atomic_json(dest/'readiness.json',{'config':read_json(run/'binding.json')['config'],'finished_at':ex.now(),
            'text':'passed','vision':'not_requested_text_only'});ex.seal(dest);return dest
    def run_mimo(self,**kw):
        ready=self.ready_record(self.mimo) if not (self.root/(self.mimo.name+'-ready')).exists() else self.root/(self.mimo.name+'-ready')
        with patch('builtins.print'):
            return ex.execute(self.root,self.mimo,stage='pilot',readiness=ready,
                client_factory=pilot.factory(self.mimo,cloud.CONFIG,True),**kw)

    def test_sample_exact_payload_hashes_scope_and_preserved_history(self):
        for name in ('glm','mimo'):
            p=Path(self.paths[name]['preview']);meta,units=ex.verify_preview(p)
            self.assertEqual([u['id'] for u in units],list(pilot.SAMPLE));pilot.validate_arm(meta,units)
            for u in units:
                old=next(p for p in self.parents[1::2] if (p/u['data']).exists())
                self.assertEqual((p/u['data']).read_bytes(),(old/u['data']).read_bytes())
                body=read_json(p/u['request']);self.assertEqual(body['messages'],read_json(old/u['request'])['messages'])
                self.assertEqual(body['max_tokens'],32768);self.assertNotIn('Prior ChatGPT',json.dumps(body))
                self.assertNotIn('image_url',json.dumps(body));self.assertNotIn('g11',u['id'])
        self.assertEqual({str(p):files_manifest(p) for p in self.parents},self.before)

    def test_retained_route_no_zdr_lookup_real_serialization_and_schema(self):
        self.run_mimo();s=read_json(self.mimo/'state.json');self.assertEqual(s['status'],'completed');self.assertEqual(len(s['calls']),12)
        posts=[b for m,p,b in self.transport.sent if m=='POST'];self.assertEqual(len(posts),12)
        for i,b in enumerate(posts):
            self.assertEqual(b,read_json(Path(self.paths['mimo']['preview'])/f'units/{pilot.SAMPLE[i]}/request.json'))
            self.assertEqual(b['provider']['data_collection'],'allow');self.assertIs(b['provider']['zdr'],False)
            self.assertEqual(b['provider']['only'],['xiaomi/fp8']);self.assertFalse(b['provider']['allow_fallbacks'])
            self.assertEqual(b['reasoning'],{'enabled':True});self.assertNotIn('reasoning_effort',b)
            self.assertTrue(b['response_format']['json_schema']['strict']);self.assertEqual(b['plugins'],[])
        self.assertFalse(any('zdr' in p for m,p,b in self.transport.sent))
        self.assertEqual(cloud.Ledger(self.mimo).summary()['actual_reported_usd'],'0.012')
        self.assertNotIn('fake-test-secret-only',''.join(p.read_text() for p in self.mimo.rglob('*.json')))

    def test_readiness_small_finite_and_charged_separately(self):
        with patch('builtins.print'):
            for _ in range(2):pilot.ready(self.mimo,True)
        with self.assertRaisesRegex(ValueError,'Two readiness'):pilot.ready(self.mimo,True)
        self.assertEqual(len([b for m,p,b in self.transport.sent if m=='POST']),2)
        self.assertEqual(cloud.Ledger(self.mimo).summary()['readiness_calls'],2)
        self.assertEqual(cloud.Ledger(self.mimo).summary()['actual_reported_usd'],'0.002')
        self.assertTrue(all(b['max_tokens']==2048 for m,p,b in self.transport.sent if m=='POST'))

    def test_opt_in_boundary_and_local_failure_never_cloud_fallback(self):
        with self.assertRaisesRegex(ValueError,'allow-paid'):pilot.factory(self.mimo,cloud.CONFIG)
        with self.assertRaises(ValueError):LocalClient(cloud.BASE,model=cloud.MODEL,purpose='text_critic')
        self.assertIs(pilot.factory(self.glm,pilot.GLM),LocalClient)
        CriticClient.actions=['length']*12;CriticClient.counter=0;CriticClient.sent=[]
        with patch('builtins.print'):
            ex.execute(self.root,self.glm,stage='pilot',readiness=self.ready_record(self.glm),client_factory=CriticClient)
        self.assertEqual(len(CriticClient.sent),12);self.assertFalse(self.transport.sent)
        self.assertTrue(all(b['reasoning_effort']=='high' for b in CriticClient.sent))

    def test_identity_and_provider_mismatch_stop_without_fallback(self):
        self.transport.actions=['provider'];self.run_mimo()
        self.assertEqual(read_json(self.mimo/'state.json')['status'],'stopped_identity')
        self.assertEqual(sum(m=='POST' for m,p,b in self.transport.sent),1)
        self.assertEqual(cloud.Ledger(self.mimo).summary()['actual_reported_usd'],'0.001')

    def test_recovery_accounting_pause_resume_and_no_replay(self):
        self.transport.actions=['bad'];self.transport.hook=lambda:(self.mimo/'PAUSE').touch();self.run_mimo()
        self.transport.hook=None;(self.mimo/'PAUSE').unlink()
        self.transport.actions=['drop','drop','bad','ok','bad','ok']+['ok']*9
        self.run_mimo(resume=True);s=read_json(self.mimo/'state.json')
        self.assertEqual(sum(c['method']=='baseline' for c in s['calls']),12)
        self.assertEqual(sum(c['method']!='baseline' for c in s['calls']),4)
        self.assertEqual(sum(c['parent']=='g01-Y' for c in s['calls']),3)
        self.assertEqual(cloud.Ledger(self.mimo).summary()['reservations'],16)
        posts=sum(m=='POST' for m,p,b in self.transport.sent);self.run_mimo(resume=True)
        self.assertEqual(sum(m=='POST' for m,p,b in self.transport.sent),posts)

    def test_uncertain_charges_remain_reserved_and_timeouts_not_retried(self):
        self.transport.actions=['timeout','unknown']+['ok']*10;self.run_mimo()
        ledger=cloud.Ledger(self.mimo);summary=ledger.summary()
        self.assertEqual(summary['reservations'],12);self.assertEqual(len(summary['unresolved_charge_ids']),2)
        self.assertGreater(cloud.decimal(summary['unresolved_reserved_usd']),0)
        self.client().reconcile_costs();self.assertEqual(len(ledger.summary()['unresolved_charge_ids']),1)
        self.assertEqual(sum(m=='POST' for m,p,b in self.transport.sent),12)

    def test_price_capability_or_budget_refusal_before_any_paid_reservation(self):
        self.transport.routes['data']['endpoints'][0]['pricing']['completion']='0.00000088'
        self.run_mimo();self.assertEqual(read_json(self.mimo/'state.json')['calls'],[])
        self.assertEqual(cloud.Ledger(self.mimo).summary()['reservations'],0)
        self.transport.routes=endpoint();self.transport.remaining='0.001';self.run_mimo(resume=True)
        self.assertFalse(any(m=='POST' for m,p,b in self.transport.sent))

    def test_ledger_durable_cost_ceiling_tampering_and_missing_never_reset(self):
        l=cloud.Ledger(self.mimo);body=cloud.body_for(tc.request(passage())['messages'])
        n=0
        while True:
            try:l.reserve(body,self.mimo/'calls'/str(n),cloud.Decimal(1),'trial');n+=1
            except cloud.AdmissionError:break
        self.assertLessEqual(l.exposure(l.read()),1);self.assertGreater(n,0)
        self.assertEqual(cloud.Ledger(self.mimo).summary(),l.summary())
        reservation=self.mimo/'billing/0001/reservation.json';reservation.write_text(reservation.read_text()+' ')
        with self.assertRaises(IntegrityError):cloud.Ledger(self.mimo)
        (self.mimo/'billing.json').unlink()
        with self.assertRaisesRegex(IntegrityError,'never reset'):cloud.Ledger(self.mimo)

    def test_changing_prepared_profile_rejected_before_dispatch(self):
        p=Path(self.paths['mimo']['preview']);m=read_json(p/'preview.json');m['config']['provider']['zdr']=True
        atomic_json(p/'preview.json',m)
        with self.assertRaises(IntegrityError):pilot.arm(self.mimo)
        self.assertFalse(self.transport.sent)

    def test_reservation_precedes_dispatch_and_exact_model_is_enforced(self):
        def check_reserved():
            ledger=cloud.Ledger(self.mimo).read();item=ledger['reservations'][-1]
            self.assertTrue((self.mimo/item['evidence']).is_file())
            self.assertNotIn('actual_cost_usd',item)
            self.assertEqual(item['request_sha256'],read_json(self.mimo/'calls/0001/reservation.json')['request_sha256'])
        self.transport.hook=check_reserved;self.transport.actions=['identity'];self.run_mimo()
        self.assertEqual(read_json(self.mimo/'state.json')['status'],'stopped_identity')
        self.assertEqual(len([m for m,p,b in self.transport.sent if m=='POST']),1)

    def test_overflow_charge_stops_admission_and_zero_cost_is_not_assumed_free(self):
        l=cloud.Ledger(self.mimo);body=cloud.body_for(tc.request(passage())['messages'])
        first=l.reserve(body,self.mimo/'calls/0001',cloud.Decimal(1),'trial')
        l.settle(first,{'id':'fake-gen','usage':{'cost':0,'completion_tokens':200}},'fake source')
        self.assertEqual(l.summary()['unresolved_charge_ids'],[first])
        l.settle(first,{'id':'fake-gen','usage':{'cost':'.9','completion_tokens':200}},'fake source')
        with self.assertRaisesRegex(cloud.AdmissionError,'above reservation'):l.admit(body,cloud.Decimal(1))

    def test_http_timeout_reserved_across_resume_with_no_duplicate_submission(self):
        self.transport.actions=['timeout','timeout'];self.run_mimo()
        s=read_json(self.mimo/'state.json');self.assertEqual(s['status'],'paused_connection')
        self.assertEqual(len(s['calls']),2)
        self.run_mimo(resume=True);s=read_json(self.mimo/'state.json')
        self.assertEqual(len(s['calls']),12);self.assertEqual(sum(c['parent']=='g01-Y' for c in s['calls']),1)
        self.assertEqual(cloud.Ledger(self.mimo).summary()['unresolved_charge_ids'],['0001','0002'])

    def test_side_by_side_denominators_unknown_not_zero_and_bundle(self):
        self.run_mimo()
        with patch('builtins.print'):z=pilot.bundle(self.comparison)
        d=read_json(Path(z['report']).parent/'comparison.json');self.assertEqual(len(d['rows']),12)
        self.assertEqual(d['summary']['mimo']['final_valid'],12)
        for v in d['summary'].values():
            self.assertEqual(v['planned_units'],12);self.assertEqual(v['paired_groups'],4);self.assertEqual(v['selected_groups'],8)
        self.assertIsNone(d['summary']['mimo']['usage']['all']['reasoning_tokens']['total'])
        with zipfile.ZipFile(z['path']) as archive:
            self.assertIsNone(archive.testzip());self.assertIn('report.md',archive.namelist())
            self.assertFalse(any('fake.key' in n or n.endswith('.pdf') for n in archive.namelist()))
            self.assertNotIn(b'fake-test-secret-only',b''.join(archive.read(n) for n in archive.namelist()))
        self.assertEqual({str(p):files_manifest(p) for p in self.parents},self.before)

    def test_budget_refresh_only_mimo_exact_requests_and_completed_glm_preserved(self):
        CriticClient.actions=[];CriticClient.counter=0;CriticClient.sent=[]
        with patch('builtins.print'):
            ex.execute(self.root,self.glm,stage='pilot',readiness=self.ready_record(self.glm),client_factory=CriticClient)
        olddirs=[self.comparison,self.glm,self.mimo,Path(self.paths['glm']['preview']),Path(self.paths['mimo']['preview'])]
        before={str(p):files_manifest(p) for p in olddirs}
        new=pilot.reprepare_mimo(self.comparison,self.root/'budget-comparison',budget_usd='10')
        self.assertEqual(new['glm'],self.paths['glm'])
        newp=Path(new['mimo']['preview']);newr=Path(new['mimo']['run']);meta,units=ex.verify_preview(newp)
        self.assertEqual(meta['config'],cloud.profile('10'));self.assertEqual(meta['limits'],pilot.LIMITS)
        self.assertEqual([u['id'] for u in units],list(pilot.SAMPLE))
        for u in units:
            for field in ('request','data'):
                self.assertEqual((newp/u[field]).read_bytes(),(Path(self.paths['mimo']['preview'])/u[field]).read_bytes())
        self.assertEqual(cloud.Ledger(newr).summary()['ceiling_usd'],'10.00')
        self.transport.limit=self.transport.remaining='10';self.mimo=newr;self.paths=new
        self.run_mimo()
        with patch('builtins.print'):z=pilot.bundle(Path(new['comparison']))
        self.assertTrue(Path(z['report']).is_relative_to(newr))
        report=read_json(Path(z['report']).with_name('comparison.json'))
        self.assertEqual(report['summary']['glm']['usage']['inherited']['calls'],12)
        self.assertEqual(report['summary']['glm']['usage']['current_run']['calls'],0)
        self.assertEqual({str(p):files_manifest(p) for p in olddirs},before)
        with zipfile.ZipFile(z['path']) as archive:
            self.assertIsNone(archive.testzip());self.assertIn('mimo/prepared/budget-lineage.json',archive.namelist())

    def test_budget_refresh_inherits_calls_readiness_unknown_charges_and_no_replay(self):
        with patch('builtins.print'):pilot.ready(self.mimo,True)
        self.transport.actions=['unknown'];self.transport.hook=lambda:(self.mimo/'PAUSE').touch();self.run_mimo()
        self.transport.hook=None;old=self.mimo;before=files_manifest(old);oldledger=cloud.Ledger(old).read()
        new=pilot.reprepare_mimo(self.comparison,self.root/'inherited-comparison',budget_usd='10.00')
        run=Path(new['mimo']['run']);self.assertEqual(read_json(run/'state.json')['calls'],read_json(old/'state.json')['calls'])
        summary=cloud.Ledger(run).summary();self.assertEqual(summary['reservations'],2)
        self.assertEqual(summary['unresolved_charge_ids'],['0002']);self.assertEqual(summary['readiness_calls'],1)
        self.assertEqual(summary['actual_reported_usd'],'0.001')
        self.transport.limit=self.transport.remaining='10'
        with patch('builtins.print'):
            ready=pilot.ready(run,True)
            ex.execute(self.root,run,stage='pilot',readiness=ready,resume=True,client_factory=pilot.factory(run,cloud.profile('10'),True))
        self.assertEqual(len(read_json(run/'state.json')['calls']),12)
        self.assertEqual(cloud.Ledger(run).summary()['readiness_calls'],2)
        self.assertEqual(cloud.Ledger(run).read()['reservations'][:2],oldledger['reservations'])
        self.assertEqual(files_manifest(old),before)
        with self.assertRaisesRegex(ValueError,'Two readiness'):pilot.ready(run,True)
        # Cost lookup can settle the inherited unknown charge, without changing the parent.
        cloud.CloudClient(cloud.BASE,cloud.MODEL,run=run).reconcile_costs()
        self.assertEqual(cloud.Ledger(run).summary()['unresolved_charge_ids'],[])
        self.assertEqual(files_manifest(old),before)

    def test_refresh_rejects_active_or_modified_parent_and_nonincrease(self):
        for amount in ('1','0.50'):
            with self.assertRaisesRegex(ValueError,'increase'):pilot.reprepare_mimo(self.comparison,self.root/'bad-budget',budget_usd=amount)
        s=read_json(self.mimo/'state.json');s['status']='running';atomic_json(self.mimo/'state.json',s)
        with self.assertRaisesRegex(ValueError,'stopped/paused'):pilot.reprepare_mimo(self.comparison,self.root/'active',budget_usd='10')
        s['status']='prepared_offline';atomic_json(self.mimo/'state.json',s)
        p=Path(self.paths['mimo']['preview'])/'units/g01-Y/request.json';p.write_text(p.read_text()+' ')
        with self.assertRaises(IntegrityError):pilot.reprepare_mimo(self.comparison,self.root/'changed',budget_usd='10')

    def test_inherited_billing_readiness_and_calls_cannot_be_reset(self):
        with patch('builtins.print'):pilot.ready(self.mimo,True)
        self.transport.hook=lambda:(self.mimo/'PAUSE').touch();self.run_mimo();self.transport.hook=None
        new=pilot.reprepare_mimo(self.comparison,self.root/'protected',budget_usd='10')
        run=Path(new['mimo']['run']);state=read_json(run/'state.json');cleared=copy.deepcopy(state);cleared['calls']=[]
        atomic_json(run/'state.json',cleared)
        with self.assertRaisesRegex(ValueError,'calls/time'):pilot.arm(run)
        atomic_json(run/'state.json',state)
        ready=read_json(run/'readiness-ledger.json');atomic_json(run/'readiness-ledger.json',{**ready,'attempts':[]})
        with self.assertRaisesRegex(ValueError,'readiness allowance'):pilot.arm(run)
        atomic_json(run/'readiness-ledger.json',ready)
        bill=read_json(run/'billing.json');atomic_json(run/'billing.json',{**bill,'reservations':[]})
        with self.assertRaisesRegex(IntegrityError,'Inherited charges'):cloud.Ledger(run)

    def test_future_approved_budget_is_configurable_without_changing_requests(self):
        first=pilot.reprepare_mimo(self.comparison,self.root/'ten',budget_usd='10')
        second=pilot.reprepare_mimo(Path(first['comparison']),self.root/'twenty-five',budget_usd='25.00')
        run=Path(second['mimo']['run']);self.assertEqual(cloud.Ledger(run).summary()['ceiling_usd'],'25.00')
        self.transport.limit=self.transport.remaining='25'
        with patch('builtins.print'):pilot.ready(run,True)
        sent=[b for method,path,b in self.transport.sent if method=='POST']
        self.assertEqual(len(sent),1);self.assertEqual(sent[0]['max_tokens'],2048)
        self.assertNotIn('budget_usd',sent[0])
        for request in (Path(first['mimo']['preview'])/'units').glob('*/request.json'):
            self.assertEqual(request.read_bytes(),(Path(second['mimo']['preview'])/'units'/request.parent.name/request.name).read_bytes())


class PolicyAndSecretTests(unittest.TestCase):
    def test_public_retention_less_than_100_no_zdr_requirement(self):
        self.assertEqual(cloud.route_check(endpoint())['tag'],'xiaomi/fp8')
        for days in (None,-1,100,101,'30',True):
            with self.assertRaises(cloud.AdmissionError):cloud.route_check(endpoint(),{**cloud.RETENTION,'documented_days':days})
        with self.assertRaises(cloud.AdmissionError):cloud.route_check(endpoint(),{**cloud.RETENTION,'training_reported':True})
        self.assertEqual(cloud.route_check(endpoint(),{**cloud.RETENTION,'documented_days':99})['tag'],cloud.TAG)

    def test_route_and_key_checks_fail_closed(self):
        for field,val in [('tag','deepinfra/fp8'),('provider_name','DeepInfra'),('quantization','fp4'),('status',1),
                          ('supported_parameters',[]),('service_tier','flex'),('max_completion_tokens',2048)]:
            e=endpoint();e['data']['endpoints'][0][field]=val
            with self.assertRaises((cloud.AdmissionError,IdentityError)):cloud.route_check(e)
        for value in ({'limit':1,'limit_remaining':1,'limit_reset':None},{'limit':10,'limit_remaining':10,'limit_reset':'daily'},
                      {'limit':1,'limit_remaining':1},{'limit':1,'limit_remaining':float('nan'),'limit_reset':None}):
            with self.assertRaises(cloud.AdmissionError):cloud.key_allowance({'data':value})

    def test_configured_key_limit_and_amount_validation(self):
        for budget in ('1','10','25.50'):
            d={'data':{'limit':budget,'limit_remaining':budget,'limit_reset':None}}
            self.assertEqual(cloud.key_allowance(d,budget),cloud.decimal(budget))
            with self.assertRaises(cloud.AdmissionError):cloud.key_allowance(d,'100')
        self.assertEqual(cloud.profile()['budget_usd'],'10.00')
        for invalid in ('0','-1','NaN','Infinity','0.001',None,True):
            with self.assertRaises(cloud.AdmissionError):cloud.profile(invalid)
        for d in ({'limit':10,'limit_remaining':11,'limit_reset':None},
                  {'limit':10,'limit_remaining':10,'limit_reset':'monthly'}):
            with self.assertRaises(cloud.AdmissionError):cloud.key_allowance({'data':d},'10')

    def test_nondefault_ledger_ceiling_persists_and_rejects_next_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);atomic_json(run/'binding.json',{'config':cloud.profile('0.10')})
            l=cloud.Ledger(run,create=True);body=cloud.body_for(tc.request(passage())['messages']);n=0
            while True:
                try:l.reserve(body,run/'calls'/str(n),cloud.Decimal('0.10'),'trial');n+=1
                except cloud.AdmissionError:break
            self.assertGreater(n,0);self.assertLess(n,16);self.assertLessEqual(l.exposure(l.read()),cloud.Decimal('.10'))
            self.assertEqual(cloud.Ledger(run).summary()['ceiling_usd'],'0.10')
            with self.assertRaises(cloud.AdmissionError):cloud.Ledger(run).admit(body,cloud.Decimal('10'))

    def test_fake_credential_only_validation_and_redaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fake';fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as f:f.write('fake-private-secret\n')
            self.assertEqual(cloud.read_key(path),'fake-private-secret')
            c=object.__new__(cloud.CloudClient);c._key='fake-private-secret'
            for value in (b'failure fake-private-secret',b'{"error":"fake-privat\\u0065-secret"}'):
                self.assertNotIn(b'fake-private-secret',c._redact(value));self.assertIn(b'REDACTED',c._redact(value))
            path.write_text('')
            with self.assertRaises(cloud.AdmissionError):cloud.read_key(path)
            path.unlink()
            with self.assertRaises(cloud.AdmissionError):cloud.read_key(path)

    def test_transport_exception_does_not_leak_key_and_no_redirect(self):
        c=object.__new__(cloud.CloudClient);c._key='fake-credential-do-not-print';c.timeout=1
        with patch.object(c,'_connection',side_effect=OSError(c._key)):
            # Construction errors are also sanitized, before any authorization header.
            with self.assertRaises(ProbeError) as raised:c._http('GET','/key')
        self.assertNotIn(c._key,str(raised.exception))
        with self.assertRaises(cloud.AdmissionError):c._http('GET','/endpoints/zdr')


if __name__=='__main__':unittest.main()
