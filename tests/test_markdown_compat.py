"""Saved Obsidian failures: exact source mapping, not renderer/fidelity claims."""
import copy,json,re,unittest
from pathlib import Path
from unittest.mock import patch
from probe import markdown_compat as m,source_formats as f,image_review
from scripts import library_pipeline as controller
import test_source_formats as setup

FIX=Path(__file__).resolve().parents[1]/'fixtures/markdown/obsidian'
def saved(name):return (FIX/(name+'.md')).read_text(),json.loads((FIX/(name+'.json')).read_text())

class SavedCompatibility(unittest.TestCase):
 def test_actual_pykhtin_all_ten_footnotes_and_exact_math(self):
  text,u=saved('pykhtin');new,log=m.normalize(text,u)
  self.assertEqual(re.findall(r'(?m)^\[\^(\d+)\]:',new),list(map(str,range(1,11))))
  self.assertEqual(len(re.findall(r'\[\^\d+\](?!:)',new)),10)
  for expression in ('$\\sigma_{k}$','$\\rho_{kl}$','$w_{k}(\\cdot)$'):self.assertIn(expression,new)
  self.assertIn('Exposure [^1]',new)
  self.assertEqual(re.findall(r'\$\$.*?\$\$',text,re.S),re.findall(r'\$\$.*?\$\$',new,re.S))
  self.assertEqual(len([x for x in log['transformations'] if x['kind']=='linked_source_footnote']),10)
  self.assertTrue(f.validate(new,unit=u)['usable']);self.assertFalse(f.validate(text,unit=u)['usable'])
  self.assertEqual(m.footnote_coverage(new,u)['missing_or_changed_definitions'],[])
 def test_zero_notes_is_not_success_and_changed_text_detected(self):
  text,u=saved('pykhtin');new,_=m.normalize(text,u)
  self.assertEqual(len(m.footnote_coverage(text,u)['missing_or_changed_definitions']),10)
  bad=new.replace('See BCBS (2014-A).','Wrong reference.')
  self.assertEqual(len(m.footnote_coverage(bad,u)['missing_or_changed_definitions']),1)
  self.assertEqual(len(m.footnote_coverage(new.split('[^1]:')[0],u)['missing_or_changed_definitions']),10)
 def test_retargeted_ref_detected_even_with_all_definitions(self):
  text,u=saved('pykhtin');new,_=m.normalize(text,u)
  bad=new.replace('Exposure [^1]','Exposure [^2]')
  self.assertTrue(m.footnote_coverage(bad,u)['unbound_references'])
  self.assertNotEqual(f.structural_tokens(new),f.structural_tokens(bad))
 def test_valid_descriptive_footnote_ids_are_preserved(self):
  text,u=saved('pykhtin');new,_=m.normalize(text,u)
  named=re.sub(r'\[\^(\d+)\]',lambda x:'[^source-note-'+x[1]+']',new)
  normalized,record=m.normalize(named,u)
  self.assertEqual(named,normalized);self.assertEqual(record['unresolved'],[])
  self.assertTrue(f.validate(named,unit=u)['usable'])
 def test_ambiguous_source_mapping_is_not_guessed(self):
  text,u=saved('pykhtin');u['native_blocks']+=copy.deepcopy([next(b for b in u['native_blocks'] if b['kind']=='page_footnote')])
  new,log=m.normalize(text,u);self.assertNotIn('Exposure [^1]',new)
  self.assertTrue(any(x['kind']=='ambiguous_footnote_mapping' for x in log['unresolved']))
 def test_cms_note_and_source_confirmed_join(self):
  text,u=saved('cms');new,log=m.normalize(text,u)
  self.assertIn('for the information available in the Market.',new)
  note=m.source_notes(u)[0]['text'];self.assertEqual(new.count(note),1)
  self.assertTrue(new.rstrip().endswith(note));self.assertIn('Unnumbered source note (physical page 1)',new)
  self.assertNotIn('[^',new);self.assertTrue(f.validate(new,unit=u)['usable'])
 def test_mushroom_join_preserves_other_paragraphs_and_context(self):
  text,u=saved('fish-stock');new,log=m.normalize(text,u)
  self.assertEqual(new,text.replace('mushroom\n\ntrimmings','mushroom trimmings').replace('remembered\n\nthat the butter','remembered that the butter'))
  self.assertEqual(re.findall(r'<!--.*?-->',text,re.S),re.findall(r'<!--.*?-->',new,re.S))
  self.assertEqual([x['kind'] for x in log['transformations']],['source_checked_paragraph_join']*2)
 def test_no_blind_join_and_stale_evidence_rejected(self):
  text,u=saved('fish-stock');empty=copy.deepcopy(u);empty.pop('markdown_compatibility_evidence')
  self.assertEqual(m.normalize(text,empty)[0],text)
  self.assertEqual(len(m.paragraph_boundary_findings(text,empty)),2)
  repaired=m.normalize(text,u)[0]
  self.assertEqual(m.paragraph_boundary_findings(repaired,u),[])
  join=u['markdown_compatibility_evidence']['joins'][0];join['block_sha256'][next(iter(join['block_sha256']))]='stale'
  with self.assertRaises(ValueError):m.normalize(text,u)
 def test_source_headings_notes_under_recipe(self):
  text,u=saved('sauces');new,log=m.normalize(text,u)
  self.assertEqual(len(re.findall(r'(?m)^## \d+ ',new)),9)
  self.assertIn('### Notes:',new);self.assertNotIn('\\section',new)
  old_titles=re.findall(r'\\section\*\{([^{}]+)\}',text)
  self.assertEqual(old_titles,re.findall(r'(?m)^#{2,3} (.+)',new))
  self.assertTrue(f.validate(new,unit=u)['usable'])
 def test_all_saved_normalizations_idempotent_and_bound(self):
  for name in ('pykhtin','cms','sauces','fish-stock'):
   text,u=saved(name);new,log=m.normalize(text,u);again,second=m.normalize(new,u)
   self.assertEqual(new,again);self.assertFalse(second['changed']);self.assertEqual(second['transformations'],[])
   self.assertEqual(log['input_sha256'],m.digest(text));self.assertEqual(log['output_sha256'],m.digest(new))
   self.assertIn('does not attest',log['review_status'])

