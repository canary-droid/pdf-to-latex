"""Additive DeepSeek Arm A baseline; historical paired inputs stay immutable."""
import copy
from pathlib import Path
import shutil

from .common import atomic_json, check_manifest, files_manifest, fingerprint, read_json, sha
from .batch_review import IdentityError, IntegrityError
from . import paired_inputs as historical
from .local_model import parse_json_response
from .page_review import validate_review_response
from .portable_export import accepted_fragment

CONFIG={**copy.deepcopy(historical.CONFIG),'endpoint':'http://127.0.0.1:8894/v1','model':'DeepSeek-V4.1-Flash-TF'}
IMAGE='sha256:35d9bda39ffde364249f21be294dde6aeee9c51940973477ca5728f32422aa35'
POLICY={'version':1,'max_requests':267,'gate_regions':12,'minimum_valid':9,
        'admission_seconds':28800,'max_attempts':1,'connection_pause_threshold':2}


def code_hashes():
    return {**historical.code_hashes(),**{n:sha(Path(__file__).parent/n) for n in
        ('deepseek_inputs.py','deepseek_trial.py','deepseek_report.py')}}


def seal(folder):atomic_json(folder/'manifest.json',files_manifest(folder))


def checked_seal(folder,digest=None,name='manifest.json'):
    if digest and sha(folder/name)!=digest:raise IntegrityError('Changed seal: '+str(folder))
    if not check_manifest(folder,read_json(folder/name)+[{'path':name,'sha256':sha(folder/name)}]):
        raise IntegrityError('Changed sealed evidence: '+str(folder))


def validate_answer(answer,data):
    if answer.get('actual_model')!=CONFIG['model']:raise IdentityError('DeepSeek response model identity missing or different')
    if answer.get('finish_reason')!='stop':raise ValueError('Non-stop/truncated completion')
    try:value=parse_json_response(answer['content'])
    except (ValueError,TypeError) as exc:raise historical.ResponseJSONError(str(exc)) from exc
    if not isinstance(value,dict) or set(value)!=set(historical.SCHEMA['required']):raise ValueError('Invalid paired response schema fields')
    validate_review_response({k:v for k,v in value.items() if k not in ('proposal_categories','observations')},data)
    cats=value['proposal_categories'];obs=value['observations']
    if not isinstance(cats,list) or len(cats)!=len(value['proposals']) or any(c not in historical.CATEGORIES for c in cats):
        raise ValueError('Invalid proposal category accounting')
    if not isinstance(obs,list) or any(not isinstance(o,dict) or set(o)!={'category','text'} or o['category'] not in historical.CATEGORIES
        or not isinstance(o['text'],str) or not o['text'].strip() for o in obs):raise ValueError('Invalid observations')
    return value


def latex_checks(value):
    """Existing conservative export safeguards; separate from format/fidelity.

    An unsupported fragment remains raw, UNACCEPTED and ineligible for export.
    This runner never applies proposals. The technical gate uses format/coverage,
    matching the historical review rather than treating compilability as fidelity.
    """
    result=[]
    for i,p in enumerate(value.get('proposals',[])):
        try:
            if p['suggested_latex']=='':packages=[];status='explicit_deletion_unaccepted'
            else:_,packages=accepted_fragment(p['suggested_latex']);status='supported_unaccepted'
            result.append({'proposal_index':i,'status':status,'packages':sorted(packages),'accepted':False})
        except ValueError as exc:result.append({'proposal_index':i,'status':'unsupported_export_blocked','reason':str(exc),'accepted':False})
    return result


def validate_order(order):
    if len(order)!=267 or [s['ordinal'] for s in order]!=list(range(1,268)) or len({s['region_id'] for s in order})!=267 or len({s['page_id'] for s in order})!=16:
        raise IntegrityError('Expected exact historical 267-region/16-page order')


