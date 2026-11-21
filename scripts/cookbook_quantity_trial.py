#!/usr/bin/env python3
"""One finite saved-input experiment, using existing streaming/reservation/seal helpers."""
import argparse,copy,json,os,sys,subprocess,shlex,time,urllib.request,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import atomic_json,read_json,sha,fingerprint,writer_lock,files_manifest
from probe.experiment import InputGuard,verify_seal,now
from probe.batch_review import seal_outcome
from probe import chapter_glm, cookbook_quantities as q
from probe.local_model import LocalClient
PEER='mdi@192.168.100.2'

def cmd(args,rank=0):
 p=subprocess.run(args if rank==0 else ['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',PEER,shlex.join(args)],capture_output=True,text=True)
 if p.returncode:raise RuntimeError('Command failed: '+shlex.join(args)+' '+p.stderr[-800:])
 return p.stdout

def inspect(name,rank=0):return json.loads(cmd(['docker','inspect',name],rank))[0]
def config_id(d):return fingerprint({'Image':d['Image'],'Config':d['Config'],'HostConfig':d['HostConfig'],'Mounts':sorted(d['Mounts'],key=lambda m:m['Destination'])})
def http(port,path,body=None):
 raw=None if body is None else json.dumps(body,ensure_ascii=False).encode()
 req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=raw,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read(8*1024*1024))

def resources():
 code="import json,pathlib;d={l.split(':')[0]:int(l.split()[1])*1024 for l in pathlib.Path('/proc/meminfo').read_text().splitlines() if ':' in l};print(json.dumps({k:d[k] for k in ['MemAvailable','SwapTotal','SwapFree']}))"
 result={}
 for rank in (0,1):
  m=json.loads(cmd(['python3','-c',code],rank));m['gpu']=cmd(['nvidia-smi','--query-gpu=temperature.gpu,utilization.gpu','--format=csv,noheader'],rank).strip();result[str(rank)]=m
 return result

def memory(run,label,floor):
 r=resources();atomic_json(run/'resources'/(label+'.json'),dict(at=now(),nodes=r))
 if any(v['MemAvailable']<floor*2**30 for v in r.values()):raise RuntimeError(f'Unchanged memory gate {floor}GiB failed: '+str({k:round(v['MemAvailable']/2**30,2) for k,v in r.items()}))
 return r

def code_binding():return {str(p.relative_to(ROOT)):sha(p) for d in ['probe','scripts'] for p in sorted((ROOT/d).glob('*.py'))}
def save(run,s):
 atomic_json(run/'state.json',s)
 atomic_json(run/'progress.json',{'at':now(),'run':str(run),'status':s['status'],'stage':s.get('stage'),'calls_consumed':len(s['calls']),'maximum':24,'tasks':s['tasks'],'diagnostic':s.get('diagnostic'),'service':s.get('service'),'worker':s.get('worker')})

def verify(run):
 b=read_json(run/'binding.json');p=read_json(run/'plan.json');s=read_json(run/'state.json')
 if sha(run/'plan.json')!=b['plan_sha256'] or code_binding()!=b['code']:raise RuntimeError('Plan/code binding changed')
 InputGuard(b['files']).check()
 if [x['id'] for x in p['tasks']]!=[x['id'] for x in s['tasks']]:raise RuntimeError('Task graph changed')
 if len(s['calls'])>24 or len({c['parent'] for c in s['calls']})!=len(s['calls']):raise RuntimeError('Finite allowance/replay violation')
 for c in s['calls']:
  if c.get('seal_sha256'):verify_seal(run/'calls'/c['id'],c['seal_sha256'],'seal.json')
 return p,s

