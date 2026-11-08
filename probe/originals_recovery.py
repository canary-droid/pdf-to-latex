"""One authorized Low conversion and one syntax request per immutable lineage."""
import copy
import difflib
import json
from pathlib import Path
from . import tex_syntax_repair as syntax, chapter_glm as runtime, originals_selection as selection
from .common import atomic_json, read_json, sha, fingerprint, contained
from .experiment import seal, verify_seal

SOURCE='original-21debf82bc2c0a3d'
KEY=SOURCE+'-part-001'
LOW_CONVERT=KEY+'/convert-low-recovery-1'
LOW_CRITIC=KEY+'/critic-low-recovery-1'
SUPERSEDED=(KEY+'/convert',KEY+'/critic')
POLICY={'version':'originals-recovery-v1','syntax_attempts_per_lineage':1,'syntax_effort':'low',
        'syntax_max_tokens':8192,'low_conversion_attempts':1,'low_conversion_max_tokens':131072,
        'normal_conversion_effort':'high','critic_effort':'max','global_limit':None}
HANDOFF_FILES={'scripts/originals_batch.py','probe/originals_selection.py',
               'probe/originals_recovery.py','probe/tex_syntax_repair.py','probe/originals_review.py','probe/originals_mineru_only.py','probe/originals_mineru_high.py'}
CONTENT_FAILURES={'syntax_failure','missing_context_or_macro','wrong_engine_or_encoding','build_failure_unresolved'}


def prepare(ctrl,run,repairs):
    """Link onto the actual selected exclusion continuation, after a full drain."""
    from .common import writer_lock, files_manifest
    from . import source_library
    import shutil,time
    if Path(read_json(ctrl.POINTER)['run']).resolve()!=run.resolve():raise runtime.Fatal('Not the current selected batch')
    if not all(ctrl.books.speed.idle(p) for p in (ctrl.ROOT,ctrl.ROOT/'runs',run)):raise runtime.Fatal('Worker must drain before recovery integration')
    with writer_lock(ctrl.ROOT),writer_lock(ctrl.ROOT/'runs'),writer_lock(run):
        state=ctrl.verify(run,recovery_handoff=True)
        if state.get('recovery_continuation'):
            ctrl.verify(run);return state['recovery_continuation']
        if state['status']!='paused' or state['resource_phase']!='glm_only' or not state.get('selection_continuation'):
            raise runtime.Fatal('Expected paused current GLM selection continuation')
        if any(c['status']=='in_progress' for c in state['calls']):raise runtime.Fatal('Unsettled requests cannot be replayed')
        for c in state['calls']:verify_seal(run/'calls'/c['id'],c['seal'])
        incoming=read_json(repairs/'index.json')
        if {x['key'] for x in incoming}!={'original-a82e7fbca0ccd9bd-part-001','original-717c892239361a44-part-001','original-496de5aa992285e2-part-001'}:
            raise runtime.Fatal('Unexpected initial saved repair set')
        for item in incoming:
            source=repairs/item['key'];verify_seal(source)
            v=state['versions'][item['key']][state['current_versions'][item['key']]]
            if v['sha256']!=item['base_sha256'] or sha(run/v['path'])!=v['sha256']:raise runtime.Fatal('Saved repair anchor/version changed')
            text=(run/v['path']).read_text();new,edits=syntax.deterministic(text,first_error(run,v))
            if not edits or syntax.digest(new)!=item['new_sha256'] or new!=(source/'document.tex').read_text():raise runtime.Fatal('Initial repair is not the approved exact syntax derivative')
            if not item['result']['status'].startswith('passed') or item['result']['input_sha256']!=item['new_sha256']:
                raise runtime.Fatal('Initial derivative lacks a passing exact-input build')
        tasks=low_tasks(run,state);folder=run/'continuations'/('recovery-'+str(time.time_ns()));folder.mkdir(parents=True)
        old_path=run/state.get('binding_path','binding.json');old=selection.binding(run,state)
        source_library.copy_verified(run/'state.json',folder/'prior-state.json');source_library.copy_verified(old_path,folder/'prior-binding.json')
        for item in incoming:shutil.copytree(repairs/item['key'],folder/'prepared-syntax'/item['key'])
        auth={'at':runtime.now(),'policy':POLICY,'low_tasks':[frozen(t) for t in tasks],
              'historical_low_parent':'call-030','initial_saved_repairs':incoming,
              'deferred_sources':state['deferred_sources'],'preserved_call_count':len(state['calls']),
              'intent':'Only approved Low recovery and syntax-only repairs; no OCR, scope additions, service changes or mathematical acceptance.'}
        atomic_json(folder/'authorization.json',auth)
        frozen_inputs={**old['frozen'],str(old_path):sha(old_path)}
        frozen_inputs.update({str(folder/e['path']):e['sha256'] for e in files_manifest(folder)})
        binding={**old,'code':ctrl.code_hashes(),'frozen':frozen_inputs,'linked_parent_binding_sha256':sha(old_path)}
        atomic_json(folder/'binding.json',binding);seal(folder)
        state.update(recovery_continuation={'path':str(folder.relative_to(run)),'seal':sha(folder/'manifest.json')},
                     binding_path=str((folder/'binding.json').relative_to(run)),binding_sha256=fingerprint(binding),
                     recovery_policy=copy.deepcopy(POLICY),syntax_lineages={})
        state['tasks'].extend(tasks)
        state['production_stage']['task_ids']=[t for t in state['production_stage']['task_ids'] if t not in SUPERSEDED]
        state['production_stage']['task_ids'].extend(t['id'] for t in tasks)
        for item in incoming:
            key=item['key'];parent=item['base_label'];lineage=fingerprint([key,item['base_sha256']]);label='syntax-initial-'+item['new_sha256'][:16]
            v=register_derivative(ctrl,run,state,key,parent,(repairs/key/'document.tex').read_text(),label,lineage,item['edits'])
            attempt=copy.deepcopy(item['result']);attempt['path']=str((folder/'prepared-syntax'/key/'build').relative_to(run))
            v['compilation']={'status':attempt['status'],'attempts':[attempt],'document_changed':True,'model_repair_requested':False}
            state['syntax_lineages'][lineage]={'key':key,'source_key':state['source_units'][key]['source_key'],
                'root_sha256':item['base_sha256'],'root_label':parent,'status':'deterministic_repaired','deterministic_version':label}
            select_version(ctrl,run,state,key,label,save=False)
        runtime.save(run,state);ctrl.verify(run);ctrl.progress(run,state)
        return state['recovery_continuation']


