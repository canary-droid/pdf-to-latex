"""Saved-result inspection export for the finite library worker. No inference."""
import csv,hashlib,io,json,time,zipfile
from datetime import datetime
from pathlib import Path
from .common import atomic_json,read_json,sha,files_manifest
from .experiment import verify_seal
from . import source_library,book_completion

def inspection(run,state,output_root):
    run=Path(run).resolve();folder=run/'report'/str(time.time_ns());folder.mkdir(parents=True)
    plan=read_json(run/'plan.json');included={};missing=[];flagged={};summary=[];timings=[]
    if plan.get('allocation_id'):
        from . import library_allocation,library_fallbacks
        allocation=library_allocation.verify(plan['paid_approval']);budget=library_fallbacks.budget_folder(run,plan['paid_approval'])
        for base,sub in ((allocation,'allocation'),(budget,'shared')):
            paths=[base/n for n in ('allocation.json','approval.json','binding.json','BUDGET-AUTHORIZATION.json','prior-billing.json','billing.json','ledger.json','initialized.json') if (base/n).exists()]
            if sub=='shared':paths += [p for name in ('results','releases','reservations','attempts') for p in (base/name).rglob('*') if p.is_file() and p.name in ('findings.json','outcome.json','transport-phase.json','admission.json','changes.diff','candidate.tex','library-answer.txt')]
            for path in paths:
                destination=run/'paid-accounting-snapshot'/sub/path.relative_to(base);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(path.read_bytes())
    def forbidden(path):
        return any(x.startswith('.venv') or x in ('.git','__pycache__','credentials','weights','models') for x in path.parts) or path.name in ('auth.json','.env','openrouter.key','mathpix.json') or path.suffix in ('.safetensors','.gguf','.key') or 'reasoning' in path.name.lower()
    def add(path,destination=None,expected=None,required=False):
        path=Path(path)
        if not path.is_absolute():path=run/path
        if not path.resolve().is_relative_to(run) or path.is_symlink() or forbidden(path.relative_to(run)):
            missing.append({'path':str(path),'reason':'Outside run / symlink / forbidden credential-weight-reasoning artifact','required':required});return
        rel=path.relative_to(run)
        if not path.is_file():
            if required:missing.append({'path':str(path),'reason':'Referenced artifact absent','required':True})
            return
        digest=sha(path)
        if expected and expected!=digest:
            missing.append({'path':str(path),'reason':'Identity differs from selected/frozen record','expected':expected,'observed':digest,'required':required});return
        dest=folder/(destination or str(rel))
        if not dest.resolve().is_relative_to(folder):raise ValueError('Unsafe inspection destination')
        source_library.copy_verified(path,dest,digest)
        included[str(rel)]=str(dest.relative_to(folder))
    def flag(sid,pages,reason):
        for page in pages:flagged.setdefault((sid,page),set()).add(reason)
    for name in ('plan.json','state.json','progress.json','binding.json','task-plan.json','normal-terminal-checks.json','preparation-link.json','effort-support-live.json'):
        add(name)
    for p in (run/'source-plans').glob('*.json'):add(p)
    for base in ('authorization','historical-hold-releases','paid-accounting-snapshot','implementation'):
        for p in (run/base).rglob('*'):
            if p.is_file():add(p)
    add('review-salvage.json');add('input-dispositions.json')
    for call in state['calls']:
        task=next((t for t in state['tasks'] if t['id']==call['parent']),{})
        usage=call.get('metadata',{}).get('usage',{});reason=usage.get('completion_tokens_details',{}).get('reasoning_tokens');total=usage.get('completion_tokens')
        timings.append({'call':call['id'],'task':call['parent'],'source':task.get('source_key'),'phase':task.get('phase'),'status':call['status'],
          'seconds':call.get('elapsed_seconds'),'reasoning_tokens':reason,'final_tokens':total-reason if isinstance(total,int) and isinstance(reason,int) else None,
          'completion_tokens':total,'cached_tokens':usage.get('prompt_tokens_details',{}).get('cached_tokens'),'server_timings':call.get('metadata',{}).get('server_timings')})
        for name in ('answer.txt','content.txt','findings.json','changes.diff','accuracy.json','outcome.json','response-metadata.json','settings.json','admission.json'):
            derived=run/'call-results'/call['id']/name
            add(derived if derived.exists() else Path('calls')/call['id']/name,destination=str(Path('calls')/call['id']/name))
    if plan.get('overnight'):
        for base in ('fallback-budget','paid-proposals','jobs','paid-readiness'):
            for file in (run/base).rglob('*'):
                if file.is_file() and file.name not in ('request.json','response.raw','reasoning.txt','reasoning-details.json') and not forbidden(file.relative_to(run)):
                    if file.suffix in ('.json','.tex','.diff','.md','.txt') and file.stat().st_size<2000000:add(file)
        add('billing.json');add('prior-billing.json')
    for doc in plan['documents']:
        sid=doc['source_id'];record=state['documents'][sid];outstanding=record.get('outstanding_scopes',[]);tasks=[t for t in state['tasks'] if t['source_key']==sid]
        delivery=Path(record.get('delivery',run/'deliveries'/sid));publication=read_json(delivery/'library-status.json') if (delivery/'library-status.json').exists() else None
        delivery_integrity='not sealed'
        if (delivery/'manifest.json').exists():
            try:verify_seal(delivery);delivery_integrity='verified'
            except (ValueError,OSError) as exc:
                delivery_integrity='failed';missing.append({'path':str(delivery),'required':True,'reason':'Delivery seal failed: '+str(exc)})
        for p in delivery.rglob('*'):
            if p.is_file():add(p,required=True)
        flag(sid,record.get('failed_pages',[]),'extraction failed/incomplete')
        for scope in outstanding:flag(sid,scope['physical_pages'],'outstanding source scope '+scope['first']+'..'+scope['last'])
        units=[]
        for key in record['units']:
            unit=state['source_units'][key];label=state['current_versions'].get(key);versions=state['versions'].get(key,{})
            selected=versions.get(label);task_rows=[t for t in tasks if t['key']==key];findings=[]
            add(Path('inputs')/key/'unit.json',required=True);add(Path('inputs')/key/'images.json');add(Path('cpu-verification')/(key+'.json'))
            for t in task_rows:
                if t.get('call'):
                    path=run/'call-results'/t['call']/'findings.json'
                    if not path.exists():path=run/'calls'/t['call']/'findings.json'
                    if path.exists():findings+=read_json(path).get('findings',[])
                if t['status'] not in ('pending','running','conversion_completed','review_completed'):
                    flag(sid,unit['physical_pages'],'task '+t['id']+': '+t['status'])
                if t.get('paid_recovery'):flag(sid,unit['physical_pages'],'paid recovery requires explicit source comparison: '+t['id'])
                if t.get('pending_suggestions') or t.get('unresolved') or (t['status']=='review_completed' and not t.get('review_complete_attested')):
                    flag(sid,unit['physical_pages'],'pending findings or incomplete review attestation: '+t['id'])
            if findings:flag(sid,unit['physical_pages'],'reviewer proposed edits/findings: '+key)
            for version_name,v in versions.items():
                # Preserve both original/model versions and any deterministic parent.
                for candidate in [v]+([v['syntax_parent']] if v.get('syntax_parent') else []):
                    path=run/candidate['path'];add(path,expected=candidate['sha256'],required=True)
                    if path.is_file() and sha(path)==candidate['sha256']:
                        for ref in book_completion.image_references(path.read_text()):
                            source=unit['assets'].get(ref)
                            if source:add(source,destination=str(Path(candidate['path']).parent/ref),required=True)
                            else:missing.append({'path':ref,'version':candidate['path'],'required':True,'reason':'Required asset absent from source allowlist'})
                    for attempt in candidate.get('compilation',{}).get('attempts',[]):
                        for name in ('console.log','document.log','document.aux','document.pdf','execution.json','outcome.json'):
                            add(Path(attempt['path'])/name,required=name in ('console.log','document.pdf') and candidate['compilation']['status']=='passed')
                        add(Path(attempt['path']).parent/'compilation.json')
                if v.get('compilation',{}).get('status') not in ('passed','not_requested'):flag(sid,unit['physical_pages'],'failed build: '+key+'/'+version_name)
            units.append({'unit':key,'physical_pages':unit['physical_pages'],'selected_label':label,'selected_version':selected,
                'tasks':task_rows,'findings':findings,'source_scope':'inputs/'+key+'/unit.json'})
        if publication:
            for index,coverage in enumerate(publication.get('coverage',[])):
                if coverage.get('coverage_status')=='omission_risk':
                    chosen=[u for u in units if u['selected_version']]
                    flag(sid,chosen[index]['physical_pages'] if index<len(chosen) else doc['physical_pages'],'generated content/figure coverage flag')
        summary.append({'source_id':sid,'filename':doc['filename'],'source_sha256':doc['sha256'],'physical_pages':doc['physical_pages'],
          'status':record['status'],'diagnostic':record.get('diagnostic'),'source_accounting':record.get('source_accounting'),
          'outstanding_scopes':outstanding,'units':units,'publication':publication,'selected_new_generation':record.get('selected_new_generation',False),
          'delivery_integrity':delivery_integrity,'content_complete':bool(delivery_integrity=='verified' and publication and publication['content_status']=='complete_assigned_source' and not outstanding),
          'source_verification':'Only explicitly recorded checks; model response/compilation are not mathematical proof'})
    images=[]
    for (sid,n),reasons in sorted(flagged.items()):
        doc=next(d for d in plan['documents'] if d['source_id']==sid);page=next((p for p in doc['pages'] if p['physical_pdf_page']==n),None)
        if page is None:missing.append({'source_id':sid,'page':n,'reason':'Flagged page absent from original-page manifest','required':True});continue
        add(page['path'],expected=page['sha256'],required=True);images.append({'source_id':sid,'physical_page':n,'path':page['path'],'sha256':page['sha256'],'reasons':sorted(reasons)})
    atomic_json(folder/'PAPER-SUMMARY.json',summary);atomic_json(folder/'FLAGGED-SOURCE-PAGES.json',images)
    atomic_json(folder/'TIMINGS.json',timings);stream=io.StringIO()
    fields=('call','task','source','phase','status','seconds','reasoning_tokens','final_tokens','completion_tokens','cached_tokens')
    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows({k:r[k] for k in fields} for r in timings);(folder/'TIMINGS.csv').write_text(stream.getvalue())
    durations=[r['seconds'] for r in timings if isinstance(r['seconds'],(int,float))];failed=[r['seconds'] for r in timings if r['status']!='completed_response' and isinstance(r['seconds'],(int,float))]
    wall=None
    if state.get('launches') and state.get('finished_at'):wall=(datetime.fromisoformat(state['finished_at'])-datetime.fromisoformat(state['launches'][0]['at'])).total_seconds()
    extraction={arm:{'status':data.get('status'),'load_seconds':data.get('load_seconds'),'pages':{key:{k:row.get(k) for k in ('status','source_id','physical_page','elapsed_seconds','peak_torch_allocated_bytes','process_lifetime_peak_rss_kib')} for key,row in data.get('pages',{}).items()}} for arm,data in state.get('extraction',{}).items()}
    atomic_json(folder/'TIMING-SUMMARY.json',{'request_seconds_summed':sum(durations),'failed_request_seconds_included':sum(failed),'elapsed_batch_seconds':wall,
      'extraction':extraction,'interpretation':'Summed request durations overlap at concurrency two. Missing timings are unknown, not zero; extraction load/page measurements are separate.'})
    lines=['# Finite library batch results','', 'Status: '+state['status'], '',
      'High conversion / High image review (unless explicit Max in plan); at most two local requests. '+('Conditional Mathpix/Kimi recovery uses ONE fresh combined $7 allocation; historical charges remain separate and provider allowance still applies.' if plan.get('allocation_id') else 'Paid recovery is explicitly approved in plan.json.' if plan.get('paid_enabled') else 'Paid routes disabled.')+' No overall deadline. This archive contains saved results, not mathematical certification.',
      '', '| Paper | Status | Content complete | Produced-part compilation | Outstanding source spans |', '|---|---|---|---|---:|']
    for row in summary:
        pub=row['publication'] or {};lines.append('| '+row['filename'].replace('|','/')+' | '+row['status']+' | '+str(row['content_complete'])+' | '+pub.get('compilation','not published')+' | '+str(len(row['outstanding_scopes']))+' |')
    lines+=['','Read PAPER-SUMMARY.json for per-unit selected versions, review findings, pending/failed reviews and exact outstanding scopes. deliveries/ contains portable selected TeX/assets and reading PDFs where produced; versions/ also retains original/reviewed candidates, including unpublished results and failed builds. calls/ contains final responses, edit diffs and compact diagnostics. TIMINGS.csv separates calls/phases/failures. FLAGGED-SOURCE-PAGES.json identifies included ORIGINAL page images. No generated reading PDF is presented as source evidence.',
      '', 'Source-plan accounting includes both scheduled and outstanding regions exactly once. A passing build of scheduled parts cannot make an incomplete paper complete. Missing/unavailable artifacts are explicit in MISSING-ARTIFACTS.json. OMITTED.json lists all run files excluded, with reasons. Credentials, model weights, environments, lengthy reasoning, repeated base64 request payloads and raw streams are excluded. Originals and full evidence remain at their saved local paths.']
    (folder/'START-HERE.md').write_text('\n'.join(lines)+'\n');atomic_json(folder/'MISSING-ARTIFACTS.json',missing)
    omitted=[]
    for p in sorted(run.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(run)
        if rel.parts[0]=='report' or str(rel) in included:continue
        if forbidden(rel):reason='credentials/weights/environment/lengthy reasoning excluded; contents not read for packaging'
        elif p.name=='request.json' or rel.parts[0]=='requests':reason='Full request/base64 payload retained locally; source/draft/image mappings included instead'
        elif p.name in ('response.raw','stream-events.jsonl'):reason='Bulky wire/stream trace retained locally; response metadata and final text included'
        elif rel.parts[0]=='sources':reason='Original source image/text not flagged for this focused inspection; frozen identity remains in plan'
        elif rel.parts[0] in ('compiler-environments','arms','peer-input.tar','host-operations','samples'):reason='Runtime/extraction bulk evidence; selected outputs/provenance and timing records included'
        else:reason='Supporting run artifact outside selected result/diagnostic scope'
        omitted.append({'path':str(rel),'existing_path':str(p),'bytes':p.stat().st_size,'reason':reason})
    omitted.append({'path':'report/','reason':'Prior report snapshots and the current report tree are not recursively copied'})
    atomic_json(folder/'OMITTED.json',omitted)
    manifest=files_manifest(folder);atomic_json(folder/'FILE-HASHES.json',manifest)
    result=source_library.archive(Path(output_root)/(run.name+'-'+folder.name+'.zip'),folder)
    with zipfile.ZipFile(result['path']) as z:
        if set(z.namelist())!={r['path'] for r in manifest}|{'FILE-HASHES.json'}:raise ValueError('Inspection manifest incomplete')
        for r in manifest:
            if hashlib.sha256(z.read(r['path'])).hexdigest()!=r['sha256']:raise ValueError('Inspection hash verification failed')
    return dict(result,hashes_verified=True,missing_artifacts=len(missing),report=str(folder))
