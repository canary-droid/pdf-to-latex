#!/usr/bin/env python3
"""Offline, explicit source-first intake. No OCR/model/paid/compile transport.

Uses the completed audit cache and one separately retrieved 0906.0103v4 package.
Preparation writes only project results; publication is a separate verified step.
"""
import argparse,copy,hashlib,json,re,sys,time,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe import author_source as author,source_library as library,library_first as policy,tex_syntax_repair
from probe.common import read_json,atomic_json,sha,writer_lock
from probe.experiment import seal,verify_seal
from scripts import library_reconcile as reconcile
OUTPUT=ROOT/'results/wiki-source-first-20261107'
AUDIT=ROOT/'results/source-availability-audit-20261104T194212Z'
TARGETS=[
 ('COS Le Floch.pdf','2005.13248v2','same'),('Attention_2017.pdf','1706.03762v7','same'),
 ('Information_Geometry.pdf','2206.08753v3','same'),('mittag_leffler_cpp.pdf','2408.10257v1','same'),
 ('PhysRevLett.127.241602.pdf','2108.07820v2','alternative'),('pricing_cryptocurrency_options_2020.pdf','2009.11007v1','alternative'),
 ('Path Integrals and SDEs.pdf','1009.5966v2','alternative'),('noether_-_invariant_variational_problems.pdf','physics/0503066v3','alternative'),
 ('RH_innocentis_levendorskii.pdf','2508.15080v3','same'),('All_about_xva.pdf','2107.10377v3','alternative'),
 ('Brigo_Deep_Interpretability.pdf','2411.19317v1','same'),('Implied_Vol_Homescu.pdf','1107.1834v1','same'),
 ('bayer_breneis23a_arxiv.pdf','2309.07023v1','unresolved'),('SINC.pdf','2009.00557v2','same'),
 ('IV Surface Construction.pdf','1107.1834v1','unresolved'),('Path Integral Schrodinger.pdf','0906.0103v4','unresolved')]

def pdf_comparison(original,other):
    import fitz
    def text(path):
        with fitz.open(path) as doc:
            pages=[p.get_text('text') for p in doc]
        joined=re.sub(r'\s+','',unicodedata.normalize('NFKC','\n'.join(pages)))
        return {'pages':len(pages),'native_characters':len(joined),'native_normalised_sha256':hashlib.sha256(joined.encode()).hexdigest(),'title_page':pages[0][:2500]}
    a=text(original);b=text(other);identical=sha(original)==sha(other);native_equal=bool(a['native_characters']>1000 and a['native_normalised_sha256']==b['native_normalised_sha256'])
    return {'original':a,'author_version':b,'exact_pdf_bytes':identical,'full_native_text_equal':native_equal,'normalisation':'Unicode NFKC and whitespace only; no dropped mathematical symbols','limitation':'Text equality does not verify graphics; differing text is not evidence of different mathematics by itself'}

