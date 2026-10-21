"""Durable serial batch execution; at most two dispatches per review unit."""
from datetime import datetime, timezone
import html
import http.client
import json
from pathlib import Path
import shutil
import time
import uuid

from .batch_inputs import POLICY, VERSION, validate_response, verify_batch
from .common import atomic_json, check_manifest, contained, files_manifest, fingerprint, read_json, sha
from .local_model import LocalClient, ProbeError, parse_json_response, validate_base_url
from .saved_pages import converter_idle


class IntegrityError(ValueError):
    pass


class IdentityError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def unit_status(record):
    return record.get('status','pending')


def coverage(meta, units):
    result=[]
    for page in meta['pages']:
        specs=[s for s in meta['units'] if s['page_id']==page['page_id']]
        done=[s for s in specs if unit_status(units.get(s['unit_id'],{}))=='completed']
        covered={b for s in done for b in s['block_ids']}
        visual=any(s['scope'] in ('whole_page','page_omissions') for s in done)
        gaps=[b for b in page['block_ids'] if b not in covered]
        result.append({'page_id':page['page_id'],'page':page['page'],
                       'missing_block_ids':gaps,'visual_omission_check_completed':visual,
                       'status':'completed' if not gaps and visual else 'coverage_gaps'})
    return result


def write_report(out, inputs, meta, state):
    records=state.get('units',{});cover=coverage(meta,records)
    prefix='' if out==inputs else 'inputs/'
    esc=lambda value:html.escape(str(value),quote=True)
    sections=['<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">',
        '<title>Saved-page batch — UNACCEPTED</title><style>body{font:15px system-ui;max-width:1100px;margin:2em auto;padding:1em}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:.4em;text-align:left}pre{white-space:pre-wrap}details{margin:1em 0}</style>',
        '<h1>Saved-page batch — UNACCEPTED</h1><p>'+esc(state.get('status','offline_preview_no_requests_sent'))+'</p>',
        '<p>Valid JSON, completed units and coverage counts do not prove mathematical correctness. Fidelity remains unreviewed. No proposals are accepted or applied.</p>',
        '<p>Pages: '+str(len(meta['pages']))+'; review units: '+str(len(meta['units']))+
        '; pages with completed block and visual checks: '+str(sum(p['status']=='completed' for p in cover))+'.</p>']
    if state.get('error'):
        sections.append('<p>Run issue: '+esc(state['error'])+'</p>')
    for page,cov in zip(meta['pages'],cover):
        pid=page['page_id'];base=prefix+'pages/'+pid+'/'
        sections.append('<details><summary>'+esc(pid)+' — selected '+str(page['page']['selected_page'])+
            ', original PDF '+str(page['page']['original_physical_page'])+' — '+cov['status']+'</summary>')
        sections.append('<p><a href="'+base+'source.png">Original source image</a> | <a href="'+base+'page.json">All original OCR blocks</a></p>')
        sections.append('<p>Block coverage gaps: '+esc(', '.join(cov['missing_block_ids']) or 'none')+
            '; visual omission check: '+('completed' if cov['visual_omission_check_completed'] else 'pending/failed')+'.</p>')
        sections.append('<table><tr><th>Unit / scope</th><th>Status / attempts</th><th>Draft and results</th></tr>')
        for spec in (s for s in meta['units'] if s['page_id']==pid):
            uid=spec['unit_id'];rec=records.get(uid,{});relative=prefix+'units/'+uid+'/'
            links='<a href="'+relative+'input.json">Original draft, blocks and crop metadata</a> | <a href="'+relative+'request.json">Prepared request</a>'
            for attempt in rec.get('attempts',[]):
                ap=attempt['path'];links+=' | <a href="'+esc(ap)+'/outcome.json">Attempt '+str(attempt['number'])+'</a>'
                if (out/ap/'outcome.json').is_file():
                    outcome=read_json(out/ap/'outcome.json')
                    for proposal in outcome.get('proposal',{}).get('proposals',[]):
                        links+='<details><summary>UNACCEPTED'+(' — uncertain' if proposal['uncertain'] else '')+': '+esc(proposal['issue'])+'</summary><pre>'+esc(proposal['suggested_latex'])+'</pre></details>'
            if rec.get('error'):
                links+='<p>Unresolved: '+esc(rec['error'])+'</p>'
            sections.append('<tr><td>'+esc(uid)+'<br>'+spec['scope']+'</td><td>'+unit_status(rec)+' / '+str(len(rec.get('attempts',[])))+'</td><td>'+links+'</td></tr>')
        sections.append('</table></details>')
    temp=out/'review.html.tmp';temp.write_text('\n'.join(sections),encoding='utf-8');temp.replace(out/'review.html')
    atomic_json(out/'coverage.json',{'pages':cover,'fidelity':'unreviewed','automatically_accepted':0})


