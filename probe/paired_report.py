"""Task 5 inspection reports, partial bundles and neutral future text critique data."""
from collections import Counter
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import tempfile
import uuid
import zipfile

from .common import atomic_json, check_manifest, read_json, sha
from .paired_inputs import CONFIG, verify_preview

AUDIT_PLAN = '''Post-run source audit (not yet performed)
Compare both arms' FULL replacements with source images, not just the named issue. Include unchanged/no-proposal controls, failures, incomplete pairs and ambiguous native alignments. Record separately for each arm: source-confirmed improvement, harmful/unnecessary change, residual/missed error, unreadable/uncertain detail, missing/invalid draft and compilation/insertion issues. Preserve apparent author errors. Classify substantive changes, punctuation and style separately. Compare priority and remainder separately; include all attempted-arm failures and unmatched pairs, rather than analyzing successful pairs alone. Record tokens, latency, unresolved cases and manual review burden without inferring savings from proposal counts. First inspect the previously selected priority core; remainder bundle selection prioritizes attempted failures/incomplete pairs, then different validated arm answers, then other attempted regions, in frozen order (at most twelve). This is a diagnostic selection, not an unbiased accuracy sample. Codex source-image judgments must be labelled Codex judgments, not independent human gold. The sixteen-page cohort includes known/previously inspected development cases; no whole-book claim and no omission coverage outside recognized blocks. A later text-only GLM critique cannot establish visual fidelity. All proposals remain UNACCEPTED.
'''


def collect(out):
    binding=read_json(out/'binding.json');preview=Path(binding['preview'])
    state=read_json(out/'state.json');order=read_json(preview/'evaluator-manifest.json')['regions']
    rows=[]
    for spec in order:
        ordinal=f"{spec['ordinal']:03d}";answers={}
        for arm in ('A','B'):
            key=ordinal+'-'+arm;rec=state['requests'][key];folder=out/'requests'/key
            item={'status':rec['status']}
            if (folder/'outcome.json').exists():
                item.update(read_json(folder/'outcome.json'))
                # Final assistant content can be malformed JSON, but no reasoning/raw API payload is exported.
                if (folder/'assistant-response.json').exists():item['final_content']=read_json(folder/'assistant-response.json')['content']
            answers[arm]=item
        paired=all(a['status']=='completed' for a in answers.values())
        rows.append({**spec,'arms':answers,'matched_completed_pair':paired,
            'pair_answer_difference':paired and answers['A']['answer']!=answers['B']['answer'],
            'source_assessment':'not performed; proposal counts are not useful/harmful corrections'})
    return preview,state,rows


def aggregate(rows):
    def stats(group):
        result={'regions':len(group),'matched_completed_pairs':sum(r['matched_completed_pair'] for r in group),
                'incomplete_or_failed_pairs':sum(not r['matched_completed_pair'] for r in group),'arms':{}}
        for arm in ('A','B'):
            items=[r['arms'][arm] for r in group]
            result['arms'][arm]={'statuses':dict(Counter(a['status'] for a in items)),
                'failure_reasons':dict(Counter(a.get('failure_kind','other') for a in items if a['status'] in ('failed','interrupted'))),
                'proposals':sum(len(a.get('answer',{}).get('proposals',[])) for a in items),
                'model_reported_categories':dict(Counter(c for a in items for c in a.get('answer',{}).get('proposal_categories',[]))),
                'model_reported_observations':dict(Counter(o['category'] for a in items for o in a.get('answer',{}).get('observations',[]))),
                'uncertain_proposals':sum(p['uncertain'] for a in items for p in a.get('answer',{}).get('proposals',[])),
                'usage':{k:sum(a.get('usage',{}).get(k,0) for a in items) for k in ('prompt_tokens','completion_tokens','total_tokens')},
                'reasoning_tokens':sum(a.get('usage',{}).get('completion_tokens_details',{}).get('reasoning_tokens',0) for a in items),
                'latency_seconds':sum(a.get('latency_seconds') or 0 for a in items)}
        return result
    return {name:stats(group) for name,group in [('overall',rows),('priority',[r for r in rows if r['phase']=='priority']),('remainder',[r for r in rows if r['phase']=='remainder'])]}


