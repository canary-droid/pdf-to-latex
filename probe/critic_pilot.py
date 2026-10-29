"""Opt-in 12-passage GLM / MiMo critic pilot; DeepSeek is saved reference only.

prepare/report/bundle/status are offline. ready/launch/route-check/reconcile are
operator-only network operations; hosted access additionally requires --allow-paid.
"""
import argparse
import copy
from collections import Counter
from datetime import datetime,timezone
import html
import json
from pathlib import Path
import shutil
import zipfile

from . import experiment as ex, text_critic as tc, cloud_critic as cloud
from .common import atomic_json,read_json,sha,fingerprint,files_manifest,writer_lock
from .local_model import LocalClient
from .recovery import response_data,diagnose
from .recovery_trial import verified_parent,save_unit,finish_preview
from .evaluation_export import usage_accounting
from .sciwrite_subset import finding_views

ROOT=Path(__file__).resolve().parents[1]
SAMPLE=('g01-Y','g02-X','g02-Y','g04-Y','g05-X','g05-Y','g07-X','g07-Y','g08-X','g09-X','g09-Y','g10-Y')
GATE=ROOT/'runs/text-critic-followup-trial-20261024T171424Z-8bb3c1'
OVERNIGHT=ROOT/'runs/text-critic-overnight-trial-20261024T211031Z-63fbda'
GLM={**tc.PROFILES['glm'],'max_tokens':32768,'timeout':900,'stream':False,
    'lower_reasoning_supported':False,'sampling':'server defaults omitted','profile':'glm','response_mode':'prompt_schema_local_validation',
    'readiness_calls':2,'readiness_max_tokens':2048}
PROFILES={'glm':GLM,'mimo':cloud.CONFIG,'deepseek':{**tc.PROFILES['deepseek'],'max_tokens':32768,
    'timeout':900,'stream':False,'reference_only':True}}
LIMITS={'baseline_calls':12,'recovery_calls':4,'per_parent_recovery':2,'admission_seconds':28800}
NOTES={
 'g01':'Previously no findings; control, not certified error-free.',
 'g02':'Corrupted/repaired stopping-time notation; external context needs.',
 'g04':'Prior ChatGPT assessment: integrating-factor exponent issue remains in the revised printed-source formula; no correction applied here.',
 'g05':'Prior ChatGPT assessment: spurious derivative dot/tildes corrected by Qwen.',
 'g07':'Prior ChatGPT assessment: missing initial f(B_0,0) term not detected; Y exhausted DeepSeek output allowance.',
 'g08':'DeepSeek output exhaustion in X.',
 'g09':'DeepSeek output exhaustion in X; prior ChatGPT assessment: Y still ends in M(s wedge tau_n) after liminf.',
 'g10':'Context-heavy class-(D) passage; repaired quotation and several prior-assessed low-value warnings.'}
CRITERIA=['Useful material detections','Missed known issues','Harmful suggestions','False alarms',
          'Context handling','First-attempt and repaired technical usability','Time and actual cost']


def metrics(folder,evidence):
    result={k:evidence.get(k) for k in ('actual_model','usage','finish_reason','latency_seconds','http_status')}
    paths=list(Path(folder).glob('attempts/*/response.raw'))
    if len(paths)==1:
        try:raw=read_json(paths[0])
        except (ValueError,OSError):raw={}
        if isinstance(raw,dict):
            result.update(returned_provider=raw.get('provider'),generation_id=raw.get('id'),
                returned_reasoning_control=raw.get('reasoning',raw.get('reasoning_effort')))
    return result


def validate_arm(meta,units):
    profile=meta['config'].get('profile')
    if profile=='mimo':cloud.validate_config(meta['config'])
    elif profile!='glm' or meta['config']!=GLM:raise ValueError('Changed pilot profile')
    if meta['kind']!='critic' or meta['limits']!=LIMITS or [u['id'] for u in units]!=list(SAMPLE):raise ValueError('Changed fixed 12-unit sample/budgets')
    if any(u['kind']!='critic' or u.get('gate') or u.get('unavailable') or u.get('split')!='development' for u in units):raise ValueError('Unexpected pilot stage/availability')
    if meta['critic_pilot'].get('reference_only') is not False:raise ValueError('Invalid trial scope')


