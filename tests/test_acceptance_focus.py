"""Explicit acceptance and selected-region contracts, with in-memory HTTP only."""
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

import test_saved_review as support
from probe import cli
from probe.acceptance import apply_accepted, make_plan, validated_selection, verify_derivative
from probe.common import atomic_json, files_manifest, read_json, sha
from probe.focused_review import select_blocks, verify_focused_inputs, write_focused_preview
from probe.local_model import LocalClient
from probe.page_review import LIMITS, review_pages, validate_review_response, verify_preview, write_preview
from probe.portable_export import accepted_fragment, render_block
from probe.saved_pages import saved_pages


def transport(outgoing, propose):
    def connection(client):
        sock = Mock(sock=None)
        def request(method, path, body=None, headers=None):
            if method == 'GET':
                value = {'data':[{'id':client.requested_model}]}
            else:
                payload = json.loads(body)
                outgoing.append(payload)
                text = payload['messages'][0]['content'][0]['text']
                focused = '\nSELECTED REGION DATA:\n' in text
                data = json.loads(text.split('\nSELECTED REGION DATA:\n' if focused else '\nCOMPLETE PAGE DATA:\n')[1])
                answer = {'page_id':data['page_id'],'complete':True,
                          'reviewed_block_ids':[b['id'] for b in data['blocks']], 'proposals':propose(data)}
                if focused:
                    answer['scope'] = 'selected_blocks'
                value = {'model':client.model,'choices':[{'finish_reason':'stop',
                         'message':{'role':'assistant','content':json.dumps(answer)}}]}
            raw = json.dumps(value).encode()
            response = Mock(status=200)
            response.getheader.return_value = str(len(raw))
            response.getheaders.return_value = [('Content-Length',str(len(raw)))]
            response.read1.side_effect = io.BytesIO(raw).read1
            sock.getresponse.return_value = response
        sock.request.side_effect = request
        return sock,urlsplit(client.base_url)
    return connection


