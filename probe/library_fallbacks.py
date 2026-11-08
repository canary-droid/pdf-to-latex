"""Bounded bridges to existing paid adapters. Default is a saved, disabled proposal."""
from decimal import Decimal
from pathlib import Path
import copy,json,time
from .common import read_json,atomic_json,sha,fingerprint,writer_lock
from . import library_first as policy,kimi_escalation as kimi,mathpix_experiment as mathpix

class NotApproved(ValueError):pass

def budget_folder(run,approval=None):
    return Path((approval or {}).get('ledger_root',Path(run)/'fallback-budget'))

def initialize_allocation_budget(folder,approval):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    with writer_lock(folder):
        if (folder/'initialized.json').exists() or (folder/'ledger.json').exists():raise kimi.IntegrityError('Allocation ledger already initialized')
        atomic_json(folder/'initialized.json',{'allocation_id':approval['allocation_id'],'approval_sha256':fingerprint(approval),'cap_usd':approval['new_spend_cap_usd']})
        atomic_json(folder/'ledger.json',{'approval_sha256':fingerprint(approval),'cap_usd':approval['new_spend_cap_usd'],'reservations':{}})

def reservation_identity(record,approval):
    if not approval.get('allocation_id'):return fingerprint({'scope':record['scope_sha256'],'phase':record['phase'],'kind':record['kind']})
    u=record['unit']
    owned=u.get('owned_blocks') or fingerprint(u.get('primary',''))
    return fingerprint({'allocation':approval['allocation_id'],'source':u['source_sha256'],'phase':record['phase'],'kind':record['kind'],'owned':owned if record['kind']=='kimi' else u['physical_pages']})

def released_hold(folder,identity,reservation):
    path=Path(folder)/'releases'/f'{identity}.json'
    if not path.exists():return False
    event=read_json(path)
    if event['reservation']!=identity or event['original_reservation_sha256']!=reservation['reservation_sha256'] or event.get('provider_refund_claim') is not False:raise kimi.IntegrityError('Invalid local-hold release')
    for name,digest in event['evidence']['proof_files'].items():
        if sha(name)!=digest:raise kimi.IntegrityError('Never-sent proof changed')
    return True

def checked_budget(folder):
    folder=Path(folder);path=folder/'ledger.json';proofs={p.stem:p for p in (folder/'reservations').glob('*.json')}
    if not path.exists():
        if (folder/'initialized.json').exists() or proofs or any((folder/'attempts').glob('*')) or any(not read_json(p).get('reused_historical_job') or read_json(p).get('shared_reservation') is not None for p in (folder/'results').glob('*.json')):raise kimi.IntegrityError('Shared ledger missing after recovery activity; no new allocation')
        return None
    ledger=read_json(path)
    if set(proofs)!=set(ledger['reservations']):raise kimi.IntegrityError('Shared reservations missing/extra; reconcile, never reset')
    for identity,item in ledger['reservations'].items():
        if sha(proofs[identity])!=item['reservation_sha256']:raise kimi.IntegrityError('Shared reservation proof changed')
        original=read_json(proofs[identity])
        if any(item.get(k)!=v for k,v in original.items() if k!='status'):raise kimi.IntegrityError('Shared reservation changed')
        if item.get('settlement_path') and sha(item['settlement_path'])!=item['settlement_sha256']:raise kimi.IntegrityError('Settlement evidence changed')
    return ledger

def scope_authorised(run,record,approval):
    if record['scope_sha256'] in approval.get('approved_scopes',[]):return True
    folder=budget_folder(run,approval);path=folder/'scopes'/f"{record['scope_sha256']}.json"
    return path.exists() and read_json(path)=={'approval_sha256':fingerprint(approval),'record':record}

