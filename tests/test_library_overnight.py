import copy,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from probe.common import atomic_json,read_json,sha,fingerprint,files_manifest
from probe import library_paid as paid,library_fallbacks as fallback,kimi_escalation,mathpix_experiment
from scripts import library_pipeline as c,mathpix_comparison as mx,prepare_library_overnight as prep
import test_library_pipeline as fixtures

class Overnight(unittest.TestCase):
 def setUp(self):
  self.h=fixtures.Pipeline();self.h.setUp();self.addCleanup(self.h.doCleanups);h=self.h
  p=read_json(h.run/'plan.json');p['overnight']=True;p['paid_enabled']=True;p['spend_cap_usd']='7.00'
  metadata=read_json(c.ROOT/'results/library-overnight-20261107/kimi-public/metadata.json');config=kimi_escalation.profile(metadata,'7.00',20);config.update(paid_limits=None,no_generation_deadline=True)
  self.approval={'explicitly_approved':True,'new_spend_cap_usd':'7.00','ledger_root':str(h.run/'fallback-budget'),'sources':{h.sid:{'sha256':'a'*64,'physical_pages':[1]}},'provider_metadata_current':True,'mathpix_price_per_page_usd':'0.005'}
  p.update(paid_approval=self.approval,kimi_config=config,prior_billing=None);atomic_json(h.run/'plan.json',p)
  b=read_json(h.run/'binding.json');b.update(plan_sha256=sha(h.run/'plan.json'),config=config,prior_billing=None,code=c.base.code_binding());atomic_json(h.run/'binding.json',b);h.s['paid_approval_sha256']=fingerprint(self.approval);c.save(h.run,h.s)
 def factory(self,answer):
  class Client:
   calls=0
   def __init__(self,run):pass
   def dispatch(inner,task,body,folder):
    Client.calls+=1;self.assertTrue(any(x['type']=='image_url' for x in body['messages'][0]['content']));self.assertTrue(read_json(self.h.run/'fallback-budget/ledger.json')['reservations'])
    folder.mkdir(parents=True,exist_ok=True);a=answer(body) if callable(answer) else answer;r={'status':'complete_response','usage':{'completion_tokens':10},'elapsed_seconds':.01};atomic_json(folder/'outcome.json',r);(folder/'answer.txt').write_text(a);return a,r
  return Client
 def test_failed_conversion_recovers_then_actual_critic_receives_exact_kimi_draft(self):
  h=self.h;h.fail_convert=True;h.coordinate();self.assertEqual(len(h.seen),1)
  Client=self.factory('```tex\n'+fixtures.DOC+'\n```');paid.model_round(h.run,h.s,client_factory=Client);self.assertEqual(Client.calls,1);self.assertEqual(h.s['tasks'][1]['status'],'pending');self.assertNotIn('convert',h.s['versions'][h.key])
  selected=h.s['versions'][h.key]['kimi-convert'];draft=(h.run/selected['path']).read_text()
  def transport(run,call,body,**kw):
   payload=c.vision.request_payload(body);self.assertEqual(payload['draft'],draft);self.assertEqual(payload['base_sha256'],selected['sha256']);h.seen.append(call['parent'])
   answer=json.dumps({'base_sha256':payload['base_sha256'],'scope_review':{'full_assigned_scope_reviewed':True,'additional_findings_remain':False,'unreviewed_scope':''},'findings':[]})
   call.update(status='completed_response',elapsed_seconds=.01,metadata={'actual_model':'glm53-regular','usage':{'prompt_tokens':777,'completion_tokens':10}});folder=run/'calls'/call['id'];folder.mkdir(parents=True);atomic_json(folder/'request.json',body);atomic_json(folder/'attempts/one/request.json',{'body':body});(folder/'content.txt').write_text(answer);atomic_json(folder/'outcome.json',call);atomic_json(folder/'manifest.json',files_manifest(folder));call['seal']=sha(folder/'manifest.json');return answer,call
  h.transport=transport;h.coordinate();self.assertEqual(len(h.seen),2);self.assertTrue(h.s['documents'][h.sid]['selected_new_generation']);self.assertEqual(h.s['documents'][h.sid]['publication_revision'],2)
  paid.model_round(h.run,h.s,client_factory=Client);h.coordinate();self.assertEqual(Client.calls,1);self.assertEqual(len(h.seen),2);c.verify(h.run)
 def test_failed_review_preserves_conversion_and_recovery_is_a_separate_derivative(self):
  h=self.h;old=h.transport
  def failed(run,call,body,**kw):
   ans,record=old(run,call,body,**kw)
   if call['parent'].endswith('/critic'):record['status']='failed';return None,record
   return ans,record
  h.transport=failed;h.coordinate();base=h.s['versions'][h.key]['convert'];before=sha(h.run/base['path'])
  def answer(body):
   # Existing Kimi schema puts the exact selected text/hash in its metadata.
   txt=body['messages'][0]['content'][0]['text'];data=json.loads(txt[txt.index('{'):]);return json.dumps({'base_sha256':data['base_sha256'],'findings':[]})
  Client=self.factory(answer);paid.model_round(h.run,h.s,client_factory=Client);self.assertEqual(Client.calls,1);self.assertIn('kimi-critic',h.s['versions'][h.key]);self.assertEqual(sha(h.run/base['path']),before);self.assertEqual(h.s['tasks'][1]['status'],'failed');self.assertIn('review_coverage',h.s['tasks'][1]['paid_recovery'])
 def test_changed_original_image_or_draft_is_rejected(self):
  h=self.h;h.fail_convert=True;h.coordinate();p=h.run/'sources'/h.sid/'page-001.png';p.write_bytes(b'changed')
  with self.assertRaises((ValueError,c.runtime.Fatal)):paid.model_round(h.run,h.s,client_factory=self.factory(fixtures.DOC))
 def test_combined_cap_dynamic_scopes_restart_and_uncertain_reservations(self):
  h=self.h
  def rec(i,kind):
   u={'id':i,'source_id':h.sid,'source_sha256':'a'*64,'physical_pages':[1]};r={'kind':kind,'phase':'extraction' if kind=='mathpix' else 'critic','unit':u,'scope_sha256':fingerprint(u)};fallback.register_scope(h.run,r,self.approval,unit_verified=True);return r
  one=rec('one','mathpix');two=rec('two','kimi');three=rec('three','kimi')
  identity,fresh=fallback.reserve_budget(h.run,one,'3.5',self.approval);self.assertTrue(fresh);fallback.reserve_budget(h.run,two,'3.5',self.approval)
  with self.assertRaises(fallback.NotApproved):fallback.reserve_budget(h.run,three,'.01',self.approval)
  self.assertFalse(fallback.reserve_budget(h.run,one,'3.5',self.approval)[1]);self.assertEqual(fallback.budget_summary(h.run,self.approval)['exposure_usd'],'7.0')
  with self.assertRaises(ValueError):fallback.reserve_budget(h.run,three,'.01',dict(self.approval,new_spend_cap_usd='8'))
 def test_registered_scope_cannot_expand_to_other_source_or_page(self):
  u={'id':'bad','source_id':self.h.sid,'source_sha256':'a'*64,'physical_pages':[2]};r={'kind':'kimi','phase':'critic','unit':u,'scope_sha256':fingerprint(u)}
  with self.assertRaises(ValueError):fallback.register_scope(self.h.run,r,self.approval,unit_verified=True)
 def test_budget_denial_does_not_stop_independent_local_work(self):
  h=self.h;h.fail_convert=True;h.coordinate()
  with patch.object(fallback,'run_kimi',side_effect=fallback.NotApproved('cap reached')):paid.model_round(h.run,h.s)
  self.assertEqual(h.s['tasks'][0]['paid_recovery']['status'],'blocked_or_failed');self.assertEqual(h.s['calls'][0]['status'],'failed');self.assertFalse(h.s['documents'][h.sid]['selected_new_generation'])
 def test_failed_extraction_retrieval_page_mapping_direct_tex_and_downstream_use(self):
  h=self.h;p=read_json(h.run/'plan.json');p['documents'][0]['pages'][0]['image']=p['documents'][0]['pages'][0]['path'];atomic_json(h.run/'plan.json',p);b=read_json(h.run/'binding.json');b['plan_sha256']=sha(h.run/'plan.json');atomic_json(h.run/'binding.json',b)
  h.s['documents'][h.sid].update(units=[],planning_done=False);h.s.update(tasks=[],source_units={},derived_inputs={},inputs_prepared=False);h.s.pop('task_plan_sha256',None);h.s['extraction']['mineru_pro']['pages'][h.sid+'-p1']['status']='failed';c.save(h.run,h.s)
  payload=io.BytesIO()
  with zipfile.ZipFile(payload,'w') as z:z.writestr('main.tex',fixtures.DOC)
  class Client:
   calls=0;key_id='mock-key'
   def redact(self,v):return v
   def safe_bytes(self,b):return b
   def submit(self,pdf,name):self.calls+=1;return 'existing-id',{'pdf_id':'existing-id'}
   def get_json(self,path):
    if path.startswith('ocr-usage'):return {'ocr_usage':[]}
    if path.startswith('converter'):return {'conversion_status':{'tex.zip':{'status':'completed'}}}
    return {'status':'completed','num_pages':1}
   def request(self,path):
    if path.endswith('.zip'):return payload.getvalue()
    if path.endswith('.json'):return json.dumps({'pages':[{'page':1,'lines':[{'text':'Complete source condition x positive, the assigned expression is $x^2=1$ and the definition retained.'}]}]}).encode()
    return b'Complete source text'
  ledger=h.root/'mx-ledger';ledger.mkdir();client=Client()
  with patch.object(mx,'LEDGER',ledger),patch.object(c.compiler_environment,'compile_saved',side_effect=AssertionError('No compilation')):
   self.assertFalse(paid.extraction_round(h.run,h.s,client=client));self.assertEqual(client.calls,1);self.assertEqual(h.s['mathpix_pages'][h.sid+'-p1']['source_sha256'],'a'*64)
   c.plan_units(h.run,h.s);self.assertEqual(h.s['tasks'][0]['conversion_origin'],'Mathpix direct TeX; no local rewriting request');self.assertEqual(h.s['tasks'][1]['status'],'pending')
   paid.extraction_round(h.run,h.s,client=client);self.assertEqual(client.calls,1)
 def test_mathpix_unknown_submission_never_reposts_across_restart(self):
  h=self.h;pdf=h.run/'subset.pdf';pdf.write_bytes(b'%PDF-fixture');u={'id':'subset','source_id':h.sid,'source_sha256':'a'*64,'physical_pages':[1],'subset':str(pdf),'subset_sha256':sha(pdf)};r={'kind':'mathpix','phase':'extraction','unit':u,'scope_sha256':fingerprint(u)};fallback.register_scope(h.run,r,self.approval,unit_verified=True)
  class Client:
   key_id='fake';calls=0
   def redact(self,v):return v
   def get_json(self,p):return {'ocr_usage':[]}
   def submit(self,pdf,name):self.calls+=1;raise OSError('disconnect')
  ledger=h.root/'mx';ledger.mkdir();client=Client()
  with patch.object(mx,'LEDGER',ledger):
   a=fallback.run_mathpix(h.run,r,self.approval,client=client);b=fallback.run_mathpix(h.run,r,self.approval,client=client)
  self.assertEqual(client.calls,1);self.assertEqual(a,b);self.assertEqual(a['status'],'uncertain_submission')
 def test_finished_resume_makes_no_provider_or_local_calls(self):
  h=self.h;h.s['status']=c.TERMINAL;c.save(h.run,h.s)
  with patch.object(c.sys,'argv',['pipeline','resume','--run',str(h.run)]),patch.object(paid,'runtime_authorise',side_effect=AssertionError('No paid startup')),patch.object(c.subprocess,'run',side_effect=AssertionError('No dispatch')):c.main()

 def test_actual_worker_lifecycle_recovers_publishes_and_finished_restart_is_inert(self):
  h=self.h;h.s['extraction_done']=True;c.save(h.run,h.s);h.fail_convert=True;normal=h.transport
  def transport(run,call,body,**kw):
   if call['parent'].endswith('/convert'):return normal(run,call,body,**kw)
   payload=c.vision.request_payload(body);candidate=h.s.get('current_versions',{})
   answer=json.dumps({'base_sha256':payload['base_sha256'],'scope_review':{'full_assigned_scope_reviewed':True,'additional_findings_remain':False,'unreviewed_scope':''},'findings':[]})
   call.update(status='completed_response',elapsed_seconds=.01,metadata={'actual_model':'glm53-regular','usage':{'prompt_tokens':777,'completion_tokens':10}})
   folder=run/'calls'/call['id'];folder.mkdir(parents=True);atomic_json(folder/'request.json',body);atomic_json(folder/'attempts/one/request.json',{'body':body});(folder/'content.txt').write_text(answer);atomic_json(folder/'outcome.json',call);atomic_json(folder/'manifest.json',files_manifest(folder));call['seal']=sha(folder/'manifest.json');return answer,call
  Client=self.factory('```tex\n'+fixtures.DOC+'\n```');model_round=paid.model_round;coordinate=c.scheduler.coordinate
  def coordinate_mock(*args,**kwargs):return coordinate(*args,**kwargs,transport=transport,poll_seconds=.001)
  with patch.object(c.os,'dup2'),patch.object(c.runtime,'check_other_jobs'),patch.object(c.base.books.speed,'module',return_value=object()),patch.object(c.base.books.book,'arrange_glm'),patch.object(c.base.books.speed,'effort_check',return_value={'status':'supported'}),patch.object(c.base.books.speed,'sampler',return_value=h.sample),patch.object(c.subprocess,'run',side_effect=h.cpu),patch.object(c.scheduler,'coordinate',side_effect=coordinate_mock),patch.object(paid,'model_round',side_effect=lambda run,state,**kw:model_round(run,state,client_factory=Client,**kw)),patch.object(c,'bundle',return_value={'mock':'bundle'}),patch.object(c.compiler_environment,'compile_saved',side_effect=AssertionError('No compiler')):
   c.worker(h.run);state=read_json(h.run/'state.json');self.assertEqual(state['status'],c.TERMINAL);self.assertEqual(len(state['calls']),2);self.assertEqual(Client.calls,1);self.assertTrue(state['documents'][h.sid]['selected_new_generation'])
   from probe.experiment import verify_seal
   verify_seal(h.run/'deliveries'/h.sid);verify_seal(Path(state['documents'][h.sid]['delivery']))
   digest=sha(h.run/'state.json');c.worker(h.run);self.assertEqual(digest,sha(h.run/'state.json'));self.assertEqual(Client.calls,1)

 def test_crash_after_recovery_pointer_before_checkpoint_resumes_publication(self):
  h=self.h;h.coordinate();old=copy.deepcopy(h.s['documents'][h.sid]['publication']);h.s['documents'][h.sid]['needs_republication']=True;c.publish_settled(h.run,h.s,h.sid)
  expected=copy.deepcopy(h.s['documents'][h.sid]['publication']);self.assertTrue(expected['generation'].endswith('-r2'))
  h.s['documents'][h.sid].update(publication=old,published=False,selected_new_generation=False);c.save(h.run,h.s)
  c.verify(h.run);c.publish_settled(h.run,h.s,h.sid);self.assertEqual(h.s['documents'][h.sid]['publication'],expected);self.assertEqual(len(h.seen),2)
  from probe.experiment import verify_seal
  verify_seal(h.run/'deliveries'/h.sid)

 def test_saved_sealed_response_uses_real_request_binding_without_dispatch(self):
  h=self.h;h.coordinate();call=h.s['calls'][0];body=c.body_for(h.run,h.s,h.s['tasks'][0]);before=len(h.seen)
  self.assertEqual(c.saved_response(h.run,call,body)['status'],'completed_response');self.assertEqual(before,len(h.seen))
  with self.assertRaises(c.runtime.Fatal):c.saved_response(h.run,dict(call,parent='wrong-task'),body)
 def test_saved_transport_failure_cannot_become_a_paid_content_fallback_on_resume(self):
  h=self.h;h.coordinate();call=copy.deepcopy(h.s['calls'][0]);folder=h.run/'calls'/call['id'];result=read_json(folder/'outcome.json');result.update(status='failed',failure_kind='transport');atomic_json(folder/'outcome.json',result)
  from probe.experiment import seal
  atomic_json(folder/'manifest.json',[r for r in files_manifest(folder) if r['path']!='manifest.json']);call['seal']=sha(folder/'manifest.json')
  with self.assertRaises(c.runtime.Fatal):c.saved_response(h.run,call,c.body_for(h.run,h.s,h.s['tasks'][0]))

 def test_finalization_keeps_raw_transport_seals_immutable(self):
  h=self.h;h.coordinate()
  from probe.experiment import verify_seal
  for call in h.s['calls']:verify_seal(h.run/'calls'/call['id'],call['seal'])
  self.assertTrue((h.run/'call-results/call-002/findings.json').exists());self.assertFalse((h.run/'calls/call-002/findings.json').exists());c.verify(h.run)
 def test_mathpix_document_error_with_unknown_page_count_continues_as_recorded_failure(self):
  h=self.h;pdf=h.run/'subset.pdf';pdf.write_bytes(b'%PDF-fixture');u={'id':'subset','source_id':h.sid,'source_sha256':'a'*64,'physical_pages':[1],'subset':str(pdf),'subset_sha256':sha(pdf)};r={'kind':'mathpix','phase':'extraction','unit':u,'scope_sha256':fingerprint(u)};fallback.register_scope(h.run,r,self.approval,unit_verified=True)
  class Client:
   key_id='fake';calls=0
   def redact(self,v):return v
   def get_json(self,p):return {'ocr_usage':[]} if p.startswith('ocr-usage') else {'status':'error','num_pages':0,'error':'document failure'}
   def submit(self,pdf,name):self.calls+=1;return 'job',{'pdf_id':'job'}
  ledger=h.root/'mx';ledger.mkdir();client=Client()
  with patch.object(mx,'LEDGER',ledger):out=fallback.run_mathpix(h.run,r,self.approval,client=client)
  self.assertEqual(client.calls,1);self.assertEqual(out['status'],'provider_error')

 def test_compatible_historical_mathpix_job_uses_no_new_charge_or_submission(self):
  h=self.h;previous=h.root/'previous';previous.mkdir();pdf=h.run/'subset.pdf';pdf.write_bytes(b'%PDF-fixture');(previous/'subset.pdf').write_bytes(pdf.read_bytes())
  unit={'id':'subset','source_id':h.sid,'source_sha256':'a'*64,'physical_pages':[1],'subset':str(pdf),'subset_sha256':sha(pdf)};record={'kind':'mathpix','phase':'extraction','unit':unit,'scope_sha256':fingerprint(unit)};fallback.register_scope(h.run,record,self.approval,unit_verified=True)
  class Client:
   key_id='same-key';calls=0
   def redact(self,v):return v
   def get_json(self,p):return {'ocr_usage':[]} if p.startswith('ocr-usage') else {'status':'error','num_pages':0}
   def submit(self,pdf,name):self.calls+=1;return 'historical-job',{'pdf_id':'historical-job'}
  ledger=h.root/'mx';ledger.mkdir();client=Client();job={'source_id':h.sid,'sha256':'a'*64,'physical_pages':[1],'subset':'subset.pdf','subset_sha256':sha(pdf)}
  with patch.object(mx,'LEDGER',ledger):
   mx.submit_once(previous,{'budget_id':'old-authorisation'},job,client);self.assertEqual(client.calls,1)
   out=fallback.run_mathpix(h.run,record,self.approval,client=client);self.assertTrue(out['reused_historical_job']);self.assertEqual(client.calls,1)
   summary=fallback.budget_summary(h.run,self.approval);self.assertEqual(summary['exposure_usd'],'0');self.assertEqual(summary['reservations'],0)