def prepare(out,gate=GATE,overnight=OVERNIGHT,*,budget_usd=cloud.DEFAULT_BUDGET_USD):
    profiles={**PROFILES,'mimo':cloud.profile(budget_usd)};budget_usd=profiles['mimo']['budget_usd']
    out=Path(out).resolve();parents=[verified_parent(p,require_recovery_budget=False) for p in (gate,overnight)]
    for r,b,s,p,m,units in parents:
        if m['kind']!='critic' or m['config']['model']!='DeepSeek-V4.1-Flash-TF' or m['config']['max_tokens']!=32768:raise ValueError('Unexpected saved DeepSeek reference')
        if any(int(c['parent'][1:3])>=11 for c in s['calls']):raise ValueError('Unexpected reserved observations; review cohort before preparation')
    found={u['id']:(r,s,p,m,u) for r,b,s,p,m,us in parents for u in us}
    if not set(SAMPLE)<=set(found):raise ValueError('Missing selected historical units')
    out.mkdir(parents=True,exist_ok=False);source_hashes={};refs=[]
    for r,b,s,p,m,us in parents:
        source_hashes.update(m['source_hashes'])
        for folder in (r,p):source_hashes.update({str(folder/e['path']):e['sha256'] for e in files_manifest(folder)})
    for identity in SAMPLE:
        r,s,p,m,u=found[identity];data=read_json(p/u['data']);body=read_json(p/u['request'])
        if body!=tc.request(data,max_tokens=32768):raise ValueError('Saved critic task/schema changed')
        folder=out/'reference'/identity;folder.mkdir(parents=True)
        shutil.copyfile(p/u['data'],folder/'input.json');shutil.copyfile(p/u['request'],folder/'request.json')
        attempts=[]
        for c in s['calls']:
            if c['parent']!=identity:continue
            ev=response_data(r/'calls'/c['id']);outcome=read_json(r/'calls'/c['id']/'outcome.json')
            attempts.append({'call':r.name+'/'+c['id'],'method':c['method'],'source_folder':str(r/'calls'/c['id']),
                'seal_sha256':c['seal_sha256'],'outcome':outcome,
                'metrics':metrics(r/'calls'/c['id'],ev)})
        atomic_json(folder/'attempts.json',attempts)
        refs.append({'id':identity,'source_run':str(r),'source_preview':str(p),'historical_code':m['code_sha256'],
            'input':str((folder/'input.json').relative_to(out)),'input_sha256':sha(folder/'input.json'),'draft_sha256':data['draft_sha256'],
            'status':s['units'][identity]['status'],'version':u['version'],'location':u['location'],
            'prior_ChatGPT_assessment_not_gold':NOTES[identity.split('-')[0]],'human_assessment':None})
    arms={name:{'preview':str(ex.new_path(ROOT,'critic-'+name+'-input')),'run':str(ex.new_path(ROOT,'critic-'+name+'-trial'))} for name in ('glm','mimo')}
    cost_plan=[]
    for identity in SAMPLE:
        _,_,p,_,u=found[identity];body=cloud.body_for(read_json(p/u['request'])['messages'])
        cost_plan.append({'unit':identity,'prompt_token_upper_bound':cloud.token_bound(body),
            'completion_token_cap':32768,'maximum_usd':str(cloud.cost_bound(body))})
    manifest={'created_at':ex.now(),'sample':list(SAMPLE),'groups':8,'profiles':profiles,'arms':arms,'references':refs,
        'cloud_baseline_cost_plan':cost_plan,
        'cloud_baseline_maximum_usd':str(sum((cloud.decimal(x['maximum_usd']) for x in cost_plan),cloud.Decimal(0))),
        'cost_bound_method':'Whole UTF-8 JSON byte count plus 4096 framing tokens; full uncached tariff. Readiness and dynamically sized repairs are separately admitted from the same sealed budget ledger. No truncation or promise that every repair fits.',
        'criteria_frozen_before_live':CRITERIA,'quality':'Independent/human assessment required; no keyword-based accuracy or automatic winner',
        'scope':'Diagnostic challenge set selected partly because DeepSeek struggled; not unbiased book-wide accuracy. No g11–g20 reserved material.',
        'cloud_exception':f'Only these selected text passages to MiMo/Xiaomi, explicit opt-in, approved USD {budget_usd} total including readiness; no cloud conversion/OCR/Gatheral.',
        'public_policy_warning':'User accepts documented provider retention below 100 days for nonpersonal published book material. OpenRouter lists Xiaomi: no training, 30-day retention (https://openrouter.ai/providers, checked 2026-10-25). Retained-data routing explicitly permitted; no ZDR attestation required. No account privacy changes, training opt-in or residency guarantee.',
        'acceptance':'UNACCEPTED','source_hashes':source_hashes,'code_sha256':ex.code_hashes()}
    atomic_json(out/'comparison.json',manifest);ex.seal(out)
    for name,paths in arms.items():
        p=Path(paths['preview']);r=Path(paths['run']);p.mkdir(parents=True);units=[]
        for identity in SAMPLE:
            _,_,old,_,u=found[identity];data=read_json(old/u['data']);original=read_json(old/u['request'])
            body={**original,'model':GLM['model'],'reasoning_effort':'high'} if name=='glm' else cloud.body_for(copy.deepcopy(original['messages']))
            assert body['messages']==original['messages']
            spec=save_unit(p,identity,data,body,kind='critic',gate=False,split='development',version=u['version'],location=u['location'],unavailable=None)
            shutil.copyfile(old/u['data'],p/spec['data']);units.append(spec)
        hashes={**source_hashes,**{str(out/e['path']):e['sha256'] for e in files_manifest(out)}}
        finish_preview(p,units,'critic',profiles[name],hashes,LIMITS,{}, {'sample':list(SAMPLE),'comparison':str(out),'quality_criteria':CRITERIA})
        (p/'manifest.json').unlink();meta=read_json(p/'preview.json');meta['critic_pilot']={'comparison':str(out),'reference_only':False}
        atomic_json(p/'preview.json',meta);ex.seal(p);ex.initialize(p,r)
        atomic_json(r/'readiness-ledger.json',{'binding_sha256':sha(r/'binding.json'),'attempts':[]})
        if name=='mimo':cloud.Ledger(r,create=True)
    return {'comparison':str(out),**arms}