def freeze(run,sample):
 if (run/'binding.json').exists():return verify(run)
 p=read_json(run/'plan.json');assert len(p['tasks'])==24
 assert p['reference_sha256']==sha(sample/'reference.json')
 files={str(x):sha(x) for d in ['sample'] for x in (sample/d).rglob('*') if x.is_file()}
 files[str(sample/'reference.json')]=sha(sample/'reference.json')
 reference=read_json(sample/'reference.json');files[reference['source']]=reference['source_sha256']
 files.update({str(x):sha(x) for x in (run/'requests').glob('*.json')})
 files[str(run/'cpu-preprocessing.json')]=sha(run/'cpu-preprocessing.json')
 atomic_json(run/'binding.json',{'code':code_binding(),'files':files,'plan_sha256':sha(run/'plan.json')})
 s={'status':'prepared','tasks':[{'id':t['id'],'status':'pending'} for t in p['tasks']],'calls':[],
 'chapter_contract':'annotated-chapter-v1','execution_limits':{'calls':24,'attempts_per_unit':1},
 'timing_policy':'manual_only','first_dispatch':None,'production_stage':{'task_ids':[t['id'] for t in p['tasks']]},'created_at':now()};save(run,s)

def reconcile(run,s):
 for c in s['calls']:
  d=run/'calls'/c['id'];t=next(t for t in s['tasks'] if t['id']==c['parent'])
  if (d/'outcome.json').exists():
   if not (d/'seal.json').exists():atomic_json(d/'seal.json',files_manifest(d))
   c['seal_sha256']=sha(d/'seal.json');verify_seal(d,c['seal_sha256'],'seal.json');o=read_json(d/'outcome.json');c['status']=t['status']=o['status']
  elif c['status']=='in_progress':
   # Uncertain transports remain consumed. Do not replay or guess settlement.
   c['status']=t['status']='interrupted_uncertain';c['reason']='No sealed outcome; reservation consumed; explicit reconciliation required'
 save(run,s)

def run_model(run,p,s,model):
 port=8888 if model=='glm' else 8894
 ids=p['initial_glm_ids'] if model=='glm' else s['deepseek_ids']; bindings=p['initial_glm_bindings'] if model=='glm' else s['deepseek_bindings']
 for rank in (0,1):
  actual=inspect(ids[str(rank)],rank)
  if not actual['State']['Running'] or config_id(actual)!=bindings[str(rank)]:raise RuntimeError('Served runtime identity changed')
 available=http(port,'/v1/models');assert q.MODELS[model][0] in [x['id'] for x in available['data']]
 atomic_json(run/(model+'-discovery.json'),available)
 for task in p['tasks']:
  state=next(x for x in s['tasks'] if x['id']==task['id'])
  if task['model']!=model or state['status']!='pending':continue
  if (run/'PAUSE').exists():s['status']='paused';save(run,s);return
  verify(run);body=read_json(run/'requests'/(task['id']+'.json'))
  if fingerprint(body)!=task['request_hash']:raise RuntimeError('Request identity changed')
  memory(run,task['id']+'-before',5)
  h=http(port,'/health')
  if h.get('requests_running',0) or h.get('busy',False):raise RuntimeError('Service has another active request')
  expected=read_json(run/'cpu-preprocessing.json')['requests'].get(task['id']) if model=='glm' else None
  if model=='deepseek':
   tokenized=http(port,'/tokenize',body);tokens=tokenized['tokens'];expected={'prompt_tokens':tokenized['count'],'image_rows':tokens.count(129264),'mode':'Non-generating installed native image frontend/tokenizer'}
   if expected['image_rows']<=0:raise RuntimeError('DeepSeek image placeholders not expanded')
   atomic_json(run/'image-verification'/(task['id']+'-preflight.json'),expected)
  if expected['prompt_tokens']+body['max_tokens']>1048576:raise RuntimeError('Context budget failed')
  c=chapter_glm.reserve(s,task['id'],fingerprint(body));state.update(status='in_progress',call=c['id']);save(run,s)
  dest=run/'calls'/c['id'];dest.mkdir(parents=True);atomic_json(dest/'reservation.json',c);atomic_json(dest/'request.json',body)
  print(now(),task['id'],c['id'],'reserved',flush=True);start=time.monotonic()
  try:
   client=LocalClient(q.MODELS[model][1],q.MODELS[model][0],api_key='',purpose='simple_chapter',timeout=None,max_tokens=16384,max_response_bytes=32*1024*1024);client.model=q.MODELS[model][0]
   response,evidence=client._request('POST','/chat/completions',body,dest,'quantity-work')
   atomic_json(dest/'response.json',response)
   if response.get('model')!=client.model:raise RuntimeError('Model identity mismatch')
   reported=q.reported_usage(response);observed=reported.get('prompt_tokens');verified=observed==expected['prompt_tokens'] and expected['image_rows']>0
   atomic_json(run/'image-verification'/(task['id']+'.json'),{'passed':verified,'expected':expected,'observed_prompt_tokens':observed,'limitation':'Prepared image rows/token usage verified; no direct GPU feature dump'})
   if not verified:raise RuntimeError('Image processing/identity verification failed')
   choice=response['choices'][0];text=choice['message'].get('content') or '';(dest/'answer.txt').write_text(text)
   if choice.get('finish_reason')!='stop' or not text.strip():
    outcome={'status':'invalid_completion','finish_reason':choice.get('finish_reason'),'reason':'Empty/truncated/abnormal response retained'}
   else:
    try:
     parsed,coverage=q.validate_answer(text,task['scope'],task['arm']);atomic_json(dest/'parsed.json',parsed)
     outcome={'status':'completed' if coverage['complete'] else 'incomplete_coverage','coverage':coverage}
    except (ValueError,KeyError,TypeError) as e:outcome={'status':'invalid_response','reason':str(e)}
   outcome.update(metadata=evidence,usage=reported,server_timings=response.get('tensorfold'),image_processing_verified=True)
  except Exception as e:
   outcome={'status':'failed','reason':str(e),'attempt_dir':str(getattr(e,'attempt_dir',''))}
   if any(x in str(e).lower() for x in ['identity','image processing']):outcome['shared_failure']=True
  outcome['elapsed_seconds']=time.monotonic()-start;seal_outcome(dest,outcome);c.update(status=outcome['status'],seal_sha256=sha(dest/'seal.json'),elapsed_seconds=outcome['elapsed_seconds'],usage=outcome.get('usage'));state.update(status=c['status']);save(run,s)
  print(now(),task['id'],outcome['status'],round(outcome['elapsed_seconds'],1),'seconds',flush=True)
  memory(run,task['id']+'-after',5)
  if outcome.get('shared_failure'):raise RuntimeError(outcome['reason'])

