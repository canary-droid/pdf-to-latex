"""Saved-input recovery contracts; real scheduler/edit boundary, mocked transport."""
import copy,json,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
from probe.common import read_json,atomic_json,files_manifest,sha,fingerprint
from probe import image_review as vision,focused_recovery as edits,chapter_editorial as editorial,chapter_concurrency as scheduler
from scripts import image_review_recovery as c

def prepared():
 if not c.POINTER.exists():raise unittest.SkipTest('Local saved recovery preparation unavailable')
 return Path(read_json(c.POINTER)['run'])

def finding(old,new,kind='tex'):
 return {'status':'edit','old':old,'new':new,'replacement_format':kind,'source':'p1 equation1','reason':'located correction',
  'printed_source':'original image','draft_reading':'draft reading','proposed_change':'precise replacement','justification':'source evidence'}

class AnnotationTests(unittest.TestCase):
 def test_observed_annotation_and_adjacent_specials_are_plain_only(self):
  note=editorial.annotation({'id':'unit-1234567890','text':'Original explanation.','status':'open'})
  draft=r'\begin{document}\[x^2=a_1\]'+note+r'\end{document}'
  text='(1-it)^c and a_b, $x$, 50% & # {braces} \\ end'
  result,log=vision.apply_review(draft,{'base_sha256':edits.digest(draft),'findings':[finding('Original explanation.',text,'plain_annotation')]})
  self.assertIn(editorial.tex_escape(text),result);self.assertIn(r'\[x^2=a_1\]',result)
  self.assertEqual(log['findings'][0]['disposition'],'applied_model_claim')
 def test_mathematical_tex_remains_exact(self):
  draft=r'\begin{document}\[x^2=a_1\]\end{document}'
  result,_=vision.apply_review(draft,{'base_sha256':edits.digest(draft),'findings':[finding('x^2=a_1',r'x^2=\frac{a_1}{2}')]})
  self.assertIn(r'\frac{a_1}{2}',result);self.assertNotIn('textbackslash',result)
 def test_annotation_missing_type_or_evidence_is_withheld(self):
  draft=editorial.annotation({'id':'unit-1234567890','text':'old explanation','status':'open'})
  for f in [finding('old explanation','unsafe ^ math'),dict(finding('old explanation','new text','plain_annotation'),printed_source='')]:
   result,log=vision.apply_review(draft,{'base_sha256':edits.digest(draft),'findings':[f]});self.assertEqual(result,draft);self.assertEqual(log['findings'][0]['disposition'],'unapplied_suggestion')
 def test_compile_failure_preserves_previous_selection(self):
  result=vision.compiling_selection('baseline','candidate',{'status':'syntax_failure'});self.assertEqual(result['selected'],'baseline')
  self.assertEqual(vision.compiling_selection('baseline','candidate',{'status':'passed'})['selected'],'candidate')
 def test_real_saved_annotation_build_and_unchanged_equations(self):
  r=prepared();self.assertEqual(read_json(r/'annotation-repair/build/compilation.json')['status'],'passed')
  d=(r/'annotation-repair/original.tex').read_text();fixed=(r/'annotation-repair/repaired.tex').read_text();marker=d.index(r'\section*{Editorial corrections and unresolved issues}')
  self.assertEqual(d[:marker],fixed[:marker]);self.assertIn(r'(1-it)\textasciicircum{}c',fixed)

class SavedContracts(unittest.TestCase):
 def test_complete_ownership_and_exact_matched_requests(self):
  r=prepared();p=read_json(r/('plan.json' if (r/'plan.json').exists() else 'plan-draft.json'));c.validate_plan(p)
  self.assertEqual([len([u for u in p['units'] if u['source']==s]) for s in ['cf','spectral']],[3,5])
  for unit in ['cf-1','spectral-2','control-cf']:
   high=read_json(r/'requests'/(unit+'-high.json'));maximum=read_json(r/'requests'/(unit+'-max.json'));high['reasoning_effort']='max';self.assertEqual(high,maximum)
  self.assertIn('original-21debf82bc2c0a3d-p010-r033',p['units'][2]['blocks'])
  for t in p['tasks']:self.assertLessEqual(t['budget']['image_count'],8)
 def test_scope_and_allowance_tampering_rejected(self):
  r=prepared();p=read_json(r/('plan.json' if (r/'plan.json').exists() else 'plan-draft.json'))
  for edit in ['blocks','allowance','stage']:
   x=copy.deepcopy(p)
   if edit=='blocks':x['units'][0]['blocks'].pop()
   elif edit=='allowance':x['maximum_model_requests']=14
   else:x['stages'][0].append(x['stages'][0][0])
   with self.assertRaises(ValueError):c.validate_plan(x)
 def test_error_control_separate_and_no_answer_key_in_requests(self):
  r=prepared();key=read_json(r/'evaluation/answer-key.json')['controlled_example'];control=(r/'inputs/control-cf/draft.tex').read_text();original=(r/'inputs/cf-1/draft.tex').read_text()
  self.assertIn(key['mutated_anchor'],control);self.assertNotIn(key['mutated_anchor'],original);self.assertIn(key['printed_anchor'],original)
  for name in ['control-cf-high','control-cf-max']:
   b=read_json(r/'requests'/(name+'.json'));text=b['messages'][0]['content'][0]['text'];self.assertNotIn('One sign only',text);self.assertNotIn('controlled_example',text);self.assertNotIn('mutation',text.lower())
 def test_unambiguous_scope_guard_and_stale_hash(self):
  draft=r'\begin{document}x=1. y=2.\end{document}';a=draft.index('x=1');b=draft.index('y=2')
  p={'base_sha256':edits.digest(draft),'findings':[finding('y=2','y=3')]}
  result,log=vision.apply_review(draft,p,[[a,b]]);self.assertEqual(result,draft);self.assertEqual(log['findings'][0]['disposition'],'rejected')
  p['base_sha256']='stale'
  with self.assertRaises(ValueError):vision.apply_review(draft,p)

