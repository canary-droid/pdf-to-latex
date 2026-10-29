"""Exact-version assessment guards; no semantic-completeness heuristic."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from probe import experiment as ex, text_critic as tc
from probe.common import atomic_json, read_json, fingerprint, files_manifest, sha
from probe.evaluation_export import (edits_for, disposition_template, build_candidate,
    candidate_source, draft)
from probe.recovery_trial import refresh_critic_recipe, prepare_critic
import test_recovery_critic as fixtures
from test_recovery_critic import FakeClient, block, proposal, critic_data


class AssessmentTests(unittest.TestCase):
    def test_no_assessment_is_fail_closed_even_for_valid_fragment(self):
        p={'id':'p','proposal':proposal(text=r'\(e^x\)')}
        edits,records=edits_for([block()],[p])
        self.assertFalse(edits);self.assertEqual(records[0]['status'],'deferred')

    def test_explicit_incomplete_decision_overrides_suitable_label(self):
        p={'id':'p','proposal':proposal()}
        edits,_=edits_for([block()],[p],{'p':{'evidence_sha256':fingerprint(p),
            'disposition':'suitable','whole_block_preserved':False,'reason':'Incomplete paragraph'}})
        self.assertFalse(edits)

    def test_assessment_cannot_follow_changed_proposal_or_call(self):
        p={'id':'p','proposal':proposal(),'call_seal_sha256':'one'}
        decision={'p':{'evidence_sha256':fingerprint(p),'disposition':'suitable','whole_block_preserved':True}}
        for changed in ({**p,'call_seal_sha256':'two'},{**p,'proposal':proposal(text='Different')}):
            with self.assertRaisesRegex(ValueError,'version changed'):edits_for([block()],[changed],decision)

    def test_saved_v105_entire_paragraph_is_preserved(self):
        run=Path(__file__).resolve().parents[1]/'runs/recovery-continuation-trial-20261024T112538Z-8d13d3'
        if not run.exists():self.skipTest('Local book evidence intentionally outside Git')
        # This is a regression against a historical response, not preparation of
        # a new derivative. The current registry legitimately gained Gatheral;
        # candidate_source must still reject that stale live source binding.
        # Read only the exact sealed historical input/call needed for this test.
        binding=read_json(run/'binding.json');state=read_json(run/'state.json')
        self.assertEqual(state['binding_sha256'],fingerprint(binding))
        preview=Path(binding['preview']);ex.verify_seal(preview,binding['manifest_sha256'])
        u=next(u for u in read_json(preview/'units.json') if u['id']=='v105')
        b=read_json(preview/u['data'])['blocks'][0]
        call=next(c for c in state['calls'] if c['id']==state['units']['v105']['last_call'])
        self.assertEqual(call['parent'],'v105')
        folder=run/'calls'/call['id'];ex.verify_seal(folder,call['seal_sha256'],'seal.json')
        proposal=read_json(folder/'outcome.json')['answer']['proposals'][0]
        self.assertEqual(proposal['block_ids'],[b['id']])
        p={'id':'v105:0:'+fingerprint(proposal)[:16],'proposal':proposal,
           'review_call':call['id'],'call_seal_sha256':call['seal_sha256']}
        before=draft(b)['text'];self.assertIn('Laplace',before)
        self.assertNotIn('Laplace',p['proposal']['suggested_latex'])
        decisions={p['id']:{'evidence_sha256':fingerprint(p),'disposition':'deferred',
            'whole_block_preserved':False,'reason':'Formula-only replacement drops paragraph'}}
        edits,records=edits_for([b],[p],decisions)
        self.assertFalse(edits);self.assertEqual(draft(b)['text'],before)
        self.assertEqual(records[0]['proposal'],p['proposal'])


class ReviewedCandidateTests(unittest.TestCase):
    setUp=fixtures.ExecutorTests.setUp
    run_stage=fixtures.ExecutorTests.run_stage
    state=fixtures.ExecutorTests.state

    def prepared(self,disposition='deferred'):
        FakeClient.actions=['tex','ok','ok'];self.run_stage();self.run_stage('continue',resume=True)
        record=disposition_template(self.out)
        for d in record['decisions']:d.update(disposition=disposition,whole_block_preserved=disposition=='suitable',reason='Complete-block assessment')
        path=self.root/'assessment.json';atomic_json(path,record)
        return path,record

    def test_deferred_paragraph_and_unaffected_order_evidence_unchanged(self):
        path,_=self.prepared();before=files_manifest(self.out);out=self.root/'candidate'
        build_candidate(self.preview,self.out,out,dispositions=path)
        rows=read_json(out/'inventory.json')
        self.assertEqual([r['block_id'] for r in rows],['p1:b1','p1:b2','p1:b3'])
        self.assertTrue(all(r['after']==r['before']['text'] for r in rows))
        self.assertEqual(read_json(out/'changes.json')[0]['status'],'deferred')
        self.assertEqual(files_manifest(self.out),before)

    def test_bound_assessment_rejects_missing_unknown_duplicate_stale(self):
        path,record=self.prepared()
        for field in ('state_sha256','catalog_sha256','preview_manifest_sha256'):
            bad=copy.deepcopy(record);bad[field]='changed';atomic_json(path,bad)
            with self.assertRaisesRegex(ValueError,'binding'):build_candidate(self.preview,self.out,self.root/'bad',dispositions=path)
        for rows in ([],record['decisions']*2,[{**record['decisions'][0],'id':'unknown'}],
                     [{**record['decisions'][0],'evidence_sha256':'changed'}]):
            atomic_json(path,{**record,'decisions':rows})
            with self.assertRaises(ValueError):build_candidate(self.preview,self.out,self.root/'bad',dispositions=path)
        self.assertFalse((self.root/'bad').exists())

    def test_historical_review_code_retained_new_assembly_code_separate(self):
        path,_=self.prepared('suitable');old=read_json(self.preview/'preview.json')['code_sha256']
        changed={**old,'evaluation_export.py':'new assembly'}
        with patch('probe.experiment.code_hashes',return_value=changed):
            build_candidate(self.preview,self.out,self.root/'candidate',dispositions=path)
        p=read_json(self.root/'candidate/provenance.json')
        self.assertEqual(p['historical_review_code_sha256'],old);self.assertEqual(p['code_sha256'],changed)
        self.assertEqual(p['applied'],1);self.assertFalse(p['final_acceptance'])

    def test_unrepresentable_deferred_content_retains_complete_native(self):
        path,_=self.prepared()
        from probe.evaluation_export import draft as real_draft
        def unsupported(b):
            result=real_draft(b)
            if b['id']=='p1:b1':return {'text':'complete raw OCR including all conditions','packages':[],
                'format':'complete_structured_OCR_JSON','export_status':'unresolved','reason':'synthetic unsupported macro'}
            return result
        with patch('probe.evaluation_export.draft',side_effect=unsupported):
            build_candidate(self.preview,self.out,self.root/'candidate',dispositions=path)
        row=read_json(self.root/'candidate/inventory.json')[0]
        self.assertEqual(row['status'],'unresolved');self.assertEqual(row['after'],row['before']['text'])
        self.assertEqual(row['source_native'],block()['native'])
        self.assertIn('Unresolved', (self.root/'candidate/candidate.tex').read_text())


class RecipeRefreshTests(unittest.TestCase):
    def recipe(self,root):
        recipe=root/'recipe';recipe.mkdir();data=critic_data()
        atomic_json(recipe/'input.json',data);atomic_json(recipe/'request.json',tc.request(data))
        atomic_json(recipe/'recipe.json',{'system_prompt_sha256':fingerprint(tc.SYSTEM),'source_hashes':{},
            'code_sha256':{'old':'historical'},'profile':'deepseek','groups':[{'id':'g01',
                'baseline_input':'input.json','baseline_request':'request.json','split':'development','gate':True}],
            'limits':{'baseline_calls':40,'recovery_calls':24,'per_parent_recovery':2,'admission_seconds':14400}})
        ex.seal(recipe);return recipe

    def test_refresh_exact_requests_selection_settings_and_original_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);old=self.recipe(root);before=files_manifest(old);new=root/'new'
            refresh_critic_recipe(old,new);ex.verify_seal(new)
            for name in ('input.json','request.json'):self.assertEqual((old/name).read_bytes(),(new/name).read_bytes())
            a=read_json(old/'recipe.json');b=read_json(new/'recipe.json')
            for key in ('groups','limits','profile','system_prompt_sha256'):self.assertEqual(a[key],b[key])
            self.assertEqual(b['lineage']['historical_code_sha256'],a['code_sha256'])
            self.assertEqual(b['code_sha256'],ex.code_hashes());self.assertEqual(files_manifest(old),before)

    def test_changed_prompt_or_request_refuses_refresh(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);old=self.recipe(root)
            for target in ('prompt','request'):
                with self.subTest(target=target):
                    if target=='prompt':
                        with patch('probe.text_critic.SYSTEM','Changed'):
                            with self.assertRaisesRegex(ValueError,'prompt changed'):refresh_critic_recipe(old,root/'bad')
                    else:
                        request=read_json(old/'request.json');request['max_tokens']=100
                        atomic_json(old/'request.json',request);(old/'manifest.json').unlink();ex.seal(old)
                        with self.assertRaisesRegex(ValueError,'request changed'):refresh_critic_recipe(old,root/'bad')
            self.assertFalse((root/'bad').exists())


if __name__=='__main__':unittest.main()