def prepare_author(doc,version,relation,packages,outroot):
    meta=packages[version];package=ROOT/meta['package'];saved=meta['sha256']
    if sha(package)!=saved:raise ValueError('Cached author package changed '+version)
    original=Path(doc['originals'][0]['path'])
    if sha(original)!=doc['sha256']:raise ValueError('Original identity changed')
    out=outroot/doc['source_id'];out.mkdir(parents=True,exist_ok=True)
    if (out/'manifest.json').exists():return policy.validate_publication(out,doc)
    library.copy_verified(package,out/'original-package',saved)
    for name,data in author.unpack(package.read_bytes()).items():
        path=out/'sources'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    evidence=package.parent/'corresponding-version.pdf'
    comparison=pdf_comparison(original,evidence) if evidence.is_file() else {'missing':'Cached corresponding PDF absent'}
    if relation=='same' and not comparison.get('exact_pdf_bytes'):raise ValueError('Recorded same-version PDF identity not reproduced '+version)
    if doc['source_id']=='original-0823b5f29df2e2b7':
        # The alias has different PDF bytes. Full native content and page sequence
        # establish correspondence; visual equivalence is not claimed from text.
        relation='same' if comparison.get('full_native_text_equal') else 'unresolved'
    if version=='0906.0103v4':relation='same' if comparison.get('exact_pdf_bytes') or comparison.get('full_native_text_equal') else 'alternative'
    if evidence.is_file():library.copy_verified(evidence,out/'author-version.pdf')
    inspection,ordered=author.inspect_tree(out/'sources',meta['main'])
    atomic_json(out/'dependency-inspection.json',inspection);(out/'ordered-source.tex').write_text(ordered)
    source_version={'identifier':'arxiv:'+version,'source_url':'https://arxiv.org/src/'+version,'package_sha256':saved,
      'correspondence':relation,'canonical_work_id':'arxiv:'+re.sub(r'v\d+$','',version),'original_pdf_sha256':doc['sha256'],
      'comparison':comparison,'original_pdf_coverage':'Correspondence supported as recorded; static dependency completeness is not a mathematical audit' if relation=='same' else 'Not established; this is complete content of the declared author version, not the original PDF',
      'retrieval_record':str(package),'inspection_date_utc':time.strftime('%Y-%m-%d',time.gmtime())}
    if version=='physics/0503066v3':source_version['translation']={'original_pdf':'D. H. Delphenich','author_source':'M. A. Tavel','relation':'Alternative English translation; never merged or labelled identical'}
    if version=='1107.1834v1':source_version['aliases']=['Implied_Vol_Homescu.pdf','IV Surface Construction.pdf'];source_version['work_count']=1
    audit=Path(meta.get('audit',''))
    if audit.is_file():library.copy_verified(audit,out/'saved-audit-inspection.json')
    for name in ('source-retrieval.json','pdf-retrieval.json','inspection.json'):
        if (package.parent/name).is_file():library.copy_verified(package.parent/name,out/'retrieval-evidence'/name)
    # These raw-file mappings resolve case/path findings without changing author
    # bytes or borrowing an image from a different version.
    figures=[d for d in inspection['resolved_dependencies'] if d['command']=='includegraphics']
    atomic_json(out/'figure-index.json',figures);atomic_json(out/'source-version.json',source_version)
    ready=inspection['complete_content_dependencies']
    status={'source_id':doc['source_id'],'source_sha256':doc['sha256'],'source_kind':'author_tex','source_version':source_version,'entry_point':meta['main'],
      'status':'ready_working_source' if ready else 'partial_source','content_status':'complete_declared_version' if ready else 'missing_substantive_dependencies',
      'compilation':'not_requested','conversion':'author_source_no_conversion','model_review':{'status':'not_requested_author_source','independent_mathematical_verification':'not established'},
      'selected_tex':[{'path':'ordered-source.tex','sha256':sha(out/'ordered-source.tex')}],
      'source_verification':'Archive identity and static dependencies inspected; mathematical accuracy not independently verified',
      'coverage':inspection,'outstanding_scopes':inspection['missing_substantive']+inspection['unresolved_content_dependencies']}
    atomic_json(out/'library-status.json',status)
    (out/'README.md').write_text('# '+doc['originals'][0]['name']+' — author source\n\n[Original reading PDF](../../original.pdf). [Declared author-version PDF](author-version.pdf).\n\nText version: **'+version+'**. Correspondence: **'+relation+'**. '+source_version['original_pdf_coverage']+'.\n\n[Ordered source view](ordered-source.tex), [raw main TeX](sources/'+meta['main']+'), [dependencies](dependency-inspection.json), [figures and exact paths](figure-index.json), [source/version evidence](source-version.json). All package files, including bibliography and custom definitions, are retained under sources/. The ordered view follows literal active includes; raw files remain authoritative. It is a reading view, not a promised compilable master.\n\nContent status: '+status['content_status']+'. Compilation and automatic model review: not requested. No mathematical accuracy certificate.\n'+ ('\nTranslation: original PDF D. H. Delphenich; author package M. A. Tavel.\n' if 'translation' in source_version else ''))
    seal(out);policy.validate_publication(out,doc);return status