class Reconciliation(unittest.TestCase):
 def test_saved_structural_repairs_retain_equations_and_numbering(self):
  tex=r'\begin{document}\begin{equation*}\begin{aligned}x^2=1'+ '\n\\end{aligned}\n\\tag{C.10}\n\\end{aligned}\n'+r'\end{equation*}\end{document}'
  result,notes=prep.saved_repairs('original-f24e3131438ab5c0',tex);self.assertEqual(result.count(r'\end{aligned}'),1);self.assertIn(r'\tag{C.10}',result);self.assertIn('x^2=1',result)
 def test_mean_caption_removes_only_stray_math_delimiter(self):
  text=r'\begin{document}weekly frequency $(ie $h=1/52)$\end{document}';result,notes=prep.saved_repairs('original-ead9d04e4c78147d',text);self.assertIn('(ie $h=1/52)$',result)
 def test_live_saved_scope_partition_is_complete_without_reconversion(self):
  p=read_json(prep.DEV/'promotions'/'original-ba2b65da21f13b69'/'reconciliation.json');self.assertEqual(p['scope_checks'][0]['blocks'],706);self.assertEqual(p['scope_checks'][0]['units'],6)
 def test_nineteen_triage_rows_reconcile_promotions_queue_and_exclusions(self):
  actions=read_json(prep.DEV/'actions.json');self.assertEqual(len(actions),19);self.assertEqual(sum(a['action']=='reuse_saved_complete' for a in actions),13);self.assertEqual(sum(a['action']=='missing_conversion' for a in actions),4);self.assertEqual(sum(a['action']=='excluded_non_paper' for a in actions),2)

