"""Display identities are snapshots of metadata, never guessed book names."""
import copy
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from probe import chapter_glm as runtime, chapter_concurrency as concurrent
from probe.common import fingerprint, read_json
from test_speed_suite import health

BODY={'model':'glm53-regular','stream':True,'reasoning_effort':'high','max_tokens':131072,
      'messages':[{'role':'user','content':'Preserve the assigned paper passage.'}]}
FILENAME='Bias in the Estimation of the Mean Reversion Parameter in Continu.pdf'
TITLE='Bias in the Estimation of the Mean Reversion Parameter in Continuous Time Models'
SECTION='Mean Reversion Bias — unit 1'


def fixture():
    return {'chapter_contract':'annotated-chapter-v1','execution_limits':{'calls':None,'attempts_per_unit':1},
        'timing_policy':'manual_only','first_dispatch':None,'calls':[],
        'tasks':[{'id':'mean-bias-1/convert','key':'mean-bias-1','source_key':'original-ead9d04e4c78147d','phase':'convert','status':'pending'}],
        'documents':{'original-ead9d04e4c78147d':{'filename':FILENAME,'title':TITLE}},
        'source_units':{'mean-bias-1':{'source_key':'original-ead9d04e4c78147d','section':{'title':SECTION}}}}


class FakeClient:
    sent=[]
    def __init__(self,*args,**kwargs):pass
    def discover_model(self,path):return {'selected_model':'glm53-regular'}
    def chapter_health(self,path):return {'context_length':1048576,'streams':{'decoding':0,'filling':0}},{}
    def chat(self,messages,dest,label,**options):
        self.sent.append((copy.deepcopy(messages),copy.deepcopy(options)))
        return {'content':'Answer','actual_model':'glm53-regular','finish_reason':'stop','http_status':200,'usage':{'completion_tokens':1}}


