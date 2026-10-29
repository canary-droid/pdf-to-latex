#!/usr/bin/env python3
"""Annotated simple chapter continuation; exact saved sources, serial local GLM only."""
import argparse
import copy
import csv
import html
import json
import os
import re
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import simple_chapter_glm as simple
from probe import chapter_editorial as edit, chapter_sources, chapter_inputs, chapter_glm as runtime, chapter_accuracy, compiler_environment, chapter_protocol, editorial_recovery as recovery, editorial_delivery as delivery, chapter_concurrency as concurrent
from probe.common import atomic_json, read_json, sha, fingerprint, files_manifest, writer_lock
from probe.experiment import verify_seal
from probe.saved_pages import converter_idle

ORIGINAL=Path('/home/mdi/projects/pdf-to-latex')
PARENT=ORIGINAL/'runs/simple-chapter-glm-trial-20261026T212942Z-533351'
BERGOMI=ORIGINAL/'runs/convert-basic-20261027T065138Z-f5d477'
POINTER=ROOT/'results/editorial-chapters-current.json'
SESSION='editorial-chapters'
CAPACITY_RECORDED=1048576


def code_hashes():
    paths={**runtime.code_hashes(),**{p:sha(ROOT/p) for p in ('scripts/editorial_chapters.py','scripts/run-editorial-chapters.sh',
        'scripts/simple_chapter_glm.py','docs/gatheral-editorial-plan.json','scripts/tex-compiler/Dockerfile',
        'docs/source-provenance/bergomi-page-classification-20261028.json','docs/gatheral-pilot-adoption-20261028.json',
        'scripts/integrate-editorial-development.py','scripts/run-editorial-continuation.sh',
        'docs/editorial-saved-repairs-20261029.json')}}
    return paths


def selected_assets(run,key):
    base=run/('bergomi/inputs' if key.startswith('bergomi-') else 'inputs')
    return {name:base/name for name in read_json(base/key/'assets.json')}


def remember(run,state,key,label,text,origin):
    dest=run/'versions'/key/label/'document.tex';dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():raise ValueError('Refusing to overwrite document version '+str(dest))
    dest.write_text(text,encoding='utf-8')
    record={'path':str(dest.relative_to(run)),'sha256':sha(dest),'origin':origin,'compilation':{'status':'not_attempted'}}
    state.setdefault('versions',{}).setdefault(key,{})[label]=record
    return record


def attach_notes(run,key,phase,answer,info,*,complete=True,before=None):
    notes,status=edit.notes_text(answer,info)
    record=edit.notes_record(key,notes,captured=status,complete=complete,phase=phase)
    if before:record=edit.reconcile_notes(before,record)
    folder=run/'accuracy'/key;folder.mkdir(parents=True,exist_ok=True)
    atomic_json(folder/(phase+'.json'),record)
    (folder/(phase+'.md')).write_text('# '+key+' '+phase+'\n\nCapture: '+record['capture_status']+'\n\n'+
        '\n\n'.join('## '+x['id']+'\nDisposition: '+x['status']+'\n\n'+x['text'] for x in record['items']),encoding='utf-8')
    (folder/(phase+'.raw.md')).write_text(notes,encoding='utf-8')
    return record


def copy_inputs(parent,run,key):
    src=parent/'inputs'/key;dst=run/'inputs'/key;dst.mkdir(parents=True)
    for name in ('source.tex','native.json','provenance.json','secondary.txt','secondary.json','assets.json'):
        shutil.copyfile(src/name,dst/name)
    for asset in read_json(src/'assets.json'):
        p=run/'inputs'/asset;p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists() and sha(p)!=sha(parent/'inputs'/asset):raise ValueError('Asset collision')
        if not p.exists():shutil.copyfile(parent/'inputs'/asset,p)


def bound_output(run,state,key,label):
    record=state['versions'][key][label];p=run/record['path']
    if sha(p)!=record['sha256']:raise runtime.Fatal('Saved version changed: '+str(p))
    return p.read_text()


def make_unit(run,state,key,phase,*,section=None,draft_label=None,context='',source_key=None):
    source_key=source_key or key
    i=len(state['tasks'])+1;ident=f'u{i:03d}-{key}-{phase}'
    task={'id':ident,'key':key,'source_key':source_key,'phase':phase,'status':'pending',
          'draft_label':draft_label,'section':section,'context':context,'attempt_limit':1}
    state['tasks'].append(task)
    save_preview(run,state,task)
    return task


def body_for(run,state,task):
    effort=edit.validate_effort(task.get('reasoning_effort',state.get('phase_efforts',{}).get(task['phase'],'max')))
    if task.get('request_input'):
        if task['phase']!='convert':raise ValueError('Historical request copy only applies to pilot conversion')
        body=read_json(run/task['request_input'])
        if body.get('reasoning_effort')!=effort:raise ValueError('Changed pilot request effort')
        return body
    folder=run/('bergomi/inputs' if task['source_key'].startswith('bergomi-') else 'inputs')/task['source_key'];primary=(folder/'source.tex').read_text();secondary=(folder/'secondary.txt').read_text()
    draft=None;notes='';section=None
    if task.get('section'):
        section=task['section']['title']+'\nExactly this coherent source section (source IDs stay in sidecars):\n'+task['section']['text']
    if task['phase']=='critic':
        label=task.get('draft_label') or state.get('current_versions',{}).get(task['key'])
        if not label:return None
        draft=bound_output(run,state,task['key'],label)
        acc=state.get('accuracy',{}).get(task['key'])
        if acc:notes=(run/acc).read_text()
    body=edit.request(primary,secondary,draft=draft,notes=notes,section=section,context=task.get('context',''),reasoning_effort=effort)
    try:chapter_protocol.budget(body,CAPACITY_RECORDED)
    except chapter_protocol.ContextBudgetGap:
        if not task.get('section'):return body  # live admission reports the intact oversized request
        from probe import critic_context
        data=read_json(folder/'native.json');group=task['section']
        rows=[{'block_id':b['id'],'text':b['tex'],'kind':b['kind'],
               'source_location':{'source_id':data['source'],'page':b['page']}} for b in data['blocks']]
        index=critic_context.build_index(rows,{'source':data['source'],'native_sha256':sha(folder/'native.json')})
        added,ledger=critic_context.resolve(index,critic_context.explicit_references(group['text']),exclude=group['blocks'])
        context='\n\n'.join(r['text'] for r in added)
        record=read_json(folder/'secondary.json');pages=record['pages']
        secondary=chapter_sources.render_pages([p for p in pages if p['physical_pdf_page'] in group['physical_pages']])
        scope='Full chapter exceeds conservative context capacity. The supplied complete section is the target. Other chapter sections are unavailable except explicitly retrieved references below; do not infer their contents.\n'
        body=edit.request(scope+group['text'],secondary,draft=draft,notes=notes,section=group['title'],context=context,reasoning_effort=effort)
        task['context_scope']={'mode':'coherent_section_with_bounded_exact_references','references':ledger,
                              'unavailable':'other chapter content and unconverted references; no clipping','full_chapter_context':False}
    return body


def save_preview(run,state,task):
    folder=run/'prepared'/task['id'];folder.mkdir(parents=True,exist_ok=True)
    body=body_for(run,state,task)
    if body is None:
        atomic_json(folder/'pending-draft.json',{'status':'awaits preceding complete conversion','policy':edit.POLICY,
                    'source_key':task['source_key'],'output_tokens':131072});return
    atomic_json(folder/'request.json',body)
    try:budget=chapter_protocol.budget(body,CAPACITY_RECORDED);budget['fit']='fits_recorded_capacity; live recheck required'
    except chapter_protocol.ContextBudgetGap as exc:budget={'fit':'context_gap','diagnostic':str(exc)}
    atomic_json(folder/'budget.json',budget);task['preview_hash']=fingerprint(body)


def normalize_bibliography(run,state,plan):
    key='gatheral-bibliography';source=bound_output(run,state,key,'reviewed-original')
    normalized=edit.apply_edits(source,plan);entries=edit.bibliography_entries(normalized)
    if len(entries)!=76:raise ValueError('Bibliography entry loss')
    old=edit.bibliography_entries(source);rows=[]
    for n,(a,b) in enumerate(zip(old,entries),1):
        rows.append({'key':f'gatheral-ref-{n:03d}','printed_or_original_glm_tex':a['text'],'normalized_tex':b['text'],
            'authors_explicit':not b['text'].startswith((',', '.')),
            'provenance':{'parent':str(PARENT),'entry':n,'physical_pdf_page':194 if n<=13 else 195 if n<=33 else 196 if n<=52 else 197 if n<=73 else 198},
            'unknown_fields_policy':'No invented fields; structured full reference retained in normalized_tex',
            'url_status':'unverified; never tested','author_expansion_status':'Codex source-sequence reading; coauthor dash scope remains inspectable' if a['text'].startswith(',') else 'explicit or repeated full-list expansion'})
    folder=run/'bibliography';folder.mkdir(exist_ok=True)
    atomic_json(folder/'references.json',{'format':'ordered structured references with stable keys, exact TeX and provenance','entries':rows,
         'source_pdf':str(ORIGINAL/'inputs/gatheral/source.pdf'),'external_metadata':plan['findings']})
    (folder/'printed-reference-version.tex').write_text(source)
    (folder/'normalized-reference-version.tex').write_text(normalized)


def prepare_gatheral(parent=PARENT,*,conversion_effort='max',critic_effort='max'):
    previous=None
    if POINTER.exists():
        prior=Path(read_json(POINTER)['run']);prior_state=read_json(prior/'state.json')
        if prior_state['calls']:raise ValueError('Existing editorial calls consumed; resume or prepare an explicit budget-preserving continuation, not a reset')
        previous={'path':str(prior),'binding_sha256':sha(prior/'binding.json'),'reason':'superseded offline preparation; no inference calls'}
    binding,old=simple.recorded_evidence(parent)
    if any(c['status']=='in_progress' for c in old['calls']):raise ValueError('Parent has unfinished calls')
    run=chapter_inputs.new_path('editorial-chapters-trial');run.mkdir(parents=True)
    plans=read_json(ROOT/'docs/gatheral-editorial-plan.json')
    state={'status':'prepared_offline','chapter_contract':edit.VERSION,'timing_policy':'manual_only','first_dispatch':None,'calls':[],
       'historical_calls':[dict(c,inherited_from=str(parent)) for c in old['calls']], 'historical_request_seconds':sum(c.get('elapsed_seconds',0) for c in old['calls']),
       'inherited_stages':{},'tasks':[],'versions':{},'current_versions':{},'accuracy':{},'accuracy_records':{},'connection_failures':0,
       'scope':'Gatheral chapters 1–11, postscript, bibliography; front/index source supplement; missing chapters explicit. Bergomi awaits completed OCR.',
       'compiler_environment':copy.deepcopy(old['compiler_environment']), 'bergomi_status':'awaiting_completed_extraction',
       'phase_efforts':{'convert':edit.validate_effort(conversion_effort),'critic':edit.validate_effort(critic_effort)}}
    shutil.copytree(parent/state['compiler_environment']['path'],run/state['compiler_environment']['path'])
    for key in [f'gatheral-{i:02d}' for i in range(1,12)]+['gatheral-postscript','gatheral-bibliography']:
        copy_inputs(parent,run,key)
        label,version=edit.current_version(old,key)
        if not version:continue
        state['inherited_stages'][key]={'conversion':'conversion_completed','critic':'critic_unchanged' if label=='first-glm' else 'critic_revised',
                                      'historical_compilation':version.get('compilation',{}).get('status','not_recorded')}
        initial=old['versions'][key]['first-glm']
        remember(run,state,key,'first-glm',(parent/initial['path']).read_text(),{'parent':str(parent),'record':initial})
        tex=(parent/version['path']).read_text()
        remember(run,state,key,'reviewed-original',tex,{'parent':str(parent),'record':version,'selection':label,
            'critic':'unchanged' if label=='first-glm' else 'revised'})
        folder=run/'accuracy'/key;folder.mkdir(parents=True,exist_ok=True)
        for phase in ('initial','post-critic'):
            src=parent/'chapters'/key/('accuracy-'+phase+'.json')
            if src.is_file():shutil.copyfile(src,folder/('historical-'+phase+'.json'))
        reply=(parent/'chapters'/key/'review.md').read_text()
        _,info=chapter_accuracy.envelope(reply,simple.extract_document)
        record=attach_notes(run,key,'recovered-critic',reply,info)
        plan=plans['chapters'][key];corrected=edit.apply_edits(tex,plan)
        for item in record['items']:
            link=plan.get('superseded_model_findings',{}).get(item['id'])
            if link:
                item['historical_text']=item['text'];item['text']='Historical GLM finding '+item['id']+' is superseded by Codex disposition '+link+'. Full original claim remains in recovered-critic.raw.md.'
                item['status']='superseded_with_recorded_disposition';item['codex_disposition']=link
        record['items'] += [dict(x,independent_verification=x['status'] in ('applied_verified','retained_verified')) for x in plan['findings']]
        atomic_json(folder/'reconciled-dispositions.json',record)
        state['accuracy_records'][key]=str((folder/'reconciled-dispositions.json').relative_to(run))
        # Program-owned findings supplement rather than rewrite historical model claims.
        changes=folder/'codex-dispositions.json';atomic_json(changes,plan)
        text='# Codex dispositions (source-audit and local checks; not GLM-authored)\n\n'+'\n\n'.join(
            '## '+x['id']+' — '+x['status']+'\n'+x['location']+'\n\n'+x['text'] for x in plan['findings'])
        (folder/'codex-dispositions.md').write_text(text)
        # Retain complete model notes in a visible appendix too, categorized separately.
        model_notes=[{'id':x['id'],'text':x['text'],'status':x['status'],'category':x['category'],
                      'label':'GLM recorded finding (historical claim; see subsequent Codex dispositions)', 'attribution':'GLM'}
                     for x in record['items'] if x['category']=='material' and x.get('attribution')=='GLM']
        annotated=edit.annotate(corrected,model_notes+plan['findings'])
        remember(run,state,key,'annotated-offline',annotated,{'source_version':'reviewed-original','plan_sha256':sha(ROOT/'docs/gatheral-editorial-plan.json')})
        state['current_versions'][key]='annotated-offline'
        state['accuracy'][key]=str((folder/'codex-dispositions.md').relative_to(run))
    normalize_bibliography(run,state,plans['chapters']['gatheral-bibliography'])
    from probe.documents import _fitz
    fitz=_fitz();supp=run/'source-supplement';supp.mkdir()
    with fitz.open(ORIGINAL/'inputs/gatheral/source.pdf') as source:
        output=fitz.open()
        for a,z in ((1,31),(199,210)):output.insert_pdf(source,from_page=a-1,to_page=z-1)
        output.save(supp/'gatheral-front-blank-index.pdf',garbage=3,deflate=True);output.close()
        (supp/'native-text.txt').write_text('\n\n'.join('Physical PDF '+str(n)+'\n'+source[n-1].get_text() for n in list(range(1,32))+list(range(199,211))))
    atomic_json(supp/'provenance.json',{'source':str(ORIGINAL/'inputs/gatheral/source.pdf'),'physical_pages':list(range(1,32))+list(range(199,211)),
        'status':'Original title/copyright, foreword/preface/acknowledgments and index preserved as source pages; not GLM converted or critic verified',
        'index':'Printed index points to original pagination; not the derivative','sha256':sha(supp/'gatheral-front-blank-index.pdf')})
    # Chapter 6 is the first recovery. Every coherent conversion is immediately reviewed.
    for chapter in (6,7,11):
        key=f'gatheral-{chapter:02d}';data=read_json(run/'inputs'/key/'native.json')
        groups=edit.section_groups(data)
        atomic_json(run/'inputs'/key/'section-plan.json',groups)
        for j,group in enumerate(groups,1):
            unit=key+f'-s{j:02d}'
            context=''
            if chapter==11:context=(run/'inputs/gatheral-02/source.tex').read_text()
            make_unit(run,state,unit,'convert',section=group,source_key=key,context=context)
            make_unit(run,state,unit,'critic',section=group,source_key=key,context=context)
    for key in plans['editorial_requests']:
        context=(run/'inputs/gatheral-02/source.tex').read_text() if key in ('gatheral-03','gatheral-05') else ''
        if key=='gatheral-10':context+=(run/'bibliography/normalized-reference-version.tex').read_text()
        make_unit(run,state,key,'critic',draft_label='annotated-offline',context=context)
    atomic_json(run/'inputs/manifest.json',files_manifest(run/'inputs'))
    atomic_json(run/'prepared/manifest.json',files_manifest(run/'prepared'))
    state['execution_limits']={'attempts_per_unit':1,'calls':2*len(state['tasks'])+32,
        'basis':'one call per sealed new unit plus bounded readiness on resumes; historical 24 calls retained separately'}
    baseline={'version':edit.VERSION,'supersedes_offline':previous,'parent':str(parent),'parent_binding_sha256':sha(parent/'binding.json'),'parent_state_sha256':sha(parent/'state.json'),
       'code':code_hashes(),'inputs_seal':sha(run/'inputs/manifest.json'),'prepared_seal':sha(run/'prepared/manifest.json'),
       'tasks':copy.deepcopy(state['tasks']),'execution_limits':state['execution_limits'],'timing_policy':'manual_only','phase_efforts':state['phase_efforts'],
       'model':'glm53-regular','endpoint':chapter_protocol.BASE_URL,'max_tokens':131072,'sample_thinking':'omitted; effective defaults not assumed',
       'bergomi_conversion':str(BERGOMI),'bergomi_intake_manifest':sha(ORIGINAL/'inputs/bergomi/intake/manifest.json')}
    atomic_json(run/'binding.json',baseline);state['binding_sha256']=fingerprint(baseline)
    runtime.save(run,state);report(run,state)
    POINTER.parent.mkdir(exist_ok=True);atomic_json(POINTER,{'run':str(run)})
    return run


