"""One explicit incremental allocation, shared by linked library runs.

Reuses library_fallbacks' monetary/proof ledger and existing provider ledgers.
No account/key limits are changed. Old ledgers are never edited.
"""
from pathlib import Path
from decimal import Decimal
import copy,time
from .common import read_json,atomic_json,sha,fingerprint,writer_lock
from .source_library import copy_verified
from . import kimi_escalation as kimi
AUTH_ID='library-next30-20261108-fresh7-v2'

def create(project,authorization_path,sources,config,parent):
    project=Path(project);authorization=read_json(authorization_path)
    if authorization['authorization_id']!=AUTH_ID or authorization['revision']!=2 or authorization['new_combined_budget_usd']!='7.00':raise ValueError('Wrong revision/allocation authority')
    registry=project/'results/library-allocations';registry.mkdir(parents=True,exist_ok=True);root=registry/AUTH_ID
    with writer_lock(registry):
        marker=registry/(AUTH_ID+'.json')
        if marker.exists():
            record=read_json(marker)
            if not (root/'allocation.json').exists() or sha(root/'allocation.json')!=record['allocation_sha256']:raise kimi.IntegrityError('Allocation record missing/changed; never recreate budget')
            frozen=read_json(root/'allocation.json')
            if frozen['authorization_sha256']!=sha(authorization_path) or frozen['sources']!=sources:raise kimi.IntegrityError('Existing allocation identity/scope changed')
            for name,digest in frozen['baseline_files'].items():
                if sha(root/name)!=digest:raise kimi.IntegrityError('Allocation baseline changed')
            return root,read_json(root/'approval.json')
        if root.exists():raise kimi.IntegrityError('Unregistered partial allocation; reconcile without creating a second budget')
        root.mkdir();copy_verified(authorization_path,root/'BUDGET-AUTHORIZATION.json')
        baseline=kimi.history_snapshot(project,exclude=[root]);atomic_json(root/'prior-billing.json',baseline)
        # This is a new authorized task allocation; historical amounts are NOT
        # deducted from its $7, but the provider client still checks them globally.
        cfg=copy.deepcopy(config);cfg.update(pilot_budget_usd='7.00',paid_limits=None,call_allowance_policy='registered_source_phases',allocation_id=AUTH_ID)
        approval={'explicitly_approved':True,'allocation_id':AUTH_ID,'new_spend_cap_usd':'7.00','ledger_root':str(root/'shared'),'cloud_run':str(root),'sources':sources,'provider_metadata_current':True,'mathpix_price_per_page_usd':'0.005','no_per_provider_allocation':True}
        atomic_json(root/'approval.json',approval)
        atomic_json(root/'binding.json',{'config':cfg,'prior_billing':{'path':str(root/'prior-billing.json'),'sha256':sha(root/'prior-billing.json')},'authorization_sha256':sha(authorization_path),'parent_run':str(parent),'source_scope_sha256':fingerprint(sources)})
        atomic_json(root/'authorisation.json',{'binding_sha256':sha(root/'binding.json'),'accepted_pilot_budget_usd':'7.00','authority':AUTH_ID})
        baseline_files={name:sha(root/name) for name in ['BUDGET-AUTHORIZATION.json','prior-billing.json','approval.json','binding.json','authorisation.json']}
        atomic_json(root/'allocation.json',{'authorization_id':AUTH_ID,'authorization_sha256':sha(authorization_path),'sources':sources,'new_cap_usd':'7.00','parent_run':str(parent),'baseline_files':baseline_files,'created_epoch':time.time(),'historical_spend_deducted':False,'old_unused_capacity_added':False})
        atomic_json(marker,{'allocation':str(root),'allocation_sha256':sha(root/'allocation.json')})
        # Initialize once, while registry ownership is held; deletion cannot renew.
        kimi.ledger(root,create=True)
        from .library_fallbacks import initialize_allocation_budget
        initialize_allocation_budget(root/'shared',approval)
        return root,approval

def verify(approval):
    root=Path(approval['cloud_run']);record=read_json(root.parent/(approval['allocation_id']+'.json'))
    if record['allocation_sha256']!=sha(root/'allocation.json') or read_json(root/'approval.json')!=approval:raise kimi.IntegrityError('Allocation registry/approval mismatch')
    for name,digest in read_json(root/'allocation.json')['baseline_files'].items():
        if sha(root/name)!=digest:raise kimi.IntegrityError('Allocation baseline mutated')
    if not (root/'shared/ledger.json').exists() or not (root/'billing.json').exists():raise kimi.IntegrityError('Initialized allocation ledger disappeared; no reset')
    return root

