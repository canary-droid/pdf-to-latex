"""Side-by-side DeepSeek/Qwen Arm A outcomes; no correctness scoring or acceptance."""
from collections import Counter
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import tempfile
import uuid
import zipfile

from .common import atomic_json, read_json, sha
from .deepseek_inputs import CONFIG, checked_seal, latex_checks, verify_preview


def result(folder,status):
    item={'status':status,'acceptance':'UNACCEPTED'}
    if (folder/'outcome.json').exists():item.update(read_json(folder/'outcome.json'))
    content=None
    if (folder/'assistant-response.json').exists():
        answer=read_json(folder/'assistant-response.json');content=answer.get('content')
        for k in ('finish_reason','usage','latency_seconds','actual_model'):item[k]=answer.get(k,item.get(k))
    else:
        # Retain final text and metadata even for invalid/truncated protocol responses;
        # never copy reasoning_content or raw request payloads to inspection artifacts.
        for p in folder.glob('attempts/*/response.raw'):
            try:
                raw=read_json(p);choice=(raw.get('choices') or [{}])[0]
                content=choice.get('message',{}).get('content')
                item['finish_reason']=choice.get('finish_reason');item['actual_model']=raw.get('model')
                item['usage']=raw.get('usage',item.get('usage',{}))
            except (ValueError,AttributeError,IndexError,TypeError):pass
        for p in folder.glob('attempts/*/record.json'):
            rec=read_json(p);item['latency_seconds']=rec.get('latency_seconds',item.get('latency_seconds'))
    item['final_answer_available']=bool(content)
    item['final_content']=content
    if item.get('answer') is not None:item['latex_checks']=latex_checks(item['answer'])
    return item


def collect(out):
    preview=Path(read_json(out/'binding.json')['preview']);meta=read_json(preview/'preview.json')
    state=read_json(out/'state.json');rows=[]
    qwen=Path(meta['historical_run']);qs=read_json(qwen/'state.json')
    for spec in read_json(preview/'order.json'):
        key=f"{spec['ordinal']:03d}";folder=preview/'regions'/key;data=read_json(folder/'input.json')
        q=result(qwen/'requests'/(key+'-A'),qs['requests'].get(key+'-A',{}).get('status','missing'))
        d=result(out/'requests'/key,state['requests'][key]['status'])
        if data['blocks'][0]['id']!=spec['region_id']:raise ValueError('Report region mismatch')
        categories=[c for r in (q,d) for c in r.get('answer',{}).get('proposal_categories',[])]
        group='content_or_uncertainty' if any(c in ('content','uncertainty') for c in categories) else 'punctuation_or_style' if categories else 'unchanged_or_no_usable_proposal'
        rows.append({**spec,'qwen':q,'deepseek':d,'matched_valid_pair':q['status']=='completed' and d['status']=='completed',
            'review_group':group,'original_draft':data['draft_by_block'],'saved_ocr':data['blocks'][0]['native'],
            'images':data['images'],'fidelity':'unassessed; no accepted corrections'})
    return preview,state,rows


def aggregate(rows):
    def stats(group):
        r={'regions':len(group),'matched_valid_pairs':sum(x['matched_valid_pair'] for x in group),
           'missing_or_nonvalid_pairs':sum(not x['matched_valid_pair'] for x in group)}
        for model in ('qwen','deepseek'):
            items=[x[model] for x in group]
            r[model]={'status_counts':dict(Counter(x['status'] for x in items)),
                'final_answers_available':sum(x['final_answer_available'] for x in items),
                'failure_kinds':dict(Counter(x.get('failure_kind','unknown') for x in items if x['status'] in ('failed','interrupted'))),
                'finish_reasons':dict(Counter(str(x.get('finish_reason')) for x in items)),
                'proposals':sum(len(x.get('answer',{}).get('proposals',[])) for x in items),
                'model_reported_categories':dict(Counter(c for x in items for c in x.get('answer',{}).get('proposal_categories',[]))),
                'unsupported_latex':sum(y['status']=='unsupported_export_blocked' for x in items for y in x.get('latex_checks',[])),
                'tokens':{k:sum((x.get('usage') or {}).get(k,0) for x in items) for k in ('prompt_tokens','completion_tokens','total_tokens')},
                'latency_seconds':sum(x.get('latency_seconds') or 0 for x in items)}
        return r
    return {name:stats(group) for name,group in [('overall',rows),('initial_gate',rows[:12]),('remaining',rows[12:])]}


