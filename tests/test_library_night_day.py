"""Frozen60 selection, real planning boundaries and finite checkpoint orchestration."""
import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from probe.common import read_json,atomic_json,sha
from probe import library_night_day as n,library_first,image_review,focused_recovery
from scripts import library_pipeline as c

class NightDay(unittest.TestCase):
 def plan(self):
  return {'night_day':{'waves':[30,60],'checkpoints':[5,30,60]},'documents':[{'source_id':str(i),'physical_pages':list(range(12 if i<44 else 11))} for i in range(60)],'settings':dict(library_first.DEFAULTS),'paid_enabled':False,'spend_cap_usd':'0','accept_exact_fragments':True}
 def test_second_wave_does_not_inherit_terminal_extractor(self):
  with tempfile.TemporaryDirectory() as td:
   run=Path(td);old={'status':'finished','pages':{'a-p1':{'source_id':'a','status':'completed','outputs':[]},'a-p2':{'source_id':'a','status':'failed_page','outputs':[]}}};state={'extraction':{'mineru_pro':old}}
   seed=n.extraction_seed(run,state,['b']);record=read_json(seed/'state.json');self.assertEqual(record,{'status':'prepared','pages':{}})
   combined=n.merge_extraction(old,{'status':'finished','pages':{'b-p1':{'source_id':'b','status':'completed','outputs':[]}}},['b'])
   self.assertEqual(len(combined['pages']),3);self.assertEqual(combined['pages']['a-p2'],old['pages']['a-p2']);self.assertEqual(old['status'],'finished')
 def test_wave_resume_retains_consumed_failed_and_completed_attempts(self):
  with tempfile.TemporaryDirectory() as td:
   run=Path(td);pages={'b-p1':{'source_id':'b','status':'completed','outputs':[]},'b-p2':{'source_id':'b','status':'failed_page','outputs':[]}}
   seed=n.extraction_seed(run,{'extraction':{'mineru_pro':{'pages':pages}}},['b']);self.assertEqual(read_json(seed/'state.json')['pages'],pages)
   self.assertEqual(n.merge_extraction({'pages':pages},{'pages':copy.deepcopy(pages),'status':'paused'},['b'])['pages'],pages)
   changed=copy.deepcopy(pages);changed['b-p2']['status']='completed'
   with self.assertRaises(ValueError):n.merge_extraction({'pages':pages},{'pages':changed},['b'])
 def test_wrong_wave_source_is_shared_integrity_failure(self):
  with self.assertRaises(ValueError):n.merge_extraction({'pages':{}},{'pages':{'a-p1':{'source_id':'a'}}},['b'])
 def test_frozen_paid_scope_and_attempts(self):
  p=self.plan();self.assertEqual(len(n.validate_plan(p)),60)
  for field,value in [('paid_enabled',True),('allocation_id','old-seven-dollar-job'),('overnight',True)]:
   bad=copy.deepcopy(p);bad[field]=value
   with self.assertRaises(ValueError):n.validate_plan(bad)
  p['settings']['review_effort']='max'
  with self.assertRaises(ValueError):n.validate_plan(p)
 def test_two_waves_three_gates_and_finished_resume(self):
  with tempfile.TemporaryDirectory() as td:
   run=Path(td);p=self.plan();atomic_json(run/'plan.json',p)
   s={'documents':{str(i):{} for i in range(60)},'tasks':[{'source_key':str(i),'id':str(i)} for i in range(60)],'inputs_prepared':False};seen=[]
   def extract(run,state,source_ids):seen.append(('ocr',len(source_ids),source_ids[0]));state.setdefault('extraction_finished_sources',[]).extend(source_ids)
   def plan(run,state,source_ids):
    for sid in source_ids:state['documents'][sid]['planning_done']=True
   api=SimpleNamespace(extract=extract,plan_units=plan,verify=lambda r:None,save=lambda r,s:None)
   def local(run,state,controller,tasks):seen.append(('local',len(tasks),tasks[0]['source_key']))
   def gate(run,state,controller,count):seen.append(('gate',count));state.setdefault('night_day_checkpoints',{})[str(count)]={'saved':True}
   with patch.object(n,'local_requests',side_effect=local),patch.object(n,'checkpoint',side_effect=gate):
    n.execute(run,s,api);self.assertEqual(seen,[('ocr',30,'0'),('local',5,'0'),('gate',5),('local',25,'5'),('gate',30),('ocr',30,'30'),('local',30,'30'),('gate',60)])
    seen.clear();n.execute(run,s,api);self.assertEqual(seen,[])
 def test_shared_gate_failure_never_starts_wave_two(self):
  with tempfile.TemporaryDirectory() as td:
   run=Path(td);atomic_json(run/'plan.json',self.plan());s={'documents':{str(i):{} for i in range(60)},'tasks':[]};seen=[]
   api=SimpleNamespace(save=lambda *a:None,verify=lambda *a:None,extract=lambda *a,**k:seen.append(k['source_ids']),plan_units=lambda *a,**k:None)
   with patch.object(n,'local_requests'),patch.object(n,'checkpoint',side_effect=c.runtime.Fatal('concrete shared defect')),self.assertRaises(c.runtime.Fatal):n.execute(run,s,api)
   self.assertEqual(len(seen),1)
 def test_actual_planner_appends_second_wave_without_resealing_first(self):
  import test_library_pipeline as f
  h=f.Pipeline();h.setUp()
  try:
   first=sha(h.run/'task-plan.json');unit=copy.deepcopy(h.s['source_units'][h.key]);p=read_json(h.run/'plan.json');d=copy.deepcopy(p['documents'][0]);d['source_id']='second';d['filename']='Second.pdf';p['documents'].append(d);atomic_json(h.run/'plan.json',p)
   h.s['documents']['second']={'filename':'Second.pdf','units':[],'historical_selection':None,'source_sha256':'b'*64,'status':'pending_extraction'}
   h.s['extraction']['mineru_pro']['pages']['second-p1']={'status':'completed'};atomic_json(h.run/'arms/mineru_pro/pages/second-p1/native.json',read_json(h.run/'arms/mineru_pro/pages'/f'{h.sid}-p1/native.json'))
   atomic_json(h.run/'sources/second/secondary-assessment.json',{'policy':'fixture','pages':[]});h.s['inputs_prepared']=False
   c.plan_units(h.run,h.s,source_ids=['second'])
   self.assertEqual(len(h.s['tasks']),4);self.assertEqual(sha(h.run/'task-plan.json'),first);self.assertEqual(h.s['source_units'][h.key],unit);self.assertNotEqual(h.s['task_plan_path'],'task-plan.json')
  finally:h.doCleanups()
 def test_numerical_instruction_and_actual_serialized_bytes(self):
  import base64,struct
  image=c.ROOT/'fixtures/vision/case-01.png';raw=image.read_bytes();parts=[{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(raw).decode()}}]
  body=focused_recovery.critic_request('draft','source','secondary','context',effort='high',images=parts)
  prompt=body['messages'][0]['content'][0]['text']
  for text in ['source pixels','signs, exponents, decimal points','row/column association']:self.assertIn(text,prompt)
  self.assertEqual(image_review.image_budget(body)['request_bytes'],len(json.dumps(body,ensure_ascii=False,allow_nan=False).encode('utf-8')))
 def test_numeric_observations_are_preserved_as_claims_not_edits(self):
  draft='Unchanged source';data={'base_sha256':focused_recovery.digest(draft),'findings':[],'numerical_cell_checks':[{'source':'p1 TableA','row':'r2','column':'c3','printed_source':'1E-03','draft_reading':'1E-03','result':'matches'}]}
  revised,log=image_review.apply_review(draft,data);self.assertEqual(revised,draft);self.assertEqual(log['numerical_cell_checks'],data['numerical_cell_checks']);self.assertIn('not independently',log['numerical_cell_check_status'])
  data['numerical_cell_checks']=['bad']
  with self.assertRaises(ValueError):image_review.validate_review_shape(data)
 def test_join_checks_detect_repeated_passages_and_references(self):
  from probe.library_repair import overlap_screen
  from probe.library_completion import reference_check
  paragraph='This substantive original paragraph preserves its conditions and mathematical meaning. '*5
  docs=[r'\begin{document}'+paragraph+'\n\n'+r'\label{same}\end{document}',r'\begin{document}'+paragraph+'\n\n'+r'\label{same}\ref{lost}\end{document}']
  self.assertTrue(overlap_screen(list(zip(['a','b'],docs)))['repeated_substantive_paragraphs']);self.assertEqual(reference_check(docs)['undefined_references'],['lost']);self.assertEqual(reference_check(docs)['duplicate_labels'],['same'])
 def test_checkpoint_isolated_partial_continues_and_identity_failure_stops(self):
  with tempfile.TemporaryDirectory() as td:
   run=Path(td);p=self.plan();atomic_json(run/'plan.json',p);s={'tasks':[],'calls':[],'documents':{str(i):{'published':True,'delivery':str(run/str(i)),'units':[]} for i in range(5)}}
   for i in range(5):p['documents'][i]['library_document']={};atomic_json(run/str(i)/'manifest.json',[])
   atomic_json(run/'plan.json',p)
   rec={'status':'partial_source','selected_tex':[],'coverage':[],'output_ownership_check':{},'model_review':{'failed_or_incomplete_reviews':['x']},'outstanding_scopes':[{'pages':[1],'reason':'local failure; paid route disabled'}]}
   api=SimpleNamespace(verify=lambda r:None,publish_settled=lambda *a:None,policy=SimpleNamespace(validate_publication=lambda *a:rec),runtime=c.runtime,save=lambda *a:None,bundle=lambda *a:None)
   for i in range(5):s['documents'][str(i)]['filename']=str(i)+'.pdf'
   n.checkpoint(run,s,api,5);out=read_json(run/'checkpoints/after-05.json');self.assertEqual(out['decision'],'continue');self.assertEqual(out['counts']['failed_without_selected_text'],5)
   api.verify=Mock(side_effect=c.runtime.Fatal('identity changed'))
   with self.assertRaises(c.runtime.Fatal):n.checkpoint(run,s,api,5)
