#!/usr/bin/env python3
"""Finite, separately budgeted Mathpix supplement; no GLM dispatch capability."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from datetime import datetime,timezone
from urllib.parse import urlencode
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe import mathpix_experiment as api, tex_compile
from probe.common import atomic_json,read_json,sha,writer_lock,files_manifest
POINTER=ROOT/'results/mathpix-comparison-current.json'
LEDGER=ROOT/'results/mathpix-accounting'
KEY=Path('/home/mdi/.config/pdf-to-latex/mathpix.json')
SESSION='pdf-mathpix-comparison'
CODE=('scripts/mathpix_comparison.py','probe/mathpix_experiment.py','probe/common.py','probe/tex_compile.py','probe/extraction_comparison_report.py')
FINISHED='mathpix_finished'


def progress(run,state):
    atomic_json(run/'state.json',state)
    atomic_json(run/'progress.json',{'at':api.now(),'run':str(run),'status':state['status'],
        'jobs':state['jobs'],'diagnostic':state.get('diagnostic'),'budget_cap_usd':1.0,
        'spending':state.get('spending'),'log':str(run/'terminal.log'),'inspection':state.get('inspection')})


def prepare():
    if POINTER.exists():return Path(read_json(POINTER)['run'])
    import fitz
    parent=Path(read_json(ROOT/'results/extraction-comparison-current.json')['run'])
    source=parent/('plan.json' if (parent/'plan.json').exists() else 'plan-draft.json')
    plan=read_json(source)
    unique={(d['sha256'],p) for d in plan['documents'] for p in d['physical_pages']}
    count=sum(len(d['physical_pages']) for d in plan['documents'])
    if len(unique)!=count or not 1<=count<=36:raise ValueError('Mathpix scope exceeds unique-page authority')
    run=ROOT/'runs'/('mathpix-comparison-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    run.mkdir();jobs=[]
    for d in plan['documents']:
        if sha(d['original'])!=d['sha256']:raise ValueError('Original source hash changed')
        folder=run/'inputs'/d['source_id'];folder.mkdir(parents=True)
        path=folder/'subset.pdf';mapping=[]
        with fitz.open(d['original']) as original,fitz.open() as subset:
            for index,number in enumerate(d['physical_pages'],1):
                subset.insert_pdf(original,from_page=number-1,to_page=number-1)
                mapping.append({'subset_page':index,'original_physical_page':number,
                                'printed_label_evidence':d['pages'][index-1]['printed_label_evidence']})
            subset.set_metadata({});subset.save(path,garbage=4,deflate=True)
        with fitz.open(path) as subset,fitz.open(d['original']) as original:
            if len(subset)!=len(mapping) or subset.embfile_count():raise ValueError('Unexpected subset contents')
            for row in mapping:
                a=original[row['original_physical_page']-1].get_pixmap(matrix=fitz.Matrix(200/72,200/72),alpha=False)
                b=subset[row['subset_page']-1].get_pixmap(matrix=fitz.Matrix(200/72,200/72),alpha=False)
                if (a.width,a.height,a.samples)!=(b.width,b.height,b.samples):raise ValueError('Subset changed rendered page')
                row['pixel_sha256']=hashlib.sha256(a.samples).hexdigest();row['render_pixel_match']=True
        atomic_json(folder/'page-map.json',mapping)
        jobs.append({'source_id':d['source_id'],'filename':d['filename'],'original':d['original'],
            'sha256':d['sha256'],'physical_pages':d['physical_pages'],'subset':str(path.relative_to(run)),
            'subset_sha256':sha(path),'page_map':mapping,
            'evidence_images':[{'physical_page':p['physical_pdf_page'],'path':str(parent/p['image']),'sha256':p['sha256']} for p in d['pages']]})
    compiler_parent=Path(read_json(ROOT/'results/focused-recovery-current.json')['run'])
    compiler=read_json(compiler_parent/'state.json')['compiler_environment']['image']
    manifest={'parent':str(parent),'parent_snapshot_sha256':sha(source),'budget_id':parent.name+'/mathpix-supplement-v1',
              'jobs':jobs,'unique_pages':count,'options':api.OPTIONS,'cap_microusd':api.CAP_MICROUSD,
              'price_microusd_per_page':api.RATE_MICROUSD,'estimated_total_microusd':count*api.RATE_MICROUSD,
              'pricing_checked_at':api.now(),'pricing_source':'https://website.mathpix.com/pricing/api',
              'api_docs':'https://docs.mathpix.com/reference/post-v3-pdf',
              'privacy_source':'https://docs.mathpix.com/concepts/data-retention',
              'privacy':'improve_mathpix=false requested; account-level policy may override. Source deleted after processing; page images/text have separate retention. Outputs downloaded locally.',
              'compiler_image':compiler,'additional_glm_requests':0,'submission_attempts_per_identity':1}
    atomic_json(run/'plan.json',manifest)
    shutil.copyfile(parent/'evaluation/critical-passages.json',run/'critical-passages.json')
    atomic_json(run/'binding.json',{'code':{p:sha(ROOT/p) for p in CODE},'plan_sha256':sha(run/'plan.json'),
        'inputs':files_manifest(run/'inputs'),'critical_sha256':sha(run/'critical-passages.json')})
    progress(run,{'status':'prepared','jobs':{},'created_at':api.now()})
    atomic_json(POINTER,{'run':str(run),'parent':str(parent)});print(run);return run


def verify(run):
    binding=read_json(run/'binding.json');plan=read_json(run/'plan.json')
    if binding['code']!={p:sha(ROOT/p) for p in CODE} or binding['plan_sha256']!=sha(run/'plan.json'):
        raise ValueError('Mathpix code/plan binding changed; no paid dispatch')
    if plan['options']!=api.OPTIONS or plan['cap_microusd']!=api.CAP_MICROUSD or plan['price_microusd_per_page']!=api.RATE_MICROUSD:
        raise ValueError('Mathpix options/budget changed')
    for f in binding['inputs']:
        if sha(run/'inputs'/f['path'])!=f['sha256']:raise ValueError('Frozen subset changed')
    for j in plan['jobs']:
        if sha(j['original'])!=j['sha256']:raise ValueError('Original identity changed')
    return plan


def usage(run,client,label):
    current=datetime.now(timezone.utc);begin=current.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    query=urlencode({'from_date':begin.isoformat(),'to_date':current.isoformat(),'group_by':'usage_type','timespan':'month'})
    result=client.get_json('ocr-usage?'+query)
    record={'retrieved_at':api.now(),'query':query,'provider_response':result,
            'interpretation':'Provider-reported consumption may lag and may include other applications. Credits and actual invoice cost are not established by these counters.'}
    atomic_json(run/'usage'/(label+'-'+str(time.time_ns())+'.json'),record)
    return record


def ledger_read():return read_json(LEDGER/'ledger.json') if (LEDGER/'ledger.json').exists() else {'version':1,'keys':{},'budgets':{}}


def submit_once(run,plan,job,client):
    identity=api.job_identity(job)
    with writer_lock(LEDGER):
        ledger=ledger_read();record,fresh=api.reserve(ledger,client.key_id,plan['budget_id'],job,run,external_budget=plan.get('external_budget'))
        if not fresh:return dict(record)
        atomic_json(LEDGER/'ledger.json',ledger)  # durable before potentially billable POST
        begin=time.monotonic()
        try:
            identifier,response=client.submit((run/job['subset']).read_bytes(),record['submission_filename'])
            record.update(pdf_id=identifier,status='submitted',submitted_at=api.now(),submission_seconds=time.monotonic()-begin)
            atomic_json(LEDGER/'ledger.json',ledger)  # persist ID before any optional output write
            atomic_json(run/'jobs'/identity/'submission.json',response)
        except Exception as exc:
            record.update(status='uncertain_submission',diagnostic=client.redact(str(exc)),submission_seconds=time.monotonic()-begin)
            if isinstance(exc,api.APIError) and exc.status in (400,401,403,429):record['shared_http_failure']=exc.status
            atomic_json(LEDGER/'ledger.json',ledger)
        return dict(record)


def update_ledger(client,identity,updates):
    with writer_lock(LEDGER):
        ledger=ledger_read();record=ledger['keys'][client.key_id]['jobs'][identity];record.update(updates)
        atomic_json(LEDGER/'ledger.json',ledger)


def compile_direct(run,folder,image,entries):
    tex=[name for name,data in entries.items() if name.endswith('.tex') and b'\\documentclass' in data]
    if len(tex)!=1:return {'status':'ambiguous_or_missing_master','candidates':tex,'content_fidelity':'not established'}
    build=folder/'direct-compile';source=build/'source';output=build/'build'
    if (build/'result.json').exists():return read_json(build/'result.json')
    source.mkdir(parents=True,exist_ok=True);output.mkdir(exist_ok=True)
    for name,data in entries.items():
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    main=Path(tex[0]);selected=source/main
    if main.name!='document.tex':shutil.copyfile(selected,selected.parent/'document.tex')
    command=tex_compile.command(image,build)
    command[command.index('--workdir')+1]='/source'+('/'+str(main.parent) if str(main.parent)!='.' else '')
    atomic_json(build/'command.json',command)
    logs=[];code=None;begin=time.monotonic()
    for attempt in range(2):
        try:cp=subprocess.run(command,capture_output=True,text=True,timeout=100);code=cp.returncode;logs.append(cp.stdout+cp.stderr)
        except subprocess.TimeoutExpired:code=124;logs.append('Qualified compiler safeguard expired');break
        if code:break
    text='\n'.join(logs);(build/'compiler.log').write_text(text)
    result={'status':tex_compile.classify_log(text,code),'exit_code':code,'elapsed_seconds':time.monotonic()-begin,
            'master':tex[0],'master_sha256':hashlib.sha256(entries[tex[0]]).hexdigest(),
            'source_modification':'none; identical master bytes copied under compiler entry filename',
            'compilation_success':code==0,'mathematical_fidelity':'not established','model_repairs':0}
    atomic_json(build/'result.json',result);return result


def download_outputs(run,plan,job,record,client):
    identity=api.job_identity(job);folder=run/'jobs'/identity;folder.mkdir(parents=True,exist_ok=True)
    results={};entries=None
    for extension in ('mmd','md','lines.json','lines.mmd.json','mmd.zip','tex.zip'):
        path=folder/('raw.'+extension)
        if path.exists():payload=path.read_bytes()
        else:
            try:payload=client.request('pdf/'+record['pdf_id']+'.'+extension)
            except api.APIError as exc:
                results[extension]={'status':'unavailable','http_status':exc.status};continue
            if extension.endswith('.json'):
                payload=json.dumps(client.redact(json.loads(payload)),ensure_ascii=False,indent=2).encode()
            else:client.safe_bytes(payload)
            if extension.endswith('.zip'):
                contents=api.safe_zip(payload)
                for content in contents.values():client.safe_bytes(content)
            temporary=path.with_suffix(path.suffix+'.partial');temporary.write_bytes(payload);os.replace(temporary,path)
        results[extension]={'status':'downloaded','path':str(path.relative_to(run)),'bytes':len(payload),'sha256':sha(path)}
        if extension=='tex.zip':entries=api.safe_zip(payload)
    if entries is not None and plan.get('compile_pdf',True):
        results['direct_compilation']=compile_direct(run,folder,plan['compiler_image'],entries)
    lines=folder/'raw.lines.mmd.json'
    if lines.exists():
        data=read_json(lines)
        atomic_json(folder/'page-mapping.json',{'source_id':job['source_id'],'map':job['page_map'],
            'provider_data':data,'note':'Subset page indices map to original physical pages; raw line data retained separately.'})
    atomic_json(folder/'outputs.json',results)
    return results


def report(run,state,client=None):
    plan=read_json(run/'plan.json');records=list(state['jobs'].values())
    reserved=sum(r.get('reserved_microusd',0) for r in records)
    known=sum(r.get('estimated_incurred_microusd') or 0 for r in records)
    state['spending']={'cap_usd':1.0,'reserved_usd':reserved/1000000,'estimated_incurred_for_reported_pages_usd':known/1000000,
                       'actual_invoice_cost':'unknown','credits':'unknown','uncertain_submissions':sum(r.get('status')=='uncertain_submission' for r in records)}
    text=['# Mathpix supplementary extraction comparison','Status: '+state['status'],
          f"Frozen workload: {plan['unique_pages']} pages, {len(plan['jobs'])} subsets. No downstream GLM calls.",
          'Published rate $0.005/page; planned estimate $'+str(plan['estimated_total_microusd']/1000000)+'. Persistent cap $1.00 before tax.',
          'Reservations and estimates are not confirmed charges. Usage snapshots may lag and include other applications. Account credits/invoice cost remain unknown.',
          plan['privacy'], '|Source|Pages|Outcome|pdf_id|Direct TeX build|','|---|---:|---|---|---|']
    for job in plan['jobs']:
        r=state['jobs'].get(job['source_id'],{});comp=r.get('outputs',{}).get('direct_compilation',{}).get('status','not_attempted')
        text.append('|'+ '|'.join(map(str,(job['filename'],len(job['physical_pages']),r.get('status','pending'),r.get('pdf_id'),comp)))+'|')
    panels=[]
    for job in plan['jobs']:
        folder=run/'jobs'/api.job_identity(job);mmd=folder/'raw.mmd'
        pages=[]
        if mmd.exists():
            chunks=mmd.read_text().split(r'\pagebreak')
            if len(chunks)==len(job['physical_pages'])+1 and not chunks[-1].strip():pages=chunks[:-1]
        if folder.exists():atomic_json(folder/'page-text.json',{'physical_pages':job['physical_pages'],'texts':pages,
            'mapping_status':'exact documented pagebreak count' if pages else 'unresolved; consult raw line JSON and complete MMD',
            'normalization':'Split only at documented page separators; no mathematical edits'})
        for i,image in enumerate(job['evidence_images']):
            source=Path(image['path'])
            if sha(source)!=image['sha256']:raise ValueError('Original-page evidence changed')
            destination=run/'source-evidence'/(job['source_id']+'-p'+str(image['physical_page'])+'.png')
            destination.parent.mkdir(exist_ok=True)
            if not destination.exists():shutil.copyfile(source,destination)
            value=pages[i] if pages else 'Per-page mapping unresolved; inspect raw MMD and line JSON. No content discarded.'
            panels.append('<h2>'+html.escape(job['filename'])+' — physical page '+str(image['physical_page'])+'</h2><section><img width="600" src="'+str(destination.relative_to(run))+'"><pre>'+html.escape(value)+'</pre></section>')
    (run/'comparison.html').write_text('<!doctype html><meta charset="utf-8"><title>Mathpix source comparison</title><style>section{display:flex;gap:1em}pre{white-space:pre-wrap;max-width:800px}</style>'+''.join(panels))
    text+=['Open comparison.html for original-page images beside Mathpix MMD. Original-to-subset maps and render-equality checks are in plan.json. Raw MMD, Markdown, line JSON, ZIPs and compiler diagnostics are saved per job.',
           'Content fidelity and sampled source-image comparison remain separate from provider completion and TeX compilation. The local experiment continues independently.']
    (run/'START-HERE.md').write_text('\n\n'.join(text)+'\n')
    archive=ROOT/'results/inspection'/('mathpix-'+run.name+'-'+str(time.time_ns())+'.zip');archive.parent.mkdir(exist_ok=True)
    manifest=[]
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in run.rglob('*'):
            if not p.is_file() or p.is_symlink() or 'inputs' in p.relative_to(run).parts or p.stat().st_size>20*1024*1024:continue
            data=p.read_bytes()
            if client:client.safe_bytes(data)
            name=str(p.relative_to(run));z.writestr(name,data);manifest.append({'path':name,'sha256':hashlib.sha256(data).hexdigest()})
        z.writestr('FILE-HASHES.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('Inspection ZIP integrity failure')
    state['inspection']=str(archive);progress(run,state)


def worker(run):
    with (run/'terminal.log').open('a',buffering=1) as log:
        os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
        with writer_lock(run):
            plan=verify(run);state=read_json(run/'state.json')
            if state['status']==FINISHED:return
            client=api.Client(read_json(KEY))
            if state.get('key_id') not in (None,client.key_id):raise ValueError('Credential identity changed; budget is not reset')
            state.update(status='running',key_id=client.key_id,pid=os.getpid());progress(run,state)
            try:
                if not state.get('usage_before'):
                    state['usage_before']=usage(run,client,'before');progress(run,state)
                for job in plan['jobs']:
                    if (run/'pause.json').exists():state['status']='paused';return
                    if job['source_id'] in state['jobs']:continue
                    record=submit_once(run,plan,job,client);state['jobs'][job['source_id']]=record;progress(run,state)
                    print('SUBMISSION',job['filename'],record['status'],flush=True)
                    if record.get('shared_http_failure'):raise RuntimeError('Submission refused with shared HTTP status '+str(record['shared_http_failure'])+'; remaining documents were not submitted')
                    if record.get('status')=='downloaded' and Path(record['run'])!=run:
                        source=Path(record['run'])/'jobs'/api.job_identity(job)
                        target=run/'jobs'/api.job_identity(job)
                        if not target.exists():shutil.copytree(source,target)
                        for value in record.get('outputs',{}).values():
                            if isinstance(value,dict) and value.get('sha256') and sha(run/value['path'])!=value['sha256']:
                                raise ValueError('Compatible saved output identity changed')
                pending=True
                while pending:
                    pending=False
                    if (run/'pause.json').exists():state['status']='paused';break
                    for job in plan['jobs']:
                        record=state['jobs'][job['source_id']]
                        if not record.get('pdf_id') or record['status'] in ('downloaded','outputs_incomplete','provider_error','invalid_output'):continue
                        status=client.get_json('pdf/'+record['pdf_id'])
                        atomic_json(run/'jobs'/api.job_identity(job)/('status-'+str(time.time_ns())+'.json'),status)
                        if status.get('num_pages') is not None and status['num_pages']!=len(job['physical_pages']):
                            raise ValueError('Provider page count differs from frozen subset; no further dispatch')
                        record['provider_status']=status
                        if status.get('status')=='error':record['status']='provider_error'
                        elif status.get('status')=='completed':
                            conversions=client.get_json('converter/'+record['pdf_id'])
                            atomic_json(run/'jobs'/api.job_identity(job)/'conversion-status.json',conversions)
                            conversion_states=conversions.get('conversion_status',{})
                            waiting=any((v.get('status') if isinstance(v,dict) else v) in ('received','pending','processing','running','queued','converting') for v in conversion_states.values())
                            if waiting:pending=True;continue
                            try:record['outputs']=download_outputs(run,plan,job,record,client)
                            except (ValueError,zipfile.BadZipFile) as exc:
                                record.update(status='invalid_output',diagnostic=client.redact(str(exc)))
                                update_ledger(client,api.job_identity(job),record);progress(run,state);continue
                            missing=[ext for ext in ('mmd','md','tex.zip') if record['outputs'].get(ext,{}).get('status')!='downloaded']
                            record['download_checks']=record.get('download_checks',0)+1
                            if missing and record['download_checks']<3:
                                record['status']='awaiting_outputs';pending=True
                                update_ledger(client,api.job_identity(job),record);progress(run,state);continue
                            record['unavailable_outputs']=missing
                            record['status']='outputs_incomplete' if missing else 'downloaded';record['estimated_incurred_microusd']=len(job['physical_pages'])*api.RATE_MICROUSD
                            record['completed_at']=api.now()
                            print('DOWNLOADED',job['filename'],flush=True)
                        else:pending=True
                        update_ledger(client,api.job_identity(job),record);progress(run,state)
                    if pending:time.sleep(5)
                if state['status']!='paused':
                    state['usage_after']=usage(run,client,'after');state.update(status=FINISHED,finished_at=api.now())
            except Exception as exc:
                state.update(status='stopped_error',diagnostic=client.redact(str(exc)))
                print('STOPPED',state['diagnostic'],flush=True)
            finally:progress(run,state);report(run,state,client)
    from probe.extraction_comparison_report import combine
    combined=combine(ROOT,run)
    if combined:print('Combined inspection:',combined,flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('prepare','run','resume','worker','status','pause','bundle','usage'));parser.add_argument('--run',type=Path)
    args=parser.parse_args()
    if args.action=='prepare':print(prepare());return
    run=(args.run or Path(read_json(POINTER)['run'])).resolve()
    if args.action=='status':print(json.dumps(read_json(run/'progress.json'),indent=2));return
    if args.action=='pause':atomic_json(run/'pause.json',{'at':api.now()});print('Mathpix submission/poll pause requested');return
    if args.action=='usage':
        client=api.Client(read_json(KEY));record=usage(run,client,'refresh');print(json.dumps(record,indent=2));return
    if args.action=='worker':worker(run);return
    state=read_json(run/'state.json');verify(run)
    if args.action=='bundle':
        with writer_lock(run):report(run,state)
        print(state['inspection']);return
    if state['status']==FINISHED:print('Finished; zero new submissions or usage calls.');return
    with writer_lock(run):
        cp=subprocess.run(['tmux','has-session','-t',SESSION],capture_output=True,text=True)
        if cp.returncode==0:raise ValueError('Mathpix worker already exists')
        if cp.returncode!=1 or 'denied' in cp.stderr or 'permitted' in cp.stderr:raise ValueError('tmux unavailable')
        (run/'pause.json').unlink(missing_ok=True)
        import shlex
        command=shlex.join([str(ROOT/'.venv-control/bin/python'),'-B','-u',str(Path(__file__).resolve()),'worker','--run',str(run)])
        subprocess.run(['tmux','new-session','-d','-s',SESSION,'cd '+shlex.quote(str(ROOT))+' && exec '+command],check=True)
        print('Mathpix worker requested:',run)


if __name__=='__main__':main()
