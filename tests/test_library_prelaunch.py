"""Targeted planner/accounting and saved-result bundle regressions. No inference."""
import copy,hashlib,json,shutil,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from probe import library_first as policy,library_report
from probe.common import read_json,atomic_json,sha
from scripts import library_pipeline as c
import test_library_pipeline as fixtures

def block(ident,page,text,kind='text',**extra):
 return {'id':ident,'kind':kind,'tex':text,'page':{'original_physical_page':page},'assets':[],**extra}

class StructuralPlanning(unittest.TestCase):
 def test_five_page_section_splits_at_complete_paragraphs_without_loss(self):
  data=[block('heading',1,r'\section*{1. Long section}','paragraph_title')]+[block('p'+str(n),n,'A complete independent argument on this page ends here.') for n in range(1,6)]
  plan=policy.structural_units(data);self.assertEqual(len(plan),2);self.assertTrue(all(x['disposition']=='included' for x in plan))
  self.assertEqual([b for x in plan for b in x['native_blocks']],data);self.assertEqual(plan[1]['physical_pages'],[5])
 def test_statement_and_cross_page_proof_cannot_split(self):
  data=[block('intro',1,'Introductory context ends.'),block('theorem',2,'Theorem 1. Assume x is positive. Then x squared is positive.','paragraph_title'),block('proof',2,r'\begin{proof}We first use the stated assumption.'),block('equation',3,r'\[x^2>0\]','equation'),block('end',4,r'This completes the argument.\end{proof}'),block('next',5,r'\section*{2. Independent results}','paragraph_title'),block('tail',5,'Other conclusions follow.')]
  plan=policy.structural_units(data,maximum_pages=3)
  owner=next(x for x in plan if 'theorem' in x['blocks']);self.assertTrue({'theorem','proof','equation','end'}<=set(owner['blocks']));self.assertEqual(owner['disposition'],'included')
  self.assertNotIn('next',owner['blocks'])
 def test_oversized_proof_outstanding_but_safe_neighbors_proceed(self):
  data=[block('intro',1,'A safe introduction.'),block('theorem',2,'Theorem 1. The stated result holds.','paragraph_title'),block('proof',2,'Proof. Start the connected argument.')]
  data += [block('step'+str(n),n,'The next connected proof step follows.') for n in range(3,7)]
  data += [block('qed',6,'The result follows. QED.'),block('heading',7,r'\section*{2. Other material}','paragraph_title'),block('tail',7,'An independent argument concludes.')]
  plan=policy.structural_units(data);self.assertEqual([x['disposition'] for x in plan],['included','outstanding','included'])
  self.assertEqual(plan[1]['physical_pages'],[2,3,4,5,6]);self.assertEqual([b for x in plan for b in x['blocks']],[b['id'] for b in data]);self.assertEqual(len({b for x in plan for b in x['blocks']}),len(data))
 def test_equations_conditions_and_figure_caption_are_atomic(self):
  data=[block('intro',1,'We define the following quantity:'),block('eq1',1,r'\begin{align}x &= 1 +','equation'),block('eq2',2,r'y\end{align}','equation'),block('where',2,'where y is strictly positive.'),block('figure',3,r'\includegraphics{assets/plot.png}','image'),block('caption',3,'Figure 1: The source plot.','caption'),block('end',4,'Independent material ends.')]
  plan=policy.structural_units(data,maximum_pages=2)
  eq=next(x for x in plan if 'eq1' in x['blocks']);self.assertTrue({'intro','eq1','eq2','where'}<=set(eq['blocks']))
  fig=next(x for x in plan if 'figure' in x['blocks']);self.assertIn('caption',fig['blocks'])
  self.assertEqual([b for x in plan for b in x['native_blocks']],data)
 def test_single_oversized_native_region_not_cut_or_discarded(self):
  data=[block('one',1,'Unsplit source paragraph '+('x'*25000)+'.'),block('two',2,'A separate complete sentence.')]
  rows=policy.structural_units(data);self.assertEqual(rows[0]['disposition'],'outstanding');self.assertEqual(rows[0]['text'],data[0]['tex']);self.assertEqual(rows[1]['disposition'],'included')
 def test_formatted_proof_ending_allows_safe_following_paragraph(self):
  data=[block('t',1,'<b>Theorem 1.</b> The result holds.'),block('p',1,'**Proof.** The argument begins.'),block('e',2,r'The argument ends.\qed'),block('tail',3,'An independent application follows.')]
  rows=policy.structural_units(data,maximum_pages=2);self.assertEqual(rows[0]['blocks'],['t','p','e']);self.assertEqual(rows[1]['blocks'],['tail']);self.assertTrue(all(x['disposition']=='included' for x in rows))
 def test_box_operator_inside_equation_is_not_end_of_proof(self):
  data=[block('t',1,'Theorem 1. A wave equation result.'),block('p',1,'Proof. Use the wave operator.'),block('eq',2,r'\[\Box\phi=0\]','equation'),block('more',3,'An essential remaining proof step.'),block('end',4,'Finally the claim follows. QED.')]
  rows=policy.structural_units(data,maximum_pages=2);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['disposition'],'outstanding');self.assertEqual(rows[0]['blocks'],[b['id'] for b in data])