def critic(preview,rows):
    result=[]
    for r in rows:
        folder=preview/'regions'/f"{r['ordinal']:03d}";data=read_json(folder/'input.json')
        result.append({'region_id':r['region_id'],'page':r['page'],
            'input_sha256':sha(folder/'input.json'),'native_sha256':sha(folder/'native.json'),
            'source_images':[{k:v for k,v in im.items() if k in ('sha256','bbox','role')} for im in data['images']],
            'saved_ocr':data['blocks'][0]['native'],'draft_by_block':data['draft_by_block'],
            'native_text':read_json(folder/'native.json')['text'],
            'qwen':{arm:{'validation_status':a['status'],'proposals':a.get('answer',{}).get('proposals',[]),
                        'observations':a.get('answer',{}).get('observations',[])} for arm,a in r['arms'].items()}})
    return {'notice':'NEUTRAL TEXT-ONLY EXPORT: cannot establish visual/source fidelity. No GLM call. Text streams and UNACCEPTED proposals may all be wrong. No evaluator labels.',
            'regions':result}


def html_report(preview,state,rows,image_prefix,*,compact=False):
    esc=lambda x:html.escape(str(x))
    parts=['<!doctype html><meta charset="utf-8"><title>Paired Qwen native-evidence trial</title>',
        '<style>body{font:15px system-ui;max-width:1100px;margin:2em auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}img{max-width:100%}details{border-top:1px solid #bbb;padding:1em}</style>',
        '<h1>Paired native-evidence trial — UNACCEPTED</h1><p>Status: '+esc(state['status'])+'</p>',
        '<p>Completed means response format, identity and claimed region coverage passed. Fidelity is NOT scored. No proposals accepted. Context is not reviewed coverage; whole-page omissions outside recognized regions are excluded.</p>',
        '<p>Each pair uses fresh conversations. A has source images + OCR; B adds native PDF evidence. Categories are model reports, not source-confirmed useful/harmful changes.</p>',
        '<p><a href="aggregate.json">Overall / priority / remainder totals</a> | <a href="ledger.json">All 267 per-region records</a> | <a href="neutral-critic.json">Future text-only critique export (no visual qualification)</a> | <a href="source-audit-plan.txt">Post-run source audit plan</a></p>',
        '<pre>'+esc(json.dumps({'elapsed_seconds':state.get('elapsed_seconds'),'gate':state.get('gate'),'counts':state.get('counts'),'error':state.get('error')},indent=2))+'</pre>']
    if compact:parts.append('<p>Images below cover the 48 priority cases plus at most twelve diagnostic remainder cases. Complete ledgers include pending and failed work. This image selection is not an accuracy sample.</p>')
    for r in rows:
        folder=preview/'regions'/f"{r['ordinal']:03d}";data=read_json(folder/'input.json')
        parts += ['<details><summary>'+esc(r['region_id'])+' original PDF '+str(r['page']['original_physical_page'])+' — '+r['phase']+
            ' — A: '+r['arms']['A']['status']+' / B: '+r['arms']['B']['status']+'</summary>',
            '<p>Pilot alignment: '+esc(r['alignment'])+'; evaluator stratum flagged='+str(r['flagged'])+'. These labels were NOT model inputs.</p>']
        for im in data['images']:
            link=image_prefix+im['path']
            parts.append('<p><a href="'+esc(link)+'">'+esc(im['role'])+'</a></p>')
            if im['role']=='selected detail':parts.append('<img loading="lazy" src="'+esc(link)+'">')
        parts+=['<h3>Saved OCR / draft</h3><pre>'+esc(json.dumps({'ocr':data['blocks'][0]['native'],'draft':data['draft_by_block']},ensure_ascii=False,indent=2))+'</pre>',
            '<h3>Native evidence (not authoritative)</h3><pre>'+esc(read_json(folder/'native.json')['serialization'])+'</pre>']
        for arm,a in r['arms'].items():parts.append('<h3>Arm '+arm+' — UNACCEPTED</h3><pre>'+esc(json.dumps(a,ensure_ascii=False,indent=2))+'</pre>')
        parts.append('</details>')
    return '\n'.join(parts)


