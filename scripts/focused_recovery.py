#!/usr/bin/env python3
"""Finite local recovery trial. Never invokes the originals production worker."""
import argparse,copy,difflib,json,os,re,shlex,shutil,subprocess,sys,time,uuid,zipfile
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import originals_batch as collection
from probe import focused_recovery as core, chapter_glm as runtime, chapter_concurrency as concurrent
from probe import book_completion as scope, originals_recovery as repair, tex_syntax_repair as syntax, chapter_inputs, chapter_sources, cli
from probe.common import atomic_json,read_json,sha,fingerprint,writer_lock,files_manifest
from probe.experiment import InputGuard,seal,verify_seal
from probe.saved_pages import render_region
books=collection.books
POINTER=ROOT/'results/focused-recovery-current.json';SESSION='pdf-focused-recovery';TERMINAL='focused_trial_finished'
CF=repair.SOURCE;SP='original-185f783748bb248e';PATH='original-26781ea8225bd6e9';BIAS='original-ead9d04e4c78147d';ALT='original-ba2b65da21f13b69'
AN='original-496de5aa992285e2';BB='original-1fc68aa26e4deb3b';CONTROL='original-dcbf009549ec6318';SOURCES=(CF,SP,PATH,BIAS,ALT,AN,BB,CONTROL)
PYTHON=ROOT/'.venv-control/bin/python'

def code_hashes():return {str(p.relative_to(ROOT)):sha(p) for d in ('probe','scripts') for p in (ROOT/d).glob('*.py')}
def copy_file(src,dest):
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
 if sha(src)!=sha(dest):raise runtime.Fatal('Copy identity mismatch')
def pause(run):
 if (run/'pause.json').exists():raise runtime.StopRun('Operator pause: drained before next owned phase')
def definition(t):return {k:t[k] for k in ('id','key','source_key','phase','reasoning_effort','depends_on','arm')}

def verify(run):
 s=read_json(run/'state.json');b=read_json(run/'binding.json')
 if b['code']!=code_hashes() or fingerprint(b)!=s['binding_sha256']:raise runtime.Fatal('Trial code/binding changed')
 InputGuard(b['frozen']).check();plan=read_json(run/'plan.json')
 if s['suite_protocol']!=core.VERSION or s['execution_limits']!={'calls':None,'attempts_per_unit':1} or s['timing_policy']!='manual_only' or s['concurrency_policy']!=concurrent.POLICY:raise runtime.Fatal('Trial settings changed')
 allowed={x['id'] for x in plan['tasks']}
 if set(s['production_stage']['task_ids'])!=allowed or any(c['parent'] not in allowed|{'readiness'} for c in s['calls']):raise runtime.Fatal('Unscheduled reservation')
 for sid,d in plan['sources'].items():
  if any(s['documents'][sid].get(k)!=d[k] for k in ('filename','source_sha256','pages','original')):raise runtime.Fatal('Source identity changed')
 if s.get('qualified_warp_continuation')!=plan.get('qualified_warp_continuation'):raise runtime.Fatal('Qualified OCR continuation authority changed')
 if [definition(t) for t in s['tasks']]!=plan['tasks']:raise runtime.Fatal('Frozen trial schedule changed')
 for key,unit in plan['units'].items():
  if key!='spectral-section' and s['source_units'][key]!=unit:raise runtime.Fatal('Frozen source/output scope changed')
 if s.get('spectral_scope_seal'):
  verify_seal(run/'spectral-scope',s['spectral_scope_seal'])
  if s['source_units']['spectral-section']!=read_json(run/'spectral-scope/unit.json'):raise runtime.Fatal('Resolved Spectral scope changed')
 if any(sum(c['parent']==t['id'] for c in s['calls'])>1 for t in s['tasks']):raise runtime.Fatal('Phase allowance exceeded')
 if sum(c['parent']=='readiness' for c in s['calls'])>1:raise runtime.Fatal('Readiness allowance exceeded')
 for c in s['calls']:
  if c.get('seal'):verify_seal(run/'calls'/c['id'],c['seal'])
 for key,vs in s['versions'].items():
  for v in vs.values():
   if sha(run/v['path'])!=v['sha256']:raise runtime.Fatal('Saved draft identity changed')
 for name,digest in s.get('derived_inputs',{}).items():
  if sha(run/name)!=digest:raise runtime.Fatal('Derived OCR input changed')
 return s

def find(native,pattern):
 hits=[b['id'] for b in native['blocks'] if re.search(pattern,b['tex'])]
 if len(hits)!=1:raise ValueError('Structural anchor not unique: '+pattern+' '+str(hits))
 return hits[0]

def selected(native,a,b=None,title='Assigned passage'):
 blocks=[x for x in native['blocks'] if x['kind'] not in scope.FURNITURE];ids=[x['id'] for x in blocks];i=ids.index(a);j=ids.index(b) if b else len(ids)
 return scope.target(native,ids[i:j],title=title)

def add_unit(state,key,sid,section,effort='high',saved=None,ranges=None):
 state['source_units'][key]={'source_key':sid,'section':section,'saved_draft':saved,'editable_ranges':ranges}
 if saved:phases=[('critic','low' if sid==PATH else 'max','primary',None)]
 else:phases=[('convert',effort,'primary',None),('critic','max','primary',key+'/convert')]
 if any(p=='critic' and e=='max' for p,e,_,_ in phases):phases.append(('critic','low','critic_recovery',key+'/critic'))
 phases.append(('syntax','low','syntax',None))
 for phase,e,arm,dep in phases:
  ident=key+'/'+('critic-low-recovery' if arm=='critic_recovery' else phase)
  state['tasks'].append({'id':ident,'key':key,'source_key':sid,'phase':phase,'reasoning_effort':e,'arm':arm,'depends_on':dep,'status':'dormant' if arm!='primary' else 'pending'})

def excerpt_range(text,start,end):
 a=re.search(start,text,re.I);b=re.search(end,text[a.end():],re.I) if a else None
 if not a or not b:raise ValueError('Saved draft passage anchors ambiguous/unavailable')
 return [[a.start(),a.end()+b.start()]]

