#!/usr/bin/env python3
"""Persistent finite extraction comparison; never invokes a production worker."""
import argparse
import copy
import csv
import html
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from probe import extraction_comparison as core, chapter_glm as runtime, chapter_concurrency as concurrent
from probe import focused_recovery as requests, chapter_sources, book_completion as scope
from probe.common import atomic_json,read_json,sha,fingerprint,writer_lock,files_manifest
from probe.experiment import InputGuard,verify_seal
from scripts import originals_batch as collection, focused_recovery as focused
books=collection.books
POINTER=ROOT/'results/extraction-comparison-current.json'
SESSION='pdf-extraction-comparison'
TERMINAL='extraction_comparison_finished'
PYTHON=ROOT/'.venv-control/bin/python'
PEER='mdi@192.168.100.2'


def code_binding():
    return {str(p.relative_to(ROOT)):sha(p) for d in ('probe','scripts') for p in sorted((ROOT/d).glob('*.py'))}


def progress(run,state):
    rows=[]
    for call in state['calls']:
        usage=call.get('metadata',{}).get('usage',{})
        total=usage.get('completion_tokens');reason=usage.get('completion_tokens_details',{}).get('reasoning_tokens')
        rows.append({'call':call['id'],'task':call['parent'],'status':call['status'],
                     'seconds':call.get('elapsed_seconds'),'reasoning_tokens':reason,
                     'final_tokens':total-reason if isinstance(total,int) and isinstance(reason,int) else None})
    atomic_json(run/'progress.json',{'at':runtime.now(),'run':str(run),'status':state['status'],
        'stage':state.get('stage'),'diagnostic':state.get('diagnostic'),'extraction':state.get('extraction',{}),
        'tasks':[{k:t.get(k) for k in ('id','status','call')} for t in state['tasks']],
        'calls':rows,'log':str(run/'terminal.log'),'inspection':state.get('inspection'),
        'source_verification':'Eight frozen source pages inspected; generated outputs require recorded checks'})


def save(run,state):
    runtime.save(run,state);progress(run,state)


def verify(run):
    plan=read_json(run/'plan.json');core.validate_plan(plan)
    state=read_json(run/'state.json');binding=read_json(run/'binding.json')
    if sha(run/'plan.json')!=binding['plan_sha256'] or binding['code']!=code_binding():
        raise runtime.Fatal('Frozen comparison plan/code changed; preserve prior run and reconcile')
    if [focused.definition(t) for t in state['tasks']]!=plan['tasks']:
        raise runtime.Fatal('Frozen downstream task definitions changed')
    if state['production_stage']['task_ids']!=[t['id'] for t in plan['tasks']]:
        raise runtime.Fatal('Dispatch scope changed')
    for task in state['tasks']:
        if task.get('plan_seal'):verify_seal(run/task['plan_path'],task['plan_seal'])
    InputGuard(binding['files']).check()
    for call in state['calls']:
        if call.get('seal'):verify_seal(run/'calls'/call['id'],call['seal'])
    for versions in state['versions'].values():
        for version in versions.values():
            if sha(run/version['path'])!=version['sha256']:raise runtime.Fatal('Saved version changed')
    for path,digest in state.get('derived_inputs',{}).items():
        if sha(run/path)!=digest:raise runtime.Fatal('Derived comparison input changed')
    if state.get('downstream_prepared'):
        for key,unit in state['source_units'].items():
            contract=run/'inputs'/key/'unit-contract.json'
            if contract.exists() and {k:unit.get(k) for k in ('source_key','section','context','arm','assignment')}!=read_json(contract):
                raise runtime.Fatal('Derived assignment/source scope changed')
    return state


