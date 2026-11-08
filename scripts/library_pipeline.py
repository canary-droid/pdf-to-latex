#!/usr/bin/env python3
"""Finite operator-launched library processing on the existing owned scheduler.

Preparation is offline. Paid recovery stays disabled; no implicit corpus resume.
"""
import argparse,copy,difflib,json,os,re,shlex,shutil,subprocess,sys,tarfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha,fingerprint,writer_lock,files_manifest
from probe.experiment import InputGuard,seal,verify_seal
from probe import library_first as policy,library_fallbacks as fallback,source_library as library
from probe import focused_recovery as requests,image_review as vision,chapter_glm as runtime,chapter_concurrency as scheduler
from probe import chapter_accuracy,compiler_environment,book_completion,followup_lifecycle,tex_syntax_repair,author_source
from scripts import extraction_comparison as base,library_reconcile as reconcile,simple_chapter_glm as simple
POINTER=ROOT/'results/library-first-batch-current.json';SESSION='pdf-library-first';TERMINAL='library_batch_finished'
RUNTIME_FIELDS=('chapter_contract','timing_policy','compiler_environment','runtime_image','remote_models','remote')

def save(run,s):
    plan=read_json(run/'plan.json');approval=plan.get('paid_approval',{});cloud=Path(approval.get('cloud_run',run));budget=fallback.budget_folder(run,approval)
    runtime.save(run,s);atomic_json(run/'progress.json',{'at':runtime.now(),'run':str(run),'status':s['status'],'stage':s.get('stage'),'diagnostic':s.get('diagnostic'),
      'documents':{sid:{**{k:d.get(k) for k in ('filename','status','units','failed_pages','outstanding_scopes','delivery','publication','selected_new_generation','reused_units')},'selected_units':sum(k in s['current_versions'] for k in d['units']),'pages_with_selected_text':sorted({n for k in d['units'] if k in s['current_versions'] for n in s['source_units'][k]['physical_pages']}),'mathpix_status':d.get('mathpix',{}).get('status')} for sid,d in s['documents'].items()},'tasks':[{k:t.get(k) for k in ('id','status','call','scope_review','pending_suggestions','paid_stage','paid_recovery')} for t in s['tasks']],
      'calls':[{'id':c['id'],'task':c['parent'],'status':c['status'],'seconds':c.get('elapsed_seconds'),'usage':c.get('metadata',{}).get('usage')} for c in s['calls']],
      'paid_execution':{'kimi_response_records':sum(1 for _ in (budget/'attempts').glob('*/outcome.json')),'kimi_provider_reservations':len(read_json(cloud/'billing.json')['reservations']) if (cloud/'billing.json').exists() else 0,'mathpix_confirmed_new_jobs':sum(bool(d.get('mathpix',{}).get('provider_record',{}).get('pdf_id')) and not d.get('mathpix',{}).get('reused_historical_job',False) for d in s['documents'].values()),'mathpix_reused_jobs':sum(bool(d.get('mathpix',{}).get('reused_historical_job')) for d in s['documents'].values())},
      'paid_routes':read_json(run/'plan.json').get('paid_approval',{'enabled':False}), 'paid_accounting':fallback.budget_summary(run,read_json(run/'plan.json').get('paid_approval')), 'ready_baseline':s.get('ready_baseline'), 'ready_added_offline':s.get('ready_added_offline'), 'newly_selected':sum(bool(d.get('selected_new_generation')) for d in s['documents'].values()),'log':str(run/'terminal.log'),'inspection':s.get('inspection')})