def prepare():
 if POINTER.exists():
  r=Path(read_json(POINTER)['run']);verify(r);print('Existing trial:',r);return r
 parent=Path(read_json(collection.POINTER)['run']);ps=read_json(parent/'state.json')
 if ps['status']!='collection_finished_with_report' or not all(books.speed.idle(p) for p in (ROOT,ROOT/'runs',parent)):raise runtime.Fatal('Source run/writer is not settled')
 with writer_lock(ROOT),writer_lock(ROOT/'runs'):
  run=ROOT/'runs'/('focused-recovery-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:6]);run.mkdir()
  manifest=read_json(parent/'collection.json');docs={d['source_id']:d for d in manifest['documents']};env=copy.deepcopy(ps['compiler_environment']);shutil.copytree(parent/env['path'],run/env['path'])
  s={'status':'prepared_offline','created_at':runtime.now(),'suite_protocol':core.VERSION,'chapter_contract':'annotated-chapter-v1','timing_policy':'manual_only','execution_limits':{'calls':None,'attempts_per_unit':1},'first_dispatch':None,'calls':[],'tasks':[],'versions':{},'current_versions':{},'accuracy':{},'accuracy_records':{},'source_units':{},'selection_ledger':[],'compiler_environment':env,'connection_failures':0,'concurrency_policy':copy.deepcopy(concurrent.POLICY),'active_stage':1,'stages':{'1':{}},'production_stage':{'task_ids':[]},'documents':{},'resource_phase':'not_started','launches':[],'derived_inputs':{},'syntax_lineages':{},'ocr_status':'pending','parent':str(parent),'readiness_done':False}
  for name in ('state.json','collection.json'):copy_file(parent/name,run/'parent'/name)
  copy_file(parent/'effort-support-offline.json',run/'effort-support-offline.json')
  for sid in SOURCES:
   d=docs[sid];rec=ps['documents'][sid]
   if sha(parent/rec['original'])!=d['sha256']:raise runtime.Fatal('Original identity mismatch')
   s['documents'][sid]={'filename':d['originals'][0]['name'],'source_sha256':d['sha256'],'pages':d['page_count'],'original':str(parent/rec['original'])}
   if sid==SP:continue
   shutil.copytree(parent/'inputs'/sid,run/'inputs'/sid)
   for a in read_json(parent/'inputs'/sid/'assets.json'):copy_file(parent/'inputs'/a,run/'inputs'/a)
   quality=core.secondary_assessment(read_json(run/'inputs'/sid/'secondary.json')['pages']);atomic_json(run/'quality'/(sid+'.json'),quality)
  n=read_json(run/'inputs'/CF/'native.json')
  for key,a,b in [('cf-cases-1-3',r'^Case 1\.',r'^Case 4\.'),('cf-cases-16-18',r'^Case 16\.',r'^Case 19\. McNolty')]:add_unit(s,key,CF,selected(n,find(n,a),find(n,b),key),'low')
  n=read_json(run/'inputs'/BIAS/'native.json');cuts=[find(n,r'\\subsection\*\{3 Monte'),find(n,r'\\subsection\*\{6 Appendix')]
  for i,u in enumerate(core.partition(n,cuts,'Mean Reversion Bias'),1):add_unit(s,'mean-bias-'+str(i),BIAS,scope.target(n,u['blocks'],title=u['title']),'low')
  n=read_json(run/'inputs'/ALT/'native.json');cuts=[find(n,r'\\subsection\*\{'+number+r' '+title) for number,title in [('4','Generalized'),('5','Function'),('6','Application'),('7','Numerical'),('8','Conclusion')]]
  for i,u in enumerate(core.partition(n,cuts,'Alternatives to DL'),1):
   if u['expected_output_tokens_upper']>60000:raise ValueError('Structural unit exceeds output planning bound: '+u['title'])
   add_unit(s,'alternatives-'+str(i),ALT,scope.target(n,u['blocks'],title=u['title']))
  add_unit(s,'spectral-section',SP,{'resolver':{'first_heading':r'^6\.2\.','end_heading':r'^6\.4\.','meaning':'Complete OU and Bessel sections after qualified OCR; no whole-paper conversion'}},'high')
  # Retain exact saved whole drafts; only named ranges are editable by review.
  for sid,key,pages,start,end,label in [(PATH,'pathint-barriers',[26,27,28,29,30,31,32],r'\\subsection\*?\{[^}]*4\.2',r'\\(?:section|subsection)\*?\{[^}]*5\.', 'convert-call-098-annotated'),(AN,'anfuso-appendix',[8,9],r'\\section\*?\{Calculation of',r'\\(?:section|subsection)\*?\{[^}]*[Aa]cknowledg',None),(CONTROL,'information-control',[3,4],r'\\section\*?\{2 Information',r'\\section\*?\{3 Risks',None)]:
   oldkey=ps['documents'][sid]['units'][0];label=label or ps['current_versions'][oldkey];v=ps['versions'][oldkey][label];text=(parent/v['path']).read_text();n=read_json(run/'inputs'/sid/'native.json');target=scope.target(n,[b['id'] for b in n['blocks'] if b['kind'] not in scope.FURNITURE and b['page']['original_physical_page'] in pages],title=key)
   anchors={PATH:(r'\\subsection\*\{4\.2\.',r'\\subsection\*\{5\. Conclusion'),AN:(r'\\subsection\*\{A Calculation',r'\\subsection\*\{Acknowledgements'),CONTROL:(r'\\subsection\*\{2 Information',r'\\subsection\*\{3 Risks')}
   first_anchor,last_anchor=anchors[sid];target=selected(n,find(n,first_anchor),find(n,last_anchor),key)
   ranges=excerpt_range(text,start,end);add_unit(s,key,sid,target,saved={'parent_version':label,'sha256':v['sha256'],'path':str(parent/v['path'])},ranges=ranges);books.remember(run,s,key,'saved-baseline',text,{'parent':str(parent/v['path']),'sha256':v['sha256']});s['current_versions'][key]='saved-baseline'
  n=read_json(run/'inputs'/BB/'native.json');target=scope.target(n,[b['id'] for b in n['blocks'] if b['kind'] not in scope.FURNITURE and b['page']['original_physical_page']==6],title='Breaking Barriers final page with original figure')
  asset=run/'inputs/assets/breaking-barriers-original-figure-4.png';record=render_region(Path(s['documents'][BB]['original']),5,asset,bbox=[.085,.185,.355,.423],max_edge=1000);atomic_json(run/'evidence/figure4-provenance.json',record)
  aa=read_json(run/'inputs'/BB/'assets.json');aa.append('assets/'+asset.name);atomic_json(run/'inputs'/BB/'assets.json',aa)
  (run/'inputs'/BB/'manifest.json').rename(run/'inputs'/BB/'parent-input-manifest.json');seal(run/'inputs'/BB)
  target['source_image_addition']={'original_page':6,'asset':'assets/'+asset.name,'sha256':sha(asset)};add_unit(s,'breaking-figure',BB,target)
  for key,row in s['source_units'].items():
   if row.get('saved_draft'):
    s['selection_ledger'].append({'unit':key,'source_key':row['source_key'],'blocks':row['section']['blocks'],'selection':'saved-baseline','version_sha256':row['saved_draft']['sha256']})
    oldkey=ps['documents'][row['source_key']]['units'][0]
    if (parent/'accuracy'/oldkey).exists():shutil.copytree(parent/'accuracy'/oldkey,run/'baseline/accuracy'/key)
  # Whole Low CF comparison is retained and deterministically repaired, never reconverted here.
  oldkey=repair.KEY;v=ps['versions'][oldkey][ps['current_versions'][oldkey]];copy_file(parent/v['path'],run/'baseline/cf-low.tex');atomic_json(run/'baseline/cf-identity.json',v)
  for sid,pset in [(CF,[1,5,6]),(AN,[8,9]),(BB,[6]),(PATH,[30,31]),(BIAS,[7,21]),(CONTROL,[3])]:
   for p in pset:render_region(Path(s['documents'][sid]['original']),p-1,run/'evidence'/f'{sid}-p{p}.png',max_edge=1400)
  atomic_json(run/'evaluation/held-out.json',{'never_in_request':True,'anfuso':{'source_checked_pages':[8,9],'printed_numerator':'alpha+rho*X','independence':'X and epsilon stated independent in appendix; distinguish conditional eta from earlier noise','assessment':'Original numerator supported by conditional representation; model change requires correction or explicit unresolved note'},'breaking':{'source_checked_page':6,'required_asset':'assets/'+asset.name,'figure_parameters':{'r':.05,'d':.03,'sigma':.15,'H':100}},'cf':{'tag_number_to_preserve':'33','mathematical_status':'Individual case formulas still require independent checking'}})
  for key,row in s['source_units'].items():
   if key=='spectral-section':continue
   # Broad but bounded complete earlier definitions, never duplicate output ownership.
   n=read_json(run/'inputs'/row['source_key']/'native.json');blocks=[b for b in n['blocks'] if b['kind'] not in scope.FURNITURE];owned=set(row['section']['blocks']);first=next(i for i,b in enumerate(blocks) if b['id'] in owned)
   context=blocks[:min(first,20)]+blocks[max(0,first-3):first];unique={b['id']:b for b in context if b['id'] not in owned};row['context']='\n\n'.join(b['tex'] for b in unique.values());row['context_blocks']=list(unique)
  path_native=read_json(run/'inputs'/PATH/'native.json');context_section=selected(path_native,find(path_native,r'\\subsection\*\{2\.1\.'),find(path_native,r'\\subsection\*\{2\.2\.'),'Black Scholes definitions')
  s['source_units']['pathint-barriers']['context']=context_section['text'];s['source_units']['pathint-barriers']['context_blocks']=context_section['blocks']
  atomic_json(run/'evidence/model-capabilities.json',{'model':'glm53-regular','request_modality':'text only','image_support':'not established; no image requests attempted','effort_support':'installed mapping/template must match at every launch; actual internal effort is not attested by response'})
  s['production_stage']['task_ids']=[t['id'] for t in s['tasks']]
  plan={'protocol':core.VERSION,'parent':str(parent),'parent_state_sha256':sha(parent/'state.json'),'sources':s['documents'],'units':copy.deepcopy(s['source_units']),'tasks':[definition(t) for t in s['tasks']],
        'maximum_model_requests':len(s['tasks'])+1,'request_derivation':dict(Counter(t['arm']+'_'+t['phase'] for t in s['tasks'])),'readiness':1,'fallbacks':'At most one Low focused-critic recovery for failed primary Max criticism, same exact baseline and scope. No conversion repeat/subdivision; planned section conversions are the sole recovery round for historical failures. One final selected-version syntax request per unit. No recursive splitting.',
        'ocr':'One diagnostic pass over missing windows, preserving 24 completed pages; one evidence-gated subpixel correction pass if and only if the observed exact caller/geometry qualifies; maximum parent+2 attempts on failed window. Later windows once per pass; no service setting changes.',
        'scope_note':'CF covers two case groups; Pathint and controls are passage reviews; Mean Bias and Alternatives output partitions cover their full saved assigned source; Spectral conversion is only sections 6.2–6.3 after OCR.'}
  previous=ROOT/'results/focused-recovery-development-20261103/unlaunched-preparation.json'
  if previous.exists():plan['previous_unlaunched_preparation']=read_json(previous)
  atomic_json(run/'plan.json',plan)
  frozen={str(p):sha(p) for p in run.rglob('*') if p.is_file()};frozen[str(parent/'state.json')]=sha(parent/'state.json')
  for sid in SOURCES:frozen[s['documents'][sid]['original']]=s['documents'][sid]['source_sha256']
  for p in (ROOT/'.venv-mineru/lib/python3.12/site-packages/docvortex/foundation/_image_numeric.py',ROOT/'.venv-mineru/lib/python3.12/site-packages/mineru/model/ocr/image.py',ROOT/'.venv-mineru/lib/python3.12/site-packages/mineru/model/ocr/results.py'):
   frozen[str(p)]=sha(p)
  b={'code':code_hashes(),'frozen':frozen,'helper_hashes':collection.helper_hashes(books.speed.module())};atomic_json(run/'binding.json',b);s['binding_sha256']=fingerprint(b);runtime.save(run,s);atomic_json(POINTER,{'run':str(run),'prepared':True});progress(run,s);print('PREPARED',run,'maximum requests',plan['maximum_model_requests']);return run

def progress(run,s):
 rows=[]
 for c in s['calls']:
  u=c.get('metadata',{}).get('usage',{});n=u.get('completion_tokens');r=u.get('completion_tokens_details',{}).get('reasoning_tokens');rows.append({'call':c['id'],'task':c['parent'],'status':c['status'],'seconds':c.get('elapsed_seconds',time.time()-c['reserved_epoch'] if c['status']=='in_progress' else None),'completion_tokens':n,'reasoning_tokens':r,'final_tokens':n-r if isinstance(n,int) and isinstance(r,int) else None})
 atomic_json(run/'progress.json',{'at':runtime.now(),'run':str(run),'status':s['status'],'stage':s.get('stage'),'ocr':s.get('ocr_status'),'spectral_extraction':s.get('spectral_extraction'),'spectral_preparation':s.get('spectral_preparation'),'tasks':[{k:t.get(k) for k in ('id','status','call','error','failure_class')} for t in s['tasks']], 'counts':dict(Counter(t['status'] for t in s['tasks'])),'calls':rows,'diagnostic':s.get('diagnostic'),'maximum_requests':read_json(run/'plan.json')['maximum_model_requests'],'total_completed_request_seconds':sum(c.get('elapsed_seconds',0) for c in s['calls']),'log':str(run/'terminal.log')})

def body_for(run,s,t):
 row=s['source_units'][t['key']]
 if t['phase']=='syntax':return read_json(run/t['plan_path']/'request.json')
 if t['source_key']==SP and not row.get('section',{}).get('blocks'):return None
 sec=row['section'];q=read_json(run/'quality'/(t['source_key']+'.json'));secondary=chapter_sources.render_pages([p for p in q['pages'] if p['physical_pdf_page'] in sec['physical_pages']]);context=row.get('context','')
 primary=sec['text']
 if sec.get('source_image_addition'):primary+='\n\nOriginal source figure image supplied with this scope: '+r'\includegraphics{'+sec['source_image_addition']['asset']+'}'
 if t['phase']=='convert':return core.conversion_request(primary,secondary,context,t['reasoning_effort'],read_json(run/'inputs'/t['source_key']/'assets.json'))
 label=t.get('base_label') or s['current_versions'].get(t['key'])
 if not label:return None
 v=s['versions'][t['key']][label];text=(run/v['path']).read_text();return core.critic_request(text,primary,secondary,context,t['reasoning_effort'],row.get('editable_ranges'))

def before(run,s,t,body):
 if t['status']!='pending' or any(c['parent']==t['id'] for c in s['calls']):raise runtime.Fatal('Consumed task allowance')
 if body!=body_for(run,s,t):raise runtime.Fatal('Request changed')
 if t['reasoning_effort']=='low' and not s.get('low_supported'):raise runtime.Fatal('Low template not verified')
 if t['phase']=='critic':
  label=t.get('base_label') or s['current_versions'][t['key']];t['base_label']=label;t['base_sha256']=s['versions'][t['key']][label]['sha256']
  atomic_json(run/'dispatch'/ (t['id'].replace('/','-')+'.json'),{'draft_label':label,'draft_sha256':t['base_sha256'],'request_sha256':fingerprint(body)})
 print('TRIAL',s['documents'][t['source_key']]['filename'],t['id'],t['reasoning_effort'],flush=True)

def compile_version(run,s,key,label):return collection.compile_version(run,s,key,label)

def finish(run,s,t,answer,call):
 if t.get('settled_call')==call['id']:return
 key=t['key'];row=s['source_units'][key];t['call']=call['id']
 if t['phase']=='syntax':repair.finish_syntax(sys.modules[__name__],run,s,t,answer,call);return
 raw=(run/'calls'/call['id']/'answer.txt').read_text() if (run/'calls'/call['id']/'answer.txt').exists() else ''
 t['failure_class']=core.classify(call,raw)
 if answer is None:t.update(status=call.get('failure_kind','failed'),settled_call=call['id']);return
 if t['phase']=='convert':
  t['section']=row['section'];books.finish(run,s,t,answer,call,compiler=compile_version)
  for label,v in s['versions'].get(key,{}).items():
   if v.get('compilation',{}).get('status')=='not_attempted':compile_version(run,s,key,label)
 else:
  base=s['versions'][key][t['base_label']];text=(run/base['path']).read_text()
  if sha(run/base['path'])!=t['base_sha256']:raise runtime.Fatal('Actual critic draft changed')
  try:revised,log=core.apply_focused(text,answer,row.get('editable_ranges'))
  except (ValueError,AssertionError,TypeError,KeyError) as exc:
   t.update(status='focused_patch_rejected',error=str(exc),settled_call=call['id']);runtime.save(run,s);return
  label='focused-'+call['id'];books.remember(run,s,key,label,revised,{'call':call['id'],'base_sha256':t['base_sha256'],'focused_findings':log});s['current_versions'][key]=label
  atomic_json(run/'accuracy'/key/(label+'.json'),log);p=run/'accuracy'/key/(label+'.diff');p.write_text(''.join(difflib.unified_diff(text.splitlines(True),revised.splitlines(True),fromfile=t['base_label'],tofile=label)));compile_version(run,s,key,label)
  native=read_json(run/'inputs'/t['source_key']/'native.json');t['coverage_check']=scope.coverage_check(revised,native,row['section']['blocks'])
  ledger=next((x for x in s['selection_ledger'] if x['unit']==key),None)
  entry={'unit':key,'source_key':t['source_key'],'blocks':row['section']['blocks'],'selection':label,'version_sha256':s['versions'][key][label]['sha256'],'source_checked':'designated checks only; not wholesale mathematical verification'}
  if ledger is None:s['selection_ledger'].append(entry)
  else:ledger.update(entry)
  t.update(status='critic_revised' if revised!=text else 'critic_unchanged',final_version=label,findings=log)
  t['settled_call']=call['id']
 runtime.save(run,s)

def adjust(run,s):
 """Resolve fixed conditional tasks; never append a new model task."""
 byid={t['id']:t for t in s['tasks']}
 for t in s['tasks']:
  if t['arm']=='critic_recovery' and t['status']=='dormant':
   parent=byid[t['depends_on']]
   if parent['status'] in ('pending','running'):continue
   if parent['status'] in ('truncation','focused_patch_rejected','complete_answer_without_document') and parent.get('base_label'):
    t.update(status='pending',base_label=parent['base_label'],base_sha256=parent['base_sha256'])
   else:t['status']='not_needed'
 for t in s['tasks']:
  if t['arm']!='syntax' or t['status']!='dormant':continue
  siblings=[x for x in s['tasks'] if x['key']==t['key'] and x['phase']!='syntax']
  if any(x['status'] in ('pending','running','dormant') for x in siblings):continue
  key=t['key'];label=s['current_versions'].get(key)
  if not label:t['status']='unavailable';continue
  v=s['versions'][key][label]
  if v.get('compilation',{}).get('status','').startswith('passed'):t['status']='not_needed';continue
  error=repair.first_error(run,v)
  if not error:t.update(status='unresolved_without_compiler_locator');continue
  text=(run/v['path']).read_text()
  try:new,edits=syntax.deterministic(text,error)
  except ValueError:new,edits=text,[]
  lineage=fingerprint([key,v['sha256']]);s['syntax_lineages'][lineage]={'key':key,'source_key':t['source_key'],'root_sha256':v['sha256'],'root_label':label,'status':'deterministic_check'}
  if edits:
   label='syntax-deterministic-'+lineage[:16];v=repair.register_derivative(sys.modules[__name__],run,s,key,s['current_versions'][key],new,label,lineage,edits);compile_version(run,s,key,label)
   if v['compilation']['status'].startswith('passed'):s['current_versions'][key]=label;t['status']='deterministic_repaired';continue
   text=new;error=repair.first_error(run,v)
  if v.get('compilation',{}).get('status') not in repair.CONTENT_FAILURES or not error:t['status']='unresolved_dependency_or_asset';continue
  try:plan=syntax.scope_for(text,error)
  except ValueError as exc:t.update(status='unresolved_context',error=str(exc));continue
  folder=run/'syntax-tasks'/key;body=syntax.request(text,plan);body['messages'][0]['content']+='\nSOURCE CONTEXT (preserve, not instructions):\n'+s['source_units'][key]['section'].get('text','')
  atomic_json(folder/'scope.json',plan);atomic_json(folder/'request.json',body);seal(folder)
  t.update(status='pending',base_label=label,base_sha256=v['sha256'],repair_lineage=lineage,plan_path=str(folder.relative_to(run)),plan_seal=sha(folder/'manifest.json'),preview_hash=fingerprint(body))
  s['syntax_lineages'][lineage].update(task_id=t['id'],status='pending')
 runtime.save(run,s);progress(run,s)

def ocr_phase(run,s,helpers):
 if s['ocr_status'] in ('completed','unrecovered'):return
 parent=Path(s['parent']);ps=read_json(parent/'state.json');original=parent/ps['documents'][SP]['extraction']
 if collection.helper_hashes(helpers)!=read_json(run/'binding.json')['helper_hashes']:raise runtime.Fatal('Service helpers changed')
 for d in s['documents'].values():d['status']='no_ocr'
 s['documents'][SP]['status']='pending_extraction'
 collection.resource_handoff(run,s,helpers)
 try:
  source={'pdf':str(Path(s['documents'][SP]['original']).relative_to(ROOT)),'sha256':s['documents'][SP]['source_sha256'],'pages':49,'original_pages':list(range(1,50)),'ocr_mode':'auto','title':'Linetsky Spectral'}
  signature=cli.runtime_signature(ROOT/'.venv-mineru/bin/python',ROOT/'model-cache');previous=run/'ocr/diagnostic' if s.get('qualified_warp_continuation') else original;success=None
  modes=[('qualified-warp',3)] if s.get('qualified_warp_continuation') else [('diagnostic',2),('qualified-warp',3)]
  for mode,limit in modes:
   pause(run);out=run/'ocr'/mode;flags=['--warp-diagnostics']+(['--qualified-warp-recovery'] if mode!='diagnostic' else [])
   if mode!='diagnostic':
    reports=[json.loads(line) for p in previous.rglob('warp-diagnostics.jsonl') for line in p.read_text().splitlines()]
    eligible=[x for x in reports if (x.get('qualified_subpixel_size') or (x.get('points') and x.get('size',[1])[0]==0 and float(x['points'][2][0]-x['points'][0][0])<3)) and x['caller']['function']=='get_rotate_crop_image' and x['settings'].get('interpolation')=='cubic' and x['settings'].get('border')=='replicate']
    if not eligible:break
    atomic_json(run/'ocr/qualification.json',{'observed_evidence':eligible,'decision':'One local correction pass: move the installed width<3 rejection before cropping; positive in-image subpixel quads may use qualified ceil sizing. Same upstream rejection predicate; other failures remain unresolved.'})
   args=cli.parser().parse_args(['--config',str(ROOT/'config.example.json'),'convert','--source',SP,'--tier','basic','--ocr-isolation','none','--converter-python',str(ROOT/'.venv-mineru/bin/python'),'--models-dir',str(ROOT/'model-cache')])
   old=read_json(previous/'state.json');initial=copy.deepcopy(old['units'])
   if not (out/'state.json').exists():
    out.mkdir(parents=True,exist_ok=True)
    for record in initial.values():
     if record['status']=='running':raise runtime.Fatal('Uncertain OCR window cannot replay')
     if record['status']=='completed' and not cli.completed_integrity(previous,record):raise runtime.Fatal('Saved OCR evidence changed')
    shutil.copytree(previous/'attempts',out/'attempts',dirs_exist_ok=True)
    atomic_json(out/'linked-parent.json',{'path':str(previous),'state_sha256':sha(previous/'state.json'),'inherited_units':initial,'limit_including_inherited_attempts':limit})
   else:args.resume=str(out)
   s.update(ocr_status=mode+'_running',stage='Spectral missing OCR: '+mode);runtime.save(run,s);progress(run,s)
   def after(_run,st,window):
    s['ocr_windows']={k:v['status'] for k,v in st['units'].items()};runtime.save(run,s);progress(run,s);pause(run)
   result=cli.cmd_convert(args,source_records={SP:source},runtime=signature,run_path=out,after_window=after,max_unit_attempts=limit,worker_options=flags,initial_units=initial)
   if result==75:raise runtime.StopRun('OCR resource pause')
   if result==0:success=out;break
   summaries=[read_json(p) for p in out.rglob('summary.json')]
   if any(x.get('error_type') in ('MemoryError','ImportError','ModuleNotFoundError','PermissionError','OSError') or x.get('status')=='preflight_blocked' for x in summaries):raise runtime.Fatal('Shared OCR infrastructure fault; preserve diagnostics')
   previous=out
  if success:
   s['spectral_extraction']={'status':'completed','path':str(success)}
   try:
    prepared=run/'spectral-native'
    if not (prepared/'manifest.json').exists():chapter_inputs.prepare(prepared,source_specs=[{'source':SP,'run':str(success),'prefix':SP,'parts':[('full','Spectral',1,49)],'pages':49,'blanks':collection.verified_blanks(success)}],evidence_root=ROOT)
    verify_seal(prepared);folder=prepared/'chapters'/(SP+'-full');dest=run/'inputs'/SP;dest.mkdir(exist_ok=True)
    copy_file(folder/'source.json',dest/'native.json');copy_file(folder/'source.tex',dest/'source.tex');assets=[]
    for p in (prepared/'assets').glob('*'):
     if p.is_file():copy_file(p,run/'inputs/assets'/p.name);assets.append('assets/'+p.name)
    atomic_json(dest/'assets.json',assets)
    import fitz
    with fitz.open(s['documents'][SP]['original']) as pdf:pages=[{'physical_pdf_page':i+1,'text':p.get_text(sort=True)} for i,p in enumerate(pdf)]
    atomic_json(dest/'secondary.json',{'pages':pages});atomic_json(run/'quality'/(SP+'.json'),core.secondary_assessment(pages));n=read_json(dest/'native.json')
    def heading(prefix):
     hits=[b['id'] for b in n['blocks'] if any(re.match(prefix,h) for h in scope.headings(b['tex']))]
     if len(hits)!=1:raise ValueError('Spectral section resolver is ambiguous')
     return hits[0]
    sec=selected(n,heading(r'^6\.2\.[^\d]'),heading(r'^6\.4\.[^\d]'),'Spectral OU and Bessel sections');s['source_units']['spectral-section']['section']=sec;s['source_units']['spectral-section']['context']='\n\n'.join(b['tex'] for b in n['blocks'][:20])
    for p in [*dest.rglob('*'),*(run/'inputs/assets').glob('*'),run/'quality'/(SP+'.json')]:
     if p.is_file():s['derived_inputs'][str(p.relative_to(run))]=sha(p)
    atomic_json(run/'spectral-scope/unit.json',s['source_units']['spectral-section']);seal(run/'spectral-scope');s['spectral_scope_seal']=sha(run/'spectral-scope/manifest.json')
    s['ocr_status']='completed';s['spectral_preparation']={'status':'completed','unit':'spectral-section'}
   except (ValueError,KeyError) as exc:s.update(ocr_status='unrecovered',spectral_preparation={'status':'failed','error':str(exc)},ocr_error='Saved extraction preparation/section qualification: '+str(exc))
  else:s.update(ocr_status='unrecovered',ocr_error='Diagnostic did not qualify a successful bounded recovery; inspect exact saved traceback/warp records')
  if s['ocr_status']=='unrecovered':
   for t in s['tasks']:
    if t['source_key']==SP:t['status']='unavailable_source_preparation' if success else 'unavailable_ocr'
 finally:
  # Restore only the deployment this controller positively identified and stopped.
  for p in (run/'ocr').glob('*/state.json'):
   if any(u['status']=='running' for u in read_json(p)['units'].values()):raise runtime.Fatal('Uncertain OCR window: GLM restoration withheld until ownership reconciliation')
  if s.get('glm_owned_before_ocr'):
   if collection.helper_hashes(helpers)!=read_json(run/'binding.json')['helper_hashes']:raise runtime.Fatal('Helpers changed before owned GLM restoration')
   books.book.arrange_glm(run,check_only=False)
  s['resource_phase']='glm_only';runtime.save(run,s);progress(run,s)

def saved_compiles(run,s):
 if s.get('saved_compile_done'):return
 for key,row in s['source_units'].items():
  if row.get('saved_draft'):compile_version(run,s,key,'saved-baseline')
 text=(run/'baseline/cf-low.tex').read_text();v=read_json(run/'baseline/cf-identity.json');error=repair.first_error(Path(s['parent']),v);revised,edits=syntax.deterministic(text,error)
 if not edits or r'\tag{33}' not in revised:raise runtime.Fatal('CF tag repair did not preserve (33)')
 (run/'baseline/cf-tag-repaired.tex').write_text(revised);(run/'baseline/cf-tag.diff').write_text(''.join(difflib.unified_diff(text.splitlines(True),revised.splitlines(True),fromfile='saved-low',tofile='tag-repaired')));atomic_json(run/'baseline/cf-tag-repair.json',{'before':core.digest(text),'after':core.digest(revised),'edits':edits,'mathematical_acceptance':False})
 assets=books.asset_map(run,CF,revised);result=collection.compiler_environment.compile_saved(run,s,ROOT,revised,run/'baseline/cf-build',assets);atomic_json(run/'baseline/cf-build-result.json',result);s['saved_compile_done']=True;runtime.save(run,s)

def bundle(run,s):
 stamp=str(time.time_ns());out=run/'inspection'/stamp;out.mkdir(parents=True);progress(run,s)
 for name in ('plan.json','progress.json','state.json','baseline','accuracy','evidence','evaluation','quality'):
  p=run/name
  if p.is_dir():shutil.copytree(p,out/name)
  elif p.is_file():copy_file(p,out/name)
 for p in (run/'versions').rglob('document.tex'):copy_file(p,out/p.relative_to(run))
 for p in (run/'versions').rglob('console.log'):copy_file(p,out/p.relative_to(run))
 metrics=read_json(run/'progress.json')['calls'];atomic_json(out/'request-metrics.json',metrics)
 import csv,io
 rows=[]
 for key,versions in s['versions'].items():
  for label,v in versions.items():rows.append({'unit':key,'version':label,'sha256':v['sha256'],'selected':s['current_versions'].get(key)==label,'compilation':v.get('compilation',{}).get('status'),'source_verification':'designated checks only; see evaluation; remaining mathematics unverified'})
 stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=['unit','version','sha256','selected','compilation','source_verification']);writer.writeheader();writer.writerows(rows);(out/'results.csv').write_text(stream.getvalue())
 parent=read_json(Path(s['parent'])/'state.json');historical=[]
 for call in parent['calls']:
  task=next((t for t in parent['tasks'] if t['id']==call['parent']),None)
  if task and task['source_key'] in SOURCES:historical.append({'call':call['id'],'source':task['source_key'],'phase':task['phase'],'status':call['status'],'seconds':call.get('elapsed_seconds'),'usage':call.get('metadata',{}).get('usage')})
 atomic_json(out/'historical-comparison.json',{'parent':s['parent'],'calls':historical,'interpretation':'Prior requests have different scope/source settings; timings are descriptive, not a controlled speed/accuracy ranking.'})
 checks={'scope':'Automated checks on source-checked designated targets only; no blanket mathematical acceptance','checks':[]}
 for key in ('anfuso-appendix','information-control','breaking-figure'):
  label=s['current_versions'].get(key)
  if not label:continue
  text=(run/s['versions'][key][label]['path']).read_text();row={'unit':key,'version':label,'review':'independent review pending','new_harmful_edits':'not automatically ruled out'}
  if key=='breaking-figure':row['original_figure_asset_preserved']='assets/breaking-barriers-original-figure-4.png' in scope.image_references(text)
  elif key=='information-control':row['changed_from_saved_baseline']=text!=(run/s['versions'][key]['saved-baseline']['path']).read_text()
  else:
   equations=[m.group() for m in re.finditer(r'\\begin\{(?:equation\*?|align\*?)\}.*?\\end\{(?:equation\*?|align\*?)\}',text,re.S) if re.search(r'\\tag\{13\}',m.group())]
   normal=''.join(equations).replace(' ','').replace('\n','');row['source_numerator_match']=bool(re.search(r'\\alpha\+\\rho[xX]',normal));row['known_conflicting_numerator_present']=bool(re.search(r'\\rho\\alpha\+[xX]',normal));row['interpretation']='Limited check against visually inspected original equation13; independence/noise-variable reasoning and all other edits still require mathematical review'
  checks['checks'].append(row)
 atomic_json(out/'designated-evaluation.json',checks)
 for name in ('outcome.json','request.json','answer.txt','response-metadata.json'):
  for p in (run/'calls').glob('*/'+name):copy_file(p,out/p.relative_to(run))
 for name in ('syntax-tasks','syntax-repairs'):
  if (run/name).exists():shutil.copytree(run/name,out/name)
 for p in (run/'ocr').rglob('early-width-guard.jsonl'):copy_file(p,out/p.relative_to(run))
 for p in (run/'ocr').rglob('warp-input-*.npz'):copy_file(p,out/p.relative_to(run))
 for p in (run/'ocr').rglob('warp-diagnostics.jsonl'):copy_file(p,out/p.relative_to(run))
 for p in (run/'ocr').rglob('traceback.txt'):copy_file(p,out/p.relative_to(run))
 unresolved=[{'task':t['id'],'status':t['status'],'scope':s['source_units'][t['key']]['section'],'suggested_escalation':'Use only this located passage plus original source page/crop and exact draft. Ask for transcription or located discrepancy edits, not a whole-paper rewrite. Paid dispatch NOT authorized.'} for t in s['tasks'] if t['status'] not in ('conversion_completed','critic_revised','critic_unchanged','not_needed','deterministic_repaired','syntax_repaired')]
 for task in s['tasks']:
  findings=[x for x in task.get('findings',{}).get('findings',[]) if x.get('disposition') in ('unresolved','unapplied_suggestion','rejected')]
  if findings:unresolved.append({'task':task['id'],'status':'review_returned_with_unresolved_or_unapplied_findings','findings':findings,'scope':s['source_units'][task['key']]['section'],'proposed_task':'Inspect these exact located findings against original source crops and draft. No full-paper upload or paid dispatch is authorised.'})
 atomic_json(out/'offline-escalations.json',unresolved)
 (out/'START-HERE.txt').write_text('Finite local focused recovery trial. See plan.json for exact targets and derived maximum; progress.json and request-metrics.json for actual outcomes/cost. Parent attempts and successful outputs are preserved. Source-image checks/expected findings are held out of model inputs in evaluation/. Model findings are attributed claims, never mathematical verification. Rejected edits remain unapplied. Compilations and coverage flags are separate. OCR qualifications may leave Spectral unavailable without blocking independent documents. No cloud calls/credentials or production continuation. The finished trial makes zero requests on resume. Full raw requests/responses/reasoning stay in the run. Offline escalation proposals are not authorization to dispatch.\n')
 atomic_json(out/'manifest.json',files_manifest(out));path=ROOT/'results/inspection'/('focused-recovery-'+run.name+'-'+stamp+'.zip')
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for p in out.rglob('*'):
   if p.is_file():z.write(p,str(p.relative_to(out)))
 with zipfile.ZipFile(path) as z:assert z.testzip() is None
 s['inspection']={'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size};runtime.save(run,s);return path

def worker(run):
 with (run/'terminal.log').open('a',buffering=1) as log:
  os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
  with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):
   s=verify(run)
   if s['status']==TERMINAL:return
   try:
    s.update(status='running',diagnostic=None);s['launches'].append({'at':runtime.now(),'pid':os.getpid()});runtime.save(run,s);progress(run,s)
    runtime.check_other_jobs();books.qualify_compiler(run,s)
    result=collection.tex_compile.compile_document(r'\documentclass{article}\usepackage{amsmath,graphicx}\begin{document}$x^2$\end{document}',run/'compiler-preflight'/str(time.time_ns()),image=s['compiler_environment']['image'],passes=2)
    if not result['compilation_claim']:raise runtime.Fatal('Isolated compiler preflight failed')
    saved_compiles(run,s);helpers=books.speed.module();ocr_phase(run,s,helpers);pause(run)
    books.book.arrange_glm(run,check_only=True);concurrent.capture_build(helpers,run);efforts=books.speed.effort_check(run,helpers)
    if efforts.get('status')=='probe_error' or not efforts.get('low_supported'):raise runtime.Fatal('Requested installed effort mappings unverified')
    s['low_supported']=True;s['stage']='finite model tasks';runtime.save(run,s)
    base_sample=books.speed.sampler(run,s,helpers)
    def sample(owned):
     observation=base_sample(owned);progress(run,s);return observation
    books.speed.healthy(sample(0))
    if not s['readiness_done']:
     if any(c['parent']=='readiness' for c in s['calls']):raise runtime.Fatal('Consumed/uncertain readiness; reconcile before resume')
     runtime.readiness(run,s);s['readiness_done']=True;runtime.save(run,s)
    # Settle a completed response once; an uncertain reservation is never replayed.
    for t in s['tasks']:
     reserved=[c for c in s['calls'] if c['parent']==t['id']]
     if reserved and not t.get('settled_call'):
      c=reserved[0];p=run/'calls'/c['id']
      if not (p/'manifest.json').exists():raise runtime.Fatal('Uncertain dispatch '+c['id'])
      verify_seal(p);record=read_json(p/'outcome.json');c.update(record);c['seal']=sha(p/'manifest.json');answer=(p/'content.txt').read_text() if c['status']=='completed_response' else None;finish(run,s,t,answer,c)
    adjust(run,s);active=[]
    def changed():
     adjust(run,s);active[:]=[t for t in s['tasks'] if t['status'] not in ('dormant','not_needed')]
    changed()
    concurrent.coordinate(run,s,active,body_for=body_for,finish=finish,verify=lambda:verify(run),sample=sample,changed=changed,before_reserve=lambda st,t,b:before(run,st,t,b),fixed_level=2)
    if any(t['status'] in ('pending','running','dormant') for t in s['tasks']):raise runtime.Fatal('Frozen tasks remain undispatched')
    s.update(status=TERMINAL,finished_at=runtime.now(),stage='finished; no next experiment')
   except runtime.StopRun as exc:s.update(status='stopped_error' if isinstance(exc,runtime.Fatal) else 'paused',diagnostic=str(exc))
   except BaseException as exc:s.update(status='stopped_error',diagnostic=type(exc).__name__+': '+str(exc),diagnostic_file=concurrent.exception_trace(run,exc,'Focused trial'))
   finally:runtime.save(run,s);progress(run,s);bundle(run,s)

