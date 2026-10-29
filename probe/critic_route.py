"""Candidate-only GLM-first critic and explicit, selected MiMo second opinion.

Preparation/selection/cost/report/bundle/status are offline. run/ready/launch are
operator-only inference commands. Reuses experiment, pilot readiness and cloud ledger.
"""
import argparse
import copy
from collections import Counter
from decimal import Decimal
import html
import json
from pathlib import Path
import random
import re
import shutil
import zipfile

from . import experiment as ex, text_critic as tc, critic_anchors as ca, critic_context as ctx
from . import critic_pilot as pilot, cloud_critic as cloud
from .common import atomic_json,read_json,sha,fingerprint,files_manifest,writer_lock
from .batch_review import IntegrityError
from .recovery_trial import save_unit,finish_preview,verified_parent
from .recovery import feedback_request,recovery_method
from .evaluation_export import draft,usage_accounting
from .sciwrite_subset import finding_views,compare_findings

ROOT=Path(__file__).resolve().parents[1]
VERSION='candidate-critic-route-v1'
LOCAL_LIMITS={'baseline_calls':8,'recovery_calls':8,'per_parent_recovery':2,'admission_seconds':14400}
SELECT_POLICY={'max_passages':4,'recovery_calls':2,'per_parent_recovery':2,'readiness_calls':1,
 'admission_seconds':7200,'clean_sample':1,'seed':20261025,'planning_margin':1.5}


def local_config(profile='glm'):
    return {**tc.PROFILES[profile],'max_tokens':32768,'timeout':900,'stream':False,
        'lower_reasoning_supported':False,'sampling':'server defaults omitted','profile':profile,
        'readiness_calls':2,'readiness_max_tokens':2048,'critic_protocol':ca.CURRENT_VERSION,
        'reasoning_support':'Requested documented profile; actual backend interpretation not established',
        'request_byte_limit':ca.MAX_INPUT_BYTES}


def paid_config(count):
    return {**cloud.profile('10.00'),'critic_protocol':ca.CURRENT_VERSION,'paid_limits':{'trial_calls':count+2,'readiness_calls':1},
        'readiness_calls':1,'request_byte_limit':ca.MAX_INPUT_BYTES}


def candidate_rows(candidate):
    candidate=Path(candidate).resolve();ex.verify_seal(candidate)
    rows=read_json(candidate/'inventory.json');prov=read_json(candidate/'provenance.json')
    ex.InputGuard(prov['bindings'])
    if len({r['block_id'] for r in rows})!=len(rows):raise IntegrityError('Duplicate candidate inventory block')
    for r in rows:
        if fingerprint(r['after'])!=r['draft_sha256']:raise IntegrityError('Candidate block text hash changed')
    version=fingerprint({'candidate_manifest':sha(candidate/'manifest.json'),'candidate_tex':sha(candidate/'candidate.tex'),
        'inventory':sha(candidate/'inventory.json')})
    return candidate,rows,prov,version


def prepare_index(candidate,conversion,source):
    from .saved_pages import saved_pages
    candidate,rows,prov,version=candidate_rows(candidate)
    conversion=Path(conversion).resolve();pages=saved_pages(ROOT,conversion,source)
    byid={r['block_id']:r for r in rows};seen=set();spans=[]
    hashes={str(candidate/e['path']):e['sha256'] for e in read_json(candidate/'manifest.json')}
    hashes[str(candidate/'manifest.json')]=sha(candidate/'manifest.json')
    hashes.update({str(conversion/'state.json'):sha(conversion/'state.json')})
    setting=read_json(conversion/'state.json')['settings']['sources'][source]
    hashes[str((ROOT/setting['pdf']).resolve())]=setting['sha256']
    identity={'source_id':source,'prepared_pdf_sha256':setting['sha256'],'original_pages':setting['original_pages'],
        'candidate_sha256':version,'source_manifest':setting.get('manifest')}
    if setting.get('manifest'):
        path=ROOT/setting['manifest'];hashes[str(path.resolve())]=sha(path)
        identity['preparation_manifest']=read_json(path)
    for p in sorted(pages,key=lambda p:p['page']['selected_page']):
        attempt=conversion/p['source_attempt']
        for name in ('page-map.json','output/middle_json.json'):
            hashes[str(attempt/name)]=sha(attempt/name)
        for b in p['blocks']:
            row=byid.get(b['id']);original=draft(b)
            if row and (row['source_block_sha256']!=fingerprint(b) or row['source_location']['source_id']!=source):
                raise IntegrityError('Candidate belongs to different source block/edition')
            seen.add(b['id']);text=row['after'] if row else original['text']
            spans.append({'block_id':b['id'],'kind':b['kind'],'text':text,'source_block_sha256':fingerprint(b),
                'format':'portable_latex' if (row and row['status']!='unresolved') or (not row and original['export_status']=='supported') else 'complete_structured_OCR_JSON',
                'basis':'current_candidate' if row else 'saved_OCR_context_unverified',
                'unresolved':row['status']=='unresolved' if row else original['export_status']=='unresolved',
                'source_location':{'source_id':source,'page':p['page'],'bbox':b['bbox'],'reading_order':b['reading_order']}})
    if set(byid)-seen:raise IntegrityError('Candidate inventory not contained in selected saved source')
    index=ctx.build_index(spans,identity)
    return candidate,rows,prov,version,index,hashes


def boundary_template(candidate,out):
    candidate,rows,prov,version=candidate_rows(candidate)
    pages={}
    for r in rows:pages.setdefault(r['page_id'],[]).append(r['block_id'])
    record={'schema':'candidate-passages-v1','candidate':str(candidate),'candidate_manifest_sha256':sha(candidate/'manifest.json'),
        'candidate_sha256':version,'boundary_status':'unresolved_edit_required','passages':[],
        'available_page_blocks':pages,'instructions':'Select coherent theorem/hypotheses/proof or derivation boundaries explicitly, in reading order. Do not infer sentence splits. Account for unselected/unresolved blocks separately.'}
    if Path(out).exists():raise ValueError('Boundary manifest already exists')
    atomic_json(out,record);return record


def anchor_row(row,version,role):
    return ca.anchor(version,row['block_id'],row['source_block_sha256'],row['text'],
        {**row['source_location'],'text_basis':row['basis'],'format':row['format']},role)


