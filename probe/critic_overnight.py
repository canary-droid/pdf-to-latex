"""Frozen, opt-in two-stage continuation of the existing text critic.

Preparation and packaging are offline. Only launch dispatches, through the shared
serial executor. No candidate edits, prompt tuning or service management.
"""
import argparse
from collections import Counter
from datetime import datetime
import html
import json
from pathlib import Path
import shutil
import zipfile

from . import experiment as ex, text_critic as tc
from .common import atomic_json, read_json, sha, fingerprint, files_manifest, writer_lock
from .evaluation_export import experiment_report, usage_accounting
from .recovery_trial import verified_parent, save_unit, finish_preview
from .recovery import response_data

ROOT=Path(__file__).resolve().parents[1]
LIMITS={'baseline_calls':31,'recovery_calls':16,'per_parent_recovery':2,'admission_seconds':28800}
CHECKPOINT={'minimum_first':9,'minimum_final':12,'minimum_coverage':9,'frozen_before_live':True}
PAGES={5:126,6:156,7:166,8:176,9:212,10:212,11:116,12:116,13:136,14:146,15:146,16:186,17:196,18:206,19:218,20:225}
UNAVAILABLE='Candidate unresolved blocks: klebaner-ch4-7-p0081:b19'


def validate_protocol(meta,units):
    expected={f'g{i:02d}-{v}' for i in range(5,21) for v in ('X','Y')}
    if len(units)!=32 or {u['id'] for u in units}!=expected:raise ValueError('Unexpected overnight cohort')
    if meta['kind']!='critic' or meta['limits']!=LIMITS or meta['gate']!=CHECKPOINT:raise ValueError('Changed overnight bounds/checkpoint')
    cfg=meta['config']
    required={**tc.PROFILES['deepseek'],'max_tokens':32768,'timeout':900,'stream':False,'lower_reasoning_supported':False,'sampling':'server defaults omitted'}
    if cfg!=required:raise ValueError('Changed frozen critic settings')
    if meta['overnight']['order']!=[u['id'] for u in units]:raise ValueError('Changed frozen order')
    if [u['split'] for u in units]!=['development']*12+['reserved']*20:raise ValueError('Stages interleaved')
    for u in units:
        n=int(u['id'][1:3])
        if u['kind']!='critic' or u['gate']!=(n<=10) or u['location']['page']!=PAGES[n]:raise ValueError('Changed stage/page mapping')
        if u.get('unavailable')!=(UNAVAILABLE if u['id']=='g16-Y' else None):raise ValueError('Unexpected unavailable cohort')
        if u['version']!=('baseline' if u['id'].endswith('X') else 'candidate'):raise ValueError('Changed neutral version assignment')


