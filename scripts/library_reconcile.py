#!/usr/bin/env python3
"""Reconcile saved sources and publish manifest-backed generations; no inference."""
import argparse,copy,csv,io,json,shutil,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha,fingerprint,files_manifest,writer_lock
from probe.experiment import seal,verify_seal
from probe import source_library as library,library_first as policy,book_completion
from scripts import prepare_library_repairs as repairs
LIBRARY=Path('/home/mdi/llm-wiki/sources')
PARENT=ROOT/'runs/originals-batch-20261101T212602Z-ab2d41'
FOLLOW=ROOT/'runs/extraction-followup-20261105T223237Z-lifecycle'
IMAGE=ROOT/'runs/glm-image-review-20261106T133752Z-stages'
RECOVERY=ROOT/'runs/image-review-recovery-20261106T215705Z'
DEV=ROOT/'results/library-first-development-20261107'

def verify_old_delivery(folder,doc):
    verify_seal(folder);coverage=read_json(folder/'coverage.json')
    if coverage['source_sha256']!=doc['sha256']:raise ValueError('Saved generation source identity changed')
    for part in coverage['parts']:
        if not part.get('selected'):continue
        tex=folder/'parts'/part['unit']/'document.tex'
        if sha(tex)!=part['sha256']:raise ValueError('Published TeX differs from selected version')
        for ref in book_completion.image_references(tex.read_text()):
            if not (tex.parent/ref).is_file():raise ValueError('Published asset absent: '+ref)
    if coverage.get('compilation')=='passed' and not (folder/'reading.pdf').is_file():raise ValueError('Recorded passing delivery has no reading PDF')
    return coverage

def experiment_inventory():
    """Keep partial successful experiments visible without mislabelling them whole papers."""
    output=[]
    for pointer in ['focused-recovery-current.json','extraction-comparison-current.json','extraction-followup-current.json','kimi-current.json']:
        path=ROOT/'results'/pointer
        if not path.exists():continue
        run=Path(read_json(path)['run']);s=read_json(run/'state.json')
        for key,label in s.get('current_versions',{}).items():
            v=s['versions'][key][label];p=run/v['path']
            if not p.is_file() or sha(p)!=v['sha256']:raise ValueError('Experimental selected output changed')
            unit=s.get('source_units',{}).get(key,{});source=unit.get('source_key',key)
            if source not in s.get('documents',{}):source=next((sid for sid in s.get('documents',{}) if key.startswith(sid)),source)
            output.append({'run':str(run),'unit':key,'source_key':source,'selected':label,'tex':str(p),'sha256':v['sha256'],'compilation':v.get('compilation',{}).get('status'),'scope':unit.get('section',{}).get('title'),'physical_pages':unit.get('section',{}).get('physical_pages'),'adoption':'Current saved scope only; no assumption this represents a whole paper'})
    return output

