#!/usr/bin/env python3
"""Persistent, frozen-originals collection using the qualified local pipeline."""
import argparse
import copy
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'scripts'))
from scripts import book_completion as books
from probe import source_library as library, cli, chapter_inputs, chapter_sources
from probe import originals_selection as selection
from probe import originals_recovery as recovery, originals_review, originals_mineru_high as mineru_high
from probe import book_completion as scope, chapter_concurrency as concurrent
from probe import chapter_glm as runtime, chapter_protocol, compiler_environment, tex_compile
from probe.common import atomic_json, read_json, sha, fingerprint, files_manifest, writer_lock
from probe.experiment import InputGuard, verify_seal, seal
from probe.batch_review import IntegrityError

PYTHON = ROOT/'.venv-control/bin/python'
ORIGINALS = Path('/home/mdi/llm-wiki/originals')
INTAKE = ORIGINALS.parent/'source-intake-20261029T102944Z'
LIBRARY = ORIGINALS.parent/'sources'
POINTER = ROOT/'results/originals-batch-current.json'
SESSION = 'pdf-originals-batch'
TERMINAL = 'collection_finished_with_report'


def code_hashes():
    paths = list((ROOT/'probe').glob('*.py')) + list((ROOT/'scripts').glob('*.py'))
    paths += [Path(__file__), ROOT/'scripts/run-originals-batch.sh', ROOT/'config.example.json']
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths))}


def prepare():
    if POINTER.exists():
        run = Path(read_json(POINTER)['run']); verify(run)
        print('Existing frozen collection retained:', run); return run
    if not books.speed.idle(ROOT):
        raise runtime.Fatal('Another project writer is active; no preparation')
    with writer_lock(ROOT):
        manifest = library.inventory(ORIGINALS, INTAKE)
        run = chapter_inputs.new_path('originals-batch'); run.mkdir(parents=True)
        atomic_json(run/'collection.json', manifest)
        reuse = []
        originals_hashes = {d['sha256'] for d in manifest['documents']}
        # Discovery is evidence, not permission to replay an old run. Matching
        # saved scope must be explicitly verified before it can be adopted.
        for p in sorted((ROOT/'runs').glob('convert-*/state.json')):
            s = read_json(p)
            reuse.append({'run': str(p.parent), 'state_sha256': sha(p), 'status': s['status'],
                          'matching_sources': [k for k,v in s['settings']['sources'].items() if v['sha256'] in originals_hashes]})
        if any(r['matching_sources'] for r in reuse):
            raise runtime.Fatal('Matching saved extraction discovered; reconcile scope/assets before new preparation: '+str(run))
        atomic_json(run/'reuse-audit.json', {'extractions': reuse, 'reused': 0,
                    'reason': 'No full SHA256 matches in saved native runs. Older wiki summaries are not conversions.',
                    'books': 'Gatheral/Bergomi hashes are outside this frozen originals collection; no replay.'})
        parent = Path(read_json(ROOT/'results/book-finalisation-current.json')['run'])
        ps = read_json(parent/'state.json'); env = copy.deepcopy(ps['compiler_environment'])
        verify_seal(parent/env['path'], env['seal']); shutil.copytree(parent/env['path'],run/env['path'])
        effort_parent = Path(read_json(ROOT/'results/overnight-suite-current.json')['run'])
        library.copy_verified(effort_parent/'effort-support-offline.json', run/'effort-support-offline.json')
        state = {'status': 'prepared_offline', 'stage': 'prepared; not running', 'created_at': runtime.now(),
                 'suite_protocol': library.PROTOCOL, 'chapter_contract': books.edit.VERSION,
                 'timing_policy': 'manual_only', 'first_dispatch': None, 'calls': [], 'tasks': [],
                 'versions': {}, 'current_versions': {}, 'accuracy': {}, 'accuracy_records': {},
                 'source_units': {}, 'selection_ledger': [], 'compiler_environment': env,
                 'connection_failures': 0, 'phase_efforts': dict(scope.EFFORTS),
                 'execution_limits': {'calls': None, 'attempts_per_unit': 1},
                 'concurrency_policy': copy.deepcopy(concurrent.POLICY), 'active_stage': 1,
                 'stages': {'1': {'status': 'pending'}}, 'launches': [], 'documents': {},
                 'production_stage': {'name': 'frozen-originals-only', 'task_ids': []},
                 'resource_phase': 'not_started', 'smoke': None}
        for d in manifest['documents']:
            path = run/'originals'/d['source_id']/'original.pdf'
            library.copy_verified(d['originals'][0]['path'],path,d['sha256'])
            state['documents'][d['source_id']] = {'status': 'pending_extraction', 'original': str(path.relative_to(run)),
                 'source_sha256': d['sha256'], 'pages': d['page_count'], 'extraction': None, 'units': [],
                 'conversion': 'not_started', 'model_review': 'not_started', 'compilation': 'not_started',
                 'source_verification': 'not independently established'}
        frozen = {str(p):sha(p) for p in [run/'collection.json',run/'reuse-audit.json',run/'effort-support-offline.json']}
        frozen.update({str(run/r['original']):r['source_sha256'] for r in state['documents'].values()})
        binding = {'code':code_hashes(), 'frozen':frozen, 'library':str(LIBRARY)}
        atomic_json(run/'binding.json',binding); state['binding_sha256'] = fingerprint(binding)
        runtime.save(run,state); atomic_json(POINTER,{'run':str(run),'prepared':True,'running':False})
        progress(run,state)
        print('PREPARED, NOT RUNNING:',run, 'sources:',manifest['unique_sources'],'pages:',manifest['pages'])
        return run


