"""Library-first policy and evidence contracts; no implicit inference or paid calls."""
import copy,re
from pathlib import Path
from .common import read_json,sha,fingerprint
from . import image_review,focused_recovery

VERSION='library-first-v1'
DEFAULTS={'converter_effort':'high','review_effort':'high','max_tokens':131072,'maximum_in_flight':2,
          'image_limits':{'image_tokens':2048,'request_image_tokens':16384,'max_images':50},
          'paid_enabled':False,'new_spend_budget_usd':'0','conversion_attempts':1,'review_attempts':1,
          'mathpix_attempts_per_subset':1,'kimi_attempts_per_task':1,'overall_deadline':None,'compile_pdf':False}
COOKING='original-e7ae674847b03f05'

def admit_missing_conversion(live_row,pointer):
    if live_row.get('status') in ('ready','deferred') or (pointer or {}).get('status') in ('ready_working_source','delivered_working_edition'):
        raise ValueError('Current library source is ready or deferred; no blanket conversion')
    if live_row.get('latest_attempt'):
        raise ValueError('A library-first attempt already exists; resume/reconcile it, never reset consumed attempts with a fresh run')

def validate_extraction_plan(plan,root):
    import struct
    expected=[]
    for d in plan['documents']:
        if [p['physical_pdf_page'] for p in d['pages']]!=d['physical_pages']:raise ValueError('Page plan has gaps/duplicates')
        for p in d['pages']:
            if p.get('image')!=p.get('path'):raise ValueError('Installed Pro worker requires the exact image field/path contract')
            image=Path(root)/p['image']
            if sha(image)!=p['sha256'] or list(struct.unpack('>II',image.read_bytes()[16:24]))!=p['dimensions']:raise ValueError('Prepared original-page image changed')
            if not d.get('fixed_native') and p['physical_pdf_page'] not in d.get('reused_extraction_pages',[]) and str(p['physical_pdf_page']) not in d.get('blank_pages',{}):expected.append([d['source_id'],p['physical_pdf_page']])
        if d.get('fixed_native') and sha(Path(root)/d['fixed_native'])!=d['fixed_native_sha256']:raise ValueError('Reusable extraction scope changed')
    if expected!=plan['workloads']['mineru_pro']:raise ValueError('Extraction workload differs from frozen page plan')

def review_summary(tasks,findings=()):
    relevant=[t for t in tasks if t.get('phase') in ('critic','review') or 'review_response' in t]
    failed=[t['id'] for t in relevant if t.get('review_response') in ('no_usable_answer','invalid_findings') or t.get('status') in ('truncation','failed','invalid_review','unavailable')]
    pending=[t['id'] for t in relevant if t.get('status') in ('pending','running','dormant')]
    unattested=[t['id'] for t in relevant if not t.get('review_complete_attested')]
    suggestions=[f for f in findings if f.get('disposition') in ('rejected','unapplied_suggestion','unresolved')]
    return {'reviewed_full_scope_attested':bool(relevant) and not (failed or pending or unattested),
            'failed_or_incomplete_reviews':failed,'pending_reviews':pending,'scope_not_attested':unattested,
            'pending_suggestions':suggestions,'pending_suggestion_count':len(suggestions),
            'independent_mathematical_verification':'not established by model response or compilation'}

def fallback_kind(phase,failure):
    if failure in ('identity','integrity','uncertain_dispatch','resource','ownership','transport_unknown'):return 'stop_and_reconcile'
    if phase=='extraction' and failure in ('failed','incomplete','garbled'):return 'mathpix'
    if phase in ('convert','critic','review') and failure in ('reasoning_exhaustion','truncation','failed','invalid_review','unresolved_passage'):return 'kimi'
    if phase=='compile':return 'deterministic_syntax_or_environment_diagnosis'
    return 'record_and_continue'

