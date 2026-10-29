"""Owned-page adapter into existing visual recovery; no new scheduler or OCR."""
import argparse
import base64
import copy
import html
import json
from pathlib import Path

from . import experiment as ex, recovery, recovery_trial as trial, evaluation_export as export, bibliography
from .batch_inputs import SCHEMA as OMISSION_SCHEMA, PROMPT as OMISSION_PROMPT, validate_response as validate_batch
from .common import atomic_json, read_json, sha, fingerprint, files_manifest, writer_lock
from .page_review import LIMITS
from .saved_pages import saved_pages, render_region

ROOT=Path(__file__).resolve().parents[1]
VERSION='owned-page-recovery-v1'
QUALIFIED_IMAGE='sha256:cf31ff0238bc6a208228be07acb4a4122a248d0e019ea1ec0cfcd621ff57fd45'


def owned_scope(pages,source,source_record):
    if not source or source in ('all','both','book') or ',' in source:
        raise ValueError('Select the explicit registered book source, never generic all/both/book')
    numbers=[];blocks=[]
    for p in pages:
        n=p['page']['selected_page']
        if p['source_id']!=source or p['page']['owner'] is not True:raise ValueError('Context is not an owned page')
        if type(n) is not int or not 1<=n<=source_record['pages'] or p['page']['original_physical_page']!=source_record['original_pages'][n-1]:
            raise ValueError('Source original-page map differs')
        numbers.append(n);blocks.extend(b['id'] for b in p['blocks'])
    if sorted(numbers)!=list(range(1,source_record['pages']+1)):raise ValueError('Missing or duplicate owned pages')
    if len(blocks)!=len(set(blocks)):raise ValueError('Duplicate owned block')
    return sorted(pages,key=lambda p:p['page']['selected_page'])


def validate_omissions(value,data):
    try:validate_batch(value,data)
    except ValueError as exc:raise recovery.ValidationError('coverage',[{'path':'$','message':str(exc)}]) from exc
    if any(p['block_ids'] for p in value['proposals']):
        raise recovery.ValidationError('coverage',[{'path':'$.proposals','message':'Omission checks cannot replace recognized blocks'}])
    return value