def binding_for(meta, preview, preflight, config):
    caps=read_json(preflight/'model/capabilities.json')
    endpoint=validate_base_url(config['base_url']);model=config.get('model')
    if (not model or model!=meta['model'] or model!=caps.get('model_discovery',{}).get('selected_model')
            or endpoint!=meta['endpoint'] or endpoint!=caps.get('endpoint')):
        raise IdentityError('Exact model/endpoint must agree with preview and preflight')
    if caps.get('text',{}).get('status')!='passed' or caps.get('vision',{}).get('status')!='qualified':
        raise ValueError('Batch requires Text: passed and vision: qualified, not just preflight exit 0')
    return {'version':VERSION,'source_run':meta['source_run'],'source_state_sha256':meta['source_state_sha256'],
        'preview_run':str(preview),'preview_manifest_sha256':sha(preview/'artifact-manifest.json'),
        'preflight_run':str(preflight),'preflight_capabilities_sha256':sha(preflight/'model/capabilities.json'),
        'model':model,'endpoint':endpoint,'limits':meta['limits'],'reasoning_effort':meta['reasoning_effort'],
        'strict_json':caps.get('strict_json',{}).get('status')=='passed','policy':POLICY}


def expected_request(inputs, spec, binding):
    payload=read_json(inputs/'units'/spec['unit_id']/'request.json')
    if not binding['strict_json']:
        payload.pop('response_format',None)
    return payload


def validate_answer(answer, data, model):
    if answer.get('actual_model')!=model:
        raise IdentityError('Response model identity differs from exact intended alias')
    if answer.get('finish_reason')!='stop':
        raise ValueError('Truncated or non-stop completion')
    return validate_response(parse_json_response(answer['content']),data)


def seal_outcome(folder, outcome):
    # Only append terminal evidence; no old attempt is reused or overwritten.
    if (folder/'outcome.json').exists() or (folder/'seal.json').exists():
        raise IntegrityError('Attempt outcome already exists')
    atomic_json(folder/'outcome.json',outcome)
    atomic_json(folder/'seal.json',files_manifest(folder))