def register_scope(run,record,approval,*,unit_verified=False):
    """Derived unit hashes under the immutable approved PDF/page scope; no new cap."""
    if not unit_verified:raise ValueError('Controller must verify sealed unit/draft before registration')
    unit=record['unit'];source=approval.get('sources',{}).get(unit['source_id'])
    if not source or source['sha256']!=unit['source_sha256'] or not set(unit['physical_pages'])<=set(source['physical_pages']):raise ValueError('Derived recovery outside frozen original/page scope')
    if record['kind'] not in ('kimi','mathpix') or record['phase'] not in ('convert','critic','review','extraction'):raise ValueError('Unsupported recovery phase')
    folder=budget_folder(run,approval);folder.mkdir(parents=True,exist_ok=True)
    with writer_lock(folder):
        path=folder/'scopes'/f"{record['scope_sha256']}.json";value={'approval_sha256':fingerprint(approval),'record':record}
        if path.exists() and read_json(path)!=value:raise ValueError('Registered scope changed')
        atomic_json(path,value)

def budget_summary(run,approval=None):
    folder=budget_folder(run,approval);d=checked_budget(folder)
    if d is None:return {'cap_usd':str((approval or {}).get('new_spend_cap_usd','0')),'exposure_usd':'0','actual_confirmed_usd':'0','unsettled_reserved_usd':'0','reservations':0}
    known=sum((Decimal(v['actual_usd']) for v in d['reservations'].values() if 'actual_usd' in v),Decimal(0))
    released=sum((Decimal(v['reserved_usd']) for k,v in d['reservations'].items() if released_hold(folder,k,v)),Decimal(0))
    unknown=sum((Decimal(v['reserved_usd']) for k,v in d['reservations'].items() if 'actual_usd' not in v and not released_hold(folder,k,v)),Decimal(0))
    return {'allocation_id':(approval or {}).get('allocation_id'),'cap_usd':d['cap_usd'],'exposure_usd':str(known+unknown),'actual_confirmed_usd':str(known),'unsettled_reserved_usd':str(unknown),'released_never_sent_holds_usd':str(released),'reservations':len(d['reservations']),'remaining_usd':str(Decimal(d['cap_usd'])-known-unknown),'counter_meaning':'Authorisations, not all confirmed submissions'}

def settle_confirmed(run,identity,approval,amount,evidence):
    """Only provider-confirmed settlement; never infer a refund from an error."""
    amount=Decimal(str(amount));evidence=Path(evidence)
    if not evidence.is_file() or amount<0:raise ValueError('Missing confirmed settlement evidence')
    folder=budget_folder(run,approval)
    with writer_lock(folder):
        path=folder/'ledger.json';d=checked_budget(folder);r=d['reservations'][identity]
        if amount>Decimal(r['reserved_usd']):raise kimi.IntegrityError('Provider charge exceeds shared reservation')
        if 'actual_usd' in r and Decimal(r['actual_usd'])!=amount:raise kimi.IntegrityError('Conflicting settlement')
        r.update(actual_usd=str(amount),settlement_path=str(evidence),settlement_sha256=sha(evidence),status='provider_settled');atomic_json(path,d)


def proposal(run,unit,phase,failure):
    kind=policy.fallback_kind(phase,failure);folder=Path(run)/'fallbacks'/(unit['id']+'-'+phase)
    record={'kind':kind,'phase':phase,'failure':failure,'unit':copy.deepcopy(unit),'attempt_limit':1,
            'status':'disabled_pending_explicit_scope_and_new_spend_approval','new_budget_usd':'0',
            'qualification':'Current provider metadata/privacy/prices and authenticated allowance must be checked before paid dispatch; historical limits are not authorisation'}
    record['scope_sha256']=fingerprint(record['unit']);path=folder/'proposal.json'
    if path.exists():
        previous=read_json(path)
        if previous!=record:raise ValueError('Fallback scope changed; preserve the prior proposal and create an explicit linked decision')
    else:atomic_json(path,record)
    return path

