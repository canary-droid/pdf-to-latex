"""Opt-in overnight recovery hooks for the existing library controller.

No private configuration is read at import or preparation. Both providers use
library_fallbacks' ONE combined ledger. There is no autonomous task expansion.
"""
import copy,difflib,json,re,time,urllib.request
from pathlib import Path
from .common import read_json,atomic_json,sha,fingerprint
from . import library_fallbacks as paid,kimi_escalation as kimi,mathpix_experiment as mathpix,author_source,book_completion

def enabled(run):return read_json(Path(run)/'plan.json').get('overnight',False)
def approval(run):return read_json(Path(run)/'plan.json')['paid_approval']

def verify(run,state,plan,binding):
    a=plan['paid_approval']
    if plan.get('approval_registry') and read_json(plan['approval_registry'])['run']!=str(run):raise kimi.IntegrityError('Obsolete preparation for this single overnight approval')
    if plan.get('allocation_id'):
        from .library_allocation import verify as verify_allocation
        root=verify_allocation(a)
        if plan['allocation_id']!=a['allocation_id'] or binding.get('config')!=read_json(root/'binding.json')['config']:raise kimi.IntegrityError('Allocation/provider binding changed')
    elif a['ledger_root']!=str(Path(run)/'fallback-budget'):raise kimi.IntegrityError('Shared budget location changed')
    if plan['paid_enabled'] is not True or plan['spend_cap_usd']!='7.00' or a['new_spend_cap_usd']!='7.00' or a.get('explicitly_approved') is not True:raise kimi.IntegrityError('Shared $7 approval changed')
    if plan['settings'].get('compile_pdf') or plan['settings']['review_effort']!='high' or plan['settings']['converter_effort']!='high':raise kimi.IntegrityError('Library settings changed')
    if binding.get('config')!=plan['kimi_config'] or binding.get('prior_billing')!=plan['prior_billing']:raise kimi.IntegrityError('Frozen paid configuration changed')
    for d in plan['documents']:
        source=a['sources'][d['source_id']]
        if source['sha256']!=d['sha256'] or not set(d['physical_pages'])<=set(source['physical_pages']):raise kimi.IntegrityError('Approved source scope changed')
    if state.get('paid_approval_sha256')!=fingerprint(a):raise kimi.IntegrityError('Approval state mismatch')

def runtime_authorise(run):
    """Called only by operator launch/worker; never read a key during preparation."""
    run=Path(run);p=read_json(run/'plan.json');b=read_json(run/'binding.json')
    if p.get('allocation_id'):
        from .library_allocation import verify
        verify(p['paid_approval']);return
    atomic_json(run/'authorisation.json',{'binding_sha256':sha(run/'binding.json'),'accepted_pilot_budget_usd':b['config']['pilot_budget_usd'],'authority':'Explicit overnight combined $7 task; operator launched this frozen run'})
    kimi.ledger(run,create=not (run/'billing.json').exists())

def mathpix_pdf_rate(raw):
    """Read the first price in the standard v3/pdf card, not another route/tier."""
    from html.parser import HTMLParser
    class Text(HTMLParser):
        def __init__(self):super().__init__();self.values=[];self.hidden=0
        def handle_starttag(self,tag,attrs):
            if tag in ('script','style'):self.hidden+=1
        def handle_endtag(self,tag):
            if tag in ('script','style'):self.hidden=max(0,self.hidden-1)
        def handle_data(self,data):
            if not self.hidden:self.values.append(data)
    parser=Text();parser.feed(raw.decode('utf-8'));text=' '.join(' '.join(parser.values).split())
    match=re.search(r'POST\s*v3/pdf(.*?)(?:POST|$)',text,re.S)
    price=re.search(r'\$\s*([0-9.]+)\s*/?\s*page',match[1]) if match else None
    if not price:raise paid.NotApproved('Standard Mathpix v3/pdf price cannot be identified; no paid dispatch')
    return __import__('decimal').Decimal(price[1])

def mathpix_client(run):
    p=Path(run)/'paid-readiness/mathpix.json'
    # Current public rate/privacy checked without secrets. Authentication is read
    # only after these non-generating public checks, with existing secret-safe API.
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),mathpix.NoRedirect())
    with opener.open('https://website.mathpix.com/pricing/api',timeout=30) as response:raw=response.read(2*1024*1024)
    if mathpix_pdf_rate(raw)!=__import__('decimal').Decimal('0.005'):raise paid.NotApproved('Current standard Mathpix PDF price changed; no paid dispatch')
    atomic_json(p,{'at':mathpix.now(),'price_per_page_usd':'0.005','public_price_response_sha256':__import__('hashlib').sha256(raw).hexdigest(),'source':'https://website.mathpix.com/pricing/api','privacy_opt_out':mathpix.OPTIONS['metadata'],'invoice_or_credit_balance':'not exposed by existing usage endpoint; not inferred'})
    return mathpix.Client(read_json('/home/mdi/.config/pdf-to-latex/mathpix.json'))

