#!/usr/bin/env python3
"""Offline image/draft preparation; use existing MinerU environment for Pillow only."""
from pathlib import Path
import sys,json,copy,shutil,base64
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from probe.common import read_json,atomic_json,sha,fingerprint
from probe import focused_recovery as focused,image_review as vision
# Read existing Pillow only; no installation or environment modification.
sys.path.append(str(ROOT/'.venv-mineru/lib/python3.12/site-packages'))
from PIL import Image
PARENT=ROOT/'runs/extraction-comparison-20261105T185601Z-layout'
CROPS={'cf':[(4,[.13,.44,.89,.97]),(5,[.13,.15,.89,.63]),(5,[.13,.63,.89,.90]),(6,[.12,.08,.90,.30])], 'ig':[(3,[.38,.84,.88,.91]),(4,[.10,.08,.90,.215])]}

def prepare():
 run=Path(read_json(ROOT/'results/glm-image-review-current.json')['run'])
 if (run/'plan-draft.json').exists():raise ValueError('Already prepared; do not overwrite frozen evidence')
 sourceplan=read_json(PARENT/'plan.json');sources={};bodies={};plan={'status':'prepared_not_frozen','maximum_work_requests':8,'authorized_ceiling':10,'maximum_readiness_requests':3,'planned_readiness_requests':0,'image_limits':{'image_tokens':2048,'request_image_tokens':16384,'max_images':50},'C':{'included':False,'reason':'Source inspection shows dense assigned CF formulae fully covered by native-resolution detail crops; control equations remain legible. First evaluate A/B without a serving restart. Higher resolution is a later decision, not an automatic stage.'},'stages':[['cf-A','cf-B','ig-A','ig-B'],['cf-B-parallel','ig-B-parallel'],['cf-B-high','ig-B-high']],'tasks':[]}
 for label,call,index in [('cf','call-010',0),('ig','call-009',1)]:
  baseline=read_json(PARENT/'calls'/call/'request.json');payload=json.loads(baseline['messages'][0]['content'].split('\n',1)[1]);assert baseline['reasoning_effort']=='max' and baseline['max_tokens']==131072
  assert focused.digest(payload['draft'])==payload['base_sha256']
  textonly=focused.critic_request(payload['draft'],payload['source_output_scope'],payload['secondary'],payload['context_only']);assert textonly==baseline
  assignment=sourceplan['downstream'][index];doc=next(d for d in sourceplan['documents'] if d['source_id']==assignment['source_id']);assert sha(doc['original'])==doc['sha256']
  folder=run/'inputs'/label;folder.mkdir(parents=True);(folder/'draft.tex').write_text(payload['draft']);atomic_json(folder/'payload.json',payload);atomic_json(folder/'historical-request.json',baseline)
  full=[];crops=[]
  for n in assignment['physical_pages']:
   original=PARENT/'sources'/doc['source_id']/f'page-{n:03}.png';target=folder/f'page-{n:03}.png';shutil.copyfile(original,target)
   with Image.open(target) as im:dimensions=list(im.size)
   full.append({'path':str(target.relative_to(run)),'sha256':sha(target),'dimensions':dimensions,'physical_page':n,'crop':None,'source_sha256':doc['sha256'],'source_id':doc['source_id'],'original_pdf':doc['original'],'source_image_sha256':sha(original),'resizing':'none before server'})
  for i,(n,box) in enumerate(CROPS[label]):
   source=folder/f'page-{n:03}.png'
   with Image.open(source) as im:
    w,h=im.size;pixels=[int(w*box[0]),int(h*box[1]),int(w*box[2]),int(h*box[3])];crop=im.crop(pixels);target=folder/f'crop-{i+1}.png';crop.save(target);dimensions=list(crop.size)
   crops.append({'path':str(target.relative_to(run)),'sha256':sha(target),'dimensions':dimensions,'physical_page':n,'crop':pixels,'source_sha256':doc['sha256'],'source_id':doc['source_id'],'original_pdf':doc['original'],'source_image_sha256':sha(source),'resizing':'none; exact crop from original rendered source page'})
  sources[label]={'source_id':doc['source_id'],'filename':doc['filename'],'sha256':doc['sha256'],'scope':assignment,'draft_sha256':payload['base_sha256'],'historical_call':str(PARENT/'calls'/call),'historical_request_sha256':sha(PARENT/'calls'/call/'request.json'),'text_only_reconstruction_exact':True,'historical_comparison':'Observational: exact draft/scope/text match, but new instructions explain image evidence and evidence fields. Converter annotations are retained and may influence reviewer.'}
  for variant,records in [('A',full),('B',full+crops)]:
   ident=label+'-'+variant;body=focused.critic_request(payload['draft'],payload['source_output_scope'],payload['secondary'],payload['context_only'],images=vision.image_parts(records,run));budget=vision.image_budget(body,1048576)
   for record in records:record['expected_geometry']=vision.geometry(*record['dimensions'])
   atomic_json(folder/(variant+'-images.json'),records);atomic_json(run/'requests'/(ident+'.json'),body);bodies[ident]=body
   plan['tasks'].append({'id':ident,'source':label,'variant':variant,'effort':'max','request_sha256':fingerprint(body),'draft_sha256':payload['base_sha256'],'images_manifest':str((folder/(variant+'-images.json')).relative_to(run)),'images_manifest_sha256':sha(folder/(variant+'-images.json')),'budget':budget})
 for suffix,effort in [('parallel','max'),('high','high')]:
  for label in ['cf','ig']:
   ident=label+'-B-'+suffix;body=copy.deepcopy(bodies[label+'-B']);body['reasoning_effort']=effort;atomic_json(run/'requests'/(ident+'.json'),body);original=next(t for t in plan['tasks'] if t['id']==label+'-B');plan['tasks'].append(dict(original,id=ident,effort=effort,request_sha256=fingerprint(body)))
 plan['sources']=sources;atomic_json(run/'plan-draft.json',plan)
 for name in ['cf','ig']:
  (run/'evaluation').mkdir(exist_ok=True)
 atomic_json(run/'evaluation/reading-sheet.json',{'held_out_of_requests':True,'status':'Direct image readings checked by Codex; no prior reviewer verdict is an answer key','cf':[{'location':'physical4/printed498 Eq27b','printed':'Gamma(c+n) replaced by Gamma(b+n)','draft':'Gamma(b+n)','disposition':'faithful; historical additional-source-readings.json said Gamma(d+n), which is wrong. Historical file preserved. Any proposed d is a mathematical proposal, not a transcription repair.'},{'location':'physical4 Eq25a/25b/27a/27b','printed':'Odd (-1) and (-) factors are visibly printed','disposition':'Do not penalise faithful retention as OCR error; mathematical validity is a separate question.'},{'location':'physical5 Case17 Eq33','printed':'denominator Gamma(b)*(2+lambda*a^mu)^b; sum a^(n*mu)*x^(n*mu), Gamma(1+lambda+n*mu); a,b,lambda>0,mu>=-1,tau>=0','disposition':'Unchanged-formula/condition control.'},{'location':'physical5 Eq34','printed':'-8*a^mu lies inside denominator in final exponential fraction','disposition':'Check correct preservation; no known-error hint supplied to reviewer.'}], 'ig':[{'location':'physical3 Eqs1–3','printed':'b=f*m; beta_F=F*m; d ln F/d ln f=1/R','disposition':'Unchanged controls; three numbers retained.'},{'location':'physical3 footnote2','printed':'Large transactions with significant impact on the market invalidate the stated interpretation','disposition':'Assumption/footnote control.'}], 'limits':'Not a full mathematical proof. Significant additional findings require source adjudication; no automatic numeric score from proposal count.'})
 print(run);print([(t['id'],t['budget']['request_bytes'],t['budget']['image_tokens']) for t in plan['tasks']])
if __name__=='__main__':prepare()
