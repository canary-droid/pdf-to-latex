"""Two-source simple chapters: evidence delivery, accuracy continuity and no replay."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fitz
from probe import chapter_sources as sources, chapter_accuracy as notes, chapter_protocol as protocol, chapter_glm as runtime
from probe.common import atomic_json, read_json, sha, fingerprint, files_manifest
from scripts import simple_chapter_glm as simple
from test_simple_chapter_continuous import DOC, FakeConnection, FakeResponse, event
from probe.local_model import LocalClient
from urllib.parse import urlsplit

FIXTURE=Path(__file__).parent/'fixtures/gatheral-ch2-locator.json'


class SecondaryTests(unittest.TestCase):
    def test_exact_owned_pages_once_with_isolated_numerals_and_labels(self):
        with fitz.open() as doc:
            for i in range(5):
                p=doc.new_page();p.insert_text((40,60),f'Original page {i+1}\n5\nChapter 5 of Named Author (1992)')
            data={'pages':[{'page_id':str(n),'page':{'owner':True,'selected_page':n-1,'original_physical_page':n}} for n in (2,3,4)]}
            mapping=sources.page_map(data,1);pages=sources.extract_pages(doc,mapping);text=sources.render_pages(pages)
            self.assertEqual([p['physical_pdf_page'] for p in pages],[2,3,4])
            self.assertEqual([p['printed_page'] for p in pages],[1,2,3])
            for p in pages:self.assertIn('\n5\n',p['text'])
            self.assertNotIn('Original page 1',text);self.assertNotIn('Original page 5',text)
            self.assertEqual(text.count('Physical PDF page'),3)
            data['pages'].append(data['pages'][0])
            with self.assertRaises(ValueError):sources.page_map(data,1)
            data['pages']=data['pages'][:1];data['pages'][0]['page']['owner']=False
            with self.assertRaises(ValueError):sources.page_map(data,1)

    def test_unknown_printed_labels_are_not_guessed(self):
        data={'pages':[{'page_id':'p1','page':{'owner':True,'selected_page':1,'original_physical_page':1}}]}
        self.assertIsNone(sources.page_map(data)[0]['printed_page'])

    def test_source_checked_locator_fixture_retained_in_both_request_phases(self):
        f=read_json(FIXTURE);native=f['native_text_footnote'];self.assertIn('Chapter 5 of Kloeden and Platen (1992)',native)
        initial=notes.capture('ch','initial',f['conversion_notes'])
        for draft in (None,DOC):
            body=sources.request(f['mineru_footnote'],native,draft,notes.render(initial,provenance=False))
            message=body['messages'][0]['content']
            self.assertIn(native,message);self.assertIn(f['mineru_footnote'],message)
            self.assertIn('Chapter 5 of Kloeden and Platen (1992)',message)
            self.assertNotIn(f['visual_check'],message)

    @unittest.skipUnless((simple.ROOT/'inputs/gatheral/source.pdf').is_file(),'Original PDF not available in portable checkout')
    def test_actual_pdf_locator_matches_saved_development_fixture(self):
        f=read_json(FIXTURE)
        with fitz.open(simple.ROOT/'inputs/gatheral/source.pdf') as doc:
            p=sources.extract_pages(doc,[{'physical_pdf_page':53,'printed_page':22,'selected_page':53,'page_id':'gatheral-p0053'}])[0]
        self.assertIn(f['native_text_footnote'],p['text'])

    def test_actual_outgoing_stream_payload_keeps_both_sources_draft_and_notes(self):
        with tempfile.TemporaryDirectory() as td:
            body=sources.request('PRIMARY EXACT','SECONDARY EXACT',DOC,'OPEN EXACT')
            response=FakeResponse([event({'content':'Done'},finish='stop')+b'data: [DONE]\n\n'])
            connection=FakeConnection(response)
            client=LocalClient(protocol.BASE_URL,protocol.MODEL,purpose='simple_chapter',timeout=None,max_tokens=131072)
            client.model=protocol.MODEL;client._connection=lambda:(connection,urlsplit(protocol.BASE_URL))
            client.chat(body['messages'],Path(td),'chapter',stream=True)
            self.assertEqual(connection.sent,body)
            for value in ('PRIMARY EXACT','SECONDARY EXACT',DOC,'OPEN EXACT'):self.assertIn(value,connection.sent['messages'][0]['content'])
            self.assertNotIn('reasoning_effort',connection.sent)

    def test_full_budget_unverified_offline_and_never_clips(self):
        primary='x'*100000;secondary='λ'*90000;draft=DOC*3;accuracy='Open issue'*100
        body=sources.request(primary,secondary,draft,accuracy);snapshot=copy.deepcopy(body)
        result=sources.budget_preview(body)
        self.assertEqual(result['fit'],'unverified_current_server_context')
        self.assertEqual(result['request_bytes'],len(json.dumps(body,ensure_ascii=False,allow_nan=False).encode()))
        self.assertEqual(result['combined_upper_estimate'],result['request_bytes']+4096+131072)
        with self.assertRaises(protocol.ContextBudgetGap):protocol.budget(body,100000)
        self.assertEqual(body,snapshot);self.assertEqual(body['max_tokens'],131072)


class AccuracyTests(unittest.TestCase):
    def test_tolerant_document_with_markdown_notes_and_other_fences(self):
        answer='Intro\n```latex\n'+DOC+'```\n## Accuracy notes\nMissing assumption.\n```text\nEvidence excerpt\n```\n'
        draft,info=notes.envelope(answer,simple.extract_document)
        self.assertEqual(draft,DOC);text,status=notes.outside_notes(answer,info)
        self.assertIn('Missing assumption',text);self.assertEqual(status,'captured')
        bad=answer+'```latex\n'+DOC+'```\n'
        self.assertIsNone(notes.envelope(bad,simple.extract_document)[0])
        incomplete_notes='```latex\n'+DOC+'```\nNotes in an unclosed formatting fence:\n```markdown\nMissing reference.'
        self.assertEqual(notes.envelope(incomplete_notes,simple.extract_document)[0],DOC)

    def test_unfenced_complete_tex_and_notes_are_separate_without_edits(self):
        answer='Here it is\n'+DOC+'\nAccuracy notes: Missing hypothesis.'
        draft,info=notes.envelope(answer,simple.extract_document)
        self.assertEqual(draft,DOC.rstrip('\n'));self.assertIn('Missing hypothesis',notes.outside_notes(answer,info)[0])

    def test_missing_unparsed_and_no_issues_are_distinct(self):
        a=notes.capture('ch','initial','',capture_status='unavailable')
        b=notes.capture('ch','initial','No material issues reported.')
        c=notes.capture('ch','critic','Something difficult is discussed without recognizable note structure.')
        self.assertEqual(a['notes_status'],'unavailable');self.assertEqual(b['notes_status'],'no_material_issues_reported_by_model')
        self.assertEqual(c['notes_status'],'captured_unparsed');self.assertTrue(c['issues'])
        self.assertIn('does not mean no issues',notes.render(a))

    def test_unmentioned_issue_and_unsupported_fixed_claim_remain_open(self):
        initial=notes.capture('ch','initial','- Missing reference locator.')
        for answer in ('No material issues reported.',f"Resolves: {initial['issues'][0]['id']}\nStatus: resolved\nFixed it."):
            merged=notes.reconcile(initial,notes.capture('ch','critic',answer),sources=['Source'],before=DOC,after=DOC)
            self.assertIn(initial['issues'][0]['id'],merged['open_issues'])

    def test_source_supported_edit_resolution_requires_exact_quote_and_actual_revision(self):
        initial=notes.capture('ch','initial','- Missing reference locator.');ident=initial['issues'][0]['id']
        entry=f'Resolves: {ident}\nStatus: resolved\nOrigin: extraction\nSource quote: Chapter 5 of Named Author\nOld: Chapter ...\nNew: Chapter 5\nEvidence: verbatim native reference.'
        latest=notes.capture('ch','critic',entry)
        for source,after,closed in [('Chapter 5 of Named Author','Chapter 5 of Named Author',True),('different','Chapter 5 of Named Author',False),('Chapter 5 of Named Author','Chapter ... of Named Author',False),('Chapter 5 of Named Author',None,False),('Chapter 5 of Named Author','Chapter 5 in a different location',False)]:
            merged=notes.reconcile(initial,latest,sources=[source],before='Chapter ... of Named Author',after=after)
            self.assertEqual(ident not in merged['open_issues'],closed)
        self.assertEqual(initial['issues'][0]['status'],'open')

    def test_duplicate_group_and_positive_notes_do_not_hide_meaningful_updates(self):
        self.assertEqual(notes.category('- **Footnote:** The named reference was attached to its marker.'),'presentation_or_positive')
        self.assertEqual(notes.category('- **Footnotes:** Scrambled fragments were reassembled.'),'accuracy')
        initial=notes.capture('ch','initial','- Missing sign.\n- Missing sign.\n- **Numbering:** Tags kept unchanged.')
        self.assertEqual(len(initial['issues']),2);self.assertEqual(initial['issues'][0]['duplicate_occurrences'],2)
        rendered=notes.render(initial);self.assertIn('<details>',rendered)
        latest=notes.capture('ch','critic',f"Issue {initial['issues'][0]['id']}: evidence still requires source inspection.")
        combined=notes.reconcile(initial,latest,sources=['s'],before=DOC)
        self.assertIn('requires source inspection',notes.render(combined))
        self.assertEqual(len(combined['open_issues']),1)

    def test_truncated_notes_never_close_issues_or_become_clean_assessment(self):
        initial=notes.capture('ch','initial','- Missing hypothesis.')
        partial=notes.capture('ch','critic','No material issues reported.',complete=False)
        merged=notes.reconcile(initial,partial,sources=[''],before=DOC)
        self.assertEqual(merged['notes_status'],'review_incomplete');self.assertTrue(merged['open_issues'])


class WorkflowTests(unittest.TestCase):
    def setup_run(self,root,key='gatheral-01'):
        folder=root/'inputs'/key;folder.mkdir(parents=True);(folder/'source.tex').write_text('PRIMARY')
        (folder/'secondary.txt').write_text('SECONDARY');atomic_json(folder/'assets.json',[])
        (root/'first.tex').write_text(DOC)
        initial,hashes=notes.save_initial(root,key,'- Missing hypothesis.',origin={'kind':'synthetic initial'})
        conversion={'id':key+'/convert','key':key,'phase':'convert','status':'complete_response','output':'first.tex','output_sha256':sha(root/'first.tex')}
        review={'id':key+'/review','key':key,'phase':'review','status':'pending'}
        state={'tasks':[conversion,review],'calls':[],'timing_policy':'manual_only','chapter_contract':sources.VERSION,'connection_failures':0,
               'accuracy':{key:{'initial':'chapters/'+key+'/accuracy-initial.json'}},'accuracy_evidence':hashes}
        return state,review

    def test_critic_failure_preserves_initial_and_carries_notes_with_no_revised_tex(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);state,review=self.setup_run(run)
            with patch.object(simple,'compile_version',return_value={'status':'passed'}),patch.object(runtime,'invoke',return_value=(None,{'id':'call-002','failure_kind':'truncation','error':'length'})):
                simple.task_once(run,state,review)
            self.assertEqual((run/'first.tex').read_text(),DOC);self.assertEqual(review['status'],'truncation')
            post=read_json(run/state['accuracy']['gatheral-01']['post_critic'])
            self.assertEqual(post['notes_status'],'review_incomplete');self.assertEqual(len(post['open_issues']),1)
            self.assertNotIn('versions',state)

    def test_complete_revision_and_notes_versions_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);state,review=self.setup_run(run);revised=DOC.replace('Exact','Updated')
            answer='```latex\n'+revised+'```\n## Accuracy notes\n- Evidence remains uncertain.'
            with patch.object(simple,'compile_version',return_value={'status':'syntax_failure'}),patch.object(runtime,'invoke',return_value=(answer,{'id':'call-002'})):
                simple.task_once(run,state,review)
            self.assertEqual((run/'first.tex').read_text(),DOC)
            self.assertEqual((run/review['revised_tex']['path']).read_text(),revised)
            self.assertTrue((run/'chapters/gatheral-01/material-changes.md').exists())
            self.assertGreaterEqual(review['open_accuracy_issues'],1)

    def test_context_gap_has_exact_request_no_dispatch_or_clipping(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);state,review=self.setup_run(run)
            with patch.object(simple,'compile_version',return_value={'status':'passed'}),patch.object(runtime,'invoke',side_effect=protocol.ContextBudgetGap('exceeds actual context')):
                simple.task_once(run,state,review)
            self.assertEqual(review['status'],'context_budget_gap');self.assertEqual(state['calls'],[])
            body=read_json(run/'chapters/gatheral-01/review-request.json')
            self.assertIn('SECONDARY',body['messages'][0]['content']);self.assertIn(DOC,body['messages'][0]['content'])
            self.assertEqual(body['max_tokens'],131072)

    def test_resume_does_not_replay_failed_review_or_erase_notes(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);state,review=self.setup_run(run)
            state['calls']=[{'id':'call-002','parent':review['id'],'status':'in_progress'}]
            with patch.object(runtime,'invoke',side_effect=AssertionError('No replay')):
                simple.task_once(run,state,review)
            self.assertEqual(review['status'],'unresolved_interruption')
            self.assertEqual(read_json(run/state['accuracy']['gatheral-01']['post_critic'])['notes_status'],'review_incomplete')

    def test_context_gap_does_not_block_other_eligible_chapters(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);state,review=self.setup_run(run)
            second,other=self.setup_run(run,'gatheral-02')
            state['tasks']+=second['tasks'];state['accuracy'].update(second['accuracy']);state['accuracy_evidence'].update(second['accuracy_evidence'])
            state['first_dispatch']=1
            seen=[]
            def invoke(run,state,parent,body,**kwargs):
                seen.append(parent)
                if parent=='gatheral-01/review':raise protocol.ContextBudgetGap('too large')
                return 'No material issues reported.',{'id':'call-001'}
            with patch.object(simple,'compile_version',return_value={'status':'passed'}),patch.object(simple,'verify'),patch.object(simple,'report'),patch.object(runtime,'invoke',side_effect=invoke):
                simple.run_schedule(run,state)
            self.assertEqual(seen,['gatheral-01/review','gatheral-02/review'])
            self.assertEqual(review['status'],'context_budget_gap');self.assertEqual(other['status'],'complete_response')

    def test_linked_preparation_keeps_calls_order_source_draft_and_only_historical_notes(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);parent=root/'parent';keys=['gatheral-01','gatheral-02','gatheral-03','gatheral-04','gatheral-05','gatheral-06']
            tasks=[]
            for key in keys:
                folder=parent/'inputs'/key;folder.mkdir(parents=True);(folder/'source.tex').write_text('PRIMARY '+key)
                atomic_json(folder/'assets.json',[]);atomic_json(folder/'conversion-request.json',simple.continuous_request('PRIMARY '+key))
                complete=key in ('gatheral-01','gatheral-02','gatheral-04')
                c={'id':key+'/convert','key':key,'phase':'convert','status':'complete_response' if complete else 'pending' if key=='gatheral-06' else 'truncation'}
                if complete:
                    f=parent/'chapters'/key;f.mkdir(parents=True);(f/'generated.tex').write_text(DOC);(f/'conversion-notes.md').write_text('- Original conversion uncertainty.')
                    c.update(output=str((f/'generated.tex').relative_to(parent)),output_sha256=sha(f/'generated.tex'),notes=str((f/'conversion-notes.md').relative_to(parent)))
                tasks.extend([c,{'id':key+'/review','key':key,'phase':'review','status':'pending'}])
            atomic_json(parent/'inputs/manifest.json',files_manifest(parent/'inputs'))
            binding={'code':{'historical':'hash'},'inputs_manifest_sha256':sha(parent/'inputs/manifest.json')}
            atomic_json(parent/'binding.json',binding)
            state={'binding_sha256':fingerprint(binding),'first_dispatch':1,'status':'prepared_linked_offline','tasks':tasks,
                   'calls':[{'id':f'call-{i:03d}','parent':'old','status':'completed_response','inherited_from':str(root/'original')} for i in range(1,12)]}
            atomic_json(parent/'state.json',state);original=files_manifest(parent)
            def secondary(run,*args):
                for key in keys:(run/'inputs'/key/'secondary.txt').write_text('SECONDARY '+key)
                return {'fixture':'source identity'}
            with patch.object(simple,'KEYS',keys),patch.object(simple,'POINTER',root/'pointer.json'),patch.object(runtime.inputs,'new_path',return_value=root/'new'),patch.object(sources,'prepare_secondary',side_effect=secondary):
                run=simple.initialize_policy_continuation(parent,two_sources=True)
            b,s=simple.verify(run)
            self.assertEqual(files_manifest(parent),original);self.assertEqual(len(s['calls']),11);self.assertEqual(s['first_dispatch'],1)
            self.assertEqual(runtime.remaining(s),float('inf'));self.assertEqual(s['chapter_contract'],sources.VERSION)
            pending=[t['id'] for t in s['tasks'] if t['status']=='pending']
            self.assertEqual(pending,['gatheral-01/review','gatheral-02/review','gatheral-04/review','gatheral-06/convert','gatheral-06/review'])
            for key in keys:
                body=read_json(run/'inputs'/key/'conversion-request.json');self.assertIn('PRIMARY '+key,body['messages'][0]['content']);self.assertIn('SECONDARY '+key,body['messages'][0]['content'])
            body=read_json(run/'inputs/gatheral-02/review-request.json')
            self.assertIn(DOC,body['messages'][0]['content']);self.assertIn('Original conversion uncertainty',body['messages'][0]['content'])
            self.assertNotIn('MANUAL_AUDIT_ONLY',body['messages'][0]['content'])
            record=read_json(run/s['accuracy']['gatheral-02']['initial']);origin=record['origin']
            self.assertEqual(sha(Path(origin['run'])/origin['path']),origin['sha256'])
            (run/'chapters/gatheral-02/accuracy-initial.md').write_text('changed')
            with self.assertRaises(runtime.Fatal):simple.verify(run)


if __name__=='__main__':unittest.main()
