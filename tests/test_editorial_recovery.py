"""Focused repair regressions. No sockets, Docker, services or model calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
from probe import chapter_inputs as ci, chapter_editorial as edit, chapter_glm as rt, editorial_recovery as recovery
from probe.common import read_json, atomic_json, writer_lock
from probe.local_model import LocalClient
from probe.saved_pages import page_blocks
from scripts import editorial_chapters as controller
from test_simple_chapter_continuous import FakeConnection, FakeResponse, event

class BlankClassificationTests(unittest.TestCase):
    def test_notice_preserved_physical_not_local_or_selected_index(self):
        blocks=[{'kind':'text','native':{'type':'text','content':'This page intentionally left blank'}}]
        pages=[{'page':{'original_physical_page':217,'selected_page':117,'local_page_idx':1},'blocks':copy.deepcopy(blocks)}]
        record={'source_id':'bergomi','source_sha256':'h','pages':[{'physical_pdf_page':217,'classification':'intentional_blank_with_notice',
                    'recognized_content':[{'type':'text','text':'This page intentionally left blank'}]}]}
        ci.classify_pages(pages,record,'bergomi','h')
        self.assertEqual(pages[0]['blocks'],blocks)
        self.assertEqual(pages[0]['page']['classification'],'intentional_blank_with_notice')
        with self.assertRaises(ValueError):ci.classify_pages(pages,record,'gatheral','h')
        with self.assertRaises(ValueError):ci.classify_pages(pages,record,'bergomi','changed')
        pages[0]['blocks'].append({'kind':'equation','native':{'type':'equation','content':'x=1'}})
        with self.assertRaisesRegex(ValueError,'physical 217'):ci.classify_pages(pages,record,'bergomi','h')
        with self.assertRaises(ValueError):page_blocks({'page_idx':0})
        with self.assertRaises(ValueError):page_blocks({'blocks':[{}]},verified_blank=True)
    def test_recorded_classification_is_nine_notices_not_cleared_blocks(self):
        p=Path(__file__).resolve().parents[1]/'docs/source-provenance/bergomi-page-classification-20261028.json'
        c=read_json(p);self.assertEqual([x['physical_pdf_page'] for x in c['pages']],[5,119,149,217,323,373,407,437,469])
        self.assertEqual(c['verified_empty_pages'],[])
        self.assertTrue(all(x['recognized_content'] for x in c['pages']))

class CoverageNotesTests(unittest.TestCase):
    def test_target_span_separate_from_parent_context(self):
        data={'pages':[{'page':{'original_physical_page':n}} for n in range(118,132)],'blocks':[
            {'id':'a','kind':'text','page':{'original_physical_page':118}},
            {'id':'b','kind':'equation','page':{'original_physical_page':120}},
            {'id':'c','kind':'equation','page':{'original_physical_page':131}}]}
        t={'section':{'blocks':['a','b']}}
        c=recovery.section_coverage(t,data)
        self.assertEqual(c['target_physical_pages'],[118,120]);self.assertEqual(c['parent_chapter_pages'],list(range(118,132)))
        self.assertNotIn(131,c['target_physical_pages']);self.assertEqual(c['target_span']['last'],'b')
        with self.assertRaises(ValueError):recovery.section_coverage({'section':{'blocks':['a','a']}},data)
    def test_current_floor_supersedes_history_denominator_stays_open(self):
        old={'items':[{'id':'old-floor','text':'Annual floor unresolved','status':'open','category':'material'},
                      {'id':'G10-denominator','text':'Need contract','status':'open','category':'material'}]}
        raw='- **[G10-floor] Applied.** Twelve -1% monthly floors imply a -12% bound; current TeX uses at or below -12%.\n- **[G10-denominator] Unresolved.** Printed basket_i known; contract needed.\n- **Cosmetic:** harmless style.'
        new=recovery.latest_dispositions(old,raw,'g10',{'old-floor':['G10-floor']})
        self.assertEqual(len([x for x in new['items'] if 'G10-floor' in x['references']]),1)
        self.assertEqual(next(x for x in new['items'] if 'G10-floor' in x['references'])['status'],'applied_claim_unverified')
        self.assertEqual(next(x for x in new['items'] if 'G10-denominator' in x['references'])['status'],'open')
        self.assertEqual(len(new['history']),2);self.assertTrue(all(x['superseded_by'] for x in new['history']))
        self.assertFalse(any(x.get('independent_verification') for x in new['items']))
        self.assertEqual(old['items'][0]['status'],'open')
    def test_applied_heading_and_multiple_old_aliases_do_not_duplicate_latest(self):
        old={'items':[{'id':i,'text':'old','status':'open','category':'material'} for i in ['G5-hats','old-revert']]}
        new=recovery.latest_dispositions(old,'**Applied**\n- **[G5-hats] Codex.** Hat C/D now agree with the following definitions.\n**Unresolved**\n- **[G5-time]** Needs source assumptions.','g5',{'old-revert':['G5-hats']})
        self.assertEqual(len(new['items']),2);self.assertEqual(len(new['history']),2)
        self.assertEqual(new['items'][0]['status'],'applied_claim_unverified');self.assertEqual(new['items'][1]['status'],'open')
    def test_unaddressed_material_is_preserved_and_visible_note_not_duplicated(self):
        old=edit.notes_record('c','1. Sign uncertainty\nStatus: open')
        merged=edit.reconcile_notes(old,edit.notes_record('c','No material issues reported'))
        self.assertIn(old['items'][0],merged['items'])
        doc=r'\documentclass{article}\begin{document}\textbf{GLM correction [G10-floor].} Bound $-12\%$.\end{document}'
        item={'id':'new','references':['G10-floor'],'status':'applied_claim_unverified','text':'Bound','category':'material'}
        self.assertEqual(edit.annotate(doc,[item]),doc)

class EffortTransportTests(unittest.TestCase):
    def test_actual_runtime_to_http_body_high_max_and_none(self):
        for effort in ('high','max','none'):
            with self.subTest(effort=effort),tempfile.TemporaryDirectory() as td:
                root=Path(td);wire=event({'content':'Complete answer'},finish='stop')+b'data: [DONE]\n\n'
                connection=FakeConnection(FakeResponse([wire]))
                def factory(*a,**kw):
                    c=LocalClient(*a,**kw);c.model='glm53-regular';c._connection=lambda:(connection,urlsplit(c.base_url))
                    c.discover_model=lambda dest:None
                    c.chapter_health=lambda dest:({'max_seq_len':1048576},{})
                    return c
                state={'chapter_contract':edit.VERSION,'timing_policy':'manual_only','execution_limits':{'calls':10,'attempts_per_unit':1},
                       'first_dispatch':None,'calls':[],'connection_failures':0}
                body=edit.request('Exact primary','Exact secondary',reasoning_effort=effort)
                with patch('probe.chapter_protocol.health_capacity',return_value=1048576):
                    result,_=rt.invoke(root,state,'convert',body,client_factory=factory)
                self.assertEqual(connection.sent,body)
                self.assertEqual(read_json(root/'calls/call-001/settings.json')['requested_reasoning_effort'],effort)
                self.assertEqual(result,'Complete answer')
    def test_invalid_rejected_and_default_max(self):
        self.assertEqual(edit.request('p','s')['reasoning_effort'],'max')
        for value in ('bogus','xhigh',None,True):
            with self.assertRaises(ValueError):edit.request('p','s',reasoning_effort=value)
    def test_pilot_scope_resume_allowance_no_hidden_dispatch(self):
        s={'chapter_contract':edit.VERSION,'timing_policy':'manual_only','execution_limits':{'calls':98,'attempts_per_unit':1},
           'first_dispatch':0,'calls':[{'id':'call-001','parent':'old'}],
           'pilot':{'inherited_calls':1,'readiness_limit':1,'task_ids':['a','b']}}
        rt.reserve(s,'a','h');rt.reserve(s,'readiness','r')
        resumed=json.loads(json.dumps(s))
        for parent in ('a','readiness','bergomi'):
            with self.assertRaises(rt.StopRun):rt.reserve(resumed,parent,'h')
        rt.reserve(resumed,'b','h');self.assertEqual(len(resumed['calls']),4)

class FinalStatusTests(unittest.TestCase):
    def test_bundle_observes_error_state_and_stage_before_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);s={'status':'stopped_error','stage':'bergomi_chapter_preparation','diagnostic':'test failure'}
            def report(run,state):self.assertEqual(read_json(run/'state.json'),state)
            def bundle(run,state):
                self.assertEqual(read_json(run/'state.json')['status'],'stopped_error');return r/'inspection.zip'
            with writer_lock(r),patch.object(controller,'report',side_effect=report),patch.object(controller,'bundle',side_effect=bundle):controller.finalize(r,s)
            with writer_lock(r):self.assertEqual(read_json(r/'last-inspection.json')['stage'],'bergomi_chapter_preparation')

    def test_worker_preparation_exception_releases_locks_and_bundles_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';run.mkdir()
            state={'status':'prepared_offline','calls':[],'historical_calls':[],'historical_request_seconds':0,
                   'current_versions':{},'versions':{},'tasks':[],'accuracy':{},'scope':'test','bergomi_status':'awaiting'}
            with patch.object(controller,'ROOT',root),patch.object(controller,'verify',return_value=state),\
                 patch.object(controller.os,'dup2'),patch.object(controller,'converter_idle'),\
                 patch.object(controller.runtime,'check_other_jobs'),patch.object(controller.runtime,'readiness'),\
                 patch.object(controller,'assemble'),patch.object(controller,'prepare_bergomi',side_effect=ValueError('mapped page conflict')):
                with self.assertRaisesRegex(ValueError,'mapped page conflict'):controller.worker(run)
            saved=read_json(run/'state.json')
            self.assertEqual(saved['status'],'stopped_error');self.assertEqual(saved['bergomi_status'],'chapter_preparation_failed')
            self.assertEqual(saved['stage'],'bergomi_chapter_preparation')
            import zipfile
            with zipfile.ZipFile(read_json(run/'last-inspection.json')['path']) as z:
                self.assertEqual(json.loads(z.read('state.json'))['status'],'stopped_error')
                self.assertEqual(json.loads(z.read('summary.json'))['diagnostic'],'ValueError: mapped page conflict')
            with writer_lock(root),writer_lock(run):pass

class EditionGapTests(unittest.TestCase):
    def test_missing_section_appears_between_its_neighbors_with_editable_sources(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);state={'tasks':[],'versions':{},'current_versions':{},'scope':'test'}
            for n in range(1,12):
                folder=r/'inputs'/f'gatheral-{n:02d}';folder.mkdir(parents=True)
                data={'pages':[{'page':{'original_physical_page':p}} for p in (118,119,120)],
                      'blocks':[{'id':str(p),'kind':'equation','page':{'original_physical_page':p}} for p in (118,119,120)]}
                atomic_json(folder/'native.json',data);atomic_json(folder/'assets.json',[])
            for n in range(1,4):
                key=f'gatheral-07-s{n:02d}';state['tasks'].append({'key':key,'source_key':'gatheral-07','phase':'convert',
                    'status':'no_final_answer' if n==2 else 'conversion_completed','section':{'blocks':[str(117+n)],'title':f'Section {n}'}})
                if n!=2:
                    controller.remember(r,state,key,'saved',r'\documentclass{article}\begin{document}Exact unchanged $x$.\end{document}',{})
                    state['current_versions'][key]='saved'
            (r/'source-supplement').mkdir();(r/'source-supplement/gatheral-front-blank-index.pdf').write_bytes(b'saved supplement')
            out=controller.assemble(r,state)
            master=(out/'master.tex').read_text()
            self.assertLess(master.index('parts/gatheral-07-s01.tex'),master.index('Missing gatheral-07-s02'))
            self.assertLess(master.index('Missing gatheral-07-s02'),master.index('parts/gatheral-07-s03.tex'))
            parts=read_json(out/'coverage.json')['delivered_parts'];row=next(p for p in parts if p['key']=='gatheral-07-s01')
            self.assertEqual(row['target_physical_pages'],[118]);self.assertEqual(row['parent_chapter_pages'],[118,119,120])
            self.assertIn('Exact unchanged $x$',(out/'chapters/gatheral-07-s01/document.tex').read_text())

class InheritedReportingTests(unittest.TestCase):
    def test_linked_preparation_does_not_call_inherited_work_new_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);state={'status':'prepared_offline','calls':[{'id':'call-001','inherited_from':'parent','elapsed_seconds':9}],
                'historical_calls':[{'id':'older'}],'historical_request_seconds':8,'tasks':[],'versions':{},'current_versions':{},
                'scope':'pilot only','bergomi_status':'prepared_completed_OCR','accuracy':{}}
            controller.report(r,state);summary=read_json(r/'summary.json')
            self.assertEqual(summary['new_calls'],0);self.assertEqual(summary['inherited_parent_calls'],1)
            self.assertEqual(summary['cumulative_calls'],2);self.assertEqual(summary['request_seconds_new'],0)

    def test_metrics_do_not_confuse_utf8_bytes_with_final_characters(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);folder=root/'calls/call-001';folder.mkdir(parents=True)
            (folder/'answer.txt').write_text('η²')
            row=recovery.call_metrics(root,{'id':'call-001','status':'completed_response'})
            self.assertEqual(row['answer_characters'],2)
            self.assertIsNone(row['other_completion_tokens'])

class PhaseConfigurationTests(unittest.TestCase):
    def test_distinct_sealed_phase_settings_reach_generated_bodies(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);p=r/'inputs/book-01';p.mkdir(parents=True)
            (p/'source.tex').write_text('Complete primary');(p/'secondary.txt').write_text('Complete secondary')
            state={'phase_efforts':{'convert':'low','critic':'max'},'versions':{},'current_versions':{},'accuracy':{}}
            controller.remember(r,state,'book-01','initial',r'\documentclass{article}\begin{document}Exact draft\end{document}',{})
            state['current_versions']['book-01']='initial'
            task={'source_key':'book-01','key':'book-01','phase':'convert','section':None,'context':''}
            self.assertEqual(controller.body_for(r,state,task)['reasoning_effort'],'low')
            task['phase']='critic';body=controller.body_for(r,state,task)
            self.assertEqual(body['reasoning_effort'],'max');self.assertIn('Exact draft',body['messages'][0]['content'])
            state['phase_efforts']['critic']='unsupported'
            with self.assertRaises(ValueError):controller.body_for(r,state,task)