class Settlement(unittest.TestCase):
 def test_confirmed_cost_releases_only_verified_difference_and_tampering_is_detected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);a={'explicitly_approved':True,'new_spend_cap_usd':'7.00','approved_scopes':['one','two'],'provider_metadata_current':True};r={'kind':'kimi','phase':'critic','scope_sha256':'one'}
   identity,_=fallback.reserve_budget(root,r,'6.00',a);e=root/'provider-settlement.json';atomic_json(e,{'actual_cost_usd':'1.00','source':'mock provider confirmed response'})
   fallback.settle_confirmed(root,identity,a,'1.00',e);fallback.reserve_budget(root,dict(r,kind='mathpix',scope_sha256='two'),'6.00',a)
   self.assertEqual(fallback.budget_summary(root,a)['exposure_usd'],'7.00');e.write_text('changed')
   with self.assertRaises(ValueError):fallback.reserve_budget(root,dict(r,scope_sha256='three'),'.01',dict(a,approved_scopes=['one','two','three']))
 def test_external_mathpix_tracking_adds_no_separate_one_dollar_cap(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);a={'explicitly_approved':True,'new_spend_cap_usd':'7.00','approved_scopes':['pages'],'provider_metadata_current':True};r={'kind':'mathpix','phase':'extraction','scope_sha256':'pages','unit':{'source_id':'s','source_sha256':'a'*64,'physical_pages':list(range(1,301)),'subset_sha256':'b'*64}}
   identity,_=fallback.reserve_budget(root,r,'1.50',a);external={'ledger':str(root/'fallback-budget/ledger.json'),'approval_sha256':fingerprint(a),'reservation':identity}
   job={'source_id':'s','sha256':'a'*64,'physical_pages':list(range(1,301)),'subset_sha256':'b'*64};ledger={}
   result,fresh=mathpix_experiment.reserve(ledger,'mock','shared',job,root,external_budget=external)
   self.assertTrue(fresh);self.assertEqual(result['reserved_microusd'],1500000);self.assertNotIn('cap_microusd',ledger['budgets']['shared'])
   with self.assertRaises(ValueError):mathpix_experiment.reserve(ledger,'mock','shared',dict(job,sha256='c'*64),root,external_budget=external)

