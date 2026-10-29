"""Bounded serial chapter experiment, explicitly separate from visual review.

No service control, OCR, cloud client, automatic acceptance or semantic repair.
"""
import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
import zipfile

from . import chapter_inputs as inputs, chapter_protocol as protocol, tex_compile
from .common import atomic_json, read_json, sha, fingerprint, files_manifest, writer_lock
from .experiment import InputGuard, verify_seal
from .local_model import LocalClient, ProbeError
from .saved_pages import converter_idle

ROOT=inputs.ROOT
POINTER=ROOT/'results/chapter-glm-current.json'
SESSION='chapter-glm'
LIMITS={'calls':80,'additional_per_task':2,'wall_seconds':8*3600}
CODE=('probe/chapter_inputs.py','probe/chapter_protocol.py','probe/chapter_glm.py',
      'probe/saved_pages.py','probe/local_model.py','probe/tex_compile.py','probe/common.py',
      'scripts/render-chapter-native.py','scripts/run-chapter-glm.sh')


class StopRun(RuntimeError):pass
class Fatal(StopRun):pass


def code_hashes():
    # Bind all project controller modules, as other long-running project routes
    # do. An unrelated controller edit must not silently change a resumed job.
    paths=set(CODE)|{str(p.relative_to(ROOT)) for p in (ROOT/'probe').glob('*.py')}
    return {p:sha(ROOT/p) for p in sorted(paths)}


def test_hashes():return files_manifest(ROOT/'tests')
def now():return datetime.now(timezone.utc).isoformat()
def save(run,state):atomic_json(run/'state.json',state)


def reserve(state,parent,body_hash,wall=None):
    """Reserve before dispatch. Idle time and uncertain calls remain consumed."""
    wall=time.time() if wall is None else wall
    editorial=state.get('chapter_contract')=='annotated-chapter-v1'
    ceiling=state['execution_limits']['calls'] if editorial else LIMITS['calls']
    if ceiling is not None and len(state['calls'])>=ceiling:raise StopRun('Recorded call ceiling reached; visible unfinished tasks remain')
    if editorial and state.get('production_stage') and parent!='readiness':
        if parent not in state['production_stage']['task_ids']:
            raise StopRun('Task is outside this explicitly scheduled book stage')
    if state.get('pilot'):
        plan=state['pilot'];new=state['calls'][plan['inherited_calls']:]
        if parent=='readiness':
            if sum(c['parent']=='readiness' for c in new)>=plan['readiness_limit']:
                raise StopRun('Pilot readiness allowance exhausted; explicit continuation required')
        elif parent not in plan['task_ids']:
            raise StopRun('This preparation admits only the three-case pilot; other book work remains deferred')
    if state.get('timing_policy') != 'manual_only' and state['first_dispatch'] is not None and wall>=state['first_dispatch']+LIMITS['wall_seconds']:
        raise StopRun('Eight-hour wall deadline expired; explicit authorized extension required, never a new run/reset')
    allowance=state['execution_limits']['attempts_per_unit'] if editorial else 1+LIMITS['additional_per_task']
    if parent!='readiness' and sum(c['parent']==parent for c in state['calls'])>=allowance:
        raise StopRun('Task shared additional-call allowance exhausted')
    if state['first_dispatch'] is None:state['first_dispatch']=wall
    c={'id':f'call-{len(state["calls"])+1:03d}','parent':parent,'request_sha256':body_hash,
       'status':'in_progress','reserved_at':now(),'reserved_epoch':wall}
    state['calls'].append(c)
    return c


def remaining(state):
    if state.get('timing_policy') == 'manual_only':return float('inf')
    if state['first_dispatch'] is None:return LIMITS['wall_seconds']
    return max(0,state['first_dispatch']+LIMITS['wall_seconds']-time.time())


def extra_context(preview,key):
    """Available exact nearby definitions and bibliography; bounded, never clipped."""
    meta=read_json(preview/'inputs.json');context=[];size=0;entries=[]
    source='gatheral' if key.startswith('gatheral-') else 'klebaner-ch4-7'
    for part in meta['parts']:
        if part['source']!=source or part['key']==key:continue
        path=preview/'chapters'/part['key']/'source.json';data=read_json(path)
        blocks=data['blocks']
        if part['key']=='gatheral-bibliography':
            spans=[blocks]
        else:
            spans=[]
            for i,b in enumerate(blocks):
                t=b['tex']
                if b['kind'] not in inputs.AUX and ('Definition ' in t or 'Assumption ' in t):
                    # Keep complete observed blocks plus following display; not a
                    # claim that an unlabelled/cross-page theorem is complete.
                    group=[b]
                    if i+1<len(blocks) and blocks[i+1]['kind']=='equation':group.append(blocks[i+1])
                    spans.append(group)
        for group in spans:
            t='\n'.join('% SRC '+b['id']+'\n'+b['tex'] for b in group)
            if size+len(t)>20000:
                entries.append({'ids':[b['id'] for b in group],'status':'unavailable_in_bounded_context'})
                continue
            context.append(t);size+=len(t)
            entries.append({'ids':[b['id'] for b in group],'status':'included_unreviewed_saved_OCR',
                            'scope':'complete blocks, statement completeness not certified'})
    return '\n\n'.join(context),entries


