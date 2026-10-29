"""Offline full-book intake and service-transition guards; no OCR/services/model calls."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import fitz
from scripts import book_extraction_intake as intake
from probe.common import atomic_json, read_json, files_manifest

spec=importlib.util.spec_from_file_location('bergomi_launcher',Path(__file__).resolve().parents[1]/'scripts/run-bergomi-extraction.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)


class BergomiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        atomic_json(self.root/'sources.json',{'gatheral':{'keep':'unchanged'}})
        atomic_json(self.root/'config.example.json',{'window_pages':8,'overlap_pages':1,'minimum_available_gib_basic':8})

    def pdf(self):
        path=self.root/'inputs/bergomi/source.pdf';path.parent.mkdir(parents=True)
        with fitz.open() as d:
            for n in range(19):
                p=d.new_page()
                if n!=5:p.insert_text((40,50),f'Native text page {n+1}\n5\nComplete reference')
            d.set_metadata({'title':'Synthetic other book','author':'Test author'})
            d.set_toc([[1,'Front',1],[1,'Chapter 1',4],[1,'Chapter 2',10],[1,'Bibliography',18]])
            d.save(path)
        return path

    def test_missing_input_never_substitutes_or_registers(self):
        before=(self.root/'sources.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'Missing input'):intake.prepare(self.root,'bergomi')
        self.assertEqual((self.root/'sources.json').read_bytes(),before)

    def test_preparation_test_log_is_not_reported_as_an_extraction_terminal(self):
        folder=self.root/'runs/bergomi-operator';folder.mkdir(parents=True)
        (folder/'offline-tests.log').write_text('Offline tests passed; no OCR')
        with contextlib.redirect_stdout(io.StringIO()) as out:launcher.base.status(self.root,'bergomi')
        self.assertIn('No bergomi conversion created yet',out.getvalue())
        self.assertNotIn('Latest terminal log:',out.getvalue())

    def test_all_pages_cache_blank_map_boundaries_and_registration_idempotent(self):
        pdf=self.pdf();original=pdf.read_bytes()
        cache,meta=intake.prepare(self.root,'bergomi')
        self.assertEqual(meta['pages'],19);self.assertEqual(meta['title'],'Synthetic other book')
        self.assertEqual([p['original_physical_page'] for p in meta['page_map']],list(range(1,20)))
        self.assertTrue(meta['page_map'][5]['empty_native_text'])
        self.assertIn('unverified',meta['page_map'][5]['blank_status'])
        self.assertIn('\n5\n',(cache/'native/page-000001.txt').read_text())
        self.assertEqual([(p['first_physical_page'],p['last_physical_page']) for p in meta['bookmark_sections']],[(1,3),(4,9),(10,17),(18,19)])
        plan=read_json(cache/'window-plan.json')
        self.assertEqual([n for w in plan for n in range(w['owned_start'],w['owned_end']+1)],list(range(1,20)))
        self.assertEqual(plan[0]['input_end'],9);self.assertEqual(plan[1]['input_start'],8)
        registry=read_json(self.root/'sources.json');self.assertEqual(registry['gatheral'],{'keep':'unchanged'})
        self.assertEqual(registry['bergomi']['original_pages'],list(range(1,20)))
        before=files_manifest(self.root);intake.prepare(self.root,'bergomi')
        self.assertEqual(files_manifest(self.root),before);self.assertEqual(pdf.read_bytes(),original)
        (cache/'native/page-000001.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'Changed native-text'):intake.prepare(self.root,'bergomi')

    def test_conflicting_source_registration_rejected(self):
        self.pdf();atomic_json(self.root/'sources.json',{'bergomi':{'pdf':'different'}})
        with self.assertRaisesRegex(ValueError,'Conflicting existing'):intake.prepare(self.root,'bergomi')

    def test_converter_reuses_actual_source_and_saved_run_not_gatheral(self):
        with patch.object(launcher.base.cli,'cmd_convert',return_value=0) as convert, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.base.launch(self.root,'bergomi'),0)
        args=convert.call_args.args[0];self.assertEqual((args.source,args.tier,args.ocr_isolation),('bergomi','basic','none'))
        run=self.root/'runs/convert-basic-existing'
        atomic_json(run/'state.json',{'settings':{'tier':'basic','sources':{'bergomi':{'pdf':'inputs/bergomi/source.pdf','pages':19}},'window_pages':8,'overlap_pages':1},
                                     'status':'paused_memory','units':{}})
        before=(run/'state.json').read_bytes()
        with patch.object(launcher.base.cli,'cmd_convert',return_value=75) as convert,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.base.launch(self.root,'bergomi'),75)
        self.assertEqual(convert.call_args.args[0].resume,str(run));self.assertEqual((run/'state.json').read_bytes(),before)
        with contextlib.redirect_stdout(io.StringIO()) as out:launcher.base.status(self.root,'bergomi')
        self.assertIn('0/19; windows: 0/3',out.getvalue())

    def resource_patches(self,health):
        client=MagicMock();client.chapter_health.return_value=(health,{})
        return client

    def test_active_glm_is_never_stopped(self):
        health={'context_length':1048576,'streams':{'max':8,'decoding':1,'filling':0}}
        client=self.resource_patches(health)
        with patch.object(launcher,'ROOT',self.root),patch.object(launcher,'project_idle'), \
             patch.object(launcher,'deployments',return_value={'head':[launcher.CONTAINER],'peer':[launcher.CONTAINER]}), \
             patch.object(launcher,'LocalClient',return_value=client), \
             patch.object(launcher,'checked',return_value=launcher.CONTAINER+'\n'+launcher.PEER+'\n\n8888\n') as command:
            with self.assertRaisesRegex(ValueError,'active or paused'):launcher.arrange_resources(self.root/'launch',stop_glm=True)
        self.assertFalse(any('./stop.sh' in call.args[0] for call in command.call_args_list))

    def test_idle_glm_stops_only_via_verified_helper_and_checks_both_nodes(self):
        health={'context_length':1048576,'streams':{'max':8,'decoding':0,'filling':0}}
        client=self.resource_patches(health)
        replies=[launcher.CONTAINER+'\n'+launcher.PEER+'\n\n8888\n','Stopped both nodes','peer memory']
        with patch.object(launcher,'ROOT',self.root),patch.object(launcher,'project_idle'), \
             patch.object(launcher,'deployments',side_effect=[{'head':[launcher.CONTAINER],'peer':[launcher.CONTAINER]},{'head':[],'peer':[]}]), \
             patch.object(launcher,'LocalClient',return_value=client), \
             patch.object(launcher,'memory_inventory',return_value={'MemAvailable_bytes':12*1024**3}), \
             patch.object(launcher,'checked',side_effect=replies) as command,contextlib.redirect_stdout(io.StringIO()):
            launcher.arrange_resources(self.root/'launch',stop_glm=True)
        stop=[c for c in command.call_args_list if './stop.sh' in c.args[0]]
        self.assertEqual(len(stop),1);self.assertEqual(stop[0].kwargs['cwd'],launcher.GLM)
        client.chat.assert_not_called()

    def test_unknown_or_other_deployment_refused(self):
        with patch.object(launcher,'checked',return_value='marco-deepseek-flash17-r0\n'):
            with self.assertRaisesRegex(ValueError,'left untouched'):launcher.deployments()

    def test_policy_callback_fails_before_converter(self):
        with patch.object(launcher.base.cli,'cmd_convert') as convert:
            with self.assertRaisesRegex(ValueError,'busy'):
                launcher.base.launch(self.root,'bergomi',before_convert=lambda:(_ for _ in ()).throw(ValueError('busy')))
            convert.assert_not_called()


if __name__=='__main__':unittest.main()