class Integration(unittest.TestCase):
 def setUp(self):
  self.h=fixtures.Pipeline(methodName='runTest');self.h.setUp();self.addCleanup(self.h.doCleanups)
 def test_outstanding_accounting_reaches_tasks_context_and_partial_delivery(self):
  h=self.h;plan=read_json(h.run/'plan.json');d=plan['documents'][0];first=d['pages'][0];d['physical_pages']=list(range(1,8));d['pages']=[]
  for n in range(1,8):
   target=h.run/'sources'/h.sid/f'page-{n:03}.png'
   if n!=1:shutil.copyfile(h.run/first['path'],target)
   d['pages'].append(dict(first,physical_pdf_page=n,path=str(target.relative_to(h.run)),image=str(target.relative_to(h.run))))
   texts={1:[('title','1. Introduction'),('text','A complete introduction.')],2:[('title','Theorem 1. A connected result.'),('text','Proof. Start the proof.')],6:[('text','The proof concludes. QED.')],7:[('title','2. Safe remainder'),('text','Independent material concludes.')]}.get(n,[('text','Continue the proof on this page.')])
   atomic_json(h.run/'arms/mineru_pro/pages'/f'{h.sid}-p{n}/native.json',[{'type':kind,'content':text,'bbox':[0,0,100,100]} for kind,text in texts])
  plan['workloads']['mineru_pro']=[[h.sid,n] for n in range(1,8)];atomic_json(h.run/'plan.json',plan)
  h.s.update(inputs_prepared=False,tasks=[],source_units={},derived_inputs={});h.s['documents'][h.sid]['units']=[];h.s['documents'][h.sid].pop('planning_done',None);h.s['extraction']['mineru_pro']['pages']={f'{h.sid}-p{n}':{'status':'completed'} for n in range(1,8)}
  c.plan_units(h.run,h.s);rec=h.s['documents'][h.sid];self.assertEqual(len(rec['units']),2);self.assertEqual(len(rec['outstanding_scopes']),1);self.assertEqual(len(h.s['tasks']),4)
  second=h.s['source_units'][rec['units'][1]];self.assertIn('Proof. Start the proof.',second['context']);self.assertNotIn('Proof. Start the proof.',second['text'])
  account=read_json(h.run/'source-plans'/f'{h.sid}.json');self.assertEqual([bid for scope in account['scopes'] for bid in scope['blocks']],account['source_regions'])
  # Every safe unit succeeds; the outstanding proof MUST still block completion.
  for key in rec['units']:
   path=h.run/'versions'/key/'document.tex';path.parent.mkdir(parents=True);path.write_text(fixtures.DOC);pdf=path.parent/'document.pdf';shutil.copyfile(c.ROOT/'fixtures/known-math.pdf',pdf)
   h.s['versions'][key]={'convert':{'path':str(path.relative_to(h.run)),'sha256':sha(path),'compilation':{'status':'passed','attempts':[{'path':str(path.parent.relative_to(h.run))}]}}};h.s['current_versions'][key]='convert'
  for t in h.s['tasks']:t.update(status='review_completed' if t['phase']=='critic' else 'conversion_completed',review_complete_attested=True)
  with patch.object(c.followup_lifecycle,'coverage',return_value={'coverage_status':'requires_source_review'}):c.publish_settled(h.run,h.s,h.sid)
  result=read_json(h.run/'deliveries'/h.sid/'library-status.json');self.assertEqual(result['status'],'partial_source');self.assertEqual(result['conversion'],'incomplete');self.assertFalse(result['model_review']['reviewed_full_scope_attested']);self.assertFalse(h.s['documents'][h.sid]['selected_new_generation'])
  self.assertTrue(result['outstanding_scopes']);self.assertFalse((h.library/'fixture/current.json').exists())
 def test_bundle_contains_results_assets_diagnostics_and_flagged_originals(self):
  h=self.h;u=h.s['source_units'][h.key];asset=h.run/'inputs/assets/plot.png';asset.parent.mkdir(parents=True);shutil.copyfile(c.ROOT/'fixtures/vision/case-01.png',asset);u['assets']['assets/plot.png']=str(asset)
  # Mock output omits a required heading, producing a real coverage flag.
  u['native_blocks'][0]['tex']=r'\section*{Required missing heading}'
  atomic_json(h.run/'inputs'/h.key/'unit.json',u);h.s['derived_inputs']['inputs/'+h.key+'/unit.json']=sha(h.run/'inputs'/h.key/'unit.json')
  c.save(h.run,h.s)
  document=fixtures.DOC.replace(r'\end{document}',r'\includegraphics{assets/plot.png}\end{document}')
  plan=read_json(h.run/'plan.json');plan['settings']['compile_pdf']=True;atomic_json(h.run/'plan.json',plan);binding=read_json(h.run/'binding.json');binding['plan_sha256']=sha(h.run/'plan.json');atomic_json(h.run/'binding.json',binding)
  with patch.object(fixtures,'DOC',document):h.coordinate()
  hidden=h.run/'calls/call-001/reasoning.txt';hidden.write_text('LONG TRACE DO NOT EXPORT');(h.run/'auth.json').write_text('{"secret":"must not be copied"}')
  result=library_report.inspection(h.run,h.s,h.root/'bundles')
  with zipfile.ZipFile(result['path']) as z:
   names=set(z.namelist());prefix='deliveries/'+h.sid+'/parts/'+h.key+'/'
   for name in [prefix+'document.tex',prefix+'assets/plot.png','deliveries/'+h.sid+'/reading.pdf','calls/call-002/findings.json','calls/call-002/changes.diff','PAPER-SUMMARY.json','TIMINGS.csv','OMITTED.json','sources/'+h.sid+'/page-001.png']:self.assertIn(name,names)
   self.assertTrue(any(n.endswith('console.log') for n in names));self.assertFalse(any('reasoning.txt' in n or n.endswith('auth.json') or n.endswith('request.json') for n in names))
   omitted=json.loads(z.read('OMITTED.json'));self.assertIn('auth.json',[x['path'] for x in omitted]);self.assertIn('calls/call-001/reasoning.txt',[x['path'] for x in omitted])
   manifest=json.loads(z.read('FILE-HASHES.json'));self.assertEqual(names,{x['path'] for x in manifest}|{'FILE-HASHES.json'})
   for row in manifest:self.assertEqual(hashlib.sha256(z.read(row['path'])).hexdigest(),row['sha256'])
  previous=Path(result['path']).read_bytes();again=library_report.inspection(h.run,h.s,h.root/'bundles');self.assertNotEqual(result['path'],again['path']);self.assertEqual(Path(result['path']).read_bytes(),previous)
 def test_refresh_never_started_preparation_preserves_inputs_and_blocks_calls(self):
  h=self.h;plan=read_json(h.run/'plan.json');plan['documents'][0]['pages'][0]['image']=plan['documents'][0]['pages'][0]['path'];atomic_json(h.run/'plan.json',plan)
  h.s.update(inputs_prepared=False,source_units={},tasks=[],calls=[],derived_inputs={});h.s.pop('task_plan_sha256',None);h.s['documents'][h.sid]['units']=[];h.s['documents'][h.sid].pop('planning_done',None);c.save(h.run,h.s)
  binding=read_json(h.run/'binding.json');binding['plan_sha256']=sha(h.run/'plan.json');atomic_json(h.run/'binding.json',binding)
  root=h.root/'project';(root/'runs').mkdir(parents=True);pointer=root/'current.json';atomic_json(pointer,{'run':str(h.run)})
  oldsha=sha(h.run/'plan.json')
  with patch.object(c,'ROOT',root),patch.object(c,'POINTER',pointer):
   new=c.refresh_prepared(h.run);self.assertEqual(read_json(new/'plan.json')['settings'],plan['settings']);self.assertEqual(sha(h.run/'plan.json'),oldsha);self.assertEqual(read_json(new/'state.json')['calls'],[])
   p=read_json(h.run/'state.json');p['calls']=[{'id':'consumed'}];atomic_json(h.run/'state.json',p)
   with self.assertRaises(c.runtime.Fatal):c.refresh_prepared(h.run)

if __name__=='__main__':unittest.main()
