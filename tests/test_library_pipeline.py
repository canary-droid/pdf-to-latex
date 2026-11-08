"""Real library workflow boundaries with mocked inference/compiler/host observations."""
import copy,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from probe.common import atomic_json,read_json,sha,fingerprint,files_manifest
from probe import chapter_concurrency as scheduler,library_fallbacks as fallback,source_library
from scripts import library_pipeline as c,image_review_recovery

DOC=r'\documentclass{article}\usepackage{amsmath}\begin{document}\section*{Assigned mathematics}For x positive, the complete assigned expression is $x^2=1$. This retained sentence supplies the definition and condition.\end{document}'

class Pipeline(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.run=self.root/'run';self.run.mkdir();self.library=self.root/'sources';self.library.mkdir()
  self.sid='original-testsource';self.key=self.sid+'-unit-001';self.seen=[];self.pause=False;self.fail_convert=False
  parent=Path(read_json(image_review_recovery.POINTER)['run']);old=read_json(parent/'state.json')
  self.s={k:copy.deepcopy(old[k]) for k in ['chapter_contract','execution_limits','timing_policy','concurrency_policy','compiler_environment']}
  self.s.update(status='prepared',tasks=[],calls=[],source_units={},versions={},current_versions={},derived_inputs={},documents={self.sid:{'filename':'Fixture.pdf','units':[],'historical_selection':None,'source_sha256':'a'*64,'status':'planned'}},inputs_prepared=False,production_stage={'task_ids':[]},connection_failures=0,first_dispatch=None,suite_protocol='source-image-review-v1',active_stage=1,stages={'1':{}},launches=[])
  self.s.update(runtime_image='qualified-test-image',remote_models='/test/models',remote='/test/run')
  folder=self.run/'sources'/self.sid;folder.mkdir(parents=True);shutil.copyfile(c.ROOT/'fixtures/vision/case-01.png',folder/'page-001.png')
  import struct
  dimensions=list(struct.unpack('>II',(folder/'page-001.png').read_bytes()[16:24]))
  atomic_json(folder/'secondary-assessment.json',{'policy':'fixture','pages':[]})
  self.doc={'source_id':self.sid,'filename':'Fixture.pdf','sha256':'a'*64,'original':str(c.ROOT/'fixtures/known-math.pdf'),'physical_pages':[1],
   'pages':[{'physical_pdf_page':1,'path':str((folder/'page-001.png').relative_to(self.run)),'sha256':sha(folder/'page-001.png'),'dimensions':dimensions}],
   'library_document':{'source_id':self.sid,'folder':'fixture','sha256':'a'*64}}
  plan={'settings':dict(c.policy.DEFAULTS),'documents':[self.doc],'workloads':{'mineru_pro':[[self.sid,1]]},'paid_enabled':False,'spend_cap_usd':'0','runtime_contract':{k:self.s[k] for k in c.RUNTIME_FIELDS}};atomic_json(self.run/'plan.json',plan)
  native=[{'type':'title','content':r'\section*{Assigned mathematics}','bbox':[0,0,100,20]},{'type':'text','content':'For x positive, the complete assigned expression is $x^2=1$. This retained sentence supplies the definition and condition.','bbox':[0,20,100,100]}]
  atomic_json(self.run/'arms/mineru_pro/pages'/f'{self.sid}-p1/native.json',native);self.s['extraction']={'mineru_pro':{'pages':{f'{self.sid}-p1':{'status':'completed'}}}}
  atomic_json(self.run/'binding.json',{'code':c.base.code_binding(),'plan_sha256':sha(self.run/'plan.json'),'files':{}})
  c.plan_units(self.run,self.s);self.addCleanup(patch.stopall);patch.object(c.reconcile,'LIBRARY',self.library).start()
 def compile(self,run,s,root,document,folder,assets):
  p=folder/'attempt-1';p.mkdir(parents=True);shutil.copyfile(c.ROOT/'fixtures/known-math.pdf',p/'document.pdf');(p/'console.log').write_text('');record={'status':'passed','attempts':[{'path':str(p.relative_to(run))}]};atomic_json(folder/'compilation.json',record);return record
 def cpu(self,args,**kw):
  self.assertEqual(args[:3],['docker','exec','-i']);bodies=json.loads(kw['input']);result={'limits':c.policy.DEFAULTS['image_limits'],'requests':{k:{'prompt_tokens':777,'image_rows':c.vision.image_budget(b)['image_tokens']} for k,b in bodies.items()}}
  return type('Result',(),{'stdout':json.dumps(result)})()
 def sample(self,owned):return {'health':{'context_length':1048576,'pool_tokens':1488896,'streams':{'decoding':owned,'prefilling':0,'paused':0,'max':4},'requests_running':owned,'busy':bool(owned)},'memory_available_bytes':{'head':8*1024**3,'peer':12*1024**3},'evidence':{}}
 def transport(self,run,call,body,**kw):
  self.assertIn(call['id'],[x['id'] for x in read_json(run/'state.json')['calls']]);self.seen.append(call['parent']);critic=call['parent'].endswith('/critic')
  if critic:
   payload=c.vision.request_payload(body);saved=(run/self.s['versions'][self.key]['convert']['path']).read_text();self.assertEqual(saved,DOC+'\n');self.assertEqual(payload['draft'],saved);self.assertEqual(payload['base_sha256'],sha(run/self.s['versions'][self.key]['convert']['path']));self.assertEqual(body['reasoning_effort'],'high')
   answer=json.dumps({'base_sha256':payload['base_sha256'],'scope_review':{'full_assigned_scope_reviewed':True,'additional_findings_remain':False,'unreviewed_scope':''},'findings':[]})
  else:answer='```tex\n'+DOC+'\n```'
  call.update(status='failed' if self.fail_convert and not critic else 'completed_response',elapsed_seconds=.01,metadata={'actual_model':'glm53-regular','finish_reason':'stop','usage':{'prompt_tokens':777,'completion_tokens':10}})
  folder=run/'calls'/call['id'];folder.mkdir(parents=True);atomic_json(folder/'request.json',body);atomic_json(folder/'attempts/one/request.json',{'body':body});atomic_json(folder/'outcome.json',call);(folder/'content.txt').write_text(answer);(folder/'answer.txt').write_text(answer);atomic_json(folder/'manifest.json',files_manifest(folder));call['seal']=sha(folder/'manifest.json')
  if self.pause:atomic_json(run/'pause.json',{'operator':True})
  return (None if call['status']=='failed' else answer),call
 def coordinate(self):
  with patch.object(c.compiler_environment,'compile_saved',side_effect=self.compile),patch.object(c.subprocess,'run',side_effect=self.cpu):
   scheduler.coordinate(self.run,self.s,self.s['tasks'],body_for=c.body_for,finish=c.finish,verify=lambda:c.verify(self.run),changed=lambda:c.save(self.run,self.s),sample=self.sample,fixed_level=2,before_reserve=lambda s,t,b:c.before(self.run,s,t,b),transport=self.transport,poll_seconds=.001)
 def test_extraction_to_conversion_exact_draft_image_review_publication_and_zero_replay(self):
  atomic_json(self.library/'library-first-status.json',{'sources':[{'source_id':self.sid,'filename':'Fixture.pdf','pages':1,'folder':'fixture','status':'partial','selected_generation':None}],'counts':{'ready':0,'partial':1,'deferred':0}})
  self.coordinate();self.assertEqual(len(self.seen),2);self.assertEqual(self.s['tasks'][1]['status'],'review_completed');self.assertTrue(self.s['tasks'][1]['review_complete_attested'])
  self.coordinate();self.assertEqual(len(self.seen),2);self.assertTrue((self.run/'deliveries'/self.sid/'manifest.json').exists());self.assertTrue((self.library/'fixture/generations'/self.run.name/'library-status.json').exists())
  index=read_json(self.library/'library-first-status.json');self.assertIn('latest_attempt',index['sources'][0]);self.assertTrue((self.library/index['latest_readable_index']).exists())
  digest=sha(self.run/'deliveries'/self.sid/'manifest.json');self.s['documents'][self.sid]['published']=False
  c.publish_settled(self.run,self.s,self.sid);self.assertEqual(sha(self.run/'deliveries'/self.sid/'manifest.json'),digest)
 def test_pause_drains_and_resume_never_reconverts(self):
  self.pause=True
  with self.assertRaises(c.runtime.StopRun):self.coordinate()
  self.assertEqual(len(self.seen),1);self.pause=False;(self.run/'pause.json').unlink();self.coordinate();self.assertEqual(len(self.seen),2)
 def test_failed_conversion_skips_critic_and_creates_disabled_scoped_fallback(self):
  self.fail_convert=True;self.coordinate();self.assertEqual(len(self.seen),1);self.assertEqual(self.s['tasks'][1]['status'],'unavailable')
  p=read_json(self.run/'fallbacks'/(self.key+'-convert')/'proposal.json');self.assertEqual(p['kind'],'kimi');self.assertEqual(p['new_budget_usd'],'0');self.assertIn('primary',p['unit']);self.assertIn('cloud_images',p['unit'])
 def test_changed_scope_or_draft_stops_dispatch(self):
  self.s['source_units'][self.key]['text']='changed';c.save(self.run,self.s)
  with self.assertRaises(c.runtime.Fatal):c.verify(self.run)
 def test_changed_compiler_or_remote_runtime_refused(self):
  self.s['runtime_image']='changed-image';c.save(self.run,self.s)
  with self.assertRaises(c.runtime.Fatal):c.verify(self.run)
 def test_newly_published_source_blocks_stale_preparation_before_dispatch(self):
  atomic_json(self.library/'fixture/current.json',{'generation':'generations/other-run','status':'ready_working_source'});c.save(self.run,self.s)
  with self.assertRaises(c.runtime.Fatal):c.verify(self.run)
 def test_real_candidate_image_schema_is_checked_before_host_operations(self):
  plan=read_json(self.run/'plan.json');page=plan['documents'][0]['pages'][0]
  with self.assertRaises(ValueError):c.policy.validate_extraction_plan(plan,self.run)
  page['image']=page['path'];c.policy.validate_extraction_plan(plan,self.run)
  page['image']='wrong.png'
  with self.assertRaises(ValueError):c.policy.validate_extraction_plan(plan,self.run)
 def test_finished_launcher_does_not_touch_host_or_model(self):
  self.s['status']=c.TERMINAL;c.save(self.run,self.s)
  with patch.object(c.sys,'argv',['library','resume','--run',str(self.run)]),patch.object(c.subprocess,'run',side_effect=AssertionError('Unexpected host operation')):c.main()

class Fallbacks(unittest.TestCase):
 def test_kimi_existing_body_adapter_exact_draft_and_one_attempt(self):
  current=read_json(c.ROOT/'results/kimi-current.json');config=read_json(Path(current['run'])/'binding.json')['config']
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);cloud=root/'cloud';cloud.mkdir();atomic_json(cloud/'binding.json',{'config':config});draft=root/'draft.tex';draft.write_text(DOC);png=c.ROOT/'fixtures/vision/case-01.png'
   unit={'id':'unit','source_id':'source','source_sha256':'a'*64,'physical_pages':[1],'primary':'Source x^2=2 with positive x.','draft_path':str(draft),'draft_sha256':sha(draft),'draft_ranges':[[0,len(DOC)]],
    'cloud_images':[{'source_id':'source','source_sha256':'a'*64,'page':1,'path':str(png),'sha256':sha(png),'bbox':None}]}
   record=read_json(fallback.proposal(root,unit,'critic','failed'));approval={'explicitly_approved':True,'new_spend_cap_usd':'5','approved_scopes':[record['scope_sha256']],'provider_metadata_current':True}
   class Client:
    calls=0
    def __init__(self,path):pass
    def dispatch(self,task,body,folder):
     Client.calls+=1
     assert body['model']=='moonshotai/kimi-k3' and body['provider']['allow_fallbacks'] is False
     assert any(p['type']=='image_url' for p in body['messages'][0]['content'])
     return json.dumps({'base_sha256':c.requests.digest(DOC),'findings':[{'status':'edit','old':'x^2=1','new':'x^2=2','source':'page1','reason':'Synthetic source correction'}]}),{'status':'complete_response'}
   a=fallback.run_kimi(root,record,cloud,approval,client_factory=Client);b=fallback.run_kimi(root,record,cloud,approval,client_factory=Client)
   self.assertEqual(Client.calls,1);self.assertEqual(a,b);self.assertEqual(draft.read_text(),DOC);self.assertIn('x^2=2',Path(a['candidate_tex']).read_text())
 def test_mathpix_budget_one_submission_and_unknown_never_reposted(self):
  from scripts import mathpix_comparison as adapter
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);subset=root/'subset.pdf';subset.write_bytes(b'%PDF-fixture');unit={'id':'unit','source_id':'source','source_sha256':'a'*64,'physical_pages':[2],'subset':str(subset),'subset_sha256':sha(subset)}
   record=read_json(fallback.proposal(root,unit,'extraction','failed'));approval={'explicitly_approved':True,'new_spend_cap_usd':'0.01','approved_scopes':[record['scope_sha256']],'provider_metadata_current':True,'mathpix_price_per_page_usd':'0.005'}
   class Client:
    key_id='fake-key-identity';calls=0
    def get_json(self,path):return {'ocr_usage':[]}
    def redact(self,text):return text
    def submit(self,pdf,name):self.calls+=1;raise OSError('disconnect')
   client=Client()
   with patch.object(adapter,'LEDGER',root/'global-ledger'):
    (root/'global-ledger').mkdir();a=fallback.run_mathpix(root,record,approval,client=client);b=fallback.run_mathpix(root,record,approval,client=client)
   self.assertEqual(client.calls,1);self.assertEqual(a['status'],'uncertain_submission');self.assertEqual(b,a)
 def test_no_approved_budget_means_no_provider_or_credentials(self):
  with tempfile.TemporaryDirectory() as tmp:
   record={'scope_sha256':'scope','phase':'critic','kind':'kimi'}
   with self.assertRaises(fallback.NotApproved):fallback.reserve_budget(tmp,record,'0.01',{})
   self.assertFalse((Path(tmp)/'fallback-budget/ledger.json').exists())
 def test_shared_run_cap_cannot_reset_or_admit_another_scope(self):
  with tempfile.TemporaryDirectory() as tmp:
   approval={'explicitly_approved':True,'new_spend_cap_usd':'0.10','approved_scopes':['one','two'],'provider_metadata_current':True};a={'scope_sha256':'one','phase':'critic','kind':'kimi'};b=dict(a,scope_sha256='two',kind='mathpix')
   fallback.reserve_budget(tmp,a,'0.08',approval)
   with self.assertRaises(fallback.NotApproved):fallback.reserve_budget(tmp,b,'0.03',approval)
   self.assertFalse(fallback.reserve_budget(tmp,a,'0.08',approval)[1])
 def test_mathpix_direct_tex_uses_existing_compiler_not_glm_and_scope_is_exact(self):
  import io,zipfile
  from scripts import mathpix_comparison as adapter
  data=io.BytesIO()
  with zipfile.ZipFile(data,'w') as z:z.writestr('paper.tex',DOC)
  with tempfile.TemporaryDirectory() as tmp,patch.object(adapter,'compile_direct',return_value={'status':'passed'}) as build:
   result=fallback.direct_mathpix_tex(tmp,Path(tmp)/'build',data.getvalue(),'qualified-image',assigned_pages=[2],returned_pages=[2],compile_pdf=True);self.assertEqual(result['status'],'passed');build.assert_called_once()
   with self.assertRaises(ValueError):fallback.direct_mathpix_tex(tmp,Path(tmp)/'bad',data.getvalue(),'qualified-image',assigned_pages=[2],returned_pages=[3])
 def test_unselected_partial_publication_preserves_current(self):
  from probe.experiment import seal
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);out=root/'source';out.mkdir();atomic_json(out/'current.json',{'generation':'good'});prepared=root/'prepared';prepared.mkdir();(prepared/'README.md').write_text('partial');seal(prepared)
   source_library.publish_generation(out,'partial',prepared,'partial_source',select=False);self.assertEqual(read_json(out/'current.json'),{'generation':'good'})

if __name__=='__main__':unittest.main()
