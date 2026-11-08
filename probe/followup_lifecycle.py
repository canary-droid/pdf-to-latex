"""Validated adapter contracts for the saved-output Pro continuation only."""
import copy,hashlib,json,re
from collections import Counter
from pathlib import Path
from . import book_completion as scope
from .common import atomic_json,read_json,sha,fingerprint
from .extraction_followup import pro_export,checked_partition

AUTHORIZATION={'original_primary':20,'original_syntax':10,'eligible_primary':16,'eligible_syntax':8,'historical_calls':15,'new_readiness':0}

def allowance(plan,state):
    if plan.get('allowance_contract')!=AUTHORIZATION:raise ValueError('Changed or absent explicit allowance contract')
    if plan.get('maximum_model_requests')!=24 or plan.get('maximum_new_requests')!=30:raise ValueError('Shared reporting/authorization bounds disagree')
    if state.get('disable_dependency_downloads') is not True:raise ValueError('No-download compiler policy changed')
    tasks=state['tasks'];eligible=[t for t in tasks if not t['id'].startswith('matched-')]
    if Counter(t['phase'] for t in eligible)!=Counter(convert=8,critic=8,syntax=8):raise ValueError('Unexpected task expansion or removal')
    for t in tasks:
        if t['id'].startswith('matched-') and t['status']!='unavailable_source_scope':raise ValueError('Failed GLM-OCR gate changed')
    calls=state['calls'];parents=[c['parent'] for c in calls]
    if len(set(parents))!=len(parents) or not set(parents)<=set(t['id'] for t in eligible):raise ValueError('Duplicate or unauthorized reservation')
    counts=Counter(next(t['phase'] for t in eligible if t['id']==c['parent']) for c in calls)
    if counts['convert']+counts['critic']>16 or counts['syntax']>8:raise ValueError('Consumed allowance exceeds frozen derivation')
    if state.get('historical_consumed_calls')!=15:raise ValueError('Historical consumption changed')
    return {'authorized_new':30,'eligible_new':24,'historical_consumed':15,'new_reserved':len(calls),
            'remaining_primary':16-counts['convert']-counts['critic'],'remaining_conditional_syntax':8-counts['syntax']}

def source_regions(run,doc):
    """Reproduce old text byte-for-byte, with a stable native region ledger."""
    run=Path(run);sid=doc['source_id'];parts=[];regions=[];offset=0
    for n in doc['physical_pages']:
        folder=run/'arms/mineru_pro/pages'/f'{sid}-p{n}';raw=read_json(folder/'native.json');assets={}
        for i,b in enumerate(raw):
            crop=folder/f'region-{i}.png'
            if crop.exists():assets[i]=f'assets/{sid}-p{n}-region-{i}.png'
        exported,_=pro_export(raw,assets)
        for b in exported:
            i=b['index'];content=b['text'];kind=b['kind'];segment=f'<!-- physical page {n}; region {i}; kind={kind} -->\n'+content
            if parts:offset+=2
            start=offset;parts.append(segment);offset+=len(segment)
            mapped={'title':'paragraph_title','formula':'equation','image_block':'image'}.get(kind,kind)
            tex=content
            if mapped=='paragraph_title' and not scope.headings(tex):tex=r'\section*{'+tex+'}'
            owned_assets=[assets[i]] if i in assets else []
            regions.append({'id':f'{sid}-p{n:03}-r{i:03}','kind':mapped,'tex':tex,'raw_content':raw[i].get('content'),
                'native':raw[i],'native_file':str((folder/'native.json').relative_to(run)),'native_file_sha256':sha(folder/'native.json'),
                'native_region_index':i,'bbox':b['bbox'],'page':{'original_physical_page':n,'source_id':sid},
                'assets':owned_assets,'source_order':len(regions),'start':start,'end':offset,
                'disposition':'page_furniture' if mapped in scope.FURNITURE else 'assigned_content'})
    return '\n\n'.join(parts),regions