def new_generation(out,source,doc):
    if (out/'manifest.json').exists():return policy.validate_publication(out,doc)
    out.mkdir(parents=True,exist_ok=True)
    origin=DEV/'saved-repairs'/source if source in ['cf','spectral'] else IMAGE/'repairs'/doc['source_id']
    build=read_json(origin/'build/compilation.json')
    if build['status']!='passed':raise ValueError('Corrected edition build failed; do not promote')
    for name in ['master.tex','reading.pdf']:
        library.copy_verified(origin/name,out/name)
    for sub in ['parts','assets']:
        for p in (origin/sub).rglob('*'):
            if p.is_file():library.copy_verified(p,out/sub/p.relative_to(origin/sub))
    for p in origin.glob('*.json'):library.copy_verified(p,out/'accuracy'/p.name)
    if (origin/'changes.diff').exists():library.copy_verified(origin/'changes.diff',out/'accuracy/changes.diff')
    library.copy_verified(origin/'build/compilation.json',out/'build-diagnostics/compilation.json')
    library.copy_verified(origin/'build/attempt-1/console.log',out/'build-diagnostics/console.log')
    # Retain raw conversions and pre-correction selected text separately.
    for p in (RECOVERY/'baseline-editions'/source).glob('*.tex'):
        library.copy_verified(p,out/'prior-versions'/p.name)
    sid=doc['source_id'];fs=read_json(FOLLOW/'state.json');notes=[];tex=[]
    for key,label in fs['current_versions'].items():
        if not key.startswith(sid+'-whole-'):continue
        versions=fs['versions'][key]
        for vlabel,v in versions.items():
            if vlabel.startswith('convert-') and not vlabel.endswith('annotated'):
                if sha(FOLLOW/v['path'])!=v['sha256']:raise ValueError('Raw converter changed')
                library.copy_verified(FOLLOW/v['path'],out/'raw-transcription'/key/(vlabel+'.tex'))
                for ref in book_completion.image_references((FOLLOW/v['path']).read_text()):
                    source_asset=out/ref
                    if source_asset.is_file():library.copy_verified(source_asset,out/'raw-transcription'/key/ref)
        inp=FOLLOW/'inputs'/key
        for name in ['native.json','scope.json','scope-contract.json']:
            if (inp/name).exists():library.copy_verified(inp/name,out/'source-mapping'/key/name)
    reviewrun=read_json(RECOVERY/'state.json')
    for t in reviewrun['tasks']:
        if t['source_key']!=source or t['id'].startswith('control'):continue
        f=RECOVERY/'reviews'/t['id']/'findings.json'
        if f.exists():library.copy_verified(f,out/'review-history'/(t['id']+'.json'));notes+=read_json(f)['findings']
    review=policy.review_summary([t for t in reviewrun['tasks'] if t['source_key']==source and not t['id'].startswith('control')],notes)
    if source=='pvalues':review={'legacy_model_review':'completed','scope_attestation':'not recorded by legacy schema','pending_suggestions':[],'pending_suggestion_count':0,'independent_mathematical_verification':'sample checks only'}
    for p in (out/'parts').glob('*.tex'):tex.append({'path':str(p.relative_to(out)),'sha256':sha(p)})
    selectedrecord=read_json(origin/'provenance.json') if (origin/'provenance.json').exists() else {'parent':str(origin)}
    record={'source_id':sid,'source_sha256':doc['sha256'],'source_pages':doc['page_count'],'status':'ready_working_source',
        'content_status':'complete_assigned_source','coverage_basis':'Complete frozen Pro page/region and whole-paper part ownership; source-original figures preserved; no claim of full mathematical accuracy',
        'conversion':'complete_saved_drafts','model_review':review,'compilation':'passed','direct_source_checks':'Located CF/Spectral corrections and prior source checks only; historical failed Case19 Max remains failed',
        'selected_tex':tex,'selected_master':'master.tex','provenance':selectedrecord,'original':'../../original.pdf','pending_material_questions':'See accuracy/ and review-history/. Some historical proposals are superseded/rejected by current corrections, not silently deleted.'}
    atomic_json(out/'library-status.json',record)
    (out/'README.md').write_text('# '+doc['title']+'\n\nReady working source: [editable master](master.tex), [reading PDF](reading.pdf), [unchanged original](../../original.pdf).\n\n'
        'All assigned pages/parts are included. This is not independent whole-paper mathematical certification. Raw transcription, prior selected text, source mappings, current corrections, pending/superseded review proposals and build diagnostics remain separate.\n\n'
        '[Detailed status](library-status.json). Review failures and incomplete scope attestations remain visible even when compilation passes.\n')
    atomic_json(out/'extraction-provenance.json',{'run':str(FOLLOW),'source_sha256':doc['sha256'],'raw_pages':str(FOLLOW/'arms/mineru_pro/pages'),'model':'opendatalab/MinerU2.5-Pro-2605-1.2B','pinned_revision':'08aaea840498d49ce16247b6263196cf02814885','no_ocr_repeated':True})
    seal(out);return policy.validate_publication(out,doc)

