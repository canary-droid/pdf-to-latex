"""Experimental candidates and compact views. Never invokes final acceptance."""
from collections import Counter,defaultdict
import csv
import html
import json
import re
from pathlib import Path
import shutil
import zipfile

from .common import atomic_json,read_json,sha,fingerprint,files_manifest
from .portable_export import render_block,portable_document,escape_text,accepted_fragment,safe_compiler_fragment
from .recovery import compatible_fragment
from . import tex_compile


def draft(block):
    try:
        text,packages=render_block(block)
        return {'text':text,'packages':sorted(packages),'format':'portable_latex','export_status':'supported'}
    except ValueError as exc:
        return {'text':json.dumps(block['native'],ensure_ascii=False,indent=2),'packages':[],
            'format':'complete_structured_OCR_JSON','export_status':'unresolved','reason':str(exc)}


def disposition_template(run):
    """Bind a separate assessment to exact historical proposals, never acceptance."""
    source,proposals=candidate_source(run)
    parent,binding,state,preview,meta,units=source
    return {'schema':'candidate-dispositions-v1','assessment':'Codex assessment; not human verification or final acceptance',
        'run':str(parent),'preview':str(preview),'binding_sha256':fingerprint(binding),
        'state_sha256':sha(parent/'state.json'),'preview_manifest_sha256':sha(preview/'manifest.json'),
        'catalog_sha256':fingerprint(proposals),'decisions':[
            {'id':p['id'],'evidence_sha256':fingerprint(p),'disposition':'investigate',
             'whole_block_preserved':False,'reason':'Not yet assessed'} for p in proposals]}


def candidate_source(run):
    # Historical code is explicitly retained in provenance. This is a new linked
    # derivative, not permission to resume/reseal old model requests under new code.
    from .recovery_trial import verified_parent
    source=verified_parent(run,require_recovery_budget=False)
    parent,binding,state,preview,meta,units=source;proposals=[]
    for u in units:
        data=read_json(preview/u['data']);blocks={b['id']:b for b in data['blocks']}
        r=state['units'][u['id']]
        if r['status']!='completed':continue
        call=next(c for c in state['calls'] if c['id']==r['last_call'])
        value=read_json(parent/'calls'/call['id']/'outcome.json')['answer']
        for i,p in enumerate(value['proposals']):
            proposals.append({'id':u['id']+':'+str(i)+':'+fingerprint(p)[:16],
                'proposal':p,'review_call':call['id'],'call_seal_sha256':call['seal_sha256'],
                'category':value['proposal_categories'][i] if u['kind']!='omission' else 'missing_source_content',
                'source_target_sha256':{b:fingerprint(blocks[b]) for b in p['block_ids']}})
    return source,proposals


def reviewed_decisions(path,run,proposals):
    if path is None:return {}
    record=read_json(path);expected=disposition_template(run)
    for key in ('schema','run','preview','binding_sha256','state_sha256','preview_manifest_sha256','catalog_sha256'):
        if record.get(key)!=expected[key]:raise ValueError('Stale/different disposition binding: '+key)
    rows=record.get('decisions',[]);decisions={d['id']:d for d in rows}
    if len(rows)!=len(decisions) or set(decisions)!={p['id'] for p in proposals}:
        raise ValueError('Missing, duplicate or unknown disposition target')
    for p in proposals:
        d=decisions[p['id']]
        if d.get('evidence_sha256')!=fingerprint(p):raise ValueError('Disposition proposal version changed')
        if d.get('disposition') not in ('suitable','deferred','investigate') or not isinstance(d.get('whole_block_preserved'),bool) or not d.get('reason'):
            raise ValueError('Invalid disposition assessment')
    return decisions