def rebuild_inputs(run,state,plan):
    manifests=[];contracts={};assets_to_bind={}
    for sid in plan['boundaries']:
        doc=next(d for d in plan['documents'] if d['source_id']==sid)
        text,regions=source_regions(run,doc);old=next(x for x in read_json(run/'scope-coverage.json') if x['source_id']==sid)
        if hashlib.sha256(text.encode()).hexdigest()!=old['source_text_sha256']:raise ValueError('Saved extraction text differs from stopped plan')
        units=checked_partition(text,plan['boundaries'][sid]);assignments=[a for a in plan['assignments'] if a['type']=='paper' and a['source_id']==sid]
        if len(units)!=len(assignments):raise ValueError('Changed partition cardinality')
        ownership=[]
        for a,u in zip(assignments,units):
            key=a['key'];selected=[r for r in regions if u['start']<=r['start'] and r['end']<=u['end']]
            crossed=[r['id'] for r in regions if r['start']<u['end'] and r['end']>u['start'] and r not in selected]
            if crossed:raise ValueError('Structural boundary splits a native region: '+repr(crossed))
            ownership += [r['id'] for r in selected]
            substantive=[r for r in selected if r['disposition']=='assigned_content']
            native={'key':key,'title':state['source_units'][key]['section']['title'],'source_sha256':doc['sha256'],'blocks':substantive}
            section=scope.target(native,[r['id'] for r in substantive],title=native['title'])
            prior=[r for r in regions if r['end']<=u['start'] and r['disposition']=='assigned_content']
            # Full earlier source, not an arbitrary first-unit excerpt: all prior
            # definitions/theorems/notation are available without output ownership.
            context='EARLIER SOURCE CONTEXT ONLY; never emit again.\n'+'\n\n'.join(r['tex'] for r in prior)
            refs=sorted({p for b in substantive for p in b['assets']})
            for ref in refs:
                if not (run/'inputs'/ref).is_file():raise ValueError('Expected original crop missing '+ref)
                assets_to_bind['inputs/'+ref]=sha(run/'inputs'/ref)
            folder=run/'inputs'/key;atomic_json(folder/'native.json',native);atomic_json(folder/'assets.json',refs)
            state['source_units'][key].update(section=section,context=context,context_blocks=[r['id'] for r in prior])
            contract={'unit':key,'source_id':sid,'source_sha256':doc['sha256'],'owned_regions':[r['id'] for r in selected],
                'validation_regions':section['blocks'],'furniture':[r['id'] for r in selected if r['disposition']=='page_furniture'],
                'context_regions':[r['id'] for r in prior],'section':section,'context':context,'assets':refs,
                'bounds':[u['start'],u['end']],'input_context_policy':'All earlier substantive source regions. Runtime full input/output admission still applies; no clipping.'}
            atomic_json(folder/'scope-contract.json',contract);contracts[key]=fingerprint(contract)
            for t in state['tasks']:
                if t['key']==key:t['section']=section
            manifests.append({k:v for k,v in contract.items() if k not in ('section','context')})
        if ownership!=[r['id'] for r in regions] or len(set(ownership))!=len(ownership):raise ValueError('Gap/duplicate native ownership')
        atomic_json(run/'region-manifests'/(sid+'.json'),{'source_sha256':doc['sha256'],'regions':regions,'all_native_regions_accounted':True})
    state['derived_inputs']={str(p.relative_to(run)):sha(p) for d in ('inputs','quality','region-manifests') for p in (run/d).rglob('*') if p.is_file()}
    state['source_contracts']=contracts
    atomic_json(run/'region-ownership.json',{'units':manifests,'unique_exact_ownership':True,'unit_count':len(manifests),'semantic_coverage':'Not established by ownership'})
    plan['source_contracts']=contracts;plan['derived_input_hashes']=copy.deepcopy(state['derived_inputs'])
    return manifests

def verify_sources(run,state,plan):
    if state.get('source_contracts')!=plan['source_contracts'] or state.get('derived_inputs')!=plan['derived_input_hashes']:raise ValueError('Derived identity registry changed')
    for key,digest in plan['source_contracts'].items():
        c=read_json(run/'inputs'/key/'scope-contract.json');u=state['source_units'][key]
        if fingerprint(c)!=digest or u['section']!=c['section'] or u['context']!=c['context'] or u['context_blocks']!=c['context_regions']:raise ValueError('Altered scope/context '+key)
        n=read_json(run/'inputs'/key/'native.json');scope.validate_target(n,u['section'])
        if read_json(run/'inputs'/key/'assets.json')!=c['assets']:raise ValueError('Altered asset ownership')

