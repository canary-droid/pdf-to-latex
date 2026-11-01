#!/usr/bin/env python3
"""One frozen five-stage suite. Never calls the production worker or adopts results."""
import argparse
from collections import Counter
import copy
import difflib
import fcntl
import html
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import editorial_chapters as book
from probe import speed_suite as suite, chapter_concurrency as concurrent, chapter_glm as runtime, chapter_protocol as protocol
from probe.common import atomic_json, read_json, sha, fingerprint, files_manifest, writer_lock
from probe.experiment import InputGuard, verify_seal

POINTER=ROOT/'results/speed-suite-current.json'
SESSION='pdf-speed-suite'
OVERNIGHT_STAGES={1:'A — High critic on six saved drafts',2:'B — Low conversion / Max critic',
                  3:'C — Four adjacent recap groups',4:'D — Larger coherent Bergomi units'}

def stages(state):
    return OVERNIGHT_STAGES if state.get('suite_protocol')==suite.OVERNIGHT else STAGES

def total(state):
    return len(state['suite_manifest']['tasks'])

PYTHON=ROOT/'.venv-control/bin/python'
STAGES={1:'Four-slot pending production sample',2:'Adjacent recap grouping',3:'High critic on saved Max controls',
        4:'Complete Klebaner Chapter 4: dual versus native input',5:'Low conversion with Max criticism'}


def hashes():
    return {**book.code_hashes(),**{p:sha(ROOT/p) for p in ('scripts/speed_suite.py','scripts/run-speed-suite.sh','scripts/overnight_suite.py','scripts/run-overnight-suite.sh')}}


def idle(path):
    lock=Path(path)/'.probe.lock'
    if not lock.exists():return True
    with lock.open() as f:
        try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return False
    return True


def source_folder(run,key):return run/('bergomi/inputs' if key.startswith('bergomi-') else 'inputs')/key


def call_folder(parent,call):return Path(call.get('inherited_from',parent))/'calls'/call['id']


