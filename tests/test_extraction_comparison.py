import copy
import unittest
import importlib.util
import tempfile
from pathlib import Path
from probe import extraction_comparison as study


class ComparisonContracts(unittest.TestCase):
    def candidate_module(self):
        path=Path(__file__).resolve().parents[1]/'scripts/extraction_candidate_worker.py'
        spec=importlib.util.spec_from_file_location('candidate_setup_test',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_layout_compatibility_uses_same_processor_and_rejects_unknowns(self):
        from unittest.mock import patch
        from types import ModuleType
        import sys
        module=self.candidate_module()
        class Processor:
            @classmethod
            def from_pretrained(cls, *a): return cls()
            def post_process_object_detection(self): pass
            def _mask2polygon(self): pass
        fake=ModuleType('transformers')
        fake.__version__='5.3.0'
        fake.PPDocLayoutV3ImageProcessorFast=Processor
        fake.PPDocLayoutV3ForObjectDetection=object
        with patch.dict(sys.modules, {'transformers':fake}):
            record=module.layout_api_compatibility()
            self.assertIs(fake.PPDocLayoutV3ImageProcessor,Processor)
            self.assertEqual(record['implementation'],'Processor')
            fake.PPDocLayoutV3ImageProcessor=object
            with self.assertRaises(RuntimeError):module.layout_api_compatibility()
            self.assertIs(fake.PPDocLayoutV3ImageProcessor,object)
            fake.__version__='5.4.0'
            with self.assertRaises(RuntimeError):module.layout_api_compatibility()

    def test_declared_model_context_is_used_without_extension(self):
        module=self.candidate_module()
        self.assertEqual(module.model_context_limit({'max_position_embeddings':8192.0}),8192)
        self.assertEqual(module.model_context_limit({'max_position_embeddings':32768,'text_config':{'max_position_embeddings':8192}}),8192)
        for value in ({},{'max_position_embeddings':True},{'max_position_embeddings':8192.5}):
            with self.assertRaises(ValueError):module.model_context_limit(value)

    def test_dotenv_is_real_empty_file_and_never_overwrites_content(self):
        module=self.candidate_module()
        with tempfile.TemporaryDirectory() as folder:
            path=module.local_empty_env(Path(folder))
            self.assertTrue(path.is_file());self.assertEqual(path.read_bytes(),b'')
            self.assertEqual(module.local_empty_env(Path(folder)),path)
            path.write_text('private sentinel')
            with self.assertRaises(ValueError):module.local_empty_env(Path(folder))
            self.assertEqual(path.read_text(),'private sentinel')

    def test_partial_native_responses_cannot_be_qualified_as_complete(self):
        module=self.candidate_module()
        self.assertTrue(module.incomplete_receipt({'choices':[{'finish_reason':'length'}]}))
        self.assertTrue(module.incomplete_receipt({'choices':[{'finish_reason':None}]}))
        self.assertTrue(module.incomplete_receipt({'finished':False,'choices':[{'finish_reason':'stop'}]}))
        self.assertFalse(module.incomplete_receipt({'finished':True,'choices':[{'finish_reason':'stop'}]}))

    def test_continuation_reuses_parent_model_store_read_only(self):
        import ast
        controller=Path(__file__).resolve().parents[1]/'scripts/extraction_comparison.py'
        tree=ast.parse(controller.read_text())
        function=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='container_args')
        namespace={'Path':Path};exec(compile(ast.Module(body=[function],type_ignores=[]),str(controller),'exec'),namespace)
        args=namespace['container_args']({'remote':'/child','remote_models':'/parent/models','runtime_image':'sha256:'+'a'*64},'mineru_pro')
        self.assertIn('type=bind,src=/parent/models,dst=/models,readonly',args)
        self.assertIn('type=bind,src=/child/input,dst=/study,readonly',args)

    def test_local_only_route_and_no_silent_footnote_loss(self):
        p = study.safe_glmocr_config('/models/layout')['pipeline']
        self.assertFalse(p['maas']['enabled'])
        self.assertEqual(p['ocr_api']['api_host'], '127.0.0.1')
        self.assertEqual(p['ocr_api']['retry_max_attempts'], 0)
        self.assertIn('footnote', p['layout']['label_task_mapping']['text'])
        self.assertEqual(p['layout']['label_task_mapping']['abandon'], [])

    def test_completed_failed_and_uncertain_attempts_cannot_replay(self):
        for status in ('running','completed','failed','uncertain'):
            self.assertFalse(study.task_allowed({'status':status}))
        self.assertTrue(study.task_allowed(None))
        self.assertTrue(study.task_allowed({'status':'pending'}))

    def test_readable_view_preserves_math_and_unrecognised_blocks(self):
        blocks=[{'type':'formula','content':r'\alpha+\rho X'},
                {'type':'unrecognised','content':'AFTER REFERENCES'},
                {'type':'image','bbox':[0,0,1,1],'content':None}]
        original=copy.deepcopy(blocks)
        text=study.raw_text(blocks)
        self.assertIn(r'\alpha+\rho X',text)
        self.assertIn('AFTER REFERENCES',text)
        self.assertIn('type=image',text)
        self.assertEqual(blocks,original)

    def test_asset_containment(self):
        for path in ('/etc/passwd','../image.png','assets/../../image.png','assets\\file'):
            with self.assertRaises(ValueError):study.check_relative(path)
        self.assertEqual(study.check_relative('assets/figure.png'),'assets/figure.png')

    def test_request_identity_includes_effort_and_source(self):
        a={'reasoning_effort':'high','source':'x'}
        self.assertNotEqual(study.input_digest(a),study.input_digest(dict(a,source='y')))
        self.assertNotEqual(study.input_digest(a),study.input_digest(dict(a,reasoning_effort='low')))

    def test_scope_keeps_complete_cases_without_owning_context(self):
        from scripts.extraction_comparison import passage
        source='Context\nCase 12. x\nCase 13. a\nCase 14. b\nCase 18. c\nCase 19. d'
        result,bounds=passage(source,0)
        self.assertEqual(result,source[bounds[0]:bounds[1]])
        self.assertIn('Case 18.',result)
        self.assertNotIn('Case 19.',result)
        self.assertNotIn('Case 12.',result)
        with self.assertRaises(ValueError):passage(source+' Case 13. duplicate',0)

    def test_control_has_exact_section_boundaries(self):
        from scripts.extraction_comparison import passage
        source='Introduction\n## 2 Information derivatives\nb(x)=f(x)m(x)\n## 3 Risks as returns\nother'
        selected,_=passage(source,1)
        self.assertIn('b(x)=f(x)m(x)',selected)
        self.assertNotIn('other',selected)
        with self.assertRaises(ValueError):passage('2 Information derivatives\nincomplete',1)

    def test_tex_heading_wrappers_are_not_cut(self):
        from scripts.extraction_comparison import passage
        source='context\n\\subsection*{2 Information derivatives}\nmath\n\\subsection*{3 Risks as returns}\nlater'
        selected,_=passage(source,1)
        self.assertEqual(selected,'\\subsection*{2 Information derivatives}\nmath\n')

    def test_later_prose_case_reference_is_not_a_second_boundary(self):
        from scripts.extraction_comparison import passage
        text='Case 13.\nmath\nCase 18.\nmore math\nCase 19. McNolty\nCase 19 was developed jointly by the author.'
        selected,_=passage(text,0)
        self.assertEqual(selected,'Case 13.\nmath\nCase 18.\nmore math\n')

    def test_finished_resume_makes_no_host_or_model_calls(self):
        from scripts import extraction_comparison as controller
        from unittest.mock import patch
        with patch.object(controller,'verify',return_value={'status':controller.TERMINAL}), \
             patch.object(controller.subprocess,'run',side_effect=AssertionError('Unexpected host operation')), \
             patch.object(controller.sys,'argv',['comparison','resume','--run','/tmp/finished-comparison']):
            controller.main()

    def test_prebuilt_runtime_still_creates_new_run_mount_directories(self):
        from scripts import extraction_comparison as controller
        from unittest.mock import patch
        from types import SimpleNamespace
        from pathlib import Path
        image='sha256:'+'a'*64
        state={'runtime_image':image,'remote':'/home/mdi/projects/pdf-to-latex-comparisons/new-run'}
        with patch.object(controller.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)), \
             patch.object(controller.subprocess,'check_output',side_effect=[str(100*1024**3),image]), \
             patch.object(controller,'command') as operation:
            controller.install_runtime(Path('/tmp/run'),state)
        self.assertEqual(operation.call_count,1)
        remote_command=operation.call_args.args[2][-1]
        for name in ('input','models','outputs'):self.assertIn('/new-run/'+name,remote_command)


if __name__ == '__main__':unittest.main()