def structural_role(block):
    text=block['tex'].strip()
    text=re.sub(r'\\(?:sub)*section\*?\{(.*)\}',r'\1',text,flags=re.S)
    text=re.sub(r'\\(?:textbf|textit|emph)\{([^{}]*)\}',r'\1',text).strip()
    text=re.sub(r'</?(?:b|strong|i|em|span|p)(?:\s[^>]*)?>','',text).lstrip('#* _')
    if re.match(r'(?i)^proof\b|^\\begin\{proof\}',text):role='proof'
    elif re.match(r'(?i)^(theorem|lemma|proposition|corollary|claim)\b|^\\begin\{(?:theorem|lemma|proposition|corollary)\}',text):role='statement'
    elif re.match(r'(?i)^(definition|assumption|notation)\b',text):role='definition'
    elif block['kind'] in ('image','chart','figure','table'):role='figure'
    elif block['kind'] in ('caption','figure_title','figure_caption','table_caption') or re.match(r'(?i)^(fig(?:ure)?\.?|table)\s+\d+[.:]',text):role='caption'
    elif block['kind'] in ('equation','formula'):role='equation'
    elif block['kind'] in ('footnote','vision_footnote'):role='footnote'
    elif block['kind']=='paragraph_title':role='heading'
    else:role='paragraph'
    return role,text

def structural_units(blocks, *, maximum_pages=4, maximum_chars=24000):
    """Pack complete source atoms, returning included AND outstanding spans.

    A heading is preferred, but not required for a safe paragraph boundary. Never
    cut a native region. Keep display/condition chains, captions, definitions with
    immediate use, and theorem/proof chains together. An ambiguous unclosed proof
    stays together until an explicit end or a numbered source section boundary.
    No resizing, content truncation, retry or model-generated bookkeeping.
    """
    if not blocks:raise ValueError('No source regions to assign')
    if maximum_pages<1 or maximum_chars<1:raise ValueError('Invalid structural limits')
    ids=[b['id'] for b in blocks]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate source region identity')
    atoms=[];atom=[];proof=False;proof_seen=False;environments=[];display=False
    previous_role=None;previous_text='';previous=None;previous_proof_end=False
    for index,b in enumerate(blocks):
        role,text=structural_role(b)
        numbered_section=role=='heading' and bool(re.match(r'(?i)^(?:\d+(?:\.\d+)*[.)]?\s+\S|[A-Z]\.\d+(?:\.\d+)*\.?\s+\S|APPENDIX\s+[A-Z]\b|REFERENCES\s*$|BIBLIOGRAPHY\s*$)',text))
        # A new labelled result without an attached proof may follow another
        # stated result. Inside a proof, internal cases/lemmas are NOT cut apart.
        proof_boundary=numbered_section or (role=='statement' and not proof_seen)
        joined=bool(previous and (previous.get('continues_next') or b.get('continues_prev') or
            previous.get('native',{}).get('continues_next') or b.get('native',{}).get('continues_prev')))
        for key in ('equation_id','figure_id','table_id','structural_group_id'):
            if previous and b.get(key) is not None and b.get(key)==previous.get(key):joined=True
        terminal=previous_proof_end or bool(re.search(r'[.!?](?:[}\]"\')]|\\[)\]])*\s*$',previous_text))
        continuation=bool(re.match(r'(?i)^(where|with|and|or|provided|subject to|such that|which|so that|hence|thus|therefore)\b',text))
        boundary=bool(atom) and not (joined or environments or display) and (not proof or proof_boundary)
        if boundary:
            if role in ('proof','equation','caption','footnote') or previous_role in ('heading','definition','caption'):
                boundary=False
            elif role=='heading' or role in ('statement','definition'):
                boundary=True
            else:
                boundary=not continuation and (terminal or previous_role=='figure')
        if boundary:
            atoms.append(atom);atom=[];proof=False;proof_seen=False
        atom.append(b)
        if role=='statement':proof=True
        if role=='proof':proof=True;proof_seen=True
        # Track unclosed TeX structures across regions, including arrays/lists.
        for m in re.finditer(r'\\(begin|end)\{([^{}]+)\}|\\\[|\\\]|\$\$',b['tex']):
            if m[1]=='begin':environments.append(m[2])
            elif m[1]=='end':
                if environments and environments[-1]==m[2]:environments.pop()
            elif m[0]==r'\[':display=True
            elif m[0]==r'\]':display=False
            else:display=not display
        previous_proof_end=bool(proof and (re.search(r'\\end\{proof\}',b['tex']) or
            re.search(r'(?:\\(?:qed\b|qedhere\b|square\b|Box\b)|[□∎]|\bQ\.?E\.?D\.?)(?:\s|\\[)\]]|[$}.])*$',b['tex'])))
        if previous_proof_end:proof=False;proof_seen=False
        previous_role,previous_text,previous=role,text,b
    if atom:atoms.append(atom)
    pages=lambda xs:sorted({b['page']['original_physical_page'] for b in xs})
    size=lambda xs:len('\n\n'.join(b['tex'] for b in xs))
    result=[];current=[];offset=0
    def emit(xs,disposition,reason):
        nonlocal offset
        text='\n\n'.join(b['tex'] for b in xs)
        result.append({'blocks':[b['id'] for b in xs],'first':xs[0]['id'],'last':xs[-1]['id'],
            'physical_pages':pages(xs),'text':text,'text_sha256':focused_recovery.digest(text),
            'native_blocks':xs,'disposition':disposition,'reason':reason,
            'source_order_start':offset,'source_order_end':offset+len(xs),
            'limits':{'maximum_pages':maximum_pages,'maximum_chars':maximum_chars}})
        offset+=len(xs)
    for group in atoms:
        oversized=len(pages(group))>maximum_pages or size(group)>maximum_chars
        if current and (oversized or len(pages(current+group))>maximum_pages or size(current+group)>maximum_chars):
            emit(current,'included','Complete structural atoms packed without truncation');current=[]
        if oversized:
            emit(group,'outstanding','Indivisible source region/connected mathematical passage exceeds readable unit limits; explicit finer source qualification required')
        else:current+=group
    if current:emit(current,'included','Complete structural atoms packed without truncation')
    focused_recovery.validate_partition(result,ids)
    return result