def make_data(group,targets,index,version,explicit_context=()):
    refs=list(dict.fromkeys([*explicit_context,*ctx.explicit_references('\n'.join(r['text'] for r in targets))]))
    rows,records=ctx.resolve(index,refs,[r['block_id'] for r in targets])
    anchors=[anchor_row(r,version,'target') for r in targets]
    return {'protocol':ca.CURRENT_VERSION,'group_id':group,'candidate_sha256':version,'draft_sha256':fingerprint(anchors),
        'targets':anchors,'context_anchors':[anchor_row(r,version,'context') for r in rows],
        'context_status':records,'bibliography':{'coverage':index['bibliography']['coverage'],
            'source_identity':{k:v for k,v in index['source_identity'].items() if k not in ('preparation_manifest','original_pages')},
            'consultation':'No external sources consulted; supplied citations remain exact. Local lookup is partial.'}}


def validate_protocol(meta,units):
    route=meta.get('critic_route',{});config=meta['config'];limits=meta['limits']
    if route.get('version')!=VERSION or meta['kind']!='critic' or not units:raise IntegrityError('Unknown candidate route protocol')
    if route.get('context_policy')!=ctx.POLICY:raise IntegrityError('Changed bounded local context policy')
    if config['profile']=='mimo':
        cloud.validate_config(config)
        shared=route['shared_accounting']
        seconds=min(7200,max(0,int(shared['original_limits']['admission_seconds']-shared['local_elapsed_seconds'])))
        if not 1<=len(units)<=4 or limits!={'baseline_calls':len(units),'recovery_calls':2,'per_parent_recovery':2,'admission_seconds':seconds}:
            raise IntegrityError('Selected paid stage exceeds calibration limits')
        if config!=paid_config(len(units)):raise IntegrityError('Paid stage profile differs')
    else:
        if config['profile'] not in ('glm','deepseek') or config!=local_config(config['profile']):raise IntegrityError('Changed local critic profile')
        policy=route.get('escalation_policy',{})
        if (set(policy)!=set(SELECT_POLICY) or any(policy.get(k)!=v for k,v in SELECT_POLICY.items() if k not in ('clean_sample','seed','planning_margin'))
            or type(policy['seed']) is not int or type(policy['clean_sample']) is not int or not 0<=policy['clean_sample']<=4
            or not 1<=policy['planning_margin']<=10):raise IntegrityError('Changed escalation selection policy')
    if (set(limits)!=set(LOCAL_LIMITS) or any(type(x) is not int or x<0 for x in limits.values())
        or limits['baseline_calls']!=len(units) or limits['per_parent_recovery']!=2
        or limits['recovery_calls']>2*len(units) or not 0<limits['admission_seconds']<=28800):
        raise IntegrityError('Invalid sealed critic call/time limits')
    if len({u['id'] for u in units})!=len(units) or any(u['kind']!='critic' or u.get('gate') for u in units):raise IntegrityError('Invalid candidate-only units')


def validate_linked(run,preview,meta,state):
    route=meta['critic_route'];binding=read_json(run/'binding.json')
    for previous in route.get('superseded_unused_preparations',[]):
        ex.verify_seal(Path(previous['preview']),previous['manifest_sha256'])
    if meta['config']['profile']=='mimo':
        expected={'path':str(preview/'prior-billing.json'),'sha256':sha(preview/'prior-billing.json')}
        if binding.get('prior_billing')!=expected:raise IntegrityError('Prior paid accounting link changed')
        cloud.Ledger(run).read()
        local=Path(route['local_run']);old=read_json(local/'state.json')
        used={u:sum(c['parent']==u and c['method']!='baseline' for c in old['calls']) for u in state['units']}
        if used!=route['local_recovery_by_parent']:raise IntegrityError('Inherited local recovery accounting changed')
        for unit,count in used.items():
            if count+sum(c['parent']==unit for c in state['calls'])>2:raise IntegrityError('Original passage follow-up allowance reset')
        shared=route['shared_accounting']
        if (shared['local_recovery_calls']!=sum(c['method']!='baseline' for c in old['calls'])
            or shared['local_elapsed_seconds']!=old['elapsed_seconds']
            or shared['original_limits']!=read_json(local/'binding.json')['limits']):raise IntegrityError('Inherited global accounting changed')
        if shared['local_recovery_calls']+len(state['calls'])>shared['original_limits']['recovery_calls']:
            raise IntegrityError('Original shared global follow-up ceiling reset')
    inherited=route.get('inherited_local_state')
    if inherited:
        old=read_json(preview/inherited);count=len(old['calls'])
        if state['calls'][:count]!=old['calls'] or state['elapsed_seconds']<old['elapsed_seconds']:raise IntegrityError('Inherited local allowances reset')


def arm(run):
    run=Path(run).resolve();b=read_json(run/'binding.json');preview=Path(b['preview']);m,u=ex.verify_preview(preview)
    validate_protocol(m,u);s=read_json(run/'state.json')
    if s['binding_sha256']!=fingerprint(b) or b['manifest_sha256']!=sha(preview/'manifest.json'):raise IntegrityError('Changed route binding')
    if b['config']!=m['config'] or b['limits']!=m['limits']:raise IntegrityError('Changed route settings')
    validate_linked(run,preview,m,s)
    return run,preview,m,u


def finalize(preview,run,units,config,hashes,limits,selection,route):
    finish_preview(preview,units,'critic',config,hashes,limits,{},selection)
    (preview/'manifest.json').unlink();meta=read_json(preview/'preview.json');meta.update(protocol=ca.CURRENT_VERSION,critic_route=route)
    atomic_json(preview/'preview.json',meta);validate_protocol(meta,units);ex.seal(preview);ex.initialize(preview,run)
    if config['profile']=='mimo':
        b=read_json(run/'binding.json');b['prior_billing']={'path':str(preview/'prior-billing.json'),'sha256':sha(preview/'prior-billing.json')}
        atomic_json(run/'binding.json',b);state=read_json(run/'state.json');state['binding_sha256']=fingerprint(b);atomic_json(run/'state.json',state)
        cloud.Ledger(run,create=True)
    atomic_json(run/'readiness-ledger.json',{'binding_sha256':sha(run/'binding.json'),'attempts':[]})
    report(run)
    return {'preview':str(preview),'run':str(run)}


