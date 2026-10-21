"""Bounded batch/resume tests: synthetic saved evidence and in-memory HTTP only."""
import contextlib
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

import test_saved_review as support
from probe import cli
from probe import batch_review as runner
from probe.batch_inputs import prepare_batch, select_pages, validate_coverage, validate_response, verify_batch
from probe.common import atomic_json, files_manifest, read_json, sha, writer_lock
from probe.local_model import LocalClient
from probe.page_review import LIMITS
from probe.saved_pages import saved_pages


def transport(sent, actions=(), after=None, discovery_model=None):
    actions=iter(actions)
    def connection(client):
        wire=Mock(sock=None)
        def request(method,path,body=None,headers=None):
            if method=='GET':
                value={'data':[{'id':discovery_model or client.requested_model}]}
            else:
                payload=json.loads(body);sent.append(payload)
                data=json.loads(payload['messages'][0]['content'][0]['text'].split('REVIEW UNIT DATA:\n')[1])
                action=next(actions,'ok')
                if action=='connection':
                    raise ConnectionRefusedError('Synthetic connection refusal')
                if action=='interrupt':
                    raise KeyboardInterrupt
                proposal={'unit_id':data['unit_id'],'page_id':data['page_id'],'scope':data['scope'],
                    'complete':True,'reviewed_block_ids':[b['id'] for b in data['blocks']],
                    'missing_content_checked':data['scope']!='block_group','proposals':[]}
                value={'model':'different-model' if action.startswith('wrong_model') else client.model,
                    'choices':[{'finish_reason':'length' if action=='wrong_model_length' else 'stop',
                                'message':{'content':'{bad' if action=='invalid' else json.dumps(proposal)}}]}
                if after:
                    after(len(sent))
            raw=json.dumps(value).encode();response=Mock(status=200)
            response.getheader.return_value=str(len(raw));response.getheaders.return_value=[]
            response.read1.side_effect=io.BytesIO(raw).read1;wire.getresponse.return_value=response
            if method=='POST' and action=='body_timeout':
                response.read1.side_effect=TimeoutError('Synthetic timeout after HTTP 200 headers')
        wire.request.side_effect=request
        return wire,urlsplit(client.base_url)
    return connection


