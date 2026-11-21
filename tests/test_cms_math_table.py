import re,unittest
from pathlib import Path
from probe import markdown_compat as m,source_formats as f

TABLE='<table><caption>Table 1</caption><tr><th>Instrument</th><th>Payoff $f(x)$</th></tr><tr><td>Swap</td><td>$x^2$ with $x>0$.</td></tr></table>'
class TableMath(unittest.TestCase):
 def test_saved_cms_all_four_cells_math_and_note(self):
  root=Path(__file__).resolve().parents[1]/'fixtures/markdown/obsidian'
  import json
  text=(root/'cms.md').read_text();unit=json.loads((root/'cms.json').read_text())
  new,log=m.normalize(text,unit)
  self.assertNotIn('<table',new);self.assertIn('Table 1: Payoffs coverage',new)
  self.assertEqual(len(re.findall(r'(?m)^\|',new)),6)
  self.assertEqual(re.findall(r'\$[^$]*\$',text),re.findall(r'\$[^$]*\$',new))
  self.assertIn('for the information available in the Market.',new)
  self.assertIn('Unnumbered source note (physical page 1)',new)
  self.assertEqual(m.normalize(new,unit)[0],new)
  self.assertTrue(f.validate(new,unit=unit)['usable'])
 def test_unconverted_table_is_not_rendering_success(self):
  self.assertFalse(f.validate(TABLE)['usable']);self.assertTrue(f.validate(m.normalize(TABLE)[0])['usable'])
 def test_pipe_math_norms_and_prose(self):
  s=TABLE.replace('$x^2$ with $x>0$.',r'$|x|+\|y\|$ and A|B.')
  new=m.normalize(s)[0]
  self.assertIn(r'$\vert x\vert +\Vert y\Vert $ and A&#124;B.',new)
  self.assertEqual(m.normalize(new)[0],new)
 def test_merged_nested_unknown_and_display_preserved(self):
  for old in [TABLE.replace('<td>Swap','<td colspan="2">Swap'),TABLE.replace('$x^2$', '$$x^2$$'),TABLE.replace('Swap','<b>Swap</b>'),TABLE.replace('$x^2$',r'$\text{a|b}$'),TABLE.replace('Swap',TABLE)]:
   new,log=m.normalize(old);self.assertEqual(new,old);self.assertTrue(log['unresolved'])
 def test_nonmath_and_literal_examples_unchanged(self):
  for s in [TABLE.replace('$',''),'```html\n'+TABLE+'\n```','<!-- '+TABLE+' -->','<pre>'+TABLE+'</pre>','`'+TABLE+'`']:
   self.assertEqual(m.normalize(s)[0],s)
 def test_cell_entities_and_order(self):
  s=TABLE.replace('$x^2$', '$x&lt;2$').replace('Swap','A &amp; B')
  new=m.normalize(s)[0];self.assertIn('$x<2$',new);self.assertIn('A & B',new)