def frozen(task):
    return {k:v for k,v in task.items() if k in ('id','key','source_key','phase','reasoning_effort',
            'section','context','preview_hash','recovery_kind','repair_lineage','base_label','base_sha256','plan_path','depends_on')}


def low_tasks(run,state):
    original=next(t for t in state['tasks'] if t['id']==KEY+'/convert')
    old=next(c for c in state['calls'] if c['id']=='call-030')
    if old['parent']!=original['id'] or old.get('failure_kind')!='truncation':raise runtime.Fatal('Historical Low-recovery anchor differs')
    if selection.deferred(state,SOURCE):raise runtime.Fatal('Low recovery source is deferred')
    body=read_json(run/'calls/call-030/request.json')
    if fingerprint(body)!=old['request_sha256'] or body.get('reasoning_effort')!='high' or body.get('max_tokens')!=131072:
        raise runtime.Fatal('Historical conversion request changed')
    tasks=[]
    for phase,ident,effort in [('convert',LOW_CONVERT,'low'),('critic',LOW_CRITIC,'max')]:
        t={k:copy.deepcopy(original[k]) for k in ('key','source_key','section','context') if k in original}
        t.update(id=ident,phase=phase,reasoning_effort=effort,status='pending',recovery_kind='low_conversion',
                 depends_on=LOW_CONVERT if phase=='critic' else None,draft_label=None,attempt_limit=1)
        if phase=='convert':t['preview_hash']=fingerprint(dict(body,reasoning_effort='low'))
        tasks.append(t)
    return tasks