def initialize(preview):
    preview=Path(preview).resolve();verify_seal(preview)
    meta=read_json(preview/'inputs.json');run=inputs.new_path('chapter-glm-trial');run.mkdir()
    binding={'version':'chapter-glm-v1','preview':str(preview),'preview_manifest_sha256':sha(preview/'manifest.json'),
        'code':code_hashes(),'model':protocol.MODEL,'endpoint':protocol.BASE_URL,'limits':LIMITS,
        'max_tokens':protocol.MAX_TOKENS,'request_timeout':protocol.TIMEOUT,'compiler_image':protocol.IMAGE,
        'sampling_and_reasoning':'omitted; regular server defaults, effective reasoning unconfirmed',
        'comparison':'new MinerU-input experiment, not an exact Open WebUI replay'}
    atomic_json(run/'binding.json',binding)
    keys=['klebaner-04']+[f'gatheral-{i:02d}' for i in range(1,12)]
    schedule=[(keys[0],'convert'),(keys[0],'review')]
    schedule += [(k,'convert') for k in keys[1:]]+[(k,'review') for k in keys[1:]]
    schedule += [(k,p) for k in ('gatheral-postscript','gatheral-bibliography') for p in ('convert','review')]
    state={'status':'prepared_offline','created_at':now(),'first_dispatch':None,'calls':[],
        'binding_sha256':fingerprint(binding),'tasks':[{'id':k+'/'+p,'key':k,'phase':p,'status':'pending'} for k,p in schedule],
        'compile_unavailable':None,'connection_failures':0,'acceptance':'UNACCEPTED'}
    for key in keys+['gatheral-postscript','gatheral-bibliography']:
        folder=preview/'chapters'/key;inv=read_json(folder/'inventory.json');source=(folder/'source.tex').read_text()
        context,ledger=extra_context(preview,key)
        dest=run/'prepared'/key;dest.mkdir(parents=True)
        (dest/'review-context.txt').write_text(context);atomic_json(dest/'context-inventory.json',ledger)
        body=protocol.request(source,inv)
        atomic_json(dest/'conversion-request.json',body);atomic_json(dest/'budget.json',protocol.budget(body))
    atomic_json(run/'prepared-manifest.json',files_manifest(run/'prepared'))
    binding['prepared_manifest_sha256']=sha(run/'prepared-manifest.json')
    atomic_json(run/'binding.json',binding);state['binding_sha256']=fingerprint(binding)
    save(run,state);build_report(run,state)
    atomic_json(POINTER,{'run':str(run),'preview':str(preview)})
    return run


def verify(run):
    binding=read_json(run/'binding.json');state=read_json(run/'state.json')
    if state['binding_sha256']!=fingerprint(binding) or binding['code']!=code_hashes():
        raise Fatal('Code or binding changed; do not reseal or reset an existing run')
    if binding['limits']!=LIMITS or binding['model']!=protocol.MODEL or binding['endpoint']!=protocol.BASE_URL:
        raise Fatal('Incompatible chapter settings')
    preview=Path(binding['preview']);verify_seal(preview,binding['preview_manifest_sha256'])
    from .common import check_manifest
    if sha(run/'prepared-manifest.json')!=binding['prepared_manifest_sha256']:raise Fatal('Prepared request manifest changed')
    if not check_manifest(run/'prepared',read_json(run/'prepared-manifest.json')):raise Fatal('Prepared requests/context changed')
    for call in state['calls']:
        if call.get('seal'):verify_seal(run/'calls'/call['id'],call['seal'])
    for task in state['tasks']:
        if task.get('output') and sha(run/task['output'])!=task['output_sha256']:raise Fatal('Completed draft/review changed')
        for section in task.get('sections',[]):
            if sha(run/section['path'])!=section['sha256']:raise Fatal('Completed section changed')
    return binding,state,preview


def check_other_jobs(proc_root=Path('/proc')):
    converter_idle(ROOT)
    # Project lock handles participating writers. Fail closed on visible other
    # project model controllers and heavy alternative deployments on this host.
    hits=[]
    for p in proc_root.iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid():continue
        try:
            if p.stat().st_uid!=os.getuid():continue
            args=(p/'cmdline').read_bytes().split(b'\0');words=[x.decode(errors='replace') for x in args if x]
            if '-m' in words:
                i=words.index('-m');module=words[i+1] if i+1<len(words) else ''
                if module.startswith('probe.') and module!='probe.chapter_glm' and any(x in words for x in ('launch','run','execute','gate','continue','ready')):
                    hits.append(p.name)
        except (FileNotFoundError,ProcessLookupError):continue
    if hits:raise StopRun('Other project inference controllers are present: '+','.join(hits))
    # Read only: a resident alternative heavy deployment is a conservative
    # conflict even if it happens to be idle. Never stop it automatically.
    if not shutil.which('docker') or not shutil.which('ssh'):
        raise StopRun('Docker/SSH workload inspection unavailable; cannot establish an idle two-node phase')
    commands=[('head',['docker','ps','--format','{{.Names}}']),
              ('peer',['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','spark-92a4',
                       "docker ps --format '{{.Names}}'"])]
    for node,cmd in commands:
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
        if result.returncode:
            raise StopRun(f'Cannot check {node} deployment workload: '+result.stderr.strip())
        names=[n for n in result.stdout.splitlines() if any(x in n.lower() for x in ('deepseek','qwen','flash-next','flashnext'))]
        if names:raise StopRun(f'Other heavy deployment present on {node}; operator must arrange phases: '+', '.join(names))


