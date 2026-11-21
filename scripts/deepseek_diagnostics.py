#!/usr/bin/env python3
"""Finite local/hosted saved-image experiment; no production queue or publication."""
import argparse,json,os,sys,time,shlex,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import atomic_json,read_json,sha,fingerprint,writer_lock,files_manifest
from probe.experiment import InputGuard,verify_seal,now
from probe.batch_review import seal_outcome,IdentityError,IntegrityError
from probe import chapter_glm,cookbook_quantities as q,deepseek_diagnostics as d,cloud_critic as cloud
from probe.local_model import LocalClient
from scripts import cookbook_quantity_trial as runtime

def save(run,s):
 atomic_json(run/'state.json',s);atomic_json(run/'progress.json',{'at':now(),'run':str(run),'status':s['status'],'stage':s.get('stage'),'consumed':len(s['calls']),'primary_limit':45,'additional_unallocated_limit':3,'tasks':s['tasks'],'worker':s.get('worker'),'service':s.get('service'),'diagnostic':s.get('diagnostic'),'hosted_blocker':s.get('hosted_blocker'),'restored':s.get('restored_initial_configuration'),'finished_at':s.get('finished_at')})

def verify(run):
 b=read_json(run/'binding.json');p=read_json(run/'plan.json');s=read_json(run/'state.json')
 if sha(run/'plan.json')!=b['plan_sha256'] or runtime.code_binding()!=b['code']:raise IntegrityError('Frozen code/plan changed')
 InputGuard(b['files']).check()
 if [x['id'] for x in p['tasks']]!=[x['id'] for x in s['tasks']] or len(p['tasks'])!=45:raise IntegrityError('Task graph changed')
 if len(s['calls'])>45 or len({c['parent'] for c in s['calls']})!=len(s['calls']):raise IntegrityError('Attempt allowance/replay violation')
 for c in s['calls']:
  if c.get('seal_sha256'):verify_seal(run/'calls'/c['id'],c['seal_sha256'],'seal.json')
 return p,s

def reconcile(run,s):
 for c in s['calls']:
  folder=run/'calls'/c['id'];t=next(t for t in s['tasks'] if t['id']==c['parent'])
  if (folder/'outcome.json').exists():
   if not (folder/'seal.json').exists():atomic_json(folder/'seal.json',files_manifest(folder))
   c['seal_sha256']=sha(folder/'seal.json');verify_seal(folder,c['seal_sha256'],'seal.json');c['status']=t['status']=read_json(folder/'outcome.json')['status']
  elif c['status']=='in_progress':c['status']=t['status']='interrupted_uncertain'
 save(run,s)

def settle_response(folder,response,task):
 atomic_json(folder/'response.json',response);choice=response['choices'][0];message=choice['message'];answer=message.get('content') or ''
 (folder/'answer.txt').write_text(answer)
 reasoning=message.get('reasoning_content',message.get('reasoning'))
 if isinstance(reasoning,str):(folder/'reasoning.txt').write_text(reasoning)
 if message.get('reasoning_details') is not None:atomic_json(folder/'reasoning-details.json',message['reasoning_details'])
 outcome={'status':'invalid_completion','finish_reason':choice.get('finish_reason'),'usage':q.reported_usage(response),'server_timings':response.get('tensorfold'),'runtime':response.get('runtime')}
 if choice.get('finish_reason')=='stop' and answer.strip():
  try:
   parsed,coverage=q.validate_answer(answer,task['scope'],task['arm']);atomic_json(folder/'parsed.json',parsed);outcome.update(status='completed' if coverage['complete'] else 'incomplete_coverage',coverage=coverage)
  except (ValueError,TypeError,KeyError) as e:outcome.update(status='invalid_response',reason=str(e))
 return outcome

