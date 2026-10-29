"""Offline evidence helpers for the linked editorial repair; no dispatch/client."""
import copy
import re
from pathlib import Path
from .common import read_json, sha
from . import chapter_editorial as edit, chapter_inputs


def section_coverage(task, native):
    blocks={b['id']:b for b in native['blocks']}
    target=task['section']['blocks'] if task and task.get('section') else [b['id'] for b in native['blocks'] if b['kind'] not in chapter_inputs.AUX]
    if len(target)!=len(set(target)) or any(x not in blocks for x in target):raise ValueError('Unknown/duplicate section target')
    pages=sorted({blocks[x]['page']['original_physical_page'] for x in target})
    context=[p['page']['original_physical_page'] for p in native['pages']]
    return {'target_block_ids':target,'target_span':{'first':target[0] if target else None,'last':target[-1] if target else None},
            'target_physical_pages':pages,'parent_chapter_pages':context,
            'context_only_pages':[p for p in context if p not in pages],
            'context_scope':task.get('context_scope',{'mode':'full_chapter'}) if task else {'mode':'full_chapter'},
            'output_fidelity':'not established by source accounting or compilation'}


def latest_dispositions(before, raw, key, aliases=None):
    """Explicit source-reviewed aliases only. Unmatched material findings stay open."""
    prior=copy.deepcopy(before);aliases=aliases or {}
    for item in prior.get('items',[]):
        if item['id'] in aliases:item['references']=list(set(item.get('references',[])+aliases[item['id']]))
    latest=edit.notes_record(key,raw,phase='recovered-current-critic')
    merged=edit.reconcile_notes(prior,latest)
    merged['recovery']='Codex reconciliation of saved GLM notes; claims are not independent verification'
    return merged


def preflight_inputs(folder, tasks):
    """Every owned page, complete block, literal formula, asset and secondary page."""
    native=folder/'native';meta=read_json(native/'inputs.json');pages=[];ids=[];rows=[]
    for part in meta['parts']:
        key=part['key'];data=read_json(folder/'inputs'/key/'native.json')
        physical=[p['page']['original_physical_page'] for p in data['pages']]
        if physical!=sorted(set(physical)) or any(p['page']['owner'] is not True for p in data['pages']):raise ValueError('Owned page duplication: '+key)
        secondary=read_json(folder/'inputs'/key/'secondary.json')
        if [p['physical_pdf_page'] for p in secondary['pages']]!=physical:raise ValueError('Secondary page mismatch: '+key)
        for asset in read_json(folder/'inputs'/key/'assets.json'):
            if not (folder/'inputs'/asset).is_file():raise ValueError('Missing asset: '+asset)
        if not part['all_native_math_present']:raise ValueError('Native formulas lost: '+key)
        targets=[x for t in tasks if t['source_key']==key and t['phase']=='convert' for x in (t['section']['blocks'] if t.get('section') else part['target_ids'])]
        if key not in ('bergomi-front','bergomi-back') and targets!=part['target_ids']:raise ValueError('Section coverage/order loss: '+key)
        ids.extend(b['id'] for b in data['blocks']);pages+=physical
        rows.append({'key':key,'physical_pages':physical,'blocks':len(data['blocks']),'native_math_strings':part['native_math_strings'],
                     'assets':len(read_json(folder/'inputs'/key/'assets.json')),'secondary_pages':len(secondary['pages']),
                     'boundaries':'established source intake; whole blocks at native headings; semantic boundary fidelity not certified',
                     'fallbacks':part['fallbacks'],'targets_accounted':True})
    if pages!=list(range(1,521)) or len(ids)!=len(set(ids)):raise ValueError('Bergomi must own exactly 520 pages, without duplicate blocks')
    return {'status':'passed_offline','owned_pages':520,'unique_blocks':len(ids),'parts':rows,
            'omission_limit':'recognized content accounted, not a new visual audit of every source page',
            'native_renderer':'existing installed renderer only; no OCR or model calls'}


def call_metrics(root, call):
    folder=Path(call.get('inherited_from',root))/'calls'/call['id']
    p=folder/'response-metadata.json';record=read_json(p) if p.exists() else {}
    usage=record.get('usage') or call.get('metadata',{}).get('usage') or {}
    reasoning=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens')
    completion=usage.get('completion_tokens')
    return {'call':call['id'],'folder':str(folder),'status':call['status'],'finish_reason':record.get('finish_reason'),
            'elapsed_seconds':call.get('elapsed_seconds'),'usage':usage,'reasoning_tokens':reasoning,
            'other_completion_tokens':completion-reasoning if isinstance(completion,int) and isinstance(reasoning,int) else None,
            'answer_characters':len((folder/'answer.txt').read_text(encoding='utf-8')) if (folder/'answer.txt').exists() else None,
            'counter_limit':'other completion tokens are subtraction, not an independently reported final-answer counter'}