def validate_inheritance(run,preview,meta,state):
    parent=meta['critic_pilot'].get('budget_parent')
    if not parent:return
    inherited=read_json(preview/'inherited-state.json')
    if state['calls'][:len(inherited['calls'])]!=inherited['calls'] or state['elapsed_seconds']<inherited['elapsed_seconds']:
        raise ValueError('Inherited pilot calls/time were reset or changed')
    old=read_json(preview/'inherited-readiness-ledger.json')
    current=read_json(run/'readiness-ledger.json')
    if current['attempts'][:len(old['attempts'])]!=old['attempts']:raise ValueError('Inherited readiness allowance was reset')
    binding=read_json(run/'binding.json')
    if binding.get('inherited_billing')!={'path':str(preview/'inherited-billing.json'),'sha256':sha(preview/'inherited-billing.json')}:
        raise ValueError('Inherited billing link changed')
    cloud.Ledger(run).read()


def reprepare_mimo(comparison,out,*,budget_usd):
    """New budget-bound MiMo derivative; old arms and their reports stay immutable."""
    comparison=Path(comparison).resolve();out=Path(out).resolve();ex.verify_seal(comparison)
    old=read_json(comparison/'comparison.json');ex.InputGuard(old['source_hashes'])
    config=cloud.profile(budget_usd);budget_usd=config['budget_usd']
    if cloud.decimal(budget_usd)<=cloud.decimal(old['profiles']['mimo']['budget_usd']):
        raise ValueError('Explicit budget increase required; never reset a pilot by preparing it again')
    parents={name:verified_parent(paths['run'],require_recovery_budget=False) for name,paths in old['arms'].items()}
    for name,(r,b,s,p,m,u) in parents.items():
        validate_arm(m,u)
        if str(p)!=old['arms'][name]['preview']:raise ValueError('Historical comparison preview differs')
    r,b,s,p,m,units=parents['mimo'];ledger=cloud.Ledger(r).read()
    if ledger['halt']:raise ValueError('Resolve the recorded billing stop before a budget amendment')
    if {**m['config'],'budget_usd':budget_usd}!=config:raise ValueError('Budget refresh cannot change the MiMo request profile')
    # Refresh only the budget/controller, never quietly substitute task/validator code.
    if any(ex.code_hashes().get(n)!=digest for n,digest in m['code_sha256'].items()
           if n not in ('cloud_critic.py','critic_pilot.py','experiment.py')):
        raise ValueError('Task/validator implementation changed; budget refresh cannot rebind it')
    ready=read_json(r/'readiness-ledger.json')
    if ready['binding_sha256']!=sha(r/'binding.json'):raise ValueError('Parent readiness binding changed')
    if {a.name for a in (r/'readiness-attempts').glob('*')}!={a['id'] for a in ready['attempts']}:
        raise ValueError('Parent readiness membership changed')
    for a in ready['attempts']:
        if not a.get('manifest_sha256'):raise ValueError('Unsealed readiness attempt; resolve it before refresh')
        ex.verify_seal(r/'readiness-attempts'/a['id'],a['manifest_sha256'])
    for u in units:
        body=read_json(p/u['request'])
        if body!=cloud.body_for(body['messages']):raise ValueError('Historical request differs from fixed MiMo profile')
    hashes=dict(old['source_hashes'])
    for folder in [comparison]+[folder for rr,bb,ss,pp,mm,uu in parents.values() for folder in (rr,pp)]:
        hashes.update({str(folder/e['path']):e['sha256'] for e in files_manifest(folder)})
    newp=ex.new_path(ROOT,'critic-mimo-input');newr=ex.new_path(ROOT,'critic-mimo-trial')
    lineage={'parent_comparison':str(comparison),'parent_manifest_sha256':sha(comparison/'manifest.json'),
        'parent_mimo_run':str(r),'parent_binding_sha256':sha(r/'binding.json'),'parent_code_sha256':m['code_sha256'],
        'previous_budget_usd':m['config']['budget_usd'],'approved_budget_usd':budget_usd,
        'inherited_calls':len(s['calls']),'inherited_readiness_attempts':len(ready['attempts']),
        'inherited_charge_reservations':len(ledger['reservations']),
        'meaning':'Total cumulative budget, not an additional allowance. No request, token or retry limits changed.'}
    out.mkdir(parents=True,exist_ok=False);shutil.copytree(comparison/'reference',out/'reference')
    manifest=copy.deepcopy(old);manifest.update(created_at=ex.now(),source_hashes=hashes,code_sha256=ex.code_hashes(),
        budget_refresh=lineage,reference_arms=['glm'],report_run=str(newr))
    manifest['arms']['mimo']={'preview':str(newp),'run':str(newr)}
    manifest['profiles']['mimo']=config;manifest['profiles']['glm']['reference_only']=True
    manifest['cloud_exception']=f'User-approved total USD {budget_usd}, including inherited costs and all readiness/failures/repairs. Same twelve selected MiMo/Xiaomi passages only; no fallback, cloud OCR or whole-book upload.'
    manifest['cost_bound_method']='Whole UTF-8 JSON byte count plus 4096 framing tokens; full uncached tariff. All phases and inherited charges share the sealed cumulative budget; no truncation.'
    atomic_json(out/'comparison.json',manifest);ex.seal(out)
    newp.mkdir(parents=True);shutil.copytree(p/'units',newp/'units')
    atomic_json(newp/'inherited-state.json',s);atomic_json(newp/'inherited-billing.json',ledger)
    atomic_json(newp/'inherited-readiness-ledger.json',ready);atomic_json(newp/'budget-lineage.json',lineage)
    hashes={**hashes,**{str(out/e['path']):e['sha256'] for e in files_manifest(out)}}
    finish_preview(newp,units,'critic',config,hashes,LIMITS,m['gate'],read_json(p/'selection.json'))
    (newp/'manifest.json').unlink();meta=read_json(newp/'preview.json')
    meta['critic_pilot']={'comparison':str(out),'reference_only':False,'budget_parent':lineage}
    atomic_json(newp/'preview.json',meta);ex.seal(newp);ex.initialize(newp,newr)
    for folder in ('calls','billing','readiness-attempts'):
        if (r/folder).exists():shutil.copytree(r/folder,newr/folder)
    binding=read_json(newr/'binding.json')
    binding['inherited_billing']={'path':str(newp/'inherited-billing.json'),'sha256':sha(newp/'inherited-billing.json')}
    atomic_json(newr/'binding.json',binding)
    state=copy.deepcopy(s);state.update(binding_sha256=fingerprint(binding),created_at=ex.now(),active_since_epoch=None,
        inheritance={'parent_run':str(r),'parent_binding_sha256':sha(r/'binding.json'),
            'call_ids':[c['id'] for c in s['calls']],'meaning':'Inherited outcomes retain their historical code binding.'})
    if s['status'] not in ('completed','completed_with_failures'):
        state['status']='paused_budget_reprepared' if s['calls'] else 'prepared_offline'
    atomic_json(newr/'state.json',state)
    atomic_json(newr/'readiness-ledger.json',{**ready,'binding_sha256':sha(newr/'binding.json')})
    atomic_json(newr/'billing.json',{**ledger,'binding_sha256':sha(newr/'binding.json'),'ceiling_usd':budget_usd})
    validate_inheritance(newr,newp,meta,state)
    return {'comparison':str(out),**manifest['arms']}


