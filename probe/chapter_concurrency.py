"""One editorial coordinator; bounded parallel HTTP only, unchanged book requests.

Workers own isolated call directories. State, reservations, validation, version
selection, compilation and report writes belong to the coordinator thread.
"""
import copy
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import json
import time
from pathlib import Path
from . import chapter_glm as runtime, chapter_protocol as protocol
from .common import atomic_json, fingerprint, read_json, sha
from .experiment import verify_seal

POLICY = {'version':'editorial-concurrency-v2','two_request_sample':4,'four_request_sample':8,
          'pool_fraction':0.90,'minimum_available_bytes':2*1024**3,
          'sampling_seconds':15,'maximum_in_flight':2,
          'overall_call_limit':None,'overall_deadline':None,
          'four_acceptance':'Deferred: not admitted by this linked continuation. Reasoning-token throughput cannot qualify concurrency.',
          'pause':'stop admission, drain; stop preserves partial streams; no automatic replay'}
GOOD = {'conversion_completed','critic_revised','critic_unchanged'}
SHARED = {'identity','adapter_exception','operator_stop'}


def health_limits(health,owned=0):
    streams=health.get('streams',{})
    values=[streams.get('decoding'),streams.get('prefilling',streams.get('filling')),
            streams.get('paused'),streams.get('max'),health.get('context_length'),health.get('pool_tokens')]
    if any(type(v) is not int or v<0 for v in values):raise runtime.Fatal('Missing/invalid concurrent GLM capacity counters')
    decoding,filling,paused,slots,context,pool=values
    running=health.get('requests_running')
    if type(running) is not int or running<0:raise runtime.Fatal('Missing actual GLM request ownership counter')
    if max(running,decoding+filling)>owned or (health.get('busy') and owned==0):
        raise runtime.Fatal('Unowned active GLM request; no further dispatch, services left untouched; '
                            f'server running={running}, decoding={decoding}, prefilling={filling}, '
                            f'local owned at sample={owned}, busy={health.get("busy")}')
    if slots<2 or context<131072 or pool<=0:raise runtime.Fatal('Existing GLM cannot admit two long requests; deployment unchanged')
    return {'slots':slots,'context':context,'pool':pool,'active':decoding+filling,'paused':paused}


def room(body,budgets,health,owned):
    limits=health_limits(health,owned)
    budget=protocol.budget(body,limits['context'])
    used=sum(b['combined_upper_estimate'] for b in budgets)
    # The installed pool evicts unowned kept prefixes (multi.py fits/_room/_grow).
    # Count *all* active full prompt+output reservations against the shared pool,
    # including growth headroom. Free rows alone omit reclaimable kept prefixes.
    fits=used+budget['combined_upper_estimate']<=int(limits['pool']*POLICY['pool_fraction'])
    return fits,budget


def eligible(state,tasks):
    """Critics first, original order within each phase; never share a draft writer."""
    conversions={t['key']:t for t in tasks if t['phase']=='convert'}
    ready=[]
    for t in tasks:
        if t['status']!='pending':continue
        if t['phase']=='critic':
            c=conversions.get(t['key'])
            if c and c['status'] in ('pending','running'):continue
            if not (t.get('draft_label') or state.get('current_versions',{}).get(t['key'])):
                t.update(status='unavailable',error='No complete conversion to review');continue
        ready.append(t)
    return sorted(ready,key=lambda t:t['phase']!='critic')


def mark_uncertain(state,tasks):
    """A reservation without a coordinator disposition is never auto-replayed."""
    for t in tasks:
        calls=[c for c in state['calls'] if c['parent']==t['id']]
        if t['status'] in ('pending','running') and calls:
            t.update(status='interrupted_unresolved',error='Saved reservation/response without completed coordinator disposition; retained, no replay',
                     call=calls[-1]['id'])