def request(data,out,config,omission=False):
    schema=OMISSION_SCHEMA if omission else recovery.VISUAL_SCHEMA
    prompt=OMISSION_PROMPT if omission else trial.VISUAL_PROMPT
    text=prompt+'\nRESPONSE SCHEMA:\n'+json.dumps(schema)+'\nSELECTED DATA:\n'+json.dumps(data,ensure_ascii=False)
    if len(text)>LIMITS['max_page_characters']:raise ValueError('Complete region/context exceeds character bound; explicit smaller coherent selection required, no clipping')
    content=[{'type':'text','text':text}]
    for im in data['images']:
        p=out/im['path']
        if p.stat().st_size>LIMITS['max_image_bytes'] or im['width']*im['height']>LIMITS['max_image_pixels'] or sha(p)!=im['sha256']:
            raise ValueError('Source image exceeds bound or changed')
        content += [{'type':'text','text':'Original source '+im['role']+'; original-page bbox '+str(im['bbox'])},
            {'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode()}}]
    body={'model':config['model'],'messages':[{'role':'user','content':content}],
        'max_tokens':config['max_tokens'],'stream':False,'reasoning_effort':config['reasoning_effort']}
    # Flash Next lacks xgrammar: schema stays in prompt, validated locally.
    if len(json.dumps(body,ensure_ascii=False).encode())>LIMITS['max_request_bytes']:raise ValueError('Request exceeds byte bound; no image/text discarded')
    return body


def validate_preparation(preview,meta,units):
    book=meta['book_review'];coverage=read_json(preview/'coverage.json')
    if book['version']!=VERSION or meta['kind']!='visual' or meta['config']!=trial.CONFIG:raise ValueError('Changed owned-page review protocol/settings')
    expected=coverage['pages'];numbers=[r['selected_page'] for r in expected]
    if numbers!=list(range(1,book['source_record']['pages']+1)):raise ValueError('Incomplete owned-page inventory')
    if [r['original_physical_page'] for r in expected]!=book['source_record']['original_pages']:raise ValueError('Changed original-page identity')
    targets=[b for p in expected for b in p['block_ids']];actual=[];omissions=[]
    if len(targets)!=len(set(targets)):raise ValueError('Duplicate inventory block')
    for u in units:
        d=read_json(preview/u['data'])
        if d['source_id']!=book['source']:raise ValueError('Wrong source in request')
        if u['kind']=='omission':
            if d['blocks'] or d['scope']!='page_omissions':raise ValueError('Omission unit claims recognized targets')
            omissions.append(d['page_id'])
        elif u['kind']=='visual':
            if len(d['blocks'])!=1 or d['review_scope']!='selected_blocks':raise ValueError('Visual region must own one complete block')
            actual.append(d['blocks'][0]['id'])
        else:raise ValueError('Wrong owned-page unit kind')
        page=next((p for p in expected if p['page_id']==d['page_id']),None)
        if not page or d['page']['selected_page']!=page['selected_page'] or d['page']['original_physical_page']!=page['original_physical_page']:
            raise ValueError('Unit source map differs from owned inventory')
        if u['gate']!=(page['selected_page'] in book['gate_pages']):raise ValueError('Changed gate membership')
    if sorted(actual)!=sorted(targets) or sorted(omissions)!=sorted(p['page_id'] for p in expected):raise ValueError('Each owned block and each page omission check must occur exactly once')
    if meta['limits']['baseline_calls']!=len(units) or meta['limits']['per_parent_recovery']!=2:raise ValueError('Changed bounded review allowance')
    return coverage


def prepare(conversion,source,*,gate_first=32,gate_count=2,recovery_calls=80,hours=6,compiler_image=QUALIFIED_IMAGE):
    conversion=Path(conversion).resolve();state=read_json(conversion/'state.json')
    if state['status']!='conversion_completed_unreviewed':raise ValueError('Wait for fully completed conversion; incomplete outputs are not final evidence')
    record=state['settings']['sources'][source]
    # Normal saved-page integrity validation belongs to the operator's offline preparation.
    pages=owned_scope(saved_pages(ROOT,conversion,source),source,record)
    gate_pages=list(range(gate_first,gate_first+gate_count))
    if type(gate_first) is not int or type(gate_count) is not int or not 1<=gate_count<=4 or not set(gate_pages)<=set(range(1,record['pages']+1)):
        raise ValueError('Initial slice requires one to four actual pages')
    if not 0<=recovery_calls or not 0<hours<=24:raise ValueError('Explicit finite recovery/time limits required')
    from .tex_compile import command
    command(compiler_image,ROOT/'runs')  # Validate immutable image ID only; no Docker execution.
    cohort=fingerprint([sha(conversion/'state.json'),source,gate_pages,recovery_calls,hours,compiler_image])
    for p in (ROOT/'runs').glob('book-review-input-*/preview.json'):
        if read_json(p).get('book_review',{}).get('cohort')==cohort:
            raise ValueError('Prepared cohort already exists; resume its bound run, do not reset calls: '+str(p.parent))
    out=ex.new_path(ROOT,'book-review-input');run=ex.new_path(ROOT,'book-review-trial');out.mkdir(parents=True)
    units=[];inventory=[];hashes={str(conversion/'state.json'):sha(conversion/'state.json'),str((ROOT/record['pdf']).resolve()):record['sha256']};spans=[]
    for page in pages:
        n=page['page']['selected_page'];folder=out/'pages'/page['page_id'];folder.mkdir(parents=True)
        atomic_json(folder/'source-page.json',page)
        attempt=conversion/page['source_attempt']
        for name in ('input.pdf','page-map.json','output/middle_json.json'):hashes[str(attempt/name)]=sha(attempt/name)
        def image(name,bbox,role):
            im=render_region(attempt/'input.pdf',page['page']['local_page_idx'],folder/name,bbox=bbox,
                max_edge=LIMITS['page_max_edge'] if bbox is None else LIMITS['crop_max_edge'])
            im.update(path=str((folder/name).relative_to(out)),role=role,id=name);return im
        full=image('source.png',None,'complete page context')
        halves=[image('omission-top.png',[0,0,1,.52],'whole-page omission top'),image('omission-bottom.png',[0,.48,1,1],'whole-page omission bottom')]
        inventory.append({'page_id':page['page_id'],'selected_page':n,'original_physical_page':page['page']['original_physical_page'],
            'block_ids':[b['id'] for b in page['blocks']],'source_page':str((folder/'source-page.json').relative_to(out))})
        base={k:page[k] for k in ('page_id','source_id','page','coordinate_system')}
        for b in page['blocks']:
            original=export.draft(b)
            spans.append({'block_id':b['id'],'text':original['text'],'source_location':{'source_id':source,'page':page['page'],'bbox':b['bbox']}})
            identity=page['page_id']+'-b'+str(b['reading_order']);unavailable=None;images=[full]
            if b['bbox']:images.append(image('b'+str(b['reading_order'])+'.png',b['bbox'],'selected complete block'))
            else:unavailable='No verified source bbox; full raw block retained, explicit region preparation required'
            d={**base,'review_scope':'selected_blocks','blocks':[b],
                'context_blocks':[x for x in page['blocks'] if abs(x['reading_order']-b['reading_order'])==1],
                'context_is_reviewed':False,'draft_by_block':[{'block_id':b['id'],'latex':original['text'],'status':original['export_status']}],
                'fragment_contract_by_block':{b['id']:['latex_fragment','math_body','delete'] if b['kind']=='equation' else ['latex_fragment','delete']},'images':images}
            try:body=request(d,out,trial.CONFIG)
            except ValueError as exc:body={};unavailable=str(exc)
            units.append(trial.save_unit(out,identity,d,body,kind='visual',gate=n in gate_pages,
                location={'block':b['id'],'page':page['page']},unavailable=unavailable))
        identity=page['page_id']+'-omissions'
        d={**base,'unit_id':identity,'scope':'page_omissions','blocks':[],'context_blocks':page['blocks'],'context_is_reviewed':False,'draft_by_block':[], 'images':[full,*halves]}
        unavailable=None
        try:body=request(d,out,trial.CONFIG,True)
        except ValueError as exc:body={};unavailable=str(exc)
        units.append(trial.save_unit(out,identity,d,body,kind='omission',gate=n in gate_pages,location={'page':page['page']},unavailable=unavailable))
    units.sort(key=lambda u:(not u['gate'],u['location']['page']['selected_page'],u['id'].endswith('-omissions'),int(u['id'].rsplit('-b',1)[-1]) if u['kind']=='visual' else 0))
    atomic_json(out/'coverage.json',{'pages':inventory,'coverage_basis':'owned recognized blocks plus independent full-page omission check; technical completion is not fidelity'})
    atomic_json(out/'bibliography.json',bibliography.inventory(spans,{'source_id':source,'sha256':record['sha256']},'unknown'))
    count=sum(u['gate'] for u in units)
    trial.finish_preview(out,units,'visual',trial.CONFIG,hashes,
        {'baseline_calls':len(units),'recovery_calls':min(recovery_calls,2*len(units)),'per_parent_recovery':2,'admission_seconds':int(hours*3600)},
        {'minimum_first':0,'minimum_final':count,'minimum_coverage':count,'frozen_before_live':True},
        {'gate_pages':gate_pages,'all_owned_pages':len(pages),'acceptance':'UNACCEPTED'})
    (out/'manifest.json').unlink();meta=read_json(out/'preview.json')
    meta['book_review']={'version':VERSION,'source':source,'conversion':str(conversion),'source_record':record,
        'gate_pages':gate_pages,'compiler_image':compiler_image,'cohort':cohort,
        'expansion':'Same sealed run, continue after inspected gate; no replay or reset','omissions':'Insertion proposals remain deferred, never silently applied'}
    atomic_json(out/'preview.json',meta);validate_preparation(out,meta,units);ex.seal(out);ex.initialize(out,run)
    export.experiment_report(out,run)
    result={'preview':str(out),'run':str(run),'gate_pages':gate_pages,'all_pages':len(pages),'units':len(units),'unavailable':sum(bool(u.get('unavailable')) for u in units)}
    atomic_json(ROOT/'results/book-review-current.json',result);return result


def coverage_summary(preview,state,units):
    rows=read_json(preview/'coverage.json')['pages'];result=[]
    for page in rows:
        specs=[u for u in units if u['location']['page']['selected_page']==page['selected_page']]
        blocks=[u for u in specs if u['kind']=='visual'];omission=next(u for u in specs if u['kind']=='omission')
        checked=[u['location']['block'] for u in blocks if state['units'][u['id']]['status']=='completed']
        result.append({**page,'technically_completed_blocks':checked,'unchecked_blocks':[b for b in page['block_ids'] if b not in checked],
            'omission_check_status':state['units'][omission['id']]['status'],
            'coverage_meaning':'Model-claimed coverage, not source fidelity; omissions still require manual disposition'})
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('prepare');q.add_argument('--conversion',required=True,type=Path);q.add_argument('--source',required=True)
    q.add_argument('--gate-first',type=int,default=32);q.add_argument('--gate-count',type=int,default=2)
    q.add_argument('--recovery-calls',type=int,default=80);q.add_argument('--hours',type=float,default=6);q.add_argument('--compiler-image',default=QUALIFIED_IMAGE)
    for name in ('ready','launch','status','pause','report','bundle','dispositions','candidate'):
        q=sub.add_parser(name);q.add_argument('--run',required=True,type=Path)
        if name=='launch':
            q.add_argument('--readiness',required=True,type=Path);q.add_argument('--stage',choices=('gate','continue'),required=True);q.add_argument('--resume',action='store_true');q.add_argument('--compiler-image',required=True)
        if name=='candidate':q.add_argument('--dispositions',required=True,type=Path)
    a=p.parse_args(argv)
    if a.action=='status':
        b=read_json(a.run/'binding.json');s=read_json(a.run/'state.json');preview=Path(b['preview'])
        print(json.dumps({'run':str(a.run),'status':s['status'],'calls':len(s['calls']),'elapsed_seconds':s['elapsed_seconds'],'pages':coverage_summary(preview,s,read_json(preview/'units.json'))},indent=2));return 0
    if a.action=='pause':
        b=read_json(a.run/'binding.json');m,_=ex.verify_preview(Path(b['preview']))
        if not m.get('book_review'):raise ValueError('Wrong run type')
        (a.run/'PAUSE').touch();print('Pause requested after current bounded call.');return 0
    with writer_lock(ROOT/'runs'):
        if a.action=='prepare':print(json.dumps(prepare(a.conversion,a.source,gate_first=a.gate_first,gate_count=a.gate_count,recovery_calls=a.recovery_calls,hours=a.hours,compiler_image=a.compiler_image),indent=2));return 0
        b=read_json(a.run/'binding.json');preview=Path(b['preview']);m,_=ex.verify_preview(preview)
        if not m.get('book_review'):raise ValueError('Wrong run type')
        if a.action=='launch':
            if a.compiler_image!=m['book_review']['compiler_image']:raise ValueError('Use the sealed qualified compiler image')
            if a.resume and (a.run/'PAUSE').exists():(a.run/'PAUSE').unlink()
            code=ex.execute(ROOT,a.run,stage=a.stage,readiness=a.readiness.resolve(),resume=a.resume,compiler_image=a.compiler_image)
            export.experiment_report(preview,a.run);print(json.dumps(export.bundle(ROOT,preview,a.run),indent=2));return code
        if a.action=='ready':
            out=ex.new_path(ROOT,'book-review-readiness');ex.ready(ROOT,m['config'],out,True)
            atomic_json(a.run/'latest-readiness.json',{'path':str(out)});print('Readiness:',out);return 0
        s=read_json(a.run/'state.json')
        if s['active_since_epoch'] is not None:raise ValueError('Wait for writer to exit')
        if a.action=='report':print(json.dumps(export.experiment_report(preview,a.run),indent=2))
        elif a.action=='bundle':print(json.dumps(export.bundle(ROOT,preview,a.run),indent=2))
        elif a.action=='dispositions':
            out=ex.new_path(ROOT,'book-review-dispositions').with_suffix('.json');atomic_json(out,export.disposition_template(a.run));print(out)
        elif a.action=='candidate':
            out=ex.new_path(ROOT,'book-candidate');export.build_candidate(preview,a.run,out,dispositions=a.dispositions);print('Candidate:',out,'; compilation not performed')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,RuntimeError,OSError) as exc:raise SystemExit(str(exc)) from None