TAGS=r'\\tag\s*\*?\s*\{\s*([^}]+?)\s*\}'
def coverage(document,native,ids):
    result=scope.coverage_check(document,native,ids);blocks=scope.selected_blocks(native,ids)
    body=document.split(r'\begin{document}',1)[-1].split(r'\end{document}',1)[0];body=scope.body_only(body,[h for b in blocks if b['kind']=='paragraph_title' for h in scope.headings(b['tex'])])
    source_numbers={re.sub(r'\s+','',x) for b in blocks for x in re.findall(TAGS,b['tex'])}
    output_numbers={re.sub(r'\s+','',x) for x in re.findall(TAGS,body)}
    for b in blocks:
        if b['kind'] in ('formula_number','equation_number'):
            from .library_repair import equation_labels
            source_numbers.update(equation_labels(b['tex']))
    adjudicated=[]
    for evidence in native.get('equation_label_adjudications',[]):
        block=next((b for b in blocks if b['id']==evidence['block']),None)
        if block is None:continue
        if __import__('hashlib').sha256(block['tex'].encode()).hexdigest()!=evidence['block_text_sha256'] or not evidence.get('source_image_sha256'):raise ValueError('Unbound equation-label adjudication')
        if evidence['observed'] in source_numbers:
            source_numbers.remove(evidence['observed']);source_numbers.add(evidence['source_reading']);adjudicated.append(evidence)
    result['equation_label_adjudications']=adjudicated
    heading_checks=[]
    for evidence in native.get('heading_adjudications',[]):
        block=next((b for b in blocks if b['id']==evidence['block']),None)
        if block is None:continue
        if __import__('hashlib').sha256(block['tex'].encode()).hexdigest()!=evidence['block_text_sha256'] or not evidence.get('source_image_sha256'):raise ValueError('Unbound heading adjudication')
        title=evidence['title']
        if evidence['disposition']=='retained_caption':
            if evidence['exact_output_anchor'] not in body:continue
        elif evidence['disposition']!='running_furniture':raise ValueError('Unknown heading adjudication')
        if title in result['missing_heading_candidates']:result['missing_heading_candidates'].remove(title)
        heading_checks.append(evidence)
    result['heading_adjudications']=heading_checks
    auto=bool(re.search(r'\\begin\s*\{(?:equation|align|gather|multline)\}',body))
    missing_numbers=sorted(source_numbers-output_numbers)
    expected={a for b in blocks if b['kind'] in ('image','chart') for a in b.get('assets',[])}
    got=set(scope.image_references(body));represented=set(got)
    for group in native.get('verified_figure_groups',[]):
        if group['canonical'] in got:represented.update(group['members'])
        elif set(group['members'])<=got:represented.add(group['canonical'])
    missing_figures=sorted(expected-represented)
    prose=[];out_words=set(scope.plain(body).split())
    for b in blocks:
        if b['kind']!='text':continue
        words={w for w in scope.plain(b['tex']).split() if len(w)>3}
        if len(words)>=15 and len(words & out_words)/len(words)<.25:prose.append(b['id'])
    empty=len(scope.plain(body))<20
    risk=empty or missing_figures or result.get('duplicated_verified_figures') or result['table_count_warning'] or result['missing_heading_candidates'] or prose or (missing_numbers and not auto)
    result.update(empty_or_insubstantial_output=empty,expected_figure_assets=sorted(expected),missing_expected_assets=missing_figures,
        source_numbered_equations=sorted(source_numbers),output_explicit_equation_numbers=sorted(output_numbers),
        missing_explicit_equation_numbers=missing_numbers if not auto else [],
        automatic_numbering_unverified=missing_numbers if auto else [],missing_substantive_span_candidates=prose,
        coverage_status='omission_risk' if risk else 'requires_source_review',
        semantic_completeness='not established; no claim based on completion or compilation')
    return result

