import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from probe import focused_recovery as f,ocr_diagnostics as o,tex_syntax_repair as syntax
from scripts import focused_recovery as ctrl

class SourceQualityTests(unittest.TestCase):
 def test_corrupt_glyph_is_auditable_and_prose_retained(self):
  original='Useful assumption: x > 0.\nBroken \x01 + \ufffd\nα ≤ β; ∑ xᵢ² ≥ 0.\n'
  q=f.secondary_assessment([{'physical_pdf_page':3,'text':original}]);self.assertEqual(q['suppressed'],1);self.assertEqual(''.join(x['original'] for x in q['passages']),original);self.assertIn('Broken',q['pages'][0]['text']);self.assertIn('α ≤ β',q['pages'][0]['text']);self.assertIn('page 3, line 2',q['pages'][0]['text'])
 def test_unusual_math_or_reading_order_does_not_suppress(self):
  q=f.secondary_assessment([{'physical_pdf_page':1,'text':'α β γ δ ε ζ η θ κ λ μ ν π ρ σ τ φ χ ψ ω = 0\n'}]);self.assertEqual(q['suppressed'],0);self.assertTrue(q['passages'][0]['source_check_required'])
 def test_primary_not_declared_correct(self):
  self.assertIn('Neither extraction is automatically correct',f.TRANSCRIPTION)
 def test_scope_partition_has_no_gaps_or_duplicate_output(self):
  native={'blocks':[{'id':str(i),'kind':'text','tex':'Definition and proof together '+str(i),'page':{'original_physical_page':i+1}} for i in range(6)]}
  units=f.partition(native,['2','4'],'Fixture');f.validate_partition(units,list(map(str,range(6))))
  units[1]['blocks'].append('0')
  with self.assertRaises(ValueError):f.validate_partition(units,list(map(str,range(6))))
 def test_proof_cannot_be_new_scope(self):
  native={'blocks':[{'id':str(i),'kind':'text','tex':t,'page':{'original_physical_page':1}} for i,t in enumerate(['Theorem 1','Proof. Details'])]}
  with self.assertRaises(ValueError):f.partition(native,['1'],'fixture')

class EditTests(unittest.TestCase):
 def answer(self,draft,findings):return json.dumps({'base_sha256':f.digest(draft),'findings':findings})
 def edit(self,old,new):return {'status':'edit','old':old,'new':new,'source':'PDF p9 eq13','reason':'Printed original supports this coefficient'}
 def test_stale_hash_rejected(self):
  with self.assertRaises(ValueError):f.apply_focused('new',self.answer('old',[]))
 def test_located_math_edit_separate_derivative(self):
  text='First. $x+2y$. Last.';new,log=f.apply_focused(text,self.answer(text,[self.edit('$x+2y$','$x+3y$')]),[[7,14]])
  self.assertEqual(new,'First. $x+3y$. Last.');self.assertEqual(text,'First. $x+2y$. Last.');self.assertEqual(log['findings'][0]['disposition'],'applied_model_claim')
 def test_ambiguous_overlapping_and_outside_edits_rejected(self):
  text='alpha beta gamma alpha'
  findings=[self.edit('alpha','omega'),self.edit('beta gamma','beta delta'),self.edit('gamma','delta')]
  new,log=f.apply_focused(text,self.answer(text,findings));self.assertEqual(new,text);self.assertTrue(all(x['disposition']=='rejected' for x in log['findings']))
  text='abc def';new,log=f.apply_focused(text,self.answer(text,[self.edit('def','ghi')]),[[0,3]]);self.assertEqual(new,text)
 def test_number_assets_and_substantive_deletion_protected(self):
  for text,new in [(r'\tag{13} x',r'\tag{14} x'),(r'\includegraphics{a.png}',r'\includegraphics{b.png}'),('Entire important paragraph with assumptions.','Fixed.')]:
   result,log=f.apply_focused(text,self.answer(text,[self.edit(text,new)]));self.assertEqual(result,text);self.assertEqual(log['findings'][0]['disposition'],'rejected')
 def test_unresolved_findings_do_not_prevent_other_review(self):
  text='x+y';new,log=f.apply_focused(text,self.answer(text,[{'status':'unresolved','source':'p1','reason':'Two source readings disagree'},self.edit('x+y','x-y')]));self.assertEqual(new,'x-y');self.assertEqual(log['findings'][0]['disposition'],'unresolved')

