#!/usr/bin/env python3
"""Bounded linked comparison/paper pilot, reusing existing extraction and GLM scheduler."""
import argparse,copy,csv,hashlib,html,json,os,re,shlex,shutil,subprocess,sys,tarfile,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import extraction_comparison as base
from probe import extraction_followup as contract,book_completion as scope,followup_lifecycle as lifecycle
from probe.common import read_json,atomic_json,sha,writer_lock
from probe.experiment import InputGuard,verify_seal
runtime=base.runtime;books=base.books;collection=base.collection;focused=base.focused;concurrent=base.concurrent
PARENT=ROOT/'runs/extraction-comparison-20261105T185601Z-layout'
POINTER=ROOT/'results/extraction-followup-current.json';SESSION='pdf-extraction-followup';TERMINAL='finite_followup_finished'
CF='original-21debf82bc2c0a3d';SP='original-185f783748bb248e';PV='original-547334b059504dcb';IG='original-dcbf009549ec6318'

def save(run,s):
    if s.get('lifecycle_version'):
        s['allowance_accounting']=lifecycle.allowance(read_json(run/'plan.json'),s)
    runtime.save(run,s)
    atomic_json(run/'progress.json',{'at':runtime.now(),'run':str(run),'status':s['status'],'stage':s.get('stage'),'diagnostic':s.get('diagnostic'),
        'extraction':{a:{k:v for k,v in row.items() if k!='pages'}|{'page_counts':{status:sum(p['status']==status for p in row.get('pages',{}).values()) for status in set(p['status'] for p in row.get('pages',{}).values())}} for a,row in s.get('extraction',{}).items()},
        'tasks':[{k:t.get(k) for k in ('id','status','call')} for t in s['tasks']],
        'calls':[{'id':c['id'],'task':c['parent'],'status':c['status'],'seconds':c.get('elapsed_seconds'),'usage':c.get('metadata',{}).get('usage')} for c in s['calls']],
        'historical_consumed_calls':15,'allowance_accounting':s.get('allowance_accounting'),'maximum_new_primary_requests':20,'maximum_new_syntax_requests':10,'log':str(run/'terminal.log'),'inspection':s.get('inspection')})

def verify(run):
    binding=read_json(run/'binding.json');s=read_json(run/'state.json')
    if binding['code']!=base.code_binding() or sha(run/'plan.json')!=binding['plan_sha256']:raise runtime.Fatal('Frozen follow-up code/plan changed')
    InputGuard(binding['files']).check()
    if [focused.definition(t) for t in s['tasks']]!=read_json(run/'plan.json')['tasks']:raise runtime.Fatal('Task identity changed')
    for c in s['calls']:
        if c.get('seal'):verify_seal(run/'calls'/c['id'],c['seal'])
    for vs in s['versions'].values():
        for v in vs.values():
            if sha(run/v['path'])!=v['sha256']:raise runtime.Fatal('Saved version changed')
    for p,h in s.get('derived_inputs',{}).items():
        if sha(run/p)!=h:raise runtime.Fatal('Derived input changed')
    if s.get('lifecycle_version'):
        plan=read_json(run/'plan.json');lifecycle.allowance(plan,s);lifecycle.verify_sources(run,s,plan)
        if not s['extraction_done'] or s['glm_qualified']:raise runtime.Fatal('Extraction/gate state changed')
    return s

