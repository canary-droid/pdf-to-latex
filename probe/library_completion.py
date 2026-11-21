"""Source-bound saved-work completion helpers. No transport or publication."""
import hashlib,json,re,copy
from pathlib import Path
from .common import fingerprint,sha

PREAMBLE=(b'\\documentclass[11pt]{article}\n'
          b'\\usepackage{amsmath,amssymb,amsthm,graphicx,longtable,booktabs,array}\n'
          b'\\begin{document}\n')
POSTAMBLE=b'\n\\end{document}\n'

def digest(data):return hashlib.sha256(data if isinstance(data,bytes) else data.encode()).hexdigest()

def wrap_fragment(raw):
    """One closed TeX fence, exact bytes and all outside notes retained."""
    if isinstance(raw,str):raw=raw.encode()
    markers=list(re.finditer(rb'(?m)^ {0,3}(`{3,}|~{3,})([^\r\n]*)(?:\r?\n|$)',raw))
    if len(markers)!=2:raise ValueError('Fragment needs exactly one complete unambiguous fence')
    a,b=markers
    if a[1]!=b[1] or a[2].strip().lower() not in (b'tex',b'latex') or b[2].strip():raise ValueError('Ambiguous fragment fence')
    body=raw[a.end():b.start()]
    if not body.strip():raise ValueError('Empty fragment')
    if re.search(rb'\\(?:documentclass|documentstyle|begin\s*\{document\}|end\s*\{document\})',raw):raise ValueError('Full/partial envelope must use original parser')
    if re.search(rb'\\(?:usepackage|RequirePackage|input|include|bibliography|addbibresource|write|openout|read|catcode|csname)\b',body):raise ValueError('Unsupported preamble/external command in fragment')
    slices=[raw[:a.start()],a[0],body,b[0],raw[b.end():]]
    assert b''.join(slices)==raw
    return PREAMBLE+body+POSTAMBLE,{'raw_sha256':digest(raw),'body_sha256':digest(body),'body_byte_preserved':True,'prefix':slices[0].decode(),'opening_fence':slices[1].decode(),'body':body.decode(),'closing_fence':slices[3].decode(),'suffix':slices[4].decode(),'status':'wrapped_unreviewed','compilation':'not_requested'}

def saved_review(raw,expected_hash):
    """An exact final object delimiter is the only extra syntax repair allowed."""
    from .library_repair import salvage_json
    try:return salvage_json(raw,expected_hash),{'normalization':'none or unique complete JSON fence/object'}
    except ValueError:pass
    # Parseable after one terminal brace; never repair a string, field, list,
    # unfinished finding, truncated transport, or missing/stale base identity.
    text=raw.strip()
    if not text.startswith('{') or not text.endswith(']'):raise ValueError('Not a missing final object delimiter')
    data=json.loads(text+'}')
    if data.get('base_sha256')!=expected_hash or not isinstance(data.get('findings'),list):raise ValueError('Missing/stale exact draft identity')
    from .image_review import validate_review_shape
    validate_review_shape(data)
    return data,{'normalization':'Append exactly one terminal object brace; no fields/content/attestations invented','raw_sha256':digest(raw),'normalized_sha256':digest(text+'}')}

def source_binding(unit,block_ids):
    blocks={b['id']:b for b in unit['native_blocks']}
    return {key:fingerprint(blocks[key]) for key in block_ids}

def adjudication(document,unit,*,kind,targets,source_blocks,output_spans,images,reason,details=None):
    if kind not in ('heading','table','figure'):raise ValueError('Unsupported adjudication')
    if not output_spans or any(not x or document.count(x)!=1 for x in output_spans):raise ValueError('Need unique complete output spans')
    if not images or any(sha(p)!=h for p,h in images.items()):raise ValueError('Missing/changed original source evidence')
    return {'kind':kind,'targets':targets,'draft_sha256':digest(document),'source_text_sha256':unit['text_sha256'],'source_blocks':source_binding(unit,source_blocks),'output_spans':output_spans,'images':images,'reason':reason,'details':details or {},'limits':'Only the named structural coverage claims; no whole-paper mathematical endorsement'}

def apply_adjudications(document,unit,result):
    """Never waive unrelated flags; stale source/output evidence is itself a blocker."""
    result=copy.deepcopy(result);accepted=[];invalid=[]
    for record in unit.get('content_adjudications',[]):
        valid=(digest(document)==record['draft_sha256'] and unit['text_sha256']==record['source_text_sha256'] and source_binding(unit,list(record['source_blocks']))==record['source_blocks'] and all(document.count(x)==1 for x in record['output_spans']) and all(Path(p).is_file() and sha(p)==h for p,h in record['images'].items()))
        if not valid:invalid.append({'kind':record['kind'],'targets':record['targets'],'reason':'Source/draft/span/image changed; adjudication withheld'});continue
        if record['kind']=='heading':
            result['missing_heading_candidates']=[h for h in result['missing_heading_candidates'] if h not in record['targets']]
        elif record['kind']=='table':result['table_count_warning']=False
        accepted.append(record)
    # All other independent coverage signals retain their original meanings.
    risk=invalid or any(result.get(k) for k in ('empty_or_insubstantial_output','missing_expected_assets','duplicated_verified_figures','table_count_warning','missing_heading_candidates','missing_substantive_span_candidates','missing_explicit_equation_numbers'))
    result.update(source_bound_adjudications=accepted,invalid_adjudications=invalid,coverage_status='omission_risk' if risk else 'requires_source_review')
    return result

def validate_figure_groups(unit):
    for group in unit.get('coverage_metadata',{}).get('verified_figure_groups',[]):
        evidence=group.get('source_check')
        if evidence is None:continue  # Legacy verified groups keep their frozen historical contract.
        if not evidence.get('visual_check') or not evidence.get('caption_block'):raise ValueError('Incomplete figure qualification')
        for path,h in evidence['files'].items():
            if sha(path)!=h:raise ValueError('Figure/source crop identity changed')
        if not set([group['canonical'],*group['members']])<=set(unit['assets']):raise ValueError('Figure asset mapping absent')
        for ref,h in evidence['asset_sha256'].items():
            if sha(unit['assets'][ref])!=h:raise ValueError('Figure content changed')

def verify_ownership(units,original_ids,transfer_records=()):
    owned=[b for u in units.values() for b in u['blocks']]
    if len(owned)!=len(set(owned)) or set(owned)!=set(original_ids):raise ValueError('Gap/duplicate source ownership after completion')
    return {'blocks':len(owned),'unique':True,'complete_assigned_source_mapping':True,'transfers':list(transfer_records),'context_is_not_output':True}

def reference_check(documents,required_labels=()):
    text='\n'.join(documents)
    labels=re.findall(r'\\label\s*\{([^{}]+)\}',text)
    refs=re.findall(r'\\(?:ref|eqref|pageref)\s*\{([^{}]+)\}',text)
    return {'missing_required_labels':sorted(set(required_labels)-set(labels)),
            'undefined_references':sorted(set(refs)-set(labels)),
            'duplicate_labels':sorted({x for x in labels if labels.count(x)>1}),
            'scope':'Whole selected paper, including labels transferred with complete figures'}
