"""Combine settled inspection archives without editing either experiment."""
from contextlib import ExitStack
import fcntl
import hashlib
import html
import json
from pathlib import Path, PurePosixPath
import time
import zipfile
from .common import atomic_json,read_json,sha,writer_lock


def combine(root,mathpix_run):
    root=Path(root);mathpix_run=Path(mathpix_run)
    pointer=root/'results/extraction-comparison-current.json'
    if not pointer.exists():return None
    local=Path(read_json(pointer)['run'])
    if not (local/'state.json').exists():return None
    with ExitStack() as stack:
        for run in sorted((local,mathpix_run)):
            lock=stack.enter_context((run/'.probe.lock').open('r'))
            try:fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
            except BlockingIOError:return None
        left=read_json(local/'state.json');right=read_json(mathpix_run/'state.json')
        if left['status']!='extraction_comparison_finished' or right['status']!='mathpix_finished':return None
        local_plan=read_json(local/'plan.json');cloud_plan=read_json(mathpix_run/'plan.json')
        scope=lambda rows:{(d['sha256'],p) for d in rows for p in d['physical_pages']}
        if scope(local_plan['documents'])!=scope(cloud_plan['jobs']):raise ValueError('Combined report scopes differ')
        archives={'local':Path(left['inspection']),'mathpix':Path(right['inspection'])}
        identity=hashlib.sha256(json.dumps({k:sha(p) for k,p in archives.items()},sort_keys=True).encode()).hexdigest()
        registry=root/'results/inspection/comparison-merges'
        with writer_lock(registry):
            record=registry/(identity+'.json')
            if record.exists():return Path(read_json(record)['zip'])
            target=root/'results/inspection'/('extraction-comparison-combined-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'.zip')
            manifest=[]
            with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as output:
                def add(name,data):
                    output.writestr(name,data);manifest.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
                for prefix,archive in archives.items():
                    with zipfile.ZipFile(archive) as source:
                        if source.testzip():raise ValueError('Input archive CRC failed')
                        for item in source.infolist():
                            path=PurePosixPath(item.filename)
                            if path.is_absolute() or '..' in path.parts or item.file_size>256*1024*1024:raise ValueError('Unsafe archive entry')
                            if not item.is_dir():add(prefix+'/'+item.filename,source.read(item))
                text=['# Four-arm extraction comparison',
                      'Local run: '+str(local),'Mathpix supplement: '+str(mathpix_run),
                      'Both frozen workers have finished. The local report contains baseline, MinerU Pro and GLM-OCR results and the two-assignment downstream test. Mathpix has no downstream GLM calls.',
                      'Start with local/START-HERE.md, local/comparison.html, and mathpix/START-HERE.md. Mathpix source-to-subset maps are in mathpix/plan.json; raw page/line output, native TeX ZIPs and direct compilation are under mathpix/jobs/.',
                      'Mathpix spending: '+json.dumps(right.get('spending',{})),
                      'Reserved/estimated costs are not invoices. Provider usage snapshots may lag or include other applications; credits and actual invoiced cost remain unknown.',
                      'Source-image inspection, extraction completion, model review and compilation are separate statuses. See the frozen critical passages; incomplete checks are not mathematical verification.']
                add('START-HERE.md',('\n\n'.join(text)+'\n').encode())
                panels=[]
                for document in local_plan['documents']:
                    job=next(j for j in cloud_plan['jobs'] if j['sha256']==document['sha256'])
                    from .mathpix_experiment import job_identity
                    cloud_folder=mathpix_run/'jobs'/job_identity(job)
                    cloud_pages=read_json(cloud_folder/'page-text.json') if (cloud_folder/'page-text.json').exists() else {'texts':[]}
                    baseline=read_json(local/'sources'/document['source_id']/'baseline.json')['blocks']
                    for index,page in enumerate(document['pages']):
                        n=page['physical_pdf_page'];ident=document['source_id']+'-p'+str(n)
                        values={'baseline':'\n\n'.join(b['tex'] for b in baseline if b['page']['original_physical_page']==n)}
                        for arm in ('mineru_pro','glm_ocr'):
                            p=local/'arms'/arm/'pages'/ident/'text.md';values[arm]=p.read_text() if p.exists() else 'No completed extraction; see diagnostics.'
                        values['mathpix']=cloud_pages['texts'][index] if len(cloud_pages['texts'])==len(document['pages']) else 'Page mapping unavailable; consult Mathpix raw output.'
                        columns=['<div><img width="500" src="local/'+html.escape(page['image'])+'"></div>']
                        columns += ['<div><h3>'+arm+'</h3><pre>'+html.escape(value)+'</pre></div>' for arm,value in values.items()]
                        panels.append('<h2>'+html.escape(document['filename'])+' — physical page '+str(n)+'</h2><section>'+''.join(columns)+'</section>')
                add('four-arm-comparison.html',('<!doctype html><meta charset="utf-8"><title>Four-arm extraction comparison</title><style>section{display:flex;gap:1em;overflow:auto}section>div{min-width:500px;max-width:650px}pre{white-space:pre-wrap}</style>'+''.join(panels)).encode())
                add('RUNS.json',json.dumps({'local':str(local),'mathpix':str(mathpix_run),'scope_pages':len(scope(cloud_plan['jobs'])),'archives_sha256':{k:sha(p) for k,p in archives.items()}},indent=2).encode())
                output.writestr('FILE-HASHES.json',json.dumps(manifest,indent=2))
            with zipfile.ZipFile(target) as z:
                if z.testzip():raise ValueError('Combined archive CRC failed')
                for entry in manifest:
                    if hashlib.sha256(z.read(entry['path'])).hexdigest()!=entry['sha256']:raise ValueError('Combined archive hash failure')
            atomic_json(record,{'zip':str(target),'sha256':sha(target),'bytes':target.stat().st_size})
            atomic_json(root/'results/extraction-comparison-combined-current.json',read_json(record))
            return target