def assess_saved(row,doc):
    pointer=row.get('selected_generation');record={'source_id':row['source_id'],'filename':row['filename'],'previous_status':row['status'],'decision':'preserve','reason':row.get('reason'),'checks':[]}
    if not pointer:return record
    folder=reconcile.LIBRARY/row['folder']/pointer['generation'];verify_seal(folder,pointer['manifest_sha256'])
    if (folder/'library-status.json').exists():
        old=read_json(folder/'library-status.json');record['reason']='Existing selected scoped edition retained; recorded source checks/review remain distinct';return record
    cov=read_json(folder/'coverage.json')
    if cov['source_sha256']!=doc['sha256']:raise ValueError('Saved source identity mismatch')
    record.update(conversion=cov['conversion'],model_review=cov['model_review'],compilation=cov['compilation'],possible_content_gaps=cov['possible_content_gaps'])
    for part in cov['parts']:
        if not part.get('selected'):continue
        tex=folder/'parts'/part['unit']/'document.tex'
        if sha(tex)!=part['sha256']:raise ValueError('Selected historical text changed')
        assets={str(x.relative_to(tex.parent)):x for x in tex.parent.rglob('*') if x.is_file()}
        check=author.generated_content(tex.read_text(),assets);check.update(unit=part['unit'],tex=str(tex),sha256=part['sha256'])
        for a in part.get('compilation',{}).get('attempts',[])[-1:]:
            log=reconcile.PARENT/a['path']/'console.log'
            if log.exists():check['compiler_first_error']=tex_syntax_repair.first_error(log.read_text(errors='replace'));check['compiler_log']=str(log)
        record['checks'].append(check)
    eligible=(row['status']=='partial' and cov['conversion']=='completed' and not cov['possible_content_gaps'] and bool(record['checks']) and len(record['checks'])==len(cov['parts']) and all(c['usable'] for c in record['checks']))
    record.update(decision='promote_content_only' if eligible else 'preserve',reason='Complete assigned saved text/assets; build failure alone is not a library blocker' if eligible else ('Recorded content/coverage issues, incomplete conversion or damaged mathematics remain' if row['status']=='partial' else 'Previously selected source retained; no new mathematical certification'))
    return record

