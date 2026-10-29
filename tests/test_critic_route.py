"""Offline candidate critic protocol/context/routing regressions. No real key or HTTP."""
import copy
import json
import os
from pathlib import Path
import tempfile
from decimal import Decimal
import unittest
from unittest.mock import patch

from probe import critic_anchors as ca,critic_context as ctx,critic_route as route
from probe import cloud_critic as cloud,critic_pilot as pilot,experiment as ex,text_critic as tc
from probe.common import atomic_json,read_json,fingerprint,sha,files_manifest
from probe.recovery import ValidationError,diagnose
from probe.local_model import ProbeError
from probe.sciwrite_subset import finding_views
from test_critic_pilot import endpoint


def data(group='p1'):
    a=ca.anchor(fingerprint('candidate'),'s-p0001:b0',fingerprint('source'),r'Let \(x\) be real. Then \(x=x\).',{'source_id':'s','page':{'selected_page':1,'original_physical_page':5}})
    return {'protocol':ca.VERSION,'group_id':group,'candidate_sha256':a['candidate_sha256'],'draft_sha256':fingerprint([a]),
        'targets':[a],'context_anchors':[],'context_status':[],'bibliography':{'coverage':'unknown'}}


def answer(d,action='ok'):
    value={k:d[k] for k in ('protocol','group_id','candidate_sha256','draft_sha256')}
    value.update(coverage='complete',reviewed_anchor_ids=[a['id'] for a in d['targets']],context_needed=[],findings=[])
    if action in ('material','bad_anchor','bad_schema','visual','context_finding','editorial'):
        value['findings']=[{'id':d['group_id']+':f1','category':'editorial' if action=='editorial' else 'derivation',
            'anchor_ids':[d['targets'][0]['id']],'consequence':'A stated inference may not follow under the supplied assumptions.',
            'support':'This is a test assessment, not a real mathematical diagnosis.','proposed_correction':'',
            'severity':'low','uncertain':True,'context_required':['theorem 9.1'] if action=='context_finding' else [],
            'next_action':'source_image_review' if action=='visual' else 'editorial_review' if action=='editorial' else 'human_math_review',
            'claim_origin':'undetermined'}]
        if action=='bad_anchor':value['findings'][0]['anchor_ids']=['a-wrong']
        if action=='bad_schema':value['unexpected']='invalid'
    if action=='context':
        value.update(coverage='insufficient_context',context_needed=[{'reference':'theorem 9.1','reason':'The prior hypothesis is needed','anchor_ids':[d['targets'][0]['id']]}])
    if d['protocol']==ca.CURRENT_VERSION:
        value.pop('candidate_sha256');value.pop('draft_sha256')
        for f in value['findings']:
            f.update(assessment_kind='editorial' if action=='editorial' else 'context_only' if action=='context_finding' else 'material_concern',context_dependency='missing_evidence' if f['context_required'] else 'none')
    return value


class FakeLocal:
    actions=[];sent=[];hook=None
    def __init__(self,base_url,model=None,purpose=None,timeout=None,max_tokens=None):self.model=model;self.max_tokens=max_tokens
    def discover_model(self,out):return {'selected_model':self.model}
    def chat(self,messages,out,label,response_format=None,reasoning_effort='server-default'):
        d=json.loads(messages[1]['content'].split('<passage>\n')[1].split('\n</passage>')[0])
        action=self.actions.pop(0) if self.actions and d['group_id']!='ready' else 'ok'
        result=answer(d,action);content=json.dumps(result)
        if action=='drop':result['findings']=[];content=json.dumps(result)
        if d['protocol']==ca.CURRENT_VERSION and 'FORMAT REPAIR ONLY.' in messages[-1]['content']:
            packet=json.loads(messages[-1]['content'].split('\n',1)[1])
            changes=[]
            for error in packet['diagnostics']:
                path=error['path']
                changes.append({'path':path,'operation':'remove' if 'unexpected field' in error['message'] else 'replace','value':None if 'unexpected field' in error['message'] else [d['targets'][0]['id']]})
            if action=='drop':changes=[{'path':'$.findings','operation':'replace','value':[]}]
            content=json.dumps({'protocol':'critic-field-repair-v1','changes':changes})
        body={'model':self.model,'messages':messages,'max_tokens':self.max_tokens,'stream':False,'reasoning_effort':reasoning_effort}
        if response_format is not None:body['response_format']=response_format
        self.sent.append(copy.deepcopy(body));folder=out/'attempts'/'fake';folder.mkdir(parents=True)
        finish='length' if action in ('length','reasoning') else 'stop'
        usage={'prompt_tokens':30,'completion_tokens':100,'completion_tokens_details':{'reasoning_tokens':100 if action=='reasoning' else 95}}
        if action=='length':content='{"partial":'
        if action=='reasoning':content=None
        atomic_json(folder/'request.json',{'body':body});atomic_json(folder/'record.json',{'http_status':200,'latency_seconds':1})
        raw={'model':self.model,'usage':usage,'choices':[{'finish_reason':finish,'message':{'content':content}}]}
        atomic_json(folder/'response.raw',raw)
        if type(self).hook and d['group_id']!='ready':type(self).hook()
        return {'actual_model':self.model,'content':content,'finish_reason':finish,'usage':usage,'latency_seconds':1,'http_status':200}