def edits_for(blocks,proposals,decisions=None):
    """Apply only explicitly assessed versions; syntax/length are not fidelity."""
    decisions=decisions or {}
    byid={b['id']:b for b in blocks};bytarget=defaultdict(list);records=[]
    for item in proposals:
        p=item['proposal'];record={**item,'status':'deferred','acceptance':'UNACCEPTED'}
        records.append(record)
        if len(p['block_ids'])!=1 or p['block_ids'][0] not in byid:
            record['reason']='Unknown/multiple target; no guessed merge/insertion';continue
        target=p['block_ids'][0];record['target']=target
        decision=decisions.get(item['id']);record['assessment']=decision
        if decision is not None and decision.get('evidence_sha256')!=fingerprint(item):
            raise ValueError('Disposition proposal version changed')
        if not decision or decision.get('disposition')!='suitable' or decision.get('whole_block_preserved') is not True:
            record['reason']='No suitable whole-block assessment: '+(decision.get('reason','') if decision else 'unreviewed');continue
        if p.get('uncertain') or p.get('change_kind')=='uncertain':record['reason']='Uncertain content requires review';continue
        check=compatible_fragment(p,byid[target],item.get('legacy',False));record['compatibility']=check
        if check['status'] not in ('supported','wrapper_required'):record['reason']=check.get('reason',check['status']);continue
        record.update(status='eligible',latex=check['latex'],packages=check['packages'],
            transformation=check['transformation'],original_proposed_bytes=p['suggested_latex'])
        bytarget[target].append(record)
    edits={}
    for target,items in bytarget.items():
        if len({(r['latex'],tuple(sorted(r['proposal'].get('depends_on',[])))) for r in items})>1:
            for r in items:r.update(status='conflicted',reason='Different eligible replacements/dependencies for one source block')
        else:
            edits[target]=items[0];items[0]['duplicate_ids']=[r['id'] for r in items[1:]]
            for r in items[1:]:r.update(status='duplicate',reason='Identical displayed replacement; original proposal retained')
    # A conflict/unsupported/uncertain proposal also prevents another replacement
    # silently winning the same target, even when only one is grammar-supported.
    alltargets=defaultdict(list)
    for r in records:
        if r.get('target'):alltargets[r['target']].append(r)
    for target,items in alltargets.items():
        if len({r['proposal']['suggested_latex'] for r in items})>1:
            edits.pop(target,None)
            for r in items:r.update(status='conflicted',reason='Conflicting complete strings for one target, including deferred alternatives')
    graph=defaultdict(set)
    for r in records:
        if r.get('target'):
            for dep in r['proposal'].get('depends_on',[]):
                graph[r['target']].add(dep);graph[dep].add(r['target'])
    visited=set()
    for start in graph:
        if start in visited:continue
        group=set();todo=[start]
        while todo:
            target=todo.pop()
            if target in group:continue
            group.add(target);todo.extend(graph[target]-group)
        visited.update(group)
        for r in records:
            if r.get('target') in group:r['dependent_group']=sorted(group)
        if not group<=set(edits):
            for target in group:
                r=edits.pop(target,None)
                if r:r.update(status='deferred',reason='Dependent correction group unavailable; no partial application')
    for r in edits.values():r['status']='applied_experimental'
    return edits,records


def queue_class(proposal, before):
    """Model labels cannot hide changed mathematical content as punctuation.

    One plainly unmatched closing parenthesis is a separately recorded editorial
    repair under the user's policy. Ambiguous parentheses/signs/bounds stay main.
    """
    kind=proposal.get('change_kind')
    if kind not in ('cosmetic','editorial_repair'):return 'material_or_uncertain'
    def math_parts(t):
        return re.findall(r'\\\[(.*?)\\\]|\\\((.*?)\\\)|(?<!\\)\$(.*?)(?<!\\)\$',t,re.S)
    old=''.join(''.join(p) for p in math_parts(before));new=''.join(''.join(p) for p in math_parts(proposal['suggested_latex']))
    old=re.sub(r'\s+','',old);new=re.sub(r'\s+','',new)
    if old==new:return 'editorial_or_cosmetic'
    if kind=='editorial_repair' and old.count(')')==old.count('(')+1 and new.count(')')==new.count('('):
        if any(old[:i]+old[i+1:]==new for i,c in enumerate(old) if c==')'):return 'editorial_or_cosmetic'
    return 'material_or_uncertain'