def prepare(root,qwen,out):
    binding=read_json(qwen/'binding.json');state=read_json(qwen/'state.json')
    if state['status'] not in ('completed','completed_with_failures') or state['binding_sha256']!=fingerprint(binding):
        raise IntegrityError('Qwen trial is not a consistent completed run; do not rebind or resume it')
    preview=Path(binding['preview']);meta,order=historical.verify_preview(preview,binding['preview_manifest_sha256'])
    validate_order(order)
    if len(state['requests'])!=534 or any(r['status'] not in ('completed','failed') for r in state['requests'].values()):
        raise IntegrityError('Expected all 534 historical arms attempted, failures retained')
    for spec in order:
        for arm in ('A','B'):
            key=f"{spec['ordinal']:03d}-{arm}";folder=qwen/'requests'/key;rec=state['requests'][key]
            checked_seal(folder,rec['seal_sha256'],'seal.json')
            if read_json(folder/'request.json')!=read_json(preview/'regions'/f"{spec['ordinal']:03d}"/(arm+'.json')):
                raise IntegrityError('Historical dispatch differs from preview')
            outcome=read_json(folder/'outcome.json')
            if outcome['status']!=rec['status']:raise IntegrityError('Historical status differs from outcome')
            if rec['status']=='completed':
                data=read_json(preview/'regions'/f"{spec['ordinal']:03d}"/'input.json')
                if historical.validate_answer(read_json(folder/'assistant-response.json'),data)!=outcome['answer']:
                    raise IntegrityError('Historical answer differs from validated outcome')
    out.mkdir(parents=True,exist_ok=False);(out/'regions').mkdir();(out/'images').mkdir()
    specs=[]
    for old in order:
        key=f"{old['ordinal']:03d}";src=preview/'regions'/key;dest=out/'regions'/key;dest.mkdir()
        original=read_json(src/'A.json');payload=copy.deepcopy(original);payload['model']=CONFIG['model']
        if original['model']!=historical.CONFIG['model'] or set(original)!={'model','messages','max_tokens','stream','reasoning_effort'}:
            raise IntegrityError('Unexpected historical Arm A configuration')
        if original['max_tokens']!=16384 or original['stream'] is not False or original['reasoning_effort']!='medium':raise IntegrityError('Historical generation settings differ')
        if any(c.get('text','').startswith('ADDITIONAL NATIVE PDF EVIDENCE:') for m in original['messages'] for c in m['content']):raise IntegrityError('Arm B evidence in A request')
        data=read_json(src/'input.json')
        if len(data['blocks'])!=1 or data['blocks'][0]['id']!=old['region_id'] or data['page']!=old['page']:raise IntegrityError('Historical region mapping differs')
        shutil.copyfile(src/'input.json',dest/'input.json');atomic_json(dest/'request.json',payload)
        for image in data['images']:
            p=preview/image['path']
            if sha(p)!=image['sha256']:raise IntegrityError('Historical source image changed')
            new=out/image['path'];new.parent.mkdir(parents=True,exist_ok=True)
            if not new.exists():shutil.copyfile(p,new)
        specs.append({'ordinal':old['ordinal'],'region_id':old['region_id'],'page_id':old['page_id'],'page':old['page'],
            'phase':old['phase'],'qwen_request':str(qwen/'requests'/(key+'-A')),
            'historical_request':str(src/'A.json'),'historical_sha256':sha(src/'A.json'),
            'new_sha256':sha(dest/'request.json'),'input_sha256':sha(dest/'input.json'),
            'printed_page':old['page']['original_physical_page']-15,
            'printed_page_basis':'registered selection printed 91–210 corresponds to original PDF 106–225; separator pages may have no visible folio'})
    # Immutable source memberships and hashes include historical failures as well as successes.
    sources=dict(meta['source_hashes'])
    for folder in (qwen,preview):
        for e in files_manifest(folder):sources[str(folder/e['path'])]=e['sha256']
    atomic_json(out/'order.json',specs)
    atomic_json(out/'preview.json',{'schema':'deepseek-arm-a-v1','config':CONFIG,'policy':POLICY,'image_id':IMAGE,
        'code_sha256':code_hashes(),'historical_run':str(qwen),'historical_preview':str(preview),
        'source_hashes':sources,'notice':'Only model field changes. Omitted sampling inherits different deployment defaults; not a quantization-only comparison.'})
    seal(out)
    return out


def verify_preview(preview,expected=None):
    checked_seal(preview,expected);meta=read_json(preview/'preview.json');order=read_json(preview/'order.json')
    if meta['config']!=CONFIG or meta['policy']!=POLICY or meta['image_id']!=IMAGE or meta['code_sha256']!=code_hashes():
        raise IntegrityError('DeepSeek configuration/code/image changed; incompatible resume')
    validate_order(order)
    for name,digest in meta['source_hashes'].items():
        p=Path(name)
        if p.is_symlink() or not p.is_file() or sha(p)!=digest:raise IntegrityError('Historical/source evidence changed: '+name)
    for spec in order:
        folder=preview/'regions'/f"{spec['ordinal']:03d}";body=read_json(folder/'request.json')
        if sha(folder/'request.json')!=spec['new_sha256'] or sha(folder/'input.json')!=spec['input_sha256']:raise IntegrityError('Region binding changed')
        original=read_json(spec['historical_request'])
        if sha(spec['historical_request'])!=spec['historical_sha256'] or {**body,'model':original['model']}!=original or body['model']!=CONFIG['model']:
            raise IntegrityError('DeepSeek request must differ ONLY in model')
    return meta,order