def prepare(destination):
    dest=Path(destination);dest.mkdir(parents=True,exist_ok=True);manifest=read_json(PARENT/'collection.json');state=read_json(PARENT/'state.json');library.verify_originals(manifest)
    rows=[];updates=[];excluded=copy.deepcopy(state['deferred_sources']);excluded[policy.COOKING]={'reason':'user excluded: poor scan; do not process'}
    known={'cf':repairs.CF,'spectral':repairs.SP,'pvalues':'original-547334b059504dcb'}
    for doc in manifest['documents']:
        sid=doc['source_id'];folder=LIBRARY/doc['folder'];metadata=read_json(folder/'source.json')
        if metadata['sha256']!=doc['sha256'] or sha(folder/'original.pdf')!=doc['sha256']:raise ValueError('Existing library identity changed')
        pointer=read_json(folder/'current.json') if (folder/'current.json').exists() else None
        row={'source_id':sid,'filename':doc['originals'][0]['name'],'title':doc['title'],'type':doc['document_type'],'source_completeness':doc.get('completeness'),'pages':doc['page_count'],'folder':doc['folder'],'source_sha256':doc['sha256'],'selected_generation':pointer}
        if sid in excluded:row.update(status='deferred',reason=excluded[sid]['reason']);rows.append(row);continue
        if pointer and (folder/pointer['generation']/'library-status.json').exists():
            new=policy.validate_publication(folder/pointer['generation'],doc)
            coverage={'status':'delivered_working_edition' if new['status']=='ready_working_source' else 'delivered_with_gaps','conversion':'completed' if new['content_status']=='complete_assigned_source' else 'incomplete','model_review':new['model_review'],'compilation':new['compilation'],'possible_content_gaps':new['content_status']!='complete_assigned_source'}
        else:coverage=verify_old_delivery(folder/pointer['generation'],doc) if pointer else None
        row.update(status='ready' if coverage and coverage['status']=='delivered_working_edition' and coverage['conversion']=='completed' and coverage['compilation']=='passed' and not coverage['possible_content_gaps'] else 'partial',
          conversion=coverage.get('conversion') if coverage else 'missing',model_review=coverage.get('model_review') if coverage else 'missing',compilation=coverage.get('compilation') if coverage else 'missing',coverage_flags=coverage.get('possible_content_gaps') if coverage else True,source_verification='Not independently established; recorded checks retained')
        source=next((name for name,x in known.items() if sid==x),None)
        if source:
            generation=dest/'generations'/sid;record=new_generation(generation,source,doc);name='library-first-20261107-'+sha(generation/'manifest.json')[:16]
            updates.append({'document':doc,'prepared':str(generation),'generation':name,'previous_pointer':pointer,'previous_pointer_sha256':sha(folder/'current.json') if pointer else None,'manifest_sha256':sha(generation/'manifest.json')})
            row.update(status='ready',conversion=record['conversion'],model_review=record['model_review'],compilation=record['compilation'],coverage_flags='Region ownership complete; semantic/source verification remains limited',selected_generation={'generation':'generations/'+name,'manifest_sha256':sha(generation/'manifest.json'),'status':'ready_working_source'})
        rows.append(row)
    report={'collection':str(PARENT/'collection.json'),'inventory_sha256':sha(PARENT/'collection.json'),'sources':rows,'counts':{k:sum(r['status']==k for r in rows) for k in ['ready','partial','deferred']},'updates':updates,'experimental_outputs':experiment_inventory(),'author_sources':'No version-matched author-source package is selected by the existing per-source records; broad source search/audit deliberately deferred.'}
    atomic_json(dest/'reconciliation.json',report);atomic_json(dest/'documents.json',manifest)
    print(report['counts']);return report

def publish(destination):
    dest=Path(destination);report=read_json(dest/'reconciliation.json');manifest=read_json(dest/'documents.json');library.verify_originals(manifest)
    with writer_lock(ROOT),writer_lock(LIBRARY):
        for u in report['updates']:
            doc=u['document'];out=LIBRARY/doc['folder'];expected={'generation':'generations/'+u['generation'],'manifest_sha256':u['manifest_sha256'],'status':'ready_working_source'};pointer=read_json(out/'current.json') if (out/'current.json').exists() else None
            if pointer!=expected and pointer!=u['previous_pointer']:raise ValueError('Library selection changed since reconciliation; preserve operator work')
            policy.validate_publication(u['prepared'],doc)
            if pointer!=expected:
                history=out/'selection-history'/('before-'+u['generation']+'.json');atomic_json(history,{'current':pointer,'readme':(out/'README.md').read_text() if (out/'README.md').exists() else None})
                library.publish_generation(out,u['generation'],u['prepared'],'ready_working_source')
            # Keep source-root README/operator edits untouched. The new index links
            # directly to the selected immutable generation and its honest status.
        lines=['# Library-first source index','', 'Ready means usable complete assigned source with a passing recorded build; not mathematically certified. Partial sources remain visible. The original INDEX.md and vault are preserved.','', '| Source | Type | Pages | Status | Selected generation |','|---|---|---:|---|---|']
        for r in report['sources']:
            pointer=r['selected_generation'];target=r['folder']+'/'+pointer['generation']+'/README.md' if pointer else r['folder']+'/README.md'
            lines.append('| ['+r['filename'].replace('|','/')+']('+r['folder']+'/original.pdf) | '+r['type']+' | '+str(r['pages'])+' | '+r['status']+' | [source]('+target+') |')
        (LIBRARY/'LIBRARY-FIRST-INDEX.md').write_text('\n'.join(lines)+'\n');atomic_json(LIBRARY/'library-first-status.json',{'counts':report['counts'],'sources':report['sources'],'reconciliation':str(dest/'reconciliation.json')})
        (LIBRARY/'LIBRARY-HANDOFF.md').write_text('# Knowledge-library handoff\n\nStart with [ready/partial/deferred index](LIBRARY-FIRST-INDEX.md) and [machine-readable status](library-first-status.json). Originals are unchanged. Existing per-source folders, IDs and immutable generations are reused. Corrected CF, Spectral and P-values generations are selected by their current.json. Prior pointers are recorded in selection-history/.\n\nThe existing wiki has tools/llm.py, an older model helper, but no discovered import command for these TeX packages. No vault, extracted Markdown, SQLite or retrieval redesign was performed. Consume selected TeX and source mappings as source documents; do not describe them as already-complete Markdown or verified wiki facts. Conversion, content/build status, review completeness and direct source checks are separate.\n')
    atomic_json(dest/'publication.json',{'status':'published','counts':report['counts'],'index':str(LIBRARY/'LIBRARY-FIRST-INDEX.md'),'handoff':str(LIBRARY/'LIBRARY-HANDOFF.md'),'new_generations':[u['generation'] for u in report['updates']],'original_vault_and_index':'unchanged'})
    print(json.dumps(read_json(dest/'publication.json'),indent=2))