class ContractTests(unittest.TestCase):
    def test_exact_python_quotes_and_hash_role_version_binding(self):
        d=data();v=answer(d,'material');f=tc.located_findings(v,d)[0]
        self.assertEqual(f['quotes'][0]['text'],d['targets'][0]['text']);self.assertEqual(f['quotes'][0]['end'],len(d['targets'][0]['text']))
        self.assertNotIn('quotes',ca.SCHEMA['properties']['findings']['items']['properties'])
        for field,new in [('candidate_sha256',fingerprint('other')),('draft_sha256',fingerprint('other')),('protocol','other')]:
            broken=copy.deepcopy(v);broken[field]=new
            with self.assertRaises(ValueError):tc.validate(broken,d)
        for field,new in [('source_block_sha256',fingerprint('other')),('text','shortened'),('end',1),('role','context')]:
            broken=copy.deepcopy(d);broken['targets'][0][field]=new
            with self.assertRaises(ValueError):ca.request(broken,route.local_config())
        for refs in (['a-unknown'],[d['targets'][0]['id']]*2):
            broken=copy.deepcopy(v);broken['findings'][0]['anchor_ids']=refs
            with self.assertRaises(ValueError):ca.validate(broken,d)

    def test_context_never_counts_as_target_and_missing_is_valid_unresolved(self):
        d=data();d['context_anchors']=[ca.anchor(d['candidate_sha256'],'s-p0001:b1',fingerprint('ctx'),'A prior definition.',{'page':1},'context')]
        v=answer(d,'context');ca.validate(v,d)
        self.assertEqual(ex.validate_completion({'actual_model':'m','finish_reason':'stop','content':json.dumps(v)}, {'kind':'critic'},d,'m')['assessment'],'insufficient_context')
        v['coverage']='complete'
        self.assertEqual(ex.validate_completion({'actual_model':'m','finish_reason':'stop','content':json.dumps(v)}, {'kind':'critic'},d,'m')['assessment'],'insufficient_context')
        v['reviewed_anchor_ids'].append(d['context_anchors'][0]['id'])
        with self.assertRaisesRegex(ValueError,'context-only'):ca.validate(v,d)

    def test_old_quotation_contract_remains_exact(self):
        from test_critic_followup import passage,answer as old_answer
        old=passage();v=old_answer(old);tc.validate(v,old);self.assertIs(tc.schema_for(old),tc.SCHEMA)
        v['findings'][0]['quotes'][0]['text']='invented'
        with self.assertRaises(ValueError):tc.validate(v,old)

    def test_provisional_only_from_complete_envelope_not_truncation(self):
        d=data();v=answer(d,'material');v['findings'].append({**v['findings'][0],'id':'p1:f2','anchor_ids':['wrong']})
        ev={'actual_model':'m','finish_reason':'stop','content':json.dumps(v)}
        out=tc.rejected_diagnostics(ev,d,'m');self.assertEqual(len(out['validated_findings']),1);self.assertEqual(len(out['invalid_findings']),1)
        self.assertEqual(tc.rejected_diagnostics({**ev,'finish_reason':'length'},d,'m')['status'],'unavailable')

    def test_second_opinion_does_not_leak_free_form_local_context_diagnoses(self):
        d=data();d['context_status']=[{'reference':'UNVERIFIED DIAGNOSIS IN QUERY','key':'UNVERIFIED DIAGNOSIS IN QUERY','reason':'A prior claim'}]
        neutral=route.neutral_second_opinion(d)
        self.assertEqual(neutral['targets'],d['targets']);self.assertEqual(neutral['context_anchors'],d['context_anchors'])
        self.assertNotIn('UNVERIFIED DIAGNOSIS',json.dumps(ca.request(neutral,route.paid_config(1))))
        self.assertIn('UNVERIFIED DIAGNOSIS',json.dumps(d))

    def test_repairs_only_invalid_fields_and_preserve_other_findings(self):
        d=data();bad=answer(d,'bad_anchor');good=answer(d,'material');fail={'actual_model':'m','finish_reason':'stop','content':json.dumps(bad)}
        ca.preserve_repair(fail,good,d,'m')
        good['findings'][0]['consequence']='Different mathematical claim'
        with self.assertRaisesRegex(ValueError,'unrelated'):ca.preserve_repair(fail,good,d,'m')
        with self.assertRaisesRegex(ValueError,'count'):ca.preserve_repair(fail,answer(d),d,'m')

    def test_low_severity_material_and_draft_separated_display(self):
        d=data();a=ca.located_findings(answer(d,'material'),d)[0];b={**a,'id':'another','draft_sha256':fingerprint('other')}
        views=finding_views([a,b,{**a,'id':'duplicate','call':'0002'}]);self.assertEqual(len(views['material']),2);self.assertFalse(views['editorial'])
        self.assertEqual(len(views['material'][0]['contributors']),2)
        self.assertEqual(len(finding_views(ca.located_findings(answer(d,'context_finding'),d))['context']),1)

    def test_truncation_even_when_reasoning_dominates_and_missing_counters(self):
        base={'actual_model':'m','http_status':200,'finish_reason':'length','usage':{'completion_tokens':100,'completion_tokens_details':{'reasoning_tokens':99}}}
        self.assertEqual(diagnose(ProbeError('length'),{**base,'content':'{"partial":'},'m')['kind'],'output_truncated')
        self.assertEqual(diagnose(ProbeError('length'),{**base,'content':None,'usage':{}},'m')['kind'],'budget_exhausted_unknown')


class RouteTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        (self.root/'runs').mkdir();(self.root/'results').mkdir();self.patches=[]
        for obj,name,val in [(route,'ROOT',self.root),(pilot,'ROOT',self.root)]:self.start(patch.object(obj,name,val))
        self.start(patch('probe.experiment.converter_idle',return_value={'owned_converter_pids':[]}))
        self.start(patch.object(cloud,'read_key',side_effect=AssertionError('Local operation read a key')))
        self.start(patch.object(cloud.CloudClient,'_http',side_effect=AssertionError('Local operation called cloud')))
        self.source=self.root/'source.pdf';self.source.write_bytes(b'fake saved input, not parsed because loader mocked')
        blocks=[]
        for i,text in enumerate(('A complete first passage.', 'Theorem 9.1: The prior hypothesis is local.', 'Proof. A complete second passage.')):
            blocks.append({'id':f's-p0001:b{i}','reading_order':i,'source_block_index':i,'kind':'text','bbox':[0,.1,.9,.2],
                'bbox_pdf_points':[0,10,90,20],'native':{'type':'text','content':text}})
        page={'source_id':'s','page_id':'s-p0001','source_attempt':'attempt','page':{'selected_page':1,'original_physical_page':5,'owner':True},'blocks':blocks}
        self.conversion=self.root/'conversion';self.conversion.mkdir();(self.conversion/'attempt/output').mkdir(parents=True)
        atomic_json(self.conversion/'state.json',{'settings':{'sources':{'s':{'pdf':'source.pdf','sha256':sha(self.source),'pages':1,'original_pages':[5]}}}})
        atomic_json(self.conversion/'attempt/page-map.json',[page['page']]);atomic_json(self.conversion/'attempt/output/middle_json.json',{'pages':[page]})
        self.start(patch('probe.saved_pages.saved_pages',return_value=[page]))
        self.candidate=self.root/'candidate';self.candidate.mkdir();inv=[]
        for b in blocks:
            inv.append({'block_id':b['id'],'page_id':'s-p0001','source_block_sha256':fingerprint(b),'after':b['native']['content'],
                'draft_sha256':fingerprint(b['native']['content']),'status':'supported','review_status':'completed','source_location':{'source_id':'s','page':page['page'],'bbox':b['bbox']}})
        atomic_json(self.candidate/'inventory.json',inv);atomic_json(self.candidate/'provenance.json',{'bindings':{}})
        (self.candidate/'candidate.tex').write_text('Complete candidate');ex.seal(self.candidate)
        _,_,_,version=route.candidate_rows(self.candidate)
        self.passages=self.root/'passages.json';atomic_json(self.passages,{'schema':'candidate-passages-v1','candidate_manifest_sha256':sha(self.candidate/'manifest.json'),
            'candidate_sha256':version,'boundary_status':'reviewed','passages':[
                {'id':'p1','block_ids':['s-p0001:b0'],'boundary_reviewed':True,'boundary_basis':'whole complete statement'},
                {'id':'p2','block_ids':['s-p0001:b2'],'boundary_reviewed':True,'boundary_basis':'whole complete statement'}]})
        FakeLocal.actions=[];FakeLocal.sent=[];FakeLocal.hook=None

    def start(self,p):value=p.start();self.addCleanup(p.stop);return value
    def prepare(self,extras=2):
        paths=route.prepare(self.candidate,self.conversion,'s',self.passages,recovery_calls=extras,hours=1)
        return Path(paths['run']),Path(paths['preview'])
    def readiness(self,run):
        m=read_json(Path(read_json(run/'binding.json')['preview'])/'preview.json');p=self.root/(run.name+'-ready');p.mkdir(exist_ok=True)
        atomic_json(p/'readiness.json',{'config':m['config'],'finished_at':ex.now(),'text':'passed','vision':'not_requested_text_only'});ex.seal(p);return p
    def execute(self,run,resume=False):
        ready=self.readiness(run)
        with patch('builtins.print'):return ex.execute(self.root,run,stage='route',readiness=ready,resume=resume,client_factory=FakeLocal)

    def test_candidate_only_exact_coverage_and_no_answer_leakage(self):
        before=files_manifest(self.candidate);r,p=self.prepare();m,u=ex.verify_preview(p)
        self.assertEqual(m['config']['profile'],'glm');self.assertEqual(len(u),2)
        self.assertEqual(read_json(p/'coverage.json')['target_blocks'],['s-p0001:b0','s-p0001:b2'])
        self.assertEqual(read_json(p/'coverage.json')['outside_selected_scope'],['s-p0001:b1'])
        for unit in u:
            body=read_json(p/unit['request']);self.assertEqual(body['reasoning_effort'],'high');self.assertNotIn('boundary_basis',json.dumps(body))
        self.execute(r);self.assertEqual(read_json(r/'state.json')['status'],'completed');self.assertEqual(files_manifest(self.candidate),before)

    def test_duplicate_preparation_and_stale_candidate_refused(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError,'already exists'):self.prepare()
        (self.candidate/'candidate.tex').write_text('changed')
        with self.assertRaises(ValueError):self.prepare()

    def test_unused_changed_code_preparation_is_linked_but_consumed_cohort_cannot_reset(self):
        r,p=self.prepare();before=files_manifest(r);hashes=ex.code_hashes()
        marker=self.root/'implementation-change';marker.write_text('v1')
        with patch.object(ex,'code_hashes',return_value={**hashes,str(marker):sha(marker)}):
            r2,p2=self.prepare()
            lineage=read_json(p2/'preview.json')['critic_route']['superseded_unused_preparations']
            self.assertEqual(lineage[0]['run'],str(r));self.assertEqual(files_manifest(r),before)
            self.execute(r2)
        marker.write_text('v2')
        with patch.object(ex,'code_hashes',return_value={**hashes,str(marker):sha(marker)}):
            with self.assertRaisesRegex(ValueError,'consumed attempts/time'):self.prepare()

    def test_editable_boundaries_do_not_guess_groups(self):
        out=self.root/'boundary.json';result=route.boundary_template(self.candidate,out)
        self.assertEqual(result['passages'],[]);self.assertEqual(result['boundary_status'],'unresolved_edit_required')

    def test_whole_paragraph_and_target_order_cannot_be_silently_reduced(self):
        r,p=self.prepare();d=read_json(p/'units/p1/input.json');original=read_json(self.candidate/'inventory.json')[0]['after']
        self.assertEqual(d['targets'][0]['text'],original)
        self.assertEqual(d['targets'][0]['end'],len(original))
        selection=read_json(self.passages);selection['passages'][0]['block_ids']=['s-p0001:b1','s-p0001:b0']
        atomic_json(self.passages,selection)
        with self.assertRaisesRegex(ValueError,'reading order'):self.prepare()

    def test_ambiguous_missing_reference_and_no_context_truncation(self):
        _,_,_,_,index,_=route.prepare_index(self.candidate,self.conversion,'s')
        rows,rec=ctx.resolve(index,['theorem 9.1']);self.assertTrue(rows);self.assertEqual(rec[0]['status'],'added')
        index['entries']['theorem 9.1']*=2
        self.assertEqual(ctx.resolve(index,['theorem 9.1'])[1][0]['status'],'ambiguous')
        self.assertIn('unavailable',ctx.resolve(index,['Theorem 8.2'])[1][0]['status'])
        index['entries']['theorem 9.1']=index['entries']['theorem 9.1'][:1]
        self.assertEqual(ctx.resolve(index,['theorem 9.1'],policy={**ctx.POLICY,'max_characters':1})[0],[])

    def test_context_and_format_share_limits_resume_does_not_duplicate(self):
        r,p=self.prepare(extras=2);FakeLocal.actions=['context','bad_anchor','material','ok']
        self.execute(r);s=read_json(r/'state.json')
        self.assertEqual([c['method'] for c in s['calls']],['baseline','context_reassessment','json_feedback','baseline'])
        calls=len(s['calls']);self.execute(r,True);self.assertEqual(len(read_json(r/'state.json')['calls']),calls)
        extra=read_json(r/'calls/0002/input.json');self.assertTrue(extra['context_anchors']);self.assertEqual(extra['targets'],read_json(p/'units/p1/input.json')['targets'])

    def test_context_once_and_shared_limit_leaves_visible_gap(self):
        r,p=self.prepare(extras=1);FakeLocal.actions=['context','bad_anchor','ok'];self.execute(r)
        s=read_json(r/'state.json');self.assertEqual(len(s['calls']),3);self.assertTrue(s['units']['p1']['limits'])
        report=read_json(r/'route-summary.json');self.assertTrue(report['queues']['technical']);self.assertTrue(report['queues']['context'])

    def test_field_patch_allowance_survives_resume_and_keeps_original_findings(self):
        r,p=self.prepare();FakeLocal.actions=['bad_anchor','drop','material','ok'];self.execute(r)
        before=files_manifest(r/'calls');s=read_json(r/'state.json')
        self.assertEqual([c['method'] for c in s['calls']],['baseline','json_feedback','json_feedback','baseline'])
        final=read_json(r/'calls/0003/outcome.json')
        self.assertEqual(final['status'],'completed')
        raw=json.loads(read_json(r/'calls/0001/assistant-response.json')['content'])['findings'][0]
        after=final['answer']['findings'][0]
        self.assertEqual({k:v for k,v in raw.items() if k!='anchor_ids'},{k:v for k,v in after.items() if k!='anchor_ids'})
        self.execute(r,True)
        self.assertEqual(files_manifest(r/'calls'),before)
        self.assertEqual(len(read_json(r/'state.json')['calls']),4)

    def test_pause_resume_and_local_readiness_never_access_key(self):
        r,p=self.prepare();FakeLocal.hook=lambda:(r/'PAUSE').touch()
        with patch('builtins.print'):route.live(r,client_factory=FakeLocal)
        self.assertEqual(len(read_json(r/'state.json')['calls']),1)
        FakeLocal.hook=None
        with patch('builtins.print'):route.live(r,resume=True,client_factory=FakeLocal)
        self.assertEqual(len(read_json(r/'state.json')['calls']),2)
        self.assertEqual(len(read_json(r/'readiness-ledger.json')['attempts']),1)

    def test_output_exhaustion_has_no_identical_or_lower_effort_retry(self):
        r,p=self.prepare();FakeLocal.actions=['length','reasoning'];self.execute(r)
        s=read_json(r/'state.json');self.assertEqual(len(s['calls']),2)
        self.assertEqual([read_json(r/'calls'/c['id']/'outcome.json')['failure']['kind'] for c in s['calls']],['output_truncated','reasoning_exhausted'])
        self.assertTrue(all(b['reasoning_effort']=='high' for b in FakeLocal.sent))