def prepare():
    if not all(reconcile.ROOT.joinpath(p).is_dir() for p in ('runs','probe')):raise ValueError('Wrong project')
    from scripts import library_pipeline as pipeline
    if not all(pipeline.base.books.speed.idle(p) for p in (ROOT,ROOT/'runs')):raise ValueError('Project worker active')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    index=read_json(reconcile.LIBRARY/'library-first-status.json');collection=read_json(reconcile.PARENT/'collection.json');docs={d['source_id']:d for d in collection['documents']}
    if not (OUTPUT/'before-library-status.json').exists():atomic_json(OUTPUT/'before-library-status.json',index)
    else:index=read_json(OUTPUT/'before-library-status.json')
    packages={x['version']:x for x in read_json(OUTPUT/'package-discovery.json')}
    target=OUTPUT/'targeted-0906.0103v4';packages['0906.0103v4']={'version':'0906.0103v4','package':str(target/'original-package'),'sha256':read_json(target/'inspection.json')['sha256'],'main':'source.tex'}
    updates=[];author_rows=[];assessments=[]
    target_ids=set()
    for filename,version,relation in TARGETS:
        matches=[d for d in docs.values() if any(o['name']==filename for o in d['originals'])]
        if len(matches)!=1:raise ValueError('Ambiguous target '+filename)
        doc=matches[0];sid=doc['source_id'];target_ids.add(sid);out=OUTPUT/'generations'/sid
        status=prepare_author(doc,version,relation,packages,OUTPUT/'generations');before=next(r for r in index['sources'] if r['source_id']==sid)
        name='author-source-20261107-'+sha(out/'manifest.json')[:16]
        updates.append({'source_id':sid,'folder':doc['folder'],'prepared':str(out),'generation':name,'previous_pointer':before.get('selected_generation'),'status':status['status'],'select':status['status']=='ready_working_source','kind':'author_tex'})
        author_rows.append({'source_id':sid,'filename':filename,'version':version,'correspondence':status['source_version']['correspondence'],'status':status['content_status'],'figures':sum(d['command']=='includegraphics' for d in status['coverage']['resolved_dependencies']),'prepared':str(out)})
    for row in index['sources']:
        doc=docs[row['source_id']];assessment=assess_saved(row,doc);assessments.append(assessment)
        if assessment['decision']!='promote_content_only' or row['source_id'] in target_ids:continue
        old=reconcile.LIBRARY/row['folder']/row['selected_generation']['generation'];out=OUTPUT/'generations'/row['source_id']
        if not (out/'manifest.json').exists():
            # Copy the complete portable evidence; old seal is retained as a
            # provenance artifact, never overwritten/resealed in its old folder.
            for p in old.rglob('*'):
                if p.is_file():library.copy_verified(p,out/('previous-generation-manifest.json' if p==old/'manifest.json' else str(p.relative_to(old))))
            parts=[{'path':str(Path(c['tex']).relative_to(old)),'sha256':c['sha256']} for c in assessment['checks']]
            record={'source_id':doc['source_id'],'source_sha256':doc['sha256'],'status':'ready_working_source','content_status':'complete_assigned_source','source_kind':'saved_conversion',
              'compilation':'failed','historical_compilation':assessment['compilation'],'conversion':assessment['conversion'],'model_review':assessment['model_review'],
              'selected_tex':parts,'coverage':assessment,'source_verification':'Historical deterministic coverage checks and saved assets; not independently mathematically verified',
              'provenance':{'previous_generation':str(old),'manifest_sha256':row['selected_generation']['manifest_sha256']}}
            atomic_json(out/'library-status.json',record);(out/'README.md').write_text('# '+row['filename']+'\n\nComplete assigned saved text is useful independently of its failed historical PDF build. [Unchanged original reading PDF](../../original.pdf). See library-status.json for identity, review and content checks; previous coverage and build diagnostics are preserved. Mathematics is not independently certified.\n');seal(out)
        policy.validate_publication(out,doc);updates.append({'source_id':doc['source_id'],'folder':doc['folder'],'prepared':str(out),'generation':'content-first-20261107-'+sha(out/'manifest.json')[:16],'previous_pointer':row['selected_generation'],'status':'ready_working_source','select':True,'kind':'saved_conversion'})
    atomic_json(OUTPUT/'reassessment.json',assessments);atomic_json(OUTPUT/'author-imports.json',author_rows)
    plan={'status':'prepared','inventory':str(reconcile.PARENT/'collection.json'),'inventory_sha256':sha(reconcile.PARENT/'collection.json'),'prior_index_sha256':sha(OUTPUT/'before-library-status.json'),'updates':updates,'calls':0,'compilation':'not_requested','source_packages':15,'author_pdf_entries':16,'independent_author_works':15}
    atomic_json(OUTPUT/'intake-plan.json',plan);print(json.dumps({'prepared_imports':len(author_rows),'content_only_promotions':[r['filename'] for r in assessments if r['decision']=='promote_content_only' and r['source_id'] not in target_ids]},indent=2))

