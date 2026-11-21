"""Finite local-only library waves and saved-evidence checkpoints. No new transport."""
from pathlib import Path
from .common import read_json,atomic_json,sha,fingerprint
from .experiment import verify_seal

def validate_plan(p):
    spec=p['night_day'];ids=[d['source_id'] for d in p['documents']]
    if len(ids)!=60 or len(set(ids))!=60 or spec['checkpoints']!=[5,30,60] or spec['waves']!=[30,60]:raise ValueError('Frozen60-paper wave contract differs')
    if sum(len(d['physical_pages']) for d in p['documents'])!=704:raise ValueError('Frozen704-page contract differs')
    if p.get('overnight') or p.get('allocation_id') or p['paid_enabled'] or p['spend_cap_usd']!='0':raise ValueError('No paid allocation or paid worker path authorized')
    s=p['settings']
    if (s['converter_effort'],s['review_effort'],s['max_tokens'],s['maximum_in_flight'])!=('high','high',131072,2):raise ValueError('Frozen local settings changed')
    if s.get('compile_pdf') or not p.get('accept_exact_fragments'):raise ValueError('Optional compilation off and exact-body salvage required')
    return ids

def extraction_seed(run,s,source_ids):
    """A fresh workspace per wave, retaining every consumed attempt in that wave."""
    from .source_library import copy_verified
    records={k:v for k,v in s['extraction']['mineru_pro']['pages'].items() if v['source_id'] in source_ids}
    seed=run/'extraction-waves'/('scope-'+fingerprint(sorted(source_ids))[:12])/'seed'
    for rec in records.values():
        for artifact in rec.get('outputs',[]):copy_verified(run/'arms/mineru_pro'/artifact['path'],seed/artifact['path'],artifact['sha256'])
    atomic_json(seed/'state.json',{'status':'prepared','pages':records})
    return seed

def merge_extraction(previous,incoming,source_ids):
    import copy
    merged=copy.deepcopy(previous['pages'])
    for key,record in incoming['pages'].items():
        if record['source_id'] not in source_ids:raise ValueError('Returned extraction outside frozen wave')
        if key in merged and record!=merged[key]:raise ValueError('Consumed extraction attempt changed across wave/resume')
        merged[key]=record
    return dict(incoming,pages=merged)

def checkpoint(run,s,c,count):
    p=read_json(run/'plan.json');ids=validate_plan(p)[:count];c.verify(run)
    target=run/'checkpoints'/f'after-{count:02}.json'
    if target.exists():
        if read_json(target)['decision']!='continue':raise c.runtime.Fatal('Prior shared checkpoint failure requires reconciliation')
        return
    rows=[]
    for sid in ids:
        tasks=[t for t in s['tasks'] if t['source_key']==sid]
        if any(t['status'] in ('pending','running','interrupted_unresolved','coordinator_failure') for t in tasks):raise c.runtime.Fatal('Checkpoint has unresolved execution: '+sid)
        for call in (x for x in s['calls'] if x['parent'] in {t['id'] for t in tasks}):
            verify_seal(run/'calls'/call['id'],call['seal'])
        c.publish_settled(run,s,sid);doc=s['documents'][sid]
        if not doc.get('published'):raise c.runtime.Fatal('Checkpoint delivery missing: '+sid)
        delivery=Path(doc['delivery']);record=c.policy.validate_publication(delivery,next(x['library_document'] for x in p['documents'] if x['source_id']==sid))
        if doc.get('units') and not doc.get('source_accounting',{}).get('all_regions_accounted'):raise c.runtime.Fatal('Shared source ownership accounting failure: '+sid)
        numerical=[]
        for t in tasks:
            if t.get('call'):
                f=c.result_file(run,t['call'],'findings.json') if hasattr(c,'result_file') else None
                if f and f.exists():numerical += [{'task':t['id'],**x} for x in read_json(f).get('numerical_cell_checks',[])]
        table_units=[k for k in doc['units'] if any(b['kind']=='table' for b in s['source_units'][k]['native_blocks'])]
        rows.append({'source_id':sid,'filename':doc['filename'],'status':record['status'],'selected_units':len(record.get('selected_sources',record['selected_tex'])),
            'outstanding_scopes':record.get('outstanding_scopes',[]),'missing_conversion_scopes':record.get('missing_conversion_scopes',[]),
            'coverage':record['coverage'],'join_checks':record['output_ownership_check'],'model_review':record['model_review'],
            'table_units':table_units,'numerical_cell_observations':numerical,'numerical_cell_review':'Original-page images and explicit numerical-cell instruction supplied to each actual review; located findings retained. Absence of findings is not independent numerical verification.',
            'call_statuses':[{k:t.get(k) for k in ('id','status','call','review_complete_attested','pending_suggestions')} for t in tasks],
            'delivery':str(delivery),'manifest_sha256':sha(delivery/'manifest.json')})
    # Broad symptoms do not prove a common mathematical error. Integrity defects
    # raise above; a concrete diagnosed shared defect must block this gate.
    if s.get('shared_correctness_failure'):raise c.runtime.Fatal('Demonstrated shared correctness failure: '+str(s['shared_correctness_failure']))
    totals={'ready_working_sources':sum(x['status']=='ready_working_source' for x in rows),'partial_with_text':sum(x['status']!='ready_working_source' and x['selected_units']>0 for x in rows),'failed_without_selected_text':sum(x['selected_units']==0 for x in rows)}
    record={'at':c.runtime.now(),'papers_processed':count,'decision':'continue','counts':totals,'papers':rows,
      'criterion':'No demonstrated shared integrity/correctness/resource defect; isolated omissions, unavailable recovery and invalid reviews remain visible rather than clearing content flags',
      'source_verification':'Model review and deterministic source accounting; not complete independent mathematical verification','new_paid_submissions':0}
    atomic_json(target,record);s.setdefault('night_day_checkpoints',{})[str(count)]={'path':str(target.relative_to(run)),'sha256':sha(target),'counts':totals};c.save(run,s)
    c.bundle(run,s)

