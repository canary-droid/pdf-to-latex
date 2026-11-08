import unittest,copy,json
from pathlib import Path
from unittest.mock import patch
from probe import extraction_followup as c

class FollowupContracts(unittest.TestCase):
    def rows(self):
        return [{'index':i,'label':'formula','task_type':'formula','bbox_2d':[0,i,100,i+1]} for i in range(3)]
    def test_every_formula_must_survive_not_just_one(self):
        d=self.rows();r=[dict(x,content='x^2') for x in d]
        self.assertEqual(len(c.account_regions(d,r,{})),3)
        with self.assertRaises(ValueError):c.account_regions(d,r[:1],{})
    def test_unmapped_reference_and_formula_fail_preflight(self):
        labels={'5':'formula','2':'aside_text','18':'reference'}
        cfg=c.glm_config('/x');self.assertEqual(len(c.validate_routes(labels,cfg)),3)
        cfg['pipeline']['layout']['label_task_mapping']['formula'].remove('formula')
        with self.assertRaises(ValueError):c.validate_routes(labels,cfg)
    def test_assets_retained_and_ambiguous_identity_rejected(self):
        d=[{'index':0,'label':'chart','task_type':'skip','bbox_2d':[0,0,1,1]}];r=[dict(d[0],content='')]
        with self.assertRaises(ValueError):c.account_regions(d,r,{})
        ledger=c.account_regions(d,r,{0:'original.png'});self.assertIn('original.png',c.faithful_export(ledger))
        with self.assertRaises(ValueError):c.account_regions(d,r+r,{0:'original.png'})
    def test_raw_region_export_accounts_for_sdk_merges(self):
        d=self.rows();r=[dict(x,content='x_'+str(x['index'])) for x in d]
        out=c.faithful_export(c.account_regions(d,r,{}))
        for i in range(3):self.assertIn('x_'+str(i),out)
    def test_inferred_chart_tables_not_faithful_text(self):
        blocks=[{'type':'chart','content':'INFERRED NUMBERS'},{'type':'table','content':'ACTUAL TABLE'}]
        rows,inferred=c.pro_export(blocks,{0:'assets/chart.png'})
        self.assertNotIn('INFERRED',str(rows));self.assertIn('ACTUAL TABLE',str(rows));self.assertEqual(inferred[0]['status'],'engine_inferred_not_printed_source')
        with self.assertRaises(ValueError):c.pro_export(blocks,{})
    def test_partition_no_gaps_or_duplicate_ownership(self):
        text='Introduction\nCase 13.\nmath\nCase 19. McNolty\nreferences'
        units=c.checked_partition(text,[r'Case 13\.',r'Case 19\.'])
        self.assertEqual(''.join(x['text'] for x in units),text)
        with self.assertRaises(ValueError):c.checked_partition(text+'\nCase 13.',[r'Case 13\.'])
    def test_finished_resume_is_noop(self):
        from scripts import extraction_followup as f
        with patch.object(f,'verify',return_value={'status':f.TERMINAL}),patch.object(f.subprocess,'run',side_effect=AssertionError('host operation')),patch.object(f.sys,'argv',['followup','resume','--run','/tmp/finished']):f.main()
    def test_no_download_branch_in_controller(self):
        from scripts import extraction_followup as f
        self.assertNotIn("'download'",Path(f.__file__).read_text())

if __name__=='__main__':unittest.main()