def phase_record(progress,level):
    name='two' if level==2 else 'four'
    record=progress.setdefault('trials',{}).setdefault(name,{'level':level,'calls':[],
        'started_epoch':time.time(),'active_seconds':0,'max_server_streams':0,'resource_pressure':False,
        'resource_pressure_events':[],'status':'pending'})
    return record


def interrupted_handover(progress,old,parent):
    """Correct the linked interpretation only; never rewrite historical state."""
    for record in progress.get('trials',{}).values():
        if record['status'] in ('running','pending'):
            record.update(status='interrupted',reason=old.get('diagnostic'),inherited_from=str(parent))
            sessions=progress.get('sessions',[])
            if sessions and sessions[-1].get('finished_epoch'):
                record['last_active_epoch']=sessions[-1]['finished_epoch']
    progress.setdefault('interruptions',[]).append({'parent':str(parent),'status':old['status'],
                                                   'diagnostic':old.get('diagnostic')})


def trial_metrics(state,trial):
    calls={c['id']:c for c in state['calls']};tasks={t.get('call'):t for t in state['tasks']}
    rows=[]
    for ident in trial['calls']:
        c=calls[ident];t=tasks.get(ident,{})
        u=c.get('metadata',{}).get('usage',{});tokens=u.get('completion_tokens');reason=u.get('completion_tokens_details',{}).get('reasoning_tokens')
        row={'call':ident,'task':c['parent'],'task_status':t.get('status'),'status':c['status'],
             'elapsed_seconds':c.get('elapsed_seconds'),'finish_reason':c.get('metadata',{}).get('finish_reason'),
             'prompt_tokens':u.get('prompt_tokens'),'completion_tokens':tokens,'reasoning_tokens':reason,
             'other_completion_tokens':tokens-reason if type(tokens)is int and type(reason)is int else None,
             'usable_document_or_review':t.get('status') in GOOD,
             'structural_observations':t.get('structural_observations'),'failure':c.get('error') or t.get('error')}
        rows.append(row)
    tokens=sum(r['completion_tokens'] or 0 for r in rows if r['usable_document_or_review'])
    final=[r['other_completion_tokens'] for r in rows if r['usable_document_or_review']]
    final_tokens=sum(final) if final and all(v is not None for v in final) else None
    seconds=trial['active_seconds']
    return {'rows':rows,'usable_results':sum(r['usable_document_or_review'] for r in rows),
            'usable_completion_tokens':tokens,'active_batch_seconds':seconds,
            'wall_seconds_including_manual_pauses':trial.get('finished_epoch',trial.get('last_active_epoch',time.time()))-trial['started_epoch'],
            'usable_completion_tokens_per_active_second':tokens/seconds if seconds else 0,
            'usable_nonreasoning_tokens':final_tokens,
            'usable_nonreasoning_tokens_per_active_second':final_tokens/seconds if final_tokens is not None and seconds else None,
            'note':'Batch time includes preparation/finalization/compilation. Overlapping stream durations are not wall time. Different task sets are not a causal speed benchmark; technical usability is not fidelity.'}


def assessment(state,progress,trial):
    metrics=trial_metrics(state,trial);trial['metrics']=metrics
    if trial['resource_pressure']:return False,'Resource pressure recorded; drain before using a lower qualified level'
    if trial['max_server_streams']<trial['level']:return False,'Requested server overlap not observed; level unqualified'
    if not metrics['usable_results']:return False,'No usable completed output to qualify this sample'
    if trial['level']>POLICY['maximum_in_flight']:return False,'Concurrency level exceeds this continuation; no automatic four-slot admission'
    return True,'Bindings and normal finalization checked; server overlap observed, resource checks passed. Accuracy not established.'


def response_binding(run,call,body):
    dest=run/'calls'/call['id']
    if not call.get('seal'):raise runtime.Fatal('Unsealed request completion')
    verify_seal(dest,call['seal'])
    if fingerprint(read_json(dest/'request.json'))!=fingerprint(body):raise runtime.Fatal('Saved request/response association changed')
    for p in dest.glob('attempts/*/request.json'):
        if read_json(p).get('body')!=body:raise runtime.Fatal('Actual outgoing request differs from reserved request')


