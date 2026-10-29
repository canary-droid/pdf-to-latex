"""Opt-in complete native chapter inputs; no OCR, portable-grammar filtering or LLM."""
from collections import Counter
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

from .common import atomic_json, read_json, sha, fingerprint, files_manifest, contained
from .saved_pages import saved_pages, render_region
from .book_review import owned_scope

ROOT=Path(__file__).resolve().parents[1]
VERSION='chapter-native-v1'
GATHERAL='runs/convert-basic-20261025T230247Z-e6bb30'
KLEBANER='runs/convert-basic-20261020T075104Z-48fd90'
BLANKS=(3,9,15,21,23,31,199)
PARTS=[
 ('front','Front matter',1,31),
 ('01','Stochastic Volatility and Local Volatility',32,45),
 ('02','The Heston Model',46,55),
 ('03','The Implied Volatility Surface',56,73),
 ('04','The Heston-Nandi Model',74,80),
 ('05','Adding Jumps',81,104),
 ('06','Modeling Default Risk',105,117),
 ('07','Volatility Surface Asymptotics',118,131),
 ('08','Dynamics of the Volatility Surface',132,137),
 ('09','Barrier Options',138,152),
 ('10','Exotic Cliquets',153,163),
 ('11','Volatility Derivatives',164,192),
 ('postscript','Postscript',193,193),
 ('bibliography','Bibliography',194,198),
 ('blank','Intentional blank',199,199),
 ('index','Index (original printed-page references)',200,210),
]
AUX={'header','footer','page_number'}
VISUAL={'image','chart','table'}


def new_path(prefix):
    return ROOT/'runs'/(prefix+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6])


def strings(value, kind=None):
    """Literal saved content leaves; no equation recognition or TeX rewriting."""
    if isinstance(value,dict):
        kind=value.get('type',kind)
        for k,v in value.items():
            if k=='content' and isinstance(v,str):yield kind,v
            elif isinstance(v,(dict,list)):yield from strings(v,kind)
    elif isinstance(value,list):
        for x in value:yield from strings(x,kind)


def select_parts(pages, parts):
    index={p['page']['selected_page']:p for p in pages}
    if len(index)!=len(pages):raise ValueError('Duplicate owned pages')
    used=[];result=[]
    for key,title,first,last in parts:
        chosen=[index[n] for n in range(first,last+1)]
        if any(p['page']['owner'] is not True for p in chosen):raise ValueError('Context page cannot be owned')
        used.extend(range(first,last+1));result.append((key,title,chosen))
    if len(used)!=len(set(used)):raise ValueError('Chapter boundaries overlap')
    return result


def classify_pages(pages, classification, source, source_hash):
    """Source-bound notices are content, never permission to erase recognized blocks."""
    if classification['source_id']!=source or classification['source_sha256']!=source_hash:
        raise ValueError('Page classification belongs to a different source/version')
    by_physical={p['page']['original_physical_page']:p for p in pages}
    for row in classification['pages']:
        page=by_physical[row['physical_pdf_page']]
        actual=[{'type':b['kind'],'text':' '.join(v for _,v in strings(b['native']))} for b in page['blocks']]
        if actual!=row['recognized_content']:
            raise ValueError(f'Page classification evidence changed: {source} physical {row["physical_pdf_page"]}')
        page['page']['classification']=row['classification']


def split_plan(blocks):
    """At most two outputs at an observed section heading, never inside a block.

    Conservative structural guard: do not split at theorem/proof/example/remark
    headings, running headers or a continuation. This is not semantic certification.
    """
    total=sum(len(b['tex']) for b in blocks);pos=0;candidates=[];proof_open=False
    for i,b in enumerate(blocks):
        text=' '.join(v for _,v in strings(b['native'])).strip()
        native=b['native'];bbox=b.get('bbox')
        if re.match(r'(?i)^\s*proof\b',text):proof_open=True
        # An explicit major numbered section (e.g. 4.4) delimits the preceding
        # statement/proof even when OCR lost its end square. Lesser unnumbered
        # headings cannot close an open proof merely to make an output fit.
        major_numbered=bool(re.match(r'^\d+\.\d+\s',text))
        if (0<i<len(blocks)-1 and b['kind']=='paragraph_title'
                and native.get('level',2)<=2 and bbox and bbox[1]>.1
                and not native.get('continues_prev') and (not proof_open or major_numbered)
                and not re.match(r'(?i)(proof|theorem|lemma|corollary|definition|example|remark|proposition)\b',text)
                and .2*total<pos<.8*total):
            candidates.append((abs(pos-total/2),i,text))
        pos+=len(b['tex'])
        if re.search(r'\\(?:Box|square|blacksquare)\b|[□∎]|\bQ\.?E\.?D\.?\s*$',text):proof_open=False
    if not candidates:return {'groups':[],'reason':'No safe observed section boundary; no arbitrary text split'}
    _,i,title=min(candidates)
    return {'groups':[[b['id'] for b in blocks[:i]],[b['id'] for b in blocks[i:]]],
            'boundary_block':blocks[i]['id'],'heading':title,
            'basis':'native section heading, whole blocks; full chapter remains in each request',
            'limitation':'structural boundary, not independently verified proof completeness'}


