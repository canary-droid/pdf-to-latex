"""Shared serial, sealed experiment executor for visual recovery and text criticism.

Reuses LocalClient, project locking, durable atomic records and attempt seals.
Historical trial runners are not rebound. Every reservation consumes its budget.
"""
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import time
import uuid

from .common import atomic_json, read_json, sha, fingerprint, files_manifest, check_manifest
from .local_model import LocalClient, ProbeError, probe_model
from .saved_pages import converter_idle
from .batch_review import IdentityError, IntegrityError, seal_outcome
from .recovery import (VISUAL_SCHEMA, ValidationError, parse_validate, validate_visual,
    single_outer_fence,response_data,diagnose,recovery_method,feedback_request,reserve_budget,compatible_fragment,preserve_substance,export_failure)
from .paired_inputs import SCHEMA as LEGACY_SCHEMA
from . import text_critic

CODE=('experiment.py','recovery_trial.py','recovery.py','text_critic.py','sciwrite_subset.py',
      'bibliography.py','tex_compile.py','evaluation_export.py','portable_export.py','local_model.py',
      'page_review.py','common.py','saved_pages.py','paired_inputs.py','batch_review.py','critic_overnight.py',
      'critic_pilot.py','cloud_critic.py','critic_anchors.py','critic_context.py','critic_route.py',
      'book_review.py','batch_inputs.py','focused_review.py')


def code_hashes():return {n:sha(Path(__file__).parent/n) for n in CODE}
def now():return datetime.now(timezone.utc).isoformat()
def new_path(root,prefix):return Path(root)/'runs'/(prefix+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6])
def seal(path):atomic_json(Path(path)/'manifest.json',files_manifest(path))


def verify_seal(path,digest=None,name='manifest.json'):
    path=Path(path)
    if digest and sha(path/name)!=digest:raise IntegrityError('Changed manifest: '+str(path))
    if not check_manifest(path,read_json(path/name)+[{'path':name,'sha256':sha(path/name)}]):raise IntegrityError('Changed evidence: '+str(path))


class InputGuard:
    def __init__(self,hashes):
        self.hashes=hashes;self.stats={};self.check(full=True)
    def check(self,full=False):
        for name,digest in self.hashes.items():
            p=Path(name)
            if p.is_symlink() or not p.is_file():raise IntegrityError('Missing/symlink input: '+name)
            s=p.stat();stamp=(s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_ino)
            if full or self.stats.get(name)!=stamp:
                if sha(p)!=digest:raise IntegrityError('Changed consumed input: '+name)
            self.stats[name]=stamp


def verify_preview(preview):
    verify_seal(preview);meta=read_json(preview/'preview.json')
    if meta['code_sha256']!=code_hashes():raise IntegrityError('Code changed; incompatible prepared protocol. Preserve old attempts and prepare a new version explicitly.')
    units=read_json(preview/'units.json')
    if len({u['id'] for u in units})!=len(units):raise IntegrityError('Duplicate prepared unit')
    if meta.get('book_review'):
        from .book_review import validate_preparation
        validate_preparation(preview,meta,units)
    return meta,units


def initialize(preview,out):
    meta,units=verify_preview(preview);out.mkdir(parents=True,exist_ok=False)
    binding={'preview':str(preview),'manifest_sha256':sha(preview/'manifest.json'),
        'config':meta['config'],'limits':meta['limits'],'code_sha256':code_hashes()}
    atomic_json(out/'binding.json',binding)
    state={'status':'prepared_offline','created_at':now(),'binding_sha256':fingerprint(binding),
        'elapsed_seconds':0.0,'active_since_epoch':None,'calls':[], 'gate':None,'readiness':[],
        'units':{u['id']:{'status':'unavailable' if u.get('unavailable') else 'pending',
                       'reason':u.get('unavailable')} for u in units},
        'acceptance':'UNACCEPTED','connection_streak':0}
    atomic_json(out/'state.json',state);return state


def validator(spec,data):
    if spec['kind']=='omission':
        from .book_review import OMISSION_SCHEMA,validate_omissions
        return OMISSION_SCHEMA,lambda v:validate_omissions(v,data)
    if spec['kind']=='critic':return text_critic.schema_for(data),lambda v:text_critic.validate(v,data)
    legacy=spec['kind']=='diagnostic'
    return (LEGACY_SCHEMA if legacy else VISUAL_SCHEMA),lambda v:validate_visual(v,data,legacy)


