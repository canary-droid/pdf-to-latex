"""Recorded-response and synthetic offline regressions; no model/secret access."""
import copy
import json
from pathlib import Path
import unittest

from probe import critic_context as ctx, critic_anchors as ca, experiment as ex
from probe.common import read_json, fingerprint
from probe.recovery import ValidationError, single_outer_fence
from probe.sciwrite_subset import finding_views, compare_findings
from test_critic_route import data, answer

FIXTURE=Path(__file__).parent/'fixtures/critic-backlog-records.json'


class ContextBacklogTests(unittest.TestCase):
    def setUp(self):
        self.rows=read_json(FIXTURE)['context_rows']
        self.index=ctx.build_index(self.rows,{'source':'recorded same edition'})

    def test_complete_theorem_includes_conditions_and_excludes_folio_and_proof(self):
        rows,records=ctx.resolve(self.index,['Theorem 6.3 (hypotheses and growth conditions)'])
        self.assertEqual([r['block_id'].rsplit(':',1)[1] for r in rows],['b2','b3','b4','b5'])
        self.assertTrue(records[0]['complete_statement'])
        self.assertEqual(records[0]['status'],'added')
        self.assertEqual([r['basis'] for r in rows],[r['basis'] for r in self.rows[1:5]])
        self.assertEqual([r['source_block_sha256'] for r in rows],[r['source_block_sha256'] for r in self.rows[1:5]])
        self.assertEqual(records[0]['original_requests'],['Theorem 6.3 (hypotheses and growth conditions)'])

    def test_supplied_heading_does_not_hide_missing_continuation_and_deduplicates(self):
        rows,records=ctx.resolve(self.index,['Theorem 6.3','Theorem 6.3 (full statement)'],[r['block_id'] for r in self.rows[:3]])
        self.assertEqual([r['block_id'].rsplit(':',1)[1] for r in rows],['b4','b5'])
        self.assertEqual(len(records),1);self.assertEqual(len(records[0]['original_requests']),2)

    def test_statement_crosses_page_but_not_missing_page(self):
        rows=copy.deepcopy(self.rows)
        for r in rows[4:]:r['source_location']['page']['selected_page']+=1
        index=ctx.build_index(rows,{});self.assertEqual(len(ctx.resolve(index,['theorem 6.3'])[0]),4)
        for r in rows[4:]:r['source_location']['page']['selected_page']+=1
        index=ctx.build_index(rows,{})
        chosen,records=ctx.resolve(index,['theorem 6.3'])
        self.assertFalse(chosen);self.assertIn('partial',records[0]['status'])

    def test_budget_and_unfinished_statement_do_not_spend_on_heading_only(self):
        self.assertFalse(ctx.resolve(self.index,['theorem 6.3'],policy={**ctx.POLICY,'max_blocks':3})[0])
        short=ctx.build_index(self.rows[:3],{})
        rows,records=ctx.resolve(short,['theorem 6.3'])
        self.assertFalse(rows);self.assertIn('partial',records[0]['status'])

    def test_statement_not_passing_mention_and_ambiguous_missing(self):
        rows=copy.deepcopy(self.rows)
        rows[0]['text']='Recall Theorem 6.3 in the previous section.'
        index=ctx.build_index(rows,{})
        self.assertEqual(len(index['entries']['theorem 6.3']),1)
        index['entries']['theorem 6.3']*=2
        self.assertEqual(ctx.resolve(index,['theorem 6.3'])[1][0]['status'],'ambiguous')
        self.assertIn('unavailable',ctx.resolve(index,['Definition 99.2 (needed)'])[1][0]['status'])


class ReportingBacklogTests(unittest.TestCase):
    def test_recorded_sign_and_limit_survive_visual_context_routing(self):
        fixture=read_json(FIXTURE)
        for group in ('c03','c05'):
            findings=fixture[group]['second'];views=finding_views(findings)
            self.assertIn(findings[0]['stable_id'],[r['finding']['stable_id'] for r in views['material']])
            self.assertIn(findings[0]['stable_id'],[r['finding']['stable_id'] for r in views['visual']])
            self.assertTrue(views['context'])

    def test_partial_context_does_not_erase_locally_supported_claim_and_positive_is_separate(self):
        findings=read_json(FIXTURE)['c05']['local'];views=finding_views(findings)
        self.assertTrue(views['material']);self.assertEqual(len(views['positive']),1)
        positive=views['positive'][0]['finding']['stable_id']
        self.assertNotIn(positive,[r['finding']['stable_id'] for r in views['material']+views['visual']])
        v3={**findings[0],'assessment_kind':'material_concern','context_dependency':'source_attribution'}
        self.assertTrue(finding_views([v3])['material'])
        context={**findings[0],'assessment_kind':'context_only','next_action':'supply_context'}
        self.assertFalse(finding_views([context])['material'])

    def test_recorded_agreements_match_overlap_not_identical_categories_or_sets(self):
        fixture=read_json(FIXTURE)
        for group in ('c03','c05'):
            row=fixture[group];comparison=compare_findings(row['local'],row['second'])
            self.assertIn(row['second'][0]['stable_id'],comparison['potential_agreement'])
            altered=copy.deepcopy(row['second']);altered[0]['draft_sha256']=fingerprint('different')
            self.assertNotIn(altered[0]['stable_id'],compare_findings(row['local'],altered)['potential_agreement'])

    def test_nonrepetition_not_disagreement_and_positive_conflict_is_only_candidate(self):
        a=read_json(FIXTURE)['c03']['local'][0]
        self.assertEqual(compare_findings([a],[])['possible_contradictions'],[])
        b={**a,'stable_id':'other','assessment_kind':'positive_observation','consequence':'No error: the exponent sign is consistent.'}
        out=compare_findings([a],[b]);self.assertFalse(out['potential_agreement']);self.assertEqual(len(out['possible_contradictions']),1)