def extra_ids(run,state):
    """Validate every extra admission against the sealed authorization or lineage."""
    continuation=state.get('recovery_continuation')
    if not continuation:return []
    folder=contained(run,continuation['path']);verify_seal(folder,continuation['seal'])
    auth=read_json(folder/'authorization.json');prior=read_json(folder/'prior-state.json')
    if auth['policy']!=POLICY or state.get('recovery_policy')!=POLICY:raise runtime.Fatal('Recovery policy changed')
    if state['calls'][:len(prior['calls'])]!=prior['calls']:raise runtime.Fatal('Consumed historical calls changed')
    if state['deferred_sources']!=prior['deferred_sources'] or state['selection_continuation']!=prior['selection_continuation']:
        raise runtime.Fatal('Recovery changed source exclusions')
    if state['execution_limits']!=prior['execution_limits']:raise runtime.Fatal('Recovery reset execution allowances')
    if not state.get('mineru_only_continuation') and sha(contained(run,state['binding_path']))!=sha(folder/'binding.json'):raise runtime.Fatal('Recovery binding changed')
    prior_binding=read_json(folder/'prior-binding.json')
    selected_binding=read_json(contained(run,state['selection_continuation']['path'])/'binding.json')
    if prior_binding!=selected_binding:raise runtime.Fatal('Recovery does not link the selected exclusion binding')
    tasks={t['id']:t for t in state['tasks']};allowed=[]
    for definition in auth['low_tasks']:
        if frozen(tasks[definition['id']])!=definition:raise runtime.Fatal('Low recovery scope/settings changed')
        allowed.append(definition['id'])
    roots=set()
    for lineage,row in state.get('syntax_lineages',{}).items():
        if lineage!=fingerprint([row['key'],row['root_sha256']]) or lineage in roots:raise runtime.Fatal('Invalid repair lineage')
        roots.add(lineage)
        if row.get('task_id'):
            task=tasks[row['task_id']];plan_dir=contained(run,row['plan_path']);verify_seal(plan_dir,row['plan_seal'])
            data=read_json(plan_dir/'plan.json')
            if data['task']!=frozen(task) or data['root_sha256']!=row['root_sha256']:raise runtime.Fatal('Syntax task changed')
            if task['plan_seal']!=row['plan_seal']:raise runtime.Fatal('Syntax plan seal changed')
            if row['task_id']!=row['key']+'/syntax-'+lineage[:20]:raise runtime.Fatal('Repair allowance alias changed')
            if sha(run/state['versions'][row['key']][task['base_label']]['path'])!=task['base_sha256']:raise runtime.Fatal('Syntax input changed')
            allowed.append(row['task_id'])
    if state.get('mineru_only_continuation'):
        from .originals_mineru_only import verify
        allowed += verify(run,state)
    if state.get('mineru_high_continuation'):
        from .originals_mineru_high import verify
        allowed += verify(run,state)
    if any(t.get('recovery_kind') and t['id'] not in allowed for t in state['tasks']):raise runtime.Fatal('Unauthorized recovery task')
    if any(sum(c['parent']==ident for c in state['calls'])>1 for ident in allowed):raise runtime.Fatal('Recovery allowance exceeded')
    if len({t['id'] for t in state['tasks']})!=len(state['tasks']):raise runtime.Fatal('Duplicate task identities')
    return [t['id'] for t in state['tasks'] if t['id'] in set(allowed)]


def effective_tasks(state, source):
    tasks=[t for t in state['tasks'] if t['source_key']==source and t['phase'] in ('convert','critic')]
    if state.get('mineru_high_continuation') and source==SOURCE:
        return [t for t in tasks if t.get('recovery_kind')=='mineru_high']
    if state.get('mineru_only_continuation') and source==SOURCE:
        return [t for t in tasks if t.get('recovery_kind')=='mineru_only']
    if state.get('recovery_continuation') and source==SOURCE:
        tasks=[t for t in tasks if t['id'] not in (KEY+'/convert',KEY+'/critic')]
    return tasks


def body_for(ctrl,run,state,task):
    if task.get('recovery_kind')=='mineru_high':
        from .originals_mineru_high import request
        return request(ctrl,run,state,task)
    if task.get('recovery_kind')=='mineru_only':
        from .originals_mineru_only import request
        return request(ctrl,run,state,task)
    if task.get('recovery_kind')=='syntax':return read_json(run/task['plan_path']/'request.json')
    if task['id']==LOW_CONVERT:
        return dict(read_json(run/'calls/call-030/request.json'),reasoning_effort='low')
    return ctrl.books.request_for(run,state,task)