def arm(run):
    run=Path(run).resolve();b=read_json(run/'binding.json');p=Path(b['preview']);m,u=ex.verify_preview(p);validate_arm(m,u)
    s=read_json(run/'state.json')
    if s['binding_sha256']!=fingerprint(b) or b['manifest_sha256']!=sha(p/'manifest.json'):raise ValueError('Changed run binding')
    validate_inheritance(run,p,m,s)
    return run,p,m,u


def factory(run,config,allow_paid=False):
    if config['profile'] in ('glm','deepseek'):return LocalClient
    if not allow_paid:raise ValueError('MiMo requires explicit --allow-paid; a local failure never sends data remotely')
    return lambda *a,**kw:cloud.CloudClient(*a,**kw,run=run)


def ready(run,allow_paid=False,client_factory=None,*,arm_loader=None,readiness_builder=None):
    run,p,m,u=(arm_loader or arm)(run);ex.InputGuard(m['source_hashes']);ex.converter_idle(ROOT)
    state=read_json(run/'state.json')
    if state['active_since_epoch'] is not None:raise ValueError('Writer still active; readiness refused')
    f=client_factory or factory(run,m['config'],allow_paid)
    ledger=read_json(run/'readiness-ledger.json')
    if ledger['binding_sha256']!=sha(run/'binding.json'):raise ValueError('Readiness binding changed')
    attempts=ledger['attempts']
    if len(attempts)>=m['config'].get('readiness_calls',2):raise ValueError('Two readiness calls already reserved or sealed stage allowance exhausted; no reset')
    if {x.name for x in (run/'readiness-attempts').glob('*')}!={a['id'] for a in attempts}:raise ValueError('Readiness attempt ledger changed')
    for a in attempts:
        if a.get('manifest_sha256'):ex.verify_seal(run/'readiness-attempts'/a['id'],a['manifest_sha256'])
    client=f(m['config']['endpoint'],model=m['config']['model'],purpose='text_critic',max_tokens=2048,timeout=120)
    data={'group_id':'ready','spans':[{'block_id':'ready:b0','text':'Let x be a real number. Then x = x.','format':'portable_latex','source_location':{'page':'synthetic readiness'}}],
        'context':{'scope':'harmless synthetic readiness'},'bibliography':{'coverage':'not_applicable'}}
    data['draft_sha256']=tc.draft_hash(data['spans'])
    body=tc.request(data,'glm',max_tokens=2048) if m['config']['profile']=='glm' else cloud.body_for(tc.request(data)['messages'],max_tokens=2048)
    if readiness_builder:data,body=readiness_builder(m['config'])
    # Metadata checks can block WITHOUT consuming a paid generation/readiness reservation.
    if hasattr(client,'check_admission'):client.check_admission(body)
    identity=f'{len(attempts)+1:04d}';dest=run/'readiness-attempts'/identity
    attempts.append({'id':identity,'status':'reserved','request_sha256':fingerprint(body)});atomic_json(run/'readiness-ledger.json',ledger);dest.mkdir(parents=True)
    atomic_json(dest/'request.json',body)
    try:
        discovery=client.discover_model(dest/'discovery')
        if discovery['selected_model']!=m['config']['model']:raise ValueError('Readiness discovery mismatch')
        ans=client.chat(body['messages'],dest,'readiness',response_format=body.get('response_format'),reasoning_effort=body.get('reasoning_effort','server-default'))
        result=ex.finish_completion(ans,{'kind':'critic'},data,m['config']['model'],dest)
        if result['answer']['coverage']!='complete':raise ValueError('Readiness needs complete claimed synthetic coverage')
        atomic_json(dest/'assistant-response.json',ans);atomic_json(dest/'outcome.json',result)
        atomic_json(dest/'readiness.json',{'config':m['config'],'finished_at':ex.now(),'text':'passed','vision':'not_requested_text_only',
            'schema':'actual critic response schema validated locally; MiMo strict schema route fixed, GLM prompt schema only'})
        attempts[-1]['status']='passed'
    except Exception as exc:
        atomic_json(dest/'outcome.json',{'status':'failed','failure':diagnose(exc,response_data(dest),m['config']['model'])})
        attempts[-1]['status']='failed';raise
    finally:
        ex.seal(dest);attempts[-1]['manifest_sha256']=sha(dest/'manifest.json');atomic_json(run/'readiness-ledger.json',ledger)
    print('Readiness:',dest,'Text: passed ; vision: not_requested_text_only',flush=True);return dest