def run_tasks(run,p,s,backend):
 hosted=None
 for task in p['tasks']:
  st=next(x for x in s['tasks'] if x['id']==task['id'])
  if task['backend']!=backend or st['status']!='pending':continue
  if (run/'PAUSE').exists():s['status']='paused';save(run,s);return
  verify(run);body=read_json(run/'requests'/(task['id']+'.json'))
  if fingerprint(body)!=task['request_hash']:raise IntegrityError('Request hash changed')
  expected=None
  if backend=='local':
   for rank in (0,1):
    x=runtime.inspect(s['deepseek_ids'][str(rank)],rank)
    if not x['State']['Running'] or runtime.config_id(x)!=s['deepseek_bindings'][str(rank)]:raise IdentityError('Local deployment changed')
   runtime.memory(run,task['id']+'-before',5);h=runtime.http(8894,'/health')
   if h.get('requests_running',0) or h.get('busy',False):raise IntegrityError('Local service occupied')
   tok=runtime.http(8894,'/tokenize',body);expected={'prompt_tokens':tok['count'],'image_rows':tok['tokens'].count(129264)}
   if expected['image_rows']<=0 or expected['prompt_tokens']+body['max_tokens']>1048576:raise IdentityError('Images/context preflight failed')
   atomic_json(run/'image-verification'/(task['id']+'-preflight.json'),expected)
  elif hosted is None:hosted=d.HostedClient(run)
  c=chapter_glm.reserve(s,task['id'],fingerprint(body));st.update(status='in_progress',call=c['id']);save(run,s)
  folder=run/'calls'/c['id'];folder.mkdir(parents=True);atomic_json(folder/'reservation.json',c);atomic_json(folder/'request.json',body)
  print(now(),task['id'],c['id'],'reserved',flush=True);started=time.monotonic()
  try:
   if backend=='local':
    client=LocalClient(q.MODELS['deepseek'][1],q.MODELS['deepseek'][0],api_key='',purpose='simple_chapter',timeout=None,max_tokens=d.TOKENS,max_response_bytes=32*1024*1024);client.model=q.MODELS['deepseek'][0]
    response,metadata=client._request('POST','/chat/completions',body,folder,'deepseek-diagnostic')
    atomic_json(folder/'response.json',response)
    if response.get('model')!=client.model:raise IdentityError('Local returned model mismatch')
    observed=q.reported_usage(response)['prompt_tokens']
    if observed!=expected['prompt_tokens']:raise IdentityError('Image-aware prompt usage mismatch')
    atomic_json(run/'image-verification'/(task['id']+'.json'),{'passed':True,'expected':expected,'observed_prompt_tokens':observed})
   else:response,metadata=hosted.dispatch(task,body,folder)
   outcome=settle_response(folder,response,task);outcome['metadata']=metadata
  except Exception as e:
   reason=hosted._redact(str(e)) if hosted else str(e)
   outcome={'status':'failed','reason':reason,'type':type(e).__name__}
   if isinstance(e,(IdentityError,IntegrityError)):outcome['shared_failure']=True
   if backend=='hosted':outcome['hosted_blocker']=True
   if backend=='local' and not (folder/'response.json').exists():outcome.update(status='interrupted_uncertain',shared_failure=True)
  outcome['elapsed_seconds']=time.monotonic()-started;seal_outcome(folder,outcome);c.update(status=outcome['status'],seal_sha256=sha(folder/'seal.json'),elapsed_seconds=outcome['elapsed_seconds'],usage=outcome.get('usage'));st['status']=c['status'];save(run,s)
  print(now(),task['id'],outcome['status'],round(outcome['elapsed_seconds'],1),'seconds',flush=True)
  if backend=='local':runtime.memory(run,task['id']+'-after',5)
  if outcome.get('hosted_blocker'):
   s['hosted_blocker']=outcome['reason']
   for other in s['tasks']:
    if other['id'].startswith('H-') and other['status']=='pending':other.update(status='blocked_not_dispatched',reason=outcome['reason'])
   save(run,s);return
  if outcome.get('shared_failure'):raise IntegrityError(outcome['reason'])
 if hosted:
  try:atomic_json(run/'billing-summary.json',hosted.reconcile())
  except Exception as e:atomic_json(run/'billing-reconciliation-error.json',{'reason':hosted._redact(str(e)),'retry':False})

def worker(run):
 with writer_lock(ROOT),writer_lock(run):
  p,s=verify(run)
  if s['status']=='finished':return
  reconcile(run,s)
  if any(c['status']=='interrupted_uncertain' for c in s['calls']):raise IntegrityError('Uncertain attempt needs reconciliation; no replay')
  if (run/'PAUSE').exists():return
  # Explicit reporting callback for reused lifecycle helpers; no edits to their historical plans.
  runtime.save=save
  s.update(status='running',worker={'pid':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'start_ticks':Path(f'/proc/{os.getpid()}/stat').read_text().split()[21]},started_at=s.get('started_at',now()))
  save(run,s)
  try:
   if any(t['id'].startswith('L-') and t['status']=='pending' for t in s['tasks']):
    s['stage']='local_handoff';save(run,s);runtime.switch_to_deepseek(run,p,s);s['stage']='local';save(run,s);run_tasks(run,p,s,'local')
  except Exception as e:s.update(status='blocked',diagnostic=str(e));save(run,s);print('LOCAL BLOCKED',e,flush=True)
  finally:
   try:runtime.restore(run,p,s)
   except Exception as e:s.update(status='blocked',restoration_error=str(e));save(run,s);print('RESTORATION BLOCKED',e,flush=True)
  if s['status']=='paused' or s.get('restoration_error'):return
  try:s['stage']='hosted';save(run,s);run_tasks(run,p,s,'hosted')
  except Exception as e:s.update(hosted_blocker=str(e),status='blocked');save(run,s);print('HOSTED BLOCKED',e,flush=True)
  if all(t['status'] not in ('pending','in_progress') for t in s['tasks']):s.update(status='finished',finished_at=now(),stage='complete')
  save(run,s)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('command',choices=['worker','launch','resume','pause','status']);ap.add_argument('--run',required=True,type=Path);a=ap.parse_args();run=a.run.resolve()
 if a.command=='status':print(json.dumps(read_json(run/'progress.json'),indent=2));return
 if a.command=='pause':(run/'PAUSE').write_text(now());return
 p,s=verify(run)
 if s['status']=='finished':print('Finished; zero new requests');return
 if a.command=='worker':worker(run);return
 if a.command=='resume' and (run/'PAUSE').exists():(run/'PAUSE').unlink()
 session='deepseek-diagnostics-'+run.name[-6:]
 command=shlex.join([str(ROOT/'.venv-control/bin/python'),'-B','-u',str(Path(__file__).resolve()),'worker','--run',str(run)])+' >> '+shlex.quote(str(run/'terminal.log'))+' 2>&1'
 runtime.cmd(['tmux','new-session','-d','-s',session,command]);print(session)
if __name__=='__main__':main()
