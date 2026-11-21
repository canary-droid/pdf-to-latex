"""Format contracts and real controller paths with fake model transport; no inference."""
import copy,json,re,shutil,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from probe import source_formats as f,image_review,focused_recovery,library_report
from probe.common import atomic_json,read_json,sha,files_manifest
from scripts import library_pipeline as c,export_source_markdown
import test_library_pipeline as fixtures

MD='# Assigned mathematics\n\nFor x positive, the complete assigned expression is $x^2=1$. This retained sentence supplies the definition and condition.\n'

def proposal(text,**kw):
 return dict(base_sha256=f.digest(text),**f.explicit(),scope_review={'full_assigned_scope_reviewed':True,'additional_findings_remain':False,'unreviewed_scope':''},findings=[],**kw)

class Format(unittest.TestCase):
 def test_missing_is_legacy_new_default_explicit_unknown_rejected(self):
  self.assertEqual(f.identity({})['format_protocol'],'legacy-latex');self.assertEqual(f.explicit()['output_format'],'markdown')
  for p in ({'output_format':'markdown'},{'output_format':'html','format_protocol':'x'}):
   with self.assertRaises(ValueError):f.identity(p)
 def test_legacy_requests_byte_for_byte_unchanged(self):
  self.assertEqual(f.conversion_request('a','b','c',{},f.identity({})),focused_recovery.conversion_request('a','b','c',assets={}))
  self.assertEqual(f.critic_request('draft','a','b','c','high',[],f.identity({})),focused_recovery.critic_request('draft','a','b','c',effort='high',images=[]))
 def test_parser_refuses_truncation_wrong_format_multiple_answers(self):
  answer='````markdown\n'+MD+'<!-- source-transcription-complete -->\n````\nAccuracy: unresolved.'
  doc,note=f.parse_markdown(answer,'stop');self.assertEqual(doc,MD);self.assertIn('unresolved',note['notes'])
  for a,reason in ((answer,'length'),(answer+answer,'stop'),('```tex\n'+fixtures.DOC+'\n```','stop'),(answer.replace('<!-- source-transcription-complete -->',''),'stop')):
   with self.assertRaises(ValueError):f.parse_markdown(a,reason)
 def test_markdown_literal_images_format_draft_and_accounting(self):
  png=c.ROOT/'fixtures/vision/case-01.png';import struct
  records=[{'path':str(png),'sha256':sha(png),'dimensions':list(struct.unpack('>II',png.read_bytes()[16:24])),'physical_page':1,'crop':None}]
  body=f.critic_request(MD,'primary','secondary','context','high',image_review.image_parts(records,c.ROOT),f.explicit())
  payload=image_review.request_payload(body);self.assertEqual(payload['draft'],MD);self.assertEqual(payload['base_sha256'],f.digest(MD));self.assertEqual(payload['output_format'],'markdown')
  self.assertEqual(image_review.image_budget(body)['image_count'],1);self.assertTrue(any(x['type']=='image_url' for x in image_review.image_content(body)))
  for field,value in [('base_sha256','stale'),('output_format','latex'),('format_protocol','other')]:
   p=proposal(MD);p[field]=value
   with self.assertRaises(ValueError):image_review.apply_review(MD,p,**f.explicit())
 def test_exact_edit_preserves_figure_labels_footnotes_tables_and_equations(self):
  doc=MD+'\n$$\nx=1\\tag{3}\n$$\n<a id="eq3"></a>\n![Caption](assets/a.png)\n\nValue[^n].\n\n[^n]: Source footnote.\n\n| x | value |\n|---|---|\n| 1 | 3.538E-03 |\n'
  edit={'status':'edit','old':'3.538E-03','new':'3.538E-02','source':'physical p6 row100 columnTe10','reason':'fixture only','printed_source':'3.538E-02','draft_reading':'3.538E-03','proposed_change':'exponent','justification':'synthetic source check','replacement_format':'markdown'}
  p=proposal(doc);p['findings']=[edit];revised,log=image_review.apply_review(doc,p,**f.explicit());self.assertIn('3.538E-02',revised);self.assertEqual(log['findings'][0]['disposition'],'applied_model_claim')
  for old,new in [('assets/a.png','assets/b.png'),('\\tag{3}','\\tag{4}'),('[^n]','[^other]')]:
   p=proposal(doc);p['findings']=[dict(edit,old=old,new=new)]
   # Whole-structure edits are protected; a changed link target must also be
   # detected by final validation even when only a substring is proposed.
   revised,log=image_review.apply_review(doc,p,**f.explicit())
   self.assertEqual(revised,doc)
 def test_unrendered_tex_prose_is_retained_but_not_reported_usable(self):
  raw=MD+'\n'+r'\section{Appendix} Unconverted source structure.'
  result=f.validate(raw);self.assertFalse(result['usable']);self.assertIn('unrendered_tex_commands',[x['kind'] for x in result['unresolved_structures']])
  self.assertTrue(f.validate(MD+'\n$$\frac{x}{2}\tag{7}$$\n')['usable'])
 def test_short_missing_heading_is_an_explicit_coverage_flag(self):
  u={'native_blocks':[{'id':'h','kind':'paragraph_title','tex':r'\section{Assumptions}','page':{'original_physical_page':2},'assets':[]}]}
  self.assertEqual(f.coverage(MD,u)['missing_heading_candidates'][0]['block'],'h')
  self.assertEqual(f.coverage(MD+'\n## Assumptions\n',u)['missing_heading_candidates'],[])
 def test_empty_missing_tables_figures_spans_and_math_are_visible(self):
  blocks=[{'id':'eq','kind':'equation','tex':r'\[x=1\tag{34}\]','page':{'original_physical_page':2},'assets':[]},{'id':'fig','kind':'image','tex':'image','page':{'original_physical_page':2},'assets':['assets/a.png']},{'id':'table','kind':'table','tex':'header value','page':{'original_physical_page':2},'assets':[]}]
  c=f.coverage(MD,{'native_blocks':blocks});self.assertEqual(c['source_tables'],1);self.assertEqual(c['missing_figures'],['assets/a.png']);self.assertIn('34',c['missing_equation_tags']);self.assertEqual(c['coverage_status'],'omission_risk')
  self.assertFalse(f.validate('')['usable']);self.assertFalse(f.validate('Text with $unclosed')['usable'])
 def test_assembly_preserves_parts_and_checks_refs_duplicates_and_links(self):
  a=MD+'\n![figure](assets/a.png)\n<a id="eq1"></a>\n$$x=1\\tag{1}$$\n';b='## Proof\nSee [equation](#eq1). All details follow.\n'
  out,check=f.assembly([('u1',a),('u2',b)]);self.assertTrue(check['usable']);self.assertIn('parts/u1/assets/a.png',out);self.assertIn('assets/a.png',a)
  self.assertFalse(f.assembly([('u1',a),('u2',a)])[1]['usable']);self.assertFalse(f.assembly([('u1',b)])[1]['usable'])
 def test_assembly_namespaces_local_footnotes_without_changing_parts(self):
  a='Source A[^1].\n\n[^1]: First original footnote.\n';b='Source B[^1].\n\n[^1]: Second original footnote.\n'
  result,check=f.assembly([('a',a),('b',b)]);self.assertTrue(check['usable']);self.assertIn('[^a-1]',result);self.assertIn('[^b-1]',result);self.assertIn('[^1]',a)
 def test_verified_composite_preserves_coverage_and_detects_double_display(self):
  unit={'assets':{},'native_blocks':[{'id':'fig','kind':'image','tex':'figure','page':{'original_physical_page':1},'assets':['assets/composite.png','assets/panel.png']}],
    'coverage_metadata':{'verified_figure_groups':[{'id':'g','canonical':'assets/composite.png','members':['assets/panel.png']}]}}
  doc='![All panels](assets/composite.png)'
  self.assertEqual(f.coverage(doc,unit)['missing_figures'],[])
  self.assertEqual(f.coverage(doc+'\n![Panel](assets/panel.png)',unit)['duplicated_verified_figures'],['g'])
  unit['coverage_metadata']['verified_figure_groups'][0]['source_check']={'visual_check':False}
  with self.assertRaises(ValueError):f.coverage(doc,unit)
 def test_bounded_export_preserves_math_and_reports_raw_tables_macros(self):
  tex=r'\documentclass{article}\begin{document}\section{Accuracy of approximation}Assume $x>0$.\footnote{An original note.}\[f(x)=\frac{x^2}{2}\tag{7}\]\begin{tabular}{lr}name & value \\ a & 1.25\end{tabular}\end{document}'
  md,record=f.tex_export(tex);self.assertIn(r'f(x)=\frac{x^2}{2}\tag{7}',md);self.assertIn('Accuracy of approximation',md);self.assertIn('[^tex-1]: An original note.',md);self.assertIn(r'\begin{tabular}{lr}name & value \\ a & 1.25\end{tabular}',md);self.assertEqual(record['status'],'partial_unsupported')
 def test_portable_saved_fixture_preserves_technical_structures(self):
  path=c.ROOT/'fixtures/markdown/saved-cms-excerpt.tex';tex=path.read_text();md,record=f.tex_export(tex)
  self.assertEqual(sha(path),read_json(path.with_suffix('.provenance.json'))['fixture_sha256'])
  for env in ('tabular','lemma','proof'):
   original=re.search(r'\\begin\{'+env+r'\}.*?\\end\{'+env+r'\}',tex,re.S)[0]
   self.assertIn(original,md)
  self.assertIn(r'\tag{1}',md);self.assertEqual(record['status'],'partial_unsupported')
 def test_cli_new_prepare_defaults_markdown_with_explicit_latex_option(self):
  for args,fmt in [([], 'markdown'),(['--output-format','latex'],'latex')]:
   with patch.object(c.sys,'argv',['library','prepare','--source-id','synthetic']+args),patch.object(c,'prepare') as prepare:
    c.main();self.assertEqual(prepare.call_args.args[-1],fmt)
 def test_real_saved_tex_export_is_bound_and_never_mutates_parent(self):
  parent=c.ROOT/'runs/library-first-20261115T190611Z-power-recovery';s=read_json(parent/'state.json');key='master-5f57f34a412e4d54-unit-001';v=s['versions'][key]['convert'];path=parent/v['path'];before=sha(path)
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'export';result=export_source_markdown.export(path,before,out,asset_root=parent/'inputs');self.assertEqual(sha(path),before);self.assertEqual(sha(out/'original.tex'),before)
   self.assertTrue((out/'source.md').stat().st_size>3000);self.assertEqual(result['source_image_review'],'not performed; existing TeX review does not become a Markdown image review')
   self.assertEqual(export_source_markdown.export(path,before,out),read_json(out/'export.json'))

