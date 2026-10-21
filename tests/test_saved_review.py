"""Saved-data export/page review tests. Synthetic PDFs, fake GLM; no network/OCR."""
import copy
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

import fitz

from probe import cli
from probe.common import atomic_json, files_manifest, read_json, sha
from probe.local_model import LocalClient
from probe.page_review import LIMITS, review_pages, validate_proposals, verify_preview, write_preview
from probe.portable_export import export_saved, math_fragment
from probe.saved_pages import converter_idle, saved_pages


class FakeClient:
    calls = []
    transform = staticmethod(lambda value: value)
    finish_reason = 'stop'
    actual_model = 'glm-test'

    def __init__(self, base_url, model, **kwargs):
        self.base_url, self.model = base_url, model

    def discover_model(self, output):
        return {'selected_model':self.model, 'available_models':[self.model]}

    def chat(self, messages, output, label, response_format=None):
        page = json.loads(messages[0]['content'][0]['text'].split('COMPLETE PAGE DATA:\n')[1])
        self.calls.append(page['page_id'])
        value = {'page_id':page['page_id'], 'complete':True,
                 'reviewed_block_ids':[b['id'] for b in page['blocks']],
                 'proposals':[{'block_ids':[], 'region_bbox':[.1,.1,.2,.2],
                    'suggested_latex':r'\alpha', 'issue':'Synthetic missing-region suggestion', 'uncertain':True}]}
        result = self.transform(value)
        return {'content':result if isinstance(result,str) else json.dumps(result),
                'finish_reason':self.finish_reason,'actual_model':self.actual_model}


class SavedReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root/'runs/conversion'
        self.run.mkdir(parents=True)
        self.config = {'local_only':True,'base_url':'http://127.0.0.1:8888/v1','model':'glm-test'}
        self.preflight = self.root/'preflight'
        atomic_json(self.preflight/'model/capabilities.json', {'endpoint':self.config['base_url'],
            'model_discovery':{'selected_model':'glm-test'},'text':{'status':'passed'},
            'vision':{'status':'qualified'},'strict_json':{'status':'passed'}})
        (self.root/'fixtures').mkdir()
        (self.root/'fixtures/known-math.tex').write_text('GOLD_ONLY_SENTINEL_MUST_NOT_REACH_MODEL')
        self.state = {'status':'conversion_completed_unreviewed','settings':{'sources':{}},'units':{}}
        for source in ('fixture-native','fixture-scan'):
            original = self.root/(source+'.pdf')
            with fitz.open() as pdf:
                for number in range(2):
                    page = pdf.new_page(width=300,height=400)
                    page.insert_text((40,60),'Synthetic page '+str(number))
                pdf.save(original)
            self.state['settings']['sources'][source] = {'pdf':original.name,'sha256':sha(original),
                                                        'pages':2,'original_pages':[21,22]}
            # Two windows with context overlap; each page has only one owner.
            for owned in range(2):
                unit = f'{source}-{owned}'
                attempt = self.run/'attempts'/unit
                (attempt/'output').mkdir(parents=True)
                shutil.copyfile(original,attempt/'input.pdf')
                mapping = [{'local_page_idx':i,'selected_page':i+1,'original_physical_page':i+21,'owner':i==owned} for i in range(2)]
                atomic_json(attempt/'page-map.json',mapping)
                pages = []
                for i in range(2):
                    blocks = [
                        {'index':0,'type':'aside_text','bbox':[.05,.2,.1,.6], 'content':[{'type':'text','content':'ASIDE α uncertain'}]},
                        {'index':1,'type':'equation','bbox':[.2,.2,.8,.3], 'content':r'\begin{array}{cc} a & b \\ 1 & 2 \end{array}'},
                        {'index':2,'type':'text','bbox':[.8,.3,.9,.4],'content':[{'type':'text','content':'DETACHED (Q.7)'}]},
                        {'index':3,'type':'text','bbox':[.1,.5,.8,.6],'content':[{'type':'equation_inline','content':'1'}, {'type':'text','content':', '}, {'type':'equation_inline','content':'2'}]},
                        {'index':4,'type':'text','bbox':[.1,.6,.8,.7],'content':[{'type':'text','content':'CONTROL prose; do not drop.'}]},
                    ]
                    pages.append({'page_idx':i,'blocks':blocks})
                atomic_json(attempt/'output/middle_json.json', {'schema':'docvortex.middle','schema_version':'2.0','pages':pages})
                (attempt/'output/document.tex').write_text('NATIVE OCR ONLY')
                record = {'source_id':source,'attempt':str(attempt.relative_to(self.run)),'status':'completed',
                          'files':files_manifest(attempt/'output'),
                          'evidence_files':[{'path':x,'sha256':sha(attempt/x)} for x in ('input.pdf','page-map.json')]}
                self.state['units'][unit] = record
        atomic_json(self.run/'state.json',self.state)
        FakeClient.calls = []
        FakeClient.transform = staticmethod(lambda value:value)
        FakeClient.finish_reason = 'stop'
        FakeClient.actual_model = 'glm-test'
        self.before = files_manifest(self.run)

    def make_preview(self, limits=None, crop_plan=None, reasoning_effort='server-default'):
        output = self.root/('preview-'+str(len(list(self.root.glob('preview-*')))))
        output.mkdir()
        ready = write_preview(self.root,self.run,output,'fixture-native,fixture-scan','glm-test',
                              self.config['base_url'],limits or dict(LIMITS),crop_plan,
                              reasoning_effort=reasoning_effort)
        return ready, output

    def serialized_review(self, preview):
        """Use the real client/HTTP serialization with an in-memory connection."""
        outgoing = []

        def connection(client):
            transport = Mock(sock=None)

            def request(method, path, body=None, headers=None):
                if method == 'GET':
                    value = {'data':[{'id':'glm-test'}]}
                else:
                    payload = json.loads(body)
                    outgoing.append(payload)
                    page = json.loads(payload['messages'][0]['content'][0]['text'].split('COMPLETE PAGE DATA:\n')[1])
                    answer = {'page_id':page['page_id'],'complete':True,
                              'reviewed_block_ids':[b['id'] for b in page['blocks']],'proposals':[]}
                    value = {'model':'glm-test','choices':[{'finish_reason':'stop',
                             'message':{'role':'assistant','content':json.dumps(answer)}}]}
                raw = json.dumps(value).encode()
                response = Mock(status=200)
                response.getheader.return_value = str(len(raw))
                response.getheaders.return_value = [('Content-Length',str(len(raw)))]
                response.read1.side_effect = io.BytesIO(raw).read1
                transport.getresponse.return_value = response

            transport.request.side_effect = request
            return transport, urlsplit(client.base_url)

        output = self.root/('review-'+str(len(list(self.root.glob('review-*')))))
        output.mkdir()
        with patch.object(LocalClient,'_connection',connection):
            ready = review_pages(self.root,self.run,preview,self.preflight,output,self.config)
        self.assertTrue(ready)
        return output, outgoing

    def refresh_preview_manifest(self, preview):
        atomic_json(preview/'artifact-manifest.json',
                    [entry for entry in files_manifest(preview) if entry['path'] != 'artifact-manifest.json'])

    def test_effort_preview_matches_actual_outgoing_request(self):
        _, baseline = self.make_preview()
        for effort in ('server-default','low','medium','high','max'):
            with self.subTest(effort=effort):
                _, preview = self.make_preview(reasoning_effort=effort)
                self.assertEqual(verify_preview(preview)['reasoning_effort'],effort)
                before = files_manifest(preview)
                output, outgoing = self.serialized_review(preview)
                self.assertEqual(len(outgoing),4)
                for record, sent in zip(verify_preview(preview)['pages'],outgoing):
                    relative = Path('pages')/record['page_id']
                    prepared = read_json(preview/relative/'request.json')
                    self.assertEqual(sent,prepared)
                    attempts = list((output/relative).glob('attempts/*/request.json'))
                    self.assertEqual(len(attempts),1)
                    self.assertEqual(read_json(attempts[0])['body'],prepared)
                    self.assertEqual(read_json(output/relative/'request.json'),prepared)
                    self.assertEqual((preview/relative/'page.json').read_bytes(),
                                     (baseline/relative/'page.json').read_bytes())
                    unchanged = {k:v for k,v in prepared.items() if k != 'reasoning_effort'}
                    self.assertEqual(unchanged,read_json(baseline/relative/'request.json'))
                    if effort == 'server-default':
                        self.assertNotIn('reasoning_effort',sent)
                    else:
                        self.assertEqual(sent['reasoning_effort'],effort)
                self.assertEqual(read_json(output/'summary.json')['reasoning_effort'],effort)
                self.assertEqual(read_json(output/'provenance.json')['reasoning_effort'],effort)
                self.assertEqual(files_manifest(preview),before)

    def test_effort_survives_unsupported_schema_wrapper(self):
        _, preview = self.make_preview(reasoning_effort='low')
        caps = read_json(self.preflight/'model/capabilities.json')
        caps['strict_json']['status'] = 'unsupported'
        atomic_json(self.preflight/'model/capabilities.json',caps)
        output, outgoing = self.serialized_review(preview)
        for record, sent in zip(verify_preview(preview)['pages'],outgoing):
            prepared = read_json(preview/'pages'/record['page_id']/'request.json')
            prepared.pop('response_format')
            self.assertEqual(sent,prepared)
            self.assertEqual(sent['reasoning_effort'],'low')
            self.assertEqual(read_json(output/'pages'/record['page_id']/'request.json'),sent)

    def test_legacy_preview_sends_no_effort_and_stays_unchanged(self):
        _, preview = self.make_preview()
        metadata = read_json(preview/'preview.json')
        del metadata['reasoning_effort']
        atomic_json(preview/'preview.json',metadata)
        self.refresh_preview_manifest(preview)
        before = files_manifest(preview)
        output, outgoing = self.serialized_review(preview)
        self.assertTrue(all('reasoning_effort' not in request for request in outgoing))
        self.assertEqual(read_json(output/'summary.json')['reasoning_effort'],'server-default')
        self.assertEqual(files_manifest(preview),before)

    def test_invalid_or_inconsistent_saved_effort_fails_before_discovery(self):
        _, preview = self.make_preview(reasoning_effort='low')
        metadata = read_json(preview/'preview.json')
        first = preview/'pages'/metadata['pages'][0]['page_id']/'request.json'
        original = read_json(first)
        for selection, wire in (('medium','low'),(None,'low'),([], 'low'),
                                ('low','high'),('low',None),('server-default','server-default'),
                                ('server-default',None)):
            with self.subTest(selection=selection,wire=wire):
                atomic_json(preview/'preview.json',{**metadata,'reasoning_effort':selection})
                atomic_json(first,{**original,'reasoning_effort':wire})
                self.refresh_preview_manifest(preview)
                factory = Mock(side_effect=AssertionError('Must not create client'))
                with self.assertRaisesRegex(ValueError,'reasoning effort'):
                    review_pages(self.root,self.run,preview,self.preflight,self.root/'unused',self.config,factory)
                factory.assert_not_called()
        for invalid in ('extreme',None,False,[]):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.make_preview(reasoning_effort=invalid)

    def test_effort_cli_choices_and_preview_only_scope(self):
        base = ['review','--mode','pages','--run','unused']
        self.assertIsNone(cli.parser().parse_args(base).page_reasoning_effort)
        self.assertFalse(hasattr(cli.parser().parse_args(['preflight']),'page_reasoning_effort'))
        for effort in ('server-default','low','medium','high','max'):
            args = cli.parser().parse_args(base+['--preview-only','--page-reasoning-effort',effort])
            self.assertEqual(args.page_reasoning_effort,effort)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.parser().parse_args(base+['--page-reasoning-effort','extreme'])
        for args in (base+['--page-reasoning-effort','low'],
                     ['review','--run','unused','--preview-only','--page-reasoning-effort','server-default']):
            with self.assertRaisesRegex(ValueError,'requires --mode pages --preview-only'):
                cli.cmd_review_dispatch(cli.parser().parse_args(args))

    def run_review(self, preview):
        output = self.root/('review-'+str(len(list(self.root.glob('review-*')))))
        output.mkdir()
        ready = review_pages(self.root,self.run,preview,self.preflight,output,self.config,FakeClient)
        return ready, output

    def test_export_is_portable_preserves_sources_and_accounts_for_asides(self):
        output = self.root/'export'
        output.mkdir()
        with patch('subprocess.Popen',side_effect=AssertionError('No OCR or services')), \
             patch.object(LocalClient,'chat',side_effect=AssertionError('No model calls')):
            export_saved(self.root,self.run,output,'fixture-native,fixture-scan')
        self.assertEqual(files_manifest(self.run),self.before)
        inventory = read_json(output/'inventory.json')
        self.assertEqual(len(inventory),20)
        self.assertTrue(all(x['status']=='unresolved' for x in inventory if x['kind']=='aside_text'))
        self.assertEqual(read_json(output/'summary.json')['omitted_blocks'],0)
        moved = self.root/'moved-laptop'
        shutil.move(output,moved)
        for page in moved.glob('pages/*'):
            tex = (page/'document.tex').read_text()
            self.assertIn(r'\documentclass[11pt]{article}',tex)
            self.assertNotIn('ctex',tex)
            self.assertIn('DETACHED (Q.7)',tex)
            self.assertIn(r'\(1\), \(2\)',tex)
            self.assertIn('Unresolved content',tex)
            self.assertTrue((page/'block-0.png').exists())
        self.assertTrue((moved/'evidence/fixture-native-0/input.pdf').is_file())
        self.assertEqual(read_json(moved/'provenance.json')['pages'][0]['page']['original_physical_page'],21)

    def test_complete_page_inputs_ownership_crops_and_no_gold(self):
        plan = self.root/'crops.json'
        atomic_json(plan,{'fixture-native-p0002':[{'bbox':[.05,.2,.1,.6],'rotation':90,'reason':'Explicit upright aside'}]})
        ready, preview = self.make_preview(crop_plan=plan)
        self.assertTrue(ready)
        records = verify_preview(preview)['pages']
        self.assertEqual(len(records),4)
        self.assertEqual(len(set(x['page_id'] for x in records)),4)
        for path in preview.glob('pages/*/request.json'):
            request = read_json(path)
            text = request['messages'][0]['content'][0]['text']
            self.assertNotIn('GOLD_ONLY_SENTINEL',text)
            data = json.loads(text.split('COMPLETE PAGE DATA:\n')[1])
            self.assertEqual(len(data['blocks']),5)
            self.assertEqual(data['blocks'][0]['native']['content'][0]['content'],'ASIDE α uncertain')
            self.assertIn('DETACHED (Q.7)',text)
            self.assertIn('CONTROL prose',text)
            self.assertEqual(data['blocks'][3]['native']['content'][1]['content'],', ')
        page = read_json(preview/'pages/fixture-native-p0002/page.json')
        self.assertEqual(page['page']['original_physical_page'],22)
        rotated = next(x for x in page['images'] if x['id']=='manual-0')
        self.assertEqual(rotated['rotation_clockwise_degrees'],90)
        self.assertEqual(rotated['bbox'],[.05,.2,.1,.6])
        self.assertEqual(rotated['bbox_pdf_points'],[15,80,30,240])
        self.assertEqual(len(rotated['pdf_to_raster_matrix']),6)
        self.assertEqual(page['blocks'][0]['bbox_pdf_points'],[15,80,30,240])
        self.assertGreater(rotated['width'],rotated['height'])
        self.assertIn('original',[x['id'] for x in page['images']])
        self.assertEqual(files_manifest(self.run),self.before)

    def test_valid_review_covers_all_pages_and_never_applies_proposals(self):
        _, preview = self.make_preview()
        with patch('subprocess.Popen',side_effect=AssertionError('No OCR or launchers')):
            ready, output = self.run_review(preview)
        self.assertTrue(ready)
        summary = read_json(output/'summary.json')
        self.assertEqual(summary['coverage'],'full')
        self.assertEqual(len(summary['completed_pages']),4)
        self.assertEqual(len(FakeClient.calls),4)
        self.assertEqual(summary['automatically_accepted'],0)
        self.assertEqual(summary['unaccepted_proposals'],4)
        self.assertIn('UNACCEPTED',(output/'review.html').read_text())
        self.assertEqual(files_manifest(self.run),self.before)

    def test_invalid_references_malformed_truncation_and_partial_coverage(self):
        _, preview = self.make_preview()
        def invalid_reference(value):
            value['proposals'][0]['block_ids']=['wrong-page:b0']
            return value
        def missing_control(value):
            value['reviewed_block_ids'].pop()
            return value
        for transform in (invalid_reference,missing_control,lambda value:'{"broken":',lambda value:{**value,'complete':False}):
            FakeClient.transform = staticmethod(transform)
            ready, output = self.run_review(preview)
            self.assertFalse(ready)
            summary = read_json(output/'summary.json')
            self.assertEqual(summary['coverage'],'failed')
            self.assertEqual(len(summary['failed_pages']),4)
            self.assertTrue(list(output.glob('pages/*/assistant-response.json')))
        FakeClient.transform = staticmethod(lambda value:value)
        FakeClient.finish_reason = 'length'
        ready, output = self.run_review(preview)
        self.assertFalse(ready)
        self.assertEqual(read_json(output/'summary.json')['coverage'],'failed')
        FakeClient.finish_reason = 'stop'
        FakeClient.transform = staticmethod(lambda value:value if value['page_id']=='fixture-native-p0001' else 'bad')
        ready, output = self.run_review(preview)
        self.assertFalse(ready)
        self.assertEqual(read_json(output/'summary.json')['coverage'],'partial')
        self.assertEqual(files_manifest(self.run),self.before)

    def test_overflow_and_missing_vision_stop_before_requests(self):
        ready, preview = self.make_preview(limits={**LIMITS,'max_page_characters':10})
        self.assertFalse(ready)
        with self.assertRaisesRegex(ValueError,'incomplete'):
            self.run_review(preview)
        self.assertEqual(FakeClient.calls,[])
        with self.assertRaisesRegex(ValueError,'page limit'):
            self.make_preview(limits={**LIMITS,'max_pages':3})
        _, preview = self.make_preview()
        caps = read_json(self.preflight/'model/capabilities.json')
        caps['vision']['status']='failed'
        atomic_json(self.preflight/'model/capabilities.json',caps)
        with self.assertRaisesRegex(ValueError,'image preflight'):
            self.run_review(preview)
        self.assertEqual(FakeClient.calls,[])

    def test_changed_saved_evidence_or_preview_is_rejected(self):
        _, preview = self.make_preview()
        (preview/'pages/fixture-native-p0001/request.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'changed'):
            self.run_review(preview)
        attempt = next((self.run/'attempts').iterdir())
        (attempt/'output/middle_json.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'changed'):
            saved_pages(self.root,self.run,'all')

    def test_crop_image_and_request_overflow_are_explicit(self):
        plan = self.root/'too-many-crops.json'
        atomic_json(plan,{'fixture-native-p0001':[
            {'bbox':[.1,.1,.2,.2],'rotation':0,'reason':'extra'} for _ in range(4)]})
        ready, preview = self.make_preview(crop_plan=plan)
        self.assertFalse(ready)
        self.assertIn('overflow',read_json(preview/'preview.json')['pages'][0]['error'])
        for limit in ('max_image_bytes','max_request_bytes'):
            ready, preview = self.make_preview(limits={**LIMITS,limit:10})
            self.assertFalse(ready)
            with self.assertRaisesRegex(ValueError,'incomplete'):
                self.run_review(preview)
        self.assertEqual(FakeClient.calls,[])

    def test_proposal_regions_and_types_are_validated(self):
        page = saved_pages(self.root,self.run,'all')[0]
        value = {'page_id':page['page_id'],'complete':True,
                 'reviewed_block_ids':[b['id'] for b in page['blocks']],
                 'proposals':[{'block_ids':[],'region_bbox':[.1,.1,.2,.2],
                               'suggested_latex':'x','issue':'missing region','uncertain':True}]}
        for field, invalid in (('region_bbox',None),('region_bbox',[0,0,2,1]),
                               ('region_bbox',[False,0,1,1]),('uncertain','false'),('suggested_latex',1)):
            changed = copy.deepcopy(value)
            changed['proposals'][0][field] = invalid
            with self.assertRaises(ValueError):
                validate_proposals(changed,page)

    def test_cli_offline_commands_never_start_inference(self):
        with patch.object(cli,'ROOT',self.root), \
             patch.object(cli,'config',return_value=self.config), \
             patch('subprocess.Popen',side_effect=AssertionError('No OCR or launcher process')), \
             patch.object(LocalClient,'chat',side_effect=AssertionError('No inference')), \
             patch.object(LocalClient,'discover_model',side_effect=AssertionError('No network discovery')):
            self.assertEqual(cli.main(['export','--run',str(self.run)]),0)
            self.assertEqual(cli.main(['review','--mode','pages','--preview-only','--run',str(self.run),'--model','glm-test']),0)
        self.assertEqual(files_manifest(self.run),self.before)

    def test_owned_worker_process_blocks_review_without_host_claim(self):
        proc = self.root/'fake-proc/123'
        proc.mkdir(parents=True)
        (proc/'cmdline').write_bytes(str(self.root/'probe/mineru_worker.py').encode()+b'\0')
        with self.assertRaisesRegex(ValueError,'converter processes'):
            converter_idle(self.root,proc.parent)

    def test_page_budget_does_not_weaken_default_client_limit(self):
        with self.assertRaises(ValueError):
            LocalClient(self.config['base_url'],max_tokens=8192)
        client = LocalClient(self.config['base_url'],max_tokens=8192,purpose='page_review')
        self.assertEqual(client.max_tokens,8192)
        with self.assertRaises(ValueError):
            LocalClient(self.config['base_url'],max_tokens=16385,purpose='page_review')

    def test_math_whitespace_is_preserved_and_unsupported_is_explicit(self):
        original = r'\frac { a + b } { 2 }'
        self.assertEqual(math_fragment(original)[0],original)
        for value in (r'\unknown{x}', 'α', r'\frac{a}{b', r'\begin{array}x\end{matrix}'):
            with self.assertRaises(ValueError):
                math_fragment(value)
