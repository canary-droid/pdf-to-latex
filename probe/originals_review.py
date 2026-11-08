"""Focused review material from saved outputs; no inference or acceptance."""
import hashlib
import json
from pathlib import Path
import re
from .common import atomic_json, read_json, sha
from . import source_library, originals_recovery as recovery, originals_selection as selection

ANFUSO='original-496de5aa992285e2'
PRIORITY=re.compile(r'(?i)sign|coefficient|bound|index|indices|assum|independen|algorithm|numerical|variance|covariance|drift|denominator|numerator|equation')


def bucket(item):
    claim=' '.join(str(item.get(k,'')) for k in ('status','claimed_status','text'))
    if re.search(r'(?i)unresolved|uncertain|ambiguous|requires.*(?:image|inspection)|hypothes',claim):return 'uncertain_claims'
    if re.search(r'(?i)unapplied|not applied|suggest|propos|rejected|withdrawn',claim):return 'unapplied_suggestions'
    if re.search(r'(?i)applied|resolved_claim|corrected|restored',claim):return 'applied_changes_claimed'
    return 'uncertain_claims' if item.get('category')=='material' else 'informational'


def sampled_blocks(native, excluded_pages=(), count=1):
    candidates=[b for b in native['blocks'] if b['kind'] in ('text','equation') and len(b.get('tex',''))>=60
                and b['page']['original_physical_page'] not in excluded_pages]
    return sorted(candidates,key=lambda b:hashlib.sha256(('review-sample-v1|'+native['source']+'|'+b['id']).encode()).hexdigest())[:count]