def catalog_experiments(destination, *, publish=False):
    """Expose later useful partial work without replacing current complete editions."""
    dest=Path(destination);report=read_json(dest/'reconciliation.json');manifest=read_json(dest/'documents.json');rows={r['source_id']:r for r in report['sources']};groups={}
    for item in report['experimental_outputs']:
        sid=item['source_key']
        if sid in rows and rows[sid]['status']=='partial':groups.setdefault(sid,[]).append(item)
    catalog=[]
    from scripts import book_completion as books
    for sid,items in groups.items():
        doc=next(d for d in manifest['documents'] if d['source_id']==sid);out=dest/'experimental-supplements'/sid
        if not (out/'manifest.json').exists():
            out.mkdir(parents=True,exist_ok=True);parts=[];missing=[]
            for item in items:
                run=Path(item['run']);state=read_json(run/'state.json');key=item['unit'];tex=Path(item['tex']);folder=out/'parts'/key
                library.copy_verified(tex,folder/'document.tex',item['sha256']);parts.append({'path':str((folder/'document.tex').relative_to(out)),'sha256':item['sha256']})
                for name,path in books.asset_map(run,sid,tex.read_text()).items():library.copy_verified(path,folder/name)
                for label,v in state['versions'][key].items():
                    if label.startswith('convert-') or label=='saved-baseline':library.copy_verified(run/v['path'],folder/'previous'/('version-'+label+'.tex'),v['sha256'])
                atomic_json(folder/'source-scope.json',state['source_units'][key]);atomic_json(folder/'version.json',state['versions'][key][item['selected']])
                build=state['versions'][key][item['selected']].get('compilation',{})
                if build.get('status')=='passed':
                    path=run/build['attempts'][-1]['path']/'document.pdf'
                    library.copy_verified(path,folder/'reading.pdf')
                else:missing.append({'unit':key,'build':build.get('status')})
                for p in (run/'accuracy'/key).rglob('*'):
                    if p.is_file():library.copy_verified(p,folder/'accuracy'/p.relative_to(run/'accuracy'/key))
            status={'source_id':sid,'source_sha256':doc['sha256'],'status':'partial_source','content_status':'partial_or_not_fully_qualified','compilation':'mixed_or_scope_only','selected_tex':parts,'experimental_scopes':items,'failed_builds':missing,'model_review':'See per-version/accuracy records; some findings-only reviews cover part of the full saved draft','source_verification':'not complete; earlier selected source remains selected'}
            atomic_json(out/'library-status.json',status);(out/'README.md').write_text('# '+doc['title']+' — saved recovery supplement\n\nPartial experimental outputs only. Some draft files contain broader original text than the assigned review scope; source-scope.json records actual reviewed ownership. Do not label this a complete new conversion. The source current.json is unchanged. Passing scoped PDFs, failed versions, original drafts, assets and accuracy records are retained.\n');seal(out)
        policy.validate_publication(out,doc);name='library-supplement-20261107-'+sha(out/'manifest.json')[:16];item={'source_id':sid,'folder':doc['folder'],'generation':name,'prepared':str(out),'manifest_sha256':sha(out/'manifest.json'),'selected':False};catalog.append(item)
        if publish:
            with writer_lock(LIBRARY):library.publish_generation(LIBRARY/doc['folder'],name,out,'partial_source',select=False)
    atomic_json(dest/'experimental-catalog.json',catalog)
    if publish:
        (LIBRARY/'SAVED-RECOVERY-SUPPLEMENTS.md').write_text('# Saved recovery supplements\n\nPartial, unselected generations; existing current.json pointers are unchanged.\n\n'+'\n'.join('- ['+next(d['title'] for d in manifest['documents'] if d['source_id']==r['source_id'])+']('+r['folder']+'/generations/'+r['generation']+'/README.md)' for r in catalog)+'\n')
    print('Saved recovery supplements:',len(catalog),'published' if publish else 'prepared')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','publish','prepare-supplements','publish-supplements']);p.add_argument('--output',type=Path,default=DEV/'reconciliation');a=p.parse_args()
    if a.action.endswith('supplements'):catalog_experiments(a.output,publish=a.action=='publish-supplements')
    else:(prepare if a.action=='prepare' else publish)(a.output)
