"""Bounded exact local statements, with explicit boundary and OCR provenance."""
import re
from .sciwrite_subset import command_spans
from . import bibliography

POLICY={'max_blocks':8,'max_characters':18000,'neighbours':1,'reassessments':1}
STATEMENT=r'(Theorem|Definition|Lemma|Proposition|Corollary|Example|Assumption)\s+(\d+(?:\.\d+)+)'


def plain_start(text):
    return re.sub(r'\\(?:textbf|textit|emph)\{([^{}]*)\}',r'\1',text).lstrip()


def labels(text):
    result=[]
    m=re.match(STATEMENT,plain_start(text),re.I)
    if m:result.append(m[1].lower()+' '+m[2])
    result += ['equation '+m['argument'].strip() for m in command_spans(text,'tag')]
    result += ['label '+m['argument'].strip() for m in command_spans(text,'label')]
    for cmd in ('section','subsection'):
        result+=['section '+m['argument'].strip().lower() for m in command_spans(text.replace('\\'+cmd+'*{','\\'+cmd+'{'),cmd)]
    result+=['bibliography '+m['argument'].strip() for m in command_spans(text,'bibitem')]
    return list(dict.fromkeys(result))


def reference_keys(value):
    """Keep verbose wording in records; resolve explicit identifiers, not topics."""
    value=' '.join(value.strip().split())
    refs=[]
    for m in re.finditer(r'\b(theorem|definition|lemma|proposition|corollary|example|assumption|equation|eq\.?)\s*\(?\s*(\d+(?:\.\d+)+)\b',value,re.I):
        key=('equation' if m[1].lower().startswith('eq') else m[1].lower())+' '+m[2]
        if key not in refs:refs.append(key)
    if refs:return refs
    m=re.fullmatch(r'\(?\s*(\d+(?:\.\d+)+)\s*\)?',value)
    return ['equation '+m[1]] if m else [value.lower()]


def reference_key(value):
    keys=reference_keys(value)
    return keys[0] if len(keys)==1 else ' | '.join(keys)


def deduplicate_requests(requests):
    records={}
    for item in requests:
        item={'reference':item,'reason':'Explicit local reference'} if isinstance(item,str) else item
        for key in reference_keys(item['reference']):
            r=records.setdefault(key,{'key':key,'reference':item['reference'],'original_requests':[], 'reasons':[], 'anchor_ids':[]})
            if item['reference'] not in r['original_requests']:r['original_requests'].append(item['reference'])
            reason=item.get('reason','Explicit local reference')
            if reason not in r['reasons']:r['reasons'].append(reason)
            r['anchor_ids']=list(dict.fromkeys(r['anchor_ids']+item.get('anchor_ids',[])))
    return list(records.values())


def folio(row):
    return row.get('kind') in ('page_number','header','footer') or (row.get('kind')!='equation' and re.fullmatch(r'\d{1,5}',row['text'].strip()) is not None)


def statement_span(rows,i):
    """Whole blocks through an observed structural boundary, never punctuation."""
    chosen=[];last=rows[i]['source_location'];boundary='partial_end_of_available_text'
    for j in range(i,len(rows)):
        r=rows[j];loc=r['source_location'];text=plain_start(r['text'])
        if loc['source_id']!=last['source_id'] or not 0<=loc['page']['selected_page']-last['page']['selected_page']<=1:
            boundary='partial_source_or_page_gap';break
        if j>i and (re.match(r'Proof\b',text,re.I) or re.match(STATEMENT,text,re.I) or any(l.startswith('section ') for l in labels(r['text']))):
            boundary='observed_statement_boundary';break
        last=loc
        if not folio(r):chosen.append(r['block_id'])
    return {'blocks':chosen,'boundary_status':boundary,'complete_statement':boundary=='observed_statement_boundary'}


