"""Offline regressions for the integrated editorial launch repair; no services."""
import copy
import importlib.util
from pathlib import Path
import shlex
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from probe.common import atomic_json, files_manifest, fingerprint, read_json, sha
from probe.experiment import IntegrityError, seal
from scripts import editorial_chapters as run


class GPUWorkloadTests(unittest.TestCase):
    def module(self, rows, executable, *, identity='7:42\n7:42\n'):
        def checked(argv):
            if argv[0]=='ssh':argv=shlex.split(argv[-1])
            if argv[0]=='nvidia-smi':return rows
            if argv[0]=='readlink':
                if isinstance(executable,Exception):raise executable
                return executable+'\n'
            if argv[0]=='stat':return identity
            if argv==['cat','/proc/meminfo']:
                return 'MemTotal: 120000000 kB\nMemAvailable: 98765432 kB\n'
            raise AssertionError(argv)
        return SimpleNamespace(checked=Mock(side_effect=checked),peer=lambda command:['ssh','peer',command])

    def test_observed_desktop_verified_on_both_nodes_without_memory_credit(self):
        module=self.module('3380837, /usr/libexec/gnome-remote-desktop-daemon\n',run.DESKTOP_EXECUTABLE)
        with tempfile.TemporaryDirectory() as td:
            run.guard_gpu_workloads(Path(td),module)
            report=read_json(next((Path(td)/'launch-checks').glob('gpu-workloads-*.json')))
        for node in report['nodes']:
            self.assertEqual(node['processes'][0]['classification'],'verified_desktop')
            self.assertEqual(node['memory_bytes']['MemAvailable'],98765432*1024)
        self.assertTrue(any(c.args[0][0]=='ssh' for c in module.checked.call_args_list))

    def test_reported_name_or_pid_does_not_exempt_python_or_unknown_work(self):
        for exe in ('/usr/bin/python3.12','/opt/mineru/bin/python',
                    '/tmp/gnome-remote-desktop-daemon','/usr/local/bin/unknown-gpu-job'):
            with self.subTest(executable=exe),tempfile.TemporaryDirectory() as td:
                module=self.module('3380837, '+run.DESKTOP_EXECUTABLE+'\n',exe)
                with self.assertRaisesRegex(RuntimeError,'Active or unverifiable GPU work'):
                    run.guard_gpu_workloads(Path(td),module)
                report=read_json(next((Path(td)/'launch-checks').glob('*.json')))
                self.assertEqual(report['nodes'][0]['processes'][0]['classification'],'conflicting_or_unknown')

    def test_unreadable_replaced_or_deleted_executable_stays_blocked(self):
        for exe,identity in ((RuntimeError('Permission denied'),'7:42\n7:42\n'),
                             (run.DESKTOP_EXECUTABLE,'7:42\n7:43\n'),
                             (run.DESKTOP_EXECUTABLE+' (deleted)','7:42\n7:42\n')):
            with self.subTest(exe=exe),tempfile.TemporaryDirectory() as td:
                with self.assertRaisesRegex(RuntimeError,'GPU work'):
                    run.guard_gpu_workloads(Path(td),self.module('123, daemon\n',exe,identity=identity))

    def test_malformed_process_inventory_is_not_treated_as_idle(self):
        for row in ('unknown, python\n','123; touch bad, daemon\n','0, daemon\n'):
            with self.subTest(row=row):
                with self.assertRaisesRegex(RuntimeError,'Cannot interpret GPU workload'):
                    run.gpu_workload_snapshot(self.module(row,run.DESKTOP_EXECUTABLE),'head')

    def test_mineru_or_other_project_work_stops_before_service_operations(self):
        module=SimpleNamespace(project_idle=Mock(side_effect=ValueError('MinerU still active')),
                               deployments=Mock())
        spec=SimpleNamespace(loader=SimpleNamespace(exec_module=Mock()))
        with patch('importlib.util.spec_from_file_location',return_value=spec), \
             patch('importlib.util.module_from_spec',return_value=module), \
             patch.object(run,'guard_gpu_workloads') as gpu,patch.object(run.subprocess,'run') as command:
            with self.assertRaisesRegex(ValueError,'MinerU still active'):run.arrange_glm(Path('/unused'))
        module.deployments.assert_not_called();gpu.assert_not_called();command.assert_not_called()

    def test_unknown_gpu_work_cannot_reach_model_start_or_readiness(self):
        module=self.module('123, python\n','/usr/bin/python3.12')
        module.project_idle=Mock();module.deployments=lambda:{'head':[],'peer':[]};module.CONTAINER='glm53-flash-tf'
        spec=SimpleNamespace(loader=SimpleNamespace(exec_module=Mock()))
        with tempfile.TemporaryDirectory() as td, \
             patch('importlib.util.spec_from_file_location',return_value=spec), \
             patch('importlib.util.module_from_spec',return_value=module), \
             patch.object(Path,'iterdir',return_value=iter(())), \
             patch.object(run.subprocess,'run') as command,patch('probe.local_model.LocalClient') as client:
            with self.assertRaisesRegex(RuntimeError,'GPU work'):run.arrange_glm(Path(td))
        command.assert_not_called();client.assert_not_called()


