#!/usr/bin/env python3
"""Explicit offline triage/reconciliation and linked overnight preparation."""
import argparse,copy,difflib,re,shutil,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha,writer_lock,fingerprint
from probe.experiment import seal,verify_seal,InputGuard
from probe import library_first as policy,source_library as library,author_source,book_completion,kimi_escalation as kimi
from scripts import library_pipeline as pipeline,library_reconcile as old
DEV=ROOT/'results/library-overnight-20261107';PARENT=ROOT/'runs/library-first-20261107T212314Z-prelaunch-115000';FOCUSED=ROOT/'runs/focused-recovery-20261103T223632Z-d9c8f9'
NEW=['original-ee9d62e0261b2dcc','original-c6fbf9bf1bbc7325','original-af03317e4e74c832','original-1e05399704af3696']
EXCLUDE=['original-d881fa9f7a6483b3','original-80378207f6629262']

def exact_replace(text,old,new):
    if text.count(old)!=1:raise ValueError('Saved repair anchor not unique')
    return text.replace(old,new)

def saved_repairs(sid,text):
    notes=[]
    if sid=='original-f24e3131438ab5c0':
        text=exact_replace(text,'\\end{aligned}\n\\tag{C.10}\n\\end{aligned}','\\end{aligned}\n\\tag{C.10}')
        notes.append('Removed duplicate unmatched end{aligned} around C.10; all mathematical tokens/numbering retained. Original p28 inspected.')
    if sid=='original-ead9d04e4c78147d' and 'weekly frequency $(ie $h' in text:
        text=exact_replace(text,'weekly frequency $(ie $h','weekly frequency (ie $h');notes.append('Removed stray opening dollar before prose (ie in Figure3 caption; retained h=1/52 and all math tokens.')
    if sid=='original-1fc68aa26e4deb3b':
        a=text.index(r'\begin{tikzpicture}');b=text.index(r'\end{tikzpicture}',a)+len(r'\end{tikzpicture}')
        text=text[:a]+r'\includegraphics[width=.6\linewidth]{assets/breaking-barriers-original-figure-4.png}'+text[b:]
        notes.append('Replaced the labelled GLM recreation of Figure4 with the already saved original crop; original physical p6 inspected; caption preserved. Recreation remains in prior.tex.')
    if sid=='original-496de5aa992285e2':
        # Restore the printed conditional numerator, not an independent claimed
        # mathematical derivation; retain the previous proposal in the raw version.
        anchor=r'\frac{\rho\alpha + X}{\sqrt{1-\rho^2}}'
        if text.count(anchor)==1:
            text=exact_replace(text,anchor,r'\frac{\alpha + \rho X}{\sqrt{1-\rho^2}}');notes.append('Source-faithful restoration of first numerator in equation13 from original p9. Previous model correction and its derivation are superseded, not certified; epsilon/independent-noise distinction remains a review note.')
    if notes:
        text=text.replace(r'\end{document}', '\n\\section*{Source reconciliation record}\n'+ '\n\n'.join(n.replace('_',r'\_').replace('{',r'\{').replace('}',r'\}') for n in notes)+'\nEarlier model/editorial assertions about these particular changes are historical and superseded by this record; mathematical verification beyond the stated source check is not claimed.\n'+r'\end{document}')
    return text,notes

