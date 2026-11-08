#!/usr/bin/env python3
"""Finite linked recovery using the existing image-review controller/scheduler."""
import copy,csv,difflib,hashlib,io,json,re,shutil,sys,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha,fingerprint
from probe.experiment import InputGuard,verify_seal
from probe import focused_recovery as edits,image_review as vision,chapter_glm as runtime,compiler_environment as compiler
from scripts import glm_image_review as controller
base=controller.base
POINTER=ROOT/'results/image-review-recovery-current.json'
SESSION='pdf-image-review-recovery'
TERMINAL='image_review_recovery_finished'
PARENT=ROOT/'runs/extraction-followup-20261105T223237Z-lifecycle'
IMAGES=ROOT/'runs/glm-image-review-20261106T133752Z-stages'
SID={'cf':'original-21debf82bc2c0a3d','spectral':'original-185f783748bb248e'}
EXPECTED={'cf':'db3211b963461b55d55fb04bb7ad3b8ffb5a1b8f994d8169b703627ca8596bc0','spectral':'9d41cfab99c079768075978613e7b020fc6b0d9b6f3074cc44a4cfb5aa40268f'}
EDITIONS={'cf':IMAGES/'repairs/original-21debf82bc2c0a3d/preserved-reading-edition','spectral':IMAGES/'repairs/Spectral-numbering-qualified','pvalues':IMAGES/'repairs/original-547334b059504dcb'}
# Observed complete cases/subsections, not page-count partitions.
UNITS=[
 ('cf-1','cf','p006-r007',r'\section*{Case 19.', 'Case 19, continuation and Continuous Distributions',[(6,[.13,.30,.90,.58]),(6,[.13,.65,.90,.92])]),
 ('cf-2','cf','p007-r004',r'\section*{Mixture Representations.}', 'Mixture Representations, through its complete continuation',[(7,[.13,.24,.90,.58]),(7,[.13,.57,.90,.92])]),
 ('cf-3','cf','p008-r003',r'\section*{Sums of Random Variables.}', 'Sums of Random Variables, complete conclusion and References',[(8,[.13,.24,.90,.59]),(8,[.13,.57,.90,.92]),(9,[.13,.08,.90,.48])]),
 ('spectral-1','spectral','p021-r012',r'\section*{6. Analytically', 'Section 6 introduction and complete 6.1 double barrier options, Table 1 and Figure 1',[(22,[.10,.30,.90,.69]),(23,[.10,.10,.90,.53]),(25,[.10,.08,.90,.43])]),
 ('spectral-2','spectral','p025-r005',r'\section*{6.2.', 'Complete 6.2.1 OU and 6.2.2 interest-rate models',[(25,[.10,.53,.90,.92]),(26,[.10,.11,.90,.31])]),
 ('spectral-3','spectral','p026-r008',r'\section*{6.3.', '6.3 introduction, complete 6.3.1 Bessel and 6.3.2 CIR models',[(26,[.10,.57,.90,.93]),(27,[.10,.11,.90,.52]),(28,[.10,.10,.90,.40])]),
 ('spectral-4','spectral','p028-r006',r'\subsection*{6.3.3.', 'Complete 6.3.3 three-halves model with Whittaker solutions and expansions',[(28,[.10,.37,.90,.92]),(29,[.10,.12,.90,.55]),(30,[.10,.12,.90,.56]),(31,[.10,.10,.90,.49])]),
 ('spectral-5','spectral','p031-r006',r'\subsection*{6.3.4.', 'Complete 6.3.4 CEV model through its continuation on page 32',[(31,[.10,.49,.90,.92]),(32,[.10,.09,.90,.27])]),
]

def assets(run,source):
 folder=run/'baseline-editions'/source
 return {str(p.relative_to(folder)):p for p in (folder/'assets').rglob('*') if p.is_file()}

def save(run,s):
 runtime.save(run,s)
 atomic_json(run/'progress.json',{'at':runtime.now(),'run':str(run),'status':s['status'],'stage':s.get('stage'),'diagnostic':s.get('diagnostic'),
  'work_calls_consumed':len(s['calls']),'work_ceiling':s.get('maximum_model_requests',12),'authorized_ceiling':14,'readiness_consumed':0,
  'historical_failed_reviews':{'calls':['call-004','call-010'],'parent':str(PARENT),'reasoning_tokens_each':131072,'allowances_preserved':True},
  'tasks':[{k:t.get(k) for k in ('id','status','call','review_response','images_verified','compilation','edition_selection','applied','withheld','unresolved','scope_review','review_complete_attested','pending_suggestions','codex_source_check')} for t in s['tasks']],
  'calls':[{'id':c['id'],'task':c['parent'],'status':c['status'],'seconds':c.get('elapsed_seconds'),'usage':c.get('metadata',{}).get('usage')} for c in s['calls']],
  'log':str(run/'terminal.log'),'outputs':str(run/'deliveries'),'inspection':s.get('inspection')})