def metadata(exc):
    if not getattr(exc,'attempt_dir',None):return {}
    path=Path(exc.attempt_dir)/'record.json'
    return read_json(path) if path.is_file() else {}


def classify_failure(record,message):
    if record.get('actual_model') not in (None,protocol.MODEL):return 'identity'
    if record.get('stream_events',0)>0 and record.get('actual_model') is None:return 'identity'
    if 'Operator stop' in message:return 'operator_stop'
    if record.get('finish_reason')=='length':return 'truncation'
    if 'reasoning-only' in message:return 'empty_reasoning_only'
    if any(x in message.lower() for x in ('timed out','timeout','deadline')):
        return 'connection_timeout' if record.get('stage') == 'connection_establishment' else 'timeout'
    if record.get('transport_error'):return 'connection'
    if record.get('http_status') is None and any(x in message.lower() for x in ('local request failed','connection')):return 'connection'
    return 'content_or_format'


def invoke(run,state,parent,body,*,client_factory=LocalClient):
    if (run/'pause.json').exists():raise StopRun('Operator pause requested; current response preserved')
    if state.get('timing_policy') == 'manual_only' and (run/'stop.json').exists():raise StopRun('Operator stop requested')
    if remaining(state)<=0:raise StopRun('Eight-hour wall deadline expired')
    continuous=state.get('timing_policy') == 'manual_only'
    if continuous and body.get('stream') is not True:raise ValueError('Simple no-deadline requests require durable streaming')
    if continuous and 'reasoning_effort' in body:
        from .chapter_editorial import validate_effort
        validate_effort(body['reasoning_effort'])
    client=client_factory(protocol.BASE_URL,protocol.MODEL,purpose='simple_chapter' if continuous else 'chapter',timeout=min(10,remaining(state)),
                          max_tokens=body['max_tokens'],max_response_bytes=(256 if continuous else 8)*1024*1024)
    admission=run/'admission'/f'{len(state["calls"])+1:03d}-{time.time_ns()}'
    client.discover_model(admission)
    health,evidence=client.chapter_health(admission);capacity=protocol.health_capacity(health)
    admission_budget=protocol.budget(body,capacity)
    call=reserve(state,parent,fingerprint(body));save(run,state)
    answer,call=perform_reserved(run,call,body,continuous=continuous,
        admission_budget=admission_budget,health_evidence=evidence,client=client,
        timeout=None if continuous else min(protocol.TIMEOUT,remaining(state),120 if parent=='readiness' else protocol.TIMEOUT),
        overall_deadline=None if continuous else state['first_dispatch']+LIMITS['wall_seconds'])
    account_response(state,call);save(run,state)
    if call.get('failure_kind')=='identity':raise Fatal('Changed response model identity; stopped')
    return answer,call


def account_response(state,call):
    if call.get('failure_kind') in ('connection','connection_timeout'):
        state['connection_failures']=state.get('connection_failures',0)+1
    else:state['connection_failures']=0