class TransportDeadline(unittest.TestCase):
 def test_explicit_overnight_cloud_post_has_no_absolute_generation_timer(self):
  from probe import cloud_critic
  obj=object.__new__(cloud_critic.CloudClient);obj.config={'no_generation_deadline':True};obj.timeout=900;obj._key='mock-secret'
  class Socket:
   def __init__(self):self.times=[]
   def settimeout(self,v):self.times.append(v)
  class Reply:
   status=200
   def __init__(self):self.once=False
   def read1(self,n):
    if self.once:return b''
    self.once=True;return b'{}'
   def getheader(self,k):return None
  class Conn:
   def __init__(self):self.sock=Socket()
   def connect(self):pass
   def request(self,*args,**kwargs):pass
   def getresponse(self):return Reply()
   def close(self):pass
  conn=Conn()
  with patch.object(obj,'_connection',return_value=conn),patch.object(cloud_critic.threading,'Timer',side_effect=AssertionError('No generation deadline')):status,body,elapsed=obj._http('POST','/chat/completions',{})
  self.assertEqual(status,200);self.assertTrue(all(x is None for x in conn.sock.times))

class BudgetCorruption(unittest.TestCase):
 def test_missing_ledger_cannot_create_fresh_allowance(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);a={'explicitly_approved':True,'new_spend_cap_usd':'7.00','approved_scopes':['one','two'],'provider_metadata_current':True};r={'kind':'kimi','phase':'critic','scope_sha256':'one'}
   fallback.reserve_budget(root,r,'1.00',a);(root/'fallback-budget/ledger.json').unlink()
   with self.assertRaises(kimi_escalation.IntegrityError):fallback.reserve_budget(root,dict(r,scope_sha256='two'),'1.00',a)
 def test_removed_reservation_is_detected_on_restart(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);a={'explicitly_approved':True,'new_spend_cap_usd':'7.00','approved_scopes':['one','two'],'provider_metadata_current':True};r={'kind':'kimi','phase':'critic','scope_sha256':'one'}
   fallback.reserve_budget(root,r,'1.00',a);path=root/'fallback-budget/ledger.json';d=read_json(path);d['reservations']={};atomic_json(path,d)
   with self.assertRaises(kimi_escalation.IntegrityError):fallback.reserve_budget(root,dict(r,scope_sha256='two'),'1.00',a)

