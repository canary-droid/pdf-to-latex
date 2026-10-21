"""Focused saved-OCR review and unsupported-grammar dispatch, without sockets."""
import copy
import io
import json
from unittest import TestCase
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

import test_saved_review as support
from probe import cli
from probe.common import atomic_json, files_manifest, read_json
from probe.focused_review import write_focused_preview, verify_focused_inputs
from probe.local_model import LocalClient
from probe.page_review import (LIMITS, FOCUSED_SCHEMA, LEGACY_FOCUSED_PROMPT,
                               request_payload, review_pages, verify_preview)
from probe.portable_export import render_block
from probe.saved_pages import saved_pages


def memory_transport(outgoing, transform=lambda response: response):
    def connection(client):
        transport = Mock(sock=None)
        def request(method, path, body=None, headers=None):
            if method == 'GET':
                value = {'data':[{'id':client.requested_model}]}
            else:
                payload = json.loads(body)
                outgoing.append(payload)
                data = json.loads(payload['messages'][0]['content'][0]['text'].split('SELECTED REGION DATA:\n')[1])
                answer = {'page_id':data['page_id'],'scope':'selected_blocks','complete':True,
                          'reviewed_block_ids':[b['id'] for b in data['blocks']],'proposals':[]}
                value = transform({'model':client.model,'choices':[{'finish_reason':'stop',
                    'message':{'role':'assistant','content':json.dumps(answer)}}]})
            raw = json.dumps(value).encode()
            response = Mock(status=200)
            response.getheader.return_value = str(len(raw))
            response.getheaders.return_value = [('Content-Length',str(len(raw)))]
            response.read1.side_effect = io.BytesIO(raw).read1
            transport.getresponse.return_value = response
        transport.request.side_effect = request
        return transport,urlsplit(client.base_url)
    return connection