def perform_reserved(run,call,body,*,continuous,admission_budget,health_evidence,
                     client=None,timeout=None,overall_deadline=None):
    """Only write this reserved call's directory; no shared state or admission.

    The coordinator persists the reservation first. A private call record and
    independent safe HTTP client are used by each concurrent worker.
    """
    if call['request_sha256']!=fingerprint(body):raise Fatal('Reserved request binding changed')
    parent=call['parent']
    new_client=client is None
    if new_client:
        client=LocalClient(protocol.BASE_URL,protocol.MODEL,purpose='simple_chapter',timeout=10,
            max_tokens=body['max_tokens'],max_response_bytes=256*1024*1024)
    dest=run/'calls'/call['id'];dest.mkdir(parents=True)
    atomic_json(dest/'request.json',body);atomic_json(dest/'admission.json',{'budget':admission_budget,'health_evidence':health_evidence})
    if timeout is not None and timeout<=0:raise StopRun('Deadline expired after reservation; uncertain reservation retained')
    client.timeout=timeout;start=time.monotonic()
    if continuous:client.stop_requested=lambda:(run/'stop.json').exists()
    atomic_json(dest/'settings.json',{'model':protocol.MODEL,'endpoint':protocol.BASE_URL,'max_tokens':body['max_tokens'],
        'stream':body.get('stream',False),'connection_timeout_seconds':10,'generation_deadline_seconds':timeout,
        'max_response_bytes':(256 if continuous else 8)*1024*1024,
        'overall_deadline':overall_deadline,
        'requested_reasoning_effort':body.get('reasoning_effort','server-default'),
        'effective_reasoning_effort':'not attested by response; installed mapping documented separately',
        'thinking_and_sampling':'effort explicit where recorded; sampling overrides omitted'})
    print(f'Book: {"Bergomi, Stochastic Volatility Modeling" if "bergomi-" in parent else "Klebaner comparison" if parent.startswith("klebaner") else "Gatheral, The Volatility Surface"}. '
          f'Phase/chapter: {parent}. Model: {protocol.MODEL}. Action: reserved request {call["id"]}. Result: {run}',flush=True)
    try:
        if new_client:
            client.timeout=10
            client.discover_model(dest/'discovery')
            client.timeout=timeout
        options={'stream':True} if continuous else {}
        if 'reasoning_effort' in body:options['reasoning_effort']=body['reasoning_effort']
        result=client.chat(body['messages'],dest,'chapter',**options)
        if result['actual_model']!=protocol.MODEL:raise Fatal('Response model identity changed: '+str(result['actual_model']))
        (dest/'content.txt').write_text(result['content'])
        call.update(status='completed_response',metadata={k:v for k,v in result.items() if k!='content'})
        return result['content'],call
    except ProbeError as exc:
        record=metadata(exc);kind=classify_failure(record,str(exc))
        if 'Configured model ID is not an exact match' in str(exc):kind='identity'
        call.update(status='failed',failure_kind=kind,error=str(exc),metadata=record)
        return None,call
    except Fatal as exc:
        call.update(status='failed',failure_kind='identity',error=str(exc));return None,call
    except Exception as exc:
        call.update(status='failed',failure_kind='adapter_exception',error=type(exc).__name__+': '+str(exc))
        return None,call
    finally:
        # Preserve final-channel text even when length/empty validation rejected
        # the overall response. It remains explicitly incomplete, never a draft.
        for raw in dest.glob('attempts/*/response.raw'):
            try:
                assembled=raw.parent/'response.assembled.json'
                response=read_json(assembled if assembled.is_file() else raw);message=response['choices'][0]['message'];answer=message.get('content')
                if isinstance(answer,str):
                    (dest/'final-channel.raw.txt').write_text(answer)
                    (dest/'answer.txt').write_text(answer)
                reasoning=message.get('reasoning_content',message.get('reasoning'))
                if isinstance(reasoning,str):(dest/'reasoning.txt').write_text(reasoning)
                atomic_json(dest/'response-metadata.json',{'model':response.get('model'),'usage':response.get('usage'),
                    'finish_reason':response['choices'][0].get('finish_reason'),'server_timings':response.get('tensorfold'),
                    'stream_evidence':response.get('stream_evidence'),'status':call['status'],
                    'elapsed_seconds':time.monotonic()-start,'raw_response':str(raw.relative_to(dest)),
                    'note':'Server-returned reasoning and answer are separate; incomplete/failed answers are not completed chapters'})
            except (ValueError,KeyError,IndexError,TypeError):pass
        call['elapsed_seconds']=time.monotonic()-start
        call['completed_epoch']=time.time();call['completed_at']=now()
        atomic_json(dest/'outcome.json',call)
        atomic_json(dest/'manifest.json',files_manifest(dest));call['seal']=sha(dest/'manifest.json')
        # Only the coordinator merges this record into durable shared state.


def readiness(run,state,client_factory=LocalClient):
    body={'model':protocol.MODEL,'messages':[{'role':'user','content':'Reply with exactly CHAPTER_READY and no other text.'}],
          'max_tokens':2048,'stream':state.get('timing_policy') == 'manual_only'}
    content,call=invoke(run,state,'readiness',body,client_factory=client_factory)
    if content is None or content.strip()!='CHAPTER_READY':
        raise StopRun('GLM text readiness failed (empty/wrong reply or unavailable). No model substitution or service change. See '+str(run/'calls'/call['id']))
    atomic_json(run/'latest-readiness.json',{'call':call['id'],'actual_model':protocol.MODEL,'status':'passed','at':now()})


def output_paths(run,key,phase):
    folder=run/'chapters'/key;folder.mkdir(parents=True,exist_ok=True)
    return folder/('draft.tex' if phase=='convert' else 'review.md')


