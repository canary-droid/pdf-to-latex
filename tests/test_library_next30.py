"""Revision2 regressions: real saved defects, finite phase and shared-spend guards."""
import copy,json,tempfile,unittest
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
from probe.common import atomic_json,read_json,sha,fingerprint
from probe import library_repair as repair,library_allocation as allocation,library_fallbacks as shared,library_paid as paid,kimi_escalation as kimi,cloud_critic as cloud,author_source,followup_lifecycle as coverage
from scripts import library_pipeline as controller
from test_kimi_escalation import metadata
ROOT=controller.ROOT
PARENT=ROOT/'runs/library-overnight-20261108T040405Z'
DEV=ROOT/'results/tasks/next30-20261108T102340Z'

class Allocation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);(self.root/'runs').mkdir()
  self.auth=self.root/'authorization.json';atomic_json(self.auth,{'authorization_id':allocation.AUTH_ID,'revision':2,'new_combined_budget_usd':'7.00'})
  self.sources={'s':{'sha256':'a'*64,'physical_pages':[1,2]}}
  self.history={'summary':{'ceiling_usd':'10.00','actual_reported_usd':'1.20','unresolved_reserved_usd':'.50','reservations':16,'halt':None},'charges':[]}
  with patch.object(kimi,'history_snapshot',return_value=self.history):self.run,self.approval=allocation.create(self.root,self.auth,self.sources,kimi.profile(metadata(),'7.00',0),self.root/'previous')
 def record(self,i=1,kind='kimi',draft=None):
  unit={'id':str(i),'source_id':'s','source_sha256':'a'*64,'physical_pages':[1],'owned_blocks':['b'+str(i)],'primary':'x=1','draft_sha256':draft}
  r={'unit':unit,'kind':kind,'phase':'extraction' if kind=='mathpix' else 'convert','scope_sha256':fingerprint(unit)};shared.register_scope(self.run,r,self.approval,unit_verified=True);return r
 def authority(self,r,body):
  ident=shared.reservation_identity(r,self.approval);folder=Path(self.approval['ledger_root'])/'attempts'/ident;atomic_json(folder/'phase-authority.json',{'scope_sha256':r['scope_sha256'],'phase_identity':ident,'request_sha256':fingerprint(body),'approval_sha256':fingerprint(self.approval)});return folder
 def test_fresh_once_separate_history_child_and_missing_ledger(self):
  self.assertEqual(shared.budget_summary(self.run,self.approval)['remaining_usd'],'7.00')
  with patch.object(kimi,'history_snapshot',side_effect=AssertionError('Do not reset history')):again,a=allocation.create(self.root,self.auth,self.sources,{},self.root/'different-child')
  self.assertEqual(again,self.run);r=self.record();shared.reserve_budget(self.root/'child1',r,'4',a)
  self.assertFalse(shared.reserve_budget(self.root/'child2',r,'4',a)[1])
  with self.assertRaises(shared.NotApproved):shared.reserve_budget(self.root/'child2',self.record(2,'mathpix'),'4',a)
  self.assertEqual(kimi.ledger(self.run).prior_summary()['actual_reported_usd'],'1.20')
  (Path(a['ledger_root'])/'ledger.json').unlink()
  with self.assertRaises(kimi.IntegrityError):allocation.verify(a)
  with self.assertRaises(kimi.IntegrityError):shared.reserve_budget(self.run,r,'1',a)
 def test_unapproved_source_and_duplicate_allocation_rejected(self):
  r=self.record();r['unit']['source_sha256']='b'*64
  with self.assertRaises(ValueError):shared.register_scope(self.run,r,self.approval,unit_verified=True)
  with self.assertRaises(kimi.IntegrityError):allocation.create(self.root,self.auth,{}, {},self.root/'parent')
 def test_seventeenth_registered_phase_no_hidden_cap_and_duplicate_denied(self):
  body={'max_tokens':1,'messages':[]};ledger=cloud.Ledger(self.run,cost_estimator=lambda b:Decimal('.01'),token_estimator=lambda b:1)
  for i in range(17):
   r=self.record(i);folder=self.authority(r,body);ledger.reserve(body,folder,Decimal('8.30'),'trial')
  self.assertEqual(len(ledger.read()['reservations']),17)
  with self.assertRaises(cloud.AdmissionError):ledger.reserve(body,folder,Decimal('8.30'),'trial')
  ledger.stage_limits={'trial_calls':17,'readiness_calls':0}
  with self.assertRaises(cloud.AdmissionError):ledger.reserve(body,self.authority(self.record(18),body),Decimal('8.30'),'trial')
 def test_only_positive_prepost_proof_releases_hold_and_no_refund(self):
  r=self.record();ident,_=shared.reserve_budget(self.run,r,'1',self.approval);folder=Path(self.approval['ledger_root']);proof=self.root/'preflight.json';atomic_json(proof,{'phase':'proven_not_sent'})
  with self.assertRaises(ValueError):allocation.release_never_sent(folder,ident,{'disposition':'uncertain','proof_files':{str(proof):sha(proof)}})
  self.assertEqual(shared.budget_summary(self.run,self.approval)['exposure_usd'],'1')
  allocation.release_never_sent(folder,ident,{'disposition':'proven_not_sent','proof_files':{str(proof):sha(proof)}})
  self.assertEqual(shared.budget_summary(self.run,self.approval)['remaining_usd'],'7.00');self.assertNotIn('actual_usd',read_json(folder/'ledger.json')['reservations'][ident])
  self.assertFalse(shared.reserve_budget(self.run,r,'1',self.approval)[1])
 def test_parallel_admission_cannot_exceed_shared_cap(self):
  from concurrent.futures import ThreadPoolExecutor
  records=[self.record(1),self.record(2,'mathpix')]
  def reserve(r):
   try:return shared.reserve_budget(self.run,r,'4',self.approval)[1]
   except (shared.NotApproved,RuntimeError):return False
  with ThreadPoolExecutor(2) as pool:result=list(pool.map(reserve,records))
  self.assertEqual(sum(result),1);self.assertEqual(shared.budget_summary(self.run,self.approval)['exposure_usd'],'4')

