"""Pending-only continuation from a completed repair; no real model/compiler."""
import copy
import unittest
from unittest.mock import patch

import test_export_recovery as fixture
from test_recovery_critic import valid,proposal
from probe import experiment as ex,recovery
from probe.common import read_json,atomic_json,files_manifest
from probe.batch_review import IntegrityError
from probe.recovery_trial import prepare_continuation
from probe.evaluation_export import experiment_report,bundle


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ExportRecoveryTests();self.f.setUp();self.addCleanup(self.f.doCleanups)

    def repaired_parent(self,recovery_calls=80):
        f=self.f
        _,value=f.legacy_parent(recovery_calls=recovery_calls)
        self.gate=f.out;self.gate_before=files_manifest(self.gate)
        f.derivative()
        fixed=copy.deepcopy(value);fixed['proposals'][0]['fragment_kind']='math_body'
        fixture.RepairClient.replies=[fixed]
        with patch('probe.tex_compile.compare',return_value={
            'status':'preexisting_or_context_failure_unresolved','compiler_feedback_eligible':False,
            'original':{'status':'syntax_failure'},'proposed':{'status':'passed'}}):f.execute()
        self.parent=f.out;self.old_preview=f.preview
        self.parent_before=files_manifest(self.parent)
        self.parent_state=read_json(self.parent/'state.json')
        self.assertEqual(self.parent_state['status'],'repair_completed')
        return self.parent

    def prepare(self):
        f=self.f;preview=f.root/'continuation-preview';out=f.root/'continuation-run'
        result=prepare_continuation(self.parent,preview,out)
        f.preview=preview;f.out=out
        return result

    def execute(self,**kwargs):
        f=self.f
        return ex.execute(f.root,f.out,stage='continue',readiness=f.ready,
            client_factory=fixture.RepairClient,compiler_image=fixture.IMAGE,**kwargs)

    def test_exact_inheritance_new_code_binding_and_no_replay(self):
        self.repaired_parent();f=self.f
        old_meta=read_json(self.old_preview/'preview.json')
        current={**ex.code_hashes(),'experiment.py':'b'*64}
        with patch('probe.experiment.code_hashes',return_value=current):
            with self.assertRaises(IntegrityError):ex.verify_preview(self.old_preview)
            result=self.prepare()
            meta,_=ex.verify_preview(f.preview)
            self.assertEqual(meta['continuation_derivative']['allowed_units'],['pending'])
            self.assertNotIn('repair_derivative',meta)
            self.assertEqual((meta['config'],meta['limits']),(old_meta['config'],old_meta['limits']))
            for spec in read_json(f.preview/'units.json'):
                for key in ('data','request'):
                    self.assertEqual((f.preview/spec[key]).read_bytes(),(self.old_preview/spec[key]).read_bytes())
            self.assertEqual((f.preview/'units.json').read_bytes(),(self.old_preview/'units.json').read_bytes())
            state=read_json(f.out/'state.json')
            self.assertEqual(state['calls'],self.parent_state['calls'])
            self.assertEqual(state['elapsed_seconds'],self.parent_state['elapsed_seconds'])
            self.assertEqual(result['consumed_baselines'],1);self.assertEqual(result['consumed_recoveries'],1)
            for c in state['calls']:
                self.assertEqual(files_manifest(f.out/'calls'/c['id']),files_manifest(self.parent/'calls'/c['id']))
            d=read_json(f.preview/'units/pending/input.json');value=valid(d)
            value['proposals']=[proposal(d['blocks'][0]['id'],'Uncertain text.',uncertain=True)]
            value['proposal_categories']=['content'];fixture.RepairClient.replies=[value]
            with f.comparison():self.assertEqual(self.execute(),0)
            state=read_json(f.out/'state.json')
            self.assertEqual([c['parent'] for c in state['calls']],['1','1','pending'])
            self.assertEqual(fixture.RepairClient.sent[-1],read_json(f.preview/'units/pending/request.json'))
            summary=experiment_report(f.preview,f.out)
            self.assertEqual(summary['inherited_calls'],2);self.assertEqual(summary['current_run_calls'],1)
            self.assertEqual(summary['latest_proposal_resolutions'],{
                'exportable_proposed_compiled_original_unresolved':1,'deferred_uncertain':1})
            self.assertEqual(state['acceptance'],'UNACCEPTED')
            record=bundle(f.root,f.preview,f.out)
            import zipfile
            with zipfile.ZipFile(record['path']) as z:
                self.assertIn('prepared/continuation/provenance.json',z.namelist())
        self.assertEqual(files_manifest(self.parent),self.parent_before)
        self.assertEqual(files_manifest(self.gate),self.gate_before)

    def test_only_continue_with_bound_compiler_and_no_second_fork(self):
        self.repaired_parent();self.prepare();f=self.f
        with self.assertRaises(ValueError):ex.execute(f.root,f.out,stage='gate',readiness=f.ready)
        for image in (None,'sha256:'+'b'*64):
            with self.assertRaises(IntegrityError):
                ex.execute(f.root,f.out,stage='continue',readiness=f.ready,compiler_image=image)
        with self.assertRaisesRegex(ValueError,'already exists'):
            prepare_continuation(self.parent,f.root/'second-preview',f.root/'second-run')
        self.assertEqual(len(fixture.RepairClient.sent),2)

    def test_shared_budget_and_pending_resume_without_replaying_inherited(self):
        self.repaired_parent(recovery_calls=2);self.prepare();f=self.f
        d=read_json(f.preview/'units/pending/input.json');bad=valid(d);del bad['scope']
        other=valid(d);other['scope']='wrong';fixture.RepairClient.replies=[bad,other,valid(d)]
        fixture.RepairClient.pause_after=3;fixture.RepairClient.pause_file=f.out/'PAUSE'
        self.assertEqual(self.execute(),75)
        paused=read_json(f.out/'state.json');self.assertEqual(paused['status'],'paused_operator')
        (f.out/'PAUSE').unlink();fixture.RepairClient.pause_after=None
        self.execute(resume=True);state=read_json(f.out/'state.json')
        self.assertEqual(state['calls'][:2],self.parent_state['calls'])
        self.assertEqual([c['method'] for c in state['calls']],['baseline','export_feedback','baseline','json_feedback'])
        self.assertGreaterEqual(state['elapsed_seconds'],paused['elapsed_seconds'])
        self.assertIn('Recovery call budget exhausted',state['units']['pending']['limits'])
        self.assertEqual(len(fixture.RepairClient.replies),1)
        self.execute(resume=True);self.assertEqual(len(fixture.RepairClient.sent),4)

    def test_per_region_allowance_retains_consumed_repair(self):
        self.repaired_parent();self.prepare();f=self.f
        state=read_json(f.out/'state.json');limits=read_json(f.preview/'preview.json')['limits']
        recovery.reserve_budget(state,'1','json_feedback',limits)
        with self.assertRaisesRegex(ValueError,'Original parent recovery ceiling exhausted'):
            recovery.reserve_budget(state,'1','json_feedback',limits)
        d=read_json(f.preview/'units/pending/input.json')
        answers=[]
        for value in ('bad','different','still_wrong'):
            answer=valid(d);answer['scope']=value;answers.append(answer)
        fixture.RepairClient.replies=answers
        self.execute();state=read_json(f.out/'state.json')
        self.assertEqual(len(state['calls']),5)
        self.assertIn('Original parent recovery ceiling exhausted',state['units']['pending']['limits'])

    def test_inherited_accounting_or_completed_unit_cannot_be_reset(self):
        self.repaired_parent();self.prepare();f=self.f;original=read_json(f.out/'state.json')
        for change in ('calls','time','completed'):
            state=copy.deepcopy(original)
            if change=='calls':state['calls']=[]
            elif change=='time':state['elapsed_seconds']=0
            else:state['units']['1']['status']='pending'
            atomic_json(f.out/'state.json',state)
            with self.subTest(change=change),self.assertRaises(IntegrityError):self.execute()
        self.assertEqual(len(fixture.RepairClient.sent),2)

    def test_stale_source_and_parent_evidence_refused_before_dispatch(self):
        self.repaired_parent();self.prepare();f=self.f
        (self.parent/'calls/0002/outcome.json').write_text('{}')
        with self.assertRaises(IntegrityError):self.execute()
        self.assertEqual(len(fixture.RepairClient.sent),2)

    def test_unfinished_or_changed_parent_cannot_be_prepared(self):
        self.repaired_parent();f=self.f;original=read_json(self.parent/'state.json')
        for change in ('unfinished','time','compiler','gate'):
            state=copy.deepcopy(original)
            if change=='unfinished':state['status']='paused_operator'
            elif change=='time':state['elapsed_seconds']=0
            elif change=='compiler':state['compiler_image']='sha256:'+'b'*64
            else:state['gate']['passed']=False
            atomic_json(self.parent/'state.json',state)
            with self.subTest(change=change),self.assertRaises((ValueError,IntegrityError)):
                prepare_continuation(self.parent,f.root/'new-preview',f.root/'new-run')
            self.assertFalse((f.root/'new-preview').exists())


if __name__=='__main__':unittest.main()