def execute_task(run,state,task,preview,client_factory=LocalClient):
    key=task['key'];phase=task['phase'];src=preview/'chapters'/key
    inventory=read_json(src/'inventory.json');data=read_json(src/'source.json');source=(src/'source.tex').read_text()
    original_draft=run/'chapters'/key/'draft.tex'
    if phase=='review' and not original_draft.is_file():
        task.update(status='unavailable',error='No mechanically complete chapter draft to review');save(run,state);return
    generated=original_draft.read_text() if phase=='review' else None
    context=(run/'prepared'/key/'review-context.txt').read_text() if phase=='review' else ''
    calls=[c for c in state['calls'] if c['parent']==task['id']]
    if any(c['status']=='in_progress' or (c['status']=='completed_response' and not c.get('local_validation')) for c in calls):
        task.update(status='unresolved_interruption',error='Interrupted reservation or response not locally finalized; raw evidence retained, no automatic replay');save(run,state);return
    groups=task.get('split_groups')
    if groups is None and calls and calls[-1].get('failure_kind') in ('truncation','empty_reasoning_only'):
        groups=inventory['split']['groups']
        if not groups:
            task.update(status='failed',error='Output exhausted; no safe section boundary available');save(run,state);return
        task['split_groups']=groups
    while len([c for c in state['calls'] if c['parent']==task['id']])<3:
        groups=task.get('split_groups')
        done=task.setdefault('sections',[])
        if groups and len(done)>=len(groups):break
        tag=f'section-{len(done)+1}' if groups else 'whole'
        assigned=groups[len(done)] if groups else inventory['target_ids']
        feedback=task.get('feedback') if not groups else None
        task['status']='running';save(run,state)
        try:
            body=protocol.request(source,inventory,phase=phase,generated=generated,assigned=assigned,context=context,feedback=feedback,tag=tag)
            content,call=invoke(run,state,task['id'],body,client_factory=client_factory)
        except ValueError as exc:
            task.update(status='unavailable',error=str(exc));save(run,state);return
        if content is None:
            kind=call['failure_kind'];task.update(status='failed',error=call['error'])
            if state['connection_failures']>=2:raise StopRun('Repeated connection failures; paused without service operation')
            if kind in ('truncation','empty_reasoning_only') and not groups and inventory['split']['groups']:
                task['split_groups']=inventory['split']['groups'];save(run,state);continue
            # Never repeat an identical truncated/transport/unknown completion.
            save(run,state);return
        try:
            valid,coverage=protocol.validate_output(content,inventory,phase=phase,assigned=assigned,tag=tag,blocks=data['blocks'])
        except ValueError as exc:
            task.update(status='failed',error=str(exc))
            call['local_validation']={'status':'failed','error':str(exc)}
            # Exact raw answer remains in sealed call. New request contains the
            # diagnostic and failed answer, never a gold correction.
            task['feedback']=str(exc)+'\nFAILED ANSWER:\n'+content
            if not groups and ('incomplete' in str(exc) or 'Missing or out-of-order' in str(exc)) and inventory['split']['groups']:
                task['split_groups']=inventory['split']['groups']
            elif groups:save(run,state);return  # no remaining guaranteed complete assembly
            save(run,state);continue
        call['local_validation']={'status':'passed',**coverage}
        if groups:
            path=run/'chapters'/key/(phase+'-'+tag+('.tex' if phase=='convert' else '.md'))
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(valid)
            done.append({'path':str(path.relative_to(run)),'sha256':sha(path),'call':call['id']})
            task['status']='splitting';save(run,state)
            if len(done)<len(groups):continue
            texts=[(run/x['path']).read_text() for x in done]
            valid=protocol.assemble_sections(texts,groups,inventory,data['blocks']) if phase=='convert' else '\n\n'.join(texts)
        output=output_paths(run,key,phase);output.write_text(valid)
        task.update(status='completed',output=str(output.relative_to(run)),output_sha256=sha(output),
                    coverage={'source_blocks':len(inventory['target_ids']),'markers_accounted':True,'image_verified':False,'semantic_fidelity':'not established'})
        save(run,state)
        if phase=='convert':compile_chapter(run,state,preview,key,valid)
        return
    if task['status']!='completed':task.update(status='failed',error='Shared task allowance exhausted; incomplete sections retained')
    save(run,state)


def asset_map(preview,key=None):
    selected=[key] if key else [p['key'] for p in read_json(preview/'inputs.json')['parts']]
    names=set()
    for k in selected:
        source=read_json(preview/'chapters'/k/'source.json')
        names.update(asset for b in source['blocks'] for asset in protocol.required_assets(b))
        names.update(x['asset'] for x in source['fallback'])
    return {name:preview/name for name in sorted(names)}


def compile_chapter(run,state,preview,key,body):
    folder=run/'chapters'/key;(folder/'document.tex').write_text(protocol.document(body))
    if state['compile_unavailable']:
        atomic_json(folder/'compilation-deferred.json',{'status':'not_attempted','reason':state['compile_unavailable']});return
    if remaining(state)<125:
        atomic_json(folder/'compilation-deferred.json',{'status':'not_attempted','reason':'Remaining wall allowance too short'});return
    out=folder/'compilation'
    if out.exists():return
    result=tex_compile.compile_document(protocol.document(body),out,image=protocol.IMAGE,assets=asset_map(preview,key),template='chapter-glm-v1')
    if result['status'] in ('unavailable','adapter_configuration_failure'):
        state['compile_unavailable']=result.get('reason',result['status'])
    save(run,state)


def assemble_book(run,preview):
    target=run/'book';(target/'parts').mkdir(parents=True,exist_ok=True)
    (target/'assets').mkdir(exist_ok=True)
    for name,path in asset_map(preview).items():
        if not (target/name).exists():shutil.copyfile(path,target/name)
    lines=[r'\chapter*{Experimental Gatheral transcription}',
           'UNACCEPTED MinerU-input GLM drafts. Text review and compilation do not establish fidelity. '
           'Missing chapters are explicitly marked. Index references retain original printed-page numbers.']
    inventory=read_json(preview/'inputs.json')['parts'];gaps=[]
    for part in inventory:
        key=part['key']
        if not key.startswith('gatheral-'):continue
        draft=run/'chapters'/key/'draft.tex';source=read_json(preview/'chapters'/key/'source.json')
        if draft.is_file():body=draft.read_text()
        elif key in ('gatheral-front','gatheral-index'):
            body=r'\chapter*{'+part['title']+'}\nSource-page facsimile fallback; not GLM-converted or image-verified.\n'
            body+='\n'.join(r'\clearpage\noindent\includegraphics[width=\linewidth,height=.88\textheight,keepaspectratio]{'+x['asset']+'}' for x in source['fallback'])
        elif key=='gatheral-blank':body=r'\clearpage\null\thispagestyle{empty}\clearpage'+'\n% Verified original blank PDF 199\n'
        elif key in ('gatheral-postscript','gatheral-bibliography'):
            gaps.append(key)
            body=r'\chapter*{Unreviewed native OCR fallback: '+part['title']+'}\n'
            body+='No complete GLM draft is available for this part. Native text is preserved below.\n'
            body+=(preview/'chapters'/key/'source.tex').read_text()
        else:
            gaps.append(key)
            body=r'\chapter*{MISSING DRAFT: '+part['title']+'}\nComplete native extract remains in the inspection package; this chapter is unresolved.\n'
            # Raw native source is retained independently, never portrayed as a model result.
        name=key+'.tex';(target/'parts'/name).write_text(body);lines.append(r'\input{parts/'+name+'}')
    master=protocol.document('\n\n'.join(lines));(target/'master.tex').write_text(master)
    atomic_json(target/'coverage.json',{'mapped_pages':210,'verified_blank_pages':list(inputs.BLANKS),
        'missing_model_parts':gaps,'source_ownership':'one owner each; no overlap/context duplicates',
        'front_and_index':'facsimile fallback, original printed index references',
        'fidelity':'not manually verified; markers/inventories are structural checks only'})
    return target,gaps


