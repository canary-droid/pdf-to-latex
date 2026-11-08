"""Frozen inventory, durable extraction, real scheduler and portable deliveries."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from probe import source_library as library, cli, chapter_concurrency as concurrent
from probe import chapter_glm as runtime, book_completion as scope
from probe.common import atomic_json, read_json, sha, fingerprint, files_manifest
from probe.experiment import seal, verify_seal
from scripts import originals_batch as ctrl
from test_speed_suite import DOC, BODY, health


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.originals=self.root/'originals';self.originals.mkdir()
        self.intake=self.root/'intake';self.intake.mkdir()

    def inventory(self):
        docs=[];entries=[]
        for name,body in [('same.pdf',b'%PDF-1\nA'),('duplicate.PDF',b'%PDF-1\nA'),('different.pdf',b'%PDF-1\nB')]:
            p=self.originals/name;p.write_bytes(body);h=sha(p)
            entries.append({'sha256':h,'pdf_extension':True})
            if h not in {d['sha256'] for d in docs}:
                docs.append({'sha256':h,'bytes':p.stat().st_size,'preferred_original_name':'2020_Author_Title.pdf',
                             'title':'CON: Title / \\ ?*','document_type':'presentation','partial':True,
                             'completeness':'partial source','page_count':2,'provenance':[{'original_name':name}]})
        # An archive-only source must not leak into the frozen batch.
        docs.append(dict(docs[0],sha256='f'*64))
        atomic_json(self.intake/'manifest.json',{'documents':docs,'originals_baseline':{'entries':entries}})
        return library.inventory(self.originals,self.intake)

    def test_exact_duplicate_versions_and_scope(self):
        m=self.inventory();self.assertEqual((m['unique_sources'],m['occurrences']),(2,3))
        self.assertFalse(m['added_hashes']);self.assertNotIn('f'*64,str(m['documents']))
        for d in m['documents']:
            self.assertNotRegex(d['folder'],r'[<>:"/\\|?*]');self.assertTrue(d['partial'])
        library.verify_originals(m)
        (self.originals/'new.pdf').write_bytes(b'%PDF-new')
        with self.assertRaisesRegex(ValueError,'Frozen'):library.verify_originals(m)

    def test_collision_and_changed_metadata_fail_closed(self):
        m=self.inventory();d=read_json(self.intake/'manifest.json')
        for row in d['documents']:row['source_id']='same-id'
        atomic_json(self.intake/'manifest.json',d)
        with self.assertRaisesRegex(ValueError,'collision'):library.inventory(self.originals,self.intake)
        (self.originals/'same.pdf').write_bytes(b'%PDF-changed')
        with self.assertRaisesRegex(ValueError,'differs'):library.inventory(self.originals,self.intake)

    def test_portable_immutable_generation_resume_and_conflict(self):
        m=self.inventory();d=m['documents'][0]
        out=library.ensure_source(self.root/'sources',d,d['originals'][0]['path'])
        prepared=self.root/'ready';prepared.mkdir();(prepared/'README.md').write_text('Editable source')
        (prepared/'document.tex').write_text(DOC.replace('Complete',r'\includegraphics{assets/figure.png} Complete'))
        (prepared/'assets').mkdir();(prepared/'assets/figure.png').write_bytes(b'image bytes')
        seal(prepared)
        first=library.publish_generation(out,'generation-1',prepared,'working')
        second=library.publish_generation(out,'generation-1',prepared,'working')
        self.assertEqual(first,second);verify_seal(out/first['generation'],first['manifest_sha256'])
        self.assertEqual(sha(out/'original.pdf'),d['sha256'])
        archive=library.archive(self.root/'delivery.zip',out);self.assertGreater(archive['bytes'],0)
        (out/first['generation']/'document.tex').write_text('altered')
        with self.assertRaises(ValueError):library.publish_generation(out,'generation-1',prepared,'working')

    def test_symlink_parent_rejected(self):
        source=self.root/'source';source.write_text('x');target=self.root/'real';target.mkdir()
        link=self.root/'link';link.symlink_to(target,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'regular'):library.copy_verified(source,link/'out')


class ExtractionTests(unittest.TestCase):
    def test_failed_ocr_window_allowance_persists_across_resumes(self):
        import fitz
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);pdf=fitz.open();pdf.new_page();pdf.save(root/'original.pdf');pdf.close()
            atomic_json(root/'config.json',{'local_only':True,'window_pages':1,'overlap_pages':0,'minimum_available_gib_basic':1,'conversion_timeout_seconds':100})
            (root/'probe').mkdir();(root/'probe/mineru_worker.py').write_text('fixture')
            sources={'x':{'pdf':'original.pdf','sha256':sha(root/'original.pdf'),'pages':1,'original_pages':[1],'ocr_mode':'auto'}}
            args=cli.parser().parse_args(['--config',str(root/'config.json'),'convert','--source','x','--tier','basic','--ocr-isolation','none'])
            out=root/'runs/test'
            with patch.object(cli,'ROOT',root),patch.object(cli,'execute_window',return_value='failed') as execute,patch.object(cli,'memory_policy',return_value={'status':'meets_minimum'}),patch.object(cli,'report_run'),patch.object(cli,'bundle_run'):
                self.assertEqual(cli.cmd_convert(args,source_records=sources,runtime={},run_path=out,max_unit_attempts=2),2)
                args.resume=str(out)
                for _ in range(3):self.assertEqual(cli.cmd_convert(args,source_records=sources,runtime={},max_unit_attempts=2),2)
                self.assertEqual(execute.call_count,2);self.assertEqual(read_json(out/'state.json')['status'],'unit_allowance_exhausted')

    def test_resume_reuses_completed_windows_and_bounds_failed_attempts(self):
        import fitz
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);pdf=fitz.open()
            for n in range(3):pdf.new_page().insert_text((30,30),'Page '+str(n))
            pdf.save(root/'original.pdf');pdf.close()
            config={'local_only':True,'window_pages':1,'overlap_pages':0,'minimum_available_gib_basic':1,'conversion_timeout_seconds':100}
            atomic_json(root/'config.json',config);(root/'probe').mkdir();(root/'probe/mineru_worker.py').write_text('fixture')
            sources={'x':{'pdf':'original.pdf','sha256':sha(root/'original.pdf'),'pages':3,'original_pages':[1,2,3],'ocr_mode':'auto'}}
            args=cli.parser().parse_args(['--config',str(root/'config.json'),'convert','--source','x','--tier','basic','--ocr-isolation','none'])
            out=root/'runs/test';seen=[]
            def execute(command,attempt,*_):
                seen.append(attempt.name);output=attempt/'output';output.mkdir()
                atomic_json(output/'summary.json',{'status':'extracted_unreviewed','observed_page_indices':[0]})
                return 'completed'
            def pause(_run,state,record):raise runtime.StopRun('pause after one owned window')
            with patch.object(cli,'ROOT',root),patch.object(cli,'execute_window',side_effect=execute),patch.object(cli,'memory_policy',return_value={'status':'meets_minimum'}),patch.object(cli,'report_run'),patch.object(cli,'bundle_run'):
                with self.assertRaises(runtime.StopRun):cli.cmd_convert(args,source_records=sources,runtime={},run_path=out,after_window=pause,max_unit_attempts=2)
                first=copy.deepcopy(read_json(out/'state.json')['units']);args.resume=str(out)
                self.assertEqual(cli.cmd_convert(args,source_records=sources,runtime={},max_unit_attempts=2),0)
                self.assertEqual(len(seen),3)
                self.assertEqual(read_json(out/'state.json')['units']['x-0001-0001'],first['x-0001-0001'])
                # A completed-output alteration stops reuse, rather than repeating OCR.
                attempt=out/first['x-0001-0001']['attempt'];(attempt/'output/summary.json').write_text('{}')
                with self.assertRaisesRegex(ValueError,'changed'):cli.cmd_convert(args,source_records=sources,runtime={},max_unit_attempts=2)
                self.assertEqual(len(seen),3)

    def test_nonblank_absent_blocks_not_silently_excluded(self):
        import fitz
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);attempt=root/'a';attempt.mkdir();pdf=fitz.open()
            pdf.new_page().insert_text((30,30),'Missing appendix content');pdf.save(attempt/'input.pdf');pdf.close()
            atomic_json(root/'state.json',{'units':{'x':{'attempt':'a'}}})
            atomic_json(attempt/'page-map.json',[{'owner':True,'selected_page':1,'original_physical_page':1}])
            atomic_json(attempt/'output/middle_json.json',{'pages':[{'page_idx':0}]})
            with self.assertRaisesRegex(ValueError,'Nonblank'):ctrl.verified_blanks(root)


class SchedulerTests(unittest.TestCase):
    def state(self):
        tasks=[]
        for key in ('bad','good'):
            for phase in ('convert','critic'):
                tasks.append({'id':key+'/'+phase,'key':key,'source_key':key,'phase':phase,'status':'pending','reasoning_effort':scope.EFFORTS[phase]})
        return {'status':'running','suite_protocol':library.PROTOCOL,'chapter_contract':'annotated-chapter-v1',
                'timing_policy':'manual_only','first_dispatch':None,'execution_limits':{'calls':None,'attempts_per_unit':1},
                'concurrency_policy':copy.deepcopy(concurrent.POLICY),'active_stage':1,'calls':[],'tasks':tasks,
                'versions':{},'current_versions':{},'connection_failures':0}

    def test_failed_document_continues_own_critic_dependency_and_no_replay(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);state=self.state();seen=[]
            def transport(r,c,b,**_):
                seen.append(c['parent']);c.update(status='completed_response',elapsed_seconds=.01,metadata={'finish_reason':'stop'})
                p=r/'calls'/c['id'];atomic_json(p/'request.json',b);seal(p);c['seal']=sha(p/'manifest.json')
                return DOC,c
            def finish(r,s,t,a,c):
                t.update(status='complete_answer_without_document' if t['key']=='bad' else 'conversion_completed' if t['phase']=='convert' else 'critic_unchanged',settled_call=c['id'])
                if t['key']=='good':s['current_versions']['good']='draft';s['versions']['good']={'draft':{'sha256':'hash'}}
            def go():
                concurrent.coordinate(root,state,state['tasks'],body_for=lambda *args:BODY,finish=finish,
                    verify=lambda:None,changed=lambda:None,sample=lambda owned:health(owned),transport=transport,poll_seconds=.01,fixed_level=2)
            go();self.assertEqual(len(seen),3);self.assertNotIn('bad/critic',seen)
            self.assertEqual(state['tasks'][-1]['status'],'critic_unchanged')
            go();self.assertEqual(len(seen),3)
            with self.assertRaises(runtime.StopRun):runtime.reserve(state,'good/convert','another hash')

    def test_terminal_launch_does_not_check_services_or_infer(self):
        with patch.object(ctrl,'verify',return_value={'status':ctrl.TERMINAL}),patch.object(ctrl.subprocess,'run',side_effect=AssertionError('No service calls')):
            ctrl.launch(Path('/unused'))

    def test_uncertain_reservation_blocks_before_launch(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);pointer=root/'pointer.json';atomic_json(pointer,{'run':str(root)})
            state={'status':'paused','calls':[{'id':'call-1','status':'in_progress'}]}
            with patch.object(ctrl,'verify',return_value=state),patch.object(ctrl,'POINTER',pointer),patch.object(ctrl.books.speed,'idle',return_value=True),patch.object(ctrl.subprocess,'run',side_effect=AssertionError('No dispatch')):
                with self.assertRaisesRegex(runtime.Fatal,'Uncertain'):ctrl.launch(root)

    def test_missing_ocr_does_not_stop_active_or_unknown_deployment(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);helpers=Mock(CONTAINER='owned');helpers.deployments.return_value={'head':['owned'],'peer':[]}
            with patch.object(ctrl,'helper_hashes',return_value={'helper':'hash'}):
                with self.assertRaisesRegex(runtime.Fatal,'Partial'):ctrl.resource_handoff(root,{'documents':{'x':{'status':'pending_extraction'}}},helpers)
            helpers.arrange_resources.assert_not_called()


class ScopeAndPublicationTests(unittest.TestCase):
    def test_saved_synthetic_native_through_critic_and_portable_delivery(self):
        """Real saved-page/renderer/parser path; fake model transport and compiler."""
        import fitz
        ocr=ctrl.ROOT/'runs/convert-basic-20261018T182257Z-c99779'
        if not (ocr/'state.json').exists() or not (ctrl.ROOT/'.venv-mineru/bin/python').exists():
            self.skipTest('Optional saved native fixture / renderer unavailable')
        source=read_json(ocr/'state.json')['settings']['sources']['fixture-native']
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);run=root/'run';run.mkdir()
            document={'source_id':'fixture-native','page_count':source['pages'],'sha256':source['sha256'],
                      'title':'Saved synthetic fixture','folder':'Fixture-2026-Synthetic--'+source['sha256'][:16],
                      'document_type':'synthetic fixture','completeness':'two pages','originals':[]}
            state={'documents':{'fixture-native':{'original':str(ctrl.ROOT/source['pdf']),'extraction':str(ocr),
                    'extraction_state_sha256':sha(ocr/'state.json'),'status':'extracted'}},'tasks':[],'source_units':{},
                   'production_stage':{'task_ids':[]},'current_versions':{},'versions':{},'accuracy':{},'accuracy_records':{},
                   'selection_ledger':[],'calls':[]}
            ctrl.plan_document(run,state,document);atomic_json(run/'collection.json',{'documents':[document]})
            self.assertEqual(state['tasks'][0]['section']['physical_pages'],[1,2])
            def compile_version(r,s,key,label):
                v=s['versions'][key][label];out=r/'compiled'/label;out.mkdir(parents=True)
                p=fitz.open();p.new_page().insert_text((30,30),'Synthetic compiler fixture');p.save(out/'document.pdf');p.close()
                v['compilation']={'status':'passed','attempts':[{'status':'passed','input_sha256':v['sha256'],'path':str(out.relative_to(r))}]}
            with patch.object(ctrl,'LIBRARY',root/'library'),patch.object(ctrl,'ROOT',root),patch.object(ctrl,'compile_version',side_effect=compile_version):
                for i,task in enumerate(state['tasks'],1):
                    body=ctrl.books.request_for(run,state,task);ctrl.books.before_reserve(run,state,task,body)
                    call={'id':'call-'+str(i),'parent':task['id'],'status':'completed_response','request_sha256':fingerprint(body)}
                    path=run/'calls'/call['id'];atomic_json(path/'request.json',body);seal(path);call['seal']=sha(path/'manifest.json')
                    state['calls'].append(call)
                    ctrl.finish(run,state,task,DOC if i==1 else DOC.replace('conditions','complete conditions'),call)
            rec=state['documents']['fixture-native'];self.assertEqual(rec['conversion'],'completed');self.assertEqual(rec['model_review'],'completed')
            folder=root/'library'/document['folder'];pointer=read_json(folder/'current.json');generation=folder/pointer['generation']
            verify_seal(generation,pointer['manifest_sha256'])
            part=next((generation/'parts').iterdir());self.assertEqual((part/'initial-draft.tex').read_text(),DOC)
            self.assertIn('complete conditions',(part/'document.tex').read_text())
            self.assertTrue(list((generation/'provenance').rglob('material-comparison.json')))
            self.assertTrue((generation/'reading.pdf').exists());self.assertEqual(sha(folder/'original.pdf'),source['sha256'])
            self.assertFalse(list(generation.rglob('reasoning*')))

    def test_document_scope_retains_nested_appendix_even_shorter_title(self):
        n={'key':'article','source':'article','title':'A title','blocks':[
            {'id':'1','kind':'paragraph_title','tex':r'\section{Main}','page':{'original_physical_page':1}},
            {'id':'2','kind':'text','tex':'Assumptions and proof.','page':{'original_physical_page':1}},
            {'id':'3','kind':'paragraph_title','tex':r'\subsection{Appendix A}','page':{'original_physical_page':2}},
            {'id':'4','kind':'text','tex':r'Boundary $x>0$, full appendix.','page':{'original_physical_page':2}}]}
        parts=scope.split_meaningfully(n,['1','2','3','4'],fits=lambda _:True)
        self.assertEqual(len(parts),1);parts[0]['title']='Main'
        for phase,draft in [('convert',None),('critic',DOC)]:
            req=scope.request(n,parts[0],'Native PDF text',phase=phase,draft=draft)
            self.assertIn('full appendix',req['messages'][0]['content']);self.assertEqual(req['reasoning_effort'],scope.EFFORTS[phase])

    def test_failed_document_generation_resumes_without_reclassification(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);document={'source_id':'failed','sha256':'a'*64,'page_count':2,'title':'Paper','completeness':'partial source'}
            rec={'status':'extraction_failed','units':[],'error':'document parse failed'}
            s={'documents':{'failed':rec},'tasks':[],'calls':[],'selection_ledger':[]}
            out=ctrl.generation(root,s,document);verify_seal(out);identity=sha(out/'manifest.json')
            rec['status']='pending_extraction';ctrl.generation(root,s,document)
            self.assertEqual(rec['status'],'extraction_failed');self.assertEqual(sha(out/'manifest.json'),identity)


if __name__=='__main__':unittest.main()