def validate_plan(plan):
 units=plan['units'];tasks=plan['tasks'];ids=[t['id'] for t in tasks]
 if len(units)!=8 or len(ids)!=12 or len(set(ids))!=12:raise ValueError('Frozen scope/task cardinality changed')
 if plan['maximum_model_requests']!=12 or plan['maximum_work_requests']!=12 or plan['maximum_readiness_requests']!=1 or plan['planned_readiness_requests']!=0:raise ValueError('Explicit allowance contract mismatch')
 if [x for stage in plan['stages'] for x in stage]!=ids:raise ValueError('Stages omit/duplicate/reorder frozen tasks')
 for source in SID:
  expected=plan['source_ownership'][source]['expected_blocks'];actual=[b for u in units if u['source']==source for b in u['blocks']]
  edits.validate_partition([{'blocks':actual}],expected)
  ranges=[u['ranges'][0] for u in units if u['source']==source]
  if any(a[1]!=b[0] for a,b in zip(ranges,ranges[1:])):raise ValueError('Draft scope gap or overlap')
 for t in tasks:
  if t['effort'] not in ('high','max') or t['max_tokens']!=131072 or not 1<=t['budget']['image_count']<=8:raise ValueError('Settings or readable image allowance changed')
 if sum(t['kind']=='recovery' and t['effort']=='max' for t in tasks)!=8 or sum(t['kind']=='recovery' and t['effort']=='high' for t in tasks)!=2:raise ValueError('Recovery allowances changed')
 if plan['image_limits']!={'image_tokens':2048,'request_image_tokens':16384,'max_images':50}:raise ValueError('Image limits changed')