def recorded_evidence(run):
    """Validate saved evidence independently of the implementation that will run next."""
    binding=read_json(run/'binding.json');state=read_json(run/'state.json')
    if fingerprint(binding)!=state['binding_sha256']:raise runtime.Fatal('Changed saved binding')
    if 'phase_efforts' in binding and state.get('phase_efforts')!=binding['phase_efforts']:raise runtime.Fatal('Changed phase effort settings')
    if binding.get('production_stage'):
        if state.get('production_stage')!=binding['production_stage']:raise runtime.Fatal('Changed production admission')
    if sha(Path(binding['parent'])/'state.json')!=binding['parent_state_sha256'] or sha(Path(binding['parent'])/'binding.json')!=binding['parent_binding_sha256']:raise runtime.Fatal('Parent evidence changed')
    if binding.get('launch_repair_parent'):
        origin=binding['launch_repair_parent'];folder=Path(origin['path'])
        if sha(folder/'state.json')!=origin['state_sha256'] or sha(folder/'binding.json')!=origin['binding_sha256']:raise runtime.Fatal('Launch-repair parent evidence changed')
    if binding.get('recovery_parent'):
        origin=binding['recovery_parent'];folder=Path(origin['path'])
        if sha(folder/'state.json')!=origin['state_sha256'] or sha(folder/'binding.json')!=origin['binding_sha256']:raise runtime.Fatal('Recovery parent evidence changed')
        for field in ('pilot','phase_efforts'):
            if state.get(field)!=binding.get(field):raise runtime.Fatal('Changed '+field+' admission settings')
    if binding.get('concurrency_parent'):
        parent=binding['concurrency_parent'];folder=Path(parent['path'])
        if sha(folder/'state.json')!=parent['state_sha256'] or sha(folder/'binding.json')!=parent['binding_sha256']:
            raise runtime.Fatal('Concurrency handover evidence changed')
        if state.get('concurrency_policy')!=binding['concurrency_policy']:raise runtime.Fatal('Changed concurrency policy')
    verify_seal(run/'inputs',binding['inputs_seal']);verify_seal(run/'prepared',binding['prepared_seal'])
    expected=binding['tasks'][:]
    if state.get('bergomi_preparation'):
        extra=read_json(run/'bergomi-preparation.json')
        if fingerprint(extra)!=state['bergomi_preparation']:raise runtime.Fatal('Changed Bergomi preparation')
        verify_seal(run/'bergomi',extra['seal'])
        if not binding.get('schedule_includes_bergomi'):expected+=extra['tasks']
    if [(t['id'],t['key'],t['phase'],t['source_key'],t['section'],t['context'],t['draft_label']) for t in state['tasks']] != [(t['id'],t['key'],t['phase'],t['source_key'],t['section'],t['context'],t['draft_label']) for t in expected]:raise runtime.Fatal('Changed task schedule')
    if [(t.get('request_input'),t.get('reasoning_effort')) for t in state['tasks']] != [(t.get('request_input'),t.get('reasoning_effort')) for t in expected]:raise runtime.Fatal('Changed per-task request settings')
    limits=binding['execution_limits'] if binding.get('production_stage') else (state.get('bergomi_preparation') and read_json(run/'bergomi-preparation.json')['execution_limits'] or binding['execution_limits'])
    if state['execution_limits']!=limits:raise runtime.Fatal('Changed new-work budget')
    environment=state['compiler_environment'];verify_seal(run/environment['path'],environment['seal'])
    qualified=read_json(run/environment['path']/'result.json')
    if qualified.get('image')!=environment['image'] or qualified.get('status')!='qualified':raise runtime.Fatal('Compiler binding does not match qualification')
    for versions in state['versions'].values():
        for v in versions.values():
            if sha(run/v['path'])!=v['sha256']:raise runtime.Fatal('Changed document version')
    for c in state['calls']:
        if c.get('seal'):verify_seal(Path(c.get('inherited_from',run))/'calls'/c['id'],c['seal'])
    return binding,state


def verify(run):
    binding,state=recorded_evidence(run)
    if binding['code']!=code_hashes():raise runtime.Fatal('Changed code/binding; use linked preparation, never reseal')
    return state


def scheduled_tasks(state):
    """Explicit ordered stage, independent of historical or dormant work."""
    tasks={t['id']:t for t in state['tasks']}
    ids=state['production_stage']['task_ids']
    if len(ids)!=len(set(ids)) or any(i not in tasks for i in ids):raise runtime.Fatal('Invalid stage task IDs')
    return [tasks[i] for i in ids]


def prepare_concurrency(parent,*,repair=False):
    """Fresh linked code binding, unchanged requests/tasks; authoritative drained snapshot."""
    parent=Path(parent).resolve()
    with writer_lock(ROOT),writer_lock(parent):
        pointer=read_json(POINTER)
        if Path(pointer['run']).resolve()!=parent:raise ValueError('Operator pointer advanced; rediscover before preparing')
        old_binding,old=recorded_evidence(parent)
        if old['status'] not in ('paused','stopped_error') or any(c['status']=='in_progress' for c in old['calls']):
            raise ValueError('Pause must drain every request and release ownership before linking')
        converter_idle(ORIGINAL)
        if repair:
            if not old.get('concurrency_policy') or old.get('concurrency_progress',{}).get('phase')!='two':
                raise ValueError('Ownership repair requires the interrupted two-slot pilot')
            if old_binding['code']==code_hashes():raise ValueError('Code already bound; use resume, never duplicate')
        elif old.get('concurrency_policy'):raise ValueError('Concurrency continuation already prepared; use its resume, never duplicate')
        run=chapter_inputs.new_path('editorial-chapters-trial');run.mkdir()
        state=copy.deepcopy(old)
        for name in ('inputs','prepared','versions','accuracy','bibliography','source-supplement','bergomi',
                     'inspection-images',state['compiler_environment']['path'],*state.get('editions',{}).values()):
            if (parent/name).is_dir():shutil.copytree(parent/name,run/name)
        for name in ('bergomi-preparation.json','saved-repair-record.json','continuation-preflight.json','reference-integrity.json','continuation-plan.json',
                     'concurrency-runtime-binding.json'):
            if (parent/name).is_file():shutil.copyfile(parent/name,run/name)
        for c in state['calls']:c.setdefault('inherited_from',str(parent))
        checks=[]
        for t in scheduled_tasks(state):
            if t['status']!='pending':continue
            old_body=body_for(parent,old,copy.deepcopy(t));new_body=body_for(run,state,t)
            if old_body!=new_body:raise runtime.Fatal('Concurrency would change request '+t['id'])
            checks.append({'task':t['id'],'request_sha256':fingerprint(new_body) if new_body else None,
                           'status':'exact_match' if new_body else 'same_dependency_on_pending_draft'})
        # Nothing is reset, including failures, completed task states or cumulative calls.
        progress=copy.deepcopy(old.get('concurrency_progress')) if repair else {'phase':'two','qualified_level':None,'trials':{},'sessions':[]}
        if repair:
            concurrent.interrupted_handover(progress,old,parent)
        state.update(status='prepared_offline',stage='concurrency_two_slot_progress_pilot',diagnostic=None,
                     concurrency_policy=copy.deepcopy(concurrent.POLICY),
                     concurrency_progress=progress)
        binding=copy.deepcopy(old_binding)
        binding.update(code=code_hashes(),concurrency_parent={'path':str(parent),'state_sha256':sha(parent/'state.json'),
                       'binding_sha256':sha(parent/'binding.json')},concurrency_policy=state['concurrency_policy'])
        atomic_json(run/'binding.json',binding);state['binding_sha256']=fingerprint(binding)
        from collections import Counter
        snapshot={'parent':str(parent),'snapshot_at':runtime.now(),'state_sha256':sha(parent/'state.json'),
                  'calls_preserved':len(state['calls']),'earlier_calls_preserved':len(state['historical_calls']),
                  'stage_statuses':dict(Counter(t['status'] for t in scheduled_tasks(old))),
                  'request_comparisons':checks,'policy':'Only concurrency/bookkeeping changes; all task grouping/source IDs/phase settings and historic allowances preserved',
                  'converted_awaiting_critic':[t['key'] for t in scheduled_tasks(old) if t['phase']=='critic' and t['status']=='pending' and t['key'] in old['current_versions']]}
        atomic_json(run/'concurrency-handover.json',snapshot)
        if repair:
            atomic_json(run/'ownership-recovery.json',{'parent':str(parent),'parent_state_sha256':sha(parent/'state.json'),
                'parent_status':old['status'],'parent_diagnostic':old.get('diagnostic'),
                'historical_progress_as_recorded':old['concurrency_progress'],
                'interpretation':'Interrupted two-slot pilot; retained completed calls and batch time. Original stale running trial label is unchanged in parent.',
                'repair':'Invalidate health after completion collection; compare each health snapshot with its contemporaneous owned call set; record stop evidence.',
                'maximum_in_flight':2,'four_slot_dispatch':'not authorized by this continuation',
                'remaining_pilot_requests':max(0,concurrent.POLICY['two_request_sample']-len(progress['trials']['two']['calls']))})
        runtime.save(run,state);verify(run);report(run,state);concurrent.write_report(run,state)
        pointer['run']=str(run);pointer['concurrency_parent']=str(parent);atomic_json(POINTER,pointer)
        print('PREPARED, NOT RUNNING:',run,'Report:',run/'report.html','Log after launch:',run/'terminal.log',flush=True)
        return run


