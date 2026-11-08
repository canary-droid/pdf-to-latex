import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from probe import image_review as image,focused_recovery as focused,library_first as policy
from probe.common import read_json,atomic_json
from scripts import image_review_recovery as old,prepare_library_repairs as repairs

class ReviewReliability(unittest.TestCase):
 def test_shape_rejected_before_attribute_access(self):
  for value in [[],None,{'findings':None},{'findings':[None]},{'findings':[[]]}]:
   with self.assertRaises(ValueError):image.apply_review('draft',value)
 def test_literal_tex_and_shared_schema(self):
  draft='\\begin{document}\n\\[\nu(r)=1\n\\]\n\\end{document}'
  body=focused.critic_request(draft,'source','secondary','context',images=[])
  payload=image.request_payload(body);self.assertEqual(payload['draft'],draft)
  self.assertNotIn('draft',json.loads(body['messages'][0]['content'][0]['text'].split('\n',1)[1]))
  self.assertIn('\nu(r)',body['messages'][0]['content'][1]['text']);self.assertNotIn('\\nu(r)',body['messages'][0]['content'][1]['text'])
  example=body['messages'][0]['content'][0]['text']
  for field in image.EVIDENCE_FIELDS+('replacement_format','scope_review'):self.assertIn(field,example)
 def test_missing_scope_and_pending_suggestions_not_complete(self):
  draft='draft';_,log=image.apply_review(draft,{'base_sha256':focused.digest(draft),'findings':[{'status':'suggestion','reason':'uncertain'}]})
  self.assertFalse(log['review_complete_attested']);self.assertEqual(log['pending_suggestions'],1)
  summary=policy.review_summary([{'id':'failed','phase':'critic','status':'truncation'}],log['findings'])
  self.assertFalse(summary['reviewed_full_scope_attested']);self.assertEqual(summary['failed_or_incomplete_reviews'],['failed']);self.assertEqual(summary['pending_suggestion_count'],1)
 def test_eight_findings_requires_explicit_scope(self):
  draft='draft';p={'base_sha256':focused.digest(draft),'findings':[{'status':'unresolved','reason':'issue'}]*8,'scope_review':{'full_assigned_scope_reviewed':False,'additional_findings_remain':True,'unreviewed_scope':'last proof'}}
  _,log=image.apply_review(draft,p);self.assertFalse(log['review_complete_attested']);self.assertTrue(log['scope_review']['additional_findings_remain'])
 def test_real_finish_consumes_array_and_null_without_stopping_other_units(self):
  parent=Path(read_json(old.POINTER)['run']);plan=read_json(parent/'plan.json');original=read_json(parent/'state.json')
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);atomic_json(run/'plan.json',plan)
   import shutil
   shutil.copytree(parent/'inputs',run/'inputs')
   s=copy.deepcopy(original);s['calls']=[]
   for i,answer in enumerate(['[]','{"findings":[null]}']):
    t=s['tasks'][i];t.pop('settled_call',None);t['status']='running';p=plan['tasks'][i]
    call={'id':f'call-invalid-{i}','parent':t['id'],'metadata':{'usage':{'prompt_tokens':p['cpu_expectation']['prompt_tokens']}}}
    old.finish(run,s,t,answer,call);self.assertEqual(t['status'],'invalid_review');self.assertEqual(t['settled_call'],call['id']);self.assertEqual((run/'reviews'/t['id']/'proposal.txt').read_text(),answer)
   # A later independent valid answer still goes through the REAL settlement path.
   t=s['tasks'][2];t.pop('settled_call',None);p=plan['tasks'][2];call={'id':'call-valid','parent':t['id'],'metadata':{'usage':{'prompt_tokens':p['cpu_expectation']['prompt_tokens']}}}
   def compiler(*args,**kw):atomic_json(args[4]/'compilation.json',{'status':'passed'})
   with patch.object(old.compiler,'compile_saved',side_effect=compiler):old.finish(run,s,t,json.dumps({'base_sha256':p['draft_sha256'],'findings':[]}),call)
   self.assertEqual(t['status'],'review_completed');self.assertFalse(t['review_complete_attested'])
 def test_source_checked_saved_corrections_and_no_g_to_rho(self):
  cf=(repairs.PARENT/'deliveries/cf/parts'/f'{repairs.CF}-whole-3.tex').read_text();fixed,log=repairs.corrections(cf,'cf')
  self.assertIn(r'M = \sqrt{b^2 - 4ac}/(2c)',fixed);self.assertIn(r'\nu > -\frac{1}{2}',fixed)
  source_body=fixed.split('Editorial corrections')[0];self.assertNotIn(r'X_{\rho}',source_body);self.assertNotIn(r'X _ {o}',source_body);self.assertNotIn(r'X _ {\varrho}',source_body)
  self.assertEqual(sum(r['kind']=='transcription_repair' for r in log),7)
  self.assertIn('not an OCR/transcription repair',fixed)
  sp=(repairs.PARENT/'deliveries/spectral/parts'/f'{repairs.SP}-whole-3.tex').read_text();fixed,log=repairs.corrections(sp,'spectral');self.assertEqual(len(log),1);self.assertIn('u (r)',fixed)
 def test_policy_no_paid_inference_and_integrity_not_repair(self):
  self.assertFalse(policy.DEFAULTS['paid_enabled']);self.assertEqual(policy.DEFAULTS['new_spend_budget_usd'],'0')
  self.assertEqual(policy.fallback_kind('critic','reasoning_exhaustion'),'kimi');self.assertEqual(policy.fallback_kind('extraction','failed'),'mathpix')
  self.assertEqual(policy.fallback_kind('critic','uncertain_dispatch'),'stop_and_reconcile')
 def test_current_library_state_prevents_new_run_replay(self):
  for row,pointer in [({'status':'ready'},None),({'status':'partial'},{'status':'ready_working_source'}),({'status':'partial','latest_attempt':{'run':'finished'}},None),({'status':'deferred'},None)]:
   with self.assertRaises(ValueError):policy.admit_missing_conversion(row,pointer)
  policy.admit_missing_conversion({'status':'partial'},{'status':'extraction_failed'})

if __name__=='__main__':unittest.main()
