#!/usr/bin/env python3
"""Finite candidate extraction inside an isolated container, never a corpus queue."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback
import threading
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from probe.extraction_comparison import MODEL_PINS, raw_text
from probe.extraction_followup import glm_config as safe_glmocr_config, validate_routes, account_regions, faithful_export


def model_context_limit(config):
    values=[config.get('max_position_embeddings'),config.get('text_config',{}).get('max_position_embeddings')]
    limits=[]
    for value in values:
        if value is None:continue
        if type(value) not in (int,float) or not value>0 or not float(value).is_integer():
            raise ValueError('Invalid pinned model context metadata')
        limits.append(int(value))
    if not limits:raise ValueError('Pinned model declares no context limit; no guessed override')
    return min(limits)



def layout_api_compatibility():
    """Alias the pinned SDK import to the same upstream V3 Fast processor.

    No installed files, weights, layout algorithm or preprocessing defaults
    change. Load lazy symbols first: imports may replace the module object.
    """
    from transformers import PPDocLayoutV3ForObjectDetection, PPDocLayoutV3ImageProcessorFast
    import transformers
    if transformers.__version__ != '5.3.0':
        raise RuntimeError('Unqualified Transformers version for layout compatibility')
    existing = getattr(transformers, 'PPDocLayoutV3ImageProcessor', None)
    if existing is not None and existing is not PPDocLayoutV3ImageProcessorFast:
        raise RuntimeError('Different existing layout processor; do not overwrite')
    for method in ('from_pretrained', 'post_process_object_detection', '_mask2polygon'):
        if not callable(getattr(PPDocLayoutV3ImageProcessorFast, method, None)):
            raise RuntimeError('Required layout processor API unavailable: '+method)
    transformers.PPDocLayoutV3ImageProcessor = PPDocLayoutV3ImageProcessorFast
    return {'transformers': transformers.__version__, 'sdk_import': 'PPDocLayoutV3ImageProcessor',
            'implementation': PPDocLayoutV3ImageProcessorFast.__name__,
            'scope': 'Process-local import alias; upstream implementation and preprocessing unchanged'}


def local_empty_env(output):
    path=Path(output)/'empty.env'
    if path.is_symlink():raise ValueError('Dotenv sentinel must not be a symlink')
    if path.exists():
        if not path.is_file() or path.read_bytes()!=b'':raise ValueError('Dotenv sentinel must remain an empty regular file')
    else:
        with path.open('xb'):pass
    return path


def incomplete_receipt(data):
    return (data.get('finished') is False or bool(data.get('error')) or data.get('http_status',200)>=400 or
            not data.get('choices') or any(c.get('finish_reason')!='stop' for c in data.get('choices',[])))


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    with temporary.open('w') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def download(models):
    from huggingface_hub import snapshot_download
    records={}
    for name,(repository,revision) in MODEL_PINS.items():
        folder=models/name
        snapshot_download(repository,revision=revision,local_dir=str(folder),token=False)
        records[name]={'repository':repository,'revision':revision,'files':[
            {'path':str(p.relative_to(folder)),'sha256':digest(p),'bytes':p.stat().st_size}
            for p in sorted(folder.rglob('*')) if p.is_file() and '.cache' not in p.parts]}
        save(models/'identities.json',records)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('download','mineru_pro','glm_ocr'))
    parser.add_argument('--study',type=Path,default=Path('/study'))
    parser.add_argument('--models',type=Path,default=Path('/models'))
    parser.add_argument('--output',type=Path,default=Path('/output'))
    args=parser.parse_args()
    if args.action=='download':download(args.models);return
    plan=json.loads((args.study/'plan.json').read_text())
    if plan['status']!='frozen':raise RuntimeError('Workload is not frozen')
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    state_path=out/'state.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {'pages':{},'status':'prepared'}
    if state['status']=='finished':return
    if any(x['status']=='running' for x in state['pages'].values()):
        raise RuntimeError('Uncertain prior extraction; no replay')
    identities=json.loads((args.models/'identities.json').read_text())
    for name in (args.action, 'glm_layout') if args.action=='glm_ocr' else (args.action,):
        record=identities[name]
        if (record['repository'],record['revision'])!=MODEL_PINS[name]:raise RuntimeError('Wrong model revision')
        for f in record['files']:
            if digest(args.models/name/f['path'])!=f['sha256']:raise RuntimeError('Changed model asset')
    import torch
    if not torch.cuda.is_available():raise RuntimeError('CUDA is unavailable')
    capability=torch.cuda.get_device_capability()
    if capability!=(12,1):raise RuntimeError('Expected GB10 sm_121; observed '+str(capability))
    a=torch.ones((32,32),device='cuda',dtype=torch.bfloat16)
    b=a@torch.eye(32,device='cuda',dtype=torch.bfloat16);torch.cuda.synchronize()
    if not torch.equal(a,b):raise RuntimeError('BF16 CUDA arithmetic qualification failed')
    del a,b
    packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions()}
    save(out/'runtime.json',{'packages':packages,'capability':capability,'gpu':torch.cuda.get_device_name(),
                            'cuda':torch.version.cuda,'arm':args.action,'model':identities[args.action],
                            'layout_model':identities.get('glm_layout') if args.action=='glm_ocr' else None,
                            'model_identity_scope':'Verified disk identity and requested model; load/page outcomes separately establish actual execution',
                            'glmocr_install_provenance':importlib.metadata.distribution('glmocr').read_text('direct_url.json'),
                            'dependency_qualification':json.loads(Path('/opt/extraction-dependency-check.json').read_text()),
                            'bf16_cuda_arithmetic':'passed',
                            'rendering':'200 DPI source images; SDK-specific resizing/cropping retained',
                            'generation_deadline':None,'automatic_retries':0})
    server=None;engine=None;started=time.monotonic()
    capture={'folder':None,'count':0,'incomplete':False};capture_lock=threading.Lock()
    def receipt(data):
        with capture_lock:
            if capture['folder'] is None:return
            capture['count']+=1
            if incomplete_receipt(data):capture['incomplete']=True
            save(capture['folder']/'raw-recognition'/(str(capture['count']).zfill(4)+'.json'),data)
    load={'started_epoch':time.time(),'status':'running'}
    state.setdefault('loads',[]).append(load);save(state_path,state)
    try:
        if args.action=='mineru_pro':
            from vllm import LLM
            from mineru_vl_utils import MinerUClient, MinerULogitsProcessor
            context=model_context_limit(json.loads((args.models/'mineru_pro/config.json').read_text()))
            llm=LLM(model=str(args.models/'mineru_pro'),dtype='bfloat16',max_model_len=context,
                    gpu_memory_utilization=.30,max_num_seqs=2,logits_processors=[MinerULogitsProcessor])
            engine=MinerUClient(backend='vllm-engine',vllm_llm=llm,image_analysis=True,
                                max_concurrency=2,max_retries=0,abandon_paratext=False,abandon_list=False)
            original_content=engine.client.get_output_content
            def captured_content(output):
                receipt({'finished':output.finished,'prompt_tokens':len(output.prompt_token_ids or []),
                         'choices':[{'text':c.text,'finish_reason':c.finish_reason,'output_tokens':len(c.token_ids)} for c in output.outputs]})
                return original_content(output)
            engine.client.get_output_content=captured_content
            from mineru_vl_utils.mineru_client import DEFAULT_SAMPLING_PARAMS
            save(out/'effective-sdk-config.json',{'backend':'vllm-engine','layout_image_size':[1036,1036],
                'min_image_edge':28,'max_image_edge_ratio':50,'image_analysis':True,'max_concurrency':2,
                'model_context_limit':context,'observed_vllm_context':llm.llm_engine.model_config.max_model_len,
                'abandon_paratext':False,'abandon_list':False,'max_retries':0,
                'sampling_parameters_repr':repr(DEFAULT_SAMPLING_PARAMS),
                'preprocessing_scope':'Pinned SDK defaults and supplied 200-DPI pages; intermediate tensor dimensions are not independently instrumented'})
            extract=lambda image: engine.two_step_extract(image)
        else:
            config=safe_glmocr_config(args.models/'glm_layout')
            save(out/'label-routes.json',validate_routes(json.loads((args.models/'glm_layout/config.json').read_text())['id2label'],config))
            save(out/'layout-api-compatibility.json',layout_api_compatibility())
            # Only this container's own local OCR server is started.
            log=(out/'server.log').open('a',buffering=1)
            command=[sys.executable,'-m','vllm.entrypoints.openai.api_server',
                     '--model',str(args.models/'glm_ocr'),'--served-model-name','glm-ocr',
                     '--host','127.0.0.1','--port','18080','--dtype','bfloat16',
                     '--max-model-len','32768','--gpu-memory-utilization','0.30','--max-num-seqs','2']
            save(out/'server-command.json',command)
            server=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
            while True:
                if server.poll() is not None:raise RuntimeError('Local OCR server exited during startup')
                try:
                    with urllib.request.urlopen('http://127.0.0.1:18080/health',timeout=10) as response:
                        if response.status==200:break
                except OSError:time.sleep(2)
            # SDK defaults have a fixed 120-second read deadline. This adapter
            # removes only the read deadline and forbids any nonlocal request.
            import requests
            from urllib.parse import urlsplit
            original_request=requests.Session.request
            def local_request(session,method,url,**kwargs):
                address=urlsplit(url)
                if address.scheme!='http' or address.hostname!='127.0.0.1' or address.port!=18080:
                    raise RuntimeError('Nonlocal extraction request refused')
                kwargs['timeout']=(30,None)
                response=original_request(session,method,url,**kwargs)
                if method.upper()=='POST':
                    try:payload=response.json()
                    except ValueError:payload={'unparsed_response':response.text}
                    if isinstance(payload,dict):receipt(dict(payload,http_status=response.status_code))
                return response
            requests.Session.request=local_request
            config=safe_glmocr_config(args.models/'glm_layout')
            save(out/'sdk-config.json',config)
            from glmocr import GlmOcr
            engine=GlmOcr(config_path=str(out/'sdk-config.json'),mode='selfhosted',env_file=str(local_empty_env(out)))
            effective=engine.config_model.pipeline.model_dump()
            save(out/'effective-sdk-config.json',{k:effective[k] for k in ('layout','page_loader','result_formatter','max_workers')})
            pipeline=engine._pipeline
            observed={}
            original_layout=pipeline.layout_detector.process
            def audited_layout(*a,**kw):
                result=original_layout(*a,**kw)
                observed['detected']=result[0]
                save(capture['folder']/'detected-regions.json',result[0])
                return result
            pipeline.layout_detector.process=audited_layout
            original_format=pipeline.result_formatter.process
            def audited_format(grouped,*a,**kw):
                observed['recognized']=grouped
                save(capture['folder']/'recognized-regions.json',grouped)
                return original_format(grouped,*a,**kw)
            pipeline.result_formatter.process=audited_format
            extract=lambda image:engine.parse(str(image))
        state.update(status='running',load_seconds=time.monotonic()-started)
        load.update(status='completed',elapsed_seconds=time.monotonic()-started)
        save(state_path,state)
        jobs=[(d,p) for d in plan['documents'] for p in d['pages'] if [d['source_id'],p['physical_pdf_page']] in plan['workloads'][args.action]]
        smoke=next(((d,p) for d,p in jobs if d['source_id']=='original-21debf82bc2c0a3d' and p['physical_pdf_page']==5),jobs[0])
        jobs=[smoke]+[j for j in jobs if j!=smoke]
        for document,page in jobs:
            key=document['source_id']+'-p'+str(page['physical_pdf_page'])
            if key in state['pages']:continue
            if page.get('verified_blank'):
                state['pages'][key]={'status':'blank_source_preserved','image_sha256':page['sha256'],'physical_page':page['physical_pdf_page'],'source_id':document['source_id'],'outputs':[],'elapsed_seconds':0};save(state_path,state);continue
            if (out/'pause.json').exists():state['status']='paused';break
            image=args.study/page['image']
            if digest(image)!=page['sha256']:raise RuntimeError('Frozen image changed')
            folder=out/'pages'/key;folder.mkdir(parents=True,exist_ok=False)
            capture.update(folder=folder,count=0,incomplete=False)
            record={'status':'running','source_id':document['source_id'],'physical_page':page['physical_pdf_page'],
                    'image_sha256':page['sha256'],'started_epoch':time.time()}
            state['pages'][key]=record;save(state_path,state)
            begin=time.monotonic();torch.cuda.reset_peak_memory_stats()
            print('EXTRACT',args.action,document['filename'],page['physical_pdf_page'],flush=True)
            try:
                if args.action=='mineru_pro':
                    from PIL import Image
                    with Image.open(image) as visual:
                        result=extract(visual)
                        save(folder/'native.json',result)
                        text=raw_text(result)
                        for i,block in enumerate(result):
                            if block.get('type') in ('image','chart','image_block','table'):
                                box=block.get('bbox')
                                if box and len(box)==4:
                                    pixels=(box[0]*visual.width,box[1]*visual.height,box[2]*visual.width,box[3]*visual.height)
                                    visual.crop(pixels).save(folder/f'region-{i}.png')
                else:
                    result=extract(image)
                    save(folder/'native.json',result.to_dict())
                    result.save(output_dir=str(folder/'native-assets'))
                    (folder/'sdk-formatted.md').write_text(result.markdown_result)
                    if len(observed['detected'])!=1 or len(observed['recognized'])!=1:raise RuntimeError('Unexpected multi-page identity')
                    from PIL import Image
                    asset_refs={}
                    with Image.open(image) as source_image:
                        for region in observed['detected'][0]:
                            if region['task_type']=='skip':
                                box=region['bbox_2d'];ref='original-region-'+str(region['index'])+'.png'
                                source_image.crop((box[0]*source_image.width/1000,box[1]*source_image.height/1000,box[2]*source_image.width/1000,box[3]*source_image.height/1000)).save(folder/ref)
                                asset_refs[region['index']]=ref
                    try:ledger=account_regions(observed['detected'][0],observed['recognized'][0],asset_refs)
                    except ValueError as exc:raise RuntimeError('Shared region accounting failure: '+str(exc)) from exc
                    save(folder/'region-accounting.json',{'regions':ledger,'export':'one faithful raw-recognition block per region; SDK splits/merges retained separately in native.json/sdk-formatted.md','complete':True})
                    text=faithful_export(ledger)
                (folder/'text.md').write_text(text)
                if not text.strip() or (len(text.strip())<100 and not plan.get('allow_sparse_source_content')):raise ValueError('Empty or implausibly short extraction; inspect native output')
                if len(text.strip())<100:record['source_review_required']='Sparse nonblank content; nonempty OCR is not proof of faithful transcription'
                record['status']='failed_truncated_or_nonstop_response' if capture['incomplete'] else 'completed'
                record['outputs']=[{'path':str(p.relative_to(out)),'sha256':digest(p)} for p in folder.rglob('*') if p.is_file()]
            except (ValueError,TypeError,KeyError) as exc:
                record.update(status='failed',error=str(exc),traceback=traceback.format_exc())
            except Exception as exc:
                record.update(status='failed_shared_or_runtime',error=str(exc),traceback=traceback.format_exc())
                raise
            finally:
                record.update(elapsed_seconds=time.monotonic()-begin,
                              peak_torch_allocated_bytes=torch.cuda.max_memory_allocated(),
                              peak_torch_reserved_bytes=torch.cuda.max_memory_reserved(),
                              process_lifetime_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                              memory_scope='This Python process/allocator; separate vLLM server allocations excluded')
                save(folder/'outcome.json',record);save(state_path,state)
            if (document,page)==smoke and record['status']!='completed':
                state['status']='qualification_failed';break
        else:state['status']='finished'
    except BaseException as exc:
        if load['status']=='running':load.update(status='failed',elapsed_seconds=time.monotonic()-started,error=str(exc))
        state.update(status='stopped_error',error=str(exc),traceback=traceback.format_exc())
        raise
    finally:
        save(state_path,state)
        if args.action=='glm_ocr' and engine is not None:
            engine.close()
        if server is not None:
            # No active page request remains here; this is our private server.
            server.terminate();server.wait()


if __name__=='__main__':main()
