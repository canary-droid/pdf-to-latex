"""Two dependent Kimi requests, tested without real credentials or inference."""
import copy
import json
from pathlib import Path
import unittest
import zipfile
from unittest.mock import patch
import test_kimi_escalation as fixtures
from probe import kimi_escalation as k
from probe.common import atomic_json,read_json,sha
from probe.batch_review import IntegrityError
from probe.experiment import seal
from scripts import kimi_escalation as cli

PROCESS=cli.process_answer
BUNDLE=cli.bundle
CASE_MAP=[{'case':13,'equations':['25a','25b','26'],'pages':[4],'blocks':['b1']},
          {'case':14,'equations':['27a','27b','28'],'pages':[4,5],'blocks':['b2']},
          *[{'case':n,'equations':[str(2*n-1),str(2*n)],'pages':[5 if n<18 else 6],'blocks':['b'+str(n)]} for n in range(15,19)]]

def document():
    body=[]
    for row in CASE_MAP:
        body.append(r'\subsection*{Case '+str(row['case'])+'.}\n')
        body.append('Synthetic density, parameter restrictions and characteristic function for this complete test case. ')
        for n in row['equations']:body.append(r'\begin{equation}x_{'+n+r'}=1\tag{'+n+r'}\end{equation}')
    return '\\documentclass{article}\n\\usepackage{amsmath}\n\\begin{document}\n'+'\n'.join(body)+'\n\\end{document}\n'