class PaidRouteTests(unittest.TestCase):
    start=RouteTests.start
    prepare=RouteTests.prepare
    readiness=RouteTests.readiness
    execute=RouteTests.execute
    def setUp(self):
        RouteTests.setUp(self);self.cloud_sent=[];self.remaining='10';self.paid_actions=[]
        self.start(patch.object(cloud,'read_key',return_value='fake-test-credential-only'))
        self.start(patch.object(cloud.CloudClient,'_http',lambda client,*a,**kw:self.http(client,*a,**kw)))

    def http(self,client,method,path,body=None):
        self.cloud_sent.append((method,path,copy.deepcopy(body)))
        if method=='GET':
            if path=='/key':value={'data':{'limit':10,'limit_remaining':self.remaining,'limit_reset':None}}
            elif path.endswith('/endpoints'):value=endpoint()
            else:raise AssertionError('Unexpected hosted metadata operation')
        else:
            d=json.loads(body['messages'][1]['content'].split('<passage>\n')[1].split('\n</passage>')[0])
            if d.get('protocol'):
                action=self.paid_actions.pop(0) if self.paid_actions else 'ok';v=answer(d,action)
                if body.get('response_format',{}).get('json_schema',{}).get('name')=='critic_field_repair_v1':
                    packet=json.loads(body['messages'][-1]['content'].split('\n',1)[1])
                    v={'protocol':'critic-field-repair-v1','changes':[{'path':e['path'],'operation':'replace','value':v['findings'][0]['anchor_ids'] if v['findings'] else [d['targets'][0]['id']]} for e in packet['diagnostics']]}
            else:
                from test_critic_followup import answer as legacy_answer
                v=legacy_answer(d)
            value={'id':'fake-'+str(len(self.cloud_sent)),'model':cloud.MODEL,'provider':'Xiaomi',
                'usage':{'prompt_tokens':100,'completion_tokens':200,'cost':'.001'},
                'choices':[{'finish_reason':'stop','message':{'content':json.dumps(v)}}]}
        return 200,json.dumps(value).encode(),1.0

    def paid_parent(self):
        from probe.recovery_trial import save_unit,finish_preview
        from test_critic_followup import passage
        parents=[]
        for part,ids in enumerate((pilot.SAMPLE[:4],pilot.SAMPLE[4:])):
            p=self.root/f'historical-input-{part}';p.mkdir();r=self.root/f'historical-{part}';units=[]
            for identity in ids:
                d=passage(identity[:3]);units.append(save_unit(p,identity,d,tc.request(d,max_tokens=32768),kind='critic',
                    gate=False,split='development',version='candidate',location={'page':1,'blocks':['p:b1']}))
            finish_preview(p,units,'critic',{**tc.PROFILES['deepseek'],'max_tokens':32768},{},pilot.LIMITS,{},{});ex.initialize(p,r);parents.append(r)
        paths=pilot.prepare(self.root/'comparison',gate=parents[0],overnight=parents[1]);r=Path(paths['mimo']['run'])
        ready=self.readiness(r)
        with patch('builtins.print'):ex.execute(self.root,r,stage='pilot',readiness=ready,client_factory=pilot.factory(r,cloud.CONFIG,True))
        self.assertEqual(read_json(r/'state.json')['status'],'completed')
        return r

    def test_selective_costed_stage_preserves_prior_spending_and_requests(self):
        parent=self.paid_parent();before=files_manifest(parent);r,p=self.prepare();FakeLocal.actions=['material','ok'];self.execute(r)
        plan=route.select(r,parent);sel=read_json(plan/'selection.json');self.assertEqual(len(sel['selected']),2);self.assertEqual(sel['clean_selected'],['p2'])
        cost=read_json(plan/'cost-preview.json');self.assertEqual(cost['selected_passages'],2);self.assertEqual(cost['empirical']['actual_usd'],'0.012')
        self.assertGreater(Decimal(cost['conservative_bounds']['total_new_stage_usd']),Decimal(cost['estimated_stage_usd']))
        prepared=route.prepare_mimo(plan);paid=Path(prepared['run']);pp=Path(prepared['preview'])
        self.assertEqual(cloud.Ledger(paid).summary()['actual_reported_usd'],'0.012')
        bodies=[read_json(pp/u['request']) for u in read_json(pp/'units.json')]
        self.assertTrue(all('previous_assessment' not in json.dumps(b) and 'A stated inference' not in json.dumps(b) for b in bodies))
        self.assertTrue(all(b['provider']['only']==['xiaomi/fp8'] and b['response_format']['json_schema']['schema']==ca.SCHEMA_V3 for b in bodies))
        with patch('builtins.print'):route.live(paid,allow_paid=True)
        self.assertEqual(read_json(paid/'state.json')['status'],'completed')
        self.assertEqual(cloud.Ledger(paid).summary()['actual_reported_usd'],'0.015')
        self.assertEqual(files_manifest(parent),before)
        self.assertEqual(read_json(paid/'route-summary.json')['summary']['second_opinion']['additional_paid_calls'],2)
        with self.assertRaisesRegex(ValueError,'already has'):route.prepare_mimo(plan)

    def test_live_key_remaining_can_block_despite_historical_local_allowance(self):
        parent=self.paid_parent();r,p=self.prepare();self.execute(r);plan=route.select(r,parent);prepared=route.prepare_mimo(plan)
        paid=Path(prepared['run']);self.remaining='0.0001';count=len(self.cloud_sent)
        with self.assertRaises(cloud.AdmissionError):route.live(paid,allow_paid=True)
        self.assertFalse(any(method=='POST' for method,path,body in self.cloud_sent[count:]));self.assertEqual(cloud.Ledger(paid).summary()['current_stage_reservations'],0)

    def test_prior_unknown_reservations_and_new_stage_caps_not_reset(self):
        run=self.root/'bill';run.mkdir();prior=self.root/'prior.json'
        atomic_json(prior,{'summary':{'ceiling_usd':'10.00','actual_reported_usd':'9.90','unresolved_reserved_usd':'.09','reservations':15,'unresolved_charge_ids':['0015'],'halt':None}})
        atomic_json(run/'binding.json',{'config':route.paid_config(1),'prior_billing':{'path':str(prior),'sha256':sha(prior)}})
        ledger=cloud.Ledger(run,create=True)
        with self.assertRaises(cloud.AdmissionError):ledger.admit(ca.request(data(),route.paid_config(1)),Decimal('10'))
        self.assertEqual(ledger.summary()['remaining_local_usd'],'0.01')
        prior.write_text('{}')
        with self.assertRaises(ValueError):ledger.read()

    def test_paid_stage_preserves_consumed_local_followups(self):
        parent=self.paid_parent();r,p=self.prepare();FakeLocal.actions=['bad_anchor','drop','material','ok'];self.execute(r)
        self.assertEqual(sum(c['parent']=='p1' and c['method']!='baseline' for c in read_json(r/'state.json')['calls']),2)
        with self.assertRaisesRegex(ValueError,'budget exhausted'):route.select(r,parent)

    def test_second_opinion_itself_consumes_shared_passage_and_global_allowance(self):
        parent=self.paid_parent();r,p=self.prepare(extras=3);FakeLocal.actions=['bad_anchor','material','ok'];self.execute(r)
        plan=route.select(r,parent);prepared=route.prepare_mimo(plan);paid=Path(prepared['run']);self.paid_actions=['ok','bad_anchor','ok']
        with patch('builtins.print'):route.live(paid,allow_paid=True)
        calls=read_json(paid/'state.json')['calls'];self.assertEqual(len(calls),2)
        self.assertEqual(sum(c['method']!='baseline' for c in calls),0)
        self.assertIn('shared follow-up',read_json(paid/'state.json')['units']['p1']['limits'][0])

    def test_pilot_stays_fixed_and_cloud_cannot_be_default(self):
        with self.assertRaises(KeyError):route.local_config('mimo')
        with self.assertRaises(ValueError):cloud.validate_config({**route.paid_config(4),'paid_limits':{'trial_calls':7,'readiness_calls':1}})
        d=data();body=ca.request(d,route.local_config());self.assertNotIn('provider',body)