class PaidPause(unittest.TestCase):
 def test_pause_prevents_fresh_admission_without_creating_a_reservation(self):
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);atomic_json(run/'pause.json',{'operator':True})
   with self.assertRaises(c.runtime.StopRun):fallback.run_kimi(run,{},run,{},client_factory=lambda *x:self.fail('No credential/client creation'))
   with self.assertRaises(c.runtime.StopRun):fallback.run_mathpix(run,{}, {},client=None)
   self.assertFalse((run/'fallback-budget/ledger.json').exists())
 def test_pause_guard_leaves_owned_unknown_charge_untouched(self):
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);a={'explicitly_approved':True,'new_spend_cap_usd':'7.00','approved_scopes':['one'],'provider_metadata_current':True};r={'kind':'kimi','phase':'critic','scope_sha256':'one'}
   fallback.reserve_budget(run,r,'1.00',a);before=sha(run/'fallback-budget/ledger.json');atomic_json(run/'pause.json',{'operator':True})
   with self.assertRaises(c.runtime.StopRun):fallback.pause_guard(run)
   self.assertEqual(before,sha(run/'fallback-budget/ledger.json'))

class PriceAndReviewScope(unittest.TestCase):
 def test_pdf_price_is_not_inferred_from_other_route_or_volume_tier(self):
  self.assertEqual(str(paid.mathpix_pdf_rate(b'<div>POST v3/text $0.005/image POST v3/pdf Documents $0.005 / page 1M+ $0.0035 POST files/v1 $0.0015/page</div>')),'0.005')
  self.assertEqual(str(paid.mathpix_pdf_rate(b'<div>POST v3/text $0.005/page POST v3/pdf Documents $0.006/page 1M+ $0.005/page POST files/v1</div>')),'0.006')
  with self.assertRaises(fallback.NotApproved):paid.mathpix_pdf_rate(b'<script>POST v3/pdf $0.005/page</script>Missing live card')
 def test_reused_scope_cannot_gain_a_new_full_paper_review_attestation(self):
  h=fixtures.Pipeline();h.setUp();self.addCleanup(h.doCleanups);h.s['documents'][h.sid]['reused_units']=[h.key];h.coordinate();record=read_json(h.run/'deliveries'/h.sid/'library-status.json');self.assertFalse(record['model_review']['reviewed_full_scope_attested']);self.assertTrue(record['model_review']['new_units_reviewed_full_scope_attested']);self.assertIn(h.key,record['model_review']['reused_review_coverage'])
