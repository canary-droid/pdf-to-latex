"""Finite saved-scope diagnostics. Reuses the existing cloud transport and ledger."""
import copy,json,time,urllib.request
from decimal import Decimal,ROUND_CEILING
from pathlib import Path
from . import cloud_critic as cloud,cookbook_quantities as q,kimi_escalation as kimi
from .common import atomic_json,read_json,sha,fingerprint
from .batch_review import IdentityError,IntegrityError
MODEL='deepseek/deepseek-v4.1-flash-1017';TAG='deepinfra/fp8';PROVIDER='DeepInfra';TOKENS=32768
DIAGNOSTICS=('B-p039','D-p035','D-p038')
SEEDS={1:None,2:2026111602,3:2026111603}

def matrix():
 rows=[]
 for base in DIAGNOSTICS:
  for temperature in (0,1):
   for rep in (1,2,3):rows.append(dict(id=f'L-{base}-t{temperature}-r{rep}',base=base,backend='local',temperature=temperature,rep=rep,seed=SEEDS[rep]))
 for arm in ('B','D'):
  for page in (31,32,35,38,39,401):
   base=f'{arm}-p{page:03d}'
   if base not in DIAGNOSTICS:rows.append(dict(id=f'L-{base}-t1-r1',base=base,backend='local',temperature=1,rep=1,seed=None))
 for arm in ('B','D'):
  for page in (31,32,35,38,39,401):
   base=f'{arm}-p{page:03d}'
   for rep in ((1,2,3) if base in DIAGNOSTICS else (1,)):
    rows.append(dict(id=f'H-{base}-t1-r{rep}',base=base,backend='hosted',temperature=1,rep=rep,seed=SEEDS[rep]))
 assert len(rows)==45 and len({r['id'] for r in rows})==45
 return rows

def endpoint(metadata):
 data=metadata['endpoints']['data'];e=next((x for x in data['endpoints'] if x.get('tag')==TAG),None)
 if data['id']!=MODEL or not e or e.get('model_id')!=MODEL or e.get('provider_name')!=PROVIDER or e.get('quantization')!='fp8' or e.get('status')!=0:raise IdentityError('Pinned FP8 endpoint unavailable/changed')
 if not {'max_tokens','temperature','top_p','top_k','min_p','seed','reasoning'}<=set(e['supported_parameters']):raise cloud.AdmissionError('Pinned route parameters unsupported')
 if e['max_completion_tokens']<TOKENS or e['context_length']<TOKENS+8192:raise cloud.AdmissionError('Route capacity insufficient')
 if 'image' not in data['architecture']['input_modalities'] or 'high' not in metadata['model']['reasoning']['supported_efforts']:raise cloud.AdmissionError('Vision/High not publicly verified')
 z=[x for x in metadata['zdr']['data'] if x.get('model_id')==MODEL and x.get('tag')==TAG]
 if len(z)!=1 or z[0].get('safety_retention') is not False:raise cloud.AdmissionError('Exact route ZDR/no safety retention unqualified')
 for k,v in e['pricing'].items():
  if k not in ('prompt','completion','input_cache_read','discount') and cloud.decimal(v)!=0:raise cloud.AdmissionError('Unknown cost component')
 return e

def adapted_body(original,task,config):
 b=copy.deepcopy(original);b.update(max_tokens=TOKENS,temperature=task['temperature'],top_p=1,reasoning_effort='high')
 if task['seed'] is not None:b['seed']=task['seed']
 if task['backend']=='hosted':
  b.pop('reasoning_effort');b.update(model=MODEL,reasoning={'effort':'high','exclude':False},provider=copy.deepcopy(config['provider']),stream=False,plugins=[],top_k=20,min_p=0)
 return b

def input_bound(config,body):
 # No exact route-specific image tokenizer is published: reserve the accepted input window.
 return config['context_length']-body['max_tokens']
def cost_bound(config,body):
 return (cloud.decimal(config['rates']['prompt'])*input_bound(config,body)+cloud.decimal(config['rates']['completion'])*body['max_tokens']).quantize(Decimal('.000000001'),rounding=ROUND_CEILING)
def ledger(run,create=False):
 c=read_json(Path(run)/'binding.json')['config']
 return cloud.Ledger(run,create=create,cost_estimator=lambda b:cost_bound(c,b),token_estimator=lambda b:input_bound(c,b),rates=c['rates'])
def validate_body(body,config):
 if body.get('model')!=MODEL or body.get('provider')!=config['provider'] or body.get('reasoning')!={'effort':'high','exclude':False} or body.get('max_tokens')!=TOKENS or body.get('temperature')!=1 or body.get('top_p')!=1 or body.get('top_k')!=20 or body.get('min_p')!=0 or body.get('stream') is not False or body.get('plugins')!=[]:raise IntegrityError('Hosted request differs from frozen settings')
 if not kimi.has_images(body) or len(body['messages'])!=1 or body.get('tools'):raise IntegrityError('Missing images or unexpected conversation/tools')