def reserve_budget(run,record,cost,approval):
    """One cross-provider run cap, additional to each adapter's existing ledger.

    An operator-approved *new* budget and exact scope are required. Uncertain
    calls stay reserved; no automatic retry or inferred refund.
    """
    if approval.get('allocation_id'):
        from .library_allocation import verify
        verify(approval)
    cost=Decimal(str(cost));cap=Decimal(str(approval.get('new_spend_cap_usd','0')))
    if approval.get('explicitly_approved') is not True or cap<=0 or not scope_authorised(run,record,approval):raise NotApproved('Paid recovery disabled: exact scope and a new total spend budget are not approved')
    if approval.get('provider_metadata_current') is not True:raise NotApproved('Current provider route/privacy/price qualification missing')
    if cost<=0 or cost>cap:raise NotApproved('Invalid/excessive per-call reservation')
    folder=budget_folder(run,approval);folder.mkdir(parents=True,exist_ok=True)
    with writer_lock(folder):
        path=folder/'ledger.json';ledger=checked_budget(folder) or {'approval_sha256':fingerprint(approval),'cap_usd':str(cap),'reservations':{}}
        if ledger['approval_sha256']!=fingerprint(approval) or Decimal(ledger['cap_usd'])!=cap:raise ValueError('Approved run budget changed; no reset')
        identity=reservation_identity(record,approval)
        if identity in ledger['reservations']:return identity,False
        for r in ledger['reservations'].values():
            if r.get('settlement_path') and sha(r['settlement_path'])!=r['settlement_sha256']:raise ValueError('Settlement evidence changed')
        exposure=sum(Decimal(v.get('actual_usd',v['reserved_usd'])) for k,v in ledger['reservations'].items() if not released_hold(folder,k,v))
        if exposure+cost>cap:raise NotApproved('Approved total new-spend budget exhausted')
        ledger['reservations'][identity]={'reserved_usd':str(cost),'status':'reserved_uncertain','at_epoch':time.time(),'scope':record['scope_sha256'],'kind':record['kind'],'draft_sha256':record.get('unit',{}).get('draft_sha256'),'unit_identity':{k:record.get('unit',{}).get(k) for k in ('source_id','source_sha256','physical_pages','subset_sha256')}}
        proof=folder/'reservations'/f'{identity}.json';atomic_json(proof,ledger['reservations'][identity]);ledger['reservations'][identity]['reservation_sha256']=sha(proof)
        atomic_json(path,ledger);return identity,True

def saved_result(run,identity,approval=None):
    path=budget_folder(run,approval)/'results'/f'{identity}.json'
    return read_json(path) if path.exists() else {'status':'uncertain_reserved','diagnostic':'No second paid request; reconcile the original adapter reservation/job first'}

def sync_kimi_settlements(run,cloud_run,approval):
    bill=Path(cloud_run)/'billing.json';shared=budget_folder(run,approval)/'ledger.json'
    if not bill.exists() or not shared.exists():return
    reservations=read_json(shared)['reservations']
    for charge in kimi.ledger(cloud_run).read()['reservations']:
        folder=(Path(cloud_run)/charge['folder']).resolve();identity=folder.name
        if identity in reservations and folder==(budget_folder(run,approval)/'attempts'/identity).resolve() and 'actual_cost_usd' in charge:
            settle_confirmed(run,identity,approval,charge['actual_cost_usd'],Path(cloud_run)/charge['settlement'])

def kimi_body(config,record):
    unit=record['unit'];draft=Path(unit['draft_path']).read_text() if record['phase'] in ('critic','review') else None
    if draft is not None and sha(unit['draft_path'])!=unit['draft_sha256']:raise kimi.IntegrityError('Fallback draft changed')
    task={'id':unit['id'],'source_id':unit['source_id'],'source_sha256':unit['source_sha256'],'pages':unit['physical_pages'],'operation':'review' if draft is not None else 'convert',
          'reason':'reasoning_exhaustion' if record['failure']=='reasoning_exhaustion' else 'mathematical_transcription' if record['failure']=='unresolved_passage' else 'incomplete_answer'}
    return task,kimi.build_body(config,task,unit['primary'],unit.get('secondary',''),unit.get('context',''),draft=draft,ranges=unit.get('draft_ranges'),assets=unit['cloud_images'])