def verify(run, *, selection_handoff=False, recovery_handoff=False):
    state = read_json(run/'state.json'); b = selection.binding(run,state)
    current_code = code_hashes()
    changed = {p for p in set(current_code) | set(b['code']) if current_code.get(p) != b['code'].get(p)}
    permitted = (selection_handoff and changed <= selection.HANDOFF_FILES) or (recovery_handoff and changed <= recovery.HANDOFF_FILES)
    if state['suite_protocol'] != library.PROTOCOL or state['binding_sha256'] != fingerprint(b) or (changed and not permitted):
        raise runtime.Fatal('Frozen collection/code identity changed; no reset, replay or new preparation')
    selection.verify(run,state)
    InputGuard(b['frozen']).check()
    if b['library'] != str(LIBRARY):
        raise runtime.Fatal('Publication root changed')
    for doc in state['documents'].values():
        if doc.get('plan'):
            if sha(run/doc['plan']) != doc['plan_sha256']:
                raise runtime.Fatal('Source plan changed')
            plan=read_json(run/doc['plan']); verify_seal(run/plan['prepared_input'],plan['input_seal'])
            verify_seal(run/plan['dispatch_input'],plan['dispatch_input_seal'])
            InputGuard({str(run/'inputs'/a):h for a,h in plan['assets'].items()}).check()
            tasks=[t for t in state['tasks'] if t['source_key']==plan['source_id'] and not t.get('recovery_kind')]
            if fingerprint(books.frozen_tasks({'tasks':tasks})) != plan['task_fingerprint']:
                raise runtime.Fatal('Frozen task scope changed')
    return state


def prepare_deferrals(run):
    """Append a linked selection binding after a supported, fully drained handoff."""
    if Path(read_json(POINTER)['run']).resolve()!=run.resolve():
        raise runtime.Fatal('Not the current collection')
    if not all(books.speed.idle(p) for p in (ROOT,ROOT/'runs',run)):
        raise runtime.Fatal('Drain the current writer before selection changes')
    with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):
        state=verify(run,selection_handoff=True)
        if state.get('selection_continuation'):
            verify(run);print('Existing selection retained; no reset:',run);return
        if state['status']!='paused' or state['resource_phase']!='glm_only' or not state.get('plans_complete'):
            raise runtime.Fatal('Selection handoff requires paused, prepared GLM phase')
        if any(c['status']=='in_progress' for c in state['calls']):
            raise runtime.Fatal('Unsettled reservation; no selection change')
        known={c['id'] for c in state['calls']}
        if any(p.name not in known for p in (run/'calls').glob('call-*')):
            raise runtime.Fatal('Unreconciled call directory; no selection change')
        for call in state['calls']:
            if not call.get('seal'):raise runtime.Fatal('Unsealed inherited call')
            verify_seal(run/'calls'/call['id'],call['seal'])
        for versions in state['versions'].values():
            for v in versions.values():
                if sha(run/v['path'])!=v['sha256']:raise runtime.Fatal('Changed inherited model output')
        manifest=read_json(run/'collection.json');library.verify_originals(manifest)
        rows=selection.decisions(manifest,state)
        if not any(r['decision']=='deferred' for r in rows):
            raise runtime.Fatal('No eligible sources; no continuation created')
        old=selection.binding(run,state)
        folder=run/'continuations'/('arxiv-selection-'+str(time.time_ns()));folder.mkdir(parents=True)
        library.copy_verified(run/'state.json',folder/'prior-state.json')
        old_path=run/state.get('binding_path','binding.json')
        library.copy_verified(old_path,folder/'prior-binding.json')
        record={'at':runtime.now(),'reason':selection.REASON,'inventory_sha256':sha(run/'collection.json'),
                'inventory_documents':len(manifest['documents']),'candidates':rows,
                'included':len(manifest['documents'])-sum(r['decision']=='deferred' for r in rows),
                'deferred':sum(r['decision']=='deferred' for r in rows),
                'inherited_calls':len(state['calls']),'policy':'No call/attempt reset; original inventory and bindings remain immutable.'}
        atomic_json(folder/'selection.json',record)
        frozen={**old['frozen'],str(old_path):sha(old_path)}
        for name in ('prior-state.json','prior-binding.json','selection.json'):frozen[str(folder/name)]=sha(folder/name)
        binding={**old,'code':code_hashes(),'frozen':frozen,'linked_parent_binding_sha256':sha(old_path)}
        atomic_json(folder/'binding.json',binding);seal(folder)
        selection.apply(state,rows)
        state.update(binding_path=str((folder/'binding.json').relative_to(run)),binding_sha256=fingerprint(binding),
                     selection_continuation={'path':str(folder.relative_to(run)),'seal':sha(folder/'manifest.json')},
                     stage='Selection updated; paused pending validated resume')
        runtime.save(run,state);verify(run);progress(run,state)
        print(json.dumps(record,indent=2))


def check_pause(run):
    books.check_pause(run)


