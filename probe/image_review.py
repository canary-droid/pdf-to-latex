"""Opt-in local source-image requests and image-aware capacity estimates."""
import base64,copy,hashlib,json,math,struct,re
from pathlib import Path

EVIDENCE_FIELDS=('printed_source','draft_reading','proposed_change','justification')
REPLACEMENT_FORMATS=('tex','plain_annotation')
EDIT_REQUIRED=EVIDENCE_FIELDS+('old','new','source','reason','replacement_format')
REVIEW_EXAMPLE={'base_sha256':'EXACT_FULL_DRAFT_SHA256',
    'scope_review':{'full_assigned_scope_reviewed':True,'additional_findings_remain':False,'unreviewed_scope':''},
    'findings':[{'status':'edit','old':'unique exact TeX substring','new':'minimal replacement',
      'source':'physical page and equation/section','reason':'concise reason',
      **{k:'explicit factual evidence for '+k for k in EVIDENCE_FIELDS},'replacement_format':'tex'}]}
LITERAL_PREFIX='EXACT DRAFT — literal TeX, not JSON-escaped text. Backslashes below are TeX commands; line breaks are line breaks.\n```latex\n'
LITERAL_SUFFIX='\n```\nEND EXACT DRAFT'

def validate_review_shape(data):
    if not isinstance(data,dict):raise ValueError('Review response must be a JSON object')
    if not isinstance(data.get('findings'),list):raise ValueError('Review findings must be a list')
    if any(not isinstance(f,dict) for f in data['findings']):raise ValueError('Each review finding must be an object')
    coverage=data.get('scope_review')
    if coverage is not None:
        if not isinstance(coverage,dict) or any(type(coverage.get(k)) is not bool for k in ('full_assigned_scope_reviewed','additional_findings_remain')) or not isinstance(coverage.get('unreviewed_scope'),str):
            raise ValueError('Invalid scope_review attestation')
        if not coverage['full_assigned_scope_reviewed'] and not coverage['unreviewed_scope'].strip():raise ValueError('Incomplete scope needs a locator/description')
    return data

def request_payload(body):
    content=body['messages'][0]['content'];first=content[0]['text'] if isinstance(content,list) else content
    payload=json.loads(first.split('\n',1)[1])
    if payload.get('draft_encoding')=='literal_tex_content_part':
        blocks=[p['text'] for p in content[1:] if p.get('type')=='text' and p.get('text','').startswith(LITERAL_PREFIX)]
        if len(blocks)!=1 or not blocks[0].endswith(LITERAL_SUFFIX):raise ValueError('Missing/ambiguous literal draft')
        payload['draft']=blocks[0][len(LITERAL_PREFIX):-len(LITERAL_SUFFIX)]
    return payload

def image_content(body):
    content=body['messages'][0]['content']
    return [p for p in content[1:] if not (p.get('type')=='text' and p.get('text','').startswith(LITERAL_PREFIX))]