def prepare(gate_run,original_run,gate_zip,preview,out):
    gate,gb,gs,gp,gm,gu=verified_parent(gate_run,require_recovery_budget=False)
    old,ob,os,op,om,ou=verified_parent(original_run,require_recovery_budget=False)
    if gs['status']!='completed' or {u['id'] for u in gu}!={f'g{i:02d}-{v}' for i in range(1,5) for v in ('X','Y')}:
        raise ValueError('Require the completed eight-unit follow-up')
    checked=ex.gate_result(gs,gu,gm['gate'],gate)
    if not checked['passed'] or checked!=gs['gate']:raise ValueError('Follow-up technical gate not verified')
    lineage=read_json(gp/'lineage.json')
    if Path(lineage['parent_run'])!=old or lineage['parent_preview_manifest_sha256']!=sha(op/'manifest.json'):
        raise ValueError('Gate is not linked to this original full preparation')
    if len(ou)!=40 or {u['id'] for u in ou}!={f'g{i:02d}-{v}' for i in range(1,21) for v in ('X','Y')}:
        raise ValueError('Unexpected original cohort')
    if any(int(c['parent'][1:3])>4 for c in os['calls']):raise ValueError('Remaining set already observed')
    for name in ('text_critic.py','recovery.py','sciwrite_subset.py','local_model.py','bibliography.py'):
        if gm['code_sha256'][name]!=ex.code_hashes()[name]:raise ValueError('Successful gate prompt/validation/recovery changed: '+name)
    template=None
    for u in gu:
        body=read_json(gp/u['request']);data=read_json(gp/u['data'])
        if body!=tc.request(data,'deepseek',max_tokens=32768):raise ValueError('Successful generic request changed')
        template=body
    gate_zip=Path(gate_zip).resolve()
    with zipfile.ZipFile(gate_zip) as z:
        if z.testzip() or json.loads(z.read('state.json'))!=gs:raise ValueError('Gate inspection ZIP does not match completed state')
    preview=Path(preview).resolve();out=Path(out).resolve()
    selected=[u for u in ou if int(u['id'][1:3])>=5]
    units=[{**u,'gate':u['split']=='development'} for u in selected]
    config={k:v for k,v in gm['config'].items() if k!='diagnostic_followup_only'}
    protocol={'order':[u['id'] for u in units],'checkpoint_scope':'g05–g10 only; earlier eight-unit gate unchanged',
        'deadline':'Eight hours from first substantive reservation, INCLUDING pauses; at most one 900-second in-flight completion afterwards',
        'cleanup':'No additional inference admission; local report/ZIP cleanup only, normally seconds, no hard filesystem-time guarantee',
        'reserved':'Frozen before launch; one-time use. Once examined, not unseen for future tuning.'}
    validate_protocol({'kind':'critic','config':config,'limits':LIMITS,'gate':CHECKPOINT,'overnight':protocol},units)
    preview.mkdir(parents=True,exist_ok=False)
    for u in units:
        data=read_json(op/u['data']);oldbody=read_json(op/u['request'])
        body=tc.request(data,'deepseek',max_tokens=32768)
        expected={**oldbody,'max_tokens':32768,'messages':[template['messages'][0],*oldbody['messages'][1:]]}
        if body!=expected:raise ValueError('Passage/schema/settings differ beyond successful generic prompt/allowance: '+u['id'])
        new=save_unit(preview,u['id'],data,body,**{k:v for k,v in u.items() if k not in ('id','data','request')})
        shutil.copyfile(op/u['data'],preview/new['data'])
    hashes={**om['source_hashes'],**gm['source_hashes'],str(gate_zip):sha(gate_zip)}
    for folder in (old,op,gate,gp):hashes.update({str(folder/e['path']):e['sha256'] for e in files_manifest(folder)})
    history={'successful_gate':{'run':str(gate),'preview':str(gp),'code_sha256':gm['code_sha256'],
        'calls':len(gs['calls']),'elapsed_seconds':gs['elapsed_seconds'],'gate':checked,'state_sha256':sha(gate/'state.json'),'zip':str(gate_zip),'zip_sha256':sha(gate_zip)},
        'original_preparation':{'run':str(old),'preview':str(op),'code_sha256':om['code_sha256'],'calls':len(os['calls']),'state_sha256':sha(old/'state.json')},
        'accounting':'Historical gate calls remain historical and are not replayed or counted as overnight calls. This new 31+16 allowance is explicitly authorized.',
        'candidate':'Exactly the candidate and original passages bound by the original preview; no reassembly',
        'unchanged_protocol_files':{n:gm['code_sha256'][n] for n in ('text_critic.py','recovery.py','sciwrite_subset.py','local_model.py','bibliography.py')}}
    atomic_json(preview/'lineage.json',history)
    atomic_json(preview/'request-bindings.json',[{'id':u['id'],'split':u['split'],'input_sha256':sha(preview/u['data']),
        'original_input_sha256':sha(op/u['data']),'request_sha256':sha(preview/u['request']),
        'draft_sha256':read_json(preview/u['data'])['draft_sha256']} for u in units])
    helper='''#!/usr/bin/env bash
set -euo pipefail
cd "'''+str(ROOT)+'''"
if [[ $# -lt 1 || $# -gt 2 || -z "${1//[[:space:]]/}" ]]; then
  echo 'Usage: bash operator-launch.sh ACTUAL_READINESS_DIRECTORY [--resume]' >&2; exit 2
fi
if [[ $# == 2 && $2 != --resume ]]; then echo 'Only --resume is allowed' >&2; exit 2; fi
test -f "$1/readiness.json"
exec .venv-control/bin/python -m probe.critic_overnight launch --run "'''+str(out)+'''" --readiness "$1" "${@:2}"
'''
    (preview/'operator-launch.sh').write_text(helper)
    finish_preview(preview,units,'critic',config,hashes,LIMITS,CHECKPOINT,protocol)
    (preview/'manifest.json').unlink();meta=read_json(preview/'preview.json');meta['overnight']=protocol
    atomic_json(preview/'preview.json',meta);ex.seal(preview);ex.initialize(preview,out)
    return {'preview':str(preview),'run':str(out),'successful_gate':str(gate),'operator_launcher':str(preview/'operator-launch.sh')}