class SavedOCRFocusTests(TestCase):
    def setUp(self):
        support.SavedReviewTests.setUp(self)
        self.config['model']='flash-next-tensorfold'
        self.config['base_url']='http://127.0.0.1:8890/v1'
        caps=read_json(self.preflight/'model/capabilities.json')
        caps.update(endpoint=self.config['base_url'],model_discovery={'selected_model':self.config['model']})
        caps['strict_json']={'status':'unsupported','reason':'mock missing xgrammar'}
        atomic_json(self.preflight/'model/capabilities.json',caps)
        # Deliberately broken equation in saved test data, rejected by the exporter.
        self.broken=r'e^{\int_0^T r(u)du} + \unknownmacro{'
        unit=self.state['units']['fixture-native-0']
        attempt=self.run/unit['attempt']
        native=read_json(attempt/'output/middle_json.json')
        native['pages'][0]['blocks'][1]['content']=self.broken
        atomic_json(attempt/'output/middle_json.json',native)
        unit['files']=files_manifest(attempt/'output')
        atomic_json(self.run/'state.json',self.state)
        self.before=files_manifest(self.run)
        self.selection=self.root/'blocks.json'
        atomic_json(self.selection,{'block_ids':['fixture-native-p0001:b3','fixture-native-p0001:b1','fixture-native-p0002:b1']})
        self.limits={**LIMITS,'max_pages':2,'max_output_tokens':16384,'timeout_seconds':600}
        self.preview=self.root/'ocr-focus'
        self.preview.mkdir()
        write_focused_preview(self.root,self.run,self.preview,None,self.selection,
            self.config['model'],self.config['base_url'],self.limits,reasoning_effort='high',sources='fixture-native')

    def test_raw_equation_is_data_without_relaxing_tex_validation(self):
        pages=saved_pages(self.root,self.run,'fixture-native')
        with self.assertRaisesRegex(ValueError,'Unsupported math macros'):
            render_block(pages[0]['blocks'][1])
        metadata=verify_preview(self.preview)
        verify_focused_inputs(self.root,self.run,self.preview,metadata,pages)
        self.assertEqual(metadata['draft_source'],'saved_ocr')
        self.assertIsNone(metadata['derivative_run'])
        page=read_json(self.preview/'pages/fixture-native-p0001-b1/page.json')
        self.assertEqual(page['draft_by_block'][0]['latex'],'\\[\n'+self.broken+'\n\\]')
        self.assertEqual(page['blocks'][0],pages[0]['blocks'][1])
        request=read_json(self.preview/'pages/fixture-native-p0001-b1/request.json')
        text=request['messages'][0]['content'][0]['text']
        self.assertIn('complete source-faithful replacement LaTeX',text)
        self.assertIn('Do not simplify, summarize, add definitions or repair apparent errors in the source',text)
        self.assertNotIn('GOLD_ONLY_SENTINEL',text)
        self.assertNotIn('Unsupported math macros',text)
        self.assertEqual(files_manifest(self.run),self.before)
        self.assertFalse((self.preview/'acceptance.json').exists())

    def test_actual_http_omits_unsupported_format_but_keeps_schema_and_settings(self):
        outgoing=[]
        out=self.root/'results';out.mkdir()
        before=files_manifest(self.preview)
        caps_before=files_manifest(self.preflight)
        with patch.object(LocalClient,'_connection',memory_transport(outgoing)):
            self.assertTrue(review_pages(self.root,self.run,self.preview,self.preflight,out,self.config))
        self.assertEqual(len(outgoing),3)
        for record,payload in zip(verify_preview(self.preview)['pages'],outgoing):
            prepared=read_json(self.preview/'pages'/record['page_id']/'request.json')
            prepared.pop('response_format')
            self.assertEqual(payload,prepared)
            self.assertNotIn('response_format',payload)
            self.assertIn(json.dumps(FOCUSED_SCHEMA),payload['messages'][0]['content'][0]['text'])
            self.assertEqual(payload['model'],'flash-next-tensorfold')
            self.assertEqual(payload['reasoning_effort'],'high')
            self.assertEqual(payload['max_tokens'],16384)
            proposal=read_json(out/'pages'/record['page_id']/'proposals.json')
            self.assertEqual(proposal['status'],'proposals_unaccepted')
        summary=read_json(out/'summary.json')
        self.assertEqual(summary['coverage'],'selected_regions_complete')
        self.assertFalse(summary['full_page_coverage'])
        self.assertEqual(summary['automatically_accepted'],0)
        self.assertEqual(files_manifest(self.preview),before)
        self.assertEqual(files_manifest(self.preflight),caps_before)
        self.assertEqual(files_manifest(self.run),self.before)

    def test_unconstrained_responses_still_reject_malformed_schema_identity_and_length(self):
        def bad_json(response):
            response['choices'][0]['message']['content']='{broken JSON'
            return response
        def wrong_scope(response):
            content=json.loads(response['choices'][0]['message']['content'])
            content['scope']='whole_page'
            response['choices'][0]['message']['content']=json.dumps(content)
            return response
        def wrong_block(response):
            content=json.loads(response['choices'][0]['message']['content'])
            content['reviewed_block_ids']=['other:block']
            response['choices'][0]['message']['content']=json.dumps(content)
            return response
        def wrong_model(response):
            response['model']='other-model';return response
        def length(response):
            response['choices'][0]['finish_reason']='length';return response
        for transform in (bad_json,wrong_scope,wrong_block,wrong_model,length):
            with self.subTest(case=transform.__name__):
                out=self.root/transform.__name__;out.mkdir()
                with patch.object(LocalClient,'_connection',memory_transport([],transform)):
                    self.assertFalse(review_pages(self.root,self.run,self.preview,self.preflight,out,self.config))
                summary=read_json(out/'summary.json')
                self.assertEqual(summary['coverage'],'failed')
                self.assertEqual(summary['completed_regions'],[])
                self.assertEqual(summary['automatically_accepted'],0)
                self.assertEqual(len(list(out.glob('pages/*/attempts/*/response.raw'))),3)
        self.assertEqual(files_manifest(self.run),self.before)

    def test_stale_or_rewritten_draft_is_rejected_before_discovery(self):
        page_path=self.preview/'pages/fixture-native-p0001-b1/page.json'
        page=read_json(page_path);page['draft_by_block'][0]['latex']='OPERATOR_ANSWER_MUST_NOT_REACH_MODEL'
        atomic_json(page_path,page)
        atomic_json(self.preview/'artifact-manifest.json',[e for e in files_manifest(self.preview) if e['path']!='artifact-manifest.json'])
        out=self.root/'invalid';out.mkdir()
        with patch.object(LocalClient,'discover_model') as discovery:
            with self.assertRaisesRegex(ValueError,'Focused draft/context differs'):
                review_pages(self.root,self.run,self.preview,self.preflight,out,self.config)
            discovery.assert_not_called()

    def test_cli_uses_saved_ocr_when_derivative_omitted(self):
        args=cli.parser().parse_args(['review','--mode','regions','--preview-only','--run',str(self.run),
            '--source','fixture-native','--block-selection',str(self.selection),'--model','flash-next-tensorfold',
            '--base-url',self.config['base_url'],'--page-reasoning-effort','high','--page-max-tokens','16384','--page-timeout','600'])
        with patch.object(cli,'ROOT',self.root),patch.object(LocalClient,'discover_model',side_effect=AssertionError('No offline discovery')):
            atomic_json(self.root/'config.example.json',self.config)
            self.assertEqual(cli.cmd_review_dispatch(args),0)

    def test_medium_single_region_retry_preserves_data_and_serializes_source_guidance(self):
        selection=self.root/'one-block.json'
        identity=read_json(self.selection)['block_ids'][0]
        atomic_json(selection,{'block_ids':[identity]})
        retry=self.root/'retry';retry.mkdir()
        limits={**self.limits,'max_pages':1}
        write_focused_preview(self.root,self.run,retry,None,selection,
            self.config['model'],self.config['base_url'],limits,reasoning_effort='medium',sources='fixture-native')
        metadata=verify_preview(retry)
        self.assertEqual(metadata['focused_prompt_version'],2)
        self.assertEqual(metadata['reasoning_effort'],'medium')
        self.assertEqual(metadata['selected_block_ids'],[identity])
        self.assertEqual(len(metadata['pages']),1)
        relative='pages/'+metadata['pages'][0]['page_id']
        for name in ('page.json','source.png','region.png'):
            self.assertEqual((retry/relative/name).read_bytes(),(self.preview/relative/name).read_bytes())
        outgoing=[];out=self.root/'retry-result';out.mkdir()
        before=files_manifest(retry)
        with patch.object(LocalClient,'_connection',memory_transport(outgoing)):
            self.assertTrue(review_pages(self.root,self.run,retry,self.preflight,out,self.config))
        self.assertEqual(len(outgoing),1)
        sent=outgoing[0];expected=read_json(retry/relative/'request.json');expected.pop('response_format')
        self.assertEqual(sent,expected)
        self.assertEqual(sent['reasoning_effort'],'medium')
        self.assertEqual(sent['max_tokens'],16384)
        self.assertEqual(metadata['limits']['timeout_seconds'],600)
        text=sent['messages'][0]['content'][0]['text']
        instructions=text.split('\nRESPONSE SCHEMA:\n')[0]
        for phrase in ('Original source images','are authoritative evidence','native.content',
                       'neighbouring OCR in context_blocks and draft_by_block are OCR-derived',
                       'Correct OCR errors using the images','errors actually printed in the book, not preserving OCR mistakes',
                       'genuinely unreadable','mark the proposal uncertain'):
            self.assertIn(phrase,instructions)
        for answer in ('GOLD_ONLY_SENTINEL','ANSWER_ONLY_SENTINEL','klebaner','dot { 1 }','gamma'):
            self.assertNotIn(answer,instructions)
        self.assertIn(json.dumps(FOCUSED_SCHEMA),text)
        self.assertEqual(read_json(out/relative/'proposals.json')['status'],'proposals_unaccepted')
        self.assertEqual(read_json(out/'provenance.json')['focused_prompt_version'],2)
        self.assertEqual(files_manifest(retry),before)
        self.assertEqual(files_manifest(self.run),self.before)

    def test_legacy_focused_preview_retains_original_prompt_and_inputs(self):
        metadata=read_json(self.preview/'preview.json');del metadata['focused_prompt_version']
        atomic_json(self.preview/'preview.json',metadata)
        for record in metadata['pages']:
            folder=self.preview/'pages'/record['page_id']
            page=read_json(folder/'page.json');del page['focused_prompt_version']
            atomic_json(folder/'page.json',page)
            payload,_=request_payload(page,folder,metadata['model'],metadata['limits'],reasoning_effort='high')
            atomic_json(folder/'request.json',payload)
        atomic_json(self.preview/'artifact-manifest.json',[e for e in files_manifest(self.preview) if e['path']!='artifact-manifest.json'])
        before=files_manifest(self.preview)
        outgoing=[];out=self.root/'legacy-result';out.mkdir()
        with patch.object(LocalClient,'_connection',memory_transport(outgoing)):
            self.assertTrue(review_pages(self.root,self.run,self.preview,self.preflight,out,self.config))
        for payload in outgoing:
            text=payload['messages'][0]['content'][0]['text']
            self.assertTrue(text.startswith(LEGACY_FOCUSED_PROMPT))
            self.assertNotIn('are authoritative evidence',text)
        self.assertEqual(read_json(out/'provenance.json')['focused_prompt_version'],1)
        self.assertEqual(files_manifest(self.preview),before)

    def test_changed_or_unknown_prompt_version_fails_before_discovery(self):
        metadata=read_json(self.preview/'preview.json')
        for version in (1,3,True,None):
            with self.subTest(version=version):
                atomic_json(self.preview/'preview.json',{**metadata,'focused_prompt_version':version})
                atomic_json(self.preview/'artifact-manifest.json',[e for e in files_manifest(self.preview) if e['path']!='artifact-manifest.json'])
                factory=Mock(side_effect=AssertionError('No client creation'))
                with self.assertRaisesRegex(ValueError,'prompt version|Focused draft/context differs'):
                    review_pages(self.root,self.run,self.preview,self.preflight,self.root/'unused',self.config,factory)
                factory.assert_not_called()