def validate_publication(prepared,document):
    """Verify portable assets/selected TeX and explicit statuses before publication."""
    from .experiment import verify_seal
    from . import book_completion as scope
    prepared=Path(prepared);verify_seal(prepared);record=read_json(prepared/'library-status.json')
    if record['source_sha256']!=document['sha256']:raise ValueError('Publication source mismatch')
    from . import author_source
    ready=record['status']=='ready_working_source'
    for item in record['selected_tex']:
        p=prepared/item['path']
        if not p.resolve().is_relative_to(prepared.resolve()) or sha(p)!=item['sha256']:raise ValueError('Selected text changed/nonportable')
        if record.get('source_kind')=='author_tex':continue
        assets={str(x.relative_to(p.parent)):x for x in p.parent.rglob('*') if x.is_file()}
        if record.get('selected_master'):assets.update({str(x.relative_to(prepared)):x for x in prepared.rglob('*') if x.is_file()})
        check=author_source.generated_content(p.read_text(),assets,require_envelope=not bool(record.get('selected_master')))
        if ready and not check['usable']:raise ValueError('Incomplete substantive content: '+str(check['content_issues']))
    if record.get('selected_master'):
        master=prepared/record['selected_master']
        if not master.resolve().is_relative_to(prepared.resolve()) or not master.is_file():raise ValueError('Missing/nonportable selected master')
        check=author_source.generated_content(master.read_text(),{str(x.relative_to(prepared)):x for x in prepared.rglob('*') if x.is_file()})
        if ready and not check['usable']:raise ValueError('Incomplete master content: '+str(check['content_issues']))
    if record.get('source_kind')=='author_tex':
        version=record['source_version']
        if not version.get('identifier') or version.get('correspondence') not in ('same','alternative','unresolved'):raise ValueError('Missing declared source version')
        check,_=author_source.inspect_tree(prepared/'sources',record['entry_point'])
        if ready and not check['complete_content_dependencies']:raise ValueError('Missing author-source content dependencies')
    if ready and (not record['selected_tex'] or record['content_status'] not in ('complete_assigned_source','complete_declared_version') or record.get('outstanding_scopes')):
        raise ValueError('Incomplete source cannot masquerade as ready')
    return record