def prepare(candidate,conversion,source,passages,*,profile='glm',recovery_calls=8,hours=4,clean_sample=1,selection_seed=20261025,planning_margin=1.5):
    candidate,rows,prov,version,index,hashes=prepare_index(candidate,conversion,source)
    selection=read_json(passages)
    if (selection.get('schema')!='candidate-passages-v1' or selection.get('candidate_manifest_sha256')!=sha(candidate/'manifest.json')
        or selection.get('candidate_sha256')!=version or selection.get('boundary_status')!='reviewed'):
        raise IntegrityError('Stale/unreviewed passage boundary manifest')
    groups=selection['passages'];positions={b:i for i,b in enumerate(index['order'])};available={r['block_id']:r for r in rows};covered=[];units=[]
    if not groups or len({g['id'] for g in groups})!=len(groups):raise ValueError('Invalid explicit passage selection')
    if not 0<=clean_sample<=4 or type(selection_seed) is not int or not 1<=planning_margin<=10:raise ValueError('Invalid frozen escalation sampling/cost policy')
    limits={'baseline_calls':len(groups),'recovery_calls':recovery_calls,'per_parent_recovery':2,'admission_seconds':int(hours*3600)}
    config=local_config(profile);preview=ex.new_path(ROOT,'candidate-critic-input');run=ex.new_path(ROOT,'candidate-critic-trial')
    # Refuse duplicate executions of the same protocol/cohort. Resume the existing run.
    policy={**SELECT_POLICY,'clean_sample':clean_sample,'seed':selection_seed,'planning_margin':planning_margin}
    cohort=fingerprint([version,selection,config,limits,policy])
    unused=[]
    for path in (ROOT/'runs').glob('candidate-critic-input-*/preview.json'):
        old=read_json(path)
        if old.get('critic_route',{}).get('cohort')!=cohort:continue
        if old['code_sha256']==ex.code_hashes():raise ValueError('Identical preparation already exists; use its recorded run: '+str(path.parent))
        ex.verify_seal(path.parent)
        bound=[p.parent for p in (ROOT/'runs').glob('candidate-critic-trial-*/binding.json') if read_json(p)['preview']==str(path.parent)]
        if len(bound)!=1:raise IntegrityError('Prior cohort has no unique run; do not reset allowances')
        previous=bound[0];state=read_json(previous/'state.json');ledger=read_json(previous/'readiness-ledger.json')
        if state['status']!='prepared_offline' or state['calls'] or state['elapsed_seconds'] or ledger['attempts']:
            raise IntegrityError('Changed-code cohort has consumed attempts/time; explicit continuation preserving allowances is required')
        verified_parent(previous,require_recovery_budget=False)
        if any((previous/'readiness-attempts').glob('*/')):raise IntegrityError('Unregistered prior readiness evidence; do not reset allowances')
        unused.append({'preview':str(path.parent),'run':str(previous),'code_sha256':old['code_sha256'],
            'reason':'Supersedes unused preparation after implementation change; zero calls, readiness and consumed time',
            'manifest_sha256':sha(path.parent/'manifest.json')})
        for file in (path.parent/'manifest.json',previous/'binding.json',previous/'state.json',previous/'readiness-ledger.json'):
            hashes[str(file)]=sha(file)
    preview.mkdir(parents=True);atomic_json(preview/'context-index.json',index)
    for g in groups:
        ids=g['block_ids']
        if not re.fullmatch(r'[a-zA-Z0-9_-]+',g['id']) or not ids or len(set(ids))!=len(ids) or set(ids)-set(available):raise ValueError('Unknown/duplicate passage block')
        if ids!=sorted(ids,key=lambda b:positions[b]):raise ValueError('Passage blocks must retain source reading order')
        if set(ids)&set(covered):raise ValueError('Target block appears in multiple passages; context overlap must be explicit')
        if not g.get('boundary_reviewed') or not g.get('boundary_basis'):raise ValueError('Unresolved coherent passage boundary')
        covered+=ids;targets=[index['rows'][b] for b in ids]
        data=make_data(g['id'],targets,index,version,g.get('context_references',[]));body=ca.request(data,config)
        missing=[b for b in ids if available[b]['status']=='unresolved' or available[b].get('review_status')!='completed']
        units.append(save_unit(preview,g['id'],data,body,kind='critic',gate=False,version='candidate',
            location={'blocks':ids,'pages':sorted({available[b]['source_location']['page']['original_physical_page'] for b in ids})},
            unavailable='Unresolved candidate/visual review blocks: '+', '.join(missing) if missing else None))
    coverage={'target_blocks':covered,'candidate_blocks':len(rows),'outside_selected_scope':[r['block_id'] for r in rows if r['block_id'] not in covered],
        'unresolved_candidate_blocks':[r['block_id'] for r in rows if r['status']=='unresolved'],
        'meaning':'Only explicit target blocks; context never counts as reviewed. No source-image omissions or whole-book claim.'}
    atomic_json(preview/'coverage.json',coverage)
    hashes[str(Path(passages).resolve())]=sha(passages)
    return finalize(preview,run,units,config,hashes,limits,selection,
        {'version':VERSION,'candidate':str(candidate),'candidate_sha256':version,'context_policy':ctx.POLICY,
         'cohort':cohort,'mode':'candidate_only',
         'superseded_unused_preparations':unused,
         'escalation_policy':policy,
         'routing':'Local critic only; paid second opinion needs a new explicit selection and --allow-paid.'})


def readiness_input(config):
    a=ca.anchor(fingerprint('synthetic'), 'ready:b0',fingerprint('synthetic source'),'Let x be a real number. Then x = x.',{'page':'synthetic readiness'})
    data={'protocol':ca.CURRENT_VERSION,'group_id':'ready','candidate_sha256':a['candidate_sha256'],'draft_sha256':fingerprint([a]),
        'targets':[a],'context_anchors':[],'context_status':[],'bibliography':{'coverage':'not_applicable'}}
    return data,ca.request(data,{**config,'max_tokens':2048})