def compiler_checks(outcome,data,out,image):
    checks=[];byid={b['id']:b for b in data['blocks']}
    for i,(p,check) in enumerate(zip(outcome['answer']['proposals'],outcome['export_checks'])):
        b=byid[p['block_ids'][0]];original=draft(b)
        text=check.get('latex',p['suggested_latex'])
        if not check.get('latex') and p.get('fragment_kind')=='math_body' and b['kind']=='equation':text='\\[\n'+text+'\n\\]'
        original_text=original['text'];original_basis=None
        if original['export_status']!='supported':
            raw=b['native'].get('content')
            # An equation block has an explicit math-body contract. Preserve its
            # malformed OCR for isolated diagnosis, never make it exportable.
            if b['kind']=='equation' and isinstance(raw,str) and safe_compiler_fragment(raw):
                original_text='\\[\n'+raw+'\n\\]'
                original_basis={'status':'diagnostic_only_not_exportable','reason':original['reason'],
                    'source_block_sha256':fingerprint(b),'raw_math_body':raw,'transformation':'display_wrappers_for_verified_equation_diagnostic'}
            else:
                checks.append({'status':'not_compiled_unsupported_original','proposal_index':i,'reason':original.get('reason')});continue
        if not safe_compiler_fragment(text):
            checks.append({'status':'not_compiled_unsupported_fragment','proposal_index':i});continue
        packages=set(original['packages'])|set(check.get('packages',[]))|{'amsmath','amssymb','graphicx','inputenc','fontenc'}
        result=tex_compile.compare(original_text,text,out/str(i),packages,image=image)
        if original_basis:result={**result,'original_input_basis':original_basis}
        checks.append(result)
        if result['compiler_feedback_eligible']:
            outcome['compilation']=checks
            return {'kind':'proposal_tex_failure','content':json.dumps(outcome['answer']),
                'errors':[{'path':f'$.proposals[{i}].suggested_latex','message':'Original compiled; proposed fragment introduced a syntax failure'}],
                'compiler_feedback':tex_compile.feedback(result,original_text,text,out/str(i))}
    outcome['compilation']=checks
    return None