def progress(run,state):
    counts=Counter(selection.document_status(state,k) for k in state['documents'])
    calls=[c for c in state['calls'] if c['parent']!='readiness']
    durations=[c['elapsed_seconds'] for c in calls if c.get('elapsed_seconds') and c['status']=='completed_response']
    pending=sum(t['status']=='pending' for t in state['tasks'])
    median=sorted(durations)[len(durations)//2] if durations else None
    record={'at':runtime.now(),'run':str(run),'status':state['status'],'phase':state.get('stage'),
            'resource_phase':state['resource_phase'],'documents':len(state['documents']),'counts':dict(counts),
            'included_documents':len(state['documents'])-len(state.get('deferred_sources',{})),
            'deferred_documents':len(state.get('deferred_sources',{})), 'deferred_sources':state.get('deferred_sources',{}),
            'active':[t['id'] for t in state['tasks'] if t['status']=='running'], 'reused_documents':0,
            'reused_ocr_windows':state.get('reused_ocr_windows',0),'calls':len(state['calls']),
            'failures':{k:v.get('error',v['status']) for k,v in state['documents'].items() if not selection.deferred(state,k) and ('fail' in v['status'] or 'gap' in v['status'])},
            'settings':{'model':'glm53-regular','conversion':'high','critic':'max','max_tokens':131072,'maximum_concurrent':2},
            'request_seconds':sum(durations),'remaining_requests':pending if state.get('plans_complete') else None,
            'estimate':{'median_observed_request_seconds':median,
                        'ideal_two_slot_remaining_hours':median*pending/7200 if median and state.get('plans_complete') else None,
                        'serial_remaining_hours':median*pending/3600 if median and state.get('plans_complete') else None,
                        'uncertainty':'Different document sizes, output lengths, OCR/build overhead and failures; not a deadline. No ETA until observations.'},
            'smoke':state.get('smoke'),'diagnostic':state.get('diagnostic'),'library':str(LIBRARY),
            'recovery':{'low':[{'id':t['id'],'status':t['status'],'call':t.get('call')} for t in state['tasks'] if t.get('recovery_kind') in ('low_conversion','mineru_only','mineru_high')],
                        'syntax_counts':dict(Counter(t['status'] for t in state['tasks'] if t.get('recovery_kind')=='syntax'))},
            'log':str(run/'terminal.log'),'inspection':state.get('inspection')}
    record['usage']={key:sum(c.get('metadata',{}).get('usage',{}).get(key,0) or 0 for c in calls) for key in ('prompt_tokens','completion_tokens','total_tokens')}
    atomic_json(run/'progress.json',record)
    atomic_json(ROOT/'results/originals-batch'/('progress-'+run.name+'.json'),record)


def helper_hashes(helpers):
    paths=[helpers.GLM/'start.sh',helpers.GLM/'stop.sh']+sorted((helpers.GLM/'scripts').glob('*.sh'))
    if (helpers.GLM/'.env').exists():paths.append(helpers.GLM/'.env')  # Hash only; never export secret contents.
    return {str(p):sha(p) for p in paths}


def resource_handoff(run,state,helpers):
    """Only the documented, owned idle GLM deployment may be stopped/restarted."""
    binding=run/'service-helper-binding.json'; current=helper_hashes(helpers)
    if binding.exists() and read_json(binding)!=current:
        raise runtime.Fatal('Documented service helper configuration changed; no handoff')
    if not binding.exists():atomic_json(binding,current)
    pending=any(d['status']=='pending_extraction' for d in state['documents'].values())
    if pending:
        dep=helpers.deployments(); resident=all(helpers.CONTAINER in n for n in dep.values())
        if any(helpers.CONTAINER in n for n in dep.values()) and not resident:
            raise runtime.Fatal('Partial GLM deployment; left untouched')
        books.book.guard_gpu_workloads(run,helpers,resident_glm=resident)
        if resident:
            concurrent.capture_build(helpers,run)
            books.speed.healthy(books.speed.sampler(run,state,helpers)(0))
            verify_restart_configuration(run,helpers)
            state['glm_owned_before_ocr']=True; runtime.save(run,state)
        elif state['resource_phase']=='not_started':
            raise runtime.Fatal('GLM was not present at initial handoff; no authority inferred to start an absent deployment')
        state['resource_phase']='stopping_owned_idle_glm';runtime.save(run,state)
        helpers.arrange_resources(run/('handoff-'+str(time.time_ns())),stop_glm=resident)
        state['resource_phase']='ocr_only';runtime.save(run,state)


def verify_restart_configuration(run,helpers):
    """Check documented launch settings against observed flags before stopping."""
    names=('CONTEXT','PARALLEL','MAX_TOKENS','KV','THINKING','ABLIT')
    command='source ./scripts/config.sh; printf "%s\\n" '+ ' '.join('"$'+n+'"' for n in names)
    cp=subprocess.run(['bash','-c',command],cwd=helpers.GLM,capture_output=True,text=True,check=True,
                      env={**os.environ,'ABLIT':'0','PREPARE':'0','PULL':'0','HF_HUB_OFFLINE':'1'})
    values=cp.stdout.splitlines()
    if len(values)!=len(names):raise runtime.Fatal('Cannot read allowlisted GLM launcher settings')
    settings=dict(zip(names,values));binding=read_json(run/'concurrency-runtime-binding.json')
    for node in binding['nodes']:
        for proc in node['installed']['serving_processes']:
            for flag,key in (('--context','CONTEXT'),('--parallel','PARALLEL'),('--max-tokens','MAX_TOKENS')):
                if flag not in proc['flags'] or str(proc['flags'][flag])!=settings[key]:
                    raise runtime.Fatal('GLM helper '+key+' does not match the running deployment; no stop/restart')
            if bool(proc['flags'].get('--thinking')) != (settings['THINKING']=='1'):
                raise runtime.Fatal('GLM thinking configuration differs; no service action')
        argv=['docker','exec',helpers.CONTAINER,'python','-c','import os; print(os.environ.get("TF_GLM_KV", ""))']
        kv=helpers.checked(argv if node['node']=='head' else helpers.peer(shlex.join(argv))).strip()
        if kv!=settings['KV']:raise runtime.Fatal('GLM KV configuration differs; no service action')
        if node['installed']['selected_environment'].get('ABLIT') not in (None,'0'):
            raise runtime.Fatal('Owned deployment is not the regular configuration')
    atomic_json(run/'restart-configuration-check.json',{'settings':settings,'status':'observed_flags_match_documented_helper'})


def extract_all(run,state,manifest,helpers):
    pending=[d for d in manifest['documents'] if state['documents'][d['source_id']]['status']=='pending_extraction']
    if not pending:return
    signature=cli.runtime_signature(ROOT/'.venv-mineru/bin/python',ROOT/'model-cache')
    path=run/'ocr-runtime.json'
    if path.exists() and read_json(path)!=signature:raise runtime.Fatal('OCR environment changed; preserve prior work')
    if not path.exists():atomic_json(path,signature)
    for d in pending:
        check_pause(run); ident=d['source_id']; rec=state['documents'][ident]
        verify(run); library.verify_originals(manifest)
        helpers.arrange_resources(run/('ocr-admission-'+str(time.time_ns())),stop_glm=False)
        out=run/'extractions'/ident
        rec['extraction']=str(out.relative_to(run));state['stage']='OCR '+ident;runtime.save(run,state);progress(run,state)
        source={'pdf':str((run/rec['original']).relative_to(ROOT)), 'sha256':d['sha256'],
                'pages':d['page_count'],'original_pages':list(range(1,d['page_count']+1)),
                'ocr_mode':'auto','title':d['title']}
        args=cli.parser().parse_args(['--config',str(ROOT/'config.example.json'),'convert','--source',ident,'--tier','basic',
             '--ocr-isolation','none','--converter-python',str(ROOT/'.venv-mineru/bin/python'),'--models-dir',str(ROOT/'model-cache')])
        if (out/'state.json').exists():
            args.resume=str(out)
            state['reused_ocr_windows']=state.get('reused_ocr_windows',0)+sum(x['status']=='completed' for x in read_json(out/'state.json')['units'].values())
        def after_window(_run,ocr_state,window):
            rec['ocr_completed_pages']=sum(x['window']['owned_end']-x['window']['owned_start']+1 for x in ocr_state['units'].values() if x['status']=='completed')
            runtime.save(run,state);progress(run,state);check_pause(run)
        code=cli.cmd_convert(args,source_records={ident:source},runtime=signature,run_path=out,after_window=after_window,max_unit_attempts=2)
        if code==75:raise runtime.StopRun('OCR memory admission paused; no GLM overlap')
        if code:
            ocr_state=read_json(out/'state.json')
            for unit in ocr_state['units'].values():
                if unit['status']=='completed':continue
                summary=out/unit['attempt']/'output/summary.json'
                if not summary.exists() or read_json(summary).get('status') in ('preflight','blocked','preflight_blocked','runtime_preflight_failed'):
                    raise runtime.Fatal('Shared/uncertain OCR infrastructure failure; inspect '+str(summary))
                observed=read_json(summary)
                if observed.get('error_type') in ('MemoryError','ImportError','ModuleNotFoundError','PermissionError','OSError'):
                    raise runtime.Fatal('OCR infrastructure exception; inspect '+str(summary))
        # A failed document is settled; independent documents continue. A resume
        # retries only an interrupted window, under the persistent two-attempt cap.
        rec.update(status='extracted' if code==0 else 'extraction_failed', extraction_state_sha256=sha(out/'state.json'))
        if code:rec['error']='MinerU failed; see '+str(out/'state.json')
        runtime.save(run,state);progress(run,state)


def verified_blanks(ocr):
    """Accept absent OCR blocks only on visually blank, text-empty PDF pages."""
    import fitz
    blanks=[];state=read_json(ocr/'state.json')
    for rec in state['units'].values():
        attempt=ocr/rec['attempt']; mapping=read_json(attempt/'page-map.json')
        payload=read_json(attempt/'output/middle_json.json')
        with fitz.open(attempt/'input.pdf') as pdf:
            for page in payload['pages']:
                index=page['page_idx'];m=mapping[index]
                if m['owner'] and not page.get('blocks'):
                    pix=pdf[index].get_pixmap(matrix=fitz.Matrix(.25,.25),colorspace=fitz.csGRAY,alpha=False)
                    if pdf[index].get_text().strip() or any(v<248 for v in pix.samples):
                        raise ValueError('Nonblank page has no native blocks: '+str(m['original_physical_page']))
                    blanks.append(m['selected_page'])
    return blanks


def plan_document(run,state,document):
    import fitz
    ident=document['source_id']; rec=state['documents'][ident]; ocr=run/rec['extraction']
    if sha(ocr/'state.json')!=rec['extraction_state_sha256']:raise runtime.Fatal('Settled OCR state changed')
    previous=sorted((run/'native-preparations'/ident).glob('*/manifest.json'))
    cache=previous[-1].parent if previous else run/'native-preparations'/ident/str(time.time_ns())
    if not previous:
        chapter_inputs.prepare(cache,source_specs=[{'source':ident,'run':str(ocr),'prefix':ident,
             'parts':[('full',document['title'],1,document['page_count'])], 'pages':document['page_count'],
             'blanks':verified_blanks(ocr)}],evidence_root=ROOT)
    verify_seal(cache)
    dest=run/'inputs'/ident; dest.mkdir(parents=True,exist_ok=True)
    src=cache/'chapters'/(ident+'-full')
    library.copy_verified(src/'source.json',dest/'native.json');library.copy_verified(src/'source.tex',dest/'source.tex')
    assets=[]
    for p in sorted((cache/'assets').glob('*')):
        library.copy_verified(p,run/'inputs/assets'/p.name); assets.append('assets/'+p.name)
    atomic_json(dest/'assets.json',assets)
    pages=[]
    with fitz.open(run/rec['original']) as pdf:
        if len(pdf)!=document['page_count']:raise runtime.Fatal('Source page count differs from intake')
        pages=[{'physical_pdf_page':i+1,'printed_page':None,'text':p.get_text(sort=True)} for i,p in enumerate(pdf)]
    atomic_json(dest/'secondary.json',{'source_sha256':document['sha256'],'pages':pages})
    (dest/'secondary.txt').write_text(chapter_sources.render_pages(pages))
    native=read_json(dest/'native.json');ids=[b['id'] for b in native['blocks'] if b['kind'] not in scope.FURNITURE]
    def fits(section):
        try:
            body=scope.request(native,section,books.secondary_for(run,ident,section['physical_pages']),
                               phase='critic',draft='D'*scope.DRAFT_RESERVE_BYTES)
            chapter_protocol.budget(body,scope.CAPACITY);return True
        except chapter_protocol.ContextBudgetGap:return False
    sections=scope.split_meaningfully(native,ids,fits=fits)
    tasks=[];units=[]
    for i,section in enumerate(sections,1):
        key=ident+'-part-'+str(i).zfill(3);units.append(key)
        context,context_scope=books.context_contract(run,ident,section)
        state['source_units'][key]={'source_key':ident,'section':section,'kind':'new'}
        for phase in ('convert','critic'):
            task={'id':key+'/'+phase,'key':key,'source_key':ident,'phase':phase,'section':section,
                  'reasoning_effort':scope.EFFORTS[phase],'status':'pending',
                  'depends_on':key+'/convert' if phase=='critic' else None,'draft_label':None,
                  'context':context,'context_scope':context_scope,'attempt_limit':1}
            body=books.request_for(run,state,task)
            if body:task['preview_hash']=fingerprint(body)
            tasks.append(task)
    # Bind native/secondary/assets used by dispatch as well as the OCR renderer seal.
    for p in (dest/'manifest.json',):
        if not p.exists():seal(dest)
    plan={'source_id':ident,'source_sha256':document['sha256'],'prepared_input':str(cache.relative_to(run)),
          'input_seal':sha(cache/'manifest.json'),'dispatch_input':str(dest.relative_to(run)),
          'dispatch_input_seal':sha(dest/'manifest.json'), 'assets':{a:sha(run/'inputs'/a) for a in assets},
          'task_fingerprint':fingerprint(books.frozen_tasks({'tasks':tasks})),
          'all_target_blocks':ids,'assigned_blocks':[b for s in sections for b in s['blocks']],
          'source_pages':list(range(1,document['page_count']+1)),'verified_blank_pages':verified_blanks(ocr)}
    if plan['assigned_blocks']!=ids:raise runtime.Fatal('Target partition lost or repeated source blocks')
    plan_path=run/'plans'/(ident+'.json');atomic_json(plan_path,plan)
    rec.update(plan=str(plan_path.relative_to(run)),plan_sha256=sha(plan_path),units=units,status='queued')
    state['tasks'].extend(tasks);state['production_stage']['task_ids'].extend(t['id'] for t in tasks)
    runtime.save(run,state)


def compile_version(run,state,key,label):
    v=state['versions'][key][label]
    if sha(run/v['path'])!=v['sha256']:raise runtime.Fatal('Compilation source changed')
    text=(run/v['path']).read_text();source=state['source_units'][key]['source_key']
    try:assets=books.asset_map(run,source,text)
    except ValueError as exc:
        v['compilation']={'status':'missing_asset','error':str(exc)};return v['compilation']
    identity=fingerprint({'document':v['sha256'],'assets':books.asset_identity(assets),'environment':state['compiler_environment']['image']})
    base=run/Path(v['path']).parent/'builds';base.mkdir(exist_ok=True)
    for p in sorted(base.glob('*/collection-build.json')):
        record=read_json(p)
        if record['identity']==identity:
            verify_build_outputs(run,record['result'])
            v.update(compilation=record['result'],build_identity=identity);return record['result']
    out=base/str(time.time_ns())
    result=compiler_environment.compile_saved(run,state,ROOT,text,out,assets)
    if result['status'] in ('unavailable','compiler_environment_failure','adapter_configuration_failure'):
        raise runtime.Fatal('Shared isolated compiler unavailable; no more inference: '+str(out))
    atomic_json(out/'collection-build.json',{'identity':identity,'result':result})
    v.update(compilation=result,build_identity=identity);runtime.save(run,state);return result


def verify_build_outputs(run,result):
    for attempt in result.get('attempts',[]):
        for entry in attempt.get('outputs',[]):
            path=run/attempt['path']/entry['path']
            if not path.is_file() or path.is_symlink() or sha(path)!=entry['sha256']:
                raise runtime.Fatal('Recorded compiler output changed: '+str(path))


def finish(run,state,task,answer,call):
    ctrl=sys.modules[__name__]
    if task.get('recovery_kind')=='syntax':recovery.finish_syntax(ctrl,run,state,task,answer,call)
    else:books.finish(run,state,task,answer,call,compiler=compile_version)
    recovery.offline_low_proposal(run,state)
    recovery.queue_repairs(ctrl,run,state)
    rec=state['documents'][task['source_key']]
    related=[t for t in state['tasks'] if t['source_key']==task['source_key']]
    if all(t['status'] not in ('pending','running') for t in related):
        document=next(d for d in read_json(run/'collection.json')['documents'] if d['source_id']==task['source_key'])
        generation(run,state,document)
        publish_document(run,state,document)
        runtime.save(run,state)


def dispatch(run,state,tasks,sample,guard):
    tasks=[t for t in selection.active_tasks(state,tasks) if t['id'] in state['production_stage']['task_ids'] and mineru_high.admitted(state,t) and mineru_high.ready(state,t)]
    tasks.sort(key=lambda t:mineru_high.priority(state,t))
    ctrl=sys.modules[__name__]
    def verify_inputs():
        guard.check()
        for t in tasks:
            rec=state['documents'][t['source_key']];plan=read_json(run/rec['plan'])
            verify_seal(run/plan['dispatch_input'],plan['dispatch_input_seal'])
            InputGuard({str(run/'inputs'/a):h for a,h in plan['assets'].items()}).check()
    def before_reserve(s,t,b):
        selection.assert_dispatch(s,t)
        recovery.before_reserve(ctrl,run,s,t,b)
    def changed():
        # The sole coordinator adds syntax tasks. HTTP workers never edit state.
        tasks[:]=[t for t in selection.active_tasks(state,state['tasks']) if t['id'] in state['production_stage']['task_ids'] and mineru_high.admitted(state,t) and mineru_high.ready(state,t)]
        tasks.sort(key=lambda t:mineru_high.priority(state,t))
        for t in tasks:
            if t.get('recovery_kind') and t['phase']!='critic' and t['status']=='pending' and t.get('recovery_kind')!='mineru_high' and not state.get('low_supported',False):
                t.update(status='low_support_unverified',error='Installed Low mapping/template was not verified; no request reserved')
        runtime.save(run,state);progress(run,state)
    changed()
    concurrent.coordinate(run,state,tasks,body_for=lambda r,s,t:recovery.body_for(ctrl,r,s,t),finish=finish,verify=verify_inputs,
        changed=changed,sample=sample,fixed_level=2,
        before_reserve=before_reserve)


def generation(run,state,document):
    """Prepare a portable snapshot. Selected text remains standalone per part."""
    ident=document['source_id'];rec=state['documents'][ident]
    if selection.deferred(state,ident):raise runtime.Fatal('Deferred source cannot be generated or published as a failure')
    out=run/'deliveries'/ident
    selected={k:state['versions'][k][v]['sha256'] for k,v in state.get('current_versions',{}).items() if k in rec['units']}
    effective=recovery.effective_tasks(state,ident)
    revision=fingerprint({'selected':selected,'tasks':[(t['id'],t['status']) for t in effective]})[:20]
    if (out/'manifest.json').exists():
        previous=read_json(out/'coverage.json')
        prior_selected={row['unit']:row['sha256'] for row in previous['parts'] if row.get('selected')}
        # Existing delivered bytes stay immutable when a later derivative wins.
        if prior_selected!=selected:
            out=run/'delivery-revisions'/ident/revision
    rec['delivery_path']=str(out.relative_to(run))
    rec['delivery_generation']=run.name if out==run/'deliveries'/ident else run.name+'-'+revision
    if (out/'manifest.json').exists():
        verify_seal(out);coverage=read_json(out/'coverage.json')
        rec.update({k:coverage[k] for k in ('status','conversion','model_review','compilation')})
        return out
    out.mkdir(parents=True,exist_ok=True)
    rows=[];pdfs=[]
    for key in rec['units']:
        tasks=[t for t in effective if t['key']==key]
        label=state['current_versions'].get(key)
        row={'unit':key,'tasks':[{k:t.get(k) for k in ('id','phase','status','error','coverage_check','dispatched_draft_sha256')} for t in tasks],
             'selected':label,'source_verification':'not independently established'}
        if label:
            v=state['versions'][key][label];row.update(sha256=v['sha256'],compilation=v['compilation'])
            text=(run/v['path']).read_text();dest=out/'parts'/key
            library.copy_verified(run/v['path'],dest/'document.tex',v['sha256'])
            allowed={name:run/'inputs'/name for name in read_json(run/'inputs'/ident/'assets.json')}
            refs=scope.image_references(text)
            row['unresolved_asset_references']=[name for name in refs if name not in allowed]
            for name in refs:
                if name in allowed:library.copy_verified(allowed[name],dest/name)
            convert=next(t for t in tasks if t['phase']=='convert')
            initial='convert-'+convert['call'] if convert.get('call') else None
            if initial and initial in state['versions'][key]:
                dv=state['versions'][key][initial];dt=(run/dv['path']).read_text()
                library.copy_verified(run/dv['path'],dest/'initial-draft.tex',dv['sha256'])
                for name in scope.image_references(dt):
                    if name in allowed:library.copy_verified(allowed[name],dest/name)
            verify_build_outputs(run,v['compilation']);pdf=books.selected_pdf(run,v)
            if pdf:library.copy_verified(pdf,dest/'reading.pdf');pdfs.append(dest/'reading.pdf')
            for i,attempt in enumerate(v['compilation'].get('attempts',[]),1):
                for name in ('console.log','result.json'):
                    p=run/attempt['path']/name
                    if p.is_file():library.copy_verified(p,out/'build-diagnostics'/key/str(i)/name)
            for base in ('accuracy','provenance'):
                for p in sorted((run/base/key).rglob('*')):
                    if p.is_file():library.copy_verified(p,out/base/key/p.relative_to(run/base/key))
        rows.append(row)
    if rec.get('plan'):
        plan=read_json(run/rec['plan']);dest=run/plan['dispatch_input']
        for p in dest.iterdir():
            if p.is_file() and p.name!='manifest.json':library.copy_verified(p,out/'extraction'/p.name)
        for name,digest in plan['assets'].items():library.copy_verified(run/'inputs'/name,out/'extraction'/name,digest)
        library.copy_verified(run/rec['plan'],out/'extraction/coverage-plan.json',rec['plan_sha256'])
    if pdfs:
        import fitz
        merged=fitz.open()
        for pdf in pdfs:
            with fitz.open(pdf) as part:merged.insert_pdf(part)
        merged.save(out/'reading.partial.pdf');merged.close();os.replace(out/'reading.partial.pdf',out/'reading.pdf')
    calls=[c for c in state['calls'] if c['parent'].split('/')[0] in rec['units']]
    logs=[]
    for c in calls:
        folder=run/'calls'/c['id']
        if c.get('seal'):verify_seal(folder,c['seal'])
        logs.append({'call':c,'path':str(folder),'files':read_json(folder/'manifest.json') if (folder/'manifest.json').exists() else []})
    atomic_json(out/'raw-evidence-locations.json',logs)
    tasks=effective
    converted=bool(rec['units']) and all(k in state['current_versions'] for k in rec['units'])
    reviewed=bool(tasks) and all(t['status'] in ('critic_revised','critic_unchanged') for t in tasks if t['phase']=='critic')
    compiled=len(pdfs)==len(rec['units']) and bool(pdfs)
    flags=[r for r in state['selection_ledger'] if r['source_key']==ident]
    possible_gaps=any(r['possible_content_gaps'] for r in flags)
    rec.update(conversion='completed' if converted else 'missing_or_failed',model_review='completed' if reviewed else 'missing_or_failed',
               compilation='passed' if compiled else 'missing_or_failed')
    if rec['status'] not in ('extraction_failed','preparation_failed'):
        rec['status']='delivered_working_edition' if converted and reviewed and compiled and not possible_gaps else 'delivered_with_gaps'
    atomic_json(out/'coverage.json',{'source_sha256':document['sha256'],'source_pages':document['page_count'],
                'status':rec['status'],'conversion':rec['conversion'],'model_review':rec['model_review'],
                'compilation':rec['compilation'],'possible_content_gaps':possible_gaps,'parts':rows,'checks':flags,
                'source_completeness':document.get('completeness'),'source_verification':'not independently established',
                'missing_reading_parts':len(rec['units'])-len(pdfs),'error':rec.get('error')})
    (out/'README.md').write_text('# '+document['title']+'\n\nStatus: '+rec['status']+'.\n\n'
        'Editable text is in parts/*/document.tex; initial-draft.tex preserves the converter. '
        'Each part compiles separately with its own assets. reading.pdf concatenates passing part PDFs; '
        'missing builds are explicitly listed in coverage.json. No claim of mathematically verified completeness.\n\n'
        'Extraction, coverage, attributed accuracy notes and material comparisons are retained. '
        'Large wire/reasoning logs remain at hashed locations in raw-evidence-locations.json; portable sources do not depend on them.\n')
    seal(out);return out


def publish_document(run,state,document):
    ident=document['source_id'];rec=state['documents'][ident]
    out=library.ensure_source(LIBRARY,document,run/rec['original'])
    if selection.deferred(state,ident):
        atomic_json(out/'batch-selection.json',{'run':str(run),'status':selection.STATUS,**state['deferred_sources'][ident]})
        return
    if rec['status'] not in ('pending_extraction','extracted','queued'):
        gen=generation(run,state,document)
        previous=rec.get('publication')
        rec['publication']=library.publish_generation(out,rec['delivery_generation'],gen,rec['status'])
        if previous and previous!=rec['publication'] and previous not in rec.setdefault('publication_history',[]):rec['publication_history'].append(previous)
        library.write_source_readme(out,document)
        archive=ROOT/'results/originals-batch'/rec['delivery_generation']/(document['folder']+'.zip')
        if rec.get('archive') and rec['archive']['path']!=str(archive):
            rec.setdefault('archive_history',[]).append(rec.pop('archive'))
        if not rec.get('archive'):
            rec['archive']=library.archive(archive,out)
        elif sha(rec['archive']['path'])!=rec['archive']['sha256']:
            raise runtime.Fatal('Delivered source archive changed')


def publish(run,state,manifest):
    LIBRARY.mkdir(parents=True,exist_ok=True)
    for document in manifest['documents']:
        publish_document(run,state,document);runtime.save(run,state)
    rows=['# Original PDF source index','', 'Frozen collection: '+run.name+'. Only the original collection is admitted.','',
          '| Source | Type | Pages | Processing status |','| --- | --- | ---: | --- |']
    for d in manifest['documents']:
        rows.append('| ['+d['title'].replace('|','/')+']('+d['folder']+'/README.md) | '+d['document_type']+' | '+str(d['page_count'])+' | '+selection.document_status(state,d['source_id'])+' |')
    temp=LIBRARY/'INDEX.md.tmp';temp.write_text('\n'.join(rows)+'\n');os.replace(temp,LIBRARY/'INDEX.md')
    atomic_json(LIBRARY/'index.json',{'run':str(run),'sources':[{**{k:d[k] for k in ('source_id','sha256','folder','title','document_type')},
                    'status':selection.document_status(state,d['source_id'])} for d in manifest['documents']]})


def bundle(run,state):
    out=run/'inspection'/str(time.time_ns());out.mkdir(parents=True)
    for name in ('collection.json','reuse-audit.json','state.json','progress.json','binding.json','normal-terminal-checks.json','compiler-runtime-check.json'):
        if (run/name).exists():library.copy_verified(run/name,out/name)
    for path in sorted((run/'continuations').rglob('*')):
        if path.is_file():library.copy_verified(path,out/path.relative_to(run))
    for name in code_hashes():library.copy_verified(ROOT/name,out/'implementation'/name)
    for p in (ROOT/'tests').glob('*.py'):library.copy_verified(p,out/'tests'/p.name)
    for name in ('docs/ORIGINALS-BATCH.md','AGENTS.md','docs/CODEX-HANDOVER.md'):
        library.copy_verified(ROOT/name,out/name)
    for p in (run/'deliveries').glob('*/coverage.json'):library.copy_verified(p,out/'coverage'/p.parent.name/'coverage.json')
    for name,argv in [('git-status.txt',['git','status','--short','--branch']),('working-tree.diff',['git','diff','--no-ext-diff']),('git-revision.txt',['git','rev-parse','HEAD'])]:
        cp=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,check=True);(out/name).write_text(cp.stdout)
    (out/'START-HERE.md').write_text('Collection inspection snapshot. Read progress.json and coverage/. Saved implementation is included. '
          'No original PDFs, bulk assets, model files, credentials or wire/reasoning logs are included. Selected source crops support subsequent review. '
         'Production has no autonomous code repair. Successful model completion/builds do not prove source accuracy.\n')
    if state.get('recovery_continuation'):originals_review.export(sys.modules[__name__],run,state,out)
    seal(out)
    state['inspection']=library.archive(ROOT/'results/inspection'/('originals-'+run.name+'-'+out.name+'.zip'),out)
    runtime.save(run,state);return state['inspection']