def release_never_sent(folder,identity,evidence,*,approval=None):
    """Append a local-hold cancellation event, never a provider refund or old-ledger rewrite."""
    folder=Path(folder)
    with writer_lock(folder):
        ledger=read_json(folder/'ledger.json');r=ledger['reservations'][identity]
        if 'actual_usd' in r:raise ValueError('A settled charge cannot be cancelled')
        if evidence.get('disposition')!='proven_not_sent' or not evidence.get('proof_files'):raise ValueError('No positive never-sent proof')
        for path,digest in evidence['proof_files'].items():
            if sha(path)!=digest:raise kimi.IntegrityError('Never-sent evidence changed')
        event={'reservation':identity,'original_reservation_sha256':r['reservation_sha256'],'released_local_hold_usd':r['reserved_usd'],'provider_refund_claim':False,'evidence':evidence}
        out=folder/'releases'/f'{identity}.json'
        if out.exists():
            if read_json(out)!=event:raise kimi.IntegrityError('Release event changed')
        else:atomic_json(out,event)
        return event

def reconcile_old(parent,destination,code_snapshot):
    parent=Path(parent);destination=Path(destination);destination.mkdir(parents=True,exist_ok=True);code_snapshot=Path(code_snapshot)
    old_binding=read_json(parent/'binding.json');bill=read_json(parent/'billing.json');shared=parent/'fallback-budget';ledger=read_json(shared/'ledger.json');events=[]
    ids=['751b0d0ac717ee9df438f75e200ce84cb36866be32330034ac6ad4b4cb8bbcd6','d3e07ad8ed73805b81c05491c8b263c4227ae968a3c5a942e9e36cd50e3bb13e']
    for name in ('probe/cloud_critic.py','probe/kimi_escalation.py','probe/library_fallbacks.py'):
        if sha(code_snapshot/name)!=old_binding['code'][name]:raise ValueError('Cannot establish exact old control flow')
    old_code=(code_snapshot/'probe/cloud_critic.py').read_text();client_code=(code_snapshot/'probe/kimi_escalation.py').read_text()
    assert "else (2 if phase=='readiness' else 16)" in old_code and client_code.index('identity=self.ledger.reserve')<client_code.index("self._http('POST'")
    if len(bill['reservations'])!=16 or old_binding['config'].get('paid_limits') is not None:raise ValueError('Old ceiling evidence differs')
    for identity in ids:
        result_path=shared/'results'/f'{identity}.json';result=read_json(result_path);attempt=shared/'attempts'/identity
        if result.get('diagnostic')!='Paid readiness/trial call ceiling exhausted':raise ValueError('Different failure; do not cancel')
        if any((attempt/name).exists() for name in ['request.json','reservation-link.json','response.raw','outcome.json']):raise ValueError('Possible transport evidence; keep hold')
        if any((parent/r['folder']).resolve()==attempt.resolve() for r in bill['reservations']):raise ValueError('Provider reserved this attempt; keep hold')
        proof={str(p):sha(p) for p in [parent/'binding.json',parent/'billing.json',shared/'ledger.json',shared/'reservations'/f'{identity}.json',result_path,attempt/'admission.json']}
        proof.update({str(code_snapshot/name):sha(code_snapshot/name) for name in ['probe/cloud_critic.py','probe/kimi_escalation.py','probe/library_fallbacks.py']})
        event={'reservation':identity,'disposition':'proven_not_sent','local_hold_release_usd':ledger['reservations'][identity]['reserved_usd'],'original_reservation_sha256':ledger['reservations'][identity]['reservation_sha256'],'proof_files':proof,'reason':'Exact bound Ledger.reserve raised at16 before provider reservation creation, request.json, reservation-link.json and HTTP POST. Positive diagnostic/control-flow proof plus the complete16-entry provider ledger.','provider_refund_claim':False,'old_ledger_unchanged':True,'new_allocation_credit_usd':'0'}
        path=destination/(identity+'.json')
        if path.exists() and read_json(path)!=event:raise ValueError('Historical release event differs')
        atomic_json(path,event);events.append(event)
    atomic_json(destination/'effective-old-accounting.json',{'reported_kimi_usd':'1.219735230','retained_mathpix_hold_usd':'0.005','released_proven_not_sent_local_holds_usd':str(sum((Decimal(x['local_hold_release_usd']) for x in events),Decimal(0))),'raw_old_ledger':str(shared/'ledger.json'),'raw_old_ledger_unchanged':True,'events':[str(destination/(x['reservation']+'.json')) for x in events],'added_to_new_allocation_usd':'0'})
    return events