class RecoveryTests(unittest.TestCase):
 def test_no_answer_vs_truncated_final_and_uncertain(self):
  c={'status':'failed','metadata':{'finish_reason':'length','usage':{'completion_tokens':100,'completion_tokens_details':{'reasoning_tokens':100}}}}
  self.assertEqual(f.classify(c,''),'reasoning_exhaustion');c['metadata']['usage']['completion_tokens_details']['reasoning_tokens']=70;self.assertEqual(f.classify(c,'partial tex'),'truncated_final');self.assertEqual(f.classify({'status':'in_progress'},''),'uncertain_dispatch')
 def test_one_phase_reservation_survives_resume(self):
  s={'chapter_contract':'annotated-chapter-v1','execution_limits':{'calls':None,'attempts_per_unit':1},'timing_policy':'manual_only','calls':[],'first_dispatch':None};ctrl.runtime.reserve(s,'x/critic','hash')
  with self.assertRaises(ctrl.runtime.StopRun):ctrl.runtime.reserve(copy.deepcopy(s),'x/critic','hash')
 def test_finished_resume_has_zero_external_operations(self):
  with patch.object(ctrl,'verify',return_value={'status':ctrl.TERMINAL}),patch.object(ctrl.subprocess,'run') as subprocess:ctrl.launch(Path('/unused'));subprocess.assert_not_called()
 def test_requests_separate_context_and_do_not_include_expected_answers(self):
  b=f.conversion_request('TARGET','SECONDARY','DEFINITION','low');self.assertEqual(b['reasoning_effort'],'low');self.assertEqual(b['max_tokens'],131072);self.assertIn('DO NOT EMIT AGAIN',b['messages'][0]['content']);self.assertNotIn('held-out',b['messages'][0]['content'])
 def test_positive_subpixel_only(self):
  q=[[1.,1.],[1.4,1.],[1.4,9.],[1.,9.]];self.assertEqual(o.qualified_size(q,(10,10,3),(0,8)),(1,8));self.assertIsNone(o.qualified_size([[1,1]]*4,(10,10),(0,0)));self.assertIsNone(o.qualified_size([[-1,1],[.4,1],[.4,9],[-1,9]],(10,10),(1,8)));self.assertIsNone(o.qualified_size(q,(10,10),(4,8)))
 def test_tag_relocation_retains_exact_expression_and_number(self):
  text=r'\begin{equation*}\begin{aligned}x&=a+\tag{33}b\end{aligned}\end{equation*}'
  new=syntax.relocated_tag(text);self.assertIsNotNone(new);self.assertEqual(new.replace(r'\tag{33}',''),text.replace(r'\tag{33}',''));self.assertIn(r'\end{aligned}\tag{33}',new)
  self.assertIsNone(syntax.relocated_tag(text.replace('b',r'b\tag{34}')))
 def test_saved_cf_regression_preserves_source_number(self):
  parent=Path('/home/mdi/projects/pdf-to-latex/runs/originals-batch-20261101T212602Z-ab2d41');p=parent/'versions/original-21debf82bc2c0a3d-part-001/convert-call-080-annotated/document.tex'
  if not p.exists():self.skipTest('Saved run not available')
  text=p.read_text();new,edits=syntax.deterministic(text,{'line':409,'message':r'Package amsmath Error: \tag not allowed here.'});self.assertTrue(edits);self.assertEqual(new.replace(r'\tag{33}',''),text.replace(r'\tag{33}',''))

if __name__=='__main__':unittest.main()