class ChainTests(unittest.TestCase):
    setUp=fixtures.KimiTests.setUp
    start=fixtures.KimiTests.start
    authorise=fixtures.KimiTests.authorise
    client=fixtures.KimiTests.client
    http=fixtures.KimiTests.http
    worker_fixture=fixtures.KimiTests.worker_fixture

    def chain(self,*,missing=False,edit=False,pause=False):
        client=self.worker_fixture();data,ledger,state=cli.verify_run(self.run)
        data['config']=self.config
        data['qualification_reuse']={'run':'settled-synthetic-pilot','extra_paid_readiness':0}
        data['tasks']=data['tasks'][:2]
        first,second=data['tasks'];first.update(own_draft_chain=True,case_map=CASE_MAP)
        second.update(operation='review',draft_from=first['id'],own_draft_chain=True,case_map=CASE_MAP)
        for task in data['tasks']:task.update(reservation_usd='1.302331392',source_run=data['source_parent'])
        plan=self.root/'plan';folder=plan/'tasks'/second['id'];folder.mkdir(parents=True)
        for name,text in [('source-passage.tex','SOURCE ONLY'),('secondary.txt','WITHHELD'),('context.tex','DEFINITIONS ONLY')]:
            (folder/name).write_text(text)
        atomic_json(self.run/'state.json',{'status':'prepared','tasks':{t['id']:{'status':'pending'} for t in data['tasks']},'live_qualified':data['qualification_reuse']})
        self.start(patch.object(cli,'process_answer',side_effect=PROCESS))
        compiler=self.start(patch.object(cli.compiler_environment,'compile_saved',return_value={'status':'passed','compilation_claim':True}))
        self.start(patch.object(cli.local.books,'asset_map',return_value={}))
        original=client._http
        def transport(method,path,body=None):
            status,raw,elapsed=original(method,path,body)
            if method=='POST':
                response=json.loads(raw)
                if 'response_format' not in body:
                    tex=document().replace(r'\tag{34}','') if missing else document()
                    response['choices'][0]['message']['content']='```tex\n'+tex+'```\nCONVERTER_ACCURACY_SENTINEL'
                    if pause:(self.run/'pause.json').write_text('{}')
                else:
                    payload=json.loads(body['messages'][0]['content'][0]['text'].split('\n',1)[1])
                    findings=[{'status':'edit','old':r'x_{33}=1','new':r'x_{33}=2','source':'synthetic p5 eq33','reason':'Synthetic located correction'}] if edit else []
                    response['choices'][0]['message']['content']=json.dumps({'base_sha256':payload['base_sha256'],'findings':findings})
                response['choices'][0]['message']['reasoning']='CONVERTER_REASONING_SENTINEL'
                raw=json.dumps(response).encode()
            return status,raw,elapsed
        client._http=transport
        return data,client,compiler

    def test_two_requests_fresh_critic_exact_new_draft_and_no_reasoning_guidance(self):
        data,client,compiler=self.chain();cli.worker(self.run)
        state=read_json(self.run/'state.json');self.assertEqual(state['status'],'finished')
        posts=[b for method,path,b in self.sent if method=='POST'];self.assertEqual(len(posts),2)
        critic=posts[1];payload=json.loads(critic['messages'][0]['content'][0]['text'].split('\n',1)[1])
        draft=self.run/'calls/task-0/candidate.tex'
        self.assertEqual(payload['draft_passage'],draft.read_text());self.assertEqual(payload['base_sha256'],sha(draft))
        self.assertEqual(len(critic['messages']),1);self.assertNotIn('CONVERTER_ACCURACY_SENTINEL',json.dumps(critic));self.assertNotIn('CONVERTER_REASONING_SENTINEL',json.dumps(critic))
        self.assertEqual(critic['reasoning'],{'effort':'high','exclude':False});self.assertEqual(critic['max_tokens'],32768)
        self.assertEqual(compiler.call_count,2)
        self.assertTrue((self.run/'calls/task-0/accuracy-notes.txt').exists())
        self.assertEqual(read_json(self.run/'calls/task-1/coverage.json')['mathematical_fidelity'],'not established')
        count=len(self.sent);cli.worker(self.run);self.assertEqual(len(self.sent),count)

    def test_applied_edit_preserves_initial_and_has_reviewed_diff(self):
        self.chain(edit=True);cli.worker(self.run)
        self.assertIn('x_{33}=1',(self.run/'calls/task-0/candidate.tex').read_text())
        self.assertIn('x_{33}=2',(self.run/'calls/task-1/candidate.tex').read_text())
        self.assertIn('+', (self.run/'calls/task-1/change.diff').read_text())
        self.assertEqual(read_json(self.run/'calls/task-1/accuracy.json')['findings'][0]['disposition'],'applied_model_claim')

    def test_missing_number_stops_critic_but_preserves_and_compiles_initial(self):
        _,_,compiler=self.chain(missing=True);cli.worker(self.run)
        state=read_json(self.run/'state.json');self.assertEqual(state['status'],'finished_with_failures')
        self.assertEqual(state['tasks']['task-1']['status'],'skipped_conversion_not_usable')
        self.assertEqual(sum(m=='POST' for m,p,b in self.sent),1);self.assertEqual(compiler.call_count,1)
        self.assertIn('34',state['tasks']['task-0']['coverage']['cases'][4]['missing_explicit_numbers'])

    def test_truncation_stops_chain_without_extra_paid_control(self):
        _,_,compiler=self.chain();self.actions=['length'];cli.worker(self.run)
        state=read_json(self.run/'state.json');self.assertEqual(state['status'],'finished_with_failures')
        self.assertEqual(state['tasks']['task-1']['status'],'skipped_conversion_not_usable')
        self.assertEqual(sum(m=='POST' for m,p,b in self.sent),1);self.assertEqual(compiler.call_count,0)

    def test_pause_resume_preserves_completed_converter_and_uses_exact_draft(self):
        self.chain(pause=True);cli.worker(self.run);self.assertEqual(read_json(self.run/'state.json')['status'],'paused')
        original=(self.run/'calls/task-0/candidate.tex').read_bytes();(self.run/'pause.json').unlink();cli.worker(self.run)
        self.assertEqual(read_json(self.run/'state.json')['status'],'finished');self.assertEqual(sum(m=='POST' for m,p,b in self.sent),2)
        self.assertEqual((self.run/'calls/task-0/candidate.tex').read_bytes(),original)

    def test_modified_converter_draft_is_rejected_before_critic(self):
        data,_,_=self.chain(pause=True);cli.worker(self.run)
        (self.run/'calls/task-0/candidate.tex').write_text('changed')
        with self.assertRaisesRegex(IntegrityError,'draft changed'):cli.materialize_task(self.run,data,data['tasks'][1])
        self.assertEqual(sum(m=='POST' for m,p,b in self.sent),1)

    def test_uncertain_initial_request_never_replayed_on_resume(self):
        self.chain();self.actions=['disconnect'];cli.worker(self.run);cli.worker(self.run)
        self.assertEqual(read_json(self.run/'state.json')['status'],'blocked');self.assertEqual(sum(m=='POST' for m,p,b in self.sent),1)

    def test_final_bundle_contains_both_actual_requests_versions_pdfs_and_metrics(self):
        data,_,_=self.chain();cli.worker(self.run);plan=self.root/'plan'
        for name in ('plan.json','public-metadata.json','prior-billing.json'):atomic_json(plan/name,{'synthetic':True})
        for task in data['tasks']:
            (plan/'tasks'/task['id']).mkdir(parents=True,exist_ok=True)
            p=self.run/'calls'/task['id']/'build/attempt-1/document.pdf';p.parent.mkdir(parents=True);p.write_bytes(b'%PDF-synthetic-compiler-output')
        dest=BUNDLE(self.run)
        with zipfile.ZipFile(dest) as z:
            self.assertIsNone(z.testzip())
            for task in data['tasks']:
                for name in ('request.json','response.raw','reasoning.txt','candidate.tex','coverage.json','build/attempt-1/document.pdf'):
                    self.assertIn('calls/'+task['id']+'/'+name,z.namelist())
            metrics=json.loads(z.read('results-and-costs.json'));self.assertEqual(len(metrics),2)
            self.assertTrue(all(m['actual_cost_usd']=='.02' or m['actual_cost_usd']=='0.02' for m in metrics))
            self.assertIn('calls/task-1/change.diff',z.namelist());self.assertIn('files-sha256.json',z.namelist())

    def test_coverage_is_located_not_merely_global_tag_presence(self):
        original=document();self.assertTrue(k.chain_coverage(original,CASE_MAP)['usable_for_critic'])
        tex=original.replace(r'\tag{34}',r'\tag{99}').replace(r'\tag{36}',r'\tag{36}\tag{34}')
        result=k.chain_coverage(tex,CASE_MAP);self.assertFalse(result['usable_for_critic'])
        self.assertEqual(result['cases'][4]['missing_explicit_numbers'],['34'])
        self.assertFalse(k.chain_coverage(original.replace(r'\tag{34}','% \\tag{34}\n'),CASE_MAP)['usable_for_critic'])

    def test_chain_spec_has_two_phases_no_extra_control_and_complete_case_bounds(self):
        spec=cli.own_draft_spec();self.assertEqual(len(spec['tasks']),2)
        self.assertTrue(all(t['primary_start']==r'^Case 13\.' and t['primary_end']==r'^Case 19\.' for t in spec['tasks']))
        self.assertEqual(spec['tasks'][1]['draft_from'],spec['tasks'][0]['id'])
        self.assertFalse(any(t['control'] for t in spec['tasks']))

    def test_critic_template_image_evidence_and_no_garbled_secondary(self):
        task={**self.task,'operation':'review','own_draft_chain':True}
        body=k.build_body(self.config,task,'MINERU SOURCE','Native PDF text withheld','DEFINITIONS',k.CHAIN_DRAFT_SLOT,[[0,len(k.CHAIN_DRAFT_SLOT)]])
        text=json.dumps(body);self.assertIn(k.CHAIN_DRAFT_SLOT,text);self.assertIn('Do not add style-only findings',text)
        self.assertNotIn('CONVERTER_ACCURACY_SENTINEL',text)

    def qualified_fixture(self):
        metadata=fixtures.metadata();metadata['model']['canonical_slug']='synthetic-k3-revision'
        plan=self.root/'old-plan';plan.mkdir();atomic_json(plan/'public-metadata.json',metadata);seal(plan)
        binding=read_json(self.run/'binding.json');binding.update(plan_path=str(plan),frozen={str(plan/'public-metadata.json'):sha(plan/'public-metadata.json')},code={'old_executor.py':'historical-code-identity'})
        atomic_json(self.run/'binding.json',binding);(self.run/'billing.json').unlink();self.authorise();k.ledger(self.run,create=True)
        image=self.root/'source.png';image.write_bytes(b'\x89PNG\r\n\x1a\nsynthetic-only')
        asset={'path':str(image),'sha256':sha(image),'source_id':self.task['source_id'],'source_sha256':self.task['source_sha256'],'page':3,'bbox':[0,0,1,1]}
        body=k.build_body(self.config,self.task,'source','','',assets=[asset]);self.client().dispatch(self.task,body,self.run/'calls/selected')
        atomic_json(self.run/'calls/selected/result.json',{'status':'candidate_saved'})
        atomic_json(self.run/'state.json',{'status':'finished','live_qualified':{'call':'selected'}})
        return metadata

    def test_reuses_observed_qualification_after_executor_extension_without_new_call(self):
        metadata=self.qualified_fixture();before=len(self.sent)
        proof=k.reused_qualification(self.run,self.config,metadata)
        self.assertEqual(proof['extra_paid_readiness'],0);self.assertEqual(len(self.sent),before)
        self.assertIn(str(self.run/'calls/selected/request.json'),proof['frozen'])

    def test_changed_model_revision_or_reasoning_cannot_reuse_qualification(self):
        metadata=self.qualified_fixture();changed=copy.deepcopy(metadata);changed['model']['canonical_slug']='another-model'
        with self.assertRaises(k.IdentityError):k.reused_qualification(self.run,self.config,changed)
        config=copy.deepcopy(self.config);config['reasoning']['effort']='low'
        with self.assertRaises(k.IdentityError):k.reused_qualification(self.run,config,metadata)

    def test_unsettled_qualification_cost_or_modified_request_fails_closed(self):
        metadata=self.qualified_fixture()
        request=self.run/'calls/selected/request.json';request.write_text(request.read_text().replace('source','mutated'))
        with self.assertRaises(IntegrityError):k.reused_qualification(self.run,self.config,metadata)


if __name__=='__main__':unittest.main()