def concurrent_worker(run,state):
    import importlib.util
    spec=importlib.util.spec_from_file_location('concurrent_workloads',ROOT/'scripts/run-bergomi-extraction.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    # Actual immutable image and installed serving sources, not just a recipe tag.
    concurrent.capture_build(module,run)
    from probe.local_model import LocalClient
    from probe.system_probe import parse_meminfo
    client=LocalClient(chapter_protocol.BASE_URL,chapter_protocol.MODEL,purpose='chapter',timeout=10)
    def sample(owned):
        folder=run/'concurrency-samples'/str(time.time_ns())
        h,e=client.chapter_health(folder)
        memory={}
        for node in ('head','peer'):
            argv=['cat','/proc/meminfo']
            raw=module.checked(argv if node=='head' else module.peer(shlex.join(argv)))
            memory[node]=parse_meminfo(raw)['MemAvailable']
        obs={'health':h,'memory_available_bytes':memory,'owned_in_flight':owned,'at':runtime.now(),'evidence':e}
        atomic_json(folder/'sample.json',obs);return obs
    def checkpoint():
        for book in ('gatheral','bergomi'):assemble(run,state,book,compile=True)
        report(run,state)
    tasks=scheduled_tasks(state)
    checkpoints=state.setdefault('concurrency_chapter_checkpoints',[])
    for source in {t['source_key'] for t in tasks}:
        if all(t['status'] not in ('pending','running') for t in tasks if t['source_key']==source) and source not in checkpoints:
            checkpoints.append(source) # already reflected in inherited edition
    def finish(r,s,t,answer,call):
        finish_task(r,s,t,answer,call)
        source=t['source_key']
        if source not in checkpoints and all(x['status'] not in ('pending','running') for x in tasks if x['source_key']==source):
            assemble(run,state,'bergomi' if source.startswith('bergomi-') else 'gatheral',compile=True)
            checkpoints.append(source)
    concurrent.coordinate(run,state,tasks,body_for=body_for,finish=finish,
        verify=lambda:verify(run),changed=lambda:report(run,state),sample=sample,checkpoint=checkpoint)
    checkpoint()
    state.update(status='stage_finished_for_inspection',stage=state['production_stage']['finish_stage'],
                 diagnostic='Scheduled remaining work attempted once. Gaps and unresolved accuracy questions remain explicit; no new optimization enabled.')


def prepare_production(parent):
    """Adopt inspected saved work, then admit only the authorized book tasks."""
    parent=Path(parent).resolve()
    with writer_lock(ROOT):
        converter_idle(ROOT)
        old_binding,old=recorded_evidence(parent)
        if old['status']!='pilot_finished_for_inspection' or any(c['status']=='in_progress' for c in old['calls']):
            raise ValueError('Requires the completed inspected pilot, with no uncertain dispatch')
        done,why=extraction_complete()
        if not done:raise ValueError(why)
        plan=read_json(ROOT/'docs/gatheral-pilot-adoption-20261028.json')
        if Path(plan['parent'])!=parent:raise ValueError('Adoption is bound to a different pilot')
        run=chapter_inputs.new_path('editorial-chapters-trial');run.mkdir()
        state=copy.deepcopy(old)
        for name in ('inputs','prepared','versions','accuracy','bibliography','source-supplement','bergomi',
                     'inspection-images','future-recovery-previews',state['compiler_environment']['path']):
            shutil.copytree(parent/name,run/name)
        shutil.copyfile(parent/'bergomi-preparation.json',run/'bergomi-preparation.json')
        for c in state['calls']:c.setdefault('inherited_from',str(parent))
        state['completed_pilot']=state.pop('pilot')
        state.pop('editions',None)
        state.update(status='preparing_offline',stage='production_preparation',diagnostic=None,
                     phase_efforts={'convert':'high','critic':'max'},timing_policy='manual_only',
                     execution_limits={'calls':None,'attempts_per_unit':1,'basis':'No overall local-call ceiling; one attempt per explicitly scheduled task, one readiness per launch'},
                     scope='Gatheral working edition with flagged source issues and three recovery gaps; then Bergomi Chapter 1, PDF18–41 only. Later Bergomi work dormant.')
        adopted=[]
        for evidence in plan['images']:
            if sha(run/evidence['path'])!=evidence['sha256']:raise ValueError('Adoption image changed')
        for row in plan['rows']:
            src=state['versions'][row['source_key']][row['source_label']]
            if src['sha256']!=row['source_sha256']:raise ValueError('Adoption version changed')
            text=edit.apply_edits(bound_output(run,state,row['source_key'],row['source_label']),row)
            key=row['key'];label='adopted-reviewed-20261028'
            record=remember(run,state,key,label,text,{'parent':str(parent),'source_version':copy.deepcopy(src),
                'source_key':row['source_key'],'source_label':row['source_label'],'plan_sha256':sha(ROOT/'docs/gatheral-pilot-adoption-20261028.json'),
                'attribution':'GLM draft with separately attributed Codex source-image/local-algebra corrections'})
            state['current_versions'][key]=label
            prior=state['accuracy_records'].get(row['source_key'])
            notes={'chapter':key,'items':row['items'],'capture_status':'reviewed_saved_notes','certification':False,
                   'history_record':prior,'supersedes_current_display_only':True,'source_review':plan['assessment']}
            folder=run/'accuracy'/key;folder.mkdir(exist_ok=True)
            atomic_json(folder/'adopted-current.json',notes)
            (folder/'adopted-current.md').write_text('# '+key+' current dispositions\n\n'+
                '\n\n'.join('## '+x['id']+' — '+x['status']+'\n'+x['text'] for x in row['items'])+
                '\n\nEarlier complete logs remain unchanged at '+str(prior)+'. They are history, not additional current findings.\n')
            state['accuracy_records'][key]=str((folder/'adopted-current.json').relative_to(run))
            state['accuracy'][key]=str((folder/'adopted-current.md').relative_to(run))
            adopted.append({'key':key,'version':label,'sha256':record['sha256'],'origin':record['origin'],
                            'history':prior,'current_dispositions':state['accuracy_records'][key]})
        stage={'task_ids':[],'inherited_calls':len(state['calls']),'section_replacements':{},
               'stop_after':'Bergomi Chapter 1 conversion/critic pair','attempts_per_task':1,
               'historical_calls_accounting_only':True,'normal_terminal_checks_required':True}
        state['production_stage']=stage
        future=read_json(parent/'future-recovery-previews/plan.json')['tasks']
        for row in future:
            if row['parent_gap']=='gatheral-07-s05':continue  # Adopted, never regenerate.
            original=next(t for t in old['tasks'] if t['key']==row['parent_gap'] and t['phase']=='convert')
            data=read_json(run/'inputs'/original['source_key']/'native.json')
            ids=row['target']['target_block_ids'];blocks=[b for b in data['blocks'] if b['id'] in ids]
            if [b['id'] for b in blocks]!=ids:raise ValueError('Recovery target order changed')
            if fingerprint(read_json(parent/'future-recovery-previews'/row['key']/'request.json'))!=row['request_sha256']:
                raise ValueError('Saved recovery request changed')
            section=original['section'] if row['key']==row['parent_gap'] else {
                'title':' '.join(x for _,x in chapter_inputs.strings(blocks[0]['native'])),
                'first':ids[0],'last':ids[-1],'blocks':ids,'physical_pages':row['target']['target_physical_pages'],
                'text':'\n\n'.join(b['tex'] for b in blocks),'boundary_status':'Reused prepared natural subsection boundary; complete native blocks'}
            if row['key']!=row['parent_gap']:stage['section_replacements'].setdefault(row['parent_gap'],[]).append(row['key'])
            for phase in ('convert','critic'):
                task=make_unit(run,state,row['key'],phase,section=section,source_key=original['source_key'],context=original['context'])
                stage['task_ids'].append(task['id'])
        for gap,children in stage['section_replacements'].items():
            expected=next(t['section']['blocks'] for t in old['tasks'] if t['key']==gap and t['phase']=='convert')
            actual=[b for t in scheduled_tasks(state) if t['key'] in children and t['phase']=='convert' for b in t['section']['blocks']]
            if actual!=expected:raise ValueError('Subsections omit/duplicate gap content')
        original=next(t for t in old['tasks'] if t['key']=='bergomi-01-s01' and t['phase']=='convert')
        for phase in ('convert','critic'):
            task=make_unit(run,state,original['key'],phase,section=original['section'],source_key=original['source_key'],context=original['context'])
            stage['task_ids'].append(task['id'])
        # Seal new preparation only. Old Bergomi preparation retains its historical
        # ceiling and schedule as evidence; this linked binding owns admission.
        for name in ('inputs','prepared'):
            atomic_json(run/name/'manifest.json',[r for r in files_manifest(run/name) if r['path']!='manifest.json'])
        binding=copy.deepcopy(old_binding);binding.pop('pilot',None)
        binding.update(code=code_hashes(),recovery_parent={'path':str(parent),'state_sha256':sha(parent/'state.json'),
            'binding_sha256':sha(parent/'binding.json'),'reason':'Inspected Lewis adoption and explicit high/max production stage; all history retained'},
            tasks=copy.deepcopy(state['tasks']),schedule_includes_bergomi=True,production_stage=copy.deepcopy(stage),
            phase_efforts=state['phase_efforts'],execution_limits=state['execution_limits'],
            inputs_seal=sha(run/'inputs/manifest.json'),prepared_seal=sha(run/'prepared/manifest.json'))
        atomic_json(run/'binding.json',binding);state['binding_sha256']=fingerprint(binding)
        state.update(stage='gatheral_recoveries_then_bergomi_first_chapter')
        atomic_json(run/'adoption-record.json',{'parent':str(parent),'plan':plan,'adoptions':adopted,
            'control_06_unchanged':state['versions']['gatheral-06-s03'][state['current_versions']['gatheral-06-s03']]['sha256'],
            'pilot_controls_not_adopted':True,'no_inference':True})
        atomic_json(run/'continuation-plan.json',{'stage':stage,'queued_tasks':scheduled_tasks(state),
            'planned_conversions':13,'maximum_critics_if_conversions_complete':13,'readiness':'one per launch; separately recorded',
            'later_bergomi':'132 remaining prepared conversion units not admitted; natural section outputs retain chapter context where it fits',
            'inherited_calls':len(state['calls']),'earlier_calls':len(state['historical_calls']),
            'source_preservation':'9 blank-page notices and 118 native-renderer fallbacks unchanged; fidelity not established'})
        runtime.save(run,state);verify(run)
        state['status']='prepared_offline';assemble(run,state,compile=False);report(run,state)
        pointer=read_json(POINTER);pointer['run']=str(run);atomic_json(POINTER,pointer)
        print('PREPARED ONLY; no inference. Run:',run,flush=True)
        return run


def prepare_remaining_bergomi(parent):
    """Linked saved-output repairs and the already prepared remaining book only."""
    parent=Path(parent).resolve()
    with writer_lock(ROOT),writer_lock(parent):
        converter_idle(ROOT)
        old_binding,old=recorded_evidence(parent)
        if old['status']!='stage_finished_for_inspection' or any(c['status']=='in_progress' for c in old['calls']):
            raise ValueError('Requires a completed checkpoint with no uncertain dispatch')
        done,why=extraction_complete()
        if not done:raise ValueError(why)
        plan=read_json(ROOT/'docs/editorial-saved-repairs-20261029.json')
        if Path(plan['parent'])!=parent:raise ValueError('Saved repairs belong to another parent')
        run=chapter_inputs.new_path('editorial-chapters-trial');run.mkdir()
        state=copy.deepcopy(old)
        for name in ('inputs','prepared','versions','accuracy','bibliography','source-supplement','bergomi',
                     'inspection-images',state['compiler_environment']['path']):
            shutil.copytree(parent/name,run/name)
        shutil.copyfile(parent/'bergomi-preparation.json',run/'bergomi-preparation.json')
        for c in state['calls']:c.setdefault('inherited_from',str(parent))
        canonical,queued,reconciled=delivery.remaining_bergomi(state,run)
        if len(queued)!=264 or len([t for t in canonical if t['phase']=='convert'])!=133:
            raise ValueError('Expected 132 remaining Bergomi conversion/critic pairs and 133 unique targets')
        for task in canonical:
            if task['phase']=='convert' and task['status']=='conversion_completed':
                call=next(c for c in state['calls'] if c['id']==task['call'])
                actual=read_json(Path(call['inherited_from'])/'calls'/call['id']/'request.json')
                if fingerprint(body_for(run,state,task))!=fingerprint(actual):
                    raise ValueError('Completed Bergomi conversion is not request-compatible with this continuation')
                for row in reconciled:
                    if row['completed_task']==task['id']:row['exact_conversion_request_match']=True
        preflight=recovery.preflight_inputs(run/'bergomi',canonical)
        atomic_json(run/'continuation-preflight.json',preflight)
        old_stage=state['production_stage']
        stage={'task_ids':[t['id'] for t in queued],'attempts_per_task':1,'inherited_calls':len(state['calls']),
               'historical_calls_accounting_only':True,'normal_terminal_checks_required':True,
               'section_replacements':old_stage.get('section_replacements',{}),
               'stop_after':'All 132 remaining Bergomi conversion/critic pairs attempted once',
               'finish_stage':'remaining_bergomi_schedule_finished','checkpoint':'chapter_boundary'}
        state.setdefault('stage_history',[]).append({'parent':str(parent),'stage':old_stage,'status':old['status']})
        state.update(status='preparing_offline',stage='saved_repairs_and_remaining_bergomi',diagnostic=None,
                     production_stage=stage,phase_efforts={'convert':'high','critic':'max'},timing_policy='manual_only',
                     execution_limits={'calls':None,'attempts_per_unit':1,'basis':'One attempt per scheduled unit; no overall local-call or duration ceiling'},
                     scope='Gatheral retained annotated parts; Bergomi Chapter 1 reused, remaining 132 units (Chapters 2–12, embedded appendices, epilogue, bibliography). PDF1–17 and 520 remain source supplements.')
        state.pop('editions',None)
        repairs=[]
        for row in plan['rows']:
            key=row['key'];label=row['source_label'];src=state['versions'][key][label]
            if src['sha256']!=row['source_sha256']:raise ValueError('Saved repair version changed')
            before=bound_output(run,state,key,label);after=edit.apply_edits(before,row)
            newlabel='codex-saved-repair-20261029'
            record=remember(run,state,key,newlabel,after,{'parent':str(parent),'source_label':label,
                'source_sha256':src['sha256'],'plan_sha256':sha(ROOT/'docs/editorial-saved-repairs-20261029.json'),
                'attribution':'Codex saved technical/editorial repair; no model calls'})
            state['current_versions'][key]=newlabel
            prior=read_json(run/state['accuracy_records'][key])
            raw=(run/'accuracy'/key/(label+'.raw.md')).read_text()
            notes=edit.notes_record(key,raw,phase='saved-critic-reconciled')
            if key.startswith('bergomi'):
                notes['items']=delivery.notes_from_visible_dispositions(key,after)
                # Preserve the model's explicit outstanding source-inspection list.
                notes['items'].append({'id':key+'-source-inspection','category':'material','status':'requires_source_inspection',
                    'text':'Saved critic requests images for printed pages 4, 9, 11, 18, 22, 24 (physical 21, 26, 28, 35, 39, 41); fragment images remain. The gamma/footnote question stays open.',
                    'attribution':'GLM','independent_verification':False})
            notes['history']=prior.get('history',[])+[dict(i,superseded_by='saved-critic-reconciled; source/raw history retained') for i in prior['items']]
            notes['items'].append({'id':key+'-Codex-repair-20261029','category':'material',
                'status':'applied_independently_checked','attribution':'Codex','independent_verification':True,
                'verification_scope':'local variance algebra only; no image verification' if key.startswith('bergomi') else 'package name and paired math delimiter only; compilation pending',
                'text':'Both variance-note occurrences corrected: with coefficient sigma_hat^2/N^2 on sum z_i^2, variance is (sigma_hat^4/N^4)*2N = 2 sigma_hat^4/N^3. Main estimator and variance unchanged.' if key.startswith('bergomi') else 'Added amsfonts for mathbb; paired the mismatched inline-math delimiter. Mathematical content unchanged.'})
            notes['history_record']=old['accuracy_records'][key]
            folder=run/'accuracy'/key
            atomic_json(folder/'saved-reconciled.json',notes)
            (folder/'saved-reconciled.md').write_text('# Current saved dispositions — '+key+'\n\nGLM claims are not independent verification. Original raw notes and prior classifications remain in history.\n\n'+
                '\n\n'.join('## '+x['id']+' — '+x['status']+'\n'+x['text'] for x in notes['items']))
            state['accuracy_records'][key]=str((folder/'saved-reconciled.json').relative_to(run))
            state['accuracy'][key]=str((folder/'saved-reconciled.md').relative_to(run))
            import difflib
            (run/Path(record['path']).parent/'repair.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=label,tofile=newlabel)))
            repairs.append({'key':key,'version':newlabel,'sha256':record['sha256'],'origin':record['origin']})
        references={}
        for key,label in state['current_versions'].items():
            source=next((t['source_key'] for t in state['tasks'] if t['key']==key),key)
            references[key]=delivery.reference_inventory(bound_output(run,state,key,label),selected_assets(run,source),simple.image_references)
        atomic_json(run/'reference-integrity.json',{'parts':references,
            'scope':'Selected editable TeX label/asset linkage, not exhaustive literal-number or bibliography verification',
            'retained_unresolved':'Gatheral jump expansion/conventions and Lewis; Bergomi gamma/footnotes and pending image checks. No global sign or reference changes.'})
        for task in queued:save_preview(run,state,task)
        for name in ('inputs','prepared'):
            atomic_json(run/name/'manifest.json',[r for r in files_manifest(run/name) if r['path']!='manifest.json'])
        binding=copy.deepcopy(old_binding)
        binding.update(code=code_hashes(),recovery_parent={'path':str(parent),'state_sha256':sha(parent/'state.json'),
            'binding_sha256':sha(parent/'binding.json'),'reason':'Saved output repairs, explicit completed Chapter 1 adoption, remaining Bergomi only'},
            tasks=copy.deepcopy(state['tasks']),schedule_includes_bergomi=True,production_stage=copy.deepcopy(stage),
            phase_efforts=state['phase_efforts'],execution_limits=state['execution_limits'],
            inputs_seal=sha(run/'inputs/manifest.json'),prepared_seal=sha(run/'prepared/manifest.json'))
        atomic_json(run/'binding.json',binding);state['binding_sha256']=fingerprint(binding)
        atomic_json(run/'saved-repair-record.json',{'parent':str(parent),'plan':plan,'repairs':repairs,
            'duplicate_task_reconciliation':reconciled,'historical_calls':len(state['historical_calls'])+len(state['calls']),
            'inference_performed':False,'compilation':'Not attempted here: Docker access denied; operator launch compiles saved repairs first'})
        atomic_json(run/'continuation-plan.json',{'stage':stage,'planned_conversions':132,'maximum_critics':132,
            'readiness':'one per launch, automatically captured','reused':'Full Bergomi Chapter 1, calls 063/064; no regeneration',
            'source_coverage':'133 distinct units, physical PDF18–519, no duplicate target blocks',
            'supplement':'PDF1–17 and520: source images/native views retained. Preface PDF16–17 and front-matter/title/copyright/contents lack a reviewed typeset TeX view.',
            'historical_execution_limits':'Old 98-call preparation remains sealed historical evidence; new admission has calls=null'})
        runtime.save(run,state);verify(run)
        try:
            for book in ('gatheral','bergomi'):assemble(run,state,book,compile=False)
        except Exception as exc:
            state.update(status='preparation_failed',diagnostic=type(exc).__name__+': '+str(exc))
            runtime.save(run,state);report(run,state)
            raise
        state['status']='prepared_offline';runtime.save(run,state)
        report(run,state)
        pointer=read_json(POINTER);pointer['run']=str(run);atomic_json(POINTER,pointer)
        path=bundle(run,state);atomic_json(run/'last-inspection.json',{'path':str(path),'status':state['status']})
        print('PREPARED ONLY; no inference. Run:',run,'Report:',run/'report.html',flush=True)
        return run


def prepare_recovery(parent,bergomi_cache=None,*,conversion_effort='max',critic_effort='max'):
    """New linked preparation; historical calls remain sealed at their original paths."""
    parent=Path(parent).resolve()
    if bergomi_cache:bergomi_cache=Path(bergomi_cache).resolve()
    with writer_lock(ROOT):
        converter_idle(ROOT)  # Offline readers need no deployment/Docker access.
        old_binding,old=recorded_evidence(parent)
        if old['status']=='running' or any(c['status']=='in_progress' for c in old['calls']):raise ValueError('Parent has active/uncertain work; no preparation')
        done,why=extraction_complete()
        if not done:raise ValueError(why)
        run=chapter_inputs.new_path('editorial-chapters-trial');run.mkdir()
        state=copy.deepcopy(old)
        for name in ('inputs','prepared','versions','accuracy','bibliography','source-supplement',state['compiler_environment']['path']):
            shutil.copytree(parent/name,run/name)
        for c in state['calls']:c.setdefault('inherited_from',str(parent))
        state.update(status='preparing_offline',stage='linked_recovery',diagnostic=None,ocr_status='complete_520_pages_65_windows',
                     bergomi_status='chapter_preparation_pending',phase_efforts={'convert':edit.validate_effort(conversion_effort),'critic':edit.validate_effort(critic_effort)})
        state.pop('editions',None);state.pop('last_inspection_zip',None)
        # The unannotated final critic documents already carry their current visible
        # findings. The later program appendix duplicated older, superseded claims.
        reconciliations={}
        for key in list(state['current_versions']):
            # Only the two demonstrated stale-appendix cases are reselected.
            # Other chapters retain their complete current notes and document versions.
            if key not in ('gatheral-05','gatheral-10'):continue
            versions=state['versions'][key]
            critics=[n for n in versions if n.startswith('critic-call-') and not n.endswith('-annotated')]
            if not critics:continue
            label=sorted(critics)[-1];text=bound_output(run,state,key,label)
            new=remember(run,state,key,'current-dispositions',text,{'parent':str(parent),'selected_saved_version':label,
                'change':'Remove subsequently appended historical claims; saved critic document and mathematics byte-for-byte unchanged'})
            # It is exactly the already compiled document, not a claim of a fresh build.
            new.update({k:copy.deepcopy(versions[label][k]) for k in ('compilation','compiled_image','compile_folder') if k in versions[label]})
            new['compilation_evidence']='inherited exact-document check from '+str(parent)
            state['current_versions'][key]='current-dispositions'
            before_path=run/'accuracy'/key/'reconciled-dispositions.json'
            before=read_json(before_path) if before_path.exists() else {'items':[]}
            raw=(run/'accuracy'/key/(label+'.raw.md')).read_text()
            aliases={}
            if key=='gatheral-10':
                aliases={f'{key}-recovered-critic-{h}':[ref] for h,ref in {
                    'e5b3467114':'G10-Jeffery','0bbb63b634':'G10-denominator','8c61914ff8':'G10-floor','9334bd635d':'G10-return'}.items()}
            if key=='gatheral-05':aliases={key+'-recovered-critic-a5772d238b':['G5-hats'],
                                          key+'-recovered-critic-e6457a05fb':['2233f04ea7']}
            record=recovery.latest_dispositions(before,raw,key,aliases)
            if key=='gatheral-10':
                # Explicit review of the complete log, not a fuzzy semantic merger.
                for old_suffix,heading in [('d24f238e42','Mechanical fixes'),('3bdd536509','Contextual, no change'),
                                          ('04b17aa1fa','Contextual, no change'),('5be1027b09','Cosmetic / residual')]:
                    prior_id=key+'-recovered-critic-'+old_suffix
                    replacement=next(x for x in record['items'] if heading in x['text'].splitlines()[0])
                    previous=[x for x in record['items'] if x['id']==prior_id]
                    record['history'] += [dict(x,superseded_by=replacement['id'],reconciled_by='Codex saved-log comparison') for x in previous]
                    record['items']=[x for x in record['items'] if x['id']!=prior_id]
                if not all(token in text for token in (r'\leq-12\%', 'Christopher Jeffery',r'\mathit{basket}_{i-1}-\mathit{basket}_i')):
                    raise ValueError('Known Chapter 10 corrections missing from selected document')
                record['codex_checks']=['Annual floor bound: twelve -1% monthly floors sum to -12%; corrected text retained',
                    'Jeffery name retained from same-book bibliography', 'Printed denominator remains unchanged; contract interpretation unresolved']
            if key=='gatheral-05':
                cosmetic=next(x for x in record['items'] if x['text'].startswith('**Cosmetic**'))
                for suffix in ('9e73e0a36c','2418f39a23'):
                    previous=[x for x in record['items'] if x['id']==key+'-recovered-critic-'+suffix]
                    record['history'] += [dict(x,superseded_by=cosmetic['id'],reconciled_by='Codex: current log labels these draft artifacts cosmetic') for x in previous]
                    record['items']=[x for x in record['items'] if x['id']!=key+'-recovered-critic-'+suffix]
                if not all(token in text for token in (r'with $\hat C(u,T)$ and $\hat D(u,T)$ given by',r'\bar v',r'\eta^2')):
                    raise ValueError('Known Chapter 5 corrections missing')
                record['codex_checks']=['Hatted C/D introduction, mean-variance overbar and auxiliary prefactor retained in exact saved critic document',
                    'T-star inconsistency remains unresolved; no scaling alteration']
            folder=run/'accuracy'/key
            atomic_json(folder/'current-dispositions.json',record)
            (folder/'current-dispositions.md').write_text('# Current dispositions — '+key+'\n\nCodex reconciliation of saved GLM claims; no new inference.\n\n'+
                '\n\n'.join('## '+x['id']+' — '+x['status']+'\n'+x['text'] for x in record['items'])+
                '\n\nHistorical claims: [history](history.json). Supersession is not independent mathematical verification.\n')
            atomic_json(folder/'history.json',{'items':record['history'],'prior_raw_notes':str(parent/'accuracy'/key),'preserved_current_raw':label+'.raw.md'})
            state['accuracy_records'][key]=str((folder/'current-dispositions.json').relative_to(run))
            state['accuracy'][key]=str((folder/'current-dispositions.md').relative_to(run))
            reconciliations[key]={'old':old['current_versions'][key],'new':'current-dispositions','math_unchanged_sha256':new['sha256'],
                                 'superseded_claims':len(record['history'])}
        atomic_json(run/'annotation-reconciliation.json',reconciliations)
        cases=[('gatheral-06-s03','Completed control: local/implied volatility and jump-to-ruin, source-checkable equations and conditions'),
               ('gatheral-07-s01','Completed control: short-expiry asymptotics; source-checkable formula and limit assumptions'),
               ('gatheral-07-s05','Short failed Lewis section; retain its existing complete section boundaries, no blind splitting')]
        pilot={'inherited_calls':len(state['calls']),'readiness_limit':3,'task_ids':[],'cases':[],
               'scope':'Three conversions high, at most three immediate critics max; no retries or subsequent book dispatch',
               'comparison':'Historical omitted-effort Max versus explicit high; not a randomized contemporary benchmark',
               'quality':'Independent source inspection remains required; max critic approval is not accuracy measurement'}
        state['pilot']=pilot
        for key,reason in cases:
            original=next(t for t in old['tasks'] if t['key']==key and t['phase']=='convert')
            call=next(c for c in old['calls'] if c['id']==original['call'])
            historical=read_json(parent/'calls'/call['id']/'request.json')
            if 'reasoning_effort' in historical:raise ValueError('Expected historical omitted-effort Max request')
            body={**historical,'reasoning_effort':'high'}
            unit='pilot-'+key;path=Path('inputs/pilot-requests')/(unit+'.json');atomic_json(run/path,body)
            pair=[]
            for phase in ('convert','critic'):
                task={'id':f'u{len(state["tasks"])+1:03d}-{unit}-{phase}','key':unit,'source_key':original['source_key'],
                      'phase':phase,'status':'pending','draft_label':None,'section':copy.deepcopy(original['section']),
                      'context':original['context'],'attempt_limit':1,'reasoning_effort':'high' if phase=='convert' else 'max'}
                if phase=='convert':task['request_input']=str(path)
                if original.get('context_scope'):task['context_scope']=copy.deepcopy(original['context_scope'])
                state['tasks'].append(task);save_preview(run,state,task);pair.append(task['id']);pilot['task_ids'].append(task['id'])
            comparison={'historical_request':str(parent/'calls'/call['id']/'request.json'),'historical_request_sha256':sha(parent/'calls'/call['id']/'request.json'),
                        'prepared_request':str(path),'changed_fields':{'reasoning_effort':{'before':'absent (installed default Max)','after':'high'}},
                        'other_fields_identical':{k:v for k,v in body.items() if k!='reasoning_effort'}==historical}
            if not comparison['other_fields_identical']:raise ValueError('Pilot altered another request field')
            row={'key':unit,'historical_key':key,'reason':reason,'task_ids':pair,'comparison':comparison,
                 'historical_metrics':recovery.call_metrics(parent,call),'target':recovery.section_coverage(original,read_json(run/'inputs'/original['source_key']/'native.json'))}
            pilot['cases'].append(row)
            archive=run/'pilot-history'/key;archive.mkdir(parents=True)
            atomic_json(archive/'request-comparison.json',comparison)
            atomic_json(archive/'historical-metrics.json',row['historical_metrics'])
            for phase in ('convert','critic'):
                t=next(t for t in old['tasks'] if t['key']==key and t['phase']==phase)
                if t.get('call'):
                    source_call=parent/'calls'/t['call']
                    for name in ('request.json','answer.txt','response-metadata.json','settings.json'):
                        if (source_call/name).exists():shutil.copyfile(source_call/name,archive/(phase+'-'+name))
            for label in ('convert-'+call['id'],old.get('current_versions',{}).get(key)):
                if label and label in old['versions'].get(key,{}):
                    shutil.copyfile(parent/old['versions'][key][label]['path'],archive/(label+'.tex'))
        # Full Bergomi preflight and dormant schedule BEFORE any new model dispatch.
        binding_tasks=copy.deepcopy(state['tasks'])
        runtime.save(run,state)
        if bergomi_cache:
            if state['phase_efforts']!={'convert':'max','critic':'max'}:raise ValueError('Cached Bergomi preparation uses max/max; prepare fresh inputs for a different phase setting')
            extra=read_json(bergomi_cache/'bergomi-preparation.json')
            verify_seal(bergomi_cache/'bergomi',extra['seal'])
            if extra['conversion_state_sha256']!=sha(BERGOMI/'state.json'):raise ValueError('Cached Bergomi conversion changed')
            expected_start=len(state['tasks'])+1
            if not extra['tasks'][0]['id'].startswith(f'u{expected_start:03d}-'):raise ValueError('Cached Bergomi schedule has incompatible preceding work')
            shutil.copytree(bergomi_cache/'bergomi',run/'bergomi')
            shutil.copyfile(bergomi_cache/'bergomi-preparation.json',run/'bergomi-preparation.json')
            state['tasks']+=copy.deepcopy(extra['tasks']);state['bergomi_preparation']=fingerprint(extra)
            state['bergomi_status']='prepared_completed_OCR'
        else:prepare_bergomi(run,state)
        for folder in ('inputs','prepared'):
            atomic_json(run/folder/'manifest.json',[r for r in files_manifest(run/folder) if r['path']!='manifest.json'])
        binding=copy.deepcopy(old_binding)
        binding.update(code=code_hashes(),recovery_parent={'path':str(parent),'state_sha256':sha(parent/'state.json'),'binding_sha256':sha(parent/'binding.json'),
            'reason':'Blank-notice classification, current annotation selection, section coverage and bounded explicit-effort pilot; no historical seals modified'},
            tasks=binding_tasks,inputs_seal=sha(run/'inputs/manifest.json'),prepared_seal=sha(run/'prepared/manifest.json'),
            pilot=pilot,phase_efforts=state['phase_efforts'])
        binding['sample_thinking']='explicit per phase; requested level separate from runtime evidence'
        if bergomi_cache:binding['bergomi_preparation_origin']={'path':str(bergomi_cache),'seal':sha(bergomi_cache/'bergomi/manifest.json')}
        atomic_json(run/'binding.json',binding);state['binding_sha256']=fingerprint(binding)
        state.update(status='prepared_offline',stage='three_case_effort_pilot',diagnostic=None,
                     scope='Gatheral linked working edition with four section gaps; Bergomi 520-page inputs preflighted, dormant. Launch admits only three high/max pilot pairs.')
        atomic_json(run/'recovery-record.json',{'parent':str(parent),'historical_snapshot_note':'Parent ZIP was made while status was running, before Bergomi preparation failed. Parent on-disk state records stopped_error. Both preserved.',
            'original_diagnostic':old.get('diagnostic'),'blank_classification':'docs/source-provenance/bergomi-page-classification-20261028.json',
            'inherited_calls':len(old['calls']),'earlier_calls':len(old['historical_calls']),'no_inference':True})
        gaps=[{'key':t['key'],'section':t['section'],'status':t['status'],'historical_call':t.get('call'),
               'next_action':'Reuse pilot draft only after reviewed adoption; no duplicate dispatch' if t['key']=='gatheral-07-s05' else
                 'Short section retained; new explicit authorization/preparation before another attempt' if t['key'].startswith('gatheral-07') else
                 'Inspect coherent native subsection boundaries before a bounded recovery; not admitted by pilot'}
              for t in old['tasks'] if t['phase']=='convert' and t['status']!='conversion_completed']
        atomic_json(run/'continuation-plan.json',{'gatheral_gaps':gaps,'bergomi_first_pair':[t['id'] for t in state['tasks'] if t['key']=='bergomi-01-s01'],
             'later_work':'Prepared dormant Bergomi tasks are not admitted by this pilot binding. New explicit linked admission required; inherited calls and successful pilot work retained.',
             'efforts':{'convert':'max','critic':'max'},'no_deadlines':True})
        prepare_future_recoveries(run,state,gaps)
        prepare_inspection_images(run,state)
        runtime.save(run,state);verify(run);assemble(run,state,compile=False);report(run,state);pilot_report(run,state)
        pointer=read_json(POINTER);pointer['run']=str(run);atomic_json(POINTER,pointer)
        print('PREPARED ONLY — no inference. Run:',run,flush=True)
        return run


def prepare_inspection_images(run,state):
    from probe.saved_pages import render_region
    folder=run/'inspection-images';folder.mkdir();rows=[]
    for case in state['pilot']['cases']:
        key=case['historical_key'];source=key.split('-s')[0]
        data=read_json(run/'inputs'/source/'native.json');wanted=case['target']['target_block_ids']
        for n in case['target']['target_physical_pages']:
            name=f'gatheral-p{n:03d}.png';dest=folder/name
            if not dest.exists():render_region(ROOT/'inputs/gatheral/source.pdf',n-1,dest,max_edge=1900)
            rows.append({'case':key,'physical_page':n,'printed_page':n-31,'file':name,'scope':'source page, not reviewed output'})
        equations=[b for b in data['blocks'] if b['id'] in wanted and b['kind']=='equation']
        for b in equations[:2]:
            n=b['page']['original_physical_page'];name=b['id'].replace(':','-')+'.png'
            bbox=[max(0,b['bbox'][0]-.03),max(0,b['bbox'][1]-.02),min(1,b['bbox'][2]+.03),min(1,b['bbox'][3]+.02)]
            render_region(ROOT/'inputs/gatheral/source.pdf',n-1,folder/name,bbox=bbox,max_edge=1800)
            rows.append({'case':key,'physical_page':n,'block':b['id'],'bbox':bbox,'file':name,'scope':'legible source formula control; no gold answer in request'})
    atomic_json(folder/'index.json',{'source':'inputs/gatheral/source.pdf','images':rows,
        'inspection':'Source excerpts for independent Max/high output comparison; no model accuracy inference from successful delivery'})


def prepare_future_recoveries(run,state,gaps):
    """Dormant request previews. Short failures stay intact; long ones use headings."""
    planned=[]
    for gap in gaps:
        original=next(t for t in state['tasks'] if t['key']==gap['key'] and t['phase']=='convert')
        data=read_json(run/'inputs'/original['source_key']/'native.json')
        blocks=[b for b in data['blocks'] if b['id'] in original['section']['blocks']]
        groups=[original['section']]
        if gap['key'].startswith('gatheral-11'):
            # These failed long outputs contain clear native subsection titles.
            # Preserve intro with the first subsection; never split a native block.
            starts=[0]+[i for i,b in enumerate(blocks) if i and b['kind']=='paragraph_title'
                        and not re.match(r'(?i)^(proof|theorem|lemma|remark|example)\b',' '.join(x for _,x in chapter_inputs.strings(b['native'])))]
            if len(starts)>1:starts.pop(1)
            groups=[]
            for j,(a,z) in enumerate(zip(starts,starts[1:]+[len(blocks)]),1):
                subset=blocks[a:z];title=' '.join(x for _,x in chapter_inputs.strings(subset[0]['native']))
                groups.append({'title':title,'first':subset[0]['id'],'last':subset[-1]['id'],'blocks':[b['id'] for b in subset],
                    'physical_pages':sorted({b['page']['original_physical_page'] for b in subset}),
                    'text':'\n\n'.join(b['tex'] for b in subset),'boundary_status':'complete blocks between observed native subsection headings; source context retained'})
            if [b for g in groups for b in g['blocks']]!=original['section']['blocks']:raise ValueError('Future recovery loses section targets')
        for i,group in enumerate(groups,1):
            key=gap['key']+(f'-part{i:02d}' if len(groups)>1 else '')
            task={**copy.deepcopy(original),'section':group,'reasoning_effort':'max','status':'prepared_not_admitted'}
            body=body_for(run,state,task);folder=run/'future-recovery-previews'/key
            atomic_json(folder/'request.json',body);atomic_json(folder/'budget.json',chapter_sources.budget_preview(body))
            planned.append({'key':key,'parent_gap':gap['key'],'target':recovery.section_coverage(task,data),
                'request_sha256':fingerprint(body),'critic':'Immediately after complete conversion, max effort; exact new draft required',
                'admission':'NOT admitted by pilot; reuse approved pilot result instead of redispatching same gap'})
    atomic_json(run/'future-recovery-previews/plan.json',{'tasks':planned,'admitted':False,'no_successful_work_replayed':True})


def pilot_report(run,state):
    if not state.get('pilot'):return
    rows=[]
    for case in state['pilot']['cases']:
        tasks=[t for t in state['tasks'] if t['id'] in case['task_ids']]
        calls=[recovery.call_metrics(run,c) for c in state['calls'][state['pilot']['inherited_calls']:] if c['parent'] in case['task_ids']]
        versions=state['versions'].get(case['key'],{})
        rows.append({**case,'new_attempts':calls,'stage_statuses':{t['phase']:t['status'] for t in tasks},
                     'structural_observations':{t['phase']:t.get('structural_observations') for t in tasks},
                     'compilations':{k:v['compilation'] for k,v in versions.items()},
                     'accuracy_log':state.get('accuracy',{}).get(case['key']),
                     'independent_assessment':{'omissions':'pending source inspection','material_formula_or_assumption_changes':'pending source inspection',
                         'uncertainty':'see raw conversion/critic notes when available; not an accuracy score'}})
    atomic_json(run/'pilot-comparison.json',{'status':state['status'],'cases':rows,'inference_not_run':not any(r['new_attempts'] for r in rows)})
    (run/'pilot-comparison.md').write_text('# Explicit-effort pilot\n\nHistorical omitted effort maps to Max in the inspected installed template. New conversions request high, critics max. Runtime effort is not independently attested. No randomized or mathematical-accuracy claim.\n\n'+
        '\n\n'.join('## '+r['key']+'\n'+r['reason']+'\nStatus: '+str(r['stage_statuses'])+'\nHistorical metrics: '+json.dumps(r['historical_metrics'])+'\nNew attempts: '+json.dumps(r['new_attempts']) for r in rows)+
        '\n\nCompare every formula, condition, omission and uncertainty against the included source pages. Max critic agreement and compilation are separate technical observations.\n')


def prepare_launch_repair(parent):
    """Link the zero-dispatch preparation to this reviewed launcher-only correction."""
    parent=Path(parent).resolve()
    with writer_lock(ROOT):
        complete,why=extraction_complete()
        if not complete:raise RuntimeError(why)
        pointer=read_json(POINTER)
        if Path(pointer['run']).resolve()!=parent:raise ValueError('Use the current preparation; refusing to replace a newer pointer')
        binding,state=recorded_evidence(parent)
        if state['calls'] or state['first_dispatch'] is not None or state['status']!='prepared_offline':
            raise ValueError('Launch repair requires a preparation with no dispatched calls; never reset consumed work')
        current=code_hashes()
        changes={p:{'before':binding['code'].get(p),'after':current.get(p)}
                 for p in sorted(set(binding['code'])|set(current)) if binding['code'].get(p)!=current.get(p)}
        if set(changes)!={'scripts/editorial_chapters.py'}:
            raise ValueError('Expected only the reviewed editorial launcher change, found: '+str(sorted(changes)))
        run=chapter_inputs.new_path('editorial-chapters-trial')
        shutil.copytree(parent,run,ignore=shutil.ignore_patterns('.probe.lock','pause.json','stop.json'))
        binding['launch_repair_parent']={'path':str(parent),'binding_sha256':sha(parent/'binding.json'),
            'state_sha256':sha(parent/'state.json'),'code_changes':changes,
            'reason':'Verified desktop executable admission; requests, schedule, corrections and budgets unchanged; no calls dispatched'}
        binding['code']=current
        atomic_json(run/'binding.json',binding);state['binding_sha256']=fingerprint(binding)
        runtime.save(run,state);verify(run);report(run,state)
        # Retain the integration receipt: the old /tmp bootstrap must forward to
        # this checkout, never copy its older code back or repeat baseline checks.
        pointer['run']=str(run)
        atomic_json(POINTER,pointer)
        print('Linked launch repair; no inference. Parent:',parent,'\nPrepared run:',run,flush=True)
        return run


def compile_version(run,state,key,label):
    v=state['versions'][key][label]
    if v.get('compiled_image')==state['compiler_environment']['image']:return
    source=next((t['source_key'] for t in state['tasks'] if t['key']==key),key)
    assets=selected_assets(run,source)
    out=run/Path(v['path']).parent/('compile-'+str(time.time_ns()))
    try:result=compiler_environment.compile_saved(run,state,ROOT,bound_output(run,state,key,label),out,assets)
    except (ValueError,RuntimeError) as exc:result={'status':'compiler_environment_failure','error':str(exc)}
    v['compilation']=result;v['compiled_image']=state['compiler_environment']['image'];v['compile_folder']=str(out.relative_to(run))
    runtime.save(run,state)


def task_once(run,state,task,*,invoke=runtime.invoke):
    if task['status'] not in ('pending','running'):return
    if any(c['parent']==task['id'] for c in state['calls']):
        task.update(status='interrupted_unresolved',error='Reserved/saved call exists; no automatic replay');return
    body=body_for(run,state,task)
    if body is None:task.update(status='unavailable',error='No complete conversion to review');return
    if task.get('preview_hash') and fingerprint(body)!=task['preview_hash']:raise runtime.Fatal('Prepared request changed')
    task.pop('error',None);task['status']='running';runtime.save(run,state);report(run,state)
    try:answer,call=invoke(run,state,task['id'],body)
    except chapter_protocol.ContextBudgetGap as exc:task.update(status='context_budget_gap',error=str(exc));return
    except ValueError as exc:task.update(status='admission_failure',error=str(exc));return
    finish_task(run,state,task,answer,call)


def finish_task(run,state,task,answer,call):
    """Coordinator-only selection, notes and compilation; shared by both schedules."""
    task['call']=call['id']
    if answer is None:
        task.update(status='no_final_answer' if call.get('metadata',{}).get('content_chars',None)==0 else call['failure_kind'],error=call['error'])
        if task['phase']=='critic':
            partial=run/'calls'/call['id']/'answer.txt'
            prior=state.get('accuracy_records',{}).get(task['key'])
            attach_notes(run,task['key'],'failed-'+call['id'],partial.read_text() if partial.exists() else '',{},complete=False,before=read_json(run/prior) if prior else None)
        if call['failure_kind']=='operator_stop':raise runtime.StopRun('Stopped; partial stream retained; no replay')
        if state['connection_failures']>=2:raise runtime.StopRun('Repeated connection failures')
        return
    document,info=chapter_accuracy.envelope(answer,simple.extract_document)
    key=task['key'];phase=task['phase'];label=phase+'-'+call['id']
    previous=state.get('current_versions',{}).get(key)
    if document is not None and chapter_accuracy.complete_document(document):
        remember(run,state,key,label,document,{'call':call['id'],'extraction':info})
        state['current_versions'][key]=label
        task['status']='conversion_completed' if phase=='convert' else 'critic_revised'
        expected=task['section']['text'] if task.get('section') else (run/('bergomi/inputs' if task['source_key'].startswith('bergomi-') else 'inputs')/task['source_key']/'source.tex').read_text()
        task['structural_observations']=simple.document_observations(document,expected,set(selected_assets(run,task['source_key'])))
    elif phase=='critic':
        task['status']='critic_revision_unusable' if info.get('status')=='ambiguous' and r'\documentclass' in answer else 'critic_unchanged';task['revision_diagnostic']='No unambiguous complete revision; current draft preserved'
    else:
        task.update(status='complete_answer_without_document',error='Final answer retained but no unambiguous complete LaTeX document');return
    previous_notes=state.get('accuracy_records',{}).get(key)
    notes=attach_notes(run,key,label,answer,info,before=read_json(run/previous_notes) if previous_notes else None)
    state.setdefault('accuracy_records',{})[key]=str(Path('accuracy')/key/(label+'.json'))
    state['accuracy'][key]=str((run/'accuracy'/key/(label+'.md')).relative_to(run))
    current=state['current_versions'].get(key)
    if current:
        doc=bound_output(run,state,key,current)
        extra=[dict(x,attribution='GLM') for x in notes['items'] if x['category']=='material']
        if extra:
            annotated=edit.annotate(doc,extra);ann=label+'-annotated'
            if annotated!=doc:
                remember(run,state,key,ann,annotated,{'from':current,'notes':state['accuracy'][key]})
                state['current_versions'][key]=ann
        runtime.save(run,state)
        if document is not None:compile_version(run,state,key,label)
        compile_version(run,state,key,state['current_versions'][key])


def extraction_complete(root=ORIGINAL):
    run=root/'runs'/BERGOMI.name
    state=read_json(run/'state.json')
    if state.get('status')!='conversion_completed_unreviewed':return False,'Bergomi extraction is '+state.get('status','unknown')
    units=state.get('units',{})
    rows=units.values() if isinstance(units,dict) else units
    if len(units)!=65 or any(x.get('status')!='completed' for x in rows):return False,'Bergomi 65-window completion not established'
    owned=[n for u in rows for n in range(u['window']['owned_start'],u['window']['owned_end']+1)]
    if sorted(owned)!=list(range(1,521)) or len(set(owned))!=520:return False,'Owned page coverage is not exactly 1–520'
    try:converter_idle(root)
    except (RuntimeError,ValueError) as exc:return False,'Converter workers have not exited: '+str(exc)
    op=root/'runs/bergomi-operator'
    exits=[read_json(p) for p in op.glob('launch-*/exit.json')]
    matching=[x for x in exits if x.get('run')==str(run)]
    if matching and not any(x.get('exit_status')==0 for x in matching):return False,'Bergomi operator recorded failed exit; inspect before continuation'
    if not any(x.get('exit_status')==0 for x in matching):return False,'No successful owned operator exit record'
    return True,'520-page extraction completed; workers exited'


def prepare_bergomi(run,state):
    """Preparation is transactional; an interrupted reader never corrupts the live schedule."""
    if state.get('bergomi_preparation'):return
    folder=run/'bergomi'
    if folder.exists():
        archive=run/('bergomi-incomplete-preparation-'+str(time.time_ns()))
        folder.rename(archive)
        atomic_json(run/('bergomi-preparation-interruption-'+str(time.time_ns())+'.json'),
                    {'preserved':str(archive.relative_to(run)),'reason':'No committed preparation binding; no model requests replayed'})
    prepared=copy.deepcopy(state)
    _prepare_bergomi(run,prepared)
    state.clear();state.update(prepared)
    runtime.save(run,state)


def _prepare_bergomi(run,state):
    if state.get('bergomi_preparation'):return
    done,why=extraction_complete()
    if not done:raise RuntimeError(why+'; refusing incomplete evidence')
    meta=read_json(ORIGINAL/'inputs/bergomi/intake/metadata.json')
    provenance=read_json(ORIGINAL/'docs/source-provenance/bergomi-intake-20261027.json')
    # Use established intake boundaries, not Gatheral chapter counts or inferred titles.
    parts=[('front','Front matter',*provenance['front_matter_physical'])]+[(f'{c["chapter"]:02d}',c['title'],c['physical_pdf_start'],c['physical_pdf_end']) for c in provenance['chapters']]+[('epilogue','Epilogue',*provenance['epilogue_physical']),('bibliography','Bibliography',*provenance['bibliography_physical']),('back','Back cover',*provenance['back_cover_physical'])]
    folder=run/'bergomi';folder.mkdir()
    classification=ROOT/'docs/source-provenance/bergomi-page-classification-20261028.json'
    native=chapter_inputs.prepare(folder/'native',source_specs=[{'source':'bergomi','run':str(BERGOMI),'parts':parts,'prefix':'bergomi','pages':520,
        'blanks':read_json(classification)['verified_empty_pages'],'page_classification':str(classification)}],evidence_root=ORIGINAL)
    before=len(state['tasks']);cache=ORIGINAL/'inputs/bergomi/intake'
    for key,title,a,b in parts:
        key='bergomi-'+key;src=native/'chapters'/key;dst=folder/'inputs'/key;dst.mkdir(parents=True)
        data=read_json(src/'source.json');primary,ledger=simple.chapter_text(data)
        (dst/'source.tex').write_text(primary);atomic_json(dst/'native.json',data)
        pages=[]
        for row in meta['page_map'][a-1:b]:
            text=(cache/row['native_text']).read_text()
            if sha(cache/row['native_text'])!=row['text_sha256']:raise ValueError('Changed cached Bergomi native text')
            n=row['original_physical_page'];printed=row.get('printed_page')
            for c in provenance['chapters']:
                if c['physical_pdf_start']<=n<=c['physical_pdf_end']:printed=c['printed_start']+n-c['physical_pdf_start']
            pages.append({'physical_pdf_page':n,'printed_page':printed,'text':text})
        (dst/'secondary.txt').write_text(chapter_sources.render_pages(pages))
        atomic_json(dst/'secondary.json',{'source':meta['source_sha256'],'extractor':meta['extractor'],'pages':pages})
        assets=sorted({x for bl in data['blocks'] for x in bl['assets']});atomic_json(dst/'assets.json',assets)
        for name in assets:
            target=folder/'inputs'/name;target.parent.mkdir(exist_ok=True)
            if not target.exists():shutil.copyfile(native/name,target)
        # Read through a distinct sealed input root; no modifications to existing Gatheral inputs.
        if key in ('bergomi-front','bergomi-back'):continue
        groups=edit.section_groups(data)
        if key=='bergomi-01':
            blocks=[b for b in data['blocks'] if b['kind'] not in chapter_inputs.AUX]
            groups=[{'title':title,'first':blocks[0]['id'],'last':blocks[-1]['id'],'blocks':[b['id'] for b in blocks],
                     'physical_pages':list(range(a,b+1)),'text':'\n\n'.join(b['tex'] for b in blocks),
                     'boundary_status':'complete first chapter; existing intake boundary'}]
        atomic_json(dst/'section-plan.json',groups)
        for j,g in enumerate(groups,1):
            unit=key+f'-s{j:02d}'
            for phase in ('convert','critic'):
                ident=f'u{len(state["tasks"])+1:03d}-{unit}-{phase}'
                state['tasks'].append({'id':ident,'key':unit,'source_key':key,'phase':phase,'status':'pending','draft_label':None,
                    'section':g,'context':'','attempt_limit':1,'input_root':'bergomi/inputs'})
    from probe.documents import _fitz
    fitz=_fitz()
    with fitz.open(ORIGINAL/'inputs/bergomi/source.pdf') as original:
        supplement=fitz.open()
        for a,z in (provenance['front_matter_physical'],provenance['back_cover_physical']):supplement.insert_pdf(original,from_page=a-1,to_page=z-1)
        supplement.save(folder/'source-supplement.pdf',garbage=3,deflate=True);supplement.close()
    for task in state['tasks'][before:]:
        body=body_for(run,state,task)
        dest=folder/'prepared'/task['id'];dest.mkdir(parents=True)
        if body is not None:
            atomic_json(dest/'request.json',body);atomic_json(dest/'budget.json',chapter_sources.budget_preview(body));task['preview_hash']=fingerprint(body)
        else:atomic_json(dest/'pending-draft.json',{'status':'critic awaits complete preceding section draft'})
    atomic_json(folder/'preflight.json',recovery.preflight_inputs(folder,state['tasks'][before:]))
    atomic_json(folder/'manifest.json',files_manifest(folder))
    if not state.get('pilot'):
        state['execution_limits']={'attempts_per_unit':1,'calls':2*len(state['tasks'])+32,'basis':'one call per new unit; bounded resume readiness; history retained separately'}
    extra={'seal':sha(folder/'manifest.json'),'tasks':copy.deepcopy(state['tasks'][before:]),'execution_limits':state['execution_limits'],
        'conversion':str(BERGOMI),'conversion_state_sha256':sha(BERGOMI/'state.json'),'source_sha256':meta['source_sha256'],'pages':520,
        'scope':'12 chapters incl embedded mathematical appendices, epilogue, bibliography; front/back saved source supplement; index absent in supplied PDF'}
    atomic_json(run/'bergomi-preparation.json',extra);state['bergomi_preparation']=fingerprint(extra);state['bergomi_status']='prepared_completed_OCR'
    runtime.save(run,state)


def report(run,state):
    # Read-only callers inspect report; only the writer regenerates it.
    inherited=[c for c in state['calls'] if c.get('inherited_from')]
    current=[c for c in state['calls'] if not c.get('inherited_from')]
    summary={'status':state['status'],'stage':state.get('stage'),'diagnostic':state.get('diagnostic'),
      'ocr_status':state.get('ocr_status'),'pilot':state.get('pilot'),'production_stage':state.get('production_stage'),
      'concurrency':state.get('concurrency_progress'),
      'overall_call_ceiling':state.get('execution_limits',{}).get('calls'),
      'remaining_stage_outputs':[t['key'] for t in scheduled_tasks(state) if t['phase']=='convert' and t['key'] not in state['current_versions']] if state.get('production_stage') else None,
      'history_calls':len(state['historical_calls']),'inherited_parent_calls':len(inherited),'new_calls':len(current),
      'cumulative_calls':len(state['historical_calls'])+len(state['calls']),
      'request_seconds_new':sum(c.get('elapsed_seconds',0) for c in current),
      'inherited_parent_request_seconds':sum(c.get('elapsed_seconds',0) for c in inherited),
      'historical_request_seconds':state['historical_request_seconds'],
      'inherited_stages':state.get('inherited_stages',{}),'tasks':state['tasks'],'current_versions':state['current_versions'],'scope':state['scope'],'bergomi':state['bergomi_status'],
      'accuracy':'Codex and GLM assessments are attributed separately; compilation is not correctness; no full-book certification',
      'editions':{book:{'path':path,'coverage':read_json(run/path/'coverage.json').get('delivery'),
                       'master_compilation':read_json(run/path/'compilation.json')['status'] if (run/path/'compilation.json').exists() else 'not_attempted'}
                  for book,path in state.get('editions',{}).items()},
      'compilations':{k:{n:v['compilation'] for n,v in vs.items()} for k,vs in state['versions'].items()}}
    atomic_json(run/'summary.json',summary)
    rows=[]
    for key,label in state['current_versions'].items():
        v=state['versions'][key][label];rows.append('<tr><td>'+html.escape(key)+'</td><td><a href="'+v['path']+'">annotated/current TeX</a></td><td>'+html.escape(v['compilation']['status'])+'</td></tr>')
    displayed=scheduled_tasks(state) if state.get('production_stage') else state['tasks']
    taskrows=''.join('<tr>'+''.join('<td>'+html.escape(str(t.get(x,'')))+'</td>' for x in ('id','status','error'))+'</tr>' for t in displayed)
    index=['# Material corrections and unresolved issues', 'Attribution and resolution claims remain separate from independent checks.']
    for key,path in state['accuracy'].items():
        index += ['## '+key, '['+key+' accuracy log]('+path+')']
    (run/'corrections-index.md').write_text('\n\n'.join(index)+'\n')
    (run/'report.html').write_text('<!doctype html><meta charset="utf-8"><h1>Annotated working edition and recovery</h1><p>'+html.escape(state['status'])+
        '</p><p>Stage: '+html.escape(str(state.get('stage','not recorded')))+'; diagnostic: '+html.escape(str(state.get('diagnostic','none')))+
        '</p><p>Remaining scheduled output gaps: '+html.escape(str(summary['remaining_stage_outputs']))+
        '</p><p>Original drafts and raw responses preserved. Visible editorial notes are attributed. Technical completion is not semantic certification. '
        'Section gaps are listed in edition coverage. Front matter and index are source supplements, not GLM conversions.</p>'+
        ('<p><a href="concurrency-report.md">Concurrency pilot and batch metrics</a></p>' if state.get('concurrency_policy') else '')+
        '<p><a href="summary.json">Status and timing</a> | <a href="bibliography/references.json">Gatheral structured bibliography</a></p>'+
        ''.join('<p>'+html.escape(book)+': <a href="'+e['path']+'/README.md">edition</a>; '+html.escape(str(e['coverage']))+'; master compilation: '+html.escape(e['master_compilation'])+'</p>' for book,e in summary['editions'].items())+
        '<table border="1">'+''.join(rows)+
        '</table><h2>Admitted tasks</h2><p>Full inherited and dormant schedule remains in summary.json; only the listed stage is admitted.</p><table border="1">'+taskrows+'</table>',encoding='utf-8')


def assemble(run,state,book='gatheral',*,compile=False):
    out=run/'editions'/(book+'-'+str(time.time_ns()));out.mkdir(parents=True)
    master=[r'\documentclass{book}\usepackage{pdfpages,hyperref}\begin{document}',r'\chapter*{Annotated working edition: '+edit.tex_escape(book)+'}',
            'Experimental, partial where indicated. Source-page numbers refer to the original book. Editorial notes are not certification.']
    selected=[(k,l) for k,l in state['current_versions'].items() if k.startswith(book+'-')]
    order={k:i for i,k in enumerate([f'{book}-{i:02d}' for i in range(1,13)]+[book+'-postscript',book+'-epilogue',book+'-bibliography'])}
    selected.sort(key=lambda x:(order.get(x[0].split('-s')[0],99),x[0]))
    missing={f'{book}-{c:02d}' for c in (range(1,12) if book=='gatheral' else range(1,13)) if not any(k==f'{book}-{c:02d}' or k.startswith(f'{book}-{c:02d}-s') for k,_ in selected)}
    # A chapter represented by explicit section targets needs those exact gaps,
    # not an additional whole-chapter placeholder counted as another target.
    missing.difference_update(t['source_key'] for t in state['tasks'] if t['phase']=='convert' and t.get('section'))
    missing.update(t['key'] for t in state['tasks'] if t['phase']=='convert' and t['key'].startswith(book+'-')
                   and t.get('section') and t['key'] not in dict(selected))
    missing.difference_update(state.get('production_stage',{}).get('section_replacements',{}))
    selected += [(k,None) for k in missing];selected.sort(key=lambda x:(order.get(x[0].split('-s')[0],99),x[0]))
    assets={};coverage=[]
    for key,label in selected:
        task=next((t for t in state['tasks'] if t['key']==key and t['phase']=='convert'),None)
        source=next((t['source_key'] for t in state['tasks'] if t['key']==key),key)
        native=read_json(run/('bergomi/inputs' if source.startswith('bergomi-') else 'inputs')/source/'native.json')
        scope=recovery.section_coverage(task,native)
        if label is None:
            title=task['section']['title'] if task and task.get('section') else key
            master.append(r'\chapter*{Missing '+edit.metadata_tex(key)+'}'+edit.metadata_tex(title)+
                          '. Physical PDF pages '+edit.tex_escape(str(scope['target_physical_pages']))+
                          '. No complete GLM draft; source remains preserved. This gap occurs here in source order.')
            coverage.append({'key':key,'status':'missing_output','content_retained':False,'pdf_included':False,
                             'raw_title':title,'source_key':source,**scope});continue
        v=state['versions'][key][label];p=out/'chapters'/key;p.mkdir(parents=True)
        shutil.copyfile(run/v['path'],p/'document.tex')
        for n,src in selected_assets(run,source).items():
            if n not in simple.image_references((run/v['path']).read_text()):continue
            dest=p/n;dest.parent.mkdir(exist_ok=True)
            if not dest.exists():shutil.copyfile(src,dest)
        sourcePDF=None
        if v['compilation']['status'].startswith('passed'):
            for a in v['compilation'].get('attempts',[]):
                pp=run/a['path']/'document.pdf'
                if pp.exists():sourcePDF=pp
        part=out/'parts'/(key+'.tex');part.parent.mkdir(exist_ok=True)
        if sourcePDF:
            pdf=out/'assets'/(key+'.pdf');pdf.parent.mkdir(exist_ok=True);shutil.copyfile(sourcePDF,pdf)
            part.write_text(r'\includepdf[pages=-,pagecommand={}]{assets/'+key+'.pdf}')
            assets['assets/'+key+'.pdf']=pdf
        else:part.write_text(r'\chapter*{'+edit.metadata_tex(key)+'}Compilation not yet successful; standalone TeX retained. This is a visible edition gap.')
        assets['parts/'+key+'.tex']=part;master.append(r'\input{parts/'+key+'.tex}')
        coverage.append({'key':key,'version':label,'sha256':v['sha256'],'compilation':v['compilation']['status'],
            'content_retained':True,'pdf_included':sourcePDF is not None,
            'model_review':[t['status'] for t in state['tasks'] if t['key']==key and t['phase']=='critic' and t['status']!='pending'],
            'independent_verification':'Only explicitly attributed findings, not the complete part',
            'source_key':source,'source_pages':scope['target_physical_pages'],**scope})
    if book=='gatheral':
        supplement=run/'source-supplement/gatheral-front-blank-index.pdf'
        target=out/'assets/source-supplement.pdf';target.parent.mkdir(exist_ok=True);shutil.copyfile(supplement,target)
        assets['assets/source-supplement.pdf']=target
        master.append(r'\chapter*{Original source supplement}Front matter, intentional blank, and original index. Index locators refer to original printed pages, not this edition.\includepdf[pages=-,pagecommand={}]{assets/source-supplement.pdf}')
    if book=='bergomi' and (run/'bergomi/source-supplement.pdf').exists():
        target=out/'assets/source-supplement.pdf';target.parent.mkdir(exist_ok=True);shutil.copyfile(run/'bergomi/source-supplement.pdf',target)
        assets['assets/source-supplement.pdf']=target
        master.append(r'\chapter*{Original front matter and back cover}No index pages are present in the supplied PDF.\includepdf[pages=-,pagecommand={}]{assets/source-supplement.pdf}')
        for key in ('bergomi-front','bergomi-back'):
            folder=out/'source-supplement'/key;folder.mkdir(parents=True)
            for name in ('source.tex','secondary.txt','secondary.json','native.json','assets.json'):
                shutil.copyfile(run/'bergomi/inputs'/key/name,folder/name)
            atomic_json(folder/'source-provenance.json',{'input_root':str(run/'bergomi/inputs'/key),
                'native_sha256':sha(folder/'native.json'),'secondary_sha256':sha(folder/'secondary.json'),
                'page_mapping':'native.json pages[].page and secondary.json pages[]',
                'historical_preparation':str(run/'bergomi-preparation.json')})
            for name,src in selected_assets(run,key).items():
                dest=folder/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
            (folder/'README.md').write_text('Raw extracted TeX/native text with page provenance; not a GLM-reviewed or qualified typeset view. The source supplement preserves the PDF. Preface PDF16–17 remains substantive unreviewed front matter.\n')
    for name in ('accuracy','bibliography'):
        if name=='bibliography' and book!='gatheral':continue
        if (run/name).exists():shutil.copytree(run/name,out/name)
    master.append(r'\end{document}');(out/'master.tex').write_text('\n'.join(master))
    atomic_json(out/'coverage.json',{'delivery':delivery.edition_summary(coverage),'delivered_parts':coverage,
        'legacy_field_note':'delivered_parts is the historical inventory name; only pdf_included=true rows are delivered PDF content, never placeholders',
        'scope':state['scope'],'source_owned_pages':list(range(1,211)) if book=='gatheral' else list(range(1,521)),'fidelity':'mechanical source accounting, not verified output completeness','tasks':[{'key':t['key'],'phase':t['phase'],'status':t['status'],'blocks':t['section']['blocks'] if t.get('section') else None} for t in state['tasks'] if t['source_key'].startswith(book+'-')]})
    (out/'README.md').write_text('Each chapter/section retains a standalone document.tex and assets. Master includes compiled chapter PDFs through relative parts/*.tex to isolate conflicting preambles/macros without rewriting mathematics. Recompile each changed chapter before master. All uncompiled/missing parts are explicit gaps. Original pagination references are not retargeted.\n')
    if compile:
        result=compiler_environment.compile_saved(run,state,ROOT,(out/'master.tex').read_text(),out/'compile',assets)
        atomic_json(out/'compilation.json',result)
    state.setdefault('editions',{})[book]=str(out.relative_to(run));runtime.save(run,state);return out


def bundle(run,state):
    path=ROOT/'results'/('editorial-chapters-inspection-'+run.name.removeprefix('editorial-chapters-trial-')+'-'+str(time.time_ns())+'.zip')
    path.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
        for name in ('report.html','summary.json','binding.json','state.json','bergomi-preparation.json','corrections-index.md',
                     'recovery-record.json','annotation-reconciliation.json','continuation-plan.json','adoption-record.json','pilot-comparison.json','pilot-comparison.md','bergomi/preflight.json',
                     'saved-repair-record.json','continuation-preflight.json','reference-integrity.json',
                     'concurrency-report.json','concurrency-report.md','concurrency-handover.json','concurrency-runtime-binding.json',
                     'ownership-recovery.json','ownership-diagnosis.json','ownership-diagnosis.md'):
            if (run/name).exists():z.write(run/name,name)
        for folder in ('accuracy','bibliography','source-supplement','inspection-images','pilot-history','concurrency-stops',*state.get('editions',{}).values()):
            if not (run/folder).exists():continue
            for p in (run/folder).rglob('*'):
                if p.is_file() and p.suffix in ('.tex','.json','.md','.txt','.diff','.pdf','.log','.png','.jpg'):z.write(p,str(p.relative_to(run)))
        for c in [c for c in state.get('calls',[]) if not c.get('inherited_from')]:
            for name in ('request.json','settings.json','answer.txt','response-metadata.json','outcome.json'):
                p=run/'calls'/c['id']/name
                if p.exists():z.write(p,str(p.relative_to(run)))
        for p in (run/'prepared').rglob('budget.json'):z.write(p,str(p.relative_to(run)))
        # Only new pilot document versions; full historical raw responses stay linked.
        for key in state.get('current_versions',{}):
            if not key.startswith('pilot-'):continue
            for p in (run/'versions'/key).rglob('*'):
                if p.is_file() and p.suffix in ('.tex','.json','.md','.pdf','.log'):z.write(p,str(p.relative_to(run)))
    print('Inspection ZIP:',path,flush=True);return path


def finalize(run,state):
    """Persist terminal state before producing the snapshot, including on exceptions."""
    runtime.save(run,state);report(run,state);pilot_report(run,state)
    if state.get('concurrency_policy'):concurrent.write_report(run,state)
    path=bundle(run,state)
    atomic_json(run/'last-inspection.json',{'path':str(path),'status':state['status'],'stage':state.get('stage'),'at':runtime.now()})


def worker(run):
    with (run/'terminal.log').open('a',buffering=1) as log:
        os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
        state=verify(run)
        with writer_lock(ROOT),writer_lock(run):
            try:
                state.update(status='running',stage='workload_and_readiness',diagnostic=None);runtime.save(run,state)
                converter_idle(ORIGINAL);runtime.check_other_jobs()
                runtime.readiness(run,state)
                state['stage']='compile_selected_saved_documents';runtime.save(run,state)
                for key,label in list(state['current_versions'].items()):compile_version(run,state,key,label)
                if state.get('concurrency_policy'):
                    concurrent_worker(run,state)
                elif state.get('production_stage'):
                    for book in ('gatheral','bergomi'):
                        tasks=[t for t in scheduled_tasks(state) if t['source_key'].startswith(book+'-')]
                        for i,task in enumerate(tasks):
                            if (run/'pause.json').exists() or (run/'stop.json').exists():raise runtime.StopRun('Operator pause/stop; evidence retained')
                            verify(run);state['stage']=task['id'];runtime.save(run,state)
                            print('Book:',book,'Chapter/section:',task['key'],'Phase:',task['phase'],'Model: glm53-regular','Output:',run,flush=True)
                            task_once(run,state,task);runtime.save(run,state);report(run,state)
                            if (state['production_stage'].get('checkpoint')=='chapter_boundary' and
                                task['phase']=='critic' and i+1<len(tasks) and tasks[i+1]['source_key']!=task['source_key']):
                                state['stage']=book+'_chapter_checkpoint';runtime.save(run,state)
                                assemble(run,state,book,compile=True);report(run,state)
                        state['stage']=book+'_assembly';runtime.save(run,state);assemble(run,state,book,compile=True)
                    state.update(status='stage_finished_for_inspection',stage=state['production_stage'].get('finish_stage','after_bergomi_first_chapter_pair'),
                                 diagnostic='Explicitly scheduled stage ended; failed or uncompiled parts remain gaps. No tasks outside this stage were dispatched.')
                elif state.get('pilot'):
                    # Rebuild the linked edition using saved documents, never model regeneration.
                    assemble(run,state,'gatheral',compile=True)
                    active=[t for t in state['tasks'] if t['id'] in state['pilot']['task_ids']]
                    for task in active:
                        if (run/'pause.json').exists() or (run/'stop.json').exists():raise runtime.StopRun('Operator pause/stop; evidence retained')
                        verify(run);state['stage']=task['id'];runtime.save(run,state)
                        task_once(run,state,task);runtime.save(run,state);report(run,state);pilot_report(run,state)
                    state.update(status='pilot_finished_for_inspection',stage='awaiting_independent_pilot_inspection',
                                 diagnostic='Pilot only: no Bergomi or remaining Gatheral recovery dispatched; failures remain visible')
                else:
                    for book in ('gatheral','bergomi'):
                        state['stage']=book+'_chapter_preparation';runtime.save(run,state)
                        if book=='bergomi':
                            try:prepare_bergomi(run,state)
                            except Exception:
                                state['bergomi_status']='chapter_preparation_failed';raise
                        for task in state['tasks']:
                            if not task['source_key'].startswith(book+'-'):continue
                            if (run/'pause.json').exists() or (run/'stop.json').exists():raise runtime.StopRun('Operator pause/stop; evidence retained')
                            verify(run);state['stage']=task['id'];runtime.save(run,state)
                            task_once(run,state,task);runtime.save(run,state);report(run,state)
                        state['stage']=book+'_assembly';runtime.save(run,state);assemble(run,state,book,compile=True)
                    state['status']='finished_with_gaps' if any(t['status'] not in ('conversion_completed','critic_revised','critic_unchanged') for t in state['tasks']) else 'delivery_complete_not_certified'
                    state['stage']='finished'
            except runtime.Fatal as exc:
                state.update(status='stopped_error',diagnostic=str(exc));print('INTEGRITY/IDENTITY STOP:',exc,flush=True)
            except runtime.StopRun as exc:
                state.update(status='paused',diagnostic=str(exc));print('PAUSED:',exc,flush=True)
            except BaseException as exc:
                state.update(status='stopped_error',diagnostic=type(exc).__name__+': '+str(exc));print('ERROR:',exc,flush=True)
                raise
            finally:
                finalize(run,state)
                print('Status:',state['status'],'Report:',run/'report.html','Log:',run/'terminal.log',flush=True)


# Exact installed system executable only, never a PID, process title or substring.
DESKTOP_EXECUTABLE='/usr/libexec/gnome-remote-desktop-daemon'


def gpu_workload_snapshot(module,node):
    """Read host process identity and unadjusted unified-memory availability."""
    from probe.system_probe import parse_meminfo
    def checked(argv):
        return module.checked(argv if node=='head' else module.peer(shlex.join(argv)))
    raw=checked(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'])
    processes=[]
    for row in csv.reader(raw.splitlines()):
        if not row:continue
        if len(row)!=2 or not row[0].strip().isascii() or not row[0].strip().isdecimal() or int(row[0])<=0:
            raise RuntimeError('Cannot interpret GPU workload on '+node+'; no launch: '+repr(row))
        pid=int(row[0]);proc_exe='/proc/'+str(pid)+'/exe'
        item={'pid':pid,'reported_name':row[1].strip(),'classification':'conflicting_or_unknown'}
        try:
            exe=checked(['readlink','--',proc_exe]).strip();item['executable']=exe
            if exe==DESKTOP_EXECUTABLE:
                # Dereference /proc/exe as well as the installed file: a stale,
                # replaced/deleted or uninspectable executable is not exempt.
                identities=checked(['stat','--dereference','--format=%d:%i','--',proc_exe,DESKTOP_EXECUTABLE]).splitlines()
                if len(identities)==2 and identities[0].strip() and identities[0].strip()==identities[1].strip():
                    item.update(classification='verified_desktop',executable_identity=identities[0].strip())
        except (RuntimeError,OSError,subprocess.TimeoutExpired) as exc:
            item['identity_error']=str(exc)
        processes.append(item)
    memory=parse_meminfo(checked(['cat','/proc/meminfo']))
    if 'MemAvailable' not in memory:raise RuntimeError('Available memory unknown on '+node+'; no launch')
    return {'node':node,'processes':processes,'memory_bytes':memory,
            'memory_policy':'Unadjusted MemAvailable includes desktop usage; existing GLM launcher/TensorFold admission remains authoritative'}


def guard_gpu_workloads(run,module,*,resident_glm=False):
    observations=[gpu_workload_snapshot(module,node) for node in ('head','peer')]
    if resident_glm:
        for obs in observations:
            argv=['docker','top',module.CONTAINER,'-eo','pid']
            raw=module.checked(argv if obs['node']=='head' else module.peer(shlex.join(argv)))
            rows=raw.splitlines()
            if not rows or rows[0].strip()!='PID' or not all(x.strip().isascii() and x.strip().isdecimal() for x in rows[1:]):
                raise RuntimeError('Cannot identify owned GLM container processes on '+obs['node'])
            owned={int(x.strip()) for x in rows[1:]}
            if not owned:raise RuntimeError('Resident GLM container has no identifiable processes')
            obs['owned_glm_container']=module.CONTAINER;obs['owned_glm_pids']=sorted(owned)
            for p in obs['processes']:
                if p['pid'] in owned:p['classification']='verified_glm_container'
    path=run/'launch-checks'/('gpu-workloads-'+str(time.time_ns())+'.json')
    atomic_json(path,{'at':runtime.now(),'nodes':observations})
    for obs in observations:
        busy=[p for p in obs['processes'] if p['classification'] not in ('verified_desktop','verified_glm_container')]
        if busy:
            raise RuntimeError('Active or unverifiable GPU work on '+obs['node']+'; left untouched: '+
                               json.dumps(busy)+'; evidence: '+str(path))
        print(obs['node']+': '+str(len(obs['processes']))+' verified desktop/owned-GLM GPU processes; '+
              f"{obs['memory_bytes']['MemAvailable']/1024**3:.2f} GiB actually available (no desktop memory credited back).",flush=True)


def arrange_glm(run,*,check_only=False):
    import importlib.util
    spec=importlib.util.spec_from_file_location('bergomi_launch',ROOT/'scripts/run-bergomi-extraction.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.project_idle()
    for process in Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name)==os.getpid():continue
        try:
            if process.stat().st_uid!=os.getuid():continue
            args=[w.decode(errors='replace') for w in (process/'cmdline').read_bytes().split(b'\0') if w]
            if any(Path(a).name in ('simple_chapter_glm.py','editorial_chapters.py') for a in args) and any(a in args for a in ('worker','start-worker')):
                raise RuntimeError('Another chapter writer is active: PID '+process.name)
        except (FileNotFoundError,ProcessLookupError):continue
    dep=module.deployments()
    if any(module.CONTAINER in n for n in dep.values()):
        if any(module.CONTAINER not in n for n in dep.values()):raise RuntimeError('Partial GLM deployment; no automatic restart')
        guard_gpu_workloads(run,module,resident_glm=True)
    else:
        if check_only:raise RuntimeError('Regular GLM is unavailable; pilot does not start or change services. Use the documented operator service procedure, then resume.')
        guard_gpu_workloads(run,module)
        print('Starting existing regular GLM serially; setup/downloads disabled.',flush=True)
        result=subprocess.run(['bash','./start.sh'],cwd=module.GLM,env={**os.environ,'ABLIT':'0','PREPARE':'0','PULL':'0','HF_HUB_OFFLINE':'1'})
        if result.returncode:raise RuntimeError('Documented GLM launcher failed; no fallback')
    from probe.local_model import LocalClient
    client=LocalClient(chapter_protocol.BASE_URL,chapter_protocol.MODEL,purpose='chapter',timeout=10)
    client.discover_model(run/'launch-checks');h,_=client.chapter_health(run/'launch-checks');chapter_protocol.health_capacity(h)


def normal_terminal_checks(run):
    """Once per tested code/test identity, not before each chapter or resume."""
    identity=fingerprint({'code':code_hashes(),'tests':{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'tests').rglob('*.py'))}})
    record=run/'normal-terminal-checks.json'
    if record.exists() and read_json(record).get('passed_identity')==identity:return
    log=run/('normal-terminal-tests-'+str(time.time_ns())+'.log')
    print('Running the full offline test suite once. Log:',log,flush=True)
    with log.open('w') as output:
        result=subprocess.run([str(ORIGINAL/'.venv-control/bin/python'),'-B','-m','unittest','discover','-s','tests','-v'],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
    atomic_json(record,{'passed_identity':identity if result.returncode==0 else None,'exit_status':result.returncode,'log':str(log)})
    if result.returncode:raise RuntimeError('Required tests failed; no inference launched. Inspect '+str(log))
    print('Normal-terminal tests passed.',flush=True)


def launch(run):
    done,why=extraction_complete()
    if not done:raise RuntimeError(why+'; checkout remains untouched, finish/resume MinerU first')
    state=verify(run)
    if state.get('pilot') and state['status']=='pilot_finished_for_inspection':
        raise RuntimeError('Pilot is finished; inspect its results. No further book work is admitted by this launch.')
    if state.get('production_stage') and state['status']=='stage_finished_for_inspection':
        raise RuntimeError('Scheduled book stage is finished; inspect results. Later Bergomi work requires new explicit preparation.')
    probe=subprocess.run(['tmux','has-session','-t',SESSION],capture_output=True,text=True)
    if probe.returncode==0:raise RuntimeError('Session already active: '+SESSION)
    if probe.returncode!=1 or any(x in probe.stderr.lower() for x in ('permission denied','operation not permitted')):raise RuntimeError('Cannot inspect tmux: '+probe.stderr)
    if state.get('production_stage'):normal_terminal_checks(run)
    arrange_glm(run,check_only=bool(state.get('pilot') or state.get('production_stage')))
    for name in ('pause.json','stop.json'):
        (run/name).unlink(missing_ok=True)
    cmd=shlex.join([str(ORIGINAL/'.venv-control/bin/python'),'-B','-u',str(Path(__file__)),'worker','--run',str(run)])
    subprocess.run(['tmux','new-session','-d','-s',SESSION,'cd '+shlex.quote(str(ROOT))+' && exec '+cmd],check=True)
    print('RUNNING session:',SESSION,'\nRun:',run,'\nLog:',run/'terminal.log','\nReport:',run/'report.html')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','prepare-production','prepare-remaining-bergomi','prepare-concurrency','prepare-concurrency-repair','prepare-recovery','prepare-launch-repair','run','resume','worker','status','pause','stop','bundle','assemble','start-worker'))
    p.add_argument('--run',type=Path);p.add_argument('--bergomi-cache',type=Path)
    p.add_argument('--conversion-effort',choices=edit.EFFORTS,default='max')
    p.add_argument('--critic-effort',choices=edit.EFFORTS,default='max');a=p.parse_args()
    if a.action not in ('prepare','prepare-recovery') and any(x.startswith(('--conversion-effort','--critic-effort')) for x in sys.argv[1:]):
        p.error('Effort is a sealed preparation setting; launch/resume cannot override it')
    if a.action=='prepare':print(prepare_gatheral(conversion_effort=a.conversion_effort,critic_effort=a.critic_effort));return
    run=a.run or Path(read_json(POINTER)['run'])
    if a.action=='prepare-recovery':prepare_recovery(run,a.bergomi_cache,conversion_effort=a.conversion_effort,critic_effort=a.critic_effort)
    elif a.action=='prepare-concurrency':prepare_concurrency(run)
    elif a.action=='prepare-concurrency-repair':prepare_concurrency(run,repair=True)
    elif a.action=='prepare-production':prepare_production(run)
    elif a.action=='prepare-remaining-bergomi':prepare_remaining_bergomi(run)
    elif a.action=='prepare-launch-repair':prepare_launch_repair(run)
    elif a.action in ('run','resume'):launch(run)
    elif a.action=='worker':worker(run)
    elif a.action=='start-worker':
        s=verify(run)
        if s.get('production_stage'):normal_terminal_checks(run)
        arrange_glm(run,check_only=bool(s.get('pilot') or s.get('production_stage')));worker(run)
    elif a.action=='status':
        s=read_json(run/'state.json');print(json.dumps({'run':str(run),'status':s['status'],'stage':s.get('stage'),'diagnostic':s.get('diagnostic'),
          'historical_calls':len(s['historical_calls']),'inherited_parent_calls':sum(bool(c.get('inherited_from')) for c in s['calls']),
          'new_calls':sum(not c.get('inherited_from') for c in s['calls']),
          'overall_call_ceiling':s['execution_limits']['calls'],'concurrency':s.get('concurrency_progress'),
          'tasks':[{'id':t['id'],'status':t['status'],'error':t.get('error') if t['status']!='running' else None} for t in (scheduled_tasks(s) if s.get('production_stage') else s['tasks'])], 'log':str(run/'terminal.log'),'report':str(run/'report.html')},indent=2))
    elif a.action in ('pause','stop'):atomic_json(run/(a.action+'.json'),{'at':runtime.now()});print('Requested',a.action,'; pause finishes current response, stop preserves partial stream. GLM service unchanged.')
    elif a.action=='bundle':
        with writer_lock(run):bundle(run,read_json(run/'state.json'))
    elif a.action=='assemble':
        with writer_lock(run):assemble(run,read_json(run/'state.json'))

if __name__=='__main__':
    try:main()
    except Exception as exc:print('ERROR:',exc,file=sys.stderr);raise