def build_candidate(preview,run,out,*,image=None,dispositions=None):
    from .experiment import code_hashes
    source,proposals=candidate_source(run)
    run,binding,state,saved_preview,meta,units=source
    if Path(preview).resolve()!=saved_preview:raise ValueError('Candidate source/review binding differs')
    preview=saved_preview;decisions=reviewed_decisions(dispositions,run,proposals)
    if meta.get('book_review'):
        from .book_review import validate_preparation
        validate_preparation(preview,meta,units)
    out.mkdir(parents=True,exist_ok=False);blocks={};pages={};gaps=[];review_status={};block_images={}
    if dispositions is not None:shutil.copyfile(dispositions,out/'dispositions.json')
    for u in units:
        data=read_json(preview/u['data'])
        for im in data['images']:
            dest=out/im['path'];dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():shutil.copyfile(preview/im['path'],dest)
        for b in data['blocks']:
            blocks[b['id']]=b;review_status[b['id']]=state['units'][u['id']]['status'];block_images[b['id']]=data['images']
        pages.setdefault(data['page_id'],{'data':data,'blocks':[]})['blocks']+=data['blocks']
        r=state['units'][u['id']]
        if r['status']!='completed':gaps.append({'unit':u['id'],'status':r['status']});continue
    edits,records=edits_for(list(blocks.values()),proposals,decisions)
    inventory=[];packages=set();body=[];page_html=[];image_paths={}
    for page_id,page in sorted(pages.items()):
        source=page['data'];body.append(r'\section*{'+escape_text(page_id)+'}')
        page_html.append('<h2>'+html.escape(page_id)+'</h2>')
        for b in sorted(page['blocks'],key=lambda b:b['reading_order']):
            old=draft(b);edit=edits.get(b['id']);new=edit['latex'] if edit else old['text'];status='applied_experimental' if edit else old['export_status']
            row={'block_id':b['id'],'page_id':page_id,'source_location':{'source_id':source['source_id'],'page':source['page'],'bbox':b['bbox']},
                 'source_block_sha256':fingerprint(b),'before':old,'after':new,'status':status,
                 'proposal_id':edit['id'] if edit else None,'draft_sha256':fingerprint(new),
                 'review_status':review_status[b['id']], 'source_images':block_images[b['id']],
                 'source_native':b['native'],'acceptance':'UNACCEPTED'}
            inventory.append(row)
            if status!='unresolved':
                packages.update(edit['packages'] if edit else old['packages']);body.append('% '+b['id']+'\n'+new)
            else:
                body.append(r'\paragraph{Unresolved '+escape_text(b['id'])+'} Complete OCR and source image retained in report/inventory. No editable transcription claimed.')
            page_html.append('<article><h3>'+html.escape(b['id']+' — '+status)+'</h3><p>Before</p><pre>'+html.escape(old['text'])+'</pre><p>Evaluation version</p><pre>'+html.escape(new)+'</pre></article>')
            for im in block_images[b['id']]:page_html.append('<a href="'+im['path']+'">'+html.escape(im['role'])+'</a> ')
        for im in source['images']:
            src=preview/im['path'];dest=out/im['path'];dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():shutil.copyfile(src,dest)
            image_paths[im['path']]=sha(dest)
            page_html.append('<a href="'+im['path']+'">'+html.escape(im['role'])+'</a>')
    if meta.get('book_review'):
        expected=[b for p in read_json(preview/'coverage.json')['pages'] for b in p['block_ids']]
        if [r['block_id'] for r in inventory]!=expected:raise ValueError('Candidate lost/duplicated/reordered owned blocks')
        shutil.copyfile(preview/'bibliography.json',out/'bibliography.json')
        from .book_review import coverage_summary
        atomic_json(out/'review-coverage.json',coverage_summary(preview,state,units))
        atomic_json(out/'unresolved-insertions.json',[r for r in records if not r['proposal']['block_ids']])
    document=portable_document(body,packages)
    (out/'candidate.tex').write_text(document)
    compilation=tex_compile.compile_document(document,out/'build',image=image)
    atomic_json(out/'inventory.json',inventory);atomic_json(out/'changes.json',records)
    bindings={str(run/'binding.json'):sha(run/'binding.json'),str(run/'state.json'):sha(run/'state.json'),str(preview/'manifest.json'):sha(preview/'manifest.json')}
    bindings.update({str(run/'calls'/c['id']/'seal.json'):c['seal_sha256'] for c in state['calls'] if c.get('seal_sha256')})
    bindings.update(meta['source_hashes'])
    if dispositions is not None:bindings[str(Path(dispositions).resolve())]=sha(dispositions)
    atomic_json(out/'provenance.json',{'status':'experimental_candidate_NOT_finally_accepted_or_verified',
        'visual_run':str(run),'preview':str(preview),'bindings':bindings,'code_sha256':code_hashes(),
        'historical_review_code_sha256':meta['code_sha256'],
        'policy':'Exact-version assessments required; no uncertain, conflicted, incomplete, partial dependent or deletion edits',
        'source_gaps':gaps,'applied':len(edits),'unresolved_blocks':sum(r['status']=='unresolved' for r in inventory),
        'compilation':compilation['status'],'source_fidelity':'Bounded Codex proposal assessment only; not human verification',
        'dispositions_sha256':sha(dispositions) if dispositions is not None else None,'final_acceptance':False})
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><h1>Experimental candidate — UNACCEPTED</h1><p>Not a verified transcription. Grammar support and compilation do not establish fidelity.</p><pre>'+html.escape(json.dumps(read_json(out/'provenance.json'),indent=2))+'</pre>'+''.join(page_html))
    from .experiment import seal
    seal(out);return out


def proposal_validation(outcome):
    """Keep response validity, exportability, compilation and deferral distinct."""
    rows=[]
    for i,(proposal,check) in enumerate(zip(outcome.get('answer',{}).get('proposals',[]),outcome.get('export_checks',[]))):
        builds=outcome.get('compilation',[])
        build=builds[i] if i<len(builds) else {}
        compilation=build.get('status','not_run')
        exportable=check['status'] in ('supported','wrapper_required')
        if not exportable:resolution='unresolved_export'
        elif proposal.get('uncertain') or proposal.get('change_kind')=='uncertain':resolution='deferred_uncertain'
        elif compilation=='both_compiled':resolution='exportable_compiled_unaccepted'
        elif build.get('proposed',{}).get('status','').startswith('passed'):resolution='exportable_proposed_compiled_original_unresolved'
        else:resolution='exportable_compilation_unresolved'
        rows.append({'proposal_index':i,'block_ids':proposal['block_ids'],
            'response_validation':outcome.get('response_validation','not_established'),
            'export_check':check['status'],'exportable':exportable,'diagnostic':check.get('reason'),
            'compilation':compilation,'original_compilation':build.get('original',{}).get('status'),
            'proposed_compilation':build.get('proposed',{}).get('status'),
            'resolution':resolution,'acceptance':'UNACCEPTED'})
    return rows