def freeze(run):
    if (run/'state.json').exists():verify(run);return
    if not all(books.speed.idle(p) for p in (ROOT,ROOT/'runs',run)):raise runtime.Fatal('Writer active')
    with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):
        plan=read_json(run/'plan-draft.json');core.validate_plan(plan)
        if not (run/'evaluation/critical-passages.json').exists():raise runtime.Fatal('Missing held-out source checks')
        plan.update(status='frozen',runtime_candidate=core.RUNTIME,
                    extraction_node='peer',gpu_fraction=.30,extraction_max_sequences=2,
                    extraction_request_retries=0,maximum_syntax_requests=6,maximum_readiness_requests=1,maximum_model_requests=19,
                    request_bound='12 primary downstream + at most 6 existing-policy syntax repairs + 1 program readiness. The unchanged GLM start helper additionally performs one max-32-token thinking-disabled startup smoke per actual restoration; its command/log are separate overhead. Finite page/region extraction; zero automatic model retries.')
        atomic_json(run/'plan.json',plan)
        parent=Path(read_json(ROOT/'results/focused-recovery-current.json')['run']);old=read_json(parent/'state.json')
        state={k:copy.deepcopy(old[k]) for k in ('chapter_contract','timing_policy','execution_limits','compiler_environment','concurrency_policy')}
        state.update(status='prepared',created_at=runtime.now(),suite_protocol='extraction-comparison-v1',first_dispatch=None,
                     calls=[],tasks=[],versions={},current_versions={},accuracy={},accuracy_records={},source_units={},
                     selection_ledger=[],connection_failures=0,active_stage=1,stages={'1':{}},production_stage={'task_ids':[]},
                     documents={},resource_phase='not_started',launches=[],derived_inputs={},syntax_lineages={},
                     extraction={},readiness_done=False,remote=f'/home/mdi/projects/pdf-to-latex-comparisons/{run.name}')
        shutil.copytree(parent/state['compiler_environment']['path'],run/state['compiler_environment']['path'])
        shutil.copyfile(parent/'effort-support-offline.json',run/'effort-support-offline.json')
        for arm in core.ARMS:
            for index,assignment in enumerate(plan['downstream']):
                key=f'{arm}-assignment-{index+1}';sid=key
                document=next(d for d in plan['documents'] if d['source_id']==assignment['source_id'])
                state['documents'][sid]={**document,'status':'pending_extraction','source_sha256':document['sha256']}
                state['source_units'][key]={'source_key':sid,'section':{'title':assignment['scope'],'blocks':[],'physical_pages':assignment['physical_pages']},'arm':arm,'assignment':index}
                for phase,effort,dependency in [('convert','high',None),('critic','max',key+'/convert'),('syntax','low',None)]:
                    state['tasks'].append({'id':key+'/'+phase,'key':key,'source_key':sid,'phase':phase,'reasoning_effort':effort,
                        'arm':'syntax' if phase=='syntax' else 'primary','extraction_arm':arm,'depends_on':dependency,
                        'status':'dormant' if phase=='syntax' else 'pending'})
        state['production_stage']['task_ids']=[t['id'] for t in state['tasks']]
        plan['tasks']=[focused.definition(t) for t in state['tasks']]
        atomic_json(run/'plan.json',plan)
        files={str(p.resolve()):sha(p) for directory in ('sources','evaluation') for p in (run/directory).rglob('*') if p.is_file()}
        files.update({d['original']:d['sha256'] for d in plan['documents']})
        baseline=run/'baseline-runtime-verified.json'
        if not baseline.exists():raise runtime.Fatal('Baseline identity recheck is missing')
        files[str(baseline.resolve())]=sha(baseline)
        prepared=run/'runtime-prepared.json'
        if prepared.exists():
            image=read_json(prepared)
            if image['node']!='peer' or image['base_image']!=core.RUNTIME or sha(image['recipe'])!=image['recipe_sha256']:
                raise runtime.Fatal('Prepared runtime provenance mismatch')
            state['runtime_image']=image['image'];files[str(prepared.resolve())]=sha(prepared)
        binding={'code':code_binding(),'plan_sha256':sha(run/'plan.json'),'files':files}
        atomic_json(run/'binding.json',binding);save(run,state)
        atomic_json(POINTER,{'run':str(run),'status':'prepared'})


def command(run,label,args,observe=None):
    folder=run/'host-operations';folder.mkdir(exist_ok=True)
    name=label+'-'+str(time.time_ns());atomic_json(folder/(name+'.command.json'),args)
    begin=time.monotonic()
    with (folder/(name+'.log')).open('w') as log:
        child=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT)
        while child.poll() is None:
            if observe is not None:observe()
            time.sleep(5)
        code=child.returncode
    atomic_json(folder/(name+'.outcome.json'),{'returncode':code,'elapsed_seconds':time.monotonic()-begin,
                 'scope':'Full host operation including setup, transport, model load, extraction and shutdown where applicable'})
    if code:raise runtime.Fatal(f'{label} failed ({code}); see {folder/(name+".log")}')


def ssh(text):return ['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',PEER,text]


def pause(run):
    if (run/'pause.json').exists():raise runtime.StopRun('Pause requested; current owned work settled')