def prepare():
    import fitz
    from probe.focused_recovery import secondary_assessment
    if POINTER.exists():raise runtime.Fatal('Preparation exists; use status/resume')
    if not all(books.speed.idle(p) for p in (ROOT,ROOT/'runs',PARENT)):raise runtime.Fatal('Writer active')
    with writer_lock(ROOT),writer_lock(ROOT/'runs'):
        parent=read_json(PARENT/'state.json');oldplan=read_json(PARENT/'plan.json')
        if parent['status']!=base.TERMINAL or any(c['status']=='in_progress' for c in parent['calls']):raise runtime.Fatal('Parent unsettled')
        run=ROOT/'runs'/('extraction-followup-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));run.mkdir()
        docs=copy.deepcopy(oldplan['documents']);workloads={'glm_ocr':[[d['source_id'],p] for d in docs for p in d['physical_pages']],'mineru_pro':[]}
        shutil.copytree(PARENT/'sources',run/'sources');shutil.copytree(PARENT/'evaluation',run/'historical-evaluation')
        inventory=read_json(ROOT/'runs/originals-batch-20261101T212602Z-ab2d41/collection.json')['documents']
        for d in docs:
            if sha(d['original'])!=d['sha256'] or not any(i['source_id']==d['source_id'] and i['sha256']==d['sha256'] for i in inventory):raise runtime.Fatal('Source/inventory mismatch')
            if d['source_id'] not in (CF,SP,PV):continue
            directory=run/'sources'/d['source_id'];pdf=fitz.open(d['original']);rows={p['physical_pdf_page']:p for p in d['pages']};secondary=[]
            for n,page in enumerate(pdf,1):
                if n not in rows:
                    image=directory/f'page-{n:03}.png';pix=page.get_pixmap(matrix=fitz.Matrix(200/72,200/72),alpha=False);pix.save(image)
                    rows[n]={'physical_pdf_page':n,'image':str(image.relative_to(run)),'sha256':sha(image),'dpi':200,'width':pix.width,'height':pix.height,'printed_label_status':'requires source check','verified_blank':min(pix.samples)>=254}
                secondary.append({'physical_pdf_page':n,'text':page.get_text(sort=True)})
            d['pages']=[rows[n] for n in sorted(rows)];d['physical_pages']=list(range(1,len(pdf)+1))
            quality=secondary_assessment(secondary);quality['supplied_pages']=[] if d['source_id']==CF else quality['pages'];atomic_json(directory/'secondary-assessment.json',quality)
            workloads['mineru_pro'] += [[d['source_id'],n] for n in d['physical_pages']]
        # Preserve selected complete Pro page results and their identities, no model calls.
        reuse={};reuse_records=[]
        for sid,n in workloads['mineru_pro']:
            ident=f'{sid}-p{n}';prior=parent['extraction']['mineru_pro']['pages'].get(ident)
            if not prior:continue
            d=next(d for d in docs if d['source_id']==sid);page=next(p for p in d['pages'] if p['physical_pdf_page']==n)
            if prior['status']!='completed' or prior['image_sha256']!=page['sha256']:raise runtime.Fatal('Incompatible reuse identity')
            source=PARENT/'arms/mineru_pro';target=run/'arms/mineru_pro'
            for entry in prior['outputs']:
                p=source/entry['path']
                if sha(p)!=entry['sha256']:raise runtime.Fatal('Reusable output corrupt')
            shutil.copytree(source/'pages'/ident,target/'pages'/ident)
            reuse[ident]=copy.deepcopy(prior);reuse_records.append({'page':ident,'parent':str(PARENT),'outputs':prior['outputs']})
        atomic_json(run/'arms/mineru_pro/state.json',{'status':'prepared','pages':reuse})
        s={k:copy.deepcopy(parent[k]) for k in ('chapter_contract','timing_policy','execution_limits','compiler_environment','concurrency_policy')}
        s.update(status='prepared',created_at=runtime.now(),suite_protocol='extraction-comparison-v1',first_dispatch=None,calls=[],tasks=[],versions={},current_versions={},accuracy={},accuracy_records={},source_units={},selection_ledger=[],connection_failures=0,active_stage=1,stages={'1':{}},production_stage={'task_ids':[]},documents={},resource_phase='not_started',launches=[],derived_inputs={},syntax_lineages={},extraction={},readiness_done=True,remote='/home/mdi/projects/pdf-to-latex-comparisons/'+run.name,remote_models=parent['remote_models'],runtime_image=parent['runtime_image'],models_downloaded=True,low_supported=parent['low_supported'])
        shutil.copytree(PARENT/s['compiler_environment']['path'],run/s['compiler_environment']['path'])
        for name in ('effort-support-offline.json','baseline-runtime-verified.json','runtime-prepared.json'):shutil.copyfile(PARENT/name,run/name)
        assignments=[{'key':'matched-cf','source_id':CF,'type':'matched','arm':'glm_ocr','index':0}, {'key':'matched-control','source_id':IG,'type':'matched','arm':'glm_ocr','index':1}]
        for sid,number in ((CF,3),(SP,5),(PV,1)):
            for index in range(number):assignments.append({'key':sid+'-whole-'+str(index+1),'source_id':sid,'type':'paper','arm':'mineru_pro','index':index,'reuse':sid==CF and index==1})
        for a in assignments:
            key=a['key'];d=next(d for d in docs if d['source_id']==a['source_id']);s['documents'][key]=dict(d,source_sha256=d['sha256'],status='pending_extraction');s['source_units'][key]={'source_key':key,'section':{'title':key,'blocks':[]},'assignment':a}
            if a.get('reuse'):continue
            for phase,effort,dep in [('convert','high',None),('critic','max',key+'/convert'),('syntax','low',None)]:
                s['tasks'].append({'id':key+'/'+phase,'key':key,'source_key':key,'phase':phase,'reasoning_effort':effort,'arm':'syntax' if phase=='syntax' else 'primary','depends_on':dep,'status':'dormant' if phase=='syntax' else 'pending'})
        plan={'status':'frozen','parent':str(PARENT),'parent_binding_sha256':sha(PARENT/'binding.json'),'parent_state_sha256':sha(PARENT/'state.json'),'documents':docs,'workloads':workloads,'assignments':assignments,'tasks':[focused.definition(t) for t in s['tasks']],
            'qualification_pages':[[CF,5],[IG,3]],'maximum_new_primary_requests':20,'maximum_new_syntax_requests':10,'maximum_new_requests':30,'prior_calls_preserved':15,
            'settings':{'model':'glm53-regular','convert':'high','critic':'max','max_tokens':131072,'concurrency':2,'images':False},
            'boundaries':{CF:[r'Case[ \t]*13\b(?=[ \t]*[.:}*])',r'Case[ \t]*19\b(?=[ \t]*(?:[.:}*]|McNolty\b))'],SP:[r'4\.\s+The\s+Oscillatory',r'6\.\s+Analytically\s+Tractable',r'6\.4\.\s+Coulomb',r'7\.\s+Conclusion'],PV:[]},
            'scope_policy':'Entire assigned paper text once, including title, references, appendices, figures and tables. Exact structural heading boundaries, no clipping. CF middle unit reuses previous conversion/review. Blank final Spectral page preserved with source evidence.',
            'reuse':reuse_records,'glmocr_reuse':'Previous recognized text has no durable detected-region/request mapping; formulas and references absent. Re-extract pages to establish complete region accounting; preserve invalid historical results.',
            'qualification_policy':'Two page outputs and complete region ledger must pass direct source-image checks before remaining GLM-OCR dispatch. No paid calls; no production continuation.'}
        s['production_stage']['task_ids']=[t['id'] for t in s['tasks']];atomic_json(run/'plan.json',plan)
        atomic_json(run/'history.json',{'parent':str(PARENT),'calls':parent['calls'],'selected_versions':parent['current_versions'],'consumed_allowances':'All15 historical calls remain consumed; this separately authorised plan adds at most30, no replay.'})
        binding={'code':base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':{str(p):sha(p) for p in (run/'sources').rglob('*') if p.is_file()}}
        binding['files'].update({d['original']:d['sha256'] for d in docs});atomic_json(run/'binding.json',binding);save(run,s)
        atomic_json(POINTER,{'run':str(run)});print(run);return run

def stage_inputs(run,s,plan):
    archive=run/'peer-input.tar';atomic_json(run/'active-extraction-plan.json',plan)
    with tarfile.open(archive,'w') as tar:
        tar.add(run/'active-extraction-plan.json',arcname='plan.json');tar.add(run/'sources',arcname='sources')
        for name in ('probe/__init__.py','probe/extraction_comparison.py','probe/extraction_followup.py','scripts/extraction_followup_candidate.py'):tar.add(ROOT/name,arcname='scripts/extraction_candidate_worker.py' if name.endswith('extraction_followup_candidate.py') else name)
    base.command(run,'transfer-inputs',['scp',str(archive),base.PEER+':'+s['remote']+'/input.tar'])
    if subprocess.check_output(base.ssh('sha256sum '+shlex.quote(s['remote']+'/input.tar')),text=True).split()[0]!=sha(archive):raise runtime.Fatal('Transfer mismatch')
    base.command(run,'unpack',base.ssh('tar -xf '+shlex.quote(s['remote']+'/input.tar')+' -C '+shlex.quote(s['remote']+'/input')))

def extract_arm(run,s,arm,plan):
    stage_inputs(run,s,plan);dest=run/'arms'/arm;dest.mkdir(parents=True,exist_ok=True)
    base.command(run,'output-dir',base.ssh('mkdir -p '+shlex.quote(s['remote']+'/outputs/'+arm)))
    base.command(run,'clear-owned-pause',base.ssh('rm -f '+shlex.quote(s['remote']+'/outputs/'+arm+'/pause.json')))
    if (dest/'state.json').exists():base.command(run,'seed-reuse',['scp','-r',str(dest)+'/.',base.PEER+':'+s['remote']+'/outputs/'+arm+'/'])
    s['stage']='extraction '+arm;save(run,s)
    def observe():
        try:cp=subprocess.run(base.ssh('cat '+shlex.quote(s['remote']+'/outputs/'+arm+'/state.json')),capture_output=True,text=True,timeout=20)
        except subprocess.TimeoutExpired:return
        if cp.returncode==0:
            try:s['extraction'][arm]=json.loads(cp.stdout);save(run,s)
            except ValueError:pass
    try:base.command(run,'candidate-'+arm,base.ssh(shlex.join(base.container_args(s,arm))),observe=observe)
    except runtime.Fatal as exc:s['extraction'][arm]={'status':'failed','error':str(exc)}
    base.command(run,'collect-'+arm,['scp','-r',base.PEER+':'+s['remote']+'/outputs/'+arm+'/.',str(dest)])
    if (dest/'state.json').exists():s['extraction'][arm]=read_json(dest/'state.json')
    for row in s['extraction'][arm].get('pages',{}).values():
        for item in row.get('outputs',[]):
            if sha(dest/item['path'])!=item['sha256']:raise runtime.Fatal('Output transfer corruption')
    save(run,s)
    if s['extraction'][arm].get('status')=='paused':raise runtime.StopRun('Owned extraction drained')

def extraction(run,s):
    if s.get('extraction_done'):return
    helpers=books.speed.module();base.install_runtime(run,s)
    if any(row.get('status')=='running' for row in s.get('extraction',{}).values()):raise runtime.Fatal('Uncertain extraction; reconcile, do not replay')
    plan=read_json(run/'plan.json')
    # Existing handoff enforces helper identity, current idleness and owned deployments.
    policies={}
    for node in ('head','peer'):
        command=['docker','inspect','--format','{{json .HostConfig.RestartPolicy}}',helpers.CONTAINER]
        value=json.loads(helpers.checked(command if node=='head' else helpers.peer(shlex.join(command))))
        if value.get('Name') not in ('no','') or value.get('MaximumRetryCount',0)!=0:raise runtime.Fatal('Unsupported existing restart policy; no service action')
        policies[node]=value
    atomic_json(run/'service-restart-policy.json',policies)
    collection.resource_handoff(run,s,helpers)
    try:
        if not s.get('glm_qualification_done'):
            qualification=copy.deepcopy(plan);qualification['workloads']['glm_ocr']=plan['qualification_pages']
            extract_arm(run,s,'glm_ocr',qualification)
            s['stage']='checking two-page GLM-OCR source qualification';save(run,s)
            records=s['extraction']['glm_ocr'].get('pages',{})
            if all(records.get(f'{sid}-p{n}',{}).get('status')=='completed' for sid,n in plan['qualification_pages']):
                # Source comparison is performed by the active Codex investigator,
                # not the model under test; this is an evidence gate, no user approval.
                gate=run/'qualification/source-review.json'
                while not gate.exists():
                    if (run/'pause.json').exists():raise runtime.StopRun('Paused at qualification boundary')
                    time.sleep(5)
                review=read_json(gate)
                for sid,n in plan['qualification_pages']:
                    key=f'{sid}-p{n}';path=run/'arms/glm_ocr/pages'/key/'text.md'
                    if review['output_hashes'].get(key)!=sha(path):raise runtime.Fatal('Qualification reviewed different output')
                s['glm_qualified']=review['passed']
            else:s['glm_qualified']=False
            s['glm_qualification_done']=True;save(run,s)
        if s.get('glm_qualified') and not s.get('glm_full_done'):
            # Qualification pages are completed, hash-verified reuse. Only unsettled
            # pages are eligible in the existing candidate worker.
            state=read_json(run/'arms/glm_ocr/state.json');state['status']='prepared';atomic_json(run/'arms/glm_ocr/state.json',state)
            extract_arm(run,s,'glm_ocr',plan);s['glm_full_done']=True;save(run,s)
        if not s.get('pro_done'):
            extract_arm(run,s,'mineru_pro',plan);s['pro_done']=True;save(run,s)
        s['extraction_done']=True
    finally:
        if s.get('glm_owned_before_ocr'):
            if collection.helper_hashes(helpers)!=read_json(run/'service-helper-binding.json'):raise runtime.Fatal('Service helpers changed')
            books.book.arrange_glm(run);concurrent.capture_build(helpers,run);collection.verify_restart_configuration(run,helpers)
            for node,expected in policies.items():
                command=['docker','inspect','--format','{{json .HostConfig.RestartPolicy}}',helpers.CONTAINER]
                if json.loads(helpers.checked(command if node=='head' else helpers.peer(shlex.join(command))))!=expected:raise runtime.Fatal('Restart policy changed')
            s['resource_phase']='glm_restored';save(run,s)

def page_text(run,s,arm,sid,n,assets):
    record=s['extraction'].get(arm,{}).get('pages',{}).get(f'{sid}-p{n}')
    if not record or record['status'] not in ('completed','blank_source_preserved'):raise ValueError(f'Unavailable {arm} {sid} p{n}')
    if record['status']=='blank_source_preserved':return f'<!-- Original physical page {n}: verified blank; preserved original image. -->'
    folder=run/'arms'/arm/'pages'/f'{sid}-p{n}'
    if arm=='glm_ocr':
        if not read_json(folder/'region-accounting.json')['complete']:raise ValueError('Incomplete region accounting')
        return (folder/'text.md').read_text()
    blocks=read_json(folder/'native.json');names={}
    for i,b in enumerate(blocks):
        if b.get('type') in ('image','chart','image_block','table'):
            path=folder/f'region-{i}.png'
            if path.exists():
                name=f'assets/{sid}-p{n}-region-{i}.png';out=run/'inputs'/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,out);names[i]=name;assets.append(name)
    records,inferred=contract.pro_export(blocks,names)
    atomic_json(run/'inferred'/f'{sid}-p{n}.json',{'not_printed_source':inferred})
    return '\n\n'.join(f'<!-- physical page {n}; region {b["index"]}; kind={b["kind"]} -->\n'+b['text'] for b in records)

def prepare_downstream(run,s):
    if s.get('downstream_prepared'):return
    plan=read_json(run/'plan.json');whole={};scope_records=[]
    for sid in (CF,SP,PV):
        d=next(d for d in plan['documents'] if d['source_id']==sid);assets=[]
        try:
            chunks=[page_text(run,s,'mineru_pro',sid,n,assets) for n in d['physical_pages']]
            text='\n\n'.join(chunks);units=contract.checked_partition(text,plan['boundaries'][sid]);offset=0;spans=[]
            for n,chunk in zip(d['physical_pages'],chunks):spans.append((offset,offset+len(chunk),n));offset+=len(chunk)+2
            for u in units:u['physical_pages']=[n for a,b,n in spans if a<u['end'] and b>u['start']]
            whole[sid]=(units,assets,text)
            scope_records.append({'source_id':sid,'source_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'pages':d['physical_pages'],'units':[{k:v for k,v in u.items() if k!='text'} for u in units],'complete_partition':''.join(u['text'] for u in units)==text})
        except ValueError as exc:whole[sid]=str(exc)
    parent=read_json(PARENT/'state.json')
    for a in plan['assignments']:
        key=a['key'];sid=a['source_id'];directory=run/'inputs'/key;directory.mkdir(parents=True,exist_ok=True)
        try:
            if a['type']=='matched':
                if not s.get('glm_qualified'):raise ValueError('GLM-OCR qualification failed')
                old=read_json(PARENT/'plan.json')['downstream'][a['index']];assets=[];pages=old['physical_pages'];text='\n\n'.join(page_text(run,s,'glm_ocr',sid,n,assets) for n in pages)
                primary,_=base.passage(text,a['index']);title=old['scope'];context='Scope is only '+title+'. Earlier/later material outside the located boundaries is not assigned output.'
                parentkey='glm_ocr-assignment-'+str(a['index']+1);assets=read_json(PARENT/'inputs'/parentkey/'assets.json')
                for ref in assets:
                    dest=run/'inputs'/ref;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PARENT/'inputs'/ref,dest)
            else:
                if isinstance(whole[sid],str):raise ValueError(whole[sid])
                units,assets,text=whole[sid];u=units[a['index']];primary=u['text'];pages=u['physical_pages'];title=f'{s["documents"][key]["filename"]} — complete structural unit {a["index"]+1}/{len(units)}'
                context='Context only: earlier definitions may be used but must not be emitted again.\n'+('' if a['index']==0 else units[0]['text'])
            if len(primary.encode())>170000:raise ValueError('Frozen unit exceeds conservative output-planning admission; no clipping/splitting')
            block={'id':key+'-scope','kind':'text','tex':primary,'native':{'content':primary},'page':{'original_physical_page':pages[0]},'assets':assets}
            native={'key':key,'title':title,'blocks':[block]};atomic_json(directory/'native.json',native);atomic_json(directory/'assets.json',assets)
            sec=scope.target(native,[block['id']],title=title);sec['physical_pages']=pages;s['source_units'][key].update(section=sec,context=context)
            q=read_json(run/'sources'/sid/'secondary-assessment.json');atomic_json(run/'quality'/(key+'.json'),{'pages':[p for p in q['supplied_pages'] if p['physical_pdf_page'] in pages]})
            atomic_json(directory/'scope.json',{'title':title,'pages':pages,'primary_sha256':hashlib.sha256(primary.encode()).hexdigest(),'assets':assets,'expected_upper_output_tokens':int(len(primary.encode())*.9),'all_assigned_material_required':True})
            if a.get('reuse'):
                oldkey='mineru_pro-assignment-1';label=parent['current_versions'][oldkey]
                # Original source identity, complete Cases13–18, pinned engine and High/Max
                # settings match. Preserve original version/build identities and requests.
                s['versions'][key]=copy.deepcopy(parent['versions'][oldkey])
                for v in s['versions'][key].values():
                    source=PARENT/v['path'];target=run/v['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
                    if sha(target)!=v['sha256']:raise runtime.Fatal('Reused draft corrupt')
                s['current_versions'][key]=label;atomic_json(directory/'reused-version.json',{'parent':str(PARENT),'unit':oldkey,'calls':['call-007','call-010'],'scope':'Complete Cases13–18, same source/model/High-Max settings; original source request and builds retained at parent','selected_sha256':s['versions'][key][label]['sha256']})
        except (ValueError,KeyError,FileNotFoundError) as exc:
            s['source_units'][key]['preparation_error']=str(exc)
            for t in s['tasks']:
                if t['key']==key:t.update(status='unavailable_source_scope',error=str(exc))
    atomic_json(run/'scope-coverage.json',scope_records)
    for folder in ('inputs','quality'):
        for p in (run/folder).rglob('*'):
            if p.is_file():s['derived_inputs'][str(p.relative_to(run))]=sha(p)
    s['downstream_prepared']=True;save(run,s)

def before(run,s,t,body):
    if s.get('lifecycle_version'):
        lifecycle.allowance(read_json(run/'plan.json'),s)
        lifecycle.verify_sources(run,s,read_json(run/'plan.json'))
    focused.before(run,s,t,body)

def finish(run,s,t,answer,call):
    focused.finish(run,s,t,answer,call)
    key=t['key'];label=s['current_versions'].get(key)
    if label and s.get('lifecycle_version'):
        native=read_json(run/'inputs'/key/'native.json');v=s['versions'][key][label]
        check=lifecycle.coverage((run/v['path']).read_text(),native,s['source_units'][key]['section']['blocks'])
        t['coverage_check']=check;v['coverage_check']=check
        atomic_json(run/'coverage'/key/(label+'.json'),check)
        for row in s['selection_ledger']:
            if row['unit']==key:row.update(coverage_check=check,possible_content_gaps=check['coverage_status']=='omission_risk')
    save(run,s)

def qualify_assembly(run,s):
    marker=run/'assembly-qualification/result.json'
    if marker.exists():
        if not read_json(marker)['passed']:raise runtime.Fatal('Assembly qualification failed; preserve diagnostics')
        return
    # Real compile with image, duplicate macro names, cross-unit references,
    # bibliography keys and multi-paragraph editorial annotation.
    asset=next((run/'inputs/assets').glob('*.png'))
    one=r"\documentclass{article}\usepackage{amsmath,graphicx,xcolor}\newcommand{\localword}{First}\begin{document}\section{First}\localword.\label{shared}\begin{equation}x^2=1\label{cross}\end{equation}\includegraphics[width=1cm]{assets/fixture.png}\cite{key}\begin{thebibliography}{9}\bibitem{key}First reference.\end{thebibliography}\end{document}"
    two=r"\documentclass{article}\usepackage{amsmath,graphicx,xcolor}\newcommand{\localword}{Second}\begin{document}\section{Second}\label{shared}\localword. Equation~\eqref{cross}; local section~\ref{shared}. {\color{blue}Editorial note.\par A second paragraph retains content.}\cite{key}\begin{thebibliography}{9}\bibitem{key}Second reference.\end{thebibliography}\end{document}"
    master,parts,log=lifecycle.assemble_documents([('u1',one),('u2',two)])
    folder=run/'assembly-qualification';folder.mkdir(parents=True,exist_ok=True);assets={'assets/fixture.png':asset}
    for key,body in parts.items():
        path=folder/(key+'.tex');path.write_text(body);assets['parts/'+key+'.tex']=path
    result=collection.compiler_environment.compile_saved(run,s,ROOT,master,folder/'build',assets)
    passed=result['status']=='passed' and not log['unresolved_references']
    atomic_json(marker,{'passed':passed,'compiler':result,'assembly':log,'code':base.code_binding(),'source':'synthetic fixtures, actual isolated compiler; no model request'})
    if not passed:raise runtime.Fatal('Real multi-unit assembly qualification failed')

def assemble(run,s):
    if s.get('assembled'):return
    plan=read_json(run/'plan.json');results=[]
    for sid in (CF,SP,PV):
        dest=run/'deliveries'/sid;dest.mkdir(parents=True,exist_ok=True)
        units=[];missing=[];records=[];expected=set();assets={};log={}
        for a in [a for a in plan['assignments'] if a['type']=='paper' and a['source_id']==sid]:
            key=a['key'];native=read_json(run/'inputs'/key/'native.json')
            for b in native['blocks']:
                if b['kind'] in ('image','chart'):expected.update(b['assets'])
            label=s['current_versions'].get(key)
            if not label:missing.append(key);continue
            v=s['versions'][key][label];text=(run/v['path']).read_text()
            for name,item in s['versions'][key].items():shutil.copyfile(run/item['path'],dest/(key+'-'+name+'.tex'))
            check=lifecycle.coverage(text,native,s['source_units'][key]['section']['blocks'])
            records.append({'unit':key,'selected':label,'sha256':v['sha256'],'coverage':check,'standalone_build':v.get('compilation'),'parent_build_provenance':v.get('parent_build_provenance')})
            units.append((key,text))
        try:
            if not units:raise ValueError('No usable units')
            master,parts,log=lifecycle.assemble_documents(units)
            for key,body in parts.items():
                path=dest/'parts'/(key+'.tex');path.parent.mkdir(exist_ok=True);path.write_text(body);assets['parts/'+key+'.tex']=path
            emitted=set(scope.image_references('\n'.join(parts.values())))
            missing_assets=sorted(expected-emitted)
            for ref in sorted(expected|emitted):
                path=run/'inputs'/ref
                if not path.is_file():missing.append('missing source asset '+ref);continue
                target=dest/ref;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target);assets[ref]=target
            (dest/'master.tex').write_text(master);atomic_json(dest/'technical-changes.json',log)
            result=collection.compiler_environment.compile_saved(run,s,ROOT,master,dest/'build',assets)
            pdfs=sorted((dest/'build').glob('attempt-*/document.pdf'))
            if result['status'].startswith('passed') and pdfs:shutil.copyfile(pdfs[-1],dest/'reading.pdf')
        except (ValueError,FileNotFoundError) as exc:
            result={'status':'assembly_unresolved','diagnostic':str(exc)};missing_assets=None
        row={'source_id':sid,'missing_units':missing,'missing_expected_figures':missing_assets,'versions':records,'compilation':result,'unresolved_references':log.get('unresolved_references',[]) if 'log' in locals() else [],'assembly_completed':result.get('status')!='assembly_unresolved',
             'coverage':'omission_risk' if missing or missing_assets or any(v['coverage']['coverage_status']=='omission_risk' for v in records) else 'requires_source_review',
             'mathematical_verification':'Designated checks only, not whole-paper verification'}
        atomic_json(dest/'delivery.json',row);results.append(row)
    atomic_json(run/'delivery-index.json',results);s['assembled']=True;save(run,s)


def bundle(run,s):
    metrics=[]
    for c in s['calls']:metrics.append({'call':c['id'],'task':c['parent'],'status':c['status'],'seconds':c.get('elapsed_seconds'),'usage':c.get('metadata',{}).get('usage')})
    atomic_json(run/'request-metrics.json',metrics)
    text=['# Finite extraction follow-up',f'Run: {run}',f'Status: {s["status"]}',
          'New authorisation: corrected GLM-OCR32-page comparison plus three complete Pro papers. No production queue or paid calls. Historical15 calls retained; at most20 new primary and10 syntax requests. No conversion retries or recursive splitting.',
          'Review qualification/source-review.json, scope-coverage.json, deliveries/, accuracy/, region-accounting.json and request-metrics.json. Compilation, model review, coverage and direct source verification are distinct. Inferred Pro chart data are retained separately under inferred/, never supplied as printed tables.',
          'Decision: retain baseline and compare only qualified, complete scopes. Do not infer fidelity from completion/builds. Final manual source audit may remain incomplete; the report makes no full mathematical verification claim.',
          '## Task outcomes']+[t['id']+': '+t['status'] for t in s['tasks']]
    (run/'START-HERE.md').write_text('\n\n'.join(text)+'\n')
    path=ROOT/'results/inspection'/('extraction-followup-'+run.name+'-'+str(time.time_ns())+'.zip');manifest=[];omitted=[]
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for p in run.rglob('*'):
            if not p.is_file() or p.is_symlink():continue
            rel=p.relative_to(run)
            if any(x in rel.parts for x in ('host-operations','compiler-environment','layout_vis')) or p.suffix in ('.tar','.jsonl','.ndjson') or 'wire' in p.name or 'reasoning' in p.name or p.stat().st_size>8*1024**2:
                omitted.append({'path':str(p),'bytes':p.stat().st_size});continue
            z.write(p,str(rel));manifest.append({'path':str(rel),'sha256':sha(p),'bytes':p.stat().st_size})
        z.writestr('OMITTED.json',json.dumps(omitted,indent=2));z.writestr('FILE-HASHES.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(path) as z:
        if z.testzip():raise runtime.Fatal('Archive CRC failed')
        for row in manifest:
            if hashlib.sha256(z.read(row['path'])).hexdigest()!=row['sha256']:raise runtime.Fatal('Archive hash failed')
    s['inspection']=str(path);save(run,s);return path

def worker(run):
    with (run/'terminal.log').open('a',buffering=1) as log:
        os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
        with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):
            s=verify(run)
            if s['status']==TERMINAL:return
            try:
                s.update(status='running',diagnostic=None);s['launches'].append({'at':runtime.now(),'pid':os.getpid()});save(run,s)
                runtime.check_other_jobs();books.qualify_compiler(run,s)
                result=collection.tex_compile.compile_document(r'\documentclass{article}\usepackage{amsmath}\begin{document}$x^2$\end{document}',run/'compiler-preflight'/str(time.time_ns()),image=s['compiler_environment']['image'],passes=2)
                if not result['compilation_claim']:raise runtime.Fatal('Compiler preflight failed')
                if s.get('lifecycle_version'):
                    qualify_assembly(run,s)
                else:extraction(run,s)
                base.pause(run);prepare_downstream(run,s)
                helpers=books.speed.module();books.book.arrange_glm(run,check_only=True);concurrent.capture_build(helpers,run)
                effort=books.speed.effort_check(run,helpers)
                if effort.get('status')!='supported':raise runtime.Fatal('Effort mapping not verified')
                s['low_supported']=effort['low_supported'];sample=books.speed.sampler(run,s,helpers);books.speed.healthy(sample(0))
                for c in s['calls']:
                    t=next(t for t in s['tasks'] if t['id']==c['parent'])
                    if t.get('settled_call')==c['id']:continue
                    folder=run/'calls'/c['id']
                    if not (folder/'manifest.json').exists():raise runtime.Fatal('Uncertain prior model request')
                    verify_seal(folder);c.update(read_json(folder/'outcome.json'));c['seal']=sha(folder/'manifest.json');finish(run,s,t,(folder/'content.txt').read_text() if c['status']=='completed_response' else None,c)
                s['stage']='finite matched and complete-paper conversion/review';save(run,s);active=[]
                def changed():
                    focused.adjust(run,s);active[:]=[t for t in s['tasks'] if t['status'] not in ('dormant','not_needed')];save(run,s)
                changed();concurrent.coordinate(run,s,active,body_for=focused.body_for,finish=finish,verify=lambda:verify(run),sample=sample,changed=changed,fixed_level=2,before_reserve=lambda state,t,b:before(run,state,t,b))
                if any(t['status'] in ('pending','running','dormant') for t in s['tasks']):raise runtime.Fatal('Unsettled finite tasks')
                assemble(run,s);s.update(status=TERMINAL,finished_at=runtime.now(),stage='finished; no next queue')
            except runtime.StopRun as exc:s.update(status='stopped_error' if isinstance(exc,runtime.Fatal) else 'paused',diagnostic=str(exc))
            except BaseException as exc:s.update(status='stopped_error',diagnostic=str(exc),traceback=concurrent.exception_trace(run,exc,'Finite extraction follow-up'))
            finally:save(run,s);bundle(run,s)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','continue','qualify','run','resume','worker','status','pause','bundle'));p.add_argument('--run',type=Path);a=p.parse_args()
    if a.action=='prepare':prepare();return
    if a.action=='continue':
        a.run=lifecycle.migrate(sys.modules[__name__]);a.action='resume'
    if a.action=='run' and not POINTER.exists():prepare()
    run=(a.run or Path(read_json(POINTER)['run'])).resolve()
    if a.action=='status':print(json.dumps(read_json(run/'progress.json'),indent=2));return
    if a.action=='pause':
        atomic_json(run/'pause.json',{'at':runtime.now()});s=read_json(run/'state.json')
        for arm,row in s.get('extraction',{}).items():
            if row.get('status')=='running':base.command(run,'remote-pause',base.ssh('touch '+shlex.quote(s['remote']+'/outputs/'+arm+'/pause.json')))
        print('Drain requested; no in-flight cancellation');return
    if a.action=='worker':worker(run);return
    if a.action=='qualify':
        with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):qualify_assembly(run,verify(run))
        return
    s=verify(run)
    if a.action=='bundle':
        with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):print(bundle(run,s))
        return
    if s['status']==TERMINAL:print('Finished; zero new requests or host operations');return
    if not all(books.speed.idle(p) for p in (ROOT,ROOT/'runs',run)):raise runtime.Fatal('Existing writer')
    if any(c['status']=='in_progress' for c in s['calls']):raise runtime.Fatal('Uncertain dispatch; reconcile first')
    cp=subprocess.run(['tmux','has-session','-t',SESSION],capture_output=True,text=True)
    if cp.returncode!=1:raise runtime.Fatal('Worker exists or tmux unavailable')
    collection.normal_checks(run);(run/'pause.json').unlink(missing_ok=True)
    command=shlex.join([str(base.PYTHON),'-B','-u',str(Path(__file__).resolve()),'worker','--run',str(run)])
    subprocess.run(['tmux','new-session','-d','-s',SESSION,'cd '+shlex.quote(str(ROOT))+' && exec '+command],check=True);print('Persistent launch requested:',run)
if __name__=='__main__':main()