def assemble_documents(units, *, theorem_declarations=None):
    """Conservative editable assembly; unsupported preambles fail, never disappear."""
    parsed=[];packages={};changes=[];owners={};bibowners={};declared={}
    theorem_declarations=theorem_declarations or {}
    for key,text in units:
        m=re.search(r'\\begin\s*\{document\}(.*?)\\end\s*\{document\}',text,re.S)
        if not m:raise ValueError('Missing standalone document body '+key)
        pre=text[:m.start()];body=m.group(1)
        for cmd in re.findall(r'\\(?:documentclass|usepackage)(?:\[[^]]*\])?\{[^}]+\}',pre):
            if cmd.startswith(r'\usepackage'):
                pm=re.fullmatch(r'\\usepackage(?:\[([^]]*)\])?\{([^}]+)\}',cmd)
                options=tuple(sorted(x.strip() for x in (pm[1] or '').split(',') if x.strip()))
                for package in pm[2].split(','):
                    package=package.strip()
                    if package in packages and packages[package]!=options:raise ValueError('Conflicting package options: '+package)
                    packages[package]=options
            pre=pre.replace(cmd,'')
        for declaration in list(re.finditer(r'\\newtheorem\{([A-Za-z]+)\}\{([^{}]+)\}',pre)):
            env,title=declaration.groups()
            if theorem_declarations.get(env)!=title:continue
            if env in declared and declared[env]!=title:raise ValueError('Conflicting theorem declaration')
            declared[env]=title;pre=pre.replace(declaration[0],'')
        if re.search(r'\\(?:newtheorem|Declare|RequirePackage|bibliography|input|include|PassOptions|geometry|hypersetup|setlength|AtBegin)',pre):raise ValueError('Unsupported preamble requires explicit reconciliation: '+key)
        for label in re.findall(r'\\label\s*\{([^}]+)\}',body):owners.setdefault(label,[]).append(key)
        for label in re.findall(r'\\bibitem(?:\[[^]]*\])?\s*\{([^}]+)\}',body):bibowners.setdefault(label,[]).append(key)
        parsed.append((key,pre,body))
    for labels in (owners,bibowners):
        if any(len(v)!=len(set(v)) for v in labels.values()):raise ValueError('Duplicate label/key within a standalone unit')
    parts=[];unresolved=[]
    def rename(label,key,registry):
        candidates=registry.get(label,[])
        if key in candidates:return key+'--'+label
        if len(candidates)==1:return candidates[0]+'--'+label
        unresolved.append({'unit':key,'label':label,'candidates':candidates});return label
    for key,pre,body in parsed:
        before=body
        body=re.sub(r'\\(label|ref|eqref|pageref|autoref)\s*\{([^}]+)\}',lambda m:'\\'+m[1]+'{'+rename(m[2],key,owners)+'}',body)
        body=re.sub(r'(\\bibitem(?:\[[^]]*\])?\s*)\{([^}]+)\}',lambda m:m[1]+'{'+rename(m[2],key,bibowners)+'}',body)
        body=re.sub(r'(\\cite\w*\*?(?:\[[^]]*\])?\s*)\{([^}]+)\}',lambda m:m[1]+'{'+','.join(rename(x.strip(),key,bibowners) for x in m[2].split(','))+'}',body)
        parts.append((key,'\\begingroup\n'+pre+'\n\\setcounter{equation}{0}\n\\setcounter{figure}{0}\n\\setcounter{table}{0}\n'+body+'\n\\endgroup\n'))
        changes.append({'unit':key,'technical_operations':['article master class','package declarations deduplicated without changing options','local preamble definitions grouped','labels/citations namespaced; unique cross-unit references resolved','standalone equation/figure/table counters reset'], 'body_reference_keys_changed':body!=before})
    preamble='\\documentclass{article}\n'+'\n'.join('\\usepackage'+('['+','.join(v)+']' if v else '')+'{'+k+'}' for k,v in packages.items())
    preamble+='\n'+'\n'.join('\\newtheorem{'+k+'}{'+v+'}' for k,v in declared.items())
    master=preamble+'\n\\begin{document}\n'+'\n\\clearpage\n'.join('\\input{parts/'+key+'.tex}' for key,_ in parts)+'\n\\end{document}\n'
    return master,dict(parts),{'changes':changes,'theorem_declarations':declared,'unresolved_references':unresolved,'mathematics_changed':False}

