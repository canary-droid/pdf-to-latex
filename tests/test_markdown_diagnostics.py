"""Saved failure regressions; no transport, historical mutation or promotion."""
import json,re,unittest
from pathlib import Path
from unittest.mock import patch
from probe import book_completion as b,source_formats as f,library_repair,library_completion,chapter_accuracy
from probe.common import read_json,atomic_json,sha
from scripts import simple_chapter_glm as simple,prepare_markdown_qualification as prep,library_pipeline as c
import test_library_pipeline as fixtures
FIX=Path(__file__).resolve().parents[1]/'fixtures/markdown/diagnostics'

class Diagnostics(unittest.TestCase):
 def evidence(self,name):
  rec=read_json(FIX/(name+'.json'));p=FIX/(name+'.tex');self.assertEqual(sha(p),rec['fixture_sha256']);return p.read_text(),rec['source_blocks']
 def test_saved_bibliography_and_styled_proof_legacy_and_markdown(self):
  for name in ('bibliography','proof'):
   text,blocks=self.evidence(name);native={'blocks':blocks};ids=[x['id'] for x in blocks]
   self.assertEqual(b.coverage_check(text,native,ids)['missing_heading_candidates'],[])
   md=re.sub(r'\\(?:section\*?|textit)\{([^{}]*)\}',r'\1',text).replace('\\item ','- ').replace('\\begin{itemize}','').replace('\\end{itemize}','').replace('\\\\','\n')
   self.assertEqual(f.coverage(md,{'native_blocks':blocks})['missing_heading_candidates'],[])
   for block in blocks:
    title=b.headings(block['tex'])[0];missing=text.replace(title,'REMOVED');missing_md=md.replace(title,'REMOVED')
    self.assertIn(title,b.coverage_check(missing,native,ids)['missing_heading_candidates'])
    self.assertTrue(any(x['block']==block['id'] for x in f.coverage(missing_md,{'native_blocks':blocks})['missing_heading_candidates']))
 def test_prose_mention_or_generated_notes_do_not_satisfy_tex_heading(self):
  block={'id':'h','kind':'paragraph_title','tex':r'\section{Proof. See Appendix D}','assets':[]}
  for text in ('Some prose says Proof. See Appendix D but no assigned pointer.',r'% PDF2TEX_GENERATED_NOTES_BEGIN'+'\n'+r'\textit{Proof. See Appendix D}'):
   self.assertEqual(b.coverage_check(text,{'blocks':[block]},['h'])['missing_heading_candidates'],['Proof. See Appendix D'])
 def test_standard_notation_custom_macro_and_viewer_extension_are_distinct(self):
  doc=r'Ordinary source mathematics: $f^{\prime}(x)=\frac{1}{2}\lceil x\rceil+\arctan x+\ln x+\widehat{X}+\varnothing\rightarrow 0$.'
  self.assertTrue(f.validate(doc)['usable']);self.assertEqual(f.validate(doc)['unresolved_structures'],[])
  custom=f.validate(doc+r' $\SourceSpecific{x}$')['unresolved_structures'];self.assertEqual(custom[0]['kind'],'unqualified_math_macros');self.assertEqual(custom[0]['macros'],['SourceSpecific'])
  viewer=f.validate(doc+r' $\cancel{x}$')['unresolved_structures'];self.assertEqual(viewer[0]['kind'],'viewer_specific_math_commands')
 def test_saved_invalid_escape_does_not_fabricate_a_review(self):
  meta=read_json(FIX/'call-240.json');path=FIX/'call-240.txt';self.assertEqual(sha(path),meta['sha256']);answer=path.read_text()
  with self.assertRaises(ValueError):library_repair.salvage_json(answer,'dfef6eec0a1e06425a958d3d937ff44fa62522dd7886bfcdfe32f390e197edca')
  with self.assertRaises(ValueError):library_completion.saved_review(answer,'dfef6eec0a1e06425a958d3d937ff44fa62522dd7886bfcdfe32f390e197edca')
 def test_saved_duplicate_complete_documents_remain_ambiguous(self):
  p=FIX/'call-249.txt';self.assertEqual(sha(p),read_json(FIX/'call-249.json')['sha256']);answer=p.read_text();blocks=re.findall(r'\\documentclass\b.*?\\end\{document\}',answer,re.S)
  self.assertEqual(len(blocks),2);self.assertEqual(blocks[0].encode(),blocks[1].encode())
  doc,info=chapter_accuracy.envelope(answer,simple.extract_document);self.assertIsNone(doc);self.assertEqual(info['status'],'ambiguous')
  with self.assertRaises(ValueError):library_completion.wrap_fragment(answer)
  with self.assertRaises(ValueError):f.parse_markdown(answer,'stop')