def export(ctrl,run,state,out):
    """Add review/ to the existing inspection snapshot. All claims remain attributed."""
    dest=out/'review';dest.mkdir(parents=True,exist_ok=True)
    manifest=read_json(run/'collection.json');sources={d['source_id']:d for d in manifest['documents']}
    changes=[];documents=[];samples=[];crop_candidates=[];native_cache={}
    for source,rec in state['documents'].items():
        tasks=recovery.effective_tasks(state,source)
        phases={}
        for phase in ('convert','critic'):
            ts=[t for t in tasks if t['phase']==phase]
            good={'conversion_completed'} if phase=='convert' else {'critic_revised','critic_unchanged'}
            phases[phase]='completed' if ts and all(t['status'] in good for t in ts) else sorted({t['status'] for t in ts}) or rec['status']
        documents.append({'source_id':source,'filename':sources[source]['originals'][0]['name'],
            'sha256':sources[source]['sha256'],'selection':selection.document_status(state,source),
            'phases':phases,'compilation':rec.get('compilation'),'publication':rec.get('publication'),
            'deferred':selection.deferred(state,source),'source_verification':'not independently established'})
        if selection.deferred(state,source) or not rec.get('plan'):continue
        native=read_json(run/'inputs'/source/'native.json');native_cache[source]=native
        mapping=[{'id':b['id'],'kind':b['kind'],'page':b['page']['original_physical_page'],'bbox':b.get('bbox'),'assets':b.get('assets',[])} for b in native['blocks']]
        atomic_json(dest/'source-maps'/(source+'.json'),{'source_sha256':sources[source]['sha256'],'blocks':mapping})
        flagged_pages=set()
        for key in rec['units']:
            for p in sorted((run/'accuracy'/key).glob('*')):
                if p.is_file():source_library.copy_verified(p,dest/'accuracy'/key/p.name)
                if p.suffix!='.json':continue
                data=read_json(p)
                for item in data.get('items',[]):
                    pages=sorted({int(n) for n in re.findall(r'(?i)(?:PDF\s*)?p(?:age)?\.?\s*(\d+)',item['text']) if 1<=int(n)<=rec['pages']})
                    flagged_pages.update(pages)
                    row={'source_id':source,'unit':key,'phase':data.get('phase'),'record':str(p.relative_to(run)),
                         'bucket':bucket(item),'priority':'mathematical' if PRIORITY.search(item['text']) else 'other',
                         'source_page_candidates':pages,'locator_status':'candidate textual locators; not independently verified',
                         **item,'review_status':'model claim; independent review pending'}
                    changes.append(row)
                    if row['priority']=='mathematical' and pages:
                        crop_candidates.append((source,pages[0],None,'material note '+str(item.get('id'))))
            for label,v in state.get('versions',{}).get(key,{}).items():
                source_library.copy_verified(run/v['path'],dest/'versions'/key/(label+'.tex'),v['sha256'])
            for name in ('provenance','syntax-repairs'):
                for p in sorted((run/name/key).rglob('*')):
                    if p.is_file() and p.suffix in ('.json','.diff','.md'):source_library.copy_verified(p,dest/name/key/p.relative_to(run/name/key))
            for p in (run/'deliveries'/source).glob('coverage.json'):source_library.copy_verified(p,dest/'historical-coverage'/source/p.name)
            selected=state['current_versions'].get(key)
            if selected:
                v=state['versions'][key][selected]
                atomic_json(dest/'selected'/ (key+'.json'),{'label':selected,**v,
                    'coverage':next((r for r in state['selection_ledger'] if r['unit']==key),None)})
        flags=[r for r in state['selection_ledger'] if r['source_key']==source]
        if flags and not any(r.get('possible_content_gaps') for r in flags):
            for b in sampled_blocks(native,flagged_pages):
                samples.append({'source_id':source,'source_sha256':sources[source]['sha256'],'block':b['id'],
                    'page':b['page']['original_physical_page'],'bbox':b.get('bbox'),'source_tex':b['tex'],
                    'selected_units':[r['unit'] for r in flags if b['id'] in r['blocks']],
                    'selection_rule':'SHA256(review-sample-v1|source-id|block-id), one candidate per unflagged selected source; global hash order, first 8',
                    'status':'unflagged by saved indicators only; not source-verified'})
    samples=sorted(samples,key=lambda r:hashlib.sha256(('review-sample-v1|'+r['source_id']+'|'+r['block']).encode()).hexdigest())[:8]
    special={'id':'operator-anfuso-equation-13','source_id':ANFUSO,'pages':[8,9],
        'bucket':'uncertain_claims','priority':'highest','attribution':'operator-supplied diagnostic target',
        'text':r'Both model phases changed alpha+rho*X to rho*alpha+X in equation (13), retaining the appendix independence assumption. The conditional representation Z=-rho*X+sqrt(1-rho^2)*eta with eta independent of X supports the original numerator; distinguish eta from the earlier noise variable. Requires mathematical review. Syntax repair must not change this equation or treat the model correction as verified.',
        'review_status':'unresolved; independent mathematical review required','historical_calls':['call-031','call-032']}
    changes.insert(0,special)
    crop_candidates=[(ANFUSO,8,None,'equation 13 assumptions'),(ANFUSO,9,None,'equation 13 review')]+crop_candidates
    selected_crops=[];seen=set()
    for item in crop_candidates:
        if (item[0],item[1]) in seen:continue
        seen.add((item[0],item[1]));selected_crops.append(item)
        if len(selected_crops)>=12:break
    selected_crops += [(x['source_id'],x['page'],x['bbox'],'unflagged sample '+x['block']) for x in samples]
    crop_records=[]
    from .saved_pages import render_region
    for i,(source,page,bbox,reason) in enumerate(selected_crops):
        if source not in state['documents']:continue
        pdf=run/state['documents'][source]['original'];path=dest/'source-crops'/f'{i:02d}-{source}-p{page}.png'
        try:
            record=render_region(pdf,page-1,path,bbox=bbox,max_edge=1200)
            crop_records.append({'source_id':source,'source_sha256':sources[source]['sha256'],'physical_page':page,'reason':reason,**record})
        except (ValueError,OSError) as exc:crop_records.append({'source_id':source,'physical_page':page,'reason':reason,'unavailable':str(exc)})
        if source in native_cache:
            blocks=[b for b in native_cache[source]['blocks'] if b['page']['original_physical_page']==page]
            atomic_json(dest/'source-context'/f'{source}-p{page}.json',{'source_id':source,'physical_page':page,'blocks':blocks})
    metrics=[]
    for c in state['calls']:
        usage=c.get('metadata',{}).get('usage',{}) or {};details=usage.get('completion_tokens_details',{}) or {}
        total=usage.get('completion_tokens');reason=details.get('reasoning_tokens')
        settings=read_json(run/'calls'/c['id']/'settings.json') if (run/'calls'/c['id']/'settings.json').exists() else {}
        task=next((t for t in state['tasks'] if t['id']==c['parent']),{})
        final=run/'calls'/c['id']/'answer.txt'
        metrics.append({'call':c['id'],'task':c['parent'],'status':c['status'],'elapsed_seconds':c.get('elapsed_seconds'),
            'task_status':task.get('status'),'requested_effort':settings.get('requested_reasoning_effort'),
            'completion_allowance':settings.get('max_tokens'),'final_output_bytes':final.stat().st_size if final.exists() else None,
            'finish_reason':c.get('metadata',{}).get('finish_reason'),'prompt_tokens':usage.get('prompt_tokens'),
            'completion_tokens':total,'reasoning_tokens':reason,'final_output_tokens':total-reason if isinstance(total,int) and isinstance(reason,int) else None,
            'note':'Token categories are server-reported; faster completion is not fidelity evidence.'})
    for p in (run/'low-recovery').glob('*.json'):source_library.copy_verified(p,dest/'low-recovery'/p.name)
    atomic_json(dest/'documents.json',documents);atomic_json(dest/'changes.json',changes)
    atomic_json(dest/'samples.json',samples);atomic_json(dest/'source-crops.json',crop_records);atomic_json(dest/'request-metrics.json',metrics)
    lines=['# Focused subsequent review','', 'Packaging is not independent review. Start with the operator Anfuso equation (13) flag. Applied/resolved labels below are attributed model claims, not acceptance. All converter and critic accuracy records are retained, including later superseded material.','']
    for name in ('uncertain_claims','applied_changes_claimed','unapplied_suggestions','informational'):
        rows=[r for r in changes if r['bucket']==name];lines.extend(['## '+name,''])
        lines.extend('- '+str(r.get('id'))+' — '+r['source_id']+' — '+str(r.get('phase','operator'))+'; '+r.get('priority','other') for r in rows)
        lines.append('')
    lines+=['See changes.json for full text/attribution, source-maps and source-context for locators, source-crops for selected original-page evidence, selected/ for build/coverage records, and versions/ for converter/critic/syntax derivatives.',
            'samples.json is a reproducible small selection of otherwise unflagged source passages; compare them with the linked selected units. Raw reasoning/wire logs, original PDFs and bulk assets are omitted and remain at recorded project paths.']
    (dest/'INDEX.md').write_text('\n'.join(lines)+'\n')
