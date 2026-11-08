#!/usr/bin/env python3
"""Prepare/inspect offline; paid execution requires an explicit frozen-plan launch."""
import argparse,base64,copy,csv,difflib,html,io,json,os,re,shlex,shutil,subprocess,sys,time,uuid,zipfile
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe import kimi_escalation as kimi,cloud_critic as cloud,focused_recovery as focused
from probe import book_completion as scope,chapter_accuracy,chapter_sources,compiler_environment
from probe.common import atomic_json,read_json,sha,fingerprint,files_manifest,writer_lock
from probe.experiment import seal,verify_seal,InputGuard
from probe.saved_pages import render_region
from scripts import originals_batch as local
SESSION='pdf-kimi-pilot';TERMINAL={'finished','finished_with_failures'};PYTHON=ROOT/'.venv-control/bin/python'
CODE=('probe/kimi_escalation.py','probe/cloud_critic.py','probe/focused_recovery.py','scripts/kimi_escalation.py','scripts/run-kimi-escalation.sh')


def code_hashes():
 names=set(CODE)|{str(p.relative_to(ROOT)) for d in ('probe','scripts') for p in (ROOT/d).glob('*.py')}
 return {name:sha(ROOT/name) for name in sorted(names)}
def copied(source,target):
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 if sha(source)!=sha(target):raise cloud.IntegrityError('Copy mismatch')

def current_signature(parent,key):
 state=read_json(Path(parent)/'state.json');return fingerprint({'selected':state['current_versions'].get(key),'tasks':[{k:t.get(k) for k in ('id','status','settled_call','final_version')} for t in state['tasks'] if t['key']==key]})

def anchor(native,pattern):
 matches=[b['id'] for b in native['blocks'] if re.search(pattern,b['tex'])]
 if len(matches)!=1:raise ValueError('Passage boundary not unique: '+pattern)
 return matches[0]
def selected(native,first,last):
 blocks=[b for b in native['blocks'] if b['kind'] not in scope.FURNITURE];ids=[b['id'] for b in blocks];return scope.target(native,ids[ids.index(first):ids.index(last)],title='Selected bounded passage')
def draft_range(text,start,end):
 a=re.search(start,text,re.I);b=re.search(end,text[a.end():],re.I) if a else None
 if not a or not b:raise ValueError('Draft passage boundary unavailable; refresh selection')
 return [[a.start(),a.end()+b.start()]]


def provisional_spec(parent):
 """Purposeful, explicitly selected sample; never automatically escalates all failures."""
 return {'enabled':True,'provisional':True,'tasks':[
 {'id':'information-control-review','source_id':'original-dcbf009549ec6318','key':'information-control','operation':'review','control':True,'reason':'successful_control','primary_start':r'\\subsection\*\{2 Information','primary_end':r'\\subsection\*\{3 Risks','draft_start':r'\\section\*?\{2 Information','draft_end':r'\\section\*?\{3 Risks','context_blocks':5},
 {'id':'cf-case17-convert','source_id':'original-21debf82bc2c0a3d','key':'cf-cases-16-18','operation':'convert','control':False,'reason':'source_image_ambiguity','primary_start':r'^Case 17\.','primary_end':r'^Case 18\.','context_blocks':8},
 {'id':'cf-case17-review','source_id':'original-21debf82bc2c0a3d','key':'cf-cases-16-18','operation':'review','control':False,'reason':'converter_critic_disagreement','primary_start':r'^Case 17\.','primary_end':r'^Case 18\.','draft_start':r'\\subsection\*\{Case 17\.','draft_end':r'\\subsection\*\{Case 18\.','context_blocks':8}]}


def own_draft_spec():
 common={'source_id':'original-21debf82bc2c0a3d','key':'cf-cases-16-18','control':False,'reason':'source_image_ambiguity','primary_start':r'^Case 13\.','primary_end':r'^Case 19\.','context_blocks':8,'own_draft_chain':True}
 return {'enabled':True,'experiment':'own-draft-chain-v1','tasks':[
  {**common,'id':'cf-cases13-18-convert','operation':'convert'},
  {**common,'id':'cf-cases13-18-critic','operation':'review','draft_from':'cf-cases13-18-convert'}]}


def case_mapping(native,primary):
 blocks=[b for b in native['blocks'] if b['id'] in set(primary['blocks'])];groups=[]
 for b in blocks:
  m=re.match(r'Case (\d+)\.',b['tex'])
  if m:groups.append({'case':int(m[1]),'blocks':[],'pages':[]})
  if not groups:raise cloud.IntegrityError('Case scope starts inside a case')
  groups[-1]['blocks'].append(b['id']);groups[-1]['pages'].append(b['page']['original_physical_page'])
 numbers={13:['25a','25b','26'],14:['27a','27b','28'],15:['29','30'],16:['31','32'],17:['33','34'],18:['35','36']}
 if [g['case'] for g in groups]!=list(numbers):raise cloud.IntegrityError('Unexpected case boundaries')
 for g in groups:g.update(pages=sorted(set(g['pages'])),equations=numbers[g['case']],assigned='Complete density, characteristic function, restrictions, negative-x branches where present and explanatory text',mapping_evidence='Original physical PDF pages 4–6 visually inspected; numbering only, no expected mathematical answer.')
 return groups