def usage_accounting(outcomes):
    """Count each durable call once, including nested failed-response metrics."""
    import math
    calls={}
    for o in outcomes:
        if o['call'] in calls and calls[o['call']]!=o:raise ValueError('Conflicting duplicate call in accounting')
        calls[o['call']]=o
    def totals(items):
        result={'calls':len(items)}
        for field in ('prompt_tokens','completion_tokens','reasoning_tokens','request_latency_seconds'):
            values=[]
            for o in items:
                failed=o.get('failure',{});usage=o.get('usage') or failed.get('usage') or {}
                if field=='request_latency_seconds':v=o.get('latency_seconds',failed.get('latency_seconds'))
                elif field=='reasoning_tokens':v=(usage.get('completion_tokens_details') or {}).get(field,usage.get(field))
                else:v=usage.get(field)
                if type(v) in (int,float) and math.isfinite(v) and v>=0:values.append(v)
            result[field]={'total':sum(values) if len(values)==len(items) else None,
                'reported_sum':sum(values),'reported_calls':len(values),'missing_calls':len(items)-len(values)}
        return result
    values=list(calls.values());recovery=[o for o in values if o['method']!='baseline']
    return {'all':totals(values),'recovery':totals(recovery),
        'current_run':totals([o for o in values if o.get('origin')!='inherited']),
        'inherited':totals([o for o in values if o.get('origin')=='inherited']),
        'meaning':'Request latency sums are not full wall/admission time. Null totals mean missing counters, not zero. Inherited calls are included once.'}