def validate_completion(answer,spec,data,model):
    if answer.get('actual_model')!=model:raise IdentityError('Exact response model missing or different')
    if answer.get('finish_reason')!='stop':raise ValidationError('malformed_completion',[{'path':'finish_reason','message':'expected stop'}])
    schema,validate=validator(spec,data)
    mechanical=None
    try:value=parse_validate(answer.get('content'),schema,validate)
    except ValidationError:
        content=single_outer_fence(answer.get('content'))
        if content is None:raise
        value=parse_validate(content,schema,validate)
        mechanical={'method':'single_outer_markdown_fence','original_sha256':fingerprint(answer['content']),
                    'transformed_content':content,'transformed_sha256':fingerprint(content)}
    result={'status':'completed','answer':value,'mechanical_recovery':mechanical,'acceptance':'UNACCEPTED',
        'response_validation':'passed',
        'usage':answer.get('usage',{}),'latency_seconds':answer.get('latency_seconds'),
        'source_fidelity':'unassessed','mathematical_correctness':'unassessed'}
    if spec['kind']=='critic':
        result['findings']=text_critic.located_findings(value,data)
        result['assessment']='insufficient_context' if value['coverage']=='insufficient_context' else 'incomplete_coverage' if value['coverage']=='incomplete' else 'findings' if value['findings'] else 'no_finding'
        if data.get('protocol') and (value['context_needed'] or any(f['context_required'] for f in value['findings'])):
            result['assessment']='insufficient_context'
    elif spec['kind']=='omission':
        result['export_checks']=[{'status':'deferred_missing_content_insertion','reason':'No recognized target: explicit insertion/assembly assessment required'} for _ in value['proposals']]
        result['compilation']=[{'status':'not_attempted_deferred_insertion','proposal_index':i} for i,_ in enumerate(value['proposals'])]
    else:
        byid={b['id']:b for b in data['blocks']}
        result['export_checks']=[compatible_fragment(p,byid[p['block_ids'][0]],spec['kind']=='diagnostic') for p in value['proposals']]
    return result


def finish_completion(answer,spec,data,model,folder,compiler_image=None,previous_failure=None,method=None):
    """The same applicable validation chain for dispatch and crash reconciliation."""
    field_patch=None
    if spec['kind']=='critic' and data.get('protocol')=='critic-anchors-v3' and previous_failure and method=='json_feedback':
        from .critic_anchors import apply_field_repair
        if answer.get('actual_model')!=model:raise IdentityError('Exact response model missing or different')
        if answer.get('finish_reason')!='stop':raise ValidationError('malformed_completion',[{'path':'finish_reason','message':'expected stop'}])
        assembled,field_patch=apply_field_repair(answer.get('content'),previous_failure,data)
        outcome=validate_completion({**answer,'content':json.dumps(assembled)},spec,data,model)
        outcome['field_repair']=field_patch
    else:outcome=validate_completion(answer,spec,data,model)
    if spec['kind']=='critic' and data.get('protocol')=='critic-anchors-v3':
        outcome['request_binding']={k:data[k] for k in ('protocol','group_id','candidate_sha256','draft_sha256')}
        outcome['request_binding']['input_sha256']=fingerprint(data)
    anchor=(previous_failure or {}).get('export_repair_anchor')
    if anchor:
        outcome['substance_check']=preserve_substance(anchor['content'],outcome['answer'],'export_feedback',anchor['repair_indices'])
    elif previous_failure and method=='json_feedback' and spec['kind']=='critic':
        outcome['substance_check']=text_critic.preserve_quote_repair(previous_failure,outcome['answer'],data,model)
    elif previous_failure and method in ('json_feedback','compiler_feedback','export_feedback'):
        outcome['substance_check']=preserve_substance(previous_failure.get('content'),outcome['answer'],method,
            previous_failure.get('repair_indices'))
    elif spec.get('condition')=='feedback':
        outcome['substance_check']=preserve_substance(spec.get('recovery_source_content'),outcome['answer'],'json_feedback')
    if spec['kind']=='visual':
        failure=export_failure(outcome,data,answer.get('content'))
        outcome['compilation']=[{'proposal_index':i,
            'status':'not_compiled_export_validation' if check['status'] not in ('supported','wrapper_required') else 'not_run_compiler_unavailable' if not compiler_image else 'deferred_until_export_repair'}
            for i,check in enumerate(outcome['export_checks'])]
        if not failure and compiler_image:
            from .evaluation_export import compiler_checks
            build=Path(folder)/'tex-checks'
            if build.exists():build=Path(folder)/('tex-checks-reconcile-'+uuid.uuid4().hex)
            failure=compiler_checks(outcome,data,build,compiler_image)
        if failure:
            if anchor:failure['export_repair_anchor']=anchor
            outcome.update(status='failed',failure=failure)
    return outcome