def normal_checks(run):
    identity=fingerprint({'code':code_hashes(),'tests':runtime.test_hashes()})
    path=run/'normal-terminal-checks.json'
    if path.exists() and read_json(path).get('passed_identity')==identity:return
    log=run/('tests-'+str(time.time_ns())+'.log')
    with log.open('w') as f:
        cp=subprocess.run([str(PYTHON),'-B','-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    atomic_json(path,{'passed_identity':identity if cp.returncode==0 else None,'returncode':cp.returncode,'log':str(log)})
    if cp.returncode:raise runtime.Fatal('Required tests failed; no launch: '+str(log))


def worker(run):
    with (run/'terminal.log').open('a',buffering=1) as log:
        os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
        with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):
            state=verify(run)
            if state['status']==TERMINAL:return
            manifest=read_json(run/'collection.json')
            b=selection.binding(run,state);guard=InputGuard({**b['frozen'],**{str(ROOT/p):h for p,h in b['code'].items()}})
            try:
                state.update(status='running',diagnostic=None,stage='preflight');state['launches'].append({'at':runtime.now(),'pid':os.getpid(),'calls_before':len(state['calls'])})
                runtime.save(run,state);progress(run,state)
                library.verify_originals(manifest);books.book.converter_idle(ROOT);runtime.check_other_jobs()
                books.qualify_compiler(run,state)
                check=run/'compiler-preflight'/str(time.time_ns())
                result=tex_compile.compile_document(r'\documentclass{article}\usepackage{amsmath,graphicx}\begin{document}$x^2$\end{document}',check,image=state['compiler_environment']['image'],passes=2)
                if not result['compilation_claim']:raise runtime.Fatal('Real isolated compiler preflight failed: '+str(check))
                publish(run,state,manifest)  # Writable library checked before stopping GLM.
                helpers=books.speed.module();resource_handoff(run,state,helpers)
                extract_all(run,state,manifest,helpers)
                state['stage']='prepare full native inputs and coherent scopes';runtime.save(run,state)
                for d in manifest['documents']:
                    check_pause(run);rec=state['documents'][d['source_id']]
                    if selection.deferred(state,d['source_id']) or rec['status']!='extracted':continue
                    try:plan_document(run,state,d)
                    except IntegrityError:raise
                    except (ValueError,subprocess.CalledProcessError) as exc:
                        if isinstance(exc,runtime.Fatal):raise
                        rec.update(status='preparation_failed',error=str(exc));runtime.save(run,state)
                    progress(run,state)
                state['plans_complete']=True;runtime.save(run,state)
                check_pause(run)
                if state.get('selection_continuation'):
                    # Selection-only continuation must never start/switch a service.
                    books.book.arrange_glm(run,check_only=True)
                elif state.get('glm_owned_before_ocr'):
                    if helper_hashes(helpers)!=read_json(run/'service-helper-binding.json'):raise runtime.Fatal('GLM helpers changed')
                    state['resource_phase']='restoring_owned_glm';runtime.save(run,state)
                    books.book.arrange_glm(run,check_only=False)
                else:books.book.arrange_glm(run,check_only=True)
                concurrent.capture_build(helpers,run)
                efforts=books.speed.effort_check(run,helpers)
                if efforts.get('status')=='probe_error':raise runtime.Fatal('High/Max effort rendering unverified')
                state['resource_phase']='glm_only';state['low_supported']=efforts.get('low_supported',False);runtime.save(run,state)
                books.reconcile_unfinished(run,state,finish_fn=finish)
                recovery.queue_repairs(sys.modules[__name__],run,state)
                sample=books.speed.sampler(run,state,helpers);books.speed.healthy(sample(0))
                if any(t['status']=='pending' for t in state['tasks']):
                    check_pause(run);runtime.readiness(run,state)
                # The first successful real document is retained. Failures remain
                # visible while other independent documents can supply the smoke.
                if not state['smoke']:
                    for d in manifest['documents']:
                        rec=state['documents'][d['source_id']]
                        if rec.get('conversion')=='completed' and rec.get('model_review')=='completed' and rec.get('compilation')=='passed':
                            state['smoke']={'source_id':d['source_id'],'at':runtime.now(),'retained':True,
                                            'coverage_status':rec['status'],'source_verified':False}
                            runtime.save(run,state);break
                        if selection.deferred(state,d['source_id']) or rec['status']!='queued':continue
                        state['stage']='retained real-document smoke: '+d['source_id']
                        tasks=[t for t in state['tasks'] if t['source_key']==d['source_id']]
                        dispatch(run,state,tasks,sample,guard);generation(run,state,d);publish(run,state,manifest)
                        if rec['conversion']=='completed' and rec['model_review']=='completed' and rec['compilation']=='passed':
                            state['smoke']={'source_id':d['source_id'],'at':runtime.now(),'retained':True,
                                            'coverage_status':rec['status'],'source_verified':False};runtime.save(run,state);break
                if state['smoke']:
                    state['stage']='approved collection: High conversion / Max own-draft criticism'
                    dispatch(run,state,state['tasks'],sample,guard)
                if any(t['status'] in ('pending','running') for t in state['tasks']):raise runtime.Fatal('Undispatched work remains; not terminal')
                recovery.offline_low_proposal(run,state)
                for d in manifest['documents']:
                    if not selection.deferred(state,d['source_id']):generation(run,state,d)
                publish(run,state,manifest)
                state.update(status=TERMINAL,stage='published and packaged; no next collection',finished_at=runtime.now())
            except runtime.StopRun as exc:
                state.update(status='paused' if not isinstance(exc,runtime.Fatal) else 'stopped_error',diagnostic=str(exc))
            except BaseException as exc:
                state.update(status='stopped_error',diagnostic=type(exc).__name__+': '+str(exc),
                             diagnostic_file=concurrent.exception_trace(run,exc,'Originals collection worker'))
            finally:
                state['writer_released_at']=runtime.now();runtime.save(run,state);progress(run,state)
                bundle(run,state);progress(run,state)
            print('Worker ended:',state['status'],state.get('diagnostic'),flush=True)


def launch(run):
    state=verify(run)
    if state['status']==TERMINAL:
        print('Already finished. Zero inference, extraction or readiness.');return
    if not POINTER.exists() or Path(read_json(POINTER)['run']).resolve()!=run:
        raise runtime.Fatal('Not the selected originals run')
    if not books.speed.idle(ROOT) or not books.speed.idle(run):raise runtime.Fatal('Writer active; no second controller')
    for c in state['calls']:
        if c['status']=='in_progress' and not (run/'calls'/c['id']/'manifest.json').exists():
            raise runtime.Fatal('Uncertain reservation; no replay or readiness: '+c['id'])
    cp=subprocess.run(['tmux','has-session','-t',SESSION],capture_output=True,text=True)
    if cp.returncode==0:raise runtime.Fatal('Persistent session already exists')
    if cp.returncode!=1 or any(s in cp.stderr.lower() for s in ('permission denied','operation not permitted')):
        raise runtime.Fatal('Cannot inspect tmux: '+cp.stderr)
    normal_checks(run)
    for name in ('pause.json','stop.json'):(run/name).unlink(missing_ok=True)
    command=shlex.join([str(PYTHON),'-B','-u',str(Path(__file__).resolve()),'worker','--run',str(run)])
    subprocess.run(['tmux','new-session','-d','-s',SESSION,'cd '+shlex.quote(str(ROOT))+' && exec '+command],check=True)
    print('Persistent worker requested. Verify status and log; this message alone is not proof of progress:',run)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run','resume','worker','status','pause','bundle','defer-unstarted-arxiv','prepare-recovery','prepare-mineru-only','prepare-mineru-high'))
    parser.add_argument('--run',type=Path);args=parser.parse_args()
    if args.action=='prepare':prepare();return
    run=(args.run or Path(read_json(POINTER)['run'])).resolve()
    if args.action=='prepare-mineru-high':
        print(mineru_high.prepare(sys.modules[__name__],run))
    elif args.action=='prepare-mineru-only':
        from probe.originals_mineru_only import prepare
        print(prepare(sys.modules[__name__],run))
    elif args.action=='prepare-recovery':
        print(recovery.prepare(sys.modules[__name__],run,ROOT/'results/originals-recovery-20261102/saved-repairs'))
    elif args.action=='defer-unstarted-arxiv':prepare_deferrals(run)
    elif args.action in ('run','resume'):launch(run)
    elif args.action=='worker':worker(run)
    elif args.action=='pause':
        if read_json(run/'state.json')['status']!=TERMINAL:atomic_json(run/'pause.json',{'at':runtime.now()})
        print('Drain requested: finishes owned requests/current OCR window, admits no next work. No service stop.')
    elif args.action=='status':
        s=read_json(run/'state.json');p=read_json(run/'progress.json')
        p['writer_lock_held']=not books.speed.idle(run)
        p['saved_pid']=s['launches'][-1]['pid'] if s['launches'] else None
        print(json.dumps(p,indent=2))
    elif args.action=='bundle':
        with writer_lock(ROOT),writer_lock(run):print(bundle(run,verify(run))['path'])


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('ERROR:',type(exc).__name__+':',exc,file=sys.stderr);raise SystemExit(1)