def freeze(run):
 if (run/'state.json').exists():return verify(run)
 plan=read_json(run/'plan-draft.json');validate_plan(plan);cpu=read_json(run/'cpu-preprocessing.json')
 if read_json(run/'annotation-repair/build/compilation.json')['status']!='passed':raise ValueError('Saved annotation repair not qualified')
 if read_json(run/'inputs/control-cf/baseline-build/compilation.json')['status']!='passed':raise ValueError('Test-only input does not compile')
 for t in plan['tasks']:
  t['cpu_expectation']=cpu['requests'][t['id']]
  if t['cpu_expectation']['image_rows']!=t['budget']['image_tokens']:raise ValueError('Installed image allocation differs')
 for required in ['effort-support-offline.json','evaluation/answer-key.json','scope-ownership.json']:
  if not (run/required).is_file():raise ValueError('Missing required preparation '+required)
 plan['status']='frozen';atomic_json(run/'plan.json',plan)
 old=read_json(run/'repair-state.json');s={k:copy.deepcopy(old[k]) for k in ['compiler_environment','concurrency_policy','chapter_contract','execution_limits','timing_policy']}
 s['execution_limits']['attempts_per_unit']=1
 s.update(status='prepared',created_at=runtime.now(),first_dispatch=None,calls=[],connection_failures=0,tasks=[],versions={},current_versions={},active_stage=0,
  stages={str(i+1):{} for i in range(len(plan['stages']))},stage_results={},launches=[],source_units={},documents={},disable_dependency_downloads=True,
  suite_protocol='source-image-review-v1',stage_index=0,maximum_model_requests=12)
 for t in plan['tasks']:
  s['tasks'].append({'id':t['id'],'key':t['id'],'source_key':t['source'],'phase':'critic','status':'pending','reasoning_effort':t['effort'],'base_sha256':t['draft_sha256'],
   'conversion':'reused_complete_saved_draft','review_response':'pending','edition_selection':'baseline','codex_source_check':'designated held-out checks only; future model output not yet checked'})
  s['versions'][t['id']]={'frozen-input':{'path':t['draft_path'],'sha256':t['draft_sha256']}};s['current_versions'][t['id']]='frozen-input'
  s['documents'][t['source']]={'filename':plan['sources'][t['source']]['filename']}
  s['source_units'][t['id']]={'section':{'title':t['title']}}
 s['production_stage']={'task_ids':[t['id'] for t in s['tasks']]}
 frozen={str(p):sha(p) for directory in ['inputs','sources','requests','evaluation','baseline-editions','annotation-repair'] for p in (run/directory).rglob('*') if p.is_file()}
 for name in ['cpu-preprocessing.json','effort-support-offline.json','scope-ownership.json','repair-state.json']:frozen[str(run/name)]=sha(run/name)
 frozen.update({d['original']:d['sha256'] for d in plan['sources'].values()})
 atomic_json(run/'binding.json',{'code':base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':frozen});save(run,s);return s

def verify(run):
 plan=read_json(run/'plan.json');validate_plan(plan);s=read_json(run/'state.json');b=read_json(run/'binding.json')
 if sha(run/'plan.json')!=b['plan_sha256'] or base.code_binding()!=b['code']:raise runtime.Fatal('Frozen implementation/plan changed; no dispatch')
 InputGuard(b['files']).check()
 if s.get('maximum_model_requests')!=12 or s['execution_limits']['attempts_per_unit']!=1:raise runtime.Fatal('Allowance contract changed')
 if set(s['stages'])!={str(i+1) for i in range(len(plan['stages']))}:raise runtime.Fatal('Resource stage records missing/expanded')
 if [t['id'] for t in s['tasks']]!=[t['id'] for t in plan['tasks']] or s['production_stage']['task_ids']!=[t['id'] for t in plan['tasks']]:raise runtime.Fatal('Task set changed')
 parents=[c['parent'] for c in s['calls']]
 if len(parents)>12 or len(set(parents))!=len(parents) or not set(parents)<=set(s['production_stage']['task_ids']):raise runtime.Fatal('Consumed request replay/expansion')
 for t,p in zip(s['tasks'],plan['tasks']):
  if t['base_sha256']!=p['draft_sha256'] or t['reasoning_effort']!=p['effort'] or t['key']!=p['id'] or t['source_key']!=p['source']:raise runtime.Fatal('Draft/settings changed')
 for c in s['calls']:
  if c.get('seal'):verify_seal(run/'calls'/c['id'],c['seal'])
 return s

def body_for(run,s,t):
 p=next(x for x in read_json(run/'plan.json')['tasks'] if x['id']==t['id']);body=read_json(run/'requests'/(t['id']+'.json'))
 if fingerprint(body)!=p['request_sha256']:raise runtime.Fatal('Prepared request changed')
 content=body['messages'][0]['content'];expected=vision.image_parts(read_json(run/p['images_manifest']),run)
 if vision.image_content(body)!=expected:raise runtime.Fatal('Outgoing original images changed')
 payload=vision.request_payload(body);draft=(run/p['draft_path']).read_text();supplied='\n\n'.join(draft[a:b] for a,b in p['ranges'])
 if payload['draft']!=supplied or payload['base_sha256']!=edits.digest(draft) or edits.digest(draft)!=t['base_sha256']:raise runtime.Fatal('Stale or wrong exact draft scope')
 return body

def before(run,s,t,body):
 verify(run)
 if t['id'] not in read_json(run/'plan.json')['stages'][s['stage_index']] or t['status']!='pending' or any(c['parent']==t['id'] for c in s['calls']):raise runtime.Fatal('Consumed/out-of-stage task cannot dispatch')
 if body!=body_for(run,s,t):raise runtime.Fatal('Outgoing request changed')
 print('SOURCE IMAGE REVIEW',t['id'],t['reasoning_effort'],'draft',t['base_sha256'],flush=True)

def finish(run,s,t,answer,call):
 if t.get('settled_call')==call['id']:return
 p=next(x for x in read_json(run/'plan.json')['tasks'] if x['id']==t['id']);expected=p['cpu_expectation'];usage=call.get('metadata',{}).get('usage',{})
 t.update(call=call['id'],images_verified=usage.get('prompt_tokens')==expected['prompt_tokens'] and expected['image_rows']>0)
 atomic_json(run/'image-verification'/(t['id']+'.json'),{'observed_server_prompt_tokens':usage.get('prompt_tokens'),'expected_installed_rendering':expected,'passed':t['images_verified'],'limits':'Server usage + installed CPU expansion; GPU tensors not directly captured'})
 if not t['images_verified']:save(run,s);raise runtime.Fatal('Image processing unverified; no text-only fallback')
 if answer is None:
  t.update(status=call.get('failure_kind','failed'),review_response='no_usable_answer',settled_call=call['id']);save(run,s);return
 dest=run/'reviews'/t['id'];dest.mkdir(parents=True,exist_ok=True);(dest/'proposal.txt').write_text(answer)
 draft=(run/p['draft_path']).read_text()
 try:
  proposal=edits.parse_json_response(edits.single_outer_fence(answer) or answer)
  revised,findings=vision.apply_review(draft,proposal,p['ranges'])
 except (ValueError,KeyError,TypeError) as exc:
  t.update(status='invalid_review',review_response='invalid_findings',reason=str(exc),settled_call=call['id']);save(run,s);return
 (dest/'original.tex').write_text(draft);(dest/'reviewed.tex').write_text(revised);atomic_json(dest/'findings.json',findings)
 (dest/'changes.diff').write_text(''.join(difflib.unified_diff(draft.splitlines(True),revised.splitlines(True),fromfile='frozen-input',tofile=t['id'])))
 build=dest/'build'
 if not (build/'compilation.json').exists():compiler.compile_saved(run,s,ROOT,revised,build,assets(run,p['source']))
 record=read_json(build/'compilation.json');selection=vision.compiling_selection({'path':p['draft_path'],'sha256':p['draft_sha256'],'build_provenance':p['baseline_build']},{'path':str((dest/'reviewed.tex').relative_to(run)),'sha256':edits.digest(revised)},record)
 atomic_json(dest/'selection.json',selection)
 t.update(status='review_completed',review_response='usable_focused_findings',compilation=record['status'],edition_selection=selection['status'],settled_call=call['id'],scope_review=findings['scope_review'],review_complete_attested=findings['review_complete_attested'],pending_suggestions=findings['pending_suggestions'],
  applied=sum(f['disposition']=='applied_model_claim' for f in findings['findings']),withheld=sum(f['disposition'] in ('rejected','unapplied_suggestion') for f in findings['findings']),unresolved=sum(f['disposition']=='unresolved' for f in findings['findings']))
 # Codex does not run continuously. This machine-located control measure is
 # explicitly provisional; unanticipated findings still need source adjudication.
 if p['kind']=='control':
  key=read_json(run/'evaluation/answer-key.json')['controlled_example'];good=key['printed_anchor'];bad=key['mutated_anchor']
  atomic_json(dest/'control-score.json',{'known_error_repaired':bad not in revised and good in revised,'unchanged_control_spans_retained':[x in revised for x in key['unchanged_anchors']],
   'unanticipated_findings_require_source_review':findings['findings'],'assessment':'Exact seeded-span check, not semantic scoring of every model claim or natural error-rate estimate'})
 save(run,s)

def finalize(run,s):
 """Apply only compiling Max recovery arms to exact matching repaired parts."""
 verify(run)
 plan=read_json(run/'plan.json');outcomes=[]
 for source in SID:
  dest=run/'deliveries'/source
  if (dest/'delivery.json').exists():outcomes.append(read_json(dest/'delivery.json'));continue
  baseline=run/'baseline-editions'/source;dest.mkdir(parents=True,exist_ok=True)
  for sub in ['parts','assets']:
   if (baseline/sub).exists():shutil.copytree(baseline/sub,dest/sub,dirs_exist_ok=True)
  shutil.copyfile(baseline/'master.tex',dest/'master.tex')
  target=dest/'parts'/(SID[source]+'-whole-3.tex');assembled=target.read_text();initial=assembled;applied=[];withheld=[]
  for p in plan['tasks']:
   if p['source']!=source or p['kind']!='recovery' or p['effort']!='max':continue
   task=next(t for t in s['tasks'] if t['id']==p['id']);f=run/'reviews'/p['id']/'findings.json'
   if task.get('compilation')!='passed' or not f.exists():withheld.append({'unit':p['id'],'reason':'Review/build unavailable; original compiling part retained'});continue
   for finding in read_json(f)['findings']:
    if finding['disposition']!='applied_model_claim':continue
    old,new=finding['old'],finding['new']
    if assembled.count(old)!=1:withheld.append({'unit':p['id'],'finding':finding,'reason':'Exact repaired-edition anchor not unique/present; no fuzzy rebase'});continue
    assembled=assembled.replace(old,new,1);applied.append({'unit':p['id'],'finding':finding})
  target.write_text(assembled);(dest/'changes.diff').write_text(''.join(difflib.unified_diff(initial.splitlines(True),assembled.splitlines(True),fromfile='repaired-parent-part',tofile='new-working-part')))
  inputs={str(p.relative_to(dest)):p for sub in ['parts','assets'] for p in (dest/sub).rglob('*') if p.is_file()}
  if not (dest/'build/compilation.json').exists():compiler.compile_saved(run,s,ROOT,(dest/'master.tex').read_text(),dest/'build',inputs)
  compilation=read_json(dest/'build/compilation.json')
  def edition_identity(folder):
   files={str(p.relative_to(folder)):sha(p) for sub in ['parts','assets'] for p in (folder/sub).rglob('*') if p.is_file()};files['master.tex']=sha(folder/'master.tex')
   return {'path':str(folder.relative_to(run)),'files':files,'edition_sha256':fingerprint(files)}
  selection=vision.compiling_selection(edition_identity(baseline),edition_identity(dest),compilation)
  if compilation['status']=='passed':shutil.copyfile(dest/'build/attempt-1/document.pdf',dest/'reading.pdf')
  record={'source':source,'status':compilation['status'],'selection':selection,'applied':applied,'withheld':withheld,
   'review_coverage':[{'unit':t['id'],'response':t.get('review_response'),'build':t.get('compilation'),'unresolved':t.get('unresolved'),'pending_suggestions':t.get('pending_suggestions',t.get('withheld',0)),'scope_review':t.get('scope_review'),'review_complete_attested':t.get('review_complete_attested',False)} for t in s['tasks'] if t['source_key']==source and t['reasoning_effort']=='max' and not t['id'].startswith('control')],
   'source_verification':'Existing eight Spectral corrections/numbering preserved; new model claims not independently checked by unattended worker',
   'unresolved_references':{'inherited':read_json(baseline/'assembly-log.json').get('unresolved_references',[]) if (baseline/'assembly-log.json').exists() else 'No separately recorded inherited reference ledger',
    'compiler_warnings':[line for line in (dest/'build/attempt-1/console.log').read_text(errors='replace').splitlines() if re.search(r'(?i)(undefined.*reference|reference.*undefined|citation.*undefined|multiply.defined)',line)] if (dest/'build/attempt-1/console.log').exists() else [],
    'policy':'No guessed reference resolution; compiler warnings do not establish completeness'}}
  atomic_json(dest/'delivery.json',record);outcomes.append(record)
 atomic_json(run/'deliveries/summary.json',{'papers':outcomes,'pvalues':'Unchanged repaired edition at baseline-editions/pvalues; no new review or compilation','recommendation_5':'DEFERRED pending assessment; no High adoption or selective-review rollout'})

def bundle(run,s):
 plan=read_json(run/'plan.json');rows=[]
 for c in s['calls']:
  p=next(t for t in plan['tasks'] if t['id']==c['parent']);u=c.get('metadata',{}).get('usage',{});reason=u.get('completion_tokens_details',{}).get('reasoning_tokens');total=u.get('completion_tokens');folder=run/'calls'/c['id'];meta=read_json(folder/'response-metadata.json') if (folder/'response-metadata.json').exists() else {}
  rows.append({'task':c['parent'],'call':c['id'],'effort':p['effort'],'status':c['status'],'elapsed_seconds':c.get('elapsed_seconds'),'reasoning_tokens':reason,'final_tokens':total-reason if isinstance(total,int) and isinstance(reason,int) else None,'cached_tokens':u.get('prompt_tokens_details',{}).get('cached_tokens'),'server_timings':meta.get('server_timings'),'scope':p['title']})
 atomic_json(run/'timings.json',rows)
 stream=io.StringIO();w=csv.DictWriter(stream,fieldnames=['task','call','effort','status','elapsed_seconds','reasoning_tokens','final_tokens','cached_tokens','scope']);w.writeheader();w.writerows({k:v for k,v in r.items() if k!='server_timings'} for r in rows);(run/'TIMINGS.csv').write_text(stream.getvalue())
 pairs=[]
 for unit in ['cf-1','spectral-2','control-cf']:
  results={effort:next((r for r in rows if r['task']==unit+'-'+effort),None) for effort in ['high','max']}
  pairs.append({'unit':unit,'results':results,'assessment':'Matched requests except effort; sequential order/cache effects recorded. A machine-located seeded-span score is separate from actual source assessment. All other proposals require located adjudication; Max is not ground truth.'})
 atomic_json(run/'quality-comparison.json',{'pairs':pairs,'limits':'Only one artificial positive error control; not natural error rates. No continuous Codex verification after launch. High rollout remains deferred.','codex_checked_before_launch':read_json(run/'evaluation/answer-key.json')})
 lines=['# Image-review recovery and High/Max follow-up','Status: '+s['status'],'Run: '+str(run),
 'Eight recovery Max reviews, two additional matched High reviews and one artificial control at both efforts:12 calls maximum; one attempt each; zero planned readiness. No conversion/OCR/paid calls or service changes.',
 'Original two exhausted131072-token reviews remain consumed in the historical parent. The new scope-ownership manifest assigns every native source region once. Shared page images are context, not duplicate review ownership.',
 'The saved CF-A annotation repair is in annotation-repair/. It changes explanatory rendering only; original equations are unchanged. All source-faithful drafts and failed builds remain in their original paths.',
 'Read plan.json, scope-ownership.json, TIMINGS.csv, quality-comparison.json, reviews/*/findings.json and selection.json, and deliveries/summary.json. Compilation is not mathematical verification; findings are attributed model claims, not automatically source-checked.',
 'For error detection see evaluation/answer-key.json and control-score.json. Answers/mutation records were excluded from requests. Control outputs never enter reading editions. The historical CF27b Gamma(b+n) reading is retained as print; no Gamma(d+n) answer key.',
 'Preserved corrected editions: baseline-editions/{cf,spectral,pvalues}. Spectral eight checked corrections and source numbering remain. New candidate editions are selected only after passing compilation; failed builds retain the previous selection. P-values is unchanged.',
 'Recommendation5 (broad selective review and corpus-wide High adoption) is DEFERRED. Cooking excluded, GLM-OCR unused,350-source audit deferred. This run stops; it cannot launch production.',
 '## Tasks']+[t['id']+': '+t['status']+'; compilation='+str(t.get('compilation'))+'; selection='+str(t.get('edition_selection')) for t in s['tasks']]
 (run/'START-HERE.md').write_text('\n\n'.join(lines)+'\n')
 out=ROOT/'results/inspection'/('image-review-recovery-'+run.name+'-'+str(time.time_ns())+'.zip');out.parent.mkdir(parents=True,exist_ok=True);members={};omitted=[]
 for p in run.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(run)
  if any(x in rel.parts for x in ['requests','calls','samples','compiler-environments','runtime-bindings']) or p.name.endswith('.lock') or 'reasoning' in p.name or p.stat().st_size>8*1024**2 or 'pass-1' in rel.parts or 'pass-2' in rel.parts or p.name in ['document.log','terminal.log']:
   omitted.append({'path':str(p),'bytes':p.stat().st_size});continue
  # Build inputs/PDF duplicates remain locally; selected sources/PDFs included once.
  if 'attempt-1' in rel.parts and p.suffix in ('.tex','.pdf','.png'):continue
  members[str(rel)]=p.read_bytes()
 for t in plan['tasks']:members['request-metadata/'+t['id']+'.json']=json.dumps(t,indent=2).encode()
 for name in ['scripts/image_review_recovery.py','scripts/prepare_image_review_recovery.py','scripts/glm_image_review.py','scripts/run-image-review-recovery.sh','probe/image_review.py','tests/test_image_review_recovery.py','docs/IMAGE-REVIEW-RECOVERY.md']:
  if (ROOT/name).exists():members['implementation/'+name]=(ROOT/name).read_bytes()
 members['OMITTED.json']=json.dumps(omitted,indent=2).encode()
 manifest=[{'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in sorted(members.items())]
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  for name,data in members.items():z.writestr(name,data)
  z.writestr('FILE-HASHES.json',json.dumps(manifest,indent=2))
 with zipfile.ZipFile(out) as z:
  if z.testzip():raise runtime.Fatal('Archive CRC failure')
  if set(z.namelist())!={x['path'] for x in manifest}|{'FILE-HASHES.json'}:raise runtime.Fatal('Archive manifest omissions')
  for r in manifest:
   if hashlib.sha256(z.read(r['path'])).hexdigest()!=r['sha256']:raise runtime.Fatal('Archive hash failure')
 s['inspection']=str(out);save(run,s);atomic_json(run/'inspection.json',{'path':str(out),'bytes':out.stat().st_size,'sha256':sha(out),'crc_and_all_member_hashes':'verified'});return out

if __name__=='__main__':controller.main(sys.modules[__name__])