def reconcile(out, inputs, meta, binding, state):
    """Rebuild from durable reservations/outcomes, including crash recovery."""
    expected_ids={s['unit_id'] for s in meta['units']}
    actual_ids={p.name for p in (out/'units').iterdir()} if (out/'units').exists() else set()
    if actual_ids-expected_ids or set(state['units'])!=expected_ids:
        raise IntegrityError('Unknown or missing batch state unit')
    for spec in meta['units']:
        uid=spec['unit_id'];rec=state['units'][uid];base=out/'units'/uid
        folders=sorted(base.iterdir()) if base.exists() else []
        if len(folders)>POLICY['max_attempts'] or len(folders)<len(rec['attempts']):
            raise IntegrityError('Attempt ledger removed or retry limit exceeded')
        completed=False;rebuilt=[]
        for index,folder in enumerate(folders,1):
            if not folder.is_dir() or folder.name!=f'attempt-{index:02d}' or completed:
                raise IntegrityError('Unexpected attempt order or dispatch after completion')
            old=rec['attempts'][index-1] if index<=len(rec['attempts']) else None
            seal=folder/'seal.json'
            if old and old.get('seal_sha256') and (not seal.exists() or sha(seal)!=old['seal_sha256']):
                raise IntegrityError('Previously checkpointed attempt evidence changed')
            if seal.exists():
                entries=read_json(seal)+[{'path':'seal.json','sha256':sha(seal)}]
                if not check_manifest(folder,entries):
                    raise IntegrityError('Sealed attempt evidence changed')
            request=folder/'request.json'
            if request.exists() and read_json(request)!=expected_request(inputs,spec,binding):
                raise IntegrityError('Attempt request differs from bound preparation')
            data=read_json(inputs/'units'/uid/'input.json')
            if not (folder/'outcome.json').exists():
                if (folder/'assistant-response.json').exists():
                    try:
                        answer=read_json(folder/'assistant-response.json')
                        proposal=validate_answer(answer,data,binding['model'])
                        result={'status':'completed','proposal':proposal,'recovered':True,'acceptance':'UNACCEPTED'}
                    except IdentityError:
                        result={'status':'fatal_identity','error':'Recovered response model mismatch'}
                    except (ValueError,KeyError,TypeError) as exc:
                        result={'status':'failed','error':str(exc),'failure_kind':'validation'}
                else:
                    result={'status':'failed','error':'Interrupted before a validated response was committed; attempt consumed',
                            'failure_kind':'interrupted'}
                seal_outcome(folder,result)
            elif not seal.exists():
                # Crash after the atomic outcome commit, before sealing/checkpointing.
                atomic_json(seal,files_manifest(folder))
            result=read_json(folder/'outcome.json')
            if result['status']=='completed':
                answer=read_json(folder/'assistant-response.json')
                if validate_answer(answer,data,binding['model'])!=result['proposal']:
                    raise IntegrityError('Saved proposal differs from validated response')
                if not request.exists():
                    raise IntegrityError('Successful attempt has no saved request')
                completed=True
            if result['status']=='fatal_identity':
                state['status']='stopped_identity'
            rebuilt.append({'number':index,'path':folder.relative_to(out).as_posix(),'seal_sha256':sha(seal)})
            rec['error']=result.get('error')
        rec['attempts']=rebuilt
        rec['status']='completed' if completed else 'failed' if folders else 'pending'


def guard_files(root, preview, inputs, preflight, binding_path, meta, binding):
    if read_json(binding_path)!=binding:
        raise IntegrityError('Batch binding changed')
    paths={binding_path:sha(binding_path),preflight/'model/capabilities.json':binding['preflight_capabilities_sha256']}
    memberships={}
    for base in (preview,inputs):
        entries=read_json(base/'artifact-manifest.json')
        memberships[base]={e['path'] for e in entries}|{'artifact-manifest.json'}
        for entry in entries:
            paths[base/entry['path']]=entry['sha256']
        paths[base/'artifact-manifest.json']=binding['preview_manifest_sha256']
    run=Path(meta['source_run']);paths[run/'state.json']=meta['source_state_sha256']
    source=read_json(run/'state.json')['settings']['sources'][meta['source']]
    paths[contained(root,source['pdf'])]=source['sha256']
    for rec in read_json(run/'state.json')['units'].values():
        if rec['source_id']!=meta['source']:
            continue
        attempt=contained(run,rec['attempt'])
        for e in rec['evidence_files']:
            paths[attempt/e['path']]=e['sha256']
        for e in rec['files']:
            paths[attempt/'output'/e['path']]=e['sha256']
        memberships[attempt/'output']={e['path'] for e in rec['files']}
    return paths,memberships


def check_guard(paths, memberships):
    try:
        for base,expected in memberships.items():
            files=list(base.rglob('*'))
            if any(p.is_symlink() for p in files) or {p.relative_to(base).as_posix() for p in files if p.is_file()}!=expected:
                raise IntegrityError('Bound evidence membership changed: '+str(base))
        for path,expected in paths.items():
            if path.is_symlink() or not path.is_file() or sha(path)!=expected:
                raise IntegrityError('Bound evidence changed: '+str(path))
    except OSError as exc:
        raise IntegrityError('Cannot verify bound evidence: '+str(exc)) from exc


def reported_model(error):
    folder=getattr(error,'attempt_dir',None)
    if folder and (Path(folder)/'record.json').exists():
        return read_json(Path(folder)/'record.json').get('actual_model')
    return None


def connection_failure(error, http_status=None):
    # A timeout/connection drop can occur after HTTP 200 headers have arrived.
    cause=error
    while cause is not None:
        if isinstance(cause,(OSError,http.client.HTTPException)):
            return True
        cause=cause.__cause__
    status=error.status if http_status is None else http_status
    return (status is None or status in (502,503,504)
            or 'Incomplete HTTP response body.' in str(error))