def experiment_report(preview,out,*,report_dir=None):
    if read_json(preview/'preview.json').get('critic_route'):
        from .critic_route import report
        return report(out,report_dir=report_dir)
    dest=Path(report_dir) if report_dir is not None else out
    dest.mkdir(parents=True,exist_ok=True)
    meta=read_json(preview/'preview.json');units=read_json(preview/'units.json');state=read_json(out/'state.json')
    rows=[];main=[];cosmetic=[]
    for spec in units:
        r=state['units'][spec['id']];data=read_json(preview/spec['data']);outcomes=[]
        for c in state['calls']:
            if c['parent']==spec['id'] and (out/'calls'/c['id']/'outcome.json').exists():
                outcomes.append({'call':c['id'],'method':c['method'],
                    'origin':'inherited' if c['id'] in state.get('inheritance',{}).get('call_ids',[]) else 'current_run',
                    **read_json(out/'calls'/c['id']/'outcome.json')})
        if spec['kind']=='critic':
            from . import text_critic
            for o in outcomes:
                if 'failure' in o and 'provisional_diagnostics' not in o:
                    o['provisional_diagnostics']=text_critic.rejected_diagnostics(o['failure'],data,meta['config']['model'])
        from .experiment import repair_seed
        seed=repair_seed(preview,meta,spec['id'],r.get('last_call'))
        latest=next((o for o in reversed(outcomes) if 'answer' in o),{})
        row={'id':spec['id'],'status':r['status'],'location':spec.get('location'),
            'unavailable_reason':r.get('reason'),
            'split':spec.get('split'),'outcomes':outcomes,'data':data,
            'export_reassessment':seed,'latest_proposal_validation':proposal_validation(latest),
            'latest_proposal_response_call':latest.get('call')};rows.append(row)
        heading='<h3>'+html.escape(spec['id']+' — '+r['status'])+'</h3>'
        links=''
        for im in data.get('images',[]):links+='<a href="'+str((preview/im['path']).resolve())+'">'+html.escape(im['role'])+'</a> '
        content=heading+links+'<p>'+html.escape(r.get('reason') or '')+'</p><details><summary>Exact original draft / source map</summary><pre>'+html.escape(json.dumps(data,ensure_ascii=False,indent=2))+'</pre></details>'
        if seed:content+='<p>Current-code export reassessment; original sealed result remains unchanged.</p><pre>'+html.escape(json.dumps(seed,ensure_ascii=False,indent=2))+'</pre>'
        if r.get('limits') or r.get('retry_deferred'):
            content+='<p>Unresolved/deferred: '+html.escape(str(r.get('limits') or r.get('retry_deferred')))+'</p>'
        for o in outcomes:
            content+='<p>Call '+o['call']+' '+o['method']+' — '+o['status']+' ('+o['origin']+')</p>'
            content+='<pre>'+html.escape(json.dumps(proposal_validation(o),indent=2))+'</pre>'
            if 'failure' in o:content+='<pre>'+html.escape(json.dumps(o['failure'],ensure_ascii=False,indent=2))+'</pre>'
            if 'provisional_diagnostics' in o:
                content+='<h4>Provisional diagnostics — response rejected, not completed or accepted</h4><p>Exact citation validation is not mathematical correctness. Invalid findings are retained separately.</p><pre>'+html.escape(json.dumps(o['provisional_diagnostics'],ensure_ascii=False,indent=2))+'</pre>'
            value=o.get('answer',{})
            if 'findings' in o:
                from .sciwrite_subset import finding_views
                views=finding_views(o['findings'])
                content+='<pre>'+html.escape(json.dumps({k:views[k] for k in ('material','context','visual')},ensure_ascii=False,indent=2))+'</pre>'
                cosmetic+=views['editorial']
            # Group identical displayed proposals; retain all source indices in JSON.
            displayed={}
            for i,p in enumerate(value.get('proposals',[])):
                key=fingerprint([p['block_ids'],p['suggested_latex']])
                displayed.setdefault(key,{'proposal':p,'indices':[]})['indices'].append(i)
            for d in displayed.values():
                p=d['proposal'];render='<pre>'+html.escape(json.dumps(d,ensure_ascii=False,indent=2))+'</pre>'
                before='\n'.join(draft(b)['text'] for b in data.get('blocks',[]) if b['id'] in p['block_ids'])
                if queue_class(p,before)=='editorial_or_cosmetic':cosmetic.append({'unit':spec['id'],**d})
                else:content+=render
            if o.get('export_checks'):content+='<details><summary>Export checks (not compilation)</summary><pre>'+html.escape(json.dumps(o['export_checks'],indent=2))+'</pre></details>'
            if o.get('compilation'):content+='<details><summary>Compilation results (not source fidelity)</summary><pre>'+html.escape(json.dumps(o['compilation'],indent=2))+'</pre></details>'
        main.append(content)
    first=sum(bool(r['outcomes']) and r['outcomes'][0]['status']=='completed' for r in rows)
    recoveries=Counter(o['method'] for r in rows for o in r['outcomes'][1:] if o['status']=='completed')
    accounting=usage_accounting([o for r in rows for o in r['outcomes']])
    summary={'status':state['status'],'first_attempt_success':first,'recovery_by_method':dict(recoveries),
        'first_attempt_json_schema_coverage_success':sum(bool(row['outcomes']) and row['outcomes'][0].get('response_validation')=='passed' for row in rows),
        'mechanical_recoveries':sum(bool(o.get('mechanical_recovery')) for r in rows for o in r['outcomes']),
        'unit_statuses':dict(Counter(r['status'] for r in rows)), 'failure_reasons':dict(Counter(o['failure']['kind'] for r in rows for o in r['outcomes'] if 'failure' in o)),
        'assessment_statuses':dict(Counter(o['assessment'] for r in rows for o in r['outcomes'] if 'assessment' in o)),
        'calls':len(state['calls']),'elapsed_seconds':state['elapsed_seconds'],'gate':state['gate'],
        'inherited_calls':len(state.get('inheritance',{}).get('call_ids',[])),
        'current_run_calls':len(state['calls'])-len(state.get('inheritance',{}).get('call_ids',[])),
        'inheritance':state.get('inheritance'),'dispatch_scope':(meta.get('repair_derivative') or meta.get('continuation_derivative') or {}).get('scope','Prepared stage selection'),
        'allowed_repair_units':meta.get('repair_derivative',{}).get('allowed_units'),
        'allowed_continuation_units':meta.get('continuation_derivative',{}).get('allowed_units'),
        'latest_proposal_resolutions':dict(Counter(p['resolution'] for row in rows for p in row['latest_proposal_validation'])),
        'attempt_compilation_statuses':dict(Counter(c['status'] for row in rows for o in row['outcomes'] for c in o.get('compilation',[]))),
        'limits':meta['limits'],'extra_completion_tokens':accounting['recovery']['completion_tokens']['total'],
        'extra_latency_seconds':accounting['recovery']['request_latency_seconds']['total'],
        'usage_accounting':accounting,
        'provisional_findings_by_call':{o['call']:len(o['provisional_diagnostics']['validated_findings']) for r in rows for o in r['outcomes'] if o.get('provisional_diagnostics',{}).get('status')=='provisional'},
        'report_source_run':str(out),'derived_report':dest!=out,
        'useful_material_corrections':'not_source_assessed','missed_or_harmful_control_changes':'not_source_assessed',
        'critic_false_alarms':'not_human_assessed','human_decisions':'not_counted','acceptance':'UNACCEPTED',
        'fidelity':'Valid response / gate pass does not establish exportability, compilation or mathematical correctness; regions do not cover whole-page omissions'}
    if meta.get('book_review'):
        from .book_review import coverage_summary
        summary['owned_page_coverage']=coverage_summary(preview,state,units)
        summary['fidelity']='Recognized-block and omission-check technical statuses are separate; neither certifies fidelity. Insertions remain deferred.'
    atomic_json(dest/'summary.json',summary);atomic_json(dest/'ledger.json',rows)
    text='# Recovery/critic experiment\n\nAll proposals/findings UNACCEPTED.\n\n```json\n'+json.dumps(summary,indent=2)+'\n```\n'
    (dest/'report.md').write_text(text)
    (dest/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Recovery / critic experiment</title><h1>Recovery / critic — UNACCEPTED</h1><p>Technical success, claimed coverage and fidelity are distinct.</p><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre>'+''.join(main)+'<details><summary>Editorial/cosmetic observations (all retained)</summary><pre>'+html.escape(json.dumps(cosmetic,ensure_ascii=False,indent=2))+'</pre></details>')
    with (dest/'failures.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['unit','call','method','reason','errors']);w.writeheader()
        for r in rows:
            for o in r['outcomes']:
                if 'failure' in o:w.writerow({'unit':r['id'],'call':o['call'],'method':o['method'],'reason':o['failure']['kind'],'errors':json.dumps(o['failure']['errors'])})
    return summary


def bundle(root,preview,out):
    from .experiment import new_path
    experiment_report(preview,out)
    dest=Path(root)/'results'/(new_path(root,out.name+'-inspection').name+'.zip');dest.parent.mkdir(exist_ok=True)
    document=(out/'report.html').read_text();images={}
    for u in read_json(preview/'units.json'):
        data=read_json(preview/u['data'])
        for im in data.get('images',[]):
            image=preview/im['path'];key='images/'+sha(image)+'.png';images[key]=image
            document=document.replace(str(image.resolve()),key)
    with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED) as z:
        z.writestr('inspection.html',document)
        for name in ('report.md','summary.json','ledger.json','failures.csv','binding.json','state.json'):z.write(out/name,name)
        for name in ('preview.json','units.json','selection.json'):
            if (preview/name).exists():z.write(preview/name,'prepared/'+name)
        for name in ('repair/seed.json','repair/provenance.json','repair/inherited-state.json',
                     'continuation/provenance.json','continuation/inherited-state.json'):
            if (preview/name).exists():z.write(preview/name,'prepared/'+name)
        for name,path in images.items():z.write(path,name)
    with zipfile.ZipFile(dest) as z:
        if z.testzip():raise ValueError('Invalid inspection archive')
    record={'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest)}
    atomic_json(out/'latest-bundle.json',record);print('Inspection ZIP:',dest,flush=True);return record