def migrate(controller):
    import shutil,time
    from .common import writer_lock
    from .experiment import InputGuard
    root=controller.ROOT;parent=root/'runs/extraction-followup-20261105T204630Z'
    with writer_lock(root),writer_lock(root/'runs'),writer_lock(parent):
        state=read_json(parent/'state.json');old=read_json(parent/'plan.json');binding=read_json(parent/'binding.json')
        if state['status']!='stopped_error' or state['calls'] or not state['extraction_done']:raise ValueError('Unexpected parent consumption/state; inspect before migration')
        if read_json(parent/'qualification/source-review.json')['passed']:raise ValueError('Failed GLM gate changed')
        if len(state['extraction']['mineru_pro']['pages'])!=67 or any(p['status']!='completed' for p in state['extraction']['mineru_pro']['pages'].values()):raise ValueError('Incomplete parent OCR')
        InputGuard(binding['files']).check()
        if sha(parent/'plan.json')!=binding['plan_sha256']:raise ValueError('Parent plan changed')
        snapshot=root/'results/followup-lifecycle-development/previous-code'
        for name,digest in binding['code'].items():
            if sha(snapshot/name)!=digest:raise ValueError('Preserved implementation mismatch')
        pointer=read_json(controller.POINTER)
        if Path(pointer['run']).resolve()!=parent:raise ValueError('Selected run already changed; use existing continuation')
        size=sum(p.stat().st_size for p in parent.rglob('*') if p.is_file())
        if shutil.disk_usage(root).free<size*2+10*1024**3:raise ValueError('Insufficient copy/output disk reserve')
        child=root/'runs'/('extraction-followup-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-lifecycle')
        shutil.copytree(parent,child);shutil.copytree(snapshot,child/'parent-implementation')
        plan=copy.deepcopy(old);plan.update(lifecycle_version=1,continuation_parent=str(parent),allowance_contract=AUTHORIZATION,maximum_model_requests=24)
        state.update(status='prepared',diagnostic=None,stage='saved-output lifecycle continuation',historical_consumed_calls=15,lifecycle_version=1,disable_dependency_downloads=True,continuation_parent=str(parent))
        state.pop('traceback',None);state.pop('inspection',None);state.pop('finished_at',None)
        # Do not replay or re-qualify extraction, readiness, or failed GLM-OCR.
        assert state['extraction_done'] and state['glm_qualification_done'] and not state['glm_qualified']
        rebuild_inputs(child,state,plan)
        for key,versions in state['versions'].items():
            for label,v in versions.items():
                v['parent_build_provenance']={'run':str(controller.PARENT),'original_record':copy.deepcopy(v['compilation']),'fresh_local_compile':False,'source_sha256':v['sha256']}
        allowance(plan,state)
        atomic_json(child/'plan.json',plan)
        frozen={str(child/Path(p).relative_to(parent)) if Path(p).is_relative_to(parent) else p:h for p,h in binding['files'].items()}
        for page in state['extraction']['mineru_pro']['pages'].values():
            for item in page['outputs']:
                p=child/'arms/mineru_pro'/item['path']
                if sha(p)!=item['sha256']:raise ValueError('Saved OCR output changed')
                frozen[str(p)]=item['sha256']
        frozen[str(child/'qualification/source-review.json')]=sha(child/'qualification/source-review.json')
        atomic_json(child/'binding.json',{'code':controller.base.code_binding(),'plan_sha256':sha(child/'plan.json'),'files':frozen})
        atomic_json(child/'linked-parent.json',{'parent':str(parent),'state_sha256':sha(parent/'state.json'),'binding_sha256':sha(parent/'binding.json'),'preserved_pages':67,'preserved_new_calls':0,'historical_calls':15,'allowances_reset':False})
        controller.save(child,state);controller.verify(child)
        atomic_json(controller.POINTER,{'run':str(child),'parent':str(parent)})
        print('Linked continuation prepared:',child);return child
