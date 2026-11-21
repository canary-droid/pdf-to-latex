"""Saved next30 repair boundaries; no real model/provider/compiler requests."""
import copy,json,tempfile,unittest,re
from pathlib import Path
from unittest.mock import patch
from fractions import Fraction as F
from probe.common import read_json,atomic_json,sha,fingerprint,files_manifest
from probe import library_completion as fix,library_repair,library_fallbacks as paid
from scripts import prepare_library_completion as prep,library_pipeline as c

class SavedRepairs(unittest.TestCase):
 def test_all_eight_supplied_fragments_match_body_and_source_identity(self):
  state=read_json(prep.PARENT/'state.json')
  for row in read_json(prep.TASK/'fragment-candidates/manifest.json'):
   raw=(prep.PARENT/'calls'/row['call']/'content.txt').read_bytes();wrapped,record=fix.wrap_fragment(raw)
   self.assertEqual(fix.digest(wrapped),row['candidate_sha256']);self.assertEqual(fix.digest(record['body']),row['body_sha256'])
   self.assertEqual(''.join(record[k] for k in ('prefix','opening_fence','body','closing_fence','suffix')).encode(),raw)
   u=state['source_units'][row['unit']];self.assertEqual(u['text_sha256'],row['owned_source_text_sha256']);self.assertEqual(row['physical_pages'],u['physical_pages'])
 def test_fragment_never_repairs_partial_envelopes_or_multiple_truncated_fences(self):
  for raw in [b'```tex\nx',b'```tex\nx\n```\n```tex\ny\n```\n',b'```tex\n\\begin{document} x\n```',b'```tex\n\\input{other}\n```',b'```tex\n\\usepackage{unsafe}\n```',b'```tex\n\\write{payload}\n```']:
   with self.subTest(raw=raw),self.assertRaises(ValueError):fix.wrap_fragment(raw)
 def test_only_missing_terminal_json_brace_recovered_exactly(self):
  parent=read_json(prep.PARENT/'state.json')
  for call in ('call-073','call-121'):
   t=next(t for t in parent['tasks'] if t.get('call')==call);raw=(prep.PARENT/'calls'/call/'content.txt').read_text();data,proof=fix.saved_review(raw,t['draft_sha256'])
   self.assertEqual(data,json.loads(raw+'}'));self.assertEqual(proof['normalized_sha256'],fix.digest(raw+'}'))
  t=next(t for t in parent['tasks'] if t.get('call')=='call-140')
  with self.assertRaises(ValueError):fix.saved_review((prep.PARENT/'calls/call-140/content.txt').read_text(),t['draft_sha256'])
  with self.assertRaises(ValueError):fix.saved_review('{"base_sha256":"x","findings":[{"old":"unterminated', 'x')
 def test_all_curated_actual_shapes_pass_and_parent_records_unchanged(self):
  baseline=read_json(prep.DEV/'baseline.json');self.assertEqual(sha(prep.PARENT/'state.json'),baseline['parent_state_sha256'])
  for item in read_json(prep.DEV/'curations.json'):
   folder=prep.DEV/'curated'/item['unit'];unit=read_json(folder/'unit.json');text=(folder/'document.tex').read_text()
   self.assertEqual(sha(folder/'document.tex'),item['sha256']);self.assertTrue(c.content_check(prep.PARENT,{'source_units':{item['unit']:unit}},{'key':item['unit']},text)['usable'],item['unit'])
 def test_theorem_condition_reference_detail_caption_and_row_deletion_block(self):
  cases=[('original-af03317e4e74c832-unit-003','constant coefficients'),('master-580e3657a0208530-unit-002','Brunskill'),('master-de3d6a9223dd0bd5-unit-003','-0.1359'),('master-252f9d083f4203a2-unit-001','Fitting the leverage function')]
  for key,anchor in cases:
   folder=prep.DEV/'curated'/key;unit=read_json(folder/'unit.json');text=(folder/'document.tex').read_text();self.assertIn(anchor,text)
   result=c.unit_coverage(text.replace(anchor,'',1),unit)
   self.assertEqual(result['coverage_status'],'omission_risk');self.assertTrue(result['invalid_adjudications'])
 def test_source_mutation_cannot_preserve_adjudication(self):
  key='original-af03317e4e74c832-unit-003';folder=prep.DEV/'curated'/key;u=read_json(folder/'unit.json');record=u['content_adjudications'][-1];block=next(b for b in u['native_blocks'] if b['id'] in record['source_blocks']);block['tex']+=' changed condition'
  self.assertEqual(c.unit_coverage((folder/'document.tex').read_text(),u)['coverage_status'],'omission_risk')
 def test_kienitz_six_figures_once_and_caption_seam_owned_once(self):
  sid=prep.KIENITZ;units={};documents=[]
  for i in (1,2):
   key=sid+f'-unit-{i:03}';folder=prep.DEV/'curated'/key;units[key]=read_json(folder/'unit.json');documents.append((folder/'document.tex').read_text())
  full='\n'.join(documents);self.assertEqual(full.count(r'\begin{figure}'),6);self.assertEqual(full.count(r'\caption{'),6)
  group=read_json(prep.DEV/'figure-ownership.json')
  for g in group['groups']:
   self.assertEqual(full.count('{'+g['canonical']+'}'),1)
   for ref in g['members']:self.assertNotIn('{'+ref+'}',full)
  self.assertEqual(documents[0].count('\\caption{Fitting the leverage function'),1);self.assertNotIn('\\caption{Fitting the leverage function',documents[1])
  for row in group['transfers']:
   self.assertTrue(set(row['blocks'])<=set(units[row['to']]['blocks']));self.assertFalse(set(row['blocks'])&set(units[row['from']]['blocks']))
 def test_figure_labels_and_cross_unit_references_are_preserved(self):
  old=read_json(prep.PARENT/'state.json');sid=prep.KIENITZ;before=[];after=[]
  for key in old['documents'][sid]['units']:
   before.append(prep.selected(old,key)[0]);after.append((prep.DEV/'curated'/key/'document.tex').read_text())
  labels=re.findall(r'\\label\{([^{}]+)\}','\n'.join(before));check=fix.reference_check(after,labels)
  self.assertFalse(check['missing_required_labels']);self.assertFalse(check['undefined_references']);self.assertFalse(check['duplicate_labels'])
  broken=[x.replace(r'\label{fig:simulation}','') for x in after]
  self.assertIn('fig:simulation',fix.reference_check(broken,labels)['undefined_references'])
 def test_drained_continuation_preserves_sealed_calls_and_same_allowance(self):
  child=Path(read_json(prep.ROOT/'results/library-completion-current.json')['run']);plan=read_json(child/'plan.json');state=read_json(child/'state.json');parent_path=Path(plan['parent_run']);parent=read_json(parent_path/'state.json')
  self.assertEqual(state['inherited_call_count'],2);self.assertEqual(state['calls'][:state['inherited_call_count']],parent['calls']);self.assertEqual(sha(child/'task-plan.json'),sha(parent_path/'task-plan.json'));self.assertEqual(plan['lineage']['repair_remaining_local_requests'],11)
  from probe.experiment import verify_seal
  for call in state['calls']:verify_seal(child/'calls'/call['id'],call['seal'])
  self.assertEqual(plan['paid_approval'],read_json(parent_path/'plan.json')['paid_approval']);self.assertEqual(plan['lineage']['new_allocation_usd'],'0')
 def test_table_rows_are_exact_and_deleting_one_does_not_pass(self):
  key='master-de3d6a9223dd0bd5-unit-003';folder=prep.DEV/'curated'/key;u=read_json(folder/'unit.json');text=(folder/'document.tex').read_text()
  source=[x for b in u['native_blocks'] if b['kind']=='table' for x in prep.numeric_source_rows(b['tex'])];output=[x for t in prep.environment_spans(text,'tabular') for x in prep.numeric_tex_rows(t)]
  self.assertEqual(len(source),47);self.assertEqual(source,output)
  changed=re.sub(r'(?m)^GS &.*\n','',text,count=1);self.assertEqual(c.unit_coverage(changed,u)['coverage_status'],'omission_risk')
 def test_noncommuting_lyapunov_counterexample_is_exact(self):
  k=[[F(1),F(1)],[F(0),F(2)]];x=[[F(1,2),-F(1,6)],[-F(1,6),F(1,3)]]
  mul=lambda a,b:[[sum(a[i][m]*b[m][j] for m in range(2)) for j in range(2)] for i in range(2)]
  kt=list(map(list,zip(*k)));a=mul(x,k);b=mul(kt,x);good=[[a[i][j]+b[i][j] for j in range(2)] for i in range(2)];self.assertEqual(good,[[1,0],[0,1]])
  a=mul(k,x);bad=[[a[i][j]+b[i][j] for j in range(2)] for i in range(2)];self.assertEqual(bad,[[F(5,6),0],[-F(1,6),F(7,6)]])
 def test_actual_child_has_finite_missing_only_tasks_and_exact_parent_scopes(self):
  child=Path(read_json(prep.ROOT/'results/library-completion-current.json')['run']);plan=read_json(child/'plan.json');state=read_json(child/'state.json');parent=read_json(prep.PARENT/'state.json');oldplan=read_json(prep.PARENT/'plan.json')
  self.assertEqual(plan['paid_approval'],oldplan['paid_approval']);self.assertEqual(plan['lineage']['new_allocation_usd'],'0');self.assertEqual(plan['workloads']['mineru_pro'],[]);self.assertTrue(state['extraction_done']);self.assertEqual(len(state['tasks']),13)
  converts=[t for t in state['tasks'] if t['phase']=='convert'];self.assertEqual(len(converts),2);self.assertTrue(all('-completion-001' in t['key'] for t in converts))
  self.assertEqual(len([t for t in state['tasks'] if t['phase']=='critic']),11);self.assertEqual(len(state['historical_calls']),256)
  for t in converts:
   u=state['source_units'][t['key']];self.assertEqual(len(u['physical_pages']),5);self.assertEqual(u['text_sha256'],fix.digest(u['text']));self.assertEqual(u['source_bound_exception']['source_text_sha256'],u['text_sha256'])
  for sid,d in state['documents'].items():
   expected=[b for k in parent['documents'][sid]['units'] for b in parent['source_units'][k]['blocks']]
   for gap in parent['documents'][sid].get('outstanding_scopes',[]):expected+=gap['blocks']
   check=fix.verify_ownership({k:state['source_units'][k] for k in d['units']},expected);self.assertTrue(check['unique'])
 def test_shared_allocation_and_consumed_phase_identity_survive_child(self):
  p=read_json(prep.PARENT/'plan.json');a=p['paid_approval'];before=read_json(prep.DEV/'baseline.json')
  for name,digest in before['allocation_files'].items():self.assertEqual(sha(Path(a['cloud_run'])/name),digest)
  # Explicit paths/draft versions cannot turn an existing phase into a new budget.
  unit={'source_sha256':'a'*64,'owned_blocks':['b1','b2'],'draft_path':'/parent/a.tex','draft_sha256':'b'*64}
  record={'kind':'kimi','phase':'critic','unit':unit,'scope_sha256':'old'};first=paid.reservation_identity(record,a)
  record['scope_sha256']='new';record['unit']=dict(unit,draft_path='/child/a.tex',draft_sha256='c'*64)
  self.assertEqual(first,paid.reservation_identity(record,a))