def write_report(out):
    preview,state,rows=collect(out)
    atomic_json(out/'aggregate.json',aggregate(rows));atomic_json(out/'ledger.json',rows)
    atomic_json(out/'neutral-critic.json',critic(preview,rows))
    (out/'source-audit-plan.txt').write_text(AUDIT_PLAN)
    path=out/'report.html';temp=out/'report.html.tmp'
    temp.write_text(html_report(preview,state,rows,os.path.relpath(preview,out)+'/'));temp.replace(path)
    return rows


def diagnostic_selection(rows):
    def score(r):
        arms=r['arms'].values()
        if any(a['status'] in ('failed','interrupted','dispatched') for a in arms):return 0
        if not r['matched_completed_pair']:return 1
        if r['pair_answer_difference']:return 2
        return 3
    attempted=[r for r in rows if r['phase']=='remainder' and any(a['status']!='pending' for a in r['arms'].values())]
    return [r for r in rows if r['phase']=='priority']+sorted(attempted,key=lambda r:(score(r),r['ordinal']))[:12]


def bundle(root,out):
    binding=read_json(out/'binding.json');preview=Path(binding['preview'])
    verify_preview(preview,binding['preview_manifest_sha256'])
    for folder in (out/'requests').glob('*') if (out/'requests').exists() else []:
        if (folder/'seal.json').exists() and not check_manifest(folder,read_json(folder/'seal.json')+[{'path':'seal.json','sha256':sha(folder/'seal.json')}]):raise ValueError('Changed outcome evidence')
    rows=write_report(out);state=read_json(out/'state.json');chosen=diagnostic_selection(rows)
    name=out.name+'-inspection-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]+'.zip'
    target=root/'results'/name;target.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='paired-inspection-') as temp:
        dest=Path(temp)
        for name in ('aggregate.json','ledger.json','neutral-critic.json','source-audit-plan.txt'):(dest/name).write_bytes((out/name).read_bytes())
        atomic_json(dest/'configuration.json',{'config':CONFIG,'binding':binding,'state_without_requests':{k:v for k,v in state.items() if k!='requests'}})
        atomic_json(dest/'image-selection.json',{'rule':'All 48 priority; remainder failures/interrupted first, then incomplete pairs, then different validated answers, then other attempted pairs; frozen order breaks ties; at most twelve remainder.',
            'regions':[r['region_id'] for r in chosen]})
        (dest/'inspection.html').write_text(html_report(preview,state,chosen,'',compact=True))
        (dest/'images').mkdir()
        for r in chosen:
            folder=preview/'regions'/f"{r['ordinal']:03d}";data=read_json(folder/'input.json')
            for im in data['images']:
                p=dest/im['path']
                if not p.exists():p.write_bytes((preview/im['path']).read_bytes())
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED) as archive:
            for p in sorted(dest.rglob('*')):
                if p.is_file():archive.write(p,out.name+'/'+p.relative_to(dest).as_posix())
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:raise ValueError('Inspection ZIP integrity failure')
    result={'path':str(target),'bytes':target.stat().st_size,'sha256':sha(target),'region_images':len(chosen),'created_at':datetime.now(timezone.utc).isoformat()}
    atomic_json(out/'latest-bundle.json',result);print('Inspection ZIP:',json.dumps(result),flush=True)
    return result