class Refresh(unittest.TestCase):
 def setUp(self):
  self.h=fixtures.Pipeline(methodName='runTest');self.h.setUp();self.addCleanup(self.h.doCleanups);h=self.h
  p=read_json(h.run/'plan.json');p['isolated_publication']=True;atomic_json(h.run/'plan.json',p);binding=read_json(h.run/'binding.json');binding['plan_sha256']=sha(h.run/'plan.json');atomic_json(h.run/'binding.json',binding);atomic_json(h.run/'QUALIFICATION.json',{'kind':'technical'});c.save(h.run,h.s)
 def test_derived_unit_refresh_preserves_parent_and_scope_no_attempts(self):
  h=self.h;before={n:sha(h.run/n) for n in ('state.json','plan.json','binding.json','task-plan.json')}
  with patch.object(prep,'ROOT',h.root):child=prep.refresh(h.run)
  s=c.verify(child);self.assertEqual([t['id'] for t in s['tasks']],[t['id'] for t in h.s['tasks']]);self.assertEqual(s['calls'],[]);self.assertEqual(s['source_units'][h.key]['blocks'],h.s['source_units'][h.key]['blocks']);self.assertEqual(before,{n:sha(h.run/n) for n in before})
  self.assertTrue(read_json(child/'preparation-link.json')['settings_unchanged'])
  with patch.object(prep,'ROOT',h.root):grandchild=prep.refresh(child)
  self.assertEqual([t['id'] for t in c.verify(grandchild)['tasks']],[t['id'] for t in h.s['tasks']])
  archived=grandchild/'preparation-links'/(sha(child/'preparation-link.json')+'.json')
  self.assertEqual(sha(archived),sha(child/'preparation-link.json'))
 def test_consumption_changed_source_or_derived_scope_blocks_refresh(self):
  h=self.h
  for field,value in [('calls',[{'id':'consumed'}]),('launches',[{'pid':1}])]:
   s=dict(h.s);s[field]=value;atomic_json(h.run/'state.json',s)
   with patch.object(prep,'ROOT',h.root),self.assertRaises(ValueError):prep.refresh(h.run)
  c.save(h.run,h.s);unit=h.run/'inputs'/h.key/'unit.json';unit.write_text('{}')
  with patch.object(prep,'ROOT',h.root),self.assertRaises(Exception):prep.refresh(h.run)
if __name__=='__main__':unittest.main()

class LiveQualificationRegressions(unittest.TestCase):
 def test_standard_envelope_and_inequalities_never_eat_source_headings(self):
  doc='## Definition\n\nAssume $p<n$ and preserve all source conditions.\n\n## 2.3 Products in Scope\n\nThe next condition is $x>0$.\n\n$$q=1\\tag{7}$$\n'
  unit={'native_blocks':[{'id':'h','kind':'paragraph_title','tex':r'\section*{2.3 Products in Scope}','assets':[]}]}
  for width in (3,4):
   raw='`'*width+'markdown\n'+doc+'<!-- source-transcription-complete -->\n'+'`'*width+'\nNotes.'
   parsed,record=f.parse_markdown(raw,'stop');self.assertEqual(parsed,doc);self.assertEqual(f.coverage(parsed,unit)['missing_heading_candidates'],[])
   with self.assertRaises(ValueError):f.parse_markdown(raw+raw,'stop')
   with self.assertRaises(ValueError):f.parse_markdown(raw,'length')
  self.assertIn('2 3 products in scope',' '.join(f.plain(doc)))
  self.assertTrue(f.validate(r'An explicit proof ending: $\square$.')['usable'])
  self.assertNotIn('phantomheading',' '.join(f.plain('<!-- phantomheading --> actual source.')))
 def test_saved_consumed_qualification_continuation_only_one_critic(self):
  import tempfile
  root=Path(__file__).resolve().parents[1];parent=root/'runs/markdown-technical-20261116T035845Z-linked-406851'
  if not parent.is_dir():self.skipTest('Saved local qualification evidence unavailable')
  old=read_json(parent/'state.json');before={n:sha(parent/n) for n in ('state.json','plan.json','binding.json')}
  with tempfile.TemporaryDirectory() as td:
   temp=Path(td);(temp/'runs').mkdir()
   with patch.object(prep,'ROOT',temp):child=prep.continue_saved(parent)
   state=c.verify(child);self.assertEqual(state['calls'],old['calls']);self.assertEqual(len(state['calls']),5)
   pending=[t['id'] for t in state['tasks'] if t['status']=='pending'];self.assertEqual(pending,['master-5f57f34a412e4d54-unit-001/critic'])
   for key in prep.TECH:
    v=state['versions'][key][state['current_versions'][key]];self.assertTrue(v['content_check']['usable'])
   self.assertEqual([t['id'] for t in state['tasks']],[t['id'] for t in old['tasks']]);self.assertEqual(before,{n:sha(parent/n) for n in before})
   # Resume must not admit a consumed task, independent of its new validation.
   consumed=next(t for t in state['tasks'] if t['phase']=='convert')
   with self.assertRaises(c.runtime.Fatal):c.before(child,state,consumed,c.body_for(child,state,consumed))