def write_report(run,state):
    progress=state.get('concurrency_progress',{})
    data={'policy':state.get('concurrency_policy'),'progress':progress,'at':runtime.now(),
          'report_scope':'Operational concurrency, not source verification or a randomized speed comparison',
          'compilation':{t['key']:state.get('versions',{}).get(t['key'],{}).get(state.get('current_versions',{}).get(t['key']),{}).get('compilation')
                         for t in state['tasks'] if t.get('call') in {i for r in progress.get('trials',{}).values() for i in r['calls']}}}
    atomic_json(run/'concurrency-report.json',data)
    text=['# Concurrency operational pilot', 'Run status: '+str(state.get('status'))+'; scheduling phase: '+str(progress.get('phase','not dispatched')),
          'Only scheduling changes. High conversion / Max critic, 131072, exact dual-source requests and one attempt per task. No book-wide call/deadline ceiling.',
          '## Samples']
    for name,r in progress.get('trials',{}).items():
        m=trial_metrics(state,r)
        text += [f"{name}: {r['status']}; actual maximum server streams {r['max_server_streams']}; {m['usable_results']}/{len(r['calls'])} usable results; active batch {m['active_batch_seconds']:.1f}s. {r.get('reason','')}",
                 '|Call|Task|Result|seconds|prompt|completion|reasoning|other completion|finish|','|---|---|---|---:|---:|---:|---:|---:|---|']
        for row in m['rows']:
            text.append('|'+ '|'.join(str(row.get(k)) for k in ('call','task','task_status','elapsed_seconds','prompt_tokens','completion_tokens','reasoning_tokens','other_completion_tokens','finish_reason'))+'|')
        text.append('Non-reasoning tokens in usable results: '+str(m['usable_nonreasoning_tokens'])+'. Counts/rates alone do not qualify concurrency; the pilot must complete its operational checks.')
    text += ['Compilation and model review do not establish mathematical correctness. Omissions and substantive changes require source inspection; existing accuracy logs, structural observations and original/revised TeX remain available. Missing counters stay unknown.']
    (run/'concurrency-report.md').write_text('\n\n'.join(text)+'\n')