def owned_deepseek():
 spec=importlib.util.spec_from_file_location('owned_deepseek','/home/mdi/Downloads/deepseek-retry-20261022.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.load_original_kit();return m

def startup(run,s,kind,ids):
 began=time.monotonic()
 for rank in (1,0):cmd(['docker','start',ids[str(rank)]],rank)
 while True:
  memory(run,kind+'-loading',4)
  for rank in (0,1):
   if not inspect(ids[str(rank)],rank)['State']['Running']:raise RuntimeError(kind+' exited during loading')
  try:
   d=http(8888 if kind=='glm' else 8894,'/v1/models')
   if q.MODELS[kind][0] not in [x['id'] for x in d['data']]:raise RuntimeError('Wrong served model identity')
   break
  except (OSError,TimeoutError):pass
  print(now(),kind,'loading; no generation deadline',flush=True);time.sleep(15)
 memory(run,kind+'-ready',8);atomic_json(run/(kind+'-startup.json'),{'seconds':time.monotonic()-began,'completed_at':now(),'generating_readiness_calls':0});s['service']=kind;save(run,s)

def stop_owned(ids,bindings):
 for rank in (0,1):
  d=inspect(ids[str(rank)],rank)
  if config_id(d)!=bindings[str(rank)]:raise RuntimeError('Owned container configuration changed')
  if d['State']['Running']:cmd(['docker','stop','--time','90',ids[str(rank)]],rank)

def guard_glm_ownership(run):
 from scripts.editorial_chapters import guard_gpu_workloads
 spec=importlib.util.spec_from_file_location('existing_owned_helpers',ROOT/'scripts/run-bergomi-extraction.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 guard_gpu_workloads(run,module,resident_glm=True)


def switch_to_deepseek(run,p,s):
 guard_glm_ownership(run)
 helper=owned_deepseek();deep={};deepbindings={}
 for rank in (0,1):
  d=helper.inspect(rank);helper.verify_stopped(d,rank);helper.verify_node_files(rank);deep[str(rank)]=d['Id'];deepbindings[str(rank)]=config_id(d)
 h=http(8888,'/health')
 if h.get('requests_running')!=0 or h.get('busy'):raise RuntimeError('GLM is not idle')
 # Fail if another model container or project worker appeared. Existing desktop stays untouched.
 for rank in (0,1):
  names=set(cmd(['docker','ps','--format','{{.Names}}'],rank).splitlines())
  if names-{'glm53-flash-tf','open-webui','open_webui'}:raise RuntimeError('Unrelated deployment is active')
 s['deepseek_ids']=deep;s['deepseek_bindings']=deepbindings;s['service']='handoff';save(run,s)
 stop_owned(p['initial_glm_ids'],p['initial_glm_bindings']);s['glm_stopped_by_trial']=True;save(run,s)
 memory(run,'deepseek-before-start',110) # existing qualified unchanged gate
 startup(run,s,'deepseek',deep)

def restore(run,p,s):
 if not s.get('glm_stopped_by_trial'):return
 deep=s.get('deepseek_ids',{})
 if deep:
  if inspect(deep['0'])['State']['Running']:
   try:
    h=http(8894,'/health')
    if h.get('requests_running',0) or h.get('busy',False):raise RuntimeError('DeepSeek busy; restoration deferred')
   except OSError:pass
  stop_owned(deep,s['deepseek_bindings'])
 for rank in (0,1):
  if config_id(inspect(p['initial_glm_ids'][str(rank)],rank))!=p['initial_glm_bindings'][str(rank)]:raise RuntimeError('Original GLM configuration changed')
 startup(run,s,'glm',p['initial_glm_ids']);s['glm_stopped_by_trial']=False;s['restored_initial_configuration']=True;save(run,s)

def worker(run):
 with writer_lock(ROOT),writer_lock(run):
  p,s=verify(run);reconcile(run,s)
  if s['status']=='finished':return
  if any(c['status']=='interrupted_uncertain' for c in s['calls']):raise RuntimeError('Uncertain prior dispatch requires reconciliation; no automatic replay')
  if (run/'PAUSE').exists():return
  guard_glm_ownership(run)
  s.update(status='running',worker={'pid':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'start_ticks':Path(f'/proc/{os.getpid()}/stat').read_text().split()[21]},stage='glm');save(run,s)
  try:
   if any(t['status']=='pending' and t['id'].startswith(('A-','C-')) for t in s['tasks']):run_model(run,p,s,'glm')
   if s['status']=='paused':return
   if any(t['status']=='pending' and t['id'].startswith(('B-','D-')) for t in s['tasks']):
    s['stage']='deepseek_handoff';save(run,s);switch_to_deepseek(run,p,s);s['stage']='deepseek';save(run,s);run_model(run,p,s,'deepseek')
  except Exception as e:
   s.update(status='blocked',diagnostic=str(e));print('BLOCKED',str(e),flush=True);save(run,s)
  finally:
   try:restore(run,p,s)
   except Exception as e:s.update(status='blocked',restoration_error=str(e));print('RESTORATION BLOCKER',e,flush=True);save(run,s)
  if not s.get('restoration_error') and all(t['status']!='pending' and t['status']!='in_progress' for t in s['tasks']):s.update(status='finished',finished_at=now())
  save(run,s)

def main():
 a=argparse.ArgumentParser();a.add_argument('command',choices=['freeze','worker','launch','resume','status','pause']);a.add_argument('--run',type=Path,required=True);a.add_argument('--sample',type=Path);args=a.parse_args();run=args.run.resolve()
 if args.command=='freeze':freeze(run,args.sample.resolve())
 elif args.command=='status':print(json.dumps(read_json(run/'progress.json'),indent=2))
 elif args.command=='pause':(run/'PAUSE').write_text(now())
 elif args.command=='worker':worker(run)
 else:
  _,s=verify(run)
  if s['status']=='finished':print('Finished; zero new requests');return
  if args.command=='resume' and (run/'PAUSE').exists():(run/'PAUSE').unlink()
  session='cookbook-'+run.name[-6:]
  command=shlex.join([str(ROOT/'.venv-control/bin/python'),'-B','-u',str(Path(__file__).resolve()),'worker','--run',str(run)])+' >> '+shlex.quote(str(run/'terminal.log'))+' 2>&1'
  cmd(['tmux','new-session','-d','-s',session,command]);print('Persistent session',session)
if __name__=='__main__':main()