def repair_seed(preview,meta,parent,call_id):
    path=meta.get('repair_derivative',{}).get('seeds',{}).get(parent)
    if path:
        seed=read_json(preview/path)
        if seed['inherited_call']==call_id:return seed
    return None


def critic_failure_diagnostics(outcome,spec,data,model,prior=None):
    if spec['kind']!='critic' or 'failure' not in outcome:return
    fail=outcome['failure'];diagnostics=text_critic.rejected_diagnostics(fail,data,model)
    outcome['provisional_diagnostics']=diagnostics
    if data.get('protocol'):
        origin=(prior or {}).get('anchor_repair_origin')
        if origin:fail['anchor_repair_origin']=origin
        elif fail.get('finish_reason')=='stop' and fail.get('actual_model')==model:
            fail['anchor_repair_origin']={k:fail.get(k) for k in ('content','actual_model','finish_reason','errors')}
    if diagnostics['quote_feedback']:fail['critic_quote_feedback']=diagnostics['quote_feedback']
    anchor=(prior or {}).get('critic_repair_anchor')
    if anchor:fail['critic_repair_anchor']=anchor
    elif diagnostics['quote_feedback']:
        fail['critic_repair_anchor']={k:fail[k] for k in ('content','actual_model','finish_reason')}


def previous_failure(out,preview,meta,parent,call_id):
    if not call_id:return None
    outcome=read_json(out/'calls'/call_id/'outcome.json')
    seed=repair_seed(preview,meta,parent,call_id)
    return seed['failure'] if seed else outcome.get('failure')


def apply_repair_seeds(preview,state,meta):
    for parent in meta.get('repair_derivative',{}).get('allowed_units',[]):
        record=state['units'][parent]
        seed=repair_seed(preview,meta,parent,record.get('last_call'))
        if seed:
            record.update(status='repair_pending',failure_kind=seed['failure']['kind'])


def ready(root,config,out,vision=False,client_factory=LocalClient):
    """Explicit operator operation. Text critics do not run/require image probes."""
    out.mkdir(parents=True,exist_ok=False);atomic_json(out/'converter-exit.json',converter_idle(root))
    client=client_factory(config['endpoint'],model=config['model'],timeout=120,max_tokens=2048)
    if vision:
        cases=read_json(Path(root)/'fixtures/vision/manifest.json')
        if isinstance(cases,dict):cases=cases['cases']
        for c in cases:
            p=Path(root)/'fixtures/vision'/Path(c['image_path']).name
            if sha(p)!=c['sha256']:raise IntegrityError('Vision fixture changed')
            c['image_path']=str(p)
        caps=probe_model(client,out/'model',cases)
        if caps['model_discovery'].get('selected_model')!=config['model']:raise IdentityError('Readiness model mismatch')
        if caps['text']['status']!='passed' or caps['vision']['status']!='qualified':raise ValueError('Require Text: passed AND vision: qualified')
        if caps['strict_json']['status'] not in ('passed','unsupported'):raise ValueError('Unexpected JSON preflight failure')
        for p in (out/'model').glob('attempts/*/response.raw'):
            try:r=read_json(p)
            except (ValueError,OSError):continue
            if isinstance(r,dict) and r.get('model') is not None and r['model']!=config['model']:raise IdentityError('Failed/successful preflight response changed model')
        summary={'text':'passed','vision':'qualified','strict_json':caps['strict_json']['status']}
    else:
        discovery=client.discover_model(out/'model')
        if discovery['selected_model']!=config['model']:raise IdentityError('Text readiness discovery mismatch')
        answer=client.chat([{'role':'user','content':'Reply with exactly TEXT_READY and no other text.'}],out/'model','text_readiness')
        if answer['actual_model']!=config['model']:raise IdentityError('Text readiness response mismatch')
        if answer['content'].strip()!='TEXT_READY':raise ValueError('Text readiness did not return expected content')
        atomic_json(out/'text-response.json',answer);summary={'text':'passed','vision':'not_requested_text_only'}
    atomic_json(out/'readiness.json',{'config':config,'finished_at':now(),**summary});seal(out)
    print('Readiness:',out,'Text: passed ; vision:',summary['vision'],flush=True)
    return out