class SchedulerIntegration(unittest.TestCase):
 def test_failed_max_reviews_low_once_without_reconversion_or_reset(self):
  from probe import chapter_concurrency as concurrent
  from probe.common import atomic_json,sha
  from probe.experiment import seal
  from test_speed_suite import health
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);draft=r'\documentclass{article}\begin{document}$x+y$\end{document}'
   state={'status':'running','chapter_contract':'annotated-chapter-v1','suite_protocol':f.VERSION,'execution_limits':{'calls':None,'attempts_per_unit':1},'timing_policy':'manual_only','calls':[],'first_dispatch':None,'concurrency_policy':copy.deepcopy(concurrent.POLICY),'connection_failures':0,'active_stage':1,'source_units':{},'tasks':[],'current_versions':{'fixture':'saved-baseline'},'versions':{'fixture':{'saved-baseline':{'path':'base.tex','sha256':f.digest(draft),'compilation':{'status':'passed'}}}},'production_stage':{'task_ids':[]},'low_supported':True,'selection_ledger':[],'documents':{'s':{'filename':'fixture.pdf'}},'syntax_lineages':{}}
   (r/'base.tex').write_text(draft);section={'text':'Printed source x+y','physical_pages':[1],'blocks':['b']}
   ctrl.add_unit(state,'fixture','s',section,saved={'sha256':f.digest(draft)});state['production_stage']['task_ids']=[t['id'] for t in state['tasks']]
   atomic_json(r/'plan.json',{'maximum_model_requests':4});atomic_json(r/'quality/s.json',{'pages':[{'physical_pdf_page':1,'printed_page':None,'text':'x+y'}]});atomic_json(r/'inputs/s/native.json',{'key':'s','source':'s','blocks':[]});seen=[]
   def transport(run,call,body,**kwargs):
    seen.append(body['reasoning_effort']);folder=run/'calls'/call['id'];atomic_json(folder/'request.json',body)
    answer=None if len(seen)==1 else json.dumps({'base_sha256':f.digest(draft),'findings':[]})
    call.update(status='failed' if answer is None else 'completed_response',failure_kind='truncation' if answer is None else None,elapsed_seconds=.01,metadata={'finish_reason':'length' if answer is None else 'stop','http_status':200,'usage':{'completion_tokens':100,'completion_tokens_details':{'reasoning_tokens':100}}});(folder/'answer.txt').write_text(answer or '');seal(folder);call['seal']=sha(folder/'manifest.json');return answer,call
   def compiled(run,s,key,label):s['versions'][key][label]['compilation']={'status':'passed'};return {'status':'passed'}
   active=[]
   def changed():ctrl.adjust(r,state);active[:]=[t for t in state['tasks'] if t['status'] not in ('dormant','not_needed')]
   with patch.object(ctrl,'progress'),patch.object(ctrl,'compile_version',side_effect=compiled),patch.object(ctrl.scope,'coverage_check',return_value={}):
    changed()
    for _ in range(2):concurrent.coordinate(r,state,active,body_for=ctrl.body_for,finish=ctrl.finish,verify=lambda:None,changed=changed,sample=lambda n:health(n),transport=transport,poll_seconds=.01,fixed_level=2,before_reserve=lambda s,t,b:ctrl.before(r,s,t,b))
   self.assertEqual(seen,['max','low']);self.assertEqual(len(state['calls']),2);self.assertEqual((r/'base.tex').read_text(),draft);self.assertEqual(state['tasks'][1]['status'],'critic_unchanged');self.assertEqual(state['tasks'][2]['status'],'not_needed')


class QualifiedHandoffTests(unittest.TestCase):
 def test_existing_width_guard_preserves_accepted_box_set(self):
  for width in (-1,0,.5,2.99,3,5):
   points=[[0,0],[width,0],[width,10],[0,10]]
   self.assertEqual(o.existing_width_rejection(points,3),(points[2][0]-points[0][0])<3)
 def test_focused_saved_draft_omits_unrelated_body_but_binds_whole_hash(self):
  draft=r'\documentclass{article}\begin{document}UNRELATED-START. TARGET. UNRELATED-END.\end{document}'
  a=draft.index('TARGET.');b=a+len('TARGET.');body=f.critic_request(draft,'source','secondary','definitions',ranges=[[a,b]])
  prompt=body['messages'][0]['content'];self.assertIn(f.digest(draft),prompt);self.assertIn('TARGET.',prompt);self.assertNotIn('UNRELATED-START',prompt);self.assertNotIn('UNRELATED-END',prompt)
