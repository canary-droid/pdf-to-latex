#!/usr/bin/env python3
"""Freeze the explicitly selected60-paper local-only job. No inference or library writes."""
import copy,json,shutil,struct,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha,writer_lock
from probe.source_library import copy_verified,slug
from scripts import library_pipeline as c
from probe.library_night_day import validate_plan
DEV=ROOT/'results/library-night-day-20261109-preparation'
PARENT=ROOT/'runs/library-completion-20261109T072416Z-labels'
POINTER=ROOT/'results/library-night-day-current.json'

def prepare():
    if POINTER.exists():
        run=Path(read_json(POINTER)['run']);c.verify(run);print(run);return run
    if not all(c.base.books.speed.idle(p) for p in (ROOT,ROOT/'runs')):raise ValueError('Existing writer; no duplicate preparation')
    selection=read_json(DEV/'reconciled-60.json');rows=selection['papers']
    if len(rows)!=60 or sum(r['pages'] for r in rows)!=704:raise ValueError('Previously agreed selection changed')
    if sha(DEV/'reconciled-60.json')!=read_json(DEV/'preparation-status.json')['candidate_manifest_sha256']:raise ValueError('Reconciled exact selection identity changed')
    live=read_json(c.reconcile.LIBRARY/'library-first-status.json');known={x['source_sha256'] for x in live['sources']}
    if any(r['sha256'] in known for r in rows):raise ValueError('A selected source has subsequently entered the library; reconcile before launch')
    old=read_json(PARENT/'state.json')
    if old['status']!=c.TERMINAL:raise ValueError('Historical completion is not finished')
    run=ROOT/'runs'/('library-night-day-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));run.mkdir()
    s={k:copy.deepcopy(old[k]) for k in ('chapter_contract','timing_policy','execution_limits','concurrency_policy','compiler_environment','runtime_image','remote_models')}
    s.update(status='prepared',stage='authorized finite60 local-only preparation',calls=[],tasks=[],versions={},current_versions={},source_units={},derived_inputs={},documents={},connection_failures=0,first_dispatch=None,active_stage=1,stages={'1':{}},launches=[],disable_dependency_downloads=True,suite_protocol='source-image-review-v1',production_stage={'task_ids':[]},resource_phase='not_started',remote='/home/mdi/projects/pdf-to-latex-comparisons/'+run.name,extraction={'mineru_pro':{'status':'prepared','pages':{}}},models_downloaded=True,inputs_prepared=False,ready_baseline=live['counts']['ready'],ready_added_offline=0)
    p={'status':'frozen','workflow':'library-first-v1','night_day':{'waves':[30,60],'checkpoints':[5,30,60],'isolated_failures':'record exact gaps and continue','shared_failures':'pause safely','attempt_allowance':'One conversion and conditional own-draft image review per derived coherent unit; exact units sealed per wave before any GLM reservation; no inference retry, no recursive split','numerical_cell_checks':'Explicit pixel-based signs/exponents/decimal/row-column review; no exhaustive independent verification claim'},'settings':dict(c.policy.DEFAULTS),'documents':[],'workloads':{'mineru_pro':[]},'reuse':[],'paid_enabled':False,'spend_cap_usd':'0','paid_approval':{'enabled':False,'new_spend_cap_usd':'0','reason':'No allocation granted for these60 new sources; historical$7 remains separate and unchanged'},'accept_exact_fragments':True,'no_recursive_splitting_or_retry':True,'collection_membership':'Explicit next60 of established193 PROCESS_PDF master queue;90prior ready sources preserved','parent_run':str(PARENT),'selection_sha256':sha(DEV/'reconciled-60.json'),'runtime_image':s['runtime_image'],'remote_models':s['remote_models'],'runtime_contract':{k:s.get(k) for k in c.RUNTIME_FIELDS}}
    copy_verified(DEV/'reconciled-60.json',run/'authorization/selected-60.json')
    copy_verified(PARENT/'effort-support-offline.json',run/'effort-support-offline.json')
    oldprogress=read_json(PARENT/'progress.json');atomic_json(run/'historical/paid-accounting.json',{'read_only_at':c.runtime.now(),'parent':str(PARENT),'progress_sha256':sha(PARENT/'progress.json'),'accounting':oldprogress['paid_accounting'],'usable_for_this_run':False,'reason':'Old allocation sources/consumed costs/uncertain holds remain unchanged'})
    import fitz
    folders=set()
    for row in rows:
        sid=row['source_id'];original=Path(row['path'])
        if sha(original)!=row['sha256']:raise ValueError('Source hash changed')
        folder=slug(row['filename'][:-4],100)+'--'+row['sha256'][:16]
        if folder.casefold() in folders:raise ValueError('Portable folder collision')
        folders.add(folder.casefold())
        meta={'source_id':sid,'folder':folder,'sha256':row['sha256'],'page_count':row['pages'],'title':row['title'],'document_type':row['document_type'],'completeness':'Complete supplied paper; coverage verified separately','originals':[{'path':str(original),'name':row['filename'],'sha256':row['sha256'],'bytes':original.stat().st_size}],'archive_member':row['archive_member'],'queue_id':row['queue_id'],'queue_order':row['order'],'intake_source_id':row['intake_source_id'],'bibliographic_provenance':{k:row.get(k) for k in ('authors','source','urls','source_check','reason')}}
        doc={'source_id':sid,'filename':row['filename'],'sha256':row['sha256'],'original':str(original),'physical_pages':list(range(1,row['pages']+1)),'pages':[],'library_document':meta,'role':'new','blank_pages':{},'original_page_count':row['pages']}
        with fitz.open(original) as pdf:
            if len(pdf)!=row['pages']:raise ValueError('Actual page count changed')
            native=[]
            for n in doc['physical_pages']:
                image=run/'sources'/sid/f'page-{n:03}.png';image.parent.mkdir(parents=True,exist_ok=True)
                pdf[n-1].get_pixmap(matrix=fitz.Matrix(200/72,200/72)).save(image)
                rel=str(image.relative_to(run));doc['pages'].append({'physical_pdf_page':n,'path':rel,'image':rel,'sha256':sha(image),'dimensions':list(struct.unpack('>II',image.read_bytes()[16:24]))});native.append({'physical_pdf_page':n,'text':pdf[n-1].get_text()})
            atomic_json(run/'sources'/sid/'secondary-assessment.json',c.requests.secondary_assessment(native))
        p['documents'].append(doc);p['workloads']['mineru_pro'] += [[sid,n] for n in doc['physical_pages']]
        s['documents'][sid]={'filename':row['filename'],'status':'pending_extraction','source_sha256':row['sha256'],'original':str(original),'units':[],'historical_selection':None,'reused_units':[],'role':'new'}
        print(f'Prepared {row["order"]}/60: {row["filename"]}',flush=True)
    atomic_json(run/'plan.json',p);validate_plan(p);c.policy.validate_extraction_plan(p,run)
    atomic_json(run/'arms/mineru_pro/state.json',s['extraction']['mineru_pro'])
    for path,digest in c.base.code_binding().items():copy_verified(ROOT/path,run/'implementation'/path,digest)
    for f in (ROOT/'tests').glob('*.py'):copy_verified(f,run/'implementation/tests'/f.name)
    for f in ['AGENTS.md','docs/PROJECT-STATE.md','docs/LIBRARY-FIRST.md']:copy_verified(ROOT/f,run/'implementation'/f)
    frozen={str(f):sha(f) for directory in ('sources','authorization','historical') for f in (run/directory).rglob('*') if f.is_file()}
    frozen.update({d['original']:d['sha256'] for d in p['documents']});frozen[str(run/'effort-support-offline.json')]=sha(run/'effort-support-offline.json')
    atomic_json(run/'binding.json',{'code':c.base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':frozen})
    c.save(run,s);c.verify(run)
    atomic_json(POINTER,{'run':str(run),'status':'PREPARED_AUTHORIZED_TO_LAUNCH','papers':60,'pages':704});atomic_json(c.POINTER,{'run':str(run),'status':'PREPARED_AUTHORIZED_TO_LAUNCH'})
    print(run);return run
if __name__=='__main__':prepare()