class RealController(unittest.TestCase):
 def test_wrapped_fragment_real_finish_exact_draft_critic_pause_resume(self):
  import test_library_pipeline as fixtures
  h=fixtures.Pipeline();h.setUp()
  try:
   p=read_json(h.run/'plan.json');p['accept_exact_fragments']=True;atomic_json(h.run/'plan.json',p);b=read_json(h.run/'binding.json');b.update(plan_sha256=sha(h.run/'plan.json'),code=c.base.code_binding());atomic_json(h.run/'binding.json',b)
   body=fixtures.DOC.split(r'\begin{document}',1)[1].split(r'\end{document}',1)[0];raw='```latex\n'+body+'\n```\nAccuracy: preserved source.';wrapped,_=fix.wrap_fragment(raw);h.pause=True
   def transport(run,call,request,**kw):
    if call['parent'].endswith('/critic'):
     payload=c.vision.request_payload(request);self.assertEqual(payload['draft'],wrapped.decode());self.assertEqual(payload['base_sha256'],fix.digest(wrapped));answer=json.dumps({'base_sha256':payload['base_sha256'],'scope_review':{'full_assigned_scope_reviewed':True,'additional_findings_remain':False,'unreviewed_scope':''},'findings':[]})
    else:answer=raw
    h.seen.append(call['parent']);call.update(status='completed_response',elapsed_seconds=.01,metadata={'actual_model':'glm53-regular','finish_reason':'stop','usage':{'prompt_tokens':777,'completion_tokens':10}});folder=run/'calls'/call['id'];folder.mkdir(parents=True);atomic_json(folder/'request.json',request);atomic_json(folder/'attempts/one/request.json',{'body':request});atomic_json(folder/'outcome.json',call);(folder/'content.txt').write_text(answer);atomic_json(folder/'manifest.json',files_manifest(folder));call['seal']=sha(folder/'manifest.json')
    if h.pause:atomic_json(run/'pause.json',{'test':True})
    return answer,call
   h.transport=transport
   with self.assertRaises(c.runtime.StopRun):h.coordinate()
   self.assertEqual(len(h.seen),1);h.pause=False;(h.run/'pause.json').unlink();h.coordinate();self.assertEqual(len(h.seen),2);h.coordinate();self.assertEqual(len(h.seen),2)
   self.assertTrue((h.run/'call-results/call-001/fragment-provenance.json').exists());self.assertEqual((h.run/'calls/call-001/content.txt').read_text(),raw)
  finally:h.doCleanups()

if __name__=='__main__':unittest.main()