class AcceptanceFocusTests(unittest.TestCase):
    def setUp(self):
        support.SavedReviewTests.setUp(self)
        self.preview = self.root/'high-preview'
        self.preview.mkdir()
        self.limits = {**LIMITS,'max_pages':2,'max_output_tokens':16384,'timeout_seconds':600}
        write_preview(self.root,self.run,self.preview,'fixture-native','glm-test',self.config['base_url'],
                      self.limits,reasoning_effort='high')
        self.review = self.root/'high-review'
        self.review.mkdir()
        def propose(page):
            if page['page_id'].endswith('0001'):
                return []
            suggestions = [r'\rotatebox{90}{Aside: $\alpha_1 \neq \alpha^1$}',
                           '\\[\nx=1\\tag{Q.1}\n\\]', '', '\\[\ny=2\\tag{Q.2}\n\\]',
                           'NOT AUTHORIZED EVEN IF CERTAIN']
            return [{'block_ids':[b['id']],'region_bbox':b['bbox'],'suggested_latex':latex,
                     'issue':'Saved synthetic proposal','uncertain':i == 0}
                    for i,(b,latex) in enumerate(zip(page['blocks'],suggestions))]
        with patch.object(LocalClient,'_connection',transport([],propose)):
            self.assertTrue(review_pages(self.root,self.run,self.preview,self.preflight,self.review,self.config))
        self.plan = make_plan(self.root,self.run,self.review,self.preview)
        ids = [p['proposal_id'] for p in self.plan['catalog']]
        self.plan.update(authorization='Explicit test operator selection; no certainty inference',
            selected=[{'proposal_id':x,'operation':'delete' if i==2 else 'replace'} for i,x in enumerate(ids[:4])],
            correction_groups=[ids[1:4]],unresolved_issues=[{'block_id':'fixture-native-p0001:b3',
                                                        'note':'ANSWER_ONLY_SENTINEL_MUST_NOT_REACH_MODEL'}])
        self.plan_path = self.root/'selection.json'
        self.derivative = self.root/'derivative'

    def apply(self):
        atomic_json(self.plan_path,self.plan)
        return apply_accepted(self.root,self.plan_path,self.derivative)

    def focused(self, ids=None):
        self.apply()
        selection = self.root/'blocks.json'
        atomic_json(selection,{'block_ids':ids or ['fixture-native-p0001:b3','fixture-native-p0001:b1','fixture-native-p0002:b4']})
        preview = self.root/'focus-preview'
        preview.mkdir()
        self.assertTrue(write_focused_preview(self.root,self.run,preview,self.derivative,selection,
            'glm-test',self.config['base_url'],self.limits,reasoning_effort='high'))
        return preview

    def test_bound_application_preserves_sources_order_unaffected_content_and_deletion(self):
        before = {p:files_manifest(p) for p in (self.run,self.review,self.preview)}
        self.apply()
        inventory = verify_derivative(self.root,self.run,self.derivative)
        pages = saved_pages(self.root,self.run,'fixture-native')
        self.assertEqual([b['id'] for p in pages for b in p['blocks']],[e['block_id'] for e in inventory])
        self.assertEqual(len(inventory),10)
        for page in pages:
            document = (self.derivative/'pages'/page['page_id']/'document.tex').read_text()
            for block in page['blocks']:
                entry = next(e for e in inventory if e['block_id']==block['id'])
                if entry['operation']=='unchanged':
                    try:
                        original,_ = render_block(block)
                    except ValueError:
                        self.assertIsNone(entry['latex'])
                    else:
                        self.assertEqual(entry['latex'],original)
                        self.assertIn(original,document)
                elif entry['operation']=='delete':
                    self.assertEqual(entry['status'],'explicitly_deleted')
                    self.assertIn('Explicitly deleted source block: '+block['id'],document)
                    self.assertNotIn('DETACHED (Q.7)',document)
        p2 = (self.derivative/'pages/fixture-native-p0002/document.tex').read_text()
        self.assertIn(r'\usepackage{graphicx}',p2)
        self.assertIn(r'\usepackage{amsmath}',p2)
        self.assertIn('CONTROL prose; do not drop.',p2)
        self.assertNotIn('NOT AUTHORIZED',p2)
        self.assertEqual(read_json(self.derivative/'summary.json')['explicitly_deleted_blocks'],1)
        self.assertEqual(read_json(self.derivative/'summary.json')['compilation'],'not_run')
        for path,entries in before.items():
            self.assertEqual(files_manifest(path),entries)
        self.assertEqual(files_manifest(self.derivative/'review-evidence'),before[self.review])
        self.assertEqual(read_json(self.review/'pages/fixture-native-p0002/proposals.json')['status'],'proposals_unaccepted')

    def test_empty_authorization_and_unselected_catalog_accept_nothing(self):
        self.plan['authorization']=''
        with self.assertRaisesRegex(ValueError,'authorization'):
            self.apply()
        self.assertFalse(self.derivative.exists())
        self.plan['authorization']='Operator'
        self.plan['selected']=[]
        with self.assertRaisesRegex(ValueError,'explicitly'):
            self.apply()

    def test_partial_dependent_groups_rejected_without_derivative(self):
        original = copy.deepcopy(self.plan)
        for excluded in (1,2,3):
            self.plan = copy.deepcopy(original)
            self.plan['selected'].pop(excluded)
            with self.assertRaisesRegex(ValueError,'atomically'):
                self.apply()
            self.assertFalse(self.derivative.exists())

    def test_unknown_duplicate_and_conflicting_selections(self):
        original = copy.deepcopy(self.plan)
        self.plan['selected'].append(copy.deepcopy(self.plan['selected'][0]))
        with self.assertRaisesRegex(ValueError,'conflicting'):
            self.apply()
        self.plan=copy.deepcopy(original)
        self.plan['selected'][0]['proposal_id']='unknown'
        with self.assertRaisesRegex(ValueError,'Unknown'):
            self.apply()
        # Distinct saved proposals aimed at one target, not merely duplicate IDs.
        fresh=copy.deepcopy(original)
        fresh['catalog'][-1]['block_ids']=fresh['catalog'][0]['block_ids']
        fresh['catalog'][-1]['target_sha256']=fresh['catalog'][0]['target_sha256']
        fresh['selected'].append({'proposal_id':fresh['catalog'][-1]['proposal_id'],'operation':'replace'})
        with patch('probe.acceptance.make_plan',return_value=fresh):
            with self.assertRaisesRegex(ValueError,'Conflicting edits'):
                validated_selection(self.root,fresh)

    def test_stale_review_files_rejected(self):
        (self.review/'unexpected.txt').write_text('New evidence requires a new acceptance plan')
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.apply()
        self.assertFalse(self.derivative.exists())

    def test_stale_source_output_rejected(self):
        next(self.run.glob('attempts/*/output/document.tex')).write_text('changed')
        with self.assertRaisesRegex(ValueError,'changed'):
            self.apply()

    def test_raw_response_and_parsed_proposal_disagreement_rejected(self):
        raw = next((self.review/'pages/fixture-native-p0002').glob('attempts/*/response.raw'))
        value=read_json(raw)
        value['choices'][0]['message']['content']='{}'
        atomic_json(raw,value)
        with self.assertRaisesRegex(ValueError,'Raw HTTP'):
            self.apply()

    def test_preview_binding_and_unknown_target_catalog_rejected(self):
        self.plan['catalog'][0]['block_ids']=['unknown:block']
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.apply()
        self.plan=make_plan(self.root,self.run,self.review,self.preview)
        payload=read_json(self.preview/'pages/fixture-native-p0001/request.json')
        payload['max_tokens']=1024
        atomic_json(self.preview/'pages/fixture-native-p0001/request.json',payload)
        with self.assertRaisesRegex(ValueError,'artifact changed'):
            self.apply()

    def test_delete_requires_explicit_operation_and_empty_saved_suggestion(self):
        self.plan['selected'][2]['operation']='replace'
        with self.assertRaisesRegex(ValueError,'explicit delete'):
            self.apply()
        self.plan['selected'][2]['operation']='delete'
        self.plan['selected'][0]['operation']='delete'
        with self.assertRaisesRegex(ValueError,'must be empty'):
            self.apply()

    def test_unsupported_fragment_and_region_edits_are_deferred(self):
        for latex in (r'\input{secrets}',r'\rotatebox{90}{\input{x}}',r'\[\write18{bad}\]',
                      r'\begin{document}x\end{document}', '$x',r'\rotatebox{45}{Text}'):
            with self.subTest(latex=latex),self.assertRaises(ValueError):
                accepted_fragment(latex)
        fresh=copy.deepcopy(self.plan)
        fresh['catalog'][0]['block_ids']=[]
        with patch('probe.acceptance.make_plan',return_value=fresh):
            with self.assertRaisesRegex(ValueError,'deferred'):
                validated_selection(self.root,fresh)

    def test_focused_selection_has_exact_drafts_context_and_no_answer_leakage(self):
        preview=self.focused()
        metadata=verify_preview(preview)
        self.assertFalse(metadata['full_page_coverage'])
        self.assertEqual(len(metadata['pages']),3)
        pages=saved_pages(self.root,self.run,'fixture-native')
        verify_focused_inputs(self.root,self.run,preview,metadata,pages)
        for record,block_id in zip(metadata['pages'],metadata['selected_block_ids']):
            folder=preview/'pages'/record['page_id']
            payload=read_json(folder/'request.json')
            text=payload['messages'][0]['content'][0]['text']
            data=json.loads(text.split('\nSELECTED REGION DATA:\n')[1])
            self.assertEqual([b['id'] for b in data['blocks']],[block_id])
            self.assertEqual([d['block_id'] for d in data['draft_by_block']],[block_id])
            self.assertTrue(data['context_blocks'])
            self.assertFalse(data['context_is_reviewed'])
            self.assertEqual(len(data['images']),2)
            self.assertNotIn('GOLD_ONLY_SENTINEL',text)
            self.assertNotIn('ANSWER_ONLY_SENTINEL',text)
            self.assertNotIn('NOT AUTHORIZED',text)
            self.assertNotIn('unresolved_issues',text)
            self.assertEqual(payload['reasoning_effort'],'high')
            self.assertEqual(payload['max_tokens'],16384)
            self.assertEqual(record['budgets']['timeout_seconds'],600)

    def test_focused_actual_serialization_and_limited_result_coverage(self):
        preview=self.focused()
        outgoing=[]
        result=self.root/'focused-results'
        result.mkdir()
        before=files_manifest(preview)
        with patch.object(LocalClient,'_connection',transport(outgoing,lambda p:[])):
            self.assertTrue(review_pages(self.root,self.run,preview,self.preflight,result,self.config))
        metadata=verify_preview(preview)
        for record,payload in zip(metadata['pages'],outgoing):
            self.assertEqual(payload,read_json(preview/'pages'/record['page_id']/'request.json'))
        summary=read_json(result/'summary.json')
        self.assertEqual(summary['coverage'],'selected_regions_complete')
        self.assertFalse(summary['full_page_coverage'])
        self.assertNotIn('completed_pages',summary)
        self.assertEqual(len(summary['completed_regions']),3)
        self.assertEqual(files_manifest(preview),before)

    def test_focused_rejects_context_coverage_and_missing_scope(self):
        preview=self.focused()
        meta=verify_preview(preview)
        page=read_json(preview/'pages'/meta['pages'][0]['page_id']/'page.json')
        value={'page_id':page['page_id'],'scope':'selected_blocks','complete':True,
               'reviewed_block_ids':[b['id'] for b in page['blocks']],'proposals':[]}
        self.assertEqual(validate_review_response(value,page),value)
        value['reviewed_block_ids'].append(page['context_blocks'][0]['id'])
        with self.assertRaisesRegex(ValueError,'coverage'):
            validate_review_response(value,page)
        value.pop('scope')
        with self.assertRaisesRegex(ValueError,'selected_blocks'):
            validate_review_response(value,page)

    def test_focused_rejects_unknown_duplicates_hints_and_deleted_targets(self):
        self.apply()
        pages=saved_pages(self.root,self.run,'fixture-native')
        inventory=read_json(self.derivative/'inventory.json')
        for selection in ({'block_ids':['unknown']},{'block_ids':['fixture-native-p0001:b1']*2},
                          {'block_ids':['fixture-native-p0001:b1'],'expected':'answer'},
                          {'block_ids':['fixture-native-p0002:b2']}):
            with self.subTest(selection=selection),self.assertRaises(ValueError):
                select_blocks(selection,pages,inventory,self.limits)

    def test_changed_derivative_cannot_supply_focused_drafts(self):
        self.apply()
        (self.derivative/'pages/fixture-native-p0001/document.tex').write_text('tampered')
        with self.assertRaisesRegex(ValueError,'Derivative artifacts changed'):
            verify_derivative(self.root,self.run,self.derivative)

    def test_cli_new_modes_and_selection_options(self):
        args=cli.parser().parse_args(['review','--mode','regions','--preview-only','--run','ocr',
            '--derivative','derivative','--block-selection','blocks.json','--page-reasoning-effort','high',
            '--page-max-tokens','16384','--page-timeout','600'])
        self.assertEqual(args.mode,'regions')
        self.assertEqual(args.page_max_tokens,16384)
        self.assertEqual(cli.parser().parse_args(['apply-accepted','--plan','selection.json']).command,'apply-accepted')