def before_reserve(ctrl,run,state,task,body):
    if task.get('recovery_kind')=='mineru_high':
        from .originals_mineru_high import before_reserve as guard
        return guard(ctrl,run,state,task,body)
    if task.get('recovery_kind')=='mineru_only':
        from .originals_mineru_only import before_reserve as guard
        return guard(ctrl,run,state,task,body)
    if not task.get('recovery_kind'):return ctrl.books.before_reserve(run,state,task,body)
    if task['status']!='pending' or any(c['parent']==task['id'] for c in state['calls']):raise runtime.Fatal('Recovery allowance consumed')
    if task['id'] not in extra_ids(run,state):raise runtime.Fatal('Unapproved recovery reservation')
    if task['phase']=='critic':return ctrl.books.before_reserve(run,state,task,body)
    live=read_json(run/'effort-support-live.json')
    if live.get('low_supported') is not True:raise runtime.Fatal('Installed Low template support is unverified')
    if body!=body_for(ctrl,run,state,task):raise runtime.Fatal('Recovery request changed')
    if task['id']==LOW_CONVERT:
        old=read_json(run/'calls/call-030/request.json')
        if body!=dict(old,reasoning_effort='low'):raise runtime.Fatal('Low recovery changed more than effort')
    elif body['max_tokens']!=8192 or body['reasoning_effort']!='low':raise runtime.Fatal('Syntax repair budget/settings changed')


def first_error(run,version):
    for at in reversed(version.get('compilation',{}).get('attempts',[])):
        p=run/at['path']/'console.log'
        if p.exists():return syntax.first_error(p.read_text())
    return None


def select_version(ctrl,run,state,key,label,*,save=True):
    state['current_versions'][key]=label;v=state['versions'][key][label]
    row=next(r for r in state['selection_ledger'] if r['unit']==key)
    row.update(selection=label,version_sha256=v['sha256'],syntax_only_derivative=True)
    # Syntax-only edits preserve all existing source/accuracy dispositions.
    if save:runtime.save(run,state)


def register_derivative(ctrl,run,state,key,parent,text,label,lineage,edits):
    before=(run/state['versions'][key][parent]['path']).read_text()
    ctrl.books.remember(run,state,key,label,text,{'syntax_parent':parent,'syntax_lineage':lineage,
                                                'content_policy':'syntax only; mathematical claims unverified'})
    folder=run/'syntax-repairs'/key/label
    ctrl.books.safe_write(folder/'patch.json',json.dumps(edits,indent=2)+'\n')
    ctrl.books.safe_write(folder/'change.diff',''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile=parent,tofile=label)))
    return state['versions'][key][label]


