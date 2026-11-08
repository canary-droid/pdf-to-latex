"""Explicit High/Max MinerU-only rerun, gated by the existing syntax job."""
import copy
import time
from pathlib import Path
from . import originals_recovery as recovery, originals_mineru_only as mineru, chapter_glm as runtime
from . import originals_selection as selection
from .common import read_json, atomic_json, sha, fingerprint, contained, writer_lock, files_manifest
from .experiment import seal, verify_seal
from .source_library import copy_verified

CONVERT=recovery.KEY+'/convert-mineru-high-1'
CRITIC=recovery.KEY+'/critic-mineru-high-1'
IDS=(CONVERT,CRITIC)
POLICY={'source':recovery.SOURCE,'conversion_effort':'high','critic_effort':'max','max_tokens':131072,
        'source_layers':['saved_native_mineru'],'attempts_per_phase':1,'wait_for':'source syntax task settled or operator-cancelled'}
FINISHED={'syntax_repaired','syntax_patch_rejected','syntax_request_failed','syntax_still_uncompiled','context_budget_gap','low_support_unverified','cancelled_by_operator'}


def admitted(state,task):
    if state.get('mineru_high_continuation') and task['source_key']==recovery.SOURCE and task['phase'] in ('convert','critic'):
        return task.get('recovery_kind')=='mineru_high'
    return True


def ready(state,task):
    if task.get('recovery_kind')!='mineru_high':return True
    convert=next(t for t in state['tasks'] if t['id']==CONVERT)
    prerequisite=next(t for t in state['tasks'] if t['id']==convert['depends_on'])
    return prerequisite['status'] in FINISHED


def priority(state,task):
    if state.get('mineru_high_continuation'):
        convert=next(t for t in state['tasks'] if t['id']==CONVERT)
        if task['id']==convert['depends_on']:return 0
    if task.get('recovery_kind')=='mineru_high':return 1
    return 2 if task.get('recovery_kind') in ('mineru_only','low_conversion') else 3


def request(ctrl,run,state,task):
    if not ready(state,task):return None
    if task['phase']=='critic':
        convert=next(t for t in state['tasks'] if t['id']==CONVERT)
        if convert['status']!='conversion_completed':return None
    body=mineru.request(ctrl,run,state,task)
    if body is not None:body['reasoning_effort']='high' if task['phase']=='convert' else 'max'
    return body


def verify(run,state):
    c=state.get('mineru_high_continuation')
    if not c:return []
    folder=contained(run,c['path']);verify_seal(folder,c['seal'])
    auth=read_json(folder/'authorization.json');prior=read_json(folder/'prior-state.json')
    if auth['policy']!=POLICY:raise runtime.Fatal('High MinerU-only policy changed')
    if state['calls'][:len(prior['calls'])]!=prior['calls']:raise runtime.Fatal('Historical attempts changed')
    for name in ('mineru_only_continuation','recovery_continuation','selection_continuation','deferred_sources','execution_limits','phase_efforts','concurrency_policy','timing_policy','recovery_policy'):
        if state[name]!=prior[name]:raise runtime.Fatal('High rerun changed inherited state: '+name)
    parent=read_json(contained(run,state['mineru_only_continuation']['path'])/'binding.json')
    if read_json(folder/'prior-binding.json')!=parent:raise runtime.Fatal('Incorrect MinerU-only parent')
    if sha(contained(run,state['binding_path']))!=sha(folder/'binding.json'):raise runtime.Fatal('High rerun binding changed')
    tasks={t['id']:t for t in state['tasks']}
    if {t['id'] for t in auth['tasks']}!=set(IDS):raise runtime.Fatal('Unexpected High rerun tasks')
    for definition in auth['tasks']:
        if recovery.frozen(tasks[definition['id']])!=definition:raise runtime.Fatal('High rerun definition changed')
    prerequisite=tasks[tasks[CONVERT]['depends_on']]
    if prerequisite['source_key']!=recovery.SOURCE or prerequisite['phase']!='syntax':raise runtime.Fatal('Invalid syntax prerequisite')
    if recovery.frozen(prerequisite)!=auth['prerequisite']:raise runtime.Fatal('Syntax prerequisite changed')
    if any(sum(c['parent']==ident for c in state['calls'])>1 for ident in IDS):raise runtime.Fatal('High rerun allowance exceeded')
    if any(c['parent'] in IDS for c in state['calls']) and prerequisite['status'] not in FINISHED:raise runtime.Fatal('High rerun dispatched before syntax completion')
    return list(IDS)


def before_reserve(ctrl,run,state,task,body):
    if task['id'] not in verify(run,state) or not ready(state,task):raise runtime.Fatal('High rerun is not eligible')
    if task['status']!='pending' or any(c['parent']==task['id'] for c in state['calls']):raise runtime.Fatal('High rerun allowance consumed')
    if body!=request(ctrl,run,state,task):raise runtime.Fatal('High MinerU-only request changed')
    ctrl.books.before_reserve(run,state,task,body)