class ProtectedCases(unittest.TestCase):
 def test_delimiter_whitespace_preserves_inner_bytes(self):
  s=r'A \( \sigma_{k} \), \(\rho_{kl}\), \( w_{k}(\cdot) \); $x^2$ and $$y=3\tag{1}$$.'
  new,_,_=m.inline_math(s)
  self.assertEqual(new,r'A $\sigma_{k}$, $\rho_{kl}$, $w_{k}(\cdot)$; $x^2$ and $$y=3\tag{1}$$.')
 def test_code_examples_comments_currency_existing_math_unchanged(self):
  literals=[r'`\( x \)`',r'``a ` \(x\)``','~~~tex\n\\( x \\)\n~~~','````text\n```\n\\(x\\)\n````',r'<!-- \( x \) -->',r'%% \( x \) %%',r'\$20 and \$30',r'\\(literal\\)',r'$\sigma_k$ and $$x^2\tag{1}$$',r'\[x^2\]',r'[label](path/\(example\).png)','    \\(x\\)']
  for s in literals:self.assertEqual(m.normalize(s)[0],s,s)
  for s in ['> ```tex\n> \\(x\\)\n> ```',r'<code>\(x\)</code>',r'<pre>\(x\)</pre>']:
   self.assertEqual(m.normalize(s)[0],s)
 def test_legitimate_superscripts_are_never_footnotes_without_evidence(self):
  text=r'Powers \(x^{1}\) and \( ^{1} \), $^{1}$, $$^{1}$$.'
  new,_=m.normalize(text);self.assertNotIn('[^',new);self.assertEqual(new.count('^{1}'),4)
  self.assertEqual(m.SUP.findall('$$^{1}$$'),[])
 def test_ambiguous_math_left_visible(self):
  for text in [r'\( \frac{x}{ \)',r'\( \)',r'\(x $y$\)','\\(x\n\ny\\)']:
   new,log=m.normalize(text);self.assertEqual(new,text);self.assertTrue(log['unresolved'])
 def test_unknown_tex_heading_not_guessed(self):
  text=r'\section*{Unmapped title}';new,log=m.normalize(text)
  self.assertEqual(new,text);self.assertTrue(log['unresolved'])
 def test_literal_heading_and_note_examples_are_protected(self):
  text,u=saved('sauces');sample='```tex\n\\section*{Notes:}\n```\n'
  self.assertEqual(m.normalize(sample,u)[0],sample)
 def test_existing_spaced_dollar_math_flagged_not_silently_rewritten(self):
  s='Complete retained source with $ x^2 $ and conditions.'
  self.assertEqual(m.normalize(s)[0],s);self.assertFalse(f.validate(s)['usable'])
 def test_assembly_does_not_namespace_code_or_comment_examples(self):
  text='Actual[^1].\n\n[^1]: Note.\n\n`[^1] ![x](assets/a.png)`\n\n<!-- [^1] -->\n\n![figure](assets/a.png)\n'
  new,_=f.assembly([('unit',text)])
  self.assertIn('Actual[^unit-1]',new);self.assertIn('`[^1] ![x](assets/a.png)`',new)
  self.assertIn('<!-- [^1] -->',new);self.assertIn('![figure](parts/unit/assets/a.png)',new)
 def test_duplicate_or_missing_markdown_notes_fail_validation(self):
  for s in ['Paragraph reference[^x].','Paragraph only.\n\n[^x]: Unreferenced.','Paragraph[^x].\n\n[^x]: First.\n\n[^x]: Second.']:
   self.assertFalse(f.validate(s)['usable'])

