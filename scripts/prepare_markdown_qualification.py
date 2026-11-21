#!/usr/bin/env python3
"""Offline, isolated qualification preparation using the existing library worker.

No OCR, inference, services, credentials, corpus registration or pointer changes.
"""
import argparse,copy,json,shutil,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha
from probe import source_formats as fmt,focused_recovery,source_library
from scripts import library_pipeline as c
PARENT=ROOT/'runs/library-first-20261115T190611Z-power-recovery'
BOOK=Path('/home/mdi/pdf-benchmarks/escoffier/input/Escoffier_Le_Guide_Culinaire.pdf')
BOOK_SHA='cb9fe0df4906189d1a3e86519dc846c777fbabf555e6060b5df48318f596a49c'
TECH=['master-5f57f34a412e4d54-unit-001','master-cf49d8088dcbb711-unit-001','master-80f0aef600c203bb-unit-001']
SPANS=[(24,27,'Weights, measures, temperatures and cup conversion tables','xxiii–xxvi'),
       (28,39,'Two-column sauces; stocks, roux, numbered recipes and fractional quantities','1–12'),
       (400,403,'Poultry recipes, quantities and cross references','373–376'),
       (637,644,'Three-column alphabetical index; recipe numbers vs printed-page references','610–617')]

def refresh(parent):
    """Link a zero-call isolated preparation, preserving sealed unit ownership.

    Unlike a new preparation this copies verified inputs and tasks, never renders
    pages again, replans units, expands allowances or moves a production pointer.
    """
    parent=Path(parent).resolve()
    if not all(c.base.books.speed.idle(p) for p in (ROOT,ROOT/'runs',parent)):
        raise ValueError('Writer active; cannot refresh preparation')
    with c.writer_lock(ROOT),c.writer_lock(ROOT/'runs'),c.writer_lock(parent):
        old=read_json(parent/'state.json');plan=read_json(parent/'plan.json');binding=read_json(parent/'binding.json')
        if not plan.get('isolated_publication') or plan.get('paid_enabled') or plan.get('spend_cap_usd')!='0':
            raise ValueError('Only isolated unpaid qualification preparations can refresh here')
        if old['status']!='prepared' or old['calls'] or old.get('launches') or old['versions'] or old['current_versions'] or any(t['status']!='pending' for t in old['tasks']):
            raise ValueError('Consumed or started work cannot refresh; preserve attempts')
        # Historical code is intentionally different. Verify its sealed inputs
        # and zero-consumption ledger independently, then use the full normal
        # verifier on the child. Never patch the dispatch verifier or old seal.
        if sha(parent/'plan.json')!=binding['plan_sha256']:raise ValueError('Parent plan changed')
        c.InputGuard(binding['files']).check()
        c.InputGuard({str(parent/p):h for p,h in old['derived_inputs'].items()}).check()
        if plan['runtime_contract']!={k:old[k] for k in c.RUNTIME_FIELDS}:raise ValueError('Parent runtime identity changed')
        for key,u in old['source_units'].items():
            if read_json(parent/'inputs'/key/'unit.json')!=u:raise ValueError('Parent scope changed')
        if old.get('task_plan_sha256'):
            tp=parent/old.get('task_plan_path','task-plan.json');tasks=read_json(tp)
            if sha(tp)!=old['task_plan_sha256'] or tasks['task_ids']!=[t['id'] for t in old['tasks']] or tasks['task_definitions']!=[{k:t[k] for k in c.task_fields(plan)} for t in old['tasks']]:raise ValueError('Parent task allowance changed')
        kind=read_json(parent/'QUALIFICATION.json')['kind']
        if kind not in ('technical','cookbook'):raise ValueError('Unknown qualification kind')
        run=ROOT/'runs'/('markdown-'+kind+'-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-linked-'+str(time.time_ns())[-6:])
        shutil.copytree(parent,run,ignore=shutil.ignore_patterns('.probe.lock','report','normal-terminal-checks.json'))
        def relocate(x):
            if isinstance(x,str):return x.replace(str(parent)+'/',str(run)+'/') if x.startswith(str(parent)+'/') else x
            if isinstance(x,list):return [relocate(v) for v in x]
            if isinstance(x,dict):return {relocate(k):relocate(v) for k,v in x.items()}
            return x
        # Only derived absolute file locators change; the original bytes remain
        # in the parent and the link records the old and new JSON hashes.
        translations=[]
        for f in run.rglob('*.json'):
            value=read_json(f);new=relocate(value)
            if value!=new:
                before=sha(f);atomic_json(f,new);translations.append({'path':str(f.relative_to(run)),'parent_sha256':before,'child_sha256':sha(f)})
        state=read_json(run/'state.json');plan=read_json(run/'plan.json')
        state['remote']='/home/mdi/projects/pdf-to-latex-comparisons/'+run.name
        state.update(linked_preparation_from=str(parent),linked_at=c.runtime.now());state.pop('inspection',None)
        plan['runtime_contract']={k:state[k] for k in c.RUNTIME_FIELDS};plan['continuation_parent_preparation']=str(parent)
        for d in plan['documents']:
            if d.get('fixed_native'):d['fixed_native_sha256']=sha(run/d['fixed_native'])
        atomic_json(run/'plan.json',plan)
        state['derived_inputs']={p:sha(run/p) for p in state['derived_inputs']}
        if state.get('task_plan_sha256'):state['task_plan_sha256']=sha(run/state.get('task_plan_path','task-plan.json'))
        link={'parent':str(parent),'parent_plan_sha256':sha(parent/'plan.json'),'parent_state_sha256':sha(parent/'state.json'),'parent_binding_sha256':sha(parent/'binding.json'),
              'parent_consumed_calls':0,'task_ids_unchanged':[t['id'] for t in state['tasks']]==[t['id'] for t in old['tasks']],
              'settings_unchanged':plan['settings']==read_json(parent/'plan.json')['settings'],'relocated_json':translations,
              'reason':'Offline diagnostics and standard-notation validation; no new scope, attempts, OCR or publication'}
        prior_link=None
        if (parent/'preparation-link.json').exists():
            prior_link=run/'preparation-links'/(sha(parent/'preparation-link.json')+'.json')
            prior_link.parent.mkdir(exist_ok=True);shutil.copyfile(parent/'preparation-link.json',prior_link)
        atomic_json(run/'preparation-link.json',link)
        translated={str(run/x['path']):x for x in translations}
        files={}
        for p,h in binding['files'].items():
            child_path=str(prior_link) if Path(p)==parent/'preparation-link.json' and prior_link else relocate(p)
            change=translated.get(child_path)
            if change and change['parent_sha256']!=h:raise ValueError('Input changed during copy')
            expected=change['child_sha256'] if change else h
            if sha(child_path)!=expected:raise ValueError('Source bytes changed during copy')
            files[child_path]=expected
        files[str(run/'preparation-link.json')]=sha(run/'preparation-link.json')
        atomic_json(run/'binding.json',{'code':c.base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':files})
        c.save(run,state)
        q=read_json(run/'QUALIFICATION.json');q.update(linked_preparation_from=str(parent));q['commands']={a:'bash scripts/run-library-first.sh '+a+' --run '+str(run)+(' --allow-owned-handoff' if a=='run' and kind=='cookbook' else '') for a in ('run','status','pause','resume','bundle')};atomic_json(run/'QUALIFICATION.json',q)
        c.verify(run);print(run);return run

def continue_saved(parent):
    """Reassess saved Markdown envelopes/checks; only unconsumed critics may run.

    This is the three-unit local qualification, not historical-library recovery.
    Calls, sealed responses and consumed phase IDs are retained byte-for-byte.
    """
    parent=Path(parent).resolve()
    if not all(c.base.books.speed.idle(p) for p in (ROOT,ROOT/'runs',parent)):raise ValueError('Drain writer first')
    with c.writer_lock(ROOT),c.writer_lock(ROOT/'runs'),c.writer_lock(parent):
        old=read_json(parent/'state.json');plan=read_json(parent/'plan.json');binding=read_json(parent/'binding.json')
        if read_json(parent/'QUALIFICATION.json')['kind']!='technical' or not plan.get('isolated_publication') or plan['paid_enabled'] or plan['spend_cap_usd']!='0':raise ValueError('Only the unpaid technical qualification is eligible')
        if old['status'] not in ('paused',c.TERMINAL) or set(old['source_units'])!=set(TECH):raise ValueError('Wrong scope or undrained parent')
        ids=[t['id'] for t in old['tasks']]
        if set(ids)!={k+'/'+phase for k in TECH for phase in ('convert','critic')} or len(ids)!=6:raise ValueError('Six-phase allowance changed')
        if sha(parent/'plan.json')!=binding['plan_sha256']:raise ValueError('Parent plan changed')
        c.InputGuard(binding['files']).check();c.InputGuard({str(parent/p):h for p,h in old['derived_inputs'].items()}).check()
        tp=parent/old.get('task_plan_path','task-plan.json');sealed=read_json(tp)
        if sha(tp)!=old['task_plan_sha256'] or sealed['task_ids']!=ids or sealed['task_definitions']!=[{k:t[k] for k in c.task_fields(plan)} for t in old['tasks']]:raise ValueError('Task identity changed')
        if len({x['parent'] for x in old['calls']})!=len(old['calls']):raise ValueError('Duplicate consumed phase')
        for call in old['calls']:
            task=next(t for t in old['tasks'] if t['id']==call['parent'])
            if call['status']!='completed_response' or task.get('settled_call')!=call['id']:raise ValueError('Uncertain/unsettled call; no recovery replay')
            c.saved_response(parent,call,read_json(parent/'calls'/call['id']/'request.json'))
        run=ROOT/'runs'/('markdown-technical-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-saved-'+str(time.time_ns())[-6:])
        shutil.copytree(parent,run,ignore=shutil.ignore_patterns('.probe.lock','pause.json','report','deliveries','delivery-revisions','normal-terminal-checks.json','terminal.log'))
        state=read_json(run/'state.json')
        plan['continuation_parent_run']=str(parent);plan['maximum_work_requests_total']=6
        plan['continuation_reason']='Lossless saved-envelope parsing and coverage normalization; no repeated conversions/reviews or reset attempts'
        atomic_json(run/'plan.json',plan)
        state.update(status='prepared',stage='saved-answer reassessment; remaining original critics only',diagnostic=None,inherited_call_count=len(old['calls']),linked_continuation_from=str(parent));state.pop('inspection',None)
        reassessments=[]
        for key in TECH:
            task=next(t for t in state['tasks'] if t['key']==key and t['phase']=='convert')
            call=next(x for x in state['calls'] if x['parent']==task['id'])
            answer=(run/'calls'/call['id']/'answer.txt').read_text()
            document,info=fmt.parse_markdown(answer,call['metadata']['finish_reason'])
            existing=state['versions'].get(key,{}).get('convert')
            if existing and (sha(run/existing['path'])!=existing['sha256'] or (run/existing['path']).read_text()!=document):raise ValueError('Reassessment changed an existing draft')
            version=c.compile_version(run,state,task,document,'convert-saved-reassessment-'+call['id'])
            label='convert_reassessed' if existing else 'convert';state['versions'].setdefault(key,{})[label]=version;state['current_versions'][key]=label
            previous=task['status'];task.update(status='conversion_completed',historical_status_before_reassessment=previous)
            notes=run/'call-results'/call['id']/'saved-reassessment.json';atomic_json(notes,{'parent':str(parent),'raw_answer_sha256':sha(run/'calls'/call['id']/'answer.txt'),'parsed_draft_sha256':version['sha256'],'envelope':info,'prior_status':previous,'new_request':False})
            task.setdefault('result_files',{})[str(notes.relative_to(run))]=sha(notes)
            critic=next(t for t in state['tasks'] if t['key']==key and t['phase']=='critic')
            consumed=any(x['parent']==critic['id'] for x in state['calls'])
            if consumed:
                reviewed=state['versions'][key].get('review')
                if reviewed:
                    v=c.compile_version(run,state,critic,(run/reviewed['path']).read_text(),'review-saved-validation-'+reviewed['sha256'][:16]);state['versions'][key]['review_reassessed']=v
                    if v['content_check']['usable']:state['current_versions'][key]='review_reassessed'
            elif version['content_check']['usable']:
                if critic['status'] not in ('pending','unavailable'):raise ValueError('Cannot reset failed critic allowance')
                critic.update(status='pending',recovery_reason='Same saved complete draft now parseable; original critic allowance unconsumed')
            reassessments.append({'key':key,'conversion_call':call['id'],'draft_sha256':version['sha256'],'usable':version['content_check']['usable'],'critic_consumed':consumed,'critic_status':critic['status']})
        for doc in state['documents'].values():
            doc['inherited_delivery']=doc.get('delivery');doc['published']=False;doc['selected_new_generation']=False
        link={'parent':str(parent),'parent_plan_sha256':sha(parent/'plan.json'),'parent_state_sha256':sha(parent/'state.json'),'parent_binding_sha256':sha(parent/'binding.json'),
              'consumed_calls_preserved':len(old['calls']),'maximum_total_work_requests':6,'remaining_unconsumed_phases':[t['id'] for t in state['tasks'] if t['status']=='pending'],
              'new_conversions_permitted':0,'reassessments':reassessments,'historical_raw_answers_and_statuses_preserved_in_parent':True}
        atomic_json(run/'saved-continuation.json',link)
        files=dict(binding['files'])
        for path,h in binding['files'].items():
            if Path(path).is_relative_to(parent):
                child=run/Path(path).relative_to(parent)
                if sha(child)!=h:raise ValueError('Copied input changed')
                files[str(child)]=h
        files[str(run/'saved-continuation.json')]=sha(run/'saved-continuation.json')
        atomic_json(run/'binding.json',{'code':c.base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':files})
        q=read_json(run/'QUALIFICATION.json');q.update(linked_continuation_from=str(parent),consumed_work_requests=len(old['calls']),remaining_work_requests=len(link['remaining_unconsumed_phases']))
        q['commands']={a:'bash scripts/run-library-first.sh '+a+' --run '+str(run) for a in ('run','status','pause','resume','bundle')};atomic_json(run/'QUALIFICATION.json',q)
        c.save(run,state);c.verify(run)
        if state['calls']!=old['calls']:raise ValueError('Consumed call history changed')
        print(run);return run

def prepare(kind,output_format='markdown'):
    import fitz
    if not all(c.base.books.speed.idle(p) for p in (ROOT,ROOT/'runs')):raise ValueError('Project writer active; no bound-code preparation')
    old=read_json(PARENT/'state.json');op=read_json(PARENT/'plan.json')
    if old['status']!=c.TERMINAL or any(x['status'] not in ('completed_response','failed') for x in old['calls']):raise ValueError('Historical worker not settled')
    if kind=='cookbook':
        if not BOOK.is_file() or sha(BOOK)!=BOOK_SHA:raise ValueError('Cookbook absent or SHA-256 mismatch; independent technical preparation remains usable')
        with fitz.open(BOOK) as pdf:
            if len(pdf)!=677:raise ValueError('Cookbook physical-page count mismatch')
    run=ROOT/'runs'/('markdown-'+kind+'-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+str(time.time_ns())[-6:]);run.mkdir()
    state={k:copy.deepcopy(old[k]) for k in c.RUNTIME_FIELDS if k!='remote'}
    state.update(copy.deepcopy({k:old[k] for k in ('timing_policy','chapter_contract','concurrency_policy')}))
    contract=fmt.explicit(output_format)
    state.update(contract,status='prepared',stage='offline qualification prepared; no dispatch',calls=[],tasks=[],versions={},current_versions={},source_units={},documents={},derived_inputs={},
      connection_failures=0,first_dispatch=None,active_stage=1,stages={'1':{}},launches=[],disable_dependency_downloads=True,suite_protocol='source-image-review-v1',production_stage={'task_ids':[]},resource_phase='not_started',
      remote='/home/mdi/projects/pdf-to-latex-comparisons/'+run.name,extraction={'mineru_pro':{'status':'prepared','pages':{}}},models_downloaded=True,inputs_prepared=False,execution_limits={'calls':None,'attempts_per_unit':1})
    if state.get('compiler_environment'):
        origin=PARENT/state['compiler_environment']['path']
        if origin.exists():shutil.copytree(origin,run/state['compiler_environment']['path'])
    shutil.copyfile(PARENT/'effort-support-offline.json',run/'effort-support-offline.json')
    plan={**contract,'workflow':c.policy.VERSION,'status':'frozen','settings':dict(c.policy.DEFAULTS),'documents':[],'workloads':{'mineru_pro':[]},'reuse':[],
      'paid_enabled':False,'spend_cap_usd':'0','isolated_publication':True,'purpose':kind+' format qualification only; not a production queue',
      'parent_evidence':str(PARENT),'parent_plan_sha256':sha(PARENT/'plan.json'),'parent_state_sha256':sha(PARENT/'state.json'),
      'source_priority':'Matching author TeX remains preferred for production; these explicit technical scopes are bounded format tests, not replacement generations',
      'no_recursive_splitting_or_retry':True,'runtime_image':state['runtime_image'],'remote_models':state['remote_models'],'runtime_contract':{k:state[k] for k in c.RUNTIME_FIELDS}}
    if kind=='technical':
        for key in TECH:
            u=old['source_units'][key];sid=u['source_key'];d=copy.deepcopy(next(d for d in op['documents'] if d['source_id']==sid))
            d['physical_pages']=u['physical_pages'];d['pages']=[x for x in d['pages'] if x['physical_pdf_page'] in u['physical_pages']]
            for pg in d['pages']:source_library.copy_verified(PARENT/pg['path'],run/pg['path'],pg['sha256'])
            if sha(d['original'])!=d['sha256']:raise ValueError('Technical original changed')
            fixed={'blocks':copy.deepcopy(u['native_blocks']),'assets':{}}
            for name,path in u['assets'].items():
                source_library.copy_verified(path,run/'inputs'/name);fixed['assets'][name]=str(run/'inputs'/name)
            target=run/'sources'/sid/'fixed-native.json';atomic_json(target,fixed)
            d.update(fixed_native=str(target.relative_to(run)),fixed_native_sha256=sha(target),earlier_context=u['context'],qualified_unit_limits={'maximum_pages':4,'maximum_chars':24000},role='format_qualification',historical_unit=key)
            source_library.copy_verified(PARENT/'sources'/sid/'secondary-assessment.json',run/'sources'/sid/'secondary-assessment.json')
            # Saved TeX baseline is evidence only; it never enters new converter/critic inputs.
            for label,v in old['versions'][key].items():source_library.copy_verified(PARENT/v['path'],run/'baseline'/key/(label+'.tex'),v['sha256'])
            atomic_json(run/'baseline'/key/'versions.json',old['versions'][key])
            plan['reuse'].append({'source':sid,'unit':key,'source_blocks':u['blocks'],'extraction':'Verified saved native blocks/assets reused; no OCR','prior_conversion':'Contextual comparison, not a matching Markdown request'})
            plan['documents'].append(d)
    else:
        sid='benchmark-escoffier-'+BOOK_SHA[:16];pages=[n for a,b,_,_ in SPANS for n in range(a,b+1)]
        d={'source_id':sid,'filename':BOOK.name,'sha256':BOOK_SHA,'original':str(BOOK),'physical_pages':pages,'pages':[],
           'library_document':{'source_id':sid,'sha256':BOOK_SHA,'folder':sid,'document_type':'cookbook_benchmark_excerpt'},'role':'benchmark_only',
           'source_scope_notes':'28 assigned physical pages in four contiguous spans, not the complete cookbook. Boundary continuations are explicitly recorded; neighbouring pages are context only.',
           'earlier_context':'Cookbook benchmark: preserve wording and quantities without modernization or interpretation. Embedded PDF OCR is a fallible comparison baseline. Four sampled spans: '+json.dumps(SPANS)+'. At external sample edges preserve assigned printed fragments; do not invent omitted continuations. A cross-boundary recipe is partial in this benchmark. Index left numbers identify recipes, right numbers identify printed pages. Do not modernize fractions, measures or ingredient names.'}
        with fitz.open(BOOK) as pdf:
            quality=focused_recovery.secondary_assessment([{'physical_pdf_page':n,'printed_page':('xxiii xxiv xxv xxvi'.split()[n-24] if n<=27 else str(n-27)),'text':pdf[n-1].get_text()} for n in pages])
            quality['baseline_status']='Embedded OCR comparison only, not ground truth; page images authoritative for source reading'
            atomic_json(run/'sources'/sid/'secondary-assessment.json',quality)
            atomic_json(run/'sources'/sid/'embedded-ocr-baseline.json',[{'physical_page':n,'text':pdf[n-1].get_text()} for n in pages])
            for n in pages:
                path=run/'sources'/sid/f'page-{n:03}.png';path.parent.mkdir(parents=True,exist_ok=True);pix=pdf[n-1].get_pixmap(matrix=fitz.Matrix(200/72,200/72));pix.save(path)
                d['pages'].append({'physical_pdf_page':n,'printed_page':('xxiii xxiv xxv xxvi'.split()[n-24] if n<=27 else str(n-27)),'printed_label_status':'Mapping follows visible Roman front matter / Arabic offset; individual labels available in image for verification','path':str(path.relative_to(run)),'image':str(path.relative_to(run)),'sha256':sha(path),'dimensions':[pix.width,pix.height]})
            context=[]
            for n,reason in [(40,'Continuation after sauces sample; exclude from assigned output'),(399,'Poultry sample starts inside recipe; earlier content context only'),(404,'Recipe3130 continues after poultry sample; context only'),(645,'Adjacent index context; not assigned output')]:
                path=run/'sources'/sid/f'context-{n:03}.png';pix=pdf[n-1].get_pixmap(matrix=fitz.Matrix(200/72,200/72));pix.save(path)
                context.append({'physical_page':n,'printed_page':str(n-27),'reason':reason,'path':str(path.relative_to(run)),'sha256':sha(path),'dimensions':[pix.width,pix.height],'embedded_ocr_comparison':pdf[n-1].get_text()})
            atomic_json(run/'sources'/sid/'boundary-context.json',context)
            atomic_json(run/'sources'/sid/'edition-evidence.json',{'physical_pages':[6,7],'embedded_title_page':pdf[5].get_text(),'embedded_copyright_page':pdf[6].get_text(),'edition':'2011 fifth English edition, translation of fourth French edition; original work1903 is not this edition'})
        plan['documents']=[d];plan['workloads']['mineru_pro']=[[sid,n] for n in pages]
        plan['benchmark']={'edition':'2011 fifth English','original_work_year':1903,'total_physical_pages':677,'assigned_pages':28,'spans':[{'physical_pages':[a,b],'printed_labels':labels,'reason':reason} for a,b,reason,labels in SPANS],
         'external_boundary_policy':'All assigned page content is output-owned once. Four adjacent page images retained as comparison context, not extra extraction/assigned output. Cross-boundary recipe fragments explicitly remain partial; no implied complete recipe/paper claim.',
         'comparison':'Dan independently developed pipeline; same PDF/page hashes, raw OCR and images; no presumed ground truth from embedded OCR',
         'storage':'Run-only delivery; never registered/published in quantitative-paper collection','render_dpi':200}
    for d in plan['documents']:
        state['documents'][d['source_id']]={'filename':d['filename'],'status':'pending_extraction','source_sha256':d['sha256'],'units':[],'original':d['original'],'historical_selection':None}
    c.policy.validate_extraction_plan(plan,run);atomic_json(run/'plan.json',plan)
    frozen={str(x):sha(x) for x in (run/'sources').rglob('*') if x.is_file()};frozen.update({d['original']:d['sha256'] for d in plan['documents']});frozen[str(run/'effort-support-offline.json')]=sha(run/'effort-support-offline.json')
    atomic_json(run/'binding.json',{'code':c.base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':frozen})
    c.save(run,state)
    if kind=='technical':
        state['extraction_done']=True;c.plan_units(run,state)
        if len(state['source_units'])!=3 or len(state['tasks'])!=6:raise ValueError('Qualification must remain exactly three units/six work requests')
        for t in state['tasks']:
            if t['phase']=='convert':atomic_json(run/'previews'/(t['key']+'-convert.json'),c.body_for(run,state,t))
        plan_limit=6
    else:plan_limit='One conversion + conditional exact-draft High image review per sealed coherent unit, with no retries. Exact task count derives after OCR; no requests before ownership ledger is sealed.'
    atomic_json(run/'QUALIFICATION.json',{'state':'PREPARED_NOT_RUNNING','kind':kind,'paid_calls':0,'new_ocr_pages':len(plan['workloads']['mineru_pro']),'work_requests':plan_limit,
      'checks':['Full owned content and equation labels','Figures/captions, footnotes, table rows/headers/quantities','Draft/format-bound source-image review','Unresolved macros/structures visible','Semantic source fidelity assessed separately from Markdown syntax'],
      'commands':{a:'bash scripts/run-library-first.sh '+a+' --run '+str(run)+(' --allow-owned-handoff' if a=='run' and kind=='cookbook' else '') for a in ('run','status','pause','resume','bundle')}})
    c.verify(run);print(run);return run

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['technical','cookbook','refresh','continue-saved']);p.add_argument('--parent',type=Path);p.add_argument('--output-format',choices=['markdown','latex'],default='markdown');a=p.parse_args()
    if a.kind in ('refresh','continue-saved'):
        if a.parent is None:p.error(a.kind+' requires --parent')
        (refresh if a.kind=='refresh' else continue_saved)(a.parent)
    else:prepare(a.kind,a.output_format)