def reference_rows(comparison):
    return read_json(comparison/'comparison.json')['references']


def report(comparison):
    comparison=Path(comparison).resolve();ex.verify_seal(comparison);meta=read_json(comparison/'comparison.json');rows=[];all_attempts={k:[] for k in ('deepseek','glm','mimo')}
    ex.InputGuard(meta['source_hashes'])
    for ref in meta['references']:
        row={'unit':ref['id'],'version':ref['version'],'location':ref['location'],'input':read_json(comparison/ref['input']),
             'prior_ChatGPT_assessment_not_gold':ref['prior_ChatGPT_assessment_not_gold'],'human_assessment':None,'arms':{}}
        old=read_json(comparison/'reference'/ref['id']/'attempts.json')
        row['arms']['deepseek']={'status':ref['status'],'attempts':old,'historical_reference':True}
        for name,paths in meta['arms'].items():
            run=Path(paths['run']);state=read_json(run/'state.json')
            if state['active_since_epoch'] is not None or state['status']=='running':raise ValueError('Stop writer before report/bundle')
            attempts=[]
            for c in state['calls']:
                if c['parent']!=ref['id']:continue
                folder=run/'calls'/c['id'];o=read_json(folder/'outcome.json') if (folder/'outcome.json').exists() else {'status':'in_flight_unknown'}
                ev=response_data(folder)
                attempts.append({'call':name+'/'+c['id'],'method':c['method'],'outcome':o,
                    'origin':'inherited' if name in meta.get('reference_arms',[]) or c['id'] in state.get('inheritance',{}).get('call_ids',[]) else 'current_run',
                    'metrics':metrics(folder,ev)})
            row['arms'][name]={'status':state['units'][ref['id']]['status'],'attempts':attempts,'historical_reference':name in meta.get('reference_arms',[])}
        for name,item in row['arms'].items():
            all_attempts[name]+=[{'call':a['call'],'method':a['method'],**a['outcome'],
                'origin':a.get('origin','inherited' if name=='deepseek' else 'current_run')} for a in item['attempts']]
            latest=item['attempts'][-1]['outcome'] if item['attempts'] else {}
            item['final_views']=finding_views(latest.get('findings',[]))
            item['context_requests']=latest.get('answer',{}).get('context_needed',[])
        rows.append(row)
    summary={}
    for name in all_attempts:
        entries=[r['arms'][name] for r in rows]
        summary[name]={'planned_units':12,'selected_groups':8,'paired_groups':4,'singleton_groups':4,
            'configured_profile':meta['profiles'][name],
            'reasoning_evidence':'Requested controls are recorded; usage counters do not prove the backend honoured a graded effort. Missing counters remain unknown.',
            'statuses':dict(Counter(e['status'] for e in entries)),
            'first_attempt_valid':sum(bool(e['attempts']) and e['attempts'][0]['outcome']['status']=='completed' for e in entries),
            'final_valid':sum(e['status']=='completed' for e in entries),
            'recovery_assisted_valid':sum(e['status']=='completed' and len(e['attempts'])>1 for e in entries),
            'usage':usage_accounting(all_attempts[name]),'quality':'unassessed; quoted finding is not verified mathematical correctness'}
        if name!='deepseek':
            r=Path(meta['arms'][name]['run']);s=read_json(r/'state.json');summary[name]['elapsed_seconds']=s['elapsed_seconds']
            summary[name]['readiness_attempts']=read_json(r/'readiness-ledger.json')['attempts']
    summary['mimo']['cost']=cloud.Ledger(Path(meta['arms']['mimo']['run'])).summary()
    dest=Path(meta.get('report_run',meta['arms']['glm']['run']))/'comparison-report';dest.mkdir(exist_ok=True)
    atomic_json(dest/'comparison.json',{'summary':summary,'rows':rows,'criteria':meta['criteria_frozen_before_live'],
        'scope':meta['scope'],'cloud_policy_warning':meta['public_policy_warning'],'acceptance':'UNACCEPTED'})
    text='# GLM / MiMo / saved DeepSeek critic comparison\n\n'+meta['scope']+'\n\n'+meta['public_policy_warning']+'\n\n'
    text+='MinerU supplied OCR; Qwen supplied visual proposals; the saved experimental candidate retains unresolved content. Critics receive only the same neutral text passages. No automatic acceptance, scoring or winner. Prior ChatGPT assessments are not human gold.\n\n'
    text+='| Unit | Original/revised | PDF | DeepSeek | GLM | MiMo |\n|---|---|---|---|---|---|\n'
    for r in rows:text+='| '+ ' | '.join([r['unit'],r['version'],str(r['location']['page'])]+[r['arms'][n]['status'] for n in ('deepseek','glm','mimo')])+' |\n'
    text+='\n```json\n'+json.dumps(summary,indent=2)+'\n```\n'
    (dest/'report.md').write_text(text)
    columns=''
    for r in rows:
        columns+='<h2>'+html.escape(r['unit']+' / '+r['version']+' / PDF '+str(r['location']['page']))+'</h2><details><summary>Exact passage / locations</summary><pre>'+html.escape(json.dumps(r['input'],ensure_ascii=False,indent=2))+'</pre></details>'
        columns+='<p>Prior ChatGPT assessment, not gold: '+html.escape(r['prior_ChatGPT_assessment_not_gold'])+'</p><div class="arms">'
        for n,a in r['arms'].items():columns+='<section><h3>'+n+'</h3><pre>'+html.escape(json.dumps(a,ensure_ascii=False,indent=2))+'</pre></section>'
        columns+='</div>'
    (dest/'report.html').write_text('<!doctype html><meta charset="utf-8"><style>.arms{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1em}pre{white-space:pre-wrap;overflow-wrap:anywhere}section{border:1px solid #999;padding:1em}</style><pre>'+html.escape(text)+'</pre>'+columns)
    return dest