def install_runtime(run,state):
    if shutil.disk_usage(ROOT).free<10*1024**3:raise runtime.Fatal('Head output disk reserve below 10 GiB')
    free=subprocess.check_output(ssh("df -B1 --output=avail /home/mdi | tail -n 1"),text=True).strip()
    if not free.isdigit() or int(free)<80*1024**3:raise runtime.Fatal('Peer peak download/build/output disk reserve below 80 GiB')
    if state.get('runtime_image'):
        actual=subprocess.check_output(ssh('docker image inspect '+shlex.quote(state['runtime_image'])+" --format '{{.Id}}'"),text=True).strip()
        if actual!=state['runtime_image']:raise runtime.Fatal('Prepared runtime image unavailable or changed')
        remote=state['remote']
        command(run,'peer-input-directories',ssh('mkdir -p '+' '.join(shlex.quote(remote+'/'+part) for part in ('input','models','outputs'))))
        return
    remote=state['remote'];state['stage']='isolated peer runtime installation';save(run,state)
    context=run/'runtime-build';context.mkdir(exist_ok=True)
    dockerfile=core.runtime_dockerfile()
    (context/'Dockerfile').write_text(dockerfile)
    command(run,'peer-directory',ssh('mkdir -p '+shlex.quote(remote+'/build')+' '+shlex.quote(remote+'/models')+' '+shlex.quote(remote+'/input')+' '+shlex.quote(remote+'/outputs')))
    command(run,'peer-build-file',['scp',str(context/'Dockerfile'),PEER+':'+remote+'/build/Dockerfile'])
    tag='pdf2tex-extraction-comparison:'+run.name
    command(run,'peer-sdk-build',ssh('docker build --pull=false -t '+shlex.quote(tag)+' '+shlex.quote(remote+'/build')))
    image=subprocess.check_output(ssh('docker image inspect '+shlex.quote(tag)+" --format '{{.Id}}'"),text=True).strip()
    if not re.fullmatch(r'sha256:[a-f0-9]{64}',image):raise runtime.Fatal('Invalid built image identity')
    state['runtime_image']=image;save(run,state)


def stage_inputs(run,state):
    archive=run/'peer-input.tar'
    with tarfile.open(archive,'w') as tar:
        tar.add(run/'plan.json',arcname='plan.json')
        tar.add(run/'sources',arcname='sources')
        for name in ('scripts/extraction_candidate_worker.py','probe/extraction_comparison.py','probe/__init__.py'):
            tar.add(ROOT/name,arcname=name)
    remote=state['remote']
    command(run,'transfer-frozen-inputs',['scp',str(archive),PEER+':'+remote+'/input.tar'])
    expected=sha(archive)
    actual=subprocess.check_output(ssh('sha256sum '+shlex.quote(remote+'/input.tar')),text=True).split()[0]
    if actual!=expected:raise runtime.Fatal('Transferred source identity mismatch')
    command(run,'unpack-owned-inputs',ssh('tar -xf '+shlex.quote(remote+'/input.tar')+' -C '+shlex.quote(remote+'/input')))


def container_args(state,action):
    remote=state['remote']
    models=state.get('remote_models',remote+'/models')
    args=['docker','run','--rm','--pull=never','--name','pdf2tex-'+Path(remote).name+'-'+action,
          '--label','pdf2tex.experiment='+Path(remote).name,'--user','1000:1000',
          '--network','bridge' if action=='download' else 'none','--shm-size','8g',
          '--cap-drop','ALL','--security-opt','no-new-privileges',
          '--mount',f'type=bind,src={remote}/input,dst=/study,readonly',
          '--mount',f'type=bind,src={models},dst=/models'+('' if action=='download' else ',readonly'),
          '--mount',f'type=bind,src={remote}/outputs/{action},dst=/output',
          '--workdir','/study','--env','HOME=/tmp','--env','HF_HOME=/tmp/hf',
          '--env','HF_HUB_DISABLE_TELEMETRY=1','--env','VLLM_NO_USAGE_STATS=1']
    if action!='download':args+=['--gpus','all','--env','HF_HUB_OFFLINE=1','--env','TRANSFORMERS_OFFLINE=1']
    return args+['--entrypoint','python3',state['runtime_image'],'-B','-u','/study/scripts/extraction_candidate_worker.py',action]