def bad_pages(run,d,s):
    records=s['extraction'].get('mineru_pro',{}).get('pages',{});bad=[]
    for n in d['physical_pages']:
        if str(n) in d.get('blank_pages',{}):continue
        row=records.get(f'{d["source_id"]}-p{n}',{});path=Path(run)/'arms/mineru_pro/pages'/f'{d["source_id"]}-p{n}/native.json'
        if row.get('status')!='completed' or not path.exists():bad.append(n);continue
        raw=read_json(path);text=' '.join(str(x.get('content','')) for x in raw)
        if not raw or not text.strip() or text.count('\ufffd')>max(5,len(text)//50):bad.append(n)
    return bad

def extraction_round(run,s,*,client=None):
    """One GET round per provider job; independent local papers need not wait."""
    from scripts import library_pipeline as c
    run=Path(run);p=read_json(run/'plan.json');a=approval(run);pending=False
    for d in p['documents']:
        paid.pause_guard(run)
        sid=d['source_id'];rec=s['documents'][sid]
        if d.get('fixed_native') or rec.get('mathpix_final') or (rec.get('planning_done') and rec.get('reused_units') and not rec.get('failed_pages')):continue
        bad=bad_pages(run,d,s)
        if not bad:continue
        rec['garbled_or_failed_pages']=bad
        # A single immutable affected subset per document/extraction lineage.
        prop=run/'fallbacks'/f'{sid}-extraction/proposal.json'
        if prop.exists():record=read_json(prop)
        else:
            import fitz
            subset=run/'fallbacks'/sid/'affected-pages.pdf';subset.parent.mkdir(parents=True,exist_ok=True)
            if not subset.exists():
                with fitz.open(d['original']) as pdf:
                    out=fitz.open()
                    for n in bad:out.insert_pdf(pdf,from_page=n-1,to_page=n-1)
                    out.save(subset);out.close()
            unit={'id':sid,'source_id':sid,'source_sha256':d['sha256'],'physical_pages':bad,'subset':str(subset),'subset_sha256':sha(subset),'original_to_subset':{str(n):i+1 for i,n in enumerate(bad)}}
            record=read_json(paid.proposal(run,unit,'extraction','incomplete'))
        paid.register_scope(run,record,a,unit_verified=True)
        try:
            if client is None:client=mathpix_client(run)
            if s.get('mathpix_key_id') not in (None,client.key_id):raise kimi.IntegrityError('Mathpix credential identity changed; existing jobs/allowances cannot reset')
            s['mathpix_key_id']=client.key_id;c.save(run,s)
            out=paid.run_mathpix(run,record,a,client=client)
            rec['mathpix']=out
            if out['status']=='downloaded':
                recovered=materialise_mathpix(run,record,out)
                rec.update(mathpix_material=recovered,mathpix_final=True,failed_pages=[])
                for page in recovered['pages']:
                    n=page['physical_page'];s.setdefault('mathpix_pages',{})[f'{sid}-p{n}']=page
                if not rec.get('planning_done'):s['inputs_prepared']=False
            elif out['status'] in ('polling_existing_job','awaiting_outputs'):pending=True
            else:rec['mathpix_final']=True
        except c.runtime.StopRun:raise
        except (kimi.IntegrityError,kimi.IdentityError):raise
        except Exception as exc:rec.update(mathpix_final=True,mathpix={'status':'blocked_or_invalid','diagnostic':type(exc).__name__+': '+str(exc)})
        c.save(run,s)
    return pending

def materialise_mathpix(run,record,out):
    """Keep raw TeX/assets and reconstruct page-owned evidence, never infer accuracy."""
    unit=record['unit'];folder=Path(out['job_folder'])
    for artifact in out.get('outputs',{}).values():
        if artifact.get('sha256') and sha(Path(run)/artifact['path'])!=artifact['sha256']:raise kimi.IntegrityError('Retrieved Mathpix artifact changed')
    lines=read_json(folder/'raw.lines.mmd.json');pages=lines.get('pages',[])
    if [p.get('page') for p in pages]!=list(range(1,len(unit['physical_pages'])+1)):raise kimi.IntegrityError('Structured Mathpix page map incomplete/duplicated')
    entries=mathpix.safe_zip((folder/'raw.tex.zip').read_bytes());source=folder/'source';source.mkdir(exist_ok=True)
    from .source_library import copy_verified
    for name,data in entries.items():
        p=source/name;p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists() and p.read_bytes()!=data:raise kimi.IntegrityError('Retrieved author/source file changed')
        p.write_bytes(data)
    mains=[n for n,b in entries.items() if n.endswith('.tex') and b'\\begin{document}' in b]
    direct=None
    if len(mains)==1:
        check,text=author_source.inspect_tree(source,mains[0]);direct={'path':str(source/mains[0]),'sha256':sha(source/mains[0]),'dependency_check':check,'pages':unit['physical_pages']}
    recovered=[]
    for page,n in zip(pages,unit['physical_pages']):
        blocks=[];assets={}
        for i,line in enumerate(page.get('lines',[])):
            text=line.get('text','');kind='text'
            if not isinstance(text,str):raise ValueError('Invalid Mathpix text line')
            for match in list(re.finditer(r'!\[[^]]*\]\(([^)]+)\)',text)):
                basename=Path(match[1].split('?')[0]).name;candidates=[name for name in entries if Path(name).name==basename]
                if len(candidates)!=1:raise ValueError('Missing/ambiguous Mathpix source figure '+basename)
                ref='assets/mathpix-'+unit['source_id']+'-'+basename;assets[ref]=str(source/candidates[0]);text=text.replace(match[0],r'\includegraphics{'+ref+'}');kind='image'
            if re.search(r'\\\[|\\begin\{(?:equation|align)|^\$\$',text):kind='equation'
            if '<table' in text or r'\begin{tabular}' in text:kind='table'
            if text.startswith('#'):kind='paragraph_title';text=r'\section*{'+text.lstrip('# ')+'}'
            blocks.append({'id':f'{unit["source_id"]}-mathpix-p{n}-r{i}','kind':kind,'tex':text,'page':{'original_physical_page':n},'assets':[a for a in assets if a in text],'native':line})
        if not blocks or not any(b['tex'].strip() for b in blocks):raise ValueError('Mathpix returned an empty source page')
        recovered.append({'physical_page':n,'blocks':blocks,'assets':assets,'source_sha256':unit['source_sha256'],'raw_page_sha256':fingerprint(page),'source_kind':'Mathpix recovery, mathematically unverified'})
    result={'pages':recovered,'direct_tex':direct,'raw_folder':str(folder),'page_mapping':dict(zip(range(1,len(pages)+1),unit['physical_pages'])),'fidelity':'Requires original-image review; successful OCR is not proof'}
    atomic_json(folder/'library-material.json',result);return result

def unit_record(run,s,t):
    from scripts import library_pipeline as c
    run=Path(run);u=s['source_units'][t['key']];images=c.review_images(run,s,t);full=[x for x in images if x['crop'] is None]
    if len(full)>4:raise paid.NotApproved('Bounded Kimi route permits at most four source pages; no clipping')
    chosen=full+([next(x for x in images if x['crop'] is not None)] if len(full)<4 and any(x['crop'] is not None for x in images) else [])
    unit={'id':t['key'],'source_id':t['source_key'],'source_sha256':s['documents'][t['source_key']]['source_sha256'],'physical_pages':u['physical_pages'],'owned_blocks':u['blocks'],'primary':u['text'],'secondary':u['secondary'],'context':u.get('cloud_context',u['context']),
          'cloud_images':[{'source_id':r['source_id'],'source_sha256':r['source_sha256'],'page':r['physical_page'],'path':str(run/r['path']),'sha256':r['sha256'],'bbox':r['crop']} for r in chosen]}
    from .library_repair import lossless_images
    unit['cloud_images']=lossless_images(unit['cloud_images'],run/'inputs'/t['key']/'cloud-lossless')
    if t['phase']=='critic':
        v=s['versions'][t['key']][s['current_versions'][t['key']]];path=run/v['path'];unit.update(draft_path=str(path),draft_sha256=v['sha256'],draft_ranges=[[0,len(path.read_text())]])
    return unit

def pending_model_recovery(s):
    for t in s['tasks']:
        current=s['versions'].get(t['key'],{}).get(s['current_versions'].get(t['key']),{})
        content_failure=current and not current.get('content_check',{}).get('usable',False)
        if not t.get('paid_recovery') and (t['status'] in ('failed','invalid_conversion','invalid_review') or (t['phase']=='critic' and (t.get('pending_suggestions',0) or (t['status']=='review_completed' and content_failure)))):return True
    return False

def model_round(run,s,*,client_factory=kimi.KimiClient,one_at_a_time=False):
    from scripts import library_pipeline as c
    run=Path(run);a=approval(run);changed=False
    for t in s['tasks']:
        current=s['versions'].get(t['key'],{}).get(s['current_versions'].get(t['key']),{})
        content_failure=current and not current.get('content_check',{}).get('usable',False)
        eligible=t['status'] in ('failed','invalid_conversion','invalid_review') or (t['phase']=='critic' and (t.get('pending_suggestions',0) or (t['status']=='review_completed' and content_failure)))
        if t.get('paid_recovery') or not eligible:continue
        # Never use a compiler-only or integrity problem as a paid trigger.
        paid.pause_guard(run);c.verify(run);rec=s['documents'][t['source_key']]
        try:
            unit=unit_record(run,s,t)
            path=run/'paid-proposals'/(t['key']+'-'+t['phase'])/'proposal.json'
            if path.exists():record=read_json(path)
            else:
                record={'kind':'kimi','phase':t['phase'],'failure':'unresolved_passage' if t.get('pending_suggestions') else 'failed','unit':unit,'attempt_limit':1,'scope_sha256':fingerprint(unit)};atomic_json(path,record)
            paid.register_scope(run,record,a,unit_verified=True)
            # Live authenticated allowance + current exact public route checked in
            # the existing client for every POST; no credentials in state/prompt.
            t['paid_stage']='dispatching_or_reconciling';s['stage']='Kimi fallback: '+s['documents'][t['source_key']]['filename']+' / '+t['phase'];c.save(run,s)
            print(s['stage'],flush=True)
            out=paid.run_kimi(run,record,Path(a.get('cloud_run',run)),a,client_factory=client_factory,observer=lambda:c.save(run,s));t['paid_recovery']=out;t['paid_stage']=out['status']
            if out.get('candidate_tex'):
                if sha(out['candidate_tex'])!=out['candidate_sha256']:raise kimi.IntegrityError('Recovered candidate changed')
                text=Path(out['candidate_tex']).read_text();version=c.compile_version(run,s,t,text,'kimi-'+t['phase'])
                label='kimi-'+t['phase'];s['versions'].setdefault(t['key'],{})[label]=version
                if version['content_check']['usable']:
                    s['current_versions'][t['key']]=label;out['selection']='selected_content_checked_not_mathematically_certified';changed=True
                    if t['phase']=='convert':
                        t['local_outcome_before_recovery']=t['status'];t['status']='conversion_completed'
                        for critic in s['tasks']:
                            if critic['key']==t['key'] and critic['phase']=='critic' and not any(call['parent']==critic['id'] for call in s['calls']):critic['status']='pending'
                    rec['needs_republication']=True
                else:out['selection']='retained_unselected_content_flags'
        except c.runtime.StopRun:raise
        except (kimi.IntegrityError,kimi.IdentityError):raise
        except Exception as exc:t['paid_recovery']={'status':'blocked_or_failed','diagnostic':type(exc).__name__+': '+str(exc)}
        c.save(run,s)
        if one_at_a_time:break
    return changed

def adopt_direct_mathpix(run,s,sid):
    """Skip a rewrite only when raw TeX exactly covers a complete planned unit."""
    from scripts import library_pipeline as c
    run=Path(run);rec=s['documents'][sid];material=rec.get('mathpix_material',{});direct=material.get('direct_tex')
    if not direct or not direct['dependency_check']['complete_content_dependencies']:return
    expected={b['id'] for p in material['pages'] for b in p['blocks']}
    for key in rec['units']:
        u=s['source_units'][key]
        if set(u['blocks'])!=expected or u['physical_pages']!=direct['pages']:continue
        if sha(direct['path'])!=direct['sha256']:raise kimi.IntegrityError('Saved direct TeX changed')
        text=Path(direct['path']).read_text();original=text;source=Path(direct['path']).parent
        for ref in book_completion.image_references(text):
            matches=[a for a,path in u['assets'].items() if Path(path).name==Path(ref).name]
            if len(matches)==1:text=text.replace('{'+ref+'}','{'+matches[0]+'}')
        # Other source includes/macros remain available without running TeX.
        for file in source.rglob('*'):
            if file.is_file():u['assets'].setdefault(str(file.relative_to(source)),str(file))
        atomic_json(run/'inputs'/key/'unit.json',u);s['derived_inputs']['inputs/'+key+'/unit.json']=sha(run/'inputs'/key/'unit.json')
        t=next(t for t in s['tasks'] if t['key']==key and t['phase']=='convert');version=c.compile_version(run,s,t,text,'mathpix-direct')
        (run/version['path']).with_name('portable-assets.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),text.splitlines(True))))
        if not version['content_check']['usable']:continue
        s['versions'].setdefault(key,{})['convert']=version;s['current_versions'][key]='convert';t.update(status='conversion_completed',conversion_origin='Mathpix direct TeX; no local rewriting request',reused_provider_job=material['raw_folder']);c.review_images(run,s,t)