def coordinate(run,state,tasks,*,body_for,finish,verify,changed,sample,checkpoint=lambda:None,
               transport=runtime.perform_reserved,poll_seconds=None):
    """Caller holds project + run locks. No second writer, no worker state writes."""
    if state['concurrency_policy']!=POLICY:raise runtime.Fatal('Changed sealed concurrency policy')
    mark_uncertain(state,tasks)
    progress=state.setdefault('concurrency_progress',{'phase':'two','qualified_level':None,'trials':{},'sessions':[]})
    session={'started_at':runtime.now(),'started_epoch':time.time()};progress['sessions'].append(session)
    period=POLICY['sampling_seconds'] if poll_seconds is None else poll_seconds
    jobs={};last_sample=0;observation=None;stop=None;window_start=time.monotonic();collected=[]
    def save():
        runtime.save(run,state);write_report(run,state);changed()
    def time_account():
        nonlocal window_start
        now=time.monotonic()
        if progress['phase'] in ('two','four'):
            record=phase_record(progress,2 if progress['phase']=='two' else 4)
            record['active_seconds']+=now-window_start;record['last_active_epoch']=time.time()
        window_start=now
    def stopped(exc):
        nonlocal stop
        if stop is not None:return
        stop=exc
        record={'at':runtime.now(),'diagnostic':str(exc),'exception':type(exc).__name__,
                'phase':progress['phase'],'observation':observation,
                'local_calls':[{'call':v[0]['id'],'task':v[1]['id'],'future_done':f.done()} for f,v in jobs.items()],
                'collected_this_session':list(collected)}
        path=run/'concurrency-stops'/('stop-'+str(time.time_ns())+'.json')
        atomic_json(path,record);session['stop_record']=str(path.relative_to(run))
        session['stop_requested_at']=record['at'];session['diagnostic']=str(exc)
        save()
    try:
        with ThreadPoolExecutor(max_workers=POLICY['maximum_in_flight'],thread_name_prefix='chapter-http') as pool:
            while True:
                time_account()
                if (run/'pause.json').exists() or (run/'stop.json').exists():stopped(runtime.StopRun('Operator pause/stop; all dispatched streams drained and retained'))
                # Always collect already-finished responses before capacity/dispatch decisions.
                for future in [f for f in jobs if f.done()]:
                    call,task,body,budget=jobs.pop(future)
                    # Health belongs to the local ownership set at sampling time.
                    # Never compare its old server count against the smaller set
                    # after collecting a completion (the call-102/103 race).
                    observation=None
                    collected.append({'call':call['id'],'task':task['id'],'at':runtime.now()})
                    try:
                        answer,result=future.result()
                        if any(result[k]!=call[k] for k in ('id','parent','request_sha256')):raise runtime.Fatal('Worker returned a different reserved task')
                        response_binding(run,result,body)
                        call.update(result);runtime.account_response(state,call)
                        if (call.get('metadata',{}).get('http_status') or 0)>=500:
                            raise runtime.Fatal('Server/infrastructure failure: '+str(call.get('error')))
                        if call.get('failure_kind') in SHARED:raise runtime.Fatal('Shared request failure: '+str(call.get('error')))
                        finish(run,state,task,answer,call)
                        if state.get('connection_failures',0)>=2:raise runtime.StopRun('Repeated connection failures; drain before operator diagnosis')
                    except BaseException as exc:
                        task.update(status='interrupted_unresolved' if call['status']=='in_progress' else 'coordinator_failure',
                                    error=type(exc).__name__+': '+str(exc),call=call['id'])
                        stopped(exc)
                    save()
                if stop:
                    if not jobs:raise stop
                    wait(jobs,timeout=min(period,1),return_when=FIRST_COMPLETED);continue
                candidates=eligible(state,tasks)
                phase=progress['phase'];level=2 if phase=='two' else 4 if phase=='four' else progress['qualified_level']
                if level is not None and level>POLICY['maximum_in_flight']:
                    stopped(runtime.Fatal('Saved concurrency level exceeds the sealed two-slot continuation'));continue
                trial=phase_record(progress,level) if phase in ('two','four') else None
                goal=POLICY['two_request_sample'] if level==2 else POLICY['four_request_sample']
                if trial and len(trial['calls'])>=goal and not jobs:
                    time_account();trial['finished_epoch']=time.time()
                    passed,reason=assessment(state,progress,trial);trial.update(status='qualified' if passed else 'not_qualified',reason=reason)
                    if level==2 and not passed:
                        save();raise runtime.StopRun('Two-slot pilot unqualified: '+reason+'; no automatic rerun')
                    progress.update(qualified_level=level if passed else 2,
                                    phase='four' if level==2 and POLICY['maximum_in_flight']>=4 else 'production')
                    save();checkpoint();continue
                if not jobs and not candidates:
                    progress['phase']='finished';save();break
                if not observation or time.monotonic()-last_sample>=period or not jobs:
                    try:
                        owned_calls=[v[0]['id'] for v in jobs.values()]
                        observation=sample(len(owned_calls));last_sample=time.monotonic()
                        observation['coordinator_owned_calls']=owned_calls
                        observation['coordinator_sampled_at']=runtime.now()
                        limits=health_limits(observation['health'],len(jobs))
                        memory=observation['memory_available_bytes']
                        if len(memory)!=2 or any(type(v)is not int or v<POLICY['minimum_available_bytes'] for v in memory.values()):
                            pressure='Less than 2 GiB unadjusted available memory on a node'
                        elif limits['paused']:pressure='Server reports paused streams/cache pressure'
                        else:pressure=None
                        if trial:
                            trial['max_server_streams']=max(trial['max_server_streams'],limits['active'])
                            if pressure:trial['resource_pressure']=True;trial['resource_pressure_events'].append(pressure)
                        if pressure:
                            if level==4 and progress.get('qualified_level')==2:
                                progress['drain_to_two']=pressure
                            else:raise runtime.StopRun(pressure+'; no new dispatch')
                    except BaseException as exc:stopped(exc);continue
                if progress.get('drain_to_two'):
                    if jobs:wait(jobs,timeout=min(period,1),return_when=FIRST_COMPLETED);continue
                    if trial:trial.update(status='not_qualified',reason=progress['drain_to_two'],finished_epoch=time.time(),metrics=trial_metrics(state,trial))
                    progress.update(phase='production',qualified_level=2);progress.pop('drain_to_two');save();continue
                if level==4 and limits['slots']<4:
                    if jobs:wait(jobs,timeout=min(period,1),return_when=FIRST_COMPLETED);continue
                    if trial:trial.update(status='not_admitted',reason='Current server has fewer than four slots')
                    progress.update(phase='production',qualified_level=2);save();continue
                admitted=False
                for task in candidates:
                    if len(jobs)>=min(level,limits['slots']) or (trial and len(trial['calls'])>=goal):break
                    try:
                        verify()
                        body=body_for(run,state,task)
                        if body is None:task.update(status='unavailable',error='No complete conversion to review');save();continue
                        if task.get('preview_hash') and fingerprint(body)!=task['preview_hash']:raise runtime.Fatal('Prepared request changed')
                        # Guard the snapshot against its own ownership set;
                        # capacity reservations still include every current job.
                        fits,budget=room(body,[v[3] for v in jobs.values()],observation['health'],len(observation['coordinator_owned_calls']))
                        if not fits:
                            if jobs:continue
                            raise runtime.StopRun('Full request plus output does not fit conservative shared-pool reservation; no clipping or setting change')
                        call=runtime.reserve(state,task['id'],fingerprint(body))
                        task.pop('error',None);task.update(status='running',call=call['id'])
                        call['concurrency_binding']={'key':task['key'],'phase':task['phase'],'stage':phase,
                            'source_key':task['source_key'],'input_version':state.get('current_versions',{}).get(task['key']) if task['phase']=='critic' else None,
                            'input_version_sha256':state.get('versions',{}).get(task['key'],{}).get(state.get('current_versions',{}).get(task['key']),{}).get('sha256') if task['phase']=='critic' else None}
                        if trial:trial['calls'].append(call['id']);trial['status']='running'
                        state['stage']='concurrent_'+phase;save() # reservation durable BEFORE thread starts
                        future=pool.submit(transport,run,copy.deepcopy(call),body,continuous=True,admission_budget=budget,health_evidence=observation['evidence'])
                        jobs[future]=(call,task,body,budget);admitted=True
                    except protocol.ContextBudgetGap as exc:task.update(status='context_budget_gap',error=str(exc));save()
                    except BaseException as exc:stopped(exc);break
                if not admitted and not jobs and not stop:
                    save();break
                if jobs:wait(jobs,timeout=min(period,1),return_when=FIRST_COMPLETED)
    except BaseException as exc:
        stopped(exc)
        raise
    finally:
        time_account();session.update(finished_at=runtime.now(),finished_epoch=time.time())
        if stop and progress['phase'] in ('two','four'):
            trial=phase_record(progress,2 if progress['phase']=='two' else 4)
            if trial['status'] in ('running','pending','interrupted'):
                trial.update(status='interrupted',reason=str(stop),interrupted_at=session['finished_at'])
        save()