def extraction(run,state):
    install_runtime(run,state);stage_inputs(run,state);pause(run)
    if not state.get('models_downloaded'):
        state['stage']='download pinned candidate weights on peer';save(run,state)
        command(run,'model-output-dir',ssh('mkdir -p '+shlex.quote(state['remote']+'/outputs/download')))
        command(run,'pinned-model-downloads',ssh(shlex.join(container_args(state,'download'))))
        state['models_downloaded']=True;save(run,state)
    helpers=books.speed.module()
    if any(state.get('extraction',{}).get(arm,{}).get('status')=='running' for arm in ('mineru_pro','glm_ocr')):
        raise runtime.Fatal('Uncertain remote extraction; reconcile remote outcome before another launch')
    if all(state.get('extraction',{}).get(arm,{}).get('status') in ('finished','qualification_failed','failed') for arm in ('mineru_pro','glm_ocr')):return
    deployments=helpers.deployments()
    if not any(helpers.CONTAINER in names for names in deployments.values()):
        if not state.get('glm_owned_before_ocr') or state['resource_phase'] not in ('ocr_only','stopping_owned_idle_glm'):
            raise runtime.Fatal('GLM absent without an interrupted owned handoff; no inferred restart authority')
        policies=read_json(run/'service-restart-policies-before.json')
    else:
        policies={}
        for node in ('head','peer'):
            args=['docker','inspect','--format','{{json .HostConfig.RestartPolicy}}',helpers.CONTAINER]
            policies[node]=json.loads(helpers.checked(args if node=='head' else helpers.peer(shlex.join(args))))
            if policies[node].get('Name') not in ('no','') or policies[node].get('MaximumRetryCount',0)!=0:
                raise runtime.Fatal('Existing GLM restart policy differs from documented helper default; no service change')
        if not (run/'service-restart-policies-before.json').exists():atomic_json(run/'service-restart-policies-before.json',policies)
        elif read_json(run/'service-restart-policies-before.json')!=policies:raise runtime.Fatal('GLM restart policy changed across continuation')
    collection.resource_handoff(run,state,helpers)
    try:
        for arm in ('mineru_pro','glm_ocr'):
            pause(run)
            if state['extraction'].get(arm,{}).get('status') in ('finished','qualification_failed','failed'):continue
            books.book.guard_gpu_workloads(run,helpers)
            from probe.system_probe import parse_meminfo
            available=parse_meminfo(helpers.checked(helpers.peer('cat /proc/meminfo'))).get('MemAvailable')
            if not isinstance(available,int) or available<64*1024**3:
                raise runtime.Fatal('Peer has less than the 64 GiB candidate admission reserve after GLM handoff')
            command(run,'candidate-output-dir',ssh('mkdir -p '+shlex.quote(state['remote']+'/outputs/'+arm)))
            command(run,'clear-settled-pause',ssh('rm -f '+shlex.quote(state['remote']+'/outputs/'+arm+'/pause.json')))
            state['extraction'][arm]={'status':'running','started_at':runtime.now()};state['stage']='extraction '+arm;save(run,state)
            last_observation=[None]
            def observe():
                try:cp=subprocess.run(ssh('cat '+shlex.quote(state['remote']+'/outputs/'+arm+'/state.json')),capture_output=True,text=True,timeout=20)
                except subprocess.TimeoutExpired:
                    state['extraction'][arm]['monitor_diagnostic']='SSH observation timed out; owned extraction was not cancelled or retried'
                    save(run,state);return
                if cp.returncode:return
                try:observed=json.loads(cp.stdout)
                except ValueError:return
                records=observed.get('pages',{})
                state['extraction'][arm]['observed']={'at':runtime.now(),'status':observed.get('status'),
                    'completed':sum(p['status']=='completed' for p in records.values()),
                    'failed':sum(p['status'].startswith('failed') for p in records.values()),
                    'active':[key for key,p in records.items() if p['status']=='running']}
                value=state['extraction'][arm]['observed']
                signature=(value['completed'],value['failed'],tuple(value['active']))
                if signature!=last_observation[0]:
                    print('EXTRACTION',arm,'completed',value['completed'],'failed',value['failed'],'active',value['active'],flush=True)
                    last_observation[0]=signature
                save(run,state)
            try:
                command(run,'candidate-'+arm,ssh(shlex.join(container_args(state,arm))),observe=observe)
            except runtime.Fatal as exc:
                state['extraction'][arm].update(status='failed',error=str(exc))
            destination=run/'arms'/arm;destination.mkdir(parents=True,exist_ok=True)
            command(run,'collect-'+arm,['scp','-r',PEER+':'+state['remote']+'/outputs/'+arm+'/.',str(destination)])
            if (destination/'state.json').exists():
                outcome=read_json(destination/'state.json')
                state['extraction'][arm].update(outcome)
                if outcome['status']=='stopped_error':state['extraction'][arm]['status']='failed'
            for record in state['extraction'][arm].get('pages',{}).values():
                for entry in record.get('outputs',[]):
                    if sha(destination/core.check_relative(entry['path']))!=entry['sha256']:raise runtime.Fatal('Transferred output hash mismatch')
            save(run,state)
    finally:
        # Only restore if this experiment recorded ownership before stopping.
        if state.get('glm_owned_before_ocr'):
            if collection.helper_hashes(helpers)!=read_json(run/'service-helper-binding.json'):
                raise runtime.Fatal('GLM helpers changed; restoration requires reconciliation')
            books.book.arrange_glm(run)
            for node,expected in policies.items():
                args=['docker','inspect','--format','{{json .HostConfig.RestartPolicy}}',helpers.CONTAINER]
                actual=json.loads(helpers.checked(args if node=='head' else helpers.peer(shlex.join(args))))
                if actual!=expected:raise runtime.Fatal('Restored restart policy mismatch; downstream dispatch stopped')
            concurrent.capture_build(helpers,run)
            collection.verify_restart_configuration(run,helpers)
            state['resource_phase']='glm_restored';save(run,state)