def public_metadata(folder):
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);result={}
 for key,path in [('endpoints','/models/'+MODEL+'/endpoints'),('zdr','/endpoints/zdr'),('models','/models')]:
  url='https://openrouter.ai/api/v1'+path
  with urllib.request.urlopen(url,timeout=30) as r:raw=r.read(16*1024*1024+1)
  if len(raw)>16*1024*1024:raise cloud.AdmissionError('Metadata too large')
  (folder/(key+'.raw')).write_bytes(raw);result[key]=json.loads(raw)
 result['model']=next(m for m in result.pop('models')['data'] if m['id']==MODEL)
 result['checked_epoch']=time.time();endpoint(result);atomic_json(folder/'metadata.json',result);return result

class HostedClient(cloud.CloudClient):
 def __init__(self,run,key_reader=None):
  self.run=Path(run);b=read_json(self.run/'binding.json');self.config=b['config'];a=read_json(self.run/'authorisation.json')
  if a.get('binding_sha256')!=sha(self.run/'binding.json') or a.get('maximum_primary')!=45 or a.get('budget_usd')!=self.config['budget_usd']:raise IntegrityError('Frozen authorization mismatch')
  self.timeout=30;self._key=(key_reader or cloud.read_key)(cloud.KEY_FILE);self.ledger=ledger(run)
 def _control_paths(self):return ('/models/'+MODEL+'/endpoints','/key')
 def admission(self,body,folder):
  validate_body(body,self.config);m=public_metadata(folder/'public');e=endpoint(m)
  if e['context_length']!=self.config['context_length'] or any(cloud.decimal(e['pricing'][k])>cloud.decimal(v) for k,v in self.config['rates'].items()):raise cloud.AdmissionError('Route limits/prices changed')
  k=self.control('/key',None,private=True).get('data',{});remaining=cloud.decimal(k.get('limit_remaining'))
  # The live key limit is observed, never changed or interpreted as a fresh allocation.
  history=kimi.history_snapshot(self.run.parents[1],exclude=(self.run,));unknown=cloud.decimal(history['summary']['unresolved_reserved_usd'])
  effective=max(Decimal(0),remaining-unknown)
  record={'at_epoch':time.time(),'live_remaining_usd':str(remaining),'live_limit_usd':k.get('limit'),'live_limit_reset':k.get('limit_reset'),'prior_unsettled_reserved_usd':str(unknown),'history_summary':history['summary'],'effective_before_own_pending_usd':str(effective),'reservation_usd':str(cost_bound(self.config,body))}
  atomic_json(folder/'admission.json',record);atomic_json(folder/'history-snapshot.json',history)
  self.ledger.admit(body,effective);return effective
 def dispatch(self,task,body,folder):
  folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
  if (folder/'transport-phase.json').exists() and read_json(folder/'transport-phase.json').get('post_started'):raise cloud.AdmissionError('Prior POST uncertain/consumed; never replay')
  atomic_json(folder/'transport-phase.json',{'post_started':False,'phase':'preflight'})
  remaining=self.admission(body,folder);identity=self.ledger.reserve(body,folder,remaining,'trial')
  atomic_json(folder/'request.json',body);atomic_json(folder/'transport-phase.json',{'post_started':True,'phase':'post_started_or_uncertain','reservation':identity})
  try:
   status,raw,elapsed=self._http('POST','/chat/completions',body);(folder/'response.raw').write_bytes(self._redact(raw));data=json.loads(raw);self.ledger.settle(identity,data,str(folder/'response.raw'))
   if status!=200:raise cloud.AdmissionError('OpenRouter HTTP '+str(status)+'; response preserved, no retry')
   if data.get('model')!=MODEL or data.get('provider')!=PROVIDER:raise IdentityError('Hosted model/provider mismatch')
   if self.ledger.read().get('halt'):raise IntegrityError(self.ledger.read()['halt'])
   if data.get('choices',[{}])[0].get('message',{}).get('tool_calls'):raise IdentityError('Unexpected hosted tool call')
   return data,{'latency_seconds':elapsed,'provider_tag':TAG,'provider_attestation':'Family returned; exact route pinned in request','cloud_reservation':identity}
  except Exception as e:
   atomic_json(folder/'error.json',{'type':type(e).__name__,'reason':self._redact(str(e)),'reservation':identity,'retry':False});raise
 def reconcile(self):
  for x in self.ledger.read()['reservations']:
   if 'actual_cost_usd' in x or not x.get('generation_id'):continue
   d=self.control('/generation?id='+x['generation_id'],self.run/'billing'/x['id']/'lookup')['data']
   if d.get('id')!=x['generation_id'] or d.get('model')!=MODEL or d.get('provider_name')!=PROVIDER:raise IdentityError('Cost lookup identity mismatch')
   self.ledger.settle(x['id'],{'id':d['id'],'usage':{'cost':d.get('total_cost'),'prompt_tokens':d.get('native_tokens_prompt'),'completion_tokens':d.get('native_tokens_completion'),'completion_tokens_details':{'reasoning_tokens':d.get('native_tokens_reasoning')}}},'generation GET')
  return self.ledger.summary()
