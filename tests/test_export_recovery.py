"""Export feedback and explicit historical-run inheritance; all transport mocked."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from probe import experiment as ex, recovery as recovery
from probe.common import read_json,atomic_json,sha,files_manifest
from probe.local_model import LocalClient
from probe.batch_review import IntegrityError
from probe.recovery_trial import CONFIG,save_unit,finish_preview,prepare_repair
from probe.evaluation_export import experiment_report
from test_recovery_critic import block,data,valid,proposal

ROOT=Path(__file__).resolve().parents[1]
SAVED=ROOT/'runs/recovery-vision-trial-20261023T192309Z-cdec02'
PREVIEW=ROOT/'runs/recovery-vision-input-20261023T192304Z-70e8b9'
IMAGE='sha256:'+'a'*64


class RepairClient(LocalClient):
    replies=[];sent=[];counter=0;pause_after=None;pause_file=None
    def _request(self,method,endpoint,payload,output_dir,label):
        folder=Path(output_dir)/'attempts'/str(RepairClient.counter)
        RepairClient.counter+=1;folder.mkdir(parents=True)
        atomic_json(folder/'request.json',{'body':payload})
        atomic_json(folder/'record.json',{'http_status':200,'latency_seconds':1})
        evidence={'attempt_dir':str(folder),'http_status':200,'latency_seconds':1}
        if method=='GET':return {'data':[{'id':self.requested_model}]},evidence
        RepairClient.sent.append(copy.deepcopy(payload))
        value=RepairClient.replies.pop(0)
        raw={'model':self.requested_model,'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}],
             'usage':{'completion_tokens':20,'completion_tokens_details':{'reasoning_tokens':10}}}
        atomic_json(folder/'response.raw',raw)
        if RepairClient.pause_after==len(RepairClient.sent):RepairClient.pause_file.touch()
        return raw,evidence


class ExportRecoveryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name)
        self.preview=self.root/'preview';self.out=self.root/'run'
        RepairClient.replies=[];RepairClient.sent=[];RepairClient.counter=0
        RepairClient.pause_after=None;RepairClient.pause_file=None
        idle=patch('probe.experiment.converter_idle',return_value={'owned_converter_pids':[]})
        idle.start();self.addCleanup(idle.stop)

    def setup_preview(self,d=None,body=None,identity='1',pending=False,recovery_calls=80):
        d=d or data();d['blocks'][0]=block(kind='equation',content='x^2') if body is None else d['blocks'][0]
        body=body or {'model':CONFIG['model'],'messages':[{'role':'user','content':json.dumps(d)}],
                      'max_tokens':16384,'stream':False,'reasoning_effort':'medium'}
        self.preview.mkdir();source=self.root/'source';source.write_text('unchanged source')
        units=[save_unit(self.preview,identity,d,body,kind='visual',gate=True)]
        if pending:units.append(save_unit(self.preview,'pending',data(2),{**body,'messages':[{'role':'user','content':json.dumps(data(2))}]},kind='visual',gate=False))
        finish_preview(self.preview,units,'visual',CONFIG,{str(source):sha(source)},
            {'baseline_calls':len(units),'recovery_calls':recovery_calls,'per_parent_recovery':2,'admission_seconds':21600},
            {'minimum_first':0,'minimum_final':1,'minimum_coverage':1},{'order':[u['id'] for u in units]})
        ex.initialize(self.preview,self.out)
        self.ready=self.root/'ready';self.ready.mkdir()
        atomic_json(self.ready/'readiness.json',{'config':CONFIG,'text':'passed','vision':'qualified','finished_at':ex.now()});ex.seal(self.ready)
        value=valid(d);value['proposals']=[proposal(d['blocks'][0]['id'],r'x^2')];value['proposal_categories']=['content']
        return d,value

    def execute(self,**kwargs):
        return ex.execute(self.root,self.out,stage='gate',readiness=self.ready,client_factory=RepairClient,compiler_image=IMAGE,**kwargs)

    def comparison(self):
        return patch('probe.tex_compile.compare',return_value={'status':'both_compiled','compiler_feedback_eligible':False})

    def test_export_feedback_has_exact_context_diagnostic_and_contract(self):
        d,value=self.setup_preview()
        answer={'actual_model':CONFIG['model'],'finish_reason':'stop','content':json.dumps(value)}
        result=ex.validate_completion(answer,{'kind':'visual'},d,CONFIG['model'])
        failure=recovery.export_failure(result,d,answer['content'])
        self.assertEqual(recovery.recovery_method(failure,CONFIG),'export_feedback')
        original=read_json(self.preview/'units/1/request.json')
        body=recovery.feedback_request(original,failure,recovery.VISUAL_SCHEMA,'export_feedback')
        self.assertEqual(body['messages'][:-1],original['messages'])
        self.assertIn('Raw TeX control or mathematics outside math mode',body['messages'][-1]['content'])
        self.assertIn('"allowed_fragment_kinds": ["latex_fragment", "math_body"]',body['messages'][-1]['content'])
        self.assertEqual(failure['content'],answer['content'])
        self.assertEqual(value['proposals'][0]['fragment_kind'],'latex_fragment')

    @unittest.skipUnless(SAVED.exists(),'Saved book response intentionally outside Git')
    def test_actual_v005_response_repairs_without_changing_mathematics(self):
        d=read_json(PREVIEW/'units/v005/input.json');body=read_json(PREVIEW/'units/v005/request.json')
        value=read_json(SAVED/'calls/0003/outcome.json')['answer']
        self.setup_preview(d,body,'v005')
        fixed=copy.deepcopy(value);fixed['proposals'][0]['fragment_kind']='math_body'
        RepairClient.replies=[value,fixed]
        with patch('probe.tex_compile.compare',return_value={'status':'preexisting_or_context_failure_unresolved',
                'original':{'status':'syntax_failure'},'proposed':{'status':'passed'},'compiler_feedback_eligible':False}) as compiler:self.execute()
        self.assertEqual(compiler.call_count,1)
        self.assertEqual(read_json(self.out/'state.json')['status'],'completed')
        first=read_json(self.out/'calls/0001/outcome.json');last=read_json(self.out/'calls/0002/outcome.json')
        self.assertEqual(first['response_validation'],'passed')
        self.assertEqual(first['failure']['kind'],'proposal_export_failure')
        self.assertEqual(last['export_checks'][0]['status'],'wrapper_required')
        self.assertEqual(last['compilation'][0]['proposed']['status'],'passed')
        self.assertEqual(last['compilation'][0]['original']['status'],'syntax_failure')
        self.assertEqual(last['compilation'][0]['original_input_basis']['raw_math_body'],d['blocks'][0]['native']['content'])
        self.assertIn(d['blocks'][0]['native']['content'],compiler.call_args.args[0])
        self.assertEqual(last['answer']['proposals'][0]['suggested_latex'],value['proposals'][0]['suggested_latex'])
        self.assertEqual(RepairClient.sent[1]['messages'][:-1],body['messages'])

    @unittest.skipUnless(SAVED.exists(),'Saved book responses intentionally outside Git')
    def test_saved_gate_controls_unchanged_and_only_v005_actionable(self):
        state=read_json(SAVED/'state.json');units={u['id']:u for u in read_json(PREVIEW/'units.json')};bad=[]
        for c in state['calls']:
            spec=units[c['parent']];d=read_json(PREVIEW/spec['data'])
            answer=read_json(SAVED/'calls'/c['id']/'assistant-response.json')
            result=ex.validate_completion(answer,spec,d,CONFIG['model'])
            self.assertEqual(result['export_checks'],read_json(SAVED/'calls'/c['id']/'outcome.json')['export_checks'])
            if recovery.export_failure(result,d,answer['content']):bad.append(c['parent'])
        self.assertEqual(bad,['v005'])

    def test_math_body_control_compiles_without_recovery(self):
        d,value=self.setup_preview();value['proposals'][0]['fragment_kind']='math_body'
        RepairClient.replies=[value]
        with self.comparison() as compiler:self.execute()
        self.assertEqual(len(RepairClient.sent),1);self.assertEqual(compiler.call_count,1)

    def test_invalid_repairs_exhaust_shared_allowance_and_remain_unresolved(self):
        d,value=self.setup_preview();second=copy.deepcopy(value);second['proposals'][0]['suggested_latex']+=' '
        third=copy.deepcopy(value);third['proposals'][0]['suggested_latex']+='  '
        RepairClient.replies=[value,second,third]
        with self.comparison() as compiler:self.execute()
        state=read_json(self.out/'state.json')
        self.assertEqual([c['method'] for c in state['calls']],['baseline','export_feedback','export_feedback'])
        self.assertEqual(state['units']['1']['status'],'failed');self.assertEqual(compiler.call_count,0)
        self.assertIn('Original parent recovery ceiling exhausted',state['units']['1']['limits'])
        self.execute(resume=True);self.assertEqual(len(RepairClient.sent),3)
        summary=experiment_report(self.preview,self.out)
        self.assertEqual(summary['first_attempt_json_schema_coverage_success'],1)
        self.assertEqual(summary['latest_proposal_resolutions'],{'unresolved_export':1})

    def test_json_and_export_repairs_share_allowance_across_resume(self):
        d,value=self.setup_preview();bad=copy.deepcopy(value);del bad['scope']
        fixed=copy.deepcopy(value);fixed['proposals'][0]['suggested_latex']=r'\[x^2\]'
        RepairClient.replies=[bad,value,fixed];RepairClient.pause_after=2;RepairClient.pause_file=self.out/'PAUSE'
        with self.comparison():
            self.execute();self.assertEqual(read_json(self.out/'state.json')['status'],'paused_operator')
            (self.out/'PAUSE').unlink();RepairClient.pause_after=None;self.execute(resume=True)
        self.assertEqual([c['method'] for c in read_json(self.out/'state.json')['calls']],['baseline','json_feedback','export_feedback'])
        self.assertEqual(len(RepairClient.sent),3)

    def test_dropped_proposals_cannot_be_laundered_by_second_json_repair(self):
        d,value=self.setup_preview();empty=valid(d)
        RepairClient.replies=[value,empty,empty]
        with self.comparison() as compiler:self.execute()
        state=read_json(self.out/'state.json')
        self.assertEqual(len(state['calls']),3);self.assertEqual(state['units']['1']['status'],'failed')
        self.assertEqual(compiler.call_count,0)
        self.assertIn('original_export_repair_anchor',RepairClient.sent[-1]['messages'][-1]['content'])

    def test_representation_repair_preserves_targets_other_fields_and_proposals(self):
        d,value=self.setup_preview();fixed=copy.deepcopy(value);fixed['proposals'][0]['fragment_kind']='math_body'
        recovery.preserve_substance(json.dumps(value),fixed,'export_feedback',[0])
        for field,replacement in [('uncertain',True),('block_ids',['another']),('issue','different'),('depends_on',['other'])]:
            changed=copy.deepcopy(fixed);changed['proposals'][0][field]=replacement
            with self.subTest(field=field),self.assertRaises(recovery.ValidationError):
                recovery.preserve_substance(json.dumps(value),changed,'export_feedback',[0])

    def test_configuration_and_deletion_do_not_route_to_export_repair(self):
        self.assertIsNone(recovery.recovery_method({'kind':'configuration'},CONFIG))
        d,value=self.setup_preview();value['proposals'][0].update(fragment_kind='delete',suggested_latex='')
        outcome=ex.validate_completion({'actual_model':CONFIG['model'],'finish_reason':'stop','content':json.dumps(value)},{'kind':'visual'},d,CONFIG['model'])
        self.assertIsNone(recovery.export_failure(outcome,d,json.dumps(value)))

    def test_repair_still_requires_identity_and_coverage_before_compilation(self):
        from probe.batch_review import IdentityError
        d,value=self.setup_preview();value['proposals'][0]['fragment_kind']='math_body'
        answer={'actual_model':'wrong','finish_reason':'stop','content':json.dumps(value)}
        with self.comparison() as compiler:
            with self.assertRaises(IdentityError):ex.finish_completion(answer,{'kind':'visual'},d,CONFIG['model'],self.root/'build',IMAGE)
            answer['actual_model']=CONFIG['model'];value['reviewed_block_ids']=[]
            answer['content']=json.dumps(value)
            with self.assertRaises(recovery.ValidationError):ex.finish_completion(answer,{'kind':'visual'},d,CONFIG['model'],self.root/'build',IMAGE)
            self.assertEqual(compiler.call_count,0)

    def legacy_parent(self,used_json_repair=False,recovery_calls=80):
        d,value=self.setup_preview(pending=True,recovery_calls=recovery_calls)
        malformed=copy.deepcopy(value);del malformed['scope']
        RepairClient.replies=[malformed,value] if used_json_repair else [value]
        def old_finish(answer,spec,data,model,*args,**kwargs):
            result=ex.validate_completion(answer,spec,data,model)
            result['compilation']=[{'status':'not_compiled_unsupported_fragment','proposal_index':0}]
            return result
        with patch('probe.experiment.finish_completion',side_effect=old_finish):self.execute()
        return d,value

    def derivative(self):
        parent=self.out;new_preview=self.root/'repair-preview';new_run=self.root/'repair-run'
        result=prepare_repair(parent,'1',new_preview,new_run)
        self.preview=new_preview;self.out=new_run
        return parent,result

    def test_derivative_inherits_budget_evidence_and_only_repairs_selected_unit(self):
        d,value=self.legacy_parent();before=files_manifest(self.out);parent_state=read_json(self.out/'state.json')
        old_preview=self.preview;parent,result=self.derivative()
        self.assertEqual(result['inherited_calls'],1)
        self.assertEqual(read_json(self.out/'state.json')['elapsed_seconds'],parent_state['elapsed_seconds'])
        self.assertEqual(files_manifest(parent),before)
        self.assertEqual((self.preview/'units/pending/request.json').read_bytes(),(old_preview/'units/pending/request.json').read_bytes())
        with self.assertRaises(ValueError):
            ex.execute(self.root,self.out,stage='continue',readiness=self.ready,client_factory=RepairClient,compiler_image=IMAGE)
        with self.assertRaises(IntegrityError):
            ex.execute(self.root,self.out,stage='gate',readiness=self.ready,client_factory=RepairClient)
        fixed=copy.deepcopy(value);fixed['proposals'][0]['fragment_kind']='math_body';RepairClient.replies=[fixed]
        with self.comparison():self.execute()
        state=read_json(self.out/'state.json')
        self.assertEqual(state['status'],'repair_completed');self.assertEqual(state['units']['pending']['status'],'pending')
        self.assertEqual([c['method'] for c in state['calls']],['baseline','export_feedback'])
        self.assertEqual(files_manifest(parent),before)
        self.assertEqual((parent/'calls/0001/outcome.json').read_bytes(),(self.out/'calls/0001/outcome.json').read_bytes())
        summary=experiment_report(self.preview,self.out)
        self.assertEqual(summary['inherited_calls'],1);self.assertEqual(summary['current_run_calls'],1)
        self.assertEqual(summary['latest_proposal_resolutions'],{'exportable_compiled_unaccepted':1})

    def test_derivative_cannot_reset_consumed_calls_or_fork_allowance(self):
        d,value=self.legacy_parent();parent,_=self.derivative()
        with self.assertRaises(ValueError):prepare_repair(parent,'1',self.root/'second-preview',self.root/'second-run')
        state=read_json(self.out/'state.json');state['calls']=[]
        atomic_json(self.out/'state.json',state)
        with self.assertRaises(IntegrityError):self.execute()
        self.assertEqual(len(RepairClient.sent),1)

    def test_derivative_retry_budget_survives_pause_and_invalid_repairs(self):
        d,value=self.legacy_parent();parent,_=self.derivative()
        second=copy.deepcopy(value);second['proposals'][0]['suggested_latex']+=' '
        third=copy.deepcopy(value);third['proposals'][0]['suggested_latex']+='  '
        RepairClient.replies=[second,third];RepairClient.pause_after=2;RepairClient.pause_file=self.out/'PAUSE'
        with self.comparison() as compiler:
            self.execute();self.assertEqual(read_json(self.out/'state.json')['status'],'paused_operator')
            (self.out/'PAUSE').unlink();RepairClient.pause_after=None;self.execute(resume=True)
        state=read_json(self.out/'state.json')
        self.assertEqual(state['status'],'repair_unresolved');self.assertEqual(len(state['calls']),3)
        self.assertEqual(state['units']['pending']['status'],'pending');self.assertEqual(compiler.call_count,0)
        self.execute(resume=True);self.assertEqual(len(RepairClient.sent),3)

    def test_inherited_json_repair_leaves_only_one_export_repair(self):
        d,value=self.legacy_parent(used_json_repair=True);parent,result=self.derivative()
        self.assertEqual(result['remaining_parent_recoveries'],1)
        still_bad=copy.deepcopy(value);still_bad['proposals'][0]['suggested_latex']+=' '
        RepairClient.replies=[still_bad]
        with self.comparison():self.execute()
        state=read_json(self.out/'state.json')
        self.assertEqual(state['status'],'repair_unresolved')
        self.assertEqual([c['method'] for c in state['calls']],['baseline','json_feedback','export_feedback'])

    def test_inherited_overall_recovery_limit_cannot_be_reset(self):
        self.legacy_parent(used_json_repair=True,recovery_calls=1)
        with self.assertRaisesRegex(ValueError,'Recovery call budget exhausted'):self.derivative()
        self.assertFalse((self.root/'repair-preview').exists())

    def test_stale_parent_seal_rejected_without_repair_preparation(self):
        self.legacy_parent();(self.out/'calls/0001/outcome.json').write_text('{}')
        with self.assertRaises(IntegrityError):self.derivative()
        self.assertFalse((self.root/'repair-preview').exists())

    def test_interruption_after_answer_revalidates_export_and_compilation(self):
        d,value=self.legacy_parent();self.derivative()
        fixed=copy.deepcopy(value);fixed['proposals'][0]['fragment_kind']='math_body';RepairClient.replies=[fixed]
        with self.comparison(),patch('probe.experiment.seal_outcome',side_effect=KeyboardInterrupt):
            self.execute()
        self.assertEqual(read_json(self.out/'state.json')['status'],'paused_interrupted')
        with self.comparison() as compiler:self.execute(resume=True)
        self.assertEqual(compiler.call_count,1)
        self.assertEqual(read_json(self.out/'state.json')['status'],'repair_completed')
        self.assertEqual(len(RepairClient.sent),2)


if __name__=='__main__':unittest.main()