def passage(text,index):
    patterns=(r'Case[ \t]*13\b(?=[ \t]*(?:[.:}*]|$))',r'Case[ \t]*19\b(?=[ \t]*(?:[.:}*]|$|McNolty\b))') if index==0 else (r'2[.\s]+Information\s+derivatives',r'3[.\s]+Risks\s+as\s+returns')
    matches=[]
    for pattern in patterns:
        hits=list(re.finditer(pattern,text,re.I|re.M))
        if len(hits)!=1:raise ValueError('Unique complete scope boundary unavailable: '+pattern)
        # Keep the complete heading line, including any TeX wrapper. Cutting at
        # the title substring would leave an unmatched macro at either boundary.
        matches.append(text.rfind('\n',0,hits[0].start())+1)
    if matches[0]>=matches[1]:raise ValueError('Source scope reordered')
    return text[matches[0]:matches[1]],matches


def prepare_downstream(run,state):
    if state.get('downstream_prepared'):return
    plan=read_json(run/'plan.json')
    for key,unit in state['source_units'].items():
        arm=unit['arm'];index=unit['assignment'];assignment=plan['downstream'][index]
        original=assignment['source_id'];destination=run/'inputs'/key;destination.mkdir(parents=True,exist_ok=True)
        try:
            if arm=='baseline':
                blocks=read_json(run/'sources'/original/'baseline.json')['blocks']
                text='\n\n'.join(b['tex'] for b in blocks if b['page']['original_physical_page'] in assignment['physical_pages'])
            else:
                text=''
                for page in assignment['physical_pages']:
                    ident=original+'-p'+str(page)
                    record=state['extraction'][arm]['pages'][ident]
                    if record['status']!='completed':raise ValueError('Extraction page unavailable: '+ident)
                    text+=(run/'arms'/arm/'pages'/ident/'text.md').read_text()+'\n\n'
            assigned,offsets=passage(text,index)
            block={'id':key+'-scope','kind':'text','tex':assigned,'native':{'content':assigned},
                   'page':{'original_physical_page':assignment['physical_pages'][0]}}
            native={'key':key,'title':assignment['scope'],'blocks':[block]}
            atomic_json(destination/'native.json',native)
            section=scope.target(native,[block['id']],title=assignment['scope']);section['physical_pages']=assignment['physical_pages']
            unit.update(section=section,context='Scope is only '+assignment['scope']+'. Earlier/later material outside the located boundaries is not assigned output.')
            atomic_json(destination/'unit-contract.json',{k:unit.get(k) for k in ('source_key','section','context','arm','assignment')})
            atomic_json(destination/'scope-provenance.json',{'source_id':original,'arm':arm,'physical_pages':assignment['physical_pages'],
                        'extraction_text_sha256':requests.digest(text),'character_boundaries':offsets,'scope_sha256':requests.digest(assigned),
                        'normalization':'Verbatim contiguous extraction slice; no mathematical repair'})
            quality=read_json(run/'sources'/original/'secondary-assessment.json')
            atomic_json(run/'quality'/(key+'.json'),{'pages':[p for p in quality['supplied_pages'] if p['physical_pdf_page'] in assignment['physical_pages']]})
            assets=[]
            baseline_blocks=read_json(run/'sources'/original/'baseline.json')['blocks']
            permitted={Path(a).name for b in baseline_blocks if b['page']['original_physical_page'] in assignment['physical_pages'] for a in b.get('assets',[])}
            for asset in next(d for d in plan['documents'] if d['source_id']==original)['assets']:
                source=run/asset['path'];relative='assets/'+source.name;target=run/'inputs'/relative;target.parent.mkdir(exist_ok=True)
                if source.name not in permitted:continue
                if target.exists() and sha(target)!=asset['sha256']:raise runtime.Fatal('Shared asset basename collision')
                if not target.exists():shutil.copyfile(source,target)
                assets.append(relative)
            atomic_json(destination/'assets.json',assets)
        except (ValueError,KeyError,FileNotFoundError) as exc:
            for task in state['tasks']:
                if task['key']==key:task.update(status='unavailable_extraction_scope',error=str(exc))
    for directory in ('inputs','quality'):
        for p in (run/directory).rglob('*'):
            if p.is_file():state['derived_inputs'][str(p.relative_to(run))]=sha(p)
    state['downstream_prepared']=True;save(run,state)


