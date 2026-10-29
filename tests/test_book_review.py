"""Completed owned-page adapter, recovery staging, and conservative assembly mocks."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import test_cli as cli_tests
from probe import book_review as book, experiment as ex, evaluation_export as export
from probe.common import atomic_json,read_json,sha,fingerprint,files_manifest


class FakeVisual:
    def __init__(self,endpoint,model=None,**kwargs):self.model=model
    def discover_model(self,out):return {'selected_model':self.model}
    def chat(self,messages,out,label,**kwargs):
        d=json.loads(messages[0]['content'][0]['text'].split('SELECTED DATA:\n',1)[1])
        v={'page_id':d['page_id'],'complete':True,'reviewed_block_ids':[b['id'] for b in d['blocks']],'proposals':[]}
        if d.get('scope')=='page_omissions':v.update(unit_id=d['unit_id'],scope=d['scope'],missing_content_checked=True)
        else:v.update(scope='selected_blocks',proposal_categories=[],observations=[])
        # Historical binding verification consumes raw transport evidence too.
        folder=out/'attempts/fake';folder.mkdir(parents=True)
        atomic_json(folder/'record.json',{'http_status':200,'latency_seconds':0})
        atomic_json(folder/'response.raw',{'model':self.model,'choices':[{'finish_reason':'stop','message':{'content':json.dumps(v)}}]})
        return {'actual_model':self.model,'finish_reason':'stop','content':json.dumps(v),'latency_seconds':0,'usage':{}}


class BookAdapterTests(unittest.TestCase):
    def setUp(self):
        self.factory=cli_tests.CLIIntegrationTests(methodName='test_windows_own_each_selected_page_once_and_keep_real_adjacent_context')
        self.factory.setUp();self.addCleanup(self.factory.doCleanups)
        _,self.conversion=self.factory._convert(isolation='none');self.root=self.factory.root
        self.addCleanup(patch.stopall)
        patch.object(book,'ROOT',self.root).start()
        patch('probe.experiment.converter_idle',return_value={'owned_converter_pids':[]}).start()
        patch.dict(book.LIMITS,{'page_max_edge':120,'crop_max_edge':160}).start()
        state=read_json(self.conversion/'state.json');self.record=state['settings']['sources']['paper'];self.pages=[]
        for rec in state['units'].values():
            for m in read_json(self.conversion/rec['attempt']/'page-map.json'):
                if not m['owner']:continue
                n=m['selected_page'];block={'id':f'paper-p{n:04d}:b0','reading_order':0,'source_block_index':0,
                    'kind':'text','bbox':[.1,.1,.9,.3],'native':{'type':'text','content':f'Complete paragraph {n}. Let x be real. Formula x = x. Conditions and references remain.'}}
                blocks=[block] if n!=11 else []
                p={'source_id':'paper','page_id':f'paper-p{n:04d}','page':m,'blocks':blocks,'source_attempt':rec['attempt'],
                    'coordinate_system':'normalized source page','unit':'owned'}
                self.pages.append(p)
                atomic_json(self.conversion/rec['attempt']/'output/middle_json.json',{})
        patch.object(book,'saved_pages',return_value=self.pages).start()

    def prepare(self):
        result=book.prepare(self.conversion,'paper',gate_first=1,gate_count=1,recovery_calls=4,hours=1)
        return Path(result['preview']),Path(result['run'])

    def ready(self,preview):
        out=self.root/'ready';out.mkdir();m=read_json(preview/'preview.json')
        atomic_json(out/'readiness.json',{'config':m['config'],'text':'passed','vision':'qualified','finished_at':ex.now()});ex.seal(out);return out

    def test_all_registered_pages_without_100_page_limit_unique_ownership(self):
        record={'pages':210,'original_pages':list(range(1,211))};pages=[]
        for n in range(1,211):pages.append({'source_id':'gatheral','page':{'owner':True,'selected_page':n,'original_physical_page':n},'blocks':[{'id':f'gatheral-p{n:04d}:b0'}]})
        self.assertEqual(len(book.owned_scope(pages,'gatheral',record)),210)
        with self.assertRaisesRegex(ValueError,'duplicate'):book.owned_scope(pages+[pages[0]],'gatheral',record)
        with self.assertRaisesRegex(ValueError,'Missing'):book.owned_scope(pages[:-1],'gatheral',record)
        with self.assertRaises(ValueError):book.owned_scope(pages,'all',record)

    def test_preparation_complete_targets_omissions_and_unchanged_raw_paragraph(self):
        before=files_manifest(self.conversion);preview,run=self.prepare();m,u=ex.verify_preview(preview)
        self.assertEqual(len(u),21);self.assertEqual(sum(x['kind']=='omission' for x in u),11)
        self.assertEqual(m['limits']['baseline_calls'],21)
        d=read_json(preview/u[0]['data']);self.assertEqual(d['blocks'][0],self.pages[0]['blocks'][0])
        self.assertEqual(d['draft_by_block'][0]['latex'],self.pages[0]['blocks'][0]['native']['content'])
        self.assertNotIn('response_format',read_json(preview/u[0]['request']))
        self.assertEqual(files_manifest(self.conversion),before)
        broken=copy.deepcopy(u);broken.append(copy.deepcopy(u[0]))
        with self.assertRaisesRegex(ValueError,'exactly once'):book.validate_preparation(preview,m,broken)

    def test_incomplete_conversion_refused_before_consuming_output(self):
        p=self.conversion/'state.json';s=read_json(p);s['status']='running';atomic_json(p,s)
        with self.assertRaisesRegex(ValueError,'fully completed'):self.prepare()
        book.saved_pages.assert_not_called()

    def test_missing_bbox_retains_target_and_blocks_gate_coverage(self):
        self.pages[0]['blocks'][0]['bbox']=None
        preview,run=self.prepare();m,u=ex.verify_preview(preview)
        self.assertEqual(len(u),21)
        self.assertIn('No verified source bbox',u[0]['unavailable'])
        s=read_json(run/'state.json')
        self.assertEqual(s['units'][u[0]['id']]['status'],'unavailable')
        coverage=book.coverage_summary(preview,s,u)
        self.assertEqual(coverage[0]['unchecked_blocks'],['paper-p0001:b0'])
        self.assertEqual(read_json(preview/u[0]['data'])['blocks'],self.pages[0]['blocks'])

    def test_slice_gate_expands_same_run_without_replaying_completed_calls(self):
        preview,run=self.prepare();ready=self.ready(preview)
        with patch('builtins.print'):
            code=ex.execute(self.root,run,stage='gate',readiness=ready,compiler_image=book.QUALIFIED_IMAGE,client_factory=FakeVisual)
        s=read_json(run/'state.json');self.assertEqual(code,0);self.assertTrue(s['gate']['passed']);self.assertEqual(len(s['calls']),2)
        first=copy.deepcopy(s['calls']);first_bytes=files_manifest(run/'calls')
        with patch('builtins.print'):
            code=ex.execute(self.root,run,stage='continue',readiness=ready,resume=True,compiler_image=book.QUALIFIED_IMAGE,client_factory=FakeVisual)
        s=read_json(run/'state.json');self.assertEqual(code,0);self.assertEqual(s['status'],'completed');self.assertEqual(len(s['calls']),21)
        self.assertEqual(s['calls'][:2],first)
        for entry in first_bytes:self.assertEqual(sha(run/'calls'/entry['path']),entry['sha256'])
        dispositions=self.root/'dispositions.json';atomic_json(dispositions,export.disposition_template(run))
        candidate=self.root/'candidate';export.build_candidate(preview,run,candidate,dispositions=dispositions)
        inv=read_json(candidate/'inventory.json');self.assertEqual(len(inv),10)
        self.assertEqual(inv[0]['after'],self.pages[0]['blocks'][0]['native']['content'])
        self.assertEqual(read_json(candidate/'provenance.json')['compilation'],'unavailable')
        self.assertEqual(len(read_json(candidate/'review-coverage.json')),11)
        self.assertTrue((candidate/'bibliography.json').is_file())
        with self.assertRaisesRegex(ValueError,'already exists'):self.prepare()

    def test_omission_insertion_is_deferred_not_compiled_or_applied(self):
        d={'unit_id':'u','page_id':'p','scope':'page_omissions','blocks':[],'context_blocks':[]}
        v={'unit_id':'u','page_id':'p','scope':'page_omissions','complete':True,'missing_content_checked':True,'reviewed_block_ids':[],
            'proposals':[{'block_ids':[],'region_bbox':[0,.1,.5,.2],'suggested_latex':'Missing text','issue':'Omission','uncertain':False}]}
        result=ex.finish_completion({'actual_model':'m','finish_reason':'stop','content':json.dumps(v)},{'kind':'omission'},d,'m',self.root,compiler_image=book.QUALIFIED_IMAGE)
        self.assertEqual(result['status'],'completed');self.assertEqual(result['compilation'][0]['status'],'not_attempted_deferred_insertion')
        v['proposals'][0]['block_ids']=['unknown']
        with self.assertRaises(ValueError):book.validate_omissions(v,d)

    def test_full_paragraph_formula_only_proposal_deferred_preserves_original(self):
        block=self.pages[0]['blocks'][0];item={'id':'p','proposal':{'block_ids':[block['id']],'suggested_latex':r'\[x=x\]',
            'fragment_kind':'latex_fragment','change_kind':'ocr_repair','depends_on':[],'uncertain':False}}
        decision={'p':{'evidence_sha256':fingerprint(item),'disposition':'deferred','whole_block_preserved':False,'reason':'Formula-only replacement would delete surrounding paragraph'}}
        edits,records=export.edits_for([block],[item],decision)
        self.assertFalse(edits);self.assertEqual(export.draft(block)['text'],block['native']['content'])
        self.assertIn('Formula-only',records[0]['reason'])

    def test_compiler_binding_and_source_changes_fail_closed(self):
        preview,run=self.prepare();ready=self.ready(preview)
        with self.assertRaisesRegex(ValueError,'compiler image'):
            ex.execute(self.root,run,stage='gate',readiness=ready,compiler_image=None,client_factory=FakeVisual)
        (self.conversion/'state.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Changed consumed input'):
            ex.execute(self.root,run,stage='gate',readiness=ready,compiler_image=book.QUALIFIED_IMAGE,client_factory=FakeVisual)


if __name__=='__main__':unittest.main()