def prepare(ctrl,run):
    if Path(read_json(ctrl.POINTER)['run']).resolve()!=run.resolve():raise runtime.Fatal('Not current batch')
    if not all(ctrl.books.speed.idle(p) for p in (ctrl.ROOT,ctrl.ROOT/'runs',run)):raise runtime.Fatal('Drain the writer before High rerun integration')
    with writer_lock(ctrl.ROOT),writer_lock(ctrl.ROOT/'runs'),writer_lock(run):
        state=ctrl.verify(run,recovery_handoff=True)
        if state.get('mineru_high_continuation'):
            ctrl.verify(run);return state['mineru_high_continuation']
        if state['status']!='paused' or not state.get('mineru_only_continuation'):raise runtime.Fatal('Expected paused selected MinerU-only continuation')
        if any(c['status']=='in_progress' for c in state['calls']):raise runtime.Fatal('Requests remain unsettled')
        for call in state['calls']:verify_seal(run/'calls'/call['id'],call['seal'])
        prerequisite=[t for t in state['tasks'] if t['source_key']==recovery.SOURCE and t['phase']=='syntax']
        if len(prerequisite)!=1:raise runtime.Fatal('Ambiguous current syntax-review job')
        prerequisite=prerequisite[0]
        if prerequisite['status'] in ('pending','running') and any(c['parent']==prerequisite['id'] for c in state['calls']):
            raise runtime.Fatal('Syntax request was already reserved; preserve and reconcile it before cancellation')
        previous=next(t for t in state['tasks'] if t['id']==mineru.CONVERT)
        if previous['status']!='conversion_completed':raise runtime.Fatal('Expected saved usable Low comparison draft')
        # Hash every existing comparison version; never discard a good Low result.
        for v in state['versions'][recovery.KEY].values():
            if sha(run/v['path'])!=v['sha256']:raise runtime.Fatal('Comparison version changed; preserve and reconcile before rerun')
        tasks=[]
        for phase,ident in [('convert',CONVERT),('critic',CRITIC)]:
            t={k:copy.deepcopy(previous[k]) for k in ('key','source_key','section')}
            t.update(id=ident,phase=phase,reasoning_effort='high' if phase=='convert' else 'max',status='pending',context='',
                     draft_label=None,depends_on=prerequisite['id'] if phase=='convert' else CONVERT,recovery_kind='mineru_high',attempt_limit=1)
            if phase=='convert':
                body=mineru.request(ctrl,run,state,t);body['reasoning_effort']='high';t['preview_hash']=fingerprint(body)
            tasks.append(t)
        folder=run/'continuations'/('mineru-high-'+str(time.time_ns()));folder.mkdir(parents=True)
        old=selection.binding(run,state);old_path=run/state['binding_path']
        copy_verified(run/'state.json',folder/'prior-state.json');copy_verified(old_path,folder/'prior-binding.json')
        atomic_json(folder/'authorization.json',{'at':runtime.now(),'policy':POLICY,'tasks':[recovery.frozen(t) for t in tasks],
                    'prerequisite':recovery.frozen(prerequisite),'preserved_calls':len(state['calls']),
                    'preserved_low_versions':copy.deepcopy(state['versions'][recovery.KEY]),
                    'operator_cancellation':{'task':prerequisite['id'],'reason':'Operator repaired the TeX manually; cancel queued syntax request without spending its model allowance'}})
        body=mineru.request(ctrl,run,state,tasks[0]);body['reasoning_effort']='high';atomic_json(folder/'conversion-request.json',body)
        frozen={**old['frozen'],str(old_path):sha(old_path)}
        frozen.update({str(folder/e['path']):e['sha256'] for e in files_manifest(folder)})
        b={**old,'code':ctrl.code_hashes(),'frozen':frozen,'linked_parent_binding_sha256':sha(old_path)}
        atomic_json(folder/'binding.json',b);seal(folder)
        state.update(mineru_high_continuation={'path':str(folder.relative_to(run)),'seal':sha(folder/'manifest.json')},
                     binding_path=str((folder/'binding.json').relative_to(run)),binding_sha256=fingerprint(b))
        if prerequisite['status']=='pending':
            prerequisite.update(status='cancelled_by_operator',cancellation_reason='Operator repaired the TeX manually')
            state['syntax_lineages'][prerequisite['repair_lineage']].update(status='cancelled_by_operator',reason='Operator repaired the TeX manually')
        state['tasks'].extend(tasks);state['production_stage']['task_ids'].extend(IDS)
        runtime.save(run,state);ctrl.verify(run);ctrl.progress(run,state)
        return state['mineru_high_continuation']