def reconcile():
    before=read_json(DEV/'before-library.json');docs={d['source_id']:d for d in read_json(old.PARENT/'collection.json')['documents']};history=read_json(old.PARENT/'state.json');focused=read_json(FOCUSED/'state.json');audit=read_json(ROOT/'results/source-availability-audit-20261104T194212Z/documents.json');actions=[];updates=[]
    for row in read_json(DEV/'triage-evidence.json'):
        sid=row['source_id'];doc=docs[sid];origin=Path(row['generation']);scope_checks=[]
        evidence=next((r for r in audit if r['sha256']==doc['sha256']),None)
        own_ids=sorted(set(re.findall(r'Electronic copy available at: https://ssrn.com/abstract=(\d+)', '\n'.join(row['ssrn_mentions']))))
        entry={'source_id':sid,'sha256':doc['sha256'],'filename':row['filename'],'type':row['type'],'pages':row['pages'],'priority':0 if own_ids else 1,
            'provenance':{'ssrn_document_ids':own_ids,'ssrn_provenance':'confirmed printed document footer' if own_ids else 'not established; bibliography mentions not treated as identity','ssrn_only':'not established; saved availability searches incomplete','audit_status':evidence['status'] if evidence else 'outside master-archive audit','author_source_available':False},
            'previous_generation':str(origin),'historical_calls':[{'id':c['id'],'task':c['parent'],'status':c['status']} for c in history['calls'] if c['parent'].startswith(sid)],'action':'reuse_saved_complete','missing_scope':[]}
        if sid in EXCLUDE:
            entry.update(action='excluded_non_paper',reason='Course notes/chapter extract or presentation; outside overnight paper inference');actions.append(entry);continue
        if sid in NEW:
            entry.update(action='missing_conversion',priority=2 if sid in NEW[1:3] else 1 if sid==NEW[0] else 3,next_stage='MinerU Pro then coherent High conversion/High original-image review')
            if sid==NEW[0]:
                missing=history['source_units'][sid+'-part-002']['section'];entry.update(missing_scope=[{k:missing[k] for k in ('first','last','blocks','physical_pages','target_text_sha256')}],new_pages=missing['physical_pages'],reuse_units=[sid+'-part-001'],next_stage='Reuse complete native extraction for exact missing blocks; coherent High conversion/High image review; no upstream replay')
            else:entry.update(new_pages=list(range(1,doc['page_count']+1)),reuse_units=[],missing_scope=[{'physical_pages':list(range(1,doc['page_count']+1)),'reason':'No complete usable conversion exists'}])
            actions.append(entry);continue
        out=DEV/'promotions'/sid;out.mkdir(parents=True,exist_ok=True)
        if (out/'manifest.json').exists():
            status=policy.validate_publication(out,doc);updates.append({'source_id':sid,'folder':doc['folder'],'prepared':str(out),'generation':'overnight-reconciled-'+sha(out/'manifest.json')[:16],'previous_pointer':next(r['selected_generation'] for r in before['sources'] if r['source_id']==sid)});entry['reconciliation']=str(out);actions.append(entry);continue
        # Default selected original parts. Later complete source-unit groups replace
        # them only where exact original block ownership is demonstrably complete.
        units=[]
        if sid in ('original-ead9d04e4c78147d','original-ba2b65da21f13b69'):
            prefix='mean-bias-' if sid=='original-ead9d04e4c78147d' else 'alternatives-'
            for key,label in focused['current_versions'].items():
                if key.startswith(prefix):units.append((FOCUSED,key,focused['versions'][key][label],focused['source_units'][key]['section']))
            assigned=[b for _,_,_,u in units for b in u['blocks']];expected=history['source_units'][sid+'-part-001']['section']['blocks']
            if len(assigned)!=len(set(assigned)) or assigned!=expected:raise ValueError('Recovery scope gap/duplication or order change '+sid)
            scope_checks.append({'type':'exact_block_partition','blocks':len(expected),'units':len(units),'boundary_pages_shared_content_not_duplicated':True})
        else:
            coverage=read_json(origin/'coverage.json')
            for part in coverage['parts']:
                if not part.get('selected'):raise ValueError('Missing selected part needs queue admission '+sid)
                key=part['unit'];v=history['versions'][key][part['selected']];units.append((old.PARENT,key,v,history['source_units'][key]['section']))
        selected=[];notes=[]
        for run,key,v,section in units:
            raw=run/v['path']
            if sha(raw)!=v['sha256']:raise ValueError('Saved draft identity changed')
            text=raw.read_text();revised,edits=saved_repairs(sid,text);notes+=edits;target=out/'parts'/key;target.mkdir(parents=True,exist_ok=True)
            (target/'document.tex').write_text(revised);library.copy_verified(raw,target/'prior.tex',v['sha256']);(target/'changes.diff').write_text(''.join(difflib.unified_diff(text.splitlines(True),revised.splitlines(True),fromfile='prior.tex',tofile='document.tex')))
            from scripts import book_completion as books
            assets=books.asset_map(run,sid,text)
            if sid=='original-1fc68aa26e4deb3b':
                path=next(p for p in FOCUSED.rglob('breaking-barriers-original-figure-4.png') if p.is_file());expected=focused['source_units']['breaking-figure']['section']['source_image_addition']['sha256']
                if sha(path)!=expected:raise ValueError('Saved original crop changed')
                assets['assets/breaking-barriers-original-figure-4.png']=path
            for name,path in assets.items():library.copy_verified(path,target/name)
            check=author_source.generated_content(revised,{name:target/name for name in assets})
            if not check['usable']:raise ValueError('Substantive saved defect unresolved '+sid+': '+str(check))
            # A flagged heading is not cleared generically. Store inspected evidence
            # and the exact source/draft fragment that accounts for this candidate.
            atomic_json(target/'source-scope.json',section);atomic_json(target/'version-provenance.json',{'run':str(run),'key':key,'version':v,'content_checks':check,'repairs':edits})
            selected.append({'path':str((target/'document.tex').relative_to(out)),'sha256':sha(target/'document.tex')})
            for p in (run/'accuracy'/key).rglob('*'):
                if p.is_file() and p.suffix in ('.json','.diff','.md'):library.copy_verified(p,target/'accuracy'/p.relative_to(run/'accuracy'/key))
        waivers={
          'original-1fc68aa26e4deb3b':'Flagged headings1/A/3/4 are retained figure/table captions. Original Figure4 crop replaces the model recreation. Substantive material after references on pp5-6 is retained.',
          'original-496de5aa992285e2':'References are all11 bibitems in thebibliography, matching original p9; appendix pp8-9 and all3 figures pp10-11 retained. Source-faithful numerator restored; prior claim explicitly superseded.',
          'original-101b96b08795547f':'Abstract is begin{abstract};13 references are bibitems. Original title/abstract and reference-list endpoints inspected.',
          'original-efd2b1bf99ca1e40':'Abstract environment and21 bibliography entries retained; source p1 and reference-list endpoints match; no missing substantive heading.',
          'original-a00db1c82bd63717':'All28 reference entries retained in thebibliography; source reference-list endpoints match. Proof appendix retained.',
          'original-b1b832aa3aea4577':'Abstract retained in begin{abstract}, confirmed against source p1. Seven tables and appendices A/B remain.',
          'original-18a12603fad0d398':'Original p7 Theorem9(a) valid-cdf line is a list item, not a heading; retained in itemize. Square proof marker is not an equation number.',
          'original-c1c03f008f4ec995':'Title retained in centered cover/frontmatter, matching original pp1-2, not a section heading.',
          'original-16af71ccd52a5072':'Original p18 convergence-in-probability statement is a bullet; retained as itemize bullet, not missing heading.',
          'original-26781ea8225bd6e9':'Section2.3 heading plus introductory diffusion paragraph retained separately. Original p27 equations4.2.4a/b retained (combined label); d-lambda is a differential, not an equation label. Existing barrier-focused review remains a supplement, not whole-paper verification.'}
        assessment={'source_id':sid,'original_sha256':doc['sha256'],'historical_coverage_flags':row['coverage_flags'],'specific_disposition':waivers.get(sid,'Exact source-unit partition and substantive dependency/structure checks; prior model findings remain unverified'),'scope_checks':scope_checks,'saved_repairs':notes,'limitation':'Targeted content/structural checks only, not exhaustive source-checked mathematical accuracy'}
        atomic_json(out/'reconciliation.json',assessment);library.copy_verified(origin/'coverage.json',out/'historical-coverage.json')
        for p in (DEV/'source-checks').glob(sid+'-*.png'):library.copy_verified(p,out/'source-checks'/p.name)
        record={'source_id':sid,'source_sha256':doc['sha256'],'status':'ready_working_source','content_status':'complete_assigned_source','source_kind':'saved_conversion','selected_tex':selected,'conversion':'reused_complete_saved_content','compilation':'not_requested','model_review':{'status':'saved_review_history_retained','full_source_verified':False,'unresolved_mathematical_findings':'See retained notes and prior versions; content readiness does not endorse them'},'coverage':assessment,'outstanding_scopes':[],'source_verification':assessment['limitation']}
        atomic_json(out/'library-status.json',record);(out/'README.md').write_text('# '+row['filename']+'\n\n[Original human reading PDF](../../original.pdf). Complete substantive saved text is under parts/. Compilation not requested. Exact drafts, source partitions, repairs, old flags and targeted dispositions are retained. Mathematics remains independently unverified except specifically stated source readings; previous model corrections are not blanket approved.\n');seal(out);policy.validate_publication(out,doc)
        updates.append({'source_id':sid,'folder':doc['folder'],'prepared':str(out),'generation':'overnight-reconciled-'+sha(out/'manifest.json')[:16],'previous_pointer':next(r['selected_generation'] for r in before['sources'] if r['source_id']==sid)})
        entry['reconciliation']=str(out);entry['usable_saved_scope']='Complete original source partition; scoped review coverage remains explicit';actions.append(entry)
    atomic_json(DEV/'actions.json',actions);atomic_json(DEV/'promotions.json',updates);print({'promotions':len(updates),'queued':[a['filename'] for a in actions if a['action']=='missing_conversion'],'non_papers_excluded':[a['filename'] for a in actions if a['action']=='excluded_non_paper']})