def stage_view(rows,state,split):
    selected=[r for r in rows if r['split']==split];available=[r for r in selected if r['status']!='unavailable']
    pairs={r['id'].split('-')[0] for r in selected};paired=[g for g in sorted(pairs) if all(r['status']!='unavailable' for r in selected if r['id'].startswith(g+'-'))]
    complete_pairs=[g for g in paired if all(r['status']=='completed' for r in selected if r['id'].startswith(g+'-'))]
    outcomes=[o for r in selected for o in r['outcomes']]
    calls=[c for c in state['calls'] if c['parent'] in {r['id'] for r in selected}]
    known={o['call'] for o in outcomes}
    accounting_rows=outcomes+[{'call':c['id'],'method':c['method'],'status':c['status']} for c in calls if c['id'] not in known]
    final=[(r,next((o for o in reversed(r['outcomes']) if o['call']==state['units'][r['id']].get('last_call')),{})) for r in selected]
    views={'mathematical_consequences':[],'context_needs':[],'editorial_observations':[]}
    for r,o in final:
        if r['status']!='completed':continue
        common={'unit':r['id'],'version':r['version'],'location':r['location'],'call':o.get('call'),'acceptance':'UNACCEPTED'}
        if o.get('answer',{}).get('context_needed'):views['context_needs'].append({**common,'context_needed':o['answer']['context_needed']})
        for f in o.get('findings',[]):
            entry={**common,'finding':f}
            if f['category']=='editorial' or f['next_action']=='editorial_review':views['editorial_observations'].append(entry)
            else:views['mathematical_consequences'].append(entry)
            if f['context_required']:views['context_needs'].append(entry)
    failure_classes=Counter()
    for o in outcomes:
        f=o.get('failure')
        if not f:continue
        k=f['kind'];diagnostic=json.dumps(f.get('errors',[]))
        if k=='coverage' and 'quote' in diagnostic:k='quotation_location'
        failure_classes[k]+=1
    summary={'split':split,'planned_slots':len(selected),'callable_slots':len(available),
        'statuses':dict(Counter(r['status'] for r in selected)),
        'first_attempt_valid':sum(bool(r['outcomes']) and r['outcomes'][0]['status']=='completed' for r in selected),
        'final_valid':sum(r['status']=='completed' for r in selected),
        'recovery_assisted_valid':sum(r['status']=='completed' and len(r['outcomes'])>1 for r in selected),
        'complete_claimed_coverage':sum(r['status']=='completed' and o.get('assessment') not in ('insufficient_context','incomplete_coverage') for r,o in final),
        'planned_pairs':len(pairs),'available_pairs':len(paired),'completed_pairs':len(complete_pairs),'paired_groups':paired,
        'unpaired_callable_units':[r['id'] for r in available if r['id'].split('-')[0] not in paired],
        'reserved_calls':len(calls),'recorded_outcomes':len(outcomes),
        'failure_classes':dict(failure_classes),'usage_accounting':usage_accounting(accounting_rows),
        'denominators':'Usability includes all planned and callable slots separately; paired comparisons only use available pairs, with completed pair count explicit. Unknown usage is not zero.'}
    return {'summary':summary,'views':views,'units':selected}


def reports(preview,out):
    state=read_json(out/'state.json')
    if state['active_since_epoch'] is not None or state['status']=='running':raise ValueError('Writer must have stopped before inspection bundling')
    summary=experiment_report(preview,out);rows=read_json(out/'ledger.json');specs={u['id']:u for u in read_json(preview/'units.json')}
    for r in rows:
        r['version']=specs[r['id']]['version']
        for o in r['outcomes']:
            ev=response_data(out/'calls'/o['call'])
            o['response_metrics']={k:ev.get(k) for k in ('actual_model','finish_reason','http_status','latency_seconds','usage')}
    root=out/'overnight';root.mkdir(exist_ok=True)
    explanation=('MinerU supplied saved OCR. Qwen compared it with images and proposed revisions; the experimental candidate retains unresolved material. '
        'DeepSeek reads original and candidate text windows separately, without images. All findings remain UNACCEPTED. '
        'Exact quotations and technical usability do not establish mathematical correctness. No prompt/context/candidate tuning occurs between stages. '
        'The reserved set is used once; later tuning needs new reserved material. g16-Y is unavailable, g16-X is unpaired. '
        'v105 / PDF 205 b15 remains deferred and was outside the earlier g02 b5–b12 gate window. '
        'Three unresolved candidate blocks remain in the unchanged candidate inventory; only g16-Y prevents a selected passage. '
        'Selected passage windows are not whole pages or whole-book coverage.')
    stages={}
    for split in ('development','reserved'):
        view=stage_view(rows,state,split);stages[split]=view['summary'];atomic_json(root/(split+'.json'),view)
        text='# '+split.capitalize()+' critic inspection\n\n'+explanation+'\n\n```json\n'+json.dumps(view['summary'],indent=2)+'\n```\n'
        for section,entries in view['views'].items():text+='\n## '+section.replace('_',' ')+'\n\n```json\n'+json.dumps(entries,ensure_ascii=False,indent=2)+'\n```\n'
        text+='\n## Complete exact inputs and all attempt outcomes\n\n```json\n'+json.dumps(view['units'],ensure_ascii=False,indent=2)+'\n```\n'
        (root/(split+'.md')).write_text(text)
        (root/(split+'.html')).write_text('<!doctype html><meta charset="utf-8"><title>'+split+' critic</title><pre>'+html.escape(text)+'</pre>')
    started=state['calls'][0]['reserved_at'] if state['calls'] else None
    record={'status':state['status'],'technical_checkpoint':state['gate'],'stages':stages,
        'calls':len(state['calls']),'elapsed_seconds':state['elapsed_seconds'],'admission_started_at':started,
        'deadline_epoch':datetime.fromisoformat(started).timestamp()+LIMITS['admission_seconds'] if started else None,
        'usage_accounting':usage_accounting([o for r in rows for o in r['outcomes']]+[
            {'call':c['id'],'method':c['method'],'status':c['status']} for c in state['calls']
            if not (out/'calls'/c['id']/'outcome.json').exists()]),
        'historical_gate':read_json(preview/'lineage.json')['successful_gate'],
        'history_accounting':'Prior 9 successful-gate calls (and 10 earlier failed-gate calls) excluded from new experiment totals; no replay.',
        'explanation':explanation}
    atomic_json(root/'summary.json',record)
    md='# Overnight critic — '+state['status']+'\n\n'+explanation+'\n\nDevelopment and reserved views retain full input and answer context.\n\n```json\n'+json.dumps(record,indent=2)+'\n```\n'
    (root/'report.md').write_text(md)
    (root/'report.html').write_text('<!doctype html><meta charset="utf-8"><a href="development.html">Development</a> | <a href="reserved.html">Reserved</a><pre>'+html.escape(md)+'</pre>')
    return record


