"""Finite follow-up contracts; no transport or model side effects."""
import copy, hashlib, json, re
from .extraction_comparison import safe_glmocr_config

def glm_config(path):
    cfg=safe_glmocr_config(path)
    mapping=cfg['pipeline']['layout']['label_task_mapping']
    mapping['formula'].append('formula')
    mapping['text']+=['aside_text','reference']
    # Preserve vendor formatting for diagnostics; faithful export uses raw regions.
    return cfg

def validate_routes(labels,cfg):
    mapping=cfg['pipeline']['layout']['label_task_mapping'];records=[]
    if not labels:raise ValueError('Missing actual layout labels')
    for ident,label in labels.items():
        routes=[k for k,v in mapping.items() if label in v]
        if len(routes)!=1 or routes[0]=='abandon':raise ValueError('Unmapped/ambiguous/discarded label: '+label)
        if 'formula' in label and label!='formula_number' and routes!=['formula']:raise ValueError('Formula routing changed')
        records.append({'class':ident,'label':label,'route':routes[0]})
    return records

def account_regions(detected,recognized,asset_refs):
    """One ledger per routed region; raw export avoids formatter merge ambiguity."""
    byid={r['index']:r for r in recognized}
    if len(byid)!=len(recognized):raise ValueError('Duplicate recognition identity')
    ledger=[]
    for region in detected:
        ident=region['index'];r=byid.pop(ident,None)
        if r is None:raise ValueError('Detected region vanished before recognition: '+str(ident))
        if r.get('label')!=region['label'] or r.get('bbox_2d')!=region['bbox_2d']:raise ValueError('Recognition identity mismatch')
        task=region['task_type'];content=r.get('content','')
        if task=='skip':
            if ident not in asset_refs:raise ValueError('Image/chart region lost its original crop')
            status='retained_as_asset'
        elif not isinstance(content,str) or not content.strip():raise ValueError('Empty recognized region: '+str(ident))
        else:status='recognized'
        ledger.append({'detected_id':ident,'label':region['label'],'bbox':region['bbox_2d'],'task':task,
                       'status':status,'export_id':f'region-{ident}','sha256':hashlib.sha256(content.encode()).hexdigest(),
                       'asset':asset_refs.get(ident),'content':content})
    if byid:raise ValueError('Unattributed recognition result')
    return ledger

def faithful_export(ledger):
    parts=[]
    for row in ledger:
        content=row['content']
        if row['status']=='retained_as_asset':content='![Original source region]('+row['asset']+')'
        elif row['task']=='formula':content='\\[\n'+content+'\n\\]'
        parts.append(f'<!-- region {row["detected_id"]}; label={row["label"]}; bbox={row["bbox"]} -->\n'+content)
    return '\n\n'.join(parts)

def pro_export(blocks,assets):
    """Do not misrepresent image-analysis prose/tables as printed source content."""
    parts=[];inferred=[]
    for i,b in enumerate(blocks):
        kind=b.get('type');text=b.get('content') or ''
        if kind in ('image','chart','image_block'):
            if i not in assets:raise ValueError('Missing original figure crop')
            if text:inferred.append({'region':i,'content':text,'status':'engine_inferred_not_printed_source'})
            text='\\includegraphics{'+assets[i]+'}'
        parts.append({'index':i,'kind':kind,'text':text,'bbox':b.get('bbox')})
    return parts,inferred

def checked_partition(text,anchors):
    positions=[0]
    for pattern in anchors:
        hits=list(re.finditer(pattern,text,re.M|re.I))
        if len(hits)!=1:raise ValueError('Ambiguous/missing structural boundary '+pattern)
        # Keep any complete heading markup before the anchor.
        pos=text.rfind('\n',0,hits[0].start())+1
        # Region comment belongs with its heading.
        previous=text.rfind('\n\n',0,max(0,pos-1))
        if previous>=0 and text[previous+2:pos].lstrip().startswith('<!--'):pos=previous+2
        positions.append(pos)
    positions.append(len(text))
    if positions!=sorted(set(positions)):raise ValueError('Duplicate/reordered scope boundaries')
    return [{'start':a,'end':b,'text':text[a:b]} for a,b in zip(positions,positions[1:])]