def check_readiness(path,config,vision):
    verify_seal(path);r=read_json(path/'readiness.json')
    if r['config']!=config or r['text']!='passed' or (vision and r['vision']!='qualified'):raise IdentityError('Readiness endpoint/model/profile does not match')
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(r['finished_at'])).total_seconds()
    if not 0<=age<=3600:raise ValueError('Readiness must be fresh within one hour; run the documented readiness command')


def reconcile(out,state,units,preview):
    meta=read_json(preview/'preview.json')
    expected={u['id']:u for u in units}
    if set(state['units'])!=set(expected):raise IntegrityError('Changed unit ledger')
    folders=out/'calls';actual={p.name for p in folders.iterdir()} if folders.exists() else set()
    if actual-{c['id'] for c in state['calls']}:raise IntegrityError('Unregistered call reservation')
    if [c['id'] for c in state['calls']]!=[f'{i+1:04d}' for i in range(len(state['calls']))]:raise IntegrityError('Call reservation order/membership changed')
    prior_by_parent={}
    for c in state['calls']:
        d=folders/c['id'];spec=expected[c['parent']]
        if not d.exists():
            if c['status']!='in_flight_unknown':raise IntegrityError('Committed call disappeared')
            # Reservation was durable before mkdir; consume it, do not retransmit.
            d.mkdir(parents=True);atomic_json(d/'reservation.json',c)
        reservation=read_json(d/'reservation.json')
        for key in ('id','parent','method','request_sha256','reserved_at','previous_call','baseline_request_sha256','data_sha256'):
            if reservation.get(key)!=c.get(key):raise IntegrityError('Durable call reservation changed: '+key)
        if c.get('previous_call')!=prior_by_parent.get(c['parent']):raise IntegrityError('Recovery parent chain changed')
        baseline=read_json(preview/spec['request'])
        if c.get('baseline_request_sha256')!=fingerprint(baseline):raise IntegrityError('Original parent request changed')
        prior_by_parent[c['parent']]=c['id']
        if c.get('seal_sha256'):verify_seal(d,c['seal_sha256'],'seal.json')
        elif (d/'outcome.json').exists():
            if not (d/'seal.json').exists():atomic_json(d/'seal.json',files_manifest(d))
            verify_seal(d,None,'seal.json')
        else:
            outcome={'status':'interrupted','failure':{'kind':'unknown_in_flight','errors':[{'path':'$','message':'No committed outcome; reserved call consumed, no blind retry'}]},'acceptance':'UNACCEPTED'}
            prior=previous_failure(out,preview,meta,c['parent'],c.get('previous_call'))
            if (d/'assistant-response.json').exists():
                try:
                    body=read_json(d/'request.json');data=read_json(d/'input.json') if (d/'input.json').exists() else read_json(preview/spec['data'])
                    outcome=finish_completion(read_json(d/'assistant-response.json'),spec,data,body['model'],d,
                        state.get('compiler_image'),prior,c['method'])
                except (ValueError,TypeError,KeyError) as exc:
                    outcome={'status':'failed','failure':diagnose(exc,response_data(d),read_json(preview/'preview.json')['config']['model']),'acceptance':'UNACCEPTED'}
            elif list(d.glob('attempts/*/record.json')):
                ev=response_data(d);model=read_json(preview/'preview.json')['config']['model']
                failure=diagnose(ProbeError('Interrupted raw response'),ev,model)
                if failure['kind']=='identity':outcome={'status':'failed','failure':failure,'acceptance':'UNACCEPTED'}
            if 'failure' in outcome and (prior or {}).get('export_repair_anchor'):
                outcome['failure']['export_repair_anchor']=prior['export_repair_anchor']
            critic_failure_diagnostics(outcome,spec,read_json(d/'input.json') if (d/'input.json').exists() else read_json(preview/spec['data']),meta['config']['model'],prior)
            seal_outcome(d,outcome)
        outcome=read_json(d/'outcome.json')
        if c.get('data_sha256'):
            data=read_json(d/'input.json')
            if fingerprint(data)!=c['data_sha256']:raise IntegrityError('Reserved input changed')
            from .critic_anchors import check_data
            check_data(data)
            original=read_json(preview/spec['data'])
            if data['targets']!=original['targets']:raise IntegrityError('Target text/coverage changed in follow-up')
        if (d/'request.json').exists():
            body=read_json(d/'request.json')
            if fingerprint(body)!=c['request_sha256']:raise IntegrityError('Reserved request changed')
            if c['method']=='baseline' and body!=baseline:raise IntegrityError('Baseline differs from prepared request')
            for sent in d.glob('attempts/*/request.json'):
                if read_json(sent)['body']!=body:raise IntegrityError('Actual outgoing request changed')
        c.update(status=outcome['status'],seal_sha256=sha(d/'seal.json'))
        state['units'][c['parent']].update(status=outcome['status'],last_call=c['id'],failure_kind=outcome.get('failure',{}).get('kind'))
        if outcome.get('failure',{}).get('kind') in ('identity','integrity'):
            state['status']='stopped_'+outcome['failure']['kind']
    apply_repair_seeds(preview,state,meta)