def next_request(preview,out,meta,spec,state):
    calls=[c for c in state['calls'] if c['parent']==spec['id']]
    if not calls:return read_json(preview/spec['request']),read_json(preview/spec['data']),'baseline',None
    last=calls[-1];folder=out/'calls'/last['id'];outcome=read_json(folder/'outcome.json')
    data=read_json(folder/'input.json');body=read_json(folder/'request.json')
    if outcome['status']=='completed':
        value=outcome['answer']
        requests=list(value['context_needed'])
        for f in value['findings']:
            requests.extend({'reference':r,'reason':f['consequence'],'anchor_ids':f['anchor_ids']} for r in f['context_required'])
        if not requests or any(c['method']=='context_reassessment' for c in calls):return None
        index=read_json(preview/'context-index.json');already=[a['block_id'] for a in data['targets']+data['context_anchors']]
        policy=meta['critic_route']['context_policy']
        budget={**policy,'max_blocks':max(0,policy['max_blocks']-len(data['context_anchors'])),
            'max_characters':max(0,policy['max_characters']-sum(len(a['text']) for a in data['context_anchors']))}
        rows,records=ctx.resolve(index,requests,already,budget)
        atomic_json(out/'context-decisions'/f"{spec['id']}-{last['id']}.json",records)
        if not rows:return None
        data=copy.deepcopy(data);data['context_anchors'] += [anchor_row(r,data['candidate_sha256'],'context') for r in rows]
        data['context_status']+=records
        body=ca.request(data,meta['config'])
        body['messages'].append({'role':'user','content':'Reassess the same targets with the newly supplied exact local context. Previous assessment is unverified; retain, revise or withdraw claims explicitly in your explanation as warranted. No edit is authorized.\n'+json.dumps({'previous_assessment':value,'added_context':records},ensure_ascii=False)})
        try:ca.bounded(body)
        except ValueError:
            atomic_json(out/'context-decisions'/f"{spec['id']}-{last['id']}-deferred.json",{'reason':'Full context reassessment exceeds request bound; no clipping'});return None
        return body,data,'context_reassessment',None
    fail=outcome.get('failure')
    if not fail:return None
    if len(calls)>1:
        previous=read_json(out/'calls'/calls[-2]['id']/'outcome.json').get('failure',{})
        if (fail.get('kind'),fail.get('content'),fail.get('errors'))==(previous.get('kind'),previous.get('content'),previous.get('errors')):return None
    method=recovery_method(fail,meta['config'],[c['method'] for c in calls])
    if method!='json_feedback':return None  # No identical exhaustion retry or unverified effort change.
    if data['protocol']==ca.CURRENT_VERSION:
        body=ca.field_repair_request(body,fail,data)
        if body is None:return None
    else:body=feedback_request(body,fail,ca.schema_for(data),method)
    try:ca.bounded(body)
    except ValueError:return None
    return body,data,method,fail


def check_parent_budget(meta,state,parent,method):
    paid=meta['config']['profile']=='mimo'
    if method=='baseline' and not paid:return
    inherited=meta['critic_route'].get('local_recovery_by_parent',{}).get(parent,0)
    if inherited+sum(c['parent']==parent and (paid or c['method']!='baseline') for c in state['calls'])>=2:
        raise ValueError('Original passage shared follow-up ceiling exhausted, including inherited local calls')
    if paid:
        shared=meta['critic_route']['shared_accounting']
        if shared['local_recovery_calls']+len(state['calls'])>=shared['original_limits']['recovery_calls']:
            raise ValueError('Original shared global follow-up ceiling exhausted, including local calls')