def local_requests(run,s,c,tasks):
    helpers=c.base.books.speed.module();c.base.books.book.arrange_glm(run,check_only=True)
    if c.base.books.speed.effort_check(run,helpers)['status']!='supported':raise c.runtime.Fatal('Installed reasoning mappings not qualified')
    raw=c.base.books.speed.sampler(run,s,helpers)
    def sample(owned):
        observation=raw(owned)
        if any(type(v)is not int or v<4*1024**3 for v in observation['memory_available_bytes'].values()):raise c.runtime.StopRun('Image-workflow4GiB headroom guard; no dispatch')
        return observation
    c.base.books.speed.healthy(sample(0));taskmap={t['id']:t for t in tasks}
    for call in s['calls']:
        t=taskmap.get(call['parent'])
        if not t or t.get('settled_call')==call['id']:continue
        folder=run/'calls'/call['id']
        if not (folder/'manifest.json').exists():raise c.runtime.Fatal('Uncertain consumed request: no replay')
        call.update(c.saved_response(run,call,c.body_for(run,s,t)));call['seal']=sha(folder/'manifest.json')
        c.finish(run,s,t,(folder/'content.txt').read_text() if call['status']=='completed_response' else None,call)
    c.scheduler.coordinate(run,s,tasks,body_for=c.body_for,finish=c.finish,verify=lambda:c.verify(run),changed=lambda:c.save(run,s),sample=sample,fixed_level=2,before_reserve=lambda state,t,b:c.before(run,state,t,b))

def execute(run,s,c):
    p=read_json(run/'plan.json');ids=validate_plan(p)
    for start,end,ends in [(0,30,[5,30]),(30,60,[60])]:
        wave=ids[start:end]
        if str(end) in s.get('night_day_checkpoints',{}):continue
        s['stage']=f'Wave {start//30+1}: MinerU Pro for papers {start+1}-{end}';c.save(run,s)
        c.extract(run,s,source_ids=wave)
        if any(not s['documents'][sid].get('planning_done') for sid in wave):s['inputs_prepared']=False
        c.plan_units(run,s,source_ids=wave);c.verify(run)
        previous=start
        for count in ends:
            if str(count) in s.get('night_day_checkpoints',{}):previous=count;continue
            scope=set(ids[previous:count]);s['stage']=f'Local High conversion/image review: papers {previous+1}-{count}';c.save(run,s)
            local_requests(run,s,c,[t for t in s['tasks'] if t['source_key'] in scope])
            if (run/'pause.json').exists():raise c.runtime.StopRun('Supported pause after draining local tasks')
            checkpoint(run,s,c,count);previous=count
