#!/usr/bin/env python3
"""Persistent finite source-image reviews. No OCR, conversion, service change or paid route."""
import argparse,copy,csv,hashlib,json,os,shlex,shutil,subprocess,sys,time,zipfile,difflib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha,fingerprint,writer_lock
from probe.experiment import InputGuard,verify_seal
from probe import focused_recovery as edits,image_review as vision,chapter_glm as runtime,chapter_concurrency as scheduler,compiler_environment as compiler
from probe.local_model import LocalClient
from scripts import extraction_comparison as base
POINTER=ROOT/'results/glm-image-review-current.json';SESSION='pdf-glm-image-review';TERMINAL='image_review_finished'


def save(run,s):
 runtime.save(run,s)
 atomic_json(run/'progress.json',{'at':runtime.now(),'run':str(run),'status':s['status'],'stage':s.get('stage'),'diagnostic':s.get('diagnostic'),'work_calls_consumed':len(s['calls']),'work_ceiling':8,'authorized_ceiling':10,'readiness_consumed':0,'tasks':[{k:t.get(k) for k in ['id','status','call','images_verified','compilation','reason']} for t in s['tasks']],'calls':[{'id':c['id'],'task':c['parent'],'status':c['status'],'seconds':c.get('elapsed_seconds'),'usage':c.get('metadata',{}).get('usage')} for c in s['calls']],'log':str(run/'terminal.log'),'inspection':s.get('inspection')})

