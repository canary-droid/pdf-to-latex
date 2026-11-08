import copy,io,json,tarfile,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from probe import author_source as a,library_first as policy,library_fallbacks as fallback
from probe.common import atomic_json,read_json,sha
from probe.experiment import seal
from scripts import library_pipeline as c,wiki_source_intake as intake
import test_library_pipeline as fixtures
DOC=fixtures.DOC

class StaticSource(unittest.TestCase):
 def test_safe_archive_retains_every_file_without_execution(self):
  data=io.BytesIO()
  with zipfile.ZipFile(data,'w') as z:
   for name,value in {'main.tex':DOC,'assets/a.eps':'image','scripts/build.sh':'exit 99','agents/config.txt':'kept'}.items():z.writestr(name,value)
  with patch('subprocess.run',side_effect=AssertionError('No source execution')):files=a.unpack(data.getvalue())
  self.assertEqual(set(files),{'main.tex','assets/a.eps','scripts/build.sh','agents/config.txt'})
 def test_traversal_links_and_non_sources_rejected(self):
  for name in ('../evil','/absolute','C:/windows'):
   data=io.BytesIO()
   with zipfile.ZipFile(data,'w') as z:z.writestr(name,'x')
   with self.assertRaises(ValueError):a.unpack(data.getvalue())
  for data in (b'%PDF-1.7',b'<html>failed',b'bad response'):
   with self.assertRaises(ValueError):a.unpack(data)
 def test_nested_text_macros_bib_figures_and_comments(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'figures').mkdir()
   (root/'main.tex').write_text(r'\documentclass{unknownstyle}\usepackage{custom,missingstandard}\graphicspath{{figures/}}\begin{document}\input{body}\bibliography{refs}\end{document}')
   (root/'body.tex').write_text(r'\section{Accuracy of the method}Useful $x^2$.\includegraphics{Plot.EPS}'+'\n% \\input{missing-comment}\n'+r'\iffalse\input{missing-inactive}\fi')
   (root/'custom.sty').write_text(r'\newcommand{\themath}{x^2}')
   (root/'refs.bib').write_text('@article{a,title={Reference}}');(root/'figures/plot.eps').write_bytes(b'figure')
   report,text=a.inspect_tree(root,'main.tex');self.assertTrue(report['complete_content_dependencies']);self.assertIn('Useful $x^2$',text);self.assertIn('@article',text);self.assertIn(r'\newcommand{\themath}',text);self.assertNotIn('missing-comment',text)
   (root/'figures/plot.eps').unlink();report,_=a.inspect_tree(root,'main.tex');self.assertFalse(report['complete_content_dependencies']);self.assertEqual(report['missing_substantive'][0]['kind'],'figure')
 def test_verbatim_percent_and_inactive_input_not_executed(self):
  value='\\begin{verbatim}\nx % keep code\n\\input{not-an-include}\n\\end{verbatim}\n'+r'\verb|100%|'
  self.assertEqual(a.active_text(value),value)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'main.tex').write_text(r'\begin{document}'+value+r'\end{document}');report,text=a.inspect_tree(root,'main.tex');self.assertTrue(report['complete_content_dependencies']);self.assertIn('x % keep code',text)
 def test_style_missing_does_not_block_but_text_include_does(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'main.tex').write_text(r'\documentclass{article}\usepackage{uninstalled}\begin{document}\input{missing}\end{document}');report,_=a.inspect_tree(root,'main.tex');self.assertFalse(report['complete_content_dependencies']);self.assertEqual(report['missing_substantive'][0]['kind'],'included_text')
 def test_math_structure_not_confused_with_table_row_spacing(self):
  doc=DOC.replace('x^2=1',r'\frac{x}{y}=1')+r'\\[3pt]'
  self.assertTrue(a.generated_content(doc,{})['usable'])
  for broken in (DOC.replace('x^2=1',r'\frac{x}{y=1'),DOC.replace('$x^2=1$','$x^2=1'),DOC.replace(r'\end{document}',r'\begin{aligned}\end{document}')):self.assertFalse(a.generated_content(broken,{})['usable'])
 def test_frozen_source_list_alias_and_no_blanket_dispatch(self):
  self.assertEqual(len(intake.TARGETS),16);self.assertEqual(len({x[1] for x in intake.TARGETS}),15)
  self.assertEqual(sum(v=='1107.1834v1' for _,v,_ in intake.TARGETS),2)
  self.assertNotIn('Cooking with Collateral',[x[0] for x in intake.TARGETS])
  with self.assertRaises(ValueError):policy.admit_missing_conversion({'status':'ready'},None)

 def test_author_import_uses_static_saved_files_and_zero_external_operations(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);package=root/'original-package';original=c.ROOT/'fixtures/known-math.pdf'
   package.write_bytes(DOC.encode());(root/'corresponding-version.pdf').write_bytes(original.read_bytes())
   doc={'source_id':'fixture','sha256':sha(original),'originals':[{'path':str(original),'name':'Fixture.pdf'}]}
   packages={'1v1':{'package':str(package),'sha256':sha(package),'main':'source.tex'}}
   with patch('subprocess.run',side_effect=AssertionError('No OCR/model/compiler')),patch('subprocess.Popen',side_effect=AssertionError('No subprocess')):
    r=intake.prepare_author(doc,'1v1','same',packages,root/'outputs')
   self.assertEqual(r['compilation'],'not_requested');self.assertEqual(r['model_review']['status'],'not_requested_author_source');self.assertEqual(r['content_status'],'complete_declared_version')