class LinkedLaunchRepairTests(unittest.TestCase):
    old_code={'scripts/editorial_chapters.py':'old','probe/common.py':'unchanged'}
    new_code={**old_code,'scripts/editorial_chapters.py':'repaired'}

    def fixture(self,root):
        historic=root/'historical';atomic_json(historic/'state.json',{'calls':24});atomic_json(historic/'binding.json',{})
        parent=root/'runs/prepared';(parent/'inputs').mkdir(parents=True);(parent/'prepared').mkdir()
        (parent/'inputs/source.tex').write_text('Original full chapter and formulas')
        atomic_json(parent/'prepared/request.json',{'model':'glm53-regular','max_tokens':131072,'messages':['both unchanged sources']})
        seal(parent/'inputs');seal(parent/'prepared')
        atomic_json(parent/'compiler/result.json',{'status':'qualified','image':'qualified-image'});seal(parent/'compiler')
        (parent/'document.tex').write_text('Saved corrected draft, not regenerated')
        task={'id':'unit-1','key':'gatheral-06','phase':'convert','source_key':'gatheral-06',
              'section':None,'context':'','draft_label':None,'status':'pending'}
        limits={'calls':98,'attempts_per_unit':1}
        binding={'code':self.old_code,'parent':str(historic),'parent_state_sha256':sha(historic/'state.json'),
                 'parent_binding_sha256':sha(historic/'binding.json'),'inputs_seal':sha(parent/'inputs/manifest.json'),
                 'prepared_seal':sha(parent/'prepared/manifest.json'),'tasks':[task],'execution_limits':limits}
        state={'binding_sha256':fingerprint(binding),'status':'prepared_offline','first_dispatch':None,
               'calls':[],'historical_calls':[{'id':str(n)} for n in range(24)],'historical_request_seconds':27920,
               'tasks':[task],'execution_limits':limits,'compiler_environment':{'path':'compiler',
               'seal':sha(parent/'compiler/manifest.json'),'image':'qualified-image'},
               'versions':{'gatheral-01':{'annotated':{'path':'document.tex','sha256':sha(parent/'document.tex'),
                           'compilation':{'status':'not_attempted'}}}},
               'current_versions':{'gatheral-01':'annotated'},'accuracy':{},'scope':'unchanged','bergomi_status':'awaiting'}
        atomic_json(parent/'binding.json',binding);atomic_json(parent/'state.json',state)
        pointer=root/'results/editorial-chapters-current.json'
        atomic_json(pointer,{'run':str(parent),'development':'/tmp/original-development',
                             'copy_back_manifest':{'files':{'script':'original integration receipt'}}})
        return parent,pointer,state

    def prepare(self,root,parent,pointer,code=None):
        with patch.object(run,'ROOT',root),patch.object(run,'POINTER',pointer), \
             patch.object(run,'extraction_complete',return_value=(True,'complete')), \
             patch.object(run,'code_hashes',return_value=code or self.new_code), \
             patch.object(run.chapter_inputs,'new_path',return_value=root/'runs/linked'):
            return run.prepare_launch_repair(parent)

    def test_copy_keeps_requests_corrections_limits_and_integration_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);parent,pointer,old=self.fixture(root);before=files_manifest(parent)
            receipt=read_json(pointer);new=self.prepare(root,parent,pointer)
            self.assertEqual(files_manifest(parent),before)
            for path in ('prepared/request.json','inputs/source.tex','document.tex'):
                self.assertEqual((new/path).read_bytes(),(parent/path).read_bytes())
            actual=read_json(new/'state.json');actual['binding_sha256']=old['binding_sha256']
            self.assertEqual(actual,old)
            receipt['run']=str(new);self.assertEqual(read_json(pointer),receipt)
            with patch.object(run,'code_hashes',return_value=self.new_code):
                run.verify(new)
                with self.assertRaisesRegex(run.runtime.Fatal,'Changed code'):run.verify(parent)
                atomic_json(parent/'state.json',{**old,'tampered':True})
                with self.assertRaisesRegex(run.runtime.Fatal,'parent evidence'):run.verify(new)

    def test_consumed_calls_or_unrelated_code_change_cannot_be_reset(self):
        for kind in ('consumed','other_code'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as td:
                root=Path(td);parent,pointer,state=self.fixture(root)
                if kind=='consumed':
                    state['calls']=[{'id':'call-001','status':'failed'}];atomic_json(parent/'state.json',state)
                code={**self.new_code,'probe/common.py':'unexpected'} if kind=='other_code' else self.new_code
                with self.assertRaises(ValueError):self.prepare(root,parent,pointer,code)
                self.assertEqual(read_json(pointer)['run'],str(parent));self.assertFalse((root/'runs/linked').exists())

    def test_changed_prepared_request_is_not_resealed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);parent,pointer,_=self.fixture(root)
            (parent/'prepared/request.json').write_text('tampered')
            with self.assertRaises(IntegrityError):self.prepare(root,parent,pointer)
            self.assertFalse((root/'runs/linked').exists())

    def test_old_bootstrap_forwards_after_integration_without_copyback(self):
        spec=importlib.util.spec_from_file_location('integrator',run.ROOT/'scripts/integrate-editorial-development.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);_,pointer,_=self.fixture(root)
            dev=Path(read_json(pointer)['development'])
            with patch.object(module,'ROOT',dev),patch.object(module,'ORIGINAL',root), \
                 patch.object(module.sys,'argv',['bootstrap','resume']), \
                 patch.object(module,'integrate') as integrate,patch.object(module,'validate_destinations') as validate, \
                 patch.object(module.subprocess,'call',return_value=0) as forward:
                self.assertEqual(module.main(),0)
                forward.assert_called_once_with(['bash',str(root/'scripts/run-editorial-chapters.sh'),'resume'])
                integrate.assert_not_called();validate.assert_not_called()


if __name__=='__main__':unittest.main()