class SourceLoggingTests(unittest.TestCase):
    def setUp(self):FakeClient.sent=[]

    def test_ordinary_paper_transport_uses_filename_title_section_and_phase(self):
        state=fixture();body=copy.deepcopy(BODY);call=runtime.reserve(state,'mean-bias-1/convert',fingerprint(body));output=io.StringIO()
        with tempfile.TemporaryDirectory() as td,redirect_stdout(output):
            run=Path(td);answer,result=runtime.perform_reserved(run,call,body,continuous=True,admission_budget={},health_evidence={},client=FakeClient())
            self.assertEqual(read_json(run/'calls'/call['id']/'request.json'),BODY)
            self.assertEqual(read_json(run/'calls'/call['id']/'outcome.json')['display_identity'],call['display_identity'])
        line=output.getvalue()
        for value in (FILENAME,TITLE,SECTION,'Phase: convert'):self.assertIn(value,line)
        self.assertNotIn('Gatheral',line);self.assertNotIn('Book:',line)
        self.assertEqual(body,BODY);self.assertEqual(FakeClient.sent[0][0],BODY['messages'])
        self.assertEqual(FakeClient.sent[0][1],{'stream':True,'reasoning_effort':'high'})
        self.assertEqual(result['request_sha256'],fingerprint(BODY));self.assertEqual(answer,'Answer')

    def test_serial_invoke_captures_same_metadata_without_new_arguments(self):
        with tempfile.TemporaryDirectory() as td,redirect_stdout(io.StringIO()) as output:
            _,call=runtime.invoke(Path(td),fixture(),'mean-bias-1/convert',copy.deepcopy(BODY),client_factory=FakeClient)
        self.assertEqual(call['display_identity']['filename'],FILENAME);self.assertIn(SECTION,output.getvalue())

    def test_threaded_coordinator_saves_identity_before_transport(self):
        state=fixture();state.update(status='running',suite_protocol='originals-batch-v1',active_stage=1,
            production_stage={'task_ids':['mean-bias-1/convert']},concurrency_policy=copy.deepcopy(concurrent.POLICY),
            connection_failures=0,current_versions={},versions={})
        def transport(run,call,body,**options):
            durable=read_json(run/'state.json')['calls'][-1]
            self.assertEqual(durable['display_identity'],call['display_identity'])
            return runtime.perform_reserved(run,call,body,client=FakeClient(),**options)
        def finish(run,state,task,answer,call):task.update(status='conversion_completed',settled_call=call['id'])
        with tempfile.TemporaryDirectory() as td,redirect_stdout(io.StringIO()) as output:
            concurrent.coordinate(Path(td),state,state['tasks'],body_for=lambda *args:copy.deepcopy(BODY),finish=finish,
                verify=lambda:None,changed=lambda:None,sample=health,transport=transport,fixed_level=2,poll_seconds=.005)
        self.assertEqual(len(state['calls']),1);self.assertIn(FILENAME,output.getvalue());self.assertIn(SECTION,output.getvalue())

    def test_readiness_has_neutral_label(self):
        call=runtime.reserve(fixture(),'readiness','hash');line=runtime.reservation_message(Path('/run'),call)
        self.assertTrue(line.startswith('Model readiness.'));self.assertNotIn('Gatheral',line);self.assertNotIn('Unknown source',line)

    def test_missing_metadata_never_infers_book_from_identifier(self):
        for parent in ('ordinary/convert','gatheral-01/convert','bergomi-02/critic','klebaner/review'):
            state=fixture();state['tasks']=[];call=runtime.reserve(state,parent,'hash');line=runtime.reservation_message(Path('/run'),call)
            self.assertIn('Unknown source',line);self.assertIn('Unknown section',line)
            self.assertNotIn('The Volatility Surface',line);self.assertNotIn('Stochastic Volatility Modeling',line)

    def test_old_call_without_snapshot_is_unknown_not_migrated(self):
        call={'id':'call-old','parent':'ordinary/critic'};before=copy.deepcopy(call)
        self.assertIn('Unknown source',runtime.reservation_message(Path('/run'),call));self.assertEqual(call,before)

    def test_direct_task_metadata_and_section_take_precedence(self):
        state=fixture();state['tasks'][0].update(source_title='Actual paper',source_filename='actual.pdf',section={'title':'Assigned section'})
        identity=runtime.request_identity(state,'mean-bias-1/convert')
        self.assertEqual((identity['title'],identity['filename'],identity['section']),('Actual paper','actual.pdf','Assigned section'))

    def test_unit_title_is_used_when_task_section_has_only_block_metadata(self):
        state=fixture();state['tasks'][0]['section']={'blocks':['b1'],'text':'source'}
        self.assertEqual(runtime.request_identity(state,'mean-bias-1/convert')['section'],SECTION)

    def test_snapshot_survives_later_task_metadata_changes(self):
        state=fixture();call=runtime.reserve(state,'mean-bias-1/convert','hash')
        state['documents']['original-ead9d04e4c78147d']['filename']='changed.pdf';state['source_units']['mean-bias-1']['section']['title']='Changed'
        self.assertEqual(call['display_identity']['filename'],FILENAME);self.assertEqual(call['display_identity']['section'],SECTION)

    def test_malformed_optional_metadata_is_unknown_and_labels_stay_one_line(self):
        self.assertIsNone(runtime.request_identity({'tasks':None,'source_units':None,'documents':None},'x')['filename'])
        state=fixture();state['documents']['original-ead9d04e4c78147d']['filename']='paper\n\x1b.pdf'
        label=runtime.request_identity(state,'mean-bias-1/convert')['filename'];self.assertNotIn('\n',label);self.assertNotIn('\x1b',label)

    def test_existing_logs_and_call_records_are_preserved(self):
        history='Book: Gatheral, The Volatility Surface. Historical call.\n'
        state=fixture();past={'id':'call-001','parent':'old','status':'completed_response'};state['calls'].append(copy.deepcopy(past))
        call=runtime.reserve(state,'mean-bias-1/convert',fingerprint(BODY))
        with tempfile.TemporaryDirectory() as td:
            run=Path(td);log=run/'terminal.log';log.write_text(history)
            with log.open('a') as stream,redirect_stdout(stream):runtime.perform_reserved(run,call,BODY,continuous=True,admission_budget={},health_evidence={},client=FakeClient())
            text=log.read_text();self.assertTrue(text.startswith(history));self.assertIn(FILENAME,text[len(history):])
        self.assertEqual(state['calls'][0],past);self.assertNotIn('display_identity',state['calls'][0])


if __name__=='__main__':unittest.main()