def pause_guard(run):
    if (Path(run)/'pause.json').exists():
        from .chapter_glm import StopRun
        raise StopRun('Pause requested before paid admission; existing owned reservations remain consumed')

def run_kimi(run,record,cloud_run,approval,*,client_factory=kimi.KimiClient,observer=None):
    pause_guard(run)
    if record['kind']!='kimi':raise ValueError('Failure is not eligible for Kimi')
    config=read_json(Path(cloud_run)/'binding.json')['config'];task,body=kimi_body(config,record)
    identity=reservation_identity(record,approval)
    budget=budget_folder(run,approval);folder=budget/'attempts'/identity;prior=budget/'ledger.json'
    existing=checked_budget(budget)
    if existing and identity in existing['reservations'] and existing['reservations'][identity].get('draft_sha256')!=record['unit'].get('draft_sha256'):return {'status':'consumed_lineage_different_draft','diagnostic':'Reconcile prior phase; do not reset its allowance'}
    consumed=existing is not None and identity in existing['reservations']
    if consumed and (budget/'results'/f'{identity}.json').exists():
        result=saved_result(run,identity,approval)
        if result.get('candidate_tex') and sha(result['candidate_tex'])!=result.get('candidate_sha256'):raise kimi.IntegrityError('Saved recovered candidate changed')
        return result
    if consumed:
        # A sealed response can be applied after restart without another POST.
        if not (folder/'outcome.json').exists() or not (folder/'answer.txt').exists():return saved_result(run,identity,approval)
        result=read_json(folder/'outcome.json');answer=(folder/'answer.txt').read_text()
    else:
        if not scope_authorised(run,record,approval) or approval.get('explicitly_approved') is not True:raise NotApproved('Frozen scope not authorised')
        budget.mkdir(parents=True,exist_ok=True)
        with writer_lock(budget):
            if checked_budget(budget) is None:
                atomic_json(budget/'ledger.json',{'approval_sha256':fingerprint(approval),'cap_usd':approval['new_spend_cap_usd'],'reservations':{}})
        folder.mkdir(parents=True,exist_ok=True)
        if approval.get('allocation_id'):atomic_json(folder/'phase-authority.json',{'scope_sha256':record['scope_sha256'],'phase_identity':identity,'request_sha256':fingerprint(body),'approval_sha256':fingerprint(approval)})
        client=client_factory(cloud_run)
        if hasattr(client,'reconcile'):client.reconcile()
        if hasattr(client,'admit'):client.admit(body,folder)  # public route + live allowance, no generating request
        pause_guard(run)
        identity,fresh=reserve_budget(run,record,kimi.cost_bound(config,body),approval)
        if not fresh:return saved_result(run,identity,approval)
        if observer:observer()
        try:
            with writer_lock(Path(cloud_run)/'dispatch-ownership'):
                answer,result=client.dispatch(task,body,folder)
        except (kimi.IdentityError,kimi.IntegrityError):
            sync_kimi_settlements(run,cloud_run,approval);raise
        except Exception as exc:
            phase=read_json(folder/'transport-phase.json') if (folder/'transport-phase.json').exists() else {}
            if phase.get('phase')=='proven_not_sent':
                from .library_allocation import release_never_sent
                proof={str(folder/'transport-phase.json'):sha(folder/'transport-phase.json')}
                release_never_sent(budget,identity,{'disposition':'proven_not_sent','proof_files':proof,'reason':phase.get('reason')})
            out={'status':'proven_not_sent' if phase.get('phase')=='proven_not_sent' else 'failed_or_uncertain_consumed','diagnostic':client._redact(str(exc)) if hasattr(client,'_redact') else type(exc).__name__,'attempt_path':str(folder)}
            sync_kimi_settlements(run,cloud_run,approval)
            atomic_json(budget/'results'/f'{identity}.json',out);return out
    # Existing verified billing evidence, including failures, is authoritative.
    sync_kimi_settlements(run,cloud_run,approval)
    bill=Path(cloud_run)/'billing.json'
    if bill.exists():
        for charge in kimi.ledger(cloud_run).read()['reservations']:
            if (Path(cloud_run)/charge['folder']).resolve()==folder.resolve() and 'actual_cost_usd' in charge:
                settle_confirmed(run,identity,approval,charge['actual_cost_usd'],Path(cloud_run)/charge['settlement'])
    folder.mkdir(parents=True,exist_ok=True);(folder/'library-answer.txt').write_text(answer)
    out={'status':'failed_consumed','provider_record':result,'attempt_path':str(folder)}
    if result.get('status')=='complete_response':
        out.update(status='response_saved_unaccepted',answer_path=str(folder/'library-answer.txt'))
        try:
            if task['operation']=='review':
                from .focused_recovery import apply_focused
                from .library_repair import salvage_json
                base=Path(record['unit']['draft_path']).read_text();parsed=salvage_json(answer,record['unit']['draft_sha256']);revised,findings=apply_focused(base,json.dumps(parsed),record['unit']['draft_ranges'])
                (folder/'original.tex').write_text(base);(folder/'reviewed.tex').write_text(revised);atomic_json(folder/'findings.json',findings);(folder/'changes.diff').write_text(''.join(__import__('difflib').unified_diff(base.splitlines(True),revised.splitlines(True))));out['candidate_tex']=str(folder/'reviewed.tex')
                out['review_coverage']='Located findings only; full-scope attestation unavailable in this Kimi schema'
            else:
                from . import chapter_accuracy
                from scripts.simple_chapter_glm import extract_document
                document,info=chapter_accuracy.envelope(answer,extract_document);out['extraction']=info
                if document is not None and chapter_accuracy.complete_document(document):(folder/'candidate.tex').write_text(document);out['candidate_tex']=str(folder/'candidate.tex')
                else:out['status']='failed_no_complete_document'
        except (ValueError,KeyError,TypeError) as exc:out.update(status='invalid_candidate',diagnostic=str(exc))
    if out.get('candidate_tex'):out['candidate_sha256']=sha(out['candidate_tex'])
    atomic_json(budget/'results'/f'{identity}.json',out);return out