def bundle(root,preview,out):
    reports(preview,out)
    dest=Path(root)/'results'/(ex.new_path(root,out.name+'-inspection').name+'.zip');dest.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED) as z:
        for name in ('report.html','report.md','summary.json','ledger.json','failures.csv','binding.json','state.json'):
            z.write(out/name,name)
        for e in files_manifest(out/'overnight'):z.write(out/'overnight'/e['path'],'overnight/'+e['path'])
        for e in files_manifest(preview):
            if e['path']!='preview.json':z.write(preview/e['path'],'prepared/'+e['path'])
        # Full hashes/settings retained; no raw sources, PDFs or remote credentials.
        z.write(preview/'preview.json','prepared/preview.json')
        for c in read_json(out/'state.json')['calls']:
            folder=out/'calls'/c['id']
            for name in ('reservation.json','request.json','outcome.json'):
                if (folder/name).exists():z.write(folder/name,'calls/'+c['id']+'/'+name)
            ev=response_data(folder)
            z.writestr('calls/'+c['id']+'/response-summary.json',json.dumps({k:ev.get(k) for k in
                ('actual_model','finish_reason','content','usage','latency_seconds','http_status')},ensure_ascii=False,indent=2))
    with zipfile.ZipFile(dest) as z:
        if z.testzip():raise ValueError('Invalid inspection ZIP')
    record={'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest),
        'development_view':'overnight/development.html','reserved_view':'overnight/reserved.html'}
    atomic_json(out/'latest-bundle.json',record);print('Inspection ZIP:',dest,flush=True);return record


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('prepare');q.add_argument('--gate-run',required=True,type=Path);q.add_argument('--original-run',required=True,type=Path);q.add_argument('--gate-zip',required=True,type=Path)
    for name in ('launch','bundle'):
        q=sub.add_parser(name);q.add_argument('--run',required=True,type=Path)
        if name=='launch':q.add_argument('--readiness',required=True,type=Path);q.add_argument('--resume',action='store_true')
    a=p.parse_args(argv)
    with writer_lock(ROOT/'runs'):
        if a.command=='prepare':
            preview=ex.new_path(ROOT,'text-critic-overnight-input');out=ex.new_path(ROOT,'text-critic-overnight-trial')
            paths=prepare(a.gate_run,a.original_run,a.gate_zip,preview,out);paths['inspection_bundle']=bundle(ROOT,preview,out)
            atomic_json(ROOT/'results/critic-overnight-current.json',paths);print(json.dumps(paths,indent=2));return 0
        out=a.run.resolve();preview=Path(read_json(out/'binding.json')['preview']);meta,units=ex.verify_preview(preview);validate_protocol(meta,units)
        if a.command=='bundle':bundle(ROOT,preview,out);return 0
        try:return ex.execute(ROOT,out,stage='overnight',readiness=a.readiness.resolve(),resume=a.resume)
        finally:
            # execute clears active writer state on every controlled exit; do not package an interrupted writer as finished.
            state=read_json(out/'state.json')
            if state['active_since_epoch'] is None and state['status']!='running':bundle(ROOT,preview,out)


if __name__=='__main__':raise SystemExit(main())
