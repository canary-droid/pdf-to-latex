import copy,json,tempfile,unittest,base64
from pathlib import Path
from fractions import Fraction
from probe import cookbook_quantities as q,chapter_glm
from probe.common import sha
from scripts import cookbook_quantity_trial as runner
from unittest.mock import patch
class QuantityProtocol(unittest.TestCase):
 def setUp(self):
  self.s={'id':'p001','physical_page':1,'printed_page':'i','recipes':[7],'context_policy':'Only recipe7','regions':[{'id':'r1','recipe':7,'quantities':[{'id':'q1','value':'SECRET_ANSWER'}]}],'images':[],'draft':{'path':'draft.md','sha256':'abc'}}
 def answer(self,arm='C'):
  return {'protocol':q.PROTOCOL,'draft_sha256':'abc' if arm=='A' else None,'coverage_complete':True,'quantities':[{'id':'q1','value':'1/2','unit':'oz','association':'salt','status':'read','draft_value':'1/4' if arm=='A' else None,'verdict':'correction' if arm=='A' else 'not_applicable'}],'additional_quantities':[],'unresolved':[]}
 def test_reference_cannot_leak_via_public_scope(self):
  self.assertNotIn('SECRET_ANSWER',json.dumps(q.public_scope(self.s)))
 def test_missing_duplicate_extra_and_uncertain(self):
  d=self.answer();self.assertTrue(q.validate_answer(json.dumps(d),self.s,'C')[1]['complete'])
  for rows in [[],d['quantities']*2,[dict(d['quantities'][0],id='other')]]:
   bad=dict(d,quantities=rows);self.assertFalse(q.validate_answer(json.dumps(bad),self.s,'C')[1]['complete'])
  d['quantities'][0]['status']='uncertain';self.assertEqual(q.validate_answer(json.dumps(d),self.s,'C')[1]['uncertain'],1)
 def test_wrong_draft_or_operation_rejected(self):
  with self.assertRaises(ValueError):q.validate_answer(json.dumps(self.answer()),self.s,'A')
  with self.assertRaises(ValueError):q.validate_answer(json.dumps(self.answer('A')),self.s,'C')
 def test_equal_fractions_not_wrong_values(self):
  for s in ['⅔','2/3',r'$\frac{2}{3}$']:self.assertEqual(q.number(s),Fraction(2,3))
  self.assertNotEqual(q.number('⅔'),q.number('¾'));self.assertEqual(q.number('1¾'),Fraction(7,4))
  self.assertIsNone(q.number('uncertain'))
 def test_images_and_draft_checked_and_no_draft_in_extraction(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'draft.md').write_text('private baseline');self.s['draft']['sha256']=sha(root/'draft.md')
   with patch.object(q,'image_parts',return_value=[{'type':'image_url','image_url':{'url':'data:image/png;base64,ABC'}}]) as images:
    self.s['images']=[{}];a=q.request(self.s,'A',root);b=q.request(self.s,'B',root);c=q.request(self.s,'C',root)
    self.assertEqual(a['messages'],b['messages']);self.assertIn('private baseline',json.dumps(a));self.assertNotIn('private baseline',json.dumps(c));self.assertNotIn('SECRET_ANSWER',json.dumps(a));self.assertTrue(images.called)
    (root/'draft.md').write_text('changed')
    with self.assertRaises(ValueError):q.request(self.s,'A',root)
 def test_reservation_cannot_repeat_after_restart(self):
  s={'chapter_contract':'annotated-chapter-v1','execution_limits':{'calls':24,'attempts_per_unit':1},'timing_policy':'manual_only','first_dispatch':None,'calls':[]}
  chapter_glm.reserve(s,'A-p001','sha')
  s=json.loads(json.dumps(s))
  with self.assertRaises(chapter_glm.StopRun):chapter_glm.reserve(s,'A-p001','sha')
 def test_uncertain_resume_retains_consumption(self):
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);s={'status':'running','tasks':[{'id':'A-p001','status':'in_progress'}],'calls':[{'id':'call-001','parent':'A-p001','status':'in_progress'}]}
   runner.reconcile(run,s);self.assertEqual(len(s['calls']),1);self.assertEqual(s['calls'][0]['status'],'interrupted_uncertain')
 def test_finished_worker_never_dispatches(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(runner,'verify',return_value=({}, {'status':'finished','calls':[],'tasks':[]})),patch.object(runner,'run_model') as dispatch,patch.object(runner,'writer_lock'):
   runner.worker(Path(tmp));dispatch.assert_not_called()

class Settlement(unittest.TestCase):
 def test_real_reservation_response_seal_and_finished_reuse(self):
  from probe.common import atomic_json,fingerprint
  with tempfile.TemporaryDirectory() as tmp:
   run=Path(tmp);scope=QuantityProtocol();scope.setUp();unit=scope.s
   body={'model':q.MODELS['glm'][0],'messages':[],'max_tokens':16384,'stream':True}
   task={'id':'A-p001','model':'glm','arm':'A','scope':unit,'request_hash':fingerprint(body)}
   plan={'tasks':[task],'initial_glm_ids':{'0':'head','1':'peer'},'initial_glm_bindings':{'0':'bound','1':'bound'}}
   state={'status':'running','calls':[],'tasks':[{'id':'A-p001','status':'pending'}],'chapter_contract':'annotated-chapter-v1','execution_limits':{'calls':24,'attempts_per_unit':1},'timing_policy':'manual_only','first_dispatch':None}
   atomic_json(run/'requests/A-p001.json',body);atomic_json(run/'cpu-preprocessing.json',{'requests':{'A-p001':{'prompt_tokens':100,'image_rows':50}}})
   response={'model':body['model'],'choices':[{'finish_reason':'stop','message':{'content':json.dumps(scope.answer('A'))}}],'usage':{'prompt_tokens':100,'completion_tokens':10}}
   with patch.object(runner,'inspect',return_value={'State':{'Running':True}}),patch.object(runner,'config_id',return_value='bound'),patch.object(runner,'http',side_effect=lambda port,path,*args:{'data':[{'id':body['model']}]} if path=='/v1/models' else {'busy':False,'requests_running':0}),patch.object(runner,'verify'),patch.object(runner,'memory'),patch.object(runner.LocalClient,'_request',return_value=(response,{})) as transport:
    runner.run_model(run,plan,state,'glm');self.assertEqual(state['tasks'][0]['status'],'completed');self.assertTrue((run/'calls/call-001/seal.json').exists());runner.run_model(run,plan,state,'glm');self.assertEqual(transport.call_count,1)
 def test_runtime_identity_rejected_before_paid_or_local_reservation(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(runner,'inspect',return_value={'State':{'Running':True}}),patch.object(runner,'config_id',return_value='changed'):
   plan={'initial_glm_ids':{'0':'x'},'initial_glm_bindings':{'0':'expected'}};s={'calls':[]}
   with self.assertRaisesRegex(RuntimeError,'identity'):runner.run_model(Path(tmp),plan,s,'glm')
   self.assertEqual(s['calls'],[])

class RuntimeBinding(unittest.TestCase):
 def test_docker_mount_order_is_not_identity_but_values_are(self):
  a={'Image':'same','Config':{'Cmd':['serve']},'HostConfig':{},'Mounts':[{'Destination':'/model','Source':'/weights','RW':False},{'Destination':'/cache','Source':'/cache','RW':True}]}
  b=copy.deepcopy(a);b['Mounts'].reverse();self.assertEqual(runner.config_id(a),runner.config_id(b))
  b['Mounts'][0]['RW']=False;self.assertNotEqual(runner.config_id(a),runner.config_id(b))


class InstalledResponseShapes(unittest.TestCase):
 def test_single_outer_json_fence_and_bad_extra_content(self):
  fixture=QuantityProtocol();fixture.setUp();text=json.dumps(fixture.answer('A'));wrapped='```json\n'+text+'\n```'
  self.assertTrue(q.validate_answer(wrapped,fixture.s,'A')[1]['complete'])
  for bad in [wrapped+'\n'+wrapped,'intro\n'+wrapped,wrapped[:-3]]:
   with self.assertRaises(ValueError):q.validate_answer(bad,fixture.s,'A')
 def test_actual_native_accounting_without_usage(self):
  root=Path(__file__).resolve().parents[1]/'fixtures/markdown/quantity-comparison'
  r=json.loads((root/'deepseek-response-metadata.json').read_text());u=q.reported_usage(r)
  self.assertEqual(u['prompt_tokens'],3735);self.assertEqual(u['completion_tokens'],12451)
  self.assertNotIn('completion_tokens_details',u)
  for bad in [{'usage':{'prompt_tokens':1},'tensorfold':{'prompt':2}}, {'tensorfold':{'prompt':True}}]:
   with self.assertRaises(ValueError):q.reported_usage(bad)
 def test_saved_fenced_glm_answer_exact_draft_and_coverage(self):
  root=Path(__file__).resolve().parents[1]/'fixtures/markdown/quantity-comparison';scope=json.loads((root/'scope.json').read_text());answer=(root/'glm-answer.txt').read_text()
  parsed,cov=q.validate_answer(answer,scope,'A');self.assertTrue(cov['complete']);self.assertEqual(len(parsed['quantities']),24)
  with self.assertRaises(ValueError):q.validate_answer(answer,dict(scope,draft={'sha256':'stale'}),'A')