def bundle(comparison):
    comparison=Path(comparison).resolve();dest=report(comparison);meta=read_json(comparison/'comparison.json')
    zip_path=ROOT/'results'/(ex.new_path(ROOT,'critic-glm-mimo-inspection').name+'.zip')
    with zipfile.ZipFile(zip_path,'x',zipfile.ZIP_DEFLATED) as z:
        for e in files_manifest(dest):z.write(dest/e['path'],e['path'])
        for e in files_manifest(comparison):z.write(comparison/e['path'],'preparation/'+e['path'])
        for name,paths in meta['arms'].items():
            p=Path(paths['preview']);run=Path(paths['run'])
            for e in files_manifest(p):z.write(p/e['path'],name+'/prepared/'+e['path'])
            for n in ('state.json','binding.json','billing.json','readiness-ledger.json'):
                if (run/n).exists():z.write(run/n,name+'/'+n)
            for folder in ('calls','readiness-attempts','billing'):
                for path in (run/folder).rglob('*.json'):
                    if path.name in ('request.json','outcome.json','record.json','reservation.json','settlement.json','readiness.json'):
                        z.write(path,name+'/'+str(path.relative_to(run)))
    with zipfile.ZipFile(zip_path) as z:
        if z.testzip():raise ValueError('Inspection ZIP failed CRC')
    record={'path':str(zip_path),'bytes':zip_path.stat().st_size,'sha256':sha(zip_path),'report':str(dest/'report.html')}
    atomic_json(Path(meta.get('report_run',meta['arms']['glm']['run']))/'comparison-latest-bundle.json',record);print(json.dumps(record,indent=2));return record


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--budget-usd',default=cloud.DEFAULT_BUDGET_USD,
        help='Explicit approved total USD ceiling, sealed at preparation (default: %(default)s)')
    p=sub.add_parser('reprepare-mimo');p.add_argument('--comparison',required=True,type=Path)
    p.add_argument('--budget-usd',required=True,help='New explicitly approved total, not additional spending')
    for name in ('ready','launch','status','route-check','reconcile'):
        p=sub.add_parser(name);p.add_argument('--run',required=True,type=Path)
        if name in ('ready','launch','route-check','reconcile'):p.add_argument('--allow-paid',action='store_true')
        if name=='launch':p.add_argument('--readiness',required=True,type=Path);p.add_argument('--resume',action='store_true')
    for name in ('report','bundle'):
        p=sub.add_parser(name);p.add_argument('--comparison',required=True,type=Path)
    a=parser.parse_args(argv)
    if a.command=='status':
        s=read_json(a.run/'state.json');print(json.dumps({k:s[k] for k in ('status','elapsed_seconds','active_since_epoch','units')},indent=2))
        if (a.run/'billing.json').exists():print(json.dumps(cloud.Ledger(a.run).summary(),indent=2))
        return 0
    with writer_lock(ROOT/'runs'):
        if a.command=='prepare':
            out=ex.new_path(ROOT,'critic-glm-mimo-input');paths=prepare(out,budget_usd=a.budget_usd);paths['inspection_bundle']=bundle(out)
            atomic_json(ROOT/'results/critic-glm-mimo-current.json',paths);print(json.dumps(paths,indent=2));return 0
        if a.command=='reprepare-mimo':
            out=ex.new_path(ROOT,'critic-glm-mimo-input');paths=reprepare_mimo(a.comparison,out,budget_usd=a.budget_usd);paths['inspection_bundle']=bundle(out)
            atomic_json(ROOT/'results/critic-glm-mimo-current.json',paths);print(json.dumps(paths,indent=2));return 0
        if a.command=='report':print(report(a.comparison));return 0
        if a.command=='bundle':bundle(a.comparison);return 0
        run,p,m,u=arm(a.run)
        if a.command=='ready':ready(run,a.allow_paid);return 0
        f=factory(run,m['config'],a.allow_paid)
        if a.command in ('route-check','reconcile'):
            if m['config']['profile']!='mimo':raise ValueError('Only the explicit MiMo profile has remote routing/costs')
            client=f(m['config']['endpoint'],model=m['config']['model'],purpose='text_critic',max_tokens=32768,timeout=900)
            if a.command=='route-check':
                client.check_admission(read_json(p/u[0]['request']));print(f'Pinned MiMo route / rates / schema metadata / dedicated USD {m["config"]["budget_usd"]} key checks passed; published Xiaomi 30-day retention accepted. No ZDR lookup or inference requested.')
            else:print(json.dumps(client.reconcile_costs(),indent=2))
            return 0
        try:return ex.execute(ROOT,run,stage='pilot',readiness=a.readiness.resolve(),resume=a.resume,client_factory=f)
        finally:
            s=read_json(run/'state.json')
            if s['active_since_epoch'] is None and s['status']!='running':bundle(Path(m['critic_pilot']['comparison']))


if __name__=='__main__':
    try:raise SystemExit(main())
    except (cloud.AdmissionError,ValueError) as exc:raise SystemExit(str(exc)) from None