def publish_reconciliation():
    before=read_json(DEV/'before-library.json');index=copy.deepcopy(before);docs={d['source_id']:d for d in read_json(old.PARENT/'collection.json')['documents']}
    with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(old.LIBRARY):
        live=read_json(old.LIBRARY/'library-first-status.json')
        if live!=before and live.get('overnight_reconciliation')!=str(DEV):raise ValueError('Library changed independently')
        for u in read_json(DEV/'promotions.json'):
            d=docs[u['source_id']];folder=old.LIBRARY/u['folder'];prepared=Path(u['prepared']);record=policy.validate_publication(prepared,d);pointer=read_json(folder/'current.json');name='generations/'+u['generation']
            if pointer!=u['previous_pointer'] and pointer.get('generation')!=name:raise ValueError('Source selection changed')
            history=folder/'selection-history'/('before-'+u['generation']+'.json')
            if not history.exists():atomic_json(history,{'current':pointer,'readme':(folder/'README.md').read_text()})
            metadata=read_json(folder/'source.json');managed=(folder/'README.md').read_text() in (library.source_readme(metadata,pointer),library.source_readme(metadata,u['previous_pointer']))
            selected=library.publish_generation(folder,u['generation'],prepared,'ready_working_source')
            if managed:library.write_source_readme(folder,metadata)
            row=next(r for r in index['sources'] if r['source_id']==u['source_id'])
            row.update(status='ready',selected_generation=selected,content_status=record['content_status'],compilation='not_requested',model_review=record['model_review'],coverage_flags=record['coverage'],reason='Saved full content reconciled; historical targeted false alarms and structural faults accounted separately')
        index['counts']={k:sum(r['status']==k for r in index['sources']) for k in ('ready','partial','deferred')};index['overnight_reconciliation']=str(DEV)
        atomic_json(old.LIBRARY/'library-first-status.json',index);atomic_json(DEV/'after-library.json',index)
        lines=['# Overnight content reconciliation','',str(index['counts'])+' across63 PDF identities. Thirteen added useful papers from saved material, zero inference. Mathematical confidence remains separate.','', '| Source | Status | Selected |','|---|---|---|']
        for r in index['sources']:
            selected=r.get('selected_generation');link=r['folder']+'/'+selected['generation']+'/README.md' if selected else r['folder']+'/README.md';lines.append('| '+r['filename']+' | '+r['status']+' | [source]('+link+') |')
        (old.LIBRARY/'LIBRARY-OVERNIGHT-INDEX-20261107.md').write_text('\n'.join(lines)+'\n')
        for name in ('LIBRARY-FIRST-INDEX.md','LIBRARY-HANDOFF.md'):
            link='[Overnight reconciliation:56 useful,6 partial,1 excluded](LIBRARY-OVERNIGHT-INDEX-20261107.md)'
            p=old.LIBRARY/name
            if link not in p.read_text():
                with p.open('a') as f:f.write('\n'+link+'. All earlier tables are historical. Four missing-only research-paper scopes are prepared, not launched; one combined $7 recovery cap, compilation off. Matrix norms/Kai lecture material stays out of overnight inference.\n')
    print(index['counts'])