def bundle(run,state):
    report=['# Extraction comparison', 'Status: '+state['status'],
            'Recommendation: gather missing source-checked comparison evidence until the recorded extraction and downstream outcomes support adoption.',
            'Baseline is reused from saved extraction; its overlapping-window times are not paired per-page timings.',
            'Eight critical source pages were visually inspected before inference. Generated-output checks below are limited literal-fragment/structure checks; unresolved readings still require visual comparison. Normal completion and compilation do not certify mathematical accuracy.',
            'No conclusion about GLM reasoning savings follows from OCR scores. Compare the same two assignments and settings in downstream.csv.',
            'Expected readings and matched Information Geometry author TeX are evaluation-only.']
    rows=[]
    for call in state['calls']:
        task=next((t for t in state['tasks'] if t['id']==call['parent']),{})
        usage=call.get('metadata',{}).get('usage',{});total=usage.get('completion_tokens');reason=usage.get('completion_tokens_details',{}).get('reasoning_tokens')
        rows.append({'call':call['id'],'task':call['parent'],'arm':task.get('extraction_arm'),'phase':task.get('phase'),
                     'status':task.get('status',call['status']),'seconds':call.get('elapsed_seconds'),
                     'reasoning_tokens':reason,'final_tokens':total-reason if isinstance(total,int) and isinstance(reason,int) else None})
    with (run/'downstream.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['call','task','arm','phase','status','seconds','reasoning_tokens','final_tokens']);writer.writeheader();writer.writerows(rows)
    (run/'START-HERE.md').write_text('\n\n'.join(report)+'\n')
    plan=read_json(run/'plan.json');panels=[];page_rows=[];fragment_rows=[]
    checks=read_json(run/'evaluation/critical-passages.json')
    patterns={
        'original-496de5aa992285e2':r'(?:\\alpha|α)\s*\+\s*(?:\\rho|ρ)\s*[Xx]',
        'original-dcbf009549ec6318':r'b\s*\(\s*x\s*\)\s*=\s*f\s*\(\s*x\s*\)\s*m\s*\(\s*x\s*\)',
        'original-185f783748bb248e':r'(?:\\kappa|κ)\s*(?::?=|\\coloneqq)\s*[-−]\s*2\s*c',
        'original-59498c386e495139':r'[-−]\s*\\frac\s*\{\s*d\s*\\log',
    }
    for document in plan['documents']:
        baseline=read_json(run/'sources'/document['source_id']/'baseline.json')['blocks']
        for page in document['pages']:
            number=page['physical_pdf_page'];ident=document['source_id']+'-p'+str(number)
            columns=['<div><img width="500" src="'+html.escape(page['image'])+'"></div>']
            for arm in core.ARMS:
                if arm=='baseline':text='\n\n'.join(b['tex'] for b in baseline if b['page']['original_physical_page']==number)
                else:
                    p=run/'arms'/arm/'pages'/ident/'text.md';text=p.read_text() if p.exists() else 'No completed extraction; see arm diagnostics.'
                record=state.get('extraction',{}).get(arm,{}).get('pages',{}).get(ident,{})
                page_rows.append({'source_id':document['source_id'],'filename':document['filename'],'physical_page':number,
                                  'arm':arm,'status':'reused_saved' if arm=='baseline' else record.get('status','not_completed'),
                                  'seconds':None if arm=='baseline' else record.get('elapsed_seconds'),
                                  'memory_peak_torch_bytes':record.get('peak_torch_allocated_bytes'),
                                  'native_text_characters':len(text),'source_checked':'limited checks only'})
                critical=next((c for c in checks if c['source_id']==document['source_id'] and c['physical_pdf_page']==number),None)
                if critical:
                    pattern=patterns.get(document['source_id'])
                    normalized=re.sub(r'\\(?:left|right)\b','',text)
                    hit=re.search(pattern,normalized) if pattern else None
                    fragment_rows.append({'source_id':document['source_id'],'physical_page':number,'arm':arm,
                        'source_image_checked_reading':critical['source_image_checked_reading'],
                        'status':'literal_source_fragment_present' if hit else 'requires_visual_output_comparison',
                        'matched_text':hit.group(0) if hit else None,
                        'limitation':'Fragment presence does not verify the full equation, other passages, reading order, or mathematical equivalence.'})
                columns.append('<div><h3>'+arm+'</h3><pre>'+html.escape(text)+'</pre></div>')
            panels.append('<h2>'+html.escape(document['filename'])+' — physical page '+str(number)+'</h2><section>'+''.join(columns)+'</section>')
    (run/'comparison.html').write_text('<!doctype html><meta charset="utf-8"><title>Extraction comparison</title><style>section{display:flex;gap:1em;overflow:auto}section>div{min-width:500px;max-width:600px}pre{white-space:pre-wrap}</style>'+''.join(panels))
    with (run/'extraction-pages.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(page_rows[0]));writer.writeheader();writer.writerows(page_rows)
    atomic_json(run/'evaluation/fragment-results.json',fragment_rows)
    report.extend(['## Actual outcomes','|Arm|Completed/reused pages|Failed or unavailable pages|','|---|---:|---:|'])
    for arm in core.ARMS:
        actual=[p for p in page_rows if p['arm']==arm];good=sum(p['status'] in ('completed','reused_saved') for p in actual)
        report.append(f'|{arm}|{good}|{len(actual)-good}|')
    report+=['## Downstream observations','|Arm|Assignment|Phase|Status|Seconds|Reasoning tokens|Final tokens|','|---|---|---|---|---:|---:|---:|']
    for row in rows:
        report.append('|'+ '|'.join(str(row.get(k)) for k in ('arm','task','phase','status','seconds','reasoning_tokens','final_tokens'))+'|')
    report.append('Per-call durations can overlap. These are two matched assignments with at most two concurrent local requests, not an isolated throughput benchmark. Missing critics are unavailable, not zero cost. Syntax requests are additional repair work, separate from the 12 primary requests.')
    report+=['## Task dispositions','\n'.join('- '+t['id']+': '+t['status']+(' — '+str(t['error']) if t.get('error') else '') for t in state['tasks'])]
    (run/'START-HERE.md').write_text('\n\n'.join(report)+'\n')
    archive=ROOT/'results/inspection'/('extraction-comparison-'+run.name+'-'+str(time.time_ns())+'.zip');archive.parent.mkdir(exist_ok=True)
    included=[];omitted=[]
    for p in run.rglob('*'):
        if not p.is_file() or p.is_symlink():continue
        relative=p.relative_to(run)
        if (any(x in relative.parts for x in ('runtime-build','peer-input.tar','host-operations','compiler-environment')) or
            p.name.endswith(('.jsonl','.ndjson')) or 'wire' in p.name or p.stat().st_size>8*1024*1024 or
            (relative.parts[0]=='sources' and 'assets' in relative.parts)):
            omitted.append({'existing_path':str(p),'bytes':p.stat().st_size,'reason':'bulk transport/setup evidence or redundant asset; original retained'});continue
        included.append((p,relative))
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        manifest=[]
        for p,relative in included:
            z.write(p,str(relative));manifest.append({'path':str(relative),'sha256':sha(p),'bytes':p.stat().st_size})
        import hashlib
        omitted_bytes=json.dumps(omitted,indent=2).encode()
        z.writestr('OMITTED-ASSETS.json',omitted_bytes)
        manifest.append({'path':'OMITTED-ASSETS.json','sha256':hashlib.sha256(omitted_bytes).hexdigest(),'bytes':len(omitted_bytes)})
        for name in ('scripts/extraction_comparison.py','scripts/extraction_candidate_worker.py','probe/extraction_comparison.py','tests/test_extraction_comparison.py'):
            p=ROOT/name;target='implementation/'+name;z.write(p,target);manifest.append({'path':target,'sha256':sha(p),'bytes':p.stat().st_size})
        z.writestr('FILE-HASHES.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise runtime.Fatal('Inspection ZIP failed CRC')
    state['inspection']=str(archive);save(run,state);return archive


def worker(run):
    with (run/'terminal.log').open('a',buffering=1) as log:
        os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
        with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):
            state=verify(run)
            if state['status']==TERMINAL:return
            try:
                state.update(status='running',diagnostic=None);state['launches'].append({'at':runtime.now(),'pid':os.getpid()});save(run,state)
                runtime.check_other_jobs();books.qualify_compiler(run,state)
                result=collection.tex_compile.compile_document(r'\documentclass{article}\usepackage{amsmath,graphicx}\begin{document}$x^2$\end{document}',run/'compiler-preflight'/str(time.time_ns()),image=state['compiler_environment']['image'],passes=2)
                if not result['compilation_claim']:raise runtime.Fatal('Compiler preflight failed')
                extraction(run,state);pause(run)
                bundle(run,state)  # Raw comparison exists before any downstream rewriting.
                prepare_downstream(run,state)
                helpers=books.speed.module();books.book.arrange_glm(run,check_only=True);concurrent.capture_build(helpers,run)
                effort=books.speed.effort_check(run,helpers)
                if effort.get('status')!='supported':raise runtime.Fatal('Effective effort mapping unverified')
                state['low_supported']=effort['low_supported']
                sample=books.speed.sampler(run,state,helpers);books.speed.healthy(sample(0))
                if not state['readiness_done']:
                    if any(c['parent']=='readiness' for c in state['calls']):raise runtime.Fatal('Consumed/uncertain readiness')
                    runtime.readiness(run,state);state['readiness_done']=True;save(run,state)
                for call in state['calls']:
                    if call['parent']=='readiness':continue
                    task=next(t for t in state['tasks'] if t['id']==call['parent'])
                    if task.get('settled_call')==call['id']:continue
                    folder=run/'calls'/call['id']
                    if not (folder/'manifest.json').exists():raise runtime.Fatal('Uncertain prior model request; no replay')
                    verify_seal(folder);call.update(read_json(folder/'outcome.json'));call['seal']=sha(folder/'manifest.json')
                    answer=(folder/'content.txt').read_text() if call['status']=='completed_response' else None
                    focused.finish(run,state,task,answer,call)
                state['stage']='paired downstream';save(run,state)
                active=[]
                def changed():
                    focused.adjust(run,state)
                    active[:]=[t for t in state['tasks'] if t['status'] not in ('dormant','not_needed')]
                    progress(run,state)
                changed()
                concurrent.coordinate(run,state,active,body_for=focused.body_for,finish=focused.finish,
                    verify=lambda:verify(run),sample=sample,changed=changed,fixed_level=2,
                    before_reserve=lambda s,t,b:focused.before(run,s,t,b))
                if any(t['status'] in ('pending','running','dormant') for t in state['tasks']):raise runtime.Fatal('Frozen tasks remain unfinished')
                state.update(status=TERMINAL,finished_at=runtime.now(),stage='finished; no next queue')
            except runtime.StopRun as exc:
                state.update(status='stopped_error' if isinstance(exc,runtime.Fatal) else 'paused',diagnostic=str(exc))
            except BaseException as exc:
                state.update(status='stopped_error',diagnostic=type(exc).__name__+': '+str(exc),traceback=concurrent.exception_trace(run,exc,'Extraction comparison'))
            finally:save(run,state);bundle(run,state)
    mathpix=ROOT/'results/mathpix-comparison-current.json'
    if mathpix.exists():
        from probe.extraction_comparison_report import combine
        combined=combine(ROOT,Path(read_json(mathpix)['run']))
        if combined:print('Combined inspection:',combined,flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('freeze','run','resume','worker','status','pause','bundle'));parser.add_argument('--run',type=Path)
    args=parser.parse_args();run=(args.run or Path(read_json(POINTER)['run'])).resolve()
    if args.action=='freeze':freeze(run);print(run);return
    if args.action=='status':print(json.dumps(read_json(run/'progress.json'),indent=2));return
    if args.action=='pause':
        atomic_json(run/'pause.json',{'at':runtime.now()})
        if (run/'state.json').exists():
            state=read_json(run/'state.json')
            for arm,record in state.get('extraction',{}).items():
                if record.get('status')=='running':
                    command(run,'remote-drain',ssh('touch '+shlex.quote(state['remote']+'/outputs/'+arm+'/pause.json')))
        print('Pause requested; owned page/model work drains.');return
    if args.action=='worker':worker(run);return
    state=verify(run)
    if args.action=='bundle':
        with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):print(bundle(run,state))
        return
    if state['status']==TERMINAL:print('Finished; zero new model, OCR or readiness requests.');return
    if not all(books.speed.idle(p) for p in (ROOT,ROOT/'runs',run)):raise runtime.Fatal('Existing writer; no duplicate launch')
    if any(c['status']=='in_progress' for c in state['calls']):raise runtime.Fatal('Uncertain model reservation; no replay')
    cp=subprocess.run(['tmux','has-session','-t',SESSION],capture_output=True,text=True)
    if cp.returncode==0:raise runtime.Fatal('Comparison tmux worker already exists')
    if cp.returncode!=1 or any(x in cp.stderr.lower() for x in ('permitted','denied')):raise runtime.Fatal('tmux inaccessible: '+cp.stderr)
    collection.normal_checks(run)
    (run/'pause.json').unlink(missing_ok=True)
    command_line=shlex.join([str(PYTHON),'-B','-u',str(Path(__file__).resolve()),'worker','--run',str(run)])
    subprocess.run(['tmux','new-session','-d','-s',SESSION,'cd '+shlex.quote(str(ROOT))+' && exec '+command_line],check=True)
    print('Persistent launch requested:',run)


if __name__=='__main__':main()