class Controller(unittest.TestCase):
 def setUp(self):
  self.h=fixtures.Pipeline(methodName='runTest');self.h.setUp();self.addCleanup(self.h.doCleanups);h=self.h;p=read_json(h.run/'plan.json');p.update(f.explicit(),isolated_publication=True);h.s.update(f.explicit());atomic_json(h.run/'plan.json',p)
  # This is a disposable zero-call fixture, not a production migration.
  h.s.update(inputs_prepared=False,tasks=[],source_units={},derived_inputs={});h.s.pop('task_plan_sha256',None);h.s['documents'][h.sid].update(units=[]);h.s['documents'][h.sid].pop('planning_done',None)
  b=read_json(h.run/'binding.json');b['plan_sha256']=sha(h.run/'plan.json');atomic_json(h.run/'binding.json',b);c.plan_units(h.run,h.s);h.transport=self.transport
 def transport(self,run,call,body,**kw):
  h=self.h;h.seen.append(call['parent']);critic=call['parent'].endswith('/critic')
  if critic:
   payload=image_review.request_payload(body);self.assertEqual(payload['draft'],MD);self.assertEqual(payload['output_format'],'markdown');answer=json.dumps(proposal(MD))
  else:
   self.assertIn('technical-markdown-v1',body['messages'][0]['content']);answer='````markdown\n'+MD+'<!-- source-transcription-complete -->\n````\nNo independent source checks.'
  call.update(status='completed_response',elapsed_seconds=.01,metadata={'actual_model':'glm53-regular','finish_reason':'stop','usage':{'prompt_tokens':777,'completion_tokens':10}})
  folder=run/'calls'/call['id'];folder.mkdir(parents=True);atomic_json(folder/'request.json',body);atomic_json(folder/'attempts/one/request.json',{'body':body});atomic_json(folder/'outcome.json',call);(folder/'content.txt').write_text(answer);(folder/'answer.txt').write_text(answer);atomic_json(folder/'manifest.json',files_manifest(folder));call['seal']=sha(folder/'manifest.json')
  if h.pause:atomic_json(run/'pause.json',{'operator':True})
  return answer,call
 def test_real_path_settlement_publication_bundle_and_finished_zero_replay(self):
  h=self.h;h.coordinate();h.coordinate();self.assertEqual(len(h.seen),2);v=h.s['versions'][h.key]['review'];self.assertTrue(v['path'].endswith('.md'));self.assertEqual(v['compilation']['status'],'not_requested')
  out=h.run/'deliveries'/h.sid;self.assertTrue((out/'source.md').exists());self.assertFalse((h.library/'fixture').exists());r=read_json(out/'library-status.json');self.assertTrue(r['selected_markdown']);self.assertFalse(r['selected_tex'])
  result=library_report.inspection(h.run,h.s,h.root/'bundles')
  with zipfile.ZipFile(result['path']) as z:self.assertIn('deliveries/'+h.sid+'/source.md',z.namelist());self.assertIn('calls/call-002/changes.diff',z.namelist())
  h.s['status']=c.TERMINAL;c.save(h.run,h.s)
  with patch.object(c.sys,'argv',['library','resume','--run',str(h.run)]),patch.object(c.subprocess,'run',side_effect=AssertionError('No host dispatch')):c.main()
 def test_pause_sealed_response_restart_does_not_reconvert(self):
  h=self.h;h.pause=True
  with self.assertRaises(c.runtime.StopRun):h.coordinate()
  self.assertEqual(len(h.seen),1);call=h.s['calls'][0];task=h.s['tasks'][0]
  # Reconcile a sealed response after interrupted settlement. No transport replay.
  body=c.body_for(h.run,h.s,task);result=c.saved_response(h.run,call,body);self.assertEqual(result['status'],'completed_response')
  h.pause=False;(h.run/'pause.json').unlink();h.coordinate();self.assertEqual(len(h.seen),2)
 def test_resume_settles_consumed_sealed_answer_without_transport_replay(self):
  h=self.h;h.pause=True
  with self.assertRaises(c.runtime.StopRun):h.coordinate()
  task=h.s['tasks'][0];call=h.s['calls'][0];task.pop('settled_call');task['status']='running'
  # Simulated crash between seal and settlement; restore the durable reservation
  # then use the exact production reconciliation helper, not the fake transport.
  h.s['versions']={};h.s['current_versions']={};c.save(h.run,h.s)
  body=c.body_for(h.run,h.s,task);call.update(c.saved_response(h.run,call,body))
  c.finish(h.run,h.s,task,(h.run/'calls'/call['id']/'content.txt').read_text(),call)
  self.assertEqual(h.seen,[task['id']]);h.pause=False;(h.run/'pause.json').unlink();h.coordinate();self.assertEqual(len(h.seen),2)
 def test_wrong_unit_or_version_format_refused(self):
  h=self.h;h.coordinate();h.s['versions'][h.key]['convert']['output_format']='latex';c.save(h.run,h.s)
  with self.assertRaises(c.runtime.Fatal):c.verify(h.run)
 def test_resume_explicit_wrong_format_is_rejected_before_dispatch(self):
  h=self.h
  with patch.object(c.sys,'argv',['library','resume','--run',str(h.run),'--output-format','latex']),patch.object(c.subprocess,'run',side_effect=AssertionError('No host dispatch')):
   with self.assertRaises(c.runtime.Fatal):c.main()
 def test_unsealed_uncertain_reservation_is_not_a_retry(self):
  h=self.h;h.s['calls']=[{'id':'call-001','parent':h.s['tasks'][0]['id'],'status':'in_progress','request_sha256':'0'*64}];c.save(h.run,h.s)
  with self.assertRaises((ValueError,FileNotFoundError,c.runtime.Fatal)):c.saved_response(h.run,h.s['calls'][0],c.body_for(h.run,h.s,h.s['tasks'][0]))
  self.assertEqual(h.seen,[])

if __name__=='__main__':unittest.main()