def geometry(width,height,cap=2048):
    align=lambda v:math.ceil(v/28)*28
    h,w=align(height),align(width)
    if h*w>cap*784:
        lo,hi=1,height;h=w=28
        while lo<=hi:
            mid=(lo+hi)//2;ch,cw=align(mid),align(max(1,math.floor(width*mid/height)))
            if ch*cw<=cap*784:h,w,lo=ch,cw,mid+1
            else:hi=mid-1
    scale=min(1,h/height,w/width)
    return {'canvas':[w,h],'content':[max(1,math.floor(width*scale)),max(1,math.floor(height*scale))],'tokens':h*w//784}

def image_parts(records,root):
    parts=[]
    for r in records:
        data=(Path(root)/r['path']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=r['sha256']:raise ValueError('Missing/changed original image')
        if data[:8]!=b'\x89PNG\r\n\x1a\n' or list(struct.unpack('>II',data[16:24]))!=r['dimensions']:raise ValueError('Wrong image dimensions')
        parts += [{'type':'text','text':f"Original source physical page {r['physical_page']}; "+('full page' if r.get('crop') is None else 'detail crop, original pixel box '+str(r['crop']))}, {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(data).decode(),'detail':'high'}}]
    return parts

def with_images(body,parts):
    result=copy.deepcopy(body)
    text=result['messages'][0]['content']
    # Replace the inaccurate text-only statement, preserving exact input payload.
    text=text.replace('The source-image evidence is for operator checking; this text request contains no images.',
        'The attached original source images are evidence for what the paper prints. Read the full pages and any detail crops. Every edit REQUIRES nonempty printed_source, draft_reading, proposed_change and justification fields, in addition to old, new, source and reason. Distinguish a transcription mistake from a correction to printed mathematics. Do not rederive the whole paper. Preserve ambiguous readings and report uncertainty. Odd printed formulae are not automatically OCR errors. A mathematical edit requires supporting evidence. Set replacement_format="tex" for exact source/mathematical edits, preserving valid TeX. For prose within hash-labelled program-generated editorial notes only, set replacement_format="plain_annotation" and supply unescaped plain text in new (the program renders it safely); keep old as the exact existing TeX substring. Missing evidence or an ambiguous anchor means the proposal remains unapplied. Ignore style-only punctuation.')
    instruction,encoded=text.split('\n',1);payload=json.loads(encoded);draft=payload.pop('draft');payload['draft_encoding']='literal_tex_content_part'
    # Replace the obsolete short response example, rather than appending a second
    # contradictory schema. Missing factual evidence remains withheld, never invented.
    instruction=instruction.split('Return JSON only:',1)[0]
    instruction+='Review all assigned content. At most8 located findings; if unfinished or additional findings remain, record that honestly in scope_review. An empty list is not an attestation of full scope. Do not invent evidence to fill fields. Return JSON only, following this example: '+json.dumps(REVIEW_EXAMPLE)+'. Status may be edit, suggestion or unresolved. replacement_format is one of '+','.join(REPLACEMENT_FORMATS)+'. Do not rewrite the complete draft.'
    result['messages'][0]['content']=[{'type':'text','text':instruction+'\n'+json.dumps(payload,ensure_ascii=False)}, {'type':'text','text':LITERAL_PREFIX+draft+LITERAL_SUFFIX}]+copy.deepcopy(parts)
    return result

def annotation_ranges(draft):
    """Only program-generated, hash-labelled notes; source prose is not annotation."""
    pattern=r'\\par\\smallskip\\noindent\\textbf\{[^\n]*\[[^\]\n]*-[a-f0-9]{10}\]\.\} (.*?)\n\\par\\smallskip'
    return [(m.start(1),m.end(1)) for m in re.finditer(pattern,draft,re.S)]

def apply_review(draft, proposal, ranges=None):
    """Image evidence and typed annotations before the existing exact-edit validator.

    Plain annotation replacements are escaped once. Intentional mathematical TeX
    patches are never escaped or heuristically placed in math mode.
    """
    from . import focused_recovery as edits, chapter_editorial as editorial
    data=copy.deepcopy(validate_review_shape(proposal))
    notes=annotation_ranges(draft)
    for f in data.get('findings',[]):
        if f.get('status')!='edit':continue
        if not all(isinstance(f.get(k),str) and f[k].strip() for k in EDIT_REQUIRED) or f.get('replacement_format') not in REPLACEMENT_FORMATS:
            f.update(status='suggestion',application_withheld='Missing separated source/draft/change/justification evidence or required exact-edit/format fields')
            continue
        old=f.get('old');a=draft.find(old) if isinstance(old,str) and old else -1
        inside=a>=0 and any(x<=a and a+len(old)<=y for x,y in notes)
        kind=f.get('replacement_format','tex')
        if inside:
            if kind!='plain_annotation':
                f.update(status='suggestion',application_withheld='Generated annotation requires explicitly plain_annotation replacement')
            elif isinstance(f.get('new'),str):
                f['plain_annotation']=f['new'];f['new']=editorial.tex_escape(f['new'])
                f['rendering']='Plain annotation escaped once by chapter_editorial.tex_escape; no source equation edit'
        elif kind!='tex':
            f.update(status='suggestion',application_withheld='Plain annotation outside a verified generated-note body')
    result,log=edits.apply_focused(draft,json.dumps(data),ranges=ranges)
    scope=data.get('scope_review') or {'full_assigned_scope_reviewed':None,'additional_findings_remain':None,'unreviewed_scope':'Not attested by this response; legacy findings do not establish full review'}
    log['scope_review']=dict(scope,attribution='Model attestation, not independent verification')
    log['pending_suggestions']=sum(f['disposition'] in ('unapplied_suggestion','rejected','unresolved') for f in log['findings'])
    log['review_complete_attested']=scope['full_assigned_scope_reviewed'] is True and scope['additional_findings_remain'] is False
    return result,log

def compiling_selection(previous, candidate, compilation):
    """A response or applied proposal cannot promote a failed build."""
    if compilation.get('status')=='passed':return {'selected':candidate,'status':'compiled_working_derivative','previous':previous}
    return {'selected':previous,'status':'retained_last_compiling_version','withheld_candidate':candidate,'build_status':compilation.get('status')}

def image_budget(body,context_length=None):
    plain=copy.deepcopy(body);images=[]
    for message in plain['messages']:
        if not isinstance(message.get('content'),list):continue
        kept=[]
        for part in message['content']:
            if part.get('type')=='text':kept.append(part);continue
            if part.get('type')!='image_url':raise ValueError('Unsupported multimodal input')
            url=part['image_url']['url']
            if not url.startswith('data:image/png;base64,'):raise ValueError('Only bound local PNG content accepted')
            raw=base64.b64decode(url.split(',',1)[1],validate=True)
            if raw[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Invalid PNG')
            w,h=struct.unpack('>II',raw[16:24])
            if not 0<w<=8192 or not 0<h<=8192 or w*h>16*1024**2:raise ValueError('Image outside installed pixel limits')
            images.append((w,h))
        message['content']=kept
    if not 1<=len(images)<=50:raise ValueError('Image count outside current deployment')
    size=len(json.dumps(body,ensure_ascii=False).encode());limit=16*1024**2
    if size>limit:raise ValueError('Image transport cap exceeded; never downsample silently')
    cap=max(16,min(2048,16384//len(images)));rows=sum(geometry(w,h,cap)['tokens'] for w,h in images)
    text_bytes=len(json.dumps(plain,ensure_ascii=False).encode());total=text_bytes+4096+rows+2*len(images)+body['max_tokens']
    if context_length and total>context_length:raise ValueError('Complete text/image/output request does not fit')
    return {'request_bytes':size,'input_token_upper_estimate':text_bytes+4096+rows+2*len(images),'output_token_ceiling':body['max_tokens'],'combined_upper_estimate':total,'image_tokens':rows,'image_count':len(images),'image_feature_bytes':rows*8192,'vision_workspace_reserved_bytes':3*2**28,'basis':'UTF8 text-only upper bound + installed image rows + markers; base64 counted only for byte cap','effective_context_length':context_length}