def gate_result(state,units,policy,out):
    selected=[u for u in units if u.get('gate')]
    if any(state['units'][u['id']]['status']=='pending' for u in selected):return None
    if not selected:return {'passed':False,'reason':'empty gate'}
    final=sum(state['units'][u['id']]['status']=='completed' for u in selected)
    first=0;complete_coverage=0
    for u in selected:
        calls=[c for c in state['calls'] if c['parent']==u['id']]
        if calls and calls[0]['status']=='completed':first+=1
        if state['units'][u['id']]['status']=='completed':
            o=read_json(out/'calls'/state['units'][u['id']]['last_call']/'outcome.json')
            if o.get('assessment') not in ('insufficient_context','incomplete_coverage'):complete_coverage+=1
    return {'passed':final>=policy['minimum_final'] and first>=policy['minimum_first'] and complete_coverage>=policy['minimum_coverage'],
        'first_attempt_valid':first,'final_valid':final,'complete_claimed_coverage':complete_coverage,'units':len(selected),
        'criteria':policy,'meaning':'Technical usability/quote/coverage only; not proof every proposal is exportable, compiled or mathematically correct'}


def execute(root,out,*,stage,readiness,resume=False,client_factory=LocalClient,clock=time.monotonic,wall=time.time,compiler_image=None):
    binding=read_json(out/'binding.json');state=read_json(out/'state.json');preview=Path(binding['preview'])
    if state['status']!='prepared_offline' and not resume:raise ValueError('Use explicit --resume for an existing execution')
    if fingerprint(binding)!=state['binding_sha256'] or sha(preview/'manifest.json')!=binding['manifest_sha256']:raise IntegrityError('Run/preview binding changed')
    meta,units=verify_preview(preview)
    overnight=meta.get('overnight')
    pilot=meta.get('critic_pilot')
    route=meta.get('critic_route')
    book=meta.get('book_review')
    if book and compiler_image!=book['compiler_image']:raise IntegrityError('Owned-page review requires its sealed compiler image')
    if route:
        from . import critic_route
        critic_route.validate_protocol(meta,units)
        critic_route.validate_linked(out,preview,meta,state)
        if stage!='route':raise ValueError('Use the candidate critic route launcher')
    elif stage=='route':raise ValueError('No candidate critic route preparation')
    if pilot:
        from .critic_pilot import validate_arm,validate_inheritance
        validate_arm(meta,units)
        validate_inheritance(out,preview,meta,state)
        if stage!='pilot':raise ValueError('Use the explicit critic-pilot launcher')
    elif stage=='pilot':raise ValueError('No frozen critic-pilot scope')
    if overnight:
        from .critic_overnight import validate_protocol
        validate_protocol(meta,units)
        if stage!='overnight':raise ValueError('Use the frozen overnight controller for both stages')
    elif stage=='overnight':raise ValueError('No frozen overnight protocol')
    if binding['code_sha256']!=code_hashes() or binding['config']!=meta['config'] or binding['limits']!=meta['limits']:raise IntegrityError('Changed runtime/settings')
    guard=InputGuard({**meta['source_hashes'],**{str(preview/e['path']):e['sha256'] for e in files_manifest(preview)}})
    if overnight or pilot or route or book:
        guard.hashes.update({str(Path(__file__).parent/n):digest for n,digest in meta['code_sha256'].items()})
        guard.check()
    repair=meta.get('repair_derivative')
    continuation=meta.get('continuation_derivative')
    if continuation and stage!='continue':raise ValueError('This continuation permits only its pending units with --stage continue')
    if repair:
        if stage!='gate':raise ValueError('This derivative permits only its selected repair units with --stage gate; pending baselines are not authorized')
    linked=repair or continuation
    if linked:
        if compiler_image!=linked['compiler_image']:raise IntegrityError('Derivative requires the inherited qualified compiler image')
        inherited=read_json(preview/linked['inherited_state'])
        count=len(inherited['calls'])
        if state['calls'][:count]!=inherited['calls']:raise IntegrityError('Inherited call ledger changed')
        if state['elapsed_seconds']<inherited['elapsed_seconds']:raise IntegrityError('Inherited time budget reset')
        for identity,record in inherited['units'].items():
            if identity not in linked['allowed_units'] and state['units'].get(identity)!=record:
                raise IntegrityError('Out-of-scope inherited/pending unit changed')
        if any(c['parent'] not in linked['allowed_units'] for c in state['calls'][count:]):
            raise IntegrityError('Out-of-scope derivative call')
    reconcile(out,state,units,preview)
    if state['active_since_epoch'] is not None:
        state['elapsed_seconds']+=max(0,wall()-state['active_since_epoch']);state['active_since_epoch']=None
    def elapsed(active_elapsed):
        # This opt-in protocol has one wall deadline from first dispatch, including pauses.
        # Derive it from the durable, sealed reservation, never a renewed session timer.
        if overnight and state['calls']:
            began=datetime.fromisoformat(state['calls'][0]['reserved_at']).timestamp()
            return max(active_elapsed,wall()-began)
        if overnight:return 0.0
        return active_elapsed
    state['elapsed_seconds']=elapsed(state['elapsed_seconds'])
    if state['elapsed_seconds']>=meta['limits']['admission_seconds']:
        state['status']='budget_exhausted'
    if state['status'].startswith('stopped_') or state['status'] in ('gate_failed','budget_exhausted','completed','completed_with_failures','repair_completed','repair_unresolved'):
        atomic_json(out/'state.json',state);print('No dispatch:',state['status']);return 2
    if compiler_image!=state.get('compiler_image',compiler_image):raise IntegrityError('Compiler image cannot change during resume')
    state['compiler_image']=compiler_image
    diagnostic=meta['kind']=='diagnostic'
    if meta.get('config',{}).get('diagnostic_followup_only') and stage!='gate':raise ValueError('This bounded critic follow-up admits only its eight-unit gate')
    if stage not in ('gate','overnight','pilot','route') and not diagnostic and not (state.get('gate') or {}).get('passed'):raise ValueError('The frozen technical gate must pass first')
    if meta['kind']=='critic' and stage=='continue':raise ValueError('Use explicit critic development and reserved stages')
    if meta['kind']!='critic' and stage in ('development','reserved'):raise ValueError('Development/reserved stages belong only to the critic')
    if stage=='reserved' and any(state['units'][u['id']]['status']=='pending' for u in units if u.get('split')=='development'):raise ValueError('Complete development before reserved evaluation; do not retune after reserved results')
    def admitted(u):
        if linked:return u['id'] in linked['allowed_units']
        if stage=='gate':return u.get('gate')
        if stage in ('development','reserved'):return u.get('split')==stage
        return True
    converter_idle(root);check_readiness(Path(readiness),meta['config'],meta['kind']!='critic')
    guard.hashes.update({str(Path(readiness)/e['path']):e['sha256'] for e in files_manifest(readiness)})
    guard.hashes[str(out/'binding.json')]=sha(out/'binding.json');guard.check()
    state['readiness'].append({'path':str(Path(readiness).resolve()),'manifest_sha256':sha(Path(readiness)/'manifest.json')})
    config=meta['config'];limits=meta['limits'];base_elapsed=state['elapsed_seconds'];start=clock()
    state.update(status='running',connection_streak=0)
    def checkpoint(active=True):
        state['elapsed_seconds']=elapsed(base_elapsed+max(0,clock()-start));state['active_since_epoch']=wall() if active else None
        state['updated_at']=now();atomic_json(out/'state.json',state)
        print(f"{state['status']} calls={len(state['calls'])} completed={sum(v['status']=='completed' for v in state['units'].values())}/{len(units)} elapsed={state['elapsed_seconds']:.1f}s output={out}",flush=True)
    checkpoint()
    try:
        client=client_factory(config['endpoint'],model=config['model'],purpose='text_critic' if meta['kind']=='critic' else 'page_review',timeout=config['timeout'],max_tokens=config['max_tokens'])
        discovery=client.discover_model(out/'sessions'/uuid.uuid4().hex)
        if discovery['selected_model']!=config['model']:raise IdentityError('Current discovery differs')
        for spec in units:
            if not admitted(spec):continue
            if (out/'PAUSE').exists():state['status']='paused_operator';break
            if overnight and spec['split']=='reserved':
                # Recompute from sealed outcomes even on resume; state['gate'] alone is not authority.
                gate=gate_result(state,units,meta['gate'],out)
                state['gate']=gate
                if not gate or not gate['passed']:state['status']='gate_failed';break
            parent=spec['id'];record=state['units'][parent]
            if record['status'] in (('unavailable','unsupported') if route else ('completed','unavailable','unsupported')) or record.get('retry_deferred'):continue
            body=read_json(preview/spec['request']);data=read_json(preview/spec['data']);schema,_=validator(spec,data)
            calls=[c for c in state['calls'] if c['parent']==parent]
            prior_failure=None
            if route:
                planned=critic_route.next_request(preview,out,meta,spec,state)
                if planned is None:continue
                body,data,method,prior_failure=planned
            elif calls:
                failure=previous_failure(out,preview,meta,parent,calls[-1]['id'])
                prior_failure=failure
                method=recovery_method(failure,config,[c['method'] for c in calls]) if failure else None
                if not method:continue
                body=feedback_request(read_json(out/'calls'/calls[-1]['id']/'request.json'),failure,schema,method)
                seed=repair_seed(preview,meta,parent,calls[-1]['id'])
                if seed and body!=read_json(preview/seed['request']):raise IntegrityError('Prepared repair feedback changed')
            else:method='baseline'
            # Constrained diagnostic controls are qualification calls themselves,
            # included in the 30-call ceiling, not extra hidden model requests.
            if spec.get('condition')=='constrained':
                if state.get('schema_support')=='unsupported' or (not spec.get('gate') and not (state.get('gate') or {}).get('passed')):
                    state['units'][parent]={'status':'unsupported' if state.get('schema_support')=='unsupported' else 'unavailable',
                        'reason':'Actual schema not qualified; constrained condition not sent'}
                    continue
            while True:
                if elapsed(base_elapsed+clock()-start)>=limits['admission_seconds']:state['status']='budget_exhausted';break
                if (out/'PAUSE').exists():state['status']='paused_operator';break
                guard.check()
                for c in state['calls']:
                    if c.get('seal_sha256'):verify_seal(out/'calls'/c['id'],c['seal_sha256'],'seal.json')
                if (pilot or route) and hasattr(client,'check_admission'):
                    client.check_admission(body)
                    guard.check()
                try:
                    if route:critic_route.check_parent_budget(meta,state,parent,method)
                    call=reserve_budget(state,parent,method,limits)
                except ValueError as exc:
                    state['units'][parent].setdefault('limits',[]).append(str(exc));break
                call['request_sha256']=fingerprint(body)
                call['reserved_at']=datetime.fromtimestamp(wall(),timezone.utc).isoformat() if overnight else now()
                if overnight and len(state['calls'])==1:start=clock();base_elapsed=0.0
                prior_calls=[c for c in state['calls'][:-1] if c['parent']==parent]
                call['previous_call']=prior_calls[-1]['id'] if prior_calls else None
                call['baseline_request_sha256']=fingerprint(read_json(preview/spec['request']))
                if route:call['data_sha256']=fingerprint(data)
                checkpoint()
                dest=out/'calls'/call['id'];dest.mkdir(parents=True,exist_ok=False)
                atomic_json(dest/'reservation.json',dict(call));atomic_json(dest/'request.json',body)
                if route:atomic_json(dest/'input.json',data)
                answer=None
                try:
                    # A lowered effort changes only an expressly supported runtime control.
                    answer=client.chat(body['messages'],dest,parent,response_format=body.get('response_format'),reasoning_effort=body.get('reasoning_effort','server-default'))
                    atomic_json(dest/'assistant-response.json',answer)
                    for sent in dest.glob('attempts/*/request.json'):
                        if read_json(sent)['body']!=body:raise IntegrityError('Actual request differs from frozen/recovery payload')
                    outcome=finish_completion(answer,spec,data,config['model'],dest,compiler_image,prior_failure,method)
                except (ProbeError,ValueError,TypeError,KeyError) as exc:
                    outcome={'status':'failed','failure':diagnose(exc,response_data(dest,answer,exc),config['model']),'acceptance':'UNACCEPTED'}
                    critic_failure_diagnostics(outcome,spec,data,config['model'],prior_failure)
                    if (prior_failure or {}).get('export_repair_anchor'):
                        outcome['failure']['export_repair_anchor']=prior_failure['export_repair_anchor']
                if spec.get('condition')=='constrained' and outcome.get('failure',{}).get('kind')=='configuration':
                    outcome['status']='unsupported';outcome['failure']['kind']='actual_schema_unsupported'
                    state['schema_support']='unsupported'
                seal_outcome(dest,outcome);call.update(status=outcome['status'],seal_sha256=sha(dest/'seal.json'))
                state['units'][parent]={'status':outcome['status'],'last_call':call['id'],'failure_kind':outcome.get('failure',{}).get('kind')}
                fail=outcome.get('failure',{});kind=fail.get('kind')
                state['connection_streak']=state['connection_streak']+1 if kind in ('transport','timeout') else 0
                if kind in ('identity','integrity','configuration'):state['status']='stopped_'+kind
                elif state['connection_streak']>=2:state['status']='paused_connection'
                checkpoint()
                from .evaluation_export import experiment_report
                experiment_report(preview,out)
                if state['status']!='running' or outcome['status']=='unsupported' or (outcome['status']=='completed' and not route):break
                if route:
                    planned=critic_route.next_request(preview,out,meta,spec,state)
                    if planned is None:break
                    body,data,method,prior_failure=planned
                    continue
                previous=[c for c in state['calls'] if c['parent']==parent and c['id']!=call['id']]
                unchanged=False
                if previous:
                    old=previous_failure(out,preview,meta,parent,previous[-1]['id']) or {}
                    unchanged=(old.get('kind'),old.get('errors'),old.get('content'))==(fail.get('kind'),fail.get('errors'),fail.get('content'))
                method=None if unchanged or diagnostic else recovery_method(fail,config,[c['method'] for c in state['calls'] if c['parent']==parent])
                if unchanged:state['units'][parent]['retry_deferred']='Identical failure and final content; no unchanged blind retry'
                if not method:break
                prior_failure=fail
                body=feedback_request(body,fail,schema,method)
            if state['status']!='running':break
            if spec.get('gate') and not repair and not pilot and not route:
                gate=gate_result(state,units,meta['gate'],out)
                if gate:
                    state['gate']=gate
                    if diagnostic:
                        state['schema_support']='qualified_actual_schema_controls' if gate['passed'] else state.get('schema_support','not_qualified')
                    elif not gate['passed']:state['status']='gate_failed';break
        if state['status']=='running':
            if repair:
                state['status']='repair_completed' if all(state['units'][u]['status']=='completed' for u in repair['allowed_units']) else 'repair_unresolved'
            else:
                state['gate']=None if pilot or route else gate_result(state,units,meta['gate'],out)
                if not diagnostic and not pilot and not route and not (state['gate'] or {}).get('passed'):state['status']='gate_failed'
                elif any(v['status']=='pending' for v in state['units'].values()):state['status']='paused_stage_complete'
                else:state['status']='completed' if all(v['status']=='completed' for v in state['units'].values()) else 'completed_with_failures'
        guard.check(full=True)
    except KeyboardInterrupt:state['status']='paused_interrupted'
    except Exception as exc:
        state['status']='stopped_identity' if isinstance(exc,IdentityError) or 'Configured model ID' in str(exc) else 'stopped_integrity' if isinstance(exc,IntegrityError) else 'paused_execution'
        state['error']=str(exc)
    finally:checkpoint(False)
    return 0 if state['status'] in ('completed','paused_stage_complete','repair_completed') else 75 if state['status'].startswith('paused') else 2