def render(preview,state,rows,prefix):
    esc=lambda x:html.escape(str(x))
    parts=['<!doctype html><meta charset="utf-8"><title>DeepSeek vs historical Qwen Arm A</title><style>body{font:15px system-ui;max-width:1100px;margin:2em auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}img{max-width:100%}details{border-top:1px solid;padding:1em}</style>',
        '<h1>DeepSeek vs Qwen Arm A — UNACCEPTED</h1><p>Status: '+esc(state['status'])+'</p>',
        '<p>Identical source/OCR inputs; models and deployments differ. This is not a quantization-only experiment. Successful format, agreement and proposal counts are not mathematical accuracy. No proposals are accepted or compiled.</p>',
        '<p><a href="aggregate.json">Aggregate / gate / remainder</a> | <a href="ledger.json">Complete region ledger</a></p>',
        '<p>Review complete replacements for signs, indices, bounds, grouping, conditions, theorem/logical meaning and references. Category labels are model claims: punctuation can affect meaning. Source errors must be preserved; suspected source mistakes remain observations. Unsupported LaTeX is export-blocked, not repaired.</p>']
    for group,title in [('content_or_uncertainty','Content and uncertainty — inspect first'),('punctuation_or_style','Punctuation and style — separate review'),('unchanged_or_no_usable_proposal','Unchanged controls / failed or missing answers')]:
        parts.append('<h2>'+title+'</h2>')
        for r in (x for x in rows if x['review_group']==group):
            parts+=['<details><summary>'+esc(r['region_id'])+' — PDF '+str(r['page']['original_physical_page'])+' / printed '+str(r['printed_page'])+
                ' — Qwen '+r['qwen']['status']+' / DeepSeek '+r['deepseek']['status']+'</summary>',
                '<p>Printed folio mapping: '+esc(r['printed_page_basis'])+'</p>']
            for im in r['images']:
                path=prefix+im['path'];parts.append('<p><a href="'+esc(path)+'">'+esc(im['role'])+'</a></p>')
                if im['role']=='selected detail':parts.append('<img loading="lazy" src="'+esc(path)+'">')
            parts+=['<h3>Exact old draft / structured OCR</h3><pre>'+esc(json.dumps({'draft':r['original_draft'],'ocr':r['saved_ocr']},indent=2,ensure_ascii=False))+'</pre>']
            for name in ('qwen','deepseek'):
                parts.append('<h3>'+name+' — exact full proposed replacements and validation</h3><pre>'+esc(json.dumps(r[name],indent=2,ensure_ascii=False))+'</pre>')
            parts.append('</details>')
    return '\n'.join(parts)


def write_report(out):
    preview,state,rows=collect(out)
    atomic_json(out/'ledger.json',rows);atomic_json(out/'aggregate.json',aggregate(rows))
    temp=out/'report.html.tmp';temp.write_text(render(preview,state,rows,os.path.relpath(preview,out)+'/'));temp.replace(out/'report.html')
    return rows


def bundle(root,out):
    binding=read_json(out/'binding.json');preview=Path(binding['preview']);verify_preview(preview,binding['preview_manifest_sha256'])
    state=read_json(out/'state.json')
    for key,rec in state['requests'].items():
        if rec.get('seal_sha256'):checked_seal(out/'requests'/key,rec['seal_sha256'],'seal.json')
    rows=write_report(out)
    # All 267 existing crops are small enough for a compact image-deduplicated archive.
    name=out.name+'-inspection-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]+'.zip'
    target=root/'results'/name;target.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='deepseek-report-',dir=root/'results') as tmp:
        dest=Path(tmp);(dest/'images').mkdir()
        for n in ('aggregate.json','ledger.json'):(dest/n).write_bytes((out/n).read_bytes())
        atomic_json(dest/'configuration.json',{'binding':binding,'state':{k:v for k,v in state.items() if k!='requests'},
            'note':'Raw API payloads/base64/reasoning remain in live run. All proposals UNACCEPTED; exact answer content retained without repair.'})
        (dest/'inspection.html').write_text(render(preview,state,rows,''))
        for r in rows:
            for im in r['images']:
                p=dest/im['path']
                if not p.exists():p.write_bytes((preview/im['path']).read_bytes())
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as archive:
            for p in sorted(dest.rglob('*')):
                if p.is_file():archive.write(p,out.name+'/'+p.relative_to(dest).as_posix())
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:raise ValueError('ZIP CRC failed')
    result={'path':str(target),'bytes':target.stat().st_size,'sha256':sha(target)}
    atomic_json(out/'latest-bundle.json',result);print('Report:',out/'report.html','Inspection ZIP:',json.dumps(result),flush=True)
    return result