def run_mathpix(run,record,approval,*,client,poll_once=True):
    """One submission, durable provider ID; later calls perform GETs only."""
    pause_guard(run)
    if record['kind']!='mathpix':raise ValueError('Failure is not eligible for Mathpix')
    unit=record['unit'];subset=Path(unit['subset']);count=len(unit['physical_pages']);run=Path(run)
    if sha(subset)!=unit['subset_sha256']:raise ValueError('Affected PDF subset changed')
    rate=Decimal(str(approval.get('mathpix_price_per_page_usd','0')))
    if rate!=Decimal(mathpix.RATE_MICROUSD)/Decimal(1000000):raise NotApproved('Mathpix price absent/changed')
    from scripts import mathpix_comparison as adapter
    budget=budget_folder(run,approval)
    job={'source_id':unit['source_id'],'sha256':unit['source_sha256'],'physical_pages':unit['physical_pages'],'subset':str(subset),'subset_sha256':unit['subset_sha256'],
         'page_map':[{'subset_page':i+1,'original_physical_page':n} for i,n in enumerate(unit['physical_pages'])]}
    registry=adapter.ledger_read().get('keys',{}).get(client.key_id,{}).get('jobs',{})
    provider=registry.get(mathpix.job_identity(job))
    reused=provider is not None and provider.get('run')!=str(run)
    if reused:
        identity=reservation_identity(record,approval);fresh=False
    else:identity,fresh=reserve_budget(run,record,Decimal(count)*rate,approval)
    if not fresh and provider is None:return saved_result(run,identity,approval)
    if fresh:
        adapter.usage(run,client,'library-before-'+identity[:12])
        opts={'budget_id':'library-'+fingerprint(approval)}
        if approval.get('ledger_root'):opts['external_budget']={'ledger':str(budget/'ledger.json'),'approval_sha256':fingerprint(approval),'reservation':identity}
        provider=adapter.submit_once(run,opts,job,client)
    resultpath=budget/'results'/f'{identity}.json'
    out={'status':provider['status'],'provider_record':provider,'shared_reservation':None if reused else identity,'reused_historical_job':reused,'get_failures':0}
    if resultpath.exists():out['get_failures']=read_json(resultpath).get('get_failures',0)
    atomic_json(resultpath,out)  # durable even before GET polling
    if not provider.get('pdf_id'):return out
    if provider.get('run')!=str(run) and provider.get('outputs'):
        from .source_library import copy_verified
        source=Path(provider.get('output_run',provider['run']))/'jobs'/mathpix.job_identity(job)
        for p in source.rglob('*'):
            if p.is_file():copy_verified(p,run/'jobs'/mathpix.job_identity(job)/p.relative_to(source))
    try:
        status=client.get_json('pdf/'+provider['pdf_id']);folder=run/'jobs'/mathpix.job_identity(job)
        atomic_json(folder/('status-'+str(time.time_ns())+'.json'),status)
        if status.get('status')=='completed' and status.get('num_pages') not in (None,count):raise kimi.IntegrityError('Mathpix page identity/count mismatch')
        if status.get('status')=='error':out.update(status='provider_error',provider_status=status)
        elif status.get('status')=='completed':
            conversion=client.get_json('converter/'+provider['pdf_id']);atomic_json(folder/'conversion-status.json',conversion)
            states=conversion.get('conversion_status',{}).values()
            if any((v.get('status') if isinstance(v,dict) else v) in ('received','pending','processing','running','queued','converting') for v in states):out['status']='awaiting_outputs'
            else:
                outputs=adapter.download_outputs(run,{'compile_pdf':False},job,provider,client)
                required=('tex.zip','lines.mmd.json');missing=[x for x in required if outputs.get(x,{}).get('status')!='downloaded']
                out.update(status='outputs_incomplete' if missing else 'downloaded',outputs=outputs,missing=missing,job_folder=str(folder))
                provider.update(status=out['status'],outputs={**provider.get('outputs',{}),**outputs},output_run=str(run),estimated_incurred_microusd=count*mathpix.RATE_MICROUSD)
                adapter.update_ledger(client,mathpix.job_identity(job),provider)
                adapter.usage(run,client,'library-after-'+identity[:12])
        else:out['status']='polling_existing_job'
    except kimi.IntegrityError:raise
    except Exception as exc:
        previous=read_json(resultpath);errors=previous.get('get_failures',0)+1
        out.update(status='retrieval_blocked' if errors>=3 else 'polling_existing_job',get_failures=errors,diagnostic=client.redact(str(exc)))
    atomic_json(resultpath,out);return out


def direct_mathpix_tex(run,folder,zip_bytes,compiler_image,*,assigned_pages,returned_pages,compile_pdf=False):
    if assigned_pages!=returned_pages:raise ValueError('Mathpix direct TeX scope differs; cannot select as the complete assigned unit')
    from scripts.mathpix_comparison import compile_direct
    entries=mathpix.safe_zip(zip_bytes)
    if not compile_pdf:
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        for name,data in entries.items():
            dest=folder/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        return {'status':'not_requested','content_status':'requires_dependency_and_coverage_assessment','source_directory':str(folder)}
    # Existing isolated direct-TeX compiler does not invoke a GLM converter.
    return compile_direct(Path(run),Path(folder),compiler_image,entries)