def prepare(source_ids,review_effort='high',compile_pdf=False):
    if review_effort not in ('high','max'):raise ValueError('Choose High default or explicit Max')
    if not source_ids or len(set(source_ids))!=len(source_ids):raise ValueError('Explicit finite unique source list required')
    if not base.books.speed.idle(ROOT):raise ValueError('Project writer active; do not prepare bound files underneath it')
    reconciliation=read_json(reconcile.DEV/'reconciliation/reconciliation.json');inventory=read_json(reconcile.PARENT/'collection.json')
    historical=read_json(reconcile.PARENT/'state.json')
    rows={d['source_id']:d for d in reconciliation['sources']};docs=[]
    live=read_json(reconcile.LIBRARY/'library-first-status.json')
    live_rows={d['source_id']:d for d in live['sources']}
    for sid in source_ids:
        if sid not in rows or rows[sid]['status']=='deferred':raise ValueError('Source excluded/not in frozen originals')
        if rows[sid]['status']=='ready':raise ValueError('Already-ready source refused; no blanket reconversion')
        folder=reconcile.LIBRARY/rows[sid]['folder'];pointer=read_json(folder/'current.json') if (folder/'current.json').exists() else None
        policy.admit_missing_conversion(live_rows[sid],pointer)
        existing=[key for key in historical['current_versions'] if key in historical['documents'][sid]['units']]
        experimental=[x['unit'] for x in reconciliation['experimental_outputs'] if x['source_key']==sid]
        if existing or experimental:raise ValueError('Completed saved material exists: '+', '.join(existing+experimental)+'. Reconcile/repair it first; this missing-conversion batch must not replay it.')
        d=next(x for x in inventory['documents'] if x['source_id']==sid);docs.append(d)
    run=ROOT/'runs'/('library-first-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));run.mkdir()
    ancestor=reconcile.FOLLOW;old=read_json(ancestor/'state.json')
    s={k:copy.deepcopy(old.get(k)) for k in ['chapter_contract','timing_policy','execution_limits','concurrency_policy','compiler_environment']}
    s.update(status='prepared',stage='prepared; no inference authorised by preparation',calls=[],tasks=[],versions={},current_versions={},source_units={},documents={},
      connection_failures=0,first_dispatch=None,active_stage=1,stages={'1':{}},launches=[],disable_dependency_downloads=True,
      suite_protocol='source-image-review-v1',production_stage={'task_ids':[]},derived_inputs={},resource_phase='not_started',
      runtime_image=old['runtime_image'],remote_models=old['remote_models'],remote='/home/mdi/projects/pdf-to-latex-comparisons/'+run.name,
      extraction={},models_downloaded=True,inputs_prepared=False)
    s['execution_limits']={'calls':None,'attempts_per_unit':1}
    if s.get('compiler_environment') and (ancestor/s['compiler_environment']['path']).exists():shutil.copytree(ancestor/s['compiler_environment']['path'],run/s['compiler_environment']['path'])
    shutil.copyfile(ancestor/'effort-support-offline.json',run/'effort-support-offline.json')
    settings=dict(policy.DEFAULTS,review_effort=review_effort,compile_pdf=bool(compile_pdf));frozen_docs=[];reuse=[]
    import fitz
    for d in docs:
        sid=d['source_id'];original=Path(d['originals'][0]['path'])
        if sha(original)!=d['sha256']:raise ValueError('Original changed')
        document={'source_id':sid,'filename':d['originals'][0]['name'],'sha256':d['sha256'],'original':str(original),'physical_pages':list(range(1,d['page_count']+1)),'pages':[],'library_document':d}
        current=read_json(reconcile.LIBRARY/d['folder']/'current.json') if (reconcile.LIBRARY/d['folder']/'current.json').exists() else None
        s['documents'][sid]={'filename':document['filename'],'status':'pending_extraction','source_sha256':d['sha256'],'units':[],'original':str(original),'historical_selection':current}
        pdf=fitz.open(original)
        native_pages=[{'physical_pdf_page':i+1,'text':page.get_text('text')} for i,page in enumerate(pdf)]
        quality=requests.secondary_assessment(native_pages)
        if sid==reconcile.repairs.CF:
            quality['manual_quarantine']='Saved source inspection established corrupt mathematical ASCII text layer; no secondary text supplied.'
        atomic_json(run/'sources'/sid/'secondary-assessment.json',quality)
        for n in document['physical_pages']:
            path=run/'sources'/sid/f'page-{n:03}.png';path.parent.mkdir(parents=True,exist_ok=True)
            copied=False
            for previous in [ancestor,base.ROOT/'runs/extraction-comparison-20261105T185601Z-layout']:
                p=read_json(previous/'plan.json');source=next((x for x in p['documents'] if x['source_id']==sid and x['sha256']==d['sha256']),None)
                records=read_json(previous/'arms/mineru_pro/state.json')['pages'];record=records.get(f'{sid}-p{n}');image=previous/'sources'/sid/path.name
                if source and record and record['status']=='completed' and image.is_file() and sha(image)==record['image_sha256']:
                    for f in record['outputs']:
                        src=previous/'arms/mineru_pro'/f['path']
                        if sha(src)!=f['sha256']:raise ValueError('Completed Pro output changed')
                        library.copy_verified(src,run/'arms/mineru_pro'/f['path'],f['sha256'])
                    library.copy_verified(image,path);s['extraction'].setdefault('mineru_pro',{'status':'prepared','pages':{}})['pages'][f'{sid}-p{n}']=record
                    reuse.append({'source':sid,'physical_page':n,'run':str(previous),'native_sha256':sha(previous/'arms/mineru_pro/pages'/f'{sid}-p{n}/native.json')});copied=True;break
            if not copied:pdf[n-1].get_pixmap(matrix=fitz.Matrix(200/72,200/72)).save(path)
            import struct
            w,h=struct.unpack('>II',path.read_bytes()[16:24]);document['pages'].append({'physical_pdf_page':n,'image':str(path.relative_to(run)),'path':str(path.relative_to(run)),'sha256':sha(path),'dimensions':[w,h]})
        frozen_docs.append(document)
    plan={'status':'frozen','workflow':policy.VERSION,'settings':settings,'documents':frozen_docs,'workloads':{'mineru_pro':[[d['source_id'],p] for d in frozen_docs for p in d['physical_pages']]},
      'reuse':reuse,'next_stage':'Missing Pro pages, then one conversion/High image-review per coherent structural unit; derive and seal exact units before first GLM reservation.',
      'paid_enabled':False,'spend_cap_usd':'0','no_recursive_splitting_or_retry':True,'historical':str(reconcile.PARENT),'runtime_image':s['runtime_image'],'remote_models':s['remote_models'],'runtime_contract':{k:s[k] for k in RUNTIME_FIELDS}}
    policy.validate_extraction_plan(plan,run);atomic_json(run/'plan.json',plan)
    if s['extraction'].get('mineru_pro'):atomic_json(run/'arms/mineru_pro/state.json',s['extraction']['mineru_pro'])
    frozen={str(p):sha(p) for p in (run/'sources').rglob('*') if p.is_file()};frozen.update({d['original']:d['sha256'] for d in frozen_docs});frozen[str(run/'effort-support-offline.json')]=sha(run/'effort-support-offline.json')
    atomic_json(run/'binding.json',{'code':base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':frozen});save(run,s);atomic_json(POINTER,{'run':str(run),'status':'PREPARED_NOT_RUNNING'})
    print(run);return run

def generation_name(run,record):
    revision=record.get('publication_revision',1)
    return Path(run).name+('-r'+str(revision) if revision>1 else '')

def verify(run):
    p=read_json(run/'plan.json');b=read_json(run/'binding.json');s=read_json(run/'state.json')
    if b['code']!=base.code_binding() or b['plan_sha256']!=sha(run/'plan.json'):raise runtime.Fatal('Frozen implementation or plan changed')
    if p.get('runtime_contract')!={k:s.get(k) for k in RUNTIME_FIELDS}:raise runtime.Fatal('Frozen runtime/compiler/timing contract changed')
    InputGuard(b['files']).check()
    live_path=reconcile.LIBRARY/'library-first-status.json';live_rows={x['source_id']:x for x in read_json(live_path)['sources']} if live_path.exists() else {}
    for doc in p['documents']:
        sid=doc['source_id'];folder=reconcile.LIBRARY/doc['library_document']['folder'];pointer=read_json(folder/'current.json') if (folder/'current.json').exists() else None
        expected=s['documents'][sid].get('historical_selection');own='generations/'+generation_name(run,s['documents'][sid])
        if pointer!=expected and (pointer or {}).get('generation') not in (own,s['documents'][sid].get('publication',{}).get('generation')):raise runtime.Fatal('Source selection changed after preparation; no duplicate processing')
        attempt=live_rows.get(sid,{}).get('latest_attempt')
        if attempt and attempt['run'] not in (str(run),p.get('parent_run')):raise runtime.Fatal('Another library attempt exists; reconcile before dispatch')
    if p.get('overnight'):
        from probe.library_paid import verify as verify_paid
        verify_paid(run,s,p,b)
    elif p['paid_enabled'] or p['spend_cap_usd']!='0':raise runtime.Fatal('Paid route not explicitly approved')
    if s['concurrency_policy']!=scheduler.POLICY or s['execution_limits']!={'calls':None,'attempts_per_unit':1}:raise runtime.Fatal('Frozen safety policy changed')
    for path,digest in s['derived_inputs'].items():
        if sha(run/path)!=digest:raise runtime.Fatal('Derived scope/draft/asset changed')
    for key,unit in s['source_units'].items():
        if read_json(run/'inputs'/key/'unit.json')!=unit:raise runtime.Fatal('State source scope differs from sealed unit')
    for versions in s['versions'].values():
        for version in versions.values():
            if sha(run/version['path'])!=version['sha256']:raise runtime.Fatal('Completed draft changed')
    for task in s['tasks']:
        for path,digest in task.get('result_files',{}).items():
            if sha(run/path)!=digest:raise runtime.Fatal('Saved result annotation/diff changed')
    ids=[t['id'] for t in s['tasks']];parents=[c['parent'] for c in s['calls']]
    if len(set(parents))!=len(parents) or not set(parents)<=set(ids):raise runtime.Fatal('Reservation replay or task expansion')
    if s.get('task_plan_sha256'):
        if sha(run/s.get('task_plan_path','task-plan.json'))!=s['task_plan_sha256'] or ids!=read_json(run/s.get('task_plan_path','task-plan.json'))['task_ids']:raise runtime.Fatal('Derived finite task plan changed')
        expected=read_json(run/s.get('task_plan_path','task-plan.json'))['task_definitions']
        if [{k:t[k] for k in ('id','key','source_key','phase','reasoning_effort')} for t in s['tasks']]!=expected:raise runtime.Fatal('Derived task settings changed')
        outstanding=read_json(run/s.get('task_plan_path','task-plan.json'))['outstanding_scopes']
        if outstanding!={sid:d.get('outstanding_scopes',[]) for sid,d in s['documents'].items()}:raise runtime.Fatal('Outstanding source scopes changed')
    return s

def refresh_prepared(parent,*,source_ids=None,content_first=False):
    """Link an idle, never-started preparation to reviewed current code only.

    Never reseal a historical run, migrate active/consumed tasks, or regenerate
    source images. Started runs require their separate explicit recovery process.
    """
    parent=Path(parent).resolve()
    if not all(base.books.speed.idle(p) for p in (ROOT,ROOT/'runs',parent)):raise runtime.Fatal('Writer active; no preparation refresh')
    with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(parent):
        old=read_json(parent/'state.json');binding=read_json(parent/'binding.json')
        if old['status']!='prepared' or old['calls'] or old.get('launches') or old.get('inputs_prepared') or old['tasks']:
            raise runtime.Fatal('Only a never-started zero-call preparation can be refreshed; allowances cannot reset')
        if sha(parent/'plan.json')!=binding['plan_sha256']:raise runtime.Fatal('Parent plan changed')
        InputGuard(binding['files']).check()
        run=ROOT/'runs'/('library-first-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-prelaunch-'+str(time.time_ns())[-6:])
        shutil.copytree(parent,run,ignore=shutil.ignore_patterns('.probe.lock','report'))
        plan=read_json(run/'plan.json');state=read_json(run/'state.json')
        if content_first:
            allowed={'original-c6fbf9bf1bbc7325','original-af03317e4e74c832'}
            requested=set(source_ids or allowed)
            original_ids={d['source_id'] for d in plan['documents']}
            if not requested or not requested<=allowed or not requested<=original_ids:raise runtime.Fatal('Revised scope must be the approved subset')
            live={d['source_id']:d for d in read_json(reconcile.LIBRARY/'library-first-status.json')['sources']}
            selected=[]
            for d in plan['documents']:
                if d['source_id'] not in requested:continue
                row=live[d['source_id']]
                if row['status']=='ready':continue
                folder=reconcile.LIBRARY/d['library_document']['folder'];pointer=read_json(folder/'current.json') if (folder/'current.json').exists() else None
                policy.admit_missing_conversion(row,pointer);selected.append(d)
            plan['documents']=selected;retained={d['source_id'] for d in selected}
            plan['workloads']['mineru_pro']=[x for x in plan['workloads']['mineru_pro'] if x[0] in retained]
            plan['reuse']=[x for x in plan.get('reuse',[]) if x['source'] in retained]
            state['documents']={k:v for k,v in state['documents'].items() if k in retained}
            if state.get('extraction',{}).get('mineru_pro'):
                state['extraction']['mineru_pro']['pages']={k:v for k,v in state['extraction']['mineru_pro']['pages'].items() if any(k.startswith(sid+'-p') for sid in retained)}
                atomic_json(run/'arms/mineru_pro/state.json',state['extraction']['mineru_pro'])
            plan['settings']['compile_pdf']=False
            plan['objective']='Complete substantive machine-readable source; original PDF is reading copy; builds optional and off'
            plan['excluded_from_this_preparation']=[{'source_id':d['source_id'],'reason':'Author source selected or removed by content-first author-source priority'} for d in read_json(parent/'plan.json')['documents'] if d['source_id'] not in retained]
        state['remote']='/home/mdi/projects/pdf-to-latex-comparisons/'+run.name
        state.update(linked_preparation_from=str(parent),linked_at=runtime.now());state.pop('inspection',None)
        plan['runtime_contract']={k:state[k] for k in RUNTIME_FIELDS};plan['continuation_parent_preparation']=str(parent)
        policy.validate_extraction_plan(plan,run);atomic_json(run/'plan.json',plan)
        atomic_json(run/'preparation-link.json',{'parent':str(parent),'parent_plan_sha256':binding['plan_sha256'],'parent_binding_sha256':sha(parent/'binding.json'),
          'parent_consumed_calls':0,'reason':'Content-first author-source priority; approved subset only; zero consumed calls preserved' if content_first else 'Reviewed pre-launch code update; settings, histories, allowances and prepared source bytes preserved',
          'parent_code':binding['code'],'settings_unchanged':plan['settings']==read_json(parent/'plan.json')['settings']})
        files={str(run/Path(p).relative_to(parent)) if Path(p).is_relative_to(parent) else p:h for p,h in binding['files'].items()}
        files[str(run/'preparation-link.json')]=sha(run/'preparation-link.json')
        atomic_json(run/'binding.json',{'code':base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':files})
        if (run/'normal-terminal-checks.json').exists():
            (run/'normal-terminal-checks.json').rename(run/('parent-validation-'+sha(parent/'binding.json')[:12]+'.json'))
        save(run,state);verify(run);atomic_json(POINTER,{'run':str(run),'status':'PREPARED_NOT_RUNNING'});print(run);return run

def extract(run,s):
    if s.get('extraction_done'):return
    p=read_json(run/'plan.json');policy.validate_extraction_plan(p,run);required=p['workloads']['mineru_pro'];records=s['extraction'].get('mineru_pro',{}).get('pages',{})
    if all(records.get(f'{sid}-p{n}',{}).get('status')=='completed' for sid,n in required):s['extraction_done']=True;save(run,s);return
    if not s.get('allow_owned_handoff'):raise runtime.Fatal('Missing OCR requires explicit --allow-owned-handoff at operator launch; no service change performed')
    # This path ONLY uses the already pinned image/weights. No install/download branch.
    actual=subprocess.check_output(base.ssh('docker image inspect '+shlex.quote(s['runtime_image'])+" --format '{{.Id}}'"),text=True).strip()
    if actual!=s['runtime_image']:raise runtime.Fatal('Qualified Pro image absent or changed')
    helpers=base.books.speed.module();base.collection.resource_handoff(run,s,helpers)
    try:
        remote=s['remote'];base.command(run,'owned-pro-directories',base.ssh('mkdir -p '+shlex.quote(remote+'/input')+' '+shlex.quote(remote+'/outputs/mineru_pro')))
        base.command(run,'clear-owned-pause',base.ssh('rm -f '+shlex.quote(remote+'/outputs/mineru_pro/pause.json')))
        archive=run/'peer-input.tar'
        with tarfile.open(archive,'w') as tar:
            tar.add(run/'plan.json',arcname='plan.json');tar.add(run/'sources',arcname='sources')
            for name in ['probe/__init__.py','probe/extraction_comparison.py','probe/extraction_followup.py','scripts/extraction_followup_candidate.py']:
                tar.add(ROOT/name,arcname='scripts/extraction_candidate_worker.py' if name.endswith('extraction_followup_candidate.py') else name)
        base.command(run,'transfer',['scp',str(archive),base.PEER+':'+remote+'/input.tar'])
        if subprocess.check_output(base.ssh('sha256sum '+shlex.quote(remote+'/input.tar')),text=True).split()[0]!=sha(archive):raise runtime.Fatal('Transferred input changed')
        base.command(run,'unpack',base.ssh('tar -xf '+shlex.quote(remote+'/input.tar')+' -C '+shlex.quote(remote+'/input')))
        dest=run/'arms/mineru_pro';dest.mkdir(parents=True,exist_ok=True)
        if (dest/'state.json').exists():base.command(run,'reuse-pages',['scp','-r',str(dest)+'/.',base.PEER+':'+remote+'/outputs/mineru_pro/'])
        def observe():
            if (run/'pause.json').exists():
                subprocess.run(base.ssh('touch '+shlex.quote(remote+'/outputs/mineru_pro/pause.json')),capture_output=True)
        base.command(run,'pro-extraction',base.ssh(shlex.join(base.container_args(s,'mineru_pro'))),observe=observe)
        base.command(run,'collect-pro',['scp','-r',base.PEER+':'+remote+'/outputs/mineru_pro/.',str(dest)])
        s['extraction']['mineru_pro']=read_json(dest/'state.json')
        for record in s['extraction']['mineru_pro']['pages'].values():
            for f in record.get('outputs',[]):
                if sha(dest/f['path'])!=f['sha256']:raise runtime.Fatal('Pro output integrity failure')
        if s['extraction']['mineru_pro']['status']=='paused':raise runtime.StopRun('Paused after owned OCR window')
        s['extraction_done']=True
    finally:
        if s.get('glm_owned_before_ocr'):
            if base.collection.helper_hashes(helpers)!=read_json(run/'service-helper-binding.json'):raise runtime.Fatal('Owned helper changed; no unsafe restoration')
            base.books.book.arrange_glm(run);scheduler.capture_build(helpers,run);base.collection.verify_restart_configuration(run,helpers);s['resource_phase']='glm_restored'
        save(run,s)

def plan_units(run,s):
    if s['inputs_prepared']:return
    from probe.extraction_followup import pro_export
    p=read_json(run/'plan.json');records=s['extraction']['mineru_pro']['pages']
    for d in p['documents']:
        sid=d['source_id'];blocks=[];allassets={};inferred=[]
        if s['documents'][sid].get('planning_done'):continue
        bad=[] if d.get('fixed_native') else [n for n in d['physical_pages'] if (records.get(f'{sid}-p{n}',{}).get('status')!='completed' or n in s['documents'][sid].get('garbled_or_failed_pages',[])) and f'{sid}-p{n}' not in s.get('mathpix_pages',{}) and str(n) not in d.get('blank_pages',{})]
        if bad:
            import fitz
            subset=run/'fallbacks'/sid/'affected-pages.pdf';subset.parent.mkdir(parents=True,exist_ok=True)
            if not subset.exists():
                with fitz.open(d['original']) as original:
                    pdf=fitz.open()
                    for n in bad:pdf.insert_pdf(original,from_page=n-1,to_page=n-1)
                    pdf.save(subset);pdf.close()
            s['documents'][sid].update(status='extraction_incomplete',failed_pages=bad);fallback.proposal(run,{'id':sid,'source_id':sid,'source_sha256':d['sha256'],'physical_pages':bad,'subset':str(subset),'subset_sha256':sha(subset),'original_to_subset':{str(n):i+1 for i,n in enumerate(bad)}},'extraction','incomplete')
            if not p.get('allocation_id') or not s['documents'][sid].get('mathpix_final'):continue
        if d.get('fixed_native'):
            fixed=read_json(run/d['fixed_native']);blocks=copy.deepcopy(fixed['blocks']);allassets=copy.deepcopy(fixed['assets'])
        for n in ([] if d.get('fixed_native') else d['physical_pages']):
            if n in bad or str(n) in d.get('blank_pages',{}):continue
            if f'{sid}-p{n}' in s.get('mathpix_pages',{}):
                recovered=s['mathpix_pages'][f'{sid}-p{n}'];blocks+=copy.deepcopy(recovered['blocks']);allassets.update(recovered['assets']);continue
            folder=run/'arms/mineru_pro/pages'/f'{sid}-p{n}'
            for artifact in records[f'{sid}-p{n}'].get('outputs',[]):
                if sha(run/'arms/mineru_pro'/artifact['path'])!=artifact['sha256']:raise runtime.Fatal('Saved Pro artifact changed before scope construction')
            raw=read_json(folder/'native.json');assets={}
            for i,row in enumerate(raw):
                crop=folder/f'region-{i}.png'
                if crop.exists():
                    name=f'assets/{sid}-p{n}-region-{i}.png';library.copy_verified(crop,run/'inputs'/name);assets[i]=name;allassets[name]=str(run/'inputs'/name)
            exported,extra=pro_export(raw,assets);inferred+=extra
            for b in exported:
                kind={'title':'paragraph_title','formula':'equation','image_block':'image','chart':'image'}.get(b['kind'],b['kind'])
                if kind in book_completion.FURNITURE:continue
                text=b['text']
                if kind=='paragraph_title' and not book_completion.headings(text):text=r'\section*{'+text+'}'
                blocks.append({'id':f'{sid}-p{n}-r{b["index"]}','kind':kind,'tex':text,'page':{'original_physical_page':n},'assets':[assets[b['index']]] if b['index'] in assets else [],'native':raw[b['index']]})
        if not blocks:
            gaps=[{'first':f'{sid}-p{n}-unextracted','last':f'{sid}-p{n}-unextracted','physical_pages':[n],'blocks':[],'reason':'Failed extraction; source content remains unknown'} for n in bad]
            s['documents'][sid].update(status='no_substantive_source_regions',planning_done=True,outstanding_scopes=gaps,source_accounting={'blank_pages':d.get('blank_pages',{}),'total_regions':0,'all_regions_accounted':not bad});continue
        # Do not span an unknown failed page. Good coherent segments can proceed
        # after the finite OCR fallback settles; the gaps remain outstanding.
        segments=[[]]
        for block in blocks:
            if segments[-1] and any(segments[-1][-1]['page']['original_physical_page']<n<block['page']['original_physical_page'] for n in bad):segments.append([])
            segments[-1].append(block)
        rows=[];offset=0
        for segment in segments:
            group=policy.structural_units(segment,**d.get('qualified_unit_limits',{}))
            for u in group:u['source_order_start']+=offset;u['source_order_end']+=offset
            rows+=group;offset+=len(segment)
        scope_path=run/'source-plans'/f'{sid}.json'
        reused_keys=s['documents'][sid].get('reused_units',[])
        reused_blocks=[b for k in reused_keys for b in s['source_units'][k]['blocks']]
        if len(reused_blocks)!=len(set(reused_blocks)) or set(reused_blocks)&{b['id'] for b in blocks}:raise runtime.Fatal('Reused/new source scope overlap')
        atomic_json(scope_path,{'reused_scopes':{k:s['source_units'][k]['blocks'] for k in reused_keys},'source_id':sid,'source_sha256':d['sha256'],'source_regions':[b['id'] for b in blocks],
          'scopes':rows,'accounting':'Every region appears once in included or outstanding scopes; context never adds output ownership'})
        s['derived_inputs'][str(scope_path.relative_to(run))]=sha(scope_path)
        outstanding=[{k:v for k,v in u.items() if k not in ('text','native_blocks')} for u in rows if u['disposition']=='outstanding']
        outstanding += [{'first':f'{sid}-p{n}-unextracted','last':f'{sid}-p{n}-unextracted','physical_pages':[n],'blocks':[],'reason':'Source page extraction failed; unknown content remains outstanding, not an empty or blank page','disposition':'outstanding'} for n in bad]
        for u in outstanding:u['source_plan']=str(scope_path.relative_to(run))
        units=[u for u in rows if u['disposition']=='included']
        s['documents'][sid]['outstanding_scopes']=outstanding
        s['documents'][sid]['source_accounting']={'total_regions':len(blocks)+len(reused_blocks),'reused_regions':len(reused_blocks),'new_regions':len(blocks),'included_regions':sum(len(u['blocks']) for u in units)+len(reused_blocks),
          'outstanding_regions':sum(len(u['blocks']) for u in outstanding),'blank_pages':d.get('blank_pages',{}),'all_regions_accounted':True,'fully_scheduled':not outstanding,'source_plan':str(scope_path.relative_to(run))}
        atomic_json(run/'inferred'/f'{sid}.json',{'not_printed_source':inferred})
        new_keys=[]
        for i,u in enumerate(units,1):
            key=d.get('unit_key_prefix',sid+'-unit')+f'-{i:03}'
            if key in s['source_units']:raise runtime.Fatal('New unit collides with saved scope')
            new_keys.append(key);folder=run/'inputs'/key;folder.mkdir(parents=True,exist_ok=True)
            quality=read_json(run/'sources'/sid/'secondary-assessment.json')
            secondary='' if quality.get('manual_quarantine') else '\n\n'.join('Physical page '+str(p['physical_pdf_page'])+'\n'+p['text'] for p in quality['pages'] if p['physical_pdf_page'] in u['physical_pages'])
            preceding=blocks[:u['source_order_start']]
            unit=dict(u,source_key=sid,title=f'{d["filename"]} — coherent unit {i}/{len(units)}',
              context=d.get('earlier_context','')+'\nEarlier source definitions/context only, not repeated output. Outstanding earlier passages remain context, NOT assigned output in this unit:\n'+'\n\n'.join(b['tex'] for b in preceding),
              context_blocks=[b['id'] for b in preceding],secondary=secondary,assets=allassets)
            chosen=preceding[:6]+preceding[-12:] if len(preceding)>18 else preceding
            unit['cloud_context']=d.get('earlier_cloud_context','')+'\n\n'+'\n\n'.join(b['tex'] for b in chosen)
            unit['cloud_context_blocks']=[b['id'] for b in chosen]
            unit['cloud_context_policy']='Complete opening and immediate preceding source blocks; omitted broad history is context, never omitted assigned output. If still too large, cloud dispatch is blocked without clipping.'
            unit['secondary_policy']=quality.get('manual_quarantine',quality['policy'])
            atomic_json(folder/'unit.json',unit);s['source_units'][key]=unit;s['derived_inputs'][str((folder/'unit.json').relative_to(run))]=sha(folder/'unit.json');s['documents'][sid]['units'].append(key)
            for phase,effort in [('convert','high'),('critic',p['settings']['review_effort'])]:s['tasks'].append({'id':key+'/'+phase,'key':key,'source_key':sid,'section_title':unit['title'],'phase':phase,'status':'pending','reasoning_effort':effort})
        if d.get('unit_insertion_after'):
            order=s['documents'][sid]['units'];old=[k for k in order if k not in new_keys]
            if d['unit_insertion_after'] not in old:raise runtime.Fatal('Missing-scope insertion anchor absent')
            at=old.index(d['unit_insertion_after'])+1;s['documents'][sid]['units']=old[:at]+new_keys+old[at:]
        s['documents'][sid]['status']='planned_with_outstanding_scopes' if outstanding else 'planned'
        s['documents'][sid]['planning_done']=True
        if s['documents'][sid].get('published'):s['documents'][sid]['needs_republication']=True
        if p.get('overnight'):
            from probe.library_paid import adopt_direct_mathpix
            adopt_direct_mathpix(run,s,sid)
    for unit in s['source_units'].values():
        for asset in unit['assets'].values():
            path=Path(asset);s['derived_inputs'][str(path.relative_to(run)) if path.is_relative_to(run) else str(path)]=sha(path)
    if p.get('task_order')=='new_paper_order_with_recovery_interleave':
        from itertools import zip_longest
        active={t['key'] for t in s['tasks']}
        new=[d for d in p['documents'] if d.get('role')=='new']
        recovery=[[k for k in s['documents'][d['source_id']]['units'] if k in active] for d in p['documents'] if d.get('role')=='recovery']
        rec=[k for row in zip_longest(*recovery) for k in row if k] if recovery else []
        ordered=[]
        for i,d in enumerate(new):
            if i and rec:ordered.append(rec.pop(0))
            ordered += [k for k in s['documents'][d['source_id']]['units'] if k in active]
        ordered+=rec;rank={k:i for i,k in enumerate(ordered)}
        s['tasks'].sort(key=lambda t:(rank[t['key']],0 if t['phase']=='convert' else 1))
    if p.get('task_order')=='round_robin_units':
        order={d['source_id']:i for i,d in enumerate(p['documents'])}
        s['tasks'].sort(key=lambda t:(t.get('unit_rank',s['documents'][t['source_key']]['units'].index(t['key'])),order[t['source_key']],0 if t['phase']=='convert' else 1))
    s['production_stage']['task_ids']=[t['id'] for t in s['tasks']]
    for pth in (run/'inputs/assets').glob('*'):
        if pth.is_file():s['derived_inputs'][str(pth.relative_to(run))]=sha(pth)
    task_path='task-plan.json' if not s.get('task_plan_sha256') else 'task-plans/task-plan-'+str(time.time_ns())+'.json'
    atomic_json(run/task_path,{'task_ids':s['production_stage']['task_ids'],'task_definitions':[{k:t[k] for k in ('id','key','source_key','phase','reasoning_effort')} for t in s['tasks']],'unit_count':len(s['source_units']),'primary_request_allowance':len(s['tasks']),'automatic_retries':0,'paid_attempts':len(s['tasks']) if p.get('overnight') else 0,'mathpix_subset_allowance':sum(not d.get('fixed_native') for d in p['documents']) if p.get('overnight') else 0,'source_ownership':{k:u['blocks'] for k,u in s['source_units'].items()},'outstanding_scopes':{sid:d.get('outstanding_scopes',[]) for sid,d in s['documents'].items()}})
    s.update(task_plan_path=task_path,task_plan_sha256=sha(run/task_path),inputs_prepared=True);save(run,s)

def review_images(run,s,t):
    u=s['source_units'][t['key']];d=next(d for d in read_json(run/'plan.json')['documents'] if d['source_id']==t['source_key']);records=[]
    for n in u['physical_pages']:
        page=next(x for x in d['pages'] if x['physical_pdf_page']==n);records.append({'path':page['path'],'sha256':page['sha256'],'dimensions':page['dimensions'],'physical_page':n,'crop':None,'source_id':d['source_id'],'source_sha256':d['sha256'],'original_pdf':d['original']})
    # Full pages plus two half-page details on each of the two densest pages.
    sys.path.append(str(ROOT/'.venv-mineru/lib/python3.12/site-packages'));from PIL import Image
    dense=sorted(u['physical_pages'],key=lambda n:-sum(len(b['tex']) for b in u['native_blocks'] if b['page']['original_physical_page']==n))[:2]
    for n in dense:
        original=next(r for r in records if r['physical_page']==n)
        with Image.open(run/original['path']) as im:
            w,h=im.size
            for half,(a,b) in enumerate([(.06,.53),(.48,.94)]):
                if len(records)>=8:break
                box=[int(.08*w),int(a*h),int(.93*w),int(b*h)];path=run/'inputs'/t['key']/f'page-{n}-detail-{half}.png'
                if not path.exists():im.crop(box).save(path)
                records.append(dict(original,path=str(path.relative_to(run)),sha256=sha(path),dimensions=[box[2]-box[0],box[3]-box[1]],crop=box))
    for r in records:r['expected_fit']=vision.geometry(*r['dimensions'])
    path=run/'inputs'/t['key']/'images.json';atomic_json(path,records);s['derived_inputs'][str(path.relative_to(run))]=sha(path)
    for r in records:s['derived_inputs'][r['path']]=sha(run/r['path'])
    return records

def body_for(run,s,t):
    u=s['source_units'][t['key']]
    if t['phase']=='convert':
        ownership='OUTPUT OWNERSHIP: emit only the assigned primary source, once. Secondary full pages and earlier definitions are corroboration/context, not permission to emit neighbouring equations or prose. Do not extend the ending from secondary text. First owned source block: '+u['native_blocks'][0]['tex']+'\nLast owned source block: '+u['native_blocks'][-1]['tex']+'\n'
        return requests.conversion_request(u['text'],u['secondary'],ownership+u['context'],effort='high',assets=u['assets'])
    v=s['versions'][t['key']][s['current_versions'][t['key']]];draft=(run/v['path']).read_text()
    if sha(run/v['path'])!=v['sha256']:raise runtime.Fatal('Own-draft review identity changed')
    records=read_json(run/'inputs'/t['key']/'images.json')
    return requests.critic_request(draft,u['text'],u['secondary'],u['context'],effort=t['reasoning_effort'],images=vision.image_parts(records,run))

def before(run,s,t,body):
    verify(run)
    if any(c['parent']==t['id'] for c in s['calls']):raise runtime.Fatal('Consumed task cannot replay')
    if body!=body_for(run,s,t):raise runtime.Fatal('Prepared source/draft differs')
    if t['phase']=='critic':
        payload=vision.request_payload(body);t['draft_sha256']=payload['base_sha256']
        # Existing installed CPU image/tokenizer path, no extra model request.
        program=(ROOT/'scripts/verify_image_prompt.py').read_text();result=subprocess.run(['docker','exec','-i','glm53-flash-tf','python','-c',program],input=json.dumps({t['id']:body}),text=True,capture_output=True,check=True)
        expected=json.loads(result.stdout);t['cpu_expectation']=expected['requests'][t['id']];atomic_json(run/'cpu-verification'/(t['key']+'.json'),expected)
        if expected['limits']!=policy.DEFAULTS['image_limits'] or t['cpu_expectation']['image_rows']!=vision.image_budget(body)['image_tokens']:raise runtime.Fatal('Image runtime allocation changed')

def compilation_requested(run):
    return read_json(run/'plan.json')['settings'].get('compile_pdf',False)

def content_check(run,s,t,document):
    u=s['source_units'][t['key']]
    result=author_source.generated_content(document,u['assets'])
    if 'native_blocks' in u:
        result['coverage']=unit_coverage(document,u)
        if result['coverage']['coverage_status']=='omission_risk':result['content_issues'].append('Source coverage requires resolution')
    result['usable']=not result['content_issues']
    return result

def unit_coverage(document,u):
    if u.get('saved_coverage_adjudication') and __import__('hashlib').sha256(document.encode()).hexdigest()==u['saved_coverage_adjudication']['draft_sha256']:
        return dict(u['saved_coverage_adjudication'],coverage_status='requires_source_review',semantic_completeness='Targeted recorded checks; no whole-paper mathematical verification')
    return followup_lifecycle.coverage(document,dict(u.get('coverage_metadata',{}),blocks=u['native_blocks']),[b['id'] for b in u['native_blocks']])

def compile_version(run,s,t,document,label):
    dest=run/'versions'/t['key']/label;dest.mkdir(parents=True,exist_ok=True);(dest/'document.tex').write_text(document)
    assets={name:Path(path) for name,path in s['source_units'][t['key']]['assets'].items()}
    if not compilation_requested(run):
        version={'path':str((dest/'document.tex').relative_to(run)),'sha256':sha(dest/'document.tex'),'compilation':{'status':'not_requested','reason':'Content-first library; original PDF is reading copy'},'content_check':content_check(run,s,t,document)}
        atomic_json(dest/'version.json',version);return version
    if not (dest/'build/compilation.json').exists():
        if not s.get('compiler_environment'):atomic_json(dest/'build/compilation.json',{'status':'unavailable','reason':'Optional compiler not provisioned','attempts':[]})
        else:
            try:compiler_environment.compile_saved(run,s,ROOT,document,dest/'build',assets)
            except OSError as exc:atomic_json(dest/'build/compilation.json',{'status':'unavailable','reason':str(exc),'attempts':[]})
    version={'path':str((dest/'document.tex').relative_to(run)),'sha256':sha(dest/'document.tex'),'compilation':read_json(dest/'build/compilation.json')}
    # Optional compiler failure remains recorded; it does not erase usable text.
    if version['compilation']['status']!='passed':
        log=dest/'build/attempt-1/console.log';error=tex_syntax_repair.first_error(log.read_text(errors='replace')) if log.exists() else None
        repaired,edits=tex_syntax_repair.deterministic(document,error)
        if edits:
            derivative=dest/'deterministic';derivative.mkdir(exist_ok=True);(derivative/'document.tex').write_text(repaired);atomic_json(derivative/'edits.json',edits)
            if not (derivative/'build/compilation.json').exists():compiler_environment.compile_saved(run,s,ROOT,repaired,derivative/'build',assets)
            result=read_json(derivative/'build/compilation.json')
            if result['status']=='passed':version={'path':str((derivative/'document.tex').relative_to(run)),'sha256':sha(derivative/'document.tex'),'compilation':result,'syntax_parent':version}
    version['content_check']=content_check(run,s,t,(run/version['path']).read_text());atomic_json(dest/'version.json',version)
    return version

def result_file(run,call_id,name):
    path=Path(run)/'call-results'/call_id/name
    return path if path.exists() else Path(run)/'calls'/call_id/name

def finish(run,s,t,answer,call):
    if t.get('settled_call')==call['id']:return
    folder=run/'calls'/call['id'];results=run/'call-results'/call['id'];t['call']=call['id'];key=t['key'];u=s['source_units'][key]
    if t['phase']=='critic' and call.get('metadata',{}).get('usage',{}).get('prompt_tokens')!=t['cpu_expectation']['prompt_tokens']:raise runtime.Fatal('Image processing not verified; no text fallback')
    if answer is None:
        t.update(status='failed',settled_call=call['id'])
    elif t['phase']=='convert':
        document,info=chapter_accuracy.envelope(answer,simple.extract_document)
        if document is None or not chapter_accuracy.complete_document(document):t.update(status='invalid_conversion',settled_call=call['id'])
        else:
            version=compile_version(run,s,t,document,'convert-'+call['id']);s['versions'].setdefault(key,{})['convert']=version;s['current_versions'][key]='convert';review_images(run,s,t)
            t.update(status='conversion_completed',settled_call=call['id']);atomic_json(results/'accuracy.json',{'envelope':info,'notes':chapter_accuracy.outside_notes(answer,info),'source_verification':'not established'})
    else:
        matches=[v for v in s['versions'][key].values() if v['sha256']==t['draft_sha256']]
        if not matches:raise runtime.Fatal('Exact dispatched critic draft absent')
        v=matches[0];draft=(run/v['path']).read_text()
        if sha(run/v['path'])!=t['draft_sha256']:raise runtime.Fatal('Critic draft changed before settlement')
        try:
            from probe.library_repair import salvage_json
            parsed=salvage_json(answer,t['draft_sha256']);revised,log=vision.apply_review(draft,parsed)
            log['response_normalization']={'method':'Unique valid JSON object with exact draft hash; no invented fields or fuzzy anchors','raw_answer_sha256':requests.digest(answer)}
        except (ValueError,KeyError,TypeError) as exc:t.update(status='invalid_review',review_response='invalid_findings',reason=str(exc),settled_call=call['id'])
        else:
            version=compile_version(run,s,t,revised,'review-'+call['id']);s['versions'][key]['review']=version
            version['selection']={'selected':version['content_check']['usable'],'reason':'Exact-anchor validated derivative with substantive content/coverage checks' if version['content_check']['usable'] else 'Saved proposal; content issues prevent selection'}
            if version['selection']['selected']:s['current_versions'][key]='review'
            atomic_json(results/'findings.json',log);(results/'changes.diff').write_text(''.join(difflib.unified_diff(draft.splitlines(True),revised.splitlines(True))))
            t.update(status='review_completed',review_response='usable_focused_findings',settled_call=call['id'],scope_review=log['scope_review'],review_complete_attested=log['review_complete_attested'],pending_suggestions=log['pending_suggestions'])
    # Persist completed versions; failed converter cannot leave an eligible critic.
    if t['phase']=='convert' and t['status']!='conversion_completed':
        for critic in s['tasks']:
            if critic['key']==key and critic['phase']=='critic':critic.update(status='unavailable',review_response='no_complete_draft')
    if t['status'] in ('failed','invalid_conversion','invalid_review'):
        images=review_images(run,s,t);chosen=[x for x in images if x['crop'] is None]
        if len(chosen)<4:chosen+=next(([x] for x in images if x['crop'] is not None),[])
        unit={'id':key,'source_id':t['source_key'],'source_sha256':s['documents'][t['source_key']]['source_sha256'],'physical_pages':u['physical_pages'],'primary':u['text'],'secondary':u['secondary'],'context':u['context'],'call':str(folder),
              'cloud_images':[{'source_id':r['source_id'],'source_sha256':r['source_sha256'],'page':r['physical_page'],'path':str(run/r['path']),'sha256':r['sha256'],'bbox':r['crop']} for r in chosen]}
        if t['phase']=='critic':
            v=s['versions'][key][s['current_versions'][key]];unit.update(draft_path=str(run/v['path']),draft_sha256=v['sha256'],draft_ranges=[[0,len((run/v['path']).read_text())]])
        fallback.proposal(run,unit,t['phase'],'reasoning_exhaustion' if call.get('metadata',{}).get('usage',{}).get('completion_tokens_details',{}).get('reasoning_tokens')==131072 else 'failed')
    t['result_files']={str(p.relative_to(run)):sha(p) for p in results.glob('*') if p.is_file()}
    save(run,s);publish_settled(run,s,t['source_key'])

def publish_settled(run,s,sid):
    tasks=[t for t in s['tasks'] if t['source_key']==sid]
    if any(t['status'] in ('pending','running') for t in tasks):return
    rec=s['documents'][sid]
    if rec.get('published') and not rec.get('needs_republication'):return
    if rec.pop('needs_republication',False) and rec.get('published'):
        rec['publication_revision']=rec.get('publication_revision',1)+1;rec['published']=False;save(run,s)
    d=next(d for d in read_json(run/'plan.json')['documents'] if d['source_id']==sid);out=run/'deliveries'/sid
    if rec.get('publication_revision',1)>1:out=run/'delivery-revisions'/sid/('revision-'+str(rec['publication_revision']))
    if (out/'manifest.json').exists():
        record=policy.validate_publication(out,d['library_document']);commit_publication(run,s,sid,d,out,record);return
    out.mkdir(parents=True,exist_ok=True);parts=[];findings=[];pdfs=[];coverage=[]
    for key in rec['units']:
        label=s['current_versions'].get(key)
        if not label:continue
        v=s['versions'][key][label];text=(run/v['path']).read_text();target=out/'parts'/key/'document.tex';library.copy_verified(run/v['path'],target,v['sha256']);parts.append({'path':str(target.relative_to(out)),'sha256':v['sha256']})
        for name,path in s['source_units'][key]['assets'].items():library.copy_verified(path,target.parent/name)
        for name,version in s['versions'][key].items():library.copy_verified(run/version['path'],target.parent/(name+'-original.tex'))
        atomic_json(target.parent/'versions.json',s['versions'][key])
        for origin in (run/'inputs'/key/'review-history').glob('*'):
            if origin.is_file():library.copy_verified(origin,target.parent/'review-history'/origin.name)
        for name in ('prior.tex','changes.diff','provenance.json'):
            origin=(run/v['path']).parent/name
            if origin.exists():library.copy_verified(origin,target.parent/'saved-reconciliation'/name)
        for name,version in s['versions'][key].items():
            raw=version.get('syntax_parent',version)
            library.copy_verified(run/raw['path'],target.parent/(name+'-raw.tex'),raw['sha256'])
            for index,attempt in enumerate(version['compilation'].get('attempts',[]),1):
                log=run/attempt['path']/'console.log'
                if log.exists():library.copy_verified(log,target.parent/'build-diagnostics'/name/str(index)/'console.log')
        native={'blocks':s['source_units'][key]['native_blocks']};coverage.append(unit_coverage(text,s['source_units'][key]))
        atomic_json(target.parent/'source-scope.json',s['source_units'][key])
        for t in tasks:
            if t['key']!=key:continue
            paid_result=t.get('paid_recovery',{})
            if paid_result.get('attempt_path'):
                paid_folder=Path(paid_result['attempt_path'])
                for name in ('findings.json','changes.diff','original.tex','reviewed.tex','library-answer.txt','outcome.json','error.json'):
                    if (paid_folder/name).is_file():library.copy_verified(paid_folder/name,target.parent/'paid-recovery'/t['phase']/name)
                atomic_json(target.parent/'paid-recovery'/t['phase']/'selection.json',paid_result)
            if not t.get('call'):continue
            path=result_file(run,t['call'],'findings.json')
            if path.exists():findings+=read_json(path)['findings'];library.copy_verified(path,target.parent/(t['phase']+'-findings.json'))
            accuracy=result_file(run,t['call'],'accuracy.json')
            if accuracy.exists():library.copy_verified(accuracy,target.parent/(t['phase']+'-accuracy.json'))
        if v['compilation']['status']=='passed':
            pdf=run/v['compilation']['attempts'][-1]['path']/'document.pdf';library.copy_verified(pdf,target.parent/'reading.pdf');pdfs.append(pdf)
    compiled=bool(parts) and len(pdfs)==len(rec['units']);content_ok=all(s['versions'][k][s['current_versions'][k]].get('content_check',{}).get('usable',False) for k in rec['units'] if k in s['current_versions']);complete=content_ok and bool(rec['units']) and not rec.get('outstanding_scopes') and len(parts)==len(rec['units']) and all(x.get('coverage_status')!='omission_risk' for x in coverage)
    if pdfs:
        import fitz
        merged=fitz.open()
        for p in pdfs:
            with fitz.open(p) as doc:merged.insert_pdf(doc)
        merged.save(out/'reading.pdf');merged.close()
    from probe.library_repair import overlap_screen
    overlap=overlap_screen([(k,(run/s['versions'][k][s['current_versions'][k]]['path']).read_text()) for k in rec['units'] if k in s['current_versions']])
    if overlap['duplicate_equation_tags']:complete=False
    atomic_json(out/'assembly-check.json',overlap)
    ordered='\n\n'.join('% BEGIN OWNED PART '+key+'\n'+book_completion.body_only((run/s['versions'][key][s['current_versions'][key]]['path']).read_text())+'\n% END OWNED PART '+key for key in rec['units'] if key in s['current_versions'])
    (out/'ordered-body.tex').write_text('% Machine-readable ordered bodies; original standalone preambles/macros remain in parts/. Compilation not requested.\n'+ordered)
    review=policy.review_summary(tasks,findings)
    if rec.get('reused_units'):
        review['new_units_reviewed_full_scope_attested']=review['reviewed_full_scope_attested']
        review['reviewed_full_scope_attested']=False
        review['reused_review_coverage']={key:'Historical review retained in exact version provenance; no new full-scope image-review attestation' for key in rec['reused_units']}
    if rec.get('outstanding_scopes'):review.update(reviewed_full_scope_attested=False,outstanding_source_scopes=rec['outstanding_scopes'])
    record={'source_id':sid,'source_sha256':d['sha256'],'status':'ready_working_source' if complete else 'partial_source','content_status':'complete_assigned_source' if complete else 'incomplete_or_flagged',
      'conversion':'complete' if len(parts)==len(rec['units']) and parts and not rec.get('outstanding_scopes') else 'incomplete',
      'model_review':review,'compilation':'passed' if compiled else ('not_requested' if not compilation_requested(run) else 'failed_or_partial'),'compilation_scope':'Produced parts only; outstanding passages are not built',
      'selected_tex':parts,'source_verification':'Model reviewed, not independently mathematically verified','coverage':coverage,
      'outstanding_scopes':rec.get('outstanding_scopes',[]),'source_accounting':rec.get('source_accounting'),'output_ownership_check':overlap,'missing_conversion_scopes':[{'unit':k,'physical_pages':s['source_units'][k]['physical_pages'],'blocks':s['source_units'][k]['blocks']} for k in rec['units'] if k not in s['current_versions']],'paid_recovery':[t.get('paid_recovery') for t in tasks if t.get('paid_recovery')],'reused_units':rec.get('reused_units',[])}
    atomic_json(out/'library-status.json',record);(out/'README.md').write_text('# '+d['filename']+'\n\nStatus: '+record['status']+'. Editable parts and assets are under parts/. The unchanged original PDF is the human reading copy. Optional compilation is independent of content readiness. Review omissions, suggestions and source checks are separate in library-status.json.\n')
    atomic_json(out/'raw-evidence-locations.json',[{'call':c['id'],'path':str(run/'calls'/c['id']),'seal':c.get('seal'),'status':c['status'],'seconds':c.get('elapsed_seconds'),'usage':c.get('metadata',{}).get('usage')} for c in s['calls'] if any(t.get('call')==c['id'] for t in tasks)])
    seal(out);policy.validate_publication(out,d['library_document'])
    commit_publication(run,s,sid,d,out,record)

def commit_publication(run,s,sid,d,out,record):
    rec=s['documents'][sid];complete=record['status']=='ready_working_source' and record['content_status']=='complete_assigned_source'
    folder=reconcile.LIBRARY/d['library_document']['folder']
    with writer_lock(reconcile.LIBRARY):
        previous=read_json(folder/'current.json') if (folder/'current.json').exists() else None
        if previous!=rec['historical_selection'] and previous!=rec.get('publication') and (previous or {}).get('generation')!='generations/'+generation_name(run,rec):raise runtime.Fatal('Library pointer changed; preserve independent selection')
        metadata=read_json(folder/'source.json') if (folder/'source.json').exists() else None
        managed=metadata is not None and (folder/'README.md').exists() and (folder/'README.md').read_text() in (library.source_readme(metadata,previous),library.source_readme(metadata,rec['historical_selection']))
        generation=generation_name(run,rec)
        publication=library.publish_generation(folder,generation,out,record['status'],select=complete)
        if managed and complete:library.write_source_readme(folder,metadata)
        update_library_index(run,sid,record,publication,complete)
    rec.update(status=record['status'],published=True,delivery=str(out),publication=publication,selected_new_generation=complete);save(run,s)

def update_library_index(run,sid,record,publication,selected):
    """Refresh machine status as papers settle; preserve hand-edited index prose."""
    path=reconcile.LIBRARY/'library-first-status.json'
    if not path.exists():return  # low-level fixtures; real library intake supplies it
    index=read_json(path);row=next((x for x in index['sources'] if x['source_id']==sid),None)
    if row is None:raise runtime.Fatal('Source missing from reconciled library index')
    row['latest_attempt']={'run':str(run),'generation':publication,'selected':selected,'content_status':record['content_status'],'model_review':record['model_review'],'compilation':record['compilation']}
    if selected:row.update(status='ready',selected_generation=publication,conversion=record['conversion'],model_review=record['model_review'],compilation=record['compilation'],coverage_flags=record['coverage'])
    index['counts']={kind:sum(x['status']==kind for x in index['sources']) for kind in ['ready','partial','deferred']}
    snapshot='LIBRARY-FIRST-INDEX-'+run.name+'.md';index['latest_readable_index']=snapshot
    lines=['# Current library sources','',str(index['counts']),'', '| Source | Pages | Status | Selected source |','|---|---:|---|---|']
    for item in index['sources']:
        pointer=item.get('selected_generation');target=item['folder']+'/'+pointer['generation']+'/README.md' if pointer else item['folder']+'/README.md'
        lines.append('| '+item['filename'].replace('|','/')+' | '+str(item['pages'])+' | '+item['status']+' | [source]('+target+') |')
    temp=reconcile.LIBRARY/(snapshot+'.partial');temp.write_text('\n'.join(lines)+'\n');os.replace(temp,reconcile.LIBRARY/snapshot);atomic_json(path,index)
    landing=reconcile.LIBRARY/'LIBRARY-FIRST-INDEX.md';marker='[Latest '+run.name+']('+snapshot+')'
    if landing.exists() and marker not in landing.read_text():
        with landing.open('a') as f:f.write('\n'+marker+' — current statuses after this batch; earlier table preserved.\n')

def bundle(run,s):
    from probe.library_report import inspection
    result=inspection(run,s,ROOT/'results/inspection');s['inspection']=result;save(run,s);return result

def saved_response(run,call,body):
    """The same identity/shared-failure gates as live scheduler collection."""
    folder=Path(run)/'calls'/call['id'];verify_seal(folder,call.get('seal'))
    result=read_json(folder/'outcome.json')
    if any(result.get(k)!=call.get(k) for k in ('id','parent','request_sha256')):raise runtime.Fatal('Saved response differs from reserved task')
    result['seal']=sha(folder/'manifest.json')
    scheduler.response_binding(run,result,body)
    if result.get('status') not in ('completed_response','failed'):raise runtime.Fatal('Uncertain saved reservation; reconcile without replay')
    if (result.get('metadata',{}).get('http_status') or 0)>=400 or result.get('failure_kind') in scheduler.SHARED|{'connection','connection_timeout','transport'}:
        raise runtime.Fatal('Saved shared/infrastructure failure requires explicit reconciliation; not eligible for model fallback')
    return result

def register_sources(run,s):
    """Manifest-backed intake only for the frozen new selection, before publication."""
    plan=read_json(run/'plan.json')
    if not plan.get('allocation_id'):return
    with writer_lock(reconcile.LIBRARY):
        path=reconcile.LIBRARY/'library-first-status.json';index=read_json(path)
        for d in plan['documents']:
            sid=d['source_id'];known=next((x for x in index['sources'] if x['source_id']==sid),None)
            if known:
                if known['source_sha256']!=d['sha256']:raise runtime.Fatal('Library source ID collision')
                continue
            if any(x['source_sha256']==d['sha256'] or x['folder'].casefold()==d['library_document']['folder'].casefold() for x in index['sources']):raise runtime.Fatal('Library identity/folder collision')
            library.ensure_source(reconcile.LIBRARY,d['library_document'],d['original'])
            index['sources'].append({'source_id':sid,'source_sha256':d['sha256'],'folder':d['library_document']['folder'],'filename':d['filename'],'pages':len(d['physical_pages']),'status':'partial','selected_generation':None,'document_type':d['library_document']['document_type'],'collection_membership':'Explicit selected30 master PDFs','introduced_by':str(run)})
        index['counts']={k:sum(x['status']==k for x in index['sources']) for k in ('ready','partial','deferred')};atomic_json(path,index)

def worker(run):
    with (run/'terminal.log').open('a',buffering=1) as log:
        os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
        with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):
            s=verify(run)
            if s['status']==TERMINAL:return
            try:
                s.update(status='running',stage='preflight',diagnostic=None);s['launches'].append({'at':runtime.now(),'pid':os.getpid()});save(run,s);runtime.check_other_jobs()
                register_sources(run,s)
                for sid,record in s['documents'].items():
                    if record.get('planning_done') and record.get('units'):publish_settled(run,s,sid)
                if compilation_requested(run) and s.get('compiler_environment'):
                    try:check=compiler_environment.compile_saved(run,s,ROOT,r'\documentclass{article}\begin{document}Compiler qualification.\end{document}',run/'compiler-preflight'/str(time.time_ns()),{})
                    except OSError as exc:check={'status':'unavailable','reason':str(exc)}
                    s['optional_compiler_preflight']=check;save(run,s)
                extract(run,s)
                if read_json(run/'plan.json').get('overnight'):
                    from probe import library_paid
                    library_paid.runtime_authorise(run);library_paid.extraction_round(run,s)
                plan_units(run,s)
                helpers=base.books.speed.module();base.books.book.arrange_glm(run,check_only=True)
                if base.books.speed.effort_check(run,helpers)['status']!='supported':raise runtime.Fatal('Installed reasoning mappings not qualified')
                rawsample=base.books.speed.sampler(run,s,helpers)
                def sample(owned):
                    observation=rawsample(owned)
                    if any(type(v)is not int or v<4*1024**3 for v in observation['memory_available_bytes'].values()):raise runtime.StopRun('Image-workflow4GiB headroom guard; no dispatch')
                    return observation
                base.books.speed.healthy(sample(0))
                for c in s['calls']:
                    t=next(t for t in s['tasks'] if t['id']==c['parent'])
                    if t.get('settled_call')==c['id']:continue
                    path=run/'calls'/c['id']
                    if not (path/'manifest.json').exists():raise runtime.Fatal('Uncertain consumed request: no replay')
                    c.update(saved_response(run,c,body_for(run,s,t)));c['seal']=sha(path/'manifest.json');finish(run,s,t,(path/'content.txt').read_text() if c['status']=='completed_response' else None,c)
                scheduler.coordinate(run,s,s['tasks'],body_for=body_for,finish=finish,verify=lambda:verify(run),changed=lambda:save(run,s),sample=sample,fixed_level=2,before_reserve=lambda state,t,b:before(run,state,t,b))
                if read_json(run/'plan.json').get('overnight'):
                    # Work is finite: derived units only; one reserved phase and
                    # one fallback each. Never replay a successful upstream call.
                    while True:
                        if (run/'pause.json').exists():raise runtime.StopRun('Pause requested; owned calls drained')
                        more_ocr=library_paid.extraction_round(run,s)
                        if not s['inputs_prepared']:plan_units(run,s)
                        library_paid.model_round(run,s,one_at_a_time=True)
                        if any(t['status']=='pending' for t in s['tasks']):
                            scheduler.coordinate(run,s,s['tasks'],body_for=body_for,finish=finish,verify=lambda:verify(run),changed=lambda:save(run,s),sample=sample,fixed_level=2,before_reserve=lambda state,t,b:before(run,state,t,b))
                        else:
                            for sid in s['documents']:publish_settled(run,s,sid)
                            if not more_ocr and not library_paid.pending_model_recovery(s):break
                            if more_ocr:time.sleep(5)
                for sid in s['documents']:publish_settled(run,s,sid)
                s.update(status=TERMINAL,finished_at=runtime.now(),stage='finished; no automatic next batch')
            except runtime.StopRun as exc:s.update(status='stopped_error' if isinstance(exc,runtime.Fatal) else 'paused',diagnostic=str(exc))
            except BaseException as exc:s.update(status='stopped_error',diagnostic=str(exc),traceback=scheduler.exception_trace(run,exc,'Library batch'))
            finally:save(run,s);bundle(run,s)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','refresh-prepared','revise-content-first','run','resume','worker','status','pause','bundle']);p.add_argument('--source-id',action='append',default=[]);p.add_argument('--review-effort',choices=['high','max'],default='high');p.add_argument('--compile-pdf',action='store_true');p.add_argument('--run',type=Path);p.add_argument('--allow-owned-handoff',action='store_true');a=p.parse_args()
    if a.action=='prepare':prepare(a.source_id,a.review_effort,a.compile_pdf);return
    run=(a.run or Path(read_json(POINTER)['run'])).resolve()
    if a.action=='revise-content-first':refresh_prepared(run,source_ids=a.source_id or None,content_first=True);return
    if a.action=='refresh-prepared':refresh_prepared(run);return
    if a.action=='status':print(json.dumps(read_json(run/'progress.json'),indent=2));return
    if a.action=='pause':atomic_json(run/'pause.json',{'at':runtime.now()});print('Pause requested; owned requests drain');return
    if a.action=='worker':worker(run);return
    s=verify(run)
    if a.action=='bundle':
        with writer_lock(ROOT),writer_lock(run):print(bundle(run,s))
        return
    if s['status']==TERMINAL:print('Finished; zero new requests');return
    if not all(base.books.speed.idle(p) for p in (ROOT,ROOT/'runs',run)):raise runtime.Fatal('Existing writer; no duplicate launch')
    if any(c['status']=='in_progress' and not (run/'calls'/c['id']/'manifest.json').exists() for c in s['calls']):raise runtime.Fatal('Uncertain call must be reconciled')
    check=subprocess.run(['tmux','has-session','-t',SESSION],capture_output=True)
    if check.returncode!=1:raise runtime.Fatal('Worker already exists or tmux unavailable')
    base.collection.normal_checks(run);s['allow_owned_handoff']=a.allow_owned_handoff or s.get('allow_owned_handoff',False);save(run,s);(run/'pause.json').unlink(missing_ok=True)
    command=shlex.join([str(base.PYTHON),'-B','-u',str(Path(__file__).resolve()),'worker','--run',str(run)])
    subprocess.run(['tmux','new-session','-d','-s',SESSION,'cd '+shlex.quote(str(ROOT))+' && exec '+command],check=True);print('Persistent launch requested:',run)
if __name__=='__main__':main()