class SourceRepairs(unittest.TestCase):
 def test_blank_source_not_empty_ocr_and_no_formula_or_image_erasure(self):
  import fitz
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'source.pdf';doc=fitz.open();doc.new_page();doc.new_page().insert_text((72,72),'x = 1');doc.new_page().draw_rect(fitz.Rect(40,40,90,90));doc.save(path);doc.close()
   self.assertTrue(repair.blank_page(path,1,sha(path))['qualified_blank'])
   self.assertFalse(repair.blank_page(path,2,sha(path))['qualified_blank']);self.assertFalse(repair.blank_page(path,3,sha(path))['qualified_blank'])
   with self.assertRaises(ValueError):repair.blank_page(path,1,'a'*64)
 def test_escape_aware_lee_math_and_actual_damage(self):
  self.assertEqual(repair.math_spans(r'\\[1ex] $x^2$ \$ \[x+1\]')[1],[])
  self.assertEqual(repair.math_spans(r'\\[1ex] $x^2$ \$ \[x+1\]')[0],['x^2','x+1'])
  self.assertTrue(repair.math_spans(r'\[x+1')[1]);self.assertTrue(repair.unbalanced_math_groups(r'\frac{x}{2'))
  state=read_json(PARENT/'state.json');key='original-c6fbf9bf1bbc7325-unit-001';version=state['versions'][key][state['current_versions'][key]]
  text=(PARENT/version['path']).read_text();self.assertIn(r'\\[1ex]',text);self.assertTrue(author_source.generated_content(text,{})['usable'])
 def test_equation_namespaces_and_real_missing_label(self):
  self.assertEqual(repair.equation_labels(r'\tag{A.59c} (B.59c) (59c)'),{'A.59c','B.59c','59c'})
  native={'blocks':[{'id':'b','kind':'formula_number','tex':'(A.59c)','assets':[]}]}
  result=coverage.coverage('Complete assigned prose $x=1$ '+r'\tag{B.59c}',native,['b'])
  self.assertIn('A.59c',result['missing_explicit_equation_numbers'])
 def test_salvage_never_invents_hash_or_ambiguous_edit_anchor(self):
  from probe.focused_recovery import apply_focused,digest
  draft='Equation x=1. Equation x=1.';value={'base_sha256':digest(draft),'findings':[]}
  self.assertEqual(repair.salvage_json('Here is JSON:\n'+json.dumps(value),digest(draft)),value)
  with self.assertRaises(ValueError):repair.salvage_json(json.dumps(value),'b'*64)
  with self.assertRaises(ValueError):repair.salvage_json(json.dumps(dict(value,base_sha256='EXACT_FULL_DRAFT_SHA256')),digest(draft))
  value['findings']=[{'status':'edit','old':'x=1','new':'x=2','source':'page1','reason':'fixture'}]
  revised,report=apply_focused(draft,json.dumps(value));self.assertEqual(revised,draft);self.assertNotEqual(report['findings'][0]['status'],'applied')
 def test_actual_saved_seams_and_source_accounting(self):
  rows=read_json(DEV/'curated.json')
  self.assertEqual(len(rows),24)
  for sid in {r['source_id'] for r in rows}:
   selected=[r for r in rows if r['source_id']==sid]
   self.assertFalse(repair.overlap_screen([(r['unit'],Path(r['selected_tex']).read_text()) for r in selected])['duplicate_equation_tags'])
   self.assertTrue(all(controller.content_check(PARENT,{'source_units':{r['unit']:r['source_unit']}},{'key':r['unit']},Path(r['selected_tex']).read_text())['usable'] for r in selected))
  raw=read_json(PARENT/'source-plans/original-1e05399704af3696.json');scope=next(r for r in raw['scopes'] if r['disposition']=='outstanding')
  self.assertEqual(len(scope['blocks']),53);self.assertEqual(scope['text_sha256'],'d0e768823ff486938dad56208c68c1c6e83b7cf8d44d31ad005e0b16bc2fa35d')
  from probe.library_first import structural_units
  units=structural_units(scope['native_blocks'],maximum_pages=6,maximum_chars=24000)
  self.assertTrue(all(u['disposition']=='included' for u in units));self.assertEqual([b for u in units for b in u['blocks']],scope['blocks'])
 def test_exact_thirty_identities_and_no_substitution(self):
  task=Path(read_json(ROOT/'results/next30-task-current.json')['task_directory']);selection=read_json(task/'selected-30.json')['papers'];resolved=read_json(DEV/'resolved-inputs.json')
  self.assertEqual(len(selection),30);self.assertEqual(sum(x['pages'] for x in selection),397);self.assertIn('Kienitz',selection[0]['filename'])
  self.assertEqual({x['sha256'] for x in selection},{x['sha256'] for x in resolved})
  self.assertFalse(any('Anfuso' in x['filename'] or x['queue_id']=='P029' for x in selection))
 def test_appendix_section_ends_proof_chain_without_splitting_proof(self):
  from probe.library_first import structural_units
  blocks=[{'id':str(i),'kind':'paragraph_title' if i==3 else 'text','tex':text,'page':{'original_physical_page':i+1}} for i,text in enumerate(['Lemma A.1. The claim.','Proof. Full argument.','The complete last step.',r'\section*{B.1. Newton procedure}','Independent algorithm.'])]
  units=structural_units(blocks,maximum_pages=3)
  self.assertTrue(all(x['disposition']=='included' for x in units));self.assertEqual(units[0]['blocks'],['0','1','2'])

