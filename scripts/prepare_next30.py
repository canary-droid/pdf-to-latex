#!/usr/bin/env python3
"""Revision2: saved four-paper repair plus the exact authorized30. No inference here."""
import argparse,copy,difflib,hashlib,json,re,shutil,struct,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha,fingerprint,writer_lock
from probe.source_library import copy_verified,slug
from probe import library_repair as repair,library_allocation as allocation,library_first as policy,kimi_escalation as kimi
from probe.experiment import verify_seal
from scripts import library_pipeline as c
PARENT=ROOT/'runs/library-overnight-20261108T040405Z'
TASK=Path(read_json(ROOT/'results/next30-task-current.json')['task_directory']);DEV=TASK.parent
LIBRARY=Path('/home/mdi/llm-wiki/sources')
SMILE='original-ee9d62e0261b2dcc';LEE='original-c6fbf9bf1bbc7325';BOY='original-af03317e4e74c832';LEWIS='original-1e05399704af3696'

def curated():
    parent=read_json(PARENT/'state.json');rows=[]
    for sid in [SMILE,LEE,LEWIS]:
        for key in parent['documents'][sid]['units']:
            label=parent['current_versions'][key]
            if key==SMILE+'-unit-001':label='kimi-critic'
            if key==LEWIS+'-unit-010':label='review'
            version=parent['versions'][key][label];path=PARENT/version['path']
            if sha(path)!=version['sha256']:raise ValueError('Saved selected/candidate version changed')
            original=path.read_text();text=original;notes=[]
            if key==SMILE+'-part-001':
                tag=text.index(r'\tag{A.44}');end=text.index(r'\end{equation}',tag)+len(r'\end{equation}')
                text=text[:end]+'\n\n\\end{document}\n';notes.append('Owned source ends atA44; secondary-derived A45-A51 and their uncertain reconstruction notes retained in prior.tex, superseded by unit001. Original p16 verified; complete equations/prose throughA44 retained.')
            if key==SMILE+'-unit-001':
                tag=text.index(r'\tag{A.61}');start=text.rfind(r'\begin{equation',0,tag)
                text=text[:start]+'\n\\end{document}\n';notes.append('Retain A3 introductory prose; A61-A65 and all associated prose have sole emitted owner unit002. Original p18 checked. Adopt already-reviewed A47[f-K]+ correction, confirmed against original p16.')
            out=DEV/'curated'/key;out.mkdir(parents=True,exist_ok=True);copy_verified(path,out/'prior.tex');(out/'document.tex').write_text(text);(out/'changes.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True),fromfile='prior.tex',tofile='document.tex')))
            u=copy.deepcopy(parent['source_units'][key])
            if key==SMILE+'-part-001':
                decisions=[]
                for b in u['native_blocks']:
                    titles=c.book_completion.headings(b['tex']) if b['kind']=='paragraph_title' else []
                    if not titles or titles[0] not in ('Wilmott magazine','TECHNICAL ARTICLE','TABLE 3.2'):continue
                    title=titles[0];n=b['page']['original_physical_page']
                    image=DEV/'source-checks'/SMILE/f'page-{n:03}.png'
                    if not image.exists():
                        import fitz
                        original=next(d['original'] for d in read_json(PARENT/'plan.json')['documents'] if d['source_id']==SMILE);image.parent.mkdir(parents=True,exist_ok=True)
                        with fitz.open(original) as pdf:pdf[n-1].get_pixmap(matrix=fitz.Matrix(2,2)).save(image)
                    evidence={'block':b['id'],'block_text_sha256':hashlib.sha256(b['tex'].encode()).hexdigest(),'title':title,'source_image_sha256':sha(image),'source_image':str(image),'disposition':'retained_caption' if title=='TABLE 3.2' else 'running_furniture','reason':'Source running journal header, or retained source table caption immediately before actual table.'}
                    if title=='TABLE 3.2':evidence['exact_output_anchor']=r'\noindent{\small\itshape TABLE 3.2\enspace MATRIX OF CORRELATIONS $\rho$ BETWEEN THE'
                    decisions.append(evidence)
                u['coverage_metadata']={'heading_adjudications':decisions}
            if key==SMILE+'-unit-001':
                block=next(b for b in u['native_blocks'] if b['id']==SMILE+'-p0018:b10')
                u['coverage_metadata']={'equation_label_adjudications':[{'block':block['id'],'block_text_sha256':hashlib.sha256(block['tex'].encode()).hexdigest(),'observed':'59c','source_reading':'A.59c','source_image_sha256':sha(PARENT/'sources'/SMILE/'page-018.png'),'source_location':'Physicalp18/printed101, leftcolumn; original image visibly prints A.59c; nearby A59b and source-reference A59a-A59c agree.'}]}
            check=c.content_check(PARENT,dict(parent,source_units={key:u}),{'key':key},text)
            record={'source_id':sid,'unit':key,'parent_label':label,'parent_version':version,'parent_path':str(path),'selected_tex':str(out/'document.tex'),'sha256':sha(out/'document.tex'),'source_unit':u,'changes':notes,'content_check':check,'review_history':'Parent local/Kimi logs retained. Curated ownership edits are independently source-checked; not retrospective model attestation.'}
            atomic_json(out/'provenance.json',record);rows.append(record)
    for sid in [SMILE,LEE,LEWIS]:
        screen=repair.overlap_screen([(r['unit'],Path(r['selected_tex']).read_text()) for r in rows if r['source_id']==sid]);atomic_json(DEV/'curated'/(sid+'-assembly-screen.json'),screen)
        if screen['duplicate_equation_tags']:raise ValueError('Unreconciled output overlap '+sid)
    atomic_json(DEV/'curated.json',rows);print('Curated saved units:',len(rows),'content flags:',[(r['unit'],r['content_check']['content_issues']) for r in rows if not r['content_check']['usable']])

def resolve_docs():
    selected=read_json(TASK/'selected-30.json');resolved=read_json(DEV/'resolved-inputs.json');index=read_json(LIBRARY/'library-first-status.json');known={x['source_sha256']:x for x in index['sources']};docs=[];dispositions=[]
    for item in selected['papers']:
        record=next((r for r in resolved if r['sha256']==item['sha256']),None)
        if not record or not Path(record['resolved_path']).exists():dispositions.append(dict(item,disposition='missing_input'));continue
        p=Path(record['resolved_path'])
        if sha(p)!=item['sha256']:raise ValueError('New source identity changed')
        import fitz
        with fitz.open(p) as pdf:
            if len(pdf)!=item['pages']:raise ValueError('New source page count differs')
        prior=known.get(item['sha256'])
        meta=record['intake_metadata'];sid=prior['source_id'] if prior else meta['source_id']
        folder=prior['folder'] if prior else slug(item['filename'][:-4],100)+'--'+item['sha256'][:16]
        d={'source_id':sid,'folder':folder,'sha256':item['sha256'],'page_count':item['pages'],'title':meta['title'],'document_type':meta['document_type'],'completeness':meta['completeness'],'originals':[{'path':str(p),'name':item['filename'],'sha256':item['sha256'],'bytes':p.stat().st_size}],
          'archive_member':item['archive_member'],'master_archive_sha256':'a75f2a6c1e7d7bffe81ff006b93883a9ced319f7d98ec5a5d5eddd66b11a4d3d','queue_id':item['queue_id'],'order':item['order'],'collection_membership':'350-PDF master, explicit selected30; not the376-source union','bibliographic_metadata':meta}
        disposition='reuse_ready_generation' if prior and prior['status']=='ready' else 'queued'
        if prior and (LIBRARY/folder/'source.json').exists():d=read_json(LIBRARY/folder/'source.json')
        docs.append((d,record,item,disposition));dispositions.append(dict(item,source_id=sid,disposition=disposition,resolved_path=str(p),existing_generation=prior.get('selected_generation') if prior else None))
    if len(dispositions)!=30:raise ValueError('All30 must be represented')
    atomic_json(DEV/'input-dispositions.json',dispositions);return docs,dispositions

def prepare():
    if not all(c.base.books.speed.idle(p) for p in [ROOT,ROOT/'runs',PARENT]):raise ValueError('Existing writer active; do not create duplicate')
    parent=read_json(PARENT/'state.json');oldplan=read_json(PARENT/'plan.json')
    if parent['status']!=c.TERMINAL:raise ValueError('Parent is not finished; reconcile active state first')
    registry=DEV/'active-run.json'
    if registry.exists():
        previous=Path(read_json(registry)['run']);state=read_json(previous/'state.json')
        if state['calls'] or state.get('launches'):print('Existing execution; resume only:',previous);return previous
    curated_rows=read_json(DEV/'curated.json');docs,dispositions=resolve_docs();source_scope={d['source_id']:{'sha256':d['sha256'],'physical_pages':list(range(1,d['page_count']+1))} for d,_,_,_ in docs}
    for d in oldplan['documents']:source_scope[d['source_id']]={'sha256':d['sha256'],'physical_pages':list(range(1,d['library_document']['page_count']+1))}
    if len(source_scope)!=34:raise ValueError('The allocation must bind all exact34 source identities')
    metadata=read_json(DEV/'kimi-public/metadata.json');config=kimi.profile(metadata,'7.00',tasks=0);config.update(paid_limits=None,no_generation_deadline=True,readiness='No generating control: reuse successful route, verify public metadata/private allowance per genuine task')
    cloud,approval=allocation.create(ROOT,TASK/'BUDGET-AUTHORIZATION.json',source_scope,config,PARENT)
    config=read_json(cloud/'binding.json')['config'];prior_billing=read_json(cloud/'binding.json')['prior_billing']
    allocation.reconcile_old(PARENT,DEV/'historical-hold-releases',DEV/'before-code')
    run=ROOT/'runs'/('library-next30-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));run.mkdir()
    state={k:copy.deepcopy(parent[k]) for k in ['chapter_contract','timing_policy','execution_limits','concurrency_policy','compiler_environment','runtime_image','remote_models']}
    state.update(status='prepared',stage='new authorization v2; launch authorized',calls=[],tasks=[],versions={},current_versions={},source_units={},derived_inputs={},documents={},connection_failures=0,first_dispatch=None,active_stage=1,stages={'1':{}},launches=[],disable_dependency_downloads=True,suite_protocol='source-image-review-v1',production_stage={'task_ids':[]},resource_phase='not_started',remote='/home/mdi/projects/pdf-to-latex-comparisons/'+run.name,extraction={'mineru_pro':{'status':'prepared','pages':{}}},models_downloaded=True,inputs_prepared=False,ready_baseline=56,ready_added_offline=0,paid_approval_sha256=fingerprint(approval))
    plan={'status':'frozen','workflow':'library-first-v1','allocation_id':allocation.AUTH_ID,'overnight':True,'settings':dict(policy.DEFAULTS,paid_enabled=True,new_spend_budget_usd='7.00'),'paid_enabled':True,'spend_cap_usd':'7.00','paid_approval':approval,'kimi_config':config,'prior_billing':prior_billing,'approval_registry':str(registry),
          'documents':[],'workloads':{'mineru_pro':[]},'reuse':[],'input_dispositions':dispositions,'task_order':'new_paper_order_with_recovery_interleave','allow_sparse_source_content':True,'runtime_image':state['runtime_image'],'remote_models':state['remote_models'],'runtime_contract':{k:state.get(k) for k in c.RUNTIME_FIELDS},'parent_run':str(PARENT),'authorization_file_sha256':sha(TASK/'BUDGET-AUTHORIZATION.json'),'source_selection_sha256':sha(TASK/'selected-30.json'),'no_recursive_splitting_or_retry':True}
    import fitz
    live={x['source_id']:x for x in read_json(LIBRARY/'library-first-status.json')['sources']}
    available=[(d,record['resolved_path'],item['filename'],'new',disposition) for d,record,item,disposition in docs]
    available += [(d['library_document'],d['original'],d['filename'],'recovery','recover_saved') for d in oldplan['documents']]
    for d,original,filename,role,disposition in available:
        sid=d['source_id'];pages=list(range(1,d['page_count']+1));doc={'source_id':sid,'filename':filename,'sha256':d['sha256'],'original':str(original),'physical_pages':pages,'pages':[],'library_document':d,'role':role,'disposition':disposition,'blank_pages':{},'original_page_count':d['page_count']}
        folder=LIBRARY/d['folder'];pointer=read_json(folder/'current.json') if (folder/'current.json').exists() else None
        state['documents'][sid]={'filename':filename,'status':'pending_extraction','source_sha256':d['sha256'],'original':str(original),'units':[],'historical_selection':pointer,'reused_units':[],'role':role}
        if role=='recovery':doc['reused_extraction_pages']=pages
        with fitz.open(original) as pdf:
            native=[]
            for n in pages:
                path=run/'sources'/sid/f'page-{n:03}.png';path.parent.mkdir(parents=True,exist_ok=True)
                previous=PARENT/'sources'/sid/path.name
                if previous.exists():copy_verified(previous,path)
                else:pdf[n-1].get_pixmap(matrix=fitz.Matrix(200/72,200/72)).save(path)
                page={'physical_pdf_page':n,'path':str(path.relative_to(run)),'image':str(path.relative_to(run)),'sha256':sha(path),'dimensions':list(struct.unpack('>II',path.read_bytes()[16:24]))};doc['pages'].append(page)
                native.append({'physical_pdf_page':n,'text':pdf[n-1].get_text()})
                if not pdf[n-1].get_text().strip():
                    blank=repair.blank_page(original,n,d['sha256'])
                    if blank['qualified_blank']:doc['blank_pages'][str(n)]=blank
            atomic_json(run/'sources'/sid/'secondary-assessment.json',c.requests.secondary_assessment(native))
        if disposition=='reuse_ready_generation':
            doc['reused_extraction_pages']=pages;state['documents'][sid].update(status='reused_ready',planning_done=True,published=True,publication=pointer)
        elif role=='new':plan['workloads']['mineru_pro'] += [[sid,n] for n in pages if str(n) not in doc['blank_pages']]
        if role=='recovery':
            for key,rec in read_json(PARENT/'arms/mineru_pro/state.json')['pages'].items():
                if rec['source_id']!=sid or rec['status']!='completed':continue
                for artifact in rec['outputs']:copy_verified(PARENT/'arms/mineru_pro'/artifact['path'],run/'arms/mineru_pro'/artifact['path'],artifact['sha256'])
                state['extraction']['mineru_pro']['pages'][key]=dict(rec,reused_from=str(PARENT))
                plan['reuse'].append({'source':sid,'page':rec['physical_page'],'parent':str(PARENT),'outputs':rec['outputs']})
            for row in curated_rows:
                if row['source_id']!=sid:continue
                key=row['unit'];u=copy.deepcopy(row['source_unit']);assets={}
                for name,p in u['assets'].items():copy_verified(p,run/'reused-assets'/sid/name);assets[name]=str(run/'reused-assets'/sid/name)
                u['assets']=assets;state['source_units'][key]=u;atomic_json(run/'inputs'/key/'unit.json',u);state['derived_inputs']['inputs/'+key+'/unit.json']=sha(run/'inputs'/key/'unit.json')
                dest=run/'versions'/key/'reconciled';dest.mkdir(parents=True)
                for name in ('document.tex','prior.tex','changes.diff','provenance.json'):copy_verified(DEV/'curated'/key/name,dest/name)
                v={'path':str((dest/'document.tex').relative_to(run)),'sha256':row['sha256'],'compilation':{'status':'not_requested'},'parent':row['parent_version'],'source_checked_repairs':row['changes'],'content_check':c.content_check(run,state,{'key':key},(dest/'document.tex').read_text())}
                state['versions'][key]={'reconciled':v};state['current_versions'][key]='reconciled';state['documents'][sid]['units'].append(key);state['documents'][sid]['reused_units'].append(key)
                plan['reuse'].append({'source':sid,'unit':key,'sha256':row['sha256'],'parent_version_sha256':row['parent_version']['sha256']})
                history=run/'inputs'/key/'review-history';history.mkdir()
                for t in parent['tasks']:
                    if t['key']!=key:continue
                    if t.get('call'):
                        for f in (PARENT/'call-results'/t['call']).glob('*'):
                            if f.is_file():copy_verified(f,history/(t['call']+'-'+f.name))
                    pr=t.get('paid_recovery',{})
                    if pr.get('attempt_path'):
                        for name in ('findings.json','changes.diff','outcome.json'):
                            p=Path(pr['attempt_path'])/name
                            if p.exists():copy_verified(p,history/('kimi-'+t['phase']+'-'+name))
                    salvage=DEV/'salvaged-reviews'/t.get('call','none')/'findings.json'
                    if salvage.exists():copy_verified(salvage,history/(t['call']+'-salvaged-findings.json'))
            if sid in (SMILE,LEE):
                keys=state['documents'][sid]['units'];owned=[b for k in keys for b in state['source_units'][k]['blocks']]
                state['documents'][sid].update(status='reconciled_saved',planning_done=True,source_accounting={'total_regions':len(owned),'reused_regions':len(owned),'all_regions_accounted':len(owned)==len(set(owned)),'fully_scheduled':True,'basis':'Exact saved owned scopes; duplicate output reconciled separately'})
            if sid==LEWIS:
                raw=read_json(PARENT/'source-plans'/f'{sid}.json');missing=[u for u in raw['scopes'] if u['disposition']=='outstanding']
                if len(missing)!=1 or len(missing[0]['blocks'])!=53 or len(missing[0]['text'])!=14709:raise ValueError('Missing Lewis source differs')
                u=missing[0];assets=copy.deepcopy(state['source_units'][sid+'-unit-003']['assets']);path=run/'fixed-scopes'/f'{sid}.json';atomic_json(path,{'blocks':u['native_blocks'],'assets':assets,'source_sha256':d['sha256'],'parent_scope_sha256':u['text_sha256']})
                doc.update(fixed_native=str(path.relative_to(run)),fixed_native_sha256=sha(path),qualified_unit_limits={'maximum_pages':6,'maximum_chars':24000},earlier_context=parent['source_units'][sid+'-unit-003']['context']+'\n'+parent['source_units'][sid+'-unit-003']['text'],earlier_cloud_context='')
                doc['unit_key_prefix']=sid+'-missing';doc['unit_insertion_after']=sid+'-unit-003'
                doc['qualification']={'scope_sha256':u['text_sha256'],'physical_pages':u['physical_pages'],'characters':14709,'full_pages':6,'detail_crops':2,'maximum_image_tokens':16384,'per_image_tokens':2048,'image_count':8,'serving_limit_changes':False,'context_token_capacity':'Actual image/token/body admission is mandatory before dispatch','reason':'Keep Proposition2.1 and connected mathematics intact; a single source-bound6-page exception. No split proof or source clipping.'}
        plan['documents'].append(doc)
    atomic_json(run/'arms/mineru_pro/state.json',state['extraction']['mineru_pro'])
    if state.get('compiler_environment') and (PARENT/state['compiler_environment']['path']).exists():shutil.copytree(PARENT/state['compiler_environment']['path'],run/state['compiler_environment']['path'])
    copy_verified(PARENT/'effort-support-offline.json',run/'effort-support-offline.json')
    for name in ['BUDGET-AUTHORIZATION.json','selected-30.json','recovery-4.json','selected-30-source-audit.json']:copy_verified(TASK/name,run/'authorization'/name)
    shutil.copytree(DEV/'historical-hold-releases',run/'historical-hold-releases');copy_verified(DEV/'review-salvage.json',run/'review-salvage.json')
    atomic_json(run/'plan.json',plan);policy.validate_extraction_plan(plan,run)
    atomic_json(run/'input-dispositions.json',dispositions)
    for path,digest in c.base.code_binding().items():copy_verified(ROOT/path,run/'implementation'/path,digest)
    for path in (ROOT/'tests').glob('*.py'):copy_verified(path,run/'implementation/tests'/path.name)
    for name in ('AGENTS.md','docs/CODEX-HANDOVER.md','docs/PROJECT-STATE.md','docs/LIBRARY-FIRST.md'):copy_verified(ROOT/name,run/'implementation'/name)
    (run/'implementation/working-tree.diff').write_bytes(c.subprocess.check_output(['git','diff','--no-ext-diff'],cwd=ROOT))
    frozen={str(p):sha(p) for directory in ('sources','fixed-scopes','reused-assets','authorization','historical-hold-releases') for p in (run/directory).rglob('*') if p.is_file()}
    frozen.update({d['original']:d['sha256'] for d in plan['documents']});frozen[str(run/'effort-support-offline.json')]=sha(run/'effort-support-offline.json')
    atomic_json(run/'binding.json',{'code':c.base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':frozen,'config':config,'prior_billing':prior_billing});atomic_json(registry,{'run':str(run),'authorization_id':allocation.AUTH_ID});c.save(run,state);c.verify(run)
    atomic_json(ROOT/'results/next30-current.json',{'run':str(run),'authorization_id':allocation.AUTH_ID,'task_directory':str(TASK),'status':'prepared'});atomic_json(c.POINTER,{'run':str(run),'status':'PREPARED_NOT_RUNNING'});print(run);return run

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['curate','prepare']);a=p.parse_args();(curated if a.action=='curate' else prepare)()
