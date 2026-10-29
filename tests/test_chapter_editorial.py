"""Offline editorial derivative regressions; recorded examples are development data."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from probe import chapter_editorial as edit, chapter_accuracy, chapter_glm as runtime, chapter_protocol, tex_compile
from probe.common import atomic_json, read_json, fingerprint, sha
from scripts import editorial_chapters as run
from scripts import simple_chapter_glm as simple

TEX=r'\documentclass{article}\begin{document}Complete paragraph. $x=1$.\end{document}'
ROOT=Path(__file__).resolve().parents[1]

class SelectionNotesTests(unittest.TestCase):
    def test_findings_only_retains_first_draft_and_review_status(self):
        state={'versions':{'gatheral-09':{'first-glm':{'path':'initial.tex'}}},'current_versions':{},
               'tasks':[{'key':'gatheral-09','phase':'review','status':'complete_response','revised_tex':{'status':'not_supplied'}}]}
        self.assertEqual(edit.current_version(state,'gatheral-09'),('first-glm',{'path':'initial.tex'}))
        self.assertEqual(state['tasks'][0]['status'],'complete_response')
    def test_fenced_markdown_and_individual_resolved_claims(self):
        answer='Review outcome: unchanged.\n## Updated accuracy notes\n```markdown\n# Accuracy notes\n1. Missing factor restored — resolved.\nEvidence: multiplication by the omitted factor.\n2. Source ambiguity remains open.\nStatus: requires-source-inspection\n```\n'
        document,info=chapter_accuracy.envelope(answer,simple.extract_document)
        self.assertFalse(document and chapter_accuracy.complete_document(document))
        text,status=edit.notes_text(answer,info);self.assertEqual(status,'captured')
        record=edit.notes_record('g09',text)
        self.assertTrue(any(i['status'] in ('resolved_claim_unverified','applied_claim_unverified') for i in record['items']))
        self.assertTrue(any(i['status']=='open' for i in record['items']))
    def test_bibliography_fields_do_not_become_whole_open_log(self):
        text='**M1. Breve correction.**\n- **Evidence:** source breve.\n- **Correction:** caron -> breve.\n- **Status:** resolved.\n\n- **g-bib-initial-123 (scope).** 76 entries. **Status: resolved/verified.**\n- **g-bib-initial-234 (URL).** glyph uncertain. **Status: open.**'
        result=edit.notes_record('g-bib',text)
        self.assertEqual(len(result['items']),3)
        self.assertEqual(result['items'][0]['status'],'applied_claim_unverified')
        self.assertEqual(result['items'][1]['category'],'contextual_observation')
        self.assertEqual(result['items'][2]['status'],'open')
        self.assertFalse(any(i['independent_verification'] for i in result['items']))
    def test_missing_and_failed_notes_are_not_no_issues(self):
        self.assertEqual(edit.notes_text('')[1],'unavailable')
        r=edit.notes_record('c','partial issue',complete=False)
        self.assertEqual(r['capture_status'],'review_incomplete')
    def test_unaddressed_issue_survives_no_error_claim(self):
        prior=edit.notes_record('c','1. Sign question\nStatus: open')
        new=edit.notes_record('c','No new material issues.')
        merged=edit.reconcile_notes(prior,new)
        self.assertEqual(merged['items'][0],prior['items'][0])
    def test_annotation_visible_and_original_preserved(self):
        original=TEX;entry={'id':'G-test','status':'unresolved','attribution':'GLM','text':'Source x sign is uncertain; see PDF 3.'}
        out=edit.annotate(TEX,[entry])
        self.assertEqual(original,TEX)
        self.assertIn(r'\textbf{GLM unresolved issue [G-test]',out)
        self.assertIn('Source x sign',out)
        self.assertEqual(out.count(r'\begin{document}'),1)
        self.assertIn(r'\ensuremath{\beta}',edit.tex_escape('β'))

class PlanTests(unittest.TestCase):
    def block(self,i,text,kind='paragraph'):
        return {'id':f'b{i}','kind':kind,'native':{'content':text,'level':2},'tex':text,
                'page':{'selected_page':i+1,'original_physical_page':i+1,'owner':True}}
    def test_section_boundaries_keep_proof_and_one_owner(self):
        bs=[self.block(0,'CHAPTER','doc_title'),self.block(1,'1.1 First','paragraph_title'),self.block(2,'Theorem statement'),
            self.block(3,'Proof'),self.block(4,'Intermediate detail','paragraph_title'),self.block(5,'Proof end □'),
            self.block(6,'1.2 Second','paragraph_title'),self.block(7,'last equation')]
        groups=edit.section_groups({'blocks':bs})
        self.assertEqual([b for g in groups for b in g['blocks']],[b['id'] for b in bs])
        self.assertEqual(len(groups),2)
        self.assertIn('Proof end',groups[0]['text']);self.assertIn('last equation',groups[1]['text'])
    def test_prompt_both_sources_no_block_contract(self):
        q=edit.request('PRIMARY TAIL','SECONDARY Chapter 5 locator',draft=TEX,notes='Open sign question',section='A whole proof')
        t=q['messages'][0]['content']
        for x in ('PRIMARY TAIL','Chapter 5 locator',TEX,'Open sign question',edit.POLICY):self.assertIn(x,t)
        self.assertEqual(q['max_tokens'],131072);self.assertTrue(q['stream'])
        self.assertNotIn('response_format',q);self.assertNotIn('% SRC',t)
        with self.assertRaises(chapter_protocol.ContextBudgetGap):chapter_protocol.budget(q,1000)
    def test_exact_edit_binding_and_unchanged_control(self):
        plan={'text_fingerprint':fingerprint(TEX),'edits':[{'id':'x','old':'$x=1$','new':'$x=2$'}]}
        self.assertEqual(edit.apply_edits(TEX,plan),TEX.replace('$x=1$','$x=2$'))
        with self.assertRaises(ValueError):edit.apply_edits(TEX+' ',plan)
        plan['edits']=[];self.assertEqual(edit.apply_edits(TEX,plan),TEX)
    def test_recorded_mathematical_changes_and_locations(self):
        p=read_json(ROOT/'docs/gatheral-editorial-plan.json')['chapters']
        eta='\n'.join(e['new'] for e in p['gatheral-01']['edits'])
        self.assertIn(r'\phi ( S , \nu , t ) d t + \eta d Z',eta)
        self.assertIn(r"\alpha ' d t + \eta \beta",eta)
        self.assertNotIn(r'\eta \phi',eta)
        self.assertTrue(any('24\\%' in e['new'] and '2.88\\%' in e['new'] for e in p['gatheral-08']['edits']))
        self.assertTrue(any(r'$\leq-12\%$' in e['new'] for e in p['gatheral-10']['edits']))
        self.assertIn('PDF 153 / printed 122',str(p['gatheral-10']['findings']))
        self.assertIn('PDF 70 / printed 39',str(p['gatheral-03']['findings']))
        self.assertEqual(p['gatheral-postscript']['edits'],[])
    def test_bibliography_balanced_accents_preserved(self):
        t=r'\newcommand{\bibentry}[1]{#1}\bibentry{Dr\u{a}gulescu. 2002. A {nested} title.}\bibentry{. 2003. Title.}'
        rows=edit.bibliography_entries(t)
        self.assertEqual(len(rows),2);self.assertIn(r'\u{a}',rows[0]['text'])
        self.assertEqual(t[rows[1]['start']:rows[1]['end']],'. 2003. Title.')

class ExecutionTests(unittest.TestCase):
    def setup_run(self,p):
        folder=p/'inputs/gatheral-09';folder.mkdir(parents=True)
        (folder/'source.tex').write_text('Full chapter source');(folder/'secondary.txt').write_text('Full native PDF')
        atomic_json(folder/'assets.json',[])
        state={'status':'prepared','calls':[],'historical_calls':[{'id':'old'}],'historical_request_seconds':10,'scope':'test',
               'bergomi_status':'awaiting','versions':{},'current_versions':{},'accuracy':{},'connection_failures':0,'tasks':[]}
        run.remember(p,state,'gatheral-09','first-glm',TEX,{'test':True});state['current_versions']['gatheral-09']='first-glm'
        t={'id':'review','key':'gatheral-09','source_key':'gatheral-09','phase':'critic','status':'pending','context':'','section':None,'draft_label':None}
        state['tasks']=[t];return state,t
    def test_findings_only_critic_keeps_initial_and_is_reviewed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state,t=self.setup_run(p)
            def invoke(*args):return 'No material issues reported.',{'id':'call-001'}
            with patch.object(run,'compile_version'):
                run.task_once(p,state,t,invoke=invoke)
            self.assertEqual(t['status'],'critic_unchanged');self.assertEqual(state['current_versions']['gatheral-09'],'first-glm')
            self.assertEqual(run.bound_output(p,state,'gatheral-09','first-glm'),TEX)
    def test_failed_critic_preserves_original_and_no_replay(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state,t=self.setup_run(p)
            def invoke(*args):
                c={'id':'call-001','parent':'review','failure_kind':'truncation','error':'length','metadata':{}};state['calls'].append(c);return None,c
            run.task_once(p,state,t,invoke=invoke)
            self.assertEqual(t['status'],'truncation');self.assertEqual(run.bound_output(p,state,'gatheral-09','first-glm'),TEX)
            t['status']='pending'
            run.task_once(p,state,t,invoke=lambda *a:self.fail('No repeat'))
            self.assertEqual(t['status'],'interrupted_unresolved')
    def test_new_units_do_not_reset_historical_or_change_legacy_budget(self):
        state={'chapter_contract':edit.VERSION,'timing_policy':'manual_only','execution_limits':{'calls':3,'attempts_per_unit':1},'first_dispatch':None,'calls':[],
               'historical_calls':[{'id':f'old{i}'} for i in range(24)]}
        runtime.reserve(state,'new-unit','hash')
        with self.assertRaises(runtime.StopRun):runtime.reserve(state,'new-unit','hash')
        runtime.reserve(state,'readiness','r');runtime.reserve(state,'other','o')
        with self.assertRaises(runtime.StopRun):runtime.reserve(state,'third','o')
        self.assertEqual(len(state['historical_calls']),24);self.assertEqual(runtime.LIMITS['calls'],80)
    def test_original_scope_all_pages_and_no_klebaner(self):
        from probe.chapter_inputs import PARTS
        pages=[n for _,_,a,b in PARTS for n in range(a,b+1)]
        self.assertEqual(pages,list(range(1,211)))

@unittest.skipUnless(os.environ.get('PDF2TEX_COMPILER_IMAGE'),'Opt-in real isolated compiler only')
class RealAnnotationTests(unittest.TestCase):
    def test_visible_annotation_compiles_and_extracts(self):
        import fitz
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'compile'
            text=edit.annotate(TEX,[{'id':'G8-coupons','status':'applied_verified','attribution':'Codex','text':'Four coupons total 24 percent; error 2.88 percent.'}])
            result=tex_compile.compile_document(text,out,image=os.environ['PDF2TEX_COMPILER_IMAGE'],passes=2)
            self.assertTrue(result['compilation_claim'],result)
            with fitz.open(out/'document.pdf') as doc:extracted='\n'.join(p.get_text() for p in doc)
            self.assertIn('Codex editorial correction',extracted);self.assertIn('2.88',extracted)

if __name__=='__main__':unittest.main()

class SafetyAndIntegrationTests(unittest.TestCase):
    def test_unfinished_extraction_is_not_consumed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);r=p/'runs'/run.BERGOMI.name;r.mkdir(parents=True)
            atomic_json(r/'state.json',{'status':'running','units':{}})
            with patch.object(run,'converter_idle') as idle:
                self.assertEqual(run.extraction_complete(p),(False,'Bergomi extraction is running'));idle.assert_not_called()
    def test_completed_state_alone_cannot_allow_copyback(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);r=p/'runs'/run.BERGOMI.name;r.mkdir(parents=True)
            units={str(i):{'status':'completed','window':{'owned_start':i*8+1,'owned_end':min((i+1)*8,520)}} for i in range(65)}
            atomic_json(r/'state.json',{'status':'conversion_completed_unreviewed','units':units})
            with patch.object(run,'converter_idle',side_effect=ValueError('worker active')):
                self.assertFalse(run.extraction_complete(p)[0])
            with patch.object(run,'converter_idle',return_value={}):
                self.assertIn('exit record',run.extraction_complete(p)[1])
            exitpath=p/'runs/bergomi-operator/launch-test/exit.json';atomic_json(exitpath,{'exit_status':0,'run':str(r)})
            with patch.object(run,'converter_idle',return_value={}):self.assertTrue(run.extraction_complete(p)[0])
    def test_copyback_rejects_intervening_edit_and_new_collision(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('copyback',ROOT/'scripts/integrate-editorial-development.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);src=p/'dev';dst=p/'orig';src.mkdir();dst.mkdir()
            (src/'a.py').write_text('new');(dst/'a.py').write_text('old');original=sha(dst/'a.py')
            manifest={'files':{'a.py':{'before':original,'after':sha(src/'a.py')}}}
            m.validate_destinations(manifest,src,dst)
            (dst/'a.py').write_text('user change')
            with self.assertRaises(ValueError):m.validate_destinations(manifest,src,dst)
            self.assertEqual((dst/'a.py').read_text(),'user change')
            manifest['files']['a.py']['before']=None
            with self.assertRaises(ValueError):m.validate_destinations(manifest,src,dst)
    def test_context_gap_preserves_complete_section_and_unavailable_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);folder=p/'inputs/gatheral-test';folder.mkdir(parents=True)
            (folder/'source.tex').write_text('Full chapter '+'z'*1000000)
            (folder/'secondary.txt').write_text('native '+'x'*100000)
            atomic_json(folder/'secondary.json',{'pages':[{'physical_pdf_page':1,'printed_page':None,'text':'exact section native'},{'physical_pdf_page':2,'printed_page':None,'text':'other context'}]})
            bs=[{'id':'b1','kind':'paragraph','native':{'content':'Complete proof tail'},'tex':'Complete proof tail','page':{'selected_page':1,'original_physical_page':1}}]
            atomic_json(folder/'native.json',{'source':'gatheral','blocks':bs})
            t={'key':'gatheral-test-s01','source_key':'gatheral-test','phase':'convert','context':'','section':{'title':'Proof','text':'Complete proof tail','physical_pages':[1],'blocks':['b1']}}
            body=run.body_for(p,{},t)
            self.assertIn('Complete proof tail',body['messages'][0]['content']);self.assertIn('exact section native',body['messages'][0]['content'])
            self.assertIn('Other chapter sections are unavailable',body['messages'][0]['content'])
            self.assertFalse(t['context_scope']['full_chapter_context'])


class TransactionTests(unittest.TestCase):
    def test_failed_bergomi_preparation_cannot_change_live_schedule(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state={'tasks':[{'id':'done'}],'calls':[{'id':'already-consumed'}]}
            original=copy.deepcopy(state)
            def failed(path,temporary):
                temporary['tasks'].append({'id':'partial-new-unit'})
                raise ValueError('reader failure')
            with patch.object(run,'_prepare_bergomi',side_effect=failed):
                with self.assertRaises(ValueError):run.prepare_bergomi(p,state)
            self.assertEqual(state,original)


class AmbiguousNotesTests(unittest.TestCase):
    def test_ambiguous_document_is_raw_evidence_not_one_mathematical_issue(self):
        raw='```latex\n'+TEX+'\n```\n```latex\n'+TEX.replace('x=1','x=2')+'\n```'
        document,info=chapter_accuracy.envelope(raw,simple.extract_document)
        self.assertIsNone(document)
        text,status=edit.notes_text(raw,info)
        self.assertEqual(text,raw);self.assertEqual(status,'unavailable_unparsed')
        record=edit.notes_record('g',text,captured=status)
        self.assertEqual(record['items'],[]);self.assertEqual(record['raw_notes'],raw)