# Read-only, allowlisted container inspection. No environment dump, credentials,
# model-weight hashing, imports of the serving engine, or serving changes.
BUILD_PROGRAM = r'''
import hashlib, importlib.util, importlib.metadata, json, os
from pathlib import Path
spec=importlib.util.find_spec('tensorfold')
if spec is None: raise RuntimeError('Installed TensorFold package not found')
root=Path(spec.origin).parent
files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and p.suffix in ('.py','.jinja','.jinja2')}
source='\n'.join(p.read_text() for p in root.rglob('multi.py') if 'glm' in str(p))
cache_eviction_verified='self._evict(' in source and 'self.pool.free_rows()' in source and 'x.owner is None' in source
flags={};models={};processes=[]
allowed={'--context','--parallel','--max-tokens','--kv','--kv-format','--thinking','--no-thinking','--drafter','--policy','--model-alias','--served-model-name','--tp','--rank'}
for p in Path('/proc').iterdir():
 if not p.name.isdigit(): continue
 try: args=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
 except (OSError,PermissionError): continue
 if not args or Path(args[0]).name not in ('python','python3','tensorfold') or 'serve' not in args: continue
 # Exclude this diagnostic's source argument; require a TensorFold entrypoint.
 if not any(Path(a).name=='tensorfold' or a=='tensorfold' for a in args[:3]): continue
 observed={}
 for i,a in enumerate(args):
  if a in allowed: observed[a]=args[i+1] if i+1<len(args) and not args[i+1].startswith('--') else True
 i=args.index('serve');model=args[i+1] if i+1<len(args) else ''
 if model and not model.startswith('-'):
  folder=Path(model);models[model]={}
  for name in ('config.json','chat_template.jinja','chat_template.jinja2','tokenizer_config.json'):
   f=folder/name
   if f.is_file():models[model][name]=hashlib.sha256(f.read_bytes()).hexdigest()
 processes.append({'pid':int(p.name),'flags':observed,'model_path':model})
print(json.dumps({'tensorfold_version':importlib.metadata.version('tensorfold'),'installed_source_hashes':files,
 'cache_eviction_verified':cache_eviction_verified,'serving_processes':processes,'model_metadata_hashes':models,
 'selected_environment':{k:os.environ.get(k) for k in ('TF_GLM_CLEAR_THINKING','TF_GLM_KEEP_PER_CHAT','TF_GLM_KEEP_SHARED_POINTS','THINKING','ABLIT')}}))
'''