class Publication(unittest.TestCase):
 def test_complete_text_ready_with_failed_or_unrequested_build_and_pending_review(self):
  for build in ('not_requested','failed'):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);(root/'document.tex').write_text(DOC)
    record={'source_sha256':'a'*64,'selected_tex':[{'path':'document.tex','sha256':sha(root/'document.tex')}],'status':'ready_working_source','content_status':'complete_assigned_source','compilation':build,'model_review':{'pending_reviews':['critic'],'reviewed_full_scope_attested':False}}
    atomic_json(root/'library-status.json',record);seal(root);result=policy.validate_publication(root,{'sha256':'a'*64});self.assertEqual(result['model_review'],record['model_review'])
 def test_missing_content_blocks_ready_even_without_build(self):
  for extra in (r'\input{missing}',r'\includegraphics{missing.pdf}','outstanding'):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);(root/'document.tex').write_text(DOC if extra=='outstanding' else DOC.replace(r'\end{document}',extra+r'\end{document}'))
    record={'source_sha256':'a'*64,'selected_tex':[{'path':'document.tex','sha256':sha(root/'document.tex')}],'status':'ready_working_source','content_status':'complete_assigned_source','compilation':'not_requested','outstanding_scopes':[1] if extra=='outstanding' else []};atomic_json(root/'library-status.json',record);seal(root)
    with self.assertRaises(ValueError):policy.validate_publication(root,{'sha256':'a'*64})
 def test_author_version_and_missing_dependency_validation(self):
  for relation in ('same','alternative','unresolved'):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);(root/'sources').mkdir();(root/'sources/main.tex').write_text(DOC);(root/'ordered.tex').write_text(DOC)
    record={'source_sha256':'a'*64,'source_kind':'author_tex','source_version':{'identifier':'arxiv:1v2','correspondence':relation},'entry_point':'main.tex','selected_tex':[{'path':'ordered.tex','sha256':sha(root/'ordered.tex')}],'status':'ready_working_source','content_status':'complete_declared_version','compilation':'not_requested'}
    atomic_json(root/'library-status.json',record);seal(root);self.assertEqual(policy.validate_publication(root,{'sha256':'a'*64})['source_version']['correspondence'],relation)