def report(run,*,report_dir=None):
    run=Path(run).resolve();binding=read_json(run/'binding.json');preview=Path(binding['preview'])
    meta=read_json(preview/'preview.json');state=read_json(run/'state.json');units=read_json(preview/'units.json')
    dest=Path(report_dir) if report_dir else run;dest.mkdir(exist_ok=True)
    rows=[];findings=[];technical=[];context=[];visual=[];all_calls=[]
    for u in units:
        rec=state['units'][u['id']];attempts=[]
        for c in state['calls']:
            if c['parent']!=u['id']:continue
            folder=run/'calls'/c['id'];outcome=read_json(folder/'outcome.json') if (folder/'outcome.json').exists() else {'status':'in_flight_unknown'}
            attempts.append({'call':c['id'],'method':c['method'],**outcome});all_calls.append(attempts[-1])
        latest=attempts[-1] if attempts else {};data=read_json(preview/u['data'])
        if attempts and (run/'calls'/latest['call']/'input.json').exists():data=read_json(run/'calls'/latest['call']/'input.json')
        for attempt in reversed(attempts):
            current=attempt.get('findings',[]) if attempt.get('status')=='completed' else [x['finding'] for x in attempt.get('provisional_diagnostics',{}).get('validated_findings',[])]
            origin=('final' if attempt.get('status')=='completed' else 'provisional_rejected') if attempt is latest else 'historical_superseded_no_current_completion_credit'
            findings +=[{**f,'call':attempt['call'],'unit':u['id'],'origin':origin} for f in current]
        for extra in latest.get('field_repair',{}).get('retained_extra_fields',[]):
            context.append({'unit':u['id'],'call':latest['call'],'status':'retained_extra_commentary_requires_review','commentary':extra})
        for need in ctx.deduplicate_requests(latest.get('answer',{}).get('context_needed',[])):context.append({'unit':u['id'],'call':latest['call'],'request':need,'status':'unresolved unless reassessed with sufficient evidence'})
        if latest.get('answer',{}).get('coverage') in ('incomplete','insufficient_context') and not latest.get('answer',{}).get('context_needed'):
            context.append({'unit':u['id'],'status':'coverage gap'})
        if rec.get('limits'):context.append({'unit':u['id'],'status':'followup_limit','diagnostic':rec['limits']})
        if rec['status'] in ('failed','interrupted','pending','in_flight_unknown'):
            technical.append({'unit':u['id'],'status':rec['status'],'failure':latest.get('failure'),'limits':rec.get('limits'),
                'next_strategy':'No identical retry. Explicit selective second opinion or reviewed coherent smaller boundaries; no unverified reasoning control.'})
        if rec['status']=='unavailable':visual.append({'unit':u['id'],'reason':rec.get('reason')})
        decisions=[]
        for path in (run/'context-decisions').glob(u['id']+'-*.json'):decisions.append(read_json(path))
        rows.append({'unit':u['id'],'status':rec['status'],'final_assessment':latest.get('assessment'),
            'data':data,'attempts':attempts,'context_retrieval':decisions,'limits':rec.get('limits'),
            'technical_validity':latest.get('response_validation','not_passed'),
            'reported_target_coverage':latest.get('answer',{}).get('reviewed_anchor_ids',[]),
            'context_sufficiency':'unresolved' if latest.get('assessment')=='insufficient_context' else 'model_assessment_only',
            'retained_extra_commentary':latest.get('field_repair',{}).get('retained_extra_fields',[]),
            'final_call':rec.get('last_call'),'scope':u['location']})
    coverage=read_json(preview/'coverage.json')
    reviewed=[]
    for row in rows:
        final=row['attempts'][-1] if row['attempts'] else {}
        if row['status']=='completed':
            ids=set(final.get('answer',{}).get('reviewed_anchor_ids',[]))
            reviewed += [a['block_id'] for a in row['data']['targets'] if a['id'] in ids]
    coverage={**coverage,'reported_reviewed_target_blocks':reviewed,
        'unchecked_target_blocks':[b for b in coverage['target_blocks'] if b not in reviewed],
        'reviewed_meaning':'Model-reported target inspection in technically valid final responses; not verified mathematical fidelity'}
    visual +=[{'block_id':b,'reason':'Unresolved candidate assembly, complete raw OCR/source references retained in candidate inventory'} for b in coverage.get('unresolved_candidate_blocks',[])]
    views=finding_views([f for f in findings if f['origin']!='historical_superseded_no_current_completion_credit']);queues={'material':views['material'],'context':views['context']+context,
        'visual_or_assembly':views['visual']+visual,'technical':technical,'editorial':views['editorial'],'positive_observations':views['positive']}
    summary={'status':state['status'],'protocol':meta.get('protocol',ca.VERSION),'candidate_sha256':meta['critic_route']['candidate_sha256'],
        'profile':meta['config'],'requested_reasoning':'Requested settings only; reported token counters do not prove backend interpretation',
        'passage_statuses':dict(Counter(r['status'] for r in rows)),
        'final_assessments':dict(Counter(r['final_assessment'] or r['status'] for r in rows)),
        'calls':len(state['calls']),'elapsed_seconds':state['elapsed_seconds'],'limits':meta['limits'],
        'usage':usage_accounting(all_calls),'coverage':coverage,'queue_counts':{k:len(v) for k,v in queues.items()},
        'acceptance':'UNACCEPTED','quality':'Not source-verified, mathematical proof, or whole-book accuracy. Empty findings mean no issue detected.',
        'lineage':meta['critic_route'].get('lineage')}
    if meta['config']['profile']=='mimo':
        summary['cost']=cloud.Ledger(run).summary()
        summary['account_allowance']='Historical local remaining is not live key balance; current authenticated remaining checked before each paid dispatch.'
        # Exact anchors/drafts permit a transparent comparison, never a model-vote verdict.
        local=Path(meta['critic_route']['local_run']);local_report=read_json(local/'route-summary.json')
        summary['second_opinion']={'local_calls':local_report['summary']['calls'],'additional_paid_calls':len(state['calls']),
            'comparison_rule':'Overlapping bound target spans and claim topics suggest agreement for inspection, not proof; missing repetition is not a refutation.'}
        comparisons=[]
        local_rows={r['unit']:r for r in local_report['passages']}
        for row in rows:
            before=local_rows[row['unit']];a=before['attempts'][-1].get('findings',[]) if before['attempts'] else []
            b=row['attempts'][-1].get('findings',[]) if row['attempts'] else []
            comparisons.append({'unit':row['unit'],'local_status':before['status'],'second_status':row['status'],
                **compare_findings(a,b),'local_findings':a,'second_findings':b})
        summary['second_opinion']['passages']=comparisons
    result={'summary':summary,'queues':queues,'passages':rows,'historical_findings':[f for f in findings if f['origin']=='historical_superseded_no_current_completion_credit']}
    atomic_json(dest/'route-summary.json',result)
    text='# Candidate critic — UNACCEPTED\n\n'+summary['quality']+'\n\n| Passage | Final status | Assessment | Attempts |\n|---|---|---|---:|\n'
    for r in rows:text+=f"| {r['unit']} | {r['status']} | {r['final_assessment'] or 'unresolved'} | {len(r['attempts'])} |\n"
    text+='\n```json\n'+json.dumps(summary,indent=2)+'\n```\n';(dest/'report.md').write_text(text)
    parts=['<!doctype html><meta charset="utf-8"><style>pre{white-space:pre-wrap;overflow-wrap:anywhere}body{max-width:1100px;margin:2em auto}</style><h1>Candidate critic — UNACCEPTED</h1><pre>'+html.escape(text)+'</pre>']
    for name,items in queues.items():
        tag='details' if name in ('editorial','positive_observations') else 'section';heading='summary' if tag=='details' else 'h2'
        parts.append(f'<{tag}><{heading}>'+html.escape(name)+f'</{heading}><pre>'+html.escape(json.dumps(items,ensure_ascii=False,indent=2))+f'</pre></{tag}>')
    for r in rows:
        links=' '.join('<a href="calls/'+html.escape(a['call'])+'/outcome.json">Attempt '+html.escape(a['call'])+'</a>' for a in r['attempts'])
        parts.append('<details><summary>'+html.escape(r['unit']+' — exact passage, context, all attempts')+'</summary>'+links+'<pre>'+html.escape(json.dumps(r,ensure_ascii=False,indent=2))+'</pre></details>')
    (dest/'report.html').write_text(''.join(parts))
    return summary


def stopped(run):
    s=read_json(Path(run)/'state.json')
    if s['active_since_epoch'] is not None or s['status']=='running':raise ValueError('Writer active; do not select/report/bundle')
    return s