def freeze(run):
 if (run/'plan.json').exists():return verify(run)
 plan=read_json(run/'plan-draft.json');cpu=read_json(run/'cpu-preprocessing.json')
 assert len(plan['tasks'])==8 and plan['C']['included'] is False
 if not (run/'evaluation/reading-sheet.json').exists():raise ValueError('Missing held-out source readings')
 for t in plan['tasks']:
  expected=cpu['requests'][t['id'].replace('-parallel','')]
  if expected['image_rows']!=t['budget']['image_tokens']:raise ValueError('CPU image allocation differs from request budget')
  t['cpu_expectation']=expected
 plan['status']='frozen';atomic_json(run/'plan.json',plan)
 old=read_json(run/'repair-state.json');s={k:copy.deepcopy(old[k]) for k in ['compiler_environment','concurrency_policy','chapter_contract','execution_limits','timing_policy']}
 s.update(status='prepared',created_at=runtime.now(),first_dispatch=None,calls=[],connection_failures=0,tasks=[],versions={},current_versions={},active_stage=0,stages={str(i+1):{} for i in range(len(plan['stages']))},stage_results={},launches=[],source_units={},documents={},disable_dependency_downloads=True,suite_protocol='source-image-review-v1',stage_index=0)
 for t in plan['tasks']:
  s['tasks'].append({'id':t['id'],'key':t['id'],'source_key':t['source'],'phase':'critic','status':'pending','reasoning_effort':t['effort'],'base_sha256':t['draft_sha256']})
  s['versions'][t['id']]={'historical-input':{'path':'inputs/'+t['source']+'/draft.tex','sha256':t['draft_sha256']}}
  s['current_versions'][t['id']]='historical-input';s['documents'][t['source']]={'filename':plan['sources'][t['source']]['filename']}
 s['production_stage']={'task_ids':[t['id'] for t in s['tasks']]}
 frozen={str(p):sha(p) for directory in ['inputs','requests','evaluation'] for p in (run/directory).rglob('*') if p.is_file()}
 frozen[str(run/'cpu-preprocessing.json')]=sha(run/'cpu-preprocessing.json')
 for source in plan['sources'].values():
  manifest=read_json(run/'inputs'/('cf' if '21debf' in source['source_id'] else 'ig')/'A-images.json')
  frozen[manifest[0]['original_pdf']]=source['sha256']
 atomic_json(run/'binding.json',{'code':base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':frozen});save(run,s);return s

def verify(run):
 s=read_json(run/'state.json');plan=read_json(run/'plan.json');binding=read_json(run/'binding.json')
 if sha(run/'plan.json')!=binding['plan_sha256'] or base.code_binding()!=binding['code']:raise runtime.Fatal('Frozen implementation/plan changed')
 InputGuard(binding['files']).check()
 if [t['id'] for t in s['tasks']]!=[t['id'] for t in plan['tasks']]:raise runtime.Fatal('Task set changed')
 if len(s['calls'])>8 or len({c['parent'] for c in s['calls']})!=len(s['calls']):raise runtime.Fatal('Consumed allowance/replay violation')
 for t in s['tasks']:
  original=next(x for x in plan['tasks'] if x['id']==t['id'])
  if t['base_sha256']!=original['draft_sha256'] or t['reasoning_effort']!=original['effort']:raise runtime.Fatal('Draft/settings changed')
 for c in s['calls']:
  if c.get('seal'):verify_seal(run/'calls'/c['id'],c['seal'])
 return s

def body_for(run,s,t):
 p=next(p for p in read_json(run/'plan.json')['tasks'] if p['id']==t['id']);body=read_json(run/'requests'/(t['id']+'.json'))
 if fingerprint(body)!=p['request_sha256']:raise runtime.Fatal('Prepared request changed')
 records=read_json(run/p['images_manifest']);expected=vision.image_parts(records,run)
 content=body['messages'][0]['content']
 if vision.image_content(body)!=expected:raise runtime.Fatal('Outgoing images differ from original-image manifest')
 payload=vision.request_payload(body);draft=(run/'inputs'/t['source_key']/'draft.tex').read_text()
 if payload['draft']!=draft or payload['base_sha256']!=edits.digest(draft) or edits.digest(draft)!=t['base_sha256']:raise runtime.Fatal('Stale draft')
 return body

def before(run,s,t,body):
 verify(run)
 if t['id'] not in read_json(run/'plan.json')['stages'][s['stage_index']]:raise runtime.Fatal('Task not in current frozen stage')
 if t['status']!='pending' or any(c['parent']==t['id'] for c in s['calls']):raise runtime.Fatal('Consumed task cannot replay')
 if body!=body_for(run,s,t):raise runtime.Fatal('Outgoing request identity changed')
 print('IMAGE REVIEW',t['id'],t['reasoning_effort'],'draft',t['base_sha256'],flush=True)

def finish(run,s,t,answer,call):
 if t.get('settled_call')==call['id']:return
 p=next(p for p in read_json(run/'plan.json')['tasks'] if p['id']==t['id']);usage=call.get('metadata',{}).get('usage',{})
 # This is returned SERVER usage, compared with installed CPU rendering of the
 # exact PNG bytes, vision template and expanded <image> rows; fields alone don't pass.
 expected=p['cpu_expectation'];observed=usage.get('prompt_tokens')
 t['images_verified']=observed==expected['prompt_tokens'] and expected['image_rows']>0
 atomic_json(run/'image-verification'/(t['id']+'.json'),{'observed_server_prompt_tokens':observed,'expected_installed_rendering':expected,'passed':t['images_verified'],'method':'Exact server prompt usage equals independently rendered image-expanded prompt; installed vision frontend/engine refuses missing feature rows. GPU tensor contents are not directly instrumented.'})
 if not t['images_verified']:
  t.update(status='image_processing_unverified',settled_call=call['id'],call=call['id']);save(run,s);raise runtime.Fatal('Image processing/identity verification failed; no text-only fallback')
 t.update(call=call['id'],settled_call=call['id'])
 if answer is None:t['status']=call.get('failure_kind','failed');save(run,s);return
 draft=(run/'inputs'/t['source_key']/'draft.tex').read_text()
 proposal_path=run/'proposals'/(t['id']+'.txt');proposal_path.parent.mkdir(exist_ok=True);proposal_path.write_text(answer)
 try:
  proposal=edits.parse_json_response(edits.single_outer_fence(answer) or answer)
  revised,findings=vision.apply_review(draft,proposal)
 except (ValueError,KeyError,TypeError) as exc:t.update(status='invalid_review',reason=str(exc));save(run,s);return
 dest=run/'reviews'/t['id'];dest.mkdir(parents=True,exist_ok=True);(dest/'original.tex').write_text(draft);(dest/'reviewed.tex').write_text(revised)
 atomic_json(dest/'findings.json',findings);(dest/'changes.diff').write_text(''.join(difflib.unified_diff(draft.splitlines(True),revised.splitlines(True),fromfile='exact-historical-draft',tofile=t['id'])))
 # No model-assisted repair. Both actual versions compiled once in this trial.
 for label,text in [('original',draft),('reviewed',revised)]:
  if not (dest/label/'compilation.json').exists():compiler.compile_saved(run,s,ROOT,text,dest/label,{})
 selection=vision.compiling_selection({'path':str((dest/'original.tex').relative_to(run)),'sha256':edits.digest(draft)},
  {'path':str((dest/'reviewed.tex').relative_to(run)),'sha256':edits.digest(revised)},read_json(dest/'reviewed/compilation.json'))
 atomic_json(dest/'selection.json',selection)
 t.update(status='review_completed',revised_sha256=edits.digest(revised),compilation=read_json(dest/'reviewed/compilation.json')['status'],scope_review=findings['scope_review'],pending_suggestions=findings['pending_suggestions'],review_complete_attested=findings['review_complete_attested']);save(run,s)

def live_binding(run):
 program="""import json,hashlib,os; from pathlib import Path; from tensorfold.vision.glm import GlmVisionLimits; l=GlmVisionLimits.from_env(); p=Path('/usr/local/lib/python3.12/dist-packages/tensorfold'); print(json.dumps({'limits':{k:getattr(l,k) for k in ['image_tokens','request_image_tokens','max_images']},'sources':{n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['vision/glm.py','vision/images.py','server/prompts.py','cuda/chat_template.py','server/request_options.py','families/glm5_next/cuda/app.py']}}))"""
 actual=json.loads(subprocess.check_output(['docker','exec','glm53-flash-tf','python','-c',program],text=True));expected=read_json(run/'cpu-preprocessing.json')
 if actual['limits']!=expected['limits'] or actual['sources']!=expected['sources']:raise runtime.Fatal('Running limits/installed image path changed')
 atomic_json(run/'runtime-bindings'/(str(time.time_ns())+'.json'),actual)

def bundle(run,s):
 plan=read_json(run/'plan.json');rows=[]
 for c in s['calls']:
  u=c.get('metadata',{}).get('usage',{});reason=u.get('completion_tokens_details',{}).get('reasoning_tokens');total=u.get('completion_tokens');meta=run/'calls'/c['id']/'response-metadata.json'
  rows.append({'call':c['id'],'task':c['parent'],'status':c['status'],'seconds':c.get('elapsed_seconds'),'reasoning_tokens':reason,'final_tokens':total-reason if isinstance(total,int) and isinstance(reason,int) else None,'server_timings':read_json(meta).get('server_timings') if meta.exists() else None})
 comparisons={}
 bytask={c['parent']:c for c in s['calls']}
 for source in ('cf','ig'):
  comparisons[source]={}
  for name,left,right in [('crops','A','B'),('effort','B','B-high')]:
   a=bytask.get(source+'-'+left);b=bytask.get(source+'-'+right)
   if a and b:comparisons[source][name]={'left_status':a['status'],'right_status':b['status'],'left_seconds':a.get('elapsed_seconds'),'right_seconds':b.get('elapsed_seconds'),'interpretation':'Descriptive elapsed time including failure cost; not evidence of fidelity or a general speed claim'}
 sequential=[bytask.get(x) for x in ('cf-B','ig-B')]
 if all(sequential) and '1' in s.get('stage_results',{}):comparisons['concurrency']={'sequential_request_seconds':sum(x['elapsed_seconds'] for x in sequential),'parallel_stage_wall_seconds':s['stage_results']['1']['elapsed_seconds'],'limitations':'Compare only usable exact-input runs; includes finalization and cache/server-load differences'}
 atomic_json(run/'comparisons.json',comparisons)
 atomic_json(run/'results.json',{'requests':rows,'stages':s.get('stage_results'),'repairs':read_json(run/'repairs/report.json'),'mathematical_dispositions':read_json(run/'evaluation/spectral-eight-edits.json'),'evaluation':'Model findings kept separate from the held-out source readings. Returned count/compilation/agreement does not establish better accuracy. New harmful edits and missed errors require located source adjudication. Small sample and cache/load differences limit speed conclusions.'})
 text=['# Finite GLM source-image experiment','Status: '+s['status'],'Run: '+str(run),'Settings stay2048/image,16384 shared,50 images. Optional C was deferred before freezing; no serving change.','Work ceiling8 (within authorised10), one attempt each, no generating-readiness calls. No OCR, conversion, syntax-model repair, paid request or production queue.',
 'Saved-file repairs: '+json.dumps(read_json(run/'repairs/report.json')),
 'Read results.json, plan.json, image-verification/, reviews/, evaluation/ and repairs/. Original source-faithful versions, model proposals and applied derivatives remain separate. Eight Spectral changes are locally source/derivation-checked corrections to printed mathematics, not OCR repairs. Two earlier exhausted whole-paper review scopes remain unreviewed.','## Tasks']+[t['id']+': '+t['status']+(' — '+t.get('reason','') if t.get('reason') else '') for t in s['tasks']]
 (run/'START-HERE.md').write_text('\n\n'.join(text)+'\n')
 out=ROOT/'results/inspection'/('glm-image-review-'+run.name+'-'+str(time.time_ns())+'.zip');manifest=[];omitted=[]
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  for p in run.rglob('*'):
   if not p.is_file():continue
   rel=p.relative_to(run)
   if any(x in rel.parts for x in ('requests','preparation-history','compiler-environments','calls','samples')) or 'reasoning' in p.name or p.stat().st_size>6*1024**2:
    omitted.append({'path':str(p),'bytes':p.stat().st_size});continue
   z.write(p,str(rel));manifest.append({'path':str(rel),'sha256':sha(p),'bytes':p.stat().st_size})
  for t in plan['tasks']:
   z.writestr('request-metadata/'+t['id']+'.json',json.dumps(t,indent=2))
  z.writestr('OMITTED.json',json.dumps(omitted,indent=2));z.writestr('FILE-HASHES.json',json.dumps(manifest,indent=2))
 with zipfile.ZipFile(out) as z:
  if z.testzip():raise runtime.Fatal('ZIP integrity failed')
 s['inspection']=str(out);save(run,s);return out

def worker(run,workflow=None):
 # Explicit workflow callbacks reuse this controller's ownership, durable
 # scheduler and installed vision checks; no second transport or supervisor.
 wf=workflow or sys.modules[__name__]
 save,verify,finish,bundle=wf.save,wf.verify,wf.finish,wf.bundle
 body_for,before=wf.body_for,wf.before
 with (run/'terminal.log').open('a',buffering=1) as log:
  os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
  with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):
   s=verify(run)
   if s['status']==wf.TERMINAL:return
   try:
    s.update(status='running',diagnostic=None);s['launches'].append({'at':runtime.now(),'pid':os.getpid()});save(run,s)
    runtime.check_other_jobs();helpers=base.books.speed.module();base.books.book.arrange_glm(run,check_only=True);live_binding(run)
    efforts=base.books.speed.effort_check(run,helpers)
    if efforts.get('status')!='supported':raise runtime.Fatal('Installed High/Max effort mappings unverified')
    plan=read_json(run/'plan.json');rawsample=base.books.speed.sampler(run,s,helpers)
    def sample(owned):
     obs=rawsample(owned);available=obs['memory_available_bytes'];s.setdefault('memory_samples',[]).append({'at':runtime.now(),'owned':owned,'available':available})
     save(run,s)
     if any(v<4*1024**3 for v in available.values()):raise runtime.StopRun('Less than4GiB observed headroom; no image dispatch')
     return obs
    base.books.speed.healthy(sample(0))
    for c in s['calls']:
     t=next(t for t in s['tasks'] if t['id']==c['parent'])
     if t.get('settled_call')==c['id']:continue
     folder=run/'calls'/c['id']
     if not (folder/'manifest.json').exists():raise runtime.Fatal('Uncertain consumed request; no replay')
     verify_seal(folder);c.update(read_json(folder/'outcome.json'));c['seal']=sha(folder/'manifest.json');finish(run,s,t,(folder/'content.txt').read_text() if c['status']=='completed_response' else None,c)
    for index,ids in enumerate(plan['stages']):
     s['stage_index']=index;s['active_stage']=index+1;tasks=[t for t in s['tasks'] if t['id'] in ids]
     if all(t['status']!='pending' for t in tasks):continue
     if index==1 and workflow is None:
      prerequisite=[t for t in s['tasks'] if t['id'] in ('cf-B','ig-B')]
      if not all(t['status']=='review_completed' and t.get('images_verified') for t in prerequisite):
       for t in tasks:t.update(status='skipped',reason='Sequential B/Max did not yield usable image-verified reviews')
       save(run,s);continue
      try:base.books.speed.healthy(sample(0))
      except runtime.StopRun as exc:
       for t in tasks:t.update(status='skipped',reason='Concurrency resource qualification failed: '+str(exc))
       save(run,s);continue
     spec=plan.get('stage_specs',{}).get(str(index),{})
     s['stage']=spec.get('title','sequential Max A/B' if index==0 else 'two simultaneous B/Max' if index==1 else 'sequential B/High');save(run,s);start=time.time()
     scheduler.coordinate(run,s,tasks,body_for=body_for,finish=finish,verify=lambda:verify(run),changed=lambda:save(run,s),sample=sample,fixed_level=spec.get('concurrency',2 if index==1 else 1),before_reserve=lambda state,t,b:before(run,state,t,b))
     s['stage_results'][str(index)]={'elapsed_seconds':time.time()-start,'tasks':ids};save(run,s)
    if workflow is not None:wf.finalize(run,s)
    s.update(status=wf.TERMINAL,finished_at=runtime.now(),stage='finished; no next experiment')
   except runtime.StopRun as exc:s.update(status='stopped_error' if isinstance(exc,runtime.Fatal) else 'paused',diagnostic=str(exc))
   except BaseException as exc:s.update(status='stopped_error',diagnostic=str(exc),traceback=scheduler.exception_trace(run,exc,'Image review'))
   finally:save(run,s);bundle(run,s)

def main(workflow=None):
 wf=workflow or sys.modules[__name__]
 p=argparse.ArgumentParser();p.add_argument('action',choices=('freeze','run','resume','worker','status','pause','bundle'));p.add_argument('--run',type=Path);a=p.parse_args();run=(a.run or Path(read_json(wf.POINTER)['run'])).resolve()
 if a.action=='freeze':wf.freeze(run);print(run);return
 if a.action=='status':print(json.dumps(read_json(run/'progress.json'),indent=2));return
 if a.action=='pause':atomic_json(run/'pause.json',{'at':runtime.now()});print('Pause requested; drain owned calls');return
 if a.action=='worker':worker(run,workflow);return
 s=wf.verify(run)
 if a.action=='bundle':
  with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):print(wf.bundle(run,s))
  return
 if s['status']==wf.TERMINAL:print('Finished; zero new requests');return
 if not all(base.books.speed.idle(p) for p in (ROOT,ROOT/'runs',run)):raise runtime.Fatal('Existing writer; no duplicate worker')
 if any(c['status']=='in_progress' and not (run/'calls'/c['id']/'manifest.json').exists() for c in s['calls']):raise runtime.Fatal('Uncertain request; no replay')
 cp=subprocess.run(['tmux','has-session','-t',wf.SESSION],capture_output=True,text=True)
 if cp.returncode!=1:raise runtime.Fatal('Worker exists or tmux unavailable')
 base.collection.normal_checks(run);(run/'pause.json').unlink(missing_ok=True)
 command=shlex.join([str(base.PYTHON),'-B','-u',str(Path(wf.__file__).resolve()),'worker','--run',str(run)])
 subprocess.run(['tmux','new-session','-d','-s',wf.SESSION,'cd '+shlex.quote(str(ROOT))+' && exec '+command],check=True);print('Persistent launch requested:',run)
if __name__=='__main__':main()