def build_report(run,state):
    binding=read_json(run/'binding.json');preview=Path(binding['preview'])
    rows=[];compilations={}
    for t in state['tasks']:
        calls=[c for c in state['calls'] if c['parent']==t['id']]
        output=t.get('output');link=f'<a href="{html.escape(output)}">output</a>' if output else 'none'
        compile_path=run/'chapters'/t['key']/'compilation/result.json'
        compilation=read_json(compile_path)['status'] if compile_path.is_file() else 'not_attempted'
        compilations[t['key']]=compilation
        link+='; compiler: '+html.escape(compilation)
        if compile_path.is_file():link+=f' <a href="chapters/{t["key"]}/compilation/result.json">record</a>'
        rows.append('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in (t['key'],t['phase'],t['status'],len(calls),t.get('error','')))+f'<td>{link}</td></tr>')
    totals={'elapsed_request_seconds':sum(c.get('elapsed_seconds',0) for c in state['calls']),
            'calls_including_failures_readiness':len(state['calls']),
            'prompt_tokens':sum(c.get('metadata',{}).get('usage',{}).get('prompt_tokens',0) for c in state['calls']),
            'completion_tokens':sum(c.get('metadata',{}).get('usage',{}).get('completion_tokens',0) for c in state['calls']),
            'reasoning_tokens_reported':sum(c.get('metadata',{}).get('usage',{}).get('completion_tokens_details',{}).get('reasoning_tokens',0) for c in state['calls']),
            'missing_usage_calls':[c['id'] for c in state['calls'] if not c.get('metadata',{}).get('usage')]}
    summary={'status':state['status'],'preview':str(preview),'run':str(run),'totals':totals,
        'tasks':state['tasks'],'compilations':compilations,'deadline_epoch':state['first_dispatch']+LIMITS['wall_seconds'] if state['first_dispatch'] is not None else None,
        'acceptance':'UNACCEPTED','visual_coverage':'none; does not replace Qwen image review',
        'next_action':'Inspect drafts/reviews and unresolved gaps; never autoapply semantic suggestions'}
    atomic_json(run/'summary.json',summary)
    inventories=read_json(preview/'inputs.json')['parts']
    source_rows=[]
    for part in inventories:
        relative=os.path.relpath(preview/'chapters'/part['key']/'source.tex',run)
        source_rows.append('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in
            (part['key'],f"{part['original_pages'][0]}–{part['original_pages'][-1]}",part['block_count'],
             part['native_math_strings'],part['source_characters'],part['all_native_math_present']))+
            f'<td><a href="{relative}">complete extract</a></td></tr>')
    text=f'''<!doctype html><meta charset="utf-8"><title>Experimental chapter drafts and reviews</title>
<style>body{{font-family:system-ui;max-width:1400px;margin:2em auto}}td,th{{border:1px solid #aaa;padding:.4em}}table{{border-collapse:collapse}}</style>
<h1>Gatheral chapter experiment; Klebaner comparison separately identified</h1>
<p>Status: {html.escape(state['status'])}. MinerU saved extraction → regular glm53-regular → independent text review.
All output UNACCEPTED. No image verification, mathematical certification or automatic semantic repairs.</p>
<p>Calls: {len(state['calls'])}; request seconds: {totals['elapsed_request_seconds']:.1f}.
Missing usage counters are not zero-token evidence. Sampling/thinking overrides omitted; effective reasoning not established.</p>
<p>Complete raw attempts are retained separately. <a href="summary.json">Summary and coverage</a>;
<a href="book/master.tex">Assembled TeX with explicit gaps</a>.</p>
<table><tr><th>Chapter</th><th>Phase</th><th>Outcome</th><th>Calls</th><th>Gap/reason</th><th>Output</th></tr>{''.join(rows)}</table>
<h2>Prepared source accounting (not semantic verification)</h2>
<p>210 Gatheral owned pages once; seven verified blanks. Klebaner physical 106–136 only.
All saved native blocks retained, including page furniture. Native mathematics is not filtered by portable-export grammar.</p>
<table><tr><th>Part</th><th>Original PDF pages</th><th>Blocks</th><th>Native math strings</th><th>Characters</th><th>All native math present</th><th>Source</th></tr>{''.join(source_rows)}</table>'''
    (run/'report.html').write_text(text)