def bundle(run):
    run,preview,meta,units=arm(run);stopped(run);report(run)
    path=ROOT/'results'/(ex.new_path(ROOT,'candidate-critic-inspection').name+'.zip')
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
        for name in ('report.md','report.html','route-summary.json','state.json','binding.json','billing.json','readiness-ledger.json'):
            if (run/name).exists():z.write(run/name,name)
        for name in ('preview.json','selection.json','coverage.json','units.json','cost-preview.json','prior-billing.json'):
            if (preview/name).exists():z.write(preview/name,'prepared/'+name)
        for u in units:
            for key in ('data','request'):z.write(preview/u[key],'prepared/'+u[key])
        for folder in ('calls','readiness-attempts','context-decisions','billing'):
            for p in (run/folder).rglob('*.json'):
                if p.name in ('request.json','input.json','outcome.json','reservation.json','settlement.json','record.json','readiness.json') or folder=='context-decisions':z.write(p,str(p.relative_to(run)))
    with zipfile.ZipFile(path) as z:
        if z.testzip():raise ValueError('Invalid ZIP')
    record={'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path),'report':str(run/'report.html')}
    atomic_json(run/'latest-bundle.json',record);return record


def empirical_record(parent):
    parent=Path(parent).resolve();ledger=cloud.Ledger(parent);s=read_json(parent/'state.json')
    count=sum(c['method']=='baseline' for c in s['calls'])
    if not count:raise ValueError('No empirical baseline denominator')
    cost=ledger.summary();stage_cost=Decimal(cost['actual_reported_usd'])-Decimal(ledger.prior_summary().get('actual_reported_usd','0'))
    if cost['unresolved_charge_ids']:raise ValueError('Empirical charge is incomplete; retain uncertainty rather than inventing a mean')
    return {'run':str(parent),'state_sha256':sha(parent/'state.json'),'billing_sha256':sha(parent/'billing.json'),
        'planned_passages':count,'actual_usd':str(stage_cost),
        'usd_per_planned_passage':str(stage_cost/count),
        'meaning':'Empirical extrapolation includes historical readiness/repairs, not a maximum or account balance.'}


def cost_preview(bodies,prior,empirical,margin=1.5):
    if not 1<=margin<=10:raise ValueError('Planning margin must be 1–10; not a spending limit')
    # All admitted follow-up requests are independently checked against this byte cap.
    rates=cloud.RATES;upper=(Decimal(ca.MAX_INPUT_BYTES+4096)*Decimal(rates['prompt'])+Decimal(32768)*Decimal(rates['completion']))
    readiness_upper=Decimal(ca.MAX_INPUT_BYTES+4096)*Decimal(rates['prompt'])+Decimal(2048)*Decimal(rates['completion'])
    per=Decimal(empirical['usd_per_planned_passage']);n=len(bodies);base=sum((cloud.cost_bound(b) for b in bodies),Decimal(0))
    return {'scope':'selective candidate second opinion, not all-book dispatch','selected_passages':n,
        'inputs':[{'bytes':ca.bounded(b),'prompt_token_reservation_bound':cloud.token_bound(b),'output_tokens':b['max_tokens'],'baseline_reservation_usd':str(cloud.cost_bound(b))} for b in bodies],
        'empirical':empirical,'estimated_stage_usd':str(per*n),'planning_margin_multiplier':margin,
        'estimate_with_margin_usd':str(per*n*Decimal(str(margin))),
        'all_book_extrapolations_not_authorized':[{'passages':count,'usd_before_margin':str(per*count),'usd_with_margin':str(per*count*Decimal(str(margin)))} for count in (200,400,600)],
        'conservative_bounds':{'baseline_usd':str(base),'two_shared_context_or_repair_calls_usd':str(2*upper),
            'one_readiness_usd':str(readiness_upper),'total_new_stage_usd':str(base+2*upper+readiness_upper),
            'request_byte_cap':ca.MAX_INPUT_BYTES,'method':'Full uncached input tariffs; one token per UTF-8 JSON byte plus 4096; maximum output; no cache discount.'},
        'cumulative_ceiling_usd':'10.00','prior_accounted':prior,'live_key_remaining_usd':'unknown_until_authenticated_readiness; other application spending may reduce it',
        'pricing_source':'Pinned xiaomi/fp8 ceilings recorded 2026-10-25; authenticated readiness checks current endpoint prices again.'}


def neutral_second_opinion(data):
    """Keep exact source context, exclude free-form local queries/diagnoses."""
    data=copy.deepcopy(data)
    data['context_status']=[{'status':'bounded_exact_local_context',
        'supplied_block_ids':[a['block_id'] for a in data['context_anchors']],
        'limitation':'Context may be incomplete. Prior critic queries and assessments are not included; identify specific missing local references independently.'}]
    ca.check_data(data)
    return data


def select(run,billing_parent):
    run,preview,meta,units=arm(run);state=stopped(run)
    policy=meta['critic_route']['escalation_policy'];max_passages=policy['max_passages'];clean_sample=policy['clean_sample'];seed=policy['seed'];margin=policy['planning_margin']
    if meta['config']['profile'] not in ('glm','deepseek'):raise ValueError('Select only from a local candidate critic')
    if not 1<=max_passages<=4 or not 0<=clean_sample<=max_passages:raise ValueError('Calibration selection is at most four passages')
    if any(r['status'] in ('pending','in_flight_unknown') for r in state['units'].values()) or state['status'] not in ('completed','completed_with_failures'):
        raise ValueError('Finish bounded local phase before selecting second opinions; no service-failure fallback')
    report(run);result=read_json(run/'route-summary.json');eligible=[];clean=[];excluded=[]
    consumed=sum(c['method']!='baseline' for c in state['calls'])
    remaining=meta['limits']['recovery_calls']-consumed
    if remaining<=0 or state['elapsed_seconds']>=meta['limits']['admission_seconds']:
        raise ValueError('Shared local-origin follow-up/time budget exhausted; no paid second opinion admitted')
    for row in result['passages']:
        last=row['attempts'][-1] if row['attempts'] else {};reason=None
        views=finding_views(last.get('findings',[]))
        if sum(c['parent']==row['unit'] and c['method']!='baseline' for c in state['calls'])>=2:
            excluded.append({'unit':row['unit'],'reason':'Original passage already consumed both follow-ups; escalation does not reset them'});continue
        if views['material']:reason='Material mathematical concern requiring independent assessment'
        elif views['context'] or row['final_assessment']=='insufficient_context':reason='Unresolved mathematical context/uncertainty after bounded local phase; no missing source invented'
        elif row['status']=='failed' and last.get('failure',{}).get('kind') in ('json','schema','coverage','output_truncated','reasoning_exhausted','budget_exhausted_unknown','malformed_completion'):
            reason='Technically unusable bounded local assessment; changed strategy is explicit model escalation'
        if reason:eligible.append({'unit':row['unit'],'reason':reason,'selection_class':'difficult'})
        elif row['final_assessment']=='no_finding' and not views['visual'] and not views['context']:clean.append(row['unit'])
        else:excluded.append({'unit':row['unit'],'reason':'Visual-only, editorial-only, unavailable, infrastructure failure or incomplete coverage; text escalation not justified'})
    slots=min(max_passages,remaining)
    sample=random.Random(seed).sample(sorted(clean),min(clean_sample,len(clean),slots))
    chosen=eligible[:slots-len(sample)]+[{'unit':u,'reason':'Seeded apparently-clean sample for false-negative checking, not certified correct','selection_class':'clean_sample'} for u in sample]
    if not chosen:raise ValueError('No eligible passages; no paid stage prepared')
    parent,b,ps,pp,pm,pu=verified_parent(billing_parent,require_recovery_budget=False)
    billing=cloud.Ledger(parent).summary()
    if billing['ceiling_usd']!='10.00' or billing['halt']:raise ValueError('Prior USD 10 paid accounting is incompatible')
    empirical=empirical_record(parent)
    plan=ex.new_path(ROOT,'critic-escalation-plan');plan.mkdir();bodies=[]
    byid={r['unit']:r for r in result['passages']}
    for item in chosen:
        data=neutral_second_opinion(byid[item['unit']]['data'])
        body=ca.request(data,paid_config(len(chosen)));bodies.append(body)
        atomic_json(plan/'units'/item['unit']/'input.json',data);atomic_json(plan/'units'/item['unit']/'request.json',body)
    record={'schema':'critic-escalation-selection-v1','local_run':str(run),'local_binding_sha256':sha(run/'binding.json'),
        'local_state_sha256':sha(run/'state.json'),'local_preview_manifest_sha256':sha(preview/'manifest.json'),
        'candidate_sha256':meta['critic_route']['candidate_sha256'],'billing_parent':str(parent),
        'billing_parent_binding_sha256':sha(parent/'binding.json'),'billing_parent_ledger_sha256':sha(parent/'billing.json'),
        'selected':chosen,'eligible_not_selected':eligible[slots-len(sample):],'excluded':excluded,
        'clean_pool':sorted(clean),'clean_selected':sample,'seed':seed,'max_passages':max_passages,'clean_sample':clean_sample,
        'limits':policy,'approval':'Reviewable offline plan. --allow-paid at operator readiness/launch required; no automatic acceptance.',
        'local_calls_consumed':len(state['calls']),'local_limits':meta['limits'],'planning_margin':margin}
    atomic_json(plan/'selection.json',record);atomic_json(plan/'cost-preview.json',cost_preview(bodies,billing,empirical,margin));ex.seal(plan)
    atomic_json(run/'escalation-plan.json',{'path':str(plan),'manifest_sha256':sha(plan/'manifest.json')})
    return plan


def prepare_mimo(plan):
    plan=Path(plan).resolve();ex.verify_seal(plan);selection=read_json(plan/'selection.json')
    local,p,m,units=arm(Path(selection['local_run']));stopped(local)
    for actual,expected in ((sha(local/'binding.json'),selection['local_binding_sha256']),
                            (sha(local/'state.json'),selection['local_state_sha256']),
                            (sha(p/'manifest.json'),selection['local_preview_manifest_sha256'])):
        if actual!=expected:raise IntegrityError('Stale local escalation selection')
    chosen=selection['selected'];specs={u['id']:u for u in units};state=read_json(local/'state.json')
    if (selection['schema']!='critic-escalation-selection-v1' or selection['limits']!=m['critic_route']['escalation_policy']
        or not 1<=len(chosen)<=4 or len({x['unit'] for x in chosen})!=len(chosen)
        or any(x['unit'] not in specs for x in chosen)):
        raise IntegrityError('Invalid selected passage scope/policy')
    consumed=sum(c['method']!='baseline' for c in state['calls'])
    seconds=min(7200,max(0,int(m['limits']['admission_seconds']-state['elapsed_seconds'])))
    if consumed+len(chosen)>m['limits']['recovery_calls'] or seconds<=0:
        raise ValueError('Selected second opinions exceed original shared follow-up/time budget')
    for item in chosen:
        identity=item['unit'];u=specs[identity]
        if sum(c['parent']==identity and c['method']!='baseline' for c in state['calls'])>=2:
            raise ValueError('Selected passage follow-ups exhausted')
        data=read_json(plan/'units'/identity/'input.json')
        base=read_json(p/u['data'])
        if data['targets']!=base['targets'] or data['candidate_sha256']!=base['candidate_sha256']:
            raise IntegrityError('Selected candidate/target version changed')
    parent=Path(selection['billing_parent']);stopped(parent)
    if sha(parent/'billing.json')!=selection['billing_parent_ledger_sha256'] or sha(parent/'binding.json')!=selection['billing_parent_binding_sha256']:
        raise IntegrityError('Prior paid evidence changed; refresh selection without resetting costs')
    # One child from a paid ledger prevents two apparent independent allowances.
    for path in (ROOT/'runs').glob('candidate-critic-input-*/preview.json'):
        if read_json(path).get('critic_route',{}).get('billing_parent')==str(parent):raise ValueError('Paid parent already has a linked stage; resume it, do not fork spending')
    preview=ex.new_path(ROOT,'candidate-critic-input');run=ex.new_path(ROOT,'candidate-critic-trial');preview.mkdir()
    shutil.copyfile(p/'context-index.json',preview/'context-index.json');shutil.copyfile(plan/'cost-preview.json',preview/'cost-preview.json')
    prior={'parent_run':str(parent),'binding_sha256':sha(parent/'binding.json'),'ledger_sha256':sha(parent/'billing.json'),
        'summary':cloud.Ledger(parent).summary(),'raw_ledger':read_json(parent/'billing.json'),
        'meaning':'Frozen prior costs/unknown reservations retained under USD 10; new explicitly authorized stage call caps are separate from the frozen pilot.'}
    atomic_json(preview/'prior-billing.json',prior)
    hashes=dict(m['source_hashes'])
    for folder in (plan,p):hashes.update({str(folder/e['path']):e['sha256'] for e in files_manifest(folder)})
    for name in ('binding.json','state.json','route-summary.json'):hashes[str(local/name)]=sha(local/name)
    for c in read_json(local/'state.json')['calls']:
        for e in files_manifest(local/'calls'/c['id']):hashes[str(local/'calls'/c['id']/e['path'])]=e['sha256']
    hashes.update({str(parent/'billing.json'):sha(parent/'billing.json'),str(parent/'binding.json'):sha(parent/'binding.json')})
    new=[]
    for item in chosen:
        identity=item['unit'];u=specs[identity];data=read_json(plan/'units'/identity/'input.json');body=read_json(plan/'units'/identity/'request.json')
        if body!=ca.request(data,paid_config(len(chosen))):raise IntegrityError('Selected paid request differs from neutral profile')
        new.append(save_unit(preview,identity,data,body,kind='critic',gate=False,version='candidate',location=u['location'],unavailable=None))
    coverage=read_json(p/'coverage.json');target=[a['block_id'] for u in new for a in read_json(preview/u['data'])['targets']]
    coverage={**coverage,'target_blocks':target,'local_targets_not_selected':[b for b in coverage['target_blocks'] if b not in target]}
    atomic_json(preview/'coverage.json',coverage)
    result=finalize(preview,run,new,paid_config(len(new)),hashes,
        {'baseline_calls':len(new),'recovery_calls':2,'per_parent_recovery':2,'admission_seconds':seconds},selection,
        {'version':VERSION,'candidate':m['critic_route']['candidate'],'candidate_sha256':m['critic_route']['candidate_sha256'],
         'context_policy':ctx.POLICY,'local_run':str(local),'billing_parent':str(parent),'lineage':selection,
         'shared_accounting':{'original_limits':m['limits'],'local_recovery_calls':consumed,'local_elapsed_seconds':state['elapsed_seconds'],
             'meaning':'Every paid passage call, including its first second opinion, consumes the original local passage and global follow-up allowances. Readiness is separately bounded.'},
         'local_recovery_by_parent':{u['id']:sum(c['parent']==u['id'] and c['method']!='baseline' for c in read_json(local/'state.json')['calls']) for u in new},
         'mode':'explicit_selected_second_opinion','no_automatic_acceptance':True})
    atomic_json(local/'escalation-run.json',result);return result


def live(run,*,allow_paid=False,resume=False,client_factory=None):
    run,preview,meta,units=arm(run);state=stopped(run)
    if meta['config']['profile']=='mimo':
        if not allow_paid:raise ValueError('Selected MiMo needs explicit --allow-paid')
        print(json.dumps(read_json(preview/'cost-preview.json'),indent=2),flush=True)
    if not resume and state['status']!='prepared_offline':raise ValueError('Existing execution requires resume; no replay')
    readiness=None
    for attempt in reversed(read_json(run/'readiness-ledger.json')['attempts']):
        if attempt['status']!='passed':continue
        path=run/'readiness-attempts'/attempt['id']
        try:ex.check_readiness(path,meta['config'],False)
        except ValueError:continue
        readiness=path;break
    if readiness is None:
        readiness=pilot.ready(run,allow_paid,client_factory,arm_loader=arm,readiness_builder=readiness_input)
    if not readiness or not (readiness/'readiness.json').is_file():raise ValueError('Missing actual readiness result')
    if resume:(run/'PAUSE').unlink(missing_ok=True)
    factory=client_factory or pilot.factory(run,meta['config'],allow_paid)
    try:return ex.execute(ROOT,run,stage='route',readiness=readiness,resume=resume,client_factory=factory)
    finally:
        if read_json(run/'state.json')['active_since_epoch'] is None:print(json.dumps(bundle(run),indent=2))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('boundaries');p.add_argument('--candidate',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p=sub.add_parser('prepare');p.add_argument('--candidate',required=True,type=Path);p.add_argument('--conversion',required=True,type=Path)
    p.add_argument('--source',required=True);p.add_argument('--passages',required=True,type=Path);p.add_argument('--profile',choices=('glm','deepseek'),default='glm')
    p.add_argument('--recovery-calls',type=int,default=8);p.add_argument('--hours',type=float,default=4)
    p.add_argument('--clean-sample',type=int,default=1);p.add_argument('--selection-seed',type=int,default=20261025);p.add_argument('--planning-margin',type=float,default=1.5)
    for name in ('run','resume','ready','status','pause','report','bundle','select','prepare-selected','cost'):
        p=sub.add_parser(name);p.add_argument('--run',required=True,type=Path)
        if name in ('run','resume','ready'):p.add_argument('--allow-paid',action='store_true')
        if name=='select':p.add_argument('--billing-parent',required=True,type=Path)
    args=parser.parse_args(argv)
    if args.command=='status':
        s=read_json(args.run/'state.json');print(json.dumps({k:s[k] for k in ('status','active_since_epoch','elapsed_seconds','units')},indent=2))
        if (args.run/'billing.json').exists():print(json.dumps(cloud.Ledger(args.run).summary(),indent=2))
        return 0
    if args.command=='pause':
        arm(args.run);(args.run/'PAUSE').touch();print('Pause requested; current bounded call may finish.');return 0
    with writer_lock(ROOT/'runs'):
        if args.command=='boundaries':boundary_template(args.candidate,args.out);print(args.out);return 0
        if args.command=='prepare':
            result=prepare(args.candidate,args.conversion,args.source,args.passages,profile=args.profile,recovery_calls=args.recovery_calls,hours=args.hours,
                clean_sample=args.clean_sample,selection_seed=args.selection_seed,planning_margin=args.planning_margin)
            result['bundle']=bundle(Path(result['run']));atomic_json(ROOT/'results/candidate-critic-current.json',result);print(json.dumps(result,indent=2));return 0
        if args.command in ('run','resume'):return live(args.run,allow_paid=args.allow_paid,resume=args.command=='resume')
        if args.command=='ready':
            run,p,m,u=arm(args.run)
            if m['config']['profile']=='mimo':print(json.dumps(read_json(p/'cost-preview.json'),indent=2))
            pilot.ready(run,args.allow_paid,arm_loader=arm,readiness_builder=readiness_input);return 0
        if args.command=='report':stopped(args.run);print(json.dumps(report(args.run),indent=2));return 0
        if args.command=='bundle':print(json.dumps(bundle(args.run),indent=2));return 0
        if args.command=='select':
            path=select(args.run,args.billing_parent);print('Selection:',path);print(json.dumps(read_json(path/'cost-preview.json'),indent=2));return 0
        if args.command=='prepare-selected':
            stopped(args.run);pointer=read_json(args.run/'escalation-plan.json');path=Path(pointer['path']);ex.verify_seal(path,pointer['manifest_sha256'])
            result=prepare_mimo(path);result['bundle']=bundle(Path(result['run']));print(json.dumps(result,indent=2));return 0
        if args.command=='cost':
            b=read_json(args.run/'binding.json');p=Path(b['preview'])
            if not (p/'cost-preview.json').exists():
                pointer=read_json(args.run/'escalation-plan.json');p=Path(pointer['path']);ex.verify_seal(p,pointer['manifest_sha256'])
            print(json.dumps(read_json(p/'cost-preview.json'),indent=2));return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,cloud.AdmissionError) as exc:raise SystemExit(str(exc)) from None