def prepare(parent,project_root,metadata_folder,budget,out=None,selection=None,qualified_run=None):
 parent=Path(parent).resolve();project_root=Path(project_root).resolve();state=read_json(parent/'state.json');metadata=read_json(Path(metadata_folder)/'metadata.json');kimi.validate_metadata(metadata,images=True)
 if selection and qualified_run:raise cloud.AdmissionError('Use the fixed two-request chain or explicit selection, not both')
 spec=own_draft_spec() if qualified_run else read_json(selection) if selection else provisional_spec(parent)
 if spec.get('enabled') is not True or not spec.get('tasks'):raise cloud.AdmissionError('Explicit enabled passage selection required')
 ids=[t['id'] for t in spec['tasks']]
 if len(ids)!=len(set(ids)) or any(not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}',x) for x in ids):raise cloud.IntegrityError('Duplicate or unsafe task identity')
 if not qualified_run and not spec['tasks'][0].get('control'):raise cloud.AdmissionError('First task must be an explicitly selected successful control')
 spec['selected_tasks']=ids;config=kimi.profile(metadata,budget,len(spec['tasks']))
 qualification=kimi.reused_qualification(qualified_run,config,metadata) if qualified_run else None
 if qualification:
  config['readiness']='Reuse the settled live image-bearing protocol qualification. Current public metadata, compiler availability and authenticated remaining allowance checks only; zero extra inference.'
  config['qualification']=qualification['qualification']
 if cloud.decimal(config['pilot_budget_usd'])>Decimal(kimi.KEY_CEILING):raise cloud.AdmissionError('Pilot cap exceeds historical key ceiling')
 out=Path(out) if out else ROOT/'runs'/('kimi-plan-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:6]);out.mkdir(parents=True,exist_ok=False)
 history=kimi.history_snapshot(project_root);atomic_json(out/'prior-billing.json',history);atomic_json(out/'public-metadata.json',metadata);tasks=[];frozen={};sources=[]
 if qualification:atomic_json(out/'qualification-reuse.json',qualification);frozen.update(qualification['frozen'])
 for task in spec['tasks']:
  if not kimi.opt_in(spec,task):raise cloud.AdmissionError('Cloud stage disabled or task not selected')
  sid=task['source_id'];doc=state['documents'][sid];pdf=Path(doc['original']);pdf=pdf if pdf.is_absolute() else parent/pdf
  if sha(pdf)!=doc['source_sha256']:raise cloud.IntegrityError('Source PDF identity mismatch')
  related=[t for t in state['tasks'] if t['key']==task['key']]
  if not related or any(t['status'] in ('pending','running','dormant') for t in related):raise cloud.AdmissionError('Pilot source unit is absent or not settled; select settled evidence only')
  native_path=parent/'inputs'/sid/'native.json';native=read_json(native_path)
  if native.get('source')!=sid:raise cloud.IntegrityError('Native source mapping differs')
  primary=selected(native,anchor(native,task['primary_start']),anchor(native,task['primary_end']));blocks=[b for b in native['blocks'] if b['id'] in set(primary['blocks'])]
  if len(primary['physical_pages'])>4:raise cloud.AdmissionError('Passage exceeds the four-page pilot scope; no clipping')
  context='';context_ids=[];context_pages=[]
  if task.get('context_start'):
   context_scope=selected(native,anchor(native,task['context_start']),anchor(native,task['context_end']))
   context=context_scope['text'];context_ids=context_scope['blocks'];context_pages=context_scope['physical_pages']
  elif task['context_blocks']:
   context_native=[b for b in native['blocks'][:task['context_blocks']] if b['kind'] not in scope.FURNITURE and b['id'] not in primary['blocks']]
   context='\n\n'.join(b['tex'] for b in context_native);context_ids=[b['id'] for b in context_native]
   context_pages=sorted({b['page']['original_physical_page'] for b in context_native})
  if len(context.encode())>40000:raise cloud.AdmissionError('Necessary definitions too broad for this pilot; rescope explicitly')
  secondary_path=parent/'inputs'/sid/'secondary.json';secondary_pages=[p for p in read_json(secondary_path)['pages'] if p['physical_pdf_page'] in primary['physical_pages']];secondary=chapter_sources.render_pages(secondary_pages)
  task=copy.deepcopy(task);task.update(source_sha256=doc['source_sha256'],filename=doc.get('filename','Unknown source'),pages=primary['physical_pages'],context_pages=context_pages,context_block_ids=context_ids,blocks=primary['blocks'],source_run=str(parent),source_unit_signature=current_signature(parent,task['key']),source_snapshot_status=[{k:t.get(k) for k in ('id','status','call')} for t in related])
  folder=out/'tasks'/task['id'];folder.mkdir(parents=True);assets=[]
  if qualified_run:
   assessment=focused.secondary_assessment(secondary_pages)
   assessment.update(manual_disposition='All secondary text on physical pages 4–6 quarantined outside model inputs after original-image comparison.',reason='Severely corrupted symbol mappings and disrupted mathematical reading order; ASCII lookalikes evade invalid-glyph detection. Automatic suppression count is not a quality pass.',supplied_secondary_lines=0)
   atomic_json(folder/'secondary-assessment.json',assessment);atomic_json(folder/'secondary-original.json',secondary_pages)
   secondary='Native PDF text for this output scope is withheld because image comparison established corrupted mathematical symbol mappings and reading order. Use the saved MinerU material and supplied source images; record remaining ambiguity rather than assuming either extraction is correct.'
   task['case_map']=case_mapping(native,primary)
   atomic_json(folder/'scope.json',{'cases':task['case_map'],'scope':primary,'context_block_ids':context_ids,'context_pages':context_pages,'secondary_policy':'quarantined, not sent'})
  image_pages=sorted(set(task['pages']+task['context_pages'])) if qualified_run else task['pages']
  for page in image_pages:
   image_blocks=blocks if page in task['pages'] else [b for b in native['blocks'] if b['id'] in set(context_ids)]
   boxes=[b['bbox'] for b in image_blocks if b['page']['original_physical_page']==page and b.get('bbox')]
   bbox=[max(0,min(b[0] for b in boxes)-.015),max(0,min(b[1] for b in boxes)-.015),min(1,max(b[2] for b in boxes)+.015),min(1,max(b[3] for b in boxes)+.015)] if boxes else None
   image=folder/('source-p'+str(page)+'.png');rendered=render_region(pdf,page-1,image,bbox=bbox,max_edge=1800 if qualified_run else 1400)
   assets.append({'path':str(image),'sha256':sha(image),'page':page,'bbox':bbox,'source_id':sid,'source_sha256':doc['source_sha256'],'render':rendered})
  draft=None;ranges=None
  if task.get('draft_from'):
   draft=kimi.CHAIN_DRAFT_SLOT;ranges=[[0,len(draft)]]
   task['request_is_template']=True;task['draft_contract']={'from_task':task['draft_from'],'content':'exact newly extracted candidate.tex, with full SHA256; no reasoning or accuracy log','maximum_draft_bytes':50000,'gate':'Complete document, successful finish and all assigned case/equation presence checks; never a retry'}
  elif task['operation']=='review':
   label=state['current_versions'][task['key']];version=state['versions'][task['key']][label];path=parent/version['path'];assert sha(path)==version['sha256'];draft=path.read_text();ranges=draft_range(draft,task['draft_start'],task['draft_end'])
   task.update(draft_path=str(path),draft_sha256=version['sha256'],draft_label=label,editable_ranges=ranges);(folder/'draft-passage.tex').write_text('\n\n'.join(draft[a:b] for a,b in ranges));frozen[str(path)]=sha(path)
  task['images']=assets;body=kimi.build_body(config,task,primary['text'],secondary,context,draft,ranges,assets)
  request_name='request-template.json' if task.get('draft_from') else 'request.json'
  atomic_json(folder/request_name,body);(folder/'source-passage.tex').write_text(primary['text']);(folder/'secondary.txt').write_text(secondary);(folder/'context.tex').write_text(context)
  estimate=kimi.planning_cost(config,body)
  if task.get('draft_from'):
   draft_allowance=32768;estimate['assumed_prompt_tokens']+=draft_allowance
   estimate['usd_at_full_output_allowance']=str(cloud.decimal(estimate['usd_at_full_output_allowance'])+draft_allowance*cloud.decimal(config['rates']['prompt']))
   estimate['caveat']+=' Critic estimate additionally budgets 32768 input tokens for the not-yet-generated draft.'
  task.update(request=str((folder/request_name).relative_to(out)),request_sha256=fingerprint(body),reservation_usd=str(kimi.cost_bound(config,body)),planning_estimate=estimate);atomic_json(folder/'task.json',task);tasks.append(task)
  for p in (pdf,native_path,secondary_path):frozen[str(p)]=sha(p)
  sources.append({'source_id':sid,'sha256':doc['source_sha256'],'original_path':str(pdf),'native_path':str(native_path)})
  # The preview shows every textual part and exact image, without expected answers or full draft bodies.
  label='Frozen critic recipe: the draft slot and its hash will be replaced by the exact new conversion only. The actual request is saved before dispatch.' if task.get('draft_from') else 'Exact proposed outbound request. No inference has been sent.'
  parts=['<!doctype html><meta charset="utf-8"><title>Outbound preview</title><style>body{font:15px system-ui;margin:2em}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f5f5;padding:1em}img{max-width:100%}</style>',f'<h1>{html.escape(task["filename"])} — {task["operation"]}</h1><p>{label} <a href="{request_name}">Request JSON</a></p>']
  image_index=0
  for p in body['messages'][0]['content']:
   if p['type']=='text':parts.append('<pre>'+html.escape(p['text'])+'</pre>')
   else:parts.append('<img src="'+Path(assets[image_index]['path']).name+'">');image_index+=1
  (folder/'preview.html').write_text('\n'.join(parts))
 total=sum((cloud.decimal(t['reservation_usd']) for t in tasks),Decimal(0))
 if total>cloud.decimal(config['pilot_budget_usd']):raise cloud.AdmissionError('Conservative plan reservation exceeds explicit pilot cap')
 if total+cloud.decimal(history['summary']['actual_reported_usd'])+cloud.decimal(history['summary']['unresolved_reserved_usd'])>Decimal(kimi.KEY_CEILING):raise cloud.AdmissionError('Recorded historical exposure leaves insufficient global headroom')
 plan={'created_epoch':time.time(),'config':config,'tasks':tasks,'source_parent':str(parent),'project_root':str(project_root),'provisional':True,'refresh_policy':'At launch recheck each selected unit signature and source/draft/image hashes. If newer local results changed it, prepare a fresh selection before paid dispatch.','historical_accounting':history['summary'],'authenticated_remaining_usd':None,'maximum_requests':len(tasks),'readiness_requests':0,'authorised_recovery_requests':0,'conservative_maximum_usd':str(total),'pilot_cap_usd':config['pilot_budget_usd'],'sources':sources,'acceptance':'All cloud results remain unaccepted, not mathematically verified.','compiler_environment':copy.deepcopy(state['compiler_environment'])}
 if qualification:
  plan.update(experiment='own-draft-chain-v1',qualification_reuse=qualification,provisional=False)
  # Saved GLM material is comparison evidence only, never a model input.
  overlap=state['versions']['cf-cases-16-18'];comparison=[]
  for label,version in overlap.items():
   path=parent/version['path']
   if sha(path)!=version['sha256']:raise cloud.IntegrityError('Saved GLM comparison identity changed')
   target=out/'comparison'/label/'document.tex';copied(path,target)
   origin=version.get('origin',{});call=origin.get('call');call_record=next((c for c in state['calls'] if c['id']==call),{})
   comparison.append({'version':label,'sha256':version['sha256'],'origin':origin,'compilation':version.get('compilation',{}).get('status'),'recorded_call':call_record,'scope':'GLM Cases16–18 versus Kimi Cases13–18: only partial overlap; no equal-workload speedup claim.'})
  atomic_json(out/'comparison/manifest.json',comparison)
 atomic_json(out/'plan.json',plan)
 for p in out.rglob('*'):
  if p.is_file():frozen[str(p)]=sha(p)
 binding={'code':code_hashes(),'config':config,'frozen':frozen,'prior_billing':{'path':str(out/'prior-billing.json'),'sha256':sha(out/'prior-billing.json')},'project_root':str(project_root),'plan_sha256':sha(out/'plan.json')};atomic_json(out/'binding.json',binding);seal(out)
 print('PREPARED, NO INFERENCE:',out,'maximum USD',total,'pilot cap',config['pilot_budget_usd'],'historical recorded',history['summary']['actual_reported_usd'],'live remaining UNKNOWN');return out


def verify_plan(plan):
 plan=Path(plan);verify_seal(plan);binding=read_json(plan/'binding.json');InputGuard(binding['frozen']).check()
 if binding['code']!=code_hashes():raise cloud.IntegrityError('Prepared code changed; reconcile rather than reseal')
 data=read_json(plan/'plan.json')
 if fingerprint(data['config'])!=fingerprint(binding['config']):raise cloud.IntegrityError('Pilot configuration changed')
 for task in data['tasks']:
  body=read_json(plan/task['request']);kimi.validate_body(data['config'],body)
  if fingerprint(body)!=task['request_sha256']:raise cloud.IntegrityError('Exact preview request changed')
  actual=[hashlib_sha(base64.b64decode(p['image_url']['url'].split(',',1)[1])) for m in body['messages'] for p in m['content'] if p['type']=='image_url']
  if actual!=[a['sha256'] for a in task['images']]:raise cloud.IntegrityError('Outbound image identity mismatch')
  if task.get('draft_from'):
   folder=plan/'tasks'/task['id']
   rebuilt=kimi.build_body(data['config'],task,(folder/'source-passage.tex').read_text(),(folder/'secondary.txt').read_text(),(folder/'context.tex').read_text(),kimi.CHAIN_DRAFT_SLOT,[[0,len(kimi.CHAIN_DRAFT_SLOT)]],task['images'])
   if rebuilt!=body:raise cloud.IntegrityError('Critic template differs from sealed source-only recipe')
 return data,binding

def hashlib_sha(data):return __import__('hashlib').sha256(data).hexdigest()
def selected_fresh(data):
 for t in data['tasks']:
  if current_signature(t['source_run'],t['key'])!=t['source_unit_signature']:raise cloud.IntegrityError('Newer local results require refreshed pilot selection: '+t['id'])

def existing_run(plan):
 p=Path(plan)/'launched-run.json'
 # The sealed plan directory must never be mutated; launches are indexed separately.
 index=ROOT/'results/kimi-plan-runs.json';values=read_json(index) if index.exists() else {};return Path(values[str(Path(plan).resolve())]) if str(Path(plan).resolve()) in values else None

def initialise(plan,accepted_budget):
 data,binding=verify_plan(plan)
 if cloud.budget_amount(accepted_budget)!=data['pilot_cap_usd']:raise cloud.AdmissionError('Explicit accepted budget differs from reviewed pilot cap')
 selected_fresh(data)
 run=ROOT/'runs'/('kimi-trial-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:6]);run.mkdir(parents=True)
 runtime_binding={**binding,'plan_path':str(Path(plan).resolve()),'plan_manifest_sha256':sha(Path(plan)/'manifest.json')};atomic_json(run/'binding.json',runtime_binding)
 atomic_json(run/'authorisation.json',{'binding_sha256':sha(run/'binding.json'),'accepted_pilot_budget_usd':accepted_budget,'at_epoch':time.time(),'scope':'This exact frozen plan only; '+('reuse prior qualification, two dependent work requests' if data.get('qualification_reuse') else 'first task is paid qualification')+'; no extra readiness/retries.'})
 kimi.ledger(run,create=True);state={'status':'prepared_for_explicit_paid_launch','tasks':{t['id']:{'status':'pending'} for t in data['tasks']},'calls':[],'live_qualified':data.get('qualification_reuse',False)};atomic_json(run/'state.json',state)
 index=ROOT/'results/kimi-plan-runs.json';entries=read_json(index) if index.exists() else {};entries[str(Path(plan).resolve())]=str(run);atomic_json(index,entries);atomic_json(ROOT/'results/kimi-current.json',{'run':str(run),'plan':str(plan)});return run


def verify_run(run):
 binding=read_json(run/'binding.json');plan=Path(binding['plan_path']);data,old=verify_plan(plan)
 if sha(plan/'manifest.json')!=binding['plan_manifest_sha256'] or any(binding[k]!=old[k] for k in old):raise cloud.IntegrityError('Paid run/plan binding differs')
 return data,kimi.ledger(run),read_json(run/'state.json')

def progress(run,state):
 summary=kimi.ledger(run).summary();atomic_json(run/'progress.json',{'at_epoch':time.time(),'run':str(run),'status':state['status'],'tasks':state['tasks'],'live_qualified':state['live_qualified'],'billing':summary,'diagnostic':state.get('diagnostic'),'log':str(run/'terminal.log')})


def materialize_task(run,data,task):
 """Freeze a fresh critic request from the exact usable new TeX, never its reasoning."""
 plan=Path(read_json(run/'binding.json')['plan_path'])
 if not task.get('draft_from'):return task,read_json(plan/task['request'])
 parent=run/'calls'/task['draft_from'];result=read_json(parent/'result.json');draft_path=parent/'candidate.tex'
 if result.get('status')!='candidate_saved' or result.get('usable_for_critic') is not True:raise cloud.AdmissionError('New conversion is not usable; critic must not dispatch')
 if sha(draft_path)!=result['sha256']:raise cloud.IntegrityError('New converter draft changed')
 draft=draft_path.read_text();actual={**task,'draft_path':str(draft_path),'draft_sha256':result['sha256'],'editable_ranges':[[0,len(draft)]],'draft_label':task['draft_from']}
 folder=plan/'tasks'/task['id']
 body=kimi.build_body(data['config'],actual,(folder/'source-passage.tex').read_text(),(folder/'secondary.txt').read_text(),(folder/'context.tex').read_text(),draft,actual['editable_ranges'],task['images'])
 if kimi.cost_bound(data['config'],body)>cloud.decimal(task['reservation_usd']):raise cloud.AdmissionError('Derived critic exceeds sealed reservation')
 actual['actual_request_sha256']=fingerprint(body)
 dest=run/'calls'/task['id'];dest.mkdir(parents=True,exist_ok=True)
 for name,value in [('resolved-task.json',actual),('derived-request.json',body)]:
  p=dest/name
  if p.exists() and read_json(p)!=value:raise cloud.IntegrityError('Previously materialized critic identity changed')
  if not p.exists():atomic_json(p,value)
 return actual,body

def process_answer(run,task,answer,record,data):
 folder=run/'calls'/task['id'];result={'transport':record['status'],'acceptance':'unaccepted','mathematical_verification':False}
 if record['status']!='complete_response':return dict(result,status='incomplete_answer')
 if task['operation']=='review':
  base=Path(task['draft_path']);draft=base.read_text()
  if sha(base)!=task['draft_sha256']:raise cloud.IntegrityError('Draft changed before application')
  try:revised,notes=focused.apply_focused(draft,answer,task['editable_ranges'])
  except (ValueError,TypeError,KeyError) as e:return dict(result,status='rejected_edits',error=str(e))
  for note in notes['findings']:note['attribution']='Kimi K3 claim; independent source review pending'
  notes['acceptance']='Changes apply only to this unaccepted derivative, never the local selected edition.';atomic_json(folder/'accuracy.json',notes)
  (folder/'change.diff').write_text(''.join(difflib.unified_diff(draft.splitlines(True),revised.splitlines(True),fromfile='local-baseline',tofile='unaccepted-kimi-derivative')))
 else:
  revised,info=chapter_accuracy.envelope(answer,local.books.book.simple.extract_document)
  if revised is None or not chapter_accuracy.complete_document(revised):return dict(result,status='no_complete_document')
  atomic_json(folder/'accuracy.json',{'raw_answer_path':'answer.txt','envelope':info,'acceptance':'unaccepted; annotations/model corrections require source review'})
  notes,note_status=chapter_accuracy.outside_notes(answer,info)
  (folder/'accuracy-notes.txt').write_text(notes)
 (folder/'candidate.tex').write_text(revised);result.update(status='candidate_saved',sha256=sha(folder/'candidate.tex'),path=str(folder/'candidate.tex'))
 if task.get('case_map'):
  coverage=kimi.chain_coverage(revised,task['case_map']);atomic_json(folder/'coverage.json',coverage)
  result.update(coverage=coverage,usable_for_critic=coverage['usable_for_critic'])
 # Reuse the existing isolated compiler policy and the source's allowed assets.
 parent=Path(task['source_run']);env=copy.deepcopy(data['compiler_environment'])
 if not (run/env['path']).exists():shutil.copytree(parent/env['path'],run/env['path'])
 compile_state={'compiler_environment':env}
 try:
  assets=local.books.asset_map(parent,task['source_id'],revised)
  # Use the qualified image only. This pilot does not authorise provisioning.
  def no_provision(*args,**kwargs):raise ValueError('Missing compiler dependency: deferred, no environment changes in Kimi pilot')
  result['compilation']=compiler_environment.compile_saved(run,compile_state,ROOT,revised,folder/'build',assets,provision=no_provision)
 except (ValueError,OSError) as exc:result['compilation']={'status':'unresolved_compile_or_asset','error':str(exc),'compilation_claim':False}
 return result


def bundle(run):
 data,ledger,state=verify_run(run);dest=ROOT/'results/inspection'/('kimi-'+run.name+'-'+str(time.time_ns())+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
  for name in ('state.json','progress.json','binding.json','billing.json'):z.write(run/name,name)
  z.writestr('START-HERE.txt','Explicit Kimi passage pilot. Results are separate unaccepted derivatives, not mathematical verification. See state/progress/billing, original exact preview, source page/hash mappings and accuracy/diffs. No full chat/key is included. Failed/uncertain charges remain reserved; no automatic retries.\n')
  for task in data['tasks']:
   for name in ('request.json','response.raw','answer.txt','reasoning.txt','reasoning-details.json','outcome.json','error.json','accuracy.json','accuracy-notes.txt','coverage.json','change.diff','result.json','resolved-task.json','derived-request.json'):
    p=run/'calls'/task['id']/name
    if p.exists():z.write(p,str(p.relative_to(run)))
   plan=Path(read_json(run/'binding.json')['plan_path']);folder=plan/'tasks'/task['id']
   for p in folder.iterdir():
    if p.is_file():z.write(p,'preview/'+str(p.relative_to(plan)))
   candidate=run/'calls'/task['id']/'candidate.tex'
   if candidate.exists():z.write(candidate,str(candidate.relative_to(run)))
   for p in (run/'calls'/task['id']/'build').rglob('*'):
    if p.is_file() and (p.suffix=='.pdf' or p.name in ('compilation.json','outcome.json','console.log')):z.write(p,str(p.relative_to(run)))
  for name in ('plan.json','public-metadata.json','prior-billing.json'):z.write(plan/name,'preview/'+name)
  if (plan/'comparison').exists():
   for p in (plan/'comparison').rglob('*'):
    if p.is_file():z.write(p,'preview/'+str(p.relative_to(plan)))
  metrics=[]
  for task in data['tasks']:
   folder=run/'calls'/task['id'];o=read_json(folder/'outcome.json') if (folder/'outcome.json').exists() else {};usage=o.get('usage') or {};reason=(usage.get('completion_tokens_details') or {}).get('reasoning_tokens');total=usage.get('completion_tokens')
   charge=next((x for x in ledger.read()['reservations'] if x['folder']=='calls/'+task['id']),{})
   metrics.append({'task':task['id'],'status':state['tasks'][task['id']],'elapsed_seconds':o.get('elapsed_seconds'),'usage':usage,'reasoning_tokens':reason,'final_tokens':total-reason if isinstance(total,int) and isinstance(reason,int) else None,'actual_cost_usd':charge.get('actual_cost_usd'),'unresolved_reservation_usd':charge.get('reserved_usd') if 'actual_cost_usd' not in charge else None,'comparison':'Saved GLM comparison overlaps only Cases16–18; no equal-workload speedup inferred.'})
  z.writestr('results-and-costs.json',json.dumps(metrics,indent=2))
  z.writestr('files-sha256.json',json.dumps({i.filename:hashlib_sha(z.read(i.filename)) for i in z.infolist()},indent=2))
 with zipfile.ZipFile(dest) as z:assert z.testzip() is None
 atomic_json(run/'latest-bundle.json',{'path':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size});return dest


def prepared_bundle(plan):
 data,_=verify_plan(plan);dest=ROOT/'results/inspection'/('kimi-prepared-'+Path(plan).name+'-'+str(time.time_ns())+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
  for p in Path(plan).rglob('*'):
   if p.is_file():z.write(p,'plan/'+str(p.relative_to(plan)))
  for name in ('probe/kimi_escalation.py','scripts/kimi_escalation.py','tests/test_kimi_escalation.py','tests/test_kimi_chain.py','docs/KIMI-ESCALATION.md'):
   if (ROOT/name).exists():z.write(ROOT/name,'repository/'+name)
  z.writestr('START-HERE.md','# PREPARED, NOT RUNNING\n\nNo new inference or credential read. The converter request is exact; the critic preview is a sealed recipe with a new-draft slot, not an existing GLM draft. At runtime the exact converter TeX and SHA256 replace that slot in a fresh request, without reasoning/accuracy notes. Both actual wire requests, responses, available reasoning, separately compiled PDFs, coverage, diffs and accounting will be in the automatic final run bundle. The existing pilot qualifies the unchanged route; no extra control is planned. See plan/plan.json, task previews, scope and quarantined secondary assessments. Comparison material is not a model input and has a different scope.\n')
  z.writestr('files-sha256.json',json.dumps({i.filename:hashlib_sha(z.read(i.filename)) for i in z.infolist()},indent=2))
 with zipfile.ZipFile(dest) as z:assert z.testzip() is None
 atomic_json(ROOT/'results/kimi-prepared-bundle-current.json',{'path':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size,'plan':str(plan)});return dest


def restore_reserved(run,data,ledger,state):
 """Resume saved results locally; a reservation can never become a fresh POST."""
 records=ledger.read()['reservations']
 for task in data['tasks']:
  reserved=next((x for x in records if x['folder']=='calls/'+task['id']),None)
  if not reserved and state['tasks'][task['id']]['status']=='dispatching':state['tasks'][task['id']]={'status':'pending'}
  if reserved and state['tasks'][task['id']]['status'] in ('pending','dispatching'):
   folder=run/'calls'/task['id'];result=folder/'result.json'
   if result.exists():state['tasks'][task['id']]=read_json(result)
   elif (folder/'outcome.json').exists() and (folder/'answer.txt').exists():
    actual,_=materialize_task(run,data,task)
    value=process_answer(run,actual,(folder/'answer.txt').read_text(),read_json(folder/'outcome.json'),data)
    atomic_json(result,value);state['tasks'][task['id']]=value
   else:state['tasks'][task['id']]={'status':'reserved_unfinished','reservation':reserved['id'],'retry':False}
 if data.get('qualification_reuse'):
  state['live_qualified']=data['qualification_reuse'];return
 first=data['tasks'][0];status=state['tasks'][first['id']]['status']
 if status=='candidate_saved':
  record=read_json(run/'calls'/first['id']/'outcome.json')
  state['live_qualified']={'transport_and_output_protocol':True,'requested_route':kimi.TAG,'returned_provider':record['returned_provider'],'images_in_request':bool(first['images']),'image_understanding':'not independently established','mathematical_verification':False,'call':first['id']}
 elif status!='pending':raise cloud.AdmissionError('First paid qualification is unsuccessful/uncertain; no later dispatch or retry')


def worker(run):
 with (run/'terminal.log').open('a',buffering=1) as log:
  os.dup2(log.fileno(),1);os.dup2(log.fileno(),2)
  with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):
   data,ledger,state=verify_run(run)
   if state['status'] in TERMINAL:return
   if Path(data['project_root']).resolve()!=ROOT.resolve():raise cloud.AdmissionError('Development overlay cannot execute a paid worker')
   client=None
   try:
    selected_fresh(data)
    env=data['compiler_environment'];source=Path(data['source_parent'])/env['path']
    if not (run/env['path']).exists():shutil.copytree(source,run/env['path'])
    local.books.qualify_compiler(run,{'compiler_environment':env})
    client=kimi.KimiClient(run,history_reader=lambda:kimi.history_snapshot(ROOT,exclude=[run]))
    client.reconcile();restore_reserved(run,data,ledger,state)
    if cloud.decimal(ledger.summary()['unresolved_reserved_usd'])>0:raise cloud.AdmissionError('Uncertain charges remain reserved. Use authenticated GET-only reconciliation; no paid retry.')
    # Require room for the whole unreserved remainder, including all selected operations.
    future=sum((cloud.decimal(t['reservation_usd']) for t in data['tasks'] if state['tasks'][t['id']]['status']=='pending'),Decimal(0));live=cloud.key_allowance(client.control('/key',None,private=True),kimi.KEY_CEILING);history=kimi.history_snapshot(ROOT,exclude=[run]);own=ledger.exposure(ledger.read());prior=cloud.decimal(history['summary']['actual_reported_usd'])+cloud.decimal(history['summary']['unresolved_reserved_usd'])
    if future+own>cloud.decimal(data['pilot_cap_usd']) or future+own+prior>Decimal(kimi.KEY_CEILING) or future+cloud.decimal(history['summary']['unresolved_reserved_usd'])>live:raise cloud.AdmissionError('Remaining plan does not fit pilot/global/live allowance; no partial launch')
    state['status']='running';atomic_json(run/'state.json',state);progress(run,state)
    for index,task in enumerate(data['tasks']):
     if state['tasks'][task['id']]['status']!='pending':continue
     if (run/'pause.json').exists():state['status']='paused';break
     verify_run(run);selected_fresh(data)
     if task.get('draft_from') and state['tasks'][task['draft_from']].get('usable_for_critic') is not True:
      state['tasks'][task['id']]={'status':'skipped_conversion_not_usable','paid_requests':0};continue
     task,body=materialize_task(run,data,task);folder=run/'calls'/task['id']
     state['tasks'][task['id']]={'status':'dispatching','operation':task['operation'],'filename':task['filename'],'started_epoch':time.time()}
     atomic_json(run/'state.json',state);progress(run,state)
     print('Kimi passage:',task['filename'],task['id'],task['operation'],flush=True)
     answer,record=client.dispatch(task,body,folder)
     result=process_answer(run,task,answer,record,data);atomic_json(folder/'result.json',result);state['tasks'][task['id']]=result
     if index==0 and not data.get('qualification_reuse'):
      if result['status']!='candidate_saved':raise cloud.AdmissionError('First paid qualification task did not produce a valid candidate; plan stopped')
      state['live_qualified']={'transport_and_output_protocol':True,'requested_route':kimi.TAG,'returned_provider':record['returned_provider'],'images_in_request':bool(task['images']),'image_understanding':'not independently established','mathematical_verification':False,'call':task['id']}
     atomic_json(run/'state.json',state);progress(run,state)
     if cloud.decimal(ledger.summary()['unresolved_reserved_usd'])>0:raise cloud.AdmissionError('Reported cost missing; hold reservation and reconcile before next paid task')
    else:state['status']='finished' if all(t['status']=='candidate_saved' for t in state['tasks'].values()) else 'finished_with_failures'
   except Exception as exc:
    state.update(status='blocked',diagnostic=client._redact(str(exc)) if client else 'Preflight failed: '+type(exc).__name__)
   finally:atomic_json(run/'state.json',state);progress(run,state);bundle(run)


def launch(plan,budget=None,resume=False):
 data,_=verify_plan(plan)
 if Path(data['project_root']).resolve()!=ROOT.resolve():raise cloud.AdmissionError('Staged development code cannot launch paid work; integrate at a verified idle boundary first')
 old=existing_run(plan)
 if old:
  _,_,state=verify_run(old)
  if state['status'] in TERMINAL:print('Finished plan: zero new calls, no credential read.');return old
  if not resume:raise cloud.AdmissionError('Plan already launched; use resume without resetting allowances')
  run=old
 else:
  if resume:raise cloud.AdmissionError('No authorised run to resume')
  if not budget:raise cloud.AdmissionError('Explicit --accept-budget is required for paid launch')
  if not local.books.speed.idle(ROOT) or not local.books.speed.idle(ROOT/'runs'):raise cloud.AdmissionError('Local trial/worker active; no pause or cloud launch')
  with writer_lock(ROOT),writer_lock(ROOT/'runs'):run=initialise(plan,budget)
 if not local.books.speed.idle(ROOT) or not local.books.speed.idle(ROOT/'runs') or not local.books.speed.idle(run):raise cloud.AdmissionError('Writer active; no duplicate launch')
 cp=subprocess.run(['tmux','has-session','-t',SESSION],capture_output=True,text=True)
 if cp.returncode==0:raise cloud.AdmissionError('Kimi persistent session exists')
 if cp.returncode!=1 or 'permitted' in cp.stderr or 'denied' in cp.stderr:raise cloud.AdmissionError('tmux unavailable')
 # Code/test identity is checked once; no generation is part of these checks.
 local.normal_checks(run);(run/'pause.json').unlink(missing_ok=True)
 command=shlex.join([str(PYTHON),'-B','-u',str(Path(__file__).resolve()),'worker','--run',str(run)])
 subprocess.run(['tmux','new-session','-d','-s',SESSION,'cd '+shlex.quote(str(ROOT))+' && exec '+command],check=True);print('Paid frozen-plan worker requested:',run);return run


def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=('metadata','prepare','inspect','launch-paid','resume','status','pause','worker','bundle','reconcile-charges'));p.add_argument('--metadata',type=Path);p.add_argument('--parent',type=Path);p.add_argument('--project-root',type=Path,default=ROOT);p.add_argument('--out',type=Path);p.add_argument('--plan',type=Path);p.add_argument('--run',type=Path);p.add_argument('--selection',type=Path);p.add_argument('--qualified-run',type=Path);p.add_argument('--pilot-budget-usd',default=kimi.DEFAULT_PILOT_BUDGET);p.add_argument('--accept-budget');a=p.parse_args()
 if a.action=='metadata':
  if not a.out:p.error('--out required')
  print(json.dumps(kimi.fetch_metadata(a.out),indent=2));return
 if a.action=='prepare':
  if not a.parent or not a.metadata:p.error('--parent and --metadata required')
  prepare(a.parent,a.project_root,a.metadata,a.pilot_budget_usd,a.out,a.selection,a.qualified_run);return
 if a.action=='inspect':
  data,_=verify_plan(a.plan);print(json.dumps({k:data[k] for k in ('config','maximum_requests','conservative_maximum_usd','pilot_cap_usd','historical_accounting','authenticated_remaining_usd')},indent=2));return
 if a.action in ('launch-paid','resume'):
  if a.project_root.resolve()!=ROOT.resolve():raise cloud.AdmissionError('Paid execution must use integrated project code, not a development overlay')
  launch(a.plan,a.accept_budget,resume=a.action=='resume');return
 if a.plan and a.action in ('status','bundle','pause'):
  run=existing_run(a.plan)
  if run is None:
   data,_=verify_plan(a.plan)
   if a.action=='status':print(json.dumps({'status':'PREPARED_NOT_RUNNING','plan':str(a.plan),'maximum_requests':data['maximum_requests'],'conservative_maximum_usd':data['conservative_maximum_usd'],'pilot_cap_usd':data['pilot_cap_usd']},indent=2))
   elif a.action=='bundle':print(prepared_bundle(a.plan))
   else:raise cloud.AdmissionError('No worker for this plan')
   return
 else:run=a.run or Path(read_json(ROOT/'results/kimi-current.json')['run'])
 if a.action=='status':print(json.dumps(read_json(run/'progress.json') if (run/'progress.json').exists() else read_json(run/'state.json'),indent=2))
 elif a.action=='pause':atomic_json(run/'pause.json',{'requested_epoch':time.time(),'policy':'Finish current single request; do not interrupt transport'})
 elif a.action=='worker':worker(run)
 elif a.action=='bundle':
  with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):print(bundle(run))
 elif a.action=='reconcile-charges':
  with writer_lock(ROOT),writer_lock(ROOT/'runs'),writer_lock(run):verify_run(run);print(kimi.KimiClient(run).reconcile())
if __name__=='__main__':main()