def bundle(run):
    binding,state,preview=verify(run);assemble_book(run,preview);build_report(run,state)
    out=ROOT/'results'/('chapter-glm-inspection-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.zip')
    if out.exists():raise ValueError('Inspection ZIP already exists; preserve it')
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
        report=(run/'report.html').read_text()
        for part in read_json(preview/'inputs.json')['parts']:
            report=report.replace(os.path.relpath(preview/'chapters'/part['key']/'source.tex',run),'source/'+part['key']+'/source.tex')
        z.writestr('report.html',report)
        for name in ('summary.json','binding.json','state.json'):z.write(run/name,name)
        # One portable asset set, shared by chapter TeX and book. No previous runs.
        for p in (run/'book').rglob('*'):
            if p.is_file():z.write(p,str(p.relative_to(run)))
        for p in (run/'chapters').rglob('*'):
            if p.is_file():z.write(p,str(p.relative_to(run)))
        for p in (run/'prepared').rglob('*'):
            if p.is_file():z.write(p,str(p.relative_to(run)))
        for part in read_json(preview/'inputs.json')['parts']:
            for n in ('source.tex','source.json','inventory.json'):
                p=preview/'chapters'/part['key']/n;z.write(p,'source/'+part['key']+'/'+n)
        z.write(preview/'inputs.json','source/inputs.json')
        for call in state['calls']:
            for n in ('outcome.json','final-channel.raw.txt'):
                p=run/'calls'/call['id']/n
                if p.is_file():z.write(p,'calls/'+call['id']+'/'+n)
        z.writestr('README.txt','Experimental UNACCEPTED chapter drafts and text reviews.\n'
            'All assets appear once in book/assets. Compile book/master.tex from book/.\n'
            'For an individual chapter, stay in book/ and compile ../chapters/KEY/document.tex.\n'
            'This package includes complete source extracts, native block sidecars, drafts, reviews,\n'
            'coverage, settings, usage summaries and available compiler logs/PDFs. Full HTTP raw\n'
            'responses and reasoning remain in the separately retained run; failed final-channel\n'
            'text here is NOT a complete draft. No semantic suggestions were applied.\n')
    atomic_json(run/'latest-bundle.json',{'path':str(out),'bytes':out.stat().st_size,'sha256':sha(out)})
    return out


def execute(run,resume=False,client_factory=LocalClient):
    with writer_lock(ROOT):
        binding,state,preview=verify(run)
        if state['first_dispatch'] is not None and not resume:raise StopRun('Existing dispatches: use resume; no reset')
        if remaining(state)<=0:raise StopRun('Eight-hour wall deadline expired; no readiness dispatched')
        # Check only consumed source files, once fully per launch then on changes.
        guard=InputGuard(read_json(preview/'inputs.json')['consumed'])
        guard_code=InputGuard({str(ROOT/p):h for p,h in binding['code'].items()})
        check_other_jobs()
        if resume and (run/'pause.json').exists():(run/'pause.json').unlink()
        state['status']='running';save(run,state)
        try:
            readiness(run,state,client_factory)
            for task in state['tasks']:
                if task['status'] in ('completed','failed','unavailable','unresolved_interruption'):continue
                guard.check();guard_code.check()
                if (run/'pause.json').exists():raise StopRun('Operator pause after current bounded request')
                if remaining(state)<=0 or len(state['calls'])>=LIMITS['calls']:raise StopRun('Wall/call limit reached; pending work retained')
                execute_task(run,state,task,preview,client_factory)
                build_report(run,state)
            state['status']='completed_with_gaps' if any(t['status']!='completed' for t in state['tasks']) else 'drafts_and_reviews_completed_unaccepted'
        except (StopRun,ProbeError,ValueError) as exc:
            state.update(status='stopped',stop_reason=str(exc));print('STOPPED: '+str(exc),flush=True)
        except KeyboardInterrupt:
            state.update(status='interrupted',stop_reason='Interrupted request may have completed remotely; reservation retained, never automatically replayed')
        finally:
            save(run,state);target,gaps=assemble_book(run,preview)
            if not gaps and not state['compile_unavailable'] and remaining(state)>125 and not (target/'compilation').exists():
                assets={str(p.relative_to(target)):p for d in ('assets','parts') for p in (target/d).rglob('*') if p.is_file()}
                tex_compile.compile_document((target/'master.tex').read_text(),target/'compilation',image=protocol.IMAGE,assets=assets,template='chapter-glm-v1')
            build_report(run,state)
            # Only this stopped writer bundles; status never rewrites live evidence.
            print('Inspection ZIP: '+str(bundle(run)),flush=True)
            print(f'Status: {state["status"]}; output: {run}',flush=True)
        return 0 if state['status']=='drafts_and_reviews_completed_unaccepted' else 2


def current():
    if not POINTER.is_file():raise ValueError('No chapter run prepared; use run/prepare')
    run=Path(read_json(POINTER)['run'])
    if not run.is_dir() or not (run/'binding.json').is_file():raise ValueError('Invalid chapter run pointer')
    return run


def ensure_prepared():
    if POINTER.exists():
        run=current();verify(run);return run
    # Reuse already produced complete offline inputs; never duplicate a live cohort.
    candidates=sorted((ROOT/'runs').glob('chapter-glm-input-*/inputs.json'))
    if len(candidates)>1:raise ValueError('Multiple input preparations; select the actual intended one explicitly with prepare --preview')
    preview=candidates[0].parent if candidates else inputs.prepare()
    return initialize(preview)