def queue_repairs(ctrl,run,state):
    """Coordinator-only admission: one lineage per selected model version."""
    if not state.get('recovery_continuation'):return
    for key,label in list(state['current_versions'].items()):
        source=state['source_units'][key]['source_key']
        if selection.deferred(state,source):continue
        relevant=[t for t in effective_tasks(state,source) if t['key']==key]
        if any(t['status'] in ('pending','running') for t in relevant):continue
        v=state['versions'][key][label]
        if v.get('compilation',{}).get('status') not in CONTENT_FAILURES:continue
        lineage=v['origin'].get('syntax_lineage') or fingerprint([key,v['sha256']])
        existing=state.setdefault('syntax_lineages',{}).get(lineage)
        if existing and (existing.get('task_id') or existing['status']!='deterministic_check'):continue
        error=first_error(run,v)
        if not error:continue
        row={'key':key,'source_key':source,'root_sha256':v['sha256'],'root_label':label,'status':'deterministic_check'}
        if existing:row=existing
        state['syntax_lineages'][lineage]=row;runtime.save(run,state)
        text=(run/v['path']).read_text()
        try:new,edits=syntax.deterministic(text,error)
        except ValueError:new,edits=text,[]
        if edits:
            derivative='syntax-deterministic-'+lineage[:16]
            candidate=register_derivative(ctrl,run,state,key,label,new,derivative,lineage,edits)
            ctrl.compile_version(run,state,key,derivative)
            row['deterministic_version']=derivative
            if candidate['compilation']['status'].startswith('passed'):
                select_version(ctrl,run,state,key,derivative);row['status']='deterministic_repaired';runtime.save(run,state);continue
            label=derivative;v=candidate;text=new;error=first_error(run,v)
        if not error:
            row['status']='unresolved_without_precise_error';runtime.save(run,state);continue
        try:scope=syntax.scope_for(text,error)
        except ValueError as exc:
            row.update(status='unresolved_context',error=str(exc));runtime.save(run,state);continue
        ident=key+'/syntax-'+lineage[:20];folder=run/'syntax-tasks'/lineage
        task={'id':ident,'key':key,'source_key':source,'phase':'syntax','status':'pending','reasoning_effort':'low',
              'recovery_kind':'syntax','repair_lineage':lineage,'base_label':label,'base_sha256':v['sha256'],
              'plan_path':str(folder.relative_to(run)),'depends_on':None}
        request=syntax.request(text,scope);task['preview_hash']=fingerprint(request)
        definition={'task':frozen(task),'root_sha256':row['root_sha256']}
        if (folder/'manifest.json').exists():
            verify_seal(folder)
            if read_json(folder/'plan.json')!=definition or read_json(folder/'request.json')!=request:raise runtime.Fatal('Recovered syntax plan differs')
        else:
            atomic_json(folder/'scope.json',scope);atomic_json(folder/'request.json',request)
            atomic_json(folder/'plan.json',definition);seal(folder)
        task['plan_seal']=sha(folder/'manifest.json')
        row.update(task_id=ident,plan_path=task['plan_path'],plan_seal=task['plan_seal'],status='pending')
        state['tasks'].append(task);state['production_stage']['task_ids'].append(ident);runtime.save(run,state)


def finish_syntax(ctrl,run,state,task,answer,call):
    if task.get('settled_call')==call['id']:return
    row=state['syntax_lineages'][task['repair_lineage']];task['call']=call['id']
    if answer is None:task.update(status='syntax_request_failed',error=call.get('error'))
    else:
        try:
            base=state['versions'][task['key']][task['base_label']];text=(run/base['path']).read_text()
            new,record=syntax.apply_response(text,read_json(run/task['plan_path']/'scope.json'),answer)
            label='syntax-'+call['id'];v=register_derivative(ctrl,run,state,task['key'],task['base_label'],new,label,task['repair_lineage'],record)
            ctrl.compile_version(run,state,task['key'],label)
            if v['compilation']['status'].startswith('passed'):
                select_version(ctrl,run,state,task['key'],label);task.update(status='syntax_repaired',final_version=label)
            else:task.update(status='syntax_still_uncompiled',candidate_version=label)
        except ValueError as exc:task.update(status='syntax_patch_rejected',error=str(exc))
    task['settled_call']=call['id'];row.update(status=task['status'],call=call['id']);runtime.save(run,state)


def offline_low_proposal(run,state):
    if state.get('mineru_only_continuation'):return  # Preserve the earlier dual-source failure proposal.
    task=next((t for t in state['tasks'] if t['id']==LOW_CONVERT),None)
    if not task or task['status'] in ('pending','running','conversion_completed'):return
    native=read_json(run/'inputs'/SOURCE/'native.json');ids=task['section']['blocks'];blocks=[b for b in native['blocks'] if b['id'] in set(ids)]
    import re
    from .book_completion import plain
    starts=[i for i,b in enumerate(blocks) if re.match(r'^case\s+\d+\b',plain(b['tex']))]
    boundaries=sorted(set([0,*starts,len(blocks)]));groups=[]
    for a,b in zip(boundaries,boundaries[1:]):
        if a<b:groups.append({'blocks':[x['id'] for x in blocks[a:b]],'pages':sorted({x['page']['original_physical_page'] for x in blocks[a:b]}),'opening':blocks[a]['tex'][:250]})
    atomic_json(run/'low-recovery/offline-case-proposal.json',{'status':'offline_only_not_scheduled','historical_high_call':'call-030',
        'low_call':task.get('call'),'source_sha256':state['documents'][SOURCE]['source_sha256'],'groups':groups,
        'requirement':'Review case boundaries against source: each density, characteristic function and ALL parameter conditions must remain together. Group adjacent cases with needed definitions; no automatic dispatch or extra allowance.'})