class BatchReviewTests(unittest.TestCase):
    def setUp(self):
        support.SavedReviewTests.setUp(self)
        self.limits={**LIMITS,'max_pages':1,'max_output_tokens':16384,'timeout_seconds':600}
        caps=read_json(self.preflight/'model/capabilities.json');caps['strict_json']['status']='unsupported'
        atomic_json(self.preflight/'model/capabilities.json',caps)
        self.preview=self.root/'batch-preview';self.preview.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            prepare_batch(self.root,self.run,self.preview,'fixture-native',1,2,'glm-test',self.config['base_url'],self.limits,'medium')
        self.output=self.root/'batch-result';self.output.mkdir()

    def execute(self, actions=(), resume=False, after=None, discovery_model=None):
        sent=[]
        with contextlib.redirect_stdout(io.StringIO()),patch.object(LocalClient,'_connection',transport(sent,actions,after,discovery_model)):
            code=runner.execute_batch(self.root,self.preview,self.preflight,self.output,self.config,resume=resume)
        return code,sent

    def change_native(self, transform):
        for record in self.state['units'].values():
            if record['source_id']!='fixture-native':
                continue
            path=self.run/record['attempt']/'output/middle_json.json';data=read_json(path)
            for page in data['pages']:
                transform(page)
            atomic_json(path,data);record['files']=files_manifest(path.parent)
        atomic_json(self.run/'state.json',self.state)

    def test_first_100_owned_selection_and_mapping_rejects_gaps_duplicates(self):
        template=saved_pages(self.root,self.run,'fixture-native')[0]
        pages=[]
        for n in range(1,121):
            pages.append({**template,'page_id':f'fixture-native-p{n:04d}',
                'page':{'selected_page':n,'original_physical_page':n+105,'owner':True}})
        pages.reverse()
        # Context overlap records are never owners and never count toward selection.
        pages += [{**pages[-1],'page':{**pages[-1]['page'],'owner':False}}]
        chosen=select_pages(pages,'fixture-native',1,100)
        self.assertEqual([p['page']['original_physical_page'] for p in chosen],list(range(106,206)))
        for invalid in (pages+[pages[0]],pages[1:]):
            # The missing-page case selects the full endpoint range containing page 120.
            with self.assertRaises(ValueError):
                select_pages(invalid,'fixture-native',21,100)
        with self.assertRaises(ValueError):select_pages(pages,'fixture-native',1,101)

    def test_whole_page_and_dense_splits_cover_all_blocks_and_source_area(self):
        def dense(page):
            base=copy.deepcopy(page['blocks'][3])
            page['blocks']=[{**copy.deepcopy(base),'index':i,'bbox':[.1,.04+i*.05,.9,.08+i*.05]} for i in range(16)]
        self.change_native(dense)
        preview=self.root/'dense';preview.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            meta=prepare_batch(self.root,self.run,preview,'fixture-native',1,2,'glm-test',self.config['base_url'],{**self.limits,'max_page_characters':14000},'medium')
        checked,pages=verify_batch(self.root,preview)
        self.assertEqual(meta,checked)
        for p in meta['pages']:
            units=[s for s in meta['units'] if s['page_id']==p['page_id']]
            self.assertGreater(len(units),2)
            self.assertEqual([b for s in units for b in s['block_ids']],p['block_ids'])
            self.assertEqual(sum(s['scope']=='page_omissions' for s in units),1)
            for s in units:
                self.assertLessEqual(s['budgets']['characters'],14000)
                data=read_json(preview/'units'/s['unit_id']/'input.json')
                self.assertIn('draft_by_block',data)
                if s['scope']=='page_omissions':
                    self.assertEqual(len(data['context_blocks']),16)
                    self.assertEqual([i['bbox'] for i in data['images']],[[0,0,1,1],[0,0,1,.52],[0,.48,1,1]])
        for mutation in ('drop_block','duplicate','drop_visual'):
            bad=copy.deepcopy(meta)
            if mutation=='drop_block':bad['units'][0]['block_ids'].pop()
            elif mutation=='duplicate':bad['units'].append(bad['units'][0])
            else:bad['units']=[s for s in bad['units'] if s['scope']!='page_omissions']
            with self.assertRaises(ValueError):validate_coverage(bad,pages)
        blocked=self.root/'overflow';blocked.mkdir()
        with contextlib.redirect_stdout(io.StringIO()),self.assertRaisesRegex(ValueError,'character limit'):
            prepare_batch(self.root,self.run,blocked,'fixture-native',1,2,'glm-test',self.config['base_url'],
                          {**self.limits,'max_page_characters':9000},'medium')
        self.assertFalse((blocked/'artifact-manifest.json').exists())

    def test_blank_recognition_still_requires_visual_missing_content_check(self):
        self.change_native(lambda page:page.update(blocks=[]))
        preview=self.root/'blank';preview.mkdir()
        with contextlib.redirect_stdout(io.StringIO()):
            meta=prepare_batch(self.root,self.run,preview,'fixture-native',1,2,'glm-test',self.config['base_url'],self.limits,'medium')
        self.assertEqual(len(meta['units']),2)
        data=read_json(preview/'units'/meta['units'][0]['unit_id']/'input.json')
        value={'unit_id':data['unit_id'],'page_id':data['page_id'],'scope':'whole_page','complete':True,
               'reviewed_block_ids':[],'missing_content_checked':False,'proposals':[]}
        with self.assertRaisesRegex(ValueError,'Visual omission'):validate_response(value,data)
        value['missing_content_checked']=True
        value['proposals']=[{'block_ids':[],'region_bbox':[.1,.1,.3,.3],'suggested_latex':'unreadable',
                             'issue':'Synthetic missing content','uncertain':True}]
        self.assertEqual(validate_response(value,data),value)

    def test_serialization_preservation_and_completed_resume_sends_nothing(self):
        before={p:files_manifest(p) for p in (self.run,self.preview,self.preflight)}
        code,sent=self.execute();self.assertEqual(code,0);self.assertEqual(len(sent),2)
        for payload in sent:
            self.assertNotIn('response_format',payload)
            self.assertEqual(payload['reasoning_effort'],'medium');self.assertEqual(payload['max_tokens'],16384)
            text=payload['messages'][0]['content'][0]['text']
            self.assertIn('Original source images establish what is printed',text)
            self.assertIn('RESPONSE SCHEMA:',text);self.assertNotIn('GOLD_ONLY_SENTINEL',text)
        code,sent=self.execute(resume=True);self.assertEqual(code,0);self.assertEqual(sent,[])
        state=read_json(self.output/'state.json');self.assertEqual(state['completed_pages'],2)
        self.assertEqual(state['automatically_accepted'],0)
        for p,manifest in before.items():self.assertEqual(files_manifest(p),manifest)

    def test_failures_continue_and_exactly_one_retry_survives_resumes(self):
        code,sent=self.execute(['invalid','ok','invalid'])
        self.assertEqual(code,2);self.assertEqual(len(sent),3)
        state=read_json(self.output/'state.json');records=list(state['units'].values())
        self.assertEqual([r['status'] for r in records],['failed','completed'])
        self.assertEqual([len(r['attempts']) for r in records],[2,1])
        before=files_manifest(self.output/'units')
        code,sent=self.execute(resume=True);self.assertEqual(code,2);self.assertFalse(sent)
        self.assertEqual(files_manifest(self.output/'units'),before)
        coverage=read_json(self.output/'coverage.json');self.assertTrue(coverage['pages'][0]['missing_block_ids'])

    def test_repeated_connection_failure_pauses_and_budget_persists(self):
        code,sent=self.execute(['connection','connection']);self.assertEqual(code,75);self.assertEqual(len(sent),2)
        self.assertEqual(read_json(self.output/'state.json')['consecutive_connection_failures'],2)
        total=2
        for remaining in (1,1):
            code,sent=self.execute(['connection'],resume=True);self.assertEqual(code,75);self.assertEqual(len(sent),remaining)
            total+=len(sent)
        code,sent=self.execute(resume=True);self.assertEqual(code,2);self.assertFalse(sent);self.assertEqual(total,4)

    def test_interruption_is_preserved_and_consumes_attempt(self):
        code,sent=self.execute(['interrupt']);self.assertEqual(code,130);self.assertEqual(len(sent),1)
        attempt=next((self.output/'units').glob('*/attempt-01'));before=files_manifest(attempt)
        code,sent=self.execute(resume=True);self.assertEqual(code,0);self.assertEqual(len(sent),2)
        self.assertEqual(files_manifest(attempt),before)
        self.assertEqual(sorted(len(r['attempts']) for r in read_json(self.output/'state.json')['units'].values()),[1,2])

    def test_repeated_timeouts_after_response_headers_also_pause(self):
        code,sent=self.execute(['body_timeout','body_timeout'])
        self.assertEqual(code,75);self.assertEqual(len(sent),2)
        self.assertEqual(read_json(self.output/'state.json')['consecutive_connection_failures'],2)
        records=list((self.output/'units').glob('*/attempt-01/attempts/*/record.json'))
        self.assertEqual(len(records),2)
        self.assertTrue(all(read_json(p)['http_status']==200 for p in records))

    def test_committed_answer_recovered_after_interruption_without_repeat(self):
        original=runner.atomic_json;fired=False
        def write(path,value):
            nonlocal fired
            original(path,value)
            if Path(path).name=='assistant-response.json' and not fired:
                fired=True;raise KeyboardInterrupt
        with patch.object(runner,'atomic_json',write):
            code,sent=self.execute()
        self.assertEqual(code,130);self.assertEqual(len(sent),1)
        self.assertEqual(read_json(self.output/'state.json')['counts']['completed'],1)
        code,sent=self.execute(resume=True);self.assertEqual(code,0);self.assertEqual(len(sent),1)

    def test_wrong_model_even_on_length_failure_stops_before_other_units(self):
        for action in ('wrong_model','wrong_model_length'):
            self.output=self.root/action;self.output.mkdir()
            code,sent=self.execute([action]);self.assertEqual(code,2);self.assertEqual(len(sent),1)
            self.assertEqual(read_json(self.output/'state.json')['status'],'stopped_identity')
            with self.assertRaises(runner.IntegrityError):self.execute(resume=True)

    def test_discovery_changed_alias_stops_without_chat(self):
        code,sent=self.execute(discovery_model='other-alias')
        self.assertEqual(code,2);self.assertFalse(sent)
        self.assertEqual(read_json(self.output/'state.json')['status'],'stopped_identity')

    def test_incompatible_resume_and_changed_attempt_evidence_are_rejected(self):
        self.execute()
        for filename in ('batch.json','units/'+read_json(self.preview/'batch.json')['units'][0]['unit_id']+'/request.json'):
            path=self.preview/filename;before=path.read_bytes();path.write_bytes(before+b' ')
            with self.assertRaisesRegex(ValueError,'evidence changed'):self.execute(resume=True)
            path.write_bytes(before)
        caps=self.preflight/'model/capabilities.json';before=caps.read_bytes();caps.write_bytes(before+b' ')
        with self.assertRaisesRegex(ValueError,'Incompatible resume'):self.execute(resume=True)
        caps.write_bytes(before)
        old=self.config['model'];self.config['model']='changed'
        with self.assertRaises(runner.IdentityError):self.execute(resume=True)
        self.config['model']=old
        result=next((self.output/'units').glob('*/attempt-01/outcome.json'));result.write_text('{}')
        code,sent=self.execute(resume=True);self.assertEqual(code,2);self.assertFalse(sent)

    def test_source_integrity_change_during_run_stops_next_dispatch(self):
        def change(count):
            if count==1:
                source=self.root/'fixture-native.pdf';source.write_bytes(source.read_bytes()+b'changed')
        code,sent=self.execute(after=change)
        self.assertEqual(code,2);self.assertEqual(len(sent),1)
        self.assertEqual(read_json(self.output/'state.json')['status'],'stopped_integrity')

    def test_status_bypasses_writer_lock_and_partial_bundle_is_append_only(self):
        self.execute(['interrupt'])
        with patch.object(cli,'ROOT',self.root),contextlib.redirect_stdout(io.StringIO()):
            with writer_lock(self.root/'runs'):
                self.assertEqual(cli.main(['batch-status','--run',str(self.output)]),0)
            first=cli.bundle_run(self.output);before=sha(first);second=cli.bundle_run(self.output)
        self.assertNotEqual(first,second);self.assertEqual(sha(first),before)


if __name__=='__main__':
    unittest.main()