def persistent(mode):
    if not shutil.which('tmux'):raise ValueError('tmux unavailable; no session started')
    run=ensure_prepared()
    status=read_json(run/'state.json')
    if mode=='run' and status['first_dispatch'] is not None:raise ValueError('Use resume for existing dispatches')
    if mode=='resume' and remaining(status)<=0:raise ValueError('Deadline expired; no budget reset')
    check=subprocess.run(['tmux','has-session','-t',SESSION],capture_output=True,text=True)
    if check.returncode==0:raise ValueError('Chapter tmux session already exists; inspect it, do not duplicate the writer')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    launch=run/'launches'/stamp;launch.mkdir(parents=True,exist_ok=False)
    # Read-only endpoint admission gives the launching terminal an immediate,
    # clear error. The single text readiness still belongs to the persistent job.
    check_other_jobs()
    client=LocalClient(protocol.BASE_URL,protocol.MODEL,purpose='chapter',timeout=10)
    client.discover_model(launch/'endpoint-check')
    health,_=client.chapter_health(launch/'endpoint-check');protocol.health_capacity(health)
    cmd=[str(ROOT/'.venv-control/bin/python'),'-B','-u','-m','probe.chapter_glm','worker','--run',str(run),'--launch',str(launch)]
    if mode=='resume':cmd.append('--resume')
    command='cd '+shlex.quote(str(ROOT))+' && '+shlex.join(cmd)
    subprocess.run(['tmux','new-session','-d','-s',SESSION,command],check=True,capture_output=True,text=True)
    print(f'Book: Gatheral, The Volatility Surface (Klebaner Chapter 4 first). Phase: chapter experiment. '
          f'Model: {protocol.MODEL}. Action: offline checks, then captured text readiness.\n'
          f'Persistent session started: {SESSION}. Inference has not yet been confirmed.\nRun: {run}\nLog: {launch/"terminal.log"}\nStatus: bash scripts/run-chapter-glm.sh status',flush=True)
    time.sleep(.5)
    if (launch/'exit.json').exists():print('Launch exited: '+json.dumps(read_json(launch/'exit.json')))


def worker(run,launch,resume):
    log=launch/'terminal.log'
    with log.open('a',buffering=1) as f:
        os.dup2(f.fileno(),1);os.dup2(f.fileno(),2)
        result=1
        try:
            print('Book: Gatheral, The Volatility Surface. Phase: full offline tests, preparation checks, then regular GLM chapter conversion/review.',flush=True)
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'};env.pop('PDF2TEX_COMPILER_IMAGE',None)
            # Full normal-terminal suite once for a code version; resume reuses
            # that exact passing check. Real compiler executes during the job.
            stamp=ROOT/'results/chapter-glm-tests-passed.json'
            checked=read_json(stamp) if stamp.is_file() else {}
            # Bytecode caches are runtime artifacts, not test sources.
            test_sources=[x for x in test_hashes() if '__pycache__/' not in x['path'] and not x['path'].endswith('.pyc')]
            if checked.get('code')!=code_hashes() or checked.get('tests')!=test_sources:
                result=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','tests','-v'],cwd=ROOT,env=env).returncode
                if result:raise StopRun('Full test suite failed; no inference started. See terminal.log')
                atomic_json(stamp,{'code':code_hashes(),'tests':test_sources,'at':now(),'log':str(log)})
            verify(run)
            result=execute(run,resume)
        except Exception as exc:
            print('ERROR: '+str(exc)+'. No fallback model or service operation.',flush=True);result=2
        finally:atomic_json(launch/'exit.json',{'exit_status':result,'at':now()})
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run','resume','worker','status','pause','bundle'))
    parser.add_argument('--preview',type=Path);parser.add_argument('--run',type=Path)
    parser.add_argument('--launch',type=Path);parser.add_argument('--resume',action='store_true')
    a=parser.parse_args(argv)
    if a.action=='prepare':
        with writer_lock(ROOT):
            if POINTER.exists():print(ensure_prepared())
            else:print(initialize(a.preview) if a.preview else ensure_prepared())
        return 0
    if a.action in ('run','resume'):persistent(a.action);return 0
    run=a.run.resolve() if a.run else current()
    if a.action=='worker':return worker(run,a.launch,a.resume)
    if a.action=='status':
        state=read_json(run/'state.json');print('Run:',run,'\nStatus:',state['status'],'\nCalls:',len(state['calls']),'/ 80')
        print('Remaining wall seconds:',round(remaining(state)), '(clock starts at first dispatch)')
        if state.get('stop_reason'):print('Stop reason:',state['stop_reason'])
        for t in state['tasks']:print(t['id'],t['status'],t.get('error',''))
        for p in sorted((run/'launches').glob('*/exit.json')):print('Launch outcome:',p,read_json(p))
        if (run/'latest-bundle.json').is_file():print('Inspection ZIP:',read_json(run/'latest-bundle.json')['path'])
    elif a.action=='pause':atomic_json(run/'pause.json',{'requested_at':now()});print('Pause requested after current bounded call; idle time continues to count.')
    elif a.action=='bundle':
        with writer_lock(ROOT):print(bundle(run))
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,RuntimeError,ProbeError,subprocess.SubprocessError) as exc:
        print('ERROR: '+str(exc)+'; no service change or model substitution.',file=sys.stderr);raise SystemExit(2)