class FieldRepairTests(unittest.TestCase):
    def v3(self):
        original=read_json(FIXTURE)['c06'];d=copy.deepcopy(original['input.json']);d['protocol']=ca.CURRENT_VERSION
        value=json.loads(single_outer_fence(original['assistant-response.json']['content']))
        value['protocol']=ca.CURRENT_VERSION;value.pop('candidate_sha256');value.pop('draft_sha256')
        failure={'content':json.dumps(value),'actual_model':'glm53-regular','finish_reason':'stop'}
        return d,value,failure

    def test_legacy_c06_extra_notes_and_wrong_hash_remain_rejected(self):
        f=read_json(FIXTURE)['c06'];d=f['input.json'];v=json.loads(single_outer_fence(f['assistant-response.json']['content']))
        with self.assertRaisesRegex(ValidationError,'notes'):ca.validate(v,d)
        v.pop('notes');ca.validate(v,d)
        v['candidate_sha256']=fingerprint('wrong')
        with self.assertRaisesRegex(ValidationError,'hash'):ca.validate(v,d)

    def test_v3_uses_program_binding_and_exact_field_patch_retains_commentary(self):
        d,bad,f=self.v3();request=ca.field_repair_request(ca.request(d,{'model':'glm53-regular','reasoning_effort':'high','max_tokens':16384}),f,d)
        self.assertIn('FORMAT REPAIR ONLY',request['messages'][-1]['content'])
        patch={'protocol':'critic-field-repair-v1','changes':[{'path':'$.notes','operation':'remove','value':None}]}
        result=ex.finish_completion({'actual_model':'glm53-regular','finish_reason':'stop','content':json.dumps(patch)}, {'kind':'critic'},d,'glm53-regular',Path('.'),previous_failure=f,method='json_feedback')
        self.assertEqual(result['answer']['findings'],[])
        self.assertEqual(result['field_repair']['retained_extra_fields'][0]['value'],bad['notes'])
        self.assertEqual(result['request_binding']['candidate_sha256'],d['candidate_sha256'])
        self.assertNotIn('candidate_sha256',ca.schema_for(d)['properties'])

    def test_extra_findings_changed_identifiers_or_truncation_cannot_be_repaired_away(self):
        d,bad,f=self.v3()
        with self.assertRaises(ValidationError):ca.apply_field_repair(json.dumps({'protocol':'critic-field-repair-v1','changes':[{'path':'$.findings','operation':'replace','value':[]}]}),f,d)
        bad['candidate_sha256']=fingerprint('wrong');f['content']=json.dumps(bad)
        self.assertIsNone(ca.field_repair_plan(f,d))
        self.assertIsNone(ca.field_repair_plan({**f,'finish_reason':'length'},d))
        d,bad,f=self.v3();good={k:v for k,v in bad.items() if k!='notes'};good['findings']=[{'id':'invented'}]
        with self.assertRaisesRegex(ValidationError,'count'):ca.preserve_repair(f,good,d,'glm53-regular')

    def test_patch_preserves_unrelated_substantive_findings_uncertainty_and_references(self):
        d=data();d['protocol']=ca.CURRENT_VERSION;v=answer(d,'material');v['notes']='Substantive extra commentary retained'
        f={'content':json.dumps(v),'actual_model':'m','finish_reason':'stop'}
        patch={'protocol':'critic-field-repair-v1','changes':[{'path':'$.notes','operation':'remove','value':None}]}
        repaired,record=ca.apply_field_repair(json.dumps(patch),f,d)
        self.assertEqual(repaired['findings'],v['findings']);self.assertEqual(repaired['reviewed_anchor_ids'],v['reviewed_anchor_ids'])


if __name__=='__main__':unittest.main()
