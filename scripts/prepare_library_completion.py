#!/usr/bin/env python3
"""Finite saved-work-first child preparation; never creates a budget or calls a model."""
import argparse,copy,difflib,hashlib,json,re,shutil,sys,time,html
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha,fingerprint
from probe.source_library import copy_verified
from probe import library_completion as complete,book_completion as book,image_review as vision
from scripts import library_pipeline as c
PARENT=ROOT/'runs/library-next30-20261108T113644Z';TASK=ROOT/'results/tasks/next30-repair-20261109';DEV=ROOT/'results/next30-repair-development-20261109'
KIENITZ='master-252f9d083f4203a2';BOY='original-af03317e4e74c832'
def selected(s,key):
 v=s['versions'][key][s['current_versions'][key]];path=PARENT/v['path']
 if sha(path)!=v['sha256']:raise ValueError('Parent selected version changed')
 return path.read_text(),v

def image_evidence(sid,pages):return {str(PARENT/'sources'/sid/f'page-{n:03}.png'):sha(PARENT/'sources'/sid/f'page-{n:03}.png') for n in pages}
def norm(text):return ''.join(c for c in book.plain(text).casefold() if c.isalnum())
def environment_spans(text,env):return [m[0] for m in re.finditer(r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}',text,re.S)]
def proof_span(text,heading):
 i=text.index(heading)
 if heading=='THEOREM 3.2.':return text[i:text.index('REMARK 3.1.',i)].rstrip()
 if heading=='REMARK 3.1.':return text[i:text.index(r'\section',i)].rstrip()
 return text

def numeric_source_rows(text):
 rows=[]
 for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',text,re.S):
  cells=[html.unescape(re.sub('<[^>]+>','',x)).strip() for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',tr,re.S)]
  if len(cells)>1 and all(re.fullmatch(r'-?\d+(?:\.\d+)?',x) for x in cells[1:]):rows.append((cells[0],[str(Decimal(x).normalize()) for x in cells[1:]]))
 return rows

def numeric_tex_rows(text):
 rows=[]
 for line in text.splitlines():
  cells=re.split(r'(?<!\\)&',line)
  if len(cells)<2:continue
  name=cells[0].strip().replace(r'\&','&');values=[]
  for cell in cells[1:]:
   value=re.sub(r'[\s$]|\\\\','',cell)
   if not re.fullmatch(r'-?\d+(?:\.\d+)?',value):break
   values.append(str(Decimal(value).normalize()))
  else:rows.append((name,values))
 return rows

def curate():
 if not all(c.base.books.speed.idle(p) for p in (ROOT,ROOT/'runs',PARENT)):raise ValueError('Active writer; no integration')
 s=read_json(PARENT/'state.json');assert s['status']==c.TERMINAL
 units=copy.deepcopy(s['source_units']);texts={k:selected(s,k)[0] for k in s['current_versions']};changes={};decisions=[];changed=set();reviews=[];review_salvage=[];transfers=[]
 def change(key,new,reason):
  if key not in changes:changes[key]={'original':texts.get(key,''),'reasons':[]}
  texts[key]=new;changes[key]['reasons'].append(reason);changed.add(key)
 def note(key,body):
  text=texts[key];addition='\n% PDF2TEX_GENERATED_NOTES_BEGIN\n\\section*{Source-checked completion notes}\n'+body+'\n'
  if '% PDF2TEX_GENERATED_NOTES_BEGIN' in text:addition='\n'+body+'\n'
  change(key,text.replace(r'\end{document}',addition+r'\end{document}'),'Attributed source-check note; source-faithful parent retained')
 # Exact provided candidates, originals and source inputs are checked before adoption.
 for row in read_json(TASK/'fragment-candidates/manifest.json'):
  key=row['unit'];raw=(PARENT/'calls'/row['call']/'content.txt').read_bytes();candidate=TASK/'fragment-candidates'/row['call']/'candidate.tex'
  if complete.digest(raw)!=row['original_response_sha256'] or sha(candidate)!=row['candidate_sha256']:raise ValueError('Fragment candidate/raw identity differs')
  if fingerprint(read_json(TASK/'fragment-candidates'/row['call']/'source-unit.json'))!=fingerprint(units[key]):raise ValueError('Fragment source scope differs')
  wrapped,evidence=complete.wrap_fragment(raw)
  if wrapped!=candidate.read_bytes():raise ValueError('Generic envelope differs from supplied candidate')
  for asset in row['assets']:
   if sha(units[key]['assets'][asset['reference']])!=asset['sha256']:raise ValueError('Fragment image changed')
  change(key,wrapped.decode(),'Exact saved single-fence body wrapped; outside notes and raw response retained');reviews.append({'key':key,'reason':'Saved converter fragment now has a qualified envelope; original critic never dispatched','parent_call':row['call'],'prior_local_review_attempts':0})
  atomic_json(DEV/'fragment-evidence'/key/'normalization.json',evidence)
  for f in (TASK/'fragment-candidates'/row['call']).rglob('*'):
   if f.is_file():copy_verified(f,DEV/'fragment-evidence'/key/f.relative_to(TASK/'fragment-candidates'/row['call']))
 # Restore only an objectively missing outer JSON brace; preserve attestations.
 for call in ('call-073','call-121','call-140'):
  task=next(t for t in s['tasks'] if t.get('call')==call);key=task['key'];raw=(PARENT/'calls'/call/'content.txt').read_text();base=texts[key]
  try:
   data,normalization=complete.saved_review(raw,complete.digest(base));new,log=vision.apply_review(base,data)
  except (ValueError,KeyError,TypeError) as exc:
   review_salvage.append({'call':call,'unit':key,'status':'not_recoverable','reason':str(exc)})
   reviews.append({'key':key,'reason':'Exact saved review cannot be recovered without inventing the draft identity','parent_call':call,'prior_local_review_attempts':1});continue
  change(key,new,'Recovered saved review with unchanged exact draft hash and fields; '+normalization['normalization'])
  folder=DEV/'review-salvage'/call;folder.mkdir(parents=True,exist_ok=True);(folder/'raw.txt').write_text(raw);atomic_json(folder/'normalized.json',data);atomic_json(folder/'findings.json',log);atomic_json(folder/'normalization.json',normalization);(folder/'original.tex').write_text(base);(folder/'reviewed.tex').write_text(new)
  review_salvage.append({'call':call,'unit':key,'status':'recovered','normalization':normalization,'findings':log,'new_request':False})
 # Kienitz: original-source checked vectors, then whole figure objects across seam.
 key=KIENITZ+'-unit-001';provided=read_json(TASK/'source-checked-candidate'/key/'provenance.json')
 assert complete.digest(texts[key])==provided['original_selected_sha256'] and texts[key].count(provided['old'])==1
 assert sha(PARENT/'sources'/KIENITZ/'page-003.png')==provided['source_image_sha256']
 change(key,texts[key].replace(provided['old'],provided['new']),'Original p3 stacked vectors directly checked; two column arrays restored without changing entries')
 decisions.append({'id':'kienitz-vectors','disposition':'applied_source_transcription_repair',**provided,'independent_check':'Codex rechecked original p3; stacked X/Y and muX/muY unambiguous','images':image_evidence(KIENITZ,[3])})
 groups=[(1,2,0,[1,2,3],4),(2,4,0,[1,2,3],4),(3,4,9,[10,11],12),(5,5,7,[8,9,10],11),(6,6,4,[5,6,7,8,9,10],11)]
 fig_records=[]
 for number,page,canonical,members,caption_index in groups:
  asset=lambda i:f'assets/{KIENITZ}-p{page}-region-{i}.png'
  owner=KIENITZ+('-unit-001' if number<=3 else '-unit-002');raw=read_json(PARENT/'arms/mineru_pro/pages'/f'{KIENITZ}-p{page}'/'native.json');canonical_name=asset(canonical);member_names=[asset(i) for i in members];caption_id=f'{KIENITZ}-p{page}-r{caption_index}'
  chunks=[(k,chunk) for k in (KIENITZ+'-unit-001',KIENITZ+'-unit-002') for chunk in environment_spans(texts[k],'figure') if any('{'+a+'}' in chunk for a in [canonical_name,*member_names])]
  captions=[re.search(r'\\caption\s*\{',chunk) for _,chunk in chunks];captions=[book.braced(chunk,m.end()-1)[0] for (_,chunk),m in zip(chunks,captions) if m]
  if len(captions)!=1:raise ValueError('Figure caption ambiguous')
  labels=[label for _,chunk in chunks for label in re.findall(r'\\label\{[^{}]+\}',chunk)]
  if len(labels)!=len(set(labels)):raise ValueError('Conflicting figure labels; explicit reconciliation needed')
  figure='\\begin{figure}[htbp]\n\\centering\n\\includegraphics[width=.95\\linewidth,keepaspectratio]{'+canonical_name+'}\n\\caption{'+captions[0]+'}\n'+'\n'.join(labels)+'\n\\end{figure}'
  first=True
  for k,chunk in chunks:
   replacement=figure if k==owner and first else ''
   if replacement:first=False
   change(k,texts[k].replace(chunk,replacement,1),f'Figure {number}: retain complete composite once with original full caption; remove visually verified duplicate panel display')
  if first:raise ValueError('Figure owner not found')
  needed=[f'{KIENITZ}-p{page}-r{i}' for i in [canonical,*members,caption_index]]
  moved=[]
  for k in (KIENITZ+'-unit-001',KIENITZ+'-unit-002'):
   if k==owner:continue
   rows=[b for b in units[k]['native_blocks'] if b['id'] in needed]
   if rows:
    units[k]['native_blocks']=[b for b in units[k]['native_blocks'] if b['id'] not in needed];units[owner]['native_blocks']+=rows;moved+=[b['id'] for b in rows]
  if moved:transfers.append({'figure':number,'from':KIENITZ+'-unit-002','to':owner,'blocks':moved,'reason':'Whole Figure3/caption has one emitted owner; neighbour receives read-only context'})
  crop_files={str(PARENT/'sources'/KIENITZ/f'page-{page:03}.png'):sha(PARENT/'sources'/KIENITZ/f'page-{page:03}.png')};crop_files.update({units[owner]['assets'][a]:sha(units[owner]['assets'][a]) for a in [canonical_name,*member_names]})
  record={'id':f'kienitz-figure-{number}','canonical':canonical_name,'members':member_names,'source_check':{'visual_check':True,'physical_page':page,'caption_block':caption_id,'caption_native_sha256':fingerprint(raw[caption_index]),'asset_sha256':{a:sha(units[owner]['assets'][a]) for a in [canonical_name,*member_names]},'files':crop_files,'geometry':{str(i):raw[i]['bbox'] for i in [canonical,*members]},'reason':'Original source page and complete composite/individual panels directly compared; not inferred solely from overlapping boxes'}}
  units[owner].setdefault('coverage_metadata',{}).setdefault('verified_figure_groups',[]).append(record);fig_records.append((owner,record,figure,needed))
 for k in (KIENITZ+'-unit-001',KIENITZ+'-unit-002'):
  u=units[k];u['native_blocks'].sort(key=lambda b:(b['page']['original_physical_page'],int(b['id'].rsplit('-r',1)[1])));u['blocks']=[b['id'] for b in u['native_blocks']];u['first']=u['blocks'][0];u['last']=u['blocks'][-1];u['text']='\n\n'.join(b['tex'] for b in u['native_blocks']);u['text_sha256']=complete.digest(u['text']);u['physical_pages']=sorted({b['page']['original_physical_page'] for b in u['native_blocks']})
  u['figure_ownership_crosswalk']=transfers
 units[KIENITZ+'-unit-001']['source_order_end']=units[KIENITZ+'-unit-001']['source_order_start']+len(units[KIENITZ+'-unit-001']['blocks'])
 units[KIENITZ+'-unit-002']['source_order_start']=units[KIENITZ+'-unit-001']['source_order_end']
 units[KIENITZ+'-unit-002']['source_order_end']=units[KIENITZ+'-unit-002']['source_order_start']+len(units[KIENITZ+'-unit-002']['blocks'])
 units[KIENITZ+'-unit-002']['context']+='\nREAD-ONLY CONTEXT: complete Figure3 and its caption are emitted by preceding unit001; do not duplicate them.\n'+next(x[2] for x in fig_records if x[1]['id']=='kienitz-figure-3')
 for k,group,figure,ids in fig_records:units[k].setdefault('content_adjudications',[]).append(complete.adjudication(texts[k],units[k],kind='figure',targets=[group['id']],source_blocks=ids,output_spans=[figure],images=group['source_check']['files'],reason='Complete figure and full caption preserved as one source-checked assembly object',details=group))
 # Mathematical adjudication: keep printed and editorial readings distinct.
 key=BOY+'-unit-010';old_formula=r'\kappa X + \kappa^ {T} X - \Gamma = 0.';new_formula=r'X \kappa + \kappa^ {T} X - \Gamma = 0.'
 if texts[key].count(old_formula)!=1:raise ValueError('Lyapunov source/selected anchor differs')
 change(key,texts[key].replace(old_formula,new_formula),'Editorial correction to printed AppendixD: linearizing Y^2+Y*kappa+kappa^T*Y-epsilon*Gamma=0 gives X*kappa+kappa^T*X-Gamma=0. Printed kappa*X order retained in parent.')
 note(key,r'Independent source check (physical p31, with CARE on pp7/28): the print reads $\kappa X+\kappa^T X-\Gamma=0$. The working derivative uses $X\kappa+\kappa^T X-\Gamma=0$, the first-order equation obtained by setting $Y=\epsilon X+O(\epsilon^2)$ in CARE. Matrix products need not commute. This is an attributed correction to the printed mathematics, not a transcription repair. The original printed reading remains in the parent. Appendix F recurrence and index discrepancies remain unresolved; no algorithmic corrections are silently applied.')
 decisions.append({'id':'boy-lyapunov','disposition':'applied_editorial_correction_to_print','old':old_formula,'new':new_formula,'images':image_evidence(BOY,[7,28,31]),'support':'CARE Y^2+Y*kappa+kappa^T*Y-epsilon*Gamma=0: coefficient of epsilon gives X*kappa+kappa^T*X-Gamma=0. Counterexample kappa=[[1,1],[0,2]], Gamma=I, X=[[1/2,-1/6],[-1/6,1/3]] solves corrected equation; printed order yields [[5/6,0],[-1/6,7/6]] rather than I.','source_faithful_parent_preserved':True})
 decisions.append({'id':'boy-discount-rate','disposition':'existing_editorial_correction_supported','images':image_evidence(BOY,[1,2]),'printed':'Discounting integrand (X_s), with r omitted','working':'r(X_s)','support':'Price must discount at the short rate defined in1.2; generator1.5 subtracts r(x). Originalpage2 was directly checked. No new formula edit required.'})
 decisions.append({'id':'boy-proof-label','disposition':'existing_editorial_correction_supported','images':image_evidence(BOY,[12,28]),'printed':'Second Proof of(4.3) onp28','working':'Proof of(4.4)','support':'Second calculation proves commutation with Q2; page12 equation4.4 is precisely [Ltilde,Q2]=0. Original duplicated label is retained in provenance; no new formula edit.'})
 decisions.append({'id':'kenyon-discount-superscript','disposition':'existing_transcription_repair_supported','images':image_evidence('master-5ab1bbb5db23a427',[12]),'printed':'r^B + lambda^C without a bar on B','working':'r^B + lambda^C','support':'Original physicalp12, paragraph immediately before2.2.1, directly checked. Existing selected edit removes a draft-only bar; no new formula edit.'})
 for topic,reading,reason in [('mu-indices','mu11+mu22 vs mu1+mu2','Diagonal values are defined as mu_j; plausible notation typo, but retain source reading and flag a consistency check.'),('initial-phi','phi^1_{0,0}=1','Degree-zero polynomial suggests superscript0; retained unverified source reading pending a full recurrence consistency check.'),('recurrence','Previous-row indices2r,2r+1','These exceed the previous degree2r-2. Printed formula directly checked; do not guess replacements without deriving the recurrence.'),('dC','C1 := C1 + dC after defining dC_s','Likely missing s suffix in update. Original p32 checked; source formula remains with explicit uncertainty.')]:decisions.append({'id':'boy-'+topic,'disposition':'unresolved_source_notation','printed':reading,'support':reason,'images':image_evidence(BOY,[32,33])})
 # Complete source-reference matches, plus explicitly checked title/theorem spans.
 analysis=read_json(DEV/'heading-source-analysis.json');bykey={}
 for row in analysis:bykey.setdefault(row['key'],[]).append(row)
 for key,rows in bykey.items():
  text=texts[key];u=units[key];details=[];ids=[]
  for row in rows:
   ids+=row['source_ids'];h=row['heading']
   if row['complete_normalized_source_present']:
    if norm(row['source']) not in norm(text):raise ValueError('Full reference entry no longer present')
    details.append({'heading':h,'comparison':'Complete source reference segment, including title/venue/numbers, preserved under formatting normalization','source_ids':row['source_ids']})
   elif key==BOY+'-unit-003':
    details.append({'heading':h,'comparison':'Directly checked original pp10-11: theorem(a)-(b),3.4-3.7 and remark(a)-(d) all retained. Macro spelling differs, statement content preserved.'})
   elif key=='master-02d24558f31b3ccc-unit-001':
    if r'\title*{' not in text or 'The opinions expressed here are those of the author' not in text:raise ValueError('Title/footnote differs')
    change(key,text.replace(r'\title*{',r'\title{',1),'Correct standard article title command only; preserve full title and explanatory footnote');text=texts[key];details.append({'heading':h,'comparison':'Full title, author/date, abstract and complete explanatory footnote retained; source marker is attached to footnote, not lost text.'})
   elif key=='master-2fa20dfd5aa19000-unit-001':
    for cmd in ('title','author','date'):text=text.replace('\\'+cmd+'*{','\\'+cmd+'{')
    change(key,text,'Standard article title/author/date command syntax only; all metadata/footnote content retained');details.append({'heading':h,'comparison':'Full title, author, date and publication notice are present; starred standard commands normalized separately.'})
   elif key=='master-2cf2afa6f61b8942-unit-001':
    if 'Schr' not in text or not all(re.search(r'\\tag\s*\{'+str(n)+r'\}',text) for n in range(2,6)):raise ValueError('Algorithm statement/numbered steps absent')
    details.append({'heading':h,'comparison':'Section title and full Sinkhorn/Newton-Sinkhorn passage, equations2-5, implementation method and figure2 retained. Source bullet and accented TeX spelling differ; no scope removal.'})
   else:raise ValueError('Unqualified heading adjudication '+key)
  source_pages=sorted({b['page']['original_physical_page'] for b in u['native_blocks'] if b['id'] in ids});spans=environment_spans(text,'thebibliography')
  if not spans:
   if key==BOY+'-unit-003':spans=[proof_span(text,h) for h in ('THEOREM 3.2.','REMARK 3.1.')]
   else:spans=[text] # Full checked title/abstract or algorithm passage; exact draft bound.
  record=complete.adjudication(text,u,kind='heading',targets=[row['heading'] for row in rows],source_blocks=list(dict.fromkeys(ids)),output_spans=spans,images=image_evidence(u['source_key'],source_pages),reason='Close only verified heading-absence claims; full reference/statement spans bound, not keyword presence',details=details)
  units[key].setdefault('content_adjudications',[]).append(record);changed.add(key)
 # Tables: strict ordered row equality; captions and continuation source images bound.
 key='master-de3d6a9223dd0bd5-unit-003';u=units[key];text=texts[key];source_tables=[b for b in u['native_blocks'] if b['kind']=='table'];source_rows=[x for b in source_tables for x in numeric_source_rows(b['tex'])];output_tables=environment_spans(text,'tabular');output_rows=[x for table in output_tables for x in numeric_tex_rows(table)]
 if len(source_rows)!=47 or source_rows!=output_rows:raise ValueError('Lou numeric table cells/order differ')
 previous_key='master-de3d6a9223dd0bd5-unit-002';previous_text=texts[previous_key];previous_tables=[b for b in units[previous_key]['native_blocks'] if b['kind']=='table'];previous_rows=[x for b in previous_tables for x in numeric_source_rows(b['tex'])]
 previous_out=[x for table in environment_spans(previous_text,'tabular') for x in numeric_tex_rows(table)]
 if previous_rows!=previous_out:raise ValueError('Lou preceding Table2 seam differs')
 details={'source_region_rows':[len(numeric_source_rows(b['tex'])) for b in source_tables],'rows':source_rows,'preceding_unit':previous_key,'preceding_selected_sha256':complete.digest(previous_text),'preceding_table_rows_verified':previous_rows,'source_groups':[[source_tables[0]['id']],[b['id'] for b in source_tables[1:]]],'logical_tables':2,'caption':'Table3 full parameter caption and Table2 top-decliner/top-gain headers retained','visual_check':'Original pp8-10 checked; p9 begins continued Table2, Table3 starts p9 and continues p10'}
 units[key].setdefault('content_adjudications',[]).append(complete.adjudication(text,u,kind='table',targets=[b['id'] for b in source_tables],source_blocks=[b['id'] for b in u['native_blocks'] if b['kind'] in ('table','table_caption')],output_spans=environment_spans(text,'table') or output_tables,images=image_evidence(u['source_key'],[8,9,10]),reason='Three extracted regions comprise two logical tables with all47ordered numeric rows',details=details));changed.add(key)
 key='master-5ab1bbb5db23a427-unit-001';u=units[key];text=texts[key];tables=environment_spans(text,'table');assert len(environment_spans(text,'tabular'))==1
 if text.count(r'\co{}-equivalent')!=1 or r'\newcommand{\co}{CO\textsubscript{2}e}' not in text:raise ValueError('Kenyon macro identity changed')
 change(key,text.replace(r'\co{}-equivalent',r'CO\textsubscript{2}-equivalent',1),'Original p3 table spells CO2-equivalent; replace only the doubled-equivalent macro wording, retaining CO2e elsewhere')
 text=texts[key];expanded=text.replace(r'\codeva{}','CO2eVA').replace(r'\co{}','CO2e')
 source_tables=[b for b in u['native_blocks'] if b['kind']=='table'];cells=[]
 for b in source_tables:
  for cell in re.findall(r'<td>(.*?)</td>',b['tex'],re.S):
   if norm(html.unescape(cell)) not in norm(expanded):raise ValueError('Kenyon full table cell missing')
   cells.append(html.unescape(cell))
 if len(cells)!=15:raise ValueError('Kenyon table shape changed')
 note(key,'Source visual key (physical p3): CCVA and CO2eVA are green climate-related categories; CVA, FVA and KVA are grey existing valuation adjustments. The two separated printed blocks comprise one numbered Table 1. This textual colour key preserves category meaning without a new PDF build.');text=texts[key]
 units[key].setdefault('content_adjudications',[]).append(complete.adjudication(text,u,kind='table',targets=[b['id'] for b in source_tables],source_blocks=[b['id'] for b in u['native_blocks'] if b['kind'] in ('table','table_caption')],output_spans=environment_spans(text,'table') or environment_spans(text,'tabular'),images=image_evidence(u['source_key'],[3]),reason='Original p3: two blocks of Table1, all5row names/descriptions and caption retained',details={'source_cells':cells,'logical_tables':1,'colour_key':'CCVA/CO2eVA green; CVA/FVA/KVA grey'}));changed.add(key)
 # Freeze current curations and independently assess every preserved/new selection.
 outrows=[]
 for key in sorted(changed):
  folder=DEV/'curated'/key;folder.mkdir(parents=True,exist_ok=True);text=texts[key];before=changes.get(key,{}).get('original',selected(s,key)[0] if key in s['current_versions'] else '')
  (folder/'document.tex').write_text(text);(folder/'prior.tex').write_text(before);(folder/'changes.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='prior.tex',tofile='document.tex')));atomic_json(folder/'unit.json',units[key])
  check=c.content_check(PARENT,{'source_units':{key:units[key]}},{'key':key},text)
  record={'unit':key,'sha256':complete.digest(text),'original_sha256':complete.digest(before),'source_unit_sha256':sha(folder/'unit.json'),'changes':changes.get(key,{}).get('reasons',['Source-bound coverage adjudication; TeX unchanged']),'content_check':check,'review_pending':any(x['key']==key for x in reviews)};atomic_json(folder/'provenance.json',record);outrows.append(record)
 original=[b for u in s['source_units'].values() for b in u['blocks']];ownership=complete.verify_ownership(units,original,transfers)
 atomic_json(DEV/'curations.json',outrows);atomic_json(DEV/'review-plan.json',reviews);atomic_json(DEV/'review-salvage.json',review_salvage);atomic_json(DEV/'source-checked-decisions.json',decisions);atomic_json(DEV/'figure-ownership.json',{'groups':[g for _,g,_,_ in fig_records],'transfers':transfers});atomic_json(DEV/'ownership-before-new-scopes.json',ownership)
 print('Curations',len(outrows),'pending reviews',len(reviews),'content flags',[(x['unit'],x['content_check']['content_issues']) for x in outrows if not x['content_check']['usable']])


def prepare():
 from probe.library_allocation import verify as verify_allocation
 from probe.experiment import verify_seal
 from probe import library_first as policy
 pointer=ROOT/'results/library-completion-current.json'
 if pointer.exists():
  existing=Path(read_json(pointer)['run']);existing_state=read_json(existing/'state.json')
  if existing_state.get('calls') or existing_state.get('launches'):
   print('Existing completion run; resume only:',existing);return existing
 if not all(c.base.books.speed.idle(p) for p in (ROOT,ROOT/'runs',PARENT)):raise ValueError('Existing writer; no duplicate')
 baseline=read_json(DEV/'baseline.json');parent=read_json(PARENT/'state.json');old=read_json(PARENT/'plan.json')
 if parent['status']!=c.TERMINAL or sha(PARENT/'state.json')!=baseline['parent_state_sha256']:raise ValueError('Parent state changed; reconcile')
 verify_allocation(old['paid_approval'])
 rows=read_json(DEV/'curations.json');bykey={x['unit']:x for x in rows};review_plan=read_json(DEV/'review-plan.json')
 run=ROOT/'runs'/('library-completion-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));run.mkdir()
 state={k:copy.deepcopy(parent[k]) for k in ('chapter_contract','timing_policy','execution_limits','concurrency_policy','compiler_environment','runtime_image','remote_models')}
 state.update(status='prepared',stage='finite saved-work completion',calls=[],tasks=[],versions=copy.deepcopy(parent['versions']),current_versions=copy.deepcopy(parent['current_versions']),source_units=copy.deepcopy(parent['source_units']),derived_inputs={},documents={},connection_failures=0,first_dispatch=None,active_stage=1,stages={'1':{}},launches=[],disable_dependency_downloads=True,suite_protocol='source-image-review-v1',production_stage={'task_ids':[]},resource_phase='reuse_existing_GLM_no_OCR',remote='/home/mdi/projects/pdf-to-latex-comparisons/'+run.name,extraction=copy.deepcopy(parent['extraction']),extraction_done=True,models_downloaded=True,inputs_prepared=True,ready_baseline=72,ready_added_offline=0,paid_approval_sha256=fingerprint(old['paid_approval']),historical_tasks=copy.deepcopy(parent['tasks']),historical_calls=copy.deepcopy(parent['calls']))
 plan=copy.deepcopy(old);plan.update(parent_run=str(PARENT),workflow='library-first-v1',completion_phase=True,accept_exact_fragments=True,task_order='completion_frozen',approval_registry=str(pointer),workloads={'mineru_pro':[]},runtime_contract={k:state.get(k) for k in c.RUNTIME_FIELDS},objective='Finish existing34source identities using exact saved work; no new allocation/OCR/corpus expansion',lineage={'parent_state_sha256':sha(PARENT/'state.json'),'parent_plan_sha256':sha(PARENT/'plan.json'),'parent_binding_sha256':sha(PARENT/'binding.json'),'parent_local_calls_consumed':len(parent['calls']),'parent_provider_reservations_consumed':len(read_json(Path(old['paid_approval']['cloud_run'])/'billing.json')['reservations']),'same_allocation_id':old['allocation_id'],'new_allocation_usd':'0'},task_instruction_sha256=sha(TASK/'CODEX-REPAIR-AND-RUN.md'))
 plan.pop('task_plan_sha256',None);plan['paid_admission_note']='Existing allocation/key holds preserved; live/current provider guards remain mandatory. Unavailable cloud work must not block local work.'
 # Preserve saved byte identities; all completed attempt records remain at parent.
 for folder in ('versions','sources'):
  shutil.copytree(PARENT/folder,run/folder)
 shutil.copytree(PARENT/'arms/mineru_pro',run/'arms/mineru_pro')
 atomic_json(run/'historical/parent-tasks.json',parent['tasks']);atomic_json(run/'historical/parent-calls.json',parent['calls']);atomic_json(run/'historical/parent-deliveries.json',parent['documents'])
 for d in plan['documents']:
  sid=d['source_id'];doc=parent['documents'][sid];folder=c.reconcile.LIBRARY/d['library_document']['folder'];current=read_json(folder/'current.json') if (folder/'current.json').exists() else None;expected=doc.get('publication') if doc.get('selected_new_generation') else doc.get('historical_selection')
  if current!=expected or sha(d['original'])!=d['sha256']:raise ValueError('Library source/selection changed')
  d['reused_extraction_pages']=d['physical_pages'];d.pop('fixed_native',None);d.pop('fixed_native_sha256',None);d.pop('unit_key_prefix',None);d.pop('unit_insertion_after',None)
  record=copy.deepcopy(doc);record.update(historical_selection=current,reused_units=list(doc['units']),selected_new_generation=False,planning_done=True,parent_publication=doc.get('publication'),parent_model_review=read_json(Path(doc['delivery'])/'library-status.json')['model_review'])
  affected=any(k in bykey for k in doc['units']) or bool(doc.get('outstanding_scopes')) or any(t['key'] in doc['units'] for t in review_plan)
  if affected:
   record.update(status='saved_recovery_prepared',published=False);record.pop('publication',None);record.pop('publication_revision',None);record.pop('delivery',None)
  else:
   verify_seal(Path(doc['delivery']));shutil.copytree(doc['delivery'],run/'reused-deliveries'/sid);record.update(published=True,delivery=str(run/'reused-deliveries'/sid),status=doc['status'])
  state['documents'][sid]=record
 for key,unit in list(state['source_units'].items()):
  if key in bykey:unit=read_json(DEV/'curated'/key/'unit.json');state['source_units'][key]=unit
  newassets={}
  for ref,path in unit['assets'].items():
   source=Path(path);dest=run/'inputs'/ref;copy_verified(source,dest);newassets[ref]=str(dest)
  unit['assets']=newassets
  history=run/'inputs'/key/'review-history';history.mkdir(parents=True,exist_ok=True)
  for f in (PARENT/'inputs'/key/'review-history').glob('*'):
   if f.is_file():copy_verified(f,history/f.name)
  for task in [t for t in parent['tasks'] if t['key']==key]:
   if task.get('call'):
    for f in (PARENT/'call-results'/task['call']).glob('*'):
     if f.is_file():copy_verified(f,history/(task['call']+'-'+f.name))
   paid=task.get('paid_recovery',{})
   if paid.get('attempt_path'):
    for name in ('findings.json','changes.diff','outcome.json','error.json'):
     f=Path(paid['attempt_path'])/name
     if f.exists():copy_verified(f,history/('kimi-'+task['phase']+'-'+name))
  if key in bykey:
   dest=run/'versions'/key/'source-checked-completion';dest.mkdir(parents=True)
   for name in ('document.tex','prior.tex','changes.diff','provenance.json'):copy_verified(DEV/'curated'/key/name,dest/name)
   version={'path':str((dest/'document.tex').relative_to(run)),'sha256':bykey[key]['sha256'],'compilation':{'status':'not_requested'},'provenance':{'parent_run':str(PARENT),'parent_selection':parent['current_versions'].get(key),'supplied_task_sha256':sha(TASK/'CODEX-REPAIR-AND-RUN.md'),'changes':bykey[key]['changes']}}
   state['versions'].setdefault(key,{})['source-checked-completion']=version;state['current_versions'][key]='source-checked-completion'
 # New source scopes: one qualified coherent output scope each, no recursive splitting.
 new_units=[]
 for g in read_json(TASK/'evidence/OUTSTANDING-SCOPES.json'):
  sid=g['source_id'];source=read_json(PARENT/'source-plans'/f'{sid}.json');scope=next(x for x in source['scopes'] if x['blocks']==g['blocks'])
  if scope['text_sha256']!=g['text_sha256'] or complete.digest(scope['text'])!=scope['text_sha256']:raise ValueError('Missing scope identity differs')
  if len(scope['physical_pages'])!=5 or len(scope['text'])>30000:raise ValueError('Specific missing-scope qualification changed')
  key=sid+'-completion-001';blocks=[b for x in source['scopes'] for b in x['native_blocks']];before=blocks[:scope['source_order_start']]
  previous=next(k for k in state['documents'][sid]['units'] if state['source_units'][k]['blocks'][-1]==before[-1]['id'])
  assets=copy.deepcopy(state['source_units'][previous]['assets']);quality=read_json(run/'sources'/sid/'secondary-assessment.json')
  unit=copy.deepcopy(scope);unit.update(source_key=sid,title=state['documents'][sid]['filename']+' — previously unscheduled complete connected passage',disposition='included',limits={'maximum_pages':5,'maximum_chars':30000},context='Earlier source definitions are read-only context, never emitted again.\n'+'\n\n'.join(b['tex'] for b in before),context_blocks=[b['id'] for b in before],secondary='\n\n'.join('Physical page '+str(p['physical_pdf_page'])+'\n'+p['text'] for p in quality['pages'] if p['physical_pdf_page'] in scope['physical_pages']),assets=assets,cloud_context='\n\n'.join(b['tex'] for b in before[-6:]),source_bound_exception={'authority_sha256':sha(TASK/'CODEX-REPAIR-AND-RUN.md'),'source_text_sha256':scope['text_sha256'],'pages':scope['physical_pages'],'reason':'Keep connected mathematical passage intact; five original pages plus three detail crops remain within unchanged16384image-token/16MiBrequest/context guards','no_global_limit_change':True})
  state['source_units'][key]=unit;order=state['documents'][sid]['units'];order.insert(order.index(previous)+1,key);state['documents'][sid]['outstanding_scopes']=[];state['documents'][sid]['source_accounting']=dict(state['documents'][sid].get('source_accounting',{}),outstanding_regions=0,fully_scheduled=True,completion_scope=key);new_units.append(key)
  atomic_json(run/'source-plans'/f'{sid}.json',{'parent_source_plan':str(PARENT/'source-plans'/f'{sid}.json'),'parent_sha256':sha(PARENT/'source-plans'/f'{sid}.json'),'completion_scope':unit,'scopes':[unit]})
  for phase in ('convert','critic'):state['tasks'].append({'id':key+'/'+phase,'key':key,'source_key':sid,'phase':phase,'status':'pending','reasoning_effort':'high','section_title':unit['title'],'recovery_lineage':{'original_scope_sha256':scope['text_sha256'],'prior_local_phase_attempts':0,'authorized_new_attempts':1}})
 # Only genuinely missing review phases; the failed historic responses stay consumed.
 for item in review_plan:
  key=item['key'];unit=state['source_units'][key];state['tasks'].append({'id':key+'/critic','key':key,'source_key':unit['source_key'],'phase':'critic','status':'pending','reasoning_effort':'high','section_title':unit['title'],'recovery_lineage':{'parent_call':item['parent_call'],'prior_local_phase_attempts':item['prior_local_review_attempts'],'authorized_new_attempts':1,'reason':item['reason']}})
 for sid,doc in state['documents'].items():
  ids=[b for k in parent['documents'][sid]['units'] for b in parent['source_units'][k]['blocks']]
  for gap in parent['documents'][sid].get('outstanding_scopes',[]):ids+=gap['blocks']
  doc['completion_ownership']=complete.verify_ownership({k:state['source_units'][k] for k in doc['units']},ids,read_json(DEV/'figure-ownership.json')['transfers'] if sid==KIENITZ else ())
  if not doc.get('published'):doc['source_accounting']=dict(doc.get('source_accounting',{}),total_regions=len(ids),included_regions=len(ids),outstanding_regions=0,all_regions_accounted=True,fully_scheduled=True)
 for key,unit in state['source_units'].items():
  atomic_json(run/'inputs'/key/'unit.json',unit);state['derived_inputs']['inputs/'+key+'/unit.json']=sha(run/'inputs'/key/'unit.json')
  for asset in unit['assets'].values():state['derived_inputs'][asset]=sha(asset)
  if key in state['current_versions']:
   v=state['versions'][key][state['current_versions'][key]];v['content_check']=c.content_check(run,state,{'key':key},(run/v['path']).read_text())
 state['production_stage']['task_ids']=[t['id'] for t in state['tasks']]
 atomic_json(run/'plan.json',plan)
 for t in state['tasks']:
  if t['phase']=='critic':c.review_images(run,state,t)
  if t['phase']=='convert' or t['key'] in state['current_versions']:
   body=c.body_for(run,state,t);c.runtime.protocol.budget(body,1048576)
 task_plan={'task_ids':state['production_stage']['task_ids'],'task_definitions':[{k:t[k] for k in ('id','key','source_key','phase','reasoning_effort')} for t in state['tasks']],'primary_request_allowance':len(state['tasks']),'local_conversions':2,'local_reviews':len(review_plan)+2,'automatic_retries':0,'conditional_paid_attempts_maximum':len(state['tasks']),'paid_scope':'Original logical source/phase reservations remain shared; previously dispatched phases cannot be resent','source_ownership':{k:u['blocks'] for k,u in state['source_units'].items()},'outstanding_scopes':{sid:d.get('outstanding_scopes',[]) for sid,d in state['documents'].items()},'lineages':{t['id']:t['recovery_lineage'] for t in state['tasks']}}
 atomic_json(run/'task-plan.json',task_plan);state['task_plan_path']='task-plan.json';state['task_plan_sha256']=sha(run/'task-plan.json')
 for name in ('curations.json','review-plan.json','review-salvage.json','source-checked-decisions.json','figure-ownership.json','ownership-before-new-scopes.json','account-readiness.json','paid-size-audit.json','heading-source-analysis.json','baseline.json'):copy_verified(DEV/name,run/'completion-evidence'/name)
 checked_images={}
 for unit in state['source_units'].values():
  for record in unit.get('content_adjudications',[]):checked_images.update(record['images'])
 for decision in read_json(DEV/'source-checked-decisions.json'):checked_images.update(decision.get('images',{}))
 for name,digest in checked_images.items():
  source=Path(name);relative=source.relative_to(PARENT) if source.is_relative_to(PARENT) else Path('external')/source.name
  copy_verified(source,run/'completion-evidence/source-checks'/relative,digest)
 shutil.copytree(DEV/'fragment-evidence',run/'completion-evidence/fragment-evidence');shutil.copytree(DEV/'review-salvage',run/'completion-evidence/recovered-reviews');shutil.copytree(TASK,run/'completion-evidence/supplied-task')
 for name in ('BUDGET-AUTHORIZATION.json','selected-30.json','recovery-4.json'):copy_verified(PARENT/'authorization'/name,run/'authorization'/name)
 copy_verified(PARENT/'effort-support-offline.json',run/'effort-support-offline.json')
 if state.get('compiler_environment'):shutil.copytree(PARENT/state['compiler_environment']['path'],run/state['compiler_environment']['path'])
 frozen={str(f):sha(f) for directory in ('sources','inputs/assets','completion-evidence','authorization') for f in (run/directory).rglob('*') if f.is_file()}
 frozen.update({d['original']:d['sha256'] for d in plan['documents']});frozen.update({str(PARENT/x):sha(PARENT/x) for x in ('state.json','plan.json','binding.json')})
 # Every independent source check is bound to its original page/crop bytes.
 for u in state['source_units'].values():
  for record in u.get('content_adjudications',[]):frozen.update(record['images'])
  for group in u.get('coverage_metadata',{}).get('verified_figure_groups',[]):frozen.update(group.get('source_check',{}).get('files',{}))
 for dec in read_json(DEV/'source-checked-decisions.json'):frozen.update(dec.get('images',{}))
 atomic_json(run/'binding.json',{'code':c.base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':frozen,'config':plan['kimi_config'],'prior_billing':plan['prior_billing']})
 atomic_json(pointer,{'run':str(run),'parent':str(PARENT),'allocation_id':old['allocation_id'],'status':'prepared','new_allocation_usd':0});c.save(run,state);c.verify(run)
 atomic_json(c.POINTER,{'run':str(run),'parent':str(PARENT),'status':'prepared'})
 print('PREPARED',run,'primary requests',len(state['tasks']),'new conversions',2,'missing reviews',len(review_plan)+2);return run


def continue_drained():
 """Preserve all consumed calls at a supported drain boundary; repair labels only."""
 from probe.experiment import verify_seal
 pointer=ROOT/'results/library-completion-current.json';previous=Path(read_json(pointer)['run']);old=read_json(previous/'state.json');oldplan=read_json(previous/'plan.json');binding=read_json(previous/'binding.json')
 if not all(c.base.books.speed.idle(p) for p in (ROOT,ROOT/'runs',previous)):raise ValueError('Writer has not released; no integration')
 if old['status']!='paused' or any(x['status']=='in_progress' for x in old['calls']):raise ValueError('Only a drained paused worker can continue')
 for call in old['calls']:verify_seal(previous/'calls'/call['id'],call['seal'])
 if any(t['status']=='running' for t in old['tasks']):raise ValueError('Unsettled task remains')
 run=ROOT/'runs'/('library-completion-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-labels')
 shutil.copytree(previous,run,ignore=shutil.ignore_patterns('report','pause.json','terminal.log','normal-terminal-checks.json'))
 copy_verified(previous/'normal-terminal-checks.json',run/'historical/parent-normal-terminal-checks.json')
 state=copy.deepcopy(old);plan=copy.deepcopy(oldplan);state.update(status='prepared',diagnostic=None,stage='linked label repair after supported drain',inherited_call_count=len(old['calls']),remote='/home/mdi/projects/pdf-to-latex-comparisons/'+run.name)
 state.pop('inspection',None);state.pop('traceback',None);state.pop('finished_at',None)
 plan.update(parent_run=str(previous),root_parent_run=str(PARENT),runtime_contract={k:state.get(k) for k in c.RUNTIME_FIELDS})
 plan['lineage'].update(root_parent_run=str(PARENT),root_parent_local_calls_consumed=256,drained_parent_run=str(previous),drained_parent_calls_preserved=len(old['calls']),repair_primary_allowance_total=len(old['tasks']),repair_remaining_local_requests=sum(t['status']=='pending' for t in old['tasks']),label_repair='Preserve all source figure labels with complete composites and captions. No new model task/allowance.')
 live={x['source_id']:x for x in read_json(c.reconcile.LIBRARY/'library-first-status.json')['sources']}
 for d in plan['documents']:
  sid=d['source_id'];rec=state['documents'][sid];folder=c.reconcile.LIBRARY/d['library_document']['folder'];current=read_json(folder/'current.json') if (folder/'current.json').exists() else None
  expected=rec.get('publication') if rec.get('selected_new_generation') else rec.get('historical_selection')
  if current!=expected:raise ValueError('Library selection changed outside paused controller')
  rec['historical_selection']=current;d['inherited_latest_attempt']=live[sid].get('latest_attempt')
  if rec.get('delivery') and Path(rec['delivery']).is_relative_to(previous):rec['delivery']=str(run/Path(rec['delivery']).relative_to(previous))
  if sid==KIENITZ:
   d['required_assembly_labels']=['fig:leverage','fig:tpc','fig:simulation','fig:stressed'];rec.update(published=False,selected_new_generation=False,publication_revision=rec.get('publication_revision',1)+1);rec.pop('needs_republication',None)
 for key,u in state['source_units'].items():
  u['assets']={name:str(run/Path(path).relative_to(previous)) if Path(path).is_relative_to(previous) else path for name,path in u['assets'].items()}
  if key.startswith(KIENITZ+'-unit-'):
   fixed=read_json(DEV/'curated'/key/'unit.json');fixed['assets']=u['assets'];state['source_units'][key]=fixed;u=fixed
   folder=run/'versions'/key/'source-checked-labels';folder.mkdir(parents=True,exist_ok=True)
   original_version=state['versions'][key][state['current_versions'][key]];copy_verified(run/original_version['path'],folder/'prior.tex')
   copy_verified(DEV/'curated'/key/'document.tex',folder/'document.tex');text=(folder/'document.tex').read_text();before=(folder/'prior.tex').read_text()
   (folder/'changes.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='before-label-repair.tex',tofile='document.tex')))
   version={'path':str((folder/'document.tex').relative_to(run)),'sha256':sha(folder/'document.tex'),'compilation':{'status':'not_requested'},'parent':original_version,'provenance':{'parent_run':str(previous),'change':'Figure labels move with their preserved figure/caption. No mathematical/source text change.'}}
   state['versions'][key]['source-checked-labels']=version;state['current_versions'][key]='source-checked-labels';version['content_check']=c.content_check(run,state,{'key':key},text)
   atomic_json(folder/'provenance.json',version['provenance'])
  atomic_json(run/'inputs'/key/'unit.json',u)
 state['derived_inputs']={str(run/Path(name).relative_to(previous)) if Path(name).is_absolute() and Path(name).is_relative_to(previous) else name:digest for name,digest in old['derived_inputs'].items()}
 for name in state['derived_inputs']:
  if name.startswith('inputs/') and name.endswith('/unit.json'):state['derived_inputs'][name]=sha(run/name)
 current_texts=[(run/state['versions'][k][state['current_versions'][k]]['path']).read_text() for k in state['documents'][KIENITZ]['units']]
 expected_labels=next(d['required_assembly_labels'] for d in plan['documents'] if d['source_id']==KIENITZ);check=complete.reference_check(current_texts,expected_labels)
 if any(check[k] for k in ('missing_required_labels','undefined_references','duplicate_labels')):raise ValueError('Label qualification failed')
 atomic_json(run/'completion-evidence/label-repair.json',{'parent':str(previous),'source_checked_changes':'Restore existing fig:leverage, fig:simulation and fig:stressed labels with their figures/captions','reference_check':check,'calls_preserved':[{'id':x['id'],'seal':x['seal'],'task':x['parent']} for x in old['calls']],'new_model_tasks':0,'new_allowance':0})
 # Retain the finite task graph byte-for-byte and all old sealed response bytes.
 if sha(run/'task-plan.json')!=sha(previous/'task-plan.json'):raise ValueError('Migration expanded tasks')
 atomic_json(run/'plan.json',plan)
 frozen={str(run/Path(name).relative_to(previous)) if Path(name).is_relative_to(previous) else name:digest for name,digest in binding['files'].items()}
 frozen.update({str(previous/name):sha(previous/name) for name in ('state.json','plan.json','binding.json','task-plan.json')});frozen[str(run/'completion-evidence/label-repair.json')]=sha(run/'completion-evidence/label-repair.json')
 atomic_json(run/'binding.json',{'code':c.base.code_binding(),'plan_sha256':sha(run/'plan.json'),'files':frozen,'config':plan['kimi_config'],'prior_billing':plan['prior_billing']})
 atomic_json(pointer,{'run':str(run),'parent':str(previous),'allocation_id':plan['allocation_id'],'status':'prepared','new_allocation_usd':0});c.save(run,state);c.verify(run);atomic_json(c.POINTER,{'run':str(run),'parent':str(previous),'status':'prepared'})
 print('LINKED',run,'consumed calls preserved',len(state['calls']),'remaining',sum(t['status']=='pending' for t in state['tasks']));return run

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['curate','prepare','continue-drained']);args=parser.parse_args();{'curate':curate,'prepare':prepare,'continue-drained':continue_drained}[args.action]()