def build_index(rows,source_identity):
    if len({r['block_id'] for r in rows})!=len(rows):raise ValueError('Duplicate block in local context index')
    entries={};byid={r['block_id']:r for r in rows};order=list(byid);spans={}
    for i,r in enumerate(rows):
        if re.match(STATEMENT,plain_start(r['text']),re.I):spans[r['block_id']]=statement_span(rows,i)
    for row in rows:
        for label in labels(row['text']):
            span=spans.get(row['block_id'])
            if span is None:
                enclosing=[s for s in spans.values() if row['block_id'] in s['blocks']]
                span=enclosing[0] if len(enclosing)==1 else {'blocks':[row['block_id']],'boundary_status':'labelled_block_only; surrounding_statement_unknown','complete_statement':False}
            entries.setdefault(label,[]).append({'block_id':row['block_id'],**span,'location_basis':'explicit_statement_or_display_label'})
    return {'schema':'local-critic-context-v2','source_identity':source_identity,'rows':byid,'order':order,'entries':entries,
        'bibliography':bibliography.inventory(rows,source_identity,'unknown'),
        'limitations':'Structural boundaries are not source verification. Partial/unavailable/ambiguous context remains explicit. Exact candidate and unreviewed OCR retain distinct provenance.'}


def resolve(index,requests,exclude=(),policy=POLICY):
    selected=[];records=[];used=set(exclude);characters=0
    for query in deduplicate_requests(requests):
        matches=index['entries'].get(query['key'],[])
        record={**query,'reason':'; '.join(query['reasons']),'status':'unavailable','candidates':[m['block_id'] for m in matches],'added_blocks':[]}
        records.append(record)
        if len(matches)!=1:
            record['status']='ambiguous' if matches else 'unavailable_not_in_converted_or_recognized_index';continue
        match=matches[0];record.update(boundary_status=match['boundary_status'],statement_blocks=match['blocks'],complete_statement=match.get('complete_statement',False))
        rows=[index['rows'][b] for b in match['blocks'] if b not in used]
        # A supplied heading is not a supplied theorem: add its missing continuation.
        if not rows:record['status']='already_supplied' if match.get('complete_statement') else 'already_supplied_partial';continue
        if any(r.get('unresolved') for r in rows):record['status']='unavailable_unresolved_transcription';continue
        if len(selected)+len(rows)>policy['max_blocks'] or characters+sum(len(r['text']) for r in rows)>policy['max_characters']:
            record['status']='unavailable_context_bound; no clipping';continue
        # A newly indexed unfinished statement cannot justify spending a reassessment
        # on a heading/display alone. Keep the complete raw span in the local index.
        if index['schema']=='local-critic-context-v2' and not match.get('complete_statement') and query['key'].split()[0] in ('theorem','definition','lemma','proposition','corollary','assumption','example'):
            record['status']='partial_statement_unavailable_for_reassessment';continue
        selected.extend(rows);used.update(r['block_id'] for r in rows);characters+=sum(len(r['text']) for r in rows)
        record.update(status='added' if match.get('complete_statement') else 'added_partial_context',added_blocks=[r['block_id'] for r in rows],
            provenance=[{'block_id':r['block_id'],'basis':r.get('basis','unknown'),'source_block_sha256':r.get('source_block_sha256'),'source_location':r['source_location']} for r in rows])
    position={b:i for i,b in enumerate(index['order'])};selected.sort(key=lambda r:position[r['block_id']])
    return selected,records


def explicit_references(text):
    found=[]
    for m in re.finditer(r'\b(Theorem|Definition|Lemma|Proposition|Corollary|Equation|Example|Assumption)\s*\(?\s*(\d+(?:\.\d+)+)',text,re.I):
        key=reference_key(m[1]+' '+m[2])
        if key not in found:found.append(key)
    for cmd in ('ref','eqref'):
        for m in command_spans(text,cmd):
            key='label '+m['argument']
            if key not in found:found.append(key)
    return found