def collect_assets(native, page, root, out, consumed):
    """Copy only paths referenced by this native block; retain native evidence separately."""
    run=Path(page['source_run']);attempt=run/page['source_attempt'];mapping={}
    def visit(v):
        if isinstance(v,dict):
            for k,x in list(v.items()):
                if k=='image_path' and isinstance(x,str) and x:
                    src=contained(attempt/'output',x)
                    if not src.is_file() or src.is_symlink():raise ValueError('Missing saved native asset: '+str(src))
                    if src.suffix.lower() not in ('.png','.jpg','.jpeg'):raise ValueError('Unsupported native image format')
                    digest=sha(src);name='assets/'+digest[:24]+src.suffix.lower()
                    dest=out/name;dest.parent.mkdir(exist_ok=True)
                    if not dest.exists():shutil.copyfile(src,dest)
                    consumed[str(src)]=digest;mapping[x]=name;v[k]=name
                elif isinstance(x,(dict,list)):visit(x)
        elif isinstance(v,list):
            for x in v:visit(x)
    visit(native)
    return list(dict.fromkeys(mapping.values()))


def prepare(out=None, *, source_specs=None, evidence_root=None, renderer_python=None):
    out=Path(out) if out else new_path('chapter-glm-input')
    out.mkdir(parents=True,exist_ok=False)
    consumed={};books={};jobs=[];all_items=[]
    evidence_root=Path(evidence_root) if evidence_root else ROOT
    specs=source_specs or [{"source":"gatheral","run":GATHERAL,"parts":PARTS,"prefix":"gatheral","blanks":BLANKS,"pages":210},
                          {"source":"klebaner-ch4-7","run":KLEBANER,"parts":[("04","Brownian Motion Calculus",1,31)],"prefix":"klebaner","blanks":[]}]
    for spec in specs:
        source=spec['source'];run=evidence_root/spec['run']
        state=read_json(run/'state.json');record=state['settings']['sources'][source]
        blanks=[(source,n) for n in spec.get('blanks',[])]
        pages=owned_scope(saved_pages(evidence_root,run,source,verified_blank_pages=blanks),source,record)
        if spec.get('page_classification'):
            classification=read_json(spec['page_classification'])
            classify_pages(pages,classification,source,record['sha256'])
            consumed[str(Path(spec['page_classification']).resolve())]=sha(spec['page_classification'])
        consumed[str(run/'state.json')]=sha(run/'state.json')
        consumed[str(evidence_root/record['pdf'])]=record['sha256']
        parts=spec['parts']
        chosen=select_parts(pages,parts)
        if source=='gatheral' and sum(len(p) for _,_,p in chosen)!=210:raise ValueError('Gatheral must account for all 210 pages')
        if source=='klebaner-ch4-7' and [p['page']['original_physical_page'] for p in chosen[0][2]]!=list(range(106,137)):
            raise ValueError('Klebaner Chapter 4 boundary mismatch')
        if spec.get('pages') and sum(len(p) for _,_,p in chosen)!=spec['pages']:raise ValueError('Incomplete registered book coverage')
        books[source]={'conversion':str(run),'source_record':record,'selected_owned_pages':sum(len(p) for _,_,p in chosen)}
        for key,title,part_pages in chosen:
            key=spec['prefix']+'-'+key
            folder=out/'chapters'/key;folder.mkdir(parents=True)
            rows=[];page_rows=[];fallback=[]
            for page in part_pages:
                attempt=run/page['source_attempt'];payload=read_json(attempt/'output/middle_json.json')
                for n in ('input.pdf','page-map.json','output/middle_json.json'):consumed[str(attempt/n)]=sha(attempt/n)
                page_rows.append({k:page[k] for k in ('page_id','page','source_run','source_attempt','structured_sha256','page_map_sha256')})
                if key in ('gatheral-front','gatheral-index') and page['page']['selected_page'] not in BLANKS:
                    name='assets/'+page['page_id']+'-source.png'
                    render_region(attempt/'input.pdf',page['page']['local_page_idx'],out/name,max_edge=1800)
                    fallback.append({'page':page['page'],'asset':name})
                for block in page['blocks']:
                    native=copy.deepcopy(block['native'])
                    assets=collect_assets(native,page,ROOT,out,consumed)
                    if (block['kind'] in VISUAL or not list(strings(native))) and not assets and block.get('bbox'):
                        name='assets/'+block['id'].replace(':','-')+'.png'
                        render_region(attempt/'input.pdf',page['page']['local_page_idx'],out/name,bbox=block['bbox'],max_edge=1800)
                        assets=[name]
                    rows.append({**block,'page':page['page'],'assets':assets,'render_native':native})
                    header={k:v for k,v in payload.items() if k!='pages'}
                    all_items.append({'id':block['id'],'document':header,'native':native})
            jobs.append({'key':key,'title':title,'source':source,'pages':page_rows,'blocks':rows,'fallback':fallback})
    atomic_json(out/'renderer-input.json',all_items)
    renderer=ROOT/'scripts/render-chapter-native.py'
    subprocess.run([str(renderer_python or evidence_root/'.venv-mineru/bin/python'),'-B',str(renderer),str(out/'renderer-input.json'),str(out/'renderer-output.json')],
                   check=True,timeout=180,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
    rendered=read_json(out/'renderer-output.json');parts=[]
    for job in jobs:
        blocks=job['blocks'];source=[];last=None;fallbacks=[];math_count=0
        for b in blocks:
            if b['page']['selected_page']!=last:
                source.append(f"% SOURCE_PAGE selected={b['page']['selected_page']} original={b['page']['original_physical_page']} source={job['source']}")
                last=b['page']['selected_page']
            r=rendered[b['id']];tex=r['tex']
            if b['kind'] in AUX:
                tex='% Page furniture: '+json.dumps(list(strings(b['native'])),ensure_ascii=False)
            elif not tex:
                # Explicit complete raw OCR, never a successful empty export.
                tex='% UNRESOLVED NATIVE BLOCK: '+json.dumps(b['native'],ensure_ascii=False)
                tex+='\n'+ '\n'.join(r'\includegraphics[width=.95\linewidth]{'+x+'}' for x in b['assets'])
                fallbacks.append({'block':b['id'],'reason':r['error'] or 'Native renderer emitted no body'})
            literal_math=[v for kind,v in strings(b['native']) if kind in ('equation','equation_inline') and v]
            for literal in literal_math:
                math_count+=1
                if literal not in tex:
                    # Exact native value is available even for renderer normalization.
                    tex+='\n% Literal native mathematics follows (comparison data):\n'+literal+'\n'
            # Tables retain editable native rendering as comparison material, but
            # source images are the required output representation for this pilot.
            if b['kind']=='table':tex+='\n% TABLE SOURCE ASSET (preserve source crop/caption; editable fidelity unverified): '+','.join(b['assets'])
            b['tex']=tex;b['renderer_error']=r['error'];b.pop('render_native')
            source.extend(['% SRC '+b['id'],tex])
        text='\n\n'.join(source)+'\n'
        folder=out/'chapters'/job['key'];(folder/'source.tex').write_text(text)
        atomic_json(folder/'source.json',job)
        substantive=[b for b in blocks if b['kind'] not in AUX]
        plan=split_plan(substantive)
        inventory={'key':job['key'],'title':job['title'],'source':job['source'],
            'pages':[p['page']['selected_page'] for p in job['pages']],
            'original_pages':[p['page']['original_physical_page'] for p in job['pages']],
            'verified_blanks':[p['page']['selected_page'] for p in job['pages'] if job['source']=='gatheral' and p['page']['selected_page'] in BLANKS],
            'block_count':len(blocks),'kinds':dict(Counter(b['kind'] for b in blocks)),
            'target_ids':[b['id'] for b in substantive],
            'source_characters':len(text),'source_bytes':len(text.encode()),'source_sha256':sha(folder/'source.tex'),
            'native_math_strings':math_count,'all_native_math_present':all(v in text for b in blocks for k,v in strings(b['native']) if k in ('equation','equation_inline') and v),
            'fallbacks':fallbacks,'split':plan,
            'assets':sorted(set(x for b in blocks if b['kind'] in VISUAL for x in b['assets'])),
            'semantic_fidelity':'not verified; all owned blocks and complete native data retained',
            'mechanical_coverage':'block inventory including unnumbered equations, footnotes, captions, references and auxiliary text'}
        if not inventory['all_native_math_present']:raise ValueError('Native mathematics lost during chapter assembly')
        atomic_json(folder/'inventory.json',inventory);parts.append(inventory)
    if 'gatheral' in books and sum(p['kinds'].get('ref_text',0) for p in parts if p['key']=='gatheral-bibliography')!=76:raise ValueError('Bibliography no longer has 76 saved reference blocks')
    atomic_json(out/'inputs.json',{'version':VERSION,'books':books,'parts':parts,'consumed':consumed,
        'blank_policy':'explicit verified source-page list, schema-default absent blocks allowed only there',
        'renderer':'installed DocVortex public render_latex, isolated blocks; no recognition or inference',
        'render_bridge_sha256':sha(renderer)})
    # A preparation seal binds complete extracts, assets and sidecars; raw runs untouched.
    atomic_json(out/'manifest.json',files_manifest(out))
    return out
