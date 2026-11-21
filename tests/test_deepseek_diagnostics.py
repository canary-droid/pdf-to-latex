import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from decimal import Decimal
from probe import deepseek_diagnostics as d,cookbook_quantities as q,cloud_critic as cloud,chapter_glm
from probe.common import atomic_json,sha,fingerprint
from scripts import deepseek_diagnostics as runner
class Diagnostics(unittest.TestCase):
 def test_frozen_matrix_allowance_reuse_and_seeds(self):
  m=d.matrix();self.assertEqual(len(m),45);self.assertEqual(sum(x['backend']=='local' for x in m),27);self.assertEqual(sum(x['backend']=='hosted' for x in m),18)
  self.assertEqual(m[0]['id'],'L-B-p039-t0-r1');self.assertIsNone(m[0]['seed'])
  primary=[x for x in m if x['temperature']==1 and x['rep']==1];self.assertEqual(len(primary),24)
  for b in d.DIAGNOSTICS:
   self.assertEqual(len([x for x in m if x['base']==b]),9)
 def test_first_allowance_only_and_hosted_envelope(self):
  b={'model':'DeepSeek-V4.1-Flash-TF','messages':[{'role':'user','content':[{'type':'image_url','image_url':{'url':'data:image/png;base64,TEST'}}]}],'max_tokens':16384,'reasoning_effort':'high','temperature':0,'top_p':1,'stream':True}
  cfg={'provider':{'only':[d.TAG],'allow_fallbacks':False,'require_parameters':True,'data_collection':'deny','zdr':True}}
  first=d.adapted_body(b,d.matrix()[0],cfg);self.assertEqual({k for k in first if first[k]!=b[k]},{'max_tokens'})
  hosted=d.adapted_body(b,next(x for x in d.matrix() if x['backend']=='hosted'),cfg);d.validate_body(hosted,cfg);self.assertEqual(hosted['messages'],b['messages'])
  for field,value in [('model','other'),('top_p',.9),('provider',{}),('max_tokens',131072)]:
   wrong=copy.deepcopy(hosted);wrong[field]=value
   with self.assertRaises(Exception):d.validate_body(wrong,cfg)
 def test_route_identity_support_and_zdr(self):
  e={'tag':d.TAG,'model_id':d.MODEL,'provider_name':d.PROVIDER,'quantization':'fp8','status':0,'max_completion_tokens':393216,'context_length':1048576,'supported_parameters':['max_tokens','temperature','top_p','top_k','min_p','seed','reasoning'],'pricing':{'prompt':'.000000098','completion':'.000000294','input_cache_read':'.00000000294'}}
  m={'endpoints':{'data':{'id':d.MODEL,'endpoints':[e],'architecture':{'input_modalities':['text','image']}}},'zdr':{'data':[dict(e,safety_retention=False)]},'model':{'reasoning':{'supported_efforts':['high']}}};self.assertEqual(d.endpoint(m),e)
  for key,value in [('quantization','bf16'),('status',-5),('supported_parameters',[])]:
   bad=copy.deepcopy(m);bad['endpoints']['data']['endpoints'][0][key]=value
   with self.assertRaises(Exception):d.endpoint(bad)
  m['zdr']['data'][0]['safety_retention']=True
  with self.assertRaises(Exception):d.endpoint(m)
 def setup_ledger(self,p):
  cfg={'budget_usd':'2.30','pilot_budget_usd':'2.30','paid_limits':{'trial_calls':21,'readiness_calls':0},'context_length':1048576,'rates':{'prompt':'.000000098','completion':'.000000294'}};atomic_json(p/'binding.json',{'config':cfg});return d.ledger(p,True)
 def test_reserve_disconnect_restart_duplicate_and_live_denial(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);ledger=self.setup_ledger(p);body={'max_tokens':32768};amount=d.cost_bound(read_json(p/'binding.json')['config'],body)
   self.assertGreater(amount,Decimal('.10'))
   with self.assertRaises(cloud.AdmissionError):ledger.reserve(body,p/'calls/one',Decimal('0'),'trial')
   ledger.reserve(body,p/'calls/one',Decimal('2'),'trial');again=d.ledger(p)
   self.assertEqual(again.summary()['unresolved_reserved_usd'],str(amount))
   with self.assertRaises(cloud.AdmissionError):again.reserve(body,p/'calls/one',Decimal('2'),'trial')
   again.settle('0001',{'id':'abc','usage':{'cost':.002,'prompt_tokens':1000,'completion_tokens':1000}},'test');self.assertEqual(again.summary()['actual_reported_usd'],'0.002')
 def test_secret_redaction_and_uncertain_post_guard(self):
  c=object.__new__(d.HostedClient);c._key='private-test-key'
  self.assertNotIn(c._key,c._redact('problem '+c._key))
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);atomic_json(p/'transport-phase.json',{'post_started':True})
   with patch.object(c,'_http') as transport,self.assertRaises(cloud.AdmissionError):c.dispatch({}, {}, p)
   transport.assert_not_called()
 def test_saved_empty_length_and_exact_draft(self):
  root=Path(__file__).resolve().parents[1];parent=root/'runs/cookbook-quantity-comparison-20261116T142504Z-36e24a'
  if not parent.exists():self.skipTest('Saved run not installed')
  plan=json.loads((parent/'plan.json').read_text());t=next(x for x in plan['tasks'] if x['id']=='B-p039')
  with tempfile.TemporaryDirectory() as tmp:
   out=runner.settle_response(Path(tmp),{'choices':[{'finish_reason':'length','message':{'content':''}}],'tensorfold':{'completion':16384,'prompt':1}},t);self.assertEqual(out['status'],'invalid_completion')
 def test_real_reservation_boundary_and_restart_no_replay(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);s={'status':'running','tasks':[{'id':'a','status':'pending'}],'calls':[],'chapter_contract':'annotated-chapter-v1','execution_limits':{'calls':45,'attempts_per_unit':1},'timing_policy':'manual_only','first_dispatch':None,'production_stage':{'task_ids':['a']}}
   c=chapter_glm.reserve(s,'a','hash');runner.save(p,s);runner.reconcile(p,s);self.assertEqual(c['status'],'interrupted_uncertain')
   with self.assertRaises(Exception):chapter_glm.reserve(s,'a','hash')
 def test_finished_resume_zero_requests(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(runner,'verify',return_value=({}, {'status':'finished'})),patch.object(runner.runtime,'cmd') as command,patch('sys.argv',['x','resume','--run',tmp]):runner.main();command.assert_not_called()
 def test_images_wrong_draft_and_coverage_reuse(self):
  from tests.test_cookbook_quantities import QuantityProtocol
  f=QuantityProtocol();f.setUp();s=f.s;a=f.answer('A');a['draft_sha256']='wrong'
  with self.assertRaises(ValueError):q.validate_answer(json.dumps(a),s,'B')
  a=f.answer('A');a['quantities']=[];self.assertFalse(q.validate_answer(json.dumps(a),s,'B')[1]['complete'])
from probe.common import read_json