def execute_batch(root, preview, preflight, out, config, *, resume=False, client_factory=LocalClient):
    converter_idle(root)
    meta,_=verify_batch(root,preview)
    binding=binding_for(meta,preview,preflight,config)
    inputs=out/'inputs'
    if resume:
        state=read_json(out/'state.json')
        if read_json(out/'binding.json')!=binding or state['binding_sha256']!=fingerprint(binding):
            raise IntegrityError('Incompatible resume: source, preview, preflight, model or settings changed')
        if state['status'] in ('stopped_identity','stopped_integrity'):
            raise IntegrityError('Batch was stopped for identity/integrity failure; inspect it before preparing another run')
        copied,_=verify_batch(root,inputs)
        if copied!=meta or sha(inputs/'artifact-manifest.json')!=binding['preview_manifest_sha256']:
            raise IntegrityError('Copied prepared evidence changed')
    else:
        if (out/'state.json').exists() or inputs.exists():
            raise ValueError('New batch output must be empty; use --resume for existing work')
        shutil.copytree(preview,inputs)
        atomic_json(out/'binding.json',binding)
        state={'version':VERSION,'binding_sha256':fingerprint(binding),'created_at':now(),
               'status':'prepared','elapsed_seconds':0,'consecutive_connection_failures':0,
               'units':{s['unit_id']:{'status':'pending','attempts':[]} for s in meta['units']}}
        atomic_json(out/'state.json',state)
    paths,memberships=guard_files(root,preview,inputs,preflight,out/'binding.json',meta,binding)
    start=time.monotonic();prior=state['elapsed_seconds']
    def checkpoint():
        state['elapsed_seconds']=round(prior+time.monotonic()-start,3);state['updated_at']=now()
        state['counts']={status:sum(unit_status(r)==status for r in state['units'].values())
                         for status in ('completed','failed','pending','running')}
        state['retryable_units']=sum(r['status']=='failed' and len(r['attempts'])<POLICY['max_attempts'] for r in state['units'].values())
        state['completed_pages']=sum(p['status']=='completed' for p in coverage(meta,state['units']))
        state['fidelity']='unreviewed';state['automatically_accepted']=0
        atomic_json(out/'state.json',state)
        write_report(out,inputs,meta,state)
        print(f"Batch {state['status']}: {state['counts']} retryable={state['retryable_units']} pages={state['completed_pages']}/{len(meta['pages'])} elapsed={state['elapsed_seconds']:.1f}s output={out}",flush=True)
    session=out/'sessions'/uuid.uuid4().hex
    session.mkdir(parents=True)
    client=client_factory(binding['endpoint'],model=binding['model'],purpose='page_review',
                         timeout=meta['limits']['timeout_seconds'],max_tokens=meta['limits']['max_output_tokens'])
    try:
        check_guard(paths,memberships);reconcile(out,inputs,meta,binding,state)
        for rec in state['units'].values():
            for attempt in rec['attempts']:
                folder=out/attempt['path'];entries=read_json(folder/'seal.json')
                paths.update({folder/e['path']:e['sha256'] for e in entries})
                paths[folder/'seal.json']=attempt['seal_sha256']
                memberships[folder]={e['path'] for e in entries}|{'seal.json'}
        if state['status']=='stopped_identity':
            checkpoint();return 2
        eligible=lambda r:r['status']!='completed' and len(r['attempts'])<POLICY['max_attempts']
        if not any(eligible(r) for r in state['units'].values()):
            state['status']='completed_unaccepted' if all(r['status']=='completed' for r in state['units'].values()) else 'completed_with_gaps'
            checkpoint();return 0 if state['status']=='completed_unaccepted' else 2
        state['status']='running';state.pop('error',None);checkpoint()
        try:
            discovery=client.discover_model(session/'model')
            if discovery['selected_model']!=binding['model']:
                raise IdentityError('Discovery selected a different model')
        except ProbeError as exc:
            status=getattr(exc,'status',None)
            folder=getattr(exc,'attempt_dir',None)
            if folder and (Path(folder)/'record.json').exists():
                status=read_json(Path(folder)/'record.json').get('http_status',status)
            if connection_failure(exc,status):
                state.update(status='paused_connection',error=str(exc));checkpoint();return 75
            raise IdentityError('Model discovery failed: '+str(exc)) from exc
        atomic_json(session/'model-identity.json',discovery)
        # First finish unattempted units, then the single permitted retry pass.
        for pass_number in range(POLICY['max_attempts']):
            for spec in meta['units']:
                uid=spec['unit_id'];rec=state['units'][uid]
                if not eligible(rec) or len(rec['attempts'])!=pass_number:
                    continue
                check_guard(paths,memberships)
                number=len(rec['attempts'])+1;folder=out/'units'/uid/f'attempt-{number:02d}'
                folder.mkdir(parents=True,exist_ok=False)
                payload=expected_request(inputs,spec,binding)
                atomic_json(folder/'reservation.json',{'unit_id':uid,'number':number,'started_at':now(),
                    'binding_sha256':state['binding_sha256'],'request_sha256':fingerprint(payload)})
                atomic_json(folder/'request.json',payload)
                rec['attempts'].append({'number':number,'path':folder.relative_to(out).as_posix(),'seal_sha256':None})
                rec['status']='running';state['current_unit']=uid;checkpoint()
                print(f"Dispatch {uid} ({spec['scope']}) attempt {number}/2",flush=True)
                data=read_json(inputs/'units'/uid/'input.json')
                try:
                    kwargs={'reasoning_effort':payload['reasoning_effort']} if 'reasoning_effort' in payload else {}
                    answer=client.chat(payload['messages'],folder,'batch_review',response_format=payload.get('response_format'),**kwargs)
                    atomic_json(folder/'assistant-response.json',answer)
                    proposal=validate_answer(answer,data,binding['model'])
                    outcome={'status':'completed','proposal':proposal,'acceptance':'UNACCEPTED'}
                    state['consecutive_connection_failures']=0
                except IdentityError as exc:
                    outcome={'status':'fatal_identity','error':str(exc)}
                except ProbeError as exc:
                    actual=reported_model(exc)
                    if actual is not None and actual!=binding['model']:
                        outcome={'status':'fatal_identity','error':'Failed response reported a different model: '+actual}
                    else:
                        connection=connection_failure(exc)
                        outcome={'status':'failed','error':str(exc),'failure_kind':'connection' if connection else 'response'}
                        state['consecutive_connection_failures']=(state['consecutive_connection_failures']+1 if connection else 0)
                except (ValueError,TypeError,KeyError) as exc:
                    outcome={'status':'failed','error':str(exc),'failure_kind':'validation'}
                    state['consecutive_connection_failures']=0
                seal_outcome(folder,outcome)
                rec['attempts'][-1]['seal_sha256']=sha(folder/'seal.json')
                rec['status']='completed' if outcome['status']=='completed' else 'failed';rec['error']=outcome.get('error')
                paths.update({folder/e['path']:e['sha256'] for e in read_json(folder/'seal.json')})
                paths[folder/'seal.json']=sha(folder/'seal.json')
                memberships[folder]={e['path'] for e in read_json(folder/'seal.json')}|{'seal.json'}
                state.pop('current_unit',None)
                if outcome['status']=='fatal_identity':
                    state.update(status='stopped_identity',error=outcome['error']);checkpoint();return 2
                checkpoint()
                if state['consecutive_connection_failures']>=POLICY['connection_failure_pause_threshold']:
                    state.update(status='paused_connection',error='Repeated connection failures; resume explicitly after checking the endpoint')
                    checkpoint();return 75
        check_guard(paths,memberships)
        state['status']='completed_unaccepted' if all(r['status']=='completed' for r in state['units'].values()) else 'completed_with_gaps'
        checkpoint();return 0 if state['status']=='completed_unaccepted' else 2
    except KeyboardInterrupt:
        reconcile(out,inputs,meta,binding,state)
        if state['status']!='stopped_identity':
            state['status']='paused_interrupted'
        state.pop('current_unit',None);checkpoint();return 130
    except (IntegrityError,IdentityError) as exc:
        state.update(status='stopped_identity' if isinstance(exc,IdentityError) else 'stopped_integrity',error=str(exc))
        checkpoint();return 2


def show_status(out):
    state=read_json(out/'state.json')
    print(json.dumps({k:state.get(k) for k in ('status','counts','retryable_units','completed_pages',
        'current_unit','elapsed_seconds','updated_at','error','fidelity')},indent=2))
    print('Output:',out,'\nReport:',out/'review.html')
    return 0