def prepare(parent):
    """Copy only consumed inputs/control records; never write the production pointer."""
    parent=parent.resolve()
    if not idle(ROOT) or not idle(parent):raise RuntimeError('Production is still writing/draining; preparation deferred')
    book.converter_idle(ROOT)
    old=read_json(parent/'state.json');binding=read_json(parent/'binding.json')
    if old['binding_sha256']!=fingerprint(binding):raise runtime.Fatal('Production binding changed')
    if old['status'] not in ('paused','stopped_error','stage_finished_for_inspection') or any(c['status']=='in_progress' for c in old['calls']):
        raise RuntimeError('Production is not at a confirmed released handover')
    if POINTER.exists():raise RuntimeError('A suite preparation already exists; use its status/run, never duplicate it silently')
    run=book.chapter_inputs.new_path('speed-suite');run.mkdir()
    tasks=[];baselines={};consumed={str(parent/'state.json'):sha(parent/'state.json'),str(parent/'binding.json'):sha(parent/'binding.json')}
    copied=set()
    def copy_source(origin,key):
        if key in copied:return
        folder=source_folder(origin,key);dest=source_folder(run,key);dest.mkdir(parents=True)
        for name in ('source.tex','native.json','provenance.json','secondary.txt','secondary.json','assets.json'):
            p=folder/name
            if p.exists():shutil.copyfile(p,dest/name);consumed[str(p)]=sha(p)
        native=read_json(dest/'native.json');secondary=read_json(dest/'secondary.json')
        pages=[p['page']['original_physical_page'] for p in native['pages']]
        if pages!=sorted(set(pages)) or not all(p['page']['owner'] for p in native['pages']):raise ValueError('Owned chapter page duplication')
        if pages!=[p['physical_pdf_page'] for p in secondary['pages']]:raise ValueError('Dual-source page mismatch')
        for name in read_json(dest/'assets.json'):
            p=folder.parent/name;target=dest.parent/name
            if Path(name).is_absolute() or '..' in Path(name).parts or p.is_symlink():raise ValueError('Unsafe source asset')
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and sha(target)!=sha(p):raise ValueError('Conflicting asset identities')
            if not target.exists():shutil.copyfile(p,target)
            consumed[str(p)]=sha(p)
        copied.add(key)
    def historical(key,phase):
        t=next(t for t in old['tasks'] if t['key']==key and t['phase']==phase and t.get('call'))
        c=next(c for c in old['calls'] if c['id']==t['call']);folder=call_folder(parent,c)
        verify_seal(folder,c['seal'])
        request=read_json(folder/'request.json')
        if fingerprint(request)!=c['request_sha256']:raise ValueError('Historical request binding mismatch')
        expected='max' if phase=='critic' else 'high'
        if request.get('reasoning_effort')!=expected or request.get('max_tokens')!=131072 or request.get('model')!='glm53-regular':
            raise ValueError('Incompatible saved High/Max control')
        ident=key+'/'+phase
        if ident not in baselines:
            dest=run/'controls'/key/phase;dest.mkdir(parents=True)
            for name in ('request.json','answer.txt','response-metadata.json','outcome.json','settings.json'):
                p=folder/name
                if p.exists():shutil.copyfile(p,dest/name);consumed[str(p)]=sha(p)
            baselines[ident]={'task':t['id'],'call':c['id'],'folder':str(folder),'seal':c['seal'],
                'request_sha256':c['request_sha256'],'task_status':t['status'],'elapsed_seconds':c.get('elapsed_seconds'),
                'usage':c.get('metadata',{}).get('usage'),'finish_reason':c.get('metadata',{}).get('finish_reason'),
                'input_version':c.get('concurrency_binding',{}), 'selected_version':old['versions'].get(key,{}).get(old['current_versions'].get(key))}
        return t,c,request
    def original(key):return next(t for t in old['tasks'] if t['key']==key and t['phase']=='convert')
    def add_pair(stage,arm,original_task,*,section=None,body=None,reason='',recipe='production'):
        key=f's{stage}-{arm}-{original_task["key"]}'
        copy_source(parent,original_task['source_key'])
        native=read_json(source_folder(run,original_task['source_key'])/'native.json')
        new=[]
        for phase in ('convert','critic'):
            t={'id':key+'/'+phase,'key':key,'stage':stage,'arm':arm,'phase':phase,'status':'pending',
               'source_key':original_task['source_key'],'section':copy.deepcopy(section or original_task.get('section')),
               'context':original_task.get('context',''),'reasoning_effort':'max' if phase=='critic' else 'low' if stage==5 else 'high',
               'depends_on':key+'/convert' if phase=='critic' else None,'request_recipe':recipe,'draft_label':None,
               'selection_reason':reason,'baseline':original_task['key']}
            t['coverage']=book.recovery.section_coverage(t,native);new.append(t);tasks.append(t)
        if body is None:body=book.body_for(run,{'phase_efforts':{'convert':'high','critic':'max'}},new[0])
        freeze_request(run,new[0],body)
        # Actual critic body depends on a not-yet-produced draft. Seal its recipe,
        # complete source inputs and dependency now, exact body/hash at dispatch.
        atomic_json(run/'prepared'/key/'critic-dependency.json',{'task':new[1],'input_status':'awaiting own completed conversion',
            'no_placeholder_dispatch':True,'template_code_sha256':sha(ROOT/'probe/chapter_editorial.py')})
        return new
    # Stage 1: four genuinely pending, independent conversions of varied sizes.
    for key in ('bergomi-04-s03','bergomi-05-s01','bergomi-06-s01','bergomi-06-s06'):
        t=original(key)
        if t['status']!='pending' or any(c['parent']==t['id'] for c in old['calls']):raise ValueError('Stage 1 target is no longer untouched pending work')
        body=book.body_for(parent,old,copy.deepcopy(t))
        pair=add_pair(1,'four',t,body=body,reason='Untouched production section; varied mathematical size; independent full source context')
        atomic_json(run/'comparisons'/(pair[0]['key']+'.json'),{'allowed_difference':'scheduler concurrency only','body_difference':suite.difference(body,read_json(run/pair[0]['frozen_request']))})
    # Stage 2: adjacent digest entries with saved individual High/Max controls.
    for arm,keys in (('recap-a',('bergomi-02-s11','bergomi-02-s12')),('recap-b',('bergomi-02-s15','bergomi-02-s16'))):
        sections=[original(k)['section'] for k in keys];copy_source(parent,'bergomi-02')
        group=suite.grouped_section(sections,read_json(source_folder(run,'bergomi-02')/'native.json'))
        for key in keys:
            for phase in ('convert','critic'):historical(key,phase)
        pair=add_pair(2,arm,original(keys[0]),section=group,reason='Adjacent printed digest entries with complete saved individual controls; repeated headings retained')
        atomic_json(run/'comparisons'/(pair[0]['key']+'.json'),{'constituents':list(keys),'ordered_blocks':group['blocks'],
            'individual_controls':{k:{p:baselines[k+'/'+p] for p in ('convert','critic')} for k in keys},'only_intended_change':'target grouping'})
    # Stage 3: substantive preservation/PDE correction and difficult source uncertainty.
    saved_drafts={}
    for key,reason in (('bergomi-04-s01','Substantive omitted footnote and unresolved volatility coefficient'),
                       ('bergomi-04-s02','Terminal-condition and time-argument corrections'),
                       ('pilot-gatheral-07-s05','Difficult Lewis second-order coefficients; supplied section lacks external definitions')):
        t,c,b=historical(key,'critic');copy_source(parent,t['source_key'])
        newkey='s3-high-'+key
        text=b['messages'][0]['content'];draft=text.rsplit('\n\nCURRENT DRAFT:\n',1)[1].split('\n\nFINITE FINDINGS / ACCURACY LOG (attribution retained):\n',1)[0]
        if not book.chapter_accuracy.complete_document(draft):raise ValueError('Saved critic lacks a complete exact draft')
        matches=[v for v in old['versions'][key].values() if (parent/v['path']).read_text()==draft]
        if not matches:raise ValueError('Cannot bind historical critic draft to saved version')
        consumed[str(parent/matches[0]['path'])]=matches[0]['sha256']
        nt={'id':newkey+'/critic','key':newkey,'stage':3,'arm':'high','phase':'critic','status':'pending',
            'source_key':t['source_key'],'section':copy.deepcopy(t.get('section')),'context':t.get('context',''),
            'reasoning_effort':'high','depends_on':None,'draft_label':'saved-control-draft',
            'expected_draft_sha256':matches[0]['sha256'],'request_recipe':'exact_historical','baseline':key,
            'selection_reason':reason,'coverage':book.recovery.section_coverage(t,read_json(source_folder(run,t['source_key'])/'native.json'))}
        variant=suite.effort_variant(b,'high');freeze_request(run,nt,variant);tasks.append(nt);saved_drafts[newkey]=draft
        atomic_json(run/'comparisons'/(newkey+'.json'),{'baseline':baselines[key+'/critic'],'difference':suite.difference(b,variant),
            'assertion':'only reasoning_effort differs; exact draft, sources, notes and prompt preserved'})
    # Stage 4: reuse complete, already cached Chapter 4 (31 owned pages).
    kcache=ROOT/'runs/simple-chapter-glm-trial-20261026T210920Z-316b1a'
    copy_source(kcache,'klebaner-04');folder=source_folder(run,'klebaner-04');native=read_json(folder/'native.json')
    if [p['page']['original_physical_page'] for p in native['pages']]!=list(range(106,137)):raise ValueError('Klebaner Chapter 4 boundary mismatch')
    for arm in ('dual','native'):
        key='s4-'+arm+'-klebaner-04';nts=[]
        for phase in ('convert','critic'):
            t={'id':key+'/'+phase,'key':key,'stage':4,'arm':arm,'phase':phase,'status':'pending','source_key':'klebaner-04',
               'section':None,'context':'','reasoning_effort':'high' if phase=='convert' else 'max',
               'depends_on':key+'/convert' if phase=='critic' else None,'request_recipe':'short_chapter','baseline':'Open WebUI reported 16 minutes; unknown payload/settings, not a matched control',
               'coverage':book.recovery.section_coverage(None,native),'draft_label':None,
               'selection_reason':'Complete Klebaner Chapter 4 with both cached extractions, original PDF and assets; no Chapter 5'}
            tasks.append(t);nts.append(t)
        body=suite.chapter_request((folder/'source.tex').read_text(),(folder/'secondary.txt').read_text(),suite.asset_locators(native,read_json(folder/'assets.json')),arm=arm)
        freeze_request(run,nts[0],body)
        atomic_json(run/'prepared'/key/'critic-dependency.json',{'task':nts[1],'sources':'same as conversion arm; no undeclared MinerU in native critic','status':'awaiting own completed draft'})
    # Stage 5: two exact High production conversions, now Low, existing Max controls.
    for key in ('bergomi-04-s01','bergomi-04-s02'):
        t,c,b=historical(key,'convert');historical(key,'critic');variant=suite.effort_variant(b,'low')
        pair=add_pair(5,'low',t,body=variant,reason='Saved complete High/Max pair with equations, references, footnotes and substantive review findings')
        atomic_json(run/'comparisons'/(pair[0]['key']+'.json'),{'baseline':baselines[key+'/convert'],
            'difference':suite.difference(b,variant),'assertion':'only conversion reasoning_effort changes; critic remains Max'})
    pending_mapping=[]
    # Repeated subsection titles at chapter ends identify *opportunities*, not
    # permission to delete/reclassify content. All proposed IDs remain untouched.
    bychapter={}
    for t in old['tasks']:
        if t['phase']=='convert' and t['source_key'].startswith('bergomi-'):bychapter.setdefault(t['source_key'],[]).append(t)
    for source,items in bychapter.items():
        seen=set();group=[]
        for t in items:
            title=(t.get('section') or {}).get('title','').split(' (including')[0]
            recap=title in seen;seen.add(title)
            if recap and t['status']=='pending' and not any(c['parent']==t['id'] for c in old['calls']):group.append(t)
        if group:pending_mapping.append({'source_key':source,'tasks':[t['id'] for t in group],
            'ordered_blocks':[b for t in group for b in t['section']['blocks']],
            'native_characters':sum(len(t['section']['text']) for t in group),
            'status':'candidate only; source-page classification and adjacency must be checked before later production regrouping'})
    atomic_json(run/'pending-grouping-opportunities.json',pending_mapping)
    environment=copy.deepcopy(old['compiler_environment']);shutil.copytree(parent/environment['path'],run/environment['path'])
    shutil.copyfile(parent/'concurrency-runtime-binding.json',run/'concurrency-runtime-binding.json')
    consumed[str(parent/'concurrency-runtime-binding.json')]=sha(parent/'concurrency-runtime-binding.json')
    atomic_json(run/'historical-two-slot.json',old['concurrency_progress'])
    admitted=book.scheduled_tasks(old)
    atomic_json(run/'production-handover.json',{'parent':str(parent),'status':old['status'],'calls':len(old['calls']),
        'historical_calls':len(old.get('historical_calls',[])),'task_counts':dict(Counter(t['status'] for t in old['tasks'])),
        'admitted_task_counts':dict(Counter(t['status'] for t in admitted)),
        'converted_awaiting_critic':[t['id'] for t in admitted if t['phase']=='critic' and t['status']=='pending' and old['current_versions'].get(t['key'])],
        'pending':{p:sum(t['phase']==p and t['status']=='pending' for t in old['tasks']) for p in ('convert','critic')},
        'last_calls':[{k:c.get(k) for k in ('id','parent','status','reserved_at','completed_at','elapsed_seconds')} for c in old['calls'][-4:]],
        'chapter_2_s10':{'conversion':'call-083 completed_response, finish_reason stop; 37,323 final characters; document extraction ambiguous: surrounded fence must contain one complete document, never multiple documents',
                         'critic':'unavailable; no eligible complete draft, no dispatched critic call. Raw answer retained; no recovery in this suite'},
        'pause_correction':'Pause requested 17:59:27 UTC while calls112/113 remained owned; actual drain completed18:20:54 UTC. Historical wording is premature, preserved unchanged.',
        'source_quality':'Recognized OCR/structural accounting is not independently verified fidelity',
        'production_pointer_unchanged':True})
    # Low template proof uses the exact host-mounted metadata, no weights/key.
    recorded=read_json(run/'concurrency-runtime-binding.json')['nodes'][0]['installed']
    model=next(iter(recorded['model_metadata_hashes']));template=Path(model.replace('/root/.cache/huggingface','/home/mdi/models/tensorfold/huggingface'))/'chat_template.jinja'
    low={'runtime_check':'required at launch via installed request-options + actual template rendering',
         'recorded_request_options_sha256':recorded['installed_source_hashes']['server/request_options.py']}
    if template.exists():
        if sha(template)!=recorded['model_metadata_hashes'][model]['chat_template.jinja']:raise ValueError('Host template differs from serving evidence')
        text=template.read_text()
        low.update(template_sha256=sha(template),template_path=str(template),
                   offline_low_branch="reasoning_effort in ['low', 'high'] else 'max'" in text and 'Reasoning Effort: {{ effective_reasoning_effort | capitalize }}' in text,
                   offline_render='Controller has no Jinja2; inspected exact branch read-only. Installed renderer executes at operator launch, without generation.',
                   interpretation='Low template path verified; actual effective model behavior is not attested by usage')
        # HF metadata snapshots are symlinks to small content-addressed blobs.
        # Bind the resolved metadata file; never relax InputGuard for book inputs.
        consumed[str(template.resolve())]=sha(template)
    atomic_json(run/'effort-support-offline.json',low)
    prepare_source_checks(run)
    checkpoint=subprocess.run(['git','log','-1','--format=%H'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip()
    manifest={'protocol':suite.VERSION,'created_at':runtime.now(),'checkpoint':checkpoint,'parent':str(parent),
        'tasks':[suite.frozen_task(t) for t in tasks],'stage_caps':suite.CAPS,'maximum_work_generations':suite.TOTAL,
        'reference_concurrency':2,'stage1_concurrency':4,'attempts_per_work_request':1,
        'readiness':'one small request per genuine initial launch/resume; terminal run/resume zero requests',
        'deadline':None,'generation_deadline':None,'connection_timeout_seconds':10,
        'final_status':suite.TERMINAL,'production_adoption':False,'stage_order':list(STAGES),
        'request_dependency_policy':'Future critics seal exact sources/template/settings/dependency now; actual body and draft hash are persisted before dispatch',
        'estimates':estimate(tasks,baselines,old),'controls':baselines}
    suite.validate_manifest(manifest)
    atomic_json(run/'suite-manifest.json',manifest)
    state={'suite_protocol':suite.VERSION,'suite_manifest':manifest,'status':'prepared_offline','created_at':runtime.now(),
        'chapter_contract':'annotated-chapter-v1','timing_policy':'manual_only','execution_limits':{'calls':None,'attempts_per_unit':1},
        'first_dispatch':None,'calls':[],'historical_calls':[],'source_history':{'parent':str(parent),'calls':len(old['calls'])},
        'tasks':tasks,'current_versions':{},'versions':{},'accuracy':{},'accuracy_records':{},'connection_failures':0,
        'compiler_environment':environment,'phase_efforts':{'convert':'high','critic':'max'},
        'concurrency_policy':copy.deepcopy(concurrent.POLICY),'active_stage':None,'reference_concurrency':None,
        'stage':'prepared','launches':[],'stages':{str(n):{'name':title,'status':'pending','sessions':[]} for n,title in STAGES.items()},
        'production_stage':{'task_ids':[t['id'] for t in tasks]},'acceptance':'EXPERIMENTAL_UNACCEPTED',
        'scope':'Frozen local experiments only; never adopt or continue either book'}
    for key,text in saved_drafts.items():
        book.remember(run,state,key,'saved-control-draft',text,{'source':'exact historical critic input','acceptance':'UNACCEPTED'})
        state['current_versions'][key]='saved-control-draft'
    own={str(p):sha(p) for folder in ('inputs','bergomi/inputs','prepared','controls','comparisons') for p in (run/folder).rglob('*') if p.is_file()}
    own[str(run/'suite-manifest.json')]=sha(run/'suite-manifest.json')
    for key in saved_drafts:
        v=state['versions'][key]['saved-control-draft'];own[str(run/v['path'])]=v['sha256']
    binding={'protocol':suite.VERSION,'code':hashes(),'consumed':consumed,'prepared':own,'manifest_sha256':sha(run/'suite-manifest.json'),
             'compiler_environment':environment,'runtime_identity':read_json(run/'concurrency-runtime-binding.json')['identity']}
    atomic_json(run/'binding.json',binding);state['binding_sha256']=fingerprint(binding)
    runtime.save(run,state);verify(run);report(run,state);bundle(run,state)
    atomic_json(POINTER,{'run':str(run)});print('PREPARED, NOT RUNNING:',run)
    return run


def prepare_source_checks(run):
    """A small, fixed Codex inspection outside every model input and template."""
    from probe.saved_pages import render_region
    folder=run/'source-checks';folder.mkdir()
    shutil.copyfile(ROOT/'docs/evidence/bounded-speed-suite-source-checks-20261029.md',folder/'assessment.md')
    cases=[('bergomi',113,96,'Adjacent digest statements and formula controls'),
           ('bergomi',151,134,'Missing square in volatility drift: source versus extraction origin'),
           ('bergomi',154,137,'Density definition, terminal condition and variation PDE'),
           ('gatheral',128,97,'Lewis J(3) source discrepancy and limits of the saved Max interpretation')]
    records=[]
    for bookname,physical,printed,scope in cases:
        name=f'{bookname}-p{physical}.png';pdf=ROOT/'inputs'/bookname/'source.pdf'
        render_region(pdf,physical-1,folder/name,max_edge=2100)
        records.append({'source':str(pdf),'physical_page':physical,'printed_page':printed,'image':name,
            'scope':scope,'new_output_assessment':'pending; no suite inference yet','source_image_inspection':'Codex, 29 October 2026; bounded to named formula regions'})
    atomic_json(folder/'index.json',records)


def freeze_request(run,task,body):
    path=Path('prepared')/task['key']/(task['phase']+'-request.json')
    atomic_json(run/path,body);task['frozen_request']=str(path);task['preview_hash']=fingerprint(body)
    atomic_json(run/path.with_name(task['phase']+'-budget.json'),protocol.budget(body,1048576))


def estimate(tasks,baselines,old):
    """Size-aware ranges, not deadlines or a causal concurrency speedup."""
    result={}
    for n in STAGES:
        seconds=0;basis=[]
        for t in (t for t in tasks if t['stage']==n):
            base=baselines.get(t['baseline']+'/'+t['phase'])
            if n==2:
                constituents=[ot for ot in old['tasks'] if ot['phase']==t['phase'] and ot['source_key']==t['source_key']
                              and ot.get('section') and set(ot['section']['blocks'])<=set(t['section']['blocks']) and ot['key']+'/'+ot['phase'] in baselines]
                value=sum(baselines[ot['key']+'/'+ot['phase']]['elapsed_seconds'] for ot in constituents)
                method='sum of saved constituent controls; grouping overhead saving unknown'
            elif base and base.get('elapsed_seconds'):value=base['elapsed_seconds'];method='same saved target'
            else:
                size=len((t.get('section') or {}).get('text',''))
                candidates=[]
                for ot in old['tasks']:
                    if ot['phase']!=t['phase'] or not ot.get('call') or ot['status'] not in suite.GOOD:continue
                    c=next(c for c in old['calls'] if c['id']==ot['call'])
                    if c.get('elapsed_seconds'):candidates.append((abs(len((ot.get('section') or {}).get('text',''))-size),c['elapsed_seconds']))
                value=sum(v for _,v in sorted(candidates)[:3])/max(1,len(sorted(candidates)[:3]));method='nearest three saved section sizes'
                if n==4:value=3600;method='complete 31-page chapter; very uncertain (not extrapolated from recap)'
            seconds+=value;basis.append({'task':t['id'],'seconds_basis':round(value,1),'method':method})
        slots=4 if n==1 else 2
        result[str(n)]={'hours_range':[round(max(.05,seconds/slots*.5/3600),2),round(max(.1,seconds*2/3600),2)],
                       'basis':basis,'note':'Planning range only; cache, reasoning, capacity serialization and output failures can exceed it. No execution deadline; no whole-book ETA inferred.'}
    return result


def verify(run,guard=None):
    if read_json(run/'binding.json')['code']!=hashes():
        raise runtime.Fatal('Changed suite code/binding; preserve evidence, no reseal')
    return recorded_evidence(run,guard)


def recorded_evidence(run,guard=None):
    """Verify recorded bindings without claiming historical calls used current code.

    Only explicit linked preparation uses this for an older implementation.
    Execution always enters through verify(), including the current-code check.
    """
    b=read_json(run/'binding.json');s=read_json(run/'state.json');m=read_json(run/'suite-manifest.json')
    if s['binding_sha256']!=fingerprint(b) or sha(run/'suite-manifest.json')!=b['manifest_sha256']:
        raise runtime.Fatal('Changed suite code/binding; preserve evidence, no reseal')
    suite.validate_manifest(m)
    if s['suite_manifest']!=m or [suite.frozen_task(t) for t in s['tasks']]!=m['tasks']:raise runtime.Fatal('Frozen suite tasks changed')
    if s['execution_limits']!={'calls':None,'attempts_per_unit':1} or s['production_stage']['task_ids']!=[t['id'] for t in s['tasks']]:
        raise runtime.Fatal('Changed frozen attempt/dispatch policy')
    if guard:guard.check()
    else:InputGuard({**b['consumed'],**b['prepared']})
    ids={t['id'] for t in s['tasks']};work=[c for c in s['calls'] if c['parent']!='readiness']
    if len(work)>len(ids) or len({c['parent'] for c in work})!=len(work) or any(c['parent'] not in ids for c in work):
        raise runtime.Fatal('Invalid consumed work history')
    for c in s['calls']:
        if c.get('seal'):
            folder=run/'calls'/c['id'];verify_seal(folder,c['seal'])
            if fingerprint(read_json(folder/'request.json'))!=c['request_sha256']:
                raise runtime.Fatal('Consumed call/request binding changed: '+c['id'])
    if b.get('linked_parent'):
        inherited=read_json(Path(b['linked_parent']['path'])/'state.json')['calls']
        if s['calls'][:len(inherited)]!=inherited:raise runtime.Fatal('Inherited call accounting changed')
    for vs in s['versions'].values():
        for v in vs.values():
            if sha(run/v['path'])!=v['sha256']:raise runtime.Fatal('Saved document changed')
    return s


def body_for(run,state,task):
    draft=suite.verify_draft(run,state,task)
    if task['phase']=='critic' and draft is None:return None
    if task.get('frozen_request'):body=read_json(run/task['frozen_request'])
    elif task['request_recipe'] in ('short_chapter','short_section'):
        folder=source_folder(run,task['source_key']);notes=(run/state['accuracy'][task['key']]).read_text() if task['key'] in state['accuracy'] else 'Accuracy notes unavailable; not a clean assessment.'
        body=suite.chapter_request((folder/'source.tex').read_text(),(folder/'secondary.txt').read_text(),
            suite.asset_locators(read_json(folder/'native.json'),read_json(folder/'assets.json')),arm='dual' if task['request_recipe']=='short_section' else task['arm'],draft=draft,notes=notes)
        if task['request_recipe']=='short_section':
            body=larger_body(run,task,draft=draft,notes=notes)
    else:body=book.body_for(run,state,task)
    if task['phase']=='critic':
        # Both dynamically constructed and exact historical bodies must contain
        # the exact selected input document, not a different arm's response.
        if draft not in body['messages'][0]['content']:raise runtime.Fatal('Critic body/draft mismatch')
        dest=run/'dispatch-previews'/task['id'].replace('/','-')
        if dest.with_suffix('.json').exists() and read_json(dest.with_suffix('.json'))['body']!=body:
            raise runtime.Fatal('Critic request changed after preparation')
        atomic_json(dest.with_suffix('.json'),{'body':body,'draft_sha256':task['dispatch_draft_sha256'],
            'task':task['id'],'request_sha256':fingerprint(body),'dependency':task.get('depends_on')})
    return body


def larger_body(run,task,*,draft=None,notes=''):
    folder=source_folder(run,task['source_key'])
    body=suite.chapter_request(task['section']['text'],task['secondary_target'],
        suite.asset_locators(read_json(folder/'native.json'),read_json(folder/'assets.json')),
        arm='dual',draft=draft,notes=notes)
    body['messages'][0]['content'] += ('\n\nOUTPUT SCOPE: '+task['section']['title']+
        '\nConvert/review the complete MinerU target section above. Native page excerpts may include adjacent material at page boundaries; that is context, not additional output. The following complete parent chapter is context only. No block markers are required.\n'+
        'PARENT CHAPTER — MINERU CONTEXT:\n'+(folder/'source.tex').read_text()+
        '\nPARENT CHAPTER — NATIVE PDF CONTEXT:\n'+(folder/'secondary.txt').read_text()+
        '\nAVAILABLE LOCAL CROSS-REFERENCES:\n'+task.get('context',''))
    return body


def module():
    spec=importlib.util.spec_from_file_location('suite_bergomi_helpers',ROOT/'scripts/run-bergomi-extraction.py')
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj


def sampler(run,state,helpers):
    from probe.local_model import LocalClient
    from probe.system_probe import parse_meminfo
    client=LocalClient(protocol.BASE_URL,protocol.MODEL,purpose='chapter',timeout=10)
    def sample(owned):
        folder=run/'samples'/str(time.time_ns());health,evidence=client.chapter_health(folder)
        memory={}
        for node in ('head','peer'):
            argv=['cat','/proc/meminfo'];raw=helpers.checked(argv if node=='head' else helpers.peer(shlex.join(argv)))
            memory[node]=parse_meminfo(raw).get('MemAvailable')
        obs={'health':health,'evidence':evidence,'memory_available_bytes':memory,'at':runtime.now(),'epoch':time.time(),'owned_at_sample':owned}
        atomic_json(folder/'observation.json',obs)
        if state.get('active_stage'):
            rec=state['stages'][str(state['active_stage'])];streams=health.get('streams',{})
            rec['max_server_streams']=max(rec.get('max_server_streams',0),streams.get('decoding',0)+streams.get('prefilling',streams.get('filling',0)))
            rec['last_observation']=str(folder/'observation.json')
            rec['minimum_memory_bytes']={n:min(rec.get('minimum_memory_bytes',{}).get(n,v),v) if type(v)is int else None for n,v in memory.items()}
        return obs
    return sample


def healthy(obs):
    limits=concurrent.health_limits(obs['health'],0,minimum_slots=1)
    memory=obs['memory_available_bytes']
    if len(memory)!=2 or any(type(v)is not int or v<concurrent.POLICY['minimum_available_bytes'] for v in memory.values()) or limits['paused']:
        raise runtime.Fatal('Unsafe shared memory/cache condition; all experiment dispatch stopped')
    return limits


def effort_check(run,helpers):
    argv=['docker','exec',helpers.CONTAINER,'python','-c',suite.EFFORT_CHECK]
    try:
        result=json.loads(helpers.checked(argv));recorded=read_json(run/'effort-support-offline.json')
        if result['options_sha256']!=recorded['recorded_request_options_sha256'] or result['template_sha256']!=recorded.get('template_sha256'):
            raise runtime.Fatal('Installed effort mapping/template changed from saved runtime')
        result['low_supported']=result['results']['low']=={'mapped':{'reasoning_effort':'low','enable_thinking':True},'rendered_label':'Low'}
        result['status']='supported' if result['low_supported'] else 'unsupported'
        if any(result['results'][e]['rendered_label']!=e.capitalize() for e in ('high','max')):
            raise runtime.Fatal('Installed High/Max mapping does not match requested labels')
    except runtime.Fatal:raise
    except (RuntimeError,ValueError,KeyError) as exc:result={'status':'probe_error','low_supported':False,'diagnostic':'Low rendering probe failed; only Low stage skips: '+str(exc)}
    atomic_json(run/'effort-support-live.json',result);return result


def run_stages(run,state,*,sample,verify_inputs,coordinator=concurrent.coordinate,low_supported=True,finish=None):
    """Finite stage loop; injectable scheduler for offline tests, no production branch."""
    def finalized(r,s,t,answer,call):
        start=time.monotonic();book.finish_task(r,s,t,answer,call)
        t['finalization_seconds']=time.monotonic()-start
    finish=finish or finalized
    titles=stages(state);overnight=state.get('suite_protocol')==suite.OVERNIGHT
    for number in titles:
        rec=state['stages'][str(number)]
        if rec['status'] in ('finished_for_inspection','skipped'):continue
        if (run/'pause.json').exists() or (run/'stop.json').exists():raise runtime.StopRun('Pause requested; no next stage dispatched')
        state.update(active_stage=number,stage=titles[number],status='running',diagnostic=None)
        active=suite.stage_tasks(state,number);concurrent.mark_uncertain(state,active)
        obs=sample(0);limits=healthy(obs)
        if state['reference_concurrency'] is None:
            state['reference_concurrency']=2 if limits['slots']>=2 else 1
            state['reference_reason']='Existing slots support two; oversized pairs serialize under unchanged shared-pool reservations' if limits['slots']>=2 else 'Common serial reference: current runtime has one slot'
        skip=None
        if number==1 and not overnight:
            conversions=[body_for(run,state,t) for t in active if t['phase']=='convert']
            budgets=[protocol.budget(b,limits['context']) for b in conversions]
            required=sum(b['combined_upper_estimate'] for b in budgets)
            rec['four_admission']={'observation':obs,'reserved_prompt_plus_outputs':required,'available_reservation_pool':int(limits['pool']*.90),'limits':limits}
            if limits['slots']<4 or required>int(limits['pool']*.90):skip='Four independent full prompt/output reservations not admissible on current slots/shared pool; no substitute requests'
        if number==(2 if overnight else 5) and not low_supported:skip='Installed Low mapping/template not verified; no none/other-model substitution'
        if skip:
            suite.finish_stage(state,number,skip=skip);runtime.save(run,state);report(run,state);continue
        level=4 if number==1 and not overnight else state['reference_concurrency']
        if limits['slots']<level:raise runtime.Fatal('Reference capacity changed within suite; no new scheduling arm')
        rec['status']='running';rec['level']=level;session={'started_at':runtime.now(),'started_epoch':time.time()};rec['sessions'].append(session)
        state['concurrency_progress']={'phase':'suite_stage','qualified_level':level,'trials':{},'sessions':[]}
        runtime.save(run,state);report(run,state);start=time.monotonic()
        try:
            coordinator(run,state,active,body_for=body_for,finish=finish,verify=verify_inputs,
                changed=lambda:report(run,state),sample=sample,fixed_level=level,before_reserve=suite.reservation_guard)
            suite.finish_stage(state,number)
        except BaseException:
            rec['status']='interrupted';raise
        finally:
            session.update(finished_at=runtime.now(),active_seconds=time.monotonic()-start)
            runtime.save(run,state);report(run,state)
    state.update(status=suite.TERMINAL,stage='All frozen stages ended; inspection only',active_stage=None)
    # No production continuation here, regardless of outcomes or apparent winner.
    runtime.save(run,state)


def report(run,state):
    started=time.monotonic();summary={'status':state['status'],'stage':state.get('stage'),'reference_concurrency':state.get('reference_concurrency'),
        'work_calls':sum(c['parent']!='readiness' for c in state['calls']),'readiness_calls':sum(c['parent']=='readiness' for c in state['calls']),
        'stages':{str(n):suite.metrics(run,state,n) for n in stages(state)},'tasks':state['tasks'],
        'recommendation':'Pending source inspection; no experimental output adopted. Complete responses/compilation are not mathematical accuracy.',
        'production_parent':state['source_history'],'last_diagnostic':state.get('diagnostic')}
    lines=['# Bounded local GLM speed suite',state['status']+' — '+state.get('stage',''),
        f'Separate experimental derivatives. At most {total(state)} work requests, one attempt each; readiness separate. Stops after the frozen final stage. No book continuation or adoption.',
        'Normal finish, source accounting, compilation, model review and independent source checks are separate outcomes.',
        f"Work: {summary['work_calls']}/{total(state)}; readiness: {summary['readiness_calls']}. Reference concurrency: {state.get('reference_concurrency') or '2 planned, live capacity check pending'}."]
    if state.get('local_recovery_parent'):
        link=state['local_recovery_parent'];summary['local_recovery_parent']=link
        lines += ['## Linked local recovery',
            f"Parent: {link['path']}. Historical stop: {link['historical_diagnostic']}. All {link['inherited_calls']} calls retain their original request/output bytes and implementation provenance.",
            'Stage A is finalized without resending its six requests. The findings-only critic retained the original draft; its existing notes/annotation were verified and reused. Suggestions were not applied and mathematical correctness is unverified. See local-recovery/ for the separate recovery record. Compilation of that annotation is a separate operator check.',
            'Only the 38 frozen B/C/D work requests remain, plus readiness once per actual launch. Low requires verified rendering; no production fall-through.']
    for n,title in stages(state).items():
        rec=state['stages'][str(n)];m=summary['stages'][str(n)];estimate=state['suite_manifest']['estimates'][str(n)]
        lines += [f'## Stage {n}: {title}',f"{rec['status']}; {m['usable_outputs']}/{m['work_calls']} usable responses; active batch {m['active_batch_seconds']:.1f}s; observed server streams {m['max_server_streams']}.",
                  f"Planning range {estimate['hours_range']} hours; estimate, never a deadline. {rec.get('diagnostic','')}",
                  '|Task|Result|seconds|reasoning|other completion|finish|Compilation|','|---|---|---:|---:|---:|---|---|']
        for t in suite.stage_tasks(state,n):
            row=next((r for r in m['rows'] if r['task']==t['id']),{})
            result=suite.document_result(state,t);v={'compilation':result['compilation']}
            t['document_result']=result
            lines.append('|'+ '|'.join(str(x) for x in (t['id'],t['status'],row.get('elapsed_seconds'),row.get('reasoning_tokens'),row.get('other_completion_tokens'),row.get('finish_reason'),v.get('compilation',{}).get('status','not attempted')+'; '+('complete model TeX' if result['complete_model_document'] else 'no model document from this call')))+'|')
            if t['status']=='critic_unchanged':
                lines.append(t['id']+': '+result['suggestions']+' Raw findings: calls/'+str(t.get('call'))+'/answer.txt')
        controls=state['suite_manifest'].get('controls',{})
        relevant={}
        for t in suite.stage_tasks(state,n):
            comparison=run/'comparisons'/(t['key']+'.json')
            keys=[t['baseline']]
            if comparison.exists():keys=read_json(comparison).get('constituents',keys)
            for ident,control in controls.items():
                if any(ident.startswith(str(k)+'/') for k in keys):relevant[ident]=control
        if relevant:
            lines += ['Historical context (individual request seconds, **not** serial wall time or accuracy ground truth):',
                      '|Saved control|seconds|completion|reasoning|finish|','|---|---:|---:|---:|---|']
            for ident,c in relevant.items():
                u=c.get('usage') or {};lines.append('|'+ '|'.join(str(x) for x in (ident,c.get('elapsed_seconds'),u.get('completion_tokens'),u.get('completion_tokens_details',{}).get('reasoning_tokens'),c.get('finish_reason')))+'|')
        if rec['status'] in ('finished_for_inspection','skipped'):
            conclusion='Inconclusive: stage skipped or no usable output.'
            if m['usable_outputs']:
                conclusion='Worth source-checking; delivery observed, accuracy and causal speedup not established.'
                if state.get('suite_protocol')!=suite.OVERNIGHT and n==1 and m['max_server_streams']<4:conclusion='Four-slot overlap not observed; concurrency level remains unqualified.'
            lines.append('Recommendation: '+conclusion)
    lines+=['## Evidence and limits',
        'Exact frozen bodies and dependent-critic recipes: prepared/. Actual requests, settings, raw streams, reasoning, answers, usage and failures: calls/. Model review notes: accuracy/. Original and revised TeX and compilation: versions/.',
        'Historical control outputs and request bindings: controls/ and suite-manifest.json. New-versus-control and initial-versus-critic diffs: diffs/. Source coverage: every task coverage sidecar distinguishes target blocks from context pages; output fidelity remains unverified.',
        'Independent inspection plan/findings: source-checks/. Historical controls are not truth. Native PDF text is not ground truth; no images are sent by this text route. Enormous reasoning/wire files stay local and are indexed in evidence-index.json.',
        'No whole-book speed promise from recap samples. Edit-only criticism, deterministic MinerU plus correction, and pinned runtime trials remain deferred.']
    if state.get('suite_protocol')==suite.OVERNIGHT:
        first_keys=list(dict.fromkeys(t['key'] for t in suite.stage_tasks(state,4)))[:2]
        checkpoint=[t for t in suite.stage_tasks(state,4) if t['key'] in first_keys]
        summary['early_diagnostic']={'complete':all(t['status'] not in ('pending','running') for t in checkpoint),
            'tasks':[{k:t.get(k) for k in ('id','status','call','error','structural_observations')} for t in checkpoint],
            'policy':'Nonblocking observation of first two larger units; no refill, quality approval or production promotion'}
        atomic_json(run/'early-diagnostic.json',summary['early_diagnostic'])
        remaining=[]
        for number,estimate in state['suite_manifest']['estimates'].items():
            pending={t['id'] for t in suite.stage_tasks(state,int(number)) if t['status'] in ('pending','running')}
            basis=sum(x['seconds_basis'] for x in estimate['basis'] if x['task'] in pending)
            # Adjust only within the same stage after at least two observations;
            # never extrapolate tiny recap latency to substantial chapters.
            ratios=[]
            by_id={x['task']:x for x in estimate['basis']}
            for row in summary['stages'][number]['rows']:
                if row['elapsed_seconds'] and row['task'] not in pending:
                    ratios.append(row['elapsed_seconds']/max(1,by_id[row['task']]['seconds_basis']))
            import statistics
            factor=statistics.median(ratios) if len(ratios)>=2 else 1
            remaining.append({'stage':number,'pending_tasks':len(pending),'within_stage_observations':len(ratios),
                              'hours_range':[round(basis*factor*.65/2/3600,1),round(basis*factor*1.5/3600,1)]})
        summary['remaining_planning_ranges']=remaining
        lines+=['Remaining planning ranges (hours; not deadlines or promised finish times): '+json.dumps(remaining),
                'Linked offline repairs and their own compilation: offline-repairs/index.json. Frozen controls remain unchanged.']
    atomic_json(run/'summary.json',summary)
    text='\n\n'.join(lines)+'\n';(run/'report.md').write_text(text)
    links=['suite-manifest.json','summary.json','production-handover.json','historical-two-slot.json','pending-grouping-opportunities.json','evidence-index.json']
    (run/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Bounded GLM suite</title>'+''.join('<p><a href="'+x+'">'+x+'</a></p>' for x in links)+'<pre style="white-space:pre-wrap">'+html.escape(text)+'</pre>')
    state['last_report_seconds']=time.monotonic()-started
    write_progress(run,state)


def write_progress(run,state,*,operator=False):
    active=[t['id'] for t in state['tasks'] if t['status']=='running']
    counts=dict(Counter(t['status'] for t in state['tasks']))
    progress={'at':runtime.now(),'state':state['status'],'stage':state.get('stage'),'active':active,
        'counts':counts,'work_calls':sum(c['parent']!='readiness' for c in state['calls']),
        'readiness_calls':sum(c['parent']=='readiness' for c in state['calls']),
        'planned_work':total(state),'latest_error':state.get('diagnostic') or next((t.get('error') for t in reversed(state['tasks']) if t.get('error')),None),
        'run':str(run),'log':str(run/'terminal.log'),'report':str(run/'report.html'),
        'zip':read_json(run/'last-inspection.json')['path'] if (run/'last-inspection.json').exists() else None,
        'scope':'Frozen experiment only; no production continuation; completion is not accuracy'}
    progress['diagnostic_file']=str(run/state['diagnostic_file']) if state.get('diagnostic_file') else None
    atomic_json(run/'progress.json',progress)
    if operator or os.environ.get('PDF2TEX_SUITE_OPERATOR')=='1':
        try:atomic_json(Path('/home/mdi/Downloads')/(run.name+'-progress.json'),progress)
        except OSError as exc:print('Progress copy unavailable:',exc,flush=True)


def bundle(run,state):
    """Compact final/partial inspection; huge raw/reasoning evidence stays linked."""
    evidence=[]
    for c in state['calls']:
        d=run/'calls'/c['id'];evidence.append({'call':c['id'],'task':c['parent'],'folder':str(d),'seal':c.get('seal'),
            'files':[{'name':p.name,'bytes':p.stat().st_size} for p in d.iterdir() if p.is_file()] if d.exists() else []})
        reasoning=d/'reasoning.txt'
        if reasoning.exists() and (c.get('failure_kind') or (c.get('elapsed_seconds') or 0)>1200):
            text=reasoning.read_text();out=run/'reasoning-excerpts'/c['id'];out.parent.mkdir(exist_ok=True)
            out.with_suffix('.txt').write_text('Excerpt only; full verbatim reasoning: '+str(reasoning)+'\n\n'+text[:1800]+'\n\n[...middle omitted from compact pack...]\n\n'+text[-1800:])
    atomic_json(run/'evidence-index.json',evidence)
    for key,versions in state['versions'].items():
        converted=next((v for k,v in versions.items() if k.startswith('convert-') and not k.endswith('-annotated')),None)
        current=versions.get(state['current_versions'].get(key))
        if converted and current:
            dest=run/'diffs'/(key+'.diff');dest.parent.mkdir(exist_ok=True)
            dest.write_text(''.join(difflib.unified_diff((run/converted['path']).read_text().splitlines(True),(run/current['path']).read_text().splitlines(True),fromfile=converted['path'],tofile=current['path'])))
        task=next(t for t in state['tasks'] if t['key']==key)
        baseline=run/'controls'/task['baseline']/task['phase']/'answer.txt'
        if not baseline.exists():baseline=run/'controls'/task['baseline']/'critic/answer.txt'
        baseline_text=baseline.read_text() if baseline.exists() else None
        comparison=run/'comparisons'/(key+'.json')
        if task['stage']==2 and state.get('suite_protocol')!=suite.OVERNIGHT and comparison.exists():
            baseline_text='\n\n'.join((run/'controls'/k/'critic/answer.txt').read_text() for k in read_json(comparison)['constituents'])
        if current and baseline_text is not None:
            dest=run/'diffs'/(key+'-historical-answer.diff');dest.parent.mkdir(exist_ok=True)
            dest.write_text(''.join(difflib.unified_diff(baseline_text.splitlines(True),(run/current['path']).read_text().splitlines(True),fromfile='historical final answer(s), source order, including notes',tofile=current['path'])))
    report(run,state)
    path=ROOT/'results'/('speed-suite-inspection-'+run.name.removeprefix('speed-suite-')+'-'+str(time.time_ns())+'.zip')
    roots=('prepared','comparisons','controls','versions','accuracy','diffs','source-checks','reasoning-excerpts','dispatch-previews','offline-repairs','historical-report','inventories','local-recovery','diagnostics')
    # The progress file inside the pack must also point to this pack, not its
    # predecessor. Final byte size is recorded after closing the archive.
    atomic_json(run/'last-inspection.json',{'path':str(path),'bytes':None,'status':state['status']})
    write_progress(run,state)
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
        for p in run.iterdir():
            if p.is_file() and p.suffix in ('.json','.md','.html'):z.write(p,p.name)
        for name in roots:
            for p in (run/name).rglob('*'):
                if p.is_file() and p.suffix in ('.json','.md','.tex','.txt','.diff','.pdf','.png','.jpg','.log'):
                    # Immutable container-build output isn't needed in this pack.
                    z.write(p,str(p.relative_to(run)))
        for c in state['calls']:
            for name in ('request.json','settings.json','answer.txt','response-metadata.json','outcome.json'):
                p=run/'calls'/c['id']/name
                if p.exists():z.write(p,str(p.relative_to(run)))
        # Each used relative asset once. Preserve editability without duplicating
        # every chapter's complete source-crop collection in the compact pack.
        added=set()
        for key,versions in state['versions'].items():
            source=next(t['source_key'] for t in state['tasks'] if t['key']==key)
            assets=book.selected_assets(run,source)
            for v in versions.values():
                for name in book.simple.image_references((run/v['path']).read_text()):
                    if name in assets and name not in added:z.write(assets[name],name);added.add(name)
        z.writestr('README.txt','Experimental outputs, not adopted book editions. Full raw responses/reasoning are indexed by local path. For standalone compilation copy assets/ beside the selected document.tex. No credentials included.\n')
    atomic_json(run/'last-inspection.json',{'path':str(path),'bytes':path.stat().st_size,'status':state['status']})
    write_progress(run,state)
    return path


def export_diagnostics(run):
    """Called only by the operator's live launcher/worker, never offline prepare."""
    try:
        target=Path('/home/mdi/Downloads')/(run.name+'-diagnostics.json')
        shutil.copyfile(run/'summary.json',target)
        shutil.copyfile(run/'report.md',target.with_suffix('.md'))
        print('Uploadable diagnostics:',target,flush=True)
    except OSError as exc:print('Downloads copy unavailable; diagnostics remain at',run/'summary.json',str(exc),flush=True)


def worker(run):
    os.environ['PDF2TEX_SUITE_OPERATOR']='1'
    with (run/'terminal.log').open('a',buffering=1) as log:
        os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
        state=verify(run)
        if state['status']==suite.TERMINAL:return
        b=read_json(run/'binding.json');guard=InputGuard({**b['consumed'],**b['prepared'],**{str(ROOT/p):h for p,h in b['code'].items()}})
        try:
            with writer_lock(ROOT),writer_lock(run):
                state.update(status='running',stage='workload and readiness',diagnostic=None)
                state.pop('diagnostic_file',None)
                state['launches'].append({'at':runtime.now(),'call_count_before':len(state['calls'])});runtime.save(run,state)
                try:
                    book.converter_idle(ROOT);runtime.check_other_jobs();helpers=module()
                    concurrent.capture_build(helpers,run);sample=sampler(run,state,helpers);healthy(sample(0))
                    low=effort_check(run,helpers)
                    if state.get('suite_protocol')==suite.OVERNIGHT:
                        from overnight_suite import compile_repairs, compile_local_recoveries
                        compile_repairs(run,state)
                        compile_local_recoveries(run,state)
                    # Exactly once per launch; never on a terminal no-op.
                    runtime.readiness(run,state)
                    run_stages(run,state,sample=sample,verify_inputs=guard.check,low_supported=low['low_supported'])
                except runtime.StopRun as exc:
                    manual=(run/'pause.json').exists() or (run/'stop.json').exists()
                    state.update(status='draining' if manual and not isinstance(exc,runtime.Fatal) else 'stopped_error',diagnostic=str(exc))
                except BaseException as exc:
                    state['diagnostic_file']=concurrent.exception_trace(run,exc,'Suite worker')
                    state.update(status='stopped_error',diagnostic=type(exc).__name__+': '+str(exc))
                finally:
                    runtime.save(run,state);report(run,state)
                    if state.get('diagnostic'):
                        print(state['diagnostic']+'; detail: '+str(run/state.get('diagnostic_file','state.json')),flush=True)
            # Publish paused only after both coordinator locks have been released.
            if state['status']=='draining':state['status']='paused'
            state['writer_released_at']=runtime.now();runtime.save(run,state);path=bundle(run,state)
            write_progress(run,state,operator=True);export_diagnostics(run)
            print('Suite ended:',state['status'],'Report:',run/'report.html','ZIP:',path,flush=True)
        except Exception as exc:
            print('Suite stopped:',type(exc).__name__,str(exc),flush=True);raise


def launch(run):
    state=verify(run)
    if state['status']==suite.TERMINAL:
        print('Suite already finished. Zero requests, including readiness. Report:',run/'report.html');return
    if any(c['status']=='in_progress' for c in state['calls']):raise RuntimeError('Uncertain in-flight reservation remains; inspect it read-only. No automatic resend/readiness.')
    if not idle(ROOT) or not idle(run):raise RuntimeError('Project/suite writer active or draining; no launch')
    probe=subprocess.run(['tmux','has-session','-t',SESSION],capture_output=True,text=True)
    if probe.returncode==0:raise RuntimeError('Suite session already active: '+SESSION)
    if probe.returncode!=1 or any(x in probe.stderr.lower() for x in ('permission denied','operation not permitted')):
        raise RuntimeError('Cannot inspect tmux: '+probe.stderr)
    # Include this new script and protocol in the once-per-identity full tests.
    identity=fingerprint({'code':hashes(),'tests':runtime.test_hashes()});record=run/'normal-terminal-checks.json'
    if not record.exists() or read_json(record).get('passed_identity')!=identity:
        path=run/('normal-terminal-tests-'+str(time.time_ns())+'.log');print('Running required tests once:',path,flush=True)
        with path.open('w') as f:result=subprocess.run([str(PYTHON),'-B','-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        atomic_json(record,{'passed_identity':identity if result.returncode==0 else None,'exit_status':result.returncode,'log':str(path)})
        if result.returncode:raise RuntimeError('Tests failed; no inference. See '+str(path))
    book.arrange_glm(run,check_only=True)
    for name in ('pause.json','stop.json'):(run/name).unlink(missing_ok=True)
    cmd=shlex.join([str(PYTHON),'-B','-u',str(Path(__file__).resolve()),'worker','--run',str(run)]+(['--overnight'] if state.get('suite_protocol')==suite.OVERNIGHT else []))
    subprocess.run(['tmux','new-session','-d','-s',SESSION,'cd '+shlex.quote(str(ROOT))+' && exec '+cmd],check=True)
    # Long diagnostic copy is an operator-runtime convenience, not a Codex write
    # outside its allowed working roots.
    try:
        dest=Path('/home/mdi/Downloads')/(run.name+'-preparation.txt');shutil.copyfile(run/'report.md',dest)
        print('Uploadable preparation summary:',dest)
    except OSError as exc:print('Downloads copy unavailable; use',run/'report.md',str(exc))
    print('STARTED persistent tmux:',SESSION,'\nFrozen suite; automatic final stop.\nRun:',run,'\nLog:',run/'terminal.log','\nReport:',run/'report.html')


def status(run):
    state=read_json(run/'state.json');counts=Counter(t['status'] for t in state['tasks'])
    locked=not idle(run);flag=(run/'pause.json').exists() or (run/'stop.json').exists()
    label='draining' if locked and flag else state['status']
    active=[t['id'] for t in state['tasks'] if t['status']=='running'];nextstage=next((n for n in stages(state) if state['stages'][str(n)]['status']=='pending'),None)
    print(f"{label}; stage {state.get('active_stage')}: {state.get('stage')}; writer {'owned' if locked else 'released'}")
    print('Active arm/target:',', '.join(active) or 'none')
    print('Running:',len(active),'completed:',sum(counts[x] for x in suite.GOOD),'pending:',counts['pending'],'skipped/unavailable:',counts['skipped']+counts['unavailable'],'other:',sum(v for k,v in counts.items() if k not in suite.GOOD|{'pending','running','skipped','unavailable'}))
    print('Next stage:',nextstage or 'none','; work calls:',sum(c['parent']!='readiness' for c in state['calls']),'/'+str(total(state))+'; readiness:',sum(c['parent']=='readiness' for c in state['calls']))
    print('Report:',run/'report.html','\nLog:',run/'terminal.log')
    if (run/'last-inspection.json').exists():print('ZIP:',read_json(run/'last-inspection.json')['path'])
    if state.get('diagnostic'):print('Diagnostic:',state['diagnostic'][:280],'; detail:',run/state.get('diagnostic_file','state.json'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','link-repair','run','resume','worker','status','pause','stop','bundle'))
    parser.add_argument('--overnight',action='store_true');
    parser.add_argument('--run',type=Path);parser.add_argument('--parent',type=Path);a=parser.parse_args()
    global POINTER,SESSION
    if a.overnight:
        POINTER=ROOT/'results/overnight-suite-current.json';SESSION='pdf-overnight-suite'
        if a.action=='prepare':
            from overnight_suite import prepare as prepare_overnight
            prepare_overnight();return
        if a.action=='link-repair':
            from overnight_suite import prepare_continuation
            prepare_continuation(a.parent or Path(read_json(POINTER)['run']));return
    if a.action=='link-repair':raise ValueError('Local finalization recovery is for the overnight suite only')
    if a.action=='prepare':prepare(a.parent or Path(read_json(book.POINTER)['run']));return
    run=(a.run or Path(read_json(POINTER)['run'])).resolve()
    if a.action in ('run','resume'):launch(run)
    elif a.action=='worker':worker(run)
    elif a.action=='status':status(run)
    elif a.action in ('pause','stop'):
        if read_json(run/'state.json')['status']==suite.TERMINAL:print('Already finished; no action.');return
        atomic_json(run/(a.action+'.json'),{'at':runtime.now()})
        print('pause_requested/draining: no new admission; pause retains active requests, stop saves partial streams. No paused claim until writer release.')
    elif a.action=='bundle':
        with writer_lock(run):print(bundle(run,read_json(run/'state.json')))


if __name__=='__main__':
    try:main()
    except Exception as exc:print('ERROR:',type(exc).__name__+':',exc,file=sys.stderr);sys.exit(1)