if __name__=='__main__':unittest.main()

class SavedLifecycle(unittest.TestCase):
 def test_boy_37_reused_pages_and_lewis_missing_scope_plan_without_ocr_or_mathpix(self):
  import shutil
  current=Path(read_json(ROOT/'results/next30-current.json')['run']);s=read_json(current/'state.json');p=read_json(current/'plan.json')
  with tempfile.TemporaryDirectory() as tmp:
   r=Path(tmp);p['documents']=[d for d in p['documents'] if d['role']=='recovery'];p['overnight']=False;p['paid_approval']={};s['documents']={d['source_id']:s['documents'][d['source_id']] for d in p['documents']}
   for name in ('sources','fixed-scopes','arms','inputs'):shutil.copytree(current/name,r/name)
   atomic_json(r/'plan.json',p)
   with patch.object(paid,'mathpix_client',side_effect=AssertionError('Blank page must not dispatch')),patch.object(controller,'extract',side_effect=AssertionError('Do not repeat saved OCR')):
    controller.plan_units(r,s);count=len(s['tasks']);controller.plan_units(r,s);self.assertEqual(count,len(s['tasks']))
   boy='original-af03317e4e74c832';lewis='original-1e05399704af3696'
   self.assertFalse(s['documents'][boy]['outstanding_scopes']);self.assertEqual(s['documents'][boy]['source_accounting']['blank_pages']['38']['disposition'],'source_verified_blank_no_inference')
   keys=s['documents'][lewis]['units'];self.assertEqual(keys[keys.index(lewis+'-unit-003')+1],lewis+'-missing-001');self.assertFalse(s['documents'][lewis]['outstanding_scopes'])
   owned=[b for k in s['documents'][boy]['units'] for b in s['source_units'][k]['blocks']];self.assertEqual(len(owned),len(set(owned)))
   self.assertEqual({n for k in s['documents'][boy]['units'] for n in s['source_units'][k]['physical_pages']},set(range(1,38)))
 def test_real_finish_salvages_wrapper_and_preserves_exact_draft_and_raw_response(self):
  import test_library_pipeline as fixtures
  h=fixtures.Pipeline('test_finished_launcher_does_not_touch_host_or_model');h.setUp()
  try:
   normal=h.transport
   def transport(run,call,body,**kw):
    answer,out=normal(run,call,body,**kw)
    if call['parent'].endswith('/critic'):
     from probe.common import files_manifest
     answer='Here is the review JSON:\n'+answer+'\nEnd of review.';folder=run/'calls'/call['id'];(folder/'content.txt').write_text(answer);(folder/'answer.txt').write_text(answer);atomic_json(folder/'manifest.json',[x for x in files_manifest(folder) if x['path']!='manifest.json']);out['seal']=sha(folder/'manifest.json')
    return answer,out
   h.transport=transport;h.coordinate()
   self.assertEqual(h.s['tasks'][1]['status'],'review_completed');self.assertEqual(len(h.seen),2)
   findings=read_json(h.run/'call-results/call-002/findings.json');self.assertIn('response_normalization',findings)
   self.assertEqual((h.run/h.s['versions'][h.key]['convert']['path']).read_text(),fixtures.DOC+'\n')
  finally:h.doCleanups()
