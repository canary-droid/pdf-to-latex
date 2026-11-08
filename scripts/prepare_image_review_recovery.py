#!/usr/bin/env python3
"""Offline finite scope/image preparation. No OCR, model call or service operation."""
import copy,datetime,difflib,json,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import image_review_recovery as c
from probe.common import read_json,atomic_json,sha,fingerprint
from probe import focused_recovery as edits,image_review as vision,chapter_editorial as editorial
sys.path.append(str(ROOT/'.venv-mineru/lib/python3.12/site-packages'))
from PIL import Image

def copy_edition(source,target):
 target.mkdir(parents=True,exist_ok=True)
 for p in source.rglob('*'):
  if not p.is_file() or 'build' in p.relative_to(source).parts:continue
  dest=target/p.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 record=source/'build/compilation.json'
 if record.exists():atomic_json(target/'parent-build-provenance.json',{'path':str(record),'sha256':sha(record),'record':read_json(record),'interpretation':'Reused successful build, not a fresh compilation'})

def prepare(run):
 if run.exists():raise ValueError('Preparation already exists; preserve immutable evidence')
 if not all(c.base.books.speed.idle(p) for p in [ROOT,ROOT/'runs']):raise ValueError('Existing writer; prepare independently first')
 run.mkdir(parents=True);old=read_json(c.IMAGES/'state.json')
 for label,path in c.EDITIONS.items():copy_edition(path,run/'baseline-editions'/label)
 shutil.copytree(c.IMAGES/old['compiler_environment']['path'],run/old['compiler_environment']['path'])
 shutil.copyfile(c.IMAGES/'effort-support-offline.json',run/'effort-support-offline.json')
 atomic_json(run/'repair-state.json',{**{k:old[k] for k in ['compiler_environment','concurrency_policy','chapter_contract','execution_limits','timing_policy']},'disable_dependency_downloads':True})
 parent=read_json(c.PARENT/'plan.json');state=read_json(c.PARENT/'state.json');sources={};units=[];ownership={}
 for source,sid in c.SID.items():
  document=next(d for d in parent['documents'] if d['source_id']==sid);assert sha(document['original'])==document['sha256'];sources[source]=document
  key=sid+'-whole-3';call='002' if source=='cf' else '009';original=c.PARENT/'versions'/key/f'convert-call-{call}-annotated/document.tex';assert sha(original)==c.EXPECTED[source]
  chosen=run/'baseline-editions'/source/(key+('-convert-call-002-annotated.tex' if source=='cf' else '-working.tex'))
  draft=chosen.read_text();prior=original.read_text()
  assert draft==prior if source=='cf' else draft==prior.replace('\\section*{Editorial corrections and unresolved issues}','% PDF2TEX_GENERATED_NOTES_BEGIN\n\\section*{Editorial corrections and unresolved issues}')
  native=read_json(c.PARENT/'inputs'/key/'native.json');blocks=native['blocks'];definitions=[u for u in c.UNITS if u[1]==source]
  starts=[next(i for i,b in enumerate(blocks) if b['id']==sid+'-'+u[2]) for u in definitions]+[len(blocks)]
  cut=[draft.index(u[3]) for u in definitions];note=draft.index(r'\section*{Editorial corrections and unresolved issues}');end=draft.rfind(r'\clearpage',0,note);cut.append(end)
  assert starts[0]==0 and end>cut[-2]
  ownership[source]={'expected_blocks':[b['id'] for b in blocks],'source_sha256':document['sha256'],'historical_draft':str(original),'historical_sha256':sha(original),
   'chosen_version':str(chosen.relative_to(run)),'chosen_sha256':sha(chosen),'historical_difference':'none' if source=='cf' else 'Only explicit generated-note boundary marker; no mathematical/prose change',
   'draft_source_range':[cut[0],end],'notes_preserved_outside_review_scope':draft[end:],'preamble_context':draft[:cut[0]]}
  oldrequest=read_json(c.PARENT/'calls'/('call-004' if source=='cf' else 'call-010')/'request.json');payload=json.loads(oldrequest['messages'][0]['content'].split('\n',1)[1])
  secondary=read_json(c.PARENT/'sources'/sid/'secondary-assessment.json')
  for i,(uid,_,_,_,title,crops) in enumerate(definitions):
   selected=blocks[starts[i]:starts[i+1]];pages=sorted({b['page']['original_physical_page'] for b in selected});folder=run/'inputs'/uid;folder.mkdir(parents=True)
   (folder/'draft.tex').write_text(draft);atomic_json(folder/'native.json',dict(native,blocks=selected))
   (folder/'source.txt').write_text('\n\n'.join(b['tex'] for b in selected))
   context=payload['context_only']+'\n\nEARLIER MATERIAL IN THIS SAME SAVED UNIT, CONTEXT ONLY:\n'+'\n\n'.join(b['tex'] for b in blocks[:starts[i]])
   # Complete filtered secondary pages, never raw garbled CF native text.
   secondary_text='' if source=='cf' else '\n\n'.join('Physical PDF page '+str(p['physical_pdf_page'])+'\n'+p['text'] for p in secondary['pages'] if p['physical_pdf_page'] in pages)
   (folder/'context.txt').write_text(context);(folder/'secondary.txt').write_text(secondary_text)
   records=[]
   for page in pages:
    src=c.PARENT/'sources'/sid/f'page-{page:03}.png';dst=run/'sources'/source/f'page-{page:03}.png';dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists():shutil.copyfile(src,dst)
    with Image.open(dst) as im:dimensions=list(im.size)
    records.append({'path':str(dst.relative_to(run)),'sha256':sha(dst),'dimensions':dimensions,'physical_page':page,'printed_page':page+(494 if source=='cf' else 336),'crop':None,'source_id':sid,'source_sha256':document['sha256'],'original_pdf':document['original'],'source_image_sha256':sha(src),'resizing':'Saved original-page rendering, unchanged; server fitting separately recorded'})
   for number,(page,box) in enumerate(crops):
    assert page in pages
    source_image=run/'sources'/source/f'page-{page:03}.png';dst=folder/f'crop-{number+1}.png'
    with Image.open(source_image) as im:
     w,h=im.size;pixels=[int(w*box[0]),int(h*box[1]),int(w*box[2]),int(h*box[3])];crop=im.crop(pixels);crop.save(dst);dimensions=list(crop.size)
    record=copy.deepcopy(next(r for r in records if r['physical_page']==page and r['crop'] is None));record.update(path=str(dst.relative_to(run)),sha256=sha(dst),dimensions=dimensions,crop=pixels,resizing='Exact source crop, no preparer rescaling');records.append(record)
   assert len(records)<=8
   for r in records:r['expected_fit']=vision.geometry(*r['dimensions']);r['effective_cap']=2048
   atomic_json(folder/'images.json',records)
   units.append({'id':uid,'source':source,'title':title,'physical_pages':pages,'blocks':[b['id'] for b in selected],'ranges':[[cut[i],cut[i+1]]],
    'source_sha256':document['sha256'],'draft_sha256':edits.digest(draft),'draft_path':str((folder/'draft.tex').relative_to(run)),
    'images_manifest':str((folder/'images.json').relative_to(run)),'baseline_build':{'path':str(c.PARENT/state['versions'][key][f'convert-call-{call}-annotated']['compilation']['attempts'][0]['path']),'record':state['versions'][key][f'convert-call-{call}-annotated']['compilation'],'selected_edition_build':str(c.EDITIONS[source]/'build/compilation.json'),'status':'passed inherited; marker-only Spectral change compiled in repaired assembly'},
    'scope_rule':'Each native region owned exactly once. Shared pages/context are not additional review targets. Complete hypotheses, equations, prose, table/figures, footnotes and references retained.'})
  edits.validate_partition([u for u in units if u['source']==source],ownership[source]['expected_blocks'])
 atomic_json(run/'scope-ownership.json',ownership)
 # A small source-checked positive error control, distinct from delivered drafts.
 cf=next(u for u in units if u['id']=='cf-1');draft=(run/cf['draft_path']).read_text();a,b=cf['ranges'][0]
 pre=draft[:draft.index(r'\begin{document}')+len(r'\begin{document}')];clean=pre+'\n'+draft[a:b]+'\n\\end{document}\n'
 good=r'e ^ {- \tau x ^ {2}}';bad=r'e ^ {+ \tau x ^ {2}}';assert clean.count(good)==1
 control=clean.replace(good,bad,1);folder=run/'inputs/control-cf';folder.mkdir();(folder/'unmutated.tex').write_text(clean);(folder/'draft.tex').write_text(control)
 for name in ['source.txt','secondary.txt','context.txt']:shutil.copyfile(run/'inputs/cf-1'/name,folder/name)
 control_unit=dict(cf,id='control-cf',title='Case 19 and complete continuation',draft_path='inputs/control-cf/draft.tex',draft_sha256=edits.digest(control),ranges=[[len(pre),control.index(r'\end{document}')]],kind='control',baseline_build={'status':'test-only mutation; compile before dispatch, never selected into an edition'})
 atomic_json(run/'evaluation/answer-key.json',{'checked_by':'Codex direct original-image inspection plus stated local reasoning; not independent human certification',
  'controlled_example':{'source':sources['cf']['sha256'],'physical_page':6,'printed_page':500,'equation':'37','printed_anchor':good,'mutated_anchor':bad,
   'mutation':'One sign only, in a test-only copy. Source clearly prints negative tau x squared; positive sign grows exponentially for tau>0 and cannot be a density with the rational denominator.',
   'unmutated_sha256':edits.digest(clean),'mutated_sha256':edits.digest(control),'unchanged_anchors':[r'a, b, c > 0; \tau \geq 0',r'e ^ {- t ^ {2} / 4 u}',r'\quad b ^ {2} \neq 4 a c.'],
   'annotations_removed':'Generated note appendix not in evaluation copy; no source-body change besides the recorded sign. Normal recovery draft/hash remain intact.',
   'limitations':'One artificial error is a detection sanity check, not a natural error-rate estimate. Other odd printed formulae remain unchanged; unanticipated findings need adjudication.'},
  'unchanged_source_checks':[{'unit':'cf-1','page':6,'print':'Eq37 negative tau exponent; positive a,b,c, nonnegative tau; Eq38 e^(-t^2/(4u)); discriminant b^2 !=4ac','status':'directly source-image checked'},
   {'unit':'spectral-2','page':26,'print':'lambda_n=kappa n, xi=sqrt(kappa)(x-theta)/sigma, N_n^2=sigma sqrt(kappa)/(2^(n+1) n! sqrt(pi))','status':'directly source-image checked; unchanged draft control'},
   {'unit':'historical CF','page':4,'print':'Eq27b Gamma(b+n), not Gamma(d+n)','status':'Previous direct source check retained, not an evaluation target or a hint in new requests'}],
  'comparison_selection':'cf-1 dense characteristic function; spectral-2 OU scale/normalisation with ordinary prose. Chosen before outcomes. No sufficiently independently established natural draft error in these two units, therefore one separated artificial control.'})
 atomic_json(run/'evaluation/mutation.json',{'source_draft':cf['draft_path'],'before_sha256':edits.digest(clean),'after_sha256':edits.digest(control),'old':good,'new':bad,'location':control.index(bad),'test_only':True,'never_deliver':True})
 shutil.copyfile(c.IMAGES/'evaluation/spectral-eight-edits.json',run/'evaluation/spectral-eight-edits-preserved.json')
 # Offline renderer repair: the historical proposal used TeX-escaped dollars in
 # plain note prose. Explicitly decode only those recorded escapes, then render
 # plain text once. Never transform general mathematical patches.
 dest=run/'annotation-repair';dest.mkdir();draft=(c.IMAGES/'reviews/cf-A/original.tex').read_text();proposal=read_json(c.IMAGES/'proposals/cf-A.txt');raw=copy.deepcopy(proposal)
 for f in proposal['findings']:
  if f.get('status')=='edit' and f.get('printed_source'):
   f['replacement_format']='plain_annotation';f['new']=f['new'].replace(r'\$','$')
 revised,log=vision.apply_review(draft,proposal)
 marker=draft.index(r'\section*{Editorial corrections and unresolved issues}');assert draft[:marker]==revised[:marker]
 (dest/'original.tex').write_text(draft);(dest/'failed.tex').write_text((c.IMAGES/'reviews/cf-A/reviewed.tex').read_text());(dest/'repaired.tex').write_text(revised)
 atomic_json(dest/'raw-proposal.json',raw);atomic_json(dest/'typed-replay.json',proposal);atomic_json(dest/'application.json',log)
 (dest/'changes.diff').write_text(''.join(difflib.unified_diff(draft.splitlines(True),revised.splitlines(True),fromfile='compiling-original',tofile='safe-annotation-derivative')))
 atomic_json(dest/'provenance.json',{'historical':str(c.IMAGES/'reviews/cf-A'),'mathematical_body_sha256':edits.digest(draft[:marker]),'source_equations_unchanged':True,'historical_escapes_decoded':['backslash-dollar in two explicitly identified plain note replacements'],'claims':'Original model speculation remains attributed, not newly certified by renderer repair'})
 # Pair order alternates across the recovery cases. No concurrent paired call.
 stages=[['cf-1-high','cf-1-max'],['spectral-2-max','spectral-2-high'],['control-cf-high','control-cf-max'],[u['id']+'-max' for u in units if u['id'] not in ['cf-1','spectral-2']]]
 tasks=[]
 for stage in stages:
  for task_id in stage:
   uid,effort=task_id.rsplit('-',1);unit=control_unit if uid=='control-cf' else next(u for u in units if u['id']==uid);folder=run/'inputs'/uid;draft=(run/unit['draft_path']).read_text()
   body=edits.critic_request(draft,(folder/'source.txt').read_text(),(folder/'secondary.txt').read_text(),(folder/'context.txt').read_text(),effort=effort,ranges=unit['ranges'],images=vision.image_parts(read_json(run/unit['images_manifest']),run))
   budget=vision.image_budget(body,1048576);atomic_json(run/'requests'/(task_id+'.json'),body)
   tasks.append(dict(unit,id=task_id,unit=uid,kind=unit.get('kind','recovery'),effort=effort,max_tokens=131072,request_sha256=fingerprint(body),budget=budget))
 plan={'status':'prepared_not_frozen','parent':str(c.PARENT),'image_parent':str(c.IMAGES),'maximum_model_requests':12,'maximum_work_requests':12,'authorized_ceiling':14,'maximum_readiness_requests':1,'planned_readiness_requests':0,
  'image_limits':{'image_tokens':2048,'request_image_tokens':16384,'max_images':50},'units':units,'sources':sources,'source_ownership':ownership,'tasks':tasks,'stages':stages,
  'stage_specs':{str(i):{'title':title,'concurrency':1 if i<3 else 2} for i,title in enumerate(['CF matched High then Max','Spectral matched Max then High','Artificial control High then Max','Other coherent recovery units, maximum two'])},
  'allowance_derivation':'8 coherent Max recovery units +2 High comparators +2 requests for one artificial positive control =12; no retries, recursive splits, conversion, OCR, syntax-model repair, production continuation or service changes',
  'historical_consumption':{'failed_reviews':[{'call':str(c.PARENT/'calls/call-004'),'reasoning_tokens':131072},{'call':str(c.PARENT/'calls/call-010'),'reasoning_tokens':131072}],'completed_image_reviews':8,'reset':False},
  'annotation_policy':'Typed plain annotation renderer; exact mathematical edits unchanged; compilation before candidate selection',
  'limitations':'Eight findings maximum per unit; any further findings must be recorded unresolved. Images clarify print but do not certify mathematical correctness. Context annotations not supplied as expected answers.'}
 c.validate_plan(plan);atomic_json(run/'plan-draft.json',plan);atomic_json(c.POINTER,{'run':str(run),'status':'prepared_not_frozen','scope':'finite image review recovery only; other pointers unchanged'})
 print(run);print('Prepared12 requests; no model calls. Annotation/control compilation and CPU image qualification still required.')

if __name__=='__main__':
 run=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'runs'/('image-review-recovery-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
 prepare(run)