def launch(run):
 s=verify(run)
 if s['status']==TERMINAL:print('Finished trial; zero requests, OCR or readiness.');return
 if not all(books.speed.idle(p) for p in (ROOT,ROOT/'runs',run)):raise runtime.Fatal('Writer active; no duplicate worker')
 for c in s['calls']:
  if c['status']=='in_progress' and not (run/'calls'/c['id']/'manifest.json').exists():raise runtime.Fatal('Uncertain dispatch; reconcile first')
 for p in (run/'ocr').glob('*/state.json'):
  if any(u['status']=='running' for u in read_json(p)['units'].values()):raise runtime.Fatal('Uncertain OCR attempt; no automatic replay')
 cp=subprocess.run(['tmux','has-session','-t',SESSION],capture_output=True,text=True)
 if cp.returncode==0:raise runtime.Fatal('Persistent trial already exists')
 if cp.returncode!=1 or 'permitted' in cp.stderr or 'denied' in cp.stderr:raise runtime.Fatal('tmux inaccessible: '+cp.stderr)
 collection.normal_checks(run)
 (run/'pause.json').unlink(missing_ok=True)
 command=shlex.join([str(PYTHON),'-B','-u',str(Path(__file__).resolve()),'worker','--run',str(run)])
 subprocess.run(['tmux','new-session','-d','-s',SESSION,'cd '+shlex.quote(str(ROOT))+' && exec '+command],check=True);print('Persistent launch requested:',run)

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run','resume','worker','status','pause','bundle'));p.add_argument('--run',type=Path);a=p.parse_args()
 if a.action=='prepare':prepare();return
 if a.action=='run' and not POINTER.exists():prepare()
 run=(a.run or Path(read_json(POINTER)['run'])).resolve()
 if a.action in ('run','resume'):launch(run)
 elif a.action=='worker':worker(run)
 elif a.action=='pause':atomic_json(run/'pause.json',{'at':runtime.now(),'policy':'Drain owned model/OCR work; no cancellation'});print('Pause requested')
 elif a.action=='status':print(json.dumps(read_json(run/'progress.json'),indent=2))
 elif a.action=='bundle':
  if not books.speed.idle(run):raise runtime.Fatal('Worker owns state; automatic progress remains available')
  with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):print(bundle(run,verify(run)))
if __name__=='__main__':main()