def prepare_queue():
    """Create a new linked plan from the verified zero-call parent; never reseal it."""
    if not all(pipeline.base.books.speed.idle(p) for p in (ROOT,ROOT/'runs',PARENT)):raise ValueError('Writer active')
    previous=None
    registry=DEV/'new-preparation.json'
    if registry.exists():
        previous=Path(read_json(registry)['run']);previous_state=read_json(previous/'state.json')
        if previous_state['calls'] or previous_state.get('launches') or (previous/'billing.json').exists() or (previous/'fallback-budget/ledger.json').exists():raise ValueError('This overnight approval has started/consumed allowances; resume its selected run, never allocate another $7')
    if previous:
        cached_binding=read_json(previous/'binding.json')
        if sha(previous/'plan.json')!=cached_binding['plan_sha256']:raise ValueError('Earlier preparation changed')
        InputGuard(cached_binding['files']).check()
    ps=read_json(PARENT/'state.json');pb=read_json(PARENT/'binding.json')
    if ps['status']!='prepared' or ps['calls'] or ps.get('launches') or ps['tasks'] or ps['inputs_prepared']:raise ValueError('Parent has started; no replacement in place')
    if sha(PARENT/'plan.json')!=pb['plan_sha256']:raise ValueError('Parent plan changed')
    InputGuard(pb['files']).check()
    run=ROOT/'runs'/('library-overnight-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));run.mkdir()
    state=copy.deepcopy(ps);state.update(documents={},source_units={},versions={},current_versions={},derived_inputs={},extraction={'mineru_pro':{'status':'prepared','pages':{}}},tasks=[],calls=[],inputs_prepared=False,ready_baseline=43,ready_added_offline=13,stage='prepared productive missing-only queue; operator launch required',remote='/home/mdi/projects/pdf-to-latex-comparisons/'+run.name)
    state.pop('inspection',None)
    oldplan=read_json(PARENT/'plan.json');plan=copy.deepcopy(oldplan);plan.update(documents=[],workloads={'mineru_pro':[]},reuse=[],overnight=True,paid_enabled=True,spend_cap_usd='7.00',continuation_parent_preparation=str(PARENT),objective='Finite missing-only productive paper queue; original PDF is reading copy; one combined $7 recovery cap')
    plan['settings'].update(compile_pdf=False,paid_enabled=True,new_spend_budget_usd='7.00')
    docs={d['source_id']:d for d in read_json(old.PARENT/'collection.json')['documents']};live={d['source_id']:d for d in read_json(old.LIBRARY/'library-first-status.json')['sources']};hist=read_json(old.PARENT/'state.json')
    actions=sorted((a for a in read_json(DEV/'actions.json') if a['action']=='missing_conversion'),key=lambda a:(a['priority'],len(a['new_pages'])))
    import fitz,struct
    for action in actions:
        sid=action['source_id'];d=docs[sid]
        if live[sid]['status']=='ready':continue
        folder=old.LIBRARY/d['folder'];pointer=read_json(folder/'current.json') if (folder/'current.json').exists() else None
        policy.admit_missing_conversion(live[sid],pointer)
        source=Path(d['originals'][0]['path'])
        if sha(source)!=d['sha256']:raise ValueError('Original identity changed')
        record={'source_id':sid,'filename':action['filename'],'sha256':d['sha256'],'original':str(source),'physical_pages':action['new_pages'],'pages':[],'library_document':d,'action':action,'original_page_count':d['page_count']}
        state['documents'][sid]={'filename':action['filename'],'source_sha256':d['sha256'],'original':str(source),'units':[],'historical_selection':pointer,'status':'pending_extraction','reused_units':[]}
        with fitz.open(source) as pdf:
            prior=next((x for x in oldplan['documents'] if x['source_id']==sid),None);cache=PARENT
            if previous:
                cached=next((x for x in read_json(previous/'plan.json')['documents'] if x['source_id']==sid and x['sha256']==d['sha256']),None)
                if cached:prior=cached;cache=previous
            if prior:library.copy_verified(cache/'sources'/sid/'secondary-assessment.json',run/'sources'/sid/'secondary-assessment.json')
            else:atomic_json(run/'sources'/sid/'secondary-assessment.json',pipeline.requests.secondary_assessment([{'physical_pdf_page':n+1,'text':p.get_text()} for n,p in enumerate(pdf)]))
            for n in action['new_pages']:
                path=run/'sources'/sid/f'page-{n:03}.png';path.parent.mkdir(parents=True,exist_ok=True)
                if prior:
                    page=next(x for x in prior['pages'] if x['physical_pdf_page']==n);library.copy_verified(cache/page['path'],path,page['sha256'])
                else:pdf[n-1].get_pixmap(matrix=fitz.Matrix(200/72,200/72)).save(path)
                record['pages'].append({'physical_pdf_page':n,'path':str(path.relative_to(run)),'image':str(path.relative_to(run)),'sha256':sha(path),'dimensions':list(struct.unpack('>II',path.read_bytes()[16:24]))})
        if sid==NEW[0]:
            # Exact historical source block ownership, not a coarse page split.
            native=read_json(old.PARENT/'inputs'/sid/'native.json');blocks={b['id']:b for b in native['blocks']};missing=hist['source_units'][sid+'-part-002']['section'];kept=hist['source_units'][sid+'-part-001']['section']
            if set(missing['blocks'])&set(kept['blocks']):raise ValueError('Saved scope ownership overlaps')
            from scripts import book_completion as books
            assets=books.asset_map(old.PARENT,sid,kept['text']+'\n'+missing['text'])
            copied={}
            for name,asset in assets.items():library.copy_verified(asset,run/'reused-assets'/sid/name);copied[name]=str(run/'reused-assets'/sid/name)
            fixed={'blocks':[blocks[k] for k in missing['blocks']],'assets':copied,'source_sha256':d['sha256'],'parent_run':str(old.PARENT),'parent_native_sha256':sha(old.PARENT/'inputs'/sid/'native.json'),'reason':'Complete saved extraction reused for exactly missing assigned blocks; historical Pro generation not invented'}
            path=run/'fixed-scopes'/f'{sid}.json';atomic_json(path,fixed);record.update(fixed_native=str(path.relative_to(run)),fixed_native_sha256=sha(path),earlier_context=kept['text'],earlier_cloud_context='\n\n'.join(blocks[b]['tex'] for b in kept['blocks'][:6]+kept['blocks'][-12:]))
            key=sid+'-part-001';v=hist['versions'][key][hist['current_versions'][key]];raw=old.PARENT/v['path'];target=run/'versions'/key/'saved/document.tex';library.copy_verified(raw,target,v['sha256'])
            u={'source_key':sid,'title':action['filename']+' — reused original part1','physical_pages':kept['physical_pages'],'blocks':kept['blocks'],'native_blocks':[blocks[k] for k in kept['blocks']],'text':kept['text'],'context':'','secondary':'','assets':copied,
               'saved_coverage_adjudication':{'draft_sha256':v['sha256'],'reason':'Wilmott/TECHNICAL ARTICLE are page furniture; TABLE3.2 is retained in a literal caption and tabular. Saved source ownership covers first332 blocks; flags are not cleared for any other draft.'}}
            atomic_json(run/'inputs'/key/'unit.json',u);state['source_units'][key]=u;state['derived_inputs']['inputs/'+key+'/unit.json']=sha(run/'inputs'/key/'unit.json')
            saved={'path':str(target.relative_to(run)),'sha256':sha(target),'compilation':{'status':'not_requested','historical':v.get('compilation')},'content_check':pipeline.content_check(run,dict(state,source_units={key:u}),{'key':key},raw.read_text()),'provenance':{'run':str(old.PARENT),'version':v}}
            if not saved['content_check']['usable']:raise ValueError('Saved Smile part has unresolved content damage')
            state['versions'][key]={'saved':saved};state['current_versions'][key]='saved';state['documents'][sid]['units']=[key];state['documents'][sid]['reused_units']=[key]
            plan['reuse'].append({'source':sid,'unit':key,'sha256':v['sha256'],'scope':kept['blocks'],'historical_reviews_preserved':True})
        else:plan['workloads']['mineru_pro'] += [[sid,n] for n in action['new_pages']]
        plan['documents'].append(record)
    if not plan['documents']:raise ValueError('Nothing missing; no productive queue required')
    library.copy_verified(PARENT/'effort-support-offline.json',run/'effort-support-offline.json')
    if state.get('compiler_environment'):
        source=PARENT/state['compiler_environment']['path']
        if source.exists():shutil.copytree(source,run/state['compiler_environment']['path'])
    public=read_json(DEV/'kimi-public/metadata.json');config=kimi.profile(public,'7.00',tasks=1);config.update(paid_limits=None,no_generation_deadline=True,readiness='Non-generating live route/allowance checks; earlier successful K3 protocol retained; no paid control',qualification='Prior successful K3 route protocol reused; current metadata verified; private live allowance checked at operator dispatch')
    prior=kimi.history_snapshot(ROOT,exclude=[run]);atomic_json(run/'prior-billing.json',prior);plan['prior_billing']={'path':str(run/'prior-billing.json'),'sha256':sha(run/'prior-billing.json')};plan['kimi_config']=config
    a={'explicitly_approved':True,'new_spend_cap_usd':'7.00','combined_providers':['mathpix','kimi'],'ledger_root':str(run/'fallback-budget'),'sources':{d['source_id']:{'sha256':d['sha256'],'physical_pages':d['physical_pages']} for d in plan['documents']},'provider_metadata_current':True,'mathpix_price_per_page_usd':'0.005','scope_registration':'Exact derived unit/page/draft hashes must be verified and registered without changing this approval','no_per_provider_allocation':True}
    plan['paid_approval']=a;state['paid_approval_sha256']=fingerprint(a);plan['approval_registry']=str(DEV/'new-preparation.json');plan['runtime_contract']={k:state.get(k) for k in pipeline.RUNTIME_FIELDS}
    atomic_json(run/'candidate-actions.json',read_json(DEV/'actions.json'));library.copy_verified(DEV/'kimi-public/metadata.json',run/'public-metadata.json')
    atomic_json(run/'preparation-link.json',{'parent':str(PARENT),'parent_plan_sha256':sha(PARENT/'plan.json'),'parent_binding_sha256':sha(PARENT/'binding.json'),'parent_calls':0,'history_preserved':True,'scope_change':'13 complete saved papers reconciled; four explicit missing-only paper assignments; $7 one combined new-spend cap; no inference launched'})
    atomic_json(run/'plan.json',plan);policy.validate_extraction_plan(plan,run)
    frozen={str(p):sha(p) for sub in ('sources','fixed-scopes','reused-assets') for p in (run/sub).rglob('*') if p.is_file()};frozen.update({d['original']:d['sha256'] for d in plan['documents']})
    for name in ('effort-support-offline.json','candidate-actions.json','public-metadata.json','preparation-link.json','prior-billing.json'):frozen[str(run/name)]=sha(run/name)
    atomic_json(run/'binding.json',{'code':pipeline.base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':frozen,'config':config,'prior_billing':plan['prior_billing']})
    pipeline.save(run,state);atomic_json(DEV/'new-preparation.json',{'run':str(run),'status':'PREPARED_NOT_RUNNING'});pipeline.verify(run);print(run);return run

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['reconcile','publish','prepare']);a=p.parse_args()
    {'reconcile':reconcile,'publish':publish_reconciliation,'prepare':prepare_queue}[a.action]()