def publish():
    from scripts import library_pipeline as pipeline
    plan=read_json(OUTPUT/'intake-plan.json');original_index=read_json(OUTPUT/'before-library-status.json');index=copy.deepcopy(original_index)
    if sha(reconcile.PARENT/'collection.json')!=plan['inventory_sha256']:raise ValueError('Inventory changed')
    docs={d['source_id']:d for d in read_json(plan['inventory'])['documents']}
    with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(reconcile.LIBRARY):
        live=read_json(reconcile.LIBRARY/'library-first-status.json')
        if live!=original_index and live.get('source_first_intake')!=str(OUTPUT):raise ValueError('Library index changed; reconcile independently')
        for u in plan['updates']:
            doc=docs[u['source_id']];out=reconcile.LIBRARY/u['folder'];prepared=Path(u['prepared']);record=policy.validate_publication(prepared,doc)
            if sha(out/'original.pdf')!=doc['sha256']:raise ValueError('Original identity changed')
            pointer=read_json(out/'current.json') if (out/'current.json').exists() else None;expected={'generation':'generations/'+u['generation'],'manifest_sha256':sha(prepared/'manifest.json'),'status':u['status']}
            if pointer!=u['previous_pointer'] and pointer!=expected:raise ValueError('Selection changed since preparation')
            history=out/'selection-history'/('before-'+u['generation']+'.json')
            if not history.exists():atomic_json(history,{'current':pointer,'readme':(out/'README.md').read_text() if (out/'README.md').exists() else None})
            publication=library.publish_generation(out,u['generation'],prepared,u['status'],select=u['select'])
            metadata=read_json(out/'source.json');managed=(out/'README.md').exists() and (out/'README.md').read_text()==library.source_readme(metadata,pointer)
            if managed and u['select']:library.write_source_readme(out,metadata)
            row=next(x for x in index['sources'] if x['source_id']==u['source_id'])
            if u['select']:row.update(status='ready',selected_generation=publication,source_kind=record['source_kind'],source_version=record.get('source_version'),content_status=record['content_status'],compilation=record['compilation'],conversion=record['conversion'],model_review=record['model_review'],coverage_flags=record['coverage'],reason='Useful declared source content; original PDF retained; build independent')
        index['counts']={k:sum(x['status']==k for x in index['sources']) for k in ('ready','partial','deferred')};index['source_first_intake']=str(OUTPUT)
        index['objective']='Full substantive source for declared version. Original PDF is reading copy. Content, review, mathematical confidence and builds are separate.'
        index['known_aliases']=[{'work':'arxiv:1107.1834','source_ids':['original-35e1b06250285f1b','original-0823b5f29df2e2b7'],'independent_works':1}]
        atomic_json(reconcile.LIBRARY/'library-first-status.json',index);atomic_json(OUTPUT/'after-library-status.json',index)
        lines=['# Library source-first index','',index['objective'],'',str(index['counts'])+'. Counts are PDF identities, not independent works; the two Homescu PDFs share one work. Ready is useful declared content, not mathematical certification.','', '| Original PDF | Pages | Status | Selected version | Content | Build |','|---|---:|---|---|---|---|']
        for r in index['sources']:
            v=r.get('source_version') or {};pointer=r.get('selected_generation');target=r['folder']+'/'+pointer['generation']+'/README.md' if pointer else r['folder']+'/README.md'
            lines.append('| ['+r['filename'].replace('|','/')+']('+target+') | '+str(r['pages'])+' | '+r['status']+' | '+v.get('identifier','Saved conversion')+' '+v.get('correspondence','')+' | '+r.get('content_status','See recorded coverage')+' | '+str(r.get('compilation','not_requested'))+' |')
        for name in ('LIBRARY-FIRST-INDEX.md','LIBRARY-HANDOFF.md'):
            old=reconcile.LIBRARY/name
            if old.exists() and not (OUTPUT/('previous-'+name)).exists():library.copy_verified(old,OUTPUT/('previous-'+name))
        (reconcile.LIBRARY/'LIBRARY-FIRST-INDEX.md').write_text('\n'.join(lines)+'\n')
        (reconcile.LIBRARY/'LIBRARY-HANDOFF.md').write_text('# Content-first library handoff\n\n'+index['objective']+'\n\nSee [current index](LIBRARY-FIRST-INDEX.md) and [machine status](library-first-status.json). Author packages preserve raw sources, ordered source, macros, bibliography and figures. Noether is the Tavel translation, distinct from the Delphenich original; alternative versions do not establish original-PDF coverage. All previous editions and selection histories remain.\n\n'+str(index['counts'])+' across 63 PDF identities (62 works after the one established alias). Failed builds alone no longer block useful text. Outstanding content, mathematical ambiguity, missing substantive includes/assets and unfinished reviews remain visible.\n\nPrepared next batch: only Implied_Vol_Lee.pdf and BoyarchenkoLevendorskii_eigenfunction_MF_07.pdf, 65 pages; not launched. High conversion, High original-image review, at most two requests. Cooking excluded; broad audit deferred; paid fallbacks unarmed; no PDF build requested.\n')
    atomic_json(OUTPUT/'publication.json',{'status':'published','counts':index['counts'],'source_packages':15,'author_pdf_entries':16,'independent_author_works':15,'updates':plan['updates'],'inference_calls':0,'ocr_calls':0,'builds':0});print(index['counts'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','publish']);a=p.parse_args();(prepare if a.action=='prepare' else publish)()
