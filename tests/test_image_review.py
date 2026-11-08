import copy,json,tempfile,unittest,re
from pathlib import Path
from unittest.mock import patch
from probe import image_review as v,focused_recovery as focused,chapter_protocol,book_completion as coverage,followup_lifecycle
from probe.common import read_json,fingerprint
from probe.local_model import LocalClient
ROOT=Path(__file__).resolve().parents[1]
def run():
 p=ROOT/'results/glm-image-review-current.json'
 if not p.exists():raise unittest.SkipTest('Saved image experiment preparation unavailable')
 return Path(read_json(p)['run'])
class ImageReviewTests(unittest.TestCase):
 def test_real_saved_images_in_actual_client_payload(self):
  r=run();body=read_json(r/'requests/cf-B.json');seen=[]
  client=LocalClient('http://127.0.0.1:8888/v1','glm53-regular',api_key='',purpose='simple_chapter',timeout=None,max_tokens=131072);client.model='glm53-regular'
  # Stub socket boundary only; verify LocalClient.chat builds the exact body.
  def transport(method,path,payload,*a):
   seen.append(payload);raise RuntimeError('stop before network')
  with patch.object(client,'_request',side_effect=transport):
   with self.assertRaises(RuntimeError):client.chat(body['messages'],r,'mock',reasoning_effort='max',stream=True)
  self.assertEqual(seen,[body]);self.assertEqual(sum(x['type']=='image_url' for x in body['messages'][0]['content']),7)
 def test_missing_changed_images_and_stale_draft(self):
  r=run();records=read_json(r/'inputs/cf/B-images.json');bad=copy.deepcopy(records);bad[0]['sha256']='0'*64
  with self.assertRaises(ValueError):v.image_parts(bad,r)
  bad=copy.deepcopy(records);bad[0]['path']='nonexistent.png'
  with self.assertRaises(FileNotFoundError):v.image_parts(bad,r)
  payload=read_json(r/'inputs/cf/payload.json')
  with self.assertRaises(ValueError):focused.apply_focused(payload['draft'],json.dumps({'base_sha256':'stale','findings':[]}))
 def test_text_only_request_unchanged_and_image_budget(self):
  r=run();p=read_json(r/'inputs/cf/payload.json');original=read_json(r/'inputs/cf/historical-request.json')
  self.assertEqual(focused.critic_request(p['draft'],p['source_output_scope'],p['secondary'],p['context_only']),original)
  body=read_json(r/'requests/cf-B.json');budget=chapter_protocol.budget(body,1048576)
  self.assertGreater(budget['image_tokens'],6000);self.assertLess(budget['combined_upper_estimate'],budget['request_bytes']);self.assertEqual(budget['image_count'],7)
 def test_exact_parallel_and_high_comparisons(self):
  r=run()
  for source in ['cf','ig']:
   a=read_json(r/'requests'/(source+'-B.json'));b=read_json(r/'requests'/(source+'-B-parallel.json'));h=read_json(r/'requests'/(source+'-B-high.json'))
   self.assertEqual(a,b);h['reasoning_effort']='max';self.assertEqual(a,h)
 def test_legitimate_headings_and_verified_figure_group(self):
  text=r'\section{Accuracy of the approximation}\begin{tabular}{c}1\end{tabular}\section{Editorial history}\section{Notes and results}'
  self.assertEqual(coverage.body_only(text),text)
  for title in ['Editorial notes','Accuracy notes','Notes and source results']:
   genuine=r'\section{'+title+'}Original source material.'
   self.assertEqual(coverage.body_only(genuine,[title]),genuine)
  marked=text+'\n% PDF2TEX_GENERATED_NOTES_BEGIN\n'+r'\section*{Editorial corrections and unresolved issues}generated'
  self.assertEqual(coverage.body_only(marked),text+'\n')
  r=run();native=read_json(ROOT/'runs/extraction-followup-20261105T223237Z-lifecycle/inputs/original-547334b059504dcb-whole-1/native.json');native['verified_figure_groups']=[read_json(r/'repairs/original-547334b059504dcb/verified-figure-group.json')]
  selected=(r/'repairs/original-547334b059504dcb/original-547334b059504dcb-whole-1-working.tex').read_text();ids=[b['id'] for b in native['blocks']];result=coverage.coverage_check(selected,native,ids)
  self.assertEqual(result['missing_required_charts'],[]);self.assertFalse(result['table_count_warning']);self.assertFalse(result['duplicated_verified_figures'])
  duplicate=selected.replace(r'\begin{document}',r'\begin{document}\includegraphics{assets/original-547334b059504dcb-p4-region-3.png}')
  self.assertTrue(coverage.coverage_check(duplicate,native,ids)['duplicated_verified_figures'])
 def test_real_spectral_assembly_and_reference_propagation(self):
  r=run();report=read_json(r/'repairs/report.json');sp=next(x for x in report if '185f' in x['source']);self.assertEqual(sp['status'],'passed');self.assertFalse(sp['unresolved_references'])
  checks=read_json(r/'repairs/original-185f783748bb248e/render-checks.json');self.assertEqual(set(checks['printed_theorems']),set('123456'));self.assertEqual(set(checks['printed_assumptions']),set('1234'))
  x=r'\documentclass{article}\begin{document}\label{same}\end{document}';y=r'\documentclass{article}\begin{document}\ref{same}\end{document}'
  _,_,log=followup_lifecycle.assemble_documents([('a',x),('b',x),('c',y)]);self.assertEqual(len(log['unresolved_references']),1)
 def test_real_figure_bounds_and_source_reading(self):
  r=run();d=read_json(r/'repairs/original-547334b059504dcb/render-checks.json');self.assertEqual(len(d['image_bounds']),1);self.assertFalse(d['image_bounds'][0]['outside']);self.assertFalse(d['severe_float_warning'])
  sheet=read_json(r/'evaluation/reading-sheet.json');self.assertIn('Gamma(b+n)',sheet['cf'][0]['printed'])
 def test_finished_resume_has_no_host_or_model_operations(self):
  from scripts import glm_image_review as ctrl
  with patch.object(ctrl,'verify',return_value={'status':ctrl.TERMINAL}),patch.object(ctrl.subprocess,'run',side_effect=AssertionError('host call')),patch.object(ctrl.sys,'argv',['review','resume','--run','/tmp/finished']):ctrl.main()
 def test_consumed_requests_and_wrong_outgoing_images_cannot_replay(self):
  import shutil
  from scripts import glm_image_review as ctrl
  r=run()
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp)
   for name in ['plan.json','binding.json','state.json']:shutil.copyfile(r/name,dest/name)
   for name in ['inputs','requests']:shutil.copytree(r/name,dest/name)
   state=read_json(dest/'state.json');state['calls']=[{'id':'call-001','parent':'cf-A','status':'in_progress'}]
   (dest/'state.json').write_text(json.dumps(state));t=state['tasks'][0]
   with self.assertRaises(ctrl.runtime.Fatal):ctrl.before(dest,state,t,ctrl.body_for(dest,state,t))
   state['calls'].append(dict(state['calls'][0],id='call-002'));(dest/'state.json').write_text(json.dumps(state))
   with self.assertRaises(ctrl.runtime.Fatal):ctrl.verify(dest)
   state['calls']=[];(dest/'state.json').write_text(json.dumps(state));b=read_json(dest/'requests/cf-A.json');b['messages'][0]['content'][-1]['image_url']['url']='wrong image';(dest/'requests/cf-A.json').write_text(json.dumps(b))
   with self.assertRaises(ctrl.runtime.Fatal):ctrl.body_for(dest,state,t)
 def test_first_response_without_image_expansion_stops(self):
  import shutil
  from scripts import glm_image_review as ctrl
  r=run()
  with tempfile.TemporaryDirectory() as tmp:
   dest=Path(tmp);shutil.copyfile(r/'plan.json',dest/'plan.json');s=read_json(r/'state.json');t=s['tasks'][0]
   # The saved fixture is now finished. Exercise a FIRST response, not the
   # intentional idempotent return for its already-settled historical call.
   t.pop('settled_call',None)
   call={'id':'call-001','parent':t['id'],'status':'completed_response','metadata':{'usage':{'prompt_tokens':10}}}
   s['calls']=[call]
   with self.assertRaises(ctrl.runtime.Fatal):ctrl.finish(dest,s,t,'{}',call)
   self.assertFalse(read_json(dest/'image-verification/cf-A.json')['passed'])
 def test_repaired_numbering_matches_printed_equation_start(self):
  d=read_json(run()/'repairs/Spectral-numbering-qualified/numbering-verification.json');self.assertTrue(d['passed']);self.assertEqual(d['actual_standalone_numbers'][:23],list(range(1,24)))

 def test_real_resource_sampler_has_every_frozen_stage(self):
  from scripts import glm_image_review as ctrl
  from unittest.mock import Mock
  from probe.local_model import LocalClient
  r=run();plan=read_json(r/'plan.json')
  s={'active_stage':0,'stages':{str(i+1):{} for i in range(len(plan['stages']))}}
  helper=Mock();helper.checked.return_value='MemTotal: 120000000 kB\nMemAvailable: 10000000 kB\n';helper.peer.side_effect=lambda x:x
  health={'streams':{'decoding':0,'prefilling':0}}
  with tempfile.TemporaryDirectory() as tmp,patch.object(LocalClient,'chapter_health',return_value=(health,{})):
   sample=ctrl.base.books.speed.sampler(Path(tmp),s,helper)
   for i in range(1,4):
    s['active_stage']=i;obs=sample(0);self.assertGreater(obs['memory_available_bytes']['head'],4*1024**3)
    self.assertIn('last_observation',s['stages'][str(i)])