class ControllerCompatibility(setup.Controller):
 def test_real_transport_boundary_critic_sees_normalized_saved_draft(self):
  h=self.h;raw=setup.MD.replace('$x^2=1$',r'\( x^2=1 \)');normalized=m.normalize(raw)[0]
  original_transport=h.transport
  def transport(run,call,body,**kw):
   with patch.object(setup,'MD',normalized if call['parent'].endswith('/critic') else raw):
    return original_transport(run,call,body,**kw)
  h.transport=transport;h.coordinate()
  self.assertEqual(len(h.seen),2)
  converted=h.s['versions'][h.key]['convert']
  self.assertEqual(converted['sha256'],m.digest(normalized))
  payload=image_review.request_payload(json.loads((h.run/'calls/call-002/request.json').read_text()))
  self.assertEqual(payload['draft'],normalized);self.assertEqual(payload['base_sha256'],converted['sha256'])
 def test_real_settlement_normalizes_before_critic_and_retains_raw(self):
  h=self.h;raw=r'Paragraph has \( x^{2} \) and its complete original assumptions.'+'\n';new=m.normalize(raw)[0]
  t=next(t for t in h.s['tasks'] if t['phase']=='convert')
  v=controller.compile_version(h.run,h.s,t,raw,'format-fixture')
  self.assertEqual((h.run/v['path']).read_text(),new);self.assertEqual(v['sha256'],m.digest(new))
  self.assertEqual((h.run/v['path']).with_name('before-normalization.md').read_text(),raw)
  proposal=setup.proposal(raw)
  with self.assertRaises(ValueError):image_review.apply_review(new,proposal,**f.explicit())
  critic=dict(t,phase='critic',draft_sha256=m.digest(new))
  reviewed=controller.compile_version(h.run,h.s,critic,new+'\nNew \\( y \\).','review-format-fixture')
  self.assertTrue(reviewed['compatibility']['post_review_format_change'])
  self.assertEqual(reviewed['compatibility']['critic_input_sha256'],m.digest(new))
