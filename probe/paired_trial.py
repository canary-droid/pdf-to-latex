"""Bounded Task 5 launcher: offline prepare, operator-only launch, status and bundle.

No retries: a durable reservation consumes its arm even after interruption.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid

from .common import atomic_json, check_manifest, files_manifest, fingerprint, read_json, sha, writer_lock
from .local_model import LocalClient, ProbeError, probe_model
from .saved_pages import converter_idle
from .batch_review import IdentityError, IntegrityError, connection_failure, seal_outcome
from .paired_inputs import CONFIG, POLICY, prepare, verify_preview, validate_answer, code_hashes, ResponseJSONError

ROOT=Path(__file__).resolve().parents[1]
TERMINAL={'completed','completed_with_failures','budget_exhausted','paused_reliability',
          'stopped_identity','stopped_integrity','stopped_configuration'}


def now():return datetime.now(timezone.utc).isoformat()


def new_directory(root,prefix):
    return root/'runs'/(prefix+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6])


def slots(order):
    return [(f"{s['ordinal']:03d}-{arm}",s,arm) for s in order for arm in s['arm_order']]


def initialize(preview,out):
    meta,order=verify_preview(preview)
    out.mkdir(parents=True,exist_ok=False)
    binding={'preview':str(preview),'preview_manifest_sha256':sha(preview/'manifest.json'),
             'config':CONFIG,'policy':POLICY,'code_sha256':code_hashes()}
    atomic_json(out/'binding.json',binding)
    state={'status':'prepared_offline','binding_sha256':fingerprint(binding),'created_at':now(),
           'elapsed_seconds':0.0,'active_since_epoch':None,'connection_streak':0,'gate':None,
           'requests':{k:{'status':'pending'} for k,_,_ in slots(order)},'readiness':[],
           'counts':{'pending':len(slots(order)),'dispatched':0,'completed':0,'failed':0,'interrupted':0},
           'attempted':0,'fidelity':'unassessed','acceptance':'UNACCEPTED'}
    atomic_json(out/'state.json',state)
    return state


def reliability(state,order):
    keys=[(f"{s['ordinal']:03d}-{a}",a) for s in order[:POLICY['gate_pairs']] for a in ('A','B')]
    if any(state['requests'][k]['status'] in ('pending','dispatched') for k,_ in keys):return None
    counts={a:sum(state['requests'][k]['status']=='completed' for k,arm in keys if arm==a) for a in ('A','B')}
    return {'passed':all(n>=POLICY['gate_min_pass_each_arm'] for n in counts.values()),
            'valid_responses':counts,'pairs':12,'minimum_each_arm':9,
            'meaning':'response format, identity and claimed coverage only; not fidelity'}


def inspect_failure(error,folder):
    record={}
    if getattr(error,'attempt_dir',None):
        p=Path(error.attempt_dir)/'record.json'
        if p.exists():record=read_json(p)
    if not record:
        retained=list(folder.glob('attempts/*/record.json'))
        if len(retained)==1:record=read_json(retained[0])
    actual=record.get('actual_model')
    if (actual is not None and actual!=CONFIG['model']) or (record.get('completion_validation') and actual!=CONFIG['model']) or isinstance(error,IdentityError):kind='identity'
    elif isinstance(error,IntegrityError):kind='integrity'
    elif isinstance(error,ProbeError) and error.status in (400,404,415,422):kind='configuration'
    elif record.get('finish_reason')=='length' or 'truncat' in str(error).lower():kind='token_limit'
    elif isinstance(error,ProbeError) and connection_failure(error):
        kind='timeout' if any(w in str(error).lower() for w in ('timeout','timed out','deadline')) else 'transport'
    elif isinstance(error,(json.JSONDecodeError,ResponseJSONError)) or any(w in str(error).lower() for w in ('duplicate json','non-finite json','strict json')):kind='json'
    elif any(w in str(error).lower() for w in ('coverage','wrong page','incomplete page','selected_blocks','block reference')):kind='coverage'
    else:kind='schema'
    return {'status':'failed','failure_kind':kind,'error':str(error),'usage':record.get('usage',{}),
            'latency_seconds':record.get('latency_seconds'), 'finish_reason':record.get('finish_reason'),
            'actual_model':actual,'acceptance':'UNACCEPTED'}


def reconcile(out,preview,order,state):
    expected={k for k,_,_ in slots(order)}
    if set(state['requests'])!=expected:raise IntegrityError('Request ledger membership changed')
    folder=out/'requests'
    actual={p.name for p in folder.iterdir()} if folder.exists() else set()
    if actual-expected:raise IntegrityError('Unknown attempt reservation')
    for key,spec,arm in slots(order):
        rec=state['requests'][key];dest=folder/key
        if not dest.exists():
            if rec['status']!='pending':raise IntegrityError('Reserved attempt disappeared')
            continue
        expected_request=preview/'regions'/f"{spec['ordinal']:03d}"/(arm+'.json')
        if not (dest/'reservation.json').exists():
            # mkdir succeeded but process died before reservation; consume conservatively.
            atomic_json(dest/'reservation.json',{'key':key,'request_sha256':sha(expected_request),'crash_before_reservation':True})
        reservation=read_json(dest/'reservation.json')
        if reservation['key']!=key or reservation['request_sha256']!=sha(expected_request):raise IntegrityError('Reservation binding changed')
        if (dest/'request.json').exists() and read_json(dest/'request.json')!=read_json(expected_request):raise IntegrityError('Dispatched request differs')
        if rec.get('seal_sha256') and (not (dest/'seal.json').exists() or sha(dest/'seal.json')!=rec['seal_sha256']):raise IntegrityError('Attempt seal changed')
        if (dest/'seal.json').exists():
            if not check_manifest(dest,read_json(dest/'seal.json')+[{'path':'seal.json','sha256':sha(dest/'seal.json')}]):raise IntegrityError('Attempt evidence changed')
        if not (dest/'outcome.json').exists():
            outcome={'status':'interrupted','failure_kind':'interrupted','error':'Reserved/dispatched without committed outcome; consumed, never resent','acceptance':'UNACCEPTED'}
            for record_path in dest.glob('attempts/*/record.json'):
                raw_record=read_json(record_path)
                if raw_record.get('actual_model') is not None and raw_record['actual_model']!=CONFIG['model']:
                    outcome={'status':'failed','failure_kind':'identity','error':'Interrupted attempt reported another model','acceptance':'UNACCEPTED'}
                elif raw_record.get('http_status') in (400,404,415,422):
                    outcome={'status':'failed','failure_kind':'configuration','error':'Interrupted attempt recorded rejected configuration','acceptance':'UNACCEPTED'}
            if (dest/'assistant-response.json').exists():
                try:
                    answer=read_json(dest/'assistant-response.json')
                    value=validate_answer(answer,read_json(expected_request.parent/'input.json'))
                    outcome={'status':'completed','answer':value,'usage':answer.get('usage',{}),
                             'latency_seconds':answer.get('latency_seconds'),'recovered':True,'acceptance':'UNACCEPTED'}
                except (ValueError,TypeError,KeyError) as exc:outcome=inspect_failure(exc,dest)
            seal_outcome(dest,outcome)
        elif not (dest/'seal.json').exists():atomic_json(dest/'seal.json',files_manifest(dest))
        outcome=read_json(dest/'outcome.json')
        if outcome['status']=='completed':
            answer=read_json(dest/'assistant-response.json')
            if validate_answer(answer,read_json(expected_request.parent/'input.json'))!=outcome['answer']:raise IntegrityError('Validated outcome changed')
        state['requests'][key]={'status':outcome['status'],'seal_sha256':sha(dest/'seal.json'),
                                'failure_kind':outcome.get('failure_kind')}
        if outcome.get('failure_kind') in ('identity','integrity','configuration'):
            state['status']='stopped_'+outcome['failure_kind']
    state.pop('current_request',None)
    gate=reliability(state,order)
    if state['gate'] is not None and state['gate']!=gate:raise IntegrityError('Reliability decision changed')
    if gate:
        state['gate']=gate
        if not gate['passed'] and not state['status'].startswith('stopped_'):state['status']='paused_reliability'


def readiness(root,out,client_factory=LocalClient):
    folder=out/'readiness'/uuid.uuid4().hex
    folder.mkdir(parents=True)
    atomic_json(folder/'converter-exit.json',converter_idle(root))
    cases=read_json(root/'fixtures/vision/manifest.json')
    if isinstance(cases,dict):cases=cases['cases']
    for c in cases:
        p=root/'fixtures/vision'/Path(c['image_path']).name
        if sha(p)!=c['sha256']:raise IntegrityError('Preflight fixture changed')
        c['image_path']=str(p)
    c=client_factory(CONFIG['endpoint'],model=CONFIG['model'],timeout=120,max_tokens=2048)
    caps=probe_model(c,folder/'model',cases)
    print('Fresh preflight:',folder,'Text:',caps['text']['status'],'vision:',caps['vision']['status'],flush=True)
    # Inspect failed capability records too: a mismatched truncated response cannot be overlooked.
    for f in (folder/'model').glob('attempts/*/record.json'):
        actual=read_json(f).get('actual_model')
        if actual is not None and actual!=CONFIG['model']:raise IdentityError('Preflight response model mismatch')
    if caps.get('selected_model')!=CONFIG['model'] or caps['model_discovery'].get('status')!='passed':
        raise RuntimeError('Qwen exact alias is unavailable; no service changed. Inspect '+str(folder))
    if caps['text']['status']!='passed' or caps['vision']['status']!='qualified':
        raise RuntimeError('Preflight must have Text: passed AND vision: qualified. Inspect '+str(folder))
    if caps['strict_json']['status'] not in ('passed','unsupported'):raise RuntimeError('Unexpected preflight JSON failure; inspect '+str(folder))
    return {'path':str(folder),'capabilities_sha256':sha(folder/'model/capabilities.json'),
            'strict_json':caps['strict_json']['status'],'finished_at':now()}


def execute(root,out,*,client_factory=LocalClient,ready=readiness,clock=time.monotonic,wall=time.time):
    binding=read_json(out/'binding.json');state=read_json(out/'state.json');preview=Path(binding['preview'])
    if state['binding_sha256']!=fingerprint(binding):raise IntegrityError('Live binding changed')
    # Before any network activity, validate current code, all preparation and original evidence.
    try:
        _,order=verify_preview(preview,binding['preview_manifest_sha256'])
        if binding['config']!=CONFIG or binding['policy']!=POLICY or binding['code_sha256']!=code_hashes():raise IntegrityError('Incompatible runner settings')
        reconcile(out,preview,order,state)
    except (ValueError,OSError,KeyError) as exc:
        state.update(status='stopped_integrity',error=str(exc));atomic_json(out/'state.json',state);return 2
    if state['active_since_epoch'] is not None:
        # Unknown crash downtime is charged conservatively; never creates extra admission time.
        state['elapsed_seconds']+=max(0,wall()-state['active_since_epoch']);state['active_since_epoch']=None
    if state['elapsed_seconds']>=POLICY['admission_seconds'] and state['status'] not in TERMINAL:state['status']='budget_exhausted'
    if state['status'] in TERMINAL:
        atomic_json(out/'state.json',state);print('No dispatch:',state['status'],state.get('gate'),flush=True);return 2
    atomic_json(out/'state.json',state)
    try:
        check=ready(root,out,client_factory)
        state['readiness'].append(check)
        converter_idle(root)
    except (Exception,KeyboardInterrupt) as exc:
        state.update(status='stopped_identity' if isinstance(exc,IdentityError) else 'stopped_integrity' if isinstance(exc,IntegrityError) else 'paused_readiness',error=str(exc))
        atomic_json(out/'state.json',state);print('Readiness blocked:',exc,flush=True);return 2
    # A successful explicit resume rechecks endpoint and acknowledges the connection pause.
    state['connection_streak']=0
    client=client_factory(CONFIG['endpoint'],model=CONFIG['model'],purpose='page_review',timeout=600,max_tokens=16384)
    prior=state['elapsed_seconds'];start=clock();state['status']='running';state.pop('error',None)
    def checkpoint(active=True):
        state['elapsed_seconds']=prior+max(0,clock()-start)
        state['active_since_epoch']=wall() if active else None
        state['updated_at']=now()
        state['counts']={x:sum(r['status']==x for r in state['requests'].values()) for x in ('pending','dispatched','completed','failed','interrupted')}
        state['attempted']=len(state['requests'])-state['counts']['pending']
        atomic_json(out/'state.json',state)
        print(f"{state['status']} {state['counts']} elapsed={state['elapsed_seconds']:.1f}s / 32400s output={out}",flush=True)
    checkpoint()
    try:
        try:discovery=client.discover_model(out/'sessions'/uuid.uuid4().hex)
        except ProbeError as exc:
            if 'Configured model ID is not an exact match' in str(exc):
                raise IdentityError('Qwen alias changed after fresh preflight') from exc
            raise
        if discovery['selected_model']!=CONFIG['model']:raise IdentityError('Discovery model mismatch')
        for key,spec,arm in slots(order):
            if state['requests'][key]['status']!='pending':continue
            if prior+max(0,clock()-start)>=POLICY['admission_seconds']:
                state['status']='budget_exhausted';break
            verify_preview(preview,binding['preview_manifest_sha256'])
            for done,record in state['requests'].items():
                if record.get('seal_sha256'):
                    evidence=out/'requests'/done
                    if sha(evidence/'seal.json')!=record['seal_sha256'] or not check_manifest(evidence,read_json(evidence/'seal.json')+[{'path':'seal.json','sha256':record['seal_sha256']}]):
                        raise IntegrityError('Previously completed/failed evidence changed')
            for ready_record in state['readiness']:
                if sha(Path(ready_record['path'])/'model/capabilities.json')!=ready_record['capabilities_sha256']:
                    raise IntegrityError('Bound preflight evidence changed')
            if prior+clock()-start>=POLICY['admission_seconds']:
                state['status']='budget_exhausted';break
            if sha(out/'binding.json')!=fingerprint_file_binding(binding):raise IntegrityError('Live binding changed during dispatch')
            src=preview/'regions'/f"{spec['ordinal']:03d}";payload=read_json(src/(arm+'.json'))
            dest=out/'requests'/key;dest.mkdir(parents=True,exist_ok=False)
            atomic_json(dest/'reservation.json',{'key':key,'request_sha256':sha(src/(arm+'.json')),'reserved_at':now(),'at_most_once':True})
            atomic_json(dest/'request.json',payload)
            state['requests'][key]={'status':'dispatched'};state['current_request']=key;checkpoint()
            print(f"Dispatch {key}: {spec['region_id']} {spec['phase']} arm {arm}; one attempt only",flush=True)
            try:
                answer=client.chat(payload['messages'],dest,'paired_'+key,reasoning_effort='medium')
                atomic_json(dest/'assistant-response.json',answer)
                # Check the actual serialized client request, without rewriting it.
                if answer.get('attempt_dir'):
                    actual=read_json(Path(answer['attempt_dir'])/'request.json')['body']
                    if actual!=payload:raise IntegrityError('Actual outgoing request differs from sealed arm')
                value=validate_answer(answer,read_json(src/'input.json'))
                outcome={'status':'completed','answer':value,'usage':answer.get('usage',{}),
                         'latency_seconds':answer.get('latency_seconds'),'acceptance':'UNACCEPTED'}
            except (ProbeError,ValueError,TypeError,KeyError) as exc:outcome=inspect_failure(exc,dest)
            for sent in dest.glob('attempts/*/request.json'):
                if read_json(sent)['body']!=payload:
                    outcome={'status':'failed','failure_kind':'integrity','error':'Outgoing request changed','acceptance':'UNACCEPTED'}
            seal_outcome(dest,outcome)
            state['requests'][key]={'status':outcome['status'],'failure_kind':outcome.get('failure_kind'),'seal_sha256':sha(dest/'seal.json')}
            state.pop('current_request',None)
            kind=outcome.get('failure_kind')
            state['connection_streak']=state['connection_streak']+1 if kind in ('transport','timeout') else 0
            gate=reliability(state,order)
            if gate:state['gate']=gate
            if kind in ('identity','integrity','configuration'):state['status']='stopped_'+kind
            elif gate and not gate['passed']:state['status']='paused_reliability'
            elif state['connection_streak']>=2:state['status']='paused_connection'
            checkpoint()
            # A compact status ledger is written every request; detailed report is also refreshed.
            from .paired_report import write_report
            write_report(out)
            if state['status']!='running':break
        else:state['status']='completed' if all(r['status']=='completed' for r in state['requests'].values()) else 'completed_with_failures'
        verify_preview(preview,binding['preview_manifest_sha256'])
    except KeyboardInterrupt:
        reconcile(out,preview,order,state)
        if state['status'] not in TERMINAL:state['status']='paused_interrupted'
    except (Exception,) as exc:
        state.update(status='stopped_identity' if isinstance(exc,IdentityError) else 'stopped_integrity' if isinstance(exc,(IntegrityError,ValueError)) else 'paused_execution',error=str(exc))
    finally:checkpoint(active=False)
    return 0 if state['status']=='completed' else 75 if state['status'].startswith('paused') else 2


def fingerprint_file_binding(binding):
    # atomic_json uses this exact canonical on-disk representation.
    import hashlib
    return hashlib.sha256((json.dumps(binding,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode()).hexdigest()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--pilot',required=True)
    for name in ('launch','status','bundle'):
        p=sub.add_parser(name);p.add_argument('--run',required=True)
    a=parser.parse_args(argv)
    if a.command=='status':
        out=Path(a.run).resolve();s=read_json(out/'state.json')
        print(json.dumps({k:v for k,v in s.items() if k!='requests'},indent=2));print('Output:',out)
        if (out/'latest-bundle.json').exists():print(json.dumps(read_json(out/'latest-bundle.json'),indent=2))
        return 0
    from .paired_report import write_report,bundle
    with writer_lock(ROOT/'runs'):
        if a.command=='prepare':
            preview=new_directory(ROOT,'qwen-native-input');out=new_directory(ROOT,'qwen-native-trial')
            prepare(ROOT,Path(a.pilot).resolve(),preview);initialize(preview,out);write_report(out);bundle(ROOT,out)
            print('Preview:',preview,'\nPrepared live run:',out)
            return 0
        out=Path(a.run).resolve()
        if a.command=='bundle':bundle(ROOT,out);return 0
        code=execute(ROOT,out)
        try:write_report(out);bundle(ROOT,out)
        except (ValueError,OSError,KeyError) as exc:print('Report/bundle unavailable; raw evidence preserved:',exc,flush=True)
        return code


if __name__=='__main__':raise SystemExit(main())