def capture_build(module,run):
    import shlex
    nodes=[]
    for node in ('head','peer'):
        def checked(argv):return module.checked(argv if node=='head' else module.peer(shlex.join(argv)))
        info={k:json.loads(checked(['docker','inspect','--format','{{json '+field+'}}',module.CONTAINER]))
              for k,field in (('image_id','.Image'),('image_name','.Config.Image'),('started_at','.State.StartedAt'))}
        info['installed']=json.loads(checked(['docker','exec',module.CONTAINER,'python','-c',BUILD_PROGRAM]));info['node']=node
        if not info['installed']['cache_eviction_verified'] or not info['installed']['serving_processes']:
            raise runtime.Fatal('Cannot verify running GLM cache reclamation/build; no concurrent dispatch on '+node)
        nodes.append(info)
    # PID/started-at may change only following an external operator action. The
    # immutable image + source/metadata/config record remains the comparison key.
    stable=[]
    for n in nodes:
        v=copy.deepcopy(n);v.pop('started_at');
        for p in v['installed']['serving_processes']:p.pop('pid')
        stable.append(v)
    identity=fingerprint(stable)
    saved=run/'concurrency-runtime-binding.json'
    if saved.exists() and read_json(saved)['identity']!=identity:raise runtime.Fatal('Running GLM build/settings changed since concurrency launch; no silent comparison across runtimes')
    if not saved.exists():atomic_json(saved,{'identity':identity,'nodes':nodes,'at':runtime.now()})
    return nodes