class ContentPipeline(unittest.TestCase):
 def setUp(self):
  self.h=fixtures.Pipeline();self.h.setUp();self.addCleanup(self.h.doCleanups)
 def test_default_runtime_path_never_calls_compiler_and_publishes_content(self):
  h=self.h
  with patch.object(c.compiler_environment,'compile_saved',side_effect=AssertionError('Compiler must not be required')),patch.object(c.subprocess,'run',side_effect=h.cpu):
   c.scheduler.coordinate(h.run,h.s,h.s['tasks'],body_for=c.body_for,finish=c.finish,verify=lambda:c.verify(h.run),changed=lambda:c.save(h.run,h.s),sample=h.sample,fixed_level=2,before_reserve=lambda s,t,b:c.before(h.run,s,t,b),transport=h.transport,poll_seconds=.001)
  r=read_json(h.run/'deliveries'/h.sid/'library-status.json');self.assertEqual(r['compilation'],'not_requested');self.assertEqual(r['status'],'ready_working_source');self.assertTrue((h.library/'fixture/current.json').exists())
 def test_optional_absent_compiler_retains_usable_version(self):
  h=self.h;plan=read_json(h.run/'plan.json');plan['settings']['compile_pdf']=True;atomic_json(h.run/'plan.json',plan);h.s['compiler_environment']=None
  v=c.compile_version(h.run,h.s,h.s['tasks'][0],DOC,'absent-compiler');self.assertEqual(v['compilation']['status'],'unavailable');self.assertTrue(v['content_check']['usable'])
 def test_optional_failed_build_retains_usable_version(self):
  h=self.h;plan=read_json(h.run/'plan.json');plan['settings']['compile_pdf']=True;atomic_json(h.run/'plan.json',plan)
  def failed(run,s,root,document,dest,assets):atomic_json(dest/'compilation.json',{'status':'build_failure_unresolved','attempts':[]})
  with patch.object(c.compiler_environment,'compile_saved',side_effect=failed):v=c.compile_version(h.run,h.s,h.s['tasks'][0],DOC,'failed-build')
  self.assertTrue(v['content_check']['usable']);self.assertEqual(v['compilation']['status'],'build_failure_unresolved')
 def test_paid_direct_tex_storage_has_no_compiler_call_by_default(self):
  data=io.BytesIO()
  with zipfile.ZipFile(data,'w') as z:z.writestr('main.tex',DOC)
  with patch('scripts.mathpix_comparison.compile_direct',side_effect=AssertionError('No build')):r=fallback.direct_mathpix_tex(self.h.run,self.h.run/'mathpix',data.getvalue(),None,assigned_pages=[1],returned_pages=[1])
  self.assertEqual(r['status'],'not_requested')

 def test_linked_revised_plan_is_approved_subset_with_original_evidence_unchanged(self):
  h=self.h;plan=read_json(h.run/'plan.json');original_doc=plan['documents'][0]
  ids=['original-c6fbf9bf1bbc7325','original-af03317e4e74c832','original-f0a614adf845cfc3']
  plan['documents']=[];documents={}
  for sid in ids:
   d=copy.deepcopy(original_doc);d['source_id']=sid;d['pages'][0]['image']=d['pages'][0]['path'];d['library_document']['source_id']=sid;d['library_document']['folder']=sid;plan['documents'].append(d)
   documents[sid]={'units':[],'historical_selection':None,'status':'pending_extraction'}
  plan['workloads']['mineru_pro']=[[sid,1] for sid in ids];plan['reuse']=[]
  h.s.update(documents=documents,inputs_prepared=False,source_units={},tasks=[],calls=[],derived_inputs={});h.s.pop('task_plan_sha256',None)
  atomic_json(h.run/'plan.json',plan);c.save(h.run,h.s);binding=read_json(h.run/'binding.json');binding['plan_sha256']=sha(h.run/'plan.json');atomic_json(h.run/'binding.json',binding)
  atomic_json(h.library/'library-first-status.json',{'sources':[{'source_id':sid,'status':'partial' if sid in ids[:2] else 'ready'} for sid in ids]})
  root=h.root/'project';(root/'runs').mkdir(parents=True);pointer=root/'current.json';oldsha=sha(h.run/'plan.json')
  with patch.object(c,'ROOT',root),patch.object(c,'POINTER',pointer):new=c.refresh_prepared(h.run,content_first=True)
  revised=read_json(new/'plan.json');self.assertEqual([d['source_id'] for d in revised['documents']],ids[:2]);self.assertFalse(revised['settings']['compile_pdf']);self.assertEqual(oldsha,sha(h.run/'plan.json'));self.assertEqual(read_json(new/'state.json')['calls'],[])

class MasterPublication(unittest.TestCase):
 def test_fragment_selected_through_master_retains_envelope_and_include_checks(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'parts').mkdir();part=root/'parts/section.tex';part.write_text(r'Complete source $x^2=1$.')
   (root/'master.tex').write_text(r'\documentclass{article}\begin{document}\input{parts/section.tex}\end{document}')
   record={'source_sha256':'a'*64,'selected_tex':[{'path':'parts/section.tex','sha256':sha(part)}],'selected_master':'master.tex','status':'ready_working_source','content_status':'complete_assigned_source','compilation':'failed'}
   atomic_json(root/'library-status.json',record);seal(root);self.assertEqual(policy.validate_publication(root,{'sha256':'a'*64})['status'],'ready_working_source')