class Lifecycle(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.fixture=Path(cls.tmp.name)/'fixture';src=prepared();shutil.copytree(src,cls.fixture,ignore=shutil.ignore_patterns('calls','samples','reviews','deliveries','*.zip','state.json','binding.json','progress.json','plan.json','terminal.log'))
  c.freeze(cls.fixture)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.run=Path(self.tmp.name)/'run';shutil.copytree(self.fixture,self.run)
  # Bind the test's own immutable copies, preserving exact real saved inputs.
  b=read_json(self.run/'binding.json');b['files']={str(self.run/Path(k).relative_to(self.fixture)) if Path(k).is_relative_to(self.fixture) else k:v for k,v in b['files'].items()};atomic_json(self.run/'binding.json',b)
  self.s=read_json(self.run/'state.json');self.s['stage_index']=0;self.s['active_stage']=1;self.seen=[];self.pause=False
 def sample(self,owned):
  return {'health':{'context_length':1048576,'pool_tokens':1488896,'streams':{'decoding':owned,'prefilling':0,'paused':0,'max':4},'requests_running':owned,'busy':bool(owned)},'memory_available_bytes':{'head':8*1024**3,'peer':12*1024**3},'evidence':{}}
 def transport(self,run,call,body,**kwargs):
  self.assertIn(call['id'],[x['id'] for x in read_json(run/'state.json')['calls']]);self.seen.append(call['parent'])
  p=next(t for t in read_json(run/'plan.json')['tasks'] if t['id']==call['parent']);payload=json.loads(body['messages'][0]['content'][0]['text'].split('\n',1)[1]);answer=json.dumps({'base_sha256':payload['base_sha256'],'findings':[]})
  call.update(status='completed_response',elapsed_seconds=.01,metadata={'actual_model':'glm53-regular','finish_reason':'stop','usage':{'completion_tokens':10,'completion_tokens_details':{'reasoning_tokens':2},'prompt_tokens':p['cpu_expectation']['prompt_tokens']}})
  folder=run/'calls'/call['id'];folder.mkdir(parents=True);atomic_json(folder/'request.json',body);atomic_json(folder/'attempts/one/request.json',{'body':body});atomic_json(folder/'outcome.json',call);(folder/'content.txt').write_text(answer);atomic_json(folder/'manifest.json',files_manifest(folder));call['seal']=sha(folder/'manifest.json')
  if self.pause:atomic_json(run/'pause.json',{'operator':True})
  return answer,call
 def compile(self,run,state,root,document,folder,assets):
  atomic_json(folder/'compilation.json',{'status':'passed','attempts':[]});return {'status':'passed'}
 def coordinate(self):
  tasks=[t for t in self.s['tasks'] if t['id'] in ['cf-1-high','cf-1-max']]
  c.save(self.run,self.s)
  with patch.object(c.compiler,'compile_saved',side_effect=self.compile):
   scheduler.coordinate(self.run,self.s,tasks,body_for=c.body_for,finish=c.finish,verify=lambda:c.verify(self.run),changed=lambda:c.save(self.run,self.s),sample=self.sample,
    fixed_level=1,before_reserve=lambda s,t,b:c.before(self.run,s,t,b),transport=self.transport,poll_seconds=.001)
 def test_actual_reservation_settlement_and_finished_queue_zero_replay(self):
  self.coordinate();self.assertEqual(self.seen,['cf-1-high','cf-1-max']);self.coordinate();self.assertEqual(len(self.seen),2)
  self.assertTrue(all(t['images_verified'] for t in self.s['tasks'][:2]));self.assertTrue(all(t['review_response']=='usable_focused_findings' for t in self.s['tasks'][:2]))
 def test_pause_drains_and_resume_preserves_consumption(self):
  self.pause=True
  with self.assertRaises(c.runtime.StopRun):self.coordinate()
  self.assertEqual(len(self.seen),1);self.pause=False;(self.run/'pause.json').unlink();self.coordinate();self.assertEqual(len(self.seen),2)
 def test_uncertain_dispatch_cannot_replay(self):
  t=self.s['tasks'][0];body=c.body_for(self.run,self.s,t);c.runtime.reserve(self.s,t['id'],fingerprint(body));c.save(self.run,self.s)
  with self.assertRaises(c.runtime.Fatal):c.before(self.run,self.s,t,body)
  self.coordinate();self.assertNotIn(t['id'],self.seen)
 def test_sealed_restart_settlement_no_transport_replay(self):
  t=self.s['tasks'][0];body=c.body_for(self.run,self.s,t);call=c.runtime.reserve(self.s,t['id'],fingerprint(body));c.save(self.run,self.s)
  answer,settled=self.transport(self.run,copy.deepcopy(call),body);call.update(settled)
  with patch.object(c.compiler,'compile_saved',side_effect=self.compile):c.finish(self.run,self.s,t,answer,call);c.finish(self.run,self.s,t,answer,call)
  self.coordinate();self.assertEqual(self.seen,['cf-1-high','cf-1-max'])
 def test_wrong_images_and_stale_draft_are_rejected(self):
  t=self.s['tasks'][0];p=self.run/'requests/cf-1-high.json';b=read_json(p);b['messages'][0]['content'][-1]['image_url']['url']='wrong';atomic_json(p,b)
  with self.assertRaises(c.runtime.Fatal):c.body_for(self.run,self.s,t)
  shutil.copyfile(self.fixture/'requests/cf-1-high.json',p);(self.run/'inputs/cf-1/draft.tex').write_text('wrong draft')
  with self.assertRaises(c.runtime.Fatal):c.body_for(self.run,self.s,t)
 def test_real_sampler_effort_and_stage_records(self):
  helper=Mock();helper.checked.return_value='MemTotal: 120000000 kB\nMemAvailable: 10000000 kB\n';helper.peer.side_effect=lambda x:x
  with patch.object(c.controller.LocalClient,'chapter_health',return_value=({'streams':{'decoding':0,'prefilling':0}},{})):
   sample=c.base.books.speed.sampler(self.run,self.s,helper)
   for n in range(1,5):self.s['active_stage']=n;sample(0);self.assertIn('last_observation',self.s['stages'][str(n)])
  self.assertTrue((self.run/'effort-support-offline.json').exists());self.assertEqual(self.s['maximum_model_requests'],12)
 def test_actual_launcher_finished_resume_zero_host_calls(self):
  self.s['status']=c.TERMINAL;c.save(self.run,self.s)
  with patch.object(c.controller.subprocess,'run',side_effect=AssertionError('Unexpected host operation')),patch.object(c.controller.sys,'argv',['review','resume','--run',str(self.run)]):c.controller.main(c)
 def test_final_assembly_retains_checked_parts_and_failed_build_selection(self):
  def failed_compile(run,state,root,document,folder,assets):
   atomic_json(folder/'compilation.json',{'status':'syntax_failure','attempts':[]})
  with patch.object(c.compiler,'compile_saved',side_effect=failed_compile):c.finalize(self.run,self.s)
  for source in ['cf','spectral']:
   record=read_json(self.run/'deliveries'/source/'delivery.json');self.assertEqual(record['selection']['status'],'retained_last_compiling_version')
   self.assertEqual((self.run/'deliveries'/source/'master.tex').read_bytes(),(self.run/'baseline-editions'/source/'master.tex').read_bytes())
  part=c.SID['spectral']+'-whole-4.tex'
  self.assertEqual(sha(self.run/'deliveries/spectral/parts'/part),sha(self.run/'baseline-editions/spectral/parts'/part))
  with patch.object(c.compiler,'compile_saved',side_effect=AssertionError('Replayed compilation')):c.finalize(self.run,self.s)
 def test_partial_bundle_complete_hash_manifest_and_no_wire_payloads(self):
  import zipfile,hashlib
  self.s['status']='paused'
  with patch.object(c,'ROOT',self.run/'bundle-root'):out=c.bundle(self.run,self.s)
  with zipfile.ZipFile(out) as z:
   manifest=json.loads(z.read('FILE-HASHES.json'));self.assertEqual({r['path'] for r in manifest}|{'FILE-HASHES.json'},set(z.namelist()))
   self.assertIn('START-HERE.md',z.namelist());self.assertFalse(any(x.startswith(('requests/','calls/')) for x in z.namelist()))
   for row in manifest:self.assertEqual(hashlib.sha256(z.read(row['path'])).hexdigest(),row['sha256'])

if __name__=='__main__':unittest.main()
